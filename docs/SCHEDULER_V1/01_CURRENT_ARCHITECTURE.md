# Scheduler V1 — kiến trúc hiện tại

## Các ingress

```text
Public async /api/v1/quotes -> /jobs
  -> public_api.invocation.submit
  -> job_submit.submit_with_credit
  -> jobs.submit -> PostgreSQL jobs

Internal product job
  -> runtime_noi_bo.job.nop_job
  -> job_submit.submit_with_credit
  -> jobs.submit -> PostgreSQL jobs

Agent child
  -> agent.runs.submit_child
  -> jobs.submit -> PostgreSQL jobs

Web app routes
  -> job_submit.submit_with_credit
  -> jobs.submit -> PostgreSQL jobs
```

Codex/CLI dùng credential public đi qua `/api/v1`; vì vậy là public/external.

## Claim và thi hành async

```text
PostgreSQL jobs
  -> jobs.claim: due + capability + resource prefilter
  -> aging -> never-served -> last-account-claim -> FIFO
  -> FOR UPDATE SKIP LOCKED
  -> running
  -> ExecutionLease (resource/slot, unique)
  -> GPU lease nếu cần
  -> admitted -> handler -> complete/fail/resource_wait
  -> settle/refund + terminal webhook outbox
```

Resource prefilter chỉ giảm claim hụt; `ExecutionLease` vẫn là arbitration vật
lý cuối cùng. Race giành slot đưa job về `queued` mà không tăng attempt.

## Sync/stream

`/api/v1/chat/completions`, `/messages`, `/responses` và internal text stream
không tạo Job. Chúng xin cùng `ExecutionLease`; bận thì mặc định 429 trước khi
giữ tiền. Đây là Q114 và phải giữ để không phá OpenAI/Anthropic client.

## Phản hồi hiện tại

- Public async: POST trả job; GET owner-scoped trả status/progress/time/credit.
- Web: HTMX poll progress mỗi 2 giây; JSON history owner-scoped.
- Job events: timeline bền, nhưng không có public SSE lifecycle.
- Webhook: chỉ terminal milestone; không gửi mỗi lần vị trí đổi.
- Metrics/admin: depth và oldest wait theo resource, lease holder aggregate;
  chưa tách internal/external và chưa có ETA/vị trí.

## Khoảng trống kiến trúc

Claim là source duy nhất biết ranking nhưng logic nằm nội tuyến, nên status
không thể tái dùng. Ingress chưa gắn nguồn/lớp, do đó internal và public đang
cùng một fairness pool. ETA aggregate tồn tại nhưng không quy thành dự báo cho
một job cụ thể.

