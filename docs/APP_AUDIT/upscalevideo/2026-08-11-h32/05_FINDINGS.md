# H32.6 — Findings: Upscale Video

## Đã sửa

| ID | Sev | Hiện tượng/root cause | Kết quả |
|---|---|---|---|
| H32-U01 | P1 | Smooth lấy base 30 khi preserve off nên 24→60 | Source cadence 24→48; test/runtime pass |
| H32-U02 | P1 | Manifest giữ 4 GB trong khi Quality peak 11.176 MB | Reserve 12.000 MB cho job type hiện tại |
| H32-U03 | P2 | Mobile panel ẩn nhưng control vẫn tabbable | inert/aria-hidden/focus return pass |
| H32-U04 | P2 | Revoke blob khi metadata request chưa dứt | detach/load/delayed revoke; network pass |
| H32-U05 | P2 | Fake `PRO`, R2/CORS jargon, raw worker message | bỏ/đổi customer copy và localized state |
| H32-U06 | P2 | Không có lối vào full history/log từ app | thêm History và Activity log |

## Còn mở

| ID | Sev | Finding | Acceptance |
|---|---|---|---|
| SEC-01 | P1 | Presigned upload thiếu policy size/type/quota/rate/session hoàn chỉnh | Abuse matrix + staged key TTL PASS |
| DATA-02 | P1 | Upload/artifact mồ côi, retention chưa khép kín | promote/cleanup/sweeper idempotent |
| QLT-03 | P1 | Chất lượng thị giác chưa calibrate; reference hiện là Lanczos, không HR truth | Bộ HR đa thể loại + blind panel + threshold version |
| CORE-04 | P2 | Spatial Real-ESRGAN chưa denoise/deblur/temporal | Benchmark có quality/cost/P95 trước BUILD |
| UX-05 | P2 | Queue trong app tĩnh; thiếu retry/full pagination | live state + retry idempotent + history cursor |
| OPS-06 | P2 | Job type chung buộc Fast giữ 12 GB | tách Fast/Quality type và scheduler regression |
| PERF-07 | P2 | Current dual-GPU test bị GPU0 external workload chặn | chạy lại khi cả hai GPU idle, không cưỡng dừng workload |
| UX-08 | P2 | Quote thiếu runtime/output-size range và confirm giá cao | canonical preflight + confirmation |
| PERF-09 | P3 | Card video tạo metadata Range lặp | poster/lazy load, đo request/bytes trước-sau |
| UX-10 | P3 | Preview chưa chọn đoạn đại diện | timeline in-point + quote/contract |

Không có P0 mới. Technical option matrix PASS không mở release gate của
SEC-01/DATA-02/QLT-03.

