# 07 — Implementation Roadmap: Upscale Video

Roadmap này là đầu ra audit, **chưa phải trạng thái đã triển khai**. Mỗi phase
chỉ mở khi phase trước PASS; không trộn với audit app kế tiếp.

## Phase plan

| Phase | Scope | Dependency | Acceptance/PASS gate | Test/evidence | Rollback | Status |
|---|---|---|---|---|---|---|
| 0A Upload security | F-001: upload session, CSRF, MIME/signature, size/quota/rate, staging namespace | R2 policy + storage contract | G2 PASS; abuse/cross-tenant/over-limit bị chặn | Route + staging R2 boundary + browser large upload | Cờ tắt direct upload về multipart ≤90MB | Chưa làm |
| 0B Artifact lifecycle | F-002: promote/cleanup/sweeper/retention/report | 0A + storage delete/idempotency | G5/G8 PASS; fail/abandon không orphan | Credit fail, partial batch, crash/race, dry-run/purge | Sweeper dry-run; revert promote contract | Chưa làm |
| 0C Honest UI/i18n | F-004/005/006/016 | locale helper + shared shell | EN/VI A-Z PASS; không PRO giả/R2 jargon/link name rỗng | Playwright desktop/mobile/keyboard/console/network | Revert copy/template only | Chưa làm |
| 1A Core recovery | F-007/008/009: full history/link, retry, live polling | Job history/retry API có sẵn | queued→done/error/cancel/retry bền sau reload | Browser fixture ≥55 job + SSE/poll/offline | Tắt polling, giữ link global history | Chưa làm |
| 1B Canonical validation/quote | F-010/012: server probe, canonical duration/quote, confirm high-cost | Staging upload | Không hold file corrupt; quote/hold khớp; runtime range honest | Corrupt/huge/VFR/no-audio + insufficient credit | Fallback worker probe, giữ policy cũ | Chưa làm |
| 1C Delivery performance | F-011/013: signed attachment CDN, poster/lazy media | Storage URL headers + thumbnail worker | 4K file resume/direct; initial bytes/request budget PASS | Network trace, range/resume, owner/cross-tenant | Proxy local fallback | Chưa làm |
| 2A Quality benchmark | Baseline 12–20 clip representative; temporal engine/provider spike | GPU/provider budget | Blind panel + flicker/LPIPS + cost/P95 report; không đoán | Repro dataset, schema evidence | Không ship engine thua baseline | Chưa làm |
| 2B Selective parity | Auto/Fast/Quality; Detail/Denoise/Deblur; advanced nội bộ | 2A chọn engine | Market table-stakes ≥75; customer không thấy model dev | Golden/regression GPU + browser quote/output | Feature flags theo capability | Chưa làm |
| 3 Differentiate | Seedance handoff 1 click, preset recommendations; Watch giữ admin | 1A/2B | Handoff quote/confirm/retry thống nhất, không import chéo | Seedance→Upscale A-Z + owner/credit | Tắt entrypoint, giữ direct app | Chưa làm |
| 4 Optimize | Production SLO, cost/success, GPU queue routing, cleanup alerts | ≥20 finished/app | success ≥90%, queue P95 ≤120s, stale/event fail 0 | Operator metrics + soak có sample thật | Alert-only trước auto action | Chưa làm |
| 5 Release | Full gate, canary, authenticated production verify, audit lại Q/M/E | Phase 0–4 PASS + quyết định D1–D7 | G0–G8 PASS; Q≥80, M≥75, E≥85; no P0/P1 | `tools/gate.py`, Playwright A-Z, hash/health/rollback | Archive + backup + rollback rehearsal | Chưa làm |

## Baseline và post-release metrics

| Metric | Baseline | Target | Cửa sổ đo | Nguồn | Kết quả |
|---|---:|---:|---|---|---:|
| Task completion | UNKNOWN | ≥90% | 5-user moderated + telemetry | User study/job funnel | Chưa đo |
| Time-to-first-result Fast 10s clip | ≈21s runtime, chưa gồm queue/upload | ≤baseline và P95 công bố theo class | ≥20 job | EV-GPU-002 + production metric | Chưa đo |
| Error/retry rate | UNKNOWN; retry app MISSING | Error <10%, retry success ≥80% | 30 ngày | JobEvent | Chưa đo |
| Job success rate | Development evidence PASS, production insufficient | ≥90% | ≥20 terminal/app | `job_metrics` | Chưa đủ mẫu |
| Credit dispute/refund | UNKNOWN | 0 double charge; 100% eligible cancel refunded | 30 ngày | Ledger/JobEvent | Chưa đo |
| Cost/successful output | UNKNOWN production | Báo theo preset/resolution | 30 ngày | Credit + JobEvent | Chưa đo |
| Queue wait P95 | Dev soak 5.4–5.6s generic | ≤120s compute | ≥20 terminal/app | SLO operator | Chưa đủ mẫu |
| Artifact orphan | Không đo; code có đường tạo orphan | 0 quá TTL | Daily sweeper | Storage report | Chưa làm |
| Market score | 57 | ≥75 | Sau Phase 2 | LTT-AQA benchmark | Chưa làm |
| Quality score | 64 | ≥80 | Sau Phase 5 | LTT-AQA scorecard | Chưa làm |

