# A5 — Scorecard

## Dashboard

**Q 58 · M 56 · E 92 · BLOCKED**

| Nhóm | Trọng số | Điểm 0–5 | Điểm quy đổi | Lý do tóm tắt |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 3.6 | 10.8 | JTBD rõ, pipeline thật; chưa có quality proof |
| Tính năng/độ đầy đủ | 12 | 3.0 | 7.2 | Có highlight→package; thiếu editor/project/publish |
| Đúng chức năng/control | 12 | 2.4 | 5.8 | SRT, cancel, validation và partial state lỗi |
| UX/workflow/IA | 12 | 2.8 | 6.7 | Tương đối rõ; recovery/history/edit còn mỏng |
| UI/design system | 8 | 3.4 | 5.4 | Hierarchy tốt, output dense và score kỹ thuật |
| Responsive/accessibility | 7 | 3.4 | 4.8 | Không overflow; chưa có audit WCAG đầy đủ |
| Performance/reliability | 9 | 2.5 | 4.5 | Range tốt; thiếu deadline/checkpoint/SLO thật |
| AI output/economics | 8 | 3.0 | 4.8 | Có pipeline/actual settle; chưa blind QA/calibration |
| Security/privacy/credit | 10 | 2.4 | 4.8 | Ownership tốt; upload/quote/lifecycle chưa đủ |
| Kiến trúc/ops/observability | 7 | 2.5 | 3.5 | Có job log/test; thiếu per-stage recovery/retention |
| **Tổng** | **100** |  | **58.1 → 58** | Cần nâng cấp lớn |

Market Score 56 vì LTT có pipeline thật và economics hợp lý nhưng thiếu editor, quản trị project, đa nguồn và publish/schedule; correctness hiện tại kéo table stakes xuống. Evidence 92 vì source + 19 targeted test + browser/file thật + ZIP artifact; production SLO, GPU render và user test thật chưa chạy.

## G0–G8

| Gate | Kết quả | Điều kiện mở lại |
|---|---|---|
| G0 Scope | PASS | Charter khóa |
| G1 Core Outcome | FAIL | Render canary thật + MP4/SRT/package đúng |
| G2 Security | FAIL | Signed upload bound size/type, probe, lifecycle/tenant abuse test |
| G3 Money/Credit | FAIL | Quote canonical sau probe; hold/settle/refund/cancel/partial matrix PASS |
| G4 Honest UI | FAIL | Partial/error/cancel/retry và estimate hiển thị đúng sự thật |
| G5 Data Recovery | FAIL | Cooperative cancel, stage timeout/checkpoint/resume và TTL/delete |
| G6 Accessibility | FAIL | WCAG core journey/keyboard/screen-reader evidence |
| G7 Performance | UNKNOWN | GPU/load production-like P50/P95/SLO |
| G8 Operations | FAIL | Metrics/alerts/runbook/artifact retention/release evidence |

Release Gate: `BLOCKED`; không dùng điểm Q để bù gate.
