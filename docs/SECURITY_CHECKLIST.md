# Security Checklist — Web Dashboard

> P3 exit-criterion artifact. Each control lists how to verify it, so this
> is a checklist someone can actually run, not a list of claims.
> No secret value appears in this file.

## Legend

- **Implemented** — control exists and is covered by an automated test.
- **Deferred** — deliberately not done yet, with the reason.

---

## 1. Authentication

| # | Control | Status | Verify |
|---|---|---|---|
| 1.1 | Passwords stored as PBKDF2-HMAC-SHA256, 600k iterations, per-password random salt | Implemented | `pytest tests/test_37_p3_web_foundation.py -k password` |
| 1.2 | No plaintext password is ever stored or logged | Implemented | `test_password_hash_never_contains_plaintext` |
| 1.3 | Password verification is constant-time (`hmac.compare_digest`) | Implemented | `server/auth/password_hashing.py::verify_password` |
| 1.4 | Malformed/foreign hash fails closed (returns False, never raises) | Implemented | `test_verify_password_fails_closed_on_malformed_hash` |
| 1.5 | No default/fallback admin password ships in the codebase | Implemented | `server/settings.py` — dev mode leaves the hash empty, so nobody can log in rather than granting a known credential |
| 1.6 | Production refuses to start without explicit admin + session secrets | Implemented | `test_production_env_requires_explicit_secrets` |
| 1.7 | Operator can generate a hash without writing the plaintext anywhere | Implemented | `python tools/hash_admin_password.py` (uses `getpass`) |

## 2. Session management

| # | Control | Status | Verify |
|---|---|---|---|
| 2.1 | Session cookie is signed (`itsdangerous` via `SessionMiddleware`) | Implemented | `server/app.py` |
| 2.2 | Cookie is `HttpOnly` | Implemented | `test_secure_cookie_flag_set_outside_development` |
| 2.3 | Cookie is `Secure` outside development | Implemented | same test |
| 2.4 | `SameSite=lax` | Implemented | `server/app.py` |
| 2.5 | Session has an expiry (8h) | Implemented | `SESSION_MAX_AGE_SECONDS` |
| 2.6 | Pre-auth session state is cleared on login (session-fixation mitigation) | Implemented | `server/auth/session.py::log_in` |
| 2.7 | Logout clears the session | Implemented | `test_login_success_then_dashboard_then_logout` |
| 2.8 | Server-side revocable sessions | **Deferred** | Starlette sessions are client-side cookies; there is no server-side session ID to revoke. Accepted for a single-admin dashboard (ADR-011: no Redis/DB in release 1). Rotating `LTT_SESSION_SECRET` invalidates all sessions as the blunt-instrument fallback. |

## 3. CSRF

| # | Control | Status | Verify |
|---|---|---|---|
| 3.1 | Synchronizer token on state-changing form POSTs | Implemented | `server/auth/csrf.py` |
| 3.2 | Token compared in constant time | Implemented | `verify_csrf_token` uses `hmac.compare_digest` |
| 3.3 | Missing/incorrect token rejected with 400 | Implemented | `test_login_post_without_csrf_token_is_rejected` |
| 3.4 | CSRF on `/logout` | **Deferred** | `/logout` is POST-only and its only effect is clearing the attacker-uncontrolled session. Forced logout is a nuisance, not a compromise. Worth adding when more POST routes exist (P4). |

## 4. Rate limiting / brute force

| # | Control | Status | Verify |
|---|---|---|---|
| 4.1 | Login limited to 5 attempts / 60s per client | Implemented | `test_login_rate_limited_after_repeated_failures` |
| 4.2 | Successful login resets the counter | Implemented | `test_rate_limiter_unit_allows_then_blocks_then_resets` |
| 4.3 | Limiter state is per-application, not module-global | Implemented | `app.state.login_rate_limiter` — a module-level limiter leaked counters between app instances |
| 4.4 | Distributed/persistent rate limiting | **Deferred** | In-memory by design (ADR-011). A restart clears counters; acceptable for a single-operator dashboard, not for a public service. |

## 5. Network exposure

| # | Control | Status | Verify |
|---|---|---|---|
| 5.1 | App binds `127.0.0.1` by default | Implemented | `server/run.py` |
| 5.2 | Public traffic terminates at the reverse proxy (80/443 only) | **Deferred to P9** | Caddy is not deployed yet (ADR-007). |
| 5.3 | No database/app port exposed publicly | **Deferred to P9** | Firewall configuration is a deployment task. |

## 6. Secret handling

| # | Control | Status | Verify |
|---|---|---|---|
| 6.1 | No secret value in source control | Implemented | `python tools/scan_source_secrets.py` → 0 findings |
| 6.2 | Secrets injected from environment, never edited into source | Implemented | `server/settings.py`, `platform_core/runtime_paths.py` |
| 6.3 | Config validation errors never echo secret values | Implemented | `test_load_settings_invalid_config_raises_config_validation_error_no_secret_leak` |
| 6.4 | Token-store failures never print token material | Implemented | `test_unreadable_message_never_contains_token_material`, `test_doctor_output_contains_no_token_material` |
| 6.5 | Logs redact bearer/access/refresh tokens and client secrets | Implemented | `utils/logger.py::_REDACT_RULES` |
| 6.6 | Example config contains placeholders only | Implemented | `test_example_config_has_zero_secret_scanner_findings` |

## 7. Error handling / information disclosure

| # | Control | Status | Verify |
|---|---|---|---|
| 7.1 | Error pages show a generic message, not a stack trace | Implemented | `server/app.py` error handler + `templates/error.html` |
| 7.2 | Each response carries a correlation ID for support without exposing internals | Implemented | `test_error_page_includes_correlation_id` |
| 7.3 | Health endpoints stay machine-readable (JSON) for probes | Implemented | `test_health_errors_stay_json_for_machine_probes` |

## 8. Authorization

| # | Control | Status | Verify |
|---|---|---|---|
| 8.1 | Dashboard requires login | Implemented | `test_anonymous_dashboard_access_redirects_to_login` |
| 8.2 | `/status` requires login | Implemented | `test_status_page_requires_login` |
| 8.3 | Health endpoints intentionally unauthenticated | Implemented (by design) | Probed by the proxy/service manager; they expose only up/ready state and a version string. |
| 8.4 | Role-based access control | **Deferred** | Single-administrator model in release 1 (P11 candidate work). |

---

## Not yet verified

- **No external security review** has been performed. Everything above is
  self-assessment plus automated tests.
- **No accessibility/responsive audit at real browser widths** — templates
  use a responsive viewport and relative widths, but this has not been
  checked in a real browser (no browser-automation tool available in the
  implementing session).
- **No dependency vulnerability scan** — scheduled for P8
  ("Dependency/security scan").

## Re-run everything

```bash
python -m pytest tests/test_37_p3_web_foundation.py -q   # web security tests
python tools/scan_source_secrets.py                      # secret boundary
python tools/doctor.py                                   # runtime health
```
