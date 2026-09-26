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

═══════════════════════════════════════════════════════════════════════════════
🔴 **DINH CHINH 26/09 (Task 5b) — ban truoc cua tep nay ⛔ KHONG DO GI.**

   Ban truoc doc `gd["tom_tat"]` cua mot muc trong `quan_sat.dong_thoi_gian`.
   ⛔ Muc `giai_doan` cua dong thoi gian **khong he co khoa `tom_tat`** (no co
   `bat_dau · giai_doan · giai_doan_hong · giay · ket_thuc · loi_co_ma ·
   so_ket_qua · trang_thai`). `thi_hanh.py:589` do `tom_tat` cua giai doan
   **PHANG** vao `asv_stage.outputs`:

       ket_qua = {"stage": ten, "khoa_asset": khoa_ra, **(ra.get("tom_tat") or {})}

   ⇒ moi phep do tra `None`, tuc *"chua do duoc"*, **mai mai** — mot dung cu do
   im lang khong do gi ma van xanh.

   ⭐ Va vi sao bo test cu XANH: fixture BIA ra mot `dong` co dung khoa ma ma
   nguon **muon nhan**. Chinh kho nay da ghi cai bay do o
   `giai_doan_noi_dung.py` (tim `cua_ai_gia`): *"Mot ban gia tra ve dung thu ma
   ma nguon muon nhan, thay vi thu cua that tra ve, se lam ca bo test xanh
   quanh mot loi khong the khong xay ra."*

   ⇒ Tu ban nay: lop TINH nhan `{ten_giai_doan: outputs}` (thuan, kiem duoc,
   ⛔ khong can CSDL), lop `main` dung map do TU CSDL.

🔴 **HAI khoa dac ta cu doi ma ⛔ KHONG MOT AI GHI RA** — da bo khoi bang:

   - `so_doan_nan_oan`: `giai_doan_giong.py:188` co dem no trong `dong_ho` va
     `:438` co tang no, nhung `tom_tat` o `:539-540` **chi** lay `giay_tts` va
     `giay_llm_nan` tu `dong_ho`. Bo dem ay ⛔ khong bao gio roi khoi ham.
     (`test_2018` chot no bang `'"so_doan_nan_oan"' in ma` — mot phep do CACH
     GO, no xanh nho dong `:188`.) ⇒ Đ4 hien **chua do duoc**, va chua the do
     duoc tu `outputs`.
   - `pause_kha_dung_s`: ⛔ khong ton tai o bat ky dau trong `apps/`. Khai niem
     that la `thoi_gian.ngan_sach_nan_s(khe_s, ngan_sach_s) - khe_s`, va no
     ⛔ khong duoc ghi vao `outputs` cua giai doan nao.

⚠️ **Mau so.** `sai_so_*` doc thang `lech` cua chinh ban ghi luot doc, tuc
   `(giay - khe) / khe` (`nan_cho_vua.lech`) — **cung mau so** ma `can_nan` /
   `dung_sai_giay` dung de phan quyet. Ban truoc chia cho `giay` (so THAT), tuc
   mot mau so khac, nen con so cua no ⛔ khong so sanh duoc voi nguong nao ca.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Khoa `outputs` ma cong cu nay doc, theo TEN GIAI DOAN.
#:
#: ⭐ Khai ra thanh DU LIEU chu khong an trong than ham, de mot phep kiem CO HOC
#:    doi chieu duoc tung khoa voi cho THAT SU ghi no (`test_408`). Mot loi dan
#:    do ⛔ khong chan duoc lan sau; mot phep do thi co.
KHOA_CAN: dict[str, tuple[str, ...]] = {
    # `giai_doan_giong.chay` -> `tom_tat` (phang vao outputs boi `thi_hanh`)
    "voice_synthesis": ("tung_luot_doc", "giay_tts", "giay_llm_nan"),
    # `giai_doan_thoi_gian.chay` -> `tom_tat["master"] = do_duoc`
    "timing_align": ("master",),
}

#: Khoa nam TRONG `outputs["master"]` cua `timing_align` — mot cau truc LONG,
#: ⛔ khong phang: `giai_doan_thoi_gian.py:159` dat ca `do_duoc` duoi mot khoa.
KHOA_TRONG_MASTER: tuple[str, ...] = (
    "he_so_toc_da_ap", "so_doan_lech_cuoi", "giay_lech_cuoi")

#: Khoa cua MOT ban ghi trong `tung_luot_doc` (`nan_cho_vua.ban_ghi_luot_doc`).
KHOA_TRONG_LUOT_DOC: tuple[str, ...] = ("giay", "khe", "lech")


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


def doi_soat(outputs_theo_giai_doan: dict[str, dict]) -> dict:
    """Sau con so tu `outputs` cua CAC GIAI DOAN — ⛔ khong can CSDL.

    `outputs_theo_giai_doan` = `{ten_giai_doan: dict(asv_stage.outputs)}`. Giai
    doan chua chay thi vang mat (hoac map toi `{}`), va moi phep do cua no tra
    `None` = *"chua do duoc"*.
    """
    giong = dict(outputs_theo_giai_doan.get("voice_synthesis") or {})
    thoi = dict(outputs_theo_giai_doan.get("timing_align") or {})
    master = dict(thoi.get("master") or {})

    # ── Đ1/Đ2: sai so thoi luong doc, tren TUNG LUOT DOC ────────────────────
    #
    # ⚠️ `tung_luot_doc` (mot dong moi LUOT) chu ⛔ khong `tung_doan` (mot dong
    #    moi DOAN, giay CUOI CUNG sau nan): luot doc DAU la thu tra loi *"bo uoc
    #    luong co dung khong"*, con giay sau nan da bi chinh phep nan keo ve.
    luot = [d for d in (giong.get("tung_luot_doc") or []) if isinstance(d, dict)]

    sai_so: list[float] = []
    ngan = 0
    for e in luot:
        khe = float(e.get("khe") or 0.0)
        if khe <= 0:
            continue
        # ⭐ Doc `lech` co san cua chinh ban ghi ay — cung mau so voi
        #    `nan_cho_vua.can_nan`. ⛔ Khong tu chia lai: hai ban sao cua mot
        #    phep tinh la thu kho nay da tra gia.
        lc = e.get("lech")
        if lc is None:
            continue
        sai_so.append(abs(float(lc)))
        if float(lc) < 0:
            ngan += 1

    he_so = [float(x) for x in (master.get("he_so_toc_da_ap") or [])]

    return {
        # Đ1 — sai so tuong doi so voi KHE (mau so = khe, nhu chinh sach nan)
        "sai_so_p50": _phan_vi(sai_so, 0.50),
        "sai_so_p90": _phan_vi(sai_so, 0.90),
        "sai_so_max": max(sai_so) if sai_so else None,
        # ⭐ `0` o day nghia la "co du lieu va khong luot nao ngan"; `None`
        #    nghia la "khong mot luot doc nao do duoc".
        "so_luot_do_duoc": len(sai_so) if luot else None,
        # Đ2 — ti le luot doc NGAN hon khe (`ngon_ngu.py:99` tro vao ten nay)
        "ti_le_doan_ngan": (ngan / len(sai_so)) if sai_so else None,
        # Đ3 — giai doan giong cham vi cai gi
        "giay_tts": giong.get("giay_tts"),
        "giay_llm_nan": giong.get("giay_llm_nan"),
        # Đ5 — he so tang toc THAT SU da ap (⛔ khong phai thu khach chon)
        "he_so_toc_p90": _phan_vi(he_so, 0.90),
        # Đ6 — nac (c): chap nhan lech nhung ⛔ khong im
        "so_doan_lech_cuoi": master.get("so_doan_lech_cuoi"),
        "giay_lech_cuoi": master.get("giay_lech_cuoi"),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Lop CSDL — dung map `{ten_giai_doan: outputs}` roi giao cho lop TINH
# ══════════════════════════════════════════════════════════════════════════════

def outputs_tung_giai_doan(db, run_id: str) -> dict[str, dict]:
    """`{ten_giai_doan: dict(outputs)}` cho dung cac giai doan `KHOA_CAN` can.

    ⭐ Cung khuon voi `quan_sat._outputs` va `giai_doan_noi_dung._doc_ban_bien_tap`:
       doc `asv_stage.outputs`, ⛔ khong doc `dong_thoi_gian`.
    """
    from apps.auto_scan_video import features

    ra: dict[str, dict] = {}
    for ten in KHOA_CAN:
        s = features.giai_doan_theo_ten(db, run_id, ten)
        ra[ten] = dict((s.outputs if s is not None else None) or {})
    return ra


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

    from apps.auto_scan_video.tables import AsvRun

    gen = get_session()
    db = next(gen)
    try:
        run = db.get(AsvRun, run_id)
        if run is None:
            print(f"KHONG THAY run {run_id!r} trong CSDL nay.")
            return 1

        ra = doi_soat(outputs_tung_giai_doan(db, run.id))
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
