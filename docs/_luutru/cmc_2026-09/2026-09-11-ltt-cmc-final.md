# LTT-CMC Final Integration and Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the certified Voice and LLM handoffs into `main`, certify the combined source, switch repository authority, and remove all retired Git/session state after a separate destructive approval.

**Architecture:** Voice functionality is already present exactly once in the
immutable CMC baseline; any later documentation-only Voice commits are reviewed
and ported without replaying implementation history. Accept the clean LLM handoff,
integrate it as one atomic changeset with semantic review, normalize the active
worktree/branch authorities, and certify the frozen source once. Move remote
authority only after certification, then present a literal deletion ledger and
stop. Cleanup and post-clean verification are a separate, explicitly approved
continuation.

**Tech Stack:** Git, GitHub CLI or authenticated repository UI, Python gate tooling, Alembic, pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`

## Global Constraints

- Do not begin until both handoff branches are clean, tested and based on the exact same `CMC_BASE_SHA`.
- Never deploy production in this plan.
- Before all heavy runs, use both load/lock commands and obey `BẬN`/`QUÁ TẢI`.
- Test cadence is defined only by `docs/00_LTT_OPERATING_CONTRACT.md`; this plan
  defines evidence checkpoints, not a competing cadence.
- Do not run L3 after each cherry-pick. Freeze the complete integration
  changeset, run affected verification, then one pre-clean L3. If an earlier
  L1 fails closed to L3 because impact cannot be proved, accept that safeguard
  and do not bypass it.
- `docs/QUY_TRINH_WORKTREE.md` remains the one worktree authority. Do not create
  a competing `docs/van_hanh_worktree.md`; startup documents link to the
  canonical file instead of copying its full rules.
- No branch/worktree/session/ref/archive deletion occurs before a fresh literal ledger and separate user approval.
- Do not use force push, recursive filesystem deletion, `git gc` or `git prune`.

## Pinned entry checkpoint (2026-09-12)

- Canonical worktree: `D:\LTTSTUDIOSAPP`, branch `main`, clean HEAD
  `072d6d970063bf9ee60f3c8b8bcac8911788dd23`.
- Immutable baseline: `cmc-base-20260911` =
  `09b219a371e1261f0f0eef0e316c1ca42754cb78`.
- Voice branch and baseline contain the same certified Voice behavior; three
  later documentation commits were discovered and require a narrow semantic port.
- Pre-handoff main evidence:
  `test-results/gates/20260912T005150Z-17608.json`, PASS 33/33,
  `cay_da_doi_giua_chung=false`.
- Only the LLM workstream remains protected. Do not mutate either LLM source
  worktree until it returns `HANDOFF_READY_FINAL`.

---

### Task 0: Accept and verify the final LLM handoff

**Files:**
- Read: `docs/LTT_CMC/HANDOFF_LLM_DUAL.md`
- Read: `docs/ltt_llm_dual/CMC_SOURCE_STATE.md` from the returned branch

**Interfaces:**
- Produces: an accepted immutable LLM source HEAD.
- Consumes: the literal `HANDOFF_READY_FINAL` returned by the owning session.

- [ ] Require branch `cmc/llm-dual-reconcile`, full final HEAD, source A/B
      final HEADs, exact merge-base, clean status and exact test/gate reports.
- [ ] Verify the branch exists locally and the reported HEAD equals the real
      ref; verify its worktree is clean without refreshing or modifying another
      session's index.
- [ ] Require merge-base
      `09b219a371e1261f0f0eef0e316c1ca42754cb78`; reject a branch based on a
      moving `main` or an older migration lineage.
- [ ] Verify one Alembic head, D04 proof, ModelProfile authority, machine-B
      boundary, kept/skipped commit ledger and every `NOT_RUN`/`BLOCKED` item.
- [ ] Stop on an unexplained dirty file, missing source commit, surviving
      semantic duplicate or claimed PASS without a real report.

### Task 1: Verify the Voice no-op

**Files:**
- Read: `docs/LTT_CMC/HANDOFF_VOICE.md`
- Read: `docs/LTT_VOICE/HOP_NHAT/CMC_SOURCE_STATE.md` when present
- Modify only if evidence drifted: `docs/LTT_CMC/STATE.md`

**Interfaces:**
- Produces: proof that `main` already contains certified Voice capability once.
- Consumes: immutable CMC baseline and Voice handoff evidence.

- [ ] Verify main is clean/current and `cmc-base-20260911` still resolves to the
      recorded full SHA.
- [ ] Verify the Voice branch HEAD is already an ancestor/equivalent of the
      baseline and the recorded Voice tests belong to that source.
- [x] Record disposition `NO_OP_FUNCTIONAL_ALREADY_IN_BASELINE`; port only the
      three post-baseline documentation commits discovered by live rescan. No
      Voice implementation history is replayed.

### Task 2: Integrate the LLM handoff

**Files:**
- Modify through integration: the exact files recorded in `docs/ltt_llm_dual/CMC_SOURCE_STATE.md`
- Modify: `docs/LTT_CMC/STATE.md`

**Interfaces:**
- Produces: combined Voice + dual-model/multijob canonical source.
- Consumes: clean LLM handoff and Task 1 state.

- [ ] Verify the LLM merge-base equals the same recorded CMC baseline.
- [ ] Review patch equivalence against the post-Voice `main`; do not replay any duplicated WIP patch.
- [ ] Treat the reviewed LLM range as one atomic integration changeset.
      Cherry-pick in dependency order and resolve shared
      registry/migration/runtime files semantically against the already
      integrated Voice state; never accept an entire side.
- [ ] Search callers/imports/registries after replacement. Require no old live
      implementation or orphan reference before removing a duplicate.
- [ ] Run the affected LLM, registry and one-head verification required by the
      Operating Contract after both load checks. Do not run a separate L3 after
      each commit.
- [ ] Record actual integrated commits and main HEAD; secret-scan and commit
      reconciliation fixes before candidate freeze.

### Task 3: Certify the combined canonical source

**Files:**
- Modify: `docs/LTT_CMC/STATE.md`
- Modify: `docs/KE_HOACH_TRIEN_KHAI.md`
- Prepare: `docs/LTT_CMC/FINAL_REPORT.md`
- Modify: `.github/workflows/gate-quick.yml`
- Modify: `docs/QUY_TRINH_WORKTREE.md`
- Modify: `docs/16_CAP_NHAT_VA_DEPLOY.md`
- Modify: `CLAUDE.md`
- Modify only when needed to keep the startup hard gate consistent: `AGENTS.md`
- Modify: `tests/test_974_cmc_rule_authority.py`

**Interfaces:**
- Produces: `CANONICAL_CERTIFIED` evidence on a clean, unchanged tree.
- Consumes: combined main from Tasks 1–2.

- [ ] Verify one Alembic head, unique registry identities, model-profile consistency and frontend source hash.
- [ ] Normalize the future lifecycle in the existing worktree authority:
      `main -> task branch -> temporary worktree -> freeze -> handoff ->
      canonical integration -> certification -> retire worktree/branch`.
- [ ] Keep pre-commit checks distinct from end-of-session evidence: focused
      verification and secret scan before a commit; the required gate and a
      clean/full-HEAD handoff before a session claims completion.
- [ ] Make `CLAUDE.md`/`AGENTS.md` point to the worktree and Operating Contract
      authorities without copying a second cadence. Reduce active CI targets to
      `[main]` only when this candidate is ready to become remote authority.
- [ ] If frontend/test source changed, build release as the final file-generating action before candidate freeze.
- [ ] Commit every tracked executable/configuration/rule change. Prepare the
      static final report with status `PENDING_FINAL_L3`, then require a clean
      tree; do not edit the candidate while L3 runs.
- [ ] Run both load checks; wait for an acceptable window.
- [ ] Run `python tools\scan_source_secrets.py` and exactly one `python tools\gate.py`; require zero findings and L3 PASS.
- [ ] Treat the gated commit as `SOURCE_CERTIFIED_SHA`; preserve the exact
      command/result/report path, skipped environment checks and rollback
      boundary for the single closure commit in Task 4. Never call a skip a
      pass and do not change tracked source/configuration after this point.

### Task 4: Move repository authority to `main`

**Files:**
- Modify: `docs/LTT_CMC/FINAL_REPORT.md`
- Modify: `docs/LTT_CMC/STATE.md`
- Modify: `docs/KE_HOACH_TRIEN_KHAI.md`
- Modify: `docs/NHAT_KY.md`

**Interfaces:**
- Produces: remote default/protected branch `main`; no new work targets old branches.
- Consumes: `CANONICAL_CERTIFIED` main SHA.

- [ ] Push `SOURCE_CERTIFIED_SHA` on `main` normally and verify remote SHA
      equals the local certified source SHA.
- [ ] Change the private GitHub repository default branch to `main` using `gh repo edit giaitritruyenthongltt-spec/LTTSTUDIOSAPP --default-branch main`, or the authenticated repository UI if GitHub CLI is unavailable.
- [ ] Move branch-protection/ruleset targets to `main`; verify PR base defaults to `main`.
- [ ] Confirm CI/startup authority files were already certified in Task 3; do
      not create a post-certification executable/configuration diff here.
- [ ] Write L3 and remote-authority evidence to the report/journal/state/plan
      in one documentation-only closure commit. Prove
      `SOURCE_CERTIFIED_SHA..HEAD` changes only those allowed documents;
      secret-scan and run the documentation evidence level required by the
      Operating Contract instead of paying for a second L3 when the
      executable/configuration tree is byte-identical.
- [ ] Push the documentation-only closure and verify a fresh remote query
      reports default branch `main`; separately record `SOURCE_CERTIFIED_SHA`
      and the closure HEAD so they are not falsely described as one commit.

### Task 5: Present and approve the destructive cleanup ledger

**Files:**
- Create: `docs/LTT_CMC/CLEANUP_LEDGER.md`

**Interfaces:**
- Produces: literal approved targets; consumes final inventory and integration evidence.

- [ ] Re-run inventory after repository authority migration.
- [ ] List every linked worktree with absolute resolved path, branch, HEAD, status and integration evidence.
- [ ] List every local/remote branch, CMC rescue ref, temporary bundle/patch/archive and Claude session state with exact target and disposition.
- [ ] Prove every deletion target lies within its intended Git common directory, repository workspace, configured temporary backup directory or identified Claude session directory.
- [ ] Present the completed ledger and request separate explicit destructive approval.
- [ ] **MANDATORY USER-REQUESTED STOP:** stop here even if earlier messages
      granted full permission or approved cleanup in principle. Do not remove a
      worktree/branch/ref/session until the owner has seen this fresh literal
      ledger and explicitly continues.

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
