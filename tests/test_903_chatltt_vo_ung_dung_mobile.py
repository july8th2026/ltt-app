"""703 — vo ung dung ChatLTT tren man hep phai la UNG DUNG, khong phai TRANG.

## Phep do dung sau tep nay (05/09, hoi thoai 27 tin nhan)

Ban truoc dat `height: auto; max-height: none` cho `.ltc` duoi 860px:

    390x844   `.ltc` cao 2412  ·  <body> cao 2648  ·  TRANG tu cuon
              `.ltc-luong` cao 1970 — `overflow-y:auto` cua no khong bao gio chay
              o soan o y=929 trong khung cao 844   ->  DUOI MAN HINH
    844x390   o soan o y=549 trong khung cao 390   ->  DUOI MAN HINH
    1440x900  `.ltc` cao 710, `.ltc-luong` cuon trong (511/1430), o soan o 775 -> OK

⭐ Chi ban mobile hong, va no hong theo kieu de bo qua nhat: khong cat chu nao,
   khong tran ngang, khong loi console. Chi la sau moi cau tra loi nguoi dung
   phai cuon mot trang dai de tim lai o nhap. Moi phep kiem "khong tran / khong
   loi" deu xanh — nen phep kiem PHAI hoi thang: *o soan co tren man khong*.

Sau khi sua: 832/844 o doc, 378/390 o ngang, desktop khong doi mot pixel.

## Vi sao kiem CSS bang cau truc chu khong bang trinh duyet

Mot phep kiem trinh duyet o day can may chu + dang nhap + mot hoi thoai co
noi dung; no thuoc ve ma tran QA (Phase G). Tep nay chot nhung MENH DE ma mot
lan sua CSS vo y co the pha, va chot chung trong 0,2 giay.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
CSS = GOC / "frontend" / "chatltt" / "src" / "chatltt.css"


def boc_chu_thich(s: str) -> str:
    """Bo `/* ... */`, giu do dai. CSS khong co chu thich dong `//`."""
    ra = list(s)
    i, n = 0, len(s)
    while i < n:
        if s.startswith("/*", i):
            j = s.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if ra[k] != "\n":
                    ra[k] = " "
            i = j
        else:
            i += 1
    return "".join(ra)


def khoi_media(s: str, dieu_kien: str) -> str:
    """Than cua MOI `@media <dieu_kien> { ... }`, noi lai, lay bang doi ngoac.

    ⚠️ Phai gom TAT CA chu khong lay cai dau tien. `chatltt.css` co hai khoi
       `(max-width: 860px)` — mot cho `#chatltt-day-truoc` va mot cho vo ung
       dung — va ban dau ham nay chi tra khoi dau, nen ba phep kiem do vi doc
       nham khoi. Mot bo trich lay "cai dau tien" la mot bo trich se noi doi
       ngay khi ai do them mot khoi thu hai.
    """
    ra = []
    for m in re.finditer(r"@media\s+" + re.escape(dieu_kien) + r"\s*\{", s):
        i = m.end() - 1
        sau = 0
        for j in range(i, len(s)):
            if s[j] == "{":
                sau += 1
            elif s[j] == "}":
                sau -= 1
                if sau == 0:
                    ra.append(s[i:j + 1])
                    break
        else:
            pytest.fail(f"ngoac cua `@media {dieu_kien}` khong dong")
    assert ra, f"khong tim thay `@media {dieu_kien}`"
    return "\n".join(ra)


def luat(than: str, chon: str) -> str:
    """Than cua mot luat `<chon> { ... }` ben trong `than`."""
    m = re.search(re.escape(chon) + r"\s*\{([^}]*)\}", than)
    return m.group(1) if m else ""


@pytest.fixture(scope="module")
def css() -> str:
    return boc_chu_thich(CSS.read_text(encoding="utf-8"))


def test_bo_boc_chu_thich_that_su_boc():
    """Neu no khong boc, moi phep kiem duoi day xanh gia — chinh cac chu thich
    trong `chatltt.css` co nhac `height: auto` de giai thich vi sao no sai."""
    vao = "a /* height: auto; */ b"
    ra = boc_chu_thich(vao)
    assert "height: auto" not in ra
    assert len(ra) == len(vao)


def test_khoi_media_lay_dung_bang_doi_ngoac():
    s = "@media (max-width: 860px) { .a { x: 1 } } .b { y: 2 }"
    than = khoi_media(s, "(max-width: 860px)")
    assert ".a" in than and ".b" not in than


def test_khoi_media_gom_MOI_khoi_cung_dieu_kien():
    """Lay "cai dau tien" la mot bo trich se noi doi khi co khoi thu hai —
    va do dung la cach ba phep kiem duoi day do nham o lan chay dau."""
    s = ("@media (max-width: 860px) { .a { x: 1 } }"
         " .giua { z: 0 } "
         "@media (max-width: 860px) { .b { y: 2 } }")
    than = khoi_media(s, "(max-width: 860px)")
    assert ".a" in than and ".b" in than and ".giua" not in than


# ── Menh de that ───────────────────────────────────────────────────────────

def test_vo_mobile_khong_duoc_tra_ve_chieu_cao_TU_DO(css):
    than = khoi_media(css, "(max-width: 860px)")
    ltc = luat(than, ".ltc")
    assert ltc, "`.ltc` bien mat khoi khoi mobile"
    assert not re.search(r"height\s*:\s*auto", ltc), (
        "`.ltc` quay ve `height: auto` duoi 860px. Hau qua do duoc 05/09: vo cao "
        "2412px, trang tu cuon, va o soan roi xuong DUOI man hinh.")
    m = re.search(r"(?<!min-)(?<!max-)height\s*:\s*([^;]+);", ltc)
    assert m, "`.ltc` khong con dat `height` o khoi mobile"
    assert "dvh" in m.group(1), (
        f"`.ltc` dung `{m.group(1).strip()}`. Phai la `dvh`: tren dien thoai thanh "
        "dia chi thu vao/nho ra, con `100vh` giu gia tri LON NHAT — o soan bi day "
        "xuong duoi mep man dung luc thanh dia chi dang hien.")


def test_vo_mobile_khong_giu_san_chieu_cao_cua_desktop(css):
    """`min-height: 420px` tren khung cao 390px la mot mau thuan."""
    than = khoi_media(css, "(max-width: 860px)")
    ltc = luat(than, ".ltc")
    m = re.search(r"min-height\s*:\s*(\d+)px", ltc)
    assert not m or int(m.group(1)) <= 320, (
        f"`.ltc` giu san {m.group(1)}px tren mobile. Dien thoai xoay ngang chi con "
        "313px kha dung sau khi tru chrome, nen mot san lon hon the lam chinh cai "
        "no dinh chua: o soan lai bi day xuong duoi man.")


def test_cho_danh_truoc_KHOP_voi_chieu_cao_vo_o_moi_diem_ngat(css):
    """Chinh `chatltt.css` ghi: *"Ba con so phai KHOP voi `.ltc` ben duoi"*.

    🔴 Va do la thu suyt bi pha ngay 05/09. Khi `.ltc` duoi 860px doi sang
       `calc(100dvh - 77px)`, `#chatltt-root` van giu `calc(100vh - 190px)`:
       o 390x844 la 654px danh cho cho mot vo chiem 767px ⇒ chan trang nhay
       113px ngay khi React mount.

    ⭐ Nen menh de o day khong phai "ba con so", ma la **moi diem ngat doi chieu
       cao `.ltc` deu phai co mot dong `#chatltt-root` tuong ung**.
    """
    than = khoi_media(css, "(max-width: 860px)")
    ltc = luat(than, ".ltc")
    m_vo = re.search(r"(?<!min-)(?<!max-)height\s*:\s*calc\(([^)]+)\)", ltc)
    assert m_vo, "`.ltc` mobile khong dat height bang calc()"

    # `#chatltt-root` phai co mot luat cho CUNG diem ngat, voi CUNG cong thuc.
    m_goc = re.search(
        r"@media\s*\(max-width:\s*860px\)\s*\{\s*#chatltt-root\s*\{([^}]*)\}",
        css)
    assert m_goc, (
        "khong co `@media (max-width: 860px) { #chatltt-root { ... } }`. "
        "`.ltc` doi chieu cao o diem ngat nay ma cho danh truoc thi khong — "
        "chan trang se nhay ngay khi React mount, va chi tren dien thoai.")
    assert m_vo.group(1).strip() in m_goc.group(1), (
        f"cho danh truoc dung cong thuc khac `.ltc`: `.ltc` = calc({m_vo.group(1)}), "
        f"root = `{m_goc.group(1).strip()}`. Lech mot cai la lai nhay, chi it hon "
        "— tuc kho thay hon.")


def test_o_soan_co_le_an_toan_o_mobile(css):
    than = khoi_media(css, "(max-width: 860px)")
    soan = luat(than, ".ltc-soan")
    assert "safe-area-inset-bottom" in soan, (
        "o soan nam sat mep duoi vo ung dung tren mobile; thieu `env(safe-area-"
        "inset-bottom)` thi thanh Home cua iPhone de len no")


def test_man_rat_thap_rut_thanh_ben_de_lay_cho_cho_tin_nhan(css):
    """844x390: 313px kha dung. Thanh ben 132 + thanh tren 65 + o soan 99 = 296."""
    than = khoi_media(css, "(max-width: 860px) and (max-height: 500px)")
    ben = luat(than, ".ltc-ben")
    m = re.search(r"max-height\s*:\s*(\d+)px", ben)
    assert m and int(m.group(1)) <= 100, (
        "man rat thap khong rut thanh ben — vung tin nhan con ~17px")
