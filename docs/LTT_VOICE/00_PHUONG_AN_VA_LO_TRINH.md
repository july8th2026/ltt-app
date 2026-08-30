# LTT VOICE — phương án và quy trình triển khai đầy đủ (MÁY A, GPU-first)

> Ngày lập: **2026-08-30**. Nhánh: `admin-mvp-v3`.
> Đích: **MÁY A — `C:\LTTPlatform`**, cùng máy với web và worker.
> Chính sách tài nguyên chủ sản phẩm chốt: **RAM sẽ nâng, dùng thoải mái. Việc gì
> cần GPU thì đẩy hết lên GPU.**
> Trạng thái: **KẾ HOẠCH — chưa viết một dòng mã nào.**

Nhãn: **[V]** verified — đọc được từ mã nguồn thật (có trích đường dẫn) ·
**[S]** suy ra · **[Đ]** đề xuất.

---

## 0. Hai lần sửa, và một khẳng định sai phải rút lại

### 0.1 Sửa lần một — máy A chứ không phải máy B

Bản đầu đặt engine lên máy B vì đó là hình dạng của H37 (ảnh) và H38 (LLM). Sai
đích. Sửa xong ở §1.

### 0.2 🔴 Sửa lần hai — **"streaming chỉ chạy trên CPU/ONNX" là SAI**

Bản trước tôi viết: *"Streaming CHỈ chạy trên ONNX/CPU"* và dựng cả QĐ-5 trên đó.
**Đó là sai.** Tôi lấy một câu khuyến nghị trong README làm ràng buộc năng lực,
thay vì mở mã nguồn ra đọc.

Mã nguồn nói ngược lại, ngay tại chỗ:

```python
# src/vieneu/v3turbo.py — infer_stream()
# Prefer the engine's native frame-level streaming (low first-audio latency);
# both the PyTorch and ONNX engines expose infer_stream. Fall back to one
# full infer per chunk if not available.
stream_fn = getattr(self.engine, "infer_stream", None)
```

Và cả hai engine đều có thật:

| Engine | Tệp | Dòng |
|---|---|---|
| PyTorch / GPU | `src/vieneu/_v3_turbo_engine/inference_v3_turbo.py` | `def infer_stream(..., chunk_frames: int = 25, ...)` |
| ONNX / CPU | `src/vieneu/_v3_turbo_engine/onnx_runtime_lite.py` | `def infer_stream(...)` |

README khuyên `backend="onnx"` cho realtime vì **TTFA thấp hơn với câu ngắn** —
đó là **khuyến nghị hiệu năng, không phải giới hạn năng lực**.

⛔ Bài học ghi lại để không lặp: đây đúng cái bẫy mà chính pack V2 cảnh báo ở §2.3
(*"`config.yaml` khai `supports_streaming: false` trong khi mã có streaming"*) — và
tôi vẫn dính, chỉ ở một tầng khác: **một câu văn xuôi trong README cũng là
metadata.** Năng lực phải đọc từ **mã** rồi **đo lúc chạy**, không đọc từ chữ.

### 0.3 Hệ quả của chính sách tài nguyên mới

| Bản trước | Bản này |
|---|---|
| Dịch vụ **ấm CPU** cho câu ngắn + **tiến trình một lần trên GPU** cho long-form — hai đường, hai khuôn | **Một dịch vụ ấm duy nhất, chạy GPU**, phục vụ cả ba: ngắn · streaming · batch |
| RAM 32 GB là **câu hỏi chặn** ở V1 | RAM không còn là cổng chặn. Model nhỏ hơn nhiều so với lo ngại (§2.3) |
| Streaming hoãn vì *"phải đổi backend"* | Streaming **không còn bị kiến trúc chặn** — cùng dịch vụ, cùng engine. Hoãn chỉ vì hợp đồng `STREAM` (§4 QĐ-5) |

---

## 1. Logic vận hành máy A — [V] đọc từ mã

### 1.1 Ba dịch vụ đang chạy

`setup/2-cai-dat.ps1` cài đúng ba dịch vụ NSSM, đều lấy biến môi trường từ
`secrets\app.env` qua `AppEnvironmentExtra`:

| Dịch vụ | Chạy gì | Cổng | venv |
|---|---|---|---|
| `LTTStudioWeb` | `uvicorn server.run:app` | `127.0.0.1:8100` | `C:\LTTPlatform\venv` |
| `LTTStudioWorker` | `job_worker.py`, N tiến trình | — | `C:\LTTPlatform\venv` |
| `LTTStudioCodex` | `codex_sidecar_main.py` | `127.0.0.1:8110` | `C:\LTTPlatform\venv` |
| **`LTTStudioVoice`** | **sẽ thêm** — `voice_sidecar_main.py` | `127.0.0.1:8120` | **`vieneu-venv`** |

### 1.2 Đã có tiền lệ venv cách ly

`deploy/windows/install-whisperx-sidecar.ps1` tạo `C:\LTTPlatform\whisperx-venv`
**ngoài `app\`**, idempotent, in đường dẫn python ra để `2-cai-dat.ps1` ghi vào
app.env. Lý do ghi ngay trong tệp: *"WhisperX 3.8.6 requires torch 2.8.x. The
platform venv uses a newer Blackwell torch build, so installing WhisperX in-place
would downgrade and break other GPU apps."*

VieNeu có **đúng cùng xung đột** — xem §2.4. Cùng luật, cùng khuôn tệp, thực thể
thứ hai: **`C:\LTTPlatform\vieneu-venv`**.

### 1.3 Cập nhật xoá trắng `app\`

`update.ps1` dừng **Codex → Worker → Web**, backup, rồi `Move-Item app app.previous`.
Robocopy loại trừ `data secrets logs .venv venv __pycache__ …`.
⇒ Mọi venv, mọi cache model, mọi dữ liệu **phải nằm ngoài `app\`**. Và §7.2 —
đây là chỗ dịch vụ thứ tư sẽ làm **gãy cập nhật** nếu quên.

### 1.4 GPU máy A và cách nền tảng trọng tài

| | |
|---|---|
| Card | **2× RTX 5060 Ti 16 GB** (Blackwell, cu128) |
| Đang chiếm | `autosubvideo` ~6 GB · `upscalevideo` 2 GB (fast) / 12 GB (quality) |
| Trọng tài | `platform_core/gpu_lease.py` — khoá nguyên tử trong CSDL, neo bằng **UUID** |
| Đo chỗ trống | `platform_core/gpu.py` gọi `nvidia-smi --query-gpu=…,memory.free,…` **trực tiếp, mỗi lần** |
| Ghim tiến trình | `gpu.env_for(uuid)` → `CUDA_VISIBLE_DEVICES` |

⭐ **[V] Điểm này giải bài toán "dịch vụ ấm giữ card" mà không cần cơ chế mới.**
Vì `gpu.py` đọc `memory.free` **sống** chứ không đọc một bảng kê khai, một model
thường trú trên card X **tự động** hiện ra thành phần trống ít đi. `gpu_lease` giữ
chỗ dựa trên số đó, nên nó **đã** tính đúng — không phải khai thêm gì, không phải
sửa `platform_core`.

### 1.5 🔴 Bẫy đội hình worker

**[V]** `platform_core/jobs.py:129` — `set(item.manifest.requires).issubset(capabilities)`.

Khai `requires=("voice",)` mà `LTT_WORKER_POOLS` trên production **không** có làn
`voice` ⇒ job nằm `queued` **mãi mãi**. Không lỗi, không cảnh báo,
`/health/ready` vẫn 200.

---

## 2. Nghiên cứu upstream — đọc mã, không đọc mô tả

Tất cả mục dưới đây **[V]**, đọc ngày 2026-08-30 từ
`pnnbao97/VieNeu-TTS` @ `36c4b50` (main, 20/08), tag `v3.3.0`, Apache-2.0.

### 2.1 Bề mặt SDK — và món quà lớn nhất cho kiến trúc

```python
# src/vieneu/factory.py
def Vieneu(mode="v3turbo", **kwargs)          # v3turbo là MẶC ĐỊNH

# src/vieneu/v3turbo.py — class V3TurboVieNeuTTS
__init__(device="auto", dtype="auto", backend="auto",
         precision="int8", max_batch_size=32, ...)
    # backend "auto" → ONNX trên CPU, PyTorch trên GPU; ép được "onnx"|"pytorch"
    # precision CHỈ áp cho đường ONNX (chọn subfolder graph int8 vs fp32)

encode_reference(ref_audio, denoise=True) -> (speaker_emb, ref_codes)   # ⭐
get_preset_voice(name) -> {"speaker_emb": ..., "codes": ...}
add_voice(name, ref_audio, denoise=True, ...)
denoise(ref_audio, out_path=None)
infer(text, voice=<str|dict>, ref_audio=..., batch_size=None, ...)
infer_stream(text, voice=..., max_chars=256, ...)  -> Generator[np.float32]
infer_batch(texts, voice=..., batch_size=None, ...)
```

⭐ **`encode_reference()` trả thẳng `(speaker_emb, ref_codes)` dạng numpy, và
`infer(voice=<dict>)` nhận lại đúng dict đó.**

Nghĩa là: **ta sở hữu trọn vẹn biểu diễn giọng.** Không cần `voices.json` của
VieNeu, không cần `add_voice`/`save_voices`, không phụ thuộc định dạng tệp của
upstream. Ghi danh = gọi `encode_reference` một lần rồi cất hai mảng vào kho của
ta; tạo tiếng = nạp hai mảng đó và truyền vào.

⇒ Bất biến *"đổi engine không đổi `voice_id`"* mà pack đặt lên hàng đầu **được hỗ
trợ trực tiếp bởi API**, không phải một lớp bọc ta tự nghĩ ra.

### 2.2 🔴 CUDA graph — và vì sao tham số sinh mẫu KHÔNG được lộ ra khách

```python
# src/vieneu/v3_turbo_serve/cudagraph.py
"""CUDA-graph capture for the per-frame acoustic step (no C compiler required).
   ...
   Unlike ``torch.compile``, ``torch.cuda.CUDAGraph`` needs no compiler toolchain,
   so it works on Windows + CUDA."""
class CudaGraphedFrame:
    def __init__(self, model, batch_size, *, temperature, top_k, top_p, warmup=3)

# src/vieneu/v3_turbo_serve/engine.py
self._graphs = {}   # (B, temp, top_k, top_p) -> CudaGraphedFrame
```

Hai kết luận, cả hai đều là bằng chứng chứ không phải suy đoán:

1. ⭐ **Đường batch GPU được thiết kế để chạy trên Windows.** Tác giả nói thẳng
   là dùng `torch.cuda.CUDAGraph` thay vì `torch.compile` **chính vì** không cần
   trình biên dịch C. Đây là rủi ro lớn nhất của một kế hoạch GPU-first trên
   Windows, và nó đã được upstream xử lý.
2. 🔴 **Cache graph khoá theo `(B, temperature, top_k, top_p)`.** Mỗi tổ hợp mới =
   một graph mới + một bộ đệm tĩnh + 3 lượt warmup. Cho khách chỉnh
   `temperature`/`top_k`/`top_p` là mời họ **làm nổ cache graph** trên card của ta.
   ⇒ **QĐ-7**: tham số sinh mẫu là **hằng số phía máy chủ**.

### 2.3 Kích thước model — [V] đọc từ HuggingFace API

`pnnbao-ump/VieNeu-TTS-v3-Turbo` @ `2da0efab`, apache-2.0, tổng kho **1.678 MB**.
Nhưng **ta chỉ cần một tập con**:

| Đường | Tệp cần | Tổng |
|---|---|---|
| **PyTorch / GPU** | `update/model.safetensors` 248 MB + `denoiser.onnx` 42,7 + `speaker_encoder.onnx` 28,3 + tokenizer | **≈ 320 MB** |
| ONNX / CPU int8 | `onnx_int8/` (~165 MB) + denoiser + speaker_encoder | ≈ 236 MB |

⇒ **Trọng số nhỏ — hàng trăm MB, không phải hàng GB.** Trên GPU ở bf16, phần
trọng số cỡ vài trăm MB; VRAM thật gồm thêm KV cache, activations và graph tĩnh.
**[S] Dự đoán 1–3 GB, phải đo ở V1** — nhưng nếu đúng thì VieNeu **sống chung
thoải mái** với `autosubvideo` (6 GB) và cả `upscalevideo` quality (12 GB) trên
cùng một card 16 GB.

### 2.4 Cài GPU — [V] **không có extra `[gpu]`**, phải làm tay

`pyproject.toml` ghi thẳng trong chú thích của `dependencies`:

> *"GPU is a manual step (install a CUDA torch + transformers yourself — **there is
> no [gpu] extra**; see [project.optional-dependencies] below)"*

Mục `gpu` trong `[dependency-groups]` là **nhóm của uv cho người phát triển**,
không phải extra của pip. Thứ tự cài đúng (khớp README):

```
pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
pip install "transformers==4.57.6"      # README ghim: "most stable transformers for the GPU SDK"
pip install vieneu==3.3.0
```

Phụ thuộc lõi (torch-free): `sea-g2p>=0.9.0` · `onnxruntime>=1.20` · `numpy` ·
`soundfile` · `soxr` · `kaldi-native-fbank>=1.20` · `tokenizers>=0.20` ·
`huggingface_hub` · `PyYAML` · `gradio>=5.49.1` · `librosa>=0.11.0` · `perth>=0.2.0`.

⇒ **Xung đột với venv nền tảng là thật**: `transformers==4.57.6` ghim cứng, và
`torch==2.8.0` ghim cứng. Venv cách ly là bắt buộc.

### 2.5 ✅ Không cần espeak-ng trên Windows

`sea-g2p` 0.9.1 có **`requires_dist` rỗng** (ngoài extra `dev`) và phát hành wheel
`sea_g2p-0.9.1-cp310-abi3-win_amd64.whl` (27 MB) — Rust, tự chứa.
Biến `PHONEMIZER_ESPEAK_LIBRARY` trong docker-compose là của **đường v1/v2 cũ**.
⇒ **Không có phụ thuộc cấp hệ điều hành nào** cho đường v3 Turbo trên Windows.

### 2.6 🔴 Watermark — lỗi đã truy tới tận gốc, và ta sửa được

`base.py`:

```python
def _init_watermarker(self) -> None:
    try:
        import perth
        self.watermarker = perth.PerthImplicitWatermarker()   # ← AttributeError
    except (ImportError, AttributeError):
        self.watermarker = None                               # ← nuốt im lặng

def _apply_watermark(self, wav):
    if self.watermarker: return self.watermarker.apply_watermark(...)
    return wav                                                # ← trả nguyên xi
```

Đo PyPI ngày 30/08:

| Gói | Mô tả thật |
|---|---|
| `perth` **1.0.0** (thứ `vieneu` khai) | *"Wrapper for `threading.local` with enhanced value accessor"* — **không liên quan âm thanh** |
| `resemble-perth` **1.0.1** (thứ cần dùng) | *"Audio Watermarking and Detection Library"* |

`import perth` **thành công** (gói có thật) nên nhánh `ImportError` không chạy;
`perth.PerthImplicitWatermarker` không tồn tại → `AttributeError` → bị nuốt. Không
một dòng log. Mặc định `apply_watermark=True` ở khắp nơi.

⇒ **Mọi lượt sinh đều KHÔNG có watermark, trong khi API nói là có.**
⇒ Cách sửa của ta, hai bước, cả hai bắt buộc:
1. trong `vieneu-venv`: **gỡ `perth`, cài `resemble-perth`** (cùng tên module
   `perth` — không gỡ trước thì xung đột);
2. sidecar **kiểm lúc khởi động** `engine.watermarker is not None` và **chết to**
   nếu không — không đi tiếp trong im lặng như upstream.

### 2.7 🔴 Trôi giọng — con số cụ thể lấy từ chính người dùng upstream

Issue **#168**: tác giả báo đã **sửa xong** drift ngày 05/07. Người thử phản hồi
06/07:

> *"hiện tượng đổi giọng ít xảy ra hơn. Nhưng lỗi sẽ xuất hiện nhiều khi xử lý
> **text dài khoảng 3.000 ký tự trở lên**. Giọng Xuân Vĩnh sẽ dễ bị đổi giọng khác
> (chuyển sang giọng như miền Trung). Các giọng khác đôi lúc đọc sang tiếng khác
> như Thái... chỉ một đoạn rồi quay lại Việt."*

Và **#168** ban đầu: `"chưởng môn"` → `"trưởng môn"` (lẫn `ch`/`tr`).
Issue **#173**: lệch tông/cao độ giữa các câu liền kề khi nhân bản bài dài.

⇒ Ba hệ quả **thiết kế**, không phải ba ghi chú:
1. **Trần ký tự cho MỘT lượt sinh phải nằm sâu dưới 3.000.** Bài dài = **nhiều
   lượt sinh**, không bao giờ một lượt dài (QĐ-8).
2. `ch`/`tr` và tên riêng → **từ điển phát âm** ở V5, có test.
3. Giữ `temperature` thấp và **cố định** giúp giảm lệch giữa các đoạn — trùng đúng
   với QĐ-7 vốn ra đời vì CUDA graph. **Hai lý do độc lập, một quyết định.**

Nhánh `future` mà tác giả nhắc trong #168 **[V] không còn tồn tại** — kho chỉ còn
`main`, tức các bản sửa đã merge. Ghim `main@36c4b50` là đúng.

### 2.8 Bảo hiểm sẵn có của upstream, và cái ta vẫn phải tự làm

```python
# src/vieneu/v3_turbo_serve/engine.py
MIN_FRAMES_PER_PHONE = 0.25
# "Guard chống 'chunk câm': một row khỏe sinh >= ~0.4 frame trên mỗi ký tự
#  phoneme; dưới 0.25 gần như chắc chắn là EOS sớm / cụt giữa chừng -> sinh lại."
```

Upstream **đã** tự sinh lại đoạn câm trong đường batch. Tốt — nhưng ta vẫn phải
tự đo ở tầng của mình, vì `infer` đơn lẻ không đi qua engine batch, và vì quyết
toán tiền của ta dựa trên **thời lượng thật**.

### 2.9 Tham chiếu giao thức streaming — `apps/web_stream.py`

Bản demo FastAPI của upstream (đọc **để học**, không chép vào sản phẩm) đưa ra ba
mẹo dùng được ngay ở V-streaming:

- Phát WAV header với `setnframes(1_000_000_000)` để trình duyệt phát ngay khi
  byte đầu tới, không chờ biết độ dài;
- PCM16: `(f32 * 32767).clip(-32768, 32767).astype(int16)`;
- Đo **TTFA** ngay tại chunk đầu tiên, và RTF = `gen_time / audio_s` ở cuối.

### 2.10 Bài học từ triển khai của cộng đồng

`hoangtung386/vietnamese-tts-local` (self-host FastAPI, GPU + ONNX codec) — dùng
backbone v2 GGUF nên không phải khuôn của ta, nhưng ba điều dùng được:

- **"Chỉ chạy một worker"** — họ viết thành luật vận hành. Trùng QĐ-6 của ta.
- **Ghim `==` cho mọi phụ thuộc trực tiếp + lockfile** cho phụ thuộc bắc cầu.
- **Tải model lần đầu ~500 MB rồi chạy offline** nếu giữ cache HF.
  ⇒ Bộ cài của ta phải **làm ấm cache lúc cài**, và đặt `HF_HOME` **ngoài `app\`**.

`docs/Deploy.md` của upstream chỉ có đường **Docker + NVIDIA Container Toolkit
(Linux)**, và `serve.py` là máy chủ **LMDeploy cho v2**.
⇒ **[V] Upstream không có câu chuyện phục vụ v3 Turbo trên Windows.** Ta tự dựng
sidecar — đây là kết luận có bằng chứng, không phải lựa chọn tuỳ tiện.

---

## 3. Bảng quyết định

### QĐ-1 · Hình dạng → **một app + một sidecar. KHÔNG provider, KHÔNG `api_pool`.**

| Phương án | Phán quyết |
|---|---|
| Provider kiểu `ltt_image` + khoá trong `api_pool` | ❌ `api_pool` để xoay khoá / đo hạn mức / cooldown nhà cung cấp — **localhost không có cả ba**. Đổi lại phải mở rộng enum hạng mục khoá ⇒ sửa `platform_core` cho thứ không dùng |
| Gọi thẳng `vieneu` trong worker | ❌ Xung đột phụ thuộc (§2.4); N worker = N bản model |
| ✅ **`apps/ltt_voice/` + `voice_sidecar/` nghe loopback** | ✅ Khuôn `LTTStudioCodex` đã chạy thật. **Không sửa `platform_core/` hay `server/` một dòng** |

### QĐ-2 · Nơi chạy → **MỘT dịch vụ ấm, GPU/PyTorch, ghim một card**

Chính sách chủ sản phẩm: việc gì cần GPU thì đẩy lên GPU. Bằng chứng ủng hộ:

- **[V]** trọng số chỉ ~320 MB (§2.3) ⇒ VRAM nhỏ, sống chung được;
- **[V]** đường batch dùng CUDA graph và **được thiết kế cho Windows** (§2.2);
- **[V]** `gpu.py` đọc `memory.free` sống ⇒ model thường trú **tự động** được
  `gpu_lease` tính vào, không cần cơ chế mới (§1.4);
- **[V]** `infer_stream` chạy trên cả PyTorch (§0.2) ⇒ **một engine phục vụ cả ba
  loại việc**, không phải chia hai đường như bản trước.

Ghim card bằng `CUDA_VISIBLE_DEVICES` (giá trị lấy từ `gpu.visible_devices_value(uuid)`)
đặt trong `AppEnvironmentExtra` của dịch vụ lúc cài.

⚠️ Giữ **làn CPU/ONNX làm dự phòng có cờ**, không phải làm mặc định: nó là đường
duy nhất còn chạy khi card bận hoặc OOM, và có thể cho TTFA thấp hơn với câu rất
ngắn. **Đo ở V1 rồi mới chọn ngưỡng**, đừng chốt trước.

### QĐ-3 · Định danh → **`vc_<uuid4-hex>`; ta sở hữu biểu diễn**

Nhờ `encode_reference()` (§2.1), biểu diễn giọng là **hai mảng numpy của ta**:
`speaker_emb` + `ref_codes`. Cất ở `platform_core.storage`, tham chiếu bằng một
dòng `voice_repr` ghi rõ `engine · model_repo · revision · fingerprint · status`.

Nâng v3 Turbo → v3 full = **thêm một dòng biểu diễn mới**; `voice_id` không đổi.
⛔ Không bao giờ là: tên hiển thị · khoá trong `voices.json` · đường dẫn checkpoint
· chỉ số preset · chính `speaker_emb`.

### QĐ-4 · Tiền → **theo giây tiếng nói sinh ra thật**

Giữ chỗ theo ký tự × tỉ lệ đã đo (luôn ≥ giá thật) → quyết toán theo thời lượng
`ffprobe` → handler **phải** báo `credit_cost` → không đo được thì **hoàn đủ, thu
0**. Giá vốn = **giây GPU trên 5060 Ti** (điện + khấu hao), vào `gia_von.json`.

### QĐ-5 · Streaming → **hạ từ "chặn kiến trúc" xuống "chờ hợp đồng"**

Sau §0.2, streaming **không còn bị backend chặn**. Nó vẫn ngoài MVP, nhưng chỉ vì
chế độ `STREAM` của nền tảng đòi khai bốn lời hứa (`STREAM_PHAI_KHAI`:
`event_types`, `heartbeat_seconds`, `usage_event`, `cancel_on_disconnect`) và một
lease từ admission plane (Q114).

⇒ Sidecar dựng `/v1/stream` **ngay từ V2** (rẻ — cùng engine, cùng model đã ấm),
để sau MVP chỉ còn việc viết hợp đồng. Năng lực công bố qua `/v1/capabilities`
**bằng phép dò lúc chạy**, không đọc `config.yaml`.

### QĐ-6 · Chặn đồng thời → **ba tầng, cả ba đều cần**

| Tầng | Cơ chế | Chặn gì |
|---|---|---|
| Đội hình worker | làn `voice:1` trong `LTT_WORKER_POOLS` | số job VOICE song song trong worker |
| Admission plane | `admission_resource="vieneu_gpu"`, `admission_slots=1` | **cả ba cửa** job / sync / stream giành cùng một slot (Q114) |
| Sidecar | `max_dong_thoi` → **429 + `Retry-After`** | hàng rào cuối — **429 chứ không bao giờ 5xx** |

⛔ Bỏ tầng nào cũng hỏng theo kiểu riêng: bỏ ① thì N worker cùng gọi; bỏ ② thì cửa
đồng bộ đi vòng qua hàng đợi; bỏ ③ thì một lỗi cấu hình đủ để treo cả card.

### QĐ-7 · 🔴 **Tham số sinh mẫu là hằng số phía máy chủ** — [MỚI]

`temperature`, `top_k`, `top_p`, `repetition_penalty`, `repetition_window`
**không ra hợp đồng công khai và không có trên giao diện**.

Hai lý do độc lập, cả hai có bằng chứng:
1. **CUDA graph cache khoá theo `(B, temperature, top_k, top_p)`** (§2.2) — mỗi tổ
   hợp mới tốn một graph + bộ đệm tĩnh + warmup;
2. **`temperature` cao làm lệch tông giữa các đoạn** (§2.7, #173).

⇒ Chốt một bộ tham số, ghi vào cấu hình sidecar **có phiên bản**, đổi thì phải qua
cổng chất lượng V10. Đây là tham số **chất lượng sản phẩm**, không phải nút vặn
của khách.

### QĐ-8 · 🔴 **Trần ký tự một lượt sinh** — [MỚI]

**[V]** #168: drift bùng lên từ **~3.000 ký tự**. `config.yaml` upstream đặt
`max_chars_per_chunk: 256` và `max_total_chars_streaming: 3000`.

⇒ Trần công bố cho **một lượt** đặt **sâu dưới 3.000** (đề xuất khởi điểm
**1.500**, chốt bằng số đo ở V1/V10). Dài hơn ⇒ **long-form nhiều lượt sinh**, mỗi
lượt cùng một `speaker_emb`/`ref_codes`, ghép bằng ffmpeg.
⛔ Đừng nâng trần để "tiện" — đây là **trần chất lượng**, không phải trần hiệu năng.

---

## 4. Kiến trúc và ba luồng vận hành

```
                    ┌─ Web Studio /ltt-voice   (Jinja + ltt.css, cache-bust)
   KHÁCH ───────────┤
                    └─ /api/v1 tool speech.ltt (ASYNC_JOB, cổng 3 lớp fail-closed)
                              │
   ┌──────────────────────────┼───────────────── MÁY A · C:\LTTPlatform ─────┐
   │                          ▼                                             │
   │  LTTStudioWeb :8100 ──► platform_core/jobs   (HÀNG ĐỢI DUY NHẤT)       │
   │                                │                                        │
   │  LTTStudioWorker (làn voice:1) ┘                                        │
   │        │  apps/ltt_voice/features.py   ← NGHIỆP VỤ, dùng chung mọi cửa  │
   │        │                                                                │
   │        └──► HTTP 127.0.0.1:8120 ──► LTTStudioVoice   [MỘT DỊCH VỤ ẤM]  │
   │                bearer token             vieneu-venv                     │
   │                                         CUDA_VISIBLE_DEVICES=<1 card>   │
   │                                         V3TurboVieNeuTTS(               │
   │                                            backend="pytorch",           │
   │                                            dtype=bf16, max_batch_size)  │
   │                                         ├ /v1/speech   ngắn             │
   │                                         ├ /v1/batch    long-form        │
   │                                         ├ /v1/stream   (sau cờ)         │
   │                                         ├ /v1/enroll   encode_reference │
   │                                         └ /v1/capabilities  dò lúc chạy │
   │                                                                          │
   │  platform_core/  jobs · credit · storage(R2) · upload_sessions          │
   │                  gpu · gpu_lease · leases · media(ffprobe) · i18n       │
   └──────────────────────────────────────────────────────────────────────────┘
      HF_HOME = C:\LTTPlatform\hf-cache      (NGOÀI app\ — sống qua cập nhật)
```

### 4.1 Luồng A — tạo tiếng ngắn (đường chính)

```
1  Web/API   text + voice_id + định dạng
2  features  chuẩn hoá; kiểm QUYỀN SỞ HỮU voice_id; kiểm TRẦN KÝ TỰ (QĐ-8)
3  gia       uoc_tran(ký tự) → credit giữ chỗ, LUÔN ≥ giá thật
4  jobs      quote → approve → hold → queue        (một giao dịch CSDL)
5  worker    claim (làn voice) → admission lease "vieneu_gpu"
6  features  text_pipeline: chuẩn hoá VI/EN + chia đoạn ≤ 256 ký tự
7  storage   nạp speaker_emb + ref_codes của voice_id
8  sidecar   POST /v1/speech  {phoneme-ready text, emb, codes}
              ├─ bận → 429 + Retry-After → nhả lease, xếp lại (KHÔNG coi là hỏng)
              └─ xong → WAV 48 kHz
9  media     ffprobe → THỜI LƯỢNG THẬT
10 storage   put → khoá artifact
11 result    {audio_key, duration_s, credit_cost: gia.tinh(duration_s)}
12 jobs      settle theo credit_cost, HOÀN phần giữ dư
```

⛔ Bước 11 là chốt sinh tử: không báo `credit_cost` thì `job_runner` **thu trọn
phần đã giữ** — im lặng, sổ vẫn cân, khách vẫn mất tiền. Đúng lỗi H37 đã mắc.

### 4.2 Luồng B — ghi danh giọng

```
1  upload_sessions   staging → verify → promote            (đã có sẵn, Q85)
2  audio_input       MIME THẬT (không tin trình duyệt) · thời lượng 3–30 s
                     · clipping · im lặng · một người nói
3  storage           giữ NGUYÊN BẢN bất biến  voice/<owner>/<vc_id>/source.wav
4  consent           ghi thành DỮ LIỆU: ai · khi nào · bản điều khoản nào
                     · hash tệp nguồn
5  job               ltt_voice.enroll — IDEMPOTENT theo hash tệp nguồn
6  sidecar           POST /v1/enroll → encode_reference(denoise=True)
                                     → (speaker_emb, ref_codes)
7  storage           lưu hai mảng đó — KHÔNG BAO GIỜ ra ngoài
8  tables            voice_repr: engine · model_repo · revision · fingerprint
9  tables            voice_profile.status = active   ← CHỈ sau khi (8) ready
```

### 4.3 Luồng C — long-form (V9)

```
1  chia đoạn theo RANH GIỚI NGỮ NGHĨA, mỗi đoạn ≤ trần QĐ-8, số thứ tự bất biến
2  mỗi đoạn = một bản ghi trạng thái riêng
3  gửi theo lô ≤ max_batch_size sang /v1/batch  (một forward, CUDA graph tái dùng)
4  đoạn xong → lưu ngay; chạy lại thì BỎ QUA đoạn đã xong
5  MỌI đoạn dùng CÙNG speaker_emb + ref_codes + CÙNG tham số sinh mẫu (QĐ-7)
6  ghép tất định bằng ffmpeg concat
7  quyết toán theo tổng thời lượng THẬT
```

---

## 5. Cây tệp

### 5.1 Tạo mới

```
apps/ltt_voice/
    manifest.py        job_types · requires("voice") · gpu_vram_mb · credit_cost
                       · ToolSpec speech.ltt · admission_resource · table_prefix
    features.py        NGHIỆP VỤ — mọi cửa gọi vào đây
    jobs.py            handler mỏng: gọi features, dịch lỗi, BÁO credit_cost
    gia.py             MỘT bảng giá · PHIEN_BAN_GIA · bang_gia() · uoc_tran()
    tables.py          voice_profile · voice_ref · voice_repr · voice_consent
    routes.py          CHỈ HTTP
    text_pipeline.py   chuẩn hoá VI/EN + chia đoạn theo trần QĐ-8
    audio_input.py     kiểm tệp tiếng tải lên (đối xứng image_input)
    sidecar_client.py  gọi 127.0.0.1:8120 (khuôn chataistudio/sidecar_client.py)
    dieu_khoan.py      điều khoản + consent, đối chiếu được bằng test
    templates/         ltt_voice_studio.html · _voices.html · _history.html

voice_sidecar/
    server.py          /live · /health · /v1/capabilities · /v1/speech
                       · /v1/batch · /v1/enroll · /v1/stream (sau cờ)
    engine.py          MỘT V3TurboVieNeuTTS ấm · khoá · warmup · đếm đồng thời
                       · KIỂM watermarker KHÁC None lúc khởi động (§2.6)
    tham_so.py         tham số sinh mẫu CỐ ĐỊNH, có phiên bản (QĐ-7)
    ngan_sach.py       từ chối cấu hình CHƯA ĐO trước khi chạm GPU
voice_sidecar_main.py  điểm chạy NSSM (khuôn codex_sidecar_main.py)

requirements-vieneu.txt
deploy/windows/install-vieneu-sidecar.ps1
alembic/versions/xxxx_voice_tables.py

docs/LTT_VOICE/01_KHOA_UPSTREAM.md   bản ghim + bảng đo V1
docs/LTT_VOICE/02_VAN_HANH.md        runbook

tests/  gia · features+quyền · sidecar(429/timeout/huỷ) · enroll(idempotent)
        · text(fixture hồi quy) · api(hợp đồng + sandbox không chạm GPU)
        · watermark(dấu CÓ trên tệp ra)
```

### 5.2 Sửa — và **chỉ** những tệp này

| Tệp | Vì sao |
|---|---|
| `setup/2-cai-dat.ps1` | cài `vieneu-venv` · sinh token + port · đặt `HF_HOME` · **ghim card** · cài dịch vụ `LTTStudioVoice` |
| `deploy/windows/update.ps1` | **dừng/bật dịch vụ thứ tư** — §7.2, lỗi chắc chắn xảy ra nếu quên |
| `deploy/windows/rollback.ps1` | như trên |
| `setup/nap_lai_env.ps1` | đang nạp env cho **"ba dich vu"** → thành bốn |
| `setup/4-nghiem-thu.ps1` | chốt dịch vụ + `/live` + **chốt làn `voice` có trong `LTT_WORKER_POOLS`** |
| `platform_core/gia_von.json` | mục giá vốn `ltt-voice-v3turbo` (mcredit/giây) |
| `server/api/inventory.py` | chỉ nếu V8 thêm route |
| `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md` | `test_212` đọc bảng này **cả hai chiều** |
| `docs/QUYET_DINH_NEN_TANG.md` · `CLAUDE.md` | Q-số mới + một hàng trạng thái |

⛔ **`platform_core/` và `server/` không có tệp mã nào trong danh sách** (chỉ dữ
liệu `gia_von.json` và sổ đăng ký `inventory.py`). Nếu thấy buộc phải sửa thật:
**dừng lại và nói vì sao.**

---

## 6. Lộ trình — 11 cổng. Vạch MVP sau V6.

### V0 · Quyết định nền — ½ ngày
Ghi Q-số: QĐ-1 (app + sidecar, **không** provider) · QĐ-2 (GPU-first, dịch vụ ấm
ghim card) · QĐ-6 (ba tầng) · QĐ-7 (tham số sinh mẫu là hằng số) · QĐ-8 (trần ký
tự). Ghi **cả phương án đã bác**, để phiên sau không "sửa cho giống H37".
→ **Qua khi** quyết định có trong `QUYET_DINH_NEN_TANG.md` kèm lý do.

### V1 · Khoá upstream + lô đo trên máy A — 1–2 ngày ⭐ chặn mọi thứ sau
- `requirements-vieneu.txt`: `vieneu==3.3.0` · `torch==2.8.0`+cu128 ·
  `transformers==4.57.6` · **`resemble-perth`** (và **gỡ `perth`**) · ghim
  revision HF `2da0efab` của v3-Turbo.
- `install-vieneu-sidecar.ps1` theo khuôn WhisperX: tạo `vieneu-venv`,
  **idempotent theo phiên bản**, làm ấm cache HF, in đường dẫn python ra stdout.
- Ma trận khói: VI · EN · trộn VI/EN · nhân bản 3–8 s · số/ngày/tiền/% · danh sách
  đánh số · **ch/tr và tên riêng** · đoạn 500/1.500/3.000 ký tự · lặp 20 lượt.
- Đo trên **GPU (chính)** và **CPU/ONNX (dự phòng)**: nạp model · TTFA · RTF ·
  **VRAM đỉnh** · RAM · kích thước WAV/giây · thời gian capture CUDA graph.
- 🔴 Đo **hai lần**: máy rảnh, và **trong lúc chạy một job `upscalevideo` quality
  (12 GB)** — đó mới là điều kiện thật của card.
- 🔴 Kiểm watermark: sinh tệp rồi **tự dò dấu**; và kiểm `watermarker is not None`.
- 🔴 Đo drift theo độ dài để **chốt con số cho QĐ-8**.

→ **Qua khi** `01_KHOA_UPSTREAM.md` trả lời: VRAM đỉnh bao nhiêu · sống chung với
upscale quality được không · watermark có áp không · trần ký tự an toàn là bao nhiêu
· CPU có đáng làm làn dự phòng không.

### V2 · Sidecar ấm `LTTStudioVoice` — 2–3 ngày
`/live` không khoá · `/health` có khoá · `/v1/capabilities` **dò lúc chạy** ·
`/v1/speech` · `/v1/batch` · `/v1/stream` sau cờ · một engine ấm + khoá + warmup
(gồm **warm CUDA graph cho các batch size sẽ dùng**) · `tham_so.py` cố định ·
`ngan_sach.py` từ chối cấu hình chưa đo **trước khi chạm GPU** · dịch vụ NSSM từ
`vieneu-venv`, ghim card, xoay log theo dung lượng (`test_61` chốt).
→ **Qua khi** khuôn tầng 1 đạt **8/8**; bận→429; quá giờ→dừng sạch; huỷ→chết hẳn;
**khởi động thất bại nếu watermarker None**.

### V3 · Lát cắt dọc — tiền đúng ngay từ đầu — 2–3 ngày
Một job `ltt_voice.synthesize`, giọng dựng sẵn, luồng A đầy đủ kể cả bước 9–12.
Chưa bảng, chưa UI.
→ **Qua khi** sinh được VI + EN qua đúng đường job · restart vẫn phát lại được ·
**xin dài nhận ngắn thì thu theo ngắn** · hoá đơn khớp từng credit.

### V4 · Voice Profile + ghi danh — 3–4 ngày
Bốn bảng tiền tố `voice_`, ràng buộc **duy nhất ở tầng CSDL** theo khuôn
`apps/vps/tables.py`. Migration có đường lùi. Luồng B đầy đủ.
→ **Qua khi** tạo giọng → restart → gọi lại vẫn đúng giọng · ghi danh hỏng không
để lại hồ sơ nửa vời · **khách A không đọc được giọng khách B** (test IDOR).

### V5 · Ống văn bản VI/EN — 2–3 ngày
Chuẩn hoá **cấp sản phẩm** trên nền `sea-g2p` — **không viết lại G2P**. Số/tiền/
ngày giờ/% · viết tắt · danh sách đánh số · URL/email · **từ điển phát âm riêng
(ch/tr, tên riêng — §2.7)** · chia đoạn theo câu, tôn trọng 256 ký tự/chunk và
trần QĐ-8.
→ **Qua khi** fixture hồi quy từ kịch bản thật; lịch sử job ghi **cả text gốc lẫn
text đã chuẩn hoá**; không regex rải rác trong handler.

### V6 · Voice Studio (web) — 3–4 ngày → ✅ **VẠCH MVP**
Bốn màn: Tạo tiếng · Giọng của tôi · Tạo giọng mới · Lịch sử. Jinja + `ltt.css`
với `?v={{ asset_ver }}`. Không React trừ khi chứng minh được cần.
🔴 **Đọc `LTT_WORKER_POOLS` thật trên production và thêm làn `voice`** (§1.5).
→ **Qua khi** kiểm bằng trình duyệt **trên `https://app.lttstudios.com`** (không
chỉ loopback) · console sạch · mặc định không lộ một điều khiển VieNeu nào.

### V7 · Giá công bố + giá vốn — 1 ngày
`gia.py` có phiên bản; `gia_von.json` tính từ **giây GPU đo thật ở V1**; `/gia-api`
lấy số **từ chính hàm ra hoá đơn**.
→ **Qua khi** khuôn tầng 3 đạt 6/6; `test_261` xanh.

### V8 · Mở `/api/v1` — tool `speech.ltt` — 2 ngày
`ASYNC_JOB`; `api_contract` đủ; **`hidden` cho mọi tham số sinh mẫu (QĐ-7)**; cập
nhật `inventory.py` + `APP_API_COVERAGE_FINAL.md`; sandbox **không chạm GPU,
không chạm sổ tiền**; bật cờ bằng `cong_tac_tool_api.ps1` **rồi mới** deploy.
→ **Qua khi** gọi thật qua Cloudflare bằng khoá thật.
⚠️ `User-Agent` **không** được bắt đầu bằng `Python-urllib/` (chữ P hoa).

### V9 · Long-form + batch — 3–5 ngày
Luồng C đầy đủ; `job_type_lanes` tách làn theo `mode`; `gpu_vram_mb` lấy từ số đo
V1; tận dụng `infer_batch` + CUDA graph đã ấm.
→ **Qua khi** giết worker giữa chừng ⇒ chạy lại **không bắt đầu từ 0** · nộp trùng
không sinh việc trùng · **đã đo trôi tông (#173) và độ dài công bố lấy từ số đo**.

### V10 · Cổng chất lượng trong Quality Lab — 3–4 ngày
CER/WER qua **sidecar WhisperX đã có**, tương đồng người nói, clipping/độ ồn, tỉ
lệ hỏng, TTFA/RTF, **chỉ số trôi tông giữa các đoạn**. A/B mù, **mỗi phiếu quyết
đoán phải viết lý do** (D-052).
→ **Qua khi** baseline **ghim theo phiên bản**; v3 full **không được lên** chỉ vì
"nghe hay hơn"; đổi `tham_so.py` cũng phải qua cổng này.

**Sau V10:** V11 bảo mật/giấy phép/consent · V12 streaming (chỉ còn viết hợp
đồng) · V13 vận hành + tổng kiểm 31 chốt.

---

## 7. Quy trình cài, cập nhật, lùi bản

### 7.1 Cài lần đầu

Chèn vào `2-cai-dat.ps1`, **sau** bước WhisperX sidecar và **trước** bước cài dịch vụ:

1. gọi `deploy\windows\install-vieneu-sidecar.ps1` → nhận đường dẫn python;
2. ghi vào `app.env` **nếu chưa có** (khuôn "GIU NGUYEN" của `LTT_CODEX_SIDECAR_TOKEN`):
   `LTT_VIENEU_PYTHON` · `LTT_VOICE_SIDECAR_TOKEN` (sinh ngẫu nhiên) ·
   `LTT_VOICE_SIDECAR_PORT=8120` · `HF_HOME=C:\LTTPlatform\hf-cache` ·
   `LTT_VOICE_GPU_UUID=<uuid card đã chọn>`;
3. cài dịch vụ `LTTStudioVoice` chạy `voice_sidecar_main.py` bằng python của
   `vieneu-venv`, `AppDirectory` = `app\`, `CUDA_VISIBLE_DEVICES` ghim card, xoay
   log theo dung lượng;
4. **làm ấm cache HF** (~320 MB) ngay lúc cài — để lần khởi động đầu không tải mạng.

Trong `install-vieneu-sidecar.ps1`, thứ tự cài **bắt buộc** (§2.4):

```
python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install "transformers==4.57.6"
python -m pip install vieneu==3.3.0
python -m pip uninstall -y perth          # goi SAI (thu vien threading)
python -m pip install resemble-perth      # watermarker THAT
python -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"
python -c "import perth,sys; sys.exit(0 if hasattr(perth,'PerthImplicitWatermarker') else 1)"
```

⚠️ Ghi `app.env` **không BOM**:
`[IO.File]::WriteAllText($p,$t,(New-Object Text.UTF8Encoding($false)))`.
⚠️ Tệp `.ps1` **thuần ASCII**.

### 7.2 🔴 Cập nhật — chỗ chắc chắn gãy nếu quên

`LTTStudioVoice` có `AppDirectory` = `app\` ⇒ **giữ handle trên thư mục đó**.
Không dừng nó thì `Move-Item app app.previous` **ném lỗi** giữa chừng — hoặc tệ
hơn, dịch vụ chạy tiếp bằng **mã cũ**, im lặng, tới lần restart sau.

```
DỪNG :  LTTStudioVoice → LTTStudioCodex → LTTStudioWorker → LTTStudioWeb
        ↓ backup data → xoay app\ → bung bản mới
        ↓ pip install lại venv nền tảng
        ↓ install-vieneu-sidecar.ps1   (idempotent THEO PHIÊN BẢN)
        ↓ alembic upgrade head
BẬT  :  LTTStudioWeb → LTTStudioWorker → LTTStudioCodex → LTTStudioVoice
        ↓ 4-nghiem-thu.ps1
```

Sửa cùng lần: `update.ps1` · `rollback.ps1` · `nap_lai_env.ps1` · `4-nghiem-thu.ps1`.

### 7.3 Đổi biến môi trường
⛔ Sửa `app.env` rồi `Restart-Service` là **không đủ** — nssm nướng env vào đăng ký
dịch vụ lúc cài. Đã dính hai lần. Dùng `setup\nap_lai_env.ps1`.

### 7.4 Lùi bản
`rollback.ps1` đổi `app.previous` về `app`. **`vieneu-venv` và `hf-cache` không bị
đụng** — đều ngoài `app\`. Nếu bản mới đã nâng `vieneu`, lùi mã mà không lùi venv
là lệch ⇒ installer phải **idempotent theo phiên bản**, không theo "đã tồn tại".

---

## 8. Vận hành

| Tài nguyên | Trần | Ghi chú |
|---|---|---|
| VRAM thường trú | **đo ở V1**, khai vào `gpu_vram_mb` | `gpu.py` đọc `memory.free` sống ⇒ `gpu_lease` tự tính (§1.4) |
| Job VOICE đồng thời | **1** (`voice:1` + `admission_slots=1`) | tầng ba ở sidecar là hàng rào cuối |
| Ký tự một lượt | **QĐ-8**, khởi điểm 1.500 | trần **chất lượng**, không phải hiệu năng |
| Trần chạy một job | `max_runtime_s` | job **treo** mà vẫn đập nhịp giữ slot vô hạn |

**Giám sát:** `/live` không khoá · `/health` có khoá (model nạp chưa · **đang chạy
GPU hay đã rơi về CPU** · số lượt đang chạy · số CUDA graph đã capture).
🔴 Chốt GPU-hay-CPU **đọc từ số đo**, không đọc từ cấu hình — sự cố 23/08 ở máy B
là *mọi chốt sống/chết đều xanh hơn một giờ* trong khi model bò trên CPU.

| Triệu chứng | Nguyên nhân thật |
|---|---|
| Job VOICE `queued` mãi, không lỗi | `LTT_WORKER_POOLS` thiếu làn `voice` |
| Cờ mới không tác dụng sau khi sửa app.env | chưa chạy `nap_lai_env.ps1` |
| Cập nhật ném lỗi ở `Move-Item` | quên dừng `LTTStudioVoice` |
| Tiếng đúng nhưng **không có watermark** | `perth` sai gói quay lại sau một lần cài (§2.6) |
| Giọng đổi vùng miền giữa bài | vượt trần QĐ-8, hoặc ai đó nới `temperature` |
| Tiếng ra cụt/sai giọng sau khi nâng | biểu diễn gắn revision cũ — dựng lại từ bản nguồn |
| 403 khi khách gọi API | `User-Agent` bắt đầu bằng `Python-urllib/` |

---

## 9. Sổ rủi ro

| # | Rủi ro | Mức | Cách chặn |
|---|---|---|---|
| R1 | Máy A là production đang phục vụ khách — không có đường cascade như model ảnh | 🔴 P0 | Ba tầng chặn (QĐ-6); deploy ngoài giờ cao điểm |
| R2 | **v3 full sắp ra** — nền đang di chuyển | 🔴 P0 | Ghim tag + revision HF `2da0efab`; cổng V10 là điều kiện **duy nhất** để nâng |
| R3 | **Watermark không áp** (gói `perth` sai) | 🔴 P0 | Gỡ `perth`, cài `resemble-perth`; sidecar **chết to** nếu `watermarker is None`; test chốt dấu trên tệp ra |
| R4 | Thêm dịch vụ thứ tư làm **gãy cập nhật** | 🔴 P0 | §7.2 — sửa cả bốn script cùng một lần |
| R5 | **Trôi giọng từ ~3.000 ký tự** (#168, #173) | 🟠 P1 | QĐ-8 trần ký tự; QĐ-7 tham số cố định; đo trôi tông ở V9/V10 |
| R6 | VRAM đụng `upscalevideo` quality (12 GB) trên cùng card | 🟠 P1 | V1 đo **trong lúc upscale đang chạy**; `gpu_vram_mb` lấy từ số đo; hai card |
| R7 | **CUDA graph nở** nếu ai đó lộ tham số sinh mẫu | 🟠 P1 | QĐ-7: `hidden` trong `api_contract`, không có trên UI, có test chốt |
| R8 | Đội hình worker thiếu làn `voice` ⇒ job nằm im, **không lỗi** | 🟠 P1 | Chốt trong `4-nghiem-thu.ps1` |
| R9 | Nhân bản giọng chạm **quyền nhân thân** | 🟠 P1 | Chỉ giọng tự sở hữu; consent lưu thành dữ liệu, đối chiếu bằng test |
| R10 | `transformers==4.57.6` ghim cứng — nâng torch/transformers là phá | 🟡 P2 | venv cách ly; installer idempotent theo phiên bản |
| R11 | Cloudflare 100 MB/request, 125 giây | 🟡 P2 | Audio dài đi presigned R2; việc dài đi `ASYNC_JOB` |
| R12 | `audio[]` không có trong Public API | 🟡 P2 | Hợp đồng: một tệp vào, một tệp ra |

---

## 10. Bắt đầu

Chủ sản phẩm đã chốt: **cứ xây**. Nên V0 và V1 chạy **song song** — V0 là viết
quyết định, không chờ số đo.

V1 vẫn là cổng chặn cho V2 trở đi, nhưng câu hỏi của nó đã đổi: không còn là *"CPU
có đủ nhanh không"* (GPU-first đã trả lời), mà là **bốn con số để chốt tham số**:

1. **VRAM đỉnh** trên 5060 Ti — để khai `gpu_vram_mb` và biết có sống chung với
   `upscalevideo` quality được không.
2. **RTF và TTFA trên GPU** — để đặt giá và đặt `max_runtime_s`.
3. **Ngưỡng ký tự trước khi trôi giọng** — để chốt QĐ-8 bằng số, không bằng
   con số 3.000 mượn từ một issue.
4. **Watermark có áp không sau khi thay `resemble-perth`** — để biết ta được phép
   nói gì về provenance.

⇒ V1 không còn là *"đo xem có làm được không"*. Nó là **đo để điền bốn tham số**
mà V2–V10 đã có chỗ chờ sẵn.
