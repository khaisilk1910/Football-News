# Quy trình phát hành Football News (ESPN-only)

1. Đưa toàn bộ mã nguồn repository lên nhánh `main`. Không tạo tag khi kiểm thử thất bại.
2. Kiểm tra workflow **Validate Football News** (unit tests, JavaScript, Hassfest, HACS).
3. Tạo tag **v2026.11.13.8** từ commit chính xác, không sửa tag đã phát hành.
4. Workflow **Release Football News** sẽ đính kèm `football_news.zip` vào GitHub Release.
5. Trong Home Assistant 2026.11+, làm mới Marketplace, cập nhật Football News rồi khởi động lại HA.
6. Kiểm tra phiên bản trong dashboard, mở phần cầu thủ nổi bật theo từng giải và xác nhận phản hồi ESPN.

`hacs.json` không yêu cầu `zip_release`: Marketplace có thể cài từ mã nguồn repository. ZIP dành cho cài thủ công và phát hành asset.

Nếu ESPN từ chối truy cập: bật log `custom_components.football_news: debug`, tải diagnostics và kiểm tra mã HTTP / mùa / giải. Không gọi API nhiều lần để vượt HTTP 403/429.

Bản nâng cấp này tự dọn các tùy chọn nhà cung cấp bóng đá cũ trong config entry; cấu hình Zalo và đội yêu thích được giữ lại.

## Kiểm chứng cache sau nâng cấp 2026.11.13.8

- Đợi ESPN tải thành công ít nhất một lần và chờ vài giây để `Store.async_delay_save` ghi lên ổ đĩa. Khi mở lại sidebar, dữ liệu hợp lệ trong `.storage` hiển thị trước; ESPN đồng bộ bất đồng bộ sau.
- Nếu bảng xếp hạng ESPN trả JSON rỗng / HTTP 200 nhưng không có bảng, bản này chỉ giữ snapshot tốt trước đó và ghi warning có giới hạn; không ghi bản rỗng vào cache.
- Nếu cả ESPN chính và dự phòng đều lỗi, không thể đảm bảo có dữ liệu mới; xem diagnostics và nhật ký để kiểm tra kết nối, không xóa cache cũ.

## Kiểm chứng cache sau nâng cấp 2026.11.13.1

- Sau khi mở Football News và tải dữ liệu thành công, chờ bản ghi cache được lưu (ghi có trì hoãn), sau đó khởi động lại Home Assistant.
- Mở Football News một lần; dữ liệu ESPN được khôi phục từ `.storage` trước khi hoàn tất cập nhật mạng, với nhãn tạm và thời điểm ESPN đã trả dữ liệu.
- Kiểm tra `disk_cache.restored_datasets` trong Download diagnostics; không coi cache cũ là số liệu trực tiếp.
- Màu giao diện kế thừa theme sáng/tối và giữ nút mở menu/điều hướng đã có.
- Nếu số liệu thực chưa từng được ESPN tải thành công, cache không tạo ra thông tin mới. Không xóa/tạo lại config entry hoặc đội yêu thích.
