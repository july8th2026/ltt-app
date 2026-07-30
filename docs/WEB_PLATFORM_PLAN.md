# LTTStudio Web Platform — Detailed Implementation Plan

## 1. Purpose

Build a browser-based LTT AI Studio control platform around the existing
Facebook/TikTok publishing core while preserving the working Windows desktop
application. Develop and verify the platform locally first, then publish a
versioned release to the existing Windows VPS.

This plan is the implementation roadmap. Current truth, progress, blockers, and
test outcomes belong in `PROJECT_MEMORY.md`.

## 2. Product outcomes

The first production web release must provide:

- authenticated LTT AI Studio dashboard;
- Facebook Bot and TikTok Bot modules;
- manual publishing workflows required from the desktop app;
- account and authorization management;
- Google Sheet/schedule worker control;
- job status, history, errors, and logs;
- background execution independent of browser sessions;
- automatic server startup and failure recovery;
- repeatable install, update, backup, restore, and rollback procedures;
- a platform shell that can accept additional tools later.

## 3. Non-goals for the first release

- Removing the desktop application.
- Running many worker replicas.
- Kubernetes or microservices.
- Rewriting the publishing engines.
- A public multi-tenant SaaS product.
- Billing/subscriptions.
- Mobile-native applications.
- Migrating every local historical record unless it is needed operationally.

## 4. Engineering principles

1. Preserve the known-good desktop path.
2. Separate user interface, application services, and platform integrations.
3. One source of truth for Facebook/TikTok publishing behavior.
4. No secret values in source control.
5. No phase is complete without test evidence.
6. Prefer reversible, incremental changes.
7. Prevent duplicate publishing before improving throughput.
8. Build release artifacts; do not edit production code directly on the VPS.
9. Keep production data outside versioned application releases.
10. Design module boundaries for future apps without prematurely building them.

## 5. Target logical architecture

```text
Browser
  |
  | HTTPS
  v
Caddy reverse proxy
  |
  | HTTP on 127.0.0.1
  v
FastAPI web application
  |-- authentication/session layer
  |-- dashboard and module routes
  |-- application service layer
  |-- worker/orchestrator lifecycle
  |
  +--> existing shared publishing core
  |      |-- Facebook API
  |      |-- TikTok API
  |      |-- Google Sheets/Drive API
  |
  +--> persistent runtime data
         |-- configuration
         |-- encrypted tokens
         |-- SQLite initially
         |-- logs/audit
         |-- temporary video cache
```

Initial release: one orchestrator process. Future scale: separate API and worker
only after a durable queue/state boundary exists.

## 6. Proposed source layout

```text
BOT UP Facebook/
|-- core/                         existing reusable domain/integration code
|-- gui/                          existing desktop UI
|-- server/
|   |-- app.py                    FastAPI factory
|   |-- settings.py               server-safe settings schema
|   |-- dependencies.py
|   |-- auth/
|   |-- routes/
|   |-- services/
|   |-- templates/
|   `-- static/
|-- deploy/
|   `-- windows/
|       |-- install.ps1
|       |-- update.ps1
|       |-- rollback.ps1
|       |-- backup.ps1
|       |-- restore.ps1
|       |-- Caddyfile.example
|       `-- service.xml.example
|-- tests/
|   |-- server/
|   `-- existing tests
|-- worker_main.py
|-- requirements-base.txt
|-- requirements-desktop.txt
|-- requirements-server.txt
`-- main.py                      preserved desktop entry point
```

Do not perform the full directory move at once. Introduce boundaries
incrementally to reduce regression risk.

## 7. Phase overview

| Phase | Focus | Primary deliverable |
|---|---|---|
| P0 | Governance and baseline | Clean, recoverable, testable starting point |
| P1 | Headless boundary | Worker lifecycle independent of GUI |
| P2 | Runtime boundary | Safe configuration, secrets, paths, and persistence |
| P3 | Web foundation | Authenticated dashboard shell |
| P4 | Facebook module | Facebook workflows on web |
| P5 | TikTok module | TikTok workflows on web |
| P6 | Scheduler control | Reliable always-on orchestration |
| P7 | Operations | Health, logging, backup, restore, recovery |
| P8 | Release candidate | Production-like local verification |
| P9 | VPS package | Repeatable Windows deployment |
| P10 | Launch | Controlled cutover and monitoring |
| P11 | Expansion | Multi-app platform and scale decisions |

---

## P0 — Governance, baseline, and secret hygiene

### Goal

Create a safe baseline before architecture changes.

### Tasks

- Create and maintain `AGENTS.md`, this plan, and `PROJECT_MEMORY.md`.
- Back up source, runtime data, token files, databases, and operational config.
- Verify that the backup can be listed/read; record location without secrets.
- Expand `.gitignore` for all runtime and sensitive files.
- Scan documentation and prospective source-controlled files for secret values.
- Redact discovered values; rotate compromised credentials externally.
- Confirm no credential value exists in fixtures or screenshots.
- Initialize Git only after the scan passes.
- Create a clean baseline commit/tag.
- Run the complete existing pytest suite.
- Run GUI smoke validation.
- Launch the desktop app and verify critical navigation.
- Document the known-good local run procedure and rollback point.

### Required tests

- `python -m pytest --collect-only -q`
- `python -m pytest tests -q`
- `python tests/gui_smoke_validator.py`
- Secret scan command documented without printing secret values.
- Manual desktop startup smoke check.

### Exit criteria

- Recoverable backup exists.
- Git boundary contains no runtime secrets/data.
- Previously exposed credentials are marked rotated/verified by the owner.
- Full test results are recorded accurately.
- Desktop operational baseline is known.
- `PROJECT_MEMORY.md` is updated.

### Rollback

Restore the pre-P0 backup; no application behavior should change in this phase.

---

## P1 — Headless core boundary

### Goal

Start, inspect, and stop publishing workers without importing or creating GUI
objects.

### Tasks

- Map GUI callbacks to explicit application-service interfaces.
- Introduce a `WorkerApplication` or equivalent lifecycle object.
- Define `start()`, `stop()`, `status()`, and graceful shutdown behavior.
- Inject log/status callbacks as optional adapters.
- Create a server-safe configuration loader independent of GUI widgets.
- Add `worker_main.py` as a CLI/headless entry point.
- Add signal/stop-event handling.
- Ensure download/upload cleanup occurs on controlled shutdown.
- Preserve GUI behavior by making GUI call the same service layer.
- Introduce a cross-mode ownership lock.
- Define stable job and worker status models.

### Required tests

- Importing `worker_main` does not import `customtkinter` or `gui.*`.
- Headless lifecycle unit tests.
- Start/stop idempotency tests.
- Crash and graceful shutdown tests.
- Ownership-lock conflict tests.
- Existing full regression suite.
- Desktop manual publish smoke test with safe/non-production fixture where
  possible.

### Exit criteria

- Headless worker runs locally from a console.
- Closing a controlling client does not stop the worker.
- Desktop and headless modes cannot own the same runner simultaneously.
- Desktop regression gate passes.
- Memory update records interfaces and changed files.

### Rollback

Keep `main.py` using the previous GUI wiring behind a temporary compatibility
adapter until the new lifecycle is proven.

---

## P2 — Runtime configuration, data, and security boundary

### Goal

Make the application portable between local development and Windows VPS without
copying secrets into source releases.

### Tasks

- Define environment profiles: development, local-server-test, production.
- Separate non-secret settings from secret values.
- Add an example configuration containing placeholders only.
- Resolve runtime paths through one path/settings service.
- Move production paths outside the release directory.
- Design the token-encryption migration:
  - option A: re-OAuth on VPS using the existing machine-bound method;
  - option B: external encryption key stored in protected secrets storage.
- Select and document the production approach before implementation.
- Add protected file permissions/ACL guidance for the Windows service account.
- Define SQLite connection settings, busy timeout, backup rules, and ownership.
- Add atomic configuration writes and schema/version validation.
- Add startup validation that reports missing configuration without exposing it.
- Define data retention for logs, audits, cache, and completed jobs.

### Required tests

- Development/production config precedence tests.
- Missing-secret and malformed-config tests.
- No-secret logging tests.
- Runtime path tests from a non-project working directory.
- Encryption/decryption and migration tests using synthetic keys/tokens.
- Atomic-write interruption tests.
- Existing full regression suite.

### Exit criteria

- A source-only release can start validation without any real secret.
- Production secrets can be injected without editing source files.
- Persistent data survives a simulated release replacement.
- Token migration/re-authorization strategy is approved and documented.

### Rollback

Maintain a compatibility reader for the existing `data/config.json` until the
new settings boundary is verified.

---

## P3 — Web platform foundation

### Goal

Provide an authenticated local LTT AI Studio dashboard with no publishing
behavior changes yet.

### Tasks

- Add FastAPI/Uvicorn server dependencies.
- Implement an application factory and startup/shutdown lifespan.
- Add `/health/live`, `/health/ready`, and version endpoints.
- Build the dashboard shell matching the intended LTT AI Studio navigation.
- Add Facebook Bot and TikTok Bot placeholder modules.
- Implement administrator authentication.
- Use secure password hashing; never store plaintext passwords.
- Add server-side sessions, secure cookie settings, logout, expiry, and rotation.
- Add CSRF protection for state-changing forms.
- Add basic rate limiting for login and sensitive endpoints.
- Add common error pages and request correlation IDs.
- Ensure the API binds to loopback during production proxy use.
- Add accessibility/responsive checks for desktop and mobile browser widths.

### Required tests

- Route/API tests.
- Authentication success/failure/logout/expiry tests.
- Authorization tests for protected routes.
- CSRF tests.
- Secure-cookie production configuration tests.
- Health/readiness tests.
- Browser smoke test for main navigation.
- Existing desktop regression suite.

### Exit criteria

- Dashboard works at localhost.
- Anonymous users cannot access protected pages.
- Browser closure has no effect on server lifecycle.
- No real publishing endpoint is exposed prematurely.
- Security review checklist passes.

### Rollback

Web package remains additive; desktop entry point is unchanged.

---

## P4 — Facebook web module

### Goal

Expose required Facebook workflows through the authenticated web dashboard.

### Tasks

- Inventory desktop Facebook features and classify must-have/deferred.
- Add Facebook account/page list and connection health.
- Implement server-side OAuth start/callback/state validation.
- Add account connect, refresh/test, page selection, and disconnect workflows.
- Add manual video/post form with validation and confirmation.
- Show upload progress, result, link, and sanitized error details.
- Add Facebook settings with secret fields never returned after save.
- Add history and audit views.
- Map every web action to the shared application service/core.
- Add idempotency keys for state-changing publish requests.
- Prevent double submission from refresh/double click.

### Required tests

- OAuth state/replay/error tests with mocked external API.
- Account/page mapping tests.
- Publish validation and idempotency tests.
- Token/error redaction tests.
- Progress/status serialization tests.
- Desktop-vs-web service parity tests.
- Controlled live smoke test only with explicit user authorization.

### Exit criteria

- All agreed P4 must-have Facebook workflows work locally.
- Web and desktop use the same publishing service implementation.
- No token/secret reaches browser HTML, API response, or logs.
- Duplicate-submit protection passes.

### Rollback

Disable the Facebook web module feature flag; desktop Facebook remains usable.

---

## P5 — TikTok web module

### Goal

Expose required TikTok workflows through the authenticated web dashboard while
preserving TikTok compliance behavior.

### Tasks

- Inventory desktop TikTok features and classify must-have/deferred.
- Implement TikTok account list, health, connect, refresh, and disconnect.
- Implement server-side OAuth callback and state validation.
- Add manual upload/direct-post/draft UI according to approved capabilities.
- Preserve creator-info, privacy, interaction, branded-content, and AI-content
  confirmations.
- Add progress polling and final publish status.
- Add TikTok settings with write-only secret behavior.
- Add history/audit/compliance views.
- Add idempotency and duplicate-submit protection.

### Required tests

- OAuth state/replay/error tests with mocked external API.
- Creator-info and privacy-option tests.
- Consent/compliance validation tests.
- Chunk upload/status polling tests.
- Error redaction tests.
- Idempotency tests.
- Desktop-vs-web service parity tests.
- Controlled live smoke test only with explicit user authorization.

### Exit criteria

- Agreed P5 TikTok workflows work locally.
- Compliance confirmations cannot be bypassed.
- Web and desktop share the same publisher service.
- No credential leakage is observed.

### Rollback

Disable the TikTok web module feature flag; desktop TikTok remains usable.

---

## P6 — Scheduler, job queue, and worker control

### Goal

Run scheduled publishing reliably without a browser or RDP session.

### Tasks

- Define job lifecycle states and allowed transitions.
- Implement start/stop/pause/drain controls.
- Make worker state visible in the dashboard.
- Persist sufficient state to recover after process/server restart.
- Add ownership lease/heartbeat and stale-owner recovery.
- Add job idempotency and duplicate-content guards.
- Reconcile Google Sheet state with local state after interruption.
- Add retry, backoff, cancellation, timeout, and dead-letter/error handling.
- Guarantee only one scheduler/orchestrator instance in release 1.
- Add controlled shutdown that stops accepting work before process exit.
- Add maintenance mode for updates/backups.

### Required tests

- Job state-machine tests.
- Restart/recovery tests.
- Ownership lease and stale-lock tests.
- Duplicate scheduler and duplicate job tests.
- Network loss and API timeout tests.
- Cancellation during download/upload/poll tests.
- Google Sheet reconciliation tests.
- Long-running local simulation/soak test.

### Exit criteria

- Worker survives browser disconnect.
- Worker resumes safely after process/server restart.
- Duplicate scheduling tests pass.
- Dashboard controls reflect true worker state.
- No job is silently lost.

### Rollback

Stop server runner and return ownership to the desktop runner using the documented
lock-release/recovery procedure.

---

## P7 — Observability, backup, and recovery

### Goal

Make failures diagnosable and data recoverable.

### Tasks

- Add structured application logs with correlation/job IDs.
- Add sensitive-data redaction at the logging boundary.
- Add health, readiness, worker heartbeat, disk-space, and queue-age metrics.
- Add dashboard system status and recent failure views.
- Define log rotation and retention.
- Add scheduled backup for databases, configuration, and required key material.
- Exclude disposable video cache from normal backup.
- Add restore script and test it into an isolated directory.
- Add failure recovery policies for Windows Services.
- Add optional notifications for repeated failures and token expiry.
- Create incident and recovery runbooks.

### Required tests

- Redaction tests.
- Log rotation test.
- Backup integrity test.
- Restore rehearsal.
- Low-disk/read-only-path tests.
- Service crash/restart simulation.
- Health/readiness failure-mode tests.

### Exit criteria

- Operator can identify why a job failed without RDP.
- Verified restore recovers application state.
- Service restart does not duplicate completed work.
- Retention and backup schedules are documented.

### Rollback

Disable optional monitoring integrations; retain core local logs and manual
backup procedure.

---

## P8 — Local production-like release candidate

### Goal

Prove the release on the development machine under production-like constraints.

### Tasks

- Build a clean source/release artifact excluding runtime data.
- Install it into a fresh staging directory.
- Create a fresh virtual environment from locked dependencies.
- Inject synthetic/staging configuration externally.
- Run behind local Caddy or an equivalent reverse-proxy rehearsal.
- Run with production flags: no reload, one orchestrator, secure settings.
- Reboot/restart rehearsal.
- Perform upgrade and rollback rehearsal.
- Run a multi-hour soak test with mocked/safe jobs.
- Verify desktop and web ownership exclusion.
- Complete release and security checklists.

### Required tests

- Clean-install test.
- Full automated suite.
- Browser end-to-end smoke suite.
- Upgrade and rollback tests.
- Backup/restore test.
- Restart and soak test.
- Dependency/security scan.
- Release artifact secret scan.

### Exit criteria

- Release installs without using the development `.venv`.
- No secret/runtime data exists in the artifact.
- Upgrade and rollback are proven.
- Soak test has no duplicate jobs or unrecovered crashes.
- Release candidate version is recorded in memory.

### Rollback

Delete only the isolated staging installation; the operational desktop directory
remains untouched.

---

## P9 — Windows VPS deployment package

### Goal

Create a repeatable, documented Windows Server installation without editing code
on the VPS.

### Tasks

- Confirm VPS Windows version, vCPU, RAM, disk, public IP, and backups.
- Create a dedicated low-privilege service account.
- Define `C:\LTTPlatform` application/data/secrets/logs/backups layout.
- Install supported Python and create per-app virtual environment.
- Install Caddy and configure it as a Windows Service.
- Install the LTT application through a service wrapper.
- Bind FastAPI to `127.0.0.1`.
- Configure Windows/Vultr firewall:
  - public 80/443;
  - RDP restricted to trusted administration IP/VPN;
  - no public database/application ports.
- Add DNS staging subdomain first.
- Configure protected production secrets.
- Configure service restart/recovery and delayed startup dependencies.
- Test install, update, rollback, uninstall, and reboot on staging.

### Required tests

- Service starts without interactive login.
- Service restarts after forced failure.
- Reboot test without RDP login.
- HTTPS/certificate test.
- Firewall/port exposure test.
- Health/readiness test.
- Backup and restore test on VPS staging.
- Update and rollback rehearsal.

### Exit criteria

- A new server can be installed from documented artifacts/scripts.
- No production code was edited manually on the VPS.
- Application runs after reboot without RDP.
- Only intended ports are public.
- Rollback completes within the defined recovery target.

### Rollback

Stop/disable new services, restore the prior release/data backup, and leave the
desktop application as the production publishing path.

---

## P10 — Controlled production launch

### Goal

Cut over publishing to the VPS safely.

### Tasks

- Schedule a maintenance/cutover window.
- Stop desktop runners and verify ownership is released.
- Back up desktop and VPS state.
- Deploy approved release.
- Configure final `app.lttstudios.com` DNS/HTTPS.
- Perform Facebook/TikTok OAuth on the VPS dashboard as required.
- Run health and account-connection checks.
- Run one controlled Facebook job and one controlled TikTok job.
- Verify links, history, audit, Sheet updates, and no duplication.
- Monitor worker heartbeat/errors/resource usage.
- Keep desktop application available but runner-disabled as rollback.
- Document the final operating procedure.

### Required tests

- Post-deployment smoke checklist.
- Controlled live job checks with explicit authorization.
- Browser logout/close test while worker continues.
- VPS reboot test.
- Backup verification.
- Security exposure review.

### Exit criteria

- Authorized jobs complete correctly on both platforms.
- No RDP session is required for normal operation.
- Operator can start/stop/view jobs through the dashboard.
- Monitoring and backup are active.
- Rollback window completes without incident.

### Rollback

Stop VPS worker, release ownership, restore/enable desktop runner, and revert DNS
only if required for dashboard access.

---

## P11 — Multi-application platform evolution

Start only after the first production release is stable.

### Decision triggers

- More than one independent application is ready.
- More than one worker process is required.
- SQLite contention or reporting needs justify PostgreSQL.
- Queue durability/throughput justifies Redis/RabbitMQ or another broker.
- Windows operational overhead justifies a Linux/Docker migration.

### Candidate work

- Extract common identity, navigation, jobs, notifications, and audit modules.
- Give each app its own service, virtual environment, loopback port, and data
  boundary.
- Use one Caddy instance to route subdomains.
- Introduce PostgreSQL with a database/user per application.
- Introduce a durable queue only after workload measurements.
- Add roles/permissions if more administrators are needed.
- Evaluate Linux VPS and Docker Compose using measured operational needs.

## 8. Definition of done for every phase

A phase is done only when:

- scope tasks are completed or explicitly deferred with rationale;
- code review/self-review is complete;
- required automated tests pass;
- required manual checks are recorded;
- no new secret exposure exists;
- desktop regression status is known;
- rollback steps are verified or rehearsed as required;
- `PROJECT_MEMORY.md` is updated with exact evidence;
- the next phase's first three actions are identified.

## 9. Release versioning

Use semantic versions after Git initialization:

- `0.x`: local web development.
- `0.8.x`: local release candidates.
- `0.9.x`: VPS staging releases.
- `1.0.0-web`: first stable VPS dashboard/worker release.

Every release record must include commit/tag, artifact checksum, database/config
schema version, test result, deployment date, and rollback target. Never include
credentials.

## 10. Memory and session continuity

At the start of a session:

1. Read `AGENTS.md`.
2. Read `PROJECT_MEMORY.md`.
3. Read the active phase here.
4. Inspect working-tree state.
5. Verify assumptions before changing code.

At the end of a material session:

1. Update current phase status.
2. Record changed files and behavior.
3. Record exact tests and outcomes.
4. Record decisions, risks, and rollback.
5. Set the next three concrete actions.

The memory file records truth. This plan records intent. If they conflict, stop,
inspect the repository, and correct the memory using evidence.

