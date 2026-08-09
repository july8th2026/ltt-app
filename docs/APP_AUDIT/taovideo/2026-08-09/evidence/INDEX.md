# Evidence Index — Tạo Video Seedance DEEP audit

| ID | Loại | Nguồn/kết quả |
|---|---|---|
| EV-SRC-001 | Source E1 | `manifest.py`, `models.py`, `cost.py`, commit `a31d028` |
| EV-SRC-002 | Source E1 | `templates/taovideo.html`, render/filter/client behavior |
| EV-SRC-003 | Source E1 | `routes.py`: refs, estimate, queue, ownership/download |
| EV-SRC-004 | Source E1 | `jobs.py`, `modelark.py`, key pool/task retry/poll/storage |
| EV-SRC-005 | Source E1 | manifest hold + token settle + `platform_core/credit.py` |
| EV-SRC-006 | Source E1 | Upscale quote/confirm bridge và layering test |
| EV-BR-001 | Browser E3 | Desktop VI 1440×900, 7 job đủ trạng thái; `seedance-desktop-vi.png` |
| EV-BR-002 | Browser E3 | Mobile EN 390×844; offscreen focus/Escape; `seedance-mobile-en.png` |
| EV-BR-003 | Browser E3 | Model matrix, quote, prompt assist; submit 2 variant hold 94, balance 1000→906 |
| EV-BR-004 | Browser E3 | Ảnh/video thật; 5-ref validity; blob `ERR_FILE_NOT_FOUND`; ~17 estimate POST |
| EV-BR-005 | Browser E3 | EN insufficient credit 400, EN→VI, mất form; `seedance-credit-failure-locale-loss.png` |
| EV-BR-006 | Browser E3 | Initial desktop không overflow; initial console/network sạch trước ref mutation |
| EV-COST-001 | Local runtime E3 | 130% estimated token làm actual vượt hold ở 3 model/resolution sample |
| EV-TEST-001 | Test E2 | 77 targeted PASS: 39 + 38; 1 deprecation warning |
| EV-TEST-002 | Gate E2 | `python tools\gate.py --quick` PASS 8/8, 26s |
| EV-MKT-001 | Market E1 | Official docs của 6 benchmark + BytePlus, snapshot 2026-08-09 |
| EV-SRC-007 | Source E1 | `apps/taovideo/refs.py`, `assets.py`, `jobs.py`, `manifest.py`: positional tags, asset MIME/type, video-rate quote, task/poll/settle |
| EV-RJ-001 | Browser E4 | Deploy `app.lttstudios.com`, account test; Mini/4s/480p, 1 ảnh + 1 video, @handle; submit thành công, hold/credit quan sát được |
| EV-RJ-002 | Browser E4 | Job `121eb14b…`: asset → submit → poll → download → done, history/saved refs sau reload |
| EV-RJ-003 | Browser E4 | Output player readyState=4, 864×496, 4.096s, không media error; `seedance-deep-output-frame.jpg` + strip |
| EV-RJ-004 | Browser E4 | Link tải redirect signed R2 và mở player; chưa có attachment semantics |
| EV-BR-007 | Browser E3 | Desktop 1440×1000 upload ảnh/video thật, preview dimensions, role/handle, estimate/network/console sạch |
| EV-BR-008 | Browser E3 | Mobile click `Biến thể`: count=2 nhưng saved refs=0, binding không khôi phục |
| EV-BR-009 | Browser E3 | Production 390×844: overflow=0, saved refs + output card/player; drawer initial đóng |
| EV-TEST-003 | Test E2 | 67 targeted Seedance/platform tests PASS, 1 deprecation warning, 54.82s |
| EV-MEDIA-001 | Tool E2 | `ffprobe` input/output; output H.264/AAC, 864×496, 4.096s; frame strip trực quan |

Không lưu cookie, token, email, secret hoặc dữ liệu production trong hồ sơ.
