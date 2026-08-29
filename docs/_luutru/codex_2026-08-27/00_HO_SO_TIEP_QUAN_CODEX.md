# Hồ sơ chuyển tiếp Codex — LTTSTUDIOSAPP

Tài liệu này là điểm vào cho phiên Codex tiếp quản dự án từ Claude. Nó không
thay thế `AGENTS.md`, `docs/QUYET_DINH_NEN_TANG.md`, kế hoạch hay nhật ký.

## Thứ tự đọc bắt buộc

1. `docs/QUYET_DINH_NEN_TANG.md` — nguồn chân lý kiến trúc/sản phẩm.
2. `docs/KE_HOACH_TRIEN_KHAI.md` — hạng mục mở và tiêu chí nghiệm thu.
3. Hai mục mới nhất trong `docs/NHAT_KY.md`.
4. `ho_so_he_thong.txt` — bản đồ/snapshot, chỉ dùng để định vị.
5. Các file nguồn và test liên quan trước khi sửa.

## Checkpoint tiếp quản (2026-08-27)

- Phiên Claude được tiếp quản chính xác: `5a74e3b4-a8e0-4dbc-a26b-6fe9bb2ddc04`
  (tiêu đề “Phân tích hệ thống lttstudiosapp”), dừng vì weekly limit lúc
  `2026-08-27 09:54:09` và hẹn reset `2026-08-28 19:00` (Asia/Ho_Chi_Minh).
- Hạng mục gần nhất: H42 — CamCLI 1.1.0, ba phương thức phân phối, đã deploy
  production và `health/ready` ở trạng thái `ready`.
- Bằng chứng gần nhất nằm trong mục H42 của `docs/NHAT_KY.md`.
- Việc chưa trả lời của phiên đó: đo lại và cân nhắc tăng trần input Qwen3.8
  trên máy B qua LTT Nexus; không được tự đổi cấu hình máy B nếu chưa có mốc
  đo và phương án rollback.
- Hồ sơ nghiên cứu và ladder nghiệm thu nằm ở
  `.codex/qwen38_context_research.md`; hiện mới kiểm tra read-only, chưa đổi
  cấu hình hay restart dịch vụ trên B.
- Kiểm tra Nexus tiếp quản (read-only): máy B `ONLINE`, RTX 3090 24 GB, khoảng
  22.9 GB VRAM trống; `gateway.env` đang đặt `LTT_LLM_MAX_INPUT_TOKENS=60000`;
  `qwen38-api` đang dùng `-c 65536`.
- Các việc đang treo cần chủ sản phẩm hoặc phiên sau: H41.2–H41.8; H33,
  H35.10 và các mục H37 còn mở. Không tự suy diễn thành phạm vi phiên này.
- Cây làm việc lúc chuyển tiếp có các thư mục evidence GUI chưa theo dõi dưới
  `docs/developer_portal_mvp_ui/evidence/`; giữ nguyên, không dọn hộ.
- `ho_so_he_thong.txt` đã được dựng lại và kiểm tra khớp nguồn:
  `python tools/build_system_profile.py --check` → PASS.

## Cấu hình được chuyển

- `launch.json` là bản sao cấu hình chạy local từ `.claude/launch.json`:
  Uvicorn factory ở cổng 8123 với tên `ltt-dev`.
- Các tệp trạng thái tạm của Claude (`scheduled_tasks.lock` và thư mục
  `worktrees`) **không** được sao chép. Chúng gắn với PID/session cũ và không
  phải cấu hình dự án.
- `.claude/settings.local.json` **không** được chép nguyên trạng: đó là quyền
  chạy riêng của Claude, có các chế độ không có ý nghĩa trong Codex. Ranh giới
  bảo mật và quy trình chung đã nằm trong `AGENTS.md`.
- Không có secret, token, nội dung `secrets/` hoặc thông tin xác thực trong
  thư mục này.

## Lệnh tiếp tục

```powershell
python tools\build_system_profile.py --check
python tools\gate.py --vong-lap
```

Trước khi báo hoàn thành hạng mục, bắt buộc chạy `python tools\gate.py` và ghi
kết quả thật vào `docs/NHAT_KY.md`. Không chạy `pytest` trực tiếp cho toàn bộ
kho.
