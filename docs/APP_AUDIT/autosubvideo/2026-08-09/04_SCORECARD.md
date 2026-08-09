# 04 — Scorecard: Auto Sub Studio

## Dashboard

- **Quality Score: 56/100**
- **Market Score: 65/100**
- **Evidence Confidence: 61/100** — hiệu chỉnh H28 theo E1/E2/E3 thực tế
- **Release Gate: BLOCKED**
- Finding: **0 P0 · 3 P1 · 14 P2 · 5 P3**
- Blocker: upload/source lifecycle chưa an toàn; workload/giới hạn/quote không
  canonical; autosave/conflict có đường mất chỉnh sửa của khách hàng.

`BLOCKED` không nói app không chạy. Nó cấm mở rộng thương mại/tính năng hoặc coi
H26 là nghiệm thu cuối trước khi Phase 0 đóng G2/G3/G5/G7.

## Quality

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Evidence | Nhận xét |
|---|---:|---:|---:|---|---|
| Giá trị/kết quả lõi | 15 | 3.6 | 10.8 | EV-BR-003, EV-SRC-008 | Full edit/render pipeline; chưa blind-score output |
| Tính năng/độ đầy đủ | 12 | 3.8 | 9.1 | EV-MKT-001 | Breadth tốt; thiếu project/collab/recovery |
| Chức năng/control | 12 | 3.3 | 7.9 | C-01..21 | Nhiều control live; nhiều control partial/broken |
| UX/workflow/IA | 12 | 2.6 | 6.2 | J-01..20 | 4 bước rõ nhưng project/recovery/capability lủng củng |
| UI/thẩm mỹ/design system | 8 | 3.2 | 5.1 | EV-BR-002/005 | Desktop chuyên nghiệp; dày và mobile cắt |
| Responsive/accessibility | 7 | 1.8 | 2.5 | EV-BR-005/006 | Mobile/EN/keyboard timeline fail |
| Hiệu năng/tin cậy | 9 | 2.2 | 4.0 | EV-BR-002/005, EV-TEST-001 | Full video decode, history clone, warning thread |
| AI/provider economics | 8 | 1.8 | 2.9 | EV-SRC-006/008, EV-BR-004 | Free GPU quota và quote workload chưa đúng |
| Security/privacy/tenant/credit | 10 | 1.6 | 3.2 | EV-SRC-004/008 | Owner check tốt; upload ticket/orphan/admission fail |
| Kiến trúc/ops/observability | 7 | 2.9 | 4.1 | EV-SRC-003/008/009 | Snapshot/jobs tốt; retention/pagination/SLO thiếu |

Tổng quy đổi **55,8**, làm tròn **56/100**.

## Gate

| Gate | Kết quả | Evidence | Điều kiện mở |
|---|---|---|---|
| G0 Scope | PASS | 00_AUDIT_CHARTER | — |
| G1 Core outcome | PASS có điều kiện | EV-BR-003, EV-SRC-008 | Golden WER/timing/render parity |
| G2 Security | **FAIL** | F-001/F-004/F-016 | Staging ticket, signature/probe, strict source token |
| G3 Money/Credit | **FAIL** | F-002/F-006/F-007 | Canonical media/workload quote + bounded free compute |
| G4 Honest UI | **FAIL** | F-005/F-008/F-009/F-013 | Capability/waveform/preview/QA phản ánh sự thật |
| G5 Data recovery | **FAIL** | F-001/F-003/F-010/F-011/F-014 | Outbox/merge/project/artifact lifecycle |
| G6 Accessibility | **FAIL** | F-012/F-017/F-020 | VI/EN, keyboard, mobile, accessible waveform/timeline |
| G7 Performance | **FAIL** | F-002/F-009/F-018/F-021 | Peaks server-side, payload/history/upload budgets |
| G8 Operations | **FAIL** | F-001/F-006/F-014/F-019/F-022 | Retention/SLO/job pagination/thread-clean test |

## Test/lệnh đã chạy

| Flow/lệnh | Kết quả thật | Evidence |
|---|---|---|
| Playwright empty desktop 1440×900 | Mở được; console 0 | EV-BR-001 |
| Upload video thật 3 MB | Attach 10s/864×496; Range + GET 200 toàn video | EV-BR-002 |
| Import SRT | 3 cue, QA 100, preview/timeline live | EV-BR-003 |
| Tạo overlap + end 12s trên video 10s | Save 200; QA 70, hai lỗi overlap | EV-BR-004 |
| Quote source và 4K | Cả hai 1 credit; dialog vẫn mở khi QA lỗi | EV-BR-004 |
| 390×844 | Timeline/cue bị cắt ngang | EV-BR-005 |
| `/en/autosubvideo` | Toàn bộ React vẫn VI | EV-BR-006 |
| `python -m pytest -q tests/test_81_autosubvideo.py tests/test_103_autosub_projects.py` | **36 passed**, 3 warning; 2 warning là unhandled media thread | EV-TEST-001 |
| `npm test -- --run` trong frontend | **13 passed** | EV-TEST-001 |
