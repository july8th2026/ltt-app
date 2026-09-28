"""tests/test_5543_breakdown_scene_count_matches_default.py.

⛔ KHÔNG chỉ khẳng định `len(scenes) == N` — đó là đo SỐ LƯỢNG, và nó xanh cả
khi chỉ số vỡ cấu trúc (vd `[0,1,1,3]` — bốn phần tử, một lỗ, một trùng). Mỗi
test dưới đây khẳng định BẤT BIẾN CẤU TRÚC: tập chỉ số trả về đúng bằng
`{0..N-1}`, mỗi số đúng một lần — ba test tiêm lỗi theo BA CHIỀU riêng (thiếu,
thừa, trùng tiêu đề) theo đúng yêu cầu của điều phối 27/09.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _framework(**over):
    base = dict(composite_header="TIEU DE", composite_rules="LUAT",
               composite_negative_footer="KHONG", default_n_scenes=5,
               breakdown_llm_prompt="Chia cau chuyen sau thanh {N} canh: {STORY}")
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'breakdown.db').as_posix()}")
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


def _indices(scenes):
    return sorted(s["index"] for s in scenes)


def test_scene_indices_are_exactly_0_to_n_minus_1_when_llm_gives_too_few(db_session):
    """Model trả THIẾU 2 cảnh so với default_n_scenes=5."""
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=5)
    fake_raw = {"scenes": [{"title": "Canh 1", "prompt": "p1"},
                           {"title": "Canh 2", "prompt": "p2"},
                           {"title": "Canh 3", "prompt": "p3"}]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="mot cau chuyen dai")
    assert _indices(scenes) == list(range(5))
    # Hai cảnh AI không sinh phải được ĐÁNH DẤU, không lẫn với 3 cảnh thật.
    assert sum(1 for s in scenes if s["auto_filled"]) == 2
    assert sum(1 for s in scenes if not s["auto_filled"]) == 3


def test_scene_indices_are_exactly_0_to_n_minus_1_when_llm_gives_too_many(db_session):
    """Model trả THỪA so với default_n_scenes=3."""
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=3)
    fake_raw = {"scenes": [{"title": f"Canh {i}", "prompt": f"p{i}"}
                          for i in range(1, 8)]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="mot cau chuyen dai")
    assert _indices(scenes) == list(range(3))


def test_explicit_n_scenes_overrides_the_framework_default(db_session):
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=5)
    fake_raw = {"scenes": [{"title": f"Canh {i}", "prompt": f"p{i}"}
                          for i in range(1, 3)]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="mot cau chuyen dai", n_scenes=8)
    assert _indices(scenes) == list(range(8))


def test_duplicate_titles_from_llm_do_not_collapse_scene_indices(db_session):
    """CHIỀU THỨ BA: nếu implementation lỡ dùng dict-theo-tiêu-đề để dedupe
    (một bug hợp lý ai đó có thể viết), bốn cảnh TRÙNG tiêu đề sẽ bị gộp làm
    một — chỉ số sẽ có LỖ. Tách riêng khỏi hai test trên để mỗi chiều lỗi có
    một phép kiểm RIÊNG (thiếu / thừa / trùng), đúng yêu cầu "ba chiều, ba
    phép — một phép không đủ".
    """
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=4)
    fake_raw = {"scenes": [{"title": "Canh mo dau", "prompt": "p1"},
                          {"title": "Canh mo dau", "prompt": "p2"},
                          {"title": "Canh mo dau", "prompt": "p3"},
                          {"title": "Canh mo dau", "prompt": "p4"}]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="mot cau chuyen dai")
    assert _indices(scenes) == list(range(4))
    assert [s["prompt"] for s in scenes] == ["p1", "p2", "p3", "p4"]
