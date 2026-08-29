# 01 — Live Admin Evidence Lock

MODE: READ ONLY. Không sửa runtime/template/CSS trong bước này.

Mọi dòng dưới đây là **FACT** đọc từ live repo ngày 2026-08-29, nhánh
`admin-mvp-v3` (tách từ `public-api-v2` @ `d66d9b3`). Suy luận và đề xuất được
đánh dấu rõ.

---

## 0. Phạm vi tìm được

| Thứ prompt 01 yêu cầu tìm | Live equivalent |
|---|---|
| `server/admin.py` | ✅ 1.388 dòng / 75 KB |
| `server/admin_api.py` | ✅ 1.897 dòng / 98 KB |
| `server/admin_templates/**` | ✅ **chỉ** `sqladmin/base.html` (4.737 byte) — không có template cho trang tự viết |
| SQLAdmin overrides | ✅ `server/admin_templates/sqladmin/base.html` |
| operator/admin auth authority | ✅ `server/admin.py:83 AdminAuth` + `_is_admin()` |
| CSRF | ✅ `server/auth/csrf.py` (`issue_csrf_token`/`verify_csrf_token`) |
| audit logging | ✅ `server/admin.py:68 ghi_nhat_ky()` → `platform_core/models.py:574 NhatKyAdmin` |
| credit/billing/payment | ✅ `platform_core/billing.py`, `platform_core/credit.py`, `models.py:599 CreditEntry`, `models.py:753 PaymentOrder` |
| provider credentials/pool | ✅ `platform_core/providers.py`, `models.py ApiKey`, `platform_core/api_pool.py` |
| `platform_core/public_api/admin_console.py` | ✅ 670 dòng |
| public API pricing/policy/kill-switch/security/metrics | ✅ `platform_core/public_api/{pricing,policy,security_log,metrics,costing,keys,limits}.py` |
| admin tests | ✅ `test_70_admin_h3`, `test_124_admin_ui`, `test_162_cap_credit_admin`, `test_205_admin_api_console` (+ 53 tệp test khác có nhắc `admin`) |

**Phát hiện ngoài read set của prompt** (quan trọng — xem §6):
`docs/developer_portal_mvp_ui/**`, `server/routes/developer/_chung.py`,
`server/templates/developers_base.html`, `server/templates/_kieu_chung.html`.

---

## 1. Route / View inventory

Ký hiệu cột **DL** (danger level): R = READ · RW = REVERSIBLE_WRITE ·
S = SENSITIVE · D = DANGEROUS.

### 1a. Trang nghiệp vụ tự viết (`BaseView`) — `server/admin.py`

| Route | Method | Class:line | Miền | Nav | Mutation | CSRF | Audit | DL |
|---|---|---|---|---|---|---|---|---|
| `/admin/nguoi-dung` | GET | `ChiTietNguoiDungView:204` | Khách hàng | ✅ | – | – | – | R |
| `/admin/apikeys` | GET | `ApiKeysConsole:295` | Vận hành | ✅ | – | – | – | R |
| `/admin/grant-credit` | GET,POST | `GrantCreditView:504` | Tài chính | ✅ | cấp credit | ✅ | ✅ | **D** |
| `/admin/api-key-them` | GET,POST | `AddApiKeyView:664` | Vận hành | ❌ | tạo provider credential | ✅ | ❌ | **S** |
| `/admin/api-key-sua` | GET,POST | `SuaApiKeyView:766` | Vận hành | ❌ | sửa provider credential | ✅ | ❌ | **S** |
| `/admin/api-key-test` | GET | `ApiKeyActionView:919` | Vận hành | ❌ | – (gọi provider) | – | ❌ | R |
| `/admin/api-key-action` | POST | `ApiKeyActionView:919` | Vận hành | ❌ | enable/disable/reset/xoá | ✅ | ❌ | **D** |
| `/admin/api-models` | GET | `ModelsView:1007` | Vận hành | ❌ | – | – | – | R |
| `/admin/api-models-refresh` | GET | `ModelsView:1007` | Vận hành | ❌ | làm mới registry | – | ❌ | RW |
| `/admin/doanh-thu` | GET | `RevenueView:1118` | Tài chính | ✅ | – | – | – | R |
| `/admin/goi` | GET,POST | `PackagesView:1162` | Tài chính | ✅ | tạo/sửa gói nạp | ✅ | ❌ | **S** |
| `/admin/goi/action` | POST | `PackagesView:1162` | Tài chính | ❌ | bật/tắt/xoá gói | ✅ | ❌ | **S** |
| `/admin/don` | GET | `OrdersView:1266` | Tài chính | ✅ | – | – | – | R |
| `/admin/don/action` | POST | `OrdersView:1266` | Tài chính | ❌ | **mark-paid** | ✅ | ❌ | **D** |

### 1b. Bảng thô (`ModelView`) — `server/admin.py`

URL do sqladmin sinh: `/admin/<identity>/list|details|edit|delete`.

| Model | Class:line | identity | create | edit | delete | Nav | DL | Phân loại |
|---|---|---|---|---|---|---|---|---|
| `User` | `UserAdmin:377` | `user` | ❌ | ✅ | ❌ | ✅ | **S** | PRIMARY WORKFLOW |
| `CreditEntry` | `CreditEntryAdmin:425` | `credit-entry` | ❌ | ❌ | ❌ | ✅ | R | PRIMARY WORKFLOW |
| `AppAccess` | `AppAccessAdmin:440` | `app-access` | ✅ | ✅ | ✅ | ❌ | **S** | SUPPORTING |
| `Job` | `JobAdmin:458` | `job` | ❌ | ❌ | ❌ | ✅ | R | SUPPORTING |
| `DbSession` | `SessionAdmin:473` | `session` | ❌ | ❌ | ✅ | ✅ | **D** | SUPPORTING (xoá = thu hồi phiên) |
| `PlatformInfo` | `PlatformInfoAdmin:493` | `platform-info` | ❌ | ❌ | ❌ | ❌ | R | DATA EXPLORER ONLY |
| `NhatKyAdmin` | `NhatKyAdminView:608` | `nhat-ky-admin` | ❌ | ❌ | ❌ | ✅ | R | PRIMARY WORKFLOW |
| `ApiKey` | `ApiKeyAdmin:628` | `api-key` | ❌ | ✅ (field an toàn) | ✅ | ❌ | **S** | DATA EXPLORER ONLY |

`UserAdmin` là ModelView **duy nhất có audit**: `on_model_change` (`:389`) ghi
`NhatKyAdmin` khi đổi `role`/`is_active`/`is_verified`/`display_name`.

### 1c. Khu API Platform (`BaseView`) — `server/admin_api.py`

Tất cả đều có mục riêng trong sidebar (qua `NAV`, `:1883`).

| Route | Method | Class:line | Mutation | CSRF | Audit | DL |
|---|---|---|---|---|---|---|
| `/admin/api-tong-quan` | GET | `ApiOverviewView:131` | – | – | – | R |
| `/admin/api-tai-khoan` | GET | `ApiAccountsView:258` | – | – | – | R |
| `/admin/api-khoa` | GET | `ApiKeysAdminView:415` | – | – | – | R |
| `/admin/api-khoa-action` | POST | `ApiKeysAdminView:415` | revoke customer key | ✅ | ✅ | **D** |
| `/admin/api-cong-cu` | GET | `ApiToolsView:653` | – | – | – | R |
| `/admin/api-chinh-sach` | GET | `ApiPolicyView:747` | – | – | – | R |
| `/admin/api-chinh-sach-action` | POST | `ApiPolicyView:747` | đổi policy/limit | ✅ | ✅ | **S** |
| `/admin/api-kill-switch` | GET | `ApiKillSwitchView:926` | – | – | – | R |
| `/admin/api-kill-switch-action` | POST | `ApiKillSwitchView:926` | bật/tắt kill switch | ✅ | ✅ | **D** |
| `/admin/api-gia` | GET | `ApiPricingView:1057` | – | – | – | R |
| `/admin/api-gia-action` | POST | `ApiPricingView:1057` | publish/retire giá | ✅ | ✅ | **S** |
| `/admin/api-margin` | GET | `ApiMarginView:1284` | – | – | – | R |
| `/admin/api-request` | GET | `ApiRequestsView:1367` | – | – | – | R |
| `/admin/api-job` | GET | `ApiJobsView:1441` | – | – | – | R |
| `/admin/api-bao-mat` | GET | `ApiSecurityView:1532` | – | – | – | R |
| `/admin/api-trace` | GET | `ApiTraceView:1671` | – | – | – | R |
| `/admin/api-trace-export` | GET | `ApiTraceView:1671` | – (xuất tệp) | – | – | R |

### 1d. Tổng kết bề mặt

| | Số |
|---|---|
| `@expose` (custom views) | **31** (14 ở `admin.py` + 17 ở `admin_api.py`) |
| trong đó POST | **11** |
| SQLAdmin ModelView | **8** (× 4–5 URL sinh tự động mỗi model) |
| `admin.add_view()` | **19** ở `admin.py:1364–1387` + **12** từ `admin_api.VIEWS` |
| **Mục sidebar hiển thị** | **25** (13 từ `_ADM_NAV` + 12 từ `NAV`) + 4 dòng nhóm |

---

## 2. Secret inventory

| Secret | Nơi lưu | Quy tắc lộ hiện hành | Bằng chứng | Đánh giá |
|---|---|---|---|---|
| Session token | `DbSession.id` — **PK chính là token cookie** | **Không bao giờ render.** `column_list`/`column_details_list` cố ý bỏ `.id` | `server/admin.py:477–485` (có bình luận giải thích) | ✅ ĐÚNG |
| Provider credential | `ApiKey.credential_enc` (mã hoá) | Không có trong `column_list` lẫn `column_details_list`; chỉ `key_preview` (4 số cuối). `form_columns` cố ý loại `credential_enc` | `server/admin.py:640–660` | ✅ ĐÚNG |
| Customer Public API secret | `DeveloperApiKey` | Hiện một lần lúc tạo, backend không tái tạo được | `platform_core/public_api/keys.py` | ✅ ĐÚNG |
| Password hash | `User.password_hash` | Không nằm trong `column_list` của `UserAdmin` | `server/admin.py:384` | ✅ ĐÚNG |
| Webhook secret | `WebhookSubscription` | Không có ModelView | – | ✅ (không có bề mặt) |
| Payment secret | PayOS key ở `secrets/app.env` | Không có bề mặt admin | – | ✅ |

⇒ **Không tìm thấy lỗ lộ secret nào ở admin hiện tại.** Đây là bất biến phải giữ
nguyên qua toàn bộ pha C, và là nội dung cổng D1.

---

## 3. Money inventory

| Thành phần | Vị trí | Bất biến |
|---|---|---|
| Sổ credit | `models.py:599 CreditEntry` | **Append-only** — `can_create/edit/delete = False` ở `admin.py:435–437` |
| Cấp credit tay | `GrantCreditView:504` → `credit.cap_tay(by=...)` | Ghi **bút toán mới**, có CSRF + `ghi_nhat_ky` |
| Đơn nạp | `models.py:753 PaymentOrder` | `credited` chỉ True **một lần** |
| Mark-paid | `OrdersView:1321 order_action` → `billing.ghi_nhan_tra` | **Idempotent** (`billing.py:121 if order.credited: return order`), `with_for_update()` trên Postgres (`billing.py:116–117`), ghi `by="admin"` vào `order.note` |
| Gói nạp | `PackagesView:1162` | `price_vnd` + `credits` + `bonus_percent` **chốt tại lúc tạo đơn** ⇒ đổi giá gói không ảnh hưởng đơn cũ (`models.py:753` docstring) |
| Giá API | `public_api/pricing.py` qua `/admin/api-gia` | có lifecycle publish/retire + audit |
| Margin/cost | `public_api/costing.py` qua `/admin/api-margin` | chỉ đọc |

### Đơn vị tiền — bất biến hiển thị

`PaymentOrder` tách **`price_vnd`** (đồng) khỏi **`credits`** (credit).
Tỉ giá nền tảng: **1 credit = 100 đ** (Q31).
⇒ Không ô UI nào được trộn hai đơn vị. Số dư khách là **credit**, không phải "đ".

---

## 4. SQLAdmin inventory

Phân loại theo yêu cầu prompt 01:

| Phân loại | ModelView |
|---|---|
| PRIMARY WORKFLOW | `UserAdmin`, `CreditEntryAdmin`, `NhatKyAdminView` |
| SUPPORTING | `JobAdmin`, `SessionAdmin`, `AppAccessAdmin` |
| DATA EXPLORER ONLY | `PlatformInfoAdmin`, `ApiKeyAdmin` |

`ApiKeyAdmin` đã tự nhận mình là bảng thô: `name_plural = "APIKEYS (bảng thô)"`,
kèm bình luận `:630–636` ghi lại một sự cố thật — chủ dự án vào nhầm trang này
thay vì `/admin/apikeys` vì **hai mục menu từng cùng tên**.

⇒ Đây là bằng chứng sống cho luận điểm của prompt 03: trang thô cạnh tranh với
trang nghiệp vụ trong cùng một danh sách phẳng là lỗi IA có hậu quả đo được.

---

## 5. Ba nguồn điều hướng cùng tồn tại (FACT)

| # | Nơi khai | Nội dung |
|---|---|---|
| 1 | `server/admin.py:103 _ADM_NAV` | 13 mục + 4 nhóm |
| 2 | `server/admin_api.py:1883 NAV` | 12 mục `API — …`, được `*_NAV_API` chèn vào (1) |
| 3 | `server/admin_templates/sqladmin/base.html:54–59` | **5 link `<a>` hardcode** trong thanh `.ltt-adminbar` |

Nguồn (3) là một **danh sách thứ ba, viết tay, không ai đồng bộ** — trang
SQLAdmin có một bộ điều hướng khác hẳn 25 mục của trang tự viết.

### Lỗi kèm theo, tìm được ở cùng file

`server/admin_templates/sqladmin/base.html:22`:
```html
<link rel="stylesheet" href="/static/ltt.css">
```
**Không có `?v=`.** Trang tự viết thì có (`server/admin.py:161` dùng
`_asset_ver()`). ⇒ Sau mỗi lần đổi `ltt.css`, **trang SQLAdmin nhận bản CSS cũ
từ Cloudflare** cho tới khi hết TTL — đúng cái bẫy CLAUDE.md quy tắc 6 mô tả.
Xếp **P1**, sửa 1 dòng.

---

## 6. Tiền lệ đã có trong repo — `/developers` (FACT)

`docs/developer_portal_mvp_ui/` chứa đủ 11 tài liệu của một đợt hiện đại hoá đã
hoàn tất, cùng khuôn với bộ prompt này. Sản phẩm còn sống trong mã:

| Hạng mục | Vị trí | Ghi chú |
|---|---|---|
| Vỏ dùng chung | `server/templates/developers_base.html` | extends `base.html`, `{% block page_mode %}wide{% endblock %}` |
| **Một** nguồn điều hướng | `server/routes/developer/_chung.py:132 SECTIONS` · `:176 NHOM_NAV` · `:184 CHA_CUA` · `:198 MUC_CON` | mọi trang phải có một dòng ở `SECTIONS` |
| Trần chống phình nav | `test_303` | trần 12 mục |
| Primitives | `.dev-bang` `.dev-tt` `.dev-trong` `.dev-loc` `.dev-field` `.dev-hang` `.dev-nhom` `.dev-mat` `.dev-ma` `.dev-id` `.chi-so-luoi/.chi-so` `.dev-han-muc` `.tnum` — `server/static/ltt.css` | + `.card`/`.btn`/`input` ở `server/templates/_kieu_chung.html` |
| Hợp đồng viết sẵn | `docs/developer_portal_mvp_ui/10_DEVELOPER_UI_CONTRACT.md` | có cả luật "khi nào được tạo lớp CSS mới" |

⭐ **Bộ prompt V3 Final không biết về khu này.** `SOURCE_DERIVED_GUARDRAILS.md`
không nhắc `/developers` một chữ nào. Đây là INFERENCE quan trọng nhất của bước
01: prompt 04 và 07 phải chuyển từ *thiết kế mới* sang *port khuôn đã có*.

---

## 7. Token thiết kế — đã dùng chung sẵn (FACT)

`server/static/ltt.css:6–33` khai một bộ token duy nhất, rồi khai
**alias tương thích** trỏ vào chính nó:

```
--bg   → var(--surface-canvas)      --fg    → var(--text-primary)
--panel→ var(--surface-raised)      --muted → var(--text-secondary)
--line → var(--border-subtle)       --accent→ var(--brand-primary)
--ok/--warn/--err → var(--status-success/warning/danger)
```

`.adm-*` dùng nhóm alias; `.dev-*` dùng nhóm token gốc. **Cùng một giá trị.**

⇒ Hệ quả trực tiếp: **dùng lại primitive `.dev-*` bên trong vỏ admin không cần
một dòng token nào.** Và bảng màu mà prompt 06 mô tả (carbon/near-black · steel
neutral · đỏ LTT tiết chế · xanh khoẻ · hổ phách chú ý · đỏ lỗi) **chính là bộ
token đang có**, không phải một hệ thiết kế mới.

---

## 8. Blast radius của CSS admin (FACT)

```
grep -rln "adm-content|adm-side|adm-nav" server/ --include=*.py --include=*.html
→ server/admin.py
  server/admin_api.py
```

**Namespace `.adm-*` chỉ hai tệp admin dùng.** Không app nào, không `/developers`,
không `/vps`.

Ngược lại `.app-side` (`ltt.css:629–632`, 210px) **dùng chung `/developers` +
`/vps`** — đụng vào nó là đụng hai khu khác.

⇒ Nới `.adm-content` (`ltt.css:163`, đang `max-width:1180px`) là thao tác **cô
lập**, không cần cơ chế `page_mode` mới.

---

## 9. Findings mở, chuyển sang bước 02

| ID | Sev | FACT | Ghi chú |
|---|---|---|---|
| E-01 | P1 | `sqladmin/base.html:22` nạp `ltt.css` **không cache-bust** | 1 dòng |
| E-02 | P1 | Ba nguồn điều hướng độc lập (§5) | gốc của "nav drift" |
| E-03 | P2 | **6/11 POST không ghi `NhatKyAdmin`**: `/api-key-them`, `/api-key-sua`, `/api-key-action`, `/goi`, `/goi/action`, **`/don/action`** | CSRF thì **11/11 có**. Mark-paid vẫn truy được qua `order.note` + `CreditEntry`, nên là **thiếu nhật ký admin**, không phải mất dấu vết tiền |
| E-04 | P1 | 25 mục sidebar phẳng; 2 trong đó là **trang hành động** (`/admin/grant-credit`, `/admin/api-kill-switch`) | |
| E-05 | P1 | 12 route (`api-key-them/sua/test/action`, `api-models*`, `goi/action`, `don/action`, …) **không có mục nav** — vào được chỉ bằng URL trực tiếp hoặc link trong thân trang | ma trận tương thích phải giữ hết |
| E-06 | P2 | Hai hệ thiết kế: trang tự viết dùng `ltt.css`; SQLAdmin dùng **Tabler + Bootstrap** (`sqladmin/base.html:11–16`) đã bị nhuộm dark bằng CSS đè | prompt 07 cho phép giữ, chỉ cần cùng vỏ/ngữ cảnh |
| E-07 | P0-tránh | Toàn bộ HTML admin là **f-string trong Python** ⇒ không test được markup, không tái dùng được | gốc của mọi thứ ở bước 02 |

---

## 10. Bất biến phải giữ nguyên qua pha C (chốt)

1. `CreditEntry` append-only — `can_create/edit/delete = False`.
2. `billing.ghi_nhan_tra` idempotent + `with_for_update()`.
3. `DbSession.id` không bao giờ render.
4. `ApiKey.credential_enc` không bao giờ render, không vào `form_columns`.
5. CSRF trên **cả 11** POST.
6. Kill switch: `reason` bắt buộc (`public_api/policy.py:428`, `tables.py:618`
   NOT NULL) + `expires_at`. **Không được thành toggle một cú bấm.**
7. `UserAdmin.on_model_change` giữ nguyên đường ghi audit.
8. Không xoá URL nào — kể cả 12 route không có nav (E-05) và các URL SQLAdmin.

---

**STOP.** Không sửa runtime/template/CSS. Bước tiếp: `02_DEEP_AUDIT.md`.
