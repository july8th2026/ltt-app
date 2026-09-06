# P03 — LOCK ONE ENGINE + INTEGRATION CONTRACT + RESTORE POINT

## Mục tiêu
Khóa kiến trúc WanGP-only và thiết kế boundary trước khi viết LTT path.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P03.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Tạo ADR `VIDEO_ENGINE = WanGP`.
2. Tạo/verify tag hoặc archive branch `video-legacy-final-pre-wangp`.
3. Chọn direct MCP vs thin C-CLOUD bridge từ P01/P02 evidence.
4. Chốt canonical request/result/error/cancel contract.
5. Chốt baseline profile schema/versioning.
6. Chốt media transfer candidate, nhưng R2 thật sẽ chứng minh P05.
7. Chốt deletion manifest P06.
8. Chốt rằng new V2 code không có fallback/cascade sang legacy.

## Acceptance Gate
ADR + contract + restore point + deletion manifest hoàn chỉnh; integration choice có evidence.

## DỪNG
Dừng nếu P02 chưa PASS hoặc restore point chưa verify.

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
- `SAFE FOR P04` if PASS

Không chạy P04.
