# 00 — Audit charter: Demo hạ tầng

- **Ngày/mode:** 2026-08-09 · DEEP theo runtime contract.
- **Persona:** operator/developer kiểm chuỗi web → Job → worker → credit; không
  phải sản phẩm bán cho customer.
- **JTBD:** smoke test handler; nghiệm thu queue/credit/refund; kiểm quyền admin.
- **Môi trường:** local fixture, browser customer test; không production.
- **Benchmark:** canary/synthetic transaction/internal diagnostic pattern,
  không so UI customer. 8 điểm AI chuyển sang reliability/operations.

**G0 PASS.** `surface=admin`, `lifecycle=internal`, giữ vĩnh viễn làm fixture.

