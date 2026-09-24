"""bench_b2_dich_nen.py — BAN DICH NEN zh->vi, ⛔ VONG SUA TAT.

    python tools/bench_b2_dich_nen.py --ra <thu muc>          # ca ba phim
    python tools/bench_b2_dich_nen.py --phim v3 --lo 1        # mot lo, de thu

## ⭐ Vi sao "ban NEN" la viec quan trong nhat, khong phai mot bien the

Ta **chua bao gio** tach *"chat luong dich"* khoi *"dich + mot vong sua chay
bang mot bo cham hong"*. Quan sat **85 -> 85 khong hoi tu** (N-02) la so cua
**CA CUM**, va cum ay chua mot bo cham vua duoc do la **bao dong gia 43 %**.

⇒ Vong sua nhieu kha nang dang **dich lai nhung cau von da dung**. Khong co ban
  nen, moi con so dich tu truoc toi nay **khong quy duoc cho ai**.

## ⛔ Tai sao la mot BENCH chu khong phai doi cau hinh san pham

Chu du an chot: dung `ltt-3.5` cho dich. Nhung id model cua ASV den tu **MOT**
cho khai:

    apps/auto_scan_video/manifest.py:102   model_llm_noi_bo="ltt-3.8"

va cho do phuc vu **ca nam** thao tac AI cua ASV — **ke ca `qc_ai`**, dang la
vung cua mot lan khac (duong cham ngu nghia). Doi no o day la doi model cua lan
kia **trong im lang**.

⇒ ⛔ Lan nay KHONG sua cho dung chung do. Bench nay **ghim model tai cho goi**,
  va giu nguyen moi thu khac cua duong ASV:

| thanh phan | lay tu dau |
|---|---|
| loi nhac | `dich_thuat._loi_nhac` — ⛔ NGUYEN VAN, khong sua |
| chia lo | `dich_thuat.chia_lo` (`DOAN_MOI_LO = 20`) |
| doc ket qua | `dich_thuat._doc_ban_dich` (khoa theo ma doan) |
| nhiet do | `0.2` — ⛔ dung con so `dich_mot_lo` dang dung |
| model | **ghim `ltt-3.5`** ⬅ dieu DUY NHAT khac |

⚠️ **Loi nhac hien khong he nhac den phien Han-Viet cho ten rieng.** ⛔ Va bench
   nay CO Y khong them: viec 2 phai **do xem no tu ra Han-Viet hay khong**. Sua
   loi nhac truoc khi do la xoa mat chinh cau hoi.

## ⚠️ Khoa va tran dong thoi

- ⛔ **KHONG giu `cpu_nhieu`**: goi may B la **cho mang**, khong dot loi may A.
- Tran **<= 2 request moi model** ⇒ `SONG_SONG = 2`, ⛔ dung nang.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Ban chep loi MOI (co dau cau, co moc tu) — dau ra cua B1.
NGUON = GOC / "docs/auto_scan_video_final/bang_chung/b1_chep_loi_moi"

#: ⛔ Tran dong thoi moi model do chu du an chot. Dung nang.
SONG_SONG = 2

#: Bi danh model cho buoc dich. ⛔ Ghim TAI CHO GOI — xem docstring dau tep.
MODEL_DICH = "ltt-3.5"

#: ⛔ Nhiet do PHAI khop `dich_thuat.dich_mot_lo`. Doi no la do mot duong khac.
NHIET_DO = 0.2


def _model_theo_provider() -> tuple[list, dict]:
    from apps.auto_scan_video.ai import THU_TU_PROVIDER
    from platform_core.llm import canonical

    mid = canonical.ALIAS_SANG_ID.get(MODEL_DICH, MODEL_DICH)
    return list(THU_TU_PROVIDER), {pid: mid for pid in THU_TU_PROVIDER}


def dich_mot_lo(lo: list[dict], *, ngon_ngu_goc: str) -> dict:
    """MOT lo qua duong ASV, model ghim `ltt-3.5`. Tra `{ma: cau_dich}`."""
    import platform_core.db as dbmod
    from platform_core.llm import dieu_phoi

    from apps.auto_scan_video import dich_thuat as D

    thu_tu, ban_do = _model_theo_provider()
    db = next(dbmod.get_session())
    try:
        kq = dieu_phoi.goi(
            db, messages=D._loi_nhac(lo, ngon_ngu_goc),      # noqa: SLF001
            thu_tu_provider=thu_tu, model_theo_provider=ban_do,
            temperature=NHIET_DO, max_tokens=D._tran_token_ra(),  # noqa: SLF001
            timeout_s=300.0)
    finally:
        db.close()
    noi_dung = getattr(kq, "noi_dung", None) or getattr(kq, "content", "")
    return D._doc_ban_dich(str(noi_dung), {d["ma"] for d in lo})  # noqa: SLF001


def dich_mot_phim(duong: Path) -> dict:
    """Dich ca mot ban chep loi. ⛔ Vong sua TAT — khong goi `sua_chua`."""
    from apps.auto_scan_video import dich_thuat as D

    ban = json.loads(duong.read_text(encoding="utf-8"))
    doan = list(ban.get("doan") or [])
    ngon_ngu = str(ban.get("ngon_ngu") or "")
    cac_lo = D.chia_lo(doan)

    t0 = time.time()
    gop: dict = {}
    loi: list[dict] = []
    with ThreadPoolExecutor(max_workers=SONG_SONG) as bom:
        viec = {bom.submit(dich_mot_lo, lo, ngon_ngu_goc=ngon_ngu): i
                for i, lo in enumerate(cac_lo, start=1)}
        for tuong_lai, i in viec.items():
            try:
                gop.update(tuong_lai.result())
            except Exception as exc:            # noqa: BLE001
                # ⛔ Ghi TRIEU CHUNG, khong nuot: mot lo hong van la mot ket qua,
                #    va so lo hong phai di CUNG bang so (bai hoc N-19).
                loi.append({"lo": i, "kieu": type(exc).__name__,
                            "loi": str(exc)[:300]})
    return {
        "phim": ban.get("phim"), "ngon_ngu": ngon_ngu,
        "model": MODEL_DICH, "nhiet_do": NHIET_DO,
        "vong_sua": False, "vong_sua_ghi_chu": "⛔ TAT — day la ban NEN",
        "so_doan_nguon": len(doan), "so_lo": len(cac_lo),
        "so_doan_dich_duoc": len(gop),
        "so_doan_THIEU": len(doan) - len(gop),
        "lo_hong": loi, "giay": round(time.time() - t0, 1),
        "doan": [{"ma": d["ma"], "bat": d["bat"], "ket": d["ket"],
                  "chu_goc": d["chu"], "chu_dich": gop.get(d["ma"], "")}
                 for d in doan],
    }


# ─────────────────────────────────────────────────────────────────────────────
# VIEC 2 — mau doc tay. ⛔ QUY TAC CHON VIET TRUOC, khong chon sau khi thay so.
# ─────────────────────────────────────────────────────────────────────────────

#: ⛔ **Quy tac chon, chot TRUOC khi nhin bat ky ban dich nao:** moi phim **10**
#: cau, **cach deu** tren toan bo ban ghi — chi so `round(i * (n-1) / 9)` voi
#: `i = 0..9`, khu trung. ⭐ Cach deu chu khong ngau nhien, de lan sau chay lai
#: ra **dung** mau do; va ⛔ khong chon tay, de khong ai chon duoc nhung cau dep.
MAU_MOI_PHIM = 10


def chon_mau(so_doan: int, *, moi_phim: int = MAU_MOI_PHIM) -> list[int]:
    if so_doan <= moi_phim:
        return list(range(so_doan))
    return sorted({round(i * (so_doan - 1) / (moi_phim - 1))
                   for i in range(moi_phim)})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ra", default="", help="thu muc ghi ket qua")
    ap.add_argument("--phim", default="", help="v1 | v2 | v3 (mac dinh: ca ba)")
    ap.add_argument("--lo", type=int, default=0, help="chi dich N lo dau (thu)")
    a = ap.parse_args(argv)

    ten = [a.phim] if a.phim else ["v1", "v2", "v3"]
    ra_dir = Path(a.ra) if a.ra else None
    if ra_dir:
        ra_dir.mkdir(parents=True, exist_ok=True)

    for t in ten:
        duong = NGUON / f"{t}.json"
        if not duong.is_file():
            print(f"⛔ khong thay {duong}")
            return 2
        kq = dich_mot_phim(duong)
        kq["mau_doc_tay"] = chon_mau(kq["so_doan_nguon"])
        goi = json.dumps(kq, ensure_ascii=False, indent=1)
        if ra_dir:
            (ra_dir / f"{t}_nen.json").write_text(goi, encoding="utf-8")
        print(f"{t}: {kq['so_doan_dich_duoc']}/{kq['so_doan_nguon']} doan "
              f"({kq['so_lo']} lo, {kq['giay']} s) "
              f"thieu={kq['so_doan_THIEU']} lo_hong={len(kq['lo_hong'])}")
        for l in kq["lo_hong"]:
            print(f"   ⛔ lo {l['lo']}: {l['kieu']} {l['loi'][:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
