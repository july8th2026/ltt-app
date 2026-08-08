# 04 - Scorecard và gates

## Baseline tạm thời

`Q 58 (provisional) · M UNKNOWN · E 31 · Gate BLOCKED`

Đây là điểm cho **marketplace shell + lịch sử/observability**, không phải điểm
chất lượng output AI của từng app. 8 điểm AI được phân bổ lại trước A0: +3 tính
năng, +2 UX, +2 reliability, +1 operations. M chưa chấm vì A4 mới được lập kế
hoạch; bịa điểm thị trường ở đây sẽ vi phạm quy tắc evidence.

| Nhóm đã điều chỉnh | Trọng số | Điểm /5 | Đạt | Căn cứ |
|---|---:|---:|---:|---|
| Giá trị/JTBD | 15 | 3,5 | 10,5 | một tài khoản/nhiều tool và job chung có giá trị thật |
| Tính năng/đầy đủ | 15 | 2,5 | 7,5 | history có nhưng phân mảnh; lifecycle/event log thiếu |
| Control đúng | 12 | 2,5 | 6,0 | card/compare/switch/download có gap đã tái hiện bằng source |
| UX/workflow/IA | 14 | 2,2 | 6,2 | customer còn thấy metadata và bề mặt nội bộ |
| UI/design system | 8 | 2,8 | 4,5 | có shell/token nhưng icon/tag/card chưa nhất quán |
| Responsive/a11y | 7 | 3,0 | 4,2 | có baseline cũ; journey mới chưa đo đủ viewport |
| Reliability/performance | 11 | 3,5 | 7,7 | queue/GPU lease tốt; version drift và event gap |
| Security/tenant/credit | 10 | 4,0 | 8,0 | owner scope/credit tốt; log/redaction chưa có contract |
| Operations/observability | 8 | 2,0 | 3,2 | process log có, per-job durable event log chưa có |
| **Tổng** | **100** | | **57,8** | làm tròn Q58 |

## G0-G8

| Gate | Verdict | Lý do/điều kiện mở |
|---|---|---|
| G0 Scope | PASS | charter khóa rõ |
| G1 Core Outcome | UNKNOWN | chưa chạy A-Z từng tool trong lượt plan |
| G2 Security | PARTIAL | ownership hiện có; schema log/redaction chưa tồn tại |
| G3 Money/Credit | UNKNOWN | chưa rerun quote/hold/settle/refund mọi app |
| G4 Honest UI | **FAIL** | lifecycle sai/thiếu, tool nội bộ lộ với customer auth, control Upscale mâu thuẫn |
| G5 Data Recovery | PARTIAL | job không mất nhưng timeline sự kiện và retention chưa khóa |
| G6 Accessibility | UNKNOWN | chưa audit keyboard/mobile từng UI target |
| G7 Performance | UNKNOWN | chưa benchmark P50/P95 theo tool; chỉ biết hardware thật |
| G8 Operations | **FAIL** | không có durable structured per-job event log |

Không app nào được gọi là “đã hoàn thiện” theo quality gate chỉ từ nhãn catalog.

