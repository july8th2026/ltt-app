"""ASV V6 pha 16 — Subtitle Studio: tinh chinh kieu chu tren nen preset.

🔑 **Ba menh de, va menh de thu hai la ly do ca tep nay ton tai:**

  1. Mien gia tri duoc duyet bang **chinh mo hinh cua app chu**, khong bang mot
     ban sao. Chot bang cach doi chieu tung con so o `luoc_do_tinh_chinh()` voi
     rang buoc that trong `SubtitleStyleConfig`.

  2. 🔴 **Che do nhan manh cua preset PHAI toi duoc tep `.ass`.**
     `style_registry` giu no o HAI cho — `FullStylePreset.highlight_mode` va
     `SubtitleStyleConfig.highlight_mode` — va do ngay 11/09: **7 trong 9**
     preset khai o cap preset, con ca chin deu co `config.highlight_mode ==
     "none"`. Doc cai thu hai (cach tu nhien nhat, vi moi truong khac deu o do)
     lam kieu ten `word_emphasis` khong nhan manh mot tu nao — khong loi nao
     bao, tep `.ass` van hop le. Dung hinh dang **tinh nang khong ton tai**.

  3. Tinh chinh phai co tac dung tren DAU RA, khong chi nam trong ho so.

⭐ Moi bai o day chot mot menh de DUONG va do o tep DA GHI, khong dung lai o
   doi tuong Python — `du-lieu-tu-dung-khong-bao-dam-ket-qua`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import che_do_render as cdr, phu_de

SU_KIEN = [
    {"start": 0.0, "end": 2.0, "text": "Mot hai ba bon nam sau bay tam chin",
     "display_text": "Mot hai ba bon nam sau bay tam chin", "line_count": 1,
     "scene_id": "s1", "index": 0},
]


def _ho_so(**kw):
    return phu_de.chuan_hoa({"che_do": "tu_chon", **kw})


def _ass(ho_so, tmp_path, **kich) -> str:
    d = phu_de.viet_tep_ass(ho_so, SU_KIEN, tmp_path,
                            rong=kich.get("rong", 1920),
                            cao=kich.get("cao", 1080))
    assert d, "khong sinh duoc tep .ass"
    return Path(d).read_text("utf-8")


def _dong(van: str, dau: str) -> str:
    ds = [d for d in van.splitlines() if d.startswith(dau)]
    assert ds, f"khong co dong {dau!r} trong tep"
    return ds[0]


# ══ 1. MIEN GIA TRI DEN TU MO HINH ══════════════════════════════════════════

def test_moi_truong_mo_deu_co_that_trong_mo_hinh():
    """⛔ Mot ten go sai trong `TRUONG_MO` se lam ca bang tinh chinh im lang bo
       qua mot o — khong loi nao bao, o do chi khong hien.
    """
    from apps.autosubvideo.schemas import SubtitleStyleConfig

    thieu = [t for t in phu_de.TRUONG_MO
             if t not in SubtitleStyleConfig.model_fields]
    assert not thieu, thieu


def test_mien_so_trong_luoc_do_KHOP_rang_buoc_that():
    """🔑 Day la bai chot menh de *"khong co ban sao nao de troi"*.

    Neu ai do go `min`/`max` vao template hay vao `luoc_do_tinh_chinh`, hai con
    so se lech ngay lan dau app chu doi mot rang buoc — va lech im lang: giao
    dien cho keo toi 200 trong khi may chu tu choi o 120.
    """
    from apps.autosubvideo.schemas import SubtitleStyleConfig

    do_duoc = 0
    for muc in phu_de.luoc_do_tinh_chinh():
        if muc["dang"] != "so":
            continue
        f = SubtitleStyleConfig.model_fields[muc["ten"]]
        that = {}
        for m in f.metadata:
            for canh in ("ge", "le"):
                if hasattr(m, canh):
                    that[canh] = getattr(m, canh)
        if "ge" in that:
            assert muc["nho_nhat"] == that["ge"], muc["ten"]
            do_duoc += 1
        if "le" in that:
            assert muc["lon_nhat"] == that["le"], muc["ten"]
            do_duoc += 1
    assert do_duoc >= 10, (
        f"chi doi chieu duoc {do_duoc} rang buoc — bai kiem dang xanh-rong")


def test_luoc_do_phan_loai_dung_dang():
    theo_ten = {m["ten"]: m for m in phu_de.luoc_do_tinh_chinh()}
    assert theo_ten["bold"]["dang"] == "co_khong"
    assert theo_ten["font_size"]["dang"] == "so"
    assert theo_ten["font_color"]["dang"] == "mau"
    assert theo_ten["animation"]["dang"] == "chon"
    # `highlight_mode` khai mien bang `pattern`, khong bang `Literal` — hai
    # duong khai khac nhau phai ra cung mot ket qua o giao dien.
    assert theo_ten["highlight_mode"]["dang"] == "chon"
    assert "word" in theo_ten["highlight_mode"]["chon"]


@pytest.mark.parametrize("tho,cum", [
    ({"font_size": 500}, "font_size"),
    ({"font_color": "do"}, "font_color"),
    ({"bg_opacity": "rat mo"}, "bg_opacity"),
    ({"alignment": 99}, "alignment"),
])
def test_gia_tri_ngoai_mien_bi_CHAN_kem_ten_truong(tho, cum):
    with pytest.raises(phu_de.PhuDeLoi) as e:
        phu_de.chuan_hoa_tinh_chinh(tho, kieu="default")
    assert cum in str(e.value), str(e.value)


def test_go_sai_TEN_bi_chan():
    """`extra="forbid"` cua mo hinh bat ca loi go sai ten — thu ma mot vong
    `for` tu viet khong bao gio bat duoc, vi no chi nhin nhung ten no biet.
    """
    with pytest.raises(phu_de.PhuDeLoi):
        phu_de.chuan_hoa_tinh_chinh({"font_sizee": 60}, kieu="default")


def test_truong_KHONG_MO_bi_chan_kem_cau_khac():
    """⭐ Hai tinh huong, hai cau tra loi: mot ten khong ton tai va mot ten CO Y
       khong mo la hai viec khac nhau.
    """
    with pytest.raises(phu_de.PhuDeLoi) as e:
        phu_de.chuan_hoa_tinh_chinh({"italic": True}, kieu="default")
    assert "italic" in str(e.value)


def test_tinh_chinh_rong_thi_KHONG_ghi_khoa():
    """⛔ Cung luat `KHOA_THUA`: khong doi gi thi khong ghi gi."""
    assert phu_de.chuan_hoa_tinh_chinh({}, kieu="default") == {}
    assert phu_de.chuan_hoa_tinh_chinh(None, kieu="default") == {}
    assert "tinh_chinh" not in _ho_so(kieu="default")


def test_chi_srt_thi_KHONG_mang_tinh_chinh():
    """Mot `.srt` khong mang kieu chu nao, nen no khong mang tinh chinh nao."""
    ho = phu_de.chuan_hoa({"che_do": "tat", "xuat_srt": True,
                           "tinh_chinh": {"font_size": 96}})
    assert ho is not None and "tinh_chinh" not in ho


# ══ 2. NHAN MANH CUA PRESET PHAI TOI DUOC TEP ═══════════════════════════════

def test_preset_khai_nhan_manh_o_CAP_PRESET_chu_khong_o_config():
    """🔴 Doi chung cho ca nhom bai duoi.

    Neu mot ngay nao do `style_registry` chuyen nhan manh xuong `config`, bai
    nay DO — va do la luc bo bai duoi tro nen thua. Khong co no thi
    `test_nhan_manh_cua_preset_TOI_DUOC_tep_ass` co the xanh vi mot ly do khac
    han voi ly do no duoc viet ra.
    """
    from apps.autosubvideo.style_registry import list_presets

    ds = list(list_presets())
    khai_cap_preset = [p.id for p in ds if p.highlight_mode not in ("", "none")]
    khai_cap_config = [p.id for p in ds
                       if p.config.highlight_mode not in ("", "none")]
    assert len(khai_cap_preset) >= 5, khai_cap_preset
    assert not khai_cap_config, (
        "nhan manh nay da nam o `config` — bo `nhan_manh()` di, no khong con "
        "giai quyet gi")


@pytest.mark.parametrize("kieu", ["word_emphasis", "tiktok_bold", "ltt_brand",
                                  "meme_punch", "kids_color"])
def test_nhan_manh_cua_preset_TOI_DUOC_tep_ass(kieu, tmp_path):
    """🔴 Bai quan trong nhat cua tep nay — no chot mot **false feature**.

    Doc `config.highlight_mode` (cach tu nhien nhat) cho ra `none` o ca chin
    preset, tuc kieu ten `word_emphasis` khong nhan manh mot tu nao. Tep `.ass`
    van hop le, khong loi nao bao.
    """
    che_do, _mau = phu_de.nhan_manh(_ho_so(kieu=kieu))
    assert che_do != "none", kieu
    van = _ass(_ho_so(kieu=kieu), tmp_path)
    the = _dong(van, "Dialogue").split(",,", 1)[1]
    assert chr(92) in the, (
        f"preset {kieu} khai nhan manh {che_do!r} nhung dong Dialogue khong "
        f"mang mot the ASS nao: {the!r}")


@pytest.mark.parametrize("kieu", ["default", "cinematic"])
def test_preset_KHONG_khai_nhan_manh_thi_khong_them_the(kieu, tmp_path):
    """⭐ Doi chung: neu MOI preset deu ra the thi bai tren khong do duoc gi."""
    assert phu_de.nhan_manh(_ho_so(kieu=kieu))[0] == "none"
    the = _dong(_ass(_ho_so(kieu=kieu), tmp_path), "Dialogue").split(",,", 1)[1]
    assert chr(92) not in the, the


def test_tinh_chinh_DE_LEN_duoc_nhan_manh_cua_preset():
    ho = _ho_so(kieu="word_emphasis", tinh_chinh={"highlight_mode": "none"})
    assert phu_de.nhan_manh(ho)[0] == "none"
    ho2 = _ho_so(kieu="default", tinh_chinh={"highlight_mode": "word"})
    assert phu_de.nhan_manh(ho2)[0] == "word"


# ══ 3. TINH CHINH CO TAC DUNG TREN DAU RA ═══════════════════════════════════

def test_tinh_chinh_DOI_dong_Style_trong_tep(tmp_path):
    a = _ass(_ho_so(kieu="default"), tmp_path / "a")
    b = _ass(_ho_so(kieu="default",
                    tinh_chinh={"font_size": 96, "outline_width": 6,
                                "alignment": 8}), tmp_path / "b")
    sa, sb = _dong(a, "Style:"), _dong(b, "Style:")
    assert sa != sb
    assert ",96," in sb and ",48," in sa, (sa, sb)


def test_doi_mau_chu_DOI_ma_mau_ASS(tmp_path):
    """⚠️ ASS dung **BGR**, khong phai RGB. Mot phep doi mau viet nham thu tu
       cho ra do thanh xanh — va no khong bao loi, chi sai mau.
    """
    van = _ass(_ho_so(kieu="default", tinh_chinh={"font_color": "#FF0000"}),
               tmp_path)
    assert "&H000000FF" in _dong(van, "Style:"), _dong(van, "Style:")


def test_chuyen_dong_DI_VAO_dong_Dialogue(tmp_path):
    van = _ass(_ho_so(kieu="default", tinh_chinh={"animation": "pop"}),
               tmp_path)
    assert "fscx70" in _dong(van, "Dialogue")


def test_doi_tinh_chinh_thi_VAN_TAY_doi():
    """🔑 Thieu buoc nay thi hai cau hinh khac nhau dung chung mot chuoi bam, va
       lan thu hai duoc phuc vu tu cache — tuc khach doi cai gi cung khong thay.
    """
    chung = dict(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                 khoang=[(0.0, 5.0)])
    a = cdr.van_tay_che_do(**chung, phu_de=_ho_so(kieu="default"))
    b = cdr.van_tay_che_do(**chung, phu_de=_ho_so(
        kieu="default", tinh_chinh={"font_size": 96}))
    c = cdr.van_tay_che_do(**chung, phu_de=_ho_so(
        kieu="default", tinh_chinh={"font_size": 97}))
    assert len({a, b, c}) == 3


def test_cau_hinh_kieu_khong_tinh_chinh_thi_TRA_NGUYEN_preset():
    """⭐ Khong tinh chinh thi khong dung lai mot doi tuong moi: ban dung cu va
       ban dung moi cua cung mot preset phai cho ra cung mot ket qua.
    """
    from apps.autosubvideo.style_registry import get_config

    assert phu_de.cau_hinh_kieu(_ho_so(kieu="cinematic")) == \
        get_config("cinematic")


# ══ 4. GIAO DIEN ════════════════════════════════════════════════════════════

def test_gia_tri_khoi_diem_la_CUA_PRESET_khong_phai_cua_MO_HINH():
    """🔑 Hai thu nay khac nhau, va nham lan chung lam moi o khach cham vao tro
       thanh mot "tinh chinh" du ho khong doi y gi.
    """
    from apps.autosubvideo.schemas import SubtitleStyleConfig

    kc = phu_de.cho_giao_dien()["kieu_cau_hinh"]
    assert set(kc) == set(phu_de.kieu_hop_le())
    mac_dinh_mo_hinh = SubtitleStyleConfig()
    khac = [k for k, v in kc.items()
            if any(v[t] != getattr(mac_dinh_mo_hinh, t)
                   for t in phu_de.TRUONG_MO)]
    assert len(khac) >= 5, (
        "gan het preset trung mac dinh mo hinh — bang `kieu_cau_hinh` khong do "
        "duoc gi")


def test_moi_preset_phat_du_18_truong_mo():
    kc = phu_de.cho_giao_dien()["kieu_cau_hinh"]
    for k, v in kc.items():
        assert set(v) == set(phu_de.TRUONG_MO), k


def test_template_KHONG_go_mien_gia_tri_bang_tay():
    """⛔ Mot `min="12"` go tay trong HTML la mot ban sao se troi. Giao dien
       phai lay tu `luoc_do_tinh_chinh`, va bai nay chot dieu do bang CO HOC.
    """
    goc = Path(__file__).resolve().parents[1]
    html = (goc / "apps/auto_scan_video/templates/asv_trang_chinh.html"
            ).read_text("utf-8")
    i = html.index('id="asv-phu-de-tinh-chinh"')
    khoi = html[i:html.index("</details>", i)]
    import re
    go_tay = re.findall(r'(?:min|max)="(\d+)"', khoi)
    assert not go_tay, f"mien gia tri go tay trong template: {go_tay}"
    assert 'min="{{ o.nho_nhat }}"' in khoi and 'max="{{ o.lon_nhat }}"' in khoi


def test_bang_tinh_chinh_MAC_DINH_bi_an():
    """Mac dinh la khong dot phu de, nen bang tinh chinh phai an — `hidden` o
    ngay trong the, khong cho JS bat kip.
    """
    goc = Path(__file__).resolve().parents[1]
    html = (goc / "apps/auto_scan_video/templates/asv_trang_chinh.html"
            ).read_text("utf-8")
    i = html.index('id="asv-phu-de-tinh-chinh"')
    assert "hidden" in html[i:html.index(">", i)]
