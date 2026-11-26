# Quy trình phát hành Football News (ESPN-only)

1. Đưa toàn bộ mã nguồn repository lên nhánh `main`. Không tạo tag khi kiểm thử thất bại.
2. Kiểm tra workflow **Validate Football News** (unit tests, JavaScript, Hassfest, HACS).
3. Tạo tag **v2026.11.21.5** từ commit chính xác, không sửa tag đã phát hành.
4. Workflow **Release Football News** sẽ đính kèm `football_news.zip` vào GitHub Release.
5. Trong Home Assistant 2026.11+, làm mới Marketplace, cập nhật Football News rồi khởi động lại HA.
6. Kiểm tra phiên bản trong dashboard, mở phần cầu thủ nổi bật theo từng giải và xác nhận phản hồi ESPN.

`hacs.json` không yêu cầu `zip_release`: Marketplace có thể cài từ mã nguồn repository. ZIP dành cho cài thủ công và phát hành asset.

Nếu ESPN từ chối truy cập: bật log `custom_components.football_news: debug`, tải diagnostics và kiểm tra mã HTTP / mùa / giải. Không gọi API nhiều lần để vượt HTTP 403/429.

Bản nâng cấp này tự dọn các tùy chọn nhà cung cấp bóng đá cũ trong config entry; cấu hình Zalo và đội yêu thích được giữ lại.

## Kiểm chứng đồng bộ nhiều thiết bị sau nâng cấp 2026.11.19.1

- Mở cùng một tài khoản HA trên máy tính và điện thoại. Chọn tab/giải/bộ màu trên thiết bị A; thiết bị B cần hiển thị lựa chọn tương ứng sau sự kiện WebSocket hoặc một lần tải lại. Không cần và không được phụ thuộc localStorage.
- Đánh dấu CLB/trận trên thiết bị A bằng tài khoản quản trị; tất cả thiết bị đọc cùng danh sách yêu thích từ HA Store.
- Bấm làm mới, kiểm tra dữ liệu ESPN cập nhật đồng nhất cho các máy; ngắt ESPN hoặc restart HA để xác minh fallback từ `.storage`, không hiển thị tỷ số live chưa xác minh.
- Cùng một tài khoản ở các thiết bị dùng chung trạng thái UI; **khác tài khoản** được giữ tab/giải/bộ màu riêng, nhưng cùng dữ liệu ESPN và yêu thích.
- Đọc diagnostics của từng config entry: `persistence`, `dataset_counts`, `last_successful_updates`, `disk_cache`, `errors`. Bật `custom_components.football_news: debug` khi cần.
- Các kiểm thử tự động chỉ mô phỏng HA Store/WebSocket; hãy kiểm tra thực tế với Home Assistant trước khi phát hành công khai.

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

## Kiem tra popup Live ban 2026.11.19.4

- Mo Football News tren 2 thiet bi, bat ky tab nao. Trong khi tran ESPN dang Live, cho mot ban thang/the vang/the do moi. Ca hai thiet bi dang mo Football News phai nhan mot popup, voi logo hai doi, ty so va cau thu/phut neu ESPN co du lieu.
- Chuyen tab/giai dau trong Football News: popup moi van xuat hien. Bam Xem dien bien de mo chi tiet tran; bam X de dong popup.
- Khoi dong lai HA: khong duoc thong bao lap lai hang loat su kien da co tu truoc. Khong co Live thi khong truy van timeline nen.
- Neu ESPN khong tra keyEvents/scoringPlays thi khong du doan ban thang hay cau thu. Bật DEBUG custom_components.football_news de xem logger, hoac kiem tra endpoint ESPN.
- Kiem thu tu dong la mo phong, can xac nhan bang tran Live va HA that truoc khi phat hanh chinh thuc.

## Kiểm tra tải dữ liệu lần đầu (2026.11.20.1)

- Không xóa `.storage` và không gỡ cấu hình giải đấu. Mở Football News **một lần** sau restart, kiểm tra bảng xếp hạng/lịch lấy từ cache dù ESPN chưa kịp cập nhật.
- Nếu mobile WebView báo `document.hidden`, trình duyệt phải tiếp tục hỏi WebSocket Home Assistant khi chưa có lịch/bảng. Không cần đổi tab để kích hoạt.
- Xem log tại Settings → System → Logs, thêm `custom_components.football_news: debug` nếu cần. Log `HA Store first-view cache` chứng minh snapshot đã lưu được đọc.
- Nếu backend báo `has no valid snapshot`, chưa có cache hợp lệ hoặc cache bị loại do sai giải, mùa, tuổi, cấu trúc; kiểm tra diagnostics. Không bịa dữ liệu khi HA chưa lưu.

## Kiểm tra bản sửa mở lần đầu và reload (2026.11.20.2)

1. Sao lưu `/config/custom_components/football_news/` và **không xóa** `/config/.storage/`. Chép mã nguồn bản mới rồi khởi động lại Home Assistant một lần để tích hợp ghi chỉ mục `football_news_league_registry`.
2. Xác nhận đã có giải đấu cấu hình trong Settings → Devices & services → Football News; đợi bản ESPN hợp lệ được lưu (nếu cache chưa từng có).
3. Mở Football News, bấm reload trang và mở từ một thiết bị khác. Kiểm tra lịch/bảng lấy từ HA Store; không được xuất hiện popup “Không thể lưu” chỉ vì vừa vào trang.
4. Kiểm tra log `Football News durable league registry recorded`, `config-entry registry incomplete`, `Football News HA Store first-view cache`. Khi xuất diagnostics, kiểm tra `ha_registry` và `dataset_counts`.
5. Nếu vẫn trống, bật log `custom_components.football_news: debug` và lấy đoạn log thời điểm mở trang cùng diagnostics. Cần phân biệt không có config entry, cache chưa hợp lệ, lỗi Store, và lỗi WebSocket; không thể xác minh máy chủ của bạn từ mã nguồn đơn lẻ.

## Kiểm tra 2026.11.20.4 (F5, Live, popup)

1. Mở Football News khi Home Assistant đã có dữ liệu; dùng F5/Ctrl+R và xác nhận trang Tổng quan lấy lại trận/bảng từ HA Store mà không cần rời trang. Test WebSocket kiểm tra coordinator đã khôi phục sẽ không bị đọc Store thêm lần nữa.
2. Vào trang Live khi không có trận; nếu feed trận đã phản hồi, phải xuất hiện “Hiện không có trận đấu trực tiếp”, không quay spinner vô hạn.
3. Tạo thông báo test, chờ **20 giây** mà không nhấn X; phải tự ẩn. Render lại cùng một lỗi không được kéo dài thời hạn. Popup bàn thắng/thẻ phạt cũng 20 giây.
4. Các kiểm thử Chromium/Node/Python dùng HA WebSocket mô phỏng. Nếu Home Assistant đang chạy không có snapshot hợp lệ, vui lòng cung cấp log/diagnostics, không tự ý xóa `.storage`.

## Kiểm tra nâng cấp 2026.11.20.3 (cơ chế cứu cache)

1. Đảm bảo các file của `custom_components/football_news` được chép từ **cùng một** bản ZIP và khởi động lại HA; frontend không khớp backend sẽ ghi cảnh báo.
2. Mở Football News, quan sát trạng thái Backend và số giải/cache hợp lệ; nếu có dữ liệu `.storage` cũ nhưng config entry không tồn tại, thông tin chỉ ở chế độ đọc.
3. Bật `logger.logs.custom_components.football_news: debug`, lấy diagnostics trên integration nếu không xuất hiện giải; log giới hạn mỗi 60 giây phân biệt thiếu HA config entries với cache trống. Không xóa `.storage` khi chưa sao lưu.
4. Chỉ sau khi HA đã tải dữ liệu ESPN mới qua cấu hình active mới kiểm tra cập nhật Live và popup. Dữ liệu khôi phục từ Store không chứng minh trận đang Live.


## Kiểm tra 2026.11.21.1 (lần đầu vào HA, reload, Android Companion)

1. Cập nhật toàn bộ thư mục `custom_components/football_news` và restart Home Assistant. KHÔNG xóa `.storage` hay config entry.
2. Đợi HA hoàn tất khởi động; vào Football News trong Android Companion, trình duyệt máy tính, sau đó reload/F5. Đối với giải có RAM cache, lịch/bảng hiển thị từ WebSocket nhanh trước; bản Store/tùy chọn tài khoản hoàn thiện sau.
3. Nếu chưa có RAM cache (đang setup entry), trang tiếp tục đọc cache HA Store; không cần rời Football News. Không thể hiển thị lịch chưa từng được ESPN trả và lưu.
4. Nếu vẫn còn `Backend: chưa phản hồi`, bật `logger.logs.custom_components.football_news: debug` và chụp log sau khi vào trang. Phân biệt lỗi đăng ký WebSocket, mất kết nối HA Companion, hay HA Store/cache rỗng.
5. Kiểm tra `/config/.storage/football_news_cache_*` tồn tại (chỉ kiểm tra tên; không sửa tay). Các kiểm thử Python/JS là mô phỏng, không thay thế thử trên hệ thống HA thực.

## Kiểm tra 2026.11.21.2 — cache trước và ESPN sau 120 giây

1. Với HA Store đã có dữ liệu: vừa mở Football News hoặc reload, lịch thi đấu/bảng xếp hạng phải hiện từ RAM hoặc `.storage` mà không phải đợi ESPN hay thoát ra.
2. Khi HA khởi động hoặc vừa tạo config entry, log `Football News cache-first window` cho biết số giây còn lại; lần truy cập đầu không được kéo dài lịch ESPN bằng các lần reload.
3. Với bản cài mới chưa có snapshot: thông báo “Chưa có dữ liệu đã lưu trên Home Assistant” và đồng hồ chờ ESPN sẽ xuất hiện; đợi ít nhất hai phút để ESPN cập nhật tự động.
4. Nếu vẫn trống khi backend báo cache `available`, bật `custom_components.football_news: debug` và cung cấp log thời điểm truy cập và diagnostics; có thể là lỗi WebSocket/quyền truy cập. Không xóa `.storage`.
