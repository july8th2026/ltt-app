# Data Retention Policy — LTT Studios App

**Hiệu lực:** 2026-08-09
**Nguồn quyết định:** Q75–Q76 trong `QUYET_DINH_NEN_TANG.md`

Tài liệu này mô tả platform web hiện hành. Các file JSONL/SQLite của Socialbot
đóng băng được ghi riêng ở cuối; chúng không phải nguồn lịch sử Job của app web.

## Chính sách đang có hiệu lực

| Lớp dữ liệu | Thời hạn | Cơ chế | Người được đọc |
|---|---:|---|---|
| Job metadata + customer timeline | 365 ngày | `JobEvent` purge tự động; Job terminal purge explicit theo batch | Chủ Job; operator |
| Internal debug event | 30 ngày | Worker gọi purge mỗi 6 giờ | Operator/support |
| Credit ledger | Không purge theo Job | `CreditEntry` append-only, không FK cascade theo Job | Chủ tài khoản ở UI đã lọc; operator |
| Artifact/source/output | Policy storage riêng | Chưa tự xóa trong H26.11A | Owner qua opaque route; operator theo quyền |
| Session | Theo session policy | Thu hồi/hết hạn độc lập | Owner/operator theo auth |
| Application log | Size-based | Rotating handler; giới hạn theo cấu hình service | Operator |

`Job` chỉ được purge khi ở trạng thái terminal `done/error/cancelled` và quá 365
ngày. Job `queued/running` quá tuổi **không bị xóa** mà được báo trong dry-run để
đi qua recovery. Xóa Job không xóa ledger tiền hoặc artifact; hai lớp đó có
chính sách độc lập.

## Quy trình purge an toàn

1. Xem dry-run operator: `GET /ops/jobs-retention` hoặc:

   ```powershell
   python tools\job_retention.py
   ```

2. Nếu `active_jobs_older_than_policy > 0`, xử lý recovery trước; không purge để
   che job kẹt.
3. Tạo và kiểm backup theo `deploy/windows/backup.ps1`.
4. Chạy một batch có xác nhận tường minh:

   ```powershell
   python tools\job_retention.py --apply --confirm PURGE
   ```

5. Chạy lại dry-run, kiểm `/ops/jobs-metrics`, ledger và health. Lặp batch nếu
   cần. Không bật lịch xóa Job tự động trước H26.12 canary.

Worker chỉ tự purge event đã quá hạn; việc này không chạm `Job`, artifact hay
ledger. Support export tại `/ops/jobs/{job_id}/support-export` chỉ chứa metadata,
event đã lọc và tổng ledger theo loại; không chứa params/result/error/note/PII.

## Privacy và redaction

- Customer API không trả `params`, `result`, lỗi thô hoặc event internal.
- Event internal cũng được lọc trước khi ghi; support export lọc lại lần hai để
  bảo vệ dữ liệu legacy.
- `Job.error`, worker log và lỗi storage/provider cũng được lọc token/email
  trước khi ghi; traceback/payload thô không được biến application log thành
  kho bí mật thứ hai.
- Raw technical endpoint/export bắt buộc operator. Customer chỉ thấy timeline
  bằng ngôn ngữ sản phẩm.
- Secret scan và source log policy vẫn là gate trước release.

## Artifact — gap đã ghi rõ

H26.11A chưa xóa source/output vì thời hạn artifact chưa được Q75 ấn định và
nhiều project lưu reference tới kết quả cũ. Đây không phải lời hứa lưu vĩnh
viễn. Trước khi bật artifact purge phải có inventory theo app, owner check,
legal/privacy decision, preview count/bytes, restore/rollback và canary riêng.

## Dữ liệu Socialbot đóng băng

`data/audit_log.jsonl`, `content_history.db`, retry state, session lock và OAuth
token là runtime lịch sử Q10; vẫn theo rotation/maintenance cũ. H26 không refactor
hay đổi retention nghiệp vụ Socialbot. OAuth token chỉ mất khi disconnect/revoke;
không được đưa vào support export hoặc log mới.

## Changelog

- 2026-08-09: thay tài liệu desktop cũ bằng policy platform Q75/Q76; thêm
  dry-run, terminal Job purge explicit, support export lọc và ranh giới ledger/
  artifact/Socialbot.
- 2026-07-29: policy desktop/Socialbot ban đầu.
