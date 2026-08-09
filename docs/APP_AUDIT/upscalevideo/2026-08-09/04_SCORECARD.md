# 04 — Scorecard: Upscale Video

## Dashboard

- **Quality Score: 64/100**
- **Market Score: 57/100**
- **Evidence Confidence: 84/100**
- **Release Gate: BLOCKED**
- Blocker: G2/G5 fail vì direct upload chưa có policy size/type/quota đủ mạnh
  và artifact upload có thể mồ côi; G4 fail vì entitlement/copy/i18n không trung
  thực; chưa đủ evidence production để mở G7/G8 cho COMMERCIAL.

`BLOCKED` là kết luận của audit app độc lập, không phủ nhận sự thật app đang
được deploy PUBLIC theo H26.12C. Nó có nghĩa: không quảng bá/mở rộng thương mại
trước khi Phase 0 PASS.

## Quality

| Nhóm | Trọng số | Điểm 0–5 | Điểm quy đổi | Evidence IDs | Nhận xét |
|---|---:|---:|---:|---|---|
| Giá trị/kết quả lõi | 15 | 3.5 | 10.5 | EV-GPU-001/002, EV-BR-003 | Chạy thật; chưa blind-score temporal quality |
| Tính năng/độ đầy đủ | 12 | 3.0 | 7.2 | EV-MKT-001 | Đủ upscale cơ bản; thiếu detail/denoise/deblur/temporal |
| Chức năng/control | 12 | 3.3 | 7.9 | EV-BR-003/004, C-01..28 | Nhiều control live; retry/history/upload policy thiếu |
| UX/workflow/IA | 12 | 3.1 | 7.4 | EV-BR-001..004 | Desktop/mobile rõ; copy kỹ thuật và recovery yếu |
| UI/thẩm mỹ/design system | 8 | 3.4 | 5.4 | EV-BR-001/002 | Nhất quán dark LTT; PRO/status labels làm giảm độ tin cậy |
| Responsive/accessibility | 7 | 3.2 | 4.5 | EV-BR-002/003 | Không overflow, slider tốt; shell icon name rỗng, i18n lỗi |
| Hiệu năng/tin cậy | 9 | 3.2 | 5.8 | EV-GPU-001/002, EV-BR-005 | GPU ổn; Quality chậm 15×, download proxy, chưa production SLO |
| AI/provider economics | 8 | 3.5 | 5.6 | EV-SRC-004/005 | Quote/credit rõ; engine tự vận hành, chưa biết cost/output quality |
| Security/privacy/tenant/credit | 10 | 2.3 | 4.6 | EV-SRC-003/005, EV-TEST-001 | Ownership tốt; upload abuse/orphan là blocker |
| Kiến trúc/ops/observability | 7 | 3.6 | 5.0 | EV-SRC-004, EV-TEST-001 | Service/worker/telemetry tốt; artifact lifecycle và SLO còn gap |

Tổng quy đổi: **64.0/100**.

## Gate

| Gate | PASS/FAIL/UNKNOWN | Evidence | Blocker/điều kiện mở |
|---|---|---|---|
| G0 Scope | PASS | 00_AUDIT_CHARTER | — |
| G1 Core Outcome | PASS có điều kiện | EV-GPU-001/002 | Blind benchmark trước COMMERCIAL |
| G2 Security | **FAIL** | EV-SRC-003, F-001 | Upload allowlist/size/quota/rate/CSRF + abuse test |
| G3 Money/Credit | PASS có điều kiện | EV-SRC-005, EV-TEST-001 | Cleanup artifact phải đồng bộ với hold failure |
| G4 Honest UI | **FAIL** | EV-BR-001/004, F-004..006 | Bỏ entitlement giả, copy nội bộ, i18n hardcode |
| G5 Data Recovery | **FAIL** | EV-SRC-003, F-002 | Lifecycle/cleanup orphan + retry/recovery |
| G6 Accessibility | **FAIL** | EV-BR-001/002, F-011 | Accessible name shell và locale journey |
| G7 Performance | UNKNOWN | EV-GPU-001/002 | ≥20 production finished, P95 theo preset, direct large download |
| G8 Operations | **FAIL** | EV-SRC-003/004 | Artifact retention/cleanup và production SLO sample |

## Lệnh/test đã chạy

| Lệnh/flow | Kết quả thật | Evidence ID |
|---|---|---|
| Playwright desktop 1440×900 + mobile 390×844 | Không overflow; ảnh full-page lưu; console 0 | EV-BR-001/002/005 |
| Upload video thật → metadata/quote/toggle | 10s, 2.9MB; 5 credit; smooth 11 credit; mutual exclusion PASS | EV-BR-003 |
| Compare slider keyboard | 50 → End 100 → Shift+Left 90 | EV-BR-003 |
| Filter/sort/grid-list | Error 1/3; sort oldest; grid lưu LocalStorage | EV-BR-003 |
| `/en/` invalid input và cancel | Lỗi JS tiếng Việt; cancel rơi về route VI | EV-BR-004 |
| `playwright-cli -s=ltt console error` | 0 error, 0 warning | EV-BR-005 |
| `playwright-cli -s=ltt requests` | 0 failed; nhiều request metadata 206 lặp | EV-BR-005 |
| `python -m pytest -q tests/test_82_upscalevideo.py tests/test_114_upscale_ui.py tests/test_115_upscale_feature_benchmark.py tests/test_116_upscale_motion_features.py tests/test_157_upscale_h26.py tests/test_151_worker_gpu.py` | **50 passed**, 1 deprecation warning, 13.86s | EV-TEST-001 |
| `python tools\gate.py --quick` | **PASS 8/8**, 25.8s | EV-TEST-002 |
