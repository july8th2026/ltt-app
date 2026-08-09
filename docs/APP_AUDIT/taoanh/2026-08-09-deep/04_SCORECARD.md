# 04 — Scorecard: Tạo ảnh AI + Thumbnail

## Dashboard

- **Quality Score: 56/100**
- **Market Score: 54/100**
- **Evidence Confidence: 91/100**
- **Release Gate: BLOCKED**
- Finding: **0 P0 · 3 P1 · 15 P2 · 6 P3**
- Score H26.9 `Q85` là nghiệm thu sau hợp nhất shell, không còn đại diện cho
  current DEEP audit này.

| Nhóm | Trọng số | Điểm 0–5 | Quy đổi | Evidence |
|---|---:|---:|---:|---|
| Giá trị/kết quả lõi | 15 | 3.5 | 10.5 | EV-BR-001/002, EV-SRC-003 |
| Tính năng/độ đầy đủ | 12 | 2.8 | 6.7 | EV-MKT-001 |
| Chức năng/control | 12 | 3.0 | 7.2 | J-01..13 |
| UX/workflow/IA | 12 | 2.3 | 5.5 | EV-BR-002/003/007 |
| UI/design system | 8 | 3.0 | 4.8 | EV-BR-001/002 |
| Responsive/accessibility | 7 | 2.5 | 3.5 | EV-BR-003/004/005 |
| Hiệu năng/tin cậy | 9 | 2.5 | 4.5 | EV-SRC-002/004/005 |
| AI/provider economics | 8 | 2.0 | 3.2 | EV-BR-006, EV-SRC-001/003 |
| Security/privacy/credit | 10 | 2.7 | 5.4 | EV-SRC-002/005 |
| Kiến trúc/ops/observability | 7 | 3.0 | 4.2 | EV-SRC-004/005, EV-TEST-001 |

Tổng quy đổi **55,5**, làm tròn **56/100**. Không có score nào được phép mở
gate khi P1 về money/data còn tồn tại.

## Gate

| Gate | Kết quả | Điều kiện mở |
|---|---|---|
| G0 Scope | PASS | — |
| G1 Core outcome | PASS có điều kiện | golden output/provider smoke và no-loss validation |
| G2 Security | **FAIL** | early body cap + reference/artifact lifecycle |
| G3 Money/Credit | **FAIL** | canonical model-aware Thumbnail pricing + settlement tests |
| G4 Honest UI | **FAIL** | prerequisite/partial/score/config phản ánh sự thật |
| G5 Data recovery | **FAIL** | draft retention, asset library, purge/artifact contract |
| G6 Accessibility | **FAIL** | Thumbnail EN, locale links, mobile progressive/keyboard audit |
| G7 Performance | **FAIL** | upload streaming/body budget, polling/pagination budgets |
| G8 Operations | **FAIL** | full history/recovery, artifact policy, production canary |

## Kiểm tra thật

| Lệnh/flow | Kết quả |
|---|---|
| Playwright desktop/mobile/VI/EN/general/thumbnail | 5 screenshot; console 0 ở happy pages |
| Edit không source | POST 400; prompt và mode mất; console network error 400 |
| Thumbnail Gemini 3 Pro | CTA vẫn **5 credit** |
| `python -m pytest -q` 8 file targeted | **48 passed**, 1 warning deprecation |
