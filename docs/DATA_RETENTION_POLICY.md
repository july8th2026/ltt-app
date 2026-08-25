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
| Input upload đang staging | 1 giờ | `UploadSession`; worker sweep mỗi giờ, idempotent; operator CLI dry-run/apply | Owner theo vé; operator chỉ thấy báo cáo đã lọc |
| Source draft gắn AppProject | 30 ngày từ lần owner mở gần nhất | `UploadSession.attached`; owner/app/project-scoped; sweeper/reconcile dùng chung | Owner qua project; operator chỉ thấy báo cáo đã lọc |
| Input đã promote cho Job | 30 ngày sau promote | Chỉ promote sau hold; xóa ngay nếu Job lỗi/hủy; không xóa Job active | Owner qua route app; operator theo quyền |
| Output/project artifact | Policy storage riêng | Chưa tự xóa trong H26.11A/H33.R2 | Owner qua opaque route; operator theo quyền |
| Session | Theo session policy | Thu hồi/hết hạn độc lập | Owner/operator theo auth |
| Application log | Size + 30 ngày mặc định | `platform_core.observability`: JSONL rotating, redact boundary và prune file `ltt-*.jsonl*` theo `LTT_LOG_RETENTION_DAYS` | Operator |
| Quality Lab input nạp từ UI | Đến khi evaluation kết thúc | Storage key ephemeral; worker xóa trong `finally`, cleanup lỗi làm Job fail hữu hình | Chỉ operator trong lúc Job chạy |
| Quality Lab report/hash | 365 ngày theo Job | Lưu trong `Job.result`; không chứa raw media, transcript chuẩn, hostname/user/path | Operator |

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

Worker chỉ tự purge event đã quá hạn; process log LTT cũng tự prune file do LTT
tạo. Worker còn dọn riêng input upload theo Q85; không chạm output/project,
`Job` hay ledger. Xem trước/đối soát thủ công:

```powershell
python tools\upload_lifecycle.py --reconcile
python tools\upload_lifecycle.py --reconcile --apply
```

Support export tại `/ops/jobs/{job_id}/support-export` chỉ chứa metadata,
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

H26.11A chưa xóa output/project vì thời hạn artifact chưa được Q75 ấn định và
nhiều project lưu reference tới kết quả cũ. Đây không phải lời hứa lưu vĩnh
viễn. Trước khi bật artifact purge phải có inventory theo app, owner check,
legal/privacy decision, preview count/bytes, restore/rollback và canary riêng.

Input upload trả phí là contract hẹp Q85: staging một giờ, promoted input 30
ngày và xóa sớm khi Job lỗi/hủy. Source draft Q89 là contract riêng: attachment
gắn project được gia hạn khi owner mở, hết 30 ngày không dùng thì dọn và project
yêu cầu tải lại. Hai contract không cho phép xóa output hoặc asset đã lưu trong
project. Quality Lab là ngoại lệ hẹp đã khóa bởi Q83: file và transcript chuẩn do operator
nạp trực tiếp chỉ là input tạm và bị xóa sau evaluation. Artifact gốc được tham
chiếu bằng storage key không bị Quality Lab xóa; nó vẫn theo policy của app sở
hữu. Foundation chưa lưu frame/crop/audio evidence riêng và không dùng dữ liệu
production nếu chưa có consent.

## Dữ liệu Socialbot — app ĐÃ GỠ 2026-08-25 (Q108)

Mã đọc/ghi các tệp này không còn tồn tại: `data/audit_log.jsonl`,
`content_history.db`, retry state, session lock, và hai kho token
`tokens.enc` / `tiktok_tokens.enc`.

⚠️ **Hai kho token chưa bao giờ được tạo trên máy chủ này** — kiểm ngày
2026-08-25, cả hai đường dẫn đều không tồn tại, và CSDL có 0 job, 0
`app_access`, 0 `app_projects` mang slug `socialbot`. Không có token khách nào
để thu hồi.

⛔ **Các tệp còn nằm lại trong `data/` là dữ liệu vận hành, không phải mã.**
Xoá chúng là một hành động **không đảo được** trên máy đang chạy thật, tách
khỏi việc gỡ mã, và thuộc quyết định của chủ sản phẩm. Cho tới lúc đó chúng chỉ
nằm im — không tiến trình nào còn mở chúng.

## Changelog

- 2026-08-12: thêm source draft attachment/TTL/recovery Q89.
- 2026-08-12: thêm upload/input lifecycle Q85, sweeper và operator reconcile.
- 2026-08-10: thêm retention Q83 cho input ephemeral và report Quality Lab.
- 2026-08-09: thay tài liệu desktop cũ bằng policy platform Q75/Q76; thêm
  dry-run, terminal Job purge explicit, support export lọc và ranh giới ledger/
  artifact/Socialbot.
- 2026-08-25: app Socialbot bị gỡ khỏi kho mã (Q108); mục retention của nó
  chuyển thành ghi chú về dữ liệu còn sót trong `data/`.
- 2026-07-29: policy desktop/Socialbot ban đầu.
