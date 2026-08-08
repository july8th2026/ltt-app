# A5 — Scorecard H26.9

`Q 76 · M 69 · E 80 · BETA`

| Nhóm | Điểm quy đổi | Lý do chính |
|---|---:|---|
| Giá trị lõi | 12/15 | hai kết quả lõi chạy thật |
| Độ đầy đủ | 9/12 | history có nhưng IA tách |
| Control | 10/12 | validation/credit/ownership tốt |
| UX/workflow/IA | 7/12 | hai full page cho cùng product |
| UI/design system | 6/8 | Carbon Red nhưng shell trùng lặp |
| Responsive/a11y | 6/7 | H15/H26.4 đã có browser evidence |
| Reliability | 7/9 | job/recovery có; H26.9 chưa retest |
| AI/economics | 7/8 | provider/cost rõ, không giả mask |
| Security/privacy/credit | 9/10 | owner + quote/hold/settle/refund |
| Ops/observability | 3/7 | log chung có, chưa có release evidence H26.9 |

Gate trước triển khai: G0/G1/G2/G3/G6 PASS theo evidence cũ; G4 PARTIAL vì một
product nhưng hai shell; G5 PASS; G7 cần retest; G8 BLOCKED tới H26.12.

## Sau triển khai

`Q 85 · M 69 · E 94 · BETA`

| Nhóm | Điểm quy đổi | Evidence sau H26.9 |
|---|---:|---|
| Giá trị lõi | 12/15 | hai outcome thật, không thêm nút giả |
| Độ đầy đủ | 10/12 | một product, hai mode và history xuyên suốt |
| Control | 11/12 | quote trước submit, validation/CSRF/owner giữ nguyên |
| UX/workflow/IA | 10/12 | canonical shell, loading/error/retry và legacy redirect |
| UI/design system | 7/8 | dùng chung Carbon Red shell/mode navigation |
| Responsive/a11y | 7/7 | desktop/mobile không overflow, touch target và ARIA đã test |
| Reliability | 8/9 | queue/error/history/remix regression + full gate |
| AI/economics | 7/8 | hai cost model thật, không nhập nhằng executor |
| Security/privacy/credit | 9/10 | owner-scoped fragment/remix, hold/settle/refund không đổi |
| Ops/observability | 4/7 | job/log và release evidence có; production canary còn khóa |

Market giữ 69 vì H26.9 không bổ sung benchmark thị trường hay engine mới. Gate
G0–G7 PASS trong phạm vi development; G8 vẫn BLOCKED đến H26.12 vì chưa deploy,
chưa canary production và chưa chạy rollback thật.
