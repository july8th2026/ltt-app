# PHASE 19 REPORT — Legacy Decoupling and Parity Audit

**An audit phase that found one undocumented divergence and no legacy coupling.**

## Entry evidence
- starting SHA: `b9a8a67`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 18 closed, all ratchets green
- allowed change scope: tests/docs, plus only small fixes to remove accidental legacy coupling.
  **No fixes were needed** — nothing to remove.

## Tracing the call graph, not reading files (items 1–2)

The question is *"does any path from submit reach Sheet polling, Drive-as-a-queue, a bot worker
loop, a bot-local state machine, or a legacy GPU lock?"* Reading files cannot answer it: a legacy
dependency never sits on line one, it sits three imports deep, and it arrives because somebody
called one convenient function.

`test_421` computes the **import closure** from the five real entry points —
`auto_scan_video.jobs`, `auto_scan_video.thi_hanh`, and the three shells' `jobs.py` — and asks
whether that closure intersects a forbidden list. It walks function-body imports too
(`ast.walk`, not `tree.body`), because this repo uses import-inside-function everywhere to avoid
pulling heavy modules at load time — reading only file headers would miss exactly the places
most likely to hide something.

Result: **no path reaches any of them.** Nothing to fix.

⭐ The most important test in that file is `test_do_thi_goi_KHONG_RONG`. If the traversal broke —
a renamed module, a path bug — every other check would pass **vacuously**. It asserts the closure
has >60 nodes and contains four modules known to be on the path. A guard that cannot fail is the
failure mode this whole build has hit five times; here it is pinned before the conclusions are
trusted.

**Stated limits rather than implied completeness.** Import-closure does not see: dynamic
`import_module(variable)`, subprocesses, or a third-party package importing something legacy. The
first two are pinned separately (`test_khong_import_DONG_theo_ten_tinh_luc_chay`, and the
subprocess rules below). The third is out of reach and is recorded here rather than papered over.

### Subprocesses: the real boundary is tool vs orchestrator

We call ffmpeg constantly, so "no subprocesses" would be a false rule. The distinction that
matters: **ffmpeg takes arguments and returns an exit code.** It holds no state, queues nothing,
and decides nothing about what runs next. A bot worker loop does all three.

`TIEN_TRINH_CON_CHO_PHEP` pins the allowed set (`ffmpeg_bin`, `ffprobe_bin`, `sys.executable`),
and `shell=True` is now checked across **every** module in the app, not just `ket_xuat` as in
Phase 15.

## Compatibility wrappers (item 5), and a rule that was too crude

The three cross-app edges (`ltt_llm`, `autosubvideo`, `ltt_voice`) must remain until RISK-14-01
is paid down. `test_421` pins that they wrap **engines**, not orchestration.

⚠️ My first version of that rule failed, and it was the rule that was wrong. It forbade `.tables`
anywhere in the transitive closure — and the closure legitimately reaches
`ltt_voice.tables.VoiceProfile`, because `ltt_voice.features.giai_giong` (the function we
deliberately call) reads its own tables. The rule forbade a service from doing its own job.

The real invariant needed splitting in two, and the distinction is worth stating because both
cases look identical to a dependency scan:

- **Transitively** reaching another app's tables through its service function is correct.
- **Directly importing** those tables into Auto Scan and querying them ourselves would bypass
  `giai_giong` — the single place a `voice_id` is checked against its owner (I6/I7). That is not
  a style problem; it is the door to using someone else's cloned voice.

⇒ Told apart by **who imports**, not by **what is touched**. Both are now pinned, and Auto Scan
imports no other app's tables directly.

## Parity: comparing decisions, not bytes (item 3)

Byte-comparing output against the legacy implementations is not possible, and the reason is worth
recording: **the legacy code cannot run here.** `mix_stems` wants a demucs stem directory,
`replace_audio` wants a video that already went through xfade concat; both sit inside pipelines
with their own state. Building a harness to run them means rewriting them — at which point we
would be comparing our code to our code.

`test_422` pins the **decisions** instead: what the legacy chose, what we kept or changed, and
why. Six intentional divergences are now recorded as executable assertions rather than prose, so
changing a constant forces someone to write down a reason.

| # | divergence | why |
|---|---|---|
| 1 | no per-stem `volume` gain | legacy is doing a creative remix; we promise to *preserve* the author's balance between instruments |
| 2 | `loudnorm` folded into the same ffmpeg pass | one fewer decode/encode cycle and one fewer temp file that can become litter |
| 3 | multi-layer timed mix (`adelay`+`amix`) | **no legacy version does this** — no reference to compare against |
| 4 | `loudnorm` on the final mix | came from a **measurement**, not a design choice — see below |
| 5 | drift cap of 3 segments | ours; Subdub accumulates without limit, which is unbounded when the video is dense |
| 6 | bed stays at 44.1 kHz | **found by this test** — see below |

### The divergence nobody had written down

`test_422` was written asserting `TAN_SO_TACH == 48000`, following `audio.py:113`. **It failed:
we use 44 100.**

The reason was already in the code (`tach_tieng.py:58` — htdemucs is trained at 44.1 kHz), so
this is not a bug and not even a mistake. But it had existed since Phase 09 and appeared in no
comparison table. Legacy resamples before/at separation; we keep the model's native rate and
resample **once**, at RENDER, after the model has done its work.

⚠️ Why record something harmless: an undocumented divergence is one a later session "fixes" —
somebody reads `audio.py`, sees 48000, and assumes we copied it wrong.

### Divergence 4 has a different status from the rest

It did not come from a design preference. Phase 18's QC gate **measured** −12.58 LUFS against a
−14 ± 1 target and forced the change. The legacy never hit it because `replace_audio` *replaces*
the audio; we *add* voice on top of an already-normalised bed.

## Legacy bots still run (item 4)

`taoclipngan` — the app that vendors `cutclipshort` — passes: `test_84`, `test_122`, `test_123`,
**18 tests green**. `autosubvideo` passes (`test_103`). `upscalevideo` fails only on
`test_vendor_engine_co_mat`, the worktree-structural failure of RISK-14-02 (`git ls-files
apps/upscalevideo/vendor` is empty — the binaries were never committed), unrelated to Auto Scan.

## Dead migration code (item 6)

None found to record. `cutclipshort/core/job_queue.py` (RISK-00-15) is **not dead** — it is live
code owned by `taoclipngan`. Auto Scan simply never reaches it, which `test_421` now enforces.
Nothing deleted, per the prompt's explicit prohibition.

## Exit evidence

ASV-owned tests: **410 pass**, including under `-n 8`.

Ratchets: `lint_app_contract` PASS · `check_silent_except` 63/63 · `check_bo_qua` PASS ·
`check_dich_thieu` 343/343.

Externally-owned failures unchanged (peer's `dieu_khoan.py` layering + i18n, peer's
`voice_tu_dien`, and the three worktree-structural ones now owned by `lttstudiosapp-81`).

## Debt carried out of this phase

- **RISK-14-01 unchanged.** The three cross-app edges are proven to be engine-only, which is the
  best that can be said while they exist. Lifting the shared helpers into `platform_core` is
  still the exit, and still touches three apps serving paying customers.
- **Third-party transitive imports are unaudited** — stated as a limit of the method above.
