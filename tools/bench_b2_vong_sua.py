"""bench_b2_vong_sua.py — vong sua dang GIUP hay dang PHA? Do CO CHE, ⛔ khong do ca chuoi.

    python tools/bench_b2_vong_sua.py --buoc cham   --ra <thu muc>
    python tools/bench_b2_vong_sua.py --buoc dichlai --ra <thu muc>

## ⭐ Cau hoi, va vi sao khong can 67 phut

⛔ Cau ta can tra loi KHONG phai *"chay ca chuoi ra so gi"* ma la **co che**:

> **Dich lai mot doan VON DA DUNG co lam no te di khong?**

Do la toan bo gia thuyet **85 -> 85** (N-02). Ba buoc, vai phut:

1. Cham ban NEN bang bo cham **ghim SHA** -> tap doan bi gan co.
2. ⭐ **SOI TAY** tap do, tach: doan **that su sai** vs doan **bi bao nham**.
   Voi FA ~43 % cua V1, phan bi bao nham se dong.
3. Cho DUNG **doan bi bao nham** di qua **dung** duong dich-lai cua vong sua,
   roi so voi ban nen: **tot len / khong doi / te di**, dem tung loai.

**Ba ket qua, ba hanh dong khac nhau** — do la ly do phep nay dang lam TRUOC:

| ket qua | nghia | hanh dong |
|---|---|---|
| **te di** | vong sua dang **PHA** | ⭐ co can cu **TAT** no cho toi khi bo cham xong — quyet duoc NGAY |
| **khong doi** | chi **ton tien**, khong hai | 85 -> 85 duoc giai thich; cau hoi chuyen sang **chi phi** |
| **tot len** | ⚠️ gia thuyet SAI | **bao ngay** — quan trong hon ca hai ca tren |

⇒ Chi chay luot day du 67 phut NEU phep nay ra *"khong doi"* hoac lan lon.

## ⛔ Duong dich lai: dung DUNG duong cua vong sua

`sua_chua.py:61` anh xa `dich_sai -> "content_process"`, tuc vong sua **chay lai
chinh giai doan dich** cho doan do — ⛔ khong co mot loi nhac "sua chua" rieng.
⇒ Bench goi lai `dich_thuat.dich_ban_ghi` tren dung nhung doan ay.

## ⚠️ KET QUA NAY CHI NOI VE BO CHAM V1

```
apps/auto_scan_video/qc_ai.py   604b82a7eccee07473541873b8ca11bf049a8d60   2026-09-23
```

⛔ **Khong noi gi** ve vong sua voi mot bo cham V3. Cau nay phai di **canh moi
con so**, khong phai o cuoi bao cao.

⭐ Va do la CO Y: cau hoi la ve **HIEN TRANG** — *"vong sua NHU NO DANG TON TAI
HOM NAY dang giup hay dang pha?"* — va quan sat 85 -> 85 cung sinh ra tu dung bo
cham ay. Cho bo cham moi la **doi mat cau hoi**.

## Khoa

⛔ **KHONG giu `cpu_nhieu`**: goi may B la cho mang. Tran <= 2 request/model.
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

#: Ban NEN (vong sua TAT) — dau ra cua buoc truoc.
NGUON = GOC / "docs/auto_scan_video_final/bang_chung/b2_dich_nen"

#: ⛔ Nhan BAT BUOC dan vao moi ban ghi. Khong rut gon.
NHAN = ("vong sua voi bo cham V1 — DA BIET hong, bao dong gia 43 %. "
        "⛔ Khong noi gi ve vong sua voi bo cham V3.")

TEP_BO_CHAM = "apps/auto_scan_video/qc_ai.py"

#: ⛔ `ltt-3.8` la tai nguyen DUNG CHUNG voi lan khac. Cho co cap so nhan khi
#: cong tra `concurrency_limited`, ⛔ khong ban lien tiep.
LAN_THU = 5
CHO_DAU_S = 8.0


def sha_bo_cham() -> str:
    """SHA cua bo cham **luc chay**. ⛔ Doc tu git, khong go lai."""
    try:
        return subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", TEP_BO_CHAM],
            cwd=GOC, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:                           # noqa: BLE001
        return ""


def _in(dong: str) -> None:
    """⛔ In khong bao gio duoc nem — stdout co the la cp1252."""
    try:
        print(dong)
    except Exception:                           # noqa: BLE001
        bo = getattr(sys.stdout, "encoding", None) or "ascii"
        print(dong.encode(bo, "replace").decode(bo, "replace"))


# ─────────────────────────────────────────────────────────────────────────────
# BUOC 1 — cham ban nen
# ─────────────────────────────────────────────────────────────────────────────

def cham_mot_phim(duong: Path) -> dict:
    """Cham ngu nghia ban nen. ⛔ Goi `qc_ai` NGUYEN VAN, khong sua gi trong no."""
    import platform_core.db as dbmod

    from apps.auto_scan_video import ai, qc_ai

    ban = json.loads(duong.read_text(encoding="utf-8"))
    doan = [{"ma": d["ma"], "goc": d["chu_goc"], "chu": d["chu_dich"]}
            for d in ban["doan"] if d.get("chu_dich", "").strip()]
    t0 = time.time()
    phan: list[dict] = []
    loi: list[dict] = []
    db = next(dbmod.get_session())
    try:
        for lo in qc_ai.chia_lo(doan):
            ma_gui = {d["ma"] for d in lo}
            # ⚠️ **`ltt-3.8` la tai nguyen DUNG CHUNG.** Do that 24/09: ca bon lo
            #    chet ngay lap tuc voi `concurrency_limited` (429) — mot lan khac
            #    dang dung chinh model do cho duong cham. Cong bao
            #    `retry: after_delay`, `recovery: wait`.
            # ⛔ Khong ban lien tiep: cho co cap so nhan, toi da `LAN_THU`.
            #    Thua thi GHI RA, ⛔ khong nuot va ⛔ khong bia mot phan doan.
            for lan in range(LAN_THU):
                try:
                    kq = ai.goi(db, ai.QC_NGU_NGHIA,
                                qc_ai.loi_nhac_ngu_nghia(lo, "vi"),
                                temperature=0.0)
                    phan.extend(qc_ai.doc_ngu_nghia(
                        ai.doc_json(kq["noi_dung"], ai.QC_NGU_NGHIA), ma_gui))
                    break
                except Exception as exc:        # noqa: BLE001
                    # 🔴 **Bat theo KIEU, ⛔ khong theo CHUOI.** Ban dau tep nay
                    #    do `"concurrency" in str(exc)` — va no **khong he chay**:
                    #    cong tra JSON `concurrency_limited`, nhung ngoai le den
                    #    tay ta la `MayBan("... ltt_llm: ban")`, tieng Viet. ⇒ Bo
                    #    lui khong bao gio no, ca bon lo chet o `lan_thu 1`.
                    #    ⭐ Cung ho voi bay da ghi hom nay: mot nhanh phong thu
                    #       viet cho mot hinh dang KHONG PHAI hinh dang that.
                    # ⛔ `AiMoHo` thi ⛔ KHONG duoc thu lai: model co the da chay
                    #    va da tinh tien (ADR-001 D9).
                    ban_ron = type(exc).__name__ == "MayBan"
                    if ban_ron and lan < LAN_THU - 1:
                        time.sleep(CHO_DAU_S * (2 ** lan))
                        continue
                    loi.append({"ma": sorted(ma_gui)[:3], "lan_thu": lan + 1,
                                "kieu": type(exc).__name__, "loi": str(exc)[:200]})
                    break
    finally:
        db.close()
    co = [p for p in phan if not p["dat"]]
    return {
        "phim": ban.get("phim"), "nhan": NHAN,
        "sha_bo_cham": sha_bo_cham(), "model_cham": _model_cham(),
        "so_doan": len(doan), "so_cham_duoc": len(phan),
        "so_bi_gan_co": len(co), "lo_hong": loi,
        "giay": round(time.time() - t0, 1),
        "bi_gan_co": [{**p, "goc": next(d["goc"] for d in doan if d["ma"] == p["ma"]),
                       "dich_nen": next(d["chu"] for d in doan if d["ma"] == p["ma"])}
                      for p in co],
    }


def _model_cham() -> str:
    from apps.auto_scan_video import ai

    try:
        return ai.model_cho(ai.QC_NGU_NGHIA)
    except Exception:                           # noqa: BLE001
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# BUOC 3 — dich lai DUNG nhung doan BI BAO NHAM
# ─────────────────────────────────────────────────────────────────────────────

def dich_lai(ma_can: list[str], duong_nen: Path) -> dict:
    """Cho cac ma di qua DUNG duong dich cua san pham, roi so voi ban nen.

    ⛔ Khong co loi nhac "sua chua" rieng: `sua_chua.py:61` anh xa
       `dich_sai -> content_process`, tuc chay lai chinh giai doan dich.
    """
    import platform_core.db as dbmod

    from apps.auto_scan_video import dich_thuat as D

    ban = json.loads(duong_nen.read_text(encoding="utf-8"))
    can = [d for d in ban["doan"] if d["ma"] in set(ma_can)]
    ban_ghi = {"ngon_ngu": ban.get("ngon_ngu") or "zh",
               "doan": [{"ma": d["ma"], "chu": d["chu_goc"]} for d in can]}
    db = next(dbmod.get_session())
    try:
        moi = D.dich_ban_ghi(db, ban_ghi)
    finally:
        db.close()
    return {"phim": ban.get("phim"), "nhan": NHAN, "sha_bo_cham": sha_bo_cham(),
            "so_dich_lai": len(moi),
            "cap": [{"ma": d["ma"], "goc": d["chu_goc"],
                     "nen": d["chu_dich"], "moi": moi.get(d["ma"], ""),
                     "giong_het": moi.get(d["ma"], "") == d["chu_dich"]}
                    for d in can]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--buoc", choices=("cham", "dichlai"), required=True)
    ap.add_argument("--phim", default="")
    ap.add_argument("--ra", default="")
    ap.add_argument("--ma", default="", help="dichlai: danh sach ma, ngan bang dau phay")
    a = ap.parse_args(argv)

    ten = [a.phim] if a.phim else ["v1", "v2", "v3"]
    ra_dir = Path(a.ra) if a.ra else None
    if ra_dir:
        ra_dir.mkdir(parents=True, exist_ok=True)

    for t in ten:
        duong = NGUON / f"{t}_nen.json"
        if a.buoc == "cham":
            kq = cham_mot_phim(duong)
            if ra_dir:
                (ra_dir / f"{t}_cham.json").write_text(
                    json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
            _in(f"{t}: {kq['so_bi_gan_co']}/{kq['so_cham_duoc']} bi gan co "
                f"({kq['giay']} s, model {kq['model_cham']}, "
                f"sha {kq['sha_bo_cham'][:8]}) lo_hong={len(kq['lo_hong'])}")
        else:
            ma = [x for x in a.ma.split(",") if x.strip()]
            kq = dich_lai(ma, duong)
            if ra_dir:
                (ra_dir / f"{t}_dichlai.json").write_text(
                    json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
            giong = sum(1 for c in kq["cap"] if c["giong_het"])
            _in(f"{t}: dich lai {kq['so_dich_lai']} doan, "
                f"giong het ban nen: {giong}/{len(kq['cap'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
