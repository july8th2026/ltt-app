# MVP Completion Plan

> Detailed implementation plan from the 2026-07-29 audit
> (`docs/_luutru/AUDIT_REPORT.md`) to a working MVP. Sequenced so the bot becomes
> *actually runnable* before more platform surface is built on top of it.
> Phase numbering `PA`/`PB` is used for the new remediation work so it does
> not collide with `docs/_luutru/WEB_PLATFORM_PLAN.md`'s P0–P11.

## Guiding constraint

The audit found the desktop bot cannot publish today. Building P4/P5 web
modules on top of that would produce a dashboard that looks complete and
publishes nothing. **Remediation (PA) goes first.**

Deployment to the VPS and DNS changes remain gated on explicit user
authorization (AGENTS.md) — unchanged by the continuous-implementation
instruction.

---

## PA — Runnability remediation

**Goal:** every reason the bot cannot publish is either fixed, or reported
loudly with an actionable message instead of failing silently.

### PA-1 — Make credential failures loud (fixes D2, surfaces B1/B2)

- `core/token_store.py::_load()`: distinguish three states instead of
  collapsing them to "0 accounts":
  1. file absent → legitimately no accounts (silent, current behavior);
  2. file present + decrypt fails → **raise/record a distinct
     `TokenStoreUnreadableError` state**, exposed via a property the GUI
     and preflight can read;
  3. file present + decrypt OK but empty list → no accounts.
- Same treatment for `core/tiktok/token_store.py` (already warns; make it
  structured rather than a `print`).
- Do **not** crash the app on state 2 — the GUI must still open so the
  user can re-connect accounts. Surface it as a blocking banner instead.
- **Tests:** synthetic Fernet blob encrypted under a throwaway key →
  assert the unreadable state is reported, not silently swallowed; assert
  a genuinely-absent file still reports "no accounts" quietly.

### PA-2 — Fix the queue-preview crash (fixes D1)

- Replace `client.worksheet.get_all_values()` with the supported
  `SheetClient` API. `SheetClient` currently exposes no bulk row reader,
  so add one narrow public method (`get_all_rows()`) rather than reaching
  into internals from the GUI.
- **Tests:** unit test the new `SheetClient` method against a mocked
  Google API response; regression-test that the GUI code path no longer
  raises `AttributeError`.

### PA-3 — Preflight validator: config ↔ sheet (fixes B3, D4)

- New `core/preflight.py`: given a config + sheet id + tab, report
  - missing **mandatory** columns (currently only `col_schedule_time`) →
    ERROR;
  - missing optional-but-important columns (`col_status`, `col_error`,
    `col_fb_link`) → WARNING with the concrete consequence spelled out
    (e.g. "errors will not be written back to the sheet");
  - suggest the closest actual header name when a configured name is
    absent (the audit's `schedule_time_fb_dai` vs `schedule_time` case is
    exactly this).
- Called by: the doctor CLI (PA-4), the desktop Sheet Runner tab before
  `_start()`, and later the web module before enqueuing a run.
- **Tests:** table-driven over synthetic header sets — exact match,
  missing mandatory, missing optional, near-miss suggestion.

### PA-4 — `tools/doctor.py` — one-command health report

Single command an operator (or a future support session) can run to get
the audit's whole picture without a debugging session:

- runtime paths + which environment profile is active;
- config validation result;
- token store readability per platform (**never** printing a token);
- sheet connectivity + per-tab preflight for configured workers;
- worker-list presence;
- exit code non-zero when a blocking problem exists, so it can gate a
  deploy script later.
- **Tests:** run against a synthetic config in `tmp_path`; assert exit
  codes and that no secret-shaped value appears in the output.

### PA-5 — Persist the worker list (fixes D3)

- New `core/worker_store.py`: load/save `data/workers.json` atomically
  (reusing `utils/atomic_io.py`), schema-versioned like `core/settings.py`.
- `gui/sheet_runner_tab.py`: save on add/remove, load on init — so the
  user stops re-adding workers every launch.
- `worker_main.py`: prefer `data/workers.json` over the current legacy
  `sheet_tab` guess; keep `--workers` as an explicit override; **remove**
  the silent legacy fallback that the audit proved wrong for this install
  (fail with a clear message instead).
- **Tests:** round-trip, atomic-write interruption, schema-version
  rejection, `worker_main` precedence (explicit `--workers` > stored file
  > error).

### PA exit criteria

- `python tools/doctor.py` reports every audit finding accurately.
- Undecryptable token files produce a clear message, never a silent 0.
- Queue preview renders (or fails with a real reason, not AttributeError).
- Worker list survives an app restart.
- Full regression still green; GUI smoke still 9/9.

---

## PB — Finish P3 (web foundation polish)

- PB-1 styled HTML error pages (401/403/404/500) replacing the JSON 404.
- PB-2 `docs/SECURITY_CHECKLIST.md` — the controls already implemented
  (PBKDF2, CSRF, secure cookies, rate limiting, loopback bind) written up
  as a reviewable checklist with verification commands.
- PB-3 a `/status` dashboard page surfacing PA-4's doctor output in the
  browser — this is what makes the dashboard useful on day one and is a
  natural bridge into P4.
- Accessibility/responsive audit at real browser widths remains deferred
  (no browser-automation tool available in-session) — explicitly recorded
  rather than silently skipped.

---

## PC — P4 Facebook web module

Only meaningful once PA-1 is done (an account list is worthless if the
token store silently reports empty). Order:

1. read-only first: account/page list + connection health from the
   existing `TokenStore`, no mutations;
2. server-side OAuth start/callback with state validation;
3. manual publish form → existing `UploadEngine` via a service layer;
4. idempotency key + double-submit protection;
5. history/audit views.

Live publish tests require explicit user authorization (AGENTS.md).

---

## PD — P5 TikTok web module

Mirrors PC, plus TikTok's compliance surface (creator info, privacy
level, AI-content/branded-content confirmations) which must not be
bypassable from the web UI — the existing desktop confirmations are the
behavioral reference.

---

## PE — P6/P7 scheduler, worker control, observability

Depends on PA-5 (persisted workers) and PC/PD. Job lifecycle states,
start/stop/drain from the dashboard, ownership lease/heartbeat on top of
P1's `WorkerApplication`, structured logs with correlation IDs (the
middleware already emits them), backup/restore rehearsal.

---

## Sequencing summary

```
PA (runnability)  ──►  PB (P3 polish)  ──►  PC (P4 FB)  ──►  PD (P5 TT)  ──►  PE (P6/P7)
   ▲
   └── blocks everything: a dashboard over a bot that cannot publish is worse than no dashboard
```

User-only actions that no code change can substitute for:

1. Reconnect Facebook accounts (B1).
2. Reconnect TikTok accounts (B2).
3. Decide the correct column mapping per sheet tab (B3) — PA-3 will
   report the mismatch and suggest names, but choosing the intended
   mapping is an operator decision about their own spreadsheet.
