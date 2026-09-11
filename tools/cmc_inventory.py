"""Chup topology Git cho LTT-CMC ma khong doc gia tri bi mat.

Bao cao chi dung quan he Git (ref, HEAD, worktree, status). URL remote, bien moi
truong, command line tien trinh va noi dung tep khong nam trong snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def run_git(repo: Path, *args: str) -> str:
    """Chay mot phep doc Git; loi phai noi ra thay vi sinh bao cao rong."""
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.rstrip("\r\n")


def parse_worktrees(porcelain: str) -> list[dict[str, str]]:
    """Parse ``git worktree list --porcelain`` theo tung khoi trong."""
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
    """Thu mot snapshot quan he tu repo va moi linked worktree cua no."""
    repo = repo.resolve()
    raw_worktrees = parse_worktrees(
        run_git(repo, "worktree", "list", "--porcelain"))
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
        parts = line.split("\t")
        name, head = parts[:2]
        upstream = parts[2] if len(parts) > 2 else ""
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
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    snapshot["snapshot_id"] = hashlib.sha256(canonical).hexdigest()
    return snapshot


def render_markdown(snapshot: dict[str, object]) -> str:
    """Doi snapshot thanh bao cao nguoi doc co cung snapshot_id."""
    lines = [
        "# LTT-CMC inventory", "",
        f"Snapshot: `{snapshot['snapshot_id']}`", "",
        f"Branch/HEAD: `{snapshot['branch']}` / `{snapshot['head']}`", "",
        "## Worktrees", "",
        "| Path | Branch ref | HEAD | Dirty |", "|---|---|---|---|",
    ]
    worktrees = snapshot["worktrees"]
    assert isinstance(worktrees, list)
    for worktree in worktrees:
        assert isinstance(worktree, dict)
        lines.append(
            f"| `{worktree['path']}` | `{worktree['branch_ref']}` | "
            f"`{worktree['head']}` | `{worktree['dirty']}` |")
    lines.extend([
        "", "## Branches", "", "| Name | HEAD | Upstream |",
        "|---|---|---|",
    ])
    branches = snapshot["branches"]
    assert isinstance(branches, list)
    for branch in branches:
        assert isinstance(branch, dict)
        lines.append(
            f"| `{branch['name']}` | `{branch['head']}` | "
            f"`{branch['upstream']}` |")
    reflog_only = snapshot["reflog_only"]
    assert isinstance(reflog_only, list)
    lines.extend([
        "", f"Reflog-only commits: `{len(reflog_only)}`", "",
        f"Stashes: `{snapshot['stash_count']}`; "
        f"tags: `{snapshot['tag_count']}`", "",
    ])
    return "\n".join(lines)


def write_reports(snapshot: dict[str, object], json_path: Path,
                  markdown_path: Path) -> None:
    """Ghi UTF-8 khong BOM qua sibling temp, sau khi collect da thanh cong."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    markdown_tmp = markdown_path.with_suffix(markdown_path.suffix + ".tmp")
    json_tmp.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    markdown_tmp.write_text(render_markdown(snapshot), encoding="utf-8")
    json_tmp.replace(json_path)
    markdown_tmp.replace(markdown_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chup Git topology cho chien dich LTT-CMC.")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    snapshot = collect(args.repo)
    write_reports(snapshot, args.json, args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
