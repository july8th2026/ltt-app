# 01 — Current truth

## Bản đồ vận hành

`manifest nav` → các route gốc `/facebook`, `/tiktok`, `/sheet/*`, `/manual/*`,
`/monitor`, `/audit` → `require_login` → service legacy → token store/worker
controller/process-wide logs. App không dùng bảng Job/Credit chung và không có
ToolSpec.

## Sự thật đã xác minh

- Manifest: `public=False`, `lifecycle=maintenance`, nhưng `surface` mặc định
  vẫn là `customer`.
- Q25: không có `AppAccess` = `enabled`; `public=False` chỉ ẩn anonymous/catalog,
  không tạo rào quyền route cho customer đã đăng nhập.
- Tất cả route nhạy cảm chính dùng `require_login`, không dùng
  `require_operator`; POST có CSRF nhưng CSRF không thay thế authorization.
- Facebook và TikTok dùng singleton token store theo file toàn tiến trình,
  không có `user_id`/tenant ownership.
- Sheet runner và monitor cũng là state toàn tiến trình; customer thường có thể
  thêm/xóa worker, start/stop và reset metric.
- Browser E3: customer test mở trực tiếp `/facebook`, thấy form dán System User
  token và toàn bộ 8 mục điều hướng operator.
- `/settings` đã dùng `require_operator`, cho thấy ranh giới đúng đã tồn tại
  nhưng chưa áp dụng đồng nhất cho Socialbot.

## Test thật

- 411 passed, 1 skipped: legacy Facebook/TikTok/compliance/runner/monitor/web.
- Browser `/facebook`: 200, console 0 error/warning, không failed request.
- Không có test âm khẳng định customer thường bị chặn khỏi Socialbot.

## UNKNOWN

Provider permission thực tế, publish success rate, token rotation/restore trên
production, concurrency đa process, P75 latency và user task completion.

