# vps_v2 — TRA CỨU (giữ, đang sống — kiến trúc + runbook vận hành)

Loại: TRA CỨU. Tệp chủ: `STATE.md`, `ADR_INDEX.md` (quyết định kiến trúc),
`RUNBOOK_KHOI_PHUC.md` (runbook khôi phục — `apps/vps/suc_khoe.py` trỏ trực
tiếp). `apps/vps/services/dieu_khien.py` trỏ `ADR_INDEX.md` ADR-03.

4 CHET (`ADR_INDEX.md`, `BASELINE.md`, `KNOWN_BLOCKERS.md`,
`RELEASE_SCORECARD.md` đều trỏ `CORE/TARGET_ARCHITECTURE.md` hoặc
`CORE/QUALITY_SCORECARD.md`) — không tìm thấy `CORE/` ở đâu trong kho; chưa rõ
là mẫu quy trình dùng chung chưa từng viết ra. Chưa sửa — xem
`docs/_luutru/NGOAI_LE_QUET.md`. THAY `admin-mvp-v3 -> main` trong `STATE.md`
là tường thuật lịch sử, không sửa.

Xem thêm `docs/VPS/` (tầng giao diện/console) và `docs/VPS_V4/` (quyết định +
trạng thái production mới nhất).
