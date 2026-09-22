"""Giao thuc chay mot bo do trong `qc-venv` — MOT cho, moi bo do dung chung.

    chay(tep_script, dau_vao: dict, ...) -> dict

Tien trinh con doc `argv[1]` (JSON vao), ghi `argv[2]` (JSON ra), thoat 0.
Thoat khac 0 hoac khong co JSON ra ⇒ `DoLuongLoi` kem duoi log.

🔑 Card do NEN TANG cap (`JobContext.gpu_uuid`) va duoc ghim qua bien moi
   truong (`platform_core.gpu.env_for`) — bo do khong bao gio tu chon card.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

#: Python cua venv do luong. Ghi de bang `LTT_QC_PYTHON` (vd. may dev).
PYTHON_MAC_DINH = r"C:\LTTPlatform\qc-venv\Scripts\python.exe"
#: Thu muc model chuan cua nen tang (cung cho voi giong + VieNeu).
HF_HOME_MAC_DINH = r"C:\LTTPlatform\hf-cache"


class KhongKhaDung(RuntimeError):
    """Venv hoac model khong co. QC danh dau `khong_kha_dung`, khong lui."""


class DoLuongLoi(RuntimeError):
    """Bo do chay nhung hong. Thong diep mang duoi log cua tien trinh con."""


def python_qc() -> Path:
    return Path(os.environ.get("LTT_QC_PYTHON") or PYTHON_MAC_DINH)


def hf_home() -> str:
    return os.environ.get("LTT_QC_HF_HOME") or os.environ.get("HF_HOME") or HF_HOME_MAC_DINH


def san_sang() -> bool:
    return python_qc().is_file()


def _moi_truong(gpu_uuid: str) -> dict:
    env = dict(os.environ)
    if gpu_uuid:
        from platform_core.gpu import env_for
        env = env_for(gpu_uuid, env)
    env["HF_HOME"] = hf_home()
    # torch.hub (torchaudio pipelines) tai vao TORCH_HOME — de chung mot goc.
    env.setdefault("TORCH_HOME", str(Path(hf_home()) / "torch"))
    env["PYTHONIOENCODING"] = "utf-8"
    # ⛔ Khong tai model moi ngam: runner tu tai ban GHIM, co checksum.
    env.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    return env


def chay(tep_script: str | Path, dau_vao: dict, *, timeout_s: int = 1800,
         gpu_uuid: str = "", is_cancelled=None) -> dict:
    """Chay `tep_script` trong venv do luong. Tra ve JSON ra cua no."""
    py = python_qc()
    if not py.is_file():
        raise KhongKhaDung(f"chua co venv do luong: {py}")
    with tempfile.TemporaryDirectory(prefix="asv-do-") as tam:
        vao, ra, log = (Path(tam) / "vao.json", Path(tam) / "ra.json",
                        Path(tam) / "log.txt")
        vao.write_text(json.dumps(dau_vao, ensure_ascii=False), encoding="utf-8")
        with open(log, "wb") as lg:
            proc = subprocess.Popen(
                [str(py), str(tep_script), str(vao), str(ra)],
                stdout=lg, stderr=subprocess.STDOUT, env=_moi_truong(gpu_uuid),
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
            han = time.monotonic() + max(30, int(timeout_s))
            while proc.poll() is None:
                if is_cancelled is not None and is_cancelled():
                    proc.kill()
                    raise DoLuongLoi("da huy")
                if time.monotonic() > han:
                    proc.kill()
                    raise DoLuongLoi(f"qua {timeout_s}s")
                time.sleep(0.5)
        duoi = log.read_text(encoding="utf-8", errors="replace")[-2000:]
        if proc.returncode != 0 or not ra.is_file():
            if "KHONG_KHA_DUNG" in duoi:
                raise KhongKhaDung(duoi.strip().splitlines()[-1])
            raise DoLuongLoi(f"thoat {proc.returncode}: {duoi}")
        return json.loads(ra.read_text(encoding="utf-8"))


def la_tien_trinh_con() -> bool:
    """True khi dang chay BEN TRONG venv do luong (script runner goi)."""
    return Path(sys.executable).resolve() == python_qc().resolve()
