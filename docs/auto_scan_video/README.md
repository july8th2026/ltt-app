# auto_scan_video/ — TRA CỨU (V2, lớp lịch sử nền của Auto Scan Video)

Tệp chủ: **`STATE.md`** — SSOT bàn giao cho gói prompt V2. `CAPABILITY_MATRIX.md`,
`DEPENDENCY_MAP.md`, `MVP_CONTRACT.md`, `RISK_REGISTER.md` là các hợp đồng/bảng
tra của đợt V2. `reports/NN_REPORT.md` là nhật ký từng phase (00…20).

Theo thiết kế của chương trình ("V4 supersedes by ADR, never by deletion" —
`docs/auto_scan_video_v4/STATE_V4.md`), thư mục này **giữ nguyên vĩnh viễn** làm
lớp lịch sử nền cho `auto_scan_video_v4/`, `_v5/`, `_v6/` — không lưu trữ, không
xoá dù mới hơn đã ra đời.

Nhiều bảng ở đây (`CAPABILITY_MATRIX.md`, `DEPENDENCY_MAP.md`) mô tả mã của kho
**bot cũ bên ngoài** (`nerf_engine/`, `Bot_Whisper_FULL/`, `Bot_PausePipeline/`,
`DUNGVIDEO-FULL/`, `utils/gsheets.py`…) dùng để lập kế hoạch trích xuất — không
phải đường dẫn trong kho này, không phải tham chiếu vỡ. Ứng dụng sống hiện tại:
`apps/auto_scan_video/`.
