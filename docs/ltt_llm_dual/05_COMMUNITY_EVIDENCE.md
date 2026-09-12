# 05 — Bằng chứng upstream/cộng đồng (Gate R4)

> Nghiên cứu 2026-09-11 trên **đúng build đang cài** (llama.cpp tag `b10883` trong clone
> `D:\LTT_VLM_REFS\llama.cpp`, llama-swap tag `v250`) + HF/GitHub/PyPI qua `curl`.
> Kế thừa và KIỂM LẠI `docs/multijob/04_RUNTIME_CAPABILITY_MAP.md` (R-1 ở b10689).
> Nhãn: **[M]** có người đo · **[C]** tuyên bố/tài liệu · **[INFERRED]** tự tính. Không dùng số quảng cáo làm số đo.

## 1. Ma trận

| Vấn đề | LTT hiện tại | b10689 (R-1) | **b10883 (đã đọc lại mã)** | Upstream mới nhất | Tương thích build đang cài? | Quyết định tái dùng |
|---|---|---|---|---|---|---|
| `-np N -kvu` = một pool chung, một slot dùng được cả pool | `-np 1` | đúng | đúng (`src/llama-context.cpp:290-304`, `llama-kv-cache.cpp:84`) | như cũ | có | Dùng. `-c 262144 -np 4 -kvu` = **một** pool 262.144, không phải 4×262.144 |
| Trần tĩnh mỗi slot trong pool | — | `--kv-unified-per-slot` | có (`common/arg.cpp:1646-1653`, áp ở `server-context.cpp:4027-4035`), **không đặt chỗ** | như cũ | có | Chỉ là trần; không thay admission |
| Tràn pool ⇒ **giết mọi slot** | — | đúng | **đúng** (`server-context.cpp:3688-3724`, TODO "chỉ giết slot lớn nhất" `:3692`; sau đó `abort_all_slots` `:2891-2895`) | b10903 + master **như cũ**; PR #26545 đóng không merge | — | ⇒ Admission theo ngân sách **bắt buộc** ở tầng LTT (giữ TD-5) |
| Admission theo KV trong engine | không | không | **không** (`get_available_slot` `:1547-1660`; hoãn chỉ theo số slot `:2398-2424`) | không có PR nào | — | LTT tự làm (T4/T5 Multi-Job). Tham chiếu: patch 0011 của `rtx3090-llm-lab` — áp được vào b10883 (lệch dòng +11, CRLF→LF), **không có PR upstream**; `n_predict=-1` ⇒ đặt cả slot ⇒ tuần tự hoá |
| Thứ tự lấp prompt theo chỉ số slot (đói prefill) | — | đúng | đúng (`:3110-3135`) | như cũ | — | Chấp nhận; chữa ở admission (D-05) |
| `--cache-ram` (cache prompt ở RAM host) | mặc định | 8 GiB | 8 GiB, **tự co còn 40 %** khi `bad_alloc` (`server-task.cpp:1763-1772`) | #28046 mở | có | Chỉnh theo RAM 224 GB — **cache prompt, không phải cache trọng số** |
| `--cache-idle-slots` | mặc định | bật | bật; với `-kvu` còn **xoá khỏi VRAM** slot rảnh sau khi lưu RAM (`:2436-2451`) | như cũ | có | Giữ |
| Metric dùng KV | không | không | **không** (gần nhất `n_tokens_max`) | không | — | Sổ ngân sách của LTT là nguồn duy nhất |
| Hủy khi client ngắt | stream có | poll 1 s | như cũ (`server-context.cpp:39`, `server-queue.cpp:607-617`) | như cũ | có | Giữ. ⛔ Không gửi `X-Conversation-Id` |
| `preserve_reasoning` | — | — | **mặc định BẬT** (`arg.cpp:958-960`) ⇒ lịch sử dài hơn mỗi lượt | như cũ | có | Chốt tường minh (`--no-reasoning-preserve` hay giữ) + đưa vào công thức ước token |
| mmproj + `-np 4 -kvu` | 2 hồ sơ đổi nhau | — | **không hạn chế**; ảnh hỏng chỉ lỗi slot đó (`:3497-3502`); không checkpoint sau ảnh (`:3622`) | — | có | Hồ sơ gộp text+vision khả thi (khớp D-08 A) |
| MTP sau ảnh | — | — | vị trí sai | **sửa ở master** `b0dcb8192` (#28715), chưa có tag | **UPSTREAM AVAILABLE / INSTALLED BUILD MISSING** | Chờ tag > b10903; [INFERRED] hệ quả: nhận nháp thấp, không sai đầu ra |
| 🔴 **MTP + `-np N`** | draft-mtp ở `-np 1` | chưa biết | **#27572 MỞ**: nhận nháp rơi về 0 và **một số trả lời RỖNG**; một xác nhận trên **Windows CUDA + Qwen3.8-27B MTP + mmproj** (đúng cấu hình đích D-08). PR sửa #26827/#27311 **mở**. Thêm: #28286 trộn nội dung giữa slot (ROCm, fork), #27282 OOM, #23577 "////" sau phiên dài | chưa sửa | — | **Không bật MTP ở `-np 4` khi chưa có phép kiểm đúng/sai cho từng slot** |
| MTP trên Blackwell CUDA (5060 Ti = sm_120) | — | — | #26750 [M]: Qwen3.5-9B-MTP Q4_K_M nhận nháp 35,8 %, **−32 %** tok/s | mở | — | LTT-3.5 **khởi đầu không MTP** |
| MTP ở đồng thời | — | — | [M] 2×5060 Ti, 27B: +70 % ở N=1, **ngang** ở N=4 (`qwen38-mtp/sweeps/multi-gpu.md:87-99`) | — | — | Lợi ích MTP chủ yếu ở C1 |
| KV `q4_0` phạt prefill | KV q4_0 trên 3090 | — | [M] lab, **model khác** (Tiel-35B): V `q4_0` prefill chậm 14×. Nhưng M-1 của ta đo **999 tok/s** prefill 50K với q4_0 ⇒ không lặp lại trên Qwen3.8 | — | — | Không đổi; đo lại khi đổi cấu hình |
| `--no-mmap`/`--mlock` | không dùng | có | **đã gỡ ở b10875** (#28334) ⇒ `--load-mode {auto,none,mmap,mlock,mmap+mlock,dio}` (`arg.cpp:2687`) | — | — | `tests/test_637` chỉ chặn tên cũ ⇒ **mù** với `--load-mode none/dio` |
| Windows mmap / mlock | — | — | `MapViewOfFile` + `PrefetchVirtualMemory`; mlock = `VirtualLock` **chỉ sống theo tiến trình** (`src/llama-mmap.cpp:583-620,736-760`) | — | — | mlock **vô ích** cho nạp lại qua llama-swap; kho ấm = standby list của Windows (224 GB) |
| Ngủ sâu | — | — | `--sleep-idle-seconds` = gỡ hẳn trọng số+KV (≈ vLLM sleep level 2); **không có** "đỗ trọng số ở RAM" (level 1) | #28233 mở | — | Không tuyên bố "GPU sleep to RAM" |
| llama-swap hai model trên hai GPU cùng lúc | không `groups` (một model một lúc) | — | v250 **đã có** `groups` (`swap:false`), `matrix` (`sets`, `evict_costs`), `env` theo model, `hooks.on_startup.preload` (`config-schema.json:87-160`, `config.example.yaml:280,495-502`) | v255 (09-05) — lõi lịch không đổi | **có** | **Tái dùng**: một group `swap:false` gồm hai model, mỗi model `CUDA_VISIBLE_DEVICES=<UUID>`, preload |
| llama-swap gỡ model khi đang chạy | render gọi `GET /unload` | — | đổi hồ sơ & TTL **chờ lượt đang chạy**; **unload thủ công KHÔNG chờ** — lượt đang chạy chết (`fifo.go:222-270`, Windows `taskkill /t` rồi `/f`) | như cũ | — | ⛔ Đường drain phải do LTT làm (ngừng nhận → chờ in-flight = 0 → mới unload) |
| llama-swap `concurrencyLimit` | — | — | mặc định 10; vượt ⇒ **429 ngay**, không xếp hàng (`scheduler/fifo.go:17,310-321`) | — | có | Đặt ≥ slot của model; không để nó thành hàng đợi thứ hai |

## 2. Model

**Qwen3.8-27B** (`Qwen/Qwen3.8-27B`, Apache-2.0, 2026-08-05, kiến trúc `qwen3_5`): 64 lớp, 16 lớp
attention (4 KV head × 256), 48 lớp Gated-DeltaNet. `max_position_embeddings = 262144`.
GGUF đang chạy = unsloth `UD-Q4_K_M` bản re-upload Dynamic 3.0 **2026-08-19**, sha `322e194f…` (khớp hash máy B).

**262.144 trên 3090:**
- [C] `qwen38-mtp/README.md:22`: "262K vừa 24 GB ở 22,2 GB" — KV q4_0, **không** spec.
- [M] `qwen38-mtp/sweeps/rtx-3090.md:22`: "262K không nạp được trên 24 GB; 204.800 là trần làm việc" — **có MTP**.
- [INFERRED] trọng số 15,33 + mmproj 0,86 + KV q4_0 4,5 (+ lớp MTP ⇒ 4,78) ≈ 20,97 GiB + trạng thái hồi quy
  (~150 MiB/chuỗi) + buffer tính/ngữ cảnh CUDA 1,5–2 GiB ≈ **23 GiB trên ~23,3 dùng được** ⇒ sát mép, dễ hỏng
  khi đủ MTP + mmproj + 4 slot. ⇒ Chỉ đo được mới biết; thứ phải hy sinh nếu không vừa là một quyết định.

**Qwen3.5-9B** (`Qwen/Qwen3.5-9B`, Apache-2.0, 2026-02-27, `qwen3_5`): 32 lớp = 8×(3 DeltaNet + 1 attention),
attention 4 KV head × 256; 262.144 native (YaRN tới ~1M); **vision tích hợp** (cần mmproj); thinking mặc định
bật; có 1 lớp MTP. llama.cpp hỗ trợ từ b7990, MTP từ b9180 ⇒ **b10883 chạy được**.

KV/token [INFERRED, từ `config.json`]: 8 lớp × 4 × 256 × 2 = 16.384 phần tử ⇒ f16 32 KiB · q8_0 17 KiB · q4_0 9 KiB.
⇒ **262.144 token: q8_0 4,25 GiB · q4_0 2,25 GiB**. Trạng thái hồi quy ~50 MiB/chuỗi.

| repo | tệp | cỡ | mmproj | VRAM ước* | ghi chú |
|---|---|---:|---|---:|---|
| `unsloth/Qwen3.5-9B-MTP-GGUF` | `UD-Q4_K_XL` | 6,135 GB (`362f85a2…`) | F16 0,918 GB (`5a40d1f7…`) | ~9,9 GiB | có lớp MTP (dùng sau) |
| `unsloth/Qwen3.5-9B-MTP-GGUF` | `Q6_K` | 7,685 GB (`8ae8fd04…`) | như trên | ~11,4 GiB | chất lượng cao hơn nếu ComfyUI không thường trú |
| `bartowski/Qwen_Qwen3.5-9B-GGUF` | `Q4_K_M` | 6,169 GB (`d784ce9e…`) | f16 0,918 GB | ~9,9 GiB | imatrix, có MTP |
| `unsloth/Qwen3.5-9B-MTP-GGUF` | `IQ4_XS` | 5,467 GB | như trên | ~9,6 GiB | phương án ép |

\* Giả định tham chiếu: toàn bộ lớp trên GPU, mmproj F16, KV q8_0 131.072 token pool chung 4 slot, không
draft-mtp, ~1,2 GiB overhead; **chưa trừ** desktop (0,3–0,8 GiB) và ComfyUI. Không có repo GGUF chính thức của Qwen.

Bằng chứng tốc độ trên 16 GB: [C] ~48–51 tok/s trên 5060 Ti (llama-server, quant không rõ, ATLAS #28);
[M] engine khác (NInfer) 119 tok/s C1 / 204 tok/s tổng C4. **Không tìm thấy số đo llama.cpp `-np 4` của
Qwen3.5-9B trên 5060 Ti — NO EVIDENCE FOUND.**

## 3. Tài liệu / tệp đầu vào

| | Docling 2.126.0 (09-04, MIT) | markitdown 0.1.7 (MIT) — **đã có trong kho** |
|---|---|---|
| Định dạng | PDF, DOCX/XLSX/PPTX, DOC/XLS/PPT/RTF (qua LibreOffice), ODF, EPUB, MD, HTML, CSV, ảnh, email; audio/video (Whisper) với extra `asr` + ffmpeg | Office/HTML/PDF theo extra, không bố cục/bảng |
| Bố cục, bảng, OCR | có (layout "heron" 172 MB, TableFormer; OCR RapidOCR/EasyOCR/Tesseract trên Windows) | không (OCR chỉ qua plugin LLM-vision) |
| Đầu ra | DoclingDocument JSON, Markdown, chunk có provenance (`HybridChunker`, theo tokenizer) | Markdown |
| Nặng | `standard` kéo **torch + torchvision**; `docling-slim` bỏ được torch | nhẹ |
| Máy chủ | `docling-serve 1.32.0` (FastAPI :5001), image chính thức **chỉ Linux** | — |
| Windows / Py3.13 | có | có |

Đường tệp→chữ **đã có** trong kho: `apps/chatltt/services/trich_van_ban.py` (pypdf + markitdown) + `chia_doan`/`tim_doan`.
pymupdf đã bị loại vì AGPL. ⇒ Community-first: Docling (CPU) cho định dạng khó (PDF bố cục/bảng, XLSX, PPTX,
OCR), markitdown giữ làm đường nhanh — **không** tự viết parser.

## 4. Kho ấm RAM (224 GB)

- Trọng số ấm = **standby list** của Windows sau khi tiến trình thoát [INFERRED — hành vi OS, chưa đo trên máy]; sống
  tới khi có áp lực bộ nhớ (ComfyUI, demucs…). `mlock` chỉ sống theo tiến trình ⇒ không giúp nạp lại.
- `--cache-ram` = cache **prompt/KV** ở RAM, không phải trọng số.
- `nvidia-smi` **không thấy** WDDM tràn sang bộ nhớ chia sẻ ⇒ đo bằng
  `Get-Counter "\GPU Process Memory(pid_<pid>*)\Shared Usage"` (`qwen38-mtp/sweeps/rtx-3090.md` ~l.255).
- **Không có số đo công khai** cho thời gian nạp lại llama-swap từ page cache vs NVMe lạnh ⇒ phải đo (K).

## 5. Chỉ đo trên máy mới biết

1. VRAM trống 5060 Ti khi desktop chạy, ComfyUI rảnh/đang vẽ; ComfyUI có nhả model theo lệnh không.
2. VRAM đỉnh Qwen3.5-9B `-np 4` + mmproj + ảnh lớn.
3. prefill/decode với KV q8_0 vs q4_0 trên cả hai card.
4. MTP ở sm_120 và ở `-np 4` trên 3090: tỉ lệ nhận nháp, **trả lời rỗng, trộn nội dung giữa slot**.
5. Qwen3.8-27B có nạp ở 262.144 + mmproj + MTP + 4 slot trên b10883 không (kèm bộ đếm Shared Usage).
6. Nạp lại 15,33 GiB từ standby vs NVMe lạnh; standby có sống qua áp lực ComfyUI/demucs không.
7. Docling trang/phút trên 2× E5-2678 v3; OCR tiếng Việt RapidOCR vs Tesseract `vie` vs EasyOCR `vi`.
