# Hợp đồng admission/queue cho LTT LLM

> ⚠️ **ĐÃ THAY bởi L-22/L-23** (`docs/ltt_llm_dual/DECISION_LOG.md`) — ảnh chụp 28/08, thời
> `parallel=1`. Nhận theo ngân sách KV, máy A quyết định nhận, cổng máy B là rào vật lý;
> đường đi hiện hành: `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md`; số theo model: `ngan_sach.HO_SO`.

Trạng thái: Q0–Q3 của H41.9 đã triển khai ngày 2026-08-28 theo Q114. Số đo GPU
Q111/Q112 vẫn là nguồn cho cấu hình `parallel=1`, không chạy lại ở pha
CPU/CSDL/mock.

## 1. Một admission plane, không dựng queue thứ hai

```text
POST /jobs ──> jobs (durable queue) ──> worker ──┐
                                                ├─> admission lease ─> máy B
SYNC_BILLED ────────────────────────────────────┤
STREAM ─────────────────────────────────────────┘
```

- `jobs` là nguồn chân lý duy nhất cho công việc có chờ, polling, hủy và retry.
- Lease chỉ biểu diễn **quyền đang thực thi** trên một tài nguyên; nó không chứa
  payload, không được scheduler dùng làm queue và phải tự hết hạn khi chủ chết.
- SYNC_BILLED/STREAM không tạo job ngầm. Không có slot thì trả 429 trước hold
  credit/provider; client dùng `Retry-After` hoặc tự chọn `/jobs` nếu muốn chờ.
- Gateway máy B giữ một slot như chốt fail-closed cuối. Nó không thay admission
  plane và không giữ request thứ hai trong hàng đợi ẩn.

## 2. Tên tài nguyên và giới hạn

Tool khai `admission_resource` trong manifest; nền tảng không suy từ app slug,
tên model nội bộ hay hostname. Mọi request cùng chuỗi tài nguyên tranh cùng một
pool slot dù đi qua route nào.

Ba giới hạn của durable queue được kiểm trong một transaction:

1. global queued cap: tổng job `queued` mà Public API đã nhận;
2. resource queued cap: job `queued` của cùng `admission_resource`;
3. account active cap: `queued + running` của một account, kèm cap resource của
   account khi được cấu hình.

Thứ tự khóa luôn cố định `global → resource → account`; sau khi có khóa phải
đếm lại rồi mới insert. PostgreSQL dùng transaction advisory lock và tự nhả ở
commit/rollback. SQLite chỉ kiểm logic đơn luồng; race phải có test PostgreSQL
thật. `SKIP LOCKED` chỉ dành cho consumer claim queue, không dùng làm quota lock.

## 3. Trình tự không được đảo

### Durable async

```text
validate → idempotency → policy/rate → lock+cap → job+credit hold → commit
→ worker claim → execution lease → provider → settle/refund → terminal
```

Queue đầy bị từ chối trước tiền. Worker không lấy được lease thì ghi
`resource_wait`, trả job về `queued`, đặt `next_run_at` và **không tăng attempt**.

### SYNC_BILLED

```text
validate/time budget → idempotency → policy/rate → execution lease
→ credit hold+commit → provider → settle/refund → release lease
```

Không giữ transaction CSDL suốt lúc gọi model. Mọi đường thoát sau hold phải
settle hoặc refund; mọi đường thoát sau lease phải release hoặc để TTL thu hồi.

### STREAM

```text
validate → policy/rate → execution lease → credit hold+commit
→ open stream → heartbeat → measured settlement → release lease
```

Client ngắt thì chỉ tính phần token đã đo theo Q107. Nếu chưa mở được upstream,
hoàn đủ. Lease sống tới `finally` của generator, không chỉ tới lúc trả headers.

## 4. State machine và lỗi

Job giữ state machine hiện có:

```text
queued → running → done | error | cancelled
   ↑         |
   └─ resource_wait/retry_scheduled
```

- `resource_wait` là event/chờ tài nguyên, không phải failed attempt.
- Terminal không quay lại active.
- 413 là lỗi input, không retry. 429 trước provider có thể retry có backoff.
- Timeout/kết nối vỡ **trước** khi provider nhận có thể retry theo ngân sách.
- Provider đã nhận nhưng worker chết/mất kết quả là `ambiguous_provider`: không
  tự chạy lại side effect. Operator/client được thấy trạng thái an toàn đã lọc;
  credit chỉ settle khi có số đo đáng tin, nếu không thì refund theo luật hiện có.

## 5. Fairness và quan sát

Trong một tài nguyên, giữ FIFO ổn định `(created_at, id)` cho từng account rồi
round-robin giữa account; aging ngăn job cũ bị đói. Không ưu tiên theo số tiền.

Mỗi admission trace tối thiểu có: resource, mode, correlation/job id,
`enqueued_at`, `admitted_at`, `released_at`, queue/admission delay, attempt,
worker/holder và kết quả (`released`, `rejected`, `expired`, `ambiguous`). Không
ghi prompt, tool payload, token bí mật hay credential.

Metrics tối thiểu: queue depth theo resource, oldest queued age, accepted,
rejected theo lý do, active leases, expired leases, resource-wait count và
admission-delay. Số phải tồn tại qua process restart bằng mẫu CSDL hiện có hoặc
được tái dựng từ row bền; counter trong RAM không được là bằng chứng duy nhất.

## 6. Ma trận kiểm trước GPU

| Ca | Bất biến |
|---|---|
| 100 request cùng account | không vượt account cap; không hold thừa |
| 100 request nhiều account | không vượt global/resource cap |
| cùng idempotency key lặp 10 lần | một job/hold hoặc replay đúng |
| sync + stream + async cùng lúc | tối đa số execution lease đã cấu hình |
| worker không lấy được slot | job về queue, attempt không tăng |
| crash trước/sau provider accept | chỉ ca trước được retry tự động |
| restart web/worker | lease mồ côi tự hết hạn, job bền còn nguyên |
| tenant burst + tenant lẻ | tenant lẻ tiến triển nhờ round-robin/aging |

Q0–Q3 chỉ dùng SQLite cho logic, PostgreSQL scratch cho race và provider mock
cho lỗi. Không đọc trạng thái GPU thật trong unit test. Q4 chỉ bắt đầu sau khi
ma trận này xanh và full gate không có regression thuộc `ltt_llm`.

### Kết quả Q2 đã khóa

- Scheduler giữ FIFO ổn định trong account, luân phiên theo mốc claim bền vững
  của account/resource và đẩy job chờ quá 5 phút lên trước để chống starvation.
  Giá/credit tuyệt đối không tham gia phép xếp thứ tự.
- `provider_state` ghi bền `dispatched → completed|rejected|ambiguous`. Marker
  được commit ngay trước outbound HTTP; phản hồi xác định gỡ ambiguity trước
  khi fallback provider khác.
- 429/resource-busy trở về `queued`, có backoff và không tăng attempt. 413/OOM
  là terminal `rejected`. Mất kết nối sau POST hoặc worker chết sau dispatch là
  terminal `ambiguous`, không tự phát lại request có thể đã tạo side effect.
- Callback terminal của orphan chỉ chạy ở lần chuyển `running → error`; refund
  hiện có vẫn idempotent nên reclaim lặp không hoàn tiền/webhook lần hai.

### Kết quả Q3 đã khóa

- Job có `admitted_at` riêng, chỉ ghi ngay trước handler sau khi đủ execution
  lease/GPU lease; `started_at` vẫn là mốc worker claim. Vì vậy resource-wait
  không còn làm queue delay thực bị rút ngắn giả tạo.
- `/ops/jobs-metrics` đọc từ row bền để trả queue depth, oldest queued age và
  active/expired-candidate execution lease theo resource; đồng thời trả admission
  p50/p95, resource-wait và provider dispatched/rejected/ambiguous. Mẫu counter
  24 giờ được cộng từ `api_metric_samples`, không phụ thuộc RAM của một process.
- Execution lease đếm acquired/rejected/released/expired; queue cap rejection
  đếm thêm lý do global/resource/account. Flush rồi reset process vẫn đọc lại
  đúng từ CSDL.
- `tools/bench_llm_admission.py` chỉ dùng SQLite vứt đi, provider mock và không
  đọc GPU. Mốc 100 job/5 account: 679,26 submit/s, 47,90 drain/s, poll p50
  0,634 ms; 0 provider call, 0 GPU read. Đây là baseline control-plane cục bộ,
  không được diễn giải thành p95 production/PostgreSQL.
- Test restart đóng engine thật: snapshot vẫn giữ nguyên; orphan pre-dispatch
  được reclaim về queue, còn orphan post-dispatch giữ terminal ambiguous của Q2.

## 7. Căn cứ kỹ thuật

- PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` nói rõ ảnh chụp bị bỏ qua lock
  là không nhất quán, nhưng phù hợp cho nhiều consumer của queue; vì vậy nó ở
  `jobs.claim`, không ở phép kiểm quota.
- Transaction advisory lock tự nhả khi transaction kết thúc, phù hợp bao quanh
  `count + insert + credit hold`; mọi caller phải dùng cùng namespace khóa.
- Serializable cũng đúng nhưng buộc retry toàn transaction khi SQLSTATE 40001;
  đường API hiện chưa có bộ retry transaction chung, nên khóa tường minh là MVP
  nhỏ và kiểm chứng được hơn.

Nguồn chính thức:

- PostgreSQL `SELECT`, mục locking clause:
  https://www.postgresql.org/docs/current/sql-select.html
- PostgreSQL advisory locks:
  https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
- PostgreSQL xử lý serialization failure:
  https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html
