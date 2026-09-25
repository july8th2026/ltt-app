"""Pha 14 — ban long tieng cho phan duoc giu lai.

Bon nhom, theo dung bon dieu cong thoat cua pha doi:

  A. Phu kin CHINH XAC  — dung nhung doan duoc giu, khong thua, khong thieu
  B. Dinh danh          — ghep theo MA, khong bao gio theo vi tri
  C. Giong DONG BANG    — chot truoc khi viet, va di vao van tay
  D. Diem chot theo doan — thu lai khong tra tien lai cho phan da xong
"""
from __future__ import annotations

import json
import textwrap

import pytest

from apps.auto_scan_video import ban_bien_tap, long_tieng
from tests.fixtures import asv_media as fx_media

# 🔴 Cac phep kiem o day chay HET chuoi, nen chung cham toi `audio_prepare`.
#    Xem `tests/rao_chan_nang.py`.
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401


def _ban_ghi(n=6) -> dict:
    return {"ngon_ngu": "en", "doan": [
        {"ma": f"seg_{i:04d}", "bat": float(i * 10), "ket": float(i * 10 + 8),
         "chu": f"source line {i}"} for i in range(n)]}


def _ban(giu: list[str], cat: list[str], *, preset="smart_localize") -> object:
    return ban_bien_tap.BanBienTap(
        preset=preset,
        quyet_dinh=tuple(
            [ban_bien_tap.QuyetDinh(m, ban_bien_tap.THAO_TAC_GIU, "giu", 0.9)
             for m in giu]
            + [ban_bien_tap.QuyetDinh(m, ban_bien_tap.THAO_TAC_CAT, "cat", 0.9)
               for m in cat]),
        thoi_luong_nguon=100.0)


def _chuyen(mas) -> dict:
    return {m: {"chu": f"loi viet cua {m}", "cam_xuc": long_tieng.CAM_XUC[0],
                "kieu_noi": long_tieng.KIEU_NOI[0], "nhan_manh": []} for m in mas}


def _giu(bg, mas) -> dict:
    return {**bg, "doan": [d for d in bg["doan"] if d["ma"] in set(mas)]}


# ══════════════════════════════════════════════════════════════════════════════
#  A. Phu kin CHINH XAC
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_long_tieng_phu_DUNG_phan_giu_lai():
    bg = _ban_ghi()
    giu = _giu(bg, ["seg_0000", "seg_0002", "seg_0004"])
    tl = long_tieng.dung(giu, _chuyen([d["ma"] for d in giu["doan"]]),
                         ma_giong="G", van_tay_ban="vt", provider="p", model="m")
    long_tieng.kiem(tl, giu)
    assert [m["ma"] for m in tl["muc"]] == ["seg_0000", "seg_0002", "seg_0004"]


def test_mot_doan_thuoc_canh_DA_CAT_lot_vao_thi_BI_TU_CHOI():
    """⛔ Mot cau duoc **doc len** cho mot doan hinh khong con ton tai.

    Day la huong hong ton tien: no di qua tong hop tieng, qua render, va chi lo
    ra khi co nguoi XEM ban ra.
    """
    bg = _ban_ghi()
    giu = _giu(bg, ["seg_0000", "seg_0002"])
    tl = long_tieng.dung(giu, _chuyen(["seg_0000", "seg_0002"]),
                         ma_giong="G", van_tay_ban="vt", provider="p", model="m")
    tl["muc"].append({"ma": "seg_0003", "bat": 30.0, "ket": 38.0, "goc": "x",
                      "chu": "cau thua", "cam_xuc": long_tieng.CAM_XUC[0],
                      "kieu_noi": long_tieng.KIEU_NOI[0], "nhan_manh": []})
    with pytest.raises(long_tieng.LongTiengError, match="phủ đúng"):
        long_tieng.kiem(tl, giu)


def test_thieu_mot_doan_GIU_LAI_thi_BI_TU_CHOI():
    """Va huong nguoc lai: mot doan hinh con do ma **im lang**."""
    bg = _ban_ghi()
    giu = _giu(bg, ["seg_0000", "seg_0002", "seg_0004"])
    with pytest.raises(long_tieng.ThieuDoan):
        long_tieng.dung(giu, _chuyen(["seg_0000", "seg_0002"]),
                        ma_giong="G", van_tay_ban="vt", provider="p", model="m")


def test_model_BIA_THEM_ma_thi_ma_do_bi_bo_di():
    """Mot ma khong duoc gui la mot doan loi thoai gan cho mot doan hinh khong co."""
    goi = {"doan": {"seg_0000": {"chu": "a"}, "seg_9999": {"chu": "bia"}}}
    ra = long_tieng.doc_chuyen(goi, {"seg_0000"})
    assert set(ra) == {"seg_0000"}


# ══════════════════════════════════════════════════════════════════════════════
#  B. Dinh danh — ghep theo MA
# ══════════════════════════════════════════════════════════════════════════════

def test_lo_TRA_VE_THIEU_thi_NEM_chu_khong_lam_lech_moi_cau_sau_do():
    """🔴 Menh de trung tam cua nhom B.

    Ghep theo **vi tri**: mot lo 12 doan tra ve 11 thi tu doan thu k tro di moi
    cau bi gan sang doan ben canh — tai lieu van du truong, van hop le, va tu
    giua phim tro di loi thoai lech mot cau. Ghep theo **ma** bien no thanh mot
    loi noi ra duoc.
    """
    da_gui = {f"seg_{i:04d}" for i in range(12)}
    thieu_mot = {"doan": {m: {"chu": f"x {m}"} for m in sorted(da_gui)[:11]}}
    with pytest.raises(long_tieng.ThieuDoan):
        long_tieng.doc_chuyen(thieu_mot, da_gui)


def test_doi_DOAN_MOI_LO_thi_kich_thuoc_lo_DOI_THAT():
    """🔴 Mot num van trong nhu da chinh ma khong chinh gi.

    `chia_lo(moi_lo=DOAN_MOI_LO)` gan mac dinh **luc dinh nghia ham**, nen doi
    hang so sau do khong doi duoc gi — ham van chay, ket qua van hop le, chi la
    voi kich thuoc lo cu. Tim ra khi mot phep kiem dat `DOAN_MOI_LO = 1` de tao
    nhieu lo va van chi thay MOT lo.
    """
    import apps.auto_scan_video.long_tieng as lt

    doan = [{"ma": f"seg_{i:04d}"} for i in range(6)]
    cu = lt.DOAN_MOI_LO
    try:
        lt.DOAN_MOI_LO = 2
        assert len(lt.chia_lo(doan)) == 3, (
            "doi DOAN_MOI_LO khong doi duoc kich thuoc lo")
    finally:
        lt.DOAN_MOI_LO = cu


def test_khong_chac_CHI_THU_va_KHONG_duoc_lam_hong_mot_lo():
    """⭐ DUONG B — `khong_chac` la mot cot CHAN DOAN, ⛔ khong phai thu san pham.

    ⛔ Nen moi dang sai cua no phai ra `[]`, ⛔ khong duoc nem: de mot cot chan
       doan lam hong mot lo loi thoai **da tra tien** la doi mot thu dat lay mot
       thu khong dat. Khac han `chu` — sai luoc do o `chu` PHAI thanh loi.
    """
    ra = long_tieng.doc_chuyen({"doan": {
        "s1": {"chu": "a", "khong_chac": ["掐雷", "  ", "x" * 99]},
        "s2": {"chu": "b"},                       # vang mat
        "s3": {"chu": "c", "khong_chac": "khong phai list"},   # sai kieu
        "s4": {"chu": "d", "khong_chac": list(range(50))},     # xa danh sach
    }}, {"s1", "s2", "s3", "s4"})
    assert ra["s1"]["khong_chac"][0] == "掐雷"
    assert len(ra["s1"]["khong_chac"]) == 2, "chuoi rong phai bi bo"
    assert len(ra["s1"]["khong_chac"][1]) == long_tieng.KHONG_CHAC_DAI_TOI_DA
    assert ra["s2"]["khong_chac"] == [], "vang mat => [] , ⛔ khong nem"
    assert ra["s3"]["khong_chac"] == [], "sai kieu => [] , ⛔ khong nem"
    assert len(ra["s4"]["khong_chac"]) == long_tieng.KHONG_CHAC_TOI_DA
    # ⛔ Va no ⛔ KHONG duoc ro ri ra tai lieu khach nhan: `dung` chi rap cac
    #    truong san pham. Dieu phoi chot: chi GHI vao `outputs`, khong hien.
    tl = long_tieng.dung(_giu(_ban_ghi(), ["seg_0000"]),
                         {"seg_0000": ra["s1"]}, ma_giong="g",
                         van_tay_ban="vt", provider="p", model="m")
    assert "khong_chac" not in tl["muc"][0], "⛔ khong duoc di ra tai lieu khach"


def test_y_canh_DI_VAO_loi_nhac_va_KHONG_lam_ban_duong_THUONG():
    """🔴 Vong sua truoc 25/09 **mu tu thiet ke**: `y_canh` co tham so, loi
    nhac co cho nhet, nhung ⛔ khong nguoi goi nao truyen — nen doan bi che
    duoc dich lai bang loi nhac Y HET lan dau (`B2_DICH.md` §7.10).

    ⛔ **DOI CHUNG HAI CHIEU la phan khong duoc bo:**
      (a) doan CO `y_canh`   => loi nhac mang DOAN TRICH + luat "kiem lai";
      (b) lo KHONG co doan nao => loi nhac **y het ban nen**.
    Thieu ve (b) thi ta ⛔ khong biet minh co lam ban duong THUONG hay khong,
    va moi so do cu cua duong thuong het so sanh duoc.
    """
    bg = _ban_ghi()
    lo = bg["doan"][:2]

    def _msg(y=None):
        return long_tieng.loi_nhac(lo, tat_ca=bg["doan"], ngon_ngu_goc="zh",
                                   dac_diem_giong={}, ngon_ngu_dich="vi",
                                   y_canh=y)

    # (b) ⛔ DOI CHUNG: khong `y_canh` => y het ban nen, TUNG BYTE.
    nen = _msg()
    assert nen == _msg({}), "`y_canh` rong ⛔ khong duoc doi gi"
    assert "NGHI NGO" not in nen[0]["content"], (
        "lo khong co doan bi che ⛔ KHONG duoc mang luat `y_canh`")
    assert "y_canh" not in json.loads(nen[-1]["content"])["doan"][0]

    # (a) co `y_canh` => luat xuat hien VA doan trich di vao payload.
    ma = str(lo[0]["ma"])
    co = _msg({ma: {"nghi_ngo": "sai thuc the",
                    "trich_nguon": "壁球",
                    "trich_ban_cu": "quần vợt"}})
    he = co[0]["content"]
    assert "NGHI NGO" in he and "GIU NGUYEN" in he
    # 🔴 Cau chu phai cho model DUONG LUI: bo cham co bao dong gia, nen
    #    ra lenh "hay sua" la cach bien mot bao dong gia thanh mot hong that.
    assert "KHONG duoc doi mot cau dang dung" in he
    goi = json.loads(co[-1]["content"])["doan"]
    y = {d["ma"]: d.get("y_canh") for d in goi}[ma]
    assert y["trich_nguon"] == "壁球", "phai mang DOAN TRICH, ⛔ khong chi nhan"
    assert y["trich_ban_cu"] == "quần vợt"
    # Doan THU HAI trong cung lo ⛔ khong duoc mang `y_canh` cua doan kia.
    assert {d["ma"]: d.get("y_canh") for d in goi}[str(lo[1]["ma"])] is None


def test_NGUOI_GOI_that_su_TRUYEN_y_canh_cho_loi_nhac():
    """🔴 **Phep bat DUNG khuyet tat da xay ra**, ⛔ khong phai mot bien the.

    Khuyet tat that (truoc 25/09): `loi_nhac` **co** tham so `y_canh`, loi nhac
    **co** cho nhet no — va ⛔ **khong mot nguoi goi nao truyen**. Vong sua vi
    the dich lai doan bi che bang loi nhac Y HET lan dau.

    ⛔ **Bai kiem don vi o tren ⛔ KHONG bat duoc chuyen do**: chung goi
       `loi_nhac` truc tiep nen luon truyen `y_canh`. Da thu tiem loi (bo
       `y_canh=` o `giai_doan_noi_dung`) — hai bai kia van XANH.
    ⭐ => Phai doc CAY cua chinh NGUOI GOI. Mot tham so khong ai truyen la mot
       tham so khong ton tai.
    """
    import ast
    import inspect

    from apps.auto_scan_video import giai_doan_noi_dung as gdn

    cay = ast.parse(textwrap.dedent(inspect.getsource(gdn.chay)))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "loi_nhac"]
    assert goi, "`chay` khong con goi `long_tieng.loi_nhac` — bai dang nhin cho khac"
    for g in goi:
        ten = {k.arg for k in g.keywords}
        assert "y_canh" in ten, (
            "`giai_doan_noi_dung.chay` ⛔ KHONG truyen `y_canh` cho `loi_nhac` "
            "=> vong sua lai mu, va N-02 quay lai")


def test_y_canh_cho_CAT_va_bo_truong_rong():
    """`sua_chua.y_canh_cho` phai KIEM SOAT dinh dang, ⛔ khong do van tho vao.

    ⚠️ *Vi du trong loi nhac la mot MENH LENH ngam* — `y_canh` di THANG vao
    loi nhac, nen **hinh dang** cua no dang day model.
    """
    from apps.auto_scan_video import sua_chua

    kk = sua_chua.KhiemKhuyet(
        sua_chua.DICH_SAI, ma="s1", ly_do="  x" + "y" * 500,
        bang_chung={"nguon": "n" * 500, "dich": ""})
    y = sua_chua.y_canh_cho(kk)
    assert len(y["nghi_ngo"]) == sua_chua.Y_CANH_TOI_DA
    assert len(y["trich_nguon"]) == sua_chua.Y_CANH_TOI_DA
    assert "trich_ban_cu" not in y, "truong rong ⛔ khong duoc nhet vao loi nhac"
    # ⛔ Khong co gi dung duoc => `{}`, va `{}` ⛔ khong duoc vao loi nhac.
    assert sua_chua.y_canh_cho(sua_chua.KhiemKhuyet(
        sua_chua.DICH_SAI, ma="s1")) == {}


def test_chu_HAN_lot_ban_ghi_bi_DANH_DAU_va_KHONG_lam_hong_luot():
    """⭐ Bat bien o BIEN: ban ghi tieng Viet ⛔ khong duoc chua chu Han.

    Do that (`B2_DICH.md` §7.8d): **1/343** chuoi lot — `"…dùng súng提炼…"`, den
    tu mot **loi CHEP LOI** (`提炼` <- `提炼枪`), ⛔ khong phai luat ten rieng.

    ⛔ **DOI CHUNG la phan khong duoc bo.** Thieu ve "ban SACH thi IM" thi mot
       `raise` vo dieu kien — hay mot ham luon tra `["gi do"]` — cung xanh.
    """
    # (a) ban BAN: phai bat, va phai tra ve DOAN TRICH chu khong phai True.
    ban = long_tieng.chu_han_lot("Cau nay lao vao, dung sung提炼 de du no.")
    assert ban, "⛔ chu Han lot ma khong bat duoc"
    assert "提炼" in ban[0], "phai tra DOAN TRICH de nguoi soi biet o dau"
    assert not isinstance(ban[0], bool)

    # (b) ⛔ DOI CHUNG — ban SACH phai IM. Thieu ve nay thi bai dang do chinh no.
    assert long_tieng.chu_han_lot("Cach tot nhat la vao trong nha ngay.") == []
    assert long_tieng.chu_han_lot("") == []
    # ⚠️ Dau tieng Viet ⛔ KHONG duoc tinh la chu Han.
    assert long_tieng.chu_han_lot("Lý Tông Thịnh · Trương Vĩ · Quảng Châu") == []

    # (c) Nhieu cum => nhieu doan trich, ⛔ khong gop thanh mot.
    assert len(long_tieng.chu_han_lot("a 提炼 b 光子 c")) == 2


def test_quy_tac_TEN_RIENG_chi_ra_khi_dich_VI():
    """🔑 *"Phien am HAN-VIET"* la luat cua **tieng Viet**, khong phai cua moi dich.

    ⚠️ `ngon_ngu.DICH_HOP_LE` co ca `en` (`kiem_cap`). Chen luat nay vo dieu kien
       la dung lai **F-05** — loi nhac ghi cung "tieng Viet" cho moi nguon.

    ⛔ Bai kiem CA HAI chieu. Thieu ve `en` thi mot ban vo hieu hoa dieu kien
       (chen vo dieu kien) van xanh, va bai dang gac chinh no.
    """
    bg = _ban_ghi()
    def _he(dich):
        return long_tieng.loi_nhac(bg["doan"][:2], tat_ca=bg["doan"],
                                   ngon_ngu_goc="zh", dac_diem_giong={},
                                   ngon_ngu_dich=dich)[0]["content"]
    moc = long_tieng.QUY_TAC_TEN_RIENG_VI["content"]
    assert moc in _he("vi"), "dich `vi` phai mang quy tac ten rieng"
    assert moc not in _he("en"), "dich `en` ⛔ KHONG duoc mang luat Han-Viet"
    # ⭐ Vi du phai CO DAU: ban `dich_thuat` v2 viet vi du khong dau va model
    #    chep HINH DANG cua vi du — mot ten von dung tut thanh khong dau
    #    (`B2_DICH.md` §4c). Chot lai bang mot phep kiem, khong bang tri nho.
    assert "Trương Vĩ" in moc and "Lý Tông Thịnh" in moc


def test_loi_nhac_YEU_CAU_khoa_la_ma_doan():
    """Chot chinh loi nhac: doi tuong co khoa, khong phai mang."""
    bg = _ban_ghi()
    msgs = long_tieng.loi_nhac(bg["doan"][:3], tat_ca=bg["doan"],
                               ngon_ngu_goc="en", dac_diem_giong={})
    he = msgs[0]["content"]
    assert "MA DOAN" in he
    assert '"<ma doan>"' in he
    goi = json.loads(msgs[-1]["content"])
    assert [d["ma"] for d in goi["doan"]] == ["seg_0000", "seg_0001", "seg_0002"]


def test_moi_doan_mang_theo_THOI_LUONG_GOC():
    """⭐ Pha 15 rut ngan cho vua; rut ngan mot cau viet ma khong biet no phai dai
    bao nhieu la sua mot thu le ra khong nen sai ngay tu dau."""
    bg = _ban_ghi()
    goi = json.loads(long_tieng.loi_nhac(bg["doan"][:2], tat_ca=bg["doan"],
                                         ngon_ngu_goc="en",
                                         dac_diem_giong={})[-1]["content"])
    assert all(d["thoi_luong_giay"] == 8.0 for d in goi["doan"])


def test_ngu_canh_lay_tu_cac_doan_DUOC_GIU_khong_phai_ban_goc():
    """🔑 Sau khi cat, cau dung truoc mot cau trong ban ra co the la mot cau cach
    do ba phut trong ban goc — va do moi la cau khan gia vua nghe."""
    bg = _ban_ghi(8)
    giu = [d for d in bg["doan"] if d["ma"] in {"seg_0000", "seg_0005", "seg_0006"}]
    kq = long_tieng.ngu_canh_ke(giu, 1, ke=1)
    assert kq["truoc"] == ["source line 0"]      # KHONG phai "source line 4"
    assert kq["sau"] == ["source line 6"]


# ══════════════════════════════════════════════════════════════════════════════
#  C. Giong DONG BANG
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_co_giong_thi_KHONG_dung_duoc_tai_lieu():
    bg = _ban_ghi()
    giu = _giu(bg, ["seg_0000"])
    with pytest.raises(long_tieng.LongTiengError):
        long_tieng.dung(giu, _chuyen(["seg_0000"]), ma_giong="",
                        van_tay_ban="vt", provider="p", model="m")


def test_doi_GIONG_thi_van_tay_doi():
    """⛔ Loi thoai duoc viet CHO mot giong: xung ho, giong dieu, do trang trong
    deu bam vao no. Dung lai loi cu voi mot giong khac la giao mot ban long
    tieng ma khach khong dat."""
    a = long_tieng.van_tay_long_tieng(checksum_ban_ghi="c", van_tay_ban="b",
                                      ma_giong="G1", provider="p", model="m")
    b = long_tieng.van_tay_long_tieng(checksum_ban_ghi="c", van_tay_ban="b",
                                      ma_giong="G2", provider="p", model="m")
    assert a != b


def test_doi_BAN_BIEN_TAP_thi_van_tay_doi():
    a = long_tieng.van_tay_long_tieng(checksum_ban_ghi="c", van_tay_ban="b1",
                                      ma_giong="G", provider="p", model="m")
    b = long_tieng.van_tay_long_tieng(checksum_ban_ghi="c", van_tay_ban="b2",
                                      ma_giong="G", provider="p", model="m")
    assert a != b


def test_giong_duoc_ghi_VAO_tai_lieu():
    bg = _ban_ghi()
    giu = _giu(bg, ["seg_0000"])
    tl = long_tieng.dung(giu, _chuyen(["seg_0000"]), ma_giong="Minh Đức",
                         van_tay_ban="vt", provider="p", model="m")
    assert tl["ma_giong"] == "Minh Đức"
    long_tieng.kiem(tl, giu)


def test_hai_khoa_chon_giong_deu_dan_toi_MOT_ket_qua():
    """🔴 `rang_giong` doc `giong_id`; `giai_doan_giong` doc `voice_id`.

    Hai khoa cho cung mot cau hoi da song song ma khong ai noi — nen mot lan chay
    co the VIET loi thoai cho mot giong roi DOC len bang mot giong khac, va khong
    cho nao bao loi vi ca hai deu tim thay mot gia tri hop le cua rieng minh.
    """
    from apps.auto_scan_video import rang_giong

    a = rang_giong.tu_thiet_lap({"giong_id": "G"})
    b = rang_giong.tu_thiet_lap({"voice_id": "G"})
    assert a.giong_id == b.giong_id == "G"


# ══════════════════════════════════════════════════════════════════════════════
#  D. Bang tu vung DONG
# ══════════════════════════════════════════════════════════════════════════════

def test_sac_thai_ngoai_bang_ve_MAC_DINH_chu_khong_lam_hong_ca_lo():
    ra = long_tieng.doc_chuyen(
        {"doan": {"seg_0000": {"chu": "a", "cam_xuc": "buon man mac",
                               "kieu_noi": "sad"}}}, {"seg_0000"})
    assert ra["seg_0000"]["cam_xuc"] == long_tieng.CAM_XUC[0]
    assert ra["seg_0000"]["kieu_noi"] == long_tieng.KIEU_NOI[0]


def test_nhung_THIEU_CHU_thi_van_la_thieu_doan():
    """⭐ Sac thai la phu; `chu` la san pham. Mot doan khong co chu khong phai mot
    doan 'gan dung' — no la mot cho im lang trong ban ra."""
    with pytest.raises(long_tieng.ThieuDoan):
        long_tieng.doc_chuyen({"doan": {"seg_0000": {"chu": "  "}}}, {"seg_0000"})


def test_tai_lieu_co_sac_thai_ngoai_bang_thi_KIEM_bat_duoc():
    bg = _ban_ghi()
    giu = _giu(bg, ["seg_0000"])
    tl = long_tieng.dung(giu, _chuyen(["seg_0000"]), ma_giong="G",
                         van_tay_ban="vt", provider="p", model="m")
    tl["muc"][0]["cam_xuc"] = "u sau"
    with pytest.raises(long_tieng.LongTiengError):
        long_tieng.kiem(tl, giu)


# ══════════════════════════════════════════════════════════════════════════════
#  E. Doc lai duoc thu da ghi ra
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_bien_tap_doc_di_ghi_lai_giu_NGUYEN_van_tay():
    """🔴 Pha 12 ghi artifact nay ra ma khong co duong doc lai, va khong ai thay
    vi pha 12 khong tu doc lai bao gio. Pha 14 la nguoi doc dau tien.

    ⛔ `van_tay()` bam tren `sang_dict()`, nen mot vong doc-ghi lam lech van tay
       se vo hieu ca ha nguon ma khong co gi thay doi that.
    """
    b = _ban(["c1", "c3"], ["c2"])
    lai = ban_bien_tap.BanBienTap.tu_dict(b.sang_dict())
    assert lai.van_tay() == b.van_tay()
    assert lai.cac_ma_giu == b.cac_ma_giu


def test_chi_muc_canh_doc_di_ghi_lai_giu_NGUYEN_noi_dung():
    from apps.auto_scan_video import canh as canh_mod

    ci = canh_mod.ChiMucCanh(
        (canh_mod.Canh("canh_0001", 0.0, 5.0, (1.0, 3.0)),
         canh_mod.Canh("canh_0002", 5.0, 9.0, (6.0,))), 9.0)
    lai = canh_mod.tu_json(canh_mod.sang_json(ci))
    assert canh_mod.sang_json(lai) == canh_mod.sang_json(ci)


# ══════════════════════════════════════════════════════════════════════════════
#  F. Ban chep loi nguon BAT BIEN
# ══════════════════════════════════════════════════════════════════════════════

def test_loc_theo_ban_KHONG_cham_vao_ban_ghi_goc():
    bg = _ban_ghi()
    truoc = json.dumps(bg, sort_keys=True)
    b = _ban(["c1"], ["c2"])

    class Ci:
        canh = (type("C", (), {"ma": "c1", "bat": 0.0, "ket": 25.0})(),)

    ban_bien_tap.doan_giu_lai(bg, b, Ci())
    assert json.dumps(bg, sort_keys=True) == truoc, "ban ghi nguon bi sua"


# ══════════════════════════════════════════════════════════════════════════════
#  G. Chay THAT qua hang doi — gian diep, thu lai mot phan, so chi phi
# ══════════════════════════════════════════════════════════════════════════════

from tests.test_402_asv_mach_doc_gia import (asr_gia, db, giong_gia,  # noqa: E402,F401
                                             kho_tam)


def _run_cat(db, kho_tam, tmp_path, *, duration_s: float | None = None):
    """Run o preset **smart_localize**.

    ⭐ `duration_s` di thang xuong `_tao_run` — xem docstring cua no ve vi sao
       mot bai kiem CHO NOI phai xin mot nguon dai hon mau 3 giay.

    ⚠️ `hop_dong_v4.PRESET_MAC_DINH` la `localize_preserve_picture`, va preset do
       **khong cat canh nao** — dung theo thiet ke. Nen mot phep kiem ve "doan
       thuoc canh bi cat" ma dung preset mac dinh se bo qua trong im lang: xanh,
       va khong do gi.
    """
    from apps.auto_scan_video import hop_dong_v4
    from tests.test_402_asv_mach_doc_gia import _tao_run

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path, duration_s=duration_s)
    run.settings = {**dict(run.settings or {}),
                    "preset": hop_dong_v4.PRESET_CAT_THONG_MINH}
    db.commit()
    return run


def _nhieu_canh(monkeypatch):
    """Ep chi muc canh thanh SAU canh deu nhau.

    ⚠️ Mau video cua bo test la mot am sin 3 giay: phep tach canh that dung khi
       tra ve MOT canh. Voi mot canh thi khong cat duoc gi ma van giu du lieu,
       nen phep kiem gian diep se **bo qua trong im lang** — xanh ma khong do gi.
    """
    from apps.auto_scan_video import canh as canh_mod, giai_doan_ban_bien_tap

    def gia(duong, *, thoi_luong, hoi_huy=None, **kw):
        # 🔴 Canh dai 1,0 giay, TRUNG KHOP voi cac doan cua `ban_ghi_gia`
        #    ([0;0,8], [1;1,8], [2;2,8]...). Neu canh khong trung khop thi MOI
        #    doan deu chong lan mot canh duoc giu, tuc khong doan nao nam RIENG
        #    trong phan bi cat — va phep kiem gian diep tro thanh rong ruot:
        #    xanh du giai doan gui di tat ca. Kiem dot bien tim ra dung dieu do.
        n = max(1, int(round(float(thoi_luong))))
        return canh_mod.ChiMucCanh(
            tuple(canh_mod.Canh("canh_%04d" % (i + 1), float(i),
                                min(float(i + 1), float(thoi_luong)),
                                (float(i) + 0.5,))
                  for i in range(n)),
            float(thoi_luong))

    monkeypatch.setattr(canh_mod, "phan_tich", gia)
    monkeypatch.setattr(giai_doan_ban_bien_tap.canh_mod, "phan_tich", gia,
                        raising=False)


def _cat_canh_le(monkeypatch):
    """Ep ban bien tap CAT cac canh le, de co gi ma gian diep.

    ⚠️ Can thiep o `lap_ban` chu khong o dau khac: phep kiem nay do hanh vi cua
       CONTENT_PROCESS **khi da co mot ban cat**, khong do cach ban do duoc lap
       (do la viec cua pha 12, va hien no giu tat ca vi chua co ho so canh).
    """
    that = ban_bien_tap.lap_ban

    def gia(*, preset, chi_muc, hieu_canh=None, ban_ghi=None):
        b = that(preset=preset, chi_muc=chi_muc, hieu_canh=hieu_canh,
                 ban_ghi=ban_ghi)
        qd = tuple(
            ban_bien_tap.QuyetDinh(
                q.ma_canh,
                ban_bien_tap.THAO_TAC_CAT if i % 2 else ban_bien_tap.THAO_TAC_GIU,
                "ep de kiem", 0.99)
            for i, q in enumerate(b.quyet_dinh))
        if not any(q.giu for q in qd):
            qd = (ban_bien_tap.QuyetDinh(qd[0].ma_canh, ban_bien_tap.THAO_TAC_GIU,
                                         "giu toi thieu", 0.99),) + qd[1:]
        return ban_bien_tap.BanBienTap(
            preset=b.preset, quyet_dinh=qd,
            thoi_luong_nguon=b.thoi_luong_nguon, ghi_chu=dict(b.ghi_chu))

    monkeypatch.setattr(ban_bien_tap, "lap_ban", gia)


def _kho():
    """⚠️ Fixture `kho_tam` **dat kho toan cuc** roi tra ve `None` — no khong phai
    mot handle. Lay kho that qua nen tang."""
    from platform_core.storage import get_storage

    return get_storage()


def _tra_loi(mas):
    # ⚠️ `noi_dung` la CHUOI — dung thu `ai.goi` tra ve. Pha 22 tim ra rang
    #    mot ban gia tra ve dict o day che mat mot loi that o duong goi model.
    than = {"doan": {
        m: {"chu": "loi thoai cua " + m, "cam_xuc": long_tieng.CAM_XUC[0],
            "kieu_noi": long_tieng.KIEU_NOI[0], "nhan_manh": []}
        for m in mas}}
    return {"noi_dung": json.dumps(than, ensure_ascii=False), "su_dung": None}


def _ma_trong(messages):
    goi = json.loads(messages[-1]["content"])
    return [str(d["ma"]) for d in goi.get("doan") or []]


def test_KHONG_doan_nao_thuoc_canh_BI_CAT_duoc_gui_cho_model(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, giong_gia):
    """🔴 Day la cho tien chay ra ngoai, va la ly do V4-R07 ton tai.

    Mot doan thuoc canh da cat ma van duoc gui di la mot cau **duoc tra tien de
    viet va doc thanh tieng** cho mot doan hinh khong con ton tai trong ban ra.
    """
    from apps.auto_scan_video import ai, canh as canh_mod, features, pipeline
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)
    da_gui: list[str] = []

    def gia(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None, luoc_do=None):
        # ⭐ Uy quyen phan khong phai dich cho ban dung chung: stub nay do luu
        #    luong cua CONTENT_PROCESS, khong do EDIT_PLAN, va no khong duoc
        #    hong chi vi mot nguoi goi model thu hai xuat hien.
        san = fx_media.phan_hoi_ngoai_dich(thao_tac, messages)
        if san is not None:
            return san
        mas = _ma_trong(messages)
        da_gui.extend(mas)
        return _tra_loi(mas)

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)

    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)

    s = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    assert s.status == "succeeded", "content: %s %s" % (s.status, s.error)

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.EDIT_PLAN)
    khoa = next(k for k in (gd.outputs or {}).get("khoa_asset") or []
                if k.endswith(".json"))
    with _kho().open(khoa) as f:
        goi = json.loads(f.read().decode("utf-8"))
    ban = ban_bien_tap.BanBienTap.tu_dict(goi["ban"])
    # ⛔ KHONG `skip` o day. Mot phep kiem tu bo qua khi dieu kien khong thoa la
    #    mot phep kiem **im lang bien mat** — no van dem la "xanh" trong bao cao
    #    va khong ai biet no da thoi do gi. Neu ban bien tap khong cat canh nao
    #    thi mau thu sai, va do la mot LOI cua phep kiem chu khong phai mot ly do
    #    chinh dang de nghi viec.
    assert ban.cac_ma_cat, (
        "ban bien tap khong cat canh nao — mau thu sai, phep kiem nay dang "
        "khong do gi")
    ci = canh_mod.tu_dict(goi["chi_muc"])

    giu_kh = [(c.bat, c.ket) for c in ci.canh if c.ma in set(ban.cac_ma_giu)]

    tr = features.giai_doan_theo_ten(db, run.id, pipeline.TRANSCRIBE)
    kt = next(k for k in (tr.outputs or {}).get("khoa_asset") or []
              if k.endswith(".json"))
    with _kho().open(kt) as f:
        bg = json.loads(f.read().decode("utf-8"))

    # Doan KHONG chong lan bat cu canh nao duoc giu => no thuoc phan bi cat.
    chi_trong_cat = {
        d["ma"] for d in bg["doan"]
        if not any(d["ket"] > b and d["bat"] < k for b, k in giu_kh)}

    # 🔴 **Tu khang dinh truoc khi khang dinh.** Neu khong doan nao nam RIENG
    #    trong phan bi cat thi phep kiem duoi day dung voi moi cach cai dat —
    #    ke ca cach gui di TAT CA. Kiem dot bien da bat dung cho nay.
    assert chi_trong_cat, (
        "mau thu khong co doan nao nam RIENG trong canh bi cat — "
        "phep kiem nay dang khong do gi")

    lot = chi_trong_cat & set(da_gui)
    assert not lot, "gui cho model %d doan thuoc canh DA CAT: %s" % (
        len(lot), sorted(lot)[:5])


def test_thu_lai_KHONG_gui_lai_nhung_doan_DA_XONG(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, giong_gia):
    """⭐ Diem chot theo doan chi co gia tri neu lan chay thu hai THAT SU bo qua.

    🔴 **Ban dau phep kiem nay chot sai hai lan lien tiep, va ca hai deu dang ghi
       lai** — vi ca hai deu la "phep kiem xanh/do vi mot ly do khong lien quan
       toi dieu no dinh do":

       1. No khang dinh giai doan phai o trang thai HONG sau khi mot lo hong.
          Nhung `AiError` la loi **thu lai duoc**, nen nen tang chay lai giai
          doan, lan hai bo qua lo dau va chay tiep — giai doan `succeeded`. Phep
          kiem do, trong khi co che no dinh do dang chay dung.
       2. No dat `DOAN_MOI_LO = 1` de tao nhieu lo, nhung `chia_lo` gan mac dinh
          luc dinh nghia ham nen **kich thuoc lo khong doi**. Do la mot loi that
          trong ma, tim ra nho phep kiem nay khong do duoc thu no muon do.

    ⭐ Gio no goi THANG giai doan lan thu hai, va do **moi doan duoc gui dung mot
       lan** qua ca hai lan chay. Do la toan bo y nghia cua diem chot: lan sau
       tra tien cho phan CON LAI, khong tra lai tu dau.
    """
    from apps.auto_scan_video import ai, giai_doan_noi_dung
    from apps.auto_scan_video.tables import AsvRun
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi

    monkeypatch.setattr(long_tieng, "DOAN_MOI_LO", 1)
    _nhieu_canh(monkeypatch)

    da_gui: list[str] = []
    dem = {"n": 0}

    def gia(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None, luoc_do=None):
        # ⭐ Uy quyen phan khong phai dich cho ban dung chung: stub nay do luu
        #    luong cua CONTENT_PROCESS, khong do EDIT_PLAN, va no khong duoc
        #    hong chi vi mot nguoi goi model thu hai xuat hien.
        san = fx_media.phan_hoi_ngoai_dich(thao_tac, messages)
        if san is not None:
            return san
        mas = _ma_trong(messages)
        dem["n"] += 1
        if dem["n"] == 2:
            raise ai.AiError("gia lap hong o lo thu hai")
        da_gui.extend(mas)
        return _tra_loi(mas)

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)

    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)
    assert dem["n"] >= 2, "chua chay toi lo thu hai — phep kiem khong do duoc gi"
    xong = set(da_gui)
    assert xong, "lo dau chua xong thi khong co gi de bo qua"

    # Lan hai: goi thang, khong phu thuoc chinh sach thu lai cua nen tang.
    db.expire_all()
    giai_doan_noi_dung.chay(db, _kho(), run=db.get(AsvRun, run.id), ctx=None)

    trung = [m for m in set(da_gui) if da_gui.count(m) > 1]
    assert not trung, (
        "gui lai %d doan da xong: %s — diem chot khong duoc dung, "
        "lan sau dang tra tien lai tu dau" % (len(trung), sorted(trung)[:5]))


def test_diem_chot_giu_KET_QUA_va_mang_VAN_TAY(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, giong_gia):
    """Mot diem chot khong giu ket qua thi lan thu lai van phai goi model lai —
    tuc no ghi nhan cong viec ma khong tiet kiem duoc gi."""
    from apps.auto_scan_video import features, pipeline
    from apps.auto_scan_video.tables import AsvRun
    from tests.fixtures.asv_media import cua_ai_gia
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    monkeypatch.setattr(long_tieng, "DOAN_MOI_LO", 2)
    cua_ai_gia(monkeypatch)

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()
    run = db.get(AsvRun, run.id)

    s = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    assert s.status == "succeeded", "content: %s %s" % (s.status, s.error)

    dv = features.cac_don_vi(db, run.id, pipeline.CONTENT_PROCESS)
    assert dv, "khong co diem chot nao"
    assert all(x.status == "succeeded" for x in dv)
    assert all(x.fingerprint for x in dv), "diem chot khong mang van tay"
    assert all((x.outputs or {}).get("chu") for x in dv), (
        "diem chot khong giu ket qua - lan thu lai se phai goi model lai")


def test_doi_GIONG_thi_diem_chot_cu_KHONG_duoc_dung_lai(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, giong_gia):
    """🔴 Lo hong thu hai ma kiem dot bien tim ra: `da_xong` khong loc van tay.

    Diem chot tra loi cau hoi *"da viet loi cho doan nay chua"*. Sau khi doi
    giong, do la mot cau hoi **KHAC**: loi thoai duoc viet CHO mot giong — xung
    ho, giong dieu, do trang trong deu bam vao no.

    ⛔ Dung lai diem chot cu o day thi khach nhan mot ban long tieng **nua cu nua
       moi**: nhung doan da viet mang giong dat luc dau, nhung doan con lai mang
       giong moi. Va no khong hong o dau ca — chi la nghe khong ra mot nguoi.
    """
    from apps.auto_scan_video import ai, giai_doan_noi_dung
    from apps.auto_scan_video.tables import AsvRun
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi

    lan1: list[str] = []
    lan2: list[str] = []
    dang = lan1

    def gia(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None, luoc_do=None):
        # ⭐ Uy quyen phan khong phai dich cho ban dung chung: stub nay do luu
        #    luong cua CONTENT_PROCESS, khong do EDIT_PLAN, va no khong duoc
        #    hong chi vi mot nguoi goi model thu hai xuat hien.
        san = fx_media.phan_hoi_ngoai_dich(thao_tac, messages)
        if san is not None:
            return san
        mas = _ma_trong(messages)
        dang.extend(mas)
        return _tra_loi(mas)

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)

    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)
    assert lan1, "lan chay dau khong goi model lan nao"

    # Doi giong => van tay doi => moi doan phai duoc viet LAI.
    db.expire_all()
    run = db.get(AsvRun, run.id)
    run.settings = {**dict(run.settings or {}), "giong_id": "Adam"}
    db.commit()

    dang = lan2
    giai_doan_noi_dung.chay(db, _kho(), run=db.get(AsvRun, run.id), ctx=None)

    assert set(lan2) >= set(lan1), (
        "doi giong ma van dung lai diem chot cu: %s khong duoc viet lai"
        % sorted(set(lan1) - set(lan2))[:5])
