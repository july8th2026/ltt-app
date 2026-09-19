# 00 — Audit Charter H26.10C

- App: `agent` / LTT Agent AI
- Snapshot: source sau H26.10B, ngày 2026-08-09; chưa deploy
- Mode: STANDARD delta theo LTT-AQA v1.0, kế thừa hồ sơ DEEP 2026-08-04
- Môi trường: fixture local cô lập `127.0.0.1:8111`, dữ liệu test
- Persona: creator không phải dev, cần ghép Text/Image/Video/Audio thành luồng
- JTBD: tạo nhanh flow mẫu; sửa/chạy một block có dependency; biết trước chi phí
- Viewport: desktop 1920 px và mobile 390 px; tiếng Việt
- Benchmark khóa: PlenX Workflow và FLORA từ bằng chứng hands-on 2026-08-04/05;
  không suy diễn tính năng mới của đối thủ trong vòng delta này
- In scope: presentation Q68, graph, run scope, credit, persistence, responsive
- Out of scope: provider trả phí, load/soak, canary/production và user study E4

## Gate A0

PASS. Đây là app dành cho khách hàng; ToolSpec/provider/schema kỹ thuật không
được trở thành mental model chính. H26.11–12 sở hữu performance/ops/deploy.
