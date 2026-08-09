# Evidence Index — Upscale Video DEEP audit

| ID | Loại | Nguồn/kết quả |
|---|---|---|
| EV-SRC-001 | Source E1 | `manifest.py`, route/job contract, commit `1f90d8a` |
| EV-SRC-002 | Source E1 | `templates/upscalevideo.html`, `server/static/ltt.css` |
| EV-SRC-003 | Source E1 | upload, ownership, source/output/download routes |
| EV-SRC-004 | Source E1 | `service.py`, `jobs.py`, `engine.py`, `ff.py`, telemetry |
| EV-SRC-005 | Source E1 | `cost.py` và transaction credit trong service |
| EV-BR-001 | Browser E3 | Desktop 1440×900; ảnh `EV-BR-001-desktop.png` |
| EV-BR-002 | Browser E3 | Mobile 390×844; ảnh `EV-BR-002-mobile.png` |
| EV-BR-003 | Browser E3 | Video thật: metadata 10s/2.9MB, quote 5 credit; smooth 11 credit; compare phím 50→100→90 |
| EV-BR-004 | Browser E3 | `/en/`: invalid-file báo tiếng Việt; cancel chuyển `/en/upscalevideo` → `/upscalevideo` |
| EV-BR-005 | Browser E3 | Console 0 error/warning; network không failed, nhưng source metadata bị gọi lặp |
| EV-TEST-001 | Test E2 | 50 targeted PASS, 1 deprecation warning, 13.86s |
| EV-TEST-002 | Gate E2 | `python tools\gate.py --quick` PASS 8/8, 25.8s |
| EV-GPU-001 | Local runtime E3 | H26 evidence: 2 GPU × 2 preset × 3 resolution PASS; max 64°C |
| EV-GPU-002 | Local runtime E3 | Fast full 1080 ≈21s/10s; Quality ≈310–327s/10s trên baseline đã lưu |
| EV-MKT-001 | Market E1 | Official product/docs pages của 6 benchmark, snapshot 2026-08-09 |

Không lưu cookie, token, email thật, secret hoặc dữ liệu production trong hồ sơ.
