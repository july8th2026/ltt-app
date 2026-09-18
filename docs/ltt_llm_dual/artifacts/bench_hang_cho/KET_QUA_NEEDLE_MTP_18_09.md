# Kiểm định kỳ 18/09/2026 — needle 100–200K (LTT-3.8, #27756) · cổng MTP · TTFT/nạp nguội (R-16)

Plan v2 Task 10 (Step 3 + phần needle) và R-16. Không đổi cờ, không nạp lại model, không deploy. Đường vào:
`ssh -L 18290:127.0.0.1:8280` → llama-swap trên máy B (không qua 8299, không tốn credit). Trước mỗi khúc đếm kết nối
khách vào 8299 (ngoài loopback) — có khách thì chờ (chờ 4 đợt: ≤ 30 s, 30 s, 5 phút trước độ sâu 200K, 1 phút). Chốt chặn chỉ ở
ĐẦU mỗi khúc: bộ A/B 3.5 (§ tệp SAMPLING) chạy liền 100 phút với 2/3 slot — khách đến giữa chừng vẫn còn 1 slot.
Chạy 16:05–17:58, sau khi phiên C4 trả B
về yaml gốc. `llama-swap.yaml` trên B = kho, SHA-256 `168E23C9…5DFCA` (kiểm trước và sau).

Thô: `kiem_dinh_ky_18_09/` — `kim_38.jsonl`, `kim_38_repro_27756.json`, `cong_mtp_qwen35.jsonl`, `cong_mtp_qwen38.jsonl`,
`*.stdout.txt`. Chỉ dữ liệu tổng hợp.

## 1. Needle 100–200K trên LTT-3.8 — **8/8 độ sâu đạt, 4/4 sự kiện mỗi độ sâu; repro gốc #27756 ĐẠT**

Nguồn (GitHub MCP): ggml-org/llama.cpp **#27756** (mở, chưa có PR sửa) — Qwen3.8-27B (64 lớp = 48 Gated DeltaNet +
16 full attention) phát **EOS ngay token đầu** (`tokens_predicted=1`, content rỗng) khi prompt ~100–130K+; CUDA và CPU
như nhau; vLLM cùng trọng số thì đạt ⇒ lỗi engine. Bình luận 07/09: **không có ngưỡng sạch** — "lỗ" không đơn điệu
(96.519 hỏng giữa 95.979 và 99.003 đạt), tất định theo số token; người báo khuyên *kiểm đúng các độ sâu phục vụ*.
Bản người báo: `ee4c505` → `539f245` (26/08). Máy B: `91f6a6cf3`.

Công cụ `tools/kim_ngu_canh_dai.py` (test_1450): đúng đề của issue (hai ghi chú đầu/giữa, 4 sự kiện), số token đo bằng
`/tokenize` của engine (27,000 token/đoạn), mỗi độ sâu một muối + `cache_prompt:false` (`cache_n` = 0 mọi lượt ⇒ không
nhiễm cache tiền tố). Đường chat của khách: template v22.5, suy nghĩ `xhigh`, budget 4096.

| đích | prompt_n | kết quả | sự kiện | token ra | giây | prefill tok/s |
|---:|---:|---|:-:|---:|---:|---:|
| 100.000 | 100.021 | đạt | 4/4 | 195 | 124,9 | 835 |
| 115.000 | 115.033 | đạt | 4/4 | 295 | 155,3 | 788 |
| 130.000 | 130.018 | đạt | 4/4 | 255 | 183,2 | 749 |
| 145.000 | 145.030 | đạt | 4/4 | 195 | 210,9 | 713 |
| 160.000 | 160.015 | đạt | 4/4 | 208 | 243,4 | 683 |
| 175.000 | 175.026 | đạt | 4/4 | 306 | 280,4 | 653 |
| **186.368** (= `tran_vao_cua("qwen38-api")`) | 186.394 | đạt | 4/4 | 189 | 304,7 | 632 |
| 200.000 (trên trần khách, dưới `-c` 221.184) | 200.029 | đạt | 4/4 | 253 | 390,7 | 544 |
| **repro gốc #27756** (raw `/completion`, greedy, `n_predict` 250) | **129.864** (trùng số của issue) | **đạt** — `tokens_predicted` 202, `stop_type` eos sau khi trả lời | 4/4 | 202 | 260,0 | |

Đọc kết luận đúng phạm vi:
- Trên `91f6a6cf3` + quant của B, dấu vân tay #27756 **không** xuất hiện ở 9 độ sâu này, kể cả đúng prompt 129.864 token mà
  issue báo hỏng 3/3 trên CUDA. Không chứng minh không có "lỗ" ở độ sâu khác (issue: lỗ không đơn điệu, rộng ~100 token).
  9 điểm thưa trên 100–200K; một khách có thể rơi đúng lỗ ⇒ giữ phép này trong lịch chạy lại (RUNBOOK §4b).
- Chi phí thật của ngữ cảnh dài: prefill 186K = **305 s** trên 3090 (632 tok/s) — trên trần 100 s của Cloudflare với cửa đồng
  bộ; stream có nhịp tim nên sống. Không phải lỗi, ghi để đối chiếu TTFT (§3).

## 2. `cong_mtp.py` — một lượt, KHÔNG đối chứng E3

E3 (np 1, không MTP) cần đổi cờ engine ⇒ **không chạy** (plan Task 10 Step 3). Hệ quả: phân loại `hong_noi_dung` theo đối
chứng không áp dụng — chỉ bắt hỏng hình thức (� / vòng lặp / JSON sai), rỗng, deadlock, rò slot. `--song-song 2 --lan 3`,
48 lượt/model, cấu hình production (np 3, `-kvu`, `draft-mtp` n-max 2).

| model | cổng | ok | rỗng có giải thích (`length` khi nghĩ) | **rỗng không giải thích** | hỏng hình thức | deadlock | rò slot | chấm đúng W2/W3/W4/W5 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| LTT-3.5 | **đạt** | 33 | 15 | 0 | 0 | 0 | 0 | 11/18 · 3/3 · 6/6 · 9/9 |
| LTT-3.8 | **trượt** | 47 | 0 | **1** | 0 | 0 | 0 | 16/18 · 3/3 · 6/6 · 8/9 |

- **3.8 trượt vì 1 lượt**: `ctx-10` lượt 2 (W5, ~54K token, kim ở 10 %) — HTTP 200, `finish=stop`, `content` rỗng,
  `reasoning` 520 ký tự, 9,2 s. Hai lượt khác của cùng bài đạt. Đây đúng là mẫu "rỗng mà cổng báo thành công" (memory
  `model-nha-tren-may-b`; L-16) — **không** phải dấu vân tay #27756 (có suy nghĩ, không phải token đầu là EOS). Không có E3
  nên **không quy được cho MTP**. 1/48 = 2,1 % (Wilson 95 %: 0,4–10,9 %). Đề xuất: không đổi cờ; khi có cửa sổ bảo trì thì
  chạy E3 (np 1, không MTP) đúng bộ đề để tách MTP/np khỏi model.
- **3.5 — 15 "rỗng có giải thích"**: mọi lượt `finish=length` khi còn đang nghĩ, vì bộ đề cổng cấp `max_tokens` 1.400/1.500
  < budget suy nghĩ 2.048 của 3.5. Đúng kết luận R-20 ("MTP trả rỗng" thực ra là hết `max_tokens`) và sàn 2.560 của L-26.
  7 bài W2 chưa chấm được vì thế (11/18). Không phải lỗi engine.

## 3. R-16 — TTFT p95 và nạp nguội từ sổ lượt B (chỉ đo, chưa đặt ngưỡng)

Công cụ `tools/tong_hop_ttft_b.py` (test_1452). Nguồn: `H:\LTT_LLM\logs\gateway_err-20260917T160354.001.log` +
`gateway_err.log` (logger `llm_gateway.so`, một dòng/lượt, `llm_gateway/so_luot.py::ghi_so`), `llamaswap*.log`. TTL đọc
từ yaml: **1800 s**. Khoảng sổ: 12/09 19:56 → 18/09 14:30 (giờ B). Cửa đồng bộ đo **cả lượt** (`api.py`) nên tách riêng.

| model / cửa | lượt | 200 có TTFT | p50 (s) | **p95 (s)** | p99 (s) | max (s) | nạp nguội suy từ sổ | mã khác 200 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 3.8 stream | 2.022 | 2.021 | 2,92 | **32,86** | 33,47 | 47,86 | 18 | — |
| 3.5 stream | 1.024 | 1.023 | 2,39 | **31,94** | 34,06 | 43,75 | 10 | — |
| 3.8 đồng bộ (= cả lượt) | 3.047 | 2.946 | 35,45 | 173,0 | 315,6 | 591,6 | 16 | 429 ×88, 413 ×9, 499 ×2, 502, 504 |
| 3.5 đồng bộ (= cả lượt) | 3.812 | 3.626 | 17,94 | 119,1 | 256,5 | 584,7 | 19 | 429 ×143, 504 ×39, 400 ×4 |

`llamaswap*.log`: **27** lần 3.8 và **32** lần 3.5 bị nhả vì TTL 1800 s (log không có giờ ⇒ chỉ đếm).

Điều số này nói (và không nói):
- **p95 stream ~32–33 s không phải nạp nguội**: phân bố stream có một cụm rõ ở 30–35 s (432/3.044 lượt stream có TTFT), gần như toàn bộ
  `giao_thuc=messages`, tập trung 15–16/09 (253 + 193 lượt). TTFT "ấm" p95 (bỏ lượt nguội) = 32,86 / 32,0 — y như p95
  chung. 10 lượt nguội chậm nhất: 3.5 7–17 s, 3.8 21–48 s nhưng chỉ ~28 lượt/6 ngày. ⇒ p95 do một luồng khách `/messages` có
  prompt dài (prefill ~30 s) chứ không do TTL. Cần đọc thêm `token_vao` — sổ stream không có (`so_dang_tin=false`, thiết kế).
- Nạp nguội suy từ sổ (khoảng lặng > TTL) mù với lưu lượng đi thẳng llama-swap (các phép đo) và preload; số llama-swap
  đếm được (27/32) lớn hơn vì vậy.
- Đề xuất ngưỡng (để chủ dự án chốt, **chưa cài**): cảnh báo khi TTFT stream **ấm** p95 theo ngày > 45 s (trên cụm 33 s
  hiện tại + biên), hoặc > 5 lượt nạp nguội/ngày mỗi model có TTFT > 20 s. Nếu muốn bỏ hẳn độ trễ nạp nguội: TTL 1800 →
  lớn hơn (đổi yaml ⇒ nạp lại cả hai model; hai model thường trú trên hai card riêng nên TTL không giải phóng gì cho model
  kia — chỉ giải phóng cho ComfyUI/ảnh trên 3090, cần hỏi hồ sơ residency trước).

## 4. Lịch chạy lại

`docs/ltt_llm_dual/RUNBOOK.md` §4b (mới): sau **mỗi lần nâng llama.cpp** và mỗi lần đổi `-np`/`-kvu`/`--cache-ram`/`--spec-type`
chạy 5 phép: canary cô lập · needle các độ sâu phục vụ · cổng MTP · bộ đề 3.5 (biến thể A) · gộp TTFT.
