# PHASE 07 REPORT — Credential Scope Security

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 06 **PASS**
- inherited RED target: `tests/test_400...::test_RED_khoa_rieng_cua_nguoi_dung_khong_duoc_cap_cho_nguoi_khac`, `xfail(strict=True)` since Phase 04
- allowed change scope: API key/provider pool code as needed for explicit scoping; tests

## Trace performed (item 1 — all `owner_user_id` CRUD/allocation callers)

| Role | Site | Finding |
|---|---|---|
| column | `platform_core/models.py:673` | `String(36)`, indexed, `default=""` |
| migration | `alembic/versions/20260731_1600_them_bang_api_keys.py:24,47` | present since the table was created |
| writer | `platform_core/api_keys.py:77,94` | accepts the parameter |
| writer callers | `server/admin.py:734`; `tools/import_api_keys_from_botgemini.py:109`; `tools/them_key_ltt_llm.py:79` | **none passes it** |
| **readers** | — | 🔴 **none existed** |
| selection | `api_pool._ung_vien` 73, `chon_key` 101, `lay_key` 145, `thu_lan_luot` 155 | no owner predicate anywhere |
| decrypt | `api_keys.lay_credential` 126 | already the sole decrypt point |
| consumers | 10 call sites across `apps/{anhnoibo,autosubvideo,prompt_ai_ommi,taoanh,taovideo,thumbnail}`, `platform_core/{job_runner,llm/dieu_phoi,image_gen/dich_gemini}` | all use positional/keyword args that exist today |

## Decisions

Full reasoning in [`../adr/ADR-002-credential-scope.md`](../adr/ADR-002-credential-scope.md).
The one that carries the phase:

**The fix is safe because no write path sets `owner_user_id`.** All three callers of
`tao_key` were read; none passes it. Every row that can exist carries `""`. So defining
`"" = platform pool` **establishes** semantics for a column that had none, rather than
reinterpreting one anyone depends on — which is exactly why Prompt 07 item 4's prohibition on
"silently reinterpreting all empty/nonempty owner fields" is satisfied rather than dodged.

Then:
- **D2** the owner predicate goes in the `SELECT`, so the effective owner is known *before*
  selection (item 3). Filtering afterwards means a wrong selection already happened.
- **D3** user-owned **never** falls back — not to another user, and not to the platform pool
  even when it is idle. Choosing your own key is choosing whose quota and whose invoice this
  call lands on; substituting a house key spends the platform's money on a request that said
  not to, invisibly.
- **D4** fail closed: `PHAM_VI_RIENG` without an owner raises, as does an unknown scope.
  Every possible guess resolves to serving another user's key or the platform's — the two
  things I7 forbids.
- **D6** one audit-safe describer, so no caller hand-rolls a logging dict. Each hand-rolled
  dict is a chance for `credential` to reach a log line.

## Changes

| Path | Change |
|---|---|
| `platform_core/api_pool.py` | `+PHAM_VI_POOL/PHAM_VI_RIENG/PhamViError`; owner predicate in `_ung_vien`; `pham_vi`/`owner_user_id` threaded through `chon_key`, `lay_key`, `thu_lan_luot`; `+pham_vi_cua`, `+mo_ta_an_toan` |
| `tests/test_400_asv_bat_bien_thi_hanh.py` | RED target **flipped to green**, renamed, history kept in the docstring |
| `tests/test_404_pham_vi_khoa_api.py` | **new**, 16 tests |
| `docs/auto_scan_video/adr/ADR-002-credential-scope.md` | new |

**No migration.** The column, index and writer already existed; only read behaviour changed.
Rollback is reverting one file — there is no data to undo.

This is a `platform_core/` edit, which O20 restricts. It is explicitly inside Prompt 07's
allowed scope ("API key/provider pool code only as needed for explicit scoping") and is the
additive shape O15 requires.

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_404_pham_vi_khoa_api.py` | **16 passed** |
| `pytest tests/test_400...` | **13 passed** — no xfail remains |
| **existing** `test_75_api_keys` + `test_263` + `test_262` + `test_179` | **100 passed, 2 skipped** |
| invariant subset (389 + 390) | 23 passed |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline, same four `test_306` cases |

### Required verification

| Required | Test |
|---|---|
| two-user concurrency | `test_hai_nguoi_dung_xen_ke_nhau_khong_lan_khoa` — 10 interleaved rounds, because ranking uses load counters so a single call would not exercise the ordering |
| guessed credential id denial | `test_doan_trung_id_khoa_van_khong_dung_duoc` |
| platform-pool compatibility | `TestTuongThichNguoc` — 6 tests + the 100 pre-existing key tests |
| disabled / cooldown / rate-limit | `test_khoa_bi_TAT...`, `test_cooldown_van_loai...`, `test_cham_tran_rpm...` — each asserted in **both** scopes, since a limit is a property of the key, not of the scope |

## The RED target

Phase 04 planted `xfail(strict=True)` so a fix would surface as *unexpectedly passing* and
force a deliberate flip. That worked as designed — but the first run after the allocator
change failed for a reason worth recording: the old assertion said "the returned key must not
belong to uA", and the fixed allocator does something **better** than return a different key.
It raises `ThieuKeyError`, because the only key present is private and the platform pool must
not see it.

The assertion was rewritten to the correct semantics — no key at all is the right answer, not
"here, borrow uA's" — plus the two positive cases (uB denied, uA served). The marker was
removed rather than loosened.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| **I7 credential isolation** | ✅ **CLOSED** | `test_404` isolation block; RED target now green |
| I6 owner isolation | PASS | guessed-id denial |
| I16 safe errors/logs | PASS | `mo_ta_an_toan` carries no secret; owner id truncated to 8 chars |
| I1–I5, I8–I14, I18, I19 | PASS | unchanged, re-run green |

## Diff review
- changed paths: `platform_core/api_pool.py`, two test files, `docs/auto_scan_video/`
- no migration, no fixture containing a real secret (fixtures use the literal
  `"bi-mat-gia"` / `"BI-MAT-THAT"`), no generated artifact
- `secret scan` PASS in the full gate

## Risks / external evidence pending

- **RISK-07-01 (P3, new)** — if a deployment created keys with a non-empty `owner_user_id`
  through a path outside this repository, those keys silently leave the platform pool. No
  such path exists here, and the failure direction is the safe one: a key stops being shared
  rather than starting to be. The operator sees `ThieuKeyError`, not a leak. Worth a one-line
  count check before deploy — recorded for Phase 22.
- **CLOSED: RISK-00-06** (`owner_user_id` written but never read).
- Unchanged: RISK-00-02, -07, -08, -09, -10, -11, -12, -14, -15, -16; RISK-01-01;
  RISK-02-01…03; RISK-03-01…03; RISK-05-01, -02; RISK-06-01, -02.

## Exit gate

**PASS.**

Gate text: *"PASS when user credential isolation is proven and existing key consumers retain
intended behavior."*

- **Isolation proven** — platform pool cannot see a private key (asserted over 5 rounds
  because ranking is load-dependent); user-owned never falls back even with an idle pool;
  A's key never reaches B; a guessed key id is useless; an incomplete scope request fails
  closed; all three entry points (`chon_key`, `lay_key`, `thu_lan_luot`) enforce it, since one
  unguarded door makes the fence decorative.
- **Existing consumers unchanged** — all 10 call sites omit the new parameters and take the
  default; 6 targeted backward-compatibility tests plus **100 pre-existing key tests pass**;
  the full gate sits exactly on the Phase 01 baseline.

## Next phase prerequisites

Phase 08 (Media Probe & Normalize) is the **first phase to touch a real engine**:
1. `assets.kiem_hop_le` currently validates `video`/`audio` only for non-emptiness — Phase 08
   owes it real ffprobe validation (RISK-06-01);
2. `MVP_CONTRACT.md` §2 input policy becomes enforceable: MIME allow-list, ≤ 2 h, must have an
   audio stream, and the H.264/HEVC copy-path check from D-ASV-03;
3. `tests/fixtures/asv_media.py` already provides both fixtures needed, including
   `tiny_mp4_silent()` for the "reject a video with no audio" rule;
4. the fingerprint still lacks `engine_id` + model version — must be added before any cached
   result can be trusted across an engine upgrade (O13).
