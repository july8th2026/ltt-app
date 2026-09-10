# PHASE 02 REPORT — CAPABILITY INVENTORY AND BOUNDARY FREEZE

## Verdict

**PASS**

## Source / HEAD

`phien/asv-v4` @ `c709a26` (Phase 01 commit) + this phase's diff.

## Objective

Inventory every relevant LTTSTUDIOSAPP capability before any new engine code, then freeze
reuse/extension decisions. `V4_CAPABILITY_FIRST`: *a "new code" recommendation without proof
of absence fails the phase.*

## Changed paths

| Path | Kind |
|---|---|
| `docs/auto_scan_video_v4/CAPABILITY_INVENTORY_V4.md` | new — 19-app census + per-need classification |
| `tests/test_426_asv_v4_kiem_ke_nang_luc.py` | new — 17 checks pinning the inventory's premises |
| `docs/auto_scan_video_v4/STATE_V4.md` | risk table: 2 withdrawn, 2 added |

No app code, no platform code, no migration. Phase 02 forbids engine migration and new
provider clients; neither happened.

## Before -> After

| | Before | After |
|---|---|---|
| capability picture | V2's matrix, written against legacy trees outside the repo | 19-app in-repo census with traced callers |
| ASV cross-app imports | believed to be **6 private reach-throughs (P0)** | **all declared**, both sides, linter-enforced |
| diarization | assumed available | exists, **not exported** — EXTEND |
| `AUTO_MATCH` | assumed to need new code | data exists in `giong_mau.py`, **not exported** — EXTEND |
| vision | assumed to need a new path | `dieu_phoi.goi` passes `messages` verbatim into a class literally named `CongVlm` — SUFFICIENT |

## Contracts / migrations

None changed. Two **future** additive extensions identified and specified, neither applied
here (Phases 07 and 09 own them).

## Tests and commands

```bash
python -m pytest tests/test_426_asv_v4_kiem_ke_nang_luc.py tests/test_425_asv_v4_hop_dong_san_pham.py -q
```
→ **36 passed, 1 xfailed in 4.20 s**

## The correction this phase exists to make

Phase 00 recorded, as a **P0**:

> V4-R02 — Auto Scan reaches through into LTT Voice **private internals** at five sites […]
> `V4_CAPABILITY_FIRST` names "TTS sidecar client" and "copied LTT Voice text-normalization
> constants" as **forbidden inside Auto Scan**.

That was wrong, and it was wrong in an instructive way: I read an import list, matched the
module names against the pack's forbidden list, and stopped. I never checked whether the
platform had a notion of a *declared* boundary.

It has one, and it is stronger than what the V4 pack assumes exists:

```
apps/<slug>/__init__.py     BE_MAT_CONG_KHAI = {("apps.x.mod", "name"), ...}
tools/lint_app_contract.py  APP_DUOC_DUNG_APP = {("caller","callee"): {...}}
```

Both sides must agree; the linter errors otherwise; it runs inside `tools/gate.py` and passed
in the Phase 00 baseline. `apps/ltt_voice/__init__.py` declares all six names ASV uses, each
with a written justification — including why `sidecar_client` is listed (only to ask
`san_sang()`) and why `features.chuan_bi_van_ban` is deliberately **not** listed (it chunks as
well as normalises, and splitting a line of dialogue changes voice mid-sentence).

Tracing the real caller confirms ASV honours the surface exactly:

| Site | Uses | Declared? |
|---|---|---|
| `giong_noi.py:83` | `sidecar_client.san_sang()` only | ✅ and this is the stated purpose |
| `giong_noi.py:102` | `features.chuan_hoa`, `features.giai_giong` | ✅ ownership check is mandatory |
| `giong_noi.py:133` | `text_pipeline.chuan_hoa` — **not** `features.chuan_bi_van_ban` | ✅ exactly as the surface instructs |
| `giong_noi.py:149-150` | `features.goi_cong`, `TRAN_MOI_LUOT_SINH` | ✅ refuses to self-chunk, raises instead |
| `gia.py:81` | `doc_man_api.ma_giong_cua_toi` | ✅ owner-filtered inside the function |
| `dich_thuat.py:64` | `ltt_llm.ngan_sach` | ✅ single budget source of truth |

**V4-R02 and V4-R03 are withdrawn.** Had they stood, Phase 09 would have spent itself
rebuilding a boundary that already exists — the precise failure `V4_CAPABILITY_FIRST` is
written to prevent, arrived at from the opposite direction.

## The finding that reorders the work

`speech.ltt` → `ltt_voice.synthesize` is a proper public ToolSpec with `vieneu_gpu`×1
admission. Auto Scan does not use it. V2 Phase 12 recorded why: one job produces one file
keyed on `job_id`, and **`asv_stage` holds exactly one `job_id` per stage**. Per-segment TTS
needs N units under one stage, so delegation had nowhere to checkpoint.

That is a **schema** limit, not a discipline failure. Which means:

> Phase 09 is not unblocked by resolve. It is unblocked by Phase 05's `AsvWorkItem`.

Once an owner-scoped, fingerprinted per-segment checkpoint row exists, delegating to
`ltt_voice.synthesize` becomes representable — and only then is it worth deciding whether
delegation beats the in-process call. Phase 09 must **re-evaluate with evidence**, not assume
either answer. Recorded in the inventory §3 so Phase 09 does not rediscover it.

## Self-review findings (hostile pass)

**Did I duplicate an existing capability?** The near miss was `test_426` becoming a second
copy of `lint_app_contract.py`. It is not: the linter enforces *which app may call which*;
`test_426` checks that the specific names the inventory *counted on* still exist. An app can
keep `BE_MAT_CONG_KHAI` while dropping one entry from it, and only the second check notices.
Called out in the file's docstring.

**Did I prove absence, or assume it?** Proved, and the first attempt was wrong. The ABSENT
scan initially searched raw file text and immediately failed on `ContentProfile`, `EditPlan`
and `DubbingFit` — found inside a **docstring I had written myself in Phase 01** explaining
why the target language is locked. A presence test that fires on prose turns *writing
documentation* into a violation. Rewritten to walk the AST and consider only identifiers
(`ClassDef`, `FunctionDef`, `Name`, `Attribute`), so comments and docstrings cannot trigger it.

**Does the ABSENT detector actually detect?** `test_bo_do_ABSENT_that_su_bat_duoc` runs it
over three shapes that must fire (class, function, attribute) and two that must not
(docstring, comment). Without that pairing, `_ten_dinh_danh_chua` could return `False`
unconditionally and every ABSENT verdict would be a green light wired to nothing — the same
trap `test_401` guards against.

**Did I broaden scope?** No code migrated, no client written, no surface extended. The two
EXTEND decisions are specified and deferred to their owning phases.

**Am I trusting the pack over the code?** No — this phase is a worked example of the reverse,
twice: once on the boundary mechanism, once (in Phase 01) on the language justification.

## Risks / external evidence

| ID | Change |
|---|---|
| V4-R02 | **WITHDRAWN** — declared boundary, not reach-through |
| V4-R03 | **WITHDRAWN** — same |
| V4-R13 | **NEW**, P1 — diarization exists in `ai_workflows` but is unexported (Phase 07) |
| V4-R14 | **NEW**, P0 — sample-voice catalogue with gender/region/style filters exists in `giong_mau.py` but is unexported; without it `AUTO_MATCH` degrades to "the default voice" (Phase 09) |

No new external evidence required by this phase.

## Exit gate proof

> *PASS when every V4 MVP capability has an owner and no capability decision is based on
> assumption.*

| Requirement | Evidence |
|---|---|
| every need has an owner | 21 rows in `CAPABILITY_INVENTORY_V4.md` §2, each with owner, exact path, real caller, resource, billing and classification |
| classifications are evidenced | 13 SUFFICIENT (each traced to a live caller), 2 EXTEND (each shown to exist but be unexported), 6 ABSENT (each proven by AST scan) |
| ASV reach-throughs identified | done, and the answer is **none** — with the mechanism that proves it named and tested |
| no decision by assumption | the two assumptions I *did* carry in from Phase 00 were tested and both failed |
| dependency rules frozen | inventory §6, five rules |

**PASS → continue automatically to Phase 03.**
