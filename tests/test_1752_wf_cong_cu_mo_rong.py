"""`CongCu` là MỘT nguồn tra ToolSpec — plan 02 dựng NodeDefinition trên nó."""
from __future__ import annotations

from platform_core.workflow.cong_cu import CongCu, tat_ca


def test_cong_cu_gia_cua_plan_01a_van_dung_duoc():
    # ⛔ Mọi trường mới PHẢI có mặc định: `tests/test_1716` và `test_1718`
    #    dựng `CongCu` bằng tay với đúng 9 tham số.
    cc = CongCu(ten="t.x", app_slug="t", job_type="t.x", type_version=1,
                params_schema={}, side_effect="external",
                idempotency_fields=(), tinh_gia=lambda p: 3)
    assert cc.returns == {} and cc.cong == {} and cc.resource == {}
    assert cc.workflow is True and cc.customer_visible is True
    assert cc.mo_ta == "" and cc.icon == "" and cc.app_name == ""
    assert cc.timeout_expr == "" and cc.so_lan_thu == 0 and cc.mock is None


def test_tat_ca_chep_du_truong_tu_toolspec_that():
    ra = tat_ca()
    cc = ra["transcript.run"]
    assert cc.returns == {"transcript": "json"}
    assert cc.resource["class"] == "gpu" and cc.resource["vram_min_mb"] == 5000
    assert cc.mo_ta.startswith("Phiên âm")
    assert cc.app_name and cc.icon          # từ AppManifest, không gõ cứng
    assert cc.workflow is True


def test_tat_ca_khong_bo_sot_tool_nao_cua_registry():
    from platform_core import registry
    that = {t.name for i in registry.discover() if not i.error
            and i.manifest.enabled for t in i.manifest.tools}
    assert set(tat_ca()) == that
