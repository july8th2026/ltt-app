# Asset directory

## Required: TikTok official branding

TikTok yêu cầu app dùng **logo chính thức** (không phải emoji) trên nút Login Kit
để được audit duyệt.

### Bước 1 — Tải logo
1. Vào [TikTok Developer Branding Kit](https://developers.tiktok.com/doc/getting-started-create-an-app#branding-guidelines)
2. Tải `TikTok-Logo-Round.png` (hoặc tên tương đương — phiên bản logo tròn nhỏ)
3. Lưu vào folder này với tên chính xác:

```
data/assets/tiktok_logo.png
```

### Bước 2 — Yêu cầu kỹ thuật
- Format: PNG (RGBA, có alpha)
- Kích thước khuyến nghị: **24×24px** đến **48×48px**
- Tỉ lệ: vuông
- Background: trong suốt
- KHÔNG được crop / chỉnh sửa logo

### Behavior khi thiếu file
Bot vẫn chạy được — nút Login sẽ hiển thị text-only `"Continue with TikTok"`
không có logo. Nhưng audit của TikTok có thể từ chối nếu thấy thiếu branding.

### Các logo khác (optional)
- `tiktok_logo_white.png` — version dùng cho dark theme (24×24 px)
- `tiktok_logo_black.png` — version dùng cho light theme

Nếu chỉ có 1 file, code dùng `tiktok_logo.png` cho mọi trường hợp.
