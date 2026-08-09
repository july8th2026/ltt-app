# Evidence Index — Tạo Video Seedance DEEP audit

| ID | Loại | Nguồn/kết quả |
|---|---|---|
| EV-SRC-001 | Source E4 | `manifest.py`, `models.py`, `cost.py`, commit `a31d028` |
| EV-SRC-002 | Source E4 | `templates/taovideo.html`, render/filter/client behavior |
| EV-SRC-003 | Source E4 | `routes.py`: refs, estimate, queue, ownership/download |
| EV-SRC-004 | Source E4 | `jobs.py`, `modelark.py`, key pool/task retry/poll/storage |
| EV-SRC-005 | Source E4 | manifest hold + token settle + `platform_core/credit.py` |
| EV-SRC-006 | Source E4 | Upscale quote/confirm bridge và layering test |
| EV-BR-001 | Browser E4 | Desktop VI 1440×900, 7 job đủ trạng thái; `seedance-desktop-vi.png` |
| EV-BR-002 | Browser E4 | Mobile EN 390×844; offscreen focus/Escape; `seedance-mobile-en.png` |
| EV-BR-003 | Browser E4 | Model matrix, quote, prompt assist; submit 2 variant hold 94, balance 1000→906 |
| EV-BR-004 | Browser E4 | Ảnh/video thật; 5-ref validity; blob `ERR_FILE_NOT_FOUND`; ~17 estimate POST |
| EV-BR-005 | Browser E4 | EN insufficient credit 400, EN→VI, mất form; `seedance-credit-failure-locale-loss.png` |
| EV-BR-006 | Browser E4 | Initial desktop không overflow; initial console/network sạch trước ref mutation |
| EV-COST-001 | Runtime/source E4 | 130% estimated token làm actual vượt hold ở 3 model/resolution sample |
| EV-TEST-001 | Test E4 | 77 targeted PASS: 39 + 38; 1 deprecation warning |
| EV-TEST-002 | Gate E4 | `python tools\gate.py --quick` PASS 8/8, 26s |
| EV-MKT-001 | Market E1 | Official docs của 6 benchmark + BytePlus, snapshot 2026-08-09 |

Không lưu cookie, token, email, secret hoặc dữ liệu production trong hồ sơ.

