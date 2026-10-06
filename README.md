# Treo máy LMS VNU

Tự đăng nhập `lms.vnu.edu.vn` và lần lượt mở các bài học (video / bài đọc / PDF) cho tới khi LMS tích xanh.

## Cần cài trước (chỉ 1 lần)

1. **Python 3.8+** – https://www.python.org/downloads/
   Khi cài nhớ tick **"Add Python to PATH"**.
2. **Google Chrome** (bản thường là được).

Không cần cài gì thêm: `chay.bat` tự cài thư viện (`selenium`, `webdriver-manager`) và tự tải ChromeDriver khớp với Chrome. Máy cần có mạng.

## Cách dùng

1. Tải về: `git clone <link repo>` hoặc **Code → Download ZIP** rồi giải nén.
2. Nháy đúp **`chay.bat`**.
3. Lần đầu: nhập mã SV, mật khẩu, link lớp học (Enter = lớp mặc định). Thông tin lưu vào `taikhoan.json`.
4. Những lần sau: cứ nháy đúp `chay.bat`, đợi 5 giây là chạy (bấm **D** để đổi tài khoản).

Để máy chạy, không tắt Chrome / cửa sổ đen. Chạy xong script in ra danh sách bài phải tự làm (trắc nghiệm, Zoom, bài tính điểm...). Làm xong các bài đó thì chạy lại `chay.bat` để treo tiếp phần bị khoá phía sau.

## Lưu ý

- `taikhoan.json` chứa mật khẩu dạng chữ thường. Không gửi file này cho ai (đã nằm trong `.gitignore`).
- Nếu trang đăng nhập báo sai mật khẩu dù đúng: trang VNU có cơ chế phát hiện trình duyệt tự động. Khi đó tự đăng nhập tay trong cửa sổ Chrome mà script mở ra (script chờ 5 phút). Phiên được lưu trong `chrome_profile/` nên lần sau không phải đăng nhập lại.
- Đổi tài khoản bằng cách sửa `taikhoan.json` thì xoá luôn thư mục `chrome_profile/`.
