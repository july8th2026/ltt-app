# V5_UX_AUDIT — audit giao diện, đo được và tự thú nhận giới hạn

> Bước 22 của §15. Đo trên bản chạy thật (`127.0.0.1:8199`), 1440×900 và 375×812,
> ngày 2026-09-08.

---

## 0. ⛔ Bài audit này KHÔNG độc lập, và đây là điều đầu tiên phải nói

§23 gọi bước này là *"independent UX audit"*. Người chấm là **chính người vừa
xây**, trong **cùng phiên**, với **cùng những giả định** đã dẫn tới từng lựa
chọn. Ba chỗ tôi gần như chắc chắn chấm sai về phía có lợi:

| tiêu chí | vì sao tôi không đáng tin ở đây |
|---|---|
| **Discoverability** | Tôi biết accordion ở đâu vì tôi đặt nó. Khách mới thì không. |
| **Product truth** | Tôi vừa dành cả buổi lập luận rằng vùng che chỉ hợp preset cắt. Tôi khó chấm thấp một quyết định mình vừa bênh vực. |
| **Clarity** | Mọi nhãn tiếng Việt trên màn hình đều là chữ tôi viết. |

⇒ Cách tôi làm cho nó bớt vô nghĩa: **chấm theo số đo được**, không theo cảm
nhận. Và những tiêu chí **chỉ người thật trả lời được** thì tôi **bỏ trống**
thay vì đoán — một điểm số tự chấm trông tin cậy hơn giá trị thật của nó.

---

## 1. Số đo được

Tất cả lấy từ trình duyệt thật, bằng API của trình duyệt.

| phép đo | kết quả |
|---|---|
| Control **thấy được** ở tầng cơ bản | **8** |
| Control **ẩn** trong Nâng cao | **7** |
| Thứ **bắt buộc chạm** để bắt đầu một lần chạy | **3** (video · giọng · nút) |
| Nâng cao đóng sẵn | ✅ |
| Tràn ngang @1440 | ❌ không |
| Tràn ngang @375 | ❌ không (`scrollWidth` = 375) |
| Mục tiêu chạm < 44px @375 | **0** |
| Thanh hành động dính đáy @375 | ✅ `sticky` |
| Công cụ vùng che ẩn @375 | ✅ + có câu giải thích |
| Ảnh thiếu `alt` | **0** |
| Nút không nhãn (không chữ, không `aria-label`) | **0** |
| Ô nhập không nhãn | **0** |
| Lỗi console | **0** |
| Chuỗi chưa dịch lọt ra bản EN | **0** *(19 chuỗi tiếng Việt phát hiện được đều là **tên giọng** — danh từ riêng, không dịch)* |
| Cấp bậc tiêu đề | `H1 → H2 → H3`, không nhảy cấp |

### ⚠️ Một phép đo của tôi đã SAI, và cách nó lộ ra

Lần đo đầu tôi đếm **12** control ở tầng cơ bản — mâu thuẫn với IA §4 (nói 4).
Tôi suýt ghi đó thành một phát hiện.

Nguyên nhân: tôi lọc bằng `getComputedStyle` + `getBoundingClientRect`. Với con
của một `<details>` **đã đóng**, Chromium vẫn giữ layout, nên rect trả `[16,16]`
và `offsetParent !== null` — trông y hệt "đang hiện".

```
che_do_checkVisibility : false      <- API cua trinh duyet noi: KHONG hien
che_do_offsetParent    : khong null <- phep thu cu noi: dang hien
che_do_rect            : [16, 16]   <- phep thu cu noi: dang hien
```

⇒ `Element.checkVisibility()` là công cụ đúng; hai cái kia là **bản đại diện**.
Đây là ca thứ sáu trong ngày của cùng một lớp lỗi, và là ca **của chính bài
audit** — suýt nữa tôi báo một khiếm khuyết không tồn tại.

---

## 2. Chấm điểm — chỉ chấm thứ đo được

| tiêu chí | điểm | căn cứ |
|---|---|---|
| **Visual hierarchy** | 85 | H1→H2→H3 không nhảy cấp; hai cột rõ; nhóm nâng cao tách khỏi cơ bản |
| **Speed (đường tới đích)** | 90 | 3 lần chạm bắt buộc; không bước trung gian; ước giá tự hiện khi chọn video |
| **Consistency** | 85 | dùng token của `ltt.css`, không màu tự chế; nhãn lấy từ `pipeline`/`gia`, không gõ tay |
| **Accessibility (đo được)** | 82 | 0 ảnh thiếu alt · 0 nút/ô không nhãn · 0 mục tiêu chạm <44px · thứ tự tab sạch · **1** lỗi tương phản, và nó **thuộc nền tảng** (§8). ⚠️ Chưa đo: trình đọc màn hình |
| **Mobile** | 85 | 0 tràn ngang, thanh dính, công cụ vùng ẩn **có giải thích** thay vì biến mất câm |
| **Error recovery** | 75 | lỗi có đủ 4 câu + nói rõ "thử lại không tính thêm credit". ⚠️ Chưa đo trên lỗi **thật** — mới đọc mã |
| **Product truth** | *(bỏ trống)* | tôi vừa bênh vực chính quyết định cần chấm — xem §0 |
| **Clarity** | *(bỏ trống)* | mọi nhãn là chữ tôi viết |
| **Discoverability** | *(bỏ trống)* | tôi biết mọi thứ ở đâu vì tôi đặt |
| **Feature completeness** | **85** | cả hai lời hứa ở §3 đã có mã (§6, §7); còn R3/R4 chưa đo |

⛔ **Không có điểm tổng.** Cộng bốn tiêu chí bỏ trống thành một con số là làm
đúng cái việc §0 vừa nói không nên làm.

---

## 3. 🔴 Hai phát hiện thật — tài liệu hứa nhiều hơn mã

Cả hai tìm ra bằng cách **đo mã**, không bằng cách nhớ.

### ✅ P0 — Đường tải lên bền vững — phát hiện ở bước 22, **đóng ở bước 23**

**Lúc audit** (trước khi sửa):

```
grep "/ve|upload_id"  server/static/asv.js             -> 0
grep "upload_id"      templates/asv_trang_chinh.html   -> 0
```

`CURRENT_UI_AUDIT.md` §2 xếp đây là **P0-1**, mục đầu bảng: *"Trần thật của sản
phẩm là **90 MB**, không phải 2 GiB."* Tôi còn viết một phép kiểm hồi quy
(`test_455::test_duong_ve_tai_len_van_cap_duoc_ve`) với chú thích *"giữ cho nó
vẫn chạy **trong lúc V5 viết client cho nó**"* — rồi **không viết client**.

⚠️ Và đây là kiểu thiếu sót tệ nhất: nó **không hiện ra** ở bất kỳ phép đo nào ở
§1 — màn hình vẫn đẹp, 0 lỗi console, 0 tràn ngang. Chỉ khách mang một tệp lớn
mới gặp. Một bài audit chỉ đo màn hình sẽ **không bao giờ** tìm ra nó; nó lộ ra
vì tôi đối chiếu **tài liệu với mã**, không đối chiếu tài liệu với màn hình.

⇒ Đã đóng ở **§6**. Trần thật của sản phẩm nay là 2 GiB cho `mp4`/`mov`/`m4v`,
  và vẫn là 90 MB cho `mkv`/`webm` — hai kiểu mà đường bền vững không nhận.

### ✅ P1 — IA hứa một nút không tồn tại — **ĐÃ ĐÓNG ở §7**

```
V5_UI_INFORMATION_ARCHITECTURE.md:232   [ Tải video ] [ Chạy lại với cài đặt này ] [ Xong ]
V5_UI_INFORMATION_ARCHITECTURE.md:241   "Chạy lại với cài đặt này" nạp lại đúng `ban_dung` cũ...
grep "Chạy lại"  templates/asv_tien_do.html   ->  0
```

Màn kết quả chỉ có **Tải video** và **Lồng tiếng video khác**. Nút thứ ba —
thứ IA gọi là *"chỗ cache artifact trả lời rõ nhất"* — chưa có mã.

⇒ Một tài liệu kiến trúc hứa nhiều hơn sản phẩm là một tài liệu sẽ dẫn sai người
đọc sau. Sửa **một trong hai**: viết nút, hoặc sửa IA. Không để lệch.

---

## 4. Những gì bài audit này KHÔNG trả lời được

Ghi ra để không ai đọc §1 rồi tưởng đã phủ hết:

| chưa đo | vì sao |
|---|---|
| Thông điệp lỗi trên lỗi **do mạch sinh ra** | §9 dựng trạng thái lỗi bằng dữ liệu gieo; chưa xem một lỗi do chính mạch ném |
| Trình đọc màn hình | chưa đo |
| Khách **thật** có hiểu hai preset không | không ai trong phiên này trả lời được |

⭐ Mục cuối là mục quan trọng nhất, và nó là lý do bài audit này không thể thay
một lượt thử với người thật. Hai preset là quyết định sản phẩm trung tâm của cả
màn hình; tôi chỉ đo được rằng chúng **hiện ra**, không đo được rằng chúng
**được hiểu**.

---

## 5. Việc phải làm (bước 23)

| # | việc | mức | trạng thái |
|---|---|---|---|
| R1 | Viết client tải lên bền vững trong `asv.js` | **P0** | ✅ **xong** — §6 |
| R2 | Nút *"Chạy lại với cài đặt này"* | P1 | ✅ **xong** — §7 |
| R3 | Đo tương phản + thứ tự tab | P2 | ✅ **đo xong** — §8 |
| R4 | Audit màn tiến độ/kết quả với dữ liệu thật | P2 | ✅ **xong** — §9 |

*(Phần biện luận hoãn R1 đã hết hiệu lực — R1 làm xong ở §6.)*

---

## 6. Bước 23 — R1 đã đóng

### Ba đường, đo trên trình duyệt thật

| kịch bản | xin vé | kết quả |
|---|---|---|
| kho cấp vé `direct` | ✅ | `PUT` tới URL của vé · `upload_id` được đặt · ô chọn tệp **disabled** · **0** tệp gửi kèm |
| kho trả `{"mode":"local"}` | ✅ | lùi multipart · `upload_id` rỗng · tệp vẫn đính kèm |
| tệp `.mkv` | ❌ *(đúng)* | không xin vé · đi thẳng multipart |

Trang mang cả hai trần: `data-tran-ben-vung="2048"` và `data-tran-mb="90"`.
Không lỗi console. `test_458` — **12 phép kiểm**, xanh.

### 🔴 Bất biến đắt nhất, và vì sao nó suýt bị bỏ sót

`routes.tao` ưu tiên `upload_id` và trả về **trước khi** chạm tới `video`. Đọc mã
thì thấy an toàn. Nhưng trình duyệt thì **đã gửi cả thân multipart rồi** — tức
tệp đi lên **hai lần**, và lần thứ hai đâm thẳng vào đúng cái trần 100 MB của
Cloudflare mà cả R1 sinh ra để tránh.

⇒ Client phải **tắt** ô chọn tệp trước khi nộp. Và phải `disabled`, không được
`value = ""`: ô ấy có `required`, nên một ô rỗng mà còn `required` sẽ chặn cả
form — hỏng theo kiểu *"bấm nút không có gì xảy ra"*.

Phép đo trong trình duyệt chốt đúng điều đó: `so_tep_con_gui: 0`.

### ⛔ Điều R1 KHÔNG chứng minh được

Trên máy này kho là `LocalStorage`, và nó **không cấp presigned PUT** —
`tao_ve_tai_len` trả `{"mode":"local"}`. Nên **cú `PUT` thật lên R2 chưa từng
chạy ở đâu trong lượt này.** Đường `direct` được xác minh bằng một kho **giả lập
trong trình duyệt**, không bằng R2 thật.

⇒ Cái đã chứng minh: hợp đồng của vé, đường lùi, bộ lọc kiểu, và bất biến
không-gửi-hai-lần. Cái **chưa**: một tệp 500 MB thật sự tới được R2.

⚠️ Ghi ra thay vì giấu dưới một bộ phép kiểm xanh, vì đây đúng là hình dạng của
một tính năng *"đã xong"* mà chưa từng chạy thật. Nó cần một môi trường có R2 —
và đó là một lượt riêng, có chủ.

---

## 7. Bước 23 — R2 đã đóng

Nút *"Chạy lại với cài đặt này"* nay có mã. `{prefix}?run_id={id}` điền sẵn
preset · cách khớp thời gian · giọng · cách chọn giọng, và **nói ra** rằng nó
vừa làm thế.

### Ba quyết định trong bản này

**① Tham số tên đúng là `run_id`, không phải `tu_run`.**

`test_455` chốt bằng AST rằng **mọi** handler nhận `run_id` phải đi qua
`_run_cua_toi`. Đặt một tên khác vẫn chạy, nhưng sẽ **rơi ra ngoài tầm** của chốt
đó — và một đường đọc lần chạy không được chốt quyền sở hữu là đúng hình dạng một
lỗ IDOR.

⭐ Tức cái chốt viết ở bước 8 vừa **tự động** phủ một handler viết ở bước 23, mà
không ai phải nhớ thêm một dòng vào danh sách. Đó là điều `test_455` được viết
theo QUY TẮC thay vì theo DANH SÁCH để có.

**② KHÔNG nạp lại `vung`.**

Vùng che là toạ độ trên khung hình của *một* video cụ thể. Đặt chúng lên video
khác là che nhầm một vùng khách không chọn — và khách **sẽ không biết**, vì ô
chọn tệp đã đổi còn các ô khác thì không.

⇒ Ranh giới: cài đặt nói *"xử lý thế nào"* thì nạp lại được; cài đặt nói *"ở chỗ
nào trên khung hình này"* thì không.

**③ Đính chính lý do trong IA.**

IA §9 viết nút này là *"chỗ cache artifact trả lời rõ nhất (đổi giọng ⇒ không
chép lời lại)"*. **Sai ở thời điểm**: cache artifact vẫn `DEFER` (thuộc
`platform_core`, chưa có), nên hôm nay nút này **chạy lại từ đầu**.

Lợi ích thật chỉ là *khách không phải gõ lại* — đủ để làm, nhưng không phải lý do
đã viết. Đã sửa IA.

⚠️ Đáng ghi vì đây là **lần thứ hai** trong cùng bài audit tôi bắt được tài liệu
nói quá mã. Lần đầu là chính cái nút này (hứa mà không có); lần này là **lý do**
của nó (có mã, nhưng viện dẫn một lợi ích chưa tồn tại). Kiểu thứ hai khó thấy
hơn, vì `grep` tìm được một nút vắng mặt nhưng không tìm được một lập luận sai.

### Đo được

```
19 phep kiem trong test_455 (them 5 cho R2), xanh
run_id bia dat        -> 404, khong 500
run_id cua nguoi khac -> 404      <- chot boi phep kiem AST co san
trang khong co run_id -> preset mac dinh, KHONG hien bang bao nap lai
```

---

## 8. R3 — tương phản và thứ tự tab

### Thứ tự tab: sạch

```
asv-video -> preset -> preset -> asv-loc-gioi -> asv-loc-vung
          -> asv-giong -> summary(Nang cao) -> asv-batdau
```

| phép đo | kết quả |
|---|---|
| số phần tử focus được | 8, đúng thứ tự DOM |
| `tabindex` dương (cướp thứ tự) | **0** |
| focus được nhưng nằm trong `<details>` đóng | chỉ `SUMMARY` — đúng, nó **là** cái nút mở |
| ô chọn tệp (bị che bằng `clip`) | vẫn focus được, và có `<label for>` |

⭐ Ô chọn tệp đáng nói: nó bị ẩn khỏi mắt bằng kỹ thuật `clip` để thay bằng một
nút đẹp hơn. Cách ẩn **sai** (`display:none` hay `visibility:hidden`) sẽ làm nó
biến mất khỏi bàn phím luôn — và khi đó người dùng bàn phím **không có cách nào**
chọn video. Ở đây nó vẫn ở trong luồng tab.

### 🔴 Tương phản: một lỗi, và nó KHÔNG phải của ASV

```
Start dubbing   #FFFFFF tren rgb(239,55,49)   ty le 3.99   can 4.5 (13px)
                                              ^^^^ --brand-primary
lop: "btn primary"
```

21/22 phần tử chữ đạt WCAG AA. Phần tử trượt là **nút chính**, và màu của nó là
`--brand-primary` — token thương hiệu của nền tảng, dùng bởi **mọi** `.btn.primary`
ở cả 19 app.

⛔ **Không sửa**, hai lý do:

1. **Phạm vi.** Sửa `.btn.primary` là chạm mọi app. Sửa màu thương hiệu là một
   quyết định thương hiệu.
2. **Đường tránh cục bộ sẽ đánh đổi sai.** Tôi *có thể* làm riêng nút của ASV to
   hơn hoặc đậm hơn — ở ≥18,66px đậm thì ngưỡng hạ xuống 3,0 và nó đạt. Nhưng khi
   ấy nút chính của ASV trông khác mọi app còn lại, tức đổi một khiếm khuyết lấy
   một khiếm khuyết khác. Chính bài audit này chấm *Consistency* 85 **vì** dùng
   token của nền tảng.

⇒ Ghi thành mục cho chủ dự án, cùng loại với `compileall -j 0`: **thật, đo được,
và ngoài phạm vi một app.**

Hai đường sửa, cả hai đều ở tầng nền tảng:

| | làm gì | đánh đổi |
|---|---|---|
| A | tối `--brand-primary` xuống tới tỉ lệ ≥ 4,5 | đổi màu thương hiệu |
| B | `.btn.primary` dùng cỡ chữ ≥ 18,66px **đậm** (ngưỡng thành 3,0) | nút to hơn ở mọi app |

⚠️ Và một điều đáng biết trước khi chọn: **3,99 chỉ trượt 4,5 một chút**, nên
phương án A cần rất ít — không phải đổi sang một màu đỏ khác hẳn.

---

## 9. R4 — và một phép suy sai đã tự chặn tôi mấy giờ

### 🔴 `R4` chưa bao giờ bị chặn bởi máy B

Tôi ghi `R4` là *"chặn bởi bản ghi bằng chứng / máy B"* và giữ nguyên nó qua bốn
tin nhắn với ba phiên khác. **Sai.**

```
R4 = audit GIAO DIEN cua man tien do / ket qua
   -> can DU LIEU THAT TRONG MAN HINH
   -> KHONG can mot MACH CHAY THAT
```

Gộp hai thứ ấy làm một là tự chặn mình bằng một điều kiện không liên quan. Ba
lần chạy ở ba trạng thái gieo thẳng vào CSDL dev mất **ba mươi giây**, và không
chạm `nghiem_thu_hien_hanh.json` một byte nào.

⭐ Đây là ca thứ tám của lớp lỗi cả buổi, và là ca **của chính tôi, về chính công
việc của tôi**: *"R4 cần một lượt chạy thật"* là một câu đúng về **cái tên** của
việc, sai về **nội dung** của nó.

### Ba khiếm khuyết chỉ lộ ra khi có dữ liệu thật ở từng trạng thái

**① Tiêu đề nói "Đang lồng tiếng" cho một lần chạy ĐÃ HỎNG.**

Template chỉ phân biệt `done` với *"mọi thứ còn lại"*. Khách có lượt hỏng đọc một
dòng nói việc đang chạy **ngay bên trên** một khung đỏ nói việc đã dừng.

⚠️ Mọi phép kiểm V5 trước đó đều đi qua đường xanh, nên **không bài nào chạm tới
nhánh này**. Nó không phải lỗi khó — nó là lỗi ở một nhánh chưa ai bước vào.

**② Đồng hồ "đã chạy" KHÔNG BAO GIỜ hiện ở dev và trong bộ test.**

```
tables.py   created_at: DateTime(timezone=True)   <- khai CO mui gio
SQLite      '2026-09-08 04:08:46.572361'          <- doc ra NAIVE
quan_sat    except TypeError: da_chay = None      <- nuot
```

Cùng một cột, hai kiểu giá trị tuỳ backend. Và nhánh nuốt làm nó **đúng ở
production, vô hình ở mọi chỗ ta nhìn** — kiểu lệch có thể sống rất lâu.

⇒ Sửa **nguyên nhân** (chuẩn hoá múi giờ: naive ở đây *chính là* UTC vì chỉ
`_now()` ghi cột này) thay vì giữ nhánh nuốt.

**③ `elapsed 621s`** — một con số, không phải một khoảng thời gian đọc được. Nay
hiện `12 minutes 46 seconds`, dùng lại chuỗi *"phút"/"giây"* đã có trong catalog.

### Đo được, ba trạng thái

| | tiêu đề | đồng hồ | đối chiếu | khối lỗi | htmx hỏi lại | nút |
|---|---|---|---|---|---|---|
| đang chạy | Dubbing in progress | `45% · 12 minutes 46 seconds` | — | — | ✅ | Huỷ |
| xong | Dubbed video | — | ✅ | — | — | Tải · Chạy lại · Video khác |
| hỏng | **Run did not finish** | — | — | ✅ | — | Thử lại bước này |

⭐ Cột `htmx hỏi lại` đáng nhìn: chỉ lượt **đang chạy** mới hỏi lại. Một trang đã
xong mà vẫn hỏi mỗi 3 giây là một vòng lặp vô ích chạy mãi — và nó nhân lên theo
số tab khách để mở.

`test_459` chốt cả ba trạng thái, **8 phép kiểm**, gồm cả chiều *"không bày thứ
mình không có"* — chiều mà một bộ kiểm chỉ đi đường xanh sẽ không bao giờ chạm.

### Còn lại, và nó là một mục nhỏ hơn hẳn

Dữ liệu ở §9 được **gieo**, nên nó chứng minh *giao diện dựng đúng*, không chứng
minh *mạch chạy đúng*. Thứ vẫn cần một lượt chạy thật là **thông điệp lỗi do
chính mạch ném ra** — hôm nay tôi dựng trạng thái lỗi bằng một chuỗi tự đặt.

⇒ Đó là một mục nhỏ, và nó thuộc việc **ghi lại bản bằng chứng** chứ không thuộc
`R4`.
