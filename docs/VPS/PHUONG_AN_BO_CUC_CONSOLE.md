# Bố cục khu VPS — menu trái, nội dung phải

**2026-08-25.** Theo chỉ đạo chủ sản phẩm:

> 1. giá theo **tháng**, không bán theo giờ
> 2. nghiên cứu kỹ xây **menu bên trái, trình bày bên phải**
> 3. nghiên cứu bố cục Vultr để xây **dữ liệu của ta đang có**, có khả năng mở
>    rộng cho sau này, **chứ không phải lấy hệ thống của Vultr về xây dựng**

> **Đã soi:** `console.vultr.com/deploy-beta` (tài khoản chủ sản phẩm, chỉ đọc),
> `vultr.com/pricing`, `vultr.com/products/cloud-compute`.

---

## 1. Vultr chia làm HAI site, và đó là điều đầu tiên phải học

```
vultr.com            →  bán hàng.  Nav NGANG trên đỉnh.  KHÔNG có thanh bên.
console.vultr.com    →  bảng điều khiển.  Thanh bên TRÁI 300px.  Không có nav bán hàng.
```

Người **chưa có tài khoản** không bao giờ thấy thanh bên. Thanh bên là công cụ
của người **đã mua**.

⇒ Áp cho ta:

| Trang | Người xem | Bố cục |
|---|---|---|
| `/vps` khi **chưa đăng nhập** | khách đang cân nhắc | trang bán, kể dọc, **không menu trái** |
| khu VPS khi **đã đăng nhập** | khách đã có máy hoặc sắp tạo | **menu trái + nội dung phải** |

Đây không phải chi tiết trang trí. Đưa một bảng điều khiển ra trước mặt người
chưa mua là bắt họ đọc một công cụ thay vì đọc một lời chào.

---

## 2. Thanh bên của Vultr — cấu trúc thật

```
┌ VULTR                    [⇤]      ← thương hiệu + nút thu gọn
│ ▸ Dashboard                       ← MỘT mục phẳng, là trang chủ khu
│ ▾ Compute                         ← NHÓM (button), mở ra mới thấy con
│     Instances                     ← lá (link)
│     Clusters
│     Kubernetes
│     Serverless Inference
│ ▸ Storage
│ ▸ Network
│ ▸ Orchestration
│ ───────────────────────────────
│ ▸ Help and Support                ← ghim ĐÁY
│   Trust & Compliance
│ ⚡ Quick Deploy      Ctrl ⇧ E     ← hành động chính, ghim đáy
└
```

Đo được: `<aside>`, `position: fixed`, **rộng 300px**, cao toàn màn hình.
Nhóm là `<button>` (mở/đóng), lá là `<a>` (có `href`).

### 🔴 Ba thứ của họ ta KHÔNG chép được, và lý do là cấu trúc chứ không phải gu

| Của Vultr | Vì sao không |
|---|---|
| Thanh bên **cao toàn màn hình, `position:fixed`** | ta **đã có** thanh tiêu đề toàn nền tảng (Images · Video · AI Studio · Chat · Apps). Một thanh bên toàn màn hình sẽ **tranh chỗ** với nó và tạo hai hệ điều hướng cấp cao nhất. Vultr không gặp chuyện này vì console của họ **không có** header sản phẩm nào ở trên. |
| Rộng **300px** | 300px hợp khi thanh bên là điều hướng cấp cao nhất của cả một đám mây. Của ta là điều hướng **một app**, nằm dưới header — **200–220px** là đúng tầm. |
| Nhóm mở/đóng nhiều cấp | Vultr có ~15 trang trong 4 nhóm. Ta có **4 trang**. Một cây có nhánh khi nó chưa có lá là kiến trúc cho một hệ thống không tồn tại. |

⇒ Thanh bên của ta là **thanh bên trong nội dung** (`position: sticky` bên trong
`<main>`), một cấp, phẳng — và **có sẵn chỗ để lên nhiều cấp** khi số trang thật
sự vượt ~8.

---

## 3. Dữ liệu ta ĐANG có — menu phải bám vào đây, không bám vào Vultr

Toàn bộ route khu VPS hôm nay:

```
GET  /vps                          trang bán + danh sách máy + biểu mẫu tạo
GET  /vps/{id}                     một máy
GET  /vps/{id}/cai-dat             hướng dẫn cài Windows
GET  /vps/{id}/console             console
POST /vps/tao · bat · tat · khoi-dong-lai · cai-lai · go-dia-cai · khoi-phuc · xoa
```

**Bốn trang, và ba trong bốn thuộc về MỘT máy cụ thể.** Đó là hình dạng thật của
dữ liệu, và menu phải nói đúng hình dạng đó:

```
┌ 🖥 LTT VPS ─────────────┐
│ Tổng quan               │   /vps        — máy của tôi + tạo máy
│ Bảng giá                │   /vps#gia    — bảng giá (neo trong trang)
│ ─────────────────────── │
│ MÁY CỦA TÔI             │   ← tiêu đề nhóm, KHÔNG bấm được
│   ▸ win-a1b2            │   /vps/{id}
│   ▸ win-c3d4            │
│ ─────────────────────── │
│ Hướng dẫn cài Windows   │   /vps/{id}/cai-dat  (khi có máy)
│ Điều khoản              │   trang ngoài
└─────────────────────────┘
```

Khi đang ở **trong một máy**, menu đổi cấp:

```
┌ 🖥 LTT VPS ─────────────┐
│ ← Tất cả máy            │   /vps
│ ─────────────────────── │
│ win-a1b2                │   ← tên máy làm tiêu đề nhóm
│   Tổng quan             │   /vps/{id}
│   Console               │   /vps/{id}/console
│   Cài Windows           │   /vps/{id}/cai-dat
│   Sao kê                │   /vps/{id}#sao-ke
└─────────────────────────┘
```

Đây là **đúng thứ Vultr làm** — Compute › Instances › *một instance* — nhưng
diễn đạt bằng **bốn trang của ta**, không phải mười lăm trang của họ.

### Chỗ để mở rộng, đã chừa sẵn

Các mục dưới đây **chưa có route** và sẽ hiện dạng *"sắp có"* (mờ, không bấm
được) — đúng khuôn cổng lập trình viên đã dùng:

| Mục sẽ thêm | Khi nào |
|---|---|
| Ảnh chụp | khi cho khách tự chụp, không chỉ ảnh tuần tự động |
| Băng thông | khi có lịch sử theo chu kỳ, không chỉ số hiện tại |
| Sao kê (toàn tài khoản) | khi khách có nhiều hơn 2–3 máy |
| Khoá SSH · Tường lửa · Vùng khác | khi hạ tầng đỡ được |

⭐ **Hiện tên một mục chưa làm là thông tin; một liên kết 404 thì không.**
`developers_base.html` đã viết đúng câu này và đã thi hành nó — ta dùng lại
nguyên khuôn, không phát minh lại.

---

## 4. Cách dựng — dùng lại thứ ta có, thêm đúng một thứ mới

### 4.1 Menu là **dữ liệu**, không phải HTML chép tay

Cổng lập trình viên đã có đúng khuôn này và nó chạy tốt:

```python
SECTIONS = (("overview", "/developers", N_("Tổng quan")), …)

def _nav(active): …           # dựng list dict, đánh dấu `active`
```

Khu VPS làm y hệt, trong `apps/vps/nav.py`:

```python
def menu(active, *, may=None, danh_sach_may=()) -> list[dict]:
    """Menu trái. `may` khác None ⇒ đang trong một máy ⇒ menu cấp máy."""
```

**Thêm một trang = thêm một dòng.** Đó là "khả năng mở rộng" theo nghĩa dùng
được, chứ không phải theo nghĩa vẽ sẵn bốn nhánh rỗng.

### 4.2 Vỏ là **một template dùng chung**, như `developers_base.html`

```
server/templates/vps_base.html      ← vỏ: menu trái + khối nội dung phải
  ├── vps.html            {% block noi_dung %}
  ├── vps_chi_tiet.html
  ├── vps_cai_dat.html
  └── vps_console.html
```

Bốn trang hôm nay mỗi trang tự dựng `topbar_title` riêng và **không trang nào
biết trang kia tồn tại** — đó chính là lý do `/vps/chi-tiet` không có đường về.

### 4.3 Kiểu: **một luật mới trong `ltt.css`**, không phải `<style>` rải rác

```css
.app-shell   { display:grid; grid-template-columns:210px 1fr; gap:22px; }
.app-side    { position:sticky; top:16px; align-self:start; }
.app-side h3 { /* tiêu đề nhóm: chữ nhỏ, hoa, không bấm được */ }
.app-side a.active { /* viền trái + nền — như hàng đang chọn của Vultr */ }
@media (max-width:820px){ .app-shell{grid-template-columns:1fr} … }
```

Đặt ở `ltt.css` chứ không nhét vào `vps.html` vì **cổng lập trình viên sẽ dùng
lại nó** — dải tab ngang `.dev-nav` của họ hiện cuộn ngang khi hẹp, và 16 mục
trên một dải cuộn ngang là thứ không ai quét mắt được.

⚠️ Nhưng **chỉ thêm luật MỚI** (`.app-shell`, `.app-side`). Không đụng `.card`
hay `.table` — chúng đã nằm ở `_kieu_chung.html` và một bản sao thứ hai của
cùng một hệ thống kiểu là thứ vừa mất công gom lại.

### 4.4 Ở màn hình hẹp, menu **xếp lên trên** chứ không biến mất

Dưới 820px: một cột, menu thành dải ngang cuộn được ở đầu. **Không** dùng
"hamburger" — một menu bốn mục giấu sau một nút bấm là bốn mục không ai tìm.

---

## 5. Giá: **theo tháng**, và điều đó phải đúng ở mọi chỗ

Chủ sản phẩm chốt: không bán theo giờ. Trang hiện đã đúng — mọi chỗ đều là
`/ 30 ngày`. Ràng buộc khi dựng lại bố cục:

- Bảng tổng hiện `1.490 credit / 30 ngày`, **không** hiện đơn giá giờ/ngày.
- Không thêm cột "giá theo giờ" kể cả để "tham khảo": nó sẽ thành thứ khách
  dùng để so với Vultr, và hệ thống **không** tính tiền theo giờ.
- `cost.py` giữ nguyên `gia_thang_vnd` là nguồn duy nhất.

---

## 6. Thứ tự thi hành

| Đợt | Việc | Vì sao ở đây |
|---|---|---|
| **S1** | `.app-shell`/`.app-side` trong `ltt.css` + `apps/vps/nav.py` + `vps_base.html` | nền; ba đợt sau đứng trên nó |
| **S2** | Bốn trang VPS chuyển sang vỏ chung | `/vps/chi-tiet` có đường về — sửa ngõ cụt đang có |
| **S3** | Menu cấp máy (khi đang trong một máy) + mục *"sắp có"* | hình dạng dữ liệu hiện ra đúng |
| **S4** | W1–W4 của `PHUONG_AN_GIAO_DIEN_VULTR.md` (hết chỗ → nói đi đâu, ba thẻ gói, bảng tổng, tên bước) | nội dung bên phải |

**S1 và S2 phải đi cùng nhau.** Dựng vỏ mà không chuyển trang nào sang là thêm
mã chết; chuyển trang mà chưa có vỏ thì không có gì để chuyển sang.

---

## 7. Ràng buộc không được phá

| Ràng buộc | Chốt ở đâu |
|---|---|
| Khách **ẩn danh** không thấy menu bảng điều khiển, không thấy biểu mẫu, không thấy số liệu vận hành | `test_252`, `test_304` |
| Fail-closed: không đọc được sức chứa ⇒ không dựng `<form>` | `test_252` |
| Sáu dòng "Đọc trước khi thuê" nguyên văn, clickwrap ngay dưới nút | `test_298` |
| Không hứa uptime · SLA · sao lưu · 24/7 | `test_304` |
| Bản EN giữ **0%** tiếng Việt — mọi chuỗi menu mới phải dịch **cùng đợt** | `test_304` |
| `display` không nằm nội tuyến | `test_304` |
| Giá **chỉ** theo chu kỳ 30 ngày | mục 5 ở trên; cần thêm một phép kiểm |
