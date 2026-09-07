"""Tien ich cho SCRIPT DO — thu bi mien tru ky luat, va do la cho hong.

    import sys; sys.path.insert(0, "tools")
    from do_nhanh import ra, chu_ky, thay, ghi, tien_trinh

⭐ VI SAO TEP NAY TON TAI. Dem 06/09, mot phien tu ke lai 13 loi minh gay ra
   trong mot buoi: **chin trong muoi ba** nam o CONG CU DUNG DE DO, khong nam o
   thu duoc giao. Ky luat song trong ma san pham va duoc mien tru cho script
   tam — trong khi chinh script tam quyet dinh ta NHIN THAY GI.

   Ba cai bay duoi day deu DA CO ghi chu trong bo nho, va ca ba van can, vi moi
   lan chung can o mot script "chi chay mot lan":

   | bay                            | so lan can trong MOT buoi |
   |--------------------------------|---------------------------|
   | `print` vo vi cp1252           | 4                         |
   | heredoc Bash nuot mot lop `\\`  | 3                         |
   | loc tien trinh khop chinh minh | 1 (thoat ma 15)           |

⛔ Mot luat "hay can than hon" khong sua duoc cai nao trong ba. Mot ham thi co.

⚠️ VA BAY AY KHONG CHI LA BACKSLASH. Do 06/09, lan thu sau trong cung
   mot buoi: mot chu thich co BACKTICK truyen qua cong cu Bash bi shell coi
   la THAY THE LENH. Lan dau moi tu trong backtick BIEN MAT khoi tep —
   `ruff`, `B008`, `Depends()`, `from` — ma khong co loi nao. Lan sau shell chet han
   voi 'unexpected EOF while looking for matching'.

   ⇒ Luat: dung go BAT KY ky tu dac biet cua shell vao mot lenh Bash
     (\\  `  $  ") — ke ca ben trong nhay don, ke ca trong
     heredoc. Soan bang cong cu Write ra mot tep, roi CHAY tep ay.
"""
from __future__ import annotations

import ast
import io
import os
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent


def ra(*phan, **kw) -> None:
    """`print` khong bao gio vo vi bang ma console.

    🔴 Do 06/09: bon lan mot script do dung giua chung voi

        UnicodeEncodeError: 'charmap' codec can't encode character ...

    Va lan te nhat la khi no vo o dong IN KET QUA — viec da xong, ma ma thoat
    la 1. Doc ma thoat luc do se ket luan "viec hong".

    ⛔ Dung `reconfigure` tren luong DANG CO, khong boc mot `TextIOWrapper` MOI
       quanh `sys.stdout.buffer`: ban goc bi thu gom rac se dong buffer that va
       lam vo pytest. Kho nay da tra gia mot lan cho dung loi do.
    """
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    print(*phan, **kw)


def chu_ky(tep: str, ten: str) -> str:
    """In CHU KY THAT cua mot ham, doc tu AST. Tra chuoi de doi chieu.

    🔴 Bon loi trong mot buoi deu cung mot hinh dang: goi mot ham theo TRI NHO
       thay vi theo CHU KY. Vi du that:

           resources.create(kind="style")     -> app tra loi: chi nhan
                                                 character/background/prop/...
           add_variant(prompt_text=...)       -> no doi `storage_key`, vi bien
                                                 the la MOT ANH

    ⭐ Mot lenh doc chu ky re hon mot vong sua. Ham nay ton tai de cai re hon
       khong con ton cong hon.
    """
    duong = Path(tep) if Path(tep).is_absolute() else GOC / tep
    cay = ast.parse(duong.read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ten:
            dong = duong.read_text(encoding="utf-8").split(chr(10))
            khoi = dong[n.lineno - 1:(n.body[0].lineno - 1)]
            return chr(10).join(khoi).strip()
    raise LookupError(f"khong thay `{ten}` trong {tep}")


def thay(tep: str, cu: str, moi: str, *, so_lan: int = 1) -> None:
    """Thay mot doan trong tep NGUON, voi bon rao chan cung mot luc.

    Bon rao nay deu la loi da xay ra that, khong phai phong xa:

      1. `cu` phai khop DUNG `so_lan`. Neu khong -> `str.replace` im lang khong
         thay gi, va ta bao "da sua" trong khi khong sua gi.
      2. `ast.parse` sau khi thay (voi tep `.py`). Mot neo dat trong khoi `if`
         da tung sinh `IndentationError` — bat truoc khi ghi thi mien phi.
      3. Giu nguyen KIEU KET DONG cua tep. `ltt.css` la CRLF, `NHAT_KY.md` la
         LF; ghi nham kieu lam ca tep thanh mot diff khong ai doc duoc.
      4. Doc lai bang BYTE sau khi ghi. `read_text` DICH NGUOC `\\r\\n` thanh
         `\\n`, nen no khong the kiem duoc phep ghi.
    """
    duong = Path(tep) if Path(tep).is_absolute() else GOC / tep
    goc = duong.read_bytes()
    crlf = goc.count(b"\r\n") > 0 and goc.count(b"\n") == goc.count(b"\r\n")
    s = goc.decode("utf-8").replace("\r\n", "\n")

    thay_ra = s.count(cu)
    if thay_ra != so_lan:
        raise AssertionError(
            f"neo khop {thay_ra} lan, mong doi {so_lan} - "
            "`str.replace` se im lang khong thay gi")
    s = s.replace(cu, moi, so_lan)

    if duong.suffix == ".py":
        ast.parse(s)                     # bat loi cu phap TRUOC khi cham tep

    data = s.encode("utf-8")
    if crlf:
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    duong.write_bytes(data)
    if duong.read_bytes() != data:
        raise AssertionError("tep tren dia khac thu vua ghi")


def ghi(tep: str, noi_dung: str) -> None:
    """Ghi ca tep, giu kieu ket dong cua ban cu neu no da ton tai."""
    duong = Path(tep) if Path(tep).is_absolute() else GOC / tep
    crlf = False
    if duong.exists():
        cu = duong.read_bytes()
        crlf = cu.count(b"\r\n") > 0 and cu.count(b"\n") == cu.count(b"\r\n")
    data = noi_dung.replace("\r\n", "\n").encode("utf-8")
    if crlf:
        data = data.replace(b"\n", b"\r\n")
    duong.write_bytes(data)
    if duong.read_bytes() != data:
        raise AssertionError("tep tren dia khac thu vua ghi")


def _kich_ban(cl: list) -> str:
    """Ten thu dang duoc CHAY, tu `cmdline`. Rong neu khong xac dinh duoc.

    ⛔ KHONG tra ve ca dong lenh. Do la khac biet giua "tien trinh nay LA gate"
       va "tien trinh nay co NHAC chu gate o dau do trong tham so".

        python tools/gate.py --quick   -> "gate.py"
        python -m pytest -q tests/...  -> "pytest"
        python -c "... 'gate.py' ..."  -> ""        <- khong con thoa
    """
    if len(cl) < 2:
        return ""
    if cl[1] == "-m":
        return cl[2] if len(cl) > 2 else ""
    if cl[1].startswith("-"):
        return ""
    return os.path.basename(cl[1])


def tien_trinh(chua: str = "", *, ten_tien_trinh: str = "python.exe") -> list:
    """Tien trinh khop `chua`, DA LOAI TRU chinh minh va toan bo chuoi cha.

    🔴 Do 06/09, hai phien cung dinh mot ca: mot bo loc theo `cmdline` khop vao
       CHINH CONG CU DO, vi vo `bash -c` mang ca ma nguon duoc truyen cho no.
       Mot phien dung bo loc ay de `kill` va lenh giet di NGUOC LEN cay cha cua
       chinh no — script thoat ma 15.

    ⛔ Loc theo `cwd` KHONG cuu duoc ca nay: shell cua nguoi dang hoi cung co
       `cwd` dung bang cay ay. Dieu kien phai la thu tien trinh do KHONG THE TU
       THOA — tuc loai `os.getpid()` VA `parents()`.

    ⚠️ VA `parents()` VAN CHUA DU — lo thu tu cua cung mot ho bay, do 06/09 sau
       khi phien LTTCHAT V3 chi ra:

           loc ca dong lenh   4 tien trinh  (3 la `bash.exe` ANH EM)
           loc kich ban       1 tien trinh

       Ba cai thua la shell cua nhung lenh nen TRUOC DO trong cung phien. Chung
       khong phai to tien, nen `parents()` khong cham toi. Va rao
       `ten_tien_trinh="python.exe"` chi thu hep chu khong dong: mot script
       PYTHON chi NHAC chuoi ay trong ma nguon van bi dem — da dung mot tien
       trinh moi de xac nhan, no bi dem that.

    ⇒ Nen phep khop khong hoi CA DONG LENH nua, ma hoi **kich ban dang chay**:
      `python tools/gate.py` -> "gate.py";  `python -m pytest` -> "pytest".
      Mot tien trinh chi NHAC ten thi khong thoa, vi ten ay nam o argv[2+].
    """
    import psutil

    me = psutil.Process()
    try:
        bo_qua = {me.pid} | {t.pid for t in me.parents()}
    except psutil.Error:
        bo_qua = {os.getpid()}

    ra_ds = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["pid"] in bo_qua:
                continue
            if ten_tien_trinh and (p.info["name"] or "").lower() != ten_tien_trinh:
                continue
            if chua and chua not in _kich_ban(p.info["cmdline"] or []):
                continue
            ra_ds.append(p)
        except psutil.Error:
            continue
    return ra_ds


def main() -> int:
    """`python tools/do_nhanh.py chu-ky <tep> <ten_ham>` — doc chu ky that."""
    if len(sys.argv) >= 4 and sys.argv[1] == "chu-ky":
        ra(chu_ky(sys.argv[2], sys.argv[3]))
        return 0
    ra(__doc__ or "")
    ra("  python tools/do_nhanh.py chu-ky <tep> <ten_ham>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
