# Developer API key — thiết kế và vận hành (Prompt 03)

Credential **của khách**, tách tuyệt đối khỏi bảng `api_keys` (credential
provider của nền tảng). Quyết định nền tảng: **Q92**.

## 1. Vì sao không dùng lại `api_keys`

| | `api_keys` (đã có) | `developer_api_keys` (mới) |
|---|---|---|
| Ai sở hữu | **LTT** — khoá để gọi Gemini/BytePlus/… | **Khách hàng** |
| Có cần lấy lại giá trị gốc? | **Có** — worker phải gọi API thật | **Không bao giờ** |
| Cách lưu | mã hoá Fernet, `lay_credential()` giải mã được | **digest một chiều**, không có đường lấy lại |
| Rò CSDL nghĩa là gì | lộ khoá provider | không lộ gì dùng được |

Trộn hai thứ này là biến một lỗ đọc CSDL thành mất cả hai. Có test chặn:
`platform_core/public_api/keys.py` không được nhắc `lay_credential`, `secretbox`
hay import `platform_core.api_keys`.

## 2. Hình dạng token

```
ltt_sk_<key_id 32 hex>_<secret 43 ký tự base64url>
        └── công khai ──┘ └── 256 bit CSPRNG, KHÔNG lưu ──┘
```

- `ltt_sk` để một khoá lọt vào log/paste/repo công khai là **grep được** và thu hồi được.
- `key_id` công khai + `UNIQUE` + index → tra khoá là một lần trúng index, không
  phải quét bảng so digest.
- Lưu `verifier_digest = HMAC-SHA256(pepper, secret)`.

**Cạm bẫy đã dính và đã có test chặn:** secret là base64url nên **chứa dấu `_`**.
Parser đầu tiên dùng `split("_")` → khoảng một phần ba token hợp lệ bị coi là
sai, lúc xanh lúc đỏ. Nay parse bằng `split("_", 3)` + kiểm bảng chữ cái, và có
regression test ép secret chứa `_`.

## 3. Vì sao HMAC chứ không bcrypt/argon2

Digest này chạy **mỗi request API**. Một KDF định giá để chống crack offline mật
khẩu người dùng sẽ biến bất kỳ caller ẩn danh nào thành bộ khuếch đại CPU — DoS
là rủi ro lớn hơn thứ nó định chống. Và đầu vào ở đây là 256 bit ngẫu nhiên,
không có từ điển để tấn công.

Số đo thật (`python tools\bench_public_api_key.py --db --sqlite`):

| Phép đo | p50 | p95 | p99 | ~/giây |
|---|---|---|---|---|
| HMAC-SHA256 đơn thuần | 2,9 µs | 3,1 µs | 3,7 µs | ~345.000 |
| `verify()` đủ đường (kèm 1 truy vấn) | 258,6 µs | 531,9 µs | 1.101,7 µs | ~3.866 |

Có test chốt `verify()` < 10 ms/lần — nó sẽ đỏ ngay nếu ai đó thay bằng KDF đắt.

## 4. Pepper và cách xoay

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `LTT_API_KEY_PEPPER` | **có** (≥32 ký tự) | Pepper hiện hành. Thiếu → **không cấp và không xác minh được khoá nào** (fail-closed, không có giá trị mặc định). |
| `LTT_API_KEY_PEPPER_VERSION` | không (mặc định `1`) | Phiên bản ghi vào khoá mới. |
| `LTT_API_KEY_PEPPER_V<n>` | không | Pepper **đã nghỉ hưu**, giữ để khoá cũ còn xác minh được trong lúc xoay. |

Quy trình xoay: thêm `LTT_API_KEY_PEPPER_V1=<pepper cũ>`, đặt
`LTT_API_KEY_PEPPER=<pepper mới>` + `LTT_API_KEY_PEPPER_VERSION=2`, khởi động
lại web/worker. Khoá cũ vẫn chạy; `rotate()` từng khoá để chuyển dần sang V2;
xoá `_V1` khi không còn khoá nào ở version 1.

Mất pepper cũ mà chưa xoay xong = các khoá đó **ngừng hoạt động** (fail-closed),
không phải bỏ qua kiểm tra.

## 5. Vòng đời

| Thao tác | Hàm | Ghi chú |
|---|---|---|
| Cấp | `issue()` | Trả `(row, plaintext)`. **Plaintext chỉ tồn tại ở đây** — không có đường lấy lại. Tối đa 25 khoá còn sống/user, `expires_at` ≤ 1 năm. |
| Xác minh | `verify()` | Trả `None` cho mọi thất bại: sai định dạng, không có key_id, sai secret, đã thu hồi, đã tắt, hết hạn. |
| Liệt kê | `list_for_user()` | Chỉ metadata. |
| Tra một khoá | `get_owned(user_id=…, key_id=…)` | Owner nằm trong `WHERE`, không phải trong một câu `if` sau khi đã lấy dòng. |
| Tạm tắt | `set_enabled()` | Bật lại được. |
| Thu hồi | `revoke()` | **Không đảo ngược được**; đã thu hồi thì không bật lại, không rotate. |
| Đổi secret | `rotate()` | Cùng một dòng (giữ tên/scope/lịch sử), token cũ chết ngay. Muốn không gián đoạn thì cấp khoá thứ hai → chuyển client → thu hồi khoá cũ. |

Trạng thái (`status()`) suy ra từ cột, không phải một cột trạng thái riêng dễ
lệch: `revoked` → `disabled` → `expired` → `active`.

## 6. Chống enumeration

Mọi nhánh thất bại đều: (a) vẫn tính một HMAC, kể cả khi token sai định dạng
hoặc `key_id` không tồn tại; (b) so bằng `hmac.compare_digest`; (c) trả cùng một
`None`. Tầng HTTP (Prompt 04) **không được** phân biệt "không có khoá" với "sai
secret" trong phản hồi.

## 7. `last_used_at` không gây write amplification

Một client poll job mỗi 2 giây sẽ biến mọi endpoint chỉ-đọc thành một lệnh ghi
nếu cập nhật `last_used_at` mỗi request. `touch_last_used()` chỉ ghi khi đã qua
**bucket 5 phút**, và trả `True/False` để nơi gọi biết nó có ghi hay không.

## 8. Scope

Từ vựng ở `platform_core/public_api/scopes.py`, dạng `<resource>:<action>`:
`tools:read`, `jobs:read`, `jobs:write`, `uploads:write`, `artifacts:read`,
`usage:read`, `webhooks:write`. Đọc **không** được suy ra từ ghi.

Mặc định khi không khai: `tools:read` + `jobs:read` — đủ để khám phá catalog và
xem việc của mình, **không đủ để tiêu credit**.

`allowed_tools` rỗng = theo catalog công khai; khác rỗng = giao của hai tập.
Catalog vốn đã là allowlist tường minh nên rỗng **không** phải fail-open.

## 9. Migration

`alembic/versions/20260813_1000_developer_api_keys.py` (`a7b8c9d0e1f2`), thêm
bảng `developer_api_keys`, FK `users.id` `ON DELETE RESTRICT`, `UNIQUE(key_id)`,
ba index. `downgrade()` xoá sạch. Đã kiểm `upgrade → downgrade base → upgrade`
trên SQLite qua `tests/test_63_lop_csdl.py`.

Test bằng PostgreSQL thật (UNIQUE dưới tải, FK RESTRICT) nằm trong
`tests/test_179_developer_api_key.py`, **tự bỏ qua** nếu không đặt
`LTT_TEST_DATABASE_URL`.

## 10. Cố ý KHÔNG có

- ~~Không có cột `environment`/`sandbox`~~ — **EXT-12 đã thêm cột `mode`**
  (`live`/`test`), đúng vào lúc có ngữ nghĩa thật đứng sau nó: không giữ chỗ
  credit, không gọi provider, cách ly cứng khỏi job live. Trước đó một cột như
  vậy chỉ là lời hứa suông trong lược đồ.
- Không có route HTTP nào ở prompt này. Tạo/thu hồi khoá sẽ nằm ở portal có
  phiên đăng nhập (Prompt 15); một khoá tự cấp khoá khác là leo thang quyền
  không cần thiết cho V1.
