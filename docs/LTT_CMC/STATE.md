# LTT-CMC state

| Field | Value |
|---|---|
| Source lineage | `admin-mvp-v3` |
| Source SHA | `34b4626e24e5dda419adf5b407e46f5fb744c454` |
| Canonical candidate | `main` |
| Canonical worktree | `D:\LTTSTUDIOSAPP` |
| CMC base SHA | `09b219a371e1261f0f0eef0e316c1ca42754cb78` |
| CMC base tag | `cmc-base-20260911` |
| Phase | `FINAL_INTEGRATED_PENDING_L3` |

`CANONICAL_CANDIDATE` (`main`) đã nhận ba commit tài liệu Voice hậu-baseline và
merge `cmc/llm-dual-reconcile`. Chưa có L3 trên kết quả hợp nhất, chưa thay
default branch ở remote và chưa cleanup.

```text
CMC_BASE_BRANCH: main
CMC_BASE_WORKTREE: D:\LTTSTUDIOSAPP
STATUS: FINAL_INTEGRATED_PENDING_L3
```

Phần chức năng Voice đã nằm trong baseline. Quét live sau khi phiên Voice đóng
phát hiện thêm ba commit tài liệu; chúng đã được port riêng vào `main`, không
phát lại lịch sử chức năng. LLM canonical đã được nhập bằng merge commit
`c556c411`; Source A Multi-Job vẫn được bảo toàn nguyên trạng để chờ cleanup
ledger, không có hunk nào cần port thêm theo `CMC_SOURCE_STATE.md`.

## Bằng chứng hiện có

- Thiết kế: `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`.
- Master plan: `docs/superpowers/plans/2026-09-11-ltt-cmc.md`.
- Task hiện tại: H45.6 đã tích hợp nguồn; đang chuẩn bị một L3 trên `main`.
- Reconciliation matrix: `docs/LTT_CMC/reconciliation.json` (36 branches,
  25 reflog-only commits, 0 `RECONCILE`, 0 rescue refs).
- Normalization baseline: `docs/LTT_CMC/NORMALIZATION_BASELINE.md` (một Alembic
  head, registry identities duy nhất, 48 test pass và bốn frontend source hash
  khớp generated metadata).
- Barrier: `docs/LTT_CMC/CMC_SYNC_BARRIER.md`; sai lệch Voice hậu-barrier đã
  được xử lý bằng ba commit tài liệu riêng trước merge LLM.
- Source certification: **PASS 33/33**, 950,7 giây,
  `test-results/gates/20260911T235957Z-25548.json`, cây không đổi giữa lượt.
- Production deployment by LTT-CMC: `NONE`. Voice và LLM đã deploy trong các
  phiên sở hữu trước khi bàn giao; CMC không deploy lại hoặc thay đổi production.

## Ngoại lệ đang được bảo toàn

- `D:\LTTSTUDIOSAPP-vps-v4` có WIP chưa commit. Không thuộc Voice/LLM và không
  được sửa, xóa hay gộp trong H45; cleanup ledger phải ghi
  `NEED_RECONCILIATION`.
- Worktree Multi-Job Source A còn năm tệp dirty nhưng đã được Source B thay thế
  theo đối soát từng tệp. Giữ nguyên đến ledger; không stash/reset/commit hộ.
- Gate nhánh LLM ở `4bc3ea48` có 30 PASS/3 BOQUA và xảy ra trước ba commit bàn
  giao cuối, nên không được dùng làm chứng nhận HEAD hợp nhất.
