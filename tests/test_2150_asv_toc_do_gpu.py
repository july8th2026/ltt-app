"""Lan `toc-do-gpu` (asv-final): ASR khong duoc tu chon card, va khong duoc lui
ve CPU mot cach IM LANG.

Bang do that: `docs/auto_scan_video_final/L_TOC_DO_GPU.md`.

⛔ Khong phep kiem nao o day nap model that. Cho nguy hiem duy nhat
   (`WhisperModel(...)`) duoc thay bang mot lop gia.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from apps.autosubvideo import transcription as tr


# ══════════════════════════════════════════════════════════════════════════════
#  1. Khong co lease -> khong duoc cham card
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_co_lease_thi_ASR_chay_CPU(monkeypatch):
    """🔴 Ban truoc mac dinh `device="cuda"` BAT KE co lease hay khong.

    Card nay dung chung voi LTT VOICE (khach tra tien). Mot duong chay lay card
    ma nen tang khong biet la dung thu `platform_core.gpu_lease` sinh ra de chan.
    """
    monkeypatch.delenv("LTT_AUTOSUB_WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("LTT_AUTOSUB_WHISPER_COMPUTE", raising=False)

    thiet_bi, kieu, chi_so, ly_do = tr._thiet_bi_asr("")

    assert thiet_bi == "cpu" and kieu == "int8" and chi_so == 0
    assert "lease" in ly_do, "phai NOI RA vi sao chay CPU"


def test_co_lease_nhung_torch_khong_thay_card_thi_noi_ra(monkeypatch):
    """Nen tang cap card ma torch khong thay = viec cap card hong.

    ⛔ Van chay CPU (khong lam chet job cua khach), nhung KHONG duoc im lang.
    """
    monkeypatch.delenv("LTT_AUTOSUB_WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("LTT_AUTOSUB_WHISPER_COMPUTE", raising=False)
    monkeypatch.setattr(tr, "_chi_so_card", lambda _u: -1)

    thiet_bi, _kieu, _i, ly_do = tr._thiet_bi_asr("GPU-deadbeef")

    assert thiet_bi == "cpu"
    assert "khong thay" in ly_do


def test_co_lease_va_ghim_duoc_thi_dung_dung_chi_so_do(monkeypatch):
    """`device_index` — cach ghim DUY NHAT con lai o mot duong chay trong tien
    trinh worker (`CUDA_VISIBLE_DEVICES` chi ghim duoc tien trinh CON)."""
    monkeypatch.delenv("LTT_AUTOSUB_WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("LTT_AUTOSUB_WHISPER_COMPUTE", raising=False)
    monkeypatch.setattr(tr, "_chi_so_card", lambda _u: 1)

    assert tr._thiet_bi_asr("GPU-abc") == ("cuda", "float16", 1, "")


def test_nguoi_van_hanh_van_ep_duoc_bang_bien_moi_truong(monkeypatch):
    """Mot quyet dinh NOI RA thi duoc; mot mac dinh lang le thi khong."""
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_COMPUTE", "int8")
    assert tr._thiet_bi_asr("GPU-abc") == ("cpu", "int8", 0, "")


# ══════════════════════════════════════════════════════════════════════════════
#  2. `_chi_so_card` hoi TORCH, khong hoi `nvidia-smi`
# ══════════════════════════════════════════════════════════════════════════════

def test_chi_so_card_hoi_torch_chu_khong_hoi_nvidia_smi():
    """🔑 `nvidia-smi --query-gpu=index` la so thu tu TOAN MAY; `device_index`
    cua CTranslate2 la so thu tu trong tap card CUDA NHIN THAY DUOC. Lay nham
    mot cai la day job sang card khac — im lang.
    """
    ma = Path(tr.__file__).read_text(encoding="utf-8")
    cay = ast.parse(ma)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "_chi_so_card")
    ten = {getattr(n.func, "attr", "") or getattr(n.func, "id", "")
           for n in ast.walk(ham) if isinstance(n, ast.Call)}
    assert "get_device_properties" in ten
    assert "by_uuid" not in ten and "list_gpus" not in ten


def test_chi_so_card_khop_theo_uuid(monkeypatch):
    class _Tp:
        def __init__(self, u): self.uuid = u

    class _Cuda:
        @staticmethod
        def device_count(): return 2

        @staticmethod
        def get_device_properties(i):
            return _Tp(["GPU-1111", "GPU-2222"][i])

    import sys
    import types
    gia = types.SimpleNamespace(cuda=_Cuda)
    monkeypatch.setitem(sys.modules, "torch", gia)

    assert tr._chi_so_card("GPU-2222") == 1
    assert tr._chi_so_card("gpu-1111") == 0     # khong phan biet hoa/thuong
    assert tr._chi_so_card("2222") == 1         # tien to `GPU-` la tuy chon
    assert tr._chi_so_card("GPU-9999") == -1


# ══════════════════════════════════════════════════════════════════════════════
#  3. `torch` phai duoc import TRUOC `faster_whisper`
# ══════════════════════════════════════════════════════════════════════════════

def test_torch_import_TRUOC_faster_whisper():
    """⚠️ Ban `torch …+cu128` dang ky `torch/lib` (noi co `cublas64_12.dll`,
    `cudnn*64_9.dll`) qua `os.add_dll_directory`; tren Windows CTranslate2 tim
    cuBLAS/cuDNN o do. Dao thu tu thi `WhisperModel(device="cuda")` nem
    `Could not load library cublas64_12.dll`.

    `apps/asv_gpu/do_luong/giong_runner.py` da gap va ghi lai dung bay nay —
    chot bang AST de mot lan don import sau khong pha no ma khong ai thay.
    """
    cay = ast.parse(Path(tr.__file__).read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "_get_faster_model")
    dong = {}
    for n in ast.walk(ham):
        if isinstance(n, ast.Import):
            for a in n.names:
                dong.setdefault(a.name, n.lineno)
        elif isinstance(n, ast.ImportFrom):
            dong.setdefault(n.module or "", n.lineno)

    assert "torch" in dong, "`_get_faster_model` khong import torch"
    assert "faster_whisper" in dong
    assert dong["torch"] < dong["faster_whisper"], (
        "torch phai import TRUOC faster_whisper - xem docstring")


# ══════════════════════════════════════════════════════════════════════════════
#  4. Ket qua phai KHAI no chay o dau
# ══════════════════════════════════════════════════════════════════════════════

class _DoanGia:
    def __init__(self, s, e, t):
        self.start, self.end, self.text, self.words = s, e, t, []


class _ModelGia:
    def transcribe(self, *_a, **_k):
        import types
        return ([_DoanGia(0.0, 1.0, "xin chao")],
                types.SimpleNamespace(language="vi", duration=1.0))


def test_ban_ghi_tra_ve_KHAI_thiet_bi_da_chay(monkeypatch):
    """🔴 Bao cao nghiem thu `NEN_V3` (23/09) ghi "Whisper chay CPU/int8" tu mot
    bien moi truong ma no TU dat, khong tu ban ghi. Duong chay phai tu khai."""
    monkeypatch.setattr(tr, "_get_faster_model",
                        lambda _m, gpu_uuid="": (_ModelGia(), {
                            "asr_device": "cpu", "asr_compute": "int8",
                            "asr_device_index": 0,
                            "asr_cpu_reason": "nen tang khong cap card"}))
    # ⭐ `_transcribe_faster` nay tu giai ma truoc khi goi `model.transcribe`
    #    (fix dau cau tieng Han, `apps/autosubvideo/transcription.py:253`) — gia
    #    lap buoc do de test khong doi mot tep .wav that.
    monkeypatch.setattr("faster_whisper.audio.decode_audio",
                        lambda *_a, **_k: [0.0])

    ra = tr._transcribe_faster("khong-doc-tep.wav", language="vi",
                               model_name="tiny")

    assert ra["engine"] == "faster-whisper"
    assert ra["asr_device"] == "cpu" and ra["asr_compute"] == "int8"
    assert ra["asr_cpu_reason"], "lui ve CPU ma khong noi ly do = lui IM LANG"


def test_gpu_uuid_duoc_chuyen_xuong_duong_faster_whisper(monkeypatch):
    """⛔ Bản trước `_transcribe_faster` không nhận `gpu_uuid` — tức đường lùi
    không bao giờ biết nền tảng đã cấp card nào."""
    thay = {}

    def _gia(model_name, *, gpu_uuid=""):
        thay["uuid"] = gpu_uuid
        return _ModelGia(), {"asr_device": "cpu", "asr_compute": "int8",
                             "asr_device_index": 0, "asr_cpu_reason": ""}

    monkeypatch.setattr(tr, "_get_faster_model", _gia)
    monkeypatch.setattr(tr, "whisperx_available", lambda: False)
    monkeypatch.setattr("faster_whisper.audio.decode_audio",
                        lambda *_a, **_k: [0.0])

    tr.transcribe_file("khong-doc-tep.wav", language="vi", model_name="tiny",
                       gpu_uuid="GPU-cafe")

    assert thay["uuid"] == "GPU-cafe"


# ══════════════════════════════════════════════════════════════════════════════
#  5. Ban khai tai nguyen cua `asv_gpu` phai khop bang do that
# ══════════════════════════════════════════════════════════════════════════════

def test_manifest_asv_gpu_khong_con_khai_torch_la_ban_CPU():
    """🔴 Ghi chu cu o `apps/asv_gpu/manifest.py` khai "torch tren may nay la
    ban CPU-only (2.11.0+cpu, cuda False)" va lay do de khong do VRAM demucs.

    Cau do dung cho **trinh thong dich chay test**
    (`…\\Programs\\Python\\Python313`, torch 2.11.0+cpu) va SAI cho **venv cua
    worker** (`C:\\LTTPlatform\\venv`, torch 2.11.0+cu128, `cuda True`) — noi
    demucs that su chay. Mot ghi chu dung o nham venv da giu phep do treo 20 ngay.
    """
    ma = Path(__file__).resolve().parents[1] / "apps" / "asv_gpu" / "manifest.py"
    van = ma.read_text(encoding="utf-8")

    # ⛔ Khong chot bang "vang mat chuoi `CPU-only`": ban sua TRICH lai cau sai
    #    de nguoi doc sau hieu vi sao, nen chuoi do con nguyen. Chot bang thu
    #    PHAI CO MAT: ban khai phai chi dung venv nao va ban torch nao.
    for can in ("LTTPlatform", "cu128"):
        assert can in van, (
            f"ban khai VRAM phai noi ro moi truong da do ({can}) - "
            "xem docs/auto_scan_video_final/L_TOC_DO_GPU.md")


@pytest.mark.parametrize("job", ["asv_gpu.audio_prepare", "asv_gpu.transcribe",
                                 "asv_gpu.qc_do_luong"])
def test_moi_job_gpu_deu_khai_vram(job):
    from apps.asv_gpu.manifest import MANIFEST

    assert MANIFEST.gpu_vram_mb.get(job), f"{job} chua khai gpu_vram_mb"
