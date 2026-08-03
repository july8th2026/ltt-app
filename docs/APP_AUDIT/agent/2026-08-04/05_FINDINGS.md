# 05 — Findings

| ID | Sev | Hiện tượng/root cause | Ảnh hưởng | Quyết định/acceptance |
|---|---|---|---|---|
| AG-01 | P1 | Canvas v1 chỉ có tool node/edge/viewport | không thể page/frame/note/comment/version | Canvas Document v2 lossless + migration v1→v2 |
| AG-02 | P1 | 7 ToolSpec, thiếu 5 node active tương đương | parity workflow media không đạt | thêm generic text/audio/batch/extract/merge/social/image upscale theo gate |
| AG-03 | P1 | `video.generate` khóa BytePlus dù registry có PlenX | provider/model nội tại không đi tới Canvas | capability-driven provider routing; không hardcode JSX |
| AG-04 | P1 | Inspector tách khỏi node; card không composer | nhiều eye travel, khó hiểu model/cost | inline compact composer + Inspector nâng cao |
| AG-05 | P1 | chỉ chạy full workflow | iteration chậm/tốn, không parity frame/node | quote/run selection với upstream closure và artifact cache |
| AG-06 | P1 | assistant one-shot, không chat/pattern/RAG | không phân tích/cải thiện có vòng tương tác | workflow assistant SSE, tool-call schema, preview diff trước apply |
| AG-07 | P1 | chưa editor version history | autosave sai khó khôi phục | coalesced snapshots, diff, restore-as-new, retention |
| AG-08 | P1 | chưa share/ACL/revoke | thiếu collaboration/clone | private by default, view/clone roles, revoke, audit, rate-limit |
| AG-09 | P2 | auto layout đơn giản | graph lớn khó đọc | layered DAG layout, disconnected packing, frame-aware layout |
| AG-10 | P2 | model schema chưa đủ quality/mode/server/pricing | UI không phản ánh capability thực | unified ModelCapability v2 + price preview endpoint |
| AG-11 | P2 | mobile ≤640 chỉ xem | journey mobile không đầy đủ | khóa scope mobile; tối thiểu inspect/approve/run/artifact |
| AG-12 | P2 · RESOLVED | 64 KiB/32 steps chặn workflow lớn | workflow thương mại lớn không lưu được | Canvas 512 KiB, Plan 100 bước; backend/frontend benchmark 100 node PASS, planner vẫn 64 KiB |
| AG-13 | P2 | run/history/artifact phân tán | khó debug | unified activity drawer per workflow/node/frame |
| AG-14 | P2 | chưa input asset node/library | refs vẫn là field kỹ thuật | typed Asset node + R2 picker/upload/provenance |
| AG-15 | P3 | thiếu shortcut/help/layers/note/comment polish | efficiency/collaboration thấp | phase collaboration, không chặn core parity |

## Root cause tổng

P0–P13 trước đây tối ưu đúng cho **engine an toàn và executable**, nhưng scope “node editor đầy đủ” được chốt theo Plan v1/7 tool, không theo product surface hiện tại của PlenX. Vì vậy code không hỏng; chuẩn đích đã cao hơn baseline cũ.

## Guardrails

- Không copy edge validation lỏng, flash empty, misleading cost/default, auto-layout một cột hoặc share side effect của PlenX.
- Không tải model/binary mới chỉ để “đủ danh sách”; mỗi provider phải qua license, API availability, quality/cost benchmark và rollback.
- Không sửa `platform_core` vòng vo. Capability mới ở app manifest; chỉ mở rộng contract nền tảng khi nhiều app/tool thực sự cần và có quyết định kiến trúc.
