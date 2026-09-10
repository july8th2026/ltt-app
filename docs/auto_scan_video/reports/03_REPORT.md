# PHASE 03 REPORT — Execution / Billing / Resource ADR Freeze

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- pre-existing dirty: none (only my untracked `docs/auto_scan_video/`)
- previous gate: Phase 02 **PASS** (`auto_scan_mvp_v1` frozen)
- allowed change scope: **docs / ADRs only**

## Trace performed

`platform_core/jobs.py` — `submit` 99, `claim` 144, `heartbeat` 207, `mark_admitted` 213,
`mark_provider_dispatched` 232, `mark_provider_rejected` 246, `defer_resource` 259,
`mark_ambiguous` 274, `complete` 304, `cancel` 318, `fail` 337, `reclaim_orphans` 379;
states `models.py:235-239`.
`platform_core/job_runner.py` — `JobContext` 79-180, `_chay_handler` 460,
`_provider_failure_kind` 573, `_quyet_toan_credit` 652, `_hoan_credit` 668,
`_quet_giu_cho_treo` 723.
`platform_core/credit.py` — 251, 260, 393, 439, 548, 643.
`platform_core/agent/` — `executor.tick` 223, `actual_cost` 130, `runs.submit_child` 106,
`budget.approve` 71 / `settle` 105 / `ensure_can_spend` 98; `apps/agent/jobs.py:19-41`.
`platform_core/app_projects.py:85` (optimistic concurrency precedent).
`platform_core/gpu_lease.py`, `gpu.py:103`, `gpu_claims.py`.
`platform_core/storage.py:80`, `upload_sessions.py`.
`platform_core/registry.py` — `AppManifest` 192-390, `discover` 877, `credit_for` 1024.
`alembic/versions/20260831_1600_voice_du_an.py` + `20260831_1000_voice_owner_uuid.py`.
`apps/{ltt_voice,ltt_llm,autosubvideo,anhnoibo}/manifest.py`.

## Decisions

All ten in [`../adr/ADR-001-execution-billing-resource.md`](../adr/ADR-001-execution-billing-resource.md).
The three that carry the phase:

**D1/D2 — take the `AgentRun` pattern, leave the `AgentRun` table.** The precedent is right
about orchestration (tick-then-re-enqueue, never block a worker) and wrong for us about
storage. `AgentRun` carries `budget_max`/`approved_at`/`approved_by`/`decision_log`/`version`
and backs `AgentWorkflow` = Canvas; a fixed pipeline has no plan to approve and no graph to
edit, so inheriting it puts O18/I17 one convenience commit from violation.

Its `checkpoint` JSON is also read-modify-written by every tick and is safe *only* because
every writer happens to pass through `get_owned(..., lock=True)` — correctness resting on a
discipline nothing enforces. **Normalized `asv_stage` rows, one per `(run, stage)`, remove
the hazard instead of guarding it:** two stages finishing simultaneously write two different
rows and cannot collide. This is the one place the ADR deliberately improves on the
precedent rather than copying it.

**D4 — settle on measured cost, never recomputed price.** `agent/executor.actual_cost`
prices `credit_for(job_type, params) × attempts` and ignores `result["credit_cost"]`; it
charges for what was **asked**, not what was **delivered**. CLAUDE.md records that exact
defect reaching production twice (H38 23/08; H37/D-051 24/08 — "asked 4 images, got 2,
charged 4"). Auto Scan's cost is inherently variable — TTS characters, LLM tokens, GPU
seconds — so reusing that function would ship a known money bug on day one. RISK-00-05 closed
by construction: `actual = Σ asv_stage.credit_actual`, each written from real consumption.

Double-charging is made *structurally impossible* rather than merely avoided: child jobs go
through `jobs.submit` (never `submit_with_credit`), so they hold nothing, and
`_quyet_toan_credit` already no-ops at zero hold (`job_runner.py:660`).

**D5 — one customer app + three hidden runtime executors, and a rule for the fourth case.**
Per-job routing does not exist (`jobs.py:158-164` filters by app), so guardrail §3's option 2
is the answer, and today's contract already supports it (`surface="runtime"`,
`catalog_parent`, free-form `requires`; live precedent `apps/anhnoibo`). No platform-core
change (O20).

The non-obvious part is what *doesn't* get an executor. CONTENT_PROCESS and VOICE_SYNTHESIS
delegate to `ltt_llm.chat` and `ltt_voice.synthesize` as child jobs; TRANSCRIBE does **not**
delegate to `autosubvideo.transcribe` but wraps its runner module — because that manifest
declares `requires=("ffmpeg",)` while declaring GPU VRAM for `transcribe`/`diarize`
(RISK-00-11), and delegating would inherit the mis-declaration and route GPU work onto an
ffmpeg lane. Generalized: **delegate when the target's manifest is honest and its contract
public; wrap the code when it is not.**

**Inherited from Phase 02 and load-bearing here:** because `auto_scan_mvp_v1` copies the
video stream, RENDER declares `ffmpeg`, not `gpu`. The longest stage stops competing for a
card, and MVP's GPU surface shrinks to AUDIO_PREPARE + TRANSCRIBE.

## Changes

| Path | Change | Why | In scope? |
|---|---|---|---|
| `docs/auto_scan_video/adr/ADR-001-execution-billing-resource.md` | new | the frozen architecture | yes |
| `docs/auto_scan_video/reports/03_REPORT.md` | new | mandatory closeout | yes |
| `docs/auto_scan_video/STATE.md` | updated | ADR summary, invariant ledger, phase history | yes |

No production source, test, migration or manifest touched.

## Tests

| Command | Result |
|---|---|
| `python tools/scan_source_secrets.py` | `Findings: 0 — RESULT: PASS` |

Full gate not re-run: docs-only change under `docs/auto_scan_video/`, which no gate step
reads, against a certified baseline from earlier today at the same SHA. Phase 04 is the first
code-touching phase and re-runs it against the §4a-iv regression contract.

## Invariant regression

Not applicable (no invariant tests yet — Phase 04 builds them). The ADR assigns **every** one
of I1–I14 plus I18/I19 an owning mechanism and a planned test; the table is in the ADR and
mirrored into STATE. I7 is the one deferred to another ADR (Phase 07), deliberately: it is a
credential-allocator question, not an execution one.

## Diff review
- changed paths: `docs/auto_scan_video/` only
- no generated artifacts, media or binaries; secret scan clean

## Risks / external evidence pending

Closed here: **RISK-00-03** (AgentRun leak — table not reused), **RISK-00-04** (checkpoint
JSON — normalized rows), **RISK-00-05** (settlement recomputes — measured cost).
Reduced: **RISK-00-01** (routing — resolved in design; verification moves to Phase 05).

New:
- **RISK-03-01 (P1)** — delegating CONTENT/VOICE as child jobs assumes `ltt_llm.chat` and
  `ltt_voice.synthesize` accept parameters produced by a caller that is not their own UI.
  Their public API tools (`text.chat`, `speech.ltt`) suggest they do, but this is **not yet
  verified**. Closes in Phases 11/12; if a contract gap appears, the fallback is to wrap the
  code as TRANSCRIBE does.
- **RISK-03-02 (P2)** — `asv_run.credit_held` must be estimated before the source is
  transcribed, yet TTS and LLM cost depend on transcript length. The estimate must therefore
  be derived from **duration** with headroom, and D4's ceiling guard turns a bad estimate
  into a clean policy failure rather than an overspend. Phase 05 must exercise the guard.
- **RISK-03-03 (P2)** — three new app directories increase the surface `test_60` (platform
  must not hardcode app names) and `tools/lint_app_contract.py` police. Expected to pass;
  confirmed in Phase 05.

Still open and unchanged: RISK-00-02, -06, -07, -08, -09, -10, -11, -12, -14, -15, -16,
RISK-01-01, RISK-02-01…03.

## Exit gate

**PASS.**

Gate text: *"PASS only when billing cannot be double-owned, worker routing is unambiguous,
executable queue SSOT is unique, and provider/artifact crash semantics are specified."*

| Condition | Evidence |
|---|---|
| billing cannot be double-owned | D4. Children use `jobs.submit` ⇒ zero hold; `_quyet_toan_credit` already no-ops at zero hold (`job_runner.py:660`). Not policy — mechanism. |
| worker routing unambiguous | D5. Every one of the nine stages maps to exactly one app with exactly one `requires` tuple; the delegate-vs-wrap rule covers the two stages that are neither. |
| executable queue SSOT unique | D1. `platform_core.jobs` only; coordinator re-enqueues instead of blocking; no pool, loop or second queue introduced. |
| provider crash semantics | D4 retry accounting + reuse of `provider_state` / `mark_ambiguous`: ambiguous dispatch is terminal and charged, because the provider may have billed us. |
| artifact crash semantics | D7's five ordered steps with a defined recovery for each of the four gaps, and keys derived from the fingerprint so re-writes are idempotent. |

Prompt 03 additionally requires every invariant I1–I14 to have an owner or planned test —
delivered, with I18/I19 added.

## Next phase prerequisites

Phase 04 (Invariant & Safety Test Harness) is the **first phase to write code**, so:
1. it runs in `D:\LTTSTUDIOSAPP-asv` and re-runs the full gate against the §4a-iv contract;
2. its scope is guard tests only — no pipeline, no app directory, no migration;
3. the seven tests listed in ADR-001 "Tests required" are its backlog, plus the static check
   forbidding `gpu_arbiter` on Auto Scan paths (D6);
4. tests that need a run/stage table must use in-memory or fixture doubles — the real
   migration lands in Phase 05, and Phase 04 must be able to go **red before** it goes green.
