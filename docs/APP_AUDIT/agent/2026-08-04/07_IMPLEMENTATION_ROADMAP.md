# 07 — Implementation Roadmap

## Nguyên tắc thứ tự

Không làm song song nhiều app. Trong Agent, mỗi phase chỉ mở khi phase trước PASS. Mỗi feature đi theo lát dọc: contract → backend → UI → browser → telemetry → docs. Không render nút giả.

## Phase plan

| Phase | Scope | PASS gate | Rollback |
|---|---|---|---|
| P14.0 Lock ✅ | D1–D12, baseline, data migration/rollback design | Q62 + audit baseline | chỉ docs, không code |
| P14.1 Canvas v2 ✅ | pages, frames, annotations, view state, node config, v1 importer | round-trip/migration/ownership/conflict PASS | migration additive |
| P14.2 Immersive shell ✅ | full-height canvas, topbar/rail/drawers, title/save, shortcuts/layers | responsive/browser console/network PASS | prior static bundle |
| P14.3 Composer/catalog ✅ | capability schema, model/provider/mode/ratio/quality/duration, quote | invalid combo + quote server PASS | catalog fallback |
| P14.4 Media nodes I ✅ | Asset, Text, Image, Batch Images, Video, Video Upscale | upload/ownership/quote/run tests PASS | disable ToolSpec/app |
| P14.5 Media nodes II ✅ | Audio/TTS, Extract Frames, Merge Image/Video, Social Video, image upscale | SSRF/privacy/owner/GPU smoke PASS | run rollout off/tool off |
| P14.6 Scoped execution ✅ | node/selection/frame/full, closure, cache, bundle | scope/cache/credit tests PASS | set rollout off |
| P14.7 Assistant ✅* | SSE analyze/improve, private patterns, signed preview/apply | validator + no-mutation/tamper tests PASS | manual editor remains |
| P14.8 Version/share/collab ✅* | snapshots/restore, private view/clone/revoke, annotations/activity | ACL/revoke/restore tests PASS | revoke/off + snapshots retained |
| P14.9 Scale/ops ✅ | 100-node, 512 KiB document, metrics/runbook/kill switch | 100-node/backend/frontend/full load gate PASS | 100→32 and bundle rollback |
| P14.10 Parity acceptance ✅* | matrix, visual/behavior regression, deploy/canary handoff | Q91, M88, E96; health/browser unauth PASS | rollout off / prior release |

`*` Phạm vi thật: assistant chưa có VLM phân tích video độc lập; collaboration
không phải realtime cursor/multi-user. Production Canvas phiên cuối cần chủ sản
phẩm đăng nhập lại vì session hết hạn; local authenticated E2E dùng cùng bundle
đã PASS. Đây là backlog/handoff thật, không được mô tả thành bằng chứng chưa có.

## Chỉ số đích

| Metric | Baseline cần đo P14.0 | Target |
|---|---:|---:|
| Tạo workflow 3-node hợp lệ | chưa đo | ≥90% task success |
| Time-to-first-valid-graph | chưa đo | ≤3 phút manual; ≤60 giây assistant |
| Invalid edge accepted | LTT 0 theo contract | 0 |
| Save conflict mất dữ liệu | chưa thấy | 0; restore rõ |
| Quote mismatch/dispute | chưa đo | <0.1% run |
| Job success excluding provider policy | chưa đo | ≥98% |
| 100-node pan/zoom | chưa đo | ≥50 FPS p75 desktop mục tiêu |
| Save P95 | chưa đo | ≤800 ms API, có offline queue |
| Console unexpected error | 0 trong flow audit | 0 |
| Failed app request unexpected | 0 trong flow local audit | 0 |

## Vòng lặp đối soát

Mỗi phase chạy: `PlenX capability snapshot → LTT acceptance → implement → unit/integration → browser desktop/mobile → console/network → score delta → finding mới → regression/rule → PASS/rollback`. Không dùng cảm giác “trông giống” làm gate.

Full Python/frontend/secret scan chỉ chạy ở checkpoint release chung theo quyết định hiện tại; test hẹp của phase vẫn bắt buộc ngay khi code thay đổi.
