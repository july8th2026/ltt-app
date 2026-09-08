# Phase 10 — Scene segmentation and frame sampling

**Verdict: PASS** (real-video benchmark deferred, stated).
Source SHA at start `37b2fef`. Branch `phien/asv-v4`.

---

## 1. Nothing to extract, so it was built — around ffmpeg, not around Python

The brief allows *"ASV deterministic scene analysis engine **or** extracted proven
engine with parity"*. There is a proven engine at
`D:\FULL AUTO VIDEO\CUT CLIP SHORT\cutclipshort\analysis\scene_engine.py`, but:

- that tree is **read-only reference** serving real users
- `apps/taoclipngan` vendored it, and `apps/*/vendor/` is **gitignored** — so no
  copy exists in this repo to reuse

⇒ Built new, and the shape of it is the decision that matters.

## 2. 🔴 The constraint that dictated the design: memory

A 40-minute 1080p video is ~60 000 frames. Decoded into Python that is roughly
**350 GB** flowing through RAM to answer a question about *when the picture
changes*.

⭐ `ffmpeg` already answers it: `select='gt(scene,T)',metadata=print` compares
consecutive frames **inside ffmpeg** and prints only the timestamps where the
score crosses the threshold. ASV reads `stderr`. **No pixel enters Python** — an
AST test pins the absence of `cv2`, `PIL`, `numpy`, `av`, `imageio`, `decord`.

Two more properties fall out and are pinned:

- `-f null -` — run the filter, discard the output. Writing a copy of the video
  to disk to count timestamps would pay the whole disk cost for a count.
- **one** ffmpeg call for the whole video, pinned by counting `subprocess.run`
  calls in `phan_tich`. One call per scene would be N file opens and N decodes
  from the start.

## 3. The frame cap sits where frames are *produced*

Phase 11 sends these frames to the VLM, and `ai.cua_so_ngu_canh(DOC_CANH)`
measures **65 536 tokens** — half the text model's window. 200 scenes × 2 frames
overruns it before anyone counts.

So the ceiling is here, at the producer:

| bound | value | why |
|---|---|---|
| frames per scene | 2 | enough to see a scene, not enough to describe it twice |
| frames per run | **60** | a per-scene cap alone still lets 300 scenes make 600 |
| long edge | 512 px | fits the vision window; `-2` on the other axis keeps aspect |

⛔ A cap placed after the spend is a cap in the wrong place.

## 4. 🔴 The even-distribution test caught a real bug in my first draft

`chan_so_khung` originally walked the scenes giving each one frame while budget
remained. With 100 scenes and a cap of 60 that gives **one frame to each of the
first 60 scenes and nothing to the last 40** — precisely the tail-truncation its
own docstring said it must not do.

⭐ The fix is simpler than the bug: flatten every `(scene, timestamp)` in source
order and take `cap` points at even spacing. The selection does not know what a
"scene" is — it spreads evenly along the timeline, which is exactly what a
content profile of the *whole* video needs.

## 5. Short "scenes" are merged, never dropped

The `scene` filter fires on a cut to black, a noisy frame, a flash. Those 0.2-second
"scenes" are not scenes; sampling them means paying VLM credit for a noise frame.
They are merged into the previous scene — **not removed**, because removing an
interval loses a piece of the source and the index stops covering the video.

### And the first version of that test could not tell the difference

Mutation replaced "merge" with "drop" and the suite stayed **green**. Cause: the
fixture put the short intervals at the *start* of the video, where the separate
head-merge rule happened to close the gap anyway. A short scene in the **middle**
gets no such rescue — the test now uses one, and asserts contiguity directly.

## 6. What the index guarantees

`kiem_chi_muc` rejects an index that fails any of three, each of which has been a
real class of bug elsewhere in this app: **covers the whole source** · **no
overlap** · **source order preserved**. Frame timestamps must lie inside their
scene, and the total must not exceed the cap.

Sampling avoids both scene edges deliberately: a frame at a boundary is usually a
transition frame — a fade, a dissolve, a black frame — and represents no scene at
all.

## 7. Tests and evidence

`tests/test_436_asv_v4_tach_canh.py` — **28 tests**, six sections: determinism ·
memory bound · count/size caps · coverage and ordering · storage form and
cancellation · scope (no VLM, no cuts).

⛔ **No test requires ffmpeg.** The parsing and interval logic are separated from
the binary call precisely so the suite measures them on any machine — a test that
silently skips when a binary is missing is a test that reports green without
measuring anything.

**Layer 4 — six mutations, six reds** (after the merge/drop test was strengthened):

| Mutation | Caught by |
|---|---|
| reduce frames by truncating the tail | `test_ha_so_khung_DEU_TAY_chu_khong_cat_duoi` |
| drop the total frame cap | `test_tong_so_khung_KHONG_vuot_tran...` |
| drop short scenes instead of merging | `test_canh_ngan_o_GIUA_cung_bi_gop...` |
| sample at the scene boundary | `test_khung_mau_TRANH_hai_dau_canh` |
| stop checking full source coverage | `test_chi_muc_khong_phu_het_video_bi_tu_choi` |
| write a video file while counting | `test_ffmpeg_KHONG_ghi_tep_ra_khi_do_canh` |

Layer 2: `test_400 405 418 421 425–436 85` → **376 passed, 1 xfailed**.

## 8. Debt carried forward

⚠️ **`NGUONG_DOI_CANH = 0.4` has not been measured on real customer footage.** It
is the value this filter is commonly used with, and it is written down as
unmeasured in the code rather than presented as settled. The threshold is part of
the stage fingerprint, so changing it correctly invalidates cache.

⚠️ **CPU profile against a real file is not recorded.** What is proven is the
*shape* of the cost — one ffmpeg pass, no frame decoding in Python, bounded output
— which is the part that decides whether a 40-minute video is survivable. A
wall-clock number needs a representative source file, which the project does not
yet have in-repo (same external-evidence gap as G17).

⚠️ Persisting `SceneIndex` and frame files as `AsvAsset` rows is **not** wired
here: `assets.promote_va_ghi` already provides lineage and fingerprints, and the
stage that calls it belongs to Phase 11, which is the first consumer.
`sang_json` produces the durable form and is deterministic.

## 9. Exit gate

**PASS.** Any source can produce a durable, bounded `SceneIndex` with
representative frames — deterministically, in one ffmpeg pass, without decoding a
frame in Python, without a VLM call, and without any edit decision.
