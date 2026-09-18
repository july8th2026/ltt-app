# LTT-CMC Voice Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the complete LTT Voice capability onto the immutable CMC baseline without bulk-merging its divergent branch.

**Architecture:** The resumed Voice session seals its current state, creates `cmc/voice-reconcile` from the exact SHA in `docs/LTT_CMC/STATE.md`, and ports capability groups with targeted tests. Migration ancestry is forward-normalized and generated assets are rebuilt rather than binary-merged.

**Tech Stack:** Git, Python 3.13, SQLAlchemy/Alembic, Flask, gettext, JavaScript browser tests, pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`

## Global Constraints

- Execute only after `CMC_SYNC_BARRIER_READY` and only inside the Voice worktree named in `docs/LTT_CMC/HANDOFF_VOICE.md`.
- The baseline is the full SHA in the handoff, never a moving branch name.
- Do not merge/push `main`, deploy, remove a worktree, delete a branch, or edit either LLM worktree.
- Before every heavy run, execute both `python tools\tai_may.py` and `python tools\cua_so_yen.py trang-thai` from the current worktree.
- Keep canonical bytes of historical migrations; add forward migrations when applied-state evidence does not permit reparenting.

---

### Task 1: Seal and verify the Voice source state

**Files:**
- Modify only if still dirty: `apps/ltt_voice/routes/_p_audio.py`
- Modify only if still dirty: `tests/test_508_voice_license_va_curate.py`
- Modify only if still dirty: `tests/test_528_kho_chung_nghe_thu.py`
- Modify only if still dirty: `tools/soat_giong.py`
- Create on the Voice branch: `docs/LTT_VOICE/HOP_NHAT/CMC_SOURCE_STATE.md`

**Interfaces:**
- Produces: a clean, committed Voice source branch and an auditable source HEAD.
- Consumes: exact worktree/branch/HEAD/status from `HANDOFF_VOICE.md`.

- [ ] Compare `git rev-parse HEAD`, `git status --short` and file hashes with the handoff. Stop on unexplained drift.
- [ ] Create a temporary branch bundle plus binary dirty patch under the resolved
  Windows temporary directory. Verify the bundle with `git bundle verify`, the
  patch against the index with `git apply --check --cached`, and record both
  SHA-256 values in `CMC_SOURCE_STATE.md`; never place the backup in a worktree.
- [ ] Finish the four dirty files only within their existing Voice scope; do not import canonical files wholesale.
- [ ] Run `python -m pytest tests/test_508_voice_license_va_curate.py tests/test_528_kho_chung_nghe_thu.py -q`.
- [ ] Run `python tools\scan_source_secrets.py` and commit the Voice session's work with a message describing the completed behavior.
- [ ] Record source branch, old/new HEAD and exact test result in `CMC_SOURCE_STATE.md`; commit that record.

### Task 2: Create a baseline-based integration branch in the same worktree

**Files:**
- Read: `docs/LTT_CMC/HANDOFF_VOICE.md`
- Read: `docs/LTT_CMC/STATE.md`

**Interfaces:**
- Produces: `cmc/voice-reconcile` rooted exactly at `CMC_BASE_SHA`.
- Consumes: clean Voice source branch from Task 1.

- [ ] Verify `git status --porcelain` is empty and `cmc/voice-reconcile` does not exist locally/remotely.
- [ ] Read the 40-character baseline from the handoff into `$cmcBase`; verify it with `git cat-file -e "$cmcBase^{commit}"`.
- [ ] Run `git switch -c cmc/voice-reconcile $cmcBase`.
- [ ] Assert `git merge-base --is-ancestor $cmcBase HEAD` returns 0 and `git rev-parse HEAD` equals `$cmcBase` before any port.

### Task 3: Port Voice persistence and domain capabilities

**Files:**
- Modify: `apps/ltt_voice/tables.py`
- Modify: `apps/ltt_voice/features.py`
- Modify: `apps/ltt_voice/manifest.py`
- Create/modify only as present in source state: `apps/ltt_voice/lan_ngon_ngu.py`
- Create/modify only as present in source state: `apps/ltt_voice/lich_su_nd.py`
- Create/modify only as present in source state: `apps/ltt_voice/giong_vong_doi.py`
- Create/modify only as present in source state: `apps/ltt_voice/nghe_thu_cua_toi.py`
- Test: `tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py`
- Test: `tests/test_522_mot_tham_quyen_lan.py`
- Test: `tests/test_525_lich_su_xoa_trang_thai_suy.py`
- Test: `tests/test_526_nghe_thu_phan_quyet.py`

**Interfaces:**
- Produces: canonical Voice language, history, lifecycle and preview domain APIs.
- Consumes: current CMC registry/model conventions from baseline.

- [ ] Port tests first and run them to prove the capabilities are absent/incomplete on the CMC baseline.
- [ ] Port the minimal domain modules and table/manifest declarations; preserve current canonical registry APIs.
- [ ] Run the four tests above and `tests/test_60_app_registry.py`; all must pass.
- [ ] Run secret scan and commit as `feat: reconcile Voice domain capabilities` with source commit IDs in the body.

### Task 4: Port Voice routes, templates and public API behavior

**Files:**
- Modify: `apps/ltt_voice/routes/_p_audio.py`
- Modify: `apps/ltt_voice/routes/_p_du_an.py`
- Modify: `apps/ltt_voice/routes/_p_giong.py`
- Modify: `apps/ltt_voice/routes/_p_lich_su.py`
- Modify: `apps/ltt_voice/routes/_p_nghe_thu.py`
- Modify: `apps/ltt_voice/routes/_p_tao.py`
- Modify: `platform_core/public_api/catalog.py`
- Modify: `platform_core/public_api/governance.py`
- Modify: `platform_core/public_api/invocation.py`
- Modify: `server/api/jobs.py`
- Modify: Voice templates under `apps/ltt_voice/templates/`
- Test: `tests/test_520_ltt_voice_so_huu.py`
- Test: `tests/test_524_public_api_kiem_truoc.py`
- Test: `tests/test_527_doi_soat_voice.py`

**Interfaces:**
- Produces: one authorization/admission path for Voice web and public API entry doors.
- Consumes: domain functions from Task 3; current canonical scheduler/public API contracts.

- [ ] Port the three focused tests and run them for expected red behavior.
- [ ] Port route/template/public API behavior hunk-by-hunk; never replace whole shared platform files from Voice lineage.
- [ ] Verify the fallback voice cannot cross language lane and every money-spending entry door calls the same preflight authority.
- [ ] Run focused tests plus `tests/test_351_ltt_voice_lifecycle_authz.py`, `tests/test_355_hop_dong_lan_giong.py`, and `tests/test_356_moi_cua_tieu_tien_deu_qua_mot_cong.py` after both load checks.
- [ ] Secret-scan and commit with source commit IDs.

### Task 5: Normalize Voice migrations and derived assets

**Files:**
- Add forward migrations for source intents in `alembic/versions/20260911_1000_voice_ngon_ngu_nguon.py` and `alembic/versions/20260911_1100_voice_lich_su.py`, renaming revision files/IDs if those IDs collide with the CMC graph.
- Keep canonical bytes: `alembic/versions/20260908_1600_voice_license_va_curate.py`
- Modify source: `locale/en/LC_MESSAGES/messages.po`
- Regenerate: `locale/en/LC_MESSAGES/messages.mo`
- Modify atomically: `server/static/ltt.css`
- Modify atomically: `tools/gui/ltt.css`
- Test: `tests/test_508_voice_license_va_curate.py`
- Test: `tests/test_223_nexus_devices.py`

**Interfaces:**
- Produces: one Alembic head and deterministic locale/CSS outputs.
- Consumes: actual applied-revision evidence and canonical migration head from Phase 1.

- [ ] Read applied Alembic revisions from every environment authorized in the handoff; do not mutate an environment.
- [ ] If either Voice revision was applied, create a merge/forward migration; otherwise rebase only its `down_revision` onto the pinned canonical head.
- [ ] Regenerate `.mo` from `.po`; do not binary-merge `.mo`.
- [ ] Apply the same Voice CSS change to both intentional mirrors and assert byte equality.
- [ ] Run single-head/revision tests and Voice migration tests after both load checks.
- [ ] Secret-scan and commit migration/assets separately from domain code.

### Task 6: Certify the Voice handoff branch

**Files:**
- Modify: `docs/LTT_VOICE/HOP_NHAT/CMC_SOURCE_STATE.md`

**Interfaces:**
- Produces: clean `cmc/voice-reconcile` HEAD ready for CMC final integration.
- Consumes: Tasks 3–5.

- [ ] Run the Voice test set selected by `python tools\gate.py --pham-vi ltt_voice` after both load checks.
- [ ] If frontend/user flow changed, run the real local browser flow, inspect console and failed network requests, and record screenshots under the existing Voice evidence convention.
- [ ] Run `python tools\gate.py --doi` after both load checks; require PASS.
- [ ] Record branch, full HEAD, baseline SHA, source commits kept/skipped, migration head and exact test/browser evidence.
- [ ] Commit the handoff record and report it to CMC. Do not merge `main`.
