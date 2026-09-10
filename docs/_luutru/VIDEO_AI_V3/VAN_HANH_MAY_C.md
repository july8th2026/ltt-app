# LOGIC VẬN HÀNH MÁY C — hệ điều hành, và cấu hình để **chỉ mất tiền khi GPU chạy**

> Tệp này trả lời hai câu hỏi của chủ dự án ngày 04/09/2026:
> *"logic vận hành ta chạy win gì linux hay loại gì"* và *"cấu hình vận hành cho
> đúng gpu sử dụng mới mất tiền"*.
>
> **Mọi con số dưới đây đọc từ nguồn chính chủ trong phiên này** — OpenAPI
> `https://rest.runpod.io/v1/openapi.json`, `docs.runpod.io/*.md`, và GraphQL
> `api.runpod.io/graphql`. Không có số nào chép lại từ trí nhớ hay từ P03.

---

## 1. Chạy hệ điều hành gì — **Linux, và không có lựa chọn khác**

| Tầng | Máy | Hệ điều hành | Vì sao |
|---|---|---|---|
| A-CONTROL | máy hiện tại | Windows 10 Pro | nền tảng đang chạy ở đó, không đổi |
| Nơi **build** image | máy A, qua WSL2 + Docker Desktop | Linux (bên trong WSL2) | Docker build cần Linux kernel |
| C-CLOUD worker | RunPod Serverless | **Linux, trong Docker container** | RunPod không có worker Windows |

Bằng chứng, không phải suy đoán:

- `docs.runpod.io/serverless/overview.md`: worker Serverless **là container Docker**.
- OpenAPI `POST /templates` chỉ nhận `imageName` (tên image Docker) và
  `category` thuộc `['NVIDIA','AMD','CPU']` — **không có trường hệ điều hành**.
- Volume mount trên Serverless là `/runpod-volume` (đường dẫn POSIX). Trên
  Pod/Cluster là `/workspace`.

⇒ **Image phải là `linux/amd64`.** Build trên Windows bằng Docker Desktop là
được, nhưng thứ đi lên registry là một image Linux. Đừng nhầm "máy build chạy
Windows" với "worker chạy Windows".

⛔ Hệ quả cho code: mọi đường dẫn trong workflow ComfyUI, mọi script khởi động,
mọi biến `MODEL_PATH` đều dùng **dấu gạch chéo xuôi** và gốc `/runpod-volume`.
Một đường dẫn kiểu ổ đĩa Windows lọt vào image là hỏng ở lượt chạy đầu, và lượt
chạy đầu **có tính tiền**.

---

## 2. RunPod thu tiền ở đúng **ba** chỗ — không hơn

Nguồn: `docs.runpod.io/serverless/pricing.md`.

| Khoản | Cách tính | Của ta |
|---|---|---|
| **Compute** | theo giây, từ lúc worker *bắt đầu khởi động* tới lúc *dừng hẳn*, làm tròn lên giây | A100 80GB = **$0,00076/giây** = $2,736/giờ |
| **Container disk** | ~**$0,10/GB/tháng**, chốt theo khoảng 5 phút | phải đặt nhỏ nhất có thể (§4) |
| **Network volume** | **$0,07/GB/tháng** dưới 1 TB | 300 GB = **$21,00/tháng** |

🔴 **Khoản "container disk" là khoản tôi đã bỏ sót ở P03.** Mặc định
`containerDiskInGb = 50` ⇒ nếu để mặc định, đó là $5/tháng nữa. Xem §4 để biết
giá trị ta đặt và vì sao.

### Bảng giá compute đầy đủ (để tính đường lui)

| Hạng GPU | VRAM | $/giây | $/giờ |
|---|---|---|---|
| A6000, A40 | 48 GB | 0,00034 | 1,224 |
| L40, L40S, 6000 Ada PRO | 48 GB | 0,00053 | 1,908 |
| **A100** | **80 GB** | **0,00076** | **2,736** |
| 6000s PRO | 96 GB | 0,00111 | 3,996 |
| H100 PRO | 80 GB | 0,00116 | 4,176 |
| H200 PRO | 141 GB | 0,00155 | 5,580 |
| B200 | 180 GB | 0,00240 | 8,640 |

⚠️ **Đừng lẫn giá này với giá Pod.** GraphQL trả về giá **Pod** (A100 PCIe
$1,19/giờ ở US-KS-2). Pod rẻ hơn mỗi giờ nhưng **chạy liên tục**; Serverless đắt
hơn mỗi giờ nhưng **về không khi rảnh**. Với nhịp dùng của ta — vài chục phút mỗi
ngày — Serverless rẻ hơn Pod nhiều lần. Giá Pod ở đây chỉ dùng làm **chỉ dấu
phần cứng có tồn tại trong DC đó hay không**, không dùng để tính ngân sách.

---

## 3. Ba giai đoạn **đều bị tính tiền** — và cái ở giữa là cái ta điều khiển được

`pricing.md` liệt kê đúng ba:

1. **Start time** — dựng container + nạp model vào VRAM.
   Với chuỗi T2V của ta là **68,78 GB** đọc từ network volume
   (`CHUOI_MODEL_VA_VAN_HANH.md`) ⇒ **172–344 giây** ⇒ **$0,13–$0,26 mỗi lần
   khởi động nguội**. Giảm bằng FlashBoot.
2. **Execution time** — chạy thật. Chặn bằng `executionTimeoutMs`.
3. **Idle timeout** — worker còn sống chờ job kế tiếp sau khi xong.
   *"You're billed during idle time, but the worker remains warm."*

### Phép tính quyết định `idleTimeout`

Giữ ấm 1 giây tốn $0,00076. Khởi động nguội lại tốn $0,13–$0,26.

⇒ Giữ ấm **có lãi** nếu job kế tiếp tới trong vòng **171–342 giây**.

| `idleTimeout` | Chi phí xấu nhất mỗi đợt | Nhận xét |
|---|---|---|
| 5 (mặc định) | $0,0038 | mọi job đều trả khởi động nguội |
| **60** | **$0,046** | **chọn cái này cho V1** |
| 300 | $0,228 | bằng đúng một lần khởi động nguội — không còn lãi |

**Chốt `idleTimeout = 60`.** Rẻ hơn một lần nạp lại model tới ~5 lần, mà vẫn bắt
được cả một loạt job liên tiếp — đúng nhịp làm việc của một nhà sản xuất video
(dựng nhiều cảnh liền nhau). Đo lại ở P07 rồi chỉnh.

---

## 4. Cấu hình endpoint — từng tham số, giá trị của ta, và **vì sao**

Trích từ OpenAPI `POST /endpoints`. Cột "nguồn" cho biết ràng buộc đọc ở đâu.

| Tham số | Giá trị | Vì sao | Nguồn |
|---|---|---|---|
| `computeType` | `GPU` | | mặc định |
| `workersMin` | **0** | 🔑 **Đây là tham số quyết định "chỉ mất tiền khi dùng".** OpenAPI nói thẳng: worker `min` *"will be charged even if no requests are being processed"*. Đặt 0 ⇒ không có worker nào tồn tại khi không có job ⇒ **$0**. | OpenAPI |
| `workersMax` | **1** | trần cứng. Một worker không thể tiêu quá $2,736/giờ. Đây là lớp chặn ② của `CLOUD_SAFETY_PLAN`. | OpenAPI (`minimum: 0`) |
| `idleTimeout` | **60** | §3 | OpenAPI (`min 1, max 3600`) |
| `executionTimeoutMs` | **1 800 000** (30 phút) | job treo bị giết, không tiêu tới hết TTL 24 giờ | dải hợp lệ 5 giây – 7 ngày |
| `flashboot` | `true` | cắt start time, mà start time là khoản đắt thứ hai của ta | `endpoint-configurations.md` |
| `scalerType` | `QUEUE_DELAY` | mặc định | OpenAPI |
| `scalerValue` | **4** | mặc định; với `workersMax=1` tham số này gần như vô nghĩa | OpenAPI |
| `gpuTypeIds` | `["NVIDIA A100 80GB PCIe", "NVIDIA H100 NVL"]` | ưu tiên theo thứ tự. Dưới 5 worker, RunPod **luôn lấy loại ưu tiên cao nhất còn hàng** ⇒ H100 chỉ dùng khi A100 hết. | `endpoint-configurations.md` |
| `gpuCount` | **1** | Wan2.2 A14B vừa trong 80 GB; 2 GPU là nhân đôi tiền không nhân đôi tốc độ | |
| `dataCenterIds` | `["US-KS-2"]` | phải trùng DC của volume, xem §6 | |
| `networkVolumeId` | `<từ P04-b>` | | |
| `minCudaVersion` | **`12.8`** — đã đặt 05/09 | 🔴 **ĐỔI từ `12.4`.** Lý lẽ cũ (*"đặt thấp để không tự loại bớt máy"*) chết cùng `V-013`: danh sách GPU giờ chỉ có H100. Và chỉ mục `cu124` **dừng ở torch 2.6.0** trong khi `extended_fp16_support()` đòi `>= 2.7` ⇒ pin thấp là **tắt fp16 mở rộng**, trái `V-012`. Ảnh nền giờ là `nvidia/cuda:12.8.1`, nên driver máy chủ cũng phải ≥ 12.8 — đặt thấp hơn là tự cho phép rơi vào máy không chạy được, **trên GPU đang tính tiền**. | enum có `12.8`; `tools/video_ra_soat.py cham` hạng mục ③b canh |
| `templateId` | `<từ P06>` | **trường bắt buộc duy nhất** của `POST /endpoints` | OpenAPI |

### Tham số template (`POST /templates`)

| Tham số | Giá trị | Vì sao |
|---|---|---|
| `isServerless` | **`true`** | mặc định là `false` — quên trường này là tạo nhầm template Pod |
| `imageName` | `<registry riêng>/lttvideo-worker:<tag>` | |
| `containerDiskInGb` | **20** | model nằm trên network volume, container chỉ chứa ComfyUI + torch. Mặc định 50 ⇒ thừa 30 GB × $0,10 = **$3/tháng vứt đi**. |
| `containerRegistryAuthId` | `<từ P06>` | image riêng tư |
| `env` | khoá S3 + `LTT_*` | 🔒 không chứa mật khẩu CSDL, không chứa khoá cha R2 |
| `ports` | `[]` | Serverless không cần cổng mở; mặc định `8888/http,22/tcp` là của Pod |
| `volumeMountPath` | `/runpod-volume` | đường dẫn Serverless |

---

## 5. Cái **không** mất tiền — để khỏi sợ nhầm chỗ

| Việc | Có tính tiền? |
|---|---|
| Tạo template | **Không** |
| Tạo endpoint với `workersMin=0` và không gửi job | **Không** |
| Gọi `GET /endpoints`, `GET /billing/*`, GraphQL | **Không** |
| Đẩy 220 GB model lên volume qua S3 API | **Không tính compute** — chỉ tính chỗ chứa. Đây là lý do P05 nạp model **trước khi** có endpoint. |
| Volume nằm im | **Có** — $21/tháng, tính theo giờ, ~$0,70/ngày |

⇒ Sau khi dựng xong, hoá đơn ở trạng thái nghỉ là **đúng $21/tháng**. Mọi đồng
vượt qua con số đó đều là GPU đã thực sự quay.

---

## 6. 🔴 Chọn trung tâm dữ liệu — **đo, không đoán**

`dataCenterId` của volume là **tham số duy nhất không sửa được**. Ba ràng buộc
phải cùng thoả:

1. DC có **API S3** (để P05 nạp model mà không cần GPU) — 15 DC, `storage/s3-api.md`
2. DC **host được Serverless** — 28 DC, đọc từ `default` của `dataCenterIds` trong OpenAPI
3. DC **thực sự có GPU từ 80 GB**

Giao của (1) và (2) = **11 DC**: `EU-CZ-1 EU-RO-1 EUR-IS-1 EUR-NO-1 US-CA-2
US-GA-2 US-IL-1 US-KS-2 US-MD-1 US-NC-1 US-WA-1`.

Bốn DC có S3 nhưng **không** host Serverless — `US-MO-1 US-MO-2 US-NC-2 US-NE-1`
— là bẫy: trang S3 liệt kê chúng, và không có gì báo lỗi cho tới khi tạo endpoint.

### Đo (3): quét 11 DC × 8 loại GPU ≥ 80 GB, GraphQL, 04/09/2026

Giá dưới đây là **giá Pod**, dùng làm chỉ dấu phần cứng tồn tại. `-` = không có.

| DC | A100 PCIe | A100 SXM4 | H100 HBM3 | H100 NVL | H200 | 6000 PRO | B200 |
|---|---|---|---|---|---|---|---|
| EU-CZ-1 | - | - | - | - | - | Low $1,69 | - |
| EU-RO-1 | - | - | - | - | - | - | Low $5,98 |
| EUR-IS-1 | - | Low $1,39 | - | - | - | Low $1,69 | - |
| EUR-NO-1 | - | - | - | - | - | - | - |
| US-CA-2 | - | - | Low $2,69 | Low $2,59 | Low $3,59 | - | Low $5,98 |
| US-GA-2 | - | - | Low $2,69 | Low $2,59 | Low $3,59 | - | - |
| US-IL-1 | - | - | - | - | - | - | - |
| **US-KS-2** | **Low $1,19** | - | - | Low $2,59 | - | - | - |
| US-MD-1 | - | Low $1,39 | - | - | - | - | - |
| US-NC-1 | - | - | - | - | Low $3,59 | - | - |
| US-WA-1 | - | - | - | - | - | - | - |

**Ba DC trong danh sách 11 không có một GPU ≥ 80 GB nào** — `EUR-NO-1`,
`US-IL-1`, `US-WA-1`. Nếu chọn theo cảm giác thì xác suất trúng một trong ba là
27 %, và cái giá của việc trúng là nạp lại 220 GB.

### ✅ Chốt: **US-KS-2**

| Tiêu chí | US-KS-2 |
|---|---|
| API S3 | `https://s3api-us-ks-2.runpod.io/` ✓ |
| Host Serverless | ✓ (có trong danh sách 28) |
| GPU đã chốt (A100 80GB) | ✓ — **DC duy nhất trong 11 có A100 80GB PCIe** |
| Đường lui trong cùng DC | ✓ H100 NVL 94 GB |
| Giá | hạng rẻ nhất trong các hạng ≥ 80 GB |

US-CA-2 có nhiều lựa chọn hơn (4 loại) nhưng **không có A100** — hạng rẻ nhất ở
đó là $0,00111–0,00116/giây, đắt hơn **46–53 %**. Với mục tiêu đã chốt của chủ
dự án là *tối giản chi phí đầu tư lâu dài* (`D01`), US-KS-2 thắng.

⚠️ **Giới hạn của phép đo này, nói thẳng:** GraphQL `lowestPrice` phản ánh kho
**Pod**, không phải kho **Serverless**. RunPod không mở API nào cho kho
Serverless theo DC. Vì thế trước khi nạp 220 GB, phải chạy **một lượt khói** bằng
image công khai bé để chứng minh worker A100 thật sự dựng được ở US-KS-2. Lượt đó
tốn vài xu và tránh cho ta mất một buổi nạp lại.

---

## 7. 🔴 Bẫy mới phát hiện — endpoint tự co lại khi để không

`endpoint-configurations.md`, mục *idle endpoint scale-down*:

| Không có request trong | Hậu quả |
|---|---|
| **3 ngày** | `workersMax` bị hạ xuống **2** (có email báo) |
| **7 ngày** | `workersMax` bị hạ xuống **0** — endpoint **ngừng nhận job** |

Và nó **không tự hồi phục** — phải vào nâng tay lại.

⇒ Với `workersMax = 1` của ta, mốc 3 ngày vô hại (1 < 2), nhưng **mốc 7 ngày là
sự cố im lặng**: người dùng đặt job, job vào hàng đợi, không bao giờ chạy, và
không có lỗi nào.

**Cách chặn:** `manifest.bao_tri` của app `lttvideo` chạy dưới lease
(`platform_core/leases.py`) mỗi ngày, `GET /endpoints/{id}`, nếu `workersMax == 0`
thì `POST /endpoints/{id}/update` đặt lại 1 và ghi cảnh báo. Đây là việc của
P06-b, ghi vào đây để P06 không phải tìm lại.

---

## 8. Đồng hồ đo — `GET /billing/endpoints` là **nguồn chân lý duy nhất** về tiền

OpenAPI trả về mảng, mỗi phần tử:

| Trường | Nghĩa |
|---|---|
| `amount` | số USD đã tính, cho nhóm và kỳ đó |
| `timeBilledMs` | tổng thời gian đã tính tiền, mili-giây |
| `time` | đầu kỳ |
| `endpointId` / `gpuTypeId` / `podId` | khoá nhóm, tuỳ `grouping` |

Tham số truy vấn: `startTime`, `endTime`, `bucketSize`, `grouping`, `endpointId`,
`dataCenterId`, `gpuTypeId`, `templateId`, `imageName`.

⇒ Cầu dao ngân sách (`CLOUD_SAFETY_PLAN` §⑤) và giá vốn mỗi video (`V-003`)
**cùng đọc từ đây**, không đọc từ hai nơi khác nhau. Một nguồn thì không có
chuyện hai con số cãi nhau.

`GET /billing/networkvolumes` cho khoản cố định, tách riêng
`highPerformanceStorageAmount` — của ta luôn bằng 0 vì dùng standard storage.

### Giá lưu trữ — xác nhận live 04/09/2026 trên chính giao diện RunPod

> Standard storage — **$0,07/GB/tháng cho 1 TB đầu**, sau đó $0,05
> High performance storage — $0,14/GB/tháng

300 GB standard = **$21,00/tháng**, đúng bằng con số P03 đã dự toán. Bản high
performance nhanh gấp ~3 lần nhưng $42/tháng; ta không mua vì băng thông chỉ ảnh
hưởng **start time**, mà start time đã có FlashBoot xử lý.

---

## 9. Toàn bộ bề mặt REST API — 23 đường dẫn, không hơn

Đọc từ `https://rest.runpod.io/v1/openapi.json`. Ghi ra đây để phiên sau không
phải đoán tên đường dẫn (`/v1/datacenters` và `/v1/gputypes` **không tồn tại** —
đã thử, trả HTTP 400).

```
/billing/endpoints          GET
/billing/networkvolumes     GET
/billing/pods               GET
/containerregistryauth      GET POST      + /{id} GET DELETE
/endpoints                  GET POST      + /{id} GET PATCH DELETE  + /{id}/update POST
/networkvolumes             GET POST      + /{id} GET PATCH DELETE  + /{id}/update POST
/pods                       GET POST      + /{id} GET PATCH DELETE  + start/stop/restart/reset/update POST
/templates                  GET POST      + /{id} GET PATCH DELETE  + /{id}/update POST
/docs  /openapi.json        GET
```

`POST /networkvolumes` chỉ nhận đúng ba trường — `name`, `size` (0–4000 GB),
`dataCenterId` — **không có trường chọn standard hay high performance**, nên
volume tạo qua REST luôn là standard. Đúng cái ta muốn.

⚠️ GraphQL introspection **đã tắt**; muốn biết trường nào có thì phải thử.
Nhưng khoá API phạm vi `graphql` vẫn gọi được `rest.runpod.io/v1` — đã kiểm.

---

## 10. Trạng thái tài khoản tại thời điểm viết

| Mục | Giá trị |
|---|---|
| Số dư | $50,00 |
| Auto-Pay | **Disabled** (lớp chặn ① — cố ý giữ nguyên) |
| Trần chi tiêu mặc định của RunPod | $80/giờ trên toàn tài khoản |
| Network volume đang có | **0** (`GET /v1/networkvolumes` trả `[]`) |
| Endpoint đang có | 0 |
| Đã tiêu cho cloud | **$0** |
