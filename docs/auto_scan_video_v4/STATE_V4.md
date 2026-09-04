# AUTO SCAN VIDEO — STATE V4

> Handoff SSOT for the V4 MVP prompt pack.
> Pack: `G:\My Drive\AI\A LTT AII\Auto_Scan_Video_V4_MVP` — entry `start_here.md`.
> Read order: pack contracts -> repo `CLAUDE.md`/`AGENTS.md` -> V2 `docs/auto_scan_video/STATE.md`
> -> this file -> the current phase prompt.
>
> V2 history is **retained, not rewritten**. Everything under `docs/auto_scan_video/` stays.
> V4 supersedes by ADR, never by deletion (start_here §5).

- **source_branch**: `phien/asv`
- **source_sha**: `706faca50c75fb5b6dbad6c346b96c98a6736a11`
  ("wip(auto_scan_video): pha 21 dang do — DUNG theo yeu cau chu du an")
  ✅ **identical to the pack's observed SHA** — `origin/phien/asv` and the local ref both
  resolve to `706faca`, so there is **no delta to audit** (start_here §1).
- **v4_branch**: `phien/asv-v4` (created from `706faca`)
- **worktree**: `D:\LTTSTUDIOSAPP\.claude\worktrees\auto-scan-video-v4-mvp-7173d9`
  - ⚠️ The pack *suggested* `D:\LTTSTUDIOSAPP-asv-v4`. This session was launched by the
    harness inside an already-isolated worktree whose contract is "run everything here, never
    `cd` to the repo root". Creating a second tree would have left a stray checkout on the
    user's disk and split the work across two directories. The **binding** requirement —
    a dedicated worktree that is not `master`, not the existing `phien/asv` tree
    (`D:\LTTSTUDIOSAPP-asv`), and not the production tree — is satisfied. Recorded here
    rather than silently diverging.
  - ⛔ **This machine IS production** (`C:\LTTPlatform` exists). Never deploy from here.
- **current_phase**: 28
- **phase_status**: Phase 28 `BLOCKED_EXTERNAL` — **stop**. No P0/P1 blockers
  remain and 18 of 20 gates are green, but **G9** and **G17** need evidence this
  machine cannot produce, so **G20 is not satisfied**.
  ⛔ Not `READY_FOR_PRODUCTION_PILOT`. ⛔ And deliberately **not**
  `FAIL_REMEDIATE`: that verdict exists to send a DEFECT back, and there is no
  defect — returning to Phase 26 would spend a cycle on missing credentials.
- **rc_sha (code)**: `747ca288eb1cdb9eeaf0b47e325e450108d54f71` — frozen. Every
  later commit on this branch touches `docs/` and `evidence/` only, so the code
  artifact is unchanged by them.
- **rc_sha (docs head)**: `50e8083` — Phase 28 report + STATE.
- **gate at RC**: `python tools/gate.py --phien asv-v4` → **`RESULT: PASS`**, run
  twice: once at `747ca28` and again at `50e8083`.
  ⚠️ Four frontend steps report **BOQUA**, and the gate's own RESULT line says
  what that means: *"4 BUOC TU BO QUA, KHONG PHAI BANG CHUNG."*
- **evidence regenerated at the RC**: `evidence/22_nghiem_thu.json` and
  `evidence/24_hieu_nang.json`. 🔑 This was not a formality — the Phase 27
  runs predated `9ff469e`, which changes `cache_dung_duoc`, code that executes in
  every stage of every E2E run. Evidence recorded before that commit does not
  describe this RC.
- **last_green_invariant_command**: declared in `tests/bo_bat_bien_v4.py`, two rounds —
  `VONG_NHANH` (9 files, **~12.5 s**, run after every edit) and
  `VONG_DU` (+ `test_417`, **~78 s**, run before closing a phase).
  ⚠️ `test_417` alone is 84 % of the full time. It is **split, not dropped**: it proves
  downstream invalidation, and an 80-second suite gets run once a day instead of after
  every edit — which is how a defect ends up ten edits deep.
- **last_green_invariant_result**: `VONG_DU` + `test_452` + `test_453` →
  **188 passed, 1 xfailed in 53.95 s** (2026-09-04, after Phase 27)
  - The one remaining `xfail(strict)` is `test_425::test_chuoi_thi_hanh_biet_den_preset`,
    a **Phase 12** debt (`pipeline.py` never names the preset). Not a Phase 26 blocker.
  - ⭐ Two other strict-xfail pins **flipped to XPASS on real runs and were removed**:
    B22-01's (`test_448`) and B24-01's (`test_450`). Phase 22 wrote the first one
    predicting exactly that — so the suite would announce the defect's end instead of
    leaving a TODO lying around for another year. It did.
- **certified_baseline**: `python tools/gate.py --phien asv-v4` -> `RESULT: FAIL (1/26)`, 675 s,
  **2 failed / 5 769 passed / 32 skipped**, no tree-changed warning.
  Both failures proven non-ASV: `test_82` (gitignored `apps/*/vendor/`, every fresh worktree)
  and `test_361` (passes alone; red only because the gate held the quiet-window lock it asserts on).
  Raw log: `evidence/00_gate_baseline.txt`
- **gate_after_phase_27**: `python tools/gate.py --phien asv-v4` -> **`RESULT: PASS`**,
  ~11 min (2026-09-04). ⭐ Strictly better than the certified baseline: the two
  environmental failures above no longer reproduce, and every step is green.
  ⚠️ Four frontend steps report **BOQUA** — the gate says so itself, in that line:
  *"4 BUOC TU BO QUA, KHONG PHAI BANG CHUNG"*. They are not evidence of anything.
  - The gate caught two things Phase 27 would otherwise have shipped: the two new
    UI strings had no English entry (the translation ratchet), and
    `ho_so_he_thong.txt` had gone stale after 16 app files changed. ⛔ The strings
    were added **by hand** to the `.po`; running `i18n.py trich` would have let
    msgmerge guess translations and reorder the whole file.
- **critical_external_evidence_pending**: see table below
- **open_blockers**: **none.** All nine Phase 26 findings are closed or recorded
  with a written reason (`reports/27_REPORT.md`). Eight FIXED with evidence;
  A26-04 (P3) NOT_FIXED by design, with the condition that would change it
  written at the constant itself.
  - ⭐ Three `xfail(strict=True)` pins flipped and were removed: B22-01
    (`test_448`, real E2E run), B24-01 (`test_450`, real perf run) and B23-01
    (`test_449`) — the last one after **refusing** a fix that was only half of
    one. See "what Phase 27 got wrong about itself" below.
- **open_blockers (MOI, tim ra SAU pha 28)**:
  * **A29-01 (P1) — the dubbing stage could never succeed on the real path.**
    First run ever with `LTT_ASV_GIONG_THAT=1`: `voice_synthesis` ->
    `failed_terminal`, *"Chi chon mot: giong cua ban hoac giong co san."*
    `giai_doan_giong.py` passed **two** wrong arguments at once:
    `preset=cai_dat["preset"]` — that is the **render** preset
    (`localize_preserve_picture`), while `ltt_voice.preset` means the name of a
    **built-in voice** (`giong_mau.hop_le("localize_preserve_picture") = False`);
    and `voice_id=ma_giong` — but `"Minh Duc"` **is** a built-in
    (`hop_le("Minh Duc") = True`), so it belongs in `preset`. Both set at once
    trips `chuan_hoa`'s correct guard.
    ⭐ Same shape as every other finding in this programme: `giai_giong` was
    tested in isolation (test_409/test_435, with the right arguments) and the
    E2E always substituted it, so the live path had **never run**.
    **FIXED** — the rule now lives once, at the boundary
    (`giong_noi.tach_ma_giong`), and the stage stops passing a render preset.
    Measured after: `preset='Minh Duc'`, `lech_lon_nhat` 10.3 -> **0.83**, both
    runs `done`, **20 passed** with the real LTTStudioVoice.
  * **A29-02 (P2, fixture) — the translation double inflated short fragments.**
    ASR splits the source into **6** segments including "Thank you." and
    "Of course."; `_dich_gia` matched by shared words and returned a **whole**
    Vietnamese sentence for each, so a ~0.6 s slot received ~6 s of real speech
    and `timing_align` refused with "he so co gian 11.304". ⭐ SAPI had hidden
    this for 29 phases: it reads accent-stripped text so fast that a
    wrongly-proportioned translation still produced a plausible **duration** —
    a double can be right about **content** and wrong about **length**, and
    length is what the fit ladder measures. **FIXED**: the double now truncates
    in proportion to the source fragment.
  * **A29-03 (P2) — the real-model E2E is blocked by TWO things, and my first
    diagnosis named only one.** 🔴 I wrote "blocked by SQLite, and by
    nothing else" before asking machine B how it was doing. The project owner
    suggested the model might simply be busy with another session's job, and
    the measurement agreed with **them**, not me — machine B's RTX 3090 read
    `utilization 99%`, `vram_free 2,276 / 24,576 MB`, `power 367.3 / 370 W`,
    17 processes. Only 2.2 GB free is **not enough to load `qwen38-vision` at
    all**, so llama-swap must evict, queue or refuse — which is a far better
    explanation of four `tu_choi` than anything I had proposed.
    🔴 Lesson, and it is the same one this programme keeps teaching: I
    reached for the failure I could see in my own logs and stopped, instead of
    asking the other machine a question I had the access to ask.
    Measured end to end today:
      - pool key resolves and works: `GET /v1/models -> 200`, both
        `qwen38-api` and `qwen38-vision` served from `http://192.168.2.66:8299`;
      - one real `DOC_CANH` call returns **valid, schema-correct** JSON from
        `Qwen3.8-27B-UD-Q4_K_M.gguf`, correctly describing the frames
        (`loai: test_pattern_ky_thuat`, `de_xuat: khong_chac`, `do_tin: 0.2`);
      - the prompt is **8,559** estimated tokens against the measured 28,262
        vision window - **not** a context problem (V4-R08 was the first suspect
        and it was wrong).
    🔴 What actually fails: `content_process` dies with
    `sqlite3.OperationalError: database is locked`, and the four `doc_canh`
    calls are recorded `tu_choi` in its wake. Real network latency to machine B
    widens exactly the two-session window `giai_doan_noi_dung` already
    documents (`su_dung.ghi` + `danh_dau_xong` hold the handler's write lock
    while `ctx.progress` opens a second session).
    ⭐ So "real model" and "throwaway SQLite" are the same
    collision seen from a second angle. The clean route is to run this suite on
    **PostgreSQL behind `tests/pg_scratch.py`** - whose guard already refuses
    any URL whose database name does not contain `test`. Not attempted yet.
  * **A29-04 (P1, mine, introduced in Phase 27) — a write transaction was
    held across a network call.** `_doc_cac_canh` called `sd.mo_don_vi`
    (a write) and only committed *after* `_rut_khung` (ffmpeg) and
    `ai.goi_tinh_tien` (network to machine B). With the substitute model that
    is milliseconds; with the real one it is seconds, and `ctx.progress` on a
    second session cannot get in. **FIXED**: commit before the slow work.
    ⭐ `giai_doan_noi_dung` had written this exact lesson down in
    prose. It did not reach `_doc_cac_canh` because I wrote that function
    after reading it.
  * **A29-05 (P2) — and the real-model E2E still needs PostgreSQL.** After
    A29-04 the refusals went 4 -> 3, which confirms the mechanism and shows it
    is not the only writer: `ctx.provider_dispatched` durably records the
    dispatch on **its own session** immediately before the outbound HTTP, by
    design (I5). Several sessions + SQLite's single-writer lock + multi-second
    network holds is not a defect to patch away; it is what SQLite is.
    🔴 And the reason this took four rounds to establish is worth
    recording: **three hypotheses were wrong, and all three were checkable.**
    Context overflow (8,559 of 28,262 tokens - no), machine B saturated
    (still refused at 0% / 23.8 GB free - no), "SQLite in general" (a single
    paid call on SQLite succeeded - no). The answer was in the ledger the
    whole time: `AsvUsage.ghi_chu["ly_do"]` recorded
    `database is locked [SQL: UPDATE jobs SET` on every one - and the report
    printed only the **count**. It now records the reason.
  * **A29-06 (P1, PRODUCTION-FATAL) — the first paying run would die at the
    credit hold, and 29 phases never saw it.**
        AsvRun.id          = "asvr_" + 32 hex = **37** characters
        CreditEntry.job_id = VARCHAR(**36**)
    `features.py:140` passes `run.id` into `credit.giu_cho(...)`. Over by
    exactly one character.
    🔴 Production runs **PostgreSQL**, which enforces column width;
    every ASV test has run on **SQLite**, which does not. And ASV has never
    run in production (`enabled=False`), so nothing else could have caught it.
    The very first paying customer run would fail at the credit hold -
    **before any work happens** - with a raw database error.
    ⭐ This is the entire payoff of moving the acceptance suite onto
    PostgreSQL: it was found in the first run, in seven seconds.
    ⛔ NOT fixed here. Two candidate fixes and both are decisions: widen
    `CreditEntry.job_id` (platform schema + a migration on the production
    database), or shorten `AsvRun.id` (app-only, and safe **today** because
    ASV has no production rows - but it changes an id scheme chosen on
    purpose, `asvr_` prefixes exist so a wrong id cannot be passed silently).
  * **A29-07 (P1) — FIXED, and the fix disproved half my explanation.**
    Phase 22 had already installed the right mechanism - `BIEN_CHO_CODEC_DB`,
    a margin so the PCM master sits below the delivery ceiling and AAC's
    inter-sample overshoot still lands under it. It was set to **1.0 dB**,
    measured on a run where `so_cat: 0` - i.e. **on one preset only**, because
    the cutting preset could not yet cut. Raised to **2.0**.
    🔴 I explained the cut preset's larger overshoot as a denser signal.
    The confirming run says otherwise: at a -3.5 master ceiling the cut
    overshoot fell from **1.71 to 0.20 dB** - same code, same preset. So
    overshoot tracks **how hard the limiter is working**, not signal density.
    ⛔ Recorded loudly because my earlier projection said "0.29 dB of margin
    left"; the truth is ~1.8 dB, and anyone trusting the projection would
    conclude the margin is too tight and lower it - which makes the limiter
    work harder and the overshoot grow again.
  * **A29-07 original measurement (superseded):** the smart preset's delivered
    file breached its own true-peak ceiling. First fully-real end-to-end run (no doors
    substituted at all):
        preserve      T4 -14.41 LUFS ok | T5 **-2.30** dBTP ok
        smart_localize T4 -14.34 LUFS ok | T5 **-0.78** dBTP **FAIL** (max -1.5)
    Same audio master; the cut preset re-encodes, and the delivered peak is
    **1.5 dB above** the ceiling the pipeline aimed at.
    ⭐ This is the answer to **A26-04**. That finding said QC shares
    its constants with the producer, so it can only catch an *implementation*
    error and never a wrong target. Here the pipeline did **not** do what it
    was told - and QC caught it, on the first real run, exactly as designed.
    ⛔ NOT fixed: leaving headroom vs limiting after the final encode is an
    audio-chain decision, and Phase 24 already measured this chain aiming at
    -1.5 and delivering -1.45 - so the margin was known to be thin.
  * **A29-06 fix CHANGED after review by the coordinating session.** I first
    widened `credit_entries.job_id` and `jobs.plan_id` to 64 with a migration;
    it worked (the full 71-migration chain ran clean on PostgreSQL). The
    coordinator argued the cheaper direction and was right: widening edits
    **shared platform columns** and needs a migration on the production
    **money** table, while shortening the id touches **one file of this app**
    and needs no migration.
    ⭐ I measured the thing they could not see from outside: **nothing
    parses `run.id`** - every use is `[:8]` for a log line or a filename. So
    shortening is free in fact, not just in theory. `"asvr_" + 31 hex` = 36
    chars, 124 bits; precedent in this same app (`assets.py` uses 19 hex).
    🔴 And the decisive reason: the coordinator is queueing a check that
    will **enforce** `job_id <= 36` as a platform contract. Widening to 64
    would have put my patch in direct contradiction with a contract about to
    be enforced - two people fixing one thing in opposite directions is worse
    than neither fixing it.
    ⚠️ The window is open only because ASV has **no production rows**; it shuts
    permanently at the first paying run.
  * **A29-06 was TWO columns, not one.** `jobs.plan_id` is also VARCHAR(36)
    and also receives `run.id` (`jobs.py:237`). It stayed hidden **behind**
    the credit one: the run never reached it. 🔴 A fix without a re-run
    is a fix that does not know whether it was enough.
- **findings_for_phase_28**:
  * **A27-01 (P2)** — `apps/auto_scan_video/qc_ai.py` (semantic + visual QC) and
    `sua_chua.py` (repair) have **no caller in product code**. `loi.py` imports
    only their exception classes, which makes both files look live from every
    angle except the one that matters. This is the **sixth and seventh** instance
    of the habit Phase 26 counted five times, and it was found by the check that
    audit asked Phase 27 to build (`tests/test_453`). G14 was marked PARTIAL for
    *"repair plan computed but never driven"* — that was half of it.
    ⛔ Wiring them is feature expansion, which Phase 27 forbids. Held by the
    ratchet with a written reason. **Owner: Phase 28 to schedule.**
  * **A27-02 (P3)** — `tests/fixtures/asv_e2e.vung_co_tieng` estimated the noise
    floor with the **median**, on a premise stated in its own docstring: *"a dub
    speaks about a third of the duration, so the median falls on the bed."* That
    premise depends on how much silence the **source** contains — something the
    measurement does not control. The first time `smart_localize` really cut, the
    premise broke and the report said "no speech in the output" about a file with
    the same speech structure as the other preset. Fixed to the 20th percentile.
    Recorded because the **class** — a measurement whose premise depends on its
    input — is not limited to this function.
- **what_phase_27_got_wrong_about_itself**: B23-01 was written up as FIXED before
  the `xfail(strict)` guarding it had been run. The pin then failed, and its own
  stated reason named the layer that had been skipped: the storage key carries
  each **artifact's** fingerprint, not the stage's, so no string match on
  `storage_key` can answer the question at all. The real fix reads
  `AsvStage.fingerprint`. ⭐ Recorded here rather than quietly corrected: the
  failure mode was trusting a patch that matched my model of the defect over the
  check written specifically to test that model.

## Runtime measured on this machine (2026-09-03)

| Item | Value | Why it matters to V4 |
|---|---|---|
| OS / shell | Windows 10 Pro 19045, PowerShell 5.1 + Git Bash | `.ps1` must stay ASCII, config writes BOM-free |
| Python (dev/test) | 3.13.12 | the interpreter the gate and pytest run under |
| **torch (dev/test)** | **2.11.0+cpu — `cuda.is_available() == False`** | 🔴 every test here measures a **CPU** device |
| **torch (production)** | `C:\LTTPlatform\venv` — **2.11.0+cu128, cuda True, 2 devices** | 🔴 production and test disagree about the device |
| ffmpeg | 8.0.1-full (gyan.dev) | render/compose/probe |
| GPUs | 2 × RTX 5060 Ti, 16 311 MiB each (977 / 802 MiB in use) | both cards visible; the older "Code 43" fault is gone |
| `LTT_WORKER_POOLS` | unset in this shell | lane routing is production-side config |
| Production install | `C:\LTTPlatform` present, plus `vieneu-venv` and `whisperx-venv` | Voice and ASR run in **their own** interpreters |

## Current ASV runtime — traced, not summarised

`run -> advance -> stage -> job -> artifact -> settlement`, all in
`apps/auto_scan_video/`:

1. **create** — `features.tao_run` writes one `AsvRun` + nine `AsvStage` rows, takes **one**
   credit hold on `run.id`, then submits the coordinator job.
2. **advance** — `jobs.handle` -> `jobs._advance`. Locks the run row **first**
   (`features.lay_run(..., lock=True)`), returns immediately if the run is terminal — this is
   the half of I13 that stops a late child from reviving a cancelled run.
3. **reconcile** — `_thu_ket_qua_job_con` maps child `Job` states onto stages. 🔑 It refuses to
   infer `job.status == done` ⇒ `stage succeeded`; a handler that died after the engine
   returned but before `promote` is marked failed-and-retryable, not done.
4. **invalidate** — `_vo_hieu_giai_doan_da_lech` re-checks fingerprints at the top of every
   tick and resets drifted stages **plus their downstream closure**
   (`pipeline.ha_nguon_cua`).
5. **submit** — `_nop_giai_doan_san_sang` submits one child `Job` per ready stage with
   `plan_id = run.id`, `step_id = stage`, price **0**, and snapshots the admission resource.
6. **execute** — `thi_hanh.chay_theo_job_type` -> `chay_giai_doan`, five-step asset protocol
   (engine -> validate -> `storage.promote` -> persist refs+fingerprint -> commit), keys
   `asv/{owner}/{run}/{stage}/{fingerprint}` so re-writes are idempotent.
7. **settle** — `features.quyet_toan`, once, idempotent, `actual = min(Σ asv_stage.credit_actual,
   credit_held)`; the remainder is refunded. `kiem_tran_chi` is the mandatory pre-spend check.
   🔑 Measured, never recomputed from a price table (ADR-001 D4).

### The nine stages and their lanes (`pipeline.CHUOI`)

| # | Stage | Executor app | Lane (`requires`) | Admission resource |
|---:|---|---|---|---|
| 1 | `media_prepare` | `asv_media` | `ffmpeg` | — |
| 2 | `audio_prepare` | `asv_gpu` | `gpu` | `tach_nguon_cuc_bo` ×1 |
| 3 | `transcribe` | `asv_gpu` | `gpu` | `tach_nguon_cuc_bo` ×1 **(same name on purpose)** |
| 4 | `content_process` | `auto_scan_video` | `api` | `llm_remote` ×1 |
| 5 | `voice_synthesis` | `asv_voice` | `voice` | — |
| 6 | `timing_align` | `asv_media` | `ffmpeg` | — |
| 7 | `compose` | `asv_media` | `ffmpeg` | — |
| 8 | `render` | `asv_media` | `ffmpeg` | — |
| 9 | `qc` | `asv_media` | `ffmpeg` | — |

Four apps, one product: one customer-facing (`auto_scan_video`) and three hidden runtime
executors (`asv_media`, `asv_gpu`, `asv_voice`, all `catalog_parent="auto_scan_video"`).
The split exists because `platform_core/jobs.py` filters claim eligibility by **app**, not by
`job_type` — an app declaring all four capabilities is invisible to every split-lane worker
and its jobs sit `queued` forever with no error.

Declared VRAM (`asv_gpu/manifest.py`): `audio_prepare` 4 000 MB **(never measured)**,
`transcribe` 6 000 MB (borrowed from `autosubvideo.transcribe`, measured there).

## V4 target shape vs. what exists today

`V4_PIPELINE_DAG.md` needs **19** pipeline nodes. Nine exist. The V4 gap is not "polish the
nine" — it is that the whole *understanding and planning* half of the product
(`SCENE_ANALYZE`, `VISUAL_UNDERSTAND`, `CONTENT_PROFILE`, `EDIT_PLAN`, `VOICE_BIND`,
`DUBBING_FIT`, and the three AI QC lanes) has no code at all, and that `content_process`
currently does translation **before** any edit or voice decision exists — the exact ordering
V4 forbids (`V3_TO_V4_CORRECTIONS` §2/§3).

| V4 node | Today | V4 phase |
|---|---|---|
| `TECHNICAL_PREPARE` | ✅ `media_prepare` | 05 |
| `AUDIO_PREPARE` | ✅ `audio_prepare` (demucs) | 13 |
| `TRANSCRIBE` | ✅ `transcribe` (wraps autosubvideo) | 07 |
| `DIARIZE?` | ❌ absent | 07 |
| `SCENE_ANALYZE` | ❌ absent | 10 |
| `VISUAL_UNDERSTAND` | ❌ absent | 11 |
| `CONTENT_PROFILE` | ❌ absent | 11 |
| `EDIT_PLAN` | ❌ absent | 12 |
| `VOICE_BIND` | ❌ absent (voice is a raw setting) | 09 |
| `DUB_SCRIPT_ADAPT` | ⚠️ `content_process` — runs **before** edit/voice decisions | 14 |
| `VOICE_SYNTHESIS` | ✅ per-segment, resumable | 15 |
| `DUBBING_FIT` | ❌ absent | 15 |
| `TIMING + AUDIO_MASTER` | ✅ `timing_align` (ADR-003) | 16 |
| `COMPOSE_PLAN` | ✅ `compose` (manifest is data) | 17 |
| `RENDER` | ✅ `render` — **stream-copy only**, no smart-cut path | 17 |
| `TECH_QC` | ✅ `qc` (T1–T10) | 18 |
| `SPEECH/SEMANTIC/VISUAL_QC` | ❌ absent | 19 |
| `REPAIR_PLAN` | ⚠️ stage-level retry only, no segment targeting | 19 |

## V4 critical risks — read from code at `706faca`, not from old prompts

| ID | Sev | Gate | Finding (with evidence) | Owner phase |
|---|---|---|---|---|
| ~~V4-R01~~ | **CLOSED (Phase 05)** | G6 | `routes.py:155` does `du_lieu = await video.read()` and `routes.py:79` caps at `TRAN_TAI_LEN = 90 MB`. `features.tao_run_tu_tai_len` then holds that `bytes` object while it *also* writes a temp copy and *also* streams it to storage — the whole video is resident **twice**. The durable path already exists and already has a real caller (`platform_core.upload_sessions.create/upload_target/promote`, used by `apps/autosubvideo/services/source_drafts.py`), so this is a **reuse**, not a build. | 05 / 21 |
| ~~V4-R02~~ | **WITHDRAWN (Phase 02)** | G3 / G11 | 🔴 **I recorded this wrong in Phase 00.** I read the import list in `giong_noi.py`, matched it against `V4_CAPABILITY_FIRST`'s forbidden list ("TTS sidecar client", "copied LTT Voice text-normalization constants") and called it a P0 reach-through. It is not. `apps/ltt_voice/__init__.py` declares `BE_MAT_CONG_KHAI` and **every one of those six names is in it**, each with a written reason; `tools/lint_app_contract.py::APP_DUOC_DUNG_APP` enforces the other side, and that linter runs in the gate. Tracing the real caller shows ASV honours the surface exactly: `sidecar_client` only for `san_sang()`, `text_pipeline.chuan_hoa` and **not** `features.chuan_bi_van_ban`, ownership always through `giai_giong`. This is priority #2 of `V4_ARCHITECTURE_CONTRACT` already implemented. Had it stood, Phase 09 would have rebuilt a boundary that exists. | — |
| ~~V4-R03~~ | **WITHDRAWN (Phase 02)** | G3 | Same error, same cause. `apps/ltt_llm/__init__.py::BE_MAT_CONG_KHAI = {("apps.ltt_llm", "ngan_sach")}` — declared on purpose, because the token budget must have exactly one source: CLAUDE.md records a real production bug where a duplicated budget silently truncated every long answer at 1 024 tokens. | — |
| ~~V4-R13~~ | **CLOSED (Phase 07)** — two additive lines on both sides, plus `gpu_uuid` on `diarize_file`. The extension found a real GPU-arbitration defect in the owner app that had nothing to do with ASV. | G3 | **Diarization is not exported.** `autosubvideo/ai_workflows.py` has `diarize_file` + `assign_speakers` and the manifest declares `autosubvideo.diarize` (VRAM 2 000), but neither name is in `autosubvideo.BE_MAT_CONG_KHAI` — only `transcribe_file` is. EXTEND_OWNER_CONTRACT: two additive lines on both sides. | 07 |
| ~~V4-R14~~ | **CLOSED (Phase 09)** — seven additive read-only names; AUTO_MATCH now has a catalog to match against, and defers rather than defaulting when it has no evidence. | G11 | **`AUTO_MATCH` has nothing to match against yet.** `apps/ltt_voice/giong_mau.py` already carries exactly the right data — `NHAN_GIOI` (nam/nữ), `NHAN_VUNG` (bắc/trung/nam), `NHAN_PHONG_CACH`, `DANH_SACH` and a `loc(gioi=, vung=, phong_cach=)` filter — but none of it is exported. Without the extension, Phase 09 can only ship `AUTO_MATCH` as "the default voice", which `ADR-V4-001` D-V4-04 explicitly forbids. EXTEND_OWNER_CONTRACT, read-only. | 09 |
| ~~V4-R04~~ | **PARTIALLY CLOSED (Phase 06)** — the guard was added in Phase 04; Phase 06 added the missing half: even when the guard is lifted (`LTT_TEST_NANG=1`), `demucs_runner` no longer takes the whole machine (4 threads, was unlimited → measured 462–984 % CPU per process). | G7 | `tests/test_406::test_tach_nguon_ra_du_BON_stem` runs **real demucs** with **no marker, no env guard, no skip**. There is no `pytest.ini`/`pyproject` pytest config in the repo at all, so no `heavy` marker exists to hang isolation on, and `tools/test_nhanh.py::TEP_NOI_TIEP` serialises only three files — none of them this one. It runs during a gate run on a box **that is serving production**. ⚠️ **Corrected in the Phase 05 review:** I first wrote that the gate uses `-n auto` = 20 workers. It does not — `gate.py:490` passes `ngan_sach_loi() = cpu_count() - 6` = **14**, and `test_394:324` pins that `-n auto` cannot return. I had read a comment describing the *old* mechanism as current state; session `lttstudiosapp-73` caught it. The gating decision stands, for a smaller reason: a real ML model still loads weights and takes the machine's spare CPU mid-measurement. | 04 |
| V4-R05 | **P0** | G7 / G8 | **Test and production disagree about the device.** Dev/test torch is `2.11.0+cpu`; `C:\LTTPlatform\venv` is `2.11.0+cu128` with 2 CUDA devices. Every demucs/ASR measurement taken in this tree is a **CPU** measurement that says nothing about production, and `test_406:378` carries a guard that deliberately fails on a CUDA machine to force the VRAM measurement — it will fire the moment anyone runs the suite with the production interpreter. `asv_gpu` declares 4 000 MB for `audio_prepare` marked *CHUA DO* ("not measured"). | 04 / 13 / 24 |
| ~~V4-R06~~ | **CLOSED (Phase 05)** — and it was worse than recorded: two further sites existed, one with no cap at all | G18 | Three full-file `Path(...).read_bytes()` calls on **media** purely to checksum: `giai_doan_media.py:94`, `giai_doan_am_thanh.py:87`, `giai_doan_chep_loi.py:124`. `V4_RESOURCE_CPU_GPU_POLICY` calls this out by name — stream the hash. At the current 90 MB cap it is survivable; the moment V4-R01 is fixed and real videos arrive it is not. | 05 / 13 |
| ~~V4-R07~~ | **CLOSED (Phase 12)** — `EDIT_PLAN` inserted before `CONTENT_PROCESS`, which now declares `sau=(EDIT_PLAN,)`; every paid stage is downstream of the visual decision, and `doan_giu_lai` keeps cut segments out of the dubbing work list. | G10 | Expensive-work ordering is **inverted** relative to V4. `pipeline.CHUOI` runs `content_process` (paid LLM translation of the whole transcript) at position 4, with no `EDIT_PLAN` and no `VOICE_BIND` anywhere. V4 requires the cut list frozen *before* translation and the voice bound *before* final adaptation. This is a chain re-ordering, not a new stage bolted on. | 12 / 14 |
| V4-R08 | **P1 — partially addressed (Phase 08)**: `ai.cua_so_ngu_canh` now reads the real per-model window (text 131 072 vs vision 65 536) instead of assuming one ceiling. ⚠️ Still open: the registry's declared window is higher than the 28 262 measured in `docs/audit_ltt_llm/STATE.md`; Phase 11 must re-measure before packing frames. | G9 | `ltt_llm_vision` exists and is public (`apps/ltt_llm/features.py:40` -> `qwen38-vision`), so scene understanding is a **reuse**. But its real context ceiling is far below the text alias — `docs/audit_ltt_llm/STATE.md` records `ltt_llm` 88 555 vs `ltt_llm_vision` **28 262** tokens after F-02 was closed. Frame batches must be sized against 28 K, not against the text model, or Phase 11 discovers it as a 413 at runtime. | 11 |
| V4-R09 | P1 | G13 | `platform_core.media.detect_gpu_encoder()` exists and is careful (NVENC minimum-size trap already handled at `media.py:174`). ASV never calls it, because MVP v1 froze *stream-copy only* (D-ASV-03) — correct then, insufficient for `smart_localize`, which must re-encode at cut points. | 17 |
| V4-R10 | P2 | G1 | Three baseline gate failures (`test_362` ×2, `test_82`) **can never pass inside a linked worktree** (V2's RISK-14-02) and this repo's own tooling creates linked worktrees. Do not spend time on them; count them as environmental. | — |
| V4-R12 | P2 | G16 | `MVP_CONTRACT.md` §6 freezes **four** user settings; `routes.py:134-135` exposes **two** (`che_do`, `giong_id`). `keep_background` and `background_gain_db` were contracted and never surfaced. Found in Phase 01, owned by Phase 21. | 21 |
| V4-R15 | P2 | G8 | **`gpu_lease` reserves by VRAM, and the scarce resource here is not VRAM.** Measured 2026-09-04 on this host: one 1080p `h264_nvenc` session takes **+228 MiB** but puts the **encoder engine at 88 %**. With a 500 MiB declaration a 16 GiB card admits dozens of leases, so two smart-preset renders can contend on one engine while the scheduler believes both fit. ⛔ No second slot-counter was added inside the app: that creates a second owner for one resource, exactly what `pipeline.CHUOI` refused to do for demucs. Found in Phase 27. | 28 |
| V4-R11 | P2 | G4 | `enabled=False` does **not** close a route — `mount_all` mounts every error-free router. V2 fixed this with an explicit flag gate placed **before** `require_login` (after it, a closed route still 303s to `/login` and thereby admits it exists). Any V4 route added must keep that ordering. | 21 |

## External evidence pending

| Item | Why unavailable | What closes it | Blocks |
|---|---|---|---|
| Real GPU demucs/ASR resource ledger | dev interpreter is `torch+cpu` | run the profile under `C:\LTTPlatform\venv` (read-only), or install cu128 into the test env | G7, G8, G18, G24 |
| Multi-process invariants (I1/I18) | `test_214`×7 + `test_73` skip without `LTT_TEST_DATABASE_URL` | a scratch PostgreSQL DB whose name contains `test`; PG is already live on 5432 | G4 |
| Live `ltt_llm` / `ltt_llm_vision` call | keys live in `C:\LTTPlatform\secrets`, ACL-locked (`Test-Path` -> *Access denied*); Phase 22 substituted only `dieu_phoi.goi`, so prompt assembly, budget gate, ledger and schema validation all ran for real | operator-supplied token | G9, G17 |
| Real LTT Voice synthesis quality | :8120 answers `401` without `LTT_VOICE_SIDECAR_TOKEN`, same locked directory. Phase 22 substituted it with **real** SAPI speech, which closes placement/duration/level/mixing but says nothing about Vietnamese voice quality | a real run against `LTTStudioVoice` on :8120 | G11, G12, G17 |
| Representative real customer videos | Phase 22 built `tests/fixtures/asv_e2e` — real SAPI speech, two speakers, four scenes, a continuous bed and one dialogue-free scene — and ran **both presets end to end**; it is representative in structure but still synthetic | operator-supplied fixtures, both presets | G17 |
| `transcribe` on CUDA | 🔴 **Phase 22's entry was wrong and is corrected here.** Measured in Phase 24 in three separated steps: the CUDA path does **not** hang — `large-v3` loads in 8.93 s and inference then fails in **0.23 s** with `RuntimeError: Library cublas64_12.dll is not found or cannot be loaded` (`ctranslate2` ships `cudnn64_9.dll`, not CUDA 12 cuBLAS). ⚠️ Production is unaffected: `install.ps1` sets `LTT_WHISPERX_PYTHON` and `C:\LTTPlatform\whisperx-venv` exists, so ASR runs in the sidecar there; the broken path is the in-process fallback, used only where that variable is unset. 🔴 Still open in the owner app: `_get_faster_model` wraps only the *constructor* in its CPU-fallback `try`, and construction succeeds on a broken CUDA stack, so the fallback can never fire for this failure mode. ⛔ The 30-minute block seen twice (Phase 22, Phase 23 regression) is **not** explained by this and was not reproduced by the bounded harness. | install CUDA 12 cuBLAS in the dev tree, or measure the sidecar path directly | G7, G24 |

## Phase history

| Phase | Gate | Report |
|---|---|---|
| 28 Independent re-audit + RC freeze (read only) | **`BLOCKED_EXTERNAL`** | Every Phase 26 finding re-derived **from source at HEAD**, not from Phase 27's report: all closed, no P0/P1 left. Scope held hard — 16 files, all under `apps/`, and **zero** lines in `platform_core/` or `server/`; B25-01 had a live opportunity to break that and used the existing `AppManifest.bao_tri` hook instead. ⭐ Six gates moved FAIL->PASS and two PARTIAL->PASS. G10 is real now rather than vacuous: cuts happen, each decision carries reason/confidence/threshold/evidence, `preserve` refuses to cut even when every scene is recommended for removal, and `so_doan_bi_cat: 1` proves no dubbing was paid for a dropped scene. 🔴 **G14 got worse, not better**: Phase 26 recorded "repair computed but never driven"; the orphan check shows `qc_ai.py` itself has no caller either. 🔴 **G9 and G17 remain NOT PASS** — measured, not assumed: `:8120` is **open but needs a token**, and `tests/fixtures/asv_e2e_that/` does not exist. 🔴 **And one measurement in this phase was wrong**: it reported machine B's gateways unreachable after probing `127.0.0.1:8199/8299` — but they listen on **machine B**, `192.168.2.66`, where both are **OPEN** and answer `401` for lack of a token. Machine B is up; the `ltt_llm` credential already exists (there are live measurements against it in `docs/audit_ltt_llm/`). Corrected in `28_REPORT.md` rather than edited away. ⚠️ And the audit's own first probe was **wrong** about RENDER reading `gpu_uuid` — `getattr(ctx, "gpu_uuid", "")` reads through a string literal, invisible to an `ast.Attribute` walk: a check aimed at the wrong node type returns a confident, clean, false answer. Evidence re-run at the RC SHA: E2E **20 passed**, perf **12 passed**, cluster **1051 passed**, gate **PASS**. | [`reports/28_REPORT.md`](reports/28_REPORT.md) |
| 27 Blocker remediation | **PASS** | Nine findings, and the audit's own conclusion held: they were **one habit** — a capability finished, unit-tested, and never connected. Closing them showed the habit had also infected the test doubles. 🔑 For B22-01 the schema of a single VLM answer was described in **four places and no two agreed** (prompt asks flat · `DOC_CANH` declared a `canh` wrapper · the reader tolerated both · the E2E double returned a batch API that never existed), so a response obeying the prompt exactly would have been **rejected**. And the prompt had never attached a frame — it said "there are N representative frames" and sent none, so a vision model was selected to answer a question a text model answers identically. 🔑 B24-01 was wrong in **three** places, and the deepest was that COMPOSE decided the encoder from `ctx.gpu_uuid` — COMPOSE and RENDER are two jobs and a lease dies with its job, so the question was asked where the answer could never still hold. ⛔ And a pin was **protecting the defect it was written to prevent**: `test_renderer_KHONG_xin_GPU` forbade `gpu_env` on a sentence true for one preset since Phase 12. 🔴 Wiring the retention sweeper turned a harmless label into a live command — `HAN_TRUNG_GIAN` was stamped on the **deliverable** too, harmless only while nothing swept; the two changes had to land together. ⭐ The check the audit asked for (`test_453`) found the **sixth and seventh** instances (`qc_ai.py`, `sua_chua.py`) and says plainly it catches 3/5, not 5/5. ⚠️ And the phase got one thing wrong about itself: B23-01 was reported FIXED before its guarding pin was run, and the pin refused a fix that was half of one. Measured: NVENC +228 MiB but **88 % encoder** (V4-R15). E2E **20 passed**, perf **12 passed**, invariants **188 passed / 1 xfailed**. | [`reports/27_REPORT.md`](reports/27_REPORT.md) |
| 26 Independent audit (read only) | **`AUDIT_COMPLETE_WITH_BLOCKERS`** | Read from source, not from STATE; no code touched. **Five new findings** (A26-01..A26-05) and four recorded blockers re-verified from the code rather than from the claims about it. 🔴 **A26-01 (P1)**: the translation stage's fingerprint contains **no model identity** — it reads a dead module's empty constant while `qwen38-api` does the work, so changing the model invalidates nothing; and it is **masked by B23-01**, meaning fixing the cache alone would start serving stale output. 🔴 **A26-05 (P1)**: the smart preset's own description promises scene removal that measurement shows never happens, with a quality cost charged for it — the defect class Phase 21 named while shipping an instance of it. **A26-03 (P2)** contradicts STATE: V4-R01 is recorded CLOSED, but `routes.py:254` still `await read()`s the whole upload **before** the size check, violating G6's exact wording. ⭐ And the audit's own conclusion: **one habit, five times** — the VLM, the stage cache, the hardware encoder, the artifact sweeper and `dich_thuat.py` were each finished, unit-tested, and never connected to a running path. A capability with a green test and no live caller looks exactly like a finished feature from every angle except the only one that matters; Phase 27 should add the check that finds them all before fixing them one by one. Gates: G3, G4, G6, G8, G9, G16 **FAIL**; G10, G13, G14 partial; G17 not PASS (external evidence still missing); the other ten PASS. | [`reports/26_REPORT.md`](reports/26_REPORT.md) |
| 25 Security / migration / hardening | **PASS** | 🔑 **The test suite and the server had never been compared.** Tests build the schema with `create_all()`; the server runs `alembic upgrade head`; nothing in this repository — for **any** app — had ever checked that the two agree. A column added without a migration passes every gate and breaks on the first deploy. Measured on a temporary database: **zero drift for ASV tables**, and a guard now keeps it that way (adding an un-migrated column turns it red). 🔴 **Redaction locked the front door and left the back one open**: `lenh_da_che` masked paths in the render command while the same record stored ffmpeg's `stderr` unmasked — and ffmpeg prints full paths there. ⚠️ And the first masker leaked precisely what it protected: it ended a path at whitespace, and Windows paths contain spaces — inside the user's real name. A terminator must be what actually ends a path, not what usually does. IDOR now covers all **six** V4 object types (Phase 05 covered three; `asv_work_item` and `asv_usage` arrived later carrying customer data). ⚠️ **B25-01: retention is a label with nothing behind it** — nothing sweeps, and `assets.don_theo_run` has no caller: the fourth capability in four phases built and never connected. 🔴 That pin was also wrong first: it compared expiry *timestamps*, passed because RENDER is promoted 70 s later, and was measuring the clock — third instance in three phases of an assertion holding for a reason unrelated to its subject. New `san_sang.py` answers 'can this machine run me' with **three** states, because a failed probe is not an answer and must never count as ready. New `RUNBOOK.md` covers the five drills and ends by naming what it **cannot** fix, so an on-call person does not hunt for a button that does not exist. 14 tests + 1 xfail, **8/8 mutations red** after two of them had to be re-aimed. | [`reports/25_REPORT.md`](reports/25_REPORT.md) |
| 24 CPU/GPU performance and load | **PASS** (one blocker recorded) | 🔑 **The shared GPU slot stays shared, and a measurement is why.** `pipeline.CHUOI` had written down the exact experiment that would release it — peak CPU < 70% and free RAM > 8 GiB with demucs and ASR concurrent. Run: throughput **x1.5** (63.53 s sequential -> 42.43 s concurrent, better than the x1.3 predicted), free RAM 9.1 GiB clears its condition, and **peak CPU 78.6% fails the 70% one**. The tempting result was one line of config away and measurable; the pre-written condition said no. 🔴 **B24-01: the smart preset never uses the hardware encoder** — the host has `h264_nvenc`, the run records `libx264`, because COMPOSE decides from `ctx.gpu_uuid` while running on a lane that is never granted a GPU. Third capability in three phases that was finished and never connected. 🔴 **And Phase 22's CUDA-ASR entry was wrong**: the path does not hang, it fails in 0.23 s with `cublas64_12.dll is not found` — production is unaffected because it uses the WhisperX sidecar, and the owner app's CPU fallback guards the constructor rather than the call that actually fails. ⭐ Two of my own instruments were corrected before their numbers were read: the background load was sampled **after** the upload had already started work, and the VRAM check passed for any declaration on a CPU-only tree — it now skips with that reason instead of showing green. Repeated-work audit: source hashed twice (455 MB/s -> 0.2 s today, 4-9 s at the 2-hour cap), 21 ffprobe, 67 storage reads — **nothing changed**, because the evidence says none of it is worth the churn yet, and the number that would change that is written down. 6/6 mutations red. | [`reports/24_REPORT.md`](reports/24_REPORT.md) |
| 23 Failure / restart / retry / cancel | **PASS** (one blocker recorded) | 🔴 **There was no automatic retry at all.** Three mechanisms built for it existed and none was connected to the others: `loi.phan_loai` distinguishes `TAM_THOI` from a final error, `STAGE_FAILED_RETRYABLE` sits in the state table, and stage jobs dedupe on `asv:{run}:{stage}:a{attempt}` — a key shaped around an attempt counter. But `_thu_ket_qua_job_con` marked **every** failed child terminal, and nothing resubmitted a retryable stage. One flaky ffmpeg call ended the whole run — and since a terminal run has settled, `thu_lai_giai_doan` refuses it, so the only way forward was a **new run** recomputing demucs and ASR from scratch. 🔴 **A dubbed line already paid for was synthesised again**: per-segment checkpoints are committed, but the audio only becomes an artifact when the whole stage finishes — measured **6 voice calls for 3 segments** after one slip, and `UNIQUE(run_id, ma_dispatch)` hid it by blocking the second *write* while the GPU did the work twice. Fixed by reusing the segment still sitting under its staging key. 🔴 **And my own fix opened an unbounded loop**: `_thu_ket_qua_job_con` reaches the retryable state by a second road that asks nothing about attempts, so the submit site would respawn a job forever — the cap belongs at the last point before the action, not at one of the roads leading to it. ⚠️ **The first measurement of the phase described the test harness**, not the product: `test_402`'s runner passes `retry=False` for every exception, turning every failure final — exactly the question under test. 🔴 And mutation testing caught **two of my own tests measuring nothing**: they asserted the cache *refuses* a damaged artifact, and were green because it refuses everything — which is how B23-01 was found. 21 tests + 1 `xfail(strict)`, **9/9 mutations red** (plus one equivalent mutant, recorded as such). | [`reports/23_REPORT.md`](reports/23_REPORT.md) |
| 22 E2E functional acceptance | **PASS** (one blocker recorded) | 🔴 **The renderer delivered the wrong audio track.** `giai_doan_ket_xuat` loaded `tieng.nen` — the background bed — so every delivered video carried the music separated out of the customer's own source and **not one line of the dubbing**; everything phases 14–16 built was written to a file nobody read. No test caught it because both halves were correct and tested: Phase 16 proved the master is built right, Phase 17 proved the command is built right, and nobody checked the command read the right **field**. What exposed it was a measurement, not a code reading — **-18,69 LUFS** against a -14 target with **+4,1 dBTP** against a -1,5 ceiling is the signature of a signal that never passed `loudnorm`. 🔴 **And that defect was hiding a second one**: with the master finally in use, T3 went red — `loudnorm` shifts timestamps ~0,1 s, `-t` then cut the master short, and `-shortest` **truncated the picture**, breaking the preserve preset's whole promise. Invisible before, because the bed is always exactly as long as the source. `apad` does nothing (the samples are not missing, the timestamps are displaced); `asetpts=N/SR/TB` fixes it, and dubbed lines landing on their source timing went 3/4 → **4/4**. 🔴 **Both paid model calls would crash on a real model**: two call sites passed `ai.goi`'s raw *string* straight into `.get("doan")`, so translation had never once completed against a live provider — green only because the shared double returned a **dict**, which the real door never returns. ⭐ **The fixture caught me too**: before it had a background bed, T4 failed at -15,16 LUFS and it was tempting to call the -14 target unreachable; the LRA of 19,7 came from speech separated by digital silence, and with a bed the same chain lands at **-14,62**. Reporting a defect that does not exist is the most dangerous way an acceptance suite can lie. 19 tests + 1 `xfail(strict)`, **11/11 mutations red** after two holes, cluster **1113 passed**. ⚠️ Recorded not fixed: `smart_localize` produces **zero cuts** — see `open_blockers`. | [`reports/22_REPORT.md`](reports/22_REPORT.md) |
| 21 Product UI + API truth | **PASS** | 🔴 **The headline feature had no way to be chosen.** The string `preset` appeared **zero times** in `routes.py` and zero times in the template — so the whole V4 product offered the customer *one* of its two presets, and the entire `smart_localize` path that phases 12–18 were built on was a road **nobody could reach**. 🔴 **And the form offered a "default voice" the engine refuses to serve**: Phase 09 removed the silent default, but the form kept the empty option — a customer choosing it would pass four stages, have credits held, and fail mid-chain. The fix is not a more permissive engine; it is to stop offering something that does not exist. `AUTO_MATCH` is offered but **says plainly it is not ready**, because exposing a control that silently cannot work is the same false-feature defect from the other side. 20 tests, **11/11 mutations red** — but only after **eight consecutive holes**, every one in the route or template, which is the entire subject of this phase: I had tested the tables *behind* the form instead of the form. A ninth found that nothing checked the **error page**, where a mistyped submission returned a form with **no voice to choose**. ✅ Verified in a real browser on a throwaway database (this machine is production) — no console errors, all requests 200 — and the browser caught what HTTP tests could not: the page rendered **half English, half Vietnamese**, because the new strings had no EN entries. | [`reports/21_REPORT.md`](reports/21_REPORT.md) |
| 20 Observability + cost explainability | **PASS** | The three pieces all existed and had **never met**: the ledger, the per-unit checkpoints, and the stage/job timeline lived in three separate queries — so an operator asking "why did this cost that" performed a join **nothing checked**. ⭐ A stage marked `succeeded` says nothing about how much work happened: two runs can both read `succeeded` while one called the model 200 times and the other zero, and their invoices differ completely. 🔴 **The reconciliation runs in both directions, and only one is easy** — mutation testing proved it: removing the check for *unit charged with no ledger row* stayed green, because in the normal path both are written in one transaction, so the state never arises by accident. And that is the **expensive** direction: a charge against a customer with no supporting document. ⚠️ My first test built the orphan by calling `su_dung.ghi` — which **creates** the work item, so the state cannot exist through the API at all. But it arises by another road (a unit deleted while the row remains), and that is exactly what the check guards: a test that can only build state through the API would conclude "this cannot happen" while the guarded paths are the ones that **do not go through the API**. The customer view reports cost by capability and leaks neither stage names, provider app names, owner id, fingerprints nor job ids — four mutations, one per leak, all die. 14 tests, **11/11 mutations red**, 1021 in the cluster. No billing change: the phase permits one only on **proven** defect, and there was none. | [`reports/20_REPORT.md`](reports/20_REPORT.md) |
| 19 AI QC + targeted repair | **PASS** (scoped — see report) | 🔴 **The dangerous direction is the reverse one.** A line the TTS misread must **not** go back to `content_process`: that text is *correct*, and rewriting it pays to swap one correct sentence for another — which can be misread again. A mistranslation is the opposite: re-reading it any number of times yields the same wrong meaning. When one segment carries **both**, the earlier stage wins. Both directions are pinned and both inversions die under mutation. ⛔ A broad rerun is forbidden not only for cost: re-running a stage that succeeded gives a **different** result, so it trades one known defect for a set of unknown ones. **Confidence is a field, not a rounding step**: below threshold a verdict is recorded but generates no repair — an unsure model is not a reason to pay to redo work, nor a reason to hide the observation — and **missing confidence defaults to 0, never 1**, or a malformed response becomes a paid repair order. Speech QC is a **measurement** (two strings, one ratio) and carries confidence 1.0. The VLM is asked **only at the joins**: an untouched scene has nothing to ask about. Repair cycles are capped **tighter than Phase 15's** because that loop corrects a *measured* quantity and converges, while this one corrects a *subjective* verdict — looping is paying to watch the model change its mind. 25 tests, **19/19 mutations red**. ⚠️ Scope stated honestly: the plan is computed and tested; **driving** it (invalidate those units and re-run) is recorded as debt, not claimed. | [`reports/19_REPORT.md`](reports/19_REPORT.md) |
| 18 Technical QC | **PASS** | 🔴 **QC was blocking exactly what it was supposed to let through.** Phase 17 made the cutting preset real; QC did not know it existed, and two of its twelve checks would fail on **every** smart run — T3 compared the video hash against the source (but the smart preset must re-encode, so it can never match) and T2 compared duration against the source (but being shorter by the removed scenes **is the product's purpose**). Both are now mode-aware, and neither was loosened. **New T13**: a file can be valid, the right length, correctly loudness-normalised, and **entirely black** — nothing caught that before, because T1 only asks whether a video stream exists and an all-black stream is one. Threshold deliberately very low (2.0/255) so it cannot be confused with a night scene, and a failed *measurement* is never a failed *check*. ⭐ **An optimisation refused because the measurement said so**: full-stream hashing costs **0.27 s** on a 154 MB file (~3.5 s at the 2-hour ceiling) — the premise that it is expensive does not hold here, and every cheaper method is strictly weaker evidence. What did change: hashing is skipped in cut mode, because computing a comparison whose answer we already know is noise with a runtime cost. 16 tests, **13/13 mutations red** — two holes found first, both at the **seam** rather than the policy: the checks were tested by calling them directly, so mutations that made the *stage* pass wrong values stayed green. That is exactly where a smart run would fail in production. | [`reports/18_REPORT.md`](reports/18_REPORT.md) |
| 17 Compose + dual render + GPU encode | **PASS** | 🔴 **The cutting preset cannot stream-copy, and the measurement settles it:** GOP is **8.333 s** on a file this chain produces, so a cut would be dragged up to 8.3 s from where the audio master was built — re-encoding is not an optimisation, it is the condition for picture and sound still matching. ⚠️ **My first encoder benchmark used the wrong scale** (`cq=23` is not `crf=23`), making NVENC look pointlessly twice as large. At matched quality (SSIM ≈ 0.995) NVENC is **1.68× faster and 25% larger** — neither dominates; the deciding axis is mean host CPU **61% → 41%** on a machine whose scarcest resource is CPU. And stated accurately: both peak at ~91%, because decode and the concat filter stay on the CPU — NVENC offloads the *encode*, not everything. 🔴 **A test written before this phase caught me removing a guard**: `test_427` anticipated this refactor and warned that the wrong way to relax "never re-encode" is to delete it, because preserve then loses protection **silently**. I had moved the decision upstream and left the renderer blind; the manifest now carries the preset and the renderer cross-checks at the last gate. The renderer also **stopped mixing audio** — Phase 16's master would otherwise be normalised twice and read by nobody — and `_loc_am`'s four earned lessons moved into `am_master` with their tests. 24 tests, **19/19 mutations red**, three holes found first — including my `dual_mono` test **scanning file text**, so the comment explaining the rule satisfied it and removing the code stayed green: `test_401`'s lesson inverted, fixed by reading the AST. | [`reports/17_REPORT.md`](reports/17_REPORT.md) |
| 16 Timing plan + audio master | **PASS** | 🔴 **The cutting preset was placing every line on the wrong clock.** `lap_ke_hoach` planned on the **source** axis, so with `smart_localize` a line at source second 120 went to output second 120 — while a cut scene had already moved its real home to second 74. Not a fixed offset: the error **accumulates with every cut**, so the more the editor removes the further the ending drifts, and nothing raised. `BanDoThoiGian` is the missing conversion, and a timestamp *inside* a cut returns **`None`, never the nearest edge** — snapping turns a line that was removed into a line placed wrong. ⚠️ **My own patch nearly re-created the bug**: `ngan_sach_doan` still read source marks while `tong_ms` had become output time. And my first test for it pinned the **signature** instead of the **behaviour**, so a mutation passing source marks stayed green — the replacement uses a fixture where the two clocks give different placements (5.6 s vs 4.8 s). AudioMaster is FFmpeg only (AST-pinned, no model call), **batched** because one filter graph with 400 inputs exceeds Windows' 32,767-character limit and is truncated **silently**, `amix` not `concat`, always `normalize=0` (the default would quieten the bed for every voice added), loudness normalised **once at the end**. 🔴 **A guard that could never fire — the third in five phases**: "output not longer than source" is already proven by the two checks above it, so no input could trigger it; removed from the code and pinned in tests as a consequence. Preserve preset returns the identity map **without reading the edit plan at all** — an unnecessary dependency is an unnecessary failure path. 26 tests, **19/19 mutations red**. ⚠️ Phases 15 and 16 share one clean gate — Phase 15's own run was voided by the gate itself when I created this phase's files mid-run. | [`reports/16_REPORT.md`](reports/16_REPORT.md) |
| 15 Voice synthesis + bounded fit | **PASS** | A four-rung ladder whose **order is the policy**: measure on the real file → rewrite *that one line* → light time-stretch inside the declared cap → mark `CAN_SUA`. Rung 3 must not precede rung 2 — stretching distorts the voice, rewriting does not. 🔴 **The third rung could never be reached**: the tolerance (0.15) was exactly the stretch cap (1.15), so a segment was either inside tolerance or already past the cap. A four-rung ladder on paper had three when it ran — and it failed in the worst way, **not at all**: every segment still got a valid status and one policy branch simply never executed. The *relationship* is now enforced at module load, not just the value. Tolerance is asymmetric (0.08 vs 0.35) because the consequences are: long overruns the next shot, short leaves a gap `thoi_gian.py` already absorbs. Phase 14's voice debt is paid — the stage reads `ma_giong` from the document, not `settings`. Cost is billed once by a **unique constraint**, in seconds, and two counters are reported (segments vs TTS calls) because collapsing them would make the cost report lie. 🔴 The first mutation run was **contaminated**: a second run started while it was alive, and its restore wrote back a copy still holding the first's mutation — leaving the loop bound removed in the tree and producing **five fabricated "caught" verdicts**. Caught by a number that made no sense ("voice read from settings" has no reason to hang). The clean run then found two real holes: `khe_cua` could return the end timestamp instead of the duration and stay green (every fixture starts at 0, where they are equal — the ladder would have **silently switched off** for every segment after the first), and the fingerprint could ignore the adapted text, so a rewritten line would **reuse the old audio**. 20 tests, 15/15 mutations red — one of them caught by **hanging**, which is the correct signal for removing a loop bound. | [`reports/15_REPORT.md`](reports/15_REPORT.md) |
| 14 Dubbing adaptation for retained segments | **PASS** | `CONTENT_PROCESS` stops being a translation stage: its input is now the **retained** transcript, so a segment in a cut scene is never sent and never paid for. The DubbingDocument is a deliberate **superset** of the old text document — changing the shape would have forced phases 15-17 and QC into the same commit. Lines carry source **duration** (Phase 15 shortens to fit; shortening a line written without knowing its budget is repairing what should not have been wrong) and the neighbouring **retained** lines (after a cut, the previous line can be three minutes away in the source). 🔑 Results are keyed by **segment id, never position**: 12 sent, 11 returned, merged by position shifts every later line onto the wrong shot — and nothing fails, the document is still well-formed. 🔴 **Two voice keys had been running side by side** (`giong_id` vs `voice_id`), so a run could have its lines written for one voice and spoken by another with nothing raising. 🔴 **Things written but never read**: Phase 12 stored the edit plan and scene index with no deserialiser — nobody noticed because it never read its own output; and the `smart_localize` preset **had never run end to end**, failing at its first step because it looked for a video artifact that `media_prepare` deliberately does not emit. 🔴 `commit`, not `flush`: a checkpoint that is not durable never existed — the `database is locked` error was the symptom that made the semantics obvious. 24 tests, **19/19 mutations red**, two of which were holes in my own tests — the spy guarding the phase's central claim was **vacuous** (no segment lay only in a cut scene, so the assertion held for an implementation that sends everything). And a real bug: `chia_lo`'s default bound the batch size at definition time, so setting the constant changed nothing. ⚠️ AUTO_MATCH still cannot resolve — no stage produces a ContentProfile. | [`reports/14_REPORT.md`](reports/14_REPORT.md) |
| 13 Audio separation quality + resources | **PASS** | 🔴 **A legal job, running alone, was enough to kill the host.** Measured on the production venv (the test interpreter is CPU-only and could never have run this): VRAM is **flat at ~1,1 GiB across a 30× duration range** — the thing that scales is RAM, `RSS ≈ 1253 MB + 3,35 MB/s`, i.e. **24,8 GiB for the 120-minute video the product explicitly accepts**, on a 31,9 GiB machine with ~17,8 GiB free while serving. `AppManifest` declares `gpu_vram_mb` and has **no field for RAM** — the one resource that grows is the one admission control cannot see. Fixed by bounding consumption, not by lowering the product ceiling: block-wise separation → **2,59 GiB at 7 200 s, measured not extrapolated**, and faster. 🔴 `shifts=1` (demucs's default) was one pass at a **random** offset divided by one — all the randomness of shift augmentation, **none** of the averaging — which made `van_tay_tach`'s determinism promise false; now bit-identical between runs. 🔴 Parity nearly shipped on two bad measurements: the first had **no control** (the same code differed from itself by as much), and the second hid the shape behind an average — profiling showed block 1 **bit-identical** and every later block uniformly offset, because `apply_model`'s internal grid was out of phase. Aligning block boundaries to that stride took the bed from 27,1 dB to **54,4 dB** — 23 dB *better* than the run-to-run variation the product already had. 🔴 And the interlock revealed **31 tests in 9 files were loading htdemucs for real every gate run**: the old barrier sat on the two *direct* callers, so every indirect path through the job queue walked past it. 24 tests, **17/17 mutations red**, two of which were holes in my own tests — an identity fake model cannot detect a broken crossfade, because blending two equal signals returns the same signal under *any* weights. | [`reports/13_REPORT.md`](reports/13_REPORT.md) |
| 12 Edit plan + MVP presets | **PASS** | 🔴 **Closes V4-R07 (P0)** — a chain change, not a new file. V2 ran the paid translation stage at position 4 with **no edit plan in existence**, i.e. it translated and paid for dialogue belonging to scenes that would be cut. `EDIT_PLAN` now sits between `TRANSCRIBE` and `CONTENT_PROCESS` (chain 9 → 10, runs end to end through the real queue), and invalidation is one-directional: changing the plan reaches `content_process → qc` and **nothing upstream** — re-running a paid transcription because of a picture decision is the same waste pointing the other way. `localize_preserve_picture` never cuts **and never even reads the VLM's opinion**: an unreachable opinion cannot be opened by accident. 🔑 Dialogue scenes need 0.85 to remove vs 0.65 — a silent scene cut by mistake loses a shot, a dialogue scene cut by mistake **breaks the story**. 🔴 **The empty-video guard had never once been the rule that saved us**: the 50 % floor always fired first, so mutation removed the guard and the suite stayed green. The new fixture makes the plan **lie about its own ratio**, which is exactly what a ratio bug would do — and there that guard is the last thing between the customer and an empty file. ⚠️ A **second instance of the flaky test I created in Phase 07** surfaced here and was fixed. 28 tests, 8/8 mutations red, 432 passed. ⚠️ Debt: the stage passes empty `hieu_canh`, so `smart_localize` keeps everything for lack of evidence — correct, but not yet smart. | [`reports/12_REPORT.md`](reports/12_REPORT.md) |
| 11 VLM scene understanding + ContentProfile | **PASS** (real-VLM smoke unavailable, stated) | 🔑 **The debt Phases 06 and 08 both recorded is paid here** — `ai.goi_tinh_tien` gates the budget *before* sending and writes the ledger on **all three** outcomes; writing only on success is how an ambiguous dispatch disappears from the books at exactly the moment it must be visible. 🔴 **A real conflict between Phase 06's rule and the platform's reality**: `cong_vlm.SuDung.dang_tin` is False when upstream returns no usage, but a `DA_GIAO` record requires a unit and quantity > 0. Both shortcuts lie — `so_luong=0` claims it was free, `TU_CHOI` claims it never ran. ⭐ New unit `LUOT`: **one delivered call** is measurable and true, and it does not pretend to know a token count. Two calls, not one — a bad scene must not ruin the profile, and a profile edit must not re-read every scene. ⛔ **A malformed response is not a successful artifact, and it still costs**: a scene *read and returned garbage* differs from one *never read*. That distinction reappears in the error table — `ai.LuocDoSai` is `TAM_THOI` (parse failed at transport, models are stochastic) while `HieuCanhError` is `NGUOI_DUNG` (JSON parsed and **carries a wrong value**; the model ran and was charged). Same shape, different layer, opposite fate. 35 tests, 10/10 mutations red, 434 passed. | [`reports/11_REPORT.md`](reports/11_REPORT.md) |
| 10 Scene segmentation + frame sampling | **PASS** (benchmark deferred, stated) | Built rather than extracted — the proven engine lives in the **read-only** reference tree and `taoclipngan`'s copy is under gitignored `vendor/`. 🔴 **Memory dictated the shape**: a 40-min 1080p source is ~60 000 frames (~350 GB raw), so `ffmpeg`'s `select='gt(scene,T)'` does the comparing and ASV reads only timestamps — **no pixel enters Python**, pinned by AST; `-f null -` writes nothing; one ffmpeg call for the whole video, pinned by counting `subprocess.run`. Frame cap sits **where frames are produced** (60/run, 2/scene, 512 px long edge) because the vision window is 65 536 tokens — a cap after the spend is a cap in the wrong place. 🔴 **The even-distribution test caught a real bug in my first draft**: it gave one frame to each of the first 60 scenes and **nothing to the last 40** — the exact tail-truncation its own docstring forbade. 🔴 And the merge-vs-drop test **could not tell the difference** until mutation showed it: the fixture put short scenes at the *start*, where a separate head-merge rule closed the gap anyway; a short scene in the **middle** gets no such rescue. 28 tests, 6/6 mutations red, 376 passed in regression. ⚠️ Debt: `NGUONG_DOI_CANH = 0.4` unmeasured on real footage (written down as such, and it is inside the fingerprint); wall-clock CPU profile needs a representative source file the repo does not have; persisting `SceneIndex` as `AsvAsset` belongs to Phase 11, its first consumer. | [`reports/10_REPORT.md`](reports/10_REPORT.md) |
| 09 LTT Voice boundary + voice binding | **PASS** (2 reqs deferred to 15, stated) | **V4-R14 (P0) closed**: `giong_mau`'s 20 sample voices classified on three axes existed all along and were simply **not exported** — seven additive read-only names on both sides. `loc` is exported rather than letting ASV walk `DANH_SACH`, because a filter is a **rule** and two copies of a rule drift. 🔑 **AUTO_MATCH defers, it does not default.** With no ContentProfile it resolves to `CHUA_RANG` — a valid state that is neither failure nor voice — and `ma_giong()` **raises** on it. V2 did the opposite (`routes.py:135` `giong_id: str = Form("")` → empty took the default), which `ADR-V4-001` D-V4-04 forbids by name: a default **reads nothing from the video**. Deferring beats a placeholder because Phase 14 sizes sentences against the real voice's reading speed, so a temporary voice yields an adaptation that must be redone. Ownership is **not** re-implemented — `features.giai_giong` already filters `owner_id`, handles the shared store and drops inactive voices; getting the first wrong means a customer's video read **in someone else's cloned voice**. `rang_giong.py` synthesizes **zero milliseconds**, pinned by AST. ⛔ Reqs 1–2 (per-segment synthesis service) deferred to Phase 15 — the structural blocker (`asv_stage` holds one `job_id`) was removed by Phase 05's `AsvWorkItem`, but the brief's own index puts synthesis at 15 and the billing prerequisite is still unproven. 22 tests, 6/6 mutations red, 540 passed in regression. | [`reports/09_REPORT.md`](reports/09_REPORT.md) |
| 08 LTT AI text + vision boundary | **PASS** (1 debt stated) | 🔴 **A live bug, and ASV is its third victim.** `dieu_phoi.goi`'s own docstring warns that `{"ltt_llm": "ltt_llm"}` is wrong — `ltt_llm` is the app's public **alias**, not a model id, so `chon_key` raises and the dispatcher **silently skips the only provider**. Verified against the registry rather than assumed: `models_for("ltt_llm")` returns `qwen38-api` + `qwen38-vision` only. `dich_thuat.py:45` held that exact line; the two earlier victims are named in that docstring, and ASV went unnoticed because the stage is still a fake engine. ⭐ **An example in a docstring is code that people copy** — when it is wrong it is never wrong alone. New `ai.py`: six typed operations, model chosen **semantically** (`can_thi_giac` → `providers.model_capabilities`), token ceiling single-sourced from `ltt_llm.ngan_sach`, structured-output validation, prompt/schema version for fingerprints. Context windows differ — text 131 072 vs vision **65 536** — so a frame batch packed against the text ceiling is a 413 at runtime. 🔴 **Mutation found two holes in my own tests**: the ambiguity test was measuring the string fallback instead of the class-name branch, and the one-door guard locked `import platform_core.llm.dieu_phoi` but not `from platform_core.llm import dieu_phoi`. ⚠️ Also fixed a **flaky test I created in the Phase 07 unification**: making `do_tai=True` the default made three `test_431` cases read real CPU and change answer with load — green alone, red under `-n 4`. 28 tests, 7/7 mutations red. ⛔ Debt: nothing wires `su_dung.ghi` into `ai.goi` yet — no stage makes a paid call, and a ledger write on a path that never runs is a claim without a witness. Phase 11 is the first paid caller. | [`reports/08_REPORT.md`](reports/08_REPORT.md) |
| 07 ASR + diarization capability rebase | **PASS** | **Half the objective was already met, and saying so is the finding**: for ASR, `transcribe_file` was already declared, already the only name ASV touched, and already forwarded the platform-assigned card — so *"remove the private-path dependency"* had nothing to remove, and an AST test now proves that positively. The gap was diarization (V4-R15), closed with two additive lines on both sides. 🔴 **Exporting it surfaced a live defect older than Auto Scan**: `pyannote_runner.py:20` did `if torch.cuda.is_available(): pipeline.to(torch.device("cuda"))` — it took the first card torch saw, **ignoring `gpu_lease` entirely**, while `manifest.py:51` declares `gpu_vram_mb=2000` so the platform *believed* it was arbitrating. Fixed by reusing the owner's own `_env_ghim_gpu`, adding no second arbiter. ⛔ `SCHEMA_BAN_GHI` deliberately **not** bumped — `kiem` compares by equality, so a bump invalidates every stored transcript and the customer pays for a second ASR pass they never asked for; speaker fields are additive, plus one explicit `phan_vai` with three values so Phase 09 can tell **no evidence** from **evidence that found nobody**. Diarization runs only for `AUTO_MATCH`; missing or malformed settings mean **do not spend**. ⭐ A Phase 02 test failed *forward* — it pinned the opposite state and carried the fix instruction in its failure message; a test pinning a temporary state must say what to do when it stops being temporary. ⚠️ Also relinked the ASV alembic chain after the trunk merge created **two heads** (the merging side rebases). 18 tests, 7/7 mutations red. | [`reports/07_REPORT.md`](reports/07_REPORT.md) |
| 06 Billing usage + budget foundation | **PASS** (1 debt stated) | `AsvUsage` + migration `c81d3f5a90e7` + `su_dung.py`. 🔑 **The ledger is not a second money path** — money still flows through exactly one column (`AsvWorkItem.credit_actual`); the table *explains* it, and `doi_soat` pins `item.credit_actual == Σ delivered rows`, called from `quyet_toan` **before** the charge. Three of the eight requirements were **already implemented** (child jobs use `jobs.submit`, exactly-once aggregation, no price recompute) — the honest output for those is three AST pins, not new code. 🔴 Four bugs found in my own work, each by a different mechanism: `db.rollback()` on a duplicate dispatch id destroyed **the caller's whole transaction** (→ SAVEPOINT); a reconciliation guard would have alarmed on all pre-existing rows; `test_427` caught `su_dung.py` **missing from the rebase map** (8 ADD → 9); and an integration assertion of mine encoded a contract the platform does not have — `credit.so_da_giu` returns **200** after settlement because it sums historical `CREDIT_HOLD` entries, not "still held". ⭐ Counting hold *entries* proves "one billing owner"; the sum never could, since one hold of 200 and two of 100 are indistinguishable. ⚠️ Also capped `demucs_runner` at 4 torch threads — the black box measured twelve of them at **462–984 % CPU each**, and that is precisely where `-n 6` cannot reach: it counts pytest workers, not what each worker spawns. 38 tests, 7/7 mutations red. | [`reports/06_REPORT.md`](reports/06_REPORT.md) |
| 05 DAG + item checkpoints + large input | **PASS** (2 sub-items deferred to 15, stated) | `AsvWorkItem` + migration `a4c17f9b62d0`; durable upload replaces `await video.read()`. 🔴 **`upload_sessions._SLUG` rejected 7 of 19 apps on this tree** (`ltt_llm`, `ltt_voice`, `prompt_ai_ommi` + the 4 ASV apps; on the main tree at `dac2406`, which has not merged the ASV apps, the same defect counts **3 of 15** — session `lttstudiosapp-73` measured that and the two numbers reconcile exactly) — no underscore allowed — including `ltt_voice`, which is *released and selling*. Invisible because the only caller (`autosubvideo`) is one of the few slugs without one, and `conftest` uses `APP_THU_SLUG="appthu"`: the suite exercised that path thousands of times, never once with a real slug. Widened by one character, purely additive, both directions pinned. 🔴 **Two more whole-video-into-RAM sites** beyond the one Phase 00 found — `_duong_doc_duoc` (no cap at all, and the durable path admits 2 GiB) and `kiem_hop_le`/`kiem_toan_ven` (every artifact of every run, `final.mp4` included). All three share a shape: **they never produce a wrong answer**, so the tests measure the largest single read, not the result. ⭐ Probing without downloading needed **zero** new code — `media.is_remote_source` already existed and its docstring already named the cost. | [`reports/05_REPORT.md`](reports/05_REPORT.md) |
| 04 Regression shield + heavy-test isolation | **PASS** | Found **3 real-model calls with no guard at all** — 2 × demucs (`test_406`), 1 × faster-whisper (`test_407`) — in a repo with **no pytest config to hang a marker on**. Gated behind `LTT_TEST_NANG`, because a marker only filters when somebody types `-m`, and "somebody forgets" is exactly what hard-reset this machine twice. Added a ratchet over every `tests/test_*.py` so the fourth one cannot arrive quietly. ⭐ Three drafts were wrong first: `assign_speakers` is 12 lines of interval arithmetic (proximity is not evidence), three call sites reach a heavy function but raise before the engine, and the ini check flagged its own explanatory comment — **the third text-scanning detector this session to punish the prose documenting it**. ⚠️ Full gate not re-run; debt recorded above rather than folded into the green rows. | [`reports/04_REPORT.md`](reports/04_REPORT.md) |
| 03 Rebase classification + architecture ADR | **PASS** | **17 KEEP · 6 EXTEND · 7 REFACTOR · 8 ADD · 0 REMOVE** — the default is KEEP and the exceptions are argued. `ADR-V4-002` designs `AsvWorkItem` with `UNIQUE(run_id, stage, item_key)` and proves it is **not** a queue by naming the 8 columns that would make it one, with a detector that fires on a synthetic queue table and stays quiet on a legitimate checkpoint one. ⭐ Found two guards in `test_421` that read wider than they were: `glob` is not recursive (so the first `services/` directory would leave their view silently) and they never scanned the three executor apps — where a stray thread pool would do the most damage. Widened to `rglob` × 4 apps, with an assertion that the new file set is a **strict superset** so §1 cannot degrade into a re-run under a new name. | [`reports/03_REPORT.md`](reports/03_REPORT.md) |
| 02 Capability inventory + boundary freeze | **PASS** | 19 apps censused; every V4 need classified with a traced caller. **13 SUFFICIENT, 2 EXTEND, 6 ABSENT** — and no capability recommended as new code without proof of absence (an AST scan, not a text scan). 🔴 **The phase's real output is a retraction**: this platform already implements V4's "stable cross-app boundary" rule via `BE_MAT_CONG_KHAI` + `APP_DUOC_DUNG_APP`, enforced by a linter inside the gate. V4-R02 (P0) and V4-R03 are withdrawn. ⭐ And the thing that actually blocks Phase 09 is not willpower but schema: `speech.ltt` is a fine contract with the wrong granularity, because `asv_stage` holds one `job_id` and per-segment TTS needs many. Phase 05 unblocks Phase 09. | [`reports/02_REPORT.md`](reports/02_REPORT.md) |
| 01 Product contract supersession | **PASS** | `ADR-V4-001` supersedes `auto_scan_mvp_v1` §1/§4 by banner, not by rewrite. Contract now exists in three forms: prose, constants (`hop_dong_v4.py`), and 20 tests. 🔴 **The pack's stated reason for `vi` is factually wrong** — LTT Voice is bilingual (`lan_ngon_ngu.py:6`, `language: ["vi","en"]`). Decision kept, justification replaced, and a test now goes red on exactly the move a future session would make after reading the wrong reason. One strict-xfail RED target left for Phase 12. | [`reports/01_REPORT.md`](reports/01_REPORT.md) |
| 00 Provenance and bootstrap | **PASS** | HEAD identical to the pack's SHA (no delta). Baseline certified at `FAIL (1/26)` with **0 ASV-owned failures** — V2's 7 failures were 3 commits stale, `b027e08` merged the peer fixes. 11 V4 risks read from code, 5 of them P0. ⭐ The find that reorders nothing but explains everything: `ltt_voice` **already exports** a stable `ToolSpec("speech.ltt")`; V2 bypassed it into `sidecar_client` only because `asv_stage` holds **one** `job_id` and per-segment TTS needs many. So Phase 09 is not unblocked by willpower — it is unblocked by Phase 05's `AsvWorkItem`. | [`reports/00_REPORT.md`](reports/00_REPORT.md) |
