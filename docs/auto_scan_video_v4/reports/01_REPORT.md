# PHASE 01 REPORT — PRODUCT CONTRACT SUPERSESSION

## Verdict

**PASS**

## Source / HEAD

`phien/asv-v4` @ `706faca` + this phase's diff. Baseline from Phase 00 unchanged.

## Objective

Create the authoritative V4 product ADR and freeze a real MVP before implementation, so that
no later engine phase has to make a product decision — and so the superseded dubbing-only
contract cannot silently reassert itself.

## Changed paths

| Path | Kind |
|---|---|
| `docs/auto_scan_video_v4/adr/ADR-V4-001-hop-dong-san-pham.md` | new — the decision |
| `apps/auto_scan_video/hop_dong_v4.py` | new — the decision, machine-readable |
| `tests/test_425_asv_v4_hop_dong_san_pham.py` | new — 20 checks |
| `docs/auto_scan_video/MVP_CONTRACT.md` | **banner only**, nothing below it edited |
| `ho_so_he_thong.txt` | regenerated (derived file; the new module made it stale) |

No engine, no route, no job handler, no migration, no UI touched.

## Before -> After

| | Before | After |
|---|---|---|
| product definition | "not an editor", dubbing only | Vietnamese smart-localization editor, two presets |
| presets | none (one implicit path) | `localize_preserve_picture` · `smart_localize` |
| smart-cut | `OPTIONAL_POST_MVP` | **required**, constrained to keep/cut, original order |
| target language | `vi`, justified by a **false** premise | `vi`, justified by evidence coverage (D-V4-02) |
| voice modes | one form field, empty ⇒ platform default | `USER_SELECTED` · `AUTO_MATCH`, and they are different things |
| contract enforceability | prose in a 245-line markdown file | prose **plus** constants **plus** 20 tests |

## Contracts / migrations

`PHIEN_BAN_HOP_DONG = "auto_scan_v4_mvp"` supersedes `auto_scan_mvp_v1`. No database change,
no Alembic revision, no schema touched. `hop_dong_v4.py` is declaration only — it has no
engine call, no DB access, no network, and exactly one function, a module-level consistency
check that raises at import.

## Tests and commands

```bash
python -m pytest tests/test_425_asv_v4_hop_dong_san_pham.py -q
```
→ **19 passed, 1 xfailed in 0.24 s**

```bash
python -m pytest tests/test_400_asv_bat_bien_thi_hanh.py tests/test_401_asv_ranh_gioi_va_artifact.py \
                tests/test_402_asv_mach_doc_gia.py tests/test_413_asv_be_mat_va_routes.py \
                tests/test_421_asv_tach_khoi_di_san.py -q
```
→ **66 passed in 55.51 s**

```bash
python tools/lint_app_contract.py     # Apps quet: 19 | ERROR: 0 | WARN: 0  -> PASS
python tools/check_silent_except.py   # 63 | moc: 63                       -> PASS
python tools/gate.py --quick --phien asv-v4
```
→ **`RESULT: PASS`** (3 frontend steps self-declare BOQUA: no `node_modules` in this worktree)

### One in-scope failure, found and fixed here

The first `--quick` run came back `FAIL (1/24)` on `system profile`:

```
STALE: ...\ho_so_he_thong.txt
```

Adding `apps/auto_scan_video/hop_dong_v4.py` made the generated source map stale.
`python tools/build_system_profile.py` regenerated it (+451 / −8 lines) and `--check` then
passed. Recorded rather than quietly re-run, because "a derived file went stale" is the
cheapest possible signal that a real file was added, and a phase report that hides it is
hiding the only trace.

## Invariant regression

`python -m pytest tests/test_400… tests/test_401… -q` → **24 passed**, unchanged from the
Phase 00 baseline. V4's own curated invariant suite is Phase 04's deliverable.

## Self-review findings (hostile pass)

**Did I duplicate an existing capability?** No. `hop_dong_v4.py` deliberately declares no
`job_type`, no stage, no price and no display string — those live in `pipeline.py`, `gia.py`
and the i18n catalogue respectively. Mixing them in would mean renaming a stage silently
changes the product contract.

**Did I broaden scope?** Two edits deserve the question:
- Touching `docs/auto_scan_video/MVP_CONTRACT.md` — allowed ("docs that lock product
  contract"), and it is additive: a banner above line 1, nothing below it altered. A test
  (`test_van_giu_nguyen_phan_KHONG_bi_thay_the_cua_hop_dong_cu`) now pins that T1–T12,
  ADR-003, −14 LUFS and ±0.50 s are still present in that file.
- Adding a module under `apps/` — allowed ("minor schema constants … for contract tests, not
  behavior"). It is constants plus one import-time assertion.

**Is `hop_dong_v4.py` dead code?** Today, yes — nothing in the product imports it; only
`test_425` does. That is honest and stated. It becomes load-bearing in Phases 12 (EditPlan)
and 21 (UI). The alternative — waiting until Phase 12 to write the contract down — is what
produced V2's Phase 21 stop.

**Is §1 of the test file a tautology?** Partly, and I nearly shipped it as one. Constants
asserting their own values prove nothing. §1 earns its place only because §2 ties the
declaration to a *different document* and §3 ties it to the *executable pipeline*. Called out
in the file's own docstring so a reader does not over-trust the green count.

**Did I add a silent fallback?** No. The opposite: `_kiem_tra_hop_dong()` raises at import,
and `test_hop_dong_tu_no_luc_nap_neu_mau_thuan` proves it actually fires by monkeypatching a
contradictory table — the same "prove the detector detects" pairing `test_401` uses.

**Did I take the pack's word for anything?** One place, and it was wrong. See below.

## The finding this phase was nearly going to copy forward

`V4_MVP_PRODUCT_CONTRACT.md` states the target language is Vietnamese *"because the shipped
LTT Voice capability is Vietnamese."*

```
apps/ltt_voice/lan_ngon_ngu.py:6    VieNeu-TTS v3 Turbo song ngu that,
                                    model card khai `language: ["vi", "en"]`
apps/ltt_voice/lan_ngon_ngu.py:91   NHAN_LAN = {"vi": ..., "en": ...}
```

The TTS is **bilingual**. The decision to ship `vi` only is still right, but for a different
reason: `ContentProfile`, `EditPlan`, `DubbingAdaptation`, `DubbingFit` and three semantic QC
layers have evidence for exactly one language.

Why this is worth a section rather than a footnote: the wrong reason is *self-destroying*.
The first future session to open `lan_ngon_ngu.py` sees `["vi", "en"]`, concludes the
restriction was a misunderstanding, and widens it — having verified nothing about translation
or QC quality in English. So the correction is recorded in three places that session will
actually be standing in: the ADR (D-V4-02), the constant's own docstring, and a test
(`test_ltt_voice_ho_tro_HAI_lan_nhung_hop_dong_asv_van_chi_mot`) that goes red on exactly that
move and says why.

## A second thing the code said and the docs did not

V2's UI exposes **two** settings — `che_do` (timing mode) and `giong_id`
(`routes.py:134-135`). `MVP_CONTRACT.md` §6 declares **four**: `voice_profile`, `timing_mode`,
`keep_background`, `background_gain_db`. `keep_background` and `background_gain_db` were
frozen as contract and never surfaced.

Not fixed here — Phase 21 owns UI truth (G16), and Phase 01 is forbidden from implementing UI.
Recorded in `STATE_V4.md` as V4-R12 so it is found by a gate rather than by a customer who
cannot turn the background off.

## Risks / external evidence

No new external evidence required by this phase. One deliberate RED target is open:

| Marker | Test | Owner | Meaning |
|---|---|---|---|
| `xfail(strict=True)` | `test_chuoi_thi_hanh_biet_den_preset` | **Phase 12** | The contract declares two presets; `pipeline.CHUOI` knows about neither. When Phase 12 makes it green it **must** remove the marker — `strict=True` turns an un-removed marker into a gate failure, so the promise cannot sit quietly as documentation. |

## Exit gate proof

> *PASS when one unambiguous MVP contract exists and all required/deferred features are
> machine-testable where practical.*

| Requirement | Evidence |
|---|---|
| 1. ADR supersedes dubbing-only, retains `localize_preserve_picture` | `ADR-V4-001` D-V4-01; the preset keeps its own name and its own promise |
| 2. target language `vi` frozen | `NGON_NGU_DICH_HOP_LE == ("vi",)`, 2 tests, one of which fails if `en` is opened |
| 3. `smart_localize` = keep/cut, same order, no reframe | `THAO_TAC_CHO_PHEP`, `CAM_TRONG_MVP`; 3 tests incl. a 6-way parametrised prohibition check |
| 4. voice modes `USER_SELECTED` + `AUTO_MATCH` frozen | `CHE_DO_GIONG`; test asserts `""` is not a mode, closing V2's default-as-automatch conflation |
| 5. user-visible output/failure behaviour defined | D-V4-05; `DUNG_SAI_DO_DAI_S`, `GIAO_KHI_QC_HONG`, 2 tests |
| 6. post-MVP list explicit | `HAU_MVP`; test asserts non-empty and disjoint from allowed operations |
| 7. old restriction cannot silently reassert | `test_hop_dong_V2_mang_bang_chi_duong_toi_ADR_V4` + `test_ADR_V4_ton_tai_va_khai_ro_no_thay_the_cai_gi` — removing or renaming the ADR turns the suite red **before** anyone writes code to the old contract |

**PASS → continue automatically to Phase 02.**
