"""Van tay giai doan phai mang PHIEN BAN ENGINE — mon no tu pha 05, tra o pha 15.

## Vi sao tep nay ton tai

`thi_hanh.van_tay` ban pha 05 gom `(stage, contract, settings, dau_vao)`, va
docstring cua chinh no ghi mon no:

    "Ban pha 05 co du hinh dang dung nhung chua co `engine_id` va phien ban
     model… Pha 08+ **phai** them chung — thieu chung thi nang model len ban moi
     se dung lai ket qua cu, im lang."

Mon no do di qua **bay pha** ma khong ai tra. Khong phai vi ai quen doc: vi
khong co gi bao no thieu. Mot chu thich noi "phai lam X" khong lam X, va no
cung khong do duoc rang X chua duoc lam.

⭐ Cai lam no lo ra la mot phep kiem cua pha 15 — nang `PHIEN_BAN_KET_XUAT` roi
   chay lai, va ket qua **khong doi**. Tep nay bien phat hien do thanh mot chot
   cho **ca chuoi**, thay vi chi cho giai doan tinh co bi soi toi.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import pipeline, thi_hanh


class _RunGia:
    contract_version = "auto_scan_mvp_v1"
    settings: dict = {}


def test_MOI_giai_doan_deu_khai_mot_phien_ban_engine():
    """Chot theo TAP HOP giai doan, khong theo mot danh sach chep tay.

    ⇒ Them mot giai doan vao `pipeline.CHUOI` ma quen khai phien ban engine se
      lam phep kiem nay do NGAY, chu khong doi toi luc ai do nang engine len va
      thay ket qua khong doi.
    """
    thieu = [g.ten for g in pipeline.CHUOI
             if not thi_hanh.phien_ban_engine(g.ten)]
    assert thieu == [], (
        f"giai doan khong khai phien ban engine: {thieu} — nang engine cua "
        f"chung se KHONG lam moi cache, va ban va se khong bao gio chay")


#: Giai doan con dung ENGINE GIA. Chot bang TAP HOP, khong bang so luong: mot
#: luot sau thay engine gia bang engine that ma quen sua cho nay se lam phep
#: kiem do, va do la dieu ta muon — no buoc phien ban engine phai doi, tuc moi
#: ket qua gia da luu bi vo hieu thay vi duoc coi la cache hop le.
CON_DUNG_ENGINE_GIA = {"qc"}


def test_tap_hop_giai_doan_con_dung_ENGINE_GIA_dung_nhu_khai_bao():
    gia = {g.ten for g in pipeline.CHUOI
           if thi_hanh.phien_ban_engine(g.ten).startswith("gia/")}
    assert gia == CON_DUNG_ENGINE_GIA, (
        f"tap hop giai doan dung engine gia da doi: {gia}. Neu vua thay mot "
        f"engine gia bang engine that, cap nhat cho nay VA dam bao phien ban "
        f"engine moi khac `gia/{thi_hanh.PHIEN_BAN_ENGINE_GIA}`")


@pytest.mark.parametrize("ten", [g.ten for g in pipeline.CHUOI])
def test_doi_phien_ban_engine_thi_van_tay_PHAI_doi(ten, monkeypatch):
    """Chot dieu **thuc su** quan trong, chu khong chi rang chuoi khac rong.

    Mot ban cai dat tra ve mot chuoi hang so cho moi giai doan van qua duoc
    phep kiem ben tren, nhung khong bao ve gi ca. O day ta doi chinh gia tri
    va doi hoi van tay doi theo.
    """
    run = _RunGia()
    truoc = thi_hanh.van_tay(ten, run, {})
    # ⚠️ Chup ham GOC truoc khi va. Ban dau lambda goi
    #    `thi_hanh.phien_ban_engine(t)`, ma sau khi va thi ten do TRO VAO chinh
    #    lambda ⇒ RecursionError, va bay phep kiem do vi mot ly do khong lien
    #    quan gi toi thu dang duoc kiem.
    goc = thi_hanh.phien_ban_engine
    monkeypatch.setattr(thi_hanh, "phien_ban_engine", lambda t: goc(t) + "-x")
    sau = thi_hanh.van_tay(ten, run, {})
    assert truoc != sau, f"{ten}: doi phien ban engine ma van tay khong doi"


def test_hai_giai_doan_KHAC_nhau_khong_dung_chung_van_tay():
    """Chieu nguoc lai: van tay phai phan biet duoc giai doan.

    Neu khong, cache cua giai doan nay se tra loi cho giai doan kia.
    """
    run = _RunGia()
    vt = {g.ten: thi_hanh.van_tay(g.ten, run, {}) for g in pipeline.CHUOI}
    assert len(set(vt.values())) == len(vt), "co hai giai doan trung van tay"


def test_phien_ban_engine_KHONG_nap_ca_cay_module_luc_import():
    """`thi_hanh` duoc ca ba app vo thi hanh nap.

    Keo ca cay module engine vao luc import se bat mot worker chi chay lan `api`
    phai co du moi thu cua lan `gpu` — va no hong o luc **khoi dong worker**,
    tuc xa cho gay ra no nhat.
    """
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(thi_hanh.phien_ban_engine))
    o_dau_tep = [n for n in ast.walk(cay)
                 if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert o_dau_tep, "ham nay phai import ben trong, khong o dau tep"
    # Va cac module engine nang KHONG duoc nam o dau `thi_hanh.py`.
    dau = ast.parse(inspect.getsource(thi_hanh))
    ten_dau_tep: set[str] = set()
    for n in dau.body:          # chi than module, khong di vao trong ham
        if isinstance(n, ast.ImportFrom) and n.level == 1:
            ten_dau_tep |= {a.name for a in n.names}
    for nang in ("tach_tieng", "ban_ghi", "dich_thuat", "giong_noi", "ket_xuat"):
        assert nang not in ten_dau_tep, (
            f"`{nang}` bi import o dau `thi_hanh.py` — moi worker deu phai nap no")
