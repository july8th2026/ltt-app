# P09 — TRUE INTERNAL E2E + FINAL CLEANUP + HANDOFF

## Mục tiêu
Nghiệm thu toàn bộ one-engine architecture từ LTT user đến WanGP cloud và dọn trạng thái cuối.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P09.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Real user-path browser test:
   login → LTT Video → cloud cold start → generate → R2 → history.
2. Test max profiles for mandatory tasks.
3. Test Deepy path.
4. Test cancel/timeout/error.
5. Test employee/admin permissions.
6. Verify WanGP WebUI not required on user path.
7. Search repo for legacy runtime refs.
8. Full LTT gate + secret scan.
9. Verify idle shutdown and final provider resource state.
10. Produce `FINAL_HANDOFF.md`:
    architecture, SHAs, profiles, model BOM, operations, start/stop, rollback, update WanGP procedure.
11. Keep commercial gate CLOSED.

## Acceptance Gate
Full gate PASS; browser E2E PASS; one engine only; cloud lifecycle PASS; docs reproducible; commercial gate CLOSED.

## DỪNG
If any critical gate fails, mark FAILED and stop; do not claim completion.

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
- `SAFE FOR PROGRAM COMPLETE` if PASS

Không chạy PROGRAM COMPLETE.
