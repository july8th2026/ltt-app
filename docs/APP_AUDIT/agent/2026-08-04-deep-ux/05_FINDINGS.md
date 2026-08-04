# Findings

## Đã đóng trong H20

1. P1 — Edge tồn tại trong server nhưng renderer không vẽ vì node/handle chưa
   initialized. Đã thêm measured geometry + typed handle registry; E3 reload 1/1.
2. P1 — Chạy node bị full-workflow validation chặn bởi node không liên quan.
   Đã lọc issue theo target và transitive prerequisite; E3 tạo awaiting approval.
3. P2 — Chọn reference mới để lại nhiều edge trên cùng input. Đã chuyển thành
   replace semantics; E3 từ 2 edge về 1 edge, state và renderer đồng bộ.
4. P2 — Schema kỹ thuật quyết định UX. Đã có node presentation layer và
   contextual composer; Inspector giữ advanced fields.
5. P2 — Canvas thiếu right-click/quick-create. Đã triển khai và regression test.

## Còn mở sau code gate

1. P2 — Chưa có E4 user task/telemetry cho time-to-first-workflow và tỷ lệ lỗi.
   Acceptance: beta cohort hoàn thành ba JTBD, có task success/time/error metrics.
2. P2 — Chưa smoke bundle H20 trên production vì audit không cấp quyền deploy.
   Acceptance: deploy riêng, health + desktop/mobile + console/network sạch.
3. P3 — Mobile chỉ xem. Đây là omission minh bạch; xem xét authoring sau khi có
   dữ liệu nhu cầu, không đưa vào table stake hiện tại.
4. P3 — Cảnh báo Starlette/httpx deprecation trong test harness. Không ảnh hưởng
   runtime; lên ticket dependency maintenance, không nâng nóng trong H20.
