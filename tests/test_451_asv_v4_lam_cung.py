"""Pha 25 — LAM CUNG cho pilot: migration, IDOR, che du lieu, han luu, gioi han.

## Phep kiem quan trong nhat o day khong kiem san pham, no kiem CACH TRIEN KHAI

Bo test dung `Base.metadata.create_all()`. May chu chay `alembic upgrade head`.
Hai duong do co the lech nhau **ma khong ai biet**: mot cot them vao `tables.py`
khong kem migration se xanh o moi luot gate va hong o lan deploy dau tien, voi
mot thong bao ve mot cot khong ton tai.

⇒ Muc A dung mot CSDL rong, chay migration that, roi doi chieu voi model. Kho nay
  chua tung co phep kiem do — cho bat ky app nao.

## Vi sao IDOR duoc kiem lai o day du pha 05 da kiem

Pha 05 kiem `asv_run`/`asv_stage`/`asv_asset`. Pha 06 va pha 19 them **hai bang
moi** (`asv_work_item`, `asv_usage`) mang du lieu cua khach — va mot bang moi la
mot be mat moi. Muc B doi chieu ca sau loai doi tuong cua V4, khong phai ba.
"""
from __future__ import annotations

import json

import pytest

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (  # noqa: F401
    _chay_het_hang_doi, _tao_run, asr_gia, db, dich_gia, giong_gia, kho_tam)

NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}


# ══════════════════════════════════════════════════════════════════════════════
#  A. MIGRATION va MODEL phai noi cung mot chuyen
# ══════════════════════════════════════════════════════════════════════════════

def _lech_sau_migration(tmp_path) -> tuple[list, list]:
    """Chay `alembic upgrade head` tren CSDL rong roi doi chieu voi model.

    Tra ve `(lech_asv, lech_khac)`.
    """
    import os

    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.frontend_bundle import REPO_ROOT
    from platform_core.registry import load_app_tables

    duong = (tmp_path / "sau_migration.db").as_posix()
    cu = os.environ.get("LTT_DATABASE_URL")
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{duong}"
    try:
        load_app_tables()
        import apps.auto_scan_video.tables  # noqa: F401
        dbmod.reset_engine()

        cfg = Config(str(REPO_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{duong}")
        command.upgrade(cfg, "head")

        with dbmod.get_engine().connect() as ket:
            ctx = MigrationContext.configure(ket)
            lech = compare_metadata(ctx, dbmod.Base.metadata)
    finally:
        if cu is None:
            os.environ.pop("LTT_DATABASE_URL", None)
        else:
            os.environ["LTT_DATABASE_URL"] = cu
        dbmod.reset_engine()

    asv = [repr(x) for x in lech if "asv" in repr(x)]
    khac = [repr(x) for x in lech if "asv" not in repr(x)]
    return asv, khac


def test_MIGRATION_va_MODEL_khong_lech_o_bang_ASV(tmp_path):
    """🔑 May chu chay migration; bo test chay `create_all`. Neu hai duong lech
    nhau thi moi luot gate deu xanh va lan deploy dau tien hong.

    ⛔ Chi chot phan ASV. Cac bang khac cua nen tang co san mot so khac biet
       hinh thuc tren SQLite (BIGINT vs BigInteger, mot vai FK) — do la no cua
       nen tang, va gop no vao day se lam phep kiem nay do vi mot ly do khong
       lien quan gi den Auto Scan, roi bi ai do tat di.
    """
    asv, _khac = _lech_sau_migration(tmp_path)
    assert asv == [], "migration va model lech nhau o bang ASV:\n" + "\n".join(asv)


def test_MOI_bang_ASV_deu_co_trong_CSDL_sau_migration(tmp_path):
    """⛔ Mot bang chi ton tai trong `tables.py` la mot bang khong co o may chu."""
    import os

    from sqlalchemy import create_engine, inspect

    from alembic import command
    from alembic.config import Config

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.frontend_bundle import REPO_ROOT
    from platform_core.registry import load_app_tables

    duong = (tmp_path / "b.db").as_posix()
    cu = os.environ.get("LTT_DATABASE_URL")
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{duong}"
    try:
        load_app_tables()
        import apps.auto_scan_video.tables  # noqa: F401
        dbmod.reset_engine()
        cfg = Config(str(REPO_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{duong}")
        command.upgrade(cfg, "head")
        co = set(inspect(create_engine(f"sqlite:///{duong}")).get_table_names())
        can = {t for t in dbmod.Base.metadata.tables if t.startswith("asv_")}
    finally:
        if cu is None:
            os.environ.pop("LTT_DATABASE_URL", None)
        else:
            os.environ["LTT_DATABASE_URL"] = cu
        dbmod.reset_engine()

    assert can, "khong tim thay bang ASV nao trong model"
    assert can <= co, f"bang ASV thieu migration: {sorted(can - co)}"


# ══════════════════════════════════════════════════════════════════════════════
#  B. IDOR — SAU loai doi tuong cua V4, khong phai ba
# ══════════════════════════════════════════════════════════════════════════════

def _run_hai_chu(db, tmp_path):
    """Mot lan chay xong cua `uA`, va mot nguoi dung `uB` khong lien quan."""
    from tests.conftest import bao_dam_user

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    bao_dam_user(db, "uB")
    db.commit()
    return run


def test_nguoi_khac_KHONG_doc_duoc_don_vi_viec_va_so_cai(db, kho_tam, tmp_path,
                                                         asr_gia, dich_gia,
                                                         giong_gia):
    """🔴 Hai bang MOI cua V4 mang du lieu khach: `asv_work_item` (tung doan da
    lam) va `asv_usage` (da tieu bao nhieu, o dau).

    Pha 05 kiem IDOR cho run/stage/asset. Hai bang nay den sau, va mot bang moi
    la mot be mat moi — khong phai mot chi tiet cua bang cu.
    """
    from apps.auto_scan_video import features, su_dung

    run = _run_hai_chu(db, tmp_path)

    # Chu that doc duoc.
    assert features.cac_don_vi(db, run.id), "chu that khong doc duoc don vi nao"

    # ⛔ Chu so huu nam o COT, khong chi trong duong dan (pha 06). Mot phep loc
    #    theo run_id thoi la mot phep loc doan duoc.
    from apps.auto_scan_video.tables import AsvUsage, AsvWorkItem
    from sqlalchemy import select

    for Bang in (AsvWorkItem, AsvUsage):
        hang = db.execute(select(Bang).where(Bang.run_id == run.id)).scalars().all()
        assert hang, f"{Bang.__tablename__} rong — phep kiem nay khong do gi"
        assert all(h.owner_id == "uA" for h in hang), (
            f"{Bang.__tablename__} co dong khong mang chu so huu")
        khac = db.execute(select(Bang).where(Bang.owner_id == "uB")).scalars().all()
        assert not khac, f"{Bang.__tablename__} lo du lieu sang chu khac"

    assert su_dung.so_ke(db, run)["tong"]["da_giao"] > 0


def test_nguoi_khac_KHONG_lay_duoc_run_QC_hay_ket_qua(db, kho_tam, tmp_path,
                                                      asr_gia, dich_gia,
                                                      giong_gia):
    """I6 — doan trung id cung khong mo duoc lan chay cua nguoi khac."""
    from apps.auto_scan_video import features

    run = _run_hai_chu(db, tmp_path)

    with pytest.raises(Exception):
        features.lay_run(db, run.id, "uB")
    with pytest.raises(Exception):
        features.thu_lai_giai_doan(db, run.id, "uB", "render")
    with pytest.raises(Exception):
        features.huy_run(db, run.id, "uB")

    from apps.auto_scan_video import assets
    khoa = features.khoa_ket_qua(db, run)
    assert khoa, "lan chay xong ma khong co khoa ket qua"
    with pytest.raises(Exception):
        assets.asset_cua(db, khoa, "uB")


# ══════════════════════════════════════════════════════════════════════════════
#  C. CHE DU LIEU — ho so chan doan khong duoc lo bo cuc dia
# ══════════════════════════════════════════════════════════════════════════════

#: Nhung manh KHONG duoc xuat hien trong bat ky ban ghi chan doan nao.
CAM_TRONG_CHAN_DOAN = ("C:\\Users", "/home/", "AppData", "LTTPlatform",
                       "secrets", "api_key", "token", "password")


def test_ho_so_chan_doan_KHONG_lo_duong_dan_that():
    """🔴 Pha 25: `lenh_da_che` che duong dan trong CAU LENH, con `stderr` thi
    duoc luu nguyen — va ffmpeg in ca duong dan day du vao stderr.

    Nen cau lenh sach trong khi cung thong tin do di ra bang cua sau, vao dung
    mot ban ghi duoc luu de nguoi khac doc.

    ⚠️ Va duong dan Windows CO DAU CACH: ban che dau tien cat o `\\s` nen no giau
       `C:\\Users\\Thang` roi de nguyen phan sau — tuc **ten that cua nguoi dung**
       di ra ngay sau chuoi da-che.
    """
    from apps.auto_scan_video import ket_xuat

    stderr = (
        "Input #0, mov,mp4, from 'C:\\Users\\Thang Tuong\\AppData\\Local\\Temp\\"
        "asv-render-abc\\nguon.mp4':\n"
        "Output #0, mp4, to '/home/ai/du an/ra.mp4':\n"
        "Duration: 00:00:32.19, start: 0.000000, bitrate: 417 kb/s\n")
    ban = {"hinh": {"che_do": "copy", "cach_render": "sao_chep"},
           "tieng": {"lop": []}, "ra": {"thoi_luong_giay": 1.0},
           "cong_cu": {"ffmpeg": "8.0.1"}}
    ho_so = ket_xuat.ho_so_chan_doan(
        ban, ["ffmpeg", "-i", "C:\\Users\\Thang Tuong\\x\\a.mp4"],
        duoi_stderr=stderr)

    van = json.dumps(ho_so, ensure_ascii=False)
    for cam in CAM_TRONG_CHAN_DOAN:
        assert cam not in van, f"ho so chan doan lo {cam!r}: {van[:300]}"
    # Ten tep VAN phai con — do la thu lam ho so nay co ich.
    assert "nguon.mp4" in van and "ra.mp4" in van


def test_che_duong_dan_giu_lai_dong_KHONG_phai_duong_dan():
    """⭐ Che qua tay cung la mot loi: mot ho so chan doan xoa mat thong so
    ffmpeg thi khong con chan doan duoc gi."""
    from apps.auto_scan_video import ket_xuat

    for dong in ("Duration: 00:00:32.19, start: 0.000000, bitrate: 417 kb/s",
                 "-c:v libx264 -preset veryfast -crf 23",
                 "Stream #0:0(und): Video: h264, yuv420p, 640x360, 24 fps"):
        assert ket_xuat.van_ban_da_che(dong) == dong, dong


# ══════════════════════════════════════════════════════════════════════════════
#  D. HAN LUU — mot nhan khong duoc thi hanh la mot nhan
# ══════════════════════════════════════════════════════════════════════════════

def test_MOI_vat_lieu_TRUNG_GIAN_deu_duoc_dat_han_luu(db, kho_tam, tmp_path,
                                                     asr_gia, dich_gia,
                                                     giong_gia):
    """🔴 **Chot nay tung doi MOI artifact co han — ke ca ban giao cho khach.**

    Va phep kiem ngay duoi no (`..._song_LAU_HON_...`) doi dieu nguoc lai. Hai
    chot mau thuan nhau cung xanh duoc **chi vi** khong bo quet nao ton tai: khi
    `expires_at` chi la mot nhan, ca hai deu noi ve mot thu khong xay ra.

    ⇒ Pha 27 noi bo quet vao (`features.bao_tri`), va luc do mau thuan tro thanh
      mot lua chon phai dua: vat lieu trung gian co han, ban giao **khong**.
    """
    from sqlalchemy import select

    from apps.auto_scan_video import pipeline
    from apps.auto_scan_video.tables import AsvAsset

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    hang = db.execute(select(AsvAsset)
                      .where(AsvAsset.run_id == run.id)).scalars().all()
    assert hang, "lan chay khong tao artifact nao"

    # 🔴 **BAN GIAO la `IMAGE_FINISH`, ⛔ khong con la `RENDER` (b4, 25/09).**
    #    `render` nay giao mot ban TRUNG GIAN: no chua qua phep cat cua giai doan
    #    2. Giu dong nay tro vao `RENDER` la do sai ca hai chieu — no se doi
    #    `render` khong co han (⇒ mot vat lieu trung gian nam trong kho mai mai)
    #    va doi ban giao co han (⇒ video cua khach tu bien mat sau 30 ngay).
    trung_gian = [a for a in hang if a.created_by_stage != pipeline.IMAGE_FINISH]
    giao = [a for a in hang if a.created_by_stage == pipeline.IMAGE_FINISH]
    assert trung_gian and giao, "mau thu khong du hai loai de doi chieu"

    thieu = [a.storage_key for a in trung_gian if a.expires_at is None]
    assert not thieu, f"{len(thieu)} vat lieu trung gian khong co han luu"

    # ⛔ Va ban giao KHONG duoc co han: mot bo quet dang chay cong voi mot han
    #    30 ngay tren tep khach tai ve la mot lenh xoa video cua khach.
    co_han = [a.storage_key for a in giao if a.expires_at is not None]
    assert not co_han, (
        f"ban giao cho khach mang han luu tru: {co_han} — bo quet se xoa no")


# ⭐ Nhan `xfail(strict=True)` da duoc GO o pha 27: ban giao nay khong con han,
#    nen phep kiem duoi day dat that. Neu no do tro lai thi ban giao vua bi dat
#    han lai — va lan nay co mot bo quet dang chay de thi hanh cai han do.
def test_ban_giao_cho_khach_song_LAU_HON_vat_lieu_trung_gian(db, kho_tam,
                                                             tmp_path, asr_gia,
                                                             dich_gia,
                                                             giong_gia):
    """🔴 Vat lieu trung gian va san pham ban cho khach dang co CUNG han luu."""
    from sqlalchemy import select

    from apps.auto_scan_video import pipeline
    from apps.auto_scan_video.tables import AsvAsset

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    hang = db.execute(select(AsvAsset)
                      .where(AsvAsset.run_id == run.id)).scalars().all()
    giao = [a for a in hang if a.created_by_stage == pipeline.IMAGE_FINISH]
    trung_gian = [a for a in hang if a.created_by_stage == pipeline.MEDIA_PREPARE]
    assert giao and trung_gian

    # 🔴 **So CUA SO LUU, khong so moc het han.**
    #
    #    Ban dau phep kiem nay so `expires_at` cua hai artifact — va no XPASS,
    #    tuc "dat", vi IMAGE_FINISH duoc promote sau MEDIA_PREPARE khoang 70 giay nen
    #    moc het han cua no muon hon dung 70 giay. Do la cai DONG HO, khong phai
    #    mot lop luu tru rieng.
    #
    # ⭐ Cung mot cai bay da bat duoc o pha 23 (hai phep kiem cache do chieu phu
    #    dinh cua mot ham luon phu dinh) va o pha 24 (mot dot bien sua truong
    #    khong ai doc): mot phep kiem dat vi mot ly do khac han ly do no duoc
    #    viet ra.
    def _cua_so(a):
        # ⭐ Khong co han = song vo han. Pha 27 tra loi cau hoi "ban giao song
        #    lau hon bao nhieu" bang cau tra loi manh nhat co the: no khong co
        #    ngay het han nao ca. Mot lop luu tru rieng do bang MOT con so lon
        #    hon van la mot lop co the bi bo quet cham toi.
        if a.expires_at is None:
            return float("inf")
        return float((a.expires_at - a.created_at).days)

    assert _cua_so(giao[0]) > _cua_so(trung_gian[0]), (
        f"ban giao cho khach dung chung lop luu tru voi vat lieu nhap: "
        f"{_cua_so(giao[0])} ngay vs {_cua_so(trung_gian[0])} ngay")


# ══════════════════════════════════════════════════════════════════════════════
#  E. GIOI HAN — tran tai len, tran thoi gian, tran do dai
# ══════════════════════════════════════════════════════════════════════════════

def test_MOI_lan_goi_tien_trinh_con_deu_co_TRAN_THOI_GIAN():
    """⛔ Mot tien trinh con khong co tran la mot worker bi giu vinh vien: nhip
    dap cua job van chay, nen tran runtime cua nen tang khong cuu duoc.

    Doc AST: tim moi `subprocess.run(...)` trong app va doi mot `timeout=`.
    """
    import ast
    import pathlib

    from apps.auto_scan_video import __file__ as goc

    thu_muc = pathlib.Path(goc).parent
    thieu = []
    for tep in sorted(thu_muc.glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            f = nut.func
            ten = (f.attr if isinstance(f, ast.Attribute) else
                   getattr(f, "id", ""))
            if ten != "run":
                continue
            goc_ten = getattr(getattr(f, "value", None), "id", "")
            if goc_ten != "subprocess":
                continue
            if not any(k.arg == "timeout" for k in nut.keywords):
                thieu.append(f"{tep.name}:{nut.lineno}")
    assert not thieu, f"subprocess.run khong co timeout: {thieu}"


def test_TRAN_TAI_LEN_duoi_nguong_Cloudflare():
    """⚠️ Cloudflare cat o 100 MB TRUOC khi request toi may chu, nen mot tran
    bang hay tren 100 MB co nghia khach nhan trang 413 cua Cloudflare thay vi
    mot cau tieng Viet cua san pham."""
    from apps.auto_scan_video import routes

    assert 0 < routes.TRAN_TAI_LEN < 100 * 1024 * 1024, routes.TRAN_TAI_LEN


def test_co_tinh_nang_van_chan_TRUOC_require_login():
    """🔑 V4-R11 — `Depends` chay theo thu tu khai. Dat co sau `require_login`
    thi mot route 'da dong' van 303 ve `/login`, tuc no thua nhan minh ton tai.
    """
    import inspect

    from apps.auto_scan_video import routes

    nguon = inspect.getsource(routes.trang_chinh)
    assert "_cong_co" in nguon, "route chinh khong con co chan tinh nang"
    i_co = nguon.index("_cong_co")
    j_login = nguon.find("require_login")
    assert j_login == -1 or i_co < j_login, (
        "co tinh nang dat SAU require_login — route dong van thua nhan no ton tai")


# ══════════════════════════════════════════════════════════════════════════════
#  F. SAN SANG — va RUNBOOK khong duoc tro toi hu vo
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_khai_SAN_SANG_phan_biet_ba_muc_do():
    """🔑 `chua_do` khong duoc gop vao `khong`.

    Mot phep hoi HONG doi hanh dong khac han mot phep hoi tra loi "chua cau
    hinh": cai dau la mot su co phai truy, cai sau la mot dong trong app.env.
    `giong_noi.san_sang()` bat moi ngoai le va tra `False` — o day ta khong duoc
    lam the.
    """
    from apps.auto_scan_video import san_sang

    ds = san_sang.kiem()
    assert ds, "khong khai phu thuoc nao"
    assert {p.muc for p in ds} <= {san_sang.BAT_BUOC, san_sang.TUY_CHON}
    assert any(p.muc == san_sang.BAT_BUOC for p in ds)
    for p in ds:
        assert p.trang_thai in (san_sang.CO, san_sang.KHONG, san_sang.CHUA_DO)
        if p.trang_thai != san_sang.CO:
            assert p.ghi_chu.strip(), f"{p.ten} thieu ma khong noi lam gi tiep"


def test_SAN_SANG_coi_mot_phep_hoi_HONG_la_CHUA_DU(monkeypatch):
    """⛔ Mot phep hoi hong khong duoc trong nhu mot cau tra loi 'khong'.

    Va quan trong hon: no khong duoc lam `san_sang()` tra ve True. Neu no duoc
    tinh la du, mot dich vu khong hoi duoc se im lang di qua cong.
    """
    from apps.auto_scan_video import san_sang

    def no():
        raise RuntimeError("khong hoi duoc")

    # 🔴 **Moi phu thuoc BAT BUOC khac phai tra ve CO.**
    #
    #    Ban dau phep kiem nay chi lam `_co_ffmpeg` nem, roi khang dinh
    #    `san_sang() is False`. No XANH — nhung xanh vi tren may nay
    #    `may_sinh_tieng` von da `khong`, tuc no dat vi mot ly do khac han ly do
    #    no duoc viet ra. Kiem dot bien chi thang: coi `CHUA_DO` la du van khong
    #    lam do phep kiem nao.
    #
    # ⭐ Lan thu ba cua cung mot cai bay trong ba pha (pha 23: hai phep kiem
    #    cache; pha 24: mot dot bien nham truong). Cach lam no khong lap lai la
    #    **co lap dung mot bien**: moi thu khac phai xanh, de cai duy nhat co the
    #    lam do la thu dang duoc kiem.
    monkeypatch.setattr(san_sang, "_co_may_giong", lambda: True)
    monkeypatch.setattr(san_sang, "_co_cua_model", lambda: True)
    assert san_sang.san_sang() is True, "moc chuan chua xanh — phep kiem vo nghia"

    monkeypatch.setattr(san_sang, "_co_ffmpeg", no)
    ds = {p.ten: p for p in san_sang.kiem()}
    assert ds["ffmpeg"].trang_thai == san_sang.CHUA_DO
    assert san_sang.san_sang() is False


def test_TOM_TAT_san_sang_KHONG_lo_gia_tri_bien_moi_truong(monkeypatch):
    """⛔ Mot ban bao trang thai lo mot token la mot ban bao khong duoc phep xem."""
    monkeypatch.setenv("LTT_WHISPERX_PYTHON", r"C:\bi-mat\python.exe")
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "token-rat-bi-mat")

    from apps.auto_scan_video import san_sang

    van = json.dumps(san_sang.tom_tat(), ensure_ascii=False)
    for cam in ("bi-mat", "token-rat-bi-mat", "C:\\"):
        assert cam not in van, f"tom tat san sang lo {cam!r}"


def test_RUNBOOK_chi_goi_nhung_ten_CO_THAT():
    """⭐ Mot runbook tro toi mot ham da doi ten la mot runbook dan nguoi truc vao
    hu vo — dung luc ho can no nhat.

    Doc cac ten `mo_dun.ham` xuat hien trong runbook va doi chieu voi ma nguon
    HOM NAY.
    """
    import importlib
    import pathlib
    import re

    from platform_core.frontend_bundle import REPO_ROOT

    duong = REPO_ROOT / "docs" / "auto_scan_video_v4" / "RUNBOOK.md"
    assert duong.exists(), duong
    van = duong.read_text(encoding="utf-8")

    can_co = {
        "apps.auto_scan_video.san_sang": ("kiem", "tom_tat", "san_sang"),
        "apps.auto_scan_video.features": ("lay_run", "huy_run",
                                          "thu_lai_giai_doan",
                                          "LAN_THU_GIAI_DOAN_TOI_DA"),
        "apps.auto_scan_video.quan_sat": ("dong_thoi_gian", "doi_soat_nhanh"),
        "apps.auto_scan_video.su_dung": ("cac_mo_ho", "giai_quyet_mo_ho"),
        "apps.auto_scan_video.assets": ("kiem_toan_ven", "don_theo_run"),
        "apps.auto_scan_video.nan_cho_vua": ("VONG_TOI_DA",),
        "apps.auto_scan_video.sua_chua": ("VONG_SUA_TOI_DA",),
    }
    for ten_mo_dun, ten_ham in can_co.items():
        mo_dun = importlib.import_module(ten_mo_dun)
        for h in ten_ham:
            assert hasattr(mo_dun, h), f"runbook goi ten khong con: {ten_mo_dun}.{h}"
            assert h in van, f"phep kiem chot {h} nhung runbook khong nhac toi"
