# 02 — Hợp đồng hành vi + bảo mật đang sống

Những gì công việc giao diện này **không được phép** làm lệch đi. Mỗi mục có
chỗ nó được thi hành trong mã và test giữ nó.

## A. `/developers` là bề mặt PHIÊN, `/api/v1` là bề mặt API

| | `/developers` | `/api/v1` |
|---|---|---|
| Xác thực | cookie phiên (`require_login`) | `Authorization: Bearer` |
| CSRF | **bắt buộc trên mọi POST** | không có, và không được thêm |
| Cookie | có | **bị từ chối** (`server/api/auth.py`) |

Lý do khác nhau nằm ngay trong docstring của
`server/routes/developer/__init__.py`: trình duyệt tự đính cookie vào request
liên trang, bearer token thì không.

**Giữ:** 7/7 POST gọi `verify_csrf_token(request, csrf_token)` **trước** mọi
việc khác; token phát bằng `issue_csrf_token` trong `_base_context`, nên mọi
trang render qua `_render` đều có `{{ csrf_token }}`.

**Cấm:** đổi form POST thành `fetch` mang bearer; thêm bất cứ tuyến portal nào
gọi được đường tính tiền bằng phiên.
Test: `test_197::test_writes_still_need_a_csrf_token`.

## B. Cổng cờ đặt TRƯỚC `require_login`

`Depends` chạy trước thân hàm. Một route "đã đóng" mà đặt kiểm cờ trong thân
hàm vẫn 303 về `/login` — tức nó vẫn tồn tại với người quan sát.
Không đụng tới thứ tự `Depends` của bất kỳ handler nào.

## C. Khoá API: HIỆN MỘT LẦN, và máy chủ không tái tạo được

- `devkeys.issue()` trả `(row, plaintext)`; hàng CSDL chỉ giữ
  `verifier_digest` (băm một chiều, có pepper).
- Plaintext đi vào template **đúng một lần**, qua biến `revealed_secret` của
  chính phản hồi POST đã tạo ra nó (`_keys_page(..., revealed=token)`).
- Tải lại trang là mất. Không có route nào đọc lại được.

**Cấm tuyệt đối trong công việc này:**
- lưu plaintext vào `localStorage`/`sessionStorage`/cookie;
- thêm route "xem lại secret";
- đưa plaintext vào `?query`, log, hay thuộc tính `data-*`;
- đổi thành "hiện bất cứ lúc nào".

Test: `test_179::test_plaintext_exists_only_in_the_issue_return_value`,
`::test_a_reloaded_key_cannot_reproduce_its_token`,
`::test_rotation_invalidates_the_previous_secret`.

⚠️ Cùng luật với **secret của webhook**: `webhook_console.rotate_secret` trả
plaintext, `_chung.SECRET_ONCE_KEY` mang nó qua đúng một lần render.

## D. Credential của nhà cung cấp không bao giờ tới đây

Khoá Gemini / provider của nền tảng nằm ở `platform_core.api_keys`. Không tệp
nào trong `server/routes/developer/` import nó, và không template `dev_*` nào
nhắc tới nó. Kể cả **sự tồn tại** của chúng cũng không phải việc của khách.
Test: `test_179::test_the_developer_key_domain_never_touches_provider_credentials`.

## E. Quyền sở hữu theo người thuê

Mọi truy vấn lọc theo `user.id` của phiên:
`projects.list_for(user_id=…)` · `devkeys.list_for_user(db, user.id)` ·
`webhook_console.owned_subscription(user_id=…)` ·
`ApiRequestLog.user_id == user.id` · `Job.user_id == user.id`.

Đường ghi dùng `get_owned(...)` rồi mới hành động — không có handler nào nhận
`id` từ URL và tin nó.

**Cấm:** thêm bất cứ chỗ nào lấy dữ liệu không có bộ lọc chủ sở hữu, kể cả để
"trang trông đầy hơn".
Test: `test_197::test_no_section_shows_another_account_anything` (đi qua **mọi**
section).

## F. Nội dung sinh từ hợp đồng, KHÔNG phải văn bản chép tay

Bốn chỗ, và tất cả phải giữ nguyên nguồn:

| Trang | Nguồn chân lý | Nếu tách ra thì hỏng gì |
|---|---|---|
| quickstart | `public_api.examples.*` dựng từ ToolSpec | ví dụ mô tả một lời gọi máy chủ sẽ từ chối |
| tools | `catalog.build_catalog(config)` — registry lúc chạy | danh mục nói ta bán thứ ta không bán |
| pricing | `pricing.simulate` — **cùng hàm** route báo giá gọi | số hiện ra khác số bị trừ |
| docs/openapi | `sub.openapi()` của chính app `/api/v1` đang chạy | client sinh ra từ một spec không ai phục vụ |

`test_302::test_vi_du_KHONG_tu_mau_thuan` và
`::test_dieu_kien_den_TU_HOP_DONG_chu_khong_tu_doc_van_xuoi` chốt điều này.

**⇒ Giao diện đẹp hơn không được đẻ ra nguồn chân lý thứ hai.** Mọi con số,
tên tham số, tên model trên trang phải tiếp tục đến từ context của handler.

## G. Mô phỏng giá KHÔNG tiêu tiền

`developer_pricing` gọi `pricing.simulate`, **không** đúc quote token và
**không** ghi sổ credit. Nên một mô phỏng không thể đem đi nộp ở `POST /jobs`.
Giao diện phải nói rõ điều này chứ không được làm mờ nó đi.

## H. Nhật ký request chỉ giữ BỘ XƯƠNG

`ApiRequestLog` có: `request_id`, `key_id`, `project_id`, `method`, `route`,
`status`, `code`, `latency_ms`, `tool`, `job_id`, `credit_delta`, `created_at`.

**Không có** cột nào chứa body của request hay response. Đó là chính sách, và
`dev_logs.html` đã nói ra với khách.

**Cấm:** đổi chính sách ghi log để "Request Inspector" có thêm thứ để hiện.
Được phép trình bày đẹp hơn **đúng 12 trường trên**.

## I. Webhook

Giữ nguyên: ngữ nghĩa ký (`webhooks.sign`), cửa sổ chống phát lại
(`webhooks.verify(tolerance=…)`), secret cũ còn hiệu lực trong thời gian ân hạn
(`previous_secret_until`), trần chống lạm dụng của `resend`
(`_recent_resends`).

Giao diện chỉ được đổi **cách nói**, không đổi **điều được nói**.

## J. Hai ràng buộc cứng của khu vực

1. **`test_197` chốt 32 route.** Thêm hay bớt một handler là gate đỏ. Công việc
   giao diện này **không thêm route nào**.
2. **`test_299` chốt bản dịch.** Mọi chuỗi hiển thị trong khu API phải có bản
   EN, không mục `fuzzy`, placeholder không rơi rụng. ⇒ Thêm chữ mới thì phải
   thêm bản dịch, không được để `_()` chưa dịch.

## K. Trợ năng đang được chốt

- **Đúng MỘT `aria-current="page"` trên cả trang.** Cơ chế hiện tại: có dải mục
  con thì dải đó mang `page`, thanh bên hạ xuống `aria-current="true"`; không
  có dải thì thanh bên lấy lại `page`.
  Test: `test_303::test_chi_co_dung_mot_aria_current_page`.
- `<nav class="app-side">` và `<nav class="dev-sub">` là **hình dạng markup mà
  test đọc bằng regex** (`test_303::_thanh_ben`). Đổi tên lớp hay đổi thẻ là
  làm vỡ test — nếu cần đổi thì phải sửa test kèm lý do, không sửa lén.
- Trạng thái không bao giờ chỉ mã hoá bằng màu: ô chỉ số có vấn đề mang thêm
  chữ; mục đang chọn dày viền chứ không chỉ đổi màu chữ.

## L. Ba việc buộc phải DỪNG và hỏi chủ sản phẩm

Nằm ngoài phạm vi công việc này:
1. mở một trang ra công khai (đụng `TRANG_CONG_KHAI` → đụng chốt 25/08);
2. đổi/thêm/bớt route, đổi ngữ nghĩa khoá, đổi chính sách giá;
3. đổi chính sách ghi log hay ngữ nghĩa ký webhook.
