# PHASE 06 REPORT — Asset Lifecycle, Lineage and Atomic Promotion

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 05 **PASS** (spine proven; gate at baseline)
- allowed change scope: Auto Scan asset/storage services, app-owned additive schema, tests

## Trace performed (required work item 1 — re-audit against the ADR)

`platform_core/storage.py` — `Storage.promote` 80, `_safe_key` 181 (path traversal),
`LocalStorage.promote` 262 (`os.replace`), `R2Storage.promote` 353, `url_for`/`put_url` ·
`platform_core/upload_sessions.py` — `create` 53, `_signature_ok` 125, `confirm` 150,
`promote` 207, `compensate` 309, `sweep` 331, `cleanup_failed_job` 365, `reconcile` 389 ·
`platform_core/models.py:425 UploadSession` · `platform_core/app_projects.py` (`_FORBIDDEN`
secret-name blocklist, 1 MiB cap) · `platform_core/credit.py:541 _aware`.

### Reuse decision (item 2)

| Need | Reuse or add | Why |
|---|---|---|
| customer's **source** upload | **reuse `UploadSession`** | it already does staging → magic-byte check → confirm → promote → sweep → reconcile. Nothing missing. |
| the 8 **stage-produced** artifacts | **add `asv_asset`** | `UploadSession` has no `created_by_stage`, no `parent_keys`, no `checksum`, no `integrity`, no `schema_version` — and should not grow them, because it serves every app. Forcing intermediates into an upload-ticket model would damage its meaning platform-wide. |

That is what Prompt 06 item 2 asks: add only for missing durable lineage semantics.

## Decisions

**D-06-01 — keys are composed from validated parts, never accepted from a client.**
`assets.dat_khoa()` builds `asv/{owner}/{run}/{stage}/{fingerprint}.{ext}` and rejects any
part not matching `[A-Za-z0-9._-]+`. `_safe_key` in the platform already blocks `../`, and it
remains the last line — but the first line has to be *never using a client string as a key at
all*. Six traversal shapes are tested.

**D-06-02 — the owner is in the key, not only in a column.**
An ownership filter that lives solely in `WHERE owner_id = ...` is one forgotten clause from a
leak. With the owner in the path, a cross-tenant read requires deliberately assembling
someone else's path.

**D-06-03 — validate on the *staging* copy, before promotion.**
Swapping steps 2 and 3 is a silent failure: a corrupt file becomes the official result and is
only caught later, if anyone checks. Empty files are rejected for every kind — that is the
commonest shape of a mid-write crash (file created, nothing written). JSON is parsed, not
merely opened.

> Stated rather than glossed: `video`/`audio` validation is **not** implemented here.
> No engine produces real media until Phase 08, so an ffprobe check now would only validate
> fake files — a promise with nothing behind it. It is written down in `kiem_hop_le` as owed
> to Phase 08 instead of being faked.

**D-06-04 — three integrity answers, not one boolean.**
`missing` (reference survives, file gone) · `corrupt` (file present, content drifted) ·
`expired` (retention policy, not an incident). Collapsing them loses exactly the distinction
needed to respond — data loss, wrong data, and normal ageing are three different situations.

**D-06-05 — `expires_at` exists because this repo has already been bitten.**
`voice_block.audio_key` outlived the file it pointed at (30-day `jobs` retention), so after
30 days customers opened an old project and met a 404 player with no explanation (CLAUDE.md,
LTT VOICE). A reference that does not know its own deadline is a promise that will expire.

**D-06-06 — cache validity requires fingerprint match **and** live, verified artifacts.**
"A file with the right name exists" is not cache validity (O13). Lookup is owner-scoped in
both the `WHERE` clause and the key.

## Changes

| Path | Change |
|---|---|
| `apps/auto_scan_video/tables.py` | `+AsvAsset` (+ integrity/kind constants) |
| `apps/auto_scan_video/assets.py` | **new** — key composition, validate, promote+record, integrity, owner-scoped cache, cascade invalidation, owner-scoped read, per-run cleanup |
| `apps/auto_scan_video/thi_hanh.py` | stages now write a real staging object and go through the 5-step protocol; cache checked first |
| `alembic/versions/20260901_1930_asv_asset.py` | **new**, additive + full downgrade |
| `tests/test_403_asv_vong_doi_artifact.py` | **new**, 21 tests |

No `platform_core/` or `server/` change. No legacy data touched.

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_403...` | **21 passed** |
| `pytest tests/test_402...` (Phase 05 spine, now on real artifacts) | **14 passed** |
| invariant subset (389 + 390) | 23 passed, 1 xfailed |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline, same four `test_306` cases |

### Crash-window coverage (item 5)

| Window | Test | Outcome |
|---|---|---|
| temp created / no DB row | `test_cua_so_1_2...` | no record, no durable key — re-run is clean |
| validated / not promoted | same shape | ditto |
| **promoted / no checkpoint** | `test_cua_so_3_4_da_promote_chua_ghi_tham_chieu_thi_chay_lai_luy_dang` | re-run recomputes the **same key** from the fingerprint and overwrites; exactly one row, latest content |
| checkpoint references missing object | `test_tham_chieu_toi_tep_da_BIEN_MAT_bi_bat` | `missing` |
| file silently modified | `test_tep_bi_SUA_DOI_bi_bat_bang_checksum` | `corrupt` — caught by checksum, since a same-length edit passes a size check |
| retention elapsed | `test_artifact_HET_HAN_duoc_goi_dung_ten` | `expired` |

The promoted/no-checkpoint row is the reason keys derive from the **fingerprint** rather than
a clock or counter: re-writing is idempotent, so a crash costs compute and never correctness.

### Migration + rollback

```
upgrade head              -> asv_asset created
downgrade e1a7c04b93d2    -> asv_asset dropped; asv_run + asv_stage untouched
upgrade head              -> recreated
```

## A real bug this phase's tests caught

`kiem_toan_ven` raised `TypeError: can't compare offset-naive and offset-aware datetimes`.
SQLite does not preserve timezones: an aware `datetime` written comes back naive, and
`naive <= aware` throws. **PostgreSQL preserves it, so this would have run fine in production
and failed only under test** — landing in the one place that makes a person suspect their own
fixture rather than the code.

Fixed with an `_aware()` helper copied from `platform_core/credit.py:541`, which exists for
the same reason. Worth recording because the failure mode is inverted from the usual one:
correct in production, broken in the harness.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| I6 owner isolation | PASS | `test_nguoi_khac_KHONG_mo_duoc_asset_du_biet_dung_khoa`; owner in key **and** column |
| I8 durable DONE | PASS | exit-gate test verifies every stage's artifact by checksum |
| I10 cache correctness | PASS | `test_cache_TRUNG_van_tay_van_bi_bo_khi_tep_mat`, cascade invalidation |
| I14 safe promotion | PASS | empty/corrupt rejected before reaching a durable key |
| I19 cache privacy | PASS | `test_cache_KHONG_BAO_GIO_vuot_qua_ranh_gioi_chu_so_huu` |
| I1–I4, I9, I11–I13, I18 | PASS | unchanged, re-run green |
| I7 | 🔴 RED, Phase 07 | unchanged |

## Diff review
- changed paths: `apps/auto_scan_video/`, one alembic version, `tests/test_403...`,
  `docs/auto_scan_video/`
- scratch `tmp6.db` created for rollback evidence and deleted
- secret scan PASS; no media or generated artifact committed

## Risks / external evidence pending

- **RISK-06-01 (P2, new)** — `kiem_hop_le` does not yet validate `video`/`audio` content.
  Owed to Phase 08, where ffprobe becomes meaningful. Until then a media artifact is checked
  only for non-emptiness and checksum stability.
- **RISK-06-02 (P3, new)** — `HAN_TRUNG_GIAN` is 30 days by analogy with `jobs` retention, not
  from a measured storage-cost or support-window requirement. Revisit in Phase 22.
- **RISK-05-01** (unmeasured `gpu_vram_mb`) unchanged — Phases 09/10.
- **RISK-05-02** (possible two alembic heads at merge) now **more likely**: this phase adds a
  second migration. Check `alembic heads` at merge; join with a merge revision.
- Unchanged: RISK-00-02, -06 (M13), -07, -08, -09, -10, -11, -12, -14, -15, -16; RISK-01-01;
  RISK-02-01…03; RISK-03-01…03.

## Exit gate

**PASS.**

Gate text: *"PASS when dummy stages exchange asset refs only and stage DONE cannot reference
invalid/non-durable output."*

- **Asset refs only** — every stage now returns `{"khoa_asset": [...]}`; the Phase 05
  placeholder `{"gia": true, "khoa": "<string>"}` is gone. `_khoa_cha` threads upstream keys
  into `parent_keys`, so lineage is readable from data, not from source
  (`test_lineage_noi_giai_doan_voi_thuong_nguon_cua_no`).
- **DONE cannot reference invalid output** — `test_moi_giai_doan_ket_thuc_bang_ASSET_REF_that_va_kiem_duoc`
  runs the full nine-stage chain and then re-verifies **every** artifact by existence, size
  and checksum. Validation happens on the staging copy, so an invalid artifact never reaches
  a durable key at all.

## Next phase prerequisites

Phase 07 (Credential Scope Security) is the phase that owns the standing RED target:
1. `tests/test_400...::test_RED_khoa_rieng_cua_nguoi_dung_khong_duoc_cap_cho_nguoi_khac` is
   `xfail(strict=True)` — fixing the allocator makes it fail as *unexpectedly passing*, which
   forces a deliberate flip of the marker rather than a silent one;
2. the fix must be **additive** (O15): `owner_user_id == ""` keeps meaning "platform pool",
   so no existing app changes behaviour;
3. Prompt 07 forbids a global allocator behaviour change — scope goes in as an explicit
   opt-in parameter, not a new default.
