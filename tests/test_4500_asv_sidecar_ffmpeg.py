"""Sidecar WhisperX duoi LocalSystem: moi truong con phai THAY duoc `ffmpeg`.

## Vi sao phep kiem nay ton tai

Tai hien 25/09 tren worker production (job `7c85a6c4`, run
`asvr_9fc9cc89bb104c06bb190fa3ac47bd3`, `2026-09-25T07:38:34Z`): duong san pham
WhisperX **chua bao gio chay**. Chuoi nguyen nhan, do duoc chu khong suy:

    MACHINE Path co thu muc chua ffmpeg.exe : False
    USER    Path co thu muc chua ffmpeg.exe : True   (WinGet cai THEO NGUOI DUNG)

`LTTStudioWorker` chay duoi LocalSystem ⇒ nhan MACHINE Path ⇒ khong bao gio
thay thu muc do. Loi goi ffmpeg **cua nen tang** mien nhiem vi `secrets\\app.env`
dat `LTT_FFMPEG` bang mot duong dan TUYET DOI (`platform_core.media._locate`).

⛔ Nhung sidecar la mot venv RIENG (`LTT_WHISPERX_PYTHON`), va goi `whisperx`
   trong do goi **`ffmpeg` tran** (`whisperx/audio.py::load_audio`, phan tu dau
   cua `cmd`). No **khong doc** `LTT_FFMPEG` ⇒ `FileNotFoundError: [WinError 2]`
   ⇒ `_transcribe_whisperx` nem `TranscriptionError` ⇒ `transcribe_file` lui ve
   faster-whisper, chi mot dong WARNING, va giai doan `asv_gpu.transcribe` van
   bao THANH CONG.

⭐ Nen bat bien duoc chot o day la thu **tien trinh con** thay: `PATH` cua no
   phai chua it nhat mot thu muc co `ffmpeg.exe`. ⛔ Khong chot "co bien
   LTT_FFMPEG" — bien do ton tai san trong ca huong hong, va mot phep kiem doc
   dung thu dai dien cho dieu minh muon biet thi khong phan biet duoc gi.

🔴 ⛔ Cach sua bi CAM o day: va `D:\\LTTWhisperX\\Lib\\site-packages\\whisperx`.
   Ta khong so huu goi do va mot lan `pip install --force-reinstall` xoa ban va,
   im lang, tra lai dung huong hong nay.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.autosubvideo import transcription           # noqa: E402


def _ffmpeg_gia(thu_muc: Path) -> Path:
    """Mot `ffmpeg.exe` GIA, du de `os.path.isfile` va `shutil.which` thay."""
    ten = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    binary = thu_muc / ten
    binary.write_bytes(b"MZ")                 # khong chay, chi can ton tai
    binary.chmod(0o755)
    return binary


def _moi_truong_localsystem(monkeypatch, tmp_path: Path) -> Path:
    """PATH khong co ffmpeg (nhu LocalSystem) + `LTT_FFMPEG` tuyet doi."""
    ff = _ffmpeg_gia(tmp_path / "ffbin")
    # PATH cua LocalSystem: mot thu muc trong, KHONG chua ffmpeg.
    trong = tmp_path / "machine_path"
    trong.mkdir()
    monkeypatch.setenv("PATH", str(trong))
    monkeypatch.setenv("LTT_FFMPEG", str(ff))
    monkeypatch.delenv("LTT_FFPROBE", raising=False)
    return ff


def _thu_muc_co_ffmpeg(path_str: str) -> list[str]:
    ten = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    return [d for d in (path_str or "").split(os.pathsep)
            if d and os.path.isfile(os.path.join(d, ten))]


@pytest.fixture(autouse=True)
def _thu_muc_ffbin(tmp_path: Path):
    (tmp_path / "ffbin").mkdir(parents=True, exist_ok=True)
    yield


def test_env_sidecar_co_thu_muc_chua_ffmpeg_khi_PATH_khong_co(monkeypatch, tmp_path):
    """🔴 DO truoc khi sua: `_env_ghim_gpu` tra `dict(os.environ)` nguyen xi."""
    ff = _moi_truong_localsystem(monkeypatch, tmp_path)

    env = transcription._env_ghim_gpu("")

    co = _thu_muc_co_ffmpeg(env.get("PATH", ""))
    assert co, (
        "PATH cua tien trinh con KHONG co thu muc nao chua ffmpeg.exe — "
        "`whisperx/audio.py` goi `ffmpeg` TRAN nen no se nem WinError 2. "
        f"PATH = {env.get('PATH', '')!r}, LTT_FFMPEG = {os.environ['LTT_FFMPEG']!r}")
    assert str(ff.parent) in co


def test_env_sidecar_giu_ghim_card_khi_da_them_ffmpeg(monkeypatch, tmp_path):
    """Them ffmpeg vao PATH ⛔ khong duoc lam mat `CUDA_VISIBLE_DEVICES`.

    Hai viec doc lap trong cung mot ham: mot ban va cho viec nay tung xoa viec
    kia thi job chay tren card cua LTT VOICE. Chot ca hai o mot cho.
    """
    _moi_truong_localsystem(monkeypatch, tmp_path)
    monkeypatch.setattr(transcription, "_chi_so_card", lambda _u: 0, raising=False)

    from platform_core import gpu as gpu_mod
    monkeypatch.setattr(gpu_mod, "visible_devices_value", lambda u: "GPU-abc")

    env = transcription._env_ghim_gpu("GPU-abc")

    assert env.get("CUDA_VISIBLE_DEVICES") == "GPU-abc"
    assert _thu_muc_co_ffmpeg(env.get("PATH", ""))


def test_env_sidecar_khong_no_PATH_khi_goi_nhieu_lan(monkeypatch, tmp_path):
    """Goi N lan ⛔ khong duoc chen N ban sao — PATH co tran do dai tren Windows."""
    ff = _moi_truong_localsystem(monkeypatch, tmp_path)

    p1 = transcription._env_ghim_gpu("").get("PATH", "")
    p2 = transcription._env_ghim_gpu("").get("PATH", "")

    assert p1 == p2
    assert p1.split(os.pathsep).count(str(ff.parent)) == 1


def test_env_sidecar_khong_no_khi_ffmpeg_khong_tim_duoc(monkeypatch, tmp_path):
    """Khong co ffmpeg o dau ca ⇒ tra ve moi truong nguyen, ⛔ khong nem.

    Sidecar hong se lui ve faster-whisper (cung can ffmpeg, cung se hong) —
    nhung cho hong phai la cho DOC TEP, khong phai cho dung moi truong.
    """
    monkeypatch.setenv("PATH", str(tmp_path / "machine_path_trong"))
    monkeypatch.delenv("LTT_FFMPEG", raising=False)
    monkeypatch.delenv("LTT_FFPROBE", raising=False)
    monkeypatch.setattr("platform_core.media._locate", lambda *a, **k: None)

    env = transcription._env_ghim_gpu("")

    assert isinstance(env, dict) and env.get("PATH") is not None


# ── B. Thong bao loi ⛔ khong duoc tu huy chan doan cua chinh no ──────────────

_TRACEBACK_THAT = '''Traceback (most recent call last):
  File "D:\\LTTWhisperX\\Lib\\site-packages\\whisperx\\audio.py", line 58, in load_audio
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\\Python312\\Lib\\subprocess.py", line 548, in run
    with Popen(*popenargs, **kwargs) as process:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\\Python312\\Lib\\subprocess.py", line 1026, in __init__
    self._execute_child(args, executable, preexec_fn, close_fds,
                        pass_fds, cwd, env,
                        startupinfo, creationflags, shell,
                        p2cread, p2cwrite,
                        c2pread, c2pwrite,
                        errread, errwrite,
                        restore_signals, gid, gids, uid, umask,
                        start_new_session, process_group)
  File "C:\\Python312\\Lib\\subprocess.py", line 1538, in _execute_child
    hp, ht, pid, tid = _winapi.CreateProcess(executable, args,
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [WinError 2] The system cannot find the file specified
'''


def test_thong_bao_loi_giu_DONG_CUOI_la_ngoai_le(tmp_path):
    """🔴 DO truoc khi sua: lat cat `[-1000:]` danh roi DUNG dong quan trong.

    Log production 25/09 chi con **dau mu** va **ten tham so POSIX**
    (`preexec_fn`, `close_fds`, `gid`, `gids`, `uid`, `umask`) — tuc lat cat roi
    vao GIUA mot frame `subprocess.py`. Dong `FileNotFoundError: [WinError 2]`,
    thu duy nhat noi ra nguyen nhan, nam NGOAI 1000 ky tu cuoi va bi cat.
    """
    log = tmp_path / "loi.log"
    log.write_text(_TRACEBACK_THAT, encoding="utf-8")

    tin = transcription._doc_loi_sidecar(str(log))

    assert "FileNotFoundError: [WinError 2]" in tin, (
        "dong ngoai le bi cat — day chinh la ca 25/09: thong bao loi tu xoa "
        f"thu no dung de do. Nhan duoc: {tin!r}")
    # Va van giu DAU traceback (dong goi ngoai cung noi loi xay ra o dau).
    assert "whisperx" in tin and "load_audio" in tin


def test_thong_bao_loi_khong_no_vo_han(tmp_path):
    """Giu ngan gon: log 1 MB ⛔ khong duoc di nguyen vao mot dong log."""
    log = tmp_path / "to.log"
    log.write_text("x" * 1_000_000 + "\nValueError: cuoi cung\n", encoding="utf-8")

    tin = transcription._doc_loi_sidecar(str(log))

    assert len(tin) <= 2_400
    assert "ValueError: cuoi cung" in tin


def test_thong_bao_loi_log_rong_khong_nem(tmp_path):
    log = tmp_path / "rong.log"
    log.write_text("", encoding="utf-8")
    assert transcription._doc_loi_sidecar(str(log)) == ""
    assert transcription._doc_loi_sidecar(str(tmp_path / "khong_ton_tai.log")) == ""


# ── C. Suy giam PHAI CO GHI SO, dung khuon da co cua kho ─────────────────────

def test_nhanh_lui_khai_tham_so_va_suy_giam_vao_BAN_GHI():
    """Nhanh `fallback_unaligned` phai mang `tham_so` nhu nhanh `aligned`.

    ⭐ Khuon da co trong kho (⛔ khong tao khuon thu hai): `whisperx_runner` ghi
       `tham_so` vao **chinh ban ghi** ("GHIM THAM SO — khong phai log, la mot
       phan cua BAN GHI"), va `auto_scan_video/ban_ghi.py` mang no len
       `tham_so_engine` canh `canh_chinh` + `ly_do_roi`. Nhanh lui truoc day
       khong ghi `tham_so` gi ca — tuc duong DUY NHAT tung chay tren worker that
       lai la duong khong khai gi.

    🔑 Va su that phai viet DUNG: faster-whisper **CO** moc tung tu
       (`word_timestamps=True`, `transcription.py` doc `word.start`/`word.end`),
       nhung khong qua buoc **can cuong buc** cua WhisperX ⇒ **kem chinh xac
       hon**. ⛔ Khong duoc viet "khong co moc tung tu" — noi qua thi nguoi sau
       khong tin phan con lai.
    """
    khai = transcription._khai_suy_giam_can_chinh()

    assert khai["moc_tung_tu"] is True
    assert khai["can_cuong_buc"] is False
    assert khai["suy_giam"] == transcription.SUY_GIAM_KHONG_CAN_CUONG_BUC
    assert khai["anh_huong"]


def test_suy_giam_khong_duoc_xep_thanh_loi():
    """⚠️ Luot chay VAN giao duoc hang ⇒ `muc` la suy giam, ⛔ khong phai `error`."""
    khai = transcription._khai_suy_giam_can_chinh()
    assert khai["muc"] == "suy_giam"
    assert khai["muc"] != "error"
