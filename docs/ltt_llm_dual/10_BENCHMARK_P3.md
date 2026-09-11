# P3 — Số đo trên máy B (RTX 3090 + RTX 5060 Ti)

Tài liệu kết quả của Task 3.2. Mỗi con số dưới đây đo bằng
`docs/ltt_llm_dual/artifacts/bench/do_g1_matrix.ps1` chạy như Scheduled Task
SYSTEM trên máy B, cổng thử **8290** — không đụng llama-swap (8280) và không
đụng lượt khách nào.

---

## G1 — Trần ngữ cảnh thật của `qwen38-api` trên card 24 GB

**Ngày đo:** 2026-09-11, 21:43–21:59. Engine **b10883**. GGUF
`Qwen3.8-27B-UD-Q4_K_M` (sha `322E194F…`). Nền 3090 lúc đo: **162 MiB**
(ComfyUI chưa nạp ngữ cảnh CUDA — dịch vụ chạy nhưng chưa vẽ lần nào).

Cấu hình chung mọi dòng: `-fa 1 -ngl 999 --spec-type draft-mtp
--spec-draft-n-max 2 --cache-type-k q4_0 --cache-type-v q4_0 -kvu --jinja
--reasoning-format deepseek`.

### 🔴 Trước hết: một ngưỡng của chính tôi đã SAI, và đối chứng đã bác nó

Bản đầu của cổng G1 đặt tiêu chí **`Shared Usage` phải = 0**. Lượt đo đầu tiên
(21:43) trả về `Shared Usage = 2.236 MiB` ở 262.144 và tôi suýt báo "không
vừa" dựa vào đó.

Đối chứng đã bác ngưỡng ấy: chạy **đúng cấu hình production đang phục vụ
khách** (`-c 204800 --parallel 1`, không mmproj — thứ đã đo 66,70 tok/s hôm
nay) qua **cùng bộ đếm** thì nó cũng báo **526–568 MiB**. Một cấu hình đang
chạy tốt không thể là "đang tràn".

⇒ `Shared Usage` có một **sàn cố định ~530–590 MiB** của engine/driver trên máy
này. **Phần tràn thật = Shared − sàn.** Không có dòng đối chứng ấy thì mọi con
số còn lại đều không diễn giải được, và kết luận sẽ là một con số đúng gắn vào
một câu sai.

*(Cùng gốc với ghi chép Task 0.3: production đo `Shared Usage 568 MiB`.)*

### Bảng đo

| `-c` | `-np` | vision | VRAM sau nạp | Shared | tràn thật | biên (24.576 −) |
|---:|---:|---|---:|---:|---:|---:|
| 204.800 | 1 | — | 21.649 | 526 | **0** | 2.927 |
| 204.800 | 4 | — | 22.995 | 540 | **0** | 1.581 |
| 204.800 | 4 | mmproj GPU | 24.131 | 540 | **0** | 445 |
| 212.992 | 4 | — | 23.219 | 556 | **0** | 1.357 |
| 212.992 | 4 | mmproj GPU | 24.279 | 632 | ~80 | 297 |
| 229.376 | 4 | — | 23.667 | 588 | **0** | 909 |
| 229.376 | 4 | **nooff** | 23.667 | 588 | **0** | 909 |
| 229.376 | 4 | mmproj GPU | 24.243 | 1.148 | ~600 | 333 |
| 245.760 | 4 | — | 24.115 | 620 | ~30 | 461 |
| 245.760 | 4 | **nooff** | 24.115 | 620 | ~30 | 461 |
| **262.144** | **3** | **nooff** | **24.115** | **648** | ~60 | **461** |
| 262.144 | 4 | — | 24.243 | 972 | **~400** | 333 |
| 262.144 | 4 | **nooff** | 24.243 | 972 | **~400** | 333 |
| 262.144 | 4 | mmproj GPU | 24.233 | 2.118 | **~1.550** | 343 |
| 262.144 | 1 | mmproj GPU | 24.231 | 760 | ~200 | 345 |

`nooff` = `--mmproj --no-mmproj-offload`.

### Ba điều bảng này nói

**1. `--no-mmproj-offload` làm vision tốn ĐÚNG 0 MiB VRAM.** Ba cặp dòng
(229.376 · 245.760 · 262.144) trùng khít từng MiB với bản không vision. Để
mmproj trên GPU thì nó tốn **~1.136 MiB** — bằng khoảng **40.000 token** ngữ
cảnh. Đây là cờ có sẵn của llama.cpp, không phải thứ ta chế ra.
⚠️ Đánh đổi chưa đo: mã hoá ảnh chạy trên CPU sẽ chậm hơn. Phải đo ở G4 trước
khi chốt — `token_moi_anh` và độ trễ ảnh là số của D07.

**2. KV tốn ~448 MiB mỗi 16.384 token** (≈ 28 MiB/1K) ở `q4_0`, `-np 4`.
Và **mỗi slot thêm tốn ~449 MiB**: 204.800 đi từ `-np 1` (21.649) lên `-np 4`
(22.995) là +1.346 MiB cho ba slot.

**3. 262.144 × 4 slot KHÔNG vừa card 24 GB.** Tràn ~400 MiB kể cả khi đã bỏ
mmproj khỏi GPU. Hai cách tiêu nốt gigabyte cuối, **cùng cho biên 461 MiB**:

| | ngữ cảnh | slot | biên |
|---|---:|---:|---:|
| A | 245.760 | **4** | 461 |
| B | **262.144** | 3 | 461 |
| C | 229.376 | 4 | **909** |

### ⚠️ Vì sao "tràn ~400 MiB" vẫn cho 58–63 tok/s trong phép đo này

Vì lượt thăm dò chỉ dài vài trăm token, nên **phần KV bị đẩy sang RAM chủ chưa
bị đọc tới**. Đúng cái làm sự cố 22/08 khó thấy: card bẩn vẫn `/health` xanh,
vẫn sinh chữ hợp lệ, chỉ tụt còn một phần tư **khi thật sự chạm vào phần đã
tràn**. ⇒ Tốc độ ở bảng trên **không** bác bỏ được kết luận "không vừa"; cột
`tràn thật` mới là cột phán xử.

### ⚠️ Biên 461 MiB là biên lúc ComfyUI CHƯA nạp ngữ cảnh

ComfyUI giữ **223,5 MiB** ngữ cảnh CUDA thường trú ngay khi đã vẽ một lần, và
`/free` **không** nhả nó — chỉ dừng dịch vụ mới nhả (đo 11/09, xem
`NHAT_KY_TRIEN_KHAI.md`). Nếu dịch vụ ảnh vẫn chạy trong cửa sổ LLM thì biên
thật của A và B là **~238 MiB**, dưới ngưỡng 300 MiB của chính cổng G1.

⇒ A và B **chỉ đạt** nếu trọng tài residency (Task 5.4) **dừng hẳn dịch vụ
LTTComfyUI** trong cửa sổ LLM — điều kế hoạch P5 đã yêu cầu sẵn. C đạt trong
cả hai trường hợp (686 MiB ngay cả khi ComfyUI ấm).

### Hai lỗi của chính phép đo — ghi lại để phiên sau không mất lại thời gian

1. **`max_tokens=32` + `--reasoning-format deepseek` ⇒ `content` rỗng.** Model
   còn đang nghĩ, khối `<think>` đi vào `reasoning_content`. Lượt G1 đầu tiên
   báo "trả lời rỗng" và suýt bị quy cho lỗi cộng đồng #27572. Đọc **cả hai**
   trường, và dùng 400 token.
2. **`"$nhan:"` trong PowerShell là tiền tố SCOPE.** Lỗi cú pháp ⇒ script chết
   trước dòng log đầu tiên: `Last Result 1`, không tệp log nào để đọc. Phải
   `$($nhan):`.

### Còn nợ của G1

- Đỉnh VRAM khi **4 luồng thật cùng chạy** (kịch bản `c4`) và khi **1 ảnh + 3
  text** (kịch bản `anh`) — bảng trên mới là VRAM *sau nạp* + một lượt ngắn.
- G2 (cổng đúng/sai của `draft-mtp` với `-np 4`) — `bench.py --kich-ban mtp_gate`.
- G4: `token_moi_anh` và độ trễ ảnh **khi mmproj chạy trên CPU** (`nooff`).

---

## G2–G5

Chưa chạy.
