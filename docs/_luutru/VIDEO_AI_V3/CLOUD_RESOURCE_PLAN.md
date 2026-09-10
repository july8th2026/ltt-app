# P03 — KẾ HOẠCH TÀI NGUYÊN CLOUD

> ⛔ **HỒ SƠ ĐƯỜNG ĐI — KHÔNG PHẢI CHỈ DẪN (đóng băng 2026-09-05).**
> Kế hoạch đang sống là **`KE_HOACH_XAY_DUNG.md`**; tham số sản xuất sống trong
> **`platform_core/video_gen/cau_hinh_san_xuat.py`**. Tệp này viết trước
> `V-010`/`V-012` nên nó còn mang giả định **fp8 · 4 bước · 640×640 · nhiều bậc
> chất lượng · L40**. Cả năm giả định đó **đã bị gỡ**. Đọc tệp này để hiểu
> *chương trình đã đi qua đâu*, đừng đọc để lấy con số.


> Sản phẩm của **P03**. Giá **đã hỏi lại lần hai** trong cùng phiên (04/09/2026),
> kết quả **không đổi**: RunPod serverless A100 80GB = **$2,72/giờ**.
>
> ⛔ Vẫn phải hỏi lại **một lần nữa ngay trước khi tạo tài nguyên** ở P04 —
> `GLOBAL_RULES` cấm coi ảnh chụp giá là hằng số, và "cùng ngày" không phải
> "cùng lúc".

Bối cảnh: `V-008` (A100 80GB) · `V-005②` (thuê) · `Q121` (serverless) ·
`D08` ($150/tháng).

---

## 1. Danh sách tài nguyên — đúng ba thứ

| # | Tài nguyên | Cấu hình | Vì sao |
|---|---|---|---|
| ① | **Network volume** | **300 GB ngay từ đầu** (không chia đợt) | ⚠️ **CHỈ chứa model** — xem ghi chú |
| ② | **Serverless endpoint** | A100 80GB · `max_workers = 1` · `active_workers = 0` | chạy job |
| ③ | **S3 API key** | riêng của volume | nạp model **không cần bật GPU** |

Không có Pod thường trú. Không có cluster. Không có gì khác.

🔴 **Sửa một chỗ bản đầu viết sai:** volume **không** chứa ComfyUI/torch/venv.
`docs.runpod.io/serverless/storage/overview.md`: container disk *"Cost is included
in the worker's running cost"*, và Docker image cache trên container disk. ⇒ Volume
**chỉ chứa trọng số model** ⇒ dung lượng nhỏ hơn bản đầu tính.
Số chính xác: `CHUOI_MODEL_VA_VAN_HANH.md` §2 — **220,812 GB** tĩnh cho đủ 4 mode,
**đỉnh ≈ 263 GB** khi P08 để bf16 và fp8 của cùng một mode cạnh nhau.
⇒ **300 GB**, biên 12,4 %. ⚠️ Nới được, **thu lại thì không**.

⚠️ **Tính tiền volume là THEO GIỜ**, không phải gói tháng cố định
(`billing.md`: *"Network volumes — Hourly"*). Giữ 10 ngày thì trả 10 ngày.

### Tên và nhãn — để phát hiện tài nguyên mồ côi

```
volume    lttv-models-v1
endpoint  lttv-wan22-a100
```

Quy tắc: **mọi** tài nguyên bắt đầu bằng `lttv-`.

🔴 **ĐỔI 05/09 từ `lttvideo-` sang `lttv-`.** Khi app `lttvideo` ra đời, bánh cóc `test_no_app_slug_is_hardcoded_in_the_platform` bắt được rằng `platform_core/video_gen/cloud_api.py` chứa chuỗi `"lttvideo-"` — tức `platform_core` biết tên một app. Và `V-002` đã viết trước điều đó: *"`lttvideo` không xuất hiện trong `platform_core/` và phép kiểm giữ nguyên độ sắc"*.

⭐ Sửa bằng cách **đổi tiền tố**, không bằng cách nới phép kiểm. Nới một bánh cóc để mã của mình đi lọt là bỏ luôn thứ nó đang canh. Tên tài nguyên thật trên RunPod đã đổi theo (`PATCH` trả 200): volume `lttv-models-v1`, endpoint `lttv-worker`. Bất cứ thứ gì trong tài
khoản **không** mang tiền tố đó là **không phải của dự án này** ⇒ hoặc của người
khác, hoặc mồ côi. Đó là toàn bộ cơ chế dò mồ côi, và nó đủ vì tài khoản này chưa
có gì khác.

---

## 2. Cấu hình endpoint — bốn số, và ba trong đó phải đổi khỏi mặc định

Mặc định của RunPod (đọc `docs.runpod.io/serverless/endpoints/manage-endpoints`):

| Tham số | Mặc định | **Ta đặt** | Vì sao |
|---|---|---|---|
| `Active workers` | 0 | **0** ✅ giữ | worker thường trú = đốt tiền 24/7 |
| `Max workers` | **3** | **1** ⛔ đổi | ba worker song song = **gấp ba tốc độ cháy ngân sách** |
| `GPUs per worker` | 1 | **1** ✅ giữ | |
| `Idle timeout` | 5 s | **5 s** ✅ giữ | đây chính là thứ xoá bài toán "Pod bật 20 phút chạy 3 phút" |
| `Execution timeout` | **600 s** | ⚠️ **phải xem lại** | xem §2.1 |
| `Job TTL` | 24 h | 24 h ✅ giữ | |
| `FlashBoot` | bật | **bật** ✅ giữ | giảm khởi động nguội |

### 2.1 🔴 `Execution timeout = 600 s` là một ràng buộc THẬT, không phải mặc định vô hại

10 phút là **trần thời gian một job**. Đối chiếu với số đã biết:

```
Khởi động nguội — chuỗi T2V nạp 68,78 GB @ 200–400 MB/s   172–344 s
Một lượt fp8 640×640 trên 4090 (ghi chú template)          ~536 s
                                                          ─────────
cộng lại                                                 708–880 s  >  600 s
```

🔴 **Con số này TỆ HƠN bản đầu của P03**, vốn ước "model ~30 GB → 75–150 s".
Chuỗi model thật (`CHUOI_MODEL_VA_VAN_HANH.md` §1) là **68,78 GB** cho T2V/I2V
— umt5 11,37 + **cả hai** chuyên gia MoE 28,58×2 + VAE 0,25.

⇒ **Ngay ở cấu hình NHẸ NHẤT đã vượt trần**, không phải "có thể chạm". Đường bf16
20 bước ở 720p (`V-008`) thì chắc chắn. Còn lại chỉ **256–428 giây** cho việc sinh
thật nếu khởi động nguội tính vào cùng cửa sổ.

⚠️ **Hai câu P04 phải trả lời trước khi tạo endpoint**, và tài liệu không nói:
1. Trần trên của `Execution timeout` là bao nhiêu?
2. Thời gian **khởi động nguội** có tính vào `Execution timeout` không, hay chỉ
   tính vào hoá đơn?

Câu ② quan trọng hơn: nếu có, thì mỗi lần nguội ta mất 20–25 % cửa sổ thời gian
cho việc nạp model. **Không đoán — hỏi bằng một job thật ở P06.**

**Đề xuất khởi điểm:** đặt `Execution timeout` = **1800 s (30 phút)** nếu cho
phép; nếu trần thấp hơn thì lấy trần và ghi vào `GOLDEN_PIPELINES` như một giới
hạn sản phẩm (độ dài video tối đa bán được).

---

## 3. Trung tâm dữ liệu — phải thoả **ba** điều cùng lúc

Không phải một, và đây là ràng buộc pack V3 không nêu.

| Điều kiện | Nguồn |
|---|---|
| ① Có **API S3** cho network volume | 15 DC, xem dưới |
| ② Có **A100 80GB** cho serverless | ⏳ P04 kiểm live — tài liệu không liệt kê |
| ③ Volume **khoá worker vào đúng DC đó** | *"Attaching a single network volume constrains worker deployments to that volume's datacenter"* |

**15 DC có API S3** (`docs.runpod.io/storage/s3-api`):

```
EU-CZ-1   EU-RO-1   EUR-IS-1  EUR-NO-1
US-CA-2   US-GA-2   US-IL-1   US-KS-2   US-MD-1
US-MO-1   US-MO-2   US-NC-1   US-NC-2   US-NE-1   US-WA-1
```

⭐ **Độ trễ mạng tới Việt Nam KHÔNG phải tiêu chí.** Job là bất đồng bộ, và media
đi qua presigned R2 chứ không qua máy A. Chọn theo **tính sẵn có của A100**, không
theo bản đồ.

⚠️ Điều ③ là rủi ro vận hành thật: một DC hết A100 nghĩa là job **xếp hàng vô
hạn**, không phải chuyển sang DC khác. Giảm thiểu bằng nhiều volume ở nhiều DC —
nhưng **dữ liệu không tự đồng bộ**, tức phải nạp model **hai lần** và trả tiền lưu
trữ **hai lần**. ⇒ **V1 dùng một DC.** Nếu hết hàng thì đó là một sự cố phải báo,
không phải thứ tự chữa.

---

## 4. Bốn loại bí mật — bốn chỗ khác nhau

Đây là chỗ dễ trộn nhất, và trộn thì hỏng theo hướng đắt tiền.

| # | Bí mật | Dùng để | Cất ở | Ai cầm |
|---|---|---|---|---|
| ① | **RunPod API key** | tạo/sửa/xoá endpoint, đọc hoá đơn | `secrets/app.env` | chỉ máy A |
| ② | **RunPod S3 API key** *(khác ①)* | nạp model lên volume | chỉ dùng khi vận hành thủ công ở P05 | chỉ người vận hành |
| ③ | **Khoá gọi endpoint** (Bearer) | `POST /run` | **APIKEYS**, provider `ltt_video`, category `video` | máy A, qua `api_pool` |
| ④ | **Credential R2 tạm** | worker ghi kết quả | **không cất** — sinh mỗi job, TTL ngắn, giới hạn tiền tố | worker (`V-007`) |

⛔ **① và ③ tách nhau là có chủ ý** (đã ghi ở ADR-3 §7): đặt khoá *vòng đời* vào
`api_pool` là để cơ chế cooldown/**disable-sau-5-lỗi** của một nhà cung cấp *model*
điều khiển thứ tạo ra **hoá đơn**. Sai ngữ nghĩa.

⭐ Tài liệu RunPod xác nhận ① và ② thật sự là hai thứ: *"you'll need to generate a
new key called an 'S3 API key' (**this is separate from your Runpod API key**)"*.

---

## 5. Nạp model không cần GPU — kế hoạch P05

Đường đã xác nhận: *"manage files on your network volumes **without launching a
Pod**"*, và *"Using the S3-compatible API does not affect pricing"*.

```
① Tạo volume ở DC đã chọn                     (P04)
② Tạo S3 API key                              (P04)
③ Đẩy model bằng công cụ S3 chuẩn             (P05) — 0 giây GPU
④ Sinh BANG_KE.json (sha256/size/ngày)        (P05) — khuôn render_gateway/deploy/tai_model.py
⑤ Đối chiếu bản kê với MODEL_BOM_FINAL.csv    (P05)
```

⭐ Bước ④ dùng lại `render_gateway/deploy/tai_model.py` — nó đã tải theo **bản
khai JSON**, ghi `BANG_KE.json` *(tên · nguồn · sha256 · ngày · dung lượng)*, và
**tải tiếp được** khi rớt mạng giữa chừng. Đây là chỗ hiếm hoi ta dùng lại mã của
B-LAN mà **không** chạm vào nó: chỉ chạy tệp đó từ máy A, không sửa.

---

## 6. Giữ dữ liệu ở đâu — ba nơi, ba vòng đời

| Nơi | Chứa gì | Vòng đời | Ai trả tiền |
|---|---|---|---|
| **Network volume** | ⚠️ **CHỈ model** (220,81 GB tĩnh · đỉnh ~263 GB) | **thường trú** | $0,07/GB/tháng, **tính theo giờ** |
| **Container disk** của worker | ⭐ **ComfyUI · torch · custom node** (trong Docker image) + scratch | **chết cùng worker** | **gộp trong giá giờ** |
| **R2** | media vào của khách · video ra | theo `docs/DATA_RETENTION_POLICY.md` | đã có |

⛔ **Không bao giờ để media của khách trên model volume.** Ba lý do: nó là bộ nhớ
dùng chung giữa mọi worker; nó không có vòng đời xoá; và nó nằm ngoài chính sách
giữ dữ liệu mà nền tảng đã công bố với khách.

---

## 7. Nếu A100 hết hàng — **đề xuất, không phải quyết định**

`D06` khoá A100 80GB và `V-008` đã xác nhận bằng số (Wan2.2 A14B đòi ≥80GB ngay
cả khi đã offload). Nên nếu hết hàng thì **không có bậc thấp hơn để rơi xuống** —
đây không phải chuyện chọn card rẻ hơn.

Ba đường, xếp theo mức độ đụng vào quyết định đã chốt:

| | Đường | Đụng gì |
|---|---|---|
| 1 | Chờ, hoặc đổi DC (nạp lại model, trả lưu trữ hai lần) | không đụng quyết định nào |
| 2 | **H100 80GB $4,79/giờ** (+76 %) | không đụng `V-008` (vẫn 80GB), nhưng **envelope co lại 43 %** |
| 3 | Đường fp8 trên card 48GB $1,22/giờ | ⛔ đụng `V-008` — phải trình chủ dự án |

⛔ **P04 không được tự chọn đường 3.** Nó là một quyết định sản phẩm (đổi trần
chất lượng), không phải một cách chữa cháy kỹ thuật.

---

## 8. Cái P03 **không** chốt được

| | Ai |
|---|---|
| A100 80GB có ở DC nào | **P04**, kiểm live |
| Trần trên của `Execution timeout`, và khởi động nguội có tính vào đó không | **P04/P06** |
| Thời gian thật một lượt sinh video ⇒ envelope có đủ không | **P07** |
| Kích thước ba model phụ của Character | **P05** |
