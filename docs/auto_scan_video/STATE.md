# AUTO SCAN VIDEO — STATE V2

> Handoff SSOT for the V2 prompt pack. Read this after the governance docs and before the
> current phase prompt (`START_HERE.md` read order §7).
> Pack location: `G:\My Drive\AI\A LTT AII\Auto_Scan_Video_Claude_Code_Prompt_Pack_V2\auto_scan_video_prompt_pack_v2`

## Repository baseline
- repo: `D:\LTTSTUDIOSAPP` (working tree). Reference-only: `D:\FULL AUTO VIDEO`,
  `D:\Cut_only ver2`. Pack-mandated snapshot `giaitritruyenthongltt-spec/Tailieuhethong`
  not cloned — see GAP-00-A / RISK-00-13.
- branch: `admin-mvp-v3` (PR target `master`)
- baseline SHA: `c31b1aeeee2f1831840b78f4d9ded94cfab09bc0`
- current SHA: `c31b1aeeee2f1831840b78f4d9ded94cfab09bc0`
- pre-existing dirty paths: `server/templates/vps_dieu_khoan.html` (M);
  `docs/audit_ltt_llm/evidence/` (untracked, **owned by a concurrent session**)
- environment/runtime: Windows 10 Pro, PowerShell 5.1 + Git Bash, Python 3.13,
  PostgreSQL, port 8100, Cloudflare Tunnel. Not the production machine
  (`C:\LTTPlatform` absent ⇒ development tree).

> ✅ **RISK-00-16 CLOSED since Phase 01.** Two live peers were writing to the main tree and
> the gate refused to certify any run there. Resolved by isolating into
> `D:\LTTSTUDIOSAPP-asv` (see the box below); every gate result from Phase 01 onward carries
> no tree-mutation warning. The lines above describe the **main tree** at baseline and are
> kept for provenance, not as current state.

## Current phase
- phase: **14 — Composer & Render Manifest**
- status: IN_PROGRESS
- gate: NOT_EVALUATED

**Invariant regression subset — run after every edit (~2 s):**
```bash
python -m pytest tests/test_400_asv_bat_bien_thi_hanh.py tests/test_401_asv_ranh_gioi_va_artifact.py -q
```

> 🔴 **ALL WORK HAPPENS IN `D:\LTTSTUDIOSAPP-asv` (branch `phien/asv`), NOT the main tree.**
> Created with `python tools/cay_rieng.py tao asv`. Merge back with
> `git -C "D:\LTTSTUDIOSAPP" merge phien/asv`, then `python tools/cay_rieng.py go asv`.
> ⛔ **Never deploy from this worktree** — this machine is production and
> `setup/2-cai-dat.ps1` copies the whole tree to `C:\LTTPlatform`.

**Frozen baseline (certified, no tree-mutation warning):**
`python tools/gate.py --phien asv` → `RESULT: FAIL (4/26)`, test step 63 passed / 4 failed.
A later phase regresses only if it breaks a step **outside**
`{bo qua im lang, dich thieu ban EN, system profile, bo test::test_306}`.

## Frozen MVP
- profile/version: **`auto_scan_mvp_v1` — FROZEN in Phase 02.** Authority:
  [`MVP_CONTRACT.md`](MVP_CONTRACT.md). Changing it requires an ADR.
- **product**: Vietnamese video **localization (dubbing)**. Same picture, same length,
  Vietnamese voice-over the original music/SFX. Not an editor.
- required stages: MEDIA_PREPARE → AUDIO_PREPARE → TRANSCRIBE → CONTENT_PROCESS →
  VOICE_SYNTHESIS → TIMING_ALIGN → COMPOSE → RENDER → QC
- 🔑 **the video stream is COPIED, never re-encoded** (D-ASV-03). Follows from deferring all
  picture-altering features: no MVP stage changes a pixel. ⇒ **RENDER needs no GPU**
  (`requires=("ffmpeg",)`), no generational loss, and `video/webm` is excluded (VP8/VP9
  cannot be copied into MP4).
- required despite being heavy: **source separation** (`htdemucs`) — it removes the *original
  voice*, without which the dub is unusable. SFX/music preservation comes free with it.
- optional/deferred (engines exist, deliberately unused): smart-cut, scene selection, YOLO
  reframe, motion/zoom, subtitles
- out of scope: transitions (nothing is cut, so there is no join), upscale (separate shipped
  product), music replacement, any social source/publish

## Architecture ADR summary
**FROZEN in Phase 03** — [`adr/ADR-001-execution-billing-resource.md`](adr/ADR-001-execution-billing-resource.md).

- **executable queue SSOT**: `platform_core.jobs` only. Coordinator job `asv.advance` ticks
  once then **re-enqueues itself**; it never blocks a worker waiting for children (D1).
- **run/checkpoint owner**: Auto-Scan-owned tables `asv_run` + `asv_stage`
  (`table_prefix="asv"`). **Normalized stage rows, not a JSON checkpoint** — two stages
  finishing at once write different rows and cannot collide (D2). `AgentRun` pattern copied,
  `AgentRun` table rejected (carries approval + Canvas semantics).
- **child job mapping**: child `Job` rows with `plan_id = run.id`, `step_id = stage` (D1/D3).
  `asv_stage.status` projects platform job states; no second public state machine.
- **billing owner**: one hold on `run.id`; children via plain `jobs.submit` ⇒ zero hold ⇒
  `_quyet_toan_credit` no-ops on them. 🔑 **`actual = Σ asv_stage.credit_actual` (measured),
  never `agent/executor.actual_cost` (recomputed)** — that function charges for what was
  asked, not delivered, and has caused two production money bugs (D4).
- **worker routing**: one customer app `auto_scan_video` (`api`) + hidden runtime executors
  `asv_media` (`ffmpeg`) and `asv_gpu` (`gpu`), all `catalog_parent="auto_scan_video"`.
  TRANSCRIBE **wraps** autosubvideo's runner, because that manifest is mis-declared
  (RISK-00-11). Rule: *delegate when the target manifest is honest and public; wrap when not.*
  No platform-core change (D5).
  ⚠️ **D5 AMENDED in Phase 11** — CONTENT was to be delegated as an `ltt_llm.chat` child job.
  Delegation cannot chunk / merge / detect a short response, and `asv_stage` holds one
  `job_id` per stage, so CONTENT calls `platform_core/llm/dieu_phoi` directly and runs on the
  **api lane inside `auto_scan_video`**. What D5 protected is intact: no second HTTP path, no
  self-selected key, platform-owned dispatch safety. VOICE's delegation is re-checked in
  Phase 12. See [`reports/11_REPORT.md`](reports/11_REPORT.md).
- **resource model**: `gpu_lease` + `ctx.gpu_env()`; handlers never pick a card. RENDER is
  `ffmpeg`-only thanks to the copy path (D6).
- **asset model**: five-step completion — engine → validate → `storage.promote` → persist
  refs+fingerprint → commit; recovery defined for all four crash gaps; keys are
  `asv/{owner}/{run}/{stage}/{fingerprint}` so re-writes are idempotent (D7).
- **cache**: fingerprint over stage+contract+engine version+settings+upstream hashes; a hit
  needs matching fingerprint **and** live valid outputs; lookup always owner-scoped (D8).
- **credential scope model**: unchanged allocator; Auto Scan uses the platform pool only.
  `ApiKey.owner_user_id` written-but-never-read stays open → ADR-002, Phase 07 (RISK-00-06).

## Invariant ledger

> Since Phase 03 the **authoritative** owner/test mapping is the table in
> [`ADR-001`](adr/ADR-001-execution-billing-resource.md) § "Invariants protected". The table
> below records what the *platform* provides today, which is what Phase 04 must write guards
> against. Rows marked GAP are the ones Auto Scan must build.

| Invariant | Status | Test/evidence |
|---|---|---|
| I1 platform queue SSOT | MECHANISM EXISTS | `platform_core/jobs.py:144 claim()`; `models.py:252` docstring. No test yet owned by this project. |
| I2 atomic money boundary | MECHANISM EXISTS | `job_submit.py:submit_with_credit` — price→submit→hold in one txn, caller commits once |
| I3 one billing owner per run | NOT DECIDED | precedent `agent/budget.py:90,113`; Phase 03 decides, Phase 04 tests |
| I4 retry accounting | MECHANISM EXISTS | `jobs.submit` dedupe + `Job.retry_of_id`; `submit_with_credit` re-holds only when `so_da_giu == 0` |
| I5 provider ambiguity safety | MECHANISM EXISTS | `Job.provider_state`/`provider_dispatched_at`; `JobContext.provider_dispatched/rejected`; `_provider_failure_kind` |
| I6 owner isolation | MECHANISM EXISTS | `runs.get_owned`, `app_projects.get_owned`, `upload_sessions.owned`; `submit_child` injects `owner_id` server-side |
| I7 credential isolation | ✅ **CLOSED (Phase 07)** | `api_pool` scopes: `PHAM_VI_POOL`/`PHAM_VI_RIENG`, owner predicate in the query. [`ADR-002`](adr/ADR-002-credential-scope.md); `tests/test_404_pham_vi_khoa_api.py` |
| I8 durable DONE | PARTIAL | `Storage.promote` + `upload_sessions.promote` exist; no stage-level "validate before DONE" rule exists yet |
| I9 resume correctness | PATTERN EXISTS | `executor.tick` is idempotent and restart-safe; not yet applicable to a fixed pipeline |
| I10 cache correctness | **GAP** | `executor._cached_result` exists but keys on job_type+params, not an engine/model/prompt-version fingerprint (O13) |
| I11 resource control | MECHANISM EXISTS + MIGRATION HAZARD | `gpu_lease`/`gpu_env` good; 5 legacy `gpu_arbiter` sites — RISK-00-07 |
| I12 correct worker routing | **AT RISK** | app-scoped claim filter — RISK-00-01/02 |
| I13 cancellation | PARTIAL | `JobContext.is_cancelled()` (`job_runner.py:169`) is cooperative; "cancel cannot later become success" not proven |
| I14 safe artifact promotion | MECHANISM EXISTS | `upload_sessions.compensate/sweep/reconcile` |
| I15 legacy compatibility | NOT STARTED | no parity fixtures exist anywhere — GAP-00-C / RISK-00-08 |
| I16 safe errors/logs | PARTIAL | `app_projects._FORBIDDEN` blocks secret-named keys in project JSON; no equivalent rule for job `params`/`result` |
| I17 fixed product model | HOLDS TODAY | nothing built yet; the risk is inheriting it via `AgentRun` — RISK-00-03 |
| I18 checkpoint concurrency | PATTERN EXISTS | safe only because of `get_owned(..., lock=True)` at `executor.py:227` — copying the JSON shape without the lock loses updates → RISK-00-04 |
| I19 cache privacy | **GAP** | no owner scoping in the cache path; must be designed in, not retrofitted |

## Capability matrix summary

| Capability | Source | Target adapter/owner | Migration status | Parity evidence |
|---|---|---|---|---|
| upload / input | `platform_core/upload_sessions.py` | unchanged | KEEP | platform tests |
| media probe | `platform_core/media.py:probe` | unchanged | KEEP | platform tests |
| media normalize | `nerf_engine/stages/ffmpeg_edit.py` | Auto Scan service | EXTRACT (coupling-free) | **none — fixture needed** |
| audio prepare/separate | `nerf_engine/stages/audio.py` | Auto Scan service | EXTRACT | **none — fixture needed** |
| transcribe | `apps/autosubvideo/whisperx_runner.py` | shared service | WRAP ⭐ | in-platform tests exist |
| content/translate | `apps/ltt_llm` (`text.chat`) | adapter | WRAP | `tests/test_334` |
| voice synthesis | `apps/ltt_voice` (`ltt_voice.synthesize`) | adapter | WRAP | in-platform tests |
| timing/alignment | `Bot_PausePipeline/engine/{anchor_matcher,audio_splicer,insertion_planner,transcript_adjuster}.py` | Auto Scan service | EXTRACT (drop its `stt.py`) | **none — fixture needed** |
| compose | `DUNGVIDEO-FULL/engine/{assemble,sequential_timeline,matcher,segment}.py` | Auto Scan service | EXTRACT (leave `runner.py`) | **none — fixture needed** |
| render | `apps/upscalevideo` pattern + `nerf_engine/stages/ffmpeg_edit_cutonly.py` | Auto Scan service | WRAP + EXTRACT | upscalevideo is `released` |
| QC | — | Auto Scan service | **NEW CODE (GAP-00-B)** | n/a |
| delivery | `Storage.url_for` presigned | unchanged | KEEP | platform tests |

Full table with line-level evidence: [`CAPABILITY_MATRIX.md`](CAPABILITY_MATRIX.md).

## Phase history

| Phase | Gate | SHA/diff ref | Key evidence | Report |
|---|---|---|---|---|
| 00 Repo provenance & read-only audit | **PASS** | `c31b1ae`, docs-only diff under `docs/auto_scan_video/` | 9/9 MVP stages mapped (8 sourced + 1 explicit GAP); execution/money/resource traced end to end; 15 risks + 4 gaps opened | [`reports/00_REPORT.md`](reports/00_REPORT.md) |
| 13 Timing / pause / alignment | **PASS** | `c31b1ae` + `thoi_gian.py`, ADR-003, 23 tests | 🔴 **Product owner corrected the design**: people don't speak continuously, so a segment's budget runs **until the next segment starts** — the pause belongs to the sentence. Researched 3 community projects; borrowed SoniTranslate's partial-gap borrowing (70%) and Subdub's drift-debt repayment + 1.15× cap, **added a hard 3-segment cap none of them has**. Measured: Vietnamese 60% longer now needs **zero compression** where the Phase-02 design compressed every line 1.6×. Caught 2 real bugs in my own model. | [`reports/13_REPORT.md`](reports/13_REPORT.md) |
| 12 Voice provider integration | **PASS** | `c31b1ae` + `giong_noi.py`, `giai_doan_giong.py`, `apps/asv_voice`, 21 tests | **D5 re-checked: delegation fails here too** — one file per request keyed on `job_id`, and no grain to checkpoint. So VOICE calls 3 declared service fns, `giai_giong` (the only ownership check) inside the chain. **Per-segment resume proven twice**: clean re-run = 0 engine calls; delete one file = exactly 1 regeneration. Busy ≠ failed ≠ ambiguous. 4th executor on the `voice` lane. RISK-00-02 reproduced in my own suite. ⚠️ No real synthesis — voice quality and Vietnamese duration-vs-slot unmeasured. | [`reports/12_REPORT.md`](reports/12_REPORT.md) |
| 11 Content processing / LTT_LLM adapter | **PASS** | `c31b1ae` + `van_ban.py`, `dich_thuat.py`, 23 tests | **RISK-03-01 resolved** — `ltt_llm.chat` does accept external params. **Amended ADR-001 D5**: delegation cannot chunk/merge/detect-partial, so CONTENT calls `platform_core/llm/dieu_phoi` directly; what D5 protected (no 2nd HTTP path, no self-selected key, platform dispatch safety) is kept. Moved to the **api lane**, claims `llm_remote`. Ambiguous dispatch proven terminal **and** proven not to re-enter the queue. Transcript byte-identical after translation. ⚠️ No real model call made — quality/429/timeout unmeasured. | [`reports/11_REPORT.md`](reports/11_REPORT.md) |
| 10 Transcript engine extraction | **PASS** | `c31b1ae` + `ban_ghi.py`, `giai_doan_chep_loi.py`, 19 tests | **Wrapped** `autosubvideo.transcribe_file` (declared on both sides) instead of extracting the legacy engine, which selects its own GPU card. `autosubvideo` logic untouched ⇒ legacy caller still works. TRANSCRIBE proven to run as its own child job on the **GPU lane**. Canonical `TranscriptDocument` rejects overlapping segments, duplicate ids, drifted timestamps. Real faster-whisper smoke. Chain fixtures have no speech, so the engine is stubbed there — stated, not hidden. | [`reports/10_REPORT.md`](reports/10_REPORT.md) |
| 09 Audio prepare / separation / mix | **PASS** | `c31b1ae` + `tach_tieng.py`, `demucs_runner.py`, 16 tests | **First model runs.** Real demucs smoke: 3 s stereo → 4.3 s on CPU, all 4 stems. GPU env proven to reach the subprocess. Dropped the legacy `torchaudio.save` monkey-patch entirely (its `soundfile` dep isn't installed here) — stdlib WAV I/O instead. Customer's isolated voice never persisted. Caught 2 real bugs: loudness JSON slice, and a guessed test threshold. ⚠️ VRAM still unmeasured — torch is CPU-only; a test now **fails on a CUDA machine** to force the measurement. | [`reports/09_REPORT.md`](reports/09_REPORT.md) |
| 08 Media probe & normalize | **PASS** | `c31b1ae` + `nhap_media.py`, `giai_doan_media.py`, 24 tests, +29 .po | **First real engine.** One owned input → two verified artifacts (probe JSON + 16 kHz mono WAV), original preserved. Input policy enforced before any ffmpeg second; no-audio video fails terminally at `credit_actual == 0`. Unicode paths, VFR, stereo→mono, portrait, corrupt input all covered. Caught a guard that **could not fail** (`shell=True` is an `ast.keyword`). All 29 Auto Scan strings translated so `dich thieu ban EN` is red for exactly one non-Auto-Scan reason. | [`reports/08_REPORT.md`](reports/08_REPORT.md) |
| 07 Credential scope security | **PASS** | `c31b1ae` + `api_pool.py`, 2 test files | 🔓 **I7 CLOSED.** Explicit `PHAM_VI_POOL` / `PHAM_VI_RIENG`, owner predicate inside the query so the owner is known **before** selection; user-owned never falls back; fail-closed on incomplete scope. Safe because **no write path sets `owner_user_id`** — defining `""` = pool establishes semantics rather than reinterpreting them. **100 pre-existing key tests still pass.** Phase-04 RED target flipped green. | [`reports/07_REPORT.md`](reports/07_REPORT.md) |
| 06 Asset lifecycle, lineage & atomic promotion | **PASS** | `c31b1ae` + `assets.py`, `AsvAsset`, 1 migration | Stages now exchange **real asset refs**; DONE re-verified by checksum across all 9. 5-step protocol with all 4 crash windows tested — promoted/no-checkpoint recovers idempotently because keys derive from the fingerprint. 3 integrity states. Owner in the key **and** the column. Caught a real tz bug that would have passed in production and failed only under test. Gate `FAIL (4/26)` = baseline. | [`reports/06_REPORT.md`](reports/06_REPORT.md) |
| 05 App shell + dummy vertical slice | **PASS** | `c31b1ae` + 3 apps, 1 migration, 1 test file | 9 stages run end-to-end through the real queue. **0 credit held by any of 9 child jobs**; one hold on the run, settled once, remainder refunded. ffmpeg lane cannot claim GPU stages. Resume keeps `attempt`+fingerprint. Migration up→down→up clean. Gate `FAIL (4/26)` = baseline. | [`reports/05_REPORT.md`](reports/05_REPORT.md) |
| 04 Invariant & safety test harness | **PASS** | `c31b1ae` + 3 new test files | **23 passed / 1 strict-xfail**. Gate `FAIL (4/26)` — **identical to baseline, no regression**. M01–M24 green; M13 is the mandated RED target for I7 owned by Phase 07. Zero production files touched. | [`reports/04_REPORT.md`](reports/04_REPORT.md) |
| 03 Execution/billing/resource ADR freeze | **PASS** | `c31b1ae`, docs-only | ADR-001 accepted, D1–D10. Double-charging made structurally impossible; routing resolved with no core change; normalized stage rows beat the precedent's JSON checkpoint. Closed RISK-00-03/-04/-05. Every invariant I1–I14 + I18/I19 given an owner and a planned test. | [`reports/03_REPORT.md`](reports/03_REPORT.md) |
| 02 MVP product contract freeze | **PASS** | `c31b1ae`, docs-only | `auto_scan_mvp_v1` frozen. Product = Vietnamese dubbing. 8 decisions D-ASV-01…08, the load-bearing one being **copy the video stream** (moves RENDER off GPU). Input/output policy + 10 QC tolerances inherited from real code, with one legacy contradiction resolved (T8). Walked all 9 engine phases: none left holding a product decision. | [`reports/02_REPORT.md`](reports/02_REPORT.md) |
| 01 Baseline runtime & test truth | **PASS** | `c31b1ae` + worktree `phien/asv`, docs-only | Runtime measured (Py 3.13.12, ffmpeg 8.0.1, 2×RTX 5060 Ti, PG on 5432). **100 tests green** across queue/credit/gpu-lease/upload-lifecycle/run-aggregate. Deterministic fixture byte-identical ×3. Shared-tree gate self-invalidated ×3 → isolated via `cay_rieng.py` → **certified `FAIL (4/26)`**, all four attributed, two to one committed line. 5 baseline debts, none owned by Auto Scan. | [`reports/01_REPORT.md`](reports/01_REPORT.md) |

## External evidence pending

| Item | Why unavailable | What closes it | Blocks RC? |
|---|---|---|---|
| Trustworthy repo gate baseline | concurrent sessions mutated the tree mid-run; gate self-invalidated **3/3 times**, once caught red-handed (`tools/do_chon_cua_so_bieu_cam.py` +1 831 B mid-run) | quiet tree, or a dedicated git worktree, then full `python tools/gate.py` | blocks **Phase 01**, not RC |
| Multi-process invariants (I1/I18) | `test_214` ×7 + `test_73` skip without `LTT_TEST_DATABASE_URL` | a scratch PG database whose name contains `test`. **PostgreSQL is already running locally on 5432** — this is an operator decision, not missing infrastructure | yes (G2) |
| `ltt_llm` live budget check | `test_334::_health` skipped without `LTT_LLM_TOKEN` | operator-supplied token | no (source-level comparison still runs) |
| Real-runtime GPU/model/provider smoke | not required by Phase 00 | Phases 08–17 on a machine with the GPUs free | yes (G14) |
| Engine parity fixtures | none exist in any legacy tree | build one per extraction, before extracting | yes (G11) |

## Open risks

| ID | Sev | Risk | Mitigation/owner | Status |
|---|---|---|---|---|
| RISK-00-01 | P0 | worker routing is app-scoped, not job-scoped | ADR Phase 03 — hidden runtime executor apps | OPEN |
| RISK-00-02 | P0 | missing lane ⇒ job queued forever, silently | deploy assertion, Phase 03/22 | OPEN |
| RISK-00-03 | P0 | `AgentRun` reuse imports Canvas/approval | own the table, copy the pattern — Phase 03 | OPEN |
| RISK-00-04 | P0 | checkpoint JSON lost-update without the row lock | Phase 03/04 | OPEN |
| RISK-00-05 | P0 | settlement recomputes price, ignores measured usage | Auto-Scan settlement, Phase 03/04 | OPEN |
| RISK-00-06 | P1 | `ApiKey.owner_user_id` never read | additive scope, Phase 07 | OPEN |
| RISK-00-07 | P0 | extracted engines import legacy `gpu_arbiter` | replace with `ctx.gpu_env()`, static check — Phases 08–15 | OPEN |
| RISK-00-08 | P1 | no inherited engine tests | parity fixture before each extraction | OPEN |
| RISK-00-09 | P1 | Cloudflare 100 MB / 100 s shapes the product | presigned I/O, everything async | OPEN |
| RISK-00-10 | P1 | GPU shared with 3 other tenants | measure before declaring VRAM | OPEN |
| RISK-00-11 | P2 | `autosubvideo` under-declares `requires` | baseline debt, record only (O21) | OPEN |
| RISK-00-12 | P2 | live Google OAuth material in legacy trees | copy named modules only, never directories | OPEN |
| RISK-00-13 | P2 | pack/repo provenance mismatch | resolved by precedence | ACCEPTED |
| RISK-00-14 | P2 | QC policy has no source | new code, Phase 18 | OPEN |
| RISK-00-15 | P3 | vendored `cutclipshort` in-process executor | note in Phase 19 | OPEN |
| RISK-00-16 | P1 | concurrent sessions make gate results untrustworthy | **DEMONSTRATED** 3/3 runs. Dedicated git worktree, or peers pause | OPEN — blocking Phase 01 |
| RISK-01-01 | P2 | the repo's own gate mutates source files as fixtures; a crashed run leaves real edits a broad `git commit -a` will ship | proven by BASELINE-DEBT-01 (an i18n probe is committed at HEAD in `server/templates/vps_dieu_khoan.html`). Inspect `git diff` before every commit | OPEN |

Detail: [`RISK_REGISTER.md`](RISK_REGISTER.md).

## Deferred / out of scope
- social source scanning / downloading
- social publishing
- generic workflow / Canvas / node editor
- Make / n8n / browser automation

## Exact next action

**1 — Unblock Phase 01 (needs an operator decision).** The tree has live peer sessions and
the gate refuses to certify any run. Two ways out:

- **preferred:** run the remaining Auto Scan phases in a dedicated git worktree. This
  removes the failure mode for *every* remaining phase, not just one run.
- otherwise: wait for the peer sessions to land their work, then one clean
  `python tools/gate.py`.

Then record the certified result in `reports/01_REPORT.md` §4a and flip its gate to PASS.
**Do not fix the three baseline debts while doing this** (O21 / V1 finding A09) — they are
owned by the LTT VOICE work in flight.

**2 — Phase 02 needs the product owner, not just a clean tree.**
`prompts/02_MVP_PRODUCT_CONTRACT_FREEZE.md` must classify smart-cut / reframe /
scene-selection as REQUIRED or OPTIONAL. `MVP_PRODUCT_CONTRACT.md` defers that call to
Phase 02 *by design* ("Prompt 02 must classify them ... based on verified product intent"),
and it is not derivable from code. The engines exist and are substantial
(`nerf_engine/stages/{scene_detect,select,yolo_reframe,motion*}.py`, `cutclipshort/analysis`,
`cutclipshort/editorial`), so this is a real scope fork, not a formality.

**3 — Optional, closes a Critical gate early.** `LTT_TEST_DATABASE_URL` pointing at a
scratch PostgreSQL database (name must contain `test`) unlocks the 7 multi-process
invariant tests in `test_214` plus `test_73`. These are the only proof of I1/I18, which G2
marks Critical. PostgreSQL is already running on this machine (port 5432).
