# Phase 08 — LTT AI text and vision boundary

**Verdict: PASS.**
Source SHA at start `587bbfd`. Branch `phien/asv-v4`.

---

## 1. 🔴 The finding: a live bug, and ASV is the third victim of it

`platform_core/llm/dieu_phoi.goi` carries this in its own docstring:

> `model_theo_provider={"ltt_llm": "qwen38-api", ...}`
> **VÍ DỤ TRÊN TỪNG GHI `{"ltt_llm": "ltt_llm"}`, VÀ NÓ ĐÃ DẠY SAI HAI NƠI.**
> `ltt_llm` là **bí danh công khai** của app, không phải id model. […] `chon_key`
> với `model="ltt_llm"` **luôn** ném `ThieuKeyError` — và hàm này đọc đó là
> "provider không phục vụ được, đi tiếp", tức **im lặng bỏ qua provider**.

`apps/auto_scan_video/dich_thuat.py:45` was, verbatim:

```python
MODEL_THEO_PROVIDER = {"ltt_llm": "ltt_llm"}
```

Verified against the registry rather than assumed —
`providers.models_for("ltt_llm")` returns exactly `qwen38-api` and
`qwen38-vision`; **`ltt_llm` is not a model id**. So every real translation call
would have skipped the only provider and raised `KhongCoProviderNao`.

The docstring names two victims found on 01/09 — `agent/planner.py` (every
planning turn silently fell through to Gemini despite declaring "house model
first") and `tools/kiem_ltt_llm.py`. **ASV is the third**, and it went unnoticed
for one reason: the translation stage is still a fake engine from Phase 05
(`CHI_PHI_GIA = 0`), so it has never made a real call.

⭐ The lesson is worth more than the three bugs: **an example in a docstring is
code that people copy.** When it is wrong, it is never wrong alone.

## 2. What was built

`apps/auto_scan_video/ai.py` — one door for every LLM/VLM call.

**Six typed operations** (the five the brief names, plus translation), each
declaring `can_thi_giac` and its required output fields.

**Model choice is semantic, not typed in.** `model_cho(thao_tac)` asks
`providers.model_capabilities(...)["vision"]` and returns the id the registry
gives. No ASV file names `qwen38-api` or `qwen38-vision` as a value — an AST test
pins that, and it distinguishes *mentioning* the ids in prose from *assigning*
them, so the explanation in `ai.py` does not trip its own guard.

**Ownership split, written down so nobody has to guess:**

| ASV owns | Platform owns |
|---|---|
| prompts · output schema · version of both | provider · model id · transport · budget · ambiguity |

**Token authority is single-sourced.** `tran_token_ra()` reads
`ltt_llm.ngan_sach.mac_dinh_cho("job")`. A test forbids any ASV assignment of an
int ≥ 1024 to a name containing "token" — CLAUDE.md records a real incident where
a hand-typed `1_024` cut **every long answer**.

**Context windows are not equal**, and that is now measurable from ASV:
`qwen38-api` 131 072 vs `qwen38-vision` **65 536**. A frame batch packed against
the text ceiling becomes a 413 at runtime. ⚠️ `docs/audit_ltt_llm/STATE.md`
measured a much lower usable ceiling for the vision model (28 262); the number
here is what the registry *declares*, and Phase 11 must re-measure before packing
against it.

## 3. Two holes in my own tests, both found by mutation

Seven mutations were run. Five went red immediately. **Two stayed green**, and
both were defects in the tests, not the code:

### 🔴 The ambiguity test was measuring the fallback, not the branch

`_la_mo_ho` recognises `AmbiguousProviderError` **by class name** first, with a
string check as a last resort. My test raised that class with the message
`"mat ket noi sau khi gui"` — so disabling the class-name branch entirely still
passed, via the string. The test proved the backup path worked and said nothing
about the primary one.

Fixed by giving the exception a deliberately neutral message, and adding a second
test that exercises the string fallback on purpose.

### 🔴 The one-door guard locked one of two doors

It checked `ImportFrom(module == "platform_core.llm.dieu_phoi")`. The mutation
inserted `from platform_core.llm import dieu_phoi` — a different AST shape — and
walked straight through. A door locked on one side is not locked.

## 4. A flaky test I created during the Phase 07/08 unification

The Layer 2 regression went red on three `test_431` cases — **under `-n 4`, but
green when run alone.**

Cause: unifying `loi_dang_ban` into `loi_cho_bo_test` made `do_tai=True` the
default, so the arithmetic tests began reading **real CPU** and changing answer
with machine load.

⛔ A flaky quality-gate test is worse than none: it trains people to re-run until
green, and after that nobody reads red at all. Fixed by having the shared helper
pass `do_tai=False` — the tests that deliberately exercise the measured term
monkeypatch `loi_dang_ban` and never used that helper.

## 5. What was *not* done, deliberately

⛔ **No real paid call.** The brief's billing-safety prerequisite says the
Phase 06 parent-budget + delivered-usage path must be proven active before any
real provider execution. It is built and tested (Phase 06) but **nothing wires
`su_dung.ghi` into `ai.goi` yet**, because no stage makes a paid call yet. Wiring
a ledger write into a path that never executes would be a claim without a
witness. Phase 11 is the first paid caller and is the right place to connect them.

⛔ **No owner-app or platform change.** The brief allows them only if Phase 02
required it; it did not. `model_capabilities` was already public and sufficient,
so `ltt_llm.BE_MAT_CONG_KHAI` stayed as it was.

## 6. Tests and evidence

`tests/test_434_asv_v4_ranh_gioi_ai.py` — **28 tests**, seven sections: one door ·
semantic model choice (incl. the alias-bug regression) · token authority ·
structured output · ambiguous dispatch · no second AI transport · prompt/schema
version. No test reaches a model.

**Layer 4 — seven mutations, seven reds** (after the two test defects above were
fixed):

| Mutation | Caught by |
|---|---|
| go back to passing the alias as a model id | `test_KHONG_go_bi_danh_lam_id_model` |
| let a vision op fall back to the text model | `test_thao_tac_van_ban_va_thi_giac_ra_HAI_model_khac_nhau` |
| hard-code the token ceiling | `test_tran_token_lay_tu_ngan_sach_cua_app_CHU` |
| skip required-field validation | `test_THIEU_truong_bat_buoc_thi_nem` |
| read ambiguity as an ordinary failure | `test_dispatch_MO_HO_thanh_AiMoHo...` |
| call the model after cancel | `test_HUY_thi_khong_goi_model` |
| call `dieu_phoi` directly from `dich_thuat` | `test_chi_ai_py_duoc_goi_dieu_phoi` |

Layer 2: `test_400 401 407 408 417 418 421 425–434` + `test_85` → 370 passed,
1 skipped, 1 xfailed after the two fixes above. `test_431` verified stable both
alone and under `-n 4`.

## 7. Exit gate

**PASS.** Every ASV LLM/VLM call goes through one platform-owned path; model
choice is semantic and resolved from the registry; the token ceiling has one
source; structured output is validated; ambiguous dispatch cannot be retried
blindly; and no second AI transport exists — pinned by AST, not by convention.
