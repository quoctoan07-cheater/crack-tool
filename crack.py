import sys
import os
import re
import shutil
from typing import List, Tuple, Optional, Dict

class Colors:
    RED = "\033[38;2;240;60;60m"
    BLUE = "\033[38;2;50;115;220m"
    CYAN = "\033[38;2;0;200;255m"
    GREEN = "\033[38;2;40;230;150m"
    YELLOW = "\033[38;2;255;200;0m"
    PURPLE = "\033[38;2;180;100;220m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def cprint(text: str, color: str = Colors.RESET):
    print(f"{color}{text}{Colors.RESET}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def hr(char="─", width=60, color=Colors.BLUE):
    cprint(char * width, color)

DEFAULT_KEY = 0x2E

def xor_crypt(data: bytes, key: int) -> bytes:
    return bytes([b ^ (key & 0xFF) for b in data])

def find_urls_in_data(data: bytes, include_base_only: bool = False) -> List[Tuple[int, str]]:
    """
    Tìm URL trong dữ liệu.
    include_base_only: Nếu True, cũng tìm base URL không có path (dành cho panel link riêng)
    """
    matches = []
    
    url_pattern = re.compile(rb"https?://[A-Za-z0-9\._\-?=%%&:/#]+")
    for m in url_pattern.finditer(data):
        try:
            url_str = m.group().decode('utf-8', errors='ignore')
            if '.' in url_str and len(url_str) > 10:
                matches.append((m.start(), url_str))
        except:
            continue
    
    if include_base_only:
        base_pattern = re.compile(rb"https?://[A-Za-z0-9\._\-:]+(?=[^A-Za-z0-9\._\-:/]|$)")
        for m in base_pattern.finditer(data):
            try:
                url_str = m.group().decode('utf-8', errors='ignore')
                if '.' in url_str and len(url_str) >= 10:
                    if not any(offset == m.start() for offset, _ in matches):
                        matches.append((m.start(), url_str))
            except:
                continue
    

    domain_pattern = re.compile(rb"[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z0-9][-a-zA-Z0-9.]*\.(com|net|org|io|xyz|me|co|id|app|dev|gg|cc|top|site)|fun|online|tech|store|blog|info|biz|us|uk|cn|ru|jp|fr|de|eu|tv|ws|club|vip|pro|art|design|click")
    for m in domain_pattern.finditer(data):
        try:
            domain_str = m.group().decode('utf-8', errors='ignore')
            if len(domain_str) >= 8 and domain_str.count('.') >= 1:
                if not any(offset == m.start() for offset, _ in matches):
                    matches.append((m.start(), domain_str))
        except:
            continue
    
    matches.sort(key=lambda x: x[0])
    return matches

def patch_by_offset(data: bytearray, offset: int, old_bytes: bytes, new_bytes: bytes) -> bool:
    end = offset + len(old_bytes)
    if offset < 0 or end > len(data):
        return False
    if bytes(data[offset:end]) != old_bytes:
        return False
    data[offset:offset + len(new_bytes)] = new_bytes
    if len(new_bytes) < len(old_bytes):
        pad_len = len(old_bytes) - len(new_bytes)
        data[offset + len(new_bytes):end] = b"\x00" * pad_len
    return True

def oxorany_decrypt_byte(enc_byte: int, i: int, key: int) -> int:
    temp = enc_byte ^ ((i + key) & 0xFF)
    return (temp - (key * 7)) & 0xFF

def oxorany_decrypt_string(enc_bytes: bytes, key: int) -> str:
    decrypted = []
    for i, b in enumerate(enc_bytes):
        dec = oxorany_decrypt_byte(b, i, key)
        if dec == 0:
            break
        decrypted.append(dec)
    try:
        return bytes(decrypted).decode('utf-8', errors='ignore')
    except:
        return ""

def oxorany_encrypt_string(plain_str: str, key: int) -> bytes:
    plain_bytes = plain_str.encode('utf-8') + b'\x00'
    return bytes(
        ((b + (key * 7)) ^ (i + key)) & 0xFF
        for i, b in enumerate(plain_bytes)
    )

def find_oxorany_url_candidates(data: bytes, min_len: int = 20, max_len: int = 200) -> List[Tuple[int, bytes]]:
    candidates = []
    i = 0
    n = len(data)
    while i < n - min_len:
        if data[i] == 0:
            i += 1
            continue
        start = i
        length = 0
        while i < n and data[i] != 0 and length < max_len:
            i += 1
            length += 1
        if i < n and data[i] == 0 and min_len <= length <= max_len:
            raw = data[start:start + length + 1]
            if raw.count(b'\x00') == 1:
                candidates.append((start, raw))
            i += 1
        else:
            i += 1
    return candidates

def recover_key_from_https_candidate(enc_bytes: bytes, max_key_search: int = 65536) -> Optional[Tuple[int, str]]:
    if len(enc_bytes) < 8:
        return None
    https_bytes = b"https://"
    for key in range(max_key_search):
        match = True
        for i in range(8):
            dec = oxorany_decrypt_byte(enc_bytes[i], i, key)
            if dec != https_bytes[i]:
                match = False
                break
        if match:
            full_str = oxorany_decrypt_string(enc_bytes, key)
            if full_str.startswith("https://") and '.' in full_str and len(full_str) >= 15:
                return key, full_str
    return None

def backup_file(path: str) -> str:
    bak = path + ".bak"
    shutil.copy2(path, bak)
    return bak

def brute_force_key(file_path: str) -> int:
    cprint("\n🔍 Bắt đầu brute-force XOR key (0–255)...", Colors.CYAN)
    cprint("    Tìm kiếm URL đầy đủ và base URL (cho panel link)...", Colors.CYAN)
    try:
        with open(file_path, "rb") as f:
            encrypted = f.read()
    except Exception as e:
        cprint(f"❌ Không thể đọc file: {e}", Colors.RED)
        return -1

    valid_keys = []
    for key in range(256):
        try:
            decrypted = xor_crypt(encrypted, key)
            urls = find_urls_in_data(decrypted, include_base_only=True)
            if urls:
                cprint(f"✅ Tìm thấy key: 0x{key:02X} ({key}) → {len(urls)} URL", Colors.GREEN)
                for i, (_, url) in enumerate(urls[:3], 1):
                    cprint(f"   Ví dụ: {url}", Colors.BLUE)
                valid_keys.append(key)
        except:
            continue

    if not valid_keys:
        cprint("❌ Không tìm thấy key hợp lệ nào.", Colors.RED)
        return -1
    elif len(valid_keys) == 1:
        cprint(f"\n🎯 Sử dụng key: 0x{valid_keys[0]:02X}", Colors.GREEN)
        return valid_keys[0]
    else:
        cprint(f"\n⚠️  Tìm thấy {len(valid_keys)} key hợp lệ:", Colors.YELLOW)
        for i, k in enumerate(valid_keys, 1):
            cprint(f"{i}. 0x{k:02X} ({k})", Colors.BLUE)
        while True:
            try:
                choice = input(f"\n{Colors.BOLD}Chọn số thứ tự key: {Colors.RESET}").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(valid_keys):
                    return valid_keys[idx]
                else:
                    cprint("❌ Lựa chọn không hợp lệ!", Colors.RED)
            except ValueError:
                cprint("❌ Hãy nhập số!", Colors.RED)

def list_urls_xor(file_path: str, key: int):
    try:
        with open(file_path, "rb") as f:
            encrypted = f.read()
        decrypted = xor_crypt(encrypted, key)
        
        urls = find_urls_in_data(decrypted, include_base_only=True)
        
        if not urls:
            cprint("❌ Không tìm thấy URL nào (chế độ XOR).", Colors.RED)
            return
        
        cprint(f"\n🔗 Tìm thấy {len(urls)} URL (XOR key 0x{key:02X}):", Colors.GREEN)
        for i, (pos, url) in enumerate(urls, 1):
            cprint(f"{i}. {url}", Colors.BLUE)
            cprint(f"   Offset: {hex(pos)}", Colors.CYAN)
        input("\nNhấn Enter để tiếp tục...")
    except Exception as e:
        cprint(f"❌ Lỗi: {e}", Colors.RED)

def replace_urls_xor(file_path: str, key: int):
    try:
        with open(file_path, "rb") as f:
            encrypted = f.read()
        decrypted = xor_crypt(encrypted, key)
        
        urls = find_urls_in_data(decrypted, include_base_only=True)
        
        if not urls:
            cprint("❌ Không có URL nào để thay thế (chế độ XOR).", Colors.RED)
            return
        
        cprint(f"\n🔗 Tìm thấy {len(urls)} URL:", Colors.GREEN)
        for i, (pos, url) in enumerate(urls, 1):
            cprint(f"{i}. {url}", Colors.BLUE)
            cprint(f"   Offset: {hex(pos)}", Colors.CYAN)
        choice = input(f"\n{Colors.BOLD}Chọn số thứ tự URL (ví dụ: 1 hoặc 1,3): {Colors.RESET}").strip()
        try:
            selected = [int(x.strip()) - 1 for x in choice.split(",") if x.strip()]
        except:
            cprint("❌ Lựa chọn không hợp lệ!", Colors.RED)
            return
        confirm = input(f"{Colors.BOLD}Chắc chắn thay thế URL này? (y/N): {Colors.RESET}").strip().lower()
        if confirm != 'y':
            cprint("🚫 Đã hủy.", Colors.YELLOW)
            return
        bak_file = backup_file(file_path)
        cprint(f"✅ Backup: {bak_file}", Colors.BLUE)
        patched = bytearray(decrypted)
        replacements = 0
        for idx in selected:
            if idx < 0 or idx >= len(urls):
                cprint(f"❌ Chỉ số không hợp lệ: {idx+1}", Colors.RED)
                continue
            offset, old_url = urls[idx]
            old_bytes = old_url.encode()
            new_url = input(f"\n{Colors.BOLD}URL mới cho '{old_url}': {Colors.RESET}").strip()
            if not new_url:
                cprint("⏩ Bỏ qua.", Colors.YELLOW)
                continue
            new_bytes = new_url.encode()
            if len(new_bytes) > len(old_bytes):
                cprint("⏩ URL mới quá dài! Bỏ qua.", Colors.YELLOW)
                continue
            if patch_by_offset(patched, offset, old_bytes, new_bytes):
                cprint(f"✅ Thành công: '{old_url}' → '{new_url}'", Colors.GREEN)
                replacements += 1
            else:
                cprint(f"❌ Patch thất bại tại offset {hex(offset)}", Colors.RED)
        if replacements == 0:
            cprint("🚫 Không có thay đổi nào.", Colors.YELLOW)
            return
        encrypted_out = xor_crypt(bytes(patched), key)
        out_file = file_path.replace(".so", "_MelzCrack.so") if file_path.endswith('.so') else file_path + "_patched"
        with open(out_file, "wb") as f:
            f.write(encrypted_out)
        try:
            shutil.copystat(file_path, out_file)
        except:
            pass
        cprint(f"\n💾 File mới: {out_file}", Colors.GREEN)
        cprint(f"✅ Đã thay thế {replacements} URL (chế độ XOR)", Colors.GREEN)
    except Exception as e:
        cprint(f"❌ Lỗi: {e}", Colors.RED)

def replace_oxorany_urls(file_path: str):
    try:
        with open(file_path, "rb") as f:
            data = bytearray(f.read())
    except Exception as e:
        cprint(f"❌ Không thể đọc file: {e}", Colors.RED)
        return

    cprint("\n🔍 Đang tìm URL đã mã hóa oxorany...", Colors.CYAN)
    candidates = find_oxorany_url_candidates(data)
    valid_urls: List[Dict] = []

    for offset, raw in candidates:
        result = recover_key_from_https_candidate(raw)
        if result:
            key, url = result
            valid_urls.append({
                'offset': offset,
                'original_enc': raw,
                'url': url,
                'key': key,
                'length': len(raw)
            })
            cprint(f"✅ {url[:60]}{'...' if len(url) > 60 else ''} @ {hex(offset)}", Colors.GREEN)

    if not valid_urls:
        cprint("\n❌ Không tìm thấy URL oxorany nào.", Colors.RED)
        input("\nNhấn Enter để quay lại...")
        return

    try:
        choice = input(f"\n{Colors.BOLD}Chọn số thứ tự URL (1-{len(valid_urls)}): {Colors.RESET}").strip()
        idx = int(choice) - 1
        if not (0 <= idx < len(valid_urls)):
            raise ValueError
        entry = valid_urls[idx]
    except (ValueError, KeyboardInterrupt):
        cprint("❌ Lựa chọn không hợp lệ.", Colors.RED)
        input("\nNhấn Enter để quay lại...")
        return

    new_url = input(f"\n{Colors.BOLD}URL mới cho:\n  {entry['url']}\n→ {Colors.RESET}").strip()
    if not new_url:
        cprint("🚫 Đã hủy.", Colors.YELLOW)
        input("\nNhấn Enter để quay lại...")
        return

    try:
        new_enc = oxorany_encrypt_string(new_url, entry['key'])
    except Exception as e:
        cprint(f"❌ Lỗi mã hóa: {e}", Colors.RED)
        input("\nNhấn Enter để quay lại...")
        return

    if len(new_enc) > len(entry['original_enc']):
        cprint(f"❌ URL mới quá dài! Tối đa: {len(entry['original_enc']) - 1} ký tự.", Colors.RED)
        input("\nNhấn Enter để quay lại...")
        return

    try:
        bak = backup_file(file_path)
        cprint(f"✅ Backup: {bak}", Colors.BLUE)
        
        data[entry['offset']:entry['offset'] + len(new_enc)] = new_enc
        if len(new_enc) < len(entry['original_enc']):
            pad_start = entry['offset'] + len(new_enc)
            pad_end = entry['offset'] + len(entry['original_enc'])
            data[pad_start:pad_end] = b'\x00' * (pad_end - pad_start)

        out_name = file_path.replace(".so", "_MelzCrack.so") if file_path.endswith('.so') else file_path + "_patched"
        with open(out_name, "wb") as f:
            f.write(data)
        try:
            shutil.copystat(file_path, out_name)
        except:
            pass

        cprint(f"\n🎉 THÀNH CÔNG! (chế độ oxorany)", Colors.GREEN)
        cprint(f"📁 File đầu ra: {out_name}", Colors.CYAN)
        cprint(f"🔗 URL cũ: {entry['url']}", Colors.YELLOW)
        cprint(f"🔗 URL mới: {new_url}", Colors.GREEN)

    except Exception as e:
        cprint(f"❌ Lỗi khi patch: {e}", Colors.RED)

    input("\nNhấn Enter để quay lại...")

def display_menu():
    clear_screen()
    hr("═", 55, Colors.RED)
    cprint("   🔧 MELZMOD URL TOOL (XOR + OXORANY) 🔧", Colors.RED + Colors.BOLD)
    hr("═", 55, Colors.RED)
    cprint("1. Chọn file nhị phân (.so)", Colors.BLUE)
    cprint("2. Đặt key XOR thủ công", Colors.BLUE)
    cprint("3. Xem danh sách URL (chế độ XOR)", Colors.BLUE)
    cprint("4. Thay thế URL (chế độ XOR)", Colors.BLUE)
    cprint("B. Brute-Force tự động key (XOR)", Colors.BLUE)
    cprint("5. Thay thế URL (chế độ oxorany)", Colors.BLUE)
    cprint("6. Thoát", Colors.BLUE)
    hr("─", 55, Colors.BLUE)

def main():
    current_file = ""
    current_key = DEFAULT_KEY

    while True:
        display_menu()
        choice = input(f"{Colors.BOLD}Chọn (1-6 hoặc B): {Colors.RESET}").strip().upper()

        if choice == '1':
            clear_screen()
            filename = input(f"{Colors.BOLD}Nhập đường dẫn file: {Colors.RESET}").strip()
            if not os.path.isfile(filename):
                cprint("❌ Không tìm thấy file!", Colors.RED)
                input("\nNhấn Enter...")
                continue
            current_file = filename
            cprint(f"✅ Đã chọn file: {filename}", Colors.GREEN)
            input("\nNhấn Enter...")

        elif choice == '2':
            clear_screen()
            try:
                key_input = input(f"{Colors.BOLD}Nhập key XOR (hex: 0x2E, decimal: 46): {Colors.RESET}").strip()
                if key_input.startswith('0x'):
                    key = int(key_input, 16)
                else:
                    key = int(key_input)
                current_key = key & 0xFF
                cprint(f"✅ Key mới: 0x{current_key:02X} ({current_key})", Colors.GREEN)
            except ValueError:
                cprint("❌ Key không hợp lệ!", Colors.RED)
            input("\nNhấn Enter...")

        elif choice == '3':
            clear_screen()
            if not current_file:
                cprint("❌ Chưa chọn file!", Colors.RED)
            else:
                list_urls_xor(current_file, current_key)
            input("\nNhấn Enter...")

        elif choice == '4':
            clear_screen()
            if not current_file:
                cprint("❌ Chưa chọn file!", Colors.RED)
            else:
                replace_urls_xor(current_file, current_key)
            input("\nNhấn Enter...")

        elif choice == 'B':
            clear_screen()
            if not current_file:
                cprint("❌ Hãy chọn file trước (menu 1)!", Colors.RED)
            else:
                key = brute_force_key(current_file)
                if key != -1:
                    current_key = key
                    cprint(f"\n🔑 Key đã được đặt thành: 0x{current_key:02X}", Colors.GREEN)
            input("\nNhấn Enter...")

        elif choice == '5':
            clear_screen()
            if not current_file:
                cprint("❌ Chưa chọn file!", Colors.RED)
            else:
                replace_oxorany_urls(current_file)
            input("\nNhấn Enter...")

        elif choice == '6':
            cprint("\n👋 Cảm ơn bạn! Công cụ bởi Melzmod.", Colors.CYAN)
            break

        else:
            cprint("❌ Lựa chọn không hợp lệ!", Colors.RED)
            input("\nNhấn Enter...")

if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            os.system("title MELZMOD URL TOOL - XOR + OXORANY")
        clear_screen()
        main()
    except KeyboardInterrupt:
        clear_screen()
        cprint("\n🛑 Đã dừng bởi người dùng.", Colors.YELLOW)
        sys.exit(0)