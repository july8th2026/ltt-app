"""`AdmissionModel` + `ToolSpec.admission_cho()` — một tool, hai pool (multijob 2.1).

🔴 VÌ SAO: hôm nay `admission_resource/admission_slots/admission_token_pool` chỉ
tả được MỘT pool cho cả tool. `ltt_llm` sắp có hai model (`ltt-3.8`, `ltt-3.5`)
chạy trên hai pool KV khác nhau trên CÙNG một tool `text.chat` — cần một ánh xạ
theo model, không phải một bộ ba số tĩnh. Task 5.5 (ảnh) dùng khoá `"*"` để áp
một sức chứa cho MỌI model của tool, nên bộ kiểm ở đây phải chứng minh cả hai
nhánh (theo model cụ thể VÀ theo `"*"`) trước khi có tool thật nào dùng tới.

Dải test của chương trình multijob: 1200-1249 (Task 1.2).
"""
from __future__ import annotations

import dataclasses

import pytest

from platform_core.registry import AdmissionModel, ToolSpec


def _tool(**overrides) -> ToolSpec:
    base = dict(
        name="test.tool",
        job_type="test.tool",
        description="tool test cho admission_cho",
        params_schema={"x": {"type": "string"}},
        returns={"y": "text"},
    )
    base.update(overrides)
    return ToolSpec(**base)


def test_anh_xa_theo_model_tra_dung_pool():
    """Mỗi model có resource/slots/pool riêng — đúng nhu cầu ltt-3.8 vs ltt-3.5."""
    tool = _tool(admission_theo_model={
        "ltt-3.8": AdmissionModel("llm_remote", 4, 1000, "rtx3090", "mac_dinh"),
        "ltt-3.5": AdmissionModel("llm_remote", 4, 500, "rtx3090", "mac_dinh"),
    })
    assert tool.admission_cho("ltt-3.8") == AdmissionModel(
        "llm_remote", 4, 1000, "rtx3090", "mac_dinh")
    assert tool.admission_cho("ltt-3.5") == AdmissionModel(
        "llm_remote", 4, 500, "rtx3090", "mac_dinh")


def test_wildcard_ap_dung_moi_model():
    """`"*"` là khoá áp cho MỌI model của tool (khuôn Task 5.5 — ảnh trên 3090)."""
    tool = _tool(admission_theo_model={
        "*": AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo"),
    })
    ky_vong = AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo")
    assert tool.admission_cho("bat_ky_model_nao") == ky_vong
    assert tool.admission_cho("mot_model_khac") == ky_vong
    assert tool.admission_cho("") == ky_vong


def test_model_la_khong_co_trong_anh_xa_va_khong_co_wildcard_thi_loi():
    """Model lạ, không có `"*"` để rơi về ⇒ `KeyError` — fail-closed, không im lặng."""
    tool = _tool(admission_theo_model={
        "ltt-3.8": AdmissionModel("llm_remote", 4),
    })
    with pytest.raises(KeyError):
        tool.admission_cho("ltt-3.5")


def test_tool_cu_chi_khai_admission_resource_slots_tuong_duong():
    """Tool cũ (trước 2.1) chỉ khai `admission_resource/slots[/token_pool]` —
    hành vi phải giữ nguyên, không phân biệt theo model."""
    tool = _tool(admission_resource="llm_remote", admission_slots=4,
                 admission_token_pool=262144)
    ky_vong = AdmissionModel("llm_remote", 4, 262144)
    assert tool.admission_cho() == ky_vong
    # Tool cũ không biết "model" là gì — mọi model đều nhận cùng một sức chứa.
    assert tool.admission_cho("bat_ky_model_nao") == ky_vong


def test_tool_cu_khong_token_pool_van_tuong_duong():
    """Nhánh cũ không khai `admission_token_pool` ⇒ mặc định 0, hành vi không đổi."""
    tool = _tool(admission_resource="ffmpeg", admission_slots=2)
    assert tool.admission_cho() == AdmissionModel("ffmpeg", 2, 0)


def test_tool_khong_khai_gi_tra_none():
    """Tool không khai admission gì ⇒ không có lease nào để giành — `None`."""
    tool = _tool()
    assert tool.admission_cho() is None
    assert tool.admission_cho("mot_model") is None


def test_doi_chung_bo_wildcard_lam_hong_ap_dung_moi_model(monkeypatch):
    """Đối chứng bắt buộc: tiêm bản `admission_cho` KHÔNG có nhánh `"*"` vào
    `ToolSpec`, rồi chứng minh ca 'wildcard áp mọi model' phải ĐỎ.

    Đây là phép kiểm cho chính bộ kiểm: nếu `test_wildcard_ap_dung_moi_model`
    xanh dù nhánh `"*"` bị rút ra, thì bộ kiểm đó không đo được cái nó tuyên bố
    đo — đúng bẫy "chốt không ghi vào cây" / "sự thật độc lập" đã gặp trước đây.
    """
    import platform_core.registry as registry

    def admission_cho_khong_wildcard(self, model: str = ""):
        m = self.admission_theo_model
        if m:
            if model in m:
                return m[model]
            # ⛔ Cố ý BỎ nhánh `if "*" in m: return m["*"]`.
            raise KeyError(
                f"{self.name}: model {model!r} khong co trong admission_theo_model")
        if self.admission_resource and self.admission_slots > 0:
            return registry.AdmissionModel(
                self.admission_resource, self.admission_slots,
                int(getattr(self, "admission_token_pool", 0) or 0))
        return None

    monkeypatch.setattr(registry.ToolSpec, "admission_cho",
                        admission_cho_khong_wildcard, raising=True)

    tool = _tool(admission_theo_model={
        "*": AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo"),
    })
    with pytest.raises(KeyError):
        tool.admission_cho("bat_ky_model_nao")


def test_catalog_khong_lo_admission_theo_model_ra_khach():
    """Chiếu catalog mang `admission_theo_model` để dùng nội bộ (giống
    `admission_token_pool`, `test_1201`), nhưng KHÔNG lộ nó ra `to_public_dict()`.
    """
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.public_api.catalog import project_tool

    goc = MANIFEST.tools[0]
    anh_xa = {
        "ltt-3.8": AdmissionModel("llm_remote", 4, 1000, "rtx3090", "mac_dinh"),
        "ltt-3.5": AdmissionModel("llm_remote", 4, 500, "rtx3090", "mac_dinh"),
    }
    tool_moi = dataclasses.replace(goc, admission_theo_model=anh_xa)

    projected = project_tool(MANIFEST, tool_moi)
    assert projected.admission_theo_model == anh_xa
    cong_khai = projected.to_public_dict()
    assert "admission_theo_model" not in cong_khai
    assert "ltt-3.8" not in str(cong_khai)
    assert "ltt-3.5" not in str(cong_khai)
