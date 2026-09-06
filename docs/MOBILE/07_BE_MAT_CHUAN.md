# Phase F — bề mặt chuẩn: đo 20 route, và một thứ tôi **không** sửa được

Đo 2026-09-05 ở 390×844, Chromium, 20 route khách hàng (kể cả
`/prompt-ai-ommi/classic` — trang Jinja cũ vẫn còn phục vụ).

## 1. Những thứ đã đạt, đo được

| hạng mục prompt 06 | kết quả |
|---|---|
| bảng tràn ra ngoài mà không có vùng cuộn | **0/20 route** |
| cột bảng bị `display:none` (giấu dữ liệu) | **0** |
| menu chỉ mở được bằng hover | **0** — cả 7 menu là `<details>`/`<summary>`, mở bằng chạm |
| nút phá huỷ nhỏ hơn 44px | **0** |
| tràn ngang 320–390px | **0** (xem `76bb448b`) |
| nhãn tiếng Anh làm vỡ layout | **0/15 route** ở `/en` |
| console error / status lạ | **0** |

⭐ `.tablewrap` đã bọc mọi bảng trong một vùng `overflow-x:auto`, nên bảng cuộn
trong chính nó thay vì đẩy trang — đúng yêu cầu *"card/scroll theo nghĩa, không
`display:none` dữ liệu quan trọng"*. Việc này **đã có sẵn**, không phải do lượt
soát này làm.

## 2. `inputmode` — 11 → 4

Trên iOS, `<input type="number">` **không** cho bàn phím số; nó cho bàn phím đầy
đủ có hàng số ở trên. `inputmode` mới là thứ đổi nó thành bàn phím số gọn.

Đã thêm cho **11 ô** ở 8 template Jinja + 3 app React:
`numeric` cho ô đếm/ngân sách, `decimal` cho ô có `step` thập phân (mốc thời
gian cue của Autosub).

Bốn ô còn lại đều là `type="search"` — bàn phím của nó vốn đã đúng và có phím
"Tìm", nên `inputmode="search"` là thừa. **Cố ý không thêm.**

## 3. ✅ Phóng to 200% — ĐÃ SỬA 06/09, và vì sao ba lần trước "không đổi"

Phóng to 200% trên máy 390px cho khung nhìn CSS **195px**. Trước 06/09, ở đó
**15/15 route tràn ngang**.

Đo lại sau bản vá (`tools/mobile_qa.py quet`, ba route công khai):

| khung | trước | sau |
|---|---|---|
| **p195** | `/` 117px · `/gia-api` 84px · `/huong-dan` 62px | **0 · 0 · 0** |
| p320 · p390 · p430 · tab768 · desk1440 | 0 | **0** (không hồi quy) |

### 🔑 Vì sao ba lần sửa trước đo ra "không đổi một pixel"

Các bản vá ấy **đúng**, nhưng chúng nhắm vào **thủ phạm phụ**. Chừng nào thủ
phạm **chính** còn đó, `document.scrollWidth` không nhúc nhích — nên một bản vá
đúng và một bản vá vô ích cho **cùng một con số**.

Đo 06/09 chứng minh điều đó từng bước:

```
sua .grid minmax(288px)      ->  `/` 312 -> 257   (co doi)
sua .dropdown min-width      ->  257 -> 257       (KHONG doi)
sua .dropdown position:fixed ->  257 -> 257       (KHONG doi)
sua .hdr-right flex-wrap     ->  257 -> 195       (SACH)
```

⇒ **"Đo lại không đổi" không chứng minh bản vá sai.** Nó chỉ chứng minh còn một
thứ khác lớn hơn. Hoàn tác dựa trên tín hiệu ấy là bỏ đi một bản vá đúng — và
đó chính là điều đã xảy ra ba lần.

### Cách khoanh được thủ phạm: ẩn từng con, đọc `scrollWidth`

Thứ phá được thế bế tắc không phải một giả thuyết hay hơn, mà là một **phép đo
phân biệt được**:

```
header.hdr scrollWidth = 257   (main va footer deu 195/195 -> sach)

an hdr-logo    -> 213
an hdr-nav     -> 257   (da display:none, khong doi)
an hdr-burger  -> 209
an hdr-right   -> 195   <- SACH
```

⭐ Phép ẩn-từng-con trả lời **trực tiếp** câu "ai gây ra", trong khi mọi phép đo
trước đó chỉ trả lời "ai trông rộng" — và hai câu ấy khác nhau, vì một hộp rộng
nằm trong một tổ tiên cuộn thì không đóng góp gì.

### Bốn bản vá, và ba trong bốn là cùng một hình dạng

| chỗ | trước | sau |
|---|---|---|
| `.grid` | `minmax(288px,1fr)` | `minmax(min(288px,100%),1fr)` |
| `.catbar .search` | `min-width:200px` | `min-width:min(200px,100%)` |
| `.dev-loc .dev-field.rong` | `min-width:200px` | `min-width:min(200px,100%)` |
| `.dropdown` / `.dropdown.right` | `min-width:214px` / `252px` | `min(…,calc(100vw - 20px))`, và **ghim theo khung nhìn** dưới 320px |
| `.hdr-right` | flex một hàng, không co được | `flex-wrap:wrap` dưới 320px |
| `.table` (`_kieu_chung.html`) | không vỏ cuộn, 45 chỗ / 22 template | `display:block;overflow-x:auto` dưới 320px |

🔑 Hình dạng lặp lại: **một `min-width` cứng lớn hơn khung nhìn**. Quét toàn bộ
`ltt.css` tìm `min-width:` > 195px ra **12** chỗ; 6 là `@media(min-width:…)`
(không phải lỗi), 2 nằm trong vỏ `overflow-x:auto` (**cố ý** —
`.ui-table` trong `.tablewrap`, `.lv-lo-bang` trong `.lv-lo-bang-boc`), 1 đã
được ghi đè ở `max-width:760px`, còn **3** là lỗi thật.

⚠️ Ngưỡng **320px** cho hai luật cuối là cố ý: WCAG 1.4.10 đòi reflow ở 320px và
nền tảng **đạt** ở đó. Dưới ngưỡng ấy là vùng ngoài chuẩn, nơi một bảng cuộn
được vẫn hơn một trang tràn ngang — còn đặt ngưỡng rộng hơn sẽ đổi hành vi trên
điện thoại thật (390px) mà không được lợi gì.

### Bộ dò cũng phải sửa — nó đang giấu chính thủ phạm

`tools/mobile_quet.js` lọc bỏ mọi phần tử có tổ tiên `overflow-x:auto`. Với
phần tử **`position:absolute`** thì luật ấy **sai**: chỉ **khối chứa** (tổ tiên
đã định vị gần nhất) mới cắt được nó, một tổ tiên `static` có `overflow-x` nằm
giữa thì không. Đó là lý do `.dropdown` không bao giờ xuất hiện trong danh sách
nghi can, dù nó rộng 214px trên một khung 195px.

Sửa thêm: bảng nay có thể **tự cuộn trong chính nó**, nên phép kiểm `bang_tran`
phải hỏi cả `overflow-x` của **chính** phần tử, không chỉ của tổ tiên — nếu
không nó báo "6 bảng không cuộn được" ngay sau khi cả sáu vừa được cho cuộn.

## 4. Còn lại của Phase F

- Copy IP/token ở `/vps`, `/developers`: chưa đo (VPS `enabled=False`).
- Trạng thái loading/empty/error của từng bề mặt: chưa đo có hệ thống.
- `reduced-motion`: `ltt.css` có khối `@media(prefers-reduced-motion:reduce)`,
  nhưng **chưa đo** là nó thật sự tắt mọi chuyển động trong 4 app React.
