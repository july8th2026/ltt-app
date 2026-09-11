# LTT-CMC Final Integration and Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the certified Voice and LLM handoffs into `main`, certify the combined source, switch repository authority, and remove all retired Git/session state after a separate destructive approval.

**Architecture:** Both handoffs must descend from the same immutable CMC baseline. Integrate Voice first and LLM second with semantic review, run one final full gate, then migrate default-branch controls before presenting a literal deletion ledger.

**Tech Stack:** Git, GitHub CLI or authenticated repository UI, Python gate tooling, Alembic, pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`

## Global Constraints

- Do not begin until both handoff branches are clean, tested and based on the exact same `CMC_BASE_SHA`.
- Never deploy production in this plan.
- Before all heavy runs, use both load/lock commands and obey `BẬN`/`QUÁ TẢI`.
- No branch/worktree/session/ref/archive deletion occurs before a fresh literal ledger and separate user approval.
- Do not use force push, recursive filesystem deletion, `git gc` or `git prune`.

---

### Task 1: Integrate the Voice handoff

**Files:**
- Modify through integration: the exact files recorded in `docs/LTT_VOICE/HOP_NHAT/CMC_SOURCE_STATE.md`
- Modify: `docs/LTT_CMC/STATE.md`

**Interfaces:**
- Produces: `main` containing the certified Voice capability once.
- Consumes: clean `cmc/voice-reconcile` with recorded tests.

- [ ] Verify main worktree is clean, current branch is `main`, and Voice merge-base equals the recorded CMC baseline.
- [ ] Review `git cherry -v main cmc/voice-reconcile` and the semantic matrix; skip patch-equivalent commits.
- [ ] Cherry-pick the reviewed Voice commits in dependency order. Resolve shared files semantically; never accept an entire side.
- [ ] Run Voice focused tests, migration one-head tests and `python tools\gate.py --doi` after load checks.
- [ ] Record actual integrated source commits and main HEAD; secret-scan and commit any reconciliation fix.

### Task 2: Integrate the LLM handoff

**Files:**
- Modify through integration: the exact files recorded in `docs/ltt_llm_dual/CMC_SOURCE_STATE.md`
- Modify: `docs/LTT_CMC/STATE.md`

**Interfaces:**
- Produces: combined Voice + dual-model/multijob canonical source.
- Consumes: clean LLM handoff and Task 1 state.

- [ ] Verify the LLM merge-base equals the same recorded CMC baseline.
- [ ] Review patch equivalence against the post-Voice `main`; do not replay any duplicated WIP patch.
- [ ] Cherry-pick reviewed LLM commits and resolve shared registry/migration/runtime files against the already integrated Voice state.
- [ ] Run LLM focused tests, full registry tests, migration one-head tests and `python tools\gate.py --doi` after load checks.
- [ ] Record actual integrated commits and main HEAD; secret-scan and commit reconciliation fixes.

### Task 3: Certify the combined canonical source

**Files:**
- Modify: `docs/LTT_CMC/STATE.md`
- Modify: `docs/KE_HOACH_TRIEN_KHAI.md`
- Modify: `docs/NHAT_KY.md`
- Create: `docs/LTT_CMC/FINAL_REPORT.md`

**Interfaces:**
- Produces: `CANONICAL_CERTIFIED` evidence on a clean, unchanged tree.
- Consumes: combined main from Tasks 1–2.

- [ ] Verify one Alembic head, unique registry identities, model-profile consistency and frontend source hash.
- [ ] If frontend/test source changed, build release as the final file-generating action before L3.
- [ ] Run both load checks; wait for an acceptable window.
- [ ] Run `python tools\scan_source_secrets.py` and exactly one `python tools\gate.py`; require zero findings and L3 PASS.
- [ ] Write exact command/results, final full SHA, skipped environment checks and rollback boundary to `FINAL_REPORT.md` and journal; never call a skip a pass.
- [ ] Mark integration/certification plan items complete, secret-scan and commit the evidence.

### Task 4: Move repository authority to `main`

**Files:**
- Modify: `.github/workflows/gate-quick.yml`
- Modify only active references: `docs/QUY_TRINH_WORKTREE.md`, `docs/16_CAP_NHAT_VA_DEPLOY.md`, `CLAUDE.md`
- Modify: `docs/LTT_CMC/FINAL_REPORT.md`

**Interfaces:**
- Produces: remote default/protected branch `main`; no new work targets old branches.
- Consumes: `CANONICAL_CERTIFIED` main SHA.

- [ ] Push `main` normally and verify remote SHA equals local SHA.
- [ ] Change the private GitHub repository default branch to `main` using `gh repo edit giaitritruyenthongltt-spec/LTTSTUDIOSAPP --default-branch main`, or the authenticated repository UI if GitHub CLI is unavailable.
- [ ] Move branch-protection/ruleset targets to `main`; verify PR base defaults to `main`.
- [ ] Reduce CI PR targets from `[main, admin-mvp-v3, master]` to `[main]`; run the focused authority test and L1 after load checks.
- [ ] Commit/push the transition and verify a fresh remote query reports default HEAD at the certified `main` SHA.

### Task 5: Present and approve the destructive cleanup ledger

**Files:**
- Create: `docs/LTT_CMC/CLEANUP_LEDGER.md`

**Interfaces:**
- Produces: literal approved targets; consumes final inventory and integration evidence.

- [ ] Re-run inventory after repository authority migration.
- [ ] List every linked worktree with absolute resolved path, branch, HEAD, status and integration evidence.
- [ ] List every local/remote branch, CMC rescue ref, temporary bundle/patch/archive and Claude session state with exact target and disposition.
- [ ] Prove every deletion target lies within its intended Git common directory, repository workspace, configured temporary backup directory or identified Claude session directory.
- [ ] Present the completed ledger and request separate explicit destructive approval. Stop here until approval; prior blanket permission is not substituted for this checkpoint.

### Task 6: Execute only the approved cleanup ledger

**Files:**
- Modify: `docs/LTT_CMC/CLEANUP_LEDGER.md`
- Modify: `docs/LTT_CMC/FINAL_REPORT.md`
- Modify: `docs/KE_HOACH_TRIEN_KHAI.md`
- Modify: `docs/NHAT_KY.md`

**Interfaces:**
- Produces: exactly one main worktree and one long-lived `main` branch, with no retained CMC backup/archive.
- Consumes: user-approved literal ledger from Task 5.

- [ ] Revalidate each approved path/ref immediately before deletion; stop on any changed HEAD/status.
- [ ] Remove clean linked worktrees with `git worktree remove --force` only when their integration/backup disposition is satisfied; never delete their directories through another shell.
- [ ] Delete approved local branches with `git branch -D` and approved remote branches with explicit `git push origin --delete` names from the ledger.
- [ ] Delete approved `refs/cmc-rescue/` refs and verified temporary bundles/patch archives; record that Q11-C has been fulfilled.
- [ ] Remove only approved retired Claude session records through the product's official session removal path when available; do not broadly delete Claude application data.
- [ ] Run `git worktree prune --dry-run`, `git worktree list --porcelain`, `git branch -a`, `git status --short` and remote default-HEAD verification. Do not run object pruning.
- [ ] Require exactly one worktree at `D:\LTTSTUDIOSAPP`, branch `main`, clean status; update final report/journal/plan and commit after secret scan.

### Task 7: Post-CMC final verification

**Files:**
- Modify: `docs/LTT_CMC/FINAL_REPORT.md`

**Interfaces:**
- Produces: closed H45 campaign without production deployment.
- Consumes: cleaned topology from Task 6.

- [ ] Run focused topology/rule tests.
- [ ] Run both load checks and one final L3 only if Cleanup changed tracked executable/configuration files; otherwise cite the unchanged certified SHA and run L1 for documentation-only closure.
- [ ] Verify remote `main`, local `main` and final report SHA agree.
- [ ] State explicitly that production deployment was not performed and requires its own gate.
- [ ] Mark H45 complete and commit/push the closure record.
