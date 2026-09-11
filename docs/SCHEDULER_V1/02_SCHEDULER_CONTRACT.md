# Scheduler V1 — contract canonical

## Bất biến

1. Một durable queue: PostgreSQL `jobs`.
2. `INTERNAL > EXTERNAL` cho job `queued`, đủ điều kiện, tranh cùng resource.
3. Non-preemptive: admitted/running/provider-dispatched không bị cắt ngang.
4. Trong cùng lớp: account fair-share, aging, FIFO ổn định.
5. `ExecutionLease`/DB constraint là arbitration cuối; scheduler chỉ chọn ứng viên.
6. Priority do trusted ingress gắn, không đọc từ public body/header.
7. Claim, queue position và ETA dùng cùng ranking implementation.
8. Job+credit, dedupe, retry, resource-wait, cancel và orphan semantics giữ nguyên.

## Envelope V1

- `origin`: `internal_runtime`, `agent`, `public_api`, `web`, `worker`, `codex`, `cli`,
  hoặc `unknown`; đây là audit metadata, không phải thang priority.
- `priority_class`: chỉ `internal` hoặc `external`.
- Giá trị thiếu/lạ luôn normalize về `external`; không nâng quyền bằng dữ liệu.

Trusted mapping V1:

- `runtime_noi_bo.job.nop_job` -> internal/internal_runtime.
- `agent.runs.submit_child` -> internal/agent.
- `JobIngressMiddleware` -> product web internal/web; `/api/v1` external/public_api.
- `server.api.jobs.create_job` đóng dấu external/public_api lần cuối tại route.
- Handler trong `job_runner` -> internal/worker cho job con do hệ thống sinh.
- Ngoài trusted scope, metadata thiếu/lạ -> external/unknown.

## Ranking

Trong tập cùng `admission_resource`, `queued`, đến hạn và phù hợp capability:

```text
priority_class
-> aged account/job trong cùng lớp
-> account chưa từng được phục vụ trong cùng lớp/resource
-> last account claim trong cùng lớp/resource
-> created_at
-> id
```

Strict priority đứng trước aging: external chờ lâu không vượt internal. Running
không nằm trong tập ranking nên không có preemption.

## Queue snapshot

Snapshot owner-safe gồm resource, priority class, position, jobs ahead, higher
priority ahead, same priority ahead, ETA và timestamp. Position là ảnh chụp và
có thể tăng khi internal tới. Không trả tenant, key, payload hay worker id.

Job queued nhưng chưa đến `next_run_at` vẫn được báo là queued/resource-wait;
snapshot không giả rằng nó có thể claim ngay. Contract API sẽ nói rõ trạng thái
eligibility và thời điểm thử lại nếu có.

## ETA

ETA là `estimated_*`, không phải lời hứa. V1 cộng remaining của execution đang
giữ resource và runtime ước lượng của các job đứng trước. Dữ liệu ưu tiên:
estimator giải thích được của LTT LLM khi đủ token/model metadata, sau đó median
lịch sử theo resource/job_type; vẫn thiếu thì `null`. Không lấy `position * 30`.

## Client và event

- Polling GET job là baseline bắt buộc, thêm `poll_after_ms` khi active.
- Webhook giữ terminal milestone, không spam vị trí.
- SSE lifecycle là P1: chỉ làm nếu có thể tái dùng event hiện hữu mà không tạo
  queue/event engine thứ hai; nếu chưa thì ghi rõ deferred.
- Sync/stream mặc định giữ immediate lease + 429 theo Q114.

## Rollback

Code rollback bỏ dùng metadata/ranking mới nhưng giữ hai cột additive vô hại.
Migration downgrade chỉ dùng ở môi trường chưa có dữ liệu cần giữ; production
ưu tiên roll-forward vì DROP cột làm mất audit metadata.
