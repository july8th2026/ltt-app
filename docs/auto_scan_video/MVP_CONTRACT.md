# AUTO SCAN VIDEO — MVP CONTRACT (FROZEN)

- **Profile version:** `auto_scan_mvp_v1`
- **Frozen:** Phase 02, evidence SHA `c31b1ae`, worktree `phien/asv`
- **Authority:** this file overrides any later convenience. Changing it requires an ADR.

> Exit-gate intent: *a developer must be able to implement the MVP without making new
> product decisions inside engine phases.* Anything an engine phase would otherwise have to
> guess is decided here.

---

## 1. What the product is

**Auto Scan Video localizes one video into Vietnamese.**

A user supplies one video they own, in some source language. The product returns the same
video, same length, same picture, with a **Vietnamese voice-over** that follows the original
speech timing, over the original music and sound effects.

It is not an editor. It does not cut, reframe, restyle or shorten. The picture that comes
out is the picture that went in.

### Why that definition and not a wider one
The nine stages in `MVP_PRODUCT_CONTRACT.md` (MEDIA → AUDIO → TRANSCRIPT → CONTENT → VOICE →
TIMING → COMPOSE → RENDER → QC) only form a coherent product under one reading: transcript →
translate → speak → align → recombine. That is dubbing. Every other reading leaves a stage
unexplained — a summarizer needs no TIMING, a subtitler needs no VOICE, a clip-cutter needs
no CONTENT.

**The product owner classified smart-cut / scene-selection / YOLO reframe as
OPTIONAL_POST_MVP (Phase 02 decision).** §4 records that and its consequences.

---

## 2. Accepted input policy

Inherited from what two shipping apps already enforce, not invented.

| Rule | Value | Evidence |
|---|---|---|
| container / MIME | `video/mp4`, `video/quicktime`, `video/x-m4v` | `apps/autosubvideo/routes.py:49` `_VIDEO_TYPES` |
| upload via Cloudflare | ≤ **90 MB** | `routes.py:47` `_LOCAL_VIDEO_MAX`, deliberately under the 100 MB edge limit |
| upload via presigned PUT | ≤ **2 GiB** | `routes.py:48` `_PROJECT_VIDEO_MAX` |
| duration | ≤ **7 200 s (2 h)** | `apps/autosubvideo/routes.py:368` |
| concurrent upload sessions | ≤ 20, ≤ 2 GiB in flight, ≤ 12 created/min | `platform_core/upload_sessions.py:28-30` |
| content sniff | magic-byte signature must match declared type | `upload_sessions.py:125,167` |
| must contain | ≥ 1 video stream **and** ≥ 1 audio stream | new — see below |

**`video/webm` is accepted by `upscalevideo` but is NOT accepted here.** Reason in §3:
MVP's render path is a stream copy into MP4, and VP8/VP9 cannot be copied into MP4. Widening
this later is an ADR, not a convenience edit.

**No audio stream ⇒ reject at submit, not at TRANSCRIBE.** A silent video has nothing to
localize; discovering that after paying for MEDIA_PREPARE is a refund, and refunds are the
expensive way to say no.

---

## 3. Final output contract

| Property | Value | Evidence / reason |
|---|---|---|
| container | MP4, `-movflags +faststart` | `DUNGVIDEO-FULL/engine/assemble.py:207` |
| **video stream** | **bit-exact copy of the source** (`-c:v copy`) | see below |
| audio codec | AAC, **48 000 Hz, 2 ch** | `assemble.py:199-204` |
| audio loudness | **−14 LUFS, true peak −1.5 dBTP** | `Cut_only ver2/nerf_engine/stages/audio.py:54` |
| duration | equal to source within **±0.50 s** | new tolerance, §7 |
| language of speech | Vietnamese | §1 |

### 🔑 The video stream is copied, not re-encoded — and that is a consequence, not a shortcut

Because §4 puts every picture-altering feature out of MVP, **no MVP stage changes a single
pixel.** Re-encoding would therefore spend GPU time and lose quality to produce an image
identical in intent to the input.

Consequences, all of them load-bearing:

1. **RENDER needs no GPU.** It is a mux (`-c:v copy -c:a aac`), so its executor declares
   `requires=("ffmpeg",)`. This materially changes the worker-routing ADR in Phase 03 — MVP
   has **one** GPU stage family (TRANSCRIBE, AUDIO_PREPARE separation, VOICE), not two.
2. **No generational quality loss.** The customer's picture is returned untouched.
3. **Render time becomes roughly I/O-bound**, not length × resolution.

**Fallback, decided here so no engine phase has to decide it:** if the source video codec
cannot be copied into MP4 (anything other than H.264 or HEVC), the run **fails at
MEDIA_PREPARE with a typed, actionable error** — it does not silently transcode. Silent
transcoding would spend a customer's credits on a quality loss they did not ask for.
Combined with the §2 MIME allow-list this is a narrow case, and narrowing it further is
better than guessing.

---

## 4. Feature classification

`REQUIRED` = in `auto_scan_mvp_v1`. `OPTIONAL_POST_MVP` = deliberately deferred, engine may
exist. `OUT_OF_SCOPE` = not this product.

| Feature | Class | Reasoning |
|---|---|---|
| **Source separation (vocals vs rest)** | **REQUIRED** | Load-bearing for the core promise. Without removing the original vocal track, the Vietnamese voice plays *over* the original speaker and the output is unusable. `demucs>=4.0` is already a declared platform dependency (`requirements-server.txt`), and `htdemucs` 4-stem separation already exists at `nerf_engine/stages/audio.py:61`. Note this is *separation*, not "BGM removal" — the thing removed is the **voice**. |
| **SFX / music preservation** | **REQUIRED** | Free once separation exists: it is the `drums+bass+other` stems remixed (`audio.py:95 mix_stems`). Not preserving them would mean shipping a video whose world went silent — a visible defect, not a missing nicety. |
| **Transcription with word timings** | REQUIRED | TIMING_ALIGN cannot exist without them. |
| **Translation / rewrite to Vietnamese** | REQUIRED | The product. |
| **Vietnamese TTS** | REQUIRED | The product. |
| **Timing alignment to original speech** | REQUIRED | Distinguishes dubbing from "an audio file attached to a video". |
| **Subtitles (soft or burned)** | OPTIONAL_POST_MVP | `apps/autosubvideo` **is already a shipped product** that does exactly this. Duplicating it here is scope creep, and burning subtitles would force a full re-encode, destroying §3's copy path. |
| **Smart cut / shortening** | OPTIONAL_POST_MVP | Owner decision. Engines exist (`nerf_engine/stages/{scene_detect,select}.py`, `cutclipshort/editorial`). |
| **Scene selection** | OPTIONAL_POST_MVP | Owner decision. |
| **YOLO reframe / aspect change** | OPTIONAL_POST_MVP | Owner decision. Engine `nerf_engine/stages/yolo_reframe.py`. |
| **Motion / zoom / camera path** | OPTIONAL_POST_MVP | Same family. `stages/motion*.py`, `camera_path.py`. |
| **Transitions** | OUT_OF_SCOPE | A transition joins two shots. MVP never cuts, so there is no join to make. This is not deferred — it is meaningless here. |
| **Upscale** | OUT_OF_SCOPE | `apps/upscalevideo` is a separate `lifecycle="released"` product. Sending a customer through two products is a catalog decision, not a stage. |
| **Music replacement / added SFX** | OUT_OF_SCOPE | `nerf_engine/stages` `overlay_random_sfx` exists; using it would alter authored content the customer did not ask to change. |
| **Source scanning / social download / publishing** | OUT_OF_SCOPE | `FUTURE_SCOPE.md`; a release blocker if implemented (I17). |

> ⚠ **The rule that keeps this frozen:** an engine already existing is never a reason to
> enable a feature (Prompt 02, "Explicitly forbidden"). Four of the deferrals above have
> working code sitting in the repo right now.

---

## 5. Fixed stage list

Public stages the user sees. The user cannot add, remove or reorder them.

| # | Stage | Resource | Internal substages | Durable output |
|---|---|---|---|---|
| 1 | `MEDIA_PREPARE` | ffmpeg | probe → validate policy → extract 16 kHz mono WAV | `source_probe.json`, `audio_full.wav` |
| 2 | `AUDIO_PREPARE` | gpu | demucs 4-stem → remix non-vocal bed → loudnorm | `bed.wav` (music+SFX), `vocals.wav` |
| 3 | `TRANSCRIBE` | gpu | VAD → ASR → normalize → segment | `transcript.json` (segments + word timings) |
| 4 | `CONTENT_PROCESS` | api | chunk → translate → per-segment reassembly | `content.json` (same segment ids, Vietnamese text) |
| 5 | `VOICE_SYNTHESIS` | voice | per-segment TTS | `voice/<segment_id>.wav` + durations |
| 6 | `TIMING_ALIGN` | ffmpeg | fit segments → pause plan → splice voice track | `voice_track.wav`, `timing_plan.json` |
| 7 | `COMPOSE` | cpu | build render manifest (no media touched) | `render_manifest.json` |
| 8 | `RENDER` | ffmpeg | mix `bed + voice_track` → mux with copied video | `final.mp4` |
| 9 | `QC` | ffmpeg | probe + tolerance checks (§7) | `qc_report.json`, verdict |

**AUDIO_PREPARE is a public stage, not a substage of MEDIA_PREPARE.** It is the single most
expensive non-GPU-optional step and the most likely to fail on odd input; hiding it inside
another stage would make the failure unexplainable to the user and, worse, would make
resume restart the separation every time (I9).

**COMPOSE never touches media.** It emits a manifest only. G9 requires composer ≠ renderer,
and the practical payoff is that a failed RENDER re-runs from a validated manifest instead
of recomputing eight stages.

---

## 6. User settings

Minimum viable set. Everything else is server policy.

| Setting | Values | Default | Why exposed |
|---|---|---|---|
| `voice_profile` | one of the user's LTT VOICE profiles, or the platform default | platform default | It is the customer's product identity. |
| `timing_mode` | `fit_original` \| `natural` | `fit_original` | The one genuine trade-off in dubbing — see below. |
| `keep_background` | `on` \| `off` | `on` | Some sources are talking-head only, where the bed is room noise. |
| `background_gain_db` | −12 … 0 | −6 | Vietnamese voice must sit above the bed. |

**Not exposed, deliberately:** model names, `temperature`/`top_k`/`top_p`
(`apps/ltt_voice` keeps these off its public contract because its CUDA-graph cache keys on
them), demucs model, encoder settings, chunk sizes, ASR model. Exposing any of these turns a
product into a control panel and freezes internal choices into a public contract.

### `timing_mode` — the real trade-off

> 🔴 **AMENDED by [`ADR-003`](adr/ADR-003-mo-hinh-thoi-gian.md) (Phase 13).** The original
> definition assumed each segment must fit its *spoken* window. That was wrong: **people do
> not speak continuously**, and the pauses between sentences are unspent time budget.
> Vietnamese is typically longer than the source, so under the old rule overflow would have
> been the **norm** — and the only remaining response would be truncation, i.e. losing
> dialogue on most lines.

**Current model** (ADR-003, evidenced against three community dubbing projects):
- a segment's budget runs **until the next segment starts**, so the pause after a sentence
  belongs to that sentence;
- only **70 %** of a pause may be borrowed, so the dub keeps its rhythm;
- overflow becomes a carried **drift debt**, repaid at every subsequent pause;
- speed-up (≤ **1.15×**) is used **only to repay debt**, never to force a fit;
- drift is hard-capped at the budget of **3** following segments; beyond that a segment is
  dropped and **QC must report it**.

- **`fit_original`** — the model above. **Default.**
- **`natural`** — natural pace, no debt-repayment speed-up.

**Neither mode may extend the video stream.** That constraint comes from D-ASV-03 (the video
is copied, so total duration is fixed) — not from the mode. Excess is truncated at the last
fitting segment boundary and QC records it.

---

## 7. Quality tolerances (QC must test these)

Numbers are inherited where evidence exists and stated as new where it does not.

| ID | Check | Threshold | Source |
|---|---|---|---|
| T1 | final is ffprobe-valid, has 1 video + 1 audio stream | hard | new |
| T2 | final duration vs source | **±0.50 s** (`fit_original`); never longer than source | new |
| T3 | video stream bit-identical to source | stream hash equal | consequence of §3 |
| T4 | integrated loudness | **−14 LUFS ± 1.0** | `audio.py:54` |
| T5 | true peak | **≤ −1.5 dBTP** | `audio.py:54` |
| T6 | every transcript segment has voice audio | 100 %, no gaps | new |
| T7 | per-segment start drift vs its **planned** position | **≤ 0.30 s** | ADR-003 amended: drift vs the *source* position is now by design, and is measured by T11 instead |
| T8 | inserted pause length | **120 ms … 2 500 ms** | `Bot_PausePipeline/engine/insertion_planner.py:11-13` **code defaults** |
| T9 | gap between consecutive pauses | **≥ 0.80 s** | `insertion_planner.py:10` **and** `configs/bot_config_pause.json:70` — the two agree |
| T10 | anchor match confidence | **≥ 0.65** | `configs/bot_config_pause.json:67` |
| T11 | accumulated drift | **≤ the budget of 3 following segments** | ADR-003 D5 — new; no reference project caps this |
| T12 | every segment dropped for exceeding T11 | **reported by QC** | ADR-003 — losing dialogue is a quality defect, not a technical detail |

> 🔴 **T8 resolves a real disagreement, it does not inherit one.** The legacy code defaults
> are `min_pause_ms=120 / max_pause_ms=2500`; the shipped config is `50 / 15000`
> (`configs/bot_config_pause.json:68-69`). Both are "the legacy value". **MVP freezes the
> code defaults**, because a 15-second inserted pause is not a pause — it is a hang, and it
> would pass a QC gate that inherited the config number. `min_gap_s` and `fuzzy_threshold`
> are consistent across both sources and are inherited as-is.

---

## 8. Traceability: user goal → stage → output → acceptance test

| User goal | Stage(s) | Output | Acceptance test |
|---|---|---|---|
| "my file is accepted or I'm told why" | submit + MEDIA_PREPARE | `source_probe.json` | policy §2 enforced at submit; unsupported codec ⇒ typed error, no credit spent past probe |
| "the original music is still there" | AUDIO_PREPARE | `bed.wav` | T4, T5; bed is non-silent when source has non-vocal content |
| "every word is captured" | TRANSCRIBE | `transcript.json` | segment count > 0; word timings monotonic; covers ≥ 95 % of voiced duration |
| "it's in Vietnamese and it makes sense" | CONTENT_PROCESS | `content.json` | segment ids preserved 1:1 from transcript (I8 lineage); no empty translation |
| "it sounds like my chosen voice" | VOICE_SYNTHESIS | `voice/*.wav` | T6; each file non-silent and duration > 0 |
| "the voice lands where the speaker spoke" | TIMING_ALIGN | `voice_track.wav` | T7, T8, T9, T10 |
| "the video is unchanged" | COMPOSE + RENDER | `render_manifest.json`, `final.mp4` | **T3** |
| "the length is right" | RENDER | `final.mp4` | T2 |
| "I get told if it's bad" | QC | `qc_report.json` | QC can return FAIL and block delivery (G9) |
| "I can retry without paying twice" | all | checkpoints | stage fingerprint reuse (I10); one billing owner (I3) |

---

## 9. Explicitly frozen — what an engine phase may NOT decide

1. Adding any feature from §4 that is not `REQUIRED`, on the grounds that its engine exists.
2. Re-encoding the video stream for any reason other than the §3 codec fallback.
3. Widening §2's input policy.
4. Exposing any setting beyond §6.
5. Changing a §7 threshold. QC thresholds move by ADR, never by "the test was failing".
6. Introducing a stage, or hiding a §5 public stage inside another.
