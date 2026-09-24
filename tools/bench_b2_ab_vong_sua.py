"""bench_b2_ab_vong_sua.py — khung A/B cho VONG SUA. ⛔ Dung san, chay khi V3 ve.

    python tools/bench_b2_ab_vong_sua.py --kiem          # kiem kho, KHONG goi model
    python tools/bench_b2_ab_vong_sua.py --chay --ra <thu muc>

## ⭐ Vi sao dung san TRUOC khi co bo cham

Moi phan quyet ve **dich** dang cho bo cham. ⇒ Viec dang gia nhat luc nay la lam
sao **khoanh khac V3 ve thi do duoc ngay bang MOT lenh** — ⛔ khong phai ngoi
cho roi moi bat dau dung khung.

## Thiet ke — MOT bien, va bien do la VONG SUA

| giu CO DINH | vi sao |
|---|---|
| ban chep loi | cung `b1_chep_loi_moi/` cho ca hai nhanh |
| model dich | `ai.model_cho(DICH_THUAT)` — mot lan doc, dung cho ca hai |
| model cham | `ai.model_cho(QC_NGU_NGHIA)` |
| `PHIEN_BAN_LOI_NHAC` | ghi vao ket qua, ⛔ hai nhanh phai cung so |
| **SHA bo cham** | ghim va **ghi vao ket qua** — xem duoi |

    nhanh A  =  dich, ⛔ KHONG vong sua           (ban NEN)
    nhanh B  =  dich -> cham -> dich lai doan bi gan co   (vong sua, 1 vong)

⛔ `VONG_SUA_TOI_DA = 1` (`sua_chua.py:73`) — nhanh B chay **dung mot** vong, y
   nhu san pham. ⛔ Dung tu nang len de "xem co hoi tu khong": do la mot cau hoi
   KHAC, va no doi mot thiet ke khac.

## ⚠️ HAI CAU KHONG DUOC LAN — ghi canh moi con so

1. Ket qua noi ve **vong sua voi BO CHAM DANG GHIM**, ⛔ khong noi ve vong sua
   noi chung. Doi bo cham ⇒ **phai do lai**.
2. *"Vong sua voi V1 gay troi tren doan da dung"* ⛔ KHONG suy ra *"vong sua co
   hai"*. Phep can co HAI ve: (a) doan SAI duoc sua, (b) doan DUNG bi cham roi
   troi. V1 co FA 43 % nen ve (b) rat dong; V3 ha FA xuong 23 % ⇒ ⚠️ phep can
   **co the doi dau**.

## ⛔ Tai nguyen — luat 24/09

`ltt-3.8` **nhuong lan khac** cho toi khi ho xong. ⇒ `--chay` **tu dung** neu
buoc cham se roi vao `ltt-3.8`, tru khi co `--ep-3-8` (va luc do phai da bao
dieu phoi). ⛔ Goi may B **khong** giu `cpu_nhieu`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

# 🔴 **LAN THU BA trong mot phien.** `sys.stdout` duoi lop boc la **cp1252**, nen
#    mot ky tu Han hay mot dau `⚠️` lam `print` nem `UnicodeEncodeError` va
#    **giet ca lan chay SAU KHI tien da tieu** (bench B1 mat 8 ph 57 dung kieu
#    nay). Hai tep bench truoc vá bang mot ham `_in` boc try/except — ⛔ va no
#    chi cuu nhung dong DI QUA ham do: `json.dumps` in thang van chet, va do
#    dung la cho vua chet.
# ⇒ Sua mot lan o DAU RA, khong o tung cho goi.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:                               # noqa: BLE001
    pass                                        # ⛔ khong chet vi chuyen in an

NGUON = GOC / "docs/auto_scan_video_final/bang_chung/b1_chep_loi_moi"
PHIM = ("v1", "v2", "v3")

#: ⛔ Khop `sua_chua.VONG_SUA_TOI_DA`. Doc ra de doi chieu, ⛔ khong go lai so.
TEP_BO_CHAM = "apps/auto_scan_video/qc_ai.py"

#: Model ta **duoc phep** dung cho buoc cham theo luat chia tai nguyen 24/09.
MODEL_NHUONG = "qwen38-api"


def _sha(tep: str) -> str:
    try:
        return subprocess.run(["git", "log", "-1", "--format=%H", "--", tep],
                              cwd=GOC, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:                           # noqa: BLE001
        return ""


def moi_truong() -> dict:
    """Moi thu phai GHI vao ket qua de lan sau tai lap duoc. ⛔ Khong bo bot."""
    from apps.auto_scan_video import ai, sua_chua, van_ban

    def _an_toan(f):
        try:
            return f()
        except Exception:                       # noqa: BLE001
            return ""

    return {
        "model_dich": _an_toan(lambda: ai.model_cho(ai.DICH_THUAT)),
        "model_cham": _an_toan(lambda: ai.model_cho(ai.QC_NGU_NGHIA)),
        "phien_ban_loi_nhac": van_ban.PHIEN_BAN_LOI_NHAC,
        "vong_sua_toi_da": sua_chua.VONG_SUA_TOI_DA,
        "sha_bo_cham": _sha(TEP_BO_CHAM),
        "sha_loi_nhac_dich": _sha("apps/auto_scan_video/dich_thuat.py"),
        "⚠️ pham_vi": [
            "Ket qua noi ve vong sua VOI BO CHAM DANG GHIM o tren, ⛔ khong noi "
            "ve vong sua noi chung. Doi bo cham ⇒ PHAI DO LAI.",
            "⛔ 'Vong sua voi V1 gay troi tren doan da dung' KHONG suy ra 'vong "
            "sua co hai': V1 co FA 43 % nen ve (b) rat dong; V3 ha FA xuong "
            "23 % ⇒ phep can CO THE DOI DAU.",
        ],
    }


def kiem() -> int:
    """⛔ KHONG goi model. Chi tra loi: chay duoc chua, va se chay bang gi."""
    mt = moi_truong()
    thieu = [p for p in PHIM if not (NGUON / f"{p}.json").is_file()]
    print(json.dumps({**mt, "phim_thieu": thieu,
                      "san_sang": not thieu and bool(mt["model_dich"])},
                     ensure_ascii=False, indent=1))
    if mt["model_cham"] == MODEL_NHUONG:
        print(f"\n⛔ Buoc cham se roi vao {MODEL_NHUONG} — dang NHUONG lan khac "
              f"(luat 24/09). `--chay` se tu dung; can `--ep-3-8` + da bao dieu phoi.")
    return 0 if not thieu else 2


def _mot_phim(ten: str, *, ep: bool) -> dict:
    """Nhanh A va nhanh B tren cung mot ban chep loi."""
    import platform_core.db as dbmod

    from apps.auto_scan_video import ai, dich_thuat as D, qc_ai

    ban = json.loads((NGUON / f"{ten}.json").read_text(encoding="utf-8"))
    ban_ghi = {"ngon_ngu": ban.get("ngon_ngu") or "zh",
               "doan": [{"ma": d["ma"], "chu": d["chu"]} for d in ban["doan"]]}
    goc = {d["ma"]: d["chu"] for d in ban["doan"]}

    t0 = time.time()
    db = next(dbmod.get_session())
    try:
        # ── nhanh A: ban NEN ────────────────────────────────────────────────
        A = D.dich_ban_ghi(db, ban_ghi)

        # ── nhanh B: cham roi dich lai DUNG doan bi gan co ──────────────────
        lo_cham = [{"ma": m, "goc": goc[m], "chu": A[m]} for m in sorted(A)]
        phan: list[dict] = []
        for lo in qc_ai.chia_lo(lo_cham):
            ma_gui = {d["ma"] for d in lo}
            kq = ai.goi(db, ai.QC_NGU_NGHIA,
                        qc_ai.loi_nhac_ngu_nghia(lo, "vi"), temperature=0.0)
            phan.extend(qc_ai.doc_ngu_nghia(
                ai.doc_json(kq["noi_dung"], ai.QC_NGU_NGHIA), ma_gui))
        co = [p["ma"] for p in phan if not p["dat"]]

        B = dict(A)
        if co:
            # ⛔ Dung duong cua san pham: `sua_chua.py:61` anh xa
            #    `dich_sai -> content_process`, tuc chay lai giai doan dich cho
            #    DUNG nhung don vi duoc mo lai.
            B.update(D.dich_ban_ghi(db, {
                "ngon_ngu": ban_ghi["ngon_ngu"],
                "doan": [{"ma": m, "chu": goc[m]} for m in co]}))
    finally:
        db.close()

    doi = [m for m in sorted(A) if A.get(m) != B.get(m)]
    return {
        "phim": ban.get("phim"), **moi_truong(),
        "so_doan": len(A), "so_bi_gan_co": len(co),
        "so_doan_DOI_sau_vong_sua": len(doi),
        "giay": round(time.time() - t0, 1),
        # ⭐ Giu CA HAI ban, ⛔ khong chi giu hieu so: nguoi sau phai soi tay duoc.
        "cap": [{"ma": m, "goc": goc[m], "A_nen": A.get(m, ""),
                 "B_vong_sua": B.get(m, ""), "bi_gan_co": m in co,
                 "doi": A.get(m) != B.get(m)} for m in sorted(A)],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kiem", action="store_true")
    ap.add_argument("--chay", action="store_true")
    ap.add_argument("--phim", default="")
    ap.add_argument("--ra", default="")
    ap.add_argument("--ep-3-8", action="store_true",
                    help="⛔ chi dung khi DA BAO dieu phoi")
    a = ap.parse_args(argv)

    if a.kiem or not a.chay:
        return kiem()

    mt = moi_truong()
    if mt["model_cham"] == MODEL_NHUONG and not a.ep_3_8:
        print(f"⛔ DUNG: buoc cham se dung {MODEL_NHUONG}, dang NHUONG lan khac "
              f"(luat 24/09). Them `--ep-3-8` NEU da bao dieu phoi.")
        return 3

    ra_dir = Path(a.ra) if a.ra else None
    if ra_dir:
        ra_dir.mkdir(parents=True, exist_ok=True)
    for ten in ([a.phim] if a.phim else list(PHIM)):
        kq = _mot_phim(ten, ep=a.ep_3_8)
        if ra_dir:
            (ra_dir / f"{ten}_ab.json").write_text(
                json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{ten}: {kq['so_doan']} doan · gan co {kq['so_bi_gan_co']} · "
              f"DOI sau vong sua {kq['so_doan_DOI_sau_vong_sua']} · {kq['giay']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
