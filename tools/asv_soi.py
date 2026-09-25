r"""asv_soi.py — MOT CUA DOC cho van hanh Auto Scan Video.

    python tools\asv_soi.py <run_id>

Vi sao tep nay ton tai: prompt log van hanh (25/09) doi mot noi DUY NHAT tra
loi "run nay dang o dau, va no con SONG khong" ma khong bat ky su ho tro doc
thu muc log tren may worker (log xoay vong, worker co the da bien mat) hay tu
ghep nhieu truy van CSDL bang tay.

⛔ Tep nay KHONG dung lai dong thoi gian — no goi
   `quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)`, nguon chan ly DUY
   NHAT (xem docstring `apps/auto_scan_video/quan_sat.py:1-25`). No chi THEM
   ba dieu quan_sat khong lam: doc `run_id` tu argv, chon giai doan DANG CHAY,
   va tinh "tien bo lan cuoi cach day bao lau" tu nhip `progress_counter`
   (25/09) nam trong `su_kien` cua giai doan do.

🔑 Cau tra loi quan trong nhat — "con song hay da treo" — nam o DONG DAU, chua
   xuong bang: mot nguoi ho tro doc dong nay truoc, bang chi de doi chieu.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)


def _utc(gt: datetime | None) -> datetime | None:
    """`fromisoformat` tren mot chuoi khong offset (SQLite dev, xem
    `quan_sat._theo_utc`) tra ve NAIVE. Chi CSDL nay ghi cot do bang UTC, nen
    gan UTC khong phai mot phong doan."""
    if gt is None or gt.tzinfo is not None:
        return gt
    return gt.replace(tzinfo=timezone.utc)


def _ago(gt_iso: str | None) -> str:
    if not gt_iso:
        return "khong ro"
    try:
        gt = _utc(datetime.fromisoformat(gt_iso))
    except ValueError:
        return f"khong doc duoc moc thoi gian ({gt_iso!r})"
    giay = max(0.0, (datetime.now(timezone.utc) - gt).total_seconds())
    if giay < 90:
        return f"{giay:.0f} giay truoc"
    if giay < 5400:
        return f"{giay / 60:.1f} phut truoc"
    return f"{giay / 3600:.1f} gio truoc"


def _dong_dau(dong: dict) -> str:
    """Cau tra loi DUY NHAT phan biet "dang chay" voi "da treo" — dong 1,
    khong chon duoi bang (yeu cau cua prompt log van hanh)."""
    trang_thai = dong.get("trang_thai")
    ten_dang_chay = dong.get("dang_chay") or ""
    if trang_thai not in ("queued", "running") or not ten_dang_chay:
        return (f"RUN {trang_thai.upper()} — khong con giai doan nao dang "
               f"chay (ket thuc: {dong.get('ket_thuc_luc') or 'chua xong'}).")

    muc = next((m for m in dong["giai_doan"] if m["giai_doan"] == ten_dang_chay),
              None)
    if muc is None:
        return f"DANG CHAY giai doan {ten_dang_chay!r} — khong doc duoc dong."

    su_kien = list(muc.get("su_kien") or [])
    nhip = [e for e in su_kien if e.get("ma") == "progress_counter"]
    if nhip:
        e = nhip[-1]
        ct = e.get("chi_tiet") or {}
        return (
            f"DANG CHAY {ten_dang_chay} — TIEN BO LAN CUOI CACH DAY "
            f"{_ago(e.get('luc'))} ({ct.get('da_xong', '?')}/"
            f"{ct.get('tong', '?')} {ct.get('don_vi') or 'don vi'}).")
    if su_kien:
        e = su_kien[-1]
        return (
            f"DANG CHAY {ten_dang_chay} — giai doan nay KHONG phat nhip tien "
            f"do co bo dem (binh thuong voi giai doan ngan/khong lap don vi). "
            f"Hoat dong cuoi: '{e.get('ma')}' cach day {_ago(e.get('luc'))}.")
    return (
        f"DANG CHAY {ten_dang_chay} — CHUA CO SU KIEN NAO ghi duoc cho luot "
        f"job hien tai (job cu truoc khi co tinh nang nay, hoac vua nhat).")


def _bang(dong: dict) -> str:
    dong_ra = []
    for m in dong["giai_doan"]:
        dv = m.get("don_vi") or {}
        giay_s = f"{m['giay']:.1f}" if m.get("giay") is not None else "-"
        dong_ra.append(
            f"  {m['giai_doan']:<16} {m['trang_thai']:<18} "
            f"{giay_s:>8} s   "
            f"thu {m.get('so_lan_thu', 0)}   "
            f"don_vi {dv.get('xong', '')}/{dv.get('tong', '')}   "
            f"worker {(m.get('job') or {}).get('worker', '')}   "
            f"credit {m.get('credit', '')}"
            + (f"   LOI: {m['loi']}" if m.get("loi") else ""))
    return "\n".join(dong_ra)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    run_id = argv[1]

    from platform_core.db import get_session
    from apps.auto_scan_video import quan_sat
    from apps.auto_scan_video.tables import AsvRun

    gen = get_session()
    db = next(gen)
    try:
        # ⛔ Doc THANG, khong qua `features.lay_run` (doi `owner_id`): day la
        #    cong cu van hanh chay TAY tren may, khong phai duong khach —
        #    thieu owner_id la dung ranh gioi cua no, khong phai lo hong.
        run = db.get(AsvRun, run_id)
        if run is None:
            print(f"KHONG THAY run {run_id!r} trong CSDL nay.")
            return 1

        dong = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)

        print(_dong_dau(dong))
        print()
        print(f"run_id={dong['run_id']}  chu_so_huu={dong.get('chu_so_huu', '')}  "
             f"tao_luc={dong.get('tao_luc')}  "
             f"credit_giu/tinh={dong.get('credit_da_giu')}/"
             f"{dong.get('credit_da_tinh')}")
        if dong.get("giai_doan_hong"):
            print(f"GIAI DOAN HONG: {', '.join(dong['giai_doan_hong'])}")
        print()
        print(_bang(dong))
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
