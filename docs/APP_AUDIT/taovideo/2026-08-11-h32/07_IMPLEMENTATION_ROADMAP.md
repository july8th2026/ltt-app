# H32.5 — Implementation roadmap

| Phase | Scope | PASS gate | Status |
|---|---|---|---|
| UI-0 | Composer dock, density, i18n status/title | desktop VI/EN clean | DONE |
| UI-1 | Mobile inert/close/focus/no overflow | keyboard 390×844 | DONE |
| UI-2 | Asset disclosure, compact filters, grid/list/empty | browser state matrix | DONE |
| UI-3 | Honest estimate loading/failure | 500 khóa CTA, 200 mở lại | DONE |
| R0 | Cap charge + canonical quote + stable idempotency | G3 PASS, balance không âm | PENDING BLOCKER |
| R1 | Upload staging/TTL/sniff/stream/audio contract | G2/G5 PASS | PENDING |
| R2 | Remix giữ refs/count; per-item reference manager | browser/API regression | PENDING |
| R3 | Live polling, cancel/retry, cursor history/delete | recovery task test | PENDING |
| R4 | Remote asset registry/reconcile/quota/lifecycle | G8/dry-run PASS | PENDING |
| R5 | Provider matrix + blind quality + production SLO | G1/G7/E≥85 | PENDING |

Không chạy R0–R5 trong H32.5 vì MoTa khóa visual-only. Khi mở lại, thứ tự bắt
buộc là R0 → R1 → R2 → R3 → R4 → R5; không thêm edit/extend trước P0/P1.
