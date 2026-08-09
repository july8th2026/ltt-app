# 04 — Scorecard: Prompt AI OMMI

## Dashboard

- **Quality Score: 48/100**
- **Market Score: 51/100**
- **Evidence Confidence: 56/100** — hiệu chỉnh H28 theo E1/E2/E3 thực tế
- **Release Gate: BLOCKED**
- Finding: **0 P0 · 5 P1 · 14 P2 · 6 P3**
- Blocker: paid Director không apply được; autosave có đường mất dữ liệu; core
  resource/storyboard/handoff chưa nối thành workflow; upload lifecycle chưa an toàn.

## Quality

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Evidence |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 2.3 | 6.9 | EV-BR-002, EV-SRC-003/005 |
| Tính năng/độ đầy đủ | 12 | 2.9 | 7.0 | EV-SRC-002/005, EV-MKT-001 |
| Chức năng/control | 12 | 2.1 | 5.0 | J-01..14 |
| UX/workflow/IA | 12 | 1.8 | 4.3 | EV-BR-001/004/007 |
| UI/thẩm mỹ/design system | 8 | 2.8 | 4.5 | EV-BR-001/006 |
| Responsive/accessibility | 7 | 1.7 | 2.4 | EV-BR-004/005 |
| Hiệu năng/tin cậy | 9 | 2.2 | 4.0 | EV-SRC-003/004/007 |
| AI/provider economics | 8 | 2.5 | 4.0 | EV-SRC-006 |
| Security/privacy/tenant/credit | 10 | 2.1 | 4.2 | EV-SRC-004/006 |
| Kiến trúc/ops/observability | 7 | 3.7 | 5.2 | EV-SRC-001/007, EV-TEST-001 |

Tổng quy đổi **47,5**, làm tròn **48/100**.

## Gate

| Gate | Kết quả | Evidence | Điều kiện mở |
|---|---|---|---|
| G0 Scope | PASS | 00_AUDIT_CHARTER | — |
| G1 Core outcome | **FAIL** | F-001/F-003 | paid result apply + connected A–Z journey |
| G2 Security | **FAIL** | F-004 | probe/signature, staging/promote/delete/TTL atomic |
| G3 Money/Credit | **FAIL** | F-001/F-005 | output apply, partial outcome/refund contract |
| G4 Honest UI | **FAIL** | F-002/F-006/F-007 | error/theme/locale/capability đúng sự thật |
| G5 Data recovery | **FAIL** | F-002/F-008/F-009 | durable draft/outbox/conflict/version recovery |
| G6 Accessibility | **FAIL** | F-006/F-010 | VI/EN, keyboard/mobile and focus audit |
| G7 Performance | **FAIL** | F-004/F-011 | upload/search/p95 budgets và số liệu đúng |
| G8 Operations | **FAIL** | F-012/F-013 | complete job history/SLO/current-UI regression |

## Test/lệnh đã chạy

| Lệnh/flow | Kết quả thật |
|---|---|
| Playwright desktop 1440×900 | project/resource/quote/classic; console sạch trừ 422 tái hiện |
| Playwright mobile 390×844 | panel chặn nav, prompt loss và 422 tái hiện |
| Playwright `/en/` + theme | app vẫn VI; light theme không áp dụng sau reload |
| `npm test -- --run` trong frontend | **22 passed** |
| Backend test OMMI theo nhóm | **195 passed**, warnings deprecation; không test nào bắt paid apply mismatch |
