# PHASE 05 REPORT — DAG, ITEM CHECKPOINTS, LARGE INPUT FOUNDATION

## Verdict

**PASS**, with two sub-items explicitly deferred to the phase that can test them (below).

## Source / HEAD

`phien/asv-v4` @ `9632e7b` (Phase 04) → `b3e5df7` (this phase, part 1) + part 2.

## Changed paths

| Path | Kind |
|---|---|
| `apps/auto_scan_video/tables.py` | **+ `AsvWorkItem`** |
| `alembic/versions/20260903_0300_asv_work_item.py` | new migration `a4c17f9b62d0` |
| `apps/auto_scan_video/features.py` | item API + roll-up rule + durable upload |
| `apps/auto_scan_video/assets.py` | `bam_tep`, `do_va_bam`, `nguon_soi_duoc`; streaming validate |
| `apps/auto_scan_video/giai_doan_{media,am_thanh,chep_loi}.py` | streaming hash / streaming copy |
| `apps/auto_scan_video/routes.py` | `POST /ve`; `/tao` prefers the durable path |
| **`platform_core/upload_sessions.py`** | `_SLUG` widened — see below |
| `locale/en/LC_MESSAGES/messages.{po,mo}` | 1 new string |
| `tests/test_429…`, `tests/test_430…` | new, 19 + 12 checks |

## The platform-core change, and the evidence that made it necessary

`V4_OPERATING_CONTRACT` C requires proof that an app-level fix is insufficient before touching
`platform_core`. Here is the proof.

`upload_sessions.create()` validates the caller's slug against
`_SLUG = ^[a-z0-9][a-z0-9-]{0,63}$` — **no underscore**. Run against the real registry:

```
DUNG duoc: agent anhnoibo autosubvideo chataistudio nexus qualitylab taoanh
           taoclipngan taovideo thumbnail upscalevideo vps
BI TU CHOI: asv_gpu asv_media asv_voice auto_scan_video ltt_llm ltt_voice prompt_ai_ommi
```

**Seven of nineteen apps cannot use the platform's durable upload path at all** — including
`ltt_voice`, which is `lifecycle="released"` and selling today.

It cannot be fixed at app level: the slug comes from `AppManifest.slug`, and for Auto Scan it
is load-bearing (`table_prefix="asv"`, route prefix, and `catalog_parent` on three executor
apps all key off it). And it is not a deliberate restriction — `AppManifest` places no such
limit, and seven apps already use underscores.

**Why nobody hit it before**, which is the more interesting half: the only app calling
`upload_sessions` is `autosubvideo` — one of the few slugs *without* an underscore — and
`tests/conftest.py:71` sets `APP_THU_SLUG = "appthu"`. So the whole suite exercised this path,
thousands of times, and never once with a real slug.

### Latent, not live — measured, because a peer asked the right question

Session `lttstudiosapp-73` pointed at a second caller I had missed:
`server/api/uploads.py:111` passes `app_slug=tool.app_slug` from the **public API**, where
the slug is derived from the tool the customer called rather than typed by a developer. If any
tool belonging to those three apps took an upload, this would be a defect customers hit today,
not a latent one.

Measured against the real registry — every `params_schema` field of every declared tool,
through `public_api.media.media_kind`:

```
14 tool-fields accept an upload, across 6 apps:
  anhnoibo image.ltt · autosubvideo video.subtitle · taoanh image.generate/batch_generate
  taoclipngan video.short_clips · taovideo video.generate · upscalevideo video/image.upscale
Belonging to an app with an underscore: NONE
```

`ltt_llm` (`text.chat`), `ltt_voice` (`speech.ltt`) and `prompt_ai_ommi`
(`text.prompt_package`, `story.storyboard`) declare **no** media parameter, so
`create_upload` rejects the field at `_kind_for_tool` before `upload_sessions.create` is ever
reached. ⇒ **Latent.** No customer is hitting it.

⚠️ It is still worth fixing now, and `ltt_voice` shows why: it already has a
`ltt_voice.enroll` job type — voice cloning — with no ToolSpec yet. The day that is opened on
`/api/v1` it needs an audio upload, and it would fail with "Ứng dụng upload không hợp lệ" for
a reason nobody would look for in a regex about slugs.

The fix widens the character class by one character and is **purely additive**: every
previously-valid slug is still valid. `test_429` §3 pins both directions — every app in the
registry must be accepted, and `""`, `-abc`, `_abc`, `ABC`, `a/b`, `a.b`, `a b`, 65 chars must
still be rejected. `tests/test_173_upload_sessions.py` (the owner's own suite) stays green.

## Three places that loaded a whole video into RAM — two of them new findings

Phase 00 found the one at `routes.py:155`. Reading the code properly found two more, and the
second is worse than the original:

| Site | What it did | Why it is worse than it looks |
|---|---|---|
| `assets.bam(Path(x).read_bytes())` ×3 | hash by materialising the file | the one Phase 00 found |
| **`giai_doan_media._duong_doc_duoc`** | `dich.write_bytes(f.read())` when storage is R2 | **no cap at all.** The route stops at 90 MB; this does not, and the durable path admits 2 GiB — all of which goes through that one line |
| **`assets.kiem_hop_le` / `kiem_toan_ven`** | `_doc_het` for **every** artifact | runs on every integrity audit of every run, `final.mp4` included |

All three fail the same way: **they never produce a wrong answer.** The hash is correct, the
fingerprint matches, the check passes — the machine just starts swapping when two runs
overlap. A defect with no wrong output is one that survives review indefinitely.

So the tests measure **the largest single read**, not just the result. A test that only
compared hashes would stay green if somebody rewrote `bam_tep` as
`bam(Path(d).read_bytes())` — same output, none of the reason it exists.

For `kiem_hop_le` the split is deliberate and asymmetric: media streams, JSON does not.
`json.loads` genuinely needs the whole text; ffprobe needs a *file*, so materialising it in
RAM serves no check at all.

## Probing without downloading — again, a reuse

`assets.nguon_soi_duoc` returns `local_path()` or `url_for()`. `nhap_media.soi` already passes
its argument straight to `ffprobe`, which reads a presigned URL with range requests, so **not
one line of the probe path changed**.

`platform_core/media.py:81 is_remote_source` already documented the exact cost this avoids:
*"a 2 GB video through the tunnel just to read one number."* The capability existed; Auto Scan
was not using it.

## Why the durable path does not call `upload_sessions.promote`

`promote()` requires `credit.so_da_giu(db, job.id) > 0` — it assumes the hold sits on a **job**.
Auto Scan holds **once on `run.id`**, and every child job is priced 0 (ADR-001 D4), so that
condition can never hold here.

So `tao_run_tu_ve` uses `kho.promote()` — the same `platform_core` API `assets.py` already uses
for artifacts. Nothing is duplicated: the ticket, quotas, magic-byte check and ownership
resolution all still come from `upload_sessions`. Recorded in the function's docstring as a
**real semantic mismatch between two billing models**, not a shortcut, so that if platform-core
later grows a promote path for "the holder is not a job", this moves to it.

## Two sub-items deferred, and why that is not a dodge

Prompt 05 lists seven required items. Five are done. Two are **not**, and pretending otherwise
would be the kind of green light this project keeps finding:

| Item | Status |
|---|---|
| 3. invalidation propagation for **item-level** repair | **deferred to Phase 15.** Stage-level invalidation exists and is unchanged (`jobs._vo_hieu_giai_doan_da_lech` + `pipeline.ha_nguon_cua`). No stage produces items yet, so an item-invalidation path written now would be a guard over an empty set with no way to prove it fires — exactly what `test_401` warns about. |
| 7. verify no false DONE at **item** level | **deferred to Phase 15**, same reason. The stage-level rule (`_thu_ket_qua_job_con` refuses to infer `job done ⇒ stage succeeded`) is intact and tested; items must follow it, and that is testable only once a stage writes items. |

Item 2 (evolve the chain to a fixed DAG) needed **no change**: `pipeline.CHUOI` is already a
DAG. `GiaiDoan.sau` is a tuple of predecessors, `ke_tiep()` returns a *list*, and
`timing_align` already depends on two upstreams. `test_427` §3 pins that `ha_nguon_cua` reads
dependencies rather than chain order, using a synthetic two-branch chain — so the day V4 adds
the scene/VLM branch, the difference is asserted rather than assumed.

## Tests and commands

```bash
python -m pytest tests/test_429_asv_v4_dau_vao_lon.py -q      # 19 passed
python -m pytest tests/test_430_asv_v4_don_vi_viec.py -q      # 12 passed
python -m pytest tests/test_63_lop_csdl.py -q                 # 17 passed (up->down->up)
python -m pytest <VONG_NHANH + 429 + 430 + 173> -q            # 184 passed, 1 xfailed in 20.68s
python tools/gate.py --quick --phien asv-v4                   # RESULT: PASS
```

### Two in-scope failures, found and fixed here

1. **`kieu xuong dong` FAIL** — `pathlib.write_text` on Windows rewrote `routes.py` and
   `upload_sessions.py` from LF to CRLF (65 + 24 lines). Rewritten with `newline="\n"`.
   The gate's own message explains the stake: a wholesale rewrite makes `git diff` unreadable
   *and* trips the tree-changed detector.
2. **`dich thieu ban EN` FAIL** — one new user-facing string. Added to the `.po` by hand and
   recompiled, per the repo rule against running `i18n.py trich` for a couple of strings
   (it reorders the whole file).

## Self-review findings (hostile pass)

**Did I create a second queue?** No. `test_430` pins both halves: the table carries none of the
eight claim/lease/priority columns (checked against SQLAlchemy metadata, a *different* path
from `test_427`'s AST check — one catches a commented-out column, the other catches one added
via a mixin), and `jobs.py` — the only place work is dispatched — does not mention the table
at all. A table with no `claimed_by` can still be used as a queue if something queries it to
pick work.

**Can retry double-charge?** This is the one surface where it could, and it fails silently: the
run still finishes, the video is still right, the ledger still balances. Only the number is
wrong. So `_kiem_khong_tinh_hai_lan` **raises**, and it runs inside `tong_da_dung`, which means
every path that reads the money — `quyet_toan` included — goes through it. `test_430` proves
that by calling `quyet_toan`, not by reading its source.

**Can user A reference user B's upload?** `upload_sessions.owned()` filters on `user_id` **and**
`app_slug` inside the query, so a foreign `upload_id` returns no row and surfaces as "not
found" — it cannot become a permission error the caller can distinguish. Pinned by
`test_ve_cua_NGUOI_KHAC_khong_dung_duoc`.

**Did I break old runs?** No column changed type or meaning. A run with no items reads exactly
as before (`test_giai_doan_KHONG_co_don_vi_van_tu_ghi_chi_phi_nhu_cu`), and a run created
before this migration has no item rows — a valid state, not a missing one.

**Is the multipart path still a hole?** It is bounded and kept on purpose (Prompt 05 item 4
allows "a tiny dev upload path only if explicitly bounded"): the 90 MB cap is unchanged, and it
is the only path that works when storage is `LocalStorage` — i.e. on a dev machine and in the
whole test suite, because a local backend issues no presigned PUT. The durable branch is
ordered **first** in the handler, and `test_route_tao_UU_TIEN_duong_ben_vung_khi_co_ca_hai`
asserts that ordering by AST — otherwise a client sending both would be silently pulled back
onto the capped path.

**Did I widen scope?** One platform-core line, argued above with registry evidence. Everything
else is inside `apps/auto_scan_video`.

## Risks / external evidence

| Item | Status |
|---|---|
| 500 MB-class real upload through a real presigned PUT | **not run.** This tree's storage is `LocalStorage`, which issues no presigned URL. The R2 path is covered by `_KhoR2Gia` — a fake shaped like R2 (`local_path` returns `None`) specifically so the tests exercise the presigned branch rather than the local one. Real-R2 evidence belongs to Phase 22 E2E. |
| Full `tools/gate.py` | still outstanding from Phase 04 — a peer session was deploying to production on this machine. |

## Exit gate proof

> *PASS when V4 can represent DAG+segment checkpoints and accept real-sized durable input
> without creating a second queue or breaking old runs.*

| Requirement | Evidence |
|---|---|
| represent segment checkpoints | `AsvWorkItem` + migration, `UNIQUE(run_id, stage, item_key)`, 12 tests |
| represent the DAG | already true; pinned rather than rebuilt |
| durable real-sized input | `POST /ve` → presigned PUT → `confirm` → probe-in-place → `promote`; cap 2 GiB, file never in app memory |
| no second queue | two independent checks + the positive check on `jobs.py` |
| old runs unbroken | additive migration, `downgrade` = `drop_table`; no-item runs read as before |
| owner + integrity server-side | `owned()` filters in-query; `confirm()` checks size + magic bytes |

**PASS → next: Phase 06 (billing/usage foundation).**
