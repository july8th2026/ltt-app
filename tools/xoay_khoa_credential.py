# -*- coding: utf-8 -*-
"""Xoay khoa ma hoa cua kho credential (spec Sec9.1) — ma hoa LAI moi hang.

    python tools\\xoay_khoa_credential.py --that          # ghi that
    python tools\\xoay_khoa_credential.py                 # chi dem, khong ghi

## Trinh tu DUNG, va vi sao thu tu do khong doi cho duoc

1. Sinh khoa moi. Dat khoa CU hien tai vao `LTT_TOKEN_ENCRYPTION_KEYS_CU`
   (mai nhat truoc, ngan bang dau phay), dat khoa MOI vao
   `LTT_TOKEN_ENCRYPTION_KEY`. Chay lai `setup\\2-cai-dat.ps1` — nssm NUONG
   bien moi truong luc CAI, `restart` khong nap ENV moi.
2. Chay tep nay. Tu luc nay moi hang da mang khoa moi.
3. CHI KHI DO moi duoc bo khoa cu khoi `LTT_TOKEN_ENCRYPTION_KEYS_CU`.

⛔ Bo khoa cu o buoc 1 la tu xoa du lieu cua chinh minh: `MultiFernet` doc
   duoc hang cu **vi** khoa cu con trong danh sach.

## ⛔ Khong in gi ra ngoai mot con so

Ban ro khong bao gio thanh mot bien o day: `secretbox.xoay` dung
`MultiFernet.rotate`, giai ma va ma hoa lai ben trong thu vien. Tep nay chi
dem so hang. ⛔ Khong in khoa, khong in URL CSDL, khong in preview.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--that", action="store_true",
                    help="ghi that (mac dinh chi dem roi rollback)")
    tham = ap.parse_args(argv)

    from platform_core import credential, secretbox
    from platform_core.db import get_session

    if secretbox.so_khoa() < 2 and tham.that:
        # ⚠️ Mot lan xoay voi DUNG MOT khoa la mot lan ghi lai vo nghia: no ma
        #    hoa lai bang chinh khoa cu. Doi khi do la y dinh that (doi salt),
        #    nhung thuong xuyen hon no la dau hieu buoc 1 chua lam.
        print("TU CHOI: chi co MOT khoa dang nap. Dat khoa cu vao "
              f"{secretbox.ENV_KHOA_CU} truoc, xem docstring tep nay.")
        return 3

    gen = get_session()
    db = next(gen)
    try:
        dem = credential.xoay_khoa(db)
        if tham.that:
            db.commit()
            print(f"da xoay {dem} hang")
        else:
            db.rollback()
            print(f"{dem} hang SE duoc xoay (chua ghi; them --that de ghi)")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
