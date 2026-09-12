# LTT-CMC state

| Field | Value |
|---|---|
| Source lineage | `admin-mvp-v3` |
| Source SHA | `34b4626e24e5dda419adf5b407e46f5fb744c454` |
| Canonical candidate | `main` |
| Canonical worktree | `D:\LTTSTUDIOSAPP` |
| CMC base SHA | `09b219a371e1261f0f0eef0e316c1ca42754cb78` |
| CMC base tag | `cmc-base-20260911` |
| Phase | `CMC_SYNC_BARRIER_READY` |

`CANONICAL_CANDIDATE` (`main`) đã được source-certified tại CMC base SHA, nhưng
chưa thay default branch ở remote. H45.6 vẫn phải chứng nhận LLM integration
trước final cleanup.

```text
CMC_BASE_BRANCH: main
CMC_BASE_WORKTREE: D:\LTTSTUDIOSAPP
STATUS: CMC_SYNC_BARRIER_READY
```

`SESSION_PROTECTED`: LLM dual-model recovery và LLM multijob predecessor. Voice
đã tự hòa vào `main` trước barrier; worktree Voice sạch và trỏ đúng CMC base,
nên handoff Voice là no-op, không phát lại lịch sử.

## Bằng chứng hiện có

- Thiết kế: `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`.
- Master plan: `docs/superpowers/plans/2026-09-11-ltt-cmc.md`.
- Task hiện tại: H45.5 sync barrier hoàn tất; chờ LLM handoff trước H45.6.
- Reconciliation matrix: `docs/LTT_CMC/reconciliation.json` (36 branches,
  25 reflog-only commits, 0 `RECONCILE`, 0 rescue refs).
- Normalization baseline: `docs/LTT_CMC/NORMALIZATION_BASELINE.md` (một Alembic
  head, registry identities duy nhất, 48 test pass và bốn frontend source hash
  khớp generated metadata).
- Barrier: `docs/LTT_CMC/CMC_SYNC_BARRIER.md`; Voice no-op handoff và LLM dual
  handoff đã điền bằng snapshot thật.
- Source certification: **PASS 33/33**, 950,7 giây,
  `test-results/gates/20260911T235957Z-25548.json`, cây không đổi giữa lượt.
- Production deployment by LTT-CMC: `NONE`. Phiên Voice đã deploy riêng trước
  barrier; CMC không mở rộng hành động đó sang LLM hay hệ thống khác.
