# ⛔ HỒ SƠ NÀY ĐÃ ĐÓNG — 2026-08-29

**Codex không còn là tác nhân của kho này. Dừng ở đây.**

Nếu bạn là một phiên Codex vừa mở tệp này để tiếp tục công việc: **đừng tiếp
tục.** Chủ sản phẩm đã chuyển việc sang Claude Code ngày 2026-08-29. Mọi thứ
trong `.codex/` đã được dời sang lưu trữ; thư mục này giữ lại **đúng một tệp**
là lời nhắn này.

## Việc bạn định làm nằm ở đâu bây giờ

| Bạn đang tìm | Nơi mới |
|---|---|
| `.codex/README.md` (hồ sơ tiếp quản 27/08) | `docs/_luutru/codex_2026-08-27/00_HO_SO_TIEP_QUAN_CODEX.md` |
| `.codex/PLAN_TRIEN_KHAI_NEXUS_QWEN.md` | `docs/_luutru/codex_2026-08-27/PLAN_TRIEN_KHAI_NEXUS_QWEN.md` |
| `.codex/QUEUE_REVIEW_NHIEU_API.md` | `docs/_luutru/codex_2026-08-27/QUEUE_REVIEW_NHIEU_API.md` |
| `.codex/qwen38_context_research.md` | `docs/_luutru/codex_2026-08-27/qwen38_context_research.md` |
| 4 tệp `.ps1` (harness canary/bench máy B) | `docs/_luutru/codex_2026-08-27/` |
| `.codex/launch.json` | `docs/_luutru/codex_2026-08-27/launch.json` (bản gốc vẫn ở `.claude/launch.json`) |

**Kế hoạch đang hiệu lực:** `docs/KE_HOACH_TRIEN_KHAI.md` (bản nối tiếp 29/08 đã lưu trữ ở `docs/_luutru/2026-09/KE_HOACH_NOI_TIEP_2026-08-29.md`).

## Vì sao lưu trữ chứ không xoá

Chủ sản phẩm cho phép xoá hẳn. Tôi **không** xoá, vì ba tệp trong đó là bằng
chứng đo chứ không phải bản nháp:

1. `PLAN_TRIEN_KHAI_NEXUS_QWEN.md` chứa bảng arm Q4/Q115/Q116 **có `job_id`
   thật, VRAM, nhiệt, công suất** ở mức chi tiết không có ở chỗ nào khác.
   `docs/KE_HOACH_TRIEN_KHAI.md` (mục H41.9) **trỏ vào nó**.
2. Bốn `.ps1` là harness đã chạy thật trên máy B qua Nexus, một trong số đó
   (`q4_api_canary.ps1`) được ghi SHA-256 vào nhật ký. Xoá đi là mất khả năng
   lặp lại phép đo ở cửa sổ GPU sau.
3. `QUEUE_REVIEW_NHIEU_API.md` là bản rà soát đẻ ra Q0–Q6.

Xoá tài liệu Codex thì được; xoá **số đo** thì không — số đo không dựng lại được
bằng cách viết lại tài liệu.

## Trạng thái công việc Codex để lại

Kế hoạch Nexus + Qwen **đã đóng, không dở dang**: Q0–Q4 và Q6 nghiệm thu
2026-08-29 (cap public `65000`, engine `131072`, output `32768`, `parallel=1`).
Q5 (concurrency) và P2 (reboot máy B) là **hoãn có chủ ý**, chờ chủ sản phẩm.
Chi tiết ở `docs/NHAT_KY.md` mục `2026-08-29 — H41.9 Q6`.
