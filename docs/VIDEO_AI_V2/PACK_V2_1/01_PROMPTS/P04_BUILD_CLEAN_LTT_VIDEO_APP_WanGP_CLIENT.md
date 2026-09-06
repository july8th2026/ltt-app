# P04 — BUILD CLEAN LTT VIDEO APP + WanGP CLIENT

## Mục tiêu
Xây user-facing LTT Video app và WanGP-only client bằng baseline profiles; chưa xóa legacy source.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P04.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Audit current app contract và current trunk.
2. Tạo sạch `apps/lttvideo` theo contract hiện hành.
3. Internal-only/public false/api_exposed false.
4. GUI: Create / Agent entry / History.
5. Request-bound uploads; không Asset Library.
6. Experience/task mapping dùng baseline profiles P02.
7. Implement `WanGPClient` duy nhất theo P03 contract.
8. Mock/fake tests: request, validation, progress, cancel, result.
9. Không import/call legacy worker/provider.
10. Browser verify UI theo current LTT rules.

## Acceptance Gate
Native LTT UI + only-one-engine client tồn tại; mock contract pass; no legacy fallback reference in new path.

## DỪNG
Dừng nếu phải hardcode app vào platform/server trái contract hoặc UI phụ thuộc Gradio.

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
- `SAFE FOR P05` if PASS

Không chạy P05.
