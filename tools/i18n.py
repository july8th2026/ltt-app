r"""
i18n.py — trích chuỗi, cập nhật bản dịch, biên dịch (H24).

    python tools\i18n.py trich      # quét mã → locale/messages.pot → cập nhật .po
    python tools\i18n.py bien-dich  # .po → .mo (bản chạy đọc .mo)
    python tools\i18n.py thieu      # liệt kê chuỗi chưa dịch, thoát 1 nếu còn

**Babel chỉ cần lúc phát triển.** Bản chạy đọc `.mo` bằng `gettext` của thư viện
chuẩn Python, nên máy chủ không cần cài thêm gì — chỉ cần có sẵn file `.mo`.

Vì vậy `.mo` được commit vào git như một hiện vật dựng sẵn. Đổi lại phải canh
chuyện `.po` và `.mo` lệch nhau: lệnh `thieu` (nằm trong gate) kiểm cả điều đó,
vì `.mo` cũ hơn `.po` nghĩa là bản dịch mới không tới người dùng mà **không có
lỗi nào báo**.
"""
from __future__ import annotations

import io
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
LOCALE = GOC / "locale"
POT = LOCALE / "messages.pot"
NGON_NGU = ("en",)          # tiếng Việt là msgid, không cần catalog


# Console Windows mac dinh cp1252 — in tieng Viet ra la vo. Ep UTF-8 cho stdout,
# neu khong thi `thieu` chet giua chung dung luc no dang liet ke chuoi can dich.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)


def _chay(*lenh: str) -> int:
    return subprocess.run([sys.executable, "-m", "babel.messages.frontend", *lenh],
                          cwd=str(GOC)).returncode


def trich() -> int:
    LOCALE.mkdir(parents=True, exist_ok=True)
    rc = _chay("extract", "-F", "babel.cfg", "--no-wrap",
               "--sort-output", "--omit-header",
               "-o", str(POT), ".")
    if rc:
        return rc
    for lang in NGON_NGU:
        po = LOCALE / lang / "LC_MESSAGES" / "messages.po"
        if po.exists():
            rc = _chay("update", "-i", str(POT), "-d", str(LOCALE),
                       "-l", lang, "--no-wrap", "--omit-header")
        else:
            po.parent.mkdir(parents=True, exist_ok=True)
            # `init` khong nhan `--omit-header` (khac `extract`/`update`).
            rc = _chay("init", "-i", str(POT), "-d", str(LOCALE),
                       "-l", lang, "--no-wrap")
        if rc:
            return rc
    return 0


def bien_dich() -> int:
    for lang in NGON_NGU:
        rc = _chay("compile", "-d", str(LOCALE), "-l", lang)
        if rc:
            return rc
    return 0


def _doc_po(po: pathlib.Path):
    from babel.messages.pofile import read_po
    with po.open("rb") as f:
        return read_po(f)


def thieu() -> int:
    """Liệt kê chuỗi chưa dịch. Thoát khác 0 nếu còn thiếu hoặc .mo lỗi thời."""
    loi = 0
    for lang in NGON_NGU:
        po = LOCALE / lang / "LC_MESSAGES" / "messages.po"
        mo = po.with_suffix(".mo")
        if not po.exists():
            print(f"  [{lang}] CHUA co {po.relative_to(GOC)} — chay `trich` truoc")
            loi = 1
            continue
        cat = _doc_po(po)
        chua = [m for m in cat if m.id and not m.string]
        mo_hoi = [m for m in cat if m.fuzzy and m.id]
        print(f"  [{lang}] tong {len([m for m in cat if m.id])} · "
              f"chua dich {len(chua)} · can xem lai {len(mo_hoi)}")
        for m in chua[:25]:
            s = m.id if isinstance(m.id, str) else m.id[0]
            print(f"      - {s[:80]}")
        if len(chua) > 25:
            print(f"      ... va {len(chua)-25} chuoi nua")
        if chua or mo_hoi:
            loi = 1
        if not mo.exists():
            print(f"  [{lang}] THIEU {mo.name} — chay `bien-dich`")
            loi = 1
        elif mo.stat().st_mtime < po.stat().st_mtime:
            # Khong bao loi luc chay, nen phai bat o day: ban dich moi nam trong
            # .po ma nguoi dung van thay ban cu.
            print(f"  [{lang}] {mo.name} CU HON {po.name} — chay `bien-dich`")
            loi = 1
    return loi


def main() -> int:
    lenh = sys.argv[1] if len(sys.argv) > 1 else ""
    if lenh == "trich":
        return trich()
    if lenh in ("bien-dich", "biendich"):
        return bien_dich()
    if lenh == "thieu":
        return thieu()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
