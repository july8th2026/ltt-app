"""Auto Scan Video V4 — so cai su dung da giao (`AsvUsage`), pha 06.

Bon tuyen bo dang chot, va mot trong so do la thu duy nhat co the lam khach mat
tien ma **khong lan chay nao hong**:

**§1 mot duong tien** — so cai la BANG CHUNG, khong phai nguon cong thu hai. Neu
     `tong_da_dung` cong ca no thi mot viec duoc tinh o ba noi: stage, item, so
     cai. `features._kiem_khong_tinh_hai_lan` da ton tai vi hai noi da la mot
     noi qua nhieu.

**§2 da giao ≠ da yeu cau** — `agent/executor.actual_cost` tinh tien theo thu da
     YEU CAU va da gay hai loi tien that trong du an nay. Mot ban ghi mang ten
     "da giao" phai chung minh duoc no da giao: co don vi do, co so luong.

**§3 dispatch mo ho** — ADR-001 D9. Mot lan gui mat ket noi SAU khi da gui la mot
     lan **khong biet** provider da chay chua. Thu lai mu la co the tra tien hai
     lan cho mot viec, va khong cach nao phat hien sau vi ca hai lan deu trong
     nhu that.

**§4 may chet giua ket qua va checkpoint** — ban ghi da giao va tien cua no phai
     cung song hoac cung khong. Mot khe cua so o day la mot khoan tien da tieu
     ma khong ai ghi lai.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.auto_scan_video import features, gia, pipeline, su_dung
from apps.auto_scan_video.tables import (RUN_DONE, AsvRun, AsvStage, AsvUsage,
                                         AsvWorkItem)

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Temp SQLite, cung khuon voi `tests/test_430`."""
    url = f"sqlite:///{(tmp_path / 'asv.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _run(db, *, owner="u1", held=1000) -> AsvRun:
    run = AsvRun(owner_id=owner, source_key="asv/u1/nguon/x.mp4",
                 settings={"giong_id": "Minh Đức"}, credit_held=held)
    db.add(run); db.flush()
    for g in pipeline.CHUOI:
        db.add(AsvStage(run_id=run.id, owner_id=owner, stage=g.ten))
    db.flush()
    return run


def _giao(**k) -> su_dung.SuDung:
    """Mot ban ghi DA GIAO hop le, cac truong deu doi duoc."""
    mac = dict(nang_luc="speech.ltt", app_chu="ltt_voice",
               trang_thai=su_dung.DA_GIAO, don_vi=su_dung.KY_TU,
               so_luong=1200.0, credit=12)
    mac.update(k)
    return su_dung.SuDung(**mac)


def _cay(ten: str) -> ast.Module:
    return ast.parse((APP / ten).read_text(encoding="utf-8"))


def _ten_ham_duoc_goi(cay: ast.AST) -> set[str]:
    """Ten cac ham duoc GOI, doc tu AST.

    ⛔ Khong quet chuoi. Mot phep quet chuoi bat ca doan van giai thich chinh no
       — loi do da xay ra bon lan trong du an nay, ke ca mot lan o chinh mot bo
       do duoc viet de chan no.
    """
    ra: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                ra.add(f.id)
            elif isinstance(f, ast.Attribute):
                ra.add(f.attr)
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Mot duong tien — so cai la bang chung, khong phai nguon cong
# ══════════════════════════════════════════════════════════════════════════════

def test_ghi_mot_luot_da_giao_cong_tien_vao_don_vi_viec(db):
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="seg-047",
                su_dung=_giao(credit=12))

    it = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS, "seg-047")
    assert it is not None and it.credit_actual == 12
    assert features.tong_da_dung(db, run) == 12


def test_hai_nang_luc_tren_cung_mot_item_thi_CONG_chu_khong_GAN(db):
    """🔴 Mot loi tien AM THAM neu viet nham thanh phep gan.

    Tu pha 11 mot don vi viec doc canh bang VLM **roi** sinh tieng bang TTS. Neu
    luot thu hai GAN thay vi CONG, luot dau bien mat khoi hoa don — lan chay van
    xong, video van dung, chi la khach tra it hon thu ta da mua. Khong phep kiem
    chuc nang nao thay duoc dieu do.
    """
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="seg-1",
                su_dung=_giao(nang_luc="vision.doc_canh", app_chu="ltt_llm",
                              don_vi=su_dung.TOKEN, so_luong=800, credit=5))
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="seg-1",
                su_dung=_giao(credit=12))

    it = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS, "seg-1")
    assert it.credit_actual == 17, "hai nang luc tren mot item phai CONG"
    assert len(su_dung.cac_dong(db, run, item_key="seg-1")) == 2


def test_tong_da_dung_KHONG_cong_them_so_cai(db):
    """⛔ Chot cua §1. Tong cua lan chay doc tu `credit_actual`, khong tu so cai.

    Neu ai do them mot phep cong bang nay vao `tong_da_dung`, con so o day nhan
    doi va phep kiem nay do ngay.
    """
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=30))
    assert features.tong_da_dung(db, run) == 30


def test_doi_soat_bat_duoc_mot_duong_ghi_credit_KHAC(db):
    """🔑 Thu ma phep doi soat thuc su san: mot lan `credit_actual = ...` viet tay.

    `su_dung.ghi` la duong duy nhat cong tien, nen no khong the tu lam lech. Cai
    lo ra o day la mot duong ghi thu hai — dung kieu ma mot pha sau se them vao
    mot cach vo hai, roi khong ai doi chieu lai voi bang chung.
    """
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=10))
    it = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS, "s1")
    it.credit_actual = 99          # duong ghi "khac"
    db.flush()

    with pytest.raises(su_dung.DoiSoatLech):
        su_dung.doi_soat(db, run)


def test_quyet_toan_TU_CHOI_chot_mot_con_so_khong_giai_thich_duoc(db):
    """Doi soat phai chay TRUOC khi tien duoc thu, khong phai sau."""
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=10))
    it = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS, "s1")
    it.credit_actual = 40
    db.flush()

    with pytest.raises(su_dung.DoiSoatLech):
        features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    assert run.status != RUN_DONE, "khong duoc chot khi bang chung khong khop"


# ══════════════════════════════════════════════════════════════════════════════
#  §2  DA GIAO khong phai DA YEU CAU
# ══════════════════════════════════════════════════════════════════════════════

def test_da_giao_ma_thieu_don_vi_do_thi_bi_tu_choi():
    with pytest.raises(su_dung.SuDungError):
        su_dung.SuDung(nang_luc="speech.ltt", app_chu="ltt_voice",
                       trang_thai=su_dung.DA_GIAO, so_luong=100, credit=5)


def test_da_giao_ma_so_luong_bang_khong_thi_bi_tu_choi():
    with pytest.raises(su_dung.SuDungError):
        _giao(so_luong=0)


@pytest.mark.parametrize("tt", [su_dung.TU_CHOI, su_dung.MO_HO])
def test_chua_chac_da_chay_thi_KHONG_duoc_mang_credit(tt):
    """🔴 Neu chung mang credit, tong cua lan chay cong ca nhung viec **chua chac
       da chay** — va no cong am tham."""
    with pytest.raises(su_dung.SuDungError):
        su_dung.SuDung(nang_luc="text.chat", app_chu="ltt_llm", trang_thai=tt,
                       credit=7)


def test_so_cai_KHONG_import_bang_gia():
    """⛔ ADR-001 D4: `actual` khong bao gio duoc tinh lai tu bang gia.

    Cach chac chan nhat de vi pham la nhap `gia` vao day roi "uoc tam" mot con
    so khi provider khong tra so lieu. Chan bang su vang mat.
    """
    cay = _cay("su_dung.py")
    nhap = {a.module or "" for a in ast.walk(cay) if isinstance(a, ast.ImportFrom)}
    nhap |= {n.name for a in ast.walk(cay) if isinstance(a, ast.Import)
             for n in a.names}
    assert not any(x.endswith("gia") for x in nhap), sorted(nhap)


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Lo mot phan, thu lai, cache, sua loi
# ══════════════════════════════════════════════════════════════════════════════

def test_lo_chay_mot_phan_chi_tinh_phan_DA_GIAO(db):
    """200 doan, 137 doan xong roi provider tu choi. Chi 137 doan duoc tinh."""
    run = _run(db)
    for i in range(137):
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS,
                    item_key=f"seg-{i:03d}", su_dung=_giao(credit=2))
    for i in range(137, 140):
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS,
                    item_key=f"seg-{i:03d}",
                    su_dung=su_dung.SuDung(nang_luc="speech.ltt",
                                           app_chu="ltt_voice",
                                           trang_thai=su_dung.TU_CHOI))
    assert features.tong_da_dung(db, run) == 137 * 2
    su_dung.doi_soat(db, run)


def test_don_vi_dung_lai_tu_cache_cong_ZERO(db):
    """Mot item da xong ma khong goi nang luc nao thi khong co dong so cai nao,
    va tien cua no khong doi."""
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=9))
    truoc = features.tong_da_dung(db, run)

    # Luot sau dung lai ket qua: khong goi provider, khong ghi so cai.
    su_dung.mo_don_vi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1")
    assert features.tong_da_dung(db, run) == truoc == 9


def test_thu_lai_KHONG_tinh_lai_don_vi_da_giao(db):
    """Yeu cau 5 cua pha 06: chay lai chi tinh phan viec MOI da giao.

    Doan 1 da xong o lan thu truoc; lan nay chi doan 2 chay that. Hoa don tang
    dung phan cua doan 2.
    """
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=10))
    features.thu_lai_giai_doan(db, run.id, run.owner_id, pipeline.VOICE_SYNTHESIS)

    # `s1` van con nguyen — dat lai GIAI DOAN khong xoa checkpoint don vi viec.
    assert features.tong_da_dung(db, run) == 10
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s2",
                su_dung=_giao(credit=7))
    assert features.tong_da_dung(db, run) == 17


def test_sua_loi_nham_MOT_don_vi_khong_lam_lai_ca_giai_doan(db):
    """Yeu cau 5, chieu 'repair': mot don vi hong duoc lam lai, phan con lai giu."""
    run = _run(db)
    for k in ("s1", "s2", "s3"):
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key=k,
                    su_dung=_giao(credit=5))
    # `s2` hong va duoc lam lai — mot dong so cai MOI, khong xoa dong cu.
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s2",
                su_dung=_giao(credit=5))

    assert features.tong_da_dung(db, run) == 20, "3 don vi + 1 lan lam lai"
    assert len(su_dung.cac_dong(db, run, item_key="s2")) == 2
    su_dung.doi_soat(db, run)


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Dispatch mo ho (ADR-001 D9)
# ══════════════════════════════════════════════════════════════════════════════

def _mo_ho(**k) -> su_dung.SuDung:
    mac = dict(nang_luc="speech.ltt", app_chu="ltt_voice",
               trang_thai=su_dung.MO_HO, ma_dispatch="disp-1")
    mac.update(k)
    return su_dung.SuDung(**mac)


def test_mo_ho_CHAN_duong_thu_lai_giai_doan(db):
    """⛔ Cot tru cua §3. Thu lai mot giai doan con dispatch mo ho la co the tra
       tien lan hai cho dung mot viec."""
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_mo_ho())

    with pytest.raises(features.AsvError):
        features.thu_lai_giai_doan(db, run.id, run.owner_id,
                                   pipeline.VOICE_SYNTHESIS)


def test_mo_ho_o_giai_doan_KHAC_khong_chan_giai_doan_nay(db):
    """Chan phai dung pham vi: mot lan gui mo ho o `content_process` khong duoc
    khoa chan `voice_synthesis`."""
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.CONTENT_PROCESS, item_key="c1",
                su_dung=_mo_ho())
    ra = features.thu_lai_giai_doan(db, run.id, run.owner_id,
                                    pipeline.VOICE_SYNTHESIS)
    assert ra["run_id"] == run.id


def test_giai_quyet_mo_ho_DA_CHAY_thi_tinh_tien_va_mo_khoa(db):
    run = _run(db)
    dong = su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                       su_dung=_mo_ho())
    su_dung.giai_quyet_mo_ho(db, dong, da_chay=True, don_vi=su_dung.KY_TU,
                             so_luong=900, credit=8, boi="ho-tro:an")

    assert features.tong_da_dung(db, run) == 8
    assert su_dung.cac_mo_ho(db, run) == []
    su_dung.doi_soat(db, run)
    features.thu_lai_giai_doan(db, run.id, run.owner_id, pipeline.VOICE_SYNTHESIS)


def test_giai_quyet_mo_ho_KHONG_CHAY_thi_khong_tinh_tien(db):
    run = _run(db)
    dong = su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                       su_dung=_mo_ho())
    su_dung.giai_quyet_mo_ho(db, dong, da_chay=False, boi="ho-tro:an")

    assert dong.trang_thai == su_dung.TU_CHOI
    assert features.tong_da_dung(db, run) == 0
    assert su_dung.cac_mo_ho(db, run) == []


def test_giai_quyet_DA_CHAY_van_doi_don_vi_do(db):
    """Mot lan giai quyet khong duoc mem hon mot lan ghi. Cung bo luat."""
    run = _run(db)
    dong = su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                       su_dung=_mo_ho())
    with pytest.raises(su_dung.SuDungError):
        su_dung.giai_quyet_mo_ho(db, dong, da_chay=True, credit=8)


def test_KHONG_co_duong_TU_DONG_nao_goi_giai_quyet_mo_ho():
    """🔑 Diem cot loi cua ADR-001 D9, va no chi cuong che duoc bang su vang mat.

    Mot lan gui mo ho ma he thong tu ket luan la mot lan he thong doan bang tien
    cua khach. Ham `giai_quyet_mo_ho` chi duoc goi tu ben ngoai (giao dien ho tro,
    hoac test), khong tu bat cu duong chay tu dong nao trong app.
    """
    goi = set()
    for t in sorted(APP.glob("*.py")):
        goi |= _ten_ham_duoc_goi(_cay(t.name))
    assert "giai_quyet_mo_ho" not in goi, (
        "co mot duong TU DONG goi giai_quyet_mo_ho - xem ADR-001 D9")


# ══════════════════════════════════════════════════════════════════════════════
#  §5  May chet giua ket qua da giao va checkpoint
# ══════════════════════════════════════════════════════════════════════════════

def test_cung_ma_dispatch_ghi_hai_lan_bi_TU_CHOI(db):
    """Kich ban: provider tra ket qua, ta ghi so cai, may chet truoc khi
    checkpoint. Luot sau phat lai **cung** ma dispatch."""
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(ma_dispatch="prov-abc", credit=12))
    with pytest.raises(su_dung.DaGhiRoi):
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                    su_dung=_giao(ma_dispatch="prov-abc", credit=12))
    assert features.tong_da_dung(db, run) == 12, "khong duoc tinh tien hai lan"


def test_lan_ghi_bi_tu_choi_KHONG_cuon_theo_nhung_gi_da_ghi_truoc(db):
    """🔴 Loi that trong ban dau cua pha nay: doan bat `IntegrityError` goi
       `db.rollback()`, va no cuon **ca giao dich** — moi dong so cai da ghi
       truoc do trong cung luot dispatch bien mat.

    Mot rang buoc lam dung viec cua no khong duoc pha huy cong viec cua nguoi goi.
    """
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s0",
                su_dung=_giao(ma_dispatch="prov-0", credit=4))
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(ma_dispatch="prov-1", credit=6))
    with pytest.raises(su_dung.DaGhiRoi):
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                    su_dung=_giao(ma_dispatch="prov-1", credit=6))

    assert features.tong_da_dung(db, run) == 10, "hai luot truoc phai con nguyen"
    assert len(su_dung.cac_dong(db, run)) == 2


def test_khong_co_ma_dispatch_thi_moi_lan_la_mot_lan_gui_KHAC(db):
    """⚠️ Pham vi cua loi hua chong-tinh-hai-lan, noi thang ra.

    Khong dua ma dispatch thi `ghi` sinh mot ma moi, va hai lan ghi la hai lan
    tinh tien. Do la **dung**: mot lan gui khong co danh tinh thi khong ai chung
    minh duoc no trung voi lan nao. Phep kiem nay ton tai de khong ai doc rang
    buoc kia rong hon thuc te.
    """
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=5))
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=5))
    assert features.tong_da_dung(db, run) == 10


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Mot hold duy nhat — job con khong giu tien cua khach
# ══════════════════════════════════════════════════════════════════════════════

def test_app_KHONG_BAO_GIO_dung_submit_with_credit():
    """Yeu cau 2 cua pha 06. Tien duoc giu MOT lan tren `AsvRun`; moi job con di
    qua `jobs.submit` va chay duoi ngan sach cua run cha.

    ⛔ Mot job con tu giu credit se tao mot hold thu hai cho cung mot lan chay —
       khach thay tien bi giu hai lan cho mot video.
    """
    goi = set()
    for t in sorted(APP.glob("*.py")):
        goi |= _ten_ham_duoc_goi(_cay(t.name))
    assert "submit_with_credit" not in goi


def test_chi_MOT_cho_trong_app_goi_giu_cho():
    """Va do la `features.tao_run`. Hai cho giu tien la hai cau tra loi cho cau
    hoi 'lan chay nay giu bao nhieu'."""
    cho = []
    for t in sorted(APP.glob("*.py")):
        cay = _cay(t.name)
        for n in ast.walk(cay):
            # 🔑 So CA CHU THE, khong chi ten ham. `cache_chung.giu_cho` (23/09)
            #    giu mot KHOA — lease "mot tinh, cac ben kia cho" — va khong
            #    cham mot dong nao. Bat bien o day la "chi MOT cho giu TIEN".
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "giu_cho"
                    and isinstance(n.func.value, ast.Name)
                    and n.func.value.id == "credit"):
                cho.append(t.name)
    assert cho == ["features.py"], cho


def test_so_cai_khong_cham_toi_so_credit_cua_khach():
    """So cai ghi chi phi DA DO; no khong tru tien. Viec tru tien la cua
    `features.quyet_toan`, mot lan, o cuoi."""
    goi = _ten_ham_duoc_goi(_cay("su_dung.py"))
    for cam in ("tru", "nap", "hoan_phi", "giu_cho", "cap_tay"):
        assert cam not in goi, f"su_dung.py goi credit.{cam}"


# ══════════════════════════════════════════════════════════════════════════════
#  §7  Hai nguoi dung
# ══════════════════════════════════════════════════════════════════════════════

def test_so_ke_cua_nguoi_nay_khong_thay_dong_cua_nguoi_kia(db):
    a = _run(db, owner="u1")
    b = _run(db, owner="u2")
    su_dung.ghi(db, a, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=10))
    su_dung.ghi(db, b, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=99))

    assert su_dung.so_ke(db, a)["tong"]["credit"] == 10
    assert su_dung.so_ke(db, b)["tong"]["credit"] == 99
    assert features.tong_da_dung(db, a) == 10
    assert {d.owner_id for d in su_dung.cac_dong(db, a)} == {"u1"}


def test_cung_ma_dispatch_o_HAI_lan_chay_khac_nhau_thi_hop_le(db):
    """Rang buoc la `(run_id, ma_dispatch)`, khong phai `ma_dispatch` toan cuc.

    Hai lan chay cua hai khach co the nhan cung mot ma tu hai provider khac nhau;
    khoa toan cuc se lam lan chay thu hai that bai vi mot ly do khong lien quan
    gi den no.
    """
    a = _run(db, owner="u1")
    b = _run(db, owner="u2")
    su_dung.ghi(db, a, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(ma_dispatch="x", credit=3))
    su_dung.ghi(db, b, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(ma_dispatch="x", credit=4))
    assert features.tong_da_dung(db, a) == 3
    assert features.tong_da_dung(db, b) == 4


# ══════════════════════════════════════════════════════════════════════════════
#  §8  Cua chan ngan sach truoc khi tieu
# ══════════════════════════════════════════════════════════════════════════════

def test_cua_chan_cho_lo_hong_TRUOC_KHI_bat_dau_chu_khong_o_giua(db):
    """⭐ Kiem CA LO. Kiem tung cai thi lo chay toi doan 137 roi dung — khach da
       tra cho 136 doan cua mot san pham khong dung duoc."""
    run = _run(db, held=100)
    with pytest.raises(features.AsvError):
        su_dung.cua_chan_cho_lo(db, run, uoc_moi_don_vi=2, so_don_vi=200)
    # Vua du thi qua.
    su_dung.cua_chan_cho_lo(db, run, uoc_moi_don_vi=2, so_don_vi=50)


def test_ghi_su_dung_KHONG_bi_ngan_sach_tu_choi(db):
    """⛔ Tien da tieu roi. Khong ghi lai chi lam no bien mat khoi so sach chu
       khong lam no chua tieu — va mot so cai giau bot chi tieu la mot so cai vo
       dung."""
    run = _run(db, held=5)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=50))
    assert features.tong_da_dung(db, run) == 50, "phai ghi that, du vuot hold"

    # ⭐ Mot lan chay DA GIAO, 10 phut nguon: gia phang 100 credit tren mot hold 5.
    #    (Khong dung hai su that o `_dat_thoi_luong_nguon` thi `quyet_toan` di duong
    #     "khong co hien vat ⇒ thu 0" va bai nay xanh ma khong cham phep `min`.)
    _dat_thoi_luong_nguon(db, run, 600.0)
    assert gia.tinh_credit(600.0) > 5, "ca thu nay khong con y nghia"

    # Va tran tren van la muc da giu khi chot.
    features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    assert run.credit_actual == 5


# ══════════════════════════════════════════════════════════════════════════════
#  §9  So ke cho quan sat va giao dien (yeu cau 8)
# ══════════════════════════════════════════════════════════════════════════════

def test_so_ke_gom_theo_nang_luc_va_giu_don_vi_do(db):
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.CONTENT_PROCESS, item_key="c1",
                su_dung=_giao(nang_luc="text.chat", app_chu="ltt_llm",
                              don_vi=su_dung.TOKEN, so_luong=1200, credit=6))
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=12))
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s2",
                su_dung=_mo_ho(ma_dispatch="d2"))

    ke = su_dung.so_ke(db, run)
    theo = {m["nang_luc"]: m for m in ke["theo_nang_luc"]}
    assert theo["text.chat"]["don_vi"] == su_dung.TOKEN
    assert theo["text.chat"]["so_luong"] == 1200
    assert theo["speech.ltt"]["credit"] == 12
    assert ke["tong"]["credit"] == 18
    assert ke["mo_ho_chua_giai_quyet"] == 1


def test_so_ke_KHONG_cong_hai_don_vi_do_khac_nhau_vao_mot_o(db):
    """Mot bang tom tat khong duoc lam phep do. Cong 1.200 token voi 12 giay la
    mot phep cong vo nghia, nen o don vi bo trong thay vi im lang lay cai cuoi."""
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.CONTENT_PROCESS, item_key="c1",
                su_dung=_giao(nang_luc="text.chat", app_chu="ltt_llm",
                              don_vi=su_dung.TOKEN, so_luong=1200, credit=6))
    su_dung.ghi(db, run, stage=pipeline.CONTENT_PROCESS, item_key="c2",
                su_dung=_giao(nang_luc="text.chat", app_chu="ltt_llm",
                              don_vi=su_dung.GIAY, so_luong=12, credit=1))
    theo = {m["nang_luc"]: m for m in su_dung.so_ke(db, run)["theo_nang_luc"]}
    assert theo["text.chat"]["don_vi"] == ""


def test_bang_so_cai_khong_mang_cot_cua_mot_hang_doi():
    """Cung luat voi `AsvWorkItem` (ADR-V4-002 D-V4-11): `platform_core.jobs` la
    hang doi SSOT duy nhat, va mot bang moi khong duoc lang le thanh cai thu hai."""
    cot = {c.name for c in AsvUsage.__table__.columns}
    cam = {"claimed_by", "worker_id", "locked_by", "lease_until",
           "visible_at", "available_at", "priority", "heartbeat_at"}
    assert not (cot & cam), sorted(cot & cam)


def test_moi_dong_so_cai_deu_neo_vao_mot_don_vi_viec_co_that(db):
    """`doi_soat` phai bat duoc mot dong mo coi — bang chung tro toi mot item
    khong ton tai la bang chung khong kiem duoc."""
    run = _run(db)
    db.add(AsvUsage(run_id=run.id, owner_id=run.owner_id,
                    stage=pipeline.VOICE_SYNTHESIS, item_key="ma-khong-co",
                    nang_luc="speech.ltt", app_chu="ltt_voice",
                    trang_thai=su_dung.DA_GIAO, don_vi=su_dung.KY_TU,
                    so_luong=10, credit=1, ma_dispatch="d", ghi_chu={}))
    db.flush()
    with pytest.raises(su_dung.DoiSoatLech):
        su_dung.doi_soat(db, run)


def test_khong_con_don_vi_viec_mo_coi_sau_mot_luot_ghi_binh_thuong(db):
    """Chieu khang dinh cua phep kiem tren: `ghi` tu mo don vi viec, nen duong
    binh thuong khong bao gio sinh ra dong mo coi."""
    run = _run(db)
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=3))
    su_dung.doi_soat(db, run)
    assert db.query(AsvWorkItem).count() == 1


# ══════════════════════════════════════════════════════════════════════════════
#  §10  Tich hop: so cai + so credit THAT cua nen tang, mot lan chay tron ven
# ══════════════════════════════════════════════════════════════════════════════
#
# Cac muc tren dung `AsvRun` dung tay. Muc nay di qua `features.tao_run` — tuc
# qua `platform_core.credit.giu_cho` that — de chung minh "MOT hold duy nhat"
# bang CHUC NANG, khong chi bang mot phep quet AST.

def test_ca_luot_chay_chi_giu_credit_MOT_lan_va_quyet_toan_dung_so_do_duoc(db):
    """Duong tien day du: nap -> giu -> ghi so cai -> doi soat -> quyet toan.

    🔑 Bon dieu duoc chot cung mot luc, va chung chi co nghia khi di CUNG nhau:

        1. `tao_run` giu credit dung MOT lan, tren `run.id`
        2. moi luot goi nang luc chi cong vao `AsvWorkItem.credit_actual`
        3. `quyet_toan` doi soat TRUOC khi thu, roi thu dung tong DO DUOC
        4. phan khong dung duoc HOAN — khach khong tra cho thu khong chay
    """
    from platform_core import credit

    from apps.auto_scan_video import pipeline as pl

    credit.nap(db, "u-tich-hop", 1000)
    db.commit()
    truoc = credit.so_du(db, "u-tich-hop")

    run = features.tao_run(db, owner_id="u-tich-hop",
                           source_key="asv/u/nguon/a.mp4",
                           settings={"giong_id": "Minh Đức"}, uoc_luong_credit=200)
    db.commit()

    # (1) dung MOT lan giu, va giu tren chinh `run.id`
    #
    # 🔑 Dem BUT TOAN giu cho, khong chi doc tong. `so_da_giu` cong moi but toan
    #    `CREDIT_HOLD` cua `job_id`, nen mot lan giu 200 va hai lan giu 100 cho
    #    ra **cung mot so**. Cai ta muon chot la "chi mot chu so huu tinh tien",
    #    va dieu do chi doc duoc o SO LUONG but toan.
    from platform_core.models import CreditEntry
    but_toan = db.query(CreditEntry).filter(
        CreditEntry.job_id == run.id,
        CreditEntry.kind == "hold").all()
    assert len(but_toan) == 1, f"phai co DUNG mot but toan giu cho, co {len(but_toan)}"
    assert credit.so_da_giu(db, run.id) == 200
    assert credit.so_du(db, "u-tich-hop") == truoc - 200

    # (2) ba luot goi nang luc that (fake provider), tong do duoc = 47
    for khoa, c in (("seg-1", 20), ("seg-2", 15), ("seg-3", 12)):
        su_dung.ghi(db, run, stage=pl.VOICE_SYNTHESIS, item_key=khoa,
                    su_dung=_giao(credit=c, ma_dispatch=f"prov-{khoa}"))
    # mot luot bi provider tu choi: khong dong nao
    su_dung.ghi(db, run, stage=pl.VOICE_SYNTHESIS, item_key="seg-4",
                su_dung=su_dung.SuDung(nang_luc="speech.ltt", app_chu="ltt_voice",
                                       trang_thai=su_dung.TU_CHOI,
                                       ma_dispatch="prov-seg-4"))
    db.flush()

    assert features.tong_da_dung(db, run) == 47
    su_dung.doi_soat(db, run)

    # (3) 🔑 **Tu 25/09/2026 so THU khong con la tong do duoc — gia PHANG.**
    #
    #     `media_prepare` la noi do dai video nguon duoc do, va gia la
    #     `10 credit x so phut nguon` (`gia.tinh_credit`). Nen bai nay dat mot ho
    #     so soi THAT vao day thay vi de `quyet_toan` roi ve duong lui.
    #
    # ⭐ Va do dai duoc chon co chu dinh de gia phang (50) **khac** tong do duoc
    #    (47): hai con so bang nhau thi bai nay khong phan biet duoc "thu theo gia
    #    phang" voi "thu theo so cai".
    _dat_thoi_luong_nguon(db, run, 300.0)
    phai_thu = gia.tinh_credit(300.0)
    assert phai_thu != 47, "ca thu nay khong con phan biet duoc hai cong thuc"

    # (4) quyet toan thu dung gia phang, hoan phan du
    features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    db.commit()

    assert run.credit_actual == phai_thu

    # ⚠️ `so_da_giu` KHONG ve 0 sau quyet toan, va do la dung: no cong moi but
    #    toan `CREDIT_HOLD` — mot **so sach lich su**, khong phai "con giu bao
    #    nhieu". Phep kiem dau tien toi viet o day khang dinh no ve 0 va do la
    #    toi doc sai hop dong cua nen tang chu khong phai nen tang sai.
    assert credit.so_da_giu(db, run.id) == 200
    assert credit._da_ket_so(db, run.id), "quyet toan phai de lai but toan ket so"

    # ⭐ Bang chung THAT rang phan khong dung da duoc hoan nam o SO DU.
    assert credit.so_du(db, "u-tich-hop") == truoc - phai_thu, (
        "phan khong dung phai duoc hoan — khach khong tra cho thu khong chay")

    # 🔑 **So cai VAN ghi dung chi phi noi bo, va no khac so da thu.** Do la diem
    #    quan trong nhat cua bai nay sau 25/09: gia phang doi thu duoc THU, ⛔ khong
    #    doi thu duoc DO. Nguoi van hanh van doc duoc 47 de biet lan chay nay dot
    #    bao nhieu, trong khi khach chi tra gia phang.
    ke = su_dung.so_ke(db, run)
    assert ke["tong"]["credit"] == 47
    assert ke["tong"]["da_giao"] == 3 and ke["tong"]["tu_choi"] == 1


def _dat_thoi_luong_nguon(db, run, giay: float) -> None:
    """Dung HAI su that ma luat thu tien (25/09/2026) doi hoi:

        `media_prepare.thoi_luong`   do dai video NGUON -> `gia.tinh_credit`
        `render.khoa_asset` co .mp4  HIEN VAT -> co gi giao cho khach khong (N-57)

    ⚠️ Thieu mot trong hai thi `quyet_toan` roi ve mot duong KHAC — duong lui theo
       `credit_held`, hoac duong *"khong co hien vat ⇒ thu 0"*. Ca hai deu hop le,
       nhung chung ⛔ khong phai duong dang duoc kiem, va mot bai xanh nho mot duong
       khac la mot bai xanh gia.
    """
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    features.cap_nhat_giai_doan(db, gd, outputs={"stage": pipeline.MEDIA_PREPARE,
                                                 "thoi_luong": float(giay)})
    rd = features.giai_doan_theo_ten(db, run.id, pipeline.RENDER)
    features.cap_nhat_giai_doan(
        db, rd, status=STAGE_SUCCEEDED,
        outputs={"stage": pipeline.RENDER, "dat": True,
                 "khoa_asset": [f"asv/{run.owner_id}/{run.id}/long-tieng.mp4"]})
    db.flush()


def test_hai_khach_chay_cung_luc_khong_cham_vao_so_cua_nhau(db):
    """Cach ly chu so huu o duong tien THAT, khong chi o truy van so cai.

    ⭐ Hai video co do dai KHAC nhau (gia phang ⇒ hai so tien khac nhau), nen mot
       lan roi so cua nguoi nay sang nguoi kia se lo ra thanh mot con so sai — chu
       khong bi che bang hai con so tinh co bang nhau.
    """
    from platform_core import credit

    from apps.auto_scan_video import pipeline as pl

    for u in ("u-a", "u-b"):
        credit.nap(db, u, 500)
    db.commit()

    ra = features.tao_run(db, owner_id="u-a", source_key="asv/a/x.mp4",
                          settings={"giong_id": "Minh Đức"}, uoc_luong_credit=100)
    rb = features.tao_run(db, owner_id="u-b", source_key="asv/b/y.mp4",
                          settings={"giong_id": "Minh Đức"}, uoc_luong_credit=100)
    db.commit()

    _dat_thoi_luong_nguon(db, ra, 60.0)        # 1 phut
    _dat_thoi_luong_nguon(db, rb, 540.0)       # 9 phut
    thu_a, thu_b = gia.tinh_credit(60.0), gia.tinh_credit(540.0)
    assert thu_a != thu_b

    su_dung.ghi(db, ra, stage=pl.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=10))
    su_dung.ghi(db, rb, stage=pl.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=90))
    db.flush()

    features.quyet_toan(db, ra, trang_thai_cuoi=RUN_DONE)
    features.quyet_toan(db, rb, trang_thai_cuoi=RUN_DONE)
    db.commit()

    assert credit.so_du(db, "u-a") == 500 - thu_a
    assert credit.so_du(db, "u-b") == 500 - thu_b


def test_vuot_hold_thi_khach_chi_tra_TOI_DA_phan_da_giu(db):
    """⛔ Bat bien co san cua nen tang, va so cai khong duoc pha no.

    `su_dung.ghi` co y KHONG tu choi ghi mot viec da giao vi ly do ngan sach —
    tien da tieu roi, giau no di chi lam so sach sai. Nhung `quyet_toan` van
    chan tren o muc da giu: phan vuot la ta chiu, khong phai khach.
    """
    from platform_core import credit

    from apps.auto_scan_video import pipeline as pl

    credit.nap(db, "u-vuot", 500)
    db.commit()
    run = features.tao_run(db, owner_id="u-vuot", source_key="asv/u/x.mp4",
                           settings={"giong_id": "Minh Đức"}, uoc_luong_credit=30)
    db.commit()

    su_dung.ghi(db, run, stage=pl.VOICE_SYNTHESIS, item_key="s1",
                su_dung=_giao(credit=90))
    db.flush()
    assert features.tong_da_dung(db, run) == 90, "so cai phai ghi that"

    # ⭐ Tu 25/09 chan tren duoc thu bang GIA PHANG vuot hold, ⛔ khong bang so cai:
    #    mot video 60 phut o day cho gia phang 600 credit tren mot hold 30. (Khong
    #    dat do dai thi `quyet_toan` roi ve duong lui va bai nay xanh ma khong he
    #    cham vao phep `min` dang duoc kiem.)
    _dat_thoi_luong_nguon(db, run, 3600.0)
    assert gia.tinh_credit(3600.0) > 30, "ca thu nay khong con y nghia"

    features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
    db.commit()
    assert run.credit_actual == 30, "chan tren o muc da giu"
    assert credit.so_du(db, "u-vuot") == 500 - 30
