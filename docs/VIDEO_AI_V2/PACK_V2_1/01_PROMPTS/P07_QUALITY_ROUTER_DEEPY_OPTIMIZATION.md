# P07 — QUALITY ROUTER + DEEPY OPTIMIZATION

## Mục tiêu
Từ baseline profiles, benchmark và promote profile chất lượng cao; cấu hình Deepy theo policy LTT.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P07.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Shortlist candidate models per task using WanGP capability metadata.
2. Audit model/weight licenses.
3. Benchmark fixed corpus: adherence, identity/reference, motion, temporal consistency, artifacts, runtime/VRAM/cost.
4. Promote winners:
   `ltt.video.<task>.max.v1`.
5. Keep baseline profiles for reproducibility/diagnostics, not runtime fallback engine.
6. Map curated max profiles/templates to Deepy.
7. Benchmark local vs remote Deepy if needed.
8. Lock LTT Deepy guidance:
   quality > adherence > identity > temporal > speed > cost.
9. Agent may choose only allowed task/profile policy unless explicitly authorized.

## Acceptance Gate
Quality winners reproducible; Deepy uses curated defaults; no unlicensed/unknown model winner.

## DỪNG
Dừng nếu no clear winner; report tie and one bounded follow-up benchmark.

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
- `SAFE FOR P08` if PASS

Không chạy P08.
