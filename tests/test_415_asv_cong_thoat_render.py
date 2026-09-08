"""Pha 15 — CONG THOAT.

Prompt 15 phat bieu cong thoat bang mot cau: *mot ban dung da luu, MOT MINH,
phai tai tao duoc mot tep media da kiem.* `test_414` kiem tung manh cua trinh
render; tep nay kiem dung cau do, va no phai di qua **hang doi that + worker
that** moi co nghia — mot phep kiem goi thang `giai_doan_ket_xuat.chay` se bo
qua chinh thu dang duoc khang dinh (rang khong giai doan nao khac bi danh thuc).
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from platform_core.storage import get_storage

from apps.auto_scan_video import features, ket_xuat, nhap_media, pipeline
from apps.auto_scan_video.tables import (AsvAsset, RUN_RUNNING, STAGE_PENDING,
                                          STAGE_SUCCEEDED)
from tests.fixtures import asv_media as fx

# Dung lai bo do cua pha 05: hang doi that, worker that, chi cong viec ben trong
# la gia. `noqa` vi pytest can chung o pham vi module de tiem fixture.
from tests.test_402_asv_mach_doc_gia import (  # noqa: F401
    _chay_het_hang_doi, _tao_run, asr_gia, db, dich_gia, giong_gia, kho_tam)

# 🔴 Pha 13: cac phep kiem trong tep nay chay HET chuoi, nen chung cham toi
#    `audio_prepare` — va truoc pha 13 dieu do co nghia la chung nap
#    **htdemucs THAT** moi luot gate, tren mot may dang phuc vu khach.
#    Fixture autouse duoi day thay dung mieng nang do; ffmpeg, kho, CSDL,
#    hang doi va worker van that.  (`LTT_TEST_NANG=1` de chay model that)
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401

NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}


def _render(db_, run):
    s = features.giai_doan_theo_ten(db_, run.id, pipeline.RENDER)
    khoa = ((s.outputs or {}).get("khoa_asset") or [None])[0] if s else None
    return khoa, s


def _ha_render_ve_pending(db_, run):
    """Xoa ket qua RENDER (ca so lan bytes) va dat giai doan ve `pending`.

    ⚠️ Kho lay qua `get_storage()`, khong qua fixture: `kho_tam` chi CAI DAT kho
       toan cuc roi `yield` rong, nen nhan gia tri cua no se duoc `None`.
    """
    kho = get_storage()
    khoa, _ = _render(db_, run)
    assert khoa, "chua co ket qua RENDER de xoa"
    a = db_.execute(select(AsvAsset).where(
        AsvAsset.storage_key == khoa)).scalars().one()
    kho.delete(khoa)
    db_.delete(a)
    s = features.giai_doan_theo_ten(db_, run.id, pipeline.RENDER)
    # ⚠️ Rong = `""` / `{}`, KHONG phai `None`. Bon cot nay deu NOT NULL, va
    #    `outputs=None` bien thanh chuoi JSON `'null'` chu khong thanh NULL —
    #    tuc "khong co ket qua" va "ket qua la null" la hai thu khac nhau.
    s.status = STAGE_PENDING
    s.fingerprint = ""
    s.outputs = {}
    s.job_id = ""
    s.error = ""

    # 🔑 Va danh thuc lai dieu phoi vien. Ha mot giai doan ve `pending` KHONG tu
    #    lam viec do: `advance` chi tu nop lai chung nao run con song, va run nay
    #    da ve `done`. Ban dau phep kiem nay thieu hai dong duoi va no do voi mot
    #    van tay RONG — tuc RENDER khong chay lai chut nao, chu khong phai chay
    #    lai rồi ra sai.
    run_ = features.lay_run(db_, run.id, run.owner_id)
    run_.status = RUN_RUNNING
    features._nop_dieu_phoi(db_, run_, ly_do="kiem-render-lai")
    db_.commit()
    return khoa


@pytest.fixture()
def run_da_chay(db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    return run


def test_RENDER_that_su_sinh_ra_mot_mp4_PHAT_DUOC(run_da_chay, db, tmp_path):
    """⛔ Chot rang RENDER chay engine THAT, khong roi vao `_engine_gia`.

    Khong chot bang "giai doan bao succeeded" — engine gia cung bao succeeded,
    va suot cac pha 05-14 no da bao dung nhu the. Chot bang cach **soi tep ra
    bang ffprobe**: mot engine gia khong sinh ra duoc mot mp4 co luong hinh
    h264 va luong tieng aac.
    """
    khoa, s = _render(db, run_da_chay)
    assert s.status == STAGE_SUCCEEDED
    assert khoa and khoa.endswith(".mp4"), f"RENDER khong ra mp4: {khoa!r}"

    ra = tmp_path / "kiem.mp4"
    with get_storage().open(khoa) as f:
        ra.write_bytes(f.read())

    tt = nhap_media.soi(str(ra))
    assert tt["co_video"] and tt["co_tieng"]
    assert tt["codec_video"] == "h264", "hinh bi ma hoa lai — mat `-c:v copy`"
    assert tt["codec_tieng"] == "aac"
    assert tt["tan_so"] == 48000 and tt["so_kenh"] == 2
    assert tt["thoi_luong"] > 0 and tt["co_byte"] > 0


def test_render_lai_KHONG_danh_thuc_mot_giai_doan_thuong_nguon_nao(
        run_da_chay, db):
    """🔑 CHINH LA CONG THOAT.

    Xoa ket qua RENDER roi chay lai. Neu ban dung that su du de tai tao ket qua
    thi **khong giai doan nao khac** duoc dong vao — dac biet CONTENT (goi
    model) va VOICE (sinh tieng), vi chay lai chung la tra tien lan hai cho
    cung mot ban dich.
    """
    truoc = {s.stage: (s.status, s.fingerprint)
             for s in features.cac_giai_doan(db, run_da_chay)}
    _ha_render_ve_pending(db, run_da_chay)

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    khoa_sau, s_sau = _render(db, run_da_chay)
    assert khoa_sau, "khong tai tao duoc ket qua tu ban dung"
    assert s_sau.status == STAGE_SUCCEEDED

    sau = {s.stage: (s.status, s.fingerprint)
           for s in features.cac_giai_doan(db, run_da_chay)}
    for ten in pipeline.TEN_GIAI_DOAN:
        if ten == pipeline.RENDER:
            continue
        assert sau[ten] == truoc[ten], (
            f"giai doan {ten} bi dong vao trong mot lan render lai — "
            f"ban dung chua du de tai tao mot minh")


def test_render_lai_ra_DUNG_van_tay_cu(run_da_chay, db):
    """Van tay giong nhau ⇒ cung dau vao, cung cach dung lenh.

    Neu no doi thi hoac ban dung khong tat dinh, hoac van tay dang bo qua mot
    dau vao — va ca hai deu lam cache sai: mot lan chay lai se **tinh tien lai**
    cho mot ket qua khong doi.
    """
    _, s_truoc = _render(db, run_da_chay)
    vt = s_truoc.fingerprint
    _ha_render_ve_pending(db, run_da_chay)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    _, s_sau = _render(db, run_da_chay)
    assert s_sau.fingerprint == vt


def test_doi_cach_dung_lenh_thi_van_tay_PHAI_doi(run_da_chay, db, monkeypatch):
    """Chieu nguoc lai cua phep kiem tren, va la thu de quen han.

    Neu `PHIEN_BAN_KET_XUAT` khong nam trong van tay thi mot lan sua cach dung
    lenh ffmpeg se **dung lai tep cu tu cache** va khong ai thay cach dung lenh
    moi — mot ban va da giao nhung chua bao gio chay.
    """
    _, s_truoc = _render(db, run_da_chay)
    vt = s_truoc.fingerprint
    _ha_render_ve_pending(db, run_da_chay)

    monkeypatch.setattr(ket_xuat, "PHIEN_BAN_KET_XUAT",
                        ket_xuat.PHIEN_BAN_KET_XUAT + 1)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    _, s_sau = _render(db, run_da_chay)
    assert s_sau.fingerprint != vt, (
        "doi cach dung lenh ma van tay khong doi — mot lan chay lai se dung "
        "lai tep cu va ban sua khong bao gio chay")


def test_render_hong_KHONG_de_lai_ket_qua_dang_do(run_da_chay, db, monkeypatch):
    """Muc 10: mot lan ngat khong bao gio duoc de lo mot tep dang do.

    Mot tep dang do trong kho **trong y het** mot ket qua that — do moi la ly
    do phai ghi tam roi promote, chu khong phai vi gon gang.
    """
    _ha_render_ve_pending(db, run_da_chay)

    def _no(*_a, **_k):
        raise ket_xuat.KetXuatError("ep hong giua chung")
    monkeypatch.setattr(ket_xuat, "_chay_co_tien_do", _no)

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    khoa_sau, s_sau = _render(db, run_da_chay)
    assert not khoa_sau, "mot lan render hong da de lai mot khoa ket qua"
    assert s_sau.status != STAGE_SUCCEEDED
    con = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run_da_chay.id,
        AsvAsset.created_by_stage == pipeline.RENDER)).scalars().all()
    assert con == [], "co artifact RENDER trong so du render that bai"


def test_thieu_mot_tep_tieng_thi_DUNG_TRUOC_khi_ton_suat_render(
        run_da_chay, db, monkeypatch):
    """Muc 3: doi chieu MOI tham chieu truoc khi chay.

    Mot ban dung tro toi mot artifact khong con la mot lan render that bai o
    phut thu muoi — sau khi da chiem suat, da tai tep, da giai ma. Phai dung o
    buoc doi chieu, va phai dung **truoc** khi ffmpeg duoc goi.
    """
    from apps.auto_scan_video import giai_doan_giong  # noqa: F401 - chi de dinh vi

    # Xoa mot tep tieng cua VOICE khoi kho, giu nguyen ban ghi trong so.
    a = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run_da_chay.id,
        AsvAsset.created_by_stage == pipeline.VOICE_SYNTHESIS)).scalars().first()
    # ⛔ KHONG `pytest.skip`. Bo do nay chay ca chuoi voi `giong_gia`, nen mot
    #    lan chay khong sinh ra tep tieng nao la mot LOI dang bao, khong phai
    #    mot dieu kien moi truong dang bo qua. Va mot test bi bo qua la mot test
    #    khong canh gi ca — no se lam banh coc `check_bo_qua` bao mot muc moi,
    #    dung nhu no da bao khi ban dau cho nay la mot `skip`.
    assert a is not None, "chuoi khong sinh ra tep tieng nao — bo do da hong"
    get_storage().delete(a.storage_key)

    _ha_render_ve_pending(db, run_da_chay)

    da_goi = []
    that = ket_xuat._chay_co_tien_do
    monkeypatch.setattr(ket_xuat, "_chay_co_tien_do",
                        lambda *a_, **k_: (da_goi.append(1), that(*a_, **k_))[1])

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    khoa_sau, s_sau = _render(db, run_da_chay)
    assert not khoa_sau
    assert s_sau.status != STAGE_SUCCEEDED
    assert da_goi == [], "ffmpeg da duoc goi du mot tham chieu da hong"
