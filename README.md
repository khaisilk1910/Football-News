# Football News · Chỉ sử dụng dữ liệu ESPN

**Phiên bản 2026.11.12.7** — Home Assistant 2026.11+, tiếng Việt và giao diện sáng/tối.

Football News sử dụng **ESPN** cho lịch thi đấu, kết quả, bảng xếp hạng, tin bóng đá và thống kê cầu thủ. Không yêu cầu API key hoặc tích hợp dữ liệu khác. Zalo Bot chỉ dùng để **gửi thông báo**, không cung cấp dữ liệu bóng đá.

> **Lưu ý:** Các JSON endpoint ESPN được sử dụng là nguồn công khai nhưng **không có hợp đồng API chính thức**. Trang web ESPN có thể đòi xác minh trình duyệt; bản tích hợp không tìm cách vượt qua cơ chế bảo vệ đó. Số liệu thiếu sẽ không được tự tạo.

[![Thêm Football News vào Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=khaisilk1910&repository=Football-News&category=integration)

## Cài đặt

### Marketplace

1. Bấm nút trên hoặc mở **Cài đặt → Marketplace** và thêm repository `https://github.com/khaisilk1910/Football-News` dưới loại Integration.
2. Cài Football News, khởi động lại Home Assistant.
3. Mở **Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp → Football News**, chọn từng giải.
4. Trong sidebar mở Football News; chọn giải đấu từ dropdown.

### Thủ công

Giải nén ZIP phát hành `football_news.zip` vào `/config/custom_components/football_news/` sao cho thư mục có trực tiếp `manifest.json` và `__init__.py`. Khởi động lại Home Assistant và thêm tích hợp từ giao diện.

## Tính năng

- Lịch / vòng đấu, kết quả, trận trực tiếp, đội yêu thích, bảng xếp hạng và màu suất dự cúp/xuống hạng.
- Dashboard tiếng Việt tông đỏ-vàng, phù hợp điện thoại, dropdown, theme Home Assistant sáng/tối.
- Thống kê theo mùa từ ESPN: ghi bàn, kiến tạo, thẻ vàng/đỏ, điểm đánh giá, số trận và số phút nếu feed có đủ dữ liệu được xếp hạng.
- Bảng cầu thủ dạng 4 cột: thứ hạng, **biểu tượng SVG tại chỗ**, tên + câu lạc bộ và chỉ số bên phải. Không tải ảnh chân dung cầu thủ, không phát sinh HTTP tới CDN ảnh.
- **Ghi bàn:** biểu tượng bóng đá; **kiến tạo:** biểu tượng giày chuyền bóng. Vị trí 1/2/3 lần lượt vàng/bạc/đồng, hạng tiếp theo dùng màu trung tính.
- **Tổng quan:** Top 3 bàn thắng và Top 3 kiến tạo. **Cầu thủ nổi bật:** tối đa **Top 15** của mỗi loại khi ESPN cung cấp đủ cầu thủ; không tự bổ sung vị trí còn thiếu.
- **Bố cục responsive:** trên máy tính có đủ chiều rộng, hai bảng **Vua phá lưới** và **Kiến tạo hàng đầu** hiển thị **hai cột ngang nhau**. Trên điện thoại hoặc vùng nội dung hẹp, tự động xếp thành **một cột**, theo chiều rộng thực tế của panel Home Assistant (không phụ thuộc vào kích thước màn hình thiết bị).
- **SVG mới:** bóng đá có các mảng ghép rõ nét và giày chuyền bóng kèm bóng chuyển động; dùng màu vàng/bạc/đồng cho ba vị trí đầu, không tải ảnh hoặc biểu tượng từ bên ngoài.
- Các nhóm thẻ phạt/đánh giá khác giữ mức Top 3 nếu ESPN có số liệu.
- Thông báo Zalo qua action `zalo_bot.send_message`, danh sách chọn nhiều đội theo ID, nhắc trước trận, bàn thắng và kết quả.
- Không truy vấn mạng trong quá trình khởi động tích hợp. Chỉ nạp bảng cầu thủ khi mở trang cần, cache kết quả 6 giờ, giới hạn yêu cầu đồng thời và ngắt khi ESPN giới hạn truy cập.
- Cache trình duyệt **6 giờ** (dữ liệu bóng đá công khai) sử dụng `localStorage` để hiện ngay khi trở lại sidebar/tải lại tab. Giao diện đánh dấu dữ liệu cũ và tự đồng bộ qua Home Assistant WebSocket; khi dữ liệu chưa sẵn sàng sẽ thử lại theo khoảng cách tăng dần. ID người nhận Zalo và tùy chọn yêu thích cá nhân không được lưu trong cache chia sẻ.
- Không có chức năng Donate hoặc cá cược.

## Dữ liệu cầu thủ ESPN

Trang thống kê tham chiếu: https://www.espn.com/soccer/stats/_/league/eng.1

Nguồn JSON ESPN được thử theo thứ tự: `sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/seasons/{season}/types/2/leaders`, `/seasons/{season}/leaders`, `/leaders`, sau đó các endpoint ESPN Site/Web có thể cung cấp cùng nhóm dữ liệu. Định dạng của ESPN có thể thay đổi. Các endpoint này **không phải API hỗ trợ chính thức**. Nếu JSON của ESPN trả dữ liệu khác với trang web, Football News chỉ hiển thị giá trị xác thực được.

Để tránh lỗi 404, tốn băng thông và chờ ảnh, bảng thống kê Football News **không tải ảnh cầu thủ**. Tên, câu lạc bộ, bàn thắng và kiến tạo vẫn đến từ ESPN; biểu tượng bóng và giày chuyền bóng được dựng cục bộ bằng SVG.

Season của Premier League 2026–27 dùng `2026`; các giải theo năm lịch có mùa riêng. Giao diện ẩn bảng Top nếu không có cầu thủ hợp lệ.

## Cấu hình Zalo

Mở **Thiết bị & dịch vụ → Football News → Cấu hình**. Chọn nhiều đội trong dropdown (để trống = toàn giải). Nhập tài khoản gửi và ID người nhận dạng **chuỗi** theo README của Zalo Bot; bật Markdown của Zalo Bot để định dạng tin nhắn.

## Chẩn đoán lỗi

Trong `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.football_news: debug
```

Kiểm tra **Cài đặt → Thiết bị & dịch vụ → Football News → Download diagnostics**. Log ghi mã giải, mùa, domain ESPN và loại lỗi, không ghi nội dung Zalo riêng tư. Nếu thấy HTTP 403/429, tránh làm mới liên tục.

## Phát hành GitHub

Cập nhật nhánh `main`, kiểm tra GitHub Actions, tạo tag tương ứng phiên bản `v2026.11.12.7`; workflow tạo Release. Giữ `.gitignore` (file ẩn trong một số ứng dụng), LICENSE và `hacs.json` tại thư mục gốc.

## Giấy phép

Xem file `LICENSE` trong repository. ESPN và các nhãn hiệu bóng đá thuộc chủ sở hữu tương ứng; repository không phải sản phẩm chính thức của ESPN hoặc Home Assistant.


### Khắc phục lần đầu mở sidebar không thấy giải đấu (2026.11.12.3)

Khi Home Assistant vừa phục hồi config entries, trang Football News hiển thị **Đang đồng bộ danh sách giải đấu** thay vì thông báo sai rằng chưa thêm giải. Giao diện tự thử lại. Các dữ liệu ESPN đã tải thành công trước đó được giữ trong phiên trình duyệt và có đánh dấu **dữ liệu lưu tạm** nếu nguồn chưa cập nhật.

Nếu sau khi cập nhật vẫn không có giải đấu, mở **Cài đặt → Thiết bị & dịch vụ → Football News** và tải **diagnostics**, bật tạm `custom_components.football_news: debug` trong `logger`. Không cần xóa/tạo lại các config entry đang hoạt động.

### Khi ESPN chưa trả thống kê cầu thủ

Mục **Cầu thủ nổi bật** giờ hiển thị ngắn gọn lý do từ ESPN và ghi log theo mã giải (ví dụ `eng.1`). Dữ liệu chỉ được tổng hợp khi ESPN trả xếp hạng theo mùa thực sự; nếu nguồn từ chối truy cập, tích hợp không bỏ qua hạn chế truy cập hoặc tạo số liệu giả. Đầu tiên hãy thử **Premier League** rồi tải diagnostics/log để xác minh HTTP 403, 429, 404 hoặc cấu trúc JSON/HTML thay đổi.

### Cache và mở sidebar lần đầu (2026.11.12.6)

- Dữ liệu ESPN công khai được lưu dưới khóa trình duyệt `football_news_snapshot_v2` trong tối đa 6 giờ, với giới hạn dung lượng và số trận/tin mỗi giải. Dữ liệu từ lần tải thành công trước sẽ hiển thị trước khi WebSocket hoàn tất.
- Khi Home Assistant đang nạp config entry hoặc coordinator, một phản hồi ban đầu rỗng **không** xóa cache. Trang tự thử lại; yêu cầu WebSocket bị treo quá 12 giây sẽ báo lỗi rồi thử lại.
- Bảng cầu thủ ESPN có cache riêng `football_news_leaders_v1` trong 6 giờ. Cả hai cache chỉ nhằm cải thiện trải nghiệm, **không** thay đổi tần suất cập nhật dữ liệu trực tiếp của backend.
- Dữ liệu bóng đá lưu tạm có thể đã cũ, nhất là khi trận đang diễn ra. Luôn kiểm tra nhãn **Đang hiển thị dữ liệu lưu tạm** và làm mới khi cần.
- Nếu **chưa từng** tải thành công một lần, hoặc trình duyệt chặn lưu trữ, cache không thể tạo dữ liệu. Khi đó phải kết nối thành công tới Home Assistant/ESPN lần đầu.
