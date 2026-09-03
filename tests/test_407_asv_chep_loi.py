"""Auto Scan Video — TRANSCRIBE: hop dong ban ghi, boc engine, van tay.

## Bo cuc

  §1 hop dong ban ghi     — chuan hoa + kiem, khong can engine
  §2 boc engine           — doi chieu voi duong dang chay cua `autosubvideo`
  §3 van tay va cache
  §4 cong thoat
  §5 cho bang chung ngoai

⛔ Prompt 10 cam: khong dich, khong TTS trong giai doan nay.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests import rao_chan_nang

from tests.fixtures.asv_media import ban_ghi_gia, require_ffmpeg


def _wav_16k(dich: Path, *, giay: float = 2.0, hz: int = 300) -> Path:
    from platform_core import media
    require_ffmpeg()
    dich.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"sine=frequency={hz}:duration={giay}",
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dich)],
        check=True, capture_output=True)
    return dich


# ══════════════════════════════════════════════════════════════════════════════
#  §1 Hop dong ban ghi
# ══════════════════════════════════════════════════════════════════════════════

def test_chuan_hoa_gan_ma_doan_theo_thu_tu_thoi_gian():
    """Muc 4 — ma doan on dinh trong pham vi mot ban ghi.

    Doan duoc sap theo thoi gian TRUOC khi danh ma, nen engine tra ve lon xon
    cung ra cung mot ket qua.
    """
    from apps.auto_scan_video import ban_ghi

    tho = {"segments": [
        {"start": 2.0, "end": 3.0, "text": "sau", "words": []},
        {"start": 0.0, "end": 1.0, "text": "truoc", "words": []},
    ], "language": "vi"}
    ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=5.0)

    assert [d["ma"] for d in ban["doan"]] == ["seg_0001", "seg_0002"]
    assert ban["doan"][0]["chu"] == "truoc"


def test_chuan_hoa_BO_doan_rong_thay_vi_giu():
    """Mot doan khong co chu khong co gi de dich va khong co gi de doc — nhung
    no VAN chiem mot khe thoi gian, va TIMING se chen mot khoang lang vao do."""
    from apps.auto_scan_video import ban_ghi

    tho = {"segments": [
        {"start": 0.0, "end": 1.0, "text": "co chu", "words": []},
        {"start": 1.0, "end": 2.0, "text": "   ", "words": []},
    ]}
    ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=5.0)
    assert len(ban["doan"]) == 1


def test_chuan_hoa_TU_CHOI_ban_ghi_khong_co_loi_noi():
    """Hanh vi san pham, khong phai mot loi ky thuat.

    Mot video khong co loi noi thi khong co gi de long tieng. Chap nhan mot ban
    ghi rong o day nghia la de chuoi chay tiep qua bon giai doan co tinh tien roi
    giao mot ban long tieng khong co tieng nao.
    """
    from apps.auto_scan_video import ban_ghi

    with pytest.raises(ban_ghi.BanGhiError):
        ban_ghi.chuan_hoa({"segments": []}, thoi_luong_nguon=5.0)


def test_kiem_BAT_doan_chong_thoi_gian_len_nhau():
    """⛔ Loi chet nguoi o ha nguon: TIMING se chen hai doan tieng vao cung mot
    khe, va ban long tieng se co hai giong noi de len nhau."""
    from apps.auto_scan_video import ban_ghi

    ban = {"schema": ban_ghi.SCHEMA_BAN_GHI, "doan": [
        {"ma": "seg_0001", "bat": 0.0, "ket": 2.0, "chu": "a", "tu": []},
        {"ma": "seg_0002", "bat": 1.0, "ket": 3.0, "chu": "b", "tu": []},
    ]}
    with pytest.raises(ban_ghi.BanGhiError):
        ban_ghi.kiem(ban)


def test_kiem_BAT_ma_doan_trung():
    from apps.auto_scan_video import ban_ghi

    ban = {"schema": ban_ghi.SCHEMA_BAN_GHI, "doan": [
        {"ma": "seg_0001", "bat": 0.0, "ket": 1.0, "chu": "a", "tu": []},
        {"ma": "seg_0001", "bat": 1.0, "ket": 2.0, "chu": "b", "tu": []},
    ]}
    with pytest.raises(ban_ghi.BanGhiError):
        ban_ghi.kiem(ban)


def test_kiem_BAT_tu_nam_ngoai_doan_chua_no():
    """Moc thoi gian cua tu la thu TIMING dung de chia nho. Mot tu nam ngoai
    doan cua no la mot moc da troi, va no se troi tiep o ha nguon."""
    from apps.auto_scan_video import ban_ghi

    ban = {"schema": ban_ghi.SCHEMA_BAN_GHI, "doan": [
        {"ma": "seg_0001", "bat": 1.0, "ket": 2.0, "chu": "a",
         "tu": [{"bat": 0.0, "ket": 0.5, "chu": "lac"}]},
    ]}
    with pytest.raises(ban_ghi.BanGhiError):
        ban_ghi.kiem(ban)


def test_kiem_BAT_ban_ghi_sai_phien_ban_cau_truc():
    """Doc mot ban ghi cu bang luat moi la mot loi phan tich im lang."""
    from apps.auto_scan_video import ban_ghi

    ban = {"schema": 99, "doan": [
        {"ma": "seg_0001", "bat": 0.0, "ket": 1.0, "chu": "a", "tu": []}]}
    with pytest.raises(ban_ghi.BanGhiError):
        ban_ghi.kiem(ban)


def test_chuan_hoa_GIU_NGUYEN_trang_thai_canh_chinh_cua_engine():
    """⛔ `whisperx` canh theo tung tu; faster-whisper thi khong va tu khai
    `fallback_unaligned`. Giau khac biet do la hua mot do chinh xac thoi gian
    ma ta khong co."""
    from apps.auto_scan_video import ban_ghi

    tho = dict(ban_ghi_gia(2.0))
    tho["alignment_status"] = "fallback_unaligned"
    ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=5.0)
    assert ban["canh_chinh"] == "fallback_unaligned"


def test_tom_tat_KHONG_chua_loi_thoai():
    """Tom tat di vao `stage.outputs` va vao log. Loi thoai cua khach khong
    thuoc ve mot dong log."""
    from apps.auto_scan_video import ban_ghi

    ban = ban_ghi.chuan_hoa(ban_ghi_gia(3.0), thoi_luong_nguon=5.0)
    goi = repr(ban_ghi.tom_tat(ban))
    assert "cau thu" not in goi, "loi thoai lot vao tom tat"
    assert ban_ghi.tom_tat(ban)["so_doan"] == 3


# ══════════════════════════════════════════════════════════════════════════════
#  §2 Boc engine — doi chieu voi duong dang chay
# ══════════════════════════════════════════════════════════════════════════════

class TestBocEngine:
    """Doi chieu (parity) voi `apps/autosubvideo/transcription.py:162`.

    ⚠️ Kho di san `Bot_Whisper_FULL` **khong co bo test nao** (GAP-00-C), va hai
       cho trong no goi `gpu_arbiter.current_gpu` — tuc no tu chon card, dung thu
       I11/O6 cam. Nen "ban goc" de doi chieu o day la duong **dang chay trong
       nen tang**, khong phai kho di san.

    ⭐ Va do la mot phep doi chieu manh hon: no chot rang lop boc cua ta khong
       lam doi thu engine sinh ra.
    """

    def test_boc_KHONG_doi_ket_qua_cua_engine(self, tmp_path, monkeypatch):
        """`chep_loi` phai la mot lop chuyen tiep, khong phai mot lop bien doi."""
        from apps.auto_scan_video import giai_doan_chep_loi

        goi_voi = {}

        def engine_gia(duong, **kw):
            goi_voi.update({"duong": duong, **kw})
            return ban_ghi_gia(2.0)

        monkeypatch.setattr("apps.autosubvideo.transcription.transcribe_file",
                            engine_gia)
        ra = giai_doan_chep_loi.chep_loi("/duong/a.wav", ngon_ngu="vi")

        assert ra == ban_ghi_gia(2.0), "lop boc da sua ket qua cua engine"
        assert goi_voi["duong"] == "/duong/a.wav"
        assert goi_voi["language"] == "vi"
        assert goi_voi["model_name"] == giai_doan_chep_loi.MODEL_ASR

    def test_boc_CHUYEN_TIEP_card_do_nen_tang_cap(self, monkeypatch):
        """I11/O6 — `gpu_uuid` den tu `JobContext`, khong bao gio tu chon.

        `transcription._env_ghim_gpu` goi `platform_core.gpu.env_for(uuid)`, tuc
        chinh duong nen tang dung. Ta chi phai chuyen tiep dung id.
        """
        from types import SimpleNamespace

        from apps.auto_scan_video import giai_doan_chep_loi

        bat = {}
        monkeypatch.setattr("apps.autosubvideo.transcription.transcribe_file",
                            lambda d, **kw: bat.update(kw) or ban_ghi_gia(1.0))

        ctx = SimpleNamespace(gpu_uuid="GPU-abc", progress=None,
                              is_cancelled=None)
        giai_doan_chep_loi.chep_loi("/a.wav", ctx=ctx)
        assert bat["gpu_uuid"] == "GPU-abc", "card da cap khong toi engine"

    def test_boc_CHUYEN_TIEP_tien_do_va_huy(self, monkeypatch):
        from types import SimpleNamespace

        from apps.auto_scan_video import giai_doan_chep_loi

        bat = {}
        monkeypatch.setattr("apps.autosubvideo.transcription.transcribe_file",
                            lambda d, **kw: bat.update(kw) or ban_ghi_gia(1.0))

        tien_do = lambda *a: None      # noqa: E731
        huy = lambda: False            # noqa: E731
        ctx = SimpleNamespace(gpu_uuid="", progress=tien_do, is_cancelled=huy)
        giai_doan_chep_loi.chep_loi("/a.wav", ctx=ctx)

        assert bat["on_progress"] is tien_do
        assert bat["is_cancelled"] is huy

    def test_canh_lien_app_da_duoc_KHAI_o_ca_hai_phia(self):
        """Hop dong app doi hai ban khai khop nhau chinh xac.

        ⭐ `autosubvideo` KHONG bi sua dong logic nao — chi them mot ban khai
           rang mot cai ten da la cong khai. Duong cu cua no chay nguyen, dung
           dieu O10 va cong thoat pha 10 doi.
        """
        import apps.autosubvideo as auto_sub
        from tools.lint_app_contract import APP_DUOC_DUNG_APP

        can = ("apps.autosubvideo.transcription", "transcribe_file")
        assert can in auto_sub.BE_MAT_CONG_KHAI
        assert can in APP_DUOC_DUNG_APP[("auto_scan_video", "autosubvideo")]


@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_engine_ASR_that_chay_duoc(tmp_path):
    """Smoke THAT voi faster-whisper. Model da nam trong cache HF.

    Do tren may nay: 2 giay tieng, model `tiny`, CPU -> **22,8 giay**.

    ⭐ Ket qua la **khong doan nao**, va do la dung: fixture la mot am sin, khong
       co loi noi. Phep kiem nay chot **duong goi engine**, khong chot do chinh
       xac nhan dang — thu do can mot mau tieng noi that (xem §5).
    """
    import os

    from apps.autosubvideo.transcription import transcribe_file

    os.environ["LTT_AUTOSUB_WHISPER_DEVICE"] = "cpu"
    os.environ["LTT_AUTOSUB_WHISPER_COMPUTE"] = "int8"

    ra = transcribe_file(str(_wav_16k(tmp_path / "a.wav", giay=1.0)),
                         language="", model_name="tiny")

    assert isinstance(ra, dict)
    assert "segments" in ra and isinstance(ra["segments"], list)
    assert ra.get("engine"), "engine phai tu khai ten"
    # `whisperx` khong duoc cai o day, nen duong chay la faster-whisper.
    assert ra["engine"] == "faster-whisper"
    assert ra.get("alignment_status") == "fallback_unaligned"


# ══════════════════════════════════════════════════════════════════════════════
#  §3 Van tay
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_doi_theo_tieng_model_ngon_ngu_va_ma():
    from apps.auto_scan_video import ban_ghi

    goc = dict(checksum_tieng="aaa", model="large-v3", ngon_ngu="vi",
               phien_ban_ma=1)
    nen = ban_ghi.van_tay_ban_ghi(**goc)

    assert nen != ban_ghi.van_tay_ban_ghi(**{**goc, "checksum_tieng": "bbb"})
    assert nen != ban_ghi.van_tay_ban_ghi(**{**goc, "model": "medium"})
    assert nen != ban_ghi.van_tay_ban_ghi(**{**goc, "ngon_ngu": "en"})
    assert nen != ban_ghi.van_tay_ban_ghi(**{**goc, "phien_ban_ma": 2})


# ══════════════════════════════════════════════════════════════════════════════
#  §4 Cong thoat
# ══════════════════════════════════════════════════════════════════════════════

def test_cong_thoat_TRANSCRIBE_la_job_con_doc_lap(tmp_path, monkeypatch):
    """Cong thoat pha 10: giai doan chay nhu MOT JOB CON DOC LAP.

    Chot ba dieu: no la mot `Job` rieng thuoc app `asv_gpu` (tuc lan GPU), no
    sinh ra mot ban ghi ben vung kiem duoc, va ma doan giu nguyen tu ban ghi ra
    `outputs` — thu ma CONTENT_PROCESS se bam vao.
    """
    import json

    import platform_core.db as dbmod
    from platform_core import credit, jobs
    from platform_core.job_runner import JobContext
    from platform_core.models import Job
    from platform_core.storage import LocalStorage, set_storage
    from sqlalchemy import select
    from tests.conftest import bao_dam_user
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'p10.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)

    from apps.auto_scan_video import assets, ban_ghi, features, giai_doan_chep_loi
    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: ban_ghi_gia(2.0))
    try:
        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
        run = features.tao_run(db, owner_id="uA", source_key=khoa, settings={},
                               uoc_luong_credit=10)
        db.commit()

        for _ in range(12):
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

        s = features.giai_doan_theo_ten(db, run.id, "transcribe")
        assert s.status == "succeeded", f"transcribe: {s.status} {s.error}"

        # (a) la mot job con DOC LAP, thuoc lan GPU
        con = db.execute(select(Job).where(Job.plan_id == run.id,
                                           Job.step_id == "transcribe")).scalars().all()
        assert len(con) == 1
        assert con[0].app_slug == "asv_gpu", (
            "TRANSCRIBE phai chay o lan GPU, khong phai lan ffmpeg")

        # (b) ban ghi ben vung va kiem duoc
        khoa_ra = (s.outputs or {}).get("khoa_asset") or []
        assert len(khoa_ra) == 1
        a = assets.asset_cua(db, khoa_ra[0], "uA")
        assert assets.kiem_toan_ven(db, kho, a) == "ok"

        with kho.open(a.storage_key) as f:
            doc_lai = json.loads(f.read())
        ban_ghi.kiem(doc_lai)       # con dat hop dong sau khi doc lai tu kho
        assert [d["ma"] for d in doc_lai["doan"]] == ["seg_0001", "seg_0002"]

        # (c) tom tat co so lieu, khong co loi thoai
        assert (s.outputs or {}).get("so_doan") == 2
        assert "cau thu" not in repr(s.outputs)
    finally:
        db.close(); set_storage(None); dbmod.reset_engine()


def test_ban_ghi_dai_hon_ban_tieng_bi_TU_CHOI(tmp_path, monkeypatch):
    """Moc thoi gian troi phai bi bat o day, khong phai o TIMING.

    Neu lot, TIMING se dat tieng vao mot cho khong con hinh — va trieu chung se
    hien ra o cuoi day chuyen, xa cho gay ra no.
    """
    import platform_core.db as dbmod
    from platform_core import credit, jobs
    from platform_core.job_runner import JobContext
    from platform_core.storage import LocalStorage, set_storage
    from tests.conftest import bao_dam_user
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'p10b.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)

    from apps.auto_scan_video import features, giai_doan_chep_loi
    # Fixture dai 3 giay; ban ghi gia dai 30 giay -> phai bi tu choi.
    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: ban_ghi_gia(30.0))
    try:
        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
        run = features.tao_run(db, owner_id="uA", source_key=khoa, settings={},
                               uoc_luong_credit=10)
        db.commit()
        for _ in range(12):
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

        s = features.giai_doan_theo_ten(db, run.id, "transcribe")
        assert s.status != "succeeded", "ban ghi troi moc da duoc chap nhan"
        assert "trôi" in (s.error or ""), f"ly do khong ro: {s.error!r}"
    finally:
        db.close(); set_storage(None); dbmod.reset_engine()


# ══════════════════════════════════════════════════════════════════════════════
#  §5 Cho bang chung ngoai
# ══════════════════════════════════════════════════════════════════════════════

class TestChoBangChungNgoai:
    """Nhung thu may nay khong chung minh duoc, ghi ra thay vi lam ngo."""

    def test_whisperx_KHONG_duoc_cai_nen_luon_di_duong_du_phong(self):
        """Nen moc thoi gian TUNG TU den tu `word_timestamps` cua faster-whisper,
        **khong** tu phep canh chinh cuong buc cua whisperx.

        ⛔ Khac biet nay co that va anh huong toi pha 13: canh chinh cuong buc
           chinh xac hon dang ke o muc tu. Ban ghi tu khai `fallback_unaligned`
           nen ha nguon **doc duoc** dieu do — nhung dung sai so cua pha 13 phai
           duoc do lai neu whisperx duoc cai.
        """
        from apps.autosubvideo.transcription import whisperx_available

        assert not whisperx_available(), (
            "whisperx da duoc cai — hay DO LAI sai so canh chinh o pha 13 "
            "va cap nhat `MVP_CONTRACT.md` muc 7 T7, roi xoa phep kiem nay.")

    def test_chua_co_mau_TIENG_NOI_that_de_do_do_chinh_xac(self):
        """Fixture deu la am sin, nen khong phep kiem nao o day noi duoc gi ve
        chat luong nhan dang.

        Dieu do can mot mau tieng noi that co ban ghi tay di kem. Ghi ra day de
        pha 21 (nghiem thu E2E) khong tuong rang do chinh xac ASR da duoc kiem.
        """
        from tests.fixtures import asv_media

        assert not hasattr(asv_media, "mau_tieng_noi"), (
            "Da co mau tieng noi — hay them phep kiem do chinh xac ASV va xoa "
            "phep kiem nay.")
