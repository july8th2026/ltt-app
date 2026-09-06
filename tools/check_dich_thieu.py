"""
check_dich_thieu.py — banh coc chan CHUOI RA TIENG VIET TREN BAN TIENG ANH.

    py tools/check_dich_thieu.py            # kiem, so voi moc
    py tools/check_dich_thieu.py --list     # liet ke tung muc con thieu
    py tools/check_dich_thieu.py --accept   # ha moc (chi khi da dich bot)

BA LOP, VA MOT CHUOI CO THE HONG O BAT KY LOP NAO

   Mot chuoi phai qua BA cua moi toi duoc mat nguoi doc ban tieng Anh:

     1. duoc BOC `_()`          -> `check_i18n.py` canh cua nay
     2. co MAT trong catalog    -> loai `VANG` o tep nay
     3. co `msgstr` khong rong  -> loai `TRONG` / `FUZZY` o tep nay

   Do 25/08/2026: **203 muc `msgstr` rong** va **76 muc `#, fuzzy`** tren 2.352.

🔴 CUA THU HAI KHONG AI CANH, VA NO DA LOT THAT

   Ngay 26/08, hai chuoi o chan trang dung chung — `Gia API` va `Huong dan API` —
   ra **tieng Viet tren moi trang cua ban EN**. Chung da boc `_()` tu tuoi,
   nen `check_i18n` bao dep. Chung **khong co mot dong nao** trong `.po`, nen
   phep dem muc rong cung khong thay. Chung chi hong o cho khong ai nhin.

   Nguyen nhan: `.po` **troi lai phia sau ma nguon**. Ai do them mot chuoi da
   boc `_()` va khong chay `i18n.py trich` — va khong the trach ho, vi
   `trich` co gia rieng cua no (xem duoi).

   Do luc them phep kiem nay: **67 chuoi** dang o trang thai do.

⛔ FUZZY DEM NHU RONG, KHONG DEM NHU DA DICH

   `msgfmt` BO QUA moi muc `#, fuzzy` khi bien dich `.mo`. Nghia la mot ban dich
   fuzzy khong bao gio toi mat nguoi dung — no giong het mot `msgstr` rong khi
   chay, chi khac la no TRONG NHU da lam xong khi doc tep `.po`. Do la ly do
   chung nam chung mot moc o day.

⛔ VI SAO KHONG DICH HET 279 MUC NGAY BAY GIO

   Chung nam rai o cac app cu va trang admin — nhung
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
#: ⭐ SEAM CHO TEST — va do la SUA LOI, khong phai tien nghi.
#:
#:    `test_306` phai chay CHINH cong nay (mot cong chi kiem qua thu vien la mot
#:    cong khong ai kiem day dien). De lam vay, ba phep kiem cua no ghi de
#:    `messages.po` THAT roi tra ve trong `finally`. Cho do da vá **ba lan**:
#:      · 26/08 — `write_text` doi LF thanh CRLF, "khoi phuc" khac ban goc
#:                10.465 dong, va `git status` cua bat ky ai chay pytest bong
#:                co mot tep .po sua doi khong hieu tu dau;
#:      · luot sau — phai tra lai ca `st_mtime` (`os.utime`), vi dau van tay cua
#:                gate doc mtime nen mot lan ghi-lai-y-het van lam no keu
#:                "CAY DA DOI TRONG LUC CHAY";
#:      · 30/08 — mot luot gate bi cat ngang de tep o lai **ban**, va nguoi don
#:                phai chon giua "khoi phuc" va "giu cong nguoi khac dang lam
#:                do trong cung tep do". Lan do mat 78 ban dich cua mot phien
#:                khac.
#:
#: ⛔ Ba lan vá deu la vá TRIEU CHUNG. Goc la: **test khong duoc ghi vao tep
#:    that**. Tro bien nay sang mot ban sao thi ca ba trieu chung bien mat cung
#:    luc, va mot tien trinh bi giet giua chung khong de lai gi.
#:
#: ⛔ Bien nay CHI de test dung. Ma chay that khong bao gio dat no.
_PO_THU = __import__("os").environ.get("LTT_PO_FILE")
TEP_PO = (pathlib.Path(_PO_THU) if _PO_THU
          else GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po")

#: ⛔ CUNG MOT BAI voi `LTT_PO_FILE` o tren, va no da du dieu kien de dinh HAI
#:    lan trong mot phien (06/09):
#:
#:      tien trinh BI GIET  -> `finally` khong chay, `.moc` o lai ban trong cay
#:      HAI tien trinh      -> worker A tiem vao `.moc`, worker B doc phai ban
#:                             tiem ay -> ba phep kiem `test_306` do
#:
#:    Docstring cua chinh `test_KHONG_test_nao_duoc_GHI_vao_messages_po_THAT`
#:    da viet ra nguyen ly: *"mot test ghi vao tep that thi KHONG THE an toan"*.
#:    No moi chi duoc ap cho `.po`; `.moc` va template la cung mot lop van de.
#:
#: ⛔ Hai bien duoi CHI de test dung. Ma chay that khong bao gio dat chung.
_MOC_THU = __import__("os").environ.get("LTT_MOC_FILE")
TEP_MOC = (pathlib.Path(_MOC_THU) if _MOC_THU
           else pathlib.Path(__file__).with_name("check_dich_thieu.moc"))

#: Goc de babel TRICH msgid. Tach khoi `GOC` vi `GOC` con quyet dinh cho cua
#: `.po` mac dinh — gop lam mot thi doi cai nay keo theo cai kia.
_MA_THU = __import__("os").environ.get("LTT_SRC_ROOT")
GOC_MA = pathlib.Path(_MA_THU) if _MA_THU else GOC
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


def _msgid_trong_ma_nguon() -> set:
    """Moi chuoi da boc `_()`/`N_()`/`_t()` ma babel trich duoc tu MA NGUON.

    Trich **trong bo nho**, khong ghi gi. Do la khac biet quan trong nhat giua
    ham nay va `i18n.py trich`: `trich` goi `msgmerge`, va `msgmerge` DOAN ban
    dich cho msgid moi bang cach khop gan dung voi msgid vua bien mat.

    ⛔ Do 26/08: mot luot trich de don 9 chuoi chet da tu sinh **25 ban dich SAI
       moi** (`Ngan sach cua ban` -> `Your scripts`). Don it hon phan no lam hong.

    ⭐ Nen luat la: **ha moc bang cach DICH, khong bao gio bang cach TRICH LAI.**
       Ham nay chi DOC de so sanh, va do la ly do no an toan de chay moi luot gate.
    """
    import io
    import warnings

    from babel.messages import extract
    from babel.messages.frontend import parse_mapping_cfg

    cau_hinh = GOC_MA / "babel.cfg"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fh = io.StringIO(cau_hinh.read_text(encoding="utf-8"))
        method_map, options_map = parse_mapping_cfg(fh)
        tu_khoa = {**extract.DEFAULT_KEYWORDS, "N_": None, "_t": None}
        ra = set()
        for _tep, _dong, msg, _c, _x in extract.extract_from_dir(
                str(GOC_MA), method_map=method_map, options_map=options_map,
                keywords=tu_khoa):
            if isinstance(msg, (tuple, list)):
                msg = msg[0] if msg else ""
            if isinstance(msg, str) and msg:
                ra.add(msg)
    return ra


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

    # Lop thu hai: da boc `_()` ma KHONG co mot dong nao trong catalog.
    trong_catalog = set()
    for muc in catalog:
        if muc.id:
            mid = muc.id[0] if isinstance(muc.id, (tuple, list)) else muc.id
            trong_catalog.add(mid)
    for mid in _msgid_trong_ma_nguon() - trong_catalog:
        ra[_khoa("VANG", mid)] = "chua tung vao catalog"
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
    p.add_argument("--khoi-tao-loai", metavar="LOAI",
                   help="MOT LAN khi them mot LOAI moi (TRONG/FUZZY/VANG): nhan "
                        "trang thai hien co CUA RIENG loai do vao moc")
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
    vang = sum(1 for k in thieu if k.startswith("VANG"))

    if a.list:
        for khoa in sorted(thieu):
            print(f"  {_an_toan(khoa)}   [{thieu[khoa]}]")

    if a.khoi_tao_loai:
        # 🔴 CUA THOAT DUY NHAT, VA NO BI CHAN HAI PHIA.
        #
        #    Them mot LOAI kiem tra moi vao banh coc thi lan chay dau tien luon
        #    thay "hang chuc muc moi" — chung khong moi, chung vua duoc nhin thay
        #    lan dau. `--accept` tu choi (dung), nen can mot duong khoi tao.
        #
        # ⛔ Nhung mot cua thoat khong gioi han se thanh cach nguoi ta lam im
        #    lang moi thu khac. Nen no chi nhan muc CUA DUNG MOT LOAI duoc goi
        #    ten, va moi loai khac van phai sach truoc da.
        loai = a.khoi_tao_loai.upper()
        khac = [k for k in moi if not k.startswith(loai + "\t")]
        if khac:
            print(f"KHONG khoi tao duoc: con {len(khac)} muc MOI ngoai loai "
                  f"{loai}. Dich chung truoc.", file=sys.stderr)
            for k in khac[:10]:
                print(f"  {_an_toan(k)}", file=sys.stderr)
            return 1
        TEP_MOC.write_text(DAU_HIEU + "\n"
                           + "".join(f"{k}\n" for k in sorted(thieu)),
                           encoding="utf-8")
        print(f"Da khoi tao loai {loai}: nhan {len(moi)} muc vao moc "
              f"(tong {len(thieu)}). Tu day chung chi duoc phep GIAM.")
        return 0

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
        print(f"Da ghi moc: {len(thieu)} muc "
              f"({trong} trong, {fuzzy} fuzzy, {vang} vang)"
              + (f"; bo {len(da_dich)} muc da dich" if da_dich else ""))
        return 0

    print(f"Ban EN con thieu: {len(thieu)} muc "
          f"({trong} msgstr rong, {fuzzy} fuzzy, {vang} vang khoi catalog) "
          f"| moc: {len(moc)}")
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
        print("Muc `VANG` thi THEM TAY vao .po (msgid + msgstr) — dung chay")
        print("`i18n.py trich`: msgmerge se doan ban dich cho chung.")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
