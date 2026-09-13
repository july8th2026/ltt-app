# 03 — Information Architecture Freeze

MODE: DESIGN DECISION ONLY. Prerequisites: `01_LIVE_EVIDENCE.md`, `02_DEEP_AUDIT.md`.

Tài liệu này **đóng băng** bố cục danh mục. Pha C không được đổi nó; muốn đổi
thì sửa tài liệu này trước.

---

## 1. Luật nền

**L1.** Không route nào bị xoá hay đổi URL. 31 `@expose` + mọi URL SQLAdmin giữ
nguyên đường dẫn. Hạ khỏi thanh bên ≠ xoá (bằng chứng đã có: 12 route hôm nay đã
sống ngoài nav — `02` A-03).

**L2.** Thanh bên khai **nơi chốn**, không khai **hành động**. Hành động sống
trong ngữ cảnh của đối tượng nó tác động.

**L3.** Trần thanh bên: **7 mục cha** (sáu miền nền tảng và một miền app được
duyệt ngày 2026-09-13 cho VPS V4). Trần mục con mỗi miền: **6**. Vượt trần là
gate đỏ (test chốt, khuôn `test_303` của `/developers`).

**L4.** Bảng thô SQLAdmin không đứng ngang hàng trang nghiệp vụ. Chúng sống ở
`Hệ thống → Nâng cao / Data Explorer`.

**L5.** Một trang chỉ có **một** mục cha sáng. Mở trang con thì cha sáng.

---

## 2. Cây điều hướng đích

```
Tổng quan                    /admin/
Khách hàng                   /admin/khach-hang
  └ Hồ sơ 360                /admin/nguoi-dung?q=…
Tài chính                    /admin/doanh-thu
  ├ Đơn hàng                 /admin/don
  ├ Sổ credit                /admin/credit-entry/list
  └ Gói nạp                  /admin/goi
API Platform                 /admin/api-tong-quan
  ├ Overview                 /admin/api-tong-quan
  ├ Access                   /admin/api-tai-khoan
  ├ Governance               /admin/api-cong-cu
  ├ Operations               /admin/api-request
  └ Economics                /admin/api-gia
Vận hành                     /admin/apikeys
  ├ Provider Credentials     /admin/apikeys
  ├ Model                    /admin/api-models
  └ Job                      /admin/job/list
Hệ thống                     /status
  ├ Tình trạng               /status
  ├ Nhật ký admin            /admin/nhat-ky-admin/list
  └ Nâng cao / Data Explorer /admin/nang-cao
```

**6 mục cha · nhiều nhất 5 mục con · tổng 17 mục hiển thị** (hôm nay: 25 mục
phẳng). Mỗi mục cha trỏ tới trang con đầu tiên của nó — không có "trang cha rỗng".

Ba mục con dùng thẳng URL SQLAdmin (`credit-entry/list`, `job/list`,
`nhat-ky-admin/list`): chúng **đã** thoả hợp đồng trang tương ứng (chỉ đọc, có
lọc, không có nút tạo/sửa/xoá) và prompt cấm rewrite SQLAdmin. Chúng được nâng
**lên** subnav vì là workflow chính, khác với 5 bảng còn lại ở Data Explorer.

---

## 3. Ma trận Current → Target (mọi view hiện có)

Cột **Loại**: PRIMARY = trang chính của miền · SUB = mục con · CTX = hành động
theo ngữ cảnh (không có mục nav) · HIDDEN = giữ URL, không có mục nav ·
EXPLORER = khu dữ liệu thô.

### 3a. Trang tự viết — `server/admin.py`

| URL hiện tại | Nhãn hôm nay | → Miền | Loại | Nhãn mới | Ghi chú |
|---|---|---|---|---|---|
| *(chưa có)* | – | Tổng quan | **PRIMARY** | Tổng quan | **URL mới `/admin/`** — mục duy nhất được thêm |
| *(chưa có)* | – | Khách hàng | **PRIMARY** | Khách hàng | **URL mới `/admin/khach-hang`** |
| `/admin/nguoi-dung` | Chi tiết người dùng | Khách hàng | SUB | Hồ sơ 360 | mở rộng thành Customer 360 |
| `/admin/doanh-thu` | Doanh thu | Tài chính | **PRIMARY** | Tổng quan tài chính | **giữ URL**, đổi nhãn |
| `/admin/don` | Đơn hàng | Tài chính | SUB | Đơn hàng | |
| `/admin/don/action` | – | Tài chính | CTX | – | mark-paid |
| `/admin/goi` | Gói nạp | Tài chính | SUB | Gói nạp | |
| `/admin/goi/action` | – | Tài chính | CTX | – | |
| `/admin/grant-credit` | Cấp credit | Tài chính | **CTX** | – | **rời primary nav** (`02` A-02); vào từ Hồ sơ 360 |
| `/admin/apikeys` | APIKEYS | Vận hành | **PRIMARY** | Provider Credentials | đổi nhãn (`02` A-04) |
| `/admin/api-key-them` | – | Vận hành | CTX | – | |
| `/admin/api-key-sua` | – | Vận hành | CTX | – | |
| `/admin/api-key-test` | – | Vận hành | CTX | – | |
| `/admin/api-key-action` | – | Vận hành | CTX | – | |
| `/admin/api-models` | – | Vận hành | SUB | Model | lên subnav |
| `/admin/api-models-refresh` | – | Vận hành | CTX | – | |

### 3b. Khu API — `server/admin_api.py` (12 mục → 1 mục cha + 5 mục con)

| URL hiện tại | → Mục con | Loại |
|---|---|---|
| `/admin/api-tong-quan` | Overview | **PRIMARY** của miền |
| `/admin/api-tai-khoan` | Access | SUB |
| `/admin/api-khoa` | Access | HIDDEN (tab trong Access) |
| `/admin/api-khoa-action` | Access | CTX |
| `/admin/api-cong-cu` | Governance | SUB |
| `/admin/api-chinh-sach` | Governance | HIDDEN (tab) |
| `/admin/api-chinh-sach-action` | Governance | CTX |
| `/admin/api-kill-switch` | Governance | HIDDEN (tab) — **rời primary nav** |
| `/admin/api-kill-switch-action` | Governance | CTX |
| `/admin/api-request` | Operations | SUB |
| `/admin/api-job` | Operations | HIDDEN (tab) |
| `/admin/api-bao-mat` | Operations | HIDDEN (tab) |
| `/admin/api-trace` | Operations | CTX (mở từ một request) |
| `/admin/api-trace-export` | Operations | CTX |
| `/admin/api-gia` | Economics | SUB |
| `/admin/api-margin` | Economics | HIDDEN (tab) |

⭐ Đây là chỗ giảm mạnh nhất: **12 mục sidebar → 1 mục cha + 5 mục con**, không
mất một năng lực nào, không đổi một URL nào.

### 3c. Bảng thô SQLAdmin

| URL | → Miền | Loại | Vì sao |
|---|---|---|---|
| `/admin/credit-entry/*` | Tài chính | **SUB** | sổ credit là workflow chính; đã chỉ-đọc sẵn |
| `/admin/job/*` | Vận hành | **SUB** | GJ3 |
| `/admin/nhat-ky-admin/*` | Hệ thống | **SUB** | audit là workflow chính |
| `/admin/user/*` | Hệ thống → Nâng cao | EXPLORER | trang chính là `/admin/khach-hang`; sửa vai trò/khoá vẫn ở đây (giữ `on_model_change` audit) |
| `/admin/session/*` | Hệ thống → Nâng cao | EXPLORER | thu hồi phiên **cũng** có ở Hồ sơ 360 |
| `/admin/app-access/*` | Hệ thống → Nâng cao | EXPLORER | |
| `/admin/api-key/*` | Hệ thống → Nâng cao | EXPLORER | bảng thô của Provider Credentials |
| `/admin/platform-info/*` | Hệ thống → Nâng cao | EXPLORER | |

---

## 4. Ma trận tương thích route

Mọi URL đang sống, và điều gì xảy ra với nó.

| URL | Giữ? | Trong nav? | Redirect? | Mục cha sáng | Dấu trang cũ |
|---|---|---|---|---|---|
| `/admin/nguoi-dung` | ✅ | mục con | ❌ | Khách hàng | ✅ nguyên vẹn |
| `/admin/grant-credit` | ✅ | ❌ (CTX) | ❌ | Tài chính | ✅ vẫn mở được |
| `/admin/apikeys` | ✅ | mục cha | ❌ | Vận hành | ✅ |
| `/admin/api-key-them\|sua\|test\|action` | ✅ | ❌ | ❌ | Vận hành | ✅ |
| `/admin/api-models`, `-refresh` | ✅ | mục con / CTX | ❌ | Vận hành | ✅ |
| `/admin/doanh-thu` | ✅ | mục cha | ❌ | Tài chính | ✅ |
| `/admin/goi`, `/goi/action` | ✅ | mục con / CTX | ❌ | Tài chính | ✅ |
| `/admin/don`, `/don/action` | ✅ | mục con / CTX | ❌ | Tài chính | ✅ |
| 16 URL `/admin/api-*` | ✅ tất cả | 5 mục con, còn lại tab/CTX | ❌ | API Platform | ✅ |
| 8 × `/admin/<model>/list\|details\|edit\|delete` | ✅ tất cả | 3 mục con + 5 ở Nâng cao | ❌ | theo §3c | ✅ |
| `/status` | ✅ | mục cha | ❌ | Hệ thống | ✅ |

**Số redirect: 0. Số URL bị xoá: 0. Số URL đổi: 0.**
Chỉ có **2 URL mới**: `/admin/` và `/admin/khach-hang`; cộng `/admin/nang-cao`
(trang mục lục của Data Explorer) = **3 URL mới**.

⚠️ `/admin/` hiện chưa có trang riêng. Phải kiểm: sqladmin có đang chiếm `/admin/`
làm trang index của nó không — nếu có thì Tổng quan phải là một `BaseView` được
đăng ký ở vị trí đầu, hoặc dùng một đường dẫn khác. **Việc kiểm này thuộc C0.**

---

## 5. Hợp đồng tìm kiếm & điều hướng

### 5a. Tìm kiếm toàn cục — chốt phạm vi theo authority thật

Ảnh mockup vẽ một ô "Tìm kiếm người dùng, đơn hàng, log…". **Hôm nay không có
backend nào cho tìm kiếm liên thực thể.**

**Chốt MVP:** topbar có **một ô tìm KHÁCH HÀNG**, không phải omnibox.
Nhãn đúng: *"Tìm khách hàng (email hoặc User ID)"*.
Authority: `credit.tim_theo_email(db, q)` + `db.get(User, q)` — đã dùng ở
`server/admin.py:237`. Submit → `/admin/nguoi-dung?q=…`.

⛔ **Không** làm ô tìm kiếm nhận cả đơn hàng/log rồi trả rỗng — đó là hứa hẹn giả.
Tìm theo mã đơn ở `/admin/don`; theo `request_id` ở API → Operations. Omnibox
liên thực thể → `24_DEFERRED_POST_MVP.md`.

### 5b. Breadcrumb

`Miền / Trang` (2 cấp). Cấp đầu là mục cha, luôn bấm được. Trang PRIMARY của miền
không hiện breadcrumb (nó **là** cấp đầu).

### 5c. Trạng thái mục cha sáng

Bảng ánh xạ `trang → mục cha` là **dữ liệu**, khai một chỗ (`CHA_CUA`, khuôn
`/developers`). Route CTX và HIDDEN cũng phải có dòng ở đó — nếu không, vào
`/admin/api-kill-switch` sẽ không mục nào sáng.

### 5d. Subnav

Dải mục con hiện **trong** trang, dưới tiêu đề. Chỉ hiện các mục con của mục cha
đang mở. Tab cấp ba (Access/Governance/Operations/Economics có nhiều tab) dùng
`.dev-sub` — đã có sẵn trong `ltt.css:586–598`.

### 5e. Mobile

Giữ `.adm-mobilebar` + `<details>` hiện có (`admin.py:170–173`), đổ ra **cây hai
cấp** thay vì danh sách phẳng 25 mục.

---

## 6. Phương án đã cân nhắc và LOẠI

| Phương án | Vì sao loại |
|---|---|
| Giữ 12 mục API ở sidebar, chỉ đổi màu/icon | Không giải quyết A-01. Chủ sản phẩm yêu cầu **bố cục lại danh mục**, không phải trang trí |
| Xoá các route trùng lặp cho gọn | Vi phạm L1 và prompt 03. Dấu trang + link hỗ trợ đang sống |
| Đổi `/admin/doanh-thu` → `/admin/tai-chinh` cho khớp nhãn mới | Đổi URL để chiều một cái nhãn. Nhãn đổi được, URL thì không |
| Xây trang Sổ credit mới thay `credit-entry/list` | SQLAdmin đã thoả hợp đồng (chỉ đọc, có lọc). Viết lại là công không đổi lấy gì. Cross-link đặt ở Hồ sơ 360 + Đơn hàng — đúng chỗ operator cần |
| Bỏ `/admin/khach-hang` mới, dùng `/admin/user/list` làm danh sách khách | SQLAdmin không dựng được rail chú ý, không đặt được "Mở hồ sơ 360" làm hành động chính, và trộn bảng thô vào workflow chính (A-05) |
| Omnibox tìm mọi thứ như trong ảnh | Không có authority (§5a) |
| Đưa Nexus / VPS / các app vào sidebar admin | Ngoài phạm vi MVP ban đầu. **Phần VPS ĐÃ THAY ngày 2026-09-13**: chủ dự án duyệt hợp đồng admin chung cho `ADMIN > VPS > Cổng hạ tầng`; app khai metadata, nền tảng không biết slug cụ thể. |

---

## 7. Điều kiện ra của bước 03

- [x] Mọi view hiện có đã có ô trong ma trận §3
- [x] Ma trận tương thích §4 **không có ô "xoá"** và **không có redirect**
- [x] Cây điều hướng ≤ 6 mục cha, ≤ 6 mục con/miền
- [x] Phạm vi tìm kiếm chốt theo authority thật, không hứa hẹn giả
- [ ] **C0 phải kiểm**: `/admin/` có bị sqladmin chiếm không (§4)

---

**STOP.** Không implement. Bước tiếp: `04_EXTENSION_CONTRACT.md`.
