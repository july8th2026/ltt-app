"""P7: verifier ordering, fault policy va credit trong bo kiem.

⏭️ 23/09/2026: ba bai *chay that qua runtime* (`structural_retry`,
   `policy_dung_ngay`, `inconclusive_retry_huu_han`) DA GO cung
   `platform_core/agent/executor.py` — spec §17.5. Chung lai `tick()` cua
   runtime v1 qua mot fixture `runtime`, va duong ay khong con.

⚠️ Chinh sach thu lai co gioi han **khong** chet theo: no la luat cua dong co
   Workflow V2 bay gio (`platform_core/workflow/may_trang_thai.py` —
   `RETRY_SCHEDULED`), va do la cho phai dung mot bai tuong duong khi lop ay
   duoc do. `verifier.py` o lai nguyen ven (spec §17.6), nen cac bai don vi
   ngay duoi van la phep do that cua no.
"""
from __future__ import annotations

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
    # Đọc đơn giá từ app rồi suy ra trần, thay vì gõ lại hai con số — chúng
    # đổi cùng bảng giá model nhà (pha 06.3).
    from apps.taoanh.manifest import MANIFEST as M_TAO
    don_gia = M_TAO.credit_cost({"count": 1})
    assert result.step_costs[0]["unit"] == don_gia
    assert result.valid and result.estimated_max_credit == (
        (don_gia + result.step_costs[0]["verifier_unit"])
        * (1 + result.step_costs[0]["max_retry"]))
    assert result.step_costs[0]["verifier_unit"] == 1
