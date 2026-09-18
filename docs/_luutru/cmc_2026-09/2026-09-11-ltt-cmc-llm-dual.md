# LTT-CMC LLM Dual-Model Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the multijob foundation and dual-model recovery design onto the immutable CMC baseline as one LLM workstream.

**Architecture:** Seal both source worktrees, treat the recovery WIP patch as duplicate evidence, and build `cmc/llm-dual-reconcile` from the exact CMC SHA. Port admission/model/runtime capabilities onto current ToolSpec V2 and scheduler contracts; never restore the old `chataistudio` tree.

**Tech Stack:** Git, Python 3.13, SQLAlchemy/Alembic, Flask streaming, llama-swap, pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`

## Global Constraints

- Execute only after `CMC_SYNC_BARRIER_READY` and use both actual worktrees in `docs/LTT_CMC/HANDOFF_LLM_DUAL.md`.
- Do not recreate or apply the retired WIP Task 9 patch; it duplicated the live
  Multi-Job dirty diff and was removed after final source reconciliation.
- Do not restore `chataistudio`, old registries, old app lists or whole shared files from the 450-commit-old lineage.
- D04 is authoritative: sync admission may wait at most 60 seconds after idempotency commit.
- Machine A owns business admission; machine B only executes residency/drain fail-closed and binds GPUs by UUID/PCI.
- Do not merge/push `main`, deploy, remove worktrees or touch the Voice worktree.

---

### Task 1: Seal both LLM source states

**Files:**
- Existing dirty: `platform_core/job_runner.py`
- Existing dirty: `platform_core/llm/tham_so_da_luot.py`
- Existing dirty: `platform_core/runtime_noi_bo/luong.py`
- Existing dirty: `server/api/chat.py`
- Existing dirty: `server/api/streaming.py`
- Existing untracked: `docs/ltt_llm_dual/`
- Existing untracked: `docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md`

**Interfaces:**
- Produces: clean committed source branches and verified duplicate-patch evidence.
- Consumes: exact heads/status/hashes from the LLM handoff.

- [ ] Compare both worktrees to the handoff; stop on unexplained drift.
- [ ] Create temporary verified bundles for both source branches, a binary patch
  for the five dirty tracked files and a hash manifest/copy of all untracked
  recovery documents under the resolved Windows temporary directory. Verify
  bundles with `git bundle verify`, the patch with `git apply --check --cached`,
  and every copied artifact by SHA-256; do not write backups into a worktree.
- [ ] Verify the WIP patch payload still equals the multijob dirty `git diff`; record its SHA-256 and mark it `ARCHIVE_ONLY`.
- [ ] Finish and test the five dirty files on the multijob source branch without changing D04.
- [ ] Commit multijob dirty work after secret scan.
- [ ] Commit recovery documents/spec on the recovery source branch after secret scan; do not apply the patch.

### Task 2: Create the LLM integration branch from CMC baseline

**Files:**
- Read: `docs/LTT_CMC/HANDOFF_LLM_DUAL.md`
- Read: `docs/LTT_CMC/STATE.md`
- Create: `docs/ltt_llm_dual/CMC_SOURCE_STATE.md`

**Interfaces:**
- Produces: `cmc/llm-dual-reconcile` rooted at the full `CMC_BASE_SHA`.
- Consumes: clean source branches from Task 1.

- [ ] In the multijob worktree, verify status is clean and the integration branch does not exist.
- [ ] Verify the full baseline commit from the handoff exists, then switch to `cmc/llm-dual-reconcile` at that exact SHA.
- [ ] Copy only the reviewed recovery documents from the recovery source commit; omit the duplicate WIP patch from canonical history.
- [ ] Record both source branches/HEADs, baseline SHA and patch-equivalence result in `CMC_SOURCE_STATE.md`; commit.

### Task 3: Consolidate model profiles and per-model admission resources

**Files:**
- Modify: `platform_core/llm/canonical.py`
- Modify: `apps/ltt_llm/features.py`
- Modify: `apps/ltt_llm/manifest.py`
- Modify: `apps/ltt_llm/ngan_sach.py`
- Modify: `platform_core/providers.py`
- Modify: `llm_gateway/catalog.py`
- Modify if its context metadata disagrees: `platform_core/gia_von.json`
- Modify: `platform_core/public_api/catalog.py`
- Modify: `platform_core/public_api/governance.py`
- Modify: `platform_core/registry.py`
- Test: `tests/test_952_so_ngan_sach_mo_hinh.py`
- Test: `tests/test_954_admission_ngan_sach.py`
- Test: `tests/test_60_app_registry.py`

**Interfaces:**
- Produces: one `ModelProfile` authority per public model and per-model admission pool identifiers.
- Consumes: existing canonical alias API and ToolSpec V2 contracts.

The canonical record introduced by this task is:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    alias: str
    provider_model: str
    context_window: int
    max_output_tokens: int
    admission_resource: str
    supports_vision: bool
```

- [ ] Port tests first for the 204800 text context, the chosen vision context, derived warning/catalog limits, two distinct admission pools and duplicate alias rejection.
- [ ] Run the focused tests and observe failures against contradictory constants/scalar pool behavior.
- [ ] Implement a frozen `ModelProfile` record containing alias, provider model, context window, output limit, admission resource and public capability metadata.
- [ ] Derive provider warnings, budget checks, manifest/catalog metadata and ToolSpec resource selection from that record; remove copied numeric truths only after every caller migrates.
- [ ] Run focused tests plus `tests/test_313_llm_admission.py`; secret-scan and commit.

### Task 4: Port multijob reservation and D04 wait behavior

**Files:**
- Modify: `platform_core/job_runner.py`
- Modify: `platform_core/llm/admission.py`
- Modify: `platform_core/llm/luat_nhan.py`
- Modify: `platform_core/llm/phong_cho.py`
- Modify: `platform_core/llm/tham_so_da_luot.py`
- Modify: `platform_core/llm/thanh_toan.py`
- Modify: `platform_core/llm/uoc_moi.py`
- Modify: `platform_core/runtime_noi_bo/luong.py`
- Modify: `server/api/chat.py`
- Modify: `server/api/streaming.py`
- Test: `tests/test_953_luat_nhan.py`
- Test: `tests/test_955_phong_cho.py`
- Test: `tests/test_956_uoc_token_moi.py`

**Interfaces:**
- Produces: centralized `luat_cho`, atomic per-model reservation and bounded sync wait after idempotency commit.
- Consumes: model/admission resource mapping from Task 3.

- [ ] Port tests proving reservation is atomic, queue rank is interaction-before-background, jobs scheduler ranking remains independent, timeout is 60 seconds, and provider/GPU is not touched before admission.
- [ ] Port multijob code hunk-by-hunk; discard source hunks that return immediate busy contrary to D04.
- [ ] Make sync and streaming entry doors call the same central wait/reservation policy; preserve current idempotency and credit semantics.
- [ ] Run the focused tests plus `tests/test_272_cua_streaming.py`; secret-scan and commit.

### Task 5: Normalize LLM schema and machine-B execution boundary

**Files:**
- Port intent from: `alembic/versions/20260911_1200_llm_multijob_ngan_sach.py`
- Modify: `platform_core/models.py`
- Modify: `llm_gateway/deploy/llama-swap.yaml`
- Modify: `llm_gateway/config.py`
- Modify: `llm_gateway/api.py`
- Modify: `llm_gateway/trong_tai.py`
- Modify: `llm_gateway/don_dep.py`
- Modify: `llm_gateway/tren_gpu.py`
- Test: `tests/test_950_ghim_gpu_may_b.py`
- Test: `tests/test_951_mot_nguon_so_slot.py`
- Test: `tests/test_223_nexus_devices.py`

**Interfaces:**
- Produces: one Alembic head, execution lease/waiter schema, and one business slot authority.
- Consumes: applied revision evidence and the pinned canonical head.

- [ ] Read applied revisions without migrating any environment.
- [ ] Port execution lease KV and `llm_waiters` schema through a forward migration based on the canonical head; never attach the old migration directly to its historical parent if applied-state evidence is unknown.
- [ ] Make machine-B configuration expose residency/drain only; remove independent business-slot decisions and bind device identity by UUID/PCI.
- [ ] Run one-head/schema tests and the two GPU-authority tests after both load checks; secret-scan and commit.

### Task 6: Certify the LLM handoff branch

**Files:**
- Modify: `docs/ltt_llm_dual/CMC_SOURCE_STATE.md`

**Interfaces:**
- Produces: clean `cmc/llm-dual-reconcile` HEAD ready for CMC final integration.
- Consumes: Tasks 3–5.

- [ ] Run `python tools\gate.py --pham-vi ltt_llm` after both load checks.
- [ ] Run the current mock/CPU/DB multijob suite; GPU/live checks remain explicitly `NOT_RUN` unless the approved exclusive GPU window is available.
- [ ] Run `python tools\gate.py --doi` after both load checks and require PASS.
- [ ] Record branch/full HEAD, baseline SHA, source commits kept/skipped, migration head, D04 proof and exact tests.
- [ ] Commit the handoff record and report it to CMC. Do not merge `main`.
