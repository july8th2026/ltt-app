# SOÁT TÍNH NĂNG WanGP → THIẾT KẾ GUI

Ngày 07/09/2026. Trả lời bốn câu của chủ dự án, và sửa **một khuyến nghị sai**
tôi đưa ở `QUYET_DINH_DA_KHOA_V1.md` §3.

---

## 1. 🔴 SỬA A5 — WanGP **không** chỉ có đường CLI

Hôm qua tôi trả lời: *"WanGP chỉ có ba engine Codex / Claude Code / OpenCode,
đều là CLI"*. **Đó là câu trả lời thiếu.** Ba engine ấy là đường **remote**;
`PROMPTS.md` §*Prompt Enhancer Families* cho biết WanGP còn có bộ mở rộng
**chạy tại chỗ**:

```
Llama 3.2 · Llama Joy · Qwen3.5-4B Abliterated · Qwen3.5-9B Abliterated
                                              · Qwen3.8-27B Uncensored
```

⇒ **`Qwen3.8-27B` mà anh nhắc là có thật, là lựa chọn hạng nhất của WanGP, chạy
thẳng trên C-CLOUD.** Không cần CLI, không cần `Deepy Prime`, **không cần nạp
API nào**.

⭐ Tôi đã khuyến nghị đi đường LLM nội bộ LTT **vì chỉ đọc `REMOTE_LLMS.md` mà
chưa đọc `PROMPTS.md`** — đúng lỗi anh đã chỉ ra một lần: dựng khuyến nghị trên
một phần tài liệu rồi gọi đó là kết luận.

### Và nó **đúng là VLM**, không chỉ là LLM

`PROMPTS.md` §*Based On Images Prompts Content*:

> *"Start from a portrait or reference image, **let the enhancer read the
> image**, then have it write a motion prompt that fits what is actually
> visible."*

Ba chế độ: theo **chữ** · theo **ảnh** · theo **cả hai**. Đây **chính là** cơ chế
Seedance: người dùng ném vào một tấm ảnh với vài chữ, hệ thống tự hiểu.

### ⛔ Nhưng có một trở ngại thật: nhân GGUF

`Qwen3.8` dùng **trọng số GGUF**. Log pod ngày 06/09:

```
[GGUF][llama.cpp CUDA] kernels unavailable, using fallback
```

`INSTALLATION.md` phát hành nhân GGUF CUDA cho **đúng hai bộ**:

| Bánh xe | Python | torch | CUDA |
|---|---|---|---|
| `torch210cu130py311` | 3.11 | 2.10.0 | **13.0** |
| `torch271cu128py310` | 3.10 | **2.7.1** | 12.8 |

Pod ta: Python **3.10** · torch **2.10.0** · CUDA **12.8** ⇒ **không khớp bộ
nào**. Và nghịch lý là bộ ấy do **chính `Dockerfile` của WanGP** tạo ra —
`setup_config.json` thì chỉ liệt kê bánh xe `py311/cu130`.

### ✅ Nâng pod lên đúng bộ WanGP đề xuất — **làm được**, và **bây giờ là lúc rẻ nhất**

Sự thật quyết định, đọc từ `nvidia-smi` trong `install.log`:

```
Driver Version: 580.159.04     CUDA Version: 13.0
```

⇒ Driver của máy chủ **đỡ được CUDA 13**. Đường chính chủ của WanGP
(`py3.11.14` + `torch 2.10.0+cu130`) **chạy được trên đúng cái card này**.

🔑 **Và cái card đã nhả rồi.** Pod đang `EXITED` theo `B1`, nên rủi ro "thuê lại
không được" ta **đã gánh sẵn**. Đổi ảnh container lúc này tốn thêm **~0** rủi ro;
để sau mới đổi thì phải gánh lần nữa.

🔑 **44,8 GB trọng số model KHÔNG phải tải lại.** Chúng là `safetensors`, không
phụ thuộc phiên bản Python hay CUDA. Chỉ dựng lại **môi trường Python**.

| | Đường | Đổi lại |
|---|---|---|
| ① | Giữ nguyên, dùng **Qwen3.5-9B Int8** | `Int8` không phải GGUF ⇒ né vấn đề. Nhưng **bỏ 27B**, và giữ mãi một bộ nằm ngoài ma trận của WanGP |
| ② | Giữ ảnh `cu12.8`, hạ **torch 2.7.1** | khớp bánh xe GGUF, nhưng đây là hàng *"GTX 10xx"* của `INSTALLATION.md` — lùi hai đời torch để chạy card 2026 |
| ③ | **Ảnh CUDA 13 + py3.11.14 + torch 2.10.0+cu130** | bộ **chính chủ**, đúng bánh xe GGUF mà `setup_config.json` phát hành. Trả giá một lần: dựng lại venv |

*Đề xuất đổi thành **③**.* Lý do ①/② từng hấp dẫn là *"đừng đụng vào thứ đang
chạy"* — nhưng thứ đó **đang không chạy** (pod đã tắt), nên lập luận ấy mất hiệu
lực.

**Các bước, và chỗ trả giá:**

1. `DELETE` pod cũ → `POST /pods` với ảnh **CUDA 13 devel**, kèm `gpuTypeIds`
   **cả danh sách** (§3 của `TAI_NGUYEN_VA_CACH_DUNG_LAI.md`), ghim
   `dataCenterIds` về `US-KS-2` để gắn được volume.
2. `cai_dat.sh` mới: **miniconda trên `/data`** → `python=3.11.14` → `torch
   2.10.0 --index-url .../cu130` → `requirements.txt` → SageAttention → **bánh
   xe GGUF `py311/cu130`**. Đúng từng dòng `INSTALLATION.md`.
3. Dựng lại venv: **~40–60 phút GPU ≈ $1,0–1,6**.
4. `ckpts/` **giữ nguyên** — không tải lại 44,8 GB.

⚠️ Ba điều chưa biết, phải kiểm lúc làm chứ không đoán trong tài liệu:
- ảnh CUDA 13 **chính xác nào** RunPod kéo được (thử `13.0.x-cudnn-devel`);
- SageAttention có biên dịch sạch với `nvcc` 13 không;
- venv cũ (py3.10) **giữ lại** cho tới khi bộ mới nghiệm thu xong — không xoá.

⛔ Bước 1 là **xoá một tài nguyên cloud**. Theo ràng buộc anh đặt, tôi **không tự
làm**; chờ anh duyệt.

---

## 2. Soát tính năng WanGP — **226 định nghĩa model**

Đếm được trên volume: `Wan2GP/defaults/` có **226** tệp. Theo họ:

| Họ | Số bản | Họ | Số bản |
|---|---|---|---|
| `ltx2` | 23 | `z_image` | 9 |
| `flux` | 17 | `qwen_image` | 8 |
| `hunyuan` | 16 | `t2v` | 7 |
| `vace` | 14 | `ovi` | 6 |
| `minimax` | 12 | `krea` | 4 |
| `ace_step` | 9 | *(khác)* | 43 |
| `i2v` · `k5` | 9 mỗi | | |

### Phân loại theo **thứ người dùng nhận được**

WanGP tự phân loại bằng `metadata.main_output` (`SETTINGS.md`) — ta dùng chính
nó, không tự nghĩ bảng:

| Loại đầu ra | WanGP làm được gì | Ví dụ |
|---|---|---|
| **Video** | sinh từ chữ / ảnh / video; nối cửa sổ; điều khiển tư thế–chiều sâu–biên; outpaint | `t2v_2_2` · `i2v_2_2` · `vace_14B` · `ltx2` |
| **Video + tiếng** | sinh hình và nhạc/thoại trong **một** lượt | `ltx2` · `ovi` |
| **Video từ người** | chuyển động, thay diễn viên, giữ nhận dạng khuôn mặt | `animate` · `lynx` · `scail2` |
| **Video nói** | khớp môi nhiều người, hội thoại dài | `multitalk` · `infinitetalk` |
| **Ảnh** | sinh, sửa, inpaint/outpaint, chữ trong ảnh | `qwen_image_edit` · `z_image` · `krea2` |
| **Giọng nói** | nhân bản giọng, hội thoại hai người, cảm xúc | `qwen3_tts` · `index_tts2` |
| **Nhạc / âm thanh** | bài hát có lời, nhạc nền, hiệu ứng | `ace_step` · `stable_audio3` |
| **Hậu kỳ** | nâng độ phân giải, nội suy khung, ghép tiếng | `lanczos` · `rife` · MMAudio |

---

## 3. 🔴 Quyết định GUI lớn nhất: **một hộp không ôm được tám loại đầu ra**

Composer phẳng kiểu Seedance hoạt động vì Seedance **chỉ làm video**. Suy ra
*"người này muốn một bài hát"* từ một câu chữ là đoán, và đoán sai thì đốt 13
phút GPU của khách.

⇒ **Tầng trên cùng chọn THỨ MUỐN TẠO, tầng dưới phẳng tuyệt đối.**

```
[ Video ]  [ Ảnh ]  [ Giọng nói ]  [ Nhạc ]      <- san pham, KHONG phai che do engine
    |
    +-- mot o nhap:  prompt  +  keo tha media (anh/video/am thanh)
    +-- ba nut don:  Ti le  ·  Do dai  ·  Tao
    +-- he thong tu chon model theo `metadata.media_inputs`
```

⭐ Người dùng vẫn **không bao giờ** thấy `t2v` / `i2v` / `vace` / `animate`.
Chọn "Video" không phải chọn chế độ engine — nó là chọn **sản phẩm**, y như
Seedance là một sản phẩm video chứ không phải một sản phẩm đa phương tiện.

📌 Và cách chia này **là của WanGP**: `metadata.main_output` chia đúng bốn nhóm
ấy. Ta đọc, không phát minh.

**V1 dựng tab `Video`.** Ba tab kia là app riêng sau này, dùng lại toàn bộ hạ
tầng (cầu nối, điều phối pod, credit, R2) — thêm tab là **thêm dữ liệu**, không
sửa kiến trúc.

---

## 4. Model cần tải — theo đúng tiêu chí đã khoá

| Việc người dùng làm | Model | Trạng thái |
|---|---|---|
| gõ chữ → video | `t2v_2_2` | ✅ **đã có** (29,8 GB hai chuyên gia MoE) |
| đính **ảnh** → video | `i2v_2_2` | ⬇️ cần tải |
| đính **video** → sửa/điều khiển | `vace_14B` | ⬇️ cần tải |
| mở rộng prompt + **đọc ảnh** | `Qwen3.8-27B Uncensored` (GGUF Q4) | ⬇️ cần tải, **sau khi nâng bộ** |
| nút **Upscale** | `lanczos*2` | ✅ không cần model |
| Upscale chất lượng cao | `flashvsr*2` / `coz*4` | ⬇️ tuỳ chọn |

Encoder dùng chung (`umt5-xxl` 6,73 GB, CLIP 2,39 GB) **đã có** và **dùng lại**
cho cả `i2v_2_2` lẫn `vace_14B` — nên ba model video **không** cộng thẳng.

Volume **300 GB**, đang dùng **44,8 GB** ⇒ dư sức.

⚠️ Con số cho `i2v_2_2` / `vace_14B` / Qwen3.5-9B là **ước theo lớp model**,
chưa đo. Đo bằng cách tải rồi `du -sh` — không đoán tiếp trong tài liệu.

---

## 5. Sửa lại bảng việc

| # | Việc | GPU |
|---|---|---|
| V1 | Ảnh chụp `metadata` 226 model tại SHA ghim, làm fixture | ❌ |
| V2 | Composer: đính media → lọc model theo `metadata` → `apply_media_flag_defaults()` | ❌ |
| V3 | Điều phối viên pod (bật/chờ/tắt) + B3 hoàn credit | ❌ |
| V4 | Lịch sử · tiến độ · huỷ · giữ 3 ngày · lưu prompt | ❌ |
| V5 | Thao tác thứ 7 `/hau_ky` + nút Upscale (`lanczos*2`) | ❌ |
| **V0** | **Nâng pod lên bộ chính chủ** (CUDA 13 · py3.11.14 · torch cu130) | ⚠️ dựng lại venv |
| **V6** | **Bộ mở rộng prompt CỦA WanGP** (`Qwen3.8-27B`) — ~~LLM nội bộ LTT~~ | ⚠️ tải model |
| V7 | Độ dài tới 15s: truyền `"15s"` | ❌ |
| V8 | Tải `i2v_2_2` + `vace_14B` | ⚠️ cần pod |
| V9 | Nghiệm thu đầu-cuối | ✅ |

🔴 **V6 đổi bản chất.** Bản cũ: LTT gọi LLM nội bộ rồi gửi prompt đã sửa —
một lớp LTT **tự xây**. Bản mới: bật một tuỳ chọn **có sẵn của WanGP**. Ít mã
hơn, ít đường mạng hơn, và đúng luật *"triển khai như WanGP triển khai"*.
