# Audit giao diện API trên web — chấm điểm từng hạng mục

**2026-08-25.** Theo yêu cầu chủ sản phẩm: *audit sâu giao diện API trên web,
chấm điểm từng hạng mục, đưa từng hạng mục lên MVP 10/10 thực sự.*

> Mọi con số dưới đây là **số đo**, lấy trên HTML render thật của một máy chủ
> sạch (SQLite tạm, tài khoản gieo sẵn 50.000 credit, `LTT_PUBLIC_API=1`, ba
> tool mở), bằng `requests` và bằng trình duyệt thật. Không đọc template rồi
> suy ra.

Tài liệu này **không thay thế** `KE_HOACH_MVP_CONG_LAP_TRINH_VIEN.md` — bản đó
soi *đường tới nội dung* (tài liệu, công cụ, SDK, tải về) và đã thi hành xong
đợt P0. Bản này soi **chính các trang**: chúng nói gì, nói với ai, và nói bằng
ngôn ngữ nào.

---

## 0. Thước đo

Một hạng mục đạt **10/10** khi cả bốn vế đều đúng:

| Vế | Nghĩa |
|---|---|
| **Đúng** | không nói sai, không hứa thứ không có |
| **Đủ** | người lạ dùng được mà không hỏi ai |
| **Đúng người** | thứ giúp quyết định mua thì công khai; thứ gắn tài khoản thì sau đăng nhập |
| **Không trôi được** | có phép kiểm chốt, đổi mã mà quên sửa trang thì gate đỏ |

Vế thứ tư là vế hay bị bỏ. Ba lỗi tuần này (tiền kẹt trong hold, log 500 rỗng,
ngữ cảnh gửi model bị bóp méo) đều **có mã và có test**, và đều chỉ lộ ra ở lượt
gọi thật đầu tiên.

---

## 1. Nền: những gì đã ĐÚNG

Ghi trước, vì một bản audit chỉ liệt kê lỗi là một bản audit không đọc được.

| Đo | Kết quả |
|---|---|
| 16 trang trong cổng + 2 trang công khai | **18/18 trả `200`** khi đã đăng nhập |
| Lỗi console trình duyệt trên cả 18 trang | **0** |
| Request hỏng (≥400) khi tải trang | **0** |
| Biểu mẫu POST thiếu CSRF | **0/21** |
| `<h1>` trên mỗi trang | đúng **1**, trừ `/gia-api` có **2** |
| `<title>` riêng cho từng trang | có, đủ 18 |
| Luồng thật: tạo project → tạo khoá → gọi `/api/v1/tools` | **đi trọn**, khoá hiện đúng một lần, gọi trả `200` |

Nói cách khác: **phần cơ khí lành.** Vấn đề nằm ở nội dung và ở ranh giới.

---

## 2. Chấm điểm 13 hạng mục

| # | Hạng mục | Điểm | Chặn ở đâu |
|---|---|---|---|
| A | Bản tiếng Anh của cổng | **1/10** | 85% đoạn văn vẫn là tiếng Việt |
| B | Ranh giới công khai / riêng tư | **4/10** | 16/18 trang sau đăng nhập |
| C | Luồng lần đầu (project → khoá → gọi) | **7/10** | đi được, nhưng không ai dẫn đường |
| D | Khoá API | **8/10** | hiện một lần đúng; lỗi cấu hình lộ ra ngoài |
| E | Quan sát được (log · job · usage) | **7/10** | có dữ liệu, thiếu lối ra khi rỗng |
| F | Webhook | **7/10** | đủ nút, thiếu ví dụ kiểm chữ ký |
| G | Playground | **6/10** | không nối với trang khoá |
| H | Giá & mô phỏng | **6/10** | hai trang giá, một công khai một không |
| I | Tài liệu & SDK | **8/10** | *(đợt P0 của phiên Public API đã sửa phần nặng)* |
| J | Cắm CLI | **8/10** | *(đợt P0 đã sửa)* |
| K | Dữ liệu & quyền riêng tư | **8/10** | trang dài nhất, không mục lục |
| L | Cài đặt & bảo mật | **6/10** | mỏng nhất cổng, 20 dòng |
| M | Chất lượng nền (a11y · số · trạng thái rỗng) | **4/10** | 0/69 `<th scope=>`, 12 khối mã không nút chép |

**Trung bình 6,2/10.**

---

### A. Bản tiếng Anh của cổng — **1/10**

🔴 **Bản dịch tiếng Anh của khu API không tồn tại. Chỉ có thẻ `<html lang="en">`.**

Đo trên `/en/developers/*`, đã bỏ `<pre>` và `<code>` (curl và JSON không có dấu
tiếng Việt nên chúng làm mọi trang trông như đã dịch một nửa):

```
TỔNG bản EN: 367/434 = 85% đoạn văn VẪN LÀ TIẾNG VIỆT

thuần Việt 100% dù lang="en" : projects · keys · jobs · notifications · settings
gần như thế                  : privacy 96% · webhooks 95% · logs 94%
pha trộn                     : overview 88% · docs 88% · usage 84% · playground 82%
                               cli 68% · quickstart 66% · tools 62% · pricing 56%
```

Trên cây mã: **278/422 msgid trong khu API (66%) không có bản dịch EN.**

Thứ khách thấy là một bảng như thế này — ba cột đầu tiếng Việt, hai cột sau
tiếng Anh, trong cùng một hàng tiêu đề:

```
Tên | Identifier | Khóa | Tạo lúc | [Archive]
```

Hoặc trang tổng quan:

```
Status
  API công khai: đang phục vụ
  Số dư: 50000 credit
  Used today: 0 credit — chưa đặt trần ngày
Start
  Chưa có khóa nào. Ba bước để gọi được lần đầu:
```

⚠️ **Đây không phải chuyện thẩm mỹ.** Khách của Public API là lập trình viên, và
phần lớn sẽ chọn `en`. Một trang nửa nọ nửa kia không đọc là *"chưa dịch"*, nó
đọc là **làm dở dang** — và hạ tầng làm dở dang thì không ai giao thẻ tín dụng
cho.

⚠️ Việc đổi ngôn ngữ mặc định `en` → `vi` (phiên Public API, cùng ngày) làm **ít
người gặp cảnh này hơn**, nhưng không sửa gì: ai chọn `en` vẫn thấy y nguyên. Một
phép che, không phải một phép sửa. *(Ghi ra vì lớp lỗi này đã lặp trong cùng
ngày: mặc định `vi` cũng che luôn việc cột "Cấu hình" ở trang VPS hiện thành
"Settings".)*

**Chiều ngược lại thì lành.** Chỉ 15 msgid được viết bằng tiếng Anh trong mã
nguồn, và gần hết là từ mượn đã quen trong tiếng Việt kỹ thuật (`Project`,
`Job`, `Webhook`, `token`, `credit`, `request`). Không cần đụng.

**Lên 10/10 khi:** 278 chuỗi có bản dịch EN, **và** có bánh cóc trong gate không
cho khu API thêm chuỗi mới mà thiếu bản dịch — nếu không, nợ này sẽ mọc lại đúng
như cách nó đã mọc.

---

### B. Ranh giới công khai / riêng tư — **4/10**

```
/developers/pricing    -> 303      /gia-api    -> 200
/developers/tools      -> 303      /huong-dan  -> 200
/developers/quickstart -> 303
/developers/docs       -> 303
```

16 trong 18 trang vẫn sau `require_account`. Phiên Public API đã mở `/huong-dan`
và `/huong-dan/cong-cu` trong đợt P0, nhưng **danh mục công cụ, bắt đầu nhanh và
giá trong cổng vẫn đóng**.

Ranh giới đúng đã được viết ra ở `KE_HOACH_MVP_CONG_LAP_TRINH_VIEN.md` §2.3 — chỉ
là chưa thi hành hết:

```
công khai: giá · công cụ có gì · cắm thế nào · gọi thử · điều khoản
riêng tư : khoá · dự án · log · usage · webhook · ngân sách
```

Đây **cùng một lỗi** vừa sửa ở trang VPS hôm nay: thẻ app trong catalog hiện cho
khách ẩn danh, còn trang thì đòi đăng nhập ⇒ ngõ cụt ở đúng bước đầu của phễu.
Dự án đã học bài này **ba lần** (trang giá, hướng dẫn cắm, trang VPS) và mỗi lần
chỉ sửa đúng trang đang đau.

**Lên 10/10 khi:** `tools` và `quickstart` mở công khai (nội dung nguyên vẹn, chỉ
thay khối "khoá của bạn" bằng lời mời đăng ký), **và** có phép kiểm chốt danh
sách trang công khai — thêm một trang riêng tư vào danh sách đó phải là gate đỏ.

---

### C. Luồng lần đầu — **7/10**

Đi trọn được, đã đo:

```
1. tạo project              -> 200, project hiện trong bảng
2. tạo khoá                 -> 200, `ltt_sk_…` hiện ĐÚNG MỘT LẦN
3. GET /api/v1/tools        -> 200, danh mục trả về
4. nhật ký request          -> có ghi lượt gọi đó
```

Trừ điểm vì **không ai dẫn đường**: trang tổng quan có *"Ba bước để gọi được lần
đầu"* nhưng ba bước đó là ba liên kết rời, không có trạng thái đã-làm-hay-chưa,
và sau khi tạo khoá xong không có gì đưa khách sang lượt gọi đầu tiên.

**Lên 10/10 khi:** ba bước thành một danh sách **có trạng thái thật** (đọc từ
CSDL: đã có project? đã có khoá? đã có lượt gọi nào?), và bước cuối là một lệnh
`curl` đã điền sẵn tên tool thật, có nút chép.

---

### D. Khoá API — **8/10**

Làm đúng thứ khó: bí mật hiện **một lần**, có `mode` (Test/Live), giới hạn theo
`scopes`, `allowed_tools`, `allowed_ips`, `expires_in_days`. Thu hồi và xoay khoá
đều có.

🟡 **Một lỗi thật.** Khi thiếu `LTT_API_KEY_PEPPER`, trang hiện thẳng cho khách:

```
LTT_API_KEY_PEPPER is missing or too short (need at least 32 character…
```

Khách học được tên một biến môi trường của ta, bằng tiếng Anh, giữa một trang
tiếng Việt, và **không làm gì được** — vì đó không phải việc của họ.

**Lên 10/10 khi:** lỗi cấu hình phía ta hiện một câu cho khách (*"hệ thống đang
trục trặc, chúng tôi đã được báo"*) còn chi tiết đi vào log; và trang khoá có nút
chép ngay tại chỗ bí mật hiện ra.

---

### E · F · G · H · K · L — bảng gọn

| Hạng mục | Điểm | Đo được | Lên 10/10 khi |
|---|---|---|---|
| **E. Quan sát được** | 7 | log/job/usage đều có dữ liệu thật; trạng thái rỗng **không có nút hành động** ở 10/16 trang | mỗi trạng thái rỗng có đúng một lối ra |
| **F. Webhook** | 7 | đủ gửi-thử · xoay khoá · tắt · gửi lại; 1 khối mã, **0 nút chép** | có ví dụ kiểm chữ ký chép được, ít nhất hai ngôn ngữ |
| **G. Playground** | 6 | chạy được nhưng không nối với trang Khoá; khách chưa có khoá vào đây sẽ mắc kẹt | tự dùng khoá Test của phiên đăng nhập, và in ra lệnh `curl` tương đương |
| **H. Giá & mô phỏng** | 6 | **hai** trang giá: `/gia-api` (công khai) và `/developers/pricing` (đóng) | một nguồn, hai vỏ — như `_cam_than.html` đã làm đúng cho hướng dẫn |
| **K. Dữ liệu & riêng tư** | 8 | trang dài nhất cổng (127 đoạn), không mục lục | có mục lục nhảy, và bảng vòng đời dữ liệu sinh **từ `governance.py`** chứ không gõ tay |
| **L. Cài đặt & bảo mật** | 6 | **20 dòng** — mỏng nhất cổng | gom về đây: xoay khoá, IP cho phép, ngân sách/trần ngày, thông báo — hiện đang rải rác |

---

### M. Chất lượng nền — **4/10**

| Đo | Kết quả |
|---|---|
| `<th scope=>` trên 8 trang có bảng | **0/69** — không cột nào khai phạm vi |
| Khối `<pre>` không có nút chép | `quickstart` **10/10**, `webhooks` 1/1, `playground` 1/1 |
| Số credit có dấu phân cách nghìn | **0** — hiện `50000`, trong khi trang VPS hiện `149.000` |
| Trạng thái rỗng có nút hành động | **6/16** |

Bốn thứ này nhỏ từng cái, nhưng chúng là thứ khách gặp **trên mọi trang**, và
cộng lại chúng nói một câu: *chưa ai đi hết cổng này bằng mắt của người lạ.*

⚠️ Riêng phần khối mã: phiên Public API đang thêm `sao_chep.js` và kiểu cho `pre`
ở `_kieu_chung.html`. Việc của tôi là **dùng nó**, không dựng bản thứ hai.

---

## 3. Kế hoạch — thứ tự, và vì sao thứ tự này

| Đợt | Việc | Vì sao ở đây |
|---|---|---|
| **Q1** | **A** — dịch 278 chuỗi + bánh cóc trong gate | ảnh hưởng **cả 18 trang**; mọi việc khác đều nhân đôi công nếu làm trước |
| **Q2** | **B** — mở `tools` + `quickstart` công khai, có test chốt danh sách | bỏ chặn khách; rẻ, và là lỗi đã lặp ba lần |
| **Q3** | **M** — `scope=`, nút chép, dấu phân cách nghìn, trạng thái rỗng | chạm mọi trang, làm sau A để khỏi sờ hai lần |
| **Q4** | **C · D · G** — luồng lần đầu có trạng thái thật, giấu lỗi cấu hình, nối Playground với khoá | phần *cảm giác dùng được*; cần A xong mới viết chuỗi một lần |
| **Q5** | **H · L · K** — gộp hai trang giá, gom trang cài đặt, mục lục trang riêng tư | cấu trúc thông tin; cần bàn với chủ sản phẩm về nội dung |

**A đứng đầu không phải vì dễ.** Nó là hạng mục duy nhất mà mọi hạng mục khác đều
đi qua: sửa trạng thái rỗng ở 16 trang rồi mới dịch nghĩa là viết chuỗi hai lần,
và dịch rồi mới sửa cũng thế. Nó cũng **rẻ nhất tính theo điểm thu được**: 1/10 →
10/10 cho một việc gần như cơ khí.

---

## 4. Chia việc với phiên Public API

| Của tôi | Của phiên Public API |
|---|---|
| `server/routes/developer.py` | `server/api/*`, `platform_core/public_api/*` |
| `server/templates/dev_*.html` **trừ** `dev_cli.html`, `dev_docs.html` | `base*.html`, `_header.html`, `_kieu_chung.html`, `sao_chep.js`, `templating.py` |
| `locale/*/LC_MESSAGES/messages.po` | `gia_api.html`, `huong_dan*.html`, `_cam_than.html`, `tools/cam_cli.py` |

Hạng mục **I** và **J** đã do phiên kia đưa lên 8/10 trong đợt P0 và vẫn là của
họ. Hạng mục **H** chạm `gia_api.html` nên phải bàn trước khi làm.

---

## 5. Cái **không** làm

| Không làm | Vì sao |
|---|---|
| Thêm `.card`/`.table` vào `ltt.css` | phiên kia đang tách `_kieu_chung.html`; thêm nữa là tạo bản sao thứ hai của cùng một hệ thống kiểu |
| Thiết kế lại bố cục / màu | hệ thống thiết kế không phải vấn đề — **cấu trúc thông tin và ngôn ngữ** mới là |
| Dịch sang ngôn ngữ thứ ba | chưa có một khách nào ở ngôn ngữ thứ hai |
| Dịch máy hàng loạt rồi để đó | 278 chuỗi là giao diện của một sản phẩm **bán tiền**; dịch sai một dòng về cách tính tiền thì tệ hơn không dịch |

---

## 6. Đã thi hành — 25/08

Mọi con số dưới đây đo lại trên **cùng một cách đo** đã dùng ở mục 2, sau khi
sửa. Không có con số nào là ước lượng.

### Hạng mục A — **1/10 → 10/10**

| Đo (phần `<main>`, 14 trang, đã bỏ `<pre>`/`<code>`) | Trước | Sau |
|---|---|---|
| Đoạn văn còn tiếng Việt trên bản `en` | 367/434 = **85%** | 0/286 = **0%** |
| Trang thuần tiếng Việt dù `lang="en"` | 5 | 0 |

Ba đợt, **358 chuỗi**:

1. **214 chuỗi** `msgstr` rỗng trong 16 tệp khu API.
2. **74 mục `fuzzy`** — và đây là phần đáng nói nhất.
3. **70 chuỗi** còn lại: thông báo lỗi, cảnh báo gửi khách, mô tả vòng đời dữ
   liệu (`governance.py`, `webhooks.py`).

🔴 **`fuzzy` không phải "dịch chưa xong". Nó là bản dịch SAI đang nằm sẵn.**
`msgmerge` đoán bằng cách ghép msgid mới với một msgstr cũ tương tự:

```
"Ngân sách của bạn"            ->  "Your scripts"
"Chưa đăng ký điểm nhận nào."  ->  "Not signed in"
"Chờ kết quả bằng"             ->  "✅ Result"
```

`msgfmt` bỏ qua mục fuzzy, nên **chưa ai từng thấy chúng** — thứ duy nhất giữ
chúng khỏi production là một mặc định của công cụ. Một lần ai đó thêm
`--use-fuzzy` "cho đầy đủ" là "Your scripts" lên trang ngân sách, và nó lên
dưới dạng một câu tiếng Anh trôi chảy chứ không phải một ô trống dễ nhận ra.

⚠️ Toàn catalog còn **89 mục fuzzy ngoài khu API**. Tôi **không** đụng tới:
gỡ cờ cho một bản dịch chưa ai đọc lại chính là làm nó hiện ra. Đây là một
**rủi ro có tên**, không phải một việc đã xong.

🟡 **Một bài học về công cụ đo.** Phép đo đầu của tôi cho ra 56% và **sai**, vì
hai lẽ: nó lấy bản mặc định (vừa đổi sang `vi`) chứ không phải bản `en`, và nó
đếm cả `<pre>` — curl với JSON không có dấu tiếng Việt nên chúng làm mọi trang
trông như đã dịch một nửa. Con số thật là 85%, tức **nặng hơn**. Bộ trích cũng
sót 7 chuỗi vì `governance.py` nối chuỗi ngầm qua nhiều dòng và một regex bắt
literal sẽ cắt cụt msgid — triệu chứng là *"đã dịch xong mà trang vẫn tiếng
Việt"*, và không ai nghĩ tới bộ trích. `tests/test_299` vì thế đọc `.py` bằng
**AST**, không bằng regex.

**Chốt bằng `tests/test_299_khu_api_da_dich.py`** (8 phép kiểm): mọi chuỗi khu
API phải có bản dịch · không còn mục fuzzy nào · placeholder không được rơi
(`%(n)s` mất = trang nổ `TypeError`, và **chỉ nổ ở tiếng Anh** nên bộ test chạy
bằng tiếng Việt xanh suốt) · một phép kiểm tiền đề bắt chính bộ trích hỏng.
Đã thử ngược: thêm một chuỗi chưa dịch → đỏ. *(Nó đã bắt đúng bốn chuỗi tôi tự
thêm trong cùng phiên này.)*

### Hạng mục B — **4/10 → 9/10**

`/developers/quickstart` và `/developers/tools` nay mở cho khách chưa đăng nhập:

```
/developers/quickstart -> 200      /developers/keys  -> 303
/developers/tools      -> 200      /developers/logs  -> 303
```

Ba thứ đi kèm, vì mở một trang ra không phải là xong:

- **Thanh điều hướng rút gọn cho khách ẩn danh.** Hiện đủ 16 mục nghĩa là 14
  liên kết bật về `/login` — một thanh điều hướng mà phần lớn là ngõ cụt thì tệ
  hơn một thanh ngắn.
- **Lời mời đăng ký nằm trong thân trang**, ngay dưới tiêu đề, và **biến mất khi
  đã đăng nhập**. Đặt ở `developers_base.html` một chỗ, nên mở thêm trang thứ ba
  thì nó có sẵn.
- **Cổng cờ `LTT_PUBLIC_API` vẫn đứng trước.** Công khai nghĩa là *"không đòi
  đăng nhập"*, không phải *"bỏ qua cờ"*.

**Chốt bằng `tests/test_300_khu_api_ranh_gioi.py`** (20 phép kiểm) — và nó chốt
**cả hai chiều**. Chiều thứ hai mới là chiều nguy hiểm: thêm một trang vào
`TRANG_CONG_KHAI` là một dòng sửa dễ, và nếu trang đó đọc dữ liệu tài khoản thì
đó là rò dữ liệu của khách, **không có triệu chứng nào** cho tới khi có người
báo. Nên có riêng một phép kiểm rằng hai trang mở **không đọc gì của tài khoản**.

Còn 1 điểm: `pricing` vẫn đóng trong khi `/gia-api` mở — đó là hạng mục **H**
(hai trang giá), cần gộp chứ không phải mở thêm.

⚠️ **Một phép kiểm của tôi đã xanh vì lý do sai.** Bản đầu chỉ hỏi
`"/register" in t` và xanh — vì **header toàn cục luôn có nút "Đăng ký"**, tức
nó xanh trong khi trang không mời gì cả. Đã siết: phải tìm trong `<main>`, và
phải **biến mất** khi đã đăng nhập.

### Hạng mục M — **4/10 → 7/10**

| Đo | Trước | Sau |
|---|---|---|
| `<th scope=>` | 0/69 | **+115** trên 13 tệp |
| Khối `<pre>` có nút chép ở `quickstart` | 0/10 | **10/10** |
| Lỗi console trên trang đã sửa | 0 | 0 |

Nút chép dùng **đúng** `sao_chep.js` và `.khoi-ma`/`.nut-chep` mà phiên Public
API vừa dựng cho trang công khai — nạp qua `{% block scripts %}` trong
`developers_base.html`, không sửa `base.html`, không chép luật CSS nào sang chỗ
khác. Một hệ thống kiểu, không phải hai.

Còn 3 điểm: **dấu phân cách nghìn** (`50000` chứ không phải `50.000` — cần một
filter dùng chung trong `templating.py`, tệp của phiên Public API) và **trạng
thái rỗng có lối ra** (6/16 trang).

### Điểm sau đợt này

| Hạng mục | Trước | Sau |
|---|---|---|
| A — bản tiếng Anh | 1 | **10** |
| B — ranh giới công khai/riêng tư | 4 | **9** |
| M — chất lượng nền | 4 | **7** |
| *(C · D · E · F · G · H · K · L — chưa động)* | | |

**Trung bình 6,2 → 7,5.**

### Còn lại, theo thứ tự

| Đợt | Hạng mục | Vì sao chưa làm |
|---|---|---|
| Q3 (nốt) | M — dấu phân cách nghìn · trạng thái rỗng | filter số nằm ở `templating.py` (phiên Public API giữ) |
| Q4 | C · D · G | luồng lần đầu có trạng thái thật · giấu lỗi cấu hình khỏi khách · nối Playground với trang Khoá |
| Q5 | H · L · K | gộp hai trang giá · gom trang cài đặt · mục lục trang riêng tư — **cần chủ sản phẩm** vì chúng đổi cấu trúc thông tin, không chỉ đổi mã |

---

## 7. Đợt Q4 — hạng mục C · D · G

Ba hạng mục khác nhau nhưng cùng một câu hỏi: **một người lạ có tự đi hết được
không, hay đến một chỗ thì mắc kẹt mà không biết bước tiếp theo là gì.**

### C. Luồng lần đầu — **7/10 → 10/10**

Trước: ba liên kết rời, không biết bước nào đã làm, và sau khi tạo khoá xong
không có gì đưa khách sang lượt gọi đầu. Một danh sách ba bước mà không biết
mình đang ở đâu thì không phải hướng dẫn, nó là **một cái menu**.

Nay đọc trạng thái **từ CSDL thật**, và bước cuối là một lệnh chạy được:

```
Chưa có gì  →  1. Tạo một project
               2. Tạo khóa trong project đó
               3. Gọi thử — (cần khóa ở bước trên trước)

Có khoá     →  ✓ Đã có project (1)
               ✓ Đã có khóa đang hoạt động (1)
               3. Gọi thử — lệnh này không tốn credit:
                  curl -s https://…/api/v1/tools \
                    -H "Authorization: Bearer $LTT_API_KEY"

Đã gọi được →  "Bạn đã gọi được. Những nơi hay dùng: …"
```

🔑 **`da_goi_api` KHÔNG suy ra từ số job.** Phần lớn lượt gọi đầu tiên là
`GET /tools` hoặc `/credits/balance`, và chúng **không tạo job nào**. Suy từ job
sẽ nói *"chưa gọi bao giờ"* với người vừa gọi xong — và đó là kiểu sai làm
người ta ngờ cả phần còn lại của trang. Đọc từ `ApiRequestLog`.

⚠️ **Lệnh mẫu lấy gốc URL từ `LTT_BASE_URL`, không viết cứng.** Viết cứng
`app.lttstudios.com` thì lệnh **sai trên mọi cài đặt khác**, và nó sai im lặng:
khách chép, chạy, nhận lỗi mạng, và không nghĩ rằng chính trang hướng dẫn đưa
nhầm địa chỉ. Có test riêng chốt điều này.

`GET /tools` được chọn làm lệnh mẫu vì nó là lượt gọi **rẻ nhất chứng minh được
khoá sống**: không báo giá, không job, không tốn credit — trả `200` là xác thực,
phạm vi và hạn mức đều đúng.

### D. Khoá API — **8/10 → 10/10**

Trước, khi thiếu `LTT_API_KEY_PEPPER`, trang hiện thẳng cho khách:

```
LTT_API_KEY_PEPPER is missing or too short (need at least 32 characters).
```

Khách học được tên một biến môi trường của ta, và **vẫn không làm gì được** —
đó không phải việc của họ.

🔑 **Cách phân biệt KHÔNG phải khớp chuỗi.** `DeveloperKeyError` gom cả hai loại
lỗi: thứ khách sửa được (*"Không tìm thấy project."*) và thứ **ta** hỏng (thiếu
pepper). Khớp chuỗi để tách chúng sẽ trượt ngay lần đổi câu chữ đầu tiên. Thay
vào đó tách bằng **lời gọi nào hỏng**: `current_pepper()` là hàm **chỉ** kiểm
cấu hình máy chủ, nên gọi riêng nó trước là đủ.

Khách nhận một câu nói rõ đây là lỗi phía chúng tôi; tên biến đi vào log.

⚠️ Và có test chốt **chiều ngược lại**: giấu lỗi cấu hình không được kéo theo
việc giấu lỗi khách sửa được. Một thông báo chung chung cho mọi thứ là cách
biến một lỗi sửa được thành một lỗi không sửa được.

### G. Playground — **6/10 → 9/10**

Trang này làm **đúng** thứ khó và điều đó phải được giữ: nó không tự điền khoá,
vì máy chủ chỉ giữ dấu vân tay một chiều, và một cổng nội bộ mượn phiên đăng
nhập để gọi thay sẽ là **đường thứ hai** tới đường tính tiền — nền tảng cố ý chỉ
có một, vì một lỗi chính sách ở đường thứ hai là mất tiền thật.
Có `test_playground_van_KHONG_tu_dien_khoa` chốt, vì đây đúng là thứ dễ bị
"cải thiện" nhầm.

Lỗ nằm chỗ khác: một khách **chưa có khoá nào** vào đây thấy một ô nhập họ
không thể điền, không lối ra. Và không ai nói cho họ biết khoá **Test** không
chạm vào sổ credit — đúng thứ một người vào Playground muốn nghe nhất.

Nay: chưa có khoá → nói thẳng + đường tới chỗ tạo khoá Test. Có khoá → liệt kê
`key_id` (nửa công khai, không phải bí mật) kèm nhãn Test/Live. Câu cảnh báo
đổi từ *"Lời gọi ở đây tiêu credit thật"* thành *"Khóa **live** ở đây tiêu
credit thật… muốn thử không mất tiền thì dùng khóa Test"*.

Còn 1 điểm: chưa in ra lệnh `curl` tương đương với lời gọi vừa dựng.

### Bánh cóc "nuốt lỗi lặng lẽ" — một lỗi của tôi, phiên Public API bắt được

`_tai_khoan_tuy_chon` của tôi bọc `user_hien_tai` trong `except Exception:
return None`. Ý định đúng (trang công khai phải hiện được dù phiên hỏng) nhưng
`except Exception` trần **nuốt cả những lỗi không liên quan**: CSDL sập, cấu
hình sai, một bug trong chính `user_hien_tai`. Ba thứ đó sẽ im lặng biến thành
*"khách ẩn danh"*, và triệu chứng là trang vẫn trả `200` với nội dung sai.

Đọc lại thì hoá ra **không cần lớp try nào cả**: `user_hien_tai`
(`server/deps.py:44`) đã trả `None` cho đúng ba trường hợp đó và đã có try
riêng bên trong. Gỡ hẳn. Bánh cóc về mốc 90.

### Điểm sau Q4

| Hạng mục | Đầu | Sau Q1–Q3 | Sau Q4 |
|---|---|---|---|
| A — bản tiếng Anh | 1 | 10 | 10 |
| B — ranh giới công khai/riêng tư | 4 | 9 | 9 |
| C — luồng lần đầu | 7 | 7 | **10** |
| D — khoá API | 8 | 8 | **10** |
| G — Playground | 6 | 6 | **9** |
| M — chất lượng nền | 4 | 7 | **8** |

**Trung bình 6,2 → 8,2.**

Còn lại là **Q5** (H · L · K): gộp hai trang giá, gom trang cài đặt, mục lục
trang riêng tư. Cả ba đổi **cấu trúc thông tin** chứ không chỉ đổi mã, và H
chạm `gia_api.html` — nên chúng cần chủ sản phẩm chốt, không phải một phiên
Claude tự quyết.

---

## 8. ĐÍNH CHÍNH — hạng mục B chấm sai trên một tiền đề bị bác

**Chủ sản phẩm chốt 25/08, nguyên văn:**

> *"/developers/tools đứng sau đăng nhập là đúng rồi. hệ thống của ta API cần
> phải đăng nhập mới được kích hoạt"*

và sau đó:

> *"developers đều sau đăng nhập hết"*

⇒ **Điểm 4/10 cho hạng mục B ở mục 2 là SAI, và điểm 9/10 ở mục 6 cũng sai.**
Cả hai chấm trên giả định *"16/18 trang sau đăng nhập là một khuyết điểm"*. Giả
định đó bị bác, và người bác nó đúng: hệ thống API của LTT **phải đăng nhập mới
kích hoạt được**, nên danh mục công cụ là trang **của một tài khoản** — nó trả
lời *"tôi đang dùng cái gì"*, không phải *"có đáng mua không"*.

Thứ trả lời *"có đáng mua không"* đã công khai từ trước: `/gia-api`,
`/huong-dan`, `/huong-dan/cong-cu`, `/status/api`, `/tai/…`,
`/api/v1/openapi.json`.

**Hạng mục B: không phải 4/10, mà là 9/10 ngay từ đầu** — ranh giới đã đúng,
chỉ thiếu một phép kiểm chốt nó.

### Đã hoàn nguyên

`TRANG_CONG_KHAI` nay là **tập rỗng**, mọi `/developers/*` trả `303`. Bộ máy
(`TRANG_CONG_KHAI`, `tai_khoan_tuy_chon`, lời mời đăng ký, `test_300` chốt cả
hai chiều) **giữ nguyên** — nó đúng và dùng ngay được nếu có ngày chốt mở một
trang nào; xoá đi rồi dựng lại là làm hai lần.

Thêm `test_danh_sach_cong_khai_dung_bang_chot_cua_chu_san_pham`, vì
`parametrize` trên một danh sách rỗng **không chạy phép kiểm nào** — không có
nó, hai phép kiểm chiều-mở sẽ im lặng biến mất và không ai biết.

### Bài học, và nó không nhỏ

Tôi đo được một sự thật (*16/18 trang sau đăng nhập*) rồi **tự gắn cho nó một
phán đoán** (*đó là khuyết điểm*), và viết phán đoán đó vào bảng điểm như thể
nó cũng là số đo. Ba đoạn văn về *"dự án đã học bài này ba lần"* nghe rất
thuyết phục — và chúng thuyết phục vì chúng đúng ở ba trường hợp kia, không
phải vì chúng đúng ở đây.

Cái phân biệt hai loại: **trang giá và hướng dẫn cắm trả lời "có đáng mua
không"; danh mục công cụ trả lời "tôi đang dùng cái gì".** Tôi đã gộp cả ba vào
một quy luật, và một quy luật gộp quá tay thì áp đúng ba lần rồi sai ở lần thứ
tư mà vẫn nghe như đang đúng.

⚠️ Điểm trung bình ở mục 6 và mục 7 (**7,5** và **8,2**) tính cả điểm B sai.
Chấm lại với B = 9 từ đầu: **6,6 → 8,4**. Con số nhỏ hơn cái sai.

### Điểm cuối, đã sửa

| Hạng mục | Đầu | Cuối |
|---|---|---|
| A — bản tiếng Anh | 1 | **10** |
| B — ranh giới công khai/riêng tư | **9** *(không phải 4)* | **10** |
| C — luồng lần đầu | 7 | **10** |
| D — khoá API | 8 | **10** |
| G — Playground | 6 | **9** |
| M — chất lượng nền | 4 | **8** |
| E · F · H · I · J · K · L | *(chưa động)* | |

**Trung bình 6,6 → 8,4.**

Còn lại **Q5 (H · L · K)** — và hạng mục **H** (hai trang giá) nay phải đọc lại
dưới ánh sáng của chốt trên: `/gia-api` công khai và `dev_pricing.html` sau
đăng nhập **có thể là đúng chứ không phải trùng lặp**, vì chúng trả lời hai câu
hỏi khác nhau. Đừng gộp trước khi trả lời được câu đó.
