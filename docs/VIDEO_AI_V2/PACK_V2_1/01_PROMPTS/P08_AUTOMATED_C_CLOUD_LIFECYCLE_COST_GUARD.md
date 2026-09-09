# P08 — AUTOMATED C-CLOUD LIFECYCLE + COST GUARD

## Mục tiêu
Tự động hóa start/health/busy/idle-stop/reconcile sau khi engine path đã ổn định.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P08.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Read current RunPod API/OpenAPI at execution time.
2. Implement ensure_running with lock/lease.
3. Health = WanGP + required profile/model ready.
4. Handle two jobs arriving while stopped.
5. Handle job arriving while stopping.
6. Start timeout/failure cleanup.
7. Idle TTL + drain + stop/terminate compute.
8. Orphan reconciliation.
9. Hourly/monthly budget guard.
10. Test with short TTL and real provider state.
11. Never require serverless legacy endpoint.

## Acceptance Gate
No double-start/orphan; health meaningful; idle shutdown verified; budget guard fail-closed.

## DỪNG
Dừng nếu provider API contract cannot safely support lifecycle; document stable fallback API mechanism, not legacy video engine.

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
- `SAFE FOR P09` if PASS

Không chạy P09.
