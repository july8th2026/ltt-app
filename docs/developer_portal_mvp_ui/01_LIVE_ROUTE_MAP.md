# 01 — Bản đồ route THẬT của `/developers`

Đọc từ mã sống ngày **2026-08-26**, nhánh `public-api-v2`.
Nguồn: `server/routes/developer/` (package 7 tệp, chẻ ra từ `developer.py` ngày
26/08), `server/templates/dev_*.html`, `server/templates/developers_base.html`.

## 0. Tóm tắt trong bốn dòng

| | |
|---|---|
| Số route | **32** (25 GET · 7 POST) — `test_197` chốt đúng con số này |
| Xác thực | **32/32** đi qua `require_account` → chưa đăng nhập là 303 về `/login` |
| CSRF | **7/7** POST gọi `verify_csrf_token` trước khi làm bất cứ việc gì |
| Công khai | **0** — `TRANG_CONG_KHAI = frozenset()`, và đó là một CHỐT (xem §5) |

## 1. Bảng đầy đủ

`P` = trang cha có mặt trên thanh bên · `C` = mục con (route sống, không nằm
trên thanh bên) · `—` = không phải trang.

| Route | M | Template | Auth | CSRF | Cấp | Nguồn dữ liệu | Tác dụng phụ | Test |
|---|---|---|---|---|---|---|---|---|
| `/developers` | GET | `dev_overview.html` | `require_account` | — | **P** `overview` | `_overview_counts` + `_usage_context` (CSDL) | không | 197, 301, 303 |
| `/developers/quickstart` | GET | `dev_quickstart.html` | `require_account` | — | **C** → `cli` | `build_catalog` + `public_api.examples` | không | 199, 303 |
| `/developers/cli` | GET | `dev_cli.html` | `require_account` | — | **P** `cli` | `examples.*` + `tai_lieu_api.bo_cai_moi_nhat()` | không | 275, 303 |
| `/developers/tools` | GET | `dev_tools.html` | `require_account` | — | **P** `tools` | `build_catalog(config)` (registry) | không | 302 |
| `/developers/tools/{tool_name}` | GET | `dev_tool_detail.html` | `require_account` | — | **C** → `tools` | `build_catalog` + `_tham_so` | không | 302 |
| `/developers/playground` | GET | `dev_playground.html` | `require_account` | — | **C** → `tools` | catalog + `devkeys.list_for_user` (chỉ nửa công khai) | không | 200, 301 |
| `/developers/pricing` | GET | `dev_pricing.html` | `require_account` | — | **P** `pricing` | `pricing.simulate` (cùng hàm route báo giá dùng) | **không** đúc quote token, **không** trừ credit | 207 |
| `/developers/docs` | GET | `dev_docs.html` | `require_account` | — | **P** `docs` | `request.base_url` | không | 197 |
| `/developers/openapi/download` | GET | — (`Response`) | `require_account` | — | — | `sub.openapi()` của app `/api/v1` đang chạy | không | 191, 210 |
| `/developers/projects` | GET | `dev_projects.html` | `require_account` | — | **C** → `keys` | `projects.list_for` | không | 197, 303 |
| `/developers/projects` | POST | `dev_projects.html` | `require_account` | ✅ | — | `projects.create` | **tạo project** | 197 |
| `/developers/projects/{id}/archive` | POST | → 303 | `require_account` | ✅ | — | `projects.archive` | **lưu trữ project** | 197 |
| `/developers/keys` | GET | `dev_keys.html` | `require_account` | — | **P** `keys` | `_keys_context` + `_projects_context` | không | 179, 197 |
| `/developers/keys` | POST | `dev_keys.html` | `require_account` | ✅ | — | `devkeys.issue` | **tạo khoá** · plaintext trả **một lần** trong phản hồi này | 179, 197 |
| `/developers/keys/{key_id}/revoke` | POST | → 303 | `require_account` | ✅ | — | `devkeys.revoke` | **thu hồi, không đảo ngược** | 179 |
| `/developers/keys/{key_id}/rotate` | POST | `dev_keys.html` | `require_account` | ✅ | — | `devkeys.rotate` | **đổi bí mật** · plaintext mới trả **một lần** | 179 |
| `/developers/logs` | GET | `dev_logs.html` | `require_account` | — | **P** `logs` | `request_log` (chỉ metadata — §7) | không | 201, 208 |
| `/developers/logs/{wanted_id}` | GET | `dev_log_detail.html` | `require_account` | — | **C** → `logs` | `request_log` + job liên quan | không | 201, 208 |
| `/developers/jobs` | GET | `dev_jobs.html` | `require_account` | — | **C** → `logs` | `_recent_api_jobs` (10 job mới nhất có `api_meta`) | không | 197 |
| `/developers/usage` | GET | `dev_usage.html` | `require_account` | — | **P** `usage` | `usage.*` + `budgets.*` + `credit.so_du` | không | 203 |
| `/developers/budgets` | POST | `dev_usage.html` | `require_account` | ✅ | — | `budgets.create` | **tạo ngân sách** (KHÔNG chạm sổ credit) | 203 |
| `/developers/budgets/{id}/delete` | POST | → 303 | `require_account` | ✅ | — | `budgets.delete` | **xoá ngân sách** | 203 |
| `/developers/webhooks` | GET | `dev_webhooks.html` | `require_account` | — | **P** `webhooks` | `_all_webhooks` + `webhook_console.*` | không | 202 |
| `/developers/webhooks/{id}/test` | POST | → 303 | `require_account` | ✅ | — | `webhook_console.send_test` | **gửi sự kiện thử ra ngoài** | 202 |
| `/developers/webhooks/{id}/rotate` | POST | → 303 | `require_account` | ✅ | — | `webhook_console.rotate_secret` | **đổi secret** · plaintext **một lần** qua `SECRET_ONCE_KEY` | 202 |
| `/developers/webhooks/{id}/disable` | POST | → 303 | `require_account` | ✅ | — | cột `enabled` | **tắt endpoint** | 202 |
| `/developers/webhooks/deliveries/{id}/resend` | POST | → 303 | `require_account` | ✅ | — | `webhook_console.resend` | **giao lại** (có trần chống lạm dụng) | 202 |
| `/developers/notifications` | GET | `dev_notifications.html` | `require_account` | — | **C** → `overview` | `notifications.*` | không | 197 |
| `/developers/notifications/read` | POST | → 303 | `require_account` | ✅ | — | `notifications.mark_read` | **đánh dấu đã đọc** | 197 |
| `/developers/settings` | GET | `dev_settings.html` | `require_account` | — | **P** `settings` | tĩnh | không | 197 |
| `/developers/privacy` | GET | `dev_privacy.html` | `require_account` | — | **C** → `settings` | `governance.*` | không | 211 |
| `/developers/privacy/export` | GET | — (`Response`) | `require_account` | — | — | `governance.export_for` | **xuất dữ liệu tài khoản** | 211 |

## 2. Cây điều hướng đang sống

Khai ở **một chỗ**: `server/routes/developer/_chung.py`
(`SECTIONS` · `NHOM_NAV` · `CHA_CUA` · `MUC_CON`).

```
BẮT ĐẦU     Tổng quan ─────── Thông báo
            Cắm vào công cụ ─ Bốn bước đầu (quickstart)
THAM CHIẾU  Công cụ & model ─ Chạy thử (playground) · {tool_name}
            Giá & mô phỏng
            Tài liệu & SDK
TÀI KHOẢN   Khóa API ──────── Project
            Hoạt động ─────── Job
            Sử dụng & credit
            Webhook
            Cài đặt & bảo mật ─ Dữ liệu & lưu trữ
```

**10 mục cấp cao nhất, 3 nhóm.** Trần cứng là 12 (`test_303:TRAN_MUC`).

## 3. Sáu route bị hạ khỏi thanh bên vẫn SỐNG

`quickstart` · `projects` · `playground` · `jobs` · `notifications` · `privacy`.

`test_303::test_trang_bi_ha_cap_van_song_va_van_tim_lai_duoc` chốt cả hai
chiều: route trả 200, **và** dải mục con của trang cha phải trỏ tới nó.
⇒ Không được xoá, không được bỏ khỏi `MUC_CON`.

## 4. Route KHÔNG có trang riêng

`/developers/openapi/download` và `/developers/privacy/export` trả `Response`
(tệp tải về), không phải HTML. Chúng không có mục điều hướng và không cần.

## 5. Ranh giới công khai/riêng tư

`TRANG_CONG_KHAI` **rỗng** — và khối chú thích 30 dòng trên nó nói rõ đây là
một **chốt của chủ sản phẩm ngày 25/08**, không phải việc chưa làm:

> "/developers tools dung sau dang nhap la dung roi. he thong cua ta API can
> phai dang nhap moi duoc kich hoat"

Bán hàng nằm ở `/gia-api` và `/huong-dan` — cả hai đã công khai, ngoài khu này.
`test_300` chốt **cả hai chiều**: thêm một trang riêng tư vào danh sách công
khai là gate đỏ, và mở một trang mà không sửa danh sách cũng vậy.

Bộ máy phục vụ khách ẩn danh (`tai_khoan_tuy_chon`, `_nav(da_dang_nhap=…)`,
khối "Đăng ký lấy khóa" trong `developers_base.html`) **vẫn còn và vẫn chạy**,
chỉ là hiện không trang nào kích hoạt nó. Đó là cố ý — mở một trang sau này chỉ
cần thêm một khoá vào `frozenset`.

## 6. Điều KHÔNG có ở đây, và là cố ý

- **Không** có credential của nhà cung cấp. `platform_core.api_keys` (khoá
  Gemini v.v.) không được import ở bất cứ tệp nào trong `server/routes/developer/`.
  `test_179::test_the_developer_key_domain_never_touches_provider_credentials`.
- **Không** có OAuth app management — D1 quyết không xây.
- **Không** có tuyến nào của portal gọi thẳng đường tính tiền của `/api/v1`.
  Playground gửi khoá của chính khách từ trình duyệt tới `/api/v1`
  (`dev_playground.py` docstring: *"the platform has exactly one on purpose"*).
