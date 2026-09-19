# Ngoại lệ máy quét `tools/quet_tai_lieu.py`

Danh sách CHET/THAY đã xem lại bằng `git grep`/đọc nội dung thật (yêu cầu
"chống dọn nhầm") và xác định KHÔNG phải lỗi cần sửa — máy quét không phân biệt
được các trường hợp dưới đây với tham chiếu vỡ thật. Không đoán khi chưa xem —
mỗi mục ghi bằng chứng đã kiểm.

## Làn L-D (`docs/CHATLTT`, `docs/CHATLTT_V3`, `docs/LTT_VOICE`,
`docs/MVP_OPTIMIZATION_V2`, `docs/VIDEO_AI_V2`, `docs/admin_mvp_v3`,
`docs/auto_scan_video`, `docs/auto_scan_video_v4/_v5/_v6`, `docs/multijob`) — 19/09

Quét cụm ban đầu: 329 dòng (228 CHET, 101 THAY) trên 11 thư mục. Sau khi thêm
dòng `apps/chataistudio -> apps/chatltt` vào từ điển (Lớp 4) và 9 `README.md`
mới (Bước 5), quét lại còn 349 dòng — 20 dòng mới đều thuộc các lớp dưới đây:
13 dòng `apps/chataistudio` mới bị bắt bởi từ điển vừa thêm (Lớp 4, tất cả nằm
trong tài liệu kế hoạch/audit đã có ngày, không sửa) + 7 dòng là ví dụ minh hoạ
ngay trong các `README.md` mới viết (tự tham chiếu để giải thích ngoại lệ — xem
nội dung `README.md` của `LTT_VOICE`, `MVP_OPTIMIZATION_V2`, `admin_mvp_v3`,
`auto_scan_video`, `auto_scan_video_v5`, mỗi câu đều nói rõ đó là ví dụ không sửa
thành tên mới). Tổng cuối: 349 dòng, 0 dòng cần sửa thêm ngoài các lớp đã liệt kê.
Tất cả 11 thư mục giữ
nguyên phân loại TRA CỨU/giữ của kiểm kê Task 2 — đã xác minh lại bằng
`git grep` (code_refs thật cho từng thư mục, ví dụ `admin_mvp_v3` được
`server/admin.py`/`server/routes/admin/*.py` trích dẫn trực tiếp,
`MVP_OPTIMIZATION_V2` được `tools/lint_app_contract.py` trích một mục). Không
thư mục nào đủ ba bằng chứng để chuyển LỊCH SỬ.

### Lớp 1 — Tên nhánh lịch sử `admin-mvp-v3` (toàn bộ 101 dòng THAY của cụm)

Mọi dòng `THAY … admin-mvp-v3 -> main` trong cụm L-D nằm trong văn bản có ngày/
tên nhánh cụ thể ("Ngày: 2026-08-29. Nhánh: admin-mvp-v3", "gốc chung với trunk
768b1dba (admin-mvp-v3)") — ghi chép ĐÚNG tên nhánh tại thời điểm viết, trước khi
nó gộp vào `main`. Từ điển `admin-mvp-v3 -> main` đúng cho câu hướng dẫn HIỆN
HÀNH ("chờ admin-mvp-v3 để deploy"), không đúng cho câu tường thuật lịch sử đã có
ngày tháng đi kèm — sửa sẽ làm sai lịch sử. Đã kiểm mẫu ở `admin_mvp_v3/`,
`CHATLTT/STATE.md`, `CHATLTT_V3/STATE.md`, `LTT_VOICE/*`, `VIDEO_AI_V2/DECISIONS.md`,
`VIDEO_AI_V2/LEGACY_INVENTORY.md`, `auto_scan_video*/`. Không sửa.

### Lớp 2 — Đường dẫn thuộc kho/dự án tham chiếu NGOÀI `D:\LTTSTUDIOSAPP`

Không phải tham chiếu vỡ — các đường dẫn này thuộc mã nguồn của dự án khác dùng
để lập kế hoạch trích xuất/so sánh, không nằm trong kho này:
- `nerf_engine/…`, `Bot_Whisper_FULL/…`, `Bot_PausePipeline/…`,
  `DUNGVIDEO-FULL/…`, `FULL AUTO VIDEO/…`, `Cut_only ver2/…`, `utils/gsheets.py`,
  `utils/gdrive.py` — kho "bot cũ" tham chiếu trong `docs/auto_scan_video*`
  (xác nhận: `docs/auto_scan_video_v4/CAPABILITY_INVENTORY_V4.md` dòng 92 tự ghi
  "legacy `nerf_engine/stages/scene_detect.py` is outside the repo").
- `packages/`, `client/`, `api/server/`, `e2e/` (LibreChat), `mem0/configs/…`
  (Mem0), `gpt_researcher/…` (GPT Researcher), `backend/open_webui/…`
  (Open WebUI), `LibreChat/…` — mã tham chiếu trong `docs/CHATLTT/reports/01_librechat_tham_chieu.md`
  và nhiều `docs/CHATLTT_V3/NN_KE_HOACH_*.md`.
- `docs/API.md`, `docs/CLI.md`, `docs/MODELS.md`, `docs/DEEPY.md`,
  `docs/PLUGINS.md`, `models/wan/…`, `shared/api.py`, `shared/mcp_server.py`,
  `wangp-agent/…`, `defaults/*.json`, `workflows/*.json` — tài liệu/mã của
  **WanGP** (engine chạy trên C-CLOUD, không vendor trong kho này; xem
  `docs/VIDEO_AI_V2/README.md`, `docs/VIDEO_AI_V2/DECISIONS.md` D-V2-005).
  Xác nhận: `tools/wangp/` trong kho này chỉ là lớp điều phối gọi WanGP từ xa,
  không có `docs/API.md` cục bộ.
- `src/vieneu/…`, `vieneu_utils/…`, `sea_g2p/…`, `license_server/…`,
  `apps/gradio_main.py` — mã nguồn động cơ giọng nói tham chiếu ngoài kho trong
  `docs/LTT_VOICE/NGUON_CHAN_LY.md`, `UPGRADE_98/`, `VIRAL_VOICE_AUDIT_2026-09-07.md`.

### Lớp 3 — Tệp cục bộ/không commit/đã xoay vòng

`test-results/gates/<timestamp>.json` (bản ghi gate máy sinh, xoay vòng — không
giữ vĩnh viễn), `.claude/launch.json`, `.claude/settings.local.json`
(cấu hình máy cục bộ, không commit), `.superpowers/sdd/…/progress.md`
(scratch phiên `superpowers`, không commit), `tmp/*.json` (tệp tạm), `.ltt/chatltt/state.json`
(runtime state), `.github/workflows/gate.yml` (workflow thật ở kho là
`.github/workflows/gate-quick.yml` — tên khác lúc viết `LTT_VOICE/UPGRADE_98/06_BLOCKERS.md`,
CẦN XEM nếu phiên sau đọc kỹ blocker đó) — phần lớn còn lại là tài liệu
ĐÚNG mô tả một tệp từng tồn tại tại máy/thời điểm viết, không phải lỗi.

### Lớp 4 — Kế hoạch mô tả tên tệp DỰ KIẾN, khác tên thật lúc triển khai

`docs/LTT_VOICE/GUI_MASTER_PLAN.md`, `GUI_VOICE_CATALOG_CONTRACT.md`,
`VOICE_UI_EXECUTION_PLAN.md` đặt tên tệp dự kiến bằng tiếng Anh (`catalog.py`,
`routes.py`, `voice.js`) — `apps/ltt_voice/` triển khai xong dùng quy ước tiếng
Việt khác (`giong_mau.py`, `doc_man_giong.py`…), xác nhận bằng
`find apps/ltt_voice -maxdepth 1 -name "*.py"`. Tương tự
`docs/CHATLTT_V3/06_KE_HOACH_P06.md` dòng 385 ghi `apps/chataistudio/features.py`
— app đã đổi tên thành `apps/chatltt/` (đã thêm dòng vào
`docs/_luutru/TU_DIEN_DA_THAY.md`); tệp `features.py` cụ thể không tồn tại ở tên
mới, tính năng trích văn bản PDF mô tả trong kế hoạch chưa xác nhận đã triển
khai đúng như vậy — CẦN XEM lại nếu có phiên sau đi sâu vào tính năng PDF của
CHATLTT_V3, không tự sửa ở đây (không chắc sự thật mã hiện tại).

### Lớp 5 — `docs/MVP_OPTIMIZATION_V2/` là ảnh chụp cũ, giữ vì 1 trích dẫn

Xem `docs/MVP_OPTIMIZATION_V2/README.md`. Không rewrite toàn bộ audit (quá lớn,
rủi ro đoán sai) — đã thêm cảnh báo "đã cũ, đối chiếu lại" ở đầu README thư mục
thay vì sửa từng dòng trong 7 tệp audit.
