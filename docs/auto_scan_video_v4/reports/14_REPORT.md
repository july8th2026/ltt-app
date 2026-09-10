# Phase 14 — Dubbing adaptation for retained segments

**Verdict: PASS.**
Source SHA at start `41b3c06`. Branch `phien/asv-v4`.

---

## 1. What changed: `CONTENT_PROCESS` stopped being a translation stage

Phase 12 closed V4-R07 on the **chain** side by putting `EDIT_PLAN` before the
paid stage. Phase 14 closes it on the **content** side: the stage's input is now
`ban_bien_tap.doan_giu_lai(...)` — only segments overlapping a kept scene. A
segment belonging to a cut scene is never sent, never paid for, and cannot appear
in the output.

The output is a **DubbingDocument**, and it is deliberately a *superset* of the
old text document rather than a new shape: same `schema`, same
`muc[].ma/bat/ket/goc/chu`, so `van_ban.kiem` and the downstream stages keep
working. Changing the shape "for cleanliness" would have forced phases 15, 16, 17
and QC to change in the same commit — which is how one phase becomes four.

Each line carries what a translation does not need and a dubbed line does:

    source text · **source duration** · the neighbouring **retained** lines ·
    the target voice's traits · a closed-vocabulary mood and speech style

⭐ Duration is present now rather than in Phase 15. Phase 15 *shortens lines to
fit*; shortening a line that was written without knowing how long it had to be is
repairing something that should not have been wrong. Telling the model up front
means most lines never need the second pass.

🔑 And the neighbouring lines are taken from the **retained** sequence, not from
the source order: after cutting, the line before a line can be three minutes away
in the original — and that is the line the viewer actually just heard.

## 2. Results are keyed by segment id, never by position

A batch of 12 comes back with 11. Merging by **position** shifts every line from
that point onto the wrong segment — and nothing fails: the document is still
well-formed, still complete, still passes validation. The film simply has the
wrong line under every shot from the middle onward.

Merging by **id** turns that into "missing segment X": a sentence someone can act
on. `doc_chuyen` raises rather than silently returning fewer entries, and it
**drops ids that were never sent** — an invented id is a line attached to a shot
that does not exist.

## 3. The voice is frozen into the document, and into its fingerprint

Phase 09 allows `AUTO_MATCH` to defer. By this stage it cannot: lines are written
**for** a voice — address forms, register, formality all bend to it. So
`ma_giong()` raises rather than falling back to a default; a default voice here
produces a perfectly listenable dub that is simply not what the customer ordered.

### 🔴 And two voice keys had been running side by side

`rang_giong` reads `settings["giong_id"]`; `giai_doan_giong` — which has been
running since V2 — reads `settings["voice_id"]`. So a run could have its lines
**written for one voice and spoken by another**, with nothing raising, because
each side found a perfectly valid value of its own.

`tu_thiet_lap` now accepts both, `giong_id` first. That is half a fix, and the
report says so: Phase 15 must make `giai_doan_giong` read `ma_giong` **from the
DubbingDocument** instead of reading settings at all. One question, one answer.

## 4. Checkpoint per segment — and `commit`, not `flush`

The ledger key is the **batch** (one model call, one ledger row); the checkpoint
key is the **segment**. Two different axes, and collapsing them would mean a
batch of 12 charged as one item.

🔴 The first version used `db.flush()` after each batch and hit
**`database is locked`**: `su_dung.ghi` + `danh_dau_xong` hold a write lock on the
handler's session while `ctx.progress()` opens a second session to update `jobs`.
This stage's second batch is the first place in the repo where those two paths run
next to each other — Phase 11 has `goi_tinh_tien` but is not wired into the chain.

⭐ `commit` is not a workaround for that; it is what a checkpoint *means*. A
flush only pushes statements into an open transaction — a worker that dies right
after loses them, and the "checkpoint" never existed. The lock contention was the
symptom that made the semantics obvious.

## 5. 🔴 Things that were written but never read

Phase 12 stored the edit plan and the scene index as one artifact. Neither
`BanBienTap` nor `ChiMucCanh` had a way back: `sang_dict`/`sang_json` with no
`tu_dict`/`tu_json`. Nobody noticed because Phase 12 never read its own output.
**Phase 14 is the first reader**, and it needed both.

⛔ A serialiser with no deserialiser is a storage format nobody has ever tried to
read — and it only surfaces a phase later, when the artifact is already in the
customer's storage. `van_tay()` hashes `sang_dict()`, so a round trip must return
the *same fingerprint*, or one read-write cycle would invalidate everything
downstream with nothing actually changed. That is now pinned.

### And the smart preset had never run end to end

`giai_doan_ban_bien_tap._nguon_soi_duoc` looked for a video artifact among
`media_prepare`'s outputs. `media_prepare` deliberately emits **no video** — the
original is left untouched, on purpose. So `smart_localize` failed at its very
first step with "no media to analyse scenes": a sentence that is literally true
and points at the wrong cause.

It went unnoticed because `PRESET_MAC_DINH` is `localize_preserve_picture`, and
that branch **bypasses the function entirely**. The cutting preset had never run
through the chain once. It reads `run.source_key` now, and this phase's tests run
it.

## 6. Tests and evidence

`tests/test_440_asv_v4_long_tieng.py` — **24 tests**, seven groups: exact
coverage · identity · frozen voice · closed vocabularies · round-trip
serialisation · source immutability · a real end-to-end run through the queue
(spy, partial retry, checkpoint contents).

**Mutation testing — 19 mutations, 19 red** (after the two holes below):

| Mutation | Caught by |
|---|---|
| merge results by position | `test_lo_TRA_VE_THIEU_thi_NEM...` |
| missing segments silently tolerated | same |
| accept ids the model invented | `test_model_BIA_THEM_ma_thi_ma_do_bi_bo_di` |
| drop the exact-coverage check | `test_mot_doan_thuoc_canh_DA_CAT_lot_vao...` |
| build the document with no voice | `test_khong_co_giong_thi_KHONG_dung_duoc...` |
| voice / edit plan absent from the fingerprint | `test_doi_GIONG_thi_van_tay_doi` + sibling |
| drop the closed-vocabulary check | `test_tai_lieu_co_sac_thai_ngoai_bang...` |
| accept a segment with no text | `test_nhung_THIEU_CHU_thi_van_la_thieu_doan` |
| `chia_lo` binds the constant at def time | `test_doi_DOAN_MOI_LO_thi_kich_thuoc_lo_DOI_THAT` |
| **translate the whole transcript, unfiltered** | `test_KHONG_doan_nao_thuoc_canh_BI_CAT...` |
| ignore checkpoints / drop their fingerprint / stop writing them | three separate tests |
| `flush` instead of `commit` | `test_diem_chot_giu_KET_QUA...` |
| round-trip changes the plan's fingerprint | `test_ban_bien_tap_doc_di_ghi_lai...` |
| the two voice keys split apart again | `test_hai_khoa_chon_giong_deu_dan_toi_MOT_ket_qua` |
| `da_xong` ignores the fingerprint | `test_doi_GIONG_thi_diem_chot_cu_KHONG_duoc_dung_lai` |
| smart preset loses its video source | the end-to-end spy test |

### 🔴 Two holes mutation testing found in my own tests

1. **The spy test was vacuous — and it was guarding the phase's central claim.**
   The forced cut scenes did not line up with the fixture's segments, so *every*
   segment still overlapped some kept scene and the set of "segments only in cut
   scenes" was **empty**. The assertion was true for any implementation,
   including one that sends everything. Scenes are now aligned to the segments,
   and the test asserts its own non-vacuity before asserting anything else.
2. **Nothing tested that changing the voice invalidates the checkpoints.**
   `da_xong` filters by fingerprint, and removing that filter stayed green. Reusing
   a checkpoint after a voice change hands the customer a dub that is **half old
   voice, half new** — and nothing fails; it just does not sound like one person.

### A real bug in my own code, found because a test could not do what it said

`chia_lo(moi_lo=DOAN_MOI_LO)` binds the default **at function definition**, so
changing `DOAN_MOI_LO` afterwards — by config or by `monkeypatch` — changes
nothing. The function keeps running, keeps returning valid results, with the old
batch size. Found when a test set it to 1 to create several batches and still saw
one. A knob that looks set and is not is the most expensive kind: every
measurement after it describes a configuration that does not exist.

⚠️ One dead `pytest.skip` was removed from the spy test after the non-vacuity
assertion made it unreachable. The quality gate flags silent skips for exactly
this reason: a test that excuses itself still counts as green.

Regression: **890 passed, 3 skipped, 1 xfailed**. `lint_app_contract`: 20 apps,
0 ERROR, 0 WARN.

## 7. Debt carried forward

⚠️ **`AUTO_MATCH` still cannot resolve.** No stage produces a `HoSoNoiDung` —
`ai.HO_SO_NOI_DUNG` is parsed in `hieu_canh.py` and called by nobody, because
`giai_doan_ban_bien_tap` passes an empty `hieu_canh` (Phase 12's recorded debt).
The phase prerequisite "ContentProfile exists" was **not met**; USER_SELECTED is
fully wired and AUTO_MATCH's code path is tested with a stub profile. Wiring the
VLM into `EDIT_PLAN` also makes `smart_localize` actually smart, so it is one
piece of work serving two phases.

⚠️ **`giai_doan_giong` still reads `settings`, not `ma_giong`.** Freezing the
voice into the document means nothing until the stage that speaks reads it.

⚠️ **`DOAN_MOI_LO = 12` and `NGU_CANH_KE = 2` are unmeasured** — chosen
conservatively. Phase 21 measures.

⚠️ **No real model has written a line yet.** Every test stubs the door
(`ai.goi_tinh_tien`). The prompt, the closed vocabularies and the id-keyed
response shape are unexercised against a live model.

## 8. Exit gate

**PASS.** A versioned DubbingDocument exists for exactly the retained segments,
in source order, with stable ids; the source transcript is untouched; the voice is
resolved before the first line is written and frozen into both the document and
its fingerprint; every segment is checkpointed durably, so a retry pays for what
is left rather than starting over.
