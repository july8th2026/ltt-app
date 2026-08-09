# 00 — Audit Charter: Tạo ảnh AI + Thumbnail

- Product parent/mode: `taoanh` + `thumbnail`
- Version/commit nền: `0a3e724`
- Snapshot: 2026-08-09, **DEEP** theo LTT-AQA v1.0.
- Lý do audit lại: hồ sơ H26.9 trong `2026-08-09/` nghiệm thu việc hợp nhất shell
  và kế thừa evidence cũ; không phải kiểm kê độc lập A0–A10/G0–G8. Hồ sơ cũ
  được giữ nguyên để bảo toàn lịch sử.
- Môi trường: fixture cô lập `http://127.0.0.1:8132`; DB/storage riêng, 500 credit
  fixture; không production và không gọi Gemini thật.
- Persona: creator/marketing không chuyên kỹ thuật cần tạo, chỉnh, tái sử dụng
  ảnh và thumbnail nhất quán mà hiểu trước giá phải trả.
- JTBD:
  1. Prompt/reference → 1–4 ảnh đúng tỉ lệ/chất lượng mong muốn.
  2. Chỉnh/remix output cũ mà không mất dữ liệu.
  3. Tạo thumbnail đúng brand/text/safe-zone, so sánh biến thể và tải/dùng lại.
- Device/locale: Chrome 1440×900 và 390×844; VI và `/en/`.
- Benchmark: Adobe Firefly, Midjourney Web, Gemini Image API và YouTube Studio.
- Reliability budget: quote/settlement model đúng 100%; validation loss = 0;
  partial outcome minh bạch 100%; orphan reference/output = 0; terminal output
  vẫn truy cập theo policy đã công bố.
- In scope: manifest/routes/templates/features/jobs, image input/provider/model/
  credit/storage/history/remix/brand/score/i18n/mobile/a11y/ops.
- Out of scope: sửa code, deploy, provider trả phí và chấm chất lượng hình AI thật.

## Gate A0

- [x] Scope/persona/JTBD/môi trường khóa trước khi chấm
- [x] Không dùng score H26.9 làm current truth
- [x] Không mutation production/không tiêu credit thật
