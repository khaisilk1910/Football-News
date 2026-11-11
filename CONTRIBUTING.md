# Đóng góp / Contributing

1. Mở issue mô tả tính năng/lỗi, ghi rõ phiên bản Home Assistant và giải đấu.
2. Tạo nhánh riêng, chỉnh sửa code mới thuộc Football News; **không chép** mã/tài sản từ Football Hub hoặc dự án có giấy phép không tương thích.
3. Chạy `python -m unittest discover -s tests -p 'test_*.py' -v` và `node --check custom_components/football_news/frontend/panel.js`.
4. Giữ bản dịch `translations/en.json`, `translations/vi.json` đồng bộ; viết thông báo không chứa dữ liệu cá nhân.
5. Đợi CI `Validate Football News` thành công trước khi merge hoặc tag release.

Mọi đóng góp trong repo MIT này được cấp phép lại theo MIT.
