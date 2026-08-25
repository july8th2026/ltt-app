"""check_server_routes.py — bánh cóc kích thước cho `server/routes/`.

## ⭐ VÌ SAO TỆP NÀY TỒN TẠI

`tools/lint_app_contract.py` thi hành trần **900 dòng / 30 handler** cho `apps/`.
Trần đó ra đời sau khi đo được một điều thật: *"hợp đồng không nói logic nghiệp
vụ nằm ở đâu, nên route thành chỗ để mọi thứ rơi vào"* — và đã có tệp route
**1.799 dòng** vì vậy.

`server/` thì **không có ngưỡng nào**. Và ba tệp lớn nhất kho đều nằm ở đó:

    server/admin_api.py         1.897 dòng
    server/routes/developer.py  1.521 dòng · 32 handler
    server/admin.py             1.388 dòng

`developer.py` vượt **cả hai** ngưỡng của `apps/` — 1.521 > 900 và 32 > 30 — mà
không có gì cân nó, chỉ vì nó nằm ở thư mục khác. Cùng một lực đang tác dụng lên
cùng một loại tệp; chỉ khác là một bên có cân, một bên không.

## 💡 VÌ SAO LÀ BÁNH CÓC CHỨ KHÔNG PHẢI TRẦN CỨNG

Đặt trần cứng 900 dòng hôm nay thì gate đỏ ngay, và ba tệp trên **không phải lỗi
cần sửa gấp** — audit 2026-08-26 đo change locality của chúng:

  `developer.py`  sửa cùng `public_api/tables`(7), `invocation`(5), `examples`(5)
                  => nghiệp vụ đang sống trong tầng vận chuyển. ĐÁNG chẻ.
  `admin_api.py`  churn 16, bạn đồng hành thưa (4/3/3)
                  => tệp lớn mà ít đổi và đổi cô lập là CHI PHÍ THẤP. Chưa đáng.

Chẻ `admin_api.py` bây giờ là trả tiền hôm nay cho một vấn đề chưa xuất hiện.

⇒ Bánh cóc: **chốt tập hợp hiện có, không cho THÊM**. Cùng khuôn
`check_silent_except.py` và `check_bo_qua.py`.

⛔ Và chốt **TẬP HỢP**, không chốt **SỐ LƯỢNG**: một tệp mới vượt ngưỡng trong khi
một tệp cũ được chẻ sẽ giữ nguyên tổng số, và một bánh cóc đếm số sẽ im lặng cho
qua. Bài học đó đã trả giá ở `check_so_test.py`.

    python tools/check_server_routes.py            # kiểm
    python tools/check_server_routes.py --update   # hạ mốc sau khi ĐÃ chẻ thật
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
MOC = pathlib.Path(__file__).resolve().parent / "server_routes_baseline.json"

#: Cùng con số với `lint_app_contract.py`. Một hợp đồng, hai nơi thi hành — nếu
#: hai bên lệch nhau thì người đọc không biết tin bên nào.
MAX_DONG = 900
MAX_HANDLER = 30

#: Quét ở đâu. `server/api/` cố ý KHÔNG có ở đây: nó là bề mặt hợp đồng công khai
#: đã bị đóng băng bởi `check_api_compat.py` + ảnh chụp golden, tức đã có thứ
#: khác canh, và canh chặt hơn.
THU_MUC = ("server/routes", "server")

HANDLER = re.compile(r"^\s*@(?:router|app)\.(get|post|put|delete|patch)\(", re.M)


def do(f: pathlib.Path) -> tuple[int, int]:
    txt = f.read_text(encoding="utf-8", errors="replace")
    return len(txt.splitlines()), len(HANDLER.findall(txt))


def quet() -> dict[str, dict]:
    ra: dict[str, dict] = {}
    for thu_muc in THU_MUC:
        d = GOC / thu_muc
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.py")):
            if f.name.startswith("_"):
                continue
            dong, handler = do(f)
            if dong > MAX_DONG or handler > MAX_HANDLER:
                ra[f.relative_to(GOC).as_posix()] = {"dong": dong,
                                                     "handler": handler}
    return ra


def _doc_moc() -> dict:
    if not MOC.is_file():
        return {}
    return json.loads(MOC.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--update", action="store_true",
                   help="ghi lai moc — chi dung sau khi DA che that")
    args = p.parse_args()

    hien = quet()
    if args.update:
        MOC.write_text(json.dumps(hien, ensure_ascii=False, indent=2,
                                  sort_keys=True) + "\n", encoding="utf-8")
        print(f"da ghi moc: {len(hien)} tep vuot nguong")
        return 0

    moc = _doc_moc()
    moi = sorted(set(hien) - set(moc))
    da_sua = sorted(set(moc) - set(hien))

    for ten in sorted(hien):
        s = hien[ten]
        dau = "!!" if ten in moi else "  "
        print(f"{dau} {ten:<38} {s['dong']:5d} dong  {s['handler']:3d} handler")

    if da_sua:
        print(f"\nDA XU LY (khong con vuot nguong): {', '.join(da_sua)}")
        print("Chay --update de ha moc.")

    if moi:
        print(f"\nTHEM {len(moi)} tep vuot nguong {MAX_DONG} dong / "
              f"{MAX_HANDLER} handler:")
        for ten in moi:
            print(f"   {ten}")
        print("\nTach theo USE CASE ra module rieng — dung cat doi cho du con so.")
        print("RESULT: FAIL")
        return 1

    print(f"\nVuot nguong: {len(hien)} tep | moc: {len(moc)} tep — khong them.")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
