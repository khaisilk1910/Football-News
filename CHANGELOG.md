# Lịch sử Football News

## 2026.11.12.7 — Hai cột cầu thủ trên màn hình rộng, SVG bóng/giày mới

- Trang **Cầu thủ nổi bật** hiển thị 2 bảng Top 15 cạnh nhau khi khu vực hiển thị đủ rộng, tự xếp dọc khi hẹp; không thay đổi bố cục Top 3 trong trang Tổng quan.
- Thay nét icon nội bộ bằng SVG bóng đá nhiều mảng rõ nét và giày chuyền bóng, có bóng và vệt chuyển động; giữ huy chương vàng/bạc/đồng cho ba hạng đầu.
- Không phát sinh request ảnh; kiểm tra 14 tổ hợp kích thước và theme bằng Chromium, có test hồi quy frontend.

## 2026.11.12.6 — Top 15, icon nội bộ và ổn định cache

- Thay toàn bộ ảnh chân dung của bảng Top cầu thủ bằng biểu tượng SVG: bóng cho bàn thắng, giày chuyền bóng cho kiến tạo; hạng 1/2/3 vàng, bạc, đồng, các hạng sau trung tính. Không tạo request ảnh cầu thủ.
- Tổng quan vẫn Top 3 của mỗi nhóm; trang Cầu thủ nổi bật mở rộng tối đa Top 15 bàn thắng và Top 15 kiến tạo khi ESPN cung cấp đủ.
- Bộ đọc ESPN Core cho phép xét tối đa 15 vị trí ở hai nhóm, xử lý tham chiếu có giới hạn song song và timeout, không suy diễn thống kê bị thiếu.
- Lưu snapshot công khai vào localStorage (6 giờ) và cache cầu thủ (6 giờ), giữ dữ liệu khi mở lại sidebar, tải lại trang, hoặc khi WebSocket trả phản hồi chưa đầy đủ.
- Giảm thời gian chờ và thử đồng bộ lại khi config entry/coordinator chưa sẵn sàng. Thêm kiểm thử dữ liệu cache xuyên tab và bố cục Chromium.


## 2026.11.12.5 - Overview leader layout fix

- Overview Top 3 goals and assists now align rank, portrait, name/club, and a numeric value in four columns; values no longer sit beneath a player name.
- Adds an Overview Top 3 assists card when ESPN supplies data, with responsive layout and screen-reader descriptions.
- No changes to ESPN provider, Zalo settings, or startup behavior.

## 2026.11.12.4 — Ảnh chân dung cầu thủ ESPN

- Bảng Cầu thủ nổi bật hiển thị Top 3 cho từng nhóm, với ảnh cầu thủ tròn, thứ hạng, tên, CLB, giá trị thống kê theo thiết kế di động.
- Lấy URL ảnh từ `headshot`/`photo` ESPN; khi JSON thiếu ảnh nhưng có ESPN athlete ID hợp lệ thì dùng ảnh từ ESPN CDN.
- Với dữ liệu thống kê HTML ESPN, lấy athlete ID từ liên kết hồ sơ cầu thủ để khôi phục ảnh mà không gọi thêm API.
- Cũng áp dụng ảnh ESPN cho danh sách đội hình; ảnh lỗi 404 hiển thị hình người dự phòng thay vì hình lỗi.
- Không tải ảnh trong backend hoặc khi khởi động Home Assistant; trình duyệt tải ảnh lazy-load. Bổ sung kiểm thử Python, Node.js và giao diện.


## 2026.11.12.3 — Ổn định khởi tạo và thống kê ESPN

- Lần đầu mở sidebar không còn báo sai chưa có giải đấu trong lúc Home Assistant đang nạp config entry; thử lại có kiểm soát, giữ snapshot hợp lệ khi backend tạm trả danh sách rỗng.
- Dùng runtime đã nạp nếu registry Home Assistant tạm thời không trả entry.
- Cải thiện ESPN Core: tham chiếu cầu thủ theo mùa và league, tải có giới hạn song song, trả Top có dữ liệu sớm hơn.
- Cải thiện fallback HTML ESPN: bảng tách cột, tiêu đề HTML `Table__Title`; không vượt trang chặn truy cập.
- Hiển thị lỗi ESPN có mã HTTP/nguyên nhân khi mở Cầu thủ nổi bật; thêm kiểm thử cold-open, quay lại dashboard và hồi quy JSON/HTML.


## 2026.11.12.2

- Giữ ESPN làm nguồn dữ liệu bóng đá duy nhất; bỏ toàn bộ mã provider khác, tùy chọn khóa và cầu nối cảm biến bên ngoài.
- Dọn các cài đặt nhà cung cấp cũ trong config entry khi nâng cấp; không ảnh hưởng cấu hình Zalo, đội yêu thích hoặc dữ liệu giải.
- Ưu tiên ESPN Core leaders theo mùa, bổ sung nhóm thống kê và giải mã athlete references có giới hạn.
- Tài liệu tiếng Việt và kiểm thử cho các trường hợp không có dữ liệu, lỗi 403/429, và season hợp lệ.

