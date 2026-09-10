# Phase 09 — LTT Voice boundary and voice binding

**Verdict: PASS** (two requirements deferred to Phase 15 with reasons stated).
Source SHA at start `1c4e785`. Branch `phien/asv-v4`.

---

## 1. The reach-through the brief assumes does not exist

The objective says *"replace ASV's private LTT Voice reach-through with a stable
owner-app boundary"*. Phase 02 already withdrew that claim (V4-R02), and it is
still true today — verified name by name rather than assumed:

| ASV uses | in `BE_MAT_CONG_KHAI`? |
|---|---|
| `features.chuan_hoa`, `features.giai_giong`, `features.goi_cong` | ✅ |
| `sidecar_client` | ✅ |
| `text_pipeline`, `text_pipeline.chuan_hoa` | ✅ |
| `tham_so_cong_khai.TRAN_MOI_LUOT_SINH` | ✅ |
| `doc_man_api.ma_giong_cua_toi` | ✅ |

⇒ Requirement 7 ("remove ASV calls to private internals") again has **nothing to
remove**, and an AST test now proves it positively across the whole app tree.

⚠️ One apparent conflict, resolved by reading: the brief forbids "ASV sidecar
client", and `giong_noi.py:83` imports `sidecar_client`. But it is used for
**exactly one thing** — `san_sang()`, a readiness probe. That is asking the owner
whether it is up, not a second synthesis transport. And the owner exports it
deliberately.

## 2. What was actually blocking AUTO_MATCH (V4-R14, P0)

`apps/ltt_voice/giong_mau.py` already carried precisely the right data — 20
sample voices classified on three axes (`gioi`, `vung`, `phong_cach`) with a
`loc(...)` filter — and **none of it was exported**.

Closed with seven additive read-only names on both sides
(`loc`, `tim`, `hop_le`, `DANH_SACH`, and the three label maps). Create/edit/
delete stay where they were: LTT Voice's own screen.

⭐ `loc` is exported rather than making ASV walk `DANH_SACH` itself, because the
filter is a **rule** — and two copies of a rule are two copies that will drift.
A test forbids ASV from re-implementing the comparisons.

## 3. 🔑 The load-bearing decision: AUTO_MATCH **defers**, it does not default

`ADR-V4-001` D-V4-04 forbids AUTO_MATCH degrading into "use the default voice",
and V2 did exactly that — `routes.py:135` declared `giong_id: str = Form("")` and
an empty value took the default. That is a different thing entirely: a default
**reads nothing from the video**.

So `rang_giong.rang()` returns one of:

| state | meaning |
|---|---|
| `DA_RANG` | a voice is chosen, with `can_cu` recording why |
| `CHUA_RANG` | not enough evidence yet — **valid**, neither failure nor voice |

and `KetQua.ma_giong()` **raises** on `CHUA_RANG`. A function returning `""` here
would produce a synthesis run in the default voice **that nobody asked for** —
the precise outcome the design exists to prevent.

Two situations resolve to `CHUA_RANG`, and the second is the one worth naming:

- no ContentProfile yet (Phase 11 fills it)
- **the filter matched nothing** — not "take one anyway". Relaxing a constraint is
  the caller's decision, because the caller knows which axis matters most and
  this module does not.

### Why defer rather than pick a placeholder and fix it later

A temporary voice creates a window where the run **has a voice**, and any stage
that runs early binds to it. Phase 14 sizes sentences against the real voice's
reading speed, so a placeholder produces an adaptation that must be redone. A
readable "not yet" blocks that; a temporary value does not.

## 4. Ownership stays where it belongs

Owner checks are **not** re-implemented in ASV. `features.giai_giong` already
filters `owner_id`, handles the shared voice store, and drops inactive voices —
three things that are easy to get subtly wrong, and getting the first one wrong
means a customer's video is read **in someone else's cloned voice**.

So `_rang_khach_chon` calls the owner's function and lets it raise. Sample voices
skip that path entirely: they have no owner, and asking an ownership question
about them is a database round-trip for a question that does not exist.

An AST test pins that `rang_giong.py` synthesizes **zero milliseconds** of audio —
it never calls `goi_cong`, `sinh`, `synthesize`, or even `san_sang`.

## 5. Requirements deferred, with reasons

⛔ **Req 1 & 2** (owner-checked per-segment/batch synthesis returning durable
reference + measured duration + actual usage) are **not** done here, and that is
deliberate rather than an omission:

- The blocker Phase 00 identified was structural — `asv_stage` holds **one**
  `job_id` while per-segment TTS needs many — and Phase 05's `AsvWorkItem`
  removed it. The path is unblocked.
- But the brief's own phase index puts synthesis at **Phase 15**
  (`15_voice_synthesis_and_bounded_dubbing_fit`). Building the synthesis service
  here would mean writing the consumer before the producer's phase, with the
  billing prerequisite (§6) still unproven.

⛔ **Billing safety prerequisite**: not satisfied, and not needed yet — nothing in
Phase 09 makes a paid call. `rang_giong` reads a catalog and a database row.

⚠️ Two of the brief's required tests have no subject yet: *segment repeat
idempotency* is already pinned at the checkpoint level by `test_430`
(`UNIQUE(run_id, stage, item_key)`), and *no duplicate GPU lease* by `test_428`
(the pipeline's `tai_nguyen` declarations). Re-testing them here would restate
existing guarantees under new names rather than add one.

## 6. Tests and evidence

`tests/test_435_asv_v4_rang_giong.py` — **22 tests**, five sections: AUTO_MATCH
never defaults · ownership belongs to the owner app · ASV owns policy only ·
surface is additive · settings parsing.

**Layer 4 — six mutations, six reds:**

| Mutation | Caught by |
|---|---|
| AUTO_MATCH with no profile takes catalog[0] | `test_AUTO_MATCH_chua_co_ho_so_thi_CHUA_RANG...` |
| `ma_giong()` returns "" instead of raising | `test_doc_giong_tu_rang_buoc_CHUA_CHOT_thi_NEM` |
| accept USER_SELECTED with no voice id | `test_USER_SELECTED_de_TRONG_bi_tu_choi...` |
| skip the owner's ownership check | `test_giong_cua_NGUOI_KHAC_bi_tu_choi` |
| no candidates → take one anyway | `test_khong_ung_vien_nao_khop_thi_CHUA_RANG...` |
| unstable choice between two calls | `test_cung_dac_diem_thi_ra_CUNG_mot_giong` |

Layer 2: `test_400 401 409 418 421 425–435 85 330–339` → **540 passed, 3 skipped,
1 xfailed**. `lint_app_contract`: 20 apps, 0 ERROR, 0 WARN.
`speech.ltt` verified still present — this phase only added.

⭐ Two ratchets that caught earlier phases were satisfied **before** running them
this time: `rang_giong.py` went into `REBASE_MAP_V4.md` (11 ADD) and its two
exception classes into the error table, rather than waiting for `test_427` and
`test_418` to find them a third time.

## 7. Exit gate

**PASS.** LTT Voice owns synthesis, ownership and security; ASV owns only binding
policy; the catalog AUTO_MATCH matches against is exported read-only; and
AUTO_MATCH cannot silently become the default voice — pinned by six mutations,
not by convention.
