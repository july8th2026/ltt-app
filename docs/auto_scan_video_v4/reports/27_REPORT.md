# Phase 27 — Blocker remediation

**Verdict: `PASS`.** Every release blocker from Phase 26 is fixed with evidence.
**Three** `xfail(strict=True)` pins flipped to XPASS and were removed — two on
real end-to-end runs (B22-01, B24-01) and one on the cache (B23-01), which had
first refused a fix that was only half of one.
Three new findings are recorded for Phase 28; none of them is a release blocker,
and each carries the reason it was not fixed here.

- **source_sha (branch base):** `706faca50c75fb5b6dbad6c346b96c98a6736a11`
- **Phase 26 landing commit:** `3e26b7c`
- **Phase 27 commits:** `b5aeaf0` (Lot A) · `8d56c05` (Lot B) · `94e67b5` (Lot C)
  · `196313e` (evidence) · line-ending restoration

---

## Verdict basis

| Finding | P | Gate | Outcome |
|---|---|---|---|
| **B22-01** — VLM never wired into `EDIT_PLAN` | P1 | G9 | **FIXED** |
| **B24-01** — hardware encoder unreachable | P1 | G8/G13 | **FIXED** |
| **A26-01** — translation fingerprint has no model identity | P1 | G3/G4 | **FIXED** |
| **A26-05** — `smart_localize` promises cutting it cannot do | P1 | G16 | **FIXED** |
| **A26-02** — `AsvWorkItem.revision` documented, never enforced | P2 | G4 | **FIXED** |
| **A26-03** — direct upload reads whole video into RAM | P2 | G6 | **FIXED** |
| **B23-01** — stage cache has never returned a hit | P2 | G4 | **FIXED** (two layers; first patch was insufficient — see below) |
| **B25-01** — retention declared, never swept | P2 | G19 | **FIXED** |
| **A26-04** — technical QC shares constants with the producer | P3 | G14 | **NOT_FIXED (by design, condition recorded)** |

⛔ No severity was reclassified to close anything. A26-04 is recorded NOT_FIXED
with the audit's own stated reason — it asked for a record, not a fix.

---

## The habit, and what closing it actually took

Phase 26's conclusion was not nine defects but **one habit repeated five times**:
a capability written to completion, unit-tested, and never connected to a path
that runs. Closing them confirmed the shape and added something the audit did
not see: **the same habit had produced matching defects in the test doubles.**

For B22-01 the schema of a single VLM answer was described in **four** places and
**no two agreed**, because no live caller ever exercised any of them:

| where | what it said |
|---|---|
| `hieu_canh.loi_nhac_canh` | asks the model for a **flat** object |
| `ai.DOC_CANH.truong_bat_buoc` | declared `("canh",)` — a **wrapper** key |
| `hieu_canh.doc_hieu_canh` | tolerated **both** shapes |
| `tests/fixtures/asv_e2e._phan_hoi` | returned a **batch** API that never existed |

So a response obeying the prompt exactly would have been rejected with
*"thiếu trường bắt buộc ['canh']"*. Phase 27 collapsed all four to one shape.

⭐ And the prompt had never sent a frame. It said *"có N khung hình đại diện"* and
attached nothing — so `can_thi_giac=True` selected a vision model and then asked
it a question a text model answers identically. `canh.lenh_rut_khung` had existed
since Phase 11 with no caller.

---

## Per-finding: reproduction, root cause, fix, evidence

### B22-01 · P1 · G9 — FIXED

**Reproduction.** `giai_doan_ban_bien_tap.chay` passed `hieu = ()`;
`ban_bien_tap._quyet_dinh_mot_canh` returns KEEP when `h is None`. Measured in
Phase 22: `so_canh 4, so_giu 4, so_cat 0` on a source containing a scene with no
dialogue at all.

**Fix.** `_doc_cac_canh` in `giai_doan_ban_bien_tap.py`: extract representative
frames via `canh.lenh_rut_khung`, ask per scene through `ai.goi_tinh_tien`,
checkpoint **per scene** in `AsvWorkItem` (a re-run reads `outputs` instead of
paying the model twice), and let one bad scene fail only itself. Plus the schema
collapse above, and frames actually attached to the prompt as OpenAI
`image_url` + `data:` parts.

**Three principles, all of them "one scene must not take down the run":**
1. checkpoint per scene, keyed by a fingerprint that includes prompt/schema
   version, frame count and the scene's dialogue context;
2. a broken scene becomes *no evidence about this scene*, and no evidence means
   **keep** — cutting blind is worse than keeping too much;
3. ⛔ but a scene that **answered with garbage has still been paid for**;
   `ai.goi_tinh_tien` writes the ledger on all three branches before we see the
   result, so discarding the result drops no entry.

**Evidence — real E2E run** (`evidence/22_nghiem_thu.json`):
`so_canh 4, so_giu 3, so_cat 1, so_canh_da_doc 4`; output 27.29 s against a
32.19 s source; `timing_align` recorded `so_doan_bi_cat: 1` — a dubbed line
belonging to the cut scene was not placed, which is V4-R07 working.
`test_preset_CAT_phai_cat_it_nhat_MOT_canh_khong_co_thoai` reported
**XPASS(strict)** and the marker was removed.

### B24-01 · P1 · G8/G13 — FIXED

**Root cause was in three places, not one.**

1. `asv_media` declared no `gpu_vram_mb`, so `_vram_can` returned 0 and no lease
   was ever taken → `ctx.gpu_uuid` empty → `chon_bo_ma_hoa(cho_phep_gpu=False)`.
2. 🔴 **COMPOSE decided the encoder from `ctx.gpu_uuid`** — but COMPOSE and
   RENDER are two jobs and a lease dies with its job. The question "do I have a
   card" was asked in a place where the answer can never still hold when
   something uses it. COMPOSE is a 300-second JSON-planning stage.
3. ffmpeg ran without `env=ctx.gpu_env()`, so a job granted card 1 could still
   encode on card 0.

**Fix.** `gpu_vram_mb={"asv_media.render": 500}`; COMPOSE records the **declared
ceiling** (what this machine can do) and RENDER may only **lower** it, never
raise; ffmpeg pinned to the granted card.

**The 500 is measured, not chosen.** One 1080p `h264_nvenc` session, `-preset p5`,
sampled every 0.2 s via `nvidia-smi` on this machine (two RTX 5060 Ti):

```
peak card memory:   +228 MiB over baseline
encoder utilisation: 88 % peak
throughput:          244 fps (~8x realtime)
```

⛔ **And a pin was protecting the defect it was written to prevent.**
`test_renderer_KHONG_xin_GPU` forbade `gpu_env` outright. Its sentence —
*"`-c:v copy` doesn't touch the encoder"* — was true for one preset and stopped
being true at Phase 12, and nobody re-read it. It is re-aimed, not relaxed:
forbid **self-granting** (`gpu_lease`, `list_gpus`, `detect_gpu_encoder`) and
**require** pinning. `test_419` held a second copy of the same claim and got the
same treatment.

⚠️ **A measurement nobody had made:** one 1080p session already puts the encoder
engine at 88 %. The genuinely scarce resource is the **NVENC engine**, not VRAM —
and `gpu_lease` reserves by VRAM, so it does not serialise two concurrent
encodes on one card. Recorded as **V4-R15**; no second slot-counter was added
inside the app, because that would create a second owner for one resource —
exactly what `pipeline.CHUOI` refused to do for demucs.

**Evidence:** `evidence/24_hieu_nang.json` — `bo_ma_hoa_may_co: h264_nvenc`, and
the `cat_thong_minh` run records `bo_ma_hoa: h264_nvenc` where it previously
recorded `libx264`. `test_preset_CAT_dung_bo_ma_hoa_PHAN_CUNG_khi_may_co`
reported **XPASS(strict)**; marker removed.

### B23-01 + A26-01 · P2 + P1 · G3/G4 — FIXED **together**

The audit was explicit that these must not be separated, and the reason is
non-obvious: the dead cache was **masking** the fingerprint defect. Fixing the
cache alone would have started serving a stale translation after a model change.

- **B23-01 had two layers, and my first patch only touched one — the pin caught
  me.** Layer one: `cache_dung_duoc` filtered `f"/{van_tay}." in storage_key`
  with a 64-character fingerprint while `dat_khoa` truncates to
  `DAI_VAN_TAY_TRONG_KHOA = 32`. Truncating the needle closes that, and I
  recorded B23-01 as FIXED on the strength of it — **before running the
  `xfail(strict)` that guards it**. It still failed.

  🔴 Layer two, which the pin's own text had spelled out and I had skimmed: the
  key carries each **artifact's** fingerprint, not the stage's. Measured: one
  `media_prepare` run writes two artifacts under two different fingerprints,
  because `promote_va_ghi` takes `van_tay=phan["van_tay"] or vt`. So **no**
  single value inside `storage_key` can answer the question being asked.

  **The real fix removes string matching entirely.** *"Has this stage already
  finished with this fingerprint"* has exactly one honest place to be answered —
  `AsvStage.fingerprint`, written by `features.danh_dau_xong` — and the artifact
  list is already in that row's `outputs["khoa_asset"]`. Missing one artifact
  now rejects the whole cache entry rather than returning a partial set.

  ⭐ Two unit tests then went red, and they were right to: they built a scene of
  **artifacts with no stage row** — a state `chay_giai_doan` never produces,
  since it always has that row before it asks. Their propositions (owner
  isolation; upstream not invalidated by downstream) are untouched; only the
  setup moved to a state that can exist.
- **A26-01:** the CONTENT_PROCESS engine version read
  `dich_thuat.PROVIDER_CHINH` / `MODEL_CHINH` — an **empty** constant in a module
  with no callers since Phase 14, while `qwen38-api` does the work. Now it reads
  `ai.ban_do_model(ai.CHUYEN_LOI_THOAI)`, the same map handed to `dieu_phoi.goi`,
  so the fingerprint and the call cannot drift apart.

**Evidence:** `thi_hanh.phien_ban_engine(CONTENT_PROCESS)` returns
`noi_dung/1/ltt_llm:qwen38-api` (was `noi_dung/1/ltt_llm/`). And
`test_449::test_cache_cap_GIAI_DOAN_dung_lai_duoc_mot_giai_doan_khong_doi`
reported **XPASS(strict)** — the stage cache returned a hit for the first time
since it was written; marker removed.

### A26-05 · P1 · G16 — FIXED

Phase 27 wired the VLM, so cutting can now happen — but it stays **conditional**:
no evidence means keep, and `SAN_GIU_LAI` refuses to cut past half the duration.
A video where every scene earns its place comes back the same length and has
still been re-encoded. The customer-facing text now says so, before they choose.
English catalogue updated by hand, LF preserved, no re-extraction.

### A26-02 · P2 · G4 — FIXED

`tables.py:327` promises `UPDATE ... WHERE revision = :r` for `AsvWorkItem`;
`features.cap_nhat_giai_doan` implements exactly that for `AsvStage`;
`su_dung.danh_dau_xong` did a plain ORM read-increment-write. Now a conditional
`UPDATE`, raising `XungDotDonVi` on a lost race.

🔴 **And the new class first inherited `SuDungError` "for tidiness"** — which made
`loi.phan_loai` catch it on the branch above and return `NGUOI_DUNG`, *final
failure, do not retry*. Losing a race is not a programming error and **must** be
retryable. The class is deliberately outside that family, and `tests/test_418`
pins both directions.

### A26-03 · P2 · G6 — FIXED

G6's wording: *"production path does not `await read()` entire large video into
RAM"*. Worse than the allocation was the **order**: the 90 MB ceiling was checked
on the line **after** `read()`, so a 100 MB file was fully allocated before being
refused — a decision about whether to accept something, placed after the act it
was supposed to prevent. Now streamed in 1 MiB chunks with the ceiling enforced
mid-stream, and the business layer takes a **path** instead of bytes.

⚠️ STATE recorded V4-R01 as CLOSED. Phase 05 closed the *checksum* half; the
*memory* half named in the same risk was still open. Both are closed now.

### B25-01 · P2 · G19 — FIXED, and it turned a harmless label into a live command

Nothing swept: no caller of `assets.don_theo_run`, no job read `expires_at`.
The platform has had the `AppManifest.bao_tri` hook since 2026-08-24 — added
**because** another app (`vps`) wrote `thu_phi_dinh_ky` with tests and nothing
called it. Auto Scan repeated it exactly. Now `features.bao_tri` runs under the
platform's maintenance lease (once per cluster) and `assets.quet_het_han` deletes
only rows past `expires_at`, bounded per pass so it cannot hold the lease.

🔴 **Wiring the sweeper made a benign defect dangerous.** `promote_va_ghi` stamped
`HAN_TRUNG_GIAN = 30 days` on **everything**, deliverable included. That was
harmless only because nothing swept. The two changes had to land together: the
deliverable is now promoted with `han=None`; intermediates keep 30 days.

⭐ Two existing pins were **mutually contradictory** and both green for that same
reason — one demanded every artifact carry an expiry, the one directly below it
(strict xfail) demanded the deliverable outlive the scratch. When `expires_at` was
just a label, both described something that never happened. They are now one
consistent pair.

### A26-04 · P3 · G14 — NOT_FIXED, deliberately

The audit's own minimal fix was *"none required for the MVP; record it"*. Sharing
constants with the producer is **correct** for the question being asked — *did the
pipeline do what it was told* — and it cannot catch a wrong target. The reason and
the **condition to change** are now written at the constant: the day a delivery
spec exists, T4/T5 must read *that document*, and must not be reconciled by
copying the number across.

---

## The check Phase 26 asked for — `tests/test_453`

The audit ended with an instruction: *add a check that would have caught all five
before fixing them one by one.* It counts callers in **product code** and
deliberately does not count `tests/` or `tools/`, because a capability whose only
caller is the test suite is precisely the thing being hunted: its green suite is
evidence of **existence**, not of **use**.

⛔ **It catches 3 of 5, and says so.** B23-01 and B24-01 both *had* callers; their
defects were a wrong comparison and an unreachable branch. Written down rather
than left for a later reader to assume the class is closed.

It ratchets on the **set**, not a count — a number would let one debt be swapped
for another while the bar stays green. Mutation-tested: adding a public function
with no caller turns it red immediately.

🔴 **And it found two more instances the audit had not:** `qc_ai.py` (semantic and
visual QC) and `sua_chua.py` have **no caller in product code** — `loi.py` imports
only their exception classes, which makes both files look live from every angle
except the one that matters. G14 was marked PARTIAL for *"repair plan computed but
never driven"*; that was half of it. Recorded as **A27-01**. Wiring them is
feature expansion and out of this phase's scope.

---

## The failure that was not a failure — A27-02

Re-running the E2E after B22-01 landed turned
`test_tieng_long_NAM_DUNG_CHO_trong_tep_ra` **red** for the cutting preset:
*"tệp ra không có đoạn nào nổi lên trên nền"*. Three measured runs, and the
answer inverted the first hypothesis.

`vung_co_tieng` estimated the noise floor with the **median**, carrying a premise
written in its own docstring: *"a dub speaks about a third of the duration, so the
median falls on the bed"*. That premise depends on how much silence the **source**
happens to contain — something the measurement does not control. Cutting the
dialogue-free scene removed the quietest five seconds and pushed the median up
**0.6 dB**, which was enough:

```
preserve  n=64  p20 -17.73  p50 -17.07  ->  median: 4 regions,  p20: 6 regions
cut       n=54  p20 -17.80  p50 -16.48  ->  median: 1 region,   p20: 6 regions
```

⭐ The decisive evidence: **the first 44 windows of the two level series are
identical**, diverging only where the cut begins. The product did not change; the
instrument did. The bed is now the **20th percentile** — which is also the better
definition, since the bed is the quiet part of the distribution and the median is
only valid if you already know most of the track is bed.

The full per-window level series is now recorded in the evidence file. A report
saying "0 speech regions" without the floor, the threshold and the distribution
forces the reader to guess between two very different explanations — and here the
true one was the less likely.

---

## The harness that could not measure what it was pointed at

Phase 24's benchmark worker skipped the platform's GPU-granting step entirely, so
a question like *"does this run use the hardware encoder"* could only ever measure
that omission. It now reads `job_runner._vram_can` and calls `gpu_lease.acquire`
for real.

⚠️ With one guard, and its reason: this tree runs `torch+cpu` (V4-R05). Granting a
card to `asv_gpu.*` here makes `demucs_runner` believe it has one and raise
`ThieuCard: "Nền tảng đã cấp card nhưng tiến trình tách không thấy GPU"` — a
completely correct classification of a situation the harness had just invented.
So it asks `torch.cuda.is_available()` first: on the production venv the condition
holds and leases are granted like the real worker; on this tree they are not, and
the harness says so instead of pretending. `asv_media.render` is still granted —
it runs ffmpeg, and NVENC does not go through torch.

---

## Hostile self-review (`V4_TEST_REVIEW_PROTOCOL` Layer 4)

| question | answer |
|---|---|
| Did we duplicate an existing capability? | No. Every fix **connected** something already built. The one new module-level function pair (`quet_het_han`, `bao_tri`) exists because the platform hook had no implementation, not because one was missing. |
| Did we broaden scope? | Two deliberate refusals: `qc_ai`/`sua_chua` wiring (A27-01) and NVENC session serialisation (V4-R15) are recorded, not built. `dich_thuat.py` was **not** deleted — that would take a 200-line test file and two exception classes `loi.py` still uses, which is larger than the blocker requires. |
| Did we break old callers? | `features.tao_run_tu_tai_len` changed signature (`du_lieu` → `duong_tep`). Its only product caller is the route, updated in the same commit; `test_423`/`test_429` pin it by name and both pass. |
| Did we add a silent fallback? | RENDER's encoder downgrade is a fallback, and it is **logged** and one-directional (never upgrades). A scene whose VLM read fails becomes "no evidence" — logged, and it decays to the safe answer (keep), never to a cut. |
| Did we add CPU/GPU work without admission? | The VLM calls run in `EDIT_PLAN`, which already declared `tai_nguyen="llm_remote"`, slot 1. Frame extraction is ffmpeg on a lane that already runs ffmpeg for scene detection. RENDER now takes a **declared** 500 MiB lease. |
| Can a crash between output and checkpoint leave a false DONE? | Per-scene: `ai.goi_tinh_tien` writes the ledger before we read the result; `danh_dau_xong` + `db.commit()` follow, per scene, not per stage. An ambiguous dispatch commits the ledger and **does not** mark the item done. |
| Can user A reference user B's asset/voice/run? | Untouched. Scene work items carry `run.owner_id`; the fingerprint includes `run_id`; storage keys still carry the owner. `test_451`'s six-object IDOR checks pass. |
| Can retry double-charge or repeat a paid ambiguous dispatch? | Scene checkpoints are read back before any call, so a re-run pays only for scenes not yet answered. `UNIQUE(run_id, ma_dispatch)` still guards; `AiMoHo` is recorded `mo_ho`, never auto-retried. |

**One more, which the protocol does not list but this phase earned:**
*did a test change make a check weaker?* Five pins were re-aimed. Each one was
pinning a premise this phase disproved, and in every case the replacement forbids
strictly more than the original in the dimension that matters. Four of my own new
checks failed on first write because they searched the **source text** and matched
the comment explaining the fix — the third occurrence of that trap in this repo.
They read the AST now.

**And one honest correction to this report itself:** B23-01 was written up as
FIXED before its guarding pin had been run. The pin then failed, and its stated
reason named the layer I had skipped. The finding is genuinely closed now, but
the sequence is worth recording: I trusted a fix that matched my model of the
defect over the check that had been written specifically to test that model.
`xfail(strict=True)` earned its keep three times in this phase — twice announcing
a defect's end, once refusing to let one be declared over early.

---

## Commands run

```
python -m pytest -q -p no:randomly <VONG_DU + test_452 + test_453>
    -> 188 passed, 1 xfailed
python -m pytest -q -p no:randomly tests/test_4xx  (except 448/450)
    -> 1049 passed, 3 skipped, 2 xfailed
LTT_TEST_NANG=1 ... tests/test_448_asv_v4_e2e_nghiem_thu.py
    -> 20 passed          (real run, both presets, evidence regenerated)
LTT_TEST_NANG=1 ... tests/test_450_asv_v4_hieu_nang.py
    -> 12 passed, 1 skipped   (real run, evidence regenerated)
python -m pytest -q -p no:randomly tests/test_403 tests/test_449
    -> 43 passed          (cache + failure/recovery, after the real B23-01 fix)
```

The one remaining `xfail(strict=True)` is `test_425::test_chuoi_thi_hanh_biet_den_preset`
— a Phase 12 debt about `pipeline.py` naming the preset, not a Phase 26 blocker.

---

## Housekeeping that was not cosmetic

Three patch batches wrote files with `pathlib.Path.write_text`, which translates
newlines on Windows: **30 files silently became CRLF**. The damage was not
ugliness, it was concealment — the phase reported 14,302 changed lines against a
real figure of ~2,400, and an auditor reading the first number would conclude
Phase 27 rewrote half the app. That is exactly what Phase 28 is about to read.

⚠️ The first correction was also wrong: normalising everything to LF, when this
repository legitimately **mixes** both. Each file is now back to its own ending as
of `bae01d2`.

---

## Unresolved external evidence

Unchanged from Phase 26 and still blocking **G17**:

| item | what closes it | blocks |
|---|---|---|
| Live `ltt_llm` / `ltt_llm_vision` call | operator-supplied pool key (machine B, :8299) | G9, G17 |
| Real LTT Voice synthesis | `LTT_VOICE_SIDECAR_TOKEN` for :8120 | G11, G12, G17 |
| Real customer footage, both presets | operator-supplied files at `tests/fixtures/asv_e2e_that/` | G17 |
| `transcribe` on CUDA in the dev tree | CUDA 12 cuBLAS, or measuring the sidecar path | G7, G24 |

⛔ Phase 27's exit gate does not require them; Phase 28's does.

---

## New findings for Phase 28

| id | P | summary |
|---|---|---|
| **A27-01** | P2 | `qc_ai.py` and `sua_chua.py` have no caller in product code. Same habit, sixth and seventh instances. Now held by `test_453`'s ratchet with a written reason. |
| **A27-02** | P3 | `vung_co_tieng` used the median as noise floor; the premise broke the first time the cutting preset actually cut. Fixed to p20; recorded because the *class* of defect — a measurement whose premise depends on the input — is not limited to this one function. |
| **V4-R15** | P2 | One 1080p NVENC session puts the encoder engine at 88 %. `gpu_lease` reserves by VRAM and therefore does not serialise concurrent encodes on one card. |

---

## Exit verdict

**`PASS`** — every Phase 26 release blocker is fixed with evidence; the two
strict-xfail pins that guarded the two P1 defects flipped on real runs and were
removed; the invariant round and both heavy suites are green; and the check the
audit asked for exists, ratchets, and has already earned its keep.

⇒ Proceed to **Phase 28 — independent re-audit and RC freeze**.
