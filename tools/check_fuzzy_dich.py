r"""
check_fuzzy_dich.py — tìm mục `#, fuzzy` mà Babel đoán SAI.

    python tools\check_fuzzy_dich.py          # liệt kê mục đáng ngờ
    python tools\check_fuzzy_dich.py --dem    # chỉ in số, thoát 1 nếu > 0

## Vì sao có file này

Khi chạy `i18n.py trich`, Babel tự gán bản dịch cũ cho msgid mới nếu chúng "trông
giống nhau", rồi đánh dấu `#, fuzzy`. gettext **bỏ qua** mục fuzzy, nên hôm nay
chúng chỉ hiện tiếng Việt giữa trang tiếng Anh — khó chịu chứ chưa sai nghĩa.

Nguy hiểm nằm ở chỗ khác: **mục fuzzy vẫn mang sẵn bản dịch đoán bừa**. Ai chạy
`msgattrib --clear-fuzzy` hoặc gỡ cờ hàng loạt để "dọn cho sạch" sẽ đẩy nguyên
chúng lên production. Rà 2026-08-23 tìm thấy 47 mục sai, trong đó:

    "Bắt buộc"   ->  "Optional"     một trường BẮT BUỘC ghi thành TUỲ CHỌN
    "đang khỏe"  ->  "Pending"      trạng thái KHOẺ ghi thành ĐANG CHỜ
    "đang tắt"   ->  "Finishing"    trạng thái TẮT ghi thành ĐANG HOÀN TẤT
    "chỉ đọc"    ->  "Topic"
    "Định danh"  ->  "Fast"

Ba cái đầu nằm trong cổng lập trình viên và trang tình trạng hệ thống — tức là
chỗ mà nói sai thì khách tin theo.

## Phép dò

Không thể tự biết bản dịch đúng hay sai, nên chỉ bắt hai dấu hiệu của việc **gán
nhầm sang một msgid khác**:

1. msgid từ 2 từ trở lên mà bản dịch chỉ **một từ** — dấu hiệu điển hình của việc
   Babel lấy nhãn ngắn của mục khác;
2. độ dài lệch quá xa (gấp/kém 3 lần).

Sót thì có, báo nhầm cũng có. Nó không thay người đọc — nó chỉ thu 1.900 mục
xuống còn vài chục để người đọc kịp nhìn.
"""
from __future__ import annotations

import io
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
PO = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"


def _go_ngoac(dong: str) -> str:
    d = dong.strip()
    return d[1:-1] if len(d) >= 2 and d[0] == '"' and d[-1] == '"' else d


def doc_muc(duong: pathlib.Path):
    """Trả (co_fuzzy, tham_chieu, msgid, msgstr) cho từng mục trong .po."""
    khoi, hien = [], []
    for dong in io.open(duong, encoding="utf-8").read().splitlines():
        if dong.strip() == "":
            if hien:
                khoi.append(hien)
                hien = []
        else:
            hien.append(dong)
    if hien:
        khoi.append(hien)

    for k in khoi:
        fuzzy = any(d.startswith("#,") and "fuzzy" in d for d in k)
        ref = next((d[3:].strip() for d in k if d.startswith("#:")), "")
        gid, gstr, che_do = [], [], None
        for d in k:
            if d.startswith("msgid "):
                che_do = "id"
                gid.append(_go_ngoac(d[6:]))
            elif d.startswith("msgstr "):
                che_do = "str"
                gstr.append(_go_ngoac(d[7:]))
            elif d.startswith('"'):
                (gid if che_do == "id" else gstr).append(_go_ngoac(d))
        yield fuzzy, ref, "".join(gid), "".join(gstr)


def dang_ngo(gid: str, gstr: str) -> str:
    """Lý do nghi bản dịch bị gán nhầm, hoặc "" nếu trông hợp lý."""
    if not gid or not gstr:
        return ""
    n_goc, n_dich = len(gid.split()), len(gstr.split())
    if n_goc >= 2 and n_dich == 1:
        return "mot tu thay cho ca cau"
    if n_goc and (n_dich > n_goc * 3 or n_dich * 3 < n_goc):
        return "do dai lech xa"
    return ""


def main() -> int:
    # Doi stdout sang UTF-8 CHI khi chay nhu mot script. Lam viec nay o cap module
    # thi module khong import duoc tu test: pytest thay stdout bi thay giua chung
    # va vo o buoc thu don (`ValueError` trong contextlib).
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)
    if not PO.exists():
        print(f"khong thay {PO}")
        return 1
    muc = [m for m in doc_muc(PO) if m[2]]
    fz = [m for m in muc if m[0]]
    ngo = [(dang_ngo(g, s), r, g, s) for _, r, g, s in fz if dang_ngo(g, s)]

    chi_dem = "--dem" in sys.argv
    print(f"fuzzy: {len(fz)}/{len(muc)} muc · nghi dich sai: {len(ngo)}")
    if not chi_dem:
        for ly_do, ref, gid, gstr in ngo:
            print(f"  [{ly_do}] {ref}")
            print(f"      goc : {gid[:78]}")
            print(f"      dich: {gstr[:78]}")
    if ngo:
        print("\nSua bang cach viet ban dich DUNG roi go dong `#, fuzzy` cua muc do.")
        print("Dung `msgattrib --clear-fuzzy` cho ca tep: no bat nguyen ban doan bua.")
    return 1 if (chi_dem and ngo) else 0


if __name__ == "__main__":
    raise SystemExit(main())
