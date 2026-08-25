"""P7: verifier ordering, fault policy, bounded retry and credit."""
from __future__ import annotations

from tests.conftest import bao_dam_user
import pytest


def test_technical_reject_truoc_vlm(tmp_path):
    from platform_core.agent import verifier
    called = []
    result = verifier.verify(
        {"video": str(tmp_path / "missing.mp4")},
        [{"check": "vlm_judge", "rubric": "ok"},
         {"check": "technical", "mime": "video/"}],
        judge=lambda *_: called.append(True),
    )
    assert len(result) == 1
    assert result[0].check == "technical" and result[0].fault == "structural"
    assert called == []


def test_technical_probe_timeout_la_inconclusive(tmp_path):
    from platform_core.agent import verifier
    video = tmp_path / "x.mp4"; video.write_bytes(b"not-real-video")
    result = verifier.technical(
        {"video": str(video)}, {"check": "technical", "min_duration": 1},
        probe=lambda _path: (_ for _ in ()).throw(TimeoutError()),
    )
    assert not result.passed and result.fault == "inconclusive"


@pytest.mark.parametrize("raw,fault", [
    ({"pass": False, "score": .2, "fault": "partial", "reason": "x"}, "partial"),
    ({"pass": False, "score": .2, "fault": "structural", "reason": "x"}, "structural"),
    ({"pass": False, "score": .0, "fault": "policy", "reason": "x"}, "policy"),
    ("not json", "inconclusive"),
])
def test_vlm_fault_schema_deterministic(raw, fault):
    from platform_core.agent import verifier
    result = verifier.vlm_judge({}, {}, judge=lambda *_: raw)
    assert not result.passed and result.fault == fault


def test_face_identity_khong_co_recognition_khong_gia_pass():
    from platform_core.agent import verifier
    result = verifier.face_identity({}, {})
    assert not result.passed and result.fault == "inconclusive"


def test_reason_redact_secret_email_token():
    from platform_core.agent import verifier
    result = verifier.vlm_judge({}, {}, judge=lambda *_: {
        "pass": False, "score": 0, "fault": "policy",
        "reason": "email a@b.com token=abc123 Bearer xyz",
        "model": "safe-model", "key_ref": "key-slot-2",
    })
    assert "a@b.com" not in result.reason
    assert "abc123" not in result.reason and "xyz" not in result.reason


def test_validator_tinh_verifier_vao_tran_moi_attempt():
    from platform_core.agent.validator import validate_plan
    plan = {"version": 1, "budget_max_credit": 12, "steps": [{
        "id": "s1", "tool": "image.generate", "after": [],
        "params": {"prompt": "forest"}, "fanout": 1, "max_retry": 1,
        "on_fail": "regenerate", "verify": {"check": "vlm_judge"},
    }]}
    result = validate_plan(plan)
    assert result.valid and result.estimated_max_credit == 12
    assert result.step_costs[0]["unit"] == 5
    assert result.step_costs[0]["verifier_unit"] == 1


@pytest.fixture()
def runtime(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'verifier-runtime.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    from platform_core.agent import executor
    from platform_core.registry import ToolSpec
    spec = ToolSpec(name="fake.image", job_type="fake.image", description="fake",
                    params_schema={}, returns={"image": "image"},
                    verifiable=("vlm_judge",))
    app = type("App", (), {"slug": "fake", "error": "",
                            "manifest": type("Manifest", (), {
                                "tools": (spec,), "requires": ("api",)})()})()
    monkeypatch.setattr(executor, "discover_tools", lambda: {spec.name: spec})
    monkeypatch.setattr(executor.registry, "discover", lambda: [app])
    monkeypatch.setattr(executor.registry, "credit_for", lambda *_a, **_k: 2)
    try:
        yield session
    finally:
        session.close(); dbmod.reset_engine()


def _run(runtime, *, max_retry=1, on_fail="regenerate"):
    from platform_core import credit
    from platform_core.agent import budget, runs
    from platform_core.agent.validator import ValidationResult
    plan = {"version": 1, "budget_max_credit": 30, "steps": [{
        "id": "s1", "tool": "fake.image", "after": [], "params": {},
        "verify": {"check": "vlm_judge", "rubric": "quality"},
        "max_retry": max_retry, "on_fail": on_fail,
    }]}
    bao_dam_user(runtime, "u1"); credit.cap_tay(runtime, "u1", 100, by="test")
    run = runs.create_run(runtime, user_id="u1", goal="verify")
    budget.set_quote(runtime, run, plan=plan,
                     validation=ValidationResult(True, (), 8, ()))
    budget.approve(runtime, run_id=run.id, user_id="u1", approved_by="u1",
                   expected_version=run.version)
    runtime.commit()
    return run


def test_structural_retry_dung_cap_va_actual_credit(runtime):
    from platform_core import jobs
    from platform_core.agent import executor, runs
    run = _run(runtime)
    answers = iter([
        {"pass": False, "score": .1, "fault": "structural", "reason": "bad"},
        {"pass": True, "score": .9, "fault": "", "reason": "good"},
    ])
    judge = lambda *_: next(answers)
    executor.tick(runtime, run_id=run.id, user_id="u1", judge=judge); runtime.commit()
    jobs.complete(runtime, runs.children(runtime, run)[0], {"image": "r1"}); runtime.commit()
    executor.tick(runtime, run_id=run.id, user_id="u1", judge=judge); runtime.commit()
    assert len(runs.children(runtime, run)) == 2
    jobs.complete(runtime, runs.children(runtime, run)[1], {"image": "r2"}); runtime.commit()
    executor.tick(runtime, run_id=run.id, user_id="u1", judge=judge); runtime.commit()
    assert run.status == "done" and run.actual == 10
    assert run.checkpoint["s1"]["attempt"] == 1
    assert len([e for e in run.decision_log if e.get("event") == "retry"]) == 1


def test_policy_dung_ngay_khong_retry(runtime):
    from platform_core import jobs
    from platform_core.agent import executor, runs
    run = _run(runtime, max_retry=2)
    executor.tick(runtime, run_id=run.id, user_id="u1"); runtime.commit()
    jobs.complete(runtime, runs.children(runtime, run)[0], {"image": "r"}); runtime.commit()
    executor.tick(runtime, run_id=run.id, user_id="u1", judge=lambda *_: {
        "pass": False, "score": 0, "fault": "policy", "reason": "blocked"})
    runtime.commit()
    assert run.status == "error" and len(runs.children(runtime, run)) == 1


def test_inconclusive_retry_huu_han_roi_dung(runtime):
    from platform_core import jobs
    from platform_core.agent import executor, runs
    run = _run(runtime, max_retry=1)
    executor.tick(runtime, run_id=run.id, user_id="u1"); runtime.commit()
    for index in range(2):
        child = runs.children(runtime, run)[index]
        jobs.complete(runtime, child, {"image": "r"}); runtime.commit()
        executor.tick(runtime, run_id=run.id, user_id="u1",
                      judge=lambda *_: "garbage"); runtime.commit()
    assert run.status == "error" and len(runs.children(runtime, run)) == 2
