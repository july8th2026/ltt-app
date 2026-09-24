"""Runner MOS cho `do_gioi_giong.py cham-en` — chay TRONG `qc-venv`.

    python do_gioi_giong_mos.py vao.json ra.json

Hai bo cham, ca hai da XAC MINH giay phep tu nguon goc ngay 23/09/2026:

  · **Distill-MOS** `microsoft/Distill-MOS` 0.9.1 — MOS 1-5, khong can tham
    chieu. Ma **MIT** (`LICENSE` cua repo, "Copyright (c) Microsoft
    Corporation"), weights **MIT**: tep `distillmos/weights/distill_mos_v7.pt`
    nam NGAY TRONG cay MIT ay, va model card ghi `| License | MIT |` kem cau
    *"Nothing contained in this Model Card should be interpreted as or deemed a
    restriction or modification to the license the model is released under."*
    Phu thuoc `xls-r-sqa` 0.1.0 cung **MIT** (lcn-kul/xls-r-analysis-sqa).
    ⚠️ Model card khai ro: huan luyen cho tieng ANH, cho canh **tang cuong /
       suy hao tin hieu**. Dung no de xep hang giong doc la mot PHEP XAP XI;
       bao cao phai noi ra, va phai doi chieu voi cac cot khac.

  · **DNSMOS P.835** — SIG/BAK/OVRL. Dung lai `voice_sidecar/dnsmos.py` (da co
    trong kho, da ghim commit + sha256), KHONG viet lai.
    🔴 `THIRD_PARTY_METRICS.md` §2 ghi DNSMOS la DO-NOT-SHIP vi *"khong co
       tuyen bo giay phep cho tep .onnx"*. Cau do SAI, va chinh kho nay da co
       cau tra loi tu 31/08: `microsoft/DNS-Challenge` tach doi giay phep —
       `LICENSE-CODE` (MIT) cho **ma**, `LICENSE` goc (**CC BY 4.0**) cho
       *"the Microsoft documentation and other content in this repository"*,
       va tep `.onnx` la "other content". Doc thang tu README muc "Legal
       Notices" + tep `LICENSE` (dong dau: "Attribution 4.0 International").

⛔ Khong resample bang scipy: `dnsmos._ve_16k` goi `scipy.signal` (khong co
   trong qc-venv). Ta dua vao no mang DA 16 kHz nen nhanh do khong chay.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.asv_gpu.do_luong import _runner  # noqa: E402

SR = 16000
PHIEN_BAN = "distillmos-0.9.1/v7 + dnsmos-sig_bak_ovr"


def _doc(tep: str):
    import soundfile as sf
    import torch
    import torchaudio

    x, sr = sf.read(tep, dtype="float32", always_2d=True)
    w = torch.from_numpy(x.T.copy()).mean(0, keepdim=True)
    if sr != SR:
        w = torchaudio.functional.resample(w, sr, SR)
    return w


def main() -> None:
    vao, ra = _runner.mo()
    dh = _runner.DongHo()
    try:
        import torch
        from distillmos import ConvTransformerSQAModel

        from voice_sidecar import dnsmos
    except ImportError as exc:
        _runner.khong_kha_dung(f"thieu thu vien trong qc-venv: {exc}")

    thiet_bi = "cuda" if torch.cuda.is_available() else "cpu"
    model = ConvTransformerSQAModel()
    model.eval().to(thiet_bi)
    co_dnsmos = dnsmos.co_san()
    dh.danh_dau("nap_model")

    ket: dict = {}
    with torch.inference_mode():
        for d in vao["doan"]:
            w = _doc(d["tep"])
            r: dict = {"giay": round(w.shape[-1] / SR, 3)}
            try:
                r["distill_mos"] = round(float(model(w.to(thiet_bi))[0]), 3)
            except Exception as exc:            # noqa: BLE001
                r["distill_mos_loi"] = f"{type(exc).__name__}: {exc}"
            if co_dnsmos:
                k = dnsmos.cham(w[0].numpy(), SR)
                if k:
                    r.update({"dnsmos_sig": round(k["sig"], 3),
                              "dnsmos_bak": round(k["bak"], 3),
                              "dnsmos_ovrl": round(k["ovrl"], 3),
                              "dnsmos_so_cua_so": k.get("so_cua_so")})
            else:
                r["dnsmos"] = "khong_kha_dung"
            ket[d["ma"]] = r
            del w
            if thiet_bi == "cuda":
                torch.cuda.empty_cache()
    dh.danh_dau("cham")
    del model
    _runner.ghi(ra, {"ket_qua": ket, "phien_ban": PHIEN_BAN,
                     "tai_nguyen": dh.ket(thiet_bi=thiet_bi, so_doan=len(ket))})


if __name__ == "__main__":
    main()
