# Cổng lập trình viên — rà soát và kế hoạch đưa về MVP thật

**2026-08-25.** Rà soát theo yêu cầu chủ sản phẩm: *công cụ `.exe` đã tối ưu
chưa · tài liệu đủ để một dev đọc hiểu và triển khai chưa · trang API cần phân
tích logic vận hành và thiết kế lại thế nào.*

> Mọi dòng trong mục 1 là **số đo**, lấy trên production
> (`https://app.lttstudios.com`) và trên cây mã, không phải nhận định.

---

## 0. "MVP thật" ở đây đo bằng gì

`docs/VLM_NOI_BO/DUT_DIEM.md` đã đặt thước, và thước đó vẫn đúng:

> Một người lạ **tìm được giá, đăng ký, lấy khoá, cắm vào công cụ của họ, gọi
> được, bị tính đúng tiền — và ta biết ngay nếu hỏng.**

Tài liệu này soi **vế ④ (cắm vào công cụ)** và mọi thứ quanh nó: trang, tài liệu,
công cụ. Vế ⑤ ⑥ đã chứng minh; vế ② ③ cần người thật đi thử.

⛔ Một luật xuyên suốt, và nó là thứ đã sai nhiều lần ở dự án này:
**"có mã và có test" không phải là xong.** Ba lỗi tối 24/08 (tiền kẹt trong hold,
log 500 rỗng, ngữ cảnh gửi model bị bóp méo) đều có mã, đều có test, và đều chỉ
lộ ra ở **lượt gọi thật đầu tiên từ máy khách**.

---

## 1. Bảy phát hiện, kèm bằng chứng

### 1.1 🔴 Toàn bộ cổng lập trình viên nằm **sau đăng nhập**

```
/developers            -> 303      /developers/pricing  -> 303
/developers/docs       -> 303      /developers/cli      -> 303
/developers/quickstart -> 303
/gia-api               -> 200      /api/v1/openapi.json -> 200
```

18 trang trong `server/templates/dev_*.html`, **tất cả** sau `require_account`.

⚠️ **CHỐT CHỦ SẢN PHẨM 25/08 — TOÀN BỘ `/developers/*` nằm sau đăng nhập.**
Đây là kết luận cuối, sau khi tôi ghi nhầm "cả 18 trang sau `require_account`"
thành một khuyết điểm. `/developers/tools` và cả khu **đúng** khi ở sau đăng nhập: hệ thống API của LTT phải
đăng nhập mới kích hoạt được, nên danh mục công cụ là trang **của một tài
khoản**, không phải trang bán hàng. Cùng lý do với `keys`, `usage`, `logs`,
`webhooks`, `playground`.

⇒ Phần thật sự đặt sai, và là phần đã sửa: **hướng dẫn cắm** + **đường tải công
cụ và SDK**. Người đang cân nhắc không đọc được một dòng nào và không lấy được
một tệp nào.

⭐ Ranh giới để lần sau không phải hỏi lại: **thứ trả lời "có đáng mua không" thì
công khai; thứ trả lời "tôi đang dùng cái gì" thì sau đăng nhập.**

Một người đang **cân nhắc** không đọc được một dòng hướng dẫn tích hợp nào trước
khi tạo tài khoản. Dự án đã học đúng bài này một lần — `DUT_DIEM.md` §7 ghi *"trang
giá cũ nằm sau `require_account`… thứ tự ngược, và nó chặn đúng người cần nhất"* —
nhưng chỉ sửa **riêng trang giá**. Bài học chưa được áp cho phần còn lại.

### 1.2 🔴 Trang tài liệu trỏ khách vào **đường dẫn tệp trong kho mã của ta**

`server/templates/dev_docs.html` liệt kê cho khách:

```
docs/PUBLIC_API/DEVELOPER_GUIDE.md
docs/PUBLIC_API/PROTOCOL_V1.md
docs/PUBLIC_API/RECIPES.md
sdk/python/ltt_public_api.py
sdk/typescript/ltt-public-api.ts
sdk/postman/
```

Khách **không có kho mã của ta**. Bảy mục thì năm mục là đường dẫn không tồn tại
đối với người đọc. Trang này trông như một mục lục đầy đủ, và đó là phần tệ nhất:
nó làm ta tin rằng tài liệu đã có.

### 1.3 🔴 SDK **không tải được bằng bất kỳ đường nào**

```
/developers/sdk/python          -> 404
/sdk/python/ltt_public_api.py   -> 404
/static/sdk/ltt_public_api.py   -> 404
```

Không có route nào phục vụ `sdk/`. SDK một-file, không phụ thuộc — thứ được quảng
cáo là điểm mạnh — hiện **chỉ tồn tại trong kho của ta**.

### 1.4 🔴 Công cụ `.exe` **không được nhắc tới ở đâu trên site**

`grep` cả `server/routes/` và `server/templates/`: không có chuỗi `CamCLI`, không
có route tải, `/developers/cli` **không nhắc một chữ nào** về công cụ.

Ta đã dựng bộ cài 24,7 MB có chữ ký băm, chạy thật trên VM sạch — và khách không
có cách nào lấy nó. Một công cụ không phân phối được thì chưa tồn tại.

### 1.5 🟡 `cam_cli.py` **không có số phiên bản và không ghi log ra tệp**

`grep -E "PHIEN_BAN|VERSION|logging"` trong `tools/cam_cli.py`: **không có gì**.
Bộ cài khai `1.0.0`, còn chương trình bên trong không biết mình là bản nào.

Hệ quả khi có khách: họ báo "cắm không được", ta không biết họ chạy bản nào, và
không có tệp log nào để họ gửi. `#nhatky` trong GUI chỉ là một `<div>` trên màn
hình, mất khi đóng cửa sổ.

### 1.6 🔴 `kiem` **không kiểm hai thứ vừa làm vỡ Claude Desktop**

`lenh_kiem` gọi `/tools`, `/credits/balance`, rồi `/messages` với
`{"model": MODEL, "stream": True}`.

Tức nó **không** kiểm:
* tên tuyến `ltt-llm-claude-compat` (bề mặt Claude Desktop),
* đường **không-stream** (chính đường Claude Desktop dùng để thăm dò).

Đêm 24/08 `kiem` báo xanh trong khi Claude Desktop **không gửi nổi một tin nhắn**.
Một phép tự kiểm không phủ được bề mặt mà nó vừa cấu hình là một phép tự kiểm
đang trấn an nhầm chỗ.

### 1.7 🔴 `/messages` khai `tool_use` mà **không trả khối `tool_use`**

`server/api/streaming.py` đặt `stop_reason = "tool_use"` khi model gọi tool, nhưng
`content` luôn chỉ là `[{"type": "text", …}]`. Dữ liệu có sẵn (`kq.tool_calls`),
chỉ là bị vứt. Client Anthropic đọc `stop_use` rồi đi tìm khối tương ứng, không
thấy ⇒ vỡ hoặc treo.

Đây đúng là vế `D1` mà `DUT_DIEM.md` ghi là *"phiên thật có gọi tool"* — chưa ai
thử, và bây giờ biết chắc là sẽ hỏng.

### 1.8 🟡 `/api/v1/models` lệch hình dạng Anthropic

Ta trả `{"items": [{"name": …}]}`; hợp đồng Anthropic là
`{"data": [{"id", "type", "display_name", …}]}`. Hiện né được vì công cụ đặt
`modelDiscoveryEnabled=false`, nhưng bất kỳ client nào bật khám phá model sẽ vấp.

### 1.9 🟡 Không có **điều khoản riêng cho API**

`PUBLIC_LINKS` có `terms` chung và `vps_terms` riêng, **không** có `api_terms`.
Bán dung lượng tính toán theo credit mà không có điều khoản riêng là một khoảng
trống pháp lý, không phải một mục trang trí.

---

## 2. Trả lời thẳng ba câu hỏi

### 2.1 Công cụ `.exe` đã tối ưu chưa?

**Phần lõi: rồi.** Nó làm đúng việc khó nhất và làm cẩn thận — đọc/ghi giữ nguyên
ký tự xuống dòng, chèn theo khối có mốc, sao lưu trước khi chạm, `go` trả về đúng
trạng thái cũ, không bao giờ ghi khoá vào tệp cấu hình, phủ cả năm bề mặt.

**Phần đưa tới tay khách: chưa.** Ba lỗ, xếp theo mức chặn:

| # | Thiếu | Hậu quả |
|---|---|---|
| 1 | không có đường tải | khách không lấy được — công cụ coi như không tồn tại |
| 2 | không có số phiên bản + log tệp | không hỗ trợ được khi khách báo lỗi |
| 3 | `kiem` không phủ Claude Desktop | báo xanh trong khi bề mặt đó đang hỏng |

### 2.2 Tài liệu đã đủ để một dev đọc hiểu và triển khai chưa?

**Nội dung: thừa. Đường tới nội dung: gần như không có.**

29 tệp, hơn 10.000 dòng trong `docs/PUBLIC_API/` — trong đó `DEVELOPER_GUIDE.md`
646 dòng, `RECIPES.md`, `PROTOCOL_V1.md`, `HUONG_DAN_CAM_CLI.md` 352 dòng đều là
tài liệu tốt. Nhưng **không dòng nào được xuất bản**. Thứ khách thấy là một trang
liệt kê đường dẫn tệp họ không có (1.2), sau một cổng đăng nhập (1.1).

⇒ Câu trả lời trung thực: **một dev bên ngoài hiện KHÔNG triển khai được** nếu
không có ai trong ta cầm tay chỉ.

### 2.3 Trang API — logic vận hành và thiết kế

18 trang, gần hết sửa lần cuối **13–15/08** — tức được dựng khi **chưa mở tool
nào**. Từ đó `text.chat` và `image.ltt` đã mở, model nhà đã bán, công cụ cắm đã
có. Cấu trúc thông tin vẫn là cấu trúc của thời "hạ tầng đã sống, cửa hàng chưa
mở".

Vấn đề **không phải màu sắc hay bố cục** — hệ thống thiết kế (`ltt.css`) dùng
token đã thống nhất và ổn. Vấn đề là **thứ tự kể chuyện** và **ranh giới công
khai / riêng tư**:

```
Hôm nay:   [đăng nhập] → mọi thứ
Phải là:   công khai: giá · công cụ có gì · cắm thế nào · gọi thử · điều khoản
           riêng tư: khoá · dự án · log · usage · webhook · ngân sách
```

Ranh giới đúng rất rõ: **thứ giúp người ta quyết định mua thì công khai; thứ gắn
với tài khoản thì sau đăng nhập.** Hôm nay ranh giới đó nằm sai chỗ hoàn toàn.

---

## 3. Kế hoạch

## 3b. Đã thi hành — 25/08

**Deploy `deploy-20260825-014354`, `EXITCODE=0`, 01:44:35.** Nghiệm thu trên
**URL công khai** (không phải loopback), bằng trình duyệt thật:

| Đường | Kết quả |
|---|---|
| `/huong-dan` | `200`, 22.426 byte — **không** cần đăng nhập |
| `/huong-dan/cong-cu` | `200`, 10.681 byte |
| `/tai/cong-cu-cam` | `200`, **25.937.392 byte** qua Cloudflare |
| SHA-256 tệp tải về | **khớp từng byte** với bản dựng |
| `/tai/ltt_public_api.py` · Postman | `200` |
| Console trình duyệt · request hỏng | **không có** |

| # | Trạng thái |
|---|---|
| P0-1 | ✅ `/huong-dan` + `/huong-dan/cong-cu` công khai; thêm link ở chân trang và ở `/gia-api` |
| P0-2 | ✅ `/tai/cong-cu-cam` + băm SHA-256 **tính từ chính tệp**, không phải chuỗi gõ tay |
| P0-3 | ✅ `/tai/<goi>` cho 5 tệp SDK; `dev_docs.html` không còn một đường dẫn kho mã nào |
| P0-4 | 🟡 hướng dẫn cắm đã xuất bản (một include dùng chung với `/developers/cli`, nên không thể lệch). `RECIPES.md` **chưa** thành trang |
| P0-5 | ✅ `kiem` thử thêm `ltt-llm-claude-compat` **và** đường không-stream — đúng hai thứ đã làm vỡ Claude Desktop mà nó từng báo xanh |
| P0-6 | ✅ `PHIEN_BAN` (khớp bộ cài, có test chốt) + nhật ký `%LOCALAPPDATA%\LTTStudios\cam-cli.log`, xoay vòng, **không bao giờ ghi khoá** |

Thêm một việc ngoài kế hoạch, phát sinh khi rà `tool_use` (§1.7) — và số đo làm
đổi kết luận:

> `_mot_cuc` **không hề truyền `tools`** lên model. Nên `stop_reason: "tool_use"`
> hiện **chưa thể xảy ra** ở đường đó; thứ thực sự hỏng là **`tools` bị bỏ im
> lặng** — tác tử của khách không dùng được công cụ, và không có triệu chứng nào.

Đã bịt phần **nói dối**: nếu upstream báo `tool_calls` mà ta không dựng được khối
`tool_use`, hạ `stop_reason` về `end_turn`. Một câu trả lời thiếu tool là thứ
khách thấy ngay; một client **treo** thì không. Hỗ trợ tool cho tử tế cần dịch
**hai chiều** (`tools`/`tool_use`/`tool_result` ↔ `tools`/`tool_calls`/tin `tool`)
— đó là P1-1, một đợt riêng có test riêng, không phải một miếng vá đính kèm.

---

### Đợt P0 — bỏ chặn khách (không cần chủ sản phẩm)

| # | Việc | Đạt khi |
|---|---|---|
| P0-1 | **Mở công khai** ba trang: hướng dẫn cắm (`/huong-dan`), danh mục công cụ, bắt đầu nhanh. Tách khỏi `require_account`, giữ nguyên nội dung | mở bằng cửa sổ ẩn danh, không đăng nhập, đọc hết |
| P0-2 | **Route tải công cụ** `.exe` + hiện băm SHA256 ngay cạnh nút | tải từ máy sạch, băm khớp bản dựng |
| P0-3 | **Route tải SDK** (`python`, `typescript`, `postman`) và **xoá mọi đường dẫn kho mã** khỏi `dev_docs.html` | không còn chuỗi `docs/` hay `sdk/` nào trong template khách đọc |
| P0-4 | **Xuất bản** `HUONG_DAN_CAM_CLI.md` + `RECIPES.md` thành trang thật (không phải link tệp) | nội dung trên web khớp tệp nguồn, có test chốt |
| P0-5 | `kiem` phủ **cả** `ltt-llm-claude-compat` và đường **không-stream** | chạy `kiem` trên máy hỏng Claude Desktop thì nó ĐỎ |
| P0-6 | `cam_cli` có `PHIEN_BAN` + ghi log `%LOCALAPPDATA%\LTTStudios\cam-cli.log` (xoay vòng, **không** ghi khoá) | `xem` in phiên bản; log có dòng cho mỗi lần `cam`/`go` |

### Đợt P1 — đúng hợp đồng (không cần chủ sản phẩm)

| # | Việc | Đạt khi |
|---|---|---|
| P1-1 | **Khối `tool_use`** trong `/messages` (1.7) | một lượt gọi tool đi trọn vòng: model gọi → client chạy → gửi `tool_result` → model trả lời |
| P1-2 | `/api/v1/models` **thêm** hình dạng Anthropic, giữ tương thích ngược (1.8) | bật `modelDiscoveryEnabled=true` trên VM, picker tự đầy |
| P1-3 | Kể lại **trang API** theo ranh giới ở §2.3: trang đích công khai → giá → cắm → gọi thử → (đăng nhập) bảng điều khiển | một người lạ đi từ trang chủ tới lượt gọi đầu tiên **không hỏi ai** |
| P1-4 | Trang **trạng thái** công khai (`/status-api`) — có sẵn template, chưa mở | 200 khi không đăng nhập |

### Đợt P2 — cần chủ sản phẩm

| # | Việc | Ai |
|---|---|---|
| P2-1 | **Điều khoản API** + thêm `api_terms` vào `PUBLIC_LINKS` (1.9) | nội dung: chủ sản phẩm · nháp: tôi |
| P2-2 | **C16** thu tường lửa máy B về một IP | chủ sản phẩm |
| P2-3 | Đi thử bằng **tài khoản mới toanh** (vế ② ③) — tôi bị Turnstile chặn, và tôi không vượt CAPTCHA | chủ sản phẩm |
| P2-4 | Hoàn `−1` credit hold mồ côi 23:58:10 (trước bản vá) | chủ sản phẩm cho phép ghi bút toán |
| P2-5 | Một khách thật gọi và trả tiền | chủ sản phẩm |

---

## 3c. Audit giao diện — chấm điểm, 25/08

Đo bằng **Chrome thật** (Playwright) trên `https://app.lttstudios.com` và trên một
bản chạy cục bộ, không phải đọc template. Mỗi trang render, chụp màn hình, soi
console và request hỏng, xem cả 1440px lẫn 390px.

### Thang điểm — 5 tiêu chí, mỗi tiêu chí 2 điểm

| Tiêu chí | 0 | 1 | 2 |
|---|---|---|---|
| **Đến được** | không link nào trỏ tới | chỉ từ một chỗ khuất | có trong điều hướng chính |
| **Có kiểu** | class không có luật CSS nào khớp | có nhưng thiếu (khối mã trần) | thẻ, bảng, khối mã đều đúng |
| **Hành động được** | chỉ có chữ | có lệnh nhưng phải tự tô để chép | có nút, có bước tiếp theo rõ |
| **Trạng thái rỗng** | bảng trắng | báo "chưa có gì" | nói luôn phải làm gì để có |
| **Không nói dối** | link chết / trỏ vào kho mã | có chỗ lỗi thời | đúng hết, cấu trúc heading đúng |

### 🔴 Phát hiện gốc: `ltt.css` KHÔNG có `.card`, `.table` hay `pre`

Kiểu của ba thứ đó nằm **nội tuyến trong `base.html`** — vỏ đã đăng nhập.
`base_public.html` có khối `<style>` riêng chỉ đặt nền `body`.

⛔ Nên **mọi trang công khai** render với class không có luật nào khớp: thẻ không
tách nhau, bảng chỉ là mấy cột chữ trôi nổi, **khối mã là chữ trần trên nền
trang** — trên đúng một trang mà toàn bộ mục đích là để khách **chép cấu hình**.

⭐ Đối chứng làm rõ chẩn đoán: `/status/api` dùng `base.html` và trông đẹp chuẩn.
Cùng một hệ thống thiết kế, khác nhau ở chỗ **có CSS hay không**.

⚠️ Và nó giải thích một lỗi thứ hai tưởng không liên quan: `/gia-api` có **hai
thẻ `<h1>`** trong khi 17 trang còn lại có đúng một. Thẻ và bảng không ai kiểm
thì cấu trúc tài liệu cũng không ai kiểm — hai lỗi cùng một gốc.

### Điểm, trước và sau

| Hạng mục | Trước | Sau | Đã làm gì |
|---|---|---|---|
| Kiểu dùng chung cho vỏ công khai | 0/2 | **2/2** | tách `_kieu_chung.html`, **cả hai vỏ cùng include** — một nguồn, không tạo bản sao thứ hai |
| Khối mã | 0/2 | **2/2** | nền + viền + lề + cuộn ngang trong khung riêng; thêm **nút Sao chép** (`sao_chep.js`, tăng cường dần — không JS thì không nút, trang vẫn đọc được) |
| Đến được khu API | 0/2 | **2/2** | thêm `API` vào **thanh trên**, hiện cho cả người chưa đăng nhập. Trước đó lối duy nhất là mục trong menu tài khoản — **chỉ hiện sau khi đăng nhập** |
| Cấu trúc heading | 1/2 | **2/2** | `/gia-api` còn đúng một `h1` |
| Trang tình trạng | 1/2 | **2/2** | `/status/api` vốn đã công khai nhưng **không trang nào trỏ tới** — nay có link |
| Cache-bust tài sản tĩnh | 0/2 | **2/2** | `ASSET_VER` trước chỉ băm `ltt.css`; một tệp JS mới sẽ mang đúng số của CSS và bị Cloudflare giữ mãi |

### Còn nợ — do phiên VPS đo, ghi lại ở đây để không mất

**P1-5 — bản tiếng Anh của cổng lập trình viên không tồn tại.**
Đo trên `/en/developers/...` thật, đã bỏ khối mã khỏi phép đo:
**367/434 = 85% đoạn văn vẫn là tiếng Việt**. Năm trang thuần Việt 100% dù
`lang="en"`: `projects`, `keys`, `jobs`, `notifications`, `settings`.

⛔ Kết luận đúng không phải "dịch dở dang" mà là **không có bản dịch nào cả**,
chỉ đổi thẻ `<html lang>`. Khách của Public API là lập trình viên và phần lớn sẽ
chọn `en`; thứ họ thấy là một hạ tầng làm dở — và không ai giao thẻ tín dụng cho
một hạ tầng làm dở.

⚠️ Việc đổi mặc định sang `vi` (25/08) làm **ít người gặp cảnh này hơn**, nhưng
**không sửa gì**: ai chọn `en` vẫn thấy y nguyên.

**Trạng thái 25/08: khu API đã dịch xong** — phiên VPS đo lại trên trang render
thật, phần `<main>`, 14 trang: **0/286 = 0%** còn tiếng Việt. Chốt bằng
`tests/test_299_khu_api_da_dich.py`.

### 🔴 P1-7 — tài liệu SINH RA đã trôi khỏi mã, ngay trong `HEAD`

Phiên VPS phát hiện 25/08, và nó **không phải lỗi của lần sửa nào trong ngày**:

```
git show HEAD:apps/ltt_llm/manifest.py      ->  MAX_TOKENS_TRAN = 32_768
git show HEAD:docs/…/DEVELOPER_GUIDE.md     ->  max_tokens … max 16384
```

Commit `c246858` nâng trần nhưng không chạy `tools/build_public_api_docs.py`, và
tài liệu lệch **kể từ đó**.

⛔ Vì sao ca này nguy hiểm hơn nó trông: `DEVELOPER_GUIDE.md` là tài liệu ta
**xuất bản cho khách** (đợt P0-3 vừa gỡ hết đường dẫn kho mã khỏi `dev_docs.html`
để trỏ tới nó). Nó báo trần **thấp hơn một nửa** thực tế — nên khách tự kẹp ở
16.384 và **không bao giờ dùng hết thứ họ đã trả tiền để được dùng**.

⭐ Và nó sai **về phía không ai báo lỗi**: không `422`, không `429`, không một
triệu chứng nào. Chỉ có người dùng ít hơn mức họ có.

✅ ĐÃ BỊT 25/08: thêm bước gate `tai lieu sinh ra`
(`build_public_api_docs.py --check`). Phép kiểm đó **vốn đã tồn tại và đã trả mã
1 khi lệch** — nhưng nó chỉ chạy trong pytest, thứ `gate --quick` bỏ qua. Cùng
đúng một lỗ với ảnh chụp hợp đồng (§3b): **phép kiểm CÓ, mà không ai gặp nó đúng
lúc cần.** Đã thử ngược: làm lệch tài liệu → mã 1; khôi phục → mã 0.

⚠️ Bài học chung của cả hai ca, đáng nhớ hơn từng ca: **mọi thứ "sinh ra từ mã"
đều là một bản sao, và bản sao nào không có bánh cóc canh thì sẽ trôi.** Ta hiện
có ba: ảnh chụp hợp đồng, `DEVELOPER_GUIDE.md`, `ho_so_he_thong.txt`. Cả ba nay
đều có bước gate riêng.

### ⚠️ Và một vế nữa, do phiên VPS chỉ ra — nó rộng hơn cả ba ca

**Cả ba lần trôi đã biết đều đi qua CÙNG một cửa: người commit chạy
`gate --quick`.**

`--quick` tồn tại vì một lý do thật (vòng lặp ngắn khi đang sửa). Nhưng phép
kiểm bắt được cả ba ca đều nằm ở **phía bên kia** cửa đó — nên chúng có mà không
ai gặp đúng lúc cần.

⛔ Nếu có lần trôi thứ tư thì câu hỏi **không còn là** *"thêm bánh cóc nào"* mà
là *"vì sao chúng nằm bên kia cửa"*.

⭐ Đề xuất khi tới lúc đó: chuyển mọi bước **rẻ** (dưới ~2 giây) sang `--quick`,
và để `--quick` chỉ còn nghĩa là *"bỏ pytest"*. Ba bánh cóc thêm ngày 25/08 —
`anh chup hop dong`, `tai lieu sinh ra`, `bien dich duoc` — đều dưới 2 giây.

---

### 🔴 P1-6 — 89 mục `fuzzy` ngoài khu API là **bản dịch SAI đang nằm sẵn**

Không phải "chưa dịch xong". `msgmerge` **đoán** bản dịch, và đoán sai kiểu nguy
hiểm:

| msgid | msgstr fuzzy |
|---|---|
| Ngân sách của bạn | Your **scripts** |
| Chưa đăng ký điểm nhận nào. | **Not signed in** |

⛔ Thứ duy nhất giữ chúng không hiện ra là một **mặc định của `msgfmt`** (bỏ qua
mục fuzzy). Một lần đổi công cụ, hoặc một lần ai đó thêm `--use-fuzzy` "cho đầy
đủ", là chúng lên production — và lên dưới dạng **một câu tiếng Anh trôi chảy**,
không phải một ô trống dễ nhận ra.

⚠️ Cố ý **chưa** gỡ cờ: gỡ cờ cho một bản dịch chưa ai đọc lại chính là làm nó
hiện ra. Việc đúng là **đọc lại rồi mới gỡ**, và đó là việc của người biết tiếng.
Ghi số 89 ở đây để nó không biến mất cùng phiên làm việc.

### ⚠️ Bài học kỹ thuật đi kèm, rộng hơn i18n

`governance.py` nối chuỗi ngầm qua nhiều dòng: `N_("aaa" "bbb")`. Một bộ trích
bằng **regex** sẽ cắt cụt `msgid` và **im lặng bỏ sót** — triệu chứng là *"đã
dịch xong mà trang vẫn tiếng Việt"*, và không ai nghĩ tới bộ trích.

⭐ `tools/check_i18n.py` **không** dính: nó dùng `ast`, và trong AST hai literal
kề nhau đã là **một** node `Constant` — Python nối chúng ngay lúc phân tích cú
pháp. Kiểm 25/08. Ghi lại để phiên sau không đi sửa một thứ không hỏng.

---

## 4. Cái **không** làm trong đợt này

| Không làm | Vì sao |
|---|---|
| Ký số công cụ | chủ sản phẩm đã chốt không mua chứng chỉ; chấp nhận cảnh báo SmartScreen |
| Thiết kế lại `ltt.css` | hệ thống thiết kế không phải vấn đề; cấu trúc thông tin mới là |
| Mở `qwen38-ops` (200K) · `text.vision` · streaming cho SDK OpenAI | `DUT_DIEM.md` §3 đã chốt: chưa ai cần |
| Tự động cập nhật cho `.exe` | thêm một bề mặt tấn công và một dịch vụ phải nuôi, trong khi chưa có khách |

---

## 5. Vì sao thứ tự này

P0 xếp trước **không phải vì dễ** mà vì mọi thứ khác đều vô nghĩa nếu khách không
tới được: tài liệu hay tới đâu, sau một cổng đăng nhập thì cũng không ai đọc; công
cụ tốt tới đâu, không tải được thì cũng không ai chạy.

P1-1 (`tool_use`) xếp trên P1-3 (thiết kế) vì nó là **hợp đồng sai**, không phải
trải nghiệm chưa đẹp. Một client gọi tool sẽ treo, và triệu chứng — như mọi lỗi
trong tuần này — **không chỉ về phía nguyên nhân**.
