# Nghiên cứu khả thi — VLM nội bộ Qwen3.8-27B + cổng API

**2026-08-22.** Tài liệu **nghiên cứu**, chưa phải quyết định. Nó trả lời ba câu:
model nào, chạy được trên phần cứng đang có không, và xây theo trình tự nào.

Mọi con số về máy A/B đọc thẳng từ `docs/ANH_NOI_BO/` (đã đo thật). Mọi con số về
model đọc từ model card, vLLM recipe và **repo cộng đồng đã chạy đúng model này
trên đúng card 3090** — không có số nào tôi tự ước lượng. Chỗ nào chưa ai đo, tôi
ghi rõ là chưa đo.

---

## 1. Model: xác định đúng tên trước đã

`Qwen3.8-27B` là model có thật, **không** thuộc họ `Qwen3-VL`. Hai họ khác nhau:

| | Qwen3-VL (2025) | **Qwen3.8-27B (13–14/08/2026)** |
|---|---|---|
| Kích cỡ | dense 2B/4B/8B/32B · MoE 30B-A3B/235B-A22B | **27–28B dense, một cỡ** |
| Attention | full attention toàn bộ | **hybrid** — xem dưới |
| Vision | là mục đích chính | **có sẵn vision tower**, đồng thời là model text/agentic mạnh |
| Giấy phép | Apache-2.0 | **Apache-2.0** ✅ bán được |

**Kiến trúc — chỗ này quyết định VRAM, phải đọc kỹ:**

```
64 lớp  =  16 × ( 3×(Gated DeltaNet -> FFN)  +  1×(Gated Attention -> FFN) )
           └── 48 lớp linear attention          └── 16 lớp full attention
hidden 5.120 · FFN 17.408
Gated Attention: 24 head Q · 4 head KV · head_dim 256
Gated DeltaNet:  48 head V · 16 head QK · head_dim 128 · state hằng số
Kiến trúc: Qwen3_5ForConditionalGeneration · có sẵn MTP draft head
Ngữ cảnh: 262.144 native, nới tới 1.000.000 bằng YaRN
```

**Hệ quả thực dụng:** chỉ **16/64 lớp** giữ KV cache. Một model dense 64 lớp bình
thường (GQA 8 KV head × 128) tốn ~262 KiB/token; model này tốn
`16 lớp × 4 head × 256 × 2(K,V) × 2 byte` = **64 KiB/token** — **nhỏ hơn ~4 lần**.
Ở 32K ngữ cảnh, KV chỉ ~2 GiB (fp16) hoặc ~1 GiB (fp8/int8 KV).

Đó là lý do một model 27B lại vừa được 24 GB **cùng với** ngữ cảnh dài — điều mà
một model 27B thế hệ trước không làm được. *(Kích thước state hằng số của 48 lớp
DeltaNet **chưa đo**; cộng đồng báo nó nhỏ, nhưng đừng chép con số đó vào ngân
sách VRAM khi chưa tự đo.)*

---

## 2. Sự thật phần cứng — và một chốt chặn cứng

| | **MÁY A** — production | **MÁY B** — máy AI |
|---|---|---|
| GPU | **2× RTX 5060 Ti 16 GB** — Blackwell, sm 12.0 | **1× RTX 3090 24 GB** — Ampere, **sm 8.6** |
| RAM | 32 GB | 192 GB |
| Đang làm gì | web + worker + Postgres + sidecar Codex, **phục vụ khách trả tiền** | ComfyUI (ảnh) + dự án video `E:\LTT AI` |

### 2.1. 3090 KHÔNG chạy được bản lượng tử hoá chính thức

vLLM recipe của Qwen khuyến nghị **NVFP4** (24,6 GiB, một GPU Blackwell). NVFP4
cần tensor core FP4 → **chỉ có từ Blackwell**. FP8 tensor core → **chỉ từ Ada 8.9**.
3090 là **8.6**, không có cả hai.

Dự án này **đã đo và đã trả giá cho bài học đó**: `DECISIONS.md` D-021 ghi fp8 trên
đúng card 3090 này vừa **chậm hơn** (2,04 vs 1,09 s/bước) vừa **tốn VRAM hơn 42 %**
(23.992 vs 16.860 MB) so với bf16.

⇒ Trên 3090, đường duy nhất là **INT4** (AWQ / GPTQ / AutoRound W4A16) hoặc **GGUF**.
Cả hai chỉ để **vừa VRAM**, không để nhanh hơn.

### 2.2. 🔴 Chốt chặn: máy B KHÔNG còn một GB VRAM nào

Ba con số đã đo, cùng một card 24.576 MB:

| Việc | VRAM | Nguồn |
|---|---|---|
| Ảnh (ComfyUI, model **thường trú** giữa các job) | **23.764 MB trung vị · 23.967 đỉnh = 97,5 %** | D-022 |
| Video (`E:\LTT AI`, dùng **chung** ComfyUI đó) | **24.251 / 24.576 = 98,7 %** | nhật ký sự cố 19/08 |
| VLM 27B INT4 (cần thường trú để hữu dụng) | **17,9 – 23,0 GB** | mục 3 |

`23,7 + 19 = 42,7 GB` trên một card `24,6 GB`. **Không có tham số nào sửa được điều
này.** Đây là kết luận vật lý, không phải chính sách — đúng như §2 của
`CHIA_GPU_VOI_VIDEO.md` đã kết luận cho cặp ảnh/video.

Và VLM **tệ hơn** ảnh/video ở một điểm: ảnh và video là việc theo lô, chờ được. Một
VLM cắm vào Codex là **việc tương tác** — nạp lại 18 GB trọng số mỗi lượt là hàng
chục giây trước mỗi câu trả lời. Không dùng được.

---

## 3. Model chạy được trên 3090 không? — Có, cộng đồng đã chứng minh, hai ngăn xếp

### 3.1. vLLM — nhanh nhất, **hiện chỉ text**

Repo [`syv-ai/qwen38-27b-rtx3090`](https://github.com/syv-ai/qwen38-27b-rtx3090) —
đúng model, đúng một card 3090:

| | |
|---|---|
| vLLM | **0.27.1** + **9 patch** trong `patches/` (phải áp lại sau mỗi lần nâng cấp) |
| Lượng tử | thân **W4A16 AutoRound** · KV **fp8** · `lm_head`+embedding **int8 GPTQ** · MTP drafter **int4 GPTQ** |
| VRAM đỉnh | **23,0 GiB** @ 64 request đồng thời |
| Ngữ cảnh | 64k–150k mặc định · 150k–262k chế độ `long` |
| Tốc độ | **114–124 tok/s** một người dùng (MTP) · **~1.000–1.222 tok/s** @ 64 đồng thời |
| Vision | ⚠️ **README không nói tới multimodal.** Coi như **chưa chứng minh** |

### 3.2. llama.cpp — chậm hơn, nhưng **vision đã chạy**

[Thảo luận `ggml-org/llama.cpp#27164`](https://github.com/ggml-org/llama.cpp/discussions/27164) —
cũng đúng model, đúng 3090:

| | |
|---|---|
| Build | **≥ commit `ece963f41`** (build ~10450). Commit cũ (`221f0f6`) **ra rác** — lỗi CUDA ở lớp DeltaNet |
| Cờ build | `cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_BUILD_TYPE=Release` |
| VRAM | **~19 GB** |
| Tốc độ | **~42,9 tok/s** |
| Vision (mmproj) | ✅ **chạy** · Flash Attention ✅ · MTP ✅ |

Bản Unsloth Q4_K_XL: **17,9 GB**, 32K ngữ cảnh KV f16 → 43,9 / 79,8 tok/s.

### 3.3. Nhưng để cắm vào Codex thì **buộc phải là vLLM**

Từ **tháng 2/2026 Codex CLI bỏ `wire_api = "chat"`**; giá trị hợp lệ duy nhất là
`responses` (OpenAI Responses API). `llama-server` chỉ nói Chat Completions.

```toml
# ~/.codex/config.toml
model = "qwen38-27b"
model_provider = "ltt_local"

[model_providers.ltt_local]
name = "LTT local VLM"
env_key = "LTT_VLM_KEY"
base_url = "http://192.168.2.66:8299/v1"
wire_api = "responses"
```

vLLM phải bật thêm: `--reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser <parser>`.

> **⚠️ Mâu thuẫn phải nhìn thẳng:** đường có **vision** (llama.cpp) và đường chạy
> được **Codex** (vLLM) hiện là **hai đường khác nhau**, và trên một card 3090
> **không thể giữ thường trú cả hai**. Trước khi hứa "một cổng cho mọi việc",
> phải tự kiểm chứng vLLM 0.27.1 phục vụ ảnh cho Qwen3.8-27B trên sm_86 — recipe
> chính thức nói *"text serving is what this recipe covers and what has been verified"*.

---

## 4. Bốn phương án đặt model ở đâu

| | Nơi đặt | Được | Mất |
|---|---|---|---|
| **PA-1** | Máy A, **NVFP4 TP=2** trên 2× 5060 Ti | Blackwell có **NVFP4 native**; trọng số chỉ **~14 GB** chia đôi → vừa 2×16 GB. Cộng đồng đã chạy Qwen3.6-27B NVFP4+MTP trên đúng cặp 5060 Ti: **30 tok/s** | A **là production**, 32 GB RAM, GPU đang chạy job khách (whisper/YOLO/upscale). Đây **đúng lý do Q102 từ chối** đặt model ảnh lên A |
| **PA-2** | Máy B, chia lượt với ComfyUI | Không tốn tiền | Nạp/nhả 18 GB mỗi lần đổi việc → Codex không dùng được. **Loại** |
| **PA-3** | **GPU/máy thứ ba riêng cho VLM** | Cách duy nhất giữ model thường trú mà không đụng ai. Giữ nguyên kiến trúc Q102 | Tốn tiền thật |
| **PA-4** | **VLM nhỏ** (Qwen3-VL-8B AWQ ~6–9 GB) trên **một** card 5060 Ti của A | Dựng được **cổng + hợp đồng API + tích hợp Codex ngay hôm nay**, rủi ro nhỏ, có đường nâng cấp | Chất lượng dưới 27B |

**Khuyến nghị: PA-4 trước, PA-3 sau.**

Lý do: thứ có giá trị lâu dài trong yêu cầu này **không phải model** — mà là **cổng
API và hợp đồng** ("cắm vào Codex, và cắm vào các VLM sau này"). Cổng đó dựng và
kiểm được với model 8B trên phần cứng đang có, **không đụng vào GPU của B và không
đem rủi ro OOM vào giữa job khách trên A**. Khi có GPU riêng (PA-3), đổi model là
đổi một dòng cấu hình — hợp đồng, billing, cascade, test đã đứng sẵn.

PA-1 chỉ nên xét **sau khi** đo thật VRAM còn trống trên hai card của A trong giờ
cao điểm. Chưa đo thì không chạy — đúng nguyên tắc `ngan_sach.py`.

---

## 5. Kiến trúc cổng — soi gương `render_gateway/`

Bài học lớn nhất của H37 nên dùng lại nguyên: **cổng không phải là engine.** vLLM
**đã là** máy chủ OpenAI rồi; đừng viết lại `/v1/chat/completions`.

```
Máy A (production)                              Máy đặt GPU VLM
├─ platform_core/providers.py  + "ltt_local_llm"      llm_gateway :8299
├─ platform_core/llm/  <-- adapter dùng chung   ---->  (FastAPI + bearer,
├─ apps/…  ·  sidecar Codex                            chính sách + trọng tài)
└─ sổ credit · hàng đợi job (DÙNG LẠI, không dựng cái thứ hai)      │ loopback
                                                                    v
                                                        vLLM :8000 (CHỈ 127.0.0.1)
```

`llm_gateway/` **chỉ làm chính sách**, chép đúng bộ khung của `render_gateway/`:

| File | Việc | Lấy lại từ |
|---|---|---|
| `config.py` | mọi tham số từ biến môi trường | `render_gateway/config.py` |
| `busy.py` | GPU có bận không · ETA · **đếm tiến trình chứ không đo ngưỡng VRAM** | D-013, D-022 |
| `ngan_sach.py` | **chặn trước khi chạm GPU**: trần token vào/ra, trần số ảnh/request, trần ngữ cảnh — theo số **đã đo** | `render_gateway/ngan_sach.py` |
| `api.py` | `/health` · `/v1/models` · proxy `/v1/responses` + `/v1/chat/completions` | `render_gateway/api.py` |
| `catalog.py` | model nào mở, chế độ nào mở — **fail-closed như Q92** | `render_gateway/catalog.py` |

Ba nguyên tắc bê nguyên, không bàn lại:

1. **Máy GPU không giữ bí mật nền tảng** — không mật khẩu CSDL, không khoá R2 (Q102).
2. **vLLM chỉ nghe `127.0.0.1`**, y như ComfyUI. Chỉ cổng chính sách nghe LAN, bearer
   token, tường lửa mở cho đúng một IP. **Không bao giờ đưa ra Cloudflare.**
3. **Bận ≠ hỏng.** Khi GPU bận, **không** gọi `api_pool.danh_dau_loi()` cho key
   `ltt_local_llm` — cooldown rồi `disable` sau 5 lần sẽ tự tắt vĩnh viễn model nhà.

---

## 6. Quy trình xây dựng — 8 cổng, cổng nào chưa qua thì không đi tiếp

| Cổng | Việc | Tiêu chí qua |
|---|---|---|
| **V0** | Đo: VRAM còn trống thật trên **cả hai card của A** trong giờ cao điểm · dung lượng đĩa · PCIe link width | Có bảng số, ghi vào `DECISIONS.md` |
| **V1** | Chốt PA (mục 4) — **cần chủ dự án quyết**, vì nó tiêu tiền hoặc tiêu rủi ro production | Một dòng quyết định Q10x |
| **V2** | Dựng vLLM trên máy đích, model **8B trước** (PA-4). Cửa sổ có người canh | `vllm serve` lên, `/v1/models` trả đúng |
| **V3** | **Kiểm vision thật**: gửi ảnh qua `image_url`, đọc kết quả. Đo VRAM đỉnh, tok/s | Ảnh vào → chữ ra đúng; số đo ghi lại |
| **V4** | `llm_gateway/` — auth, `ngan_sach`, `busy`, catalog fail-closed. Test bằng vLLM giả lập, **chạy được trên máy A không cần GPU** | Test xanh trong `tools\gate.py` |
| **V5** | Cắm Codex: `wire_api = "responses"`, tool calling, reasoning parser | Codex gọi được tool, chạy hết một việc thật |
| **V6** | Provider `ltt_local_llm` + `platform_core/llm/` + cascade sang cloud khi bận | Rơi về cloud đúng lúc bận, khách không chờ |
| **V7** | Nâng lên 27B **chỉ khi** V0/V1 cho phép. Áp 9 patch của repo cộng đồng, đo lại từ đầu | VRAM đỉnh < trần đã chốt, có biên ≥ 2 GB |

---

## 7. Bẫy cộng đồng đã dính — đọc trước khi mất buổi tối

| Bẫy | Hậu quả | Cách tránh |
|---|---|---|
| `git clone --depth 1` llama.cpp | `git pull` báo "up to date" trong khi trễ **hàng trăm commit** | clone đầy đủ |
| Thay mỗi file thực thi, để `libggml-cuda.so` cũ trong `LD_LIBRARY_PATH` | Lỗi cũ **im lặng** tồn tại tiếp | kiểm bằng `ldd` |
| llama.cpp commit cũ + DeltaNet | Model nạp bình thường, VRAM đúng, **output là rác** | build ≥ `ece963f41`; **thử tắt MTP trước khi đổ tội cho MTP** |
| vLLM cudagraph `FULL_AND_PIECEWISE` | Hỏng output | dùng `PIECEWISE` |
| DFlash speculative decoding trên Ampere | `head_dim=256` non-causal **không có backend attention nào** | tắt DFlash trên 3090, dùng MTP |
| 4 draft trên backend FlashInfer | `illegal memory access` | giảm số draft |
| Codex `wire_api = "chat"` | Không kết nối được (đã bỏ từ 02/2026) | `responses` |
| Nâng cấp vLLM | Mất **9 patch** của repo 3090 | ghim phiên bản; áp lại có chủ ý |

---

## 8. Bốn câu cần chủ dự án chốt

1. **PA nào?** (mục 4) — PA-4 rồi PA-3 là khuyến nghị của tôi; PA-1 cần chấp nhận
   rủi ro trên máy production.
2. **Nếu PA-3: mua GPU gì?** Một card Blackwell 24–32 GB mở khoá NVFP4 → đúng đường
   chính thức của model, thay vì INT4 vá víu như trên 3090.
3. **Vision là bắt buộc ngay, hay chờ được?** Nếu bắt buộc ngay mà vLLM chưa xác
   minh multimodal trên sm_86 → phải chạy **hai tiến trình** (vLLM cho Codex,
   llama.cpp cho ảnh) → càng khẳng định cần GPU riêng.
4. **Model 8B tạm dùng bản nào?** `Qwen3-VL-8B` là ứng viên rõ nhất (Apache-2.0,
   AWQ ~6–9 GB, vLLM đỡ sẵn multimodal).

---

## Nguồn

- Model card: https://huggingface.co/Qwen/Qwen3.8-27B
- vLLM recipe chính thức: https://recipes.vllm.ai/Qwen/Qwen3.8-27B
- Qwen3.8-27B trên **một** RTX 3090 (vLLM): https://github.com/syv-ai/qwen38-27b-rtx3090
- Qwen3.8-27B trong llama.cpp, vision chạy: https://github.com/ggml-org/llama.cpp/discussions/27164
- Cờ MTP cho Qwen3.8-27B: https://github.com/sudoingX/qwen38-mtp
- vLLM đỡ kiến trúc hybrid Gated DeltaNet: https://vllm.ai/blog/2025-09-11-qwen3-next
- Bản AWQ-INT4: https://huggingface.co/cyankiwi/Qwen3.8-27B-AWQ-INT4
- Codex + vLLM: https://docs.vllm.ai/en/latest/serving/integrations/codex/
- Cấu hình provider Codex: https://developers.openai.com/codex/config-reference
- Qwen3-VL (họ khác): https://github.com/QwenLM/Qwen3-VL · https://arxiv.org/abs/2511.21631
- 2× RTX 5060 Ti + NVFP4: https://note.com/cute_agapan9087/n/nb4b3456ca8b4

---

# Phụ lục A — SỐ ĐO THẬT 22/08/2026 và trả lời bốn câu hỏi

> ⚠️ Phụ lục này **sửa khuyến nghị ở mục 4**. Mục 4 viết khi chưa đo topology PCIe.
> Đo xong thì kết luận đổi: **máy B, không phải máy A.** Lý do ở §A.4.

## A.1. Số đo — `nvidia-smi`, không phải suy đoán

### MÁY A — `DESKTOP-H9AGFUQ` (production)

| | GPU 0 | GPU 1 |
|---|---|---|
| Bus | `0000:01:00.0` | `0000:03:00.0` |
| VRAM | 16.311 MiB | 16.311 MiB |
| **Link width** | **x8** | **x4** ⚠️ (khe chipset) |
| Link gen | card đỡ **gen 5** · **host chỉ gen 3** | như trên |
| **Băng thông thực** | **~7,9 GB/s** | **~3,9 GB/s** |
| Lúc đo | rảnh | **99 % util · 12.555 MiB đang dùng** |

- CPU **i9-10900K** trên **Z490 GAMING X** → chỉ có **PCIe 3.0**, 16 làn từ CPU.
  Card 5060 Ti là thiết bị **x8**, nên GPU0 chạy đủ x8; GPU1 rơi xuống **x4 qua chipset**,
  và làn đó **chia băng thông DMI với SSD/LAN/USB**.
- **RAM hệ thống: 31,85 GB** — tổng cộng, cho cả máy.
- Đang chạy: `LTTStudioWeb`, `LTTStudioWorker`, `LTTStudioCodex`, `LTTNexus`, `postgresql-x64-17`.
- 🔴 Kẻ đang giữ 12,5 GB của GPU1: `D:\BOT GEMINI\vendor\upscale\engine\realesrgan-ncnn-vulkan.exe`
  — tức **kho tham chiếu CHỈ ĐỌC đang phục vụ người dùng thật ở cổng 8000**.

### MÁY B — `MAY-B`

| | |
|---|---|
| GPU | RTX 3090 · **24.576 MiB** · sm 8.6 |
| **Link width** | **x16** · gen 3 → **~12–15 GB/s thực** |
| Lúc đo | 17.547 dùng / 6.779 trống · 100 % util |
| RAM | **192 GB** |
| **WSL** | ❌ **CHƯA CÀI** (`wsl --status` → *not installed*) |

## A.2. Câu 1 — 2× 5060 Ti có chạy nổi Qwen3.8-27B không?

**VRAM thì thừa.** NVFP4 ~14 GB, AWQ-INT4 ~16 GB, chia trên 32 GB → dư chỗ cho ngữ cảnh dài.
**Nhưng phải trả ba cái giá, và giá thứ ba là giá đắt nhất.**

| # | Cái giá | Chi tiết |
|---|---|---|
| 1 | **Cầu nối giữa hai card là PCIe 3.0 x4** | `TP=2` bắn **2 all-reduce mỗi lớp × 64 lớp** — đúng thứ đường hẹp ghét nhất. Phải chuyển sang **`PP=2`** (chỉ 1 lần truyền/token), đổi lấy TTFT cao hơn và ~10–15 % throughput thấp hơn ở batch 1 |
| 2 | **NVFP4 trên SM120 chưa êm** | Kernel FP4 cho GeForce Blackwell cần patch vLLM + FlashInfer + CUTLASS; cộng đồng đang bisect nightly. Né bằng AWQ-INT4 (Marlin) thì chạy ngay — **nhưng khi đó vứt đúng ưu thế FP4 của Blackwell**, và lợi thế duy nhất của máy A so với 3090 biến mất |
| 3 | 🔴 **Đây là máy production, GPU đang bận thật** | GPU1 đang bị BOT GEMINI chiếm 12,5/16 GB. RAM hệ thống **31,8 GB** phải nuôi web + worker + Codex + Postgres. Nạp thêm 16 GB trọng số vào đây là đem rủi ro vào giữa job của khách trả tiền |

⇒ **Chạy được, nhưng máy A là chỗ tệ nhất trong ba lựa chọn để đặt nó.**

## A.3. Câu 2 — RAM 192 GB của máy B có thay VRAM được không?

**Hai câu trả lời khác nhau. Đừng trộn.**

### (a) Làm VRAM mở rộng lúc suy luận → **KHÔNG**. Đây là số học, không phải ý kiến.

Qwen3.8-27B là **dense** — mỗi token đọc **toàn bộ** trọng số. Phần nằm ở RAM phải bò
qua PCIe **mỗi token một lần**:

| Cấu hình | Byte qua PCIe / token | Ở 12 GB/s (x16 máy B) | Trần tốc độ |
|---|---|---|---|
| Toàn bộ trong VRAM | 0 | — | **42–124 tok/s** |
| Offload 20 % | ~3,5 GB | ~0,29 s | **~3,4 tok/s** |
| Offload toàn bộ | ~17 GB | ~1,4 s | **~0,7 tok/s** |

⇒ Offload là **giảm lùi nặng hơn nhiều** so với việc đổi sang model nhỏ hơn.

> **Ngoại lệ đáng biết:** điều trên đúng vì model **dense**. Với **MoE** (vd 35B-A3B, chỉ
> 3B hoạt động mỗi token) thì offload chuyên gia sang RAM lại **rất hợp lý** — đó là
> cả điểm mạnh của MoE. Nhưng anh chốt 27B dense, không giảm lùi, nên đường đó đóng.

### (b) Làm kho **chuyển đổi** VRAM ↔ RAM → **CÓ, và đúng là tính năng chính thức**

vLLM **Sleep Mode** sinh ra đúng cho việc này:

```
vllm serve … --enable-sleep-mode          (kèm VLLM_SERVER_DEV_MODE=1)
POST /sleep?level=1   → trọng số ĐẨY SANG RAM, KV cache bỏ, giải phóng >90 % VRAM
POST /wake_up         → nạp lại từ RAM: ~3–6 s với model lớn
```

Nhanh hơn nạp lại từ đĩa **18–200 lần**. Và nó chạy **tốt hơn ở máy B**, không phải máy A:

| | Máy A | **Máy B** |
|---|---|---|
| RAM chứa trọng số lúc ngủ | 31,8 GB **tổng**, đang nuôi Postgres + web + worker | **192 GB** |
| Đường nạp lại | x8 (7,9) / **x4 (3,9 GB/s)** | **x16 (12–15 GB/s)** ✅ |

⇒ **Trực giác của chủ dự án đúng.** Cơ chế "RAM giữ, VRAM luân phiên" là có thật, có
API, và máy B là máy hợp nhất để làm.

## A.4. Câu 3 — Nên chạy máy nào? → **MÁY B**

| | Máy A (2× 5060 Ti) | **Máy B (1× 3090)** |
|---|---|---|
| 27B INT4 vừa **một** card? | ❌ phải chẻ đôi qua x4 | ✅ **17,9–23 GB vừa 24 GB** |
| PCIe lúc suy luận | all-reduce/hidden-state qua x4 | **không có gì đi qua PCIe** |
| Sleep-mode swap | RAM 31,8 GB, đường x4 | **192 GB, đường x16** |
| Máy production? | ✅ **có, đang phục vụ khách** | ❌ không |
| GPU đang bận? | ✅ BOT GEMINI giữ 12,5 GB | ⚠️ ComfyUI/video — **nhưng chính ta điều phối được** |
| FP4 tensor core | có, **nhưng phải vá mới dùng được** | không (Ampere) |

**Ba cái phải chấp nhận nếu chọn B:**

1. **VLM không dùng được trong lúc B chạy video.** Lượt video ăn 98,7 % VRAM và
   **không cắt ngang được** — đó là dự án khác, cổng của ta không điều khiển nó.
   → khi đó **cascade sang cloud**, đúng tầng 3 của `CHIA_GPU_VOI_VIDEO.md`.
2. **Đổi lượt với ComfyUI mất ~3–6 s mỗi chiều** (sleep/wake). Chấp nhận được cho
   việc tương tác; **phải đo lại thật**, đừng tin con số của blog.
3. 🔴 **Máy B chưa cài WSL, mà vLLM đường chính thức trên Windows là WSL2.**
   Ba lối ra, phải thử mới biết:
   - cài WSL2 (**cần reboot** — mà reboot máy B là chuyện nhạy cảm, xem D-025);
   - bản fork Windows native `SystemPanic/vllm-windows` (v0.20.0, có NCCL + TP/PP);
   - **llama.cpp** — chạy native Windows ngay, **vision đã chứng minh**, đổi lại
     ~42,9 tok/s thay vì ~114 và **không nói được Responses API cho Codex**.

## A.5. Câu 4 — Codex và Claude Desktop là HAI đường khác nhau

| Client | Cắm được model nhà? | Bằng cách nào |
|---|---|---|
| **Codex CLI** | ✅ | `wire_api = "responses"` → **buộc phải là vLLM** (llama.cpp không nói Responses API) |
| **Claude Code (CLI)** | ✅ | `ANTHROPIC_BASE_URL` → cần **Anthropic Messages API**. llama.cpp / LM Studio ≥0.4.1 / Ollama **có `/v1/messages` native**; vLLM **không** → phải có proxy dịch |
| **Claude Desktop (app GUI)** | ❌ **KHÔNG đổi được model** | App không đọc biến môi trường, không có ô nhập endpoint. Đường duy nhất: **MCP server** bọc model nhà thành **công cụ** — Claude vẫn là bộ não, model nhà làm việc vặt (đọc log, đọc ảnh, tóm tắt) |

⇒ Hai client, hai giao thức ngược nhau: **Codex cần Responses (vLLM), Claude Code cần
Messages (llama.cpp)**. Đó chính là lý do phải có `llm_gateway` ở giữa thay vì phơi
thẳng engine — cổng dịch giao thức, còn engine giữ nguyên.

## A.6. Việc phải đo trước khi viết dòng code nào (V0 sửa lại)

| # | Đo gì | Vì sao |
|---|---|---|
| 1 | vLLM lên được trên máy B bằng lối nào (WSL2 / fork native / không được) | Quyết định cả kiến trúc. **Chưa xong thì mọi thứ sau là giả định** |
| 2 | VRAM đỉnh thật của Qwen3.8-27B AWQ-INT4 trên 3090 ở ngữ cảnh mục tiêu | `ngan_sach.py`: chưa đo thì không chạy |
| 3 | Thời gian `/sleep` và `/wake_up` thật, đo 10 lượt | Toàn bộ phương án đổi lượt đứng trên con số này |
| 4 | Vision qua vLLM trên sm_86 — có hay không | Nếu không → phải hai engine → tính lại VRAM |
| 5 | ComfyUI có nhả sạch VRAM sau `/free` không (đo bằng `nvidia-smi`, D-013) | Nếu nó giữ lại thì swap vô nghĩa |

## A.7. Nguồn bổ sung

- vLLM Sleep Mode: https://docs.vllm.ai/en/latest/features/sleep_mode/ · https://vllm.ai/blog/2025-10-26-sleep-mode
- NVFP4 trên GeForce Blackwell SM120: https://github.com/lna-lab/blackwell-geforce-nvfp4-gemm
- vLLM SM120 NVFP4 (PR/issue): https://github.com/vllm-project/vllm/pull/21309 · https://github.com/vllm-project/vllm/issues/33416
- TP vs PP khi không có NVLink: https://docs.vllm.ai/en/stable/serving/parallelism_scaling/
- vLLM trên Windows 2026: https://fazm.ai/t/vllm-windows-support-2026
- Claude Code + model local qua `ANTHROPIC_BASE_URL`: https://renezander.com/guides/claude-code-local-llm-anthropic-base-url/
- Claude Desktop + model local qua MCP: https://bestllmfor.com/guides/claude-desktop-mcp-local-llm-setup/
