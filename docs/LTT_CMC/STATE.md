# LTT-CMC state

| Field | Value |
|---|---|
| Source lineage | `admin-mvp-v3` |
| Source SHA | `34b4626e24e5dda419adf5b407e46f5fb744c454` |
| Canonical candidate | `main` |
| Canonical worktree | `D:\LTTSTUDIOSAPP` |
| Phase | `PHASE_1_NORMALIZATION_BASELINED` |

`CANONICAL_CANDIDATE` hiện chỉ là nhánh đang xây dựng; chưa được chứng nhận và
chưa thay default branch ở remote.

`SESSION_PROTECTED`: Voice reconciliation, LLM dual-model recovery và LLM
multijob predecessor. LTT-CMC không được mutate các worktree đó trước sync
barrier.

## Bằng chứng hiện có

- Thiết kế: `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`.
- Master plan: `docs/superpowers/plans/2026-09-11-ltt-cmc.md`.
- Task hiện tại: H45.3 hoàn tất; chuẩn bị H45.4 candidate certification.
- Reconciliation matrix: `docs/LTT_CMC/reconciliation.json` (36 branches,
  25 reflog-only commits, 0 `RECONCILE`, 0 rescue refs).
- Normalization baseline: `docs/LTT_CMC/NORMALIZATION_BASELINE.md` (một Alembic
  head, registry identities duy nhất, 48 test pass và bốn frontend source hash
  khớp generated metadata).
- Production deployment: `NOT_AUTHORIZED_BY_CMC`.
