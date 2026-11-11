# Đối chiếu tính năng Football News với Football Hub 0.8.19

> Đây là bảng **đối chiếu chức năng**, không phải bản sao mã nguồn Football Hub. Football Hub thuộc Adrian Apel và có giấy phép cấm đổi thương hiệu/tái phân phối nếu chưa được cấp phép bằng văn bản. Football News triển khai độc lập, không bao gồm mã nguồn, tệp giao diện, logo hoặc âm thanh gốc.

## Tình trạng trong bản 2026.11.11.4

| Nhóm | Có trong Football News | Giới hạn đang tồn tại |
|---|---|---|
| Trung tâm nhiều giải | Tổng hợp lịch, trận live, kết quả và tin của **các giải đã thêm vào Home Assistant**; lọc từng giải | Không tự tải toàn bộ thế giới: chỉ tải giải đã cấu hình để bảo vệ hiệu năng |
| Danh mục giải/cúp | 25 mã cấu hình, trong đó có giải quốc nội, cúp và giải quốc tế | Mã ESPN mở rộng **chưa được kiểm chứng toàn bộ**; từng giải có thể không có dữ liệu |
| Lịch thi đấu và kết quả | Khoảng thời gian gần hiện tại, truy vấn lịch theo tháng khi người dùng yêu cầu | Chưa có lịch mùa đầy đủ dạng phân trang tự động |
| Chi tiết trận | Diễn biến, thống kê, sân, khán giả, trọng tài, thời tiết, đội hình nếu nguồn cung cấp | Không tự tổng hợp thẻ phạt, kiến tạo, thay người khi không có bản ghi nguồn |
| Cầu thủ | Truy vấn roster câu lạc bộ, danh sách dẫn đầu khi nguồn hỗ trợ | Chưa bảo đảm được danh sách cầu thủ ghi bàn/kiến tạo cho tất cả giải |
| My Club | Theo dõi tối đa 5 đội, giữ mã giải sân nhà, lịch và vị trí từ dữ liệu đã nạp; xem roster theo yêu cầu | Chưa có các bảng riêng injuries, suspensions, transfers, records, trophies; chưa tạo đầy đủ thiết bị/cảm biến riêng cho từng đội |
| Live alerts | Zalo: trước trận, bắt đầu, cập nhật bàn thắng/tỷ số, kết quả, tin mới; theo trận đã đánh dấu | Không có âm thanh kickoff/thẻ phạt trong trình duyệt; chỉ gửi các thay đổi phát hiện khi HA đang chạy |
| TV/Watch | Có link bài/trận từ ESPN khi họ cung cấp; mở nguồn bằng HTTPS | **Không tích hợp Sports Streams/Stremio**, không phân phối URL stream, không xác nhận bản quyền phát sóng |
| Ngôn ngữ | Giao diện tiếng Việt và tiếng Anh, action/cấu hình Việt hóa | Tên riêng và bài tin từ ESPN được giữ nguyên, không dịch máy |
| Zalo | Sử dụng `zalo_bot.send_message`, Markdown rich text, ID lớn dạng chuỗi | Cần cài `zalo_bot` riêng; giới hạn API và quyền nhóm tùy Zalo Bot Server |
| HA/Marketplace | Config flow, options, entities, diagnostics, service responses, cấu trúc source-based, kiểm thử tự động | Chưa được xác thực end-to-end trên Home Assistant thực tế hoặc kiểm tra toàn bộ mã giải đấu |

## Dữ liệu và độ chính xác

- Không biến tỷ số chưa biết thành 0–0 và không suy diễn thông tin vắng mặt.
- Trận và tin được tải từ các endpoint ESPN công khai, **không chính thức**, có thể ngừng cung cấp hoặc thay đổi định dạng.
- Dữ liệu hiển thị nguồn, trạng thái, thời điểm cập nhật; cache và log lỗi để có thể chẩn đoán.
- Các endpoint roster/leader có khả năng khác nhau giữa từng giải; thất bại trả trạng thái không có dữ liệu.
- Football News không nhận/mặc định đã tiếp nhận database, config entry hoặc dữ liệu cá nhân từ Football Hub.

## Hướng phát triển để đạt đủ mức chức năng mong muốn

1. Bổ sung các nguồn được phép sử dụng cho lịch mùa, chuyển nhượng, chấn thương, danh hiệu, bảng TV và stats nếu API đáp ứng.
2. Tạo cảm biến và thiết bị riêng cho mỗi câu lạc bộ; quản lý xóa entity khi bỏ theo dõi.
3. Bổ sung âm báo trình duyệt do chính dự án tạo, tinh chỉnh thông báo theo bàn thắng/thẻ phạt mà không gọi quá nhiều API.
4. Chạy kiểm thử trên Home Assistant 2026.11+ thực, kiểm tra dữ liệu thật từng giải và các luồng Marketplace/Release.

Không gắn nhãn “đầy đủ tính năng Football Hub” trước khi các mục còn thiếu đã được triển khai và xác nhận.
