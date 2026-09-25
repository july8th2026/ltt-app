"""Pha 0.2 — cache phân tích chia sẻ cross-job (override cache_dir).

`ProjectPaths(project_dir, cache_dir=...)` cho phép trỏ cache/ (engine outputs
tái-sinh được) ra ngoài cây project — nền taoclipngan đặt nó theo
source_hash để job kế cùng video ăn cache hit. Mọi thứ khác (candidates/,
plans/, logs/) vẫn trong project_dir.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cutclipshort.storage.paths import ProjectPaths


def test_muc_dinh_cache_van_trong_project():
    p = ProjectPaths(Path("C:/x/proj"))
    assert p.cache_dir == Path("C:/x/proj/cache")
    assert p.analysis_manifest == Path("C:/x/proj/cache/analysis_manifest.json")


def test_override_cache_dir_di_moc_khac():
    proj = Path("C:/temp/job_1/project")
    shared = Path("C:/data/tcn_cache/abc123")
    p = ProjectPaths(proj, cache_dir=shared)
    assert p.cache_dir == shared
    assert p.analysis_manifest == shared / "analysis_manifest.json"
    assert p.scenes_json == shared / "scene.json"
    # phần còn lại KHÔNG bị kéo sang shared
    assert p.root == proj
    assert p.candidates_dir == proj / "candidates"
    assert p.plans_dir == proj / "plans"
    assert p.logs_dir == proj / "logs"
    assert p.source_dir == proj / "source"
