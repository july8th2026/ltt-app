"""
test_614 — Phase 06 (điều kiện PASS của gói): một alias model MỚI xuất hiện trong
catalog ChatLTT **chỉ bằng bản khai registry**, không sửa một dòng UI/app nào.

Bộ chọn model của ChatLTT đọc `NangLuc.models` (alias → description/stability/
constraints) — không có `if alias == ...` ở đâu. Test này là phản đề của
`visionModels[]` hardcode trong LibreChat (báo cáo Phase 01 §6).
"""
from __future__ import annotations

from apps.chatltt.services import chinh_sach
from platform_core import registry as reg


def _app_text(models: dict):
    tool = reg.ToolSpec(
        name="text.chat", job_type="t614.j", description="d",
        params_schema={"messages": {"type": "json[]", "required": True},
                       "model": {"type": "enum", "values": list(models),
                                 "default": next(iter(models))}},
        returns={"content": "text", "usage": "json"},
        sync_executor="tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA",
        api_exposed=True,
        api_contract={"description": "chat", "scopes": ("jobs:create",),
                      "models": models, "enums": {"model": list(models)}},
    )
    m = reg.AppManifest(slug="t614", display_name="t614", route_prefix="/t614",
                        job_types=("t614.j",), credit_cost=lambda p: 1,
                        surface="runtime", lifecycle="internal", tools=(tool,))
    return reg.LoadedApp(manifest=m, router=None)


HAI_ALIAS = {
    "ltt_llm": {"id": "noi-bo-a", "stability": "stable",
                "constraints": {"context_window": 88555, "max_output_tokens": 32768}},
    "ltt_llm_vision": {"id": "noi-bo-b", "stability": "stable",
                       "constraints": {"context_window": 28000, "reads_images": True}},
}
BA_ALIAS = dict(HAI_ALIAS, ltt_llm_nhanh={
    "id": "noi-bo-c", "stability": "experimental",
    "description": "ban nhanh, ngu canh ngan",
    "constraints": {"context_window": 8000, "max_output_tokens": 2048}})


def test_them_alias_bang_registry_la_du():
    truoc = chinh_sach.danh_muc(None, user_id="u", apps=[_app_text(HAI_ALIAS)])[0]
    sau = chinh_sach.danh_muc(None, user_id="u", apps=[_app_text(BA_ALIAS)])[0]
    assert set(truoc.models) == {"ltt_llm", "ltt_llm_vision"}
    assert set(sau.models) == {"ltt_llm", "ltt_llm_vision", "ltt_llm_nhanh"}
    moi = sau.models["ltt_llm_nhanh"]
    assert moi["stability"] == "experimental"
    assert moi["constraints"]["context_window"] == 8000
    assert "id" not in moi                                   # id nội bộ không rời nền tảng
    # Cờ năng lực đi theo metadata: UI bật nút đính ảnh khi `reads_images`, không khi thiếu.
    assert sau.models["ltt_llm_vision"]["constraints"].get("reads_images") is True
    assert not sau.models["ltt_llm_nhanh"]["constraints"].get("reads_images")
    # Hợp đồng công khai cũng liệt kê enum alias — cùng nguồn, không gõ tay ở UI.
    enum = sau.hop_dong["input_schema"]["properties"]["model"]["enum"]
    assert set(enum) == set(BA_ALIAS)


def test_khong_co_if_theo_ten_model_trong_app_chatltt():
    """Không dòng mã nào của ChatLTT rẽ nhánh theo tên alias hay id nội bộ."""
    import re
    from pathlib import Path

    goc = Path(__file__).resolve().parents[1] / "apps" / "chatltt"
    xau = re.compile(r"(qwen|hidream|noi-bo|ltt_llm_vision|ltt_llm_nhanh)")
    for tep in goc.rglob("*.py"):
        for i, dong in enumerate(tep.read_text(encoding="utf-8").splitlines(), 1):
            ma = dong.split("#", 1)[0]
            assert not xau.search(ma), f"{tep.name}:{i} re nhanh theo ten model: {dong.strip()}"
