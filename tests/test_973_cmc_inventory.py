"""Behavioral tests for the LTT-CMC repository inventory."""
from pathlib import Path
import json
import subprocess

from tools import cmc_inventory


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip()


def _init_repo(repo: Path) -> str:
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "cmc@example.invalid")
    git(repo, "config", "user.name", "CMC Test")
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-m", "one")
    return git(repo, "rev-parse", "HEAD")


def test_collect_reads_relationships_and_dirty_state(tmp_path: Path):
    expected_head = _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")

    snapshot = cmc_inventory.collect(tmp_path)

    assert snapshot["head"] == expected_head
    assert snapshot["branch"] == "main"
    assert snapshot["worktrees"][0]["dirty"] is True
    assert snapshot["worktrees"][0]["status"] == [" M a.txt"]
    assert "remote_urls" not in snapshot


def test_cli_writes_matching_machine_and_human_reports(tmp_path: Path):
    _init_repo(tmp_path)
    json_path = tmp_path / "inventory.json"
    md_path = tmp_path / "inventory.md"

    assert cmc_inventory.main([
        "--repo", str(tmp_path), "--json", str(json_path),
        "--markdown", str(md_path)]) == 0

    machine = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    assert machine["snapshot_id"] in markdown
    assert machine["head"] in markdown


def test_git_failure_does_not_replace_existing_reports(tmp_path: Path):
    json_path = tmp_path / "inventory.json"
    md_path = tmp_path / "inventory.md"
    json_path.write_text("old-json\n", encoding="utf-8")
    md_path.write_text("old-md\n", encoding="utf-8")

    try:
        cmc_inventory.main([
            "--repo", str(tmp_path), "--json", str(json_path),
            "--markdown", str(md_path)])
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("non-Git directory must fail closed")

    assert json_path.read_text(encoding="utf-8") == "old-json\n"
    assert md_path.read_text(encoding="utf-8") == "old-md\n"


def test_reconciliation_covers_the_frozen_inventory():
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads(
        (root / "docs/LTT_CMC/inventory.json").read_text(encoding="utf-8"))
    reconciliation = json.loads(
        (root / "docs/LTT_CMC/reconciliation.json").read_text(encoding="utf-8"))

    assert reconciliation["snapshot_id"] == inventory["snapshot_id"]

    branch_items = reconciliation["branches"]
    branch_dispositions = {
        item["name"]: item["disposition"] for item in branch_items}
    branch_heads = {item["name"]: item["head"] for item in branch_items}
    assert len(branch_dispositions) == len(branch_items)
    assert set(branch_dispositions) == {
        item["name"] for item in inventory["branches"]}
    assert branch_heads == {
        item["name"]: item["head"] for item in inventory["branches"]}
    assert "UNCLASSIFIED" not in set(branch_dispositions.values())

    reflog_items = reconciliation["reflog_only"]
    reflog_dispositions = {
        item["sha"]: item["disposition"] for item in reflog_items}
    assert len(reflog_dispositions) == len(reflog_items)
    assert set(reflog_dispositions) == set(inventory["reflog_only"])
    assert "UNCLASSIFIED" not in set(reflog_dispositions.values())

    protected = reconciliation["protected_branches"]
    assert all(
        branch_dispositions[name].startswith("DEFER_") for name in protected)
    assert set(protected) == {
        name for name, disposition in branch_dispositions.items()
        if disposition.startswith("DEFER_")}

    selected = {
        sha for sha, disposition in reflog_dispositions.items()
        if disposition == "RECONCILE"}
    assert {item["sha"] for item in reconciliation["rescue_refs"]} == selected
