# Dọn tài liệu toàn hệ thống — plan (khối F của tổng plan phiên, làm SAU khi xong LLM v2)

> Nguồn: bản rà chỉ đọc 18/09 (không sửa gì). Mỗi lô một commit. Tệp chuyển vào `docs/_luutru/<bo>_2026-09/` luôn để lại **tệp con trỏ 3 dòng** ở chỗ cũ (docstring test 1203, 1218, 1227, 980–988 còn nhắc tên các tệp này). Các mục đã có trong plan LLM v2 (Task 1 Step 6, Task 4, Task 11) — **đánh dấu ở plan đó**, không làm hai lần.
>
> Luật loại bỏ: tên đã gỡ ở L-23 (danh sách trong Global Constraints của plan LLM v2) + `--no-cache-idle-slots`, `cache-ram 8192/12288`, sàn RAM 48 cho LLM, mức effort của 3.5, "canonical integrator", "vòng lặp là `gate.py --doi`".

## Lô 1 — Tài liệu nguồn LLM đang nói sai (~60 phút)
- `docs/ltt_llm_dual/DECISION_LOG.md`: gạch L-24 phần 12288/48 ("THAY bởi L-25"), giữ checkpoints/`-b 512`/`-watch-config`; sửa mục "Trạng thái" đầu tệp (quyết định mới nhất L-25, plan hiện hành, bản đồ = `BAN_DO_DUONG_DI.md`); ghi chú đính chính L-15/L-16 "server-global" (ghi đè budget theo request — Task 4); L-22 gắn "ĐÃ GỠ ở L-23" cho `SO_SLOT`/`POOL_KV`.
- `KE_HOACH_PHUONG_AN_C.md`: banner "ĐÃ THỰC THI 17/09 (L-23); §1–§2 là ảnh chụp trước khi sửa; §3 hiện hành; §6 R-2 còn mở"; `:68-69`, `:338`, `:356` theo L-25/O-19.
- `docs/ltt_llm_dual/README.md`: viết lại thành chỉ mục (câu hỏi → tệp chủ); 00–06 ghi "ảnh chụp 11/09".
- `RUNBOOK.md:3-4` trỏ `BAN_DO_DUONG_DI.md`; chuyển §2.0 (bản ghi deploy 12/09, `MAX_DONG_THOI`) sang `NHAT_KY_TRIEN_KHAI.md`.
- `BANG_DOI_SOAT.md` ghi "ảnh chụp 13/09" + trỏ `NGHIEM_THU_PHUONG_AN_C_17_09.md`.

## Lô 2 — Quyết định sản phẩm + tài liệu VLM cũ (~45 phút)
- `docs/QUYET_DINH_NEN_TANG.md`: Q120 (`:300-330`, `LE`, 96.256, `MAX_INPUT_TOKENS`) gắn "THAY bởi L-23"; Q111/Q112 (`:138-139`) gạch `MAX_INPUT_TOKENS=90000`, `-c 131072`, `MAX_DONG_THOI=1`; Q132 (`:152`) sửa "slot/token pool/RPM" → "`-np` + `Σ ≤ -c`, RPM đã gỡ"; Q135 (`:577`) "canonical integrator" → "phiên tự gộp main (hợp đồng §4)"; thêm Q136 con trỏ sang DECISION_LOG L-22…L-25; ghi chú số Q123 bị dùng hai lần (`:436`, `:462`).
- `docs/VLM_NOI_BO/CAM_CLI.md:255` (Task 11), `ADMISSION_QUEUE_LTT_LLM.md` banner "THAY bởi L-22/L-23".
- `docs/CHATLTT_V3/00_KE_HOACH_V3.md:253`, `docs/AI_CLEAN_REBUILD/CAMPAIGN_STATE.md:650`: nhịp gate cũ → "theo hợp đồng §4".

## Lô 3 — Chú thích trong mã (đi cùng plan LLM v2)
- `apps/ltt_llm/ngan_sach.py:552-554, :583` → Task 4. `examples.py:841-842`, `server/api/tools.py:36`, `tools/do_ngan_sach_chuyen_loi_thoai.py` → Task 11. **Thêm vào Task 11:** `apps/auto_scan_video/pipeline.py:178` (`DONG_THOI_MAY_B = 1`).

## Lô 4 — Lưu trữ plan/spec đã xong hoặc bỏ (~40 phút, `git mv` + con trỏ)
- `docs/multijob/` + `superpowers/specs/2026-09-11-ltt-llm-multijob-design.md` (57k/171k chia đều).
- `specs/2026-09-11-ltt-llm-dual-model-design.md`, `plans/2026-09-11-ltt-llm-dual-model.md`.
- `plans/2026-09-11-ltt-cmc*.md` (5) + `specs/2026-09-11-ltt-cmc-design.md` (đóng ở Q135).
- Bộ nâng cấp LLM 09/09: `docs/LLM_OPERATIONS_RUNBOOK.md`, `LLM_FINAL_ARCHITECTURE.md`, `LLM_UPGRADE_MASTER_PLAN.md`, `LLM_UPGRADE_BASELINE*`, `LLM_FINAL_GATE_*`, `LLM_QUALITY_LEDGER*`, `LLM_CHANGELOG_UPGRADE*`, `LLM_OPEN_SOURCE_RESEARCH*` (trùng RUNBOOK/BAN_DO).
- `VLM_NOI_BO/KE_HOACH_TRIEN_KHAI_MAY_B.md`; `OPERATING_STANDARDIZATION/SESSION_MIGRATION_NOTE.md` (nhịp gate cũ, trùng hợp đồng).
- **Giữ nguyên** (đã ghi rõ là lịch sử): `ltt_llm_dual/00–06, 10`, `RA_SOAT_THAM_SO`, `NGU_CANH_DAI_2026-09-03`, `PUBLIC_API/CHANGELOG`, `NHAT_KY*`.

## Lô 5 — Ảnh chụp chiến dịch không ghi ngày (~20 phút)
Một banner đầu mỗi tệp/thư mục chiến dịch ("ảnh chụp dd/mm; số đồng thời LLM đã cũ → `ngan_sach.HO_SO`"): `AI_CLEAN_REBUILD/{MIGRATION_MAP, PHA13_SO_TAY, PRODUCT_DEPENDENCY_MAP}`, `architecture/workflow_v2_audit/01_CURRENT_LTT_ARCHITECTURE.md`, `auto_scan_video_v5/V5_IMPLEMENTATION_STATUS.md`, `auto_scan_video_v6/CHAN_DOAN_TEST_448.md`, `vps_v2/KNOWN_BLOCKERS.md`, `LTT_VOICE/UPGRADE_98/07_CHANGE_LEDGER.md`, `CHATLTT/reports/03_text_noi_bo.md`, `audit_ltt_llm/`.

## Lô 6 — Kho LTTCODEAPP (~20 phút, commit trong kho đó)
- `docs/LTTCODE/HANDOFF_2026-09-17.md` → `_superseded/` (lối vào là `STATE.md`).
- Plan 16–17/09 có checkbox không còn cập nhật (tiến độ nằm ở `DANH_MUC_CONG_VIEC.md`): `plans/2026-09-17-{bat-cong-cu-harness, ke-hoach-tong-phien, truoc-build-0.1.5, dot-updater-dang-nhap-search}.md`, `2026-09-16-updater-kenh-phat-hanh.md` → `_superseded/`; sửa con trỏ `STATE.md:6-7`. (Hai tệp này còn câu "57k" — lưu trữ là đủ.)

## Lô 7 — Memory (~25 phút, ngoài git)
- `model-nha-tren-may-b.md`: "L-16 server-global `--reasoning-budget 512`" → budget 4096/2048 theo model (L-20/Q131); client ghi đè được ở cửa A (Task 4). Sửa dòng chỉ mục.
- `may-b-duong-vao-va-du-phong.md:53-54`: `SO_SLOT_MAY_B`/`DONG_THOI_MAY_B` → `HO_SO[m].np`.
- `lttcode-desktop-dot-updater.md:26-31`: → 0.1.7 stable 100 % (18/09); lối vào `STATE.md`.
- `gate-chi-chay-cuoi-cung.md:14-18`: thêm đính chính cùng ngày (deploy giữa phiên sau L1/L2 xanh).
- (Đã xử lý 18/09) `agent-song-song-phai-xep-hang-khoa-may.md` khớp hợp đồng: `-n` ≤ 6 + khoá.

## Lô 8 — Chặn tái phát (~1,5 giờ)
`tools/check_ten_da_go.py` (mẫu `tools/check_luat_van_hanh.py`), đăng ký làm `Step` trong `tools/gate.py` cạnh "luat van hanh" (chạy ở L1/L2/L3), kèm `tests/test_12xx_ten_da_go.py` có đối chứng (tiêm một dòng cũ ⇒ đỏ). Một bảng tên đã gỡ duy nhất trong tool; phạm vi: `CLAUDE.md`, `AGENTS.md`, `docs/00_*`, `docs/ltt_llm_dual/{BAN_DO_DUONG_DI,RUNBOOK,README}.md`, plan mới nhất, `HUONG_DAN_CAM_CLI.md`, `CAM_CLI.md`, chú thích trong `apps/ltt_llm/`, `platform_core/llm/`, `llm_gateway/`. Miễn: `_luutru/`, `NHAT_KY*`, `artifacts/`, ảnh chụp có ngày, và dòng (+3 dòng sau) chứa `ĐÃ GỠ`/`ĐÃ THAY`/`~~`/`Gỡ:`. Bánh cóc: khoá tập hit hôm nay, chỉ đỏ khi tăng. Mở rộng `tests/test_1249_ban_do_khong_duoc_cu.py` thay vì viết trùng.

**Thứ tự:** Lô 1 → 2 → 8 → 4 → 5 → 6 → 7 (Lô 3 đi cùng plan LLM v2). **Tổng ~5 giờ.**
