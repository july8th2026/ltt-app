# 24 — Hoãn sau MVP

Việc **cố ý** không làm trong đợt `admin_mvp_v3`, kèm lý do và điều kiện mở lại.
Danh sách này là một phần của kết quả, không phải phần thiếu của nó.

---

## A. Chuyển thân bốn miền API sang Jinja (C5–C8)

**Trạng thái:** hoãn · ưu tiên **thấp hơn trước**

⭐ Cập nhật sau lô C5–C8 (`09_LO_C5_C8.md`): giá trị vận hành của khu API — hết
năm ngõ cụt, 13 ô chỉ số bấm được, mọi liên kết mang bộ lọc đặt sẵn — **đã lấy
được mà không cần viết lại thân**. Nên lý do hoãn nay mạnh hơn lúc đầu.

`server/admin_api.py` còn ~1.880 dòng HTML dựng bằng f-string cho 16 trang API.

**Vì sao hoãn, không phải bỏ quên.** Hợp đồng P6–P8 đòi ba thứ, và **cả ba đã
đạt** sau C0:
- IA đúng: 12 mục ngang cấp → 1 mục cha + 5 mục con + tab cấp ba, 0 route mất;
- không nội dung bịa: các trang này vốn đã trung thực (chính `admin_console.py`
  ghi rõ nhật ký chỉ lưu lời gọi hỏng, nên trang không hứa "tổng request");
- giữ ngữ nghĩa kill switch: form có ô lý do bắt buộc, không thành toggle.

Viết lại thân là **polish trình bày**. Prompt 00 §5: giữ diff nhỏ nhất đáp ứng
hợp đồng.

**Mở lại khi:** một trang API cần khối UI mới mà f-string không dựng nổi, hoặc
khi có người sửa cùng lúc ≥ 2 trang trong đó.

---

## B. Ô tìm liên thực thể (omnibox)

**Trạng thái:** hoãn · cần backend

Ảnh mockup vẽ ô "Tìm người dùng, đơn hàng, log…". Không có backend nào tìm liên
thực thể. Ô hiện tại nói **đúng phạm vi của nó**: *"Tìm khách hàng — email hoặc
User ID"*.

⛔ Không làm ô nhận cả đơn hàng/log rồi trả rỗng. Một ô hứa nhiều hơn nó làm được
là một lỗi vận hành, không phải một thiếu sót thẩm mỹ.

**Mở lại khi:** có một read-model tìm kiếm hợp nhất (khách + đơn + request id +
job id) trả về kết quả có phân loại.

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

**Trạng thái:** hoãn

Ảnh mockup có "« Thu gọn" ở đáy thanh bên. Nó thêm một trạng thái phải nhớ
(localStorage) và một biến thể bố cục phải kiểm ở cả 6 viewport. Không thuộc MVP.

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

**Trạng thái:** nợ có chủ ý · gỡ khi C5–C8 xong

`server/admin.py:_KHOA_CU` dịch khoá `active` cũ (`"revenue"`, `"chitiet"`,
`"api_pricing"`, …) sang khoá mới của `SECTIONS`. Nó tồn tại để đổi vỏ mà không
phải sửa 29 chỗ gọi trong cùng một lô.

**Gỡ khi:** trang cuối cùng chuyển sang khoá mới. Đừng thêm dòng vào nó — trang
mới khai thẳng khoá mới ở `SECTIONS`.

---

## H. Nhật ký admin: tra theo đối tượng còn lỏng

**Trạng thái:** đã ghi nhận

`NhatKyAdmin.doi_tuong` là chuỗi tự do, nên các đường ghi khác nhau dùng khác
nhau — chỗ ghi `user_id`, chỗ ghi `email`, chỗ ghi `order_code`.
`admin_console.ho_so_khach()` phải tra **cả hai** (id và email) để không bỏ sót
một nửa dấu vết.

**Mở lại khi:** cần lọc nhật ký theo thực thể ở quy mô lớn. Khi đó thêm cột
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

**Trạng thái:** đề xuất · cần chủ sản phẩm chốt

`platform_core/public_api/admin_console.overview()` đếm job **toàn nền tảng** —
không lọc `_api` — trong khi mọi số khác trên cùng bảng điều khiển (khoá,
project, request, credit) đều là của API. Hai phạm vi trong một trang.

Lô C5–C8 xử lý bằng cách **nói ra**: ô ghi nhãn phụ "toàn nền tảng" và dẫn sang
bảng job của nền tảng. Trung thực, nhưng vẫn hơi lạ trên một trang tên là
"API — Tổng quan".

**Sửa đúng** là thêm điều kiện `params._api.tool IS NOT NULL` vào hai truy vấn
job trong `overview()`. Nó đổi một read-model đang có test, và nó đổi ý nghĩa
của một con số chủ sản phẩm có thể đang theo dõi — nên nó là một quyết định, không
phải một lần sửa lỗi.
