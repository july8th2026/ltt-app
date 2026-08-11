# H32.2 — Audit charter: Prompt AI OMMI

- Scope: yêu cầu `PromptAI/MoTa.txt`, ảnh `AnhThamKhao.png`, app hiện hành và
  module Prompt Seedance Studio tại `D:\BOT GEMINI` ở chế độ chỉ đọc.
- Profile: LTT-AQA `DEEP`, customer-facing; không phục dựng dashboard quản trị
  team trong ảnh thành UI khách hàng.
- Journey: tạo project → điền brief → chọn Style/Meta/Snippet → lưu → preview
  miễn phí → preflight → quote. Apply job được kiểm bằng API regression vì
  fixture không cấu hình provider/worker thật.
- Dữ liệu: SQLite/storage/tài khoản test riêng tại cổng 8141; production 8100
  không bị tác động.
- PASS: thư viện phải tham gia prompt thật, draft không mất khi click, quote
  khóa đúng payload và job hoàn tất phải apply được theo optimistic revision.

Rollback: revert commit H32.2; catalog tích hợp là immutable và không có
migration dữ liệu.
