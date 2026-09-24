# -*- coding: utf-8 -*-
"""Chay test can PostgreSQL THAT — duong DUY NHAT, va no khong in bi mat.

    python tools\chay_test_pg.py -q tests/test_1787_wf_flow_acf_pg.py

## Vi sao cong cu nay ton tai

🔴 SU CO 24/09/2026. Mat khau superuser PostgreSQL (`C:\LTTPlatform\secrets\
   postgres-superuser.txt` — thu muc co ACL chan CO Y) duoc quet thay trong
   **bon** tep ban ghi hoi thoai dang van ban thuan, **hai** trong so do tu cac
   phien TRUOC. Tuc day la duong TAI DIEN, khong phai mot lan lo tay.

   Co che: moi ai can chay test PG deu tu do URL scratch bang
   `check_multiproc._tim_url()`, va URL do **nhung mat khau**. Chi can mot lan
   `print` de xem no dung chua la bi mat roi vao ban ghi — noi khong co ACL nao.

⛔ Mot dong luat trong brief ("khong in url") KHONG du: no da co san, va van bi
   vi pham. Cach chan that la **khong ai phai cam URL trong tay**: cong cu nay
   lay URL, dat vao `os.environ` cua tien trinh con, va **khong bao gio** tra no
   ra cho nguoi goi.

⭐ No cung giu `postgres_test` giup — mot phien chen vao giua se `drop_all` CSDL
   scratch duoi chan phep do dang chay.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    import check_multiproc as cm
    from cua_so_yen import CuaSoYen

    url, ly_do = cm._tim_url()
    if not url:
        # ⚠️ Khong co URL thi pytest se BO QUA im lang (`skip_without_postgres`)
        #    va in "passed" cho mot luot khong do gi. Tu choi thang o day.
        print(f"TU CHOI: khong co CSDL scratch PostgreSQL ({ly_do}).")
        print("  Dat LTT_TEST_DATABASE_URL, hoac cau hinh LTT_DATABASE_URL tro"
              " toi PostgreSQL.")
        return 3
    print("co CSDL scratch PostgreSQL (khong in url)")
    moi = dict(os.environ, LTT_TEST_DATABASE_URL=url)
    phien = os.environ.get("LTT_PHIEN") or "chay-test-pg"
    with CuaSoYen(phien, "chay test PostgreSQL that",
                  tai_nguyen=("postgres_test",), cho_toi_da_s=3 * 3600):
        # `-rA` de in TEN tung phep: mot luot PG tung exit 0 ma khong chay phep
        # nao, va "khong do" doc giong het "khong hong".
        r = subprocess.run([sys.executable, "-m", "pytest", "-rA", *argv],
                           cwd=str(GOC), env=moi)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
