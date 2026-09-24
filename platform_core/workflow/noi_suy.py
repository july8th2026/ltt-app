"""Tang noi suy `{{ }}` — spec §6.1. Tach chuoi, ap ba luat, ghep lai.

Mo-dun nay KHONG biet ngon ngu bieu thuc. No nhan bo tinh qua **tham so**
(`tinh(expr) -> Any`) va chi lam mot viec: quyet dinh chuoi nay cho ra mot
gia tri CO KIEU hay mot chuoi da noi.

## Ba luat (spec §6.1)

1. Chuoi **chi gom mot** `{{ expr }}` ⇒ gia tri **giu KIEU**.
2. Chuoi **tron chu** ⇒ noi chuoi, moi `{{ }}` ep `to_string`.
3. `\\{{` la **chu thuong**.

⭐ Luat 1 la luat ve TIEN, khong phai ve tien nghi. `{{ workflow.input.n }}`
phai tra **so 5**; neu no tra chuoi `"5"` thi cong typed §4.7 hoac tu choi,
hoac — te hon — nhan roi hong luc chay o mot node khac, sau khi da tieu credit.

## ⭐ TRA NGUON — `" {{ a }} "` (khoang trang bao ngoai) la TRON CHU

Hai engine doc lap cho cung cau tra loi, va ta lay no:

- **Jinja2 `NativeEnvironment`** — `pallets/jinja`, `src/jinja2/nativetypes.py`,
  `native_concat`: chi `len(head) == 1` moi tra thang gia tri; `" {{ a }} "`
  bien dich ra ba node ⇒ `"".join([str(v) for v in values])`.
- **n8n / tournament** — `n8n-io/tournament`, `src/ExpressionBuilder.ts`,
  `getExpressionCode`: duong giu kieu la nhanh `else`, vao duoc chi khi
  `chunks.length <= 2 && chunks[0].text === ''`. `splitExpression`
  (`src/ExpressionSplitter.ts`) luon phat mot chunk text dau tien.

Ly do doc duoc, ngoai "hai engine lam vay": mot khoang trang bao ngoai la ky
tu NGUOI GO CO Y go. Nuot no de giu kieu thi `" {{ a }} "` va `"{{ a }}"` cho
hai kieu khac nhau ma nhin mat khong phan biet duoc — dung hang loi ma cong
typed khong bat duoc.

## ⛔ Ba thu MUON DUOC ma CO Y KHONG muon

1. **`literal_eval` cua Jinja2 native.** `native_concat` goi `literal_eval` ke
   ca o duong tron chu ⇒ `"{{a}}{{b}}"` voi 1 va 2 ra **so 12**, va hang so
   `"1"` khong co `{{ }}` nao cung thanh **so 1**. Do la suy kieu tu hinh dang
   chu: kieu cua tham so se phu thuoc vao *gia tri* chu khong vao *cau*.
2. **n8n chap nhan `{{` khong dong** (`hasClosingBrackets: false`, comment
   trong ma noi ro do la tuong thich `tmpl` doi cu). Ta TU CHOI co cho: tham
   so khong ro ket thuc o dau thi kieu khong xac dinh, va §4.7 can kieu truoc
   khi chay.
3. **GitHub Actions tu choi ep Array/Object** (docs Expressions, bang casting
   to string: `Array`/`Object` *"are not converted to a string"*). Ta ep, bang
   JSON — mapping vao than HTTP la ca ly do tang nay ton tai. Nhung ta lay
   phan KHAC cua cung bang do: `Null → ''`, `Boolean → 'true'/'false'`, de
   `None` khong bao gio ra `"None"` truoc mat khach.

## ⛔ Gioi han da biet

- `}}` DAU TIEN dong bieu thuc; khong dem muc long, khong co `\\}}`. Nen
  `{{ "}}" }}` khong viet duoc. La gioi han co chu dich (cung cach
  `ExpressionSplitter` lam), khong phai bug.
- `\\` chi mang nghia thoat khi no dung NGAY TRUOC `{{`. `c:\\tmp\\x` giu
  nguyen. (tournament thu MOI `\\\\` trong chunk chu; ta hep hon, vi duong
  dan Windows di qua day nhieu hon bieu thuc thoat.)
"""
from __future__ import annotations

import json
from typing import Any, Callable, NamedTuple

__all__ = ["BIEU_THUC", "CHU", "LoiNoiSuy", "Manh", "TRAN_CHUOI", "ep_chuoi",
           "noi_suy", "tach"]

#: Tran chuoi, spec §6.4. Ap cho chuoi VAO va cho chuoi da noi di RA.
TRAN_CHUOI = 1024 * 1024

CHU = "chu"
BIEU_THUC = "bieu_thuc"


class Manh(NamedTuple):
    """Mot mieng cua chuoi. `vi_tri` la chi so trong chuoi GOC (de bao loi)."""

    loai: str
    text: str
    vi_tri: int


class LoiNoiSuy(ValueError):
    """Noi suy that bai. Mang `vi_tri` (cot) — cung khuon `LoiBieuThuc` §6.4.

    ⚠️ Co y KHONG ke thua `bieu_thuc.LoiBieuThuc`: tang nay phai test duoc ma
    khong cham vao mo-dun cua tang bieu thuc. Gop ho lop la viec cua luc lap
    ngon ngu §6 lai voi nhau, khong phai cua tang nay.
    """

    def __init__(self, ly_do: str, *, vi_tri: int = 0, bieu_thuc: str = ""):
        self.ly_do = ly_do
        self.vi_tri = vi_tri
        self.bieu_thuc = bieu_thuc[:200]
        super().__init__(f"{ly_do} (cot {vi_tri})" if not bieu_thuc
                         else f"{ly_do} (cot {vi_tri}): {self.bieu_thuc}")


def tach(chuoi: str) -> list[Manh]:
    """Cat chuoi thanh manh chu / manh bieu thuc, da go thoat `\\{{`.

    ⭐ Khong phat manh chu RONG. Do la co so co hoc cua luat 1: "chi gom mot
    `{{ }}`" kiem duoc bang `len(manh) == 1`, khong phai bang mot chuoi dieu
    kien ve chunk rong nhu `getExpressionCode` phai lam.
    """
    manh: list[Manh] = []
    dem: list[str] = []
    dau_chu = 0
    i = 0
    n = len(chuoi)

    def xa_chu() -> None:
        if dem:
            manh.append(Manh(CHU, "".join(dem), dau_chu))
            dem.clear()

    def them_chu(s: str, tai: int) -> None:
        nonlocal dau_chu
        if not dem:
            dau_chu = tai
        dem.append(s)

    while i < n:
        if chuoi[i] == "\\":
            j = i
            while j < n and chuoi[j] == "\\":
                j += 1
            so = j - i
            if chuoi[j:j + 2] == "{{":
                # tournament: `isEscaped = backslashCount % 2 === 1`
                them_chu("\\" * (so // 2), i)
                if so % 2 == 1:
                    them_chu("{{", i)
                    i = j + 2
                else:
                    i = j          # `{{` that — vong sau xu ly
                continue
            them_chu("\\" * so, i)
            i = j
            continue

        if chuoi.startswith("{{", i):
            xa_chu()
            dong = chuoi.find("}}", i + 2)
            if dong < 0:
                raise LoiNoiSuy("thieu dau dong `}}`", vi_tri=i,
                                bieu_thuc=chuoi[i:i + 200])
            bt = chuoi[i + 2:dong].strip()
            if not bt:
                raise LoiNoiSuy("bieu thuc rong", vi_tri=i)
            manh.append(Manh(BIEU_THUC, bt, i))
            i = dong + 2
            continue

        them_chu(chuoi[i], i)
        i += 1

    xa_chu()
    return manh


def ep_chuoi(gia_tri: Any) -> str:
    """`to_string` cua §6.1 luat 2.

    ⛔ KHONG dung `str()` cua Python o cac kieu ghep: `str({'a': 1})` cho
    `{'a': 1}` — nhay don, khong phai JSON, khong dan lai vao than HTTP duoc.
    Va `str(None)` cho `"None"`, thu ma khach se doc tren giao dien.
    """
    if gia_tri is None:
        return ""                       # GHA casting table: Null → ''
    if gia_tri is True:
        return "true"                   # GHA: Boolean → 'true' / 'false'
    if gia_tri is False:
        return "false"
    if isinstance(gia_tri, str):
        return gia_tri
    if isinstance(gia_tri, (int, float)):
        return str(gia_tri)
    if isinstance(gia_tri, (list, tuple, dict)):
        try:
            return json.dumps(gia_tri, ensure_ascii=False,
                              separators=(", ", ": "))
        except (TypeError, ValueError) as loi:
            raise LoiNoiSuy(
                f"khong ep duoc gia tri thanh chuoi: {loi}") from loi
    raise LoiNoiSuy(f"khong ep duoc kieu {type(gia_tri).__name__} thanh chuoi")


def _goi(tinh: Callable[[str], Any], m: Manh) -> Any:
    """Goi bo tinh, va dan VI TRI trong chuoi goc vao loi neu no chua co.

    Bo tinh biet cot trong BIEU THUC; chi tang nay biet bieu thuc do nam o dau
    trong chuoi. Mot template 5 000 ky tu voi muoi `{{ }}` ma bao "loi ten"
    khong noi cai nao thi nguoi dung phai do.
    """
    try:
        return tinh(m.text)
    except Exception as loi:
        # `__dict__` la dieu kien de gan duoc thuoc tinh moi: mot lop loi khai
        # `__slots__` se nem `AttributeError` ngay o day. Hoi truoc thay vi bat
        # sau — bat sau la nuot mot loi khac han loi ta dang bao cao.
        if getattr(loi, "vi_tri_manh", None) is None and hasattr(loi, "__dict__"):
            loi.vi_tri_manh = m.vi_tri   # type: ignore[attr-defined]
        raise


def noi_suy(gia_tri: Any, tinh: Callable[[str], Any], *,
            ep: Callable[[Any], str] = ep_chuoi) -> Any:
    """Noi suy mot gia tri tham so. Khong phai chuoi ⇒ tra nguyen ven.

    `tinh(expr) -> Any` la bo tinh bieu thuc (§6.1–6.4). No di qua tham so chu
    khong qua `import`, nen tang nay test duoc mot minh va khong khoa chung
    nhip phat hanh voi tang bieu thuc.
    """
    if not isinstance(gia_tri, str):
        # n8n `resolveSimpleParameterValue`: khong phai bieu thuc thi tra thang
        return gia_tri
    if len(gia_tri) > TRAN_CHUOI:
        raise LoiNoiSuy(f"chuoi vao vuot tran {TRAN_CHUOI} ky tu (1 MB)",
                        vi_tri=TRAN_CHUOI)
    if "{{" not in gia_tri and "\\" not in gia_tri:
        return gia_tri

    manh = tach(gia_tri)

    # Luat 1 — dung mot manh, va manh do la bieu thuc ⇒ GIU KIEU.
    if len(manh) == 1 and manh[0].loai == BIEU_THUC:
        return _goi(tinh, manh[0])

    # Luat 2 — tron chu ⇒ noi chuoi, moi `{{ }}` qua `to_string`.
    phan: list[str] = []
    tong = 0
    for m in manh:
        s = m.text if m.loai == CHU else ep(_goi(tinh, m))
        tong += len(s)
        if tong > TRAN_CHUOI:
            raise LoiNoiSuy(f"ket qua noi vuot tran {TRAN_CHUOI} ky tu (1 MB)",
                            vi_tri=m.vi_tri)
        phan.append(s)
    return "".join(phan)
