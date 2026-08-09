# 07 — Implementation Roadmap: Tạo Video Seedance

Đây là output audit, **chưa triển khai**. Phase tuần tự; phase sau chỉ mở khi
phase trước PASS.

| Phase | Scope | Acceptance/PASS gate | Test/evidence | Rollback | Status |
|---|---|---|---|---|---|
| 0A Credit cap/calibration | F-001: charge ≤ held, provider variance metric, P95 calibration | Không balance âm; quote/settle/reconcile idempotent; G3 partial PASS | Unit/property/concurrent ledger + ≥100 usage sample | Feature flag cap, giữ ledger schema | Chưa làm |
| 0B Reference lifecycle | F-002: upload session, staging/TTL/promote/cleanup/retention | Fail/abandon/crash không orphan; G2/G5/G8 partial PASS | Credit fail, partial upload, sweeper race, dry-run | Sweeper dry-run; local upload fallback | Chưa làm |
| 0C Idempotent submit/recovery | F-003/F-004: stable idempotency, PRG/flash, preserve locale/form/ref | Double click/replay một batch; mọi 4xx giữ workspace | Browser EN/VI/network replay/concurrency | Tắt JS enhancement, server idempotency vẫn giữ | Chưa làm |
| 0D Canonical quote/upload safety | F-005/F-008: quote id từ refs; stream/probe/signature/quota | Quote=hold; corrupt/oversize chặn trước job; memory budget PASS | Media corpus boundary/load | Cap multipart thấp, tắt large video ref | Chưa làm |
| 0E i18n/a11y/shared shell | F-006/F-018 | VI/EN A-Z; drawer inert/focus restore; WCAG AA | Playwright 390/768/1440 + axe/keyboard | Revert template/CSS only | Chưa làm |
| 1A Live recovery/history | F-009/F-010/F-016 | queued→terminal live; cancel/retry; cursor history/assets delete | Fixture >100 job, offline/backoff/refund/retry | Tắt polling, giữ manual refresh/global history | Chưa làm |
| 1B Reference manager | F-007/F-017 | Add/remove/replace/role/handle không blob fail; capability rõ | File thật + keyboard/mobile/network | Basic file picker fallback | Chưa làm |
| 1C Delivery | F-011/F-015 | Direct attachment/range/resume; estimate request budget | R2 staging + network trace | Local proxy/cache fallback | Chưa làm |
| 2A Provider operations | F-012/F-013 | Dynamic config/probe; usage từng attempt; budget/reconciliation | Sandbox provider fault/billing fixtures | Pin known endpoint/version | Chưa làm |
| 2B Selective parity | F-014: edit, extend, first/last clarity, simple sequence | Capability + user test + cost/SLO pass; không full editor | Golden journeys + output blind panel | Feature flag từng capability | Chưa làm |
| 3 Quality benchmark | Representative prompt/ref/audio set | Prompt/identity/motion/audio ≥ baseline; cost/P95 rõ | Blind score + task metadata | Không ship model thua baseline | Chưa làm |
| 4 Optimize | Production funnel/SLO/cost/orphan alert | ≥20 terminal/model; success≥95%; queue P95≤30s; orphan 0 | Operator metrics 30 ngày | Alert-only trước auto action | Chưa làm |
| 5 Release | Full gate/canary/auth production/re-audit | 0 P0/P1; G0–G8 PASS; Q≥80/M≥75/E≥85 | `tools/gate.py`, Playwright A-Z, rollback rehearsal | Archive/backup/feature flags | Chưa làm |

## Metric baseline/target

| Metric | Baseline | Target |
|---|---|---|
| Quality Score | 57 | ≥80 |
| Market Score | 64 | ≥75 |
| Negative balance | Contract cho phép | 0 |
| Double job/hold | Có đường tái hiện từ source | 0 |
| Orphan reference | Không đo; có đường tạo | 0 quá TTL |
| Form recovery sau 4xx | Mất prompt/model/count/locale | 100% preserve |
| EN core journey | FAIL | 100% VI-free |
| Mobile keyboard drawer | FAIL | PASS |
| Production success/P95 | UNKNOWN | ≥95%; queue P95≤30s |
| Retry success | UI MISSING | ≥80% lỗi retryable |

## Deep-round evidence delta (2026-08-09)

Canary thật đã **PASS G1 core outcome** có điều kiện nhưng **FAIL G3 P0**:
Mini 4s/480p với ảnh + video tạo MP4 playable; actual 78 credit trong khi hold
video-rate 29. Vì vậy mọi phase sau 0A đều khóa, không chạy thêm job trả phí.

| Phase bắt buộc trước provider canary tiếp theo | Acceptance đóng phase |
|---|---|
| 0A Credit cap + canonical quote | Không charge quá hold; quote phân biệt video/audio; ledger idempotent; balance không âm |
| 0B Audio/input contract | magic sniff; `AssetType`/MIME Audio đúng; corrupt media refund; canary audio pass |
| 0C Asset registry | hash cache, owner, remote reconcile, 50-slot quota, pin/grace/LRU, cleanup audit |
| 0D Recovery/delivery | remix giữ refs/handles; retry/cancel/re-poll; ffprobe; download attachment |

**Rollback:** feature flag tắt audio/video-reference mới; giữ đường image-inline
đã chứng minh; cap charge ở held và hoàn phần variance platform; không xóa asset
remote khi chưa có dry-run/reconcile.
