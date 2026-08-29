"""Hop dong dieu huong khu quan tri — chot bang test, khong bang loi khuyen.

Truoc dot `admin_mvp_v3` khu quan tri co BA danh sach dieu huong song song cho
cung mot cay (`server/admin.py:_ADM_NAV`, `server/admin_api.py:NAV`, va nam the
<a> viet tay trong `server/admin_templates/sqladmin/base.html`), 25 muc phang o
thanh ben, va khong co tran nao ngan no phinh tiep. Tep nay la thu ngan dieu do
quay lai.

Khuon lay tu `test_303` cua khu `/developers` — cung mot van de, da giai mot lan.

Hop dong: docs/admin_mvp_v3/03_IA_FREEZE.md
          docs/admin_mvp_v3/04_EXTENSION_CONTRACT.md
          docs/admin_mvp_v3/06b_SO_DANG_KY_NOI_DUNG_CAM.md
"""

from __future__ import annotations

import pathlib
import re

import pytest

from server.routes.admin import _chung

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── Cau truc cay ─────────────────────────────────────────────────────────────

def test_moi_khoa_chi_khai_mot_lan():
    khoa = [k for k, _, _ in _chung.SECTIONS]
    assert len(khoa) == len(set(khoa)), "khoa trung trong SECTIONS"


def test_tran_muc_cha():
    """SAU muc cha, khong hon.

    Con so nay la mot QUYET DINH (03_IA_FREEZE §1 L3), khong phai mot gioi han
    ky thuat. Muon vuot thi sua tai lieu do truoc, roi moi sua so o day — doi
    theo chieu nguoc lai la cach 25 muc phang da hinh thanh.
    """
    muc_cha = [k for nhom in _chung.NHOM_NAV for k in nhom]
    assert len(muc_cha) == len(set(muc_cha)), "muc cha trung"
    assert len(muc_cha) <= _chung.TRAN_MUC_CHA, muc_cha


def test_tran_muc_con_moi_mien():
    for cha, con in _chung.MUC_CON.items():
        assert len(con) <= _chung.TRAN_MUC_CON, (cha, len(con))


def test_moi_tham_chieu_tro_vao_mot_khoa_da_khai():
    """Khong duoc tro vao khoa la.

    Mot khoa la khong lam sap trang — no lam THANH BEN KHONG SANG GI CA, va
    nguoi dang xu su co khong biet minh dang dung o dau. Kieu hong im lang do
    phai bi bat o cong, khong phai luc chay.
    """
    khoa = {k for k, _, _ in _chung.SECTIONS}
    for con, cha in _chung.CHA_CUA.items():
        assert con in khoa, f"CHA_CUA: khoa con la {con!r}"
        assert cha in khoa, f"CHA_CUA: khoa cha la {cha!r}"
    for cha, muc in _chung.MUC_CON.items():
        assert cha in khoa, f"MUC_CON: khoa cha la {cha!r}"
        for k, _ in muc:
            assert k in khoa, f"MUC_CON[{cha}]: khoa la {k!r}"
    for anh, tab in _chung.TAB_CUA.items():
        assert anh in khoa, f"TAB_CUA: khoa la {anh!r}"
        for k, _ in tab:
            assert k in khoa, f"TAB_CUA[{anh}]: khoa la {k!r}"


def test_khong_khoa_nao_mo_coi():
    """Moi trang phai co duong ve mot muc cha.

    Ha mot trang khoi thanh ben la hop le (12 route hom nay da song ngoai nav);
    de no khong thuoc nhanh nao thi khong.
    """
    khoa = {k for k, _, _ in _chung.SECTIONS}
    muc_cha = {k for nhom in _chung.NHOM_NAV for k in nhom}
    mo_coi = sorted(khoa - muc_cha - set(_chung.CHA_CUA))
    assert not mo_coi, mo_coi


@pytest.mark.parametrize("khoa", [k for k, _, _ in _chung.SECTIONS])
def test_moi_trang_dung_duoc_dieu_huong(khoa):
    nav = _chung.dieu_huong(khoa)
    sang = [m for m in nav["thanh_ben"] if m["active"]]
    assert len(sang) == 1, (khoa, [m["nhan"] for m in sang])


# ── Mot nguon duy nhat ───────────────────────────────────────────────────────

def test_khong_con_danh_sach_dieu_huong_thu_hai():
    """`_ADM_NAV` va `admin_api.NAV` phai da bien mat.

    Chung khong bi bo sung, chung bi THAY. De lai mot ban thu hai la de lai dung
    thu da tao ra van de: ban thu hai luon la ban bi quen khi them trang.
    """
    for ten in ("server/admin.py", "server/admin_api.py"):
        src = (GOC / ten).read_text(encoding="utf-8")
        assert not re.search(r"^_ADM_NAV\s*=", src, re.M), ten
        assert not re.search(r"^NAV\s*=", src, re.M), ten


def test_vo_sqladmin_khong_con_dieu_huong_viet_tay():
    """Nam the <a> hardcode trong vo SQLAdmin la danh sach thu BA."""
    vo = (GOC / "server/admin_templates/sqladmin/base.html").read_text(encoding="utf-8")
    thanh = vo[vo.index('class="ltt-adminbar"'):vo.index("</nav>")]
    assert "adm_nav" in thanh, "thanh SQLAdmin phai lay tu nguon chung"
    # Chi con hai lien ket viet tay hop le: thuong hieu va duong ve nen tang.
    assert thanh.count("<a ") <= 2, thanh


def test_vo_sqladmin_cache_bust_css():
    """Doi `ltt.css` ma URL khong doi thi Cloudflare phuc vu ban cu toi het TTL.

    Loi nay da tung xay ra that o du an nay (CLAUDE.md quy tac 6).
    """
    vo = (GOC / "server/admin_templates/sqladmin/base.html").read_text(encoding="utf-8")
    assert "/static/ltt.css?v={{ asset_ver }}" in vo


# ── Su that du lieu ──────────────────────────────────────────────────────────

def _mau_cam() -> list[tuple[str, str]]:
    """Doc bang §2 cua so dang ky noi dung cam nhu DU LIEU.

    Cung khuon voi `test_212` doc `APP_API_COVERAGE_FINAL.md`. Them mot dong vao
    tai lieu do la them mot phep kiem — khong phai sua tep nay.
    """
    md = (GOC / "docs/admin_mvp_v3/06b_SO_DANG_KY_NOI_DUNG_CAM.md").read_text(
        encoding="utf-8")
    ra = []
    for dong in md.splitlines():
        if not dong.startswith("| `"):
            continue
        o = [c.strip() for c in dong.strip("|").split("|")]
        if len(o) < 3 or o[1] != "AUTO":
            continue
        mau = o[0].strip("`").replace("*", "")
        if mau:
            ra.append((mau, o[2]))
    return ra


def test_so_dang_ky_doc_duoc():
    mau = _mau_cam()
    assert len(mau) >= 25, f"chi doc duoc {len(mau)} mau AUTO — bang co con dung dinh dang?"


def test_giao_dien_quan_tri_khong_chua_noi_dung_khong_co_authority():
    """Bo prompt cam 'fake metric' bang LOI, o 21 cho, va khong co co che nao.

    Va thu de lot nhat trong bo anh khong trong giong mot metric: no la cot
    "Goi dich vu: Starter / Pro / Business" o ba trang khac nhau, cho mot nen
    tang ban CREDIT chu khong ban thue bao. Mot dong van xuoi khong chan duoc
    dieu do; phep kiem nay thi co.
    """
    can_quet = [GOC / "server/templates/admin"]
    tep = [p for goc in can_quet if goc.exists()
           for p in goc.rglob("*.html")]
    assert tep, "khong tim thay template quan tri nao de quet"

    vi_pham = []
    for mau, ly_do in _mau_cam():
        for p in tep:
            noi_dung = p.read_text(encoding="utf-8")
            # Bo qua chu thich Jinja: tai lieu hoa VI SAO mot thu bi cam la
            # dung viec, khong phai vi pham.
            noi_dung = re.sub(r"\{#.*?#\}", "", noi_dung, flags=re.S)
            if mau.lower() in noi_dung.lower():
                vi_pham.append(f"{p.relative_to(GOC)}: {mau!r} — {ly_do}")
    assert not vi_pham, "\n".join(vi_pham)
