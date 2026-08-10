"""H31.3b — evaluator asset provision phải offline và fail closed."""
from __future__ import annotations

import hashlib
import json


def _write_manifest(root, *, corrupt: bool = False):
    directory = root / "lpips"
    directory.mkdir(parents=True)
    artifacts = []
    for role, filename, payload in (
        ("linear_alex_v0.1", "alex-linear.pth", b"linear-weight"),
        ("backbone_alexnet", "alexnet.pth", b"backbone-weight"),
    ):
        (directory / filename).write_bytes(payload)
        artifacts.append({"role": role, "filename": filename, "bytes": len(payload),
                          "sha256": hashlib.sha256(payload).hexdigest(),
                          "source_url": f"https://example.invalid/{filename}",
                          "license": "BSD"})
    if corrupt:
        artifacts[0]["sha256"] = "0" * 64
    (directory / "manifest.json").write_text(json.dumps({
        "schema_version": 1, "evaluator": "lpips", "package_version": "0.1.4",
        "source": "https://github.com/richzhang/PerceptualSimilarity",
        "license": "BSD-2-Clause",
        "artifacts": artifacts,
    }), encoding="utf-8")


def test_lpips_asset_manifest_verifies_all_required_roles(tmp_path):
    from apps.qualitylab.evaluator_assets import verify_manifest

    _write_manifest(tmp_path)
    result = verify_manifest("lpips", tmp_path)
    assert result["ready"] is True
    assert result["reason"] == "verified"
    assert {item["role"] for item in result["artifacts"]} == {
        "linear_alex_v0.1", "backbone_alexnet"}


def test_asset_manifest_fails_closed_on_hash_mismatch(tmp_path):
    from apps.qualitylab.evaluator_assets import verify_manifest

    _write_manifest(tmp_path, corrupt=True)
    result = verify_manifest("lpips", tmp_path)
    assert result == {"ready": False, "reason": "ValueError", "artifacts": []}


def test_asset_manifest_rejects_traversal_and_never_downloads(tmp_path, monkeypatch):
    from apps.qualitylab.evaluator_assets import verify_manifest

    _write_manifest(tmp_path)
    manifest = tmp_path / "lpips" / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["artifacts"][0]["filename"] = "../outside.pth"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("network must not be used")))
    result = verify_manifest("lpips", tmp_path)
    assert result["ready"] is False


def test_unapproved_evaluator_cannot_be_provisioned(tmp_path):
    from apps.qualitylab.evaluator_assets import verify_manifest

    assert verify_manifest("pyiqa", tmp_path)["reason"] == "evaluator_not_provisionable"
