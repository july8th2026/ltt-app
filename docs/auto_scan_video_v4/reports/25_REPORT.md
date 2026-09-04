# Phase 25 — Security, migration and production hardening

**Verdict: PASS**, with one hardening defect fixed, one retention gap recorded,
and a runbook that names what it cannot fix.
Branch `phien/asv-v4`. New: [`RUNBOOK.md`](../RUNBOOK.md),
`apps/auto_scan_video/san_sang.py`, `tests/test_451_asv_v4_lam_cung.py`.

---

## 1. 🔑 The test suite and the server were never compared

Tests build the schema with `Base.metadata.create_all()`. The server runs
`alembic upgrade head`. Nothing in this repository — for **any** app — had ever
compared the two.

That gap is silent by construction: a column added to `tables.py` without a
migration passes every gate and breaks on the first deploy, with an error about a
column that does not exist.

Measured: a temporary database, `alembic upgrade head`, then
`compare_metadata` against the models.

**ASV tables: zero differences.** Migrations and models agree exactly.

⚠️ Thirteen differences exist outside ASV — SQLite rendering artifacts
(`BIGINT` vs `BigInteger` on seven voice tables), a unique-index difference on
`developer_api_keys`, two foreign keys on platform tables. They are pre-existing
and not this phase's to fix; the check is scoped to `asv_*` deliberately, because
a check that fails for someone else's reason is a check that gets switched off.

The guard bites: adding a column to `AsvStage` without a migration turns it red.

## 2. 🔴 Redaction covered the command and leaked through stderr

`ket_xuat.lenh_da_che` masks paths in the **command line** of a failed render, and
its docstring explains exactly why: full paths expose the server's disk layout and
the Windows user's real name.

The same diagnostic record also stores `stderr[-2000:]` — **unmasked**. And ffmpeg
prints full paths there:

```
Output #0, mp4, to 'C:\Users\<real name>\AppData\Local\Temp\asv-render-…\ra.mp4':
```

So the front door was locked and the back door was the same information, into the
same stored record.

Fixed with `van_ban_da_che`, applied to stderr. Basenames survive — they are what
makes a diagnostic useful; directories do not.

### ⚠️ And the first version of the masker leaked the exact thing it was protecting

It ended a path at the first whitespace. Windows paths **contain spaces**, and the
space in this one is inside the user's name:

```
before:  '<da-che>/Thang Tuong\AppData\Local\Temp\asv-render-abc\ra.mp4'
```

The mask ended at `C:\Users\Thang` and printed `Tuong\AppData\…` right after it.
A terminator must be what actually ends a path in the text — a quote, a bracket,
end of line — not what usually does. Verified on six shapes including UNC
(`\\server\share\…`) and paths with spaces, and pinned by a second test that
ffmpeg's *non-path* lines (`Duration:`, `-c:v libx264`) come through untouched:
over-masking a diagnostic until it diagnoses nothing is also a defect.

## 3. IDOR across all six V4 object types

Phase 05 covered `asv_run`, `asv_stage`, `asv_asset`. Phases 06 and 19 added
**two more tables carrying customer data** — `asv_work_item` (which segment was
done) and `asv_usage` (what was spent, where). A new table is a new surface, not a
detail of an old one.

Pinned: every row of both tables carries `owner_id` in a **column** (not merely in
a storage path), a second user sees none of them, and `lay_run`, `thu_lai_giai_doan`,
`huy_run` and `asset_cua` all refuse another owner's run — including with the
correct id in hand.

## 4. ⚠️ Retention is a label with nothing behind it

`HAN_TRUNG_GIAN = 30 days` is stamped on every promoted artifact, and
`kiem_toan_ven` reports `expired` when the date passes. Two things are missing:

**Nothing ever sweeps.** No scheduled job reads `expires_at` for ASV artifacts.
`assets.don_theo_run` exists and **has no caller** — the fourth capability in four
phases that was built and never connected (after the VLM, the stage cache, and the
hardware encoder). Storage grows without bound; `expires_at` only changes a verdict
if something happens to read it.

**The deliverable shares the scratch class.** `thi_hanh.chay_giai_doan` calls
`promote_va_ghi` without `han`, so the customer's finished video gets the same
30-day intermediate window as the working files — while `assets.py` states the
deliverable "is written with its own retention".

⛔ Not fixed: how long a customer's video is kept is a business decision with a
storage bill attached. Pinned with `xfail(strict=True)`. **Owner: Phase 27.**

### 🔴 And that pin was wrong the first time, in a way worth recording

Its first version compared `expires_at` of the render against `expires_at` of
`media_prepare` — and it **passed**. Not because retention classes differ, but
because RENDER is promoted ~70 seconds later, so its expiry is 70 seconds later.
It was measuring the clock.

⭐ Third instance in three phases of the same fault: Phase 23's cache tests only
exercised a function that always says no; Phase 24 aimed a mutation at a field no
test reads; here an assertion passed for a reason unrelated to its subject. The
fix each time is the same discipline — **compare the property, not a proxy for
it**. Now it compares retention *windows* (`expires_at − created_at`), and
correctly reports that both are 30 days.

## 5. Readiness: ASV can now answer "can this machine run me"

`/health/ready` answers two questions — is the database alive, is the process
orphaned — and neither says anything about ffmpeg, the voice sidecar, the model
door, or the hardware encoder. So a run can pass four stages and fail at the fifth
on an unconfigured dependency while readiness says `ready`, and the operator finds
out **after** the customer waited and credits were held.

`apps/auto_scan_video/san_sang.py` answers it: five dependencies, each `bat_buoc`
or `tuy_chon`, each with a one-line "what to do if missing".

⛔ **Deliberately a function, not a route.** This phase forbids feature expansion,
and a new endpoint is new public surface. The runbook calls it, the tests call it,
and if the platform ever opens a contract for apps to contribute to
`/health/ready`, that will call it too.

🔑 **Three states, not two.** `chua_do` — the question could not be asked — is not
folded into `khong`. A broken probe and an unconfigured dependency demand different
actions from the operator, and `giong_noi.san_sang()` swallows every exception into
`False`. A failed probe **never** counts as ready.

⛔ And the summary returns only `co`/`khong`, never the value of an environment
variable. A status report that leaks a token is a status report nobody may look at.

Run on this tree, it immediately says what is true: not ready — no voice token, no
ASR sidecar — with the exact remedy for each.

## 6. A runbook that also names what it cannot fix

[`RUNBOOK.md`](../RUNBOOK.md) covers the five required drills: stuck run, resource
wait, ambiguous provider, repair exhausted, storage corruption. Each answers three
questions in order — where to look, what it means, what to do — and every write
operation is marked 🔻 and goes through an existing function, because a hand-typed
`UPDATE` on `asv_stage` bypasses `cap_nhat_giai_doan` and its `revision` guard.

It grounds "is this slow or stuck?" in Phase 24's numbers (`audio_prepare` ≈ 22 s,
`transcribe` ≈ 34–41 s for a 32 s source, both scaling with length) rather than in
a feeling.

⭐ Its last section lists what it **cannot** fix — the smart preset that cuts
nothing, the cache that never hits, the CPU encoding, the artifacts nobody sweeps —
so an operator does not spend an outage hunting for a button that does not exist.

A test reads the runbook and checks every `module.function` it names still exists,
in both directions: a runbook pointing at a renamed function sends the on-call
person into a wall at the moment they most need it.

⚠️ Written in Phase 25 and **not yet drilled on the server**. Read-only steps are
safe; write steps need the project owner.

## 7. Limits

* Every `subprocess.run` in the app carries a `timeout` — checked by walking the
  AST of every module, so a new call site is covered without anyone remembering.
  A subprocess without a ceiling holds a worker forever, and the platform's runtime
  ceiling cannot save it because the job keeps heart-beating.
* `TRAN_TAI_LEN = 90 MB` stays below Cloudflare's 100 MB cut, so an oversized file
  gets a Vietnamese sentence from the product rather than a Cloudflare 413.
* The feature flag still runs **before** `require_login` (V4-R11) — after it, a
  "closed" route still redirects to `/login` and thereby admits it exists.

## 8. Tests and mutation results

`tests/test_451_asv_v4_lam_cung.py` — **14 tests + 1 `xfail(strict)`**.

**Mutation testing: 8 mutations, 8 red** — after two corrections:

* adding an un-migrated column needed the anchor re-aimed at the real source text;
* and "count `chua_do` as ready" stayed green until the test was fixed, because
  another required dependency was already `khong` on this machine, so the assertion
  held for the wrong reason. It now asserts a green baseline first, then breaks one
  variable — the only shape in which a single-variable claim can be tested.

Regression: ASV cluster and V4 invariant round green (see commit).

## 9. Debt carried forward

⚠️ **Nothing sweeps expired artifacts** (§4) — the storage bill grows forever.
⚠️ **The deliverable has no retention class of its own** (§4).
⚠️ **Readiness is not surfaced** anywhere an operator or a probe would look; it
needs a platform contract change to reach `/health/ready`.
⚠️ **The runbook is undrilled** on the real server.
⚠️ **Ambiguous ledger rows still need a human**, and nothing tells that human they
are waiting (carried from Phase 23).

## 10. Exit gate

**PASS.** Migrations and models agree for every ASV table and a guard keeps them
that way; the diagnostic record no longer leaks server paths or user names through
either channel; all six V4 object types are owner-scoped in columns and refuse a
second owner; limits, timeouts and the feature flag are pinned; and an operator can
now ask this machine whether Auto Scan can run at all, and get an answer that
distinguishes "not configured" from "could not ask".

⚠️ No P0 remains. The P1 recorded here is retention: a policy that is declared,
never enforced, and applied equally to scratch material and to the thing the
customer paid for.
