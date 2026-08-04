# LTT-AQA Scorecard — H20 Candidate

> **ĐÃ HẾT HIỆU LỰC CHO RELEASE.** Score này thiếu E4 owner task và đã đánh giá
> quá cao learnability. Baseline thay thế: `../2026-08-04-ux-reset/04_SCORECARD.md`
> (`Q58 · M42 · E93 · BLOCKED`, UX/UI 2,8/10).

## Dashboard

`Q 87 · M 85 · E 89 · BETA`

| Nhóm | Điểm 0–5 | Điểm trọng số |
|---|---:|---:|
| Giá trị sản phẩm/kết quả lõi | 4.0 | 12.00/15 |
| Tính năng và độ đầy đủ | 4.5 | 10.80/12 |
| Đúng chức năng và control | 4.5 | 10.80/12 |
| UX/workflow/IA | 4.5 | 10.80/12 |
| UI/thẩm mỹ/design system | 4.3 | 6.88/8 |
| Responsive/accessibility | 4.0 | 5.60/7 |
| Hiệu năng/độ tin cậy | 4.0 | 7.20/9 |
| AI output/provider economics | 4.4 | 7.04/8 |
| Security/privacy/tenant/credit | 4.6 | 9.20/10 |
| Kiến trúc/vận hành/quan sát | 4.6 | 6.44/7 |
| **Quality** |  | **87.12/100** |

Market: table stakes 88, differentiator 78, làm tròn `M 85`. Evidence `E 89`
vì vòng 3 đã đối chiếu JSON một workflow mua sẵn 13 node/13 edge, dựng lại nhánh
đại diện 8 node/9 edge trên LTT, upload ảnh thật, validate/báo giá server và kiểm
console/network; vẫn chưa có user task và production telemetry E4 nên giữ BETA.

## Gate

- G0, G2, G3, G4, G5, G6, G8: PASS bằng E2/E3.
- G1: PASS trong phạm vi transform thật và workflow đa phương thức đến báo giá;
  provider output trả phí không chạy trong audit.
- G7: PASS regression/budget hiện có; chưa tuyên bố production percentile.
- PUBLIC/COMMERCIAL chưa mở từ hồ sơ này: cần controlled beta task và smoke sau
  một lệnh deploy production riêng.
