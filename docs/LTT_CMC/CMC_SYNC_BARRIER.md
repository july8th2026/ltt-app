# LTT-CMC sync barrier

Chụp và chứng nhận ngày 2026-09-12.

| Field | Value |
|---|---|
| `CMC_BASE_BRANCH` | `main` |
| `CMC_BASE_WORKTREE` | `D:\LTTSTUDIOSAPP` |
| `CMC_BASE_SHA` | `09b219a371e1261f0f0eef0e316c1ca42754cb78` |
| Immutable tag | `cmc-base-20260911` |
| `STATUS` | `CMC_SYNC_BARRIER_READY` |

## Chứng nhận source

- Frontend source so với source lineage `34b4626e`: `NOT_NEEDED: source
  unchanged`; không rebuild để tạo churn.
- `python tools\scan_source_secrets.py`: **PASS**, 3.281 tệp, 784.349 dòng,
  0 finding.
- `python tools\gate.py --cho 60`: **PASS 33/33**, 950,7 giây; report
  `test-results/gates/20260911T235957Z-25548.json`.
- Gate giữ `cpu_nhieu` + `postgres_test`, tải lúc bắt đầu 0,8/20 lõi
  (`RANH`), `cay_da_doi_giua_chung=false` và report ghi đúng SHA ở trên.
- Alembic head sau Voice: `d9a1f6c2b3e5`, đúng một head.

## Sự kiện Voice xảy ra trước barrier

Trong lúc CMC chứng nhận baseline trước Voice, phiên Voice đã tự hòa `main` vào
RC tại `f98be1be`, fast-forward RC vào `main`, rồi hoàn tất Tầng 2 tại
`09b219a3`. CMC không reset, cherry-pick hay viết vào worktree Voice. Lượt gate
đầu trên `28f6a089` vẫn hợp lệ cho SHA đó nhưng không được dùng làm baseline
cuối; một lượt sau trên `5330711c` xanh 33/33 nhưng bị loại vì Voice sửa test
giữa lượt. Lượt cuối nêu trên chứng nhận chính `09b219a3` trên cây đứng yên.

Do đó Voice đã nằm trong immutable baseline. `HANDOFF_VOICE.md` là handoff
no-op để ngăn phát lại; LLM phải bắt đầu từ tag này và không merge lịch sử
Voice hoặc `main` vào hai source worktree.

## Ranh giới

- Tag không được move, rewrite, delete hoặc tái sử dụng cho SHA khác.
- Không deploy, đổi default branch, xóa branch/worktree/ref/archive tại barrier.
- LTT-CMC không thực hiện deploy. Phiên Voice đã deploy riêng trước barrier;
  bằng chứng và phán quyết của việc đó nằm trong `docs/LTT_VOICE/HOP_NHAT/`.
- Chỉ `cmc/llm-dual-reconcile` được phép mang LLM vào sau barrier; final CMC sẽ
  chứng nhận hợp nhất rồi mới dùng cleanup ledger.
