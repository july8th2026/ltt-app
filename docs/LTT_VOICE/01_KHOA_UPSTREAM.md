# LTT VOICE — V1: khoá upstream và lô đo trên máy A

> Đo ngày **2026-08-30** trên **máy A**, RTX 5060 Ti (16.311 MiB), Windows.
> Số thô: `docs/LTT_VOICE/do_v1.json` (ghi sau mỗi phép đo, chạy lại thì bỏ qua
> phép đã xong).
> Trạng thái: **V1 ĐÓNG.** Bốn câu hỏi chặn đều có câu trả lời bằng số.

---

## 1. Bản ghim

| Hạng mục | Giá trị ghim | Ghim ở đâu |
|---|---|---|
| Kho upstream | `pnnbao97/VieNeu-TTS` @ `36c4b50` (main, 20/08), tag `v3.3.0` | — |
| Gói SDK | `vieneu==3.3.0` | `requirements-vieneu.txt` |
| Model | `pnnbao-ump/VieNeu-TTS-v3-Turbo` @ **`2da0efab622a1722125991736524f080b751ef5b`** | `install-vieneu-sidecar.ps1` |
| Torch | `2.8.0` + `cu128` | như trên |
| Transformers | `4.57.6` (upstream ghim cho GPU SDK) | như trên |
| huggingface_hub | `>=0.34.0,<1.0` | như trên — **xem §4.1** |
| Watermarker | **`resemble-perth==1.0.1`** (thay `perth`) | như trên — **xem §4.2** |
| Giấy phép | Apache-2.0 (mã **và** trọng số) | — |

⛔ **Ghim revision, không ghim `main`.** Bản v3 full sắp ra và sẽ đổi hành vi mà
**không đổi tên repo**. Một bản cài hôm nay và một bản cài tháng sau phải cho ra
cùng một model, nếu không thì toàn bộ bảng số dưới đây mất nghĩa.

**Chỉ tải phần đang dùng:** kho đầy đủ 1.678 MB, đường PyTorch/GPU cần
`update/` + `denoiser.onnx` + `speaker_encoder.onnx` = **305 MB đo thật**
(ước 320 MB, khớp).

---

## 2. Bốn câu hỏi chặn — trả lời bằng số

### 2.1 VRAM: **641 MB đỉnh** — nhỏ hơn ước tính một bậc

| Phép đo | Giá trị |
|---|---|
| `torch.max_memory_allocated` (đỉnh, bài 1.500 ký tự) | **641 MB** |
| `torch.max_memory_reserved` | **1.288 MB** |
| `nvidia-smi` cho cả tiến trình | ~1.859 MiB |
| Sau khi nạp, chưa sinh gì | 334 MB |

⇒ Khai `gpu_vram_mb = 2000` — trên mức reserved, **dưới xa `upscalevideo`
quality (12.000 MB)**. Hai app sống chung được trên một card 16 GB.

⭐ Kế hoạch dự đoán 1–3 GB. Số thật thấp hơn cả cận dưới, và điều đó **đổi một
quyết định**: không cần dành riêng một card cho giọng nói.

### 2.2 Tốc độ: RTF **0,12–0,70**, và nó phụ thuộc độ dài

| Độ dài | Sinh (s) | Audio (s) | RTF | ký tự/giây |
|---:|---:|---:|---:|---:|
| 47 (câu ngắn) | 3,36 | 3,36 | 1,00 | 14,0 |
| 500 | 10,05 | 24,42 | 0,412 | 20,5 |
| 1.000 | 11,27 | 47,66 | 0,236 | 21,0 |
| 1.500 | 12,58 | 71,62 | 0,176 | 20,9 |
| 2.000 | 15,68 | 97,10 | 0,162 | 20,6 |
| 3.000 | 17,55 | 144,54 | 0,121 | 20,8 |

⭐ **Đây chính là phần thắng của batching mà README mô tả**, và nó đo được: từ
500 tới 3.000 ký tự thời gian sinh chỉ tăng **1,75 lần** trong khi audio tăng
**5,9 lần**.

**Ổn định** (10 lượt cùng một câu): RTF trung bình 0,7017, lệch chuẩn **0,0048**.
**Nạp model**: 19,4 s lần đầu; 10,5 s khi cache đã ấm.
**TTFA** (`infer_stream`): **398 ms** qua 10 chunk.

### 2.3 Ngưỡng ký tự: 3.000 **vẫn sinh được**, nên trần là trần chất lượng

3.000 ký tự chạy hết trong 17,55 s, **không lỗi, không cắt**. Nghĩa là trần
`TRAN_KY_TU_MOT_LUOT = 1500` **không đến từ giới hạn kỹ thuật** — nó đến từ
upstream #168, nơi người thử báo giọng bắt đầu trôi vùng miền từ khoảng 3.000 ký
tự.

⇒ Giữ 1.500 (một nửa ngưỡng báo cáo). ⛔ Nới nó là một **quyết định chất lượng**
và phải qua cổng V10 — không phải một tham số hiệu năng để chỉnh cho tiện.

### 2.4 🔴 Watermark: **CÓ, và đọc lại được** — sau khi thay gói

```
nap_duoc            : true
hai_ban_khac_nhau   : true      (apply_watermark=True vs False cho hai song khac nhau)
doc_lai_duoc        : 1.0       (perth.get_watermark tren chinh tep ra)
```

Đây là bằng chứng, không phải một cờ cấu hình: dấu được **lấy lại từ sóng âm**
của tệp đã sinh, kể cả tệp sinh bằng giọng nhân bản.

⇒ Ta **được phép** công bố "audio có đóng dấu chìm". Trước bản vá ở §4.2 thì
không.

---

## 3. Ma trận khói — bảy ô, bảy lượt chạy được

| Ô | Ký tự | Audio (s) | RTF | Kết quả |
|---|---:|---:|---:|---|
| Tiếng Việt ngắn | 47 | 3,36 | 1,001 | ✅ |
| Tiếng Anh ngắn | 56 | 3,60 | 0,698 | ✅ |
| Trộn VI/EN | 59 | 3,12 | 0,711 | ✅ |
| Số / tiền / ngày / % | 81 | 8,16 | 0,694 | ✅ |
| Danh sách đánh số | 52 | 3,04 | 0,695 | ✅ |
| `ch`/`tr` (#168) | 53 | 2,40 | 0,701 | ✅ |
| Viết tắt kỹ thuật | 51 | 3,76 | 0,694 | ✅ |

⚠️ **"Chạy được" ≠ "đọc đúng".** Bảng này chứng minh đường đi thông và không có ô
nào làm sập engine. Nó **không** chứng minh `ch`/`tr` phát âm đúng hay số đọc
đúng — đó là việc của **V10** (CER/WER qua WhisperX + A/B mù). Đừng đọc bảng này
thành một chứng chỉ chất lượng.

---

## 4. Ba lỗi upstream đã chạm phải, và cách vá

### 4.1 Phụ thuộc upstream **tự mâu thuẫn** khi cài theo thứ tự của README

```
transformers 4.57.6  yeu cau  huggingface-hub>=0.34.0,<1.0
vieneu 3.3.0         khai     huggingface_hub          (khong tran tren)
```

Cài theo đúng thứ tự README (torch → transformers → vieneu) để lần cài **cuối
cùng** kéo hub `1.29.0`, vượt trần của transformers. pip **cảnh báo rồi đi tiếp**:

> *ERROR: pip's dependency resolver does not currently take into account all the
> packages that are installed…*

⇒ venv trông như bình thường cho tới lần `import transformers` đầu tiên, rồi chết
với một `ImportError` **nêu tên hub** — trỏ vào đúng gói không có lỗi gì.

**Vá:** ghim `huggingface_hub>=0.34.0,<1.0` **sau** khi cài vieneu, và nghiệm thu
bằng cách import **engine thật** (`from vieneu._v3_turbo_engine.inference_v3_turbo
import VieNeuTTSv3Turbo`), không chỉ `import vieneu`.

⚠️ Hai cảnh báo pip còn lại **là bình thường, đừng "sửa"**:
`vieneu requires perth>=0.2.0` (ta cố ý thay bằng `resemble-perth`) và
`gradio requires huggingface-hub>=1.16.0` (gradio chỉ dùng cho web UI ta không chạy).

### 4.2 🔴 `perth` là **sai gói** — watermark chưa bao giờ được áp (upstream #191)

| Gói | Mô tả thật trên PyPI |
|---|---|
| `perth` 1.0.0 — thứ `vieneu` khai | *"Wrapper for `threading.local` with enhanced value accessor"* |
| `resemble-perth` 1.0.1 — thứ cần | *"Audio Watermarking and Detection Library"* |

`base.py::_init_watermarker` bắt cả `AttributeError` rồi đặt `watermarker = None`
— **không một dòng log**. Mặc định `apply_watermark=True` ở khắp nơi.

**Vá, hai bước, cả hai bắt buộc:**
1. installer **gỡ `perth` rồi cài `resemble-perth`** (cùng chiếm tên module
   `perth`; không gỡ trước thì kết quả không tất định);
2. sidecar **từ chối khởi động** nếu `watermarker is None` — không thừa kế sự im
   lặng của upstream.

### 4.3 Tải model trên Windows có một **cuộc đua cục bộ**

Lượt cài đầu chết với `FileNotFoundError: ...\blobs\5c9785c1…`, lượt chạy lại
ngay sau đó **thành công không sửa gì**.

Cơ chế: Windows không cho tài khoản thường tạo symlink, nên `huggingface_hub` rơi
về chế độ **chép** từ `blobs\` sang `snapshots\`. Tải song song làm hai bước đó
đua nhau.

**Vá:** `max_workers=1` + thử lại 3 lần.
⛔ Đừng đọc lỗi này thành "mạng hỏng" hay "repo sai".

---

## 5. Một thứ ngoài phạm vi nhưng phải nói ra

🔴 **Ổ C: còn 5,6 GB / 930,9 GB (99,4 % đầy)** — đo lúc `pip install torch` chết
giữa chừng với `[Errno 28] No space left on device`, để lại một venv hỏng 4,2 GB.

Nền tảng **không phải thủ phạm**: `C:\LTTPlatform` chỉ chiếm 16,1 GB. Chỗ đầy là
`Users` 384 GB, `Riot Games` 44 GB.

⚠️ **Postgres nằm trên C:** (`C:\Program Files\PostgreSQL\17\data`). C: đầy thì
Postgres từ chối ghi, và triệu chứng sẽ **không** nói "hết đĩa" — nó hiện ra
thành job hỏng ngẫu nhiên hoặc `/health/ready` 503.

⇒ **Việc của chủ sản phẩm, không phải của phiên này.** Ở đây chỉ làm hai thứ:
- đặt `vieneu-venv` + `hf-cache` sang **`D:\LTTPlatform-runtime`** (còn 60,6 GB),
  qua tham số `-VenvRoot` / biến `LTT_VOICE_VENV_ROOT`;
- installer **từ chối chạy** khi ổ đích còn dưới 12 GB, thay vì cài dở rồi để lại
  một cây torch hỏng.

📌 Phát hiện kèm theo: `C:\LTTPlatform\whisperx-venv` chỉ **0,01 GB** — WhisperX
**chưa từng cài được**. `apps/autosubvideo` vì thế đang chạy nhánh dự phòng
`faster-whisper`, có ghi nhãn `alignment_status: fallback_unaligned`. Hệ quả thật
là **mất căn chỉnh theo từ**, không mất phụ đề; và tool `video.subtitle` trên
`/api/v1` **không chạm ASR** (khách tự mang transcript). *(Đồng nghiệp
`lttstudiosapp-a5` xác minh và thu hẹp kết luận này.)*

---

## 6. Nghiệm thu đã chạy thật

Sidecar chạy trên `127.0.0.1:8120`, `vieneu-venv`, backend `pytorch`, `cuda`:

| Chốt (khuôn tầng 1) | Kết quả |
|---|---|
| 1.7 `/live` **không** cần khoá | ✅ `{"ok":true}` |
| 1.7 `/health` **cần** khoá | ✅ 401 khi thiếu token |
| 1.6 chốt GPU/CPU đọc từ **số đo** | ✅ `tren_gpu:true`, `vram_mb:342` từ `memory_allocated` |
| Năng lực dò **lúc chạy** | ✅ `streaming:true` — trong khi `config.yaml` upstream khai `false` |
| 1.2 vượt ngân sách ⇒ **413 trước GPU** | ✅ 2.000 ký tự → 413 `too_long`, trần 1.500 |
| 1.3/1.4 bận ⇒ **429, không bao giờ 5xx** | ✅ 3 lượt song song → **1×200, 2×429** kèm `Retry-After`, **0×5xx** |
| Ghi danh vòng tròn | ✅ 1,3 s → `emb_dim 192`, 704 codes |
| Sinh tiếng bằng giọng vừa nhân bản | ✅ 200, 48 kHz |
| Watermark trên tệp giọng nhân bản | ✅ đọc lại **1.0** |

---

## 7. Đã đủ để đóng V1, còn thiếu gì

**Đóng được:** bốn con số chặn đều có, ba lỗi upstream đã vá và có nghiệm thu,
đường đi thông đầu-tới-cuối.

**Còn nợ, có chủ ý:**

- ⏳ **Lô đo thứ hai trong lúc GPU đang bận** (`--nhan gpu-ban`, chạy song song
  một job `upscalevideo` quality giữ 12 GB). Đo lúc rảnh là đo một điều kiện
  không có thật. **Nhưng nó không còn chặn V2** như kế hoạch dự tính: 641 MB so
  với 16 GB nghĩa là tranh chấp VRAM gần như không tồn tại — cái cần đo là tranh
  chấp **thời gian GPU**, và đó là một con số hiệu năng chứ không phải một con
  số an toàn.
- ⏳ **Lô đo đường CPU/ONNX** (làn dự phòng). Chưa tải `onnx_int8/`.
- ⏳ **Chất lượng** — CER/WER, tương đồng người nói, trôi tông. Đó là V10.
