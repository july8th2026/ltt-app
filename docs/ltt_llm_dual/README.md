# LTT LLM Dual-Model — mục lục

Chương trình hợp nhất di sản **Multi-Job** (nhánh `claude/ltt-llm-multijob-audit-43efd3`) với kiến trúc **hai model**:
LTT-3.8 (Qwen3.8-27B, RTX 3090, chia với model ảnh) và LTT-3.5 (Qwen3.5-9B, RTX 5060 Ti).

| Tệp | Nội dung |
|---|---|
| `00_CURRENT_BASELINE.md` | Gate R0/R2/R3 — git, máy B, engine, model, hash (ảnh chụp 2026-09-11) |
| `01_MULTI_JOB_INHERITANCE.md` | Gate R1 — phân loại từng phần Multi-Job |
| `02_REQUEST_TRACE.md` | Đường request, hợp đồng model, tiền, hủy, đầu vào (máy A) |
| `03_GPU_RESOURCE_MAP.md` | Giả định GPU trong mã + trọng tài ComfyUI↔LLM đang sống |
| `05_COMMUNITY_EVIDENCE.md` | Gate R4 — llama.cpp b10883, llama-swap v250, Qwen3.5-9B, Docling, kho ấm RAM |
| `06_GAP_ANALYSIS.md` | Gate R5 — CURRENT → TARGET → GAP → REUSE → CHANGE → TEST |
| `DECISION_LOG.md` | **Nguồn chân lý của quyết định** (D01–D08, L-*, TD-*) |
| WIP Task 9 Multi-Job | Đã đối soát vào `CMC_SOURCE_STATE.md`; patch lưu trữ không được đưa vào lịch sử canonical |
| **Spec 1** | `docs/superpowers/specs/2026-09-11-ltt-llm-dual-model-design.md` — kiến trúc, nghiệm thu, rollback |

Spec 2 (Input Intelligence MVP) và implementation plan: chưa viết (chờ duyệt Spec 1).
