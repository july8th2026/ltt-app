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
| Đường stream A (`luong.py`, `streaming`), sổ lượt B (`llm_gateway/so_luot.py`) | T1 (có thể), T4 | T4 chỉ thiết kế tới khi T1 gộp `main` |
| Xếp hàng A (`admission.py`, `luat_nhan.py`, L-29) | — | không hạng mục nào sửa |
| Dịch giao thức Claude/Codex (`server/api/*`, `public_api`) | T3 | chỉ thiết kế |
| LTTCODE preset/skill/adapter (kho LTTCODEAPP) | T2, T4 (header) | T4 phần LTTCODE sau T2 gộp |
| `tools/` công cụ vận hành | T5 | độc lập |

## Hạng mục

| # | Hạng mục | Thuộc | Trạng thái | Ghi chú |
|---|---|---|---|---|
| T1 | 3.5 gọi không stream trả 200 rỗng khi `max_tokens` nhỏ (2/5 lượt, `stop=max_tokens`, không text/thinking) | A + engine B | 🔵 điều tra (`phien/35-rong`) | có từ trước 18/09; nghi ngân sách máy chủ đặt (L-26, `max_tokens−512`) không tới engine |
| T2 | Harness gợi ý skill theo từ khoá cho LTT-3.5 (3.5 chỉ tự gọi `skill` 62 %) | LTTCODE | ⏸ HOÃN (chủ dự án 18/09: phân tích thêm, cập nhật harness một lượt) | tra cách cộng đồng Claude Code làm (hook UserPromptSubmit + luật từ khoá), cơ chế DSH; eval 109 câu đã có |
| T3 | R-14 tool search cho client Claude Code/Codex (`defer_loading`/`tool_reference`, hiện `ENABLE_TOOL_SEARCH=false`) | A (dịch giao thức) | ⬜ thiết kế | tài liệu Anthropic tool search, Codex tương đương, cách làm với Qwen |
| T4 | R-06/07 nối id phiên client (`X-Claude-Code-Session-Id`, Codex `session-id`/`thread-id`) vào sổ lượt A + nối sổ B qua `X-LTT-Request-Id`; LTTCODE gửi header phiên | A + B (+ LTTCODE ⏸ hoãn cùng harness) | ⬜ thiết kế → mã phía A/B sau T1 | không chuyển header xuống B (X-Conversation-Id tắt huỷ) |
| T5 | R-16 cảnh báo: p95 TTFT stream theo ngày (> 45 s) + nạp lạnh (> 5/ngày/model, TTFT > 20 s) từ `tools/tong_hop_ttft_b.py` | A (vận hành) | ⬜ | ngưỡng từ số đo 12–18/09 |
| T6 | Chứng chỉ Authenticode EV + E2E trên máy ảo sạch (B2/B-VM) | chủ dự án | ⛔ ngoài agent | cần mua chứng chỉ |
| T7 | 5 thư mục worktree rỗng bị khoá tiến trình (`D:\LTTSTUDIOSAPP-{kiem-dinh-ky,np4-35,t17,tich-hop-2,tong-ket}`) | dọn | ⬜ | xoá sau khi tiến trình nhả |

**Thứ tự gộp:** T1 → (T4 mã) ; T2, T3, T5 song song. Khi hết: gộp tích hợp → L3 MỘT lần → deploy → báo.
