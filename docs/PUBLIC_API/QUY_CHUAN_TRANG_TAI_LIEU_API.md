# Quy chuẩn trang tài liệu API

**2026-08-25.** Chốt trước khi ta có hệ thống API thứ hai, chứ không phải sau.

> Lý do viết bây giờ: hôm nay ta có **một** khu API. Ngày có hai, mỗi khu sẽ tự
> mọc một cách trình bày riêng, và không ai đủ động lực gom lại. Quy chuẩn rẻ
> lúc này và đắt về sau.

Tham chiếu đã soi bằng trình duyệt thật: `plenxai.com/developer` (25/08). Tài
liệu này **không** chép giao diện của họ — nó rút ra **quyết định nào đúng** và
ghi lại kèm lý do, để lần sau không phải soi lại.

---

## 1. Ba khu, tách bằng thanh bên — không trộn

```
API Keys        thứ gắn với TÀI KHOẢN   → sau đăng nhập
Usage           thứ gắn với TÀI KHOẢN   → sau đăng nhập
Documentation   thứ giúp QUYẾT ĐỊNH MUA → CÔNG KHAI
```

Đó là ranh giới của trang tham chiếu. **Ranh giới của ta khác một chỗ, và đó là
chốt của chủ sản phẩm (25/08):**

> **TOÀN BỘ `/developers/*` đứng sau đăng nhập.** Hệ thống API của LTT phải
> đăng nhập mới kích hoạt được, nên cả khu đó là khu **của tài khoản**, không
> phải khu bán hàng.

⚠️ Chốt này đã đi qua hai nhịp, ghi cả hai để không ai đọc nửa chừng: nhịp đầu
chủ sản phẩm bác riêng `tools`; nhịp sau chốt **cả khu**. Bản đang thi hành là
nhịp sau. `TRANG_CONG_KHAI` trong `server/routes/developer/_chung.py` (tách gói
thành nhiều tệp sau 25/08, trước đó là một tệp `developer.py` duy nhất) là
**tập rỗng**.

⇒ Ranh giới thi hành:

| Công khai | Sau đăng nhập |
|---|---|
| `/gia-api` — giá | **toàn bộ `/developers/*`** |
| `/huong-dan` — cách cắm vào công cụ | tools · quickstart · keys · usage |
| `/huong-dan/cong-cu` — tải công cụ cắm | logs · webhooks · playground · docs · cli |
| `/status/api` — tình trạng | |
| `/tai/…` — bộ cài + SDK | |
| `/api/v1/openapi.json` — đặc tả máy đọc | |

Đã đo lại sau khi chốt: mọi `/developers/*` trả `303`, năm đường công khai trả
`200`.

⭐ Cách phân biệt, để lần sau không phải hỏi lại: **thứ trả lời "có đáng mua
không" thì công khai; thứ trả lời "tôi đang dùng cái gì" thì sau đăng nhập.**
Giá và cách cắm thuộc vế thứ nhất. Danh mục công cụ đang mở cho *tài khoản này*
thuộc vế thứ hai.

⛔ Cái ta thật sự đặt sai và đã sửa 25/08 là **hướng dẫn cắm** và **đường tải
công cụ/SDK**: chúng nằm sau `require_account`, nên người đang cân nhắc không
đọc được một dòng nào và không lấy được tệp nào.

---

## 2. Quick Start là **ba bước**, nằm ngay đầu, không cuộn

Một dải ngang, đánh số, mỗi bước một câu:

```
① Tạo API key   →   ② Gửi request kèm header <tên header>   →   ③ Lấy kết quả
```

⭐ Ba bước là **hợp đồng vận hành** của cả khu API, không phải trang trí. Ai đọc
xong ba dòng đó là biết mình sẽ phải làm gì, kể cả trước khi hiểu từng endpoint.

⚠️ Nếu một khu API không tóm được vào ba bước thì vấn đề nằm ở **thiết kế API**,
không nằm ở trang tài liệu.

---

## 3. Nhóm theo **NĂNG LỰC**, và nêu cơ chế xác thực ngay ở tiêu đề nhóm

```
Image & Video Generation (X-API-Key)
Status & Polling
Text Generation API (X-API-Key)
Media Upload API (X-API-Key)
Error Handling
```

Không nhóm theo tài nguyên (`/jobs`, `/artifacts`) mà theo **việc khách muốn
làm**. Cơ chế xác thực nằm trong tiêu đề vì nó là thứ khác nhau giữa các nhóm và
là thứ hỏng đầu tiên.

⭐ `Status & Polling` tách riêng vì nó là **bước ③ dùng chung** cho mọi endpoint
bất đồng bộ. Nhắc lại nó trong từng endpoint là ba bản sao sẽ lệch.

---

## 4. Thẻ endpoint: **mặc định gập**, mở một cái mỗi lần

Dòng gập chỉ có ba thứ:

| | |
|---|---|
| Nhãn method | tô màu theo động từ: `POST` xanh lá · `GET` xanh dương · `DELETE` đỏ |
| Đường dẫn | phông đơn cách |
| Một dòng mô tả | *một* dòng, không hai |

⭐ VÌ SAO GẬP. Toàn bộ bề mặt API lọt vào **một màn hình** dưới dạng danh sách
quét được. Trải phẳng thì trang dài 4.000 pixel và không ai nhìn thấy cái thứ
hai. Đây là lỗi trang `/huong-dan` của ta đang mắc: 22 KB xếp chồng.

---

## 5. 🔴 Điều quan trọng nhất: **bảng tham số là hàm của (endpoint, MODEL)**

Trong thẻ đã mở, thứ tự cố định:

```
① Chip chọn model        (chip đang chọn được tô đậm)
② Một dòng model đó là gì
③ BẢNG THAM SỐ           TÊN · LOẠI · BẮT BUỘC · MÔ TẢ
④ Ví dụ request          sinh theo ĐÚNG model đang chọn
⑤ Phản hồi 200 OK
```

Đổi chip thì **cả bốn thứ dưới đổi theo** — đo thật khi bấm từ *Nano Banana PRO*
sang *Flux 2 Pro*:

| | Nano Banana PRO | Flux 2 Pro |
|---|---|---|
| `model` (mã trong bảng) | `nano-banana-pro` | `flux-2-pro` |
| `resolution` cho phép | `1k, 2k, 4k` | `1k, 2k` |
| `aspect_ratio` cho phép | 6 giá trị | 8 giá trị **khác** |
| tham số riêng | `references_urls` (tối đa 8) | `negative_prompt` |

⛔ **Một tham số CÓ ở model này và KHÔNG có ở model kia.** Nên viết tham số dưới
dạng văn xuôi chung cho cả endpoint là nói dối một nửa số model. Đây là lý do
mô hình "một endpoint, N model, schema theo model" phải là quy chuẩn, không phải
lựa chọn.

### ⭐ Và chỗ ta phải làm KHÁC — làm tốt hơn

Bảng của họ trông như **gõ tay**. Của ta **không được phép** gõ tay:

> **Bảng tham số phải sinh từ `input_schema` của `ToolSpec`.**

Ta đã đóng băng hợp đồng ở `tests/golden/public_api_catalog_v1.json` và có bước
gate `anh chup hop dong` (thêm 25/08) chặn mọi thay đổi không chủ ý. Sinh bảng từ
chính hợp đồng đó nghĩa là **trang tài liệu không thể trôi khỏi API** — cùng luật
mà `/gia-api` đã theo khi lấy số từ `bang_gia()` thay vì gõ lại.

⚠️ Gõ tay một bảng tham số là tạo bản sao thứ hai của hợp đồng. Bản sao đó sẽ
lệch, và nó lệch **âm thầm**: khách đọc trang, gửi tham số theo trang, nhận `422`.

---

### ⚠️ Ta đang ở đâu so với chốt này (25/08) — nói thẳng, không tô

Bảng tham số của ta **đã sinh từ `input_schema`** và đã hiển thị ngay trong thẻ
gập của danh mục (`_tham_so` dùng chung cho cả danh mục lẫn trang riêng). Phần
**chưa** có là chip model:

> Hợp đồng của ta hiện **không cho schema thay đổi theo model**. Một `ToolSpec`
> có đúng một `input_schema`; `build_models` chỉ ánh xạ model → *danh sách công
> cụ nhận nó*, chứ không mang schema riêng.

⇒ Thứ đóng vai trò đó ở ta là **`x-ltt-only-when`** — tham số có ở chế độ này
và không có ở chế độ kia (`image_key` chỉ dùng với `edit`/`subject`). Nó lấy từ
hợp đồng, và trang hiện nó như một nhãn riêng chứ không chôn vào văn xuôi.

⛔ **Đừng dựng chip model bằng cách gõ tay bảng cho từng model.** Làm vậy là tạo
đúng cái bản sao thứ hai mà mục 5 vừa cấm. Ngày cần chip model thật thì việc
phải làm là **cho `ToolSpec` khai schema theo model**, rồi trang tự có.

---

## 6. Ví dụ phải **chạy được**, và phải khớp model đang chọn

```
Ví dụ request cho Flux 2 Pro          [BASH] [Copy]
curl -X POST https://…/generate/image \
  -H "X-API-Key: pk_your_api_key_here" \
  -d '{ "model": "flux-2-pro", … }'

Phản hồi 200 OK                        [JSON] [Copy]
```

Bốn luật:

1. **Nút Copy trên mọi khối mã**, kèm nhãn ngôn ngữ ở góc (`BASH`, `JSON`).
2. Thân ví dụ mang **đúng** `model` của chip đang chọn — không phải một ví dụ chung.
3. Chỗ điền khoá là một **placeholder nhìn ra ngay là placeholder**
   (`pk_your_api_key_here`), không bao giờ là khoá thật.
4. Kèm **phản hồi thành công**, không chỉ request. Khách cần biết hình dạng trả
   về để viết bộ giải mã trước khi gọi lần đầu.

---

## 7. Giá đứng cạnh endpoint, không ở một trang xa

Họ đặt một dòng `Servers: [business]` + nút **Xem giá** ngay trong thẻ.

⭐ Quyết định mua xảy ra lúc đọc endpoint, không phải lúc mở trang giá. Với ta,
liên kết đó trỏ `/gia-api` và **số phải lấy từ hàm ra hoá đơn**, không gõ lại.

---

## 7b. 🔴 Trang CẮM: một ô chọn, toàn bộ bên dưới vẽ lại

**Tham chiếu thứ hai, soi thật 25/08: `api.nghimmo.com/huongdan`.** Nó giải một
bài toán **khác** với plenxai, và trộn hai bài toán đó vào một trang là lý do
trang cắm của ta trước đây dài 133 dòng.

| Trang | Trả lời câu | Cơ chế |
|---|---|---|
| plenxai | *"endpoint này nhận gì?"* | thẻ endpoint **gập**, chip model sinh lại bảng tham số |
| nghimmo | *"làm sao cắm được?"* | **một** ô chọn ở đầu, không điều hướng, không rời trang |

Đo thật khi bấm từ *Key Claude* sang *Key Codex*:

| | Key Claude | Key Codex |
|---|---|---|
| Base URL | `api.nghimmo.com` | `api.nghimmo.com/v1` |
| Dòng cảnh báo | "Không có /v1" | "Luôn có /v1. Key Codex không chạy Claude Code." |
| Bảng model | chip + danh sách chép được | bảng `MODEL / DÙNG KHI` |
| Tab cài đặt | Claude Desktop · Claude Code CLI · … | ChatGPT/Codex · Cursor Pro · … |

⭐ Khách **không bao giờ nhìn thấy thứ không áp dụng cho mình.** Đó không phải
tiện nghi — nó là **an toàn**.

⛔ **Vì sao là an toàn, không phải thẩm mỹ.** Trang cắm của ta trước 25/08 xếp
chồng cả năm bề mặt, nên hai giá trị **dễ sai nhất** của cả khu API nằm cạnh
nhau trên cùng một màn hình, không có gì nói cái nào của ai:

```
địa chỉ   /api/v1  ><  /api           lệch đúng bốn ký tự
model     ltt-3.8  ><  ...-compat     chỉ Claude Desktop
```

Chép nhầm thì Codex nhận `404`, hoặc nút gửi của Claude Desktop **im lặng
không làm gì cả**. Cả hai triệu chứng đều vô dụng. Một trang hướng dẫn không
được phép là thứ dựng nên cái bẫy đó.

⇒ **Quy chuẩn:** khi một khu API có **nhiều hơn hai bề mặt tích hợp**, trang
cắm phải là **một ô chọn + N khu**, không phải N khu xếp chồng. Mỗi khu tự nó
đủ để cắm xong một công cụ: địa chỉ, tên model, các bước, và **cảnh báo riêng
của bề mặt đó**.

⚠️ Ba ràng buộc thi hành, cả ba đều đã trả giá ở dự án này:

1. **Không có JS thì hiện hết**, mỗi khu một tiêu đề. Script chỉ được **ẩn
   bớt**, không được **dựng ra** — nên nó không thể làm trang trống.
2. **Văn xuôi không nằm trong module sinh mã.** `examples.py` cố ý không có bộ
   dịch; một câu tiếng Việt viết ở đó hiện ra **mất dấu**. Đã mắc đúng lỗi này
   25/08 và sửa tại chỗ.
3. **Không gõ lại giá trị nào.** Địa chỉ và tên model đến từ cùng module mà
   công cụ `.exe` ghi ra. Ba nơi cùng một nguồn là ba nơi không thể lệch nhau.

---

## 7b-bis. ⚠️ Gỡ bẫy ở một cấp thì phải kiểm cấp dưới nó

Sau khi tách năm bề mặt thành năm khu, tôi tuyên bố cái bẫy "hai địa chỉ cạnh
nhau" đã đóng. Một phép kiểm viết ngay sau đó nói ngược lại:

```
khu `vscode` khai /api nhưng đoạn mã trong khu dùng /api/v1
```

Và nó đúng. **Khu VS Code phục vụ HAI tiện ích** — Claude Code (`/api`) và
Codex (`/api/v1`) — nhưng bảng *Kết nối* chỉ có một dòng địa chỉ. Bảng đó
**nói đúng một nửa khu và sai nửa còn lại**.

⛔ Tôi gỡ bẫy ở cấp *"năm bề mặt xếp chồng"* rồi **dựng lại chính nó** ở cấp
*"một bề mặt, hai công cụ"*. Nếu phép kiểm không bắt thì nó đã lên production.

⇒ **Quy chuẩn:** một khu phục vụ nhiều hơn một công cụ thì bảng Kết nối phải có
**một dòng cho mỗi công cụ** (`dia_chi_theo`), không phải một dòng gộp.

⇒ **Và phép kiểm bắt được nó phải tồn tại**, vì đây là loại lỗi mà người viết
trang không thấy: người viết biết dòng địa chỉ nói về tiện ích nào, khách thì
không.

⭐ Kết luận đúng cho cả mục này, và nó rộng hơn chuyện địa chỉ:

> **Hiểu một lớp lỗi không làm ta miễn nhiễm với nó; chỉ một phép đo mới làm
> được.**
>
> *(phiên VPS, 25/08 — họ mắc lại lớp lỗi `N_()` thiếu `_()` **hai lần trong
> cùng một ngày**, sau khi đã tự viết nó ra thành tài liệu. Tôi gỡ bẫy hai địa
> chỉ ở cấp "năm bề mặt" rồi dựng lại đúng nó ở cấp "một bề mặt, hai công cụ".)*

```python
# test_303 — đối chiếu địa chỉ KHAI với địa chỉ NẰM TRONG đoạn mã
lac = sorted(co_trong_ma - khai)
assert lac == [], "khu khai X nhung doan ma con dung Y"
```

---

## 7c. Điều hướng: nhóm, và có trần

Mười sáu mục phẳng trên một dải cuộn ngang **không phải điều hướng, nó là một
danh sách**. Của ta còn trộn **ba nghề** vào cùng một hàng ngang cấp:

```
"làm sao cắm được"      quickstart · cli · docs
"API này nhận gì"       tools · pricing · playground
"tài khoản tôi ra sao"  keys · projects · logs · jobs · usage · webhooks · …
```

Ba nghề đó khách làm ở **ba thời điểm khác nhau** — cắm một lần, tra cứu khi
viết mã, xem tài khoản khi vận hành.

⇒ **Quy chuẩn:** thanh bên **gom nhóm**, và số mục cấp cao nhất **có trần**
(`test_303`: 12). Vượt trần thì phải hạ mục xuống làm mục con, không phải nới
trần.

⛔ **Hạ khỏi điều hướng ≠ xoá route.** Một URL đã đi vào dấu trang, tin nhắn hỗ
trợ và ảnh chụp màn hình thì việc nó `404` là thiệt hại **thật**; việc nó rời
khỏi thanh điều hướng thì không. Sáu mục hạ cấp 25/08 vẫn trả `200` và vẫn tìm
lại được từ dải mục con của trang cha — `test_303` chốt cả hai chiều.

---

## 7d. 🔴 Đo bản dịch: năm cái bẫy, tất cả cùng một hình

**25/08, một buổi, năm lần.** Ghi lại vì cả năm đều là *phép đo báo xanh trong
khi nó không đo thứ nó khai*, và cái giá là trang tiếng Anh hiện tiếng Việt cho
khách chưa đăng ký.

| # | Phạm vi được định nghĩa bằng | Vùng mù | Bỏ sót |
|---|---|---|---|
| 1 | tệp **của ai** (`THU_MUC_MAU`) | `dev_docs.html` | 14 chuỗi |
| 2 | **tên thư mục** (`dev_*`) | trang bán hàng | 67 chuỗi |
| 3 | **ai include tệp này** | `gia_api.html` | 3 chuỗi |
| 4 | **có chuyển hướng không** | mọi trang | *toàn bộ* |
| 5 | **`.po` nhìn thấy gì** | msgid trùng | 4 chuỗi |

⭐ Câu chung, và nó là quy chuẩn:

> **Phạm vi của phép đo phải được định nghĩa bằng chính thứ cần đo.**
>
> Thứ cần đo là *khách nhìn thấy chữ gì* ⇒ **render trang, đọc chữ ra**, và
> **liệt kê trang từ bảng định tuyến**, không từ một danh sách gõ tay.

⚠️ Bốn trong năm lần, vùng mù rơi đúng vào **trang thương mại**. Không phải
trùng hợp: trang thương mại được viết **sớm nhất** và đặt tên theo một hệ khác
(`gia_api`, `huong_dan`), còn phép đo bao giờ cũng viết **sau** và bám vào hệ
tên của thời điểm nó ra đời.

### Bốn luật thi hành

**① Kiểm trên thứ hệ thống THẬT SỰ dùng, không trên thứ ta vừa ghi.**

```
`.po` là thứ ta ghi        →  `.mo` qua gettext() là thứ chạy
danh sách trang gõ tay     →  bảng định tuyến là thứ phục vụ
`pattern` trong mã nguồn   →  repr(compiled.pattern) là thứ khớp
```

**② Một phép kiểm bỏ qua phải KHÓ bỏ qua hơn một phép kiểm đỏ.**
`12 passed, 1 skipped` và `8 passed, 5 skipped` trông giống nhau ở cuối màn
hình, mà cái sau là một phép đo **không đo gì**. Nên phải **khẳng định số trang
đo được**; `pytest -rs` không phải thói quen của ai.

**③ Gọi thẳng `/en/…`, đừng thương lượng qua `Accept-Language`.**
Đo thật: tiền tố đường dẫn **thắng** cả khi header nói `vi`. Gọi thẳng xoá luôn
cái chuyển hướng đã sinh ra bẫy ④.

**④ Phân loại "công khai" bằng ĐÍCH ĐẾN, không bằng mã trạng thái.**
Với `follow_redirects=True`, một trang riêng tư trả **200**. Phân loại bằng mã
sẽ gọi nó là công khai — sai theo hướng nguy hiểm.

### Hai cái bẫy kỹ thuật, cả hai đều hỏng im lặng

⛔ **`\b` viết qua heredoc thành ký tự backspace `\b` thật.** Vô hình trong
`grep`; regex im lặng không khớp gì. Soi bằng `repr(compiled.pattern)`. Cách
tránh: dùng công cụ ghi tệp cho mọi regex, đừng dùng heredoc.

⛔ **Nối msgid vào cuối `.po` khi nó đã tồn tại ở trên với `msgstr ""`** thì
`msgfmt` lấy bản **đầu** — tức bản rỗng. `.po` nhìn như đã dịch, `.mo` trả về
nguyên chuỗi gốc, trang vẫn tiếng Việt. Triệu chứng **y hệt** "chưa dịch", nên
người sửa tiếp theo sẽ nối thêm một bản trùng nữa.
⇒ **Tìm entry có sẵn rồi điền vào, đừng nối thêm.**

### Và một phân biệt sẽ mất thời gian của bạn nếu không biết trước

**`đ` là ký hiệu tiền tệ, không phải chữ chưa dịch.** Nền tảng tính tiền bằng
VND ở **cả hai** ngôn ngữ, nên `100đ` đúng trên bản `en` y hệt bản `vi`. Lọc
`\d[\d.,]*\s*đ` trước khi tìm dấu tiếng Việt — nếu không, phép đo sẽ đỏ vì
một thứ **đúng**, và người sửa sẽ đi "dịch" ký hiệu tiền.

---

## 8. Bảng kiểm khi thêm một khu API mới

| # | Chốt | Đạt khi |
|---|---|---|
| 1 | **Giá + cách cắm** công khai (danh mục theo tài khoản thì không) | mở bằng cửa sổ ẩn danh: đọc được giá và cách tích hợp, tải được SDK |
| 2 | Quick Start **ba bước** | ba câu, nằm trên màn hình đầu |
| 3 | Nhóm theo năng lực + nêu cơ chế xác thực | tiêu đề nhóm có tên header/scheme |
| 4 | Thẻ endpoint **gập mặc định** | cả bề mặt API lọt một màn hình |
| 5 | Bảng tham số **sinh từ `input_schema`** | đổi schema ⇒ trang đổi, không ai sửa template |
| 6 | Ví dụ khớp model đang chọn + có nút Copy | chép nguyên khối là chạy được |
| 7 | Có phản hồi mẫu và **bảng lỗi** | khách viết được bộ giải mã trước lần gọi đầu |
| 8 | Giá đứng cạnh endpoint | một cú bấm tới `/gia-api` |
| 9 | Trang cắm là **một ô chọn + N khu** khi có >2 bề mặt | chọn một bề mặt ⇒ chỉ còn MỘT địa chỉ và MỘT tên model trên màn hình |
| 10 | Không có JS vẫn đọc được đủ | tắt JS ⇒ mọi khu hiện, mỗi khu có tiêu đề |
| 11 | Điều hướng **gom nhóm**, số mục cấp cao nhất có trần | thanh bên có ≥3 nhóm, ≤12 mục; có test chốt |
| 12 | Công cụ tải được **có mặt trong khu đã đăng nhập** | người vừa tạo khoá xong thấy ngay đường tải |
| 13 | Phép đo bản dịch **render trang**, liệt kê từ bảng định tuyến | đổi một route ⇒ phép đo tự thấy, không chờ ai nhớ |
| 14 | Số trang đo được **được khẳng định** | một trang rơi khỏi phép đo là gate đỏ, không phải một dòng `skipped` |
| 15 | Chuỗi mới kiểm bằng `gettext()`, không bằng `.po` | msgid trùng không thể lọt |

⛔ Mục 5 là mục dễ bỏ nhất và tốn nhất về sau. Một trang tài liệu gõ tay **luôn**
trôi khỏi API — câu hỏi chỉ là bao lâu.

---

## 9. Khoảng cách của ta hôm nay

⚠️ **Bảng dưới là bản ĐO LẠI.** Bản đầu tôi chấm `/developers/tools/{ten}` bằng
cách nhìn kích thước tệp template và suy ra, rồi cho chốt 5 điểm 🔴 và chốt 7
điểm 🟡. Khi render trang thật thì **cả hai đã xong từ trước** (EXT-06) — và
xong tốt. Ghi lại cái sai này vì nó đúng loại sai mà tài liệu này đang cố chặn:
**suy ra thay vì đo.**

| Chốt | Trạng thái thật (đo 25/08 trên trang render) |
|---|---|
| 1 công khai | ✅ theo chốt chủ sản phẩm: `/developers/*` sau đăng nhập, giá + hướng dẫn + tải công khai |
| 2 Quick Start ba bước | ✅ có trên trang tool (`quotes → jobs → poll`). 🟡 chưa có ở cửa vào khu API |
| 3 nhóm + cơ chế xác thực ở tiêu đề | 🟡 có nhóm `image`/`text` và bộ lọc; chưa nêu header xác thực |
| 4 gập mặc định | 🔴 trang chi tiết là **một cuộn dài**, không có mục lục |
| 5 bảng sinh từ `input_schema` | ✅ **đã có từ trước** — Tên · Kiểu · Bắt buộc · Giới hạn · Mặc định · Mô tả · ví dụ |
| 6 ví dụ + nút Copy | ✅ curl sinh sẵn, có nút Copy |
| 7 phản hồi mẫu + bảng lỗi | ✅ có cả hai: `output_schema` + bảng `Mã · HTTP · Thử lại · Idempotency-Key · Nên làm gì` |
| 8 giá cạnh endpoint | 🟡 nói rõ giá đến từ `POST /quotes`; chưa có liên kết tới `/gia-api` |

### 🔴 Việc còn lại ở tầng HỢP ĐỒNG, không phải tầng giao diện

Chốt 5 mới xong **một nửa**: bảng là hàm của *tool*, chưa phải hàm của
*(tool, model/mode)*.

Với `image.ltt`, `mode` có ba giá trị `t2i · edit · subject`, và `image_key`
**chỉ dùng cho hai trong ba** — chính `description` trong schema đã nói:
*"Required for edit and subject; ignored for t2i."*

⇒ Thông tin **có đủ**, nhưng nó nằm trong một câu văn xuôi tiếng Anh giữa bảng.
Muốn trang tự lọc tham số theo mode thì `input_schema` phải **khai** điều kiện
đó (JSON Schema `if/then`, hoặc một khoá trong `api_contract`), chứ không phải
để giao diện đoán bằng cách đọc chữ.

⚠️ Đó là **đổi hợp đồng công khai**: chạm `contract_hash`, chạm ảnh chụp vàng,
chạm `APP_API_COVERAGE_FINAL.md`. Không làm vội, và không làm bằng cách để
template phân tích câu tiếng Anh — một template đọc văn xuôi để quyết định hiển
thị là một template sẽ sai vào ngày ai đó sửa câu chữ.

