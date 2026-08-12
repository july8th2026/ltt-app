# H33.R2 — Shared upload/artifact lifecycle evidence

## Kết luận

`SOURCE PASS`, `RELEASE CONDITIONAL`. Upscale, Clip ngắn, Tạo ảnh và Seedance
đã dùng cùng thứ tự tiền/dữ liệu: validate → staging → giữ credit → promote →
commit. Production cổng 8100 không bị thay đổi.

## Contract đã khóa

- Vé gắn owner + app, TTL một giờ; tối đa 20 vé/2 GiB active và 12 vé/phút.
- MIME allowlist không đủ: server kiểm exact byte size và magic signature.
- File chỉ chuyển khỏi `staging/` khi Job đã có hold credit.
- Storage move được bồi hoàn về staging nếu transaction DB không commit.
- Retry vé promoted trả đúng Job cũ, không tạo hold thứ hai.
- Job lỗi/hủy xóa input; sweeper bỏ qua Job active và dọn input terminal sau
  30 ngày. Worker chạy mỗi giờ; CLI operator mặc định dry-run.
- Audit event `input_promoted`/`input_cleaned` chỉ lưu upload id, byte và MIME;
  report CLI không in filename/storage key.

Seedance batch hai variant tạo hai staging copy độc lập. Vì vậy một variant lỗi
không thể xóa input mà variant còn lại đang dùng.

## Bằng chứng đã chạy

| Bằng chứng | Kết quả |
|---|---|
| Core + HTTP route lifecycle | 12 passed: promote, insufficient credit, retry, DB compensation, active-job safety, operator redaction; bốn app đều có route integration |
| Targeted Upscale/Clip trước browser | 65 passed |
| Targeted Image | 22 passed |
| Targeted Seedance | 55 passed |
| `python tools\gate.py --quick` | Lượt 1 bắt silent cleanup + i18n; sửa xong, lượt 2 **PASS 8/8** |
| `python tools\gate.py` | Lượt 1: 2.669 pass/1 fail, bắt MIME `text/html` đội lốt `.mp4`; sửa fail-closed. Lượt 2 **PASS 9/9**, pytest PASS 1.792,0 giây |
| Playwright fixture `127.0.0.1:8150` | MP4 thật 6.592.927 byte; `/upload-url` 200, `/batch` 200, credit 1000→992, source 206; console 0; mobile 390×844 `overflow=false` |

## Chưa được suy diễn thành PASS phát hành

- Migration mới chưa chạy trên staging PostgreSQL exact RC.
- Direct browser→R2 vẫn default-off theo Q48; cần cấu hình và browser CORS
  canary trên staging. Multipart ≤90 MB đã pass.
- Chưa deploy production. Các bước này thuộc R6, không phải thiếu source R2.

## Rollback

Revert commit H33.R2 trước khi migration được áp dụng. Sau khi migration đã áp
dụng, downgrade chỉ an toàn khi dry-run xác nhận không còn session active; file
staging/final phải được reconcile trước khi drop bảng.
