"""P4: untrusted planner output is normalized and deterministically rejected/accepted."""
from __future__ import annotations

import json

import pytest

from platform_core.agent.normalizer import (PlanNormalizeError, extract_json,
                                            normalize_plan)
from platform_core.agent.planner import build_prompt, plan_once
from platform_core.agent.validator import validate_plan


def _valid_plan():
    return {
        "version": 1, "goal": "Tạo và nâng cấp video", "budget_max_credit": 10000,
        "steps": [
            {"id": "s1", "tool": "video.generate", "after": [], "fanout": 1,
             "max_retry": 0, "on_fail": "retry_same", "verify": None,
             "params": {"prompt": "Rừng ban mai", "model": "seedance-2.0-mini",
                        "resolution": "720p", "duration": 5,
                        "aspect_ratio": "16:9", "generate_audio": True}},
            {"id": "s2", "tool": "video.upscale", "after": ["s1"], "fanout": 1,
             "max_retry": 0, "on_fail": "retry_same", "verify": None,
             "params": {"video_key": "$s1.video_key", "preset": "fast",
                        "target_height": 1080, "codec": "h264", "preview": False}},
        ],
    }


def _codes(result):
    return {issue.code for issue in result.issues}


def test_normalize_fenced_plain_and_tool_arguments():
    raw = json.dumps(_valid_plan())
    assert normalize_plan(raw)["version"] == 1
    assert normalize_plan(f"```json\n{raw}\n```")["steps"][0]["id"] == "s1"
    assert normalize_plan({"arguments": raw})["goal"] == "Tạo và nâng cấp video"


def test_normalize_flat_aliases():
    plan = normalize_plan({"nodes": [{"tool_name": "image.generate",
                                      "inputs": {"prompt": "x"},
                                      "depends_on": "s0"}]})
    assert plan["steps"][0]["tool"] == "image.generate"
    assert plan["steps"][0]["after"] == ["s0"]


def test_rac_truncated_va_json_bomb_bi_tu_choi():
    with pytest.raises(PlanNormalizeError):
        extract_json("không phải JSON")
    with pytest.raises(PlanNormalizeError):
        extract_json('{"steps": [')
    bomb = value = {}
    for _ in range(25):
        value["x"] = {}; value = value["x"]
    with pytest.raises(PlanNormalizeError, match="quá sâu"):
        extract_json(bomb)


def test_plan_hop_le_co_gia_tat_dinh():
    first = validate_plan(_valid_plan())
    second = validate_plan(_valid_plan())
    assert first.valid
    assert first.estimated_max_credit > 0
    assert first == second


@pytest.mark.parametrize(("mutate", "expected"), [
    (lambda p: p.update(version=2), "version"),
    (lambda p: p["steps"][0].update(tool="unknown.tool"), "tool"),
    (lambda p: p["steps"][0]["params"].update(resolution="4k"), "params"),
    (lambda p: p["steps"][1]["params"].update(video_key="$s9.video_key"), "reference"),
    (lambda p: p["steps"][1]["params"].update(video_key="$s1.missing"), "reference"),
    (lambda p: p["steps"][1]["params"].update(video_key="$s1.video_key") or p["steps"][1].update(after=[]), "reference_order"),
    (lambda p: p["steps"][1].update(after=["s1", "s2"]), "cycle"),
    (lambda p: p["steps"][0].update(fanout=5), "fanout"),
    (lambda p: p["steps"][0].update(max_retry=3), "retry"),
    (lambda p: p.update(budget_max_credit=0), "budget"),
    (lambda p: p["steps"][0]["params"].update(callback_url="https://evil.invalid"), "unsafe_param"),
    (lambda p: p["steps"][0]["params"].update(command="powershell.exe"), "unsafe_param"),
    (lambda p: p["steps"][0]["params"].update(source="file:///private/data"), "unsafe_param"),
])
def test_moi_nhom_plan_sai_bi_chan(mutate, expected):
    plan = _valid_plan()
    mutate(plan)
    assert expected in _codes(validate_plan(plan))


def test_sai_kieu_cong_video_noi_vao_text_bi_chan():
    plan = _valid_plan()
    plan["steps"][1] = {
        "id": "s2", "tool": "image.generate", "after": ["s1"],
        "params": {"prompt": "$s1.video_key", "model": "gemini-2.5-flash-image"},
        "fanout": 1, "max_retry": 0, "on_fail": "retry_same",
    }
    assert "port_type" in _codes(validate_plan(plan))


def test_input_reference_hop_le_va_sai_kieu():
    plan = _valid_plan()
    plan["steps"] = [{
        "id": "s1", "tool": "video.upscale", "after": [],
        "params": {"video_key": "$input.video"}, "fanout": 1,
        "max_retry": 0, "on_fail": "retry_same",
    }]
    assert validate_plan(plan, input_types={"video": "video"}).valid
    assert "port_type" in _codes(validate_plan(plan, input_types={"video": "image"}))


def test_quyen_app_va_so_du_duoc_chan():
    plan = _valid_plan()
    assert "tool" in _codes(validate_plan(plan, allowed_slugs=set()))
    assert "balance" in _codes(validate_plan(plan, balance=0))


def test_quyen_app_duoc_doc_tu_db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'access.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    from platform_core import app_access, users
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    try:
        user = users.tao_nguoi_dung(db, email="p4@x.com", password="matkhau-tot-12")
        app_access.dat_quyen(db, user.id, "taovideo", app_access.LOCKED)
        db.commit()
        assert "tool" in _codes(validate_plan(_valid_plan(), db=db, user=user))
    finally:
        db.close(); dbmod.reset_engine()


def test_storage_callback_va_artifact_literal_bi_chan():
    plan = _valid_plan()
    plan["steps"][0]["params"]["refs"] = [{"storage_key": "private/other-user"}]
    assert "unsafe_param" in _codes(validate_plan(plan))
    plan = _valid_plan()
    plan["steps"][1]["params"]["video_key"] = "private/other-user.mp4"
    assert "artifact_ref" in _codes(validate_plan(plan))


def test_planner_mock_khong_tao_job_credit_va_khong_lo_secret(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'p4.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    import platform_core.models as models
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    seen = {}
    try:
        def fake(prompt):
            seen["prompt"] = prompt
            return json.dumps(_valid_plan())
        plan = plan_once(db, goal="Tạo video", budget_max_credit=10000, llm_call=fake)
        assert validate_plan(plan).valid
        assert db.query(models.Job).count() == 0
        assert db.query(models.CreditEntry).count() == 0
        assert "credential" not in seen["prompt"].lower()
    finally:
        db.close(); dbmod.reset_engine()


def test_prompt_chi_chua_schema_khong_chua_secret(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET_SHOULD_NOT_APPEAR")
    prompt = build_prompt("x", budget_max_credit=100)
    assert "SECRET_SHOULD_NOT_APPEAR" not in prompt
    assert "[AVAILABLE TOOLS]" in prompt and "[BUDGET]" in prompt
