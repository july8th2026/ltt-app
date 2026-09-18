# Kết quả cửa sổ C4 máy B — số slot (`-np`) ở `-c` không đổi — 18/09/2026

**Một dòng:** **LTT-3.8 giữ `-np 3 -c 221184`** (np4 ở `-c 221184` tràn shared; np4 ở `-c 204800`
không tràn nhưng mỗi luồng rơi còn 48 % tốc độ đơn luồng). **LTT-3.5 lên `-np 4 -c 262144` là
phương án đạt biên**: VRAM sạch, 0 rò, 0 rỗng, khoảng lặng và prefill không đổi, tổng +15 %.
Chỉ trượt tiêu chí "mỗi luồng ≥ ~60 % đơn luồng" 2,5 điểm (57,5 %); lý do vẫn đề xuất ở §4.
np5/np6 (3.5) và np5 (3.8) đều tràn ⇒ bỏ. Chủ dự án/phiên chính quyết; phiên đo **không**
đổi `ngan_sach.py`, yaml hay deploy.

## 0. Điều kiện

| mục | giá trị |
|---|---|
| Giờ (UTC+7) | 14:58 (điều kiện bắt đầu: `l2_t7b_admin.log` có `TONG EXIT=0` + `c4_go.txt`) → 16:03 (khôi phục + `c4_done.txt`) |
| Đường đo | `ssh -L 18280:127.0.0.1:8280` → **llama-swap** trên B (không qua cổng 8299, không tốn credit, chịu được restart cổng) |
| Engine | llama.cpp `b10883-91f6a6cf3`, llama-swap v250 `-watch-config` |
| Cờ chung | như production (`-kvu`, `draft-mtp` n-max 2, `--cache-ram 24576`, `--ctx-checkpoints 8`; 3.8 `-b 512 -ub 512`, 3.5 b/ub mặc định 2048/512); chỉ đổi dòng `-np`/`-c` bằng `c4_18_09/gen_yaml.py` |
| Tải ngoài | Trước mỗi phép: `/running` + `/upstream/<model>/slots` phải rảnh (`cho_ranh` trong `c4_do.py`) và 0 kết nối Established vào 8299 từ ngoài loopback. Không lần nào phải chờ. LTTComfyUI Stopped suốt cửa sổ |
| Một model một lúc | mỗi lần lưu yaml nạp lại cả hai model; đo 3.8 thì `POST /api/models/unload/qwen35-api` và ngược lại. Riêng canary (§3) chạy hai model song song (đúng tính, không đo tốc độ) |
| Điểm lùi | `H:\LTT_LLM\gateway\llama-swap.yaml.c4-20260918-145823`, SHA-256 `168e23c9…dfca` (= yaml gốc = kho `main`) |
| Công cụ | `c4_18_09/c4_do.py` (đo), `c4_18_09/c4_b.ps1` (VRAM/log/backup/apply trên B), `c4_18_09/gen_yaml.py`, `c4_18_09/kiem_co_lap_llm_c4.py` (canary nhánh `phien/canary-co-lap`, sửa `dong_thoi` bắn N = `--song-song` luồng thay vì cố định 3). Thô: `c4_18_09/ket_qua/` |

**Phương pháp (mọi cấu hình giống hệt):** ấm — 1 lượt ngắn + 1 lượt 32K **bỏ đi**, rồi hiệu chỉnh tài liệu
về ~32,8K token. Mọi prompt có nonce ở **đầu** (không trúng cache). Số là **trung vị n=3**, thời gian từ
`timings` của engine (`prompt_ms`, `predicted_per_second`). `reasoning_effort=low` cho mọi lượt.

- **prefill 32K một mình**: 3 × ~32,8K token, `max_tokens` 1.
- **1 luồng**: prompt ~1K, `max_tokens` 1024.
- **N luồng = np**: 3 đợt × np luồng đồng thời, `max_tokens` 1024; tổng = Σ `predicted_n` / (token cuối − token đầu của cả đợt); mỗi luồng = `predicted_per_second`.
- **lặng cạnh prefill 32K**: (np − 1) luồng nhỏ (~1K vào, 2600 ra) bắt đầu, sau 8 s chèn 1 prompt 32K
  ⇒ tải đủ np slot. Cửa sổ prefill = [token đầu job to − `prompt_ms`, token đầu job to]. Lặng = khoảng trống
  dài nhất giữa hai chunk của một luồng nhỏ giao với cửa sổ; lấy luồng tệ nhất mỗi đợt, trung vị 3 đợt.
- **#27572** (MTP + np>1, rỗng): công thức của issue — np luồng đồng thời, mỗi luồng system ~16K token
  **khác nhau**, `max_tokens` 1200 (3.8) / 2600 (3.5 — sàn budget 2048 + 512), 2 đợt. Đếm `finish=stop` mà
  `content` rỗng, và `draft_n_accepted = 0` (chữ ký gốc: acceptance sập về 0). Ngoài ra mọi lượt khác
  trong mọi phép cũng được đếm cùng tiêu chí rỗng.
- **VRAM**: `\GPU Process Memory(pid_*)\Dedicated/Shared Usage` của đúng tiến trình `llama-server` +
  `nvidia-smi`. Sàn shared (-ub 512): 3.8 ≈ 526–584, 3.5 ≈ 644–678 (đo lại hôm nay ở np3). Tràn = shared
  vượt sàn > 100 MiB.

## 1. VRAM và nạp (tiêu chí 1)

| model | np | -c | dedicated MiB (nạp → sau đo) | shared MiB (nạp → sau đo) | Δ shared so sàn np3 | card dùng / tổng | kết luận |
|---|---|---|---|---|---|---|---|
| 3.8 | 3 | 221184 | 23999 → 24007 | 580 → 584 | 0 | 24072 / 24576 | nền |
| 3.8 | **4** | **221184** | 24169 | **822** | **+242** | 24234 / 24576 | ❌ tràn |
| 3.8 | 4 | 204800 | 23971 → 24005 | 540 → 558 | −26 | 24070 / 24576 | ✅ sạch |
| 3.8 | 5 | 221184 | 24184 | **1266** | **+686** | 24248 / 24576 | ❌ tràn (chỉ đo nạp) |
| 3.5 | 3 | 262144 | 15365 → 15375 | 672 → 678 | 0 | 15788 / 16311 | nền |
| 3.5 | **4** | 262144 | 15407 → 15525 | 644 → 684 | +6 | 15938 / 16311 | ✅ sạch (biên card ~373 MiB) |
| 3.5 | 5 | 262144 | 15495–15539 → 15549 | 714 (nạp cùng 3.8) / **810 → 820** (nạp một mình) | **+142** | 15962 / 16311 | ❌ tràn, và prefill tụt 26 % (§2) |
| 3.5 | 6 | 262144 | 15527 | **844** | **+166** | 15940 / 16311 | ❌ tràn (chỉ đo nạp) |

Mọi cấu hình nạp thành công (`model loaded`, 8,5–25,4 s). Dòng `compute buffer size` **không đo được**:
log llama-swap ở verbosity 3 không in dòng này (chỉ có `load_model`, `n_slots`, `model loaded`); bật `-lv`
là một thay đổi yaml khác nên không làm. VRAM dedicated/shared ở trên đã gồm compute buffer.

Khớp với "Đính chính 18/09" của `TRA_CUU_B_UB_18_09.md`: thêm slot không nhân KV (`-kvu`) nhưng vẫn tốn
thật — 3.8 np3→np4 +170 MiB dedicated **và** +242 MiB shared ở `-c 221184` (card 3090 chỉ còn ~445 MiB biên
ở np3), nên np4 cần hạ `-c` một nấc 16K (204800) mới sạch. 3.5 np3→np4 +42…150 MiB, còn vừa card 16 GB.

## 2. Tốc độ (ấm, n=3, trung vị)

| model · cấu hình | prefill 32K một mình | 1 luồng | N = np luồng: tổng / mỗi luồng (min) | mỗi luồng / 1 luồng | lặng max cạnh 32K (N−1 luồng nhỏ) | luồng nhỏ trong prefill | prefill 32K khi có người sinh |
|---|---|---|---|---|---|---|---|
| **3.8 np3 c221184** (nền) | 29,57 s · 1104 tok/s | 62,6 | 93,4 / 36,3 (31,6) | **58 %** | **0,75 s** | 4,2 tok/s | 36,2 s |
| 3.8 np4 c204800 | 29,95 s · 1096 | 64,6 | 106,8 / 31,1 (26,6) | **48 %** ❌ | 0,79 s (đợt 3: **35,57 s**, xem §5) | 4,5 | 36,9 s |
| **3.5 np3 c262144** (nền) | 16,10 s · 2040 | 75,4 | 147,8 / 50,7 (49,2) | **67 %** | **1,24 s** | 2,5 | 17,9 s |
| 3.5 np4 c262144 | 16,10 s · 2040 | 75,4 | **169,9** / 43,4 (41,8) | **57,5 %** ⚠️ | 1,22 s | 2,3 | 18,2 s |
| 3.5 np5 c262144 | **21,69 s · 1513** (−26 %) | 70,6 | 157,6 / 33,4 (30,7) | 47 % ❌ | 1,59 s (+28 %) | 1,8 | 24,5 s |

Ghi chú: 3.5 `-b 2048` nên lặng ~1,2 s (khớp 17/09: 1,22 s); 3.8 `-b 512` nên ~0,75 s (khớp bảo trì 18/09: 0,75 s).
Cột "luồng nhỏ trong prefill" là số chunk/giây của luồng đang sinh trong suốt prefill 32K (gần như đứng, như 17/09).
3.5 np5 tụt prefill 26 % và decode đơn 6 % — dấu hiệu tràn shared làm chậm âm thầm (đúng cảnh báo `TRA_CUU_B_UB`).

## 3. Đúng đắn (tiêu chí 3)

| phép | 3.8 | 3.5 |
|---|---|---|
| Canary cô lập (np4; 3.8 ở `-c 204800`): `tuan_tu_khong_lien_quan` + `dong_thoi` (4 luồng) + `dong_thoi_lru_27148` (nạp 5 > np, rồi 4 đồng thời), 5 vòng | **70 lượt, 0 rò**, 0 không đo được; 70/70 `stop`, 0 sai mã | **70 lượt, 0 rò**, 0 không đo được; 4 lượt `dong_thoi` không nêu đúng mã của mình (không chứa marker lạ — chất lượng 9B ở `reasoning_effort=low`, cùng kiểu 18/09: 51/54), 1 `tool_calls`, 1 `length` |
| #27572 — np luồng × ~16K khác nhau đồng thời | np3: 6/6 có content, acceptance 0,68–0,83; np4: 8/8, 0,62–0,87 | np3: 6/6 (mt 2600), np4: 8/8, np5: 10/10; acceptance 0,51–0,75 |
| Rỗng `finish=stop` trên **mọi** lượt của các phép đo | 0 / 51 | 0 / 92 |

Không có lượt nào `draft_n_accepted = 0` khi `draft_n > 0`. Build `91f6a6cf3` trên CUDA **không** tái hiện
#27572 ở np3/np4/np5 với công thức của issue (issue đo trên HIP, gfx1151, `-ub 256`; PR sửa #27705 còn mở).
Giới hạn: 2 đợt mỗi cấu hình, prompt 16K (issue dùng 19K, `-ub 256` ⇒ nhiều ubatch hơn ta).
Lượt 3.5 với `max_tokens` 1200 (lượt đầu, np3) ra 3/3 `length` với content rỗng — suy nghĩ ăn hết trần,
**không** phải chữ ký #27572 (acceptance khoẻ); đã chạy lại với 2600 như bảng.

## 4. Khuyến nghị theo model

### LTT-3.8 (3090): **giữ `-np 3 -c 221184`**
- np4 ở `-c 221184`: tràn shared +242 MiB ⇒ loại ngay (tiêu chí 1).
- np4 ở `-c 204800`: VRAM sạch, 0 rò, 0 rỗng, lặng 0,79 s (≤ +25 % của 0,75), prefill như cũ — nhưng mỗi
  luồng khi đủ 4 luồng chỉ còn **31,1 tok/s = 48 %** đơn luồng (tiêu chí ~60 % trượt 12 điểm), tổng chỉ
  +14 % (93→107), và mất 16.384 token ngữ cảnh. Không đáng đổi.
- np5: tràn +686 MiB ⇒ loại.

### LTT-3.5 (5060 Ti): **`-np 4 -c 262144` — đạt biên, đề xuất nếu chủ dự án chấp nhận 57,5 %**
Đạt: VRAM (+6 MiB shared), 0 rò / 70, 0 rỗng / 92, lặng 1,22 s (≤ 1,24 s), prefill 32K không đổi (16,10 s),
tổng **+15 %** (147,8 → 169,9 tok/s). Trượt: mỗi luồng khi **cả 4** slot cùng sinh = 43,4 tok/s = **57,5 %**
đơn luồng (dải 3 đợt 41,8–44,5 so với đơn 72,5–77,1 ⇒ tỉ lệ 54–61 %), dưới ngưỡng ~60 % 2,5 điểm.

Vì sao vẫn đề xuất: (1) thêm slot **không** làm chậm khi ≤ 3 luồng — cùng `-c`, decode mỗi bước chia theo số
luồng đang chạy chứ không theo số slot (đơn luồng np4 = np3 = 75,4; 17/09 cũng thấy vậy); 57,5 % chỉ xảy
ra khi đang có người thứ tư, (2) phương án thay thế cho người thứ tư ở np3 là **xếp hàng** — chờ một lượt
đang chạy xong (lượt 1024 token ở ~50 tok/s ≈ 20 s, p50 ra 1137 token theo phép 4 17/09) rồi mới nhận token
đầu, tệ hơn nhiều so với nhận ngay 43 tok/s, (3) 43,4 tok/s vẫn cao hơn đơn luồng của 3.8 hiện nay ở 3 luồng
(36,3). Nếu giữ tiêu chí 60 % cứng thì 3.5 **giữ np3**; không có cấu hình trung gian nào vì np5/np6 tràn.

Nếu chọn np4 cho 3.5, những chỗ phải đổi cùng lúc (phiên chính, không phải phiên đo): `llama-swap.yaml`
dòng `-np` của `qwen35-api` (cổng B `vat_ly.py` đọc từ đây — `/health` cho thấy `vat_ly.theo_model.qwen35-api.np`),
`apps/ltt_llm/ngan_sach.py` (số slot của máy A), và test đối chiếu yaml ↔ ngân sách nếu có.

## 5. Bất thường — phân tích

**3.8 np4 c204800, đợt 3 của phép lặng: một luồng "đứng" 35,57 s.** Không phải luồng đang sinh bị treo.
Ba luồng nhỏ bắt đầu cùng lúc ở t=0; ở 3.8, ba prompt ~1,3K cùng prefill cho TTFT 4,6–8,4 s (các đợt khác).
Ở đợt 3, luồng #1 **chưa xong prefill** khi prompt 32K vào ở t=8 s; nó nhận token đầu ở **t=43,9 s** — đúng
lúc prefill 32K xong (8 + 36,9 s). Tức là: một prompt **ngắn đang/đợi prefill** khi prompt dài đến thì chờ
**hết** prefill dài (TTFT ~44 s), trong khi luồng đã ở pha decode vẫn nhích ~4,5 tok/s (lặng ≤ 0,8 s). Khớp
cơ chế server ghi ở `TRA_CUU_B_UB_18_09.md` (mỗi vòng nhồi token prompt theo thứ tự slot tới đủ `n_batch`:
slot cá voi đứng trước thì chiếm cả lô 512 mỗi vòng, slot sau không được token prompt nào cho tới khi cá voi
xong). Hệ quả:
- **Không do np4** — np3 cũng có đường này; ở np3 hôm nay không lộ vì 2 luồng nhỏ đều prefill xong trước t=8 s
  (TTFT 4,6–6,5 s). Nhiều slot hơn ⇒ nhiều prompt ngắn cùng prefill hơn ⇒ **xác suất** va vào cá voi cao hơn.
- Con số trung vị 0,79 s là đúng cho "luồng đang sinh"; con số 35,6 s là **TTFT của người mới** cạnh cá voi.
  Đây là chỉ số khách thấy rõ hơn cả — nên đo riêng (người mới đến *trong* lúc cá voi prefill) ở lần sau; với
  cấu hình hiện hành nó ≈ toàn bộ thời gian prefill còn lại của cá voi (3.8: tới ~37 s cho 32K).
- Giảm thiểu nằm ở phía máy A (một cá voi prefill mỗi lúc, ngưỡng cá voi 3.8 > 8K — phương án C 17/09), không
  ở `-np`. `-b` không cứu được trường hợp này (nó chỉ chia lô, thứ tự slot giữ nguyên).

**Chỉ số "trước" trong phép lặng** (tok/s của luồng nhỏ 5 s trước prefill) thấp ở np4/np5 (1,5–6,7) vì phần lớn
luồng nhỏ còn đang trong TTFT lúc t=8 s — đừng đọc cột này như tốc độ nền; nó có trong JSON thô, không dùng để kết luận.

**Shared của 3.5 np5 phụ thuộc thứ tự nạp:** 714 MiB khi nạp cùng lúc với 3.8 (preload sau lưu yaml), 810–820
khi nạp một mình. Kết luận tràn không đổi (np5 tụt prefill 26 % ở lần đo có shared 820).

## 6. Không làm / hoãn

- **Ma trận `-b/-ub` (mục 4)**: bỏ theo chỉ đạo phiên chính (nhiều eval + gate đang chờ `c4_done.txt`). Hàng A
  (cấu hình đang chạy) có số ở §2 dòng "nền" — dùng làm đối chứng khi đo B/C/D sau.
- 3.8 np4 ở `-c 221184`: chỉ đo nạp (tràn ⇒ loại), không đo tốc độ; không thử `-c` trung gian 212992 (np4 đã trượt tiêu chí tốc độ ngay ở 204800).
- 3.5 np6, 3.8 np5: chỉ đo nạp.
- Task 12 (tham số lấy mẫu 3.5 theo model card): bỏ qua như chỉ dẫn.
- Chưa đo "TTFT người mới đến khi cá voi đang prefill" (§5).

## 7. Khôi phục (16:01–16:03)

- `apply` bản gốc (`goc_B.yaml`, chép byte từ B lúc 14:58) ⇒ SHA-256 yaml B = **`168e23c9b2b12395b937b624cd10a5c75b18ed1145a6bb8db6c269681e85dfca`**
  = bản sao lưu `.c4-20260918-145823` = `llm_gateway/deploy/llama-swap.yaml` trên `main`.
- `/running`: `qwen38-api` ready (`-c 221184 -np 3 -b 512 -ub 512`), `qwen35-api` ready (`-c 262144 -np 3`).
- Chat thật qua 8280: 3.8 `finish=stop` content `'4'`; 3.5 `finish=stop` content `'4'`.
- VRAM: 3.8 23993/578 MiB, 3.5 15365/672 MiB = mức nền đầu cửa sổ; 3090 24058, 5060 Ti 15766 MiB.
- Cổng B `/health` (token đọc trong script trên B, không in): HTTP 200, `trong_tai.ban=false`, RAM trống 80,4 GB,
  `vat_ly` 3.5 (262144, np 3) / 3.8 (221184, np 3).
- Dịch vụ: LTTLlamaSwap, LTTLlmGateway, LTTRenderGateway Running; LTTComfyUI Stopped (như đầu cửa sổ).
- Tunnel SSH của phiên đo đã đóng. Tệp tạm trên B: `E:\AI\ltt_dual\tmp_claude\c4\` (script + các yaml biến thể, không dùng bởi dịch vụ nào).
- Trong cửa sổ yaml B đã qua 5 lần lưu (v1 np4/np4, v3 3.8 np4 c204800 + 3.5 np5, v4 3.8 np5 + 3.5 np6, v5 np4/np4 c204800, gốc) — mỗi lần cả hai model nạp lại, cache RAM mất.
