# Lịch sử cập nhật Football News

## 2026.11.11.4 — Sửa dashboard và nguồn lịch thi đấu

- Đăng ký trang Football News bằng API `panel_custom` của Home Assistant và khai báo dependency tương ứng.
- Giao diện vẫn hiển thị trang và gợi ý khắc phục khi WebSocket hoặc quá trình dựng nội dung bị lỗi.
- Fallback truy vấn scoreboard ESPN một lần khi không dùng được khoảng ngày; bổ sung thông báo lỗi và log rõ ràng.
- Lược bỏ hoàn toàn các tính năng quản lý giải phụ không thuộc mục tiêu xem bóng đá và thông báo.
- Giữ các tính năng lịch thi đấu, kết quả, câu lạc bộ yêu thích, chi tiết trận và Zalo.

## 2026.11.11.3 — Mở rộng chức năng độc lập

- Dashboard đa giải đấu đã cấu hình: lịch, trực tiếp, kết quả, bảng xếp hạng, tin, lịch theo tháng.
- Danh mục 25 mã giải/cúp, cảnh báo rõ giới hạn dữ liệu từ ESPN.
- My Club: tối đa 5 câu lạc bộ, chọn qua ngôi sao, xem danh sách cầu thủ theo yêu cầu.
- Chi tiết trận đọc thêm referee, weather và line-up khi nguồn có thông tin.
- Dữ liệu đội bóng và danh sách cầu thủ dẫn đầu chỉ tải khi người dùng yêu cầu.
- Zalo: thêm tùy chọn thông báo bàn thắng/thay đổi tỷ số, lọc trận được đánh dấu, lưu lịch sử để giảm gửi trùng.
- Thêm bảng đối chiếu tính năng và giới hạn tại `FEATURES.md`, không sao chép tài sản Football Hub.
- 11 bài kiểm thử đơn vị trên lõi dữ liệu và Zalo.

## 2026.11.11.2 — Cài đặt Marketplace từ mã nguồn

- Không bắt buộc GitHub Release ZIP khi cài từ Home Assistant Marketplace.
- Đồng bộ phiên bản ở manifest/const, tăng kiểm tra CI và hướng dẫn phát hành.

## 2026.11.11.1 — README tiếng Việt và nhận diện đỏ-vàng

- Cài nhanh Marketplace, icon Football News, cải thiện giao diện và tài liệu tiếng Việt.
