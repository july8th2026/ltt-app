# H26 Operations Runbook — Job, storage và credit

**Phạm vi:** nền tảng `app.lttstudios.com`, mọi app dùng hàng đợi Job chung.  
**Nguyên tắc:** ưu tiên bảo toàn dữ liệu và tiền của khách; không chạy purge,
retry hàng loạt hoặc restore production chỉ để làm mất dấu cảnh báo.

## 1. Tín hiệu và phân loại sự cố

1. Kiểm tra `/health/live`, `/health/ready` và `/ops/jobs-metrics` bằng tài khoản
   operator. Đọc theo từng app; `insufficient_data` không phải PASS.
2. Dùng correlation ID và Job ID để mở timeline. Customer chỉ thấy message sản
   phẩm; operator có internal event đã lọc.
3. Phân loại trước khi thao tác:

| Nhóm | Dấu hiệu | Hành động đầu tiên |
|---|---|---|
| Worker restart/orphan | `running` quá heartbeat, stale tăng | kiểm service/host rồi để reclaim có giới hạn |
| Provider outage | retry tăng ở một job type, nhiều lỗi cùng thời điểm | dừng canary mới, kiểm credential/network/status provider |
| Storage/R2 | presign trả `None`, log storage error, upload/download lỗi | kiểm R2 config/CORS/network; không proxy file >90 MB qua tunnel |
| GPU/resource | `resource_wait`, GPU lease stale hoặc OOM | kiểm từng GPU riêng, nhiệt/VRAM và worker mapping |
| Credit | hold không có settle/refund sau terminal | cô lập Job ID, đối soát ledger; không sửa số dư trực tiếp |
| Event/log | `event_write_failures > 0` | coi là hard failure, dừng release và kiểm CSDL |

Không chép `params`, prompt, email, token hay raw provider response vào ticket.
Support export dùng `GET /ops/jobs/{job_id}/support-export`.

## 2. Worker chết hoặc job mồ côi

1. Không tạo Job thay thế bằng tay khi Job cũ còn `running`.
2. Kiểm `heartbeat_at`, worker service và GPU lease. Job còn heartbeat không
   được reclaim.
3. Worker loop sẽ gọi `reclaim_orphans`: lượt cũ được tính là một attempt; còn
   lượt thì về `queued` với backoff, hết lượt thì `error`.
4. Credit hold được giữ qua retry. Chỉ terminal `error/cancelled` mới refund;
   `done` settle đúng một lần.
5. Sau restart, kiểm timeline có `reclaimed`/`retry_scheduled`, số attempt không
   tăng hai lần và không có hai artifact cho cùng Job.

## 3. Provider outage

1. Xác định phạm vi theo `app_slug` + `job_type`; không dùng throughput tổng để
   che một app đang lỗi.
2. Nếu lỗi tạm thời, để retry/backoff hiện hành xử lý. Không bấm retry liên tục.
3. Nếu credential/config sai, sửa secret ngoài repo rồi restart đúng service;
   không đưa giá trị secret vào log/tài liệu.
4. Lỗi provider trước khi ghi Job/log phải qua `job_events.sanitize_text()`.
   Customer không được nhận `Job.error` thô.
5. Khi provider ổn lại, chạy một canary nhỏ; đối soát quote, hold, output và
   settle/refund trước khi mở lưu lượng.

## 4. Storage/R2 outage

1. `try_url_for()`/`try_put_url()` được phép degrade về `None`, nhưng lỗi bất
   ngờ phải tạo log exception đã lọc.
2. Với LocalStorage, ghi qua file `.part<PID>` rồi `os.replace`; lỗi giữa chừng
   không được để lại artifact đích hay partial.
3. Không cho file lớn đi vòng qua Cloudflare khi direct upload hỏng. Mốc vận
   hành vẫn là >90 MB cần R2/CORS đã PASS.
4. Kiểm quyền owner trước khi thử download; không dùng object của user thật cho
   diễn tập.

## 5. Cancel, retry và credit

| Trạng thái | Credit đúng |
|---|---|
| `queued/running` | hold còn nguyên |
| retry về `queued` | không refund rồi hold lại |
| `done` | settle một lần, trả phần ước tính dư nếu có |
| `error` terminal | refund đủ một lần |
| `cancelled` | refund đủ một lần |

`cancel`, `settle` và `refund` phải idempotent. Nếu ledger sai, dừng thao tác và
đối soát các entry theo Job ID; không update số dư vì số dư là tổng sổ append-only.

## 6. Retention và support

1. Dry-run: `python tools\job_retention.py`.
2. Active Job quá policy phải đi recovery, không purge.
3. Backup được xác minh rồi mới chạy batch explicit:
   `python tools\job_retention.py --apply --confirm PURGE`.
4. Job terminal/customer timeline: 365 ngày; internal event: 30 ngày; ledger
   không purge theo Job; artifact theo policy riêng chưa tự xóa.

## 7. Release, rollback và tiêu chí đóng sự cố

Trước release: full `python tools\gate.py`, browser A-Z, secret scan 0, backup
đọc được và có `app.previous`. Canary phải kiểm health, build-meta, một Job thật
nhỏ, event và credit trước production.

Rollback code dùng `deploy/windows/rollback.ps1`; script giữ bản lỗi ở
`app.failed`. Rollback code không tự rollback CSDL. Restore dữ liệu là hành động
riêng, chỉ làm khi đã xác minh backup và hậu quả mất dữ liệu sau thời điểm backup.

Chỉ đóng sự cố khi: health ready; stale/event-write-failure về 0; canary đúng;
ledger đối soát; không còn request fail mới; và nguyên nhân/cách phòng đã ghi
vào nhật ký.
