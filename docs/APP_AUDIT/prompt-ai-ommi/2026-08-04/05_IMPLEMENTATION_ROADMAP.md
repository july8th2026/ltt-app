# 05 — Roadmap triển khai chi tiết

Trình tự là bắt buộc. Không mở phase sau khi gate phase trước còn đỏ; không
triển khai app khác song song trong cùng chuỗi nghiệm thu.

## P0 — Contract, parity ledger và threat model

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-000 | Khóa tên `prompt_ai_ommi`, URL, persona, core workflow | Manifest contract test phác thảo, không trùng slug/prefix/tool/job |
| OMMI-001 | Lập endpoint/capability ledger 261 endpoint → KEEP/MERGE/ADMIN/REJECT | 100% route nguồn có disposition; không “quên vì không thấy UI” |
| OMMI-002 | Chọn pure logic/resource và ghi provenance/license | Danh sách file copy được; scan secret/data; không copy DB/runtime/user data |
| OMMI-003 | Golden fixtures cho prompt, anchors, scene split, export | Fixture synthetic; output baseline khóa được |
| OMMI-004 | Threat model tenant/import/export/provider/credit | Abuse case + security acceptance đầy đủ |
| OMMI-005 | Spike app→ToolSpec submit cho handoff ảnh/video | Có public contract dùng được, hoặc dừng và mở contract-gap chính thức |

**Gate P0:** ledger 100%, source vẫn read-only, G0 PASS; chưa viết feature nếu
OMMI-005 chưa có kết luận.

## P1 — App shell và tenant-safe persistence

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-100 | Tạo app folder/manifest/routes/template, rollout `off` | Registry/lint pass, app không hiện public khi off |
| OMMI-101 | Project schema v1 + validator/migrator | Payload cap/depth/forbidden fields và schema tests |
| OMMI-102 | Project CRUD/AppProject revision/archive/restore | Two-user 404/403, stale revision 409, no cross-owner list |
| OMMI-103 | Asset upload metadata + Storage owner key | MIME/size/pixel/hash, path traversal, ownership tests |
| OMMI-104 | Preferences owner-scoped | Locale/theme/defaults giữ qua reload; không chứa secret |

**Gate P1:** G2 ownership core PASS; rollback = rollout off + bỏ folder app.

## P2 — Core Studio: project, brief, preflight, prompt package

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-200 | Project/brief workflow và autosave conflict UI | Create/edit/reload/two-tab conflict browser PASS |
| OMMI-201 | Prompt fragments/meta/style + placeholder validation | Golden parity ≥90%; no hardcoded giant prompt in jobs |
| OMMI-202 | Asset mentions `@IMG/@VID/@AUD` | Mapping deterministic, missing/duplicate/capability error rõ |
| OMMI-203 | Free preflight/preview | Không gọi provider/không trừ credit; rate-limit |
| OMMI-204 | Director job + provider/model capability | Job reclaim/retry/idempotency; model status truthful |
| OMMI-205 | Quote/confirm/credit settlement | Hold before call; done/error/cancel settle/refund exactly once |
| OMMI-206 | Scene editor, reorder, prompt history | Revision/version/undo boundary và browser control tests |

**Gate P2:** một user đi end-to-end brief→prompt package; G1/G3 core PASS.

## P3 — Consistency, iteration và storyboard

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-300 | Character/location/prop/style anchors | Cùng input cho anchor deterministic; override có trace |
| OMMI-301 | Scene split + camera/lighting/mood/continuity | Golden fixtures và schema validation |
| OMMI-302 | Regenerate with feedback/versions/compare | Không ghi đè selected version; quote riêng, owner-only |
| OMMI-303 | Storyboard framework/pack/composite/per-scene | Preview miễn phí; generate job thật; partial failure rõ |
| OMMI-304 | Clone/reorder/snapshot/restore | Restore tạo revision mới, không mất bản hiện hành |

**Gate P3:** project 20 scene tạo/sửa/restore không mất dữ liệu; storyboard
artifact owned và downloadable.

## P4 — Library, catalog và Admin split

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-400 | Private asset/prompt/style/meta libraries | User chỉ CRUD của mình |
| OMMI-401 | Admin LTT catalog publish/version/deprecate | User read/clone; direct update/delete bị chặn |
| OMMI-402 | Seed defaults idempotent | Không nhân bản sau reload; upgrade catalog không ghi đè clone user |
| OMMI-403 | Provider/model/status link tới admin hiện có | Không có key input trong app; status không lộ secret |
| OMMI-404 | Admin ops: health/orphan/retention/audit | Dry-run, queued ops, audit evidence, kill switch |

**Gate P4:** G2 admin/user split PASS; không còn Settings/Maintenance nguy hiểm
từ module nguồn.

## P5 — Export, import và handoff sang hệ sinh thái LTT

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-500 | Markdown/JSON/PDF/ZIP prompt package | Owned artifact, deterministic filenames, no internal paths |
| OMMI-501 | Package import dry-run/merge/new-copy | ZIP bomb/path traversal/MIME/schema/entity cap tests |
| OMMI-502 | Handoff Tạo ảnh | Quote/confirm/job/owned refs; result quay lại project |
| OMMI-503 | Handoff Tạo video Seedance | Prompt/media capability validation + quote popup |
| OMMI-504 | Handoff Agent Canvas/Upscale khi phù hợp | Chỉ tool contract public, không private cross-app import |

**Gate P5:** handoff không duplicate job/charge, không lộ asset người khác;
export→import round-trip giữ nghĩa.

## P6 — Batch, recovery và vận hành

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-600 | Batch bounded + per-item state | Cap rõ; retry/cancel/partial settlement minh bạch |
| OMMI-601 | Trash/restore/retention | Owner-only; purge async; admin dry-run; audit log |
| OMMI-602 | Metrics/telemetry/alerts | Success/error/refund/P95/cost; redact prompt/media/PII |
| OMMI-603 | Backup/restore drill và migration rehearsal | Restore synthetic project/artifact/version PASS |
| OMMI-604 | Runbook/rollback/feature flag | off/admin/allowlist/public, kill switch provider/job |

## P7 — UI/UX Carbon Red và browser acceptance

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-700 | Immersive shell, icon rail, contextual drawer | Desktop workspace rộng; không nested-scroll vô lý |
| OMMI-701 | Studio stepper + scene cards + inspector | Người mới hoàn tất core task không cần đọc tài liệu |
| OMMI-702 | Storyboard/version/compare interactions | Keyboard/touch/focus, loading/error/empty states |
| OMMI-703 | Mobile review/edit flow | 390×844 không page overflow; core review controls usable |
| OMMI-704 | Full control registry | Mọi nút có backend/disabled reason/test; không decorative fake |

**Gate P7:** Playwright desktop/tablet/mobile; console 0 error; failed network
0 ngoài test cố ý; axe/keyboard/contrast gate; visual regression.

## P8 — Parity audit, canary và release

| Ticket | Việc | PASS |
|---|---|---|
| OMMI-800 | Re-run source parity ledger | ≥90% user-value parity; 100% P0/P1 disposition |
| OMMI-801 | LTT-AQA DEEP post-build | Q≥88, M≥80, E≥90; P0=0; G0–G8 PASS |
| OMMI-802 | Full regression/secret/app lint/frontend build | Tất cả lệnh chạy thật xanh, secret 0 |
| OMMI-803 | Local/fixture E2E synthetic media | Core + error/refund/retry/recovery browser PASS |
| OMMI-804 | Admin→allowlist canary | Metrics trong budget, không credit dispute/data leak |
| OMMI-805 | Production release | Chỉ khi có yêu cầu deploy rõ; backup/health/browser/rollback PASS |

## Chỉ số nghiệm thu

| Metric | Mục tiêu trước public |
|---|---:|
| Hoàn tất brief→prompt package | ≥90% task study |
| Time-to-first-preview | ≤2 phút với brief có sẵn |
| User-value parity nguồn | ≥90% |
| Cross-user adversarial tests | 100% chặn |
| Duplicate charge/provider submit | 0 |
| Job success không tính input lỗi | ≥95% canary |
| Refund đúng khi lỗi/cancel | 100% |
| Page overflow 390–1920 px | 0 |
| Console error/failed unexpected network | 0 |
| P0 finding và G2/G3 fail | 0 |

