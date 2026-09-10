# KẾ HOẠCH DỰNG MÁY C — chi tiết, từ tài khoản trống tới video đầu tiên

> Bao P04 → P06. Viết trước khi bấm nút nào, để lúc chạy không phải nghĩ.
>
> ✅ **Đã xác nhận: RunPod có REST API đầy đủ.** `POST rest.runpod.io/v1/endpoints`
> và `POST rest.runpod.io/v1/networkvolumes`. ⇒ Sau khi anh nạp tiền, **toàn bộ
> phần còn lại dựng và vận hành bằng API**, không bấm tay.

Cấu hình đã chốt: A100 80GB serverless · volume **300 GB** · `max_workers = 1` ·
Wan2.2 A14B · ngân sách **$97,50 compute = 35,8 giờ** + sàn credit **$31,50**.

---

## 0. Ranh giới — ai làm gì

| | Việc | Ai |
|---|---|---|
| ① | Đăng ký tài khoản · 2FA · gắn Visa · nạp tiền | 🔴 **CHỦ DỰ ÁN** |
| ② | Tạo **API key** trong console, dán vào `secrets/app.env` | 🔴 **CHỦ DỰ ÁN** (xem §2) |
| ③ | Mọi thứ còn lại: volume, endpoint, image, nạp model, đo | ✅ **Claude, qua API** |

⛔ Tôi **không** gõ mật khẩu, không nhập thẻ, không nhận mã OTP. Trình duyệt đang
mở sẵn ở trang đăng ký; tôi dừng ở đó.

---

## 1. Việc của chủ dự án — đúng ba bước

### Bước 1 — Tạo tài khoản
Trình duyệt đã mở tại `console.runpod.io/signup`. Đăng ký bằng Google/GitHub hoặc
email đều được. Phiên sẽ được giữ trong profile `C:\LTTBrowserProfiles\RunpodLTT`.

### Bước 2 — Gắn thẻ và nạp tiền

> 💵 **Nạp bao nhiêu:** đề xuất **$50 cho đợt đầu**, không phải $150.

Vì sao không nạp trọn $150 ngay:
- P04 và P05 **không tiêu một đồng GPU nào** — chỉ có phí volume (~$0,70/ngày).
- Rủi ro thật của việc nạp nhiều vào một tài khoản mới: nếu cấu hình sai thì trần
  chi tiêu mặc định của RunPod là **$80/giờ**. $50 là mức mà một sai sót **không
  thể** làm mất quá số đó.
- Nạp thêm bất cứ lúc nào cũng được, và có **auto-pay** nếu muốn.

⚠️ **Đừng bật auto-pay ở đợt đầu.** Auto-pay + một vòng lặp hỏng = nạp lại tự động
trong khi tiền đang cháy. Bật nó **sau khi** cầu dao ngân sách đã chạy thật.

### Bước 3 — Tạo API key và đưa cho hệ thống

Trong console: **Settings → API Keys → Create API Key** (quyền đọc/ghi).

Khoá hiện ra **đúng một lần**. Chủ dự án dán nó vào `secrets/app.env` bằng lệnh
sẵn có của kho:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\dat_bien_env.ps1
```

⛔ **Đừng dán khoá vào khung chat.** Tôi không cần thấy giá trị — tôi chỉ cần nó
nằm trong `app.env` để đọc lúc gọi API. Đây cùng khuôn với `LTT_CODEX_SIDECAR_TOKEN`
và token cổng render: khoá đi thẳng vào chỗ cất, không đi qua nơi nào khác.

Tên biến: **`RUNPOD_API_KEY`**.

---

## 2. Việc của tôi — theo thứ tự, mỗi bước có điều kiện đạt

### P04-a · Kiểm trước khi tạo gì — ✅ **ĐÃ XONG 04/09/2026**

```
① Hỏi GIÁ LIVE lần thứ ba          — không dùng bảng của P03
② Đọc số dư + trần chi tiêu tài khoản
③ Chọn DC từ danh sách 11 (§2b) — KHÔNG từ danh sách 15 của trang S3
④ Thử `executionTimeoutMs = 1800000` xem máy chủ có nhận không
```

**Kết quả — toàn văn ở `VAN_HANH_MAY_C.md`:**

| Kiểm | Kết quả |
|---|---|
| ① Giá live A100 80GB Serverless | **$0,00076/giây = $2,736/giờ** — khớp P03, lệch 0 % |
| ① Giá lưu trữ standard | **$0,07/GB/tháng** ⇒ 300 GB = $21,00/tháng — khớp P03 |
| ② Số dư · Auto-Pay · trần | $50,00 · **Disabled** · $80/giờ |
| ③ **DC** | **`US-KS-2`** — DC **duy nhất** trong 11 có `NVIDIA A100 80GB PCIe`, và có đường lui `H100 NVL` 94 GB ngay trong cùng DC |
| ④ `executionTimeoutMs` | dải hợp lệ **5 giây – 7 ngày**; 1 800 000 ms nằm trong dải |

🔴 **Phép đo ③ đã cứu một sai lầm đắt:** ba trong 11 DC (`EUR-NO-1`, `US-IL-1`,
`US-WA-1`) **không có một GPU ≥ 80 GB nào**. Chọn theo cảm giác là 27 % rơi vào
đó, và giá của việc rơi vào đó là nạp lại 220 GB.

🔴 **Hai khoản chi P03 bỏ sót, nay đã vá vào `VAN_HANH_MAY_C.md`:**
container disk ~$0,10/GB/tháng (mặc định 50 GB ⇒ $5/tháng thừa; ta đặt 20), và
`idleTimeout` (chốt **60 giây**, có phép tính đi kèm).

### P04-b · Tạo network volume

```bash
POST https://rest.runpod.io/v1/networkvolumes
{ "name": "lttvideo-models-v1", "size": 300, "dataCenterId": "<1 trong 11 DC>" }
```

⛔ **Ba tham số, và `dataCenterId` là cái duy nhất không sửa lại được.** `size` nới
được bằng `PATCH`; `name` đổi được; **DC thì không** — sai DC là tạo volume mới và
nạp lại 220 GB.

**Đạt khi:** có `volumeId`, ghi ngay vào `COST_LEDGER.csv` cùng DC và thời điểm.

⚠️ **Đây là lúc đồng hồ tiền bắt đầu chạy** — $21/tháng tính **theo giờ**. Từ đây
mỗi ngày trôi qua tốn ~$0,70 dù chưa sinh khung hình nào.

#### ✅ ĐÃ XONG 04/09/2026 16:20 (+07)

```json
{"id":"uizchbiet5","name":"lttvideo-models-v1","size":300,"dataCenterId":"US-KS-2"}
```

Đối chứng độc lập ngay sau đó: GraphQL `myself.currentSpendPerHr` nhảy từ 0 lên
**0,029 USD/giờ** ⇒ 0,029 × 24 × 30 = **$20,88/tháng**, khớp phép nhân
300 × $0,07 = $21,00. Hai nguồn khác nhau nói cùng một con số.

### P04-c · Cầu dao ngân sách — **trước** khi có endpoint

Ba phép thử dry-run của `CLOUD_SAFETY_PLAN.md` §3, chạy **không cần GPU**:

| Thử | Đạt khi |
|---|---|
| Cầu dao ngân sách | sổ giả tiêu 100 % envelope ⇒ provider về không phục vụ; job mới nhận `DangBan`, không tiêu attempt, không chạm sổ credit |
| Sàn credit | số dư giả = $30 (< sàn $31,50) ⇒ ngắt compute, **volume vẫn sống** |
| Kiểm kê mồ côi | liệt kê qua API, lọc tiền tố `lttvideo-`, khớp đúng danh sách |

Cả ba nằm dải test **700–799**.

⛔ **Không tạo endpoint trước khi ba phép thử này xanh.** Đây là hard gate của
`NON_NEGOTIABLE_GATES` P04, và nó có lý do: sau khi có endpoint thì một lỗi cấu
hình tiêu tiền thật.

#### ✅ ĐÃ XONG 04/09/2026 — **26 phép kiểm xanh, 0 đồng, 0 lượt chạm mạng**

| Tệp | Nội dung |
|---|---|
| `platform_core/video_gen/ngan_sach.py` | cầu dao + sàn credit. **Thuần**, sáu con số gõ tay, phần còn lại tính ra |
| `platform_core/video_gen/cloud_api.py` | client REST + GraphQL, HTTP **tiêm được** |
| `tests/test_710_ngan_sach_video.py` | 13 phép kiểm — ngắt, sàn, thứ tự ưu tiên, `DangBan` |
| `tests/test_711_cloud_api_video.py` | 13 phép kiểm — kiểm kê mồ côi, đường dừng, lỗi mạng |
| `tools/video_cloud.py` | `trang-thai` · `kiem-ke` · `dung` · `mo-lai` — hỏi máy, không đọc bảng |

Ba phép kiểm đáng nhớ hơn cả:

- **`test_thu_tu_kiem_theo_thu_tu_thiet_hai`** — khi cả hai ngưỡng cùng thủng,
  cầu dao phải báo **sàn credit**, không báo hết envelope. Một bản cài đặt kiểm
  ngược lại vẫn ngắt đúng 100 % trường hợp nhưng **báo sai lý do**, và người vận
  hành đọc "hết ngân sách tháng" sẽ đi chờ sang tháng thay vì đi nạp tiền — trong
  khi cái đang bị đe doạ là 300 GB model.
- **`test_bang_envelope_pha_khong_duoc_vuot_tong`** — bảng cấp phát theo pha của
  P03 cộng lại ra **36,0 giờ** trong khi tổng thật là **35,63**. Một sổ vượt chi
  ngay trên giấy, sống sót vì nó được cộng bằng tay. Đã hạ dự phòng 5,4 → 5,0.
- **`test_khong_co_duong_nao_xoa_network_volume`** — đọc mã, chốt rằng client
  **không có** đường xoá volume. Rào cản cố ý, không phải thiếu sót.

Đối chiếu với tài khoản thật (`python tools\video_cloud.py kiem-ke`):
**1 tài nguyên, của ta, 0 mồ côi.**

### P05 · Nạp 220,8 GB model — **không đốt một giây GPU**

```
① Tạo S3 API key (Settings → S3 API Keys) — KHÁC RunPod API key
② Đẩy model qua endpoint S3 của DC: https://s3api-<dc>.runpod.io/
③ Sinh BANG_KE.json (tên · nguồn · sha256 · ngày · dung lượng)
④ Đối chiếu với MODEL_BOM_FINAL.csv — thiếu một tệp là dừng
```

Dùng lại `render_gateway/deploy/tai_model.py` (bản khai JSON, sha256, **tải tiếp
được**) — chạy từ máy A, **không sửa tệp đó**.

**Thứ tự nạp theo thứ tự P07 sẽ dùng**, để bắt đầu đo được sớm:
`dùng chung (11,6) → T2V (57,2) → I2V (57,2) → V2V (57,2) → Character (37,7)`

⏱️ Ước thời gian: 220,8 GB qua mạng nhà. Đây là việc **để chạy nền**, không ngồi chờ.

### P06 · Docker image — phần việc lớn nhất và chưa ai làm

Endpoint cần một **template** trỏ tới một **Docker image**. Đây là thứ ta phải tự dựng.

#### ⛔ Không dùng lại `runpod-workers/worker-comfyui`

Nó **AGPL-3.0**, và §13 của AGPL kích hoạt **qua mạng** — chạy nó thành dịch vụ
cho khách là phải chào mã nguồn. Kho này đã trả giá để hiểu khác biệt AGPL/GPL ở
Q94/Q100 (RustDesk). Và nó **chỉ xử lý ảnh** (`handler.py:842` cảnh báo rồi bỏ qua
mọi khoá khác) nên dùng cho video cũng không chạy.

⇒ **Đọc để học hình dạng, viết handler của mình.**

#### Thành phần image

```
base        nvidia/cuda hoặc pytorch chính chủ (ghim tag)
+ ComfyUI   GPL-3.0 — CHẠY thì không kích hoạt nghĩa vụ; ghim commit
+ custom node   chỉ mode Character cần (segment-anything-2 · controlnet_aux · KJNodes)
+ handler.py    MÃ CỦA TA — cửa serverless của video_gateway
+ runpod SDK
```

⚠️ **Đẩy image lên registry RIÊNG TƯ.** Đẩy công khai là **phân phối**, và lúc đó
GPL-3 của ComfyUI đòi chào mã nguồn. Registry riêng ⇒ không phân phối ⇒ không có
nghĩa vụ. RunPod nhận thông tin đăng nhập registry riêng.

#### Dựng ở đâu

Máy A là Windows. Ba đường:

| | Đường | Đánh giá |
|---|---|---|
| 1 | **Docker Desktop + WSL2 trên máy A** | WSL đã bật cho việc Nexus. Dựng cục bộ, đẩy lên registry riêng. **Đề xuất** |
| 2 | RunPod build từ GitHub | phải đẩy mã lên GitHub — kho này riêng tư, thêm một bề mặt |
| 3 | Dựng trên một Pod tạm | tốn GPU-giờ cho việc CPU làm được |

⛔ Đường 3 vi phạm chính luật của `P05`: *"không dùng A100 để làm việc mà CPU làm được"*.

#### Ba câu P06 phải trả lời bằng **một job thật**, không đoán

1. **Trần trên của `Execution timeout`** là bao nhiêu?
2. **Khởi động nguội có tính vào `Execution timeout` không**, hay chỉ vào hoá đơn?
   → Quyết định mode nào chạy được (`CLOUD_RESOURCE_PLAN.md` §2.1).
3. **Băng thông volume thật** — 200 hay 400 MB/s? Chênh gấp đôi thời gian nguội.

⭐ Cách đo rẻ nhất: một job **cố ý tầm thường** (nạp model rồi thoát, không sinh
gì). Nó trả lời cả ba câu với chi phí gần bằng một lần khởi động nguội.

4. **Subgraph.** Template T2V/I2V để 30 node thật trong `definitions.subgraphs`.
   Phải xác minh bản ComfyUI đã chọn hỗ trợ, **và** bản xuất *API format* có làm
   phẳng không — nếu không phẳng thì `workflows.py` (thay thẻ `"@ten"`) mù.

### P06-b · Tạo endpoint

```bash
POST https://rest.runpod.io/v1/endpoints
{
  "name": "lttvideo-wan22-a100",
  "templateId": "<từ bước trên>",
  "gpuTypeIds": ["NVIDIA A100 80GB PCIe"],
  "dataCenterIds": ["<DC của volume>"],
  "networkVolumeId": "<từ P04-b>",
  "workersMin": 0,
  "workersMax": 1,          ← ⛔ console mặc định 3; API bắt khai rõ
  "idleTimeout": 5,
  "flashboot": true,
  "executionTimeoutMs": <theo câu trả lời P04-a④>
}
```

**Đạt khi:** endpoint trả `RUNNING` cho một job tầm thường, và **huỷ được** bằng
`workersMax = 0`.

---

## 2b. Đặc tả API — đọc từ **OpenAPI chính chủ**, không đoán

`https://rest.runpod.io/v1/openapi.json` **công khai, không cần khoá**. Đây là
nguồn chuẩn cho mọi lời gọi dưới đây (tra 2026-09-04).

**23 đường dẫn.** Những cái ta dùng:

```
POST   /networkvolumes                   tạo ổ đĩa
PATCH  /networkvolumes/{id}              ⭐ ĐỔI DUNG LƯỢNG (name, size)
POST   /templates                        khai Docker image
POST   /endpoints                        tạo endpoint
PATCH  /endpoints/{id}                   sửa (dùng cho thoát hiểm mức 2)
DELETE /endpoints/{id}                   xoá
POST   /containerregistryauth            ⭐ khoá registry RIÊNG TƯ
GET    /billing/endpoints                ⭐ chi tiêu compute — cầu dao đọc cái này
GET    /billing/networkvolumes           chi tiêu lưu trữ
```

### 🔴 BẪY: 4 trung tâm dữ liệu có API S3 nhưng **KHÔNG host được endpoint**

Giao hai danh sách (28 DC nhận endpoint × 15 DC có API S3):

```
✅ DÙNG ĐƯỢC CẢ HAI — 11 DC:
   EU-CZ-1  EU-RO-1  EUR-IS-1  EUR-NO-1  US-CA-2  US-GA-2
   US-IL-1  US-KS-2  US-MD-1   US-NC-1   US-WA-1

⛔ CÓ S3 NHƯNG KHÔNG HOST ĐƯỢC ENDPOINT — 4 DC:
   US-MO-1   US-MO-2   US-NC-2   US-NE-1
```

**Hậu quả nếu chọn nhầm:** tạo volume ở `US-MO-1` thì **nạp model qua S3 vẫn
chạy** — đến khi tạo endpoint mới phát hiện không gắn được. Lúc đó 220 GB đã nạp
xong là **bỏ đi**: phải tạo volume mới ở DC khác, nạp lại từ đầu, và **trả tiền cả
hai** cho tới khi xoá cái cũ.

⇒ **P04-a phải chọn DC từ danh sách 11**, không phải từ danh sách 15 của trang S3.

### Tham số thật của từng lời gọi

**`POST /networkvolumes`** — `dataCenterId`* · `name`* · `size`* (**tối đa 4000 GB**)

**`PATCH /networkvolumes/{id}`** — `name` · `size` ⇒ **nới bằng API được**, không
phải vào console. (Vẫn chỉ tăng, không giảm.)

**`POST /templates`** — `name`* · `imageName`* · `isServerless` · `containerDiskInGb`
(mặc định **50**) · `containerRegistryAuthId` · `env` · `dockerStartCmd` ·
`volumeMountPath` (mặc định `/workspace` — ta để `/runpod-volume`)

**`POST /endpoints`** — `templateId`* và:

| Tham số | Mặc định | **Ta đặt** | Ghi chú |
|---|---|---|---|
| `gpuTypeIds` | — | **`["NVIDIA A100 80GB PCIe"]`** | ⭐ khớp đúng `D06`. Enum có 45 giá trị; cũng có `NVIDIA A100-SXM4-80GB` |
| `dataCenterIds` | 28 DC | **`["<DC đã chọn>"]`** | phải trùng DC của volume |
| `networkVolumeId` | — | từ P04-b | |
| `workersMax` | — | **1** | `minimum = 0` ⇒ **đặt 0 là đường dừng khẩn cấp** ✅ |
| `workersMin` | — | **0** | |
| `idleTimeout` | 5 | **5** (P08: **60**) | ⭐ `maximum = 3600` ⇒ kế hoạch gộp lô **khả thi**, xác nhận bằng spec |
| `executionTimeoutMs` | — | ⚠️ xem dưới | |
| `flashboot` | — | **true** | |
| `vcpuCount` | **2** | ⚠️ xem dưới | |
| `scalerType` | `QUEUE_DELAY` | giữ | |

⚠️ **`executionTimeoutMs` KHÔNG có `maximum` trong spec.** Tức schema không chặn —
nhưng điều đó **không** chứng minh máy chủ chấp nhận mọi giá trị. Câu hỏi
*"trần trên là bao nhiêu"* vẫn phải hỏi bằng **một lời gọi thật** ở P04-a: tạo thử
với `1800000` (30 phút) và đọc phản hồi.

⚠️ **`vcpuCount` mặc định chỉ 2.** ComfyUI video còn phải **encode video** (ffmpeg)
sau khi sinh khung hình — đó là việc CPU. Hai nhân có thể thành nút cổ chai ở
chính bước cuối. P06 đo, và nâng nếu cần (giá đã gộp trong giá giờ GPU).

### ⭐ `GET /billing/endpoints` — cầu dao và `V-003` cùng dùng nguồn này

Trả về từng dòng: `amount` · **`timeBilledMs`** · `gpuTypeId` · `endpointId` ·
`diskSpaceBilledGb` · `time`. Lọc được theo `startTime`/`endTime`/`endpointId`.

Hai chỗ cần nó, và cả hai đều **không còn phải tự đoán**:

1. **Cầu dao ngân sách** (`CLOUD_SAFETY_PLAN.md` §1⑤) — đọc `amount` cộng dồn
   trong tháng, so với envelope.
2. **`V-003` quyết toán** — `timeBilledMs` **là** `billed_seconds` mà `V-003` đòi
   ghi cho từng job. Không phải phép nhân của ta, mà là **con số ra hoá đơn**.

⭐ Đúng khuôn `credit.SettlementResult` (`provider_credit` vs `charged_credit`):
ước tính và thực tế nằm hai cột, chênh lệch **nhìn thấy được**.

---

## 3. Vận hành sau khi dựng — công cụ trên máy A

Để không phải mở console mỗi lần, dựng **một** công cụ, khuôn
`tools/api_prod_canary.py` (một lệnh, mười giây, trả lời trạng thái thật):

```powershell
python tools\may_c.py trang-thai      # số dư · endpoint · volume · chi tiêu tháng · envelope còn
python tools\may_c.py kiem-ke         # mọi tài nguyên mang tiền tố lttvideo-
python tools\may_c.py dung            # max_workers=0  (thoát hiểm mức 2)
python tools\may_c.py gia             # hỏi giá live, so với bảng đang dùng
```

⭐ Vì sao là công cụ chứ không phải một bảng chép tay: `CLAUDE.md` ghi rằng bảng
"cái gì đang sống" chép tay đã **nói sai năm lần, cả năm về phía nguy hiểm**. Câu
trả lời phải đến từ **hỏi máy chủ**, không từ trí nhớ.

---

## 4. Thứ tự chạy và chi phí từng chặng

| Chặng | Tiêu gì | GPU-giờ | Chặn bởi |
|---|---|---|---|
| P04-a kiểm trước | $0 | 0 | ① ② ③ của chủ dự án |
| P04-b tạo volume | ~$0,70/ngày | 0 | |
| P04-c cầu dao | $0 | 0 | ⛔ **hard gate** |
| P05 nạp model | $0 GPU | **0** | |
| P06 dựng image | $0 (dựng cục bộ) | 0 | |
| P06 job tầm thường | ~$0,30 | ~0,1 | |
| P06-b endpoint + dựng lại | | **3,6** | |
| P07 bốn mode | | **7,2** | |

⛔ **Envelope P06 là 3,6 giờ.** Một job tầm thường ~0,1 giờ ⇒ có chỗ cho ~30 lần
thử. Nếu image sai và phải sửa nhiều vòng thì đó là chỗ envelope cháy — nên **mọi
thứ kiểm được trên CPU phải kiểm trước khi đẩy lên**.

---

## 5. Rủi ro đã biết trước

| Rủi ro | Dấu hiệu | Xử |
|---|---|---|
| **Hết A100 ở DC đã khoá volume** | job nằm `queued` mãi, `/health` xanh | kiểm tồn kho. **Không** tự đổi DC (nạp lại 220 GB + trả lưu trữ hai lần) |
| **Subgraph không phẳng khi xuất API** | ComfyUI nhận workflow nhưng thẻ `"@ten"` không được thay | làm phẳng thủ công, ghi vào `WORKFLOW_LOCK` |
| **`Execution timeout` không nâng đủ** | job bị cắt giữa chừng | hạ độ phân giải/số khung, và ghi vào `GOLDEN_PIPELINES` như **giới hạn sản phẩm** |
| **`DownloadAndLoadSAM2Model` tự tải** | Character chậm bất thường mỗi lần nguội | đổi sang nạp từ `/runpod-volume` |
| **Số dư chạm sàn** | cầu dao ngắt compute | nạp thêm; **volume vẫn sống** — đó là mục đích của sàn |
| **Image quá to** | kéo image lâu ⇒ nguội lâu ⇒ đắt | tách custom node sang volume, hoặc bỏ mode Character khỏi image đầu |

---

## 6. Điều kiện đóng P04 *(bản đã cập nhật)*

- [ ] Chủ dự án: tài khoản · thẻ · nạp **$50** · API key vào `secrets/app.env`
- [ ] Giá hỏi lại **ngay lúc đó**, lệch < 10 %
- [ ] A100 80GB **có hàng** ở một DC thuộc 15 DC có API S3
- [ ] Volume `lttvideo-models-v1` **300 GB** tạo ở đúng DC đó
- [ ] `volumeId` + DC + thời điểm ghi vào `COST_LEDGER.csv`
- [ ] Ba phép thử dry-run cầu dao **PASS** (gồm phép thử **sàn credit**)
- [ ] Bốn loại bí mật vào đúng bốn chỗ
- [ ] ⛔ **Chưa tạo endpoint, chưa có worker GPU nào**
- [ ] ⚠️ **Auto-pay TẮT**
