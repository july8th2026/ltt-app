# 00 — Audit Charter: Auto Sub Studio

- App/slug: Khắc phụ đề video / `autosubvideo`
- Version/commit: `c3b64da`
- Ngày snapshot: 2026-08-09
- Mode: **DEEP** theo LTT-AQA v1.0 (`docs/quy_tac_audit.md`)
- Môi trường/URL: fixture cô lập `http://127.0.0.1:8130/autosubvideo`,
  SQLite và LocalStorage riêng; không ghi production, không gọi provider trả phí.
- Persona chính: creator/marketing không chuyên kỹ thuật cần tạo, sửa, định dạng,
  dịch và xuất phụ đề chính xác mà không phải dùng phần mềm dựng chuyên nghiệp.
- JTBD chính:
  1. Nạp video hoặc transcript và có caption đồng bộ nhanh.
  2. Sửa nội dung/timing/speaker/style bằng preview đáng tin cậy.
  3. Biết đúng chi phí trước render, theo dõi/retry/download và tìm lại project.
- Device/language: Chrome 1440×900 và 390×844; VI và `/en/`; Asia/Saigon.
- Benchmark: CapCut, Descript, VEED, Adobe Premiere, Kapwing.
- Dữ liệu: video thật 3.005.870 byte do chủ sản phẩm chỉ định và SRT fixture;
  không render output mới, không tiêu credit.
- Trọng số: LTT-AQA v1.0, khóa trước khi chấm.
- Reliability budget: profile `media`; upload/attach P95 ≤15 giây cho file nhỏ,
  queue wait P95 ≤30 giây, autosave loss = 0, orphan artifact = 0, success ≥95%
  khi có tối thiểu 20 terminal render.
- In scope: manifest, project/transcript/style/timeline/render, ASR/diarize/translate,
  upload/storage/credit/job/recovery/i18n/responsive/a11y, benchmark và G0–G8.
- Out of scope: sửa code, deploy, production mutation, provider trả phí, blind-score
  độ chính xác ASR/render và tải thêm model.

## Gate A0

- [x] App/version/persona/JTBD rõ
- [x] Production boundary và dữ liệu test rõ
- [x] Benchmark/trọng số khóa trước khi chấm
- [x] Audit độc lập; không suy PASS từ H26 hay test cũ

