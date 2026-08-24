# Chia một card cho hai model nhà — số đo, lời giải cộng đồng, và đề xuất

**2026-08-24.** Chủ sản phẩm hỏi: *"sau khi vận hành job xong thì nhả model về RAM
để giữ, model nào hoạt động sẽ đưa từ RAM sang VRAM — quy trình như vậy là tối ưu
nhất đúng không?"*

Trả lời ngắn: **hướng đúng, và một nửa đã tự chạy sẵn rồi.** Nhưng "cả hai nhả sau
job" cần sửa ở hai chỗ, và số đo nói rõ sửa chỗ nào.

---

## 1. Số đo thật, đo hôm nay trên máy B

| | Số đo | Cách đo |
|---|---|---|
| HiDream — đỉnh khi vẽ | **18.450 MB** | lô 100 lượt (D-056) |
| HiDream — thường trú lúc rảnh | ~16.600–16.900 MB | `nvidia-smi` khi GPU 0–1 % |
| HiDream — **nhả** (`POST /free`) | 15.616 MB trong **~0,2 giây** | 16.879 → 1.263 MB |
| HiDream — **nạp lại** | **+0,8 giây** | 110,5 s lạnh so với 109,7 s ấm |
| Qwen3.8-27B — thường trú | **19.237 MB** | ổn định qua 5 lần đo cách nhau 3 s |
| Qwen — **nhả** (`GET /unload`) | 0,7 giây | `running` về 0 model |
| Qwen — **nạp lạnh, card sạch** | **18 giây** | tính cả câu trả lời đầu tiên |
| Qwen — gọi ấm | 0,7 – 1,2 giây | |
| Qwen — TTL tự nhả hiện tại | **1.800 giây** (30 phút) | `llama-swap /running` |

Cấu hình Qwen đang chạy (đọc từ `/running`, không phải đoán):
`-ngl 999 -c 65536 --cache-type-k q8_0 --cache-type-v q8_0 --spec-type draft-mtp`.

### 🔴 Phép cộng quyết định mọi thứ

```
HiDream đỉnh   18.450 MB
Qwen thường trú 19.237 MB
                --------
tổng           37.687 MB      trên một card 24.576 MB
```

**Mỗi model một mình đã chiếm 75–78 % card.** Hai model **không bao giờ** cùng lúc
được — kể cả khi một bên ngồi im không làm gì (16.600 + 19.237 = 35.837, vẫn vượt).

⇒ Swap **không phải một tối ưu hoá**. Nó là **chế độ vận hành duy nhất** có thể.

### Và điều này giải thích con số "23,9 GB" mà tài liệu vẫn cảnh báo

Tôi từng ghi (D-056) rằng cảnh báo *"VRAM 23,9 / 24,6 GB = 97,5 %"* là **lỗi thời
vì đo trước `--reserve-vram 3`**. **Điều đó không đúng, hoặc không đủ.** Hôm nay tôi
tái hiện đúng 23.860 MB — bằng cách gọi LLM **trong lúc ComfyUI đang giữ model**.

Con số 23,9 GB không đo HiDream một mình. Nó đo **hai model đè nhau**. Đó chính là
cái nghẽn đang hỏi, không phải một số đo cũ.

---

## 2. Trả lời câu hỏi: hai chỗ cần sửa trong đề xuất

### ① "Nhả về RAM để giữ" — **đã có sẵn, đừng xây lại**

Máy B có 192 GB RAM. Trọng số model nằm trong **page cache của hệ điều hành**;
`POST /free` của ComfyUI chỉ nhả **bản trên VRAM**, không xoá bản trong RAM.

Đó là toàn bộ lý do nạp lại HiDream chỉ tốn **0,8 giây** — đúng thời gian đẩy
15,6 GB qua PCIe. Không cần viết tầng "giữ ở RAM" nào; nó là hành vi mặc định.

### ② Bất đối xứng **22 lần** ⇒ chính sách **không được đối xứng**

| | Nhả | Nạp lại |
|---|---|---|
| HiDream | 0,2 s | **0,8 s** |
| Qwen | 0,7 s | **18 s** |

- **HiDream nhả sau mỗi job là gần như miễn phí**: 0,8 s trên một job 110 s = **0,7 %**.
- **Qwen nhả sau mỗi request là không bán được**: khách chờ 18 giây cho *mỗi* câu.
  Với Codex/Claude Code gọi hàng chục lượt một phiên, đó là hàng phút chờ vô ích.

⇒ Chính sách đúng: **ảnh nhả sau mỗi job; LLM giữ thường trú và chỉ bị đuổi khi
có job ảnh thật sự cần card.**

---

## 3. Lời giải của cộng đồng — llama-swap đã có sẵn, không cần tự xây

Tra `mostlygeek/llama-swap` (đúng thứ đang chạy trên máy B) thì nó **đã có nguyên
bộ nguyên liệu**, kể cả phần dành riêng cho ComfyUI:

| Thứ | Dùng để làm gì |
|---|---|
| `groups` với `swap: true` | **chỉ một thành viên chạy một lúc** — loại trừ lẫn nhau, hai chiều, trong cùng nhóm |
| `groups` với `exclusive: true` | nạp một thành viên thì **đuổi mọi nhóm khác** |
| `matrix` + **`evict_costs`** | DSL swap có **giá đuổi từng model** — đúng cái bất đối xứng 0,8 s / 18 s ở trên |
| `POST /api/models/unload` · `/unload/:model_id` | đuổi theo yêu cầu |
| `GET /unload` | đuổi tất cả (đã thử trên máy B: **200 OK, 0,7 giây**) |
| `ttl` / `globalTTL` | tự nhả sau N giây rảnh |
| `hooks.on_startup.preload` | nạp trước lúc khởi động |
| **model tên `comfyui_auto`** | **ComfyUI thành một "model" do llama-swap quản** |
| lọc `^\/ws$\|^\/api\/jobs$` | để **một tab ComfyUI đang mở không gây swap** |

Tức là: cách làm chuẩn của cộng đồng là **đưa ComfyUI vào cùng một `group` với
Qwen, đặt `swap: true`** — rồi llama-swap tự lo phần loại trừ.

⚠️ **Một cái bẫy đã đọc trước:** `exclusive` của llama-swap là **một chiều**
(issue #215, đóng với trạng thái *not planned*): nạp một model ở nhóm
`exclusive: false` thì **không** đuổi nhóm `exclusive: true`. Cách tránh: đặt cả
hai vào **cùng một nhóm** với `swap: true` — trong cùng nhóm thì loại trừ là hai
chiều. Đừng dựa vào `exclusive` giữa hai nhóm.

---

## 4. ⛔ Nhưng ta KHÔNG dùng được bản đầy đủ, và lý do không nằm trong tài liệu nào

`comfyui_auto` hoạt động bằng cách **llama-swap sở hữu vòng đời tiến trình
ComfyUI** — nó `cmd` để bật và `cmdStop` để tắt.

Trên máy B, ComfyUI **dùng chung với dự án video** (`E:\LTT AI`, D-037). Nó là một
dịch vụ Windows (`LTTComfyUI` qua nssm) và **một người đang chạy việc trên đó**.

⇒ Nếu llama-swap tắt ComfyUI mỗi khi có yêu cầu LLM, nó sẽ **giết job video đang
chạy giữa chừng**. Một lượt video từng chạy **72,5 phút**. Đó là cái giá không ai
đồng ý trả, và không có cấu hình llama-swap nào biết về nó.

### Đề xuất: lấy đúng phần cần, không lấy phần sở hữu tiến trình

**Đừng tắt tiến trình ComfyUI — chỉ nhả VRAM của nó.** `POST /free` nhả 15,6 GB
trong 0,2 giây mà tiến trình vẫn sống, tab vẫn mở, job video vẫn còn đó.

Trọng tài đặt ở **`render_gateway`**, vì nó đã sở hữu quan hệ với ComfyUI và đã
có `busy.py` đọc VRAM thật:

```
Job ảnh tới:
  ① GET  llama-swap /unload          (0,7 s)   ← đuổi Qwen
  ② đọc nvidia-smi, CHỜ tới khi VRAM < ngưỡng  ← XÁC MINH, không giả định
  ③ gửi prompt cho ComfyUI                     (nạp lại +0,8 s)
  ④ job xong, chờ N giây không có job mới
  ⑤ POST ComfyUI /free               (0,2 s)   ← trả card cho LLM

Yêu cầu LLM tới:
  · card đã sạch (nhờ ⑤)  → nạp 18 s lần đầu, sau đó 0,7–1,2 s
  · Qwen giữ thường trú, TTL dài — nó chỉ mất card khi bước ① xảy ra
```

### 🔴 Bước ② là bước không có công cụ nào làm hộ, và là bước quan trọng nhất

**Đuổi phải được XÁC MINH bằng số đo, không được giả định.** Đây là bài học P6 và
D-051: nếu model kia chưa thật sự rời VRAM, model mới **âm thầm** offload một phần
sang RAM chủ — và mọi chốt sống/chết vẫn xanh trong khi tốc độ giảm 3–10 lần.

Hôm nay tôi tự dính đúng cái đó: khi hai model đè nhau tôi đọc được 23,86 GB và
**suýt kết luận sai** rằng LLM đang hỏng.

Nền tảng đã có sẵn nguyên liệu cho bước này: `render_gateway/busy.py` đọc VRAM thật
qua `nvidia-smi`, và `render_gateway/tren_gpu.py` (H37/L3) đã là chốt
"đang vẽ mà VRAM thấp". Cần thêm chiều ngược lại: *"sắp vẽ mà VRAM còn cao"*.

⚠️ Và **đếm tiến trình python là sai** — D-037: `llama-server.exe` không phải
python, nên chốt dò bận từng báo *rảnh* trong khi card chỉ còn 4,6 GB.

---

## 5. Ba thứ đã loại, nói ra để không ai đề xuất lại

| Không dùng | Vì sao |
|---|---|
| **MIG** (chia card thành nhiều phần) | RTX 3090 là Ampere **tiêu dùng** — không có MIG. Chỉ A100/H100 có. |
| **MPS** | Chia *tính toán*, **không chia bộ nhớ**. Không giải quyết 37,7 > 24,6. |
| **Offload một phần cho LLM** (`-ngl` thấp) | Đó **chính là** sự cố P6: 18 tok/s thay vì 63. Là suy giảm có kiểm soát, không phải giải pháp. |
| **Card thứ hai** | ✅ Đã kiểm: máy B chỉ có **một** RTX 3090 (`nvidia-smi` thấy 1 thiết bị; Windows thấy 1 GPU thật). Card Code 43 trong `CLAUDE.md` ở **máy khác**. Nên đây không phải đường ra cho máy B — nhưng **thêm một card vào máy B thì cả tài liệu này thành vô nghĩa**, và đó là cách sửa rẻ nhất nếu có card. |
| **Giảm ngữ cảnh / lượng tử hoá sâu hơn** | Cắt 64K → 32K tiết kiệm ~2 GB. Cần cắt **13 GB** mới đủ cho cả hai. Không tới. |

---

## 6. Việc cần làm, xếp theo giá trị trên công sức

| # | Việc | Vì sao trước/sau |
|---|---|---|
| **1** | `render_gateway` gọi `llama-swap /unload` **trước** khi gửi prompt, rồi **chờ VRAM xuống** mới gửi | Rẻ nhất, chặn đúng cái nghẽn hôm nay. Không cần đụng cấu hình llama-swap. |
| **2** | Sau job, chờ **N giây không có job mới** rồi `POST ComfyUI /free` | Trả card cho LLM. Chờ N giây (không nhả ngay) để một lô ảnh liên tiếp không nạp lại từng lần. Đề xuất N = 60 s. |
| **3** | Chốt **"sắp vẽ mà VRAM còn cao"** vào `tren_gpu.py`, và **cảnh báo** nếu bước ② hết giờ | Không có nó thì việc 1 hỏng lặng lẽ. |
| **4** | Hạ `ttl` của Qwen từ 1.800 s xuống ~600 s | Bớt thời gian Qwen ngồi không mà giữ card. Không hạ quá thấp: 18 s nạp lại là giá khách trả. |
| **5** | *(khi dự án video rời ComfyUI dùng chung)* chuyển sang `comfyui_auto` + `groups swap: true` | Bỏ được trọng tài tự viết, dùng đường chuẩn của cộng đồng. **Chưa làm được bây giờ.** |

⛔ **Việc 1 và 2 phải đi cùng nhau.** Chỉ làm 1 thì ảnh chạy được nhưng LLM chờ mãi
(ComfyUI không bao giờ nhả). Chỉ làm 2 thì ảnh vẫn đè lên Qwen.

⚠️ **Chưa có việc nào ở đây được viết.** Đây là đề xuất, không phải báo cáo đã làm.

---

## Nguồn

- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap) — README, tính năng
- [config.example.yaml](https://github.com/mostlygeek/llama-swap/blob/main/config.example.yaml) — `groups`, `matrix`/`evict_costs`, `ttl`, `cmdStop`, `hooks`, lọc ComfyUI
- [Issue #215 — Group exclusivity is only one-way](https://github.com/mostlygeek/llama-swap/issues/215) — đóng, *not planned*
- [Issue #643 — Groups V2 (Swap Matrix) Design](https://github.com/mostlygeek/llama-swap/issues/643)
- [Dynamic VRAM in ComfyUI](https://blog.comfy.org/p/dynamic-vram-in-comfyui-saving-local) — quản lý VRAM phía ComfyUI
- [ComfyUI — Automatically unload models from VRAM](https://forum.comfy.org/t/automatically-unload-models-from-vram/1511)
