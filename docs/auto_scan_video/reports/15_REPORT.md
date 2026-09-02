# PHASE 15 REPORT — Renderer Integration

**The phase where a test written to check the renderer found a seven-phase-old debt.**

## Entry evidence
- starting SHA: `8e9d846`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 14 closed at `FAIL (2/26)`, 7 failures all owned elsewhere
- allowed change scope: renderer service/runtime executor, extraction from
  DUNGVIDEO/Cut_only, tests

## 1. Comparing the three existing renderers (item 1)

|  | `DUNGVIDEO-FULL/engine/assemble.py` | `Cut_only/…/ffmpeg_edit_cutonly.py` | `apps/autosubvideo/burn.py` |
|---|---|---|---|
| job | cut clips + xfade + re-encode | replace audio, keep picture | burn subtitles |
| video | **re-encodes** libx264 | **`-c:v copy`** | re-encodes (unavoidable) |
| multi-layer timed audio overlay | no | no | no |
| progress | none | 15 s heartbeat from a thread | **`-progress pipe:1`, parses `out_time`** |
| cancel | no | no | **yes** — `on_progress` raising kills it |
| invocation | `subprocess.run`, argv list | `subprocess.run`, argv list | `Popen`, argv list |
| temp-then-rename | no | no | no |

**None was reusable as-is**, and not for quality reasons:

- `assemble.py` is the **cut** path, which `MVP_CONTRACT.md` §4 deferred (D-ASV-02).
  What survives is its encode policy: `-c:a aac -ar 48000 -ac 2` and `-movflags +faststart`.
- `replace_audio` has the right **shape** — replace audio, keep picture — but takes **one**
  pre-mixed audio file. We have N layers to place at N different timestamps, so the hard part
  is not in it.
- `burn.py` has the two things the others lack (real progress, cooperative cancel), so the
  **execution** pattern comes from there.

⇒ Policy from the first, shape from the second, execution from the third. The timed multi-layer
mix is new.

**Parity fixture (item 2)** is `test_414::PARITY_DI_SAN` — six flags pinned against the legacy
shape. It deliberately does not compare output *files*: those depend on the ffmpeg build and do
not reproduce across machines. It compares **decisions**, so changing one is possible but must
be deliberate.

## 2. `-c:v copy` decides the rest of the phase

The picture is never touched. Two real consequences:

1. **No GPU.** Prompt 15 item 6 says claim one only if the renderer actually uses it. Copying a
   video stream and encoding AAC is CPU work, so `pipeline.CHUOI` puts RENDER on the
   `asv_media` (ffmpeg) lane with no `tai_nguyen` declared. `test_414` pins that, because
   "helpfully" adding a `ctx.gpu_env()` later would hold a scarce slot to not use it.
2. Fast, and lossless — the customer's picture comes out at the bitrate it went in.

## 3. The bug this phase actually found

`test_415::test_doi_cach_dung_lenh_thi_van_tay_PHAI_doi` bumps `PHIEN_BAN_KET_XUAT` and re-runs.
The fingerprint **did not change** — meaning a fix shipped to the renderer would never run,
because every re-run would serve the cached file.

The cause was not in the renderer. `thi_hanh.van_tay` hashed
`(stage, contract, settings, dau_vao)` and **no engine version at all** — and its own docstring,
written in Phase 05, recorded the debt:

> *"Phase 08+ **must** add them — without them, upgrading the model will silently reuse the old
> result."*

That debt passed through **seven phases** unpaid. Not because anyone skipped a read: because
nothing measured it. A comment saying "X must be done" does not do X, and cannot tell you X is
still undone.

Fixed by `thi_hanh.phien_ban_engine(stage)`, which every stage now contributes to. Each stage
already had a version constant — `PHIEN_BAN_CHUAN_HOA`, `PHIEN_BAN_TACH`, `PHIEN_BAN_MA`,
`PHIEN_BAN_LOI_NHAC` + provider/model, `PHIEN_BAN_GIONG`, `PHIEN_BAN_THOI_GIAN`,
`PHIEN_BAN_BAN_DUNG`, `PHIEN_BAN_KET_XUAT`. None of them reached the fingerprint.

⚠️ Stages without a real engine return `gia/0` rather than `""`. Returning empty would mean
"nothing here can invalidate a cache", which is the same bug one level down. `test_416` pins the
**set** of dummy-engine stages (`{qc}`), so Phase 18 cannot replace QC's engine without changing
its version — which is exactly the moment old dummy results must stop counting as cache.

⭐ The generalisation matters more than the fix. A test that only checked RENDER would have left
the other eight stages rotting in the same way. `test_416` parametrises over `pipeline.CHUOI`,
so the invariant covers stages that do not exist yet.

## 4. Cancel had to be rebuilt, not copied

`burn.py` cancels by having `on_progress` raise — which only works **while ffmpeg is printing
progress**. A render stuck somewhere that prints nothing (reading a corrupt file, for example)
cannot be cancelled that way.

Here a separate watchdog thread polls `hoi_huy` and the deadline every 0.5 s, independent of
whether ffmpeg says anything.

⚠️ The test for this was wrong first. It used `-preset veryslow` on a small video and failed:
ffmpeg finished before the cancel could land. A control test whose result depends on CPU speed
is measuring CPU speed, not control. Rewritten with `-re`, which forces real-time input reading,
so the command deterministically runs 30 s on any machine.

## 5. Order that cannot be reshuffled: temp → ffprobe → promote

- writing straight to storage leaves a half-file on interruption, and a half-file in storage
  **looks exactly like a real result** (item 10);
- promoting before probing publishes something nobody checked;
- probing without writing to temp leaves nothing to probe.

`kiem_tep_ra` is where "ffmpeg returned 0" and "there is a usable file" stop being the same
claim. It rejects: empty file, missing video stream, missing audio stream, and duration off by
more than 1 s. That last one matters most — a dubbed video of the wrong length is one where
audio and picture are out of step, i.e. broken at the exact thing this product sells.

Diagnostics are redacted before storage (item 9): temp paths carry the machine layout and the
Windows username, and a diagnostic record is read by someone who does not own that file. File
**names** are kept, because that is what makes the record useful.

## 6. Exit gate

> *A stored manifest alone can regenerate a validated final media asset.*

`test_415` proves it through the real queue and real workers — calling
`giai_doan_ket_xuat.chay` directly would skip the very thing being claimed:

- **`test_RENDER_that_su_sinh_ra_mot_mp4_PHAT_DUOC`** — pinned by `ffprobe`, not by
  "the stage reported succeeded". The dummy engine also reported succeeded, and did so for ten
  phases. The output is h264 + aac, 48 kHz stereo, non-zero duration.
- **`test_render_lai_KHONG_danh_thuc_mot_giai_doan_thuong_nguon_nao`** — delete the render
  output, re-run, and every other stage's `(status, fingerprint)` is byte-identical. CONTENT and
  VOICE especially: re-running them is paying twice for one translation.
- **`test_render_hong_KHONG_de_lai_ket_qua_dang_do`** — a forced failure leaves no key and no
  `AsvAsset` row.
- **`test_thieu_mot_tep_tieng_thi_DUNG_TRUOC_khi_ton_suat_render`** — with one voice file gone,
  ffmpeg is never invoked at all.

⚠️ That last test first stopped the chain at the wrong place, and the fixture reset was wrong
twice: `outputs=None` violates NOT NULL (and becomes the JSON string `'null'`, not SQL NULL), and
lowering a stage to `pending` does **not** wake the coordinator — `advance` only re-enqueues
while the run is alive, and this run had reached `done`. The first symptom was an **empty**
fingerprint, i.e. RENDER never ran, which reads at a glance like "ran and produced the wrong
answer".

## 7. Guards that caught their own author — fourth occurrence

`test_414::test_khong_bao_gio_shell_true` had both a substring scan and an AST check. The
substring scan went red on `ket_xuat.py`'s own line saying it does not use `shell=True`.

Dropping the substring branch does not weaken the guard, which is the point worth keeping: a
string in a comment does not execute, while the AST sees every real call — including
`shell=<variable>`, which a substring scan never catches. Verified firing in five directions.

## 8. Exit evidence

`python tools/gate.py --phien asv` → **FAIL (3/26)**.

ASV-owned tests: **279 pass**, including under `-n 8`.

Failures, all traced, none in this phase's work — the same seven as Phase 14 plus the
i18n step:

| failure | cause | owner |
|---|---|---|
| `chuoi chua dich` (781 vs 774) | `platform_core/public_api/dieu_khoan.py` (6) + `api_dieu_khoan.html` (1) | peer, `d14431f` |
| `test_147` / `test_60` layering | same file imports `apps.ltt_llm` | peer, `d14431f` |
| `test_211` / `test_155` | `voice_tu_dien` unclassified | peer |
| `test_82`, `test_362` ×2 | worktree-structural (RISK-14-02) | n/a |

⚠️ One self-inflicted gate failure was found and fixed rather than pinned: a `pytest.skip` in
`test_415` tripped the skip ratchet. The condition — "this run produced no voice files" — cannot
legitimately happen in a fixture that runs the whole chain, so it became an assertion. Pinning it
would have recorded a test that guards nothing.

## Debt carried out of this phase

- No render has been measured on a **real customer video**; all evidence is on 2–3 s fixtures.
  Duration tolerance (`LECH_THOI_LUONG_GIAY = 1.0`) is reasoned, not measured (RISK-15-01).
- `atempo` above ~2.0 needs chaining; the manifest caps speed at 1.15 so it cannot arise today,
  but a future timing model change would hit it silently (RISK-15-02).
