

## Tình trạng trong bản 2026.11.12.7

**Nguồn bóng đá duy nhất: ESPN**. Bộ cấu hình không còn khóa API hoặc cầu nối dữ liệu khác. Các bảng cầu thủ được truy vấn theo mùa khi mở trang; HTML chính thức chỉ được đọc khi ESPN cho phép truy cập bình thường.


| Nhóm | Có trong Football News | Giới hạn đang tồn tại |
|---|---|---|
| Tổng quan tóm tắt | Trận kế tiếp, bảng top 4, kết quả gần nhất, phong độ thật của CLB yêu thích, vua phá lưới và 3 trận tới; nhấn Xem tất cả để vào mục chi tiết; ẩn thẻ thiếu dữ liệu | Phong độ chỉ tính từ trận đã kết thúc trong khoảng lịch có dữ liệu; chỉ hiện cầu thủ khi nguồn cho số liệu |
| Trung tâm nhiều giải | Tổng hợp lịch, trận live, kết quả và tin của **các giải đã thêm vào Home Assistant**; lọc từng giải | Không tự tải toàn bộ thế giới: chỉ tải giải đã cấu hình để bảo vệ hiệu năng |
| Danh mục giải/cúp | 25 mã cấu hình, trong đó có giải quốc nội, cúp và giải quốc tế | Mã ESPN mở rộng **chưa được kiểm chứng toàn bộ**; từng giải có thể không có dữ liệu |
| Lịch thi đấu và kết quả | 14 ngày gần đây và 35 ngày sắp tới, truy vấn theo các tháng `YYYYMM`; xem lịch tháng của giải đang chọn khi yêu cầu | Bộ lọc tháng có thể gặp hạn chế của ESPN ở một số giải; không gộp lịch nhiều giải trong một yêu cầu |
| Chi tiết trận | Diễn biến, thống kê, sân, khán giả, trọng tài, thời tiết, đội hình nếu nguồn cung cấp | Không tự tổng hợp thẻ phạt, kiến tạo, thay người khi không có bản ghi nguồn |
| My Club | Theo dõi tối đa 5 đội; thẻ logo/tên/sân nhà/năm thành lập khi có; thêm/bỏ yêu thích có xác nhận lưu HA Store; popup thông tin đội/roster theo yêu cầu | Chưa có các bảng riêng injuries, suspensions, transfers, records, trophies; chưa tạo đầy đủ thiết bị/cảm biến riêng cho từng đội |
| Live alerts | Zalo: trước trận, bắt đầu, cập nhật bàn thắng/tỷ số, kết quả, tin mới; theo trận đã đánh dấu | Không có âm thanh kickoff/thẻ phạt trong trình duyệt; chỉ gửi các thay đổi phát hiện khi HA đang chạy |
| TV/Watch | Có link bài/trận từ ESPN khi họ cung cấp; mở nguồn bằng HTTPS | **Không tích hợp Sports Streams/Stremio**, không phân phối URL stream, không xác nhận bản quyền phát sóng |
| Ngôn ngữ | Giao diện tiếng Việt/Anh, hai dropdown sử dụng biến theme Home Assistant; giữ trạng thái tab/giải và snapshot dữ liệu công khai (tối đa 6 giờ) xuyên phiên trình duyệt | Tên riêng và bài tin từ ESPN được giữ nguyên, không dịch máy |
| Zalo | Sử dụng `zalo_bot.send_message`, Markdown rich text, ID lớn dạng chuỗi | Cần cài `zalo_bot` riêng; giới hạn API và quyền nhóm tùy Zalo Bot Server |
| HA/Marketplace | Config flow, options, entities, diagnostics, service responses, nút tạo nhanh 6 config entry; WebSocket Probatio 2026 và giao diện ẩn mục không có dữ liệu | Chưa được xác thực end-to-end trên Home Assistant thực tế hoặc kiểm tra toàn bộ mã giải đấu |

## Dữ liệu và độ chính xác

- Không biến tỷ số chưa biết thành 0–0 và không suy diễn thông tin vắng mặt.
- Trận và tin được tải từ các endpoint ESPN công khai, **không chính thức**, có thể ngừng cung cấp hoặc thay đổi định dạng.
- Dữ liệu hiển thị nguồn, trạng thái, thời điểm cập nhật; cache và log lỗi để có thể chẩn đoán.
- Các endpoint roster/leader có khả năng khác nhau giữa từng giải; thất bại trả trạng thái không có dữ liệu.

## Hướng phát triển để đạt đủ mức chức năng mong muốn

1. Bổ sung các nguồn được phép sử dụng cho lịch mùa, chuyển nhượng, chấn thương, danh hiệu, bảng TV và stats nếu API đáp ứng.
2. Tạo cảm biến và thiết bị riêng cho mỗi câu lạc bộ; quản lý xóa entity khi bỏ theo dõi.
3. Bổ sung âm báo trình duyệt do chính dự án tạo, tinh chỉnh thông báo theo bàn thắng/thẻ phạt mà không gọi quá nhiều API.
4. Chạy kiểm thử trên Home Assistant 2026.11+ thực, kiểm tra dữ liệu thật từng giải và các luồng Marketplace/Release.


### Cập nhật 2026.11.11.11

Điều hướng lịch theo vòng nếu ESPN cung cấp `round`; nếu không có, nhóm theo tuần có ghi rõ là đợt ngày. Có lọc đội bóng theo tên. Vua phá lưới phụ thuộc endpoint ESPN, không bảo đảm có dữ liệu mọi giải. Không còn dropdown “Mọi giải đã cài”.


### Cập nhật 2026.11.11.12

- Đã kiểm thử giao diện thẻ CLB trên 10 tổ hợp màn hình/theme, tránh tên đội bị xuống từng ký tự.
- Bổ sung `club_brief` để chỉ tải metadata nhẹ khi mở trang đội yêu thích; popup đội tải roster riêng khi người dùng nhấn Chi tiết.
- Popup trận có tỷ số, các sự kiện theo phút với biểu tượng, thống kê và đội hình. Số liệu chỉ được lấy từ ESPN, không bịa thêm.
- Dữ liệu vua phá lưới phụ thuộc ESPN Web/Core; không bảo đảm hỗ trợ từng giải. Không có dữ liệu thì ẩn khối.

### Cập nhật 2026.11.11.13

- Zalo: lựa chọn nhiều đội theo ID từ danh sách từng giải trong Options Flow; tải khi mở cấu hình, không tải ở startup; bộ lọc tin trận tách biệt với lọc tin cấp giải.
- Ô tìm tên đội có gợi ý tương tác; chọn tên đưa đến đợt/vòng phù hợp trong lịch hiện có.
- Vòng hiển thị **N/T** khi ESPN có `round`/`matchday`/`week` chính thức. Đợt ngày là phương án trung thực khi nguồn không có vòng.
- Lấy cầu thủ theo mùa từ năm hiện tại qua ESPN Web và các endpoint Core hạn chế; mở rộng đọc `statistics/splits/categories`. Không khẳng định đã có dữ liệu nếu ESPN không cung cấp.
- Bảng xếp hạng tô vùng màu theo quy tắc giải quốc nội đã biết (C1 cơ bản, nhóm xuống hạng, play-off); hiển thị chú giải và ghi rõ là tạm thời, không đoán thêm suất UEFA.

### Cập nhật 2026.11.12.2

- Bảng cầu thủ của Football News hiển thị các nhóm chỉ khi có dữ liệu thực. Top 3 bàn thắng trên Tổng quan vẫn phụ thuộc nguồn hợp lệ.
- Dữ liệu này chỉ được yêu cầu khi người dùng mở trang. Quy trình khởi động Home Assistant không gọi endpoint cầu thủ.

### Cập nhật 2026.11.12.6

- Tổng quan: Top 3 ghi bàn/kiến tạo, biểu tượng bóng/giày vàng–bạc–đồng. Cầu thủ nổi bật: tối đa Top 15 cho mỗi loại nếu ESPN cung cấp đủ dữ liệu. Không tải ảnh cầu thủ.
- Cache trình duyệt (localStorage) và bộ nhớ module giữ dữ liệu bóng đá công khai qua lần mở sidebar khác, reload và tab mới; hồi phục khi WebSocket/coordinator tạm chưa sẵn sàng, không ghi thông tin Zalo cá nhân.
- ESPN vẫn là nguồn bóng đá duy nhất, không gọi thêm dịch vụ ảnh chân dung.

### Cập nhật 2026.11.12.7

- Cầu thủ nổi bật: hai bảng bàn thắng và kiến tạo cùng hàng khi vùng panel rộng; xếp dọc trên điện thoại.
- Biểu tượng SVG bóng đá/giày chuyền bóng mới, nội bộ, không cần ảnh chân dung hoặc thêm request mạng.
