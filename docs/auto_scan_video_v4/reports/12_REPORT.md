# Phase 12 — Edit plan and MVP presets

**Verdict: PASS.**
Source SHA at start `bac856e`. Branch `phien/asv-v4`.

---

## 1. 🔴 This phase closes V4-R07 (P0) — and it is a chain change, not a new file

The risk register has said since Phase 00:

> Expensive-work ordering is **inverted** relative to V4. `pipeline.CHUOI` runs
> `content_process` (paid LLM translation of the whole transcript) at position 4,
> with no `EDIT_PLAN` and no `VOICE_BIND` anywhere.

So V2 translated — and **paid for** — dialogue belonging to scenes that would be
cut. `EDIT_PLAN` is now inserted between `TRANSCRIBE` and `CONTENT_PROCESS`, and
`content_process` declares `sau=(EDIT_PLAN,)` so the coordinator cannot submit it
until the plan has succeeded.

The chain went **9 → 10 stages**, and it runs end to end through the real queue
and a real worker (`test_402`, 81 s).

### Invalidation is one-directional, and that is the point

`ha_nguon_cua(EDIT_PLAN)` returns `content_process → qc` and **nothing upstream**.
Changing the plan must not invalidate ASR or source separation: re-running a paid
transcription because of a *picture* decision is the same class of waste V4-R07
describes, just pointing the other way.

## 2. `localize_preserve_picture` never cuts — and never even asks

`THAO_TAC_CHO_PHEP[PRESET_GIU_HINH]` is an **empty tuple**. This is a product
promise — "dub it, leave the picture alone" — not a soft default.

⛔ The preserve branch does not read `hieu_canh` at all. An opinion about what to
cut is an opinion that must not be reachable here; reading it would create a path
a later edit could open by accident. A mutation that lets the preserve branch see
the VLM's advice turns the suite red.

## 3. Scenes with dialogue need a higher bar to remove

| | threshold |
|---|---|
| no dialogue | 0.65 |
| **has dialogue** | **0.85** |

🔑 A silent scene cut by mistake costs the viewer a shot. A dialogue scene cut by
mistake **breaks the story** — they hear an answer to a question that no longer
exists. Two different damages, so two different thresholds.

⭐ And the reason string says *why* the bar was higher, not just what it was. A
log line reading "below threshold 0.85" does not tell the reader why this scene
was harder to cut than the one beside it — which is exactly the question they
have. A test pinned that, and the code was what changed.

## 4. Safety rules, and which one had never actually fired

Three rules protect the output: **never cut everything**, **keep at least 50 % of
the duration**, and **no cut action in preserve mode**.

When the floor forces cuts back, it reverts the ones with the **lowest
confidence** first — not the ones latest in the file. Reverting in order would
keep the start of the video and cut the whole ending.

### 🔴 The empty-video guard had never been the rule that saved us

Mutation removed it and the suite stayed **green**: in every fixture the 50 % floor
had already prevented total removal, so the last-resort guard was never reached.

The new fixture makes the plan **lie about its own ratio** (claims 1.0 while
cutting everything), so only the empty-video guard can catch it. That is exactly
the situation a ratio-computation bug would produce — and there, this guard is the
last thing between the customer and an empty file.

## 5. CUT segments cannot reach downstream

`doan_giu_lai` reduces the transcript to segments overlapping kept scenes, and
this is the mechanism that stops money leaking: a segment belonging to a cut scene
that slips through is a line **translated and spoken aloud** for a picture that no
longer exists. Order and original timestamps are preserved — retiming is Phase 16.

The filtered transcript carries the plan's fingerprint, so a downstream stage can
tell **which plan** it was filtered by.

## 6. Tests and evidence

`tests/test_438_asv_v4_ban_bien_tap.py` — **28 tests**, six sections: position in
the chain · preserve mode · thresholds · floor/ceiling · determinism and
fingerprints · CUT segments absent downstream.

**Layer 4 — eight mutations, eight reds** (after the empty-video fixture was
strengthened):

| Mutation | Caught by |
|---|---|
| preserve mode reads the VLM and cuts | `test_giu_hinh_KHONG_doc_y_kien_cua_VLM` |
| same threshold for dialogue scenes | `test_canh_CO_LOI_THOAI_can_do_tin_CAO_HON` |
| drop the retained-duration floor | `test_giu_lai_it_nhat_bang_SAN` |
| allow cutting everything | `test_ban_CAT_SACH_bi_tu_choi...` |
| cut when there is no evidence | `test_KHONG_co_bang_chung_thi_GIU` |
| revert cuts in order, not by confidence | `test_hoan_cat_theo_do_tin_THAP_NHAT_truoc` |
| let cut segments reach downstream | `test_doan_thuoc_canh_bi_CAT_KHONG_co...` |
| `content_process` no longer depends on the plan | `test_content_process_phu_thuoc_TRUC_TIEP...` |

Two existing pins were updated deliberately, both encoding the **old chain
shape**: `test_402`'s 9-stage count and `test_417`'s "the stage right after
transcribe". Each carries a comment saying what changed and why.

⚠️ And a **second instance of the flaky test I created in Phase 07** surfaced
here: `test_431::test_moi_ve_deu_tinh_tren_LOI_VAT_LY` called
`loi_cho_bo_test` directly, so it still read real CPU and changed answer under
`-n 4`. Fixed the same way. Both call sites are now load-independent, verified
alone and under load.

## 7. Debt carried forward

⚠️ **The stage does not call the VLM yet.** `giai_doan_ban_bien_tap.chay` passes
an empty `hieu_canh`, so `smart_localize` currently keeps everything for lack of
evidence — which is the correct behaviour when there is none ("cutting a scene we
know nothing about is cutting blind"), but it means the smart path is not yet
smart. Wiring Phase 11's `hieu_canh` into this stage needs per-scene work items
driven from the stage, which is where Phase 13+ picks up.

⚠️ **`SAN_GIU_LAI = 0.5` and the two thresholds are unmeasured.** They are chosen
conservatively — toward keeping material — and they are inside the stage
fingerprint, so changing them correctly invalidates cache.

## 8. Exit gate

**PASS.** The EditPlan is the authoritative visual decision: it is deterministic,
versioned, source-ordered, it sits before every paid stage in the chain with a
declared dependency, its invalidation reaches only downstream, and no cut segment
can reach the dubbing work list.
