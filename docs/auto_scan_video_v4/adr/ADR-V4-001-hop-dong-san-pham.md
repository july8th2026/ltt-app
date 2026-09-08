# ADR-V4-001 — Auto Scan Video is a Vietnamese smart-localization editor

- **Status:** ACCEPTED (Phase 01, V4)
- **Date:** 2026-09-03
- **Evidence SHA:** `706faca50c75fb5b6dbad6c346b96c98a6736a11`, branch `phien/asv-v4`
- **Supersedes:** `docs/auto_scan_video/MVP_CONTRACT.md` §1 and §4 — profile `auto_scan_mvp_v1`
- **Superseded by:** —
- **Machine-readable form:** `apps/auto_scan_video/hop_dong_v4.py`
- **Tests:** `tests/test_425_asv_v4_hop_dong_san_pham.py`

---

## Context

`auto_scan_mvp_v1` was frozen in V2 Phase 02 and says, in its own words:

> "It is not an editor. It does not cut, reframe, restyle or shorten. The picture that comes
> out is the picture that went in."

That freeze was correct for what it described. It was reached because
`MVP_PRODUCT_CONTRACT.md` explicitly deferred the smart-cut / scene-selection call to the
product owner, and the owner classified them `OPTIONAL_POST_MVP` at the time. V2's own
`STATE.md` records the deferral as *"a real scope fork, not a formality"* and stopped Phase 21
awaiting exactly this decision.

The V4 pack carries the owner's answer: the product is a **smart-localization editor** with
two presets, one of which may remove scenes.

## Decision

### D-V4-01 — The product is a Vietnamese smart-localization editor with two presets

Auto Scan Video takes one owner-scoped video, understands its scenes, optionally removes
low-value ones, replaces the source dialogue with Vietnamese speech, preserves background and
SFX as far as practical, and validates the result.

| Preset | Picture | Editing allowed |
|---|---|---|
| `localize_preserve_picture` | never altered; stream-copy where the container/codec permits | **none** — cannot cut, cannot reorder |
| `smart_localize` | re-encoded only at cut points | **keep / cut only**, original order |

`localize_preserve_picture` **is** `auto_scan_mvp_v1`'s behaviour. V4 does not deprecate it,
does not "migrate" it, and does not make it a special case of the smart path. It keeps its own
name because it keeps its own promise, and because V2 paid for that path with nine closed
phases of evidence.

**Why `THAO_TAC_CHO_PHEP[PRESET_GIU_HINH]` is an empty tuple and not an absent key.** A
missing key reads as "not implemented yet". An empty tuple reads as "forbidden". G10 requires
the second meaning, and only the second one is testable.

### D-V4-02 — Target language is `vi`, and the *reason* matters more than the value

Target language for V4 MVP is Vietnamese. Source language is auto-detected or hinted.

🔴 **The reason given in `V4_MVP_PRODUCT_CONTRACT.md` is factually wrong and is corrected
here.** The pack says target is Vietnamese *"because the shipped LTT Voice capability is
Vietnamese."* It is not:

```
apps/ltt_voice/lan_ngon_ngu.py:6   VieNeu-TTS v3 Turbo **song ngu that**,
                                   model card khai `language: ["vi", "en"]`
apps/ltt_voice/lan_ngon_ngu.py:91  NHAN_LAN = {"vi": ..., "en": ...}
```

The decision stands; the justification is replaced. The real reason is that V4's entire
understand-and-adapt chain — `ContentProfile`, `EditPlan`, `DubbingAdaptation`, `DubbingFit`
and three semantic QC layers — has evidence for exactly one target language. Adding `en` is
adding a body of evidence, not a config entry.

This distinction is load-bearing, not pedantry. A future session that inherits the wrong
reason will open `lan_ngon_ngu.py`, see `["vi", "en"]`, conclude the restriction was a
misunderstanding, and widen it. The reason is recorded in the code
(`hop_dong_v4.NGON_NGU_DICH`) precisely where that session will be standing.

### D-V4-03 — `smart_localize` may only keep or cut

Scenes may be kept or removed. They may **not** be reordered, reframed, cropped, zoomed,
re-timed for effect, or joined with transitions, and no B-roll may be generated.

`reorder` is listed in `CAM_TRONG_MVP` rather than merely being absent from the allowed set.
Absence and prohibition look identical to a reader and to a linter; only one of them survives
a later session that "adds the missing operation".

Every cut must be traceable to deterministic policy plus scene evidence. Dialogue-bearing and
story-critical scenes require stronger evidence before removal. Minimum/maximum retained
duration is configurable and versioned. Those rules are Phase 12's to implement; this ADR
fixes only that they must exist and that nothing beyond keep/cut may appear.

### D-V4-04 — Two voice modes, and `AUTO_MATCH` is not "the default voice"

- `USER_SELECTED` — the customer picks a sample voice or one they own.
- `AUTO_MATCH` — the system binds a voice from the LTT Voice catalog to the speaker
  characteristics found in the source.

⚠️ V2 exposed `giong_id: str = Form("")` (`routes.py:135`), where empty meant "platform
default". That is **not** `AUTO_MATCH`: a default value reads nothing from the video.
Conflating the two would let Phase 09 ship a stub that passes a naming check while binding
nothing.

`VoiceBinding` is resolved **before** final dubbing adaptation, because speaking rate and
style change how long a line takes to say, and length is what the fit loop is fighting over.

### D-V4-05 — Output and failure behaviour the customer sees

- Container MP4, `+faststart`, AAC 48 kHz stereo, −14 LUFS ± 1.0, true peak ≤ −1.5 dBTP
  (inherited unchanged from `MVP_CONTRACT.md` §3/§7).
- `localize_preserve_picture`: output duration equals source within **±0.50 s**.
- `smart_localize`: output duration is **shorter than or equal to** source.
- **No preset may make the video longer.** A customer submits a video, not a slot to fill.
- A run that fails, fails whole. There is no partial delivery.
- QC can block delivery (`GIAO_KHI_QC_HONG = False`). A gate that cannot block is not a gate —
  V2 Phase 18 shipped exactly that bug and caught it in its own report.

### D-V4-06 — Post-MVP is a list, not a feeling

`HAU_MVP` names them: reframe/YOLO, zoom/motion, burned subtitles, upscale, generative B-roll,
per-speaker multi-voice, multilingual targets, social ingest and publish.

The V2 rule that keeps this honest is retained verbatim: **an engine already existing is never
a reason to enable a feature.** Four of these have working code in the repo right now.

## Consequences

1. **The render path forks.** `MVP_CONTRACT.md` §3 derived "video stream is copied" from "no
   MVP stage changes a pixel". Under `smart_localize` that premise is false at cut points, so
   D-ASV-03 becomes **preset-conditional**: copy under `localize_preserve_picture`, re-encode
   under `smart_localize`. That in turn puts `render` back on the GPU-encoder question for one
   preset only — `platform_core.media.detect_gpu_encoder()` exists and is Phase 17's problem.
2. **The pipeline order changes, and this is the expensive consequence.** Today
   `pipeline.CHUOI` pays for LLM translation at position 4 with no `EDIT_PLAN` and no
   `VOICE_BIND` in existence. V4 requires the cut list frozen before translation (so removed
   scenes cost nothing) and the voice bound before final adaptation. This is a re-ordering of
   the chain, not a stage bolted onto the end.
3. **`asv_media` may need the `gpu` lane for one preset.** Its manifest currently declares
   `requires=("ffmpeg",)` and its docstring explains at length why RENDER avoids the card.
   That reasoning was sound under a copy-only contract and is now half true. Phase 17 owns the
   resolution; recorded here so it is not discovered as a mysterious `queued` job.
4. **`auto_scan_mvp_v1` is not deleted.** `docs/auto_scan_video/MVP_CONTRACT.md` keeps every
   word it had; a supersession banner is added at its top pointing here. Sections 2, 3, 5, 6,
   7 and 8 of that document remain in force — input policy, output format, QC tolerances T1–T12
   and the ADR-003 timing model are all inherited unchanged.

## What this ADR does NOT decide

- How scenes are detected, sampled, or scored (Phases 10–12).
- The keep/cut policy thresholds themselves (Phase 12).
- How `AUTO_MATCH` measures a speaker (Phase 09).
- Whether `asv_media` gains the `gpu` lane or a fifth executor app appears (Phase 17).
- Anything about `AsvWorkItem` or per-segment durability (Phases 03/05).

## Rejected alternatives

| Option | Why not |
|---|---|
| Make `smart_localize` the only preset and treat preserve as `cuts = []` | Collapses two different *promises* into one code path. "I never touch your picture" is a guarantee a customer can be told; "the cut list happened to come back empty" is not. It would also silently put every preserve run through the re-encode branch's risk surface. |
| Keep `auto_scan_mvp_v1` and add smart-cut as a "mode" inside it | The frozen text says "it is not an editor". Adding an editor to a document that denies being one is exactly the silent rewrite `start_here.md` §5 forbids. |
| Widen target language to `vi` + `en` now, since LTT Voice supports both | The TTS supports it. Nothing else in the chain has been measured for it. See D-V4-02. |
| Leave the pack's incorrect justification for `vi` in place, since the value is right | A wrong reason is a live invitation to reverse the decision. See D-V4-02. |
