"""Runner bo do `gioi` (ECAPA gender, MIT) — chay TRONG `qc-venv`.

    python gioi_runner.py vao.json ra.json

Xem `gioi.py` (cau hoi, license, vi sao cua so truot) va `_ecapa_gioi/NOTICE`.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Goc kho neo bang TEN thu muc `apps/` — ⛔ khong dem cap. Lap lai o day (chu
# khong goi `_runner._goc_kho`) vi chinh dong nay moi lam `_runner` nhap duoc.
for _cha in Path(__file__).resolve().parents:
    if _cha.name == "apps":
        sys.path.insert(0, str(_cha.parent))
        break
else:  # pragma: no cover - chi xay ra khi tep bi chep ra ngoai `apps/`
    raise RuntimeError(f"khong thay `apps/` tren duong di cua {__file__}")

from apps.asv_gpu.do_luong import _runner  # noqa: E402

SR = 16000
#: Dai F0 quet. Cung dai voi `tools/do_bai_dai.py` de hai bang so sanh duoc.
F0_MIN, F0_MAX = 70.0, 400.0
#: Cua so ngan hon ngan nay thi khong cham (ECAPA can it nhat ~1 s de on dinh).
TOI_THIEU_S = 1.0
#: So cua so cham MOT luot. Cung ly do voi `squim_runner.LO_CUA_SO`: card la
#: card DUNG CHUNG voi Voice/VLM, dinh bo nho phai la dinh cua MOT lo.
LO = 8


def _doc(tep: str):
    import soundfile as sf
    import torch
    import torchaudio

    x, sr = sf.read(tep, dtype="float32", always_2d=True)
    w = torch.from_numpy(x.T.copy()).mean(0, keepdim=True)          # (1, T) mono
    if sr != SR:
        w = torchaudio.functional.resample(w, sr, SR)
    return w


def _f0_trung_vi(w) -> float | None:
    """F0 trung vi tren cac khung CO TIENG. `None` khi khong do duoc.

    ⚠️ `detect_pitch_frequency` (torchaudio, BSD-2) tra MOT gia tri cho MOI
       khung, ke ca khung im lang — no khong co khai niem "co tieng". Nen loc
       bang nang luong truoc, neu khong trung vi se bi keo ve nhieu nen.
    """
    import torch
    import torchaudio

    try:
        f0 = torchaudio.functional.detect_pitch_frequency(
            w, SR, frame_time=0.02, freq_low=int(F0_MIN), freq_high=int(F0_MAX))[0]
    except Exception as exc:                   # noqa: BLE001 - doan qua ngan
        # ⛔ KHONG nuot lang le: F0 la cot doi chieu, va mot cot doi chieu im
        #    lang trong bao cao trong y het mot cot doi chieu dong y.
        print(f"F0 khong do duoc: {type(exc).__name__}: {exc}", flush=True)
        return None
    n = f0.shape[-1]
    if n < 5:
        return None
    khung = w[0, :n * int(0.02 * SR)].reshape(-1, int(0.02 * SR))[:n]
    nang = khung.pow(2).mean(dim=1).sqrt()
    co_tieng = nang > 0.2 * float(nang.max())
    v = f0[co_tieng]
    if v.numel() < 5:
        return None
    return round(float(torch.median(v)), 1)


def main() -> None:
    vao, ra = _runner.mo()
    dh = _runner.DongHo()
    try:
        import torch
        from apps.asv_gpu.do_luong._ecapa_gioi import ban_ghim
    except ImportError as exc:
        _runner.khong_kha_dung(f"thieu thu vien trong qc-venv: {exc}")

    # 🔑 Thiet bi theo **lease**, khong theo `is_available()`. Xem
    #    `_runner.chon_thiet_bi`.
    thiet_bi, ly_do_thiet_bi = _runner.chon_thiet_bi(vao)
    try:
        model = ban_ghim.nap(thiet_bi)
    except Exception as exc:                   # noqa: BLE001
        _runner.khong_kha_dung(f"khong nap duoc weights gioi: {type(exc).__name__}: {exc}")
    dh.danh_dau("nap_model")

    cs = int(float(vao.get("cua_so_s") or 3.0) * SR)
    buoc = int(float(vao.get("buoc_s") or 1.5) * SR)
    nguong_rms = float(vao.get("nguong_rms") or 0.1)
    ket: dict = {}
    with torch.inference_mode():
        for d in vao["clip"]:
            w = _doc(d["tep"])
            giay = w.shape[-1] / SR
            if giay < TOI_THIEU_S:
                ket[d["ma"]] = {"bo_qua": f"clip {giay:.2f} s, ngan hon {TOI_THIEU_S} s"}
                continue
            f0 = _f0_trung_vi(w)
            wg = w.to(thiet_bi)

            # Ca clip.
            p_ca = model.xac_suat(wg)[0]

            # Cua so truot. Clip ngan hon mot cua so ⇒ chi co mot "cua so" = ca clip.
            if w.shape[-1] > cs + buoc:
                khung = wg.unfold(-1, cs, buoc)[0]
                rms = khung.pow(2).mean(dim=1).sqrt()
                giu = rms > nguong_rms * float(rms.max())
                khung = khung[giu]
                ps = []
                for i in range(0, khung.shape[0], LO):
                    ps.extend(model.xac_suat(khung[i:i + LO]))
                del khung
            else:
                ps = [p_ca]
            if not ps:
                ps = [p_ca]
            n = len(ps)
            tb_nam = sum(p[0] for p in ps) / n
            ti_le_nam = sum(1 for p in ps if p[0] >= 0.5) / n
            nhan = "nam" if tb_nam >= 0.5 else "nu"
            # ⭐ `do_tin` = MIN(chac chan trung binh, ti le cua so dong y).
            #    Mot giong doi dai co the co trung binh cao ma ti le thap; lay
            #    min la cach duy nhat de con so ay KHONG giau chuyen do.
            tb = tb_nam if nhan == "nam" else 1.0 - tb_nam
            tl = ti_le_nam if nhan == "nam" else 1.0 - ti_le_nam
            ket[d["ma"]] = {
                "nhan": nhan,
                "p_nam": round(float(p_ca[0]), 4),
                "p_nu": round(float(p_ca[1]), 4),
                "tb_p_nam_cua_so": round(tb_nam, 4),
                "ti_le_cua_so_nam": round(ti_le_nam, 4),
                "do_tin": round(min(tb, tl), 4),
                "so_cua_so": n,
                "f0_trung_vi": f0,
                "giay": round(giay, 2),
            }
            del w, wg
            if thiet_bi == "cuda":
                torch.cuda.empty_cache()
    dh.danh_dau("cham")
    del model
    _runner.ghi(ra, {"ket_qua": ket,
                     "tai_nguyen": dh.ket(thiet_bi=thiet_bi,
                                          ly_do_thiet_bi=ly_do_thiet_bi,
                                          so_clip=len(ket))})


if __name__ == "__main__":
    main()
