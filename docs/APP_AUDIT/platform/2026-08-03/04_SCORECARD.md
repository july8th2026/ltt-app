# 04 — Scorecard toàn nền tảng

## Dashboard

- **Quality Score Q:** 70/100
- **Market Score M:** 50/100
- **Evidence Confidence E:** 86/100
- **Current production:** đang PUBLIC.
- **Readiness khuyến nghị:** **BLOCKED cho lần nâng cấp thương mại kế tiếp** bởi
  G6 accessibility/mobile và F-001 website live/source mismatch; không có kết
  luận phải tắt production hiện hành.

## Quality

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Bằng chứng chính |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 3.8 | 11.4 | 9 app public có workflow thật |
| Tính năng/độ đầy đủ | 12 | 3.0 | 7.2 | app lõi đủ, market gap rộng |
| Chức năng/control | 12 | 3.7 | 8.9 | route/test/browser; label/target debt |
| UX/workflow/IA | 12 | 3.2 | 7.7 | shell và workflow đổi theo app |
| UI/thẩm mỹ/design system | 8 | 2.8 | 4.5 | bốn ngôn ngữ thị giác |
| Responsive/accessibility | 7 | 2.2 | 3.1 | overflow 48 px, target nhỏ, thiếu label |
| Hiệu năng/tin cậy | 9 | 3.8 | 6.8 | queue/retry/canary mạnh; chưa đo CWV field lượt này |
| AI/provider economics | 8 | 3.4 | 5.4 | quote/settle và provider thật; feature depth lệch |
| Security/privacy/tenant/credit | 10 | 4.5 | 9.0 | audit/test/canary trước đó mạnh |
| Kiến trúc/ops/observability | 7 | 4.2 | 5.9 | test, health, logs, backup/rollback |
| **Tổng** | **100** | | **69.9 ≈ 70** | |

## Điểm app/bề mặt để ưu tiên, không thay scorecard chi tiết từng app

| Bề mặt | Q | M | E | Nhận định |
|---|---:|---:|---:|---|
| Public/Auth/Commerce | 64 | 52 | 88 | logic ổn; brand/a11y/website gap |
| Home authenticated | 76 | 58 | 92 | style đích tốt; placeholder/nav cần dọn |
| Agent/Canvas | 76 | 54 | 88 | runtime mạnh; product workflow gap |
| Auto Sub | 82 | 68 | 93 | app hoàn thiện nhất, a11y/capability polish |
| Upscale | 80 | 48 | 94 | vận hành mạnh, enhancement portfolio hẹp |
| Tạo video | 70 | 55 | 88 | studio thật nhưng visual/form/asset gap |
| Chat AI | 64 | 43 | 80 | core chat/ảnh có, workspace depth thấp |
| Tạo clip ngắn | 67 | 50 | 84 | engine mạnh, editor/product layer mỏng |
| Thumbnail | 64 | 44 | 80 | generation tốt, design/brand loop thiếu |
| Tạo ảnh | 62 | 40 | 80 | generator cơ bản, editing/reference thiếu |
| Kịch bản | 66 | 46 | 81 | structured text tốt, project/revision thiếu |
| Socialbot | 68 | N/A | 87 | internal/frozen; không đưa vào roadmap redesign |

## Gate

| Gate | Kết quả | Ghi chú |
|---|---|---|
| G0 Scope | PASS | inventory/source/production snapshot rõ |
| G1 Core Outcome | PASS | dựa test/canary mới nhất và browser routes |
| G2 Security | PASS | không phát hiện regression trong audit này |
| G3 Money/Credit | PASS | primitives và flow hiện có đã kiểm trước đó |
| G4 Honest UI | PASS có debt | feature nghiên cứu/disabled được nói thật |
| G5 Data Recovery | PASS có debt | job/project recovery tốt ở app mới |
| G6 Accessibility | **FAIL** | overflow public mobile, target nhỏ, field thiếu name |
| G7 Performance | UNKNOWN/PARTIAL | cần field CWV và budget theo page trong DS phase |
| G8 Operations | **FAIL ngoài app** | website repo/live route mismatch |
