# 00 — Audit Charter toàn nền tảng

- **Phạm vi:** control plane `app.lttstudios.com`, 11 app/module, trang vận hành
  và gói website `docs/lttstudios-website/`.
- **Version baseline:** commit `214277d`; production snapshot 2026-08-03.
- **Mode:** DEEP theo LTT-AQA, nhưng không chạy lại output-quality corpus của mọi
  provider; dùng kết quả E2–E4 mới nhất trong nhật ký cho phần đó.
- **Mục tiêu:** kiểm kê đúng bề mặt; chấm chất lượng/tính năng/UI; xác định thiếu,
  thừa và bất nhất; lập backlog tuần tự, không triển khai nhiều app song song.
- **Persona:** creator Việt Nam; operator/admin LTT; khách đang cân nhắc mua credit.
- **JTBD:** tìm đúng công cụ; tạo/biên tập media bằng job có báo giá; quản lý kết
  quả/credit/tài khoản mà không phải học lại giao diện ở mỗi app.
- **Viewport:** 1440×1000/1280 desktop và 390×844 mobile.
- **Môi trường:** production read-only qua Playwright; canary admin tạm cho trang
  authenticated, đã vô hiệu hóa sau audit. Không dùng dữ liệu khách hàng.
- **Style đích:** LTT Carbon Red, rút từ Marketplace authenticated, Upscale Studio
  và Auto Sub Studio; không lấy nguyên magic number của từng app.

## Inventory app/module

| # | Slug/module | Route chính | Nhóm | Runtime/đầu ra | Trạng thái sản phẩm |
|---:|---|---|---|---|---|
| 1 | `agent` | `/agent`, `/agent/canvas` | AI Studio | Plan/Canvas + 7 ToolSpec | Public |
| 2 | `autosubvideo` | `/autosubvideo` | Video | WhisperX/pyannote/Gemini/FFmpeg | Public, Studio mới |
| 3 | `chataistudio` | `/chataistudio` | Chat | streaming sidecar + ảnh | Public |
| 4 | `kichban` | `/kichban` | Kịch bản | Gemini text/JSON | Public |
| 5 | `taoanh` | `/taoanh` | Ảnh | Gemini Image | Public |
| 6 | `taoclipngan` | `/taoclipngan` | Video | Whisper/YOLO/FFmpeg GPU | Public |
| 7 | `taovideo` | `/taovideo` | Video | Seedance/BytePlus | Public, Studio mới |
| 8 | `thumbnail` | `/thumbnail` | Ảnh | Gemini Image + prompt catalog | Public |
| 9 | `upscalevideo` | `/upscalevideo` | Video | Real-ESRGAN/FFmpeg GPU | Public, Studio mới |
| 10 | `socialbot` | nhiều route gốc | Đăng bài | browser/Sheet/OAuth | Internal, đóng băng Q10 |
| 11 | `demo` | `/demo` | Hạ tầng | worker/storage/credit fixture | Internal, không benchmark |

## Inventory trang control plane

| Nhóm | Trang/route |
|---|---|
| Acquisition/Auth | `/`, `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password` |
| Commerce | `/nap`, `/nap/don/{id}`, trạng thái order, webhook PayOS |
| User workspace | `/`, `/jobs`, `/jobs/{id}`, `/settings`, `/status` |
| Socialbot legacy | `/facebook`, `/tiktok`, `/manual/*`, `/sheet/*`, `/monitor`, `/audit` |
| Operator/Admin | `/workers`, `/admin/`, `/chataistudio/admin`, Agent admin APIs |
| System/API | `/live`, `/ready`, `/version`, OAuth callbacks và webhook |

## Inventory website đã xây trong repo

Gói `docs/lttstudios-website/` có 404/500, home, products, download, about,
architecture, changelog, contact, support, transparency, legal (privacy, terms,
cookies, DPA, security, callback, data deletion), compliance Meta/TikTok, bản VI,
manifest, robots và sitemap. Production `lttstudios.com` hiện không phục vụ gói
này; xem finding F-001.

## A0 Gate

- [x] Scope/persona/JTBD/mode rõ.
- [x] Không có quyền thay đổi dữ liệu khách hàng.
- [x] Trọng số LTT-AQA giữ nguyên.
- [x] Thứ tự triển khai tuần tự được khóa ở `07_IMPLEMENTATION_ROADMAP.md`.
