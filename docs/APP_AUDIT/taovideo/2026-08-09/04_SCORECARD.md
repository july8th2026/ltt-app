# 04 — Scorecard: Tạo Video Seedance

## Dashboard

- **Quality Score: 57/100**
- **Market Score: 64/100**
- **Evidence Confidence: 87/100**
- **Release Gate: BLOCKED**
- Finding: **0 P0 · 3 P1 · 11 P2 · 4 P3**
- Blocker chính: quyết toán có thể vượt khoản giữ và làm số dư âm; reference
  được lưu trước credit/job rồi không cleanup; double-submit với ref mới có thể
  vượt dedupe và giữ credit hai lần.

`BLOCKED` không phủ nhận app đang public theo H26. Nó có nghĩa không mở rộng
thương mại hoặc thêm feature trước khi Phase 0 đóng G2/G3/G5.

## Quality

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Evidence | Nhận xét |
|---|---:|---:|---:|---|---|
| Giá trị/kết quả lõi | 15 | 3.5 | 10.5 | EV-BR-003, EV-SRC-004 | Generate thật, multimodal; chưa blind-score output |
| Tính năng/độ đầy đủ | 12 | 3.3 | 7.9 | EV-MKT-001 | Input tốt; thiếu edit/extend/project/scene workflow |
| Chức năng/control | 12 | 2.8 | 6.7 | C-01..22 | Nhiều control live; cancel/retry/delete/pagination thiếu |
| UX/workflow/IA | 12 | 2.5 | 6.0 | EV-BR-001..005 | Composer rõ; lỗi submit làm mất công việc, recovery yếu |
| UI/thẩm mỹ/design system | 8 | 3.4 | 5.4 | EV-BR-001/002 | Dark LTT nhất quán, responsive; status/copy còn kỹ thuật |
| Responsive/accessibility | 7 | 2.2 | 3.1 | EV-BR-002 | Không overflow nhưng drawer ẩn nhận focus, EN lẫn VI |
| Hiệu năng/tin cậy | 9 | 3.0 | 5.4 | EV-BR-004, EV-TEST-001 | Test nhanh; file đọc RAM, HTMX spam, progress tĩnh |
| AI/provider economics | 8 | 2.1 | 3.4 | EV-SRC-004/005, EV-COST-001 | Token thật nhưng calibration một mẫu, retry billing unknown |
| Security/privacy/tenant/credit | 10 | 1.8 | 3.6 | EV-SRC-003/005 | Owner/CSRF tốt; orphan/double hold/negative balance blocker |
| Kiến trúc/ops/observability | 7 | 3.2 | 4.5 | EV-SRC-004/006, EV-TEST-001 | Task id/event tốt; lifecycle/model config/SLO còn gap |

Tổng quy đổi **56,5**, làm tròn **57/100**.

## Gate

| Gate | Kết quả | Evidence | Điều kiện mở |
|---|---|---|---|
| G0 Scope | PASS | 00_AUDIT_CHARTER | — |
| G1 Core outcome | PASS có điều kiện | EV-BR-003, EV-SRC-004 | Blind benchmark trước COMMERCIAL |
| G2 Security | **FAIL** | F-002/F-008 | Staging refs, signature/container, memory/quota test |
| G3 Money/Credit | **FAIL** | F-001/F-003/F-005 | Không âm, quote canonical, idempotent submit |
| G4 Honest UI | **FAIL** | F-004/F-005/F-006/F-017 | Locale/copy/quote phản ánh đúng request |
| G5 Data recovery | **FAIL** | F-002/F-004/F-009/F-010 | Preserve form/ref, cleanup, retry/history/delete |
| G6 Accessibility | **FAIL** | F-006/F-018 | Inert/focus restore, EN A-Z, shared accessible names |
| G7 Performance | UNKNOWN | U-05, F-008/F-015 | Production sample + upload memory/load budget |
| G8 Operations | **FAIL** | F-002/F-012/F-013 | Lifecycle report, dynamic model config, billing proof/SLO |

## Test/lệnh đã chạy

| Flow/lệnh | Kết quả thật | Evidence |
|---|---|---|
| Playwright 1440×900 VI + 390×844 EN | Không overflow; 3 screenshot full-page | EV-BR-001/002/005 |
| Model/capability/quote/prompt assist | Mini/Standard/Fast đổi đúng; 2 variant quote 94 | EV-BR-003 |
| Ảnh + video thật, limit refs | Preview role/handle có; blob request fail; limit báo muộn | EV-BR-004 |
| Submit an toàn 2 variants | 2 queued; 1000→906; không chạy provider | EV-BR-003 |
| EN insufficient credit | 400; EN→VI; prompt/model/count mất; URL POST | EV-BR-005 |
| Mobile Tab/Escape | Focus đi vào panel ngoài màn hình, không restore | EV-BR-002 |
| 39 test app trực tiếp | **39 passed**, 3,72s | EV-TEST-001 |
| 38 test vận hành/layout/layer | **38 passed**, 1 warning, 54,06s | EV-TEST-001 |
| `python tools\gate.py --quick` | **PASS 8/8**, 26s | EV-TEST-002 |

