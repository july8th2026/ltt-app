# PHASE 00 REPORT — Repository Provenance and Read-only Audit

## Entry evidence
- starting SHA: `c31b1aeeee2f1831840b78f4d9ded94cfab09bc0`
- branch: `admin-mvp-v3` (main branch for PRs: `master`)
- pre-existing dirty files: `server/templates/vps_dieu_khoan.html` (modified, **not touched
  by this phase**); untracked `docs/audit_ltt_llm/evidence/` (belongs to a concurrent session)
- previous gate: none — Phase 00 is the first phase
- allowed change scope: documentation under `docs/auto_scan_video/` only. No production
  source, dependency, migration or test behaviour edits.

## Trace performed

**Platform execution / money / resource, end to end**
`platform_core/registry.py` (app contract, `AppManifest`, `ToolSpec`, `discover`,
`credit_for`) · `platform_core/jobs.py` (`submit`, `claim`) ·
`platform_core/job_submit.py` (`submit_with_credit`) · `platform_core/job_runner.py`
(`JobContext`, `_chay_mot_job`, `_giu_gpu`, `_chay_handler`, `_quyet_toan_credit`,
`_hoan_credit`, `_provider_failure_kind`, `_mot_luot_bao_tri`, `run_forever`) ·
`platform_core/credit.py` (`giu_cho`, `quyet_toan`, `hoan`, `so_da_giu`, `giu_cho_treo`,
`tu_hoan_treo`) · `platform_core/gpu_lease.py`, `gpu.py`, `gpu_claims.py` ·
`platform_core/storage.py` (`Storage.promote`, `url_for`, `put_url`, `R2Storage`) ·
`platform_core/upload_sessions.py` (full staging→confirm→promote→compensate→sweep→reconcile) ·
`platform_core/app_projects.py` · `platform_core/api_pool.py` + `api_keys.py` +
`models.py:ApiKey` · `platform_core/media.py` · `platform_core/leases.py` ·
`platform_core/models.py` (`Job`, `AgentRun`, `AgentWorkflow`, `AppProject`).

**Agent run/executor primitives** (guardrail §1 candidate)
`platform_core/agent/executor.py` (`tick`, `_sync_children`, `actual_cost`) ·
`agent/runs.py` (`get_owned`, `submit_child`, `children`) · `agent/budget.py`
(`quote`, `approve`, `ensure_can_spend`, `settle`, `cancel`) · `apps/agent/jobs.py`.

**Existing app precedents**
`apps/autosubvideo/` (whisperx, segmenter, burn, ass_builder) · `apps/upscalevideo/` ·
`apps/taoclipngan/` + vendored `cutclipshort/` · `apps/ltt_voice/` (manifest, jobs, tables) ·
`apps/ltt_llm/` · `apps/anhnoibo/` (the `catalog_parent` precedent).

**Legacy trees (read-only)**
`D:\FULL AUTO VIDEO\BOT_TRANSCRIPT\Bot_Whisper_FULL\engine\` ·
`D:\FULL AUTO VIDEO\Bot_PausePipeline\engine\` + `utils\` ·
`D:\FULL AUTO VIDEO\DUNGVIDEO-FULL\engine\` ·
`D:\Cut_only ver2\nerf_engine\` + `stages\` + the three `bot_*.py` shells.

Full evidence with line numbers: [`../DEPENDENCY_MAP.md`](../DEPENDENCY_MAP.md),
[`../CAPABILITY_MATRIX.md`](../CAPABILITY_MATRIX.md).

## Decisions / ADRs

No architecture chosen — Prompt 00 forbids it ("do not choose architecture by preference
yet; collect evidence"). Four *findings* that will drive the Phase 03 ADR:

1. **The V2 execution/billing model already exists in this platform.** `apps/agent` +
   `platform_core/agent` implement tick-and-re-enqueue orchestration (no worker held for
   polling), row-locked checkpoint mutation, run-level single hold/settle, and children
   that create no holds of their own. This is not a design to invent; it is a pattern to
   copy with its table left behind.
2. **`AgentRun` itself must not be reused.** Approval (`approved_at`/`approved_by`),
   budget-quote versioning and Canvas (`AgentWorkflow`) live in that family. Importing it
   imports semantics O18/I17 forbid.
3. **Worker routing is app-scoped, and the manifest is already inconsistent about it**
   (`requires` per app, `gpu_vram_mb`/`max_runtime_s` per job type). The
   hidden-runtime-executor option in `EXECUTION_GUARDRAILS §3.2` is supported by the
   existing contract (`surface="runtime"`, `catalog_parent`, free-form `requires`) with a
   real precedent in `apps/anhnoibo`. No core change is indicated.
4. **Two migration targets are effectively free, and two are not.** `Cut_only ver2/nerf_engine`
   has zero legacy-shell coupling; `apps/autosubvideo` and `apps/ltt_voice`/`apps/ltt_llm`
   are already in-platform. The FULL_AUTO_VIDEO transcript/pause/DUNGVIDEO engines each
   carry a `gpu_arbiter` import that is an I11 violation on copy.

## Changes

| Path | Change | Why | Within scope? |
|---|---|---|---|
| `docs/auto_scan_video/STATE.md` | new | handoff SSOT required by START_HERE §7 | yes |
| `docs/auto_scan_video/DEPENDENCY_MAP.md` | new | Prompt 00 items 3–8, 10 | yes |
| `docs/auto_scan_video/CAPABILITY_MATRIX.md` | new | Prompt 00 item 7 | yes |
| `docs/auto_scan_video/RISK_REGISTER.md` | new | Prompt 00 items 9, 10 | yes |
| `docs/auto_scan_video/BASELINE_COMMANDS.md` | new | Prompt 00 "produce a list of baseline commands" | yes |
| `docs/auto_scan_video/reports/00_REPORT.md` | new | mandatory closeout | yes |

No production source, test, migration, dependency or manifest file was created, modified,
renamed or deleted. `docs/auto_scan_video/adr/` and `docs/auto_scan_video/audit/` were
created empty for later phases.

## Tests

| Command | Before | After | Evidence |
|---|---|---|---|
| `python tools/gate.py --vong-lap` | not established | `RESULT: FAIL (2/22)` **[CAY DA DOI GIUA CHUNG — KHONG DUNG LAM BANG CHUNG]** | see below |

Ran twice (~16:10, ~16:14). Both failed at step `bo qua im lang`
(`tests/test_306_banh_coc_bo_qua_va_dich.py::test_bo_qua_hien_tai_dat_moc`, the silent-skip
ratchet). The two runs reported **different skip sets** and the gate printed its own
mid-run-mutation warning.

Cause established, not assumed: `ListAgents` at 16:16 showed two live interactive peer
sessions in this same working tree (`lttstudiosapp-01`, `lttstudiosapp-bb`, both started
18 min prior), and `docs/audit_ltt_llm/evidence/` carried an mtime of 16:09 — work that is
not this phase's.

Phase 00 changed no executable code, so this failure is **not attributable to this phase**,
and O21 forbids repairing it while auditing. It is handed to Phase 01 as baseline debt
together with the precondition that produced it.

## Invariant regression

Not applicable. No invariant tests exist yet — Phase 04 creates them. The invariant
**ledger** is opened in STATE with each invariant's current mechanism and status.

## Diff review
- changed paths: `docs/auto_scan_video/**` only (6 new markdown files, 2 empty dirs)
- `git status` confirms `server/templates/vps_dieu_khoan.html` remains modified and
  untouched, and `docs/audit_ltt_llm/evidence/` (peer session) untouched
- secret scan: no credential, token, key or `.env` content was copied into any artifact.
  Legacy `credentials.json` / `token.json` / `secrets/oauth/` were **noted by path only**
  and never opened (RISK-00-12)
- no generated media, no binaries, no dependency changes

## Risks / external evidence pending

15 risks opened — see [`../RISK_REGISTER.md`](../RISK_REGISTER.md). Release-blocking P0s:
RISK-00-01 (routing), -02 (silent no-execution), -03 (AgentRun leak), -04 (checkpoint
concurrency), -05 (settlement recomputes instead of measuring), -07 (legacy GPU plane on
extraction), plus P1 RISK-00-06 (credential owner scope never read).

Gaps recorded honestly: GAP-00-A (pack's mandatory repo/exclusion report absent locally —
resolved by precedence), GAP-00-B (QC policy has no source anywhere — it is new code),
GAP-00-C (no inherited engine tests — every extraction needs a parity fixture first),
GAP-00-D (smart-cut/reframe deliberately left unclassified for Phase 02).

**External evidence pending:** none blocking Phase 00. Real-runtime evidence (GPU, models,
providers) is not required by this gate.

## Exit gate

**PASS.**

Gate text: *"PASS only when every logical MVP stage has at least one evidence-backed
source/target plan or an explicit GAP, and the platform execution/money/resource mechanisms
are traced end-to-end."*

- All nine MVP stages covered — eight with an evidence-backed source, QC with explicit
  GAP-00-B. Table: `CAPABILITY_MATRIX.md` § "Stage-to-source coverage check".
- Execution traced: `job_submit → jobs.claim → job_runner → handler → settle`, with the
  claim predicate and its app-granularity limitation quoted from source.
- Money traced: `credit_for → giu_cho → quyet_toan/hoan`, plus stranded-hold sweep, plus
  the run-level alternative in `agent/budget.py`.
- Resource traced: `gpu_lease.acquire/hold → gpu.env_for → JobContext.gpu_env`, and the
  five legacy `gpu_arbiter` call sites that must not survive migration.

The failing repo gate does not block this gate: Phase 00's exit condition is evidential
coverage, no code was changed, and the failure is documented, attributed and handed on
rather than hidden or repaired.

## Next phase prerequisites

1. **Resolve the concurrent-session hazard before Phase 01 records any baseline.** Two live
   sessions share this tree; no gate result is trustworthy until there is a file-boundary
   agreement or a quiet tree. This is a precondition, not a nicety — Phase 01's entire
   product is a trustworthy BEFORE state.
2. Phase 01 runs `python tools/gate.py` (full) and `python tools/test_nhanh.py`, records
   pass/fail/skip verbatim, and freezes it. It does **not** fix the `bo qua im lang`
   ratchet failure; it records it as pre-existing debt with an owner.
3. Phase 01 stays read-only for production behaviour (O21, V1 finding A09).
