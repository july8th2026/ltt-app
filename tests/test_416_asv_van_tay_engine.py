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
#: ⭐ RONG tu pha 18: QC da co engine that (`qc.PHIEN_BAN_QC`). Truoc do tap
#:    hop nay la `{"qc"}`, va chinh phep kiem duoi day buoc luot thay engine
#:    phai cap nhat cho nay — dung nhu no duoc thiet ke.
CON_DUNG_ENGINE_GIA: set[str] = set()


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


# ══════════════════════════════════════════════════════════════════════════════
#  N-23 — `temperature` ghim, va no PHAI o trong van tay
# ══════════════════════════════════════════════════════════════════════════════

def test_N23_nhiet_do_ghim_CHI_cho_chuyen_loi_thoai():
    """⛔ Ghim ho mot lan khac mot tham so doi dau ra = doi hanh vi cua ho trong
    im lang. `qc_ngu_nghia` thuoc lan bo cham — vang mat = giu nguyen mac dinh
    cong, dung khuon `MODEL_THEO_THAO_TAC`.
    """
    from apps.auto_scan_video import ai

    assert ai.nhiet_do_cho(ai.CHUYEN_LOI_THOAI) == 0.0
    assert ai.nhiet_do_cho(ai.QC_NGU_NGHIA) is None
    assert ai.nhiet_do_cho(ai.DOC_CANH) is None


def test_N23_doi_nhiet_do_thi_van_tay_CONTENT_PROCESS_PHAI_doi(monkeypatch):
    """🔴 Ve THU HAI cua N-23: mot tham so DOI DAU RA ma khong vao van tay thi
    cache tra ket qua cua nhiet do CU cho mot cau hinh MOI — im lang.

    ⛔ Bai kiem CA BA trang thai, vi *"khong khai"* va *"khai 0,0"* la hai thu
       khac nhau: gop chung lai la dung bay "hai trang thai mot gia tri".
    """
    from apps.auto_scan_video import ai

    def _vt():
        return thi_hanh.phien_ban_engine(pipeline.CONTENT_PROCESS)

    goc = _vt()
    monkeypatch.setitem(ai.NHIET_DO_THEO_THAO_TAC, ai.CHUYEN_LOI_THOAI.ma, 0.7)
    khac = _vt()
    monkeypatch.delitem(ai.NHIET_DO_THEO_THAO_TAC, ai.CHUYEN_LOI_THOAI.ma)
    khong_khai = _vt()

    assert goc != khac, "doi nhiet do ma van tay khong doi => cache tra ban cu"
    assert khong_khai not in (goc, khac), (
        "'khong gui temperature' phai la mot trang thai RIENG, khong duoc trung "
        "voi bat ky gia tri so nao")


def test_N23_goi_tinh_tien_GUI_dung_nhiet_do_da_ghim(monkeypatch):
    """⭐ Van tay va cu goi phai doc CUNG mot nguon — neu khong, van tay ghi mot
    dang va model nhan mot dang.

    ⛔ Va ben goi khai tuong minh thi van thang: `nhiet_do_cho` la MAC DINH,
       khong phai mot cai khoa.
    """
    from apps.auto_scan_video import ai

    thay: dict = {}

    def _gia(db, thao_tac, messages, **kw):
        thay[thao_tac.ma] = kw.get("temperature")
        return {"noi_dung": "{}", "provider": "p", "model": "m"}

    monkeypatch.setattr(ai, "goi", _gia)
    ai.goi_tinh_tien(None, None, ai.CHUYEN_LOI_THOAI, [], stage="s", item_key="i")
    assert thay[ai.CHUYEN_LOI_THOAI.ma] == 0.0

    ai.goi_tinh_tien(None, None, ai.QC_NGU_NGHIA, [], stage="s", item_key="i")
    assert thay[ai.QC_NGU_NGHIA.ma] is None, "⛔ khong duoc ghim ho lan bo cham"

    ai.goi_tinh_tien(None, None, ai.CHUYEN_LOI_THOAI, [], stage="s",
                     item_key="i", temperature=0.9)
    assert thay[ai.CHUYEN_LOI_THOAI.ma] == 0.9, "ben goi khai tuong minh phai thang"


def test_N23_ve_BA_ep_luoc_do_o_tang_GIAI_MA():
    """⭐ `response_format` ep bang khoa-theo-ma — DUNG cac ma da gui.

    Do duoc: 2/21 lo hong (chi ghim nhiet do) -> **0/20 lo, 188/188 doan**.
    ⛔ Bai nay chot HINH DANG, khong chot con so do.
    """
    from apps.auto_scan_video import long_tieng

    ld = long_tieng.luoc_do_phan_hoi([{"ma": "s1"}, {"ma": "s2"}])
    doan = ld["schema"]["properties"]["doan"]
    assert ld["type"] == "json_object"
    assert doan["required"] == ["s1", "s2"], "phai ep DU cac ma da gui"
    assert doan["additionalProperties"] is False, "⛔ khong cho bia them ma"
    # ⛔ `doan` phai la OBJECT — che do hong da do la model tra ve mot MANG.
    assert doan["type"] == "object"
    assert ld["schema"]["required"] == ["doan"]


def test_N23_doi_PHIEN_BAN_RANG_LUOC_DO_thi_van_tay_PHAI_doi(monkeypatch):
    """Bat/tat rang buoc luoc do DOI DAU RA ⇒ phai o trong van tay.

    ⛔ Thieu no thi cache tra ket qua cua cau hinh CU — dung ve thu hai N-23.
    """
    from apps.auto_scan_video import long_tieng

    goc = thi_hanh.phien_ban_engine(pipeline.CONTENT_PROCESS)
    monkeypatch.setattr(long_tieng, "PHIEN_BAN_RANG_LUOC_DO",
                        long_tieng.PHIEN_BAN_RANG_LUOC_DO + 1)
    assert thi_hanh.phien_ban_engine(pipeline.CONTENT_PROCESS) != goc


def test_N23_goi_tinh_tien_CHUYEN_luoc_do_xuong_than_request(monkeypatch):
    """⭐ `luoc_do` phai toi `dieu_phoi.goi(them={"response_format": ...})`.

    ⛔ Mot tham so duoc nhan roi bi bo giua duong la loai hong im lang nhat:
       ma doc nhu da bat, va hanh vi thi khong doi.
    """
    from apps.auto_scan_video import ai

    thay: dict = {}

    class _Kq:
        noi_dung = "{}"
        provider = "p"
        model = "m"
        su_dung = None

    def _gia(db, **kw):
        thay.update(kw)
        return _Kq()

    from platform_core.llm import dieu_phoi
    monkeypatch.setattr(dieu_phoi, "goi", _gia)
    ai.goi(None, ai.CHUYEN_LOI_THOAI, [], luoc_do={"type": "json_object"})
    assert thay.get("them", {}).get("response_format") == {"type": "json_object"}
