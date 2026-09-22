"""Runner bo do `chat_luong_tieng` (SQUIM_OBJECTIVE) — chay TRONG `qc-venv`.

    python squim_runner.py vao.json ra.json

Xem `squim.py` (license, weights ghim).
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from apps.asv_gpu.do_luong import _runner  # noqa: E402

SR = 16000


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def _weights(url: str, sha: str) -> Path:
    import torch
    dich = Path(torch.hub.get_dir()) / "torchaudio" / "models" / url.rsplit("/", 1)[-1]
    if not dich.is_file():
        dich.parent.mkdir(parents=True, exist_ok=True)
        tam = dich.with_suffix(".tai")
        try:
            torch.hub.download_url_to_file(url, str(tam), progress=False)
        except Exception as exc:                # noqa: BLE001
            _runner.khong_kha_dung(f"khong tai duoc weights SQUIM: {type(exc).__name__}")
        os.replace(tam, dich)
    that = _sha256(dich)
    if that != sha:
        _runner.khong_kha_dung(f"sha256 weights SQUIM lech: {that[:16]} != {sha[:16]}")
    return dich


def _doc(tep: str):
    import soundfile as sf
    import torch
    import torchaudio

    x, sr = sf.read(tep, dtype="float32", always_2d=True)
    w = torch.from_numpy(x.T.copy()).mean(0, keepdim=True)     # mono (1, T)
    if sr != SR:
        w = torchaudio.functional.resample(w, sr, SR)
    return w


def main() -> None:
    vao, ra = _runner.mo()
    dh = _runner.DongHo()
    try:
        import torch
        from torchaudio.models import squim_objective_base
    except ImportError as exc:
        _runner.khong_kha_dung(f"thieu thu vien trong qc-venv: {exc}")

    p = _weights(vao["url"], vao["sha256"])
    thiet_bi = "cuda" if torch.cuda.is_available() else "cpu"
    model = squim_objective_base()
    model.load_state_dict(torch.load(p, weights_only=True))
    model.eval().to(thiet_bi)
    dh.danh_dau("nap_model")

    cs = int(float(vao.get("cua_so_s") or 2.0) * SR)
    buoc = int(float(vao.get("buoc_s") or 1.0) * SR)
    ket: dict = {}
    with torch.inference_mode():
        for d in vao["doan"]:
            w = _doc(d["tep"]).to(thiet_bi)
            if w.shape[-1] < SR // 4:
                ket[d["ma"]] = {"bo_qua": "doan ngan hon 0,25 s"}
                continue
            stoi, pesq, sdr = (float(t[0]) for t in model(w))
            r = {"stoi": round(stoi, 4), "pesq": round(pesq, 3),
                 "si_sdr": round(sdr, 2), "giay": round(w.shape[-1] / SR, 3)}
            if w.shape[-1] > cs + buoc:
                khung = w.unfold(-1, cs, buoc)[0]                  # (n, cs)
                s2, p2, d2 = model(khung)
                r.update({"stoi_min_cua_so": round(float(s2.min()), 4),
                          "pesq_min_cua_so": round(float(p2.min()), 3),
                          "si_sdr_min_cua_so": round(float(d2.min()), 2),
                          "so_cua_so": int(khung.shape[0])})
            ket[d["ma"]] = r
    dh.danh_dau("cham")
    del model
    _runner.ghi(ra, {"ket_qua": ket,
                     "tai_nguyen": dh.ket(thiet_bi=thiet_bi, so_doan=len(ket))})


if __name__ == "__main__":
    main()
