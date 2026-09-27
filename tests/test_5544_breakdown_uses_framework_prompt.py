"""tests/test_5544_breakdown_uses_framework_prompt.py."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'breakdown2.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def test_system_prompt_is_built_from_composite_header_rules_and_footer(db_session):
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = SimpleNamespace(
        composite_header="TIEU DE X", composite_rules="LUAT Y",
        composite_negative_footer="KHONG Z", default_n_scenes=2,
        breakdown_llm_prompt="Chia {STORY} thanh {N} canh")

    captured = {}

    def _fake_generate_json(system, prompt, *, model):
        captured["system"] = system
        captured["prompt"] = prompt
        return {"scenes": [{"title": "A", "prompt": "pa"},
                           {"title": "B", "prompt": "pb"}]}, 10

    with patch("apps.prompt_ai_ommi.provider.generate_json",
              side_effect=_fake_generate_json), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        bsvc.breakdown(db_session, framework=framework, story_vi="cau chuyen ABC")

    assert "TIEU DE X" in captured["system"]
    assert "LUAT Y" in captured["system"]
    assert "KHONG Z" in captured["system"]
    assert "cau chuyen ABC" in captured["prompt"]
    assert "2" in captured["prompt"]
