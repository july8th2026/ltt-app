# A6 — Findings và root cause

| ID | Sev | Finding → root cause | Xử lý/acceptance |
|---|---|---|---|
| CHAT-01 | P0 | Ảnh settle vượt hold 3 → không reserve incremental | hold 20 trước từng ảnh; thiếu thì không giao; balance không âm |
| CHAT-02 | P1 | Partial output mất khi error/disconnect → chỉ save cuối vòng | save partial rồi settle; zero output refund |
| CHAT-03 | P1 | Locale lẫn + engine ID → literal và render model raw | catalog 0 missing/0 fuzzy; public label map |
| CHAT-04 | P2 | Header/title/credit stale sau send → SSE done thiếu receipt | done trả title/cost/balance/token; DOM cập nhật |
| CHAT-05 | P2 | Không dừng stream → fetch không signal | Stop + AbortController; finalizer backend giữ contract |
| CHAT-06 | P2 | Trace lượt khó đọc → token/timestamp không render | per-turn detail + lifecycle log + ledger correlation |
| CHAT-07 | P2 | Export kỹ thuật chiếm header | gom MD/JSON/branch trong menu thao tác |

Deferred: project knowledge/library, rename/pin/share, copy/retry response và
provider web search. Chỉ BUILD sau khi có yêu cầu, contract, privacy/cost và test.

