# LTT-AQA Scorecard — UX Reset baseline

## Dashboard

`Q 58 · M 42 · E 93 · BLOCKED`

| Nhóm | Điểm 0–5 | Điểm trọng số |
|---|---:|---:|
| Giá trị sản phẩm/kết quả lõi | 2.0 | 6.00/15 |
| Tính năng và độ đầy đủ | 3.2 | 7.68/12 |
| Đúng chức năng và control | 3.2 | 7.68/12 |
| UX/workflow/IA | 1.3 | 3.12/12 |
| UI/thẩm mỹ/design system | 1.5 | 2.40/8 |
| Responsive/accessibility | 2.4 | 3.36/7 |
| Hiệu năng/độ tin cậy | 4.0 | 7.20/9 |
| AI output/provider economics | 3.4 | 5.44/8 |
| Security/privacy/tenant/credit | 4.6 | 9.20/10 |
| Kiến trúc/vận hành/quan sát | 4.4 | 6.16/7 |
| **Quality** |  | **58.24/100** |

UX + UI riêng là `5,52/20 = 27,6/100`, khớp phản hồi 3/10. Evidence cao vì có
production canary, PlenX E3, source và tài liệu chính thức; chưa có five-user
task/telemetry nên không chấm E4 đầy đủ.

## Gate

- G0 inventory: PASS.
- G1 happy path: FAIL về learnability dù API/graph chạy.
- G2 control: FAIL vì scope Run và connection destination mơ hồ.
- G3 UX/UI: FAIL.
- G4 responsive/accessibility: CONDITIONAL; render không overflow nhưng density
  và focus hierarchy chưa đạt product acceptance.
- G5–G8 runtime/security/ops: PASS trong phạm vi đã kiểm.
- Release: `BLOCKED`; backend tốt không được bù điểm cho failure G1–G3.
