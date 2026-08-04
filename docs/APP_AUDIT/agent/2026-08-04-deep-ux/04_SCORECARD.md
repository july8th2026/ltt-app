# LTT-AQA Scorecard — H20 Candidate

## Dashboard

`Q 85 · M 82 · E 84 · BETA`

| Nhóm | Điểm 0–5 | Điểm trọng số |
|---|---:|---:|
| Giá trị sản phẩm/kết quả lõi | 4.0 | 12.00/15 |
| Tính năng và độ đầy đủ | 4.3 | 10.32/12 |
| Đúng chức năng và control | 4.4 | 10.56/12 |
| UX/workflow/IA | 4.4 | 10.56/12 |
| UI/thẩm mỹ/design system | 4.3 | 6.88/8 |
| Responsive/accessibility | 4.0 | 5.60/7 |
| Hiệu năng/độ tin cậy | 4.0 | 7.20/9 |
| AI output/provider economics | 4.2 | 6.72/8 |
| Security/privacy/tenant/credit | 4.5 | 9.00/10 |
| Kiến trúc/vận hành/quan sát | 4.4 | 6.16/7 |
| **Quality** |  | **85.00/100** |

Market: table stakes 84, differentiator 79, làm tròn `M 82`. Evidence `E 84`
vì re-audit vòng 2 có thao tác control sâu, source/test/full regression/browser
desktop-mobile; vẫn chưa có user task và production telemetry E4 nên giữ BETA.

## Gate

- G0, G2, G3, G4, G5, G6, G8: PASS bằng E2/E3.
- G1: PASS trong phạm vi tạo scoped run trước approval; provider output trả phí
  không chạy trong audit.
- G7: PASS regression/budget hiện có; chưa tuyên bố production percentile.
- PUBLIC/COMMERCIAL chưa mở từ hồ sơ này: cần controlled beta task và smoke sau
  một lệnh deploy production riêng.
