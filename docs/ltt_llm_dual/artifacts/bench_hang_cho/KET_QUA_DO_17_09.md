# Kết quả đo máy B — cửa sổ bảo trì 17/09/2026

Cửa sổ: nhả 3.5 lúc 16:38, nhả 3.8 lúc 16:48, cả hai nạp lại lúc ~18:04 (3.5 vắng ~86 phút, 3.8 ~76 phút).
Engine `b10883-91f6a6cf3`, tham số production chép từ `/running` (có `-kvu`, MTP `--spec-draft-n-max 2`,
`--no-cache-idle-slots`, 3.5 KV q8_0 `-c 262144`, 3.8 KV q4_0 `-c 221184`). Mỗi cấu hình ghi đủ dòng lệnh,
build, n_ctx, VRAM nền trước nạp: `ket_qua_17_09/*/<phép>.jsonl` (sự kiện `nap`). Bảng sinh tự động đầy đủ:
`ket_qua_17_09/BANG_TU_DONG.md` (`tong_hop_17_09.py`). Không có lưu lượng khách từ 16:28:08 đến lúc khôi phục.

## 0. Cách đo — lạnh và ấm (đọc trước khi dùng số)

| lượt | thư mục | điều kiện | số là |
|---|---|---|---|
| **LẠNH** m1/m3/m5/m6/m2 | `ket_qua`, `ket_qua_35`, `ket_qua_38` | server mới nạp, **không** có lượt khởi động bỏ, **mỗi điểm 1 lần chạy** | cận trên / chỉ báo xu hướng |
| **ẤM** am35/am38 | `ket_qua_am35`, `ket_qua_am38` | 1 server production np3 (-b mặc định 2048) nạp một lần; 2 lượt khởi động (200 và 32k token) **bỏ**; mỗi điểm **trung vị [min–max] của 3 lần**; rồi 10 phút tải trộn 3 luồng; rồi đo lại | số dùng cho quyết định |
| đối chứng ctrl | `ket_qua_ctrl_co_lap`, `ket_qua_35`, `ket_qua_38` | np3, 3 lượt đơn 1k→512 + 1 prefill 32k; cô lập rồi song song | nhiễu chéo hai card |

- Thời gian nạp (`giay_nap`, 9,5–19,8 s) ghi riêng, **không** trộn vào tok/s/TTFT.
- Trong một cấu hình, mọi mức đồng thời/độ dài prompt dùng **cùng một server** (không nạp lại).
- Prompt có nonce đầu ⇒ không lượt nào trúng cache: TTFT = prefill đầy đủ (+ chờ hàng khi k > slot).
- Hai card đo **song song** từ 16:51 (theo yêu cầu chủ dự án). Nhiễu chéo đo được: **không đáng kể** (mục 5).

## 1. Bảng từng card

### RTX 5060 Ti — LTT-3.5 (9B Q6_K, KV q8_0)

| np | -c | dedicated / shared MiB (nạp → sau tải) | biên card MiB |
|---|---|---|---|
| 3 | 262144 | 15257/640 → 15375/678 | 641 → 523 |
| 4 | 262144 | 15407/644 → 15525/684 | 491 → 373 |
| 6 | 262144 | 15527/844 → 15549/**984** | 371 → 349 |

np6 đội shared +344 MiB so với np3 (mức nền 640) ⇒ dấu hiệu tràn sang RAM hệ thống; np4 biên còn 373 MiB.

**ẤM np3** (trung vị [min–max], n=3; tok/s decode server):

| đo | mới nạp + 2 lượt bỏ | sau 10 phút tải |
|---|---|---|
| k=1, prompt 1k: decode / TTFT | 54,7 [54,7–56,4] / 1,02 s | 53,0 [50,0–55,3] / 1,24 s |
| k=1, prompt 32k: decode / TTFT / prefill | 48,3 [46,9–57,9] / 19,7 s / 1612 | 47,1 / 20,9 s / 1559 |
| k=2 (1k+8k): tổng / mỗi luồng | 81,5 [78,7–82,8] / 41,0 | 78,5 / 38,6 |
| k=3 (1k+8k+32k): tổng / mỗi luồng (min–max) | 106,5 [102,6–112,7] / 31,1 (12,5–37,0) | 113,2 / 30,0 (13,5–39,9) |
| TTFT luồng 32k trong k=3 | 25,5 s | 25,1 s |

**LẠNH, 1 lần** (np3/np4/np6, tổng tok/s khi cả k luồng cùng decode; k > np là xếp hàng, cửa sổ chồng âm ⇒ "–"):

| k (prompt) | np3 | np4 | np6 |
|---|---|---|---|
| 1 (1k) decode / TTFT | 72,0 / 0,78 s | 68,9 / 0,84 | 67,0 / 0,64 |
| 1 (8k) | 69,5 / 4,0 s | 64,3 / 4,2 | 67,0 / 4,0 |
| 1 (32k) decode / TTFT / prefill | 54,9 / 17,4 s / 1852 | 54,6 / 17,8 / 1819 | 51,9 / 18,5 / 1745 |
| 2 tổng | 90,3 | 83,7 | 81,9 |
| 3 tổng (mỗi luồng) | 117,2 (13,9–39,4) | 87,5 (21–32) | 95,0 (10,5–32,1) |
| 4 tổng | xếp hàng | 123,5 (12,7–31,8) | 115,2 (9,5–29,1) |
| 6 tổng | xếp hàng | xếp hàng | 143,5 (5,8–26,0), TTFT 32k 65,8 s |

Kiểm rỗng: np3 6/6, np4 8/8, np6 12/12 có content, `finish=stop`. Cặp slot {0,2} không chậm hơn cặp khác
(54,3/56,5 vs 54,8/55,0 tok/s ở np3) ⇒ không tái hiện #25840.

### RTX 3090 — LTT-3.8 (27B UD-Q4_K_M, KV q4_0)

| np | -c | dedicated / shared MiB (nạp → sau tải) | biên card MiB |
|---|---|---|---|
| 3 | 221184 | 23971/568 → 24007/614 | 540 → 504 |
| 4 | 200704 | 23859/532 | 652 (không đo tải — xem mục 5) |
| 5 | 184320 | 23861/506 → 23895/556 | 650 → 616 |

**ẤM np3**:

| đo | mới nạp + 2 lượt bỏ | sau 10 phút tải |
|---|---|---|
| k=1, 1k: decode / TTFT | 48,5 [44,1–51,4] / 2,13 s | 43,3 [41,7–47,2] / 2,68 s |
| k=1, 32k: decode / TTFT / prefill | 42,4 [38,6–45,4] / 37,1 s / 862 | 46,4 / 38,4 s / 851 |
| k=2 tổng / mỗi luồng | 62,4 / 29,5 | 66,6 / 33,3 |
| k=3 tổng / mỗi luồng (min–max) | 84,7 [76,8–86,5] / 22,9 (7,4–28,3) | 82,6 / 26,2 (7,8–31,0) |
| TTFT luồng 32k trong k=3 | 49,0 s | 48,0 s |

**LẠNH, 1 lần** (m2): np3 k=1 61,9 / k=2 75,4 / k=3 86,5 tổng; np5 (-c 184320) k=1 56,8 / k=3 89,3 /
k=4 92,5 / k=5 114,9 tổng, nhưng mỗi luồng ở k≥4 chỉ 5,8–23,4 tok/s và TTFT lên 57–66 s. Cổng decode đơn:
np3 71,6, np5 75,0, np4 56,6 (<60 ⇒ bỏ qua, xem mục 5). Kiểm rỗng np3 3/3, np5 5/5 có content.

## 2. Câu hỏi chủ dự án — job 1 đang stream một mình, job 2 vào

Job 1: prompt 1k, `max_tokens` 8000; job 2 vào sau 15 s với prompt 1k hoặc 32k, `max_tokens` 500.
Cột job 1: tok/s **trước** | **trong** prefill job 2 (khoảng lặng dài nhất) | khi **cả hai** decode | **sau**.

| card · -b | job 2 | job 1 trước | trong prefill (lặng max) | cả hai decode | sau | job 2 TTFT | job 2 prefill | job 2 decode |
|---|---|---|---|---|---|---|---|---|
| 3.5 · 2048 ẤM n=3 | 1k | 55,1 | 3,5 (1,26 s) | 47,3 | 61,5 | 1,74 s | 1121 | 47,8 |
| 3.5 · 2048 ẤM n=3 | 32k | 73,0 | **2,1** (1,22 s) trong 17,8 s | 47,2 | 57,9 | **17,79 s** | 1817 | 46,2 |
| 3.5 · 2048 LẠNH | 32k | 67,5 | 2,6 (1,21 s) | 48,5 | 65,6 | 17,63 s | 1830 | 45,4 |
| 3.5 · **512** LẠNH | 1k | 75,1 | – (0,29 s) | 61,3 | 75,7 | 0,71 s | 1530 | 52,8 |
| 3.5 · **512** LẠNH | 32k | 69,0 | **7,2** (0,48 s) | 47,7 | 60,7 | **20,23 s** | 1597 | 46,1 |
| 3.8 · 2048 ẤM n=3 | 1k | 60,7 | 2,1 (2,17 s) | 38,1 | 59,0 | 3,09 s | 610 | 41,6 |
| 3.8 · 2048 ẤM n=3 | 32k | 59,8 | **1,5** (2,68 s) trong 34,6 s | 44,9 | 48,7 | **34,58 s** | 934 | 36,1 |
| 3.8 · 2048 LẠNH | 32k | 71,4 | 1,2 (2,23 s) | 33,7 | 60,5 | 31,80 s | 1010 | 35,4 |
| 3.8 · **512** LẠNH | 1k | 75,4 | 4,4 (0,51 s) | 41,2 | 74,0 | 1,43 s | 751 | 53,9 |
| 3.8 · **512** LẠNH | 32k | 63,5 | **5,3** (0,88 s) | 46,1 | 61,5 | **35,09 s** | 917 | 33,9 |

Prefill rất dài chèn vào hai luồng đang decode (LẠNH, 1 lần; tổng tok/s 2 luồng):

| card | prompt | -b 2048: trước → trong → sau · lặng max · giây prefill | -b 512 |
|---|---|---|---|
| 3.5 | 32k | 84,3 → 5,0 → 91,1 · 1,20 s · 17,6 s | 88,9 → 12,3 → 95,9 · 0,55 s · 20,4 s |
| 3.5 | 163k | 97,8 → 1,9 → 55,8 · 2,56 s · **133 s** | 74,7 → 8,0 → 43,3 · 1,10 s · 154 s |
| 3.8 | 32k | 64,0 → 3,2 → 79,7 · 2,21 s · 31,4 s | 69,4 → 7,7 → 69,2 · 0,95 s · 35,2 s |
| 3.8 | 128k | 68,0 → 2,0 → 57,3 · 3,91 s · **176 s** | 71,6 → 7,0 → 69,5 · 1,41 s · 196 s |

**Trả lời:** prompt ngắn gần như không làm job 1 khựng (TTFT job 2 ≤ 3 s). Prompt 32k làm job 1 **gần như
đứng** (1,5–2,6 tok/s, tức ~3 % tốc độ) trong **suốt** prefill job 2 — 17,8 s trên 5060 Ti, 34,6 s trên 3090 — rồi
cả hai chạy ~45–47 tok/s (3.5) / ~34–45 (3.8), sau đó job 1 hồi về 58–60. `-b 512` nâng tốc độ job 1 trong prefill
lên ~3× (7,2 / 5,3 tok/s) và cắt khoảng lặng dài nhất xuống < 1 s, đổi lại TTFT của prompt dài chậm hơn 10–15 %
(3.5: 17,6→20,2 s; 3.8: 31,8→35,1 s; 128k: 176→196 s). Số -b 512 là 1 lần chạy lạnh — hướng rõ, biên độ chưa chắc.

## 3. Tràn KV (m5) và cache (m6)

**m5 — tràn có ý** (3.5, `-c 16384 -np 3 -kvu`): đối chứng 3×(1k+1,5k)=7,5k token: 3/3 xong. Tràn 3×(3k+4k)=21k:
server log `failed to find free space in the KV cache, retrying with smaller batch size` (n_batch 1024→16), rồi
**2/3 luồng nhận lỗi giữa stream** sau 2359 và 2448 token: `500 got exception: speculative batch index 6 is not
inside the current sub-batch [0, 4)`; luồng thứ 3 xong đủ 4000 token. Server **không chết** (`/health` ok, lượt mới
sau đó chạy 79 tok/s). ⇒ b10883 không giết hết slot, nhưng tràn = **khách đang stream nhận lỗi sau khi đã trả
200**. Đường lỗi đi qua MTP (upstream gần giống: ggml-org/llama.cpp#24840 — offset batch_view không truyền sang
ctx_dft; chưa xác nhận là cùng lỗi).

**m6 — tỷ lệ trúng prompt cache**: 6 hội thoại (system chung 3k + tài liệu riêng 2k, 5 lượt) + 5 lượt lạ 4k, 3 thợ.
`--cache-ram` mặc định: **0/30 lượt có `cache_n` > 0**, `prompt_tokens_cached` = 0, TTFT p50 3,27 s.
`--cache-ram 0`: 0/30, TTFT p50 4,94 s (khác biệt là thứ tự hàng đợi, không phải cache — cả hai đều prefill đủ
151.570 token). Log cho thấy server **chọn đúng slot theo LCP** (f_sim ≈ 0,59) nhưng vẫn xử lý lại toàn bộ ~4.970
token, không có dòng context checkpoint nào. Qwen3.5 là model lai (Gated DeltaNet): trạng thái hồi quy không cắt
lùi được về tiền tố nếu không có checkpoint (upstream: #28194, #28276). ⇒ **Hiện tại cache tiền tố không mua gì
cho LTT-3.5** ở dạng hội thoại này; `--cache-ram` không đổi kết quả.

## 4. Khuyến nghị phương án C

Dữ liệu đầu vào: pool KV (3.5: 262.144; 3.8: 221.184 token, unified), phép 4 (token ra p50/p95/p99: 3.5
1137/6815/13502, 3.8 1488/6000/11605; token vào p50/p95/p99: 3.5 2947/20057/44635, 3.8 3115/6411/52408;
chạm `length` 2,8–2,9 %), m5, mục 2.

| tham số | LTT-3.5 (5060 Ti) | LTT-3.8 (3090) | lý do |
|---|---|---|---|
| ngân sách token | **254.000** (262.144 − 8.192) | **213.000** (221.184 − 8.192) | m5: tràn ⇒ lỗi giữa stream, không có đường lùi ⇒ không bao giờ để tổng giữ chỗ chạm pool; biên 8.192 phủ nháp MTP (2/slot), ước lệch token (`LE` 2.048) và khuôn chat |
| trần chuỗi / `-np` | **3** | **3** | np4/np6 (3.5) và np5 (3.8) tăng tổng 5–33 % nhưng mỗi luồng rơi 6–23 tok/s, TTFT 32k lên 57–66 s; np6 3.5 đội shared +344 MiB. Đồng thời thật do cổng token + hàng đợi quyết, không do thêm slot |
| `-c` | giữ 262.144 | giữ 221.184 | biên VRAM 504–523 MiB sau tải, không tràn; hạ -c không đổi decode đơn |
| giữ chỗ mỗi lượt | prompt ước + `max_tokens` (mặc định 32.768) | như bên trái | 3 lượt p99 vào + 32.768 ra = 3.5: 232k ≤ 254k; 3.8 khi 3 lượt p95: 117k ≤ 213k ⇒ giữ đủ `max_tokens` không làm mất slot trong ~99 % lượt; không cần đoán p99 ra (13,5k / 11,6k) — hoàn giữ chỗ theo token thật khi xong |
| ngưỡng cá voi | prompt **> 16k** | prompt **> 8k** | prefill chặn luồng khác ~1 s/1,8k token (3.5) và ~1 s/0,9k token (3.8); 16k ≈ 9 s và 8k ≈ 9 s lặng cho người đang stream. Chỉ **1 cá voi prefill mỗi lúc**; cá voi xếp sau khi nó vừa ngân sách. 3.5 p95 vào 20k, 3.8 p95 6,4k ⇒ ~5 % lượt vào làn cá voi |
| trần prompt cá voi 3.8 | — | cân nhắc ≤ ~128k | 128k prefill 176–196 s; upstream #27623 (decode sập > ~80K vị trí) và #27756 (EOS im lặng > ~130k) cho Qwen3.8-27B — chưa đo ở đây |
| `-b / -ub` | **512 / 512** | **512 / 512** | mục 2: người đang stream giữ 5–12 tok/s thay vì 1–5, lặng max < 1,5 s thay vì 2–4 s; đổi lấy TTFT prompt dài +10–15 %. Cần một lượt ấm n=3 xác nhận trước khi đổi production |

## 5. Khôi phục, bất thường, chưa đo

**Bằng chứng khôi phục (18:04–18:07, máy B):**
- `/running`: `qwen35-api ready :8281` (busy 0, n_ctx 262144), `qwen38-api ready :8282` (busy 0, n_ctx 221184).
- Chat thật qua 8280: 3.8 `finish=stop token_ra=104 content_rong=False`; 3.5 `finish=stop token_ra=1867 content_rong=False`.
- dedicated/shared: 3.8 23971/568 MiB; 3.5 15257/640 MiB = mức nạp đo trong cửa sổ ⇒ không tràn.
- nvidia-smi 5 mẫu: 3090 24058 MiB 0 %, 5060 Ti 15778 MiB 0 %. **Nền production 3090 (3.8 nạp, ComfyUI tắt) = 24058 MiB, biên 518 MiB** (trước cửa sổ 24273 với ComfyUI chạy).
- Dịch vụ: LTTLlamaSwap, LTTLlmGateway, LTTRenderGateway Running (RenderGateway `/live` 200); LTTComfyUI Stopped (cố ý).
- Không còn task `LTT_BenchHangCho*`, không `pythonw` do_b, chỉ llama-server 8281/8282.

**Thay đổi trên máy B về ComfyUI (chủ dự án duyệt, để sửa `render_gateway/deploy/cai_dat_dich_vu.ps1:134` cho khớp):**
1. `sc config LTTComfyUI start= demand` — StartType Automatic → **Manual** (`DEMAND_START`).
2. Thử khi 3090 trống: `sc start` chạy được trên Manual (stub `E:\AI\venv\Scripts\python.exe` PID 9244 sinh
   ComfyUI thật `Python312\python.exe` PID 2776, VRAM 3090 +224 MiB); `Stop-Service` ⇒ không còn tiến trình
   ComfyUI, VRAM về 66 MiB nền. LTTRenderGateway **không** phụ thuộc LTTComfyUI trên máy này (`DEPENDENCIES` trống)
   ⇒ không gặp 1051.
3. `khoi_phuc` không bật lại ComfyUI (residency `llm`); để trọng tài bật ở trạng thái `anh`.
Khác trên máy B: thư mục kết quả dưới `E:\AI\ltt_dual\bench_hang_cho\ket_qua*`, script theo dõi tạm `E:\AI\ltt_dual\tmp_claude\`.
Không đổi cấu hình llama-swap, không restart dịch vụ LLM, không đụng công tắc khách.

**Bất thường:**
- **Ấm chậm hơn lạnh**: decode đơn 1k 3.5 72→55, 3.8 62→48 tok/s; prefill 1k 3.8 914→~650 tok/s. Không do card kia
  (am38 lap0/1 chậm khi 5060 Ti util 0 %). Giả thuyết khớp dữ liệu, **chưa cô lập**: với `-kvu`, ngữ cảnh 32k còn
  nằm trong slot rảnh (lượt khởi động, lượt 32k) làm attention quét nhiều ô hơn; lượt lạnh m1 chạy sau `cap_slot`
  đã ghi đè cả 3 slot bằng ngữ cảnh ~1,5k. Production luôn có slot rảnh giữ ngữ cảnh ⇒ **dùng số ẤM**.
  Hệ quả đáng đo: bỏ `--no-cache-idle-slots` (nhả slot rảnh) — cache không trúng (m6) nên có thể không mất gì.
- 10 phút tải trộn: 3.5 53 lượt/46.379 token, 52 lượt content rỗng; 3.8 46 lượt/24.472 token, 17 rỗng; 0 lỗi.
  Rỗng vì `max_tokens` 200–1500 bị suy nghĩ ăn hết (production mặc định 32.768) — hiện vật của phép đo.
- `dot_dong_thoi` với k > np: cửa sổ chồng âm ⇒ tổng "–" (dùng `tok_s_tong_ca_dot` trong jsonl).
- Máy A 16:27:50 job-worker tái tạo 8 tiến trình con; từ 16:28:08 không còn POST nào tới máy B.

**Nhiễu chéo hai card (song song):** prefill 32k 3.5 1990 vs 1999 tok/s cô lập, 3.8 1092 vs 1095; decode đơn
trung vị 81,5 vs 70,7 (3.5), 59,9 vs 58,7 (3.8) — trong nhiễu MTP. CPU máy B p50 14,5–16,8 %, max 31,9 %; RAM trống
tối thiểu 73,2 GB / 192 GB. ⇒ Không có nhiễu đo được.

**Chưa đo / lý do:**
- m2 np4 (-c 200704): cổng decode đơn trả trung vị 56,6 < 60 (3 mẫu 60,1/56,6/54,1) ⇒ script bỏ qua; decode đơn 3.8
  dao động 44–78 tok/s do MTP nên cổng 3 mẫu này nhiễu — np4 chưa có số tải.
- m1 np4/np6 và m2 không có lượt ấm n=3; -b 512 không có lượt ấm (chỉ lạnh, 1 lần).
- m3 163k/128k: 1 lần. Tràn KV chỉ đo ở 3.5.
- Tỷ lệ trúng cache với checkpoint ngữ cảnh / hội thoại giữ nguyên suy nghĩ: chưa đo.
- Nguồn lưu lượng 15:50–16:28 theo khoá/khách: không đọc được log server/CSDL production (bị chặn quyền).
