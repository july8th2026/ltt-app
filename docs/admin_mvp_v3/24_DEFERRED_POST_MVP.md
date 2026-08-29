# 24 — Hoãn sau MVP

Việc **cố ý** không làm trong đợt `admin_mvp_v3`, kèm lý do và điều kiện mở lại.
Danh sách này là một phần của kết quả, không phải phần thiếu của nó.

---

## A. Chuyển thân 12 trang API sang Jinja (C5–C8)

**Trạng thái:** ✅ **XONG 2026-08-29** — `server/admin_api.py` **1.894 → 846 dòng**.

⭐ **Điều kiện mở lại đã tự chạm, và nó chạm từ trước khi mục này được viết.**
Bản hoãn ghi: *"mở lại khi… có người sửa cùng lúc ≥ 2 trang trong đó"*. Lô C5–C8
sửa **mười hai** trang — thêm liên kết sâu, thêm bộ lọc đặt sẵn, sửa nhãn. Nên
câu "giữ diff nhỏ nhất" không còn đúng với thực tế: diff đã không nhỏ.

**Đã làm gì.** Mười hai thân trang thành mười bốn template dưới
`server/templates/admin/`, cộng `_macro_api.html` giữ tám thứ dùng chung. Tám
hàm/hằng sinh HTML bằng chuỗi (`_stat`, `_pager`, `_mode_chip`, `_key_badge`,
`_error_note`, `_reason_form`, `_TILES`, `_COLS`) và `_trace_body` đã **gỡ hẳn**
— để lại là để dành sẵn một đường quay về nối chuỗi.

🔴 **Cái giá phải trả, đo được, và đã trả:** một bẫy Jinja làm sai **ba** trang
mà **không** trang nào trả khác 200.

`x.keys` được Jinja giải bằng `getattr` **trước** rồi mới `getitem`. Cả
`accounts_page()` lẫn `account_detail()` đều trả dict có khoá `keys`, nên
`x.keys` cho ra `<built-in method keys of dict>`. Trang tổng quan in một chuỗi
rác ở ô "Khoá live đang chạy"; trang chi tiết tài khoản thì `|length` trên method
→ **500**. Không phép kiểm chức năng nào thấy điều đó.

⇒ Đã chốt bằng `test_323::test_khong_trang_nao_ro_ri_phuong_thuc_cua_dict` (12
trang) + `test_moi_trang_api_render_duoc`. Cùng bẫy áp cho `items`, `values`,
`get`, `copy`, `pop`.

⭐ Và bánh cóc **nội dung cấm** bắt thêm hai chữ **có sẵn từ bản f-string**, chỉ
lộ ra khi thân trang thành template (bộ quét chỉ soi `server/templates/admin`):
- *"con số đã **đối soát**"* ở trang Margin — hứa một luồng đối soát **ngân
  hàng** không tồn tại. Sửa thành "đã **quyết toán**", đúng tên bước thật trong
  sổ credit.
- *"**Địa chỉ**"* làm tiêu đề cột IP ở hai trang — chữ này bị cấm vì nền tảng
  không có trường địa chỉ của khách. Đổi thành **"IP"**: vừa hết mơ hồ, vừa
  không chạm hàng rào.

⚠️ Đây là một lập luận **cho** việc chuyển sang template, không phải chống: hai
lỗi chữ đó sống trong `admin_api.py` suốt thời gian nó là f-string vì **không bộ
quét nào soi tới mã Python**.

---

## B. Ô tìm liên thực thể (omnibox)

**Trạng thái:** ✅ **XONG 2026-08-29** — `admin_console.tim_lien_thuc_the()` +
`/admin/tim`.

⭐ **Mục này được mở đúng bằng điều kiện chính nó đặt ra.** Bản hoãn viết: *"mở
lại khi có một read-model tìm kiếm hợp nhất (khách + đơn + request id + job id)
trả về kết quả có phân loại"*. Đó chính là thứ được viết, nên đây không phải một
lần đổi ý — nó là điều kiện đã đạt.

**Năm loại, mỗi loại chỉ ra được một bảng thật:**

| Loại | Bảng | Tra bằng |
|---|---|---|
| Khách hàng | `users` | email chứa · User ID chính xác |
| Đơn nạp | `payment_orders` | `order_code` (số) |
| Job | `jobs` | id hoặc **tiền tố** |
| Lời gọi API | `public_api_requests` | `request_id` hoặc tiền tố |
| Khoá của khách | `developer_api_keys` | `key_id` hoặc tiền tố |

Nhãn của ô liệt kê **đúng** năm thứ đó. `test_327::test_nhan_o_tim_va_read_model_khong_tach_nhau`
đọc cả nhãn lẫn nguồn read-model và bắt lỗi nếu chúng lệch — tức luật *"không
hứa nhiều hơn nó làm được"* nay là một phép kiểm, không phải một dòng văn xuôi.

⭐ **Tiền tố job/request/khoá được cho phép có lý do:** UUID hiện ra dưới dạng
**cắt** ở khắp khu quản trị (`job.id[:12]`), nên thứ người ta chép được từ màn
hình là một tiền tố. Bắt họ tìm bằng chuỗi đầy đủ là bắt họ tìm bằng thứ giao
diện không cho.

⛔ **Không có tìm toàn văn**, và đó là một chốt: không `LIKE %q%` trên
`jobs.params`, không tra `nhat_ky_admin.chi_tiet`. Cả hai là quét toàn bảng trên
bảng lớn nhất hệ thống, và người gõ vào ô này **đang có sự cố** — một truy vấn
30 giây ở đúng lúc đó tệ hơn là không có ô tìm. `test_khong_tim_toan_van` đọc
chính nguồn, vì ràng buộc hiệu năng **không lộ ra ở hành vi** cho tới khi bảng
đủ lớn.

🔴 **Một lỗi 500 thật đã bị bắt trong lúc làm.** `payment_orders.order_code` là
`BigInteger`. Chuỗi `"9"×40` vẫn qua `.isdigit()`, và `int()` **thành công** vì
Python có số lớn — nhưng cột thì không: SQLite ném `OverflowError`, PostgreSQL
ném `NumericValueOutOfRange`. Tức gõ nhầm một chuỗi số dài vào ô tìm làm đổ
trang. Nay chặn ở `_TRAN_BIGINT` **trước khi** chạm CSDL;
`test_so_qua_lon_khong_lam_do_trang` giữ nó.

⭐ Một kết quả duy nhất thì **đi thẳng** (303) tới thực thể đó. Bắt người đang xử
sự cố bấm thêm một lần vào một danh sách có đúng một dòng là một bước thừa ở
đúng lúc họ không có thời gian.

⚠️ Đã dựng lớp CSS **riêng** (`.adm-timkq`) thay vì dùng lại `.adm-hangdoi`: hàng
đợi chú ý là lưới **ba** cột cho một cấu trúc ba mảnh, dòng kết quả tìm chỉ có
hai — đo bằng trình duyệt thấy cột thứ ba nhận phần còn lại và chữ tràn ra ngoài
thẻ. Kèm `minmax(0,1fr)` + `overflow-wrap` để một email 45 ký tự không làm vỡ bố
cục.

---

## C. Trang danh sách khách hàng: sắp xếp theo cột

**Trạng thái:** ✅ **XONG** — bốn cách sắp (`SAP_XEP` trong
`platform_core/admin_console.py`): mới nhất · cũ nhất · đăng nhập cuối · email.

Ba chốt kèm theo, đều có test (`test_318`):
- **danh sách trắng**, không nhận tên cột tuỳ ý từ URL — đó là một đường ghép
  chuỗi vào câu truy vấn;
- đổi thứ tự **giữ nguyên bộ lọc** — mất bộ lọc là làm mất chỗ người ta đang đứng;
- chỉ cột **thật sự** sắp được mới có liên kết ở tiêu đề; một mũi tên trên mọi
  cột rồi ba trong số đó không làm gì là một lời hứa rỗng.

⛔ **"Số dư" cố ý KHÔNG sắp được, và đó là một chốt.** Nó là tổng của sổ
append-only, nên sắp theo nó cần một phép gộp trên toàn bảng `credit_entries`
rồi mới phân trang được — một lượt quét toàn bảng cho mỗi lần đổi trang. Muốn có
thì phải có cột tổng được duy trì hoặc một view, không phải thêm một dòng vào
`SAP_XEP`. `test_so_du_khong_sap_xep_duoc_va_do_la_mot_chot` giữ điều này.

---

## D. Nút thu gọn thanh bên

**Trạng thái:** ✅ **XONG 2026-08-29** — 236px → 64px, nhớ bằng `localStorage`.

Bản hoãn lo hai thứ, và cả hai đã được xử chứ không bị bỏ qua:

1. **"một trạng thái phải nhớ".** Trạng thái đặt trên `<html data-adm-side>`
   bởi một `<script>` trong `<head>` — **trước** khi vẽ. Đọc `localStorage` ở
   cuối `<body>` thì trình duyệt đã vẽ thanh bên rộng rồi mới thu lại: một cú
   giật ở **mọi** lần tải trang, khó chịu hơn hẳn cái tiện mà nút này mang lại.
   `test_trang_thai_thanh_ben_dat_truoc_khi_ve` chốt vị trí đó.
   ⚠️ Cả hai lần chạm `localStorage` đều bọc `try/catch`: nó **ném** chứ không
   trả rỗng khi trình duyệt chặn site data, và một ngoại lệ trong `<head>` làm
   hỏng cả vỏ.

2. **"một biến thể bố cục phải kiểm ở cả 6 viewport".** Không có biến thể thứ
   ba: dưới 820px `.adm-side` vốn đã `display:none`, nên nút cũng
   `display:none` ở đó. Đo bằng trình duyệt 375px — nút biến mất, điều hướng
   vẫn đi qua `<details>` của thanh mobile.

Toàn bộ hình dạng ở `ltt.css` dưới `[data-adm-side="hep"]`; JS chỉ đổi một
thuộc tính. Tắt JS thì thanh bên đơn giản là luôn rộng, không vỡ.

---

## E. Đo trên URL công khai `https://app.lttstudios.com`

**Trạng thái:** ✅ **ĐÃ DEPLOY + ĐÃ ĐO 2026-08-29** — xem
`25_DEPLOY_VA_KIEM_URL_CONG_KHAI.md`.

Cái bẫy lịch sử đã đóng: `ASSET_VER` khớp hai đầu (`8aae308b`),
`cf-cache-status: MISS`, 8/8 lớp CSS mới có trong bản Cloudflare phục vụ. HTML
`no-store`/`DYNAMIC` nên không bị cache.

⚠️ **Còn một nửa chưa đóng:** giao diện admin **đã đăng nhập** với dữ liệu
production. Cloudflare chặn trình duyệt tự động ở `/login` (403 + thử thách bot)
và tôi không giải CAPTCHA, không nhập mật khẩu. Rủi ro còn lại là rủi ro **dữ
liệu**, không phải rủi ro mã — 30 trang đã soi ở 6 viewport trên bản dựng giống
hệt. Xem `25` §5.

---

### (ghi chú lịch sử của mục này)

CLAUDE.md quy tắc 5b: loopback **bỏ qua** Cloudflare (cache, CSP biên, minify).
Dự án này đã dính một lần: sau khi sửa `ltt.css`, CF phục vụ bản CSS **cũ** (TTL
4h) → chip hiện thành radio thô, dù origin đã đúng.

Đợt này có đổi `ltt.css` (nhiều lớp mới) ⇒ **phải** kiểm lại trên URL công khai
sau deploy. `asset_ver` đã lo cache-bust, và lỗi thiếu `?v=` ở vỏ SQLAdmin đã sửa
— nhưng "đã lo" không phải "đã đo".

---

## F. Kiểm bàn phím / focus

**Trạng thái:** ✅ **đã rà bằng máy trên 13 trang**

Đo trên DOM đã render, không phải đọc mã:

| Phép kiểm | Kết quả |
|---|---|
| `skip-link` | có ở **13/13** |
| `<h1>` mỗi trang | đúng 1 ở **13/13** |
| liên kết không có nhãn (không chữ, không `aria-label`, không icon) | **0** |
| nút không có nhãn | **0** |
| `tabindex` dương (phá thứ tự DOM) | **0** |
| bảng thiếu `<thead><th>` | **0** |
| ô nhập không có nhãn nào | **3 → 0** (đã sửa) |

Ba ô đã sửa: `<select name="scope">` ở Kill switch, `<select name="status">` và
`<input name="hours">` ở trang Request — cả ba nay có `aria-label`. `<select>`
không có `placeholder`, nên không nhãn thì trình đọc màn hình chỉ đọc ra giá trị
đang chọn: người dùng biết "24" nhưng không biết **24 cái gì**.

Còn lại: đi hết bằng Tab bằng tay để cảm nhận thứ tự (máy đã xác nhận thứ tự =
thứ tự DOM vì không có `tabindex` dương).

---

## G. Bảng `_KHOA_CU` — cầu tạm phải gỡ

**Trạng thái:** ✅ **ĐÃ GỠ 2026-08-29.**

Nó dịch khoá `active` cũ (`"revenue"`, `"chitiet"`, `"api_pricing"`, …) sang khoá
mới của `SECTIONS`, để đổi vỏ mà không phải sửa 29 chỗ gọi trong cùng một lô.
Mọi chỗ gọi nay khai thẳng khoá mới.

`test_317::test_bang_cau_tam_khong_quay_lai` giữ nó không quay lại: nó đọc chính
`server/admin.py` và bắt lỗi nếu `_KHOA_CU` xuất hiện lại ngoài dòng chú thích.

⛔ **Món nợ này trả được vì có hạn trả ghi sẵn.** Một cầu tạm không có dòng "gỡ
khi X" thì X không bao giờ tới.

---

## H. Nhật ký admin: tra theo đối tượng còn lỏng

**Trạng thái:** hoãn — **cố ý giữ hoãn ngày 29/08**, dù lượt này làm hết A/D/G/J.

`NhatKyAdmin.doi_tuong` là chuỗi tự do, nên các đường ghi khác nhau dùng khác
nhau — chỗ ghi `user_id`, chỗ ghi `email`, chỗ ghi `order_code`.
`admin_console.ho_so_khach()` phải tra **cả hai** (id và email) để không bỏ sót
một nửa dấu vết. Đã kiểm 29/08: nó vẫn tra cả hai, nên **không có dấu vết nào
đang bị mất**.

🔴 **Vì sao không làm nốt trong lượt này.** Sửa đúng là thêm cột
`doi_tuong_loai`, tức một **migration Alembic trên CSDL đang phục vụ khách trả
tiền**. Cái giá đó chỉ đáng trả khi có nhu cầu thật — và nhu cầu ("lọc nhật ký
theo thực thể ở quy mô lớn") **chưa xảy ra**. Bảng nhật ký hiện đủ nhỏ để tra
bằng hai điều kiện `OR`.

Chạy một migration cho một nhu cầu giả định thì rủi ro là thật còn lợi ích là
tưởng tượng. Đây là một mục **được quyết định giữ hoãn**, không phải một mục bị
bỏ sót.

**Mở lại khi:** thật sự cần lọc theo thực thể ở quy mô lớn. Khi đó thêm cột
`doi_tuong_loai` chứ đừng viết lại chuỗi cũ.

---

## I. Ảnh tham chiếu cho Admin Overview

**Trạng thái:** không cần nữa

Tệp ảnh trong bộ mockup hỏng (34 byte, `{"detail":"Internal Server Error"}`). Chủ
sản phẩm chốt: suy theo phong cách đang triển khai. Đã làm theo
`06_VISUAL_REFERENCE_CONTRACT.md` §1, và trang Tổng quan nay đã tồn tại và có
test.

Sinh lại ảnh **không còn giá trị** — nó sẽ là một mockup của một trang đã có
thật, và nếu nó vẽ khác thì ảnh sai chứ không phải trang sai.


---

## J. Thu hẹp `overview()["jobs"]` về đúng job của API

**Trạng thái:** ✅ **XONG 2026-08-29.**

`overview()` nay dùng **cùng** bộ lọc `_api` mà `jobs_page()` vẫn dùng
(`Job.params[(API_META_KEY,"tool")] IS NOT NULL`), nên con số và đích **khớp
nhau**. Nhãn phụ "toàn nền tảng" đã gỡ; đích của hai ô job trỏ về
`/admin/api-job` chứ không còn trỏ ra bảng job của nền tảng.

Xử tạm thời trước đó là **nói ra** — trung thực, nhưng vẫn là một bảng điều
khiển API báo một con số không phải của API, và bấm vào thì rơi vào một danh
sách **nhỏ hơn** con số vừa bấm.

`test_323::test_o_job_dem_dung_job_cua_API_va_dich_khop_con_so` chốt bằng **số**
chứ không bằng nhãn: fixture dựng đúng một job API `error`, ô phải hiện `1`, và
đích phải ra đúng một dòng.
