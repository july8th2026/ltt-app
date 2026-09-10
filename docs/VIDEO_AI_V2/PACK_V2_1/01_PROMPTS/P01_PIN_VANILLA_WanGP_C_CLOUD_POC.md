# P01 — PIN + VANILLA WanGP C-CLOUD POC

## Mục tiêu
Pin exact WanGP source/license và chạy WanGP nguyên bản trên C-CLOUD.

## Đọc trước
1. Current repo `CLAUDE.md`
2. Relevant `AGENTS.md`
3. `docs/VIDEO_AI_V2/PROJECT_STATE.md` nếu đã tồn tại
4. V2.1 architecture + decisions
5. prompt phase này

## Luật bắt buộc
- Chỉ thực hiện P01.
- Không tự chạy phase kế.
- Không chạm B-LAN.
- Không sửa production tree trực tiếp.
- Không đưa secret vào docs/log/chat.
- Mã nguồn + provider state thật > tài liệu stale.
- New V2 implementation **không được fallback/cascade sang legacy**.
- Nếu tốn GPU: cost/resource preflight trước, cleanup verify sau.
- Dùng current repo gates từ `CLAUDE.md`, không tin command stale trong pack.

## Việc phải làm
1. Đọc exact upstream LICENSE/README/API/DEEPY/PLUGINS ở current SHA.
2. Ghi SHA + hashes + license gate internal-only.
3. Inventory RunPod resources/balance/rates/volume.
4. Chọn test Pod/GPU/region dựa dữ liệu hiện tại.
5. Boot pinned vanilla WanGP với persistent volume phù hợp.
6. Private access only.
7. Verify WebUI operator, API/MCP entrypoint, queue, basic cancel primitive.
8. Không theme, không LTT GUI, không fork core nếu chưa cần.
9. Stop/terminate paid compute sau evidence theo kế hoạch.

## Acceptance Gate
Pinned vanilla WanGP reproducible; private; API/MCP visible; cost/resource evidence; cleanup verified.

## DỪNG
Dừng nếu license gate fail, private access fail, hoặc spend vượt budget.

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
- `SAFE FOR P02` if PASS

Không chạy P02.
