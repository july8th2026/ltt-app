# Phase và PASS gate bắt buộc

## Template cho mỗi app

| Phase | Nội dung | PASS bắt buộc |
|---|---|---|
| P0 Repair | P0/P1 security, money, core, loss | không P0; G1/G2/G3/G5 theo scope; abuse/race test |
| P1 Core | table stakes + honest controls | core journey E3; mọi paid control có quote/receipt/error |
| P2 UX/UI | IA, design, responsive, a11y | desktop/mobile/keyboard; console/network sạch; no DEAD/MISLEADING |
| P3 Parity | market gap chọn lọc | capability acceptance + cost/ops/rollback; không build-all |
| P4 Ops | perf/provider/output/telemetry | P50/P95, success/cost, alert/runbook, backup/restore |
| P5 Release | regression/canary/deploy evidence | `python tools\\gate.py`; authenticated browser; rollback rehearsal; owner sign-off |

## Definition of Done cho một finding

`evidence → root cause → smallest fix → unit/integration → browser E3 →
regression → metric/alert nếu cần → nhật ký → commit`. Chỉ đổi FAIL thành PASS
khi acceptance gốc trong `05_FINDINGS.md` được chứng minh.

## Definition of Done cho một app

- Control Registry không còn DEAD/MISLEADING ở core/paid journey.
- P0=0; P1 release blocker=0; UNKNOWN quan trọng có owner/evidence plan.
- G0–G8 đạt mức release đã khóa; không lấy Q trung bình bù Gate FAIL.
- Q/M được chấm lại độc lập; E không giảm vì mất browser/provider evidence.
- Targeted tests + quick gate trong vòng lặp; full gate chỉ ở P5 hoặc thay đổi
  shared/high-risk phù hợp.
- Browser desktop/mobile/locale/keyboard, console errors và failed requests đã
  kiểm trên build thật.
- Rollback và data migration/restore được diễn tập khi có schema/storage.

## Portfolio Gate

Không gọi “hoàn tất toàn bộ” khi chỉ code xong. Portfolio chỉ sẵn sàng
commercial khi: 3 P0 đóng; shared contract ổn; từng customer app qua P5; SLO và
provider authorization có evidence; full gate + backup/restore + canary PASS.

