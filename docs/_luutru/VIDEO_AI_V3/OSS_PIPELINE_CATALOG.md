# P02 — CATALOG PIPELINE MÃ NGUỒN MỞ CHO 4 MODE V1

> ⛔ **HỒ SƠ ĐƯỜNG ĐI — KHÔNG PHẢI CHỈ DẪN (đóng băng 2026-09-05).**
> Kế hoạch đang sống là **`KE_HOACH_XAY_DUNG.md`**; tham số sản xuất sống trong
> **`platform_core/video_gen/cau_hinh_san_xuat.py`**. Tệp này viết trước
> `V-010`/`V-012` nên nó còn mang giả định **fp8 · 4 bước · 640×640 · nhiều bậc
> chất lượng · L40**. Cả năm giả định đó **đã bị gỡ**. Đọc tệp này để hiểu
> *chương trình đã đi qua đâu*, đừng đọc để lấy con số.


> Sản phẩm của **P02**. Tra ngày **2026-09-04** bằng `curl` vào GitHub API,
> HuggingFace API và **chính tệp workflow JSON chính chủ** — không đọc bài blog,
> không suy từ tên.
>
> ⛔ Mọi số VRAM ở đây là **ƯỚC** hoặc **trích từ ghi chú của người khác**.
> Chưa có một số nào do ta đo. Cột "đã đo" chỉ được điền ở **P07**.

Bối cảnh đã chốt: `V-008` (Wan2.2, A100 80GB) · `V-001` (nội bộ trước) ·
`D04` (ComfyUI là baseline, backend production quyết sau benchmark).

---

## 0. Kết luận

| Mode V1 | Ứng viên **baseline** | Ứng viên **thay thế** | Rủi ro |
|---|---|---|---|
| **T2V** | `video_wan2_2_14B_t2v` + Wan2.2-T2V-A14B | Wan2.2-TI2V-5B | 🟢 thấp — **0 custom node** |
| **I2V** | `video_wan2_2_14B_i2v` + Wan2.2-I2V-A14B | Wan2.2-TI2V-5B · `flf2v` | 🟢 thấp — **0 custom node** |
| **V2V** | `video_wan2_2_14B_fun_control` + Wan2.2-Fun-Control-A14B | Fun-VACE-A14B · Fun-Inpaint | 🟡 vừa — lõi đủ chạy, **tiền xử lý** cần custom node |
| **Character** | `video_wan2_2_14B_animate` + Wan2.2-Animate-14B | Fun-VACE-A14B (không có template chính chủ) | 🔴 **cao** — nhiều custom node + 3 model phụ |

**Cả 4 mode đều có baseline. Không mode nào NO-GO.** Nhưng rủi ro **không đều**,
và điều đó phải vào thứ tự chạy của P07 — xem §5.

⭐ **Xác nhận `V-008` bằng một phép tra riêng:** không có trọng số **mở** nào mới
hơn Wan2.2. Tìm `Wan2.5` / `Wan2.6` / `Wan2.7` trên HuggingFace ⇒ **không có kho
chính chủ nào**. Trong kho template của ComfyUI có `api_wan2_6_*`, `api_wan2_7_*`
— nhưng đó là **API node trả tiền** gọi về `wan.video`, không phải trọng số tải
được. Wan2.2 **là** bản mở mới nhất.

---

## 1. Giấy phép — cổng chặn, không phải lời khuyên

| Thứ | Giấy phép | Bán được không |
|---|---|---|
| **Wan2.2** (mọi biến thể) | **Apache-2.0** | ✅ Và README nói thẳng: *"We claim no rights over the your generated contents"* |
| `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` | apache-2.0 | ✅ |
| `Comfy-Org/workflow_templates` | **MIT** | ✅ |
| `kijai/ComfyUI-WanVideoWrapper` | Apache-2.0 | ✅ |
| `Kosinkadink/ComfyUI-VideoHelperSuite` | **GPL-3.0** | ⚠️ xem dưới |
| ComfyUI (lõi) | GPL-3.0 | ⚠️ xem dưới |

⚠️ **GPL-3.0 và mô hình SaaS của ta.** GPL-3 kích hoạt nghĩa vụ khi **phân phối**
phần mềm. Ta **chạy** ComfyUI như một dịch vụ nội bộ và không giao binary cho ai
⇒ nghĩa vụ không kích hoạt. Đây **khác** AGPL-3.0 (§13 kích hoạt qua mạng) — và
kho này đã trả giá để biết khác biệt đó ở Q94/Q100 với RustDesk.

⛔ Nên nhớ đúng một điều: **`runpod-workers/worker-comfyui` là AGPL-3.0.** Chép mã
của nó vào `video_gateway` sẽ kéo AGPL vào một dịch vụ chạy qua mạng. Đó là lý do
kỹ thuật *và* pháp lý để **đọc nó rồi viết mã của mình** (đã ghi ở
`NGHIEN_CUU_CLOUD_GPU.md` §1).

---

## 2. Bốn mode, từng cái một

Nguồn workflow: `Comfy-Org/workflow_templates` @ `templates/`, MIT.
Nguồn trọng số: `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` @ `split_files/`.

### 2.1 T2V — `video_wan2_2_14B_t2v.json` 🟢

| | |
|---|---|
| **Node** | **100 % lõi ComfyUI**: `UNETLoader` · `CLIPLoader` · `VAELoader` · `CLIPTextEncode` · `LoraLoaderModelOnly` · `ModelSamplingSD3` · `KSamplerAdvanced` ×2 · `EmptyHunyuanLatentVideo` · `VAEDecode` · `CreateVideo` · `SaveVideo` |
| **Custom node** | **KHÔNG CÓ** ✅ |
| **Model** | `wan2.2_t2v_{high,low}_noise_14B` · `umt5_xxl` · `wan_2.1_vae` |
| **Mặc định** | **640×640 · 81 khung · 16 fps** (≈5,06 s) · `shift=5.0` |
| **Hai chặng MoE** | KSampler ①: bước `0→2` trên **high-noise expert**, `add_noise=enable`; KSampler ②: bước `2→4` trên **low-noise expert**, `add_noise=disable` |
| **Bậc nhanh (mặc định của template)** | **4 bước, cfg=1**, kèm LoRA `lightx2v_4steps_v1.1` |
| **Bậc chất lượng** | **20 bước, cfg=3.5**, không LoRA distill |

### 2.2 I2V — `video_wan2_2_14B_i2v.json` 🟢

Giống hệt T2V về cấu trúc, thay `EmptyHunyuanLatentVideo` bằng **`WanImageToVideo`**
và thêm `LoadImage`. Vẫn **0 custom node**. Mặc định **640×640 · 81 · 16 fps**.

### 2.3 V2V — `video_wan2_2_14B_fun_control.json` 🟡

| | |
|---|---|
| **Node lõi** | `Wan22FunControlToVideo` · `LoadVideo` · `GetVideoComponents` · `Canny` · `CreateVideo` · `SaveVideo` + bộ nạp/sampler như trên |
| **Custom node** | **KHÔNG bắt buộc.** `Canny` là node lõi ⇒ chạy được ngay |
| **Tuỳ chọn** | Ghi chú trong template: *"You may need the following custom nodes to preprocess the control video"* → `comfyui_controlnet_aux`, `ComfyUI-DepthAnythingV2` |
| **Model** | `wan2.2_fun_control_{high,low}_noise_14B` |
| **Mặc định** | 640×640 · 81 · 16 fps · `shift=8.0` (khác T2V/I2V!) |

⭐ **Vì sao chọn Fun-Control làm baseline V2V chứ không phải VACE:** nó có
**template chính chủ**, chạy được bằng **node lõi**, và tách bạch *"giữ chuyển
động từ video nguồn"* — đúng nghĩa V2V. Fun-VACE mạnh hơn nhưng **không có
template chính chủ** trong kho Comfy-Org (chỉ có blueprint cho **Wan2.1**-VACE).

### 2.4 Character / Reference — `video_wan2_2_14B_animate.json` 🔴

Đây là mode **rủi ro nhất**, và phải nói thẳng.

| | |
|---|---|
| **Node** | 40 node, gồm **`DownloadAndLoadSAM2Model`**, **`DWPreprocessor`**, `BlockifyMask`, `DrawMaskOnImage`, `GrowMask`, `PixelPerfect*`, `CLIPVisionLoader/Encode` |
| **Custom node** | **BẮT BUỘC**, ít nhất ba gói: segment-anything-2 · `comfyui_controlnet_aux` (DWPose) · KJNodes |
| **Model phụ** | `clip_vision_h` · `sam2_hiera_base_plus` · `dw-ll_ucoco_384_bs5.torchscript.pt` — **ngoài** kho Comfy-Org |
| **Trọng số chính** | Template trỏ `Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors` — **bản của Kijai**, không phải bản Comfy-Org. Comfy-Org có `wan2.2_animate_14B_bf16` (34,55 GB) và `_int8_convrot` (18,41 GB) |
| **Phụ trợ** | `WanAnimate_relight_lora` · `lightx2v_I2V_14B_480p_cfg_step_distill_rank64` |

⛔ **Ba rủi ro cụ thể, không phải cảm giác:**

1. **`DownloadAndLoadSAM2Model` TỰ TẢI MODEL LÚC CHẠY.** Trên serverless đó là
   tải lại mỗi lần khởi động nguội, và là một phụ thuộc mạng **giữa** một job
   đang tính tiền. Phải thay bằng nạp từ volume — tức **sửa workflow**, tức
   lệch khỏi "upstream nguyên bản" ngay ở mode khó nhất.
2. **Trộn nguồn trọng số**: template dùng bản Kijai, BOM của ta dùng bản
   Comfy-Org. Hai bản **có thể** khác cách lượng tử hoá ⇒ phải chọn một và ghi ra.
3. **Ba gói custom node** = ba lịch phát hành ngoài tầm kiểm soát, và
   `ComfyUI-VideoHelperSuite` là **GPL-3.0**.

**Ứng viên thay thế:** Fun-VACE-A14B (`wan2.2_fun_vace_{high,low}_noise_14B`,
34,68 GB mỗi bản). Nặng hơn, **không có template chính chủ**, nhưng VACE sinh ra
đúng cho *tham chiếu + chỉnh sửa*. Nếu Animate vướng ở P07 thì đây là đường lui.

---

## 3. ⚠️ Hai phát hiện làm lệch giả định của `V-008`

### 3.1 Template chính chủ **mặc định fp8 + 4 bước**, không phải bf16 20 bước

Mọi template trên đều trỏ `*_fp8_scaled.safetensors` và nạp LoRA distill
`lightx2v_4steps`. Tức **"upstream nguyên bản" có HAI nghĩa**:

| "Upstream" theo | Nghĩa là | Chi phí |
|---|---|---|
| Kho **Wan-Video/Wan2.2** | bf16 đầy đủ, ~20–50 bước, 720p | **≥80GB** |
| Kho **template ComfyUI** | fp8_scaled + LoRA 4 bước, 640×640 | vừa **24GB** |

⇒ **P07 phải chọn một và nói rõ đang đo cái nào.** Đề xuất: chạy **bf16 20 bước**
làm *trần chất lượng* (đúng tinh thần `V-008`), rồi **ngay trong P07** chạy thêm
một lượt fp8+4bước cùng seed/prompt để P08 có sẵn cặp so sánh. Chi phí lượt thứ
hai rất nhỏ (4 bước thay vì 20).

### 3.2 Một số đo VRAM có sẵn trong chính template — và nó nói 24GB là đủ cho fp8

`MarkdownNote` trong cả hai template T2V/I2V ghi:

> *"GPU: RTX4090D 24GB — fp8_scaled | 640×640 | **VRAM 84 %** | lần 1 ≈ **536 s**,
> lần 2 ≈ **513 s**"*

⛔ Đọc cho đúng, đừng dùng nó để mở lại `V-008`:
- đây là **640×640**, không phải 720p;
- đây là **fp8**, không phải bf16;
- đây là số của **người khác**, không phải ta đo.

Nó **không** mâu thuẫn với con số 80GB của kho Wan (bf16 @ 720p). Hai cấu hình
khác nhau. Nhưng nó **là** bằng chứng sớm rằng đường fp8 rẻ hơn nhiều — và đó
đúng là câu hỏi P08 phải trả lời, không phải P02.

⭐ Một phép tính hậu thuẫn `V-008`: một chuyên gia A14B ở fp16 là **28,58 GB**,
cộng `umt5_xxl_fp16` **11,37 GB** = **39,95 GB trước khi có một activation nào**.
Trên card 48GB còn ~8GB cho activation ở 720p×81 khung — rất sát. Trên 80GB thì
thoải mái. **A100 80GB là đúng cho đường bf16.**

---

## 4. Ràng buộc kỹ thuật phải mang sang P06

1. 🔴 **Template dùng SUBGRAPH.** T2V và I2V chỉ có 4–5 node ở cấp cao nhất; 30
   node thật nằm trong `definitions.subgraphs`. Đây là tính năng **ComfyUI mới**.
   `gateway_core/comfy.py` (chép từ `render_gateway`) được kiểm chứng với ComfyUI
   **0.30.0 / `6f7cd7f`**. ⇒ **P06 phải xác minh**: bản ComfyUI trên C-CLOUD hỗ
   trợ subgraph, **và** bản xuất *API format* có làm phẳng subgraph không. Nếu
   không phẳng thì `workflows.py` (thay thẻ `"@ten"`) sẽ không tìm thấy node.
2. **Hai VAE khác nhau**: `wan_2.1_vae` (0,25 GB) cho mọi model 14B;
   `wan2.2_vae` (1,41 GB) **chỉ** cho TI2V-5B. Nạp nhầm là hỏng im lặng.
3. **`shift` khác nhau theo mode**: 5.0 (T2V/I2V) vs 8.0 (Fun-Control). Đây là
   giá trị thuộc **workflow**, phải nằm trong template chứ không phải hằng số mã.
4. **Node lưu là `SaveVideo`/`CreateVideo` của lõi** ⇒ đầu ra nằm dưới khoá
   **`"images"`** kèm `"animated": (True,)`, **không** phải `"gifs"`. Khớp với
   phát hiện ở `NGHIEN_CUU_CLOUD_GPU.md` §3③. Đây là điều `videos_of()` phải đọc.

---

## 4b. Tổng BOM và chi phí lưu trữ — đầu vào trực tiếp cho P03

Cộng từ `MODEL_BOM_PLANNED.csv` (dùng chung đếm **một lần**):

| Đường | T2V | I2V | V2V | Character | Dùng chung | **Tổng** |
|---|---|---|---|---|---|---|
| **bf16/fp16** (trần chất lượng) | 57,16 | 57,16 | 57,16 | 34,55 + 1,44 | 11,62 | **≈ 219 GB** |
| **fp8_scaled** (mặc định template) | 28,58 | 28,58 | 28,60 | 18,41 + 1,44 | 6,99 | **≈ 113 GB** |
| LoRA distill (nếu chạy đường 4 bước) | 2,46 | 2,46 | — | — | — | +4,92 GB |

⚠️ Chưa gồm ba model phụ của Character (`clip_vision_h`, `sam2`, `dwpose`) —
**chưa tra được kích thước**, P05 phải bổ sung.

Cộng ComfyUI + custom node + scratch + biên **25 %**:

| Đường | Dung lượng volume | **Chi phí/tháng** ($0,07/GB) | % của $150 |
|---|---|---|---|
| bf16 | **300 GB** | **$21,00** | **14 %** |
| fp8 | **150 GB** | **$10,50** | 7 % |
| chỉ T2V+I2V bf16 (chạy P07 theo đợt) | **200 GB** | **$14,00** | 9 % |

🔴 **Đây là một khoản P00 chưa hề tính vào envelope.** Lưu trữ là **phí cố định
hằng tháng** — nó tiêu ngân sách kể cả tháng không chạy job nào. Ở đường bf16 nó
ăn **14 %** ngân sách trước khi có một khung hình nào được sinh ra.

⭐ Cách giảm mà **không** đụng `V-008`: **tải theo đợt.** P07 chạy T2V → I2V →
V2V → Character theo thứ tự §5, nên volume không cần chứa cả bốn mode ngay từ
đầu. Xoá bớt giữa các đợt cũng được — API S3 của RunPod cho phép quản tệp **không
cần bật Pod**, nên chi phí dọn dẹp bằng không.

⇒ **Đề nghị cho P03:** khởi điểm **200 GB**, nới khi P07 sang mode thứ ba.

---

## 5. Thứ tự chạy P07 — theo rủi ro tăng dần, không theo thứ tự D03

```
1. T2V           0 custom node · template chính chủ · đơn giản nhất
2. I2V           0 custom node · chỉ khác một node so với T2V
3. V2V           lõi đủ chạy (Canny), tiền xử lý nâng cao để sau
4. Character     nhiều custom node + 3 model phụ + một node TỰ TẢI lúc chạy
```

⭐ Lý do không chạy theo thứ tự D03: nếu Character hỏng thì ta muốn biết **sau
khi** đã có ba mode chạy được, chứ không phải cháy nửa ngân sách vào mode khó
nhất rồi mới biết ba mode kia có chạy không. Đúng tinh thần *"đường nào rẻ nhất
để loại bỏ nghi ngờ trước"*.

---

## 6. Cái P02 **không** trả lời được

| | Ai trả lời |
|---|---|
| VRAM/thời gian **thật** của từng mode trên A100 | **P07** — mọi số ở đây là ước hoặc của người khác |
| fp8+4bước mất bao nhiêu chất lượng so với bf16 20 bước | **P08** |
| ComfyUI bản nào trên C-CLOUD, subgraph có phẳng khi xuất API không | **P06** |
| Kích thước thật của 3 model phụ cho Animate (`clip_vision_h`, `sam2`, `dwpose`) | **P05** — chưa tra được, không nằm trong kho Comfy-Org |
| Fun-VACE có template dùng được không | **P07**, chỉ khi Animate hỏng |
