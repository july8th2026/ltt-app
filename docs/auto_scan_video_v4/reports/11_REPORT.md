# Phase 11 — VLM scene understanding and content profile

**Verdict: PASS** (real-VLM smoke unavailable, stated).
Source SHA at start `93978a3`. Branch `phien/asv-v4`.

---

## 1. The debt Phases 06 and 08 both wrote down is paid here

Both earlier reports closed with the same line: *nothing calls `su_dung.ghi`
yet, and writing a ledger entry into a path that never executes is a claim with
no witness.* Phase 11 is the first paid caller, so `ai.goi_tinh_tien` exists now:

```
1. cua_chan_truoc_khi_tieu   before sending — running out of budget must be a
                             clean policy failure, not a surprise invoice
2. goi                       the actual call
3. write the ledger          on ALL THREE outcomes
4. return / re-raise
```

⛔ Step 3 runs on **delivered, refused and ambiguous alike**. Writing only on
success is how an ambiguous dispatch disappears from the books — at exactly the
moment it most needs to be visible.

## 2. 🔴 A real conflict between Phase 06's rule and the platform's reality

`platform_core.llm.cong_vlm.SuDung` carries a `dang_tin` flag, and its own
docstring says: *"False khi thượng nguồn không trả `usage`. Bên gọi **phải** xử
lý riêng. Đừng coi 0 token là miễn phí."*

Phase 06's rule requires a `DA_GIAO` record to carry a unit and a quantity > 0.
When `dang_tin` is False there is no token count. The two easy paths are both a
lie, in opposite directions:

| shortcut | the lie |
|---|---|
| `DA_GIAO` with `so_luong=0` | claims it was free |
| `TU_CHOI` | claims it never ran |

⭐ But something **is** measurable and true: **one delivered call**. A new unit
`LUOT` records exactly that. It does not pretend to know a token count, and it
does not pretend the call did not happen. Pricing for that unit belongs to
Phase 21; the ledger records what it actually knows.

## 3. Two calls, not one

Reading a scene is a **local** question — what is in it, who speaks, does it
matter. Building a profile is a **global** one — genre, pace, which voice fits.

⛔ Asking both in one call means one bad scene ruins the whole profile, and one
profile revision re-reads every scene. Split, a bad scene damages only itself —
which is what *"checkpoint per scene"* asks for.

Each scene is an `AsvWorkItem` keyed by scene id, so a VLM failure at scene 47
does not make the 46 already-paid-for scenes run again. `ma_dispatch` is
`(operation, stage, scene)`, so a repeat of the same scene hits
`UNIQUE(run_id, ma_dispatch)` — and that is a **success**, not an error: it just
prevented a second charge.

## 4. A malformed response is not a successful artifact — and it still costs

Requirement 5, and it forces a distinction worth stating plainly: a scene that
was **read and returned garbage** is not the same as a scene **never read**. The
first already cost money and belongs in the ledger; the second does not.

So `LuocDoSai` still travels with a `da_giao` entry.

### That distinction shows up again in the error table

`HieuCanhError` is classified `NGUOI_DUNG` — meaning *final failure, do not
retry* — and this is the easiest row in that table to get wrong:

- **`ai.LuocDoSai` (Phase 08) is `TAM_THOI`.** There the JSON parse failed at the
  **transport** layer, before we knew what the content meant. Models are
  stochastic; the next generation usually parses.
- **`hieu_canh.HieuCanhError` is `NGUOI_DUNG`.** Here the JSON parsed and
  **carries a wrong value** — `de_xuat` is an invented word, `quan_trong` is 5.
  The model ran and was charged; retrying is paying twice for the same scene with
  no reason to expect a different answer.

Same shape, different layer, opposite fate.

## 5. Bounded context, because the vision window is half the text one

`ai.cua_so_ngu_canh(DOC_CANH)` measures **65 536 tokens**. Sending the whole
transcript with every scene is the surest way to hit that ceiling, and it hits it
in the worst way: green at scene 1, **413 at scene 40 — after paying for 39**.

So only the dialogue overlapping the scene is sent, capped at 1 200 characters,
and truncation cuts **at a sentence boundary**: a severed sentence makes the model
guess the rest, and it guesses using the customer's tokens.

## 6. Fingerprints carry two independent versions

`van_tay_canh` includes this phase's `PHIEN_BAN_HIEU_CANH` **and** `ai.py`'s
`PHIEN_BAN_PROMPT`/`PHIEN_BAN_LUOC_DO`. They move independently: the *question*
can change without the *door* changing, and vice versa. Without both, editing a
prompt leaves the cache matching and the run reuses an answer produced by the old
prompt — a product change that never reaches the customer.

## 7. Tests and evidence

`tests/test_437_asv_v4_hieu_canh.py` — **35 tests**, five sections: strict schema ·
bounded context · fingerprints · **the live billing path** · scope.

**Layer 4 — ten mutations, ten reds:**

| Mutation | Caught by |
|---|---|
| drop the pre-dispatch budget gate | `test_cua_chan_ngan_sach_chay_TRUOC_khi_goi` |
| skip the ledger on refusal | `test_luot_TU_CHOI_van_duoc_ghi...` |
| skip the ledger on ambiguity | `test_luot_MO_HO_duoc_ghi_va_CHAN_duong_thu_lai` |
| record unmeasured usage as `TOKEN` | `test_provider_KHONG_tra_so_do_thi_ghi_don_vi_LUOT` |
| drop the scene id from `ma_dispatch` | `test_moi_canh_la_MOT_don_vi_viec_rieng` |
| stop validating `de_xuat` | `test_phan_hoi_sai_luoc_do_thi_NEM` |
| stop validating the 0–1 range | same |
| unbounded per-scene context | `test_ngu_canh_bi_CHAN_do_dai` |
| drop the prompt version from the fingerprint | `test_doi_PHIEN_BAN_PROMPT_thi_van_tay_DOI` |
| stop filtering the profile to three axes | `test_ho_so_LOC_ve_dung_ba_mat_cua_catalog` |

Layer 2: `test_400 408 418 421 425–437 85 211` → **434 passed, 1 xfailed**.

## 8. Debt carried forward

⚠️ **No real VLM smoke.** `test_334::_health` skips without `LTT_LLM_TOKEN`, and
machine B is currently serving another session's long-context measurement. What
is proven is that every path — delivered, refused, ambiguous, malformed — reaches
the ledger correctly with a fake provider. The one thing a real call would add is
whether `qwen38-vision` returns `usage`; the `LUOT` unit exists precisely because
the answer may be no.

⚠️ **The stage that calls this is not wired into `pipeline.CHUOI`.** Phase 12
(edit plan and presets) is the first consumer of `SceneUnderstanding`, and the
chain reordering that V4-R07 requires belongs there. `hieu_canh` provides the
domain; the stage that drives it does not exist yet.

⚠️ **`ai.cua_so_ngu_canh` reports the registry's declared 65 536**, while
`docs/audit_ltt_llm/STATE.md` measured a usable ceiling of 28 262 (V4-R08). The
frame cap (60/run, Phase 10) was chosen against the smaller figure's spirit, but
the number itself still needs re-measuring before frame batches are packed.

## 9. Exit gate

**PASS.** `SceneUnderstanding` and `ContentProfile` are durable (per-scene work
items), bounded (context cap, frame cap, field-length caps), reusable
(fingerprints covering both prompt and schema versions), and produced only
through the single LTT AI door — with every outcome, including the ones that cost
money and returned nothing usable, recorded in the ledger.
