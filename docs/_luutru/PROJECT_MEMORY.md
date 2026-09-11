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
  `docs/_luutru/AUDIT_REPORT.md` B1/B2. Facebook and TikTok accounts must be
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

Detailed tasks and exit criteria are in `docs/_luutru/WEB_PLATFORM_PLAN.md`.

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
- Validated that `docs/_luutru/PROJECT_STATE.json` remains valid JSON.
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

- Goal: finish `docs/_luutru/WEB_PARITY_PLAN.md` W4-W6 and reach an MVP that runs
  entirely on the web.
- Current phase: W1-W6 complete.
- Status: completed (7 items remain that only the user can do - see
  `docs/_luutru/WEB_PARITY_PLAN.md` section 6).

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
  `docs/_luutru/DEPLOY_APP_LTTSTUDIOS.md`.

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
  1. **User:** follow `docs/_luutru/DEPLOY_APP_LTTSTUDIOS.md` — VPS prep, DNS A
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

#### Audit outcome (full detail in `docs/_luutru/AUDIT_REPORT.md`)

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
  3. Start P4 (Facebook web module) per `docs/_luutru/MVP_COMPLETION_PLAN.md`
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
     per `docs/_luutru/WEB_PLATFORM_PLAN.md` P3 task list.
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
     `docs/_luutru/WEB_PLATFORM_PLAN.md` — environment profiles, secret/non-secret
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
  `docs/_luutru/WEB_PLATFORM_PLAN.md` P1 task list.
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
  - `docs/_luutru/PROJECT_MEMORY.md`
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
  - `docs/_luutru/PROJECT_MEMORY.md`
  - `docs/_luutru/WEB_PLATFORM_PLAN.md`
  - `docs/_luutru/HANDOFF.md`
  - `docs/_luutru/PROJECT_STATE.json`
- Behavior changed: no application runtime behavior changed.
- Tests/checks run:
  - `python -m pytest --collect-only -q` → PASS, 962 tests collected.
  - PowerShell `ConvertFrom-Json` validation → PASS for
    `docs/_luutru/PROJECT_STATE.json`.
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

---

## 2026-08-21 — H37 khởi động (model tạo ảnh nội bộ, máy B RTX 3090)

- **Scope:** dựng model tạo ảnh chạy máy nhà thành **một provider nội bộ** (Q102),
  không phải một app. Kế hoạch 13 phase, mỗi phase có cổng chấm điểm ≥ 9/10.
- **Behavior changed:** chưa có gì trong `platform_core/` hay `apps/`. Mã mới nằm
  gọn trong `render_gateway/` (chạy trên máy B), `tools/cham_mu.py`, `bench/`.
- **Tests run:**
  - `python -m pytest tests/test_245_render_gateway.py -q` → **74 passed, 1 skipped**
  - `python -m pytest tests/test_247_cham_mu.py -q` → **17 passed**
  - `python tools\gate.py --quick` → **PASS 12/12**
- **Decisions:** Q102 (nền tảng) · D-001…D-016 (thi hành). D-003 → D-008 → D-009
  (model đích đổi hai lần, cả hai do bằng chứng). D-004 và D-005 bị D-010 sửa đổi.
- **Security/data impact:** máy B **không giữ bí mật nào** của nền tảng. ComfyUI vẫn
  chỉ nghe `127.0.0.1`. Chưa mở cổng nào ra LAN — G7 chưa chạy.
- **Known issues:**
  - G3 dở: baseline + thí nghiệm độ phân giải chưa chạy (máy B có việc trên GPU).
  - Template `edit`/`subject`/`structure` chưa viết.
  - `extra_model_paths.yaml` trên máy B: đã **thêm** khối `ltt_h37` (có sao lưu), và
    **BOM của tệp gốc bị lệnh ghi của tôi xoá** — ngoài dự định, đã xác minh vẫn đọc đúng.
- **Rollback:** xoá `render_gateway/`, `bench/`, `docs/ANH_NOI_BO/`, `tools/cham_mu.py`,
  hai tệp test; gỡ Q102 + mục H37. Trên máy B: khôi phục `extra_model_paths.yaml` từ
  `.truoc_h37_20260821.bak`, xoá `H:\LTT_MODELS\` và `E:\AI\ltt_render\`.
- **Next actions:**
  1. Chờ GPU máy B rảnh → chạy nốt G3 (baseline bf16 + thí nghiệm độ phân giải).
  2. G4 quét cấu hình chất lượng, **có thêm trục trần công suất 370 W ↔ 250 W**.
  3. G6b đối chứng mù với Gemini 3 Pro Image — **cổng chặn trước khi nối nền tảng**.

---

## 2026-08-22 — Nexus: vòng sửa lỗi sau khi chạy thật hai máy (đóng hết mục A+B)

- **Scope:** chủ sản phẩm chạy app trên hai máy cùng một tài khoản và báo 6 vấn đề;
  danh sách việc đầy đủ ở `docs/nexus/N7_DANH_SACH_VIEC.md`. Vòng này đóng **toàn bộ
  mục A (7 lỗi) và mục B (4 việc thiếu)**.
- **Behavior changed**
  - **Máy luôn hiện "tắt"** — client Model B chỉ gọi `/status`, không bao giờ gọi
    `/heartbeat`, nên `last_seen_at` mãi rỗng. `/status` nay ghi nhịp tim (`test_247`).
  - **`/nexus`** không còn là bảng điều khiển web-broker: nay là **trang giới thiệu
    công khai** (`server/templates/nexus_gioi_thieu.html`). Tám route cũ nằm sau cờ
    `LTT_NEXUS_WEB_BROKER`, **mặc định TẮT** → 404 kể cả gõ thẳng URL (`test_248`).
  - **`/may-cua-toi`** có bảng **Nhật ký truy cập**: ai vào máy nào, lúc nào, từ IP nào,
    kéo dài bao lâu (`test_245`, 13 test).
  - **SSO app ↔ web (B3):** `POST /nexus-agent/web-login` phát **vé một-lần** (là một
    hàng `sessions` sống 90 giây); app mở `/nexus-sso?ma=…&next=…`. Nút *Nạp credit*
    trong app không còn bắt gõ mật khẩu lần hai (`test_250`, 12 test). **Không thêm
    bảng, không migration.**
  - **Client 1.2.0 → 1.4.0:** tự cập nhật thật (tải → đối chiếu SHA-256 → cài im lặng),
    mục Giới thiệu mang đúng thương hiệu LTT, bỏ tab tài khoản thứ hai của RustDesk,
    bỏ câu xui dựng máy chủ riêng, dọn nốt chữ `rustdesk.com` ở bản mobile.
- **Tests run:** `tools\gate.py` (14 bước) · `test_245` 13 · `test_248` 10 · `test_250` 12
  · Rust unit test cho `ma_hoa_url`.
- **Bằng chứng chạy thật:** từ bản 1.2.0 đang chạy, bấm *Cập nhật ngay* → exe trong
  `C:\Program Files\LTTNexus` thay lúc 16:52:37, app tự bật lại lúc 16:52:41, mục Giới
  thiệu hiện 1.3.0. **Không có cửa sổ UAC.**
- **Ba cái bẫy đã dính, ghi lại để khỏi dính lần nữa**
  1. Phép đổi thương hiệu trong `src/lang.rs` thay **mọi** chữ "RustDesk", nên dòng ghi
     công AGPL biến thành *"Dựa trên LTTNexus 1.4.9"* — xoá đúng cái tên giấy phép bắt
     giữ. Nay có `GIU_TEN_GOC` loại trừ các khoá ghi công.
  2. Cổng cờ đặt trong **thân hàm** thì `Depends(require_login)` chạy trước → route đã
     đóng vẫn trả 303 về `/login`, tức vẫn xác nhận bề mặt đó tồn tại. Cổng phải là
     `Depends` và đứng **trước** `require_login` trong chữ ký.
  3. `phat-hanh-windows.ps1` đọc bản kê bằng `Get-Content -Raw` — PowerShell 5.1 đọc
     theo ANSI nên chữ có dấu trong `notes` sẽ nát ở lần phát hành **kế tiếp**, mà nát
     im lặng. Nay đọc bằng `[IO.File]::ReadAllText(..., UTF8Encoding(false))`.
- **Security/data impact:** vé SSO đi qua thanh địa chỉ nên có bốn hàng rào, mỗi cái một
  test: sống 90 giây · dùng một lần (đổi xong xoá vé, cấp phiên mới) · từ chối cookie
  phiên thường · `next` qua `safe_next` (chặn open-redirect).
- **Known issues:** trang giới thiệu chưa có ảnh chụp sản phẩm; trang tài khoản trên web
  chưa hiện máy + thuê bao; macOS `.dmg` chưa build; iOS chờ Apple Developer.
- **Next actions:** C1 dời relay khỏi Windows Server 2016 Eval (hết hạn 15/12/2026) ·
  C2 relay thứ hai · C3 đặt `LTT_NEXUS_RELAY_HOST` · C4 đổi mật khẩu relay + đóng RDP.


## 2026-09-02 — System Purification V1 (Phase -1 … 10) · FINAL PASS

- **Pham vi:** chuong trinh 11 phase don dep/dong nhat ma nguon + quy tac. **Khong
  deploy** (nhung xem "loi hua yeu" ben duoi). Nhanh `admin-mvp-v3`.
- **Ket qua gate cuoi:** `20260902T144559Z-21084` — **PASS 25 · BOQUA 1 · FAIL 0**,
  303s, tren cay chinh, `cay_da_doi_giua_chung: False`. Buoc BOQUA duy nhat
  (`test_214`) da dong **rieng**: 7/7 tren PostgreSQL that.
- **Push da xac minh:** `origin/admin-mvp-v3` = `01c23a5`, 0 commit con lai. Ca 13
  SHA moc kiem bang `merge-base --is-ancestor`, gom `89eb46c` — ban **dang chay
  production** ma truoc do khong nam tren remote nao.

### Lam duoc

- **Ngan sach CPU cho gate** (bao cao 08b). Goc: gate dem **tien trinh**, thu bi
  tranh la **loi**. `pytest -n auto` + 3×vitest 12 worker = ~61 luong / 20 loi,
  tren mot may **la production**. Nay `Step.so_loi` khai LOI, lich nhan viec theo
  loi, han muc truyen XUONG cong cu con, cong `BELOW_NORMAL_PRIORITY_CLASS`.
  ⇒ dinh ≤14 luong, va gate **nhanh hon 31%** (430s → ~300s).
- **`CLAUDE.md` 496 → 263 dong.** Bang trang thai chep tay (280 dong, 56% tep) da
  noi sai **nam lan**, ca nam ve phia nguy hiem. Thay bang mot **lenh**:
  `python tools\api_prod_canary.py trang-thai`.
- **Nen da phien:** `tools/thanh_phan.py` (so dang ky thanh phan, quan he suy tu
  **import** chu khong tu ten tep) · khoa theo **ten tai nguyen** (`cua_so_yen`) ·
  `cay_rieng.py` cap **dai so test** luc tao cay, **dem tren MOI cay**.
- **Banh coc:** nuot loi 63→62 · route server 2→1 tep · app-contract WARN 1→0.
  **Khong moc nao bi NANG.** `check_server_routes` truoc chi GHI so luong — nay so
  gia tri.
- **Hop dong app nhan them `bang_gia`**: `dashboard.py` thoi `import apps.anhnoibo`
  / `apps.ltt_voice` theo ten. Da kiem tren **URL cong khai** sau deploy.

### Nam cai bay da dinh, ghi de khoi dinh lai

1. **Gia thuyet khop qua vua KET THUC dieu tra** — 4 lan trong mot ngay:
   `.git` la tep o worktree → *"phep kiem chi dung o cay chinh"* (3 phien xep nham)
   · gate dot CPU → *"frontend nap vao bong bo test"* (2 lan treo may)
   · chay >180s → *"deadlock"* (that ra `BudgetError` o khau **dung**)
   · `fatal: does not appear to be a git repository` → *"kho sao luu khong ton
   tai"* (that ra **ACL chan doc**; `Test-Path` **nem loi** chu khong tra `False`).
   ⭐ Bai hoc: **mot thong bao loi noi ve cai NHIN THAY cua cong cu, khong noi ve
   THE GIOI.** Git da cai san su de dat — *"does NOT APPEAR TO be"* — va van bi doc
   thanh khang dinh ve the gioi.
2. **Cong cu kiem tra noi sai ve chinh no, theo huong nghe nhu tin tot.** Canh gac
   CPU in *"da xong, CPU dinh 0%"* suot ca ngay — no thoat o giay thu 2 cua moi
   luot 300 giay, vi `$!` cua bash **khong phai** PID cua Windows. Neu no im lang
   thi co nguoi hoi; vi no noi "da xong" nen khong ai hoi.
3. **`git add -A` khong biet ranh gioi nao ca.** No quet 7 tep chua theo doi cua
   mot phien khac. Giao uoc ranh gioi tep song trong dau nguoi, con lenh thi quet
   ca cay. ⇒ liet ke duong dan tuong minh, hoac `git add -u`.
4. **Heredoc nuot backslash** — dinh 3 lan, lan hai trong luc dang viet tai lieu
   canh bao ve chinh no. `\a` → BEL, `\t` → TAB. Ghi bang `Write`, va **doc
   `SyntaxWarning`**: mot canh bao khong lam lenh that bai **van la mot phep do**.
5. **Hang so go tay canh mot hang so khac se lech.** `budget_max_credit: 20` +
   `estimated 20` thieu mat `PLANNING_COST = 4`. Nay **suy ra**.

### No con lai — co ten, co pham vi

- 🔴 **Ban sao luu `D:\LTTBackups` CHUA XAC MINH DUOC** (khong phai "da mat") —
  ACL chan, `Get-Acl` cung tu choi. Chua `icacls` thi khong biet noi dung con dung
  khong. **Can nang quyen.**
- **294/774 chuoi i18n khach thay** (149 route app + 145 template) — viec **noi
  dung**, khong dich may.
- **`thanh_phan` mu voi test doc `.ps1`**: `--test trien_khai` tra **0 tep**, trong
  khi 10 tep test trien khai that chay **250 phep kiem xanh**. Do thi **import**
  khong thay canh do — va no mu dung o cho da tung lam sap production (BOM).
- **Ngan sach CPU la per-RUN, khong per-MAY**: hai phien moi phien 14 loi "dung
  luat" van la 28 tren 20.
- 22 so tep test trung san co (⛔ khong doi ten — chay theo duoi); dai so chan
  tuong lai.
- Chua tao mot **luot tieng noi that tren production** (khong co tai khoan khach).

### Tai lieu

`docs/system_purification/reports/` — 13 bao cao (`00`…`10`, `01b`, `08b`,
`phase_minus_1`). Bao cao `10_final_acceptance.md` chua ca hai **dinh chinh** va
phan quyet chot.

## 2026-09-04 — ChatLTT: bo kiem GUI dot 5-7, va sau lan bo kiem VU KHONG san pham

Gate day du **PASS** (`20260903T193457Z-12864.json`). Truoc do lat noi tiep:
5.934 passed / 32 skipped / 3 failed trong 41m32s — ca ba la `ho_so_he_thong`
cu, da sinh lai.

### Thu dang gia nhat cua buoi nay khong phai bug san pham

Bo kiem GUI bao **sau** hang muc HONG. **Khong cai nao la loi san pham.** Moi cai
sai mot kieu, va do la sau kieu khac nhau de mot bo kiem noi doi:

| Bao | Su that | Loai sai |
|---|---|---|
| 6.1/6.2 "nut media khong san sang" | model chua nap tren may B | suy tu giao dien thay vi hoi may chu |
| 6.3 "may chu nhan `voice_id` cua nguoi khac" | job `failed`, giu 1/thu 0/**hoan 1** | do chi tiet cai dat thay vi bat bien |
| 6.4 "bam Doc to khong gui gi" | dung thiet ke: phai qua o xac nhan gia | doi san pham **bo mot chot an toan** |
| 6.4 lan hai `manh_doi_chieu:""` | nua menh de tu tat | **xanh ma khong chung minh gi** |
| 3 hang muc dot 0 | man hinh dang hien "Model dang ban… khong bi tinh tien" | may ban bi doc thanh san pham hong |
| 7.4 "so du phai giam" | do 921 -> **933**: mot khoan hoan vua ve | chot huong tren mot dai luong khong don dieu |

🔴 **Cai nguy nhat la dong thu tu, du no XANH.** Nam dong kia do nen duoc dieu
tra; dong xanh do dong ho so lai.

⛔ Va 6.3 suyt gay thiet hai that: "sua" san pham cho khop se them mot cho kiem
so huu **thu hai** o route — dung thu `tham_chieu.tim_profile` canh bao — va cho
do **khong thay kho giong chung** nen se chan nham giong hop le.

### Hai gia thuyet sai bi phep do bac bo (khong thanh ban va)

- **"`mo_luong` ro suat admission"**: chi `server/api/streaming.py` co
  `BackgroundTask(release_by_id)`; duong ChatLTT khong thay cho nha, ma
  `llm_remote` chi co **1 suat** — mot ro se khoa ca san pham 20 phut. Do that:
  giu **1** giua luong, **0** sau luong. Cho nha o `_phat`: `with keep_alive(...)`.
- **"tran ra khong theo model"**: `tran_theo_ngu_canh()` dung `CUA_SO_MODEL`
  (204.800) vo dieu kien, con vision chi 65.536. Bac bo bang **so hoc**:
  `tran_vao_cua` da tru san `TOKEN_RA_TRAN`, nen dau vao hop le lon nhat cua
  vision la 30.720 va 30.720 + 32.768 = 63.488 <= 65.536.

### Chot moi, va mot chot dau tien la TAUTOLOGY

`tests/test_334`: chot `tran_vao_cua(m) + TOKEN_RA_TRAN + LE == CUA_SO_THEO_MODEL[m]`
(DANG THUC). Ban `<=` viet truoc **khong the do**: tong luon bang `cua_so - LE`,
nen nang `TOKEN_RA_TRAN` len 40.000 van xanh. Ban dang thuc **do dung mot thay
doi**: bo phan tru tran-ra khoi `tran_vao_cua` (98.304 > 65.536).

⭐ Hai luat rut ra, dung cho moi phep kiem sau:
**mot chot phai kem duoc kich ban lam no DO** — khong viet ra duoc thi chot ay
chua ton tai; va **mot phep do phai kem duoc doi chung lam no ra KHAC di**.

### ⛔ CHAN: khong dang nhap lai duoc production tu may nay

Hai thu chong len nhau, moi thu mot minh da du chan:
1. `/login` tra **403 `cf-mitigated: challenge`** ke ca voi client HTTP tran mang
   UA Chrome qua IPv4 (`/` tra 200, `/chatltt` tra 303 — khong thu thach);
2. thu thach khong hoan tat duoc: `brunhild.challenges.cloudflare.com` co **0 ban
   ghi A, chi AAAA** (do cheo 1.1.1.1 + 8.8.8.8; doi chung
   `challenges.cloudflare.com` dual-stack), ma may **khong co IPv6 toan cuc nao**.

⛔ Cach sua ghi trong `don-dep-sau-h6` (`Disable-NetAdapterBinding ms_tcpip6`)
**khong ap duoc** — voi mot host chi-AAAA thi tat IPv6 la di lui.

Con lai sau khi mo duoc dang nhap: **5.2, 5.3** (tao anh) va **6.2** (giong nhan
ban — tai khoan kiem chua nhan ban giong nao).

---

## 2026-09-05 — LTT Voice: "giao dien hien 1500" hoa ra la BAN DEPLOY CU

Trieu chung: kho ghi `TRAN_KY_TU_CONG_KHAI = 100_000`, web hien `0 / 1500 ky tu`.

⛔ **Khong phai cache, va khong phai loi ma nguon.** `C:\LTTPlatform\app` giu mot
ban chep tu thoi `master`, con `admin-mvp-v3` da di truoc **94 commit**. Bang
chung phan biet duoc hai gia thuyet: md5 cua `/static/voice.js` may chu **phuc
vu** khop **chinh xac** ban tren dia o thu muc deploy (79.040 B) chu khong khop
ban trong kho (91.281 B). Cache thi dia phai moi ma phuc vu moi cu.

⭐ Dieu dang giu khong phai "nho deploy". La: **khong co cho nao hoi duoc may chu
dang chay ma nao.** `/health/version` khi ay tra `"v1.0"` — doc tu `version.py`
cua *LTTStudios VideoBot*, hang so go tay tu 2025, khong doi qua bat ky lan
deploy nao. Nen cau hoi chi tra loi duoc bang cach so md5 hai thu muc bang tay.

⇒ `/health/version` nay tra **ba truong bat ba kieu troi DOC LAP**: `commit` (ma
nguon), `asset_ver` (tai san tinh qua CF), `ltt_voice` (hop dong tran). Chung
hong rieng re, nen gop lai mot truong thi khong phan biet duoc — ma phan biet
chinh la toan bo gia tri. `setup/2-cai-dat.ps1` ghi `dau_van_tay.json` (bang
`Write-NoBom`) vi ban deploy **khong** co `.git`.

### Bon loi TIM THEM khi dieu tra, khong ai bao

1. 🔴 **JS dem UTF-16, Python dem diem ma.** `maxlength` cung dem don vi ma, nen
   50.001 emoji = 50.001 ky tu voi may chu nhung **100.002 don vi ma** voi o
   nhap ⇒ trinh duyet **cat mat mot nua** mot van ban may chu hoan toan chap
   nhan, khong loi nao bao. Da go `maxlength`; `voice.js::demKyTu()` dem bang
   `Array.from` va chan o **cho NOP** (tat nut Tao + `role="alert"`), khong chan
   o cho go — van ban o nguyen de khach tu cat.
2. **Nhap TXT `s.slice(0, tran)`** — mat phan duoi ngay luc nhap, khong hoan tac
   duoc. Nay giu nguyen ca tep (da bo BOM).
3. **Song am `decodeAudioData` ca tep.** O tran moi: ~483 MB tai + ~967 MB PCM.
   Chu thich cu ngay tren `veSong` **da du bao dung** ("neu tran ky tu duoc noi
   thi cho nay phai doi") — tran noi 03/09, cho ay thi khong. Nay co
   `TRAN_GIAY_SONG = 600` + `songDeu()` (track PHANG, khong phai song bia ra).
4. **`100000` vs `100.000` tren cung mot luong**: o dem hien co dau cham, thong
   diep loi cua **chinh cua ay** thi khong. Filter `|so` chi toi duoc noi co
   Jinja ⇒ tach than ham ra `platform_core/dinh_dang.py::so_viet()`.

### Residue "Chay lo" — man chua bao gio duoc xay

`taoLo()` + `motLo()` trong `voice.js`: **236 dong**, export qua `window.LttVoice`,
**khong khuon mau nao goi**, gui toi moi khach cua moi trang Voice. `manifest.py`
ghi *"SAU TAB, va tu P8 ca sau deu da xay"* trong khi nav co **NAM**.

⛔ Da go, va ghi ro **dieu kien de no duoc phep quay lai**: mot nang luc lo THAT
nhu `infer_batch` (gop nhieu doan vao MOT luot GPU, do 01/09 cho 3,47x thong
luong), chu khong phai "moi dong mot job" — mo hinh cu chi la mot vong lap co
giao dien. **Dung dung lai no de mot chu thich noi "sau tab" thanh dung.**

⚠️ Giu nguyen nhung cho nhac Chay lo o **thi qua khu co ghi ngay**
(`tables_du_an.py`, `vo.py:106`, `ltt_voice_thongbao.html`) — viet lai lich su
cho khop hien tai la xoa mat chinh thu khien tai lieu ay co gia.

### Hai cai bay gap lai trong lot nay

- **Bo do quet trung phat viec giai thich.** Ban dau cua
  `test_nhap_txt_khong_cat_lang_le` tim `s.slice(0, tran)` trong ca tep va **do
  ngay** — chinh chu thich giai thich cai bay da trich dan doan ma ay. Ai muon
  no xanh se phai *xoa loi giai thich*. ⇒ `_bo_chu_thich()` + `test__..._tu_kiem`
  (mot bo loc hong ma khong tu-kiem se lam moi phep kiem dung no xanh vinh vien).
- **Heredoc Bash nuot `\n`** — lai mot lan nua. Dung `chr(10)` hoac Edit.

Tai lieu day du: `docs/LTT_VOICE/AUTONOMOUS_AUDIT/` (00–07).

### Ket qua 05/09: DA DEPLOY, va bon loi cua chinh ban va

Ba noi khop nhau o `fca8833e`: kho = GitHub = production.

    /health/version cong khai:  commit=fca8833ee57f  nguon=marker
    voice.js khach nhan:        63c7c169…  (truoc deploy: 7ace0b84…)
    tran dang chay:             100.000 / 1.500

25 giong kho chung da doi ten (public_id NGUYEN, nen hop dong API khong doi mot
chu). Bang doi khoa theo `ma_cu` chu khong theo ten hien thi — va quyet dinh do
CUU ca luot: `-Xem` lo ra 5 giong mang ten khac bang, trong do hai cai giu dung
ten toi dinh gan cho giong khac (`Ethan`, `Ivy`). Do `sua_luc` truoc khi ghi:
ca bon cung MOT GIAY (01/09 12:43:12) va `tao_luc` som hon ca nhom => do la bon
giong nhap dot dau ma luot nhap 01/09 chi va xuat xu, khong doi ten. Khong phai
phien nao dang lam song song.

## ⛔ BON LOI CUA CHINH BAN VA, VA MOT CAI DA VAO PRODUCTION

  ① nhanh `!AudioContext` van `return` tran => `songGia` (song ngau nhien) nam
    lai VINH VIEN — dung thu cai tran sinh ra de tranh. Tu bat khi soat diff.
  ② `/health/version` khong xac thuc ma `doc()` fork `git` moi luot goi. Tu bat.
  ③ bang doi ten khoa theo ten hien thi — thu troi duoc. Tu bat.
  ④ `songDeu` TU GOI LAI CHINH NO (de quy vo han). **Lot qua gate day du 6000
    test, vao production.** Phien Mobile V1 tim ra khi doc ma.

⭐ ④ dang ghi nhat, vi hai le:

  · Nguyen nhan la mot `str.replace` TOAN CUC cho dong `if (!canvas) return;` —
    dong ay co o HAI noi, va toi doc lai "cho toi nghi da sua" chu khong doc lai
    CA THAN HAM.
  · No CHUA BAO GIO NO (moi cho goi deu truyen canvas that). Nhung duong DUY
    NHAT kich hoat no lai chinh la nhanh phong thu — tuc dong viet ra de tu bao
    ve se la dong giet ca handler bang `RangeError`.

⇒ **Mot loi khong bao gio no van la mot loi**, va loai nguy hiem nhat la loai
  chi no o dung nhanh hiem ma nguoi ta viet ra de phong than.

⚠️ Va phep kiem dau tien toi viet de chot ④ CUNG SAI: cat tu chinh dong khai
   ham nen `"songDeu(" in than` luon dung, do tren mot ma da sach. Ban sua cat
   SAU chu ky, va da kiem nguoc bang cach tiem lai loi cu.

Memory moi: `thay-chuoi-toan-cuc-cham-dong-phong-thu`,
`hoi-may-chu-dang-chay-ban-nao`.

## Con lai, KHONG duoc doc thanh "da xong"

  1. Bug mobile (`/audio` thieu `Range` => Safari tu choi phat) da sua o
     `phien/mobile-v1`, **CHUA merge**. Do tren cay vua deploy: `grep -c "Range"
     _p_audio.py` -> 0. Can mot chuyen deploy rieng.
  2. O dem hien `100.000` la SUY RA tu ba manh da xac minh trong ban deploy
     (hang so, `|so`, khong con `maxlength`) — **chua mo trang bang mat**, vi
     dang nhap production tu may nay bi Cloudflare chan.
  3. `TRAN_GIAY_SONG = 600` co lap luan moi de ha (phien Mobile do: o 35 cot thi
     mot cot ganh 17 giay tieng). Co y KHONG gop vao chuyen nay.

Tai lieu: `docs/LTT_VOICE/NGUON_CHAN_LY.md` (chi muc), `AUTONOMOUS_AUDIT/00-08`,
`KHO_GIONG/00-01`.

---

## 2026-09-07 — ChatLTT V3: P10 (ba lỗ tiền), deploy, và PHÁT HÀNH sáu cờ

**Kết quả:** `33a76d8b` lên production 16:53; sáu cờ V3 bật 17:06; trunk đóng ở
`a0ef52cf`. Nghiệm thu ba chiều: 515 tệp `.py`, lệch 0 / thiếu 0 / **thừa 0**.

⚠️ **Chủ dự án quyết định phát hành TRƯỚC P11 (red team)** và xử lý P11 sau. Ghi
   ra đây là một quyết định **thương mại**, không phải kết luận kỹ thuật.

### P10 — ba lỗ tiền thật, cùng MỘT hình dạng

> Mọi đường phòng thủ đều canh lúc **có luồng đang chạy**.
> Lúc lượt **đứng chờ** thì không ai canh.

| # | Lỗ | Hậu quả |
|---|---|---|
| 1 | Dừng lúc lượt đang chờ là **no-op im lặng** | duyệt xong lượt vẫn chạy tiếp, tiêu tiền sau khi người dùng bảo dừng |
| 2 | Hai nguồn cùng chạy tiếp **một** run | **hai lượt model cho một lần duyệt** ⇒ tiền đi hai lần |
| 3 | Huỷ rồi mà **thẻ duyệt vẫn hiện** | bấm Duyệt, không có gì xảy ra, không lời giải thích |

Cả ba đều **tiêm bản cũ để xem có đỏ không** trước khi tin màu xanh. Lỗ 2 vá
bằng `platform_core.leases` chứ không lật cột trạng thái — lật cột chặn được đua
nhưng tạo ra một cách **kẹt vĩnh viễn** mới.

⭐ Lỗ 2 là đúng cái bẫy mà `duyet._quyet` **đã học và ghi vào mã của chính nó**
  (*"Điều kiện nằm TRONG WHERE"*). Cùng kho, cùng tuần — một chỗ học được, một
  chỗ chưa. Bài học không tự lan sang tệp bên cạnh.

### Bẫy 33 — bật một bước gate đang tắt cũng là một THAY ĐỔI

Đặt `LTT_TEST_DATABASE_URL` để cứu một bước `[BOQUA]` ⇒ bước chạy thật 140,7 s,
**và gate ĐỎ**: biến ấy tới **mọi worker pytest**, `pg_scratch.py` dùng nó làm
công tắc bật năm tệp sang PostgreSQL thật, chúng đâm nhau qua xdist.

Cách đúng: chạy **cạnh** gate, không **trong** gate ⇒ được cả hai vế.

### 🔴 Giải thích được một chặn mà mục 05/09 đã ghi

Mục **2026-09-05** viết: *"đăng nhập production từ máy này bị Cloudflare chặn"*.
Hôm nay tìm ra nguyên nhân, và nó **không phải bot-detection**:

```
brunhild.challenges.cloudflare.com  ->  CHI CO IPv6
ket noi IPv6 tu may nay             ->  KHONG DUOC (may khong co IPv6 toan cuc)
```

Challenge cần một host chỉ có IPv6 ⇒ không tải nổi ⇒ treo vĩnh viễn ở *"Just a
moment…"*. Lỗi **hạ tầng mạng**, không phải phán quyết bot.

🚨 **Và hệ quả chưa xác định bán kính:** nếu Cloudflare cũng phát challenge cho
   khách thường thì **mọi khách ở mạng chỉ có IPv4 đều kẹt**. Đo từ một IP thì
   không phân biệt được "chính sách chung" với "IP máy này bị chấm điểm". Phép
   kiểm rẻ nhất: mở site trên điện thoại 4G.

### Còn nợ — không cờ nào che được

| Nợ | Trạng thái |
|---|---|
| **P11** red team | chưa chạy; bản giao ở `docs/CHATLTT_V3/15_BAN_GIAO_P11_RED_TEAM.md` |
| **CK1** | ma trận 5 mốc + CLS đã đo trên Chrome thật; vế **URL công khai** chưa |
| **Hạn mức lưu trữ** | tải lên **miễn phí**, không giới hạn số lượng; `C:` còn 458,6 GB ≈ 23.500 lượt là đầy ⇒ **sập cả nền tảng** |
| **M3 · R3** | hai hằng số vẫn là **neo tự suy**; R3 **đã từng sai 13 lần** |
| **D1 · D2** | hai lỗ trong chính đường ray deploy — xem `docs/16` |

### Ba lần tôi sai trong ngày, đều cùng hình dạng

Một lời giải thích **khớp vừa đủ** làm điều tra dừng sớm:

| Tôi tưởng | Thật ra |
|---|---|
| Huỷ hỏng vì **đa tiến trình** | `_danh_thuc_run` chạy ở tiến trình web |
| URL công khai chặn vì **Cloudflare coi là bot** | **thiếu IPv6** |
| Phụ phí V3 là **204 ms** | 987 ms lượt đầu (nạp module) rồi **2,7 ms** |

⭐ Và một lần nữa do phiên khác bắt: tôi ghi bài học deploy đổ lỗi cho **thời
  điểm**, trong khi lỗi thật là tôi **đã thấy** dòng `??` và **đọc nó thành
  "không sao"**. Phép kiểm chạy đúng; người đọc nó sai.

Tài liệu: `docs/CHATLTT_V3/STATE.md` · `docs/BAY_TRONG_CONG_CHAT_LUONG.md`
(Bẫy 33) · `docs/16_CAP_NHAT_VA_DEPLOY.md` (D1/D2).

## 2026-09-08 — ASV GUI V5 (`phien/asv-v4`, `7f658fb3`)

Ba commit: giao dien san pham (24 buoc §15) · mo hai van da co san · ban giao.
Gate L3 `FAIL (1/29)`, do dung mot buoc — 19 ERROR deu la `test_448`.
8.072 + 96 passed, **0 FAILED**.

Chi tiet o `docs/auto_scan_video_v5/BAN_GIAO.md`. Ba dieu dang mang sang phien
sau:

- 🔴 **"Sinh lai bang chung can UAC" la SAI.** Bai ghi bao cao chi doi
  `LTT_TEST_NANG=1` + `LTT_ASV_E2E_RA`. Script `nghiem_thu_asv.ps1` can quyen de
  lay **token giong that**; hai `assert` doi giong that thi **co dieu kien**.
  Toi da go duoc rao "khong dao nguoc duoc" roi **giu nguyen rao UAC ma khong
  kiem lai no** — nam luot chan doan sai cua bon phien troi qua vi mot cai rao
  khong ton tai.

- ⛔ **Luot nghiem thu 21:41 khong hop le**: chay thieu co bat duong that nen
  `thay_the` = 4 cua (LLM + ba cua giong), **khong cham may B**. Hai loi thu duoc
  la `database is locked` (ha tang test) va truot QC T4 (giong SAPI tieng Anh
  trong mot bai long tieng Viet). Da hoan nguyen, bam khop ban sao ngoai kho.
  **Viec dau tien cua phien sau: tim co bat duong MODEL THAT.**

- ⭐ **Bon phien tim ra bon ca cua cung mot hinh dang** trong mot ngay: nang luc
  dung, phep kiem xanh, ma **khong ai di tren duong toi no** (`license_status` ·
  `a11y_quet --cookie` · `NHAN_LOC[phong_cach]` · `tu_dien_rieng`). Cai sai nam o
  khoang giua, cho khong tang nao so huu.


---

## 2026-09-08 — OPERATING STANDARDIZATION: một hợp đồng vận hành, và một cửa giả

Bốn commit: `229927d6` · `144c4847` · `9484e5f1` · `974cb984`. Đã đẩy GitHub.

### Vấn đề

Cadence chép lại trong **10 tệp kế hoạch**, và **5 bản chép KHÁC NHAU**:
`--vong-lap` sau mỗi lần sửa · `--doi` trong vòng lặp · `test_nhanh --lf` sau mỗi
lần sửa · một tập bất biến riêng · và `test_nhanh.py` **rồi** `gate.py`.

Không ai cố ý viết sai. Cái sai là **không có chỗ nào để trả lời**, nên ai cần
một cadence thì tự viết một cái.

⇒ `docs/00_LTT_OPERATING_CONTRACT.md` (mới) · `CLAUDE.md` 375 → 186 dòng ·
`tools/check_luat_van_hanh.py` (bánh cóc trong gate, 1,9 s, chốt TẬP HỢP).

### 🔴 `--doi` tồn tại, được tài liệu hoá, và CHƯA TỪNG thu hẹp gì

Đếm 59 bản ghi `test-results/gates/*.json`: `doi` **0 lượt**, `pham-vi` **0 lượt**.
`thanh_phan.toml` không khai `tests/`, nên **mọi thay đổi chạm một tệp test đều
hạ cấp xuống gate đầy đủ** — mà gần như mọi thay đổi thật đều kèm một tệp test.

| Thay đổi | Trước | Sau |
|---|---|---|
| chỉ một tệp test | 532/532 | **1/532** |
| app + test của nó | 532/532 | **118/532** |

⛔ Bản sửa **đầu tiên sai**: suy chủ tệp test từ `import` của chính nó → **86 %**,
một phạm vi *trông hẹp mà không hề hẹp*. Phép đo giết giả thuyết, không phải trực giác.

### Tài liệu sai gấp đôi ở 6 chỗ

Gate đầy đủ: tài liệu ghi "~5 phút"; trung vị 43 lượt là **11,4 phút**, và lượt
đo trực tiếp hôm nay là **12,4 phút**. Cả sáu chỗ đều chép tay từ nhau.

### Ba lần tôi sai, và cả ba đều được phiên khác hoặc phép đo bắt

| Tôi tưởng | Thật ra |
|---|---|
| gate có **26 bước** (đếm `Step(` bằng AST) | **30** — ba lời gọi frontend nằm trong vòng lặp có điều kiện |
| deploy chép **cây sống** ⇒ việc dở của phiên Voice sẽ lên production | `git archive` từ **commit** (`setup/2-cai-dat.ps1:201`); tệp chưa commit **không** lên |
| hai phiên sửa bánh cóc **sau khi tôi nhắn** | Workflow V2 sửa **trước**; tôi gán nhân quả cho một phép đo không trả lời câu đó |

Và một lỗi tôi tự mắc **ngay sau khi viết luật cấm nó**: đọc `check_ruff.py 2>&1
| tail -4; echo "EXIT=$?"` — `$?` đó là của `tail`. Thứ cứu tôi không phải sự cẩn
thận mà là `pre-commit` tự chạy lại ruff.

### 🔴 Bài học đắt nhất — một PHÂN BIỆT

Chủ sản phẩm bảo các phiên khác **"dừng chạy pytest"**. Họ **giữ lời tuyệt đối**:
máy chỉ `0.9/20` lõi bận suốt 12,4 phút. Lượt gate vẫn ra `CAY DA DOI GIUA CHUNG`
— 16 tệp. Họ không **chạy** gì cả; họ **gõ**.

> **"Không dùng CPU" ≠ "cây đứng yên".** Một lượt gate cần **cả hai**, và
> `cua_so_yen` chỉ đo được vế đầu.

Cái bẫy không nằm ở sự sơ ý mà ở chỗ **hai câu nghe giống nhau**: "đừng dùng CPU"
thoả mãn được bằng cách viết mã suốt 12 phút. Một phiên **tuân thủ hoàn hảo** vẫn
phá lượt đo của người khác. ⇒ `docs/00_LTT_OPERATING_CONTRACT.md` **§4.9**.

⚠️ Và tôi mắc đúng lỗi đó trong cùng lượt: sửa `docs/BAY_TRONG_CONG_CHAT_LUONG.md`
giữa lượt gate của **chính mình**, chỉ thoát vì `docs/` không nằm trong `THU_MUC_CHUP`.

### Bẫy 37 — `pre-commit` stash UNSTAGED nhưng không stash UNTRACKED

Một tệp untracked của phiên A cộng vào bánh cóc của phiên B, và **không** hiện
trong `git diff --cached` của người bị chặn. Hôm nay đánh trúng **hai** bánh cóc:
`ruff` F401 và `bo qua`.

### Nợ

| Nợ | Trạng thái |
|---|---|
| **Deploy** | ⛔ **CHƯA** — bị chặn bởi chế độ quyền của phiên, không phải bởi mã. 10 commit từ bản đang chạy (`03a83a1c`) tới `974cb984`, gồm **5 migration Workflow V2** |
| Số giây thật cho `--doi` | chưa đo được — cả ngày chưa có cửa sổ nào cây đứng yên |
| `docs/**` vẫn hạ cấp xuống đầy đủ | **70 tệp test đọc `docs/`** ⇒ cần bản khai chủ sở hữu, không phải luật miễn trừ |
| `@pytest.mark.slow` | dùng 1 lần mà chưa khai trong `pytest.ini` |


---

## 2026-09-08 — LTT VOICE: 15/20 hạng mục của bản kiểm toán VIRAL_VOICE

**Commit:** `2d9dcf1a` (13 hạng mục) · `c8a9eed0` (U-15, U-17) · đẩy GitHub xong
**Quyết định:** `docs/LTT_VOICE/DECISIONS.md` DV-012 → DV-018

### Ba lỗ TIỀN, tìm ra khi nối hồ sơ tốc độ vào đường báo giá

| lỗ | đo được |
|---|---|
| `_gia` tính cả bài như **một** lượt phát | bài 100.000 ký tự = 67 đoạn: giữ **1.112**, giá thật **1.132** |
| ô "ước credit" không nhận `preset` | hiện số của giọng **mặc định**, phần tạm giữ dùng số giọng khách chọn |
| nhận/bác hồ sơ **theo từng trường** | `1,0 + n/18` **<** `1,5 + n/18` — ước thấp hơn cả đường lùi thuần |

Cả ba lệch về **đúng phía chốt 3.3 cấm**: giữ thiếu credit.

### 🔴 Một cánh cửa MỘT CHIỀU KHÔNG CÓ CHÌA — do chính lượt sửa gây ra

`license_status` (U-05) được cổng **đọc**, và **không ai ghi**. Trước bản vá,
`dung_chung=True` là **đủ**; sau nó là **cần nhưng không đủ**, và điều kiện đủ
**không đường nào đạt tới**.

⭐ Đúng lớp lỗi `DV-010` mà chính lượt ấy viết cảnh báo về nó. Một bảng đọc được
mà không ai ghi trông **y hệt** một bảng đang hoạt động.

⇒ `tools/soat_giong.py`, bắt buộc `--ly-do` ở **cả hai** chiều. Chủ sản phẩm hỏi
*"còn sót hạng mục nào"* là thứ bắt được nó — nếu không nó đã vào gate và **xanh**,
vì mọi phép kiểm đều chỉ đo phía đọc.

### Bốn ca cùng một họ trong một ngày, bốn người khác nhau tìm ra

```
license_status          cong DOC duoc, khong ai GHI
--cookie cua a11y_quet  docstring khai, CHUA BAO GIO chay
NHAN_LOC[phong_cach]    route loc du 3 mat, template ve 2 o  (ASV tim ra)
doc_so_tran cua ASV     nhanh "theo khuon" khong ai vao       (ASV tim ra)
```

Hai câu hỏi rẻ bắt được cả bốn — và cần **cả hai**:

1. **có ĐƯỜNG tới người dùng không?** → bắt hai ca đầu
2. **có XE trên đường đó không?** → bắt hai ca sau

⚠️ Câu 2 khó hơn hẳn: câu 1 trả lời được bằng `grep` một tên; câu 2 phải phân
biệt **phía nhận** với **phía gọi**.

### Bộ đo hỏng ở đúng chỗ nó được cần tới lần đầu

`tools/a11y_quet.js` gọi `new URL(...)` — không tồn tại trong sandbox
`playwright-cli run-code`. Nằm **trong** nhánh `if (CAU_HINH.cookie)`, mà
`ROUTE_MAC_DINH` chỉ có bốn route **công khai** ⇒ nhánh ấy **chưa bao giờ chạy**.

⭐ Bản vá **đã nằm sẵn** ở `tools/mobile_quet.js:189` kèm nguyên chú thích giải
thích. Ai đó gặp lỗi, sửa ở **một** tệp, ghi lại lý do — tệp anh em cùng đoạn mã
thì không ai sửa.

> **Chép lại bộ đo mà không chép bài học là cách một lớp lỗi sống sót qua chính
> bản vá của nó.**

⇒ `tests/test_513` chốt **cả hai** tệp, và dò danh sách **bằng nội dung**
(`const CAU_HINH`) nên bản sao thứ ba cũng bị bắt.

### Kết quả soát a11y — lần đầu ba màn cần đăng nhập được đo

`55 nút / 5 mã` → sửa `aria-progressbar-name` → `53 nút / 4 mã`.

⛔ **36 nút còn lại là một QUYẾT ĐỊNH, không phải một bản vá.** Chúng đến từ một
dòng: `<article role="button" tabindex="0">` bọc hai `<button>` thật. Cấu trúc ấy
đã gây **hai lỗi thật đã vá bằng JS** (04/09 chuột không mở được panel; Enter trên
nút nghe thử bị nuốt). Gỡ nó đổi điều hướng bàn phím của **mọi** khách. Nêu kèm
bằng chứng ở DV-018, chưa làm.

### 🔴 Bảy phép kiểm chặn gate của MỌI phiên, và không phiên nào sửa được

`test_448` đọc một tệp báo cáo **TĨNH** ghi nguyên văn
`'khong provider nao phuc vu duoc: ltt_llm: ban'`. Đo ở **ba** cây: cùng
`20.475 B`, sửa lần cuối `09-07 20:25`.

⚠️ Sinh lại chạy qua `setup/nghiem_thu_asv.ps1`, script ấy đọc `secrets\app.env`
đang bị ACL chặn ⇒ **bật UAC** ⇒ **chủ sản phẩm phải bấm chuột**.

⛔ `icacls` để đi vòng là **gỡ hạng mục W1.5**. `CLAUDE.md` xếp UAC vào bốn thứ
giữ lại kể cả khi chưa có khách: *"ràng buộc **cơ học** — không phải chuyện quyền"*.

⭐ Phiên ASV tự sửa một chỗ đáng ghi: họ từng từ chối sinh lại vì tưởng là **ghi
đè bằng chứng không đảo được**. Kiểm lại: tệp được git theo dõi và đang sạch ⇒
`git checkout` đảo được. **Hai rào bị gộp làm một, và chỉ một là thật** — cái rào
không tồn tại đã giữ tệp ấy đứng yên qua **năm** lượt chẩn đoán sai của bốn phiên.

### Ba vòng chẩn đoán sai về PostgreSQL, và cả ba đều "đúng" ở tầng của nó

```
vong 1  "thieu PostgreSQL"       -> sai. Postgres DANG CHAY
vong 2  "thieu quyen CREATEDB"   -> sai. Xac thuc TRUOT TRUOC do
vong 3  doc nham TEP app.env, vi tep dung bi ACL chan
```

⚠️ Thứ cắt được vòng lặp không phải sự cẩn thận — là in `user=` và `host=` thay
vì chỉ in `type(ex).__name__`. **Một tên lớp ngoại lệ tương thích với mọi giả
thuyết.**

⇒ Đã đính chính `docs/OPERATING_STANDARDIZATION/FINAL_REPORT.md` (phiên
OPERATING đã kết thúc), và đổi mục P0 từ một **lệnh sửa** sang một **lệnh đo** —
một P0 ghi sẵn `GRANT CREATEDB` sẽ được ai đó chạy, và nó **không sửa gì**.

### Hình dạng lỗi lặp nhiều nhất trong ngày

**Phạm vi phép đo hẹp hơn phạm vi lời tuyên bố** — ít nhất **chín** lần, ở cả bốn
phiên. Ba lần rõ nhất của tôi:

| tôi ĐO | tôi TUYÊN BỐ |
|---|---|
| `grep` trong `tests/test_50*` + `test_51*` | *"không còn ai gọi `nang_luc`"* (sót `test_338`) |
| **7** công cụ tĩnh chạy `rc=0` | *"bánh cóc xanh"* (gate có **24**) |
| commit **cùng cây** đổi mtime | *"commit chạm cây của **mọi** phiên"* |

⭐ Cái thứ hai đắt nhất: bước làm lượt L3 đỏ trả lời trong **2,6 giây**, và tôi
tiêu **15 phút** cộng một cửa sổ ba phiên đứng yên để học nó.

> **Một tập con không tự khai rằng nó là tập con.** Bảy dòng `rc=0` trông y hệt
> hai mươi bốn dòng `rc=0` — khác biệt nằm ở thứ *không có mặt*.

⇒ `DV-016`. Danh sách bước tĩnh nay lấy **từ `tools/gate.py::_steps`**, chạy hết
trong ~50 giây — tỉ lệ 1:15 so với một lượt L3 đỏ.

### Điều kiện thứ BA của một lượt gate

Ngoài *"máy rảnh"* (§4.8) và *"cây đứng yên"* (§4.9), có vế thứ ba chưa ai nói:

> **Đừng chạm cây làm việc qua git** — và `commit` đứng **đầu** danh sách, không
> phải cuối.

Đo được: commit `0d1ffe5a` lúc `16:56:48`, và `16:56:49` **năm tệp unstaged của
phiên khác đổi mtime**. `pre_commit/staged_files_only.py` dùng
`git checkout -- .` rồi `git apply` — xoá sạch rồi đắp lại.

⚠️ **Đính chính của chính tôi:** tôi suy rộng thành *"commit chạm cây của **mọi**
phiên"*. Sai — `_CHECKOUT_CMD` dùng `'.'` = **thư mục hiện tại**, nên nó chỉ chạm
**cùng cây**. Phiên `AI Clean Rebuild` bắt được, bằng cách đọc nguồn.

⭐ Và kết luận của họ mạnh hơn cả bản sửa:

> **Đường thoát không phải thêm một cửa sổ, mà là đứng ở cây khác. Cửa sổ phải
> thương lượng mỗi lần và hỏng khi một bên quên; cây riêng thì hỏng không được.**

Hôm nay **cả bốn phiên** đều vi phạm đúng cái luật mình vừa tự viết ra. Tôi viết
§4.9 rồi vi phạm nó ở **lượt kế tiếp**.

### Còn lại — và mỗi cái chặn bởi một thứ ĐO ĐƯỢC

| | chặn bởi |
|---|---|
| U-07 streaming | mô hình **tính tiền mới** (luồng không có tệp cuối) + cửa đang tắt + PCM16 kém float32 |
| U-10, phần đo U-01 | **sidecar không chạy** (`san_sang()=False`, 0 giọng đã đo) |
| U-16 | clip có **consent** — chủ sản phẩm |
| U-19 | license trọng số |
| U-20 | XL |

**Bàn giao:** `tests/test_514` (bất biến liên app: không app nào ghim cứng khuôn
chuẩn hoá) đã soạn xong nhưng **chưa thả vào** — nó sẽ đỏ cho tới khi ASV đổi
`giong_noi.py:148` `bool = False` → `bool | None = None`. ASV đang sửa tệp ấy
trong changeset của họ.

---

# Phiên 09/09/2026 — VPS V2 lên production, và hai lỗ rò chỉ URL công khai mới thấy

Deploy `84661047`. Trunk `admin-mvp-v3`, nhánh phiên và production **cùng một băm**.

```
nghiem_thu_deploy   635 tep .py   lech 0 · thieu 0 · THUA 0
/health/ready 200   ·   gate: 7 do, ca 7 la test_448
```

## Việc chính: VPS V2 (11 tệp test, 3 migration, 7 lỗi P0)

Tách năm khái niệm trạng thái (vòng đời / điện mong muốn / điện quan sát / tác vụ
đang chạy / độ tươi), cột `trang_thai` cũ thành **phép chiếu**. Bốn lệnh điều
khiển chuyển sang hàng đợi job. Bảng `vps_thao_tac` — bản ghi thao tác bền, khác
hàng đợi job và khác nhật ký sự kiện. TLS **fail-closed**: production không có CA
thì từ chối nối Proxmox.

Chi tiết ở `docs/vps_v2/` (kế hoạch · STATE · ADR · KNOWN_BLOCKERS · scorecard).

## 🔴 Bài học đắt nhất — và nó không nằm trong mã

Sau khi deploy, **một lượt `curl` lên URL công khai** tìm ra trang bán hàng `/vps`
đang in cho khách chưa đăng nhập:

```
Hien chua nhan may moi. (chua cau hinh Proxmox: production ma khong co
LTT_VPS_PROXMOX_CA: tu choi noi toi Proxmox ...)
```

Vá xong, **quét AST cả `apps/vps/` theo HẠNG lỗi** (f-string mang tên biến ngoại
lệ, không nằm trong `log.*`) ra 14 chỗ — và một chỗ đang sống, trên **trang máy
của khách**:

```
{'thong_diep': 'ProxmoxError: 500 loi tai https://10.10.0.2:8006/api2/json/nodes/pve1'}
```

Tên class Python + IP nội bộ + cổng quản trị + đường dẫn cụm. Cả hai **có sẵn từ
trước** chương trình này, và cả hai lọt qua `test_557` + `test_559`.

⛔ **Không phải vì hai bộ test yếu.** Vì chúng đo **mã** và đo **render local**.

⭐ Và `RELEASE_SCORECARD.md` đã **viết ra** hạn chế ấy — dòng *"⚠️ local, chưa phải
   `app.lttstudios.com`"* nằm ngay trong bảng, tôi đọc qua nó rồi vẫn chấm 95.

> **Một hạn chế đã biết và đã ghi ra giấy không tự biến thành một phép đo.** Nó
> chỉ đổi trạng thái khi có người chạy một lệnh và đọc kết quả.

⇒ Bản vá dài hạn không phải hai commit sửa chuỗi, mà là **`tools/vps_quet_ro_ri.py`**
  — quét chuỗi cấm trên chính URL công khai, chạy sau mỗi deploy, cạnh
  `nghiem_thu_deploy.py`. Không nằm trong gate: gate phải chạy được khi không có
  mạng và nó đo *commit ở cây*, còn công cụ này đo *bản đang phục vụ khách*.

  Nó đòi **tiền đề** (HTTP 200 + ≥2 KB) trước khi kết luận, và nó **đỏ trên bản
  production cũ** — đó là đối chứng, không phải một cái vỏ luôn xanh.

Điểm hạ thật thà: SOFTWARE 94 → **91** · Bảo mật 94 → **88** · GUI 95 → **90**.

## Bài học thứ hai: git xoá thứ nó theo dõi, để lại thứ nó bỏ qua

Lượt hoà chiến dịch AI CLEAN REBUILD V2 xoá `chataistudio` + `codex_sidecar`.
`git status` sạch **0 dòng** ở cả hai cây. Nhưng:

```
apps/chataistudio/__pycache__/  6 .pyc      codex_sidecar/__pycache__/  3 .pyc
tep nguon: 0        git ls-files: 0
```

Ba phép kiểm **có sẵn** bắt được (`test_60` · `test_85` · `test_1004`). Và
`robocopy` trong `setup\2-cai-dat.ps1` lọc `/XD` theo **tên thư mục**, không theo
trạng thái git — nên nó sẽ chép `apps\chataistudio\` lên production thành một
thư mục con của `apps/` **không có `manifest.py`**.

🔑 Thứ thiếu không phải phép kiểm, mà là **chạy chúng trên cây sẽ được chép đi**.
   Gate của phiên xoá chạy *trước* ff; gate của phiên deploy chạy *sau* lượt hoà.
   Chỉ vị trí thời gian ấy quyết định ai nhìn thấy.

⇒ **Sau mỗi ff/merge có xoá thư mục: `git clean -ndX` trên cây ĐÍCH.** Và lượt
  gate cuối phải chạy trên cây **sẽ được deploy**, sau khi mọi thao tác git xong.

## Bài học thứ ba: `cua_so_yen` trả lời một câu KHÁC

Lần thứ ba trong bốn ngày. Hai phiên bấm gate cách nhau **56 giây**; tôi có chạy
`cua_so_yen.py trang-thai` và nó trả `RANH`.

**Nó không sai.** `tools/test_nhanh.py:414-436` ghi từ 05-06/09: nó trả lời câu
*"có ai **xin** khoá không"*, không trả lời *"có gì đang **chạy** không"*. Tôi đọc
`RANH` rồi bỏ bước kiểm **cây tiến trình** — vế quyết định.

⇒ Đo khoá (điều kiện **cần**) rồi đo cây tiến trình (điều kiện **quyết định**),
  lọc theo `Name -eq 'python.exe'` chứ **không** theo `CommandLine -like '*gate.py*'`
  — chuỗi ấy nằm trong chính lệnh mình vừa gõ nên nó tự khớp vào mình.

## Còn lại — chặn bởi thứ ĐO ĐƯỢC, không phải bởi mã

| | chặn bởi |
|---|---|
| `lifecycle` vẫn `development` | chưa chạy mạch nghiệm thu live (B-04) — cần VM thử |
| Bán máy đầu tiên | `LTT_VPS_PROXMOX_CA` chưa đặt (B-03); 0 máy đang chạy nên hôm nay không cắt gì |
| Backup/DR trần **50** | không có đích sao lưu độc lập (B-01) — phải mua/dựng |
| LIVE INFRA **45** | một node PVE chạy lồng, không HA (B-02) |
| `/api/v1` đóng cho VPS | ba quyết định sản phẩm (B-06) |

---

## 2026-09-09 → 10 · Phiên **Dọn Dẹp hệ thống API** — AI CLEAN REBUILD V2 đóng

**Chiến dịch: 19/19 pha.** Trunk `3b22503c` · production `3b22503cc590` (build 2026-09-10T10:18:13).

### Cái đã gỡ — đo **có phạm vi**

```
21 tep xoa han · 2.978 dong
```

⛔ Không phải `git diff --shortstat` của cả nhánh (`328 tệp, +29.153/−5.524`).
Nhánh `phien/aiclean` mang **51 commit** kể từ nền, chỉ ~15 là của chiến dịch —
số còn lại là LTT VOICE, WORKFLOW V2, VPS V2. Lấy con số tổng rồi gán cho chiến
dịch là **nhận công của bốn phiên khác**.

| | Trước | Sau |
|---|---|---|
| Nhà cung cấp ngoài gọi được | 5 | **1** (BytePlus) |
| Khoá API legacy trong CSDL | 4 **đang sống**, ~455 lượt/cái | **0** |
| Khoá legacy trong `secrets\app.env` | 4 | **0** |
| Dịch vụ Windows của đường đã gỡ | 1 (`LTTStudioCodex`) | **0** |
| Nhánh remote | 25 | **10** |

### Bốn đường sinh thật — chứng minh, không suy

| | Bằng chứng |
|---|---|
| Text | ba cửa `/chat/completions` · `/messages` · `/responses`, 200 với token thật |
| IMAGE | ảnh **5.519.918 byte** qua Cloudflare, `held:3 charged:3`, `mode:"live"` |
| VLM | `{"so_hinh_tron": 3, "chu": "K7QX"}` — khớp đáp án **máy sinh** |
| Voice | job `7a0ea335` qua hàng đợi production → **8,48s tiếng**, báo giá 2 = thu 2 |

⚠️ **Seedance ⊘ ngoài phạm vi** bằng **lời xác nhận của chủ sản phẩm**, không
phải phép đo. Nên E2E là **9/10**, không phải 10/10 — bốn đường đo được thì đã
đo, đường thứ năm thì ta *tin*, và hai thứ đó không được viết cùng một chữ.

**Điểm 82 → 86**, trong đó **một trục bị HẠ**: `Legacy removal` 10 → 9.

### 🔑 Bài học lớn nhất: mọi phép kiểm soi MÃ, không cái nào soi HÀNG TRONG BẢNG

Sau khi mọi phép kiểm đã xanh và báo cáo đã viết, việc dọn **dữ liệu** lôi ra
thứ việc dọn **mã** không thấy: bảng `api_keys` production còn **bốn khoá đang
bật** của chính các nhà cung cấp đã gỡ. Một khoá `cheapkeyai` được cấp phát lúc
**23:35:41** — đúng giây một job ảnh của khách được tạo.

`public_api/capacity.py::_providers_healthy` xin khoá **không lọc nhà cung cấp**,
nên `/api/v1/capacity` đã trả lời khách *"còn phục vụ"* dựa trên một khoá mà
`chan_neu_da_ngung` sẽ từ chối ngay khi có ai gọi thật — **chào bán một năng lực
không tồn tại**.

⇒ Đã vá ở **mã** (`tests/test_1008`, 6 phép kiểm, một là đối chứng chạy lại
  nguyên văn thân hàm cũ), và xoá 4 hàng khỏi CSDL (có sao lưu). Xoá dữ liệu chỉ
  dập triệu chứng của hôm nay.

### Ba lỗi của tôi, ghi ra vì một báo cáo chỉ liệt kê lỗi người khác thì không ai tin phần còn lại

1. **Giải thích một triệu chứng bằng sai nguyên nhân, rồi phát tán nó.** Ba lần
   `cua_so_yen` báo `RANH` khi gate đang chạy; tôi kết luận *"nó trả lời câu
   khác"* và gửi kết luận ấy cho **ba phiên**. Nguyên nhân thật: một fixture test
   (`test_394`) **xoá khoá thật của máy** — khoá vắng **84%** thời lượng mỗi lượt
   gate. Tôi tự tái hiện: bộ test **31 passed** trong khi nó xoá hàng rào.
   ⇒ Dấu hiệu đáng lẽ phải làm tôi đi tiếp: khoá không chỉ *"không thấy"* mà
     **tệp biến mất**. Một công cụ trả lời sai câu thì vẫn để lại tệp.

2. **Một byte BEL chặn gate cho mọi cây.** `C:\LTTPlatform\secrets\app.env` viết
   trong chuỗi Python không raw → `\a` thành `0x07`. Tôi **đọc lại đoạn văn ấy
   vài lần** và không thấy — vì mắt đọc **ký tự**, lỗi ở tầng **byte**. Và bản
   sửa đầu tiên của tôi **xoá luôn dấu gạch chéo**: phép thoát là *hai-đổi-một*
   nên phục hồi phải là *một-đổi-hai*.

3. **Cảnh báo sai về việc hạ mốc.** Tôi tự khai hạ mốc `ruff` là "tác dụng phụ
   phạt cây chưa hoà" — **sai**: mốc là **tệp trong cây**, nó đi cùng mã biện
   minh cho nó. Tôi khớp mẫu vào một bài học đúng cho trạng thái **toàn cục**,
   cho một cơ chế **khác hình dạng**.

### Việc phối hợp — sáu phiên, một máy 10 lõi

Cơ chế **đo-lại-sau-khi-bấm** chạy nhiều lần, hai chiều. Ca hẹp nhất: **2 giây**.
Luật bổ sung rút ra cùng phiên `4bot`: **lệch dưới ~5 giây thì đừng phân xử bằng
thời điểm** — nó nhỏ hơn độ phân giải của chính cơ chế — mà phân xử bằng **cây
nào mất nhiều hơn**; cây chính thắng.

Và tách được phạm vi của câu *"chồng gate làm sai"*: nó làm sai **bộ test**,
không làm sai **bánh cóc đếm** (đọc mã rồi đếm, ra cùng số dù CPU 2% hay 100%).
Hai phiên suýt vứt một lượt gate hợp lệ vì câu ấy được truyền đi **không kèm
phạm vi**.

### Còn lại — nói rõ để không ai đọc rộng hơn phạm vi

- **`test_448` × 7** — nợ của ASV v4, truy được về commit `3eae396d` của chính
  phiên ấy, kèm tệp bằng chứng do cùng commit ghi ra. **Không phải của chiến dịch.**
- **Năm phát hiện ngoài phạm vi** — báo cáo, **cố ý không tự sửa** (`PHA15` §5).
- **`llm_gateway/dem.py` không có trên trunk** ⇒ lượt deploy này **không** mang
  phần gia cố LLM gateway của phiên `LLM LTT`; phần ấy chạy trên **máy B** qua
  một đường deploy khác.
- **Một khoá Gemini ngoài kho** (`D:\FULL AUTO VIDEO\`) — **không** thuộc phạm vi
  chiến dịch. Ghi con trỏ vì *"đã gỡ Gemini"* rất dễ bị đọc thành *"máy này không
  còn khoá Gemini nào"*, và câu thứ hai **sai**.

### ⚠️ Một câu tôi viết SAI, và phiên `4bot` hỏi ngược đúng lúc

Tôi gọi bản vá khoá (`test_394`/`test_361`) là *"bản vá `tests/`, không đổi hành
vi sản phẩm"*. Họ hỏi ngược: **đúng với sản phẩm, sai với máy chủ — nếu ai đó
chạy bộ test trên chính máy production.**

Đo được, và câu trả lời là **CÓ**:

```
Test-Path C:\LTTPlatform  ->  True          (may nay LA may chu)
ba luot gate day du trong 12 gio qua, deu chay o day, deu do TOI chay
```

⇒ Trước bản vá, mỗi lượt ấy gọi `nha(ep=True)` trên **mọi khoá thật của máy
  chủ**. Nên nó **là** một bản vá hành vi trên máy này.

⭐ Và nó làm rõ một điều dễ quên: `D:\LTTSTUDIOSAPP` **vừa là cây phát triển
   vừa là nguồn deploy của máy chủ**. Mọi thứ ta chạy ở đây đều chạy *trên*
   production theo nghĩa vật lý — kể cả bộ test.

### Nghiệm thu deploy — ba chiều, và một chiều thứ tư do phiên ASV V6 đề nghị

```
[OK] Xuat commit 3b22503cc590: 3943 tep (nguon BAT BIEN)   <- di duong git archive
lech 0 · thieu 0 · THUA 0   ->  "khop tuyet doi mot commit xac dinh"
app\.claude False · app\.git False · app	est-results False · app	mp False
production  commit 3b22503cc590 · asset_ver 9b7ae80d · build 2026-09-10T10:18:13
```

⛔ `setup\2-cai-dat.ps1` có một **đường lui** (`$srcChep = $src`, dòng 248) chép
   **cây sống**, và danh sách `/XD` **không có `.claude`**. Nếu `git archive` hỏng,
   deploy sẽ chép **sáu worktree của sáu phiên** lên production — và **không đỏ ở
   đâu cả**: bản xuất vẫn đủ tệp, dịch vụ vẫn lên, `/health/version` vẫn đúng.

⭐ Giá trị của phép kiểm ấy không nằm ở việc nó bắt được gì hôm nay (đường bất
   biến đã chạy). Nó nằm ở chỗ: **thứ chỉ hỏng im lặng là loại duy nhất đáng
   dựng thêm một cửa riêng.**

⚠️ Không sửa `setup/` ngay trước một lượt deploy — đó là đổi một rủi ro **đã
   hiểu** lấy một rủi ro **chưa hiểu**.
