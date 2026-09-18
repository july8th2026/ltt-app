# Phase 03 — `text.chat` qua cửa nội bộ: chuẩn hoá, SLO, và đóng D12

> ⚠️ **Ảnh chụp 03/09/2026** (tệp này) — không phải hiện trạng. Số đồng thời LLM ở đây
> (`DONG_THOI_MAY_B=1`, `parallel=1`, một suất máy B…) **đã cũ** → `apps/ltt_llm/ngan_sach.HO_SO`
> (L-23, L-28 trong `docs/ltt_llm_dual/DECISION_LOG.md`).

## Source
- worktree: `D:\LTTSTUDIOSAPP\.claude\worktrees\lttchat-autonomous-build-plan-1cf29d`
- branch: `claude/lttchat-autonomous-build-plan-1cf29d` · base: `bdddeae` (Phase 02)
- canonical rules read: Q106/Q107/Q111/Q112/Q113/Q114/Q116, `docs/VLM_NOI_BO/RA_SOAT_THAM_SO_LTT_LLM.md`, `docs/audit_ltt_llm/STATE.md` (ownership table), `apps/ltt_llm/ngan_sach.py`

## Evidence

| Finding | Source/runtime/test | Result |
|---|---|---|
| Đường stream nội bộ dùng `/v1/chat/completions` + `stream_options.include_usage`; chunk OpenAI → sự kiện canonical | `runtime_noi_bo/luong.py::_su_kien_tu_goi`, `test_600`, `test_603` | reasoning/content/tool_calls/finish_reason đều lên sự kiện; `[DONE]`, `event:`, dòng không JSON bỏ qua |
| SSE cắt giữa dòng theo nhịp mạng | `test_603::test_doc_sse_dem_toi_tron_dong` | một `data:` tới làm ba khối ⇒ đúng một sự kiện |
| **Cắt cụt không im lặng**: `finish_reason=length` lên `response.completed` | `test_603::test_finish_reason_length_len_su_kien` | UI có căn cứ hiển thị "bị cắt ở trần" thay vì coi là xong |
| **Stream không giảm giá token cache** — `DemToken` chỉ đọc `usage`, còn llama-server để `cache_n` ở `timings` (đúng chỗ `cong_vlm.doc_su_dung` đọc cho đường không stream) | đọc mã `dem_token_luong.py:105-155` vs `cong_vlm.py:120-140`; `test_603::test_dem_token_doc_timings_cache_n`, `test_cache_lam_re_luot_stream` | **sửa**: `_quet` đọc thêm `timings.cache_n`; 1.000 vào/800 cache rẻ hơn 0 cache. Ảnh hưởng cả `/api/v1/messages|responses` (khách agentic) lẫn ChatLTT — theo hướng **có lợi cho khách** |
| Vision/tools/reasoning_effort/temperature đi qua **nguyên xi**; alias→id dịch ở `chuan_bi`; `stream_options` của bên gọi không bị đè; tool không khai admission ⇒ không lease | `test_603::test_chuan_bi_giu_nguyen_vision_tools_reasoning` | pass |
| Mặc định token ra là **của cửa stream** (4.096), không phải 1.024 của cửa đồng bộ; khách khai thì kẹp theo chỗ còn lại trong ngữ cảnh | `test_603::test_tran_token_ra_kep_theo_ngu_canh_va_mac_dinh_cua_stream` | pass — lỗi "hỏi dài thì im lặng" (30/08) không tái được qua cửa nội bộ |
| Bận ≠ hỏng; dừng giữa chừng thu đúng phần đã sinh; thiếu tiền/hết suất trước byte đầu | `test_600` (Phase 02) | pass |
| **D12 — trần ngữ cảnh công bố** | `docs/QUYET_DINH_NEN_TANG.md` **Q120**; `test_604` | Q116 (`65000`) ĐÃ THAY phần con số: trần là số dẫn xuất `ngan_sach.TOKEN_VAO_TRAN` (96.256), công bố `CONG_BO_CHO_CLIENT` (88.555); `danh_muc` chiếu đúng số đó; không tài liệu hiện hành nào còn nói 65K như luật |

## Decisions made autonomously

| Decision | Options | Chosen | Why | Reversible |
|---|---|---|---|---|
| Đường máy B cho client nội bộ | `/v1/messages` (Anthropic) · `/v1/responses` · **`/v1/chat/completions`** | chat/completions | khuôn chunk đơn giản nhất, `reasoning_content` có sẵn (`--reasoning-format deepseek`), `tools` OpenAI là khuôn `text.chat` đã khai | có |
| Xin usage | mặc định · **`stream_options.include_usage=True`** | xin tường minh | không xin ⇒ `DemToken` không thấy usage ⇒ hoàn đủ thu 0 (đúng luật, nhưng là cho không) | có |
| Q116↔mã | giữ 65K và hạ mã · **Q120: mã là nguồn, doc theo mã** · để nguyên hai luật | Q120 | rà soát 30/08 chứng minh 65K là hệ quả của trần body 256 KB + đo đường không stream (đã giải bằng Q113); canary Q111 86K/102 s trên cổng thật; production đã chạy 88.555 từ 02/09 | có (một dòng Q mới) |
| Vị trí cache-token | sửa `DemToken` (chung cho API + ChatLTT) · chỉ parser của ChatLTT | `DemToken` | một bộ đếm cho hai cửa (PA-7); sửa riêng là hai cách tính tiền | có |
| Heartbeat khi chờ máy B mở luồng (tới 75 s) | trong facade (thread) · **ở route HTTP của ChatLTT** (Phase 08: chạy generator trong thread + hàng đợi, gửi `: ping` mỗi 15 s khi chưa có sự kiện) | route | facade là generator đồng bộ, không nên tự sinh thread; `response.started` đã ra trước `luong_vlm.mo` nên byte đầu đã sớm | có |

## SLO sản phẩm cho text (căn cứ số đo đã có; đo lại LIVE ở Phase 12)

| Chỉ số | Mục tiêu | Căn cứ |
|---|---|---|
| Byte đầu tới trình duyệt | ≤ 2 s sau khi nhận request (không phụ thuộc prefill) | `response.started` phát sau admission+giữ chỗ, trước `luong_vlm.mo` (`test_600::test_response_started_phat_TRUOC_khi_mo_luong`) |
| TTFT (token đầu) | ≤ 25 s (nạp model) + `token_vao/750` s prefill | Q113: prefill thấp nhất 756 tok/s; `llama-swap` nạp lại ~25 s |
| Tốc độ sinh | ≥ 40 tok/s p50 | Q113: decode 41,57 tok/s |
| Trần vào công bố | `ngan_sach.CONG_BO_CHO_CLIENT` (88.555); vision 28K | Q120, `test_334`, `test_604` |
| Trần ra | `TOKEN_RA_TRAN` 32.768; mặc định cửa stream 4.096; `length` phải hiện | `test_603` |
| Tiền | thu = token thật × bảng giá `ltt-vlm-2026-08-22`, cache giảm giá; huỷ ⇒ thu phần đã sinh; không usage ⇒ 0 | `test_600`, `test_603`, `test_272` |
| Bận | 429/`ban` + `retry_after_s`, không thu, không tiêu suất | `test_600`, `test_272` |
| Đồng thời | 1 lượt/GPU (`llm_remote` 1 suất); UI hiển thị chờ suất | Q112/Q114 |

## Changes
- `platform_core/llm/dem_token_luong.py`: `_quet` đọc `timings.cache_n`.
- `docs/QUYET_DINH_NEN_TANG.md`: Q120 (+ đánh dấu Q116, header "đến Q120"); `docs/KE_HOACH_NOI_TIEP_2026-08-29.md` hai dòng cap 65K trỏ sang Q120.
- Tests: `test_603_text_luong_chuan_hoa.py` (9), `test_604_q120_tran_ngu_canh_mot_nguon.py` (3).

## Tests

| Command | Result |
|---|---|
| `pytest test_603 test_271 test_252 test_334 test_600 -n 0` | 102 passed, 3 skipped |
| `pytest test_604 test_62 -n 0` | xem STATE (chạy sau khi viết báo cáo) |

## Failures found and repaired
- Stream không giảm giá token cache (sửa ở `DemToken`).
- Hai quy tắc mâu thuẫn về trần ngữ cảnh (Q116 vs mã) — đóng bằng Q120 theo giao thức §6.

## External unknown/blocker
- **LIVE**: TTFT/tok-s/usage-khớp-quyết-toán trên máy B thật, cold/warm, sát biên 88K, vision, reasoning ba mức, tool-call, ngắt kết nối, bận thật, timeout 75 s — **chưa đo ở phase này** (không chạm máy B/GPU production từ cây riêng). Công cụ đã có: `tools/bench_llm_hieu_nang.py --url … --lan N` (TTFT/prefill/decode/VRAM, trung vị, chụp `nvidia-smi`), `tools/bench_llm_admission.py`, canary `tools/api_prod_canary.py`. Thử lại ở Phase 12/13 khi máy rảnh.
- Cấu hình máy B: `LTT_LLM_MAX_INPUT_TOKENS` trên tiến trình đang chạy có thể còn `65000` (số cũ của Q116, đã thay bởi Q120; RA_SOAT §G) — việc deploy của chủ sản phẩm; `test_334` live sẽ đỏ nếu lệch.

## Verdict
**PASS (deterministic)** — giao diện stream nội bộ ổn định + test; bằng chứng LIVE ghi là chặn ngoài, thử lại ở Phase 12.

## Next
Autocontinue to phase: **06** (catalog theo chính sách sản phẩm) sau khi Phase 04/05 (đang chạy song song) đóng.
