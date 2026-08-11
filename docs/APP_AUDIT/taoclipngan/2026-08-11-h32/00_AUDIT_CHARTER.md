# H32.4 — Audit charter: Tạo Clip ngắn

- **Ngày:** 2026-08-11
- **Mode:** DEEP, có job media/GPU thật và kiểm output byte-level
- **Phạm vi:** `/taoclipngan`, worker `taoclipngan.render`, source library,
  social package và ZIP/SRT
- **Persona:** creator/marketing không phải developer
- **JTBD:** đưa video dài vào, chọn mục tiêu đơn giản, nhận các clip đúng tỉ lệ,
  caption dễ sửa, tải/publish package và tìm lại lịch sử.
- **Nguồn yêu cầu:** `TaoClipNgan/MoTa.txt` và `VideoTest.mp4` trong batch chỉ đọc.
- **Môi trường:** fixture cô lập `127.0.0.1:8143`, SQLite/storage/test credit riêng;
  production 8100 và dữ liệu người dùng không bị tác động.
- **Máy đo:** RTX 5060 Ti 16 GB, worker bằng `C:\LTTPlatform\venv` CUDA;
  browser Chrome headed qua Playwright.
- **Ranh giới:** Fast/1 clip/talking-head/VI/9:16 và 4:5 có E4. Balanced,
  Best, 1:1, 16:9, 2–10 clip và các genre khác chỉ có contract/test, không được
  ghi là đã benchmark runtime.

PASS A0: source, account, credit, GPU, rollback và bằng chứng được cô lập.
