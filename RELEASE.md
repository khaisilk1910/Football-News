# Quy trình phát hành Football News (ESPN-only)

1. Đưa toàn bộ mã nguồn repository lên nhánh `main`. Không tạo tag khi kiểm thử thất bại.
2. Kiểm tra workflow **Validate Football News** (unit tests, JavaScript, Hassfest, HACS).
3. Tạo tag **v2026.11.12.7** từ commit chính xác, không sửa tag đã phát hành.
4. Workflow **Release Football News** sẽ đính kèm `football_news.zip` vào GitHub Release.
5. Trong Home Assistant 2026.11+, làm mới Marketplace, cập nhật Football News rồi khởi động lại HA.
6. Kiểm tra phiên bản trong dashboard, mở phần cầu thủ nổi bật theo từng giải và xác nhận phản hồi ESPN.

`hacs.json` không yêu cầu `zip_release`: Marketplace có thể cài từ mã nguồn repository. ZIP dành cho cài thủ công và phát hành asset.

Nếu ESPN từ chối truy cập: bật log `custom_components.football_news: debug`, tải diagnostics và kiểm tra mã HTTP / mùa / giải. Không gọi API nhiều lần để vượt HTTP 403/429.

Bản nâng cấp này tự dọn các tùy chọn nhà cung cấp bóng đá cũ trong config entry; cấu hình Zalo và đội yêu thích được giữ lại.
