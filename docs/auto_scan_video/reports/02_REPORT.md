# PHASE 02 REPORT — MVP Product Contract Freeze

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- pre-existing dirty: none in this worktree (Phase 00/01 docs untracked, mine)
- previous gate: Phase 01 **PASS** (certified baseline `FAIL (4/26)`, all four attributed)
- allowed change scope: **docs only**

## Trace performed

Input policy: `apps/autosubvideo/routes.py:47-49,368` · `apps/upscalevideo/routes.py:32-34` ·
`platform_core/upload_sessions.py:28-30,125,167`.
Output profile: `DUNGVIDEO-FULL/engine/assemble.py:160-210` (`_video_encode_args`,
`_audio_encode_args`, `_common_mov_args`).
Audio: `Cut_only ver2/nerf_engine/stages/audio.py:48-116,173` (`extract_audio`, `loudnorm`,
`demucs_separate`, `mix_stems`, `prepare_segment_audio`).
Timing tolerances: `Bot_PausePipeline/engine/insertion_planner.py:8-45` ·
`Bot_PausePipeline/engine/anchor_matcher.py` · `Bot_PausePipeline/configs/bot_config_pause.json:58-70`.
Voice/LLM public contracts: `apps/ltt_voice/tham_so_cong_khai.py:59` ·
`apps/ltt_voice/du_an.py:225-251` · `apps/ltt_llm/ngan_sach.py`.
Deferred-feature engines (to confirm they exist and are still deferred):
`nerf_engine/stages/{scene_detect,select,yolo_reframe,motion,motion_zoom,camera_path}.py`,
`cutclipshort/{analysis,editorial}`.

## Decisions

**D-ASV-01 — the product is Vietnamese video localization (dubbing).**
Derived, not assumed: the nine mandated stages only cohere under transcript → translate →
speak → align → recombine. Every competing reading orphans a stage (a subtitler needs no
VOICE; a clip-cutter needs no CONTENT; a summarizer needs no TIMING).

**D-ASV-02 — visual editing is OPTIONAL_POST_MVP** (product owner, this phase). Smart cut,
scene selection, YOLO reframe, motion/zoom.

**D-ASV-03 — MVP copies the video stream instead of re-encoding it.**
The most consequential decision in this phase, and it *follows* from D-ASV-02 rather than
being a preference: with every picture-altering feature deferred, no MVP stage changes a
pixel, so re-encoding would burn GPU time and lose quality to reproduce the same image.
Three consequences that reach into later phases:
- **RENDER no longer needs a GPU** — it is `-c:v copy -c:a aac`, i.e. `requires=("ffmpeg",)`.
  MVP has one GPU family (AUDIO_PREPARE, TRANSCRIBE, VOICE), not two. This changes the input
  to the Phase 03 routing ADR (RISK-00-01) and makes the hidden-executor split cleaner.
- No generational quality loss.
- `video/webm` is excluded from the input policy, because VP8/VP9 cannot be copied into MP4.
  `upscalevideo` accepts webm; Auto Scan deliberately does not.

**D-ASV-04 — source separation is REQUIRED, and it is voice removal, not "BGM removal".**
Without stripping the original vocal, the Vietnamese track plays over the source speaker and
the output is unusable — this is load-bearing for the core promise, not polish. Cheap to
adopt: `demucs>=4.0` is already a declared platform dependency and `htdemucs` 4-stem
separation already exists at `nerf_engine/stages/audio.py:61`. SFX/music preservation then
costs nothing extra — it is the same call's remaining stems.

**D-ASV-05 — T8 resolves a contradiction in the legacy source rather than inheriting it.**
Pause bounds are `120 / 2500 ms` in code defaults but `50 / 15000 ms` in the shipped config.
Both are "the legacy value". MVP freezes the **code defaults**: a 15-second inserted pause is
not a pause, it is a hang, and a QC gate that inherited the config number would pass it.
`min_gap_s = 0.8` and `fuzzy_threshold = 0.65` agree across both sources and are inherited.

**D-ASV-06 — `timing_mode` is the single exposed trade-off**, with `fit_original` default.
`natural` may never extend the video stream (that would silently break D-ASV-03); excess is
truncated at the last fitting segment boundary and QC warns.

**D-ASV-07 — subtitles are OPTIONAL_POST_MVP, not REQUIRED**, despite being the most obvious
adjacent feature: `apps/autosubvideo` already ships exactly that product, and burning
subtitles would force a full re-encode and destroy D-ASV-03.

**D-ASV-08 — no audio stream ⇒ reject at submit**, not at TRANSCRIBE. Discovering it later
means a refund, and refunds are the expensive way to say no.

## Changes

| Path | Change | Why | In scope? |
|---|---|---|---|
| `docs/auto_scan_video/MVP_CONTRACT.md` | new | the frozen contract, `auto_scan_mvp_v1` | yes |
| `docs/auto_scan_video/reports/02_REPORT.md` | new | mandatory closeout | yes |
| `docs/auto_scan_video/STATE.md` | updated | frozen MVP section, phase history | yes |

No production source, test, migration or manifest touched.

## Tests

| Command | Result | Evidence |
|---|---|---|
| `python tools/scan_source_secrets.py` | `Findings: 0 — RESULT: PASS` | docs-only phase; confirms no hex/secret pattern in the new contract |

Full-gate regression was **not** re-run: this phase changed only markdown under
`docs/auto_scan_video/`, which no gate step reads, and the Phase 01 baseline
(`FAIL (4/26)`) is < 1 h old at the same SHA. Re-running would cost 5 minutes to reproduce a
number that cannot have moved. The next code-touching phase (04) re-runs it.

## Invariant regression
Not applicable — no invariant tests exist yet (Phase 04 creates them). The contract does
however *pre-commit* to several: I8 lineage (segment ids preserved 1:1 through CONTENT),
I9 resume (AUDIO_PREPARE kept public so resume does not redo separation), I17 fixed product
model (§9 freezes what engine phases may not decide).

## Diff review
- changed paths: `docs/auto_scan_video/` only
- no generated artifacts, no media, no binaries
- secret scan clean

## Risks / external evidence pending

New:
- **RISK-02-01 (P1)** — `fit_original` assumes Vietnamese speech can be fitted into source
  segment windows often enough to be usable. Vietnamese is typically *longer* than English
  for the same content. If real measurement shows frequent overflow, `fit_original` degrades
  into constant truncation. **Closes in Phase 13** with a measured overflow rate on real
  material; if it is bad, the answer is a rate/compression policy, not a silent default flip.
- **RISK-02-02 (P2)** — D-ASV-03's copy path assumes source video codecs are overwhelmingly
  H.264/HEVC in MP4/MOV. Not yet measured against real customer files. Closes in Phase 08.
- **RISK-02-03 (P2)** — T7 (0.30 s start drift) and T2 (±0.50 s duration) are **new numbers
  with no legacy evidence behind them**. They are stated as new in the contract rather than
  dressed up as inherited. Phase 18 must confirm they are both achievable and meaningful.

Updated: **RISK-00-01** (worker routing) is materially reduced by D-ASV-03 — MVP now needs
`api`, `ffmpeg`, `gpu` and `voice` lanes, but RENDER moves off GPU, so the heaviest and
longest stage no longer competes for a card.

## Exit gate

**PASS.**

Gate text: *"PASS only when a developer can implement the MVP without making new product
decisions inside engine phases."*

Tested by walking each engine phase (08–15) and asking what product question it would
otherwise have to invent an answer to:

| Phase | Question it would have faced | Where the contract answers it |
|---|---|---|
| 08 Media | which containers/codecs? what if uncopyable? | §2, §3 fallback |
| 09 Audio | separate or duck? which stems? how loud? | §4 D-ASV-04, §7 T4/T5 |
| 10 Transcript | word timings needed? coverage bar? | §5, §8 |
| 11 Content | chunking unit? segment identity? | §5 (segment ids 1:1), §8 |
| 12 Voice | which knobs are public? | §6 "not exposed, deliberately" |
| 13 Timing | fit or natural? pause bounds? may it extend? | §6 D-ASV-06, §7 T8/T9 |
| 14 Composer | does it touch media? | §5 "COMPOSE never touches media" |
| 15 Renderer | copy or transcode? output profile? | §3, D-ASV-03 |
| 18 QC | what blocks delivery? | §7 T1–T10 |

No phase is left holding a product decision. §9 additionally names six things an engine
phase may **not** decide, which is the half that actually prevents drift — four of the
deferred features have working engines sitting in this repo right now, and "the code already
exists" is exactly the pressure Prompt 02 forbids yielding to.

## Next phase prerequisites

Phase 03 (Execution/Billing/Resource ADR) may start. It inherits three inputs from here:
1. **Resource shape is now known**: GPU for AUDIO_PREPARE + TRANSCRIBE, `voice` for
   VOICE_SYNTHESIS, `api` for CONTENT, `ffmpeg` for MEDIA/TIMING/RENDER/QC, cpu for COMPOSE.
   That is four capability classes across nine stages — the concrete case RISK-00-01 must
   solve.
2. **Nine stages, one run** — the billing owner question is now precisely "one hold across
   nine child jobs", with the `agent/budget.py` precedent already traced in Phase 00.
3. **Metered cost is real**: TTS characters, LLM tokens and demucs GPU seconds all vary per
   run, so RISK-00-05 (settlement recomputing instead of measuring) is a live blocker, not a
   theoretical one.
