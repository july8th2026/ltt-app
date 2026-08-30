"""
check_bo_qua.py — banh coc chan BO QUA IM LANG trong bo test.

    py tools/check_bo_qua.py           # kiem, so voi moc
    py tools/check_bo_qua.py --accept  # ghi lai moc (khi da bo bot mot cho bo qua)

VI SAO CO TEP NAY

   `pytest -q` in mot chu `s` cho moi test bi bo qua. Mot chu `s` giua ba nghin
   dau cham la vo hinh, va gate chi giu 4 dong cuoi cua dau ra — nen ngay ca
   `-rs` cung khong toi mat ai.

   Do 25/08/2026: cum VPS chay sach **503 passed, 2 skipped**. Hai cai `s` do la
   `test_293_vps_dung_lai_cong_vao.py`, va chung khong phai hai phep kiem phu:
   chung la hai phep kiem DUY NHAT chot rang kich ban dung lai cong vao con khop
   bo luat nftables dang chay that. Chung bo qua vi `secrets/cong_vao/` khong
   bao gio duoc commit — nghia la tren MOI may lam viec, chung khong bao gio
   chay, va bo luat co the troi bao lau cung duoc.

   Do dung la loai hong te nhat: mot phep kiem TON TAI, nen khong ai viet lai
   no, va no KHONG CHAY, nen no khong canh gi ca.

VI SAO KHONG BAT CHUNG PHAI CHAY

   Phan lon cho bo qua o day la dung: khong co PostgreSQL, khong co ffmpeg,
   khong co bucket R2 vut di, khong phai Windows. Bat chung chay tren may khong
   co dieu kien la doi mot phep kiem im lang lay mot phep kiem bao dong gia.

   Nen tep nay khong ep chay. No **bat moi cho bo qua phai duoc KHAI BAO**: in
   het danh sach moi luot, va bao do khi xuat hien mot cho MOI chua co trong
   moc. Them mot cho bo qua tu nay la mot hanh dong co chu y, hien trong diff.

⭐ Cung khuon `check_so_test.py`: chot TAP HOP chu khong chot SO LUONG. Chot so
   luong thi mot cho bo qua moi van lot neu mot cho cu vua duoc don trong cung
   luot — da xay ra that voi trung so tep test ngay 25/08.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys
import warnings

GOC = pathlib.Path(__file__).resolve().parent.parent
THU_MUC = GOC / "tests"
TEP_MOC = pathlib.Path(__file__).with_name("check_bo_qua.moc")
DAU_HIEU = "# tap-hop-cho-bo-qua"


def _an_toan(value: str) -> str:
    """Console PowerShell 5.1 thuong la CP1252. Ly do bo qua viet tieng Viet,
    va mot cong cu CHET vi in duoc ly do la mot cong cu che mat chinh thu no
    sinh ra de lam hien ra."""
    dich = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return value.encode(dich, errors="backslashreplace").decode(dich)
    except LookupError:
        return value.encode("ascii", errors="backslashreplace").decode("ascii")


def _la_skip(node: ast.AST) -> str:
    """Ten cua loi goi neu no la `skip`/`skipif`, nguoc lai chuoi rong."""
    dich = node.func if isinstance(node, ast.Call) else node
    if isinstance(dich, ast.Attribute) and dich.attr in ("skip", "skipif"):
        return dich.attr
    return ""


def _ly_do(node: ast.AST) -> str:
    """`reason=` khi no la chuoi hang, hoac doi so dau tien cua `pytest.skip`."""
    if not isinstance(node, ast.Call):
        return ""
    for kw in node.keywords:
        if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return ""


def quet() -> dict:
    """{khoa: ly do} cho moi cho co the bo qua mot test.

    Khoa la `<tep>::<ten>` — ten ham test, ten bien module, hoac `pytestmark`.
    Chon ten chu khong chon so dong vi so dong troi moi lan sua tep, va mot moc
    troi theo tung lan sua la mot moc khong ai duy tri.
    """
    ra: dict = {}
    for f in sorted(THU_MUC.glob("*.py")):
        try:
            with warnings.catch_warnings():
                # Chuoi thoat khong hop le trong tep NGUOI KHAC viet la
                # viec cua `check_bien_dich.py`, khong phai viec cua tep
                # nay — va no lam nhieu dung dau ra ma ta muon ai cung doc.
                warnings.simplefilter("ignore", SyntaxWarning)
                cay = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            # 🔴 `check_bien_dich.py` la buoc DAU TIEN cua gate va no bao do cho
            #    tep khong parse duoc. Im lang o day la dung phan cong; im lang
            #    ma khong noi ly do thi khong.
            print(f"  [bo qua, khong doc/parse duoc] {f.name}", file=sys.stderr)
            continue
        for node in ast.walk(cay):
            ten = ""
            cho = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ten = node.name
                cho = list(node.decorator_list)
            elif isinstance(node, ast.Assign):
                dich = node.targets[0] if node.targets else None
                if isinstance(dich, ast.Name):
                    ten, cho = dich.id, [node.value]
            if not ten:
                continue
            for c in cho:
                if _la_skip(c):
                    ra[f"{f.name}::{ten}"] = _ly_do(c)
        # `pytest.skip(...)` goi thang trong than mot ham test.
        for node in ast.walk(cay):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for con in ast.walk(node):
                if isinstance(con, ast.Call) and _la_skip(con) == "skip":
                    ra.setdefault(f"{f.name}::{node.name}", _ly_do(con))
    return ra


def doc_moc(hien_tai: dict) -> set:
    try:
        tho = TEP_MOC.read_text(encoding="utf-8").strip()
    except OSError:
        return set(hien_tai)
    dong = [d.strip() for d in tho.splitlines() if d.strip()]
    if dong and dong[0] == DAU_HIEU:
        return set(dong[1:])
    print(f"[moc la khong doc duoc: {dong[0] if dong else '?'}] lay tap hien tai")
    return set(hien_tai)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chan bo qua im lang trong bo test")
    p.add_argument("--accept", action="store_true", help="ghi lai moc")
    a = p.parse_args(argv)

    cho = quet()
    moc = doc_moc(cho)
    moi = sorted(set(cho) - moc)
    da_don = sorted(moc - set(cho))

    if a.accept:
        # `newline=""` de giu LF. Mac dinh cua Python tren Windows dich \n
        # thanh \r\n, nen moi lan `--accept` doi CA TEP thay vi mot dong — diff
        # 14 dong cho mot thay doi 1 dong lam nguoi doc bo qua thu can nhin.
        TEP_MOC.write_text(DAU_HIEU + "\n"
                           + "".join(f"{k}\n" for k in sorted(cho)),
                           encoding="utf-8", newline="")
        print(f"Da ghi moc: {len(cho)} cho bo qua"
              + (f"; bo {len(da_don)}: {da_don}" if da_don else ""))
        return 0

    # ⭐ In HET moi luot, khong chi in khi do. Muc dich cua tep nay la lam cho
    #    cac cho bo qua NHIN THAY DUOC — mot danh sach chi hien luc hong thi van
    #    de nguoi ta song ca nam ma khong biet minh dang khong do cai gi.
    print(f"Cho co the bo qua test: {len(cho)} | moc: {len(moc)}")
    for khoa in sorted(cho):
        ly_do = cho[khoa]
        print(f"  {khoa}" + (f"  <- {_an_toan(ly_do)}" if ly_do else ""))
    if da_don:
        print(f"\nDa bo {len(da_don)} cho: {da_don}  -> chay `--accept`")
    if moi:
        print(f"\nCHO BO QUA MOI ({len(moi)}):")
        for khoa in moi:
            print(f"  {khoa}"
                  + (f"  <- {_an_toan(cho[khoa])}" if cho[khoa] else ""))
        print("\nMot test bi bo qua la mot test KHONG canh gi ca. Neu dieu kien")
        print("bo qua la co that va khong tranh duoc thi chay `--accept` de khai")
        print("bao no; lan ghi do hien trong diff cho nguoi review thay.")
        print("RESULT: FAIL")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
