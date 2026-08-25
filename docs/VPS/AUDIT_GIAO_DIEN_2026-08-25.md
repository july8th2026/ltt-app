# Audit giao diện `/vps` — chấm điểm và phương án lên MVP

**2026-08-25.** Theo yêu cầu chủ sản phẩm: *phân tích sâu giao diện `/vps`, mở
Chrome kiểm giao diện thực tế, đối chiếu các trang cùng chức năng trên thế giới,
đưa ra phương án nâng cấp giao diện và chức năng lên MVP thực sự.*

> **Cách đo.** Chrome thật (`playwright-cli --browser=chrome`), hai bề ngang
> **1440×900** và **390×844**, ở **cả hai tư cách người xem** (ẩn danh và đã
> đăng nhập), trên máy chủ đọc được sức chứa Proxmox thật. Mọi con số dưới đây
> lấy từ `getBoundingClientRect` / `getComputedStyle` của trang đang chạy —
> không đọc template rồi suy ra. Đó là điều kiện: bản kiểm trước của tôi chỉ
> đọc cây trợ năng, và **cây trợ năng không có bố cục**, nên nó bỏ sót đúng lỗi
> nặng nhất ở mục 4.1.

---

## 1. Những gì đã ĐÚNG

Ghi trước, vì phần lớn trang này tốt và phương án nâng cấp phải giữ chúng.

| Đo | Kết quả |
|---|---|
| Tràn ngang ở 390px | **không** (`scrollWidth == innerWidth == 390`) |
| Bảng tràn ở mobile | **không** |
| Lỗi console | **0** |
| Request hỏng | **0** |
| Biểu mẫu POST thiếu CSRF | **0** |
| Fail-closed khi không đọc được sức chứa | **đúng** — bảng giá chỉ đọc, không dựng `<form>` |
| Clickwrap điều khoản ngay dưới nút | **có** |
| Tóm tắt sống (giá · số dư · còn lại) | **có**, cập nhật đúng |

**Trang tạo máy (đã đăng nhập) tốt hơn hẳn trang bán (ẩn danh).** Đó là một
nghịch lý cần sửa: trang tốt hơn là trang chỉ người **đã trả tiền** mới thấy.

---

## 2. Đối chiếu bốn trang cùng chức năng

Soi bằng Chrome thật, 25/08.

### Contabo — `contabo.com/en/vps`

```
Hero: "The Best Value Cloud VPS on Earth"
      Free Firewall & DDoS Protection · Unlimited Traffic · 99.9% Uptime
Bảng: gói là CỘT, mỗi cột có GIÁ + nút "Get Started" riêng
Hàng: Cores · Memory · Storage · Snapshots · Port Speeds · Traffic
Dưới: "VPS for Web Hosting and CMS" — hướng dẫn chọn theo VIỆC
```

### Hetzner — `hetzner.com/cloud`

```
Hero: một câu + MỘT nút "Create cloud instance"
4 ô lợi ích: Price calculator · Made in Germany/GDPR · Features · Simple to use
Chọn gói đóng khung thành CÂU HỎI:
  "WHICH HETZNER CLOUD SERVER IS RIGHT FOR YOU?"
  Shared Resources   — "Perfect for test environments"
  Cost-Optimized     — "Low CPU usage, medium traffic applications"
```

### AZDIGI · Tino Group (thị trường Việt)

```
Dải tin cậy: 99.9% Uptime · Datacenter tại Việt Nam · Sao lưu & bảo mật · Hỗ trợ 24/7
Số liệu xã hội: 10+ năm · 80K+ khách hàng · 600K+ websites
Giá nêu theo quy ước: "Giá chỉ từ: 99.000 đ/tháng"
Băng rôn khuyến mãi có đồng hồ đếm ngược
```

### Ba ý CHUYỂN được, một ý KHÔNG

| Ý | Chuyển được? |
|---|---|
| **Giá + nút riêng cho từng gói** (Contabo) | ✅ ta đang là bảng trơ, 0 nút |
| **Mô tả gói theo AI HỢP DÙNG, không chỉ theo thông số** (Hetzner) | ✅ ta **đã có** `mo_ta`, chỉ là giấu trong biểu mẫu |
| **Giá nêu "chỉ từ …đ/tháng" nổi bật** (quy ước VN) | ✅ ta chôn giá dưới hai thẻ |
| **Dải tin cậy uptime / SLA / hỗ trợ 24-7 / sao lưu** | 🔴 **KHÔNG** |

🔴 **Vì sao ý thứ tư không chuyển được, và vì sao đó là điều quan trọng nhất
trong bản audit này.**

Cả bốn đối thủ đều bán trên cùng một trục: *uptime cao, sao lưu, hỗ trợ 24/7*.
Ta **cố ý không hứa cả ba** — `docs/VPS/GIAO_DIEN.md` đã chốt *"không dùng chữ
cloud, không giới hạn, 99,9% uptime — ta không có SLA, và một câu quảng cáo sai
là một vụ tranh chấp về sau."*

Nên trang này **không thể thắng trên trục của họ**, và mọi phương án "làm cho
giống Contabo hơn" đều sai hướng. Nó phải thắng trên một trục khác, và ta thật
sự có một trục khác — chỉ là **chưa nói ra**:

| Ta có thật | Đối thủ (ở tầm giá này) |
|---|---|
| **IP công khai riêng cho từng máy, dùng được mọi cổng** | thường NAT chia cổng |
| **Tạo xong trong ~17 giây** (đã đo) | vài phút tới vài giờ |
| **Trả bằng credit, không hợp đồng, xoá là dừng** | chu kỳ tháng, có ràng buộc |
| **Chúng tôi không bao giờ biết mật khẩu của bạn** | provider cấp mật khẩu |
| **Console trong trình duyệt khi RDP hỏng** | thường phải mở ticket |

Bốn dòng đầu **đang nằm trong trang** nhưng ở dạng câu văn trong một đoạn; dòng
thứ năm nằm trong một gạch đầu dòng. Không dòng nào được trình bày như một
**lý do mua**.

---

## 3. Chấm điểm 9 hạng mục

| # | Hạng mục | Điểm | Chặn ở đâu |
|---|---|---|---|
| A | Bố cục bước-2 của biểu mẫu tạo máy | **2/10** | JS làm **vỡ** bố cục ngay khi tải |
| B | Cấu trúc tài liệu (heading) | **3/10** | `<h1>` = **0** |
| C | Đường từ "đây là gì" tới "bao nhiêu tiền" | **4/10** | mobile: giá nằm dưới màn hình **277px** |
| D | Bảng giá như một công cụ quyết định | **4/10** | **0 nút**, 0 gợi ý nên chọn gói nào |
| E | Nói ra thứ ta thật sự hơn đối thủ | **3/10** | có trong câu văn, không có trong thiết kế |
| F | Bản tiếng Anh | **2/10** | pha trộn, cùng bệnh với khu API |
| G | Trợ năng (a11y) | **4/10** | `th scope` 0/4 · chữ phụ 12,6px |
| H | Lộ số liệu vận hành cho khách lạ | **3/10** | "Còn trống: 48.5 GB RAM · 186 GB đĩa" |
| I | Nền kỹ thuật (không tràn, không lỗi, fail-closed) | **9/10** | — |

**Trung bình 3,8/10.**

⚠️ Điểm thấp **không** vì trang xấu. Nội dung của nó trung thực và viết tốt hơn
phần lớn trang cùng loại. Nó thấp vì trang đang là **một tài liệu**, trong khi
việc của nó là **một trang bán hàng**.

---

## 4. Chi tiết bốn hạng mục nặng nhất

### 4.1 🔴 A — bước 2 của biểu mẫu VỠ BỐ CỤC, và đã vỡ từ khi G8 lên

Đo trên trang đang chạy:

```js
[...document.querySelectorAll('.vps-os')].map(o => getComputedStyle(o).display)
→ ["inline", "none", "inline", "none", "none"]
```

Nhãn chọn hệ điều hành khai `style="display:block; border:…; padding:…"` trong
template, nhưng JS lọc theo gói chạy dòng này:

```js
o.style.display = hop ? '' : 'none';
```

`''` **xoá** thuộc tính nội tuyến chứ không đặt lại giá trị — nên nhãn rơi về
mặc định của `<label>`, tức `inline`. Hệ quả: hai thẻ chọn hệ điều hành nằm đè
nhau trên một dòng, chiều rộng lệch (396px và 609px), viền và khoảng đệm mất
tác dụng.

**`capNhat()` được gọi ngay khi tải trang**, nên bố cục vỡ **ngay lập tức**,
không cần khách bấm gì.

⚠️ **Vì sao lần kiểm trước không thấy.** Tôi đọc cây trợ năng và HTML — cả hai
đều **đúng**: nhãn có mặt, chữ đúng, radio đúng. **Cây trợ năng không mang bố
cục.** Đúng thứ `CLAUDE.md` mục 5 đã cảnh báo: *"test xanh không chứng minh
trang hiển thị đúng"* — và một snapshot trợ năng xanh cũng không.

### 4.2 🔴 C — mobile: khách phải cuộn qua 6 dòng cảnh báo mới thấy giá

| Bề ngang | Cảnh báo ở y | Giá đầu tiên ở y | Màn hình | Giá trên màn hình đầu? |
|---|---|---|---|---|
| 1440×900 | 394 | 659 | 900 | ✅ vừa kịp |
| **390×844** | 594 | **1121** | 844 | 🔴 **thiếu 277px** |

Sáu dòng "Đọc trước khi thuê" là nội dung **đúng và bắt buộc** (điều kiện Q103,
số đo thật). Vấn đề không phải chúng tồn tại mà là **vị trí**: chúng đứng giữa
"đây là cái gì" và "bao nhiêu tiền".

Người chưa biết sản phẩm mà đọc sáu điều nó **không** hứa thì đóng tab. Người
đã biết giá và thấy nó hợp lý thì đọc hết sáu dòng — và **đó mới là lúc chúng
làm việc**, vì lúc đó chúng đang giúp khách quyết định chứ không đang cản.

### 4.3 🟡 D — bảng giá không giúp quyết định

```
nút trong bảng giá: 0
```

Ba hàng, bốn cột, không hàng nào có nút, không hàng nào được đánh dấu nên chọn.
Khách phải tự dịch "2 vCPU · 4 GB" thành "gói này hợp với tôi".

Mà **ta đã viết sẵn câu dịch đó**: `cost.py` có `mo_ta` cho từng gói —
*"Đây là gói phần lớn người dùng nên chọn"*, *"Hợp khi bạn chỉ cần một máy chạy
phần mềm hoặc script nền"*. Chúng chỉ hiện **bên trong biểu mẫu tạo máy**, tức
chỉ người **đã đăng nhập** đọc được. Người cần chúng nhất là người chưa đăng
nhập.

### 4.4 🟡 H — lộ số liệu vận hành cho khách lạ

```
Còn trống: 48.5 GB RAM · 186 GB đĩa
```

Dòng này nói với người lạ rằng cả hệ thống còn 186 GB đĩa. Không đối thủ nào
hiện con số này, và lý do không phải là giấu giếm: **đó là con số của người vận
hành, không phải của khách.** Khách cần biết *"gói tôi muốn còn chỗ không"* —
một câu trả lời có/không cho **gói họ đang xem**, không phải tổng tài nguyên.

Giữ nó cho người đã đăng nhập thì hợp lý (họ đang cân nhắc tạo máy thứ hai).

---

## 5. Phương án — bốn đợt, theo thứ tự

### V1 — sửa lỗi thật *(không đổi thiết kế gì)*

| # | Việc | Đạt khi |
|---|---|---|
| V1.1 | `o.style.display = hop ? 'block' : 'none'` — và bỏ style nội tuyến, chuyển sang class | `getComputedStyle` trả `block`, có test chốt |
| V1.2 | Thêm `<h1>` thật cho trang | `main h1` = 1 |
| V1.3 | `scope="col"` cho `<th>` bảng giá | 4/4 |
| V1.4 | Ẩn "Còn trống" khỏi khách ẩn danh | chỉ hiện khi `da_dang_nhap` |

V1.1 là **lỗi đang sống**, không phải cải tiến. Nó đứng đầu vì lý do đó.

### V2 — đảo thứ tự kể chuyện *(đổi vị trí, không đổi nội dung)*

```
Hôm nay:  giá trị → 6 cảnh báo → bảng giá
Phải là:  giá trị + GIÁ TỪ …đ/tháng → bảng giá → 6 cảnh báo → CTA
```

| # | Việc | Đạt khi |
|---|---|---|
| V2.1 | Đưa "chỉ từ **149.000đ**/30 ngày" lên khối mở đầu | mobile: giá trên màn hình đầu |
| V2.2 | Bảng giá lên **trước** khối cảnh báo | `gia_y < canhbao_y` ở cả hai bề ngang |
| V2.3 | Giữ nguyên **toàn văn** 6 dòng cảnh báo | `test_298` vẫn xanh (nó đối chiếu từng con số) |

⚠️ V2.3 là ràng buộc, không phải việc: **không được rút gọn cảnh báo để trang
gọn hơn.** Chúng là điều kiện Q103 và có test đối chiếu từng con số.

### V3 — biến bảng giá thành công cụ quyết định

| # | Việc | Đạt khi |
|---|---|---|
| V3.1 | Mỗi gói một nút riêng (`/vps` → biểu mẫu đã chọn sẵn gói đó, hoặc `/login?next=`) | ẩn danh và đã đăng nhập đều tới đúng chỗ |
| V3.2 | Đưa `mo_ta` của gói ra **bảng giá công khai** (đang chỉ có trong biểu mẫu) | ba dòng mô tả hiện cho khách ẩn danh |
| V3.3 | Đánh dấu **VPS Vừa** là gói nên chọn — `cost.py` đã nói vậy bằng chữ | có chỉ dấu thị giác + `aria-label`, không chỉ màu |
| V3.4 | Thay "Còn trống: …" bằng trạng thái **theo từng gói** (còn chỗ / hết chỗ) | khách biết gói mình muốn có tạo được không |

### V4 — nói ra thứ ta thật sự hơn

Năm điểm ở mục 2 đang nằm trong câu văn. Đưa chúng thành một dải bốn ô ngay
dưới tiêu đề — **đúng vị trí đối thủ đặt dải "99.9% uptime"**, nhưng nói thứ ta
kiểm chứng được:

```
IP riêng, mọi cổng   ·   Tạo xong ~17 giây   ·   Không hợp đồng   ·   Ta không biết mật khẩu của bạn
```

⚠️ **"~17 giây" là số đo thật** (G-series, đo trên cụm này). Nếu có ngày nó
không còn đúng thì phải bỏ khỏi trang — một con số đo được hôm qua vẫn là một
lời hứa hôm nay.

---

## 6. Cái **không** làm

| Không làm | Vì sao |
|---|---|
| Dải tin cậy kiểu "99.9% uptime · hỗ trợ 24/7 · sao lưu" | ta **không có** cả ba; chép chúng là quảng cáo sai |
| Số liệu xã hội ("80K+ khách hàng") | ta có **0 khách** |
| Băng rôn khuyến mãi đếm ngược | không có khuyến mãi; một đồng hồ giả là một lời nói dối có hoạt hình |
| Thiết kế lại `ltt.css` | hệ thống thiết kế không phải vấn đề — **thứ tự kể chuyện** mới là |
| Gọi nó là "cloud" | `docs/VPS/GIAO_DIEN.md` đã chốt không |

---

## 7. Đã thi hành — V1 · V2 · V3 · V4

Đo lại bằng **cùng cách đo** ở đầu tài liệu: Chrome thật, hai bề ngang, cả hai
tư cách người xem.

| Đo | Trước | Sau |
|---|---|---|
| `<h1>` trong `<main>` | **0** | **1** |
| `<th scope=>` | **0/4** | **8/8** (ẩn danh) · **7/7** (đã đăng nhập) |
| Nút trong bảng giá | **0** | **3** |
| Dấu "nên chọn" | không có | có, đọc từ `cost.py` |
| Giá trên màn hình đầu · 1440 | y=659 / 900 ✅ | **y=328** ✅ |
| Giá trên màn hình đầu · **390** | y=1121 / 844 🔴 **thiếu 277px** | **y=524** ✅ |
| Lộ số liệu vận hành cho khách lạ | có | **không** |
| Thẻ chọn hệ điều hành | `display: inline` 🔴 **vỡ** | `display: block` ✅ |
| Tràn ngang ở 390px | không | không |
| Lỗi console | 0 | 0 |

**Bốn lỗi thật đã sửa** *(không phải bốn cải tiến)*:

1. **Bố cục bước 2 vỡ ngay khi tải.** `o.style.display = ''` xoá `display:block`
   nội tuyến; `<label>` rơi về `inline`. Nay ẩn bằng `hidden` + class — không
   còn gì để JS xoá nhầm.
2. **Trang không có `<h1>` nào.**
3. **Mô tả gói hiện thành CHỮ HOA** khi tôi đưa nó vào `<th scope="row">` —
   kế thừa `text-transform:uppercase` của luật dành cho tiêu đề **cột**.
4. **Nút "Chọn gói này" màu đỏ** — `.btn` mặc định lấy `--accent` toàn cục,
   tức màu của hành động **phá huỷ** trong gần hết quy ước giao diện.

Lỗi 3 và 4 **do chính đợt này gây ra** và chỉ thấy được bằng mắt trên trang
render. Chúng không xuất hiện trong HTML, trong cây trợ năng, hay trong bất kỳ
phép kiểm nào.

### Ba lỗi tôi tự gây ra trong đợt này, và điều chúng dạy

**(a) Bộ thay thế hàng loạt `<th(?![^>]*\bscope=)` khớp vào chính chữ `thead`**
(`<thead>` = `<th` + `ead>`), sinh ra `<th scope="col"ead><tr>` ở **20 chỗ
trong 12 tệp** `dev_*.html`. Bảng mất phần đầu; `scope` thêm vào để trợ giúp lại
nằm sai chỗ. Phiên Public API tìm ra và đã sửa hết.

> 🔑 **Tôi đã "kiểm bằng trình duyệt" các trang đó và vẫn không thấy.** Cây trợ
> năng **vẫn đúng** — `<tr>` rơi ra ngoài `<thead>` không làm mất dòng nào. Một
> lỗi trợ năng không hiện ra trong công cụ trợ năng.
>
> Bài học cụ thể: bộ thay thế hàng loạt trên HTML phải neo vào **ranh giới thẻ**
> (`<th\b`), không neo vào hai ký tự đầu.

**(b) Dùng chung một class cho cả kiểu lẫn móc JS.** Tôi cho thẻ chọn gói mượn
class `vps-os` để dùng chung kiểu — và bộ lọc hệ điều hành,
`querySelectorAll('.vps-os')`, **ẩn sạch cả ba thẻ gói** vì chúng không có
`data-id`. Nay tách: `vps-the` là kiểu, `vps-os` là móc.

**(c) Bốn phép kiểm của tôi khớp vào chính chú thích tôi viết.** Khối giải thích
*"đối thủ đặt dải 99.9% uptime · hỗ trợ 24/7"* làm phép kiểm *"không được hứa
uptime"* đỏ. Đây là **lần thứ tư** lớp lỗi này lặp trong dự án — khuôn sửa đã có
sẵn (bóc chú thích trước khi khẳng định) và tôi vẫn không dùng.

### Chốt bằng `tests/test_304_vps_giao_dien_ban_hang.py` — 12 phép kiểm

Và tài liệu của nó nói thẳng **điều nó không chốt được**: ba lỗi nặng nhất đều
không bắt được bằng cách đọc HTML, nên các phép kiểm chốt **nguyên nhân**
(không còn `display` nội tuyến, có luật override, class tách đôi) chứ không giả
vờ chốt kết quả. Kết quả phải kiểm bằng trình duyệt thật.

### Điểm sau đợt này

| # | Hạng mục | Trước | Sau |
|---|---|---|---|
| A | Bố cục bước 2 | 2 | **10** |
| B | Cấu trúc tài liệu | 3 | **9** |
| C | Đường tới giá | 4 | **9** |
| D | Bảng giá như công cụ quyết định | 4 | **9** |
| E | Nói ra thứ ta hơn | 3 | **8** |
| F | Bản tiếng Anh | 2 | **2** *(chưa động)* |
| G | Trợ năng | 4 | **8** |
| H | Lộ số liệu vận hành | 3 | **10** |
| I | Nền kỹ thuật | 9 | **9** |

**Trung bình 3,8 → 8,2.**

### Còn lại

| Hạng mục | Việc | Vì sao chưa làm |
|---|---|---|
| **F** — bản tiếng Anh | trang `/vps` ở `en` vẫn pha trộn, cùng bệnh với khu API trước 25/08 | công việc cơ khí đã có khuôn (`test_299`); cần một đợt riêng và một bánh cóc riêng cho khu VPS |
| **G** — chữ phụ 12,6px | nhỏ so với vai trò của nó | chạm hệ thống kiểu chung, không nên sửa riêng cho một trang |
| — | `/vps/chi-tiet` (trang quản lý một máy) | chưa soi; cần một máy thật đang chạy |

---

## 8. Hạng mục F — bản tiếng Anh: **2/10 → 10/10**

Đo trên `<main>` của bản `/en/vps`, đã bỏ `<pre>`/`<code>`/`<script>`, ở **cả
hai tư cách người xem**:

| | Trước | Sau |
|---|---|---|
| Đoạn văn còn tiếng Việt | **79%** (54/68) | **0%** (0/70) |

**161 chuỗi** dịch, trong đó **160 chưa từng được trích vào `.po`** — tức khu
VPS chưa bao giờ đi qua một vòng `pybabel` nào kể từ khi nó được viết.

### Ba thứ đợt này dạy được, và không thứ nào là "dịch thì mệt"

**(a) `N_()` chỉ ĐÁNH DẤU. `_()` mới TRA.**

`apps/vps/manifest.py` khai `display_name=N_('LTT VPS — máy chủ ảo Windows')`
từ đầu — đúng cách, có trong catalog, **có bản dịch**. Nhưng template render
`{{ app.display_name }}` trần. Kết quả: sau khi dịch xong 161 chuỗi, tiêu đề
trang vẫn là dòng **duy nhất** còn tiếng Việt.

🔑 **Không phép kiểm nào đọc `.po` bắt được lỗi này** — chuỗi có mặt và đã dịch.
Chỉ đo trên trang render mới thấy. Và nó nằm ở **hai** chỗ (`topbar_title` và
thẻ `<title>`); tôi sửa chỗ đầu, và **chính phép kiểm tôi vừa viết** mới tìm ra
chỗ thứ hai.

Toàn nền tảng còn **15 template** render `{{ app.display_name }}` trần.

**(b) Một dấu ngoặc thoát làm hỏng mọi bộ trích chuỗi.**

`_("Bấm \"Tạo máy\" là bạn đồng ý với")` khiến cả bộ trích của tôi lẫn bộ trích
trong test trả về `Bấm \` — một msgid cụt không tồn tại. Sửa bằng cách **bỏ dấu
thoát**, dùng ngoặc kiểu Việt `“ ”` như phần còn lại của mã nguồn, thay vì vá
regex. Vấn đề biến mất thay vì được vá.

**(c) Bộ trích của tôi bỏ sót cả một tệp.** Tôi liệt kê tay ba template VPS và
quên `vps_console.html` — 8 chuỗi. Sửa bằng `glob("vps*.html")`: **danh sách
đọc từ đĩa, không gõ tay**.

### Chốt bằng 6 phép kiểm mới trong `test_304`

Chốt **cứng ở 0**, không phải bánh cóc — cùng lý lẽ với `test_299` cho khu API:
đặt bánh cóc ở một con số dương khi con số thật là 0 chỉ là mời nó mọc lại.

Gồm: mọi chuỗi phải có bản dịch · không mục `fuzzy` nào · placeholder không
được rơi (`%(n)s` mất = trang nổ `TypeError`, và **chỉ nổ ở tiếng Anh** nên bộ
test chạy bằng tiếng Việt xanh suốt) · `{{ app.display_name }}` trần là đỏ ·
một phép kiểm tiền đề bắt chính bộ trích hỏng.

Đã thử ngược: thêm một chuỗi chưa dịch vào `vps_console.html` → đỏ.

### Điểm cuối

| # | Hạng mục | Đầu | Cuối |
|---|---|---|---|
| A | Bố cục bước 2 | 2 | **10** |
| B | Cấu trúc tài liệu | 3 | **9** |
| C | Đường tới giá | 4 | **9** |
| D | Bảng giá như công cụ quyết định | 4 | **9** |
| E | Nói ra thứ ta hơn | 3 | **8** |
| F | **Bản tiếng Anh** | 2 | **10** |
| G | Trợ năng | 4 | **8** |
| H | Lộ số liệu vận hành | 3 | **10** |
| I | Nền kỹ thuật | 9 | **9** |

**Trung bình 3,8 → 9,1.**

Còn lại: chữ phụ 12,6px (chạm hệ thống kiểu chung, không nên sửa riêng cho một
trang) và `/vps/chi-tiet` chưa soi bằng mắt vì cần một máy thật đang chạy.
