"""Chot viec don source tam va disposition cua exact duplicate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]

NHOM_EXACT = {
    "frontend_tsconfig": (
        "frontend/agent-canvas/tsconfig.app.json",
        "frontend/autosub-studio/tsconfig.app.json",
        "frontend/chatltt/tsconfig.app.json",
        "frontend/prompt-ai-ommi/tsconfig.app.json",
    ),
    "shared_ltt_css": (
        "server/static/ltt.css",
        "tools/gui/ltt.css",
    ),
    "g9_prompt_alias": (
        "bench/G9_ben_100.json",
        "bench/G9_prompts.json",
    ),
    "comfyui_inventory_history": (
        "docs/VIDEO_AI_V2/khoi_phuc/BANG_KE_COMFYUI_V3.json",
        "docs/_luutru/VIDEO_AI_V3/BANG_KE_MONG_DOI.json",
    ),
}


def _sha256(relative_path: str) -> str:
    return hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()


def test_khong_track_source_trong_merge_tam():
    result = subprocess.run(
        ["git", "ls-files", ".merge_tam/*.py"], cwd=ROOT,
        check=True, capture_output=True, text=True)
    assert result.stdout.strip() == ""


def test_bon_nhom_exact_duplicate_co_disposition_va_bang_chung_doc_lap():
    inventory = json.loads(
        (ROOT / "docs/LTT_CMC/inventory.json").read_text(encoding="utf-8"))
    duplicate = json.loads(
        (ROOT / "docs/LTT_CMC/duplicates.json").read_text(encoding="utf-8"))
    report = (ROOT / "docs/LTT_CMC/DUPLICATES.md").read_text(encoding="utf-8")

    assert duplicate["snapshot_id"] == inventory["snapshot_id"]
    by_id = {item["id"]: item for item in duplicate["groups"]}
    assert set(by_id) == set(NHOM_EXACT)

    for identity, paths in NHOM_EXACT.items():
        item = by_id[identity]
        hashes = {_sha256(path) for path in paths}
        assert len(hashes) == 1, f"{identity} khong con la exact duplicate"
        assert item["paths"] == list(paths)
        assert item["sha256"] == hashes.pop()
        assert item["disposition"] == "INTENTIONAL_DUPLICATE"
        assert identity in report
        for path in paths:
            assert path in report
