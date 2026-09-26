"""Lan scheduler theo tham so — job tu API khong duoc giu thua VRAM.

`gpu_vram_mb` khoa theo `job_type`, nen `job_type` KHONG phai mot chi tiet noi
bo: no la con so VRAM ma scheduler giu cho truoc khi job chay.

🔴 Loi that, do duoc 2026-08-29. `apps/upscalevideo` khai ba lan
(`render` 12.000 MB · `render.fast` 2.000 · `render.quality` 12.000). Duong WEB
chon lan theo preset tu lau (`service.job_type_for_preset`). Duong API thi dung
thang `tool.job_type`, tuc MOI job tu API xin 12.000 MB — ke ca `preset=fast`,
von do that chi an 848 MB (H32.6).

⇒ Tren mot may co ba ho dung chung GPU, mot job fast tu API khong vua cho trong
  con lai va nam cho, du no chi can mot phan sau cho no dang xin. Khach da bi
  giu credit roi.

⭐ Bang khai la DU LIEU chu khong phai mot ham, va do la mot lua chon: mot bang
   anh xa thi registry kiem duoc LUC NAP. Mot ham thi khong kiem duoc gi cho toi
   khi no chay — va cho no chay la cho tieu tien cua khach.
"""
from __future__ import annotations

import pytest

from platform_core.registry import (AppManifest, RegistryError, ToolSpec,
                                    _validate_tool, discover)

SLUG = "lanthu"


def _tool(**doi) -> ToolSpec:
    goc = dict(
        name="video.lanthu", job_type="lanthu.render",
        description="Tool thu de kiem bang lan.",
        params_schema={
            "video_key": {"type": "video", "required": True},
            "preset": {"type": "enum", "values": ["fast", "quality"],
                       "default": "fast"},
        },
        returns={"video_key": "video"},
        job_type_by="preset",
        job_type_lanes={"fast": "lanthu.render.fast",
                        "quality": "lanthu.render.quality"},
    )
    goc.update(doi)
    return ToolSpec(**goc)


def _manifest(tool: ToolSpec) -> AppManifest:
    return AppManifest(
        slug=SLUG, display_name="App lan thu", route_prefix=f"/{SLUG}",
        job_types=("lanthu.render", "lanthu.render.fast", "lanthu.render.quality"),
        requires=("api",), credit_cost=lambda p: 1, tools=(tool,),
        enabled=False, public=False, surface="runtime", lifecycle="internal")


# ── Giai lan ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("params,mong_doi", [
    ({"preset": "fast"}, "lanthu.render.fast"),
    ({"preset": "quality"}, "lanthu.render.quality"),
    # Khong khai preset -> lay `default` cua chinh params_schema, KHONG roi ve
    # lan mac dinh. Day la truong hop hay gap nhat tu API: khach gui dung mot
    # `video_key` roi de nen tang chon phan con lai.
    ({}, "lanthu.render.fast"),
    ({"preset": None}, "lanthu.render.fast"),
])
def test_lan_giai_theo_tham_so(params, mong_doi):
    assert _tool().lane_for(params) == mong_doi


def test_gia_tri_la_thi_ve_lan_mac_dinh_chu_khong_no():
    """Gia tri la bi tang validate chan tu truoc; o day chi can KHONG NEM."""
    assert _tool().lane_for({"preset": "bua"}) == "lanthu.render"


def test_tool_khong_khai_gi_thi_giu_nguyen_hanh_vi_cu():
    tool = _tool(job_type_by="", job_type_lanes={})
    assert tool.lane_for({"preset": "fast"}) == "lanthu.render"


# ── Hop dong: khai sai thi app KHONG NAP DUOC ───────────────────────────────

def test_khai_nua_voi_bi_tu_choi():
    xau = _tool(job_type_lanes={})
    with pytest.raises(RegistryError, match="nửa vời"):
        _validate_tool(_manifest(xau), xau, set())


def test_job_type_by_tro_toi_tham_so_khong_co_that():
    xau = _tool(job_type_by="khong_co_that")
    with pytest.raises(RegistryError, match="job_type_by"):
        _validate_tool(_manifest(xau), xau, set())


def test_lan_khong_thuoc_job_types_cua_app():
    xau = _tool(job_type_lanes={"fast": "app_khac.render", "quality": "lanthu.render.quality"})
    with pytest.raises(RegistryError, match="job_types"):
        _validate_tool(_manifest(xau), xau, set())


def test_thieu_mot_gia_tri_enum_la_DO():
    """Thieu mot gia tri thi no roi AM THAM ve lan mac dinh.

    Do dung la loi viec nay sinh ra de sua, chi khac la nay no nap trong mot
    bang trong nhu da day du — te hon ban goc vi no trong giong mot quyet dinh.
    """
    xau = _tool(job_type_lanes={"fast": "lanthu.render.fast"})
    with pytest.raises(RegistryError, match="thiếu giá trị"):
        _validate_tool(_manifest(xau), xau, set())


# ── App that: bat khi ai do go bang khai di ─────────────────────────────────

def test_video_upscale_xin_dung_VRAM_cua_preset_no_chay():
    """Banh coc. Go `job_type_lanes` thi phep kiem nay do truoc khach."""
    man = next(i.manifest for i in discover()
               if not i.error and i.manifest.slug == "upscalevideo")
    tool = next(t for t in man.tools if t.name == "video.upscale")

    lan_fast = tool.lane_for({"preset": "fast"})
    lan_quality = tool.lane_for({"preset": "quality"})

    # H32.6 (2026-09-25, docs/UPSCALE_V2/01_HARDWARE_TRUTH.md): ban khai da
    # giam theo do that (fast 848MB -> xin 1000, quality 11.176MB -> xin
    # 11500). Phep kiem nay van giu nguyen viec no bao ve: fast/quality PHAI
    # khac lan legacy (12000) va khac nhau, khong phai con so 2000/12000 cu.
    assert man.vram_for(lan_fast) == 1000, (
        f"job fast xin {man.vram_for(lan_fast)}MB — do that la 848MB")
    assert man.vram_for(lan_quality) == 11500
    # Va mac dinh (khach khong khai preset) phai la lan NHE, khong phai lan cu.
    assert man.vram_for(tool.lane_for({})) == 1000


def test_duong_web_va_duong_api_chon_CUNG_mot_lan():
    """Hai duong lech nhau chinh la hinh dang cua loi nay.

    `service.job_type_for_preset` la duong web; `lane_for` la duong API. Chung
    phai tra ve cung mot thu cho cung mot preset, neu khong thi mot trong hai
    dang giu thua GPU va khong ai biet ben nao.
    """
    from apps.upscalevideo.service import job_type_for_preset

    tool = next(t for i in discover() if not i.error
                for t in i.manifest.tools if t.name == "video.upscale")
    for preset in ("fast", "quality"):
        assert tool.lane_for({"preset": preset}) == job_type_for_preset(preset), preset


def test_hai_tool_ANH_EM_khong_duoc_chay_hai_hanh_vi_khac_nhau():
    """`video.upscale` va `image.upscale` dung chung handler va chung bang VRAM.

    ⚠️ Chung da tung lech nhau **trong luc ca hai cung mo cho khach**: ngay
       29/08 ban sua lan len production cho `video.upscale` truoc, con
       `image.upscale` — tool mo TU LAU va dang thu tien — van giu lan cu.

    Hai tool cung ho ma xep lich khac nhau la thu khong ai doc ra tu ma: chung
    o canh nhau trong CUNG mot manifest, nen mat gap qua cho lech do.
    """
    man = next(i.manifest for i in discover()
               if not i.error and i.manifest.slug == "upscalevideo")
    tools = {t.name: t for t in man.tools}

    for preset in ("fast", "quality"):
        v = tools["video.upscale"].lane_for({"preset": preset})
        i = tools["image.upscale"].lane_for({"preset": preset})
        assert v == i, f"{preset}: video->{v} nhung image->{i}"

    # Va mac dinh cua CA HAI phai la lan nhe.
    # H32.6 (2026-09-25): ban khai giam 2000->1000 theo do that 848MB.
    for ten in ("video.upscale", "image.upscale"):
        lane = tools[ten].lane_for({})
        assert man.vram_for(lane) == 1000, (
            f"{ten} mac dinh xin {man.vram_for(lane)}MB — do that la 848MB")


def test_moi_lan_deu_co_handler_that():
    """Mot lan khong ai nhan thi job chet o worker, khong phai o gate."""
    from platform_core.jobs import resolve_handler

    tool = next(t for i in discover() if not i.error
                for t in i.manifest.tools if t.name == "video.upscale")
    for lane in set(tool.job_type_lanes.values()) | {tool.job_type}:
        assert callable(resolve_handler(lane)), lane
