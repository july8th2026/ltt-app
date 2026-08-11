# H32.2 — Scorecard: Prompt AI OMMI

- **Quality Score: 72/100** (trước sửa carry-forward 48/100)
- **Market Score: 68/100**
- **Evidence Confidence: 86/100**
- **Release Gate: CONDITIONAL** — core composer pass; provider E4 chưa có.

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Nhận xét |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 3.7 | 11.1 | Prompt deterministic tốt; AI output chưa canary |
| Tính năng/độ đầy đủ | 12 | 4.0 | 9.6 | 8 style/4 meta/4 snippet đã usable |
| Chức năng/control | 12 | 4.1 | 9.8 | Save/preview/quote/apply contract pass |
| UX/workflow/IA | 12 | 3.8 | 9.1 | Luồng rõ, còn dài và thiếu onboarding |
| UI/design system | 8 | 3.5 | 5.6 | Đồng nhất; preview dễ kiểm, chưa đạt mockup polish |
| Responsive/accessibility | 7 | 3.3 | 4.6 | Mobile không overflow; chưa audit bàn phím/AT sâu |
| Hiệu năng/tin cậy | 9 | 4.0 | 7.2 | Loại 7 redirect GET; revision fail-closed |
| AI/economics | 8 | 2.8 | 4.5 | Quote 6 credit; provider/settlement chưa chứng minh |
| Security/privacy/credit | 10 | 4.0 | 8.0 | owner-scoped catalog/private, không copy DB nguồn |
| Kiến trúc/ops/log | 7 | 2.9 | 4.1 | Test tốt; thiếu trace UI theo project |

Tổng: **71,6 → 72/100**.

Gate: G0 PASS · G1 CONDITIONAL · G2 PASS sampled · G3 PARTIAL · G4 PASS ·
G5 PASS revision · G6 PARTIAL · G7 PASS sampled · G8 PARTIAL.
