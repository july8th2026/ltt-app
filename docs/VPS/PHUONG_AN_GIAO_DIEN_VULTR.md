# Phương án giao diện VPS — học từ Vultr

**2026-08-25.** Theo yêu cầu chủ sản phẩm: *giao diện trang VPS quá thô sơ, học
tập giao diện từ Vultr để xây dựng bố cục trang.*

> Soi trực tiếp **bảng điều khiển thật** của Vultr (`console.vultr.com/deploy-beta`,
> tài khoản của chủ sản phẩm, chỉ đọc — không bấm nút hành động nào), cộng
> `vultr.com/pricing` và `vultr.com/products/cloud-compute`.

---

## 0. Điều phải nói trước, nếu không cả phương án sẽ sai hướng

**Trang deploy của Vultr dày đặc vì họ có ~40 gói và 32 vùng. Ta có 3 gói và 1
vùng.**

Chép độ dày của họ là chép **triệu chứng của một vấn đề ta không có**. Ô tìm
kiếm "Filter Plans…", dải tab lọc bên trái (All / VX1 / General Purpose / CPU
Optimized / …), bảng có cột sắp xếp được, lưới 32 thành phố chia ba châu lục —
tất cả tồn tại để **thu hẹp một danh sách quá dài**. Danh sách của ta có ba
dòng.

Thứ **thật sự** chuyển được không phải độ dày mà là **giàn giáo ra quyết định**:
họ đặt tên cho từng bước, nói rõ mỗi gói **hợp với ai**, giữ một bảng tổng luôn
nhìn thấy, và — quan trọng nhất — **khi một lựa chọn không dùng được, họ nói
ngay lựa chọn thay thế là gì**.

---

## 1. Vultr làm gì — quan sát, không diễn giải

```
Compute › Create Instance                    [Documentation] [API]

┌─ Plan ──────────────────────────────────────────────┐  ┌─ Summary ──────┐
│ [🖥 Dedicated CPU]  [🖥 Shared CPU]  [GPU]  [Metal]  │  │ Dedicated CPU  │
│  mỗi thẻ: icon + TÊN ĐẬM + 3 dòng "hợp với ai"       │  │ vx1-g-2c-8g    │
│  thẻ đang chọn: NỀN xanh nhạt + VIỀN xanh            │  │ ┌Cores───────┐ │
└─────────────────────────────────────────────────────┘  │ │ 2 vCPUs    │ │
┌─ Plan Selection ⌄ ──────────────────────────────────┐  │ ├Memory┬Storage│
│ [🔍 Filter Plans…]                                   │  │ │ 8 GB │ Block │
│ ┌All──────┐ ┌ Name  vCPU  Memory  Storage  Bandwidth│  │ ├Location─────┤ │
│ │VX1  ◀   │ │ ▸vx1-g-2c-8g  2  8GB  Block  5TB/mo  │  │ │🇺🇸 Atlanta  │ │
│ │General  │ │  vx1-g-2c-8g… 2  8GB  120GB  5TB/mo  │  │ ├Total Price──┤ │
│ │CPU Opt  │ │  …                                    │  │ │ $0.060/hr   │ │
│ ├About VX1┤ │  hàng đang chọn: VIỀN TRÁI xanh + nền │  │ └─────────────┘ │
│ │giải thích│ └───────────────────────────────────────│  └────────────────┘
└─────────────────────────────────────────────────────┘  ┌──────────────┐
┌ Step 1: Select Location & Plan │ Step 2: Configure   ┐  │ Configure  → │
│   Configure Hardware           │   OS / Software     │  └──────────────┘
└━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷─────────────────────┘
```

Năm thứ đáng học, xếp theo giá trị:

### 1.1 🔑 Khi một lựa chọn KHÔNG dùng được, họ nói ngay cái thay thế

Đây là thứ tốt nhất trên trang đó, và nó là **chức năng chứ không phải thẩm mỹ**.
Chọn một gói không có ở vùng đang chọn, bảng tổng đổi thành:

```
This plan is unavailable in this location.
Your currently selected plan is not available in atl
You can request to reserve this plan:  [Request Reserved Capacity]
Or, select an on-demand location:
  Atlanta, US · Chicago, US · New York, US · Tokyo, JP · Amsterdam, NL · …
```

Nó không chỉ nói **không**, nó nói **đi đâu thì được**.

Trang của ta hiện nói `hết chỗ` rồi dừng. Khách hết đường.

### 1.2 Mỗi lựa chọn có một câu "hợp với ai", đặt NGAY TRONG thẻ

> Dedicated CPU — *"Demanding business apps, production websites, CI/CD, video
> transcoding, or larger databases."*
> Shared CPU — *"Apps with bursty performance, dev/test environments, and small
> databases."*

Không phải thông số. Là **việc**.

Ta đã có sẵn câu đó cho cả ba gói trong `cost.py` (`mo_ta`), và từ đợt trước nó
đã ra tới bảng giá công khai. Nhưng nó đang là **văn xuôi trong một ô bảng**,
không phải một tiêu chí để quét mắt.

### 1.3 Thẻ đang chọn nhìn thấy được ở tầm mắt, không phải tầm chấm radio

Nền xanh nhạt + viền xanh cho thẻ; viền trái dày + nền nhạt cho hàng bảng.
Nhận ra được từ xa nửa mét.

### 1.4 Bảng tổng: mỗi trường một ô có viền, giá **to** ở cuối

Không phải bảng hai cột. Từng ô riêng, và `Total Price` cỡ chữ lớn hẳn.

### 1.5 Hai bước có TÊN, và một thanh tiến trình ở chân trang

```
Step 1: Select Location & Plan      Step 2: Configure Software & Deploy
        Configure Hardware                  OS / Software / Deploy
```

Mỗi bước có **tiêu đề** và **một dòng nói bước đó làm gì**. Nút chính
(`Configure →`) nằm cuối cột tóm tắt, không lẫn vào thân trang.

---

## 2. Cái KHÔNG chép, và vì sao

| Của Vultr | Vì sao không chép |
|---|---|
| Ô tìm kiếm "Filter Plans…" | ta có **3** gói; một ô lọc cho ba dòng là chế nhạo người dùng |
| Dải tab lọc bên trái (6 nhóm) | ta có một nhóm |
| Bảng có cột sắp xếp được | sắp xếp 3 hàng |
| Lưới 32 thành phố, chia ba châu lục | ta có **một** vùng |
| Giá theo giờ (`$0.060/hr`) | ta bán theo **chu kỳ 30 ngày**; đổi sang giờ là hứa một thứ hệ thống không làm |
| "Request Reserved Capacity" | ta không có cơ chế đặt trước |
| Thanh bên điều hướng toàn bộ sản phẩm | ta có một sản phẩm |

⚠️ Và thứ tuyệt đối không chép — **đã ghi trong `docs/VPS/GIAO_DIEN.md` từ
trước**: mọi câu về *uptime · SLA · sao lưu · hỗ trợ 24/7*. Vultr nói được vì
họ có. Ta không có, và một câu quảng cáo sai là một vụ tranh chấp về sau.

---

## 3. Phương án — năm việc, theo thứ tự giá trị

### W1 · Khi hết chỗ thì NÓI ĐI ĐÂU *(chức năng, không phải thẩm mỹ)*

Hôm nay: `hết chỗ` — hết câu.

Phải là: nói **gói nào còn**, và cho bấm thẳng sang gói đó.

```
VPS Lớn   4 vCPU · 8 GB RAM · 80 GB   329.000đ   [hết chỗ]
          Còn chỗ cho: VPS Vừa (179.000đ) · VPS Nhỏ (149.000đ)
```

Dữ liệu đã có sẵn — `g.con_cho` tính cho **từng gói** rồi. Chỉ là trang chưa
dùng nó để đề xuất.

**Đạt khi:** không gói nào rơi vào ngõ cụt; nếu *cả ba* hết chỗ thì nói rõ
"toàn hệ thống đang hết chỗ, thử lại sau" chứ không hiện ba chữ `hết chỗ` rời
rạc.

### W2 · Ba gói thành ba THẺ, không phải ba hàng bảng

Vultr dùng bảng cho 40 gói **và dùng thẻ cho 4 nhóm**. Ba gói của ta gần với
"4 nhóm" hơn là với "40 gói".

```
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ 🖥 VPS Nhỏ      │ │ 🖥 VPS Vừa  ★  │ │ 🖥 VPS Lớn      │
│ 1 vCPU · 2 GB   │ │ 2 vCPU · 4 GB   │ │ 4 vCPU · 8 GB   │
│ 40 GB · 300 GB  │ │ 60 GB · 600 GB  │ │ 80 GB · 1 TB    │
│                 │ │                 │ │                 │
│ Hợp khi bạn chỉ │ │ Chạy được mọi   │ │ Hợp khi bạn     │
│ cần một máy     │ │ bản trong danh  │ │ chạy phần mềm   │
│ chạy phần mềm   │ │ mục. Phần lớn   │ │ nặng hoặc nhiều │
│ hoặc script nền │ │ nên chọn gói này│ │ việc cùng lúc   │
│                 │ │                 │ │                 │
│   149.000đ      │ │   179.000đ      │ │   329.000đ      │
│   / 30 ngày     │ │   / 30 ngày     │ │   / 30 ngày     │
└────────────────┘ └────────────────┘ └────────────────┘
```

- **Một thẻ, một quyết định.** Thông số, việc-nó-hợp, và giá cùng nằm trong tầm
  mắt — hôm nay chúng nằm ở ba cột cách nhau nửa màn hình.
- Thẻ đang chọn: **nền + viền** như Vultr, không chỉ chấm radio.
- Dùng **cùng một khối** cho cả trang bán (ẩn danh, thẻ dẫn tới `/register`) và
  trang tạo máy (đã đăng nhập, thẻ là `<label>` bọc radio). Một nguồn, hai vỏ.
- Ở 390px xếp dọc — vốn đã đúng vì `flex-wrap`.

⚠️ **Giữ bảng giá dạng bảng ở đâu đó**, vì bảng vẫn là thứ so sánh cột-với-cột
tốt nhất. Đề xuất: thẻ ở trên (quyết định), bảng gọn ở dưới (đối chiếu).

### W3 · Bảng tóm tắt: mỗi trường một ô, giá to

Hôm nay là `<table>` hai cột chữ nhỏ đều nhau — `SẼ TRỪ 1.490 credit` trông
ngang hàng với `BĂNG THÔNG 300 GB`, trong khi một cái là **số tiền** còn cái kia
là một thông số.

Đổi thành các ô có viền như Vultr, và **số credit sẽ trừ + số dư còn lại** cỡ
chữ lớn hẳn.

### W4 · Hai bước có tên và một thanh tiến trình

Ta đã có `Bước 1 · Chọn máy` / `Bước 2 · Chọn hệ điều hành` — đúng hướng, nhưng
chúng là hai dòng `<h3>` trôi trong thân trang. Thêm **một dòng nói bước đó làm
gì** (như Vultr: *"Configure Hardware"* / *"OS / Software / Deploy"*), và một
thanh tiến trình mảnh ở chân khối.

### W5 · Breadcrumb

`Compute › Create Instance` của Vultr trả lời "tôi đang ở đâu". Ta có
`LTT VPS — máy chủ ảo Windows` trên thanh tiêu đề, nhưng ở trang chi tiết máy
thì nó thành tên máy và **mất đường về**.

`VPS › Tạo máy` · `VPS › <tên máy>` — rẻ, và nó là thứ duy nhất trong danh sách
này sửa được cả `/vps/chi-tiet`.

---

## 4. Thứ tự, và vì sao

| Đợt | Việc | Vì sao ở đây |
|---|---|---|
| **W1** | hết chỗ → nói đi đâu | **chức năng**, không phải thẩm mỹ; là ngõ cụt duy nhất còn lại trong luồng mua |
| **W2** | ba gói thành ba thẻ | thay đổi lớn nhất về "trông chuyên nghiệp", và là thứ chủ sản phẩm nhìn thấy đầu tiên |
| **W3** | bảng tóm tắt | rẻ, và nó làm **số tiền** nổi lên đúng tầm quan trọng của nó |
| **W4** | tên bước + thanh tiến trình | rẻ |
| **W5** | breadcrumb | rẻ, và sửa được cả trang chi tiết máy |

W1 đứng đầu **không phải vì dễ**. Bốn việc còn lại làm trang đẹp hơn; W1 làm
trang **hoạt động được** ở một trường hợp nó đang bỏ khách giữa đường. Một trang
đẹp mà đến chỗ "hết chỗ" thì im lặng vẫn là một trang mất khách.

---

## 5. Ràng buộc không được phá khi làm

| Ràng buộc | Chốt ở đâu |
|---|---|
| **Fail-closed**: không đọc được sức chứa thì **không dựng `<form>`** | `test_252` |
| Sáu dòng "Đọc trước khi thuê" giữ **nguyên văn** | `test_298` đối chiếu từng con số |
| Clickwrap ngay dưới nút "Tạo máy" | `test_298` |
| Không hứa uptime / SLA / sao lưu / 24-7 | `test_304` |
| Khách ẩn danh **không** thấy biểu mẫu, **không** thấy số liệu vận hành | `test_252`, `test_304` |
| Bản EN giữ **0%** tiếng Việt | `test_304` (6 phép kiểm) |
| `display` **không** được nằm nội tuyến (JS sẽ xoá) | `test_304` |

Mọi chuỗi mới phải dịch ngay trong cùng đợt — bánh cóc EN sẽ đỏ, và đó là chủ ý.

---

## 7. Đã thi hành — S1 · S2 · S3 · S4 *(25/08)*

### Vỏ khu: menu trái + nội dung phải (S1–S3)

Bốn trang VPS nay dùng chung `vps_base.html`; menu là **dữ liệu**
(`apps/vps/nav.py`), thêm một trang là thêm một dòng.

**Menu đổi cấp theo hình dạng dữ liệu thật** — ba trong bốn trang thuộc về một
máy cụ thể, nên menu ở trong một máy liệt kê các trang của máy đó kèm đường về.

**Breadcrumb `VPS › <tên máy>`** sửa ngõ cụt cuối: ba trang trong một máy trước
đây lấy tên máy làm thanh tiêu đề và **mất đường về**.

🔴 **Khách ẩn danh không thấy vỏ điều khiển.** Đây là thứ đáng học nhất ở
Vultr: `vultr.com` bán hàng (nav ngang, không thanh bên) tách hẳn khỏi
`console.vultr.com` (thanh bên). Đưa một bảng điều khiển ra trước mặt người
chưa mua là bắt họ đọc một công cụ thay vì đọc một lời chào.

### Nội dung bên phải (S4 = W1–W4)

| Việc | Trước | Sau |
|---|---|---|
| **W1** hết chỗ | `hết chỗ` — hết câu | `Hết chỗ cho cấu hình này. Còn chỗ: VPS Vừa · VPS Nhỏ` |
| **W2** ba gói | ba hàng bảng, thông số/mô tả/giá cách nhau nửa màn hình | ba **thẻ**, mỗi thẻ một quyết định; bảng đối chiếu gấp gọn ở dưới |
| **W3** tóm tắt | bảng hai cột, `SẼ TRỪ` ngang hàng `BĂNG THÔNG` | các **ô** có viền, số credit **1,5rem** |
| **W4** bước | hai `<h3>` trôi | tiêu đề + một dòng nói bước đó làm gì |

**W1 là việc chức năng, không phải thẩm mỹ.** Dữ liệu đã sẵn (`g.con_cho` tính
cho từng gói); trang chỉ chưa dùng nó để đề xuất. Đây đúng là thứ Vultr làm khi
một gói không có ở vùng đang chọn — họ liệt kê thẳng những vùng **có**.

🔑 **Một macro `the_goi` cho cả hai vỏ.** Trang bán (ẩn danh, thẻ dẫn tới
`/register`) và trang tạo máy (đã đăng nhập, thẻ là `<label>` bọc radio) dùng
**cùng một nguồn** — hai bản sao của một thẻ giá sẽ lệch, và cái lệch sẽ là cái
nói sai giá.

### Sáu lỗi tôi tự gây ra trong đợt này

1. **Lặp lại đúng lỗi của hạng mục F** — `nav.py` dùng `N_()` đánh dấu, template
   render `{{ m.nhan }}` trần ⇒ menu vẫn tiếng Việt trên bản `en`. Tôi vừa viết
   lớp lỗi này vào tài liệu **ba mươi phút trước** và vẫn mắc lại ở đợt kế tiếp.
   Và một lần **thứ ba** ở nhãn vùng (`NHAN_VUNG` khai `N_()`, template đưa
   `vung[0][1]` thẳng vào chuỗi).
2. **`"Tắt"` → *"Disable"*** — msgid trần dùng chung với nút vô hiệu hoá webhook
   ở khu API. Với một cái máy đúng phải là *"Stop"*. Cùng lớp với `"Cấu hình"` →
   *"Settings"*.
3. **Nút điều khiển máy toàn màu đỏ** — `.btn` mặc định lấy `--accent` toàn cục.
   "Start"/"Restart" hoàn tác được bằng cách bấm cái kia; đỏ là màu của thứ
   **không** hoàn tác được. Nay chỉ *"Delete permanently"* đỏ.
4. **Luật `.tbl .btn-goi`** giới hạn theo tổ tiên — im lặng mất tác dụng ngay
   khi thẻ rời khỏi bảng ở S4.
5. **Chú thích Jinja đặt bên trong một biểu thức `{% %}`** ⇒ `TemplateSyntaxError`,
   trang 500. Bắt được bằng cách **mở trang**, không phải bằng test.
6. **`\b` trong mã vá thành ký tự backspace 0x08** — lần thứ tư trong ngày. Đã
   bỏ hẳn `\b` khỏi các regex viết qua mã vá.

⭐ Bốn trong sáu lỗi trên **không hiện ra trong HTML, trong cây trợ năng, hay
trong bất kỳ phép kiểm nào** — chỉ thấy khi mở trang bằng mắt.

### Chốt

`test_304` **25 phép kiểm**, trong đó hai cái vừa được viết lại để đo **tính
chất** thay vì cấu trúc: bản trước chốt `class="vps-the"` và đỏ ngay khi thẻ đổi
tên class, dù lỗi thật không tái diễn. Bản mới chốt *"mọi phần tử mang móc lọc
đều phải có `data-id`"* — sống qua lần đổi tên kế tiếp.

Thêm một phép kiểm chốt **giá chỉ theo chu kỳ 30 ngày**: cấm cả `/hr`,
`theo giờ`, `per hour` để không ai thêm "giá tham khảo theo giờ" cho giống
Vultr, trong khi hệ thống **không** tính tiền theo giờ.

```
test_252 · 298 · 303      72 xanh
gate --quick              17/17 PASS
lỗi console               0 (cả hai tư cách, cả hai bề ngang)
```
