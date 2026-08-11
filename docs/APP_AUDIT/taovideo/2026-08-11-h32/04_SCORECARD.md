# H32.5 — Scorecard: Tạo Video Seedance

- **Quality Score: 63/100** (baseline deep audit 57).
- **Market Score: 64/100** (không có market evidence mới).
- **Evidence Confidence: 84/100** (E3 UI rộng; kế thừa một E4 canary; không
  chạy provider H32.5).
- **Release Gate: BLOCKED** bởi P0 billing/canonical quote của audit 2026-08-09.

| Nhóm | Trọng số | 0–5 | Quy đổi | Nhận xét |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 3.5 | 10.5 | Kế thừa canary; không test job vòng này |
| Tính năng/độ đầy đủ | 12 | 3.3 | 7.9 | Input/history mạnh; recovery/edit thiếu |
| Chức năng/control | 12 | 3.2 | 7.7 | State chính live; Remix/cancel/retry gap |
| UX/workflow/IA | 12 | 3.3 | 7.9 | Composer+dock/library rõ hơn |
| UI/design system | 8 | 4.1 | 6.6 | Bám reference, Carbon Red nhất quán |
| Responsive/accessibility | 7 | 4.0 | 5.6 | Inert, close/focus, VI/EN, no overflow |
| Hiệu năng/tin cậy | 9 | 3.0 | 5.4 | UI nhẹ; upload/progress vẫn nợ |
| AI/provider economics | 8 | 2.1 | 3.4 | Không evidence mới; billing blocker |
| Security/privacy/credit | 10 | 1.8 | 3.6 | Owner/CSRF tốt; P0/P1 cũ còn |
| Kiến trúc/ops/log | 7 | 3.2 | 4.5 | Job log có; lifecycle/reconcile thiếu |

Tổng **63,1**, làm tròn **63**.

Gate: G0 PASS · G1 PASS có điều kiện · G2 FAIL · G3 FAIL P0 · G4 PARTIAL ·
G5 FAIL · G6 PASS phạm vi H32.5 · G7 UNKNOWN · G8 FAIL.

Test: 50 targeted pass; browser desktop/mobile VI/EN pass; quote 500 negative
pass; quick/full gate ghi sau khi chạy thật ở nhật ký/master plan.
