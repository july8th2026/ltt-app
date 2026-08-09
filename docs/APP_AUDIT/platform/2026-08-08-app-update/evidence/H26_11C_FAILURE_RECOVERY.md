# H26.11C — Failure recovery evidence

Ngày chạy: 2026-08-09. Mọi test dùng SQLite/storage tạm và provider giả lập;
không gọi production, không dùng credit hay dữ liệu khách thật.

## Kết quả

Lệnh tổng hợp:

```powershell
python -m pytest tests\test_67_hang_doi_job.py tests\test_68_credit.py `
  tests\test_69_web_jobs.py tests\test_80_r2_storage.py `
  tests\test_89_agent_runs.py tests\test_98_agent_canvas_run.py `
  tests\test_103_autosub_projects.py tests\test_149_presign_khong_nuot_loi.py `
  tests\test_150_gpu_lease.py tests\test_162_chat_customer_workflow_h26.py -q
```

Kết quả thật: **102 passed**, 1 warning deprecation từ Starlette/TestClient,
115,75 giây.

| Failure mode | Bằng chứng | Kết quả |
|---|---|---|
| Worker chết/restart | heartbeat cũ được reclaim; heartbeat sống không bị nhặt | PASS |
| Retry | attempt tăng một lần, backoff, hold không bị trừ lại | PASS |
| Cancel race | handler unwind sau cancel không đổi lại queued/error | PASS |
| Provider outage | terminal error refund đủ; error DB/log đã lọc token/email | PASS |
| Storage outage | presign degrade có signal; log lọc; local partial được dọn | PASS |
| WhisperX timeout | dừng process tree, không để pipe treo | PASS |
| GPU worker chết | lease orphan được reclaim, lease sống giữ nguyên | PASS |
| Agent/Chat/AutoSub credit | settle/refund/unused budget idempotent | PASS |
| Tenant boundary | owner/cross-tenant trên Job API | PASS |

Regression riêng được viết theo TDD: lần đầu có 3 fail (raw DB error, raw worker
log, raw storage traceback), sau fix chạy lại **35 passed**. Secret scan sau thay
đổi: **0 finding / PASS** trên 1.136 file, 175.783 dòng.

## Fix phát sinh từ drill

- `jobs.fail()` lọc lỗi trước khi ghi `Job.error` và internal event.
- worker chỉ log bản lỗi đã lọc.
- storage giữ `exc_info` để monitoring nhận biết exception nhưng thay message
  bằng bản đã lọc, không chuyển payload/traceback thô vào log.
- test khóa tính nguyên tử của LocalStorage khi stream hỏng giữa chừng.

## Ranh giới bằng chứng

Đây là failure drill development, không chứng minh provider/R2 production đang
khỏe. Production canary, backup/rollback rehearsal và quan sát SLO theo app nằm
ở H26.12. Runbook vận hành: `docs/H26_OPERATIONS_RUNBOOK.md`.
