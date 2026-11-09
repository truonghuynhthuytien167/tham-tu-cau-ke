# THÁM TỬ CÂU KỂ – WEB THI ĐỒNG THỜI

Ứng dụng Python thuần + HTML/CSS/JS, không cần Firebase. Học sinh truy cập **cùng một URL HTTPS**, nhập tên đội (không cần tài khoản), thi hai vòng. Bảng xếp hạng chung được máy chủ cập nhật và các thiết bị tải lại tự động mỗi 2 giây.

## Chạy thử trên máy tính

Cài Python 3, mở Terminal/CMD tại thư mục dự án và chạy:

Windows PowerShell: `$env:GAME_ADMIN_PASSWORD="mat-khau-manh"; python server.py`

macOS/Linux: `GAME_ADMIN_PASSWORD='mat-khau-manh' python3 server.py`

Mở `http://localhost:8000`. Đây chỉ là chạy thử trên máy, **chưa phải website công khai**.

## Đăng lên Render

1. Đăng nhập GitHub, tạo repository mới và tải **toàn bộ nội dung thư mục này** lên gốc repository, gồm `server.py`, `index.html`, `static/`, `render.yaml`.
2. Vào https://dashboard.render.com → New → Web Service → kết nối GitHub → chọn repository.
3. Chọn Python, build command `echo ready`, start command `python server.py`, gói Free để thử.
4. Trong Environment → thêm `GAME_ADMIN_PASSWORD` với mật khẩu giáo viên tự chọn, **không ghi mật khẩu vào mã nguồn**.
5. Deploy, chờ trạng thái Live và sao chép **đường link thực tế** `https://<ten-dich-vu>.onrender.com` từ trang Render. Link ví dụ không phải link đã hoạt động.
6. Mở URL trên hai điện thoại khác nhau và máy giáo viên, cho hai nhóm thử thi, quan sát bảng xếp hạng cập nhật.

## Lưu ý quan trọng

- Render Free có thể ngủ khi không sử dụng, khởi động lại chậm. SQLite trên ổ đĩa mặc định của Render Free **không bền vững** khi deploy/restart; điểm và bảng xếp hạng có thể bị mất. **Không dùng gói Free cho buổi thi quan trọng nếu cần giữ dữ liệu ổn định**. Dùng dịch vụ có ổ đĩa bền vững (Render paid persistent disk) và đặt biến `GAME_DB=/var/data/game.sqlite3`, hoặc nâng cấp sang cơ sở dữ liệu PostgreSQL được quản lý.
- Tính điểm do máy chủ thực hiện. Vòng 1 đúng toàn bộ mới mở vòng 2; điểm vòng 1 tính theo lần nộp đầu. Vòng 2 nộp **một lần**, câu chưa phân loại tính sai. Điểm tối đa 110, xếp hạng theo điểm rồi thời gian.
- Mỗi đội chỉ được dùng một tên trong một đợt thi. Để tránh mất lượt, không đóng tab khi đang chơi. Không có chức năng khôi phục phiên sau khi tải lại trang.
- Tên nhóm không nên chứa thông tin cá nhân học sinh. Mật khẩu giáo viên chỉ dùng ở trang bảng xếp hạng.
- Thiết bị phải có Internet và kết nối được URL; không cần chung Wi-Fi.
