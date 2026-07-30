# LTTStudio project instructions

These instructions apply to the entire `BOT UP Facebook` project.

## Required context at the start of every session

Before planning or changing code:

1. Read `docs/PROJECT_MEMORY.md` completely.
2. Read the relevant phase in `docs/WEB_PLATFORM_PLAN.md`.
3. Inspect the current working tree. If Git is not initialized yet, record that fact instead of assuming a clean tree.
4. Inspect the files involved in the requested task before editing them.
5. Treat older files such as `docs/HANDOFF.md` and `docs/PROJECT_STATE.json` as historical references. For the web-platform migration, `docs/PROJECT_MEMORY.md` is the current source of truth.

## Product constraints

- The desktop CustomTkinter application remains the operational production path until a web phase explicitly passes its exit gate.
- Do not break or remove the desktop entry point while building the web platform.
- Reuse the existing `core/` publishing logic. Do not create a second independent Facebook/TikTok publishing implementation.
- Never allow the desktop runner and the web/server runner to process the same account, page, sheet tab, or job concurrently.
- The browser dashboard is a control plane. Long-running uploads and schedules must continue when the browser is closed.
- During the initial server architecture, run only one scheduler/orchestrator instance. Multiple web processes must not create duplicate schedulers.
- Do not deploy to the VPS or change production DNS unless the user explicitly requests that production action.

## Security rules

- Never put secret values, access tokens, refresh tokens, application secrets, relay secrets, service-account JSON contents, passwords, or private keys in documentation, Git, logs, tests, screenshots, or chat summaries.
- Documentation may record only the secret name, storage location, rotation status, and last verification date.
- Runtime secrets belong outside the source release and must be injected from a protected production secrets directory or environment variables.
- Before the first Git commit, verify that `secrets/`, runtime configs, config backups, token stores, databases, logs, and temporary videos are ignored.
- If a secret is found in tracked or documentation files, redact it and record the remediation in `docs/PROJECT_MEMORY.md` without copying the value.

## Change and test discipline

- Make the smallest coherent change for the active phase.
- Add or update tests for every behavior change.
- Preserve existing tests unless a documented product decision intentionally changes behavior.
- Do not mark a phase complete until every exit criterion in `docs/WEB_PLATFORM_PLAN.md` is satisfied.
- Record exact test commands and results in `docs/PROJECT_MEMORY.md`. Distinguish `collected`, `passed`, `failed`, and `not run`.
- For risky changes, define rollback steps before implementation.

## Memory update protocol

Update `docs/PROJECT_MEMORY.md`:

- after every completed implementation phase;
- after a material architecture or security decision;
- after discovering a blocker or important defect;
- after a deployment, rollback, credential rotation, or production incident;
- at the end of any session that changes code or project state.

Each update must include:

1. `Last updated` date and session summary.
2. Current phase and status.
3. Files materially changed.
4. Tests actually executed and their outcomes.
5. Decisions made and their rationale.
6. Known issues/blockers.
7. The next three concrete actions.

Never claim work was completed based only on a plan or test collection.

