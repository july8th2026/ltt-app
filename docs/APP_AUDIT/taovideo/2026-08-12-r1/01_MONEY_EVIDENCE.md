# Seedance R1 — Money correctness evidence

## Kết luận

Source contract **PASS**; release vẫn **CONDITIONAL** đến khi chạy paid provider
canary trên exact release candidate. Production cổng 8100 không bị sửa/deploy.

## Contract đã khóa

- Quote ký, TTL 15 phút, khóa user/model/resolution/duration/aspect/input
  video/count; thay cấu hình hoặc sửa token trả 409 trước khi lưu file/tạo job.
- Quote intent là khóa một-lần của batch. Replay/double-click dùng lại job mọi
  status và không giữ credit lần hai.
- Khách trả `min(provider_actual, held)`; overage là variance nền tảng, có
  internal warning event. Worker công khai số thực thu, không giá provider.
- Settle và refund cùng job dùng PostgreSQL advisory transaction lock; đường
  thắng đầu tiên là kết sổ duy nhất.

## Test/evidence thật

| Kiểm tra | Kết quả |
|---|---|
| Targeted pytest | **48 pass** |
| `python tools\gate.py --quick` | lượt đầu FAIL i18n 1 chuỗi mới; bọc gettext, rerun **PASS 8/8** |
| Browser desktop 1586×992 | MP4 thật 6.592.927 byte; quote no-video 47, video 29; preview đúng video |
| Duplicate browser submit | hai POST cùng quote đều redirect thành công; chỉ 1 card/job mới |
| Ledger browser | fixture bắt đầu 500; job no-video 47 + video 29 → còn **424**, không giữ lần hai |
| Tamper | đổi 480p→720p nhưng dùng quote cũ → **409**, không tạo job |
| Mobile 390×844 | drawer inert/open đúng, không horizontal overflow |
| Console cuối | **0 error, 0 warning** |

Lỗi browser tìm thấy trong vòng này: HTMX từng gửi ba input file cùng tên ở
encoding URL thành `[object File]`, endpoint estimate trả 422. File field đã
tách theo modality; estimate chỉ nhận cờ giá, còn queue luôn kiểm lại MIME thật
và quote trước khi submit.

## Chưa được gọi là pass release

Paid provider canary sau sửa chưa chạy vì fixture cô lập không có provider key
và production 8100 vẫn là code cũ. R1.3 phải chạy ở staging exact commit, ghi
đủ hold/customer charge/provider actual/variance và xác minh balance không âm.
