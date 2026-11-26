## 2026.11.26.3 — First open / Reload: WebSocket recovery and reliable HA Store retry

- **Fix:** the **Đọc lại dữ liệu đã lưu** button now preempts a hung snapshot request instead of silently returning while `_loading` is true. Old WebSocket responses cannot erase a newer successful snapshot.
- **Fix:** detect Companion socket replacement even when HA mutates the same `hass` object. Prefer Home Assistant's public `hass.callWS` facade.
- **HA Store-first:** use a shared asynchronous HA Store read with a maximum **6-second fast / 10-second full** foreground budget. If storage is slow, return an explicit WebSocket response with server diagnostics and let the HA Store read finish in the background, then broadcast a data-updated event. No ESPN call is started by this path.
- **Recovery:** bring a suspended/hidden mobile WebView back to a working state with bounded request deadlines, a page activation retry, and a 17-second stalled-read watchdog. Retain last-good data across retries.
- **Diagnostics:** surface whether HA has supplied the `hass` object or if the backend WebSocket has not yet replied; log slow disk reads without printing sensitive data.
- **Tests:** added regressions for a manual retry during a hung request, changing a socket on an in-place `hass` object, shared Store reads that exceed the foreground deadline, and Chromium mobile/desktop cold-panel recovery.

**Compatibility:** Cache, config entries, per-league sensors, Live updates, and Zalo notifications are unchanged. Keep `.storage` intact. As before, an unavailable Home Assistant connection or an empty/invalid HA Store cannot supply football scores.

## 2026.11.26.2 — HA Store-first on every device and browser reload

- The initial `football_news/data` WebSocket call now **reads persisted Home Assistant Store snapshots before coordinator RAM**, even when the coordinator is still starting. Stored fixtures, tables and news can be rendered on the first open without waiting for ESPN or a second navigation.
- Share per-league Store reads across simultaneous sessions; validate the saved data and preserve the existing read-only fallbacks for temporarily unavailable config-entry indexes and old entry IDs. A brief timeout is bounded to the dashboard request and never blocks Home Assistant startup.
- Both fast and full snapshot paths use Store-first recovery, with explicit `cache_source` (`ha_store`, `memory`, `none`) and `store_attempted`/`store_restored`/`store_errors` diagnostics. Only valid persisted datasets are shown; keep fresher coordinator feeds when available.
- Continue the existing 120-second ESPN grace period and adaptive Live updates. No per-device data copy, new ESPN request, or startup disk-wait is introduced. Update frontend asset version and tests for concurrent HA Store reads, reload and fresh-install behavior.

## 2026.11.26.1 — Nonblocking first-open HA cache and socket reconnect recovery

- **Immediate HA-memory bootstrap:** `football_news/data` with `fast:true` replies synchronously with valid coordinator RAM and already warmed HA Store snapshots. It does not await slow HA Store reads, league registry discovery, account preferences or ESPN. This addresses first-open WebSocket timeouts in Android Companion.
- **Shared server-side disk warm:** when memory has no data, launch one Home Assistant task to read saved snapshots from HA Store and/or restore the configured league index. Broadcast `football_news_data_updated` when local cache has been loaded; all open devices re-read the same server-owned snapshot. No per-browser persistence or ESPN network call is involved.
- **No store writes on reads:** remove redundant league-registry `remember()` from the snapshot read path; registration/removal already manages the registry. Reuse warmed disk feeds in full snapshots instead of duplicating HA Store I/O.
- **WebSocket generation safety:** when HA Companion replaces the WebSocket during login or reload, release the old loading lock, start a new fast read immediately and discard late replies from the old connection. Reduce blocking request timeouts and keep automatic retries on the same page.
- Keep the existing 120-second cache-first grace period and all prior Live, Zalo, voice and per-league functions. Missing/expired HA Store data still requires ESPN once the grace period ends; no system can display football data that was never saved.
- Add regression coverage for single-flight HA Store recovery and an in-flight request on a replaced HA WebSocket.

## 2026.11.21.7 — Zalo goal notifications with full ESPN play-by-play

- Add the verified goal's ESPN `text`/`description`/`shortText` commentary to Zalo notifications, keeping the precise match incident text (shot description and assist when ESPN supplies it) alongside score, scorer, team, match minute and competition.
- Choose the longest source text for the **same goal event**, not a generic label like `Goal!`; sanitize rich-text markup, bound length for Zalo, and keep multiple new goals distinct.
- Retain existing score and complete-timeline verification. If ESPN's summary is stale or incomplete, notify only the score with an explicit unavailable attribution rather than attaching a previous goal's commentary.
- No additional ESPN requests at Home Assistant startup or during match polling; reuse the already bounded Match Summary lookup in the asynchronous Zalo notification path.
- Add unit and end-to-end notification regressions for rich commentary, multi-goal matching, stale ESPN snapshots, message sanitization and delivery deduplication.

## 2026.11.21.6 — Logo đội bóng trong Thống kê và Đội hình

- Bảng so sánh trận đấu: thay nhãn chữ “Chủ nhà/Đội khách” bằng logo CLB lớn, tên CLB thu nhỏ bên dưới, giữ đủ ba cột và các chỉ số.
- Danh sách cầu thủ: đặt logo chính thức bên trái tên từng CLB cho cả hai đội.
- Giữ logo từ dữ liệu ESPN Match Summary, sau đó dùng cache giải đấu / bảng xếp hạng cùng giải khi thiếu logo; không gọi thêm ESPN khi mở trang.
- Giữ biểu tượng trung tính nếu ESPN không cung cấp logo; cải thiện khả năng hiển thị trên màn hình nhỏ.
- Không thay đổi lịch polling, cache HA Store, sensor hay tùy chọn của tích hợp.

## 2026.11.21.5 — Chi tiết cầu thủ và phút ghi bàn trong Zalo

- Làm giàu thông báo `goal_alerts` gửi qua Zalo Bot: khi tỷ số Live tăng, đối chiếu nhanh với ESPN Match Summary để gửi **đội ghi bàn, cầu thủ ghi bàn và phút thi đấu** (gồm phút bù giờ). Giữ nguyên tên cặp đấu, tỷ số, giải đấu.
- Chỉ gắn tên cầu thủ khi ESPN Summary xác nhận cùng tỷ số và diễn biến ghi bàn đầy đủ cho đội vừa ghi bàn. Nếu ESPN trả chậm, lỗi hoặc có bàn phản lưới / điều chỉnh tỷ số chưa xác thực, vẫn thông báo tỷ số mà không gán sai cầu thủ.
- Dùng chung cache ESPN match summary trên Home Assistant, giới hạn tối đa 5 giây cho bước lấy chi tiết và thực hiện trong tác vụ thông báo nền; không tăng truy vấn lúc khởi động HA và không thay đổi giao diện popup.
- Thêm kiểm thử tỷ số 0–1 → 1–1, phút bù giờ, hai đội cùng đổi tỷ số, thiếu cầu thủ, ESPN lỗi, dữ liệu Summary cũ và chống trùng sau khi gửi.

## 2026.11.21.4 — Three-column stats and readable match lineups

- Replace separate home/away statistics panels with a single accessible table: **statistic | home team | away team**, aligned by ESPN statistic keys (not array positions). Resolve team order from ESPN home/away markers, IDs and fixture names; missing values remain `—` rather than being assigned to the wrong team.
- Always render one position chip per listed player so missing ESPN position data cannot squeeze player names into the narrow badge column. Correct mobile grid widths and preserve names across the full row.
- Expand source-supplied position values into GK/DF/MF/FW; preserve explicit CB, CDM, CF and other precise codes. When a recent-match roster already loaded from HA provides a more specific position for the same player ID, use it; never invent a specific role from generic D/M/F.
- Continue to keep teams, player groups, HA Store data and startup/ESPN poll behavior unchanged. Add data-normalization, mobile viewport and JavaScript regression coverage.

## 2026.11.21.3 — Reverse Live timeline and clear match-day squads

- Show match events newest-to-oldest with stoppage-time aware minute ordering (including 45+2, 90+3). First-half kickoff now appears at the bottom, and the latest Live incident at the top.
- Clearly separate the **starting XI**, **substitutes**, and **players not named in the match sheet** for each team. Visually distinguish GK, CB, CM, CF and other ESPN-supplied position abbreviations with role-specific high-contrast badges, including in club roster cards.
- Match summary normalization retains ESPN athlete/team IDs and declared starter/inactive status. Players are never marked absent merely because `starter` is false.
- Optionally load the two clubs' season rosters only when opening a recent match with a sufficiently complete ESPN match sheet. Compare stable player IDs and names; if the source is incomplete or the roster is unavailable, say the absent group cannot be confirmed. A historical match is never compared against today's squad.
- Add `football_news/match_roster`, an on-demand authenticated WebSocket command using the existing 12-hour server-side ESPN roster cache. No new requests at Home Assistant startup or while merely browsing fixtures. Live detail refresh preserves the classification without repeated roster fetches.
- Add Python, JavaScript and Chromium regression checks for event ordering, match-sheet grouping, position badges and uncertain squad membership.

## 2026.11.21.2 — Cache-first initial visit and deferred ESPN

- First WebSocket response reads RAM **or** the existing HA Store snapshot (3-second bounded concurrent disk fallback), not just coordinator RAM. Missing stores are not treated as missing configured leagues.
- Keep a 120-second non-blocking grace period for automatic ESPN polling after each Home Assistant config-entry startup. Saved cache is restored first; no ESPN access on the first panel read.
- Fresh installation or expired/absent disk cache reports an explicit waiting-for-ESPN state, instead of a never-ending "restoring" spinner.
- Prevent automatic initial player-leader and favourite-form requests from bypassing the cache-first window.
- Preserve existing favourites, per-league sensors, live notifications, and persisted data. Live adaptive polling resumes after initial grace period.

## 2026.11.21.1 — Fast first paint for Home Assistant Companion and browser refresh

- Add an authenticated `football_news/data` WebSocket `fast` option that returns already-restored coordinator RAM feeds immediately. It does **not** wait for a local HA Store read, league-registry load, per-account UI settings, ESPN, or any notification network I/O.
- Always follow the fast first paint with a full, authoritative HA Store snapshot; retain fixtures/standings already visible while profile preferences and remaining feeds hydrate. On a WebSocket reconnect, repeat the fast bootstrap on the new connection.
- Run optional favourites and per-account UI Store reads concurrently with league/cache recovery instead of serially, and bound league registry lookups with a shared total time budget. Avoid rereading the same validated emergency Store cache twice.
- Extend the full snapshot WebSocket budget to handle cold disks while the fast RAM snapshot is already displayed. Retry on the same open page, including Android WebViews reporting `document.hidden`.
- Preserve per-league favourites, ten-match form, next-round voice sensors, adaptive Live polling, popup notifications and 20-second auto-dismiss. No new upstream ESPN requests during HA startup.
- Add separate Python and JavaScript regressions for instant first-paint responses while HA Store is blocked, initial empty entries, late full hydration, and repeated browser refresh.

## 2026.11.20.7

- Use responsive two-club crest posters instead of text-only favourite next-match rows; deduplicate a shared game between two favourites and retain match-details navigation.
- Change the per-competition 30-day Voice schedule into Next Round Fixtures using ESPN matchday/round metadata; if absent, clearly label a near-term estimated slate. Include all known fixtures in the next round, not just an arbitrary date window.
- Preserve the existing sensor entity-registry unique ID, bounded Recorder attributes, saved-fixture fallback and network-free startup; bump frontend cache-busting version.
- Add per-round tests, multi-favourite deduplication and responsive browser regression.

## 2026.11.20.6

- Display the next scheduled match for **each** saved favourite in the selected competition; never replace a missing club fixture with an unrelated league match.
- Display each favourite club's **up to 10** latest genuine final results (W/D/L with score, opponent, kickoff tooltip); preserve 5-clubs-per-league isolation and mobile layout.
- Fetch historical ESPN scoreboard months **only on demand** when Overview opens, stopping as soon as all favourite teams have ten results. Share per-month provider caches between devices; bound concurrent network requests and fail safely on partial ESPN outages.
- Persist up to 100 historical results per league in the existing HA Store cache (90-day validity). Reuse data after HA restart, reload, and on another device without per-browser storage; no new network work at HA startup.
- Add regression tests for five clubs with ten results each, missing matches, partial provider failures, Store persistence and scope isolation.

## 2026.11.20.5
- Per-league favourites: up to five clubs for **each** competition, with unchanged persisted data and no global five-club ceiling.
- My Clubs filters and requests club summaries only for the selected competition; per-league counters.
- Favorite-club and fixture sensor states scoped to the associated league config entry.
- Add a per-league 30-day fixture sensor with bounded `matches` and Assist/TTS `voice_text` attributes, generated locally from coordinator/HA Store fixtures.
- No startup network calls or new ESPN polling.

## 2026.11.20.4 — Reload/Live empty and 20-second notifications

- Prefer the Home Assistant coordinator's already-restored Store snapshot on F5/reload, without another disk read or ESPN request. Continue disk-only recovery if the coordinator is still starting.
- Live tab shows an explicit **no live matches** message after HA confirms fixture data, independently of other league feeds still hydrating. Loading spinner appears only when the fixture feed is not yet ready.
- In-panel status/warning/error notifications and Live event popups automatically close after 20 seconds. Persistent conditions do not reset a toast's countdown on every HA update; the manual close button remains.
- Consistent frontend/backend cache-busting version 2026.11.20.4.

## 2026.11.20.3 — Read-only HA Store rescue for empty first page

- Keep coordinator cache hydration retryable after WebSocket cancellation; use a shielded, bounded first-view read.
- Recover public saved competition snapshots from the HA Store namespace when both HA config entry enumeration and its saved league index are absent, and reuse prior valid same-league cache after an entry-id change. No ESPN request is started for cache recovery; no automatic config-entry creation occurs.
- Never overwrite a valid recovered snapshot with an empty cold-index lookup. Validate cache schema, league, season and age before rendering saved data; stale Live status remains untrusted.
- Distinguish missing saved registry from Home Assistant startup in websocket metadata. Include backend version and safe diagnostic counts, with rate-limited no-snapshot logs; show backend status in empty-page UI.
- Reduce repeated local cache reads when showing orphaned read-only snapshots. Add cancellation, missing-entry, reconfigured-entry and browser smoke regressions.

## 2026.11.20.2 — Durable HA league registry and safe first-reload cache access

- Persist only league config-entry IDs/codes in an HA Store registry, written asynchronously and removed when HA removes the entry. Restore football `.storage` snapshots on the first WS request when the HA config-entry registry is temporarily empty or incomplete after reload.
- Bound optional Store reads, isolate preferences/UI read failure from public football data, and log native vs fallback registry state in diagnostics. Preserve ESPNs' adaptive Live polling and event popups.
- Never send a UI settings write while correcting a stale saved league during bootstrap. Initial empty view recovery reads the HA cache directly instead of invoking the ESPN refresh service, preventing a misleading error when the coordinator is not set up.
- Add server and frontend regression tests plus Chromium desktop/mobile cold-start checks. Requires at least one previously saved HA football snapshot; initial upgrade must register the entries once to create the new durable index.

## 2026.11.20.1 — Khôi phục dữ liệu HA Store ngay khi mở Football News lần đầu

- Sửa tình trạng WebView của Home Assistant báo `document.hidden` ngay khi mở: không dừng retry nếu danh sách giải đã có nhưng lịch thi đấu/bảng xếp hạng vẫn rỗng. Tự đọc lại WebSocket nội bộ trên chính trang đang mở.
- Tách trạng thái đã nhận registry ra khỏi trạng thái đã có dữ liệu bóng đá để không coi một phản hồi chỉ có tin tức (hoặc các feed rỗng) là đã hoàn tất khởi tạo.
- Luồng WebSocket ở HA ưu tiên các snapshot từ `.storage` cho những feed còn rỗng, kể cả khi coordinator đã gán timestamp nhưng ESPN chưa trả lịch/bảng. Không ghi đè feed RAM có dữ liệu mới.
- Giữ dữ liệu tốt đã nhận trong phiên đang mở khi HA tạm gửi phản hồi chưa đầy đủ; không lưu thêm snapshot riêng trên thiết bị.
- Hiển thị trạng thái khôi phục có nút tải lại trên Tổng quan thay vì màn hình trắng. Tăng thời gian chờ riêng cho snapshot đầu từ HA lên 20 giây, giữ 12 giây cho các yêu cầu phụ.
- Thêm log xác nhận lần đọc HA Store, các bài kiểm thử độc lập cho runtime có feed rỗng, WebView ẩn, trang chỉ có news, và WebSocket trả phản hồi từng phần.
- Không phát sinh truy vấn ESPN khi khởi tạo HA hoặc lúc đọc cache lần đầu. Giữ nguyên popup Live, cache tập trung, options và cấu trúc HACS/Marketplace.

## 2026.11.19.4 - Global in-panel Live goal/yellow/red card popups

- Add ESPN Live timeline monitoring on each configured competition's central Home Assistant coordinator; score/polling and timeline share the existing provider cache and network limits. Timeline requests run asynchronously, never blocking HA startup or primary sensor updates.
- Publish `football_news_live_event` through the HA event bus for newly confirmed goals, yellow cards and red cards (including second-yellow send-offs). Prefer the latest ESPN summary scoreboard when available, and include both team crests, current score, player, minute and league.
- First confirmed timeline becomes a baseline: never replay all historic goals/cards when the integration restarts or a device opens Football News. Deduplicate event IDs at the server and in each active panel, preserve the baseline across ESPN partial outages and stop background requests on entry unload.
- Add animated responsive Stadium Night popup cards, green for a goal, yellow/red for disciplinary cards, mobile/desktop layouts, close and match-details buttons. Alerts display on all Football News tabs regardless of the currently selected competition; simultaneous updates are queued and shown three at a time.
- Source-limited behavior: when ESPN omits player/minute, display an explicit unknown instead of guessing. No operating-system push outside the Football News panel; ESPN delays/429 can delay or suppress alerts.
- Add parser/coordinator/9-tab browser tests, real Chromium desktop/mobile smoke and release-version consistency checks.

## 2026.11.19.3 — Adaptive Live polling and match events

- Add per-league adaptive scheduling: 300s idle, 150s upcoming, 60s warmup, 30s kickoff, 20s Live by default and 60s for recent FT; live interval configurable to 15/20/30/45/60 seconds in native Options Flow.
- Add ESPN scoreboard day-specific single-flight cache (12s), merge day results by event ID and reconcile full calendar every 5 minutes. ESPN errors preserve last-known-good scores; 429 backoff remains enabled.
- Refresh match timeline and statistics every 15 seconds while Live detail modal is visible; share match summary cache on Home Assistant, stop on close/tab hide, preserve modal scroll.
- Persist only changed football data or periodic heartbeat; prevent duplicate alert processing on unchanged ESPN responses; add adaptive status and settings in diagnostics.
- Keep Home Assistant network-independent at startup. Expand pure-Python policy, provider, coordinator and browser behavior tests.

## 2026.11.19.2 — First-open dashboard bootstrap

- Fix an empty first sidebar visit when HA mounts the panel before assigning `hass` or while a socket request is in flight.
- Keep cold-start retries active even if a companion-app WebView reports `document.hidden`; throttle after leagues are displayed.
- Return a `startup_pending` flag and briefly recheck only the local config-entry registry in the WebSocket handler. Never wait on ESPN during HA startup.
- Announce restored coordinator cache to already-open devices immediately and register WebSocket handlers before exposing the sidebar.
- Bump the frontend module URL to invalidate previously cached JavaScript.

## 2026.11.19.1 — Đồng bộ dữ liệu tập trung Home Assistant (không cache riêng theo thiết bị)

- Bỏ snapshot ESPN, leaderboard và lựa chọn tab/giải/bộ màu khỏi `localStorage`/`sessionStorage`; mọi thiết bị tải chung từ HA WebSocket và cache Store trên máy chủ.
- Thêm `FootballUIState`: giao diện theo từng tài khoản HA được lưu bền vững (revision + field-level patches), chống ghi đè khác trường, kiểm tra dữ liệu đầu vào và xác nhận lưu đĩa trước khi báo thành công.
- Giữ nguyên lưu favorites tại HA Store toàn cục, đồng bộ ngay cho các panel khác qua HA event; hoàn nguyên RAM khi lưu không thành công.
- Phát sự kiện cho dữ liệu từ coordinator và kết quả cầu thủ mới; các panel đang mở tự lấy snapshot máy chủ mới mà không gọi ESPN theo từng trình duyệt.
- Không tăng công việc khi HA khởi động: chỉ đọc dữ liệu UI/favorites khi panel yêu cầu; cập nhật ESPN vẫn sau `homeassistant_started`.
- Bổ sung diagnostics nguồn lưu dữ liệu, log cấp debug/warning có ngữ cảnh, kiểm thử 2 trình duyệt tách biệt và lưu trữ thất bại; giữ cấu trúc HACS/Marketplace 2026.11.

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

