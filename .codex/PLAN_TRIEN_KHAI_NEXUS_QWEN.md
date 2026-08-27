# Plan triển khai Nexus + benchmark Qwen context dài + admission/queue nhiều API

Ngày: 2026-08-27. Mục tiêu: cài Nexus đầy đủ trên máy B, bảo đảm tự khởi
động sau reboot, chuẩn hóa hàng đợi cho nhiều API cùng gọi model/GPU, chạy
benchmark Qwen bằng job async không phụ thuộc timeout proxy, sau đó mới chốt
cap public. Các việc không cần GPU phải được làm trước hoặc xen kẽ trong lúc
GPU đang bận; không dùng thời gian GPU quý giá cho việc có thể kiểm tra bằng
DB/mock/provider giả.

## Nguyên tắc

1. Nexus là kênh vận hành chính; không dùng OpenSSH thường trực.
2. Mọi thay đổi code/config bắt đầu ở máy A, build thành artifact, rồi mới
   chuyển sang B. Không sửa tay cấu hình production và để source lệch.
3. Không mở public API trước khi có số đo thật của đúng model/build/GPU.
4. Job đang chạy khi Nexus restart được ghi `INTERRUPTED`, không tự chạy lại
   lệnh tuỳ ý. Job đã xong giữ nguyên log, exit code và trạng thái trong SQLite.
5. Mỗi pha có bằng chứng; không dùng kế hoạch hoặc số test dự kiến làm bằng
   chứng hoàn thành.

## Nguyên tắc phân bổ tài nguyên và cửa sổ GPU

Hàng đợi được xem là hai tầng tài nguyên, không phải một FIFO duy nhất:

```text
control plane/API/DB  (CPU, có thể chạy liên tục)
        |
        +--> queue CPU-only / provider-mock
        |
        +--> admission GPU/model --> GPU lease --> llama.cpp slot/KV --> job
```

Mỗi job hoặc request LLM phải có metadata tối thiểu:

```text
resource_class = cpu | gpu:<model> | gpu:<host>:<uuid>
requires_gpu   = true/false
estimated_vram_mb, context_tokens, output_tokens
exclusive_gpu  = true/false
priority/aging_key, idempotency_key
```

Quy tắc vận hành:

1. Job CPU-only không được chờ GPU; có thể chạy song song với benchmark nếu
   không gây tranh chấp CPU/đĩa.
2. Job GPU chỉ được claim sau khi admission chung cấp ngân sách và GPU lease;
   không để `/chat/completions`, streaming hoặc endpoint mới bypass lớp này.
3. `queue_full` phải được quyết định trước khi giữ credit. `resource_wait` do
   GPU bận không phải là failed attempt và không trừ retry budget.
4. Trong cửa sổ benchmark GPU, chỉ cho phép một workload GPU đã khai báo;
   request GPU ngoài benchmark phải bị queue hoặc trả `Retry-After`, không
   chạy chen để làm sai số đo.
5. Mọi số đo GPU phải ghi `queue_delay`, `admission_delay`, `load_time`,
   `prefill`, `decode`, `total`, peak VRAM/nhiệt/công suất và build/model.

### Ma trận công việc và cách xen kẽ

| Hạng mục | Cần GPU thật | Chạy khi GPU đang bận | Bằng chứng kết thúc |
|---|---:|---:|---|
| DB schema, quota lock, global queue cap | Không | Có | migration + PostgreSQL concurrency tests |
| `LLMAdmission` và route wiring | Không ở pha đầu | Có, dùng provider mock | tất cả route đi qua một admission plane |
| idempotency, credit settle/refund, retry classification | Không | Có | test cùng key/khác key/crash |
| fair scheduler, queue position, metrics | Không | Có | test nhiều tenant + metric snapshot |
| contract/API docs, SDK, poll/ETag/no-store | Không | Có | contract tests |
| unit/static/gate/build/release | Không | Có | lệnh gate thật, artifact hash |
| cold model load/context ladder | Có | Không | GPU telemetry + kết quả lặp lại |
| warm resident prefill/decode | Có | Không | warm-session report, không tính load đầu |
| GPU concurrency/slot/KV sweep | Có | Không | p95, VRAM, 429/OOM, không decode cliff |
| canary public và soak | Có | Không | 15–30 phút telemetry + credit audit |

### Chu kỳ một cửa sổ GPU

```text
G0 chuẩn bị (CPU): khóa queue GPU, snapshot config, GPU idle check
G1 đo độc quyền: một workload GPU, telemetry 2 giây, không deploy/restart
G2 thu dọn: chờ job terminal, release lease, kiểm tra VRAM/nhiệt về nền
G3 phân tích (CPU): tính median/p95, cập nhật hồ sơ, quyết định arm kế tiếp
```

Nếu G1 lỗi hoặc bị huỷ, đánh dấu arm **invalid**, không đưa vào baseline. Không
đồng thời chạy benchmark cold-start và warm-session trong cùng một phép đo.

## Q0 — khóa hợp đồng hàng đợi trước khi sửa code (CPU-only)

Đây là hạng mục kiến trúc bắt buộc, có thể triển khai hoàn toàn không cần GPU:

- Chọn một admission plane dùng chung cho `/api/v1/jobs`,
  `/chat/completions` và streaming; giữ tương thích sync bằng cách chờ ngắn
  sau admission hoặc trả `job_id` khi vượt ngưỡng.
- Chốt resource class, global queue cap, cap theo resource và cap theo account.
- Chốt state machine: `queued → running → terminal`, `resource_wait` không phải
  failed; terminal state bất biến.
- Chốt hợp đồng idempotency, credit hold/settle/refund và trạng thái
  `ambiguous_provider` khi worker chết sau khi provider đã nhận.
- Chốt trường quan sát: `enqueued_at`, `started_at`, `queue_delay_ms`,
  `admission_delay_ms`, `attempt`, `worker`, `resource_class`.

**Qua khi:** tài liệu hợp đồng được review, không còn route LLM nào có đường
đi riêng trong sơ đồ, và có test contract dùng provider mock.

## Q1 — admission, global cap và khóa quota (CPU/DB)

Triển khai theo thứ tự nhỏ nhất:

1. Thêm global queued cap và cap theo resource; reject trước credit hold.
2. Bao bọc active-limit check + insert bằng account/resource lock trong cùng
   transaction; kiểm tra lại quota sau khi lấy lock.
3. Tách `resource_wait` khỏi retry/attempt; trả `Retry-After` có giới hạn.
4. Đưa sync/streaming qua `LLMAdmission`; provider mock trước, GPU thật sau.
5. Thêm metrics queue depth/oldest age/rejected/admission delay.

**Test không GPU:** 100 request cùng account, 100 request nhiều account, hai
idempotency key khác nhau, retry cùng key 10 lần, queue đầy, polling burst.

**Qua khi:** không vượt active limit, không âm hoặc charge trùng credit, queue
không tăng vô hạn, mọi route LLM có cùng admission trace.

## Q2 — fair scheduler và khôi phục lỗi (CPU/DB)

- Giữ thứ tự ổn định `(created_at, id)` trong từng resource class.
- Thêm round-robin/fair-share theo account và aging cho job chờ lâu.
- Không ưu tiên theo giá tiền khi chưa có quyết định sản phẩm.
- Bổ sung retry policy theo lỗi: 429, 413, OOM, timeout, worker crash và
  provider-accepted/worker-dead.
- Kiểm tra cancel race, reclaim orphan và settle/refund chỉ một lần.

**Test không GPU:** dùng provider giả có kịch bản trả 429/413/timeout, chết sau
claim, chết sau provider-accept; chạy PostgreSQL concurrency thật.

**Qua khi:** không claim trùng, không retry side effect mù, tenant burst không
độc chiếm queue, terminal state không quay ngược.

## Q3 — quan sát và tải giả (CPU-only)

- Thêm dashboard/log fields cho queue, admission, worker, credit và provider.
- Tạo load harness chỉ dùng provider mock để đo throughput của API/DB và poll.
- Tạo test restart web/worker không có GPU; xác minh job state sau restart.
- Chạy static lint, contract tests và regression khi GPU đang dành cho benchmark.

**Không được:** đọc tải GPU thật trong unit test; đưa benchmark/mock artifacts
vào dữ liệu production; dùng HTTP cache cho response job chứa dữ liệu riêng.

## Q4 — tích hợp GPU/model admission (GPU window)

Chỉ bắt đầu sau khi Q0–Q3 xanh:

- Nối `LLMAdmission` với GPU lease và ngân sách slot/KV của llama.cpp.
- RTX 3090/Qwen context dài: canary `parallel=1`, một GPU request tại một
  thời điểm; request còn lại phải nằm trong queue có giới hạn.
- Ghi riêng load-time và warm-session; không trộn hai loại vào một baseline.
- Chạy ladder context và warm combined prompt+generation theo từng cửa sổ G0–G3.
- Sau mỗi arm: kiểm tra VRAM/nhiệt/công suất về mức nền trước arm kế tiếp.

**Qua khi:** không OOM, không spill CPU ngoài ngưỡng, không decode cliff,
queue delay đo được, và kết quả lặp lại trong biên đã chốt.

## Q5 — thử concurrency GPU có kiểm soát (GPU window)

Chỉ thử `parallel=2` hoặc cao hơn nếu Q4 pass:

1. Giữ cùng model/build/KV/context; thay đúng một biến `parallel` mỗi arm.
2. Chạy 1, 2, rồi tải hỗn hợp short/long; không tăng đồng thời context cap.
3. So sánh throughput tổng, p50/p95 TTFT, decode, VRAM peak, nhiệt, 429/OOM.
4. Dừng ngay khi p95 hoặc VRAM vượt ngưỡng, decode tụt không hồi phục, hoặc
   fairness xấu; quay về cấu hình arm trước.

**Qua khi:** concurrency mới tốt hơn `parallel=1` theo tiêu chí đã định, không
chỉ nhanh hơn throughput mà làm hỏng p95, queue fairness hoặc độ ổn định.

## Q6 — canary và nghiệm thu liên tục

- Mở một alias/canary key duy nhất; các alias khác vẫn giữ cấu hình cũ.
- Chạy request ngắn, 60K, 80–90K, vượt cap, đồng thời gửi CPU-only jobs.
- Xác minh GPU job chờ đúng queue, CPU-only job vẫn tiến triển, không bypass.
- Theo dõi 15–30 phút: queue depth, queue age, admission delay, p95, VRAM,
  nhiệt, 429/OOM, retry, credit và log audit.
- Reboot B sau canary; kiểm tra queue/job terminal và Nexus tự khởi động.

**Rollback:** tắt canary alias, đưa provider/catalog/cap về artifact trước,
reload service; không xóa job history hay credit ledger.

## Tiêu chí không được bỏ qua trước public

1. Ba P0 đã xanh: admission plane chung, global queue cap, quota-lock race.
2. Có test crash/ambiguous provider và idempotency thật.
3. Có queue metrics và log đủ để điều tra một request từ API tới GPU.
4. Có baseline warm-session riêng với GPU telemetry; benchmark cold-start chỉ
   dùng để biết chi phí nạp model.
5. `parallel` chỉ tăng sau canary có số đo; mặc định an toàn vẫn là 1.
6. Chạy `python tools\gate.py --vong-lap` sau mỗi thay đổi và
   `python tools\gate.py` trước khi báo hoàn tất.

## P0 — kiểm tra quyền và snapshot

- Kiểm tra node B online, fingerprint, capability, service hiện có, cổng 8299,
  GPU/VRAM, ổ đĩa và checksum artifact.
- Xác nhận Nexus credential có `file.write`, `command.run`, `service.restart`
  hoặc `command.run_admin`. Nếu thiếu quyền cài/restart, dừng trước bước thay
  đổi và yêu cầu bootstrap local admin.
- Backup cấu hình Nexus và LTT LLM hiện tại; ghi đường rollback và thời điểm.

**Qua khi:** snapshot đọc lại được, artifact có SHA-256, biết rõ quyền thật.

## P1 — cài Nexus bằng artifact đã kiểm tra

- Dùng `LTT-Nexus-Setup.zip` đã build/smoke-test, không copy từ thư mục build
  tạm.
- Cài worker B bằng installer chính thức, giữ data/identity/database ngoài
  release directory.
- Kiểm tra service wrapper, firewall, certificate pinning và allowed roots.
- Chạy `nexus version` và health check qua controller A.

**Qua khi:** service ở trạng thái RUNNING, `/health` trả đúng node/version,
không có secret trong log, audit ghi đủ thao tác.

## P2 — xác minh khả năng sống qua reboot

- Reboot B bằng kênh quản trị được phê duyệt.
- Chờ heartbeat từ B về A; kiểm tra service tự khởi động, certificate,
  capability, GPU metrics và cổng cần thiết.
- Chạy một lệnh async ngắn, đọc `job_id`, status, log và exit code.

**Rollback:** nếu service không tự lên, giữ kênh bootstrap tạm thời; khôi phục
release trước hoặc chạy rollback script. Chỉ đóng OpenSSH sau khi P2 pass.

## P3 — OpenSSH bootstrap (chỉ khi P0 thiếu quyền)

- Cài OpenSSH Server bằng local Administrator hoặc quyền elevated đã được cấp.
- Chỉ key authentication, firewall giới hạn từ máy A, không dùng password và
  không lưu private key trong repo/log.
- Dùng SSH để hoàn tất P1/P2, sau đó stop/disable `sshd`, xoá rule firewall và
  key tạm.
- Xác nhận cổng 22 đóng và Nexus vẫn điều khiển được B.

OpenSSH không phải dependency vận hành lâu dài; nếu Nexus đã có quyền elevated
thì bỏ qua toàn bộ P3.

## P4 — benchmark async Qwen

Gửi `POST /api/v1/exec/async` tới B qua controller A với lệnh benchmark đã
được chuẩn hóa. Không gọi trực tiếp `/exec` đồng bộ cho phép đo dài.

Mỗi job phải ghi:

- `job_id`, command profile, build/model/quant/KV;
- context và prompt size;
- VRAM trước/sau/đỉnh, nhiệt độ, công suất;
- prefill tok/s, TTFT, decode tok/s, p95 token latency;
- MTP acceptance, lỗi, timeout, exit code và log đầy đủ.

Ladder tối thiểu:

```text
65536 → 73728 → 81920 → 90112 → 98304 → 131072
```

Mỗi mốc lặp 3 lần, bỏ warm-up đầu tiên. Prompt phải là prompt thật của quy
trình code/đọc log, không chỉ token ngẫu nhiên. Kiểm tra GPU sạch trước mỗi arm.

**Qua khi:** mốc được chọn không có decode cliff, không spill CPU, còn biên
VRAM an toàn, không vượt timeout workload thực tế và kết quả lặp lại được.

## P5 — chốt thông số source và API

Nếu mốc 131072 đạt, cấu hình ứng viên:

```text
engine_context       = 131072
public_input_cap     = 90000
output_hard_cap      = 32768
context_reserve      = 8192
dynamic_output       = min(requested, context - actual_input - reserve)
KV                   = q8_0
MTP                  = draft-mtp / n-max 2
parallel             = 1
```

Nếu 90K không ổn định, chọn mốc thấp hơn từ ladder; không ép 90K vì mục tiêu
đã đặt ra.

Đồng bộ một commit các file engine/gateway/provider catalog/CamCLI/tài liệu và
test tổng `input + output <= context`. Không thay riêng một biến trên B.

## P6 — gate, release, deploy

Trên repo LTTSTUDIOSAPP:

```powershell
python tools\gate.py --vong-lap
python tools\gate.py
```

Trên repo Nexus:

```powershell
.venv\Scripts\python.exe -m ruff check apps packages tests
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\package_release.py
```

Chỉ artifact đã smoke-test và có SHA-256 mới được đưa sang B.

## P7 — mở public theo canary

- Mở trước một model alias/canary key, không bật đại trà ngay.
- Test request ngắn, request 60K, request 80–90K và request vượt cap.
- Xác nhận vượt cap trả 413; không biến thành 503/retry storm.
- Theo dõi 15–30 phút: latency, timeout, VRAM, GPU contention, log và credit.
- Chỉ sau canary pass mới mở allowlist public đầy đủ.

Rollback public: đưa provider catalog/cap về bản trước, reload service và xác
nhận alias cũ vẫn hoạt động. Giữ artifact và backup trước deploy.

## P8 — nghiệm thu cuối

- Reboot B lần cuối sau khi public canary đã pass.
- Kiểm tra Nexus tự lên, async job mới chạy được, job cũ hoàn tất vẫn đọc được.
- Chạy `python tools\gate.py` lần cuối trên A và ghi kết quả thật vào nhật ký.
- Cập nhật `QUYET_DINH_NEN_TANG.md`, `KE_HOACH_TRIEN_KHAI.md` và
  `NHAT_KY.md`; commit source và artifact metadata riêng, không commit secret.
