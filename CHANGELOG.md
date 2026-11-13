## 2026.11.13.8 — Sửa ESPN standings và cache bền vững

- Nhận diện bảng xếp hạng ESPN dạng `standings.entries`, `children[].standings`, nhóm lồng nhau; bác bỏ bảng chỉ chứa tên đội hoặc thiếu chỉ số thi đấu.
- Khi endpoint bảng xếp hạng ESPN trả HTTP 200 nhưng nội dung rỗng/không hợp lệ, thử **tối đa một lần** trên endpoint ESPN dự phòng có tham số mùa. Không truy vấn vượt giới hạn HTTP 403/429.
- Không ghi đè bảng xếp hạng hợp lệ bởi phản hồi rỗng hoặc bảng cũ khác mùa. Giữ nguyên thời điểm cập nhật thật và khôi phục từ RAM/`.storage`.
- Loại bỏ bộ giới hạn ghi `.storage` 120 giây áp dụng chung, vì có thể bỏ lỡ dataset mới tải thành công. Dùng cơ chế debounce `Store.async_delay_save` sẵn có để ghi bất đồng bộ.
- Thêm backoff cho endpoint ESPN lỗi, giảm lặp request khi người dùng reload; hạn chế log lặp trong thời gian mất kết nối mà vẫn giữ lỗi đầy đủ trong diagnostics.
- Khi đã có cache, dashboard thông báo sự cố kết nối ngắn gọn thay vì hiển thị traceback hoặc câu lỗi provider thô; khi chưa từng có dữ liệu, vẫn báo lỗi để xử lý.
- Bổ sung kiểm thử cache từng dataset, hồi phục sau restart, ESPN trả metadata, nhóm bảng lồng nhau, sai mùa, rate-limit và đồng bộ một lần.
- **Không đổi nguồn bóng đá** (vẫn ESPN), thông báo Zalo, giao diện Stadium Night hoặc cấu hình đội yêu thích.

## 2026.11.13.7 — Đồng nhất thẻ Tổng quan và logo giải đấu

- Căn giữa Trận tiếp theo và Kết quả gần nhất theo chiều cao thẻ.
- Dùng chung bộ dựng hàng Top cầu thủ cho Tổng quan và Cầu thủ nổi bật.
- Đặt huy hiệu Champions League trên nền sáng và sửa căn giữa logo bằng CSS Grid.
- Giới hạn kích thước, khoảng cách thẻ cho màn hình hẹp; không thêm API hoặc thư viện.

## 2026.11.13.6
- Hide redundant visible dropdown labels while preserving accessible names.
- Use high-contrast ESPN league crest surfaces.
- Match player club crests from existing same-league ESPN standings/fixtures/roster or the leader record; highlight ranks 1-3.
- Add cross-league logo safety, missing-image fallback and layout regression tests.

## 2026.11.13.5
- Thay ký tự viết tắt trên banner bằng logo giải chính thức lấy từ ESPN.
- Danh mục 25 giải và bộ xem trước sử dụng logo CDN có kiểm chứng, tự đọc metadata ESPN khi chưa xác minh được URL tĩnh.
- SVG bóng đá trung tính khi không có ảnh, không gán logo sai giải.
- Không thay ESPN API, Zalo hoặc cache; chỉ bổ sung ảnh CDN cho giải được chọn.

# Lịch sử Football News

## 2026.11.13.4 — Stadium Night: Thiết kế lại toàn bộ giao diện

- Thay cấu trúc frontend: thanh điều hướng dạng rail trên desktop, toolbar mới và một header sân vận động chứa cả bộ chọn nội dung/giải/giao diện (không còn chỉ thêm banner vào giao diện cũ).
- Thiết kế lại toàn bộ thẻ trận đấu, bảng xếp hạng, bảng Top cầu thủ, khối tin tức và các ô Tổng quan theo hệ thống nền tối có độ tương phản cao.
- Bổ sung 5 hình nền sân vận động SVG nội bộ khác nhau theo màu sắc giải; tự chuyển skin khi đổi giải hoặc chọn thủ công; không tải ảnh nền lớn.
- Căn giữa số liệu và tiêu đề bảng xếp hạng; menu rail đáp ứng bằng data-tab cũ để giữ luồng điều hướng.
- Thử giao diện 280–1920 px và 5 giải đấu, kiểm tra không tràn trang/chồng lấn tỷ số; giữ backend ESPN, Zalo và cache nguyên trạng.

## 2026.11.13.3 — Stadium Editions

- Năm bộ màu giao diện có thể chọn trực tiếp, mặc định tự đổi theo giải đấu.
- Nền vector sân vận động lưu trong tích hợp, không tăng truy vấn ESPN.
- Logo đội và tỷ số co giãn theo kích thước thẻ; tối ưu desktop, tablet, điện thoại.
- Căn giữa toàn bộ thống kê số của bảng xếp hạng; tên đội vẫn căn trái.
- Giữ nguyên cache RAM/đĩa, WebSocket, Zalo và nguồn ESPN.

## 2026.11.13.2 — Loại bỏ tiêu đề trùng dropdown

- Không tạo khối tiêu đề trang trùng dropdown trên Kết quả, Bảng xếp hạng, Tin tức, Trực tiếp.
- Giữ nội dung bảng và danh sách hiển thị trực tiếp, căn lề responsive trên desktop/mobile.
- Tiêu đề thẻ Tổng quan đổi thành "Bảng xếp hạng" (vẫn hiển thị Top 4).
- Tăng phiên bản frontend để bỏ cache JavaScript cũ.

## 2026.11.13.1 — Khôi phục cache ngay lần đầu mở sidebar

- Sửa gốc lỗi **config entry đã tồn tại nhưng coordinator chưa khởi tạo**: WebSocket đọc snapshot `.storage` trực tiếp theo entry, giải, mùa, không phải chờ runtime.
- Khôi phục cache coordinator bằng background task sớm hơn, trước khi chờ platform setup và không gọi ESPN ở bước này.
- Ghép cache theo từng dataset; dữ liệu ESPN mới không bị cache cũ ghi đè.
- Thử lại liên tục có giới hạn thời gian chờ, không dừng sau sáu lần; tải cầu thủ/đội bóng độc lập với lần tải dashboard chính.
- Giảm độ trễ ghi Store xuống 2 giây; giữ chính sách hạn chế ghi thường kỳ và cảnh báo dữ liệu tạm.
- Bổ sung kiểm thử WebSocket trực tiếp, trường hợp runtime chưa tạo, dữ liệu từng phần và thử lại frontend.


## 2026.11.12.9 — Cache bền vững và tương phản tiêu đề

- Bổ sung cache ESPN RAM + `Store` của Home Assistant (`.storage`), tách theo từng config entry và xác minh đúng giải/mùa; không thực hiện I/O ESPN trong quá trình khởi tạo.
- Phục hồi bất đồng bộ lịch, bảng xếp hạng, tin và Top cầu thủ sau khi khởi động lại, giữ thời gian cập nhật nguồn, phân biệt bản lưu tạm và bản mới.
- Giới hạn tuổi và kích thước dữ liệu, không coi trận `live` lưu trên đĩa là đang diễn ra, không ghi nội dung Zalo hoặc cấu hình người dùng vào cache công khai.
- Hạn chế số lần ghi ổ đĩa; xử lý lỗi, dữ liệu sai cấu trúc và ESPN mất kết nối mà không ghi đè cache tốt. Phản hồi rỗng sau dữ liệu tốt cần được xác nhận lần thứ hai.
- Bảo đảm Zalo chỉ nhận các feed trận/tin vừa được cập nhật, không phát lại thông báo dựa trên cache ổ đĩa.
- Tăng độ rõ của tiêu đề, liên kết, các bảng thống kê theo theme; kiểm tra độ tương phản và overflow bằng Chromium.
- Bổ sung kiểm thử Python/JavaScript cho cache khôi phục, bảo vệ tuổi/mùa, dữ liệu từng giải và cảnh báo dữ liệu lưu tạm.


## 2026.11.12.8 — Sửa lỗi Home Assistant gọi cập nhật entity sai luồng

- Sửa listener `football_news_preferences_updated` trong `sensor.py`: thay lambda bằng phương thức có `@callback`, bảo đảm `async_write_ha_state()` chạy trên event loop, không trên executor thread.
- Giữ đúng cơ chế `async_on_remove` để tránh rò rỉ listener khi gỡ hoặc reload config entry.
- Thêm regression test giả lập Home Assistant điều phối listener không đánh dấu qua thread pool, xác nhận không còn `RuntimeError`.
- Không thay đổi giao diện, ESPN, dữ liệu yêu thích hoặc thông báo Zalo.


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

