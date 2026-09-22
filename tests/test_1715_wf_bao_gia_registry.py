"""Giá node lấy từ registry, không từ params.gia của client (audit 22/09)."""
from __future__ import annotations

import pytest

from platform_core.workflow import bao_gia
from platform_core.workflow.cong_cu import CongCu


def _cc(schema, gia):
    return {"t.x": CongCu(ten="t.x", app_slug="t", job_type="t.x",
                          type_version=1, params_schema=schema,
                          side_effect="external", idempotency_fields=(),
                          tinh_gia=gia)}


def _g(params):
    return {"schema": "ltt.workflow/3", "nodes": [
        {"id": "a", "type": "app.t.x", "params": params, "thi_hanh": "job"}],
        "edges": [], "thu_tu": ["a"]}


def test_params_gia_cua_client_bi_bo_qua():
    g = _g({"gia": 0, "count": 2})
    bg = bao_gia.bao_gia_do_thi(g, cong_cu=_cc({}, lambda p: 7 * p.get("count", 1)))
    assert bg.toi_da == 14 and g["bang_gia"] == {"a": 14}
    assert g["nodes"][0]["gia_tran"] == 14


def test_tham_chieu_enum_lay_max():
    schema = {"model": {"type": "enum", "values": ["re", "dat"]}}
    gia = {"re": 3, "dat": 30}
    g = _g({"model": "{{ nodes.z.output.m }}"})
    bg = bao_gia.bao_gia_do_thi(
        g, cong_cu=_cc(schema, lambda p: gia.get(p.get("model"), 1)))
    assert bg.toi_da == 30


def test_tham_chieu_int_lay_max():
    schema = {"count": {"type": "int", "min": 1, "max": 4}}
    g = _g({"count": "{{ nodes.z.output.n }}"})
    bg = bao_gia.bao_gia_do_thi(g, cong_cu=_cc(schema,
                                               lambda p: 5 * p.get("count", 1)))
    assert bg.toi_da == 20


def test_tham_chieu_khong_bien_thi_tinh_theo_mac_dinh():
    g = _g({"prompt": "{{ nodes.z.output.t }}"})
    bg = bao_gia.bao_gia_do_thi(g, cong_cu=_cc({}, lambda p: 9 if "prompt" not in p else 99))
    assert bg.toi_da == 9


def test_khong_tinh_duoc_gia_thi_tu_choi():
    def hong(_p):
        raise RuntimeError("chua khai gia")
    with pytest.raises(bao_gia.KhongBaoGiaDuoc):
        bao_gia.bao_gia_do_thi(_g({}), cong_cu=_cc({}, hong))
