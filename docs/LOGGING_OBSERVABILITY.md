# Logging & Job Observability — hợp đồng dùng chung

Tài liệu này là runbook cho mọi app trong `apps/`. Mục tiêu là khi một job lỗi,
operator có thể trả lời được: job nào, app nào, loại tác vụ nào, correlation
nào, worker nào xử lý, attempt bao nhiêu, dừng ở mốc nào, bao lâu, và credit đã
giữ/quyết toán/hoàn ra sao — mà không đọc payload riêng tư của khách hàng.

## Audit trước khi nâng cấp

| Lớp | Trước | Sau hạng mục này |
|---|---|---|
| Lịch sử customer | `JobEvent` có submitted/started/progress/completed | Giữ nguyên cho mọi app |
| Log kỹ thuật | claimed/retry/orphan và event app rời rạc | Tự động thêm execution_started/completed/failed/cancelled với attempt, worker, thời lượng, key kết quả và fingerprint lỗi |
| Correlation | Có trên Job/Event nhưng process log không gắn | JSONL có job_id/app_slug/job_type/worker_id/correlation_id |
| Credit | Ledger + settle/refund | Bổ sung hold; settle ghi held/actual/adjustment; refund ghi amount |
| File process log | Chỉ stdout/basicConfig | `logs/ltt-<component>.jsonl`, redact boundary, size rotation |
| Dọn dẹp | Event customer 365 ngày, internal 30 ngày; worker purge mỗi 6 giờ | Giữ policy; file log LTT prune theo `LTT_LOG_RETENTION_DAYS` (mặc định 30) |
| Xóa Job terminal | Operator explicit sau dry-run/backup | Không đổi; không auto-delete Job, artifact hay ledger |

## Event contract

Mọi event đi qua `platform_core.job_events.append()`. `details` là metadata đã
lọc, không phải params/provider response. Event internal không hiện cho customer;
support đọc qua `/ops/jobs/{job_id}/events` hoặc support export.

### Tự động cho mọi app/job

| Code | Visibility | Nội dung chính |
|---|---|---|
| `submitted` | customer | Đã tiếp nhận |
| `claimed` | internal | worker và attempt dự kiến |
| `started` | customer | Bắt đầu |
| `execution_started` | internal | worker, attempt |
| `progress` | customer | percent, message, status |
| `execution_completed` | internal | duration_ms, result key names, credit cost được khai báo |
| `completed` | customer | Hoàn tất |
| `execution_failed` | internal | error đã lọc, duration_ms, fingerprint |
| `attempt_error` | internal | lỗi của attempt |
| `retry_scheduled` | customer | retry và delay |
| `execution_cancelled` | internal | attempt + duration |
| `cancelled` | customer | Đã hủy |
| `credit_held` | internal | số credit giữ chỗ |
| `credit_settled` | internal | held, actual, adjustment |
| `credit_refunded` | customer | số credit hoàn |
| `orphan_reclaimed` / `resource_wait` | internal | recovery worker/tài nguyên |

App có mốc đặc thù gọi `ctx.event(...)` hoặc `ctx.stage(...)` trong `jobs.py`.
API best-effort: telemetry lỗi không làm hỏng job; counter
`event_write_failures` và process log vẫn báo để operator xử lý.

## File process log

Entry point `server/run.py`, `job_worker.py`, `worker_main.py` và agent-browser
worker gọi `platform_core.observability.configure_logging()`. File chỉ do LTT
tạo, tên `ltt-<component>.jsonl`. Mỗi dòng có UTC timestamp, level, logger,
message đã lọc, pid/thread và correlation fields nếu đang chạy job.

Biến môi trường:

| Biến | Mặc định | Ý nghĩa |
|---|---:|---|
| `LTT_FILE_LOGGING` | `1` | 0/false/off chỉ tắt file, không tắt JobEvent |
| `LTT_LOGS_DIR` | `logs/` runtime | nơi ghi file |
| `LTT_LOG_MAX_BYTES` | 10 MiB | ngưỡng xoay file |
| `LTT_LOG_BACKUP_COUNT` | 5 | số file xoay giữ lại |
| `LTT_LOG_RETENTION_DAYS` | 30 | chỉ xóa file `ltt-*.jsonl*` quá tuổi |

Cleanup này không xóa artifact/source/output. Job terminal vẫn cần dry-run +
backup + lệnh explicit theo `docs/DATA_RETENTION_POLICY.md`.

## Runbook debug

1. Lấy `correlation_id` từ job detail hoặc `/ops/jobs/{id}/events`.
2. Tìm `execution_failed` và fingerprint, rồi đối chiếu cùng thời điểm trong
   `logs/ltt-job-worker*.jsonl`.
3. Kiểm tra chuỗi `credit_held → credit_settled/refunded`; actual khác held là
   finding billing, không sửa ledger bằng tay.
4. Kiểm tra `retry_scheduled`, `orphan_reclaimed`, `resource_wait` trước khi kết
   luận provider/GPU lỗi.
5. Support export chỉ dùng cho operator; không chép params/result vào ticket.

## Ma trận app

Mọi job type khai trong manifest và chạy qua `platform_core.job_runner` đều nhận
automatic lifecycle events: `agent`, `anhnoibo`, `autosubvideo`, `chataistudio`,
`ltt_llm`, `prompt_ai_ommi`, `qualitylab`, `taoanh`,
`taoclipngan`, `taovideo`, `thumbnail`, `upscalevideo`. Không app nào được tự
ghi file log riêng hoặc ghi payload vào `JobEvent`.

Khi thêm app: manifest khai job_types/credit_for; handler dùng ctx.progress;
mốc provider/upload/render/output dùng ctx.stage/event với metadata đã lọc; test
lỗi có execution_failed + fingerprint và credit không mất; test retention không
xóa job active, ledger hay artifact.

