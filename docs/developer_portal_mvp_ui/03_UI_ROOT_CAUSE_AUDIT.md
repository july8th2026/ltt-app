# 03 — Nguyên nhân gốc của giao diện yếu

Đo bằng trình duyệt thật (Chromium qua `playwright-cli`) ngày **2026-08-26**
trên một bản `/developers` **có dữ liệu**, chạy cách ly ở cổng 8101
(`tools/dev_portal_harness.py` — 2 project, 4 khoá gồm một khoá đã thu hồi và
một khoá test, 10 dòng nhật ký gồm 402/429/422/500, 1 webhook có 3 lần giao
hỏng, 1 ngân sách).

Ảnh + số đo: `evidence/before/` · `evidence/before/do_dac.json`
Bộ chạy lại: `tools/qa/dev_portal_qa.js`

> ⚠️ Mọi mục dưới đây là **số đo**, không phải cảm nhận. Triệu chứng chủ sản
> phẩm nêu ("quá basic", "nhiều khoảng trắng") đều quy về đúng sáu nguyên nhân.

---

## RC-1 — Khu API chưa bao giờ khai bề rộng trang · **P1**

**Đo @1920×1080, cả 16 trang, không sai một trang nào:**

```
main.page  = 1180 px
.app-shell = 1132 px
.app-main  =  898 px      ← nội dung thật
```

**898 / 1920 = 47 %.** Hơn một nghìn pixel bỏ trống mỗi màn hình.

**Vì sao.** `base.html:107` đặt `{% block page_mode %}standard{% endblock %}`,
và `ltt.css:271` định nghĩa `.page{max-width:1180px}`. `developers_base.html`
**không override block đó**. Trừ 210px thanh bên + 24px khe ⇒ 898px.

Khu VPS thì có: `vps_base.html:17` → `{% block page_mode %}wide{% endblock %}`
→ `.page--wide{max-width:1600px}` (`ltt.css:273`).

⭐ Đây **không phải** thiếu một hệ thống bố cục. Hệ thống đã có, có bốn mức
(`standard` 1180 · `catalog` 1600 · `wide` 1600 · `immersive` 1800), và khu API
là khu duy nhất trong nhóm "nhiều dữ liệu" quên khai. Một dòng.

⛔ Và nó giải thích luôn vì sao bảng khoá trông chật: 8 cột trong 810px thì
tên khoá phải xuống ba dòng, không phải vì bảng thiết kế tệ.

---

## RC-2 — Nền tảng chưa bao giờ có kiểu cho bốn loại control · **P1**

`_kieu_chung.html` chọn ô nhập **theo thuộc tính `type`**:

```css
input[type=text], input[type=password], input[type=number], input[type=email],
select, textarea { … }
```

Bốn thứ **không khớp luật nào trong toàn bộ nền tảng**:

| | Ở đâu | Trình duyệt vẽ ra gì (đo được) |
|---|---|---|
| `<input>` **không có `type`** | keys ×3 · projects ×1 · usage ×1 | `bg rgb(59,59,59)` · `2px inset rgb(133,133,133)` · `radius 0` · `padding 1px/2px` |
| `input[type=search]` | logs ×1 · tools ×1 | y hệt trên |
| `input[type=checkbox|radio]` | keys ×13 · usage ×1 | 13×13px mặc định, không `accent-color` |
| `fieldset` / `legend` | keys ×3 | **`2px groove rgb(107,107,107)`** |

So với ô ĐƯỢC vẽ (`select` ngay bên cạnh trong cùng form):

```
select :  bg rgb(27,20,19)   1px solid rgb(56,36,34)   radius 6px   padding 9/10px
input  :  bg rgb(59,59,59)   2px inset rgb(133,133,133) radius 0px   padding 1/2px
```

⇒ Cái gọi là *"giống trang HTML thô"* chính là hai ô này nằm cạnh nhau, cách
nhau 12 pixel, trong cùng một cái thẻ. Ảnh: `evidence/before/1920/keys.png`.

⭐ **Đây là lỗ hổng cấp nền tảng, không phải của riêng khu API.** Bằng chứng:
mọi app từng cần checkbox đều tự vẽ lấy một bộ riêng —
`.tv-*` (video) · `.th-*` (thumbnail) · `.im-*` (ảnh) · `.clip-*` (clip) ·
`.up-*` (upscale). Năm lần dựng lại cùng một thứ là dấu hiệu của một primitive
còn thiếu, không phải của năm app cẩu thả.

Khu API là app **duy nhất không tự vẽ**, nên nó là app duy nhất lộ ra.

---

## RC-3 — Bảng không có vỏ cuộn, nên tài liệu tràn ngang · **P1**

`ltt.css:124` có sẵn `.tablewrap{overflow-x:auto}` — nhưng nó đi cặp với
`.ui-table`, còn 8 template `dev_*` dùng `<table class="table">` **trần**.
Đo: `parentOverflowX = visible`.

**Tám lần tài liệu tràn ngang thật:**

| Khung | Trang | Tài liệu | Thủ phạm |
|---|---|---|---|
| 1024 | keys | 1087 > 1024 | `table.table` |
| 768 | keys | 853 > 768 | `table.table` |
| 390 | keys | 853 > 390 | `table.table` |
| 390 | logs | 667 > 390 | `table.table` |
| 390 | usage | 410 > 390 | `table.table` |
| 390 | tools | 448 > 390 | `code` |
| 390 | quickstart | 422 > 390 | `table.table` |
| 390 | webhooks | 589 > 390 | `table.table` |

Đây là mục "No systemic document overflow" của Definition of Done, đang đỏ.

---

## RC-4 — HAI bộ từ vựng thành phần, và bộ thắng là bộ nghèo hơn · **P2**

| Thành phần | `ltt.css` (`<link>`, nạp TRƯỚC) | `_kieu_chung.html` (`<style>`, nạp SAU → **thắng**) |
|---|---|---|
| thẻ | `.ui-card` | `.card` |
| ô nhập | `.inp` / `.ui-input` | `input[type=…]` |
| bảng | `.tablewrap` + `.ui-table` | `table` / `.table` |
| nút phụ | `.btn.ghost` | `.btn-ghost` |
| nút nguy hiểm | `.btn.danger` *(nền trong, viền đỏ)* | `.btn-danger` *(nền `#b91c1c` đặc)* |
| nhãn trạng thái | `.badge` *(inline-flex, có chấm)* | `.badge` *(inline-block, không chấm)* |

Template `dev_*` dùng bộ thứ hai. Hậu quả đo được trên `/developers/keys`:

```
button.btn           bg=rgb(239,55,49)   border=0px none
button.btn btn-danger bg=rgb(185,28,28)  border=0px none
button.btn btn-primary bg=rgb(239,55,49) border=0px none   ← lớp KHÔNG TỒN TẠI ở đâu cả
```

**Không một nút nào trên trang có viền, và mọi nút đều đỏ đặc.** Bảng khoá có
6 nút đỏ đặc xếp thành hai cột. Đó chính là triệu chứng "red glow everywhere"
mà bản tóm yêu cầu tránh — và nguyên nhân là `border:none` trong
`_kieu_chung.html` đè lên `.btn.ghost` của `ltt.css` (lớp ghost chỉ đặt
`border-color`, không đặt `border-style`, nên nó thua).

`btn-primary` được dùng ở 3 template và **không được định nghĩa ở đâu**, nên nó
im lặng rơi về `.btn` đỏ đặc.

---

## RC-5 — Không có primitive cho hàng form và dải lọc · **P2**

`input, select { width:100% }` (`_kieu_chung.html`) + `<form>` không có bố cục
= mọi control giãn hết bề ngang và **xếp chồng dọc**.

`/developers/logs` @1920: ô tìm + 3 ô chọn, mỗi ô **850px**, xếp bốn tầng, cao
tổng cộng ~180px cho một dải lọc.
Ảnh: `evidence/before/1920/logs.png`.

Template viết form bằng `<p><label>…<br><input></p>` — không có `.row`/`.field`
(chúng **có** trong `_kieu_chung.html`, chỉ là không trang nào dùng).

---

## RC-6 — Trạng thái không được mã hoá, nên trang gỡ lỗi không gỡ được gì · **P2**

`dev_logs.html` in `<strong>{{ row.status }}</strong>`. Trên màn hình, `200` và
`500` là **cùng một hình dạng, cùng một màu**. Mắt không có gì để bắt.

Nền tảng đã có `.badge` + `.b-ok/.b-warn/.b-err` (có chấm màu **và** chữ) —
khu API không dùng ở bảng nhật ký, bảng job hay bảng khoá (`status` in trần:
`active` / `revoked`).

Đây là Golden Outcome **D** đang hụt: *"REQUEST → STATUS → ERROR CODE"* mà
STATUS không nhìn thấy được.

---

## Ba thứ tôi đã kiểm và **KHÔNG** phải nguyên nhân

Ghi ra để phiên sau không đi lại:

1. **KHÔNG có hai vỏ.** Chỉ một: `base.html` → `main.page` → `.app-shell` →
   `.app-side` + `.app-main`. Không tệ nạn shell thứ hai. `developers_base.html`
   dùng lại đúng primitive của khu VPS như chú thích của nó đã hứa.
2. **KHÔNG có lỗi JavaScript và KHÔNG có request hỏng.** Quét 16 trang × 6 khung:
   `loi console: 0`, `phan hoi >=400: 0`.
3. **Điều hướng KHÔNG hỏng.** Ba nhóm, 10 mục, mục cha sáng khi đứng ở mục con,
   đúng một `aria-current="page"`. Phần này đã tốt và không nên đụng vào.

---

## Xếp hạng

| | Nguyên nhân | Ảnh hưởng | Sửa ở đâu |
|---|---|---|---|
| P1 | RC-1 bề rộng | 16/16 trang | 1 dòng ở `developers_base.html` |
| P1 | RC-2 control thô | keys · logs · tools · usage · projects | ~10 dòng ở `_kieu_chung.html` (cấp nền tảng) |
| P1 | RC-3 tràn ngang | 8 trường hợp đo được | vỏ cuộn, lớp `.dev-*` + 8 template |
| P2 | RC-4 hai từ vựng | mọi nút, mọi bảng | thống nhất về một bộ, ở lớp `.dev-*` |
| P2 | RC-5 không có hàng form | keys · logs · usage · tools · pricing | primitive `.dev-*` + migrate template |
| P2 | RC-6 trạng thái không mã hoá | logs · jobs · keys · webhooks | dùng `.badge` sẵn có |

**Bốn trong sáu nguyên nhân là CSS/template dùng chung.** Theo §32 của bản giao
việc, phần đó thi hành thẳng. Không nguyên nhân nào đòi đổi route, hợp đồng
bảo mật, backend hay giá.
