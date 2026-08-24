# Số đo thật trên máy B — P2 đến P6

**2026-08-22, 19:00–20:30.** Tất cả đo bằng `nvidia-smi` và `timings` của chính
`llama-server`. Card RTX 3090 24.576 MiB, `Qwen3.8-27B-UD-Q4_K_M.gguf` (15,33 GiB),
llama.cpp **b10580** (`54ee5ee64`).

---

## 1. P2 — chạy trần, không cờ nào. ✅ QUA CỔNG

Cấu hình: `--jinja -ngl 999 -fa 1 -c 8192`, không mmproj, không spec, không template vá.

| | |
|---|---|
| Thời gian nạp | **18 giây** (15,33 GiB từ `H:` NVMe) |
| VRAM | **17.778 MiB** · sau 3 lượt: 17.790 MiB (ổn định) |
| Decode | **39,6 – 40,2 tok/s** |
| Điện · nhiệt | 303 W · 44 °C |

**Cổng quan trọng nhất — đầu ra CÓ NGHĨA, không phải rác:**

| Test | Kết quả |
|---|---|
| Tiếng Việt | "Hà Nội." ✅ |
| Toán | 17 × 23 = **391** ✅ |
| Code | `def add(a: int, b: int) -> int: return a + b` ✅ |

Log nạp cho thấy `blk.64.nextn.*` bị bỏ qua vì "unused" — **đó chính là đầu MTP**,
chưa dùng vì chưa bật `--spec-type draft-mtp`. Đúng như dự kiến.

---

## 2. P3 + P4 — chất lượng, tool calling, vision. ✅ QUA CỔNG

Cấu hình đích: template đã vá + `--reasoning-format deepseek` + MTP `n-max 2` +
mmproj + `-c 65536` + KV `q8_0`.

| Hạng mục | Kết quả |
|---|---|
| Tiếng Việt | Giải thích 429 vs 503 đầy đủ, **có bảng so sánh**, đúng cả về ai chịu trách nhiệm |
| Đọc traceback production | **Đúng nguyên nhân gốc** trong một câu: *"At least one item in `cart` is a dictionary that lacks the `'price'` key"* |
| 🔴 **Tool calling** | ✅ `get_weather` với `{"city":"Hanoi"}`, `finish_reason: tool_calls` |
| **Vision** | ✅ "Red circle, blue square, and text 'LTT 4'" |
| VRAM | **21.451 MiB** / 24.576 (87,3 %) — còn 2.875 MiB |
| Decode | **58,5 tok/s** |

**Tool calling chạy được là kết quả quan trọng nhất của cả phiên** — nó là thứ mọi
agent và bot của khách dựa vào, và template chính thức của Qwen3.8 **làm hỏng đúng
chỗ này**. Bản vá `froggeric` giải quyết được.

*(Model đọc "LTT 4" chứ không phải "LTT 42" — **lỗi ở ảnh test của tôi**: chữ vẽ ở
x=340 trên ảnh rộng 480 nên số "2" bị cắt. Model đọc đúng thứ có trong ảnh.)*

---

## 3. P5 — prefill, prefix cache, MTP. ✅ QUA CỔNG

Hồ sơ `ltt_llm`: `-c 65536`, KV `q8_0`, **không** mmproj.
VRAM **20.315 MiB**, còn trống **4.011 MiB** (82,7 %).

### 3.1. Prefill ở kích thước thật — và nó CHỐT trần Cloudflare

| Mục tiêu | Token thật | Prefill tok/s | TTFT | Wall | Cloudflare |
|---:|---:|---:|---:|---:|---|
| 1.000 | 638 | 796 | 0,8 s | 1,6 s | ✅ |
| 4.000 | 2.529 | 1.140 | 2,2 s | 2,9 s | ✅ |
| 16.000 | 10.031 | **1.188** | 8,4 s | 7,6 s | ✅ |
| 50.000 | 31.328 | 1.050 | **29,8 s** | 21,7 s | ✅ |

⭐ **Prefill 1.050–1.190 tok/s — khớp gần như chính xác ước tính 1.000 tok/s của
cộng đồng.** Và nó xác nhận quyết định 64K là đúng:

```
cua so day 65.536 token / 1.050 tok/s = 62 giay
Cloudflare cat o 100 giay  =>  con bien 38 giay
```

**Cửa sổ 64K tự nó đã nằm trong trần Cloudflare.** Không phải trùng hợp may mắn —
đó là lý do 200K không dùng được cho khách ngoài: một prompt lấp đầy 200K cần
**~195 giây** prefill, chắc chắn 524.

### 3.2. Prefix cache — tính tiền token cache chạy được

| | prompt | `cache_n` | prefill |
|---|---:|---:|---:|
| lần 1 | 1.882 | **0** | 1.078,8 tok/s |
| lần 2 (gọi lại y hệt) | 1.882 | **1.878** | — |

✅ **99,8 % prompt lấy lại từ cache.** Trường `timings.cache_n` có thật và đúng ⇒
mức giá **10 credit/1M cho token cache** thi hành được.

### 3.3. MTP — 3 lượt prompt code

| Lượt | Decode | Sinh | Draft chấp nhận |
|---|---:|---:|---|
| 1 | 70,5 tok/s | 600 | 381/436 = **0,87** |
| 2 | 65,9 tok/s | 600 | 368/461 = 0,80 |
| 3 | 68,1 tok/s | 600 | 376/445 = 0,84 |
| **Trung vị** | **68,1 tok/s** | | |

So với P2 (không MTP): **40,0 → 68,1 tok/s = +70 %**.

⭐ **Nhanh hơn hàng 3090 tốt nhất của cộng đồng** (b10450: 41,3 → 63,5 = +54 %).
Nhiều khả năng vì build b10580 mới hơn 130 build, cộng với 64K thay vì 131K.

---

## 4. 🔴 P6 — TRỌNG TÀI VRAM. THẤT BẠI Ở LẦN ĐẦU, VÀ ĐÓ LÀ KẾT QUẢ GIÁ TRỊ NHẤT

### 4.1. Điều đã xảy ra

| Bước | Kết quả |
|---|---|
| llama-swap lên, `/v1/models` trả **ba hồ sơ** | ✅ |
| Lượt 1 trên card sạch | **65,3 tok/s**, VRAM 20.333 MiB ✅ |
| `POST /api/models/unload` | VRAM về **1.612 MiB** ✅ |
| ComfyUI render một ảnh | xong sau **15,2 giây** ✅ |
| *nhưng ComfyUI giữ lại* | **16.620 MiB** ⚠️ |
| **Lượt 2 — nạp lại** | **17,3 tok/s** 🔴 |
| Lượt 3 — đổi sang `vision` | 19,7 tok/s · VRAM **24.102/24.576 = 98,1 %** ⚠️ |

### 4.2. A/B xác nhận chẩn đoán

Cùng cấu hình, cùng model, cùng prompt. **Chỉ khác trạng thái card trước khi nạp:**

| Arm | VRAM trước khi nạp | Decode | VRAM lúc chạy |
|---|---:|---:|---|
| **A — card bẩn** | 6.211 MiB | **18,2 tok/s** | 24.102 / còn **224 MiB** |
| **B — card sạch** (sau `/free`) | 1.515 MiB | **63,3 tok/s** | 20.236 / còn 4.090 MiB |

**Chênh 3,5 lần.**

### 4.3. Hai sự thật rút ra

**(a) llama.cpp KHÔNG báo lỗi khi card chưa sạch — nó tràn trong im lặng.**

⚠️ **Đây là đính chính một điều tôi đã ghi sai vào repo.** Tôi viết trong
`llama-swap.yaml` và trong lộ trình rằng *"llama.cpp báo lỗi to lúc nạp, khác vLLM
— thất bại là LOUD chứ không SILENT"*. Số đo bác bỏ: `/health` xanh, `/v1/models`
đúng, nội dung sinh ra hợp lệ, chỉ tốc độ lặng lẽ còn một phần tư. Đã sửa cả hai chỗ.

Đúng **luật 7** của cộng đồng: *"A shared desktop halves everything, silently —
spilled 3.5 GB of weights to host RAM over PCIe while /health stayed green."*

**(b) ComfyUI giữ model thường trú KỂ CẢ SAU KHI RENDER XONG.**
Sau một lượt vẽ nó vẫn ôm 6.211 MiB. Chỉ `POST /free` với `unload_models` mới đưa
về 1.515 MiB. ⇒ **"Đợi ComfyUI rảnh" là không đủ** — phải bảo nó nhả rồi tự đo lại.

### 4.4. Đã sửa

`llm_gateway/don_dep.py` — trước khi để một yêu cầu đi tiếp:

1. đọc VRAM bằng **`nvidia-smi`** (D-013 — không tin `/health`, chính phase này
   chứng minh vì sao);
2. nếu > **2.500 MiB** → gọi `/free` của ComfyUI;
3. **đo lại**, thử tối đa 6 lần;
4. vẫn bẩn → cổng trả **429**, **không nạp đè**. Nạp đè là tự chọn phục vụ ở 1/4
   tốc độ.

Ngưỡng 2.500 MiB nằm gọn giữa hai vùng **đã đo**: desktop 1.515–1.612 MiB ·
ComfyUI thường trú 6.211–16.620 MiB.

**Và một lỗi thứ hai được phát hiện nhờ đó:** `trong_tai.py` bản đầu coi
`>0 tiến trình python` là bận. Trên máy B ComfyUI **luôn** chạy ⇒ cổng sẽ trả 429
**vĩnh viễn**. Ngưỡng đúng là **≥ 2**, đúng ngữ nghĩa `render_gateway` đã chốt:
*1 python = chỉ ComfyUI = bình thường*.

---

## 5. Bảng số chốt lại, để `ngan_sach` và bảng giá dùng

| Số | Giá trị đo được | Dùng ở đâu |
|---|---|---|
| VRAM `ltt_llm` (64K, q8_0, không mmproj) | **20.315 MiB** (còn 4.011) | ngân sách VRAM |
| VRAM `ltt_llm_vision` (64K, q8_0, có mmproj) | **21.451 MiB** (còn 2.875) | ngân sách VRAM |
| VRAM card bẩn → tràn | **24.102 MiB** (còn 224) | ngưỡng `don_dep` |
| VRAM nền (desktop) | **1.515 – 1.612 MiB** | ngưỡng `don_dep` = 2.500 |
| VRAM ComfyUI thường trú | **6.211 – 16.620 MiB** | ngưỡng `don_dep` |
| Nạp model | **15 – 21 giây** | `healthCheckTimeout` |
| Prefill | **1.050 – 1.190 tok/s** | **trần Cloudflare** |
| Decode có MTP | **63 – 70 tok/s** (trung vị 68,1) | giá token ra |
| Decode không MTP | **39,6 – 40,2 tok/s** | đối chứng |
| Decode trên card bẩn | **17,3 – 19,7 tok/s** | vì sao cần `don_dep` |
| Draft acceptance | **0,80 – 0,87** | — |
| Điện đỉnh · nhiệt đỉnh | **358 W · 62 °C** | chi phí biên, còn xa mốc throttle 84 °C |

### Chi phí điện tính lại theo số THẬT

358 W × 3.000đ/kWh = **1.074đ/giờ**.

| | Tốc độ đo | Token/giờ | Chi phí điện /1M | Giá bán | **Lãi gộp** |
|---|---:|---:|---:|---:|---:|
| Token ra | 68,1 tok/s | 245.160 | **~4.380đ = 44 credit** | 400 credit | **9,1×** |
| Token vào | 1.100 tok/s | 3.960.000 | **~271đ = 2,7 credit** | 50 credit | **18,5×** |

Biên rộng hơn ước tính ban đầu (8× / 16×) vì máy chạy nhanh hơn dự kiến.
