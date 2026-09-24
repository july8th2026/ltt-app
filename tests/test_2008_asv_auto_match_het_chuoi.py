"""R-01 §3 — `AUTO_MATCH` chay HET CHUOI, tren CA HAI preset.

🔴 **Bai nay ton tai vi mot luot chay THAT da chet.** `NEN_V3` luot A
   (`docs/auto_scan_video_final/bang_chung/NEN_V3.md`): preset giu hinh,
   `AUTO_MATCH`, phim khach that — chet o `content_process` voi `ChuaRangError`
   sau 133 giay demucs + ASR da tra tien. Khong mot phep kiem nao trong kho bat
   duoc, vi moi phep kiem chay het chuoi deu nop `giong_id` (`USER_SELECTED`).

⭐ Va **hai** preset chu khong mot, vi do la ca nua thu hai cua lo hong:
   `localize_preserve_picture` khong doc mot canh nao (khong canh nao bi cat ⇒
   khong co gi de hoi VLM), nen mot ban sua di qua duong VLM se xanh o
   `smart_localize` va van chet o preset mac dinh.

Hang doi that, worker that, dinh tuyen that, ffmpeg that, kho that, CSDL that.
Chi mieng NANG (demucs, ASR, may sinh tieng, model) la gia — khuon cua
`test_402`.
"""
from __future__ import annotations

import pytest

from tests.conftest import bao_dam_user
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401

PRESET_GIU = "localize_preserve_picture"
PRESET_CAT = "smart_localize"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'asv2008.db').as_posix()}"
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
def kho_tam(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(str(tmp_path / "kho")))
    yield
    set_storage(None)


@pytest.fixture()
def may_gia(monkeypatch, tmp_path):
    """ASR + may sinh tieng + cua model — ba mieng nang, mot cho.

    ⛔ `cua_ai_gia` la cua DUY NHAT moi loi goi model cua app di qua, ke ca lan
       goi `ho_so_noi_dung` moi them. Dat mot ban thay the rieng cho thao tac
       moi la lam lai dung ba-ban-sao ma `cua_ai_gia` sinh ra de dep.
    """
    import subprocess
    from pathlib import Path

    from platform_core import media
    from apps.auto_scan_video import giai_doan_chep_loi, giong_noi
    from tests.fixtures.asv_media import ban_ghi_gia, cua_ai_gia

    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: ban_ghi_gia())
    cua_ai_gia(monkeypatch)

    mau = Path(tmp_path) / "_giong_mau.wav"
    subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
         "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(mau)],
        check=True, capture_output=True)
    du_lieu = mau.read_bytes()
    monkeypatch.setattr(giong_noi, "san_sang", lambda: True)
    monkeypatch.setattr(giong_noi, "giai_giong", lambda db, **kw: (None, "bac"))
    monkeypatch.setattr(giong_noi, "doc_mot_doan", lambda chu, **kw: (du_lieu, {}))
    return True


def _tao_run(db, tmp_path, *, preset: str, owner="uA"):
    """Mot lan chay `AUTO_MATCH` — **khong** nop `giong_id`.

    🔑 Day la khac biet duy nhat so voi moi phep kiem chay het chuoi khac trong
       kho, va no la ly do lo hong song duoc qua 27 pha: tat ca chung deu nop
       mot ma giong, tuc tat ca deu di duong `USER_SELECTED`.
    """
    from pathlib import Path

    from platform_core import credit
    from platform_core.storage import get_storage
    from apps.auto_scan_video import features
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    bao_dam_user(db, owner)
    credit.nap(db, owner, 1000)
    khoa = nap_nguon_vao_kho(get_storage(), Path(tmp_path), owner_id=owner)
    run = features.tao_run(
        db, owner_id=owner, source_key=khoa,
        settings={"che_do_giong": "AUTO_MATCH", "preset": preset,
                  "timing_mode": "fit_original"},
        uoc_luong_credit=10)
    db.commit()
    return run


def _chay_het_hang_doi(db, *, toi_da=200) -> None:
    from platform_core import jobs
    from platform_core.job_runner import JobContext

    for _ in range(toi_da):
        job = jobs.claim(db, worker_id="w-2008",
                         capabilities={"api", "ffmpeg", "gpu", "voice"})
        if job is None:
            break
        db.commit()
        handler = jobs.resolve_handler(job.job_type)
        ctx = JobContext(job.id)
        ctx.job_type = job.job_type
        try:
            jobs.complete(db, job, handler(dict(job.params), ctx) or {})
        except Exception as exc:                            # noqa: BLE001
            jobs.fail(db, job, str(exc), retry=False)
        db.commit()
    # Phien cua test van cam ban ghi cu (`expire_on_commit=False`) — xem
    # `test_402._chay_het_hang_doi`.
    db.expire_all()


def _giai_doan(db, run, ten):
    from apps.auto_scan_video import features

    return features.giai_doan_theo_ten(db, run.id, ten)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Mot giong DUOC CHOT — o CA HAI preset
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("preset", [PRESET_GIU, PRESET_CAT])
def test_AUTO_MATCH_chot_duoc_giong_va_chay_het_chuoi(db, kho_tam, tmp_path,
                                                      may_gia, preset):
    from apps.ltt_voice.giong_mau import hop_le as la_giong_mau
    from apps.auto_scan_video import features, pipeline, rang_giong
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    run = _tao_run(db, tmp_path, preset=preset)
    _chay_het_hang_doi(db)
    run = features.lay_run(db, run.id, "uA")

    gd = _giai_doan(db, run, pipeline.CONTENT_PROCESS)
    assert gd is not None and gd.status == STAGE_SUCCEEDED, (
        f"[{preset}] content_process khong xanh: "
        f"{getattr(gd, 'status', None)} / {getattr(gd, 'error', None)}")

    # 🔑 Giong den tu NOI DUNG, khong tu mot gia tri mac dinh.
    assert (gd.outputs or {}).get("nguon_giong") == rang_giong.NGUON_TU_KHOP

    ma_giong = str((run.settings or {}).get("giong_id") or "")
    ho_so = dict((run.settings or {}).get("dac_diem_giong") or {})
    assert ho_so, f"[{preset}] khong ho so nao duoc ghi xuong"

    # Ban long tieng phai mang DUNG ma giong da chot — do dai cau duoc nan theo
    # toc do doc cua giong do, nen mot ma khac o day la mot ban viet mu.
    ban = _ban_long_tieng(db, run)
    assert la_giong_mau(str(ban.get("ma_giong") or "")), (
        f"[{preset}] ma giong khong thuoc catalog: {ban.get('ma_giong')!r}")
    assert ma_giong in ("", str(ban.get("ma_giong")))


def _ban_long_tieng(db, run) -> dict:
    import json

    from platform_core.storage import get_storage
    from apps.auto_scan_video import features, pipeline

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    khoa = next(k for k in ((gd.outputs or {}).get("khoa_asset") or [])
                if k.endswith(".json"))
    with get_storage().open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def test_preset_GIU_HINH_khong_phai_tra_tien_mot_luot_doc_canh(db, kho_tam,
                                                               tmp_path, may_gia):
    """⛔ Ban sua khong duoc keo preset giu hinh vao mot luot VLM.

    `edit_plan` cua preset nay co chu dinh la mot duong **re tien**: mot chi muc
    mot-canh, khong khung hinh nao, khong mot lan goi model nao. Neu ho so noi
    dung di qua VLM thi con so duoi day khac 0, va khac biet gia giua hai preset
    bien mat.
    """
    from apps.auto_scan_video import features, pipeline

    run = _tao_run(db, tmp_path, preset=PRESET_GIU)
    _chay_het_hang_doi(db)
    run = features.lay_run(db, run.id, "uA")

    gd = _giai_doan(db, run, pipeline.EDIT_PLAN)
    assert int((gd.outputs or {}).get("so_canh_da_doc") or 0) == 0
    assert int((gd.outputs or {}).get("so_canh") or 0) == 1


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Khong co can cu thi DUNG LAI — khong roi ve giong mac dinh
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_du_can_cu_thi_DUNG_LAI_chu_khong_lay_giong_mac_dinh(
        db, kho_tam, tmp_path, may_gia, monkeypatch):
    """🔴 Nua kia cua `ADR-V4-001` D-V4-04, va la nua de mat hon.

    Mot ban sua "cho AUTO_MATCH chay duoc" rat de bien thanh "AUTO_MATCH luon
    chon dai mot giong". Bai nay dung phep do F0 im lang (video fixture la mot
    sin 440 Hz — ngoai khoang tieng noi) CONG voi mot model khong tra loi duoc,
    tuc **khong mot mat nao** co can cu, roi doi lan chay phai dung lai.
    """
    from apps.auto_scan_video import features, ho_so_noi_dung, pipeline
    from apps.auto_scan_video.tables import STAGE_SUCCEEDED

    monkeypatch.setattr(ho_so_noi_dung, "_hoi_model",
                        lambda db, run, **kw: None)

    run = _tao_run(db, tmp_path, preset=PRESET_GIU)
    _chay_het_hang_doi(db)
    run = features.lay_run(db, run.id, "uA")

    gd = _giai_doan(db, run, pipeline.CONTENT_PROCESS)
    assert gd is not None and gd.status != STAGE_SUCCEEDED
    # ⭐ Va cau loi phai chi cho khach loi ra, khong phai mot ma loi.
    assert "tự chọn" in str(gd.error or ""), gd.error
    # ⛔ Va KHONG mot giong nao duoc ghi len lan chay.
    assert not dict((run.settings or {}).get("dac_diem_giong") or {})
    assert not str((run.settings or {}).get("giong_id") or "")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Ho so chi duoc dung MOT lan cho ca lan chay
# ══════════════════════════════════════════════════════════════════════════════

def test_luot_chay_lai_KHONG_hoi_model_lan_hai(db, kho_tam, tmp_path, may_gia,
                                               monkeypatch):
    """⭐ Van tay cua `content_process` co `ma_giong` trong do: mot ho so sinh
    lai moi luot co the cho ra mot giong khac, va khi do MOI diem chot cua
    nhung lo da tra tien deu khong con tinh — tuc hoa don nhan doi moi lan
    worker sap."""
    from apps.auto_scan_video import features, ho_so_noi_dung

    run = _tao_run(db, tmp_path, preset=PRESET_GIU)
    _chay_het_hang_doi(db)
    run = features.lay_run(db, run.id, "uA")
    lan_dau = ho_so_noi_dung.loc_dac_diem(
        (run.settings or {}).get("dac_diem_giong") or {})
    assert lan_dau

    dem = {"n": 0}

    def dem_len(db_, run_, **kw):
        dem["n"] += 1
        return None

    monkeypatch.setattr(ho_so_noi_dung, "_hoi_model", dem_len)
    lai = ho_so_noi_dung.bao_dam(db, run, ban_ghi={"doan": []})
    assert dem["n"] == 0, "goi model lan hai cho cung mot lan chay"
    assert lai.get("dac_diem_giong") == lan_dau


def test_ghi_ho_so_KHONG_dat_lai_demucs_va_ASR(db, kho_tam, tmp_path, may_gia):
    """🔴 **Lo hong thu hai cua cung mot ban sua, va no dot dung 133 giay ay.**

    `thi_hanh.van_tay` gom CA `run.settings` vao van tay giai doan, va
    `jobs._vo_hieu_giai_doan_da_lech` dat lai moi giai doan lech. Nen ban nhap
    dau cua duong nay — ghi `dac_diem_giong` vao `settings` giua chuoi — lam
    xuat hien dong log *"dat lai 5 giai doan do lech van tay"*: `media_prepare`,
    `audio_prepare`, `transcribe`, `edit_plan` chay LAI tu dau. Tuc demucs + ASR
    tra tien hai lan, dung khoan ma `NEN_V3` luot A da dot, chi khac cach dot.

    ⇒ `cai_dat.KHOA_DAN_XUAT` loai hai khoa do khoi van tay giai doan. Bai nay
      do dieu do tren mot lan chay THAT da ghi ho so, chu khong do ham loc.
    """
    from apps.auto_scan_video import features, thi_hanh

    run = _tao_run(db, tmp_path, preset=PRESET_GIU)
    _chay_het_hang_doi(db)
    run = features.lay_run(db, run.id, "uA")
    assert (run.settings or {}).get("dac_diem_giong"), "chua ghi ho so nao"

    assert thi_hanh.giai_doan_lech_van_tay(db, run) == [], (
        "ghi ho so noi dung lam lech van tay giai doan — demucs va ASR se chay lai")
