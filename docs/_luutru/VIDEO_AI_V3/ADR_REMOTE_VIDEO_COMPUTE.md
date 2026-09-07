# ADR-3 — Kiến trúc compute video từ xa (A-CONTROL ↔ C-CLOUD)

- **Trạng thái:** ✅ **APPROVED** — chủ dự án duyệt **2026-09-04**
  (*"Duyệt như bạn khuyến nghị. Triển khai theo quy trình."*)
- **Ghi vào nguồn chân lý:** `docs/QUYET_DINH_NEN_TANG.md` → **Q121**
- **Ngày:** 2026-09-04 · **Người đề xuất:** Claude (theo V-006)
- **Bối cảnh quyết định bởi:** V-001 · V-002 · V-003 (`DECISIONS.md`), D01–D12
- **Chấm điểm:** `docs/VIDEO_AI/ARCHITECTURE_SCORECARD.csv`
- **Phiên bản:** **v4** (2026-09-04) — xem §0, §0b, §0c

## 0c. v4: ranh giới tin cậy hạ một bậc, và GPU đã chốt

Hai quyết định của chủ dự án, ghi đầy đủ ở `DECISIONS.md`:

**`V-007` — C-CLOUD ĐƯỢC giữ credential lưu trữ.** Ràng buộc *"không giữ bí mật
nào"* của Q102 **không còn áp cho C-CLOUD**. Thi hành bằng **temporary credentials
của R2**: máy A sinh credential giới hạn ở tiền tố `lttvideo/<user>/<job_id>/`,
`ttlSeconds` bằng trần thời gian job, thu hồi được dây chuyền qua token cha.
⇒ Mục *"Ranh giới tin cậy"* ở §2 bên dưới **đã bị thay** — đọc `V-007` thay vì nó.
⇒ **Máy B không đụng** (cách presigned của nó đang chạy đúng; đổi là phá D02 để
lấy về không gì cả).

**`V-008` — GPU chốt A100 80GB.** Wan2.2 **A14B** (bậc chất lượng) đòi **≥80GB
ngay cả khi đã bật `--offload_model --convert_model_dtype`** — README chính chủ nói
ba lần cho ba mode. ⇒ **Không có bậc 48GB để nhắm tới**; "đòn bẩy 2,23×" mà v3 nêu
**không tồn tại với model này**. Ngân sách thực: **~55 giờ GPU/tháng** ở
$2,72/giờ serverless.

## 0b. v3: nghiên cứu cộng đồng đổi HÌNH DẠNG, không đổi phán quyết

Chủ dự án yêu cầu tra tài liệu cộng đồng thay vì tự suy. Kết quả đầy đủ ở
**`NGHIEN_CUU_CLOUD_GPU.md`**. Một câu:

> 🔴 **Cộng đồng không thuê Pod rồi tự viết vòng đời GPU — họ dùng SERVERLESS GPU**,
> và nhà cung cấp đã bán đúng thứ mà **P14** định xây.

| | v2 | **v3** |
|---|---|---|
| Hình dạng C-CLOUD | Pod thuê dài, ta tự quản vòng đời | **Serverless endpoint** |
| `video_gateway` | dịch vụ FastAPI | **một lõi + HAI cửa vào** (handler serverless · dịch vụ) |
| **P14** | máy trạng thái 8 trạng thái, single-flight, đối soát mồ côi | **phần lớn XOÁ** |
| Xác thực (§9 ①) | câu hỏi mở | **khoá API nhà cung cấp → APIKEYS**, ta không mở cổng nào ra Internet |
| Media lớn (§9 ②) | câu hỏi mở | **presigned PUT một phát là đủ** (R2 single-part 5 GiB); yêu cầu thật là **chảy dòng**, không phải multipart |
| `videos_of()` (§9 ③) | câu hỏi mở | **đọc được từ mã**: lõi ComfyUI → `"images"` + `"animated"`; VideoHelperSuite → `"gifs"` |

**KHÔNG đổi:** không sửa `render_gateway` · app `lttvideo` · provider `ltt_video` ·
`platform_core/video_gen/` · ranh giới Q102 (presigned GET/PUT, C-CLOUD không giữ
bí mật nào).

⭐ **"Một lõi, hai cửa vào"** giữ nguyên tính khả chuyển mà v2 đã hứa: V1 chạy
serverless (rẻ nhất khi tải thưa); vượt **ngưỡng hoà vốn 36–51 %** thì bật cửa
dịch vụ trên Pod **không viết lại**; và nếu sau này chạy tại nhà thì vẫn cửa đó.

## 0. Bản v2 đổi gì so với v1, và vì sao

Chủ dự án bổ sung ba dữ kiện sau khi đọc v1:

> *"Máy B hiện tại đang **max tải**. Mua card **giá rất đắt, không khả thi**.
> Ta sẽ phải triển máy C — đây là **kế hoạch phát triển**, không phải thí nghiệm."*

Điều đó **đóng `V-005②`** (thuê hay mua → **thuê**) và **đổi một trọng số**:
C-CLOUD là **vĩnh viễn**, không phải một POC có thể vứt.

⚠️ Và nó làm **yếu đi** đúng một lập luận của v1. v1 viết *"nợ trùng lặp tạm thời,
trả sau P09"* — chữ **tạm thời** dựa trên giả định C-CLOUD có thể chỉ là một giai
đoạn. Nếu nó là vĩnh viễn thì ~600 dòng trùng lặp là **vĩnh viễn**, và
"trả sau" là cách mà nợ kỹ thuật thường không bao giờ được trả.

**Đổi:** v1 đề xuất *chép các mô-đun chung vào `video_gateway/` rồi trích lõi
sau P09*. **v2 đề xuất tạo gói lõi chung `gateway_core/` NGAY TỪ ĐẦU**, chỉ
`video_gateway` dùng nó ở giai đoạn 1, và `render_gateway` chuyển sang dùng ở
giai đoạn 2. Chi phí thêm ở giai đoạn 1 gần bằng **không** (mã vẫn phải nằm ở
đâu đó), nhưng giai đoạn 2 biến từ **một cuộc trích xuất** thành **một lần xoá**.

**KHÔNG đổi:** phán quyết gốc — **không sửa `render_gateway`, tạo cổng mới.**
Bản v2 đọc sâu hơn hẳn v1 (`runner.py`, `busy.py`, `storage_io.py`,
`ngan_sach.py`, `theo_doi_luot.py`, `tren_gpu.py`, `deploy/*.ps1` và 111 phép
kiểm của `test_245`) và **mọi thứ đọc thêm đều đẩy mạnh hơn về cùng phía** — xem
§3b, phần đo mới.

✅ **Đã duyệt.** D01 thoả. Code kiến trúc tích hợp được phép từ **P10** trở đi —
nhưng vẫn theo đúng thứ tự pha: P01/P02 → P03 → P04 → P05/P06 → P07 → P08 → P09 → P10.

---

## 1. Câu hỏi

`policies/TOPOLOGY_AND_BOUNDARIES.md` cố ý không trả lời sẵn:

> **A** — tổng quát hoá `render_gateway` tại chỗ
> **B** — một lõi/giao thức chung + hai runtime riêng (LAN và cloud)
> **C** — một worker cloud riêng, tương thích các hợp đồng đã có
> **D** — phương án khác có bằng chứng

---

## 2. Đề xuất

> ## ✅ Chọn **C** — cổng mới, **không sửa `render_gateway`**.
> ## Nhưng tách **lõi chung `gateway_core/` ngay từ đầu**, không chép rồi hẹn dọn.

Bốn thành phần, không thành phần nào sửa thứ đang phục vụ khách:

```
gateway_core/                 LÕI CHUNG (mới) — comfy · workflows · catalog
                              · jobs · http · ma_loi.  KHÔNG chứa trọng tài card,
                              KHÔNG chứa gì của ảnh, KHÔNG chứa gì của Windows.
video_gateway/                cổng chạy TRÊN C-CLOUD (Linux). Dùng gateway_core.
platform_core/video_gen/      adapter phía A: cong_video.py · dieu_phoi.py
apps/lttvideo/                app: manifest · jobs · routes · gia.py     (V-002)
platform_core/providers.py    + MỘT mục `ltt_video`   ← thay đổi duy nhất ở nền tảng

render_gateway/               ⛔ KHÔNG ĐỤNG ở giai đoạn 1. Giữ nguyên bản sao của
                              nó. Giai đoạn 2 mới trỏ sang gateway_core và xoá.
```

Tên gọi không phải tuỳ hứng — nó là khuôn đã có ba lần trong kho:
`render_gateway` (ảnh, máy B) · `llm_gateway` (LLM, máy B) · **`video_gateway`**
(video, C-CLOUD). Phía A: `platform_core/image_gen/` ⇒ `platform_core/video_gen/`.

### Vì sao là một PROVIDER chứ không phải một sidecar

Kho này có **hai** tiền lệ đối nghịch, và phải chọn đúng cái:

| | Q102 — `ltt_image` | Q117 — LTT VOICE |
|---|---|---|
| Engine chạy ở đâu | **máy khác**, qua mạng | cùng máy, sau loopback |
| Có khoá phải xoay? | **có** | không |
| Chết độc lập được? | **có** | không |
| Có hạn mức/bận phải đo? | **có** (429) | không |
| Kết luận | **provider** | app + sidecar, **không** provider |

C-CLOUD khớp **từng dòng** của cột Q102. Và lý do Q117 từ chối provider —
*"sẽ buộc phải mở rộng enum hạng mục khoá API… tức sửa nền tảng cho một năng lực
không dùng tới"* — **không áp dụng ở đây**: `APIKEY_CAT_VIDEO = "video"` đã tồn tại
sẵn trong `platform_core/models.py:650`.

⇒ Đăng ký provider **không** phải là mở rộng nền tảng. Nó là dùng đúng cái cửa đã
chừa sẵn, và `providers.py` nói thẳng điều đó ở dòng đầu:
*"Thêm loại API mới về sau = thêm MỘT dòng ở REGISTRY (+ tuỳ 1 adapter gọi HTTP),
KHÔNG sửa app, KHÔNG sửa nơi khác."*

Được miễn phí kèm theo: `api_pool` (cấp phát khoá, cooldown, telemetry rpm/tpm,
cascade đa-provider), `providers_live` (làm mới danh sách model), và toàn bộ
`jobs`/`credit`/`storage` không phải chạm.

### Hợp đồng HTTP của `video_gateway`

Trùng khuôn `render_gateway` — **không phải để dùng chung mã**, mà để phía A đọc
được **không thêm một nhánh phân tích nào**:

| Đường | Khoá | Hợp đồng |
|---|---|---|
| `GET /live` | ❌ | sống/chết, không nói gì thêm, không mang bí mật |
| `GET /health` | ✅ | `busy` · `reason` · `eta_s` · `gpu` · `models` |
| `GET /v1/models` | ✅ | khuôn `{"data":[…]}` ⇒ `providers_live.parse_models` đọc được ngay |
| `POST /v1/videos/generations` | ✅ | **202 + `job_id`**; gửi lại cùng `job_id` ⇒ trả job cũ (idempotency) |
| `GET /v1/jobs/{id}` | ✅ | |
| `POST /v1/jobs/{id}/cancel` | ✅ | huỷ **đúng** `prompt_id` |
| mọi lúc bận | | **429 + `Retry-After`**, ⛔ không bao giờ 5xx |

### ~~Ranh giới tin cậy — sao chép nguyên Q102~~ — **ĐÃ THAY bởi `V-007`** (xem §0c)

> ⚠️ Đoạn dưới mô tả ranh giới **của bản v1–v3**. Từ `V-007`, C-CLOUD **được** giữ
> một credential R2 **tạm, giới hạn tiền tố, có hạn**. Ba luật của `cong_render.py`
> (429≠hỏng · không đổi model sau lưng khách · `job_id` là khoá idempotency) thì
> **vẫn nguyên hiệu lực**. Giữ văn bản gốc để truy được lý do:

**C-CLOUD không giữ bí mật nào của nền tảng.** Không mật khẩu CSDL, không khoá gốc
R2, không khoá phiên. Media **vào** bằng presigned GET, **ra** bằng presigned PUT,
cả hai do máy A cấp, có hạn, ràng buộc đúng một khoá.

⛔ Và ba luật của `platform_core/image_gen/cong_render.py` là **bắt buộc**, không
phải gợi ý — cả ba đều đã được trả giá:

1. **429 là BẬN, không phải hỏng.** Coi nó là lỗi provider ⇒ `api_pool` cooldown ⇒
   `disable` sau 5 lần ⇒ **tự tắt vĩnh viễn** cổng của chính mình. Phía A dịch nó
   thành `jobs.DangBan` (`platform_core/jobs.py:86`) ⇒ về hàng đợi, **không tiêu
   một lượt thử nào**.
2. **Không tự đổi model sau lưng khách.** Bận thì báo bận kèm ETA. C-CLOUD **không**
   được lặng lẽ rơi về Seedance.
3. **`job_id` là của máy A và phải ổn định** — nó là khoá idempotency. Bản đầu của
   cổng ảnh thiếu chốt này và đốt ~100 giây GPU mỗi lần gửi lại. Với A100 thuê
   theo giờ, cùng lỗi đó là **tiền mặt**.

---

## 3. Vì sao **không** phải A hay B

### Điểm chung giết cả hai: chúng đều phải sửa `render_gateway` **ngay bây giờ**

Mà D02 nói: *"B-LAN tuyệt đối không thay đổi behavior/deployment **trước khi**
C-CLOUD Video POC chạy độc lập."* Không phải "hạn chế thay đổi" — mà là một thứ
tự bắt buộc. A và B đảo ngược đúng thứ tự đó.

### Và một lý do thứ hai, ít hiển nhiên hơn nhưng mạnh hơn

Tiền đề của **B** là *"dùng chung phần ống nước ComfyUI"*. Nhưng **D04 chưa chốt
backend production**:

> *"ComfyUI là baseline; backend production được quyết sau benchmark, không fix
> DiffSynth/ComfyUI trước."*

⇒ Trích một **lõi ComfyUI dùng chung trước P09** là đầu tư vào đúng thành phần
có thể bị thay. Nếu P09 chọn DiffSynth thì công trích lõi đó **bốc hơi**, và tệ hơn
là nó đã kịp lôi `render_gateway` vào cuộc.

⭐ **Tài sản bền không phải client ComfyUI — nó là hợp đồng HTTP của cổng.**
Đó chính là thứ `render_gateway` làm đúng: ComfyUI là chi tiết cài đặt **sau** một
hợp đồng nhỏ, và đổi model từ Klein 9B sang HiDream-O1 không phải sửa dòng nào.
Phương án C giữ nguyên bài học đó mà không phải động vào bản đang chạy.

### Trùng lặp thật của C là bao nhiêu

⚠️ **Bảng đo của v1 đã bị §3b thay.** v1 ước ~600 dòng dựa trên bốn mô-đun;
v2 đọc hết 2.823 dòng và cho một bức tranh khác — xem **§3b**. Cố ý **không**
để hai con số trong cùng một tài liệu: hai bảng lệch nhau thì bảng nào cũng
không đáng tin, và đó đúng là lỗi mà `CLAUDE.md` ghi đã xảy ra năm lần.

---

## 3b. Đo lại sâu hơn (v2) — và nó lật một giả định của chính câu hỏi

Câu hỏi *"sửa `render_gateway` hay tạo cổng mới"* ngầm giả định `render_gateway`
là **một cổng ComfyUI**. Đọc hết 2.823 dòng thì nó không phải:

> 🔴 **`render_gateway` là một cổng ComfyUI CỘNG một trọng tài tranh chấp GPU cho
> một máy nhà bốn hộ dùng chung một card — và phần trọng tài chiếm khoảng một
> phần ba mã, cùng phần lớn độ phức tạp đắt giá nhất của nó.**

C-CLOUD có **card riêng, một hộ**. Nó không cần một dòng nào của phần đó.

### Bảng phân loại từng tệp

| Nhóm | Tệp | Dòng | Sang C-CLOUD được? |
|---|---|---|---|
| **Lõi chung** | `workflows.py` · `catalog.py` · `http.py` · `jobs.py` | 414 | ✅ **0 chỗ dính ảnh** |
| **Lõi chung** | `comfy.py` | 247 | ✅ 18/21 thành viên thuần runtime; cần **thêm** `videos_of()` |
| **Điều phối** | `runner.py` | 321 | ✅ ~250 dòng (idempotency xuyên tiến trình qua `/history` · thử lại OOM đúng một lần · hết giờ thì huỷ **đúng** prompt · kiểm node trước khi tiêu GPU · bảng mã lỗi là hợp đồng với máy A) |
| **Đo lúc chạy** | `theo_doi_luot.py` | 214 | ✅ gần như nguyên — bắt ca "model chỉ thường trú một phần", ca này **có ở mọi GPU** |
| ⛔ **Trọng tài card dùng chung** | `busy.py` · `nhuong_card.py` | 690 | ⛔ **không** — lý do tồn tại là *nhiều hộ một card* |
| ⛔ **Trọng tài card dùng chung** | phần trong `api.py` | ~130 | ⛔ 37 dòng gọi thẳng, trải từ dòng 36→305: luồng trả card, `goi_nha`, `SoDuoi`, và **thứ tự ba chốt** (giữ suất → xin card → hỏi bận) |
| ⛔ **Hằng số đã đo theo model** | `ngan_sach.py` · `tren_gpu.py` | 265 | ⛔ **ý tưởng** đi được, **số** thì không: `PATCH = 32` là của HiDream-O1, trần 11.412 token là số đo trên 3090 |
| ⛔ **Ảnh** | `storage_io.py` + phần `runner`/`api` | ~215 | ⛔ phải **viết lại**, không phải sửa — xem dưới |
| ⛔ **Windows/NSSM** | `main.py` + `deploy/*.ps1` | 95 + **1.183** | ⛔ Runpod là **Linux** |

### Bốn điều đọc thêm mới thấy, và cả bốn đều đẩy về cùng một phía

**① Triển khai KHÔNG dùng lại được, dù chọn phương án nào.**
`main.py` đọc `C:\ProgramData\LTTRender\gateway.env`, chạy dưới **NSSM**;
`deploy/deploy.ps1` đẩy qua SSH tới `192.168.2.66` và mở tường lửa Windows.
**1.183 dòng PowerShell**, thuần ASCII vì PowerShell 5.1. Trên Pod Linux thì
toàn bộ chỗ này viết mới — nên cái lợi *"một mã nguồn, hai nơi triển khai"* của
phương án A **nhỏ hơn nhiều so với cảm giác ban đầu**.

**② Ảnh và video khác nhau về CẤU TRÚC, không phải về đuôi tệp.**
`storage_io.day_ket_qua(anh: list[bytes], …)` giữ **toàn bộ** kết quả trong RAM
rồi PUT một phát; `comfy.download()` cũng `buf.extend` cả tệp. Đúng cho một ảnh
PNG vài MB. Với video — `TRAN_ANH_REF_MB = 8` cho đầu vào, và một video 720p/10s
đã hàng chục MB, 1080p dài hơn thì hàng trăm — thì đây là **một mô hình vào/ra
khác**: phải chảy dòng ra presigned PUT, và đầu vào V2V là **video**, không phải
ảnh ≤8 MB có kiểm magic byte PNG/JPEG/WebP.
⇒ Tổng quát hoá tệp này nghĩa là **viết lại nó** rồi bắt đường ảnh đang chạy
dùng bản viết lại đó.

**③ `ngan_sach.py` YẾU ĐI khi bị tổng quát hoá — và nó là chốt an toàn.**
Nó tồn tại vì một sự cố thật: 22/08 máy B **khởi động lại đột ngột** giữa một lô
ảnh, ở cấu hình chiếm 97,5 % VRAM. Nguyên tắc của nó là *"chưa đo thì không
chạy"*, và sức mạnh đến **từ chỗ nó là hằng số cứng, theo model, đã đo**
(`PATCH = 32` của HiDream; trần 11.412 token nâng lên **bằng số đo**, không bằng
suy đoán). Biến nó thành cấu hình cho hai model trên hai loại card là **làm mềm
đúng cái chốt** đã ngăn máy sập.

**④ 111 phép kiểm trong `test_245` là bản mô tả hành vi của B-LAN.**
Chúng chốt những thứ như *"có mục lịch sử KHÔNG có nghĩa là thành công"*,
*"OOM thì nhả VRAM và thử lại ĐÚNG MỘT lần"*, *"hết giờ thì huỷ ĐÚNG prompt của
mình"*, *"việc lạ trong hàng đợi làm máy bận"*. Sửa `render_gateway` nghĩa là
phải giữ cả 111 phép kiểm đó xanh **trong khi** thêm một chiều hoàn toàn mới.
Đó không phải một lý do để không bao giờ làm — nhưng nó là lý do để **không làm
lúc máy B đang max tải và C-CLOUD còn chưa chạy được một khung hình nào**.

### Và một lập luận ngược, phải nói ra vì nó thật

`runner.py` **không** phải mã tầm thường. Từng khối trong nó là một sự cố đã xảy
ra: idempotency xuyên tiến trình (21/08, xếp hàng lại một job đã xong, đốt 100
giây GPU cho không) · huỷ đúng `prompt_id` (nếu không thì giết lượt video 70
phút của hộ khác) · hai điều kiện để coi là xong chứ không phải một · lấy mẫu
trong lúc chạy (24/08, đường khách dùng chạy mù trong khi đường đo lấy 198 mẫu).

**Viết lại nó từ đầu là vứt đi bốn sự cố đã trả giá.** Đó chính là lý do v2
không nói *"chép sang rồi tính sau"* mà nói **tách vào `gateway_core/` ngay từ
đầu**: để hai cổng dùng **cùng một** bản, chứ không phải hai bản sẽ trôi.

---

## 4. Nợ và cách trả — **v2 sửa chỗ này**

### Giai đoạn 1 (tới hết P09) — không đụng `render_gateway`

`gateway_core/` sinh ra bằng cách **chép** phần chung ra một gói mới (kèm
`videos_of()` thêm vào `comfy.py`). Chỉ `video_gateway` dùng nó.
`render_gateway` **giữ nguyên bản của nó, không sửa một dòng** ⇒ D02 thoả, gate
**G-B** xanh, 111 phép kiểm của `test_245` không bị đụng tới.

**Nợ trong giai đoạn này:** ~700 dòng tồn tại hai bản.

### Chống trôi — bằng bánh cóc, không bằng lời hứa

Kho đã có sẵn khuôn tệp mốc: `tools/check_bo_qua.moc`, `check_dich_thieu.moc`,
`check_so_test.moc`. Thêm một cái nữa:

```
tools/check_song_sinh.moc      băm của các tệp render_gateway có bản song sinh
```

Phép kiểm (dải **700–799**) ghim **băm** của `render_gateway/{comfy,workflows,
catalog,jobs,http}.py`. Ai sửa một trong số đó ⇒ **gate đỏ**, và chỉ có hai cách
đi tiếp: **chuyển thay đổi sang `gateway_core/`**, hoặc **cập nhật mốc kèm lý
do**. Cả hai đều là một quyết định có ý thức.

⭐ Vì sao ghim băm chứ không so từng byte hai tệp: chúng **được phép khác nhau**
(bản `gateway_core` có thêm `videos_of`). Thứ phải bắt không phải *"hai tệp khác
nhau"* mà là *"một bên đổi mà bên kia không ai nhìn"*.

### Giai đoạn 2 — **có điều kiện kích hoạt, không có ngày hẹn suông**

Kích hoạt khi **cả hai** đã đúng:
① C-CLOUD POC đã chạy độc lập (điều kiện D02 tự nói ra);
② backend production đã chốt (D04) — biết ComfyUI có thắng không.

Việc phải làm: `render_gateway` `import` từ `gateway_core`, xoá bản sao của nó,
gỡ `check_song_sinh.moc`. **111 phép kiểm của `test_245` là bộ characterization
test** — chúng đã tồn tại, không phải viết mới, và phải xanh **không sửa một
dòng test nào**.

⛔ Nếu ② hoá ra là *"đổi sang DiffSynth"* thì giai đoạn 2 **không xảy ra** và
`gateway_core` bị vứt cùng `video_gateway`'s ComfyUI. Đó là kết cục **chấp nhận
được** — và chính là lý do `gateway_core` phải **mỏng**: nó chỉ chứa ống nước
ComfyUI + kho việc + bảng mã lỗi, không chứa chiến lược nào.

## 5. Chấm điểm

Bảng đầy đủ ở `ARCHITECTURE_SCORECARD.csv`. Tổng có trọng số (tối đa **300**):

| | A tại chỗ | B lõi chung | **C worker riêng** |
|---|---|---|---|
| **Tổng** | **168** | **210** | **277** |

**Đọc bảng cho trung thực:** C thắng **11/14** tiêu chí, hoà 2, và thua đúng **một**
— `code_reuse`/`maintainability`, tức là **món nợ ở §4**. Nếu chỉ nhìn tổng điểm thì
bảng này là trang trí; cuộc tranh luận thật gói gọn trong một câu:

> *Có đáng đổi ~600 dòng trùng lặp tạm thời để lấy blast radius bằng **không** trên
> hai cổng đang thu tiền, cộng quyền hoãn quyết định backend tới khi có số?*

Với D02, D04 và V-001 (*tối giản chi phí, hỏng production là đắt nhất*) — **đáng**.

---

## 6. Ràng buộc mà ADR này phải thoả, và cách nó thoả

| Ràng buộc | Cách thoả |
|---|---|
| **D02** B-LAN không đổi trước POC | C không chạm `render_gateway`/`llm_gateway`. Gate **G-B** (`git diff` rỗng) canh tự động |
| **D04** backend chốt sau benchmark | ComfyUI nằm **sau** hợp đồng HTTP ⇒ đổi backend không đổi phía A |
| **D05** Runpod V1, mở đường thêm provider | vòng đời cloud tách khỏi đường gọi model; `providers.py` vốn đã đa provider |
| **D11** B-LAN không tham gia Video V1 | provider `ltt_video` là một mục **riêng**, `base_url` riêng; không hộ nào của B-LAN bị đụng |
| **D09 + V-003** giá ổn định, ghi cost thật | `credit.SettlementResult` đã tách `provider_credit`/`charged_credit`/`variance`/`capped` |
| **V-005②** thuê hay mua là quyết định *triển khai* | ⭐ `base_url` đọc từ biến môi trường, đúng như `ltt_image` hôm nay. Mua card về chạy `video_gateway` tại nhà ⇒ **đổi một biến**, không đổi một dòng kiến trúc |
| Ràng buộc §5: việc dài phải qua hàng đợi | mọi mode đi qua `jobs`; `requires=("api",)` |
| **Q114** admission plane dùng chung | app khai `admission_resource="ltt_video_gpu"`, `admission_slots=1` |
| `platform_core` không biết tên app nào | `video_gen/` chỉ biết provider `ltt_video`, không biết `lttvideo` |

---

## 7. Ranh giới với P14 (vòng đời GPU) — ⚠️ **v3 thu hẹp mạnh**

> 🔴 **Với serverless, phần lớn P14 không còn việc để làm.** Scale-to-zero, đồng hồ
> nhàn rỗi (mặc định **5 giây**), tính tiền theo giây, không thể có Pod mồ côi vì
> không có Pod nào để mồ côi. Xem `NGHIEN_CUU_CLOUD_GPU.md` §2.
>
> **Còn lại của P14:** trần chi tiêu · ghi `billed_seconds` thật cho từng job
> (`V-003`) · chính sách **gộp lô** (đo được: một video chạy lẻ tốn gần **gấp đôi**
> một video chạy trong lô, vì phải trả lại chi phí nạp model).
>
> Phần bên dưới **vẫn đúng** cho trường hợp sau này chuyển sang Pod (khi vượt
> ngưỡng hoà vốn), nên giữ lại chứ không xoá.

**Hai thứ khác nhau, hai chỗ khác nhau, hai loại khoá khác nhau:**

| | Gọi model | Điều khiển vòng đời Pod |
|---|---|---|
| Là gì | *"vẽ hộ tôi video này"* | *"bật/tắt một cỗ máy tiêu tiền"* |
| Đi qua | provider `ltt_video` + `api_pool` | mô-đun riêng (P14 chốt chỗ, đề xuất `platform_core/cloud_gpu/`) |
| Khoá cất ở | **APIKEYS** (như token cổng render, Q102) | **`secrets/app.env`** (như `LTT_CODEX_SIDECAR_TOKEN`, Q117) |
| Vì sao tách | | ⛔ Đặt khoá vòng đời vào `api_pool` là để cơ chế cooldown/**disable-sau-5-lỗi** của một nhà cung cấp *model* điều khiển thứ tạo ra **hoá đơn**. Sai ngữ nghĩa, và hỏng theo hướng đắt tiền |

Single-flight khi tạo Pod dùng `leases.acquire` (`platform_core/leases.py:87`) —
giành bằng `INSERT`, `IntegrityError` nghĩa là người khác thắng, tự lành sau TTL.
Đối soát Pod mồ côi đi qua `manifest.bao_tri` (chạy **dưới lease** ⇒ đúng một lần
trên toàn cụm, kể cả khi có N tiến trình worker).

---

## 8. Hệ quả nếu ADR này được duyệt

**Được:**
- P10 co lại: không refactor, chỉ nối hai đầu đã có khuôn.
- `gateway_core/` làm giai đoạn 2 thành **một lần xoá**, không phải một cuộc trích
  xuất — tức món nợ có đường ra, không chỉ có lời hứa.
- P11 chủ yếu là khai báo (`manifest` + `gia.py` + `jobs.py`), không phải dựng hạ tầng.
- Rollback của cả chương trình = **xoá một thư mục + gỡ một mục provider**.
- Mua card về chạy tại nhà sau này là **đổi một biến môi trường** (V-005②).

**Mất:**
- ~700 dòng tồn tại hai bản cho tới sau P09, canh bằng `check_song_sinh.moc` (§4).
- `video_gateway` phải tự viết phần đọc kết quả video từ ComfyUI (`videos_of`),
  không thừa hưởng được `images_of` đã kiểm chứng.

**Không đổi:** `render_gateway`, `llm_gateway`, `apps/taovideo`, 27 route
`/api/v1`, `platform_core/jobs.py`, `credit.py`, `storage.py`.

---

## 9. ~~Cái ADR này chưa trả lời~~ — **ba câu đã có đáp án ở v3**

> ✅ **① · ② · ③ đã được trả lời** bằng tài liệu chính chủ và mã nguồn thật —
> `NGHIEN_CUU_CLOUD_GPU.md` §3. Tóm tắt: ① biến mất (không mở cổng nào ra Internet);
> ② một phát là đủ, R2 single-part **5 GiB**; ③ `"images"`+`"animated"` với node
> lõi, `"gifs"` với VideoHelperSuite.
>
> ⏳ **Còn lại bốn câu mới, đều phải ĐO chứ không tra được:** pipeline nào vừa
> **48GB** (đòn bẩy **2,23×** chi phí) · cold start thật với model ~30 GB · trần
> thời gian thực thi của serverless với job video dài · giá 04/09 sẽ cũ.

Văn bản gốc giữ lại bên dưới để truy được lý do:

Ghi ra thay vì để lộ ra ở P10.

1. **Cổng C-CLOUD tự xác thực bằng gì.** Bearer token như `render_gateway` là mặc
   định hợp lý, nhưng đường đi là Internet chứ không phải LAN có tường lửa
   ⇒ P06 phải quyết mTLS / IP allowlist / Runpod proxy, và quyết bằng cái gì
   Runpod thật sự cung cấp.
2. **Video ra R2 bằng presigned PUT một phát hay multipart.** Ảnh vài MB thì một
   phát là đủ; video vài trăm MB thì chưa chắc. `storage.R2Storage` hiện chỉ có
   `put_url` đơn. → P06/P10 đo rồi quyết.
3. **`videos_of()` đọc khoá nào trong `outputs` của ComfyUI** — phụ thuộc node lưu
   video mà workflow dùng. Phải **đọc từ mã node**, không đoán (đúng cách
   `comfy.py` đã làm với ComfyUI 0.30.0 / `6f7cd7f`).
4. **Chỗ đặt mô-đun vòng đời Pod** — đề xuất `platform_core/cloud_gpu/`, P14 chốt.

---

## 10. Quyết định

- [x] ✅ **DUYỆT** (2026-09-04) — Claude được viết code theo phương án C (**kèm
      `gateway_core/` từ giai đoạn 1**) ở P10, và **đã ghi Q121** vào
      `docs/QUYET_DINH_NEN_TANG.md` (đặt LTT Video AI trong kiến trúc, khuôn Q102).
- [ ] **SỬA** — chủ dự án chỉ ra chỗ cần đổi.
- [ ] **TỪ CHỐI** — chọn A / B / D kèm lý do, P01 chấm lại.

⛔ Cho tới khi có dấu tick: **không một dòng code tích hợp nào** (D01).
