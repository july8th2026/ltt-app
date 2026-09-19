# VPS_V4 — TRA CỨU (giữ, tầng kiến trúc VPS hiện hành — xác nhận lại 19/09)

Loại: TRA CỨU (nâng từ CẦN XEM ở lượt 19/09). Tệp chủ: `02_DECISION_LOCK.md`
(khoá quyết định D01-D10, 2026-09-12) → `10_FINAL_REPORT.md` (Status: **CLOSED
17/09/2026 — PRODUCTION; OVH DEFAULT; SALES OPEN**). Đây là kiến trúc VPS **hiện
đang chạy production** (khớp `apps/vps/` OVH-mặc-định, auto-buy IP), không phải
đợt cũ đã bị thay — dù chưa có comment mã nào trỏ thẳng đường dẫn `docs/VPS_V4/`.

Gộp làn với `docs/VPS/` và `docs/vps_v2/` (cụm VPS ba tầng, tránh xung đột chéo
giữa các làn). Quan hệ ba tầng (`VPS` = giao diện console cũ hơn, `vps_v2` =
kiến trúc + runbook đang vận hành với `apps/vps/services/dieu_khien.py` và
`apps/vps/suc_khoe.py` trỏ trực tiếp, `VPS_V4` = quyết định kiến trúc + trạng
thái production mới nhất) — cần chủ dự án xác nhận có nên gộp tên hay không;
không tự đổi tên/gộp thư mục ở lượt này. Không lưu trữ (tất cả < 10 ngày; nội
dung mô tả trạng thái đang sống, không phải đợt đã đóng).
