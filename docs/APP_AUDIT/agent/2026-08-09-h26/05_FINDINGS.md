# 05 — Findings

## Đã đóng trong code hiện tại

- F-AG-01 (P1): mental model dev lộ ra khách hàng → bốn creative block và chế
  độ đơn giản mặc định theo Q68.
- F-AG-02 (P1): Run node dễ bị hiểu là chạy toàn flow → drawer hiển thị target,
  dependency closure, số bước và giá tối đa trước confirm.
- F-AG-03 (P1): canvas/mobile chật → shell full viewport; 390 px không overflow.
- F-AG-04 (P1): theme không ổn định → dark mặc định, preference lưu theo user.

## Còn mở, không vá đoán trong H26.10C

| ID | Mức | Finding | Acceptance |
|---|---|---|---|
| F-AG-05 | P1 | Chưa có load/soak và P95 mới | Budget H26.11 đạt, có artifact máy đọc |
| F-AG-06 | P1 | Chưa drill worker/provider timeout/recovery thật | Không mất project/credit, retry có giới hạn |
| F-AG-07 | P2 | Chưa có task-success từ user thật | Canary có completion/time-to-result/support metric |

Không phát hiện bug chức năng mới trong browser delta. Không sửa code chỉ để
tạo cảm giác đang tiến triển khi evidence không chỉ ra lỗi.
