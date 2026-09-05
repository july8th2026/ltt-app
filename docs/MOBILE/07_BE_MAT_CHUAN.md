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

## 3. 🔴 Phóng to 200% — đo được, và tôi KHÔNG sửa được

Phóng to 200% trên máy 390px cho khung nhìn CSS **195px**. Ở đó **15/15 route
tràn ngang** 2–101px, với con số **56px lặp lại ở chín route**.

### Ba lần sửa, ba lần không đổi một pixel

| tôi nghĩ thủ phạm là | đã sửa | kết quả đo lại |
|---|---|---|
| `.dropdown{min-width:214px}` | `min(214px, calc(100vw - 16px))` | **56px, không đổi** |
| `.dropdown.right{min-width:252px}` | `min(252px, …)` | **56px, không đổi** |
| hình học dropdown neo theo cha | `@media(max-width:240px)` → `position:fixed` | **56px, không đổi** |

Lượt cuối đã kiểm tận nơi rằng CSS **thực sự tới trang**: `min-width` tính ra
`0px`, `position` tính ra `fixed`. Luật chạy. Triệu chứng không đổi.

⛔ **Nên cả ba thay đổi đã được hoàn tác.** Một luật CSS không dời được phép đo
nào là một luật sẽ bị người sau đọc như một lời giải thích — và nó sẽ giải thích
sai. Kho này đã có năm ca "luật tồn tại mà không làm gì" ghi trong `CHECKPOINT.md`;
không thêm ca thứ sáu bằng chính tay mình.

### Vì sao dừng ở đây, và nó có thật sự quan trọng không

WCAG 1.4.10 (Reflow) đòi nội dung chạy lại ở bề ngang **320 CSS px**. Ở 320px
nền tảng này **đạt: 0/20 route tràn**. 195px là chặt hơn tiêu chuẩn.

⇒ Ghi lại là **phát hiện đã đo, chưa sửa, ngoài phạm vi bắt buộc** — không phải
một lỗi đang chờ, cũng không phải một thứ đã xong.

### Cái đã loại trừ, để người sau không đo lại

- ✗ không phải `.dropdown` / `.dropdown.right` (đã thử, không đổi)
- ✗ không phải bảng — `.tablewrap` cuộn trong chính nó (`w=147, sw=680`)
- ✗ không phải bản dịch — `/en` sạch ở mọi route
- ✓ `header.hdr` có `scrollWidth 250` trong khi `clientWidth 195`, và
  `main.page` có `scrollWidth 208`. `document.scrollWidth` = 251 ⇒ **header là
  phần đóng góp chính**, nhưng bốn con trực tiếp của nó kết thúc ở x=185 (vừa).
  Phần dôi ra đến từ một hậu duệ định vị tuyệt đối mà tôi chưa khoanh được.

⚠️ Và một ghi chú về **bộ đo**: bộ dò tràn xếp theo `getBoundingClientRect().right`
đã chỉ nhầm thủ phạm **ba lần** trong phiên này, vì nó báo cả phần đã bị một tổ
tiên `overflow-x:auto` hấp thụ. Bản lọc theo tổ tiên cuộn được sửa ở
`76bb448b` giúp cho ca 320px, nhưng ở 195px thủ phạm là một hậu duệ tuyệt đối —
một lớp mà bộ lọc ấy chưa xử lý.

## 4. Còn lại của Phase F

- Copy IP/token ở `/vps`, `/developers`: chưa đo (VPS `enabled=False`).
- Trạng thái loading/empty/error của từng bề mặt: chưa đo có hệ thống.
- `reduced-motion`: `ltt.css` có khối `@media(prefers-reduced-motion:reduce)`,
  nhưng **chưa đo** là nó thật sự tắt mọi chuyển động trong 4 app React.
