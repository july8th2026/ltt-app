# AUTO SCAN VIDEO — DEPENDENCY MAP (Phase 00)

Evidence SHA `c31b1aeeee2f1831840b78f4d9ded94cfab09bc0`, branch `admin-mvp-v3`.
Read-only. Every claim below cites a real path + line.

---

## 1. Source snapshots

| Name | Location used as evidence | Role | Writable? |
|---|---|---|---|
| `LTTSTUDIOSAPP` | `D:\LTTSTUDIOSAPP` (this working tree) | target platform | yes (later phases) |
| `FULL_AUTO_VIDEO` | `D:\FULL AUTO VIDEO` | transcript / pause-timing / DUNGVIDEO engines | **NO — reference only** |
| `Cut_only_ver2` | `D:\Cut_only ver2` | media/audio/render engine (`nerf_engine`) | **NO — reference only** |
| `Tailieuhethong` | GitHub `giaitritruyenthongltt-spec/Tailieuhethong` | published snapshot of the three above, for AI reading | **NO — snapshot, not a work repo** |

**GAP-00-A** — `START_HERE.md` names `Tailieuhethong` as the "mandatory repository" and
Prompt 00 asks to read `KHONG_CO_GI_TRONG_KHO_NAY.md` + an exclusion report. Neither file
exists in this working tree (`find . -maxdepth 2 -iname "*KHONG_CO_GI*"` → empty). The
snapshot repo was not cloned in this phase; the three local trees above are the *originals*
the snapshot is made from, so they are strictly higher authority under the
`START_HERE` precedence rule (code > docs > pack). Recorded, not "fixed".

---

## 2. Platform execution spine (LTTSTUDIOSAPP)

```
HTTP route
  └─ platform_core/job_submit.py:submit_with_credit()      # price → submit → hold, ONE txn
       ├─ platform_core/registry.py:credit_for()           # raises if job_type has no price
       ├─ platform_core/jobs.py:submit()                   # dedupe on (user, dedupe_key, unfinished)
       └─ platform_core/credit.py:giu_cho(user, amount, job_id)

worker process (platform_core/job_runner.py:run_forever)
  └─ _chay_mot_job(worker_id, capabilities=...)
       ├─ platform_core/jobs.py:claim()                    # FOR UPDATE SKIP LOCKED
       ├─ _giu_gpu() → platform_core/gpu_lease.py:acquire()
       ├─ _chay_handler() → apps/<slug>/jobs.py:handle(params, ctx)
       ├─ _quyet_toan_credit()  → credit.quyet_toan()      # no-op when hold == 0
       └─ _hoan_credit()        → credit.hoan()            # no-op when hold == 0
```

### 2.1 Queue SSOT — I1 ✅ available
`platform_core/models.py:249` `Job.__tablename__ = "jobs"`, docstring line 252 states it is
the single source of truth. `platform_core/jobs.py:144 claim()` is the only claim path
(`with_for_update(skip_locked=True)`, line 182).

### 2.2 Worker capability routing — **A04 CONFIRMED**
`platform_core/jobs.py:158-164`:
```python
if capabilities is not None:
    eligible = [item.slug for item in discover() if not item.error and
                set(item.manifest.requires).issubset(capabilities)]
    stmt = stmt.where(Job.app_slug.in_(eligible))
```
Routing granularity is **the app**, via `AppManifest.requires` (`registry.py:221`), *not*
the `job_type`. A single Auto Scan app declaring `requires=("api","ffmpeg","gpu")` is only
claimable by a lane holding **all three**. `gpu_vram_mb` and `max_runtime_s`
(`registry.py:330,340`) *are* per-`job_type`, so the contract is already inconsistent in
granularity — the ADR must exploit that rather than change core.

`requires` is **not** validated against a closed vocabulary — `apps/ltt_voice/manifest.py:118`
declares `requires=("voice",)`, an app-invented capability. Lanes come from
`LTT_WORKER_POOLS` (e.g. `api:8, gpu+ffmpeg:2`); unset ⇒ one universal worker.
Per `docs/LTT_VOICE/02_QUY_TRINH_TRIEN_KHAI.md:132`, production currently does **not**
set it, so today everything is claimable — the failure mode is latent, and silent when it
fires (job sits `queued` forever, no error).

### 2.3 Run aggregate precedent — already exists, already correct-shaped
`platform_core/agent/` + `apps/agent/jobs.py` implement exactly the pattern
`EXECUTION_GUARDRAILS.md §1` asks for:

| Guardrail requirement | Existing mechanism | Evidence |
|---|---|---|
| run aggregate coordinating child `Job` rows | `AgentRun.plan` / `.checkpoint` + `Job.plan_id/step_id` | `models.py:458`, `models.py:296-300` |
| parent must NOT hold a worker to poll | `agent.advance` ticks once then **re-enqueues itself** at +2 s | `apps/agent/jobs.py:31-37` |
| checkpoint concurrency safe (I18) | `runs.get_owned(..., lock=True)` row lock around every tick | `agent/executor.py:227` |
| one billing owner (I3/O4) | hold + settle keyed on `run.id`; children via `runs.submit_child` → plain `jobs.submit`, **no hold** | `agent/budget.py:90,113`; `agent/runs.py:117` |
| child settlement cannot double-charge | `_quyet_toan_credit` returns early when `so_da_giu(job.id) == 0` | `job_runner.py:660` |

**This is the single most important Phase 00 finding.** The V2 billing/execution model is
not hypothetical — a working, tested implementation of it is already in the platform.

**But it is Agent-shaped, and the leak surface is real** (`EXECUTION_GUARDRAILS §1` warns
about exactly this): `AgentRun` carries `budget_max`, `approved_at`, `approved_by`,
`decision_log`, `version` (`models.py:471-477`) and `budget.approve()` **requires** an
explicit human approval transition (`budget.py:81`). It is also the storage behind
`AgentWorkflow` = Canvas (`models.py:493`, docstring "Canvas lưu layout/config"). Reusing
`AgentRun` directly would drag planner/approval/Canvas semantics into a fixed-pipeline
product — forbidden by O18/I17. Phase 03 must decide: *reuse the **pattern**, own the
**table***.

### 2.4 Billing primitives
`platform_core/credit.py` — `giu_cho(db, user_id, amount, job_id)` (line 260),
`quyet_toan(db, user_id, job_id, actual)` (393), `hoan(db, user_id, job_id)` (439),
`so_da_giu(db, job_id)` (251), plus stranded-hold recovery `giu_cho_treo` (548) and
`tu_hoan_treo` (643) swept by `job_runner._quet_giu_cho_treo` (723) / `_tu_hoan_giu_cho_treo` (788).
The hold identity is a bare string, so a **run id** works as a hold identity — that is
precisely what `budget.approve` does.

**RISK-00-05**: `agent/executor.py:130 actual_cost()` recomputes cost from
`registry.credit_for(row.job_type, row.params)` × attempts. It **ignores**
`result["credit_cost"]` that handlers report — the exact defect class CLAUDE.md records
twice (H38 fixed 23/08, H37 fixed 24/08: "asked 4 images, machine returned 2, customer
charged 4"). A metered pipeline (render seconds, TTS characters, LLM tokens) cannot settle
correctly on this function.

### 2.5 Provider side-effect safety — I5/O5 ✅ available
`Job.provider_state` + `Job.provider_dispatched_at` (`models.py:326-328`);
`JobContext.provider_dispatched()` / `.provider_rejected()` (`job_runner.py:119,127`);
outcome classification `_provider_failure_kind(exc, provider_state=...)` (`job_runner.py:573`)
with `ambiguous` as a **terminal reason**, explicitly documented as not creating a parallel
queue. Auto Scan's LLM + TTS + any paid render must use this and nothing else.

### 2.6 Resource ownership — I11/O6 ✅ available, and the legacy path is the trap
- `platform_core/gpu_lease.py`: `acquire()` (128), `heartbeat()` (204), `release()` (217),
  `hold()` context manager (234), `reclaim_orphans()` (102).
- `platform_core/gpu.py:env_for(uuid, base)` (103) and `JobContext.gpu_env()`
  (`job_runner.py:97`) are how a handler hands the assigned card to a subprocess.
- `platform_core/gpu_claims.py` is the **machine-wide** plane shared with the other tenants
  on this box; it is called *by* `gpu_lease`, never by handlers.

### 2.7 Assets — O12/I14 ✅ primitives exist
`Storage.promote(staging_key, final_key)` (`storage.py:80`, impls at 262 and 353),
`url_for` / `put_url` presigned (103/109), `LocalStorage` + `R2Storage`.
`platform_core/upload_sessions.py` already implements the full commit protocol:
`create` (53) → `upload_target` (117) → `confirm` + magic-byte signature check (150/125) →
`promote(..., job=...)` (207) → `compensate` (309) → `sweep` (331) →
`cleanup_failed_job` (365) → `reconcile` (389).

### 2.8 App-owned durable state
Two roads, both in-contract:
- `AppProject` JSON container — `platform_core/app_projects.py`, optimistic concurrency in
  `save()` (85), **1 MiB cap** (`MAX_PROJECT_BYTES`), depth cap 32, and a secret-name
  blocklist (`_FORBIDDEN`, line 16).
- Real tables — `AppManifest.table_prefix` (`registry.py:315`) + `apps/<slug>/tables.py`.
  Precedent: `apps/ltt_voice/tables.py` (`voice_profile`, `voice_ref`, `voice_repr`,
  `voice_consent`) with `table_prefix="voice"`.

### 2.9 Credential scope — **A05 / I7 CONFIRMED AS A LATENT GAP**
`ApiKey.owner_user_id` exists (`models.py:673`, indexed, migration
`alembic/versions/20260731_1600_them_bang_api_keys.py:24`) and is written by
`api_keys.tao_key(..., owner_user_id=)` (`api_keys.py:77,94`).

It is **never read**. `api_pool._ung_vien()` (`api_pool.py:73-98`) filters on
`enabled`, `status`, `categories`, `supported_models`, rpm/tpm — and nothing else.
`chon_key` (101) and `lay_key` (145) therefore treat every key as platform-pool.

Not a live leak **today**: the only writer of keys is the admin console
(`server/admin.py:734`) plus two operator scripts, so `owner_user_id` is `""` everywhere in
practice. It becomes a real cross-tenant leak the moment any app accepts a user-supplied
key. Fix must be additive per O15 (`owner_user_id == ""` keeps meaning "platform pool").

---

## 3. Engine sources

### 3.1 Already inside the platform (highest-value reuse)
`apps/autosubvideo/` — the only in-platform transcript+burn path:
`whisperx_runner.py`, `transcription.py`, `transcript_normalizer.py`, `segmenter.py`,
`pyannote_runner.py`, `ass_builder.py`, `burn.py`, `project_render.py`, `cost.py`.
Manifest: `requires=("ffmpeg",)`, `gpu_vram_mb={"autosubvideo.transcribe": 6000,
"autosubvideo.diarize": 2000}`, `lifecycle="development"`.

> ⚠ Note the manifest declares `requires=("ffmpeg",)` while declaring GPU VRAM for two job
> types. Under a `LTT_WORKER_POOLS` deployment those transcribe jobs would land on an
> ffmpeg-only lane. Pre-existing baseline debt — **recorded, not fixed** (O21).

`apps/upscalevideo/` — `engine.py`, `ff.py`, `autotune.py`, `telemetry.py`,
`requires=("gpu","ffmpeg")`, `lifecycle="released"`. The only *released* heavy-media app;
the closest thing to a working model for Auto Scan's RENDER stage.

`apps/ltt_voice/` — `requires=("voice",)`, job types `ltt_voice.synthesize` /
`ltt_voice.enroll`, own tables, loopback engine at `127.0.0.1:8120`. TTS is **in-platform
and already billed**, so VOICE_SYNTHESIS is a WRAP, not an integration project.

`apps/ltt_llm/` — tool `text.chat` → job `ltt_llm.chat`; three doors (jobs / sync / stream);
single token-budget authority `apps/ltt_llm/ngan_sach.py`. CONTENT_PROCESS is a WRAP.

`cutclipshort/` — a *vendored* copy of the Cut_only engine already sitting at repo root
(3 223 lines under `core/` alone) used by `apps/taoclipngan`. Contains its own
`core/job_queue.py` with a `ThreadPoolExecutor` (line 134) — an in-process executor. Not a
worker-claim queue, so not an I1 violation as vendored, but nothing new may route through it.

`platform_core/media.py` — `ffmpeg_bin`/`ffprobe_bin` (58/65), `probe()` (92) returning
duration/width/height/codec/fps/audio_codec/size/bitrate, `duration_seconds` (137),
`detect_gpu_encoder()` (154). MEDIA_PROBE has a platform-owned home already.

### 3.2 External legacy trees (reference only)

| Engine | Path | Lines | Legacy shell coupling |
|---|---|---|---|
| Whisper transcript | `FULL AUTO VIDEO/BOT_TRANSCRIPT/Bot_Whisper_FULL/engine/` | `stt.py` 501, `whisper_integration.py` 409, `vad.py` 219, `stt_runner.py` 207, + `segment/` (13 modules) | `stt.py:274` and `whisper_integration.py:207` → `from gpu_arbiter import current_gpu` |
| Pause/timing | `FULL AUTO VIDEO/Bot_PausePipeline/engine/` | `audio_splicer.py` 469, `stt.py` 436, `anchor_matcher.py` 384, `transcript_adjuster.py` 128, `insertion_planner.py` 107 | `stt.py:82-89` → `gpu_arbiter.current_gpu`; `utils/gsheets.py`, `utils/gdrive.py`; `credentials.json`, `token.json`, `state_pause.json` at bot root |
| DUNGVIDEO compose | `FULL AUTO VIDEO/DUNGVIDEO-FULL/engine/` | `assemble.py`, `matcher.py`, `segment.py`, `sequential_timeline.py`, `clip_sampling.py`, `runner.py`, `video_sanitize.py`, `subtitle/`, `music/`, `audio/`, `filters/`, `evaluation/` | `runner.py:697` → `from gpu_arbiter import GpuLease` |
| Cut/render | `Cut_only ver2/nerf_engine/` | `pipeline.py`, `stages/{audio,ffmpeg_edit,ffmpeg_edit_cutonly,scene_detect,select,upscale,yolo_reframe,motion,motion_zoom,camera_path,pipeline_motion}.py` | **NONE** — a grep for `gsheets\|gdrive\|gpu_arbiter\|gpu_claims\|job_claimer\|Sheet` across the tree hits only `bot_cut_only.py`, `bot_cut_remove_bgm.py`, `bot_gui.py`. The engine is clean. |

**The single migration rule this produces:** every legacy `gpu_arbiter.current_gpu` /
`GpuLease` call site is an I11 violation on import. Five sites, all listed above. An
extraction that copies the file without cutting that import silently re-introduces the
legacy GPU plane on a paid path.

`Cut_only ver2/nerf_engine` is the **cheapest** extraction in the whole project: the
legacy shell never reached inside it.

---

## 4. Duplicated systems found (O8 input)

| Concern | Implementations found | Note |
|---|---|---|
| job queue | `platform_core/jobs.py` (SSOT) · `cutclipshort/core/job_queue.py` (in-process pool) · `FULL AUTO VIDEO/job_claimer.py` + Google Sheets · `Cut_only ver2/bot_cut_only.py` | only the first may execute Auto Scan work |
| GPU arbitration | `platform_core/gpu_lease.py` + `gpu_claims.py` (platform) · `FULL AUTO VIDEO/gpu_arbiter.py` (legacy, 5 live call sites in engines) | legacy forbidden on new paths |
| run/checkpoint | `AgentRun` (platform, Canvas-coupled) · `AppProject` (generic JSON, 1 MiB) · `cutclipshort/core/project_manager.py` · `run_logger.py` | Phase 03 chooses one |
| speech-to-text | `apps/autosubvideo/whisperx_runner.py` (in-platform) · `Bot_Whisper_FULL/engine/stt.py` · `Bot_PausePipeline/engine/stt.py` · `DUNGVIDEO-FULL/engine/stt.py` | four; MVP needs one |
| ffmpeg wrapper | `platform_core/media.py` · `apps/upscalevideo/ff.py` · `nerf_engine/stages/ffmpeg_edit.py` | platform one is probe-only today |
