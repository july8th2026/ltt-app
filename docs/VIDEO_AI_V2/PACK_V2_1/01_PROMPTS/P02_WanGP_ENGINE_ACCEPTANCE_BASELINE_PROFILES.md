# P02 — WanGP ENGINE ACCEPTANCE + BASELINE PROFILES

## Mục tiêu
Chứng minh WanGP engine thực sự bao phủ task cần thiết và lưu settings baseline; chưa yêu cầu LTT R2/lifecycle.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P02.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Chạy `P02 WanGP Engine Acceptance Matrix`.
2. Real generation cho mandatory tasks:
   T2V, I2V, reference, motion/control, character; edit nếu V2 MVP.
3. Test progress/cancel/timeout behavior.
4. Test native media ingest/output retrieval.
5. Test restart/persistence.
6. Test Deepy availability/capability tối thiểu.
7. Với mỗi task PASS, lưu exact model/settings/input roles thành
   `ltt.video.<task>.baseline.v1`.
8. Ghi model license status cho các baseline model.
9. Chưa benchmark winner quality, chưa tự động cloud lifecycle.

## Acceptance Gate
Mọi mandatory engine capability PASS bằng real evidence và có reproducible baseline profiles.

## DỪNG
Nếu mandatory task fail, legacy không được xóa. Chỉ đề xuất patch/adaptor nhỏ nhất hoặc đổi WanGP-supported model và retest.

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
- `SAFE FOR P03` if PASS

Không chạy P03.
