# A1 — Current Truth

## Chuỗi vận hành thật

`browser → /taoclipngan/upload-url hoặc multipart /queue → Storage → Job + credit hold → worker taoclipngan → probe/Whisper/YOLO/planner/FFmpeg → MP4 + manifest → settle theo số clip thật → history/compare/package ZIP`.

Nguồn đã đọc: `manifest.py`, `routes.py`, `features.py`, `cost.py`, `jobs.py`, template; engine `cutclipshort`; JobContext/storage/credit contract và test liên quan.

## Năng lực đang LIVE

- Upload local hoặc direct-to-storage; tái dùng nguồn gần đây đã gắn với job.
- 4 aspect ratio, 3 tier, genre/language, số clip, khoảng thời lượng, brand preset và platform metadata.
- Chi phí theo phút nguồn × tier × 5, cộng 5 credit/output thật; worker đo duration thật và tăng hold khi cần.
- Pipeline phân tích, tuyển chọn, reframe, caption và render cục bộ; kết quả có score/rationale/transcript.
- History trạng thái queued/running/done/error; compare tối đa hai clip; video hỗ trợ HTTP Range.
- Chỉnh title/transcript trong package, sinh SRT/metadata/ZIP; owner check ở route kết quả/package.

## Sự thật giới hạn/rủi ro

- Ticket direct upload không CSRF và không khóa kích thước/nội dung; `/queue` chỉ kiểm prefix owner + object tồn tại, tin `duration_s` client cho hold ban đầu.
- Multipart fallback đọc toàn file trước khi kiểm trần 90 MB và tin MIME khai báo; chưa probe media tại admission.
- Worker không gọi `ctx.is_cancelled()` và không có deadline theo stage.
- Manifest chỉ ghi sau khi dựng xong toàn bộ; crash giữa các clip chạy lại phần tốn GPU.
- Clip render lỗi riêng bị bỏ qua; job vẫn DONE nếu còn ít nhất một clip, UI không trình bày rõ partial/refund.
- Transcript lưu timestamp tuyệt đối của video nguồn; `srt_text()` không rebase về đầu clip. ZIP đã kiểm chứng clip 1 bắt đầu `00:00:04,000`.
- Source/output không có xóa/TTL khép kín; job retention 365 ngày không đồng nghĩa artifact retention.
- History và source library chỉ hiển thị 8 mục; không pagination/search/project management.

## Dependency và rollback

Phụ thuộc: PostgreSQL Job/Credit, Storage, ffprobe/FFmpeg, Whisper, YOLO/GPU và `cutclipshort`. Đây là audit, rollback là revert commit tài liệu H27.6; không có thay đổi runtime.
