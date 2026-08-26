# 05 — Nhật ký thi hành

Sáu đợt, mỗi đợt đo bằng trình duyệt trước khi sang đợt sau.
Số đo đầy đủ: `evidence/<nhãn>/do_dac.json`.

## Bảng chốt qua từng đợt

| | trước | đợt 1 | đợt 2 | đợt 6 | sau cùng |
|---|---|---|---|---|---|
| `.app-main` @1920 | **898 px** | 1318 | 1318 | 1318 | **1318 px** |
| `fieldset` viền `groove` | **18** | 18 | **0** | 0 | **0** |
| ô nhập viền `inset` | **42** | 42 | **0** | 0 | **0** |
| tài liệu tràn ngang | **8** | 8 | **0** | 0 | **0** |
| lỗi console | 0 | 0 | 0 | 0 | **0** |
| phản hồi ≥ 400 | 0 | 0 | 0 | 0 | **0** |

*(18 = 3 `fieldset` × 6 khung; 42 = 7 ô nhập × 6 khung)*

---

## Đợt 1 — Vỏ · bề rộng · nhịp chữ

**`server/templates/developers_base.html`** — thêm đúng một khối:

```jinja
{% block page_mode %}wide{% endblock %}
```

Khu API chưa bao giờ khai `page_mode`, nên nó rơi về mặc định `standard`
(`.page{max-width:1180px}`). Trừ 210px thanh bên + 24px khe ⇒ **898px** nội
dung trên một màn hình 1920.

`wide` là token **đã có** (`.page--wide{max-width:1600px}`) và là token khu VPS
đang dùng — không đặt một con số mới ở một chỗ mới.

**`ltt.css`** — `.dev-h1` 20px → 24px (nó đang **nhỏ hơn** `h2` trong chính
trang nó), thêm `.dev-dan` cho dòng dẫn dưới tiêu đề.

→ `.app-main` **898 → 1318 px (+47 %)** trên cả 16 trang.

---

## Đợt 2 — Primitive dùng chung

### (a) Vá lỗ hổng cấp nền tảng — `_kieu_chung.html`

| Sửa | Vì sao |
|---|---|
| `input[type=text\|password\|number\|email]` → `input:not([type=checkbox]):not([type=radio]):not([type=file])…` | một `<input>` **không có** thuộc tính `type` không khớp `input[type=text]` — thuộc tính phải **có mặt**. 5 ô nhập + 2 `type=search` rơi ra ngoài mọi luật của nền tảng |
| thêm `input[type=checkbox\|radio]{width:16px;height:16px;accent-color:var(--accent)}` | 5 app trước đây đều tự vẽ lại một bộ chip riêng — dấu hiệu một primitive còn thiếu |
| thêm `fieldset{border:0;padding:0}` + `legend` | mặc định trình duyệt là `2px groove` xám nổi 3D. Năm lớp app hiện có **đều đã tự đặt `border:0`** ⇒ luật chung chỉ nói ra thứ chúng đã làm |
| `button,.btn{border:none}` → `border:1px solid transparent` | `border:none` đặt `border-style:none`, nên `.btn.ghost` (chỉ đổi `border-color`) **không thể** thắng lại. Hậu quả đo được: không một nút nào trên `/developers/keys` có viền, và **mọi** nút đều đỏ đặc |
| `.btn-danger` nền `#b91c1c` đặc → viền + chữ đỏ, nền chỉ hiện khi rê chuột | một bảng bốn hàng với bốn nút đỏ đặc là bốn lần mất nhìn thấy cảnh báo |
| thêm `:disabled`, `::placeholder`, `[aria-invalid]` | ba trạng thái form chưa từng có kiểu |

⚠️ **Một thứ tôi đã thêm rồi rút lại.** Ban đầu tôi đổi `.btn` sang
`display:inline-flex; gap:7px; white-space:nowrap` cho đẹp. Quét trình duyệt 14
trang ngoài khu API thấy `/autosubvideo` có chín nút mẫu chữ tự vẽ bằng
`display:grid`, và `nowrap` sẽ ăn vào chữ mẫu bên trong chúng. **Không nguyên
nhân gốc nào đòi ba thuộc tính đó** ⇒ bỏ. Luật này chạm mọi trang của nền tảng;
bán kính nổ phải bằng đúng thứ cần sửa.

### (b) Lớp `.dev-*` — `ltt.css`, cuối tệp

`.dev-bang` (vỏ cuộn bảng) · `.dev-loc` (dải lọc) · `.dev-field`/`.dev-hang` ·
`.dev-nhom` · `.dev-chon` · `.dev-tt` (trạng thái) · `.dev-trong` (trạng thái
rỗng) · `.dev-mat` (bí mật hiện một lần) · `.dev-ma` (khối mã có nhãn) ·
`.dev-buoc` · `.dev-han-muc` · `.dev-gioi-han` · `.dev-hanh-dong` · `.dev-id`.

### (c) 19 bảng được bọc vỏ cuộn

Một lượt máy móc qua 11 template: `<table class="table">` → bọc `.dev-bang`.
⇒ **8 trường hợp tài liệu tràn ngang → 0.**

---

## Đợt 3 — Tổng quan *(cổng dừng)*

- 5 nút đỏ đặc → **1 chính + 4 phụ**.
- Dòng hạn mức văn xuôi → `<dl class="dev-han-muc">` ba cặp nhãn–giá trị.
- `.dev-buoc` — lớp này **được template dùng từ 25/08 và chưa bao giờ được định
  nghĩa**, nên danh sách quan trọng nhất của khu (Golden Outcome A) vẫn vẽ bằng
  `<ol>` mặc định. Nay có huy hiệu số, và bước đã xong đổi **cả** huy hiệu lẫn
  dấu ✓ trong chữ.

⭐ **Soi trình duyệt bắt được thứ test không bắt:** bốn chuỗi mới hiện ra
**tiếng Việt trên bản EN**. `test_299` chốt điều này, nhưng chỉ khi chuỗi đã có
mục trong `.po`. Đã thêm tay 4 mục.

Cổng dừng: Tổng quan trông đúng ⇒ đi tiếp.

---

## Đợt 4 — Khóa API + Hoạt động

**`dev_keys.html`** — viết lại:
- bảng: trạng thái thành `.dev-tt` có màu ngữ nghĩa; bốn ràng buộc gộp vào một
  cột "Giới hạn" (`.dev-gioi-han`) thay vì tràn ra cột "Phạm vi" thành tường
  `<code>` cao bốn dòng; hành động thành một hàng `.dev-hanh-dong`;
- "Thu hồi" và "Đổi bí mật" **đều hỏi lại** — cả hai đều không đảo ngược được ở
  mức tích hợp đang chạy;
- form: `.dev-field`/`.dev-hang`/`.dev-nhom`/`.dev-chon`, thêm dòng gợi ý cho
  từng trường;
- khối bí mật → `.dev-mat` + `role="alert"`; **`<code>` giữ nguyên** vì đó là
  hình dạng `test_191` đọc để chứng minh plaintext chỉ sống ở phản hồi đó;
- trạng thái rỗng có bước tiếp.

**`dev_logs.html`** — viết lại:
- dải lọc bốn ô xếp chồng (mỗi ô 850px, cao ~180px) → **một hàng** `.dev-loc`;
- `<strong>200</strong>` và `<strong>500</strong>` cùng hình dạng cùng màu →
  `.dev-tt` xanh/hổ phách/đỏ, **chữ vẫn là chữ thật**, mã lỗi xuống dòng dưới;
- hai gạch đầu dòng trộn ba con số với một câu chính sách → `.dev-han-muc` +
  câu chính sách xuống cuối trang;
- trạng thái rỗng phân biệt "chưa gọi bao giờ" và "không khớp bộ lọc", mỗi cái
  một bước tiếp khác nhau.

⚠️ **Một chỗ đo rồi mới sửa:** hai nút hành động vẫn xếp chồng sau lần sửa đầu.
Đo: cột được chia 128px, hai nút cần 91+60+6 = **157px**. `flex-wrap:nowrap` làm
bề rộng tối thiểu của flex container thành tổng các nút, thuật toán bảng tự chia
đủ. *(Không đoán — nếu đoán, tôi đã đi thu nhỏ nút.)*

Chạy `pytest` 6 tệp hợp đồng khu API: **104 passed, 1 skipped.**

---

## Đợt 5 + 6 — Các trang còn lại

`dev_projects` · `dev_jobs` · `dev_notifications` · `dev_settings` ·
`dev_privacy` · `dev_webhooks` · `dev_usage`:
trạng thái rỗng có bước tiếp, trạng thái có màu ngữ nghĩa, dải lọc một hàng,
hành động một hàng với nút nguy hiểm dạng viền, khối bí mật webhook dùng chung
`.dev-mat` thay vì một thẻ viền cam viết cứng.

**`dev_privacy.html`**: `.tablewrap`+`.ui-table` → `.dev-bang`+`.table`, để cả
khu có **một** ngôn ngữ bảng.

**`btn-primary`** — lớp này **không tồn tại ở đâu trong nền tảng**; nó im lặng
rơi về `.btn` đỏ đặc. Bỏ khỏi 7 template khu API.
⛔ **Không** định nghĩa nó toàn cục: `apps/prompt_ai_ommi` dùng `btn-primary`
**độc lập** (không kèm `.btn`), nên thêm một luật toàn cục sẽ đổi giao diện app đó.

### 🔴 Một lỗi NỘI DUNG, không phải lỗi trình bày

`dev_settings.html` viết:

> *"Xuất và xoá dữ liệu tích hợp là hạng mục riêng, **chưa có ở bước này**.
> Trong lúc chờ, liên hệ hỗ trợ kèm mã khóa công khai."*

Trong khi `/developers/privacy` và `/developers/privacy/export` **đã chạy**, và
chính nó là **mục con của trang đang nói câu ấy**. Một trang bảo khách đi liên hệ
hỗ trợ để làm một việc họ tự bấm được. Đã sửa thành liên kết tới trang đó.

⚠️ Không test nào bắt được loại lỗi này — nó đúng cú pháp, đúng bản dịch, đúng
route. Chỉ đọc trang mới thấy.

---

## Bản dịch

**56 mục thêm vào `locale/en/LC_MESSAGES/messages.po`**, tất cả **thêm tay**,
mỗi mục có cả `msgid` lẫn `msgstr` không rỗng, giữ LF. Rồi `i18n.py bien-dich`.

⛔ **Không chạy `i18n.py trich` lần nào** — nó sắp xếp lại cả tệp, và một phiên
khác đo được ngày 26/08 rằng `msgmerge` tự sinh **25 bản dịch SAI** khi trích lại.

⚠️ **Một cái bẫy tôi đã tự đâm vào:** phép kiểm đầu của tôi dùng
`grep 'msgid "<chuỗi đầy đủ>"'` và báo **29 chuỗi thiếu**. Đọc lại bằng
`babel.messages.pofile.read_po` thì thật ra chỉ **24** — `msgid` dài bị `.po`
cắt thành nhiều dòng nên regex ngây thơ **không bao giờ khớp**, và nó sai **về
phía báo động**. Phép kiểm cuối dùng babel, và nó báo **0 thiếu** cho khu API.

---

## Tệp công cụ mới

| Tệp | Việc |
|---|---|
| `tools/dev_portal_harness.py` | dựng một bản `/developers` **có dữ liệu** trên cổng riêng, CSDL SQLite tạm — 2 project, 4 khóa (một đã thu hồi, một test), 10 dòng nhật ký gồm 402/429/422/500, webhook có 3 lần giao hỏng, 1 ngân sách. **Không chạm production.** |
| `tools/qa/dev_portal_qa.js` | quét 16 trang × 6 khung, chụp ảnh **và đo** năm chốt |
| `tools/qa/dev_portal_golden.js` | bốn Hành trình Vàng + hồi quy bảo mật, trên trình duyệt thật |
