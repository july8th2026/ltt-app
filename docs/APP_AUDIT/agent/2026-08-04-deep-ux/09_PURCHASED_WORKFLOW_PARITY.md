# Vòng 3 — Purchased workflow parity

Ngày 2026-08-04. Benchmark: workflow Lookbook đã mua trong phiên PlenX được
người dùng cho phép. Chỉ đọc/export cấu trúc và thao tác control; không chạy node
trả phí, không tải output và không lưu token/profile vào source hay release.

## Bằng chứng PlenX E3

- 13 node, 13 connection, 1 frame: 5 Image, 2 Text, 6 Video.
- Ba Image asset đi vào một Image generate để phối mẫu/trang phục/bối cảnh.
- Output Image đi tiếp vào Image generate cận cảnh, Text phân tích cảnh và nhiều
  Video generate; Text output cũng trở thành prompt cho Video.
- Node config tách khỏi graph; connection PlenX không typed port. LTT giữ typed
  port vì an toàn hơn, không sao chép kết nối mơ hồ.

## Delta đã triển khai

1. `image.generate` và `image.batch_generate` nhận `image_key`/`image_keys`.
2. Worker chỉ đọc key có segment owner đúng, verify JPEG/PNG/WebP, giới hạn 8
   ảnh, 8 MB/ảnh, tổng 20 MB và gửi inlineData vào Gemini.
3. Collection input nhận nhiều scalar edge theo thứ tự; xóa/copy/remap edge cập
   nhật cả graph và param reference.
4. Text nhận ảnh/video/text để phân tích và có thể cấp text cho Image/Video.
5. Video nhận image/image[]/video/audio; Social Video và transform dùng executor
   có quote thật, không quảng bá capability giả.

## Acceptance LTT E3

- Chromium 1920×1080, user fixture owner-scoped.
- Upload ba ảnh thật rồi dựng: 3 Asset Image → Image generate → Image generate
  → Text generate → 2 Video generate, tổng 8 node/9 edge.
- Workflow validate thành công; server báo tối đa 132 credit và chặn bởi budget
  fixture 50. Không bấm approve/generate, actual credit 0.
- Console error 0. API palette/workflow/preferences/assets/quote/save/validate
  đều 200/201; không có failed request.
- Ảnh bằng chứng local chỉ nằm trong `tmp/agent-lookbook-parity.png`, không thuộc
  source/release.

## Kết luận

Khoảng trống ngăn workflow đa ảnh thực tế đã đóng. LTT đạt behavioral parity ở
chuỗi Image→Image→Text→Video và giữ lợi thế typed validation, owner scope, quote
và approval. Chưa tuyên bố output parity vì audit chủ động không tiêu provider
credit; cần beta task E4 sau release.
