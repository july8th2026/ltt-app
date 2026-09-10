# PHASE 12 REPORT — Voice Provider Integration

**The second paid stage, and the first with many billable calls inside one run.**

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 11 **PASS**; Phase 07 (credential isolation) **PASS**
- allowed change scope: voice provider adapters/services, runtime executor, tests

## Trace performed (item 1) — real contract, no invention

`apps/ltt_voice/jobs.py:84 _tao_tieng` · `features.py:92 chuan_hoa` (validates text,
rejects `voice_id` + `preset` together) · `features.py:187 giai_giong` — *"Đây là chỗ
**quyền sở hữu** được kiểm, và nó là chỗ duy nhất"* · `features.py:244 goi_cong` →
`(wav_bytes, headers)` · `features.py:69 DangBanTam` · `tham_so_cong_khai.TRAN_MOI_LUOT_SINH`.

Three facts that shaped the design:
1. `synthesize` produces **one file per request**, keyed on `ctx.job_id`;
2. `giai_giong` is the **only** ownership check;
3. **busy ≠ failed** — `features.py:219` records that wrapping `DangBanTam` as a failure
   turns "machine is busy" into "job failed", and a failed job **charges the customer for
   work that never ran**.

## ADR-001 D5 re-checked — delegation fails here too, for a different reason

Phase 11 amended D5 for CONTENT because delegation cannot chunk/merge. VOICE was expected
to hold, since `ltt_voice` declares `requires=("voice",)` honestly. It does not hold either:

- Auto Scan needs **one audio file per segment** — TIMING places each segment in its own
  slot. `ltt_voice.synthesize` writes to `voice/out/{owner}/{job_id}/tieng.wav`, so N calls
  with one `ctx` overwrite the same key.
- Prompt 12 item 7 demands **per-segment resumability**. One job for the whole script has no
  grain smaller than itself to checkpoint.

So VOICE calls three declared service functions and owns its own files, keys, lineage and
checkpoints. **`giai_giong` is inside that chain and cannot be skipped** — bypassing it to
"go faster" would open a path to using someone else's voice, the exact I6/I7 invariant
ADR-002 just closed.

## Decisions

**D-12-01 — one audio artifact per segment, plus an index.** A single continuous file leaves
TIMING nothing to place, and makes one corrected line force the whole script to be re-read.

**D-12-02 — the fingerprint is per segment**, over `(segment id, text, voice_id, preset)`.
That is what makes "regenerate only the missing segments" possible. A stage-level fingerprint
would make one bad segment cost a full re-read — and every re-read is money.

**D-12-03 — a segment longer than the quality ceiling is rejected, not silently split.**
1 500 chars is `ltt_voice`'s **quality** ceiling (#168 reports voice drift from ~3 000).
Splitting one line of dialogue into two synthesis turns turns it into two different readings
mid-sentence. Refusing is the honest answer.

**D-12-04 — three distinct outcomes: `MayBan`, `GiongMoHo`, `GiongError`.** Collapsing them
loses exactly what is needed to respond. Busy must be re-queued and **must not** be billed;
ambiguous must never be retried; ordinary errors may be.

**D-12-05 — the fourth executor, `asv_voice`, declares `requires=("voice",)`.**
The voice engine is a **separate service** behind loopback :8120, not a library loaded in the
worker — "has ffmpeg" does not imply "has the voice engine". It declares **no**
`gpu_vram_mb`: the worker loads no model, and reserving a card for a job that does not use
one would waste a scarce resource.

**D-12-06 — audio is validated by ffprobe before a segment counts as done** (item 8). A WAV
with correct headers and zero duration passes every format check, and TIMING would insert
silence exactly there with nobody the wiser.

## Changes

| Path | Change |
|---|---|
| `apps/auto_scan_video/giong_noi.py` | **new** — error classification, per-segment fingerprint, audio validation, ownership-preserving voice resolution |
| `apps/auto_scan_video/giai_doan_giong.py` | **new** — stage body with per-segment resume |
| `apps/asv_voice/` | **new** executor — `requires=("voice",)` |
| `apps/auto_scan_video/pipeline.py`, `thi_hanh.py` | VOICE → voice lane, dispatch |
| `apps/ltt_voice/__init__.py` | `+BE_MAT_CONG_KHAI` — **declaration only, no logic touched** |
| `tools/lint_app_contract.py` | +2 declared edges |
| `tests/test_409_asv_giong_noi.py` | **new**, 21 tests |
| `tests/test_401…` | `+apps/asv_voice` in the guard path list |
| `tests/test_402…`, `test_403…` | `+giong_gia` fixture; `voice` added to worker capabilities |
| `locale/en/LC_MESSAGES/messages.po` | +8 entries |

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_409…` | **21 passed** |
| `pytest tests/test_402… test_403…` | **35 passed** — five real stages in the chain |
| `python tools/lint_app_contract.py` | `ERROR: 0` (19 apps) |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline |

### Required verification

| Required | Test |
|---|---|
| two-user credential | `test_giai_giong_la_NOI_DUY_NHAT_kiem_quyen_so_huu` — `owner_id` and `voice_id` proven to reach the only ownership check |
| **partial batch** | `test_chi_sinh_lai_doan_bi_MAT` — delete one file, re-run generates **exactly one** segment |
| timeout after dispatch → ambiguity | `test_mat_ket_noi_thanh_GiongMoHo_khong_bao_gio_thu_lai` |
| malformed audio | empty WAV and non-audio file both rejected before the segment counts |
| **resume with some segments durable** | `test_chay_lai_KHONG_sinh_lai_doan_da_co` — second run makes **zero** engine calls |
| real smoke with credential | **not run** — see §"pending" |

## RISK-00-02 reproduced inside my own test suite

Adding the `voice` lane made three chain tests fail with `voice_synthesis` stuck at `queued`
— because their fake workers advertised `{api, ffmpeg, gpu}` and nothing served `voice`.

That is **exactly RISK-00-02**: a missing lane leaves jobs queued forever with no error
anywhere. `apps/ltt_voice/manifest.py:112` records the same failure hitting production.
Useful to have felt it in a place where it was cheap — and it is a live reminder that
`setup/4-nghiem-thu.ps1`'s lane assertion must cover `asv_voice` before release.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| I5 provider ambiguity | PASS | `GiongMoHo` distinct from retryable; busy distinct from both |
| I6/I7 ownership | PASS | `giai_giong` in the chain; declared surface makes bypassing it a lint failure |
| I8 durable DONE | PASS | ffprobe validation before a segment is counted |
| I10 cache correctness | PASS | per-segment fingerprint + integrity check before reuse |
| I12 routing | PASS | ffmpeg and gpu workers both refused the voice job; only `{voice}` claimed it |
| I16 safe logs | PASS | summary carries counts and durations, no dialogue |
| I1–I4, I9, I11, I13, I14, I18, I19 | PASS | 35 chain tests green |

## Two mistakes worth recording

**A test stub with the wrong arity.** My `giai_giong` stub returned a 2-tuple; the real
function returns `(ref_b64, preset, canh_bao)`. The test failed with `ValueError` — correctly,
and it was a fault in the **test**, not the code. A stub with the wrong arity is a stub
testing a different contract than the real one.

**`temperature`/`top_k`/`top_p` are asserted absent, not just avoided.** `ltt_voice` keeps
them off its public contract because its CUDA-graph cache keys on them. A comment saying
"don't pass these" is not a guard; `test_KHONG_truyen_temperature_top_k_top_p` scans both
modules by AST.

## Diff review
- changed paths: `apps/auto_scan_video/`, `apps/asv_voice/`, `apps/ltt_voice/__init__.py`
  (declaration only), `tools/lint_app_contract.py`, `tests/`, `locale/en/`
- one scratch script created and deleted; `.po` appended only, LF preserved
- no audio committed — every fixture is generated at run time; secret scan PASS

## Risks / external evidence pending

- 🔴 **RISK-12-01 (P1, new) — no real synthesis has been performed.** Every test uses a fake
  engine. A real call needs `LTTStudioVoice` live on :8120 plus a valid
  `LTT_VOICE_SIDECAR_TOKEN`. So **voice quality, and crucially the duration of Vietnamese
  speech versus its time slot (RISK-02-01), are unmeasured.**
  `TestChoBangChungNgoai::test_chua_goi_may_sinh_tieng_THAT_lan_nao` **fails the moment the
  engine becomes reachable**, naming the measurement task. `PENDING_EXTERNAL_EVIDENCE`.
- 🔴 **RISK-02-01 is now due.** Phase 13 fits Vietnamese speech into source segment windows,
  and Vietnamese is typically longer than English. Neither Phase 11 nor 12 could measure the
  real ratio. **Phase 13 must not assume it fits** — it needs a measured overflow rate or an
  explicit policy for what happens when it does not.
- **RISK-12-02 (P2, new)** — `setup/4-nghiem-thu.ps1` asserts a `voice` lane exists for
  `ltt_voice`; it must also cover `asv_voice`, or Auto Scan runs stall silently in a pooled
  deployment. Phase 22.
- **RISK-05-01, -10-01, -10-02, -11-01, -11-02** unchanged; each has a test that fails when
  its assumption expires.

## Exit gate

**PASS.**

Gate text: *"PASS when voice generation is owner-safe, paid-call-safe and resumable at the
smallest safe granularity."*

- **Owner-safe** — every synthesis passes through `giai_giong`, the single ownership check,
  with `owner_id` proven to reach it. The declared cross-app surface makes bypassing it a
  lint failure rather than a code-review question.
- **Paid-call-safe** — busy, ambiguous and ordinary failures are three distinct outcomes.
  Busy is re-queued and never billed; ambiguous is terminal and never auto-retried.
- **Resumable at the smallest safe granularity** — the grain is one segment, proven twice:
  a clean re-run makes **zero** engine calls, and deleting one file causes **exactly one**
  regeneration. Smaller would not be safe: splitting a line of dialogue produces two
  different readings mid-sentence, which is why an over-long segment is rejected instead.

**Explicitly forbidden and confirmed absent:** no timing splicing or composition inside the
provider adapter — asserted by AST scan for `concat`/`amix`/`adelay`/`apad` in both modules.

## Next phase prerequisites

Phase 13 (Timing / Pause / Alignment):
1. **RISK-02-01 must be settled here.** `fit_original` is the default `timing_mode`; if
   Vietnamese routinely overflows its window, the default is wrong and the contract needs an
   ADR, not a silent truncation;
2. inputs are ready: per-segment audio with measured durations, the index file, the bed, and
   the transcript's word timings;
3. `MVP_CONTRACT.md` §7 already fixes the tolerances — T7 (0.30 s start drift), T8
   (120–2 500 ms pause), T9 (≥ 0.80 s gap), T10 (0.65 anchor confidence);
4. `MVP_CONTRACT.md` §6 forbids `natural` mode from extending the video stream — excess is
   truncated at the last fitting segment boundary and QC warns.
