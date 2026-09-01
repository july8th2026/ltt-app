# ADR-002 — Explicit credential scope for the API key allocator

- **Status:** ACCEPTED
- **Date:** 2026-09-01 (Phase 07)
- **Evidence SHA:** `c31b1ae`, worktree `phien/asv`
- **Closes:** RISK-00-06, invariant I7, gate G4

---

## Context

`ApiKey.owner_user_id` has existed since the table's first migration
(`alembic/versions/20260731_1600_them_bang_api_keys.py:24`, indexed) and is written by
`api_keys.tao_key(..., owner_user_id=)` (`api_keys.py:77,94`).

**It has never been read.** `api_pool._ung_vien` filtered on `enabled`, `status`,
`categories`, `supported_models`, rpm/tpm — and nothing else. A grep for `owner_user_id`
returns the model, the migration, and `tao_key`; **zero read sites**.

So a user-owned key would be handed to any user's request.

## Existing mechanisms traced

| Item | Where | State before this ADR |
|---|---|---|
| column | `models.py:673` | exists, indexed, always `""` in practice |
| writer | `api_keys.py:77,94` | accepts the parameter |
| callers of the writer | `server/admin.py:734`, `tools/import_api_keys_from_botgemini.py:109`, `tools/them_key_ltt_llm.py:79` | **none passes `owner_user_id`** |
| selection | `api_pool._ung_vien` 73, `chon_key` 101, `lay_key` 145, `thu_lan_luot` 155 | no owner filter anywhere |
| decryption | `api_keys.lay_credential` 126 | already the only decrypt point |
| safe preview | `models.ApiKey.key_preview`, `secretbox.preview` | already exists |

## The fact that makes this safe

**No write path in the repository sets `owner_user_id`.** Verified by reading all three
callers of `tao_key`. Every row that can exist today carries the empty string.

Therefore defining `"" = platform pool` **establishes** semantics for a column that had
none. It does not reinterpret a column anyone is relying on, and no existing row changes
behaviour. That is precisely the backward-compatibility O15 demands, and it is why Prompt 07
item 4 ("do not silently reinterpret all empty/nonempty owner fields") is honoured rather
than skirted: there is nothing in production to reinterpret.

## Decision

### D1 — Two explicit scopes, defaulting to the current behaviour

```python
PHAM_VI_POOL  = "platform_pool"   # default
PHAM_VI_RIENG = "user_owned"
```

`chon_key`, `lay_key` and `thu_lan_luot` all take `pham_vi=PHAM_VI_POOL, owner_user_id=""`.
Every existing call site omits both and is unaffected.

### D2 — The filter runs inside the query, before ranking

`_ung_vien` adds the owner predicate to the `SELECT`, not to a post-filter. The effective
owner is therefore known **before selection** (Prompt 07 item 3). Filtering afterwards means
a wrong selection already happened and is being corrected — and one day someone omits the
correction.

- `PHAM_VI_POOL` → `WHERE owner_user_id = ''`. The platform pool can never touch a private key.
- `PHAM_VI_RIENG` → `WHERE owner_user_id = :owner`. Exactly one owner.

### D3 — User-owned never falls back

Not to another user, and **not to the platform pool** — even when the pool is idle. A
customer choosing their own key is choosing whose quota and whose invoice this call lands on.
Silently substituting a house key spends the platform's money on a request that explicitly
asked not to, and the customer never finds out.

If a product ever wants "try mine, else the pool", it must ask for that in two calls, so the
fallback is a visible product decision rather than an allocator default.

### D4 — Fail closed on an incomplete request

`PHAM_VI_RIENG` without `owner_user_id` raises `PhamViError`. An unknown scope string raises
too. There is no safe guess here: every guess resolves to serving either another user's key
or the platform's, which are the two things I7 forbids.

### D5 — Decryption stays at the provider-call boundary

Unchanged, because it was already correct: `chon_key` returns the record, and
`api_keys.lay_credential()` is the only decrypt point. Confirmed by test rather than assumed.

### D6 — One audit-safe describer

`api_pool.mo_ta_an_toan(key)` returns `{key_id, provider, pham_vi, chu_so_huu (8 chars),
preview, status, health, rpm, tpm}`. No `credential`, no `credential_enc`.

It exists so callers do not hand-roll a dict for logging — every hand-rolled dict is a chance
for `credential` to reach a log line. I16 says no raw secret is persisted or logged; the way
to keep that is to make the correct path the available one.

## Invariants protected

| Inv | Mechanism | Test |
|---|---|---|
| I7 credential isolation | D1–D4 | `test_404` isolation block; `test_400` (was the strict RED target) |
| I6 owner isolation | owner filter in the query | `test_doan_trung_id_khoa_van_khong_dung_duoc` |
| I16 safe logs | D6 | `test_mo_ta_an_toan_khong_chua_bi_mat...` |
| O15 backward compatibility | D1 defaults | `TestTuongThichNguoc` (6 tests) + 100 pre-existing key tests |

## Compatibility impact

None measurable. All ten allocator call sites in `apps/` and `platform_core/` omit the new
parameters. `tests/test_75_api_keys.py`, `test_263`, `test_262`, `test_179` — **100 passed,
2 skipped**, unchanged.

**Residual risk, stated plainly:** if some deployment created keys with a non-empty
`owner_user_id` through a path outside this repository, those keys silently leave the
platform pool. No such path exists here, and the failure direction is the safe one — a key
stops being shared rather than starting to be. An operator would see `ThieuKeyError`, not a
cross-tenant leak.

## Migration / rollback

**No migration.** The column, its index and its writer already exist; only read behaviour
changed. Rollback is reverting `api_pool.py` — no data to undo.

## Alternatives rejected

| Option | Why rejected |
|---|---|
| Filter by owner unconditionally, no scope parameter | changes the meaning of every existing call site at once; O15 forbids a global allocator behaviour change |
| Keep no filter; scope at the app layer | every app would reimplement it, and the first one to forget leaks. The allocator is the only place that sees all requests |
| `PHAM_VI_RIENG` falls back to the pool when empty | D3 — spends platform money on a request that asked not to, invisibly |
| Infer scope from whether `owner_user_id` was passed | implicit scope is how "did anyone pass this?" becomes a security boundary. An explicit enum fails closed on a typo |
| A third `PROJECT` scope now | Prompt 07 allows it "only if a real requirement exists". None does yet; adding it now would freeze a guess into a contract |
