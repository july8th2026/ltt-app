# Hợp đồng giao diện khu VPS — bản chốt

**2026-08-27.** Kết quả Đợt 7 (Prompt 06 §6). Đây là **luật cho mọi thay đổi
giao diện VPS về sau**, không phải một bản tóm tắt của việc đã làm.

> Đọc trước: `00_KE_HOACH_GIAO_DIEN.md` (kế hoạch + ma trận ảnh↔live),
> `01_QUYET_DINH_D01_D04.md` (bốn quyết định + căn cứ),
> `15_FINAL_MVP_REPORT.md` (bằng chứng đo được).

---

## 1. Năm màn hình, và ranh giới giữa chúng

| Màn | Route | Người xem | Vỏ |
|---|---|---|---|
| **A** Storefront | `GET /vps` | ẩn danh | **không** thanh bên |
| **B** Nhà của khách + tạo máy | `GET /vps` | đã đăng nhập | thanh bên |
| **C** Trung tâm điều khiển | `GET /vps/{id}` | chủ máy | thanh bên, cấp máy |
| **D** Cài Windows | `GET /vps/{id}/cai-dat` | chủ máy | thanh bên, cấp máy |
| **E** Console | `GET /vps/{id}/console` | chủ máy | thanh bên, cấp máy |

🔴 **Thanh bên là công cụ của người ĐÃ mua.** Vultr chia làm hai site vì lẽ đó.
`_menu()` trả rỗng cho khách ẩn danh, và `vps_base.html` không dựng vỏ điều
khiển khi menu rỗng. Đừng "sửa" điều này — nó là thiết kế, không phải thiếu sót.

---

## 2. Nơi từng loại thứ được phép sống

| Loại | Chỗ duy nhất | Cấm |
|---|---|---|
| Kiểu (CSS) | mục `LỚP NGỮ NGHĨA CỦA KHU VPS` trong `server/static/ltt.css` | khối `<style>` trong template |
| Nhãn trạng thái + màu badge | `apps/vps/nhan.py` | bảng tra chép tay trong Jinja |
| Nhãn sự kiện nhật ký | `apps/vps/nhan.py:SU_KIEN` | như trên |
| Việc nào hợp lệ ở trạng thái nào | `services/dieu_khien.kiem_dieu_khien_duoc` | danh sách trạng thái thứ hai trong template |
| Giá, cấu hình, băng thông | `apps/vps/cost.py` | số viết cứng |
| Nhịp ảnh chụp, chu kỳ, ân hạn | `sao_luu.GIU`, `CHU_KY_NGAY`, `billing.AN_HAN_TRUOC_KHI_XOA_NGAY` | số viết cứng |
| Đếm, gộp, lọc | route (`_thong_ke`, `_may_cua_toi`) | vòng lặp tính toán trong Jinja |
| Thứ lặp ở ≥ 2 **trang** | `server/templates/_vps_mac.html` | chép sang trang thứ hai |

**Ranh giới của tệp macro:** chỉ thứ lặp ở ≥ 2 **trang**. Không macro cho hero,
khối Nguy hiểm, cột bước, thanh công cụ console — mỗi thứ chỉ sống ở một trang.
Prompt 00 §8 cấm dựng một khung thành phần; năm macro hiện có không phải một
khung, chúng là năm hàm.

---

## 3. Ngữ pháp màu — một luật cho cả năm trang

| Ý nghĩa | Token | Dùng ở |
|---|---|---|
| khoẻ · đang chạy | `--ok` / `.b-ok` | badge `dang_chay` |
| vận hành · đang chọn | `--vps-teal*` | nút Bật/Console/Tạo máy, thẻ gói đang chọn |
| đang tạo · cần chú ý | `--warn` / `.b-warn` | `dang_tao`, `bi_treo`, còn ≤ 3 ngày, băng thông ≥ 80% |
| lỗi · phá huỷ | `--err` / `.b-err` | `loi`, khối Nguy hiểm, băng thông ≥ 100% |
| đã tắt · không hoạt động | `--grey` / `.b-grey` | `da_tat`, `da_xoa`, ngắt kết nối sạch |
| **đỏ thương hiệu LTT** | `--accent` | **chỉ** header/footer nền tảng |

⚠️ **Màu không bao giờ đứng một mình.** Mọi badge mang chấm **và** chữ; mọi thẻ
đang chọn mang viền dày **và** nền. Một ô đỏ không có chữ là một ô vô nghĩa với
người không phân biệt được màu.

🔴 **`.btn.btn-goi`, không phải `.btn-goi`.** `_kieu_chung.html` là khối
`<style>` nội tuyến trong `<head>` **đứng sau** thẻ `<link>` tới `ltt.css`, và
nó khai `button, .btn { background: var(--accent) }`. Cùng độ đặc hiệu nhưng đến
sau ⇒ nó thắng mọi luật `.btn-*` **một-class** viết trong `ltt.css`, và nút vận
hành ra **màu đỏ** mà không có cảnh báo nào. Bẫy này áp cho **mọi khu**, không
riêng VPS.

---

## 4. Mười tám thứ KHÔNG được nói

Năm ảnh tham chiếu vẽ đúng hình dạng và sai mười lăm lời hứa. Danh sách cấm,
áp cho **cả năm trang**, có bánh cóc canh
(`test_311::test_KHONG_trang_VPS_nao_hua_thu_KHONG_CO`):

**Lời hứa dịch vụ không có:** `99,9% / 99.9% / uptime / SLA` · `hỗ trợ 24/7` ·
`ticket` · `Enterprise` · `unlimited` / `không giới hạn` · `cloud`.

**Số liệu không có nguồn:** tốc độ cổng (`1 Gbps`) · `% tiến độ` hay ETA khi tạo
máy · đồng hồ đếm ngược phiên console · `AES-256`.

**Thứ nền tảng không giữ:** mật khẩu Windows (ô hiện/chép/đặt lại) · IP nội bộ
của cụm · `vmid` · `UPID` của Proxmox · IP và trình duyệt của khách.

**Sai sự thật sản phẩm:** ảnh chụp "hằng ngày" (thật: **hằng tuần, giữ 1 bản,
cùng kho**) · "sao lưu" thay cho "ảnh chụp" · vùng "Hà Nội" (thật: **IP riêng ở
Singapore**, máy chủ tại Việt Nam) · nút dẫn tới route không tồn tại.

---

## 5. Sáu dòng "Đọc trước khi thuê" là RÀNG BUỘC

Toàn văn là điều kiện của Q103. `test_298` đối chiếu **từng con số** trong đó
với hằng số thật trong mã. Được đổi **cách bày**; **không** được đổi một chữ, và
**không** được rút gọn để trang gọn hơn.

Chúng là **một macro** (`doc_truoc()`), hiện khác nhau tuỳ người xem:

* khách ẩn danh — **mở sẵn**, ngay dưới bảng giá: họ đang **quyết định**;
* chủ máy — **gấp lại** ở cuối trang: họ đã đồng ý một lần, lúc bấm "Tạo máy".

---

## 6. Hợp đồng an ninh — không đợt giao diện nào được chạm

| Hợp đồng | Ở đâu | Bánh cóc |
|---|---|---|
| Cờ tắt ⇒ 404, và cổng cờ đứng **trước** `require_login` | `routes._cong_co` | `test_252` |
| Khách ẩn danh: không vỏ điều khiển, không thấy máy của ai | `_menu()`, `_may_cua_toi` | `test_252`, `test_304` |
| Máy người khác ⇒ **404**, không phải 403 | `_may_cua_khach` | `test_297` |
| Ba việc phá huỷ đòi **gõ đúng tên máy** | `cai_lai` · `khoi_phuc` · `xoa` | `test_280`, `test_311` |
| Gỡ đĩa cài là **POST có CSRF do khách bấm** | `go_dia_cai` | `test_280` |
| Vé console **60 giây, một lần**, không vào URL trang | `console.cap_ve` | `test_282` |
| Console: `resizeSession=false`, không tự nối lại bằng vé đã tiêu | `vps_console.html` | `test_311` |
| Fail-closed: không đọc được sức chứa ⇒ **không dựng `<form>`** | `vps.html` | `test_252`, `test_298` |
| Thiếu credit **không khoá nút** — máy chủ trả câu lỗi rõ | `vps.html` | `test_298` |

**Đổi tên máy (`POST /{id}/doi-ten`) cố ý KHÔNG đòi gõ xác nhận:** đổi nhãn là
việc đảo được, và đặt rào chắn ở việc đảo được thì rào chắn ở việc **không** đảo
được bị nhờn.

---

## 7. Luật responsive

* **Sáu bề ngang bắt buộc soi:** 1920 · 1440 · 1280 · 1024 · 768 · 390.
* **0 tràn ngang tài liệu.** Nội dung rộng (bảng, khối mã, sơ đồ) cuộn **trong
  khung của nó** (`overflow-x:auto`), không đẩy cả trang cuộn.
* 🔴 **`minmax(0,1fr)`, không phải `1fr`.** Một cột `1fr` mặc định là
  `minmax(auto,1fr)` — **sàn của nó là min-content**, nên nội dung dài hơn cột
  thì cột nở ra và tràn khỏi trang. Đã dính ở 390px trang cài đặt: tràn 7px, và
  trang vẫn render bình thường nên không ai báo lỗi.
* **Hình trang trí biến mất ở màn hẹp** (`.vps-hero-art`, ngưỡng 860px). Đặt một
  hình trên giá ở 390px là đẩy con số quan trọng nhất xuống dưới màn hình đầu.
* **Cột phụ xuống dưới, không co lại:** biểu mẫu ba chặng nhét vào 300px là một
  biểu mẫu không ai điền. Ngưỡng theo **nội dung**, không theo tên thiết bị.

---

## 8. Thêm một trang VPS mới thì phải làm gì

1. Thêm **một dòng** vào `apps/vps/nav.py` (menu là dữ liệu, không phải HTML).
2. Kế thừa `vps_base.html`; `{% import "_vps_mac.html" as mac with context %}`
   — ⚠️ thiếu `with context` thì mọi chuỗi trong macro ra tiếng Việt trên bản
   EN, và **không phép kiểm `.po` nào bắt được** (chuỗi có trong catalog và đã
   dịch).
3. Kiểu vào mục VPS của `ltt.css`. **Không** `<style>` trong template.
4. Trạng thái máy qua `mac.badge_trang_thai()` / `mac.dinh_may()`.
5. Dịch chuỗi mới **cùng đợt**: sửa tay `.po` (giữ LF), rồi
   `python tools/i18n.py bien-dich`. ⛔ Không chạy `i18n.py trich` cho vài chuỗi
   — nó sắp xếp lại cả tệp.
6. Thêm tài sản tĩnh mới ⇒ thêm vào `templating.TAI_SAN_CO_VERSION`. Quên là
   dính bẫy cache Cloudflare (quy tắc 6).
7. Dựng cảnh bằng `python tools\vps_dung_mau.py`, phục vụ qua HTTP, soi bằng
   Chrome thật ở sáu bề ngang. ⚠️ Chrome **chặn giao thức `file:`** — và khi bị
   chặn nó không báo lỗi rõ, mọi số đo về 0.

---

## 9. Điều bộ test KHÔNG chốt được

Ba lỗi nặng nhất của đợt 25/08 và **cả ba lỗi tự gây ra trong đợt này** đều có
**HTML đúng** và **cây trợ năng đúng**:

* nút vận hành ra màu đỏ (thua độ đặc hiệu),
* bố cục vỡ vì `display` nội tuyến bị JS xoá,
* tràn ngang 7px vì `1fr` thay vì `minmax(0,1fr)`.

⇒ Bánh cóc chốt **nguyên nhân** (không còn `<style>` trong template, luật hai
class, không `display` nội tuyến). **Kết quả phải kiểm bằng trình duyệt thật.**
Một phép kiểm đọc HTML mà báo "giao diện đúng" là một phép kiểm nói quá phạm vi
của nó.

⚠️ Và một phép kiểm đọc **mã nguồn** phải đọc **mã**, không đọc lời bàn về mã.
Lớp lỗi "phép kiểm khớp vào chính chú thích của mình" đã lặp **năm lần** trong
dự án; bóc chú thích trước khi khẳng định, và cắt lát từ `/*` **mở** khối chứ
không từ chính cái mốc.
