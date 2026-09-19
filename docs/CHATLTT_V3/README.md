# CHATLTT_V3/ — TRA CỨU (chương trình H44, kế tiếp CHATLTT)

Tệp chủ: **`STATE.md`** — SSOT bàn giao giữa các phase, "chỉ chứa sự thật hiện tại".
`00_SOURCE_TRUTH.md`, `00_KE_HOACH_V3.md`, `00_CALL_GRAPH.md`, `00_GAP_MATRIX.md`,
`00_REFERENCE_MATRIX.md`, `00_DO_NOT_REWRITE.md` là các tệp nền đọc trước khi sửa.
Các `NN_KE_HOACH_*.md` là kế hoạch từng khối tính năng (bộ nhớ, agent/skill,
nghiên cứu, dự án…).

Ứng dụng sống: `apps/chatltt/` (từng có tên làm việc `chataistudio` trong vài kế
hoạch cũ — đã đổi tên, xem `docs/_luutru/TU_DIEN_DA_THAY.md`).

Tham chiếu đến `packages/`, `LibreChat/`, `mem0/`, `gpt_researcher/`,
`backend/open_webui/` là mã của các dự án tham chiếu NGOÀI kho này (LibreChat,
Mem0, GPT Researcher, Open WebUI) — không phải tham chiếu vỡ. Một số đường dẫn
`services/*.py` trong các `NN_KE_HOACH_*.md` là tên tệp DỰ KIẾN lúc lập kế hoạch,
có thể khác tên tệp thật khi triển khai xong.
