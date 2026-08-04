# PROMPT AI OMMI — Audit Charter

- App đích: **PROMPT AI OMMI**
- Slug kỹ thuật đề xuất: `prompt_ai_ommi`
- URL đề xuất: `/prompt-ai-ommi`
- Nguồn tham chiếu chỉ đọc: `D:\BOT GEMINI\app\modules\seedance`
- Ngày snapshot: 2026-08-04
- Mode: **DEEP — pre-build/source-to-product audit**
- Production authorization: **KHÔNG**; phiên này không sửa BOT GEMINI, không
  build app, không deploy và không dùng dữ liệu production.
- Persona chính: creator/marketer cần biến ý tưởng hoặc kịch bản thành gói
  prompt nhiều cảnh nhất quán, có thể chuyển tiếp sang app tạo ảnh/video.
- Ba JTBD:
  1. Từ brief và tài sản tham chiếu tạo prompt production-ready theo từng cảnh.
  2. Giữ nhất quán nhân vật, bối cảnh, phong cách và continuity khi lặp/sửa.
  3. Quản lý phiên bản, storyboard, export và handoff mà không làm mất nguồn.
- Thiết bị đích: desktop-first 1366–1920 px; tablet/mobile hỗ trợ review,
  chỉnh nhanh và theo dõi job, không ép toàn bộ studio ba cột lên 390 px.
- Benchmark: LTX Studio, Google Flow, Runway Workflows/References và Freepik
  Spaces; chỉ dùng tài liệu chính thức hiện hành làm bằng chứng thị trường.
- In scope: toàn bộ năng lực hữu ích của Prompt Seedance Studio, ownership,
  admin/user split, dữ liệu, job, credit, provider, storage, IA/UI, test,
  rollout và rollback.
- Out of scope phiên khảo sát: copy code, nhập CSDL thật, gọi provider, chạy
  test bên BOT GEMINI, thay `platform_core/`/`server/`, deploy production.
- Nguồn luật: Q3, Q5, Q26, Q30, Q43, Q49, Q51, Q52 và Q65.

## Evidence hiện có

| ID | Cấp | Bằng chứng |
|---|---|---|
| OMMI-E01 | E1 | Đọc manifest/config/routes/database/service/UI/test của module nguồn |
| OMMI-E02 | E1 | Đếm tĩnh: 194 file liên quan, 47.665 dòng, 261 endpoint, 49 bảng |
| OMMI-E03 | E1 | Đọc hợp đồng LTT: AppProject, Job, credit, Storage, APIKEYS, provider, ToolSpec |
| OMMI-E04 | E1 | Tài liệu chính thức của bốn benchmark nêu trên |

Chưa có E2/E3 từ browser hoặc job thật. Vì vậy điểm UI, task success, hiệu năng
và release gate trong hồ sơ này là baseline có điều kiện, không phải nghiệm thu.

## Gate A0

- [x] App/persona/JTBD và ranh giới production rõ.
- [x] Mode và evidence confidence rõ.
- [x] Benchmark và trọng số khóa trước khi chấm.
- [x] Đích là app prompt-production độc lập, không phải một trang cấu hình của
  app Tạo video và không phải bản sao runtime BOT GEMINI.

