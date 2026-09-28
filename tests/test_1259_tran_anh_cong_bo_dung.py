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

from apps.ltt_llm.ngan_sach import (ANH_BYTE_TOI_DA, SO_ANH_TOI_DA,
                                    TOKEN_ANH_TOI_DA, TOKEN_ANH_TOI_THIEU)


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
        # ⛔ `max_images` DA GO 28/09 (C4). Thay bang ba so cho khach TU TINH
        #    duoc chi phi ngu canh cua tung anh - thu that su quyet dinh mot anh
        #    co lot hay khong. Mot con so DEM khong noi len dieu gi.
        assert "max_images" not in m.constraints, (
            f"`{m.name}` con cong bo `max_images` — tran dem da go, cong bo lai "
            f"la hua mot dieu khong ai cuong che")
        for k, mong in (("min_image_tokens", TOKEN_ANH_TOI_THIEU),
                        ("max_image_tokens", TOKEN_ANH_TOI_DA)):
            assert m.constraints.get(k) == mong, (
                f"`{m.name}` khong cong bo `{k}` — khach khong tinh truoc duoc "
                f"chi phi ngu canh cua anh, tuc lai phai dam vao tuong moi biet")
        assert m.constraints.get("max_image_bytes") == ANH_BYTE_TOI_DA, (
            f"`{m.name}` khong cong bo `max_image_bytes`")


def _hoi_may_b() -> dict | None:
    """`{max_images, max_image_bytes}` cua cong may B, hoac `None` khi khong hoi duoc."""
    goc = (os.environ.get("LTT_LLM_BASE_URL") or "").strip()
    if not goc:
        return None
    token = (os.environ.get("LTT_LLM_TOKEN") or "").strip()
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = urllib.request.Request(goc.rstrip("/") + "/health", headers=headers)
        with urllib.request.urlopen(r, timeout=8) as tra:
            d = json.loads(tra.read())
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None

    ra: dict = {}
    # 🔴 Hop dong /health CU cong bo so anh duoi `tran.images`. Ban 28/09 go no
    #    va thay bang `vat_ly.theo_model[m].image_{min,max}_tokens`. Doc CA HAI:
    #    su co mat cua ten CU la bang chung may B chua deploy, va do la mot ca
    #    phai DO — khong phai mot ca bo qua.
    tran = d.get("tran") if isinstance(d, dict) else None
    if isinstance(tran, dict) and "images" in tran:
        ra["max_images"] = tran["images"]

    def di(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("max_images", "max_image_bytes",
                         "image_min_tokens", "image_max_tokens"):
                    ra[k] = v
                else:
                    di(v)

    di(d)
    return ra or None


def test_hoi_may_B_mang_bearer_vi_health_duoc_bao_ve(monkeypatch):
    """`/health` production doi bearer; thieu header thi doi chieu luon skip."""
    monkeypatch.setenv("LTT_LLM_BASE_URL", "http://may-b:8299")
    monkeypatch.setenv("LTT_LLM_TOKEN", "token-thu")

    class Tra:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return json.dumps({"tran": {"images": SO_ANH_TOI_DA}}).encode()

    def urlopen(req, timeout):
        assert timeout == 8
        assert req.get_header("Authorization") == "Bearer token-thu"
        return Tra()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert _hoi_may_b() == {"max_images": SO_ANH_TOI_DA}


@pytest.fixture(scope="module", autouse=True)
def _nap_moi_truong_may_b_cho_pytest_go_tay():
    """`pytest tests/test_1259...` go tay khong di qua `gate.py`, nen
    `_nap_moi_truong_test` cua gate (chi chay trong buoc "bo test" cua MOT
    luot gate) khong tung cap `LTT_LLM_BASE_URL`/`LTT_LLM_TOKEN` o day. Goi lai
    dung bo nap do (`tools/moi_truong_may_b.nap_env_may_b`, qua SSH khoa
    `~/.ssh/nexus_b`) de `test_BAN_SAO_khop_may_B` doi chieu duoc khi chay tay.

    Chi dat bien con THIEU, va tra lai nguyen trang sau khi het module — khong
    ro sang tep test khac trong cung phien `pytest`. Khong hoi duoc may B
    (thieu khoa SSH, may khong tra loi) thi khong dat gi — test_BAN_SAO van DO
    dung thiet ke; khong in, khong log token.
    """
    m = _nap()
    truoc = {k: os.environ.get(k) for k in ("LTT_LLM_BASE_URL", "LTT_LLM_TOKEN")}
    trang_thai = m.nap_env_may_b(os.environ)
    if trang_thai:
        print(f"  [may B] {trang_thai}")
    yield
    for k, v in truoc.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_BAN_SAO_khop_may_B():
    """⛔ Doi chieu that; khong hoi duoc la DO, khong bo qua va khong xanh gia."""
    that = _hoi_may_b()
    assert that is not None, (
        "khong doi chieu duoc cong may B: can LTT_LLM_BASE_URL, "
        "LTT_LLM_TOKEN va ket noi toi /health")

    # 🔴 MAY B CON CUONG CHE TRAN DEM ⇒ A VA B LECH NHAU, PHAI DO.
    #    A da go `max_images` (C4, 28/09). Neu B van chan o anh thu 5 thi khach
    #    doc catalog cua A, gui 10 anh, va an 400 ma KHONG co cho nao bao truoc —
    #    dung cai benh tep nay sinh ra de chan, chi doi chieu.
    assert "max_images" not in that, (
        f"may B van cuong che tran DEM ({that.get('max_images')} anh) trong khi "
        f"may A da go no. HAI MAY PHAI DEPLOY CUNG NHAU: chay "
        f"`llm_gateway/deploy/deploy.ps1` cho may B truoc khi gop nhanh nay vao "
        f"`main`. Do o day la DUNG, khong phai mot phep kiem hong.")
    for k, mong in (("image_min_tokens", TOKEN_ANH_TOI_THIEU),
                    ("image_max_tokens", TOKEN_ANH_TOI_DA)):
        if k in that:
            assert int(that[k]) == mong, (
                f"may B khai {k}={that[k]} nhung may A dat cho theo {mong} — "
                f"hai ben dat cho bang hai so khac nhau")
    if "max_image_bytes" in that:
        assert int(that["max_image_bytes"]) == ANH_BYTE_TOI_DA, (
            f"may B cuong che {that['max_image_bytes']} byte nhung ta cong bo "
            f"{ANH_BYTE_TOI_DA}")


# ── Gate CAP moi truong cho phep doi chieu tren (do ton dong L3 16-19/09) ────

def _nap():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import moi_truong_may_b as m
    return m


def _ssh_gia(stdout: str, ma: int = 0):
    goi: list = []

    def chay(argv, **kw):
        import subprocess
        goi.append(argv)
        return subprocess.CompletedProcess(argv, ma, stdout=stdout, stderr="")
    return chay, goi


def test_nap_env_may_b_dat_ca_hai_bien_va_KHONG_lo_token(tmp_path):
    m = _nap()
    khoa = tmp_path / "nexus_b"
    khoa.write_text("x")
    chay, goi = _ssh_gia("LTT_LLM_TOKEN=bi-mat-123\r\n")
    env: dict = {}
    dong = m.nap_env_may_b(env, chay=chay, khoa=khoa)
    assert env == {"LTT_LLM_TOKEN": "bi-mat-123", "LTT_LLM_BASE_URL": m.URL_CONG_LLM_B}
    assert "bi-mat-123" not in dong and dong.isascii()
    assert "BatchMode=yes" in goi[0] and m.MAY_B in goi[0]


def test_nap_env_may_b_khong_hoi_duoc_thi_KHONG_dat_gi(tmp_path):
    """Không nới phép kiểm: không có token ⇒ env nguyên vẹn ⇒ test_BAN_SAO vẫn ĐỎ."""
    m = _nap()
    env: dict = {}
    assert "khong co khoa" in m.nap_env_may_b(env, khoa=tmp_path / "vang")
    khoa = tmp_path / "nexus_b"
    khoa.write_text("x")
    chay, _ = _ssh_gia("", ma=255)
    assert "DO" in m.nap_env_may_b(env, chay=chay, khoa=khoa)
    assert env == {}


def test_nap_env_may_b_giu_bien_da_dat_san(tmp_path):
    m = _nap()
    chay, goi = _ssh_gia("LTT_LLM_TOKEN=khac\n")
    env = {"LTT_LLM_BASE_URL": "http://tu-cap:1", "LTT_LLM_TOKEN": "tu-cap"}
    m.nap_env_may_b(env, chay=chay, khoa=tmp_path / "nexus_b")
    assert env == {"LTT_LLM_BASE_URL": "http://tu-cap:1", "LTT_LLM_TOKEN": "tu-cap"} and goi == []


def test_gate_nap_moi_truong_KHI_VA_CHI_KHI_luot_co_bo_test(monkeypatch):
    """Hành vi, không phải hình dạng mã: gate gọi bộ nạp đúng lúc có `bo test`."""
    m = _nap()
    import gate
    goi: list = []
    monkeypatch.setattr(m, "nap_env_may_b", lambda env: (goi.append(env), "ok")[1])
    env: dict = {}
    assert gate._nap_moi_truong_test([gate.Step("ruff", ["x"], ".")], env) == ""
    assert goi == []
    assert gate._nap_moi_truong_test([gate.Step("bo test (song song)", ["x"], ".")], env) == "ok"
    assert goi == [env]
