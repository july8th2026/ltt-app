# 07 — Roadmap

1. **Phase 0:** test âm customer/anonymous và nhãn direct-vs-queue. PASS G2/G4.
2. **Phase 1:** thêm artifact nhỏ → storage → download → cleanup qua queue.
3. **Phase 2:** scheduled synthetic, correlation ID, duration/result history.
4. **Phase 3:** alert threshold và release evidence export.
5. **Phase 4–5:** canary/rollback rehearsal; không deploy UI customer.

Rollback: bỏ synthetic schedule/artifact handler mới; giữ `demo.reverse` hiện
tại. Không cần Decision Gate customer vì surface luôn INTERNAL.

