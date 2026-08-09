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

---

## Release re-audit — 2026-08-09

`Q 87 · M 73 · E 80 · PUBLIC`

Điểm này áp dụng cho **marketplace shell + vận hành portfolio/customer
journey**, không áp dụng cho chất lượng output/model AI. Trọng số vẫn giữ đúng
phân bổ đã khóa ở baseline; không đổi sau khi thấy kết quả.

| Nhóm đã điều chỉnh | Trọng số | Điểm /5 | Đạt | Evidence chính |
|---|---:|---:|---:|---|
| Giá trị/JTBD | 15 | 4,2 | 12,6 | một tài khoản, catalog/customer audience, history và credit chung |
| Tính năng/đầy đủ | 15 | 4,2 | 12,6 | lifecycle, JobEvent, retry/cancel/download, image modes và các phase app |
| Control đúng | 12 | 4,4 | 10,6 | control registry, quote/confirm, compare, queue và regression theo app |
| UX/workflow/IA | 14 | 4,1 | 11,5 | card-link, taxonomy, ẩn nội bộ, history entry point và browser A-Z |
| UI/design system | 8 | 4,1 | 6,6 | shell/token/card/state thống nhất; vẫn còn nợ asset library xuyên app |
| Responsive/a11y | 7 | 4,2 | 5,9 | 11 route desktop/mobile, keyboard control, không overflow |
| Reliability/performance | 11 | 4,5 | 9,9 | load/soak, retry/reclaim, GPU lease, canary và production health |
| Security/tenant/credit | 10 | 4,7 | 9,4 | ownership, redaction, secret scan, quote/hold/settle/refund |
| Operations/observability | 8 | 4,7 | 7,5 | metrics/alert/runbook, support export, backup/restore/rollback/deploy |
| **Tổng** | **100** | | **86,6 → Q87** | |

### Evidence Confidence

- E3 cho product, feature, control, UX, UI, responsive và security: source/test
  đã chạy và quan sát browser thật.
- E4 cho reliability và operations: archive canary, production health, service
  state, backup/restore và deploy log thật.
- `E = 81 × 0,75 + 19 × 1,00 = 79,75 → E80`.

Không nâng E lên 90+: chưa có authenticated production session lưu sẵn cho
vòng browser sau deploy, chưa đủ mẫu production SLO và chưa có external
pentest/user study độc lập.

### G0-G8 sau release

| Gate | Verdict | Evidence/giới hạn |
|---|---|---|
| G0 Scope | PASS | charter, audience, route và dữ liệu canary đã khóa |
| G1 Core Outcome | PASS | A-Z theo app ở H26.5-H26.10; archive canary chạy output thật và public shell đúng build |
| G2 Security | PASS | owner scope, role/audience guard, log redaction, protected env và secret scan 0 |
| G3 Money/Credit | PASS | quote/confirm/hold/settle/refund/idempotency test; browser Chat/Agent/Tạo ảnh trừ đúng |
| G4 Honest UI | PASS | retired/internal bị ẩn; lifecycle thật; control P1 đã đóng và không còn CTA giả đã biết |
| G5 Data Recovery | PASS | append-only JobEvent, retry/reclaim, partial cleanup, backup restore và rollback rehearsal |
| G6 Accessibility | PASS baseline | keyboard/card/compare và desktop/mobile core journey đạt baseline; không tuyên bố chứng nhận WCAG toàn site |
| G7 Performance | PASS release budget | SLO theo app, load/soak và topology hai GPU đạt evidence development/canary; tiếp tục thu production sample |
| G8 Operations | PASS | metrics/alerts/runbook/support export, rollback đủ 3 service, backup và release evidence |

### Release class

`PUBLIC` là mức hợp lý: production có thể cho khách dùng, đường lùi và
observability đã đủ. Chưa nâng `COMMERCIAL` cho toàn portfolio cho tới khi đủ
production SLO sample, trial benchmark có trả phí và blind evaluation output AI.
