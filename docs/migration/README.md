# migration — TRA CỨU (giữ, đang sống)

Loại: TRA CỨU. Nội dung hiện tại: `workflow_apps/` — audit các bot cũ
(Gemini/Whisper/pause/dungvideo…) đang được soát để di trú sang nền tảng
Workflow mới. Tệp chủ: `00_STATUS.md`/`01_SOURCE_MANIFEST.md`. 276 blocking
(43 code) — code_ref/test gate thật cao nhất cụm L-E.

Toàn bộ CHET (`bot/worker.py`, `engine/*.py`, `utils/gsheets.py`,
`configs/*.json`…) là đường trong MÃ NGUỒN CÁC BOT CŨ đang audit (kho khác,
ví dụ `D:\BOT GEMINI`), không phải kho này — không sửa, xem
`docs/_luutru/NGOAI_LE_QUET.md`.
