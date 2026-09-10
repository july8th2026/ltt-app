# PHASE 08 REPORT — Media Probe and Normalize

**The first phase with a real engine.** Everything before this was a dummy.

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 07 **PASS** (I7 closed)
- allowed change scope: media capability service in the ADR-selected executor; extraction
  from Cut_only_ver2 where needed; tests/fixtures

## Trace performed (item 1)

**Cut_only_ver2** — `nerf_engine/stages/audio.py:48 extract_audio`
(`-vn -ac 2 -ar 48000`), `:54 loudnorm` (−14 LUFS / −1.5 dBTP), `:61 demucs_separate`;
`stages/ffmpeg_edit_cutonly.py:203 _get_video_duration` (ffprobe, 30 s timeout),
`:323 replace_audio` (**`-c:v copy` + AAC + `+faststart`** — the shape MVP's RENDER will
take, D-ASV-03).

**LTT platform** — `platform_core/media.py` (`ffmpeg_bin`, `ffprobe_bin`, `probe`,
`detect_gpu_encoder`); `apps/upscalevideo/ff.py:36 _run` (Popen + cancel poll + deadline),
`:61 probe_video`; `apps/autosubvideo/routes.py:47-49,368` (input policy).

## Decisions

**D-08-01 — "normalize" here does not touch video.**
D-ASV-03 copies the video stream, so MEDIA_PREPARE produces exactly two things:
`source_probe.json` and a 16 kHz mono WAV for ASR. The original is untouched and the WAV is
a **new lineage branch** back to it (item 4) — losing the original means losing the ability
to recompute everything downstream.

**D-08-02 — an app-level probe instead of extending `platform_core.media`.**
`media.probe` returns duration/size/codec/fps and is enough for most apps. The input policy
and the copy path additionally need: has-audio, copyable codec, channels, sample rate, VFR,
rotation. That is one app's need, and O20 says extend core only when there is no app-level
answer. `nhap_media.soi()` calls ffprobe with `-show_streams` and returns a **flat** dict, so
no caller re-walks a `streams` tree.

**D-08-03 — policy runs before a single second of ffmpeg.**
`kiem_chinh_sach` is checked immediately after probing and before extraction. Rejecting early
is the difference between an instant answer and a refund. Every message names **what is
wrong and what the limit is** — "invalid format" makes the customer guess, they guess wrong,
and each retry pays for an answer we already knew.

**D-08-04 — `-ac 1 -ar 16000`, deliberately different from the legacy `-ac 2 -ar 48000`.**
ASR does not use the second channel, and Whisper resamples to 16 kHz internally — feeding it
48 kHz does that work twice. Recorded as a deliberate divergence in `TestDoiChieuDiSan`
rather than silently.

**D-08-05 — the fingerprint is `source checksum + normalize config + ffmpeg version`** (item 8).
Keyed on the **content hash**, not the filename or key: two files with the same name and
different content must produce different fingerprints. The tool version is in there because
a different ffmpeg can produce different audio from identical arguments — without it, a
version bump silently reuses stale results (O13).

**D-08-06 — no GPU claimed** (item 6). MEDIA_PREPARE stays in `asv_media`
(`requires=("ffmpeg",)`). Nothing here needs a card.

## Changes

| Path | Change |
|---|---|
| `apps/auto_scan_video/nhap_media.py` | **new** — safe subprocess runner, ffmpeg version, full probe, input policy, ASR audio extraction, fingerprint |
| `apps/auto_scan_video/giai_doan_media.py` | **new** — the stage body: probe → policy → extract → two artifacts |
| `apps/auto_scan_video/thi_hanh.py` | dispatches MEDIA_PREPARE to the real engine; dummy stages keep the identical path |
| `apps/auto_scan_video/assets.py` | `kiem_hop_le` now ffprobe-validates `video`/`audio` — Phase 06's stated debt, paid |
| `tests/fixtures/asv_media.py` | `+nap_nguon_vao_kho()` |
| `tests/test_401…` | `_vi_pham` now also inspects **keyword arguments** — see below |
| `tests/test_402…`, `tests/test_403…` | seeded with a real source video |
| `tests/test_405_asv_nhap_media.py` | **new**, 24 tests |
| `locale/en/LC_MESSAGES/messages.po` | +29 Auto Scan entries, added by hand |

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_405…` | **24 passed** |
| all six Auto Scan suites | **99 passed** |
| `python tools/check_i18n.py` | 774, at the mark — no increase |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline |

### Required verification

| Required | Test |
|---|---|
| unit + integration fixture | 24 tests, all on real ffmpeg output |
| **real FFmpeg smoke** | `test_cong_thoat_mot_dau_vao_thanh_artifact_chinh_tac` — real queue, real worker, ends with a real WAV verified by ffprobe |
| cancel / partial-file | `test_huy_giua_chung_GIET_tien_trinh_con`, `test_tach_tieng_that_bai_thi_NEM_chu_khong_de_lai_tep_cut` |
| item 7 edge cases | VFR (detected via `r_frame_rate` vs `avg_frame_rate`), mono/stereo (stereo→mono test), missing audio, **Unicode paths** (`Thư mục Tiếng Việt/video của tôi — bản 1.mp4`), portrait/landscape, corrupt input |

### Parity fixture (item 2), stated honestly

The legacy tree has **no test suite** (GAP-00-C), so "parity" cannot mean re-running old
tests. `TestDoiChieuDiSan` does the two things that are actually possible:
- pins the **command skeleton** the legacy helper used (`-vn`, `-ac`, `-ar`, never a shell);
- pins **measurable properties** of the output — duration preserved within 0.1 s, and the
  extracted track is **not silent** (a correctly-formatted 16 kHz mono file full of zeros
  passes every format check and hands ASR an empty transcript).

## Two guard failures worth recording

**1. I walked into the documentation-punishing guard a second time.**
`test_KHONG_BAO_GIO_dung_shell_khi_chay_ffmpeg` was first written as
`assert "shell=True" not in source` — and it failed, because `nhap_media.py` contains a
comment *forbidding* `shell=True`. Exactly the trap Phase 05 hit with `gpu_arbiter`, and I
had already written the fix. Now it reuses the AST checker.

**2. That AST checker could not have caught `shell=True` at all.**
After switching, the test passed — and passing was the problem. `shell=True` is an
`ast.keyword`, and `_vi_pham` collected `Name`, `Attribute`, `Constant` and imports, but
**not keyword argument names**. I checked the detector against a real
`subprocess.run(cmd, shell=True)` sample and it returned `[]`.

So for one commit there was a green light wired to nothing — the vacuous guard Phase 04
introduced `test_may_do_...` specifically to prevent. It was caught only because that
self-test asserts **both** directions, and I extended it rather than trusting the green.
`ast.keyword` is now collected, and the self-test pins the `shell=True` case.

> The general lesson, now paid for twice: **a guard's own test must prove it can fail.**
> "The suite is green" and "the guard works" are different claims.

## i18n: not hiding behind a pre-existing red light

The new user-facing messages tripped `chuoi chua dich` (+16 unwrapped strings). These
genuinely reach users — they land in `stage.error` → `run.error` → the progress view — so
they were wrapped in `_()` rather than exempted.

That moved the problem to `dich thieu ban EN`, which was **already failing at baseline**. It
would have been easy to leave it: the ratchet was red anyway, and my strings would have
hidden in the noise. Instead all **29** Auto Scan strings were translated and added to
`locale/en` by hand (no `i18n.py trich` — `msgmerge` reorders the file and guesses
translations, both of which this repo warns about).

Result: `dich thieu ban EN` now reports exactly **one** missing item —
`Chuoi thu banh coc VANG`, the committed test-fixture garbage of BASELINE-DEBT-01, owned by
another session. Auto Scan contributes zero to that failure.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| I8 durable DONE | **strengthened** | media artifacts are now ffprobe-validated, not just non-empty |
| I10 cache correctness | **strengthened** | fingerprint now includes source checksum + tool version |
| I11 resource control | PASS | AST guard over 14 files; no GPU claimed |
| I13 cancellation | PASS | subprocess killed, `DaHuy` raised |
| I14 safe promotion | PASS | extraction writes to temp; the caller promotes |
| I1–I7, I9, I12, I18, I19 | PASS | 99 Auto Scan tests green |

## Diff review
- changed paths: `apps/auto_scan_video/`, `tests/`, `locale/en/LC_MESSAGES/messages.{po,mo}`
- two scratch scripts (`tmp_gom_chuoi.py`, `tmp_them_po.py`) created and deleted
- `.po` kept LF-only (verified: 0 CRLF); appended, never reordered
- secret scan PASS; no media committed — every fixture is generated at run time

## Risks / external evidence pending

- **RISK-08-01 (P2, new)** — `_kiem_media` only ffprobe-validates when storage exposes a
  local path. On R2 it returns without checking, because downloading every artifact just to
  validate turns a check into a bandwidth bill. Stated in the code. Phase 15 closes it where
  the file is on disk anyway.
- **RISK-08-02 (P3, new)** — VFR is **detected and recorded**, not corrected. Fine while the
  video stream is copied, but Phase 13 (timing) must decide what a VFR source means for
  drift. Recorded so it is a decision, not a surprise.
- **CLOSED: RISK-06-01** (`kiem_hop_le` not validating media).
- Unchanged: RISK-00-02, -07…-16; RISK-01-01; RISK-02-01…03; RISK-03-01…03; RISK-05-01, -02;
  RISK-06-02; RISK-07-01.

## Exit gate

**PASS.**

Gate text: *"PASS when one owned input becomes a validated canonical media asset without
legacy queue/locks."*

`test_cong_thoat_mot_dau_vao_thanh_artifact_chinh_tac` runs a real run through the real
queue and asserts:
- MEDIA_PREPARE `succeeded`;
- **two** durable artifacts (`json` probe + `audio` WAV), each re-verified by checksum;
- the WAV is genuinely 16 kHz mono, confirmed by ffprobe — not a JSON placeholder;
- **the original source object still exists**;
- owner-scoped throughout.

No legacy queue or lock is involved: the job came from `platform_core.jobs`, and the AST
boundary guard confirms no `gpu_arbiter`/`gpu_claims`/`CUDA_VISIBLE_DEVICES` reference in any
Auto Scan file.

The negative path is proven too: a video with no audio stream fails the run **terminally**
with a message naming the missing stream, and settles at `credit_actual == 0`.

## Next phase prerequisites

Phase 09 (Audio Prepare / Separation / Mix) is the **first GPU stage**:
1. `asv_gpu.gpu_vram_mb` is still an **estimate** (RISK-05-01). The repo's rule is
   *"CHUA DO THI KHONG CHAY"* — measure demucs before declaring;
2. the extracted 16 kHz mono WAV is ASR material, **not** separation material — demucs needs
   the full-band stereo track, so Phase 09 must extract its own input rather than reuse this
   one;
3. `nerf_engine/stages/audio.py` (`demucs_separate`, `mix_stems`, `loudnorm`) is
   coupling-free and is the extraction target;
4. every subprocess must take its GPU from `ctx.gpu_env()` — the guard is live and covers
   `apps/asv_gpu/`.
