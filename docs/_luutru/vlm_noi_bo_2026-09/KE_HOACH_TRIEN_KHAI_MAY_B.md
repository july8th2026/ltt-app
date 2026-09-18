# Kế hoạch thi hành — VLM vận hành Qwen3.8-27B trên MÁY B

**2026-08-22.** Chủ dự án đã chốt: **làm trên máy B**. Tài liệu này là kế hoạch
thi hành. Nghiên cứu nền ở [`NGHIEN_CUU_KHA_THI.md`](NGHIEN_CUU_KHA_THI.md).

Mục tiêu: một **VLM vận hành** chạy tại nhà, phơi ra API để **Codex, Claude Code
và nền tảng LTTSTUDIOSAPP** cắm vào, và **các VLM sau này thay được mà không sửa
hợp đồng**.

---

## 1. ĐÍNH CHÍNH quan trọng: engine là **llama.cpp**, không phải vLLM

Ở tài liệu nghiên cứu tôi viết *"để cắm vào Codex thì buộc phải là vLLM"*. **Câu đó
sai.** Đọc kỹ README của `llama-server` thì:

| Nhu cầu | llama.cpp có? | Ghi chú |
|---|---|---|
| `POST /v1/responses` — **Codex CLI** | ✅ **CÓ** | server tự dịch Responses → Chat Completions |
| `POST /v1/messages` — **Claude Code** | ✅ **CÓ** | Anthropic Messages API, PR #17570, 19/01/2026 |
| `POST /v1/chat/completions` — mọi thứ khác | ✅ | |
| Vision | ✅ `--mmproj` | **đã chứng minh trên đúng 3090 + đúng model này** |
| Tool calling | ✅ `--jinja` | |
| Chạy **native Windows** + CUDA | ✅ | **không cần WSL, không cần reboot máy B** |

Đối chiếu vLLM: nhanh hơn (114 vs 43 tok/s) và có sleep mode, **nhưng** trên Windows
đường chính thức là WSL2 (máy B **chưa cài** → phải reboot, mà reboot máy B là chuyện
nhạy cảm — D-025), và **multimodal trên sm_86 chưa ai chứng minh**.

> **Chốt: khởi đầu bằng llama.cpp.** vLLM là đường **nâng cấp về sau**, chỉ mở khi
> throughput thật sự thành nút thắt — mà với một trợ lý vận hành 1–2 người dùng thì
> 43 tok/s không phải nút thắt.

Đây cũng đúng tinh thần dự án: **đừng dựng cái thứ hai khi cái thứ nhất đã đủ.**

---

## 2. Ngân sách VRAM — tính từ số thật, chừa biên có chủ ý

Card **24.576 MiB = 24,0 GiB**. Số đầu vào:

| Khoản | Dung lượng | Nguồn |
|---|---|---|
| `Qwen3.8-27B-Q4_K_M.gguf` | **17,1 GB** | bảng kích thước GGUF thật |
| `mmproj-F16.gguf` (vision) | **0,93 GB** | Unsloth |
| KV cache | **64 KB/token** | hệ quả của 16/64 lớp full attention — **khớp phép tính ở §1 tài liệu nghiên cứu** |

| Ngữ cảnh | KV | Tổng | Biên còn lại | Đánh giá |
|---|---|---|---|---|
| **32K** | 2,0 GB | **~20,0 GB** | **4,0 GB** | ✅ **điểm khởi đầu** |
| 48K | 3,0 GB | ~21,0 GB | 3,0 GB | ✅ sau khi đo |
| 64K | 4,0 GB | ~22,0 GB | 2,0 GB | ⚠️ sát |
| 128K | 8,0 GB | ~26,0 GB | — | ❌ **không vừa** |

Cộng đồng đo thật ở cấu hình 32K: **~19 GB**. Khớp.

> 🔴 **Biên 4 GB là cố ý, không phải thừa.** D-024: cấu hình chạy ở **97,5 % VRAM và
> ở lì đó** là lỗi thiết kế đã được ghi nhận. Đừng ăn hết biên để lấy thêm ngữ cảnh.

**Tuỳ chọn có thể mở SAU KHI ĐO:** `--cache-type-k q8_0 --cache-type-v q8_0` giảm KV
một nửa → 64K chỉ tốn 2 GB. **Phải đo chất lượng trước**, đừng bật mặc định.

---

## 3. Kiến trúc — ba tầng, mỗi tầng một việc

```
Codex CLI ──────┐
Claude Code ────┤                        MÁY B
apps/ nền tảng ─┼── LAN ──►  [3] llm_gateway  :8299   FastAPI · bearer · chính sách
Nexus ──────────┘             (auth, ngân sách token, trọng tài VRAM,
                               đo đếm credit, cascade sang cloud)
                                          │ loopback
                                          ▼
                              [2] llama-swap  :8280   vòng đời model · TTL nhả VRAM
                                          │ loopback
                                          ▼
                              [1] llama-server :8281  CHỈ 127.0.0.1
                                  --jinja --mmproj -ngl 99
                                          │
                                  trọng tài VRAM
                                          ▼
                                  ComfyUI :8188  (ảnh — H37)
```

**Vì sao ba tầng chứ không phải một:**

| Tầng | Có sẵn? | Việc riêng của nó |
|---|---|---|
| **[1] llama-server** | ✅ thượng nguồn | Chạy model. **Không viết gì ở đây.** |
| **[2] llama-swap** | ✅ có sẵn (`mostlygeek/llama-swap`, 1 binary Go + 1 YAML) | Bật/tắt model theo yêu cầu, **`ttl` hết hạn thì giết tiến trình và trả VRAM**, `POST /api/models/unload` để ép nhả ngay |
| **[3] llm_gateway** | ❌ **ta viết** | Thứ duy nhất không ai làm hộ: **xác thực LAN, ngân sách token chặn-trước-khi-chạm-GPU, trọng tài với ComfyUI, đo credit, cascade sang cloud khi B bận** |

**Tầng 2 chính là lời giải cho bài toán chia VRAM với ComfyUI** — và nó **không cần
WSL, không cần sleep mode của vLLM**:

```
Job ảnh tới  ──►  gateway gọi  POST /api/models/unload  ──►  VRAM trả về ~20 GB
                                                          ──►  ComfyUI nạp và render
Yêu cầu chat tới ──► llama-swap tự nạp lại (GGUF nằm sẵn trong page cache của 192 GB RAM)
Không ai dùng quá `ttl` giây ──► tự nhả, không cần ai ra lệnh
```

**Ba nguyên tắc bê nguyên từ H37, không bàn lại:**

1. **Máy B không giữ bí mật nền tảng** — không mật khẩu CSDL, không khoá R2 (Q102).
2. **`llama-server` chỉ nghe `127.0.0.1`**, y như ComfyUI. Chỉ `llm_gateway` nghe LAN,
   bearer token, tường lửa mở đúng `192.168.2.17`. **Không bao giờ ra Cloudflare.**
3. **Bận ≠ hỏng.** B bận thì cascade, **không** gọi `api_pool.danh_dau_loi()` — 5 lần
   là key `ltt_local_llm` tự tắt vĩnh viễn.

---

## 4. Chín bước, mỗi bước một cổng chấm

> ⚠️ **Mục này ĐÃ ĐƯỢC THAY.** Bản thi hành chi tiết — dựng trên tài nguyên cộng
> đồng đã tải về, có số đo của đúng card 3090 — nằm ở
> [`LO_TRINH_THI_HANH.md`](LO_TRINH_THI_HANH.md) (10 phase P0–P9).
> Hai đính chính đáng kể so với bảng dưới: **không cần build llama.cpp từ nguồn**
> (đã có binary Windows CUDA chính thức hằng ngày), và **ngữ cảnh khởi điểm là 64K
> với KV `q8_0`**, không phải 32K với KV f16.

| # | Việc | Ở đâu | Tiêu chí QUA |
|---|---|---|---|
| **B0** | Đo nền: VRAM/RAM trống, tốc độ đọc `H:`, ComfyUI có nhả sạch VRAM sau `/free` không (đo bằng `nvidia-smi`, D-013) | B | Bảng số ghi vào `DECISIONS.md` |
| **B1** | Tải `Qwen3.8-27B-Q4_K_M.gguf` (17,1 GB) + `mmproj-F16.gguf` (0,93 GB) về **`H:\LTT_MODELS\llm\`** | B | Checksum khớp. **H: là NVMe, nhanh ~6× so với E:** (D-014) |
| **B2** | llama.cpp CUDA **≥ commit `ece963f41`**, `-DCMAKE_CUDA_ARCHITECTURES=86`. Chạy tay một lượt text | B | Ra chữ **có nghĩa** — commit cũ ra rác |
| **B3** | Bật `--jinja` + `--mmproj`. Thử: 1 câu text · 1 ảnh · 1 tool call | B | Cả ba đúng |
| **B4** | **Đo**: VRAM đỉnh, tok/s, ngữ cảnh an toàn tối đa, nhiệt | B | Biên VRAM **≥ 2 GB**; số ghi vào ngân sách |
| **B5** | `llama-swap` + `ttl`. Đo **thời gian nhả và nạp lại**, 10 lượt. Kiểm ComfyUI lấy lại được VRAM và render xong | B | Nhả sạch; nạp lại **< 30 s**; ComfyUI không OOM |
| **B6** | `llm_gateway/` — auth, `ngan_sach.py`, `busy.py`, catalog **fail-closed**. Test bằng llama-server giả lập, **chạy được trên máy A không cần GPU** | **A** (mã) | Test xanh trong `tools\gate.py` |
| **B7** | Cắm client: Codex (`wire_api="responses"`) · Claude Code (`ANTHROPIC_BASE_URL`) | A | Mỗi client chạy trọn **một việc thật**, có gọi tool |
| **B8** | Provider `ltt_local_llm` + `platform_core/llm/` + cascade cloud + service Windows + tường lửa | A+B | Rơi về cloud đúng lúc B bận; sống qua reboot |

**Mã nguồn viết ở máy A, trong repo này. Model và dữ liệu nằm ở máy B.** Giữ nguyên
Q102, không đổi.

### Lệnh khởi động dự kiến (B3)

```
llama-server -m H:\LTT_MODELS\llm\Qwen3.8-27B-Q4_K_M.gguf ^
  --mmproj H:\LTT_MODELS\llm\mmproj-F16.gguf ^
  --jinja -ngl 99 -c 32768 --flash-attn ^
  --host 127.0.0.1 --port 8281
```

### Cấu hình client (B7)

```toml
# ~/.codex/config.toml  — Codex CLI
model = "qwen38-27b"
model_provider = "ltt_local"
[model_providers.ltt_local]
name = "LTT local VLM"
env_key = "LTT_VLM_KEY"
base_url = "http://192.168.2.66:8299/v1"
wire_api = "responses"
```

```
:: Claude Code (CLI)
set ANTHROPIC_BASE_URL=http://192.168.2.66:8299
```

> **Claude Desktop (app GUI) KHÔNG đổi được model** — không đọc biến môi trường,
> không có ô nhập endpoint. Đường duy nhất là **MCP server** bọc model nhà thành
> **công cụ**: Claude vẫn là bộ não, model nhà làm việc vặt. Đó là một hạng mục
> **riêng**, không nằm trong B0–B8.

---

## 5. Bẫy — đọc trước khi mất buổi tối

| Bẫy | Hậu quả | Cách tránh |
|---|---|---|
| **Thiếu `--jinja`** | Model *"không có mốc nào để biết lượt của bạn kết thúc ở đâu"* → lan man qua stop token, hoặc trả lời cụt | **Bắt buộc có `--jinja`** |
| Quên `--mmproj` | Model **lịch sự từ chối** phân tích ảnh dù nó có vision | Nạp kèm `mmproj-F16.gguf` |
| llama.cpp commit cũ | Nạp bình thường, VRAM đúng, **output là rác** (lỗi CUDA ở lớp DeltaNet) | build ≥ `ece963f41`; **thử tắt MTP trước khi đổ tội cho MTP** |
| `git clone --depth 1` | `git pull` báo "up to date" trong khi trễ hàng trăm commit | clone đầy đủ |
| Thay mỗi file exe, để lib CUDA cũ trong đường dẫn | Lỗi cũ **im lặng** sống tiếp | kiểm bằng `ldd` / `where` |
| Đặt model ở `E:` | E: là SSD SATA 476 MB/s; nạp 17 GB ≈ 36 s thay vì ~6 s | **`H:` (NVMe)** — D-014 |
| Ăn hết biên VRAM để lấy 128K ngữ cảnh | 26 GB > 24 GB, và D-024 đã trả giá cho việc chạy ở 97,5 % | **32K trước, đo rồi mới nâng** |
| Phơi `llama-server` ra LAN | Không có xác thực | chỉ `127.0.0.1`; LAN chỉ qua gateway |
| Gọi `danh_dau_loi()` khi B bận | 5 lần → `ltt_local_llm` tự tắt vĩnh viễn | bận ≠ hỏng |

---

## 6. Kiểm kê model Qwen đang có trên máy B — và đề xuất

Quét ngày 22/08 (`E:\ai\models`, `H:\LTT_MODELS`, HF cache, ollama, LM Studio).
**Tìm thấy đúng ba model Qwen, tất cả nằm trong `E:\ai\models\vlm\`:**

| Model | Dung lượng | Ghi chú |
|---|---|---|
| `Qwen2.5-VL-7B-Instruct` | **15,46 GiB** | bf16 safetensors, 5 shard |
| `Qwen3-VL-8B-Instruct` | **16,34 GiB** | bf16 safetensors, 4 shard |
| `Qwen3-VL-8B-Thinking` | **16,34 GiB** | bf16 safetensors, 4 shard |
| **Tổng** | **48,14 GiB** | |

Không có Qwen nào trong `H:\LTT_MODELS` (chỉ 3 checkpoint HiDream-O1 của H37), không
có trong HF cache (chỉ whisper/clip/demucs), không có ollama, không có LM Studio.

### Hai sự thật phải nói rõ trước khi xoá

**(a) Chúng thuộc kho model của DỰ ÁN VIDEO.** `E:\ai\models\` chính là `base_path`
mà `extra_model_paths.yaml` trỏ ComfyUI vào, và `E:\LTT AI\src\ltt\` **có một module
VLM**. Ba model này gần như chắc chắn là bộ chú thích khung hình / sinh prompt của
dự án đó. Chủ dự án đã nói *"không lo, tôi sẽ nối lại sau"* — đây chỉ là ghi lại cho
đúng: **cái gì sẽ gãy, gãy ở đâu.**

**(b) Xoá KHÔNG mua được gì về mặt kỹ thuật.**

| | |
|---|---|
| Đĩa trống | C: 393 · E: 339 · G: 373 · **H: 818** · I: 373 GB |
| Model mới cần | **18,03 GB** trên `H:` |
| Xung đột VRAM | là chuyện **cái gì đang CHẠY**, không phải cái gì **nằm trên đĩa** |

Model nằm im trên đĩa **không tốn một byte VRAM nào** và không tranh chấp gì.

### Đề xuất: **DI DỜI**, không xoá

```
E:\ai\models\vlm\  ──►  E:\ai\models\_vlm_TAM_CAT_2026-08-22\
```

Hiệu quả **giống hệt** việc xoá — ComfyUI và dự án video không còn nạp được chúng,
không còn nhầm lẫn model nào là model nào — nhưng:

- **hoàn tác trong 1 giây** thay vì tải lại 48 GiB (nhiều giờ);
- đúng thói quen đã có trên máy B: thư mục `E:\.nexus-quarantine` là cùng một ý;
- khi chủ dự án "nối lại sau", chỉ cần đổi tên thư mục về chỗ cũ.

Nếu vẫn muốn **xoá cứng** thì đó là quyền của chủ dự án — chỉ cần nói một câu, tôi
làm. Nhưng tôi không tự xoá 48 GiB trong thư mục của một dự án khác khi có phương án
đạt cùng mục tiêu mà không mất gì.

---

## 7. Nguồn

- `llama-server` — danh sách endpoint (`/v1/responses`, `--jinja`, `--mmproj`): https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- Anthropic Messages API trong llama.cpp (PR #17570): https://huggingface.co/blog/ggml-org/anthropic-messages-api-in-llamacpp
- Kích thước GGUF thật · KV cache · bẫy template: https://dev.to/purpledoubled/run-qwen-38-27b-locally-real-gguf-sizes-the-kv-cache-trick-and-the-template-trap-114j
- GGUF + mmproj: https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/tree/main
- Qwen3.8-27B chạy thật trên 3090 (vision + MTP): https://github.com/ggml-org/llama.cpp/discussions/27164
- Cờ MTP: https://github.com/sudoingX/qwen38-mtp
- `llama-swap` — TTL, unload, groups: https://github.com/mostlygeek/llama-swap
- Codex config: https://developers.openai.com/codex/config-reference
