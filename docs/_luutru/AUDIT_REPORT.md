# Audit Report — 2026-07-29

> Pre-implementation audit answering one question: **can the bot actually
> publish right now?** Answer: **no** — two independent blockers, detailed
> below. No secret value appears in this file.

## 1. Automated checks — all PASS

| Check | Command | Result |
|---|---|---|
| Full regression | `python -m pytest tests -q` | **1021 passed**, 1 skipped, 23 subtests, 289s |
| GUI smoke | `python tests/gui_smoke_validator.py` | **PASS** — 9/9 tabs, 9 screenshots, 0 errors |
| Secret scan | `python tools/scan_source_secrets.py` | **PASS** — 296 files, 72,949 lines, 0 findings |
| Config validation | `core.config_validator.validate_config()` | **PASS** — 1 advisory warning (`tiktok_audit_approved` is true) |
| Google Sheets connectivity | `SheetClient.connect()` + `get_all_tabs()` | **PASS** — 26 tabs listed |
| Web dashboard | real `uvicorn` + `curl` | **PASS** — `/health/live` 200, `/login` renders |

The test suite passing does **not** mean the bot works: every failing
condition below sits in configuration/credential state that the test
suite deliberately mocks out.

## 2. Blockers — bot cannot publish

### B1 — Facebook token store is undecryptable (CRITICAL)

- `data/tokens.enc` exists, **27,704 bytes**, valid Fernet format
  (`gAAAAA…` prefix) — so real account data was written at some point.
- Decryption fails with `InvalidToken` under **every** candidate key:
  | Key source | Result |
  |---|---|
  | Registry `MachineGuid`, default view | `InvalidToken` |
  | Registry `MachineGuid`, explicit 64-bit view | `InvalidToken` |
  | Registry `MachineGuid`, explicit 32-bit (WOW6432Node) view | key absent |
  | Fallback `node_system_machine` formula | `InvalidToken` |
- The P0 recovery backup
  (`_recovery/LTTStudio_P0_prechange_20260729_165857.zip`) contains a
  `data/tokens.enc` that is **byte-identical** (same SHA-256 prefix
  `d83df03f501a9b13`) — so it is not an older, decryptable copy.
- **Conclusion:** these tokens were encrypted under a machine identity that
  no longer exists on this host (different PC, or a Windows reinstall that
  regenerated `MachineGuid`). They are **not recoverable by any code
  change**. `TokenStore.count()` returns 0.

### B2 — TikTok token store is undecryptable (CRITICAL)

Same failure mode: `data/tiktok_tokens.enc`, 100 bytes, valid Fernet
format, `InvalidToken`. Unlike the FB store, this one at least prints a
warning (`Fernet decrypt failed … attempting plain-text fallback`).
0 accounts loadable.

**Required action — user only.** Reconnect Facebook and TikTok accounts
through the desktop app (`🔐 Tài khoản FB` / `🎵 Tài khoản TikTok` tabs).
No code change can decrypt these files. ADR-013's external-key override
prevents this from recurring after a future host change, but only applies
to tokens saved *after* an external key is configured.

### B3 — Config column mapping does not match any sheet tab (HIGH)

Checked all 26 tabs of the configured spreadsheet against the five
columns the runner reads:

- **0 of 26 tabs fully match.**
- `col_schedule_time = "schedule_time_fb_dai"` — the only **mandatory**
  column (`SheetClient.get_next_pending_row` raises without it). Present
  in only 2 tabs (`Hùng Sử Trung Hoa`, `VertexTruong`). The configured
  legacy default tab `LTT nerf war` uses **`schedule_time`** instead.
- `col_target_page = "target_page"` — **absent from all 26 tabs**.
  Non-fatal: `SheetRunner` falls back to the worker's configured page.
- `col_error = "error_message_dai"` — absent from all tabs (they have
  `error_message` / `error_message_fb`). Non-fatal but **silently
  destructive to observability**: `mark_error()` skips missing columns,
  so failures are never written back to the sheet — an operator sees a
  row stuck with no explanation.

Reproduced live: running `worker_main.py` against the real config
connected to the sheet successfully, then failed at the **read** step with
`Không tìm thấy cột schedule_time 'schedule_time_fb_dai'`. The failure
occurred inside `get_next_pending_row()`, i.e. **before** any
`mark_running()` call — **no row was written and no sheet data was
modified**.

## 3. Code defects found

| ID | Severity | Location | Defect |
|---|---|---|---|
| D1 | Medium | `gui/sheet_runner_tab.py:594` | Calls `client.worksheet.get_all_values()`, but `SheetClient` has no `worksheet` attribute (leftover from a gspread → Google API migration). The queue-preview panel therefore **always** fails and shows an error box. |
| D2 | Medium | `core/token_store.py::_load()` | Swallows a decrypt failure (`except Exception: pass`), then swallows the resulting JSON parse failure (`except Exception: self._accounts = {}`). Result: an undecryptable token file is indistinguishable from "no accounts connected" — exactly the state hiding B1. The TikTok store warns; the FB store is silent. |
| D3 | Medium | `gui/sheet_runner_tab.py` | The worker list (`self._workers`) is built in-session and **never persisted**. Users must re-add every worker on each app launch, and no headless/server process can reproduce the operator's real configuration. |
| D4 | Low | config | `col_error` points at a non-existent column (see B3) — error write-back silently disabled. |

## 4. What this means for the roadmap

`worker_main.py`'s "default single worker from legacy `sheet_tab`/`sheet_id`
config keys" (added in P1) is now demonstrably wrong for this
installation: it targets `LTT nerf war`, whose schedule column does not
match the config. D3 is the underlying cause — there is no persisted
source of truth for what the workers actually are. Fixing D3 is a
prerequisite for P6 (scheduler/worker control) and for any headless or
web-driven run, so it is pulled forward into the remediation phase.
