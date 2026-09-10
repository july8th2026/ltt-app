# P06 — ONE-ENGINE CUTOVER + DELETE LEGACY RUNTIME

## Mục tiêu
Sau replacement E2E PASS, xóa video-specific legacy runtime để repo chỉ còn WanGP path.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P06.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Verify P05 PASS and restore tag/branch.
2. Disable/remove any legacy route/provider registration first.
3. Delete only items marked DELETE_AT_P06.
4. Preserve generic storage/jobs/credits/RunPod helpers used elsewhere.
5. Rewrite/remove implementation-specific tests; retain behavior/invariant tests.
6. Search old symbols, endpoint IDs, workflow names.
7. Target zero executable/runtime legacy references.
8. Run full relevant gates.
9. Do NOT destructively delete old cloud resources unless user authorization for those specific resources is already explicit; list them as cleanup candidates.

## Acceptance Gate
Repository gates PASS; one executable engine path; zero runtime legacy refs; restore point valid.

## DỪNG
Nếu generic regression appears, restore/refactor generic dependency rather than retaining legacy engine fallback.

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
- `SAFE FOR P07` if PASS

Không chạy P07.
