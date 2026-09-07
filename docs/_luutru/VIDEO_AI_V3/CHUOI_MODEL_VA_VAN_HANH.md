# CHUỖI MODEL VÀ PHÂN TÍCH VẬN HÀNH — số GB chính xác

> ⛔ **HỒ SƠ ĐƯỜNG ĐI — KHÔNG PHẢI CHỈ DẪN (đóng băng 2026-09-05).**
> Kế hoạch đang sống là **`KE_HOACH_XAY_DUNG.md`**; tham số sản xuất sống trong
> **`platform_core/video_gen/cau_hinh_san_xuat.py`**. Tệp này viết trước
> `V-010`/`V-012` nên nó còn mang giả định **fp8 · 4 bước · 640×640 · nhiều bậc
> chất lượng · L40**. Cả năm giả định đó **đã bị gỡ**. Đọc tệp này để hiểu
> *chương trình đã đi qua đâu*, đừng đọc để lấy con số.


> Bổ sung P02/P03 sau khi chủ dự án hỏi thẳng: *"đã có số GB chính xác chưa?"*
>
> **Câu trả lời trung thực lúc được hỏi: CHƯA.** BOM còn ba tệp ghi
> `0.00 GB / CHƯA_XÁC_ĐỊNH`, và con số "+10 GB cho ComfyUI" là **ước**, không đo.
> Tệp này đóng cả hai lỗ, và sửa **một chỗ tôi đã sai**.

Tra 2026-09-04 bằng HuggingFace API (`?blobs=true` — kích thước thật từng tệp).

---

## 0. 🔴 Một chỗ tôi đã SAI, và nó làm volume nhỏ đi

P03 viết *"cộng ComfyUI + custom node + venv ~10 GB"* vào dung lượng volume.
**Sai.** `docs.runpod.io/serverless/storage/overview.md` nói rõ:

> **Container disk** — *"Cost is **included in the worker's running cost**."*
> *"Docker images cache locally on container disk."*

⇒ ComfyUI, Python, torch, CUDA đều nằm trong **Docker image**, và image được tính
vào **giá giờ worker**, không phải vào volume. Custom node cũng nên nằm trong image.

> ⭐ **Network volume chỉ cần chứa TRỌNG SỐ MODEL.** Không có ComfyUI, không có
> venv, không có scratch (scratch là container disk, chết cùng worker).

---

## 1. Chuỗi model theo từng mode — thứ tự nạp và dung lượng thật

Đọc từ chính tệp workflow JSON chính chủ, không suy từ tên.

### 1.1 T2V — `video_wan2_2_14B_t2v.json`

```
CLIPLoader   → umt5_xxl_fp16.safetensors              11,370 GB   (bộ mã hoá văn bản)
UNETLoader ① → wan2.2_t2v_high_noise_14B_fp16          28,580 GB   (chuyên gia SỚM, bước 0→2)
UNETLoader ② → wan2.2_t2v_low_noise_14B_fp16           28,580 GB   (chuyên gia MUỘN, bước 2→4)
VAELoader    → wan_2.1_vae.safetensors                  0,250 GB
                                                       ─────────
                                                        68,780 GB
```

⭐ **Hai `UNETLoader` KHÔNG cùng nằm VRAM một lúc.** MoE hai chuyên gia: KSampler①
chạy trên bản high-noise, KSampler② chạy trên bản low-noise. ComfyUI đổi model
giữa hai chặng. ⇒ **VRAM đỉnh ≈ một chuyên gia (28,58) + umt5 (11,37) = 39,95 GB**
trước activation — nhưng **đĩa phải chứa cả hai**.

🔑 Đây chính là chỗ số 80GB của `V-008` có nghĩa: 39,95 GB tĩnh + activation ở
720p×81 khung. Trên card 48GB còn ~8 GB cho activation — rất sát. Trên 80GB thoải mái.

### 1.2 I2V — `video_wan2_2_14B_i2v.json`

Y hệt T2V, thay `EmptyHunyuanLatentVideo` → `WanImageToVideo` + `LoadImage`.
Trọng số khác tên nhưng **cùng kích thước**: **68,780 GB**.

### 1.3 V2V — `video_wan2_2_14B_fun_control.json`

```
CLIPLoader   → umt5_xxl_fp16                           (dùng chung)
UNETLoader ① → wan2.2_fun_control_high_noise_14B_bf16   28,580 GB
UNETLoader ② → wan2.2_fun_control_low_noise_14B_bf16    28,580 GB
VAELoader    → wan_2.1_vae                              (dùng chung)
LoadVideo → GetVideoComponents → Canny → Wan22FunControlToVideo
```
Riêng của mode: **57,160 GB**. `shift = 8.0` (khác 5.0 của T2V/I2V).

### 1.4 Character — `video_wan2_2_14B_animate.json` 🔴 chuỗi dài nhất

```
UNETLoader        → wan2.2_animate_14B_bf16             34,550 GB   ⚠️ MỘT tệp, không phải MoE
LoraLoaderModelOnly → wan2.2_animate_14B_relight_lora    1,440 GB
CLIPLoader        → umt5_xxl_fp16                       (dùng chung)
VAELoader         → wan_2.1_vae                         (dùng chung)
CLIPVisionLoader  → clip_vision_h.safetensors            1,264 GB   ← kho Wan 2.1!
DownloadAndLoadSAM2Model → sam2_hiera_base_plus          0,323 GB   ⛔ TỰ TẢI LÚC CHẠY
DWPreprocessor    → dw-ll_ucoco_384_bs5.torchscript.pt   0,135 GB
                                                        ─────────
riêng của mode                                           37,712 GB
```

⚠️ **`clip_vision_h` đến từ kho `Comfy-Org/Wan_2.1_ComfyUI_repackaged`** — nguồn
thượng nguồn **thứ năm**, không phải kho Wan 2.2. Dễ bỏ sót khi nạp.

⛔ **`DownloadAndLoadSAM2Model` tự tải lúc chạy.** Trên serverless đó là tải lại
mỗi lần khởi động nguội **và** một phụ thuộc mạng giữa job đang tính tiền. Phải
đổi sang nạp từ `/runpod-volume` trước khi chạy thật.

---

## 2. Số GB chính xác — không còn ô `CHƯA_XÁC_ĐỊNH` nào

| Nhóm | Tệp | GB |
|---|---|---|
| **Dùng chung** | `umt5_xxl_fp16` | 11,370 |
| | `wan_2.1_vae` | 0,250 |
| | **cộng** | **11,620** |
| **T2V** | high + low noise | **57,160** |
| **I2V** | high + low noise | **57,160** |
| **V2V** | fun_control high + low | **57,160** |
| **Character** | animate bf16 | 34,550 |
| | relight lora | 1,440 |
| | clip_vision_h | 1,264 |
| | sam2_hiera_base_plus | 0,323 |
| | dw-ll_ucoco_384_bs5 | 0,135 |
| | **cộng** | **37,712** |
| | | |
| | **TỔNG 4 MODE (bf16)** | **220,812 GB** |

### Đỉnh dung lượng thật — **không phải 220,8 mà là ~263 GB**

220,812 GB là trạng thái *tĩnh* của 4 mode. Nhưng **P08 phải để bf16 và fp8 của
cùng một mode nằm cạnh nhau** để so cùng seed. Đỉnh thật:

```
4 mode bf16 (thường trú)                              220,812 GB
+ fp8 của MỘT mode, lấy mode nặng nhất (V2V 14,30×2)   28,600 GB
+ umt5_xxl_fp8 (bộ mã hoá của đường fp8)                6,740 GB
+ LoRA distill 4 bước (nếu đo đường nhanh)              4,920 GB
                                                      ──────────
ĐỈNH                                                  261,072 GB
+ model phụ mà custom node tự tải (controlnet_aux…)    ~2 GB (ước)
                                                      ──────────
                                                     ≈ 263 GB
```

⛔ **KHÔNG tải cả 4 bộ fp8 cùng lúc** (220,8 + 115,8 = 336,6 GB) — tải **từng
mode một**, đo xong thì xoá. API S3 quản tệp không cần bật Pod ⇒ tốn 0 đồng GPU.

### ✅ Chốt: **300 GB ngay từ đầu**

| Phương án | Biên trên đỉnh 263 GB | Đánh giá |
|---|---|---|
| 275 GB | 12 GB = **4,4 %** | ⛔ **quá mỏng** — con số 275 của tôi tính trên trạng thái tĩnh, quên đỉnh P08 |
| **300 GB** | **37 GB = 12,4 %** | ✅ |
| chia đợt 160 → 230 → 300 | — | ⛔ lần nới rơi **giữa P07** |

⚠️ **Nới được, thu lại thì không** — `network-volumes.md`: *"Volume size can be
increased later but **cannot be decreased**."* ⇒ đặt hụt thì phải tạo volume mới
và chép lại toàn bộ.

⛔ **Và một cảnh báo mới đọc được, liên quan trực tiếp:** *"Writing to the same
volume from multiple workers simultaneously **may cause data corruption**."*
Với `max_workers = 1` ta an toàn — nhưng đây là **lý do thứ ba** để giữ nó bằng 1,
bên cạnh chi phí và envelope.

---

## 3. 🔴 Cách tính tiền ổ đĩa — trả lời thẳng câu hỏi

> **Hỏi:** *gói thuê tháng tính theo giờ sử dụng, hay fix thuê là dứt điểm tiền luôn?*
>
> **Đáp: TÍNH THEO GIỜ. Không có gói tháng cố định.**

`docs.runpod.io/accounts-billing/billing.md` — bảng chính chủ:

| Loại lưu trữ | Giá niêm yết | **Nhịp tính tiền** |
|---|---|---|
| Container disk (Pod đang chạy) | $0,10/GB/tháng | **theo giây** |
| Volume disk (Pod đang chạy) | $0,10/GB/tháng | **theo giây** |
| Volume disk (Pod đã **dừng**) | **$0,20/GB/tháng** | theo giây |
| **Network volume < 1 TB** | **$0,07/GB/tháng** | **theo GIỜ** |
| Network volume > 1 TB | $0,05/GB/tháng | theo giờ |

**Nghĩa là gì cho ta:**

1. **`$/GB/tháng` chỉ là ĐƠN VỊ QUY ĐỔI, không phải chu kỳ thu tiền.** Giữ volume
   300 GB trong 10 ngày ⇒ trả `$21,00 × 10/30 = $7,00`, không phải $21,00.
2. **Trả trước bằng credit, trừ dần theo thời gian thực** — *"charges are deducted
   in real-time"*. Không phải hoá đơn cuối tháng.
3. ⭐ **Không tính phí truyền dữ liệu** — *"with no fees for data transfer"*. Tải
   model từ volume và đẩy video lên R2 **không** phát sinh phí mạng phía RunPod.
4. ⚠️ **Cột "Volume disk (Pod đã dừng) = $0,20"** là của **Pod**, không phải
   network volume. Ta không dùng Pod ⇒ không dính. Ghi ra để không ai đọc nhầm rồi
   tưởng dừng máy là đắt gấp đôi.

### ⛔ Và một rủi ro tôi CHƯA biết khi viết `CLOUD_SAFETY_PLAN`

Cùng trang, nguyên văn:

> *"Storage charges continue to accrue on network volumes while your Pods are
> stopped. **If your balance stays at $0 and these charges can't be covered, the
> network volume may eventually be terminated, and its data can't be recovered.**"*
>
> *"Runpod is **not designed for long-term data storage**… If your account runs
> out of funds, storage may be deleted and cannot be recovered."*

🔴 **Cầu dao ngân sách của tôi có một lỗ chết người.** Nó thiết kế để *ngừng tiêu
khi chạm envelope* — nhưng nếu số dư về $0 thì **volume 220 GB model bị xoá và
không khôi phục được**. Nạp lại là nhiều giờ và phải làm lại từ đầu.

**Sửa — thêm luật vào cầu dao:**

```
SÀN CREDIT = chi phí lưu trữ 30 ngày × 1,5
           = $21,00 × 1,5 = $31,50  (ở volume 300 GB)

Cầu dao ngắt COMPUTE khi:  số dư ≤ SÀN CREDIT   (không đợi tới $0)
Cảnh báo vận hành khi:     số dư ≤ SÀN × 2
```

⇒ Tiền còn lại **chỉ đủ nuôi ổ đĩa**, không đủ chạy job. Đó là trạng thái đúng:
mất khả năng sinh video là **phiền**; mất 220 GB model là **mất nhiều giờ**.

⭐ Và nó đổi cách đọc `D08`: **$150/tháng không phải thứ được tiêu tới đồng cuối.**
Trần tiêu thật là **$150 − volume $21,00 − sàn $31,50 = $97,50**, tức **35,8 giờ
GPU**. Envelope ở `COST_BUDGET_LEDGER.md` §2 đã tính theo số này.

---

## 4. Vận hành: một job đi qua những gì

```
① máy A: jobs.claim → giữ credit → sinh credential R2 tạm (tiền tố + TTL)
② máy A: POST api.runpod.ai/v2/<endpoint>/run   { workflow, refs, put_target }
③ RunPod: khởi động worker (nguội: kéo image + gắn volume)
④ worker: nạp model TỪ VOLUME  ← 68,78 GB cho T2V, đây là phần lớn thời gian nguội
⑤ worker: tải media vào bằng presigned GET
⑥ worker: ComfyUI chạy workflow
⑦ worker: đọc kết quả ở outputs[node]["images"]  (node lõi SaveVideo/CreateVideo)
⑧ worker: ghi thẳng lên R2 bằng credential tạm (V-007)
⑨ máy A: poll /status hoặc nhận webhook → quyết toán theo billed_seconds thật
```

**Chi phí khởi động nguội, tính lại bằng số chính xác:**

```
T2V/I2V:   68,78 GB ÷ 200–400 MB/s  =  172–344 giây
Character: 49,33 GB ÷ 200–400 MB/s  =  123–247 giây
```

🔴 **Đây là con số tệ hơn ước tính cũ.** P02/P03 ước "model ~30 GB → 75–150 s".
Thật ra chuỗi T2V nạp **68,78 GB** ⇒ **172–344 giây**, tức **gấp đôi**.

Hệ quả trực tiếp lên `Execution timeout = 600 s`:

```
khởi động nguội 172–344 s  +  một lượt sinh  ≤ 600 s
⇒ chỉ còn 256–428 giây cho việc sinh thật
```

⇒ **Gần như chắc chắn phải nâng `Execution timeout`.** Và câu hỏi *"khởi động
nguội có tính vào Execution timeout không"* nay **không còn là chi tiết** — nó
quyết định mode nào chạy được.

⭐ Đây cũng là lý do `FlashBoot` và **gộp lô** đáng tiền: worker ấm bỏ qua bước ④.
Ở giá $2,72/giờ, 344 giây khởi động = **$0,26 mỗi lần nguội**.

---

## 5. Cái vẫn phải ĐO, không tra được

| | Ai | Vì sao không tra được |
|---|---|---|
| Băng thông volume thật (200 hay 400 MB/s) | **P06** | dải công bố rộng gấp đôi ⇒ thời gian nguội chênh gấp đôi |
| Khởi động nguội có tính vào `Execution timeout` không | **P06** | tài liệu không nói |
| Thời gian sinh thật một lượt bf16 720p trên A100 | **P07** | chưa ai công bố cho cấu hình này |
| Custom node đặt trong image hay trên volume | **P06** | đánh đổi: image to hơn (kéo lâu) ↔ volume tốn tiền |
