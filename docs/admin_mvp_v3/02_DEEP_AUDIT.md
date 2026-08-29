# 02 — Deep Architecture + UX Audit

MODE: READ ONLY. Prerequisite: `01_LIVE_EVIDENCE.md`.

Lược đồ finding: `ID · severity · FACT · root cause · operator impact ·
architecture impact · class · regression risk`.
Class ∈ KEEP / NORMALIZE / MERGE / MOVE / HIDE / EXPLORER / DEFER.

---

## A. Information Architecture

### A-01 · **P0** · Sidebar là danh mục route, không phải mô hình miền

**FACT.** 25 mục phẳng: `server/admin.py:103 _ADM_NAV` (13) + `admin_api.py:1883
NAV` (12). Bốn dòng nhóm (`__grp__`) là toàn bộ cấu trúc phân cấp đang có. Không
có subnav, không có breadcrumb, không có khái niệm "mục cha đang mở".

**Root cause.** Mỗi lần thêm một `BaseView` là thêm một dòng vào `_ADM_NAV`. Danh
sách lớn dần theo số **trang**, không theo số **miền**. 12 mục `API — …` là ví dụ
cực đoan: một miền duy nhất chiếm **48% thanh bên**.

**Operator impact.** Muốn xử một sự cố API phải tự đoán trong 12 mục cùng tiền tố
cái nào chứa câu trả lời. Không có gì nói `api-request` và `api-job` và `api-trace`
là ba lát cắt của **một** dòng chảy.

**Architecture impact.** Không có chỗ đặt trang mới ngoài "cuối danh sách".

**Class.** NORMALIZE — 6 miền + subnav. **Regression risk:** cao nếu đổi URL;
**bằng 0 nếu chỉ đổi cách hiển thị** (xem A-03).

### A-02 · **P1** · Trang hành động nằm ở primary nav

**FACT.** `/admin/grant-credit` (`_ADM_NAV` mục "Cấp credit") và
`/admin/api-kill-switch` (mục "API — Kill switch") là hai **hành động**, không
phải hai nơi chốn. Cả hai đều là danger level D (`01` §1).

**Operator impact.** "Cấp credit" đứng ngang hàng "Người dùng" mời người ta bấm
vào nó **trước khi** biết cấp cho ai — đúng chiều ngược với luồng an toàn
(chọn đối tượng → xem ngữ cảnh → hành động).

**Class.** MOVE — thành hành động theo ngữ cảnh trong Customer 360 / API Governance.
Giữ URL cũ (A-03). **Regression risk:** thấp.

### A-03 · **P1** · 12 route không có mục nav, chỉ vào được bằng URL

**FACT.** `/admin/api-key-them`, `/api-key-sua`, `/api-key-test`, `/api-key-action`,
`/api-models`, `/api-models-refresh`, `/goi/action`, `/don/action`,
`/api-khoa-action`, `/api-chinh-sach-action`, `/api-kill-switch-action`,
`/api-gia-action` — không xuất hiện ở `_ADM_NAV` lẫn `NAV`.

**Hệ quả cho thiết kế.** "Không có trong nav" **đã là** một trạng thái hợp lệ
trong hệ này. Hạ một trang khỏi sidebar **không** phải là xoá nó. Đây là bằng
chứng để ma trận tương thích ở bước 03 không cần xoá URL nào.

**Class.** KEEP.

### A-04 · **P1** · Hai khái niệm "APIKEYS" khác nhau, và đã gây sự cố thật

**FACT.** `server/admin.py:630–636` ghi lại: `ApiKeyAdmin` từng có nhãn trùng với
`ApiKeysConsole`, và ngày 23/08 chủ dự án vào nhầm trang rồi báo *"Provider đâu có
`ltt_image`"*. Đã vá bằng cách đổi nhãn thành `"APIKEYS (bảng thô)"`.

Ngoài ra tồn tại **khái niệm thứ ba** cùng chữ "key": `/admin/api-khoa` =
**khoá của KHÁCH** (`DeveloperApiKey`). `admin_api.py:1879–1882` có bình luận
thừa nhận đúng rủi ro này khi chọn ký tự viết tắt.

**Root cause.** Ba thực thể — provider credential của nền tảng, bảng thô của nó,
và API key của khách — chia nhau một từ.

**Class.** NORMALIZE nhãn: `Provider Credentials` (Vận hành) vs `Khoá API của
khách` (API Platform → Access). **Không đổi định danh DB/domain.**

### A-05 · **P2** · Bảng thô cạnh tranh với trang nghiệp vụ trong cùng danh sách

**FACT.** `_ADM_NAV` trộn `/admin/user/list` (SQLAdmin thô) với
`/admin/nguoi-dung` (trang nghiệp vụ tổng hợp) — hai mục cạnh nhau, cùng nói về
người dùng, khác hẳn năng lực.

**Class.** EXPLORER — bảng thô xuống `Hệ thống → Advanced / Data Explorer`.

---

## B. Controller / Presentation

### B-01 · **P0** · Toàn bộ HTML admin là f-string trong Python

**FACT.** `server/admin.py` 75 KB / 1.388 dòng và `server/admin_api.py` 98 KB /
1.897 dòng — tỉ lệ byte/dòng ~54 và ~52, tức phần lớn là **chuỗi HTML dài**.
Vỏ trang: `server/admin.py:145 _admin_shell()` nối chuỗi thủ công.
`server/admin_templates/` **không có** template nào cho trang tự viết.

**Hệ quả đo được.**
- Không test được markup (4 tệp test admin đều test hành vi HTTP, không test cấu trúc).
- Inline style rải rác: `style="max-width:620px"` (`:222`), `style="font-size:12px"`
  (`:260`), `style="width:{w}%;background:{col}"` (`:200`).
- Mỗi trang tự dựng lại `pagehead`, `ui-card`, `billing-line` bằng tay.
- Hàm helper cục bộ trong từng view (`_bang()` ở `:253`) — không tái dùng được.

**Root cause.** Chưa từng có tầng template cho admin. `/developers` có
(`01` §6), admin thì không.

**Class.** NORMALIZE → Jinja + primitive dùng chung. **Regression risk: cao** —
đây là toàn bộ rủi ro của pha C, và là lý do prompt 07 bắt dừng nếu nền móng đỏ.

### B-02 · **P1** · Ba nguồn điều hướng, một trong đó viết tay

**FACT.** `01` §5: `_ADM_NAV`, `admin_api.NAV`, và 5 thẻ `<a>` hardcode trong
`server/admin_templates/sqladmin/base.html:54–59`.

**Operator impact.** Trang SQLAdmin có bộ điều hướng **khác** trang tự viết; đi
từ `/admin/user/list` sang `/admin/api-tong-quan` không có đường trực tiếp.

**Class.** MERGE về một authority. **Regression risk:** thấp.

### B-03 · **P1** · SQLAdmin nạp `ltt.css` không cache-bust

**FACT.** `sqladmin/base.html:22` `<link ... href="/static/ltt.css">` — không
`?v=`. Trang tự viết dùng `_asset_ver()` (`admin.py:161`).

**Operator impact.** Sau deploy đổi CSS, trang SQLAdmin hiển thị bằng bản cũ tới
hết TTL Cloudflare. Đây đúng là cái bẫy CLAUDE.md quy tắc 6 mô tả, và đã có tiền
lệ thật ở dự án này (chip hiện thành radio thô).

**Class.** NORMALIZE — 1 dòng. **Regression risk:** bằng 0.

### B-04 · **P2** · Hai hệ thiết kế cùng sống

**FACT.** Trang tự viết: `ltt.css`. SQLAdmin: Tabler + Bootstrap + FontAwesome +
select2 + flatpickr (`sqladmin/base.html:11–16`), nhuộm dark bằng ~30 dòng CSS đè
trong `<style>` inline.

**Class.** KEEP (prompt cấm bỏ SQLAdmin) + MOVE vào Advanced. Việc cần làm là
**ngữ cảnh** (cùng vỏ, cùng đường về), không phải thống nhất CSS.

### B-05 · **P2** · Vỏ admin thiếu ba thứ mà mọi trang đều cần

**FACT.** `_admin_shell(title, active, body)` chỉ có sidebar + mobilebar. Không có:
topbar, page header (mỗi trang tự viết `<div class="pagehead">`), breadcrumb,
subnav, vùng hành động của trang, khối flash success/error.

**Operator impact.** Không biết mình đang ở nhánh nào của cây; không có đường
"quay lại" ngoài nút back của trình duyệt.

**Class.** NORMALIZE.

---

## C. Domain boundary

### C-01 · **P1** · Truy vấn ORM thô nằm thẳng trong view

**FACT.** `ChiTietNguoiDungView.chi_tiet` (`admin.py:248–251`) gọi
`db.query(Job).filter(...).order_by(...).limit(20).all()`,
`db.query(PaymentOrder)...`, `db.query(PhienDb)...`, `db.query(CreditEntry)...`
trực tiếp trong handler HTTP.

**Root cause.** Không có read-model/service cho "toàn cảnh một khách hàng".

**Architecture impact.** Customer 360 (prompt 10) sẽ cần đúng bộ truy vấn đó cộng
thêm. Nếu tiếp tục viết trong view thì trang mới lại là một khối 200 dòng nữa.

**Class.** NORMALIZE — rút thành một read-model. **Nhưng:** giữ diff nhỏ nhất
(prompt 00 §5). Chỉ rút phần **có ≥ 2 call-site thật**, không tạo abstraction
một-call-site.

### C-02 · **P2** · `admin_api.py` là adapter, và phần lớn giữ đúng vai

**FACT.** Nghiệp vụ Public API nằm ở `platform_core/public_api/*`
(`policy.py:428` kiểm `reason`; `pricing.py` giữ lifecycle). `admin_api.py` gọi
vào đó. Đây là ranh giới **đúng** — không phải finding tiêu cực.

**Class.** KEEP. Ghi lại để pha C không phá.

### C-03 · **P2** · Không có phụ thuộc vòng, nhưng có một phụ thuộc ngược chiều

**FACT.** `server/admin.py:101` `from server.admin_api import NAV as _NAV_API` —
tệp "nền" import danh sách nav từ tệp "miền". Nó hoạt động, và bình luận
`:118–120` giải thích có chủ ý (tránh bản sao thứ hai của cùng danh sách).

**Class.** NORMALIZE — thay bằng registry để chiều phụ thuộc là miền → registry.

---

## D. Extension locality

Mô phỏng theo yêu cầu prompt 02 §4.

| Kịch bản | Tệp trung tâm phải sửa hôm nay |
|---|---|
| Thêm một trang Tài chính | ① class trong `server/admin.py` ② dòng ở `_ADM_NAV` (`:103`) ③ `admin.add_view()` (`:1364`) → **3 chỗ, 2 trong đó là danh sách trung tâm** |
| Thêm một trang API Operations | ① class trong `admin_api.py` ② `VIEWS` (`:1875`) ③ `NAV` (`:1883`) → **3 chỗ** |
| Thêm một thao tác Provider | ① class/route ② `_ADM_NAV` nếu muốn thấy ③ `add_view` → **3 chỗ** |
| Thêm một mục vào thanh SQLAdmin | sửa **tay** `sqladmin/base.html:54–59` → **chỗ thứ 4, không ai nhớ** |

**Kết luận D.** Không có cơ chế nào ngăn danh sách phình; không có trần; không có
test chốt. Đối chiếu: `/developers` có `SECTIONS` là nguồn duy nhất và `test_303`
chốt trần 12 mục.

**Class.** NORMALIZE theo khuôn `/developers`. **Regression risk:** thấp.

---

## E. Golden Journeys — đi bằng route thật hôm nay

| GJ | Đường đi hiện có | Đứt ở đâu |
|---|---|---|
| **GJ1** hỗ trợ khách | `/admin/nguoi-dung?q=email` → có số dư, 15 bút toán, 20 job, 10 đơn, **số** phiên | ⛔ không có hành động nào ngoài link "Cấp credit"; **không thu hồi được phiên** (phải sang `/admin/session/list` lọc bằng UUID); không có ngữ cảnh API; không có nhật ký admin của khách đó |
| **GJ2** sửa tiền | `/admin/grant-credit` (form riêng) | ⛔ **bắt đầu từ hành động, không từ khách**. Không vào được từ trang khách kèm sẵn đối tượng |
| **GJ3** job hỏng | `/admin/job/list` (bảng thô SQLAdmin) | ⛔ không lọc theo trạng thái lỗi ở nav; từ job **không** sang được khách/app/provider; không có đường từ Tổng quan |
| **GJ4** sự cố API | `/admin/api-tong-quan` → tự chọn trong 11 mục còn lại | ⛔ `api-request` → `api-job` → `api-trace` là ba trang rời; không có deep-link giữa chúng theo `request_id` |
| **GJ5** lỗi thanh toán | `/admin/don` → `POST /don/action` mark-paid | ⚠️ chạy được. Thiếu: đường từ đơn → khách, đơn → bút toán credit sinh ra |
| **GJ6** sức khoẻ nền tảng | **không có trang Tổng quan** | ⛔ `_ADM_NAV` mục đầu là `/` (trang chủ nền tảng), mục "Hệ thống" trỏ `/status`. **Không tồn tại `/admin/` overview** |

⭐ **GJ6 không có điểm bắt đầu.** Đây là lý do prompt 08 tồn tại, và là lý do kế
hoạch xếp Admin Overview làm **cuối** — nó chỉ có nghĩa khi 9 đích deep-link đã có.

---

## F. Safety UX — rủi ro thao tác nhầm

| Hành động | Route | Hiện có | Rủi ro |
|---|---|---|---|
| Cấp credit | `/grant-credit` | CSRF ✅ audit ✅ | **P2** — không có xác nhận số tiền lớn; form đứng độc lập nên dễ nhập nhầm người |
| Mark-paid | `/don/action` | CSRF ✅ idempotent ✅ audit ❌ | **P2** — không nhật ký admin; không nhãn "đây là đường dự phòng" |
| Bật/tắt/xoá gói nạp | `/goi/action` | CSRF ✅ audit ❌ | **P2** — ảnh hưởng giá bán |
| Đổi vai trò / vô hiệu hoá tài khoản | SQLAdmin `user/edit` | CSRF (sqladmin) ✅ audit ✅ (`on_model_change:389`) | **P2** — nằm trong form sửa chung, không tách theo mức nguy hiểm |
| Thu hồi phiên | SQLAdmin `session/delete` | audit ❌ | **P2** — thao tác an ninh thực hiện bằng nút "xoá dòng" của bảng thô |
| Provider key reset/rotate/disable | `/api-key-action` | CSRF ✅ audit ❌ | **P1** — hạ tầng dùng chung, không dấu vết |
| Revoke khoá API của khách | `/api-khoa-action` | CSRF ✅ audit ✅ | ✅ |
| Publish/retire giá API | `/api-gia-action` | CSRF ✅ audit ✅ | ✅ |
| Kill switch | `/api-kill-switch-action` | CSRF ✅ audit ✅ **reason bắt buộc ở service** | ✅ — **và phải giữ nguyên** |

**F-tổng.** CSRF **11/11**. Audit **5/11**. Bất biến kill-switch và secret đều
đúng. Rủi ro lớn nhất **không** phải thiếu kiểm soát mà là **thiếu ngữ cảnh**:
hành động nguy hiểm được thực hiện ở một trang không hiển thị đối tượng bị tác động.

---

## G. Xếp hạng — thứ tự phải sửa

| Hạng | Finding | Vì sao |
|---|---|---|
| 1 | **B-01** f-string HTML | chặn mọi thứ khác; là nền móng C0 |
| 2 | **A-01 + B-02 + D** nav 25 mục / 3 nguồn / không trần | là toàn bộ "bố cục lại danh mục" mà chủ sản phẩm yêu cầu |
| 3 | **E** sáu Golden Journey đứt ở 5/6 | giá trị vận hành thật |
| 4 | **A-02 + F** hành động thiếu ngữ cảnh | an toàn |
| 5 | **B-03** cache-bust SQLAdmin | 1 dòng, P1, làm luôn ở C0 |
| 6 | **E-03/audit 6 POST** | ghi nhận, đề xuất; xem `24_DEFERRED` |

---

## H. Ba điều KHÔNG được kết luận từ audit này

1. **Không** kết luận "SQLAdmin là nợ kỹ thuật cần gỡ". Nó là công cụ dữ liệu thô
   có giá trị thật (`01` §4) và prompt cấm bỏ.
2. **Không** kết luận "admin_api.py cần tách nhỏ vì nó dài". Nó dài vì chứa HTML
   (B-01), không vì nghiệp vụ sai chỗ (C-02). Sửa B-01 thì độ dài tự giảm.
3. **Không** kết luận "cần hệ thiết kế mới". Token đã đủ và đã dùng chung
   (`01` §7). Việc cần làm là **cấu trúc**, không phải bảng màu.

---

**STOP.** Bước tiếp: `03_IA_FREEZE.md`.
