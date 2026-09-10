"""Auto Scan Video — MEDIA_PREPARE: soi, chinh sach dau vao, chuan hoa tieng.

Engine THAT dau tien. Moi phep kiem o day chay ffmpeg/ffprobe that tren tep that
sinh tu `lavfi` — khong tep nao co ban quyen, khong tep nao co du lieu ca nhan,
va ca ba lan sinh cho ra byte giong het nhau (do o pha 01).

## Doi chieu (parity) voi helper di san — Prompt 08 muc 2

Kho di san khong co bo test nao (GAP-00-C), nen "doi chieu" o day khong the la
"chay lai bo test cu". No la thu manh hon mot chut va trung thuc hon nhieu:
**chot HINH DANG LENH** ma ban di san dung, roi chot **tinh chat do duoc** cua
ket qua. Xem `TestDoiChieuDiSan`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.fixtures.asv_media import require_ffmpeg, tiny_mp4, tiny_mp4_silent


# ══════════════════════════════════════════════════════════════════════════════
#  Soi
# ══════════════════════════════════════════════════════════════════════════════

def test_soi_doc_du_thu_chinh_sach_can(tmp_path):
    """`platform_core.media.probe` khong tra ve nhung truong nay, va do la ly do
    co mot ham soi rieng."""
    from apps.auto_scan_video import nhap_media

    tt = nhap_media.soi(str(tiny_mp4(tmp_path / "a.mp4")))

    assert tt["co_video"] and tt["co_tieng"]
    assert tt["codec_video"] == "h264"
    assert tt["thoi_luong"] == pytest.approx(3.0, abs=0.2)
    assert tt["rong"] == 320 and tt["cao"] == 240
    assert tt["so_kenh"] >= 1 and tt["tan_so"] > 0
    assert tt["doc"] is False, "320x240 la khung NGANG"


def test_soi_nhan_ra_video_KHONG_co_tieng(tmp_path):
    from apps.auto_scan_video import nhap_media

    tt = nhap_media.soi(str(tiny_mp4_silent(tmp_path / "cam.mp4")))
    assert tt["co_video"] is True
    assert tt["co_tieng"] is False
    assert tt["so_kenh"] == 0


def test_soi_nhan_ra_khung_DOC(tmp_path):
    """Muc 7 — doc/ngang. 240x320 phai duoc nhan la khung doc."""
    from apps.auto_scan_video import nhap_media

    tt = nhap_media.soi(str(tiny_mp4(tmp_path / "doc.mp4", size="240x320")))
    assert tt["doc"] is True


def test_soi_tep_HONG_nem_loi_ro_rang(tmp_path):
    """Muc 7 — dau vao hong. Phai nem `MediaError`, khong duoc tra ve mot tu dien
    rong ma tang tren se hieu nham la "video 0 giay"."""
    from apps.auto_scan_video import nhap_media

    require_ffmpeg()
    hong = tmp_path / "hong.mp4"
    hong.write_bytes(b"day khong phai mot tep mp4" * 50)
    with pytest.raises(nhap_media.MediaError):
        nhap_media.soi(str(hong))


def test_soi_duong_dan_UNICODE(tmp_path):
    """Muc 7 — ten tep Unicode. Khach Viet Nam dat ten tep bang tieng Viet, va
    tren Windows day la cho de vo nhat."""
    from apps.auto_scan_video import nhap_media

    thu_muc = tmp_path / "Thư mục Tiếng Việt"
    thu_muc.mkdir()
    duong = tiny_mp4(thu_muc / "video của tôi — bản 1.mp4")
    tt = nhap_media.soi(str(duong))
    assert tt["co_video"] and tt["thoi_luong"] > 0


# ══════════════════════════════════════════════════════════════════════════════
#  Chinh sach dau vao (MVP_CONTRACT.md muc 2)
# ══════════════════════════════════════════════════════════════════════════════

def test_video_KHONG_co_tieng_bi_tu_choi(tmp_path):
    """D-ASV-08 — tu choi NGAY LUC NOP, khong phai o giai doan chep loi.

    Mot video cam khong co gi de long tieng. Phat hien dieu do sau ba giai doan
    co tinh tien la mot lan hoan tien, va hoan tien la cach dat de noi "khong".
    """
    from apps.auto_scan_video import nhap_media

    tt = nhap_media.soi(str(tiny_mp4_silent(tmp_path / "cam.mp4")))
    with pytest.raises(nhap_media.MediaError) as loi:
        nhap_media.kiem_chinh_sach(tt)
    assert "tiếng" in str(loi.value), "thong bao phai noi ro thieu cai gi"


def test_video_qua_dai_bi_tu_choi_kem_CON_SO(tmp_path):
    """Thong bao phai noi ca do dai that lan gioi han.

    Mot loi "định dạng không hợp lệ" bat khach doan, va ho se doan sai roi thu
    lai — moi lan thu lai la mot lan tra tien cho mot cau tra loi ta da biet.
    """
    from apps.auto_scan_video import nhap_media

    tt = nhap_media.soi(str(tiny_mp4(tmp_path / "a.mp4")))
    tt["thoi_luong"] = nhap_media.THOI_LUONG_TOI_DA_S + 1
    with pytest.raises(nhap_media.MediaError) as loi:
        nhap_media.kiem_chinh_sach(tt)
    assert "120" in str(loi.value), "phai noi gioi han la bao nhieu phut"


def test_codec_KHONG_copy_duoc_bi_tu_choi(tmp_path):
    """🔑 D-ASV-03 — MVP sao chep luong video.

    Mot codec khong copy duoc vao MP4 se buoc phai ma hoa lai: tieu GPU cua
    khach va lam mat chat luong cho mot viec ho khong yeu cau. Tu choi to ro hon
    la lam lang.
    """
    from apps.auto_scan_video import nhap_media

    tt = nhap_media.soi(str(tiny_mp4(tmp_path / "a.mp4")))
    tt["codec_video"] = "vp9"           # webm — bi loai co y
    with pytest.raises(nhap_media.MediaError) as loi:
        nhap_media.kiem_chinh_sach(tt)
    assert "H.264" in str(loi.value)


def test_video_hop_le_di_qua_chinh_sach(tmp_path):
    from apps.auto_scan_video import nhap_media

    nhap_media.kiem_chinh_sach(nhap_media.soi(str(tiny_mp4(tmp_path / "a.mp4"))))


# ══════════════════════════════════════════════════════════════════════════════
#  Chuan hoa tieng
# ══════════════════════════════════════════════════════════════════════════════

def test_tach_tieng_ra_dung_16k_mot_kenh(tmp_path):
    """Dang vao chuan cua Whisper. Chuyen mot lan o day thay vi de tang chep loi
    tu lam — no lam moi lan chay lai deu ton lai cong giai ma."""
    from apps.auto_scan_video import nhap_media

    nguon = tiny_mp4(tmp_path / "a.mp4")
    wav = nhap_media.tach_tieng_cho_asr(str(nguon), str(tmp_path / "ra.wav"))

    tt = nhap_media.soi(wav)
    assert tt["co_tieng"] and not tt["co_video"]
    assert tt["tan_so"] == nhap_media.TAN_SO_ASR
    assert tt["so_kenh"] == nhap_media.SO_KENH_ASR
    assert tt["thoi_luong"] == pytest.approx(3.0, abs=0.2)


def test_tach_tieng_tu_nguon_STEREO_ra_MONO(tmp_path):
    """Muc 7 — mono/stereo. Nguon hai kenh phai duoc tron ve mot."""
    from apps.auto_scan_video import nhap_media

    require_ffmpeg()
    from platform_core import media
    nguon = tmp_path / "stereo.mp4"
    subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=12:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-ac", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-shortest", str(nguon)], check=True, capture_output=True)
    assert nhap_media.soi(str(nguon))["so_kenh"] == 2

    wav = nhap_media.tach_tieng_cho_asr(str(nguon), str(tmp_path / "ra.wav"))
    assert nhap_media.soi(wav)["so_kenh"] == 1


def test_ban_GOC_khong_bi_cham(tmp_path):
    """Muc 4 — artifact chuan hoa la mot dong lineage MOI, khong phai ban thay the.

    Mat ban goc la mat kha nang tinh lai moi thu ha nguon.
    """
    from apps.auto_scan_video import assets, nhap_media

    nguon = tiny_mp4(tmp_path / "a.mp4")
    truoc = assets.bam(nguon.read_bytes())
    nhap_media.tach_tieng_cho_asr(str(nguon), str(tmp_path / "ra.wav"))
    assert assets.bam(nguon.read_bytes()) == truoc, "ban goc da bi sua"


def test_tach_tieng_that_bai_thi_NEM_chu_khong_de_lai_tep_cut(tmp_path):
    from apps.auto_scan_video import nhap_media

    require_ffmpeg()
    hong = tmp_path / "hong.mp4"
    hong.write_bytes(b"khong phai mp4" * 50)
    with pytest.raises(nhap_media.MediaError):
        nhap_media.tach_tieng_cho_asr(str(hong), str(tmp_path / "ra.wav"))


# ══════════════════════════════════════════════════════════════════════════════
#  Van tay (muc 8)
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_doi_khi_NOI_DUNG_NGUON_doi():
    """Dua tren CHECKSUM tep nguon, khong phai ten hay khoa cua no.

    Hai tep cung ten khac noi dung phai ra hai van tay; mot ten tep khong noi
    len dieu gi ve noi dung.
    """
    from apps.auto_scan_video import nhap_media

    a = nhap_media.van_tay_chuan_hoa(checksum_nguon="aaa", phien_ban_cong_cu="8.0")
    b = nhap_media.van_tay_chuan_hoa(checksum_nguon="bbb", phien_ban_cong_cu="8.0")
    assert a != b


def test_van_tay_doi_khi_PHIEN_BAN_FFMPEG_doi():
    """🔑 O13. Thieu thanh phan nay thi sau khi nang ffmpeg, moi lan chay lai se
    dung lai ket qua cu — im lang."""
    from apps.auto_scan_video import nhap_media

    a = nhap_media.van_tay_chuan_hoa(checksum_nguon="aaa", phien_ban_cong_cu="7.1")
    b = nhap_media.van_tay_chuan_hoa(checksum_nguon="aaa", phien_ban_cong_cu="8.0.1")
    assert a != b


def test_van_tay_doi_khi_CAU_HINH_CHUAN_HOA_doi(monkeypatch):
    from apps.auto_scan_video import nhap_media

    truoc = nhap_media.van_tay_chuan_hoa(checksum_nguon="aaa",
                                         phien_ban_cong_cu="8.0")
    monkeypatch.setattr(nhap_media, "TAN_SO_ASR", 22050)
    sau = nhap_media.van_tay_chuan_hoa(checksum_nguon="aaa",
                                       phien_ban_cong_cu="8.0")
    assert truoc != sau


def test_phien_ban_ffmpeg_doc_duoc_va_khong_bao_gio_nem():
    """Van tay khong duoc phep vo vi mot lenh phu that bai."""
    from apps.auto_scan_video import nhap_media

    v = nhap_media.phien_ban_ffmpeg()
    assert isinstance(v, str) and v


# ══════════════════════════════════════════════════════════════════════════════
#  Doi chieu voi helper di san (muc 2)
# ══════════════════════════════════════════════════════════════════════════════

class TestDoiChieuDiSan:
    """Doi chieu voi `Cut_only ver2/nerf_engine/stages/audio.py:48 extract_audio`.

    ⚠️ NOI CHO DUNG: kho di san **khong co bo test nao** (GAP-00-C), nen day
       khong phai "chay lai bo kiem cu". Ban di san la:

           ffmpeg -y -hide_banner -loglevel error -i <vao> -vn -ac 2 -ar 48000 <ra>

       Ta co y KHAC no o hai cho, va ca hai deu co ly do:

         `-ac 1`     : ASR khong dung kenh thu hai, va tron ve mono giam mot nua
                       du lieu phai chuyen qua GPU.
         `-ar 16000` : Whisper lay mau lai ve 16 kHz o ben trong. Dua 48 kHz vao
                       la lam dung cong viec do hai lan.

    ⭐ Nen "doi chieu" o day la: **cung mot bo khung lenh**, va **cung tinh chat
       do duoc** (thoi luong giu nguyen, tieng khong im). Do la thu bao ve duoc
       khi khong co bo kiem nao de ke thua.
    """

    def test_giu_dung_bo_khung_lenh_cua_ban_di_san(self):
        """Ta van dung `-vn`, `-ac`, `-ar` va khong bao gio `shell=True`."""
        import inspect

        from apps.auto_scan_video import nhap_media

        ma = inspect.getsource(nhap_media.tach_tieng_cho_asr)
        for co in ('"-vn"', '"-ac"', '"-ar"'):
            assert co in ma, f"mat co {co} cua ban di san"
        assert "shell=True" not in ma

    def test_thoi_luong_giu_nguyen_qua_phep_tach(self, tmp_path):
        """Tinh chat quan trong nhat: moc thoi gian cua transcript se doi chieu
        nguoc ve video, nen mot lech thoi luong o day se lam lech ca ban long
        tieng."""
        from apps.auto_scan_video import nhap_media

        nguon = tiny_mp4(tmp_path / "a.mp4", duration_s=5.0)
        goc = nhap_media.soi(str(nguon))["thoi_luong"]
        wav = nhap_media.tach_tieng_cho_asr(str(nguon), str(tmp_path / "ra.wav"))
        assert nhap_media.soi(wav)["thoi_luong"] == pytest.approx(goc, abs=0.1)

    def test_ban_tach_ra_KHONG_im_lang(self, tmp_path):
        """Mot ban 16 kHz mono dung kich thuoc nhung toan so 0 se qua moi phep
        kiem ve dinh dang — va lam tang chep loi tra ve mot ban ghi rong."""
        import struct
        import wave

        from apps.auto_scan_video import nhap_media

        nguon = tiny_mp4(tmp_path / "a.mp4")
        wav = nhap_media.tach_tieng_cho_asr(str(nguon), str(tmp_path / "ra.wav"))
        with wave.open(wav, "rb") as f:
            khung = f.readframes(min(f.getnframes(), 16000))
        mau = struct.unpack(f"<{len(khung) // 2}h", khung[:len(khung) // 2 * 2])
        assert max(abs(m) for m in mau) > 100, "ban tach ra im lang"


# ══════════════════════════════════════════════════════════════════════════════
#  Huy giua chung (yeu cau kiem chung cua pha)
# ══════════════════════════════════════════════════════════════════════════════

def test_huy_giua_chung_GIET_tien_trinh_con(tmp_path):
    """Huy la hop tac: giet tien trinh con roi nem, thay vi de mot lan chay dai
    tiep tuc sau khi khach da bam huy va da duoc hoan tien."""
    from apps.auto_scan_video import nhap_media

    require_ffmpeg()
    nguon = tiny_mp4(tmp_path / "a.mp4")
    with pytest.raises(nhap_media.DaHuy):
        nhap_media.tach_tieng_cho_asr(str(nguon), str(tmp_path / "ra.wav"),
                                      hoi_huy=lambda: True)


def test_KHONG_BAO_GIO_dung_shell_khi_chay_ffmpeg():
    """Ten tep den tu `filename` cua ve tai len. `shell=True` voi mot chuoi do
    khach dat ten la mot duong tiem lenh.

    ⚠️ Do bang AST chu khong bang tim chuoi con — va day la lan THU HAI cai bay
       do bat duoc trong du an nay. Ban dau phep kiem nay `assert "shell=True"
       not in ma`, va no do vi `nhap_media.py` co mot doan van **cam** dung
       `shell=True`. Mot hang rao lam do vi chinh loi canh bao cua no day nguoi
       sau xoa loi canh bao di cho xanh.

       Lan dau la o pha 05 voi `gpu_arbiter`; `tests/test_401...::_vi_pham` da
       duoc viet lai bang AST vi ly do do. Dung lai no thay vi lap lai loi cu.
    """
    import inspect

    from apps.auto_scan_video import nhap_media
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    ma = inspect.getsource(nhap_media)
    assert _vi_pham(ma, ("shell",)) == [], "co dung shell khi chay tien trinh con"


# ══════════════════════════════════════════════════════════════════════════════
#  Cong thoat: mot dau vao co chu -> mot artifact chinh tac da kiem
# ══════════════════════════════════════════════════════════════════════════════

def test_cong_thoat_mot_dau_vao_thanh_artifact_chinh_tac(tmp_path, monkeypatch):
    """Cong thoat cua pha 08, chay qua hang doi that.

    Sau `media_prepare`: hai artifact ben vung (ho so soi + ban tieng), ca hai
    kiem duoc bang checksum, va ban tieng la mot tep WAV THAT doc duoc bang
    ffprobe — khong phai mot chuoi JSON gia.
    """
    from platform_core import credit, jobs
    from platform_core.job_runner import JobContext
    from platform_core.storage import LocalStorage, set_storage
    import platform_core.db as dbmod
    from tests.conftest import bao_dam_user
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'p8.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)
    try:
        from apps.auto_scan_video import assets, features

        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
        run = features.tao_run(db, owner_id="uA", source_key=khoa, settings={},
                               uoc_luong_credit=10)
        db.commit()

        for _ in range(6):      # dieu phoi + media_prepare
            job = jobs.claim(db, worker_id="w", capabilities={"api", "ffmpeg"})
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

        s = features.giai_doan_theo_ten(db, run.id, "media_prepare")
        assert s.status == "succeeded", f"media_prepare: {s.status} {s.error}"

        khoa_ra = (s.outputs or {}).get("khoa_asset") or []
        assert len(khoa_ra) == 2, "phai ra HO SO SOI va BAN TIENG"

        loai = set()
        for k in khoa_ra:
            a = assets.asset_cua(db, k, "uA")
            assert assets.kiem_toan_ven(db, kho, a) == "ok"
            loai.add(a.kind)
        assert loai == {"json", "audio"}

        wav = next(k for k in khoa_ra if k.endswith(".wav"))
        from apps.auto_scan_video import nhap_media
        tt = nhap_media.soi(kho.local_path(wav))
        assert tt["tan_so"] == nhap_media.TAN_SO_ASR and tt["so_kenh"] == 1

        # Ban goc VAN CON — no la nguon de tinh lai moi thu ha nguon.
        assert kho.exists(khoa)
    finally:
        db.close(); set_storage(None); dbmod.reset_engine()


def test_video_KHONG_tieng_lam_giai_doan_HONG_HAN_khong_thu_lai(tmp_path, monkeypatch):
    """Chinh sach dau vao la mot that bai CUOI CUNG.

    Mot tep khong co luong tieng se khong tu moc them mot luong tieng o lan thu
    hai; thu lai chi ton them thoi gian worker de nhan cung mot cau tra loi.
    """
    from platform_core import credit, jobs
    from platform_core.job_runner import JobContext
    from platform_core.storage import LocalStorage, set_storage
    import platform_core.db as dbmod
    from tests.conftest import bao_dam_user
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'p8b.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)
    try:
        from apps.auto_scan_video import features
        from apps.auto_scan_video.tables import RUN_ERROR

        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA", im_lang=True)
        run = features.tao_run(db, owner_id="uA", source_key=khoa, settings={},
                               uoc_luong_credit=10)
        db.commit()

        for _ in range(10):
            job = jobs.claim(db, worker_id="w", capabilities={"api", "ffmpeg"})
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

        run = features.lay_run(db, run.id, "uA")
        assert run.status == RUN_ERROR
        assert "tiếng" in (run.error or ""), (
            f"ly do hong phai noi ro thieu tieng, nhan duoc: {run.error!r}")
        # Va tien phai duoc tra lai het: khong giai doan nao lam duoc gi.
        assert run.credit_actual == 0
    finally:
        db.close(); set_storage(None); dbmod.reset_engine()
