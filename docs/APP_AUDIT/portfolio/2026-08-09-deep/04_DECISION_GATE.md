# Portfolio Decision Gate

Khuyến nghị mặc định **A** để Dev khóa trước BUILD:

1. **A — Scope:** đóng P0/P1 và shared foundation trước feature mới.
2. **A — Socialbot:** operator-only, security maintenance; không thay Q10.
3. **A — Agent:** literal Text/Asset là source 0-credit; Generate là hành động
   trả phí riêng; một workflow library/customer mental model.
4. **A — Storage:** một artifact registry dùng chung; không GC theo Job đơn lẻ.
5. **A — Money:** server quote canonical, atomic max hold, itemized receipt,
   reconciler cho mọi terminal/crash path.
6. **A — Provider:** không commercial nếu chưa có quyền/retention/DPA/economics
   evidence; UNKNOWN không đổi thành PASS.
7. **A — UI:** customer mode mặc định; dev details chỉ advanced/operator;
   dark/light theo app quyết định nhưng design token chung.
8. **A — Delivery:** tuần tự theo `02_DEPENDENCY_AND_SEQUENCE.md`; không build
   tất cả feature đối thủ.
9. **A — Testing:** targeted trong vòng lặp, browser E3 mỗi slice, full gate ở
   release/high-risk shared contract; không lặp full suite vô ích mỗi file.
10. **A — Deploy:** audit không cấp quyền deploy; chỉ deploy sau P5/canary/
    rollback và lệnh deploy rõ ràng.

## Trạng thái sau audit

- Audit inventory: **DONE**.
- Decision Gate: **chờ khóa trước BUILD**.
- Runtime fixes: **0% trong H27** vì H27 cố ý audit-only.
- Hạng mục đầu tiên sau khi khóa A: **Socialbot route authorization**, sau đó
  **Agent P0 exactly-once**.

