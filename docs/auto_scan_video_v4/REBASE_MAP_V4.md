# V4 REBASE MAP — every current ASV module, classified

Evidence SHA `d7f5a73` (Phase 02 commit), tree `phien/asv-v4`.
33 modules, ~7 100 lines across `apps/auto_scan_video` + three executor apps.

Decision vocabulary: **KEEP** (untouched) · **EXTEND** (additive, all callers survive) ·
**REFACTOR** (behaviour changes) · **ADD** (new file) · **REMOVE**.

> The default is KEEP. `V4_OPERATING_CONTRACT` A.1: *"Do not rebuild `AsvRun`, `AsvStage`,
> owner isolation, credit hold, asset lineage, fingerprinting, retry/invalidation,
> cancellation or durable promotion unless a failing test proves a defect."* No failing test
> proves any such defect. The V4 change is **shape**, not **soundness**.

## Verdict count

**17 KEEP · 6 EXTEND · 7 REFACTOR · 15 ADD · 0 REMOVE.**
>
> ⚠️ `su_dung.py` (ADD, phase 06) was appended after the phase-03 census. The count moved 8 → 9 (and → 10 with `ai.py`, phase 08); `test_427` is what forced the update — a module missing from this map is a module whose fate nobody decided.

Nothing is removed. That is not caution — V2 closed 20 phases of evidence against these
modules, and the parts V4 changes are the parts whose *premises* changed (one preset became
two; translation moved after planning), not the parts that were wrong.

## The existing 33

| Module | ln | Responsibility | Decision | Why / what changes | Phase |
|---|---:|---|---|---|---|
| `__init__.py` | 30 | app marker | KEEP | | |
| `manifest.py` | 117 | declaration | **EXTEND** | `enabled=True` at release; `max_runtime_s` for new job types | 17, 21 |
| `pipeline.py` | 203 | **the fixed chain** | **REFACTOR** | 9 stages → ~15; must become preset-aware. The `_kiem_tra_chuoi()` import-time topology check and `ha_nguon_cua()` closure logic are **kept verbatim** — they are the load-bearing parts | 05, 12 |
| `tables.py` | 261 | `AsvRun`/`AsvStage`/`AsvAsset` | **EXTEND** | **+ `AsvWorkItem`** (ADR-V4-002). Existing three untouched | 05 |
| `features.py` | 486 | run lifecycle, money, ownership | **EXTEND** | `preset` + `voice_mode` in settings; item-aware `tong_da_dung`. Hold/settle/cancel logic **kept** | 05, 06 |
| `su_dung.py` | 340 | delivered-usage ledger + budget gate | **ADD** | `AsvUsage` (`asv_usage`): one row per capability call — capability, owning app, dispatch state, unit, quantity, **measured** credit, dispatch id. ⛔ **Not a second money path**: money still flows through exactly one column (`AsvWorkItem.credit_actual`); this table *explains* that number and `doi_soat` pins `item.credit_actual == Σ delivered rows`, called from `quyet_toan` **before** the charge. Also owns the ambiguous-dispatch rule (ADR-001 D9): `thu_lai_giai_doan` refuses while an unresolved `mo_ho` row exists, and an AST test pins that **no automatic path** calls `giai_quyet_mo_ho` | 06 |
| `ai.py` | 300 | one door for every LLM/VLM call | **ADD** | Five typed operations (scene understanding, content profile, dubbing adaptation, shorten-for-fit, semantic QC) plus translation, all through `platform_core.llm.dieu_phoi`. Model choice is **semantic** — the operation declares `can_thi_giac`, and `model_cho` asks `providers.model_capabilities` rather than naming an internal id. 🔴 Closing this surfaced a **live bug**: `dich_thuat.py:45` had `{"ltt_llm": "ltt_llm"}` — the exact pattern `dieu_phoi.goi`'s own docstring warns about, which makes `chon_key` raise and the dispatcher **silently skip the only provider**. Two earlier victims were already named there; ASV was the third, unnoticed because the stage is still a fake engine. Owns prompt/schema version for fingerprints, structured-output validation, and the ambiguous-dispatch translation | 08 |
| `rang_giong.py` | 230 | VoiceBinding: which voice, on what evidence | **ADD** | ASV owns the *policy*; LTT Voice owns the voice, ownership, synthesis, GPU and normalization — this file synthesizes **zero milliseconds** of audio, pinned by AST. 🔑 `AUTO_MATCH` with no ContentProfile yet resolves to **`CHUA_RANG`**, a valid state that is neither a failure nor a voice, and `ma_giong()` **raises** on it: `ADR-V4-001` D-V4-04 forbids AUTO_MATCH degrading into "use the default", which is exactly what V2 did (`routes.py:135` `giong_id: str = Form("")`). Deferring rather than picking a placeholder is deliberate — Phase 14 sizes sentences against the real voice's reading speed, so a temporary voice produces an adaptation that must be redone | 09 |
| `canh.py` | 300 | deterministic scene index + bounded frame sampling | **ADD** | `ffmpeg`'s `select='gt(scene,T)'` reports boundary timestamps; **no pixel enters Python** — a 40-minute video is ~60 000 frames, ~350 GB raw, and an AST test pins the absence of `cv2`/`PIL`/`numpy`/`av`. One ffmpeg call for the whole video, `-f null -` so nothing is written. Frame count is capped **where frames are produced**, not where they are consumed: the vision context window measures 65 536 tokens (half the text model), so a cap placed after the spend is a cap in the wrong place. 🔴 The even-distribution test caught a real bug in my first draft — it gave one frame to each of the first 60 scenes and **nothing to the last 40**, i.e. exactly the tail-truncation its own docstring forbade | 10 |
| `hieu_canh.py` | 330 | SceneUnderstanding + ContentProfile | **ADD** | Two calls, not one: reading a scene is a **local** question, building a profile is a **global** one — asking both at once means one bad scene ruins the profile and one profile edit re-reads every scene. Strict schema validation, because a malformed response **is not a successful artifact** — and a scene that was *read and returned garbage* differs from one *never read*: the first already cost money and belongs in the ledger. Per-scene fingerprint includes prompt **and** schema version, both this phase's and `ai.py`'s, which move independently | 11 |
| `ban_bien_tap.py` | 280 | EditPlan: the authoritative visual decision | **ADD** | 🔴 Closes **V4-R07 (P0)**: in V2 the paid translation stage ran at position 4 with no edit plan in existence — translating, and paying for, dialogue belonging to scenes that would be cut. Deterministic, source-ordered, versioned. `localize_preserve_picture` never cuts and never even reads the VLM's opinion. Scenes **with dialogue** need a higher removal confidence (0.85 vs 0.65): a silent scene cut by mistake loses a shot, a dialogue scene cut by mistake **breaks the story** — the viewer hears an answer to a question that no longer exists | 12 |
| `giai_doan_ban_bien_tap.py` | 150 | the `edit_plan` stage | **ADD** | Inserted into `pipeline.CHUOI` **before** `content_process`, so every paid stage is downstream of the visual decision. Changing the plan invalidates dubbing/timing/render/QC and **not** ASR or source separation — re-running a paid transcription because of a picture decision would be the same class of waste V4-R07 describes | 12 |
| `long_tieng.py` | 300 | DubbingDocument: Vietnamese lines for the retained segments only | **ADD** | Not a translation: each line carries the source **duration**, the neighbouring **retained** lines (after the cut, the line before a line may be three minutes away in the source), and the target voice's traits. 🔑 Results are keyed by **segment id, never by position** — a batch of 12 that comes back with 11 would silently shift every later line onto the wrong segment, and the document would still be well-formed. Closed vocabularies for `cam_xuc`/`kieu_noi`, because a free-text mood field returns four spellings of the same thing and downstream can use none of them. The chosen voice is **frozen into the document** and into its fingerprint | 14 |
| `nan_cho_vua.py` | 230 | fitting policy: make one line fit its slot | **ADD** | A four-rung ladder whose **order is the policy**: synthesize and measure on the real file → ask the model to rewrite *that one line* → allow light time-stretch within the declared cap → mark repair-needed. ⛔ Rung 3 must not come before rung 2: stretching audio distorts the voice, rewriting a sentence does not — fix the **content** before the **signal**. Tolerance is deliberately **asymmetric** (long overruns the next shot; short leaves a gap `thoi_gian.py` already knows how to absorb), and the rewrite prompt carries the **measured** duration, not just the target — \"this reads as 4.8s, the slot is 3.2s\" is a checkable goal, which is why a second round is usually unnecessary | 15 |
| `ban_do_thoi_gian.py` | 190 | source time → output time across the cuts | **ADD** | 🔴 Without it the cutting preset is wrong **silently**: `thoi_gian.py` planned on the **source** axis, so a line at source second 120 was placed at output second 120 — while its real home might be second 74, and the error **accumulates with every cut scene**. ⛔ A timestamp landing *inside* a cut returns `None`, never the nearest edge: snapping turns a line that was **removed** into a line **placed wrong**, trading a visible loss for a hard-to-find bug. `ra_gan_nhat` exists for exactly one caller — the background bed, which is continuous and must have a real timestamp at a join | 16 |
| `am_master.py` | 250 | deterministic FFmpeg mix: bed + fitted voices | **ADD** | No model call anywhere — arithmetic and FFmpeg only. Mixes in **batches** because one `filter_complex` with 400 voice inputs exceeds Windows' 32,767-character command limit, which truncates **silently** and surfaces as an FFmpeg syntax error unrelated to the cause. `amix` not `concat` (segments sit at their own marks, they do not follow one another), always `normalize=0` (the default divides by input count, so adding a voice would quieten the whole bed), and loudness normalised **once at the end** — running `loudnorm` per batch and summing gives a level nobody can predict | 16 |
| `che_do_render.py` | 200 | which render path, and which encoder | **ADD** | 🔴 The cutting preset **cannot** use `-c:v copy`: stream copy can only cut at keyframes, and measured on a file this very chain produces the GOP is **8.333 s** — so a cut point would be dragged up to 8.3 s away from where the audio master was built for. Re-encoding is not an optimisation choice; it is the condition for picture and sound still matching. ⚠️ My first encoder comparison **used the wrong scale** (`cq=23` is not `crf=23`), making NVENC look twice as large for nothing. At matched quality (SSIM ≈ 0.995) NVENC is **1.68× faster and 25% larger** — neither dominates; the deciding axis is that mean host CPU drops **61% → 41%** on a machine whose scarcest resource is CPU. And honestly: both peak at ~91%, because decode and the concat filter stay on the CPU — NVENC offloads the *encode*, not everything | 17 |
| `sua_chua.py` | 300 | RepairPlan: defect → the **earliest stage that can fix it** | **ADD** | 🔴 The dangerous direction is the reverse one: a line the TTS misread must **not** be pushed back to `content_process` — that text is *correct*, and rewriting it pays to swap one correct sentence for another. A mistranslation is the opposite: re-reading it any number of times yields the same wrong meaning. When one segment carries both defects the **earlier** stage wins, because re-reading a mistranslated line still gives a mistranslated line. Repair cycles are capped **tighter than Phase 15's fitting loop** and for a stated reason: that loop corrects a *measured* quantity and converges; this one corrects a model's *subjective* verdict, and looping is paying to watch it change its mind | 19 |
| `qc_ai.py` | 260 | speech / semantic / visual QC through the one door | **ADD** | Speech QC is a **measurement** (two strings, one ratio) and carries confidence 1.0; the other two are model *judgements* and carry the model's own confidence — below threshold they are **recorded but generate no repair**, because an unsure model is not a reason to pay to redo work, nor a reason to hide the observation. Missing confidence defaults to **0**, never 1. The VLM is asked only **at the joins**: an untouched scene has nothing to ask about, and asking across the whole film is paying to hear it confirm that what was not touched is intact | 19 |
| `jobs.py` | 223 | `advance` coordinator | **KEEP** | The five-step tick (lock → reconcile → invalidate → submit → re-enqueue) is exactly what V4 wants. New stages ride it unchanged | |
| `thi_hanh.py` | 347 | shared stage body, fingerprint | **EXTEND** | item-level fingerprint alongside stage-level; `phien_ban_engine` gains entries. Five-step asset protocol **kept** | 05 |
| `assets.py` | 443 | artifact lifecycle, promote | **EXTEND** | streaming checksum (V4-R06); keys/lineage/integrity **kept** | 05, 13 |
| `routes.py` | 290 | customer surface | **REFACTOR** | durable upload replaces `await video.read()`; preset + voice mode; 2 missing settings (V4-R12) | 21 |
| `vung_che.py` | 142 | masked-region geometry (GUI V5) | **ADD** | Normalised 0..1 boxes drawn by the customer on the preview frame. Owns four rules, all learned at another system's expense (`docs/auto_scan_video_v5/VIRAL_RENDER_FEATURE_MAP.md` §3): coordinates are **fractions, never pixels**; malformed input is **rejected, never guessed** (a silently-corrected box masks a region the customer did not draw, and they only find out from the delivered file); regions must enter the `ban_dung` hash or a changed mask serves a stale result. 🔴 The fourth rule — *a box pushed outside the frame by a geometric transform is DROPPED, not clamped* — has **no code here on purpose**: `zoom` sits in `CAM_TRONG_MVP`, so an implementation would have no caller, and `test_453` correctly refuses capability written without a call site. The rule lives in `V5_UI_INFORMATION_ARCHITECTURE.md` §11 until an ADR-V5 opens `zoom` | V5 |
| `tu_dien.py` | 85 | customer pronunciation dictionary (GUI V5) | **ADD** | `apps/ltt_voice/text_pipeline.chuan_hoa` has accepted `tu_dien_rieng` for a long time and `giong_noi` forwards it through four call sites — the capability existed, the **road to the user** did not. That is the fourth instance of the same shape found on 08/09 by four different sessions (`license_status`, `a11y_quet --cookie`, `NHAN_LOC[phong_cach]`, this). Owns four rules: malformed input is **rejected, never guessed**; a name declared twice is a contradiction **of the customer's**, so choosing one is guessing; the dictionary **must enter the per-segment hash** or two different dictionaries share one storage key and the second customer receives the first customer's audio; but it enters **only when present** — `{}` and `None` must hash identically, otherwise every existing fingerprint changes and the whole generated voice store is discarded. 🔑 `_van_tay` takes `tu_dien` as a **required** keyword: forgetting a call site must be a `TypeError`, never a silently wrong hash | V5 |
| `cat_dau_cuoi.py` | 105 | trim window (V6 phase 10) | **ADD** | The customer's start/end window, as a fraction of duration. Reuses `vung_che`'s four rules on a different axis rather than starting a second rule set — **fractions never seconds**, **rejected never guessed** (a reversed window silently re-sorted trims a stretch the customer did not choose), a range fully outside the window is **dropped not clamped**, and `(0.0, 1.0)` is **identical to absent** so a run that trims nothing does not disturb one existing fingerprint. ⭐ Unlike `vung_che` it needs **no new fingerprint field**: it narrows `ban_do.giu`, `khoang_giu` is already in the manifest, and the manifest is already in the hash. 🔴 And its L3 differs from `vung_che`'s in kind, which is the part worth reading: masking **cannot** exist under `-c:v copy` (no frame is ever decoded — physics), while trimming **can** (`-ss`/`-to` cut a copied stream fine) and is refused because `localize_preserve_picture` **promises** the output runs as long as the input (`DUNG_SAI_DO_DAI_S`). Saying "impossible" where the truth is "promised otherwise" sends the next session to fix the wrong layer | V6 |
| `gia.py` | 97 | price estimate | **REFACTOR** | `smart_localize` costs differently — scene analysis + VLM added, discarded scenes subtracted | 06, 12 |
| `loi.py` | 145 | error taxonomy → platform | **EXTEND** | new typed errors for scene/VLM/binding/fit. The boundary-translation design **kept** | |
| `quan_sat.py` | 142 | run observability | **EXTEND** | per-item timeline; cost explainability | 20 |
| `san_sang.py` | 130 | can this host run Auto Scan at all | **ADD** | ⛔ Deliberately a **function, not a route**: Phase 25 forbids feature expansion, and a new endpoint is new public surface. 🔑 Three states, not two — `chua_do` (the probe itself failed) is never folded into `khong`, because a broken probe and an unconfigured dependency demand different actions, and a failed probe must never count as ready. Returns `co`/`khong` only, never the value of an environment variable | 25 |
| `nhap_media.py` | 308 | probe, input policy, normalize | **EXTEND** | policy gains preset awareness; streaming hash | 05, 13 |
| `tach_tieng.py` | 263 | demucs separation + bed mix | **KEEP** | Phase 13 measures it; changes only if the ledger says so | 13 |
| `demucs_runner.py` | 126 | isolated subprocess | **KEEP** | | |
| `ban_ghi.py` | 196 | `TranscriptDocument` | **KEEP** | canonical, validated, already rejects overlaps/dupes/drift | |
| `van_ban.py` | 168 | `ProcessedText` | **EXTEND** | must carry scene id + speaker + target duration for the fit loop | 14 |
| `dich_thuat.py` | 218 | transcript → Vietnamese via LLM | **REFACTOR** | 🔑 **the ordering fix**: translates only **retained** segments, and only after `EditPlan` and `VoiceBinding` exist. Chunk/merge/partial-detection logic **kept** | 14 |
| `giong_noi.py` | 216 | one segment → one wav | **KEEP** | The declared LTT Voice boundary is honoured exactly (Phase 02 §12). Phase 09 re-evaluates delegation but changes nothing here unless evidence says so | 09 |
| `thoi_gian.py` | 306 | TimingPlan (ADR-003) | **EXTEND** | must consume a cut list; the debt/borrow/1.15×/3-segment-cap model **kept** | 16 |
| `ban_dung.py` | 220 | RenderManifest as **data** | **EXTEND** | cut list + per-preset video mode. "Manifest is data, not a command string" **kept** | 17 |
| `ket_xuat.py` | 360 | renderer | **REFACTOR** | forks: `-c:v copy` (preserve) vs re-encode at cut points via `detect_gpu_encoder()` (smart). `ket_xuat.py:177` currently **raises** on any mode ≠ copy — that guard becomes preset-conditional, not deleted | 17 |
| `qc.py` | 237 | technical QC T1–T12 | **EXTEND** | T3 (bit-identical video) applies to preserve only; smart needs its own visual check | 18, 19 |
| `giai_doan_media.py` | 123 | MEDIA_PREPARE wiring | **EXTEND** | streaming hash | 13 |
| `giai_doan_am_thanh.py` | 111 | AUDIO_PREPARE wiring | **EXTEND** | streaming hash | 13 |
| `giai_doan_chep_loi.py` | 141 | TRANSCRIBE wiring | **EXTEND** | optional diarization (V4-R13) | 07 |
| `giai_doan_noi_dung.py` | 93 | CONTENT_PROCESS wiring | **REFACTOR** | becomes `DUB_SCRIPT_ADAPT`, downstream of EditPlan + VoiceBinding | 14 |
| `giai_doan_giong.py` | 176 | VOICE_SYNTHESIS wiring | **REFACTOR** | per-`AsvWorkItem` checkpoint replaces per-file-existence resume; bounded fit loop | 15 |
| `giai_doan_thoi_gian.py` | 104 | TIMING_ALIGN wiring | **KEEP** | | |
| `giai_doan_ban_dung.py` | 132 | COMPOSE wiring | **KEEP** | re-verifies every reference before spending a render slot — keep exactly | |
| `giai_doan_ket_xuat.py` | 214 | RENDER wiring | **REFACTOR** | dual path | 17 |
| `giai_doan_qc.py` | 153 | QC gate | **EXTEND** | AI QC lanes + RepairPlan emission. The "gate must block" fix **kept** | 19 |
| `giai_doan_qc_ai.py` | 178 | AI QC stage (semantic) | **NEW** | Phase 19 second half. **Off by default** (`LTT_ASV_QC_AI`) - turning it on is a pricing decision, so the switch is an operator env var, never a customer `settings` field. Semantic only; speech QC needs ASR and visual QC needs frame extraction, both deferred | 19 |
| `hop_dong_v4.py` | 213 | V4 product contract | **KEEP** | written in Phase 01 | |

### Executor apps

| App | Decision | Why |
|---|---|---|
| `asv_media` | **EXTEND** | new `job_types` for scene sampling / compose variants |
| `asv_gpu` | **EXTEND** | VRAM for `audio_prepare` must be **measured**, not guessed (V4-R05) |
| `asv_voice` | **KEEP** | |

## The 8 new modules (all ABSENT, proven in Phase 02)

| New module | Domain object | Owner rationale | Phase |
|---|---|---|---|
| `canh.py` | shot boundaries + representative frames | **domain policy** — sampling rate, frame choice | 10 |
| `giai_doan_canh.py` | SCENE_ANALYZE wiring | | 10 |
| `hieu_canh.py` | VLM prompt + response schema | prompts/schemas are ASV's per A.3; the *model call* stays platform | 11 |
| `ho_so_noi_dung.py` | `ContentProfile` | | 11 |
| `ke_hoach_bien_tap.py` | `EditPlan` + preset policy | keep/cut policy is domain policy | 12 |
| `rang_buoc_giong.py` | `VoiceBinding` + AUTO_MATCH | binds against `giong_mau` attributes (V4-R14) | 09 |
| `khop_do_dai.py` | `DubbingFit` bounded loop | | 15 |
| `qc_ai.py` | speech/semantic/visual QC + `RepairPlan` | | 19 |

**None of these is AI infrastructure.** Each owns a prompt, a schema, or a policy; every model
call goes through `platform_core/llm/dieu_phoi.py` or a declared owner-app surface.

## Migration order — and why this order

```
05  AsvWorkItem + large input          <- unblocks 09 and 15; nothing else can start cleanly
06  billing/usage foundation           <- MUST precede any new paid call
07  ASR/diarize surface extension      <- additive, independent
08  LLM/vision boundary                <- additive, independent
09  VoiceBinding (needs 05, 07)        <- AUTO_MATCH needs speaker evidence + item rows
10  scene segmentation                 <- independent of the audio branch
11  VLM understanding (needs 10)
12  EditPlan (needs 11)                <- freezes the cut list
13  audio separation resources
14  dubbing adaptation (needs 12, 09)  <- first paid call that depends on the new order
15  synthesis + fit (needs 14, 05)
16  timing/master  17  render  18  QC  19  AI QC  20  observability  21  UI
```

🔑 **06 before 14 is not a preference.** `V4_OPERATING_CONTRACT` A.6 makes `AsvRun` the single
billing owner; every new paid capability added before that foundation is a place a second
owner can appear by accident.

🔑 **12 before 14** is the correction V4 exists for: freeze the cut list, then pay to translate
what survives.

## Rollback

Every step is additive at the schema level. `AsvWorkItem` is a **new table**; no existing
column changes type or meaning, so `downgrade()` is a `drop_table` and old rows keep working.
`pipeline.CHUOI` grows by appending declarations — a run created under the old chain keeps its
`AsvStage` rows and its `contract_version`, which is what that column is for.
