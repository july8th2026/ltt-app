r"""i18n_merge_driver.py — cham dut xung dot git tren locale/**/*.mo (H25).

    python tools\i18n_merge_driver.py cai-dat     # cai driver (MOT LAN, xem duoi)
    python tools\i18n_merge_driver.py driver %O %A %B %P   # git tu goi, dung tay ich gi
    python tools\i18n_merge_driver.py touch-fresh           # git hook tu goi

## Van de

`.mo` la hien vat NHI PHAN dung san tu `.po` (ly do commit no — doc
`tools/i18n.py` dong 5-13). Git khong 3-way merge duoc nhi phan, nen MOI lan
hai phien them chuoi dich khac nhau vao `.po`, `.mo` xung dot — du ban than
`.po` (van ban) gop sach. Nguoi phai giai tay bang `i18n.py bien-dich` moi
lan (do thuc te 25/09: bon lan trong mot buoi).

## Giai phap

Mot git "merge driver" (`.gitattributes`: `locale/**/*.mo merge=ltt_mo`) —
KHONG chon `ours`/`theirs` (ca hai deu sai, `.mo` la dan xuat cua `.po`), ma
SINH LAI `.mo` tu ban gop cua `.po`:

  1. Tim sha "ours" (= HEAD, luon co san) va sha "theirs".
  2. `merge-base(ours, theirs)` -> ba ban `.po` (base/ours/theirs) qua
     `git show <sha>:<duong>`.
  3. `git merge-file` gop ba ban do y het thuat toan git dung cho `.po` that
     trong cay lam viec — nen ket qua giong ket qua `.po` that se co.
  4. Bien dich ban gop thanh `.mo` (babel, giong het `i18n.py bien-dich`),
     ghi vao `%A` (git doc ket qua tu day).

Neu buoc nao khong chac (that su xung dot trong `.po`, thieu revision, khong
phai merge thuong) -> THOAT KHAC 0. Git roi ve xung dot nhi phan nhu HIEN
NAY — khong doan bay, khong lam sai.

🔴 **`MERGE_HEAD` CHUA TON TAI luc driver chay** (do thuc nghiem 25/09 — git
chi ghi `MERGE_HEAD` SAU KHI moi duong da duoc gop). `git ls-files -u` cung
rong luc nay. Cai DUY NHAT co san la `HEAD` (chua doi) va mot bien moi truong
`GITHEAD_<sha40>=<nhan>` git dat cho moi phia truoc khi goi driver (von danh
cho mergetool hien nhan). `ours` doc tu `HEAD`; `theirs` doc tu ten bien do —
neu KHONG dung 1 ung vien (0 hoac >1), coi la khong-phai-merge-thuong va thoat
khac 0.

## Cai dat — vi sao MOT LAN la du cho CA repo (không phai tung worktree)

Repo nay bat `extensions.worktreeConfig = true`, nhung do CHI mo kha nang
dung `git config --worktree` — no KHONG doi hanh vi MAC DINH cua `git config`.
Lenh `git config <key> <value>` (khong co `--worktree`) van ghi vao file
CHUNG `<git-common-dir>/config` — file DUY NHAT ma MOI worktree (chinh lan
lien ket) cung tham chieu. Da do thuc nghiem (kho scratch rieng, 2 worktree,
extensions.worktreeConfig=true giong het repo nay): cai tu MOT worktree,
worktree KIA thay ngay, khong can chay lai gi ca. `core.hooksPath` nam trong
CUNG file do nen chung dung co che.

⇒ `cai-dat` chi can chay MOT LAN, TU BAT KY cay nao (chinh hay lien ket).
Khong can moc vao `tools/cay_rieng.py::_tao()` — da kiem, KHONG phai cho noi
dung (dung sai gia dinh ban dau cua viec nay).

Git CO Y khong cho commit `merge.*.driver` (chay lenh tuy y luc checkout la
lo hong an toan chuoi cung ung) — day la GIOI HAN CUA GIT, khong phai thieu
sot o day. `.gitattributes` + docstring nay la loi nhac; `cai-dat` la buoc
thu cong MOT LAN (tuong tu bat cu du an nao dung merge driver cho tep sinh
san, vd Xcode .pbxproj, Jupyter .ipynb qua nbdime).

## Vi sao co `touch-fresh` / `tools/githooks/post-merge`

`i18n.py thieu` coi `.mo` cu hon `.po` la loi (ban dich moi khong toi nguoi
dung ma khong bao loi). Do thuc nghiem 25/09: SAU mot merge tu dong (driver
o tren da chay dung), git checkout `.mo` va `.po` GAN NHU cung luc — nhung
thu tu (`.mo` truoc hay sau `.po`) KHONG on dinh, lech nhau ~1 ms, nen `.mo`
CO THE ra doi truoc `.po` mot chut du NOI DUNG da dung. Do 10 lan chay that:
khong hook -> 3/6 lan `.mo` "cu hon"; co hook -> 0/11 lan. Sua bang mot git
hook `post-merge` (tracked o `tools/githooks/`, `core.hooksPath` tro toi no
— cung dung chung file config nen cung khong can cai tung worktree), chay
SAU KHI checkout xong, dam `os.utime()` moi `.mo` len sau `.po` cua no.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          cwd=str(GOC))


def _bien_dich_po_bytes(po_text: str) -> bytes | None:
    """Bien dich noi dung `.po` (chuoi) thanh bytes `.mo`, giong `i18n.py
    bien-dich` (cung babel, cung `read_po`/`write_mo`)."""
    from babel.messages.pofile import read_po
    from babel.messages.mofile import write_mo
    import io
    try:
        cat = read_po(io.BytesIO(po_text.encode("utf-8")))
    except Exception as loi:
        sys.stderr.write(f"i18n_merge_driver: .po gop khong doc duoc: {loi}\n")
        return None
    buf = io.BytesIO()
    write_mo(buf, cat)
    return buf.getvalue()


def _theirs_sha(ours: str) -> str | None:
    """Doc sha 'theirs' tu bien moi truong `GITHEAD_<sha40>` git dat truoc
    khi goi driver (xem docstring — `MERGE_HEAD` chua ton tai luc nay)."""
    ung_vien = []
    for k in os.environ:
        m = re.fullmatch(r"GITHEAD_([0-9A-Fa-f]{40})", k)
        if m and m.group(1).lower() != ours.lower():
            ung_vien.append(m.group(1))
    if len(ung_vien) != 1:
        sys.stderr.write(
            f"i18n_merge_driver: can dung 1 GITHEAD_* cho 'theirs', "
            f"thay {len(ung_vien)} — khong phai merge thuong, bo qua\n")
        return None
    return ung_vien[0]


def driver(argv: list[str]) -> int:
    """%O %A %B %P — git goi khi `.mo` xung dot (xem .gitattributes)."""
    if len(argv) != 4:
        sys.stderr.write("i18n_merge_driver: can du %O %A %B %P\n")
        return 1
    _o, a_path, _b, p_path = argv
    mo_path = Path(p_path)
    po_path = mo_path.with_suffix(".po")

    ours_r = _git("rev-parse", "HEAD")
    if ours_r.returncode != 0:
        sys.stderr.write("i18n_merge_driver: khong doc duoc HEAD, bo qua\n")
        return 1
    ours = ours_r.stdout.strip()

    theirs = _theirs_sha(ours)
    if theirs is None:
        return 1

    base_r = _git("merge-base", ours, theirs)
    if base_r.returncode != 0 or not base_r.stdout.strip():
        sys.stderr.write("i18n_merge_driver: khong tim duoc merge-base, bo qua\n")
        return 1
    base = base_r.stdout.strip()

    with tempfile.TemporaryDirectory(prefix="ltt_i18n_merge_") as td_s:
        td = Path(td_s)
        duong_tam = {}
        for nhan, rev in (("base", base), ("ours", ours), ("theirs", theirs)):
            r = _git("show", f"{rev}:{po_path.as_posix()}")
            if r.returncode != 0:
                sys.stderr.write(
                    f"i18n_merge_driver: {po_path.as_posix()} khong co o "
                    f"{nhan} ({rev[:8]}), bo qua\n")
                return 1
            dich = td / f"{nhan}.po"
            dich.write_bytes(r.stdout.encode("utf-8"))
            duong_tam[nhan] = dich

        gop = subprocess.run(
            ["git", "merge-file", "-p", str(duong_tam["ours"]),
             str(duong_tam["base"]), str(duong_tam["theirs"])],
            capture_output=True, text=True)
        if gop.returncode != 0:
            # `.po` THAT SU xung dot (hai phien sua cung mot cho). Khong
            # doan — de git bao xung dot nhi phan nhu cu tren CA HAI tep.
            sys.stderr.write(
                "i18n_merge_driver: .po that su xung dot, bo qua "
                "(giai bang tay nhu truoc)\n")
            return 1

        mo_bytes = _bien_dich_po_bytes(gop.stdout)
        if mo_bytes is None:
            return 1

        Path(a_path).write_bytes(mo_bytes)

    sys.stderr.write(
        f"i18n_merge_driver: da sinh lai {mo_path.as_posix()} tu ban gop "
        f".po (ours={ours[:8]} theirs={theirs[:8]} base={base[:8]})\n")
    return 0


def touch_fresh() -> int:
    """`post-merge` hook goi ham nay. Dam `.mo` khong "cu hon" `.po` ve
    mtime sau mot merge (xem docstring — checkout khong on dinh thu tu)."""
    import time
    now = time.time()
    locale_dir = GOC / "locale"
    if not locale_dir.is_dir():
        return 0
    for mo in locale_dir.glob("*/LC_MESSAGES/*.mo"):
        po = mo.with_suffix(".po")
        if po.exists():
            os.utime(mo, (now, now))
    return 0


def cai_dat() -> int:
    """Cai driver + hook — MOT LAN cho CA repo (xem docstring). Luy dang:
    chay lai khong sao, ghi de gia tri cu."""
    buoc = [
        ("merge.ltt_mo.name", "sinh lai .mo tu ban gop .po (tools/i18n_merge_driver.py)"),
        ("merge.ltt_mo.driver", "python tools/i18n_merge_driver.py driver %O %A %B %P"),
        ("core.hooksPath", "tools/githooks"),
    ]
    for khoa, gia_tri in buoc:
        r = subprocess.run(["git", "config", "--local", khoa, gia_tri],
                           cwd=str(GOC))
        if r.returncode != 0:
            print(f"LOI: khong ghi duoc `git config {khoa}`.")
            return 1
        print(f"  da cai: {khoa} = {gia_tri}")
    print("\nXong. Dung chung .git/config nen CA repo (moi worktree) da co "
          "hieu luc ngay — khong can chay lai o cay khac.")
    print("Kiem tra: git config --get merge.ltt_mo.driver")
    return 0


def main() -> int:
    lenh = sys.argv[1] if len(sys.argv) > 1 else ""
    if lenh == "driver":
        return driver(sys.argv[2:])
    if lenh == "touch-fresh":
        return touch_fresh()
    if lenh == "cai-dat":
        return cai_dat()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
