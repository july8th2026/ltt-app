# 07 — Implementation Roadmap

| Phase | Scope | PASS gate | Status |
|---|---|---|---|
| H26.10C | Re-audit Agent customer flow + Socialbot maintenance | Browser desktop/mobile + targeted tests | PASS |
| H26.11A | Retention/privacy/log redaction | Customer 365d, debug 30d, raw log operator-only | NEXT |
| H26.11B | SLO/load/soak | Budget khóa trước; P50/P95/error artifact | PENDING |
| H26.11C | Failure recovery | timeout/cancel/retry/orphan/refund drill | PENDING |
| H26.12 | Full gate/browser A–Z/backup/rollback/canary/deploy | G0–G8 + evidence production | PENDING |

Rollback H26.10C không cần code rollback vì audit không đổi runtime Agent.
Release vẫn bị chặn cho đến khi H26.11–12 PASS.
