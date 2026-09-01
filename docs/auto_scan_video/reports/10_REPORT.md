# PHASE 10 REPORT — Transcript Engine Extraction

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 09 **PASS**
- allowed change scope: shared transcript engine/service extraction, Auto Scan adapter, tests

## Trace performed (item 1)

`apps/autosubvideo/transcription.py` — `whisperx_available:42`,
`_transcribe_whisperx:46` (sidecar subprocess), `_get_faster_model:112` (model cache +
CPU fallback), `_transcribe_faster:130` (`word_timestamps=True`, `vad_filter=True`,
`beam_size=5`), `_env_ghim_gpu:154` (**calls `platform_core.gpu.env_for`** — the
platform-owned path), `transcribe_file:162` (public surface, explicit fallback contract).
`apps/autosubvideo/whisperx_runner.py:18-26` (device/compute selection, alignment).

**Environment probe:**

| | |
|---|---|
| `faster_whisper`, `ctranslate2` | installed |
| `whisperx` | **not installed** ⇒ `transcribe_file` always takes the fallback path |
| model cache | `Systran/faster-whisper-{tiny,base,small,medium,large-v3}` present |
| `torch` | 2.11.0+cpu — ASR runs on CPU |

## Decisions

**D-10-01 — wrap `autosubvideo`'s engine; do not extract from `Bot_Whisper_FULL`.**
Prompt 10 names the legacy bot, but it was written before Phase 00 found an in-platform
whisper path. The legacy engine calls `gpu_arbiter.current_gpu` in two places
(`engine/stt.py:274`, `whisper_integration.py:207`) — it selects its own card, exactly what
I11/O6 forbid. The in-platform path already routes through `platform_core.gpu.env_for`.
Wrapping it is cheaper *and* correct; the deviation from the prompt is recorded rather than
made silently.

**D-10-02 — wrap the function, do not delegate a job** (ADR-001 D5). `apps/autosubvideo`
declares `requires=("ffmpeg",)` while declaring `gpu_vram_mb` for `transcribe`/`diarize`
(RISK-00-11). Delegating a job would inherit that mis-declaration and route GPU work onto an
ffmpeg lane. Wrapping the function lets Auto Scan run it inside `asv_gpu`, which declares
`requires=("gpu",)` honestly.

The cross-app edge is declared on **both** sides — `BE_MAT_CONG_KHAI` in
`apps/autosubvideo/__init__.py` and `APP_DUOC_DUNG_APP` in the linter — so it is a visible
decision, not a quiet reach. **No logic in `autosubvideo` was changed**, so its existing path
still runs: precisely what the exit gate and O10 require.

**D-10-03 — a canonical `TranscriptDocument`, separate from the engine's dict.**
`transcribe_file` returns a *tool's* shape, and that shape already differs between whisperx
and faster-whisper. Four downstream stages must not depend on it (O11).

**D-10-04 — segment ids are positional (`seg_0001`), and that is sufficient.**
The transcript is a **single atomic artifact**: recomputed whole or not at all, decided by
its fingerprint. If it is recomputed and segmentation shifts, everything downstream must
recompute too — and it will, because the transcript's fingerprint is inside theirs. A
content-hash id would give two identical segments in different places the same id, which is a
worse lineage error. The ids are stable *within the scope where they mean anything*.

**D-10-05 — the engine's `alignment_status` is preserved verbatim.**
whisperx force-aligns per word; faster-whisper does not and self-reports
`fallback_unaligned`. Hiding that difference would promise a timing precision we do not have.
Phase 13 reads it.

**D-10-06 — the transcript may not run longer than the audio.** Checked in the stage, not in
TIMING: drift caught here names its own cause; drift caught downstream shows up far from it.

## Changes

| Path | Change |
|---|---|
| `apps/auto_scan_video/ban_ghi.py` | **new** — canonical document, normalize, validate, fingerprint, safe summary |
| `apps/auto_scan_video/giai_doan_chep_loi.py` | **new** — stage body + engine wrapper |
| `apps/auto_scan_video/thi_hanh.py` | dispatches TRANSCRIBE |
| `apps/autosubvideo/__init__.py` | `+BE_MAT_CONG_KHAI` — **declaration only, no logic touched** |
| `tools/lint_app_contract.py` | +1 declared edge |
| `tests/fixtures/asv_media.py` | `+ban_ghi_gia()` |
| `tests/test_402…`, `tests/test_403…` | `+asr_gia` fixture on chain tests |
| `tests/test_407_asv_chep_loi.py` | **new**, 19 tests |
| `locale/en/LC_MESSAGES/messages.po` | +13 entries |

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_407…` | **19 passed** |
| `pytest tests/test_402… test_403…` | **35 passed** (59 s) |
| `python tools/lint_app_contract.py` | `ERROR: 0` |
| `python tools/check_i18n.py` | 774, at the mark |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline |

### Required verification

| Required | Evidence |
|---|---|
| unit / mocked | §1 contract tests — overlap, duplicate ids, word-outside-segment, wrong schema, empty transcript |
| **parity comparison** | `TestBocEngine` — the wrapper passes the engine result through **unchanged**, and forwards path/language/model/gpu_uuid/progress/cancel |
| **real tiny speech smoke** | `test_engine_ASR_that_chay_duoc` runs real faster-whisper. Measured: 1 s audio, `tiny`, CPU. Confirms `engine == "faster-whisper"` and `alignment_status == "fallback_unaligned"` |
| no-audio / invalid behaviour | empty transcript rejected; transcript longer than audio rejected with a named reason |
| cache reuse + corrupt invalidation | inherited from Phase 06 (`test_403`), now keyed on the transcript fingerprint |
| no Sheet/Drive/token registry | AST boundary guard over all Auto Scan files |

## The fixture problem, and why I did not solve it by weakening the product

Real ASR on the `lavfi` fixtures returns **zero segments** — correctly, because a sine tone
contains no speech. `chuan_hoa` then refuses the run, which is also correct: a video with
nothing spoken has nothing to dub.

That broke the chain tests. Two ways out:

1. let TRANSCRIBE accept an empty transcript — **weakens the product to suit a fixture**, and
   lets a run proceed through four billed stages to deliver a dub with no speech in it;
2. substitute the engine in chain tests, and smoke the real engine separately.

Took (2). `ban_ghi_gia()` produces a deterministic engine-shaped transcript; the real engine
is exercised by its own test. The docstring on the fixture states this so nobody later reads
a green chain test as evidence that ASR works.

Measured, and a second reason for (2): **2 s of audio took 22.8 s with `tiny` on CPU** —
about 11× realtime. A chain test cannot call that.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| I11 resource control | PASS | `gpu_uuid` forwarded from `JobContext`; engine resolves it via `platform_core.gpu.env_for`; AST guard clean |
| I12 worker routing | PASS | exit-gate test asserts the TRANSCRIBE child job's `app_slug == "asv_gpu"` |
| I8 durable DONE | PASS | document re-validated after reading back from storage |
| I10 cache correctness | PASS | fingerprint = audio checksum + model + language + schema/code version, each pinned |
| I15 legacy compatibility | PASS | `autosubvideo` gained a declaration and **no logic change** |
| I16 safe logs | PASS | `tom_tat` carries counts only — `test_tom_tat_KHONG_chua_loi_thoai` asserts dialogue never reaches `outputs`/logs |
| I1–I7, I9, I13, I14, I18, I19 | PASS | 35 chain tests green |

## Diff review
- changed paths: `apps/auto_scan_video/`, `apps/autosubvideo/__init__.py` (declaration only),
  `tools/lint_app_contract.py`, `tests/`, `locale/en/`
- two scratch scripts created and deleted; `.po` appended only, LF preserved
- no model weights or media committed; secret scan PASS

## Risks / external evidence pending

- **RISK-10-01 (P1, new)** — `whisperx` is not installed, so word timestamps come from
  faster-whisper's `word_timestamps=True`, **not** from forced alignment. Forced alignment is
  materially more accurate at word level, and Phase 13's timing tolerances (T7: 0.30 s) were
  written without knowing which path produces them.
  `TestChoBangChungNgoai::test_whisperx_KHONG_duoc_cai...` **fails the moment whisperx is
  installed**, naming the re-measurement task — so the assumption cannot quietly outlive its
  basis.
- **RISK-10-02 (P1, new)** — **no real speech sample exists**, so nothing here says anything
  about recognition accuracy. A second guard test fails as soon as one is added. Recorded so
  Phase 21 does not mistake a green suite for verified ASR quality.
- **RISK-10-03 (P2, new)** — `MODEL_ASR = "large-v3"` is the production choice and is correct
  for a GPU lane. On a CPU-only host it would be unusably slow; `max_runtime_s` (3600) would
  kill long runs. Same shape as RISK-09-01; one startup check in Phase 22 covers both.
- **RISK-05-01** still open (VRAM unmeasured — torch is CPU-only).
- Unchanged: RISK-00-02, -07…-16; RISK-01-01; RISK-02-01…03; RISK-03-01…03; RISK-06-02;
  RISK-07-01; RISK-08-01, -02; RISK-09-01, -02.

## Exit gate

**PASS.**

Gate text: *"PASS when transcript stage runs as an independent child job and legacy caller
remains working or parity-approved migration is documented."*

- **Independent child job** — `test_cong_thoat_TRANSCRIBE_la_job_con_doc_lap` asserts exactly
  one `Job` with `step_id == "transcribe"` and `app_slug == "asv_gpu"`, i.e. it runs on the
  GPU lane rather than inheriting `autosubvideo`'s mis-declared `ffmpeg`. Its output is a
  durable transcript that still validates after being read back from storage, with segment
  ids intact for CONTENT_PROCESS to key on.
- **Legacy caller still works** — `apps/autosubvideo` had no logic changed; the only edit is
  a `BE_MAT_CONG_KHAI` declaration naming what was already public. Its own path is untouched,
  and the parity tests confirm the wrapper passes the engine's result through unmodified.

**Explicitly forbidden and confirmed absent:** no translation, no TTS in this stage.

## Next phase prerequisites

Phase 11 (Content / LTT_LLM adapter):
1. ADR-001 D5 chose **delegation** here, not wrapping: `ltt_llm.chat` declares
   `requires=("api",)` honestly and is a public API tool. RISK-03-01 (does it accept params
   from a caller that is not its own UI?) gets settled or falsified in this phase;
2. segment ids must survive 1:1 — `MVP_CONTRACT.md` §8 makes that the lineage contract, and
   `ban_ghi.kiem` already enforces uniqueness on the input side;
3. token budgets have a single authority, `apps/ltt_llm/ngan_sach.py`; the default must be
   requested by door name (`mac_dinh_cho("job")`). CLAUDE.md records a real bug where a
   generic default silently truncated every long answer at 1 024 tokens;
4. this is the first stage that spends money at a provider — `provider_dispatched` /
   ambiguity handling (I5) becomes live rather than theoretical.
