# Ngoại lệ máy quét tài liệu

Dòng `CHET`/`THAY` của `tools/quet_tai_lieu.py` đã được KIỂM TAY và cố ý giữ nguyên
(tệp · dòng · lý do). Mỗi làn một mục; số dòng theo SHA lúc ghi.

## L-A — `docs/` gốc, CLAUDE.md, AGENTS.md (nhánh `phien/don-tl-la`, 19/09)

Quét: `python tools/quet_tai_lieu.py $(ls docs/*.md) CLAUDE.md AGENTS.md` — 137 dòng, cả 137 thuộc bảng dưới.

| tệp | dòng | lý do |
|---|---|---|
| `CLAUDE.md` | 95, 96 | tệp runtime gitignored có chủ đích (câu cấm commit) — không phải tham chiếu vỡ |
| `docs/00_LTT_OPERATING_CONTRACT.md` | 60, 382 | dòng 60: ví dụ đường dẫn trong repo `ggml-org/llama.cpp`; dòng 382: `.claude/pha_dang_chay.json` là tệp runtime do `tools/hook_khong_dung_giua_pha.py` đọc |
| `docs/01_COPY_LEN_SERVER.md` | 22, 97 | `data/config.json` là tệp runtime gitignored trên máy chủ |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | 1866, 1905, 2072, 2088, 2103, 2762, 2764 | chuyện kể sự cố: `admin-mvp-v3` là nhánh lúc xảy ra; `tools/co_san.py` là tệp giả trong ví dụ test; `tools/video_cloud.py` là cột đo 'không có' |
| `docs/DOI_CHIEU_THUMBNAIL.md` | 18 | đường dẫn trong kho `D:\BOT GEMINI` (dòng 'Gốc (BOT GEMINI)') |
| `docs/HO_SO_HE_THONG.md` | 3, 13, 50, 51 | câu tự nói bộ sinh/test đã bị gỡ (dòng 3) — đúng sự thật |
| `docs/KE_HOACH_NOI_TIEP_2026-08-29.md` | 23, 318, 349 | ảnh chụp trạng thái 29/08 (mục CẦN XEM, đề xuất lưu trữ) — không viết lại lịch sử |
| `docs/KE_HOACH_TRIEN_KHAI.md` | 13 dòng (409…4028) | tracker: mục [x] đã xong/đã xoá có chủ đích (tách routes, gỡ build_system_profile, xoá nap-anh-xa-tinh.ps1), bản ghi `test-results/gates/` runtime, `data/config.json` runtime, đường dẫn `D:\BOT GEMINI` |
| `docs/KHAO_SAT_BOT_GEMINI.md` | 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56 | đường dẫn trong kho `D:\BOT GEMINI` (kiểm 19/09: tồn tại ở đó) |
| `docs/KIEM_KE_VA_LO_TRINH_AGENT.md` | 13 dòng (71…91) | đường dẫn trong kho `D:\BOT GEMINI` (tương đối từ `app/`; kiểm 19/09: tồn tại) |
| `docs/LTT_CLI_COMPAT_DECISIONS.md` | 103, 133 | bằng chứng `tmp/` lúc chạy, không theo dõi git |
| `docs/NHAT_KY.md` | 67 dòng (33…19222) | nhật ký sống, giữ nguyên (Logic bổ sung 1): đường dẫn/nhánh là sự thật lúc ghi; `test-results/`, `tmp/`, `secrets/` là tệp runtime |
| `docs/QUYET_DINH_NEN_TANG.md` | 135, 237, 272, 445, 457 | Q108 kể tệp đã xoá; `src/vieneu/...` là mã trong repo engine ngoài; Q123 kể nguồn gốc nhánh `main` từ `admin-mvp-v3` — đúng sự thật |
| `docs/VAN_HANH_THAT.md` | 64 | `tools/soi_lease_tien.py`/`dem_lease.py` chưa từng vào git (`git log --all` rỗng) và không có trên đĩa 19/09 — chưa rõ thay bằng gì, không đoán; hỏi chủ LLM (L-B `BO_DO_CHUAN.md` cũng trỏ) |

## Làn L-B (nhánh `phien/don-tl-lb`) — Ngoại lệ máy quét (`tools/quet_tai_lieu.py`)

Mỗi dòng: cụm CHET/THAY máy quét gắn cờ, nhưng kiểm tay xác nhận **không phải
lỗi** (hoặc chưa đủ bằng chứng để sửa mà không đoán) — lý do không sửa. Tạo
19/09 bởi làn L-B (`docs/ltt_llm_dual/`, `docs/audit_ltt_llm/`, `docs/VLM_NOI_BO/`,
`docs/PUBLIC_API/`) khi dọn Task 3 của
`docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md`.

### THAY `admin-mvp-v3` → `main` — 10 chỗ, KHÔNG sửa

Từ điển ghi "admin-mvp-v3 | main | git" cho câu văn nói **quy trình hiện hành**.
10 chỗ dưới đây không phải vậy: mỗi tệp tự khai ngày chụp/audit ở đầu tệp
(`Chụp 2026-09-11…`, `Audit tĩnh trên … 2026-09-11`, `Ảnh chụp 01/09/2026 —
không phải hiện trạng`) và câu chứa `admin-mvp-v3` mô tả **nhánh trunk lúc đó**
— đổi thành `main` sẽ SAI lịch sử (tại thời điểm chụp, trunk thật sự là
`admin-mvp-v3`, không phải `main`). Nhánh `admin-mvp-v3` đã không còn tồn tại
(`git branch -a` rỗng) nên không ai đọc nhầm là "vẫn dùng được hôm nay".

- `docs/ltt_llm_dual/00_CURRENT_BASELINE.md:23`
- `docs/ltt_llm_dual/01_MULTI_JOB_INHERITANCE.md:12`
- `docs/ltt_llm_dual/02_REQUEST_TRACE.md:3`
- `docs/ltt_llm_dual/03_GPU_RESOURCE_MAP.md:5`
- `docs/ltt_llm_dual/06_GAP_ANALYSIS.md:10` và `:29`
- `docs/ltt_llm_dual/DECISION_LOG.md:58` (quyết định TD-D1, log khoá — không sửa lời quyết định đã LOCKED)
- `docs/audit_ltt_llm/reports/08_final_acceptance.md:56`
- `docs/audit_ltt_llm/STATE.md:16`
- `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md:3`

### CHET — trích dẫn mã nguồn bên ngoài kho (không phải đường dẫn trong kho này)

Máy quét đối chiếu mọi cụm `` `a/b.ext` `` với cây LTTSTUDIOSAPP; các dòng dưới
trích dẫn tệp của **dự án khác** (vllm, llama.cpp/codex-rs, starlette, uvicorn,
sweep model card, tài liệu Anthropic) làm bằng chứng cộng đồng — đúng mục đích,
không phải lệnh chạy được trong kho này, không sửa.

- `docs/ltt_llm_dual/05_COMMUNITY_EVIDENCE.md:90` — `qwen38-mtp/sweeps/rtx-3090.md`
- `docs/ltt_llm_dual/artifacts/bench_hang_cho/SAMPLING_35_MODEL_CARD_18_09.md:89` — `codex-rs/models-manager/prompt.md`
- `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md:44,47,48` — `codex-rs/codex-api/...`, `codex-rs/core/src/client.rs`, `codex-rs/core/src/turn_metadata.rs`
- `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md:179` — `starlette/background.py`
- `docs/ltt_llm_dual/SO_LOI_DO_TAI.md:346` — `starlette/background.py`; `:1315` — `uvicorn/protocols/http/h11_impl.py`
- `docs/ltt_llm_dual/DECISION_LOG.md:956` — `vllm/v1/core/sched/scheduler.py`
- `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md:19,45,108` — `sweeps/rtx-3090.md`, `docs/gotchas.md`, `bench/quality_battery.py`, `docs/long-context.md`, `docs/quality.md`; `:284` — `qwen38-27b-rtx3090/bench/quality_battery.py`
- `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md:668` — `codex-client/src/retry.rs`; `:928` — `code.claude.com/docs/en/env-vars.md`
- `docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md:415` — `.vscode/settings.json` (ví dụ cấu hình IDE người đọc tự tạo, không phải tệp của kho); `:741` — `app/resources/ion-dist/assets/v1/...` (đường cài đặt cục bộ ví dụ của công cụ ngoài)
- `docs/PUBLIC_API/CODEX_DESKTOP_CONFIG.md:78` — `.codex/config.toml` (tệp cấu hình cục bộ của Codex Desktop trên máy người dùng, không phải của kho)

### CHET — tệp tạm/artifact lịch sử đã mất theo đúng thiết kế (scratchpad, tmp, test-results, WIP)

Đường dẫn từng tồn tại một lần trong phiên tạo báo cáo, không phải tệp sống
trong kho; giữ nguyên vì là trích dẫn bằng chứng đo đạc tại thời điểm đó.

- `docs/ltt_llm_dual/BANG_DOI_SOAT.md:86` — `scratchpad/do_cong_q_soak.py`
- `docs/ltt_llm_dual/SO_LOI_DO_TAI.md:813` — `scratchpad/do_khoa_hang_khoa.py`
- `docs/ltt_llm_dual/BAN_GIAO_PHIEN.md:19` — `test-results/gates/20260912T125202Z-8004.json`
- `docs/ltt_llm_dual/DECISION_LOG.md:155` — `.superpowers/sdd/2026-09-11-ltt-llm-dual-model/task-1.5-report.md` (worktree của phiên khác, không phải nhánh này)
- `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md:154` — `alembic/versions/2026MMDD_HHMM_public_api_requests_phien.py` (mẫu đặt tên, không phải tên tệp thật)
- `docs/audit_ltt_llm/evidence/N7_N9_SAU_KHOI_DONG_2026-09-01.md:4` — `tmp/sau_khoi_dong.json`, `tmp/sau_khoi_dong_system.json`
- `docs/PUBLIC_API/AUDIT_API_2026-08-15.md:52` — `scratchpad/repro_double_webhook.py`
- `docs/ltt_llm_dual/artifacts/NGHIEM_THU_PHUONG_AN_C_17_09.md:97` — `nt_c/kh.py`: dòng ngay trước tự
  ghi "Kịch bản trong scratchpad phiên (không commit)" — chưa từng vào kho

### CHET — mã đã bị xoá theo quyết định, tài liệu là NHẬT KÝ đã ghi ngày (log tiến độ/audit, không phải luật đang hiệu lực)

Các tệp dưới là log tiến độ/audit tự mang mốc ngày trong tên hoặc đầu tệp, mô
tả đúng cái đã làm ở thời điểm đó; mã đã đổi SAU thời điểm log (di trú sang
gói/tệp khác, hoặc bị gỡ theo quyết định chủ dự án) — không sửa lại log cũ.

- `docs/PUBLIC_API/AUDIT_GIAO_DIEN_API_2026-08-25.md:257`, `docs/PUBLIC_API/EXTENSION_PROGRESS.md:628`,
  `docs/PUBLIC_API/FULL_PLATFORM_GAP_MATRIX.md:208`, `docs/PUBLIC_API/RELEASE_READINESS_V1.md:210`,
  `docs/PUBLIC_API/PROGRESS.md:1541` — `server/routes/developer.py`: đúng tại thời điểm log (14–25/08);
  sau đó tách gói thành `server/routes/developer/` (nhiều tệp). Đã SỬA chỗ còn là quy chuẩn đang hiệu lực:
  `docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md:32` → trỏ `server/routes/developer/_chung.py`.
- `docs/PUBLIC_API/PROGRESS.md:1549` — `tools/system_profile_config.json`: đúng tại thời điểm log (Prompt 14/15);
  tính năng `ho_so_he_thong` sau đó bị gỡ hẳn theo quyết định chủ dự án (`git log` commit `e85020eb`
  "chore: go tinh nang ho_so_he_thong theo quyet dinh chu du an").
- `docs/VLM_NOI_BO/SO_DO_P2_P6.md:151` — `llm_gateway/don_dep.py`: đúng tại thời điểm đo (22/08); tệp bị
  xoá 12/09 khi `don_dep.py` + `render_gateway/nhuong_card.py` gộp thành `llm_gateway/trong_tai.py`
  (`DECISION_LOG.md` D01). Đã SỬA chỗ đang là tài liệu lộ trình sống:
  `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md:172` (thêm câu "đã bị xoá 12/09 … nay là `trong_tai.py`").
- `docs/ltt_llm_dual/artifacts/bench_hang_cho/KET_QUA_BAO_TRI_18_09.md:85` — báo cáo TỰ ghi rằng
  `llm_gateway/don_dep.py`/`render_gateway/nhuong_card.py` là "hai tệp mồ côi đã xoá khỏi kho" — đã đúng,
  không cần sửa.
- `docs/ltt_llm_dual/DECISION_LOG.md:81-82` — quyết định D01 (LOCKED) tự mô tả hai trọng tài **sắp bị**
  thay; không sửa lời quyết định đã khoá.

### CHET — số hiệu test đã quy hoạch (`check_so_test`) va chạm với test khác cùng số, không đoán tên đúng

- `docs/ltt_llm_dual/01_MULTI_JOB_INHERITANCE.md:68` — `tests/test_958_cua_dong_bo_job_planner.py`: bảng
  TỰ đánh dấu "UNFINISHED … Chưa có (và số 958 trùng trunk)" — đã đúng, test chưa từng được viết dưới tên
  này; `tests/test_958_wf_he_kieu_cong.py` hiện có là chủ đề khác (hệ kiểu cổng workflow), không phải bản
  đổi tên. Không đoán, để chủ dự án/L-A quyết có cần cấp lại số khác.
- `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md:238` — `tests/test_1512_so_luot_so_do.py`:
  mục 6.3 là kế hoạch (P2) cho thiết kế R06/R07 (12/09), test chưa được viết dưới tên này;
  `tests/test_1512_the_suy_nghi_lot.py` hiện có là chủ đề khác (thẻ `</think>` lọt ra). Không đoán.
- `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md:318` — `tests/test_12xx_phuong_an_c_hop_dong.py`: `12xx` là
  MẪU đặt tên chờ `check_so_test` cấp số thật, không phải tên tệp — không phải lỗi.
- `docs/PUBLIC_API/KERNEL_V1.md:46` — `tests/test_152_socialbot_route_flag.py`, `tests/test_51_oauth_web.py`:
  câu ngay sau ĐÃ tự ghi "cả hai đã bị xoá cùng app socialbot ngày 2026-08-25; hành vi Starlette không đổi"
  — không phải lỗi, không cần sửa.

### Đã sửa thật (không phải ngoại lệ, ghi lại để đối chiếu)

- `docs/PUBLIC_API/ARCHITECTURE_V1.md:127` — `apps/chataistudio/routes.py` → ghi chú app gỡ 09/09/2026,
  trỏ `apps/chatltt/`.
- `docs/VLM_NOI_BO/PHAN_TICH_KHOANG_TRONG.md:46` — `apps/kichban/jobs.py` → ghi chú app gỡ 25/08/2026 (Q108/Q109).
- `docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md:32` — `server/routes/developer.py` → `server/routes/developer/_chung.py`.
- `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md:172` — thêm câu `don_dep.py` đã xoá 12/09, nay là `llm_gateway/trong_tai.py`.

## Làn L-C (nhánh `phien/don-tl-lc`) — Ngoại lệ máy quét `tools/quet_tai_lieu.py`

Dòng CHET/THAY mà agent xem lại bằng tay nhưng **không sửa** vì không chắc, hoặc
vì sửa sẽ làm sai nội dung lịch sử. Mẫu: `tệp:dòng` — lý do — ai ghi, ngày.

### L-C — 2026-09-19

- `docs/APP_AUDIT/control-plane/2026-08-06/00_CHARTER_VA_HIEN_TRANG.md:44,45,47,52`,
  `01_LOGIC_VAN_HANH.md:75,76`, `03_SCORECARD.md:72,75,109,112`,
  `04_BAN_DO_CORE.md:73` — CHET trỏ `apps/prompt_ai_ommi/routes.py`,
  `apps/agent/routes.py`, `core/sheet_runner.py`,
  `core/tiktok/compliance_guard.py`, `gui/monitor_tab.py`. Đây là ảnh chụp
  đường dẫn mã THẬT TẠI THỜI ĐIỂM audit 2026-08-06 (đường dẫn app hiện đã đổi
  tên/cấu trúc; `core/` đã bị xoá hẳn 2026-08-25 — xem
  `tests/test_147_layering.py::test_nen_tang_va_app_khong_phu_thuoc_core_legacy`).
  Thư mục này đang được GIỮ (không lưu trữ) chính vì `tests/test_147` trích dẫn
  nó làm bằng chứng lịch sử cho lý do `core/` bị xoá — sửa các đường dẫn cũ
  thành đường dẫn hiện tại sẽ làm sai sự thật đã ghi nhận tại thời điểm đó.
  Không sửa. (agent L-C, 2026-09-19)
- `docs/lttstudios-website/README.md:338` — CHET trỏ
  `docs/fb-app-review-submission-plan.md` (mục "Optional PHP relay cho TikTok
  cross-machine OAuth"). Tệp đã chuyển từ lâu sang
  `docs/_luutru/fb-app-review-submission-plan.md`, nhưng đã kiểm nội dung tệp
  đó (và `docs/_luutru/lttstudios-deployment-guide.md`,
  `docs/_luutru/lttstudios-migration-plan.md`) — **không tệp nào trong kho
  chứa đoạn code mẫu PHP relay** mà dòng này hứa hẹn. Tham chiếu chết thật,
  nhưng không rõ đích đúng là gì (có thể đoạn code mẫu chưa từng được commit,
  hoặc đã mất khi tệp gốc bị dọn ở một đợt trước 2026-09). Không đoán/không
  tự viết lại; cần chủ dự án xác nhận có còn dùng PHP relay hay bỏ hẳn đoạn
  này. (agent L-C, 2026-09-19)

## Làn L-D (nhánh `phien/don-tl-ld`) — Ngoại lệ máy quét `tools/quet_tai_lieu.py`

Danh sách CHET/THAY đã xem lại bằng `git grep`/đọc nội dung thật (yêu cầu
"chống dọn nhầm") và xác định KHÔNG phải lỗi cần sửa — máy quét không phân biệt
được các trường hợp dưới đây với tham chiếu vỡ thật. Không đoán khi chưa xem —
mỗi mục ghi bằng chứng đã kiểm.

### Làn L-D (`docs/CHATLTT`, `docs/CHATLTT_V3`, `docs/LTT_VOICE`,
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

#### Lớp 1 — Tên nhánh lịch sử `admin-mvp-v3` (toàn bộ 101 dòng THAY của cụm)

Mọi dòng `THAY … admin-mvp-v3 -> main` trong cụm L-D nằm trong văn bản có ngày/
tên nhánh cụ thể ("Ngày: 2026-08-29. Nhánh: admin-mvp-v3", "gốc chung với trunk
768b1dba (admin-mvp-v3)") — ghi chép ĐÚNG tên nhánh tại thời điểm viết, trước khi
nó gộp vào `main`. Từ điển `admin-mvp-v3 -> main` đúng cho câu hướng dẫn HIỆN
HÀNH ("chờ admin-mvp-v3 để deploy"), không đúng cho câu tường thuật lịch sử đã có
ngày tháng đi kèm — sửa sẽ làm sai lịch sử. Đã kiểm mẫu ở `admin_mvp_v3/`,
`CHATLTT/STATE.md`, `CHATLTT_V3/STATE.md`, `LTT_VOICE/*`, `VIDEO_AI_V2/DECISIONS.md`,
`VIDEO_AI_V2/LEGACY_INVENTORY.md`, `auto_scan_video*/`. Không sửa.

#### Lớp 2 — Đường dẫn thuộc kho/dự án tham chiếu NGOÀI `D:\LTTSTUDIOSAPP`

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

#### Lớp 3 — Tệp cục bộ/không commit/đã xoay vòng

`test-results/gates/<timestamp>.json` (bản ghi gate máy sinh, xoay vòng — không
giữ vĩnh viễn), `.claude/launch.json`, `.claude/settings.local.json`
(cấu hình máy cục bộ, không commit), `.superpowers/sdd/…/progress.md`
(scratch phiên `superpowers`, không commit), `tmp/*.json` (tệp tạm), `.ltt/chatltt/state.json`
(runtime state), `.github/workflows/gate.yml` (workflow thật ở kho là
`.github/workflows/gate-quick.yml` — tên khác lúc viết `LTT_VOICE/UPGRADE_98/06_BLOCKERS.md`,
CẦN XEM nếu phiên sau đọc kỹ blocker đó) — phần lớn còn lại là tài liệu
ĐÚNG mô tả một tệp từng tồn tại tại máy/thời điểm viết, không phải lỗi.

#### Lớp 4 — Kế hoạch mô tả tên tệp DỰ KIẾN, khác tên thật lúc triển khai

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

#### Lớp 5 — `docs/MVP_OPTIMIZATION_V2/` là ảnh chụp cũ, giữ vì 1 trích dẫn

Xem `docs/MVP_OPTIMIZATION_V2/README.md`. Không rewrite toàn bộ audit (quá lớn,
rủi ro đoán sai) — đã thêm cảnh báo "đã cũ, đối chiếu lại" ở đầu README thư mục
thay vì sửa từng dòng trong 7 tệp audit.

## Làn L-E (nhánh `phien/don-tl-le`) — Ngoại lệ quét (`tools/quet_tai_lieu.py`)

Mỗi dòng: `CHET`/`THAY` mà máy quét bắt được nhưng KHÔNG sửa vì không chắc (Task 3
bước 3: "không chắc ⇒ ghi ngoại lệ, không đoán"). Sửa khi có bằng chứng mới; xoá
dòng khi tệp đã lưu trữ hoặc câu chữ đã sửa.

### L-E (19/09) — nhóm theo NGUYÊN NHÂN, không liệt kê từng dòng

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

**Con trỏ NGOÀI CỤM L-E — liệt kê cho điều phối/L-C, KHÔNG tự sửa** (luật chống
dọn nhầm mục 2):
- `docs/developer_portal_mvp_ui/06_BROWSER_QA.md:79` và
  `docs/developer_portal_mvp_ui/09_FINAL_MVP_REPORT.md:116` — cả hai trỏ
  `docs/ui_stabilization/`. Thư mục đó đã lưu trữ 19/09 (L-E) sang
  `docs/_luutru/2026-09/ui_stabilization/`. `developer_portal_mvp_ui/` thuộc
  cụm L-C — nhờ L-C hoặc điều phối sửa 2 dòng này khi gộp.

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

## Bảng máy — `tools/quet_tai_lieu.py` đọc (sinh 19/09 bởi làn tích hợp)

Mỗi dòng: tệp · mẫu máy quét gắn cờ (glob, khớp CẢ HAI thì bỏ) · lý do. Sinh từ lượt quét sau
khi đã sửa mọi con trỏ sửa được; lý do chi tiết ở mục của từng làn phía trên. Mẫu CHÍNH XÁC
theo từng tệp (không glob rộng) ⇒ tham chiếu vỡ MỚI trong cùng tệp vẫn bị bắt. Sửa được câu nào
thì xoá dòng tương ứng.

| tệp | mẫu | lý do |
|---|---|---|
| `docs/NHAT_KY.md` | * | L-A: nhật ký sống, chỉ thêm — đường dẫn/nhánh là sự thật lúc ghi |
| `CLAUDE.md` | `cloudflare/config.yml` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `CLAUDE.md` | `data/config.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/00_LTT_OPERATING_CONTRACT.md` | `.claude/pha_dang_chay.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/00_LTT_OPERATING_CONTRACT.md` | `tools/server/README.md` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/01_COPY_LEN_SERVER.md` | `data/config.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/AGENT_LTT/03_TOOLSPEC_KHI_PORT.md` | `app/models/image_model_registry.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AGENT_LTT/03_TOOLSPEC_KHI_PORT.md` | `app/models/video_model_registry.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AGENT_LTT/03_TOOLSPEC_KHI_PORT.md` | `app/modules/seedance_video/face_detect.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/ADMIN_V3_RECONCILIATION.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/AI_CLEAN_REBUILD/ADMIN_V3_RECONCILIATION.md` | `codex_sidecar/server.py` | L-E: mã trong kho đã xoá ở Pha 07 (`ac46d371`) |
| `docs/AI_CLEAN_REBUILD/ADMIN_V3_RECONCILIATION.md` | `docs/OPERATING_STANDARDIZATION/FINAL_REPORT.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `apps/chataistudio` | L-E: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `apps/chataistudio/luong_chat.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `apps/chataistudio/routes.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `codex_sidecar/runtime.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `platform_core/image_gen/dich_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `scratchpad/doi_chung_pha04.py` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `tools/doi_chung_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md` | `tools/import_api_keys_from_botgemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/DELETE_DEPENDENCY_GRAPH.md` | `apps/chataistudio` | L-E: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/AI_CLEAN_REBUILD/DELETE_DEPENDENCY_GRAPH.md` | `platform_core/image_gen/dich_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/FINAL_AI_CONTRACT.md` | `LTT_AI_CLEAN_REBUILD_CLAUDE_PACK_V2/policies/HARD_DELETE_POLICY.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/MIGRATION_MAP.md` | `apps/chataistudio` | L-E: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/AI_CLEAN_REBUILD/MIGRATION_MAP.md` | `tools/doi_chung_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/PHA13_SO_TAY.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/AI_CLEAN_REBUILD/PHA14_DON_NHANH_REMOTE.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/AI_CLEAN_REBUILD/PHA15_BAO_CAO_NEN_KHO.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/AI_CLEAN_REBUILD/PHA15_BAO_CAO_NEN_KHO.md` | `apps/chataistudio` | L-E: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/AI_CLEAN_REBUILD/PHA15_BAO_CAO_NEN_KHO.md` | `platform_core/image_gen/dich_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/PHA15_BAO_CAO_NEN_KHO.md` | `tools/doi_chung_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/PHA15_BAO_CAO_NEN_KHO.md` | `tools/import_api_keys_from_botgemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/PRODUCT_DEPENDENCY_MAP.md` | `apps/chataistudio` | L-E: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/AI_CLEAN_REBUILD/PRODUCT_DEPENDENCY_MAP.md` | `apps/chataistudio/sidecar_client.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/PRODUCT_DEPENDENCY_MAP.md` | `codex_sidecar/runtime.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/AI_CLEAN_REBUILD/PRODUCT_DEPENDENCY_MAP.md` | `codex_sidecar/server.py` | L-E: mã trong kho đã xoá ở Pha 07 (`ac46d371`) |
| `docs/AI_CLEAN_REBUILD/W2_LOCAL_WORKTREE_CLEANUP.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/ANH_NOI_BO/CHAM_DIEM.md` | `script_examples/websockets_api_example.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/CHAM_DIEM.md` | `scripts/live_check_control_b.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/CHIA_GPU_VOI_VIDEO.md` | `comfy/cli_args.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/CHIA_GPU_VOI_VIDEO.md` | `docs/23_Queue_And_Scheduler/_README.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/CHIA_GPU_VOI_VIDEO.md` | `ltt/chay_job.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/CHIA_GPU_VOI_VIDEO.md` | `src/cong_gpu.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `bench/EN_s30.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `bench/G5b_edit_1anh_1mp.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `comfy/cli_args.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `comfy_api/latest/_io.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `llm_gateway/don_dep.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `logs/do_ck2.ps1` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `logs/do_ck4.ps1` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `logs/thu_trongtai.ps1` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `ltt/chay_job.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `render_gateway/nhuong_card.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `script_examples/websockets_api_example.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `tests/test_251_dich_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `tests/test_255_doi_chung_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `tests/test_278_nhuong_card.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `tools/build_system_profile.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DECISIONS.md` | `tools/doi_chung_gemini.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DE_XUAT_CHU_TIENG_VIET.md` | `platform_core/image_gen/ghep_chu.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/DE_XUAT_NOI_VAO_APP.md` | `platform_core/image_gen/sinh_anh.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `bench/baseline.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `configs/profile_fast.yaml` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `configs/profile_quality.yaml` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `docs/ANH_NOI_BO/BENCHMARK.md` | tài liệu dự kiến G4–G11 chưa từng viết (chú thích tại chỗ §11) |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `docs/ANH_NOI_BO/DOI_CHUNG_GEMINI.md` | tài liệu dự kiến G4–G11 chưa từng viết (chú thích tại chỗ §11) |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `docs/ANH_NOI_BO/EDIT_REFERENCE.md` | tài liệu dự kiến G4–G11 chưa từng viết (chú thích tại chỗ §11) |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `docs/ANH_NOI_BO/PERFORMANCE.md` | tài liệu dự kiến G4–G11 chưa từng viết (chú thích tại chỗ §11) |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `docs/ANH_NOI_BO/RUNBOOK.md` | tài liệu dự kiến G4–G11 chưa từng viết (chú thích tại chỗ §11) |
| `docs/ANH_NOI_BO/KE_HOACH_H37.md` | `ltt_render/scripts/gpu_check.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `bench/G3_baseline.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `bench/G3_do_phan_giai.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `comfy_api/latest/_io.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `configs/profile_quality.yaml` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `docs/ANH_NOI_BO/BENCHMARK.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `docs/ANH_NOI_BO/EDIT_REFERENCE.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `docs/ANH_NOI_BO/PERFORMANCE.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `scripts/deploy_render_gateway.ps1` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `scripts/live_check_control_b.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` | `tests/test_246_provider_local.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/PHAN_TICH_BUILD_PACK.md` | `comfy_extras/nodes_flux.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/PHAN_TICH_BUILD_PACK.md` | `docs/DECISIONS.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/ANH_NOI_BO/PHAN_TICH_BUILD_PACK.md` | `docs/SYSTEM_AUDIT.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/APP_AUDIT/control-plane/2026-08-06/00_CHARTER_VA_HIEN_TRANG.md` | `apps/agent/routes.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/00_CHARTER_VA_HIEN_TRANG.md` | `apps/prompt_ai_ommi/routes.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/00_CHARTER_VA_HIEN_TRANG.md` | `core/sheet_runner.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/00_CHARTER_VA_HIEN_TRANG.md` | `core/tiktok/compliance_guard.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/01_LOGIC_VAN_HANH.md` | `apps/agent/routes.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/01_LOGIC_VAN_HANH.md` | `apps/prompt_ai_ommi/routes.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/03_SCORECARD.md` | `apps/agent/routes.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/03_SCORECARD.md` | `prompt_ai_ommi/routes.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/APP_AUDIT/control-plane/2026-08-06/04_BAN_DO_CORE.md` | `gui/monitor_tab.py` | L-C: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-C |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | `admin-mvp-v3` | L-A: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | `apps/chataistudio` | L-A: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | `tools/co_san.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | `tools/video_cloud.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` | `.ltt/chatltt/state.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` | `apps/chataistudio` | L-D: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` | `packages/core/src/types/message.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` | `templates/PHASE_REPORT_TEMPLATE.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/STATE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `api/server/routes/agents/index.js` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `client/package.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `e2e/setup/fake-model.js` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `e2e/specs/a11y.spec.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `packages/api/src/stream/GenerationJobManager.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `packages/api/src/types/events.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `packages/data-schemas/package.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/01_librechat_tham_chieu.md` | `packages/data-schemas/src/schema/message.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT/reports/02_runtime_noi_bo.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT/reports/02_runtime_noi_bo.md` | `test-results/gates/20260902T175553Z-19724.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/CHATLTT/reports/04_anh_noi_bo.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT/reports/05_tieng_noi_bo.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT/reports/10_ux.md` | `e2e/specs/a11y.spec.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/00_KE_HOACH_V3.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT_V3/00_KE_HOACH_V3.md` | `artifacts/01_ket_qua.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/00_KE_HOACH_V3.md` | `docs/function-calling.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/00_REFERENCE_MATRIX.md` | `docs/function-calling.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/00_SOURCE_TRUTH.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT_V3/06_KE_HOACH_P06.md` | `apps/chataistudio` | L-D: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/CHATLTT_V3/06_KE_HOACH_P06.md` | `apps/chataistudio/features.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/09_PLAN_TONG_LAP_GHEP.md` | `mem0/configs/prompts.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/10_KE_HOACH_B4_GHI_NHO.md` | `backend/open_webui/models/memories.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/10_KE_HOACH_B4_GHI_NHO.md` | `mem0/configs/prompts.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/11_KE_HOACH_P09_UX.md` | `packages/core/src/types/message.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/12_KE_HOACH_B5_DU_AN.md` | `LibreChat/packages/data-schemas/src/schema/chatProject.ts` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/13_KE_HOACH_B6_NGHIEN_CUU.md` | `gpt_researcher/retrievers/base.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/14_KE_HOACH_P07_AGENTS_SKILLS.md` | `services/skill.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/14_KE_HOACH_P07_AGENTS_SKILLS.md` | `services/tac_nhan.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/CHATLTT_V3/STATE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/CHATLTT_V3/STATE.md` | `test-results/gates/20260905T052942Z-17052.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/CHATLTT_V3/STATE.md` | `tmp/kiem_gui/bao_cao.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/CHATLTT_V3/STATE.md` | `tools/video_cloud.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/DOI_CHIEU_THUMBNAIL.md` | `app/models/image_model_registry.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/DOI_CHIEU_THUMBNAIL.md` | `static/js/modules/thumbnail-api.js` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/HO_SO_HE_THONG.md` | `tests/test_177_system_profile.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/HO_SO_HE_THONG.md` | `tools/build_system_profile.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/HO_SO_HE_THONG.md` | `tools/system_profile_config.json` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `app/modules/seedance_video/cost.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `apps/agent/routes.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `apps/prompt_ai_ommi/routes.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `data/config.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `server/routes/developer.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `test-results/gates/20260906T163550Z-23388.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `test-results/gates/20260911T235957Z-25548.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `test-results/gates/20260915T014235Z-22516.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `tools/build_system_profile.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `tools/import_api_keys_from_botgemini.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `tools/system_profile_config.json` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KE_HOACH_TRIEN_KHAI.md` | `tools/vps_gateway/nap-anh-xa-tinh.ps1` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/models/job.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/models/user.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/modules/seedance_video/cost.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/services/job_queue.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/services/job_store.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/services/quota_guard.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/services/r2_config.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/services/role_groups.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/services/scheduler.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/services/workspace_policy.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/storage/artifact_store.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/KHAO_SAT_BOT_GEMINI.md` | `app/storage/job_store.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/LTTCODE/README.md` | `data/lttcode_releases.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTTCODE/README.md` | `docs/LTTCODE/DANH_MUC_CONG_VIEC.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/LTTCODE/README.md` | `docs/LTTCODE/MASTER_IMPLEMENTATION_PLAN.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/LTTCODE/README.md` | `docs/LTTCODE/STATE.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/LTTCODE/README.md` | `docs/LTTCODE/specs/2026-09-16-updater-kenh-phat-hanh-design.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/LTTCODE/README.md` | `tools/release.ps1` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/LTT_CLI_COMPAT_DECISIONS.md` | `tmp/kiem_cli_van_hanh/codex-manual.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CLI_COMPAT_DECISIONS.md` | `tmp/kiem_cli_van_hanh/prod.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/CLEANUP_LEDGER.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_CMC/CLEANUP_LEDGER.md` | `test-results/gates/20260912T155432Z-20964.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/CMC_SYNC_BARRIER.md` | `test-results/gates/20260911T235957Z-25548.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/DUPLICATES.md` | `.merge_tam/goc.py` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/DUPLICATES.md` | `.merge_tam/ho.py` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/FINAL_REPORT.md` | `test-results/gates/20260912T125202Z-8004.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/FINAL_REPORT.md` | `test-results/gates/20260912T155432Z-20964.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/HANDOFF_LLM_DUAL.md` | `test-results/gates/20260911T235957Z-25548.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/INVENTORY.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_CMC/RECONCILIATION.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_CMC/STATE.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_CMC/STATE.md` | `test-results/gates/20260911T235957Z-25548.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_CMC/STATE.md` | `test-results/gates/20260912T155432Z-20964.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` | `apps/web_stream.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` | `docs/Deploy.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` | `src/vieneu/_v3_turbo_engine/inference_v3_turbo.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` | `src/vieneu/_v3_turbo_engine/onnx_runtime_lite.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/AUTONOMOUS_AUDIT/00_RUNTIME_TRUTH.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/AUTONOMOUS_AUDIT/01_RELEASE_DRIFT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/AUTONOMOUS_RUN/01_RA_SOAT_HIEN_TRANG.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/AUTONOMOUS_RUN/VOICE_MVP_AUTONOMOUS_FINAL_REPORT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/AUTONOMOUS_RUN/VOICE_MVP_AUTONOMOUS_FINAL_REPORT.md` | `tests/test_394_ltt_voice_nghe_thu.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/GUI_DECISION_LOCK.md` | `apps/ltt_voice/voice.js` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/GUI_DOI_SOAT_VA_PLAN_V2.md` | `scripts/kiem_dung_db.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/GUI_MASTER_PLAN.md` | `apps/ltt_voice/catalog.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/GUI_MASTER_PLAN.md` | `tests/test_5xx_catalog.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/GUI_VOICE_CATALOG_CONTRACT.md` | `apps/ltt_voice/catalog.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/GUI_VOICE_CATALOG_CONTRACT.md` | `tests/test_5xx_catalog.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/HOP_NHAT/TANG1_RC1.md` | `.superpowers/sdd/2026-09-11-ltt-voice-rc1/progress.md` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/HOP_NHAT/TANG1_RC1.md` | `.superpowers/sdd/2026-09-11-ltt-voice-rc1/tang1-e2e-report.md` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/HOP_NHAT/TANG1_RC1.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/HOP_NHAT/TANG1_RC1.md` | `apps/chataistudio` | L-D: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/LTT_VOICE/HOP_NHAT/TANG1_RC1.md` | `test-results/gates/20260911T142721Z-21580.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/HOP_NHAT/TANG1_RC1.md` | `test-results/gates/20260911T183256Z-19848.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/HOP_NHAT/TANG2_RC1.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/KHO_GIONG/00_KIEM_KE.md` | `tmp/kho_giong_cu.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/KHO_GIONG/00_KIEM_KE.md` | `tmp/nhap_kho_giong_cu.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/NGUON_CHAN_LY.md` | `sea_g2p/g2p.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/NGUON_CHAN_LY.md` | `tmp/kho_giong_cu.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/NGUON_CHAN_LY.md` | `tmp/nhap_kho_giong_cu.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/NGUON_CHAN_LY.md` | `vieneu_utils/phonemize_text.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/README.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/UPGRADE_98/00_BASELINE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/UPGRADE_98/01_SCORECARD_BASELINE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/UPGRADE_98/03_RESEARCH_REGISTRY.md` | `apps/gradio_main.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/UPGRADE_98/04_ACTIVE_WAVE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/UPGRADE_98/06_BLOCKERS.md` | `.claude/settings.local.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/LTT_VOICE/UPGRADE_98/06_BLOCKERS.md` | `.github/workflows/gate.yml` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/UPGRADE_98/06_BLOCKERS.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/UPGRADE_98/07_CHANGE_LEDGER.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/UPGRADE_98/07_CHANGE_LEDGER.md` | `apps/chataistudio` | L-D: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/LTT_VOICE/UPGRADE_98/07_CHANGE_LEDGER.md` | `tools/giu_may_b.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/UPGRADE_98/ACTIVE_WRITER.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/VIRAL_VOICE_AUDIT_2026-09-07.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/VIRAL_VOICE_AUDIT_2026-09-07.md` | `docs/LTT_VOICE/BENCHMARK_VI_EN.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/VIRAL_VOICE_AUDIT_2026-09-07.md` | `license_server/dong_bo_11labs.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` | `apps/ltt_voice/routes.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` | `routes/_p_chua_xay.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` | `specs/FEATURE_MATRIX.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` | `specs/VISUAL_REFERENCE_NOTES.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` | `vieneu/assets/voices_v3_turbo.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MOBILE/00_KE_HOACH.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/MOBILE/00_KE_HOACH.md` | `docs/MOBILE/REAL_DEVICE_CHECKLIST.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/MOBILE/00_KE_HOACH.md` | `platform_core/media_transport.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/MOBILE/06_EDITOR.md` | `dist/esm/index.js` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/MOBILE/08_BAO_CAO.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/MOBILE/CHECKPOINT.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/MOBILE/README.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md` | `apps/chataistudio` | L-D: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md` | `apps/chataistudio/routes.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md` | `core/settings.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md` | `data/config.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md` | `server/routes/developer.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md` | `tests/test_152_socialbot_route_flag.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/05_MODULE_FILE_CHANGE_LOCALITY.md` | `server/routes/developer.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/06_RUNTIME_RELIABILITY_AUDIT.md` | `apps/chataistudio` | L-D: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/MVP_OPTIMIZATION_V2/07_SECURITY_TENANT_PRIVACY_AUDIT.md` | `data/config.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/MVP_OPTIMIZATION_V2/08_DATA_CONFIG_AUTHORITY_AUDIT.md` | `data/config.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/MVP_OPTIMIZATION_V2/11_MASTER_PLAN.md` | `server/routes/developer.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/15_FINAL_MVP_AUDIT.md` | `server/routes/developer.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/LO_TRINH_CHI_TIET.md` | `server/routes/developer.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/LO_TRINH_CHI_TIET.md` | `templates/HUMAN_DECISIONS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/MVP_OPTIMIZATION_V2/README.md` | `apps/chataistudio` | L-D: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/MVP_OPTIMIZATION_V2/README.md` | `server/routes/developer.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/OPERATING_STANDARDIZATION/GATE_COMPONENT_MAP.md` | `mot/duong/khong/ton/tai.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/OPERATING_STANDARDIZATION/GATE_COMPONENT_MAP.md` | `tests/fixtures/x.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/OPERATING_STANDARDIZATION/README.md` | `mot/duong/khong/ton/tai.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/OPERATING_STANDARDIZATION/README.md` | `tests/fixtures/x.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/PUBLIC_API/ARCHITECTURE_V1.md` | `apps/chataistudio` | L-B: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/PUBLIC_API/ARCHITECTURE_V1.md` | `apps/chataistudio/routes.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/AUDIT_API_2026-08-15.md` | `scratchpad/repro_double_webhook.py` | L-B: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/PUBLIC_API/AUDIT_GIAO_DIEN_API_2026-08-25.md` | `server/routes/developer.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/CODEX_DESKTOP_CONFIG.md` | `.codex/config.toml` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/EXTENSION_PROGRESS.md` | `server/routes/developer.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/FULL_PLATFORM_GAP_MATRIX.md` | `server/routes/developer.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md` | `.vscode/settings.json` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/HUONG_DAN_CAM_CLI.md` | `app/resources/ion-dist/assets/v1/ce459c687-CEBp0mVy.js` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/KERNEL_V1.md` | `tests/test_152_socialbot_route_flag.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/KERNEL_V1.md` | `tests/test_51_oauth_web.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/PROGRESS.md` | `apps/chataistudio` | L-B: tên app cũ trong kế hoạch/audit có ngày (app đổi tên `apps/chatltt/`) |
| `docs/PUBLIC_API/PROGRESS.md` | `server/routes/developer.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/PROGRESS.md` | `tools/system_profile_config.json` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/PUBLIC_API/RELEASE_READINESS_V1.md` | `server/routes/developer.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/QUYET_DINH_NEN_TANG.md` | `admin-mvp-v3` | L-A: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/QUYET_DINH_NEN_TANG.md` | `data/config.json` | L-A: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/QUYET_DINH_NEN_TANG.md` | `src/vieneu/v3_turbo_serve/cudagraph.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/QUYET_DINH_NEN_TANG.md` | `src/vieneu/v3_turbo_serve/engine.py` | L-A: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-A |
| `docs/SCHEDULER_V1/00_PREFLIGHT.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/SCHEDULER_V1/FINAL_REPORT.md` | `test-results/gates/20260911T084027Z-25272.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/VIDEO_AI_V2/CHAM_DIEM_WANGP_VS_SEEDANCE.md` | `apps/lttvideo/ho_so.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/CHUOI_PROMPT_VA_MEDIA.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/CHUOI_PROMPT_VA_MEDIA.md` | `models/wan/modules/t5.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DECISIONS.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/VIDEO_AI_V2/DECISIONS.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DECISIONS.md` | `docs/CLI.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DECISIONS.md` | `docs/VIDEO_AI/PROJECT_STATE.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DEEPY_UNKNOWN_GAPS.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DEEPY_UNKNOWN_GAPS.md` | `docs/MODELS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DEEPY_UNKNOWN_GAPS.md` | `shared/api.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DEEPY_UNKNOWN_GAPS.md` | `shared/mcp_server.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DEEPY_UNKNOWN_GAPS.md` | `wangp-agent/SKILL.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DEEPY_UNKNOWN_GAPS.md` | `wangp-agent/agents/openai.yaml` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DU_LIEU_DA_DO.md` | `defaults/t2v_2_2.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DU_LIEU_DA_DO.md` | `models/_settings.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/DU_LIEU_DA_DO.md` | `shared/prompt_enhancer/qwen35_vl.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/FINAL_IMPLEMENTATION_PLAN.md` | `platform_core/wangp_client.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/FINAL_MINIMAL_LTT_WANGP_ARCHITECTURE.md` | `shared/api.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/LEGACY_INVENTORY.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/VIDEO_AI_V2/LEGACY_INVENTORY.md` | `apps/lttvideo/gia.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/LEGACY_INVENTORY.md` | `workflows/video_wan2_2_14B_fun_control.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/LEGACY_INVENTORY.md` | `workflows/video_wan2_2_14B_i2v.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/LEGACY_INVENTORY.md` | `workflows/video_wan2_2_14B_t2v.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_KET_QUA_DO.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_KE_HOACH_THUC_THI.md` | `defaults/t2v_2_2.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_KE_HOACH_THUC_THI.md` | `tools/video_nap_model.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_KIEN_TRUC_XAY_DUNG.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_KIEN_TRUC_XAY_DUNG.md` | `docs/CLI.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_KIEN_TRUC_XAY_DUNG.md` | `platform_core/video_gen/ngan_sach.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_TRIEN_KHAI_THEO_WANGP.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` | `docs/CLI.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` | `docs/DEEPY.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` | `docs/PLUGINS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/P01_UPSTREAM_PIN.md` | `wangp-agent/SKILL.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `docs/CLI.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `docs/MODELS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `docs/SETTINGS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `docs/SPATIAL_UPSAMPLERS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `docs/TEMPORAL_UPSAMPLERS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `ho_so_data/ltt.video.chuan.v1.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `models/_settings.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_SUA_LAI_THEO_WANGP.md` | `scratchpad/doi_chieu_ho_so.py` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/VIDEO_AI_V2/PLAN_TOAN_DIEN_THEO_TAI_LIEU_WANGP.md` | `models/_settings.json` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `apps/lttvideo/chon_model.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `apps/lttvideo/tables.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `apps/lttvideo/wangp_client.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `shared/prompt_enhancer/qwen35_vl.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `tests/test_728_lttvideo_lich_su.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `tests/test_729_lttvideo_chon_model.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V1_CHI_TIET.md` | `tools/video_cloud.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V2_2_GIA_LAP_TRUOC.md` | `apps/lttvideo/chon_model.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V2_2_GIA_LAP_TRUOC.md` | `apps/lttvideo/ho_so.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V2_2_GIA_LAP_TRUOC.md` | `apps/lttvideo/wangp_client.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V2_2_GIA_LAP_TRUOC.md` | `scratchpad/wangp_src/docs_API.md` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/VIDEO_AI_V2/PLAN_V2_2_GIA_LAP_TRUOC.md` | `tests/test_743_gui_gallery.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PLAN_V2_2_GIA_LAP_TRUOC.md` | `tests/test_744_ban_ghi.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/PROJECT_STATE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/VIDEO_AI_V2/PROJECT_STATE.md` | `test-results/gates/20260906T061946Z-6764.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/VIDEO_AI_V2/PROJECT_STATE.md` | `test-results/gates/20260907T010725Z-20212.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `apps/lttvideo/ho_so.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `docs/DEEPY.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `platform_core/video_gen/cloud_api.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `platform_core/wangp_client.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `tools/video_cloud.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `tools/video_theo_doi.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` | `wangp-agent/SKILL.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/TAI_NGUYEN_VA_CACH_DUNG_LAI.md` | `apps/lttvideo/wangp_client.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/TAI_NGUYEN_VA_CACH_DUNG_LAI.md` | `platform_core/video_gen/cloud_api.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/TAI_NGUYEN_VA_CACH_DUNG_LAI.md` | `shared/qtypes/gguf.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/TAI_NGUYEN_VA_CACH_DUNG_LAI.md` | `tools/video_cloud.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `docs/API.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `docs/CLI.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `docs/DEEPY.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `docs/MODELS.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `shared/api.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `shared/api_cli.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `shared/api_webui.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `shared/mcp_server.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_ARCHITECTURE_EXTRACTION.md` | `shared/utils/files_locator.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_VS_LTT_RECONCILIATION.md` | `shared/api.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VIDEO_AI_V2/WANGP_VS_LTT_RECONCILIATION.md` | `video_gen/ngan_sach.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/VLM_NOI_BO/LO_TRINH_API_CLI.md` | `deploy chép cả cây` | L-B: trích dẫn/audit có ngày |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `bench/quality_battery.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `docs/gotchas.md` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `docs/long-context.md` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `docs/quality.md` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `llm_gateway/don_dep.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `qwen38-27b-rtx3090/bench/quality_battery.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `render_gateway/nhuong_card.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/LO_TRINH_THI_HANH.md` | `sweeps/rtx-3090.md` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md` | `code.claude.com/docs/en/env-vars.md` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md` | `codex-client/src/retry.rs` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/PHAN_TICH_KHOANG_TRONG.md` | `apps/kichban/jobs.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VLM_NOI_BO/SO_DO_P2_P6.md` | `llm_gateway/don_dep.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/VPS/PHAN_TICH_VPS_PROXMOX.md` | `setuppromox/KIEN-TRUC-GATEWAY.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/VPS/README.md` | `setuppromox/KIEN-TRUC-GATEWAY.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/admin_mvp_v3/00_KE_HOACH_TRIEN_KHAI.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/admin_mvp_v3/01_LIVE_EVIDENCE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/admin_mvp_v3/20_FINAL_MVP_REPORT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/admin_mvp_v3/25_DEPLOY_VA_KIEM_URL_CONG_KHAI.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/admin_mvp_v3/README.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/architecture/README.md` | `scratchpad/do_kho.py` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/architecture/workflow_v2_audit/01_CURRENT_LTT_ARCHITECTURE.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/architecture/workflow_v2_audit/03_REPOSITORY_MANIFEST.md` | `scratchpad/do_kho.py` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/architecture/workflow_v2_audit/07_08_KESTRA_WINDMILL_AUDIT.md` | `backend/windmill-worker/src/worker_flow.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/architecture/workflow_v2_audit/09_TRIGGER_DEV_AUDIT.md` | `internal-packages/run-engine/README.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/architecture/workflow_v2_audit/27_29_DI_TRU_LO_TRINH_RUI_RO.md` | `deploy chép cả cây` | L-E: trích dẫn/audit có ngày |
| `docs/architecture/workflow_v2_audit/30_QUYET_DINH_KIEN_TRUC_CUOI_CUNG.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/audit_ltt_llm/STATE.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/audit_ltt_llm/evidence/N7_N9_SAU_KHOI_DONG_2026-09-01.md` | `tmp/sau_khoi_dong.json` | L-B: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/audit_ltt_llm/evidence/N7_N9_SAU_KHOI_DONG_2026-09-01.md` | `tmp/sau_khoi_dong_system.json` | L-B: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/audit_ltt_llm/reports/08_final_acceptance.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video/CAPABILITY_MATRIX.md` | `nerf_engine/stages/audio.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/CAPABILITY_MATRIX.md` | `nerf_engine/stages/ffmpeg_edit.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/CAPABILITY_MATRIX.md` | `nerf_engine/stages/ffmpeg_edit_cutonly.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/CAPABILITY_MATRIX.md` | `stages/audio.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/CAPABILITY_MATRIX.md` | `utils/gdrive.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/CAPABILITY_MATRIX.md` | `utils/gsheets.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | `Bot_PausePipeline/engine/stt.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | `Bot_Whisper_FULL/engine/stt.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | `DUNGVIDEO-FULL/engine/stt.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | `nerf_engine/stages/ffmpeg_edit.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | `utils/gdrive.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | `utils/gsheets.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/MVP_CONTRACT.md` | `nerf_engine/stages/yolo_reframe.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/README.md` | `reports/NN_REPORT.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/README.md` | `utils/gsheets.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/RISK_REGISTER.md` | `reports/NN_REPORT.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/STATE.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video/STATE.md` | `nerf_engine/stages/audio.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/STATE.md` | `nerf_engine/stages/ffmpeg_edit.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/STATE.md` | `nerf_engine/stages/ffmpeg_edit_cutonly.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/STATE.md` | `prompts/02_MVP_PRODUCT_CONTRACT_FREEZE.md` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/reports/00_REPORT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video/reports/01_REPORT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video/reports/01_REPORT.md` | `tools/check_cay_chinh.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/reports/02_REPORT.md` | `Bot_PausePipeline/engine/anchor_matcher.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/reports/08_REPORT.md` | `nerf_engine/stages/audio.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/reports/14_REPORT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video/reports/15_REPORT.md` | `DUNGVIDEO-FULL/engine/assemble.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video/reports/20_REPORT.md` | `.claude/launch.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/auto_scan_video_v4/CAPABILITY_INVENTORY_V4.md` | `nerf_engine/stages/scene_detect.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video_v4/STATE_V4.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video_v4/STATE_V4.md` | `test-results/gates/20260905T060709Z-19316.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/auto_scan_video_v4/reports/00_REPORT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video_v4/reports/00_REPORT.md` | `test-results/gates/20260902T174701Z-11816.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/auto_scan_video_v4/reports/23_REPORT.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video_v4/reports/23_REPORT.md` | `tools/build_system_profile.py` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video_v5/README.md` | `.claude/launch.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/auto_scan_video_v5/V5_REAUDIT.md` | `.claude/launch.json` | L-D: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/auto_scan_video_v5/V5_REAUDIT.md` | `server/static/asv.js` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/auto_scan_video_v6/PHA00_04_NEN_TANG.md` | `admin-mvp-v3` | L-D: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/auto_scan_video_v6/PHA06_KIEN_TRUC_GUI.md` | `server/static/asv.js` | L-D: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-D |
| `docs/ltt_llm_dual/00_CURRENT_BASELINE.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/ltt_llm_dual/01_MULTI_JOB_INHERITANCE.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/ltt_llm_dual/01_MULTI_JOB_INHERITANCE.md` | `tests/test_958_cua_dong_bo_job_planner.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/02_REQUEST_TRACE.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/ltt_llm_dual/03_GPU_RESOURCE_MAP.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/ltt_llm_dual/05_COMMUNITY_EVIDENCE.md` | `qwen38-mtp/sweeps/rtx-3090.md` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/06_GAP_ANALYSIS.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/ltt_llm_dual/BANG_DOI_SOAT.md` | `scratchpad/do_cong_q_soak.py` | L-B: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/ltt_llm_dual/BAN_DO_DUONG_DI.md` | `starlette/background.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/BAN_GIAO_PHIEN.md` | `test-results/gates/20260912T125202Z-8004.json` | L-B: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/ltt_llm_dual/DECISION_LOG.md` | `.superpowers/sdd/2026-09-11-ltt-llm-dual-model/task-1.5-report.md` | L-B: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/ltt_llm_dual/DECISION_LOG.md` | `admin-mvp-v3` | L-B: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/ltt_llm_dual/DECISION_LOG.md` | `llm_gateway/don_dep.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/DECISION_LOG.md` | `render_gateway/nhuong_card.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/DECISION_LOG.md` | `vllm/v1/core/sched/scheduler.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` | `tests/test_12xx_phuong_an_c_hop_dong.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` | `scratchpad/do_khoa_hang_khoa.py` | L-B: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` | `starlette/background.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/SO_LOI_DO_TAI.md` | `uvicorn/protocols/http/h11_impl.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/NGHIEM_THU_PHUONG_AN_C_17_09.md` | `nt_c/kh.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` | `alembic/versions/2026MMDD_HHMM_public_api_requests_phien.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` | `codex-rs/codex-api/src/requests/headers.rs` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` | `codex-rs/core/src/client.rs` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` | `codex-rs/core/src/turn_metadata.rs` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` | `tests/test_1512_so_luot_so_do.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/bench_hang_cho/KET_QUA_BAO_TRI_18_09.md` | `llm_gateway/don_dep.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/bench_hang_cho/KET_QUA_BAO_TRI_18_09.md` | `render_gateway/nhuong_card.py` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/ltt_llm_dual/artifacts/bench_hang_cho/SAMPLING_35_MODEL_CARD_18_09.md` | `codex-rs/models-manager/prompt.md` | L-B: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-B |
| `docs/migration/README.md` | `bot/worker.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/README.md` | `utils/gsheets.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/00_STATUS.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/migration/workflow_apps/01_SOURCE_MANIFEST.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/migration/workflow_apps/02_LTT_RUNTIME_BASELINE.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/migration/workflow_apps/03_AUDIT_BOT_TRANSCRIPT.md` | `bot/state_manager.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/03_AUDIT_BOT_TRANSCRIPT.md` | `bot/worker.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/03_AUDIT_BOT_TRANSCRIPT.md` | `engine/gemini_corrector.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/03_AUDIT_BOT_TRANSCRIPT.md` | `engine/whisper_integration.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/03_AUDIT_BOT_TRANSCRIPT.md` | `utils/gdrive.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/03_AUDIT_BOT_TRANSCRIPT.md` | `utils/gsheets.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/04_AUDIT_BOT_PAUSE.md` | `bot/state_manager.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/04_AUDIT_BOT_PAUSE.md` | `bot/worker.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/04_AUDIT_BOT_PAUSE.md` | `configs/bot_config_pause.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/05_AUDIT_BOT_GEM.md` | `BOT_VEO3/PROMPT_KICHBAN/core/workflow_engine.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/05_AUDIT_BOT_GEM.md` | `core/gemini_client.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/05_AUDIT_BOT_GEM.md` | `core/workflow_engine.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/06_AUDIT_BOT_DUNGVIDEO.md` | `bot/gsheets.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/06_AUDIT_BOT_DUNGVIDEO.md` | `bot/recovery.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/06_AUDIT_BOT_DUNGVIDEO.md` | `bot/worker.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/06_AUDIT_BOT_DUNGVIDEO.md` | `configs/pipeline.yaml` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/06_AUDIT_BOT_DUNGVIDEO.md` | `gui/widgets/subtitle_form.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/07_CROSS_BOT_SYNTHESIS.md` | `configs/bot_config_pause.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/07_CROSS_BOT_SYNTHESIS.md` | `core/chatgpt_automation.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/08_CAU_HINH_THAT_TREN_PRODUCTION.md` | `configs/bot_config_pause.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/08_CAU_HINH_THAT_TREN_PRODUCTION.md` | `configs/bot_config_whisper.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/08_CAU_HINH_THAT_TREN_PRODUCTION.md` | `configs/pipeline.yaml` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/30_PARITY_VOI_BOT_THAT.md` | `configs/bot_config_whisper.json` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/migration/workflow_apps/31_KE_HOACH_DU_LIEU_TEST_BON_APP.md` | `configs/pipeline.yaml` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/03_OSS_LICENSE.md` | `references/OSS_BOUNDARY_RULES.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/EXECUTION_PLAN.md` | `LTTnexus/BUILD_WINDOWS.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/EXECUTION_PLAN.md` | `LThbbs/LTT_HBBS_FORK.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/EXECUTION_PLAN.md` | `data/nexus_versions.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/nexus/EXECUTION_PLAN.md` | `scratchpad/e2e_live.py` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/nexus/N3_2_ENGINE.md` | `src/relay_server.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/N3_2_ENGINE.md` | `src/tcp.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/N3_2_FORK.md` | `src/client.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/N5_VAN_HANH.md` | `data/nexus/release_manifest.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/nexus/N7_DANH_SACH_VIEC.md` | `src/lang.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/README.md` | `src/client.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/README.md` | `src/relay_server.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/nexus/README.md` | `src/tcp.rs` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-11-ltt-voice-rc1.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/superpowers/plans/2026-09-13-ltt-voice-public-api-speed-language.md` | `tests/test_516_voice_speed_language_api.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-18-don-tai-lieu.md` | `canonical integrator` | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-18-don-tai-lieu.md` | `docs/LTTCODE/HANDOFF_2026-09-17.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-18-don-tai-lieu.md` | `tests/test_12xx_ten_da_go.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-18-ltt-llm-v2-lam-lai-tren-phuong-an-c.md` | `docs/.../CLAUDE_CONFIG_MATRIX.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-18-ltt-llm-v2-lam-lai-tren-phuong-an-c.md` | `plugins/llm-ltt/src/adapter.ts` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-18-tong-plan-phien.md` | `.claude/settings.local.json` | L-E: tệp runtime/tạm không theo dõi git (bằng chứng một lần) |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `bốn bước trước lệnh nặng` | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `canonical integrator` | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | chay_nang.py (khoá `cpu_nhieu`) | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `eval máy B phải khoá eval_may_b` | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `gate.py --doi là vòng lặp` | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `ltt-3.8 mặc định xhigh` | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `purification-v1` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `tests/test_quet_tai_lieu.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `tools/co_that.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `tools/da_xoa.py` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md` | `tối đa 3 agent` | plan dọn tài liệu tự trích cụm cũ để định nghĩa từ điển |
| `docs/superpowers/plans/2026-09-19-tong-plan.md` | `LTTCODEAPP/docs/LTTCODE/plans/2026-09-19-plan-v2-dung-harness.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/plans/2026-09-19-tong-plan.md` | `pha-c/LOI_TONG.md` | L-E: đường kho ngoài / tên dự kiến / mã đã đổi trong văn bản có ngày — xem mục làn L-E |
| `docs/superpowers/specs/2026-09-11-ltt-voice-system-reconciliation-design.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/system_purification/README.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/system_purification/STATE.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/system_purification/STATE.md` | `purification-v1` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/vps_v2/ADR_INDEX.md` | `CORE/TARGET_ARCHITECTURE.md` | tài liệu `CORE/` chưa từng tồn tại (chú thích tại chỗ 19/09) |
| `docs/vps_v2/BASELINE.md` | `CORE/TARGET_ARCHITECTURE.md` | tài liệu `CORE/` chưa từng tồn tại (chú thích tại chỗ 19/09) |
| `docs/vps_v2/KE_HOACH_TRIEN_KHAI.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/vps_v2/KNOWN_BLOCKERS.md` | `CORE/QUALITY_SCORECARD.md` | tài liệu `CORE/` chưa từng tồn tại (chú thích tại chỗ 19/09) |
| `docs/vps_v2/README.md` | `CORE/QUALITY_SCORECARD.md` | tài liệu `CORE/` chưa từng tồn tại (chú thích tại chỗ 19/09) |
| `docs/vps_v2/README.md` | `CORE/TARGET_ARCHITECTURE.md` | tài liệu `CORE/` chưa từng tồn tại (chú thích tại chỗ 19/09) |
| `docs/vps_v2/README.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
| `docs/vps_v2/RELEASE_SCORECARD.md` | `CORE/QUALITY_SCORECARD.md` | tài liệu `CORE/` chưa từng tồn tại (chú thích tại chỗ 19/09) |
| `docs/vps_v2/STATE.md` | `admin-mvp-v3` | L-E: tên nhánh lúc viết, văn bản có ngày — đổi là sai lịch sử |
