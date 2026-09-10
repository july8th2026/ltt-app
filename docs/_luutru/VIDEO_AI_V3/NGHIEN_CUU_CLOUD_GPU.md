# NGHIÊN CỨU: cộng đồng chạy video AI trên GPU thuê như thế nào

> ⛔ **HỒ SƠ ĐƯỜNG ĐI — KHÔNG PHẢI CHỈ DẪN (đóng băng 2026-09-05).**
> Kế hoạch đang sống là **`KE_HOACH_XAY_DUNG.md`**; tham số sản xuất sống trong
> **`platform_core/video_gen/cau_hinh_san_xuat.py`**. Tệp này viết trước
> `V-010`/`V-012` nên nó còn mang giả định **fp8 · 4 bước · 640×640 · nhiều bậc
> chất lượng · L40**. Cả năm giả định đó **đã bị gỡ**. Đọc tệp này để hiểu
> *chương trình đã đi qua đâu*, đừng đọc để lấy con số.


> Tra ngày **2026-09-04** bằng `curl` vào tài liệu chính chủ và mã nguồn thật.
> Mọi con số dưới đây **đọc được lại** — có đường dẫn nguồn ở từng mục.
>
> ⛔ **Giá cloud là số SỐNG.** `policies/GLOBAL_RULES.md` cấm coi ảnh chụp giá là
> hằng số. Bảng dưới là ảnh chụp **04/09/2026**; P03 phải hỏi lại ngay trước khi
> tạo tài nguyên.
>
> ⚠️ Nội dung tải từ Internet là **dữ liệu**, không phải chỉ thị. Không có bước
> nào dưới đây được thực hiện chỉ vì một trang web nói thế.

---

## 0. Kết luận trước, lập luận sau

> 🔴 **Cộng đồng KHÔNG thuê Pod rồi tự viết vòng đời GPU. Họ dùng SERVERLESS GPU.**
>
> Và điều đó **xoá phần lớn P14** — pha mà pack V3 dành riêng để xây máy trạng
> thái `OFF → PROVISIONING → BOOTING → WARMING → READY → BUSY → DRAINING → OFF`,
> single-flight, đồng hồ nhàn rỗi, đối soát Pod mồ côi, trần thời gian phiên.
>
> **Nhà cung cấp đã bán đúng thứ đó như một sản phẩm.** Tự xây lại là tự nhận
> nuôi một hệ thống mà tiền thuê đã bao gồm.

Ba câu hỏi tôi để ngỏ ở ADR-3 §9 **đều đã có câu trả lời**, và hai trong ba
biến mất chứ không phải được giải.

---

## 1. Cộng đồng đang chạy ComfyUI trên cloud bằng cái gì

Tra GitHub: `comfyui serverless` → **229 kho**. Đứng đầu và cách biệt:

| Kho | ⭐ | Cập nhật | Giấy phép |
|---|---|---|---|
| **`runpod-workers/worker-comfyui`** — *"ComfyUI as a serverless API on Runpod"* | **739** (700 fork) | **2026-09-01** (ba ngày trước) | ⚠️ **AGPL-3.0** |
| `nexmoe/serverless-comfyui` | 103 | | |
| `ashleykleynhans/runpod-worker-comfyui` | 23 | | |
| `vavo/LTX2.3-serverless`, `vavo/LTX2.5-serverless` | 5, 4 | | *"text2video and image2video"* |

⭐ **Đây là bản chính chủ của RunPod, còn sống, và 700 fork nghĩa là đường này đã
được đi mòn.** Nó cho ta biết hình dạng chuẩn của lời giải — kể cả khi ta không
dùng lại mã của nó.

⚠️ **Và nó cho biết một chỗ hụt quan trọng:** đọc `handler.py` (37 KB) thì worker
chính chủ **chỉ xử lý ảnh**. Dòng 842:

```python
other_keys = [k for k in node_output.keys() if k != "images"]
if other_keys:
    warn_msg = f"Node {node_id} produced unhandled output keys: {other_keys}."
```

Nó **cảnh báo rồi bỏ qua** mọi khoá khác. ⇒ Dùng nó cho video là không chạy —
ta vẫn phải viết handler riêng. Cộng thêm **AGPL-3.0**: kho này đã có tiền lệ xử
lý AGPL (Q94/Q100 với RustDesk), nên nếu chép mã của nó thì phải qua đúng cổng
giấy phép đó. **Đề xuất: đọc để học hình dạng, viết mã của mình.**

---

## 2. Serverless vs Pod — và vì sao nó đổi kiến trúc

### Hợp đồng serverless của RunPod (đọc từ README chính chủ)

```
POST https://api.runpod.ai/v2/<endpoint_id>/run       → async, trả job id
GET  https://api.runpod.ai/v2/<endpoint_id>/status/<id>
POST https://api.runpod.ai/v2/<endpoint_id>/runsync   → đồng bộ
     Authorization: Bearer <api_key>
     + webhook báo xong (không phải poll)
```

⭐ **Hình dạng này TRÙNG KHÍT với thứ nền tảng đã có**: async submit → poll/webhook
→ kết quả. Đúng khuôn `apps/taovideo/jobs.py` đang chạy với ModelArk, và đúng
khuôn `cong_render.py` đang chạy với máy B.

### Tính tiền (docs.runpod.io/serverless/pricing)

> *"pay-per-second pricing… billed from when a worker starts until it fully
> stops, rounded up to the nearest second."*

Ba khoản được tính, và tài liệu **nói thẳng ra cả ba**:

| Khoản | Nội dung |
|---|---|
| **Start time** | khởi tạo container + nạp model vào VRAM |
| **Execution time** | chạy thật |
| **Idle timeout** | worker còn sống chờ việc tiếp sau khi xong — **mặc định 5 giây** |

Hai loại worker: **Flex** (scale về 0 khi rảnh) và **Active** (chạy 24/7, có
chiết khấu).

🔑 **Đây chính là lời giải cho chỗ mơ hồ của `V-003`.** Câu hỏi *"Pod bật 20 phút
để chạy 3 phút video thì 17 phút tính vào đâu"* — với serverless thì **17 phút đó
không tồn tại**: nhàn rỗi mặc định 5 giây rồi về 0. Khoản ② (phần khởi động phân
bổ) không còn là một ước lượng, nó là **một dòng trên hoá đơn**.

### Điểm hoà vốn — số thật, không phải cảm giác

| | Pod (on-demand) | Serverless |
|---|---|---|
| A100 PCIe/SXM 80GB | **$1,39–1,59/hr** | **$2,72/hr** |
| 48GB (A6000 / A40) | **$0,44–0,53/hr** | **$1,22/hr** |
| 48GB (L40S / 6000 Ada) | $0,82–0,99/hr | $1,75/hr |
| 24GB (3090 / 4090) | $0,50 / $0,74/hr | $0,69 / $1,10/hr |

Serverless đắt hơn ~**2×** mỗi giờ **chạy**, nhưng chỉ tính giây **thật sự chạy**.

```
A100:  Pod rẻ hơn khi mức sử dụng > 1,39 / 2,72 = 51 %
48GB:  Pod rẻ hơn khi mức sử dụng > 0,44 / 1,22 = 36 %
```

⇒ **V1 (nội bộ, việc theo đợt) sẽ ở rất xa dưới ngưỡng đó** — serverless thắng
rõ. Nhưng ⭐ nếu `V-001③` thành sự thật (gộp lô, chủ dự án tự xếp lịch, tải dày)
thì **Pod thắng lại**. Đó không phải mâu thuẫn — nó là lý do kiến trúc phải để
việc đổi giữa hai đường là **cấu hình**, không phải viết lại (xem §6).

### Chi phí khởi động — đo được, và nó biện minh cho việc gộp lô

Network volume: **NVMe 200–400 MB/s** (đỉnh 10 GB/s) — docs.runpod.io.

```
Model video ~30 GB  →  75–150 giây chỉ để đọc từ volume
Ở serverless A100 ($2,72/hr = $0,000756/giây):  150 s ≈ $0,11 mỗi lần khởi động nguội
Một video 3 phút chạy thật:                     180 s ≈ $0,136
```

⇒ **Một video chạy lẻ tốn gần GẤP ĐÔI một video chạy trong lô.** Đây là con số
biến `V-001③` từ một nhận xét thành một chính sách vận hành có tiền đằng sau,
và nó là đầu vào trực tiếp cho `giá_vốn_chuẩn` của `V-003`.

RunPod có **FlashBoot** và model caching để giảm khoản này — P07/P08 phải đo thật.

---

## 3. Ba câu hỏi của ADR-3 §9 — đã có câu trả lời

### ① Cổng C-CLOUD tự xác thực bằng gì trên Internet? → **CÂU HỎI BIẾN MẤT**

Với serverless, **ta không mở cổng nào ra Internet cả.** Cửa trước là
`api.runpod.ai/v2/<endpoint_id>` với `Authorization: Bearer <api_key>` — hạ tầng
của nhà cung cấp, có TLS, có xác thực, không phải thứ ta phải tự bảo vệ.

⭐ Và khoá đó **rơi đúng vào cơ chế đã có**: một khoá API của một provider ⇒ cất
trong **APIKEYS** dưới provider `ltt_video`, category `video` — y hệt token cổng
render của máy B (Q102). Không cần mTLS, không cần IP allowlist, không cần
Cloudflare Tunnel thứ hai.

⛔ Không còn lý do gì để cân nhắc phơi một cổng của ta ra Internet ở V1.

### ② Video ra R2 — một phát hay multipart? → **MỘT PHÁT LÀ ĐỦ**

Đọc `developers.cloudflare.com/r2/platform/limits/`:

| | |
|---|---|
| Kích thước một đối tượng | **5 TiB** |
| **Tải lên một-phần (single-part)** | **5 GiB** |
| Multipart | 4,995 TiB / tối đa 10.000 phần |

⇒ Mọi video V1 nằm **rất xa** dưới 5 GiB ⇒ **presigned PUT một phát là đủ**,
không cần multipart. Đúng cơ chế `storage.try_put_url()` đang chạy.

⚠️ Nhưng yêu cầu thật **không phải multipart, mà là CHẢY DÒNG**: `storage_io.py`
của cổng ảnh giữ trọn tệp trong RAM (`day_ket_qua(anh: list[bytes])`), và
`comfy.download()` cũng `buf.extend`. Với video vài trăm MB × nhiều worker thì đó
là chỗ vỡ. Bản video phải đọc/ghi theo dòng.

⚠️ **Đoạn về khoá S3 ở đây ĐÃ THAY bởi `V-007`** (chủ dự án chốt cùng ngày).
Worker chính chủ của RunPod giữ khoá S3 trong biến môi trường
(`BUCKET_ENDPOINT_URL` → `rp_upload.upload_image`); bản đầu của tài liệu này gọi
đó là **vi phạm Q102** và đề xuất dùng presigned PUT.

**Nay: C-CLOUD ĐƯỢC giữ credential** — nhưng theo hình dạng an toàn hơn cả hai
đường trên: **temporary credentials của R2**, giới hạn tiền tố
`lttvideo/<user>/<job_id>/`, có `ttlSeconds`, thu hồi được dây chuyền (§6b).
Nó rẻ hơn presigned PUT về mặt viết mã *và* nhỏ hơn khoá tài khoản về bán kính
thiệt hại. Xem `DECISIONS.md` V-007.

### ③ `videos_of()` đọc khoá nào trong `outputs`? → **ĐỌC ĐƯỢC TỪ MÃ, HAI KHOÁ**

Không đoán — đọc thẳng mã nguồn:

| Node | Khoá trong `outputs[node_id]` | Nguồn |
|---|---|---|
| ComfyUI **lõi**: `SaveVideo`, `SaveWEBM` | **`"images"`** kèm **`"animated": (True,)`** | `comfy_api/latest/_ui.py:437` — `PreviewVideo.as_dict()` trả `{"images": self.values, "animated": (True,)}` |
| **VideoHelperSuite** `VHS_VideoCombine` | **`"gifs"`** | `videohelpersuite/nodes.py:634` — `return {"ui": {"gifs": [preview]}, ...}` |

⭐ Hai hệ quả cụ thể:

1. Node **lõi** đặt video dưới khoá `"images"` ⇒ `comfy.images_of()` hiện tại sẽ
   **tìm thấy** tệp video, nhưng phần còn lại của đường ảnh (`content_type`,
   `_MAGIC`, đuôi `.png`) sẽ sai. Đây là kiểu hỏng **im lặng đến tận cuối** —
   đúng lớp lỗi mà `render_gateway` đầy chú thích cảnh báo.
2. Chọn node lưu **là một quyết định hợp đồng**, không phải chi tiết workflow:
   nó quyết định khoá đầu ra. `WORKFLOW_LOCK.json` của P05 phải ghi rõ node nào.

---

## 4. Chọn nhà cung cấp nào

Bảng dưới là **serverless / trả theo giây** — mặt hàng ta cần. Ảnh chụp 04/09/2026.

| Nhà cung cấp | A100 80GB | 48GB | 24GB | Tính CPU/RAM riêng? | Ghi chú |
|---|---|---|---|---|---|
| **RunPod Serverless** | **$2,72/hr** | **$1,22/hr** (A6000/A40)<br>$1,75 (L40S) | $0,69–1,10 | ❌ **đã gộp** | volume $0,07/GB/tháng |
| **Modal** | $2,50/hr | $1,95/hr (L40S) | $0,80 (L4) | ✅ **có tính thêm** | volume 1 TiB **miễn phí**; **$30/tháng credit miễn phí** |
| **Replicate** | $5,04/hr | $3,51/hr (L40S) | — | | ~2× — là chợ model, không phải compute thô |
| **fal.ai** | — (H100 $4,50) | — | — | | như trên |

**Modal trông rẻ hơn nhưng không hẳn.** Giá niêm yết của Modal **chưa gồm** CPU
và RAM (`$0,0000131/lõi/giây` + `$0,00000222/GiB/giây`). Một container A100 với
8 lõi + 64 GiB cộng thêm ≈ **$0,89/hr** ⇒ thực tế **≈ $3,39/hr**, **đắt hơn**
RunPod. ComfyUI video cần RAM thật, nên khoản này không bỏ qua được.

### Đề xuất: **RunPod Serverless**, và lý do không phải "vì D05 đã chốt"

1. ⭐ **Có bậc 48GB giá $1,22/hr** — Modal không có (rẻ nhất 48GB là L40S $1,95).
   Nếu pipeline vừa 48GB thì đây là **đòn bẩy chi phí lớn nhất trong cả dự án**:
   `$2,72 → $1,22` là **2,23×**, tức ngân sách $150 đi từ **55 giờ → 123 giờ**.
2. **Giá đã gộp CPU/RAM** — không có hoá đơn phụ bất ngờ.
3. **Có worker ComfyUI chính chủ còn sống** (739⭐, cập nhật ba ngày trước) — kể
   cả khi ta viết mã riêng, có một bản tham chiếu đang chạy thật là rất khác với
   tự mò.
4. **Network volume + API S3** cho preload không GPU (§5).
5. Hợp **D05** — nhưng đây là lý do thứ năm, không phải thứ nhất.

**Modal là phương án hai nghiêm túc**: `$30/tháng credit miễn phí` + `1 TiB volume
miễn phí` đáng kể trên ngân sách $150, và trải nghiệm lập trình sạch hơn. Nhược:
không có bậc 48GB rẻ, tính CPU/RAM riêng, và mô hình "hàm Python" hợp với inference
thuần hơn là với "chạy một máy chủ ComfyUI".

**Replicate / fal.ai: không dùng làm hạ tầng.** Chúng là chợ model — dùng chúng
là **thêm một Seedance nữa**, đúng thứ `V-001` muốn thoát khỏi. ⭐ Nhưng chúng có
một vai trò thật: **làm mốc so giá cho cổng GO/NO-GO của `V-003`**.

**Vast.ai / Salad / TensorDock:** compute thô rẻ nhất nhưng không có vòng đời
serverless và độ tin cậy kiểu cộng đồng/ngắt được. Là đòn bẩy giảm giá **sau** khi
đã chạy ổn, không phải lựa chọn V1.

---

## 5. Preload model không cần GPU — đã xác nhận, không còn là hy vọng

P05 của pack đặt điều kiện *"nếu provider hỗ trợ đường preload"*. **Có.**
docs.runpod.io/storage/s3-api nói thẳng:

> *"Runpod provides an S3-protocol compatible API for direct access to your
> network volumes. This allows you to manage files on your network volumes
> **without launching a Pod**, reducing cost and operational friction. Using the
> S3-compatible API does not affect pricing."*

⇒ Đẩy toàn bộ BOM model lên bằng công cụ S3 chuẩn, **không đốt một giây GPU nào**.
Và `render_gateway/deploy/tai_model.py` (tải theo bản khai + `BANG_KE.json` sha256,
tải tiếp được) là thứ ta đã có để sinh ra bản kê đó.

⚠️ **Hai ràng buộc phải cộng vào lúc chọn trung tâm dữ liệu ở P03/P04:**

1. *"Attaching a single network volume **constrains worker deployments to that
   volume's datacenter**, which may limit GPU availability."* Giảm thiểu bằng
   nhiều volume ở nhiều DC — nhưng **dữ liệu không tự đồng bộ** giữa chúng.
2. *"The S3-compatible API is available for network volumes in **select
   datacenters**."*

⇒ DC phải thoả **ba** điều cùng lúc: có GPU ta cần · có API S3 · chịu được rủi ro
một-DC. Đây là một ràng buộc P00/pack chưa hề nêu.

---

## 6. Hệ quả lên kiến trúc — ADR-3 giữ phán quyết, đổi hình dạng

**Không đổi:** không sửa `render_gateway`; app `lttvideo`; provider `ltt_video`;
adapter `platform_core/video_gen/`; ranh giới tin cậy Q102 (presigned GET/PUT).

**Đổi — và đây là chỗ nghiên cứu này trả tiền cho chính nó:**

| | ADR-3 v2 (hôm qua) | v3 sau nghiên cứu |
|---|---|---|
| Hình dạng C-CLOUD | Pod thuê dài, ta tự quản vòng đời | **Serverless endpoint**, nhà cung cấp quản |
| `video_gateway` | dịch vụ FastAPI nghe cổng | **lõi + HAI cửa vào**: một handler serverless, một `main.py` chạy như dịch vụ |
| P14 vòng đời GPU | máy trạng thái 8 trạng thái, single-flight, đối soát mồ côi | **phần lớn XOÁ** — còn lại: trần chi tiêu, ghi `billed_seconds`, chính sách gộp lô |
| Xác thực | câu hỏi mở (mTLS? IP allowlist?) | **khoá API của nhà cung cấp, cất trong APIKEYS** |
| Đưa media vào | chưa rõ | **presigned GET** (bắt buộc: `/run` giới hạn **10 MB**, `/runsync` **20 MB** ⇒ base64 không đủ cho video) |

### ⭐ "Một lõi, hai cửa vào" — và vì sao nó gần như miễn phí

Viết phần nghiệp vụ của `video_gateway` như một thư viện thuần, rồi bọc **hai**
lớp mỏng:

```
video_gateway/loi.py        nhận việc → dựng workflow → ComfyUI → lấy kết quả → PUT
video_gateway/handler.py    cửa SERVERLESS: {"input": {...}} → loi.chay(...)
video_gateway/main.py       cửa DỊCH VỤ:   FastAPI /v1/videos/generations → loi.chay(...)
```

Được ba thứ, không mất gì:

1. **V1 chạy serverless** (rẻ nhất khi tải thưa).
2. **Khi tải dày vượt ngưỡng hoà vốn 36–51 %** (§2) thì bật cửa dịch vụ trên một
   Pod — **không viết lại**.
3. **Nếu sau này mua card về chạy tại nhà** thì vẫn là cửa dịch vụ đó. Đúng thứ
   `V-005②` cần: *chạy ở đâu* là quyết định **triển khai**.

---

## 6b. Bổ sung sau khi chủ dự án chốt model (2026-09-04)

### Wan2.2 cần bao nhiêu VRAM — đọc README chính chủ

`github.com/Wan-Video/Wan2.2/README.md`:

| Lệnh | Yêu cầu |
|---|---|
| `--task t2v-A14B --size 1280*720` | *"at least **80GB VRAM**"* |
| `--task i2v-A14B --size 1280*720` | *"at least **80GB VRAM**"* |
| `--task s2v-14B --size 1024*704` | *"at least **80GB VRAM**"* |
| `--task ti2v-5B --size 1280*704` | *"at least **24GB VRAM** (e.g, RTX 4090)"* |

🔴 **80GB đó ĐÃ KÈM tiết kiệm bộ nhớ** — cả ba lệnh đều chạy với
`--offload_model True --convert_model_dtype`. Nó không phải mức "chạy thoải mái",
nó là mức **đã nén rồi**.

A14B là MoE hai chuyên gia, tổng **27B tham số** / 14B hoạt động mỗi bước — đây là
bậc chất lượng. TI2V-5B là bậc nén cao.

⇒ **Đòn bẩy 48GB (2,23×) mà §4 nêu KHÔNG TỒN TẠI với model này.** Ngân sách thực:

```
$150/tháng ÷ $2,72/giờ (RunPod serverless A100 80GB) = ~55 giờ GPU/tháng
```

⏳ DiffSynth-Studio (README Wan2.2 tự nhắc) có *"low-GPU-memory layer-by-layer
offload, FP8 quantization"*, và ComfyUI có bản fp8 của A14B. Đó là đường giảm giá
**cho P08/P09**, sau khi P07 đã có trần chất lượng bằng bản bf16 không nén.

### R2 temporary credentials — cách đúng để worker cầm khoá

`developers.cloudflare.com/r2/api/s3/temporary-credentials/` — bốn tính chất dùng được:

- **`ttlSeconds`**: *"A credential that lives for 15 minutes has a smaller blast
  radius than one that lives for a day."*
- **Giới hạn theo đường dẫn**: *"Set paths and permission scope so the credential
  can only do what the caller needs."*
- **Thu hồi dây chuyền**: *"If you revoke the parent API token, all temporary
  credentials derived from it stop working immediately."*
- Không gửi token cha đi: *"Local signing must happen in a trusted environment
  (such as your backend)."*

⇒ Dùng ở `V-007`: máy A sinh credential giới hạn tiền tố `lttvideo/<user>/<job_id>/`,
TTL bằng trần thời gian job. **Rẻ hơn presigned PUT về mặt viết mã** (một lời gọi
thay vì N vé) mà bán kính thiệt hại vẫn nhỏ.

---

## 7. Cái nghiên cứu này **chưa** trả lời

Trung thực về giới hạn — cả bốn đều cần đo thật, không tra được:

1. ~~Pipeline nào vừa 48GB~~ — **ĐÃ ĐÓNG** bởi `V-008`: Wan2.2 A14B đòi ≥80GB
   ngay cả khi đã offload (§6b). Không còn đòn bẩy này. **A100 80GB đã chốt.**
2. **Cold start thật với model video ~30 GB.** Ước 75–150 s từ băng thông công bố;
   FlashBoot có thể đổi hẳn con số. P06/P07 đo.
3. **Trần thời gian thực thi của serverless với job video dài.** Có cấu hình
   `execution timeout`, nhưng giới hạn cứng thì phải đọc lại lúc P04.
4. **Giá 04/09/2026 sẽ cũ.** P03 hỏi lại trước khi tạo bất kỳ tài nguyên nào.

---

## Nguồn

| Nội dung | Nguồn |
|---|---|
| Worker ComfyUI chính chủ, hợp đồng `/run` `/status`, giới hạn 10/20 MB, chỉ xử lý `images`, AGPL-3.0 | `github.com/runpod-workers/worker-comfyui` — README + `handler.py` |
| Tính tiền serverless: theo giây, start/exec/idle, Flex vs Active, volume $0,07/GB | `docs.runpod.io/serverless/pricing` |
| Bảng giá Pod và Serverless | `runpod.io/pricing` |
| Network volume: 200–400 MB/s, khoá theo DC, preload | `docs.runpod.io/storage/network-volumes` |
| API S3 — quản tệp **không cần Pod** | `docs.runpod.io/storage/s3-api` |
| Giá Modal (kèm CPU/RAM tính riêng, $30 credit, 1 TiB volume) | `modal.com/pricing` |
| Giá Replicate, fal.ai | `replicate.com/pricing`, `fal.ai/pricing` |
| R2: object 5 TiB, **single-part 5 GiB**, multipart 10.000 phần | `developers.cloudflare.com/r2/platform/limits/` |
| Khoá đầu ra video của ComfyUI lõi | `ComfyUI/comfy_api/latest/_ui.py:437` |
| Khoá đầu ra của VideoHelperSuite | `ComfyUI-VideoHelperSuite/videohelpersuite/nodes.py:634` |
