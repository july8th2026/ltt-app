# 05 — Findings

Tổng: **0 P0 · 2 P1 · 8 P2 · 3 P3**.

| ID | Sev | Finding/root cause | Acceptance |
|---|---|---|---|
| TXT-001 | P1 | literal Text trong Agent bị ánh xạ thành paid generation | input manual không tạo job/không credit |
| TXT-002 | P1 | run orchestration có thể submit trùng (Agent P0) | đúng một child/idempotent tick |
| TXT-003 | P2 | JSON chỉ là prompt instruction | schema validate + actionable error |
| TXT-004 | P2 | không cooperative cancel/stream | cancel provider/job rõ |
| TXT-005 | P2 | single Gemini/no fallback contract | provider policy + evidence |
| TXT-006 | P2 | một job type dispatch bằng presence key | operation discriminator/schema strict |
| TXT-007 | P2 | quote modality dựa field presence, artifact metadata mỏng | canonical admission/receipt |
| TXT-008 | P2 | citations/source provenance không cấu trúc | provenance output |
| TXT-009 | P2 | legacy project migration UX không có | retention/migration rule |
| TXT-010 | P2 | SLO/output eval UNKNOWN | eval set + P50/P95 |
| TXT-011–013 | P3 | copy/i18n/a11y integration | polish sau blocker |

