# 02 — Journey & Control Registry

| Screen/control | Rule/role hiện tại | Action/state | Credit/log/recovery | Verdict |
|---|---|---|---|---|
| `/facebook` dán System User token | bất kỳ user đăng nhập | validate Graph rồi ghi token store global | 0 credit; log legacy | **BROKEN** |
| OAuth Facebook/TikTok | bất kỳ user đăng nhập | callback ghi token global | 0; state OAuth có kiểm | **BROKEN** |
| test/toggle/disconnect account | bất kỳ user đăng nhập | đọc/sửa/xóa account global | không undo | **BROKEN** |
| Sheet chọn account/tab/queue | bất kỳ user đăng nhập | đọc token và Google Sheet config global | queue riêng, không Job history chuẩn | **BROKEN** |
| add/remove/start/stop worker | bất kỳ user đăng nhập | đổi worker/controller toàn tiến trình | không tenant isolation | **BROKEN** |
| Manual Facebook/TikTok | bất kỳ user đăng nhập | publish bằng token global | confirm TikTok có; không credit | **BROKEN** |
| Monitor reset metric/log tail | bất kỳ user đăng nhập | đọc log và reset global | audit trail quyền chưa có | **BROKEN** |
| TT Audit refresh | bất kỳ user đăng nhập | chạy audit nền toàn cục | không owner/cancel | **BROKEN** |
| `/settings` | operator | cấu hình/credential | CSRF + operator | LIVE |
| Catalog public | anonymous bị ẩn | không thấy card | đúng Q10 | LIVE |

## State matrix

Happy path legacy có test; empty token render được. Unauthorized-customer state
**không tồn tại**. Failed provider có message/log nhưng ownership, undo, job
history chuẩn, credit và multi-tenant recovery không tồn tại. Mobile/keyboard
chưa audit sâu vì G2 đã chặn mọi phát hành customer.

