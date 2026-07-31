# Đánh giá UX/UI + phương án nâng tầm — 2026-08-01

> **✅ Pha UX‑1 ĐÃ XÂY XONG + deploy 2026-08-01** (phương án D). Đã làm: tách
> `server/static/ltt.css` (design system dùng chung); **console APIKEYS custom
> dark** (tab 4 loại, badge trạng thái + health + chips, Test/Bật‑Tắt/Reset tại
> dòng); chuyển 4 view trắng (Cấp credit/Thêm key/Models/Test) sang vỏ dark;
> **khoác dark cho sqladmin** (`data-bs-theme="dark"` + thanh LTT); polish catalog
> (hero + appcard hover) + login (logo mark + gradient). Full suite 1585 pass,
> scan 0; verify production qua edge (console 0 secret, sqladmin dark). Phần dưới
> là đánh giá/phương án gốc, giữ để tra cứu. **Pha UX‑2 (sau):** dashboard thống
> kê, hiệu ứng, a11y.


> Đánh giá bố cục/thẩm mĩ/tiện dụng của: trang chủ (catalog), trang đăng nhập,
> trang quản trị, menu APIKEYS. Căn cứ: template thật trong `server/templates/`
> + view quản trị trong `server/admin.py`. (Trình duyệt trên máy chủ đang chập
> IPv6 nên không chụp được ảnh; template là nguồn chân lý cho bố cục.)

## 1. Chấm điểm hiện trạng (thang 100)

| Bề mặt | Thẩm mĩ | Tiện dụng | Nhất quán | Ghi chú |
|---|---|---|---|---|
| Catalog công khai (`base_public`+`home`) | 72 | 75 | 90 | Dark sạch, nhưng **phẳng** — thiếu hero, phân cấp thị giác, thẻ app đơn điệu |
| Đăng nhập (`base_plain`+`login`) | 74 | 80 | 90 | Card giữa trang gọn; **thiếu logo/nhận diện**, tối giản quá |
| Vỏ đã-đăng-nhập (`base.html`) | 78 | 80 | 88 | Sidebar dark + topbar credit tốt; nền tảng vững nhất |
| **Quản trị (sqladmin mặc định)** | **45** | 70 | **25** | Theme **SÁNG** (Bootstrap/Tabler) — **chỏi hẳn** với nền tảng dark. Chuyển từ app dark → admin sáng gây "hẫng" |
| **View admin tự viết** (Cấp credit / Thêm key / Models / Test) | **30** | 60 | **15** | Trang **trắng trơn**, font `system-ui`, CSS inline tối thiểu — **ngôn ngữ thị giác thứ 3**, trông như chưa xong |
| **Menu APIKEYS** | **40** | 55 | 20 | Bảng sqladmin thô: category hiện dạng JSON `['image','chat']`, **không có badge trạng thái màu**, **không nút Test/Bật/Tắt tại dòng** (Test là trang trắng riêng), không thanh health, không lọc theo 4 loại |

**Điểm mấu chốt:** nền tảng có **BA ngôn ngữ thị giác rời rạc** — (1) dark tuỳ biến
đẹp cho trang khách/app, (2) sáng Bootstrap của sqladmin, (3) trắng-trơn của view
tự viết. Admin/APIKEYS vì thế **trông như bị lắp ghép, chưa hoàn thiện** — đúng
chỗ người dùng nêu. Trang khách/đăng nhập ổn nhưng còn **tối giản, thiếu điểm
nhấn** để "nâng tầm".

## 2. Vấn đề UX cụ thể (ưu tiên)

1. **Bất nhất thị giác admin** (nặng nhất): 3 look. Cần MỘT hệ thị giác dark
   xuyên suốt cả admin.
2. **View tự viết trắng trơn**: Cấp credit / Thêm key / Models / Test — không
   theo card dark của nền tảng.
3. **APIKEYS chưa "chuyên dụng"**: cần console riêng — badge trạng thái (active
   xanh / cooldown vàng / disabled đỏ), thanh health, category chips, nút
   Test/Bật/Tắt/Reset **ngay tại dòng**, lọc theo 4 loại, empty state.
4. **Catalog phẳng**: thêm hero ngắn, thẻ app có icon/accent nổi, hover nhấc,
   trạng thái "cần thiết lập" rõ hơn, responsive lưới đẹp.
5. **Đăng nhập trơ**: thêm logo mark + nền gradient rất nhẹ + nút loading state.
6. **Thiếu hệ token dùng chung**: mỗi template lặp lại `:root{--bg...}` — nên
   tách 1 file CSS tĩnh dùng chung (`/static/ltt.css`) để nhất quán + dễ sửa.

## 3. Ba phương án + chấm điểm (thang 100)

Tiêu chí: nhất quán/thẩm mĩ 30 · tiện dụng 25 · công sức (ít=cao) 20 · rủi ro
(thấp=cao) 15 · mở rộng 10.

| PA | Mô tả | Nhất quán | Tiện dụng | Công sức | Rủi ro | Mở rộng | **Tổng** |
|---|---|---|---|---|---|---|---|
| **A. Chỉ khoác dark cho sqladmin** | Inject CSS dark + sửa view trắng | 22/30 | 16/25 | 17/20 | 13/15 | 6/10 | **74** |
| **B. Thay sqladmin bằng admin custom hoàn toàn** | Viết lại mọi trang admin | 29/30 | 24/25 | 6/20 | 7/15 | 9/10 | **75** |
| **D. Hybrid theo pha (đề xuất)** | Console APIKEYS/credit/users **custom dark** dùng `base.html`; sqladmin **khoác dark** giữ cho bảng hiếm; tách `ltt.css`; polish catalog+login | 29/30 | 23/25 | 13/20 | 12/15 | 9/10 | **86** |

**A** rẻ nhưng sqladmin khoác dark vẫn "gượng" (Bootstrap cứng). **B** đẹp nhưng
viết lại cả admin (Session/Job/PlatformInfo...) tốn công cho bảng ít dùng. **D**
làm đẹp đúng bề mặt QUAN TRỌNG (APIKEYS/credit/users) bằng vỏ nền tảng, để
sqladmin (đã khoác dark) lo phần đuôi dài — tối ưu.

## 4. Phương án đề xuất: **D — Nâng tầm UX theo pha**

**Pha UX‑1 (MVP trải nghiệm, làm trước):**
1. **Tách `server/static/ltt.css`** — hệ token + component dùng chung (card,
   badge, button, table, form). Mọi template `@import`/link tới nó → hết lặp,
   nhất quán tuyệt đối. (base.html/base_public/base_plain rút CSS vào đây.)
2. **Console APIKEYS custom (dark, dùng `base.html`)** tại `/admin` hoặc route
   riêng: header + tab 4 loại (Điều khiển model / Chat / Ảnh / Video), bảng/thẻ
   với **badge trạng thái màu + thanh health + category chips + preview mono**,
   nút **Test / Bật‑Tắt / Reset ngay tại dòng**, "+ Thêm key" + "Models",
   empty state. Giữ ApiKeyAdmin (sqladmin) làm bảng thô dự phòng.
3. **Khoác dark cho sqladmin** (custom base template + CSS override) để các bảng
   còn lại (User/Credit/Job/Session) hoà vào theme.
4. **Chuyển các view tự viết** (Cấp credit / Thêm key / Models / Test) sang dùng
   `base.html` (card dark) — xoá trang trắng.
5. **Polish catalog + login**: hero ngắn ở catalog, thẻ app icon/accent + hover
   nhấc + badge "cần thiết lập"; login thêm logo mark + gradient nhẹ + nút loading.

**Pha UX‑2 (sau):** dashboard thống kê (credit/job/key health), hiệu ứng chuyển,
dark/light toggle, rà soát tiếp cận (a11y/contrast/keyboard), skeleton loading.

**Kết quả Pha UX‑1:** một hệ thị giác dark xuyên suốt; APIKEYS thành console
chuyên nghiệp (thao tác 1 chỗ); trang khách/đăng nhập có điểm nhấn — "nâng tầm"
mà không đập đi xây lại.

## 5. Gợi ý kiểm chứng
Mỗi bước: kiểm **trình duyệt thật** (khi IPv6 máy ổn / từ máy khác) — chụp
trước/sau. Test regression: template render 200, không lộ secret ở APIKEYS,
CSRF ở form. Có thể dựng **mockup HTML (artifact)** để tổng duyệt thị giác
TRƯỚC khi ghép vào code thật.
