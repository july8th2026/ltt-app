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
