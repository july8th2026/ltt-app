# Kiểm kê + phân loại tài liệu toàn hệ thống — 2026-09-19

> Sinh cho Task 2 của `docs/superpowers/plans/2026-09-19-don-sach-tai-lieu.md`, làn
> nền (worktree `D:\LTTSTUDIOSAPP-dtl-nen`, nhánh `phien/don-tl-nen`, gốc SHA
> `35f73cd5` — commit Task 1 "tools: quet_tai_lieu…").

## Phương pháp

Cột **quét** = `python tools/quet_tai_lieu.py docs CLAUDE.md AGENTS.md --json`
đếm CHET/THAY nằm TRONG thư mục/tệp đó (tổng toàn `docs/`: 1250 dòng — 1014 CHET,
236 THAY; phần lớn CHET là đường dẫn tương đối trong văn xuôi lịch sử, không phải
tất cả là tham chiếu vỡ thật — máy quét hiện tại đối chiếu đường dẫn tương đối,
CHƯA phân biệt "đường dẫn ví dụ trong báo cáo cũ" với "lệnh cần chạy được").

Cột **bằng chứng** = `blocking=<tổng>` từ `git grep -F "<tên>"` toàn kho, tách ba
nhóm:
- `code` — tệp trong `tools/ server/ platform_core/ apps/ render_gateway/
  nexus_agent/ frontend/ tests/` (mã hoặc test gate thật sự đọc/kiểm tên đó);
- `luat` — tệp đang được coi là LUẬT/TRA CỨU sống (CLAUDE.md, AGENTS.md,
  `00_LTT_OPERATING_CONTRACT.md`, `02_LENH_CHO_CLAUDE.md`, dãy `0X_*.md`,
  `QUY_TAC_CHAY_LENH_NANG.md`, `QUY_TRINH_WORKTREE.md`, …);
- `khac` — tài liệu khác trỏ tới, ĐÃ LOẠI các tệp tự thân là lịch sử/chỉ mục
  (`docs/AI_CLEAN_REBUILD/`, `docs/system_purification/`, `docs/APP_AUDIT/`,
  `docs/superpowers/plans|specs/`, `docs/NHAT_KY.md`, `docs/_luutru/`,
  `docs/REPO_HYGIENE/`, `docs/LTT_CMC/`) vì lịch sử trỏ tới lịch sử không phải
  bằng chứng "còn cần".

**LỊCH SỬ** chỉ gán khi CẢ BA: (a) `blocking=0` hoặc mọi tham chiếu còn lại tự
nó cũng thuộc cụm đang lưu trữ, (b) tên/nội dung tự thân nói rõ đã đóng (ngày
trong tên, "BÁO CÁO/BÀN GIAO/HOÀN TẤT/FINAL", pha `H<số>` đã qua), (c) sửa cuối
> 10 ngày. Thiếu một tiêu chí ⇒ **CẦN XEM**, không đoán. Thư mục có `code_refs >
0` (kể cả qua `tests/`) mặc định **GIỮ** — chương trình chưa đóng nếu còn mã/test
gate đọc nó, bất kể tài liệu bao lâu chưa sửa.

⚠️ Đây là kiểm kê CƠ HỌC + phán đoán một lượt — không phải phán quyết cuối. Làn
Task 3 đọc dòng của mình, xác minh lại bằng `git grep`/đọc nội dung thật trước
khi lưu trữ hay sửa, đúng yêu cầu "chống dọn nhầm".

## Tổng số theo loại (102 mục: 63 tệp gốc `docs/` + 39 thư mục cấp 1)

| Loại | Số mục |
|---|---|
| LUẬT | 7 |
| TRA CỨU | 50 |
| TRẠNG THÁI | 3 |
| LỊCH SỬ (đề xuất lưu trữ) | 16 |
| CẦN XEM (chưa đủ bằng chứng, làn tự quyết) | 26 |

## Danh sách CẦN XEM (không được lưu trữ nếu chưa xem lại)

- `docs/02_LENH_CHO_CLAUDE.md` — Task 4 quyết định.
- `docs/06_DON_HA_TANG.md` — 0 blocking nhưng thuộc dãy runbook 00-06.
- `docs/SECURITY_CHECKLIST.md` — LUẬT nhưng chỉ 1 ref, cần xác nhận danh sách còn đúng.
- Cụm AGENT_LTT/Plenx (7 mục): `docs/AGENT_LTT`, `docs/KIEM_KE_VA_LO_TRINH_AGENT.md`,
  `docs/PHUONG_AN_AGENT.md`, `docs/PHAN_TICH_PLENX.md`, `docs/KHAO_SAT_PLENX_AGENT.md`,
  `docs/KE_HOACH_DI_TRU_MODULE.md` — `docs/00_BAT_DAU_TU_DAY.md` (LUẬT) vẫn trỏ
  `AGENT_LTT/00_AGENT_BAT_DAU.md` cho "AI Agent LTT", nhưng `docs/nexus` (code=71,
  đang sống) có vẻ là hệ Agent MỚI. Cần chủ dự án xác nhận AGENT_LTT còn là đặc tả
  sống hay đã bị Nexus thay — nếu đã thay, sửa luôn con trỏ trong `00_BAT_DAU_TU_DAY.md`.
- 6 tệp `LLM_*` gốc (`LLM_CHANGELOG_UPGRADE`, `LLM_FINAL_ARCHITECTURE`,
  `LLM_FINAL_GATE_FAILURES`, `LLM_FINAL_GATE_REPORT`, `LLM_OPERATIONS_RUNBOOK`,
  `LLM_QUALITY_LEDGER`) — chỉ 1 ngày tuổi (18/09), 0 blocking; quá mới để lưu trữ dù
  đủ điều kiện cơ học, có thể là hồ sơ làm việc dở của đợt L-33 vừa xong.
- `docs/KE_HOACH_NOI_TIEP_2026-08-29.md`, `docs/KE_HOACH_MVP_THI_HANH.md`,
  `docs/KHAO_SAT_APIKEYS.md`, `docs/KE_HOACH_TIEP_2026-08-24.md`,
  `docs/PHAN_TICH_MVP_2026-08-23.md`, `docs/LOGGING_OBSERVABILITY.md`,
  `docs/LTT_CLI_COMPAT_DECISIONS.md` — mỗi tệp còn 1 tham chiếu chưa rõ thật/tình cờ.
- `docs/AI_CLEAN_REBUILD` — 2 blocking là test gate thật, cần L-E xác định phạm vi còn sống.
- `docs/LTT_CMC` — `STATE.md`/topology còn được `tests/test_972,973,975` gate thật,
  nhưng có `FINAL_REPORT.md`/`HANDOFF_*` cùng thư mục — cần tách trong thư mục.
- `docs/VPS_V4` — 0 code_ref riêng nhưng cùng sản phẩm với `VPS`(code=80)/`vps_v2`(code=3).
  **Đề xuất gộp lan với VPS/vps_v2 (L-E) thay vì L-D như plan gốc** — tránh xung đột
  chéo khi hai làn cùng sửa tài liệu của cùng một app `apps/vps/`.
- `docs/APP_AUDIT` — hỗn hợp: `quy_tac_audit.md` (đang sống) trỏ tới, nhưng hàng trăm
  audit con đã đóng theo ngày — L-C cần tách từng audit, không xử lý cả cụm.
- `docs/SCHEDULER_V1`, `docs/ui_stabilization` — tham chiếu còn nhưng chưa rõ chương
  trình đã đóng.

## docs/ gốc (63 tệp, làn L-A cùng CLAUDE.md/AGENTS.md/hợp đồng)

| tệp/thư mục | loại | còn đúng? | hành động | ghi chú | quét | bằng chứng |
|---|---|---|---|---|---|---|
| `docs/00_BAT_DAU_TU_DAY.md` | LUAT | co | giu | cong vao chinh, 9 commit, moi 16/09 | CHET=1 THAY=0 | blocking=7 (code=1/luat=0/khac=6), 3 ngay |
| `docs/00_LTT_OPERATING_CONTRACT.md` | LUAT | co | giu | hop dong chinh, 15 commit, moi nhat 18/09 | CHET=2 THAY=0 | blocking=47 (code=5/luat=9/khac=33), 1 ngay |
| `docs/01_COPY_LEN_SERVER.md` | TRA CUU | co | giu | con tro tu CLAUDE.md + setup script | CHET=2 THAY=0 | blocking=7 (code=0/luat=2/khac=5), 24 ngay |
| `docs/02_LENH_CHO_CLAUDE.md` | CAN XEM | khong-ro | xem-task4 | Task 4 quyet dinh con hieu luc khong (plan da ghi ro) | CHET=0 THAY=0 | blocking=6 (code=0/luat=1/khac=5), 2 ngay |
| `docs/03_THEM_APP_MOI.md` | LUAT | co | giu | con tro CLAUDE.md luat chet nguoi so 9 | CHET=0 THAY=0 | blocking=15 (code=1/luat=4/khac=10), 2 ngay |
| `docs/04_CLOUDFLARE_TUNNEL.md` | TRA CUU | co | giu | con tro CLAUDE.md bang he con | CHET=0 THAY=0 | blocking=7 (code=0/luat=3/khac=4), 50 ngay |
| `docs/05_LEN_MANG_CLOUDFLARE.md` | TRA CUU | co | giu | con tro tu 04_CLOUDFLARE_TUNNEL + setup/3-cloudflare.ps1 | CHET=0 THAY=0 | blocking=4 (code=0/luat=1/khac=3), 25 ngay |
| `docs/06_DON_HA_TANG.md` | TRA CUU | can-xem | giu | 0 blocking nhung nam trong day so 00-06 dong bo; runbook ha tang van co the can | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 15 ngay |
| `docs/16_CAP_NHAT_VA_DEPLOY.md` | LUAT | co | giu | con tro CLAUDE.md, alembic that, 30 blocking | CHET=0 THAY=0 | blocking=30 (code=3/luat=7/khac=20), 1 ngay |
| `docs/AUDIT_APPS_2026-08-02.md` | LICH SU | khong-con-dung | luu-tru | audit mot lan co ngay trong ten, sole referrer KE_HOACH_TON_DONG cung dang luu tru | CHET=0 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 48 ngay |
| `docs/AUDIT_BAO_MAT_CHONG_DICH_NGUOC.md` | LICH SU | khong-con-dung | luu-tru | audit bao mat mot lan, 0 blocking, thay bang SECURITY_CHECKLIST.md song | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 48 ngay |
| `docs/AUDIT_MVP_2026-07-31.md` | LICH SU | khong-con-dung | luu-tru | audit MVP co ngay trong ten, chi con CHATLTT_V3/MVP_OPT tham chieu lich su | CHET=0 THAY=0 | blocking=4 (code=0/luat=0/khac=4), 50 ngay |
| `docs/BAN_GIAO_CUA_TAI_BOT.md` | LICH SU | khong-con-dung | luu-tru | ban giao mot lan, 0 blocking | CHET=1 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 16 ngay |
| `docs/BAN_GIAO_S1_S7_2026-09-07.md` | LICH SU | khong-con-dung | luu-tru | ban giao S1-S7 co ngay, 2 ref deu la cum dang luu tru cung dot | CHET=0 THAY=3 | blocking=2 (code=0/luat=0/khac=2), 12 ngay |
| `docs/BAY_TRONG_CONG_CHAT_LUONG.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=3 THAY=5 | blocking=33 (code=11/luat=4/khac=18), 2 ngay |
| `docs/CONG_THUC_DI_TRU_APP.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=10 (code=1/luat=2/khac=7), 49 ngay |
| `docs/DATA_RETENTION_POLICY.md` | TRA CUU | co | giu | ref tu LOGGING_OBSERVABILITY + deploy/windows/backup.ps1 | CHET=0 THAY=0 | blocking=6 (code=0/luat=1/khac=5), 25 ngay |
| `docs/DESIGN_SYSTEM_LTT.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=7 (code=2/luat=0/khac=5), 47 ngay |
| `docs/DEVELOPMENT_WORKFLOW.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=10 (code=1/luat=1/khac=8), 3 ngay |
| `docs/DOI_CHIEU_THUMBNAIL.md` | TRA CUU | co | giu | con duoc 03_THEM_APP_MOI + CONG_THUC_DI_TRU_APP (LUAT/TRA CUU dang song) tro toi - blocking that | CHET=2 THAY=0 | blocking=5 (code=0/luat=2/khac=3), 49 ngay |
| `docs/H26_OPERATIONS_RUNBOOK.md` | LICH SU | khong-con-dung | luu-tru | pha H26 da dong, 0 blocking, 41 ngay | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 41 ngay |
| `docs/H41_3_DUONG_LUI.md` | LICH SU | khong-con-dung | luu-tru | pha H41 da dong, 0 blocking, 21 ngay | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 21 ngay |
| `docs/HO_SO_HE_THONG.md` | TRA CUU | co | giu | test_145/test_394 tro toi - kiem tra ton tai tep, con GIU | CHET=5 THAY=0 | blocking=3 (code=0/luat=0/khac=3), 15 ngay |
| `docs/KE_HOACH_2APP_UPSCALE_AUTOSUB.md` | LICH SU | khong-con-dung | luu-tru | ke hoach co ten cu the da xong, 0 blocking, 48 ngay | CHET=2 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 48 ngay |
| `docs/KE_HOACH_DI_TRU_MODULE.md` | CAN XEM | khong-ro | xem-lai | con duoc AGENT_LTT + KHAO_SAT_BOT_GEMINI tro - cum di tru BOT GEMINI co the con dang dung | CHET=0 THAY=0 | blocking=4 (code=0/luat=1/khac=3), 49 ngay |
| `docs/KE_HOACH_MVP_THI_HANH.md` | CAN XEM | khong-ro | xem-lai | 1 ref tu docs/ANH_NOI_BO/DECISIONS.md (app dang song) - chua ro con load-bearing | CHET=3 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 27 ngay |
| `docs/KE_HOACH_NGAN_SACH_LOI.md` | TRA CUU | co | giu | con duoc QUY_TAC_CHAY_LENH_NANG.md (LUAT dang song) tro toi - blocking that | CHET=0 THAY=0 | blocking=1 (code=0/luat=1/khac=0), 15 ngay |
| `docs/KE_HOACH_NOI_TIEP_2026-08-29.md` | CAN XEM | khong-ro | xem-lai | co ref la .codex/README.md khong ro tro that hay trung ten tinh co - can nguoi kiem | CHET=1 THAY=3 | blocking=4 (code=0/luat=0/khac=4), 11 ngay |
| `docs/KE_HOACH_TIEP_2026-08-24.md` | CAN XEM | khong-ro | xem-lai | co test tests/test_329_chot_so_gpu.py tro toi - can kiem la that hay trung ten | CHET=1 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 21 ngay |
| `docs/KE_HOACH_TON_DONG.md` | LICH SU | khong-con-dung | luu-tru | backlog cu, 0 blocking, 44 ngay | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 44 ngay |
| `docs/KE_HOACH_TRIEN_KHAI.md` | TRANG THAI | co | giu | tracker song, con tro tu CLAUDE.md/AGENTS.md | CHET=40 THAY=0 | blocking=25 (code=0/luat=5/khac=20), 3 ngay |
| `docs/KHAO_SAT_APIKEYS.md` | CAN XEM | khong-ro | xem-lai | 1 ref tu KE_HOACH_TRIEN_KHAI (tracker song) - can kiem con muc nao dang mo | CHET=0 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 50 ngay |
| `docs/KHAO_SAT_BOT_GEMINI.md` | TRA CUU | co | giu | con duoc 00_BAT_DAU_TU_DAY (LUAT) tro toi qua bang Tra theo viec - blocking that | CHET=12 THAY=0 | blocking=5 (code=0/luat=2/khac=3), 49 ngay |
| `docs/KHAO_SAT_PLENX_AGENT.md` | CAN XEM | khong-ro | xem-lai | cung cum AGENT_LTT/Plenx | CHET=1 THAY=0 | blocking=4 (code=0/luat=0/khac=4), 46 ngay |
| `docs/KHUON_BAN_MODEL_NHA.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=1 THAY=0 | blocking=10 (code=3/luat=0/khac=7), 26 ngay |
| `docs/KIEM_KE_VA_LO_TRINH_AGENT.md` | CAN XEM | khong-ro | xem-lai | cung cum AGENT_LTT, referrer duy nhat la AGENT_LTT/00_AGENT_BAT_DAU.md (tu tham chieu trong cum) | CHET=13 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 48 ngay |
| `docs/LLM_CHANGELOG_UPGRADE.md` | CAN XEM | khong-ro | xem-lai | chi 1 ngay tuoi (18/09) - qua moi de luu tru du 0 blocking; co the la ho so lam viec cua dot L-33 vua xong, cho chu du an xac nhan con dung khong | CHET=0 THAY=0 | blocking=1 (code=1/luat=0/khac=0), 1 ngay |
| `docs/LLM_FINAL_ARCHITECTURE.md` | CAN XEM | khong-ro | xem-lai | chi 1 ngay tuoi (18/09) - qua moi de luu tru du 0 blocking; co the la ho so lam viec cua dot L-33 vua xong, cho chu du an xac nhan con dung khong | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 1 ngay |
| `docs/LLM_FINAL_GATE_FAILURES.md` | CAN XEM | khong-ro | xem-lai | chi 1 ngay tuoi (18/09) - qua moi de luu tru du 0 blocking; co the la ho so lam viec cua dot L-33 vua xong, cho chu du an xac nhan con dung khong | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 1 ngay |
| `docs/LLM_FINAL_GATE_REPORT.md` | CAN XEM | khong-ro | xem-lai | chi 1 ngay tuoi (18/09) - qua moi de luu tru du 0 blocking; co the la ho so lam viec cua dot L-33 vua xong, cho chu du an xac nhan con dung khong | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 1 ngay |
| `docs/LLM_OPEN_SOURCE_RESEARCH.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=2 (code=1/luat=0/khac=1), 1 ngay |
| `docs/LLM_OPERATIONS_RUNBOOK.md` | CAN XEM | khong-ro | xem-lai | chi 1 ngay tuoi (18/09) - qua moi de luu tru du 0 blocking; co the la ho so lam viec cua dot L-33 vua xong, cho chu du an xac nhan con dung khong | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 1 ngay |
| `docs/LLM_QUALITY_LEDGER.md` | CAN XEM | khong-ro | xem-lai | chi 1 ngay tuoi (18/09) - qua moi de luu tru du 0 blocking; co the la ho so lam viec cua dot L-33 vua xong, cho chu du an xac nhan con dung khong | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 1 ngay |
| `docs/LLM_UPGRADE_BASELINE.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 1 ngay |
| `docs/LLM_UPGRADE_MASTER_PLAN.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=9 (code=0/luat=0/khac=9), 1 ngay |
| `docs/LOGGING_OBSERVABILITY.md` | CAN XEM | khong-ro | xem-lai | 1 ref tu KE_HOACH_TRIEN_KHAI - chua ro con hieu luc, script backup that o DATA_RETENTION | CHET=0 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 25 ngay |
| `docs/LTTSTUDIOSAPP_GIAO_DIEN_TOAN_BO.txt` | LICH SU | khong-con-dung | luu-tru | ban xuat toan bo giao dien mot lan (dump), khong phai tai lieu song | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 48 ngay |
| `docs/LTT_CLI_COMPAT_DECISIONS.md` | CAN XEM | khong-ro | xem-lai | con moi (4 ngay) nhung 0 code ref - qua som de luu tru, cho them du lieu | CHET=2 THAY=0 | blocking=2 (code=0/luat=0/khac=2), 4 ngay |
| `docs/NHAT_KY.md` | TRANG THAI | co | giu | nhat ky song - PHAI GIU nguyen theo logic bo sung so 1 | CHET=77 THAY=17 | blocking=40 (code=3/luat=7/khac=30), 0 ngay |
| `docs/PHAN_TICH_MVP_2026-08-23.md` | CAN XEM | khong-ro | xem-lai | co test tests/test_307_giu_cho_treo.py tro toi - can kiem that/trung ten | CHET=0 THAY=0 | blocking=4 (code=0/luat=0/khac=4), 26 ngay |
| `docs/PHAN_TICH_PLENX.md` | CAN XEM | khong-ro | xem-lai | cung cum AGENT_LTT/Plenx | CHET=0 THAY=0 | blocking=3 (code=0/luat=0/khac=3), 49 ngay |
| `docs/PHUONG_AN_AGENT.md` | CAN XEM | khong-ro | xem-lai | cung cum AGENT_LTT/Plenx, cho quyet dinh cum | CHET=0 THAY=0 | blocking=3 (code=0/luat=0/khac=3), 48 ngay |
| `docs/PLAN_HOAN_TAT_2026-09-07.md` | LICH SU | khong-con-dung | luu-tru | ten co chu HOAN TAT = da xong, 0 blocking | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 12 ngay |
| `docs/PLAN_LAP_RAP_2026-09-06.md` | LICH SU | khong-con-dung | luu-tru | cung cum voi PLAN_HOAN_TAT/BAN_GIAO S1-S7, 0 blocking that | CHET=0 THAY=0 | blocking=2 (code=0/luat=0/khac=2), 12 ngay |
| `docs/QUYET_DINH_NEN_TANG.md` | TRANG THAI | co | giu | so quyet dinh song, con tro rong khap | CHET=4 THAY=2 | blocking=44 (code=1/luat=7/khac=36), 0 ngay |
| `docs/QUY_TAC_CHAY_LENH_NANG.md` | LUAT | co | giu | con tro tu CLAUDE.md/AGENTS.md/hop dong, code thuc | CHET=0 THAY=0 | blocking=14 (code=3/luat=5/khac=6), 3 ngay |
| `docs/QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=4 (code=0/luat=2/khac=2), 47 ngay |
| `docs/QUY_TRINH_WORKTREE.md` | LUAT | co | giu | con tro tu CLAUDE.md/AGENTS.md/hop dong | CHET=0 THAY=0 | blocking=24 (code=2/luat=5/khac=17), 2 ngay |
| `docs/SECURITY_CHECKLIST.md` | LUAT | can-xem | sua | 0 code, 1 ref (QUYET_DINH_NEN_TANG) - kiem lai con dung danh sach kiem an ninh | CHET=1 THAY=0 | blocking=1 (code=0/luat=0/khac=1), 50 ngay |
| `docs/TAI_KHOAN_THU.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=2 (code=1/luat=0/khac=1), 3 ngay |
| `docs/UX_DANH_GIA_VA_PHUONG_AN.md` | LICH SU | khong-con-dung | luu-tru | danh gia mot lan, 0 blocking, 49 ngay | CHET=0 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 49 ngay |
| `docs/VAN_HANH_THAT.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=2 THAY=0 | blocking=5 (code=1/luat=1/khac=3), 2 ngay |
| `docs/quy_tac_audit.md` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=6 (code=0/luat=2/khac=4), 45 ngay |

## L-B — ltt_llm_dual, audit_ltt_llm, VLM_NOI_BO, PUBLIC_API

| tệp/thư mục | loại | còn đúng? | hành động | ghi chú | quét | bằng chứng |
|---|---|---|---|---|---|---|
| `docs/PUBLIC_API` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=15 THAY=0 | blocking=175 (code=47/luat=2/khac=126), 0 ngay |
| `docs/VLM_NOI_BO` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=14 THAY=1 | blocking=21 (code=6/luat=0/khac=15), 1 ngay |
| `docs/audit_ltt_llm` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=7 THAY=2 | blocking=13 (code=1/luat=0/khac=12), 1 ngay |
| `docs/ltt_llm_dual` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=53 THAY=7 | blocking=77 (code=14/luat=2/khac=61), 0 ngay |

## L-C — APP_AUDIT, developer_portal_mvp_ui, UI_REDESIGN, lttstudios-website

| tệp/thư mục | loại | còn đúng? | hành động | ghi chú | quét | bằng chứng |
|---|---|---|---|---|---|---|
| `docs/APP_AUDIT` | CAN XEM | hon-hop | xem-lai | quy_tac_audit.md (dang song) tro toi + hang tram audit con da dong theo ngay - lan L-C can tach tung audit con, khong xu ly ca cum | CHET=18 THAY=0 | blocking=7 (code=1/luat=1/khac=5), 38 ngay |
| `docs/UI_REDESIGN` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=3 THAY=0 | blocking=2 (code=0/luat=1/khac=1), 41 ngay |
| `docs/developer_portal_mvp_ui` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=6 THAY=0 | blocking=9 (code=6/luat=0/khac=3), 20 ngay |
| `docs/lttstudios-website` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=1 THAY=0 | blocking=14 (code=4/luat=0/khac=10), 24 ngay |

## L-D — LTT_VOICE, VIDEO_AI_V2, CHATLTT*, auto_scan_video*, multijob, admin_mvp_v3, MVP_OPTIMIZATION_V2

| tệp/thư mục | loại | còn đúng? | hành động | ghi chú | quét | bằng chứng |
|---|---|---|---|---|---|---|
| `docs/CHATLTT_V3` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=34 THAY=14 | blocking=29 (code=16/luat=0/khac=13), 1 ngay |
| `docs/CHATLTT` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=35 THAY=10 | blocking=56 (code=21/luat=0/khac=35), 1 ngay |
| `docs/LTT_VOICE` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=61 THAY=36 | blocking=86 (code=33/luat=0/khac=53), 1 ngay |
| `docs/MVP_OPTIMIZATION_V2` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=18 THAY=0 | blocking=2 (code=1/luat=0/khac=1), 24 ngay |
| `docs/VIDEO_AI_V2` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=119 THAY=21 | blocking=7 (code=3/luat=0/khac=4), 3 ngay |
| `docs/admin_mvp_v3` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=3 THAY=5 | blocking=20 (code=14/luat=0/khac=6), 3 ngay |
| `docs/auto_scan_video_v4` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=51 THAY=6 | blocking=18 (code=3/luat=0/khac=15), 6 ngay |
| `docs/auto_scan_video_v5` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=5 THAY=0 | blocking=10 (code=4/luat=0/khac=6), 1 ngay |
| `docs/auto_scan_video_v6` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=17 THAY=1 | blocking=4 (code=1/luat=0/khac=3), 1 ngay |
| `docs/auto_scan_video` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=68 THAY=8 | blocking=181 (code=37/luat=1/khac=143), 11 ngay |
| `docs/multijob` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=50 (code=22/luat=0/khac=28), 1 ngay |

## L-E — superpowers/plans, system_purification, migration, architecture + phần còn lại (gồm VPS/vps_v2/VPS_V4 gộp — điều chỉnh so với plan gốc)

| tệp/thư mục | loại | còn đúng? | hành động | ghi chú | quét | bằng chứng |
|---|---|---|---|---|---|---|
| `docs/AGENT_LTT` | CAN XEM | khong-ro | xem-lai | VAN duoc 00_BAT_DAU_TU_DAY.md tro toi (bang Tra theo viec, dong AI Agent LTT); nhung 0 code_ref 48 ngay trong khi docs/nexus (code=71) la he Agent moi. Can chu du an xac nhan AGENT_LTT con la dac ta song hay da bi nexus thay the. KET QUA L-E 19/09: GIU nguyen, KHONG chuyen (00_BAT_DAU_TU_DAY.md thuoc lan L-A) - xem docs/AGENT_LTT/README.md | CHET=21 THAY=0 | blocking=4 (code=0/luat=1/khac=3), 48 ngay |
| `docs/AI_CLEAN_REBUILD` | CAN XEM | khong-ro | xem-lai | 2 blocking la tests/test_1005_history_only + test_190_public_api_coverage (gate that) - lan L-E can xac dinh pham vi con song. KET QUA L-E 19/09: GIU nguyen, chua du bang chung quyet toan cum - xem docs/AI_CLEAN_REBUILD/README.md | CHET=22 THAY=18 | blocking=4 (code=2/luat=0/khac=2), 1 ngay |
| `docs/ANH_NOI_BO` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=63 THAY=0 | blocking=23 (code=8/luat=1/khac=14), 15 ngay |
| `docs/API_EXPANSION_V2` | LICH SU | khong-con-dung | luu-tru | 10_FINAL_REPORT.md xac nhan da xong, thay the boi docs/PUBLIC_API/ (code=47, dang song). DA LUU TRU 19/09 -> docs/_luutru/2026-09/API_EXPANSION_V2/ | CHET=8 THAY=0 | blocking=0 (code=0/luat=0/khac=0), 20 ngay |
| `docs/LTTCODE` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=6 THAY=0 | blocking=58 (code=25/luat=1/khac=32), 2 ngay |
| `docs/LTT_CMC` | CAN XEM | khong-ro | xem-lai | STATE.md/topology con duoc tests/test_972,973,975 gate that; nhung co FINAL_REPORT.md/HANDOFF_* trong cung thu muc - lan L-E can tach: STATE/INVENTORY GIU, FINAL_REPORT/HANDOFF co the luu tru rieng. KET QUA L-E 19/09: TAT CA sua cuoi 2026-09-11..16 (<10 ngay) - chua du bang chung (c), GIU NGUYEN toan cum, xem lai sau ~26/09 | CHET=10 THAY=5 | blocking=3 (code=0/luat=0/khac=3), 2 ngay |
| `docs/MOBILE` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=3 THAY=7 | blocking=15 (code=9/luat=0/khac=6), 11 ngay |
| `docs/OPERATING_STANDARDIZATION` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=2 THAY=0 | blocking=3 (code=1/luat=1/khac=1), 1 ngay |
| `docs/QUALITY_LAB` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=0 THAY=0 | blocking=3 (code=1/luat=0/khac=2), 12 ngay |
| `docs/REPO_HYGIENE` | LICH SU | khong-con-dung | luu-tru | chi 2 tep WORKTREE_INVENTORY.csv/md - snapshot kiem ke worktree mot lan, 0 blocking. DA LUU TRU 19/09 -> docs/_luutru/2026-09/REPO_HYGIENE/ | CHET=3 THAY=10 | blocking=0 (code=0/luat=0/khac=0), 11 ngay |
| `docs/SCHEDULER_V1` | TRA CUU | co | giu | 2 ref: KE_HOACH_TRIEN_KHAI.md (tracker song, quyet dinh Q122 "Ho so canonical: docs/SCHEDULER_V1/") + ltt_llm_dual/DECISION_LOG.md TD-D11 (mo ta priority_class o thi hien tai, khop jobs.py/job_runner.py dang chay that). KET QUA L-E 19/09: NANG len TRA CUU, giu nguyen | CHET=3 THAY=1 | blocking=2 (code=0/luat=0/khac=2), 8 ngay |
| `docs/VPS_V4` | TRA CUU | co | giu | 0 code_ref rieng nhung cung san pham voi VPS(code=80)/vps_v2(code=3); GOP LAN voi VPS de tranh xung dot cheo (dieu chinh so voi plan goc). KET QUA L-E 19/09: 10_FINAL_REPORT.md xac nhan "CLOSED 17/09 - PRODUCTION" - la trang thai VPS hien hanh, NANG len TRA CUU, giu nguyen (chua gop ten voi VPS/vps_v2, can chu du an quyet) | CHET=2 THAY=0 | blocking=3 (code=0/luat=0/khac=3), 2 ngay |
| `docs/VPS` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=2 THAY=0 | blocking=228 (code=80/luat=4/khac=144), 3 ngay |
| `docs/architecture` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=7 THAY=2 | blocking=82 (code=15/luat=1/khac=66), 1 ngay |
| `docs/migration` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=48 THAY=3 | blocking=276 (code=43/luat=3/khac=230), 8 ngay |
| `docs/nexus` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=11 THAY=0 | blocking=175 (code=71/luat=1/khac=103), 3 ngay |
| `docs/superpowers` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=39 THAY=20 | blocking=21 (code=3/luat=0/khac=18), 0 ngay |
| `docs/system_purification` | LICH SU | khong-con-dung | luu-tru | ke hoach 02/09 da ghi la cu (nhanh admin-mvp-v3/master); 1 code ref (tools/thanh_phan.toml) can kiem lai la duong dan cau hinh, khong phai phu thuoc noi dung. KET QUA L-E 19/09: xac minh CHINH XAC 2 tep con duoc tools/thanh_phan.toml + tests/test_73_dong_thoi_pg.py tro toi (STATE.md, reports/07_execution_money_provider.md) - GIU 2 tep do, LUU TRU 14/16 tep con lai -> docs/_luutru/2026-09/system_purification/ | CHET=25 THAY=27 | blocking=3 (code=1/luat=0/khac=2), 17 ngay |
| `docs/ui_stabilization` | LICH SU | khong-con-dung | luu-tru | 2 ref deu tu developer_portal_mvp_ui/ (TRA CUU dang song) - co the la buoc on dinh UI cua portal, can nguoi xac nhan da dong hay con. KET QUA L-E 19/09: 08_FINAL_REPORT.md xac nhan xong 26/08, 0 code/test/tools tro toi, 24 ngay - DU 3 bang chung, DA LUU TRU -> docs/_luutru/2026-09/ui_stabilization/, sua 2 con tro trong developer_portal_mvp_ui/ | CHET=0 THAY=0 | blocking=2 (code=0/luat=0/khac=2), 24 ngay |
| `docs/vps_v2` | TRA CUU | co | giu | co code_refs va/hoac test gate that tro toi - con song | CHET=32 THAY=2 | blocking=9 (code=3/luat=0/khac=6), 1 ngay |

## Làn nặng nhất

L-E: 20 thư mục cấp 1 (kể cả cụm VPS ba tầng vừa gộp thêm `VPS_V4`), nhiều mục
CẦN XEM nhất (AGENT_LTT/Plenx, AI_CLEAN_REBUILD, LTT_CMC, VPS_V4, SCHEDULER_V1,
ui_stabilization, system_purification). Nên tách L-E thành 2 agent con song song
theo cụm phụ (VPS ba tầng | phần còn lại) nếu thời lượng vượt ước tính của plan.
