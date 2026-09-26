"""M-02 — lop QC HINH: doi nguoc cho noi -> canh, doc phan hoi, va CHINH SACH.

Sổ lỗi `LOI_TONG.md` M-02: *"QC lien tuc canh bang VLM dinh nghia nhung **khong
ai goi**"*. Ba manh da co tu pha 19 (`qc_ai.loi_nhac_hinh`, `qc_ai.doc_hinh`,
`sua_chua.tu_qc_hinh`) va **khong manh nao co nguoi goi trong ma san pham** —
dung hinh dang ma kiem toan pha 26 dem duoc nam lan.

Tep nay chot bon nhom menh de:

  §1 DOI NGUOC   cho noi (truc BAN RA) -> canh BI BO (don vi `edit_plan` nhan)
  §2 DOC         phan hoi model: chuan hoa, va cai gi PHAI no
  §3 LOI NHAC    khung JSON — bai hoc do duoc cua lane `fix-toc-do` (R-05)
  §4 CHINH SACH  tu van hay gate, va vong sua co DUNG

⛔ `test_2121` chot CHO NOI (giai doan that goi that) — hai tep, hai cau hoi.
"""
from __future__ import annotations

import inspect

import pytest

from apps.auto_scan_video import (ai, ban_do_thoi_gian as bdtg, canh as canh_mod,
                                  giai_doan_qc_ai as gdqa, hieu_canh as hc,
                                  qc_ai, sua_chua as sc)


def _ci(n: int, dai: float = 10.0):
    return canh_mod.ChiMucCanh(
        tuple(canh_mod.Canh(f"canh_{i + 1:04d}", i * dai, (i + 1) * dai)
              for i in range(n)), n * dai)


def _kq(noi_dung: str, **them) -> dict:
    return {"noi_dung": noi_dung, "finish_reason": "stop", "suy_nghi": "",
            **them}


# ══════════════════════════════════════════════════════════════════════════════
#  §1. Doi nguoc: mot cho noi -> nhung CANH sua duoc no
# ══════════════════════════════════════════════════════════════════════════════

def test_cho_noi_doi_nguoc_ra_DUNG_canh_bi_bo():
    """🔴 Day la thu bien mot phan doan thanh mot viec SUA.

    Mot cho noi *"o giay 20 cua ban ra"* khong sua duoc: khong giai doan nao
    nhan "giay 20" lam don vi viec. Cai sua duoc la *"canh_0003 bi bo o day"*,
    va `edit_plan` nhan dung don vi do.
    """
    bd = bdtg.BanDoThoiGian.tu_khoang(
        [(0, 10), (10, 20), (30, 40), (50, 60)], thoi_luong_nguon=60.0)
    cn = qc_ai.cac_cho_noi(bd, chi_muc=_ci(6),
                           cac_ma_cat=["canh_0003", "canh_0005"])
    assert [c["moc_ra"] for c in cn] == [20.0, 30.0]
    # Cho noi thu nhat sinh ra vi `canh_0003` (20-30 s nguon) bi bo.
    assert cn[0]["ma_cat"] == ["canh_0003"]
    assert cn[0]["cat_nguon"] == [20.0, 30.0]
    # Cho noi thu hai vi `canh_0005` (40-50 s).
    assert cn[1]["ma_cat"] == ["canh_0005"]


def test_khoang_bo_NHIEU_canh_sinh_NHIEU_don_vi_sua():
    """Hai canh lien nhau cung bi bo = MOT cho noi, nhung HAI don vi sua.

    ⛔ Chon mot canh "dai dien" la doan: canh nao trong hai canh do la cau noi
       can thiet thi chi mot lan hoi lai moi biet.
    """
    bd = bdtg.BanDoThoiGian.tu_khoang([(0, 10), (30, 40)], thoi_luong_nguon=40.0)
    cn = qc_ai.cac_cho_noi(bd, chi_muc=_ci(4),
                           cac_ma_cat=["canh_0002", "canh_0003"])
    assert len(cn) == 1
    assert cn[0]["ma_cat"] == ["canh_0002", "canh_0003"]
    kk = sc.tu_qc_hinh([{**cn[0], "dat": False, "do_tin": 0.9, "ly_do": "x"}],
                       tu_van=False)
    assert sorted(k.ma for k in kk) == ["canh_0002", "canh_0003"]
    assert {k.giai_doan for k in kk} == {"edit_plan"}


def test_moc_cho_noi_nam_tren_truc_BAN_RA_khi_co_doi_TOC_DO():
    """⛔ Truc BIEN TAP va truc BAN RA chi trung khi `toc_do` bang 1.

    Rut khung o giay cua truc bien tap tren mot tep da doi toc do la rut nham
    khung — va cang ve cuoi phim cang lech xa. Hai buoc cua phep anh xa:
    `BanDoThoiGian.ra` roi `bien_tap.moc_ban_ra`.
    """
    bd = bdtg.BanDoThoiGian.tu_khoang([(0, 10), (30, 40)], thoi_luong_nguon=40.0)
    assert qc_ai.moc_cho_noi(bd) == [10.0]                 # truc bien tap
    cn = qc_ai.cac_cho_noi(bd, toc_do=1.25)
    assert cn[0]["moc_bien_tap"] == 10.0
    assert cn[0]["moc_ra"] == 8.0                          # 10 / 1,25
    assert cn[0]["khung_s"] == [7.6, 8.4]


def test_KHONG_bia_ma_canh_khi_thieu_chi_muc():
    """⚠️ Khong co chi muc canh ⇒ phan quyet van GHI duoc, viec sua thi khong.

    ⛔ Bia mot ma canh de "co viec lam" se dat lai mot canh khong lien quan.
    """
    bd = bdtg.BanDoThoiGian.tu_khoang([(0, 10), (30, 40)], thoi_luong_nguon=40.0)
    cn = qc_ai.cac_cho_noi(bd)                       # khong truyen chi_muc
    assert cn[0]["ma_cat"] == []
    assert sc.tu_qc_hinh([{**cn[0], "dat": False, "do_tin": 0.9}],
                         tu_van=False) == []


def test_ban_do_MOT_khoang_khong_co_cho_noi_nao():
    """⭐ Preset giu hinh: khong cat canh nao ⇒ khong co gi de hoi, va do la
    duong chay that chu khong phai truong hop bien — hoi khap phim la tra tien
    de nghe model xac nhan rang phan khong bi cham van nguyen ven."""
    bd = bdtg.BanDoThoiGian.giu_nguyen(100.0)
    assert qc_ai.cac_cho_noi(bd, chi_muc=_ci(10)) == []


# ══════════════════════════════════════════════════════════════════════════════
#  §2. Doc phan hoi — bai hoc R-05, va cai gi PHAI no
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tho,ra", [
    (True, True), (False, False),
    ("true", True), ("false", False),
    # 🔴 Model tra loi bang TIENG VIET THAT. 5/18 luot `doc_canh` hong vi dung
    #    dieu nay (`L_FIX_TOC_DO.md` R-05) — mot dau nga.
    ("đạt", True), ("Đạt", True), ("không đạt", False), ("KHÔNG", False),
    ("lien_mach", True), ("dut_mach", False), ("dut-mach", False),
    (1, True), (0, False),
])
def test_chuan_dat_nhan_dien_duoc_cac_hinh_dang_DA_DO(tho, ra):
    assert qc_ai.chuan_dat(tho) is ra


@pytest.mark.parametrize("tho", ["co le", "0.5", "", None, "maybe", 0.5, [], {}])
def test_chuan_dat_KHONG_nuot_rac(tho):
    """⛔ Chuan hoa NHAN DIEN, khong DOAN. Mot gia tri la ra `None` ⇒ nguoi goi
    nem — dung nguyen tac voi `hieu_canh.chuan_de_xuat` (`"bu"` -> `""`)."""
    assert qc_ai.chuan_dat(tho) is None


def test_chuan_dat_dung_DUNG_ham_bo_dau_cua_hieu_canh():
    """⛔ Khong duoc co ban sao thu hai cua phep bo dau: hai ban se lech nhau,
    va nhanh lech la nhanh it duoc chay nhat."""
    assert "hieu_canh" in inspect.getsource(qc_ai.chuan_dat)
    assert "chuan_ma" in inspect.getsource(qc_ai.chuan_dat)
    # Va `chuan_de_xuat` cung phai di qua no (mot nguon).
    assert "chuan_ma(" in inspect.getsource(hc.chuan_de_xuat)


def test_doc_hinh_nhan_CA_KET_QUA_chu_khong_phai_noi_dung():
    """🔴 Boc `noi_dung` bang tay vut mat `finish_reason` va `suy_nghi` — tuc
    vut mat thu duy nhat phan biet "model tra sai luoc do" voi "model het tran
    token giua khoi suy nghi". Bon phien lien tiep da di do nham may B vi cau
    do (09/09)."""
    kq = _kq("", finish_reason="length", suy_nghi="x" * 9000)
    with pytest.raises(ai.LuocDoSai) as e:
        qc_ai.doc_hinh(kq, moc_giay=1.0)
    assert "length" in str(e.value) and "9000" in str(e.value)
    assert "HET NGAN SACH TOKEN" in str(e.value)


def test_thieu_dat_thi_NO_chu_khong_mac_dinh_DAT():
    """⛔ Ban truoc viet `bool(goi.get("dat", True))`: mot phan hoi thieu truong
    doc ra thanh "cho noi nay DAT". Im lang cua model khong phai mot loi khai
    rang ban ra lanh lan."""
    with pytest.raises(ai.LuocDoSai):
        qc_ai.doc_hinh(_kq('{"do_tin": 0.9, "ly_do": ""}'), moc_giay=1.0)
    # Khoa CO nhung gia tri LA => van no, o tang thu hai.
    with pytest.raises(qc_ai.QcAiError):
        qc_ai.doc_hinh(_kq('{"dat": "co le", "do_tin": 0.9}'), moc_giay=1.0)


def test_thieu_do_tin_thi_NO():
    """`do_tin` la thu quyet dinh co SINH VIEC SUA hay khong. Thieu no ma di
    tiep la de `_do_tin` tra 0.0 — im lang thanh mot con so."""
    with pytest.raises(ai.LuocDoSai):
        qc_ai.doc_hinh(_kq('{"dat": false, "ly_do": "x"}'), moc_giay=1.0)


def test_doc_hinh_doc_duoc_mot_phan_hoi_TUAN_THU():
    pq = qc_ai.doc_hinh(
        _kq('```json\n{"dat": false, "do_tin": 0.82, "ly_do": "cat giua dong tac"}\n```'),
        moc_giay=12.3456, ma_cat=["canh_0004", "canh_0003"], so_khung=2)
    assert pq["dat"] is False
    assert pq["do_tin"] == 0.82
    assert pq["moc_giay"] == 12.346
    assert pq["ma_cat"] == ["canh_0003", "canh_0004"]
    assert pq["ma_canh"] == "canh_0003"        # dai dien = ma dau tien da sap
    assert pq["so_khung"] == 2


def test_QC_HINH_khai_THI_GIAC_va_o_trong_bang_thao_tac():
    """⭐ Khac `HO_SO_NOI_DUNG` (khai thi giac ma khong gui khung nao), loi nhac
    nay gui khung JPEG that — nen khai `can_thi_giac=True` la khai DUNG."""
    assert ai.QC_HINH.can_thi_giac is True
    assert ai.QC_HINH in ai.THAO_TAC
    assert ai.THEO_MA["qc_hinh"] is ai.QC_HINH
    assert set(ai.QC_HINH.truong_bat_buoc) == {"dat", "do_tin"}


# ══════════════════════════════════════════════════════════════════════════════
#  §3. Loi nhac — bai hoc DO DUOC cua lane `fix-toc-do`
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_hinh_dua_KHUNG_JSON_va_cam_mang_cam_boc_lop():
    """🔴 `L_FIX_TOC_DO.md` R-05: loi nhac DUY NHAT cua ASV ke ten khoa bang van
    xuoi la loi nhac DUY NHAT bi tra ve sai hinh — 2/18 tra ve mot MANG, 1/18
    boc trong `{"objects": [...]}`. Loi nhac nay ra doi SAU phep do do."""
    m = qc_ai.loi_nhac_hinh(["AAAA"], moc_giay=3.0)
    he = m[0]["content"]
    assert '{"dat": true, "do_tin": 0.0, "ly_do": "..."}' in he
    assert "KHONG phai mang" in he
    assert "KHONG boc them lop nao" in he
    assert "khong them dau tieng Viet" in he


def test_loi_nhac_hinh_GIOI_THIEU_thu_tu_hai_anh():
    """⚠️ Cau hoi la ve mot CHUYEN TIEP. Model khong tra loi dung neu no khong
    biet anh nao truoc anh nao sau."""
    he = qc_ai.loi_nhac_hinh(["A", "B"], moc_giay=1.0)[0]["content"]
    assert "THU NHAT" in he and "TRUOC" in he
    assert "THU HAI" in he and "SAU" in he


def test_loi_nhac_hinh_gui_dung_so_anh_dang_image_url():
    m = qc_ai.loi_nhac_hinh(["A", "B"], moc_giay=1.0)
    anh = [p for p in m[1]["content"] if p["type"] == "image_url"]
    assert len(anh) == 2
    assert anh[0]["image_url"]["url"].startswith("data:image/jpeg;base64,A")


def test_khong_khung_nao_thi_NEM_chu_khong_hoi_suong():
    """Mot cau hoi ve chuyen tiep khong hoi duoc bang khong buc anh nao."""
    with pytest.raises(qc_ai.QcAiError):
        qc_ai.loi_nhac_hinh([], moc_giay=1.0)


def test_KHUNG_MOI_CHO_NOI_la_HAI():
    """⭐ Mot khung khong tra loi duoc mot cau hoi ve mot chuyen tiep."""
    assert qc_ai.KHUNG_MOI_CHO_NOI == 2
    bd = bdtg.BanDoThoiGian.tu_khoang([(0, 10), (30, 40)], thoi_luong_nguon=40.0)
    assert len(qc_ai.cac_cho_noi(bd)[0]["khung_s"]) == qc_ai.KHUNG_MOI_CHO_NOI


# ══════════════════════════════════════════════════════════════════════════════
#  §4. Chinh sach — TU VAN hay gate, va vong sua co DUNG
# ══════════════════════════════════════════════════════════════════════════════

def test_mac_dinh_la_TU_VAN_nen_KHONG_sinh_viec_sua():
    """🔴 Con so dat co nay nam o `L_QC_HINH.md` §4. Doi co la mot quyet dinh ve
    GIA: mot bao dong gia day ca mot vong sua (`edit_plan` + `content_process` +
    `voice_synthesis` + render) cho mot cho noi khong hong."""
    assert sc.QC_HINH_LA_TU_VAN is True
    xau = [{"ma_canh": "canh_0003", "ma_cat": ["canh_0003"],
            "dat": False, "do_tin": 0.95, "ly_do": "cat giua dong tac"}]
    assert sc.tu_qc_hinh(xau) == []
    assert not sc.lap_ke_hoach(qc_hinh=xau).can_sua


def test_TU_VAN_khong_co_nghia_la_GIAU_DI():
    """⭐ Phan quyet van phai di toi nguoi doc: artifact, `stage.outputs`, bao
    cao van hanh. "Tu van" = *khong tu dong tieu tien*, khong phai *khong ai
    duoc biet*."""
    ma = inspect.getsource(gdqa.chay)
    assert '"qc_hinh_khong_dat"' in ma      # -> stage.outputs (CSDL)
    assert '"hinh": hinh' in ma             # -> artifact (phan quyet day du)
    assert "hinh_la_tu_van" in ma           # -> va noi ro no dang tu van


def test_khi_GATE_thi_cat_sai_di_ve_edit_plan_voi_DUNG_don_vi(monkeypatch):
    """⚠️ Tat co cho RIENG phep kiem nay (khuon `L_FIX_TOC_DO.md` §Phep kiem):
    menh de o day la DINH TUYEN, khong phai chinh sach."""
    monkeypatch.setattr(sc, "QC_HINH_LA_TU_VAN", False)
    ke = sc.lap_ke_hoach(qc_hinh=[
        {"ma_canh": "canh_0003", "ma_cat": ["canh_0003"], "dat": False,
         "do_tin": 0.95, "ly_do": "nguoi bien mat giua chung",
         "moc_giay": 20.0}])
    assert ke.can_sua
    assert ke.giai_doan_sua() == {"edit_plan": ["canh_0003"]}
    assert ke.khiem_khuyet[0].bang_chung["moc_giay"] == 20.0


def test_do_tin_THAP_thi_GHI_LAI_nhung_KHONG_sinh_viec_sua(monkeypatch):
    """⭐ Mot model khong chac chan khong phai mot ly do de tra tien lam lai —
    va cung khong phai mot ly do de giau di."""
    monkeypatch.setattr(sc, "QC_HINH_LA_TU_VAN", False)
    ke = sc.lap_ke_hoach(qc_hinh=[
        {"ma_canh": "canh_0003", "ma_cat": ["canh_0003"], "dat": False,
         "do_tin": sc.DO_TIN_TOI_THIEU - 0.01}])
    assert ke.khiem_khuyet          # ghi lai
    assert not ke.can_sua           # nhung khong sinh viec
    assert ke.sang_dict()["khiem_khuyet"][0]["dang_tin"] is False


def test_cho_noi_DAT_khong_sinh_gi(monkeypatch):
    monkeypatch.setattr(sc, "QC_HINH_LA_TU_VAN", False)
    assert sc.tu_qc_hinh([{"ma_canh": "canh_0003", "ma_cat": ["canh_0003"],
                           "dat": True, "do_tin": 0.9}]) == []


def test_VONG_SUA_CO_TRAN_nen_mot_cho_noi_KHONG_SUA_DUOC_se_DUNG(monkeypatch):
    """🔴 **Cau hoi quan trong nhat cua vong sua nay: no co DUNG khong.**

    Mot cho noi hong co the KHONG sua duoc — hai canh hai ben von la hai canh
    khac nhau, va khong canh bi bo nao la cau noi. Khi do moi vong sua deu cho
    ra dung phan quyet cu, va mot vong khong co tran la mot hoa don khong day.

    ⇒ Tran nam o `VONG_SUA_TOI_DA` va no duoc dem bang SO DONG SO CAI (rang
      buoc `UNIQUE(run_id, ma_dispatch)`), khong bang mot bien trong bo nho.
    """
    monkeypatch.setattr(sc, "QC_HINH_LA_TU_VAN", False)
    xau = [{"ma_canh": "canh_0003", "ma_cat": ["canh_0003"], "dat": False,
            "do_tin": 0.95, "ly_do": "van hong"}]
    # Vong 0: sua duoc.
    assert sc.lap_ke_hoach(qc_hinh=xau, vong=0).con_vong() is True
    # Vong bang tran: van GHI khiem khuyet, nhung khong con vong nao.
    ke = sc.lap_ke_hoach(qc_hinh=xau, vong=sc.VONG_SUA_TOI_DA)
    assert ke.can_sua and ke.con_vong() is False
    assert ke.sang_dict()["con_vong"] is False


def test_vong_sua_MUOI_van_tay_canh_nen_lan_hoi_lai_la_mot_cau_hoi_KHAC():
    """🔴 M-07 cua duong GIONG, ap cho duong HINH: cung van tay = cung khoa =
    cung ket qua cache. Khong muoi thi "xem lai canh nay" tra ve **dung phan
    doan vua bi bao la sai** — mot hoa don khong co san pham."""
    a = hc.van_tay_canh("c1", "x", 2, 0.65, bat=1.0, ket=2.0)
    b = hc.van_tay_canh("c1", "x", 2, 0.65, bat=1.0, ket=2.0,
                        muoi="xem_lai1:cat giua dong tac")
    assert a != b
    # Va loi nhac phai MANG bang chung do, khong chi doi van tay.
    m = hc.loi_nhac_canh("c1", "x", 2, phan_hoi_qc="cat giua dong tac")
    assert "cat giua dong tac" in m[0]["content"]
    assert "VONG SUA" in m[0]["content"]
    # ⛔ Bang chung, khong phai LENH: khong duoc bao model "hay giu canh nay".
    assert "can nhac LAI" in m[0]["content"]
    assert "giu nguyen de xuat cu" in m[0]["content"]


def test_khong_co_phan_hoi_qc_thi_loi_nhac_KHONG_DOI():
    """⚠️ Duong binh thuong (khong vong sua) phai giu nguyen van tay VA loi
    nhac cu — neu khong, moi lan chay deu mat cache mot cach im lang."""
    assert (hc.loi_nhac_canh("c1", "x", 2)
            == hc.loi_nhac_canh("c1", "x", 2, phan_hoi_qc=""))
    assert (hc.van_tay_canh("c1", "x", 2, 0.65, bat=1.0, ket=2.0)
            == hc.van_tay_canh("c1", "x", 2, 0.65, bat=1.0, ket=2.0, muoi=""))


# ══════════════════════════════════════════════════════════════════════════════
#  §5. F-10 — van tay canh khoa theo `[bat, ket]`, khong theo `ma_canh`
# ══════════════════════════════════════════════════════════════════════════════

def test_F10_doi_bo_TACH_CANH_lam_van_tay_DOI():
    """🔴 F-10. `canh_0003` la mot SO THU TU, khong phai mot danh tinh.

    Doi bo tach (lane `ky-thuat`: `select=gt(scene,0.4)` -> `ContentDetector(35)`)
    sinh ra mot `canh_0003` o **mot khoang thoi gian khac han**, va ba truong
    con lai deu co the trung: `ngu_canh` rong (canh khong thoai), `so_khung` co
    dinh moi canh, `nguong` la hang so chinh sach.

    ⇒ Diem chot cu khop, va lan chay dung mot phan doan VLM ve MOT DOAN PHIM
      KHAC. Khong loi nao bao.
    """
    cu = hc.van_tay_canh("canh_0003", "", 2, 0.65, bat=20.0, ket=30.0)
    moi = hc.van_tay_canh("canh_0003", "", 2, 0.65, bat=24.5, ket=31.2)
    assert cu != moi, "van tay khong doi khi moc canh doi — F-10 quay lai"
    # Cung ma, cung moc => van la cung mot canh (cache van phai khop).
    assert cu == hc.van_tay_canh("canh_0003", "", 2, 0.65, bat=20.0, ket=30.0)


def test_F10_moc_lam_tron_mili_giay_de_cache_KHONG_truot_vo_co():
    """⛔ Moc canh la so thuc tu PySceneDetect; hai lan tinh co the lech o chu
    so thu 15. Mot van tay nhay theo nhieu dau cham dong la mot cache khong bao
    gio khop — tuc hoi (va tra tien) lai moi luot lat cat."""
    assert (hc.van_tay_canh("c1", "", 2, 0.65, bat=20.0, ket=30.0)
            == hc.van_tay_canh("c1", "", 2, 0.65, bat=20.0000001,
                               ket=29.9999999))


def test_nguoi_goi_THAT_truyen_moc_canh_vao_van_tay():
    """🔴 **26/09/2026 — nguoi goi do DA THOI VIEC** (B1 §9b).

    `edit_plan` ⛔ khong con goi VLM, nen ⛔ khong con ai goi `van_tay_canh` tren
    duong chay. Bai kiem ngay tren (`van_tay_canh` on dinh voi moc lech o chu so
    thu 15) van la hop dong cua `hieu_canh.py`, va `hieu_canh.py` van song —
    `HO_SO_NOI_DUNG` (duong chon giong) va `tools/do_llm_cong_asv.py` doc no.

    ⇒ Y dinh cu (*"mot ban va khong co nguoi di tren duong thi khong sua gi"*)
      duoc giu bang cach chot **ai la nguoi di tren duong hom nay**, thay vi chot
      mot nguoi goi da khong con.
    """
    from apps.auto_scan_video import giai_doan_ban_bien_tap as gd
    from apps.auto_scan_video import ho_so_noi_dung

    assert not hasattr(gd, "_doc_cac_canh"), (
        "edit_plan lai goi VLM — xem test_2025 §5")
    # `HO_SO_NOI_DUNG` la nguoi doc CON LAI cua `hieu_canh`.
    assert "loi_nhac_ho_so" in inspect.getsource(ho_so_noi_dung)


# ══════════════════════════════════════════════════════════════════════════════
#  §6. Rut khung — MOT ban sao cho ca hai nguoi goi
# ══════════════════════════════════════════════════════════════════════════════

def test_rut_khung_chi_co_MOT_ban_sao():
    """⛔ Hai doan ma rut khung se lech nhau ve tran thoi gian va ve cach bo mot
    khung hong.

    ⭐ **26/09/2026:** `edit_plan` ⛔ khong con rut khung nao (no do bang
       `blackdetect`/`freezedetect` tren ca tep), nen nguoi goi CON LAI la
       `qc_ai`. Y dinh giu nguyen: chi MOT ban sao, va tran thoi gian doc tu MOT
       nguon — chot chinh dieu do, ⛔ khong chot mot nguoi goi da khong con.
    """
    from apps.auto_scan_video import giai_doan_ban_bien_tap as gd

    assert "canh_mod.rut_khung(" in inspect.getsource(gdqa._soat_hinh)
    assert not hasattr(gd, "_rut_khung"), (
        "edit_plan rut khung lai — hai ban sao se lech nhau")
    # Tran thoi gian van la MOT hang so, o dung mot cho.
    assert canh_mod.CHO_RUT_KHUNG_S > 0
