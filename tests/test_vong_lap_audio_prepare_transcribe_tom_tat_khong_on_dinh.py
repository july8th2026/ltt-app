"""Vong lap audio_prepare <-> transcribe tren worker THAT (B6, luot 2, 25-26/09).

Bang chung tu luot chay that: 8 tien trinh worker, 2.794,5 s, ket thuc vi
`ReadTimeoutError` tu sidecar WhisperX. Trong luot do `audio_prepare` thu lai
56 lan, `transcribe` thu lai 40 lan (tong 2.059 job; mot luot lanh manh ~23).
Dedupe `advance` (`dang_song` <= 2) DUNG VUNG trong luot do -> day la mot vong
lap KHAC, o tang GIAI DOAN, khong o tang dieu phoi.

## Nghi pham so mot: van tay khong on dinh giua hai lan goi

`thi_hanh._gom_dau_vao` nhet CA outputs THO cua giai doan truoc (khong chi
`fingerprint` cua no) vao chuoi bam `van_tay`. Nhung comment cua CHINH kho nay
(`features.py:327`, `assets.py:645`) mo ta dung mot mo hinh KHAC: "van tay cua
mot giai doan gom VAN TAY (fingerprint) cua cac giai doan truoc" — tuc CHI
fingerprint, khong phai outputs tho.

`giai_doan_am_thanh.chay()` (AUDIO_PREPARE) tra ve `tom_tat` chua du lieu
CHUAN DOAN khong lien quan noi dung: `thiet_bi`, `gpu_cap`, `ten_card`,
`so_khoi`, `khoi_giay`, `f0_trung_vi`... — nhung con so do doi giua hai LAN
THU cua CUNG mot giai doan (may/card/toc do khac nhau), du noi dung am thanh
(`bed.wav`, tuc `phan[].van_tay`) khong doi mot bit nao.

Vi `_gom_dau_vao` bam CA outputs do, moi lan `audio_prepare` thu lai (vi ly do
BAT KY, kem ca `ReadTimeoutError` khong lien quan) deu lam van tay cua
`transcribe` troi — du chinh no khong doi input that. `transcribe` bi dat lai
oan, chay lai (goi WhisperX sidecar THAT), va vi sao no lai lam `audio_prepare`
thu tiep thi khong con quan trong — mot khi da vao vong, no khong tu ra.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import features, pipeline, thi_hanh
from apps.auto_scan_video.tables import AsvRun, AsvStage, STAGE_SUCCEEDED
from tests.conftest import bao_dam_user

CHU = "u-vong-lap-a"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """CSDL SQLite rieng, khong dung ffmpeg/demucs/WhisperX that (tang HAM)."""
    url = f"sqlite:///{(tmp_path / 'vonglap.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_AUTO_SCAN_VIDEO", "1")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    bao_dam_user(s, CHU)
    s.commit()
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _tao_run_toi_thieu(db) -> AsvRun:
    run = AsvRun(owner_id=CHU, contract_version="auto_scan_mvp_v1",
                settings={"timing_mode": "fit_original",
                          "che_do_giong": "AUTO_MATCH",
                          "ngon_ngu_nguon": "en", "ngon_ngu_dich": "vi"},
                source_key="asv/u-vong-lap-a/nguon/goc.mp4")
    db.add(run)
    db.flush()
    return run


def _ghi_thanh_cong(db, run, ten: str, *, outputs: dict) -> AsvStage:
    """Ghi mot giai doan SUCCEEDED dung DUNG duong that: van tay tinh qua
    `thi_hanh.van_tay` + `thi_hanh._gom_dau_vao`, giong het `thi_hanh.chay_giai_doan`
    lam sau khi engine tra ve — vi day la phep kiem tang HAM, khong phai mot ban
    mo phong rieng co the lech khoi ma that."""
    stage = features.giai_doan_theo_ten(db, run.id, ten)
    if stage is None:
        stage = AsvStage(run_id=run.id, owner_id=run.owner_id, stage=ten)
        db.add(stage)
        db.flush()
    vt = thi_hanh.van_tay(ten, run, thi_hanh._gom_dau_vao(db, run.id, ten))
    features.danh_dau_xong(db, stage, outputs=outputs, fingerprint=vt,
                           credit_actual=0)
    db.flush()
    return stage


def _tom_tat_media_prepare() -> dict:
    """Media_prepare — CHI truong NOI DUNG (checksum, thoi luong, codec...).
    On dinh giua hai lan chay cung mot nguon; khong phai nghi pham."""
    return {
        "phan": [
            {"staging_key": "asv/u/mp/ho_so.json", "kind": "json", "duoi": "json",
             "van_tay": "vtjson1"},
            {"staging_key": "asv/u/mp/audio_full.wav", "kind": "audio", "duoi": "wav",
             "van_tay": "vtwav1"},
        ],
        "tom_tat": {
            "checksum_nguon": "sha256-nguon-khong-doi",
            "thoi_luong": 190.0,
            "codec_video": "h264",
            "doc": True,
            "vfr": False,
            "ffmpeg": "6.1.1",
        },
    }


def _tom_tat_audio_prepare(*, thiet_bi: str, so_khoi: int, khoi_giay: float) -> dict:
    """Audio_prepare — CUNG mot `bed.wav` (van_tay/checksum NOI DUNG khong doi)
    nhung `tom_tat` mang CHUAN DOAN doi giua hai lan thu that (thiet bi/toc do
    do demucs chon o lan do, khong phai mot phan cua noi dung am thanh)."""
    return {
        "phan": [
            {"staging_key": "asv/u/ap/bed.wav", "kind": "audio", "duoi": "wav",
             "van_tay": "vt-bed-noi-dung-khong-doi"},
        ],
        "tom_tat": {
            "thiet_bi": thiet_bi,
            "gpu_cap": "" if thiet_bi == "cpu" else "gpu-uuid-1",
            "ten_card": "" if thiet_bi == "cpu" else "RTX 5060 Ti",
            "so_khoi": so_khoi,
            "khoi_giay": khoi_giay,
            "stem_giu": ["drums", "bass", "other"],
            "lop": {},
            "f0_trung_vi": 152.3,
            "f0_ly_do": "",
            "lufs": -23.0,
            "dinh_that": -1.0,
            "thoi_luong": 190.0,
        },
    }


def _tom_tat_transcribe() -> dict:
    return {
        "phan": [
            {"staging_key": "asv/u/tr/transcript.json", "kind": "json",
             "duoi": "json", "van_tay": "vt-transcript-1"},
        ],
        "tom_tat": {"so_doan": 42},
    }


@pytest.fixture()
def chuoi_da_xong(db):
    """MEDIA_PREPARE -> AUDIO_PREPARE -> TRANSCRIBE, ca ba SUCCEEDED, van tay
    tinh dung DUONG THAT — trang thai ma mot advance() dung se thay `[]` lech."""
    run = _tao_run_toi_thieu(db)
    _ghi_thanh_cong(db, run, pipeline.MEDIA_PREPARE, outputs=_tom_tat_media_prepare())
    _ghi_thanh_cong(db, run, pipeline.AUDIO_PREPARE,
                    outputs=_tom_tat_audio_prepare(thiet_bi="cuda", so_khoi=118,
                                                   khoi_giay=41.2))
    _ghi_thanh_cong(db, run, pipeline.TRANSCRIBE, outputs=_tom_tat_transcribe())
    db.commit()
    return run


def test_fixture_tu_no_KHONG_lech(chuoi_da_xong, db):
    """Kiem tinh hop le cua fixture: ngay sau khi ghi, chua ai dong gi, phai
    khong co giai doan nao lech. Neu phep kiem nay do thi loi o FIXTURE, khong
    phai o san pham — sua fixture truoc khi doc cac phep duoi."""
    assert thi_hanh.giai_doan_lech_van_tay(db, chuoi_da_xong) == []


def test_audio_prepare_thu_lai_CUNG_NOI_DUNG_khong_duoc_lam_transcribe_LECH(
        chuoi_da_xong, db):
    """🔴 Phep tai hien RE cua nghi pham so mot (KHONG dung worker that).

    Mo phong DUNG canh B6: `audio_prepare` thu lai (vi ly do bat ky — o day
    khong can ly do, chi can NOI DUNG cua `bed.wav` giu nguyen) va lan nay
    demucs chon CPU thay vi GPU trot lot lan truoc — `thiet_bi`/`so_khoi`/
    `khoi_giay` doi, `van_tay` cua `phan[0]` (noi dung bed.wav that) KHONG doi.

    San pham DUNG: `giai_doan_lech_van_tay` khong duoc bao `transcribe` lech,
    vi cai `transcribe` thuc su can (noi dung am thanh) khong he doi.
    """
    run = chuoi_da_xong
    ap = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE)
    vt_truoc = ap.fingerprint

    _ghi_thanh_cong(db, run, pipeline.AUDIO_PREPARE,
                    outputs=_tom_tat_audio_prepare(thiet_bi="cpu", so_khoi=115,
                                                   khoi_giay=2.4))
    db.commit()

    ap_sau = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE)
    assert ap_sau.fingerprint == vt_truoc, (
        "fixture sai: van tay CUA CHINH audio_prepare doi ca khi input cua no "
        "(media_prepare) khong doi — kiem lai _tom_tat_audio_prepare/van_tay")

    lech_1 = thi_hanh.giai_doan_lech_van_tay(db, run)
    lech_2 = thi_hanh.giai_doan_lech_van_tay(db, run)  # hai lan lien tiep,
    # KHONG dong gi giua hai lan goi — doi hoi cua brief: neu lan hai VAN bao
    # lech thi day la mot phep tai hien on dinh, khong phai mot lan trung hop.
    assert lech_1 == lech_2, "ban than viec kiem cung khong on dinh giua hai lan goi"

    assert pipeline.TRANSCRIBE not in lech_1, (
        "transcribe bi dat lai OAN: bed.wav that (van_tay 'vt-bed-noi-dung-"
        "khong-doi') khong doi, nhung tom_tat CHUAN DOAN (thiet_bi/so_khoi/"
        "khoi_giay) cua audio_prepare doi va _gom_dau_vao bam CA outputs tho "
        "do vao van tay cua transcribe — day chinh la vong lap audio_prepare "
        "<-> transcribe thay tren worker that (B6)")


def test_audio_prepare_doi_ENGINE_that_van_phai_lam_transcribe_lech(
        chuoi_da_xong, db, monkeypatch):
    """Phanh doi trung: neu sua nghi pham so mot bang cach cat trui (bo HET
    day chuyen, khong chi bo `tom_tat`), phep nay se do.

    Mo phong mot lan nang ENGINE THAT cua audio_prepare (dung khuon cua
    `test_415::test_doi_cach_dung_lenh_thi_van_tay_PHAI_doi` da noi trong
    `thi_hanh.phien_ban_engine`): `tach_tieng.PHIEN_BAN_TACH` tang tu 2 len 3.
    Day la mot doi RECIPE that (fingerprint cua CHINH audio_prepare phai doi),
    va no PHAI lan sang transcribe qua `s.fingerprint` — day chuyen I10 phai
    con nguyen, chi rieng `outputs` tho (chan doan) la thu can bo.
    """
    from apps.auto_scan_video import tach_tieng
    run = chuoi_da_xong
    fp_cu = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE).fingerprint

    monkeypatch.setattr(tach_tieng, "PHIEN_BAN_TACH", tach_tieng.PHIEN_BAN_TACH + 1)
    lech_truoc_rerun = thi_hanh.giai_doan_lech_van_tay(db, run)
    assert pipeline.AUDIO_PREPARE in lech_truoc_rerun, (
        "audio_prepare PHAI lech khi engine THAT cua no nang ban — day la ca "
        "ly do `phien_ban_engine` ton tai (xem test_415)")

    # Mo phong audio_prepare DA chay lai that voi engine moi (dung DUONG THAT:
    # `thi_hanh.van_tay` doc `phien_ban_engine` moi -> fingerprint moi), va no
    # DUOC ghi lai thanh cong — dung viec `_vo_hieu_giai_doan_da_lech` lam sau
    # khi dat lai + dieu phoi nop lai giai doan.
    _ghi_thanh_cong(db, run, pipeline.AUDIO_PREPARE,
                    outputs=_tom_tat_audio_prepare(thiet_bi="cuda", so_khoi=118,
                                                   khoi_giay=41.2))
    db.commit()
    fp_moi = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE).fingerprint
    assert fp_moi != fp_cu, "fixture sai: engine nang ban ma fingerprint khong doi"

    lech = thi_hanh.giai_doan_lech_van_tay(db, run)
    assert pipeline.TRANSCRIBE in lech, (
        "transcribe PHAI lech khi fingerprint THAT cua audio_prepare doi — day "
        "la day chuyen vo hieu I10 that (qua `s.fingerprint`); dung sua nham "
        "thanh 'khong bao gio lech'")
