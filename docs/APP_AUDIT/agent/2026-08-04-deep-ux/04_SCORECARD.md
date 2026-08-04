# LTT-AQA Scorecard — H20 Candidate

## Dashboard

`Q 83 · M 80 · E 82 · BETA`

| Nhóm | Điểm 0–5 | Điểm trọng số |
|---|---:|---:|
| Giá trị sản phẩm/kết quả lõi | 4.0 | 12.00/15 |
| Tính năng và độ đầy đủ | 4.1 | 9.84/12 |
| Đúng chức năng và control | 4.2 | 10.08/12 |
| UX/workflow/IA | 4.1 | 9.84/12 |
| UI/thẩm mỹ/design system | 4.2 | 6.72/8 |
| Responsive/accessibility | 3.9 | 5.46/7 |
| Hiệu năng/độ tin cậy | 4.0 | 7.20/9 |
| AI output/provider economics | 4.2 | 6.72/8 |
| Security/privacy/tenant/credit | 4.5 | 9.00/10 |
| Kiến trúc/vận hành/quan sát | 4.4 | 6.16/7 |
| **Quality** |  | **83.02/100** |

Market: table stakes 82, differentiator 76, làm tròn `M 80`. Evidence `E 82`
vì source/test/browser mạnh nhưng chưa có user task và production telemetry E4.

## Gate

- G0, G2, G3, G4, G5, G6, G8: PASS bằng E2/E3.
- G1: PASS trong phạm vi tạo scoped run trước approval; provider output trả phí
  không chạy trong audit.
- G7: PASS regression/budget hiện có; chưa tuyên bố production percentile.
- PUBLIC/COMMERCIAL chưa mở từ hồ sơ này: cần controlled beta task và smoke sau
  một lệnh deploy production riêng.
