# Phase 20 — Operational observability and cost explainability

**Verdict: PASS.**
Source SHA at start `13a6ade`. Branch `phien/asv-v4`.

---

## 1. Three things existed and had never met

The pieces were all there and each was sound: `su_dung.so_ke` (the ledger),
`AsvWorkItem` (what was actually done, per unit), and `quan_sat.dong_thoi_gian`
(stage and job state). They lived in **three separate queries**.

So an operator asked "why did this run cost that much" had to join them by hand —
performing a reconciliation that nothing checked. Phase 20's job is to make that
join exist, and to make it answer.

⭐ A stage marked `succeeded` says nothing about **how much work actually
happened**. Two runs can both read `succeeded` while one called the model 200
times and the other called it zero — and their invoices differ completely. The
timeline now carries per-stage item counts, so the difference is visible instead
of inferred.

## 2. 🔴 The reconciliation runs in both directions, and only one is easy

    unit with credit but no ledger row  -> money charged with no receipt
    delivered ledger row but no unit    -> work billed that nothing recorded

Checking one direction leaves the other open — and mutation testing showed that
is not hypothetical: **removing the first check stayed green**, because in the
normal path both are written in one transaction by `su_dung.ghi`, so the state
never arises by accident.

⛔ And that direction is the **expensive** one: a unit recording `credit_actual > 0`
with no surviving ledger row is a charge against a customer **with no supporting
document**.

⭐ `su_dung.doi_soat` already pins this as a **constraint** — it raises on
mismatch, correctly. `quan_sat.doi_soat_nhanh` deliberately does **not** raise: an
observability surface must answer *while the system is broken*, which is exactly
when someone needs it.

### A test that was constructing an impossible state

My first attempt built the orphan by calling `su_dung.ghi` with a nonexistent
item key — and it did not work, because `ghi` **creates** the work item. An orphan
row cannot be produced through the API at all.

⭐ But it can still happen — by another road: a unit deleted or invalidated while
the ledger row remains (a cleanup, a migration, a manual patch). That is the real
case, and it is what the check exists for. A test that can only build the state
through the API would conclude "this cannot happen" — while the paths the check
guards are precisely the ones that **do not go through the API**.

Both orphan directions are now constructed the way they actually arise, and both
mutations die.

## 3. The customer sees cost, not the machine

`tom_tat_cho_khach` reports steps-completed-of-total and cost **by capability**.

⛔ It does not name internal stages. Leaking them turns every stage rename into a
UI change, and makes the chain's shape public information.

⛔ It does not name `app_chu` — the internal provider app behind a capability —
nor the owner id, fingerprints or job ids. Those are not lost; they are simply not
the customer's screen, and the operator view still carries all of them. Four
separate mutations, one per leak, all die.

## 4. Tests and evidence

`tests/test_446_asv_v4_quan_sat_chi_phi.py` — **14 tests**: two-way
reconciliation · per-stage work-item counts · the customer summary · four leak
checks · two-user isolation.

**Mutation testing — 11 mutations, 11 red** (after the hole above).

Regression: ASV cluster **1021 passed**, 3 skipped, 1 xfailed.

## 5. What the audit found in the Phase 06 foundation

Nothing broken. The invariant `item.credit_actual == Σ delivered rows` holds
across every chain run in the suite, the two-user isolation pin still holds, and
`so_ke` groups by `(app_chu, nang_luc, don_vi)` rather than summing across units —
which is what stops it from adding 1,200 tokens to 12 seconds.

⇒ No billing change was made. The phase permits one only on **proven** defect, and
there was none to prove.

## 6. Debt carried forward

⚠️ **Resource waits are not surfaced.** The phase asks for them; `job_events`
carries the platform's own events and they appear in the operator timeline, but
nothing extracts "this stage waited N seconds for `tach_nguon_cuc_bo`" as a
number. It needs a platform-side timestamp that does not exist yet, and inventing
one in the app would be the second owner of a platform fact.

⚠️ **Repair cycles are not in the timeline.** Phase 19's plan is computed but not
driven, so there is nothing durable to report yet. The two are the same piece of
work.

⚠️ **Cache hits are counted indirectly.** `so_doan_dung_lai` exists in the voice
stage summary; it is not aggregated into the timeline's item counts, so an
operator sees "20 units done" without seeing "12 of them were reused".

⚠️ **Worker-restart survival is untested here.** The evidence is durable by
construction (all of it is committed rows), and `test_419` already covers
crash/restart for the chain — but this phase adds no restart test of its own.

## 7. Exit gate

**PASS.** An operator can open one view and account for every worked and charged
unit from committed rows, with the reconciliation reported rather than assumed —
in both directions, including the one that only arises off the API path. The
Phase 06 accounting invariants remain green and untouched.
