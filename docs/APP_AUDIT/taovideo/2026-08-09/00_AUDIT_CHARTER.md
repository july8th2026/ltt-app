# 00 — Audit Charter: Tạo Video Seedance

- App/slug: Tạo Video Seedance / `taovideo`
- Version/commit: `a31d028`
- Ngày snapshot: 2026-08-09
- Mode: **DEEP**
- Môi trường/URL: fixture cô lập `http://127.0.0.1:8130/taovideo`, SQLite và
  LocalStorage riêng; source, test và browser thật. Không ghi production.
- Production authorization: **KHÔNG** mutation; trạng thái public từ H26 chỉ là
  baseline, không thay thế audit độc lập.
- Persona chính: người làm nội dung không chuyên kỹ thuật cần tạo clip ngắn từ
  mô tả và ảnh/video/audio tham chiếu, biết chi phí trước khi chạy.
- Ba JTBD:
  1. Mô tả ý tưởng, chọn model/định dạng dễ hiểu và tạo một hoặc hai biến thể.
  2. Dùng ảnh, video, audio và tài sản cũ đúng vai trò để giữ chủ thể/chuyển động.
  3. Theo dõi, tải, thử lại, hủy hoặc nâng cấp video mà không mất prompt, dữ
     liệu hay credit ngoài dự kiến.
- Device/language: Chrome 1440×900 và 390×844; VI và `/en/`; Asia/Saigon.
- Benchmark: Runway, Google Flow/Veo, Adobe Firefly Video, Luma Dream Machine,
  Kling AI Video, Pika.
- Dữ liệu test: fixture có đủ queued/running/done/error/cancelled; ảnh và video
  thật do chủ sản phẩm chỉ định; không gọi provider trả phí, không render output
  mới và không dùng dữ liệu production.
- Trọng số: giữ nguyên LTT-AQA v1.0, khóa trước khi chấm.
- Reliability budget: profile `api`; success ≥95% khi có ≥20 terminal job;
  queue wait P95 ≤30 giây; stale job/event failure = 0. Provider render time báo
  riêng, không trộn vào queue wait.
- In scope: manifest/UI/route, reference lifecycle, model/provider, credit,
  ownership, job/recovery, i18n/responsive/a11y, benchmark và G0–G8.
- Out of scope: sửa code, deploy, gọi provider tốn credit, blind-score output,
  dữ liệu production và mở thêm model.

## Gate A0

- [x] App/version/persona/JTBD rõ
- [x] Mode và ranh giới production rõ
- [x] Benchmark/trọng số khóa trước khi chấm
- [x] Audit tuần tự, không dùng kết quả portfolio để suy PASS
