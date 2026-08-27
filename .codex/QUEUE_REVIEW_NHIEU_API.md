# Rà soát hàng đợi nhiều API → GPU/model

Ngày: 2026-08-27

## Kết luận ngắn

Nền tảng hiện có một hàng đợi bền vững khá tốt cho các endpoint bất đồng bộ:
PostgreSQL là nguồn chân lý, claim nguyên tử bằng `FOR UPDATE SKIP LOCKED`,
idempotency/credit được khóa, worker heartbeat, reclaim job mồ côi và GPU lease
độc quyền. Đây là nền tảng đúng để làm MVP.

Tuy nhiên toàn bộ request LLM hiện **chưa** đi qua cùng một hàng đợi. `POST
/api/v1/jobs` đi qua `platform_core.jobs`, còn `/chat/completions` và các đường
streaming mở kết nối thẳng tới provider `ltt_llm`. Vì vậy giới hạn `max_active_jobs`
không bảo vệ được mọi đường gọi model. llama.cpp có hàng đợi và slot riêng bên
trong process, nhưng đó là lớp thứ hai; nó không thay thế admission control,
fairness, billing hoặc retry của nền tảng.

## Cơ chế đang có

| Lớp | Đã có | Ý nghĩa |
|---|---|---|
| Durability | Bảng `jobs` + `job_events` | Không mất trạng thái khi web/worker restart |
| Claim | `FOR UPDATE SKIP LOCKED`, index `(status,next_run_at,created_at)` | Nhiều worker không claim trùng |
| Duplicate | Public `Idempotency-Key` + unique DB + advisory lock; `dedupe_key` cho job nội bộ | Chống F5/retry tạo job hoặc charge hai lần |
| Admission | RPM key/account, create RPM, active jobs/account, daily credit | Chặn một phần burst trước khi giữ credit |
| Failure | retry giới hạn/backoff, cancel hợp tác, orphan reclaim | Không retry vô hạn và không để job mồ côi |
| GPU | lease unique `(host,gpu_uuid)`, heartbeat, headroom 1 GiB, shared claims | Không hai process cùng nạp một card |
| LLM server | llama.cpp có server queue, slots, continuous batching, prompt cache, `/slots`, `/metrics` | Điều phối nội bộ trong một process |

## Khoảng trống và mức độ

### P0 — Hai hàng đợi cho LLM

`/chat/completions` giữ credit rồi gọi provider đồng bộ; streaming cũng mở SSE
thẳng tới B. Các request này không tạo `Job`, không chiếm GPU lease của
`platform_core`, không có queue position và không có global concurrency. Khi
nhiều API key cùng gọi, lớp duy nhất còn lại là slot/429 của llama.cpp. Điều này
làm cho billing, fairness và backpressure của nền tảng không đồng nhất.

**MVP bắt buộc:** chọn một trong hai hợp đồng và áp dụng cho mọi đường LLM:

1. chuyển mọi request dài/chargeable sang `Job` bất đồng bộ; hoặc
2. tạo một `LLMAdmission` dùng chung trước cả sync và streaming, với semaphore
   phân布 theo model/GPU và hàng đợi có độ sâu hữu hạn.

Không được để mỗi route tự có một semaphore riêng.

### P0 — Không có giới hạn độ sâu hàng đợi toàn hệ thống

`max_active_jobs` hiện là theo tài khoản. Nhiều tài khoản có thể cùng tạo hàng
nghìn job queued và giữ credit trong thời gian dài. Cần thêm:

- `GLOBAL_QUEUE_MAX` và `GLOBAL_QUEUED_MAX_PER_RESOURCE`;
- từ chối trước hold bằng `429 queue_full` + `Retry-After`;
- metric `queue_depth`, `queue_oldest_age`, `queue_rejected_total`;
- TTL/cleanup cho job queued quá hạn nếu sản phẩm cho phép.

### P0 — Race giữa kiểm tra active và insert

`enforce_active_jobs()` đếm rồi `jobs.submit()` tạo dòng. Hai request khác
Idempotency-Key của cùng user có thể cùng thấy còn slot và cùng vượt qua. Public
idempotency chỉ giải quyết **cùng key**, không giải quyết hai ý định khác nhau.

**MVP:** khóa theo account/resource trong transaction (PostgreSQL advisory lock
hoặc một row quota được `FOR UPDATE`), đếm lại và insert trong cùng vùng khóa.
Phải có test PostgreSQL thật cho N request đồng thời.

### P1 — FIFO toàn cục gây head-of-line/fairness kém

`claim()` sắp theo `created_at`. PostgreSQL xác nhận `SKIP LOCKED` phù hợp cho
queue consumer nhưng tạo một view không nhất quán; thứ tự chỉ đáng tin khi có
`ORDER BY` duy nhất. Job dài, job cần GPU đang bận, hoặc một tenant burst lớn
có thể làm tenant khác chờ lâu.

**MVP an toàn:** giữ FIFO trong từng resource class, thêm aging/fair-share theo
account (ví dụ virtual finish time hoặc round-robin account), và dùng
`created_at, id` làm thứ tự ổn định. Không ưu tiên theo giá tiền nếu chưa có
quyết định sản phẩm.

### P1 — Retry có nhưng chưa phân loại đủ theo lỗi

Backoff hiện đúng hướng, nhưng cần phân loại rõ:

- lỗi trước provider nhận request: có thể retry;
- provider đã nhận nhưng worker chết trước ghi kết quả: **không retry mù** nếu
  side effect không idempotent;
- 429/busy: không cooldown nhầm provider key, retry theo `Retry-After`;
- 413/context quá dài: lỗi client, không retry;
- OOM/decode cliff: không retry cùng thông số vô hạn, chuyển circuit breaker.

### P1 — Lease GPU và slot llama.cpp chưa cùng một ngân sách

GPU lease bảo vệ process worker, còn llama.cpp `-np/--parallel` và continuous
batching bảo vệ các slot bên trong server. Nếu nhiều đường API gọi trực tiếp
provider, lease không nhìn thấy chúng. Cần một ngân sách thống nhất:

`admitted_requests <= min(platform_resource_limit, llama_slots, KV_budget)`.

Trên RTX 3090/Qwen context dài, MVP nên `parallel=1` cho public canary; chỉ
tăng sau khi đo KV fragmentation và p95.

### P1 — Queue position và ETA chưa phải dữ liệu hợp đồng

Job có trạng thái/progress nhưng chưa có `queue_position`, `enqueued_at`,
`started_at` public rõ ràng, hoặc ETA có confidence. Không nên hiển thị ETA giả.
Thêm position chỉ là snapshot; phải ghi `queue_delay_ms` khi claim để metric
không phụ thuộc việc client poll.

### P2 — Polling và cache

Client poll quá dày có thể tự biến thành DDoS đọc. Endpoint status phải có
`ETag`/`Last-Modified` hoặc giới hạn poll/RPM; response job phải `no-store` nếu
chứa dữ liệu nhạy cảm. Không cache kết quả theo URL nếu quyền sở hữu nằm trong
request.

## Hợp đồng MVP đề xuất

```text
submit -> validate -> capacity check -> account/resource lock
        -> idempotency claim -> credit hold + Job insert (one commit)
        -> queued

dispatcher -> choose fair eligible job -> atomically running + attempt
           -> acquire GPU/model admission -> execute
           -> heartbeat + progress -> complete/fail (one terminal transition)

restart -> running with stale heartbeat => reclaim once, bounded retry
cancel  -> queued: terminal immediately; running: cooperative cancel + settle
```

Bất biến phải giữ:

1. một logical request chỉ có một job và một hold;
2. một job chỉ có một owner/attempt đang chạy;
3. terminal state không quay lại queued/running;
4. settle/refund chỉ một lần;
5. queue full bị từ chối trước hold;
6. retry dùng cùng lineage nhưng attempt mới, không tạo charge mới;
7. GPU lease/model admission luôn được release trong `finally`;
8. worker restart không chạy lại side effect không biết idempotency;
9. mọi client retry dùng lại cùng idempotency key;
10. mọi route LLM dùng cùng một admission plane.

## Test matrix trước public canary

| Ca | Kỳ vọng |
|---|---|
| 100 request cùng lúc, một account | không vượt active limit; không âm credit |
| 100 request, nhiều account | queue depth bị chặn; không tenant độc quyền |
| cùng Idempotency-Key retry 10 lần | đúng một job/hold, replay ổn định |
| hai key khác nhau cùng account | quota lock không vượt giới hạn |
| worker chết sau claim | reclaim một lần, không claim trùng |
| worker chết sau provider nhận | không side-effect duplicate; cần trạng thái ambiguous |
| GPU đầy | job queued/resource_wait, không OOM, không tính retry lỗi |
| 429 provider | giữ nguyên key health, retry theo backoff |
| 413 context | trả 413, không retry |
| cancel queued/running race | terminal nhất quán, refund một lần |
| restart server khi stream mở | client nhận trạng thái rõ, không charge mù |
| polling burst | rate-limit đọc, không ảnh hưởng submit/worker |
| llama slots đầy | platform không tiếp tục nhận vô hạn; trả queue_full/busy chuẩn |

## Thứ tự triển khai

1. Đo riêng sync/streaming hiện tại; không mở thêm concurrency.
2. Dựng `LLMAdmission` dùng chung và global queue budget.
3. Khóa race active-limit bằng PostgreSQL transaction lock.
4. Thêm fair scheduling + queue metrics/position.
5. Bổ sung test concurrency PostgreSQL và crash/ambiguous side effect.
6. Chạy canary một alias, `parallel=1`, theo dõi p95/VRAM/429/OOM.
7. Chỉ sau đó mới quyết định tăng `parallel`, cap input/output hoặc mở rộng
   allowlist public.

## Tài liệu đối chiếu

- llama.cpp server queue/slots/batching: <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README-dev.md>
- llama.cpp server flags (`--parallel`, continuous batching, prompt cache,
  metrics, slots): <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>
- PostgreSQL `SKIP LOCKED`: <https://www.postgresql.org/docs/current/sql-select.html>
- vLLM scheduler (`max_num_batched_tokens`, `max_num_seqs`, FCFS/priority):
  <https://docs.vllm.ai/en/latest/api/vllm/config/scheduler/>
