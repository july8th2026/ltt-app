# P6 · Task 3 — Allowlist **4 piece thực dùng** (⛔ không 730)

**Kết quả: ĐẠT.** `connector_runner/allowlist.json` là nguồn duy nhất;
`src/piece_nap.js` là nơi **duy nhất** biết cách lấy `piece` ra khỏi một
module Activepieces, và nó **từ chối** mọi tên ngoài allowlist — kể cả khi gói
đó có mặt trong `node_modules`.

| Piece | Bản ghim | Auth thật |
|---|---|---|
| `@activepieces/piece-slack` | 0.20.0 | OAuth2 · CustomAuth(`botToken`,`userToken`) |
| `@activepieces/piece-github` | 0.9.0 | OAuth2 · CustomAuth(app) · SecretText |
| `@activepieces/piece-telegram-bot` | 0.7.0 | SecretText |
| `@activepieces/piece-google-sheets` | 0.17.0 | OAuth2 · CustomAuth(service account) |

`npm install --ignore-scripts` ⇒ **38 gói** tổng (nhỏ hơn dự tính nhiều — cả
bốn piece dùng chung `pieces-framework` + `shared`).

## Hai cửa chặn của chuỗi cung ứng — đo được

- **Ngoài allowlist:** `piece_ngoai_allowlist: @activepieces/piece-khong-co`
- **Lệch bản:** `phien_ban_lech: yeu cau 0.0.1-sai, cai 0.20.0`

Cả hai ném **lúc nạp**, trước khi một dòng mã piece nào chạy.

## Miền cho phép — fail **closed**

Mỗi piece khai danh sách miền (`allowlist.json → mien`), áp ở
`proxy_egress.py` tức **ngoài tiến trình piece**. Piece **không có** mục miền
⇒ danh sách **rỗng** ⇒ chặn hết. ⛔ Không có mặc định "cho đi tất".
So khớp theo **nhãn**: `slack.com.ke-tan-cong.vn` ⛔ không khớp `slack.com`
(phép kiểm có tiêm lỗi để chứng minh nó phân biệt được).

## 🔴 Nợ đã khai: `npm audit`

8 lỗ hổng trong cây phụ thuộc, trong đó **1 critical**:
`expr-eval` — *prototype pollution* (qua `@activepieces/shared`), và
`deepmerge-ts` (stack exhaustion, high). Runner của ta **không** gọi
`expr-eval` (nó gọi thẳng `action.run`), nhưng mã piece thì có thể. ⛔ Không tự
vá `node_modules`. Việc đúng: theo dõi bản lên của `@activepieces/shared`, và
cân nhắc ghi issue ngược lên kho họ.
