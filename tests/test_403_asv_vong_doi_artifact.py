"""Auto Scan Video — vong doi artifact: promote nguyen tu, lineage, toan ven.

Kiem thi hanh ADR-001 D7/D8 va cac cua so su co ma Prompt 06 muc 5 doi phai dinh
nghia va do duoc.

⛔ Khong engine media nang nao o day. Artifact la JSON that, promote that, doc
   that, bam that — chi noi dung la gia.
"""
from __future__ import annotations

import io
import json

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
    url = f"sqlite:///{(tmp_path / 'asv6.db').as_posix()}"
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
def kho(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    k = LocalStorage(str(tmp_path / "kho"))
    set_storage(k)
    yield k
    set_storage(None)


def _staging(kho, khoa: str, du_lieu: bytes) -> str:
    kho.put(khoa, io.BytesIO(du_lieu), content_type="application/json")
    return khoa


def _giai_doan_xong(db, *, run_id: str, owner_id: str, stage: str,
                    van_tay: str, khoa: list):
    """Dong `AsvStage` ma mot lan chay THAT de lai sau khi giai doan xong.

    🔑 Sau pha 27, `cache_dung_duoc` hoi `AsvStage.fingerprint` chu khong con do
       chuoi tren `storage_key`. Ly do: khoa mang van tay cua TUNG ARTIFACT
       (mot lan `media_prepare` ghi hai artifact duoi hai van tay khac nhau),
       nen khong gia tri nao trong ten tep tra loi duoc cau hoi "GIAI DOAN nay
       da chay voi van tay nay chua".

    ⇒ Cac phep kiem cache vi the phai dung canh day du. Truoc do chung chi tao
      artifact — mot trang thai `chay_giai_doan` khong bao gio tao ra, vi no
      luon co dong giai doan truoc khi hoi cache.
    """
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED, AsvStage

    gd = AsvStage(run_id=run_id, owner_id=owner_id, stage=stage,
                  status=STAGE_SUCCEEDED, fingerprint=van_tay,
                  outputs={"stage": stage, "khoa_asset": list(khoa)})
    db.add(gd)
    db.flush()
    return gd


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
    """Thay cua goi model. Than ham o `tests/fixtures/asv_media.py`.

    ⭐ Goi ham chung thay vi chep lai: truoc pha 14 co ba ban sao cua
       stub nay va ca ba cung thoi chan mot luc khi `CONTENT_PROCESS`
       doi cho goi model.
    """
    from tests.fixtures.asv_media import cua_ai_gia

    return cua_ai_gia(monkeypatch)

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


def _tao_run(db, owner="uA", giu=10):
    """Tao run kem TEP NGUON THAT.

    Tu pha 08 `MEDIA_PREPARE` la engine that: no soi tep, thi hanh chinh sach
    dau vao va tach tieng. Mot `source_key` gia lam giai doan dau that bai vi
    mot ly do khong lien quan gi toi thu dang duoc kiem.
    """
    import tempfile
    from pathlib import Path

    from platform_core import credit
    from platform_core.storage import get_storage
    from apps.auto_scan_video import features
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    bao_dam_user(db, owner)
    credit.nap(db, owner, 1000)
    khoa = nap_nguon_vao_kho(get_storage(), Path(tempfile.mkdtemp(prefix="asv-t6-")),
                             owner_id=owner)
    run = features.tao_run(db, owner_id=owner, source_key=khoa,
                           settings={"giong_id": "Minh Đức"}, uoc_luong_credit=giu)
    db.commit()
    return run


# ══════════════════════════════════════════════════════════════════════════════
#  Muc 7 — khong bao gio tin chuoi khoa cua client
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("xau", [
    "../../secrets",            # di len tren
    "a/b",                      # dau gach cheo trong mot manh
    "",                         # rong
    "C:evil",                   # dau hai cham
    "~root",                    # duong nha
    "co khoang trang",
])
def test_dat_khoa_TU_CHOI_manh_khong_hop_le(xau):
    """Lop phong thu THU NHAT: ta tu dat khoa tu cac manh da kiem.

    `platform_core/storage.py:181 _safe_key` da chan `../`, va no la lop cuoi.
    Nhung mot he thong luu tru chi bi bien thanh mot he thong doc tep tuy y khi
    co ai do dung **chuoi cua client** lam khoa. O day khong co duong nao cho
    dieu do: moi manh phai khop `[A-Za-z0-9._-]+`.
    """
    from apps.auto_scan_video import assets

    with pytest.raises(assets.AssetError):
        assets.dat_khoa(owner_id="uA", run_id="r1", stage=xau,
                        van_tay="abc", duoi="json")


def test_khoa_mang_chu_so_huu_va_van_tay():
    """I6/I19 — chu so huu nam TRONG khoa, khong chi trong mot cot CSDL.

    Mot phep loc quyen dua vao `WHERE owner_id = ...` chi cach mot lan quen viet
    menh de do. Chu so huu trong khoa thi ro ri doi hoi ai do CO Y dung ghep
    duong dan cua nguoi khac.
    """
    from apps.auto_scan_video import assets

    khoa = assets.dat_khoa(owner_id="uA", run_id="r1", stage="compose",
                           van_tay="deadbeef", duoi="json")
    assert khoa == "asv/uA/r1/compose/deadbeef.json"


# ══════════════════════════════════════════════════════════════════════════════
#  Muc 4 — kiem hop le TRUOC khi promote
# ══════════════════════════════════════════════════════════════════════════════

def test_tep_RONG_bi_tu_choi_va_KHONG_bao_gio_len_khoa_ben_vung(db, kho):
    """I8/I14 — hinh dang thuong gap nhat cua mot lan chet giua chung.

    Tep da duoc tao, chua kip ghi gi. Neu no lot qua, mot giai doan bao DONE voi
    ket qua rong va khach nhan mot tep 0 byte kem chu "thanh cong".
    """
    from apps.auto_scan_video import assets

    _staging(kho, "asv-staging/uA/r1/compose/vt.json", b"")
    with pytest.raises(assets.AssetError):
        assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json",
                              staging_key="asv-staging/uA/r1/compose/vt.json")
    assert not kho.exists("asv/uA/r1/compose/vt.json"), (
        "tep hong da len duoc khoa ben vung")


def test_JSON_hong_bi_tu_choi_truoc_khi_promote(db, kho):
    """Buoc 2 kiem NOI DUNG, khong chi kiem ton tai.

    Bo qua phep kiem nay thi "DONE" chi con nghia la "engine khong nem", va bat
    bien I8 mat het noi dung.
    """
    from apps.auto_scan_video import assets

    _staging(kho, "asv-staging/uA/r1/compose/vt.json", b"{khong phai json")
    with pytest.raises(assets.AssetError):
        assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json",
                              staging_key="asv-staging/uA/r1/compose/vt.json")
    assert not kho.exists("asv/uA/r1/compose/vt.json")


def test_promote_thanh_cong_thi_XOA_ban_staging_va_ghi_checksum(db, kho):
    from apps.auto_scan_video import assets

    noi_dung = json.dumps({"a": 1}).encode()
    tam = _staging(kho, "asv-staging/uA/r1/compose/vt.json", noi_dung)
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json", staging_key=tam)
    db.commit()

    assert kho.exists("asv/uA/r1/compose/vt.json")
    assert not kho.exists(tam), "ban staging con lai sau promote"
    assert a.size == len(noi_dung)
    assert a.checksum == assets.bam(noi_dung)
    assert a.integrity == "ok"


# ══════════════════════════════════════════════════════════════════════════════
#  Muc 5 — bon cua so su co
# ══════════════════════════════════════════════════════════════════════════════

def test_cua_so_1_2_co_staging_khong_co_CSDL_thi_khong_ro_ri(db, kho):
    """Chet sau khi ghi staging, truoc khi kiem. Khong ban ghi nao, khong khoa
    ben vung nao — chay lai la sach."""
    from apps.auto_scan_video.tables import AsvAsset
    from sqlalchemy import select

    _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"a":1}')
    assert db.execute(select(AsvAsset)).scalars().first() is None
    assert not kho.exists("asv/uA/r1/compose/vt.json")


def test_cua_so_3_4_da_promote_chua_ghi_tham_chieu_thi_chay_lai_luy_dang(db, kho):
    """Cua so su co quan trong nhat, va ly do khoa duoc dan xuat tu VAN TAY.

    Neu khoa dua tren dong ho hay bo dem, lan chay lai se tao mot tep THU HAI va
    tep dau thanh rac mo coi — khong ai tham chieu, khong ai don. Vi khoa den tu
    van tay, lan ghi thu hai de len chinh no.
    """
    from sqlalchemy import select
    from apps.auto_scan_video import assets
    from apps.auto_scan_video.tables import AsvAsset

    # Luot 1: promote xong roi "chet" (khong commit ban ghi).
    tam1 = _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"lan":1}')
    kho.promote(tam1, "asv/uA/r1/compose/vt.json")
    assert kho.exists("asv/uA/r1/compose/vt.json")
    assert db.execute(select(AsvAsset)).scalars().first() is None

    # Luot 2: chay lai voi cung van tay.
    tam2 = _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"lan":2}')
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json", staging_key=tam2)
    db.commit()

    hang = list(db.execute(select(AsvAsset)).scalars())
    assert len(hang) == 1, "chay lai da tao ban ghi thu hai"
    assert a.storage_key == "asv/uA/r1/compose/vt.json"
    with kho.open(a.storage_key) as f:
        assert json.loads(f.read()) == {"lan": 2}


def test_tham_chieu_toi_tep_da_BIEN_MAT_bi_bat(db, kho):
    """Cua so "checkpoint tro toi mot tep khong con".

    Phan biet `missing` voi `corrupt` co y: gop chung lai la mat thong tin can
    de xu ly — mot ben la mat du lieu, ben kia la du lieu sai.
    """
    from apps.auto_scan_video import assets

    tam = _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"a":1}')
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json", staging_key=tam)
    db.commit()

    kho.delete(a.storage_key)
    assert assets.kiem_toan_ven(db, kho, a) == "missing"


def test_tep_bi_SUA_DOI_bi_bat_bang_checksum(db, kho):
    """`corrupt` — tep con day du co nhung noi dung da lech.

    Chi so co thoi thi mot lan sua giu nguyen do dai se lot. Checksum la thu
    phan biet "con tep" voi "con DUNG tep".
    """
    from apps.auto_scan_video import assets

    tam = _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"a":1}')
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json", staging_key=tam)
    db.commit()

    # Ghi de bang mot noi dung khac DUNG BANG do dai.
    kho.put(a.storage_key, io.BytesIO(b'{"a":9}'), content_type="application/json")
    assert assets.kiem_toan_ven(db, kho, a) == "corrupt"


def test_artifact_HET_HAN_duoc_goi_dung_ten(db, kho):
    """Han luu tru la chinh sach, khong phai su co — va no phai NOI RA.

    🔴 Kho nay da dinh lo do dung kieu do: `voice_block.audio_key` song mai cung
       du an con tep song 30 ngay, nen khach mo du an cu thay mot trinh phat 404
       khong loi giai thich (CLAUDE.md).
    """
    from datetime import timedelta
    from apps.auto_scan_video import assets

    tam = _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"a":1}')
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json", staging_key=tam,
                              han=timedelta(seconds=-1))   # da qua han
    db.commit()
    assert assets.kiem_toan_ven(db, kho, a) == "expired"


# ══════════════════════════════════════════════════════════════════════════════
#  Muc 6 — cache theo chu so huu va tinh hop le
# ══════════════════════════════════════════════════════════════════════════════

def test_cache_TRUNG_van_tay_van_bi_bo_khi_tep_mat(db, kho):
    """I10/O13 — "co mot tep dung ten" KHONG phai cache hop le.

    Neu chi so van tay, mot tep bi xoa se lam luot dung lai thanh mot loi im
    lang, va no lo ra o cuoi day chuyen — xa cho gay ra no.
    """
    from apps.auto_scan_video import assets

    tam = _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"a":1}')
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json", staging_key=tam)
    _giai_doan_xong(db, run_id="r1", owner_id="uA", stage="compose",
                    van_tay="vt", khoa=[a.storage_key])
    db.commit()

    assert assets.cache_dung_duoc(db, kho, owner_id="uA", run_id="r1",
                                  stage="compose", van_tay="vt")
    kho.delete(a.storage_key)
    assert assets.cache_dung_duoc(db, kho, owner_id="uA", run_id="r1",
                                  stage="compose", van_tay="vt") is None


def test_cache_KHONG_BAO_GIO_vuot_qua_ranh_gioi_chu_so_huu(db, kho):
    """I19 / EXECUTION_GUARDRAILS muc 8.

    Hai khach tai len dung mot tep se ra dung mot van tay. Dung lai ket qua cua
    nguoi nay cho nguoi kia se **tiet lo rang nguoi kia dang giu dung tep do** —
    mot ro ri khong can doc noi dung cung suy ra duoc.
    """
    from apps.auto_scan_video import assets

    tam = _staging(kho, "asv-staging/uA/r1/compose/chung.json", b'{"a":1}')
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="chung", kind="json",
                              duoi="json", staging_key=tam)
    _giai_doan_xong(db, run_id="r1", owner_id="uA", stage="compose",
                    van_tay="chung", khoa=[a.storage_key])
    db.commit()

    # uB co CUNG van tay nhung khac run/chu so huu -> khong duoc dung lai.
    assert assets.cache_dung_duoc(db, kho, owner_id="uB", run_id="r1",
                                  stage="compose", van_tay="chung") is None
    assert assets.cache_dung_duoc(db, kho, owner_id="uB", run_id="r9",
                                  stage="compose", van_tay="chung") is None


def test_vo_hieu_theo_day_chuyen_danh_dau_ha_nguon(db, kho):
    """I10 — mot lan tinh lai o thuong nguon phai lam ha nguon thanh khong dung.

    Van tay ha nguon **da** chua van tay thuong nguon, nen no tu doi. Nhung ban
    ghi cu van nam do va van noi `ok`; ham nay lam trang thai khop voi su that
    thay vi doi ai do phat hien.
    """
    from apps.auto_scan_video import assets

    for stage in ("transcribe", "content_process"):
        tam = _staging(kho, f"asv-staging/uA/r1/{stage}/vt.json", b'{"a":1}')
        a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                                  stage=stage, van_tay="vt", kind="json",
                                  duoi="json", staging_key=tam)
        _giai_doan_xong(db, run_id="r1", owner_id="uA", stage=stage,
                        van_tay="vt", khoa=[a.storage_key])
    db.commit()

    so = assets.vo_hieu_theo_day_chuyen(db, "r1", ["content_process"])
    db.commit()
    assert so == 1
    assert assets.cache_dung_duoc(db, kho, owner_id="uA", run_id="r1",
                                  stage="transcribe", van_tay="vt"), (
        "thuong nguon khong duoc bi vo hieu lay")


# ══════════════════════════════════════════════════════════════════════════════
#  I6 — tu choi doc cheo chu so huu
# ══════════════════════════════════════════════════════════════════════════════

def test_nguoi_khac_KHONG_mo_duoc_asset_du_biet_dung_khoa(db, kho):
    """G4 — doan trung khoa cung khong doc duoc artifact cua nguoi khac."""
    from apps.auto_scan_video import assets

    tam = _staging(kho, "asv-staging/uA/r1/compose/vt.json", b'{"a":1}')
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id="r1",
                              stage="compose", van_tay="vt", kind="json",
                              duoi="json", staging_key=tam)
    db.commit()

    assert assets.asset_cua(db, a.storage_key, "uA").id == a.id
    with pytest.raises(assets.AssetError):
        assets.asset_cua(db, a.storage_key, "uB")


# ══════════════════════════════════════════════════════════════════════════════
#  Cong thoat: giai doan chi trao doi ASSET REF, va DONE keo theo artifact ben
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_giai_doan_ket_thuc_bang_ASSET_REF_that_va_kiem_duoc(db, kho, asr_gia, dich_gia, giong_gia):
    """Cong thoat cua pha 06.

    Sau mot lan chay day du: moi giai doan `succeeded` phai tro toi mot artifact
    co that, doc duoc, dung checksum. "DONE" khong the tro toi mot thu khong ben.
    """
    from platform_core import jobs
    from platform_core.job_runner import JobContext
    from apps.auto_scan_video import assets, features, pipeline
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    run = _tao_run(db)
    for _ in range(200):
        job = jobs.claim(db, worker_id="w", capabilities={"api", "ffmpeg", "gpu", "voice"})
        if job is None:
            break
        db.commit()
        ctx = JobContext(job.id); ctx.job_type = job.job_type
        try:
            jobs.complete(db, job, jobs.resolve_handler(job.job_type)(
                dict(job.params), ctx) or {})
        except Exception as exc:      # noqa: BLE001
            jobs.fail(db, job, str(exc), retry=False)
        db.commit()
    db.expire_all()

    ds = features.cac_giai_doan(db, run)
    assert len(ds) == len(pipeline.CHUOI)
    for s in ds:
        assert s.status == STAGE_SUCCEEDED, f"{s.stage}: {s.status} {s.error}"
        khoa = (s.outputs or {}).get("khoa_asset") or []
        assert khoa, f"{s.stage} khong tra ve asset ref nao"
        for k in khoa:
            a = assets.asset_cua(db, k, "uA")
            assert assets.kiem_toan_ven(db, kho, a) == "ok", (
                f"{s.stage} DONE nhung artifact khong ben/khong dung")


def test_lineage_noi_giai_doan_voi_thuong_nguon_cua_no(db, kho, asr_gia, dich_gia, giong_gia):
    """Muc 3 — `parent_keys` phai lan nguoc duoc day chuyen tu du lieu.

    Khong co no thi mot nguoi dieu tra phai doc lai ma nguon moi biet cai gi sinh
    ra cai gi — va ma nguon thi doi, con du lieu cu thi o lai.
    """
    from platform_core import jobs
    from platform_core.job_runner import JobContext
    from apps.auto_scan_video import assets, features

    run = _tao_run(db)
    for _ in range(200):
        job = jobs.claim(db, worker_id="w", capabilities={"api", "ffmpeg", "gpu", "voice"})
        if job is None:
            break
        db.commit()
        ctx = JobContext(job.id); ctx.job_type = job.job_type
        try:
            jobs.complete(db, job, jobs.resolve_handler(job.job_type)(
                dict(job.params), ctx) or {})
        except Exception as exc:      # noqa: BLE001
            jobs.fail(db, job, str(exc), retry=False)
        db.commit()
    db.expire_all()

    # `audio_prepare` dan xuat tu `media_prepare`.
    s_truoc = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    khoa_truoc = (s_truoc.outputs or {}).get("khoa_asset") or []
    s_sau = features.giai_doan_theo_ten(db, run.id, "audio_prepare")
    khoa_sau = (s_sau.outputs or {}).get("khoa_asset") or []

    a_sau = assets.asset_cua(db, khoa_sau[0], "uA")
    assert set(khoa_truoc).issubset(set(a_sau.parent_keys)), (
        "artifact ha nguon khong ghi lineage ve thuong nguon")
