# DỮ LIỆU ĐÃ ĐO — nguồn duy nhất cho mọi con số

Cập nhật 07/09/2026.

⛔ **Luật của tệp này.** Mọi số ở đây kèm **ngày** và **cách đo**. Tài liệu khác
**trỏ tới đây**, không chép số sang. Chương trình V3 đã mất hai ngày vì một bảng
chép tay không tự biết nó đã cũ.

⚠️ Số **chưa đo** thì ghi thẳng là chưa đo. Một ước lượng đội lốt phép đo nguy
hiểm hơn một ô trống.

---

## 1. Thượng nguồn WanGP

| Mục | Giá trị | Đo thế nào |
|---|---|---|
| SHA ghim | `1e1dd2757f24923f008593d9d4ec09062234be20` | `git rev-parse HEAD` trên volume |
| Bản | v12.71 | log khởi động dịch vụ |
| Số định nghĩa model | **226** | đếm `Wan2GP/defaults/*.json` qua S3, 07/09 |
| Số tài liệu | **26** | đếm `Wan2GP/docs/`, 07/09 |
| Bộ triển khai chính chủ | `Dockerfile` · `entrypoint.sh` · `run-docker-cuda-deb.sh` · `setup_config.json` | liệt kê gốc kho |

### Họ model đông nhất

`ltx2` 23 · `flux` 17 · `hunyuan` 16 · `vace` 14 · `minimax` 12 · `ace_step` 9 ·
`i2v` 9 · `k5` 9 · `z_image` 9 · `qwen_image` 8 · `t2v` 7 · `ovi` 6 · `krea` 4 ·
khác 43.

---

## 2. Mặc định thật của WanGP cho `t2v_2_2`

Dựng lại **ngoại tuyến** bằng bốn tầng của `get_factory_settings()`, đối chiếu
từng khoá — `tests/test_726_lttvideo_ho_so_bam_wangp.py` cưỡng chế.

| Khoá | Giá trị | Nguồn |
|---|---|---|
| `resolution` | **`832x480`** | `wgp.py:3219` — 720p **chỉ khi** tên model chứa `"720"` |
| `num_inference_steps` | **30** | `models/_settings.json` |
| `video_length` | 81 khung | `models/_settings.json` |
| `fps` | **16** | `wan_handler.py:359` |
| `frames_minimum` / `frames_steps` | 5 / 4 | `wan_handler.py:365` |
| `guidance_scale` / `guidance2_scale` | 4 / 3 | `defaults/t2v_2_2.json` |
| `guidance_phases` / `switch_threshold` | 2 / 875 | `defaults/t2v_2_2.json` |
| `flow_shift` | 12 | `defaults/t2v_2_2.json` |
| `sample_solver` | `unipc` | `wan_handler.py:1255` |
| `sliding_window` | **có** | `wan_handler.py:368` |
| `vae_upsampler` | `[1, 2]` | `wan_handler.py:341` — **chỉ dùng lúc sinh**, không dùng cho hậu kỳ |

⇒ 81 khung ÷ 16 fps = **5,06 giây**. 15 giây ⇒ **241 khung** (`5 + 4k` hợp lệ).

---

## 3. Máy C-CLOUD

### Pod đang dùng *(tạo 07/09)*

| Mục | Giá trị |
|---|---|
| Network volume | `uizchbiet5` (`lttv-models-v1`), **300 GB**, `US-KS-2` |
| Pod | **`s6bbn2cip61wo3`** (`lttv-wangp-v1`) |
| GPU | **NVIDIA H100 PCIe 80 GB** — SM **9.0** |
| Giá | **$2,89/giờ** (`costPerHr`) |
| Ảnh container | `nvidia/cuda:13.0.1-cudnn-devel-ubuntu22.04` |
| Cổng mở | **`8888/http`** · `22/tcp` |
| Driver | **580.159.04** — đỡ tới **CUDA 13.0** |
| RAM · vCPU | 251 GB · 16 |

🔴 **A100 đã hết hàng ở `US-KS-2`** (đo 07/09: cả `A100-SXM4-80GB` lẫn
`A100 80GB PCIe` đều `KHONG CO`). Danh sách `gpuTypeIds` ưu tiên đã cứu — rơi
xuống H100.

🔴 **`lowestPrice` báo $1,99, `costPerHr` thật là $2,89** — lệch **45%**. Bẫy này
đã ghi ở §5② của `TAI_NGUYEN_VA_CACH_DUNG_LAI.md` với biên độ nhỏ hơn ($1,39 vs
$1,59); nay biên độ lớn hơn hẳn. **Chỉ tin `costPerHr`.**

⚠️ H100 là **SM 9.0**, A100 là **8.0**. Mọi chỗ gán cứng arch đều sai khi rơi
card — `cai_dat.sh` nay đo bằng `nvidia-smi --query-gpu=compute_cap` và **dừng
hẳn** nếu không đo được, thay vì rơi về một mặc định im lặng.

### Pod cũ *(A100, đã tắt)*

`bly29qwp5bum3r` — A100 SXM 80 GB, $1,59/giờ, ảnh `cuda:12.8.1`, 85,09 GB VRAM,
32 vCPU. **`EXITED`**. Mọi phép đo ở §4 lượt 1–2 chạy trên máy này.

### Bộ Python hiện tại — và vì sao nó lệch

| | Hiện có | WanGP phát hành nhân GGUF cho |
|---|---|---|
| Python | **3.10** | 3.11 · **hoặc** 3.10 |
| torch | **2.10.0** | 2.10.0 · **hoặc** 2.7.1 |
| CUDA | **12.8** | **13.0** · hoặc 12.8 |

Bộ ta = `py3.10 + torch2.10 + cu128` ⇒ **không khớp bộ nào**, nên log ghi
`[GGUF][llama.cpp CUDA] kernels unavailable, using fallback`. Bộ này do **chính
`Dockerfile` của WanGP** tạo ra.

### Nơi model thật sự nằm

| Thư mục | Đo 06–07/09 |
|---|---|
| `/data/Wan2GP/ckpts/` | **44,8 GB**, 113 tệp ← model ở đây |
| `/data/ckpts/` | **rỗng** (tôi tạo nhầm) |
| `/data/hf/` | **rỗng** |

| Tệp | Cỡ |
|---|---|
| `wan2.2_text2video_14B_high_quanto_mbf16_int8` | 14,90 GB |
| `wan2.2_text2video_14B_low_quanto_mbf16_int8` | 14,90 GB |
| `umt5-xxl` (text encoder) | 6,73 GB |
| `xlm-roberta-large` (CLIP) | 2,39 GB |
| `depth_anything_v2_vitl` · `sam_vit_h` | 1,34 + 1,28 GB |

⭐ Hai tệp 14,9 GB là **hai chuyên gia MoE** (high/low-noise) — `URLs` và `URLs2`
của `t2v_2_2.json`, đổi nhau ở `switch_threshold: 875`. Không phải bản sao.

`umt5-xxl` và CLIP **dùng chung** cho `i2v_2_2` / `vace_14B` ⇒ ba model video
**không cộng thẳng**.

---

## 4. Phép đo sinh video

| | Lượt 1 (06/09) | Lượt 2 — E2E (06/09) |
|---|---|---|
| Độ phân giải | 1280×720 | **832×480** |
| Bước | 20 | **30** |
| Profile | 4 | **1** |
| Khung | 81 | 81 |
| **Giây/bước** | **79,8** | **25,8** |
| Tổng | 2.101,7 s | **1.269,8 s** |
| VRAM đỉnh | 14,08 GB | *chưa đo lại* |
| Tệp ra | 16,18 MB | *chưa đo* |

⚠️ Lượt 1 **không dùng để tính giá**: nó chạy ở ba tham số nay đã đổi hết, và
**thiếu TF32** (chín biến của `entrypoint.sh` chưa được đặt lúc đó).

### Thời gian khởi động — profile 1

| Bước | Giây |
|---|---|
| `POST /pods/{id}/start` → container chạy | ~40 |
| `cai_dat.sh` lành lại nửa tạm (apt) | ~40 |
| nạp + ghim model vào RAM dành riêng | **~450** |
| **tổng trước khi sinh được** | **~530 (≈9 phút)** |

⭐ Profile 1 ghim `transformer` · `transformer2` · `vae` · `text_encoder`
(~37 GB) vào RAM dành riêng, đọc từ **ổ mạng**. Trả **một lần**; job sau bỏ qua.

---

## 5. Cầu nối LTT ↔ C-CLOUD — đã chạy thật

7 thao tác: `/health` `/submit` `/progress` `/cancel` `/result` `/tai` `/cleanup`.
E2E 06/09 `thanh_cong=true`, tiến độ khớp **chính xác** hai phía
(`buoc=2/30` ↔ `2/30 [00:56<12:48]`).

### Bốn cái bẫy đã trả giá

| Bẫy | Sự thật |
|---|---|
| Cổng | pod chỉ mở **8888**; nghe cổng khác thì log **sạch** mà máy A không gọi tới được |
| Cloudflare | proxy RunPod chặn UA mặc định của `urllib` → **403 `error code: 1010`**; đổi UA thì 200 |
| Nạp model lười | `/submit` gọi `init()` ⇒ timeout; nâng timeout **không** cứu được vì proxy có trần riêng |
| `san_sang` | `init()` xong **không** nghĩa là sinh được ngay — trọng số nạp ở `submit_task` đầu tiên |

### Vòng đời pod

| Lệnh | Hệ quả |
|---|---|
| `POST /pods/{id}/restart` | **GIỮ** card — dùng cái này để nạp script mới |
| `POST /pods/{id}/stop` | **NHẢ** card; 06/09 mất hơn một giờ mới thuê lại được |
| `PATCH /pods/{id}` | **không nhận** `gpuTypeIds` (400) — chỉ đặt được lúc tạo |

---

## 6. Tiền

| Mục | Giá trị |
|---|---|
| Số dư RunPod (07/09) | ~$39,5 |
| Đã tiêu cho V2.1 | ~$5,0 / **$6,00** chủ dự án duyệt |
| Sàn không được tiêu | **$31,50** — về $0 thì RunPod **xoá volume** |
| Giá bán | **30 credit / giây video** (phẳng, chỉnh ở `cost.py`) |

⚠️ Dòng *"Đã tiêu"* của RunPod **trễ 20–60 phút**. Số tin được là **độ giảm số
dư**.

---

## 6b. Bộ mở rộng prompt — đọc từ nguồn, và đo trên volume *(07/09)*

### Đánh số họ model — `shared/prompt_enhancer/qwen35_vl.py`

```python
def get_qwen35_prompt_enhancer_variant(model_no) -> str:
    return {3: QWEN35_VARIANT_4B, 4: QWEN35_VARIANT_9B,
            5: QWEN38_VARIANT_27B}[int(model_no)]
```

cộng `loader.py:44,54` cho hai số đầu:

| `enhancer_enabled` | họ | ghi chú |
|---|---|---|
| `0` | tắt | |
| `1` | Florence2 + Llama 3.2 | |
| `2` | Florence2 + Llama Joy | |
| `3` | Qwen3.5-4B Abliterated | **không** hỗ trợ speculative decoding (`config.py`) |
| **`4`** | **Qwen3.5-9B Abliterated** | ← ta chọn; speculative cần ≥ 12 GB VRAM |
| `5` | Qwen3.8-27B Uncensored | speculative cần ≥ 24 GB; **đang chặn bởi lỗi cuBLAS** |

Ngữ nghĩa khoá `prompt_enhancer` mỗi lượt: `wgp.py:6561` đọc `"I"` để biết có đưa
`image_start` vào bộ mở rộng; `wgp.py:3118-3121` tự nâng `"I"` → `"TI"`.

### `wgp_config.json` thật trên volume — 4 khoá, 3 đang sai với máy này

| khoá | đo được | cần | vì sao |
|---|---|---|---|
| `enhancer_enabled` | `5` | `4` | 27B đang chặn |
| `prompt_enhancer_quantization` | `"gguf"` | `"quanto_int8"` | nhân GGUF CUDA không nạp được trên py3.11/cu130 |
| `enhancer_mode` | *vắng* ⇒ `1` | `0` | `1` = chỉ chạy khi bấm nút Gradio; đường API bị bỏ qua **im lặng** |
| `prompt_enhancer_speculative_decoding` | `2` (auto) | `0` | auto + 99 GB ⇒ tự bật đường chưa từng chạy |

Sửa bằng `tools/wangp/cau_hinh_enhancer.py` *(mặc định xem, `--ghi` mới ghi;
từ chối ghi khi pod đang chạy)*.

⚠️ Cũng đo được: tệp live có `"checkpoints_paths": ["ckpts", "."]`, trong khi
   `tools/wangp/wgp_config.json` của kho ghi `["/data/ckpts", "ckpts", "."]`.
   WanGP **tự ghi đè** tệp này lúc khởi động (`wgp.py:2661`), nên bản trong kho
   là bản *gieo hạt*, không phải bản đang chạy. Không hỏng — cwd là
   `/data/Wan2GP` nên `"ckpts"` vẫn trỏ đúng chỗ 44,8 GB — nhưng đừng đọc tệp
   trong kho rồi tưởng đó là cấu hình thật.

---

## 7. Chưa đo — đừng trích như thể đã đo

- cỡ tải `i2v_2_2` · `vace_14B` · `Qwen3.8-27B` (GGUF Q4)
- cỡ tải **`Qwen3.5-9B Abliterated` Int8** — thứ ta sẽ thật sự tải ở đợt B
- bộ mở rộng có chạy được trên py3.11/cu130 không *(chưa từng nạp một lần nào)*
- giây/bước khi bật TF32 + `--compile` + `--teacache`
- giây/bước ở 241 khung (3–4 cửa sổ trượt)
- VRAM đỉnh ở profile 1
- thời gian và VRAM của một lượt Upscale `lanczos*2`
- bộ nâng cấp nào máy thật có (`upsampler_api` trả về gì)

---

## 9. 🔴 `CUBLAS_STATUS_INVALID_VALUE` là đặc thù **cu130** — đừng đi nâng driver

**Đo 08/09/2026.** Đây là mục viết cho **phiên sau**, vì triệu chứng của lỗi này
đẩy người ta đi đúng hướng sai.

### Triệu chứng

`torch.einsum("binc,bjnc->bnij")` — một phép nhân ma trận **trần**, ngoài WanGP
hoàn toàn — ném `CUBLAS_STATUS_INVALID_VALUE` ở **cả ba** kiểu `bf16`, `fp16`,
`fp32`.

### ⛔ Vì sao nó đẩy ta đi sai hướng

Mọi dấu hiệu đều chỉ về phía driver, và **tất cả đều bình thường**:

| Thứ | Giá trị | Kết luận sai mà nó gợi ý |
|---|---|---|
| driver | `580.159.04`, khai CUDA 13.0 | *"driver hỗ trợ rồi, chắc do WanGP"* |
| card | H100 NVL, arch `9.0` | *"đúng kiến trúc đã biên dịch"* |
| torch | `2.10.0+cu130` | *"khớp ảnh container"* |

⇒ Người đọc bảng này sẽ đi **nâng driver** hoặc đi soi WanGP. Cả hai đều phí.

### Phép đo dứt điểm

Dựng pod mới, đổi **một** biến — ảnh container `cuda:13.0.1` → `cuda:12.8.1` —
giữ nguyên volume, model, mã, kiến trúc GPU:

```
pod rappv9risxm802 · image cuda:12.8.1 · H100 NVL · $3,19/h
30/30 buoc inference -> decoding -> xong
3.291.112 byte · header \x00\x00\x00 ftypisom   (MP4 that)
710 giay cho 5 giay video @ 480p / 30 buoc
```

⇒ **Không phải WanGP, không phải model, không phải mã ta, không phải driver.**
  Đặc thù stack **cu130**.

### 🔑 Ba điều rút ra

1. **Gặp lỗi này thì HẠ CUDA, đừng nâng driver.** Driver 580 hỗ trợ CUDA 13 —
   đó là sự thật, và nó không liên quan.
2. **Bốn chỉ dấu cùng "bình thường" không phải bằng chứng là không có gì sai.**
   Chúng chỉ nói bốn thứ ấy không sai.
3. **`co_moi_truong_ben()` từng KHÔNG kiểm bản CUDA của torch** — bốn điều kiện
   cũ (python · kho · kiến trúc GPU · `import torch`) đều xanh khi đổi ảnh
   container. Nay có điều kiện thứ năm `_CUDA_TORCH`, đo bằng chính
   `torch.version.cuda` chứ không bằng **tên ảnh**: một ảnh `cuda:12.8` vẫn có
   thể chứa một bánh xe cu130.

### Số phụ, cho lúc thương mại hoá

**~$0,63 / video 5 giây** @ 480p / 30 bước trên H100 NVL $3,19/h. *(Giá vốn
đang hoãn theo quyết định chủ dự án — ghi để dùng sau, không dùng chặn gì.)*
