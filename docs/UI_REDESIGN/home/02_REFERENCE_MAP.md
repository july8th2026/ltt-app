# UI-RD — Bản đồ ảnh tham khảo trang chủ

## Bố cục desktop

| Vùng | Tỷ lệ ảnh | Nội dung thấy được | Độ chắc chắn |
|---|---:|---|---|
| Sidebar trái | ~7% | Logo; Marketplace, My Apps, Workspace, Templates, Resources, Community, Settings | V |
| Top command bar | ~75% ngang | Search, filter, sort, credit, avatar/profile | V |
| Category rail | ~75% ngang | All, AI Video/Image, Chat & Prompt, Audio, Automation, Design, Marketing, Developer, Utilities, Add | V |
| Marketplace grid | ~75% ngang | 5 cột card compact, artwork, badge, description, usage, CTA | V |
| Right rail | ~17% | recent activity, jobs running/progress, Pro upsell | V |
| Responsive mobile | không có ảnh | cần drawer/sidebar collapse và one/two-column grid | S |

## Design language

- Dark near-black, panel black/charcoal, line/border đỏ-cam, glow đỏ vừa phải.
- Logo/artwork hướng sci-fi neon; card 3 tầng: artwork, nội dung, CTA/meta.
- Mật độ desktop cao: 5 cột card, sidebar cố định, right rail cố định/sticky.
- Hệ thống nhãn rõ: Popular, New, Pro, Beta; CTA nhỏ nhưng nhất quán.

## Không suy diễn từ ảnh

“lượt dùng”, badge Pro, activity, progress và tên app trong ảnh có thể là data
minh họa. Không được đưa số giả vào production; mỗi phần cần map sang dữ liệu thật
hoặc bị ẩn/defer.
