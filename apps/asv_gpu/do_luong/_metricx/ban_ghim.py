"""Ban ghim + checksum cua MetricX-24 QE — dung chung cho `tai.py` va `chay.py`.

Chay BEN TRONG qc-venv (can `huggingface_hub`). Khong import tu worker.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

GOC = Path(__file__).resolve().parent
PHIEN_BAN = json.loads((GOC / "phien_ban.json").read_text(encoding="utf-8"))


class KhongKhaDung(RuntimeError):
    pass


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 22), b""):
            h.update(khoi)
    return h.hexdigest()


def _dau_kiem(p: Path) -> Path:
    # Dau "da kiem" (bam lai khi kich thuoc/mtime doi). Tep trong HF_HOME: dau o
    # HF_HOME/ltt-kiem/ — khong rai tep la vao blobs/ cua cache HF.
    hf = os.environ.get("HF_HOME")
    if hf:
        goc = Path(hf).resolve()
        if goc in p.parents:
            ten = hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:32]
            return goc / "ltt-kiem" / f"{ten}.txt"
    return Path(str(p) + ".ltt-sha256")


def kiem(p: Path, mong_doi: str | None) -> str:
    if not mong_doi:
        raise KhongKhaDung(f"KHONG_KHA_DUNG: phien_ban.json chua ghim sha256 cho {p.name}")
    st = p.stat()
    dau = _dau_kiem(p.resolve())
    the = f"{st.st_size}:{st.st_mtime_ns}:{mong_doi}"
    try:
        if dau.read_text(encoding="ascii") == the:
            return mong_doi
    except OSError:
        pass
    thuc = sha256(p)
    if thuc != mong_doi:
        raise KhongKhaDung(f"KHONG_KHA_DUNG: sha256 {p.name} = {thuc}, mong doi {mong_doi}")
    try:
        dau.parent.mkdir(parents=True, exist_ok=True)
        dau.write_text(the, encoding="ascii")
    except OSError:
        pass
    return thuc


def tep_cuc_bo(muc: str, *, tai_ve: bool = False) -> dict[str, Path]:
    """{ten_tep: duong_dan} cua `muc` ('mo_hinh' | 'tokenizer') — chi tu HF_HOME.

    `tai_ve=False` (runner): thieu tep => KhongKhaDung, khong tai ngam.
    """
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import LocalEntryNotFoundError

    cfg = PHIEN_BAN[muc]
    ra: dict[str, Path] = {}
    for ten in cfg["tep"]:
        try:
            p = hf_hub_download(cfg["repo_id"], ten, revision=cfg["revision"],
                                local_files_only=not tai_ve)
        except LocalEntryNotFoundError as e:
            raise KhongKhaDung(
                f"KHONG_KHA_DUNG: thieu {cfg['repo_id']}@{cfg['revision'][:8]}/{ten} "
                f"trong HF_HOME={os.environ.get('HF_HOME')} — chay _metricx/tai.py") from e
        ra[ten] = Path(p)
    return ra


def kiem_muc(muc: str, *, tai_ve: bool = False) -> dict[str, Path]:
    tep = tep_cuc_bo(muc, tai_ve=tai_ve)
    for ten, p in tep.items():
        kiem(p, PHIEN_BAN[muc]["tep"][ten])
    return tep
