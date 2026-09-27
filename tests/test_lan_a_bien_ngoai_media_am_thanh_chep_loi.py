"""Lan A — hai CHO NOI RA NGOAI cua `audio_prepare`/`transcribe` do sai kenh.

Ca hai bug duoi day cung mot khuon voi `_doan_con_dung` (26/09): **kenh CUC BO
co thu kenh THAT khong co**, hoac **phep do nham vao mot dai luong khac**.

  §1 `transcribe` nap CA ban tieng vao RAM khi kho khong co dia (R2).
     `LocalStorage.local_path` tra duong that ⇒ nhanh nay KHONG BAO GIO chay
     trong test; R2 tra `None` (`platform_core/storage.py:116`, R2Storage khong
     ghi de) ⇒ **100 %** luot production di qua no.

  §2 `audio_prepare` so thoi luong ban nen voi thoi luong **CONTAINER** cua ban
     goc, trong khi ban nen duoc rut tu **LUONG TIENG**. Fixture tu sinh co
     tieng = hinh = container nen sai so bang 0; phim that thi khong.
"""
from __future__ import annotations

import io
import subprocess
import types
from pathlib import Path

import pytest

from apps.auto_scan_video import assets

# Mieng nang duy nhat: model demucs. ffmpeg/ffprobe, kho, van tay deu THAT.
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401


# ══════════════════════════════════════════════════════════════════════════════
#  §1 `transcribe` phai doc ban tieng THEO DONG CHAY
# ══════════════════════════════════════════════════════════════════════════════

class _KhoR2Gia:
    """Kho hinh dang R2: ⛔ KHONG co dia, va ghi lai moi `read(n)`."""

    def __init__(self, noi_dung: dict[str, bytes]):
        self._nd = dict(noi_dung)
        self.lan_doc: list[int] = []
        self.da_put: dict[str, bytes] = {}

    def local_path(self, khoa: str):
        return None                      # <- dung nhu R2Storage

    def open(self, khoa: str):
        kho = self
        goc = io.BytesIO(self._nd[khoa])

        class F:
            def read(self, n=-1):
                khoi = goc.read(n) if (n is not None and n >= 0) else goc.read()
                kho.lan_doc.append(len(khoi))
                return khoi

            def close(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return F()

    def put(self, khoa: str, f, content_type: str = ""):
        self.da_put[khoa] = f.read()


def _run_gia():
    # `nguon_loi="asr"` de co lap DUNG mot cho noi: doc ban tieng tu kho.
    # (Che do mac dinh cua ho so cu la `auto`, va no keo them ca mot luot tai
    #  ban goc ve — mot cho noi khac, do rieng.)
    return types.SimpleNamespace(
        id="r1", owner_id="uA", source_key="asv/uA/nguon/x.mp4",
        settings={"nguon_loi": "asr"}, contract_version="v1")


def test_transcribe_KHONG_nap_ca_ban_tieng_vao_RAM(monkeypatch):
    """🔴 `giai_doan_chep_loi.chay` lam dung dieu `_duong_doc_duoc` ton tai de
    khong lam: `Path(duong).write_bytes(f.read())`.

    ⭐ `audio_full.wav` la PCM 16 kHz mono = 32 kB/s ⇒ mot phim 2 gio (tran
       `THOI_LUONG_TOI_DA_S`) la **230 MB** nam tron trong RAM worker, nhan doi
       luc ghi. Khong loi nao no ra — chi la may bat dau swap khi hai lan chay
       trung nhau, dung kieu hong ma `test_429` da chan cho `media_prepare`.
    """
    from apps.auto_scan_video import giai_doan_chep_loi as gd

    khoa_tieng = "asv-staging/uA/r0/media_prepare/vt.wav"
    du_lieu = b"RIFF" + b"w" * (assets.KHOI_DOC * 3 + 17)
    kho = _KhoR2Gia({khoa_tieng: du_lieu})

    monkeypatch.setattr(gd, "_khoa_tieng_asr", lambda db, run: khoa_tieng)
    monkeypatch.setattr(gd.nhap_media, "soi",
                        lambda duong, **kw: {"thoi_luong": 100.0})
    monkeypatch.setattr(gd, "chep_loi", lambda duong_tieng, **kw: {
        "segments": [{"start": 0.0, "end": 1.5, "text": "ni hao", "words": []}],
        "language": "zh", "engine": "gia"})

    ra = gd.chay(None, kho, run=_run_gia(), ctx=None)

    assert ra["phan"], "khong promote gi ca — phep kiem khong do duoc gi"
    assert kho.lan_doc, "chua doc ban tieng — phep kiem khong do duoc gi"
    assert max(kho.lan_doc) <= assets.KHOI_DOC, (
        f"co mot lan doc {max(kho.lan_doc)} byte tren {len(du_lieu)} — "
        f"`transcribe` dang nap ca ban tieng vao RAM (kho R2 khong co dia)")


# ══════════════════════════════════════════════════════════════════════════════
#  §2 `audio_prepare` phai so voi LUONG TIENG, khong voi CONTAINER
# ══════════════════════════════════════════════════════════════════════════════

class _KhoDiaGia:
    """Kho co dia (khong phai cho §2 do): tra duong that, ghi vao bo nho."""

    def __init__(self, ban_do: dict[str, str]):
        self._ban_do = dict(ban_do)
        self.da_put: dict[str, bytes] = {}

    def local_path(self, khoa: str):
        return self._ban_do.get(khoa)

    def open(self, khoa: str):
        return open(self._ban_do[khoa], "rb")

    def put(self, khoa: str, f, content_type: str = ""):
        self.da_put[khoa] = f.read()


def _video_tieng_ngan_hon_hinh(dich: Path, *, hinh_s: float = 5.0,
                               tieng_s: float = 3.5) -> Path:
    """Phim co hinh dai hon tieng — hinh dang RAT thuong cua phim that.

    ⛔ Fixture chuan cua kho (`asv_media`) sinh hinh va tieng **cung do dai**,
       nen sai so cua phep so o `audio_prepare` bang 0 va khong ai thay.
    """
    from platform_core import media

    dich.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i",
         f"testsrc=size=320x240:rate=25:duration={hinh_s}",
         "-f", "lavfi", "-i", f"sine=frequency=300:duration={tieng_s}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-t", str(hinh_s), str(dich)],
        capture_output=True)
    if r.returncode != 0:
        pytest.skip("khong co ffmpeg/libx264 de dung fixture")
    return dich


def test_soi_PHAN_BIET_container_voi_luong_tieng(tmp_path):
    """Doi chung: ffprobe THAT noi ro hai con so nay khac nhau 1,5 giay."""
    from apps.auto_scan_video import nhap_media

    vid = _video_tieng_ngan_hon_hinh(tmp_path / "lech.mp4")
    tt = nhap_media.soi(str(vid))

    assert tt["thoi_luong"] == pytest.approx(5.0, abs=0.2)
    assert tt["thoi_luong_tieng"] is not None
    assert tt["thoi_luong_tieng"] == pytest.approx(3.5, abs=0.2)


def test_audio_prepare_KHONG_tu_choi_phim_co_tieng_ngan_hon_hinh(tmp_path):
    """🔴 Ban nen duoc rut tu LUONG TIENG (`-vn`) nen no dai bang luong tieng.

    So no voi thoi luong CONTAINER (= max(hinh, tieng)) la so hai dai luong
    khac nhau: do duoc 3,506 s so voi 5,0 s ⇒ lech 1,49 s ⇒ nem *"Nhac nen lech
    thoi luong so voi ban goc"* — mot thong bao chi tay vao BAN NEN trong khi
    loi nam o PHEP SO. Moi phim co hinh dai hon tieng > 0,5 s deu chet o day.
    """
    from apps.auto_scan_video import giai_doan_am_thanh

    vid = _video_tieng_ngan_hon_hinh(tmp_path / "lech.mp4")
    khoa = "asv/uA/nguon/lech.mp4"
    kho = _KhoDiaGia({khoa: str(vid)})
    run = types.SimpleNamespace(id="r2", owner_id="uA", source_key=khoa,
                                settings={}, contract_version="v1")

    ra = giai_doan_am_thanh.chay(None, kho, run=run, ctx=None)

    assert ra["phan"], "khong promote ban nen nao"
    # Ban nen dai bang LUONG TIENG, khong bang container — va do la DUNG.
    assert ra["tom_tat"]["thoi_luong"] == pytest.approx(3.5, abs=0.2)


# ══════════════════════════════════════════════════════════════════════════════
#  §3 `f0_ly_do`: KHOA VANG khac KHOA RONG
# ══════════════════════════════════════════════════════════════════════════════

def test_f0_ly_do_RONG_chi_duoc_nghia_la_DA_DO(tmp_path):
    """🔴 `cao_do` tra `(0.0, "")` cho mot video **im lang that** — mot trang
    thai co nghia. Nen `ket_qua.get("f0_ly_do") or ""` gop *"tien trinh tach
    khong khai truong nay"* vao dung o do, va hai thu thanh mot.

    ⭐ Ban gia lap demucs cua kho (`rao_chan_nang.gia_lap_demucs`) **khong** khai
       `f0_ly_do` ⇒ moi bang chung nghiem thu sinh o kenh cuc bo doc ra
       *"da do: khong co giong"*, trong khi khong ai do gi. Va gate
       `pipeline.py:203` (`f0_trung_vi_khac_0_tren_phim_co_tieng`) doc dung
       hai chu so ay.
    """
    from apps.auto_scan_video import giai_doan_am_thanh
    from tests import rao_chan_nang

    if rao_chan_nang.bat():
        pytest.skip("LTT_TEST_NANG=1: demucs THAT luon khai f0_ly_do")

    vid = _video_tieng_ngan_hon_hinh(tmp_path / "im.mp4")
    khoa = "asv/uA/nguon/im.mp4"
    kho = _KhoDiaGia({khoa: str(vid)})
    run = types.SimpleNamespace(id="r3", owner_id="uA", source_key=khoa,
                                settings={}, contract_version="v1")

    tom = giai_doan_am_thanh.chay(None, kho, run=run, ctx=None)["tom_tat"]

    assert tom["f0_trung_vi"] == 0.0, "ban gia lap khong con tra f0 = 0"
    assert tom["f0_ly_do"], (
        "`f0_trung_vi = 0.0` voi `f0_ly_do` RONG => bao cao noi 'da do: khong "
        "co giong', trong khi tien trinh tach khong khai gi ca")
