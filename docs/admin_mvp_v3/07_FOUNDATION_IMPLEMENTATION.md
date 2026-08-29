# 07 — Nền móng (C0): vỏ dùng chung + bố cục lại danh mục

MODE: IMPLEMENTATION — FOUNDATION ONLY. Prerequisites: `01`–`06b`.

Đây là lô đổi **vỏ và điều hướng cho toàn bộ 31 route cùng lúc**. Thân trang
chưa chuyển sang template — đó là việc của C1–C10, và tách hai thứ đó ra là có
chủ ý: đổi vỏ và đổi thân là hai rủi ro khác nhau, trộn vào một lô thì một lần
đỏ không chỉ ra được nguyên nhân nào.

---

## 1. Kết quả đo được

| | Trước | Sau |
|---|---|---|
| Mục thanh bên (trang tự viết) | **25** phẳng + 4 dòng nhóm | **6** mục cha + ≤5 mục con + tab cấp ba |
| Mục thanh bên (trang SQLAdmin) | **31** (mọi view đã đăng ký) | **8** bảng thô |
| Nguồn khai điều hướng | **4** | **1** |
| Mục "API — …" ngang cấp | 12 (48% thanh bên) | 1 mục cha + 5 mục con |
| Trang hành động ở primary nav | 2 (`grant-credit`, `api-kill-switch`) | 0 |
| Route bị xoá | – | **0** |
| URL bị đổi | – | **0** |
| Redirect thêm vào | – | **0** |
| Bề rộng nội dung | 1.180px | 1.600px |
| `<h1>` mỗi trang | 1 | 1 |
| `aria-current="page"` mỗi trang | 1 | 1 |
| Tràn ngang ở 390px | 1 trang (`api-kill-switch`, body 473px) | **0** |

---

## 2. Bốn nguồn điều hướng — và nguồn thứ tư không có trong kế hoạch

`01` §5 tìm ra ba. Trình duyệt tìm ra cái thứ tư:

| # | Nơi khai | Nội dung | Xử lý |
|---|---|---|---|
| 1 | `server/admin.py:_ADM_NAV` | 13 mục + 4 nhóm | **gỡ** |
| 2 | `server/admin_api.py:NAV` | 12 mục `API — …` | **gỡ** |
| 3 | `sqladmin/base.html` 5 thẻ `<a>` viết tay | thanh nhanh | **thay** bằng `adm_nav` bơm từ nguồn chung |
| 4 | 🔴 **thanh bên riêng của SQLAdmin** | tự dựng từ danh sách view đã đăng ký — **cả 31 mục** | **thay** bằng `is_visible = False` cho trang nghiệp vụ |

⭐ Nguồn ④ chỉ lộ ra khi mở `/admin/user/list` bằng mắt. Đọc mã không thấy nó,
vì nó không phải một danh sách trong kho — nó là hệ quả của `admin.add_view()`.
Đây đúng là lý do CLAUDE.md quy tắc 5 tồn tại.

`is_visible` chỉ ẩn khỏi **menu**; route vẫn sống. Bảng thô (`ModelView`) **giữ
nguyên** trong menu đó — thanh bên của SQLAdmin **chính là** khu Data Explorer,
và tám tên bảng ở đó là nội dung đúng của nó.

---

## 3. Tệp đã đổi

| Tệp | Việc |
|---|---|
| `server/routes/admin/_chung.py` | **mới** — `SECTIONS` (27 khoá) · `NHOM_NAV` · `CHA_CUA` · `MUC_CON` · `TAB_CUA` · `dieu_huong()` · `AnTrongMenuSqlAdmin` |
| `server/routes/admin/__init__.py` | **mới** |
| `server/templates/admin/_vo.html` | **mới** — vỏ Jinja duy nhất |
| `server/admin.py` | gỡ `_ADM_NAV`; `_admin_shell` render template; thêm `_AdminLTT` (ghi đè `/admin/`); 10 `BaseView` nhận mixin ẩn menu; gỡ dải `.adm-top` thừa; đổi nhãn `APIKEYS` → `Provider Credentials` |
| `server/admin_api.py` | gỡ `NAV`; 12 `BaseView` nhận mixin; gỡ **14** dải `.adm-top` thừa |
| `server/admin_templates/sqladmin/base.html` | cache-bust `?v={{ asset_ver }}`; điều hướng lấy từ nguồn chung |
| `server/static/ltt.css` | `.adm-content` 1180→1600px; thêm `.adm-chrome` · `.adm-banhmi` · `.adm-dau` · `.adm-timkiem` · `.adm-mien-luoi`; chốt chống tràn ngang |
| `tests/test_317_admin_nav_contract.py` | **mới** — 37 phép kiểm |
| `tests/test_205_admin_api_console.py` | test điều hướng viết lại **chặt hơn** (§5) |
| `tests/test_124_admin_ui.py` | chốt cache-bust (§5) |

---

## 4. Ba quyết định kỹ thuật, và vì sao không chọn phương án khác

### 4a. Vỏ độc lập, không `extends "base.html"`

Khu quản trị là app-shell tràn viền; `base.html` thêm header nền tảng + `.page`
giới hạn bề rộng. Và trang SQLAdmin **không** đi qua `base.html` được — nếu vỏ
tự viết đi qua thì hai nửa khu quản trị lệch nhau thêm một tầng nữa.

Nhưng **kiểu thì dùng chung**: `.dev-sub` (dải mục con), `.card`, `.btn`,
`.dev-tt` đều dùng lại được vì cả hai nhóm lớp đọc **cùng một bộ token** —
`ltt.css:6–33` khai alias `--bg → --surface-canvas`, `--fg → --text-primary`, …
Không có token mới nào trong lô này.

### 4b. Nới `.adm-content` trực tiếp, không thêm cơ chế `page_mode`

`grep` chứng minh `.adm-*` **chỉ** `server/admin.py` và `server/admin_api.py`
dùng — không app nào, không `/developers`, không `/vps`. Nên đây là thao tác cô
lập. Thêm một cơ chế `page_mode` cho admin sẽ là abstraction một-call-site, đúng
thứ non-negotiable của prompt 00 cấm.

`.app-side` (210px, dùng chung `/developers` + `/vps`) **không bị đụng**.

### 4c. Chrome đứng ngoài thân trang

Thân của 29 trang chưa chuyển vẫn tự mang `<div class="adm-content">`, và chúng
**không cùng hình dạng** — một số bắt đầu bằng `</div><div class="adm-content">`.
Bóc vỏ của chúng bằng chuỗi là một phép đoán, không phải một phép biến đổi. Nên
vỏ phát một khối `.adm-chrome` riêng, và `.adm-chrome + .adm-content{padding-top:0}`
gộp hai khối thành một nhịp dọc.

Hệ quả: `_admin_shell(title, active, body)` **giữ nguyên chữ ký ba tham số**, 29
chỗ gọi không phải sửa. Bảng `_KHOA_CU` dịch khoá cũ (`"revenue"`, `"chitiet"`,
`"api_pricing"`, …) sang khoá mới. Bảng đó là **cầu tạm**: khi trang cuối cùng
chuyển xong thì xoá nó.

---

## 5. Hai test đã sửa — và vì sao đó không phải làm yếu test

Non-negotiable của prompt 00: *"Không xoá hoặc làm yếu test để chiều markup/
navigation mới."* Cả hai lần sửa đều **chặt hơn** bản cũ.

### `test_205::test_the_admin_navigation_links_the_api_section`

Bản cũ: mọi trang API phải xuất hiện dưới dạng `href` **trên trang tổng quan**.
Nó mô tả một thanh bên phẳng, không mô tả một lời hứa.

Bản mới chốt lời hứa thật, và chốt nhiều hơn:
1. **cả 12 URL vẫn trả 200** — bản cũ chưa bao giờ kiểm điều này, mà đây mới là
   thứ một dấu trang phụ thuộc;
2. mọi trang điều hướng tới được trong **≤ 2 bước** từ tổng quan;
3. đúng **một** `aria-current="page"` mỗi trang.

`/admin/api-trace` được loại khỏi phép kiểm (2) **theo hợp đồng**: trace là trace
**của một cái gì đó**, chỉ được liên kết từ một dòng request/job/security dưới
dạng `?q=<id>`. Đưa nó lên thanh bên để qua được test là đặt ở đó một trang trả
lời câu "trace của cái gì?" bằng một ô tìm rỗng — đúng khiếm khuyết mà
`test_a_customer_link_from_the_key_page_lands_on_a_real_profile` được viết ra để
bắt. Thay vào đó (2b) kiểm nó sống sót khi mở bằng một id không còn tồn tại.

### `test_124::test_sqladmin_uses_shared_carbon_red_tokens`

Bản cũ chốt `href="/static/ltt.css"` — tức nó **chốt đúng trường hợp sai**.
Trang SQLAdmin nạp CSS không kèm phiên bản, nên sau mỗi lần đổi `ltt.css` nó
phục vụ bản cũ từ Cloudflare tới hết TTL trong khi trang tự viết đã đổi. Bản mới
đòi `href="/static/ltt.css?v=`.

---

## 6. Cổng nghiệm thu C0

Prompt 07 đòi render ít nhất bốn loại trang. Đã kiểm **12 trang** trên trình
duyệt thật (SQLite nháp trong scratchpad — **không** dùng dữ liệu production).

| Kiểm | Kết quả |
|---|---|
| Vỏ dùng chung trên trang tự viết | ✅ 11/11 có `.adm-side` mới |
| Vỏ dùng chung trên trang SQLAdmin | ✅ thanh trên lấy từ nguồn chung; thanh bên còn 8 bảng thô |
| Trạng thái nav đúng ba cấp | ✅ `/admin/api-kill-switch` → thanh bên **API Platform**, mục con **Governance**, tab **Kill switch**, bánh mì `API Platform / Kill switch` |
| Không hồi quy route | ✅ 12/12 trang trả 200 |
| Không tràn ngang | ✅ 12/12 ở 390px (trước: 1 trang tràn) |
| Console JS lỗi | ✅ không có |
| `<h1>` mỗi trang | ✅ đúng 1 |
| `aria-current="page"` | ✅ đúng 1 |
| Viewport đã soi | 1920 · 768 · 390 |

**Hai lỗi tìm được bằng trình duyệt mà mã và test đều không thấy:**
1. thanh bên riêng của SQLAdmin (§2 ④);
2. `.adm-top` thứ hai do **15 trang** tự vẽ trong thân — hai thanh dính cùng lớp
   chồng lên nhau khi cuộn, và một `<input size=…>` trong đó đẩy **body** rộng
   473px ở khung 390 (không phải chỉ bảng bị tràn — cả trang cuộn ngang).

Chốt chống tràn đặt ở **gốc dùng chung** (`.adm-content input,select,textarea
{max-width:100%}`) thay vì đi sửa từng thẻ input trong 173 KB f-string.

---

## 7. Việc C0 cố ý KHÔNG làm

- **Không** chuyển thân trang sang template — C1–C10.
- **Không** dựng hàng đợi chú ý ở `/admin/`. Trang Tổng quan hiện chỉ có điều
  hướng, **không một ô chỉ số nào**: hợp đồng P1 thuộc lô C10, và một ô số không
  có read-model đứng sau là đúng thứ `06b` cấm.
- **Không** thêm audit cho 6 POST còn thiếu (`01` E-03) — `05` Phần III chốt việc
  đó là PROPOSAL, thuộc `24_DEFERRED_POST_MVP.md`.
- **Không** đụng `.app-side`, `/developers`, `/vps`.

---

## 8. Điểm cần biết cho lô sau

1. Trang chuyển sang template thì truyền `tieu_de`/`mo_ta`/`hanh_dong` cho
   `_admin_shell` và **bỏ `.pagehead` trong thân** — nếu không sẽ có hai H1.
2. Thêm trang mới = **2 chỗ, cùng một tệp miền**: class view + dòng ở
   `SECTIONS`/`MUC_CON`. Sửa tệp trung tâm: **0**.
3. Khoá mới khai thẳng ở `SECTIONS`; **đừng** thêm dòng vào `_KHOA_CU`.
4. `/admin/khach-hang` (C1) và `/admin/he-thong` + `/admin/nang-cao` (C9) sẽ
   nhận lại vai mục cha từ `ho_so_360` và `nhat_ky` — đổi ở `SECTIONS` +
   `NHOM_NAV` + `CHA_CUA`, không đổi URL nào.
