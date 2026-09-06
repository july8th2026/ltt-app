# END-OF-PHASE / NEW CHAT HANDOFF

Cuối mỗi phase:

> Cập nhật `docs/VIDEO_AI_V2/PROJECT_STATE.md` bằng trạng thái THỰC:
> phase/status, branch/worktree/HEAD, dirty files, WanGP SHA,
> cloud resources/state, baseline/max profiles, spend,
> tests/gates/browser evidence, blockers, decisions, exact_next_action.
> Không bắt đầu phase kế.
> Chạy `git status`.
> Commit durable state/code khi phù hợp.
> Báo `SAFE TO START NEW CHAT FOR Pxx`.

Chat mới:

> Đọc `CLAUDE.md`, `AGENTS.md`,
> `docs/VIDEO_AI_V2/PROJECT_STATE.md`,
> V2.1 architecture/decisions,
> và prompt Pxx.
> Xác minh branch/worktree/HEAD trực tiếp bằng git.
> Chỉ thực hiện `exact_next_action` của Pxx.
> Không phục hồi kiến trúc V3/legacy từ chat cũ.
