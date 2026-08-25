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
#:
#: ⚠️ Giữ lại chỉ để đọc lịch sử. Phép so hiện tại dùng TẬP HỢP các số bị
#: trùng, không dùng số lượng — xem `doc_moc`.
MOC_MAC_DINH = 24

#: Dòng đầu của tệp mốc đời mới. Có nó để phân biệt dứt khoát với tệp đời cũ
#: (một dòng, một con số), thay vì đoán theo hình dạng.
DAU_HIEU = "# tap-hop-so-bi-trung"


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


def doc_moc() -> set:
    """Tập các số ĐƯỢC PHÉP trùng.

    🔴 VÌ SAO LÀ TẬP HỢP CHỨ KHÔNG PHẢI SỐ LƯỢNG

    Bản đầu chốt số lượng: `24 trùng / mốc 24 -> PASS`. Nhưng một va chạm
    **mới** vẫn lọt nếu một va chạm **cũ** được dọn đi trong cùng lượt — tổng
    không đổi, và phép kiểm im lặng.

    Đã xảy ra thật ngày 25/08: hai phiên song song cùng tạo `test_303_*`, và
    bánh cóc báo PASS. Nó không sai theo cách nó khai; nó **đo nhầm đối
    tượng** — thứ cần chặn là *"một số MỚI bị trùng"*, không phải *"tổng số
    tăng"*.

    Đọc được cả tệp mốc đời cũ (một dòng, một con số): lúc đó không biết tập
    nào được phép, nên lấy tập hiện tại làm mốc và nói rõ đã chuyển đời. Không
    nới lỏng gì — tập hiện tại luôn nằm trong thứ số lượng cũ cho phép.
    """
    try:
        tho = TEP_MOC.read_text(encoding="utf-8").strip()
    except OSError:
        return set(quet())
    dong = [d.strip() for d in tho.splitlines() if d.strip()]
    # ⚠️ Đời mới có DÒNG ĐẦU đánh dấu. Không đoán bằng "một dòng thì là số
    # lượng": một tập chỉ có một số (ví dụ `303`) trông y hệt một số lượng
    # `303`, và đoán sai ở đây làm bánh cóc **nới lỏng im lặng**.
    if dong and dong[0] == DAU_HIEU:
        return {int(d) for d in dong[1:] if d.isdigit()}
    print(f"[moc doi cu: {dong[0] if dong else '?'}] chuyen sang chot TAP HOP — "
          "chay `--accept` de ghi lai.")
    return set(quet())


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

    moi_trung = sorted(set(trung) - moc)
    da_don = sorted(moc - set(trung))

    if a.accept:
        if moi_trung:
            print(f"KHONG ghi moc duoc: {len(moi_trung)} so MOI bi trung "
                  f"{moi_trung}. Doi ten chung truoc.", file=sys.stderr)
            return 1
        TEP_MOC.write_text(DAU_HIEU + "\n"
                           + "".join(f"{s}\n" for s in sorted(trung)),
                           encoding="utf-8")
        print(f"Da ghi moc: {len(trung)} so"
              + (f"; bo {len(da_don)} so da don {da_don}" if da_don else ""))
        return 0

    print(f"So tep test bi trung so: {len(trung)} | moc: {len(moc)} so")
    if da_don:
        print(f"  don duoc {len(da_don)} so: {da_don}"
              "  -> chay `--accept` de ghi lai moc")
    if moi_trung:
        print(f"\nSO MOI BI TRUNG: {moi_trung}")
        for so in moi_trung:
            print(f"  {so}: {', '.join(trung[so])}")
        print("\nDoi ten mot trong cac tep tren. So con trong:", so_trong()[:10])
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
