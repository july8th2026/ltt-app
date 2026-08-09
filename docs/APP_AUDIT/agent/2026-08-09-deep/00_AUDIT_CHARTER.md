# A0 — Audit Charter: LTT Agent AI

- **Mã:** H27.8 / LTT-AQA v1.0 / DEEP; snapshot 2026-08-09.
- **Persona:** creator/khách hàng phổ thông Việt Nam muốn nối các bước tạo text,
  ảnh, video và audio; không phải dev workflow.
- **JTBD:** (1) tạo hoặc đưa nội dung vào một block; (2) nối các block theo ý đồ
  và chạy riêng/toàn chuỗi; (3) biết trước chi phí, theo dõi, sửa lỗi và dùng lại
  kết quả/workflow mà không cần hiểu schema hay job type.
- **Môi trường:** fixture cô lập `127.0.0.1:8112`, DB/Storage/Credit/worker thật,
  provider giả; desktop 1440×900, mobile 390×844, route VI/EN.
- **Dữ liệu:** dữ liệu fixture, không dùng production và không gọi provider thật.
- **Benchmark:** FLORA, PlenX (evidence nội bộ đã khảo sát), ComfyUI APP mode,
  n8n và Make; nguồn chính thức snapshot cùng ngày.
- **Budget:** core task không chạy trùng/thu sai; quote = trần; cancel dừng toàn cây;
  WCAG 2.2 AA; customer UI không lộ tool ID/schema/retry/fan-out.
- **Ranh giới:** audit-only, chưa BUILD/deploy. Audit H26 là lịch sử release, không
  được kế thừa điểm PASS.

Charter PASS. Điểm và gate áp cho app hiện tại ở môi trường audit; tác động của
race SQLite lên PostgreSQL production phải được kiểm chứng riêng, không suy đoán.
