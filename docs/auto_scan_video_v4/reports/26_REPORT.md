# Phase 26 — Independent audit (read only)

**Verdict: `AUDIT_COMPLETE_WITH_BLOCKERS`.**

Read from source, not from STATE. No code, config or test was changed in this
phase. Five new findings, four previously recorded blockers re-verified from the
code rather than from the claims about it, and one STATE entry contradicted.

---

## Verdict basis

| | |
|---|---|
| P0 | 0 |
| **P1** | **4** — A26-01, A26-05, B22-01, B24-01 |
| P2 | 4 — A26-02, A26-03, B23-01, B25-01 |
| P3 | 1 — A26-04 |
| Missing external evidence | live model call, live LTT Voice synthesis, real customer footage |

`PASS_TO_REAUDIT` requires no blockers. Four P1 findings stand, and the pack's own
rule applies independently: **missing external evidence is not PASS**.

---

# NEW FINDINGS

## A26-01 · P1 · The translation stage's fingerprint contains no model identity

**Gate:** G3 (duplicate capability path), G4 (cache/invalidation)

**Evidence**

```
thi_hanh.phien_ban_engine("content_process")  ->  "noi_dung/1/ltt_llm/"
dich_thuat.PROVIDER_CHINH = "ltt_llm"
dich_thuat.MODEL_CHINH    = ""            <- empty
ai.model_cho(ai.CHUYEN_LOI_THOAI)         -> "qwen38-api"   <- what actually runs
```

`thi_hanh.py:105` builds the CONTENT_PROCESS engine version from
`dich_thuat.PROVIDER_CHINH` and `dich_thuat.MODEL_CHINH`. Phase 14 moved that
stage onto `ai.goi_tinh_tien`; `dich_thuat.dich_ban_ghi` has had **no callers**
since. So the fingerprint of the one stage that pays a model is derived from a
module that no longer performs the work — and the constant it reads is empty.

**Why it matters.** Phase 08 added engine versions to the fingerprint for exactly
one stated reason: *"nâng model lên bản mới sẽ dùng lại kết quả cũ, im lặng"*.
Today, switching the model changes nothing in the fingerprint, so nothing
invalidates: not the stage cache, and not `_vo_hieu_giai_doan_da_lech`. Editing
the dead constant, by contrast, *would* invalidate.

**Reproduction:** the four lines above, in a Python shell.

⚠️ **This is masked by B23-01 and would be un-masked by fixing it.** The stage
cache never returns a hit today, so a stale fingerprint has nothing to hand back.
Fixing the cache alone turns this into wrong output delivered from cache after a
model change. **The two must be fixed together, cache first or not at all.**

**Minimal fix:** derive the CONTENT_PROCESS engine version from
`ai.ban_do_model(ai.CHUYEN_LOI_THOAI)`, the live map. Consider deleting
`dich_thuat.py` in the same change, or the next reader will believe it runs.

## A26-02 · P2 · `AsvWorkItem.revision` is documented as a guard and never enforced

**Gate:** G4 — the gate names "revision safety" explicitly

**Evidence**

`tables.py:327` says of `AsvWorkItem`:

> `UPDATE ... WHERE revision = :r` biến cuộc đua thành một xung đột **nhìn thấy
> được** thay vì một bản ghi đè.

`features.cap_nhat_giai_doan` implements exactly that for `AsvStage` — a
`WHERE revision = :r` update that raises `XungDot` on mismatch. For work items
there is no such writer: `su_dung.danh_dau_xong` bumps `it.revision` with a plain
ORM assignment and flushes. A search for a guarded update on the item table
returns nothing.

**Why it matters.** The scenario the column was created for — an orphaned job
picked up by a second worker while the first is still alive — resolves as
last-write-wins, and the counter increments twice with nobody notified.

⚠️ Damage is currently limited by `UNIQUE(run_id, stage, item_key)` and by the
ledger's `UNIQUE(run_id, ma_dispatch)`, which is why this has never been seen. The
documented invariant is still not enforced.

**Minimal fix:** route item writes through a guarded update like the stage one, or
delete the column and the paragraph that promises it.

## A26-03 · P2 · The direct upload path still reads the whole video into RAM

**Gate:** G6 — *"production path does not `await read()` entire large video into
RAM"*

**Evidence** — `routes.py`:

```python
254:  du_lieu = await video.read()          # whole body into memory
257:  if len(du_lieu) > TRAN_TAI_LEN:       # ...then the size check
262:  run = features.tao_run_tu_tai_len(db, ..., du_lieu=du_lieu, ...)
        -> features.py: tep.write_bytes(du_lieu)   # same bytes, now also on disk
```

The 90 MB limit is applied **after** the allocation, and `tao_run_tu_tai_len`
holds the same bytes while writing a temp copy — the payload is resident twice.

⚠️ **STATE records V4-R01 as CLOSED (Phase 05).** Phase 05 closed the *checksum*
half (three full-file `read_bytes()` calls for hashing, now streamed). The
*memory* half named in the same risk — "the whole video is resident twice" — is
still open on this path. The durable path (`tao_run_tu_ve`) exists and is correct;
the direct path is what the form uses.

**Bounded, not unbounded:** Cloudflare cuts at 100 MB, so exposure is ~100 MB per
concurrent upload rather than unbounded. It is still an allocation made before the
decision to accept it.

**Minimal fix:** stream to the temp file in chunks and enforce the ceiling while
streaming, or route the form through the durable ticket path that already exists.

## A26-04 · P3 · Technical QC shares its spec constants with the producer

**Gate:** G14

**Evidence** — `qc.py:70-73`:

```python
LUFS_DICH            = tach_tieng.LUFS_DICH
DINH_THAT_TOI_DA_DB  = tach_tieng.DINH_THAT_DB
```

`am_master` aims at those same constants. So T4/T5 ask "did you hit the number you
aimed at" — which catches an implementation error and **cannot** catch a wrong
target.

**Proof that the shape is real, not theoretical:** Phase 24's chain aimed at
exactly the ceiling (-1.5 dBTP) and delivered -1.45 dBTP. The gap was found only
because the *measurement path* differed from the *production path* (AAC output vs
PCM master) — not because the check questioned the target.

**Minimal fix:** none required for the MVP; record it. A shared constant is
correct for "did the pipeline do what it was told"; a delivery spec is a different
document, and the day one exists, T4/T5 should read *that*.

## A26-05 · P1 · The customer-facing description of `smart_localize` promises what it cannot do

**Gate:** G16 — *"UI/product truth"*

**Evidence** — `gia.PRESET_BANG`, the text the customer reads:

> **Rút gọn có biên tập** — Bỏ bớt những cảnh ít nội dung để video ngắn lại. Vì
> phải ghép lại các đoạn được giữ nên hình ảnh sẽ được mã hoá lại — chất lượng
> gần như bản gốc nhưng không còn giống hệt từng điểm ảnh.

Measured (Phase 22, on a source containing a scene with **no dialogue at all**):

```
preset smart_localize   so_canh 4   so_giu 4   so_cat 0   so_co_bang_chung 0
```

The customer is told scenes will be removed, accepts a stated quality cost for it,
and receives a video of the same length that has been re-encoded for nothing.

⚠️ **Phase 21 named this exact defect class and shipped an instance of it in the
same phase.** Its report calls the empty voice option a "false feature" and
removes it, on the principle that the fix is *to stop offering something that does
not exist*. The preset description is the same thing at product level.

**Minimal fix (until B22-01 is done):** say what the preset does today — re-encode
without cutting — or hide it. Either is honest; the current text is not.

---

# PREVIOUSLY RECORDED BLOCKERS — re-verified from source

| id | P | verified how | still true |
|---|---|---|---|
| **B22-01** — VLM never wired into `EDIT_PLAN` | P1 | `giai_doan_ban_bien_tap.chay` passes `hieu = ()`; `ban_bien_tap._quyet_dinh_mot_canh` returns KEEP when `h is None` | yes |
| **B23-01** — stage cache has never returned a hit | P2 | `cache_dung_duoc` filters `f"/{van_tay}." in storage_key`; `dat_khoa` truncates to `DAI_VAN_TAY_TRONG_KHOA = 32`; stage fingerprint is 64 chars | yes |
| **B24-01** — hardware encoder unreachable | P1 | `asv_media` declares `requires=("ffmpeg",)` with no `gpu_vram_mb` -> `_vram_can` = 0 -> no lease -> `ctx.gpu_uuid` empty -> `chon_bo_ma_hoa(cho_phep_gpu=False)` | yes |
| **B25-01** — retention declared, never swept | P2 | no caller of `assets.don_theo_run`; no job reads `expires_at`; `promote_va_ghi` called without `han` for every stage | yes |

⭐ **One shape, five times.** The VLM, the stage cache, the hardware encoder, the
artifact sweeper — and, in a different register, `dich_thuat.py` — were each built
to completion, tested in isolation, and never connected to a path that runs. Four
of them are recorded as separate blockers; they are one habit. A capability with a
passing unit test and no live caller looks exactly like a finished feature from
every angle except the only one that matters.

⇒ **Recommendation for Phase 27:** before fixing them one by one, add a check that
would have caught all five — every declared capability must have at least one
caller reachable from `pipeline.CHUOI` or from a route.

---

# G1–G19

| gate | verdict | basis |
|---|---|---|
| G1 Provenance/worktree | **PASS** | source SHA `706faca` recorded and matches; dedicated worktree; V2 docs retained. ⚠️ those docs are also lying **untracked in the main checkout**, where they belong to no branch — flagged to the deploying session today |
| G2 Contract supersession | **PASS** | `hop_dong_v4.PHIEN_BAN_BI_THAY_THE`; ADR-V4-001 |
| G3 Capability ownership | **FAIL** | no private provider client (verified: no `requests`/`httpx`/`urllib`/vendor SDK imports in the app), but `dich_thuat.py` is a complete second translation path, dead, feeding a live fingerprint — **A26-01** |
| G4 Runtime invariants | **FAIL** | queue SSOT, owner scope, one billing owner, cancellation, orphan cancellation, invalidation all verified green; **revision safety not enforced for work items** — A26-02 |
| G5 Durable item granularity | **PASS** | per-segment checkpoints reused across a failure (Phase 23, counter: 3+1 calls for 3 segments) |
| G6 Large input | **FAIL** | **A26-03** — the gate's exact wording is violated by `routes.py:254` |
| G7 Resource safety | **PASS** | barrier holds; Phase 23 closed the last indirect path to a real model through the queue; profiles measured in Phase 24 |
| G8 GPU correctness | **FAIL** | no GPU taken for stream-copy or probes ✓; **hardware encode never used** (B24-01); and the owner app's CPU fallback guards the constructor rather than the call that fails (Phase 24) |
| G9 Scene/VLM | **FAIL** | **B22-01**. Latent alongside it: `hieu_canh.doc_hieu_canh` requires a top-level `canh` key that `loi_nhac_canh` never asks the model for — a compliant response would be rejected the day the caller exists |
| G10 Content/EditPlan | **PARTIAL** | preserve cannot cut ✓ (pinned); no dubbing spend on dropped scenes ✓ (`EDIT_PLAN` precedes `CONTENT_PROCESS` in `pipeline.CHUOI`); "keep/cut decisions traceable" is **vacuous** — there are no cut decisions |
| G11 Voice | **PASS** | binding resolved through the declared `apps.ltt_voice` surface; no sidecar internals (test_435 boundary guard, which caught a violation in Phase 21) |
| G12 Dubbing fit | **PASS** | bounded ladder (`VONG_TOI_DA`), valid segments reused, no infinite retry (all loops audited: every `while True` in the app has a break or a deadline) |
| G13 Render | **PARTIAL** | manifest deterministic ✓; preserve stream-copies ✓; **renderer never calls AI ✓ (verified: no `ai.`/`giong_noi`/`chep_loi` reference in either render module)**; smart cuts do **not** use the accepted hardware encoder — B24-01 |
| G14 QC/repair | **PARTIAL** | technical QC full; speech/semantic/visual implemented; **repair plan computed but never driven** (Phase 19 debt); A26-04 |
| G15 Billing | **PASS** | one owner holds; `UNIQUE(run_id, ma_dispatch)`; ambiguity recorded, never auto-retried, never charged (re-verified Phase 23 with a call counter) |
| G16 UI/product truth | **FAIL** | **A26-05** |
| G17 E2E | **NOT PASS** | both presets produce usable files (Phase 22), but no live model call, no live LTT Voice synthesis, no real customer footage. The pack's rule is explicit: missing external evidence is not PASS |
| G18 Performance | **PASS** | Phase 24: 0.0 s above 90 % sustained in any stage of either preset; free RAM never below 8.6 GiB; every figure recorded against its measured background |
| G19 Security/hardening | **PASS** | six-object IDOR; diagnostics no longer leak paths through either channel; migrations and models agree with zero ASV drift. ⚠️ retention (B25-01) is a hardening gap carried as P2 |

---

# What I re-ran

`VONG_DU` (the V4 invariant round): **168 passed, 1 xfailed**. The xfail is
B22-01's strict pin — it is *expected* to fail and would report XPASS the day the
VLM is wired.

I did not re-run the heavy E2E or benchmark suites; their evidence files were read
instead, which is what they exist for.

---

# Audit method note

⛔ Every finding above was reached by reading code or running a probe, and each
carries the command or the file:line that produced it. Where a claim in STATE
conflicted with the source, the source won and the conflict is written down
(A26-03 vs "V4-R01 CLOSED").

⚠️ What this audit **cannot** claim: that the four unconnected capabilities are the
only ones. I found them by following the specific hazards this phase names. The
check recommended above — every capability must have a reachable caller — is what
would answer the general question, and it does not exist yet.
