# AUTO SCAN VIDEO — STATE V4

> Handoff SSOT for the V4 MVP prompt pack.
> Pack: `G:\My Drive\AI\A LTT AII\Auto_Scan_Video_V4_MVP` — entry `start_here.md`.
> Read order: pack contracts -> repo `CLAUDE.md`/`AGENTS.md` -> V2 `docs/auto_scan_video/STATE.md`
> -> this file -> the current phase prompt.
>
> V2 history is **retained, not rewritten**. Everything under `docs/auto_scan_video/` stays.
> V4 supersedes by ADR, never by deletion (start_here §5).

- **source_branch**: `phien/asv`
- **source_sha**: `706faca50c75fb5b6dbad6c346b96c98a6736a11`
  ("wip(auto_scan_video): pha 21 dang do — DUNG theo yeu cau chu du an")
  ✅ **identical to the pack's observed SHA** — `origin/phien/asv` and the local ref both
  resolve to `706faca`, so there is **no delta to audit** (start_here §1).
- **v4_branch**: `phien/asv-v4` (created from `706faca`)
- **worktree**: `D:\LTTSTUDIOSAPP\.claude\worktrees\auto-scan-video-v4-mvp-7173d9`
  - ⚠️ The pack *suggested* `D:\LTTSTUDIOSAPP-asv-v4`. This session was launched by the
    harness inside an already-isolated worktree whose contract is "run everything here, never
    `cd` to the repo root". Creating a second tree would have left a stray checkout on the
    user's disk and split the work across two directories. The **binding** requirement —
    a dedicated worktree that is not `master`, not the existing `phien/asv` tree
    (`D:\LTTSTUDIOSAPP-asv`), and not the production tree — is satisfied. Recorded here
    rather than silently diverging.
  - ⛔ **This machine IS production** (`C:\LTTPlatform` exists). Never deploy from here.
- **current_phase**: 06
- **phase_status**: Phase 05 PASS -> Phase 06 NOT STARTED
- **last_green_invariant_command**: declared in `tests/bo_bat_bien_v4.py`, two rounds —
  `VONG_NHANH` (9 files, **~12.5 s**, run after every edit) and
  `VONG_DU` (+ `test_417`, **~78 s**, run before closing a phase).
  ⚠️ `test_417` alone is 84 % of the full time. It is **split, not dropped**: it proves
  downstream invalidation, and an 80-second suite gets run once a day instead of after
  every edit — which is how a defect ends up ten edits deep.
- **last_green_invariant_result**: `VONG_DU` → **165 passed, 1 xfailed in 77.49 s** (2026-09-03)
- **certified_baseline**: `python tools/gate.py --phien asv-v4` -> `RESULT: FAIL (1/26)`, 675 s,
  **2 failed / 5 769 passed / 32 skipped**, no tree-changed warning.
  Both failures proven non-ASV: `test_82` (gitignored `apps/*/vendor/`, every fresh worktree)
  and `test_361` (passes alone; red only because the gate held the quiet-window lock it asserts on).
  Raw log: `evidence/00_gate_baseline.txt`
- **critical_external_evidence_pending**: see table below
- **open_blockers**: none
- **cong_viec_ha_tang_dang_cho** (ngoai pham vi ASV, nhung chan lai viec do dac tien):
  **ngan sach loi cua `gate.py` la per-RUN, khong per-MAY.** `ngan_sach_loi()` chi doc
  `os.cpu_count()`, nen moi luot tu tin no co 14 loi va **ca hai deu dung theo cach tinh cua
  rieng minh**. Do duoc: 1 luot + nen production = 19/20 loi (OK); **2 luot = 33/20 (qua tai
  13 luong)**; 3 luot = 47/20.
  ⚠️ `BELOW_NORMAL_PRIORITY_CLASS` khong che duoc ca nay — no cuu `LTTStudioWeb` khoi gate,
  nhung hai gate deu uu tien thap **bang nhau** nen tranh nhau song phang.
  ⛔ Mau chot: `cua_so_yen.thu_giu():134` **khong ghi `so_loi`** vao ban ghi khoa, nen mot
  phien thay phien khac dang giu van khong biet phien kia dung bao nhieu.
  Ba thay doi cong them, da gui `lttchat-...-49` (ho dang mo `gate.py`):
    A. `thu_giu()` ghi them `so_loi` (mac dinh 0 -> caller cu khong doi hanh vi)
    B. `ngan_sach_loi()` tru Sigma loi cac phien KHAC dang giu; giu `max(2, ...)`
       ⚠️ phai lay so **sau khi da giu khoa**, khong phai o `gate.py:224` luc dung danh sach buoc
  🔴🔴 **DO DUOC TRUOC KHI SUA — NGAN SACH HIEN TAI DANG LAM DIEU NGUOC LAI:**

        os.cpu_count()            = 20   (loi LOGIC)
        psutil.cpu_count(False)   = 10   (loi VAT LY  <- xdist `auto` dung so nay)
        gate truyen  -n           = 11

     `loi_bo_test = min(12, ngan_sach_loi() - len(FRONTENDS)) = min(12, 14-3) = 11`.

     ⇒ **Gate dang chay 11 worker trong khi `-n auto` chi mo 10.** Co che "ngan sach loi"
       sinh ra de GIAM tai, va tren may nay no dang TANG — dung lop loi ma `-49` mo ta
       (mot ngan sach la GIOI HAN TREN, khong phai mot phep gan), chi khac la no dang song
       trong ma chu khong phai trong mot ban nhap.

     ⭐ Nguyen nhan goc: `ngan_sach_loi()` tinh tren `os.cpu_count()` = loi **logic** (20),
       con xdist `auto` tinh tren loi **vat ly** (10). Hai don vi khac nhau bi tru cung mot
       hang so `LOI_DE_DANH_CHO_MAY = 6`. Tren mot may khong SMT thi hai so trung nhau va
       loi nay khong ton tai — nen no chi lo ra o dung loai may nay.

     ⇒ Sua bat buoc phai la `min(<ngan sach cua ta>, <cau tra loi cua chinh cong cu>)`.
       Va `test_nhanh.py:219` truyen thang `-n` cho pytest, khong kep gi — nen khong co
       lop nao ben duoi bat lai giup.

  🔴 **BA SUA CHUA tu `lttchat-...-49` sau khi doc thiet ke — diem 2 la mot LOI THAT:**
    1. **Tinh lai con so thoi thi VO NGHIA.** `gate.py:224` dung `argv` cua buoc `bo test`
       voi `-n <so>` **da co dinh** truoc khi `CuaSoYen.__enter__` chay. Lay so moi sau khi
       giu khoa ma khong dung lai `argv` thi no tru dung va **van chay 11 worker**. Cho sach
       nhat: cho `Step` giu mot HAM dung argv tre, thay vi mot list co dinh.
    2. ⛔ **`so_loi = 0` cho ban ghi cu la FAIL-OPEN.** Toi thiet ke mac dinh 0 de caller cu
       khong doi hanh vi — nhung 0 co nghia "khong khai", khong phai "khong dung loi nao".
       Mot luot gate CU dang giu khoa se doc ra 0 loi => ngan sach khong bi tru => **dung cai
       qua tai ta muon chan, chi khac la im lang**. Sua: doc ra 0 ma ban ghi CO tai nguyen
       `cpu_nhieu` thi tinh bang mot gia tri de dat (vd `ngan_sach_loi()` mac dinh), tuc
       fail-CLOSED o dung cho no re.
    3. Hop nhat chu ky: ho da them `ngan_sach_loi(do_tai=False)`. Ba co cho cung mot cau hoi
       "toi duoc dung bao nhieu loi" la ba cau tra loi khac nhau cho cung mot cau hoi — gop
       thanh MOT tham so.
  ⭐ Va mot bai hoc ho tra gia de co, ap thang vao day: ban dau ho lay `cpu_count() - 6` = 14
     lam **tran** cho `-n`. Sai — xdist tu tra loi **10** (loi vat ly), nen cai "tran" 14 lai
     **NANG** so worker len, nguoc han chieu no ton tai. Phai la `min` voi cau tra loi cua
     chinh cong cu, khong phai mot phep gan. Ngan sach nay se gap dung hinh dang do o **moi**
     cong cu con biet tu do.

    C. **PHAN CUA PHIEN NAY, lam sau khi A+B merge:** het `--cho` ma chay de thi ngan sach
       = phan CON LAI, khong phai full 14. Giu nguyen quyet dinh "khong tu choi chay" —
       chi la khi biet minh dang chen thi tu thu nho. Can mot chot rieng chung minh ngan
       sach THAT SU thu nho, khong phai mot co bao rang no thu nho.
- **debt_carried**: a **full** `tools/gate.py` run has not completed since Phase 00's
  baseline. The Phase 04 attempt died at step 20/26 with no `RESULT:` line when the
  previous session exited, and a peer session then announced a production deploy on this
  machine — restarting a 20-worker suite would have contended with it. `--quick` is PASS
  but says of itself it is not evidence. **Run the full gate at the next phase boundary**
  once the peer's deploy is done.

## Runtime measured on this machine (2026-09-03)

| Item | Value | Why it matters to V4 |
|---|---|---|
| OS / shell | Windows 10 Pro 19045, PowerShell 5.1 + Git Bash | `.ps1` must stay ASCII, config writes BOM-free |
| Python (dev/test) | 3.13.12 | the interpreter the gate and pytest run under |
| **torch (dev/test)** | **2.11.0+cpu — `cuda.is_available() == False`** | 🔴 every test here measures a **CPU** device |
| **torch (production)** | `C:\LTTPlatform\venv` — **2.11.0+cu128, cuda True, 2 devices** | 🔴 production and test disagree about the device |
| ffmpeg | 8.0.1-full (gyan.dev) | render/compose/probe |
| GPUs | 2 × RTX 5060 Ti, 16 311 MiB each (977 / 802 MiB in use) | both cards visible; the older "Code 43" fault is gone |
| `LTT_WORKER_POOLS` | unset in this shell | lane routing is production-side config |
| Production install | `C:\LTTPlatform` present, plus `vieneu-venv` and `whisperx-venv` | Voice and ASR run in **their own** interpreters |

## Current ASV runtime — traced, not summarised

`run -> advance -> stage -> job -> artifact -> settlement`, all in
`apps/auto_scan_video/`:

1. **create** — `features.tao_run` writes one `AsvRun` + nine `AsvStage` rows, takes **one**
   credit hold on `run.id`, then submits the coordinator job.
2. **advance** — `jobs.handle` -> `jobs._advance`. Locks the run row **first**
   (`features.lay_run(..., lock=True)`), returns immediately if the run is terminal — this is
   the half of I13 that stops a late child from reviving a cancelled run.
3. **reconcile** — `_thu_ket_qua_job_con` maps child `Job` states onto stages. 🔑 It refuses to
   infer `job.status == done` ⇒ `stage succeeded`; a handler that died after the engine
   returned but before `promote` is marked failed-and-retryable, not done.
4. **invalidate** — `_vo_hieu_giai_doan_da_lech` re-checks fingerprints at the top of every
   tick and resets drifted stages **plus their downstream closure**
   (`pipeline.ha_nguon_cua`).
5. **submit** — `_nop_giai_doan_san_sang` submits one child `Job` per ready stage with
   `plan_id = run.id`, `step_id = stage`, price **0**, and snapshots the admission resource.
6. **execute** — `thi_hanh.chay_theo_job_type` -> `chay_giai_doan`, five-step asset protocol
   (engine -> validate -> `storage.promote` -> persist refs+fingerprint -> commit), keys
   `asv/{owner}/{run}/{stage}/{fingerprint}` so re-writes are idempotent.
7. **settle** — `features.quyet_toan`, once, idempotent, `actual = min(Σ asv_stage.credit_actual,
   credit_held)`; the remainder is refunded. `kiem_tran_chi` is the mandatory pre-spend check.
   🔑 Measured, never recomputed from a price table (ADR-001 D4).

### The nine stages and their lanes (`pipeline.CHUOI`)

| # | Stage | Executor app | Lane (`requires`) | Admission resource |
|---:|---|---|---|---|
| 1 | `media_prepare` | `asv_media` | `ffmpeg` | — |
| 2 | `audio_prepare` | `asv_gpu` | `gpu` | `tach_nguon_cuc_bo` ×1 |
| 3 | `transcribe` | `asv_gpu` | `gpu` | `tach_nguon_cuc_bo` ×1 **(same name on purpose)** |
| 4 | `content_process` | `auto_scan_video` | `api` | `llm_remote` ×1 |
| 5 | `voice_synthesis` | `asv_voice` | `voice` | — |
| 6 | `timing_align` | `asv_media` | `ffmpeg` | — |
| 7 | `compose` | `asv_media` | `ffmpeg` | — |
| 8 | `render` | `asv_media` | `ffmpeg` | — |
| 9 | `qc` | `asv_media` | `ffmpeg` | — |

Four apps, one product: one customer-facing (`auto_scan_video`) and three hidden runtime
executors (`asv_media`, `asv_gpu`, `asv_voice`, all `catalog_parent="auto_scan_video"`).
The split exists because `platform_core/jobs.py` filters claim eligibility by **app**, not by
`job_type` — an app declaring all four capabilities is invisible to every split-lane worker
and its jobs sit `queued` forever with no error.

Declared VRAM (`asv_gpu/manifest.py`): `audio_prepare` 4 000 MB **(never measured)**,
`transcribe` 6 000 MB (borrowed from `autosubvideo.transcribe`, measured there).

## V4 target shape vs. what exists today

`V4_PIPELINE_DAG.md` needs **19** pipeline nodes. Nine exist. The V4 gap is not "polish the
nine" — it is that the whole *understanding and planning* half of the product
(`SCENE_ANALYZE`, `VISUAL_UNDERSTAND`, `CONTENT_PROFILE`, `EDIT_PLAN`, `VOICE_BIND`,
`DUBBING_FIT`, and the three AI QC lanes) has no code at all, and that `content_process`
currently does translation **before** any edit or voice decision exists — the exact ordering
V4 forbids (`V3_TO_V4_CORRECTIONS` §2/§3).

| V4 node | Today | V4 phase |
|---|---|---|
| `TECHNICAL_PREPARE` | ✅ `media_prepare` | 05 |
| `AUDIO_PREPARE` | ✅ `audio_prepare` (demucs) | 13 |
| `TRANSCRIBE` | ✅ `transcribe` (wraps autosubvideo) | 07 |
| `DIARIZE?` | ❌ absent | 07 |
| `SCENE_ANALYZE` | ❌ absent | 10 |
| `VISUAL_UNDERSTAND` | ❌ absent | 11 |
| `CONTENT_PROFILE` | ❌ absent | 11 |
| `EDIT_PLAN` | ❌ absent | 12 |
| `VOICE_BIND` | ❌ absent (voice is a raw setting) | 09 |
| `DUB_SCRIPT_ADAPT` | ⚠️ `content_process` — runs **before** edit/voice decisions | 14 |
| `VOICE_SYNTHESIS` | ✅ per-segment, resumable | 15 |
| `DUBBING_FIT` | ❌ absent | 15 |
| `TIMING + AUDIO_MASTER` | ✅ `timing_align` (ADR-003) | 16 |
| `COMPOSE_PLAN` | ✅ `compose` (manifest is data) | 17 |
| `RENDER` | ✅ `render` — **stream-copy only**, no smart-cut path | 17 |
| `TECH_QC` | ✅ `qc` (T1–T10) | 18 |
| `SPEECH/SEMANTIC/VISUAL_QC` | ❌ absent | 19 |
| `REPAIR_PLAN` | ⚠️ stage-level retry only, no segment targeting | 19 |

## V4 critical risks — read from code at `706faca`, not from old prompts

| ID | Sev | Gate | Finding (with evidence) | Owner phase |
|---|---|---|---|---|
| ~~V4-R01~~ | **CLOSED (Phase 05)** | G6 | `routes.py:155` does `du_lieu = await video.read()` and `routes.py:79` caps at `TRAN_TAI_LEN = 90 MB`. `features.tao_run_tu_tai_len` then holds that `bytes` object while it *also* writes a temp copy and *also* streams it to storage — the whole video is resident **twice**. The durable path already exists and already has a real caller (`platform_core.upload_sessions.create/upload_target/promote`, used by `apps/autosubvideo/services/source_drafts.py`), so this is a **reuse**, not a build. | 05 / 21 |
| ~~V4-R02~~ | **WITHDRAWN (Phase 02)** | G3 / G11 | 🔴 **I recorded this wrong in Phase 00.** I read the import list in `giong_noi.py`, matched it against `V4_CAPABILITY_FIRST`'s forbidden list ("TTS sidecar client", "copied LTT Voice text-normalization constants") and called it a P0 reach-through. It is not. `apps/ltt_voice/__init__.py` declares `BE_MAT_CONG_KHAI` and **every one of those six names is in it**, each with a written reason; `tools/lint_app_contract.py::APP_DUOC_DUNG_APP` enforces the other side, and that linter runs in the gate. Tracing the real caller shows ASV honours the surface exactly: `sidecar_client` only for `san_sang()`, `text_pipeline.chuan_hoa` and **not** `features.chuan_bi_van_ban`, ownership always through `giai_giong`. This is priority #2 of `V4_ARCHITECTURE_CONTRACT` already implemented. Had it stood, Phase 09 would have rebuilt a boundary that exists. | — |
| ~~V4-R03~~ | **WITHDRAWN (Phase 02)** | G3 | Same error, same cause. `apps/ltt_llm/__init__.py::BE_MAT_CONG_KHAI = {("apps.ltt_llm", "ngan_sach")}` — declared on purpose, because the token budget must have exactly one source: CLAUDE.md records a real production bug where a duplicated budget silently truncated every long answer at 1 024 tokens. | — |
| ~~V4-R13~~ | **CLOSED (Phase 07)** — two additive lines on both sides, plus `gpu_uuid` on `diarize_file`. The extension found a real GPU-arbitration defect in the owner app that had nothing to do with ASV. | G3 | **Diarization is not exported.** `autosubvideo/ai_workflows.py` has `diarize_file` + `assign_speakers` and the manifest declares `autosubvideo.diarize` (VRAM 2 000), but neither name is in `autosubvideo.BE_MAT_CONG_KHAI` — only `transcribe_file` is. EXTEND_OWNER_CONTRACT: two additive lines on both sides. | 07 |
| ~~V4-R14~~ | **CLOSED (Phase 09)** — seven additive read-only names; AUTO_MATCH now has a catalog to match against, and defers rather than defaulting when it has no evidence. | G11 | **`AUTO_MATCH` has nothing to match against yet.** `apps/ltt_voice/giong_mau.py` already carries exactly the right data — `NHAN_GIOI` (nam/nữ), `NHAN_VUNG` (bắc/trung/nam), `NHAN_PHONG_CACH`, `DANH_SACH` and a `loc(gioi=, vung=, phong_cach=)` filter — but none of it is exported. Without the extension, Phase 09 can only ship `AUTO_MATCH` as "the default voice", which `ADR-V4-001` D-V4-04 explicitly forbids. EXTEND_OWNER_CONTRACT, read-only. | 09 |
| ~~V4-R04~~ | **PARTIALLY CLOSED (Phase 06)** — the guard was added in Phase 04; Phase 06 added the missing half: even when the guard is lifted (`LTT_TEST_NANG=1`), `demucs_runner` no longer takes the whole machine (4 threads, was unlimited → measured 462–984 % CPU per process). | G7 | `tests/test_406::test_tach_nguon_ra_du_BON_stem` runs **real demucs** with **no marker, no env guard, no skip**. There is no `pytest.ini`/`pyproject` pytest config in the repo at all, so no `heavy` marker exists to hang isolation on, and `tools/test_nhanh.py::TEP_NOI_TIEP` serialises only three files — none of them this one. It runs during a gate run on a box **that is serving production**. ⚠️ **Corrected in the Phase 05 review:** I first wrote that the gate uses `-n auto` = 20 workers. It does not — `gate.py:490` passes `ngan_sach_loi() = cpu_count() - 6` = **14**, and `test_394:324` pins that `-n auto` cannot return. I had read a comment describing the *old* mechanism as current state; session `lttstudiosapp-73` caught it. The gating decision stands, for a smaller reason: a real ML model still loads weights and takes the machine's spare CPU mid-measurement. | 04 |
| V4-R05 | **P0** | G7 / G8 | **Test and production disagree about the device.** Dev/test torch is `2.11.0+cpu`; `C:\LTTPlatform\venv` is `2.11.0+cu128` with 2 CUDA devices. Every demucs/ASR measurement taken in this tree is a **CPU** measurement that says nothing about production, and `test_406:378` carries a guard that deliberately fails on a CUDA machine to force the VRAM measurement — it will fire the moment anyone runs the suite with the production interpreter. `asv_gpu` declares 4 000 MB for `audio_prepare` marked *CHUA DO* ("not measured"). | 04 / 13 / 24 |
| ~~V4-R06~~ | **CLOSED (Phase 05)** — and it was worse than recorded: two further sites existed, one with no cap at all | G18 | Three full-file `Path(...).read_bytes()` calls on **media** purely to checksum: `giai_doan_media.py:94`, `giai_doan_am_thanh.py:87`, `giai_doan_chep_loi.py:124`. `V4_RESOURCE_CPU_GPU_POLICY` calls this out by name — stream the hash. At the current 90 MB cap it is survivable; the moment V4-R01 is fixed and real videos arrive it is not. | 05 / 13 |
| ~~V4-R07~~ | **CLOSED (Phase 12)** — `EDIT_PLAN` inserted before `CONTENT_PROCESS`, which now declares `sau=(EDIT_PLAN,)`; every paid stage is downstream of the visual decision, and `doan_giu_lai` keeps cut segments out of the dubbing work list. | G10 | Expensive-work ordering is **inverted** relative to V4. `pipeline.CHUOI` runs `content_process` (paid LLM translation of the whole transcript) at position 4, with no `EDIT_PLAN` and no `VOICE_BIND` anywhere. V4 requires the cut list frozen *before* translation and the voice bound *before* final adaptation. This is a chain re-ordering, not a new stage bolted on. | 12 / 14 |
| V4-R08 | **P1 — partially addressed (Phase 08)**: `ai.cua_so_ngu_canh` now reads the real per-model window (text 131 072 vs vision 65 536) instead of assuming one ceiling. ⚠️ Still open: the registry's declared window is higher than the 28 262 measured in `docs/audit_ltt_llm/STATE.md`; Phase 11 must re-measure before packing frames. | G9 | `ltt_llm_vision` exists and is public (`apps/ltt_llm/features.py:40` -> `qwen38-vision`), so scene understanding is a **reuse**. But its real context ceiling is far below the text alias — `docs/audit_ltt_llm/STATE.md` records `ltt_llm` 88 555 vs `ltt_llm_vision` **28 262** tokens after F-02 was closed. Frame batches must be sized against 28 K, not against the text model, or Phase 11 discovers it as a 413 at runtime. | 11 |
| V4-R09 | P1 | G13 | `platform_core.media.detect_gpu_encoder()` exists and is careful (NVENC minimum-size trap already handled at `media.py:174`). ASV never calls it, because MVP v1 froze *stream-copy only* (D-ASV-03) — correct then, insufficient for `smart_localize`, which must re-encode at cut points. | 17 |
| V4-R10 | P2 | G1 | Three baseline gate failures (`test_362` ×2, `test_82`) **can never pass inside a linked worktree** (V2's RISK-14-02) and this repo's own tooling creates linked worktrees. Do not spend time on them; count them as environmental. | — |
| V4-R12 | P2 | G16 | `MVP_CONTRACT.md` §6 freezes **four** user settings; `routes.py:134-135` exposes **two** (`che_do`, `giong_id`). `keep_background` and `background_gain_db` were contracted and never surfaced. Found in Phase 01, owned by Phase 21. | 21 |
| V4-R11 | P2 | G4 | `enabled=False` does **not** close a route — `mount_all` mounts every error-free router. V2 fixed this with an explicit flag gate placed **before** `require_login` (after it, a closed route still 303s to `/login` and thereby admits it exists). Any V4 route added must keep that ordering. | 21 |

## External evidence pending

| Item | Why unavailable | What closes it | Blocks |
|---|---|---|---|
| Real GPU demucs/ASR resource ledger | dev interpreter is `torch+cpu` | run the profile under `C:\LTTPlatform\venv` (read-only), or install cu128 into the test env | G7, G8, G18, G24 |
| Multi-process invariants (I1/I18) | `test_214`×7 + `test_73` skip without `LTT_TEST_DATABASE_URL` | a scratch PostgreSQL DB whose name contains `test`; PG is already live on 5432 | G4 |
| Live `ltt_llm` / `ltt_llm_vision` call | `test_334::_health` skips without `LTT_LLM_TOKEN` | operator-supplied token | G9, G17 |
| Real LTT Voice synthesis quality | never measured in V2 either (Phase 12 report) | a real run against `LTTStudioVoice` on :8120 | G11, G12, G17 |
| Representative real customer videos | none in-repo | operator-supplied fixtures, both presets | G17 |

## Phase history

| Phase | Gate | Report |
|---|---|---|
| 12 Edit plan + MVP presets | **PASS** | 🔴 **Closes V4-R07 (P0)** — a chain change, not a new file. V2 ran the paid translation stage at position 4 with **no edit plan in existence**, i.e. it translated and paid for dialogue belonging to scenes that would be cut. `EDIT_PLAN` now sits between `TRANSCRIBE` and `CONTENT_PROCESS` (chain 9 → 10, runs end to end through the real queue), and invalidation is one-directional: changing the plan reaches `content_process → qc` and **nothing upstream** — re-running a paid transcription because of a picture decision is the same waste pointing the other way. `localize_preserve_picture` never cuts **and never even reads the VLM's opinion**: an unreachable opinion cannot be opened by accident. 🔑 Dialogue scenes need 0.85 to remove vs 0.65 — a silent scene cut by mistake loses a shot, a dialogue scene cut by mistake **breaks the story**. 🔴 **The empty-video guard had never once been the rule that saved us**: the 50 % floor always fired first, so mutation removed the guard and the suite stayed green. The new fixture makes the plan **lie about its own ratio**, which is exactly what a ratio bug would do — and there that guard is the last thing between the customer and an empty file. ⚠️ A **second instance of the flaky test I created in Phase 07** surfaced here and was fixed. 28 tests, 8/8 mutations red, 432 passed. ⚠️ Debt: the stage passes empty `hieu_canh`, so `smart_localize` keeps everything for lack of evidence — correct, but not yet smart. | [`reports/12_REPORT.md`](reports/12_REPORT.md) |
| 11 VLM scene understanding + ContentProfile | **PASS** (real-VLM smoke unavailable, stated) | 🔑 **The debt Phases 06 and 08 both recorded is paid here** — `ai.goi_tinh_tien` gates the budget *before* sending and writes the ledger on **all three** outcomes; writing only on success is how an ambiguous dispatch disappears from the books at exactly the moment it must be visible. 🔴 **A real conflict between Phase 06's rule and the platform's reality**: `cong_vlm.SuDung.dang_tin` is False when upstream returns no usage, but a `DA_GIAO` record requires a unit and quantity > 0. Both shortcuts lie — `so_luong=0` claims it was free, `TU_CHOI` claims it never ran. ⭐ New unit `LUOT`: **one delivered call** is measurable and true, and it does not pretend to know a token count. Two calls, not one — a bad scene must not ruin the profile, and a profile edit must not re-read every scene. ⛔ **A malformed response is not a successful artifact, and it still costs**: a scene *read and returned garbage* differs from one *never read*. That distinction reappears in the error table — `ai.LuocDoSai` is `TAM_THOI` (parse failed at transport, models are stochastic) while `HieuCanhError` is `NGUOI_DUNG` (JSON parsed and **carries a wrong value**; the model ran and was charged). Same shape, different layer, opposite fate. 35 tests, 10/10 mutations red, 434 passed. | [`reports/11_REPORT.md`](reports/11_REPORT.md) |
| 10 Scene segmentation + frame sampling | **PASS** (benchmark deferred, stated) | Built rather than extracted — the proven engine lives in the **read-only** reference tree and `taoclipngan`'s copy is under gitignored `vendor/`. 🔴 **Memory dictated the shape**: a 40-min 1080p source is ~60 000 frames (~350 GB raw), so `ffmpeg`'s `select='gt(scene,T)'` does the comparing and ASV reads only timestamps — **no pixel enters Python**, pinned by AST; `-f null -` writes nothing; one ffmpeg call for the whole video, pinned by counting `subprocess.run`. Frame cap sits **where frames are produced** (60/run, 2/scene, 512 px long edge) because the vision window is 65 536 tokens — a cap after the spend is a cap in the wrong place. 🔴 **The even-distribution test caught a real bug in my first draft**: it gave one frame to each of the first 60 scenes and **nothing to the last 40** — the exact tail-truncation its own docstring forbade. 🔴 And the merge-vs-drop test **could not tell the difference** until mutation showed it: the fixture put short scenes at the *start*, where a separate head-merge rule closed the gap anyway; a short scene in the **middle** gets no such rescue. 28 tests, 6/6 mutations red, 376 passed in regression. ⚠️ Debt: `NGUONG_DOI_CANH = 0.4` unmeasured on real footage (written down as such, and it is inside the fingerprint); wall-clock CPU profile needs a representative source file the repo does not have; persisting `SceneIndex` as `AsvAsset` belongs to Phase 11, its first consumer. | [`reports/10_REPORT.md`](reports/10_REPORT.md) |
| 09 LTT Voice boundary + voice binding | **PASS** (2 reqs deferred to 15, stated) | **V4-R14 (P0) closed**: `giong_mau`'s 20 sample voices classified on three axes existed all along and were simply **not exported** — seven additive read-only names on both sides. `loc` is exported rather than letting ASV walk `DANH_SACH`, because a filter is a **rule** and two copies of a rule drift. 🔑 **AUTO_MATCH defers, it does not default.** With no ContentProfile it resolves to `CHUA_RANG` — a valid state that is neither failure nor voice — and `ma_giong()` **raises** on it. V2 did the opposite (`routes.py:135` `giong_id: str = Form("")` → empty took the default), which `ADR-V4-001` D-V4-04 forbids by name: a default **reads nothing from the video**. Deferring beats a placeholder because Phase 14 sizes sentences against the real voice's reading speed, so a temporary voice yields an adaptation that must be redone. Ownership is **not** re-implemented — `features.giai_giong` already filters `owner_id`, handles the shared store and drops inactive voices; getting the first wrong means a customer's video read **in someone else's cloned voice**. `rang_giong.py` synthesizes **zero milliseconds**, pinned by AST. ⛔ Reqs 1–2 (per-segment synthesis service) deferred to Phase 15 — the structural blocker (`asv_stage` holds one `job_id`) was removed by Phase 05's `AsvWorkItem`, but the brief's own index puts synthesis at 15 and the billing prerequisite is still unproven. 22 tests, 6/6 mutations red, 540 passed in regression. | [`reports/09_REPORT.md`](reports/09_REPORT.md) |
| 08 LTT AI text + vision boundary | **PASS** (1 debt stated) | 🔴 **A live bug, and ASV is its third victim.** `dieu_phoi.goi`'s own docstring warns that `{"ltt_llm": "ltt_llm"}` is wrong — `ltt_llm` is the app's public **alias**, not a model id, so `chon_key` raises and the dispatcher **silently skips the only provider**. Verified against the registry rather than assumed: `models_for("ltt_llm")` returns `qwen38-api` + `qwen38-vision` only. `dich_thuat.py:45` held that exact line; the two earlier victims are named in that docstring, and ASV went unnoticed because the stage is still a fake engine. ⭐ **An example in a docstring is code that people copy** — when it is wrong it is never wrong alone. New `ai.py`: six typed operations, model chosen **semantically** (`can_thi_giac` → `providers.model_capabilities`), token ceiling single-sourced from `ltt_llm.ngan_sach`, structured-output validation, prompt/schema version for fingerprints. Context windows differ — text 131 072 vs vision **65 536** — so a frame batch packed against the text ceiling is a 413 at runtime. 🔴 **Mutation found two holes in my own tests**: the ambiguity test was measuring the string fallback instead of the class-name branch, and the one-door guard locked `import platform_core.llm.dieu_phoi` but not `from platform_core.llm import dieu_phoi`. ⚠️ Also fixed a **flaky test I created in the Phase 07 unification**: making `do_tai=True` the default made three `test_431` cases read real CPU and change answer with load — green alone, red under `-n 4`. 28 tests, 7/7 mutations red. ⛔ Debt: nothing wires `su_dung.ghi` into `ai.goi` yet — no stage makes a paid call, and a ledger write on a path that never runs is a claim without a witness. Phase 11 is the first paid caller. | [`reports/08_REPORT.md`](reports/08_REPORT.md) |
| 07 ASR + diarization capability rebase | **PASS** | **Half the objective was already met, and saying so is the finding**: for ASR, `transcribe_file` was already declared, already the only name ASV touched, and already forwarded the platform-assigned card — so *"remove the private-path dependency"* had nothing to remove, and an AST test now proves that positively. The gap was diarization (V4-R13), closed with two additive lines on both sides. 🔴 **Exporting it surfaced a live defect older than Auto Scan**: `pyannote_runner.py:20` did `if torch.cuda.is_available(): pipeline.to(torch.device("cuda"))` — it took the first card torch saw, **ignoring `gpu_lease` entirely**, while `manifest.py:51` declares `gpu_vram_mb=2000` so the platform *believed* it was arbitrating. Fixed by reusing the owner's own `_env_ghim_gpu`, adding no second arbiter. ⛔ `SCHEMA_BAN_GHI` deliberately **not** bumped — `kiem` compares by equality, so a bump invalidates every stored transcript and the customer pays for a second ASR pass they never asked for; speaker fields are additive, plus one explicit `phan_vai` with three values so Phase 09 can tell **no evidence** from **evidence that found nobody**. Diarization runs only for `AUTO_MATCH`; missing or malformed settings mean **do not spend**. ⭐ A Phase 02 test failed *forward* — it pinned the opposite state and carried the fix instruction in its failure message; a test pinning a temporary state must say what to do when it stops being temporary. ⚠️ Also relinked the ASV alembic chain after the trunk merge created **two heads** (the merging side rebases). 18 tests, 7/7 mutations red. | [`reports/07_REPORT.md`](reports/07_REPORT.md) |
| 06 Billing usage + budget foundation | **PASS** (1 debt stated) | `AsvUsage` + migration `c81d3f5a90e7` + `su_dung.py`. 🔑 **The ledger is not a second money path** — money still flows through exactly one column (`AsvWorkItem.credit_actual`); the table *explains* it, and `doi_soat` pins `item.credit_actual == Σ delivered rows`, called from `quyet_toan` **before** the charge. Three of the eight requirements were **already implemented** (child jobs use `jobs.submit`, exactly-once aggregation, no price recompute) — the honest output for those is three AST pins, not new code. 🔴 Four bugs found in my own work, each by a different mechanism: `db.rollback()` on a duplicate dispatch id destroyed **the caller's whole transaction** (→ SAVEPOINT); a reconciliation guard would have alarmed on all pre-existing rows; `test_427` caught `su_dung.py` **missing from the rebase map** (8 ADD → 9); and an integration assertion of mine encoded a contract the platform does not have — `credit.so_da_giu` returns **200** after settlement because it sums historical `CREDIT_HOLD` entries, not "still held". ⭐ Counting hold *entries* proves "one billing owner"; the sum never could, since one hold of 200 and two of 100 are indistinguishable. ⚠️ Also capped `demucs_runner` at 4 torch threads — the black box measured twelve of them at **462–984 % CPU each**, and that is precisely where `-n 6` cannot reach: it counts pytest workers, not what each worker spawns. 38 tests, 7/7 mutations red. | [`reports/06_REPORT.md`](reports/06_REPORT.md) |
| 05 DAG + item checkpoints + large input | **PASS** (2 sub-items deferred to 15, stated) | `AsvWorkItem` + migration `a4c17f9b62d0`; durable upload replaces `await video.read()`. 🔴 **`upload_sessions._SLUG` rejected 7 of 19 apps on this tree** (`ltt_llm`, `ltt_voice`, `prompt_ai_ommi` + the 4 ASV apps; on the main tree at `dac2406`, which has not merged the ASV apps, the same defect counts **3 of 15** — session `lttstudiosapp-73` measured that and the two numbers reconcile exactly) — no underscore allowed — including `ltt_voice`, which is *released and selling*. Invisible because the only caller (`autosubvideo`) is one of the few slugs without one, and `conftest` uses `APP_THU_SLUG="appthu"`: the suite exercised that path thousands of times, never once with a real slug. Widened by one character, purely additive, both directions pinned. 🔴 **Two more whole-video-into-RAM sites** beyond the one Phase 00 found — `_duong_doc_duoc` (no cap at all, and the durable path admits 2 GiB) and `kiem_hop_le`/`kiem_toan_ven` (every artifact of every run, `final.mp4` included). All three share a shape: **they never produce a wrong answer**, so the tests measure the largest single read, not the result. ⭐ Probing without downloading needed **zero** new code — `media.is_remote_source` already existed and its docstring already named the cost. | [`reports/05_REPORT.md`](reports/05_REPORT.md) |
| 04 Regression shield + heavy-test isolation | **PASS** | Found **3 real-model calls with no guard at all** — 2 × demucs (`test_406`), 1 × faster-whisper (`test_407`) — in a repo with **no pytest config to hang a marker on**. Gated behind `LTT_TEST_NANG`, because a marker only filters when somebody types `-m`, and "somebody forgets" is exactly what hard-reset this machine twice. Added a ratchet over every `tests/test_*.py` so the fourth one cannot arrive quietly. ⭐ Three drafts were wrong first: `assign_speakers` is 12 lines of interval arithmetic (proximity is not evidence), three call sites reach a heavy function but raise before the engine, and the ini check flagged its own explanatory comment — **the third text-scanning detector this session to punish the prose documenting it**. ⚠️ Full gate not re-run; debt recorded above rather than folded into the green rows. | [`reports/04_REPORT.md`](reports/04_REPORT.md) |
| 03 Rebase classification + architecture ADR | **PASS** | **17 KEEP · 6 EXTEND · 7 REFACTOR · 8 ADD · 0 REMOVE** — the default is KEEP and the exceptions are argued. `ADR-V4-002` designs `AsvWorkItem` with `UNIQUE(run_id, stage, item_key)` and proves it is **not** a queue by naming the 8 columns that would make it one, with a detector that fires on a synthetic queue table and stays quiet on a legitimate checkpoint one. ⭐ Found two guards in `test_421` that read wider than they were: `glob` is not recursive (so the first `services/` directory would leave their view silently) and they never scanned the three executor apps — where a stray thread pool would do the most damage. Widened to `rglob` × 4 apps, with an assertion that the new file set is a **strict superset** so §1 cannot degrade into a re-run under a new name. | [`reports/03_REPORT.md`](reports/03_REPORT.md) |
| 02 Capability inventory + boundary freeze | **PASS** | 19 apps censused; every V4 need classified with a traced caller. **13 SUFFICIENT, 2 EXTEND, 6 ABSENT** — and no capability recommended as new code without proof of absence (an AST scan, not a text scan). 🔴 **The phase's real output is a retraction**: this platform already implements V4's "stable cross-app boundary" rule via `BE_MAT_CONG_KHAI` + `APP_DUOC_DUNG_APP`, enforced by a linter inside the gate. V4-R02 (P0) and V4-R03 are withdrawn. ⭐ And the thing that actually blocks Phase 09 is not willpower but schema: `speech.ltt` is a fine contract with the wrong granularity, because `asv_stage` holds one `job_id` and per-segment TTS needs many. Phase 05 unblocks Phase 09. | [`reports/02_REPORT.md`](reports/02_REPORT.md) |
| 01 Product contract supersession | **PASS** | `ADR-V4-001` supersedes `auto_scan_mvp_v1` §1/§4 by banner, not by rewrite. Contract now exists in three forms: prose, constants (`hop_dong_v4.py`), and 20 tests. 🔴 **The pack's stated reason for `vi` is factually wrong** — LTT Voice is bilingual (`lan_ngon_ngu.py:6`, `language: ["vi","en"]`). Decision kept, justification replaced, and a test now goes red on exactly the move a future session would make after reading the wrong reason. One strict-xfail RED target left for Phase 12. | [`reports/01_REPORT.md`](reports/01_REPORT.md) |
| 00 Provenance and bootstrap | **PASS** | HEAD identical to the pack's SHA (no delta). Baseline certified at `FAIL (1/26)` with **0 ASV-owned failures** — V2's 7 failures were 3 commits stale, `b027e08` merged the peer fixes. 11 V4 risks read from code, 5 of them P0. ⭐ The find that reorders nothing but explains everything: `ltt_voice` **already exports** a stable `ToolSpec("speech.ltt")`; V2 bypassed it into `sidecar_client` only because `asv_stage` holds **one** `job_id` and per-segment TTS needs many. So Phase 09 is not unblocked by willpower — it is unblocked by Phase 05's `AsvWorkItem`. | [`reports/00_REPORT.md`](reports/00_REPORT.md) |
