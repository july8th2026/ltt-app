# Data Retention Policy

> P2 deliverable ("Define data retention for logs, audits, cache, and
> completed jobs"). Documents what already runs today, plus known gaps
> flagged for a later phase. No secret values appear in this file.

## Summary table

| Data category | Location | Retention mechanism | Default period |
|---|---|---|---|
| Application logs | `logs/*.log` | `RotatingFileHandler` (size-based) in `utils/logger.py` | 5 MB per file, 3 backups kept |
| Audit log | `data/audit_log.jsonl` | Rotation in `utils/audit_logger.py` | `_MAX_BACKUPS = 5` (`.jsonl.1` .. `.jsonl.5`) |
| Content-history dedup DB | `data/content_history.db` (SQLite) | `MaintenanceDaemon._do_sweep()` calls `purge_older_than()` hourly | `anti_spam_retention_days` config key (has a built-in default; see `core/maintenance.py::_DEFAULT_RETENTION`) |
| Temporary downloaded videos | `temp_videos/` | Deleted immediately after a successful upload | Controlled by `delete_video_after_upload` config key, default `True` |
| Video-variation scratch files | `temp_videos/` (varied copies) | `core/video_variation.cleanup_varied_tmp()`, run by `MaintenanceDaemon` | `older_than_hours=24` |
| Retry state | `data/retry_<sheet>_<tab>.json` | In-memory entries older than 1 h are discarded on load (`SheetRunner._load_retry_state`) | 1 hour for *entries*; the file itself is not deleted (see Known gaps) |
| Session ownership locks | `data/session_locks/*.lock` | TTL-based staleness check (`SessionLock.is_stale`), reclaimed on next `acquire()` for the same target | 5 minutes; the file itself is not proactively deleted until reclaimed (see Known gaps) |
| Encrypted OAuth tokens | `data/tokens.enc`, `data/tiktok_tokens.enc` | No automatic expiry — tokens live until the account is disconnected or the file is deleted | Indefinite (by design — these are credentials, not disposable data) |
| Completed job records | Google Sheet rows (external, not local storage) | Managed by the sheet owner, outside this application's retention scope | N/A |

## Backup scope (cross-reference: P7)

Per `AGENTS.md` and `WEB_PLATFORM_PLAN.md` P7, scheduled backups must cover
databases, configuration, and required key material, and must **exclude**
the disposable video cache. Given the table above, a P7 backup job should
include:

- `data/config.json` (or its environment-resolved path per `core/runtime_paths.py`)
- `data/tokens.enc`, `data/tiktok_tokens.enc`
- `data/content_history.db`
- `data/audit_log.jsonl` (current + rotated backups)

and exclude:

- `temp_videos/`
- `data/session_locks/`
- `logs/` (operational, not authoritative — recreated automatically)

## Known gaps (not fixed in this pass — flagged for a follow-up)

1. **Stale `retry_*.json` files are never deleted**, only their in-memory
   entries expire on load. A sheet tab that is removed leaves an orphaned
   retry-state file behind indefinitely. Low impact (small JSON files,
   bounded by number of sheet tabs ever configured) but should be swept by
   a future `MaintenanceDaemon` task.
2. **Stale `session_locks/*.lock` files are not proactively deleted**,
   only reclaimed the next time something tries to acquire that same
   target. A target that is never retried again (e.g., a page removed
   from rotation) leaves its lock file behind indefinitely. Same low-impact
   profile as above.

Neither gap affects correctness (both are already handled safely at
*read* time — stale entries/locks are simply ignored/reclaimed) or
security (no secret material in either file). Fixing them is a small,
independent `MaintenanceDaemon` addition better scoped as its own change
than bundled into the P2 runtime-boundary work.

## Change history

- 2026-07-29 — Initial policy documented against the current (P2) codebase
  state. No code changed as part of writing this document.
