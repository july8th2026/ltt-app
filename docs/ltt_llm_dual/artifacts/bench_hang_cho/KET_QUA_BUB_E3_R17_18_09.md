# Kết quả lane B tối 18/09 — `-b`/`-ub`, E3 (MTP và 3.8 trả rỗng), R-17 (`preserve_reasoning` nhiều lượt)

Máy B không có khách (chủ dự án xác nhận). Đo thẳng llama-swap `127.0.0.1:8280` qua đường hầm SSH (`18381`).
Dữ liệu + script: `bub_e3_r17_18_09/` (`ket_qua/*.jsonl`, `*.stdout.txt`). Production gốc: `llama-swap.yaml`
SHA `86CB1EC9…` (3.5 `-np 4 -c 262144`, b mặc định 2048/ub 512; 3.8 `-np 3 -c 221184 -b 512 -ub 512`), mọi thay
đổi có bản lưu `llama-swap.yaml.laneb-<giờ>` trên B, cuối cùng khôi phục đúng SHA gốc (§4).

**Tóm tắt khuyến nghị (chỉ đề xuất, chưa đổi production):**

| Việc | Khuyến nghị |
|---|---|
| 3.8 `-b/-ub` | **giữ `-b 512 -ub 512`** (đang chạy) |
| 3.5 `-b/-ub` | **chuyển `-b 1024`** (ub giữ 512); `-b 512` nếu ưu tiên tuyệt đối người dùng nhỏ khi có prefill dài |
| `-ub 1024` (hàng D) | **bỏ** ở cả hai model — tràn shared +904 / +1.030 MiB |
| MTP và 3.8 rỗng | **không quy được cho MTP**: 0/96 rỗng ở cả hai nhánh (MTP bật np3 và tắt np1) — giữ MTP, không đổi cờ |
| R-17 `preserve_reasoning` | **giữ `true`** (mặc định template = production); `false` không thắng, chậm hơn |

## 1. Ma trận `-b`/`-ub` (ấm, 3 đợt, trung vị; `TRA_CUU_B_UB_18_09.md`)

Mỗi hàng: lưu yaml (cả hai model nạp lại), unload model kia, đo từng model riêng. "Lặng max" = khoảng lặng dài nhất
của luồng nhỏ khi một request 32K đang prefill; "nhỏ trong prefill" = tok/s của luồng nhỏ trong lúc đó.

### LTT-3.8 (3090, np 3)

| hàng | cấu hình | prefill 32K một mình | 1 luồng tok/s | tổng 3 luồng | lặng max | nhỏ trong prefill (trước) | prefill 32K khi có người sinh |
|---|---|---:|---:|---:|---:|---:|---:|
| A | b512/ub512 (đang chạy) | 29,83 s | 63,1 | 96,5 | **0,77 s** | **4,2** (23,4) | 36,2 s |
| B | b1024/ub512 | 29,47 s | 64,4 | 97,6 | 1,14 s | 2,5 (26,1) | 33,4 s |
| C | b2048/ub512 | 29,53 s | 62,2 | 108,7 | 2,25 s | 1,4 (24,1) | 32,4 s |

- Prefill một mình ngang nhau (±1 %) — xác nhận suy luận của tra cứu: `-b` không đổi tốc độ prefill đơn.
- `-b` chỉ đổi phân chia công bằng: b512 lặng 0,77 s và luồng nhỏ giữ 4,2 tok/s; b2048 lặng 2,25 s, còn 1,4 tok/s.
  Giá: request 32K chậm thêm ~3,8 s (+12 %) khi có người khác đang sinh.
- Tổng 3 luồng dao động theo độ dài đầu ra (3.8 dừng `stop` ở độ dài khác nhau: 2.026–3.072 token/đợt) — không
  dùng để quyết. VRAM: 23.971–24.005 MiB dedicated, shared 568–614 MiB ở cả ba hàng (không khác biệt).

### LTT-3.5 (5060 Ti, np 4)

| hàng | cấu hình | prefill 32K một mình | 1 luồng tok/s | tổng 4 luồng | lặng max | nhỏ trong prefill (trước) | prefill 32K khi có người sinh |
|---|---|---:|---:|---:|---:|---:|---:|
| A | b2048/ub512 (đang chạy) | 16,17 s | 73,2 | 165,5 | 1,23 s | 2,4 (43,2) | 18,3 s |
| B | b1024/ub512 | 16,10 s | 75,9 | 158,7 | 0,67 s | 4,1 (44,4) | 19,1 s |
| C | b512/ub512 | 16,46 s | 74,7 | 150,1 | **0,47 s** | **7,1** (39,1) | 21,1 s |

- Prefill một mình: b512 chậm 1,8 %, b1024 ngang.
- Công bằng: b1024 giảm lặng 1,23 → 0,67 s và nâng luồng nhỏ 2,4 → 4,1 tok/s với giá prefill-có-tải +4 %;
  b512 tới 0,47 s / 7,1 tok/s nhưng request 32K chậm +15 % (18,3 → 21,1 s).
- Tổng 4 luồng giảm đơn điệu theo `-b` (165 → 159 → 150; đợt: A 161–170, B 158–164, C 149–158), mà đầu ra cố định
  4.096 token và phép này không có prefill dài ⇒ **chưa giải thích được** (có thể nhiễu thứ tự đo/nhiệt; không có cơ
  chế trong mã). Đây là lý do chọn b1024 (−4 %, trong vùng nhiễu) thay vì b512 (−9 %).
- VRAM: 15.515–15.525 MiB dedicated, shared 652–684 MiB ở cả ba hàng.
- Không lượt rỗng nào trong ma trận (3.8 0/20 mỗi hàng, 3.5 0/23).

### Hàng D — b1024/ub1024 (chỉ nạp + VRAM), `ket_qua/D_nap.txt`

| model | nền (production, cả hai nạp) dedicated / shared | D dedicated / shared | shared tăng | kết luận |
|---|---|---|---:|---|
| 3.8 | 23.971 / 568 MiB | 24.121 / 1.472 MiB | **+904 MiB** | **bỏ** (> 100 MiB) |
| 3.5 | 15.407 / 644 MiB | 15.535 / 1.674 MiB | **+1.030 MiB** | **bỏ** (> 100 MiB) |

Cả hai nạp được (không OOM — Windows tràn sang shared đúng như tra cứu dự báo), card đã đầy (3090 24.184/24.576,
5060 Ti 15.920/16.311 MiB). Log llama-swap không in `compute buffer size` ở mức log hiện tại ⇒ không đọc được kích
thước buffer, chỉ có VRAM tiến trình.

## 2. E3 — MTP có gây 3.8 trả rỗng?

Nhánh ON = production (np 3, `draft-mtp` n-max 2), đo lúc 19:36–20:00 (cùng lúc R-17 chạy trên 5060 Ti — card khác).
Nhánh OFF = vE3.yaml: 3.8 `-np 1`, bỏ dòng `--spec-type` (3.5 giữ nguyên), đo 21:08–21:34. Cùng bộ đề ở cả hai:
`tools/cong_mtp.py --song-song 2 --lan 3` (48 lượt, bản trên `main`) + `e3_kim.py` (48 lượt bài W5 ~54K–68K token:
ctx-10 × 30 nguyên văn trúng cache tiền tố — đúng điều kiện lượt rỗng gốc, ctx-10 × 8 lạnh có nonce đầu,
ctx-50 × 5, ctx-90 × 5; trộn hạt 1809, song song 2, `max_tokens` 1.400). Tổng hợp: `ket_qua/e3_tom.json` (`tom_e3.py`).

| nhánh | cổng `cong_mtp` | cổng chấm đúng | kim: finish | kim: rỗng `stop` | kim: đúng mã kim | tổng rỗng `stop` | Wilson 95 % |
|---|---|---:|---|---:|---:|---:|---|
| ON (np 3 + MTP) | đạt, 48 ok | 35/36 | 48 `stop` | 0/48 | 48/48 | **0/96** | 0–3,8 % |
| OFF (np 1, không MTP) | đạt, 48 ok | 36/36 | 48 `stop` | 0/48 | 48/48 | **0/96** | 0–3,8 % |

Fisher chính xác ON vs OFF: p = 1,0. Lượt sai duy nhất của ON là `vi-01` lần 2 (bài W2 tiếng Việt, có nội dung —
không rỗng). Phụ: chấp nhận nháp MTP trung bình 0,79 trong nhánh ON; lượt trúng cache p50 8,7 s (ON) vs 11,3 s (OFF);
lượt lạnh p50 138 s (ON, 2 prefill 54K song song trên 3 slot) vs 78 s (OFF, xếp hàng 1 slot) — không so tốc độ vì
khác `-np` và tải nền.

**Kết luận:** lượt rỗng 1/48 của `cong_mtp` sáng 18/09 **không tái hiện** trong 96 lượt ON (38 lượt ctx-10 đúng điều
kiện cũ) và cũng không có ở OFF ⇒ không có bằng chứng MTP (hay np 3) gây rỗng; tần suất thật, nếu có, dưới ~4 %/lượt
ở mức tin cậy 95 % với mỗi nhánh. **Không tắt MTP.** Lớp bảo vệ đúng vẫn là phát hiện "200 + content rỗng" ở cổng
(L-16 / memory `model-nha-tren-may-b`), không phải đổi cờ engine. Giới hạn: ON và OFF khác cả MTP lẫn `-np`
(đúng định nghĩa E3 của `cong_mtp.py`), nên nếu sau này thấy rỗng lại chỉ ở ON thì cần nhánh thứ ba (np 3, không MTP).

## 3. R-17 — `preserve_reasoning` trên hội thoại nhiều tin user (LTT-3.5)

Bộ `ab_nhieu_luot_35.py`: 8 hội thoại (4 lập trình chạy thật, 4 tiếng Việt), 4–5 tin user nối tiếp, 3 lần, hai biến
thể theo request (không nạp lại model). A = mặc định template (`preserve_reasoning=true`, = production);
B = `chat_template_kwargs.preserve_reasoning=false`. **Đủ dữ liệu**: 210/210 lượt (35 lượt × 3 lần × 2 biến thể).

| | A (true, production) | B (false) |
|---|---:|---:|
| lượt đúng (cặp 105) | **89** | 85 |
| chỉ biến thể này đúng | 11 | 7 |
| nhóm code / tiếng Việt | 33/48 · 56/57 | 31/48 · 54/57 |
| hội thoại đúng hết | **16/24** | 14/24 |
| rỗng / lặp / `length` | 0 / 0 / 0 | 0 / 0 / 0 |
| token prompt cộng (tổng / mới phải prefill) | 202.455 / 45.799 | 62.313 / 32.501 |
| tỉ lệ trúng cache từ lượt 2 | 0,788 | 0,508 |
| token ra p50 | 773 | 1.147 |
| giây p50 / cộng | **16,0 / 2.350** | 21,9 / 3.321 |

McNemar chính xác p = 0,48 ⇒ `B_thang_ro = false`, `B_khong_tut = true` (không khác biệt có ý nghĩa về đúng/sai).
Nhưng B **chậm hơn 41 %** tổng thời gian: bỏ suy nghĩ cũ làm lịch sử ngắn (prompt ít hơn 3×) nhưng phá tiền tố cache
(0,79 → 0,51) và model phải nghĩ lại dài hơn (token ra p50 +48 %). **Quyết: giữ `preserve_reasoning=true`**
(không đổi gì — đó là mặc định). Chi phí thật của A là ngữ cảnh phình nhanh hơn (prompt lượt cuối p50 3.077 vs 522
token) — chỉ đáng xem lại khi hội thoại chạm trần ngữ cảnh.

## 4. Khôi phục B

- Bản lưu trước mỗi thay đổi (trên B): `llama-swap.yaml.laneb-20260918-200723` (trước B), `-202126` (trước C),
  `-210618` (trước D, SHA 86CB1EC9…), `-210732` (trước E3), `-213423` (trước khôi phục). Lượt trước bị ngắt để lại
  yaml thử; phiên chính đã khôi phục 21:05, lane B tiếp tục từ đó.
- 21:34:23 áp lại `goc_86CB.yaml` ⇒ SHA **`86cb1ec93fc48b27aef9bad96f25c00c24ae0c7386572422b640f6b93a935d67`** (khớp).
- `/running`: `qwen35-api` ready np 4 (MTP), `qwen38-api` ready np 3 `-b 512 -ub 512` (MTP). VRAM trở về đúng nền:
  3.8 23.971/568 MiB, 3.5 15.407/644 MiB (dedicated/shared).
- Cả hai model trả lời (`finish=stop`, "Paris"); gateway `/health` = **200** (token đọc trong lệnh trên B, không in).
  Dịch vụ LTTLlamaSwap, LTTLlmGateway, LTTRenderGateway Running.
