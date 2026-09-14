"""test_1259 — tran anh CONG BO phai khop tran DANG CUONG CHE tren may B.

## 🔴 Do duoc 14/09/2026 tren production

    gui 4 anh  ->  200
    gui 5 anh  ->  400 "yeu cau vuot tran cua cong"

Tran co that, dang chay, va **khong cho nao cong bo no**. Khach chi biet khi da
dam vao — va truoc ban va P0-2 cung ngay, thong diep con khong noi tran NAO hay
BAO NHIEU. Nay `constraints` khai `max_images` / `max_image_bytes`.

## ⛔ Va do la mot BAN SAO, nen no phai co nguoi canh

Nguoi cuong che van la cong may B (`llm_gateway/config.py`). May A chi DEM anh
de tinh ngan sach KV (`luong.dem_anh`), khong chan. Giu dung MOT nguoi cuong
che la co chu y: hai noi cung chan la hai noi se lech nhau.

Nhung the co nghia hai hang o `ngan_sach.py` la so chep sang. So chep ma khong
ai doi chieu chinh la co che da lam bang o kho nay noi sai **nam lan** — va ca
nam deu ve phia nguy hiem.

⇒ Phep kiem nay doi chieu voi may B **khi goi duoc**, va `skip` khi khong —
  khong bao gio XANH GIA bang cach lang le bo qua.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

from apps.ltt_llm.ngan_sach import ANH_BYTE_TOI_DA, SO_ANH_TOI_DA


def test_hai_hang_co_gia_tri_hop_ly():
    """Chan loi go tay hien nhien truoc khi noi toi may B."""
    assert SO_ANH_TOI_DA >= 1, "tran anh phai cho gui it nhat mot anh"
    assert ANH_BYTE_TOI_DA >= 1024 * 1024, (
        "tran byte duoi 1 MB se tu choi gan nhu moi anh that")


def test_hai_hang_DUOC_CONG_BO_ra_catalog():
    """🔴 Khai trong `ngan_sach` ma khong day ra `constraints` thi khach van mu."""
    from platform_core.public_api.catalog import build_catalog, build_models
    from platform_core.public_api.config import load_public_api_config

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    mo_hinh = [m for m in build_models(build_catalog(cfg))
               if m.name.startswith("ltt-")]
    assert mo_hinh, "khong thay model nao ten ltt-*"

    for m in mo_hinh:
        assert m.constraints.get("max_images") == SO_ANH_TOI_DA, (
            f"`{m.name}` khong cong bo `max_images` — khach gui anh thu 5 va "
            f"an 400 ma khong co cho nao noi truoc tran la bao nhieu")
        assert m.constraints.get("max_image_bytes") == ANH_BYTE_TOI_DA, (
            f"`{m.name}` khong cong bo `max_image_bytes`")


def _hoi_may_b() -> dict | None:
    """`{max_images, max_image_bytes}` cua cong may B, hoac `None` khi khong hoi duoc."""
    goc = (os.environ.get("LTT_LLM_BASE_URL") or "").strip()
    if not goc:
        return None
    try:
        r = urllib.request.Request(goc.rstrip("/") + "/health")
        with urllib.request.urlopen(r, timeout=8) as tra:
            d = json.loads(tra.read())
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None

    ra: dict = {}

    def di(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("max_images", "max_image_bytes"):
                    ra[k] = v
                else:
                    di(v)

    di(d)
    return ra or None


def test_BAN_SAO_khop_may_B_khi_hoi_duoc():
    """⛔ Doi chieu that. `skip` khi khong goi duoc — KHONG xanh gia.

    Mot phep kiem lang le bo qua khi khong lien lac duoc se bao "dat" suot
    nhung ngay may B doi cau hinh, va do dung la khoang thoi gian ta can no
    len tieng nhat.
    """
    that = _hoi_may_b()
    if that is None:
        pytest.skip("khong hoi duoc cong may B (thieu LTT_LLM_BASE_URL hoac "
                    "khong lien lac duoc) — KHONG phai la dat")

    if "max_images" in that:
        assert int(that["max_images"]) == SO_ANH_TOI_DA, (
            f"may B cuong che {that['max_images']} anh nhung ta CONG BO "
            f"{SO_ANH_TOI_DA} — khach doc so cua ta va dam vao so cua may B")
    if "max_image_bytes" in that:
        assert int(that["max_image_bytes"]) == ANH_BYTE_TOI_DA, (
            f"may B cuong che {that['max_image_bytes']} byte nhung ta cong bo "
            f"{ANH_BYTE_TOI_DA}")
