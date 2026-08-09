# Shared finding registry

248 finding thô được khử trùng thành 12 chương trình. Finding gốc vẫn là nguồn
acceptance; registry này không xóa hoặc hạ severity.

| Program | Sev cao nhất | App chịu ảnh hưởng | Việc phải đóng |
|---|---|---|---|
| S01 Authorization/tenant boundary | P0 | Socialbot, Chat, mọi route internal | role policy, owner test, global-state isolation/redaction |
| S02 Exactly-once orchestration/money | P0 | Agent, Seedance, Chat, Image, Prompt | idempotency DB, một orchestration owner, atomic quote/hold/settle/refund |
| S03 Canonical upload/admission | P1 | Upscale, Seedance, AutoSub, Prompt, Image, Clip, Chat | stream cap, signature/probe, quota/rate, staging/promote |
| S04 Artifact lifecycle | P1 | gần mọi media app, Chat, Agent | registry owner/reference, TTL, export/delete, GC/restore audit |
| S05 Durable run/cancel/reconcile | P1 | Agent, Chat, Clip, AutoSub, Media, video/image jobs | cascade/cooperative cancel, deadline, crash reconciler, receipt |
| S06 Project/draft/conflict | P1 | Prompt, AutoSub, Agent, Chat, Image | local outbox, dirty state, optimistic conflict/merge, history/restore |
| S07 Provider/privacy/economics | P1 | Chat, Agent và app AI | commercial authorization, DPA/retention, model cost table/fallback/eval |
| S08 Customer IA/control honesty | P1 | tất cả customer app | bỏ dev jargon, one mental model, no dead/misleading control, guided errors |
| S09 History/debug/observability | P2 | tất cả | Job/Event/actor/correlation, filter/page, metrics/alert/runbook |
| S10 i18n/responsive/accessibility | P2 | tất cả | locale-safe routes, keyboard/focus/live region, mobile task parity |
| S11 Capability/entitlement truth | P2 | Upscale, Image, Agent, marketplace | Pro/price/capability theo contract thật, deliberate omission rõ |
| S12 App-specific core correctness | P1 | từng app | xem registry dưới đây |

## S12 — Core correctness không được “gom mất”

| App | Blocker riêng bắt buộc |
|---|---|
| Upscale | upload/artifact gate trước temporal enhance; Pro entitlement thật |
| Seedance | settlement không âm; reference quote/dedupe/lifecycle |
| AutoSub | workload quote, autosave conflict, QA phải chặn paid render |
| Prompt AI | Director apply revision, autosave, resource→storyboard→handoff A–Z |
| Tạo ảnh/Thumbnail | model-aware price, giữ form khi lỗi, reference lifecycle |
| Clip | rebase SRT về clip timeline; cancel/deadline; source/output lifecycle |
| Chat | provider authorization, durable context branch, bounded image quote |
| Agent | exactly-once, literal Text/Asset 0-credit, workflow library, cancel tree |
| Socialbot | operator-only; không feature build trước khi đổi Q10 |
| Demo | full synthetic queue+artifact, không dùng direct path làm release proof |
| Kịch bản | strict text operation/output; route retired không mở lại |
| Media Tools | DNS-rebinding/SSRF; typed operation/artifact contract |

## Kiểm kê đầy đủ

Mọi issue chi tiết, evidence, root cause và acceptance nằm tại
`docs/APP_AUDIT/<slug>/<snapshot>/05_FINDINGS.md`. Tổng đếm ở dashboard phải
luôn khớp **3/45/146/54**; lệch là dấu hiệu đã bỏ hoặc đếm trùng finding.

