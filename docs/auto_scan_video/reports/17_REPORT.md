# PHASE 17 REPORT — Failure Recovery and Resource Verification

**The phase where the tests were wrong five times before the code was wrong once.**

## Entry evidence
- starting SHA: `e505a1f`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 16 closed at `FAIL (3/26)`, all failures owned elsewhere
- allowed change scope: failure policy, retry adapters, manifest/resource declarations, tests

## The one real defect this phase found

`platform_core/job_runner.py:573 _provider_failure_kind` already has a good, complete taxonomy:
`loi_nguoi_goi` · `resource_wait` · `rejected` · `ambiguous` · `retry`. It recognises them by
`isinstance` against **the LLM provider's exception classes**. Everything else falls to the
default branch: `"retry"`.

Auto Scan raises seventeen typed exception classes. **None of them was recognised.** All of them
fell through to `"retry"`.

Three measurable consequences:

| exception | what actually happened | what should happen |
|---|---|---|
| `MediaError` ("source has no audio stream") | retried **3×** — three queue slots, three waits, same answer | never retry; it is the customer's file |
| `GiongMoHo` / `DichMoHo` | retried — a call that **may already have been billed** | never auto-retry (I5/G7) |
| `MayBan` (synth busy) | burned an attempt on a condition that clears itself, then failed terminally after 3 | requeue after a wait; busy ≠ broken |

The fix is `apps/auto_scan_video/loi.py`: a **translation**, not a second taxonomy. It maps our
domain errors onto the platform's classes at the boundary in `thi_hanh`, which is the only place
that speaks both languages. Engine modules keep raising their own domain types — forcing them to
raise `jobq.LoiNguoiGoi` would make every engine module know about the job queue, which is the
boundary the app contract exists to hold.

⭐ A fifth category was added rather than reusing an existing name. Seven `Thieu*` classes mean
"an upstream artifact this stage needs is absent" — behaviourally identical to `NGUOI_DUNG` (do
not retry), but calling it *the user's error* is false: the customer did nothing. It is an
internal ordering inconsistency, e.g. COMPOSE running before TIMING produced anything. So
`THIEU_THUONG_NGUON` exists and is documented as translating to `LoiNguoiGoi` **only because the
platform has no "inconsistent state" kind** and no-retry is the correct behaviour. The name is
the only thing a person reading a log has; sending them to inspect the customer's upload for a
stage-ordering bug wastes the one clue they get.

## Everything else held, and the tests are the deliverable

Nine injected failure modes, all passing:

| injected | invariant proven |
|---|---|
| video with no audio stream | run → `error`, full refund, **1 attempt** not 3 |
| artifact bytes deleted, row kept | cache refuses it (I10) |
| checkpoint content altered | checksum mismatch detected, not reused |
| ffmpeg forced to fail | no `AsvAsset` row, settlement entry written |
| child process killed | typed error, no hang |
| cancel **before** any child ran | `cancelled`, full refund |
| cancel **during** the run | no late child resurrects it (I13) |
| two users concurrently | no cross-ownership in runs, stages, assets, or keys |
| settle called twice | balance unchanged |

Resource checks (items 7–8): no module anywhere in the app sets `CUDA_VISIBLE_DEVICES`; no
legacy GPU-lock path is reachable; the two GPU stages take their card from `ctx`; RENDER — which
copies the video stream — claims no GPU and declares no resource.

## Where the phase actually went: five wrong tests

Worth recording in full, because the pattern is the finding.

1. **`Job.credit_held` does not exist.** The test read a column that isn't there and died with
   `AttributeError` — a test that cannot go green guards nothing.
2. **`run.credit_held` is "how much *was* held".** I asserted it returns to 0 after settlement
   and concluded "10 credits still held after finish" — a false conclusion about a correct
   system.
3. **`credit.so_da_giu()` is also "how much *was* held".** My second guess, wrong the same way.
   🔴 The ledger is **append-only**: settlement writes a separate `SETTLE` entry rather than
   mutating the `HOLD` entry. So "how much is still held" has no answer anywhere — because it is
   not the right question. The invariant has to be stated as *a settlement entry exists* plus
   *the balance is right*.
4. **Balance arithmetic subtracted the hold twice.** The hold is deducted at run creation, so a
   balance sampled after creation already excludes it. `1000 == 990 - 0` fails; the real identity
   is `final == after_hold + held − charged`.
5. **`"gpu_env" not in getsource(...)`** — the **fifth** time in this build that a substring scan
   matched the module's own comment explaining why it does *not* do the thing. Replaced with AST.
   And a sixth, adjacent: the GPU-stage check demanded `gpu_env()` while `giai_doan_chep_loi`
   legitimately receives its card as `ctx.gpu_uuid`. Two platform-provided forms; the invariant is
   *the card comes from `ctx`*, not a particular syntax.

Also fixed in `test_418`: the AST scan that pins "every exception class is classified" missed
`ThieuNguon` (base written as `nhap_media.MediaError`, an `Attribute` not a `Name`) and
`KetXuatError` (its base class lives in a file later in alphabetical order). Now collects both
base forms and iterates to a fixed point — a test whose result depends on filename ordering is
measuring filename ordering.

⚠️ One ordering trap in the code itself is real and load-bearing: `KetXuatError` **subclasses**
`MediaError`. Asking `MediaError` first would classify every render failure — usually a transient
disk-full or killed subprocess — as a user error and refuse to ever retry it. `test_418` pins
that ordering explicitly.

## Exit evidence

`python tools/gate.py --phien asv` — ratchets all green
(`lint_app_contract`, `check_silent_except` 63/63, `check_bo_qua`, `check_dich_thieu` 343/343).
The only red steps remain the ones owned elsewhere: `chuoi chua dich` (781 vs 774, peer's
`dieu_khoan.py`), the peer's layering and `voice_tu_dien` failures, and the three
worktree-structural ones (RISK-14-02).

ASV-owned tests: **346 pass**, including under `-n 8`.

## Debt carried out of this phase

- **Worker death is simulated, not real.** `test_419` forces exceptions and kills subprocesses; it
  does not `SIGKILL` a worker mid-transaction. The platform's own `test_214` covers multi-process
  orphan reclaim, and Auto Scan inherits it — but no Auto Scan run has been interrupted by a real
  process kill (RISK-17-01).
- **GPU OOM and provider 429/auth are not injected.** Both need a real provider; the typed classes
  they would raise (`ProviderOomError`, `BanError`) are already mapped and unit-tested, but the
  end-to-end path is unproven (RISK-17-02).
- `CHO_KHI_BAN_S = 20` is chosen for safety, not measured.
