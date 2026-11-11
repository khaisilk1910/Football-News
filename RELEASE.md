# Phát hành Football News trên Marketplace (Home Assistant 2026.11+)

## Vì sao từng gặp lỗi 404?

Bản đầu có `zip_release: true` trong `hacs.json`. Marketplace buộc phải tải
`football_news.zip` ở mỗi GitHub Release. Release `v2026.11.11.1` không có asset
đúng tên tại đường dẫn được log ghi lại, nên cài đặt thất bại trước bước cài Python.

Từ **v2026.11.11.2**, `hacs.json` bỏ `zip_release`/`filename`. Marketplace đọc
trực tiếp `custom_components/football_news` từ repository/tag. File ZIP tiếp tục
được tạo đính kèm GitHub Release để tải về **cài thủ công**, không còn là điều kiện
bắt buộc cho cài đặt Marketplace.

## Bước 1 — Đẩy ĐẦY ĐỦ repository lên GitHub

1. Giải nén `Football-News-repository.zip` và mở thư mục `Football-News` bên trong.
2. Sao chép **tất cả nội dung** vào bản Git clone của `khaisilk1910/Football-News`.
   Bao gồm `.github/workflows/release.yml`, `.github/workflows/validate.yml`,
   `.gitignore`, `hacs.json`, `README.md`, `custom_components/football_news/`.
3. Xóa các thư mục/file Football Hub cũ không có trong ZIP mới (đặc biệt
   `custom_components/football_hub/`, nếu vẫn tồn tại). Không giữ hai integration
   trong `custom_components/`, vì Marketplace có thể chọn sai domain.
4. Dùng Git (khuyến nghị) để bảo toàn các file/thư mục ẩn. **Không** tải nguyên
   ZIP lên GitHub như một file rồi kỳ vọng Marketplace tự giải nén.

Trong bản clone đã chứa mã nguồn mới, chạy:

```bash
python scripts/check_marketplace.py
python -m unittest discover -s tests -p 'test_*.py' -v
git add -A
git commit -m "Fix Marketplace install for Football News 2026.11.11.2"
git push origin main
```

Nếu `git status` báo không có thay đổi, kiểm tra lại rằng bạn đã giải nén đúng
nội dung vào clone và cả `.github/` lẫn `.gitignore` đã được đưa vào Git.

## Bước 2 — Tạo tag mới, không tái sử dụng tag cũ

**Sau khi** commit đã có trên nhánh `main` và CI thành công:

```bash
git tag -a v2026.11.11.2 -m "Football News v2026.11.11.2"
git push origin v2026.11.11.2
```

Tag **phải trỏ đến commit đã có mã mới**, chứa:

- `custom_components/football_news/manifest.json` có `"version": "2026.11.11.2"`
- `custom_components/football_news/const.py` có `VERSION = "2026.11.11.2"`
- `hacs.json` **không có** `zip_release: true` hoặc `filename`.
- `.github/workflows/release.yml` được commit đầy đủ.

GitHub Actions `Release Football News` sẽ kiểm tra tag, chạy unit tests,
đóng gói `football_news.zip` và tạo Release. Nếu đã có Release nhưng thiếu file
ZIP, vào **Actions → Release Football News → Run workflow**, nhập
`v2026.11.11.2`. Workflow sẽ upload lại asset đúng tên. Quyền `GITHUB_TOKEN`
phải cho phép `contents: write` để tạo/update Release.

Kiểm tra tại: https://github.com/khaisilk1910/Football-News/releases

> Không sửa hoặc đẩy lại tag `v2026.11.11.1` đang được phát hành; dùng bản mới.

## Bước 3 — Cài qua Marketplace

1. Home Assistant → **Settings → Marketplace**.
2. Tìm repository **Football News**. Nếu chưa có: **Add from link** và thêm
   `https://github.com/khaisilk1910/Football-News`.
3. Làm mới trang/repository để lấy phiên bản mới. Nếu vẫn thấy tag cũ, thử đóng
   và mở lại Marketplace; custom repository được đồng bộ theo chu kỳ, nên có thể
   chưa xuất hiện ngay.
4. Chọn phiên bản `v2026.11.11.2`, **Install**.
5. Mở **Settings → Devices & services → Add integration → Football News**.

Nếu giao diện vẫn cố tải `releases/download/v2026.11.11.1/football_news.zip`,
đó là metadata/phiên bản cũ: phải kiểm tra Release mới **đã được xuất bản** và
Marketplace đã nhận phiên bản mới. Không thể sửa bản cài cũ chỉ bằng cập nhật
`hacs.json` trên `main` nếu Marketplace vẫn chọn tag cũ.

## Cài thủ công khi chưa phát hành xong

Giải nén `football_news.zip` (các file `manifest.json`, `__init__.py`, v.v.
nằm ngay root của ZIP) vào:

```text
/config/custom_components/football_news/
```

Sau đó khởi động lại Home Assistant. Không chép nguyên tệp `football_news.zip`
vào thư mục integration và không thêm một tầng `football_news/football_news`.

## Kiểm tra khi có lỗi tiếp theo

- HTTP 404: sai tên/thông tin Release hoặc Marketplace vẫn dùng metadata cũ.
- Domain sai: xem lại chỉ có `custom_components/football_news` và manifest hợp lệ.
- Tải thành công nhưng setup lỗi: vào Settings → System → Logs, lọc
  `custom_components.football_news`; đây là giai đoạn khác với lỗi 404.
- Theo dõi kết quả GitHub Actions tại
  https://github.com/khaisilk1910/Football-News/actions
