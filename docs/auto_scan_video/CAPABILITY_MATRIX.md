# AUTO SCAN VIDEO — CAPABILITY MATRIX (Phase 00)

Evidence SHA `c31b1ae`. Decisions here are **evidence-backed candidates**, not the freeze.
Phase 02 freezes required-vs-optional; Phase 03 freezes execution/billing/resource.

Reuse hierarchy per O8: **KEEP → WRAP → EXTRACT/REFACTOR → REWRITE**.

| Stage | Current path/entry | Callers | Legacy shell coupling | Resource | Input → output | Quality tests | Decision | Target | Notes |
|---|---|---|---|---|---|---|---|---|---|
| **INPUT / upload** | `platform_core/upload_sessions.py` `create`→`confirm`→`promote` | all media apps | none | api | browser upload → owner-scoped staging key | `tests/` upload-session suite | **KEEP** | unchanged | Magic-byte check at `upload_sessions.py:125`. Already owner-resolved server-side. |
| **MEDIA_PREPARE (probe)** | `platform_core/media.py:probe` (92) | autosubvideo, upscalevideo, taoclipngan | none | ffmpeg | path/URL → `{duration,w,h,codec,fps,audio_codec,size,bitrate}` | present | **KEEP** | unchanged | Accepts http(s) URLs (`is_remote_source`, line 81) ⇒ can probe an R2 presigned URL without downloading. |
| **MEDIA_PREPARE (normalize)** | `Cut_only ver2/nerf_engine/stages/ffmpeg_edit.py`; `apps/upscalevideo/ff.py` | legacy bot; upscalevideo | **none in `nerf_engine`** | ffmpeg | source → normalized mezzanine | legacy: unknown | **EXTRACT** (nerf) or **WRAP** (upscalevideo/ff) | `platform_core` or app service | Prompt 08 decides. `nerf_engine` is coupling-free — cheapest extraction in the project. |
| **AUDIO_PREPARE / separation** | `Cut_only ver2/nerf_engine/stages/audio.py`; `Cut_only ver2/bot_cut_remove_bgm.py` (shell) | legacy bot | shell only, not the stage | ffmpeg (+gpu if Demucs) | video → voice/bgm stems, mix | unknown | **EXTRACT** | app service | Take `stages/audio.py`, **never** `bot_cut_remove_bgm.py`. |
| **TRANSCRIBE** | `apps/autosubvideo/whisperx_runner.py` + `transcription.py` + `transcript_normalizer.py` + `segmenter.py` | `apps/autosubvideo/jobs.py` | **none** | gpu 6000 MB | audio → word/segment timestamps | in-platform tests exist | **WRAP** ⭐ | shared service | Already in-platform, already GPU-declared. Strongly preferred over the three legacy `stt.py` copies. |
| ↳ *alt* legacy transcript | `FULL AUTO VIDEO/BOT_TRANSCRIPT/.../engine/stt.py` (501) + `segment/` (13 modules) | legacy bot | **`gpu_arbiter.current_gpu` @ `stt.py:274`, `whisper_integration.py:207`** | gpu | audio → transcript + repair/merge/split rules | unknown | **EXTRACT only if `segment/` quality rules are proven required** | shared service | The value here is `engine/segment/*` (merging, splitting, padding, silence, repair), not the STT call. Phase 10 decides. |
| **CONTENT_PROCESS** | `apps/ltt_llm/` tool `text.chat` → job `ltt_llm.chat` | public API, agent | none | api (remote GPU on máy B) | transcript → translated/rewritten text | budget suite `tests/test_334_ngan_sach_ltt_llm.py` | **WRAP** | adapter in Auto Scan app | Token budget authority is `apps/ltt_llm/ngan_sach.py` — must call `mac_dinh_cho("job")`, never a bare default (documented cutoff bug). |
| **VOICE_SYNTHESIS** | `apps/ltt_voice/` jobs `ltt_voice.synthesize` | voice UI, public API `speech.ltt` | none | `voice` capability, 2000 MB | text → audio + duration | in-platform | **WRAP** | adapter | **1 500 char/turn is a quality ceiling, not technical** — chunking belongs to Auto Scan's TIMING stage, not to a "fix" in ltt_voice. `temperature/top_k/top_p` are not public contract. |
| **TIMING_ALIGN** | `FULL AUTO VIDEO/Bot_PausePipeline/engine/` — `anchor_matcher.py` (384), `audio_splicer.py` (469), `insertion_planner.py` (107), `transcript_adjuster.py` (128) | legacy bot | `engine/stt.py:82-89` → `gpu_arbiter`; `utils/gsheets.py`, `utils/gdrive.py` at bot level | ffmpeg (+gpu only for its own stt) | transcript + new voice → timing plan, spliced audio | unknown | **EXTRACT** | app service | The four engine modules above are the asset. `engine/stt.py` is a duplicate STT — drop it, reuse the TRANSCRIBE stage output. That single substitution removes the only `gpu_arbiter` import in this engine. |
| **COMPOSE** | `FULL AUTO VIDEO/DUNGVIDEO-FULL/engine/` — `assemble.py`, `sequential_timeline.py`, `matcher.py`, `segment.py`, `clip_sampling.py` | legacy bot | `runner.py:697` → `gpu_arbiter.GpuLease` | cpu | timing plan + assets → render manifest | unknown | **EXTRACT (manifest builder only)** | app service | O9 + G9 require composer ≠ renderer. Take the timeline/assemble modules; **leave `runner.py`** — that file *is* the legacy orchestrator and holds the only GPU-lease coupling. |
| **RENDER** | `apps/upscalevideo/engine.py` + `ff.py`; `nerf_engine/stages/ffmpeg_edit_cutonly.py`; `platform_core/media.py:detect_gpu_encoder` | upscalevideo; legacy | none / none | gpu + ffmpeg | manifest → final mp4 | upscalevideo is `lifecycle="released"` | **WRAP** (`upscalevideo` pattern) + **EXTRACT** (ffmpeg_edit) | app service | `upscalevideo` is the only *released* GPU+ffmpeg app — copy its resource shape, not its code. |
| **QC** | `platform_core/media.py:probe`; `cutclipshort/evaluation/`; `DUNGVIDEO-FULL/engine/evaluation/` | mixed | none | ffmpeg | final file → validity verdict | — | **WRAP** `probe` + new gate | app service | G9 needs a QC gate that can *block*. `probe` supplies the ffprobe truth; the policy is new, small, and Auto-Scan-owned. |
| **OUTPUT/delivery** | `Storage.url_for` presigned (`storage.py:103`), `R2Storage` (300) | all apps | none | api | durable key → time-limited URL | — | **KEEP** | unchanged | Cloudflare 100 MB / 100 s limits (CLAUDE.md) make presigned direct-to-R2 mandatory for finals. |
| **Run orchestration** | `platform_core/agent/executor.py:tick` + `apps/agent/jobs.py:handle` (self re-enqueue) | agent app | Canvas/planner/approval semantics in the same table | api | run → child jobs | agent test suite | **EXTRACT PATTERN, NOT TABLE** | Auto-Scan-owned tables (`table_prefix`) | See DEPENDENCY_MAP §2.3. Reusing `AgentRun` imports approval + Canvas — violates O18/I17. |
| **Billing** | `job_submit.submit_with_credit`; `agent/budget.py` run-level hold | platform | none | — | — | credit suite | **WRAP** run-level pattern | Auto-Scan billing module | ⚠ do **not** reuse `agent/executor.actual_cost` — see RISK-00-05. |
| **GPU assignment** | `gpu_lease.acquire/hold` + `JobContext.gpu_env()` | job_runner | — | — | — | present | **KEEP** | unchanged | Every extracted engine must have its `gpu_arbiter` import replaced by this. |
| **Credential scope** | `api_pool.chon_key` | all provider apps | none | — | — | present | **EXTEND additively** | `api_pool` + explicit scope | `owner_user_id` written, never read (`api_pool.py:73-98`). O15: default `""` must keep meaning "platform pool". |

---

## Stage-to-source coverage check (Prompt 00 exit gate)

Exit gate: *every logical MVP stage has at least one evidence-backed source/target plan or
an explicit GAP.*

| MVP stage (`MVP_PRODUCT_CONTRACT.md`) | Source | Status |
|---|---|---|
| MEDIA_PREPARE | `platform_core/media.py` + `nerf_engine/stages/ffmpeg_edit.py` | ✅ covered |
| AUDIO_PREPARE | `nerf_engine/stages/audio.py` | ✅ covered |
| TRANSCRIBE | `apps/autosubvideo/whisperx_runner.py` | ✅ covered (in-platform) |
| CONTENT_PROCESS | `apps/ltt_llm` | ✅ covered (in-platform, billed) |
| VOICE_SYNTHESIS | `apps/ltt_voice` | ✅ covered (in-platform, billed) |
| TIMING_ALIGN | `Bot_PausePipeline/engine/{anchor_matcher,audio_splicer,insertion_planner,transcript_adjuster}.py` | ✅ covered (extraction) |
| COMPOSE | `DUNGVIDEO-FULL/engine/{assemble,sequential_timeline,matcher,segment}.py` | ✅ covered (extraction) |
| RENDER | `apps/upscalevideo/engine.py` pattern + `nerf_engine/stages/ffmpeg_edit_cutonly.py` | ✅ covered |
| QC | `platform_core/media.py:probe` + new policy | ⚠ **GAP-00-B — policy does not exist anywhere.** QC is genuinely new code. No existing "block bad output" gate was found in any of the three trees. |

**GAP-00-C — no engine-level quality tests exist in the legacy trees.** The `_test_*.py`
files at `FULL AUTO VIDEO` root are ad-hoc scripts, not a suite. Every EXTRACT above
therefore needs a **parity fixture built first** (O10/CHANGE_PROTOCOL "when extracting a
legacy engine, establish parity fixture first") — there is no inherited test to lean on.

**GAP-00-D — smart-cut / reframe / scene-selection** (`nerf_engine/stages/{scene_detect,
select,yolo_reframe,motion*}.py`, `cutclipshort/analysis`, `editorial`) exist and are
substantial, but `MVP_PRODUCT_CONTRACT.md` explicitly defers the REQUIRED/OPTIONAL call to
Phase 02. Not classified here on purpose.
