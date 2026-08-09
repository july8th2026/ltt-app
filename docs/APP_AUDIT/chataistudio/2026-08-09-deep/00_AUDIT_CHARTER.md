# A0 — Audit Charter: Chat AI Studio

- **Mã:** H27.7 / LTT-AQA v1.0 / DEEP; snapshot 2026-08-09.
- **Persona:** khách hàng phổ thông/creator Việt Nam cần trợ lý viết, phân tích file và tạo ảnh; không phải dev.
- **JTBD:** (1) hỏi và nhận câu trả lời dễ dùng; (2) làm việc tiếp với file/ảnh và lịch sử đúng ngữ cảnh; (3) hiểu tiền, dữ liệu và khôi phục khi stream/provider lỗi.
- **Môi trường:** fixture cô lập `127.0.0.1:8112`, sidecar giả nhưng route/SSE/Postgres-like DB/Storage/Credit thật; desktop 1440×1000, mobile 390×844, VI/EN.
- **Dữ liệu:** file JSON/PNG fixture; không gọi OpenAI production, không dùng dữ liệu khách.
- **Benchmark:** ChatGPT, Claude, Gemini, Perplexity; nguồn chính thức snapshot cùng ngày.
- **Budget:** response P95 và provider quota production UNKNOWN; core không mất tiền/context/data; WCAG 2.2 AA; không raw provider/dev controls.
- **Ranh giới:** audit-only, không BUILD/deploy. Hồ sơ H26 ở `../2026-08-09/` là delta/release history, không phải điểm kế thừa.

Charter PASS. Do app bán lượt chat cho end user qua một sidecar đăng nhập OpenAI, quyền sử dụng thương mại, data-control và auth mode là phần bắt buộc của G2/G8.
