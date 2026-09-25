"""
H25 — git merge driver cho `locale/**/*.mo` (`tools/i18n_merge_driver.py`).

Đo thật 25/09: `locale/en/LC_MESSAGES/messages.mo` xung đột BỐN lần trong một
buổi — mỗi lần một làn thêm chuỗi dịch khác nhau vào `.po`. `.mo` là nhị phân
dựng sẵn từ `.po` (lý do commit: xem `tools/i18n.py` dòng 5-13) nên git không
3-way merge được nó, dù bản thân `.po` (văn bản) gộp sạch.

Test này dựng một kho git RIÊNG, tạm, trong `tmp_path` — không đụng `.git`
của cây đang chạy test. Đây là phép kiểm DUY NHẤT chứng minh được cơ chế:
chạy `cai-dat` xong rồi `git merge` thật, không chỉ kiểm driver có được gọi.

Hai bài:
  1. Có cài driver -> hai làn thêm chuỗi KHÁC vị trí gộp SẠCH, `.mo` chứa cả
     hai chuỗi, và `.mo` không "cũ hơn" `.po` (điều kiện `i18n.py thieu` xét).
  2. ĐỐI CHỨNG — không chạy `cai-dat` -> xung đột y như trước khi có driver
     (không tệ hơn). Thiếu bài này thì không chứng minh được driver là thứ
     tạo ra khác biệt ở bài 1.
"""
from __future__ import annotations

import gettext
import shutil
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
DRIVER = GOC / "tools" / "i18n_merge_driver.py"
HOOK = GOC / "tools" / "githooks" / "post-merge"

PO_GOC = (
    'msgid ""\n'
    'msgstr ""\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    '\n'
    'msgid "hello"\n'
    'msgstr "hello-en"\n'
    '\n'
    'msgid "bye"\n'
    'msgstr "bye-en"\n'
    '\n'
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd),
                          capture_output=True, text=True)


def _bien_dich(po: Path, mo: Path) -> None:
    """Y het `tools/i18n.py bien-dich` (cung babel), nhung cho MOT tep."""
    from babel.messages.pofile import read_po
    from babel.messages.mofile import write_mo
    with po.open("rb") as f:
        cat = read_po(f)
    with mo.open("wb") as f:
        write_mo(f, cat)


def _lap_kho(goc: Path, ten: str) -> Path:
    kho = goc / ten
    (kho / "locale" / "en" / "LC_MESSAGES").mkdir(parents=True)
    (kho / "tools" / "githooks").mkdir(parents=True)
    shutil.copy2(DRIVER, kho / "tools" / "i18n_merge_driver.py")
    shutil.copy2(HOOK, kho / "tools" / "githooks" / "post-merge")
    (kho / ".gitattributes").write_text(
        "locale/**/*.mo merge=ltt_mo\n", encoding="utf-8", newline="\n")

    po = kho / "locale/en/LC_MESSAGES/messages.po"
    po.write_text(PO_GOC, encoding="utf-8", newline="\n")
    _bien_dich(po, po.with_suffix(".mo"))

    assert _git("init", "-q", cwd=kho).returncode == 0
    _git("config", "user.name", "test", cwd=kho)
    _git("config", "user.email", "test@example.com", cwd=kho)
    # KHONG de autocrlf bien "\n" thanh "\r\n" -- lech dong endings lam
    # `git merge-file` (va git noi chung) thay CA TEP doi, khong chi dong
    # thuc su them.
    _git("config", "core.autocrlf", "false", cwd=kho)
    _git("add", "-A", cwd=kho)
    assert _git("commit", "-q", "-m", "base", cwd=kho).returncode == 0
    _git("branch", "-M", "master", cwd=kho)
    return kho


def _them_chuoi(kho: Path, nhanh: str, msgid_moi: str, sau_marker: str) -> None:
    """Tao nhanh `nhanh` tu `master`, chen `msgid_moi` NGAY SAU `sau_marker`
    trong .po (vi tri khac nhau giua hai lan goi -> .po khong xung dot,
    chi .mo nhi phan xung dot -- dung kich ban do thuc te 25/09)."""
    assert _git("checkout", "-q", "-b", nhanh, "master", cwd=kho).returncode == 0
    po = kho / "locale/en/LC_MESSAGES/messages.po"
    txt = po.read_text(encoding="utf-8")
    assert sau_marker in txt
    txt = txt.replace(
        sau_marker,
        sau_marker + f'msgid "{msgid_moi}"\nmsgstr "{msgid_moi}-en"\n\n')
    po.write_text(txt, encoding="utf-8", newline="\n")
    _bien_dich(po, po.with_suffix(".mo"))
    _git("add", "-A", cwd=kho)
    assert _git("commit", "-q", "-m", f"them {msgid_moi}", cwd=kho).returncode == 0


def test_hai_lan_them_chuoi_khac_nhau_gop_sach_khi_da_cai_driver(tmp_path):
    kho = _lap_kho(tmp_path, "kho1")
    _them_chuoi(kho, "lan-mot", "one", 'msgid "hello"\nmsgstr "hello-en"\n\n')
    _them_chuoi(kho, "lan-hai", "two", 'msgid "bye"\nmsgstr "bye-en"\n\n')

    cai = subprocess.run([sys.executable, "tools/i18n_merge_driver.py", "cai-dat"],
                         cwd=str(kho), capture_output=True, text=True)
    assert cai.returncode == 0, cai.stdout + cai.stderr

    _git("checkout", "-q", "lan-mot", cwd=kho)
    m = _git("merge", "lan-hai", "--no-edit", cwd=kho)
    dau_ra = m.stdout + m.stderr
    assert m.returncode == 0, "phai gop SACH, khong xung dot:\n" + dau_ra
    assert "CONFLICT" not in dau_ra, dau_ra
    assert "da sinh lai" in dau_ra, (
        "driver phai thuc su chay (khong phai gop tinh co khong dung driver):\n"
        + dau_ra)

    po = kho / "locale/en/LC_MESSAGES/messages.po"
    mo = kho / "locale/en/LC_MESSAGES/messages.mo"
    t = gettext.GNUTranslations(open(mo, "rb"))
    assert t.gettext("hello") == "hello-en"
    assert t.gettext("bye") == "bye-en"
    assert t.gettext("one") == "one-en", ".mo thieu chuoi cua lan-mot"
    assert t.gettext("two") == "two-en", ".mo thieu chuoi cua lan-hai"

    # Dieu kien `tools/i18n.py::thieu()` xet: .mo KHONG duoc cu hon .po.
    assert mo.stat().st_mtime >= po.stat().st_mtime, (
        "hook post-merge chua cham .mo tuoi hon .po -- `i18n.py thieu` se "
        "bao nham .mo loi thoi")


def test_doi_chung_chua_cai_driver_van_xung_dot_nhu_truoc(tmp_path):
    """KHONG chay `cai-dat`. Phai xung dot y het truoc khi co driver -- day
    la bang chung driver (chu khong phai thu gi khac) tao ra khac biet o
    bai tren, va la duong lui an toan cho worktree chua cai."""
    kho = _lap_kho(tmp_path, "kho2")
    _them_chuoi(kho, "lan-mot", "one", 'msgid "hello"\nmsgstr "hello-en"\n\n')
    _them_chuoi(kho, "lan-hai", "two", 'msgid "bye"\nmsgstr "bye-en"\n\n')

    _git("checkout", "-q", "lan-mot", cwd=kho)
    m = _git("merge", "lan-hai", "--no-edit", cwd=kho)
    dau_ra = m.stdout + m.stderr
    assert m.returncode != 0, "chua cai driver -- phai xung dot nhu cu"
    assert "CONFLICT" in dau_ra

    trang_thai = _git("status", "--porcelain", cwd=kho).stdout
    dong = trang_thai.splitlines()
    mo_xung_dot = [d for d in dong if d.startswith("UU") and d.endswith(".mo")]
    po_xung_dot = [d for d in dong if d.startswith("UU") and d.endswith(".po")]
    assert mo_xung_dot, f"phai co .mo o trang thai UU:\n{trang_thai}"
    assert not po_xung_dot, (
        f".po (van ban) phai tu gop sach -- chi .mo (nhi phan) xung dot:\n"
        f"{trang_thai}")
