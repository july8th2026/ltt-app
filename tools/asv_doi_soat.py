r"""asv_doi_soat.py — Sau phep DEM tren mot luot chay ASV — ⛔ khong can ban
tham chieu, ⛔ khong can ai cham.

    python tools\asv_doi_soat.py <run_id>

🔑 **Vi sao dem chu khong cham.** `B2_DO_DICH_THAM_CHIEU.md` tu khai bo do dich
   dang bi khoa boi mot vong tron: chan ly nen la hai nguoi soi ma **ca hai deu
   la LLM**, kappa 0,714 voi KTC95 `[0,00 ; 1,00]`. Sau phep duoi day ⛔ khong
   hoi *"ban dich co hay khong"* — chung hoi *"luot chay nay co TU MAU THUAN
   khong"*, va mau thuan thi dem duoc. Mot bo cham sai gu van dem mau thuan
   dung.

⛔ `None` nghia la **chua do duoc**; `0` nghia la **do duoc va bang khong**. Gop
   hai thu do vao mot gia tri la mat dung kha nang phan biet ma bang nay ton
   tai de giu.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _phan_vi(cac: list[float], p: float) -> float | None:
    if not cac:
        return None
    xs = sorted(cac)
    if len(xs) == 1:
        return xs[0]
    vt = p * (len(xs) - 1)
    lo = int(vt)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (vt - lo)


def doi_soat(dong: dict) -> dict:
    """`dong` = `quan_sat.dong_thoi_gian(...)`. Tra ve tam con so (hoac `None`)."""
    gd = next((m for m in (dong.get("giai_doan") or [])
               if m.get("giai_doan") == "voice_synthesis"), None)
    tt = (gd or {}).get("tom_tat") or {}
    luot = list(tt.get("luot_doc") or [])

    sai_so: list[float] = []
    ngan = 0
    for e in luot:
        that = float(e.get("giay") or 0.0)
        doan = float(e.get("giay_doan") or 0.0)
        if that <= 0 or doan <= 0:
            continue
        sai_so.append(abs(that - doan) / that)
        if doan < that:
            ngan += 1

    he_so = [float(x) for x in (tt.get("he_so_toc_da_ap") or [])]
    return {
        "sai_so_p50": _phan_vi(sai_so, 0.50),
        "sai_so_p90": _phan_vi(sai_so, 0.90),
        "sai_so_max": max(sai_so) if sai_so else None,
        "ti_le_doan_ngan": (ngan / len(sai_so)) if sai_so else None,
        "pause_kha_dung_s": tt.get("pause_kha_dung_s"),
        "so_doan_nan_oan": tt.get("so_doan_nan_oan"),
        "he_so_toc_p90": _phan_vi(he_so, 0.90),
        "so_doan_lech_cuoi": tt.get("so_doan_lech_cuoi"),
    }


def main(argv: list[str]) -> int:
    # ⭐ Boc lai stdout CHI o day (khi chay nhu CLI that), khong o muc module:
    #    boc o muc module lam pytest hong capture luc import ("I/O operation
    #    on closed file") vi TextIOWrapper giu mot tham chieu rieng toi buffer.
    if hasattr(sys.stdout, "buffer"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)

    if len(argv) != 2:
        print(__doc__)
        return 2
    run_id = argv[1]

    from tools.asv_chay_worker_that import nap_env
    nap_env()

    from platform_core.db import get_session
    from apps.auto_scan_video import quan_sat
    from apps.auto_scan_video.tables import AsvRun

    gen = get_session()
    db = next(gen)
    try:
        run = db.get(AsvRun, run_id)
        if run is None:
            print(f"KHONG THAY run {run_id!r} trong CSDL nay.")
            return 1

        dong = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
        ra = doi_soat(dong)
        for khoa, gt in ra.items():
            print(f"{khoa}={gt}")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
