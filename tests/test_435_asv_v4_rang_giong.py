"""Auto Scan Video V4 — RANG GIONG (VoiceBinding), pha 09.

**§1 `AUTO_MATCH` khong duoc thoai hoa thanh "giong mac dinh"** — `ADR-V4-001`
     D-V4-04 cam bang ten, va V2 da mac dung loi ay (`routes.py:135`
     `giong_id: str = Form("")` roi de trong thi lay mac dinh). Mot gia tri mac
     dinh **khong doc gi tu video ca**.

**§2 quyen so huu do LTT VOICE kiem** — `features.giai_giong` da loc `owner_id`,
     da xu ly kho giong dung chung, da bo giong het `active`. Viet lai ba phep do
     o ASV la ba cho de lam sai, va cai thu nhat lam sai thi hau qua la mot khach
     doc video bang **giong nhan ban cua nguoi khac**.

**§3 ranh gioi** — ASV so huu CHINH SACH chon giong; LTT Voice so huu giong,
     tong hop, GPU, chuan hoa. Tep `rang_giong.py` khong sinh mot mili-giay
     tieng nao.

**§4 hoan lai, khong chon tam** — mot giong tam se lam pha 14 (chuyen loi thoai)
     sinh ra ban chuyen phai lam lai, vi do dai cau phu thuoc toc do doc cua
     giong THAT.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.auto_scan_video import rang_giong as rg

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"


# ══════════════════════════════════════════════════════════════════════════════
#  §1  AUTO_MATCH khong duoc thanh "giong mac dinh"
# ══════════════════════════════════════════════════════════════════════════════

def test_AUTO_MATCH_chua_co_ho_so_thi_CHUA_RANG_chu_khong_lay_mac_dinh():
    """🔴 Ca diem cua pha 09.

    `CHUA_RANG` la mot ket qua **hop le** — khong phai that bai, va cung khong
    phai mot giong. Tang tren hoi lai sau khi pha 11 dung xong ho so.
    """
    kq = rg.rang(None, owner_id="u1", yeu_cau=rg.YeuCau(che_do="AUTO_MATCH"))
    assert kq.trang_thai == rg.CHUA_RANG
    assert kq.giong_id == "", "chua rang ma da co giong la da lay mac dinh"
    assert not kq.da_chot


def test_doc_giong_tu_rang_buoc_CHUA_CHOT_thi_NEM(  ):
    """⛔ Mot ham tra ve chuoi rong o day se cho ra mot lan tong hop bang giong
    mac dinh **ma khong ai bam nut** — dung ket qua ca thiet ke nay de tranh."""
    kq = rg.rang(None, owner_id="u1", yeu_cau=rg.YeuCau(che_do="AUTO_MATCH"))
    with pytest.raises(rg.ChuaRangError):
        kq.ma_giong()


def test_USER_SELECTED_de_TRONG_bi_tu_choi_ngay_tu_YEU_CAU():
    """V2 khai `giong_id: str = Form("")`. Chan o ngay hinh dang yeu cau thi
    khong lop nao phia sau phai nho kiem lai."""
    with pytest.raises(rg.RangGiongError):
        rg.YeuCau(che_do="USER_SELECTED")


def test_KHONG_mat_nao_rang_buoc_thi_van_CHUA_RANG():
    """⛔ Khong mat nao rang buoc thi `loc()` tra ve CA catalog, va "lay cai dau
    tien" cua ca catalog chinh la giong mac dinh doi ten."""
    yc = rg.YeuCau(che_do="AUTO_MATCH", dac_diem=rg.DacDiemMongMuon())
    assert rg.rang(None, owner_id="u1", yeu_cau=yc).trang_thai == rg.CHUA_RANG


def test_khong_ung_vien_nao_khop_thi_CHUA_RANG_chu_khong_lay_dai():
    """⚠️ Noi long dieu kien la viec cua tang tren — no biet mat nao dang gia
    nhat, con o day ta khong biet."""
    yc = rg.YeuCau(che_do="AUTO_MATCH",
                   dac_diem=rg.DacDiemMongMuon(gioi="khong_ton_tai"))
    kq = rg.rang(None, owner_id="u1", yeu_cau=yc)
    assert kq.trang_thai == rg.CHUA_RANG
    assert "khong giong nao khop" in str(kq.can_cu.get("ly_do", ""))


def test_co_dac_diem_thi_CHOT_duoc_va_ghi_lai_CAN_CU():
    yc = rg.YeuCau(che_do="AUTO_MATCH",
                   dac_diem=rg.DacDiemMongMuon(gioi="nu", vung="bac"))
    kq = rg.rang(None, owner_id="u1", yeu_cau=yc)
    assert kq.da_chot and kq.nguon == rg.NGUON_TU_KHOP
    assert kq.ma_giong()
    # Can cu phai du de mot nguoi ho tro tra loi "vi sao lai giong nay".
    assert kq.can_cu["so_ung_vien"] >= 1
    assert kq.can_cu["dac_diem"]["gioi"] == "nu"


def test_cung_dac_diem_thi_ra_CUNG_mot_giong():
    """Van tay phu thuoc giong; mot lua chon nhay lam cache truot vo co."""
    yc = rg.YeuCau(che_do="AUTO_MATCH",
                   dac_diem=rg.DacDiemMongMuon(gioi="nam", phong_cach="tin_tuc"))
    a = rg.rang(None, owner_id="u1", yeu_cau=yc)
    b = rg.rang(None, owner_id="u1", yeu_cau=yc)
    assert a.giong_id == b.giong_id


def test_dieu_phoi_biet_luc_nao_phai_DOI_ho_so():
    """Mot lan chay `AUTO_MATCH` khong duoc di toi buoc chuyen loi thoai truoc
    khi giong da chot — do dai cau phu thuoc toc do doc cua giong that."""
    assert rg.can_cho_ho_so(rg.YeuCau(che_do="AUTO_MATCH")) is True
    assert rg.can_cho_ho_so(rg.YeuCau(
        che_do="AUTO_MATCH",
        dac_diem=rg.DacDiemMongMuon(gioi="nu"))) is False
    assert rg.can_cho_ho_so(rg.YeuCau(
        che_do="USER_SELECTED", giong_id="x")) is False


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Quyen so huu — do LTT VOICE kiem, khong phai o day
# ══════════════════════════════════════════════════════════════════════════════

def test_giong_CUA_KHACH_di_qua_ham_kiem_quyen_cua_app_CHU(monkeypatch):
    goi = {}

    def _giai(db, *, owner_id, voice_id="", preset=""):
        goi.update(owner_id=owner_id, voice_id=voice_id)
        return ("ref-b64", "preset-x")

    from apps.auto_scan_video import giong_noi
    monkeypatch.setattr(giong_noi, "giai_giong", _giai)

    kq = rg.rang(None, owner_id="u1",
                 yeu_cau=rg.YeuCau(che_do="USER_SELECTED", giong_id="voice-cua-u1"))
    assert goi == {"owner_id": "u1", "voice_id": "voice-cua-u1"}
    assert kq.da_chot and kq.nguon == rg.NGUON_KHACH_CHON


def test_giong_cua_NGUOI_KHAC_bi_tu_choi(monkeypatch):
    """🔴 Hau qua neu khong kiem: mot khach doc video bang **giong nhan ban cua
    nguoi khac**. Phep kiem quyen o app CHU, va ta de no nem len."""
    def _giai(db, *, owner_id, voice_id="", preset=""):
        raise PermissionError("giong nay khong phai cua ban")

    from apps.auto_scan_video import giong_noi
    monkeypatch.setattr(giong_noi, "giai_giong", _giai)

    with pytest.raises(PermissionError):
        rg.rang(None, owner_id="u-khac",
                yeu_cau=rg.YeuCau(che_do="USER_SELECTED", giong_id="voice-cua-u1"))


def test_giong_MAU_thi_ai_cung_dung_duoc_va_KHONG_goi_kiem_quyen(monkeypatch):
    """Giong mau khong co chu so huu — goi phep kiem quyen cho no la mot luot
    tra CSDL cho mot cau hoi khong ton tai."""
    from apps.ltt_voice import giong_mau

    ma = giong_mau.DANH_SACH[0].ma
    goi = []
    from apps.auto_scan_video import giong_noi
    monkeypatch.setattr(giong_noi, "giai_giong",
                        lambda *a, **k: goi.append(1) or ("", ""))

    kq = rg.rang(None, owner_id="bat_ky",
                 yeu_cau=rg.YeuCau(che_do="USER_SELECTED", giong_id=ma))
    assert kq.da_chot and kq.can_cu["loai"] == "giong_mau"
    assert goi == [], "goi kiem quyen cho mot giong mau"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Ranh gioi: ASV chi so huu CHINH SACH
# ══════════════════════════════════════════════════════════════════════════════

def test_rang_giong_KHONG_tong_hop_mot_mili_giay_nao():
    """⛔ Tep nay tra loi "giong nao", khong tra loi "tieng ra sao"."""
    cay = ast.parse((APP / "rang_giong.py").read_text(encoding="utf-8"))
    goi = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            goi.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    for cam in ("sinh", "tong_hop", "synthesize", "goi_cong", "san_sang"):
        assert cam not in goi, f"rang_giong.py goi {cam!r} — do la viec cua LTT Voice"


def test_ASV_KHONG_go_lai_bo_loc_cua_app_chu():
    """⭐ Phep loc la mot QUY TAC. Hai ban cua mot quy tac la hai ban se lech."""
    van = (APP / "rang_giong.py").read_text(encoding="utf-8")
    assert "giong_mau import loc" in van or "giong_mau.loc" in van
    for dau_hieu in ("g.gioi ==", "g.vung ==", "g.phong_cach =="):
        assert dau_hieu not in van, f"chep lai phep loc: {dau_hieu}"


def test_ba_mat_dac_diem_KHOP_voi_catalog_cua_app_chu():
    """🔴 Bia them mot mat thu tu se cho ra mot bo loc khong bao gio khop."""
    import dataclasses as dc

    from apps.ltt_voice import giong_mau

    mat_asv = {f.name for f in dc.fields(rg.DacDiemMongMuon)}
    mat_chu = {f.name for f in dc.fields(giong_mau.GiongMau)} - {"ma"}
    assert mat_asv == mat_chu, (
        f"ASV mong {sorted(mat_asv)}, catalog phan loai theo {sorted(mat_chu)}")


def test_gia_tri_hop_le_lay_tu_NHAN_cua_app_chu():
    """Neu app chu them mot vung/gioi moi, ASV khong phai sua gi."""
    from apps.ltt_voice import giong_mau

    assert set(giong_mau.NHAN_GIOI) == {"nam", "nu"}
    assert set(giong_mau.NHAN_VUNG) == {"bac", "trung", "nam"}
    assert giong_mau.NHAN_PHONG_CACH


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Be mat: THEM, khong SUA
# ══════════════════════════════════════════════════════════════════════════════

def test_bay_ten_catalog_nam_trong_BE_MAT_CONG_KHAI():
    from apps.ltt_voice import BE_MAT_CONG_KHAI

    for ten in ("loc", "tim", "hop_le", "DANH_SACH",
                "NHAN_GIOI", "NHAN_VUNG", "NHAN_PHONG_CACH"):
        assert ("apps.ltt_voice.giong_mau", ten) in BE_MAT_CONG_KHAI, ten


def test_linter_khop_be_mat_khong_rong_hon():
    """Mot ten trong danh sach cho phep ma app chu KHONG khai la mot canh voi
    qua rao co giay phep — te hon khong co giay phep, vi no trong nhu hop le."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_lint9", GOC / "tools" / "lint_app_contract.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    from apps.ltt_voice import BE_MAT_CONG_KHAI

    duoc = m.APP_DUOC_DUNG_APP[("auto_scan_video", "ltt_voice")]
    thua = duoc - set(BE_MAT_CONG_KHAI)
    assert thua == set(), f"cho phep nhung app chu khong khai: {sorted(thua)}"


def test_speech_ltt_van_con_nguyen():
    """⛔ Hop dong CU cua app chu khong duoc dong toi. Pha nay chi THEM."""
    from apps.ltt_voice.manifest import MANIFEST

    ten = {getattr(t, "name", "") for t in (MANIFEST.tools or ())}
    assert "speech.ltt" in ten, "pha 09 lam mat ToolSpec cong khai cua app chu"


def test_ASV_chi_cham_nhung_ten_da_khai():
    """Chieu khang dinh, quet AST ca thu muc app."""
    from apps.ltt_voice import BE_MAT_CONG_KHAI

    cho_phep = {ten for _m, ten in BE_MAT_CONG_KHAI}
    xau = []
    for tep in sorted(APP.rglob("*.py")):
        for n in ast.walk(ast.parse(tep.read_text(encoding="utf-8"))):
            if isinstance(n, ast.ImportFrom) and \
                    (n.module or "").startswith("apps.ltt_voice"):
                for a in n.names:
                    if a.name not in cho_phep:
                        xau.append(f"{tep.name}: {n.module}.{a.name}")
    assert xau == [], xau


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Doc yeu cau tu thiet lap cua lan chay
# ══════════════════════════════════════════════════════════════════════════════

def test_doc_duoc_ca_hai_che_do_tu_settings():
    yc = rg.tu_thiet_lap({"che_do_giong": "USER_SELECTED", "giong_id": "v1"})
    assert yc.che_do == "USER_SELECTED" and yc.giong_id == "v1"

    yc2 = rg.tu_thiet_lap({"che_do_giong": "AUTO_MATCH",
                           "dac_diem_giong": {"gioi": "nu", "vung": "nam"}})
    assert yc2.dac_diem.gioi == "nu" and yc2.dac_diem.vung == "nam"


def test_settings_rong_thi_ra_che_do_MAC_DINH_hop_le():
    from apps.auto_scan_video import hop_dong_v4

    # ⚠️ Mac dinh la USER_SELECTED, va no doi `giong_id` — nen settings rong
    #    phai NEM chu khong duoc lang le thanh AUTO_MATCH.
    assert hop_dong_v4.CHE_DO_GIONG_MAC_DINH == "USER_SELECTED"
    with pytest.raises(rg.RangGiongError):
        rg.tu_thiet_lap({})


def test_che_do_bia_ra_bi_tu_choi():
    with pytest.raises(rg.RangGiongError):
        rg.tu_thiet_lap({"che_do_giong": "MOT_CHE_DO_KHONG_CO"})
