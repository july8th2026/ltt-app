# H32.1 — Audit charter: AutoSub Video

- Ngày kiểm: 2026-08-11.
- Nguồn yêu cầu: `AppLttStudio_11082026/AutoSubVideo/MoTa.txt`.
- Mẫu thật: `VideoTest.mp4`, H.264/AAC, 864×496, 24 fps, 15,069 giây,
  SHA-256 `0f76e487...1209`.
- Môi trường: fixture cô lập `127.0.0.1:8140`; SQLite/data riêng; production
  `8100` không bị tác động.
- Journey chính: upload → nhập SRT → TikTok Bold → style/animation → quote →
  giữ credit → render NVENC → tải xuống → kiểm media/khung hình → reload lịch sử.
- Viewport: 1440×1000 và 390×844.
- Không kiểm bằng suy đoán: mọi PASS lõi bên dưới có bằng chứng browser, job log,
  output thật hoặc test tự động.

## Điều kiện PASS

1. Tên khách hàng nhìn thấy là **AutoSub Video** trên title/nav/page heading.
2. Source và transcript được lưu đúng project; preset/style xuất hiện trong output.
3. Quote hiện trước submit; credit chỉ trừ khi job thành công.
4. Video xuất có video + audio, giữ 864×496, 24 fps và thời lượng nguồn.
5. Job/history/artifact còn truy cập được sau reload.
6. Console không lỗi; không có request 4xx/5xx trong journey.

## Giới hạn kết luận

Fixture không có WhisperX, Pyannote và Gemini nên chỉ xác minh được UI khóa trung
thực của ba capability này; không được gọi chúng là PASS vận hành. Đây là mục
cần kiểm lại trên staging có model/key, không phải lý do giả lập kết quả.
