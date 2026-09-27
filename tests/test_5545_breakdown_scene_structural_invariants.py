"""tests/test_5545_breakdown_scene_structural_invariants.py.

Chiều THỨ HAI của bất biến cấu trúc mà điều phối yêu cầu 27/09 (khác chiều
"chỉ số lỗ/trùng" đã kiểm ở test_5543): "mọi đoạn văn bản nguồn phải thuộc
đúng một cảnh" — một cảnh AI ĐÃ SINH mà bị cắt vì vượt số lượng yêu cầu KHÔNG
được biến mất im lặng. `test_5543` tiêm lỗi ở chiều thiếu/trùng; đây tiêm lỗi
ở chiều "một đoạn nguồn bị bỏ".
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _framework(**over):
    base = dict(composite_header="TD", composite_rules="LU",
               composite_negative_footer="KH", default_n_scenes=2,
               breakdown_llm_prompt="Chia {STORY} thanh {N} canh")
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'breakdown3.db').as_posix()}")
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


def test_overflow_scenes_are_merged_into_last_scene_not_dropped_silently(db_session):
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=2)
    marker = "NOI-DUNG-DOC-NHAT-VO-NHI-CUA-CANH-BI-CAT"
    fake_raw = {"scenes": [
        {"title": "Canh 1", "prompt": "p1"},
        {"title": "Canh 2", "prompt": "p2"},
        {"title": "Canh du ra", "prompt": marker},
    ]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="cau chuyen")
    assert len(scenes) == 2
    # Nội dung cảnh thứ ba (vượt target) KHÔNG được biến mất — phải còn lại
    # ở đâu đó trong kết quả trả về, kèm ghi chú số cảnh đã gộp.
    all_text = " ".join(s["prompt"] for s in scenes)
    assert marker in all_text
    assert scenes[-1]["overflow_merged_count"] == 1


def test_scenes_without_overflow_have_no_overflow_marker(db_session):
    """Đối chứng: khi KHÔNG có cảnh vượt, key `overflow_merged_count` không
    xuất hiện — nếu nó luôn có mặt (kể cả bằng 0), test trên sẽ không phân
    biệt được "đã gộp 0 cảnh" với "chưa từng chạy nhánh gộp"."""
    from apps.prompt_ai_ommi.services import breakdown as bsvc
    framework = _framework(default_n_scenes=2)
    fake_raw = {"scenes": [{"title": "Canh 1", "prompt": "p1"},
                          {"title": "Canh 2", "prompt": "p2"}]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 42)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        scenes = bsvc.breakdown(db_session, framework=framework,
                                story_vi="cau chuyen")
    assert all("overflow_merged_count" not in s for s in scenes)
