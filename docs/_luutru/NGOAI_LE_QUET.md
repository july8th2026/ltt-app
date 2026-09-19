# Ngoại lệ quét (`tools/quet_tai_lieu.py`)

Mỗi dòng: `CHET`/`THAY` mà máy quét bắt được nhưng KHÔNG sửa vì không chắc (Task 3
bước 3: "không chắc ⇒ ghi ngoại lệ, không đoán"). Sửa khi có bằng chứng mới; xoá
dòng khi tệp đã lưu trữ hoặc câu chữ đã sửa.

## L-E (19/09) — nhóm theo NGUYÊN NHÂN, không liệt kê từng dòng

Đã kiểm tay ~163 CHET + phần lớn THAY của cụm L-E (`superpowers/plans|specs`,
`migration`, `architecture`, `nexus`, `ANH_NOI_BO`, `AGENT_LTT`, `LTTCODE`,
`MOBILE`, `OPERATING_STANDARDIZATION`, `QUALITY_LAB`, `SCHEDULER_V1`, `LTT_CMC`,
`AI_CLEAN_REBUILD`, `VPS`, `vps_v2`, `VPS_V4`). Phát hiện: đại đa số KHÔNG phải
tham chiếu chết thật — máy quét chỉ kiểm tồn tại theo gốc `D:\LTTSTUDIOSAPP`, mà
4 loại câu dưới đây trỏ nơi khác một cách CÓ CHỦ Ý:

1. **Đường trên máy/kho khác** — `docs/ANH_NOI_BO/*` phân tích ComfyUI
   (`comfy/`, `comfy_api/`, `comfy_extras/`, `script_examples/`, `bench/*.json`)
   và dự án `E:\LTT AI` (`src/cong_gpu.py`, `ltt/chay_job.py` — CHIA_GPU_VOI_VIDEO.md
   nói thẳng "sửa dự án khác"); `docs/VPS/PHAN_TICH_VPS_PROXMOX.md` nói rõ
   `setuppromox/...` **"Trên máy B"**; `docs/ANH_NOI_BO/KE_HOACH_H37.md` §G1
   `ltt_render/scripts/gpu_check.py` là đường TRIỂN KHAI trên máy B của chính
   `render_gateway/diagnostics/gpu_check.py` (đối chiếu docstring file đó — cùng
   nội dung H37/G1, khác đường vì một bên là nguồn, một bên là bản deploy).
   `docs/nexus/*` (`src/relay_server.rs`, `src/tcp.rs`, `src/client.rs`,
   `LThbbs/`, `LTTnexus/`) trỏ kho Nexus/fork riêng, không phải monorepo này.
2. **Audit hệ thống NGOÀI** — `docs/migration/workflow_apps/*` (đường `bot/`,
   `engine/`, `utils/`, `configs/*.json` — các bot Gemini/Whisper cũ đang được
   soát để di trú, không phải mã của repo này) và
   `docs/architecture/workflow_v2_audit/*` (Windmill/Kestra/Trigger.dev —
   `backend/windmill-worker/...`, `internal-packages/run-engine/...`).
3. **Sổ quyết định (append-only, lịch sử)** — `docs/ANH_NOI_BO/DECISIONS.md`,
   `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md`, `docs/AI_CLEAN_REBUILD/*` (đã tự
   gắn nhãn `HISTORY_ONLY` trong `LEGACY_SURFACE_MATRIX.csv` — "sửa nó là viết
   lại lịch sử"), `docs/LTT_CMC/*` (`test-results/gates/<timestamp>.json` là
   bằng chứng gate MỘT LẦN, đã dọn theo vòng đời `test-results/`). Sửa các
   dòng này = viết lại một quyết định/bằng chứng đã xảy ra tại thời điểm đó.
4. **Tham chiếu xuôi trong cùng tài liệu, đã tự giải quyết** — ví dụ
   `docs/ANH_NOI_BO/PHAN_TICH_BUILD_PACK.md` §8 liệt kê `docs/DECISIONS.md` là
   "pack đòi", rồi ngay cột bên cạnh ghi "Sẽ tạo tại `docs/ANH_NOI_BO/DECISIONS.md`
   khi thi hành" (đã tạo — chính là tệp mục 3 ở trên); `docs/LTTCODE/README.md`
   nói rõ mọi đường `docs/LTTCODE/*.md`, `tools/release.ps1` nằm ở kho
   **LTTCODEAPP** (`D:\LTTCODEAPP`), không phải kho này — bản thân README đã là
   tấm biển trỏ đúng, không phải tham chiếu chết.
   `docs/superpowers/plans/*.md`, `docs/superpowers/specs/*.md` (dưới 10 ngày,
   nhiều CHET là mã ví dụ trong step-by-step của TDD hoặc đường dự kiến tạo sau
   — không sửa nội dung kế hoạch để tránh viết lại lịch sử kế hoạch).

**Đã SỬA (không thuộc 4 nhóm trên, có bằng chứng cụ thể):**
- `docs/VPS/UI_MVP_V2/00_KE_HOACH_GIAO_DIEN.md` — `tests/test_306_vps_giao_dien_mvp.py`
  → `tests/test_311_vps_giao_dien_mvp.py` (đối chiếu docstring tệp test trỏ ngược
  đúng kế hoạch này; số hiệu đổi lúc thi hành).
- `docs/system_purification/STATE.md` — cập nhật đường `reports/phase_minus_1_*`
  sau khi lưu trữ (Task 3 L-E).

**THAY `admin-mvp-v3 -> main` / `purification-v1 -> main` trong L-E — không sửa
hàng loạt:** xuất hiện ở `MOBILE/*`, `LTT_CMC/*`, `AI_CLEAN_REBUILD/*`,
`SCHEDULER_V1/00_PREFLIGHT.md`, `vps_v2/*`, `architecture/workflow_v2_audit/30_*`,
`superpowers/plans|specs/*` — toàn bộ là **tường thuật lịch sử** ("việc này chạy
trên nhánh admin-mvp-v3 lúc đó"), không phải câu khẳng định LUẬT hiện hành. Từ
điển THAY nhắm câu kiểu LUẬT ("chờ canonical integrator duyệt" — dùng như quy
tắc đang áp dụng); đổi tên nhánh trong câu tường thuật lịch sử sẽ SAI sự thật
(việc đó thật sự chạy trên `admin-mvp-v3`, không phải `main`). Không sửa.

**CHƯA rõ, chưa sửa** (2 dòng, cần chủ dự án hoặc lượt sau):
- `docs/vps_v2/ADR_INDEX.md:21`, `BASELINE.md:152`, `KNOWN_BLOCKERS.md:30`,
  `RELEASE_SCORECARD.md:3` — đều trỏ `CORE/TARGET_ARCHITECTURE.md` /
  `CORE/QUALITY_SCORECARD.md`; không tìm thấy `CORE/` ở đâu trong kho. Có thể là
  mẫu quy trình dùng chung chưa từng viết ra — cần người xác nhận trước khi sửa
  hay xoá cụm trích dẫn.
- `docs/ANH_NOI_BO/KE_HOACH_H37.md` §G2 trở đi (§373–521): các đường
  `docs/ANH_NOI_BO/BENCHMARK.md`, `EDIT_REFERENCE.md`, `PERFORMANCE.md`,
  `DOI_CHUNG_GEMINI.md`, `RUNBOOK.md` chưa từng tồn tại trong thư mục — không rõ
  là "chưa viết" (kế hoạch H37 viết 22/08, còn dở) hay "đã đổi ý không viết nữa"
  như PHAN_TICH_BUILD_PACK.md §8 đã làm với hai tệp khác.
