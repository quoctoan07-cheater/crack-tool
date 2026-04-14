# 📱 REALME URL TOOL – Chỉnh sửa URL trong file .so (XOR + OXORANY)

Công cụ dòng lệnh dành cho Realme, hỗ trợ tìm và thay thế URL trong các file thư viện `.so` đã bị mã hóa bằng thuật toán **XOR** hoặc **OXORANY** (một biến thể XOR với key động).

## 🚀 Tính năng chính

- **Brute‑force key XOR** (0–255) tự động dựa trên URL tìm thấy.
- **Xem danh sách URL** trong file (cả URL đầy đủ, base URL, domain plaintext).
- **Thay thế URL** (chế độ XOR) – giữ nguyên độ dài.
- **Thay thế URL** (chế độ OXORANY) – phát hiện key từ mẫu `https://`, tự động mã hóa lại.
- **Backup** file gốc trước khi sửa (`.bak`).
- Hỗ trợ cả Windows và Linux/macOS.

## 📦 Yêu cầu

- Python 3.6 trở lên
- Các thư viện tích hợp sẵn (`sys`, `os`, `re`, `shutil`, `typing`)

## 🛠 Cài đặt

Không cần cài đặt gì thêm. Tải script `crack.py` về và chạy trực tiếp:

```bash
python crack.py
