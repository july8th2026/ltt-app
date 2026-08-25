"""
check_dich_thieu.py — banh coc chan CHUOI RA TIENG VIET TREN BAN TIENG ANH.

    py tools/check_dich_thieu.py            # kiem, so voi moc
    py tools/check_dich_thieu.py --list     # liet ke tung muc con thieu
    py tools/check_dich_thieu.py --accept   # ha moc (chi khi da dich bot)

VI SAO CO TEP NAY, VA VI SAO NO KHAC `check_i18n.py`

   `check_i18n.py` canh chuoi CHUA DUOC BOC `_()` — tuc chuoi khong bao gio vao
   duoc tep dich. Tep nay canh buoc SAU do: chuoi da vao `messages.po` roi, ma
   `msgstr` van rong. Hai loi khac nhau, va loi thu hai khong co ai canh.

   Do 25/08/2026 tren `locale/en/LC_MESSAGES/messages.po`: 2.352 muc, trong do
   **203 muc `msgstr` rong** va **76 muc `#, fuzzy`**.

⛔ FUZZY DEM NHU RONG, KHONG DEM NHU DA DICH

   `msgfmt` BO QUA moi muc `#, fuzzy` khi bien dich `.mo`. Nghia la mot ban dich
   fuzzy khong bao gio toi mat nguoi dung — no giong het mot `msgstr` rong khi
   chay, chi khac la no TRONG NHU da lam xong khi doc tep `.po`. Do la ly do
   chung nam chung mot moc o day.

⛔ VI SAO KHONG DICH HET 279 MUC NGAY BAY GIO

   Chung nam rai o khu socialbot dong bang, cac app cu, va trang admin — nhung
   cho ban tieng Anh chua ai xem. Dich het la mot buoi lam khong ai kiem lai
   duoc, va no khong sua NGUYEN NHAN: hom sau them mot trang moi la lai thieu.

   Nen tep nay khong dich qua khu — no chan tuong lai. Khu `/api/v1` va khu VPS
   da ve 0% tieng Viet trong ban EN (test_299, test_304, test_305); moc nay giu
   cho phan con lai khong xau di trong luc do.

⭐ Chot TAP HOP chu khong chot SO LUONG. Chot so luong thi mot chuoi MOI chua
   dich van lot neu mot chuoi CU vua duoc dich trong cung luot — dung cai bay da
   lam `check_so_test.py` bao PASS tren mot va cham that ngay 25/08.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from babel.messages import pofile

GOC = pathlib.Path(__file__).resolve().parent.parent
TEP_PO = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
TEP_MOC = pathlib.Path(__file__).with_name("check_dich_thieu.moc")
DAU_HIEU = "# tap-hop-muc-chua-dich"


def _khoa(loai: str, msgid) -> str:
    """`<loai>\t<msgid>` tren MOT dong.

    `msgid` co the la tuple khi muc co dang so nhieu; lay ban so it lam dai
    dien. Xuong dong trong msgid duoc thoat de mot muc luon la mot dong — mot
    moc ma mot phan tu chiem nhieu dong la mot moc khong diff duoc tu te.
    """
    if isinstance(msgid, (tuple, list)):
        msgid = msgid[0] if msgid else ""
    thoat = str(msgid).replace("\\", "\\\\").replace("\n", "\n").replace("\t", "\t")
    return f"{loai}\t{thoat}"


def quet() -> dict:
    """{khoa: vi tri dau tien trong ma nguon}."""
    with TEP_PO.open("rb") as fh:
        catalog = pofile.read_po(fh)
    ra: dict = {}
    for muc in catalog:
        if not muc.id:
            continue                      # dong dau tep (metadata)
        chuoi = muc.string
        if isinstance(chuoi, (tuple, list)):
            rong = not any(chuoi)
        else:
            rong = not chuoi
        loai = "FUZZY" if muc.fuzzy else ("TRONG" if rong else "")
        if not loai:
            continue
        noi = muc.locations[0] if muc.locations else ("?", 0)
        ra[_khoa(loai, muc.id)] = f"{noi[0]}:{noi[1]}"
    return ra


def doc_moc(hien_tai: dict) -> set:
    try:
        tho = TEP_MOC.read_text(encoding="utf-8")
    except OSError:
        return set(hien_tai)
    dong = [d.rstrip("\n") for d in tho.splitlines() if d.strip()]
    if dong and dong[0] == DAU_HIEU:
        return set(dong[1:])
    print(f"[moc la khong doc duoc: {dong[0] if dong else '?'}] lay tap hien tai")
    return set(hien_tai)


def _an_toan(value: str) -> str:
    """Console PowerShell 5.1 thuong la CP1252; msgid la tieng Viet."""
    dich = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return value.encode(dich, errors="backslashreplace").decode(dich)
    except LookupError:
        return value.encode("ascii", errors="backslashreplace").decode("ascii")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chan them chuoi chua dich o ban EN")
    p.add_argument("--list", action="store_true", help="liet ke tung muc")
    p.add_argument("--accept", action="store_true", help="ha moc xuong hien tai")
    a = p.parse_args(argv)

    if not TEP_PO.exists():
        print(f"KHONG THAY {TEP_PO} — khong ket luan duoc.", file=sys.stderr)
        return 1

    thieu = quet()
    moc = doc_moc(thieu)
    moi = sorted(set(thieu) - moc)
    da_dich = sorted(moc - set(thieu))

    trong = sum(1 for k in thieu if k.startswith("TRONG"))
    fuzzy = sum(1 for k in thieu if k.startswith("FUZZY"))

    if a.list:
        for khoa in sorted(thieu):
            print(f"  {_an_toan(khoa)}   [{thieu[khoa]}]")

    if a.accept:
        if moi:
            print(f"KHONG ha moc duoc: {len(moi)} muc MOI chua dich. "
                  "Dich chung truoc — moc chi duoc phep GIAM.", file=sys.stderr)
            for khoa in moi[:10]:
                print(f"  {_an_toan(khoa)}   [{thieu[khoa]}]", file=sys.stderr)
            return 1
        TEP_MOC.write_text(DAU_HIEU + "\n"
                           + "".join(f"{k}\n" for k in sorted(thieu)),
                           encoding="utf-8")
        print(f"Da ghi moc: {len(thieu)} muc ({trong} trong, {fuzzy} fuzzy)"
              + (f"; bo {len(da_dich)} muc da dich" if da_dich else ""))
        return 0

    print(f"Ban EN con thieu: {len(thieu)} muc "
          f"({trong} msgstr rong, {fuzzy} fuzzy) | moc: {len(moc)}")
    if da_dich:
        print(f"  da dich them {len(da_dich)} muc -> chay `--accept` de ha moc")
    if moi:
        print(f"\nMUC MOI CHUA DICH ({len(moi)}):")
        for khoa in moi[:20]:
            print(f"  {_an_toan(khoa)}   [{thieu[khoa]}]")
        if len(moi) > 20:
            print(f"  … con {len(moi) - 20} muc nua, chay `--list` de xem het")
        print("\nDich chung trong locale/en/LC_MESSAGES/messages.po roi chay")
        print("`python tools/i18n.py bien-dich`. Muc `#, fuzzy` thi ra soat ban")
        print("dich roi BO co fuzzy — msgfmt bo qua fuzzy, nen no khong toi ai.")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
