# A0 — Audit charter Tạo ảnh AI H26.9

- Mode: STANDARD, kế thừa benchmark snapshot 2026-08-08 của H26.
- Môi trường: local/fixture cô lập; không production, không gọi provider thật.
- Persona: khách hàng sáng tạo nội dung, không phải developer.
- JTBD: tạo/chỉnh ảnh; tạo Thumbnail theo preset thương hiệu; tìm, so sánh và
  dùng lại output cũ.
- Phạm vi: `taoanh` là product parent, `thumbnail` là mode/capability con.
- Ranh giới: giữ route file/output, job type, credit, Storage, ownership và dữ
  liệu cũ; không import app chéo; folder đầu vào không có mô tả/ảnh nên phần
  reference là UNKNOWN, không tự dựng thêm tính năng.
- Acceptance H26.9: một entry customer, hai mode rõ, mọi output cũ còn tìm được,
  redirect 308 tương thích, quote/submit/ownership không đổi, desktop/mobile và
  console/network PASS.
