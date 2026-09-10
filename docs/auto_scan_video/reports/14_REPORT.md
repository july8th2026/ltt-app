# PHASE 14 REPORT — Composer & Render Manifest

**The phase where merging cost more than building, and was worth it.**

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 13 **PASS**
- allowed change scope: composer service + stage, tests; plus the merge debt this phase came due on

## What was built

`apps/auto_scan_video/ban_dung.py` — the RenderManifest, and `giai_doan_ban_dung.py` — the
COMPOSE stage.

**The manifest is data, not a command string.** Generating `ffmpeg -i … -filter_complex …` and
storing it would pin an editorial decision to one ffmpeg version: change the filter syntax, or
the encoder, and you must re-run the entire upstream AI chain just to regenerate a string. The
manifest describes **what**; the renderer builds the command. That is boundary G9 (composer ≠
renderer), and the price of blurring it is a tool upgrade forcing a recount of money.

**Every reference is verified before a render slot is spent** (Prompt 14 item 5), and
`kiem_toan_ven` is re-run rather than trusting the stored `integrity` column — that column says
`ok` as of the last check, and the file may have vanished in between. A manifest pointing at a
missing artifact is otherwise a render that fails at minute ten, after the slot is taken, the
file downloaded and decoded.

The legacy editing engine was not reusable: `DUNGVIDEO-FULL/engine/assemble.py:1040` cuts clips,
re-encodes and cross-fades — the entire **cut** path, which `MVP_CONTRACT.md` §4 deferred
(D-ASV-02). What survives is `Cut_only ver2/…/ffmpeg_edit_cutonly.py:323 replace_audio`:
`-map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -movflags +faststart -shortest` — exactly the MVP
shape: replace the audio, keep the picture.

## The decision this phase actually turned on

The gate ran red at Phase 14 close for reasons **outside this phase**, and there were two ways
to respond: report the failures as external, or bring the tree up to date first.

The worktree was pinned at `c31b1ae` — **37 commits behind** `admin-mvp-v3`. Running the gate on
a four-day-old tree produces evidence about a tree that will never be merged. `gate.py:705-714`
already says this in its own words about a tree that changes *during* a run; the same logic
applies to one that is stale *before* it.

So: merge first, then measure. The merge conflicted only on the two locale files (both sides had
appended); everything else auto-merged.

**Failures went 5 → 34.** That is the finding. Thirty-four is not a regression the merge caused —
it is thirty-four things that were **already true** and that a stale tree was hiding.

| | failures | steps red |
|---|---|---|
| before merge (stale tree) | 5 | 5/26 |
| after merge | 34 | 5/26 |
| after fixes | **7** | **2/26** |

## The bug worth the whole phase

Six of my own test files went red under the gate and **green when run alone**. That signature —
green standalone, red in the gate — is the one this repo has a memory note about, and the
tempting reading is "flaky test, re-run it".

It was not flaky. It was **MAX_PATH**.

```
FileNotFoundError: [Errno 2] No such file or directory:
  …\popen-gw2\test_MOT_tep_cho_MOI_doan0\kho\asv-staging\uA\
  asvr_<32 hex>\voice_synthesis\<64 hex>.wav.part20608
```

`Storage.put` raises at `open(tmp,'wb')` — a message about a file that does not exist, for a
fault that is really *the path is too long*.

```
run alone   : 252 characters  -> green
run in gate : xdist inserts `popen-gwN\` (10 chars) -> 262 -> red
MAX_PATH    : 260
```

The fault was **not** in `platform_core/storage.py` — its `.part<pid>` suffix adds only 12
characters. It was in putting a **full** sha256 digest in a filename next to a full run id.

### And the first fix was not enough — which is the more useful half

Truncating the fingerprint to 32 characters made the tests pass. It did **not** fix the bug.

The test used `owner_id="uA"` — two characters — while a real `owner_id` is a 36-character UUID
(`AsvRun.owner_id` is `String(36)`). With realistic input the worst case was still **269**.

The first patch went green because the test data was too kind, not because the fault was gone.
Only a worst-case-real input surfaced it. `tests/test_412` now pins the total length against a
real UUID, and the budget is per-segment (`owner 16 / run 24 / fingerprint 32`) with the
arithmetic written down.

The **full** digest stays in `AsvAsset.van_tay`. Shortening the name does not shorten the
evidence.

⚠️ This would also have failed on a customer machine with a deeper storage root, running alone.
CI parallelism only made it visible early.

## Registries that were owed, and one that bites twice

| test | registry | what was missing |
|---|---|---|
| `test_147` | `CROSS_APP_ALLOWED` | 6 cross-app edges |
| `test_190` | `DISPOSITION` + `APP_DISPOSITION_V1.md` | 4 apps |
| `test_211` | `governance.STORES` | 3 tables |
| `test_212` | `APP_API_COVERAGE_FINAL.md` | 4 apps |

On `CROSS_APP_ALLOWED` the six edges are **two different things**, and recording them as one line
would have hidden the part that matters:

- **Type A** — `asv_media` · `asv_gpu` · `asv_voice` → `auto_scan_video`. Not debt. These are not
  independent apps; they are executor shells of one product, split only because job admission
  filters by **app** and not by `job_type`. "Remove one app and the other breaks" does not apply:
  removing `auto_scan_video` removes the product.
- **Type B** — `auto_scan_video` → `ltt_llm` · `autosubvideo` · `ltt_voice`. **Real debt**, same
  class as `taovideo → upscalevideo`. But the exit is *not* ToolSpec handoff: these are mostly
  **pure functions** (`ltt_voice.text_pipeline.chuan_hoa` is Vietnamese text normalisation — a
  shared concern living in the wrong place). Handing off a pure function through a job queue adds
  a queue round-trip to a string transform. The right exit is lifting the shared part into
  `platform_core`, and that touches three apps **serving paying customers** in another lane —
  which `CLAUDE.md` says to stop and name rather than bundle into a ten-item sweep. Logged as
  RISK-14-01.

On `governance.STORES`: all three tables are CONTENT at 30 days, and the 30 **deliberately
matches** the `jobs` expiry. LTT VOICE already paid for the mismatch — `voice_block.audio_key`
outlived the file it pointed at, so after 30 days a customer opened an old project and found a
404 player with no explanation. A row outliving its file is not "keeping more", it is a broken
promise.

## The nav trap, caught in the act

`auto_scan_video` declared `surface="customer"` with no `routes.py`. That is precisely the trap
`apps/ltt_llm` fell into: `nav_entries()` **synthesises** a default nav row — declaring `nav=()`
does not mean "no nav" — and every logged-in customer gets a dead link.

⚠️ And `enabled=False` does not save you. `visible_on_surface`
(`platform_core/registry.py:863-874`) never reads `enabled` at all.

Lowered to `runtime`. `tests/test_413` pins **both directions**, because `test_60` only catches
one: an app that *has* a UI but forgot to flip `surface` back fails **silently** — no 404, no
error, the product simply never appears. That direction has no victim yet, which is exactly why
it needed pinning now.

## Two guards that caught their own author

- The composer test forbade the literal string `ffmpeg` in the manifest — and went red, because
  the manifest **must** record the tool version (Prompt 14 item 6). A marker list broad enough to
  match the thing it protects.
- The same test's process-spawn guard forbade `"run"`, which matches the `run` parameter of
  `chay(db, kho, *, run, ctx)`. A marker short enough to match a common variable name measures
  naming, not behaviour.
- `test_44`'s secret scanner flagged a bare 32-character hex string in the MAX_PATH comment above.
  It was right: a bare hex literal in source is indistinguishable from a real key.

Third occurrence of this pattern in this build. It is worth stating plainly: **a guard's marker
list is part of the guard, and an over-broad marker makes the guard measure the wrong thing** —
sometimes vacuously (it cannot fire), sometimes noisily (it fires on its own documentation).

## Alembic re-anchored

`down_revision` of `20260901_1800_asv_run_va_stage` moved from `a5f31c07d2b4` to `c7b91e4a2f80`
(the VOICE lane added a migration on top, giving two heads). Re-anchoring rather than adding a
merge revision is correct **here** for a specific reason: neither `asv_*` migration has run
anywhere — no `alembic_version` row holds `e1a7c04b93d2`. For a migration that *has* run, the
opposite holds, and a merge revision is the only honest path. Verified `a5f31c07d2b4` is the
direct ancestor of `c7b91e4a2f80`, so no link is lost.

## Exit evidence

`python tools/gate.py --phien asv` → **FAIL (2/26)**, 7 test failures.

**None of the seven are in this phase's work, and each was traced rather than assumed** — proved
by `git diff 9936473...HEAD` touching none of the implicated files:

| failure | cause | owner |
|---|---|---|
| `test_147::test_platform_core_never_imports_apps` | `platform_core/public_api/dieu_khoan.py` imports `apps.ltt_llm` | peer, `d14431f` |
| `test_60::test_platform_never_imports_an_app` | same file | peer, `d14431f` |
| `test_211::test_every_table_has_a_retention_class` | `voice_tu_dien` unclassified | peer |
| `test_155::…unique_song_con_deu_nam_trong_drill` | `uq_voice_tudien_owner_tu` not in drill | peer |
| `test_82::test_vendor_engine_co_mat` | `apps/upscalevideo/vendor/` — **0 files in git** | worktree |
| `test_362::test_cay_chinh_co_dot_git_la_THU_MUC` | `.git` is a *file* in a linked worktree | worktree |
| `test_362::test_cay_lien_ket_co_dot_git_la_TEP` | inspects the main tree, where `.git` is a *dir* | worktree |

⭐ The last three are structural, and worth stating as a finding rather than an excuse: **the
gate can never be green inside a linked worktree**, and this repo's own `tools/cay_rieng.py`
creates linked worktrees. The deploy-safety test written to stop "never deploy from a worktree"
inverts and fails when actually run from one. Reported to the peer lane; not touched, because
they own it.

ASV-owned tests: **242 pass**, including under `-n 8` (the configuration that exposed MAX_PATH).

## Debt carried out of this phase

- **RISK-14-01** — type-B cross-app edges; exit is lifting shared helpers into `platform_core`.
- `tu_dien_rieng` still has no wired source (carried from Phase 12).
- `voice_tu_dien` classification and the `dieu_khoan.py` layering violation belong to the peer lane.
