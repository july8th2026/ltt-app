# 03 — Competitor benchmark

Snapshot 2026-08-09, cùng JTBD social publishing/operations. Nguồn ưu tiên tài
liệu chính thức: Meta Business Suite (schedule, planner, edit/duplicate/
reschedule/draft/delete, insights), TikTok Studio, Buffer (draft/approval/role),
Hootsuite, Later, Sprout Social và Metricool.

| Capability | Loại | LTT | Baseline thị trường | Quyết định |
|---|---|---:|---:|---|
| Kết nối FB/TikTok | TABLE_STAKES | 2 | 2 | KEEP nội bộ |
| Lập lịch/queue | TABLE_STAKES | 2 | 3 | FIX maintenance |
| Draft → review → approval theo role | TABLE_STAKES | 0 | 3 | DEFER theo Q10 |
| Calendar/list + edit/reschedule | TABLE_STAKES | 1 | 3 | DEFER |
| Multi-account ownership/RBAC | TABLE_STAKES | 0 | 3 | **FIX security** |
| History/audit actor/action | TABLE_STAKES | 1 | 3 | FIX |
| Retry/recovery/idempotency rõ | TABLE_STAKES | 1 | 3 | FIX |
| Analytics/insight | DIFFERENTIATOR | 1 | 3 | DEFER |
| Google Sheet ingestion | NICHE | 3 | 1 | KEEP nếu operator còn dùng |
| Customer tự dán token global | ANTI_FEATURE | 0 | — | REJECT |

**M35.** Điểm thấp không cấp quyền mở rộng feature; ưu tiên duy nhất là khóa
ranh giới operator và duy trì chức năng đang dùng.

Nguồn: https://www.facebook.com/help/389849807718635 ·
https://www.facebook.com/help/131809553587433 ·
https://support.buffer.com/article/665-managing-and-approving-draft-posts

