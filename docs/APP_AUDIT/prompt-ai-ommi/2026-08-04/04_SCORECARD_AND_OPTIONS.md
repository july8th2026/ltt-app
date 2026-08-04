# 04 — Scorecard và phương án

## 1. Baseline nguồn trước khi replatform

Đây là điểm **khả năng đưa module nguồn thành sản phẩm thương mại**, không phải
điểm của app đích chưa được xây.

| Dashboard | Điểm |
|---|---:|
| Quality Score | **59,8/100** |
| Market Score | **84/100** |
| Evidence Confidence | **68/100** |
| Release Gate | **BLOCKED** |

Blocker: shared namespace/full write, SQLite/data path trong source, API key và
budget riêng, task nền trong web, chưa có browser/performance/production evidence.
Điểm thị trường cao vì source có brief→scene→storyboard→export khá sâu; chất
lượng thương mại thấp không có nghĩa logic sáng tạo kém.

| Nhóm Quality | Trọng số | 0–5 | Quy đổi |
|---|---:|---:|---:|
| Core outcome | 15 | 4,0 | 12,0 |
| Feature completeness | 12 | 4,5 | 10,8 |
| Control correctness | 12 | 3,5 | 8,4 |
| UX/workflow/IA | 12 | 3,5 | 8,4 |
| UI/design system | 8 | 2,5 | 4,0 |
| Responsive/accessibility | 7 | 2,0 | 2,8 |
| Reliability/performance | 9 | 2,5 | 4,5 |
| AI/provider economics | 8 | 3,0 | 4,8 |
| Security/privacy/tenant/credit | 10 | 1,0 | 2,0 |
| Architecture/ops/observability | 7 | 1,5 | 2,1 |

UI/UX score là provisional E1; phải chấm lại bằng browser sau khi có skeleton.

## 2. Benchmark signals cần học

- LTX Studio nối script/concept/image/video với dynamic storyboard, timeline,
  shot control, references và consistency elements.
- Google Flow tổ chức Plan/Create/Refine, Ingredients, Scenebuilder, asset
  collections và credit theo model.
- Runway cho reference ảnh/video/audio với nhãn và `@` mention; reference có
  thể tạm thời, lưu riêng hoặc chia sẻ workspace.
- Runway Workflows cho chạy toàn graph hoặc từng phần, history output, compare,
  reuse output và cancel active run.
- Freepik Spaces giữ node catalog nhỏ: Media, Text, Image, Video, Assistant và
  mở rộng qua sidebar/context menu.

Nguồn chính thức:

- https://ltx.io/studio
- https://ltx.io/studio/platform/shot-video-editor
- https://labs.google/fx/tools/flow
- https://help.runwayml.com/hc/en-us/articles/52963720640275-Using-reference-media-to-guide-your-generations
- https://help.runwayml.com/hc/en-us/articles/45769159004691-Building-your-first-Workflows
- https://ru.freepik.com/ai/docs/spaces-faq

Không clone nhận diện hay UI pixel. Học mô hình tinh thần: project context,
progressive disclosure, asset mention, shot-level iteration và history.

## 3. Chấm phương án kiến trúc

Trọng số: parity 20, security/tenant/credit 20, reuse LTT 15, maintainability/
ops 15, delivery 10, UX 10, testability/rollback 10.

| Phương án | Điểm | Kết luận |
|---|---:|---|
| A. Copy nguyên module/SQLite/UI | 48/100 | Loại: nhanh bề mặt nhưng phá Q3/Q43, hai runtime và mất tenant safety |
| B. Viết MVP tối giản chỉ brief→prompt | 70/100 | Không chọn: an toàn hơn nhưng bỏ quá nhiều năng lực/không đạt parity |
| **C. Capability-preserving replatform** | **91/100** | **Khuyến nghị**: giữ chiều sâu, thay toàn bộ ranh giới hạ tầng |
| D. Tách Prompt Studio thành microservice riêng | 63/100 | Hoãn: tăng auth/data/credit/ops và distributed failure không cần thiết |

## 4. Release gate hiện tại

| Gate | Trạng thái | Điều kiện mở |
|---|---|---|
| G0 Scope | PASS | Charter và role matrix đã khóa |
| G1 Core outcome | UNKNOWN | Golden prompt package + task flow E2E |
| G2 Security | FAIL | Viết ownership contract mới + adversarial two-user tests |
| G3 Money | FAIL | Quote/hold/settle/refund/idempotency tests |
| G4 Honest UI | UNKNOWN | Browser control registry, không dead control/model giả |
| G5 Recovery | FAIL | Revision/snapshot/import/export/restore tests |
| G6 Accessibility | UNKNOWN | Keyboard/focus/contrast/mobile browser gate |
| G7 Performance | UNKNOWN | Project 20 scene, asset/job load, P95 budget |
| G8 Operations | FAIL | Metrics, kill switch, runbook, backup/retention |

