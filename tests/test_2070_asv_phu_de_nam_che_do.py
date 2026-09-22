"""asv-final lan phu-de — NAM che do phu de, vi tri tu dong, xem truoc chung ho so.

🔑 Menh de tep nay chot (deu DUONG — khang dinh mot hanh vi, khong do vang mat):

  1. Nam che do (tat/tu_dong/nguon/dich/tu_chon) cho NAM tep `.ass` khac nhau
     tu CUNG mot tai lieu — `nguon` doc `goc`, `dich` doc `chu`, `tu_dong` doi
     vi tri, `tu_chon` doi kieu.
  2. `tu_dong` DOC vung `danh_dau_phu_de` — nang luc truoc day co ma khong ai
     doc — va dat chu de len dai da che (hoac tren dai chua che).
  3. Xem truoc di qua CHINH `tu_form` + `viet_tep_ass` + `loc_cat_noi` cua nop
     that / render; khac biet duy nhat la dau vao.

⛔ Khong bai nao chay ffmpeg. Bang chung tung diem anh (xem truoc == render, 0
   diem lech o ca 5 che do) nam o
   `docs/auto_scan_video_final/bang_chung/phu_de/xem_truoc_vs_render.json`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

from apps.auto_scan_video import (che_do_render as cdr, hop_dong_v4 as hd,  # noqa: E402
                                  phu_de, thoi_gian, van_ban)

PRESET_CAT = hd.PRESET_CAT_THONG_MINH
PRESET_GIU = hd.PRESET_GIU_HINH

ZH = ["从屠宰场运送过来的牛肠还带着温热", "清洗牛肠才是最关键的一步", "想要牛肠好吃"]
VI = ["Lòng bò chở từ lò mổ về vẫn còn ấm", "Rửa sạch mới là bước quan trọng nhất",
      "Muốn lòng bò ngon"]
DAI = {"loai": "danh_dau_phu_de", "x0": 0.1, "x1": 0.9, "y0": 0.904, "y1": 0.976}


# ── Tai lieu do CHINH nguoi san xuat sinh ra ────────────────────────────────

@pytest.fixture(scope="module")
def tai_lieu() -> dict:
    ban_ghi = {"ngon_ngu": "zh", "doan": [
        {"ma": f"s{i}", "bat": i * 5.0, "ket": i * 5.0 + 4.0, "chu": z}
        for i, z in enumerate(ZH)]}
    return van_ban.dung(ban_ghi, {f"s{i}": v for i, v in enumerate(VI)},
                        provider="p", model="m")


@pytest.fixture(scope="module")
def ke_hoach(tai_lieu) -> dict:
    kh = thoi_gian.lap_ke_hoach(tai_lieu["muc"], {"s0": 3.0, "s1": 3.0, "s2": 2.0},
                                tong_giay=15.0)
    thoi_gian.kiem(kh)
    return kh


def _ass(ho, ke_hoach, tai_lieu, tmp_path, *, vung=(), rong=864, cao=576) -> str:
    ho = phu_de.chot_o_compose(dict(ho), ke_hoach=ke_hoach, van_ban=tai_lieu,
                               vung=vung)
    d = tmp_path / str(len(list(tmp_path.iterdir())))
    d.mkdir()
    p = phu_de.viet_tep_ass(ho, ho["su_kien"], d, rong=rong, cao=cao)
    return Path(p).read_text(encoding="utf-8-sig") if p else ""


def _style(ass: str) -> list[str]:
    return next(line for line in ass.splitlines()
                if line.startswith("Style: Default")).split(",")


# ══ 1. Nam che do, nam ban ra ═══════════════════════════════════════════════

def test_hang_so_nam_che_do_va_thu_tu():
    assert phu_de.CHE_DO == ("tat", "tu_dong", "nguon", "dich", "tu_chon")
    assert phu_de.CHE_DO_DOT == ("tu_dong", "nguon", "dich", "tu_chon")
    assert [m for m, _t, _d in phu_de.cho_giao_dien()["che_do"]] == list(phu_de.CHE_DO)


@pytest.mark.parametrize("che_do", ["tu_dong", "nguon", "dich", "tu_chon"])
def test_moi_che_do_dot_deu_dot(che_do):
    ho = phu_de.chuan_hoa({"che_do": che_do})
    assert phu_de.co_dot_vao_hinh(ho)


def test_nguon_doc_GOC_dich_doc_CHU(ke_hoach, tai_lieu):
    """🔴 Chu tren hinh cua `nguon` la LOI GOC tu ban ghi, cua `dich` la ban dich —
    cung ma doan, cung moc (khong co truc thoi gian thu hai)."""
    g = phu_de.su_kien_tu_ke_hoach(ke_hoach, tai_lieu, chu="nguon")
    d = phu_de.su_kien_tu_ke_hoach(ke_hoach, tai_lieu, chu="dich")
    assert [e.text for e in g] == ZH
    assert [e.text for e in d] == VI
    assert [(e.start, e.end, e.scene_id) for e in g] == \
        [(e.start, e.end, e.scene_id) for e in d]


@pytest.mark.parametrize("ho,chu", [
    ({"che_do": "tu_dong"}, "dich"), ({"che_do": "dich"}, "dich"),
    ({"che_do": "nguon"}, "nguon"), ({"che_do": "tu_chon"}, "dich"),
    ({"che_do": "tu_chon", "chu": "nguon"}, "nguon"),
    ({"che_do": "tat", "xuat_srt": True, "chu": "nguon"}, "nguon"),
])
def test_chu_cua_moi_che_do(ho, chu):
    assert phu_de.chu_cua(phu_de.chuan_hoa(ho)) == chu


def test_nam_che_do_cho_NAM_tep_ass_khac_nhau(ke_hoach, tai_lieu, tmp_path):
    """Menh de 1 — tren tep DA GHI, khong dung o doi tuong Python."""
    ra = {}
    for tho in ({"che_do": "tu_dong"}, {"che_do": "nguon"}, {"che_do": "dich"},
                {"che_do": "tu_chon", "kieu": "tiktok_bold", "chu": "nguon",
                 "tinh_chinh": {"font_size": 40}}):
        ra[tho["che_do"]] = _ass(phu_de.chuan_hoa(tho), ke_hoach, tai_lieu,
                                 tmp_path, vung=[DAI])
    assert len(set(ra.values())) == 4
    assert all(z in ra["nguon"] for z in ZH[:1])
    assert VI[0] in ra["dich"] and ZH[0] not in ra["dich"]
    # `tiktok_bold` nhan manh `word` -> mot `\kf` cho TUNG chu Han
    assert ZH[2] in re.sub(r"\{\\kf\d+\}", "", ra["tu_chon"])
    assert "{\\kf33}想{\\kf33}要" in ra["tu_chon"]
    # tu_dong vs dich: CUNG chu, KHAC vi tri (margin_v)
    assert VI[0] in ra["tu_dong"]
    assert _style(ra["tu_dong"])[21] != _style(ra["dich"])[21]
    # tat -> khong co .ass nao
    assert _ass(phu_de.chuan_hoa({"che_do": "tat", "xuat_srt": True}),
                ke_hoach, tai_lieu, tmp_path) == ""


def test_chu_chi_nhan_o_tu_chon_va_tat():
    with pytest.raises(phu_de.PhuDeLoi, match="cố định"):
        phu_de.chuan_hoa({"che_do": "dich", "chu": "nguon"})
    with pytest.raises(phu_de.PhuDeLoi, match="Nguồn chữ"):
        phu_de.chuan_hoa({"che_do": "tu_chon", "chu": "tieng_nhat"})
    # `dich` la mac dinh -> giu THUA, khong ghi
    assert "chu" not in phu_de.chuan_hoa({"che_do": "tu_chon", "chu": "dich"})


def test_ha_ve_srt_GIU_nguon_chu():
    """⚠️ Ha `nguon` o preset giu hinh ma quen `chu` = giao `.srt` ban dich cho
    nguoi da chon loi goc."""
    ho = phu_de.ha_ve_srt(phu_de.chuan_hoa({"che_do": "nguon", "xuat_srt": True}))
    assert ho["che_do"] == "tat" and phu_de.chu_cua(ho) == "nguon"
    assert "kieu" not in ho and "tinh_chinh" not in ho


# ══ 2. Vi tri TU DONG ═══════════════════════════════════════════════════════

def test_dai_phu_de_goc_chi_doc_vung_DANH_DAU():
    lam_mo = dict(DAI, loai="lam_mo")
    assert phu_de.dai_phu_de_goc([lam_mo]) is None
    assert phu_de.dai_phu_de_goc([lam_mo, DAI]) == {"y0": 0.904, "y1": 0.976,
                                                   "da_che": True}


def test_tu_dong_day_chu_TRUNG_day_dai_da_che(ke_hoach, tai_lieu, tmp_path):
    ass = _ass(phu_de.chuan_hoa({"che_do": "tu_dong"}), ke_hoach, tai_lieu,
               tmp_path, vung=[DAI], cao=576)
    st = _style(ass)
    assert st[18] == "2"                                   # alignment day giua
    assert int(st[21]) == round((1 - 0.976) * 576)         # margin_v = 14


def test_tu_dong_dai_CHUA_che_dat_phia_tren():
    ho = {"che_do": "tu_dong", "dai_phu_de_goc": {"y0": 0.76, "y1": 0.80,
                                                  "da_che": False}}
    vt = phu_de.vi_tri_tu_dong(ho, cao=1080)
    assert vt["margin_v"] == round((1 - 0.76 + phu_de.KHOANG_HO_DAI) * 1080)
    # 281 > tran 200 cua mo hinh — van ap duoc (gia tri do he thong tinh)
    assert phu_de.cau_hinh_kieu(ho, cao=1080).margin_v == vt["margin_v"] > 200


def test_tu_dong_KHONG_dai_thi_giu_vi_tri_preset(ke_hoach, tai_lieu, tmp_path):
    a = _ass(phu_de.chuan_hoa({"che_do": "tu_dong"}), ke_hoach, tai_lieu, tmp_path)
    b = _ass(phu_de.chuan_hoa({"che_do": "dich"}), ke_hoach, tai_lieu, tmp_path)
    assert a == b


def test_che_do_KHAC_tu_dong_khong_doi_vi_tri_du_co_dai():
    ho = {"che_do": "dich", "dai_phu_de_goc": {"y0": 0.9, "y1": 0.97, "da_che": True}}
    assert phu_de.vi_tri_tu_dong(ho, cao=576) == {}


def test_tinh_chinh_cua_khach_THANG_vi_tri_tu_dong():
    ho = {"che_do": "tu_dong", "tinh_chinh": {"margin_v": 77},
          "dai_phu_de_goc": {"y0": 0.9, "y1": 0.97, "da_che": True}}
    cfg = phu_de.cau_hinh_kieu(ho, cao=576)
    assert cfg.margin_v == 77 and cfg.safe_area_percent == 0


def test_dai_chot_o_COMPOSE_vao_ho_so(ke_hoach, tai_lieu):
    ho = phu_de.chot_o_compose(phu_de.chuan_hoa({"che_do": "tu_dong"}),
                               ke_hoach=ke_hoach, van_ban=tai_lieu, vung=[DAI])
    assert ho["dai_phu_de_goc"]["y1"] == 0.976
    # va no vao van tay render (ho so phu de di nguyen vao `van_tay_che_do`)
    vt = lambda h: cdr.van_tay_che_do(che_do="x", bo_ma_hoa=cdr.LUI_VE,  # noqa: E731
                                      khoang=[(0.0, 1.0)], phu_de=h)
    ho2 = dict(ho, dai_phu_de_goc=dict(ho["dai_phu_de_goc"], y1=0.95))
    assert vt(ho) != vt(ho2)


# ══ 3. Xem truoc: cung cua, cung ho so, cung chuoi loc ══════════════════════

def test_xem_truoc_duyet_Y_HET_nop_that():
    """Cung cau tra loi voi `tu_form` — xem truoc khong co cua duyet rieng."""
    with pytest.raises(phu_de.PhuDeLoi, match="Giữ nguyên"):
        phu_de.xem_truoc_tu_form('{"che_do":"dich"}', anh=b"x", preset=PRESET_GIU)
    with pytest.raises(phu_de.PhuDeLoi, match="Kiểu"):
        phu_de.xem_truoc_tu_form('{"che_do":"tu_chon","kieu":"khong-co"}',
                                 anh=b"x", preset=PRESET_CAT)


@pytest.mark.parametrize("anh", [b"", b"khong phai anh", b"GIF89a" + b"\0" * 40])
def test_xem_truoc_tu_choi_anh_hong(anh):
    with pytest.raises(phu_de.PhuDeLoi, match="Ảnh"):
        phu_de.xem_truoc_tu_form('{"che_do":"dich"}', anh=anh, preset=PRESET_CAT)


def test_xem_truoc_tu_choi_vung_hong():
    with pytest.raises(phu_de.PhuDeLoi, match="Vùng"):
        phu_de.xem_truoc_tu_form('{"che_do":"dich"}', anh=b"x", vung="{hong",
                                 preset=PRESET_CAT)


def test_lenh_xem_truoc_dung_CHINH_loc_cat_noi_va_ss_sau_i(tmp_path):
    vung = [DAI]
    cmds = phu_de.lenh_xem_truoc(ffmpeg="ffmpeg", anh="a.png", duong_ass="x.ass",
                                 vung=vung, duong_tam="t.mkv", duong_ra="r.png")
    chuan, dung = cmds
    assert chuan[chuan.index("-pix_fmt") + 1] == phu_de.DINH_DANG_VAO == "yuv420p"
    loc = dung[dung.index("-filter_complex") + 1]
    assert loc == cdr.loc_cat_noi([(0.0, phu_de.XEM_TRUOC_GIAY + 0.2)], vung=vung,
                                  duong_ass="x.ass")
    assert dung.index("-ss") > dung.index("-i")      # tim o dau RA, giu moc that


@pytest.mark.parametrize("ho,nguon,dich,cau", [
    ({"che_do": "nguon"}, "zh", "vi", "zh"), ({"che_do": "nguon"}, "auto", "vi", "zh"),
    ({"che_do": "nguon"}, "en", "vi", "en"), ({"che_do": "dich"}, "zh", "en", "en"),
    ({"che_do": "tu_dong"}, "zh", "", "vi"),
])
def test_cau_mau_theo_nguon_chu_va_cap_ngon_ngu(ho, nguon, dich, cau):
    assert phu_de.cau_mau(phu_de.chuan_hoa(ho), nguon=nguon, dich=dich) == \
        phu_de.CAU_MAU[cau]


# ══ 4. Cua HTTP va giao dien ════════════════════════════════════════════════

def test_route_xem_truoc_chi_la_mot_loi_goc_va_routes_duoi_tran():
    src = (GOC / "apps/auto_scan_video/routes.py").read_text(encoding="utf-8")
    assert len(src.splitlines()) <= 900
    m = re.search(r'@router.post\("/phu-de/xem-truoc"\)(.*?)\n@router', src, re.S)
    assert m and "phu_de_mod.xem_truoc_tu_form(" in m.group(1)
    assert "verify_csrf_token" in m.group(1)


def test_giao_dien_co_o_nguon_chu_goi_y_va_xem_truoc():
    html = (GOC / "apps/auto_scan_video/templates/asv_trang_chinh.html").read_text(
        encoding="utf-8")
    for id_ in ("asv-phu-de-chu", "asv-phu-de-goi-y", "asv-phu-de-xem-nut",
                "asv-phu-de-xem-anh"):
        assert f'id="{id_}"' in html
    assert "/phu-de/xem-truoc" in html
    js = (GOC / "server/static/asv/phu_de.js").read_text(encoding="utf-8")
    assert "danh_dau_phu_de" in js and "data-duong" in js
