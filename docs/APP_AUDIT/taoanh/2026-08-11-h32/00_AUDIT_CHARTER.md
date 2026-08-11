# H32.3 — Audit charter: Tạo ảnh AI

- **Ngày:** 2026-08-11
- **Mode:** STANDARD có kiểm thử browser desktop/mobile
- **Phạm vi:** `/taoanh` (ảnh tổng quát) và `/taoanh/thumbnail`
- **Persona:** khách hàng sáng tạo nội dung, không phải developer
- **JTBD:** tạo/chỉnh ảnh; tạo thumbnail theo brief/brand; tìm lại, mở, so sánh
  và dùng output làm đầu vào mới.
- **Nguồn yêu cầu:** `TaoAnhAI/MoTa.txt` trong batch chỉ đọc.
- **Môi trường:** fixture cô lập `127.0.0.1:8142`; production 8100 không bị tác
  động; không dùng dữ liệu production.
- **Ranh giới bằng chứng:** fixture có output PNG đã seed để test UI/history,
  không gọi provider. Vì vậy không coi ảnh seed là output AI thật và không chép
  vào folder bàn giao như một kết quả provider.

PASS A0: hai mode, dữ liệu, viewport và giới hạn provider đã được khóa rõ.
