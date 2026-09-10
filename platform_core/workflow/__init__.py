"""LTT WORKFLOW V2 — lớp định nghĩa và thi hành workflow.

Tách khỏi `platform_core/agent/` có chủ ý: `agent/` gắn với Plan v1, nơi một
hàng `agent_workflows` trộn bản-đang-soạn, bản-đang-chạy và phóng chiếu thi
hành. Xem `docs/architecture/workflow_v2_audit/30_QUYET_DINH_KIEN_TRUC_CUOI_CUNG.md`
(`ADR-WF-001`).

⛔ Chưa nối vào đường chạy nào. Đợt 2 chỉ dựng lược đồ + service + test.
"""
