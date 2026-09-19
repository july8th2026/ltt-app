# Ngoại lệ máy quét `tools/quet_tai_lieu.py`

Dòng CHET/THAY mà agent xem lại bằng tay nhưng **không sửa** vì không chắc, hoặc
vì sửa sẽ làm sai nội dung lịch sử. Mẫu: `tệp:dòng` — lý do — ai ghi, ngày.

## L-C — 2026-09-19

- `docs/APP_AUDIT/control-plane/2026-08-06/00_CHARTER_VA_HIEN_TRANG.md:44,45,47,52`,
  `01_LOGIC_VAN_HANH.md:75,76`, `03_SCORECARD.md:72,75,109,112`,
  `04_BAN_DO_CORE.md:73` — CHET trỏ `apps/prompt_ai_ommi/routes.py`,
  `apps/agent/routes.py`, `core/sheet_runner.py`,
  `core/tiktok/compliance_guard.py`, `gui/monitor_tab.py`. Đây là ảnh chụp
  đường dẫn mã THẬT TẠI THỜI ĐIỂM audit 2026-08-06 (đường dẫn app hiện đã đổi
  tên/cấu trúc; `core/` đã bị xoá hẳn 2026-08-25 — xem
  `tests/test_147_layering.py::test_nen_tang_va_app_khong_phu_thuoc_core_legacy`).
  Thư mục này đang được GIỮ (không lưu trữ) chính vì `tests/test_147` trích dẫn
  nó làm bằng chứng lịch sử cho lý do `core/` bị xoá — sửa các đường dẫn cũ
  thành đường dẫn hiện tại sẽ làm sai sự thật đã ghi nhận tại thời điểm đó.
  Không sửa. (agent L-C, 2026-09-19)
- `docs/lttstudios-website/README.md:338` — CHET trỏ
  `docs/fb-app-review-submission-plan.md` (mục "Optional PHP relay cho TikTok
  cross-machine OAuth"). Tệp đã chuyển từ lâu sang
  `docs/_luutru/fb-app-review-submission-plan.md`, nhưng đã kiểm nội dung tệp
  đó (và `docs/_luutru/lttstudios-deployment-guide.md`,
  `docs/_luutru/lttstudios-migration-plan.md`) — **không tệp nào trong kho
  chứa đoạn code mẫu PHP relay** mà dòng này hứa hẹn. Tham chiếu chết thật,
  nhưng không rõ đích đúng là gì (có thể đoạn code mẫu chưa từng được commit,
  hoặc đã mất khi tệp gốc bị dọn ở một đợt trước 2026-09). Không đoán/không
  tự viết lại; cần chủ dự án xác nhận có còn dùng PHP relay hay bỏ hẳn đoạn
  này. (agent L-C, 2026-09-19)
