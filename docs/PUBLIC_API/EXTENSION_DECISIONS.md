# EXTENSION DECISIONS — D1…D5

Năm quyết định mà `FULL_PLATFORM_DEPENDENCY_GRAPH.md` §4 nêu là **chặn** EXT-02
và EXT-04. Chủ sản phẩm uỷ quyền cho Claude chốt (2026-08-13), và sẽ điều chỉnh
nếu vận hành cho thấy vấn đề.

Mỗi quyết định có **điều kiện xem lại** cụ thể — không phải "xem lại khi cần",
mà là một dấu hiệu quan sát được. Khi prompt sở hữu thi công xong, quyết định đó
được nâng thành một mục Q trong `docs/QUYET_DINH_NEN_TANG.md` theo giao thức ở
`AGENTS.md`. Trước lúc đó, file này là nơi chốt.

---

## D1 — Delegated OAuth: **HOÃN, có ADR.** Thay bằng khoá bị giới hạn.

**Chủ sở hữu:** EXT-04.

### Bối cảnh
OAuth delegated access chỉ giải một bài toán: **bên thứ ba hành động thay mặt
người dùng LTT bằng credit của người đó**. Hôm nay chưa có bên thứ ba nào như
vậy — không có yêu cầu, không có đối tác, không có ai hỏi.

### Quyết định
Không xây OAuth trong pack này. Xây **restricted key** — thứ giải quyết ~80% nhu
cầu tích hợp thật với ~10% chi phí:

| Thuộc tính khoá | Vì sao cần |
|---|---|
| thuộc một **Project** | tách tích hợp A với B, thu hồi từng cái |
| **scope** (đã có) | quyền tối thiểu |
| **tool allowlist** (đã có) | khoá chỉ chạy được đúng việc của nó |
| **IP allowlist** | khoá rò từ máy lạ là vô dụng |
| **hạn dùng** (`expires_at`) | khoá bỏ quên tự chết |
| **trần credit riêng** | thiệt hại có biên, xem D3 |

Người dùng muốn thuê một agency vận hành tích hợp thì cấp cho họ một khoá thuộc
project riêng, có hạn, có trần chi, thu hồi được trong một cú bấm. Đó là 90%
những gì OAuth mang lại cho tình huống này, không cần authorization server.

### Vì sao không làm OAuth ngay
- Chi phí thật: authorization server + client registry + consent + PKCE +
  refresh rotation + revocation + admin console cho client + threat model cho
  redirect/code/token. Khoảng 3–4 prompt, và **vĩnh viễn phải bảo trì**.
- Nó mở một lớp tấn công mới (redirect, code injection, token replay) để bảo vệ
  một luồng chưa ai dùng.
- `RESEARCH_AND_DESIGN_BASIS.md` nói thẳng: đừng thêm OAuth theo trào lưu.
- Bài toán thật của delegated access **không phải** là grant flow mà là **tiền
  của ai bị tiêu**. Chưa trả lời được câu đó thì OAuth chỉ là vỏ.

### Bảo hiểm rẻ phải làm ngay (EXT-04)
Mọi quyết định phân quyền **chỉ đọc `Principal`**, không đọc thẳng dòng khoá.
`Principal` hiện đã có `user_id`/`key_id`/`scopes`; giữ nguyên tính chất đó thì
sau này thêm `Principal` sinh từ OAuth token là **thêm một nguồn**, không phải
viết lại authz. Chi phí hôm nay: bằng không. Phải có test chốt.

### Điều kiện xem lại
Có **một** bên thứ ba thật (đối tác đã nêu tên, không phải giả định) cần chạy
tool bằng credit của người dùng LTT mà **không** được cầm khoá của người đó.
Khi đó mở lại D1 và làm authorization code + PKCE + exact redirect + refresh
rotation, theo RFC 9700, không có ngoại lệ.

---

## D2 — Giá theo thời lượng: **đo phía server lúc báo giá.** Cấm top-up cho job API.

**Chủ sở hữu:** EXT-02 (chuẩn) + EXT-03 (contract) + prompt mở tool.
**Mở khoá:** `video.upscale`, `video.subtitle`, `video.short_clips` — cả ba.

### Bối cảnh
Ba tool này tính giá theo `duration_s` **do người gọi khai**, rồi worker nâng
hold khi đo được thời lượng thật (`_dam_bao_giu_cho`). Với người bấm nút trên
giao diện thì chấp nhận được. Với máy gọi máy thì nó phá lời hứa của một quote đã
ký (Q84) — khách được báo 10 credit rồi bị trừ 40.

### Hai lựa chọn và vì sao chọn (a)

**(a) Đo phía server lúc báo giá.** File đã nằm trong `upload_sessions`, đã qua
kiểm magic-signature trước khi báo giá. Chạy `ffprobe` một lần (~50–200 ms), lấy
thời lượng thật, khoá giá vào quote.

**(b) Cấm top-up, để job fail-refund nếu vượt.** Job chạy vài phút rồi chết giữa
chừng vì client khai thiếu. Khách được hoàn tiền nhưng mất thời gian; LTT mất
GPU thật **và không thu được gì**. Độ tin cậy của API trở thành hàm của việc
client có khai trung thực hay không — đó là thiết kế sai chỗ.

→ **Chọn (a).** Một lần đọc metadata trên file đã có sẵn, đổi lấy một hợp đồng
giá không nói dối. Đây cũng là chỗ sửa đúng cho cả đường giao diện.

### Quy tắc thi hành
1. Tool tính giá theo thời lượng **bắt buộc** nhận media qua upload đã `confirm`;
   không nhận `duration_s` từ client như một tham số tính tiền.
2. Báo giá đo từ chính file đó; **probe hỏng → từ chối báo giá**, đúng bất biến
   "không tra được giá thì không chạy" (Q5).
3. Quote khoá theo `upload_id` (đã có fingerprint input) → không đánh tráo file
   được sau khi báo giá.
4. **Job đến từ API không được top-up.** Nếu worker đo lệch, giữ nguyên giá đã
   ký và ghi variance — `quyet_toan()` đã cap thu ≤ hold và ghi variance sẵn
   (Q84). Chênh lệch nhỏ do LTT chịu; log variance sẽ nói ngay nếu nó từng đáng
   kể.
5. Hàm probe đặt ở `platform_core` (dùng chung), **không** chép vào từng app.

### Điều kiện xem lại
Log variance cho thấy sai số đo phía server vs worker vượt **2%** trên một mẫu
có ý nghĩa → xem lại cách đo, không xem lại quyết định.

---

## D3 — Trần credit ngày: **2.000 credit/ngày**, đếm **chỉ chi tiêu qua API**.

**Chủ sở hữu:** EXT-11 (cảnh báo) + EXT-14 (trần theo tier/khoá).

### Con số
`LTT_PUBLIC_API_DAILY_CREDIT=2000` làm mặc định lúc bật.

1 credit = 100đ (Q31) → trần **200.000đ/ngày**. Đủ cho ~400 thumbnail, hoặc
~125 ảnh `pro`, hoặc ~500 lượt upscale nhanh mỗi ngày — thoải mái cho tích hợp
thật giai đoạn đầu, mà một khoá rò thì thiệt hại có trần và có thời gian phát
hiện. Trần này nói về **tốc độ mất tiền**, không phải tổng: số dư tài khoản vẫn
là chặn cứng.

### Sửa một lỗi phạm vi (bắt buộc, không phải tuỳ chọn)
`limits.credit_spent_since()` hiện cộng **mọi** chi tiêu credit của tài khoản,
kể cả tiêu trên giao diện web. Hệ quả: khách dùng web nhiều thì **API của chính
họ ngừng chạy** — bất ngờ và sai mục đích. Trần này sinh ra để giới hạn bán kính
thiệt hại của **một khoá API bị rò**.

→ Chỉ đếm hold **có nguồn gốc API** (job có `key_id` trong meta). EXT-14 thêm
trần **theo từng khoá** bên cạnh trần theo tài khoản; khoá lộ thì trần khoá chặn
trước.

### Kèm theo (EXT-11)
Cảnh báo ở **50%** và **80%** trần ngày, gửi qua `platform_core/mailer.py`. Cảnh
báo **không phải** sổ cái: nó không ghi tiền, chỉ báo.

### Điều kiện xem lại
Một khách hợp lệ chạm trần **hai ngày liên tiếp** → nâng trần cho tài khoản đó
(EXT-14 tier), **không** nâng mặc định toàn hệ thống.

---

## D4 — Sandbox: **mock hoàn toàn, cùng đường code, namespace khoá riêng.**

**Chủ sở hữu:** EXT-12.

### Quyết định
Test mode chạy **đúng** route, auth, validate schema, quote, idempotency, job
lifecycle và webhook như live. Chỉ **một** mắt xích bị thay: lời gọi provider
được thay bằng artifact đóng hộp, tất định.

| Thuộc tính | Giá trị |
|---|---|
| Khoá | namespace riêng `ltt_sk_test_…`; **một khoá test không tiêu được đồng nào** |
| Credit | không có dòng ledger nào; nhưng vẫn **kiểm tra đủ số dư giả lập** để client thấy lỗi thiếu credit trước khi lên live |
| Provider | không gọi, không tốn tiền |
| Job/webhook | có thật, có `test: true`, giao qua đúng cơ chế outbox |
| Usage/log | hiện ra nhưng **gắn cờ test**, không cộng vào tổng thanh toán |
| Dữ liệu | chung bảng, tách bằng cờ — **không** dựng CSDL thứ hai |

### Vì sao mock chứ không "tiêu tiền thật với model rẻ"
Cái integrator cần chứng minh trong sandbox là **dây nối**: khoá đúng chưa,
schema đúng chưa, retry có double-charge không, webhook có tới không. Cả bốn thứ
đó không cần một lời gọi provider thật. Còn chất lượng đầu ra thì mock **không
bao giờ** chứng minh được — và họ kiểm nó bằng một lời gọi live trên tool rẻ
nhất, đó mới là phép thử đúng.

Lợi ích lớn nhất của mock lại là bảo mật: **khoá test rò ra không mất một đồng
nào.** Đó chính là thứ khoá live không thể có.

### Bẫy phải tránh, viết vào tiêu chí nghiệm thu
Sandbox mà **không** đi qua code thật thì integrator xanh ở sandbox rồi vỡ ở
live — tệ hơn là không có sandbox. Nghiệm thu EXT-12 phải chứng minh: cùng một
input sai cho ra **cùng một mã lỗi** ở test và ở live; retry trùng
`Idempotency-Key` ở test cho ra **cùng hành vi replay** như live.

### Điều kiện xem lại
Xuất hiện lỗi kiểu "chạy được ở test, hỏng ở live" mà nguyên nhân là do mock →
mở rộng phần được chạy thật, **không** chuyển sang sandbox tốn tiền.

---

## D5 — STREAM cho chat: **định nghĩa mode, KHÔNG mở chat.**

**Chủ sở hữu:** EXT-02 (định nghĩa) + EXT-20 (chứng nhận khi có operation).

### Quyết định
EXT-02 vẫn **định nghĩa đầy đủ** mode `STREAM` (ngữ nghĩa credit, cancel, retry,
lỗi giữa chừng) và SDK/docs sẵn sàng cho nó. Nhưng **không operation nào dùng
`STREAM` trong pack này**, và cụ thể là **không mở `chataistudio` ra `/api/v1`**.

### Ba lý do, lý do đầu là quyết định
1. **ToS.** `chataistudio` chạy qua sidecar đăng nhập tài khoản ChatGPT Plus —
   một rủi ro người dùng đã chấp nhận **cho việc dùng của chính mình**. Bán nó
   qua API cho bên thứ ba là chuyển từ "tự dùng" sang **bán lại quyền truy cập
   một tài khoản tiêu dùng**. Đó là một loại rủi ro khác hẳn, và không phải thứ
   nên gánh trên bề mặt thương mại.
2. **Không có Job.** Credit giữ theo id tin nhắn, không có dòng `jobs` → nằm
   ngoài toàn bộ bất biến quote/hold/settle mà API dựa vào.
3. **Ngữ nghĩa tiền khi stream** thật sự khó: đứt giữa chừng thì tính bao nhiêu?
   Câu trả lời đúng phải thiết kế cùng một provider có hợp đồng thương mại rõ —
   không phải cùng một sidecar.

### Hướng đi khi muốn có chat API
Thêm một tool text/chat **dựa trên provider có hợp đồng** (như các provider đang
dùng cho ảnh), rồi cho nó là operation `STREAM` đầu tiên. Đó là một hạng mục sản
phẩm mới, không phải một prompt trong pack này.

### Điều kiện xem lại
Có provider chat hợp đồng thương mại rõ ràng trong `api_pool` → mở D5, dùng
đúng định nghĩa STREAM mà EXT-02 đã viết.

---

## D6 — Service account: **HOÃN, có ADR.** Project là tầng sở hữu, key là danh tính máy.

**Chủ sở hữu:** EXT-04 (đã thi hành phần project).

### Bối cảnh
Phân cấp mà EXT-04 chốt:

```
User            billing, credit — mọi thứ nền tảng đã sở hữu (Q92)
 └─ Project     một tích hợp; đơn vị để THU HỒI, ĐẶT NGÂN SÁCH, ĐỌC LOG
     └─ Key     một credential; đơn vị để XOAY
```

Service account sẽ nằm **giữa** project và key: một danh tính máy sống lâu hơn
bất kỳ credential nào của nó.

### Quyết định
Không xây bây giờ. Hôm nay **key chính là danh tính máy**: nó có scope, có tool
allowlist, có IP allowlist, có hạn dùng, và thuộc một project. Thêm một thực thể
nữa với đúng một dòng cho mỗi key và **không hành vi riêng** là thêm một phép
join phải bảo trì để đổi lấy không gì cả.

### Vì sao hoãn được mà không thành nợ xấu
Thêm sau là **cộng thêm**, không phải sửa lại: key đã trỏ vào project, nên service
account chỉ cần là một chủ sở hữu **tuỳ chọn** bên trong project đó. Không dòng
nào phải di chuyển, không khoá ngoại nào phải đổi hướng.

### Điều kiện xem lại
Xuất hiện **một** trong hai dấu hiệu: (a) một khách cần nhiều credential dùng
chung *đúng một* bộ quyền và muốn quản lý bộ quyền đó ở một chỗ; hoặc (b) audit
cần trả lời "máy nào đã làm việc này" khi credential đã bị xoay nhiều lần.

---

## D7 — API Client Application (OAuth client): **KHÔNG tạo bảng trước.**

**Chủ sở hữu:** EXT-04, gắn với [D1](#d1--delegated-oauth-hoãn-có-adr-thay-bằng-khoá-bị-giới-hạn).

D1 đã hoãn delegated OAuth. `client_id`, redirect URI, consent, refresh rotation
chỉ có nghĩa **bên trong** một authorization server. Tạo sẵn bảng
`api_client_applications` rỗng lúc này là dựng một bảng không ai đọc, không ai
ghi, nhưng vẫn phải migrate, sao lưu và khôi phục.

Hình dạng đã ghi lại để lúc cần không phải thiết kế từ đầu: `client_id`, chủ sở
hữu (User), tên, trạng thái, danh sách redirect URI **khớp chính xác**, scope
được phép, `created_at`; client bí mật chỉ dành cho confidential client; không
implicit grant, không resource-owner-password.

---

## Tóm tắt

| # | Quyết định | Prompt | Hệ quả ngay |
|---|---|---|---|
| D1 | Hoãn OAuth, làm restricted key (project + IP + hạn dùng + trần chi) | EXT-04 | Bỏ 3–4 prompt; giữ `Principal` mở đường cho OAuth sau |
| D2 | Đo thời lượng phía server lúc báo giá; cấm top-up cho job API | EXT-02/03 | Mở được **3 tool** đang bị chặn |
| D3 | 2.000 credit/ngày, chỉ đếm chi tiêu qua API, cảnh báo 50%/80% | EXT-11/14 | Sửa một lỗi phạm vi đang có trong `limits.py` |
| D4 | Sandbox mock, cùng đường code, khoá `ltt_sk_test_` không tiêu tiền | EXT-12 | Khoá test rò = 0đ |
| D5 | Định nghĩa STREAM, không mở chat qua sidecar | EXT-02/20 | Tránh bán lại tài khoản tiêu dùng |
| D6 | Hoãn service account; project là tầng sở hữu, key là danh tính máy | EXT-04 | Thêm sau là cộng thêm, không phải sửa lại |
| D7 | Không tạo trước bảng OAuth client | EXT-04 | Bảng rỗng vẫn phải migrate/sao lưu/khôi phục |

Không quyết định nào ở trên còn để trạng thái UNKNOWN.
