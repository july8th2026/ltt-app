"""
check_so_test.py — bánh cóc chặn TRÙNG SỐ tệp test.

    py tools/check_so_test.py            # kiem, so voi moc
    py tools/check_so_test.py --list     # liet ke tung so bi trung
    py tools/check_so_test.py --accept   # ha moc xuong so hien tai (chi khi da don)

⭐ VÌ SAO CÓ TỆP NÀY

   Quy ước `test_<so>_<ten>.py` sinh ra để làm **một chỉ mục tra được**: nói "xem
   test_212" là người khác mở đúng một tệp. Đo ngày 23/08/2026: **24 số đang bị
   trùng**, có số mang **ba** tệp khác nhau.

   Nguyên nhân không phải ai cẩu thả. Repo này đang có **nhiều phiên làm việc song
   song**, mỗi phiên chọn số tiếp theo dựa trên thứ nó nhìn thấy lúc bắt đầu — nên
   hai phiên bắt đầu cùng buổi chiều sẽ chọn trùng nhau, đều đúng theo cách họ
   nhìn.

⛔ VÌ SAO KHÔNG ĐI ĐỔI TÊN 24 TỆP

   Đổi tên là **chạy theo đuôi**: ba tệp tôi vừa tạo (259, 263, 264) đã bị trùng
   lại **trong cùng buổi**. Sửa hậu quả mà không sửa nguyên nhân thì tuần sau lại
   24 số khác. Và đổi tên tệp test của phiên khác là đụng vào việc đang dở của họ.

   Nên tệp này **không dọn quá khứ** — nó **chặn tương lai**. Cùng khuôn
   `check_silent_except.py`: một cái mốc, không cho tăng.

⭐ Con số này **chỉ được phép giảm**. Ai dọn được một trùng lặp thì hạ mốc bằng
   `--accept`, và lần hạ đó hiện ra trong diff.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import defaultdict

GOC = pathlib.Path(__file__).resolve().parent.parent
THU_MUC = GOC / "tests"
TEP_MOC = pathlib.Path(__file__).with_name("check_so_test.moc")

#: Mốc mặc định khi chưa có tệp mốc — số đo được ngày 23/08/2026.
MOC_MAC_DINH = 24


def quet() -> dict:
    """{so: [ten tep]} cho mọi số bị dùng nhiều hơn một lần."""
    theo_so: dict = defaultdict(list)
    for f in sorted(THU_MUC.glob("test_*.py")):
        m = re.match(r"test_(\d+)_", f.name)
        if m:
            theo_so[int(m.group(1))].append(f.name)
    return {k: v for k, v in sorted(theo_so.items()) if len(v) > 1}


def so_trong(bat_dau: int = 1, het: int = 400) -> list:
    """Các số CHƯA ai dùng — để người thêm test mới chọn nhanh."""
    da_dung = set()
    for f in THU_MUC.glob("test_*.py"):
        m = re.match(r"test_(\d+)_", f.name)
        if m:
            da_dung.add(int(m.group(1)))
    return [n for n in range(bat_dau, het) if n not in da_dung]


def doc_moc() -> int:
    try:
        return int(TEP_MOC.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return MOC_MAC_DINH


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chan trung so tep test")
    p.add_argument("--list", action="store_true", help="liet ke tung so bi trung")
    p.add_argument("--accept", action="store_true",
                   help="ha moc xuong so hien tai (chi dung khi DA don bot)")
    a = p.parse_args(argv)

    trung = quet()
    moc = doc_moc()

    if a.list:
        for so, ds in trung.items():
            print(f"  {so}: {', '.join(ds)}")
        print(f"\nso con trong (10 dau): {so_trong()[:10]}")

    if a.accept:
        if len(trung) > moc:
            print(f"KHONG ha moc duoc: hien {len(trung)} > moc {moc}", file=sys.stderr)
            return 1
        TEP_MOC.write_text(f"{len(trung)}\n", encoding="utf-8")
        print(f"Da ha moc: {moc} -> {len(trung)}")
        return 0

    print(f"So tep test bi trung so: {len(trung)} | moc: {moc}")
    if len(trung) > moc:
        them = {s: ds for s, ds in trung.items() if len(ds) > 1}
        print(f"TANG {len(trung) - moc} so so voi moc.")
        print("Truoc khi them mot tep test, chay:  py tools/check_so_test.py --list")
        print(f"So con trong: {so_trong()[:10]}")
        for so, ds in list(them.items())[-6:]:
            print(f"  {so}: {', '.join(ds)}")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
