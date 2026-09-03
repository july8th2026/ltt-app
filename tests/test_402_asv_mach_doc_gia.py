"""Auto Scan Video — mach doc GIA chay dau toi cuoi (pha 05).

Muc dich cua ca tep: chung minh **xuong song thi hanh** truoc khi bat cu engine
that nao vao. Cong viec ben trong moi giai doan la gia; hang doi, dinh tuyen,
checkpoint, tien, quyen so huu, huy va resume deu la that.

Vi sao thu tu do quan trong: phat hien A01 cua ban V1 ghi rang neu runtime den
muon thi moi engine se tu bay ra quy uoc job/cache/retry cua rieng no truoc khi
co mot xuong song de tuan theo. Mot loi trong xuong song **phai** lo ra o day.
"""
from __future__ import annotations

import pytest

from tests.conftest import bao_dam_user

# 🔴 Pha 13: cac phep kiem trong tep nay chay HET chuoi, nen chung cham toi
#    `audio_prepare` — va truoc pha 13 dieu do co nghia la chung nap
#    **htdemucs THAT** moi luot gate, tren mot may dang phuc vu khach.
#    Fixture autouse duoi day thay dung mieng nang do; ffmpeg, kho, CSDL,
#    hang doi va worker van that.  (`LTT_TEST_NANG=1` de chay model that)
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'asv5.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


@pytest.fixture()
def kho_tam(tmp_path, monkeypatch):
    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(str(tmp_path / "kho")))
    yield
    set_storage(None)


@pytest.fixture()
def asr_gia(monkeypatch):
    """Thay engine ASR that bang mot ban ghi xac dinh.

    ⚠️ BAT BUOC cho moi phep kiem chay het chuoi: fixture video la mot am sin,
       khong co loi noi nao, nen ASR that tra ve khong doan — va TRANSCRIBE
       **dung khi** tu choi (mot video khong co loi thi khong co gi de long
       tieng). Xem `tests/fixtures/asv_media.ban_ghi_gia`.
    """
    from apps.auto_scan_video import giai_doan_chep_loi
    from tests.fixtures.asv_media import ban_ghi_gia

    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: ban_ghi_gia())
    return ban_ghi_gia


@pytest.fixture()
def dich_gia(monkeypatch):
    """Thay bo dich that bang mot ban dich xac dinh.

    ⚠️ BAT BUOC cho moi phep kiem chay het chuoi: `CONTENT_PROCESS` goi
       `platform_core/llm/dieu_phoi.py`, va bo dieu phoi can mot khoa API that.
       Khong co khoa thi no tu choi — **dung nhu no nen lam**. Mot bo test khong
       duoc phep doi hoi mot khoa tra tien.

    ⭐ Duong goi that (chia lo, gop, phan loai loi mo ho) duoc kiem rieng o
       `tests/test_408_asv_dich_thuat.py`.
    """
    from apps.auto_scan_video import dich_thuat

    monkeypatch.setattr(
        dich_thuat, "dich_ban_ghi",
        lambda db, ban_ghi_goc, ctx=None: {
            d["ma"]: f"ban dich cua {d['ma']}"
            for d in (ban_ghi_goc.get("doan") or [])})
    return True


@pytest.fixture()
def giong_gia(monkeypatch, tmp_path):
    """Thay may sinh tieng that bang mot tep WAV xac dinh.

    ⚠️ BAT BUOC cho moi phep kiem chay het chuoi: `VOICE_SYNTHESIS` goi dich vu
       `LTTStudioVoice` sau loopback :8120, va bo test khong duoc phep doi hoi
       mot dich vu ngoai dang chay.

    ⭐ Duong that (phan loai ban/mo ho, phuc hoi tung doan, kiem tep) duoc kiem
       rieng o `tests/test_409_asv_giong_noi.py`.
    """
    import subprocess
    from pathlib import Path

    from platform_core import media
    from apps.auto_scan_video import giong_noi

    mau = Path(tmp_path) / "_giong_mau.wav"
    subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
         "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(mau)],
        check=True, capture_output=True)
    du_lieu = mau.read_bytes()

    monkeypatch.setattr(giong_noi, "san_sang", lambda: True)
    monkeypatch.setattr(giong_noi, "giai_giong", lambda db, **kw: (None, "bac"))
    monkeypatch.setattr(giong_noi, "doc_mot_doan",
                        lambda chu, **kw: (du_lieu, {}))
    return True


def _tao_run(db, owner="uA", giu=10, *, kho=None, tmp_path=None):
    """Tao mot run kem TEP NGUON THAT.

    ⚠️ Tu pha 08, `MEDIA_PREPARE` la engine that: no soi tep, thi hanh chinh
       sach dau vao va tach tieng. Mot `source_key` gia se lam giai doan dau
       that bai vi ly do khong lien quan gi toi thu dang duoc kiem.
    """
    import tempfile
    from pathlib import Path

    from platform_core import credit
    from platform_core.storage import get_storage
    from apps.auto_scan_video import features
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    bao_dam_user(db, owner)
    credit.nap(db, owner, 1000)
    # Tu tao thu muc tam thay vi doi `tmp_path` tu moi phep kiem: nguon la chi
    # tiet cua ban dung, khong phai thu phep kiem nao dang noi ve.
    thu_muc = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp(prefix="asv-t-"))
    khoa = nap_nguon_vao_kho(kho or get_storage(), thu_muc, owner_id=owner)
    run = features.tao_run(db, owner_id=owner, source_key=khoa,
                           settings={"timing_mode": "fit_original"},
                           uoc_luong_credit=giu)
    db.commit()
    return run


def _chay_het_hang_doi(db, *, nang_luc=None, toi_da=200) -> int:
    """Nhat va chay job cho toi khi hang doi rong. Tra ve so job da chay.

    Dong vai worker THAT: dung `jobs.claim` + `resolve_handler`, nen phep dinh
    tuyen theo `manifest.requires` la phep dinh tuyen that chu khong phai mot
    ban gia lap.
    """
    from platform_core import jobs
    from platform_core.job_runner import JobContext

    dem = 0
    for _ in range(toi_da):
        job = jobs.claim(db, worker_id="w-thu", capabilities=nang_luc)
        if job is None:
            break
        db.commit()
        handler = jobs.resolve_handler(job.job_type)
        ctx = JobContext(job.id)
        ctx.job_type = job.job_type
        try:
            ket_qua = handler(dict(job.params), ctx) or {}
            jobs.complete(db, job, ket_qua)
        except Exception as exc:      # noqa: BLE001 - worker that cung bat het
            jobs.fail(db, job, str(exc), retry=False)
        db.commit()
        dem += 1
    # 🔴 BAT BUOC. Nen tang tao session voi `expire_on_commit=False`
    #    (`platform_core/db.py:154`), va moi handler chay tren SESSION RIENG cua
    #    no. Nen sau vong nay, session cua test van cam nhung doi tuong cu tu
    #    truoc — doc `run.status` se ra `queued` trong khi CSDL da `done`.
    #
    # ⭐ Day khong phai chi tiet cua test. `expire_on_commit=False` la lua chon
    #    cua nen tang, va no co nghia moi doan ma doc lai mot ban ghi sau khi
    #    mot tien trinh KHAC ghi no deu phai lam viec nay.
    db.expire_all()
    return dem


# ══════════════════════════════════════════════════════════════════════════════
#  Mach doc
# ══════════════════════════════════════════════════════════════════════════════

def test_run_chay_het_CHIN_giai_doan_va_ve_done(db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """Bang chung chinh cua pha 05.

    Mot lan chay di qua ca chin giai doan bang hang doi that, worker that, dinh
    tuyen that — chi cong viec ben trong la gia.
    """
    from apps.auto_scan_video import features, pipeline
    from apps.auto_scan_video.tables import RUN_DONE, STAGE_SUCCEEDED

    run = _tao_run(db)
    # Worker da nang: nhat duoc ca ba app.
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})

    run = features.lay_run(db, run.id, "uA")
    ds = features.cac_giai_doan(db, run)
    xong = [s.stage for s in ds if s.status == STAGE_SUCCEEDED]

    # ⚠️ **9 -> 10 o pha 12.** `edit_plan` duoc chen vao TRUOC `content_process`
    #    de dong `V4-R07` (P0): trong V2, giai doan dich (tra tien) chay o vi tri
    #    thu 4 khi chua co ban bien tap nao — tuc dich va tra tien cho nhung cau
    #    thoai thuoc nhung canh se bi cat bo.
    #
    # ⭐ Con so o day co chu dinh la mot con so, khong phai `len(pipeline.CHUOI)`
    #    doi chieu voi chinh no: mot phep kiem so chuoi voi chinh no khong bao
    #    gio do. Doi chuoi thi phai sua con so nay, va do la luc nguoi sua doc
    #    lai xem viec chen co dung cho khong.
    assert len(ds) == len(pipeline.CHUOI) == 10
    assert sorted(xong) == sorted(pipeline.TEN_GIAI_DOAN), (
        f"chua xong het: thieu {set(pipeline.TEN_GIAI_DOAN) - set(xong)}")
    assert run.status == RUN_DONE


def test_thu_tu_giai_doan_do_MAY_CHU_quyet_khong_phai_client(db, kho_tam, asr_gia, dich_gia, giong_gia):
    """I17 / O18 — khong co do thi do client gui len.

    `pipeline.CHUOI` nam trong ma nguon. Test nay chot rang moi giai doan chi
    chay SAU cac phu thuoc cua no, do bang `started_at` that.
    """
    from apps.auto_scan_video import features, pipeline

    run = _tao_run(db)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})

    moc = {s.stage: s.started_at for s in features.cac_giai_doan(db, run)}
    for g in pipeline.CHUOI:
        for truoc in g.sau:
            assert moc[truoc] is not None and moc[g.ten] is not None
            assert moc[truoc] <= moc[g.ten], (
                f"{g.ten} chay truoc phu thuoc {truoc} cua no")


# ══════════════════════════════════════════════════════════════════════════════
#  I3 / G3 — tien
# ══════════════════════════════════════════════════════════════════════════════

def test_KHONG_job_giai_doan_nao_giu_credit(db, kho_tam, asr_gia, dich_gia, giong_gia):
    """ADR-001 D4 — chin giai doan, khong dong nao giu tien.

    Chi `run.id` giu. Neu mot giai doan tu giu, khach bi tinh tien **muoi lan**
    cho mot lan chay va **so credit van can**, nen khong co gi trong nhu hong.
    """
    from platform_core import credit
    from platform_core.models import Job
    from sqlalchemy import select

    run = _tao_run(db, giu=10)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})

    con = db.execute(select(Job).where(Job.plan_id == run.id)).scalars().all()
    assert con, "khong co job con nao — mach doc chua chay"
    for job in con:
        assert credit.so_da_giu(db, job.id) == 0, (
            f"job giai doan {job.job_type} da tu giu credit")


def test_quyet_toan_MOT_LAN_va_hoan_phan_khong_dung(db, kho_tam, asr_gia, dich_gia, giong_gia):
    """I2/I3 — giu 10, cac giai doan gia ton 0, nen phai hoan het 10."""
    from platform_core import credit
    from apps.auto_scan_video import features
    from apps.auto_scan_video.tables import RUN_DONE

    run = _tao_run(db, giu=10)
    # Do sau khi nop: `_tao_run` vua nap credit **va** giu cho, nen so du luc nay
    # da tru phan giu. Cong lai 10 se ra so truoc khi giu.
    sau_khi_giu = credit.so_du(db, "uA")
    truoc_khi_giu = sau_khi_giu + 10

    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    run = features.lay_run(db, run.id, "uA")

    assert run.status == RUN_DONE
    assert run.credit_actual == 0, "giai doan gia khong ton gi"
    assert credit.so_du(db, "uA") == truoc_khi_giu, (
        "phan khong dung phai duoc hoan lai het")


def test_tran_chi_chan_truoc_khi_tieu_vuot_hold(db, kho_tam):
    """RISK-03-02 — uoc luong te phai thanh mot that bai CHINH SACH, khong phai
    mot lan tieu vuot phan da giu.

    `credit_held` uoc theo thoi luong truoc khi biet transcript, nen no **se**
    sai doi khi. `features.kiem_tran_chi` la chot bat buoc truoc moi lan ton
    tien (ADR-001 D4).
    """
    from apps.auto_scan_video import features

    run = _tao_run(db, giu=5)
    # Gia lap mot giai doan da tieu het phan giu.
    stage = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    features.cap_nhat_giai_doan(db, stage, credit_actual=5)
    db.commit()

    run = features.lay_run(db, run.id, "uA")
    features.kiem_tran_chi(db, run, 0)          # vua het, van hop le
    with pytest.raises(features.AsvError):
        features.kiem_tran_chi(db, run, 1)      # them mot don vi la vuot


# ══════════════════════════════════════════════════════════════════════════════
#  I12 / G5 — dinh tuyen
# ══════════════════════════════════════════════════════════════════════════════

def test_lan_ffmpeg_KHONG_nhat_duoc_job_GPU(db, kho_tam, asr_gia, dich_gia, giong_gia):
    """ADR-001 D5 do that: mot worker chi co ffmpeg khong cham vao giai doan GPU.

    Day la ly do ton tai cua `asv_gpu`. Neu ca chin giai doan nam trong mot app
    khai `requires=("ffmpeg","gpu")` thi lan ffmpeg khong nhat duoc **gi ca**.
    """
    from platform_core import jobs

    run = _tao_run(db)
    # Chi chay lan api (dieu phoi) + ffmpeg. `audio_prepare` la GPU nen se ket.
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg"})

    from apps.auto_scan_video import features
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED
    ds = {s.stage: s.status for s in features.cac_giai_doan(db, run)}

    assert ds["media_prepare"] == STAGE_SUCCEEDED, "giai doan ffmpeg phai chay duoc"
    assert ds["audio_prepare"] != STAGE_SUCCEEDED, (
        "worker khong co GPU da chay duoc giai doan GPU")

    # Va job GPU van nam do, cho mot lan co nang luc dung.
    con_lai = jobs.claim(db, worker_id="w-gpu", capabilities={"gpu"})
    assert con_lai is not None and con_lai.app_slug == "asv_gpu"


# ══════════════════════════════════════════════════════════════════════════════
#  I6 — quyen so huu
# ══════════════════════════════════════════════════════════════════════════════

def test_nguoi_khac_KHONG_doc_duoc_run_du_biet_id(db, kho_tam):
    """I6 / G4 — doan trung UUID cung khong mo duoc run cua nguoi khac."""
    from apps.auto_scan_video import features

    run = _tao_run(db, owner="uA")
    bao_dam_user(db, "uB"); db.commit()

    assert features.lay_run(db, run.id, "uA").id == run.id
    with pytest.raises(features.KhongTimThay):
        features.lay_run(db, run.id, "uB")


def test_moi_dong_giai_doan_deu_mang_chu_so_huu(db, kho_tam):
    """`owner_id` lap lai o `asv_stage` co y — mot phep loc quyen khong nen phu
    thuoc vao mot phep JOIN ma nguoi viet truy van co the quen."""
    from apps.auto_scan_video import features

    run = _tao_run(db, owner="uA")
    for s in features.cac_giai_doan(db, run):
        assert s.owner_id == "uA"


# ══════════════════════════════════════════════════════════════════════════════
#  I13 — huy
# ══════════════════════════════════════════════════════════════════════════════

def test_huy_giua_chung_thi_run_KHONG_BAO_GIO_thanh_done(db, kho_tam, asr_gia, dich_gia, giong_gia):
    """I13 / G10 — mot job con ve dich muon khong lam song lai run da huy.

    Nua thu nhat: job con chua ket thuc bi huy. Nua thu hai, quan trong hon:
    `_advance` doc lai `run.status` **duoi khoa** o dau moi luot va dung ngay.
    Nen ke ca khi con mot luot `advance` dang xep hang, no cung khong the ket
    luan "da xong".
    """
    from apps.auto_scan_video import features
    from apps.auto_scan_video.tables import RUN_CANCELLED

    run = _tao_run(db)
    # Chay mot phan: chi lan ffmpeg, nen chuoi ket lai o giai doan GPU.
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg"})

    features.huy_run(db, run.id, "uA"); db.commit()
    assert features.lay_run(db, run.id, "uA").status == RUN_CANCELLED

    # Bay gio tha mot worker DA NANG vao. Neu co bat cu luot advance nao con lai,
    # no se thay run da huy va dung.
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})
    assert features.lay_run(db, run.id, "uA").status == RUN_CANCELLED, (
        "run da huy lai thanh mot trang thai khac")


def test_huy_thi_hoan_lai_phan_da_giu(db, kho_tam):
    from platform_core import credit
    from apps.auto_scan_video import features

    bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000); db.commit()
    truoc = credit.so_du(db, "uA")
    run = features.tao_run(db, owner_id="uA", source_key="asv/uA/x.mp4",
                           settings={}, uoc_luong_credit=25)
    db.commit()
    assert credit.so_du(db, "uA") == truoc - 25

    features.huy_run(db, run.id, "uA"); db.commit()
    assert credit.so_du(db, "uA") == truoc, "huy phai hoan lai phan chua dung"


# ══════════════════════════════════════════════════════════════════════════════
#  I9 / I18 — resume va dong thoi
# ══════════════════════════════════════════════════════════════════════════════

def test_chay_lai_tiep_tu_giai_doan_dang_do_khong_lam_lai_tu_dau(db, kho_tam, asr_gia, dich_gia, giong_gia):
    """I9 — resume tu giai doan dau tien chua hop le, khong phai tu dau chuoi.

    Do bang `attempt`: giai doan da xong o luot mot phai giu nguyen so lan thu
    sau khi worker quay lai. Neu chung tang, ta dang tinh lai thu da tinh — voi
    engine that do la tien va hang chuc phut GPU.
    """
    from apps.auto_scan_video import features
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    run = _tao_run(db)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg"})   # ket o giai doan GPU

    truoc = {s.stage: (s.status, s.attempt, s.fingerprint)
             for s in features.cac_giai_doan(db, run)}
    da_xong = [t for t, v in truoc.items() if v[0] == STAGE_SUCCEEDED]
    assert da_xong, "luot mot chua xong giai doan nao"

    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"})   # worker tro lai

    sau = {s.stage: (s.status, s.attempt, s.fingerprint)
           for s in features.cac_giai_doan(db, run)}
    for ten in da_xong:
        assert sau[ten][1] == truoc[ten][1], (
            f"{ten} bi chay lai du da xong — mat cong va mat tien")
        assert sau[ten][2] == truoc[ten][2], f"{ten} doi van tay khi chay lai"


def test_hai_giai_doan_xong_cung_luc_deu_duoc_luu(db, kho_tam):
    """I18 — bat bien ma khoi JSON `checkpoint` khong giu duoc.

    Hai giai doan khac nhau ghi hai DONG khac nhau, nen khong co doc-sua-ghi va
    khong the mat cap nhat. Voi mot tai lieu JSON dung chung, hai lan ghi dan
    xen nhau se lam mot ben bien mat — im lang.
    """
    from apps.auto_scan_video import features
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    run = _tao_run(db)
    a = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    b = features.giai_doan_theo_ten(db, run.id, "compose")

    features.danh_dau_xong(db, a, outputs={"x": 1}, fingerprint="aaa")
    features.danh_dau_xong(db, b, outputs={"y": 2}, fingerprint="bbb")
    db.commit()

    ds = {s.stage: s for s in features.cac_giai_doan(db, run)}
    assert ds["media_prepare"].status == STAGE_SUCCEEDED
    assert ds["compose"].status == STAGE_SUCCEEDED
    assert ds["media_prepare"].outputs == {"x": 1}
    assert ds["compose"].outputs == {"y": 2}


def test_ghi_dong_giai_doan_bang_revision_CU_thi_bi_tu_choi(db, kho_tam):
    """I18 — cuoc dua con lai: worker cu mat dap nhip, job mo coi da bi nhat lai.

    `UPDATE ... WHERE revision = :r` bien no thanh mot xung dot NHIN THAY DUOC,
    thay vi mot ban ghi de. Khuon lay tu `platform_core/app_projects.py:85`.

    ⚠️ Phai dung HAI SESSION that. Ban dau tep nay gia lap bang cach gan
       `stage.revision = <so cu>` tren cung mot session — va phep kiem **khong
       do**, vi thao tac gan do lam doi tuong "ban", roi autoflush cua SQLAlchemy
       ghi so cu ay xuong CSDL ngay truoc cau UPDATE, nen menh de WHERE lai khop.
       Tuc ban gia lap tu tao ra dieu kien de minh thanh cong.

    ⭐ Hai session la mo hinh THAT: hai worker la hai tien trinh, moi ben mot
       ban sao doi tuong, va khong ben nao flush ho ben kia.
    """
    import platform_core.db as dbmod
    from apps.auto_scan_video import features

    run = _tao_run(db)
    stage_a = features.giai_doan_theo_ten(db, run.id, "media_prepare")

    gen_b = dbmod.get_session(); db_b = next(gen_b)
    try:
        stage_b = features.giai_doan_theo_ten(db_b, run.id, "media_prepare")
        assert stage_b is not None and stage_b.revision == stage_a.revision

        # Worker A ghi truoc va thang.
        features.cap_nhat_giai_doan(db, stage_a, error="worker A ghi")
        db.commit()

        # Worker B van cam ban cu -> phai bi tu choi, khong duoc ghi de.
        with pytest.raises(features.XungDot):
            features.cap_nhat_giai_doan(db_b, stage_b, error="worker B ghi de")
        db_b.rollback()
    finally:
        db_b.close()

    db.expire_all()
    sau = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    assert sau.error == "worker A ghi", "ban ghi cua worker A da bi de mat"


# ══════════════════════════════════════════════════════════════════════════════
#  Dieu phoi
# ══════════════════════════════════════════════════════════════════════════════

def test_dieu_phoi_KHONG_giu_worker_de_cho_con(db, kho_tam):
    """EXECUTION_GUARDRAILS muc 1 / ADR-001 D1.

    So tien trinh worker mac dinh **bang so GPU**, nen mot cha chay dai giu mot
    suat de hoi vong la hai run dong thoi lam dung ca nen tang — khong loi nao
    duoc ghi ra.

    Do bang hanh vi chu khong bang thoi gian: mot luot `advance` tra ve NGAY khi
    job con van chua chay, va no de lai dung mot luot ke tiep trong hang doi.
    """
    from platform_core import jobs
    from platform_core.job_runner import JobContext
    from platform_core.models import JOB_QUEUED
    from sqlalchemy import select
    from platform_core.models import Job

    run = _tao_run(db)
    job = jobs.claim(db, worker_id="w1", capabilities={"api"})
    assert job is not None and job.job_type == "auto_scan_video.advance"
    db.commit()

    ctx = JobContext(job.id); ctx.job_type = job.job_type
    ket_qua = jobs.resolve_handler(job.job_type)(dict(job.params), ctx)
    jobs.complete(db, job, ket_qua); db.commit()

    assert "media_prepare" in (ket_qua.get("da_nop") or []), (
        "advance khong nop giai doan dau")

    cho = db.execute(select(Job).where(Job.status == JOB_QUEUED)).scalars().all()
    loai = sorted({j.job_type for j in cho})
    assert "asv_media.media_prepare" in loai, "job con chua duoc nop"
    assert "auto_scan_video.advance" in loai, "advance chua tu nop lai"

    tiep = [j for j in cho if j.job_type == "auto_scan_video.advance"]
    assert len(tiep) == 1, f"advance fan-out thanh {len(tiep)} luot"
