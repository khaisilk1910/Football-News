# ⚽ Football News — Home Assistant

[![Validate](https://github.com/khaisilk1910/Football-News/actions/workflows/validate.yml/badge.svg)](https://github.com/khaisilk1910/Football-News/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/khaisilk1910/Football-News?display_name=tag)](https://github.com/khaisilk1910/Football-News/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.11%2B-18bcf2)](https://www.home-assistant.io/)
[![Language](https://img.shields.io/badge/ng%C3%B4n%20ng%E1%BB%AF-Ti%E1%BA%BFng%20Vi%E1%BB%87t-20c5bb)](#ng%C3%B4n-ng%E1%BB%AF)

**Football News** là tích hợp Home Assistant được xây dựng độc lập, cung cấp dashboard bóng đá hiện đại bằng tiếng Việt, lịch thi đấu, tỷ số trực tiếp, kết quả, bảng xếp hạng, tin tức và gửi thông báo qua tích hợp **Zalo Bot**.

## Cài nhanh trên Marketplace / HACS

[![Mở Football News trong Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=khaisilk1910&repository=Football-News&category=integration)

**Nút trên** mở đường dẫn nhanh tới repository trong Home Assistant (trên Home Assistant 2026.11+ đường dẫn HACS cũ được chuyển sang Marketplace). Bạn phải **đẩy mã nguồn lên GitHub và xuất bản GitHub Release thành công trước** vì `hacs.json` bật `zip_release`.

1. Mở **Settings → Marketplace → Add from link** trong Home Assistant 2026.11+.
2. Dán `https://github.com/khaisilk1910/Football-News` và bấm **Add**; kết nối GitHub nếu được yêu cầu.
3. Nếu được hỏi loại repository, chọn **Integration**.
4. Chọn **Football News → Install** và khởi động lại Home Assistant.
5. Vào **Settings → Devices & services → Add integration → Football News**, chọn giải đấu.
6. Mở **Football News** trong thanh bên.

**HACS cũ (Home Assistant ≤2026.10):** HACS → ba chấm → Custom repositories → thêm URL ở trên, chọn `Integration`, cài và restart. Mặc dù có thể nhận ZIP, mã nguồn này mới được thiết kế theo API của Home Assistant 2026.11+; chạy trên 2026.10 trở xuống **không được hỗ trợ**.

### Cài thủ công

1. Tải mã nguồn từ GitHub Release hoặc ZIP repository.
2. Chép **duy nhất** thư mục `custom_components/football_news` vào `/config/custom_components/football_news`.
3. Kiểm tra đường dẫn `/config/custom_components/football_news/manifest.json` tồn tại, không bị lồng hai lớp thư mục.
4. Khởi động lại Home Assistant, sau đó thêm tích hợp **Football News** qua giao diện.
5. Cài và cấu hình Zalo Bot riêng nếu muốn gửi Zalo.

## Tính năng

| Nhóm | Chức năng |
|---|---|
| Dashboard | Thiết kế đỏ đô và vàng kim, icon bóng đá + Home Assistant + News, tương thích thiết bị di động |
| Bản địa hóa | Tiếng Việt & tiếng Anh cho dashboard, setup flow, options flow, entity, action |
| Lịch thi đấu | Trận từ 2 ngày trước đến 8 ngày tới; ngày giờ theo múi giờ cấu hình Home Assistant |
| Trực tiếp | Trạng thái trước trận/đang thi đấu/kết thúc; tỷ số chưa có không bị chuyển thành `0–0` |
| Kết quả | Điểm số thực tế từ nguồn dữ liệu; thông tin sân nếu được trả về |
| Bảng xếp hạng | Vị trí, trận, thắng, hòa, thua, hiệu số và điểm khi dữ liệu có sẵn |
| Tin tức | Tiêu đề, trích đoạn, thời gian phát hành và liên kết bài gốc (HTTPS) |
| Zalo | Thử gửi tin, thông báo bắt đầu, nhắc trước trận, kết quả, tin mới; chống gửi trùng bằng lưu trạng thái |
| Chẩn đoán | Log theo từng nguồn, mốc cập nhật, số lượng dữ liệu và Download diagnostics không chứa ID Zalo |
| Hiệu năng | Không gửi HTTP tới nhà cung cấp hoặc Zalo lúc startup; polling 60 giây khi có trận trực tiếp, 5 phút khi không có trận; cache riêng cho bảng và tin |
| Chi tiết trận | Action `football_news.match_details` đọc ESPN summary khi được gọi, không tải mọi chi tiết khi khởi động |

### Giải đấu cấu hình được

Premier League, EFL Championship, LaLiga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Scottish Premiership, MLS, UEFA Champions League, UEFA Europa League và UEFA Conference League.

Các giải đấu phụ thuộc mã giải do ESPN công bố trong API không chính thức. Có thể có mùa giải, bảng xếp hạng hoặc trận thiếu dữ liệu. Việc chọn giải mới tạo một config entry riêng; dashboard mặc định hiển thị giải được cấu hình đầu tiên.

## Dữ liệu và độ tin cậy

- **Nguồn:** endpoint JSON công khai, không chính thức của ESPN (không yêu cầu API key).
- **Scoreboard**: `site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard`.
- **Bảng xếp hạng**: `site.api.espn.com/apis/v2/sports/soccer/{league}/standings`.
- **Tin tức**: `site.api.espn.com/apis/site/v2/sports/soccer/{league}/news`.
- **Chi tiết trận (theo yêu cầu)**: `site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event=...`; chọn nút **Chi tiết** của một trận trên dashboard để tải diễn biến và thống kê có sẵn.

Các endpoint này **không phải API được ESPN cam kết hỗ trợ**, có thể thay đổi cấu trúc, giới hạn truy cập hoặc ngừng hoạt động bất kỳ lúc nào. Football News không bịa thông số khi thiếu dữ liệu. Thời gian làm mới và trạng thái lỗi được hiển thị để tiện xác minh. Không dùng dữ liệu này làm cơ sở duy nhất cho hoạt động tài chính/cá cược.

## Cấu hình thông báo Zalo

Football News **không đăng nhập trực tiếp vào Zalo** và không nhận/lưu mật khẩu Zalo; ứng dụng chuyển tin qua action `zalo_bot.send_message` của custom integration Zalo Bot đã cài đặt.

Yêu cầu: cài `zalo_bot` và Zalo Bot Server tương thích, kiểm tra tài khoản Zalo đang đăng nhập, bật entity **Markdown** trong Zalo Bot để nhận rich-text. Xem [repo Zalo Bot](https://github.com/khaisilk1910/zalo-bot-hacs) và [Zalo Bot Server](https://github.com/khaisilk1910/zalo-bot-server).

1. **Settings → Devices & services → Football News → Configure**.
2. Chọn **Ngôn ngữ dashboard: Tiếng Việt**.
3. Tùy chọn **Lọc tên đội bóng**, ví dụ `Arsenal` (để trống = mọi đội của giải).
4. Bật **Bật thông báo Zalo**.
5. Điền `account_selection` (số tài khoản gửi đang đăng nhập trong Zalo Bot), `thread_id` dạng **chuỗi ký tự**, và `type` (`0` = người dùng, `1` = nhóm).
6. Bật hoặc tắt từng thông báo: **lịch thi đấu**, **bắt đầu trận**, **kết quả**, **tin tức**. Chọn nhắc trước **5–120 phút**.
7. Lưu cấu hình và chạy action `football_news.test_zalo` để kiểm tra.

Đối với Zalo ID dài, nhập `zalo:2036121378794772276` (minh họa) thay vì ép sang số. Thao tác này bảo toàn ID khi đi qua JSON/JavaScript. Không sử dụng `| int` hoặc `| float` cho Zalo ID. Không điền ID cá nhân thật vào GitHub, issue hoặc file YAML công khai.

### Tin nhắn được định dạng theo README Zalo

**Nhắc lịch thi đấu:**

```text
{big}{orange}**⏰ FOOTBALL NEWS · SẮP THI ĐẤU**{/orange}{/big}
**Arsenal**  ⚔️  **Chelsea**
🏆 Premier League
🗓 12/11 02:45
🏟 Emirates Stadium
{small}Lịch có thể thay đổi · Giờ theo múi giờ Home Assistant{/small}
```

**Kết quả trận đấu:**

```text
{big}{green}**🏁 FOOTBALL NEWS · KẾT QUẢ**{/green}{/big}
**Arsenal**  ⚔️  **Chelsea**
{big}**2 - 1**{/big}
🏆 Premier League
🗓 12/11 02:45
{small}Kết quả theo dữ liệu ESPN · Home Assistant{/small}
```

**Tin tức:**

```text
{big}{green}**📰 FOOTBALL NEWS · TIN MỚI**{/green}{/big}
[Tiêu đề lấy nguyên từ dữ liệu nguồn]
🏆 Premier League
🔗 https://www.espn.com/...
{small}Nguồn: ESPN · Thông báo từ Home Assistant{/small}
```

Các format chỉ dùng style có trong tài liệu Zalo Bot: `**bold**`, `{big}`, `{small}`, `{green}`, `{orange}`; không truyền màu HEX không được hỗ trợ. Zalo Server nhận `thread_id` kiểu chuỗi và gửi message theo đúng action:

```yaml
action: zalo_bot.send_message
data:
  account_selection: "+84123456789"     # Thay bằng tài khoản gửi của bạn
  thread_id: "zalo:2036121378794772276"  # Ví dụ, thay bằng ID của bạn
  type: "1"                              # 1 = group, 0 = user
  message: |
    {big}{green}**⚽ FOOTBALL NEWS**{/green}{/big}
    Thử định dạng từ Home Assistant.
```

**Cách hoạt động:** nhắc lịch gửi một lần trong cửa sổ đã cấu hình, thông báo bắt đầu/kết quả chỉ gửi khi nhận thấy thay đổi trạng thái trận; tin mới gửi tối đa các bài mới gần đây, không gửi hàng loạt bài cũ ở lần khởi chạy đầu tiên. Dedupe lưu trong Home Assistant `.storage` qua `Store`. Nếu HA ngắt mạng hoặc tắt máy lúc diễn ra sự kiện, thông báo bị bỏ lỡ có thể không được gửi bù. Việc nhận tin phụ thuộc tài khoản, Zalo Server và quyền hạn nhóm.

## Các action Home Assistant

### `football_news.refresh`

```yaml
action: football_news.refresh
data: {}
```

### `football_news.test_zalo`

```yaml
action: football_news.test_zalo
data: {}
```

### `football_news.match_details`

```yaml
action: football_news.match_details
data:
  event_id: "401234567" # ví dụ, thay bằng mã trận thực tế
response_variable: football_match
```

Nếu có nhiều giải, nhập thêm `entry_id` trong action để chọn cấu hình cụ thể. Mã trận là ID từ ESPN; action trả `header`, `boxscore`, `key_events`, `scoring_plays` có sẵn, không tự tạo dữ liệu giả.

## Entity được tạo

Mỗi giải được cấu hình tạo thiết bị `Football News · <league>` với các entity: **Số trận trực tiếp**, **Số trận sắp diễn ra**, **Số tin tức**, **Lịch trận tiếp theo**, **Lần cập nhật dữ liệu**, **Nguồn dữ liệu sẵn sàng**. ID entity thực tế do Home Assistant sinh và có thể khác nhau. Dữ liệu chi tiết tải qua websocket khi mở dashboard, không đưa toàn bộ tin tức vào thuộc tính sensor để tránh tăng kích thước Recorder.

## Ngôn ngữ

- Chuyển ngôn ngữ Home Assistant sang tiếng Việt để các bản dịch config/options/action/entity hiển thị bằng tiếng Việt.
- Vào **Football News → Configure** để chọn tiếng Việt/English cho dashboard.
- Tên riêng của đội bóng, giải đấu, bài báo là dữ liệu gốc của nhà cung cấp, **không dịch máy** để tránh bóp méo thông tin.

## Log và chẩn đoán

Mở **Settings → System → Logs**, lọc `football_news`. Có thể bật debug trong `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.football_news: debug
```

Khởi động lại HA sau khi đổi YAML. Log hiển thị nhóm dữ liệu lỗi và HTTP status, không hiển thị nội dung tin hoặc ID Zalo. Tại **Settings → Devices & services → Football News → Download diagnostics** để tải chẩn đoán (chỉ tổng số mục, thời gian thành công và flag thông báo).

Nếu có nguồn trả về lỗi mạng: Football News giữ kết quả gần nhất trong bộ nhớ của phiên HA hiện tại và hiển thị cảnh báo. Sau restart mà mất mạng, sensor có thể `unavailable` đến khi dữ liệu tải được. Bảng xếp hạng giữ cache 6 giờ, tin tức 30 phút, lịch thi đấu tối đa 60 giây trong bộ nhớ; không ghi raw provider JSON vào `.storage`.

## Repository và phát hành bản đầu tiên

Cấu trúc:

```text
Football-News/
├── .github/workflows/{validate.yml,release.yml}
├── .gitignore
├── LICENSE
├── README.md
├── CHANGELOG.md
├── hacs.json
├── custom_components/football_news/
│   ├── __init__.py, config_flow.py, coordinator.py
│   ├── provider.py, models.py, notifications.py
│   ├── sensor.py, binary_sensor.py, diagnostics.py
│   ├── manifest.json, services.yaml, strings.json
│   ├── translations/{vi.json,en.json}
│   ├── brand/{icon.png,icon@2x.png}
│   └── frontend/panel.js
└── tests/
```


## Giấy phép và lưu ý

Mã mới trong repository này dùng **MIT**; tài sản icon được tạo riêng cho Football News. Không sử dụng code/hình ảnh của dự án Football Hub có giấy phép hạn chế. Tên giải, CLB và nhãn hiệu dữ liệu thuộc chủ sở hữu tương ứng. Football News không liên kết hoặc được ESPN, Zalo, Home Assistant, HACS hay các ban tổ chức giải đấu bảo trợ.
