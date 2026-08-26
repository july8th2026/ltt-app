# Kế hoạch nâng giao diện khu VPS lên MVP — theo Prompt Pack V2 + 5 ảnh tham chiếu

**2026-08-26.** Yêu cầu chủ sản phẩm: *nghiên cứu sâu hệ thống và giao diện `/vps`,
đọc bộ prompt `LTT_VPS_MVP_UI_Prompt_Pack_V2`, phân tích 5 ảnh tham chiếu xem ảnh
nào là trang nào, rồi lập kế hoạch triển khai chi tiết để giao diện thật giống ảnh
nhất có thể.*

Tài liệu này là **kết quả của Prompt 00** (audit + khoá hợp đồng) gộp với
**Prompt 06 §6** (luật cuối). Nó chưa sửa một dòng runtime nào — đúng STOP
CONDITION của Prompt 00.

> ## ✅ TRẠNG THÁI 2026-08-27 — ĐỢT 1→7 XONG
>
> | Đợt | Việc | Commit |
> |---|---|---|
> | 1+2 | nền dùng chung + storefront (ảnh 1) | `ffdd498` |
> | 3 | nhà của khách + tạo máy (ảnh 2) · **D-01 tên máy** | `390a265` |
> | 4 | trung tâm điều khiển một máy (ảnh 3) | `ad1bc7d` |
> | 5+6 | cài Windows (ảnh 4) · console (ảnh 5) | `de7f8db` |
> | 7 | cổng liên trang + hai tài liệu chốt | `9d14101` |
>
> **Bằng chứng:** 14 cảnh × 6 bề ngang = **84 tổ hợp → 0 tràn ngang, 0 lỗi
> console**; **398 phép kiểm khu VPS xanh**; hai bánh cóc i18n đúng mốc.
> Báo cáo đầy đủ + khoảng trống bằng chứng: `15_FINAL_MVP_REPORT.md`.
> Luật cho mọi thay đổi về sau: `14_VPS_UI_CONTRACT_FINAL.md`.
>
> **Còn lại:** ⏳ **D-02** (một máy thật cho GJ2–GJ5) và ⏳ **deploy** — cả hai
> là quyết định của chủ sản phẩm. Đợt 8 (deploy) chưa chạy.
>
> **Nguồn dữ liệu.** Đọc live code (`apps/vps/*`, `server/templates/vps*.html`,
> `server/static/ltt.css`), bộ prompt trên Google Drive, 5 ảnh, và **trang đang
> chạy thật**: `https://app.lttstudios.com/vps` đo bằng Chrome thật
> (playwright-cli) ở 1440×900 và 390×844, ẩn danh.

---

## 0. Hai điều phải biết trước mọi việc khác

### 0.1 🔴 `/vps` ĐANG SỐNG VÀ CÔNG KHAI — `CLAUDE.md` nói ngược

`CLAUDE.md` hàng H39 viết: *"App vẫn **TẮT** (`LTT_VPS` chưa đặt)"*.

Đo 26/08:

```
C:\LTTPlatform\secrets\app.env:72   LTT_VPS=1
GET https://app.lttstudios.com/vps  → 200   (ẩn danh, không cần đăng nhập)
GET http://127.0.0.1:8100/vps       → 200
```

**Khu VPS đang mở, đang phục vụ khách ẩn danh, và biểu mẫu tạo máy thu credit
thật.** Đây đúng lớp lỗi tài liệu mà chính `CLAUDE.md` đã phải sửa cho Public API
ngày 26/08 — và nó nguy hiểm theo cùng một hướng: một phiên sau đọc dòng đó sẽ
sửa `/vps` **như sửa mã chết**.

⇒ **Việc đầu tiên của đợt thi hành là sửa dòng đó trong `CLAUDE.md`.** Và mọi
thay đổi trong kế hoạch này là thay đổi trên **trang đang bán hàng**, không phải
trên một bản nháp.

### 0.2 Trang bán đã qua một đợt nâng (25/08), ba trang còn lại thì chưa

`docs/VPS/AUDIT_GIAO_DIEN_2026-08-25.md` đã đưa `/vps` ẩn danh từ **3,8 → 8,2/10**
(V1–V4: sửa bố cục vỡ, thêm `<h1>`, đưa giá lên trên, thẻ gói có nút + dấu "nên
chọn", ẩn số liệu vận hành khỏi khách lạ). Tài liệu đó tự ghi phần còn lại:

> *"`/vps/chi-tiet` (trang quản lý một máy) — **chưa soi**; cần một máy thật đang chạy."*

Đo lại 26/08 trên trang đang chạy, ẩn danh:

| Đo | 1440×900 | 390×844 |
|---|---|---|
| Tràn ngang | không (`scrollWidth == innerWidth`) | không (390 == 390) |
| `main h1` | 1 | 1 |
| Thẻ gói | 3 | 3 |
| Chiều cao tài liệu | — | 2.197px |
| Lỗi console / request hỏng | 0 / 0 | 0 / 0 |

Nền kỹ thuật sạch. Việc còn lại là **trình bày**, và nó nằm gần hết ở ba trang
`C · D · E` — ba trang **chưa được chạm tới lần nào**.

---

## 1. Ảnh nào là trang nào

Năm ảnh khớp **đúng** năm màn hình UX mà `MVP_CONTRACT.md` khai. Không ảnh nào
thừa, không màn hình nào thiếu ảnh.

| Ảnh | Màn hình | Route | Nhận ra bằng |
|---|---|---|---|
| **(1)** | **A — Storefront công khai** | `GET /vps` *(ẩn danh)* | nav ngang marketing, hero + hình Windows, 3 thẻ gói có giá, **không có thanh bên**, nút "Đăng nhập để quản lý" |
| **(2)** | **B — Nhà của khách + Tạo máy** | `GET /vps` *(đã đăng nhập)* | thanh bên trái, "VPS của bạn", 4 ô chỉ số, danh sách 3 máy, cột phải "Tạo VPS mới" 3 bước |
| **(3)** | **C — Trung tâm điều khiển một máy** | `GET /vps/{id}` | breadcrumb `VPS của bạn › studio-win-01`, dải 5 nút hành động, 4 ô (Tài nguyên/Thanh toán/Băng thông/Snapshot), **Danger Zone** |
| **(4)** | **D — Hướng dẫn cài Windows** | `GET /vps/{id}/cai-dat` | "Cài Windows • studio-win-01", cột trái 8 bước, khối **QUAN TRỌNG** về "Press any key…", ảnh màn hình trình cài đặt |
| **(5)** | **E — Console trong trình duyệt** | `GET /vps/{id}/console` | "Console • studio-win-01", thanh công cụ Ctrl+Alt+Del/Reconnect/Full Screen, khung desktop Windows chiếm giữa, cột phải "Khi nào nên dùng Console?" |

**Ảnh (1) không có thanh bên còn ảnh (2)(3)(4)(5) đều có** — đó là bằng chứng
người vẽ ảnh hiểu đúng ranh giới mà `vps_base.html` đã dựng sẵn: *menu là công cụ
của người ĐÃ mua*. Live code và ảnh trùng nhau ở điểm này; giữ nguyên.

---

## 2. Ma trận ảnh → live: cái nào lấy, cái nào cấm

Đây là artifact `06_REFERENCE_TO_LIVE_GAP.md` mà Prompt 00 §7 đòi. Luật:
**live code thắng**. Ảnh là *north star thị giác*, không phải bản khai tính năng.

### 2.1 🔴 Mười lăm thứ trong ảnh KHÔNG ĐƯỢC đưa lên trang

Xếp theo mức nguy hiểm, không theo thứ tự ảnh.

| # | Trong ảnh | Sự thật trong mã | Vì sao cấm |
|---|---|---|---|
| 1 | **Ảnh 3: hàng `Password ••••••••` có nút hiện + sao chép** | `os_images.py`, `vps_cai_dat.html`: *"chúng tôi không biết mật khẩu của bạn và không đặt lại được nó"* | Nền tảng **không giữ** mật khẩu nào. Vẽ ô đó ra là hứa một thứ không tồn tại, đúng lúc khách đang cần nó nhất |
| 2 | **Ảnh 5: "Mã hoá AES-256 Encrypted"** | không nơi nào trong mã khẳng định thuật toán | Khẩu hiệu bảo mật bịa. Đường đi là WSS qua Cloudflare + RFB — nói "AES-256" là nói một điều ta không đo |
| 3 | **Ảnh 5: "Phiên sẽ hết hạn sau 14:47"** + đồng hồ đếm ngược | `console.HAN_VE_GIAY = 60`, vé **dùng đúng một lần**, tiêu ngay lúc mở WebSocket | Sau khi nối xong thì **không còn hạn nào để đếm**. Một đồng hồ đếm ngược ở đây đếm một thứ không có |
| 4 | **Ảnh 1+3: "Uptime SLA 99.9% / 99.95%"** | `test_298::test_KHONG_hua_SLA`, `test_khong_hua_uptime` | Đã có phép kiểm chặn. Best-effort là chốt của Q103 |
| 5 | **Ảnh 1+2+3+4+5: "Hỗ trợ 24/7", "Liên hệ hỗ trợ", "Tạo ticket hỗ trợ"** | không có hệ thống ticket, không có đội trực | Hứa một kênh không tồn tại |
| 6 | **Ảnh 1+2: "Hạ tầng NVMe Enterprise"** | `cost.py`: đĩa là **hạn mức trên kho dùng chung** (LVM-thin), không phải ổ cấp riêng | Chữ "Enterprise" mời một kỳ vọng ta không giao |
| 7 | **Ảnh 3: "Snapshot — Tự động hàng ngày"** | `sao_luu.GIU = 1`, nhịp **hằng tuần** | Sai tần suất. Khách sẽ tin có bản của hôm qua |
| 8 | **Ảnh 1: chip "Snapshot — Sao lưu & khôi phục"** | điều khoản: ảnh chụp nằm **cùng kho** với đĩa gốc, **không thay thế sao lưu** | `test_298::test_noi_ro_anh_chup_KHONG_phai_sao_luu` |
| 9 | **Ảnh 3: nút "Gia hạn ngay"** | không có route gia hạn; `bao_tri.chay` tự thu mỗi 30 ngày | Một nút không dẫn tới đâu |
| 10 | **Ảnh 3: "Quản lý snapshot", "Chi tiết băng thông", "Xem tất cả lịch sử"** | `nav.SAP_CO_MAY` khai `anh_chup`, `bang_thong` là **chưa có route** | Liên kết chết. `nav.py` đã chọn cách đúng: hiện mờ, không bấm được |
| 11 | **Ảnh 2: "Đang khởi tạo… (dự kiến 2–5 phút)"** | job trả **trạng thái**, không trả phần trăm hay ETA | Tiến độ giả. `docs/VPS/GIAO_DIEN.md` có một bản mockup `[5%]…[100%]` — **nó chưa bao giờ được thi hành**, và không có gì trong `jobs.py` sinh ra các mốc đó |
| 12 | **Ảnh 2+3+5: "Hanoi, Vietnam" / cờ Việt Nam** | trang bán: *"IP riêng ở **Singapore**. Máy chủ đặt tại Việt Nam, đường vào đi qua Singapore"* | Nửa đúng là sai. Khách đo ping sẽ thấy Singapore |
| 13 | **Ảnh 3: "1 Gbps Network"** | không nơi nào khai tốc độ cổng | Con số chưa ai đo |
| 14 | **Ảnh 2: chuông thông báo "3", chip "LTT Studio Team Pro · TEAM-LTT-001"** | không có thông báo, không có tính năng nhóm | Hai tính năng bịa |
| 15 | **Ảnh 2: "IP riêng: 10.0.0.5 🔒" hiện cạnh IP công khai** | `ip_noi_bo` là địa chỉ **trong LAN của cụm** | Không có ích cho khách, và nó là chi tiết hạ tầng |

Thêm ba thứ nhỏ hơn nhưng cùng loại: **giá 89.000đ** (thật: 149.000đ), **tên gói
Starter/Pro/Business** (thật: VPS Nhỏ/Vừa/Lớn), **cấu hình 4 vCPU/16 GB/60 GB
cho ba gói** (thật: 1/2/40 · 2/4/60 · 4/8/80). Ảnh cũng cho khách **ẩn danh** thấy
số dư credit — không thể.

> ⚠️ Cả 15 dòng trên đều **không** là lỗi của người vẽ ảnh. Ảnh do một mô hình
> sinh, và nó lấy khuôn của Vultr/AZDIGI/Contabo — nơi những lời hứa đó là thật.
> Việc của ta là **lấy hình, bỏ lời hứa**.

### 2.2 ✅ Mười ba thứ trong ảnh LẤY ĐƯỢC NGUYÊN VẸN

| Ý trong ảnh | Dữ liệu live đã có sẵn |
|---|---|
| Vỏ carbon tối, dải nhấn nhỏ, thẻ nhiều tầng bề mặt | `ltt.css` đã là hệ thiết kế đúng như vậy (`--surface-canvas/base/raised/overlay`) |
| Thanh bên trái chỉ cho người đã đăng nhập | `vps_base.html` + `nav.py` **đã làm đúng** |
| Breadcrumb `VPS của bạn › tên máy` | `nav.py` menu đổi cấp + `topbar_title` đã có |
| Badge trạng thái có chấm màu + chữ | `.badge .b-ok/.b-warn/.b-err/.b-grey` đã có trong `ltt.css` |
| 4 ô chỉ số (Tổng/Đang chạy/Đã tắt/Sắp hết hạn) | suy được từ `_may_cua_toi()`; `.chi-so-luoi` đã có sẵn (dùng ở cổng lập trình viên) |
| Thẻ máy thay bảng 7 cột | `_may_cua_toi()` đã trả đủ: trạng thái, IP, gói, OS, băng thông, `con_ngay` |
| Nút "Sao chép IP" | `sao_chep.js` đã có và đã cache-bust |
| Dải nút hành động **theo trạng thái** | `dieu_khien.kiem_dieu_khien_duoc()` đã là nguồn chân lý |
| Đồng hồ đo băng thông có % | `bang_thong.phan_tram()` + `doc_duoc()` |
| Thẻ Thanh toán: chu kỳ / trả tới / còn N ngày | `CHU_KY_NGAY=30`, `paid_until`, `billing.con_bao_nhieu_ngay()` |
| **Danger Zone** tách hẳn, ba việc, đỏ | `vps_chi_tiet.html` đã có ba khối; ảnh chỉ trình bày đẹp hơn |
| Cột 8 bước cài Windows | `vps_cai_dat.html` đã có 10 `<li>`, gộp được về 8 bước khái niệm |
| Cột phải "Khi nào dùng Console / khi nào dùng RDP" | `vps_console.html` đã có đúng câu đó ở dạng một đoạn văn |

### 2.3 ⚠️ Bảy thứ LẤY ĐƯỢC NHƯNG PHẢI SỬA LỜI

| Trong ảnh | Đổi thành |
|---|---|
| Chip "Mọi cổng — mở toàn bộ cổng (1–65535)" | ✅ **đúng thật** (NAT 1:1) — giữ nguyên, đây là thứ ta hơn đối thủ |
| "Browser Console — không cần RDP" | *"Console trong trình duyệt — dùng khi RDP hỏng. Chậm hơn RDP, không copy/paste"* |
| "Thanh toán bằng credit — không hoàn tiền" | ✅ đúng; đối chiếu nguyên văn `dieu_khoan.py` |
| Nút **"RDP"** trên dải hành động (ảnh 3) | Trang web **không mở được RDP**. Đổi thành ô sao chép `mstsc /v:<ip>` + liên kết trang hướng dẫn |
| Ảnh 5: "Trình duyệt Chrome 124 · IP của bạn 113.170.**.**" | Bỏ. Là dữ liệu client, không phải dữ liệu phiên, và IP khách là thông tin riêng tư không cần hiện |
| Ảnh 4: "3 / 8" + dấu tích + nút "Tôi đã hoàn tất bước này" | Không có tiến độ lưu ở máy chủ. Làm **cột bước neo theo mỏ neo** (`:target`/`IntersectionObserver`), **không** dấu tích lưu được, **không** đếm "3/8" |
| Ảnh 2: bút chì đổi tên máy | Xem **Quyết định D-01** ở §7 — cột `ten` có thật nhưng **chưa có đường nào đặt nó** |

---

## 3. Hợp đồng phải giữ (Prompt 00 §5) — đã xác minh trên live code

Không đợt nào trong §5 được phép chạm vào những thứ này.

| Hợp đồng | Ở đâu | Phép kiểm đang canh |
|---|---|---|
| Cờ tắt ⇒ **404**, không lộ bề mặt | `routes._cong_co`, đứng **trước** `require_login` | `test_252::test_cong_co_dung_TRUOC_require_login`, `test_co_tat_thi_URL_go_thang_tra_404` |
| Khách ẩn danh không thấy vỏ điều khiển, không thấy máy của ai | `_menu()` trả rỗng; `_may_cua_toi` chỉ gọi khi có `user_id` | `test_304::test_khach_AN_DANH_khong_thay_vo_dieu_khien`, `test_252::test_khach_AN_DANH_khong_thay_bieu_mau_va_khong_thay_may_cua_ai` |
| Máy người khác ⇒ **404**, không phải 403 | `_may_cua_khach()` | `test_297` |
| Tạo máy: CSRF → gói hợp lệ → OS × gói hợp lệ → sức chứa → **thu credit** → nộp job | `routes.tao_may` | `test_252::test_tao_may_thanh_cong_thu_tien_va_NOP_JOB_chu_khong_cham_proxmox` |
| Không đọc được sức chứa ⇒ **không dựng `<form>`**, chỉ bảng giá | `vps.html` biến `ban_duoc` | `test_252::test_khong_doc_duoc_suc_chua...`, `test_298::test_KHONG_co_bieu_mau_khi_khong_doc_duoc_suc_chua` |
| Thiếu credit **KHÔNG khoá nút** — máy chủ trả câu lỗi rõ | `vps.html` JS `capNhat()` | `test_298::test_KHONG_khoa_nut_khi_thieu_credit` |
| Hỏng JS thì trang vẫn dùng được | JS chỉ lọc/tính, máy chủ vẫn kiểm | `test_298::test_JS_hong_thi_trang_van_dung_duoc` |
| Ba việc phá huỷ đòi **gõ đúng tên máy** | `cai_lai_may`, `khoi_phuc_may`, `xoa_may` | `test_280` |
| Gỡ đĩa cài là **POST có CSRF** do khách bấm | `go_dia_cai` | `test_280` |
| Vé console 60 giây, **một lần**, không vào URL trang | `console.cap_ve` + WS query | `test_282` |
| Điều khoản đối chiếu **từng con số** với hằng số mã | `dieu_khoan.py` | `test_298` (24 phép kiểm) |
| `class` KIỂU tách khỏi `class` MÓC JS | `.vps-the` vs `.vps-os` | `test_304::test_class_KIEU_tach_khoi_class_MOC_JS` |
| Không `display` nội tuyến để JS xoá nhầm | `vps.html` | `test_304::test_khong_con_display_noi_tuyen_de_JS_xoa_nham` |
| Bản EN không còn tiếng Việt trên **mọi** trang VPS | `.po` | `test_305` (5 phép kiểm) |

⛔ **Bốn cái bẫy đã trả giá, ghi lại để không dẫm lại** (từ audit 25/08):

1. `o.style.display = ''` **xoá** thuộc tính nội tuyến → `<label>` rơi về
   `inline` → vỡ bố cục ngay khi tải. Ẩn bằng `hidden` + class.
2. Dùng chung một class cho **cả kiểu lẫn móc JS** → bộ lọc ẩn nhầm cả thẻ gói.
3. Thay thế hàng loạt `<th(?![^>]*scope=)` khớp luôn vào `<thead>`. Neo vào
   `<th\b`.
4. `{{ app.display_name }}` render **trần** thì `N_()` không bao giờ được tra —
   chuỗi có trong `.po`, đã dịch, và vẫn ra tiếng Việt. Không phép kiểm `.po`
   nào bắt được; chỉ đo trên trang render mới thấy.

---

## 4. Nền trình bày dùng chung — quyết định kiến trúc

### 4.1 CSS ở đâu: **thêm một mục vào `ltt.css`**, không tạo tệp mới

Ba lý do, và lý do thứ ba mới là lý do thật:

1. **Đã có tiền lệ rõ.** `ltt.css` đã chứa các mục riêng theo khu: `.app-shell`
   (VPS + API), `.chi-so-*` (cổng lập trình viên), `.dev-sub`, `.tv-*`, `.th-*`,
   `.up-*`, `.clip-*`. Một mục `/* ─── KHU VPS ─── */` là **đi theo khuôn**, không
   phải phá khuôn.
2. **`base.html` không có `{% block head_extra %}`.** Thêm một tệp CSS riêng là
   phải sửa `base.html` — một tệp mọi trang của mọi app đều đi qua.
3. 🔴 **Cache-bust.** `templating.TAI_SAN_CO_VERSION` là một **danh sách gõ tay**:
   `("ltt.css", "sao_chep.js", "cam_chon.js", "chon_tep.js")`. Một `vps.css` mới
   mà quên thêm vào đó sẽ mang **đúng hash của ltt.css** — đổi CSS mà URL không
   đổi, Cloudflare phục vụ bản cũ tới hết TTL. Chính chú thích trong tệp đó ghi
   *"TRƯỚC 25/08 HÀM NÀY CHỈ BĂM `ltt.css`"* và ghi rằng lỗi đó **đã xảy ra**.
   Bỏ hẳn cơ hội mắc lại là rẻ hơn nhớ đừng mắc.

⇒ Toàn bộ kiểu VPS đi vào **một mục trong `ltt.css`**, và **mọi `<style>` nội
tuyến trong 5 template VPS bị rút hết về đó**. Ước lượng ~380 dòng, +0,25% kích
thước tệp.

### 4.2 Màu vận hành: thêm token `--vps-*`, KHÔNG đổi `MANIFEST.accent`

`MANIFEST.accent = "#0B7285"` là **màu của app trong catalog**; đổi nó là đổi thẻ
app trên trang chủ. Nhưng trên nền `--surface-raised: #151111`, `#0B7285` quá tối
để làm viền/chữ — ảnh dùng một sắc lam ngọc sáng hơn hẳn, và ảnh đúng ở điểm này.

```css
:root{
  --vps-teal:#0e8fa3;        /* nền nút vận hành */
  --vps-teal-hover:#12a7bd;
  --vps-teal-soft:#0a2a30;   /* nền ô đang chọn */
  --vps-teal-line:#146d7e;   /* viền */
  --vps-teal-text:#5ed4e6;   /* chữ lam ngọc trên nền tối */
}
```

**Ngữ pháp màu** (Prompt 00 §3), một luật cho cả 5 trang:

| Ý nghĩa | Token | Dùng ở |
|---|---|---|
| khoẻ / đang chạy | `--ok` `.b-ok` | badge `dang_chay` |
| hành động vận hành / đang chọn | `--vps-teal*` | nút Bật/Console/Tạo máy, thẻ gói đang chọn |
| đang tạo / sắp hết hạn / cần chú ý | `--warn` `.b-warn` | badge `dang_tao`, `con_ngay ≤ 3`, băng thông ≥ 80% |
| lỗi / phá huỷ | `--err` `.b-err` | badge `loi`, Danger Zone, băng thông ≥ 100% |
| đã tắt / không hoạt động | `--grey` `.b-grey` | badge `da_tat`, `bi_treo`, `da_xoa` |
| **thương hiệu LTT (đỏ)** | `--accent` | **chỉ** header/footer nền tảng — **không** dùng trong khu VPS |

⚠️ Màu **không bao giờ đứng một mình**: mọi badge mang chấm + chữ; mọi thẻ đang
chọn mang viền dày + nền, không chỉ đổi màu. Đây là luật đã có trong `ltt.css`
và trong `vps.html`; kế hoạch này chỉ mở rộng nó.

### 4.3 Nguồn chân lý cho trạng thái: mở rộng `apps/vps/nhan.py`

Hiện `nhan.py` chỉ trả **chữ**. Năm trang cần thêm **màu** và **hành động hợp lệ**,
và nếu mỗi template tự quyết thì năm trang sẽ nói năm câu khác nhau về cùng một máy.

```python
# apps/vps/nhan.py  (mở rộng, không đổi hàm cũ)
BADGE = {                      # mã CSDL → class badge
    "dang_tao": "b-warn", "dang_chay": "b-ok", "da_tat": "b-grey",
    "bi_treo": "b-warn",  "loi": "b-err",     "da_xoa": "b-grey",
}
BUOC_TIEP = {                  # mã → câu "giờ làm gì"
    "dang_tao": N_("Máy đang được tạo. Tải lại trang sau vài phút."),
    "bi_treo":  N_("Hết hạn thanh toán. Nạp credit để dùng lại."),
    ...
}
SU_KIEN = {                    # loai sự kiện → câu người đọc  (ảnh 3)
    "tao_moi": N_("VPS được tạo"), "thu_phi": N_("Đã thu phí chu kỳ"),
    "bat": N_("Máy được bật"),     "tat": N_("Máy được tắt"),
    "khoi_phuc": N_("Khôi phục về ảnh chụp"), ...
}
```

`BUOC_TIEP` và `BADGE` **đọc từ cùng một chỗ với `TRANG_THAI`**, nên một trạng thái
mới thêm vào CSDL mà quên khai ở đây sẽ bị một phép kiểm bắt (`test_306` ở §5.1).

Còn **hành động nào hợp lệ ở trạng thái nào** thì **không** khai lại ở đây:
`dieu_khien.kiem_dieu_khien_duoc()` đã là nguồn chân lý. Template hỏi nó, không tự
suy — nếu không, dải nút sẽ mời khách bấm một thứ máy chủ sẽ từ chối.

### 4.4 Macro dùng chung: `server/templates/_vps_mac.html`

Prompt 00 §8 cấm dựng framework component. Chỉ **những gì thật sự lặp ở ≥ 2 trang**:

| Macro | Dùng ở | Vì sao phải chung |
|---|---|---|
| `dinh_may(may, plan, os, dia_chi, …)` | C, D, E | Ba trang cùng hiện **một** danh tính máy. Ba bản sao sẽ lệch, và cái lệch là cái nói sai địa chỉ |
| `badge_trang_thai(ma)` | B, C, D, E | Bốn trang, một ngôn ngữ trạng thái |
| `the_goi(...)` | A, B | **đã có** trong `vps.html` — chuyển ra tệp macro |
| `o_sao_chep(nhan, gia_tri)` | B, C, D | hàng nhãn/giá trị + nút chép |
| `do_bang_thong(bt)` | B, C | một công thức %, một ngưỡng cảnh báo |
| `khoi_ma(chu)` | D, (E) | `<pre><code>` + `sao_chep.js` |

Không macro cho: hero, danger zone, stepper, console toolbar — mỗi thứ chỉ ở
**một** trang, và một macro dùng một lần là một tầng gián tiếp không đổi lại gì.

---

## 5. Kế hoạch thi hành — tám đợt, theo đúng thứ tự phụ thuộc

Mỗi đợt là **một ranh giới hoàn tác**: gate xanh + kiểm bằng trình duyệt xong thì
commit, rồi mới sang đợt sau. Không gộp hai đợt vào một commit.

### Đợt 1 — Nền trình bày dùng chung *(không đổi trang nào nhìn thấy được)* ✅ **XONG 2026-08-26**

| Việc | Tệp | Trạng thái |
|---|---|---|
| 1.1 Mục `/* LỚP NGỮ NGHĨA CỦA KHU VPS */` + token `--vps-*` | `server/static/ltt.css` (+126 dòng) | ✅ |
| 1.2 Rút **mọi** `<style>` nội tuyến của template VPS về mục đó | `vps.html` (2 khối), `vps_chi_tiet.html` (1 khối) | ✅ |
| 1.3 Mở rộng `nhan.py`: `BADGE`, `BUOC_TIEP`, `SU_KIEN`, `SU_KIEN_XAU` + 5 hàm tra | `apps/vps/nhan.py` | ✅ |
| 1.4 ~~Tạo `_vps_mac.html`~~ | — | ⏭️ **HOÃN sang Đợt 3** — xem ghi chú |
| 1.5 Sửa dòng sai trong `CLAUDE.md` (§0.1) | `CLAUDE.md` | ✅ |
| 1.6 **D-04a** · chụp `bang_thong_byte` vào sự kiện `thu_phi` trước khi đặt lại | `apps/vps/services/billing.py` | ✅ |
| 1.7 **D-04b** · bỏ `anh_chup` khỏi `SAP_CO_MAY` | `apps/vps/nav.py` | ✅ |
| 1.8 22 chuỗi mới dịch sang EN, sửa tay `.po` | `locale/en/.../messages.po` | ✅ |
| 1.9 Công cụ dựng cảnh để soi bằng trình duyệt (§6.1) | `tools/vps_dung_mau.py` | ✅ |
| 1.10 14 phép kiểm mới + đổi nguồn fixture `kieu` của `test_304` | `tests/test_311_vps_giao_dien_mvp.py` | ✅ |

**⏭️ Vì sao hoãn `_vps_mac.html`.** Sáu macro ở §4.4 đều **chưa có người dùng thứ
hai** cho tới Đợt 3–5; `the_goi` thì dùng hai lần nhưng **cả hai đều trong
`vps.html`**, nên đưa nó ra một tệp riêng chỉ thêm một tầng gián tiếp. Tạo một
tệp macro rỗng-nghĩa ở Đợt 1 là thêm **mã chết** vào đúng đợt mà tiêu chí là
"không đổi gì". Tệp sinh ra ở Đợt 3, khi `dinh_may` có người dùng thứ hai thật.

#### Bằng chứng — đo bằng Chrome thật, so với trang production

Refactor là **no-op có chứng minh**: cùng con số đo trên
`https://app.lttstudios.com/vps` trước khi sửa.

| Đo · ẩn danh | Production (trước) | Sau Đợt 1 |
|---|---|---|
| `document.body.scrollHeight` @390 | 2197 | **2197** |
| Giá gói đầu tiên (`.goi-gia` y) @390 | 1378 | **1378** |
| `scrollWidth` / `innerWidth` @390 | 390 / 390 | **390 / 390** |
| `main h1` | 1 | **1** |
| Thẻ gói | 3 | **3** |
| `getComputedStyle('.btn-goi').backgroundColor` | `#0B7285` | **`rgb(11,114,133)`** = `#0B7285` |
| `.goi-the` display | flex | **flex** *(bẫy ① không tái diễn)* |
| `.vps-the` display *(trang tạo máy)* | block | **block / none** *(đúng bộ lọc)* |
| Khối `<style>` trong template VPS | 3 | **0** |

#### 🔴 Hai lỗi tự gây ra trong đợt này, và cả hai đều chỉ thấy được bằng trình duyệt

**(a) Nút vận hành đổi sang MÀU ĐỎ.** `_kieu_chung.html` là một khối `<style>`
**nội tuyến trong `<head>` của `base.html`, đứng SAU thẻ `<link>` tới
`ltt.css`**, và nó khai `button, .btn { background: var(--accent) }`. Cùng độ
đặc hiệu (0,1,0) nhưng **đến sau** ⇒ nó thắng `.btn-goi` viết trong `ltt.css`.

> ⭐ Đó chính là lý do bản cũ đặt `.btn-goi` trong `<style>` của template — khối
> ấy đứng sau `_kieu_chung.html` nên thắng. Chuyển sang `ltt.css` mà giữ nguyên
> độ đặc hiệu là làm sống lại **đúng lỗi ④** mà đợt 25/08 vừa sửa. Đo được:
> `backgroundColor == rgb(239,55,49)` = `--brand-primary`.
> Sửa bằng `.btn.btn-goi` (0,2,0). Chốt bằng phép kiểm — và phép kiểm đó **kiểm
> luôn rằng cái bẫy còn tồn tại**, để nó tự vô hiệu khi `_kieu_chung.html` đổi.

**(b) Công cụ mới dính đúng quy tắc 6.** Sửa `ltt.css`, dựng lại, đo lại — Chrome
vẫn trả **màu cũ**, vì URL `static/ltt.css` không đổi. Suýt kết luận *"luật CSS
mới không thắng được độ đặc hiệu"*, trong khi luật mới **còn chưa tới trình
duyệt**. Cùng bệnh với cái bẫy Cloudflare đã cắn production một lần; cùng thuốc:
`tools/vps_dung_mau.py` nay đính hash nội dung vào URL tệp tĩnh.

**(c) Ba lần phép kiểm khớp vào chính chú thích của tôi**, gồm một biến thể mới:
cắt lát CSS **từ chính cái mốc** thay vì từ `/*` **mở khối chứa mốc** — lát cắt
bắt đầu giữa một chú thích đang mở, nên bộ bóc ghép lệch một nhịp và **bóc mã,
giữ chú thích**. Đúng ngược điều nó sinh ra để làm.

**⚠️ Cây kho đang có phiên Claude khác làm việc song song** (cổng lập trình
viên: `server/templates/developers_base.html`, `server/routes/developer/_chung.py`,
`docs/PUBLIC_API/CONTRACT_BASELINE.json`). Hai phiên **cùng sửa `ltt.css`** —
không đè nhau vì hai mục nằm ở hai chỗ, nhưng `tools/gui/ltt.css` và
`ho_so_he_thong.txt` là tệp **dẫn xuất** nên phải sinh lại ở phút cuối, không
phải giữa đợt. `tools\gate.py` hiện đỏ ở **4 phép kiểm của phiên kia**
(7 chuỗi EN chưa dịch trong `developers_base.html` + `CONTRACT_BASELINE.json`);
đã xác minh baseline sạch bằng `git stash` — **không phải do đợt này**.

### Đợt 2 — Màn A · Storefront *(ảnh 1)*

Trang này **đã 8,2/10**; đợt này là nâng thị giác, không phải cứu hoả.

| Việc | Từ ảnh | Nguồn dữ liệu |
|---|---|---|
| 2.1 Hero hai cột: trái là lời chào + "chỉ từ 149.000đ", phải là hình khối Windows **vẽ bằng CSS/SVG nội tuyến** | ảnh 1 | *(trang trí, không dữ liệu)* |
| 2.2 Dải 6 chip đặc điểm dưới hero | ảnh 1 | 6 câu **kiểm chứng được** (§2.3), **không** SLA/24-7/NVMe |
| 2.3 Nâng thẻ gói: icon, chip thông số (vCPU/RAM/đĩa/băng thông) thành ô riêng, giá to, nút riêng | ảnh 1 | `cost.PLANS` — tên, giá, thông số, `mo_ta`, `nen_chon` |
| 2.4 Cột phải 4–6 thẻ đặc điểm | ảnh 1 | **thay** "Hỗ trợ 24/7"/"NVMe" bằng: tự đặt mật khẩu · tạo ~20 giây · console cứu hộ · không hợp đồng |
| 2.5 "Điều cần biết trước khi thuê" thành lưới 6 ô có icon | ảnh 1 | ⚠️ **giữ NGUYÊN VĂN** 6 dòng — `test_298` đối chiếu từng con số |
| 2.6 Thẻ CTA cuối "Sẵn sàng bắt đầu?" | ảnh 1 | `/register` + `/login?next=/vps` |
| 2.7 Nav ngang trong trang (Tính năng · Hạ tầng · Hướng dẫn · FAQ) | ảnh 1 | ⚠️ **chỉ** là mỏ neo tới mục **có thật** trên trang. Không tạo trang mới |
| 2.8 ❌ **Bỏ** dải tin cậy cuối trang trong ảnh | — | cả 4 mục đều là lời hứa ta không có |

**Đạt khi:** giá vẫn trên màn hình đầu ở 390 (`y < 844`); 0 tràn ngang ở 6 bề
ngang; `test_252` + `test_298` + `test_304` + `test_305` xanh; ảnh chụp Chrome
thật ở **1920/1440/1280/1024/768/390**.

### Đợt 3 — Màn B · Nhà của khách + Tạo máy *(ảnh 2)*

| Việc | Nguồn |
|---|---|
| 3.1 Bốn ô chỉ số Tổng · Đang chạy · Đã tắt · Sắp hết hạn, dùng `.chi-so-luoi` | đếm từ `may_cua_toi` trong **route**, không đếm trong template |
| 3.2 Bảng 7 cột → **thẻ máy**: logo OS, tên + badge, IP + nút chép, gói/vCPU/RAM/đĩa, băng thông có đo, "Gia hạn: dd/mm (còn N ngày)", nút `Quản lý` · `Console` | `_may_cua_toi()` — đã trả đủ, **không thêm truy vấn** |
| 3.3 `Console` **mờ đi** khi `kiem_dieu_khien_duoc()` từ chối | `dieu_khien` |
| 3.4 Trạng thái rỗng (0 máy): một thẻ mời tạo máy đầu tiên | — |
| 3.5 Cột phải "Tạo VPS mới" 3 chặng đánh số **trong cùng một `<form>`** | giữ nguyên POST `/vps/tao`, CSRF, hidden `vung` |
| 3.6 Ô "Tổng quan thanh toán": sẽ trừ · số dư · còn lại sau khi tạo | **đã có** — chỉ nâng thị giác |
| 3.7 Ba thẻ thông tin dưới cùng | ⚠️ bỏ mệnh đề *"Hệ thống sẽ gửi thông báo khi sẵn sàng"* — **không có thông báo nào** |
| 3.8 ❌ Bỏ: chuông thông báo, chip nhóm, sắp xếp, chuyển lưới/danh sách, ETA "2–5 phút", IP nội bộ | §2.1 |

**12 trạng thái phải dựng và soi bằng mắt** (Prompt 02): 0 máy · 1 máy chạy ·
nhiều máy · đang tạo · đã tắt · bị treo · lỗi · sắp hết hạn (≤3 ngày) · băng thông
bị hãm · hết sức chứa · gói đã chọn hết chỗ · thiếu credit.

⚠️ **Không có máy thật nào trong CSDL** (4 bảng `vps_*` về 0 dòng sau đợt dọn
25/08). ⇒ dựng bằng **đồ gá**, xem §6.

### Đợt 4 — Màn C · Trung tâm điều khiển *(ảnh 3)* — **đợt nặng nhất**

Trang hiện tại là 4 bảng nhãn/giá trị xếp dọc trong 940px. Ảnh là một control
center. Đây là nơi chênh lệch lớn nhất giữa ảnh và live.

| Việc | Ghi chú |
|---|---|
| 4.1 **Đầu trang danh tính**: logo OS · tên · badge · IP công khai + chép · OS · gói · mã máy | macro `dinh_may` (dùng lại ở D, E) |
| 4.2 **Dải hành động theo trạng thái** — không bày mọi nút ngang hàng | `dang_chay` → Console (chính) · Khởi động lại · Tắt máy · Cài Windows<br>`da_tat` → **Bật** (chính) · Console<br>`dang_tao` → chỉ thông tin, không nút<br>`bi_treo` → hướng dẫn nạp credit<br>`loi` → `may.ly_do` + đường phục hồi |
| 4.3 Lưới 4 ô: **Tài nguyên · Thanh toán · Băng thông · Ảnh chụp** | bỏ "1 Gbps"; bỏ nút "Gia hạn ngay"; sửa "hằng ngày"→**"hằng tuần, giữ 1 bản"** |
| 4.4 Ô **Thông tin truy cập** | RDP endpoint + chép · `mstsc /v:<ip>` + chép · liên kết Console + Cài Windows<br>🔴 **thay hàng Password** bằng câu: *"Mật khẩu là của bạn — chúng tôi không giữ bản nào và không đặt lại được."* |
| 4.5 **Sao kê thanh toán** giữ nguyên | điều khoản hứa nó; ảnh quên nó |
| 4.6 **Nhật ký** thành dòng thời gian có chấm màu + nhãn người đọc | `nhan.SU_KIEN`; **không** đổ JSON thô |
| 4.7 **Danger Zone** thành 3 thẻ trong một khung đỏ, thứ tự **ít thiệt hại trước**: Khôi phục → Cài lại → Xoá | ⚠️ **giữ ô gõ tên máy** ở cả ba — ảnh bỏ mất nó, và ảnh sai |
| 4.8 ❌ Bỏ cột trái "SLA/hỗ trợ/NVMe/Liên hệ hỗ trợ" | §2.1 |
| 4.9 Bỏ trần `max-width:940px` cho các ô lưới; giữ trần đọc cho khối văn xuôi | — |

**Trạng thái phải soi:** `dang_tao` · `dang_chay` · `da_tat` · `bi_treo` · `loi` ·
sắp hết hạn · băng thông bị hãm · có/không ảnh chụp · có/không sao kê · sự kiện có
`chi_tiet` dài · 390px.
**Hồi quy an ninh:** máy người khác → 404; POST thiếu CSRF → chặn; gõ sai tên →
từ chối.

### Đợt 5 — Màn D · Cài Windows *(ảnh 4)*

| Việc | Ghi chú |
|---|---|
| 5.1 Dải danh tính máy (macro `dinh_may`) | thống nhất với C và E |
| 5.2 Bố cục hai cột: **cột bước** bên trái, **nội dung** bên phải | 390px: cột bước lên **trên** |
| 5.3 Gộp 10 `<li>` hiện tại về **8 bước** khớp Prompt 04 | Mở Console → Chọn phiên bản → Chọn ổ đĩa → Chờ khởi động lại → Đặt mật khẩu → Bật RDP → Gỡ đĩa cài → Nối bằng RDP |
| 5.4 Bước 2 (Desktop Experience vs Core) **chỉ hiện khi** `os.id.startswith("winsrv")` | ⚠️ live đã đúng — giữ điều kiện |
| 5.5 Khối **QUAN TRỌNG** "Press any key to boot from CD or DVD…" thành callout nổi bật | ⚠️ **nguyên văn**, kể cả câu *"Bấm vào đó là quay lại đầu trình cài đặt"* |
| 5.6 `<pre>` PowerShell bật RDP có nút chép | bảo đảm `sao_chep.js` được nạp trên trang này |
| 5.7 Nút "Mở Console ở tab mới" thành CTA chính góc trên | live đã có `target="_blank"` |
| 5.8 Nút cuối "Tôi đã cài xong — gỡ đĩa cài" | ⚠️ giữ là **POST có CSRF**, giữ nguyên chữ nói rõ **bấm SAU KHI cài xong** |
| 5.9 Cột bước dùng mỏ neo + đánh dấu mục đang xem | ❌ **không** "3/8", ❌ **không** dấu tích lưu được, ❌ **không** "Tôi đã hoàn tất bước này" |
| 5.10 ❌ Bỏ "Gặp sự cố? Tạo ticket hỗ trợ 24/7" | không có hệ thống ticket |
| 5.11 ⏸️ **Hoãn** ảnh chụp màn hình trình cài Windows | cần tài sản ảnh chưa có; ghi vào backlog |

### Đợt 6 — Màn E · Console *(ảnh 5)* — **nhạy cảm an ninh nhất**

⛔ Đợt này **chỉ đổi trình bày**. Không chạm: cấp vé, tiêu vé, đường WebSocket,
mật khẩu VNC, `scaleViewport`, `resizeSession=false`, hành vi không-tự-nối-lại.

| Việc | Ghi chú |
|---|---|
| 6.1 Dải danh tính máy + câu "Console để cứu hộ, RDP để làm việc hằng ngày" | live đã có câu đó |
| 6.2 Thanh công cụ gọn: `Ctrl+Alt+Del` · `Kết nối lại` · `Toàn màn hình` · `Về trang máy` | Toàn màn hình = `requestFullscreen()`, API trình duyệt, ~8 dòng |
| 6.3 Khung VNC là **trung tâm thị giác** — bỏ lớp thẻ bọc thừa, cao `min(78vh, …)` | giữ `tabindex="0"` và `khung.focus()` — thiếu nó là "gõ không lên chữ" |
| 6.4 Trạng thái kết nối thành badge: Đang kết nối / Đã kết nối / Đã ngắt / Lỗi | ánh xạ **đúng** 3 sự kiện RFB đang có: `connect`, `disconnect` (clean/không), `securityfailure` |
| 6.5 Cột phải "Khi nào dùng Console / Khi nào dùng RDP" + mẹo | live đã có nội dung, đang ở dạng một đoạn |
| 6.6 Ô "Phiên truy cập một lần" — **giữ chữ, bỏ đồng hồ** | vé **là** một lần (đúng), nhưng **không có hạn sau khi nối** (§2.1 #3) |
| 6.7 ⏸️ Hoãn "Gửi phím tắt" (`rfb.sendKey`) | bộ noVNC kèm theo **có** hỗ trợ, nhưng Prompt 05 nói hoãn nếu chưa test được thật |
| 6.8 ❌ Bỏ: AES-256 · đếm ngược · trình duyệt · IP khách · khu vực | §2.1 |

⚠️ **Bằng chứng.** Không có Proxmox trong môi trường kiểm thì **không được gọi
PASS thị giác cho phần đã-kết-nối**. Phân biệt rõ: bố cục/thanh công cụ/trạng thái
lỗi **kiểm được** bằng đồ gá; còn gõ phím, chuột, Ctrl+Alt+Del, ngắt–nối lại thì
phải có máy thật (xem §6.2).

### Đợt 7 — Cổng liên trang *(Prompt 06)*

1. **Đối chiếu 5 màn**: vỏ, chữ, khoảng cách, bo góc, badge, teal vận hành, đỏ phá
   huỷ, tên máy, nhãn trạng thái, cách viết IP, cách viết hạn thanh toán, đơn vị
   băng thông, từ "ảnh chụp", tên nút.
2. **5 hành trình vàng** GJ1–GJ5 (§6.2).
3. **Hồi quy an ninh** — 11 mục ở §3.
4. **Ma trận trình duyệt** 1920/1440/1280/1024/768/390 × 11 trạng thái.
5. **Soát phình phạm vi**: liệt kê mọi thứ thêm vào trong đợt 2–6 mà 5 hành trình
   không cần → gỡ hoặc hoãn.
6. Viết `14_VPS_UI_CONTRACT_FINAL.md` + `15_FINAL_MVP_REPORT.md`.

### Đợt 8 — Deploy

⚠️ `/vps` đang bán hàng. Deploy chép **cả cây** `app\` — không tách được phần của
một phiên. Trước khi chạy: `git status` sạch · gate xanh · `alembic head` khớp ·
hỏi các phiên Claude khác (`ListAgents`) · và **kiểm lại trên URL công khai**, vì
loopback bỏ qua Cloudflare (quy tắc 5b).

---

## 6. Làm sao kiểm được khi trong CSDL không có máy nào

Đây là ràng buộc lớn nhất của cả kế hoạch, và nó phải giải trước đợt 3.

**Sự thật:** sau đợt dọn 25/08, 4 bảng `vps_*` về **0 dòng**, 0 VM, 0 Reserved IP.
Ba trang C · D · E **không mở được** nếu không có một máy.

### 6.1 Đường chính — dựng HTML từ đồ gá, đo bằng Chrome thật

```
tools/vps_dung_mau.py     # render 5 template với dữ liệu giả cho N trạng thái
   → scratchpad/vps_mau/{man}_{trang_thai}.html
   → playwright-cli goto file:///…  → chụp + đo getBoundingClientRect
```

Dùng `TemplateResponse` thật (đúng `ltt.css`, đúng `asset_ver`, đúng i18n), chỉ
thay nguồn dữ liệu. Đây là **bằng chứng E2 thật**: bố cục, tràn ngang, tương phản,
reflow ở 6 bề ngang, 12 trạng thái — không tốn một đồng, không chạm production.

⛔ Nó **không** chứng minh được: WebSocket console, luồng POST, hành vi thật của
job. Phải nói rõ trong báo cáo, không được gọi là PASS đầy đủ.

### 6.2 Đường phụ — **một** máy thật, ở cuối, có chủ sản phẩm đồng ý

Năm hành trình vàng GJ2–GJ5 chỉ chứng minh được bằng một máy thật. Đề xuất:
tạo **một** máy gói Nhỏ (149.000đ ≈ 1.490 credit) trên tài khoản thử, đi hết
`tạo → chờ → console → cài → gỡ đĩa → tắt/bật → khôi phục → xoá`, rồi xoá.

⚠️ **Hai rủi ro đã biết:** hạn ngạch Reserved IP của Vultr đếm **cả IP vừa xoá**,
nên tạo/xoá liên tục sẽ làm lượt sau hỏng ở mốc 92%; và bút toán credit là
append-only nên tài khoản thử **vô hiệu hoá chứ không xoá**.

⇒ **Đây là hành động không đảo được trên hạ tầng đang trả tiền. Chủ sản phẩm
quyết, không phải một phiên Claude.** Đợt 1–7 chạy được đầy đủ mà không cần nó.

---

## 7. Quyết định cần chủ sản phẩm

| # | Việc | Vì sao là quyết định, không phải lựa chọn kỹ thuật |
|---|---|---|
| **D-01** | **Đặt tên máy.** Cột `VpsInstance.ten` có thật, `nav.py` hiện nó, ba ô xác nhận phá huỷ đòi gõ nó — nhưng **không có đường nào đặt nó**. Thực tế khách đang phải gõ `may.id[:8]`, một chuỗi hex 8 ký tự | Sửa nó là **thêm một trường vào biểu mẫu tạo máy** + một POST đổi tên. Prompt Pack cấm thêm tính năng trong đợt trình bày. Nhưng ảnh 2/3/4/5 đều xoay quanh tên máy, và `docs/VPS/GIAO_DIEN.md` đã vẽ ô "Tên máy" từ đầu — **nó bị bỏ sót, không bị bỏ đi**. Đề xuất: **làm**, nhưng thành một đợt riêng sau đợt 7 |
| **D-02** | **Máy thật cho GJ2–GJ5** (§6.2) | Không đảo được, trên hạ tầng đang trả tiền |
| **D-03** | Ảnh chụp màn hình trình cài Windows cho màn D (5.11) | Cần tự chụp trên một máy thật ⇒ phụ thuộc D-02 |
| **D-04** | Mở route `Ảnh chụp` và `Băng thông` (đang là "sắp có" trong `nav.py`) | Ảnh 3 có nút cho cả hai. Đây là **tính năng mới**, ngoài MVP trình bày |

---

## 8. Phép kiểm mới sẽ viết

Đặt ở `tests/test_306_vps_giao_dien_mvp.py`. Nguyên tắc từ `test_304`: **chốt
nguyên nhân, không giả vờ chốt kết quả** — ba lỗi nặng nhất của đợt 25/08 đều
không bắt được bằng cách đọc HTML.

| Phép kiểm | Chốt điều gì |
|---|---|
| `test_moi_ma_trang_thai_deu_co_BADGE_va_BUOC_TIEP` | thêm trạng thái mà quên khai màu ⇒ đỏ |
| `test_nam_trang_dung_CHUNG_mot_nguon_nhan_trang_thai` | không template nào tự viết chữ trạng thái |
| `test_ba_trang_trong_mot_may_dung_CHUNG_macro_dinh_may` | tên/IP/OS không bị format ba kiểu |
| `test_KHONG_template_nao_con_the_style_noi_tuyen` | bánh cóc cho §4.1 |
| `test_KHONG_hua_SLA_ho_tro_247_NVMe_tren_moi_trang_VPS` | mở rộng `test_298` ra cả 5 trang; ⚠️ **bóc chú thích trước khi khẳng định** (bẫy đã dính 4 lần) |
| `test_KHONG_co_o_mat_khau_tren_trang_may` | chốt §2.1 #1 |
| `test_console_KHONG_hua_thuat_toan_ma_hoa_va_KHONG_dem_nguoc` | chốt §2.1 #2, #3 |
| `test_anh_chup_noi_dung_HANG_TUAN_khop_sao_luu_GIU` | đối chiếu chữ với `sao_luu.GIU` |
| `test_khong_co_nut_nao_tro_toi_route_khong_ton_tai` | quét `href`/`action` trong 5 template so với bảng route thật |
| `test_dai_hanh_dong_chi_hien_viec_dieu_khien_duoc_cho_phep` | chốt §5 đợt 4.2 |
| `test_moi_asset_tinh_moi_deu_nam_trong_TAI_SAN_CO_VERSION` | chốt bẫy cache-bust §4.1 |
| `test_khong_con_class_vua_la_KIEU_vua_la_MOC_JS` | mở rộng `test_304` ra 5 trang |

Chạy: `python tools\test_nhanh.py --lf` sau mỗi lần sửa; `python tools\gate.py`
trước khi báo xong. ⛔ Không gọi `python -m pytest` cho cả kho.

---

## 9. Thứ tự đọc cho phiên sau

1. Tài liệu này.
2. `docs/VPS/AUDIT_GIAO_DIEN_2026-08-25.md` — vì sao trang bán đang như hiện tại.
3. `docs/VPS/GIAO_DIEN.md` — chốt "không cloud, không SLA, không unlimited".
4. `docs/VPS/PHAN_TICH_VPS_PROXMOX.md` — trần công suất, vì sao ba gói.
5. `apps/vps/cost.py` + `os_images.py` — **nguồn chân lý duy nhất** cho giá và cấu hình.
6. Bộ prompt gốc: `G:\My Drive\AI\A\New folder (5)\LTT_VPS_MVP_UI_Prompt_Pack_V2\`.

---

## 10. Tóm tắt một câu

Năm ảnh vẽ đúng **hình dạng** mà khu VPS cần, và vẽ sai **mười lăm lời hứa** mà
sản phẩm này cố ý không hứa. Kế hoạch này lấy hết phần hình và bỏ hết phần hứa,
theo tám đợt có ranh giới hoàn tác — bắt đầu từ một nền trình bày dùng chung, để
năm trang trở thành **một sản phẩm** chứ không phải năm template độc lập.
