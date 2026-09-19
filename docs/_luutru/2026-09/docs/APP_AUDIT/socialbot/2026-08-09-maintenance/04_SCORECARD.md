# 04 — Scorecard

## Dashboard

**Q41 · M35 · E60 · BLOCKED** — E94 cũ được hiệu chỉnh ở H28.

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Evidence |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 2.5 | 7.5 | E1–E2 |
| Tính năng/độ đầy đủ | 12 | 2.5 | 6.0 | E1–E3 |
| Function/control | 12 | 1.5 | 3.6 | E1–E3 |
| UX/workflow/IA | 12 | 2.0 | 4.8 | E3 |
| UI/design system | 8 | 2.0 | 3.2 | E3 |
| Responsive/a11y | 7 | 1.5 | 2.1 | E1 |
| Reliability | 9 | 2.5 | 4.5 | E2 |
| Security/privacy/tenant/credit | 14 | 0.5 | 1.4 | E1–E3 |
| Architecture/operations | 11 | 3.5 | 7.7 | E1–E2 |
| **Tổng** | **100** |  | **40.8 → 41** | |

## Gates

| Gate | Kết quả | Lý do |
|---|---|---|
| G0 | PASS | operator-only scope đã khóa |
| G1 | UNKNOWN | không publish provider thật trong audit |
| G2 | **FAIL** | customer sửa token/worker global |
| G3 | PASS/N/A | app nội bộ không thu credit |
| G4 | **FAIL** | UI tự trình bày như customer app dù quyền operator |
| G5 | FAIL | state global, không project/job recovery chuẩn |
| G6 | UNKNOWN | chưa đủ a11y journey |
| G7 | UNKNOWN | không telemetry P75 |
| G8 | FAIL | thiếu tenant audit/alert/runbook cho access abuse |

Evidence: `evidence/01-ordinary-user-facebook-token-admin.png`, source và 411
targeted tests. E60 vì ranh giới lỗi được thấy ở E3 nhưng các nhóm khác chỉ
được E1/E2; production provider còn
UNKNOWN.
