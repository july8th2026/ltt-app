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

🔧 **Đính chính của chính mục này, đo ở G1b bên dưới:** cái sàn ấy **không cố
định**. Nó phần lớn là bộ đệm dàn trang theo `-ub`, nên ở `-ub 256` nó tụt còn
348 MiB. Mọi con số trong bảng ngay dưới đều đo ở `-ub` mặc định (512) nên so
với sàn 526–568 là đúng — nhưng **đừng mang sàn này sang đọc một `-ub` khác**.

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

## G1b — Chốt cấu hình: 3 slot, mmproj trên GPU, hạ ngữ cảnh cho vừa

**Chủ dự án quyết (2026-09-12, sau khi đọc bảng G1):** giữ **mmproj trên GPU**
(ảnh nhanh như hôm nay), **tối đa 3 slot** (bỏ mục tiêu C4), và **hạ ngữ cảnh
xuống cho phù hợp**.

⚠️ Hai lựa chọn đầu (262.144 **và** mmproj trên GPU) **không cùng vừa card**:
262.144 × 3 slot + mmproj GPU đo được cần ~25,2 GB. Đây là lần đo trả lời đúng
câu "vậy hạ xuống bao nhiêu".

### Quét ngữ cảnh ở `-np 3`, mmproj **trên GPU**

| `-c` | `-ub` | VRAM sau nạp | Shared | tràn thật | biên |
|---:|---:|---:|---:|---:|---:|
| 212.992 | 512 | 23.907 | 552 | **0** | 669 |
| **221.184** | **512** | **24.131** | **568** | **0** | **445** |
| 229.376 | 512 | 24.233 | 706 | ~140 | 343 |
| 237.568 | 512 | 24.275 | 904 | ~340 | 301 |
| 237.568 | 256 | 24.273 | 348 | **0** | 303 |
| 245.760 | 256 | 24.285 | 560 | ~210 | 291 |
| 262.144 | 512 | 24.243 | 1.656 | ~1.090 | 333 |
| 262.144 | 256 | 24.233 | 1.060 | ~490 | 343 |
| 262.144 | 128 | 24.259 | 728 | ~160 | 317 |
| 262.144 (`-np 2`) | 512 | 24.241 | 1.202 | ~630 | 335 |
| 262.144 (`-np 2`) | 256 | 24.221 | 616 | ~50 | 355 |

### ⭐ Cấu hình chọn: `-c 221184 -np 3`, mmproj trên GPU, `-ub` mặc định

Mốc **cao nhất còn sạch** ở `-ub` mặc định: `Shared 568` nằm đúng trong dải
sàn đã đo (526–568), biên **445 MiB**. Bước lên 229.376 là `Shared` đã vượt
sàn ~140 MiB — tức bắt đầu tràn.

So với 204.800 đang phục vụ khách hôm nay: **+16.384 token (+8 %)**, và vision
nằm trong **cùng một hồ sơ** (hôm nay phải đổi hồ sơ, mà đổi hồ sơ thì
llama-swap **giết lượt đang chạy** — đo 03/09).

### 🔑 Một phát hiện làm đổi cách đọc cả bảng: sàn Shared **không cố định**

Ở `-ub 256`, `Shared` tụt xuống **348 MiB** — thấp hơn cả "sàn" 526–568 đo ở
`-ub` mặc định. Vậy phần lớn cái tôi gọi là "sàn" ở mục G1 chính là **bộ
đệm dàn trang theo micro-batch**, không phải một hằng số của driver.

⇒ Sàn phải đo lại **cho từng `-ub`**; không được mang sàn của `-ub 512` sang
đọc một dòng `-ub 256`. Bảng trên đã tính theo luật đó.

### `-ub 256` được gì, mất gì — chưa đủ căn cứ để dùng

Nó cho thêm **16.384 token** (237.568 thay vì 221.184) với biên tương đương.
Nhưng `-ub` là **kích thước lô prefill**, nên hạ nó là trả bằng **tốc độ nạp
prompt** — thứ phép đo này **không đo được**: lượt thăm dò chỉ vài trăm token
nên con số tok/s ở đây gần như thuần decode. Với hồ sơ 220K, prefill mới là
phần khách chờ lâu nhất (đo 03/09: 130K mất ~179 s ở 726 tok/s).

⇒ Giữ `-ub` mặc định cho cấu hình chốt. Đưa `-ub 256` vào **G4**, đo prefill
tok/s thật ở 50K/100K/200K. Đổi 16K token lấy một prefill chậm hơn là cuộc đổi
chác **chưa có giá**, và chốt khi chưa có giá thì không phải chốt.

### Ba thứ cấu hình này kéo theo

1. **C4 → C3 cho LTT-3.8.** Đỉnh đồng thời giảm 25 %. `SO_SLOT` trong
   `apps/ltt_llm/ngan_sach.py` thành **3** (Task 2.6) và `llama-swap.yaml` dùng
   `-np 3` (Task 3.3). Mọi chỗ spec/plan viết "C4" phải đọc lại là **C3 cho
   LTT-3.8**; LTT-3.5 trên 5060 Ti chưa bị ràng buộc này — G3 sẽ đo riêng.
2. **Biên 445 MiB là biên lúc ComfyUI chưa nạp ngữ cảnh CUDA.** ComfyUI ấm
   giữ 223,5 MiB và `/free` không nhả ⇒ biên thật còn ~222 MiB. Trọng tài
   residency (Task 5.4) **phải dừng hẳn dịch vụ LTTComfyUI** trong cửa sổ LLM,
   không chỉ gọi `/free`. Đây là **ràng buộc cứng** của P5, không phải một
   tối ưu tùy chọn.
3. **`qwen38-vision` biến mất.** Một hồ sơ text+vision duy nhất ⇒ hết hẳn nguồn
   `ConnectionReset` do llama-swap đổi hồ sơ giữa chừng.

---

## G2 — `draft-mtp` có an toàn với nhiều slot không? **ĐẠT**

**Ngày đo:** 2026-09-12, 00:11 và 00:26. Cấu hình đã chốt (`-c 221184 -np 3`,
mmproj trên GPU). 201 lượt, 3 luồng đồng thời, mỗi lượt mang một dấu riêng
`DAU-<slot>-<nnn>`; 1/3 số lượt có prompt dài hơn ubatch, 1/5 có ảnh.

| | |
|---|---:|
| số lượt | **201** |
| trả lời rỗng | **0** |
| lẫn slot (đọc ra dấu của lượt khác) | **0** |
| lỗi | **0** |
| không đọc lại được dấu của mình | **0** |
| `spec_decode_num_accepted_tokens` | 0 → **48.514** |
| wall | 550 s |

⇒ Hai báo cáo cộng đồng (#27572 trả lời rỗng khi `-np > 1`, #26750) **không
tái hiện** trên build b10883 + cấu hình này, và draft-mtp thực sự đang làm
việc (48.514 token nháp được chấp nhận, không phải âm thầm tắt).

### 🔴 Lượt đầu báo `DAT: false` — và đó là lỗi của BỘ DÒ, không phải của engine

Lượt 00:11 báo **2 lần lẫn slot**. Đọc dữ liệu thô thì cả hai là giả:

```
lượt DAU-1-040  → thấy "DAU-1-0"
lượt DAU-2-047  → thấy "DAU-2"
```

Cả hai là **mảnh vỡ tiền tố của chính dấu nó** (model chèn định dạng vào giữa
chuỗi), không đúng khuôn một dấu thật, và cả hai lượt đều đọc lại **đúng** dấu
mình. Không có một byte nào của slot khác.

Bộ dò đã sửa để nó dò **đúng thứ nó tuyên bố**: một dấu đúng khuôn
`DAU-<slot>-<ba chữ số>` **thuộc slot khác**. Mảnh vỡ vẫn được báo ở trường
riêng (`so_manh_vo`, lượt 2 có 4) chứ không bị vứt — thu hẹp một phép kiểm cho
tới khi nó xanh thì dễ, thu hẹp cho nó đo đúng điều nó nói mới là việc phải làm.

⭐ **Đối chứng cho chính bộ dò:** `tests/test_1211_cong_mtp_bench.py` (7 ca) giữ
cả hai chiều — hai ca thật từng báo oan phải **xanh**, và một dấu thật của slot
khác phải **đỏ**. Không có chiều thứ hai thì "0 lượt lẫn slot" chỉ là một số 0
không ai kiểm lại được.

### Một sai lệch nhỏ của bản ghi, đã sửa

Lượt đầu chạy **4 luồng** trong khi server có **3 slot**, nên một phần lượt nằm
trong hàng đợi của llama.cpp chứ không ở trong slot. Vẫn hợp lệ, nhưng bản ghi
`so_luong: 4` không đúng với thứ đã chạy. Nay `--luong` bằng `-np`.

---

## G3 — LTT-3.5 trên RTX 5060 Ti: **ĐẠT phần VRAM**

**Ngày đo:** 2026-09-12, 00:35. Card **16.311 MiB**, nền lúc đo **54 MiB**.
`-c 262144 -kvu`, KV **q8_0**, mmproj trên GPU, **không** draft-mtp (spec).
Ngưỡng biên ở đây là **700 MiB** (chủ dự án chốt 12/09 — máy B chỉ chạy hệ
thống AI; đo được 5060 Ti lúc rảnh giữ **54 MiB**). Bản đầu của cổng đặt 2.048
theo một lo ngại chứ không theo phép đo — xem mục G3b.

| ứng viên | `-np` | VRAM sau nạp | Shared | tràn | biên | tok/s |
|---|---:|---:|---:|---:|---:|---:|
| unsloth | 4 | 13.531 | 354 | **0** | **2.780** | 50,63 |
| unsloth | 3 | 13.481 | 354 | **0** | 2.830 | 51,95 |
| lmstudio | 4 | 13.423 | 354 | **0** | **2.888** | 51,95 |
| lmstudio | 3 | 13.373 | 354 | **0** | 2.938 | 53,33 |

**262.144 × 4 slot vừa thoải mái trên 5060 Ti** — khác hẳn 3090, nơi cùng con
số ấy tràn. Lý do đơn giản: model 9B chỉ tốn ~7,3 GiB trọng số so với ~15,3 GiB
của 27B, nên dù card nhỏ hơn 8 GB thì phần còn lại cho KV vẫn rộng hơn.

⇒ **D06 đạt ở phần VRAM. Không cần REOPEN.**

### ⚠️ VRAM và tốc độ **không** chọn được giữa hai ứng viên

Lệch VRAM 108 MiB trên một biên 2,8 GiB là không đáng kể, và lệch tok/s
(50,63–53,33) nằm trong khoảng nhiễu của **một** lượt 400 token. Dùng một trong
hai con số đó để chọn là đọc nhiễu thành tín hiệu.

⇒ Chọn bằng **chấm chất lượng** (`tools/danh_gia_llm.py`, `--lan 3`, lấy trung
vị), đúng như kế hoạch nói. Đang chạy — kết quả ở mục dưới khi xong.

### G3 còn nợ

- C4 thật (4 luồng) + đỉnh VRAM khi có ảnh — bảng trên mới là VRAM *sau nạp*.
- Chấm chất lượng hai ứng viên ⇒ chọn một tệp.
- **Câu hỏi cho chủ dự án:** L-14 hạ LTT-3.8 xuống **3 slot** vì card 24 GB không
  đủ. Nhưng 5060 Ti **đủ cho 4 slot** ở ngữ cảnh đầy đủ. Để LTT-3.5 ở **4** (tận
  dụng phần cứng) hay **3** (hai model cùng một con số, dễ giải thích với khách)?
  Task 2.6 khai số slot **theo từng model** nên cả hai đều làm được.

## G3b — Chọn tệp: **unsloth**, vì nó là tệp DUY NHẤT chạy được MTP

VRAM không phân biệt được hai ứng viên (lệch 108 MiB trên biên 2,8 GiB), chấm
chất lượng cũng không (27/36 so với 27/36, và phần mất của cả hai nằm đúng ở
cùng hai bài tiếng Việt). Thứ phân biệt chúng nằm ở chỗ **không bảng nào trong
hai bảng trên nhìn tới**.

### Manh mối đến từ log nạp, không từ bảng số

Log nạp của ứng viên unsloth in ra:

```
W model has unused tensor blk.32.nextn.eh_proj.weight -- ignoring
W model has unused tensor blk.32.nextn.enorm.weight   -- ignoring
```

`nextn` là **đầu MTP** (suy đoán đa token). Tệp GGUF mang sẵn nó, và llama.cpp
**vứt đi** vì ta không truyền `--spec-type draft-mtp`. Cộng đồng mô tả đúng cái
bẫy này: *"Without the flag it prints 'unused tensor, ignoring' and you would
never guess spec decode works."*

Spec §2 ghi "LTT-3.5 chạy **không** MTP" — nhưng dòng đó viết **trước** khi biết
sẽ tải tệp nào, và ứng viên unsloth đến từ kho tên `Qwen3.5-9B-**MTP**-GGUF`.

### Phép đo A/B: cùng tệp, cùng mọi thứ, chỉ khác một cờ

| ứng viên | `--spec-draft-n-max` | `nextn` bị bỏ | VRAM | **tok/s** | spec chấp nhận |
|---|---:|---:|---:|---:|---:|
| unsloth | (không MTP) | 4 | 13.481 | 52,69 | 0 |
| **unsloth** | **2** | **0** | 15.309 | **73,00** | 1.028 |
| unsloth | 3 | 0 | 15.459 | 73,08 | 1.131 |
| lmstudio | (không MTP) | 0 | 13.373 | 53,30 | 0 |
| lmstudio | 2 | — | — | **KHÔNG NẠP ĐƯỢC** | — |

Dòng cuối là câu trả lời, và engine tự nói ra:

```
W llama_init_from_model: context type MTP requested but model doesn't contain MTP layers
E common_speculative_init_result: failed to create MTP context
E srv  llama_server: exiting due to model loading error
```

⇒ **Tệp lmstudio không có đầu MTP.** Dòng `nextn bị bỏ qua = 0` của nó **không**
nghĩa là "đã nạp MTP" mà là "không có gì để bỏ" — hai trạng thái khác hẳn nhau
cho ra **cùng một con số 0**. Nếu chỉ đọc cột đó mà không có dòng `mtp2` thì kết
luận sẽ ngược hẳn.

### ⭐ Chốt: `Qwen3.5-9B-Q6_K-unsloth.gguf` + `mmproj-9B-F16-unsloth.gguf`

**+38,5 % tốc độ giải mã** (52,69 → 73,00), và đó là thứ ứng viên kia **không
thể** có — không phải "tốt hơn một chút", mà là một năng lực vắng mặt.

`n-max 3` cho 73,08 (hơn 0,08 tok/s) nhưng tốn thêm 150 MiB ⇒ **chọn n-max 2**.

### Vì sao con số này lớn đến thế — và vì sao nó KHÔNG mâu thuẫn với vật lý

Giải mã bị chặn bởi **băng thông bộ nhớ**: mỗi token phải đọc toàn bộ trọng số.

| | RTX 3090 + 27B | RTX 5060 Ti + 9B |
|---|---:|---:|
| băng thông | 936 GB/s | 448 GB/s |
| trọng số phải đọc / token | ~16,5 GB | ~7,3 GB |
| trần lý thuyết | ~57 tok/s | ~61 tok/s |
| đo được (không MTP) | — | 52,7 (**87 %** trần) |
| đo được (có MTP) | 66,7 (**117 %**) | **73,0 (120 %)** |

87 % đã là sát trần — không còn gì để vắt bằng chỉnh tham số. Thứ **duy nhất**
vượt qua được trần ấy là sinh nhiều token cho mỗi lần đọc trọng số, tức suy
đoán. Đó cũng chính là lý do 3.8 đạt 66,7 trong khi trần của nó chỉ 57.

⇒ Và kết quả: **LTT-3.5 (73,0) nhanh hơn LTT-3.8 (66,7)**, dù card yếu hơn.

### MTP ăn 1.828 MiB VRAM — và ngưỡng biên đã được chủ dự án hạ

Biên trên 5060 Ti tụt **2.830 → 1.002 MiB**. Bản đầu của cổng G3 đặt ngưỡng
**2.048 MiB** với lý do "card này còn nuôi desktop và app nền chuyển từ 3090
sang (L-12)" ⇒ theo ngưỡng ấy thì phải hạ ngữ cảnh của 3.5 để lấy lại biên.

**Chủ dự án hạ ngưỡng xuống 600–700 MiB (2026-09-12):** *"bản chất ta chỉ chạy
hệ thống AI là chính"*. Và phép đo ủng hộ: 5060 Ti lúc rảnh chỉ giữ **54 MiB** —
tức con số 2.048 của tôi được đặt theo một **lo ngại**, không theo một **phép
đo**, và nó đắt hơn thực tế gần 40 lần.

⇒ Với ngưỡng **700 MiB**, biên 1.002 MiB **ĐẠT**. Không phải hạ ngữ cảnh:
**LTT-3.5 giữ trọn `-c 262144` VÀ có MTP.**

⚠️ Một điều kiện duy nhất còn phải kiểm: 54 MiB là lúc **không có phiên RDP nào
đang vẽ**. Desktop từng chiếm 193 MiB khi còn nằm trên 3090, nên lúc chủ dự án
điều khiển máy B qua RDP thì biên 1.002 có thể tụt vài trăm MiB. Vẫn trên 700,
nhưng phải **đo** chứ không suy — ghi vào phần nợ của G3.

### 🔴 Và một điều G3 **không** giải quyết: tiếng Việt

Chấm chất lượng: **6/6 lượt tiếng Việt trả rỗng, trên CẢ HAI ứng viên**, mỗi
lượt đốt đúng 1.400 token (chạm trần) trong 26,2–26,6 giây, trong khi bài tiếng
Anh xong trong 163–182 token / 3,2 giây.

| bài | unsloth | lmstudio |
|---|---|---|
| `vi-01`, `vi-02` | **0/3, 0/3** | **0/3, 0/3** |
| `en-01` | 3/3 | 3/3 |
| tổng | 27/36 = 75 % | 27/36 = 75 % |

Đổi tệp **không** sửa được điều này — nên nó không phải tiêu chí chọn tệp, mà là
một **hạng mục riêng phải giải trước khi bán 3.5 cho khách Việt**. Đang đo (mục
G3c) để tách bốn giả thuyết: trần token · khuôn chat đặt mức suy nghĩ quá cao ·
ngôn ngữ · cách đặt câu hỏi.

⚠️ Và lưu ý về công cụ: `tools/danh_gia_llm.py:217` chỉ đọc `content`, **không**
đọc `reasoning_content`. Với mọi hồ sơ chạy `--reasoning-format deepseek` — tức
cả production hôm nay — nó không phân biệt được "hỏng" với "đang nghĩ dở". Ở đây
kết luận không đổi (1.400/1.400 token + chạm trần là bằng chứng độc lập), nhưng
phải sửa trước khi dùng số của nó làm **cổng**.

## G3c — Tiếng Việt trả rỗng: nguyên nhân, và bản vá đưa bộ đề lên **36/36**

### Đây KHÔNG phải "model không biết tiếng Việt"

Lượt thành công trả lời **đúng** ("Hà Nội", "45000"). Thứ hỏng là model **không
bao giờ phát ra `</think>`** rồi đốt hết ngân sách token.

Ba sự thật từ tài liệu model + cộng đồng:

1. Qwen3.5 ở chế độ thinking có lỗi **truncated thinking** đã đo công khai:
   **17,4 %** đầu ra trên LiveCodeBench không phát ra `</think>`, và **84 %**
   số đó có tỉ lệ lặp > 30 %. `</think>` chỉ là **một token** trong từ điển
   (id 248069); vòng lặp lặp chữ làm xác suất của nó tụt, và **lượng tử hoá**
   (ta chạy Q6_K) làm tụt thêm vì nó là token tần số thấp.
2. **Qwen3.5 luôn "nghĩ" bằng tiếng Anh** (QwenLM issue #35) kể cả khi đề bài là
   thứ tiếng khác ⇒ đề tiếng Việt bắt nó suy luận **bắc cầu**, chuỗi dài và lỏng
   hơn, dễ vào vòng lặp hơn. Khớp số đo: **6/8 lượt tiếng Việt rỗng, 1/8 Anh**.
3. Tham số lấy mẫu mặc định của `llama-server` **lệch khuyến nghị Qwen ở bốn
   chỗ**, trong đó `presence-penalty 0` là chỗ nặng nhất — nó chính là phanh
   chống lặp mà chế độ hỏng này cần.

| | llama-server mặc định | Qwen (thinking) |
|---|---:|---:|
| temperature | 0,80 | 0,60 |
| top-k | 40 | 20 |
| min-p | 0,05 | 0 |
| **presence-penalty** | **0,00** | **1,50** |

### Bốn cách thử, đo bằng cả "có rỗng không" LẪN "có đúng không"

| cấu hình | vi_1tu rỗng | vi_tinh rỗng | đúng | token TB | giây TB |
|---|---:|---:|---:|---:|---:|
| A mặc định | 3/3 | 3/3 | **0/6** | 1400 | 26,5 |
| B tham số Qwen | 1/3 | 2/3 | 3/6 | ~990 | ~20 |
| **C + `--reasoning-budget 512`** | **0/3** | **0/3** | **6/6** | ~430 | **~9** |
| D `enable_thinking:false` | — | — | — | — | — |

Đối chứng dương `en_1tu` giữ **3/3 đúng ở cả ba** cấu hình chạy được — bản vá
không làm hỏng thứ vốn đã chạy.

⚠️ **B một mình là KHÔNG đủ** (còn 3/6 rỗng). Phải có cả phanh cứng. Khớp ghi
chép cũ về model 3.8: `reasoning_effort` dịch **xác suất** chứ không **chặn**.

⚠️ D **chưa đo được**: `--chat-template-kwargs '{"enable_thinking":false}'`
không nạp được vì lỗi truyền tham số của chính tôi qua PowerShell — **không**
phải kết luận về cờ đó. Không cần nữa vì C đủ, nhưng đừng đọc bảng này thành
"cờ ấy hỏng".

### ⭐ Chấm lại TOÀN BỘ bộ đề với bản vá: 27/36 → **36/36**

Bản vá hoạt động bằng cách **cắt ngắn khối nghĩ**, nên thứ bị cắt có thể là thứ
một bài khó đang cần. Phải chấm cả bộ chứ không chỉ hai bài tiếng Việt:

| nhóm | trước | sau |
|---|---:|---:|
| tieng_viet | **0 %** | **100 %** |
| lap_trinh | 66,7 % | **100 %** |
| sua_loi | 66,7 % | **100 %** |
| sinh_dai | 66,7 % | **100 %** |
| cau_truc · chon_tool · ngu_canh_dai · tieng_anh | 100 % | 100 % |
| **TỔNG** | **27/36 = 75 %** | **36/36 = 100 %** |

⇒ **Không phải một cuộc đổi chác.** Ba nhóm "mất một phần" trước đó cũng do
chính chế độ nghĩ-lòng-vòng, không phải do model yếu. Và mọi bài đều nhanh lên.

### Cấu hình chốt cho LTT-3.5 (vào `llama-swap.yaml` ở Task 3.3)

```
--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 1.5
--reasoning-budget 512
```

Tham số lấy mẫu đặt ở **server**, không gửi theo request: cache CUDA graph khoá
theo bộ tham số, và `danh_gia_llm.py` cố ý không truyền chúng.

### 🔴 Việc này CHƯA làm cho LTT-3.8 — và phải làm

Ghi chép cũ đã đo model 3.8 có **cùng** chế độ hỏng (~1/2 lượt ngữ cảnh dài trả
`content` rỗng, `reasoning` đầy chữ) và đã kết luận *"bản sửa đáng tin duy nhất
là `--reasoning-budget N`"* — nhưng để lại một dòng: *"chất lượng ở chế độ
runaway của phanh cứng **chưa đo**"*.

Nay đã đo, trên 3.5: phanh cứng **không** hạ chất lượng, nó nâng. Đó là bằng
chứng mạnh nhưng **trên một model khác**. Task 3.3 phải áp cùng bộ cờ cho
`qwen38-api` và **chạy lại `danh_gia_llm` cho nó** trước khi tin.

---

## G4 — Bốn tham số theo model (đo 2026-09-12, 02:0x)

Đo trên **đúng cấu hình sẽ triển khai** (L-14 ngữ cảnh + slot, L-15 bộ cờ).

| | LTT-3.8 (3090) | LTT-3.5 (5060 Ti) |
|---|---:|---:|
| **token mỗi ảnh** 1024×768 | **770** | **770** |
| nạp từ kho **ấm** | **16,3 s** | **12,1 s** |
| prefill @ 786 token | 977 tok/s | 1.765 |
| prefill @ 6,7K | 1.239 | **2.238** |
| prefill @ 32,6K | 1.132 | 2.059 |
| prefill @ 98K | 842 | 1.630 |
| prefill @ 163K | 646 | **1.350** |
| điện ở C1 | **314 W** | **119 W** |

### `token_moi_anh` = 770, và nó giống nhau ở cả hai model

Đo bằng **hiệu** giữa cùng một câu hỏi có ảnh và không ảnh (17 → 787 token), nên
phần chữ triệt tiêu và phần còn lại đúng là của ảnh. Không ước bằng công thức
patch: mỗi bản mmproj băm ảnh một kiểu, và con số này **đi thẳng vào hoá đơn**.

⇒ Một ảnh ≈ 770 token vào. Với trần vào công khai thì **4 ảnh ≈ 3.080 token**,
tức chưa tới 2 % ngữ cảnh — giới hạn ≤ 4 ảnh của spec §2 không phải ràng buộc
về bộ nhớ, nó là ràng buộc về chất lượng/giá.

### `T_NAP_LLM` thật là **16,3 s**, không phải 45,0

Máy trạng thái residency (Task 5.2, `t_nap_llm_s = 45.0`) đang giả định con số
gấp **2,8 lần** thực tế. Đây là một tham số **quyết định khi nào đáng đổi cư
trú** giữa model ảnh và LTT-3.8 trên 3090 — giả định quá cao làm trọng tài ngần
ngại đổi, tức 3090 nằm sai chỗ lâu hơn cần thiết.

⇒ Task 5.2 phải thay `45.0` bằng **16,3** và dẫn nguồn về đây.
⚠️ 16,3 s là **kho ấm** (tệp vừa đọc ở lượt trước). Cổng **G5** đo kho lạnh —
trọng tài gặp cả hai, nên nó cần cả hai con số chứ không một.

### Prefill: LTT-3.5 nhanh gấp ~2 lần ở mọi độ dài

Và khoảng cách **không** thu hẹp khi prompt dài ra (1,8× ở 6,7K, 2,1× ở 163K).
Với một lượt 163K token vào, khách chờ prefill **257 s trên 3.8** so với **125 s
trên 3.5** — chênh hơn hai phút, trong khi phần sinh chữ chỉ khác nhau vài giây.

⇒ `NGUONG_WHALE` (từ độ dài nào thì một lượt là "cá voi" đủ làm nghèo slot của
người khác) phải **khác nhau theo model**, không dùng chung một con số.

### Điện: 3.5 rẻ hơn **2,6 lần**

314 W so với 119 W cho cùng một lượt C1. Cộng với việc 3.5 còn **nhanh hơn**, chi
phí điện trên mỗi triệu token ra của 3.5 thấp hơn khoảng **ba lần** — đó là số
đi vào công thức giá D07 (Task 2.5).

### ⚠️ Một con số của G4 buộc phải kiểm lại, chưa được dùng

`dien_c1` đo LTT-3.8 ở **56,0 tok/s** — **dưới** ngưỡng cổng nghiệm thu B
(60,0 tok/s, R18). Nếu đúng thì cấu hình sẽ triển khai không đạt cổng của chính
nó. Nhưng đó là **một** lượt, và phép đo "giá của bộ cờ" ngay sau đó cho thấy
phương sai giữa các lần chạy ~5–8 % (một cấu hình còn *nhanh hơn* bản không cờ,
điều vô lý về mặt cơ chế). Một lượt không kết luận được.

⇒ Đang đo lại: 5 khối **xen kẽ** (X, Y, X, Y…) thay vì hai lô liền, lấy trung vị
— xen kẽ để máy nóng lên hay một tiến trình chen ngang ảnh hưởng **đều** lên cả
hai nhánh thay vì đổ trọn vào một bên.

### Điều G4 đã loại trừ

`spec_decode_num_accepted` giữ ~1.000 ở **cả bốn** biến thể cờ (không cờ · chỉ
tham số lấy mẫu · chỉ `--reasoning-budget` · cả hai) ⇒ **không cờ nào của L-15
làm hỏng suy đoán MTP**. Giả thuyết đó chết.

---

## G5 — Kho ấm và kho lạnh: chênh nhau **ít hơn nhiều** so với lo ngại

**Ngày đo:** 2026-09-12, 08:16. Ba lượt mỗi chế độ, lấy trung vị.

### Nạp từ kho ấm (đo trực tiếp)

| model | trung vị | ba lượt |
|---|---:|---|
| LTT-3.8 | **15,23 s** | 15,30 · 15,23 · 15,21 |
| LTT-3.5 | **10,12 s** | 10,12 · 10,12 · 10,09 |

Phương sai gần như bằng không (±0,05 s) — nạp model là thao tác rất ổn định.

### 🔴 Kho lạnh KHÔNG đo trực tiếp được, và đây là lý do

Máy B có **223,9 GB RAM**, đang trống **149,8 GB**, standby cache **24,8 GB**.
Muốn đẩy tệp model ra khỏi cache thì phải đọc **~165 GB** dữ liệu khác qua đó —
trên một máy đang phục vụ khách, và nó sẽ xoá cache của cả ComfyUI lẫn gateway.
Cái giá đó không đáng cho một con số.

⛔ Hai lần thử đầu của tôi đều sai và đáng ghi lại:

1. `--load-mode direct` — **giá trị này không tồn tại**. Tôi bịa nó. Bản b10883
   chỉ nhận `auto` · `none` · `mmap` · `mlock`. Sáu lượt đo trượt sạch.
2. Đọc tệp ứng viên lmstudio (đã 7 giờ không dùng) tưởng là "gần lạnh" ⇒ đo
   được **3.455 MB/s**. Đó là tốc độ RAM, không phải đĩa — tệp vẫn nằm trong
   cache. Một phép đo nhanh bất thường là dấu hiệu nó **không đo thứ ta tưởng**.

### ⭐ Cách đo được: đọc bỏ qua cache hệ điều hành

`FILE_FLAG_NO_BUFFERING` (`FileOptions` `0x20000000`), đệm 4 MiB căn theo sector:

```
4,00 GB (KHÔNG qua cache) trong 1,6 s = 2.592 MB/s
```

Đó là tốc độ đĩa **thật** của `H:` — NVMe. Đối chiếu: cùng tệp đọc qua cache cho
3.455 MB/s, tức đĩa chỉ chậm hơn RAM **1,33 lần** cho tải tuần tự.

### Cận trên của kho lạnh, dẫn xuất từ hai phép đo thật

| model | tệp | đọc từ đĩa | đọc từ RAM | chênh | **nạp lạnh ước** |
|---|---:|---:|---:|---:|---:|
| LTT-3.8 | 16,46 GB | 6,50 s | 4,88 s | +1,62 s | **≈ 16,9 s** (+11 %) |
| LTT-3.5 | 7,68 GB | 3,03 s | 2,28 s | +0,76 s | **≈ 10,9 s** (+7 %) |

⇒ **Kho lạnh chỉ đắt hơn 7–11 %.** Vì nút thắt của việc nạp **không phải** đọc
tệp mà là đẩy trọng số lên GPU và cấp phát ngữ cảnh — hai thứ không đổi giữa ấm
và lạnh. Trên một máy có đĩa chậm (SATA SSD ~500 MB/s) kết luận sẽ ngược lại;
con số này là của **máy B**, đừng mang đi nơi khác.

### Điều này nói gì cho trọng tài residency (Task 5.2)

1. **`t_nap_llm_s = 16,3` (G4) đứng vững**, và nay có cận trên: **17 s** phủ cả
   hai trường hợp. Không cần hai con số như tôi từng nghĩ.
2. Và trong vận hành thật, trường hợp **lạnh gần như không xảy ra**: hồ sơ mới
   (Task 3.3) đặt `ttl: 0` + `preload`, nên hai model nằm thường trú; trọng tài
   chỉ tháo/nạp **LTT-3.8** trên 3090, và lần nạp lại luôn cách lần trước vài
   phút — thừa sức còn trong standby cache 24,8 GB.

   > ⚠️ **ĐÍNH CHÍNH 13/09/2026 — vế `ttl: 0` của câu trên đã HẾT ĐÚNG.**
   >
   > Hồ sơ nay đặt **`ttl: 1800`** (30 phút), chủ sản phẩm chốt. Lý do không
   > phải sở thích: `ttl: 0` đã làm `qwen35-api` **ngừng phục vụ hoàn toàn** —
   > `VRAM trong 536 MiB < san 600 MiB`, cổng từ chối mọi lượt mới, `ltt-3.5`
   > trả 503. 5060 Ti nuôi cả desktop Windows (L-12), và với `ttl: 0` model
   > không bao giờ nhả nên card không có đường tự thoát.
   >
   > **Kết luận "lạnh gần như không xảy ra" vẫn đứng**, nhưng nay nhờ `preload`
   > (lo lúc khởi động) chứ không nhờ `ttl: 0`. Cái đổi là: sau **30 phút rảnh**
   > model *sẽ* nhả, nên lượt kế tiếp trả giá nạp — và đó là giá **ấm**, không
   > phải lạnh, vì trang GGUF còn ở standby list.
   >
   > 📏 Đo lại 13/09 bằng đồng hồ thật (3 lượt/model, `/unload` rồi gọi):
   >
   > | model | nạp ấm (tổng) | đã sẵn | **giá nạp** |
   > |---|---:|---:|---:|
   > | `qwen35-api` | 12,76 s | 2,23 s | **~10,5 s** |
   > | `qwen38-api` | 20,35 s | 0,97 s | **~19,4 s** |
   >
   > Khớp cỡ với G5 (10,12 / 15,23 s) ⇒ hai phép đo độc lập cùng nói một điều.
   >
   > ⛔ Và một khuyết tật của phép đo đầu tiên, giữ lại vì nó suýt lọt:
   > `llama-swap /unload` nhả **TẤT CẢ** model, không chỉ một. Nên đối chứng
   > "đã sẵn" chạy sau vòng của model kia thực ra đo một lượt **nạp lại** — nó
   > ra 15,04 s, *lâu hơn* cả nạp ấm 12,76 s. Chính sự vô lý ấy tố cáo phép đo.
   > Cách đúng: gọi cùng một model **nhiều lần liên tiếp**, bỏ lượt đầu.


## Phụ lục — Có cần nâng llama.cpp lên bản mới không? **Chưa cần**

Máy B chạy **b10883** (`91f6a6cf3`); master ở **b10909** — đúng **31 commit**.
Soát cả 31: phần lớn là Vulkan / Metal / s390x / OpenCL / CI, không chạm
CUDA-Windows. Ba cái đáng nhìn:

| commit | nội dung | cắn ta không |
|---|---|---|
| `b0dcb819` (**b10906**) | server: fix speculation after an image | phải đo |
| `5cdd3d1d` | fix MTP KV allocation | **không** — chỉ deepseek2, glm4moe, cohere2moe (đã kiểm danh sách đầy đủ, **không có qwen35**) |
| `fa676981` | fix mtmd chunk với DFlash | **không** — DFlash, ta dùng MTP |

`b0dcb819` đáng lo trên giấy: trước nó, server truyền **số token** thay vì **vị
trí** cho bộ nháp sau khi xử lý ảnh, làm suy đoán tụt hiệu quả **im lặng**. PR
nói rõ nó ảnh hưởng *"every drafter, not just DFlash"* — kể cả MTP. Và đó đúng
là hình dạng hồ sơ gộp text+vision + `draft-mtp` của LTT-3.8 sau L-14.

Nhưng con số 152 → 51 tok/s trong báo cáo gốc đo trên **ROCm với DFlash2**.
Kiến trúc khác, bộ nháp khác, card khác. "Lỗi có trong mã" không trả lời được
câu **"nó làm chậm máy của TA bao nhiêu"** — mà chỉ câu đó mới quyết được lúc
nâng cấp.

### Đo (`probe_anh_spec.py`, b10883, hồ sơ 3.8 đã chốt, `-np 1`)

| bài | tok/s | token ra | spec chấp nhận / token |
|---|---:|---:|---:|
| A — 4 lượt text, **không** ảnh trước | 64,06 | 1.200 | 1,165 |
| B — 1 lượt **ảnh**, rồi 4 lượt text y hệt | 62,57 | 1.200 | 1,145 |
| **tỉ lệ B/A** | **0,977** | — | **0,983** |

⇒ Chênh **~2 %** ở cả tốc độ lẫn tỉ lệ chấp nhận suy đoán — nằm trong nhiễu.
**Lỗi #28715 không cắn vào cấu hình của ta.** (`-np 1` để loại may rủi về việc
lượt text rơi vào slot chưa từng thấy ảnh.)

### Kết luận

**Giữ b10883 hết P3.** Mọi con số của G1/G1b/G2/G3 nằm trên bản này; đổi engine
là chúng hết hiệu lực (kho đã có bài học: b10883 so với b10689 **đổi cả đầu ra**,
không chỉ tốc độ).

**Nâng ở Task 3.3** — lúc viết lại `llama-swap.yaml` thì phải chạy lại cổng đo
sẵn rồi, nên một lượt chạy lại phục vụ cả hai việc. Lên **b10906 trở lên**, giữ
nguyên dòng CUDA 13 (bản đang cài dùng `cublas64_13.dll`, chạy tốt), có sẵn bản
dựng Windows CUDA đóng gói theo từng build nên là **tải + thay**, không phải
biên dịch. Bắt buộc chạy lại C1 + G1 + G2 trên bản mới trước khi cho khách dùng.

⚠️ Ghi chú đã kiểm chứ không suy: ghi nhớ cũ *"cuBLAS INVALID_VALUE thì phải hạ
CUDA"* là chuyện **torch cu130 trên pod thuê cho WanGP**, không liên quan
llama.cpp ở máy B. Không áp dụng ở đây.

---

## G6 — Đo TRƯỚC cổng nghiệm thu **C** và **E** cho LTT-3.5 (2026-09-12)

⭐ **Chạy được ngay giữa ban ngày, rủi ro bằng không**, và đó là điều đáng nhớ hơn
   cả các con số: LTT-3.5 ở trên **RTX 5060 Ti**, và **sản xuất không dùng card
   đó** (ComfyUI ghim 3090; `llama-swap` sống chỉ có hồ sơ 3.8). Nên một
   `llama-server` riêng ở cổng 8292 **không chạm** gì đang phục vụ khách. Phép đo
   này chạy **song song** với bốn agent đang viết mã, không làm chậm gì.

⚠️ Đây là **đo trước**, không phải nghiệm thu. Nghiệm thu thật chạy một lần sau
   Spec 2, **qua llama-swap** với hồ sơ thật. Mục đích ở đây: biết sớm nếu cấu
   hình đã chốt không đạt cổng, lúc còn sửa được rẻ.

Cấu hình = đúng thứ sẽ chạy thật: L-14 (`-c 262144 -np 3 -kvu`, KV `q8_0`, mmproj
trên GPU, `draft-mtp n=2`) + bộ cờ L-16. Kịch bản + JSONL từng lượt:
`artifacts/nghiem_thu_35/`.

### Cổng C — C1 văn bản + ảnh

| | |
|---|---|
| decode (trung vị 5 lượt) | **71,41 tok/s** (dải 70,96–73,19) |
| TTFT | **1,08 s** |
| prefill | **2.068 tok/s** |
| nạp từ kho ấm | **9 s** |
| ảnh (3 lượt) | **3/3 đúng**, trả lời tiếng Việt: *"Hình tròn màu đỏ… bên trái"* |

⇒ **C ĐẠT.** Và nó trả lời luôn một câu bỏ ngỏ: bộ cờ L-16 (`--reasoning-budget
512` + tham số Qwen, không `presence-penalty`) cho ra tiếng Việt đúng **kể cả ở
đường ảnh** — khối `reasoning` của lượt ảnh viết bằng tiếng Việt có dấu, không
rơi về tiếng Anh.

### Cổng E — C3 (ba luồng song song)

| lượt | wall | tổng theo **wall** | tổng theo **decode** | TTFT |
|---|---|---|---|---|
| 1 | 16,91 s | 106,4 tok/s | 135,7 | 2,99–3,47 s |
| 2 | 17,29 s | 104,1 | 136,4 | 3,46–3,93 s |
| 3 | 17,39 s | 103,5 | 134,6 | 3,38–3,86 s |

🔴 **E KHÔNG ĐẠT theo chữ của spec, và cái sai nằm ở NGƯỠNG chứ không ở máy.**
Spec §23 viết *"tổng ≥ 2 × C1 của chính nó"* ⇒ 2 × 71,41 = **142,8**. Đo được
**135,7** (theo decode) hoặc **104,1** (theo wall) — tức **95 %** hoặc **73 %**.

Ba điều bảng này nói:

1. ⛔ **"Tổng" của spec không nói rõ là tổng NÀO**, và hai cách đọc lệch nhau
   **30 %**. `tok_s_tong` tính `token_ra / wall` nên **gồm cả prefill**; tổng
   decode thì không. So một số có prefill với `2 × C1` (thuần decode) là so hai
   đại lượng khác nhau — đúng hạng lỗi *"đo đại lượng đề bài đặt tên, thay vì đại
   lượng khách phải chờ"*. **Nghiệm thu thật phải chốt định nghĩa trước khi chấm.**
2. Ngưỡng `2 ×` là **con số viết trước khi đo** (spec ghi `[CHI TIẾT SPEC]` ngay
   tại chỗ ấy), và nó viết cho **C4**. L-14 hạ xuống **C3**. Một ngưỡng suy từ 4
   luồng áp lên 3 luồng thì nó không đo gì cả.
3. Cái **đo được** và đáng giữ làm mốc: ở 3 luồng, mỗi luồng còn **~45 tok/s**
   (từ 71,4), tức **1,90×** thông lượng decode của một luồng. MTP nhận nháp
   **6.420/10.238 = 62,7 %** — khoẻ, không có dấu hiệu hỏng của #27572.

⇒ Đề nghị cho nghiệm thu: E chấm bằng **tổng decode ≥ 1,8 × C1** (đo được 1,90×,
biên 5 %), và **nói rõ** là tổng decode. Ngưỡng `2×` giữ lại trong spec như một
kỳ vọng đã bị phép đo bác — không âm thầm đổi số rồi coi như nó luôn thế.

### 🔴 Và phép đo này ĐỔI MỘT CON SỐ ĐÃ CHỐT: sàn VRAM 700 → 600

| | VRAM dùng | **trống** |
|---|---|---|
| nạp xong, rảnh | 15.309 / 16.311 MiB | **1.002** |
| đỉnh C1 | 15.425 | 886 |
| **đỉnh ảnh + C3** | **15.555** | **756** |

L-18 chốt sàn **700** dựa trên con số **lúc rảnh** (~1.000 ⇒ "còn ~300 MiB dư").
Nhưng cửa sàn chạy **trước mọi lượt**, kể cả lượt thứ ba lúc hai lượt kia đang
chạy — tức nó đọc **756**, không đọc 1.002. Sàn 700 chỉ cách đỉnh **56 MiB**: một
lát cắt nhỉnh hơn một chút là một **429 giả**, và khách không phân biệt được
"bận thật" với "thước đo quá sát".

⇒ Hạ về **600** — vẫn trong dải chủ dự án cho phép (600–700), để lại **156 MiB**.
Xem `DECISION_LOG.md` **L-18** (đã đính chính).

⚠️ `Shared Usage` đỉnh **672–678 MiB** ở cấu hình này. Đó là **sàn WDDM**, không
   phải tràn: nó khác 0 ngay cả khi mọi thứ khoẻ, và nó co giãn theo `-ub`. Ai
   viết báo động cho Task 6.3 phải đọc con số này trước khi đặt ngưỡng `> 0`.
