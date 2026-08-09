# 00 — Audit Charter: Prompt AI OMMI

- App/slug: Prompt AI OMMI / `prompt_ai_ommi`
- Version/commit nền: `217fb10`
- Ngày snapshot: 2026-08-09
- Mode: **DEEP** theo LTT-AQA v1.0 (`docs/quy_tac_audit.md`)
- Môi trường/URL: fixture cô lập `http://127.0.0.1:8131/prompt-ai-ommi`,
  SQLite và storage riêng; không ghi production, không gọi provider trả phí.
- Persona chính: creator/marketing không chuyên kỹ thuật cần biến brief thành bộ
  prompt, storyboard và tài sản hình/video nhất quán.
- JTBD chính:
  1. Tạo project từ brief và tài nguyên tham chiếu.
  2. Dùng AI Director tạo storyboard nhất quán, sửa/chạy lại từng cảnh.
  3. Chuyển cảnh sang công cụ tạo ảnh/video, theo dõi job, phiên bản và chi phí.
- Device/language: Chrome 1440×900 và 390×844; VI và `/en/`; Asia/Saigon.
- Benchmark chính thức: LTX Studio, Google Flow, Runway, Adobe Firefly Boards,
  FLORA và Freepik Spaces.
- Dữ liệu: project, scene và một ảnh fixture nội bộ; 200 credit fixture. Mọi quote
  đều bị hủy trước provider, không tiêu credit thật.
- Reliability budget: autosave loss = 0; paid-result apply success = 100%; orphan
  artifact = 0; queue success ≥95% khi có tối thiểu 20 terminal jobs.
- In scope: manifest, current React workspace, `/classic`, project/resource/
  library/storyboard, provider/job/credit/storage, i18n/responsive/a11y, G0–G8.
- Out of scope: sửa code, deploy, production mutation, provider trả phí và đánh
  giá thẩm mỹ đầu ra AI bằng blind panel.

## Gate A0

- [x] App/version/persona/JTBD rõ
- [x] Production boundary và dữ liệu test rõ
- [x] Benchmark/trọng số khóa trước khi chấm
- [x] Audit độc lập; test xanh không được suy thành release-ready
