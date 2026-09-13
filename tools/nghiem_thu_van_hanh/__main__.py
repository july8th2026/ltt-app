"""Điểm chạy của bộ nghiệm thu VẬN HÀNH THẬT.

    py -m tools.nghiem_thu_van_hanh --db <url> --kich-ban J1,J4,J5
    py -m tools.nghiem_thu_van_hanh --db <url> --tat-ca

⛔ **Pha 0 chạy TRƯỚC, luôn luôn, và nó NÉM.** Một bộ đo tự nhận mình mù rồi vẫn
   đo là tệ hơn một bộ đo không chạy — nó sinh ra những con số **trông như** dữ
   liệu. Xem `soi.tu_kiem`.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from tools.nghiem_thu_van_hanh import bao_cao, chay, kich_ban, nop_tai, soi

GOC_KHO = str(pathlib.Path(__file__).resolve().parents[2])

#: Kịch bản khai `can_tai_khoan_hai` PHẢI trải tải ra nhiều tài khoản — nếu
#: không, trần tài khoản không bật và số đo không thuộc kịch bản nào.
KHOA_NHIEU_TAI_KHOAN = {f"L{i}": ("vh1-a", "vh2-a", "vh3-a")[i % 3]
                        for i in range(1, 41)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="VAN HANH THAT — bo nghiem thu")
    ap.add_argument("--db", required=True)
    ap.add_argument("--goc", default=nop_tai.GOC_API)
    ap.add_argument("--kich-ban", default="")
    ap.add_argument("--tat-ca", action="store_true")
    ap.add_argument("--ban-ghi", default="ban_ghi_van_hanh.json")
    a = ap.parse_args()

    print("== PHA 0 — tu chung minh bo do khong mu ==")
    try:
        for m in soi.tu_kiem(a.db, a.goc):
            print(f"   {m.ten:10s} OK  {m.gia_tri!r}")
    except soi.SoMu as e:
        print(f"\n   PHA 0 DO: {e}")
        print("   ⛔ DUNG. Loi o BO DO, khong o he thong.")
        return 2
    print("   PHA 0 DAT\n")

    loi_khai = kich_ban.kiem_hop_le(kich_ban.MA_TRAN)
    if loi_khai:
        print("== MA TRAN KHAI SAI ==")
        for x in loi_khai:
            print(f"   {x}")
        return 2

    chon = ([k for k in kich_ban.MA_TRAN] if a.tat_ca else
            [kich_ban.tim(m.strip()) for m in a.kich_ban.split(",") if m.strip()])
    if not chon:
        print("khong chon kich ban nao; dung --tat-ca hoac --kich-ban J1,J4")
        return 2

    ds: list[chay.KetQuaKichBan] = []
    for kb in chon:
        print(f"== {kb.ma}: {kb.mo_ta} ==")
        khoa = KHOA_NHIEU_TAI_KHOAN if kb.can_tai_khoan_hai else None

        def _nop(k: kich_ban.KichBan, _khoa=khoa) -> dict:
            return nop_tai.nop_that(k, goc_kho=GOC_KHO, khoa_theo_nhan=_khoa)

        kq = chay.chay_mot(kb, db_url=a.db, goc=a.goc, nop=_nop)
        ds.append(kq)
        trang = ("NHIEM" if kq.nhiem else
                 "dat" if kq.dat else "TRUOT" if kq.dat is False else "chua cham")
        print(f"   -> {trang}"
              + (f"  ({kq.ly_do_nhiem})" if kq.nhiem else "")
              + f"  {({k: v for k, v in kq.do_duoc.items() if k != 'luot'})}\n")

    ban = chay.ghi_ban_ghi(ds, a.ban_ghi)
    ban["commit_production"] = next(
        (k.sau.get("http", {}).get("gia_tri") for k in ds if k.sau), "")
    print(bao_cao.bang_chat_luong(ban))
    print(f"\n   [ban ghi] {a.ban_ghi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
