# A6 — Findings

## P1 (7)

| ID | Finding → root cause/impact | Acceptance |
|---|---|---|
| CHAT-P1-01 | Shared ChatGPT/Codex subscription powers paying end users; repo has no commercial/data-processing authorization. Consumer subscription and API billing are separate; account policy is individual. | use API/business contract or written authorization; document DPA/retention/abuse/quota |
| CHAT-P1-02 | Branch clones display DB only; new sidecar thread gets no history. Lost/invalid thread also cannot rebuild. | provider fork or deterministic replay/compaction; branch/restart golden context tests |
| CHAT-P1-03 | Turn may cost 3–83 credit based on unsolicited sidecar image count, without max quote/count confirm. | user selects/approves cap; atomic hold max; settle/refund receipt |
| CHAT-P1-04 | Stop/error after partial settles but response/UI lacks actual receipt; process crash can orphan hold because turn has no Job/reconciler. | durable ChatRun state, idempotency key, terminal reconciliation and all-path receipt |
| CHAT-P1-05 | Concurrent/duplicate sends share one thread with no serialization/idempotency; can double charge and scramble context. | one active turn/conv or ordered queue; request id; race tests |
| CHAT-P1-06 | Delete removes DB only; browser proved image remains, remote thread also undeleted. Text/file retention policy and self-service purge absent. | reference-aware Storage/thread purge, TTL/export/delete audit; branch-safe GC |
| CHAT-P1-07 | Sidecar image `abs_path` opened/read unbounded without allowed-root/content validation. | signed/structured output handle; root allowlist, byte/magic/pixel validation, no arbitrary path |

## P2 (17)

1. No server-side per-turn deadline/cancel RPC; sidecar HTTP timeout is unlimited.
2. No per-user/provider concurrency/rate limit or backpressure; shared quota is single point.
3. “AI sẵn sàng” checks account only, not quota/rate-limit/model/latency readiness.
4. Page can synchronously wait on account/models calls with long timeouts when sidecar hangs.
5. Assistant output is plain text; Markdown, code, table, links and citations are unusable.
6. No copy, regenerate, edit prompt/response, feedback or branch-from-message.
7. Live attachment message differs after reload; extracted file content unexpectedly expands in transcript.
8. Privacy note does not clearly disclose storage/search/export/retention of extracted text/PDF.
9. Upload is read fully before cap; PDF extraction/page/decompression workload lacks explicit budget.
10. Conversation list capped 100 without pagination; no rename, pin, archive or grouping.
11. Server accepts free-typed model value on `/new`; no allowlist/capability validation.
12. Custom instructions exist in DB/API but customer UI cannot view/edit them.
13. Export omits actual image/file bundle and returns internal `image_key` in JSON.
14. Error during thread creation exposes raw sidecar exception in customer SSE.
15. Live title updates text but delete button aria-label remains stale until reload.
16. Mobile has no collapsible conversation drawer; long sidebar grows before current thread.
17. English route retains Vietnamese top-navigation groups, breaking locale consistency.

## P3 (5)

1. Suggestions are only three static prompts and not contextual.
2. No message-level cost estimate before Enter, only compact rate copy in header.
3. Token detail is dev-centric and more prominent than source/quality/useful actions.
4. Search does not cover image prompt/file metadata consistently.
5. No notification when a long answer completes after tab loses focus.

Total: **0 P0 · 7 P1 · 17 P2 · 5 P3**. Unknown commercial permission is treated as release blocker, not asserted as a proven legal violation.
