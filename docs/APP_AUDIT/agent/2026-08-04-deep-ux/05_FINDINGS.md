# Findings

## Đã đóng trong H20

1. P1 — Edge tồn tại trong server nhưng renderer không vẽ vì node/handle chưa
   initialized. Đã thêm measured geometry + typed handle registry; E3 reload 1/1.
2. P1 — Chạy node bị full-workflow validation chặn bởi node không liên quan.
   Đã lọc issue theo target và transitive prerequisite; E3 tạo awaiting approval.
3. P2 — Chọn reference mới để lại nhiều edge trên cùng input. Đã chuyển thành
   replace semantics; E3 từ 2 edge về 1 edge, state và renderer đồng bộ.
4. P2 — Schema kỹ thuật quyết định UX. Đã có node presentation layer và
   contextual composer; Inspector giữ advanced fields.
5. P2 — Canvas thiếu right-click/quick-create. Đã triển khai và regression test.
6. P2 — Node chưa đổi tên trực tiếp và Text chỉ là vỏ. H20.8 lưu display label
   ngoài executable data, thêm inline editor và regression/browser evidence.
7. P2 — Người dùng không thấy hoặc tháo được từng input đã nối. H20.8 thêm chip
   theo edge thật; remove đồng bộ edge + param và hỗ trợ undo.
8. P2 — Thiếu direct shortcut và output actions thường dùng. H20.8 thêm shortcut
   không chiếm focus nhập liệu, drag/drop input, open/copy/download/duplicate.
9. P1 — Image node chỉ có vỏ generate, không nhận ảnh tham chiếu nên không thể
   tái tạo workflow Lookbook thật. H20.9 thêm cổng typed `image`/`image[]`, owner
   scope, dedupe, giới hạn 8 MB/ảnh và 20 MB/node; worker gửi inlineData đã verify.
10. P1 — Collection input trước đây chỉ giữ một scalar edge. H20.9 hỗ trợ append
    nhiều scalar vào collection, disconnect/remap không để lại `$node.output`
    mồ côi; browser xác minh 3 ảnh vào một node Image.
11. P1 — Text/Video/Image chưa tạo thành chuỗi đa phương thức hai chiều. H20.9
    nối được Image→Text phân tích, Text→Image/Video tạo nội dung, Video→Text phân
    tích; typed validator chặn sai kiểu và ownership vẫn ở server.
12. P1 — Release builder vô tình duyệt `tmp/` và `test-results/`, có nguy cơ đưa
    profile Chromium/runtime fixture vào archive. Đã loại ở builder, source secret
    scanner và regression; không xóa profile đang đăng nhập.

## Còn mở sau code gate

1. P2 — Chưa có E4 user task/telemetry cho time-to-first-workflow và tỷ lệ lỗi.
   Acceptance: beta cohort hoàn thành ba JTBD, có task success/time/error metrics.
2. P3 — Bundle H20.9 đã deploy, health/manifest/login console-network sạch;
   authenticated Canvas còn manual handoff vì browser không có production
   session. Acceptance: chủ sản phẩm đăng nhập tab đã mở, reload Canvas và kiểm
   console/network; agent không tự tạo tài khoản/dữ liệu production.
3. P3 — Mobile chỉ xem. Đây là omission minh bạch; xem xét authoring sau khi có
   dữ liệu nhu cầu, không đưa vào table stake hiện tại.
4. P3 — Cảnh báo Starlette/httpx deprecation trong test harness. Không ảnh hưởng
   runtime; lên ticket dependency maintenance, không nâng nóng trong H20.
5. P1 — Chưa có Asset Catalog/history/system resources và URL ingest an toàn.
   Không dựng picker giả; tách AG-AST-01/AG-URL-02 với owner index, retention,
   SSRF, MIME, provenance và signed delivery gate.
6. P2 — Batch multi-upload/reorder và output replace/variation cần lineage,
   cleanup và partial-failure contract; theo AG-BAT-03/AG-OUT-04.
