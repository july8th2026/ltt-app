"""Ban GHIM cua bo phan loai gioi + tai/kiem weights. Viet boi LTT Studios.

Cung khuon voi `_metricx/ban_ghim.py`: mot cho duy nhat biet repo, revision,
ten tep va sha256; runner goi `tai_va_kiem()` roi nap.

⛔ `snapshot_download` KHONG kiem gi khi tep da co trong cache. Tep nay kiem
   sha256 SAU khi tai, moi lan, truoc khi nap - cung ly do `squim_runner.py`
   kiem lai weights cua SQUIM.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

#: Repo HF + revision GHIM. License weights: MIT (model card YAML).
REPO = "JaesungHuh/voice-gender-classifier"
REVISION = "db1222153bd60337e900be22add7af180452adc0"
TEP_WEIGHTS = "model.safetensors"
SHA256 = "2d8e0be1fdf159d60d5087416e6f6277c5e30ce9e33a61c767a9a409e6c503c5"
SO_BYTE = 61_907_512

#: `C` cua ECAPA - doc tu `config.json` cua chinh repo (`{"C": 1024}`).
C = 1024

PHIEN_BAN = f"ecapa_gioi/{REVISION[:12]}/{SHA256[:12]}"


def tai_va_kiem() -> Path:
    """Tai ban ghim vao HF_HOME, kiem sha256, tra duong dan tep weights."""
    from huggingface_hub import hf_hub_download

    p = Path(hf_hub_download(REPO, TEP_WEIGHTS, revision=REVISION))
    so = p.stat().st_size
    if so != SO_BYTE:
        raise RuntimeError(f"{TEP_WEIGHTS}: {so} byte, cho {SO_BYTE}")
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != SHA256:
        raise RuntimeError(f"{TEP_WEIGHTS}: sha256 {h}, cho {SHA256}")
    return p


def nap(device: str = "cpu"):
    """Tra `ECAPA_gender` da nap weights, `.eval()`, tren `device`."""
    import torch
    from safetensors.torch import load_file

    from .ecapa_gioi import ECAPA_gender

    m = ECAPA_gender(C=C)
    thieu, thua = m.load_state_dict(load_file(str(tai_va_kiem())), strict=False)
    # ⛔ Bo loc mel dung mot lan la cua TA (xem NOTICE), no khong co trong
    #    checkpoint - nen no la khoa THIEU duy nhat duoc phep.
    thieu = [k for k in thieu if not k.startswith("_mel.")]
    if thieu or thua:
        raise RuntimeError(f"checkpoint lech: thieu={thieu[:5]} thua={thua[:5]}")
    m.eval()
    return m.to(torch.device(device))
