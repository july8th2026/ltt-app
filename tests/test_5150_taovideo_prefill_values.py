"""prefill.build_form_values(): payload tho -> gia tri dien san form.

Ham THUAN — khong CSDL, khong storage, khong import `apps.prompt_ai_ommi`.
"""
from __future__ import annotations


def test_gia_tri_hop_le_duoc_giu_nguyen():
    from apps.taovideo import prefill
    payload = {"prompt": "Mot canh @IMG_1",
               "params": {"model": "seedance-2.0-mini", "resolution": "480p",
                          "duration": 5, "aspect_ratio": "16:9",
                          "generate_audio": True, "camera": "dolly_in",
                          "motion": "cinematic", "visual_style": "cinematic"}}
    values = prefill.build_form_values(payload)
    assert values["prompt"] == "Mot canh @IMG_1"
    assert values["model"] == "seedance-2.0-mini"
    assert values["resolution"] == "480p"
    assert values["duration"] == "5"
    assert values["aspect_ratio"] == "16:9"
    assert values["camera"] == "dolly_in"
    assert values["motion"] == "cinematic"
    assert values["visual_style"] == "cinematic"
    assert values["generate_audio"] is True


def test_gia_tri_khong_thuoc_enum_bi_rong_hoa():
    from apps.taovideo import models as _m
    from apps.taovideo import prefill
    payload = {"prompt": "canh khac",
               "params": {"model": "model-khong-ton-tai",
                          "camera": "medium shot, 35mm, slow push in",
                          "motion": "khong-hop-le",
                          "visual_style": "khong-hop-le"}}
    values = prefill.build_form_values(payload)
    assert values["model"] == _m.DEFAULT_MODEL
    # Payload lech chuan (chu tu do lot qua, du `_doan_enum()` phia ommi le ra
    # phai chan) -> prefill KHONG tu doan lai, chi rong hoa cho an toan form.
    assert values["camera"] == ""
    assert values["motion"] == ""
    assert values["visual_style"] == ""


def test_payload_rac_khong_lam_no_ham():
    """Payload den tu trinh duyet: `params` co the thieu, sai kieu, hoac None."""
    from apps.taovideo import prefill
    for rac in ({}, {"params": None}, {"params": "khong phai dict"},
                {"prompt": None, "params": []}):
        values = prefill.build_form_values(rac)
        assert values["prompt"] == ""
        assert values["camera"] == ""
        assert values["duration"] == ""
        # `generate_audio` mac dinh True — giong mac dinh cua `params_schema`.
        assert values["generate_audio"] is True


def test_khong_import_prompt_ai_ommi():
    """Canh app->app la MOT CHIEU — doc bang AST, khong import."""
    import ast
    import pathlib
    src = pathlib.Path("apps/taovideo/prefill.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    for node in ast.walk(cay):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("apps.prompt_ai_ommi")
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("apps.prompt_ai_ommi")


def test_banh_coc_enum_khop_manifest():
    """Hai cho khai cung mot dieu thi phai co nguoi bat khop.

    `prefill.py` khai LAI literal ba bo enum de tranh vong import
    `routes.py` <-> `prefill.py`. Tep test thi import `manifest` thoai mai.
    """
    from apps.taovideo import prefill
    from apps.taovideo.manifest import MANIFEST

    spec = next(t for t in MANIFEST.tools if t.name == "video.generate")
    that = spec.params_schema
    # `""` co trong manifest voi nghia "chua xac dinh"; `prefill` xu ly no bang
    # nhanh rong hoa, nen bo o day la bo manifest TRU `""`.
    assert prefill._CAMERA == set(that["camera"]["values"]) - {""}
    assert prefill._MOTION == set(that["motion"]["values"]) - {""}
    assert prefill._VISUAL_STYLE == set(that["visual_style"]["values"]) - {""}
