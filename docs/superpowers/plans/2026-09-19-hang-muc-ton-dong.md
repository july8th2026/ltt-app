# Hạng mục tồn đọng sau phiên 17–18/09 — plan (bảng theo dõi riêng)

> Lập 18/09 23:xx sau tổng kết phiên (`2026-09-18-tong-plan-phien.md` ~99,5 %). Quy trình theo
> `docs/00_LTT_OPERATING_CONTRACT.md` (test nhắm + L1/L2 trong phiên, L3 một lần khi hết mọi hạng mục;
> lệnh nặng qua khoá `cpu_nhieu`, `-n ≤ 6`). Mỗi hạng mục: **tra nguồn trước** (model card, tài liệu engine,
> GitHub issues của thư viện — trích số), worktree riêng, không deploy khi chưa có gate xanh đúng SHA.
> Đã BỎ theo chủ dự án (18/09): hiển thị tok/s/credit trong LTTCODE ("đã có thông tin thì bỏ qua").

## Bản đồ chồng chéo (đọc trước khi giao việc)

| Vùng mã đang sống | Hạng mục chạm | Luật |
|---|---|---|
| Đường suy nghĩ/ngân sách 3.5 (`platform_core/llm/*`, `apps/ltt_llm/*`, L-26) | T1 | chỉ T1 sửa |
| Đường stream A (`luong.py`, `streaming`), sổ lượt B (`llm_gateway/so_luot.py`) | T1 (có thể), T4, T1b (`streaming.py`), T1c (`luong.py` phần suy nghĩ) | T4 chỉ thiết kế tới khi T1 gộp `main`; T1c không chạm `streaming.py` |
| Xếp hàng A (`admission.py`, `luat_nhan.py`, L-29) | — | không hạng mục nào sửa |
| Dịch giao thức Claude/Codex (`server/api/*`, `public_api`) | T3 | chỉ thiết kế |
| LTTCODE preset/skill/adapter (kho LTTCODEAPP) | T2, T4 (header) | T4 phần LTTCODE sau T2 gộp |
| `tools/` công cụ vận hành | T5 | độc lập |

## Hạng mục

| # | Hạng mục | Thuộc | Trạng thái | Ghi chú |
|---|---|---|---|---|
| T1 | 3.5 trả 200 rỗng khi `max_tokens` nhỏ | A | ✅ deploy A `99427f4f` 23:25 | gốc: L-26 chỉ cài ở `/chat/completions`; `/messages` + `/responses` (stream + không) + job không đặt budget; llama.cpp `/v1/messages` chỉ đọc `thinking.budget_tokens`. Sửa `6cbb00ea`, L2 3 thành phần xanh; production 0/8 rỗng (trước 2/5) |
| T1b | Lọt thẻ `</think>` vào câu trả lời khi budget cắt ngang suy nghĩ (1/8 lượt) + khối thinking bị bỏ ở `/messages` không stream + `max_tokens ≤ 512` ⇒ budget 0 | A | ⬜ | lọc/đóng khối suy nghĩ ở A; quyết định có trả 400 như `/chat/completions` không |
| T1c | Bộ chọn effort 3.8 (low/medium/xhigh, L-26) VÔ TÁC DỤNG ở `/messages` stream: A gửi `reasoning_effort` cấp cao nhất, llama.cpp 91f6a6cf3 `server-chat.cpp:579` `server_chat_convert_anthropic_to_oai` chỉ chép `temperature\|top_p\|top_k\|stream\|chat_template_kwargs` ⇒ template chạy mặc định `--reasoning-effort xhigh` | A | 🟡 mã `phien/t1c-effort` (chờ gộp) | `luong.chuan_hoa_suy_nghi` gom 3 chỗ khai effort về MỘT `reasoning_effort` (+ danh sách cho phép `chat_template_kwargs` = chỉ effort) · `luong.dat_effort_cho_engine` dời sang `chat_template_kwargs.reasoning_effort` ở `/messages`. Đo engine B n=5: prompt low 62 / medium 36 / xhigh 74 token (trước ở `/messages`: 74 mọi mức); thân do mã t1c dựng (LTTCODE `/messages`, Codex `/responses`) low 80 / xhigh 92 token. ⚠️ Độ dài ra KHÔNG theo effort một cách tin được (median token ra low/xhigh: bài lát gạch 4695/4855 và 4240/4610 — chạm budget 4096; bài tàu hoả 385/245 — low DÀI hơn; bài dễ 423/434): effort của template v22.5 chỉ là một câu trong system prompt, không phải budget. ⇒ **L-32 (chủ dự án duyệt 19/09)**: máy chủ đặt budget suy nghĩ 3.8 theo mức low 1.024 / medium 2.048 / xhigh 4.096, `min(mức, max_tokens − 512)`, mọi cửa; đo: bài khó suy nghĩ đúng trần, trễ 36/67/120 s, đúng 6/9·4/9·8/9; bài dễ 30/30. Không sửa `streaming.py` (T1b). Việc lane LTTCODE: bỏ `compaction` khỏi `LOWEST_EFFORT_PURPOSES`, dùng effort của phiên (effort ở đầu prompt ⇒ đổi mức = mất cache) |
| T2 | Harness gợi ý skill theo từ khoá cho LTT-3.5 (3.5 chỉ tự gọi `skill` 62 %) | LTTCODE | ⏸ HOÃN (chủ dự án 18/09: phân tích thêm, cập nhật harness một lượt) | tra cách cộng đồng Claude Code làm (hook UserPromptSubmit + luật từ khoá), cơ chế DSH; eval 109 câu đã có |
| T3 | R-14 tool search cho client Claude Code/Codex | A (dịch giao thức) | ✅ thiết kế `c6c2cfe2` (mã chờ; pha 0 đo khung ≤ 35 %) | tài liệu Anthropic tool search, Codex tương đương, cách làm với Qwen |
| T4 | R-06/07 id phiên + bỏ định danh khách khỏi thân gửi B | A (+ LTTCODE ⏸) | ✅ thiết kế `ec046dd3`; mã P1/P2 được làm (T1 đã gộp) | không chuyển header xuống B (X-Conversation-Id tắt huỷ) |
| T5 | R-16 cảnh báo p95 TTFT + nạp lạnh | A (vận hành) | ✅ mã `3159aa3f` (`tools/canh_bao_ttft_b.py`, 52 test); chờ gộp cùng L3 cuối; lịch chạy do chủ máy tạo | ngưỡng từ số đo 12–18/09 |
| T6 | Chứng chỉ Authenticode EV + E2E trên máy ảo sạch (B2/B-VM) | chủ dự án | ⛔ ngoài agent | cần mua chứng chỉ |
| T7 | 5 thư mục worktree rỗng bị khoá tiến trình (`D:\LTTSTUDIOSAPP-{kiem-dinh-ky,np4-35,t17,tich-hop-2,tong-ket}`) | dọn | ⬜ | xoá sau khi tiến trình nhả |

**Thứ tự gộp:** T1 → (T4 mã) ; T2, T3, T5 song song. Khi hết: gộp tích hợp → L3 MỘT lần → deploy → báo.
