# H27 — Portfolio DEEP audit dashboard

> **Hiệu chỉnh H28 (2026-08-09):** Q, finding và Gate vẫn giữ; các điểm E cũ
> 84–95 không hợp lệ vì đã gắn source/test/browser thành E4. Bảng dưới đã dùng
> lại đúng E1/E2/E3. Trạng thái “DONE” của H27 chỉ là đủ file first-pass, không
> phải mọi A0–A10 đều PASS. Xem `../2026-08-09-reaudit/`.

Ngày snapshot: **2026-08-09**. Nguồn chuẩn: `docs/quy_tac_audit.md` và hồ sơ
00–07 của từng app. Đây là audit-only; không đồng nghĩa code đã được sửa.

## Mức phủ

- **13/13 manifest đã kiểm kê.** Thumbnail là child mode của Tạo ảnh, được audit
  chung nhưng có finding/giá/control riêng.
- **12/12 hồ sơ sản phẩm/runtime** có charter, truth map, control registry,
  benchmark, Q/M/E/Gate, findings, options và roadmap.
- Raw inventory: **248 finding = 3 P0 · 45 P1 · 146 P2 · 54 P3**.
- 8 customer product chính: Q trung bình **53,8**, M **53,4**, E **59,9**;
  cả 8 đều BLOCKED khi xét độc lập theo LTT-AQA.

## Bảng chấm điểm

| App/phạm vi | Q | M | E | Gate | P0/P1/P2/P3 | Hồ sơ |
|---|---:|---:|---:|---|---|---|
| Upscale Video | 64 | 57 | 61 | BLOCKED | 0/2/10/4 | `upscalevideo/2026-08-09` |
| Seedance Video | 57 | 64 | 61 | BLOCKED | 0/3/11/4 | `taovideo/2026-08-09` |
| Auto Sub | 56 | 65 | 61 | BLOCKED | 0/3/14/5 | `autosubvideo/2026-08-09` |
| Prompt AI OMMI | 48 | 51 | 56 | BLOCKED | 0/5/14/6 | `prompt-ai-ommi/2026-08-09` |
| Tạo ảnh + Thumbnail | 56 | 54 | 60 | BLOCKED | 0/3/15/6 | `taoanh/2026-08-09-deep` |
| Tạo Clip ngắn | 58 | 56 | 61 | BLOCKED | 0/4/15/5 | `taoclipngan/2026-08-09-deep` |
| Chat AI Studio | 48 | 42 | 58 | BLOCKED | 0/7/17/5 | `chataistudio/2026-08-09-deep` |
| LTT Agent AI | 43 | 38 | 61 | BLOCKED | 1/7/18/6 | `agent/2026-08-09-deep` |
| Socialbot maintenance | 41 | 35* | 60 | BLOCKED | 2/5/8/4 | `_luutru/2026-09/…/socialbot/2026-08-09-maintenance` (lưu trữ) |
| Demo hạ tầng | 78 | 70* | 40 | INTERNAL | 0/0/5/2 | `_luutru/2026-09/…/demo/2026-08-09-contract` (lưu trữ, app đã gỡ) |
| Kịch bản/Text runtime | 64 | 50* | 38 | BLOCKED | 0/2/8/3 | `_luutru/2026-09/…/kichban/2026-08-09-contract` (lưu trữ, app đã gỡ) |
| Media Tools runtime | 59 | 47* | 38 | BLOCKED | 0/4/11/4 | `_luutru/2026-09/…/mediatools/2026-08-09-contract` (lưu trữ) |

`M*` là provisional: benchmark H27 chưa đủ source/snapshot matrix theo A4. M70
của Demo là độ phù hợp synthetic-canary contract, không phải market score app.

## Ba P0 phải dừng đường phát hành

1. **Agent:** một Text→Image có thể tạo hai child text và tính gấp đôi step.
2. **Socialbot:** customer thường có thể xem/sửa/xóa token dùng chung toàn hệ.
3. **Socialbot:** customer thường có thể start/stop worker/reset monitor global.

## Cách đọc đúng

H26 chứng minh bản đang deploy có thể chạy một số canary. H27 trả lời câu khác:
app có đủ an toàn, trung thực, phục hồi và cạnh tranh để mở rộng commercial hay
không. Vì vậy `deployed/public` không tự biến Gate H27 thành PASS.
