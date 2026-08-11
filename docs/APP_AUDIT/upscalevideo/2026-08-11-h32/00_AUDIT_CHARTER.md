# H32.6 — Audit charter: Upscale Video

- **Chuẩn:** LTT-AQA v1.0, mode `DEEP`.
- **Ngày snapshot:** 2026-08-11.
- **Persona:** creator không chuyên kỹ thuật cần nâng video nhanh, biết trước giá
  và tải được kết quả đúng thông số.
- **JTBD:** (1) chọn video và preset; (2) theo dõi queue/GPU; (3) so sánh rồi
  tải output đúng resolution/FPS/audio/codec.
- **Nguồn:** `VideoTest.mp4` trong folder yêu cầu, H.264/AAC, 864×496, 24 fps,
  15,069 giây, 6.592.927 byte; SHA-256 được kiểm trong runtime evidence.
- **Môi trường:** fixture cô lập cổng 8145, tài khoản/DB/storage riêng; GPU 1 RTX
  5060 Ti 16 GB dành riêng. GPU 0 đang có workload ngoài phạm vi nên không dừng.
- **Ranh giới:** không đụng production 8100, không deploy, không dùng dữ liệu
  production, không gọi output nội suy 1 giây là bằng chứng chất lượng thương mại.
- **Budget nghiệm thu:** option/contract 100%; desktop/mobile không overflow;
  console và failed application request bằng 0; GPU không thermal slowdown;
  chất lượng cảm nhận chỉ PASS sau calibration + blind review.

## Gate charter

H32.6 có thể PASS kỹ thuật dù release app vẫn `BLOCKED`. Một ma trận codec/FPS
đúng không bù được upload security, artifact lifecycle hoặc quality chưa
calibrate.

