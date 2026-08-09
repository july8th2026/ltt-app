# A7–A8 — Options và Decision Gate

| Option | Value | Coverage | Risk | TTV | Recommendation |
|---|---:|---:|---:|---:|---:|
| A REPAIR provider/context/money/data | 5 | 5 | 2 | 5 | 94/100 |
| B PARITY UX trước | 4 | 4 | 4 | 3 | 65/100 |
| C full agent/projects/tools | 5 | 5 | 5 | 1 | 51/100 |

**Khuyến nghị:** A → parity chọn lọc → LTT handoff. Không gắn thêm web search/vector/memory/tool tự trị vào nền shared account/recovery/credit chưa đúng.

| Decision | A — khuyến nghị | B | Hệ quả A |
|---|---|---|---|
| Provider commercial | OpenAI API/business account per contract | shared subscription | chi phí đo được, đúng customer app path |
| Conversation context | durable ChatRun + replay/fork/compaction | tin sidecar thread | branch/restart đúng |
| Image price | user chọn count/max và confirm | model tự phát ảnh | G3 minh bạch |
| One conversation concurrency | serialize/queue một active turn | cho song song | tránh context/money race |
| Q56 project | giữ conversation là project, thêm metadata UX | runtime project mới | không phá quyết định nền tảng |
| Files | transient/per-conversation với retention rõ | vector store ngay | giảm privacy/cost trước parity |
| Delete | export + reference-aware hard delete/TTL | DB-only | đáp ứng privacy thật |
| Rollout | internal canary→limited beta | public ngay | thu SLO/quality/cost evidence |

Không BUILD cho tới khi provider/auth/data/credit choices được khóa thành quyết định hiệu lực.
