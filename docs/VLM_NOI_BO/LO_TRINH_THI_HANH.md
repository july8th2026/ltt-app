# Lộ trình thi hành — VLM vận hành Qwen3.8-27B trên máy B

**2026-08-22.** Đây là **kế hoạch thi hành chi tiết**, thay thế §4 của
[`KE_HOACH_TRIEN_KHAI_MAY_B.md`](KE_HOACH_TRIEN_KHAI_MAY_B.md).

Nguyên tắc viết tài liệu này, theo yêu cầu chủ dự án: **không tự suy ra con số nào.**
Mọi tham số dưới đây lấy từ **tài nguyên cộng đồng đã tải về máy** (§0) — trong đó có
sweep của **đúng card RTX 3090** với **đúng model này**. Chỗ nào cộng đồng chưa đo,
tôi ghi rõ *"ta phải đo"* và đặt nó thành cổng chặn.

---

## 0. Tài nguyên đã tải về — nền của toàn bộ kế hoạch

### 0.1. Repo đã clone về `D:\LTT_VLM_REFS\` (trên máy A)

| Repo | Thứ giá trị nhất trong đó | Dùng ở phase |
|---|---|---|
| **`qwen38-mtp`** (sudoingX) | `sweeps/rtx-3090.md` — **sweep của đúng card ta có** · `README.md` — **7 luật cộng đồng** · **`probe.py`** — công cụ đo chuẩn mà mọi số trong bảng đều dùng · `serve_mtp.sh` | **P2, P5** |
| **`qwen38-27b-rtx3090`** (syv-ai) | **`docs/gotchas.md` — 18 bẫy, mỗi bẫy tốn nhiều giờ của họ** · `bench/quality_battery.py` (perplexity + GSM8K) · `docs/long-context.md` · `docs/quality.md` | **P3, P5, P6** |
| **`llama-swap`** (mostlygeek) | `config.example.yaml` (có chú thích đầy đủ) · `config-schema.json` · cơ chế **`ttl` tự nhả VRAM** + `POST /api/models/unload` | **P6** |

### 0.2. Nhị phân và trọng số — URL chính xác, tải ở P1

| Thứ | Nguồn | Dung lượng |
|---|---|---|
| **llama.cpp Windows CUDA** | `llama-b10580-bin-win-cuda-13.3-x64.zip` (release **b10580**, 22/08/2026) | 140,1 MB |
| CUDA runtime kèm theo | `cudart-llama-bin-win-cuda-13.3-x64.zip` | 372,9 MB |
| **llama-swap Windows** | `llama-swap_250_windows_amd64.zip` (v250, 14/08/2026) | 12,7 MB |
| **Trọng số** | `unsloth/Qwen3.8-27B-GGUF` → `Qwen3.8-27B-UD-Q4_K_M.gguf` | **15,33 GiB** |
| **Vision** | cùng repo → `mmproj-F16.gguf` | **0,86 GiB** |

> ⭐ **Không phải build từ nguồn.** Kế hoạch trước dự tính phải biên dịch llama.cpp
> bằng CMake + MSVC. **Không cần nữa**: llama.cpp phát hành **binary Windows CUDA
> chính thức mỗi ngày**, và b10580 ra sáng 22/08 — **cao hơn nhiều** so với mốc
> `ece963f41` (~b10450) mà cộng đồng xác định là chỗ sửa xong lỗi CUDA ở lớp DeltaNet.
> Cắt hẳn một ngày công và một lớp rủi ro.
>
> Máy B chạy **torch cu130 / driver 610.88** → lấy bản **cuda-13.3**.

---

## 1. Cấu hình đích — chốt từ số đo của ĐÚNG card 3090

Bảng dưới **chép từ `sweeps/rtx-3090.md` và bảng cộng đồng**, không phải ước lượng.
Tất cả đều dùng `probe.py`, `--parallel 1`, bỏ lần chạy đầu:

| Cấu hình trên 3090 24 GB | Ngữ cảnh | KV | VRAM nền | VRAM +MTP | Decode nền | **Decode +MTP** | n-max |
|---|---|---|---|---|---|---|---|
| **Q4_K_M, build b10450** | **131K** | **q8_0** | — | — | 41,3 | **63,5** | **2** |
| UD-Q4_K_XL (OC) | 32K | f16 | **20,5 GB** | **21,4 GB** | 43,9 | **79,6** | 2 |
| Q4_K_M, turboquant | 131K | q4_0 | — | — | 39,8 | 61,5 | 6 |
| Q4_K_M, giới hạn 250 W | 131K | — | — | — | 31,9 | 52,8 | 4 |
| Q4_K_M, KV turbo3 | 200K | turbo3 | 23,0→**23,3 GB** ⚠️ | | 37,2 | 54,2 | 3 |
| *(4090 24 GB — bằng chứng vision)* | *200K* | *q4_0* | *mmproj nạp, 888 MB trên GPU* | | | | |

**Cấu hình khởi điểm chốt cho máy B** — hàng `b10450` là hàng gần ta nhất (cùng card,
cùng quant, cùng dòng build):

```
:: === ltt_llm_ops === van hanh, ngu canh dai, KHONG vision
llama-server.exe ^
  -m H:\LTT_LLM\models\Qwen3.8-27B-UD-Q4_K_M.gguf ^
  --jinja -ngl 999 -fa 1 ^
  -c 204800 ^
  --cache-type-k q4_0 --cache-type-v q4_0 ^
  --spec-type draft-mtp --spec-draft-n-max 2 --parallel 1 ^
  --host 127.0.0.1 --port 8281

:: === ltt_llm_vision === doc anh, ngu canh vua
llama-server.exe ^
  -m H:\LTT_LLM\models\Qwen3.8-27B-UD-Q4_K_M.gguf ^
  --mmproj H:\LTT_LLM\models\mmproj-F16.gguf ^
  --jinja -ngl 999 -fa 1 ^
  -c 65536 ^
  --cache-type-k q8_0 --cache-type-v q8_0 ^
  --spec-type draft-mtp --spec-draft-n-max 2 --parallel 1 ^
  --host 127.0.0.1 --port 8282
```

**Kỳ vọng:** `ops` ~**54 tok/s** ở 200K · `vision` ~**63 tok/s** ở 64K, acceptance 0,64–0,87.
Cả hai đi qua `llama-swap`, **chỉ một cái nằm trong VRAM tại một thời điểm**.

⚠️ `-c 204800`, **không phải 262144** — cộng đồng ghi rõ *"262K exceeded 24 GB at model
load"*. 204800 là con số họ **chạy được thật** trên card 24 GB.

### 1.1. Ngân sách VRAM — và vì sao khởi điểm là 64K chứ không phải 131K

Card **24.576 MiB = 24,0 GiB**. Số vào:

| Khoản | | Nguồn |
|---|---|---|
| `UD-Q4_K_M.gguf` | **15,33 GiB** | HF API, đo thật |
| `mmproj-F16.gguf` | **0,86 GiB** | HF API (cộng đồng báo ~888 MB thường trú GPU) |
| KV | **64 KB/token** ở f16 · **~32 KB** ở q8_0 · **~16 KB** ở q4_0 | hệ quả 16/64 lớp full attention |
| Bộ đệm MTP | **+0,8 → 0,9 GB** | chênh lệch "VRAM nền → VRAM +MTP" ở hàng UD-Q4_K_XL |

| Ngữ cảnh | KV | VRAM đo được | Biên còn | Nguồn |
|---|---|---|---|---|
| 32K | f16 | 20,5 → 21,4 GB (+MTP) | 3,2 GB | sweep 3090, UD-Q4_K_XL |
| 131K | q8_0 | ~21 GB | ~3,5 GB | hàng b10450 |
| 185K | q4_0 | **23,0 GB** | 1,6 GB | sweep 3090, turbo3 §baseline |
| **200K** | **turbo3** | **23,3 GB (94,7 %)** | **1,3 GB** | ✅ **MỤC TIÊU — chủ dự án chốt** |
| 262K | — | vượt 24 GB lúc nạp model | — | *"262K exceeded 24 GB at model load"* |

### ⭐ Quyết định 200K — và vì sao lo ngại ban đầu của tôi SAI

Bản trước tôi cấm mốc 200K. **Đọc `docs/long-context.md` và `docs/quality.md` của
cộng đồng thì lý do cấm đó không đứng vững**, và chủ dự án đúng:

| Nỗi lo | Số cộng đồng đo được | Kết luận |
|---|---|---|
| *"200K buộc phải nén KV nên hại chất lượng"* | KVarN k4v2 (K 4-bit / V 2-bit): perplexity **+0,16 %**. `int4_per_token_head`: **+0,3 %**. **Needle-in-a-haystack ĐÚNG ở 4k / 16k / 30k / 100k / 240k, cả hai độ sâu** | ❌ **Sai.** Nén KV gần như **không tốn chất lượng** |
| *"MTP speculative làm lệch đầu ra"* | *"Speculation stays exact — the sampled distribution is unchanged"* · *"drafts are verified exactly"* | ❌ **Sai.** MTP **miễn phí** về chất lượng |
| *"200K quá chậm"* | llama.cpp trên 3090: **131K → 63,5 tok/s**, **200K → 54,2 tok/s** | ⚠️ **Đúng một phần** — mất ~15 %, không phải mất một nửa |

**Cái 200K THẬT SỰ lấy đi, và phải nói thẳng:**

1. **Biên VRAM còn 1,3 GB** thay vì 3,5 GB. Chấp nhận được **chỉ vì** chủ dự án xác
   nhận mọi bot trên máy B đã nhả sạch VRAM sau khi xong job — tức khi VLM nạp thì nó
   **độc chiếm card**. Đây là điều kiện, không phải giả định: P6 phải chứng minh.
2. **TTFT khi thực sự nhồi đầy cửa sổ.** Cộng đồng đo: prefill ~1.000 tok/s ở đầu vào
   100k ⇒ một prompt 200K tốn **~2–3 phút trước token đầu tiên**. Với truy vấn ngắn
   thì không thấy gì; với phiên agent dài thì có. Prefix caching bù lại phần lớn.
3. **Không thể vừa 200K vừa dùng trọng số nặng hơn.** Xem §1.2.

### 1.2. Chất lượng: đòn bẩy nào thật sự có tác dụng — và cái đánh đổi

Cộng đồng đo IFBench trên chính stack 4-bit này: **78,3** so với **79,5** của bản
chưa lượng tử hoá (model card Qwen) ⇒ **4-bit trọng số tốn ~1 điểm**. Đó là đòn bẩy
chất lượng **lớn nhất**, lớn hơn hẳn KV và MTP.

Nhưng trên 24 GB thì **trọng số nặng hơn và ngữ cảnh 200K loại trừ nhau**:

| Ưu tiên | Trọng số | KV | Ngữ cảnh | VRAM | Decode |
|---|---|---|---|---|---|
| Chất lượng token cao nhất | **UD-Q4_K_XL** 16,35 GiB | f16 | 32K | 21,4 GB | 79,6 |
| **Ngữ cảnh cao nhất** ← chốt | **UD-Q4_K_M** 15,33 GiB | turbo3/q4_0 | **200K** | **23,3 GB** | **54,2** |
| Cân bằng | UD-Q4_K_M | q8_0 | 131K | ~21 GB | 63,5 |

`Q4_K_XL + mmproj + 200K` ≈ **24,3 GB → không vừa.** Nên với mục tiêu 200K, trọng số
là **UD-Q4_K_M**, và chất lượng lấy lại bằng ba thứ **miễn phí về VRAM**:

- **Bật thinking ở mặc định của model (`xhigh`)** — con số IFBench 78,3 đo ở đúng chế độ đó
- **Tham số sinh đúng model card**: thinking → `temperature 1.0 · top_p 0.95 · top_k 20 · min_p 0 · presence_penalty 0`
- **MTP bật** — nhanh hơn mà không đổi phân phối lấy mẫu

### 1.3. ⭐ Hai hồ sơ model thay vì một — lời giải cho mâu thuẫn vision ↔ 200K

`mmproj` tốn 0,86 GiB thường trú. Ở mốc 200K, 0,86 GiB đó là **hai phần ba biên an
toàn**. Không phải hy sinh cái nào cả — `llama-swap` sinh ra để làm đúng việc này:
khai **hai mục model**, nó tự đổi theo tên model mà client gọi, **chỉ một cái nằm
trong VRAM tại một thời điểm**.

| Tên model | Dùng cho | mmproj | Ngữ cảnh | KV | VRAM ước |
|---|---|---|---|---|---|
| **`ltt_llm_ops`** | Codex · Claude Code · phiên agent dài | ❌ không | **200K** | turbo3/q4_0 | **~23,3 GB** |
| **`ltt_llm_vision`** | đọc ảnh, ảnh chụp màn hình, biểu đồ | ✅ có | 64K | q8_0 | **~19,9 GB** |

Client chọn bằng trường `model` trong request. Cổng `llm_gateway` định tuyến. **Không
mất gì cả** — chỉ mất thời gian đổi lượt khi chuyển giữa hai loại việc.

---

## 2. Chín ràng buộc thiết kế rút từ 7 luật + 18 bẫy của cộng đồng

Đây là phần **đắt nhất** của việc tải tài nguyên về: người khác đã trả giá rồi.

| # | Điều rút ra | Nguồn | Nó đổi thiết kế của ta thế nào |
|---|---|---|---|
| **1** | 🔴 **"Một desktop dùng chung làm chậm một nửa, trong im lặng."** Compositor + trình duyệt đẩy **3,5 GB trọng số tràn sang RAM chủ qua PCIe**, `/health` vẫn **xanh**, decode giảm một nửa, **không lỗi ở đâu cả** | luật 7 | **Đây là luật quan trọng nhất với máy B.** Nó chứng minh: VLM **không được** chạy song song ComfyUI. Và `/health` **không đủ** để tin — cổng phải **kiểm chứng cư trú VRAM thật** bằng `nvidia-smi`, đúng D-013 |
| **2** | **"Khởi động lên một GPU chưa sạch thì mất 25 % trong im lặng."** | bẫy 2 | 🔴 **ĐÃ ĐO, VÀ NÓ ĐÚNG CẢ VỚI llama.cpp — TÔI TỪNG GHI SAI Ở ĐÂY.** Bản trước của dòng này viết *"llama.cpp báo lỗi to, thất bại là loud chứ không silent"*. Sai. P6 đo: card bẩn (ComfyUI giữ 6.211 MiB) → **18,2 tok/s**; card sạch → **63,3 tok/s**. Chênh **3,5 lần**, `/health` vẫn xanh, không một lỗi nào. Đã sửa. Lời giải khi đó: `llm_gateway/don_dep.py` gọi `/free` của ComfyUI rồi **tự đo lại bằng `nvidia-smi`**; chưa sạch thì trả 429, **không nạp đè** — tệp này đã bị xoá 12/09 (`don_dep.py`/`render_gateway/nhuong_card.py` gộp thành một trọng tài residency, nay là `llm_gateway/trong_tai.py`, xem `DECISION_LOG.md` D01), nguyên tắc đo/không-nạp-đè vẫn còn. Xem [`SO_DO_P2_P6.md`](SO_DO_P2_P6.md) §4 |
| **3** | **"Benchmark không cho bạn biết đầu ra là rác."** Đường int8 phục vụ vô nghĩa suốt một giờ với số throughput rất đẹp | bẫy 1 | **P3 (chất lượng) đứng TRƯỚC P5 (tốc độ).** Không đảo thứ tự |
| **4** | **"Đo hai lần."** Lần chạy đầu sau mỗi lần khởi động lại có JIT warmup, **đọc thấp 30–50 %** | bẫy 8 | Mọi phép đo: 3 lần, **bỏ lần đầu**, lấy trung vị |
| **5** | **Benchmark bằng token ngẫu nhiên là vô nghĩa với speculative decoding** — cùng một máy chủ cho 35, 83 hoặc 151 tok/s tuỳ nhiễu | bẫy 6 | Chỉ dùng **`probe.py`** với prompt thật. Không tự viết harness |
| **6** | **`--parallel 2` làm số nền đọc thấp ~20 %**, thổi phồng mức tăng | luật 5 | Mọi phép A/B đo ở **`--parallel 1`** cả hai vế |
| **7** | **Card 24 GB đạt đỉnh ở `n-max 2`**; sâu hơn thì code tăng nhưng **prose giảm**, tổng thể giảm | luật 1 + sweep 3090 | Khởi điểm `n-max 2`. Sweep 2/3/4 rồi mới chốt |
| **8** | **`--spec-draft-p-min` giúp card nghèo băng thông, hại card nhanh.** Acceptance là **chỉ số phù phiếm** — gating làm nó tăng mà throughput giảm | luật 2 | **Sweep, đừng chép.** Và **đừng tối ưu theo acceptance** |
| **9** | **Build mới hơn quan trọng hơn mọi cờ.** Số nền của b10450 **bằng đúng số có-cờ của ngày đầu**; một build hiện thời tăng 10–15 % trước khi bật cờ nào | luật 6 | **Lấy build mới nhất trước, tune sau.** Và **re-sweep sau mỗi lần nâng build** |

Ba bẫy nữa chỉ liên quan nếu sau này chuyển sang vLLM (ghi lại để khỏi phải tìm lại):
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` bắt buộc · MTP bật thì
`gpu-memory-utilization` phải hạ **0,93** · cache `torch.compile` không biết biến môi
trường của bạn.

---

## 3. Kiến trúc MVP

```
Codex CLI ──────┐                               MÁY B
Claude Code ────┤                    ┌──────────────────────────────────┐
apps/ nền tảng ─┼── LAN ─── bearer ──► [3] llm_gateway      :8299       │  ← TA VIẾT
Nexus ──────────┘                    │     xác thực · ngân sách token   │
                                     │     trọng tài VRAM · credit      │
                                     │     cascade cloud khi B bận      │
                                     └──────────────┬───────────────────┘
                                                    │ loopback
                                     ┌──────────────▼───────────────────┐
                                     │ [2] llama-swap       :8280       │  ← CÓ SẴN
                                     │     vòng đời model · ttl nhả VRAM│
                                     │     cổng chờ GPU sạch (bẫy 2)    │
                                     └──────────────┬───────────────────┘
                                                    │ loopback
                                     ┌──────────────▼───────────────────┐
                                     │ [1] llama-server  127.0.0.1:8281 │  ← CÓ SẴN
                                     │     --jinja --mmproj -ngl 999    │
                                     └──────────────┬───────────────────┘
                                                    │ tranh chấp VRAM
                                     ┌──────────────▼───────────────────┐
                                     │     ComfyUI     127.0.0.1:8188   │
                                     └──────────────────────────────────┘
```

**Chỉ tầng [3] là mã ta viết.** Tầng [1] và [2] là phần mềm thượng nguồn, ta **cấu
hình** chứ không sửa. Đó là cách rẻ nhất để sau này nâng model mà không gãy gì.

---

## 4. Chuỗi phase — mười phase, mỗi phase một cổng chặn

**Quy ước:** phase nào **chưa qua cổng** thì **không sang phase sau**. Cột "Hoàn tác"
là đường lùi nếu hỏng.

### ⭐ Thứ tự thi hành: việc KHÔNG dùng GPU làm trước

Chủ dự án chốt 22/08: **xếp mọi hạng mục cần GPU xuống cuối, làm khi card trống.**
Máy B đang chạy lô đo `edit` của H37 (xem [`DO_NEN_P0.md`](DO_NEN_P0.md)).

| Đợt | Phase | Cần GPU? |
|---|---|---|
| **Đợt 1 — làm ngay** | **P1** tải tài nguyên (mạng + đĩa) | ❌ |
| | **P7** viết `llm_gateway/` trên máy A, test bằng máy chủ giả lập | ❌ |
| | **P9a** chuẩn bị service + tường lửa + provider (chưa bật) | ❌ |
| **Đợt 2 — khi card trống** | **P0-4** đo `/free` của ComfyUI | ✅ cần card **rảnh** |
| | **P2** chạy trần · **P3** chất lượng · **P4** vision | ✅ |
| | **P5** sweep MTP/KV/ngữ cảnh · **P6** trọng tài VRAM | ✅ (việc dài — **xếp ban ngày**, xong trước 01:00) |
| **Đợt 3** | **P8** cắm client · **P9b** nghiệm thu | ✅ |

Đảo thứ tự này **không phá cổng chặn nào**: P7 vốn được thiết kế để test bằng
`llama-server` giả lập trên máy A không cần GPU. Cái duy nhất P7 phải chờ P5 là **con
số cụ thể** cho `ngan_sach.py` — nên P7 viết trần **đọc từ biến môi trường**, điền số
sau khi P5 đo xong.

---

### **P0 — Đo nền, không đụng gì đang chạy** · máy B · ~2 giờ

| | |
|---|---|
| **Việc** | 1. `nvidia-smi` nền: VRAM đang dùng, ai đang giữ<br>2. RAM trống<br>3. Tốc độ đọc tuần tự **`H:`** (NVMe) — xác nhận D-014<br>4. **ComfyUI có nhả sạch VRAM sau `/free` không** — gọi `/free`, chờ, đo lại bằng `nvidia-smi`<br>5. Xác nhận lịch chạy của dự án video (khung giờ nào bận) |
| **Cổng qua** | Có bảng số ghi vào `DECISIONS.md`. **Biết chính xác VRAM trống khi ComfyUI đã nhả.** Nếu ComfyUI **không** nhả sạch → toàn bộ phương án đổi lượt vô nghĩa, **dừng lại và thiết kế lại** |
| **Vì sao là cổng** | Ràng buộc 1 và 2. Không biết số này thì mọi thứ sau là bốc thăm |
| **Hoàn tác** | — (chỉ đọc) |

---

### **P1 — Tải tài nguyên về máy B** · ~1 giờ + thời gian tải

| | |
|---|---|
| **Việc** | Tạo `H:\LTT_LLM\{bin,models,work,logs}` (H: là **NVMe**, còn 818 GB)<br>Tải 5 thứ ở §0.2 |
| **Cổng qua** | Kích thước khớp: `UD-Q4_K_M.gguf` **15,33 GiB**, `mmproj-F16.gguf` **0,86 GiB**. `llama-server.exe --version` in ra **b10580** |
| **Bẫy tránh được** | Đặt model ở `E:` (SSD SATA 476 MB/s) thay vì `H:` → nạp lâu gấp ~6 lần |
| **Hoàn tác** | Xoá `H:\LTT_LLM\` |

---

### **P2 — Chạy trần: chưa cờ nào, chưa vision, chưa spec** · ~1 giờ

| | |
|---|---|
| **Việc** | `llama-server.exe -m ...UD-Q4_K_M.gguf --jinja -ngl 999 -c 8192 --host 127.0.0.1 --port 8281`<br>Hỏi 3 câu tiếng Việt + 1 đoạn code |
| **Cổng qua** | 🔴 **Đầu ra là chữ CÓ NGHĨA.** Build cũ nạp bình thường, VRAM đúng, **ra rác** — đây là bẫy đã hạ gục người đầu tiên thử model này<br>Ghi lại: VRAM đỉnh, tok/s (chạy 2 lần, **bỏ lần đầu** — ràng buộc 4) |
| **Vì sao chạy trần trước** | Nếu bật hết cờ ngay rồi ra rác thì không biết tại cờ nào. Ràng buộc 9 |
| **Hoàn tác** | Tắt tiến trình |

---

### **P3 — Chất lượng TRƯỚC tốc độ** · ~2 giờ

| | |
|---|---|
| **Việc** | Chạy `qwen38-27b-rtx3090/bench/quality_battery.py` (perplexity + GSM8K) với máy chủ đang sống.<br>Thêm bộ 10 prompt **vận hành thật của ta**: đọc log lỗi, tóm tắt diff, giải thích trace Python, đọc `ho_so_he_thong.txt` |
| **Cổng qua** | Perplexity trong vùng hợp lý cho Q4; GSM8K không sụp; 10 prompt vận hành trả lời đúng việc |
| **Vì sao ở đây** | ⚠️ Bẫy 1 — *"một benchmark không thể cho bạn biết đầu ra là rác"*. Có số chất lượng **trước** khi bắt đầu tối ưu tốc độ, thì mỗi lần tăng tốc sau này đều so được |
| **Hoàn tác** | — |

---

### **P4 — Bật vision** · ~2 giờ

| | |
|---|---|
| **Việc** | Thêm `--mmproj H:\LTT_LLM\models\mmproj-F16.gguf`.<br>Thử: ảnh chụp màn hình một lỗi · một biểu đồ · một trang giao diện |
| **Cổng qua** | Ảnh vào → mô tả đúng ra. **Đo VRAM tăng bao nhiêu** (cộng đồng: ~888 MB thường trú trên GPU) |
| **Bẫy** | Quên `--mmproj` thì model **lịch sự từ chối** phân tích ảnh dù nó có vision — trông như model kém, thật ra là thiếu cờ |
| **Hoàn tác** | Bỏ cờ `--mmproj` |

---

### **P5 — Tối ưu có kỷ luật: MTP · KV · ngữ cảnh** · ~1 ngày

| | |
|---|---|
| **Việc** | Dùng **`probe.py`** (không tự viết harness — ràng buộc 5).<br>**A/B 1 — MTP:** spec-off vs `--spec-type draft-mtp --spec-draft-n-max {2,3,4}`. Cả hai vế `--parallel 1` (ràng buộc 6). 3 lần mỗi arm, bỏ lần đầu, lấy trung vị (ràng buộc 4)<br>**A/B 2 — KV:** `f16` → `q8_0` → `q4_0`. Đo **cả VRAM lẫn chất lượng** (chạy lại P3 rút gọn ở mỗi mức)<br>**A/B 3 — ngữ cảnh:** 64K → 131K theo **bậc**, dừng khi biên VRAM chạm 2 GB |
| **Cổng qua** | Chốt **một** cấu hình duy nhất. **Biên VRAM ≥ 2 GB.** Có bảng số đầy đủ ghi vào `DECISIONS.md`. Chất lượng ở KV đã chọn **không tệ hơn** P3 |
| **Kỳ vọng** | ~41 → **~63 tok/s** (theo hàng b10450, cùng card cùng quant) |
| **Cấm** | Tối ưu theo **acceptance** — nó là chỉ số phù phiếm (ràng buộc 8) |
| **Hoàn tác** | Quay về cấu hình P4 |

---

### **P6 — Trọng tài VRAM với ComfyUI** · ~1 ngày

| | |
|---|---|
| **Việc** | Dựng `llama-swap` (`llama-swap_250_windows_amd64`):<br>· `ttl: 600` — không ai dùng 10 phút thì tự nhả VRAM<br>· `healthCheckTimeout: 500`<br>· **cổng chờ GPU sạch trước khi nạp** (ràng buộc 2) — kiểm bằng `nvidia-smi`, không bằng `/health`<br>· `POST /api/models/unload` để cổng ép nhả khi job ảnh tới<br>**Đo:** 10 lượt đổi qua lại VLM ↔ ComfyUI |
| **Cổng qua** | 1. Nhả **sạch** — `nvidia-smi` xác nhận, không tin `/health` (ràng buộc 1)<br>2. ComfyUI render xong không OOM<br>3. Nạp lại **< 30 giây** (GGUF nằm sẵn trong page cache của 192 GB RAM)<br>4. Sau khi nạp lại, **tok/s bằng lúc đầu** — nếu thấp hơn ~25 % thì đã dính bẫy 2 |
| **Vì sao đây là phase khó nhất** | Ràng buộc 1 nói thẳng: chỉ số có thể **xanh mà sai**. Phase này phải chứng minh bằng `nvidia-smi` và bằng tok/s sau khi nạp lại, không bằng lời của phần mềm |
| **Hoàn tác** | Bỏ llama-swap, chạy `llama-server` tay |

---

### **P7 — `llm_gateway/`** · **mã ở máy A** · ~2 ngày

| | |
|---|---|
| **Việc** | Viết theo đúng bộ khung `render_gateway/`:<br>· `config.py` — mọi tham số từ biến môi trường, **không `Path(__file__).parents[n]`**<br>· `ngan_sach.py` — **chặn trước khi chạm GPU**: trần token vào/ra, trần số ảnh, trần ngữ cảnh, theo số đã đo ở P5<br>· `busy.py` — trọng tài, **đếm tiến trình chứ không đo ngưỡng VRAM** (D-022), ETA, cascade<br>· `api.py` — `/health` (có VRAM + model đang nạp) · `/v1/models` · proxy `/v1/responses` · `/v1/chat/completions` · `/v1/messages`<br>· `catalog.py` — **fail-closed như Q92**: bật cờ không tự mở model nào |
| **Cổng qua** | Test chạy được **trên máy A không cần GPU** (llama-server giả lập), và **xanh trong `tools\gate.py`** |
| **Hoàn tác** | Nhánh git riêng |

---

### **P8 — Cắm client thật** · ~4 giờ

| | |
|---|---|
| **Việc** | **Codex:** `~/.codex/config.toml`, `wire_api = "responses"`, `base_url = "http://192.168.2.66:8299/v1"`<br>**Claude Code:** `ANTHROPIC_BASE_URL=http://192.168.2.66:8299`<br>Mỗi client chạy trọn **một việc vận hành thật** |
| **Cổng qua** | Mỗi client: hoàn thành một việc thật **có gọi tool**, không chỉ trả lời một câu |
| **Ghi chú** | **Claude Desktop (app GUI) không nằm trong phase này** — nó không đổi được model. Đường của nó là **MCP server**, một hạng mục riêng sau MVP |
| **Hoàn tác** | Bỏ cấu hình client |

---

### **P9 — Thành sản phẩm: service · tường lửa · giám sát · nghiệm thu** · ~1 ngày

| | |
|---|---|
| **Việc** | · `nssm` dựng **service Windows** cho `llama-swap` và `llm_gateway` (nssm đã có sẵn trong `tools/`)<br>· Tường lửa: mở **8299 chỉ cho `192.168.2.17`**. `llama-server` và ComfyUI **giữ nguyên chỉ `127.0.0.1`**<br>· Provider `ltt_local_llm` trong `platform_core/providers.py` + `platform_core/llm/`<br>· Cascade sang cloud khi B bận — **và tuyệt đối không gọi `danh_dau_loi()` khi chỉ là bận**<br>· `/health` báo: VRAM, model đang nạp, độ dài hàng đợi, phiên bản |
| **Cổng qua** | 1. **Sống qua một lần reboot máy B**<br>2. Cascade **đúng** khi B bận (thử bằng cách phóng một job ảnh)<br>3. `tools\gate.py` xanh<br>4. Tường lửa: từ máy khác trong LAN **không** vào được 8281/8188 |
| **Hoàn tác** | Gỡ service, giữ chạy tay |

---

## 5. Định nghĩa "XONG" của MVP

MVP gọi là xong khi **cả bảy câu đều đúng**, kiểm được, không phải cảm nhận:

| # | Câu | Kiểm bằng |
|---|---|---|
| 1 | Codex chạy trọn một việc thật bằng model nhà, có gọi tool | chạy thử, xem transcript |
| 2 | Claude Code chạy trọn một việc thật bằng model nhà | như trên |
| 3 | Gửi ảnh vào và nhận mô tả đúng | 3 ảnh khác loại |
| 4 | Job ảnh của H37 tới → VLM nhả VRAM → ảnh render xong → VLM nạp lại, **tốc độ không tụt** | 10 lượt liên tiếp |
| 5 | Máy B bận (video) → yêu cầu **cascade sang cloud**, khách không chờ, và `ltt_local_llm` **không** bị đánh dấu lỗi | phóng job lúc video chạy |
| 6 | Reboot máy B → mọi thứ tự lên | reboot thật |
| 7 | Từ một máy khác trong LAN: **vào được 8299**, **không vào được 8281/8188** | quét cổng |

**Tổng thời lượng ước tính: 7–8 ngày công**, trong đó P7 (viết cổng) chiếm nhiều nhất.

---

## 6. Rủi ro đã biết và đường lùi

| Rủi ro | Dấu hiệu | Đường lùi |
|---|---|---|
| **ComfyUI không nhả sạch VRAM sau `/free`** | P0 đo thấy VRAM không về | 🔴 **Dừng ở P0.** Phải thiết kế lại: hoặc khởi động lại tiến trình ComfyUI, hoặc chấp nhận VLM chỉ chạy khi ComfyUI tắt |
| **Máy B tự reboot vì Windows Update** | Mất lượt đang chạy | Việc dài **kết thúc trước 01:00** (Active Hours 07:00→01:00). Service tự lên lại ở P9 |
| **Model ra rác** | P2 không qua cổng | Lấy build mới hơn; kiểm không có lib CUDA cũ nào còn trong đường dẫn |
| **Tốc độ tụt sau mỗi lần đổi lượt** | P6 cổng 4 đỏ | Ràng buộc 2 — thêm cổng chờ GPU sạch, tăng `unloadTimeout` |
| **Chất lượng Q4 không đủ cho việc vận hành** | P3 đỏ | Lên `UD-Q4_K_XL` (16,35 GiB, +1 GiB) — vẫn vừa, chỉ mất ~1 GB biên |
| **Video chiếm GPU cả buổi tối** | VLM không dùng được nhiều giờ | Đã có cascade cloud (P9). Đây là **giới hạn đã biết và chấp nhận** khi chốt máy B |
| **Cần throughput cao hơn 63 tok/s** | nhiều người dùng đồng thời | Đường nâng cấp: vLLM + WSL2 (~114 tok/s, có sleep mode). **Không làm trong MVP** |

---

## 6. 🟢 SỐNG — 22/08/2026, 20:50

Hai dịch vụ đã cài trên máy B, `StartType = Automatic`, và **máy A gọi được qua LAN**.

```
LTTLlamaSwap    Running  Automatic
LTTLlmGateway   Running  Automatic
```

**Kiểm từ máy A, không phải từ máy B:**

| Kiểm | Kết quả |
|---|---|
| `GET http://192.168.2.66:8299/health` kèm bearer | ✅ `models_mo = ltt_llm, ltt_llm_vision` |
| Không có token | ✅ **401** |
| Sinh thật qua LAN | ✅ **64,2 tok/s** · trả lời tiếng Việt đúng |
| **Tool calling** | ✅ `get_price {"symbol":"BTC","currency":"USD"}` · `finish=tool_calls` |
| Model chưa liệt kê (`ltt_llm_ops`) | ✅ **404** — fail-closed làm đúng việc |
| 🔒 Cổng nội bộ **8280 / 8281 / 8282 / 8188** từ LAN | ✅ **tất cả đóng** |

Tên khách gọi: **`ltt_llm`** (mặc định, 64K) · **`ltt_llm_vision`** (đọc ảnh).
`ltt_llm_ops` (200K) khai trong `llama-swap.yaml` nhưng **không liệt kê** trong
`LTT_LLM_MODELS` — chỉ dùng khi cần, trong LAN.

### Hai lỗi trong `cai_dat_dich_vu.ps1`, tìm ra trước khi chủ dự án chạy

| Lỗi | Nếu không sửa |
|---|---|
| Tìm `llama-swap.yaml` ở `gateway\deploy\`, `deploy.ps1` đặt ở `gateway\` | `exit 1` ngay dòng đầu — **hỏng to, dễ thấy** |
| 🔴 **`gateway.env` không bao giờ được nạp vào dịch vụ** (`AppEnvironmentExtra` chỉ đặt `PYTHONPATH`) | **Hỏng im lặng**: dịch vụ lên, `/health` 200, nhưng `LTT_LLM_TOKEN` rỗng ⇒ **cổng mở toang trên LAN**; `LTT_LLM_MODELS` rỗng ⇒ `/v1/models` rỗng, trông như hỏng; `LTT_LLM_HOST` = 127.0.0.1 ⇒ máy A không gọi được. Ba triệu chứng, một nguyên nhân, không cái nào báo lỗi |

---

## 6a. ✅ NGHIỆM THU TỪ ĐẦU ĐẾN CUỐI — 22/08/2026, 20:15

```
powershell -ExecutionPolicy Bypass -File llm_gateway\deploy\kiem_tra.ps1
```

Chạy từ máy A, dựng cả ba tầng trên máy B, chạy 19 mục kiểm, rồi dọn sạch.

**KẾT QUẢ: ĐẠT 19 · HỎNG 0.**

| # | Mục | Kết quả |
|---|---|---|
| 1 | `/health`, thượng nguồn sống, không tên model lạ | ✅ `python_gpu=1` (ComfyUI thường trú) ⇒ **không** báo bận — đúng ngưỡng ≥2 |
| 2 | Token sai → 401 | ✅ |
| 3 | Model lạ → 404 (fail-closed) | ✅ |
| 4 | Đầu vào quá dài → 413 **sau 0,0 giây** | ✅ chặn trước khi chạm GPU |
| 5 | Sinh thật | ✅ **63,5 tok/s** · `usage` đủ · `cache_n` có · VRAM 1.494 → 20.212 MiB |
| 6 | **Tool calling** | ✅ `get_weather {"city":"Hanoi"}` |
| 7 | Prefix cache | ✅ `cache_n=413/417` ⇒ giảm giá token cache thi hành được |
| 8 | 🔴 **Dọn card — chính cái đã hỏng ở P6** | ✅ ComfyUI giữ **23.725 MiB** → cổng vẫn 200 → **63,1 tok/s**, không phải 18 |

Mục 8 là mục quan trọng nhất: nó chứng minh `don_dep.py` thật sự chạy. Nếu tốc độ
đọc ra ~18 tok/s thì trọng số đã tràn sang RAM chủ và không ai được báo gì cả.

**Đã dựng trên máy B:**

```
[3] llm_gateway :8299   venv rieng · bearer token sinh ngau nhien · fail-closed
[2] llama-swap  :8280   ba ho so, ttl tu nha VRAM
[1] llama-server :828x  CHI 127.0.0.1
```

---

## 6b. TIẾN ĐỘ — cập nhật 22/08/2026

| Phase | Trạng thái | Bằng chứng |
|---|---|---|
| **P0** | 🟡 **5/6 mục xong** | [`DO_NEN_P0.md`](DO_NEN_P0.md). Còn mục 4 (`/free` của ComfyUI) — **cần card rảnh** |
| **P1** | ✅ **QUA CỔNG** | `Qwen3.8-27B-UD-Q4_K_M.gguf` **16.464.440.224 B** · `mmproj-F16.gguf` **927.607.488 B** — khớp HF API. `llama-server.exe --version` → **`build 10580, commit 54ee5ee64`**, vượt xa mốc `ece963f41`. `llama-swap.exe` + `mtmd.dll` có |
| **P2–P5** | ⏸️ chờ card rảnh | |
| **P6** | 🟡 **cấu hình xong, chưa chạy** | `llm_gateway/deploy/llama-swap.yaml` — hai hồ sơ, đã **đối chiếu `config-schema.json` thật**: không khoá lạ, YAML parse được, thuần ASCII |
| **P7** | 🟢 **cốt lõi xong** | `llm_gateway/` — `config · catalog · ngan_sach · trong_tai · upstream · api · main`. **`tests/test_250_llm_gateway.py`: 26/26 xanh.** `tools\gate.py --quick`: 11/12 (lỗi còn lại là `providers.py` + `nexus_gioi_thieu.html` của **phiên khác**, không phải của hạng mục này) |
| **P8** | ⏸️ chờ P6 | |
| **P9a** | ✅ script sẵn | `llm_gateway/deploy/cai_dat_dich_vu.ps1` — service + tường lửa chỉ `192.168.2.17` + **kiểm 8280/8281/8282 không lọt ra LAN** |

### ✅ Thêm 22/08 (chiều): mảnh adapter — nợ kiến trúc lớn nhất đã đóng

`platform_core/llm/cong_vlm.py` + `tests/test_251_cong_vlm.py` (**20 test**).
Tổng `test_250` + `test_251` = **46/46 xanh**.

Bốn luật được **neo bằng test**, không chỉ ghi trong chú thích:

| Luật | Test neo | Mất nó thì mất gì |
|---|---|---|
| **429 ⇒ `BanError`, KHÔNG phải `CongVlmError`** | `test_429_nem_BanError_chu_khong_phai_CongVlmError` | `api_pool` disable key sau 5 lần ⇒ **model nhà tự tắt vĩnh viễn** |
| **413 ⇒ `VuotNganSachError` riêng** | `test_413_...khong_phai_loi_provider` | Một yêu cầu quá to bị tính thành lỗi máy B |
| **Thiếu `usage` ⇒ `dang_tin=False`** | `test_thieu_usage_thi_dang_tin_False` | Tính tiền bằng số đoán |
| **Token cache đếm riêng** | `test_cache_n_cua_llama_cpp_duoc_dem_rieng` | **Tính tiền khách hai lần cho cùng một ngữ cảnh** |
| **Không có đường tự đổi model** | `test_khong_co_duong_tu_doi_model` (soi chữ ký hàm) | D-010 — đánh tráo sản phẩm |

### ✅ Thêm 22/08 (tối): đường tiền đã đóng

| Tệp | Việc | Test |
|---|---|---|
| `platform_core/llm/gia_token.py` | Bảng giá **50 / 10 / 400 credit mỗi 1M**, nhãn `ltt-vlm-2026-08-22`. Tính bằng **milli-credit, toàn số nguyên** | `test_252` **18/18** |
| `platform_core/llm/thanh_toan.py` | **C1**: giữ chỗ theo trần ước cao → làm tròn LÊN khi quyết toán → hoàn phần dư | `test_253` **14/14** |

**Tổng bốn bộ của hạng mục: 78 test xanh** (`test_250` 26 · `test_251` 20 ·
`test_252` 18 · `test_253` 14).

Ba bất biến được neo bằng test, không chỉ ghi trong chú thích:

- **Giữ chỗ không bao giờ thiếu** — quét mọi kết cục thật (`ra` từ 0 tới `max_tokens`,
  cache từ 0 tới toàn bộ) và khẳng định `thu ≤ giữ`.
- **Không đủ credit ⇒ không đốt GPU** — `ThieuCreditError` ném **trước** khi gọi model.
- **Không đo được `usage` ⇒ hoàn đủ, KHÔNG thu** — thu tiền mà không có bằng chứng
  còn tệ hơn mất một ít tiền. Có ghi cảnh báo để nếu nó xảy ra thường xuyên thì
  người vận hành thấy.

### ✅ Thêm 22/08 (tối muộn): bộ điều phối + deploy + nghiệm thu

| Tệp | Việc | Test |
|---|---|---|
| `platform_core/llm/dieu_phoi.py` | **Một đường gọi model cho toàn nền tảng.** Chọn key qua `api_pool`, dịch giao thức (OpenAI ↔ Gemini) ở **một** chỗ, cascade theo thứ tự **bên gọi khai** | `test_255` **9/9** |
| `llm_gateway/deploy/deploy.ps1` | Chép mã A→B, dựng venv, sinh `gateway.env` **không BOM** | chạy thật ✅ |
| `llm_gateway/deploy/nghiem_thu.py` | 19 mục kiểm từ đầu đến cuối | chạy thật ✅ |
| `llm_gateway/deploy/kiem_tra.ps1` | Chạy nghiệm thu từ máy A | chạy thật ✅ |

**Tổng sáu bộ: 98 test xanh.**

Ba luật của `dieu_phoi` được neo bằng test:

- **Bận ⇒ đi tiếp provider sau, KHÔNG `danh_dau_loi`** — lẫn hai thứ này thì key
  model nhà tự tắt sau 5 lần (D-005).
- **Lỗi thật ⇒ CÓ `danh_dau_loi`** rồi mới đi tiếp.
- **Vượt ngân sách ⇒ ném ngay, KHÔNG cascade** — quá to ở đây thì quá to ở mọi nơi.

⭐ **Cascade ở `dieu_phoi` hợp lệ, và nó KHÁC cái D-010 cấm.** D-010 cấm đổi model
sau lưng **khách trả tiền**; `llm_gateway` và `cong_vlm.chat()` **không có** đường
fallback, có test soi chữ ký hàm để giữ nguyên. `dieu_phoi` phục vụ **việc nội bộ**
(planner, tóm tắt, phụ đề) — ở đó không có lời hứa nào với khách về model nào, và
thứ tự do bên gọi **khai ra**. Khai ra thì không phải là lén.

### Bốn lỗi tự gây, đã sửa trong lúc thi hành

| Lỗi | Quy tắc bị vi phạm | Triệu chứng |
|---|---|---|
| `—` trong một `.ps1` | **Quy tắc 2** — `.ps1` phải thuần ASCII | PowerShell 5.1 đọc theo ANSI, vỡ cả script, **báo lỗi ở dòng khác** |
| `python -c "..."` qua ssh | **Quy tắc 3** — đừng viết Python inline qua PowerShell | Dấu ngoặc kép bị nuốt |
| Hàm PowerShell tên `SSH` | — | PowerShell không phân biệt hoa thường ⇒ `& ssh` gọi lại chính hàm ⇒ **call depth overflow** |
| `print` tiếng Việt ra console CP1252 | — | `UnicodeEncodeError` **giữa bài nghiệm thu** — một bài kiểm tự làm hỏng chính nó |

### Việc còn lại của P7 (không cần GPU)

- Chuyển `platform_core/agent/planner.py` sang `dieu_phoi` (chỗ dễ nhất — nó đã có
  tham số `llm_call` tiêm được sẵn)
- Provider `ltt_local_llm` trong `platform_core/providers.py` — ⏸️ **hoãn có chủ ý**:
  tệp đó đang bị **phiên khác sửa dở** (Nexus SSO, +51 dòng). Đụng vào lúc này là
  mời xung đột. Làm sau khi phiên kia đóng.
- Đường **streaming** (SSE) cho adapter — tách riêng có chủ ý, vì bóc `usage` từ
  SSE là việc khác và trộn hai đường vào một hàm là cách chắc nhất để tính tiền
  sai một trong hai.

---

## 7. Việc đã làm trong phiên này

- ✅ **Xoá ba model Qwen cũ trên máy B** theo quyết định của chủ dự án:
  `Qwen2.5-VL-7B-Instruct` · `Qwen3-VL-8B-Instruct` · `Qwen3-VL-8B-Thinking`
  (**48,14 GiB**). `E:` từ 364,4 → **416,1 GB** trống. Xoá sạch, không sót file.
  ⚠️ Lúc xoá, GPU máy B đang **100 % util / 17,5 GB** — nếu dự án video đang nạp một
  trong ba model đó thì lượt đó đã hỏng. Chủ dự án đã biết trước và chấp nhận.
- ✅ Clone ba repo tham chiếu về `D:\LTT_VLM_REFS\`.
- ✅ Xác định URL và kích thước thật của toàn bộ nhị phân + trọng số.

---

## 8. Nguồn

- `qwen38-mtp` — 7 luật, sweep 3090, `probe.py`: https://github.com/sudoingX/qwen38-mtp
- `qwen38-27b-rtx3090` — 18 bẫy, `quality_battery.py`: https://github.com/syv-ai/qwen38-27b-rtx3090
- `llama-swap` — ttl, unload API: https://github.com/mostlygeek/llama-swap
- llama.cpp releases (binary Windows CUDA hằng ngày): https://github.com/ggml-org/llama.cpp/releases
- `llama-server` endpoints: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- Anthropic Messages API trong llama.cpp: https://huggingface.co/blog/ggml-org/anthropic-messages-api-in-llamacpp
- Trọng số + mmproj: https://huggingface.co/unsloth/Qwen3.8-27B-GGUF
- llama.cpp PR #22673 (draft-mtp): https://github.com/ggml-org/llama.cpp/pull/22673
- Kích thước GGUF · bẫy template: https://dev.to/purpledoubled/run-qwen-38-27b-locally-real-gguf-sizes-the-kv-cache-trick-and-the-template-trap-114j
- Cấu hình Codex: https://developers.openai.com/codex/config-reference
