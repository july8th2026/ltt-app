# 04 — Scorecard

## Dashboard

- **Quality Score:** 67/100
- **Market Score:** 52/100
- **Evidence Confidence:** 76/100
- **Release Gate cho bản parity mới:** INTERNAL
- **Không có P0 được xác nhận.** Chưa đủ bằng chứng để PUBLIC bản rebuild vì thiếu feature contracts, provider economics, a11y/load/full regression và production canary.

## Quality

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Evidence | Nhận xét |
|---|---:|---:|---:|---|---|
| Giá trị/kết quả lõi | 15 | 4.0 | 12.0 | E-CODE-01/E-LTT-01 | 7 tool thật, workflow chạy được |
| Tính năng/độ đầy đủ | 12 | 2.3 | 5.5 | E-PLX-01/E-TOOL-01 | thiếu 5 node active và lớp Canvas collaboration |
| Chức năng/control | 12 | 3.6 | 8.6 | E-CODE-01 | control kỹ thuật tốt, thiếu scoped run/version/share |
| UX/workflow/IA | 12 | 2.5 | 6.0 | E-LTT-01/E-PLX-01 | editor ba panel, Inspector xa node |
| UI/thẩm mỹ/design system | 8 | 2.6 | 4.2 | E-LTT-01 | sạch nhưng giống tool nội bộ, chưa studio immersive |
| Responsive/accessibility | 7 | 2.4 | 3.4 | E-LTT-01 | mobile chỉ xem; chưa audit WCAG đầy đủ |
| Hiệu năng/độ tin cậy | 9 | 3.4 | 6.1 | E-CODE-01 | autosave conflict/recovery tốt; chưa load/P95 |
| AI/provider economics | 8 | 2.8 | 4.5 | E-TOOL-01 | quote mạnh, catalog/provider breadth yếu |
| Security/privacy/tenant/credit | 10 | 4.5 | 9.0 | E-CODE-01/E-DOC-01 | lợi thế cốt lõi LTT |
| Kiến trúc/ops/observability | 7 | 4.0 | 5.6 | E-CODE-01/E-DOC-01 | test/metrics/rollback mạnh; rebuild chưa có evidence |
| **Tổng** | **100** | | **66.9 ≈ 67** | | |

## Gate

| Gate | Trạng thái | Evidence | Điều kiện mở PUBLIC rebuild |
|---|---|---|---|
| G0 Scope | PASS | Charter | khóa quyết định D1–D12 |
| G1 Core Outcome | PASS hiện tại / UNKNOWN rebuild | 7 tools | E2E tool mới và scoped run |
| G2 Security | PASS hiện tại / UNKNOWN share | source | ACL/revoke/SSRF/upload abuse tests |
| G3 Money/Credit | PASS hiện tại / UNKNOWN scoped run | source | quote/approve/idempotency từng node/frame |
| G4 Honest UI | PASS hiện tại | browser | không hiện node/CTA trước backend contract |
| G5 Data Recovery | PARTIAL | restore run | editor version snapshots + restore drill |
| G6 Accessibility | UNKNOWN | browser manual hạn chế | keyboard/focus/screen reader/contrast suite |
| G7 Performance | UNKNOWN | chưa đo | bundle, 100-node canvas, CWV/P95 budgets |
| G8 Operations | PARTIAL | existing telemetry | metric/runbook/rollback cho tool/provider mới |

## Lệnh/flow đã chạy

| Flow | Kết quả thật |
|---|---|
| Tạo/đổi tên workflow PlenX | PASS |
| Tạo 11 node active | PASS |
| Nối 9 edge hợp lệ + 1 edge sai kiểu | PlenX chấp nhận cả edge sai |
| Reload/autosave | dữ liệu hydrate lại; có flash empty tạm thời |
| Page 2, frame, sticky, comment | PASS |
| Version/share/logs/keyboard help | mở và kiểm kê PASS; share đã tắt lại |
| Local Agent desktop 1720×940 | PASS render; stage 1205×696 |
| Local console | 0 error/warning |
| Local API requests quan sát | palette/workflows/runs/detail đều 200 |
| `python -m pytest tests/test_61_setup_scripts.py -q` | 71 passed |
| `python tools/scan_source_secrets.py` | 0 finding, PASS |
| Full pytest/frontend/provider/GPU/load | CHƯA CHẠY trong audit này |
