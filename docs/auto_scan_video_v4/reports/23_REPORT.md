# Phase 23 — Failure, restart, retry, cancel and ambiguity acceptance

**Verdict: PASS.** Branch `phien/asv-v4`.

Phase 22 proved the success path. This phase attacked the failure paths, and the
first thing it found is that there were no *recovery* paths: three mechanisms
built for retrying a transient failure existed, and none of them was connected to
the other two.

---

## 1. 🔴 There was no automatic retry at all

Three pieces were already in the code:

* `loi.phan_loai` classifies every ASV exception, and `TAM_THOI` means
  *"a slip — retrying is the right answer"*;
* `STAGE_FAILED_RETRYABLE` exists in the stage state table;
* stage jobs are deduplicated on `asv:{run}:{stage}:a{attempt}` — a key shaped
  around an attempt counter, which only makes sense if a stage can be submitted
  more than once.

None of them met. `_thu_ket_qua_job_con` called `danh_dau_hong` with its default
`cuoi_cung=True` for **every** failed child job, so the classification never
reached the stage state; and nothing anywhere resubmitted a stage sitting in
`STAGE_FAILED_RETRYABLE` — `_nop_giai_doan_san_sang` only ever looked at
`STAGE_PENDING`. The retryable state was a dead end in the state machine.

⇒ A moment of disk pressure, a subprocess killed by the OS, one flaky ffmpeg
invocation — any of them ended the whole run.

### And the consequence did not stop there

`thu_lai_giai_doan` refuses every run in a terminal state, and that refusal is
correct: a terminal run has **settled**, its credit hold is gone, so spending
more on it would be spending against nothing.

Put the two together and the customer's only option after any hiccup was to
submit a **new run** — recomputing demucs and ASR from scratch, because the
artifact cache is keyed by `run_id`. The most expensive stages in the product
were paid for twice for a failure that lasted half a second.

**Fixed**, by connecting what was already there:

* `thi_hanh.chay_giai_doan` now classifies the exception and marks the stage
  `failed_retryable` (instead of terminal) when it is a transient slip and the
  stage still has attempts left;
* `_nop_giai_doan_san_sang` submits stages in that state, and `danh_dau_dang_chay`
  bumps `attempt` — so the dedupe key differs and a genuinely new job is created;
* `features.LAN_THU_GIAI_DOAN_TOI_DA = 3` bounds it. A "transient" failure that
  repeats three times is not transient, and trying again is just burning a slot.

## 2. 🔴 A dubbed line already paid for was being synthesised again

Per-segment checkpoints are written and **committed** inside the synthesis loop —
that was Phase 15's design and it works. But the segment's audio only becomes an
`AsvAsset` when the *whole stage* finishes and `thi_hanh` promotes the batch.

So a failure on segment three left the run with:

* ledger rows saying segments one and two were delivered — durable;
* no reusable artifact for either of them — because promotion never happened.

Measured: **6 calls to the voice engine for 3 segments**, after a single slip.

⭐ And the ledger's own uniqueness constraint hid it. `UNIQUE(run_id, ma_dispatch)`
stops the second *write*; it does not stop the second *piece of work*. The books
looked perfect while the GPU did everything twice.

**Fixed**: on resume, a segment whose audio is still sitting under its staging key
is reused. The key carries the segment's fingerprint (text + voice + preset), so a
file found there belongs to this segment and no other, and it is still re-measured
with `kiem_tep_tieng` before being trusted. Back to 4 calls for 3 segments + 1
slip — the arithmetic the design intended.

## 3. 🔴 My own fix opened an unbounded loop, and the cap was in the wrong place

`chay_giai_doan` checks `con_luot_thu` before marking a stage retryable. But that
is not the only road into that state: `_thu_ket_qua_job_con` also sets it when the
job finished while the stage did not — a handler that died between the engine
returning and the checkpoint being written — and that road asks no question about
attempts.

With the submit site accepting `failed_retryable` unconditionally, a stage landing
there would be resubmitted **forever**: every coordinator tick spawning another
job, on a machine that is serving customers.

⭐ The lesson is about where an invariant belongs: it must be enforced at the last
point before the action, not at one of the several places that can lead to it. The
cap now lives in `_nop_giai_doan_san_sang`, and a test drives the exact path that
bypassed it — a stage whose result is never recorded — and asserts the number of
jobs for one stage never exceeds the cap.

## 4. ⚠️ The first measurement of this phase described the test harness

The probe that started all of this reported: *"a render failure ends the run and
cannot be retried."* Half of that was true for the wrong reason.

`test_402._chay_het_hang_doi` — the runner every ASV chain test uses — calls
`jobs.fail(..., retry=False)` for every exception. Correct for what that file
proves (the execution spine), and fatal here: it turns every failure into a final
one, which is precisely the question this phase asks.

⇒ Phase 23 uses its own runner that calls the real
`job_runner._provider_failure_kind` and the same `jobs.*` functions the worker
calls. No copy of the policy — a copied policy is a policy that will drift.

## 5. 🔴 A test in the suite reached real ASR — and hung the whole run

The regression run for this phase stopped dead. The process had burned 5.5 s of
CPU in 30 minutes and had no child processes: not slow, **blocked**. Its loaded
modules said where: `ctranslate2.dll`, `cudnn64_9.dll`, `nvcuda.dll`.

`test_406::test_cong_thoat_ban_nen_la_artifact_chinh_tac_da_kiem` drains the
queue with capabilities `{api, ffmpeg, gpu, voice}`. It does not stop after
`audio_prepare` — it continues into `transcribe`, which is **real
faster-whisper**, whose default device is `cuda`, and whose CUDA path on this
machine hangs (Phase 22 measured >7 minutes with no result and no error, against
7.5 s on CPU).

⭐ This is the *same* defect Phase 13 fixed for demucs, in the same test, and it
was missed for the same reason: the barrier in `rao_chan_nang` is attached to
**direct** callers of a heavy model, and this path reaches it **through the job
queue**. Phase 13 stubbed demucs there and nobody noticed the queue kept going
one stage further.

⛔ And the cost is worse this time. A slow test makes a gate expensive; a test
that blocks forever makes a gate **never finish** — which is what happened twice
before the cause was found.

Fixed with `rao_chan_nang.gia_lap_asr`, a sibling of `gia_lap_demucs`: only the
heavy piece is substituted, and the queue, worker, ffmpeg, storage, database and
lineage stay real. That test now runs in **4.6 s**. A sweep of every test that
claims with `gpu` found no other indirect path: `test_400` uses fake manifests
and `test_409` only asserts claim eligibility without running a handler.

⚠️ The CUDA hang itself is not fixed here — it is not this phase's subject and it
is not understood. It stays with Phase 24, where it was already recorded.

## 6. 🔴 And a third stub pointing at a door that had moved

Turning the retry wiring on made `test_408::test_giai_doan_hong_MO_HO_thi_job_KHONG_quay_lai_hang_doi`
fail — and the reason was not the wiring.

That test substitutes `dich_thuat.dich_ban_ghi` to raise `DichMoHo`. Phase 14
moved `CONTENT_PROCESS` onto `ai.goi_tinh_tien`, so **nothing calls that function
any more**. The test had been green ever since while its scenario — an ambiguous
dispatch — never once occurred: the stage failed for an unrelated reason, and the
final assertion measured something else entirely.

⭐ Third instance of one defect class in three phases: Phase 14 found three copies
of a stub that had stopped biting, Phase 22 found a shared double returning a type
the real door never returns, and this one **substitutes a door that moved**. None
of them fails loudly. They stop testing, quietly, and the suite keeps saying yes.

Rewritten to substitute the door `content_process` actually uses and to produce a
real ambiguity (call `on_dispatch`, then lose the connection). Its assertion is
now the invariant it was written for, measured with a counter: **the model door is
touched exactly once**, no matter how many coordinator ticks follow.

⚠️ Its old assertion — "the queue is completely empty" — was also broader than the
property it defended. A leftover `advance` job calls no provider; it only settles
the run. Asserting emptiness made the test break whenever the number of
coordinator ticks changed, which is not what I5 is about.

## 7. What was exercised

`tests/test_449_asv_v4_hong_va_phuc_hoi.py` — **21 tests + 1 `xfail(strict)`**.

| scenario | what is pinned |
|---|---|
| death after provider dispatch | ledger row `mo_ho`, zero credit, never auto-retried (counter proves the door is not called again) |
| timeout **before** dispatch | `tu_choi`, not `mo_ho` — nobody charged, retrying is safe |
| death after staging, before checkpoint | the run recovers by itself; exactly one asset for the stage |
| asset deleted | `kiem_toan_ven` goes `ok` -> `missing` on the same row |
| asset corrupted | same file size class, different bytes -> `corrupt` |
| stage cache on an untouched stage | `xfail(strict)` — it returns nothing, see §6 |
| cancel during each of 6 heavy stages | stops immediately, promotes nothing, charges nothing |
| cancelled run + late children | stays `cancelled`, no orphan jobs |
| retry an upstream stage (live run) | downstream re-runs, cost does not double |
| retry downstream after a render slip | **zero** new voice calls |
| one segment fails | the other segments are not re-synthesised |
| malformed model response | fails cleanly at that stage; the next stage does not run on a translation that does not exist |
| render fails until attempts run out | run ends `error`, every upstream artifact still in storage |
| QC blocks | run ends `error`, and the QC report is still promoted so support can say why |
| re-running the queue three times | no new jobs, no new charges |

**Mutation testing: 9 mutations, 9 red** — every one of the wirings above dies
when cut, including the loop guard. One further mutation (removing
`kho.exists()` from `kiem_toan_ven`) stayed green and is an **equivalent
mutant**, not a hole: with the check gone, `do_va_bam` raises on the missing file
and the `except` branch returns the same `missing`. Recorded rather than papered
over with a test that would only pin an implementation detail.

Regression: ASV cluster **1082 passed**, 4 skipped, 3 xfailed. V4 invariant round `VONG_DU` **168 passed**, 1 xfailed.

### 🔴 And mutation testing caught two of my own tests measuring nothing

The first versions of the "deleted asset" and "corrupted asset" tests asserted
that `assets.cache_dung_duoc` **refuses** a damaged artifact. Both were green —
and removing the integrity check from that function did not turn either red.

The reason is finding §8 below: `cache_dung_duoc` refuses *everything*, including
a perfectly intact artifact. A test that only checks the negative branch of a
function that always answers negatively measures nothing at all.

⭐ Both now assert against `kiem_toan_ven` — which does work, and does distinguish
`ok` / `missing` / `corrupt` — and each starts by asserting the **positive** case
on the untouched artifact, so the test can never again pass because everything
fails.

## 8. ⚠️ BLOCKER — the stage-level fingerprint cache has never returned a hit

ADR-001 D8 promises: same inputs, same configuration, same engine version ⇒ reuse
the previous artifacts and charge nothing. `thi_hanh.chay_giai_doan` calls
`assets.cache_dung_duoc` on exactly that promise.

It returns `None` every time, on an intact, just-finished stage. Two independent
reasons, both structural:

* the filter is `f"/{van_tay}." in a.storage_key`, but `dat_khoa` truncates the
  fingerprint to `DAI_VAN_TAY_TRONG_KHOA = 32` characters in the key — while the
  stage fingerprint handed to the cache is 64 characters long, so the substring
  can never appear;
* and the promoted key does not carry the *stage* fingerprint anyway: every
  engine supplies its own per-artifact fingerprint in `phan["van_tay"]`
  (measured: one `media_prepare` run wrote two artifacts under two different
  fingerprints), so there is no single value that identifies the stage.

⇒ The whole cache branch of `chay_giai_doan` is dead code, and stage-level reuse —
the thing D8 exists to provide — has never happened.

⛔ Not fixed here: making it work means changing what goes into a storage key, or
adding a fingerprint column to `asv_asset`, and both are design decisions rather
than narrow correctness fixes. Pinned by `xfail(strict=True)` so the day someone
fixes it, the suite says so. **Owner: Phase 27.**

⭐ Worth stating plainly: the reuse that *does* work is at the **unit** level
(`AsvWorkItem` + the ledger + the staging recovery added in §2), which is why the
call-counter tests in this phase pass. Reuse at the stage level is a separate,
still-unbuilt claim.

## 9. Debt carried forward

⚠️ **Recovery still ends at the run boundary.** Within a live run, a transient
failure now recovers and expensive work is reused. Once a run is terminal it has
settled, and a new run recomputes everything, because the artifact cache is keyed
by `run_id`. Making work reusable *across* runs is a billing question (who pays
for the second run's held credit) and belongs to a decision, not to this phase.

⚠️ **Stage-level reuse is unbuilt** — see the blocker in §8.

⚠️ **`STAGE_FAILED_RETRYABLE` is not surfaced to the customer.** The progress view
shows a stage as failed; it does not say "retrying, attempt 2 of 3". Cosmetic
today, confusing the first time a customer watches it.

⚠️ **Ambiguous dispatches still need a human.** `su_dung.giai_quyet_mo_ho` exists
and is tested, but nothing schedules or prompts the reconciliation — an ambiguous
row waits for an operator who is not told it is waiting.

## 10. Two ratchets caught this phase on the way out

The full gate came back red twice, and both were mine.

**`nuot loi lang le`: 63 against a baseline of 62.** The staging-recovery helper
added in §2 ended with `except Exception: return None`. The ratchet is right, and
the fix is a log line rather than a raised baseline: a staging file that cannot be
read is *not* an incident — that segment is simply synthesised again — but if it
happened for **every** segment, the reuse path would be dead and the bill would
climb with nobody seeing it. One log line is the only thing that separates those
two situations. Back to 62/62.

**`test_177_system_profile`: stale.** Regenerating `ho_so_he_thong.txt`, then
making one more source edit, invalidates it — and the gate takes 20 minutes to
say so.

⚠️ Worth recording next to it: a peer session merging into `admin-mvp-v3` reported
that the project owner has since **removed** this whole feature (`e85020e`) —
`ho_so_he_thong.txt`, `tools/build_system_profile.py` and `test_177` are gone
there. `phien/asv-v4` forked before that commit, so this branch still carries all
three, still runs the step, and still regenerates an 18 MB file every phase for
something already decided against.

⛔ Not removed here. The decision lives on another branch, and dropping a gate
step in the middle of a phase sequence is changing the instrument while measuring
with it. Recorded in STATE_V4 as a merge-time consequence instead.

## 11. Exit gate

**PASS.** Failures are deterministic (the same interruption produces the same end
state), recoverable (a transient failure now retries, bounded, and the run
continues), and minimal recompute is proven by call counters rather than asserted:
a render retry costs zero voice calls, and one failed segment costs one extra
synthesis rather than a whole stage.
