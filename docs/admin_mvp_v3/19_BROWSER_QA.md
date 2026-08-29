# 19 — Cổng trình duyệt

MODE: BROWSER RELEASE GATE.

⚠️ Prompt 19 nói: *"If browser unavailable: DO NOT claim visual PASS."* Trình
duyệt **có** — mọi con số dưới đây là đo thật, không suy luận.

---

## 1. Môi trường đo

| | |
|---|---|
| Máy chủ | uvicorn cục bộ, cổng 8124 |
| CSDL | **SQLite nháp trong scratchpad** — không dùng dữ liệu production (CLAUDE.md toàn cục cấm khi chưa được phép rõ ràng) |
| Trình duyệt | Browser pane, đo `document.body.scrollWidth` trong iframe cô lập ở từng bề rộng |
| Tài khoản | `qa@ltt.local`, role=admin, tạo trong CSDL nháp |

⚠️ **Chưa đo trên `https://app.lttstudios.com`.** CLAUDE.md quy tắc 5b đòi chốt
trên URL công khai vì Cloudflare có thể phục vụ CSS cũ. Việc đó thuộc **sau
deploy** và cần chủ sản phẩm — xem §5.

---

## 2. Phạm vi

**35 trang × 6 viewport = 210 phép kiểm tràn ngang.**

Viewport: 1920 · 1440 · 1280 · 1024 · 768 · 390.

Trang: 6 trang mới/đã viết lại · 16 trang API · 4 trang tài chính · 3 trang vận
hành · 2 trang hệ thống · 5 bảng thô SQLAdmin · 3 trạng thái đặc biệt (tìm không
ra, chưa nhập gì, lọc rỗng).

---

## 3. Kết quả

| Phép kiểm | Kết quả |
|---|---|
| Mã trạng thái HTTP đúng | **35/35** (gồm 404 đúng chỗ cho khách không tồn tại) |
| Tràn ngang `body` | **0/210** |
| `<h1>` mỗi trang | ≤ 1 trên **35/35** |
| `aria-current="page"` mỗi trang | ≤ 1 trên **35/35** |
| Lỗi JS ở console | **0** |
| Vỏ dùng chung | 30/30 trang tự viết; 5 trang SQLAdmin dùng vỏ riêng của gói nhưng cùng thanh điều hướng + cùng token |

### Ma trận trạng thái đã soi

có dữ liệu · rỗng · lọc không ra kết quả · chưa nhập tìm kiếm · 404 · nút bị vô
hiệu hoá (thu hồi phiên khi không có phiên) · xác nhận nguy hiểm · email rất dài
(`khach.rat.dai.de.kiem.tra.tran@vidu-cong-ty.com.vn`) · một nguồn đọc không được
(hàng đợi chú ý → "không lấy được", **không** hiện 0).

---

## 4. Lỗi tìm được bằng trình duyệt mà mã và test đều không thấy

Bốn lỗi. Không cái nào lộ ra khi đọc mã.

### 4.1 · P1 · Thanh bên riêng của SQLAdmin — nguồn điều hướng **thứ tư**

`01` §5 tìm ra ba nguồn bằng cách đọc mã. Cái thứ tư chỉ hiện khi mở
`/admin/user/list` bằng mắt: gói SQLAdmin **tự dựng** thanh bên từ danh sách view
đã đăng ký, tức **31 mục phẳng**. Nửa SQLAdmin của khu quản trị vẫn là danh sách
31 mục trong khi nửa kia đã là cây sáu miền.

Nó không phải một danh sách trong kho, nên `grep` không tìm được — nó là **hệ quả
của `admin.add_view()`**.

Sửa: `is_visible = False` cho 22 trang nghiệp vụ (chỉ ẩn khỏi **menu**, route vẫn
sống). Bảng thô giữ nguyên — thanh bên đó **chính là** khu Data Explorer.
**Kết quả: 31 → 8.**

### 4.2 · P2 · Dải `.adm-top` thứ hai do 15 trang tự vẽ

Mỗi trang API tự phát `<div class="adm-top"><span class="eyebrow">API platform</span>`
trong thân. Vỏ mới cũng có `.adm-top` (thanh trên thật, sticky) ⇒ **hai thanh
dính cùng lớp chồng lên nhau khi cuộn**.

Gỡ cả 15 (14 ở `admin_api.py`, 1 ở `admin.py` — cái cuối mang thông tin thật
"N/M key hoạt động" nên được chuyển vào đầu trang).

### 4.3 · P1 · Cả **trang** cuộn ngang ở 390px, không phải chỉ cái bảng

`/admin/api-kill-switch` có `body.scrollWidth = 473px` ở viewport 390px. Thủ phạm
là một `<input>` có `size=` trong thân trang — bảng thì đã nằm trong `.tablewrap`
có `overflow-x:auto` và cuộn đúng.

Sửa ở **gốc dùng chung**: `.adm-content input,select,textarea{max-width:100%}` —
một luật, thay vì đi sửa từng thẻ input trong 173 KB f-string.

### 4.4 · P2 · `minmax(400px,1fr)` đẩy cả trang rộng ra ở 390px

Hai trang mới (`Hồ sơ 360`, `Hệ thống`) dùng
`grid-template-columns:repeat(auto-fit,minmax(400px,1fr))`. Ở viewport 390px thì
400px **lớn hơn cả màn hình**, và grid vẫn cấp cho track đó 400px ⇒ body 416px.

Sửa: `minmax(min(400px,100%),1fr)` cho cả bốn luật grid của khu quản trị.

⭐ Cả 4.3 và 4.4 đều là **tràn ở cấp trang**, không phải tràn trong một khối. Đúng
loại lỗi mà `overflow-x:hidden` toàn site sẽ che đi — và prompt 00 cấm đúng việc
che đó.

---

## 5. Việc còn lại của cổng này

| Việc | Vì sao chưa làm |
|---|---|
| Đo trên `https://app.lttstudios.com` | Cần deploy trước. CLAUDE.md 5b: loopback **bỏ qua** Cloudflare (cache, CSP biên, minify), nên trang có thể đẹp ở loopback mà vỡ với người dùng thật — đã dính một lần với `ltt.css` |
| Kiểm bàn phím/focus đầy đủ | Đã có `skip-link`, `aria-current`, `aria-label`, `sr-only`; chưa đi hết bằng Tab trên từng trang |

**Kết luận: PASS trên loopback.** Chưa được tuyên bố PASS trên URL công khai —
xem `20_FINAL_MVP_REPORT.md` §5.
