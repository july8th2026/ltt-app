# 00 — Audit charter: Agent AI launch

- **Chuẩn:** LTT-AQA v1.0 trong `docs/quy_tac_audit.md`.
- **Mức:** DEEP, audit độc lập sau thay đổi H17; không dùng điểm H16 làm kết luận.
- **Phạm vi:** `/agent`, `/agent/canvas`, palette/catalog, workflow document,
  node/edge/composer, quote/run/approval, history/share/assistant, responsive,
  accessibility, security/credit, scale, recovery và production readiness.
- **Benchmark:** PlenX Workflow quan sát hands-on ngày 2026-08-04; năng lực thị
  trường từ hồ sơ audit H16. Không đọc/lưu credential hay request bí mật.
- **Mục tiêu:** đủ chất lượng cho controlled launch, không chỉ giống ảnh tham
  khảo. Không sao chép nhận diện/IP hoặc lỗi typed-edge của PlenX.

## Acceptance

P0 = 0; G0–G8 PASS; Q ≥ 90; M ≥ 85; E ≥ 95; không page/toolbar overflow;
palette và Inspector đóng mặc định; connector ≥44 px; console/request bất ngờ
= 0; quote→approve→hold→settle không đổi; rollback có thể thực thi.
