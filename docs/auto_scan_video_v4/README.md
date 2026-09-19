# auto_scan_video_v4/ — TRA CỨU (V4 MVP, lớp ADR trên V2)

Tệp chủ: **`STATE_V4.md`** — SSOT bàn giao cho gói prompt V4, đọc SAU
`docs/auto_scan_video/STATE.md` (V2 — vẫn giữ nguyên, không bị thay). `adr/`,
`evidence/`, `reports/`, `prompts/` là hồ sơ từng bước của đợt V4.
`CAPABILITY_INVENTORY_V4.md` là bảng tra năng lực.

"V4 supersedes by ADR, never by deletion" — V4 KHÔNG xoá hay ghi đè tài liệu V2,
chỉ bổ sung quyết định mới. Ứng dụng sống: `apps/auto_scan_video/`.

`reports/` nhắc đường dẫn kho **bot cũ ngoài repo** (`nerf_engine/…`) và tệp gate
snapshot đã xoay vòng (`test-results/gates/*.json` theo timestamp) — không phải
tham chiếu vỡ, là ghi chép đúng lúc viết.
