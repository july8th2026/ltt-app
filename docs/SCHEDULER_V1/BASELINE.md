# Scheduler V1 — baseline đã đối chiếu từ mã

Ngày: 2026-09-10 · HEAD: `9d711828`

| Cơ chế | Trạng thái | Bằng chứng hiện tại |
|---|---|---|
| PostgreSQL `jobs` là durable queue | EXISTS | `platform_core.models.Job`, `platform_core.jobs` |
| `FOR UPDATE SKIP LOCKED` | EXISTS | `jobs.claim()` và `reclaim_orphans()` |
| `ExecutionLease` | EXISTS | unique `(resource, slot)`, acquire/heartbeat/release |
| `admission_resource` / `admission_slots` | EXISTS | cột Job, ToolSpec, worker prefilter + lease |
| `resource_wait` không tiêu attempt | EXISTS | `defer_resource()` và `_tra_ve_hang_doi()` |
| retry/backoff + ambiguous provider | EXISTS | `fail()`, `mark_ambiguous()` |
| heartbeat + orphan recovery | EXISTS | `JobContext.progress`, lease keep-alive, `run_forever()` reclaim |
| dedupe | EXISTS | lookup + partial unique `ux_jobs_dedupe_active` |
| fair aging | EXISTS | `FAIR_AGING` + `aged_first` trong `claim()` |
| account fairness | EXISTS | `last_account_claim` theo account/resource |
| job events | EXISTS | append-only sequence + customer/internal visibility |
| Public API polling | EXISTS | `GET /api/v1/jobs/{job_id}` owner-scoped |
| terminal webhook | EXISTS | outbox cho completed/failed/cancelled |
| SSE lifecycle của async job | MISSING | SSE hiện là token stream của sync/stream LLM, không phải job lifecycle |
| origin + priority class bền | MISSING | Job chưa có metadata nguồn/lớp |
| một ranking module canonical | MISSING | ranking chỉ nằm nội tuyến trong `jobs.claim()` |
| queue position/jobs ahead | MISSING | public/web payload chưa có snapshot |
| per-job ETA | PARTIAL | có lịch sử runtime/admission aggregate; chưa có estimator/snapshot |
| starvation visibility theo lớp | MISSING | metrics có depth/oldest theo resource, chưa tách lớp |

## Kết luận reuse

Giữ nguyên bảng `jobs`, transaction job+credit, dedupe, fair-share hiện hữu,
admission prefilter, `ExecutionLease`, worker state machine, job events, polling
và webhook terminal. Phần mới nhỏ nhất là hai cột envelope, một module scheduler
thuần, phép chiếu snapshot/ETA và metrics tách lớp.

