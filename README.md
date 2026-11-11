<div align="center">

<img src="custom_components/football_news/brand/icon@2x.png" alt="Biểu tượng Football News: bóng đá, Home Assistant và tin tức, tông đỏ vàng" width="150" />

# ⚽ FOOTBALL NEWS

### Lịch thi đấu · Tỷ số trực tiếp · Kết quả · Tin tức bóng đá

**Theo dõi bóng đá ngay trong Home Assistant và nhận thông báo qua Zalo.**

[![Phiên bản](https://img.shields.io/github/v/release/khaisilk1910/Football-News?label=Phi%C3%AAn%20b%E1%BA%A3n&color=c62828)](https://github.com/khaisilk1910/Football-News/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.11%2B-f9a825)](https://www.home-assistant.io/)
[![Kiểm tra mã nguồn](https://github.com/khaisilk1910/Football-News/actions/workflows/validate.yml/badge.svg)](https://github.com/khaisilk1910/Football-News/actions/workflows/validate.yml)
[![Ngôn ngữ](https://img.shields.io/badge/Ng%C3%B4n%20ng%E1%BB%AF-Ti%E1%BA%BFng%20Vi%E1%BB%87t-c62828)](#ng%C3%B4n-ng%E1%BB%AF-v%C3%A0-giao-di%E1%BB%87n)

</div>

<!-- ha-marketplace:exclude-start -->

## 🚀 THÊM NHANH VÀO HOME ASSISTANT MARKETPLACE

<div align="center">

[![Thêm nhanh Football News vào Marketplace](https://img.shields.io/badge/TH%C3%8AM%20NHANH-MARKETPLACE-f9a825?style=for-the-badge&labelColor=b71c1c&logo=homeassistant&logoColor=white)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=khaisilk1910&repository=Football-News&category=integration)

[![Mở repository trong Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=khaisilk1910&repository=Football-News&category=integration)

**[➡️ MỞ FOOTBALL NEWS TRONG MARKETPLACE](https://my.home-assistant.io/redirect/marketplace_repository/?owner=khaisilk1910&repository=Football-News&category=integration)**

</div>

> **Cách dùng:** Nhấn một trong các nút ở trên, chọn máy chủ Home Assistant, chấp nhận thêm repository nếu được hỏi, rồi chọn **Cài đặt (Install)**. Nút mở trang Marketplace, **không tự cài đặt mà bỏ qua xác nhận**. Cần Home Assistant **2026.11 trở lên** và repository đã chứa mã Football News cùng bản phát hành hợp lệ.

### Nếu nút không mở được Marketplace

1. Trong Home Assistant, vào **Cài đặt → Marketplace → Add from link**.
2. Nhập địa chỉ repository: `https://github.com/khaisilk1910/Football-News`.
3. Chọn **Add**; kết nối GitHub nếu được yêu cầu. Nếu cần chọn loại nội dung, chọn **Integration**.
4. Mở **Football News** trong Marketplace và nhấn **Install**.
5. Khởi động lại Home Assistant nếu hệ thống yêu cầu.
6. Vào **Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp → Football News** để hoàn tất thiết lập.

> Marketplace được tích hợp vào Home Assistant 2026.11. Người dùng phiên bản này không cần cài HACS riêng.

<!-- ha-marketplace:exclude-end -->

## 🌟 Football News mang đến những gì?

Football News tập trung vào ba trải nghiệm: **xem bóng đá nhanh**, **nhận thông báo đúng thời điểm** và **quản lý mọi thứ ngay trên Home Assistant**.

| Khu vực | Nội dung |
|:--|:--|
| 🏟️ Trung tâm trận đấu | Lịch thi đấu, trận đang diễn ra, kết quả, tỷ số, giờ thi đấu và sân vận động khi nguồn có dữ liệu |
| 📊 Bảng xếp hạng | Vị trí, số trận, thắng/hòa/thua, hiệu số, điểm số; trang thống kê cầu thủ theo nguồn |
| 📰 Tin tức | Tiêu đề, tóm tắt, thời điểm xuất bản và liên kết đến nguồn bài báo |
| ⭐ Câu lạc bộ yêu thích | Theo dõi tối đa 5 đội, ưu tiên lịch và vị trí bảng; xem đội hình theo yêu cầu |
| 🔔 Thông báo Zalo | Nhắc trước giờ bóng lăn, bắt đầu trận, thay đổi tỷ số/bàn thắng, kết quả và tin mới; có công tắc bật/tắt từng loại |
| 🧩 Home Assistant | Cấu hình bằng giao diện, tạo cảm biến, thực thi action, tải chẩn đoán và theo dõi log |
| ⚡ Hiệu năng | Không gọi API bóng đá hoặc Zalo trong quá trình thiết lập/khởi động; dữ liệu được cập nhật sau khi HA hoạt động |

### Các giải đấu hỗ trợ

- **Anh:** Premier League, EFL Championship.
- **Tây Ban Nha:** LaLiga.
- **Đức:** Bundesliga.
- **Ý:** Serie A.
- **Pháp:** Ligue 1.
- **Hà Lan:** Eredivisie.
- **Bồ Đào Nha:** Primeira Liga.
- **Scotland:** Scottish Premiership.
- **Mỹ:** Major League Soccer (MLS).
- **Châu Âu:** UEFA Champions League, UEFA Europa League, UEFA Conference League.

Ngoài 13 giải ban đầu, phiên bản này bổ sung danh mục: **League One, League Two, FA Cup, EFL Cup, Scottish Championship, League of Ireland, Cymru Premier, Liga MX, Brasileirão, Argentine Primera, UEFA Nations League và FIFA World Cup**. Tổng cộng **25 mã giải đấu/cúp**. Đây là danh sách cấu hình, **chưa phải xác nhận dữ liệu hoạt động ở toàn bộ các giải**; ESPN có thể không cung cấp một số mã hoặc loại thông tin.

Xem **[đối chiếu tính năng và giới hạn hiện tại](FEATURES.md)** trước khi chuyển từ Football Hub sang Football News.

## 🎨 Ngôn ngữ và giao diện

- **Tiếng Việt** cho giao diện, các bước cấu hình, entity và action; có thêm bản dịch tiếng Anh.
- Thiết kế **đỏ đô – đỏ tươi – vàng kim** với biểu tượng kết hợp **quả bóng, Home Assistant và News**.
- Dashboard sử dụng giao diện linh hoạt trên điện thoại, máy tính bảng và máy tính.
- Có **Trung tâm nhiều giải**, **Câu lạc bộ của tôi**, **Lịch theo tháng**, **Cầu thủ nổi bật**. Các dữ liệu bổ sung được truy vấn khi mở mục tương ứng, không tải khi khởi động.
- Các biểu tượng ngôi sao cho phép theo dõi đội và ưu tiên trận; thay đổi yêu cầu quyền quản trị Home Assistant.
- Ngày giờ hiển thị theo múi giờ Home Assistant. Tên câu lạc bộ, giải đấu và tiêu đề báo giữ nguyên từ nguồn để tránh dịch sai tên riêng.

> Football News là dự án cộng đồng độc lập, không phải sản phẩm chính thức của Home Assistant, ESPN hoặc Zalo.

## 🛠️ Thiết lập lần đầu

1. Cài Football News qua Marketplace (hoặc cài thủ công ở phần bên dưới).
2. Mở **Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp**, tìm **Football News**.
3. Chọn giải đấu muốn theo dõi; ví dụ **Premier League**.
4. Vào **Football News → Cấu hình (Configure)** để chọn ngôn ngữ, bộ lọc tên đội bóng và thông báo.
5. Mở mục **Football News** trên thanh bên Home Assistant để xem dashboard.

Không cần tạo tài khoản ESPN hoặc nhập khóa API. Nếu muốn theo dõi nhiều giải, thêm các cấu hình giải đấu riêng.

<!-- ha-marketplace:exclude-start -->

### Cài đặt thủ công

Nếu không sử dụng Marketplace, tải mã từ [trang phát hành](https://github.com/khaisilk1910/Football-News/releases), giải nén và chép thư mục:

```text
custom_components/football_news
```

vào thư mục cấu hình Home Assistant:

```text
/config/custom_components/football_news
```

Kiểm tra file `/config/custom_components/football_news/manifest.json` tồn tại, sau đó khởi động lại Home Assistant và tiến hành thiết lập như trên. **Không** chép cả thư mục `Football-News` vào `custom_components`.

<!-- ha-marketplace:exclude-end -->

## 📲 Cấu hình thông báo Zalo

Football News gửi tin qua action `zalo_bot.send_message`, **không tự đăng nhập Zalo** và **không lưu mật khẩu Zalo Bot Server**.

**Điều kiện:** Bạn đã cài và cấu hình [Zalo Bot cho Home Assistant](https://github.com/khaisilk1910/zalo-bot-hacs); Zalo Bot Server tương thích và tài khoản gửi đang hoạt động. Để hiển thị chữ đậm, màu và cỡ chữ, hãy bật tính năng **Markdown** trong tích hợp Zalo Bot.

Trong **Thiết bị & dịch vụ → Football News → Configure**, nhập:

| Mục | Ý nghĩa |
|:--|:--|
| **Bật thông báo Zalo** | Cho phép Football News gửi thông báo |
| **Tài khoản gửi (`account_selection`)** | Tài khoản đã đăng nhập trên Zalo Bot |
| **ID cuộc trò chuyện (`thread_id`)** | ID cá nhân/nhóm, nên sử dụng cú pháp `zalo:<ID>` để tránh mất độ chính xác |
| **Loại cuộc trò chuyện** | `0` = cá nhân; `1` = nhóm |
| **Nhắc lịch thi đấu** | Gửi trước giờ trận theo khoảng phút đã chọn, từ 5 đến 120 phút |
| **Thông báo bắt đầu trận** | Gửi khi dữ liệu chuyển từ trạng thái chưa bắt đầu sang đang diễn ra |
| **Thông báo kết quả** | Gửi khi dữ liệu chuyển sang kết thúc và có tỷ số hợp lệ |
| **Thông báo bàn thắng / tỷ số** | Phát hiện tỷ số tăng trong một trận đang diễn ra. Nội dung không suy diễn tên người ghi bàn khi nguồn chưa có. |
| **Đánh dấu trận** | Nhấn ký hiệu thông báo bên cạnh trận; nếu đã chọn trận trong giải, chỉ gửi thông báo trận cho các trận đó |
| **Thông báo tin tức** | Gửi bài mới đủ điều kiện, không phát lại hàng loạt tin cũ ở lần tải đầu tiên |
| **Bộ lọc đội bóng** | Chỉ thông báo trận có tên đội khớp nội dung lọc; để trống để theo dõi cả giải |

Sau khi lưu, chạy action **`football_news.test_zalo`** trong Công cụ nhà phát triển để thử gửi tin.

### Mẫu thông báo trên Zalo

Các mẫu dưới đây mô tả cách Football News định dạng tin theo cú pháp rich-text được hỗ trợ trong README của Zalo Bot. Nội dung và thời gian thực tế lấy từ dữ liệu trận/tin của nguồn.

**⏰ Trước trận:**

```text
{big}{orange}**⏰ FOOTBALL NEWS · SẮP THI ĐẤU**{/orange}{/big}
**Đội chủ nhà**  ⚔️  **Đội khách**
🏆 Premier League
🗓 19/11 21:00
🏟 Sân vận động
{small}Lịch có thể thay đổi · Giờ theo múi giờ Home Assistant{/small}
```

**🏁 Kết thúc trận:**

```text
{big}{green}**🏁 FOOTBALL NEWS · KẾT QUẢ**{/green}{/big}
**Đội chủ nhà**  ⚔️  **Đội khách**
{big}**2 - 1**{/big}
🏆 Premier League
{small}Kết quả theo dữ liệu ESPN · Home Assistant{/small}
```

**📰 Tin tức:**

```text
{big}{green}**📰 FOOTBALL NEWS · TIN MỚI**{/green}{/big}
Tiêu đề bài viết từ nguồn
🏆 Premier League
🔗 https://www.espn.com/...
{small}Nguồn: ESPN · Thông báo từ Home Assistant{/small}
```

**Lưu ý kỹ thuật:** Tin được chuyển qua action `zalo_bot.send_message`, dùng các thẻ `{big}`, `{small}`, `{orange}`, `{green}` và Markdown. Zalo ID lớn phải giữ dưới dạng **chuỗi**. Tránh dùng `int`/`float` trong template với ID Zalo.

## ⚙️ Tối ưu hiệu năng và độ chính xác

- **Khởi động nhẹ:** Không bắt Home Assistant chờ phản hồi ESPN hoặc Zalo khi nạp tích hợp.
- **Tần suất phù hợp:** Khoảng 60 giây nếu có trận đang diễn ra; 5 phút khi không có trận trực tiếp. Bảng xếp hạng và tin tức sử dụng bộ nhớ đệm riêng để giảm yêu cầu mạng.
- **Không tự tạo tỷ số:** Dữ liệu thiếu được giữ ở trạng thái chưa xác định, không thay thành kết quả `0–0`.
- **Lưu dữ liệu hợp lệ gần nhất:** Lỗi mạng tạm thời không tự động xóa dữ liệu đã lấy được trong phiên chạy hiện tại.
- **Không gửi trùng tùy tiện:** Lưu dấu trạng thái/thông báo đã xử lý; thông báo vẫn có thể bị bỏ lỡ nếu Home Assistant tắt hoặc mất mạng đúng thời điểm.
- **Chi tiết theo yêu cầu:** Dữ liệu chi tiết trận chỉ được lấy khi mở trận hoặc gọi action, không tải tất cả trong lúc khởi động.

**Nguồn dữ liệu hiện tại:** Các endpoint JSON công khai nhưng **không chính thức** của ESPN. Chúng có thể thay đổi hoặc ngừng hoạt động mà không báo trước; không phải tất cả giải đấu đều cung cấp cùng mức chi tiết.

## 🧰 Action và cảm biến

Các action sử dụng domain `football_news`:

Ghi chú: nội dung README mô tả tính năng **đã triển khai**; những mục chỉ có ở Football Hub gốc được ghi rõ trong [FEATURES.md](FEATURES.md). Không nên coi đây là bản sao đầy đủ Football Hub.

| Action | Công dụng |
|:--|:--|
| `football_news.refresh` | Yêu cầu làm mới dữ liệu |
| `football_news.test_zalo` | Gửi thử một tin thông báo Zalo |
| `football_news.match_details` | Lấy dữ liệu chi tiết của một trận từ ID ESPN (có phản hồi trả về) |

Ví dụ gọi chi tiết trận bằng YAML:

```yaml
action: football_news.match_details
data:
  event_id: "401234567"  # Thay bằng ID trận thực tế
response_variable: chi_tiet_tran
```

Mỗi giải tạo thiết bị Football News với các cảm biến tóm tắt như số trận trực tiếp, số trận sắp tới, số tin, **số CLB yêu thích**, trận tiếp theo, lần cập nhật và khả năng kết nối nguồn. Tên/ID thực tế được Home Assistant tạo theo cấu hình của bạn.

## 🩺 Khi có lỗi hoặc dữ liệu không cập nhật

### Trang Football News trong sidebar trắng

1. Xác nhận phiên bản của tích hợp là **2026.11.11.4** tại **Cài đặt → Thiết bị & dịch vụ → Football News**.
2. Mở trực tiếp `http://ĐỊA_CHỈ_HA:8123/football_news/panel.js` trong trình duyệt. Phải hiển thị mã JavaScript, không phải lỗi 404 hoặc trang đăng nhập. Dùng cùng host/port mà bạn đang mở Home Assistant.
3. **Khởi động lại Home Assistant** sau khi thay mã Python, rồi tải lại trang bằng **Ctrl+F5** để xóa cache trình duyệt.
4. Nếu vẫn trắng, nhấn **F12 → Console** và kiểm tra các lỗi có chữ `football-news-panel` hoặc `panel.js`. Bản cập nhật sẽ hiển thị thông báo khi dữ liệu WebSocket bị lỗi.

### Cảm biến lịch hoặc trạng thái nguồn hiển thị `Unavailable`

- Có thể dữ liệu tin tức vẫn hoạt động nhưng truy vấn **scoreboard ESPN** của giải đang bị lỗi; đây là **hai nguồn dữ liệu thành phần khác nhau**.
- Bản mới thử truy vấn lịch có khoảng ngày; nếu không được, thử lại **một lần** bằng truy vấn mặc định, tránh yêu cầu mạng liên tục.
- Vào **Cài đặt → Hệ thống → Nhật ký** và tìm `custom_components.football_news` hoặc bật chế độ debug bên dưới. Dashboard cũng hiển thị lỗi lấy dữ liệu ngay trên giao diện.
- Nếu ESPN không trả kết quả cho mã giải đấu, cảm biến không được tự biến thành `0` hay một tỷ số tưởng tượng. Hãy thử giải khác, chẳng hạn Premier League, để xác định có phải giới hạn nguồn.

### Các bước kiểm tra khác

1. Mở dashboard và kiểm tra mốc **cập nhật gần nhất** cùng trạng thái nguồn.
2. Thử action `football_news.refresh` để yêu cầu làm mới.
3. Xem **Cài đặt → Hệ thống → Nhật ký**, tìm `football_news`.
4. Mở **Cài đặt → Thiết bị & dịch vụ → Football News → Tải chẩn đoán** để lấy thông tin hỗ trợ đã hạn chế dữ liệu nhạy cảm.
5. Nếu không gửi được Zalo, kiểm tra tích hợp `zalo_bot`, tài khoản gửi, ID cuộc trò chuyện và quyền gửi tin vào nhóm.

Để xem log chi tiết, thêm vào `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.football_news: debug
```

Không đăng mật khẩu, token hoặc Zalo ID thật vào issue công khai. Có thể [báo lỗi tại GitHub Issues](https://github.com/khaisilk1910/Football-News/issues).

## 📦 Cập nhật và phát hành

Phiên bản mã nguồn hiện tại: **2026.11.11.4**. Cập nhật qua **Cài đặt → Marketplace** hoặc trang **Updates** khi bản phát hành mới xuất hiện. Với bản cài thủ công, thay thư mục `custom_components/football_news` rồi khởi động lại Home Assistant.

Dành cho người duy trì repository:

- Đưa **toàn bộ nội dung repository**, bao gồm `.github` và `.gitignore`, lên `https://github.com/khaisilk1910/Football-News`, không chỉ file ZIP cài đặt.
- Chạy [quy trình kiểm tra mã nguồn](https://github.com/khaisilk1910/Football-News/actions/workflows/validate.yml) và xử lý lỗi nếu có.
- Tạo Git tag **`v2026.11.11.4`** trùng phiên bản trong `manifest.json` và `const.py`. Quy trình `.github/workflows/release.yml` tự xây dựng ZIP, kiểm tra và tạo GitHub Release kèm **`football_news.zip`** cho ai cần cài thủ công.
- Marketplace cài trực tiếp thư mục `custom_components/football_news` từ mã nguồn GitHub, nên **không bắt buộc tải asset ZIP**. Vẫn nên tạo GitHub Release mới để cập nhật rõ ràng. Không dùng tag cũ `v2026.11.11.1` cho mã mới.

**Nếu gặp lỗi 404 khi cài:** đây là tình trạng bản cũ bật `zip_release: true` nhưng Release GitHub thiếu `football_news.zip`. Hãy đưa **trọn bộ repository mới** (cả thư mục ẩn `.github` và file `.gitignore`) lên nhánh `main`, tạo Release `v2026.11.11.4` từ commit mới, sau đó tải lại thông tin repository trong Marketplace và cài đặt. Xem [hướng dẫn xuất bản và sửa lỗi](RELEASE.md).

File **`.gitignore`** nằm ở **thư mục gốc** của repository, cùng cấp `README.md`, `LICENSE` và `hacs.json`. File có dấu chấm đầu tên nên có thể bị ẩn trong trình quản lý tập tin. Gói **repository ZIP** chứa file này; gói cài **`football_news.zip`** không cần chứa nó.

## 🔐 Giấy phép và ghi nhận

Football News là một tích hợp độc lập có giấy phép **MIT**; chi tiết nằm trong [LICENSE](LICENSE). Dự án không dùng mã nguồn hoặc hình ảnh có giấy phép hạn chế của Football Hub. Logo/nền tảng Home Assistant, tên đội, giải đấu, nhà cung cấp và Zalo thuộc chủ sở hữu tương ứng; việc xuất hiện trong phần mô tả không có nghĩa dự án được họ chứng nhận.

**Liên kết:** [Mã nguồn](https://github.com/khaisilk1910/Football-News) · [Phiên bản](https://github.com/khaisilk1910/Football-News/releases) · [Báo lỗi](https://github.com/khaisilk1910/Football-News/issues) · [Lịch sử thay đổi](CHANGELOG.md)
