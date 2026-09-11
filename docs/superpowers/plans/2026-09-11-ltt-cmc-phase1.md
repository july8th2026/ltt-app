# LTT-CMC Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and certify a `main` canonical candidate from the verified `admin-mvp-v3` lineage without modifying any Voice or LLM protected worktree.

**Architecture:** Work only in `D:\LTTSTUDIOSAPP`, build an evidence-backed inventory, normalize live governance and unowned duplicates, then pin an immutable CMC baseline. Unknown unique capabilities fail closed into a scoped follow-up plan instead of being bulk-merged.

**Tech Stack:** Git, Python 3.13, pytest, Alembic, PowerShell, repository gate tooling.

**Spec:** `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`

## Global Constraints

- Never modify, switch, reset, clean, commit, merge or rebase the three `SESSION_PROTECTED` worktrees listed in the spec.
- Never write to `D:\BOT GEMINI` and never deploy production.
- Do not create a new worktree for LTT-CMC.
- Before every gate, `test_nhanh.py`, or run of at least three test files, run `python tools\tai_may.py` and `python tools\cua_so_yen.py trang-thai`.
- `QUÁ TẢI` means do not run; `BẬN` means postpone or narrow the test.
- Use `python tools\gate.py --doi` for L1 and one `python tools\gate.py` for final L3 evidence.
- Run `python tools\scan_source_secrets.py` before every commit.
- Do not run `git gc`, `git prune`, force push, destructive reset or worktree removal in Phase 1.
- Infrastructure pre-answers for changes under `tools/`: partial rollout is safe because the inventory/default-branch logic does not coordinate other trees; failure to read Git exits nonzero and writes no PASS report; worktree ownership is derived from Git relations/porcelain, not names or cwd labels.

---

### Task 1: Establish `main` and record the campaign

**Files:**
- Modify: `docs/QUYET_DINH_NEN_TANG.md`
- Modify: `docs/KE_HOACH_TRIEN_KHAI.md`
- Create: `docs/LTT_CMC/STATE.md`
- Test: `tests/test_972_ltt_cmc_topology.py`

**Interfaces:**
- Consumes: approved design at `docs/superpowers/specs/2026-09-11-ltt-cmc-design.md`.
- Produces: local canonical branch `main`, decision Q123, plan item H45, and a tracked state document with the pinned source SHA.

- [ ] **Step 1: Prove the main worktree has not moved or acquired foreign changes**

Run these read-only commands separately:

```powershell
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git show-ref --verify --quiet refs/heads/main
git ls-remote --heads origin main
```

Expected: root is `D:/LTTSTUDIOSAPP`; branch is `admin-mvp-v3`; HEAD is
`34b4626e24e5dda419adf5b407e46f5fb744c454`; only `docs/superpowers/` is
untracked; neither local nor remote `main` exists. Any mismatch stops Task 1
for a new frozen snapshot—do not overwrite an existing `main`.

- [ ] **Step 2: Create the canonical branch without creating a worktree**

```powershell
git switch -c main 34b4626e24e5dda419adf5b407e46f5fb744c454
git branch --show-current
git rev-parse HEAD
```

Expected: branch `main`, HEAD still exactly `34b4626e24e5dda419adf5b407e46f5fb744c454`.

- [ ] **Step 3: Write the failing topology contract test**

Add `tests/test_972_ltt_cmc_topology.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ltt_cmc_co_quyet_dinh_va_hang_muc_dang_mo():
    decisions = (ROOT / "docs/QUYET_DINH_NEN_TANG.md").read_text(encoding="utf-8")
    plan = (ROOT / "docs/KE_HOACH_TRIEN_KHAI.md").read_text(encoding="utf-8")
    assert "### Q123 — LTT-CMC" in decisions
    assert "`main` là nhánh chuẩn" in decisions
    assert "## H45 — LTT-CMC" in plan
    assert "H45.0" in plan and "[ ]" in plan


def test_ltt_cmc_state_ghi_sha_nguon_day_du():
    state = (ROOT / "docs/LTT_CMC/STATE.md").read_text(encoding="utf-8")
    assert "34b4626e24e5dda419adf5b407e46f5fb744c454" in state
    assert "SESSION_PROTECTED" in state
    assert "CANONICAL_CANDIDATE" in state
```

- [ ] **Step 4: Run the test and confirm the contract is absent**

Run: `python -m pytest tests/test_972_ltt_cmc_topology.py -q`

Expected: FAIL because Q123, H45 and `docs/LTT_CMC/STATE.md` do not exist yet.

- [ ] **Step 5: Add the decision, plan item and initial state**

Append Q123 after Q122 without rewriting Q122. State explicitly that `main` is
the new sole long-lived canonical branch, derives from the verified lineage,
production deploy is separate, and `master`/`admin-mvp-v3` are retired only
after certification and default-branch migration.

Add H45 with unchecked subitems H45.0–H45.6: freeze/inventory, governance,
completed-history reconciliation, normalization, candidate certification,
sync barrier, and final cleanup.

Create `docs/LTT_CMC/STATE.md` with:

```markdown
# LTT-CMC state

| Field | Value |
|---|---|
| Source lineage | `admin-mvp-v3` |
| Source SHA | `34b4626e24e5dda419adf5b407e46f5fb744c454` |
| Canonical candidate | `main` |
| Canonical worktree | `D:\LTTSTUDIOSAPP` |
| Phase | `PHASE_1_IN_PROGRESS` |

`SESSION_PROTECTED`: Voice reconciliation, LLM dual-model recovery, and LLM
multijob predecessor. LTT-CMC must not mutate those worktrees before the sync
barrier.
```

- [ ] **Step 6: Verify and commit the design/bootstrap checkpoint**

Run: `python -m pytest tests/test_972_ltt_cmc_topology.py -q`

Expected: PASS.

Run: `python tools\scan_source_secrets.py`

Expected: zero findings.

```powershell
git add docs/superpowers docs/QUYET_DINH_NEN_TANG.md docs/KE_HOACH_TRIEN_KHAI.md docs/LTT_CMC/STATE.md tests/test_972_ltt_cmc_topology.py
git commit -m "docs: lock the LTT-CMC canonical topology"
```

### Task 2: Build a reproducible CMC inventory

**Files:**
- Create: `tools/cmc_inventory.py`
- Create: `tests/test_973_cmc_inventory.py`
- Create: `docs/LTT_CMC/inventory.json`
- Create: `docs/LTT_CMC/INVENTORY.md`

**Interfaces:**
- Produces: `collect(repo: Path) -> dict[str, object]`, `render_markdown(snapshot: dict[str, object]) -> str`, and CLI reports with identical `snapshot_id`.
- Consumes: Git CLI only; no Claude registry, production data or remote URL values.

- [ ] **Step 1: Write behavioral tests against a disposable Git repository**

The test must create a temporary repo with two commits, one branch and one
dirty file, then assert ground truth independently:

```python
from pathlib import Path
import json
import subprocess

from tools import cmc_inventory


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def test_collect_reads_relationships_and_dirty_state(tmp_path: Path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "cmc@example.invalid")
    git(tmp_path, "config", "user.name", "CMC Test")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    git(tmp_path, "add", "a.txt")
    git(tmp_path, "commit", "-m", "one")
    expected_head = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")

    snapshot = cmc_inventory.collect(tmp_path)

    assert snapshot["head"] == expected_head
    assert snapshot["branch"] == "main"
    assert snapshot["worktrees"][0]["dirty"] is True
    assert "remote_urls" not in snapshot


def test_cli_writes_matching_machine_and_human_reports(tmp_path: Path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "cmc@example.invalid")
    git(tmp_path, "config", "user.name", "CMC Test")
    (tmp_path / "a").write_text("x", encoding="utf-8")
    git(tmp_path, "add", "a")
    git(tmp_path, "commit", "-m", "x")
    json_path = tmp_path / "inventory.json"
    md_path = tmp_path / "inventory.md"

    assert cmc_inventory.main([
        "--repo", str(tmp_path), "--json", str(json_path),
        "--markdown", str(md_path)]) == 0
    machine = json.loads(json_path.read_text(encoding="utf-8"))
    assert machine["snapshot_id"] in md_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/test_973_cmc_inventory.py -q`

Expected: collection error because `tools.cmc_inventory` does not exist.

- [ ] **Step 3: Implement the minimal inventory utility**

Implement this complete module structure (the executor may add comments, but
must preserve these interfaces and fail-closed behavior):

```python
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip()


def parse_worktrees(porcelain: str) -> list[dict[str, str]]:
    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*porcelain.splitlines(), ""]:
        if not line:
            if current:
                worktrees.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value if value else "true"
    return worktrees


def _ref_exists(repo: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", ref], cwd=repo)
    return result.returncode == 0


def collect(repo: Path) -> dict[str, object]:
    repo = repo.resolve()
    raw_worktrees = parse_worktrees(run_git(repo, "worktree", "list", "--porcelain"))
    worktrees: list[dict[str, object]] = []
    for item in raw_worktrees:
        path = Path(item["worktree"])
        status = run_git(path, "status", "--porcelain=v1")
        worktrees.append({
            "path": path.as_posix(),
            "head": item["HEAD"],
            "branch_ref": item.get("branch", ""),
            "detached": item.get("detached") == "true",
            "dirty": bool(status),
            "status": status.splitlines(),
        })

    branches: list[dict[str, str]] = []
    branch_lines = run_git(
        repo, "for-each-ref",
        "--format=%(refname:short)%09%(objectname)%09%(upstream:short)",
        "refs/heads")
    for line in branch_lines.splitlines():
        name, head, upstream = (line.split("\t") + ["", ""])[:3]
        branches.append({"name": name, "head": head, "upstream": upstream})

    reflog_only = run_git(repo, "rev-list", "--reflog", "--not", "--all")
    snapshot: dict[str, object] = {
        "schema": 1,
        "root": repo.as_posix(),
        "head": run_git(repo, "rev-parse", "HEAD"),
        "branch": run_git(repo, "branch", "--show-current"),
        "branches": branches,
        "worktrees": worktrees,
        "reflog_only": sorted(set(reflog_only.splitlines())),
        "stash_count": int(run_git(repo, "rev-list", "--count", "refs/stash"))
        if _ref_exists(repo, "refs/stash") else 0,
        "tag_count": len(run_git(repo, "tag", "--list").splitlines()),
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    snapshot["snapshot_id"] = hashlib.sha256(canonical).hexdigest()
    return snapshot


def render_markdown(snapshot: dict[str, object]) -> str:
    lines = [
        "# LTT-CMC inventory", "",
        f"Snapshot: `{snapshot['snapshot_id']}`", "",
        f"Branch/HEAD: `{snapshot['branch']}` / `{snapshot['head']}`", "",
        "## Worktrees", "",
        "| Path | Branch ref | HEAD | Dirty |", "|---|---|---|---|",
    ]
    for worktree in snapshot["worktrees"]:
        lines.append(
            f"| `{worktree['path']}` | `{worktree['branch_ref']}` | "
            f"`{worktree['head']}` | `{worktree['dirty']}` |")
    lines.extend(["", "## Branches", "", "| Name | HEAD | Upstream |",
                  "|---|---|---|"])
    for branch in snapshot["branches"]:
        lines.append(
            f"| `{branch['name']}` | `{branch['head']}` | `{branch['upstream']}` |")
    lines.extend(["", f"Reflog-only commits: `{len(snapshot['reflog_only'])}`",
                  "", f"Stashes: `{snapshot['stash_count']}`; tags: `{snapshot['tag_count']}`", ""])
    return "\n".join(lines)


def write_reports(snapshot: dict[str, object], json_path: Path,
                  markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    md_tmp = markdown_path.with_suffix(markdown_path.suffix + ".tmp")
    json_tmp.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_tmp.write_text(render_markdown(snapshot), encoding="utf-8")
    json_tmp.replace(json_path)
    md_tmp.replace(markdown_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    snapshot = collect(args.repo)
    write_reports(snapshot, args.json, args.markdown)
    return 0
```

`collect()` records full HEAD, current branch, status entries, local branch
heads/upstreams, worktrees from `git worktree list --porcelain`, stash count,
tag count and reflog-only commit IDs. It must not record remote URLs, process
command lines, environment values or file contents. Compute `snapshot_id` as
SHA-256 of canonical JSON before adding the field. `write_reports()` writes
UTF-8 without BOM through sibling temporary files and `Path.replace()`; a Git
failure raises and leaves previous reports unchanged.

- [ ] **Step 4: Run behavioral tests**

Run: `python -m pytest tests/test_973_cmc_inventory.py -q`

Expected: PASS.

- [ ] **Step 5: Prove writers are quiescent before taking the real snapshot**

Run `git status --short` and `git worktree list --porcelain` twice, separated by
ordinary review work rather than a blocking sleep. Compare branch/HEAD/status
for the three protected paths. If any moves, do not snapshot or touch it; keep
Phase 1 limited to canonical governance until stable.

- [ ] **Step 6: Generate real reports**

```powershell
python tools\cmc_inventory.py --repo D:\LTTSTUDIOSAPP --json docs\LTT_CMC\inventory.json --markdown docs\LTT_CMC\INVENTORY.md
```

Expected: both reports carry the same `snapshot_id`; protected paths are listed
but unmodified.

- [ ] **Step 7: Verify and commit**

Run: `python tools\scan_source_secrets.py`

```powershell
git add tools/cmc_inventory.py tests/test_973_cmc_inventory.py docs/LTT_CMC/inventory.json docs/LTT_CMC/INVENTORY.md
git commit -m "feat: capture reproducible CMC topology evidence"
```

### Task 3: Make live branch and operating rules single-source

**Files:**
- Modify: `tools/cay_rieng.py`
- Modify: `tools/do_phu_diff.py`
- Modify: `.github/workflows/gate-quick.yml`
- Modify: `docs/QUY_TRINH_WORKTREE.md`
- Modify: `docs/16_CAP_NHAT_VA_DEPLOY.md`
- Modify: `CLAUDE.md`
- Modify: `tools/gate.py` (documentation/comments only)
- Create: `tests/test_974_cmc_rule_authority.py`

**Interfaces:**
- Produces: `tools.cay_rieng.NHANH_TRUNK == "main"` and `tools.do_phu_diff.NHANH_GOC_MAC_DINH == ("origin/main", "main")`.
- Consumes: `docs/00_LTT_OPERATING_CONTRACT.md` as the only test-cadence authority.

- [ ] **Step 1: Write failing authority tests**

```python
from pathlib import Path
from tools import cay_rieng, do_phu_diff

ROOT = Path(__file__).resolve().parents[1]


def test_cong_cu_dung_main_lam_trunk():
    assert cay_rieng.NHANH_TRUNK == "main"
    assert do_phu_diff.NHANH_GOC_MAC_DINH == ("origin/main", "main")


def test_ci_bao_ve_main_trong_giai_doan_chuyen_tiep():
    workflow = (ROOT / ".github/workflows/gate-quick.yml").read_text(encoding="utf-8")
    assert "branches: [main, admin-mvp-v3, master]" in workflow


def test_tai_lieu_song_tro_ve_hop_dong_van_hanh():
    deploy = (ROOT / "docs/16_CAP_NHAT_VA_DEPLOY.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "docs/00_LTT_OPERATING_CONTRACT.md" in deploy
    assert "sau mỗi lần sửa" not in deploy
    assert "docs/NHAT_KY.md" in claude
    assert "_luutru/PROJECT_MEMORY.md` | nhật ký" not in claude
```

- [ ] **Step 2: Run tests and confirm old authorities fail**

Run: `python -m pytest tests/test_974_cmc_rule_authority.py -q`

Expected: FAIL on missing constants, old CI targets and duplicate cadence/memory rules.

- [ ] **Step 3: Implement branch authority**

Add `NHANH_TRUNK = "main"` to `tools/cay_rieng.py` and use it wherever new
worktrees are based or reconciled. Add
`NHANH_GOC_MAC_DINH = ("origin/main", "main")` to `tools/do_phu_diff.py`; make
`_nhanh_goc_mac_dinh()` iterate that tuple and update help text/examples.

Keep CI targets `[main, admin-mvp-v3, master]` only during transition so old PR
targets do not lose protection before Cleanup.

- [ ] **Step 4: Remove rule duplication without rewriting historical reports**

Update only live operational authorities:

- `docs/QUY_TRINH_WORKTREE.md`: `main` is canonical base/integration target.
- `docs/16_CAP_NHAT_VA_DEPLOY.md`: source certification uses `--doi`/L3 exactly
  as Operating Contract says; link instead of copying cadence.
- `CLAUDE.md`: current session log is `docs/NHAT_KY.md`; archived memory remains
  history, not the active journal.
- `tools/gate.py`: examples/comments no longer claim `--vong-lap` runs after
  every edit; it remains explicitly diagnostic.

Do not rewrite branch names inside dated reports or archive documents.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/test_974_cmc_rule_authority.py tests/test_72_vanhanh.py tests/test_362_cay_rieng_va_deploy.py -q`

This is three test files, so first run both load commands from Global Constraints.
Expected: PASS.

- [ ] **Step 6: Run L1 and commit**

Run the two load commands, then `python tools\gate.py --doi`.

Expected: L1 PASS.

Run secret scan, then:

```powershell
git add tools/cay_rieng.py tools/do_phu_diff.py tools/gate.py .github/workflows/gate-quick.yml docs/QUY_TRINH_WORKTREE.md docs/16_CAP_NHAT_VA_DEPLOY.md CLAUDE.md tests/test_974_cmc_rule_authority.py
git commit -m "fix: make main and the operating contract authoritative"
```

### Task 4: Remove stale source copies and classify intentional duplicates

**Files:**
- Delete: `.merge_tam/goc.py`
- Delete: `.merge_tam/ho.py`
- Create: `docs/LTT_CMC/DUPLICATES.md`
- Create: `docs/LTT_CMC/duplicates.json`
- Create: `tests/test_975_cmc_duplicate_hygiene.py`

**Interfaces:**
- Produces: no tracked Python source under `.merge_tam`; explicit dispositions for known exact duplicates.
- Consumes: exact blob/hash evidence from inventory.

- [ ] **Step 1: Write the failing hygiene test**

```python
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_khong_track_source_trong_merge_tam():
    result = subprocess.run(
        ["git", "ls-files", ".merge_tam/*.py"], cwd=ROOT,
        check=True, capture_output=True, text=True)
    assert result.stdout.strip() == ""


def test_bon_nhom_exact_duplicate_co_disposition():
    report = (ROOT / "docs/LTT_CMC/DUPLICATES.md").read_text(encoding="utf-8")
    for identity in ("tsconfig.app.json", "ltt.css", "G9_prompts.json",
                     "BANG_KE_COMFYUI_V3.json"):
        assert identity in report
    assert report.count("INTENTIONAL_DUPLICATE") >= 4
```

- [ ] **Step 2: Run test and verify stale source is detected**

Run: `python -m pytest tests/test_975_cmc_duplicate_hygiene.py -q`

Expected: FAIL because two `.merge_tam` Python files are tracked and dispositions are absent.

- [ ] **Step 3: Remove only the proven stale merge variants**

Delete `.merge_tam/goc.py` and `.merge_tam/ho.py`. Do not delete unrelated
ignored `tmp/`, caches, bench evidence or archive documents.

Record these dispositions in `DUPLICATES.md` and `duplicates.json`, both tied
to the inventory `snapshot_id`:

- four frontend `tsconfig.app.json`: intentional per-app templates;
- `server/static/ltt.css` and `tools/gui/ltt.css`: intentional mirror, atomic lifecycle;
- `bench/G9_ben_100.json` and `bench/G9_prompts.json`: intentional reproducibility alias—the current consumer uses `G9_prompts.json`, while dated evidence names `G9_ben_100`;
- archived/current ComfyUI inventories: intentional recovery/history copy, non-runtime.

Use the actual filename `bench/G9_prompts.json` in the report; the pair is
`bench/G9_ben_100.json` + `bench/G9_prompts.json`.

- [ ] **Step 4: Run tests, L1 and commit**

Run: `python -m pytest tests/test_975_cmc_duplicate_hygiene.py -q`

Run both load checks, then `python tools\gate.py --doi`.

Run secret scan, then:

```powershell
git add -A .merge_tam docs/LTT_CMC/DUPLICATES.md docs/LTT_CMC/duplicates.json tests/test_975_cmc_duplicate_hygiene.py
git commit -m "chore: remove stale merge-source copies"
```

### Task 5: Reconcile completed histories outside Voice and LLM

**Files:**
- Create: `docs/LTT_CMC/RECONCILIATION.md`
- Create: `docs/LTT_CMC/reconciliation.json`
- Modify: `docs/LTT_CMC/STATE.md`

**Interfaces:**
- Produces: one disposition for every local branch and every reflog-only commit captured by Task 2.
- Consumes: `snapshot_id` from `docs/LTT_CMC/inventory.json` and the taxonomy in the design spec.

- [ ] **Step 1: Partition branch ownership fail-closed**

Mark every branch whose name or changed paths concern `ltt_voice`, voice,
`ltt_llm`, model admission, or either protected workstream as `DEFER_VOICE` or
`DEFER_LLM`. This includes the old Voice/LLM branches even when their worktree
is not currently active. Do not cherry-pick from them in Phase 1.

Mark branches already ancestral to source SHA as `ALREADY_CANONICAL`. Analyze
remaining non-Voice/LLM branches one at a time with:

Use this PowerShell loop so every actual branch name comes from the frozen
machine-readable inventory rather than hand-built shell text:

```powershell
$snapshot = Get-Content -Raw docs\LTT_CMC\inventory.json | ConvertFrom-Json
foreach ($branch in $snapshot.branches.name) {
    git merge-base main $branch
    git rev-list --left-right --count "main...$branch"
    git cherry -v main $branch
    git diff --stat "main...$branch"
    git diff --name-status "main...$branch"
}
```

- [ ] **Step 2: Classify known non-protected families**

The report must cover scheduler, ASV, aiclean, wf2, mobile, VPS, H42 release,
Video AI V3, Video V2 WangP, projects-longform and detached worktree commits.
For every `+` from `git cherry`, inspect the patch and current implementation;
commit count or a newer timestamp is not evidence of value.

If a branch contains a valid capability absent from `main`, stop before porting
it and write a capability-specific plan naming its exact files/tests. If none
does, record `ALREADY_CANONICAL`, `PATCH_EQUIVALENT`, `SUPERSEDED` or
`ARCHIVE_HISTORY_ONLY` with command evidence. This gate prevents an unknown
capability from being hidden inside the CMC orchestration plan.

- [ ] **Step 3: Preserve selected reflog-only commits temporarily**

For each reflog-only commit classified `RECONCILE`, create a namespaced ref by
appending its full 40-character SHA to `refs/cmc-rescue/`; do not create refs for superseded or equivalent
commits. Re-run inventory and assert each selected object is reachable from the
new ref. These refs are temporary and listed for deletion in final Cleanup.

- [ ] **Step 4: Verify matrix completeness**

Use a small JSON consistency check in `tests/test_973_cmc_inventory.py` that
loads inventory + reconciliation and asserts every captured local branch and
reflog-only commit has exactly one disposition, and every protected branch has
a `DEFER_*` disposition.

Append this test:

```python
def test_reconciliation_covers_the_frozen_inventory():
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads(
        (root / "docs/LTT_CMC/inventory.json").read_text(encoding="utf-8"))
    reconciliation = json.loads(
        (root / "docs/LTT_CMC/reconciliation.json").read_text(encoding="utf-8"))
    assert reconciliation["snapshot_id"] == inventory["snapshot_id"]
    branch_dispositions = {
        item["name"]: item["disposition"]
        for item in reconciliation["branches"]
    }
    assert set(branch_dispositions) == {
        item["name"] for item in inventory["branches"]
    }
    assert "UNCLASSIFIED" not in set(branch_dispositions.values())
    reflog_dispositions = {
        item["sha"]: item["disposition"]
        for item in reconciliation["reflog_only"]
    }
    assert set(reflog_dispositions) == set(inventory["reflog_only"])
    protected = reconciliation["protected_branches"]
    assert all(branch_dispositions[name].startswith("DEFER_") for name in protected)
```

Run: `python -m pytest tests/test_973_cmc_inventory.py -q`

Expected: PASS with no `UNCLASSIFIED` entry.

- [ ] **Step 5: Commit the reconciliation checkpoint**

Run secret scan, then:

```powershell
git add docs/LTT_CMC tests/test_973_cmc_inventory.py
git commit -m "docs: classify completed histories for CMC"
```

### Task 6: Certify migration, registry and generated baselines

**Files:**
- Create: `docs/LTT_CMC/NORMALIZATION_BASELINE.md`
- Modify: `docs/LTT_CMC/STATE.md`
- Test: `tests/test_103_autosub_projects.py`
- Test: `tests/test_223_nexus_devices.py`
- Test: `tests/test_60_app_registry.py`
- Test: `tests/test_148_frontend_bundle.py`

**Interfaces:**
- Produces: a measured baseline proving one Alembic head, unique registry identities and fresh frontend output before protected-session integration.
- Consumes: current tests as independent truth; no production mutation.

- [ ] **Step 1: Run the independent static checks**

Because four test files are heavy by policy, run both load checks first.

Run:

```powershell
python -m pytest tests/test_103_autosub_projects.py::test_platform_migrations_have_a_single_head tests/test_223_nexus_devices.py::test_khong_co_hai_migration_trung_revision_id tests/test_223_nexus_devices.py::test_do_thi_migration_chi_co_MOT_head tests/test_60_app_registry.py tests/test_148_frontend_bundle.py -q
```

If an exact node name differs, use `python tools\do_nhanh.py chu-ky`/pytest
collection to select the existing assertion; do not weaken or duplicate it.
Expected: PASS.

- [ ] **Step 2: Record measured facts**

Write `NORMALIZATION_BASELINE.md` with exact commands/results, current Alembic
head, manifest/ToolSpec/job/table counts, the four frontend bundle hashes and
the known hypothetical three-head risk when Voice/LLM are introduced.

Do not claim provider/model, retry, ToolSpec V2 or GPU authority normalization
is complete; those are deferred to the LLM handoff plan where ownership lies.

- [ ] **Step 3: Commit the baseline**

Run secret scan, then:

```powershell
git add docs/LTT_CMC/NORMALIZATION_BASELINE.md docs/LTT_CMC/STATE.md
git commit -m "docs: pin CMC normalization baselines"
```

### Task 7: Full certification and immutable sync barrier

**Files:**
- Modify: `docs/LTT_CMC/STATE.md`
- Create: `docs/LTT_CMC/CMC_SYNC_BARRIER.md`
- Create: `docs/LTT_CMC/HANDOFF_VOICE.md`
- Create: `docs/LTT_CMC/HANDOFF_LLM_DUAL.md`
- Modify: `docs/KE_HOACH_TRIEN_KHAI.md`
- Modify: `docs/NHAT_KY.md`

**Interfaces:**
- Produces: immutable `CMC_BASE_SHA`, `CANONICAL_CANDIDATE_READY`, and two fully populated handoff prompts.
- Consumes: all prior Phase 1 evidence and the latest stable protected-worktree snapshot.

- [ ] **Step 1: Recheck generated outputs only when their source changed**

If `git diff 34b4626e -- frontend` is nonempty, run `npm test -- --run` in each
changed directory among `frontend/agent-canvas`, `frontend/autosub-studio`,
`frontend/prompt-ai-ommi` and `frontend/chatltt`, then run
`python tools\build_release.py` as the last file-generating action.
If it is empty, record `NOT_NEEDED: source unchanged`; do not rebuild for churn.

- [ ] **Step 2: Run final machine/lock preflight**

```powershell
python tools\tai_may.py
python tools\cua_so_yen.py trang-thai
```

Proceed only when the machine/locks allow a full gate. Do not use `--khong-khoa`.

- [ ] **Step 3: Run source certification**

Run in this order:

```powershell
python tools\scan_source_secrets.py
python tools\gate.py
```

Expected: zero secret findings and L3 PASS on an unchanged tree. Record exact
result, duration and skipped environmental checks without calling skips passes.

- [ ] **Step 4: Pin the immutable baseline**

Before L3, commit every source/governance change and require a clean tree. After
L3 passes, obtain the certified commit with `git rev-parse HEAD` and create the
temporary immutable tag `cmc-base-20260911` at that exact commit. Never
amend/rebase/reset the tagged commit.

State must read:

```text
CMC_BASE_BRANCH: main
CMC_BASE_WORKTREE: D:\LTTSTUDIOSAPP
STATUS: CMC_SYNC_BARRIER_READY
```

The actual full SHA is written directly into the subsequent barrier/handoff
documentation commit. That documentation-only child commit may move `main`,
but both sessions use the tagged parent SHA; run L1 on the documentation child.

- [ ] **Step 5: Generate two real handoff prompts from the latest snapshot**

`HANDOFF_VOICE.md` contains actual Voice worktree, branch, HEAD, dirty files,
`CMC_BASE_SHA`, shared-file and migration risks. `HANDOFF_LLM_DUAL.md` contains
both actual LLM worktrees/branches/HEADs, dirty/untracked files, duplicate WIP
patch evidence, model/admission/registry/migration risks and D04.

Each prompt explicitly forbids merging `main`, moving the baseline, deploying
or deleting a worktree. Read both prompts back and verify every path, branch,
HEAD and baseline field contains its actual value rather than a template marker.

- [ ] **Step 6: Stop at the barrier**

Mark H45.0–H45.5 with actual evidence in the plan and journal; leave final
integration/cleanup unchecked. Commit the barrier documents after secret scan,
then run both load checks and `python tools\gate.py --doi` for the docs-only
child. Verify `git rev-parse cmc-base-20260911` still equals the handoff SHA.

Do not remove any worktree, delete any branch/ref/archive, change remote default
branch or deploy. Report `CMC_SYNC_BARRIER_READY` to the user and provide the
two handoff prompts.
