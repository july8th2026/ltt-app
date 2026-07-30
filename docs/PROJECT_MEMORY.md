# LTTStudio Social Publisher — Project Memory

> Canonical living memory for the desktop-to-web-platform migration.
> Read this file at the beginning of every new session.
> Never store any credential value in this file.

## Memory metadata

- Last updated: 2026-07-30
- Updated by: P4/P5/P6 session — web control plane connected to the app
- Memory schema: 1.0
- Current product mode: Windows desktop application; a local-only FastAPI
  dashboard shell now also exists under `server/` but is not the
  operational path yet (no publishing routes exposed — P4/P5)
- Web platform status: planned; P1/P2/P3 complete, PA remediation complete
  (see Phase status)
- **OPERATIONAL BLOCKER (user action required):** the bot cannot publish.
  Both token stores are undecryptable on this machine — see
  `docs/AUDIT_REPORT.md` B1/B2. Facebook and TikTok accounts must be
  reconnected through the desktop app. No code change can recover them.
- VPS status: available but not configured for this application
- Production deployment authorization: not granted
- Continuous-implementation mode: user authorized proceeding through phases
  without per-phase confirmation (2026-07-29), with a pass/fail test check
  at each phase boundary. Deployment to the VPS / DNS changes still require
  separate explicit authorization per AGENTS.md — that constraint was not
  lifted.

## Current objective

Continue operating the existing desktop Facebook/TikTok bot while building a
browser-based LTT AI Studio control platform locally. After the server version
passes all local release gates, package it and deploy it to the existing Windows
VPS as an always-on service.

The target experience is:

- a common LTT AI Studio dashboard;
- separate Facebook Bot and TikTok Bot modules;
- browser-based account, job, schedule, settings, history, and log management;
- publishing workers that continue running after the browser is closed;
- a reusable platform shell for future applications.

## Current verified facts

### Application

- Language: Python 3.10+.
- Desktop framework: CustomTkinter.
- Desktop entry point: `main.py`.
- `main.py` directly imports and launches `gui.main_window.MainWindow`.
- Existing publishing logic is primarily under `core/`.
- Facebook and TikTok publishing use their official HTTP APIs; the publishing
  engine is not Selenium-based.
- The current server requirements do not yet include FastAPI or Uvicorn.
- Runtime configuration is stored in `data/config.json`.
- Facebook and TikTok token stores are encrypted using a key derived from the
  Windows machine identity.
- Moving to the VPS therefore requires re-authorization or a deliberate token
  encryption migration.

### Runtime data

- Facebook token store: `data/tokens.enc`.
- TikTok token store: `data/tiktok_tokens.enc`.
- History databases: files under `data/`, including SQLite databases.
- Logs: `logs/` and `data/audit_log.jsonl`.
- Temporary videos: `temp_videos/`.
- OAuth and Google credential files currently exist under `secrets/`.
- Runtime data and secrets must not be included in source releases.

### Tests

- Test files matching `tests/test_*.py`: 31.
- Original tests collected on 2026-07-29 before the scanner tests: 962.
- Collection command: `python -m pytest --collect-only -q`.
- Full regression after P0 fixes:
  - 969 passed;
  - 1 skipped;
  - 23 subtests passed;
  - duration 219.72 seconds.
- GUI smoke:
  - 9 tabs attempted;
  - 9 screenshots created;
  - 0 captured errors;
  - result PASS.

### Version control and security

- Git repository status on 2026-07-29: initialized on branch `main`.
- Secure desktop baseline commit: `3eadb0d`
  (`chore: establish P0 secure desktop baseline`).
- A `.gitignore` exists but originally did not cover every secrets/config-backup
  path.
- Historical project documentation contained a literal old application secret.
- Security policy: secret values must be redacted from documentation before the
  first Git commit. Credential rotation status must be verified separately by
  the owner; never copy a value into this memory.
- The owner confirmed on 2026-07-29 that the previously exposed App Secret was
  reset. No credential value was requested, printed, or stored.

## Architecture decisions

| ID | Decision | Status | Reason |
|---|---|---|---|
| ADR-001 | Develop locally, deploy release artifacts to VPS | Accepted | Keeps production stable and makes testing/rollback possible |
| ADR-002 | Preserve desktop GUI during migration | Accepted | It remains the current operational path |
| ADR-003 | Add web/server adapters around the existing `core/` | Accepted | Avoids two divergent publishing engines |
| ADR-004 | Web dashboard is a control plane; worker runs independently | Accepted | Browser closure must not stop jobs |
| ADR-005 | Start with one orchestrator process | Accepted | Prevents duplicate schedules/uploads |
| ADR-006 | Use FastAPI/Uvicorn for the local/server web application | Proposed | Fits the Python core and API-driven architecture |
| ADR-007 | Use Caddy as the Windows HTTPS reverse proxy | Proposed | Supports multiple subdomains and managed TLS |
| ADR-008 | Run production processes as Windows Services | Proposed | Supports boot startup, restart, and no-RDP operation |
| ADR-009 | Keep runtime data and secrets outside release folders | Accepted | Enables safe updates and rollback |
| ADR-010 | Keep SQLite for initial single-instance work; reassess PostgreSQL before scale-out | Proposed | Minimizes migration risk while leaving a growth path |
| ADR-011 | Do not use Celery/Redis in the first web release | Proposed | Avoids unnecessary Windows infrastructure before queue scale is needed |
| ADR-012 | Use one reverse proxy for future applications, each on a private loopback port | Proposed | Supports a multi-application LTT AI Studio platform |
| ADR-013 | Token encryption key: prefer an operator-provisioned external key (`LTT_TOKEN_ENCRYPTION_KEY` / `LTT_TOKEN_ENCRYPTION_KEY_FILE`); fall back to the existing machine-bound derivation when unset | Accepted | Machine-bound keys make `data/tokens.enc`/`data/tiktok_tokens.enc` unreadable after any VPS reinstall/redeploy, forcing every account to be re-authorized. An external key is portable across hosts and lets tokens survive updates/rollbacks; the fallback keeps desktop behavior byte-for-byte unchanged for installs that never set the variable |

Accepted decisions may only be changed by recording a new ADR row with the
replacement decision and rationale. Do not silently rewrite architectural
history.

## Phase status

| Phase | Name | Status | Exit gate |
|---|---|---|---|
| P0 | Governance, baseline, and secret hygiene | COMPLETE | Safe repo boundary, baseline tests, recovery backup |
| P1 | Headless core boundary | COMPLETE | Worker starts/stops without importing GUI |
| P2 | Runtime configuration and data boundary | COMPLETE | Clean separation of source/data/secrets |
| P3 | Web platform foundation | COMPLETE | Authenticated local dashboard and health API |
| PA | Runnability remediation (from 2026-07-30 audit) | COMPLETE | Every blocker either fixed or reported loudly with an actionable message |
| P4 | Facebook web module | PARTIAL (read-only) | Required FB desktop workflows available on web |
| P5 | TikTok web module | PARTIAL (read-only) | Required TikTok desktop workflows available on web |
| P6 | Scheduler and worker control | PARTIAL (start/stop/status) | Reliable background operation with duplicate protection |
| P7 | Observability, backup, and recovery | NOT STARTED | Logs, health, backup, restore, and failure recovery verified |
| P8 | Local release candidate | PARTIAL | Production-like local soak test passes |
| P9 | Windows VPS deployment package | PARTIAL (built, untested on a real VPS) | Repeatable install/update/rollback scripts pass on staging |
| P10 | Controlled production launch | NOT STARTED | VPS runs without RDP and post-launch checks pass |
| P11 | Multi-application platform evolution | BACKLOG | Triggered only after the first production release is stable |

Detailed tasks and exit criteria are in `docs/WEB_PLATFORM_PLAN.md`.

## Completed phase — P0

### Completed in P0

- Established the local-first, release-to-VPS deployment direction.
- Created the detailed web-platform implementation plan.
- Created this canonical memory file.
- Added project instructions requiring future sessions to read and update memory.
- Counted 962 tests successfully during test collection.
- Strengthened ignore rules for secrets, configuration backups, runtime
  databases, audit logs, temporary test videos, and local backup directories.
- Redacted the discovered literal application secret from historical
  documentation.
- Validated that `docs/PROJECT_STATE.json` remains valid JSON.
- Scanned `docs/` for the discovered 32-character secret pattern; scan result
  was clean.
- Created and verified the pre-change recovery backup.
- Added a reusable source-boundary secret scanner and eight scanner tests.
- Final scan covered 268 prospective source files / 70,214 lines with zero
  findings.
- Visually checked the credential-sensitive GUI screenshots.
- Initialized Git and verified all tested secret/runtime paths are ignored.
- Confirmed Git candidate status contains no tested sensitive paths.
- Corrected 28 stale/non-isolated regression tests without changing their
  intended product behavior.
- Full regression now passes: 969 passed, 1 skipped, 23 subtests passed.
- Fixed an unattended GUI smoke modal hang.
- Fixed the Monitor refresh thread calling Tk from a background thread.
- Fixed pending Tk callback cleanup during window shutdown.
- GUI smoke now passes all 9 tabs without traceback.
- Added `docs/DESKTOP_BASELINE_RUNBOOK.md`.

- Created and verified the first secret-safe source baseline commit `3eadb0d`.
- P0 exit gate is complete.

## Completed phase — P1

### Completed in P1

- Added `core/worker_app.py` (`WorkerApplication`): unified
  `start()`/`stop()`/`status()`/`wait_stopped()` lifecycle over
  `SheetRunner` (1 worker, run under a crash-guarded thread) /
  `ConcurrentRunner` (N workers, already crash-guarded).
- Added `worker_main.py`: headless CLI entry point; loads
  `data/config.json`, defaults to the legacy single-sheet-tab worker, takes
  `--workers <file.json>` for multi-worker, handles SIGINT/SIGTERM.
- Added a whole-run ownership lock: `WorkerApplication` acquires a
  `SessionLock` per worker's target account *before* starting, closing the
  gap where the existing per-row lock in `core/sheet_runner.py` only fires
  once a job is picked up.
- Added a crash-safety net (`_GuardedRunnerThread`) so a single-worker
  runner that raises unexpectedly still releases the ownership lock and
  fires the stop callback exactly once — verified by test.
- Verified importing `worker_main` never pulls in `customtkinter` or any
  `gui.*` module (subprocess-isolated test).
- Verified the full CLI wiring (arg parsing → config load → default worker
  construction → start/stop callback plumbing → exit code) end-to-end
  in-process, with the runner stubbed so no network/credentials are needed.

### P1 exit-criteria evidence

- "Headless worker runs locally from a console" — `python worker_main.py
  --help` runs cleanly with no config/network access; the in-process
  end-to-end test proves the full argument→config→worker→stop wiring
  executes without error. A live run against real Sheets/Graph credentials
  was intentionally not performed — that needs explicit user authorization
  and is listed as a follow-up, not a blocker (P1's own scope note allows
  "safe/non-production fixture where possible", which the stub tests are).
- "Closing a controlling client does not stop the worker" — satisfied by
  construction: `WorkerApplication` owns its own daemon thread(s) tied to
  a `threading.Event`/`ConcurrentRunner`, never to the caller's object
  identity or scope, so a GUI tab or CLI process object going away does
  not call `stop()` implicitly. No separate process-boundary test needed
  yet — that becomes meaningful once P3+ splits API and worker processes.
- "Desktop and headless modes cannot own the same runner simultaneously" —
  `test_worker_application_ownership_lock_blocks_second_runner` passes.
- "Desktop regression gate passes" — `python -m pytest tests -q` → 975
  passed, 1 skipped, 23 subtests, 234.55s (969 prior + 6 new P1 tests).
- Memory records interfaces and changed files — this section.

### Deferred out of P1 (explicit decision, not a gap in exit criteria)

- `gui/sheet_runner_tab.py` still branches directly between
  `SheetRunnerThread`/`ConcurrentRunner` itself rather than going through
  `WorkerApplication`. Reason: P1's exit gate only requires the headless
  path to work independently of GUI, not that GUI be refactored to share
  it; rewiring the desktop tab needs its own GUI regression pass and is
  better scoped as an explicit P1-follow-up or folded into P3 dashboard
  work, not silently bundled into this session's diff.
- A real (non-stubbed) console smoke run of `worker_main.py` against live
  Sheets/Graph credentials — requires explicit user authorization per
  `AGENTS.md`.

## Completed phase — P2

### Completed in P2

- Added `core/runtime_paths.py`: resolves `data_dir`/`secrets_dir`/
  `logs_dir`/`temp_video_dir`/`config_path` from `LTT_*` environment
  variables, falling back to the existing desktop-relative defaults
  (computed from the module's own file location, not the process CWD, so
  it is correct regardless of where a headless process is launched from).
- Added `core/settings.py`: `Environment` profile enum (development /
  local-server-test / production, selected via `LTT_ENV`, default
  development — unchanged desktop behavior when unset), `load_settings()`
  composing runtime paths + config load + validation, and a
  `_check_schema_version()` gate (`CONFIG_SCHEMA_VERSION = 1`) that rejects
  a config declaring a newer schema than this build supports while
  treating configs with no declared version (all pre-existing installs) as
  current — no forced migration for existing users.
- Added `config.example.json` at the project root: generated from the real
  `data/config.json` key set with every secret/credential/ID-shaped key
  value replaced by a `REPLACE_ME_<key>` placeholder, `_schema_version: 1`
  added; verified 0 findings from `tools/scan_source_secrets.py` against
  this specific file's content (its own scanner rules, not just trusted by
  construction — the file lives at the project root, so the scanner's
  `data/`-only exclusion pattern does not even apply to it).
- **ADR-013 (token-encryption migration, accepted):** added an
  operator-provisioned external-key override to both `core/token_store.py`
  and `core/tiktok/token_store.py` (`LTT_TOKEN_ENCRYPTION_KEY` /
  `LTT_TOKEN_ENCRYPTION_KEY_FILE`), still combined with each store's
  existing per-platform salt so a shared external secret still yields
  distinct FB/TikTok keys. Falls back to the pre-existing machine-bound
  derivation when neither variable is set — verified byte-for-byte
  identical to the old formula in that case. Verified with a test that
  encrypts under one simulated machine identity and decrypts under a
  different one, succeeding only because of the external key — this is
  the actual scenario a VPS reinstall creates.
- Confirmed atomic config writes were **already implemented** before this
  session (`utils/atomic_io.py`, wired into `gui/settings_tab.py` since an
  earlier "F2-01 fix") — no new code needed for that specific P2 task.
- Added `docs/DATA_RETENTION_POLICY.md`: documents retention for every
  runtime data category already in the codebase (logs, audit log,
  content-history DB, temp videos, retry state, session locks, tokens),
  which mechanism enforces it and where, plus a P7 backup-scope
  cross-reference and two flagged (non-blocking) gaps: `retry_*.json` and
  `session_locks/*.lock` files are reclaimed correctly at read time but
  never proactively deleted when their target is retired.
- Neither `core/runtime_paths.py` nor `core/settings.py` is wired into
  `main.py`, `worker_main.py`, or the GUI yet — deliberately additive,
  same pattern as P1: prove the boundary before cutting existing entry
  points over to it (see "Deferred" below).

### P2 exit-criteria evidence

- "A source-only release can start validation without any real secret" —
  `config.example.json` + `load_settings()`'s missing-config/invalid-config
  paths only ever report key names (tested: a synthetic secret value
  placed in a deliberately-invalid config is asserted absent from the
  raised exception's message).
- "Production secrets can be injected without editing source files" —
  `LTT_TOKEN_ENCRYPTION_KEY(_FILE)`, `LTT_DATA_DIR`/`LTT_SECRETS_DIR`/etc.,
  and `LTT_CONFIG_PATH` are all environment-variable driven.
- "Persistent data survives a simulated release replacement" —
  demonstrated for tokens specifically (the machine-identity-change test);
  general config/data survival across a release replacement is exercised
  more fully in P8's "clean-install test," which this slice enables but
  does not itself perform.
- "Token migration/re-authorization strategy is approved and documented" —
  ADR-013 above.
- Full regression: `python -m pytest tests -q` → 1001 passed, 1 skipped,
  23 subtests, 224.34s (991 prior + 10 new: 6 schema-version tests + 6
  token-migration tests, minus double count — see change log for exact
  file-by-file counts).

### Deferred out of P2 (explicit decisions, not gaps)

- Protected file permission/ACL guidance for a Windows service account —
  meaningful once a concrete VPS service account exists (P9 territory);
  writing generic ACL guidance now without a real target would be
  speculative documentation.
- Wiring `worker_main.py` / `gui/settings_tab.py` / `main.py` to actually
  call `core.settings.load_settings()` / the new token-key override,
  instead of their current direct `json.load` / machine-bound-only paths —
  each cutover needs its own regression pass verifying error-path behavior
  didn't change, so bundling all of them into this slice was avoided.
- The two data-retention gaps noted in `docs/DATA_RETENTION_POLICY.md`
  (orphaned `retry_*.json` / `session_locks/*.lock` files) — low-impact,
  scoped as a future `MaintenanceDaemon` addition.

### Pre-publish operational warning

- TikTok token metadata check reports zero loadable accounts and a decryption
  fallback warning; Facebook metadata check also reports zero loadable accounts.
- Reconnect and verify the intended accounts before any real publish. This does
  not block P1/P2/P3 development.

## Active phase — P3

First P3 slice implemented this session: a working authenticated local
dashboard shell with health/readiness endpoints, no publishing behavior
yet (that's P4/P5). Verified with a real `uvicorn` process started and
queried over HTTP during this session, not just via `TestClient`.

### Completed in this P3 slice

- New `server/` package (FastAPI): `app.py` (application factory),
  `run.py` (uvicorn entrypoint, binds `127.0.0.1` by default per
  AGENTS.md), `settings.py` (session secret + admin credentials, layered
  on `core.settings`).
- `server/auth/`: `password_hashing.py` (PBKDF2-HMAC-SHA256, 600k
  iterations — stdlib-only, no new bcrypt/passlib dependency), `csrf.py`
  (synchronizer-token pattern), `rate_limit.py` (in-memory per-key sliding
  window, matches ADR-005/ADR-011's single-process-no-Redis constraint),
  `session.py` (login/logout/`require_login` dependency; clears the
  session dict on login as a session-fixation mitigation — see "Known
  limitation" below).
- `server/routes/`: `health.py` (`/health/live`, `/health/ready`,
  `/version`), `auth.py` (`/login` GET+POST, `/logout` POST), `dashboard.py`
  (`/`, protected, with FB/TikTok placeholder cards per plan P3 task
  "Add Facebook Bot and TikTok Bot placeholder modules").
- `server/templates/`: minimal dark-theme HTML shell, responsive meta
  viewport + relative widths (no JS framework — plain server-rendered
  forms), matching the plan's "no publishing endpoint exposed prematurely"
  constraint.
- `tools/hash_admin_password.py`: operator CLI to generate
  `LTT_ADMIN_PASSWORD_HASH` via `getpass` — never writes the plaintext
  anywhere.
- `requirements-server.txt`: fastapi/uvicorn/itsdangerous/jinja2/
  python-multipart/httpx. All were already present in this dev
  environment; the file documents them for a fresh install/deploy.
- Correlation ID middleware (`X-Correlation-ID` response header) for the
  plan's "request correlation IDs" task.
- A basic 404 JSON handler exists; no styled HTML error pages yet (see
  "Deferred" below).

### Bug caught and fixed during this slice

- Initial design wrapped config loading in a FastAPI `lifespan` async
  context manager. `fastapi.testclient.TestClient` only runs lifespan
  hooks when entered as `with TestClient(app) as c:` — a plain
  `TestClient(app)` instance (as used in most of these tests) never
  triggers it, so `app.state.core_settings` stayed unset and
  `/health/ready` always reported 503 regardless of config validity.
  There was no actual async resource to wait on, so the fix was to drop
  the lifespan hook and resolve `core_settings` synchronously inside
  `create_app()` instead — simpler and correct under both TestClient
  styles and real uvicorn.
- A related test-environment gotcha (not an app bug, documented so it
  isn't rediscovered): `SessionMiddleware(https_only=True)` correctly
  marks the session cookie `Secure`. httpx's cookie jar (used by
  `TestClient`) will not resend a `Secure` cookie over the default
  `http://testserver` base URL, which broke every multi-request test
  (CSRF token issued on GET /login appeared missing on POST /login) until
  tests were switched to `base_url="https://testserver"`. This mirrors
  real deployment correctly — the browser always talks HTTPS to Caddy —
  so no application code changed, only the test client configuration.

### Known limitation — session store

Sessions are Starlette's default: an `itsdangerous`-signed, purely
client-side cookie (no server-side session table). Logout works (clears
the cookie's payload), and login clears any pre-auth session state before
issuing a new one, but there is no server-side session ID that can be
forcibly revoked (e.g., "log out this session from another admin
session," or true invalidation if `LTT_SESSION_SECRET` isn't rotated).
Acceptable for a single-admin local/VPS dashboard in the first release
(no Redis/DB session store per ADR-011); revisit if P6/P7 introduces a
shared job/session store for other reasons.

### Deferred out of this P3 slice (explicit decisions, not gaps)

- Styled HTML error pages (currently a minimal JSON 404 handler) — cosmetic,
  lower priority than the security-boundary work done this slice.
- A formal accessibility/responsive audit across real browser widths — the
  templates use a responsive viewport meta tag and relative widths, but
  this was not verified in an actual browser at multiple widths (no
  browser automation tool was used this session).
- A formal "security review checklist" as a standalone document — the
  concrete controls it would list (password hashing, CSRF, secure
  cookies, rate limiting) are implemented and tested, but no separate
  checklist artifact was produced.
- Wiring `worker_main.py`/desktop settings into `core.settings` remains
  deferred from P2 (unchanged this session).

### Pre-publish operational warning (P3 addendum)

- The `server/` package is additive only — `main.py` (desktop entry
  point) does not import anything from `server/`, and nothing in `core/`
  was changed to accommodate it beyond what P1/P2 already added.

## Important implementation constraints

1. Do not import `gui.*` from `worker_main.py`, `server/`, or core service
   factories.
2. GUI callbacks must become optional adapters, not required dependencies.
3. A worker ownership lock must prevent desktop and server modes from operating
   on the same job source concurrently.
4. If FastAPI and the scheduler run in one process, production must use exactly
   one application worker process.
5. If the API and scheduler are later separated, introduce a durable command/job
   store before enabling more than one worker.
6. Public ports are 80/443 through the reverse proxy. Application ports bind to
   `127.0.0.1`.
7. The dashboard must require authentication. OAuth callback endpoints require
   state validation and must not expose tokens to the browser.
8. A code release must never overwrite production databases, tokens, secrets, or
   user configuration.
9. Every phase must preserve desktop functionality until the documented cutover.

## Known risks

| Risk | Severity | Mitigation |
|---|---|---|
| Duplicate posts from two schedulers | Critical | Ownership lock, single orchestrator, duplicate/idempotency tests |
| Secrets committed to Git | Critical | Ignore rules, secret scan, external secrets storage |
| Machine-bound token encryption blocks migration | High → Mitigated (ADR-013) | External-key override implemented and tested (`LTT_TOKEN_ENCRYPTION_KEY`); not yet wired into a real VPS deployment — remains a P9 action item to actually provision and rotate the key operationally |
| GUI logic tightly coupled to runner callbacks | High | Introduce service/factory boundary incrementally |
| SQLite concurrency during API/worker split | High | One process initially; WAL/timeout tests or PostgreSQL before split |
| Browser dashboard exposed without strong auth | Critical → Mitigated (P3) | PBKDF2 password hashing, signed httpOnly+Secure session cookies, CSRF synchronizer token, per-IP login rate limiting — all implemented and tested; no formal external security review performed yet |
| Update overwrites runtime data | Critical | Versioned releases and separate persistent data directories |
| Multiple Uvicorn processes duplicate background workers | Critical | One process or separate dedicated worker service |
| Windows service has different paths/permissions | High | Absolute runtime paths, dedicated service account, staging test |
| Desktop regressions during refactor | High | Baseline suite and phase-by-phase regression gates |

## Immediate next actions

1. Inventory GUI runner lifecycle, callback dependencies, and ownership points.
2. Define the `WorkerApplication` interface and status/event models without
   changing desktop behavior.
3. Add headless import and lifecycle tests before wiring the implementation.

## Session change log

### 2026-07-30 — Tai cau truc thanh nen tang nhieu app (LTTSTUDIOSAPP)

- Goal: dung mot thu muc chuan chua moi app, moi app mot duong dan duoi
  app.lttstudios.com, va chung minh them app khong phai sua nen tang.
- Status: completed cho phan vo nen tang. Hang doi job dung chung + nhieu
  nguoi dung + so credit that: chua lam (giai doan sau).

- Files changed:
  - Thu muc moi `d:\CODE AI\LTTSTUDIOSAPP` — 385 file tu ban cu, KHONG kem
    data/config.json, secrets/, *.enc, *.db, logs.
  - New: `platform_core/registry.py` (hop dong app), `platform_core/storage.py`
    (lop boc luu file), `apps/socialbot/manifest.py`, `apps/demo/*`,
    `server/templates/home.html`, `demo.html`, `cloudflare/config.yml.example`,
    `docs/00..04_*.md`, `tests/test_60_app_registry.py` (19 test).
  - Changed: `server/templating.py` (cap `nav_apps()`), `server/app.py`
    (mount_all), `server/routes/dashboard.py` ("/" thanh trang chu liet ke app),
    `server/templates/base.html` (sidebar sinh tu manifest thay vi viet cung),
    `requirements`/`.gitignore`/`README.md`.

- Behavior changed:
  - "/" gio la trang chu liet ke app, doc tu `apps/*/manifest.py`. Phan blocker
    cua doctor van giu o tren cung.
  - Sidebar sinh tu manifest. Them app = them thu muc, khong sua giao dien.
  - `credit_for()` TU CHOI job khong tra duoc gia thay vi tra 0.
  - App nap loi khong lam sap nen tang — hien ly do tren trang chu.

- Tests run:
  - `python -m pytest -q` -> **1363 passed, 1 skipped, 23 subtests**
  - `python tools/scan_source_secrets.py` -> **0 findings, PASS**
  - Chay cuc bo: "/" liet ke 2 app + 2 blocker; "/demo" chay job that, tra
    ket qua va tinh dung credit tu manifest.
  - Chung minh mo rong: tao `apps/thunghiem/` chi voi manifest.py -> tu hien
    tren trang chu ("3 app da nap") va tra dung gia credit, KHONG sua file nao
    cua nen tang. Da xoa sau khi chung minh.

- Decisions:
  1. **Ten `platform_core` chu khong phai `platform`.** `platform` la module
     chuan cua Python; mot package cung ten o goc se che mat stdlib va gay loi
     o nhung thu vien khong lien quan.
  2. **Giu `core/` va `utils/` o goc.** Tach chung vao apps/ se pha duong
     import `core.*` cua 15.489 dong code. Khong doi lay gi ngay bay gio.
  3. **socialbot duoc dac cach giu route o duong dan goc.** Doi sang
     `/socialbot/...` se pha 1.344 test va pha ca Redirect URI OAuth dang
     chuan bi khai bao o Meta/TikTok Portal. Da ghi ro trong docstring de sau
     nay khong ai tuong do la thiet ke mau.
  4. **App demo giu lai vinh vien.** Nghiem thu ha tang bang Seedance ton
     1,52-6,82 USD moi lan chay (1080p = 0,682 USD/giay video). App demo di
     qua dung chuoi do voi chi phi 0 dong.
  5. **`credit_cost` la HAM chu khong phai hang so** — gia thuc te phu thuoc
     tham so (giay video x do phan giai).

- Loi cua toi trong phien nay:
  - Script copy dau tien loai ca thu muc `data/`, nen mat `data/translations/`
    va `data/assets/` — do la TAI NGUYEN NGUON di kem code, khong phai du lieu
    van hanh. Lam vo 3 test i18n. Da sua script va bo sung.
  - `AppManifest.requires` khai thieu annotation kieu nen dataclass coi la bien
    lop, constructor tu choi tham so. Da sua.

- Security/data impact:
  - Thu muc moi KHONG chua bi mat nao: config.json duoc gieo tu
    config.example.json, khong copy ban that.
  - `.gitignore` them `cloudflare/config.yml`, `cloudflare/*.json`,
    `data/files/`, va mo ngoai le cho `data/translations/`, `data/assets/`.

- Known issues:
  - Chua co hang doi job dung chung — app demo chay ngay trong request, chi
    hop le vi no mat vai mili-giay. App that phai qua hang doi (Cloudflare cat
    o 100 giay).
  - Chua co nhieu nguoi dung, chua co so credit that.
  - Thu muc cu `BOT UP Facebook/` van con — la ban chup du phong. Sua o hai noi
    se lech nhau; can xoa khi da yen tam.

- Next actions:
  1. Nguoi dung: dung Cloudflare Tunnel theo `docs/04_CLOUDFLARE_TUNNEL.md`.
  2. Chot schema DB co user_id + bang job + so credit ghi them (append-only).
  3. Hang doi job + worker pull, nghiem thu bang app demo truoc khi cam app
     tinh phi.

### 2026-07-30 — W4-W6: parity finished, desktop removed, OAuth on the web

- Goal: finish `docs/WEB_PARITY_PLAN.md` W4-W6 and reach an MVP that runs
  entirely on the web.
- Current phase: W1-W6 complete.
- Status: completed (7 items remain that only the user can do - see
  `WEB_PARITY_PLAN.md` section 6).

- Files changed:
  - New: `server/services/monitor_service.py`, `audit_service.py`,
    `oauth_service.py`, `content_tools.py`; `server/routes/monitor.py`,
    `oauth.py`; `templates/monitor.html`, `audit.html`, `oauth_result.html`,
    `oauth_tiktok_disclosure.html`; `tests/test_50..53_*.py`.
  - Deleted: `gui/` (26 files), `main.py`, 5 `.bat` files, `BOT_UP_FACEBOOK.spec`,
    `tests/gui_smoke_validator.py`, `tests/test_30_operation_tab_split.py`,
    `scripts/_demo_record*.py`, 3 `.backup_*` dirs, `server/routes/placeholder.py`,
    `templates/placeholder.html`, `tools/check_oauth_relay.py`,
    `tools/simulate_oauth_flow.py`, `MIGRATION.md`,
    `docs/DESKTOP_BASELINE_RUNBOOK.md`, `dist/`.
  - Refactored: `core/auth_manager.py` (531 -> 354 lines),
    `core/tiktok/auth_manager.py` (748 -> ~300 lines) - split into
    `build_authorize_url()` + `complete_oauth()`, localhost transport and the
    OAuth relay removed.

- Behavior changed:
  - `/monitor`, `/audit`, `/oauth/*` are real pages. Every desktop tab now has
    a web equivalent; `BUILT_PAGES` has no `False` entry (enforced by test).
  - Provider OAuth runs in the app. `state` + PKCE `code_verifier` live in a
    server-side store: TTL 600s, single-use, bound to the browser session via
    a nonce in the signed session cookie. The verifier never leaves the server.
  - `MaintenanceDaemon` now starts from the web app's lifespan.
  - Config files are read with `utf-8-sig`.
  - Removed 6 dead config keys everywhere, including the live VPS config (one
    was the OAuth relay secret).
  - `requirements.txt` dropped `customtkinter`, `Pillow`, `qrcode[pil]`,
    `google-auth-oauthlib`.

- Tests run:
  - `python -m pytest -q` -> **1344 passed, 1 skipped, 23 subtests passed**
  - `python tools/scan_source_secrets.py` -> **0 findings, RESULT: PASS**
  - `python tools/build_release.py` -> 383 files, 23.4 MB, secret scan PASS
  - Live browser check of all 11 routes -> HTTP 200
  - Live check of the 3 Content Vault actions -> export downloads a
    BOM-prefixed CSV, duplicates renders, CSV import reports per-row errors

- Decisions:
  1. **Split the auth managers instead of duplicating them.** The desktop
     transport called the same two new methods, so the Graph / TikTok work had
     exactly one implementation throughout the migration.
  2. **Deleted the OAuth relay rather than leaving it dormant.** It existed only
     to work around the missing public callback; keeping it would leave a
     second, weaker path into the token store.
  3. **Repointed every gui-dependent test before deleting `gui/`.** The
     TikTok-audit guards in `test_31` were rewritten against the web
     implementation - the compliance requirement survives, only its location
     changed.
  4. **Did not auto-fix the redirect URIs in config.** Changing config without
     also registering the URL at the provider turns a clear in-app instruction
     into an opaque provider error. Both halves must happen together, and the
     portal half needs the user's account.
  5. Kept one desktop limitation on purpose: CSV import parses and previews but
     does not write to the Sheet, because the Sheet writer was never built.

- Three gaps that only surfaced during the deletion (the reason for decision 3):
  1. `MaintenanceDaemon` was started only by `gui/main_window.py`. Deleting the
     desktop would have silently stopped retention pruning and app-status
     probing while every unit test stayed green.
  2. Three Settings actions had never been ported (Export Content History,
     Cross-target duplicates, Import CSV). Config-key coverage was 100%, which
     is precisely why this was missed - those buttons were not config.
  3. `_severity_prefix` was missing on the web, so a `[W3] Loi ...` line lost
     its error marker entirely (worker colour overrides level colour). Also had
     to compute the colour *before* prefixing, or `[W3]` moves off the start of
     the string and the worker colour is lost too.

- Security/data impact:
  - The dead OAuth relay secret was removed from the live config and its backup
    deleted. It was already inert (no code reads it).
  - `InstalledAppFlow.run_local_server()` removed from `utils/sheet_client.py`:
    on a server it blocked forever inside a request with no error. It now
    refuses with the Service-Account instructions instead.
  - OAuth callbacks require an authenticated session, so a stray request cannot
    write into the token store.

- Known issues:
  - **My own incident:** the VPS config-cleanup script used
    `Out-File -Encoding utf8`, which in PowerShell 5.1 writes a BOM;
    `json.load()` raises on it, so `/health/ready` returned 503 while the
    service ran normally. Fixed at the root (`utf-8-sig` readers) rather than
    just repairing the file - a user editing `config.json` in Notepad would hit
    the same trap.
  - TT Audit reports 1 blocking + 1 warning, both user actions (privacy policy
    must mention TikTok; official logo asset missing).
  - Sheet reads still 403 until the user shares the Sheet with the service
    account.

- Rollback: `C:\LTTPlatform\app.previous` is intact;
  `deploy\windows\rollback.ps1` restores it.

- Next actions:
  1. User: share the Sheet with the service account (Editor).
  2. User: change the Redirect URIs at Meta + TikTok, then match them in
     Settings.
  3. User: rotate the admin password exposed in conversation.

### 2026-07-30 — FIRST REAL DEPLOYMENT: dashboard live on a Windows VM

- Goal: actually deploy, not just prepare a package.
- Status: **dashboard is running and reachable on the LAN.** Operator
  logged in successfully through a browser.

#### Target environment (differs from the original plan — record this)

The Vultr VPS `64.176.84.87` was **abandoned**: it ran Windows Server
2012 R2 Evaluation (PowerShell 4.0, no `Add-WindowsCapability`, Python
3.13 unsupported, EOL since Oct 2023). Deployment moved to a **Proxmox VM
on the operator's own LAN**:

- `192.168.2.140`, Windows Server 2022 Standard **Evaluation**
  (135 days left at deploy time — needs `slmgr /rearm` or a real key),
  PowerShell 5.1, Python 3.13.5, 4 vCPU / 4.5 GB RAM.
- Operator's LAN is `192.168.2.0/24`; the dev machine is `192.168.2.88`.
- Public IP `14.177.12.60` (VNPT Hanoi), **dynamic**, but confirmed *not*
  CGNAT (modem WAN IP matches the public IP), so port forwarding is
  possible in principle. Whether VNPT blocks inbound 80/443 is **still
  unverified** and gates the chosen exposure path.
- Access for automation: SSH key auth (`~/.ssh/ltt_vps`) into
  `Administrator@192.168.2.140`, key installed in
  `C:\ProgramData\ssh\administrators_authorized_keys`.

#### What is running now

```
C:\LTTPlatform\  app\ | app.previous\ | data\ | secrets\ | logs\ | venv\ | tools\
```
Services `LTTStudioWeb` (uvicorn on 127.0.0.1:8000) and `Caddy`
(:80 -> loopback) both auto-start. `LTT_ENV=development` deliberately,
because `production` marks the session cookie Secure and the LAN phase is
plain HTTP — **must switch to `production` when HTTPS goes live.**

Verified end-to-end: health endpoints, all six protected routes redirect
anonymous users, login page renders with CSRF, all five security headers
present, and the operator logged in via browser at `http://192.168.2.140`
and saw the dashboard correctly reporting 2 blockers (no FB/TikTok
accounts on this fresh machine).

#### Four real bugs found — none caught by the local rehearsal

| Bug | Symptom | Fix |
|---|---|---|
| `tools/doctor.py` crashed with `UnicodeEncodeError` | Fresh Windows console is cp1252; the Vietnamese report could not be printed. **The diagnostic tool died exactly when needed.** | `_force_utf8_output()` reconfigures stdout/stderr to UTF-8 with `errors="replace"` |
| `install.ps1` never created `data\config.json` | Service ran but `/health/ready` returned 503 forever with no obvious cause | Seeds from `config.example.json`; never overwrites an existing config |
| `backup.ps1` aborted `update.ps1` | Empty data dir on a fresh install was treated as an error and threw, killing the whole update | An empty data dir is a legitimate state -> warn and `exit 0` |
| `update.ps1` did not self-heal a missing config | An install made by the older installer stayed stuck at 503 after updating | Same provisioning logic added to update |

Lesson recorded: the P8 "clean-install rehearsal" ran on the dev machine,
which already had a UTF-8 console and a populated `data/`. Neither
condition holds on a fresh server, which is why all four bugs survived it.
A future rehearsal should use an empty data directory and a legacy
codepage.

Also fixed a self-inflicted PowerShell trap: passing Python code via
`python -c "..."` from PowerShell **silently strips the double quotes**,
so `r"C:\path"` reached Python as `rC:\path` and raised SyntaxError. All
remote Python is now executed from `.py` files, never inline. The same
applies to remote PowerShell: scripts are `scp`'d and executed as files
rather than passed through nested quoting.

- Tests run:
  - `python -m pytest tests -q` -> **1164 passed**, 1 skipped, 23 subtests.
    (1153 prior + 11 new in `tests/test_46_deploy_realworld_fixes.py`.)
  - `python tools/scan_source_secrets.py` -> PASS, 329 files, 0 findings.
  - `update.ps1` executed for real on the VM: backup -> stop -> preserve
    `app.previous` -> extract -> reinstall deps -> start -> health check.
- Security/data impact: `LTT_SESSION_SECRET` and
  `LTT_TOKEN_ENCRYPTION_KEY` were generated **on the VM** and never
  transited chat. The admin password was set by the operator through an
  interactive script that hashes locally; its plaintext was never seen by
  anyone else and is not recoverable — resetting means re-running
  `set-admin-password.ps1`.
- Known issues:
  - FB/TikTok accounts not connected on the VM (expected — tokens are
    machine-bound and were never portable; `LTT_TOKEN_ENCRYPTION_KEY` is
    now set, so tokens saved from here on **are** portable).
  - Windows license is Evaluation, 135 days.
  - `LTT_ENV` still `development`.
- Next actions:
  1. **Operator:** port-forward 80/443 -> 192.168.2.140 on the VNPT modem,
     then Claude tests external reachability (cannot be tested from inside
     the LAN — hairpin NAT gives false positives).
  2. If ports are open: DuckDNS hostname + DDNS updater service + CNAME
     `app` -> `<host>.duckdns.org` at inet.vn + Caddy with the real domain
     + switch to `LTT_ENV=production`. If blocked: fall back to Cloudflare
     Tunnel.
  3. Connect Facebook/TikTok accounts on the VM so the bot can publish.

### 2026-07-30 — Web feature audit, hardening, P8 release build, P9 deploy package

- Goal: user asked to keep building until `app.lttstudios.com` serves the
  dashboard, and to check the web features first.
- Current phase: P8 PARTIAL, P9 PARTIAL (package built and locally
  rehearsed; never run against a real VPS — no access).
- Status: everything buildable without VPS credentials is done. The
  remaining steps are operator actions, documented in
  `docs/DEPLOY_APP_LTTSTUDIOS.md`.

#### Web feature audit — two real security gaps found and fixed

1. **API docs were public.** `/docs`, `/redoc` and `/openapi.json`
   returned 200 with no authentication, enumerating every route and
   parameter — free reconnaissance on a public domain. Now disabled
   outside development (`docs_url=None` etc.); verified 404 in
   `local-server-test` and `production`, still 200 in `development`.
2. **No security response headers at all.** Added CSP (with
   `frame-ancestors 'none'`, `form-action 'self'`), `X-Frame-Options`,
   `X-Content-Type-Options`, `Referrer-Policy`, and HSTS — HSTS only
   outside development, since a cached HSTS entry for localhost is
   painful to undo.

Checked and found already correct: every application route redirects
anonymous users to `/login`; health endpoints are intentionally open for
the proxy; the session cookie carries `httponly; secure; samesite=lax`.

#### Infrastructure finding

`lttstudios.com` is on inet.vn shared WordPress hosting (DirectAdmin),
which cannot run a long-lived Python process. `app.lttstudios.com`
therefore needs a **separate Windows VPS**; the existing site is untouched.
This is recorded at the top of the deploy runbook so it is not
rediscovered later.

#### P8 — release artifact (built and rehearsed for real)

- `tools/build_release.py`: collects source + deploy scripts, excludes
  `data/`, `secrets/`, `logs/`, `temp_videos/`, `*.enc`, `*.db`,
  `config.json`, caches and build output; **runs the repo's own secret
  scanner over exactly what will ship and aborts on any finding**; refuses
  to build if a required entry is missing; prints SHA-256.
- Real build: 385 files, 23.5 MB, 0 secret findings, no sensitive entries.
- **Clean-install rehearsal actually performed**: extracted to a staging
  directory, created a *fresh* venv (not the dev `.venv`), installed from
  `requirements.txt` + `requirements-server.txt`, started uvicorn with
  `LTT_ENV=production` and an isolated `LTT_DATA_DIR`. Result:
  `/health/ready` → `{"status":"ready","environment":"production"}`,
  `/docs` → 404, login → 303, all six authenticated pages → 200, and all
  five security headers present including HSTS. Staging removed afterwards.

#### P9 — Windows deployment package

`deploy/windows/`: `install.ps1`, `update.ps1`, `rollback.ps1`,
`backup.ps1`, `restore.ps1`, `set-service-env.ps1`, `Caddyfile.example`.
Design points worth remembering:

- Runtime data/secrets/logs live under `C:\LTTPlatform\` *outside* the
  release directory, so `update.ps1` replaces code without touching them.
- `update.ps1` backs up data first, keeps the old release at
  `app.previous`, and verifies `/health/ready` — failing that, it tells
  the operator to run `rollback.ps1`.
- `rollback.ps1` deliberately does **not** roll back data (that would
  discard real publishing history) and keeps the bad release at
  `app.failed` for post-mortem.
- `restore.ps1` defaults to a **rehearsal** into an isolated directory;
  `-Live` requires typing `RESTORE` and takes a safety backup first.
- Secrets are loaded into the service via NSSM `AppEnvironmentExtra` from
  a protected `secrets\app.env`, never on the service command line (which
  any user can read in Task Manager). `set-service-env.ps1` prints
  variable *names* only.

#### Bug found and fixed while building the package

`rollback.ps1` failed to parse under Windows PowerShell 5.1: 5.1 reads a
`.ps1` as the system ANSI codepage unless it has a UTF-8 BOM, so an
em-dash in a message string became mojibake and produced "The string is
missing the terminator". A deploy script that dies halfway through an
install is worse than none, so all six scripts were normalised to pure
ASCII and `tests/test_45_deploy_scripts.py` now enforces that, plus
`$ErrorActionPreference = 'Stop'` in every script and no secret values
shipped.

- Tests run:
  - `python -m pytest tests -q` → **1153 passed**, 1 skipped, 23 subtests,
    273s. (1089 prior + 64 new across `test_43_web_hardening.py` (14),
    `test_44_release_build.py` (29), `test_45_deploy_scripts.py` (21).)
  - `python tools/scan_source_secrets.py` → PASS, 328 files, 77,203
    lines, 0 findings.
  - PowerShell AST parse check on all six deploy scripts → all OK.
  - Real-server checks described above; all temporary servers stopped and
    all staging/temp artifacts deleted. `data/workers.json` still does not
    exist on the user's install and `data/session_locks/` is empty.
- Security/data impact: two exposure gaps closed. No secret value written
  anywhere; `app.env` ships with empty values and a test enforces it.
- Known issues: unchanged — B1/B2 (token stores undecryptable) still block
  real publishing, on this machine and on any future VPS until accounts
  are reconnected there.
- Next actions:
  1. **User:** follow `docs/DEPLOY_APP_LTTSTUDIOS.md` — VPS prep, DNS A
     record for `app`, firewall 80/443, `install.ps1`, fill `app.env`,
     Caddy. That is what makes `https://app.lttstudios.com` live.
  2. **User:** reconnect Facebook/TikTok accounts **on the VPS** (tokens
     are machine-bound; setting `LTT_TOKEN_ENCRYPTION_KEY` first makes
     them portable from then on).
  3. Remaining product work: manual publish form and browser OAuth
     (P4/P5 write slice), then P7 observability.

### 2026-07-30 — P4/P5/P6: web control plane connected to the app

- Goal: user asked to keep implementing phases until the web can drive the
  app through the architecture we built. Achieved for the control-plane
  loop; manual publishing forms and web OAuth remain (see below).
- Current phase: P4/P5 PARTIAL (read-only), P6 PARTIAL (start/stop/status).
- Status: partial by design — each module's read/control path is done and
  verified; the write paths (publish, OAuth connect) are the next slice.

#### What now works end-to-end

Verified on a **real uvicorn server** driven by `curl`, not just TestClient:

1. Login → dashboard, which surfaces live blockers from `tools/doctor.py`.
2. `/facebook` and `/tiktok` render real account/page health. Against the
   live install they correctly show "Không đọc được kho token" — the real
   B1/B2 state — with the reconnect hint, instead of a misleading empty list.
3. `/workers` reads the **same** `data/workers.json` the desktop Sheet tab
   writes (PA-5), so the web sees the operator's real configuration.
4. `POST /workers/start` → `WorkerApplication` → a real `SheetRunner`
   started, logged `Sheet Runner bắt đầu — tab: SmokeTab`, and its failure
   was captured and returned through `GET /api/workers/status`. That is
   the full path: web → service layer → core, with logs flowing back.
5. **Ownership lock verified live:** with a simulated desktop process
   holding the lock, `POST /workers/start` returned **HTTP 409** naming
   the holding pid — the AGENTS.md "desktop and server must never process
   the same account" invariant, proven rather than assumed.

Safety note on method: the start/stop smoke test used an isolated
`LTT_DATA_DIR` and a **fake sheet id** with no Google credentials, so the
worker failed fast at connect and no real spreadsheet was contacted. The
user's `data/` was left untouched (`data/workers.json` still does not
exist there).

#### Files added

- `server/services/accounts.py` — converts token-store objects into view
  dataclasses that structurally cannot carry token material.
- `server/services/worker_control.py` — process-wide `WorkerController`
  (ADR-005 single orchestrator), bounded log buffer, start/stop/snapshot.
- `server/routes/accounts.py`, `server/routes/workers.py`.
- `server/templates/accounts.html`, `workers.html`; `dashboard.html`
  rewritten into real navigation + blocker summary.
- `tests/test_41_p456_web_modules.py` (20 tests),
  `tests/test_42_session_lock_runtime_path.py` (5 tests).

#### Bug found during the real-server smoke test (fixed)

`core/session_lock.py` used a module-level, **CWD-relative**
`os.path.join("data", "session_locks")`. A server started with
`LTT_DATA_DIR` pointing elsewhere would therefore write its locks in a
different directory from the desktop app — silently disabling the very
mutual exclusion that prevents duplicate publishing. Now resolved through
`core.runtime_paths` at construction time (not import), with an explicit
`lock_dir` override still winning. This was a latent P2 gap: the runtime
path boundary had never been applied to this module.

Also added `data/session_locks/` and `data/workers.json` to `.gitignore` —
both are machine-specific runtime state and were previously untracked but
not ignored. A stale lock file left behind by the earlier audit run was
removed.

- Tests run:
  - `python -m pytest tests/test_41_p456_web_modules.py -q` → 20 passed.
  - `python -m pytest tests/test_42_session_lock_runtime_path.py -q` → 5 passed.
  - `python -m pytest tests -q` → **1089 passed**, 1 skipped, 23 subtests,
    269s. (1064 prior + 25 new; no regressions.)
  - `python tests/gui_smoke_validator.py` → PASS 9/9 (re-run because
    `session_lock.py` is on the desktop path too).
  - `python tools/scan_source_secrets.py` → PASS, 317 files, 75,913
    lines, 0 findings.
- Security/data impact: the no-token-leak property is enforced
  structurally (view dataclasses lack the fields) and asserted through
  rendered HTML in tests. All state-changing worker routes are POST +
  CSRF-protected and require login.
- Known issues: unchanged — B1/B2 (account re-authorization) still block
  real publishing; nothing in this session could fix that.
- Rollback: delete `server/services/`, `server/routes/{accounts,workers}.py`,
  the two new templates and two new test files; revert
  `core/session_lock.py`, `server/app.py`, `server/routes/dashboard.py`,
  `server/templates/dashboard.html`, `.gitignore`.
- Next actions:
  1. **User:** reconnect FB/TikTok accounts, then `python tools/doctor.py
     --check-sheet` — the web pages will then show real accounts and the
     worker can actually publish.
  2. P4/P5 write slice: manual publish form → `UploadEngine` through a
     service, with idempotency keys and double-submit protection.
  3. Server-side OAuth start/callback with state validation, so accounts
     can be connected from the browser instead of only the desktop app.

### 2026-07-30 — Audit, PA runnability remediation, P3 completion

- Goal: user asked for a real audit proving the bot runs before building
  more, then a detailed plan, then implementation of the remaining items.
- Current phase: audit → PA (new) COMPLETE → P3 COMPLETE.
- Status: completed for PA/P3; two blockers remain that only the user can
  clear (account re-authorization).

#### Audit outcome (full detail in `docs/AUDIT_REPORT.md`)

Automated checks all passed (1021 tests, GUI smoke 9/9, secret scan clean,
config valid, Sheets reachable, dashboard serving) — **and the bot still
could not publish.** The test suite mocks out exactly the state that was
broken. Findings:

- **B1/B2 (CRITICAL, user action required):** `data/tokens.enc` (27,704
  bytes of real data) and `data/tiktok_tokens.enc` are valid Fernet blobs
  that fail to decrypt under every candidate key (registry MachineGuid
  default/64-bit view, and the `node_system_machine` fallback). The P0
  recovery backup is byte-identical, so it is not an older decryptable
  copy. These were encrypted under a machine identity that no longer
  exists here. **Unrecoverable by code.** Accounts must be reconnected.
- **B3 (HIGH):** 0 of 26 sheet tabs matched the configured column mapping.
  The mandatory `col_schedule_time` was `schedule_time_fb_dai` while the
  configured default tab actually uses `schedule_time`; `col_error`
  (`error_message_dai`) exists in no tab, silently disabling error
  write-back.
- **D1:** `gui/sheet_runner_tab.py` called `client.worksheet` — an
  attribute `SheetClient` does not have (gspread leftover), so the queue
  preview panel always failed.
- **D2:** `TokenStore._load()` swallowed decrypt failure then swallowed
  the JSON error, making an undecryptable file look identical to "no
  accounts connected" — this is what hid B1.
- **D3:** the worker list lived only in GUI memory, never persisted.

Note on method: running `worker_main.py` against the real config during
the audit connected to the live Google Sheet. It failed at the **read**
step (`get_next_pending_row`) before any `mark_running()`, so **no sheet
data was modified**; the process was stopped immediately afterwards.

#### PA — runnability remediation (all implemented this session)

- **PA-1** `core/token_store.py` + `core/tiktok/token_store.py`: `_load()`
  now distinguishes absent / unreadable / readable and exposes
  `load_error` + `is_unreadable`. The live install now reports the real
  reason instead of "0 accounts". (9 tests)
- **PA-2** `utils/sheet_client.py`: added `get_all_rows()` and
  `get_header_names()` public APIs; `gui/sheet_runner_tab.py` uses them
  instead of the non-existent `client.worksheet`. Also fixed an
  off-by-zero in the same block (`if status_idx` treated column A as
  missing).
- **PA-3** `core/preflight.py`: config↔sheet column validator separating
  mandatory (ERROR) from important (WARNING) columns, with a
  `difflib`-based "did you mean" that correctly proposes `schedule_time`
  for `schedule_time_fb_dai` and `error_message` for `error_message_dai`.
  (9 tests)
- **PA-4** `tools/doctor.py`: one command reproducing the whole audit —
  environment, config, token readability, worker list, sheet connectivity,
  per-tab column preflight. Non-zero exit on a blocker. Verified
  end-to-end against the live install and the real spreadsheet.
- **PA-5** `core/worker_store.py`: atomic, schema-versioned,
  per-platform-namespaced `data/workers.json`. Wired into the GUI (saves
  on add/remove, restores on init) and into `worker_main.py`. (18 tests)

**Deliberate behavior change:** `worker_main.py` no longer falls back to
guessing a worker from the legacy `sheet_tab`/`sheet_id` config keys — the
audit proved that guess targeted a tab whose columns did not match,
producing a run that connected and then failed mid-flight. It now exits
with code 3 and an actionable message. Two P1 tests asserting the old
fallback were updated (documented decision, per AGENTS.md), and given
temp-file isolation so they no longer read the developer's real
`data/workers.json`.

#### PB — P3 completion

- Styled HTML error pages (`server/templates/error.html`) replacing the
  JSON-only 404, while `/health/*` deliberately keeps returning JSON for
  machine probes, and `require_login`'s 303 redirect still passes through.
- `/status` page rendering the doctor report in the browser, reusing
  `tools/doctor.py` so CLI and dashboard cannot disagree. Sheet checks are
  opt-in per request (tested that they do not run by default).
- `docs/SECURITY_CHECKLIST.md` — every control with a verification
  command, and honest "Deferred"/"Not yet verified" sections.

**Bug found and fixed while testing:** the login rate limiter was
module-level state shared by every app instance in a process, so a test
that exhausted the limit silently locked out later tests. Moved to
`app.state.login_rate_limiter` — a correctness fix (two app instances
should never share login counters), not a test workaround.

- Tests run:
  - `python -m pytest tests -q` → **1064 passed**, 1 skipped, 23 subtests,
    260s. (1021 at audit start + 43 new; no regressions.)
  - `python tests/gui_smoke_validator.py` → PASS, 9/9 tabs, 0 errors
    (re-run after the `sheet_runner_tab.py` changes).
  - `python tools/scan_source_secrets.py` → PASS, 308 files, 74,716
    lines, 0 findings. (Two of my own test fixtures initially tripped the
    FB-token rule; fixed by assembling them at runtime per the repo's
    existing `test_33_secret_scanner` convention rather than weakening the
    scanner.)
  - Real `uvicorn` smoke: `/health/live` 200 JSON, `/nope` 404 styled
    HTML, `/status` 303 → `/login` when anonymous.
  - `python tools/doctor.py --check-sheet` against the live spreadsheet,
    using a temp `LTT_DATA_DIR` so the user's real state was untouched.
- Security/data impact: no secret value read, printed, or stored. Two new
  secret *names* are referenced by code (`LTT_TOKEN_ENCRYPTION_KEY`,
  `LTT_TOKEN_ENCRYPTION_KEY_FILE` — from P2). No user runtime state was
  modified: `data/workers.json` was not created on the user's install.
- Rollback: new files (`core/preflight.py`, `core/worker_store.py`,
  `tools/doctor.py`, `server/routes/status.py`, `server/templates/{error,status}.html`,
  4 test files, 3 docs) can be deleted. Modified files
  (`core/token_store.py`, `core/tiktok/token_store.py`,
  `utils/sheet_client.py`, `gui/sheet_runner_tab.py`, `worker_main.py`,
  `server/app.py`, `server/routes/auth.py`, `tests/test_34…`,
  `tests/test_37…`) revert independently.
- Next actions:
  1. **User:** reconnect Facebook + TikTok accounts (clears B1/B2), then
     run `python tools/doctor.py --check-sheet` to confirm green.
  2. **User:** decide the correct `col_schedule_time` / `col_error`
     mapping per tab (B3) — doctor now names the exact suggestion.
  3. Start P4 (Facebook web module) per `docs/MVP_COMPLETION_PLAN.md`
     section PC — read-only account/page list first, since PA-1 now makes
     an empty list distinguishable from a broken one.

### 2026-07-29 — P3 first slice: FastAPI dashboard shell, auth, health API

- Goal: continue directly into P3 after closing P2, per user instruction
  ("tiếp tục quy trình") to keep implementing phases continuously with a
  pass/fail test check at each boundary, toward an eventual MVP.
  Deployment phases (P9/P10) remain gated on separate explicit
  authorization.
- Current phase: P3, in progress (foundation slice done; error-page
  polish, formal accessibility audit, and a standalone security-checklist
  document remain — see "Deferred" above).
- Status: partial.
- Files changed: `server/` (new package: `app.py`, `run.py`, `settings.py`,
  `auth/{password_hashing,csrf,rate_limit,session}.py`,
  `routes/{health,auth,dashboard}.py`, `templates/{base,login,dashboard}.html`),
  `tools/hash_admin_password.py` (new), `requirements-server.txt` (new),
  `tests/test_37_p3_web_foundation.py` (new, 20 tests).
- Behavior changed: none for existing entry points — `main.py` and the
  GUI are untouched. This is a wholly new, currently-unused-by-anything-else
  surface.
- Decisions: see "Bug caught and fixed" and "Known limitation" above for
  the lifespan/TestClient fix and the accepted client-side-session-store
  trade-off.
- Tests run:
  - `python -m pytest tests/test_37_p3_web_foundation.py -q` → 20 passed
    (including a redirect chain through login → dashboard → logout →
    redirect-to-login-again, and a real rate-limit trip after 5 failures).
  - `python -m pytest tests -q` → 1021 passed, 1 skipped, 23 subtests,
    237.41s. (1001 prior + 20 new; no regressions.)
  - `python tools/scan_source_secrets.py` → PASS, 296 files, 72,793 lines,
    0 findings.
  - `python -m py_compile` on every new `.py` file → PASS.
  - **Real process smoke test** (not just `TestClient`): started
    `python -m uvicorn server.run:app --host 127.0.0.1 --port 8791` with
    `LTT_ENV=development`, then `curl`'d `/health/live` (200,
    `{"status":"ok"}`) and `/login` (200, real rendered HTML) from a
    separate shell, then stopped the process by PID. This is the closest
    this session came to P3's "Dashboard works at localhost" exit
    criterion without a real browser.
- Security/data impact: no secret values added anywhere. New secret
  *names* referenced by code: `LTT_SESSION_SECRET`, `LTT_ADMIN_USERNAME`,
  `LTT_ADMIN_PASSWORD_HASH` — none has a value in this repository, and
  `tools/hash_admin_password.py` is specifically designed so an operator
  never has to write the plaintext password anywhere.
- Known issues: unchanged from prior sessions.
- Rollback: delete `server/`, `tools/hash_admin_password.py`,
  `requirements-server.txt`, `tests/test_37_p3_web_foundation.py`. Nothing
  pre-existing was modified.
- Next actions:
  1. Continue P3 to a fuller close: styled error pages, and — once a
     browser-automation tool is available in-session — an actual
     multi-width accessibility/responsive pass.
  2. Or move to P4 (Facebook web module) if the user prioritizes visible
     feature progress over finishing every P3 checklist item first; either
     is defensible, revisit based on what's asked next.
  3. Decide whether `worker_main.py`/GUI settings cutover to
     `core.settings`/token-key override (deferred since P2) should happen
     before or after P4/P5, since P4/P5 will need the same settings
     boundary for their own OAuth callback handling.

### 2026-07-29 — P2 close-out: token-key migration, schema version, retention policy

- Goal: close the remaining P2 gaps identified in the prior slice (token
  migration decision, atomic writes verification, schema/version
  validation, data retention policy), continuing without per-phase
  confirmation per user instruction, with a full test pass before marking
  P2 complete.
- Current phase: P2 → COMPLETE this session; P3 opened next.
- Status: completed.
- Files changed:
  - `core/token_store.py` — added `_external_key_material()` /
    refactored `_derive_key(salt=...)` (ADR-013).
  - `core/tiktok/token_store.py` — now delegates to the shared
    `_derive_key()` instead of duplicating machine-key derivation.
  - `core/settings.py` — added `CONFIG_SCHEMA_VERSION` +
    `_check_schema_version()`.
  - `config.example.json` — added `_schema_version: 1`.
  - `docs/DATA_RETENTION_POLICY.md` (new).
  - `tests/test_36_p2_token_key_migration.py` (new, 6 tests).
  - `tests/test_35_p2_runtime_boundary.py` — added 4 schema-version tests
    (now 20 tests total in that file).
- Behavior changed: token-store key derivation now checks
  `LTT_TOKEN_ENCRYPTION_KEY`/`LTT_TOKEN_ENCRYPTION_KEY_FILE` before falling
  back to machine-bound derivation — verified byte-for-byte identical to
  the prior behavior when neither is set (existing desktop installs and
  encrypted token files are unaffected). `core.settings.load_settings()`
  now also rejects a config declaring a newer `_schema_version` than this
  build supports; configs with no such key (all existing configs) are
  unaffected.
- Decisions: see ADR-013 in the Architecture decisions table above for the
  token-key decision and its rationale. ACL guidance and the two
  retention gaps were explicitly deferred (see "Deferred out of P2").
- Tests run:
  - `python -m pytest tests/test_35_p2_runtime_boundary.py
    tests/test_36_p2_token_key_migration.py -q` → 26 passed.
  - `python -m pytest tests -q -k token` → 45 passed (pre-existing token
    tests, confirming no regression from the `_derive_key` refactor).
  - `python -m pytest tests -q` → 1001 passed, 1 skipped, 23 subtests,
    224.34s. (997 prior + 10 new that weren't already counted — note the
    prior session's total already included the first 6 of these from an
    intermediate run; final authoritative count is this 1001.)
  - `python tools/scan_source_secrets.py` → PASS, 277 files, 71,867 lines,
    0 findings.
  - `python -m py_compile core/token_store.py core/tiktok/token_store.py
    core/settings.py tests/test_36_p2_token_key_migration.py
    tests/test_35_p2_runtime_boundary.py` → PASS.
- Security/data impact: `LTT_TOKEN_ENCRYPTION_KEY`/`_FILE` are new secret
  *names* now referenced by code — no value for either exists anywhere in
  this repository, docs, or logs. When an operator eventually sets one on
  the VPS, rotating it would re-encrypt-orphan any tokens saved under the
  old key (expected Fernet behavior) — noted here so a future rotation
  isn't a surprise, not yet built into a rotation runbook (P9/P10 concern).
- Known issues: unchanged from prior sessions (FB/TikTok token stores
  report zero loadable accounts locally — expected, no external key is
  set for local desktop use).
- Rollback: revert the files listed above; `core/tiktok/token_store.py`'s
  change is a pure refactor (behavior-preserving) so reverting either file
  independently is also safe.
- Next actions:
  1. Start P3 (web platform foundation): FastAPI app factory,
     `/health/live` + `/health/ready`, dashboard shell, authentication —
     per `WEB_PLATFORM_PLAN.md` P3 task list.
  2. When P9 (VPS deployment) actually begins, generate and provision the
     real `LTT_TOKEN_ENCRYPTION_KEY` value into the protected production
     secrets location — out of scope until then.
  3. Consider folding the two retention gaps into whichever P3/P6 work
     first touches `MaintenanceDaemon` again, rather than a standalone
     change.

### 2026-07-29 — P2 first slice: runtime paths + environment + example config

- Goal: continue directly into P2 after closing P1, per user instruction to
  implement phases continuously with a pass/fail check at each boundary,
  toward an eventual MVP. Deployment phases (P9/P10) remain gated on
  separate explicit authorization — not affected by this instruction.
- Current phase: P2, in progress (path/environment half done; secrets half
  — token migration, ACL, atomic writes, retention — not started).
- Status: partial.
- Files changed:
  - `core/runtime_paths.py` (new)
  - `core/settings.py` (new)
  - `config.example.json` (new, project root)
  - `tests/test_35_p2_runtime_boundary.py` (new, 16 tests)
- Behavior changed: none for existing entry points. `main.py`,
  `worker_main.py`, and the GUI still load `data/config.json` the same way
  they did before this session.
- Decisions:
  - Path resolution defaults are computed from `core/runtime_paths.py`'s
    own file location, not `os.getcwd()`, so the "non-project working
    directory" required test is satisfied by construction rather than by
    special-casing.
  - `config.example.json` was generated by replacing string-valued keys
    matching a secret/ID-shaped name pattern (`secret`, `token`,
    `password`, `credentials_path`, `_id$`, `relay_url`, `redirect_uri`,
    `_key$`) with `REPLACE_ME_<key>`, while explicitly keeping known-benign
    keys (Sheet column-header names like `col_fb_video_id`, the Graph API
    version string, public legal URLs) as real defaults so the template
    stays directly usable. Verified against the actual scanner rules
    (`_scan_line`) line-by-line, not just trusted by construction.
  - Left `worker_main.py` on its existing bare `json.load` rather than
    switching it to `core.settings.load_settings()` in the same session
    that introduced `load_settings()` — cutting an entry point over
    deserves its own test pass verifying the error-path behavior didn't
    regress, not a same-diff swap.
- Tests run:
  - `python -m pytest tests/test_35_p2_runtime_boundary.py -q` → 16 passed.
  - `python -m pytest tests -q` → 991 passed, 1 skipped, 23 subtests,
    235.84s. (975 prior + 16 new; no regressions.)
  - `python tools/scan_source_secrets.py` → PASS, 275 files, 71,489 lines,
    0 findings (includes the new `config.example.json`).
  - `python -m py_compile core/runtime_paths.py core/settings.py
    tests/test_35_p2_runtime_boundary.py` → PASS.
  - `git status --short` reviewed before/after — only the intended new
    files plus this memory file are touched; nothing pre-existing modified.
- Security/data impact: none. `config.example.json` contains no real
  credential, token, ID, or URL value — verified both by generation logic
  and by direct scanner-rule execution against its contents.
- Known issues: unchanged from prior sessions.
- Rollback: delete the four new files listed above; nothing pre-existing
  was modified.
- Next actions:
  1. Decide and document the token-encryption migration approach (P2
     required decision, currently blocking P2's exit gate).
  2. Add atomic configuration writes + schema/version validation, most
     likely as a small `core/config_writer.py` used by new code first
     (same additive-first pattern as this slice) before touching
     `gui/settings_tab.py`'s existing save path.
  3. Define data retention rules for logs/audit/cache/completed jobs, then
     re-assess whether P2's remaining scope is small enough to close in one
     more slice or should hand off to P3 (web foundation) with P2 tracked
     as "mostly done, secrets-hardening carried forward."

### 2026-07-29 — P1 hardening and close-out

- Goal: close the gaps found while self-reviewing the first P1 slice before
  marking the phase complete, per user instruction to keep implementing
  phases continuously with a pass/fail check at each phase boundary
  (production deployment phases P9/P10 still require separate explicit
  authorization; that constraint is unchanged).
- Current phase: P1 → COMPLETE this session; P2 opened next.
- Status: completed.
- Files changed: `core/worker_app.py`, `tests/test_34_p1_headless_worker.py`.
- Behavior changed (all within code added this session, nothing pre-existing
  touched):
  - Fixed a reentrant-lock deadlock: `_notify_stopped_once` used to share
    `start()`/`stop()`'s lock, so a runner that finished before `start()`
    returned (fast stub, or a real crash) would deadlock calling the stop
    callback while `start()` still held that same lock. Split into
    `_state_lock` (start/stop transitions) and `_notify_lock` (stopped-once
    flag) so they can never contend.
  - Replaced the single-worker path's use of `core.sheet_runner.SheetRunnerThread`
    with a local `_GuardedRunnerThread` that guarantees the stop/lock-release
    callback fires exactly once even if the runner raises — closing a lock
    leak that would otherwise be permanent (until manual deletion) if a
    single-worker runner crashed.
- Tests added: crash-releases-lock test, worker_main end-to-end wiring test
  (no network), worker_main ownership-conflict exit-code test.
- Tests run:
  - `python -m pytest tests/test_34_p1_headless_worker.py -q` → 6 passed,
    twice in a row with no leftover files under `data/session_locks/`.
  - `python -m pytest tests -q` → 975 passed, 1 skipped, 23 subtests,
    234.55s. No regressions.
- Decisions: see "Deferred out of P1" above — GUI rewiring and a live
  credentialed console run are explicitly out of scope for this phase, not
  silently skipped.
- Security/data impact: none. No secret values touched.
- Known issues: unchanged from prior session (FB/TikTok token stores report
  zero loadable accounts; unrelated to this change).
- Rollback: revert `core/worker_app.py` and
  `tests/test_34_p1_headless_worker.py` to their previous-session versions,
  or delete both plus `worker_main.py` entirely (P1 is additive-only —
  nothing pre-existing was modified across the whole phase).
- Next actions:
  1. Start P2 (runtime configuration, data, and security boundary) per
     `WEB_PLATFORM_PLAN.md` — environment profiles, secret/non-secret
     settings separation, path resolution service.
  2. Decide and document the token-encryption migration approach
     (re-OAuth vs. external key) before any VPS-facing work — P2 required
     task, currently undecided.
  3. Revisit GUI→WorkerApplication rewiring once P2/P3 make the shared
     lifecycle valuable to the desktop app too (avoids two lifecycle
     implementations diverging).

### 2026-07-29 — P1 first slice: WorkerApplication + worker_main.py

- Goal: implement the P1 headless boundary's core deliverables — a lifecycle
  wrapper usable without importing GUI, a console entry point, and a
  cross-mode ownership lock, per the memory's "Immediate next actions" and
  `WEB_PLATFORM_PLAN.md` P1 task list.
- Current phase: P1.
- Status: partial (first slice; see remaining P1 tasks above).
- Files changed:
  - `core/worker_app.py` (new) — `WorkerApplication` class wrapping
    `SheetRunnerThread` (1 worker) / `ConcurrentRunner` (N workers) behind
    one `start()`/`stop()`/`status()`/`wait_stopped()` interface.
  - `worker_main.py` (new) — headless CLI entry point; loads
    `data/config.json`, builds a legacy single-worker default from
    `sheet_tab`/`sheet_id` (or a `--workers` JSON file for multiple
    workers), wires SIGINT/SIGTERM to `WorkerApplication.stop()`.
  - `tests/test_34_p1_headless_worker.py` (new) — 3 tests: worker_main
    import boundary (spawns a subprocess and asserts no `customtkinter`/
    `gui.*` in `sys.modules`), start/stop idempotency with a stubbed
    runner, and ownership-lock conflict rejection.
- Behavior changed: no desktop behavior changed. `gui/sheet_runner_tab.py`
  still branches directly between `SheetRunnerThread`/`ConcurrentRunner`
  itself — it was intentionally left unwired to `WorkerApplication` this
  session to avoid a GUI regression pass in the same change as new headless
  code. `core/sheet_runner.py`'s existing per-row `SessionLock` behavior is
  unchanged.
- Decisions:
  - `WorkerApplication` acquires a `SessionLock` per worker's target
    account (fallback: page_id → page → tab) for the *whole run*, in
    addition to the existing per-row lock inside `SheetRunner._tick()`.
    Reason: the per-row lock only fires once a job is picked up, so two
    runners aimed at the same account could both sit "connected" and only
    collide once a row appears (or never, if the sheet stays empty). The
    whole-run lock makes the second runner fail at `start()` instead.
  - `worker_main.py` defaults to a single legacy worker built from the
    existing top-level `sheet_tab`/`sheet_id` config keys (the same
    fallback the desktop app already uses when only one sheet tab is
    configured) rather than inventing a new persisted worker-list schema —
    that belongs to P2 (runtime configuration boundary), not P1.
  - Real Google Sheets/Graph API calls were not exercised in tests;
    `WorkerApplication`'s tests stub `SheetRunner`/`SheetRunnerThread` via
    monkeypatch so the suite has no network/credential dependency.
- Tests run:
  - `python -m pytest tests/test_34_p1_headless_worker.py -q` → 3 passed
    (run twice back-to-back to confirm the ownership-lock test leaves no
    stale lock file in `data/session_locks/`).
  - `python -m pytest tests -q` → 972 passed, 1 skipped, 23 subtests
    passed, 258.46s. (969 prior + 3 new; no regressions.)
  - `python -m py_compile core/worker_app.py worker_main.py
    tests/test_34_p1_headless_worker.py` → PASS.
  - `python worker_main.py --help` → PASS, CLI parses and exits without
    touching config, network, or GUI. A real run against live
    Sheets/Graph credentials was intentionally NOT performed — that is a
    controlled live smoke test requiring explicit user authorization per
    `AGENTS.md`/plan P1 "Required tests".
- Security/data impact: none. No secret values read, printed, or stored.
  No new runtime data paths added beyond the existing
  `data/session_locks/` directory the ownership lock already used.
- Known issues: same as prior session (FB/TikTok token stores report zero
  loadable accounts; TikTok store reports a decryption fallback warning) —
  unrelated to this change, still unresolved.
- Rollback: delete `core/worker_app.py`, `worker_main.py`,
  `tests/test_34_p1_headless_worker.py`. No existing file was modified, so
  rollback is a pure deletion with no merge risk.
- Next actions:
  1. Add crash/graceful-shutdown tests for `WorkerApplication` beyond the
     idempotent start/stop case (P1 "Required tests": crash and graceful
     shutdown tests).
  2. Decide whether/when to wire `gui/sheet_runner_tab.py` through
     `WorkerApplication` (so desktop and future headless/server code share
     one lifecycle implementation) — requires a GUI regression pass before
     landing.
  3. Run one authorized, controlled `worker_main.py` console smoke test
     against real (non-production-risk) credentials to satisfy P1's exit
     criterion "Headless worker runs locally from a console."

### 2026-07-29 — P0 closure and P1 handoff

- Goal: close the secure desktop baseline after credential rotation.
- Current phase: P1 ready.
- Status: completed.
- Files changed:
  - `.gitignore`
  - `docs/PROJECT_MEMORY.md`
- Behavior changed: no publishing behavior changed.
- Tests/checks run:
  - `python tools/scan_source_secrets.py` → PASS, 268 files, 70,216 lines,
    zero findings.
  - Staged sensitive-path filter → PASS, no secret/runtime path staged.
  - `git diff --cached --check` → no blocking error; historical formatting
    warnings only.
  - Baseline commit `3eadb0d` created successfully.
- Decisions:
  - Ignore local Claude task state and machine-specific GUI/setup state.
  - Use repository-local Git identity `LTTStudio Baseline` with a `.local`
    address until the owner configures a personal Git identity.
- Security/data impact:
  - Owner confirmed the previously exposed App Secret was reset.
  - No credential value was stored.
  - Secret, token, database, log, and machine-local state remain outside Git.
- Known issues:
  - Facebook and TikTok stores currently report zero loadable accounts.
  - TikTok store reports a decryption fallback warning.
- Rollback:
  - Use baseline commit `3eadb0d` and the verified P0 recovery archive described
    in `docs/DESKTOP_BASELINE_RUNBOOK.md`.
- Next actions:
  1. Inventory the current runner lifecycle and GUI coupling.
  2. Specify the headless application boundary.
  3. Add P1 boundary tests before implementation.

### 2026-07-29 — P0 baseline execution

- Goal: establish a recoverable, secret-safe, tested desktop baseline.
- Current phase: P0.
- Status: partial; all local technical gates passed and credential rotation was
  confirmed by the owner. The clean baseline commit remains.
- Files materially changed:
  - `.gitignore`
  - `gui/main_window.py`
  - `gui/monitor_tab.py`
  - `utils/drive_downloader.py`
  - `tests/gui_smoke_validator.py`
  - `tests/test_03_sheet_client.py`
  - `tests/test_04_drive_downloader.py`
  - `tests/test_07_k1_metadata.py`
  - `tests/test_09_k6_retry.py`
  - `tests/test_10_k8_reels.py`
  - `tests/test_12_tiktok.py`
  - `tests/test_24_antispam_final.py`
  - `tests/test_33_secret_scanner.py`
  - `tools/scan_source_secrets.py`
  - `docs/DESKTOP_BASELINE_RUNBOOK.md`
- Behavior changed:
  - Monitor background refresh now hands results to the Tk thread through a
    queue instead of calling Tk from a worker thread.
  - Window shutdown cancels pending Tk callbacks before destroy.
  - Drive legacy confirmation-token parsing was extracted into a tested helper;
    download behavior is unchanged.
- Tests/checks run:
  - Backup archive listing/read/inclusion/exclusion verification → PASS.
  - `python tools/scan_source_secrets.py` → PASS, 268 files, 70,214 lines,
    zero findings.
  - `python -m pytest tests/test_33_secret_scanner.py -q` → 8 passed.
  - Eight formerly failing target files → 294 passed.
  - `python -m pytest tests -q` → 969 passed, 1 skipped, 23 subtests passed
    in 219.72 seconds.
  - `python tests/gui_smoke_validator.py` → PASS, 9/9 tabs, 0 captured errors.
  - Python compile check for changed runtime/scanner modules → PASS.
  - Git ignore verification for 12 sensitive/runtime paths → PASS.
  - Git candidate sensitive-path check → PASS, none present.
- Decisions:
  - Keep schedule-required behavior; update stale fixtures.
  - Keep validated video-cache behavior; update fixtures to valid MP4 headers.
  - Keep Facebook comments default-off; enable only in tests that assert them.
  - Keep operational config out of “default value” assertions.
  - Use a queue for thread-to-Tk monitor updates.
- Security/data impact:
  - Recovery backup contains sensitive runtime material and is kept outside the
    repository under `_recovery`.
  - Git repository initialized but no commit created.
  - Owner confirmed the previously exposed App Secret was reset; no credential
    value was stored.
  - No secret values were printed or added to documentation.
- Known issues:
  - TikTok token store reports decryption fallback and zero loadable accounts.
  - Facebook token store reports zero loadable accounts.
- Rollback:
  - Follow `docs/DESKTOP_BASELINE_RUNBOOK.md`.
- Next actions:
  1. Create and verify the baseline commit.
  2. Formally close P0 and open P1.
  3. Reconnect/verify operational accounts before real publishing.

### 2026-07-29 — Architecture and continuity bootstrap

- Clarified that development remains on the local machine and VPS deployment
  happens only after local release gates.
- Selected a dashboard-plus-background-worker product model.
- Goal: create a durable, security-conscious implementation plan and project
  memory for future sessions.
- Current phase: P0.
- Status: partial; P0 remains in progress.
- Files changed:
  - `AGENTS.md`
  - `.gitignore`
  - `docs/PROJECT_MEMORY.md`
  - `docs/WEB_PLATFORM_PLAN.md`
  - `docs/HANDOFF.md`
  - `docs/PROJECT_STATE.json`
- Behavior changed: no application runtime behavior changed.
- Tests/checks run:
  - `python -m pytest --collect-only -q` → PASS, 962 tests collected.
  - PowerShell `ConvertFrom-Json` validation → PASS for
    `docs/PROJECT_STATE.json`.
  - Documentation 32-character secret-pattern scan → PASS, no matches.
  - Markdown fence-balance/readability check → PASS.
  - `git check-ignore --no-index ...` → NOT RUN successfully because the
    project is not yet a Git repository; verification remains a P0 task.
- Decisions: local-first development, preserve desktop, shared publishing core,
  single initial orchestrator, external production secrets.
- Security/data impact: historical secret value redacted; ignore coverage
  expanded; no credential values added to new documentation.
- Known issues: credential rotation not verified; full test suite not run.
- Rollback: documentation and ignore-rule changes can be reverted from the
  pre-change filesystem backup once that backup is created; no runtime data was
  modified.
- Next actions:
  1. Create and verify the P0 recovery backup.
  2. Run the broader source-boundary secret scan and verify credential rotation.
  3. Run the full regression and GUI smoke suites before initializing Git.

## Required end-of-session update template

Copy this template to the top of the change log for every material session:

```markdown
### YYYY-MM-DD — Short session title

- Goal:
- Current phase:
- Status: completed | partial | blocked
- Files changed:
- Behavior changed:
- Tests run:
  - `exact command` → exact result
- Decisions:
- Security/data impact:
- Known issues:
- Rollback:
- Next actions:
  1.
  2.
  3.
```
