# 03 — Competitor benchmark

Snapshot 2026-08-09 theo node text/multimodal dành cho customer, tham chiếu
FLORA/PlenX workflow, n8n AI nodes, Make AI modules và OpenAI/Google model UX.

| Capability | Loại | LTT 0–3 | Baseline | Quyết định |
|---|---|---:|---:|---|
| literal text input 0-cost | TABLE_STAKES | 0 | 3 | FIX integration |
| prompt → text | TABLE_STAKES | 2 | 3 | KEEP/FIX |
| image/video → analysis | TABLE_STAKES | 2 | 2 | KEEP |
| streaming/cancel | TABLE_STAKES | 0 | 2 | BUILD |
| structured output schema | TABLE_STAKES | 1 | 2 | EXTEND |
| provider/model fallback | DIFFERENTIATOR | 0 | 2 | DEFER/BUILD chọn lọc |
| source/citation grounding | DIFFERENTIATOR | 1 | 2 | EXTEND |
| dev-oriented prompt fragments UI | ANTI_FEATURE | — | — | REJECT customer |

**M50.** Core multimodal có thật nhưng interaction contract và control thấp hơn
baseline workflow customer.

