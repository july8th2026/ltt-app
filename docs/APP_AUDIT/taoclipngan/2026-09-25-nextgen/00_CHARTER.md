# 00 — CHARTER: Nâng cấp Next-Gen Tạo Clip Ngắn (2026-09-25)

## Mục tiêu

Biến app **Tạo Clip Ngắn** (`apps/taoclipngan` + engine `cutclipshort`) thành hệ thống
cắt clip AI thế hệ mới cạnh tranh được với OpusClip / Vizard / Klap, tận dụng lợi thế
riêng của hệ sinh thái LTT (llm_gateway + ltt_llm nội bộ, render_gateway, publish_bot,
hệ credit) mà đối thủ SaaS không có.

**Sản phẩm của đợt này: PLAN triển khai. Không viết code.** Chờ chủ dự án duyệt
trước khi triển khai.

## Phạm vi

| Trong phạm vi | Ngoài phạm vi |
|---|---|
| `apps/taoclipngan/` (manifest, routes, jobs, features, cost, UI) | `platform_core/`, `server/` — ⛔ không sửa (AGENTS.md §2.3); nếu bắt buộc → dừng và giải thích |
| `cutclipshort/` (editorial, evaluation, render, storage, core) | `apps/ltt_llm/` (máy B) — chỉ đọc, chỉ tích hợp |
| Tích hợp LLM qua cầu nối đã có (`platform_core/llm/`) | Training model riêng (không có — dùng ltt_llm/VLM có sẵn) |
| Nối publish_bot, credit, render_gateway | API/MCP công khai cho khách bên ngoài (đề xuất giai đoạn sau) |

## Nguồn dữ liệu

| File | Nội dung |
|---|---|
| `_A_CURRENT_TRUTH_RAW.md` | Audit code: pipeline thật, 6 engine, editorial pure Python, cache, cancel, GPU, credit |
| `_B_LLM_INTEGRATION_RAW.md` | Audit LTT_LLM: cầu nối LLM, VLM, admission/budget, pattern các app đã dùng |
| `_C_COMPETITORS_RAW.md` | Khảo sát 9 đối thủ (benchmark OpusClip), 16 chiều + 12 điểm cơ hội |
| Đọc trực tiếp code | `jobs.py`, `brain.py`, `candidate_generator.py`, `pipeline.py`, `gate.py`, `framing.py`, `cache.py`, `cong_vlm.py`, `dieu_phoi.py`, `admission.py` |
| Audit trước | `docs/APP_AUDIT/taoclipngan/2026-08-11-h32/` (roadmap H32.4 còn nguyên 3 phase chưa làm) |

## Ràng buộc đã chốt (không tự đổi trong plan)

1. **Lifecycle giữ `development`** — chỉ đổi `released` khi qua gate phát hành.
2. **Hợp đồng app** (AGENTS.md §8): routes.py chỉ HTTP, nghiệp vụ trong `services/`/`features.py`,
   chỉ import 4 module của `server` đã liệt kê, cạnh app→app phải khai trong
   `APP_DUOC_DUNG_APP`.
3. **Credit**: không đổi công thức mà không hỏi chủ dự án (đây là quyết định sản phẩm).
4. **Test/gate**: test nhắm mỗi pha, gate `gate.py --doi` chỉ CUỐI PLAN (CLAUDE.md luật 1).
5. **GPU**: job lease 6000 MB VRAM như hiện tại; không tăng lease mà không đo thật.
6. **Máy A/B**: LLM chạy trên máy B (llt_llm port 8299 + render_gateway); máy A
   chỉ là client qua `platform_core/llm`. Không gọi LLM trong worker render.
7. **Không import chéo** hai cây mã nguồn; không sửa `D:\BOT GEMINI`.

## Định nghĩa XONG của đợt này

- Plan đủ chi tiết để triển khai không cần thêm quyết định kiến trúc:
  mỗi hạng mục có **tệp cụ thể**, **đổi gì**, **lệnh kiểm**, **tiêu chí acceptance**.
- Mọi claim về code hiện tại có dẫn chứng `tệp:dòng`.
- Chờ duyệt: **DỪNG** tại plan.
