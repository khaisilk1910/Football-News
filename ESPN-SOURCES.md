# Nguồn thống kê Football News — ESPN

**Phiên bản:** `2026.11.12.3`  
**Nguồn dữ liệu bóng đá duy nhất:** ESPN. Không yêu cầu API key.

## Nguồn dữ liệu

| Thông tin | Nguồn ESPN được gọi | Thời điểm |
|---|---|---|
| Lịch / kết quả | `site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard` | Đồng bộ sau khi HA khởi động, theo TTL |
| Bảng xếp hạng | `site.api.espn.com/apis/v2/sports/soccer/{league}/standings` | Theo TTL |
| Đội / cầu thủ CLB | `site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams` và `teams/{id}/roster` | Khi mở trang cần |
| Tin tức | `site.api.espn.com/apis/site/v2/sports/soccer/{league}/news` | Theo TTL |
| Thống kê cầu thủ theo mùa | `sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/seasons/{season}/types/2/leaders` | Khi xem Tổng quan/Cầu thủ, cache 6 giờ |
| Dự phòng thống kê | ESPN Core `seasons/{season}/leaders`, `leaders`, ESPN Site API `leaders` | Khi thiếu nhóm |
| Trang thống kê ESPN | `https://www.espn.com/soccer/stats/_/league/{league}/season/{season}` | Chỉ đọc bảng HTML công khai khi ESPN cho phép truy cập bình thường |

## Thống kê hỗ trợ

Bàn thắng, kiến tạo, thẻ vàng, thẻ đỏ, điểm đánh giá, số trận và số phút thi đấu. Chỉ tạo một hàng khi ESPN cung cấp rõ **tên cầu thủ**, **tên thống kê** và **giá trị hợp lệ**. Không tính Top toàn giải từ một số trận hoặc một mẫu cầu thủ thiếu. Bảng thiếu số liệu được ẩn; không tự tạo kết quả.

`season=2026` dùng cho Premier League 2026–27. Với giải theo năm dương lịch, mùa giải bằng năm hiện tại. Kết quả thực tế tùy vào dữ liệu ESPN công bố cho từng giải.

## Giới hạn truy cập

- Các endpoint JSON ESPN công khai này là **không chính thức** và có thể thay đổi bất cứ lúc nào.
- Trang `www.espn.com` có thể yêu cầu JavaScript/xác minh trình duyệt hoặc hạn chế bot. Bản tích hợp **không vượt qua** yêu cầu đó; khi bị chặn sẽ báo thiếu nguồn.
- Không dùng token/API key của bên thứ ba. Không lấy dữ liệu từ bất kỳ tích hợp Home Assistant nào khác.
- Tối đa 4 yêu cầu mạng cùng lúc; không tải thống kê cầu thủ lúc Home Assistant khởi động.
- Khi nhận HTTP 403/429, dừng vòng thử thay vì liên tục gọi lại. Lỗi sẽ ghi domain, mã giải, mùa và loại lỗi.

## Kiểm tra và báo lỗi

1. Bật `logger: {logs: {custom_components.football_news: debug}}` trong cấu hình HA.
2. Khởi động lại HA, mở trang **Cầu thủ nổi bật** và chọn giải.
3. Kiểm tra log theo cụm `ESPN leaders league=... season=...` hoặc `ESPN leaders unavailable`.
4. Kiểm tra `Cài đặt → Thiết bị & dịch vụ → Football News → Download diagnostics`.
5. So sánh trên https://www.espn.com/soccer/stats/_/league/eng.1; nếu trang web có thống kê nhưng JSON trên mạng HA không trả dữ liệu, gửi phần log đã xóa thông tin cá nhân để xác định sự khác biệt.

Không có quyền truy cập mạng của Home Assistant trong bộ kiểm thử này; các test dùng phản hồi mô phỏng và không chứng minh ESPN đang cho phép máy chủ của bạn truy cập.


### Giới hạn của kiểm thử 2026.11.12.3

ESPN không cung cấp API nhà phát triển chính thức cho các bảng cầu thủ bóng đá. Bộ đọc hiện dùng ESPN Core mùa giải, ESPN Site và các bảng HTML công khai, với xử lý tham chiếu có giới hạn số yêu cầu. Kết quả kiểm thử tự động sử dụng JSON/HTML mẫu; không thay thế được xác nhận kết nối trực tiếp từ Home Assistant của người dùng. Khi ESPN chặn truy cập (403/429), tích hợp dừng và báo lỗi thay vì cố vượt rào.


## Ảnh cầu thủ (2026.11.12.4)

Football News ưu tiên trường `headshot.href` hoặc URL ảnh do ESPN trả về; nếu thiếu nhưng có ESPN athlete ID dạng số, frontend sẽ dùng URL công khai `https://a.espncdn.com/i/headshots/soccer/players/full/<id>.png`. Đối với bảng thống kê HTML, ESPN player ID được lấy từ đường dẫn hồ sơ `/soccer/player/_/id/<id>/...`. Không suy đoán ID từ tên cầu thủ. Ảnh thiếu/404 hiển thị placeholder. Các ảnh tải trực tiếp từ ESPN CDN và không được gói vào repository.
