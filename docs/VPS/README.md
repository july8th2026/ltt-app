# VPS — TRA CỨU (giữ, đang sống — tầng giao diện/console)

Loại: TRA CỨU. Tệp chủ: `GIAO_DIEN.md`, `PHAN_TICH_VPS_PROXMOX.md`,
`PHUONG_AN_BO_CUC_CONSOLE.md`. Nhiều tệp `apps/vps/*.py` trỏ trực tiếp
(`manifest.py`, `nav.py`, `os_images.py`, `services/billing.py`,
`services/vultr.py`) — 228 blocking, tệp code_ref cao nhất cụm L-E.

Xem thêm `docs/vps_v2/` (kiến trúc + runbook mới hơn) và `docs/VPS_V4/`
(quyết định + trạng thái production mới nhất) — cụm VPS ba tầng, đọc README
từng thư mục để biết tầng nào là "hồ sơ hiện hành" cho câu hỏi cụ thể.

Đã sửa 1 tham chiếu chết thật: `UI_MVP_V2/00_KE_HOACH_GIAO_DIEN.md` trỏ đúng
`tests/test_311_vps_giao_dien_mvp.py` (trước đó ghi nhầm số hiệu cũ `test_306`).
`setuppromox/KIEN-TRUC-GATEWAY.md` trong `PHAN_TICH_VPS_PROXMOX.md` là đường
trên **máy B**, không phải kho này — không sửa.
