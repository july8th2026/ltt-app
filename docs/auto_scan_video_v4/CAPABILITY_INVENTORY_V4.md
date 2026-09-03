# V4 CAPABILITY INVENTORY — evidence, then classification

Evidence SHA `706faca`, branch `phien/asv-v4`, measured 2026-09-03.
Authority: `V4_CAPABILITY_FIRST.md`. Classification vocabulary:

- **SUFFICIENT** — an existing contract already satisfies granularity, ownership and billing.
- **EXTEND_OWNER_CONTRACT** — the capability exists in its correct owner but is not exported;
  add to that owner's declared surface, additively, breaking no caller.
- **IMPLEMENTATION_ONLY** — code exists somewhere but not behind any owner contract.
- **ABSENT** — genuinely does not exist; must be built, in its correct owner.

---

## 0. The mechanism this whole phase turns on

Before classifying anything: **this platform already implements V4's "stable cross-app
boundary" rule, and implements it better than the V4 pack assumes.**

```
apps/<slug>/__init__.py        BE_MAT_CONG_KHAI = {("apps.x.mod", "name"), ...}
tools/lint_app_contract.py     APP_DUOC_DUNG_APP = {("caller", "callee"): {...}, ...}
```

Both sides must agree. The linter errors if an app is called but declares no surface, and it
runs inside `tools/gate.py` (step *app contract lint*, PASS in the Phase 00 baseline). Each
entry carries a written reason for why *that* name and not a neighbouring one.

This is exactly priority #2 in `V4_ARCHITECTURE_CONTRACT.md` — *"owner-app public service
boundary intentionally exported and tested"* — and it exists, today, with teeth.

🔴 **Phase 00 of this V4 run got this wrong and the correction is the main output of Phase
02.** Reading only the import list, I recorded V4-R02 as a P0: *"Auto Scan reaches through
into LTT Voice private internals at five sites."* It does not. Every one of those imports is
a **declared** boundary entry. See §12.

---

## 1. Full platform manifest census (19 apps)

| app | requires | surface | enabled | lifecycle | job_types | ToolSpec |
|---|---|---|---|---|---|---|
| `agent` | api | customer | ✅ | development | `agent.advance` | — |
| `anhnoibo` | api | customer | ✅ | development | `anhnoibo.generate` | `image.ltt` |
| **`asv_gpu`** | gpu | runtime | ❌ | internal | `audio_prepare`, `transcribe` | — |
| **`asv_media`** | ffmpeg | runtime | ❌ | internal | 7 stage types | — |
| **`asv_voice`** | voice | runtime | ❌ | internal | `voice_synthesis` | — |
| **`auto_scan_video`** | api | customer | ❌ | development | `advance`, `content_process` | — |
| `autosubvideo` | ffmpeg | customer | ✅ | development | `render`, `transcribe`, `diarize`, `translate` | `video.subtitle` |
| `chataistudio` | api | customer | ✅ | development | — | — |
| `ltt_llm` | api | customer | ✅ | development | `ltt_llm.chat` | `text.chat` [sync][api][`llm_remote`×1] |
| `ltt_voice` | voice | customer | ✅ | **released** | `synthesize`, `enroll` | `speech.ltt` [api][`vieneu_gpu`×1] |
| `nexus` | — | customer | ❌ | released | — | — |
| `prompt_ai_ommi` | api | customer | ✅ | released | `generate` | `text.prompt_package`, `story.storyboard` |
| `qualitylab` | ffmpeg | admin | ✅ | internal | `qualitylab.evaluate` | — |
| `taoanh` | api | customer | ✅ | development | `taoanh.generate` | `image.generate`, `image.batch_generate` |
| `taoclipngan` | gpu+ffmpeg | customer | ✅ | development | `taoclipngan.render` | `video.short_clips` |
| `taovideo` | api | customer | ✅ | released | `taovideo.generate` | `video.generate` |
| `thumbnail` | api | customer | ✅ | development | `thumbnail.generate` | `image.thumbnail` |
| `upscalevideo` | gpu+ffmpeg | customer | ✅ | **released** | `render`, `.fast`, `.quality` | `video.upscale`, `image.upscale` |
| `vps` | api | customer | ❌ | development | 3 provisioning types | — |

Declared VRAM anywhere in the platform: `upscalevideo.render` 12 000 · `.quality` 12 000 ·
`.fast` 2 000 · `autosubvideo.transcribe` 6 000 · `autosubvideo.diarize` 2 000 ·
`taoclipngan.render` 6 000 · `ltt_voice.synthesize`/`enroll` 2 000 ·
`asv_gpu.transcribe` 6 000 · **`asv_gpu.audio_prepare` 4 000 — the only unmeasured number.**

---

## 2. Classification per V4 need

| Need | Owner | Contract / path | Real caller | Resource | Billing / ownership | Class | V4 target boundary | Backward-compat |
|---|---|---|---|---|---|---|---|---|
| **ASR (transcribe)** | `autosubvideo` | `transcription.transcribe_file` (`transcription.py:162`), **declared** in `apps/autosubvideo/__init__.py::BE_MAT_CONG_KHAI` | `autosubvideo/jobs.py:90` (own) · `auto_scan_video/giai_doan_chep_loi.py:83` (ASV) | gpu, 6 000 MB | ASV holds; `autosubvideo` charges nothing on this path | **SUFFICIENT** | keep the wrap; ASV runs it inside `asv_gpu` | two live callers, unchanged |
| **Diarization** | `autosubvideo` | `ai_workflows.diarize_file` + `assign_speakers` — **now in `BE_MAT_CONG_KHAI`** (Phase 07) | `autosubvideo/jobs.py` **and** `auto_scan_video/giai_doan_chep_loi.phan_vai` | gpu, 2 000 MB | job-level | **SUFFICIENT** (was EXTEND_OWNER_CONTRACT) | closed in Phase 07: two additive lines on both sides, plus `gpu_uuid` on `diarize_file`. 🔴 The extension found a **live defect**: `pyannote_runner.py:20` did `if torch.cuda.is_available(): pipeline.to(torch.device("cuda"))` — it took the first card torch saw, **ignoring the `gpu_lease` assignment entirely**. Now pinned to the assigned card via the owner's own `_env_ghim_gpu` | additive; existing job path untouched (`gpu_uuid` defaults to `""`) |
| **Text generation** | `ltt_llm` | `ToolSpec("text.chat")` → `ltt_llm.chat`, sync executor, api-exposed, `admission_resource="llm_remote"`×1. Platform dispatch via `platform_core/llm/dieu_phoi.goi` | public `/api/v1`, `agent`, `chataistudio`, ASV `dich_thuat.py` | `llm_remote`×1 | measured usage; `ngan_sach` is the single budget source | **SUFFICIENT** | keep `dieu_phoi.goi`; ADR-001 D5-amended stands | `test_334` budget suite |
| **Vision (VLM)** | `ltt_llm` | same `text.chat`, model alias **`ltt_llm_vision`** → `qwen38-vision` (`features.py:40`). `dieu_phoi.goi(messages=…)` passes `messages` **verbatim** into `CongVlm.chat` → `{"model", "messages"}` → OpenAI-shape `/v1/chat/completions` | none yet for images | `llm_remote`×1 | same as text | **SUFFICIENT** | Phase 08/11 build OpenAI-shape image content; **no new client** | class is literally named `CongVlm`; nothing coerces `content` to `str` on the OpenAI path |
| **Voice catalog — user's own** | `ltt_voice` | `doc_man_api.ma_giong_cua_toi`, **declared** | ASV `gia.py:81` | — | owner-filtered inside the function | **SUFFICIENT** | `USER_SELECTED` uses it as-is | declared with a written reason |
| **Voice catalog — sample voices + attributes** | `ltt_voice` | `giong_mau.py`: `NHAN_GIOI` (nam/nữ), `NHAN_VUNG` (bắc/trung/nam), `NHAN_PHONG_CACH`, `DANH_SACH`, `THEO_MA`, **`loc(gioi=, vung=, phong_cach=)`**. **Not** in `BE_MAT_CONG_KHAI` | `ltt_voice` UI only | — | read-only | **EXTEND_OWNER_CONTRACT** | this is what `AUTO_MATCH` binds against; add `giong_mau.loc`/`DANH_SACH`; Phase 09 | additive, read-only |
| **Voice ownership check** | `ltt_voice` | `features.giai_giong`, **declared and mandatory** — its own docstring: *"đây là chỗ quyền sở hữu được kiểm, và nó là chỗ duy nhất"* | ASV `giong_noi.py:102` | — | I6/I7 | **SUFFICIENT** | unchanged | ADR-002 |
| **TTS, one segment** | `ltt_voice` | `features.goi_cong` + `text_pipeline.chuan_hoa` + `tham_so_cong_khai.TRAN_MOI_LUOT_SINH`, all **declared** | ASV `giong_noi.py:133,149,150` | `vieneu_gpu`×1 (held by the ToolSpec path) · sidecar service owns the VRAM | ASV holds; measured seconds | **SUFFICIENT** | unchanged | 3 declared entries, each with a recorded reason |
| **TTS as a job** | `ltt_voice` | `ToolSpec("speech.ltt")` → `ltt_voice.synthesize`, `vieneu_gpu`×1 | public `/api/v1` | `vieneu_gpu`×1 | job-level hold | **SUFFICIENT but wrong granularity** — see §3 | not used by ASV | — |
| **Durable large upload** | `platform_core` | `upload_sessions.create` → `upload_target` (presigned) → `confirm` → `promote`; magic-byte sniff at `:125`; caps ≤ 20 sessions, ≤ 2 GiB in flight | `autosubvideo/services/source_drafts.py:33-49` | api | owner resolved server-side | **SUFFICIENT** | Phase 05/21 replace ASV's `await video.read()`; **reuse, not build** | a live production caller already does this |
| **Media probe** | `platform_core` | `media.probe`; accepts http(s) URLs ⇒ can probe a presigned R2 URL without downloading | autosubvideo, upscalevideo, taoclipngan, ASV | ffmpeg | — | **SUFFICIENT** | unchanged | platform tests |
| **Hardware encode** | `platform_core` | `media.detect_gpu_encoder()` → `h264_nvenc` > `qsv` > `amf` > `""`; probes with 256×256 testsrc because NVENC has a minimum size (`media.py:174`) | upscalevideo | gpu | — | **SUFFICIENT** | Phase 17 calls it for `smart_localize` only | the minimum-size trap is already solved here |
| **Storage / delivery** | `platform_core` | `storage.url_for` presigned, R2 backend | all apps | — | — | **SUFFICIENT** | unchanged | platform tests |
| **Queue** | `platform_core` | `jobs.submit` / `claim`; **eligibility filtered by app, not job_type** | everything | — | — | **SUFFICIENT** | unchanged; no second queue, ever | ADR-001 D1 |
| **Credit** | `platform_core` | `credit.quyet_toan`, `job_submit.submit_with_credit` | all paid apps | — | one hold on `AsvRun` | **SUFFICIENT** | unchanged | ADR-001 D4 |
| **GPU lease** | `platform_core` | `gpu_lease` + `JobContext.gpu_env()` | job_runner | — | — | **SUFFICIENT** | unchanged; **no second scheduler** | — |
| **Credential scope** | `platform_core` | `api_pool.chon_key` + `PHAM_VI_POOL`/`PHAM_VI_RIENG` | all provider apps | — | owner predicate inside the query | **SUFFICIENT** | unchanged | ADR-002, `test_404` |
| **Subtitles** | `autosubvideo` | `ToolSpec("video.subtitle")` → `autosubvideo.render` | public API | ffmpeg | job-level | **SUFFICIENT**, post-MVP | not wired in MVP | — |
| **Upscale** | `upscalevideo` | `ToolSpec("video.upscale")`, `lifecycle="released"` | public API, `taovideo` | gpu 12 000 MB | job-level | **SUFFICIENT**, post-MVP | not wired in MVP | `taovideo` already calls it via a declared surface |
| **Scene detection / frame sampling** | — | nothing in `apps/`; legacy `nerf_engine/stages/scene_detect.py` is outside the repo | none | ffmpeg/cpu | — | **ABSENT** | new, owned by Auto Scan (domain policy) | Phase 10 |
| **SceneAnalysis / ContentProfile / EditPlan / VoiceBinding / DubbingFit / AI-QC** | — | nothing anywhere | none | — | — | **ABSENT** | new, owned by Auto Scan | Phases 11–19 |

---

## 3. The one contract that is right but the wrong shape

`speech.ltt` → `ltt_voice.synthesize` is a proper, public, admission-controlled ToolSpec.
Auto Scan does not use it, and V2 Phase 12 recorded why: **one job produces one file keyed on
`job_id`, and `asv_stage` holds exactly one `job_id` per stage.** Per-segment TTS needs N
units under one stage, so delegation had no place to checkpoint. V2 therefore called the
declared service functions in-process instead.

That was the right call *given V2's schema*, and it is the reason ASV's voice path looks like
a reach-through when you read only the imports.

⇒ **The fix is not in Phase 09. It is in Phase 05.** Once `AsvWorkItem` (or equivalent)
provides an owner-scoped, fingerprinted, per-segment checkpoint row, delegation to
`ltt_voice.synthesize` becomes *representable* — and only then is it worth re-deciding
whether to delegate or keep the in-process call.

Phase 09 must **re-evaluate**, not assume. Both options stay open, and the deciding evidence
is: does one job per segment give better retry/billing isolation than one stage with N
checkpointed items, at a queue cost of N rows per run?

---

## 4. `dich_thuat.py` → `ltt_llm.ngan_sach` is also declared

`apps/ltt_llm/__init__.py::BE_MAT_CONG_KHAI = {("apps.ltt_llm", "ngan_sach")}`, with the
reason spelled out: the token budget has **one** source of truth, and CLAUDE.md records a real
production bug from duplicating it — the stream path used the sync path's 1 024 budget and
**every long answer was silently cut at exactly 1 024 tokens**. A duplicated number is a number
that will drift, and drift of that kind fails no test.

⇒ V4-R03 was also wrong. Withdrawn.

---

## 5. What is genuinely missing — the honest short list

1. ~~**Diarization is not exported.**~~ **CLOSED (Phase 07)** — the two lines are in, and the extension surfaced a real GPU-arbitration defect that had nothing to do with Auto Scan: `pyannote_runner` never honoured the platform's card assignment.
2. **Sample-voice catalog is not exported.** `EXTEND_OWNER_CONTRACT`, Phase 09. Without it
   `AUTO_MATCH` has nothing to match *against*, and would degrade into "the default voice" —
   the exact conflation `ADR-V4-001` D-V4-04 forbids.
3. **Everything in the understanding/planning half is ABSENT** — scene segmentation, VLM
   analysis, ContentProfile, EditPlan, VoiceBinding, DubbingFit, three AI QC lanes, RepairPlan.
   This is *domain policy*, which `V4_OPERATING_CONTRACT` A.3 says Auto Scan **may** own.
   Nothing here is a second LLM/VLM/TTS/ASR client.
4. **`asv_gpu.audio_prepare` VRAM = 4 000 MB is a guess**, marked *CHUA DO* in its own
   manifest, and cannot be measured with this tree's `torch+cpu` interpreter (V4-R05).

## 6. Dependency rules frozen by this phase

1. Auto Scan imports another app **only** through that app's `BE_MAT_CONG_KHAI`, and every
   such edge must appear in `APP_DUOC_DUNG_APP`. Both sides, or the linter errors.
2. Auto Scan owns **domain policy** — prompts, schemas, edit policy, voice-binding policy,
   dubbing-fit policy, timing/render/QC/repair policy.
3. Auto Scan owns **no** AI infrastructure: no provider client, no key selection, no model
   endpoint, no GPU scheduler, no second queue.
4. Needing something an owner app has but does not export ⇒ **extend that owner additively**.
   Never copy, never reach past the surface, never fork.
5. `platform_core` must not learn the name of any app.
