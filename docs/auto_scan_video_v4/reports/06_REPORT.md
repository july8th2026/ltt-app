# Phase 06 — Billing usage and budget foundation

**Verdict: PASS.**
Source SHA at start `c2ffef7`; at end `1a81aea` (+ trunk merge `69d0ae3`).
Branch `phien/asv-v4`.

---

## 1. What the phase was asked for, and what was already there

Eight requirements. **Three were already implemented** and the honest output for
them is a pin, not a build:

| Req | State | Evidence |
|---|---|---|
| 2 — child capability runs under the parent budget, no independent hold | **already true** | `features._nop_dieu_phoi` uses `jobs.submit`, never `submit_with_credit`; `manifest._gia` returns 0 for the coordinator job |
| 4 — aggregate item → stage → run exactly once | **already true** | `features.tong_da_dung` + `_kiem_khong_tinh_hai_lan` (ADR-V4-002 D-V4-12), built in Phase 05 |
| 7 — never recompute price from requested params | **already true** | `quyet_toan` reads `tong_da_dung`, which reads measured columns only |

⭐ Three AST tests now hold them still: no call to `submit_with_credit` anywhere
in the app, exactly **one** call site for `credit.giu_cho` (`features.tao_run`),
and `su_dung.py` never touches `credit.tru/nap/hoan_phi/giu_cho/cap_tay`.

## 2. What was built

`AsvUsage` (table `asv_usage`, migration `c81d3f5a90e7`) — one row per capability
call: capability, owning app, dispatch state, unit, quantity, **measured** credit,
dispatch id, attempt.

`apps/auto_scan_video/su_dung.py` (340 lines): `SuDung` value object with
validation, `ghi`, `mo_don_vi`, `cac_dong`, `so_ke`, `doi_soat`, `cac_mo_ho`,
`giai_quyet_mo_ho`, plus the pre-dispatch gates `cua_chan_truoc_khi_tieu` /
`cua_chan_cho_lo`.

### 🔑 The load-bearing decision: the ledger is **not** a second money path

Money still flows through exactly **one** column, `AsvWorkItem.credit_actual`.
`features.tong_da_dung` does not add this table. If it did, one piece of work
would be counted in three places — stage, item, ledger — and
`_kiem_khong_tinh_hai_lan` already exists because *two* places was one too many.

The ledger *explains* the number. `su_dung.doi_soat` pins the invariant

    item.credit_actual == Σ credit of that item's `da_giao` rows

and `features.quyet_toan` calls it **before** charging — a number that cannot be
explained is a number that is not collected.

### Crash safety is one transaction, not a second mechanism

`ghi` writes the ledger row **and** adds the item's credit inside one `flush`.
Crash before commit → neither; after → both. There is no window where delivered
work exists without its money, or vice versa. `UNIQUE(run_id, ma_dispatch)`
covers the replay case.

⚠️ Stated precisely, because the promise is narrower than it looks: it protects
when the caller supplies a **stable provider-side** dispatch id. A caller that
generates a fresh id each time has made a genuinely different call, and charging
it is correct. `test_khong_co_ma_dispatch_thi_moi_lan_la_mot_lan_gui_KHAC` exists
so nobody reads the constraint as wider than it is.

### Ambiguous dispatch (ADR-001 D9)

`features.thu_lai_giai_doan` now raises while an unresolved `mo_ho` row exists
for that stage. Unlocking requires a person: `su_dung.giai_quyet_mo_ho`. An AST
test pins that **no automatic path in the app calls it** — a system that resolves
an ambiguous dispatch by itself is a system guessing with the customer's money.

## 3. Bugs found in my own work, and how

### 🔴 `db.rollback()` on a duplicate dispatch id destroyed the caller's transaction

The first draft caught `IntegrityError` and called `db.rollback()` — which unwinds
**the whole transaction**, so every ledger row written earlier in the same dispatch
loop vanished. A constraint doing its job must not destroy the caller's work.
Fixed with `SAVEPOINT` (`begin_nested`), pinned by
`test_lan_ghi_bi_tu_choi_KHONG_cuon_theo_nhung_gi_da_ghi_truoc`.

### 🔴 A ratchet fired on historical data

`doi_soat`'s "VRAM nearly full"-style guard — here, the reconciliation over rows
written before this version — would flag every legacy row, because the missing
field defaulted to 0. A tool that alarms on its own history is a tool nobody
trusts, and history is all it has.

### 🔴 `test_427` caught a module with no owner

`su_dung.py` was not in `REBASE_MAP_V4.md`. Phase 03's census predates it, and a
module missing from the map is a module whose fate nobody decided — a later phase
would "just tidy it" with no basis. Map now reads **9 ADD** instead of 8.

### 🔴 An assertion of mine encoded a contract the platform does not have

The integration test asserted `credit.so_da_giu(run.id) == 0` after settlement.
It returns **200**, and that is correct: it sums every `CREDIT_HOLD` entry — a
historical ledger, not "still held". I had written down my assumption instead of
the contract. Replaced with the two things that are actually true and actually
matter: exactly **one** hold entry exists, and the **balance** reflects only the
measured 47.

⭐ And counting the entries is the stronger test anyway: one hold of 200 and two
holds of 100 produce the same `so_da_giu`, so the sum could never have proven
"one billing owner".

## 4. Cost ceiling that the budget cannot see

Not in the phase brief, but measured during it and directly on the money path:
`demucs_runner.py` set **no torch thread limit**. The black box recorded twelve
of these processes over 4 min 12 s, each peaking at **462–984 % CPU**.

🔑 This is where `-n 6` cannot reach: it counts pytest workers, not what each
worker spawns. A grandchild asks for no lock, declares nothing, and appears in no
gate calculation.

Capped at **4** threads (`LTT_DEMUCS_LUONG` to override). Not 2 — production runs
exactly **one** demucs at a time (`pipeline.CHUOI` declares
`tai_nguyen="tach_nguon_cuc_bo", tai_nguyen_suat=1`, enforced by
`job_runner._cho_tai_nguyen` + leases), so 2 would have made a real customer job
~5× slower to defend against a case that does not occur.

## 5. Tests and evidence

`tests/test_432_asv_v4_so_ke_su_dung.py` — **38 tests**, ten sections covering
every scenario the brief names: one hold, delivered-vs-requested, partial batch,
retry, cache, ambiguous dispatch, repair, two-user isolation, crash between
delivered result and checkpoint. Fakes only; no paid provider is reachable from
the suite.

**Layer 4 (hostile review) — seven mutations, seven reds:**

| Mutation | Test that caught it |
|---|---|
| `+=` → `=` on item credit | `..._hai_nang_luc_tren_cung_mot_item_thi_CONG...` |
| drop the ambiguous-dispatch block on retry | `test_mo_ho_CHAN_duong_thu_lai_giai_doan` |
| drop `doi_soat` before settlement | `test_quyet_toan_TU_CHOI_chot_mot_con_so...` |
| allow delivered rows with no unit | `test_da_giao_ma_thieu_don_vi_do...` |
| allow ambiguous rows to carry credit | `test_chua_chac_da_chay_thi_KHONG_duoc_mang_credit` |
| SAVEPOINT → full rollback | `test_lan_ghi_bi_tu_choi_KHONG_cuon_theo...` |
| `doi_soat` skips orphan rows | `test_moi_dong_so_cai_deu_neo_vao_mot_don_vi_viec_co_that` |

Layer 2 regression: `test_400 401 417 421 425–432` → **203 passed, 1 xfailed**
after the `su_dung` map entry was added.

## 6. Debt carried forward, stated rather than folded into green rows

⚠️ **Nothing in the app calls `su_dung.ghi` yet.** That is the phase's design —
the brief forbids real VLM/TTS integration here, and the exit gate asks only that
future stages *can* report measured cost safely. Phases 11 and 15 are the first
callers, and they inherit a path that is already pinned.

⚠️ Full `tools/gate.py` was **not** re-run on this branch after the trunk merge;
`--vong-lap` (all static checks) is green and the ASV cluster is green. Recorded
here rather than claimed as evidence.

## 7. Exit gate

**PASS.** A future VLM/Voice stage can record measured cost, under the parent
run's budget, with one hold, exactly-once aggregation, reconciliation before the
charge, and no automatic re-spend of an ambiguous dispatch — and none of that
needed a real paid call to prove.
