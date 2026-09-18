# Tra cứu `-b` / `-ub` (llama.cpp ghim 91f6a6cf3) — 18/09/2026, chỉ đọc, chưa đo

**Kết luận:** 3.8 giữ `-b 512 -ub 512`. 3.5 đề xuất chuyển `-b 512` (ub vẫn 512 mặc định); phương án giữa `-b 1024`. Không đổi `-ub` ở cả hai card. **Chốt bằng phép đo trong cửa sổ C4** (ma trận dưới).

## Ngữ nghĩa (mã nguồn ở commit ghim)
- Mặc định b=2048, ub=512 (`common/common.h:451-452`, `common/arg.cpp:1666-1678`); mã tự ép ub = min(b, ub) (`src/llama-context.cpp:247`).
- **`-b` quyết định khoảng lặng của slot khác:** mỗi vòng server gom token decode rồi nhồi prompt tới đủ `n_batch` (`tools/server/server-context.cpp:3103-3115, :3524`), decode từng khúc `n_batch` (`:2869-2877`). Khoảng lặng ≈ `n_batch / tốc độ prefill + một bước decode` — khớp số đo 3.8: 2048 ⇒ 1,95 s (đo 2,08); 512 ⇒ 0,49 s + decode (đo 0,75).
- **`-ub` là lô vật lý**, quyết định compute buffer đặt trước (`llama-context.cpp:596, 835-839`; log `compute buffer size`).
- Model lai (DeltaNet) tách ubatch bằng `split_equal` (`src/llama-memory-hybrid.cpp:67-89`); không đòi b = ub.
- Checkpoint ngữ cảnh đặt ở `4 + n_ubatch` token trước cuối prompt (`server-context.cpp:3561-3569`).
- Không có cờ chunked-prefill/giới hạn prefill riêng — `-b` là cần gạt công bằng duy nhất.
- Nhiễu đo: #28495 (`-kvu` + FA không bỏ khối mask giữa ⇒ prefill request dài thứ hai chậm hơn) ⇒ mọi cấu hình đo ở trạng thái ấm như nhau.

## Chất lượng
Trên CUDA không ảnh hưởng đáng kể — chỉ đổi cách chia việc; bit thấp có thể lệch vì llama.cpp không bất biến theo batch (#27407), vô nghĩa ở temp 1.0. Lỗi chất lượng thật chỉ ở Vulkan (#27237) và Hexagon (#24201), không liên quan.

## VRAM
Mask FA ≈ `n_kv × n_ubatch × 2 B`: ~216 MiB (3.8) / ~256 MiB (3.5) mỗi 512 ub (ước — kiểm bằng log `compute buffer size`). ub 1024 cần thêm ≥ 250–450 MiB trong khi mỗi card còn ~500 MiB; Windows tràn sang shared thay vì OOM ⇒ chậm âm thầm. ub 256 chỉ trả ~110–200 MiB mà mất 25–30 % prefill.

## Cộng đồng
PR #26001 (mở): Qwen3.6 lai MoE, pp 16K, RTX 6000 Pro: ub 256→4378, 512→6204, 1024→8023, 2048→9131 tok/s (dense 27B lợi ít hơn). #26391 (MoE offload) không áp dụng. Chưa có benchmark công bằng đa slot — số của ta 17/09, 18/09 là tốt nhất hiện có.
Suy luận chưa đo: +12,5 % prefill ở b=512 là "giá công bằng" (64 vòng vs 16 vòng, mỗi vòng thêm một bước decode+MTP ~80 ms ≈ +3,9 s) ⇒ prefill một mình b=512 ≈ b=2048. Tổng 3 luồng 125→105 không thể do `-b` (decode 3 luồng ~9 token/batch ≪ 512) ⇒ nhiều khả năng nhiễu độ dài đầu ra.

## Ma trận đo cửa sổ C4 (ấm, n=3, trung vị)
| # | 3.8 | 3.5 |
|---|---|---|
| A | b512/ub512 (đang chạy) | b2048/ub512 (đang chạy, đối chứng) |
| B | b1024/ub512 | b1024/ub512 |
| C | b2048/ub512 (đối chứng cũ) | b512/ub512 |
| D | b1024/ub1024 — chỉ đo nạp/VRAM | b1024/ub1024 — chỉ đo nạp/VRAM |

Chỉ số: tốc độ 1 luồng · tổng 3 luồng (cố định `max_tokens`) · luồng nhỏ cạnh prefill 32K (tok/s + khoảng lặng dài nhất) · prefill 32K khi có người sinh · **prefill 32K một mình** · `compute buffer size` + VRAM dedicated/shared. D: shared tăng > 100 MiB so nền ⇒ bỏ. Mỗi cấu hình chạy một lượt 32K bỏ đi trước; nonce đầu prompt; thời gian lấy `prompt eval time` của engine. Chạy: 4 lần lưu yaml (mỗi lần cả hai model đổi cùng cặp; `-watch-config` nạp lại cả hai), trong mỗi lần `POST /api/models/unload/qwen35-api` đo 3.8, rồi nạp lại 3.5 + unload 3.8 đo 3.5. ~60 phút, gộp với đo số job (C4). Cuối cùng khôi phục cấu hình chọn và so SHA yaml.

**Chưa chắc tới khi đo:** kích thước compute buffer thật; prefill một mình b=512 có ngang b=2048; tổng 3 luồng giảm có phải nhiễu; ctx nháp MTP có dùng chung `n_ubatch` (`common/speculative.cpp` chưa đọc).

## Đính chính 18/09 — số slot không kéo theo KV
Với `-kvu`, `n_ctx_seq = n_ctx` (`src/llama-context.cpp:290-291`): kho KV dùng chung, kích thước theo `-c`, KHÔNG nhân theo `-np`. Phần tăng theo slot chỉ là trạng thái lớp DeltaNet (model lai) × (1 + `n_rs_seq` nháp MTP) (`src/llama-memory-recurrent.cpp:101`) + phần nháp MTP mỗi slot: đo 3.5 np3→np4 +150 MiB, np6 +270 MiB (tràn shared). `KET_QUA_DO_17_09.md` đo 3.8 np4/np5 với `-c` giảm (200.704/184.320) là **lựa chọn của phép đo**, không phải bắt buộc — C4 đo lại 3.8 np4/np5 ở `-c 221184`, chỉ giảm nếu tràn shared.
