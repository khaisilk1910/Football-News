# Changelog — Football News

## 2026.11.11.2 — 2026-11-11

- Sửa cài đặt Marketplace 404: bỏ yêu cầu `zip_release`, dùng cấu trúc nguồn chuẩn `custom_components/football_news`.
- Vẫn tạo `football_news.zip` đính kèm GitHub Release để tải và cài thủ công.
- Tự kiểm tra đồng bộ phiên bản Git tag, `manifest.json`, `const.py` và cấu trúc repository.
- Bổ sung workflow phát hành hỗ trợ chạy lại thủ công và tài liệu RELEASE.md.


## 1.0.1 — 2026-11-11

- Thiết kế lại icon bóng đá, biểu tượng Home Assistant, báo NEWS với tông đỏ–vàng.
- Thay bảng màu giao diện Football News sang đỏ đô, đỏ và vàng kim.
- Bổ sung giải thích vị trí file ẩn `.gitignore` và sự khác biệt giữa ZIP repository/ZIP phát hành.
- Cập nhật `manifest.json` và `const.py` cùng phiên bản 1.0.1.

## 1.0.0 — 2026-11-11

- Ra mắt tích hợp Football News **được viết độc lập** (domain `football_news`).
- Dashboard navy/cyan và icon mới, giao diện tiếng Việt và tiếng Anh.
- Lịch thi đấu, tỷ số trực tiếp, kết quả, bảng xếp hạng và tin tức qua nguồn ESPN công khai.
- Zalo Bot: nhắc lịch, bắt đầu trận, kết quả, tin mới, tin thử; rich text theo README Zalo.
- Tải dữ liệu nền sau HA startup, giới hạn polling và cache theo loại dữ liệu.
- Bổ sung diagnostics, unit tests, workflow validate, phát hành ZIP cho Marketplace/HACS.

**Giới hạn:** Bản 1.0.0 chưa tái tạo các tính năng nâng cao của Football Hub, chưa được xác nhận tương thích qua chạy thử HA/Zalo thực tế.
