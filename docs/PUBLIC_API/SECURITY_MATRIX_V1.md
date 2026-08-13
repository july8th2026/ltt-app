# Public API — ma trận bảo mật V1 (Prompt 04)

Bề mặt: `/api/v1`. Nguồn: `platform_core/public_api/principal.py`,
`server/api/auth.py`, test `tests/test_180_public_api_auth.py`.

## 1. Hợp đồng mã trạng thái — quy tắc chống dò

Đây là phần dễ làm sai nhất, nên viết thành luật một lần cho mọi route sau:

| Tình huống | Trả về | Vì sao |
|---|---|---|
| Không có `Authorization`, sai định dạng, khoá không tồn tại, sai secret, đã thu hồi/hết hạn/bị tắt | **401**, **một thông điệp duy nhất** | Phân biệt "không có khoá này" với "sai secret" là tặng người tấn công một máy dò key_id. |
| Khoá hợp lệ nhưng thiếu scope | **403**, có nêu tên scope | Đây là thông tin về **khoá của chính người gọi**, không phải về dữ liệu nền tảng. Giấu nó chỉ khiến một tích hợp phải mở ticket mới xong. |
| Khoá hợp lệ, đủ scope, tool **không** được public | **404** | API không được trở thành danh bạ năng lực nội bộ. Tool internal/retired phải trông như không tồn tại. |
| Tool public nhưng `allowed_tools` của khoá không có | **403** | Tool có tồn tại công khai; hạn chế là ở khoá. |
| Object của người khác **hoặc** object không tồn tại | **404 giống hệt nhau, từng byte** | Nếu object của người khác trả 403 thì chỉ cần duyệt id, gom các id trả 403 là đã vẽ được bản đồ job của khách khác mà không cần đọc nội dung. |
| Object không có chủ | **404** | Không có chủ thì không ai đọc được. |
| API đang read-only | **503** `read_only` | Công tắc khẩn cấp, không phải lỗi của người gọi. |

## 2. Nguồn của danh tính

`user_id` **luôn** lấy từ credential đã xác minh. Không route nào được nhận
`user_id`/`account_id` từ path, query hay body. Test
`test_ownership_comes_from_the_credential_not_from_the_request` chốt điều này.

## 3. Ma trận theo lớp lỗ hổng OWASP API

| Lớp | Cơ chế | Test |
|---|---|---|
| **BOLA** (object authorization) | `ensure_owner()` — chủ sở hữu nằm trong `WHERE` khi truy vấn, và là lưới chắn cuối khi không tiện; sai chủ → 404 | `test_another_customers_object_is_indistinguishable_from_a_missing_one`, `test_two_accounts_never_see_each_others_keys` |
| **Broken authentication** | Bearer duy nhất, digest HMAC + `compare_digest`, mọi thất bại một thông điệp | `test_every_bad_credential_looks_identical` |
| **Key enumeration** | Không phân biệt nhánh thất bại; vẫn tính HMAC cho token sai định dạng/không tồn tại | `test_verification_hashes_even_for_unknown_keys` (Prompt 03) |
| **BFLA** (function authorization) | `require_scope()` là dependency ở biên, chạy **trước** thân route | `test_scope_dependency_refuses_before_the_route_body_runs` |
| **Charge bypass** | Scope là cổng tính tiền; thiếu scope → không có bút toán credit nào | `test_no_scope_means_no_credit_mutation` |
| **Mass assignment** | Principal là dataclass frozen, dựng từ khoá; request không bơm được trường vào | (Prompt 06 mở rộng khi có body thật) |
| **Resource consumption** | Trần body + read-only switch (Prompt 02); rate/quota theo principal ở Prompt 08 | `test_oversized_declared_body_is_refused_before_it_is_read` |
| **Security misconfiguration** | Pepper thiếu → **fail-closed** (401), có log lý do `pepper_not_configured` | `test_a_missing_old_pepper_fails_closed_rather_than_open` |
| **Credential leakage** | Không log Authorization/token thô; audit chỉ ghi `key_id` công khai + mã lý do | `test_raw_bearer_token_never_reaches_the_logs` |
| **Confused deputy / CSRF** | Cookie/`request.session` không bao giờ là danh tính API | `test_a_browser_session_is_not_an_api_credential` |

## 4. Vì sao KHÔNG có CSRF ở `/api/v1`

CSRF token bảo vệ một **phiên trình duyệt** mà trình duyệt tự đính kèm. Bearer
token chỉ được đính bởi client đã có nó, và bề mặt này **từ chối cookie**, nên
lớp tấn công mà CSRF ngăn không tồn tại ở đây. Developer portal (Prompt 15) là
UI có phiên → vẫn giữ CSRF như hiện nay.

## 5. Scope baseline

`tools:read`, `jobs:create`, `jobs:read`, `jobs:cancel`, `uploads:write`,
`artifacts:read`, `credits:read`, `usage:read`, `webhooks:manage`.

- Đọc **không** suy ra từ ghi và ngược lại (`jobs:read` không cho `jobs:cancel`).
- Mặc định khi cấp khoá: `tools:read` + `jobs:read` — **không tiêu được credit**.
- `SPENDING_SCOPES` liệt kê tường minh scope có thể tiêu tiền (`jobs:create`),
  để câu hỏi "khoá này tiêu được gì của tôi" là một lần tra, không phải đọc hết
  route.

## 6. Mô hình quyền tool: `allowed_tools`, KHÔNG phải `tool:<name>` scope

Chọn **một** mô hình để không có hai câu trả lời nửa vời cho cùng một câu hỏi:

- **scope** nói *loại hành động* (`jobs:create`);
- **`allowed_tools`** trên khoá nói *nhắm vào tool nào*;
- **catalog** (Prompt 05) nói *tool nào được public*.

Nhét tên tool vào scope sẽ sinh một chuỗi scope cho mỗi tool, buộc cấp lại khoá
mỗi khi catalog đổi. Test `test_tool_policy_uses_allowed_tools_not_scope_strings`
chặn việc lén thêm scope dạng `tool:*`.

`allowed_tools` rỗng = theo catalog; catalog vốn là allowlist tường minh nên
rỗng **không** phải fail-open.

## 7. Audit khi từ chối

Một dòng `logging` mức WARNING cho mỗi request bị từ chối, gồm: mã lý do
(`no_bearer_header`, `malformed_token`, `unknown_or_wrong_secret`,
`revoked_expired_or_disabled`, `pepper_not_configured`), `key_id` **công khai**
(nếu token đúng định dạng), IP tin cậy, path, `request_id`.

Không bao giờ ghi: header `Authorization`, token thô, phần secret, digest.

## 8. Còn thiếu (có nơi xử lý)

| Việc | Prompt |
|---|---|
| Rate-limit theo principal, quota, concurrency, 429 đúng hợp đồng | 08 |
| Idempotency + kiểm mass-assignment trên body thật | 06 |
| SSRF (webhook target, tool nhận URL) | 09 |
| Ownership cho artifact/upload/webhook/usage khi các resource đó ra đời | 06–10 |
