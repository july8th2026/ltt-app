# P00 — RECOVER + AUDIT LEGACY + FRESH V2 BASELINE

## Mục tiêu
Tạo điểm xuất phát sạch từ current trunk và inventory chính xác legacy trước khi đụng cloud.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P00.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Xác định current trunk thật, HEAD, worktree, dirty state.
2. Xác định legacy video branch/commits nhưng không merge.
3. Inventory path/symbol/runtime resource legacy.
4. Phân loại KEEP_GENERIC / REUSE_CONCEPT / DELETE_AT_P06 / ARCHIVE_DOC_ONLY.
5. Tạo `docs/VIDEO_AI_V2/` và state/decisions/inventory.
6. Tạo fresh V2 branch/worktree từ current trunk.
7. Ghi: one-engine target, internal-only, B-LAN untouched.
8. Chưa xóa, chưa port legacy runtime.

## Acceptance Gate
Fresh V2 branch sạch; inventory path-level có bằng chứng; runtime không đổi.

## DỪNG
Dừng nếu không xác định được trunk thật hoặc có thay đổi ngoài phạm vi không thể tách an toàn.

## State bắt buộc
Cập nhật `docs/VIDEO_AI_V2/PROJECT_STATE.md`:
- phase/status
- branch/worktree/HEAD
- WanGP upstream SHA / LTT patch SHA nếu có
- legacy_runtime status
- cloud resource IDs + state
- baseline/quality profiles
- measured spend
- tests/gates
- browser evidence
- blockers
- decisions
- exact_next_action

Commit durable state/code before handoff when appropriate.

## Báo cáo cuối phase
- changed files
- commit SHA
- tests/gates
- cloud resources + cost
- PASS/FAIL
- exact blocker if FAIL
- `SAFE FOR P01` if PASS

Không chạy P01.
