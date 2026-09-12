# Handoff — LTT LLM recovery multijob + dual-model

Sao chép nguyên nội dung này vào phiên LLM dual-model khi tiếp tục.

## Immutable CMC baseline

- `CMC_BASE_SHA`: `09b219a371e1261f0f0eef0e316c1ca42754cb78`
- Tag: `cmc-base-20260911`
- Canonical branch/worktree: `main` / `D:\LTTSTUDIOSAPP`
- Baseline đã gồm Voice RC1, Alembic head `d9a1f6c2b3e5` và gate 33/33 PASS
  (`test-results/gates/20260911T235957Z-25548.json`).

Không merge `main` vào source worktree. Sau khi seal hai source state, tạo
`cmc/llm-dual-reconcile` **từ đúng tag/SHA trên** và port theo
`docs/superpowers/plans/2026-09-11-ltt-cmc-llm-dual.md`.

## Source A — multijob predecessor

- Worktree: `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-llm-api-http-guide-a3e123`
- Branch: `claude/ltt-llm-multijob-audit-43efd3`
- HEAD: `b3b11dbcfe0fd13107e992ac83b53dad1fa6e811`
- Tracked dirty patch-id: `2d985f9c29d7921c2085f02a5c27aaac6be991f1`
- Dirty files tại snapshot `2026-09-12T07:03:17+07:00`:
  - `platform_core/job_runner.py`
  - `platform_core/llm/tham_so_da_luot.py`
  - `platform_core/runtime_noi_bo/luong.py`
  - `server/api/chat.py`
  - `server/api/streaming.py`
- Untracked: không có.

## Source B — dual-model recovery

- Worktree: `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-video-architecture-recovery-746b24`
- Branch: `phien/ltt-llm-dual`
- HEAD: `91e42b281c80e9f52f27bb6092178c549cdbebbb`
- Tracked dirty patch-id: `447a6aad4d39dfc78be0b9e0273acba045781a96`
- Dirty tracked files:
  - `apps/ltt_llm/features.py`
  - `apps/ltt_llm/manifest.py`
  - `platform_core/llm/gia_token.py`
  - `platform_core/llm/thanh_toan.py`
  - `platform_core/public_api/dieu_khoan.py`
  - `platform_core/runtime_noi_bo/luong.py`
  - `server/api/chat.py`
  - `server/api/streaming.py`
  - `server/routes/dashboard.py`
  - `server/templates/api_dieu_khoan.html`
  - `server/templates/gia_api.html`
  - `tests/test_252_gia_token.py`
  - `tests/test_253_thanh_toan_llm.py`
  - `tests/test_256_app_ltt_llm.py`
  - `tests/test_600_runtime_noi_bo_luong.py`
  - `tests/test_603_text_luong_chuan_hoa.py`
  - `tests/test_818_tinh_tien_tich_luy.py`
  - `tools/kiem_ltt_llm.py`
- Untracked:
  - `tests/test_1211_cong_mtp_bench.py` — SHA-256
    `A431ADA17C33B18261ABCB751BC6E927BC671A782CB15B8481345B24B6AA668A`
  - `tests/test_1213_gia_theo_model.py` — SHA-256
    `5E24F3B438DBBFF42504F75470A14ACBD9E938F8ABD6816542AAB7D733889302`

## Bằng chứng chống áp trùng

`git cherry phien/ltt-llm-dual claude/ltt-llm-multijob-audit-43efd3` đánh dấu
patch-equivalent cho 8/9 commit multijob; chỉ `fd9b41b3` (T3 schema) là khác.
Không cherry-pick lại chuỗi T0–T8. Ba file dirty overlap
`runtime_noi_bo/luong.py`, `server/api/chat.py`, `server/api/streaming.py` có
patch-id khác nhau giữa hai source; phải so intent theo D04, không chọn cả file
từ một bên.

`docs/ltt_llm_dual/artifacts/wip_task9_multijob.patch` là `ARCHIVE_ONLY`:
SHA-256 `FADF6CC3FA8A31D0A1E985784A521E94D6FEFE4527961EE33A64DD50B29F3C7F`,
Git blob `449fff00687216a9be2bd14404c6ac9d38eafd4e`; current live multijob diff có
Git blob `f61c9978b0976d4bdb01bc15f277ce11dced368d`. Chúng **không bằng nhau**;
không apply patch lưu trữ.

## Authority và rủi ro bắt buộc giải

- D04 là authority: cửa sync được chờ tối đa 60 giây **sau** idempotency
  commit; bỏ mọi hunk trả busy ngay hoặc chạm provider/GPU trước admission.
- Một `ModelProfile` authority phải dẫn xuất provider model, context/output
  limit, warning, pricing/catalog và per-model admission resource; không giữ
  các hằng số song song.
- Scheduler job và LLM admission queue là hai boundary khác nhau.
- Machine A giữ business admission; machine B chỉ residency/drain fail-closed
  và ghim GPU bằng UUID/PCI.
- CMC baseline đã đổi registry/public API vì Voice. Port theo interface hiện
  hành; không thay nguyên `platform_core/registry.py`, catalog/governance hoặc
  shared server files bằng bản từ lineage cũ.
- Migration dual từng nối vào head cũ `e26c9a41d8b5`. Baseline hiện là
  `d9a1f6c2b3e5`; đọc applied revisions trước rồi tạo forward migration trên
  head hiện hành. Không rewrite ancestry đã apply.
- Không phục hồi `chataistudio`, registry/app-list cũ hoặc provider tombstone.

## Trình tự bắt buộc

1. So snapshot trên với HEAD/status/hash thật; nếu drift, dừng và báo CMC.
2. Tạo bundle/patch/hash manifest ở thư mục tạm ngoài worktree và verify.
3. Seal/commit hai source state riêng sau focused tests + secret scan.
4. Tạo `cmc/llm-dual-reconcile` tại đúng `cmc-base-20260911`; port test trước,
   rồi model profile, D04 reservation/wait, migration và machine-B boundary.
5. Chạy hai check tải trước mọi lệnh nặng; không dùng `--khong-khoa`.
6. Certify theo Task 6 của plan và trả branch/full HEAD, source commits
   kept/skipped, migration head, D04 proof và exact test results cho CMC.

## Cấm

Không merge/push `main`, move baseline, deploy, xóa branch/worktree/ref/archive
hoặc chạm worktree Voice. Final integration và cleanup chỉ do CMC thực hiện sau
handoff xanh.
