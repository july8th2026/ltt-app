# 00 — Audit Charter: LTT Agent AI ↔ PlenX Workflow

**Mã hồ sơ:** AG-DEEP-2026-08-04  
**Chuẩn:** LTT-AQA v1.0  
**Mode:** DEEP có giới hạn (browser hands-on PlenX + browser local + code); chưa chạy provider trả phí, load test, user test hoặc full suite.  
**Ngày snapshot:** 2026-08-04 (Asia/Saigon)

## Mục tiêu

Đối soát app `agent` hiện hành với Workflow của PlenX để lập lộ trình đạt **100% functional parity có chọn lọc**: đủ capability và journey hữu ích, không sao chép lỗi, nhận diện thương hiệu, bí mật triển khai hoặc hành vi làm yếu ownership/credit/security của LTT.

## Phạm vi

- PlenX: tạo workflow thật, node active, page, frame, sticky note, comment, history, share, logs, assistant, model/voice composer, autosave và kết nối node.
- LTT: `apps/agent/`, `frontend/agent-canvas/`, `platform_core/agent/`, 7 ToolSpec, provider/model registry, API workflow/run/credit và giao diện local render thật.
- Không tiêu credit PlenX; không generate media; không đọc cookie/localStorage/header bí mật; không sửa code hoặc deploy trong vòng audit này.
- Workflow audit đã tạo trên PlenX: `LTT Audit Workflow 2026-08-04`; chia sẻ đã được tắt sau khi kiểm tra modal.

## Persona và JTBD

1. Creator mới: mô tả mục tiêu và nhận workflow hợp lệ nhanh.
2. Creator chuyên nghiệp: tự dựng/chỉnh DAG, cấu hình model, chạy lại một phần và quản lý artifact.
3. Operator/owner: kiểm soát giá, provider, lỗi, lịch sử, quyền chia sẻ và khả năng khôi phục.

## Tiêu chuẩn đích

- Functional parity: 100% capability đã khóa trong ma trận, không phải sao chép pixel/IP hoặc bug.
- Mọi node có typed ports, schema model, quote, approval, state, artifact, retry/cancel và telemetry.
- Desktop immersive canvas; responsive tablet; mobile tối thiểu xem/chạy/duyệt an toàn, chỉnh sửa đầy đủ là quyết định riêng.
- Giữ lợi thế LTT: validator tất định, quote/approve/hold/settle, tenant ownership, bounded retry và restore.

## Bằng chứng

| ID | Cấp | Nguồn |
|---|---|---|
| E-PLX-01 | E3 | Browser đăng nhập PlenX, workflow mới, 1720×940 |
| E-LTT-01 | E3 | Browser local `/agent/canvas`, 1720×940 |
| E-CODE-01 | E1 | Source `frontend/agent-canvas`, `apps/agent`, `platform_core/agent` |
| E-TOOL-01 | E1 | 7 manifest ToolSpec và `platform_core/providers.py` |
| E-DOC-01 | E1 | Q39–Q43/Q49, `AGENT_LTT/`, khảo sát PlenX lịch sử |

## PASS audit

- Inventory node/control/model/resource có verdict.
- Gap có severity, root cause và acceptance.
- Có ba phương án được chấm điểm, roadmap tuần tự, vé triển khai và vòng đối soát.
- Unknown và test chưa chạy được ghi rõ; audit không bị trình bày như build hoàn tất.
