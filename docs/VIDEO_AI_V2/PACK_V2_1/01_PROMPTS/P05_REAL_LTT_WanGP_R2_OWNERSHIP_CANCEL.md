# P05 — REAL LTT↔WanGP + R2 + OWNERSHIP + CANCEL

## Mục tiêu
Chứng minh replacement path thật trước khi xóa legacy.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P05.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Start known C-CLOUD WanGP manually hoặc bằng controlled test process.
2. LTT validates user ownership.
3. Stage input qua signed/scoped media transfer.
4. Submit baseline T2V + ít nhất I2V/reference + character/motion mandatory path.
5. Map progress.
6. Cancel thật trong generation.
7. Timeout/retry/idempotency.
8. Export output vào LTT R2 trước `done`.
9. Test unauthorized key fail-closed.
10. Test large media.
11. Terminate/stop Pod và prove R2 output/history survive.
12. Record exact E2E traces redacted.

## Acceptance Gate
Real LTT browser/job → WanGP → R2 path PASS; cancel PASS; ownership PASS; output survives cloud shutdown.

## DỪNG
Nếu real path chưa PASS, P06 delete bị cấm.

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
- `SAFE FOR P06` if PASS

Không chạy P06.
