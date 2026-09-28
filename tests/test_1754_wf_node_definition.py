"""Spec §4.4 — NodeDefinition là KHUNG NHÌN dẫn xuất, không lưu vào CSDL."""
from __future__ import annotations

import dataclasses

import pytest

from platform_core.workflow import nut
from platform_core.workflow.cong_cu import CongCu


def _cc(**kw) -> CongCu:
    goc = dict(ten="image.generate", app_slug="taoanh", job_type="taoanh.generate",
               type_version=2, params_schema={"prompt": {"type": "string",
                                                         "required": True},
                                              "anh": {"type": "image"}},
               side_effect="external", idempotency_fields=("prompt",),
               tinh_gia=lambda p: 5, returns={"image_keys": "image[]"},
               mo_ta="Sinh anh tu mo ta. Cau thu hai bi cat khoi tieu de.",
               icon="ICON", app_name="Tao anh AI",
               resource={"class": "gpu", "vram_min_mb": 6000, "slots": 1})
    goc.update(kw)
    return CongCu(**goc)


def test_node_definition_dong_bang_va_khong_lo_ToolSpec():
    nd = nut.tu_toolspec(_cc())
    assert dataclasses.is_dataclass(nd)
    with pytest.raises(dataclasses.FrozenInstanceError):
        nd.type = "app.khac"                       # type: ignore[misc]
    # KHONG de `spec` (ToolSpec that) ro ra NodeDefinition: no mang
    # `api_contract`, ten provider, `sync_executor` — thu palette gui thang
    # ra trinh duyet.
    assert not any(f.name == "spec" for f in dataclasses.fields(nd))


def test_dinh_danh_va_phan_nhom():
    nd = nut.tu_toolspec(_cc())
    assert nd.type == "app.image.generate" and nd.type_version == 2
    assert nd.kind == "app" and nd.category == "LTT_APPS"
    assert nd.thi_hanh == "job" and nd.job_type == "taoanh.generate"


def test_tieu_de_lay_CAU_DAU_cua_mo_ta_khong_phai_mot_bang_nhan():
    # `_palette_tool` cu giu mot bang {"image.generate": "Tao hinh anh"} — 11
    # hang trong do da chet (test_967). Tieu de phai den tu du lieu app tu
    # khai, khong tu mot bang thu hai trong nen tang.
    nd = nut.tu_toolspec(_cc())
    assert nd.title == "Sinh anh tu mo ta"
    assert nd.description.startswith("Sinh anh tu mo ta")
    assert nd.icon == "ICON" and nd.app_name == "Tao anh AI"


def test_cong_va_tham_so_dan_xuat_qua_luoc_do():
    nd = nut.tu_toolspec(_cc())
    assert dict((t, c.type) for t, c in nd.cong_vao) == {"prompt": "text",
                                                         "anh": "image"}
    assert dict((t, c.type) for t, c in nd.cong_ra) == {"image_keys": "image[]"}
    assert nd.tham_so["properties"]["prompt"]["type"] == "string"
    assert nd.tham_so["required"] == ["prompt"]


def test_gia_theo_registry_va_tai_nguyen():
    nd = nut.tu_toolspec(_cc())
    assert nd.gia == nut.Gia.theo_registry("taoanh.generate")
    assert nd.resource == {"class": "gpu", "vram_min_mb": 6000, "slots": 1}
    assert "gpu" in nd.quyen and "network" in nd.quyen


def test_node_api_khong_xin_quyen_gpu():
    nd = nut.tu_toolspec(_cc(resource={"class": "api", "slots": 0}))
    assert nd.quyen == frozenset({"network"})


def test_resource_class_la_thi_tu_choi():
    with pytest.raises(nut.LoiNut, match="resource.class"):
        nut.tu_toolspec(_cc(resource={"class": "luong_tu"}))


def test_ma_loi_va_cho_dung_voi_cau_noi_that():
    nd = nut.tu_toolspec(_cc())
    assert nd.cho == ("JOB",)
    assert set(nd.ma_loi) == {"dau_vao_sai", "vuot_tran_bao_gia", "provider_loi",
                              "ket_qua_mo_ho", "bi_huy", "cong_cu_khong_con"}


def test_idempotency_va_side_effect_di_nguyen_tu_toolspec():
    nd = nut.tu_toolspec(_cc())
    assert nd.side_effect == "external"
    assert nd.idempotency_key_fields == ("prompt",)


def test_moi_tool_that_dung_duoc_NodeDefinition():
    from platform_core.workflow.cong_cu import tat_ca
    ra = [nut.tu_toolspec(cc) for cc in tat_ca().values()]
    # 🔴 HA 19 -> 18 (28/09): app `prompt_canh` bi xoa o `0c2aabab` (E5),
    #    mang theo ToolSpec `prompt_canh.run`. Ba phep LOAI TRU truoc khi
    #    ha — thieu chung thi ha banh coc la GIAU mot hoi quy that:
    #      1. so tut DUNG 1 (19 -> 18), khong phai 2+;
    #      2. `registry.discover()` bao 0 app nap loi => khong app nao
    #         rung vi sai kieu, tuc khong phai cai lo phep kiem nay canh;
    #      3. tool mat di dung la `prompt_canh.run` (doc tu
    #         `git show 0c2aabab^:apps/prompt_canh/manifest.py`).
    #    ⚠️ Hai tep nay bi BO SOT o luot ha 19->18 dau tien (chi sua
    #    `test_1756`/`test_1758`) vi ca hai phien deu dem tu THONG DIEP LOI
    #    cua mot tap con, khong dem KHANG DINH trong kho.
    assert len(ra) >= 18
    assert all(nd.type.startswith("app.") for nd in ra)
