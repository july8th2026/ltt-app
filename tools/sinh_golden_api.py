"""
sinh_golden_api.py — sinh lại ảnh chụp hợp đồng công khai `tests/golden/`.

    python tools\\sinh_golden_api.py            # xem khac gi, KHONG ghi
    python tools\\sinh_golden_api.py --ghi      # ghi de

⭐ VÌ SAO CẦN MỘT SCRIPT, VÀ VÌ SAO NÓ MẶC ĐỊNH **KHÔNG GHI**.

   `tests/golden/public_api_catalog_v1.json` là **hợp đồng đóng băng**: nó tồn tại
   để một thay đổi hợp đồng phải **hiện ra trong diff** và có người nhìn. Trước
   file này, cách duy nhất cập nhật nó là chép tay từ thông báo lỗi của pytest —
   nghĩa là ai cũng làm được mà không ai đọc mình vừa đổi gì.

   Nên script này in **khác biệt từng khoá** trước, và chỉ ghi khi được bảo ghi.

⛔ SINH LẠI GOLDEN KHÔNG PHẢI CÁCH SỬA MỘT TEST ĐỎ. Test đỏ nghĩa là hợp đồng
   công khai vừa đổi. Có đúng hai câu trả lời hợp lệ:

     ① Thay đổi là **cố ý** → sinh lại, và **ghi vào `CHANGELOG.md`** vì sao.
     ② Thay đổi là **ngoài ý muốn** → sửa mã, đừng sinh lại.

   Chạy script này mà chưa biết mình đang ở trường hợp nào là chọn ① một cách
   mù quáng — và tích hợp của khách sẽ là chỗ phát hiện ra.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

TEP = GOC / "tests" / "golden" / "public_api_catalog_v1.json"


def dung() -> dict:
    """Hợp đồng hiện tại, dựng đúng như `test_181` dựng nó.

    ⚠️ Mở **mọi** tool, không phải chỉ tool đang bật. Golden chốt *hợp đồng đã
       công bố*, không chốt *cái gì đang bán* — hai thứ đó đổi vì hai lý do khác
       nhau, và trộn chúng làm cả hai mất nghĩa.
    """
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    from platform_core.registry import discover

    apps = discover()
    tat_ca = ",".join(sorted({t.name for a in apps if not a.error
                              for t in a.manifest.tools}))
    os.environ["LTT_PUBLIC_API"] = "1"
    os.environ["LTT_PUBLIC_API_TOOLS"] = tat_ca
    cat = build_catalog(load_public_api_config(), apps)
    return {"tools": [t.to_public_dict() for t in cat]}


def so(cu: dict, moi: dict) -> int:
    a = {t["name"]: t for t in cu.get("tools", [])}
    b = {t["name"]: t for t in moi.get("tools", [])}
    n = 0
    for ten in sorted(set(a) - set(b)):
        print(f"  - BO   {ten}"); n += 1
    for ten in sorted(set(b) - set(a)):
        print(f"  + THEM {ten}"); n += 1
    for ten in sorted(set(a) & set(b)):
        for k in sorted(set(a[ten]) | set(b[ten])):
            x, y = a[ten].get(k), b[ten].get(k)
            if x == y:
                continue
            n += 1
            print(f"  ~ DOI  {ten}.{k}")
            print(f"      cu : {json.dumps(x, ensure_ascii=False)[:220]}")
            print(f"      nay: {json.dumps(y, ensure_ascii=False)[:220]}")
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sinh lai golden hop dong API")
    ap.add_argument("--ghi", action="store_true", help="ghi de tep golden")
    a = ap.parse_args(argv)

    moi = dung()
    cu = json.loads(TEP.read_text(encoding="utf-8")) if TEP.exists() else {"tools": []}

    print(f"Golden: {TEP}")
    n = so(cu, moi)
    if n == 0:
        print("  khong co khac biet — khong can ghi.")
        return 0

    print(f"\n{n} khac biet.")
    if not a.ghi:
        print("Chua ghi gi. Doc ky tren, roi chay lai voi --ghi neu day la thay doi CO Y.")
        print("Va nho ghi vao docs/PUBLIC_API/CHANGELOG.md vi sao.")
        return 1

    # UTF-8 KHONG BOM — quy tac 1 cua CLAUDE.md.
    TEP.write_text(json.dumps(moi, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("Da ghi. DUNG QUEN docs/PUBLIC_API/CHANGELOG.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
