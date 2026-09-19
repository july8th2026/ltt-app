# 02 — Journey & Control Registry

| Control | Role/action | Success/error/recovery | Verdict |
|---|---|---|---|
| GET `/demo` | operator | form + CSRF | LIVE |
| “chạy trực tiếp” | operator, sync handler | kết quả/error, không Job | PARTIAL |
| “qua hàng đợi” | operator có DB user | submit credit → `/jobs/{id}` | LIVE |
| input text | required chỉ ở handler | rỗng ném lỗi/refund queue | LIVE |
| customer direct URL | middleware | 404 | LIVE |
| synthetic canary tự động | chưa có control/runtime riêng | UNKNOWN | MISSING |
| artifact download | handler không tạo artifact | không kiểm được storage leg | MISSING |

Queue states dùng trang Job chung; cancel/retry/history thuộc platform, không
được tính hai lần như năng lực riêng Demo.

