# H27 — Portfolio DEEP audit dashboard

Ngày snapshot: **2026-08-09**. Nguồn chuẩn: `docs/quy_tac_audit.md` và hồ sơ
00–07 của từng app. Đây là audit-only; không đồng nghĩa code đã được sửa.

## Mức phủ

- **13/13 manifest đã kiểm kê.** Thumbnail là child mode của Tạo ảnh, được audit
  chung nhưng có finding/giá/control riêng.
- **12/12 hồ sơ sản phẩm/runtime** có charter, truth map, control registry,
  benchmark, Q/M/E/Gate, findings, options và roadmap.
- Raw inventory: **248 finding = 3 P0 · 45 P1 · 146 P2 · 54 P3**.
- 8 customer product chính: Q trung bình **53,8**, M **53,4**, E **90,6**;
  cả 8 đều BLOCKED khi xét độc lập theo LTT-AQA.

## Bảng chấm điểm

| App/phạm vi | Q | M | E | Gate | P0/P1/P2/P3 | Hồ sơ |
|---|---:|---:|---:|---|---|---|
| Upscale Video | 64 | 57 | 84 | BLOCKED | 0/2/10/4 | `upscalevideo/2026-08-09` |
| Seedance Video | 57 | 64 | 87 | BLOCKED | 0/3/11/4 | `taovideo/2026-08-09` |
| Auto Sub | 56 | 65 | 90 | BLOCKED | 0/3/14/5 | `autosubvideo/2026-08-09` |
| Prompt AI OMMI | 48 | 51 | 92 | BLOCKED | 0/5/14/6 | `prompt-ai-ommi/2026-08-09` |
| Tạo ảnh + Thumbnail | 56 | 54 | 91 | BLOCKED | 0/3/15/6 | `taoanh/2026-08-09-deep` |
| Tạo Clip ngắn | 58 | 56 | 92 | BLOCKED | 0/4/15/5 | `taoclipngan/2026-08-09-deep` |
| Chat AI Studio | 48 | 42 | 94 | BLOCKED | 0/7/17/5 | `chataistudio/2026-08-09-deep` |
| LTT Agent AI | 43 | 38 | 95 | BLOCKED | 1/7/18/6 | `agent/2026-08-09-deep` |
| Socialbot maintenance | 41 | 35 | 94 | BLOCKED | 2/5/8/4 | `socialbot/2026-08-09-maintenance` |
| Demo hạ tầng | 78 | 70* | 92 | INTERNAL | 0/0/5/2 | `demo/2026-08-09-contract` |
| Kịch bản/Text runtime | 64 | 50 | 91 | BLOCKED | 0/2/8/3 | `kichban/2026-08-09-contract` |
| Media Tools runtime | 59 | 47 | 90 | BLOCKED | 0/4/11/4 | `mediatools/2026-08-09-contract` |

`M70*` của Demo là độ phù hợp với synthetic-canary contract, không phải market
score của một app customer.

## Ba P0 phải dừng đường phát hành

1. **Agent:** một Text→Image có thể tạo hai child text và tính gấp đôi step.
2. **Socialbot:** customer thường có thể xem/sửa/xóa token dùng chung toàn hệ.
3. **Socialbot:** customer thường có thể start/stop worker/reset monitor global.

## Cách đọc đúng

H26 chứng minh bản đang deploy có thể chạy một số canary. H27 trả lời câu khác:
app có đủ an toàn, trung thực, phục hồi và cạnh tranh để mở rộng commercial hay
không. Vì vậy `deployed/public` không tự biến Gate H27 thành PASS.

