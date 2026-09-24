"""Bang ham DONG cua ngon ngu bieu thuc §6.3 — 49 ten, khong mot ten nao khac.

## Van de no giai

Ngon ngu bieu thuc §6 can tinh toan tren du lieu: cat chuoi, cong ngay, doc sau
vao mot object JSON. `chinh_sach.py` da co cho de cam mot bang ham vao
(`ChinhSach.ham`) nhung khong biet bang do nen chua gi. Day la bang do.

## ⭐ "DONG" la mot phep so TAP HOP, khong phai mot loi hua

`BANG_HAM` la mot `dict` tra duoc, va `test_1765` so `set(BANG_HAM)` voi ten doc
**tu chinh van ban spec §6.3** — CA HAI CHIEU:

    ten NGOAI spec lot vao   ⇒ do   (mot ham khong ai duyet, mo trong im lang)
    ten TRONG spec bi thieu  ⇒ do   (node publish duoc roi chet luc chay)

⛔ Them mot o vao bang nay ma khong sua spec la lam do `test_1765`. Do la chu y.

## ⛔ BA DIEU BANG NAY KHONG BAO GIO DUOC LAM

1. **Khong tra ve vat goi duoc.** Moi ham tra ve mot gia tri JSON (`None`,
   `bool`, `int`, `float`, `str`, `list`, `dict`). Tra ve mot ham, mot lop hay
   mot `datetime` la dua mot be mat Python vao trong ngon ngu; buoc ke tiep cua
   ke tan cong chi la tim cho goi no.
2. **Khong cham thuoc tinh Python.** Khong `getattr`, khong `eval`, khong
   `__class__`. `test_module_khong_co_cua_thi_hanh` doc AST cua chinh tep nay
   de bat dieu do — co hoc, khong phai giao uoc.
3. **Khoa bat dau `_` la VO HINH.** §6.1 cam truy cap thuoc tinh bat dau `_`.
   Mot `get(obj, "_x")` doc duoc la mot cua hau cho dung luat do, nen luat ay
   duoc thi hanh o MOI cua doc object: `get` `keys` `values` `pick` `omit`
   `merge`. Mot luat, khong phai sau ngoai le.

## ⚠️ NGAY LA CHUOI ISO-8601, KHONG PHAI `datetime`

§6.4 noi tham so da tinh **luu vao snapshot RUNNING** de replay. Mot `datetime`
khong JSON hoa duoc — va no vi pham dieu 1 o tren. Nen moi ham ngay nhan va tra
**chuoi ISO-8601 co offset tuong minh**.

⭐ Cai do con vo tinh go duoc bay `fold` cua PEP 495: 01:30 ngay 2026-11-01 o
New York xay ra HAI lan, va phep tru hai `datetime` CUNG mui gio **bo qua**
`fold` (do 24/09: `f1 - f0 = 0:00:00` trong khi qua UTC la `1:00:00`). Chuoi ISO
mang `-04:00` va `-05:00` — hai moc khac nhau tuong minh, khong con gi de bo qua.

## ⚠️ "Cong mot ngay" va "cong 24 gio" KHONG bang nhau

Do 24/09, CPython 3.13.12 + tzdata 2026.1, tu `2026-03-07T12:00:00-05:00`:

    date_add(d, 1, "day",  "America/New_York")  ⇒ 2026-03-08T12:00:00-04:00
    date_add(d, 24, "hour","America/New_York")  ⇒ 2026-03-08T13:00:00-04:00

"Ngay" la don vi LICH (so hoc tren gio tuong, offset tinh lai), "gio" la don vi
THOI LUONG (so hoc tren UTC). Gop chung lam mot la sai mot ben — va do dung la
hang loi da loai `croniter` khoi kho nay (issue #258: `get_next`/`get_prev` bat
dong khi lech DST khong tron gio).

⛔ Mot chuoi ISO mang OFFSET, khong mang TEN VUNG: `-05:00` khong noi duoc no la
New York hay Bogota. Nen `date_add` nhan them `tz` tuy chon; khong co `tz` thi
no lam so hoc tren offset CO DINH do — dung voi `Asia/Ho_Chi_Minh` (mot offset
tu 1975) va lech mot gio qua ranh gioi DST o noi khac.

## Nguon doi chieu (tra truoc khi tu suy, do lai ngay 24/09)

- `round` lam tron **ve phia so chan** khi hai boi so cach deu:
  https://docs.python.org/3/library/functions.html#round  — do duoc:
  `round(0.5)=0`, `round(2.5)=2`, `round(2.675, 2)=2.67` (nhi phan).
- `sorted`/`list.sort` **on dinh**:
  https://docs.python.org/3/library/stdtypes.html#list.sort — `sort_by` dua
  tren bao dam nay.
- `zoneinfo` + PEP 495 `fold`: https://docs.python.org/3/library/zoneinfo.html
  va https://peps.python.org/pep-0495/ — phep tru CUNG mui gio bo qua `fold`.
- `Asia/Ho_Chi_Minh` **khong** la mot offset co dinh trong lich su: tzdata
  2026.1 cho `+08:00` truoc 1975-06 va `+07:00` sau do (do duoc).

## ⭐ NHOM REGEX — cho trong CO CHU DICH

§6.3 hoan nhom regex vi `re` cua Python quay lui tham hoa voi mau do nguoi dung
viet. Bang nay de **mo duoc**: no ghep tu cac nhom `_NHOM_*`, nen them mot
`_NHOM_REGEX` la mot dong. ⛔ Nhung mo la mot QUYET DINH:
`test_bang_chua_mo_nhom_regex` bat ai do them lang le, va spec §6.3 phai sua
truoc. Engine khong quay lui da chon: `google-re2` (RE2 tuyen tinh).
⚠️ Do 24/09: goi do **chua duoc cai** tren trinh thong dich dang dung
(`import re2` that bai; PyPI co `google-re2 1.1.20251105`). Phai cai va do lai
truoc khi ai do dua vao ke hoach.
"""
from __future__ import annotations

import functools
import json
import math
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

__all__ = ["BANG_HAM", "LoiHam", "MUI_GIO_MAC_DINH", "nguon_slug"]

#: §6.3: mui gio bat buoc tuong minh, mac dinh gio Viet Nam.
MUI_GIO_MAC_DINH = "Asia/Ho_Chi_Minh"

#: §6.3 khai thang tran nay cho `range`.
TRAN_RANGE = 1000

#: Chuoi dinh dang dai hon nay khong phai mot dinh dang, no la mot tai trong.
_TRAN_DINH_DANG = 64

#: Cung con so voi §6.4 — de `unique`/`json_string` khong bien mot cau truc
#: long sau thanh `RecursionError` tho.
_TRAN_SAU = 32

_DON_VI_CONG = {"hour": 3600, "minute": 60}
_DON_VI_LICH = "day"
_DON_VI_HIEU = {"day": 86400, "hour": 3600, "minute": 60, "second": 1}

_GIA_TRI_JSON = (bool, int, float, str, list, dict)


class LoiHam(ValueError):
    """Goi mot ham trong bang voi dau vao sai.

    ⚠️ Lop rieng, KHONG phai `LoiBieuThuc` cua `bieu_thuc.py`: mo-dun do giu
    hop dong cua `timeout_expr` va khong duoc keo bang ham nay vao. Phuong ngu
    §6 boc `LoiHam` lai thanh `bieu_thuc_loi` kem `vi_tri` (§6.4).
    """


# ── Kiem kieu: mot cho, de cau loi giong nhau o moi ham ───────────────────

def _ten_kieu(gia_tri: Any) -> str:
    """Ten kieu dung trong CAU LOI. Khong bao gio nem — loi khong duoc loi."""
    if gia_tri is None:
        return "null"
    for kieu, ten in ((bool, "boolean"), (int, "integer"), (float, "number"),
                      (str, "text"), (list, "list"), (dict, "object")):
        if isinstance(gia_tri, kieu):
            return ten
    return "khong_ho_tro"


def _la_so(gia_tri: Any) -> bool:
    """`True` chi voi so THAT. ⚠️ `bool` la lop con cua `int` trong Python —
    khong loai no ra thi `sum([1, True])` lang le ra `2`."""
    return not isinstance(gia_tri, bool) and isinstance(gia_tri, (int, float))


def _doi_chuoi(gia_tri: Any, ten: str) -> str:
    if not isinstance(gia_tri, str):
        raise LoiHam(f"{ten}: can chuoi, gap {_ten_kieu(gia_tri)}")
    return gia_tri


def _doi_so(gia_tri: Any, ten: str) -> int | float:
    if not _la_so(gia_tri):
        raise LoiHam(f"{ten}: can so, gap {_ten_kieu(gia_tri)}")
    if isinstance(gia_tri, float) and not math.isfinite(gia_tri):
        raise LoiHam(f"{ten}: so khong huu han")
    return gia_tri


def _doi_nguyen(gia_tri: Any, ten: str) -> int:
    if isinstance(gia_tri, bool) or not isinstance(gia_tri, int):
        raise LoiHam(f"{ten}: can so nguyen, gap {_ten_kieu(gia_tri)}")
    return gia_tri


def _doi_khong_am(gia_tri: Any, ten: str) -> int:
    so = _doi_nguyen(gia_tri, ten)
    if so < 0:
        raise LoiHam(f"{ten}: chi so am khong duoc phep, gap {so}")
    return so


def _doi_ds(gia_tri: Any, ten: str) -> list:
    if not isinstance(gia_tri, list):
        raise LoiHam(f"{ten}: can danh sach, gap {_ten_kieu(gia_tri)}")
    return gia_tri


def _doi_obj(gia_tri: Any, ten: str) -> dict:
    if not isinstance(gia_tri, dict):
        raise LoiHam(f"{ten}: can object, gap {_ten_kieu(gia_tri)}")
    return gia_tri


def _doi_dinh_dang(gia_tri: Any, ten: str) -> str:
    dinh_dang = _doi_chuoi(gia_tri, ten)
    if not dinh_dang or len(dinh_dang) > _TRAN_DINH_DANG:
        raise LoiHam(
            f"{ten}: dinh dang phai co tu 1 den {_TRAN_DINH_DANG} ky tu")
    return dinh_dang


def _thay_duoc(khoa: Any) -> bool:
    """§6.1: thuoc tinh bat dau `_` khong ton tai doi voi ngon ngu nay."""
    return isinstance(khoa, str) and not khoa.startswith("_")


def _gom(dau_vao: tuple) -> list:
    """`min(a, b, c)` va `min([a, b, c])` la cung mot y."""
    if len(dau_vao) == 1 and isinstance(dau_vao[0], list):
        return list(dau_vao[0])
    return list(dau_vao)


def _cung_hang(ds: list, ten: str) -> None:
    """Sap xep duoc chi khi moi phan tu cung mot hang — Python nem `TypeError`
    tho o day va cau do khong noi cho nguoi khai workflow biet gi."""
    if not ds:
        return
    if all(isinstance(x, str) for x in ds):
        return
    if all(isinstance(x, bool) for x in ds):
        return
    if all(_la_so(x) for x in ds):
        return
    raise LoiHam(f"{ten}: chi so sanh duoc danh sach toan so, toan chuoi hoac "
                 f"toan boolean; gap {sorted({_ten_kieu(x) for x in ds})}")


# ── Chuoi ─────────────────────────────────────────────────────────────────

def _ham_len(gia_tri: Any) -> int:
    if isinstance(gia_tri, (str, list, dict)):
        return len(gia_tri)
    raise LoiHam(f"len: can chuoi, danh sach hoac object, "
                 f"gap {_ten_kieu(gia_tri)}")


def _ham_lower(chuoi: Any) -> str:
    return _doi_chuoi(chuoi, "lower").lower()


def _ham_upper(chuoi: Any) -> str:
    return _doi_chuoi(chuoi, "upper").upper()


def _ham_trim(chuoi: Any) -> str:
    return _doi_chuoi(chuoi, "trim").strip()


def _ham_split(chuoi: Any, dau: Any) -> list:
    chuoi = _doi_chuoi(chuoi, "split")
    dau = _doi_chuoi(dau, "split")
    if not dau:
        raise LoiHam("split: dau ngan cach khong duoc rong")
    return chuoi.split(dau)


def _ham_join(ds: Any, dau: Any) -> str:
    ds = _doi_ds(ds, "join")
    dau = _doi_chuoi(dau, "join")
    for vi_tri, phan in enumerate(ds):
        if not isinstance(phan, str):
            # §6.4 cam ep ngam giua chuoi va so. `join` la cho de quen nhat.
            raise LoiHam(f"join: phan tu {vi_tri} la {_ten_kieu(phan)}, "
                         f"khong phai chuoi — dung to_string()")
    return dau.join(ds)


def _ham_replace(chuoi: Any, cu: Any, moi: Any) -> str:
    chuoi = _doi_chuoi(chuoi, "replace")
    cu = _doi_chuoi(cu, "replace")
    moi = _doi_chuoi(moi, "replace")
    if not cu:
        # Python chen `moi` vao GIUA moi ky tu khi `cu` rong. Khong ai co y do.
        return chuoi
    return chuoi.replace(cu, moi)


def _ham_contains(thung: Any, phan: Any) -> bool:
    if isinstance(thung, str):
        return _doi_chuoi(phan, "contains") in thung
    if isinstance(thung, list):
        return any(x is phan or x == phan for x in thung)
    raise LoiHam(f"contains: can chuoi hoac danh sach, gap {_ten_kieu(thung)}")


def _ham_starts_with(chuoi: Any, dau: Any) -> bool:
    return _doi_chuoi(chuoi, "starts_with").startswith(
        _doi_chuoi(dau, "starts_with"))


def _ham_ends_with(chuoi: Any, duoi: Any) -> bool:
    return _doi_chuoi(chuoi, "ends_with").endswith(
        _doi_chuoi(duoi, "ends_with"))


def _ham_substring(chuoi: Any, bat_dau: Any, ket_thuc: Any = None) -> str:
    chuoi = _doi_chuoi(chuoi, "substring")
    bat_dau = _doi_khong_am(bat_dau, "substring")
    if ket_thuc is None:
        return chuoi[bat_dau:]
    ket_thuc = _doi_khong_am(ket_thuc, "substring")
    if ket_thuc < bat_dau:
        raise LoiHam(f"substring: ket_thuc {ket_thuc} < bat_dau {bat_dau}")
    return chuoi[bat_dau:ket_thuc]


@functools.cache
def nguon_slug() -> Callable[[str], str]:
    """Ham chuan hoa slug DUY NHAT cua kho — khong co ban thu hai.

    ⭐ `platform_core/public_api/projects.py` da co no, da co test, va da xu ly
    dung cho kho nay: bo dau tieng Viet TRUOC khi cat, neu khong "Trang ban
    hang" thanh mot hang gach ngang. Viet lai o day la tao ra hai ket qua cho
    cung mot chuoi — va khong ai bat khop hai ket qua do.

    ⚠️ Chi dung phan CHUAN HOA. `projects.slugify()` con cat 64 ky tu va lui ve
    `"default"` khi rong: do la luat cua COT `api_projects.slug`, khong phai cua
    ngon ngu bieu thuc. Mot ham bieu thuc bia ra `"default"` cho chuoi rong la
    tra ve gia tri nguoi khai khong he nhap.

    ⚠️ Nap tre: mo-dun `projects` keo theo SQLAlchemy, va bang ham nay phai nap
    duoc trong mot tien trinh khong co CSDL.
    """
    from platform_core.public_api.projects import chuan_hoa_slug
    return chuan_hoa_slug


def _ham_slugify(chuoi: Any) -> str:
    return nguon_slug()(_doi_chuoi(chuoi, "slugify"))


# ── So ────────────────────────────────────────────────────────────────────

def _ham_to_number(gia_tri: Any) -> int | float:
    if isinstance(gia_tri, bool):
        return 1 if gia_tri else 0
    if _la_so(gia_tri):
        return _doi_so(gia_tri, "to_number")
    chuoi = _doi_chuoi(gia_tri, "to_number").strip()
    # ⚠️ `int("1_0")` la 10 trong Python. Mot chuoi nguoi dung go co gach duoi
    # khong bao gio co y la mot so — tu choi thang.
    if not chuoi or "_" in chuoi:
        raise LoiHam(f"to_number: {chuoi!r} khong phai so")
    try:
        return int(chuoi)
    except ValueError:
        pass
    try:
        so = float(chuoi)
    except ValueError:
        raise LoiHam(f"to_number: {chuoi!r} khong phai so") from None
    if not math.isfinite(so):
        # `float("inf")` va `float("nan")` phan tich duoc, va ca hai deu pha
        # moi phep so sanh ve sau ma khong bao gi.
        raise LoiHam(f"to_number: {chuoi!r} khong phai so huu han")
    return so


def _ham_round(gia_tri: Any, so_le: Any = 0) -> int | float:
    gia_tri = _doi_so(gia_tri, "round")
    so_le = _doi_nguyen(so_le, "round")
    return round(gia_tri, so_le) if so_le else round(gia_tri)


def _ham_floor(gia_tri: Any) -> int:
    return math.floor(_doi_so(gia_tri, "floor"))


def _ham_ceil(gia_tri: Any) -> int:
    return math.ceil(_doi_so(gia_tri, "ceil"))


def _ham_abs(gia_tri: Any) -> int | float:
    return abs(_doi_so(gia_tri, "abs"))


def _day_so(dau_vao: tuple, ten: str) -> list:
    ds = _gom(dau_vao)
    for vi_tri, phan in enumerate(ds):
        if not _la_so(phan):
            raise LoiHam(f"{ten}: phan tu {vi_tri} la {_ten_kieu(phan)}, "
                         f"khong phai so")
    return ds


def _ham_min(*dau_vao: Any) -> int | float:
    ds = _day_so(dau_vao, "min")
    if not ds:
        raise LoiHam("min: danh sach rong khong co gia tri nho nhat")
    return min(ds)


def _ham_max(*dau_vao: Any) -> int | float:
    ds = _day_so(dau_vao, "max")
    if not ds:
        raise LoiHam("max: danh sach rong khong co gia tri lon nhat")
    return max(ds)


def _ham_sum(*dau_vao: Any) -> int | float:
    return sum(_day_so(dau_vao, "sum"))


# ── Kieu ──────────────────────────────────────────────────────────────────

def _ham_type_of(gia_tri: Any) -> str:
    """Tu vung GIA TRI, co y tho hon tu vung CONG (`he_kieu.KIEU_CO_BAN`).

    Muon `text`/`number`/`integer`/`boolean` tu `he_kieu` de khong de ra cach
    goi thu hai — nhung KHONG muon `json`, vi chinh `he_kieu` danh dau viec no
    gop `list` voi `dict` lam mot la mot khiem khuyet dang co.
    """
    ten = _ten_kieu(gia_tri)
    if ten == "khong_ho_tro":
        raise LoiHam("type_of: gia tri khong thuoc ngon ngu bieu thuc")
    return ten


def _ham_to_string(gia_tri: Any) -> str:
    if gia_tri is None:
        return ""
    if isinstance(gia_tri, str):
        return gia_tri
    if isinstance(gia_tri, bool):
        # `str(True)` la `"True"` — chu hoa kieu Python, khong phai kieu JSON
        # ma phan con lai cua nen tang doc.
        return "true" if gia_tri else "false"
    if isinstance(gia_tri, (int, float, list, dict)):
        return _ham_json_string(gia_tri)
    raise LoiHam(f"to_string: khong chuyen duoc {_ten_kieu(gia_tri)}")


def _ham_to_bool(gia_tri: Any) -> bool:
    if gia_tri is None:
        return False
    if isinstance(gia_tri, bool):
        return gia_tri
    if isinstance(gia_tri, int) and gia_tri in (0, 1):
        return bool(gia_tri)
    if isinstance(gia_tri, str):
        chuoi = gia_tri.strip().lower()
        if chuoi == "true":
            return True
        if chuoi == "false":
            return False
    # ⛔ Khong lui ve do-that-cua-Python: `to_bool([])` ra `false` va
    #   `to_bool("no")` ra `true` deu la cau tra loi bia ra.
    raise LoiHam(f"to_bool: chi nhan true/false, 0/1 hoac null; "
                 f"gap {_ten_kieu(gia_tri)}")


def _ham_to_int(gia_tri: Any) -> int:
    if isinstance(gia_tri, bool):
        return 1 if gia_tri else 0
    if _la_so(gia_tri):
        return math.trunc(_doi_so(gia_tri, "to_int"))
    chuoi = _doi_chuoi(gia_tri, "to_int").strip()
    if not chuoi or "_" in chuoi:
        raise LoiHam(f"to_int: {chuoi!r} khong phai so nguyen")
    try:
        return int(chuoi)
    except ValueError:
        raise LoiHam(f"to_int: {chuoi!r} khong phai so nguyen — dung "
                     f"to_int(to_number(x)) neu muon cat phan le") from None


def _ham_is_null(gia_tri: Any) -> bool:
    return gia_tri is None


def _ham_default(gia_tri: Any, mac_dinh: Any) -> Any:
    # ⚠️ CHI bat `null`. Chuoi rong, `0` va `false` la gia tri that; nuot chung
    #   la lop loi "0 bien thanh mac dinh" ma khong ai truy ra duoc.
    return mac_dinh if gia_tri is None else gia_tri


def _ham_coalesce(*dau_vao: Any) -> Any:
    for gia_tri in dau_vao:
        if gia_tri is not None:
            return gia_tri
    return None


# ── JSON ──────────────────────────────────────────────────────────────────

def _khong_hang_dac_biet(ten: str) -> Any:
    raise LoiHam(f"json_parse: {ten} khong phai JSON hop le")


def _ham_json_parse(chuoi: Any) -> Any:
    chuoi = _doi_chuoi(chuoi, "json_parse")
    try:
        return json.loads(chuoi, parse_constant=_khong_hang_dac_biet)
    except json.JSONDecodeError as loi:
        raise LoiHam(f"json_parse: {loi.msg} tai ky tu {loi.pos}") from loi
    except RecursionError as loi:
        raise LoiHam("json_parse: cau truc long qua sau") from loi


def _ham_json_string(gia_tri: Any) -> str:
    try:
        # `allow_nan=False`: mac dinh cua Python xuat `NaN`/`Infinity`, khong
        # phai JSON, va ben doc se hong. `ensure_ascii=False`: giu tieng Viet.
        return json.dumps(gia_tri, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as loi:
        raise LoiHam(f"json_string: khong chuyen duoc sang JSON ({loi})") from loi
    except RecursionError as loi:
        raise LoiHam("json_string: cau truc long qua sau") from loi


# ── Danh sach ─────────────────────────────────────────────────────────────

def _ham_first(ds: Any) -> Any:
    ds = _doi_ds(ds, "first")
    return ds[0] if ds else None


def _ham_last(ds: Any) -> Any:
    ds = _doi_ds(ds, "last")
    return ds[-1] if ds else None


def _ham_slice(ds: Any, bat_dau: Any, ket_thuc: Any = None) -> list:
    ds = _doi_ds(ds, "slice")
    bat_dau = _doi_khong_am(bat_dau, "slice")
    if ket_thuc is None:
        return ds[bat_dau:]
    ket_thuc = _doi_khong_am(ket_thuc, "slice")
    if ket_thuc < bat_dau:
        raise LoiHam(f"slice: ket_thuc {ket_thuc} < bat_dau {bat_dau}")
    return ds[bat_dau:ket_thuc]


def _ham_sort(ds: Any) -> list:
    ds = _doi_ds(ds, "sort")
    _cung_hang(ds, "sort")
    return sorted(ds)


def _ham_sort_by(ds: Any, khoa: Any) -> list:
    ds = _doi_ds(ds, "sort_by")
    khoa = _doi_chuoi(khoa, "sort_by")
    if not _thay_duoc(khoa):
        raise LoiHam(f"sort_by: khoa {khoa!r} bat dau bang '_' nen khong doc duoc")
    moc = []
    for vi_tri, phan in enumerate(ds):
        if not isinstance(phan, dict):
            raise LoiHam(f"sort_by: phan tu {vi_tri} la {_ten_kieu(phan)}, "
                         f"khong phai object")
        if khoa not in phan:
            # ⛔ Khong lui ve `None`: mot phan tu thieu khoa se troi len dau va
            #   khong ai nhan ra thu tu da sai.
            raise LoiHam(f"sort_by: phan tu {vi_tri} khong co khoa {khoa!r}")
        moc.append(phan[khoa])
    _cung_hang(moc, "sort_by")
    # `sorted` ON DINH (tai lieu Python) ⇒ hai phan tu cung khoa giu nguyen thu
    # tu goc. Doc no o day de khong ai "toi uu" thanh mot phep sap khong on dinh.
    cap = sorted(zip(moc, ds, strict=True), key=lambda o: o[0])
    return [phan for _, phan in cap]


def _dau_van(gia_tri: Any, sau: int = 0) -> tuple:
    """Dau van BAM DUOC cho mot gia tri JSON, de `unique` chay tren dict/list.

    ⚠️ Mang theo TEN KIEU: trong Python `0 == False` va `1 == True`, nen mot
    dau van chi dua tren gia tri se nuot mat mot trong hai.
    """
    if sau > _TRAN_SAU:
        raise LoiHam(f"unique: cau truc long qua {_TRAN_SAU} tang")
    if gia_tri is None:
        return ("null",)
    if isinstance(gia_tri, bool):
        return ("boolean", gia_tri)
    if isinstance(gia_tri, (int, float)):
        return ("number", gia_tri)
    if isinstance(gia_tri, str):
        return ("text", gia_tri)
    if isinstance(gia_tri, list):
        return ("list", tuple(_dau_van(x, sau + 1) for x in gia_tri))
    if isinstance(gia_tri, dict):
        return ("object", tuple(sorted(
            (k, _dau_van(v, sau + 1)) for k, v in gia_tri.items()
            if _thay_duoc(k))))
    raise LoiHam(f"unique: khong so sanh duoc {_ten_kieu(gia_tri)}")


def _ham_unique(ds: Any) -> list:
    ds = _doi_ds(ds, "unique")
    da_thay: set = set()
    ra = []
    for phan in ds:
        dau = _dau_van(phan)
        if dau not in da_thay:
            da_thay.add(dau)
            ra.append(phan)
    return ra


def _ham_pluck(ds: Any, khoa: Any) -> list:
    ds = _doi_ds(ds, "pluck")
    khoa = _doi_chuoi(khoa, "pluck")
    if not _thay_duoc(khoa):
        raise LoiHam(f"pluck: khoa {khoa!r} bat dau bang '_' nen khong doc duoc")
    ra = []
    for vi_tri, phan in enumerate(ds):
        if not isinstance(phan, dict):
            raise LoiHam(f"pluck: phan tu {vi_tri} la {_ten_kieu(phan)}, "
                         f"khong phai object")
        if khoa in phan:
            ra.append(phan[khoa])
    return ra


def _ham_flatten(ds: Any) -> list:
    ds = _doi_ds(ds, "flatten")
    ra: list = []
    for vi_tri, phan in enumerate(ds):
        if not isinstance(phan, list):
            raise LoiHam(f"flatten: phan tu {vi_tri} la {_ten_kieu(phan)}, "
                         f"khong phai danh sach")
        # MOT tang. De quy thi mot cau truc long sau bien thanh mot danh sach
        # dai bat ngo, va nguoi khai khong con cach nao lay lai tang trong.
        ra.extend(phan)
    return ra


def _ham_range(so_luong: Any) -> list:
    so_luong = _doi_khong_am(so_luong, "range")
    if so_luong > TRAN_RANGE:
        raise LoiHam(f"range: toi da {TRAN_RANGE} phan tu, xin {so_luong}")
    return list(range(so_luong))


def _ham_count(ds: Any) -> int:
    return len(_doi_ds(ds, "count"))


# ── Object ────────────────────────────────────────────────────────────────

def _ham_keys(obj: Any) -> list:
    return [k for k in _doi_obj(obj, "keys") if _thay_duoc(k)]


def _ham_values(obj: Any) -> list:
    return [v for k, v in _doi_obj(obj, "values").items() if _thay_duoc(k)]


def _ham_get(obj: Any, duong: Any, mac_dinh: Any = None) -> Any:
    """`get(obj, "a.b", mac_dinh)` — di SAU, va chi di trong `dict`/`list`.

    ⭐ Day la be mat de mo cua nhat trong ca bang, va no dong bang BA lop:

      1. Chi di vao `dict` (theo khoa) va `list` (theo chi so thap phan ASCII).
         ⛔ Khong `getattr`. `__class__.__init__.__globals__` la duong di kinh
         dien ra `os.system`, va no di bang `getattr`.
      2. Doan bat dau `_` bi tu choi **ke ca khi dict that su co khoa do** —
         neu khong, `get` la cua hau cho dung luat §6.1 no dang phuc vu.
      3. Gia tri cuoi cung phai la gia tri JSON. Mot `dict` van co the chua mot
         vat goi duoc (nap tu mot cho khong phai JSON); tra no ra la dua mot be
         mat Python vao ngon ngu.

    ⛔ Sai thi tra `mac_dinh`, khong nem: `get` ton tai de doc du lieu co the
      vang mat. Nem o day bien moi loi go nham khoa thanh mot run FAILED.
    """
    if not isinstance(duong, str) or not duong:
        return mac_dinh
    hien_tai = obj
    for doan in duong.split("."):
        if not doan or doan.startswith("_"):
            return mac_dinh
        if isinstance(hien_tai, dict):
            if doan not in hien_tai:
                return mac_dinh
            hien_tai = hien_tai[doan]
        elif isinstance(hien_tai, list):
            # ⚠️ KHONG dung `str.isdigit()`: no dung voi "²" va voi chu so
            # Arabic-Indic, va `int()` nuot ca hai.
            if not doan or any(c not in "0123456789" for c in doan):
                return mac_dinh
            chi_so = int(doan)
            if chi_so >= len(hien_tai):
                return mac_dinh
            hien_tai = hien_tai[chi_so]
        else:
            return mac_dinh
    if hien_tai is None or isinstance(hien_tai, _GIA_TRI_JSON):
        return hien_tai
    return mac_dinh


def _ham_merge(*dau_vao: Any) -> dict:
    ra: dict = {}
    for vi_tri, obj in enumerate(_gom(dau_vao)):
        for khoa, gia_tri in _doi_obj(obj, f"merge[{vi_tri}]").items():
            if _thay_duoc(khoa):
                ra[khoa] = gia_tri
    return ra


def _ham_pick(obj: Any, *khoa: Any) -> dict:
    obj = _doi_obj(obj, "pick")
    muon = _gom(khoa)
    return {k: obj[k] for k in muon
            if _thay_duoc(k) and k in obj}


def _ham_omit(obj: Any, *khoa: Any) -> dict:
    obj = _doi_obj(obj, "omit")
    bo = set(_gom(khoa))
    return {k: v for k, v in obj.items() if _thay_duoc(k) and k not in bo}


# ── Ngay ──────────────────────────────────────────────────────────────────

def _vung(tz: Any) -> ZoneInfo:
    ten = MUI_GIO_MAC_DINH if tz is None else _doi_chuoi(tz, "mui gio")
    try:
        return ZoneInfo(ten)
    except (KeyError, ValueError, OSError) as loi:
        raise LoiHam(f"mui gio {ten!r} khong co trong tzdata") from loi


def _gan_vung(tho: datetime, vung: ZoneInfo) -> datetime:
    """Gan mui gio cho mot moc KHONG co offset, va tu choi gio khong ton tai.

    ⚠️ 02:30 ngay 2026-03-08 o New York khong ton tai (dong ho nhay 02:00 →
    03:00). CPython **khong** bao loi: no lay offset truoc chuyen doi roi im
    lang cho ra mot moc UTC ung voi 03:30. Mot tran thoi gian lech mot tieng ma
    khong ai biet la dung hang loi phai chan — nen ta doi chieu bang cach quay
    vong qua UTC va so lai gio tuong.
    """
    co_vung = tho.replace(tzinfo=vung)
    quay_ve = co_vung.astimezone(timezone.utc).astimezone(vung)
    if quay_ve.replace(tzinfo=None) != tho:
        raise LoiHam(f"gio {tho.isoformat()} khong ton tai o mui gio "
                     f"{quay_ve.tzname()} (ngay doi gio mua he)")
    return co_vung


def _doc_moc(chuoi: Any, ten: str) -> datetime:
    """Doc mot moc ISO-8601 DA co offset. Thieu offset la thieu hop dong."""
    chuoi = _doi_chuoi(chuoi, ten)
    try:
        moc = datetime.fromisoformat(chuoi)
    except ValueError as loi:
        raise LoiHam(f"{ten}: {chuoi!r} khong phai moc ISO-8601") from loi
    if moc.utcoffset() is None:
        raise LoiHam(f"{ten}: {chuoi!r} khong co mui gio — dung date_parse() "
                     f"de gan mui gio tuong minh truoc")
    return moc


def _ham_date_parse(chuoi: Any, dinh_dang: Any = "iso",
                    tz: Any = None) -> str:
    """Chuoi + dinh dang + mui gio ⇒ moc ISO-8601 co offset tuong minh."""
    chuoi = _doi_chuoi(chuoi, "date_parse")
    dinh_dang = _doi_dinh_dang(dinh_dang, "date_parse")
    vung = _vung(tz)
    if dinh_dang == "iso":
        try:
            moc = datetime.fromisoformat(chuoi)
        except ValueError as loi:
            raise LoiHam(
                f"date_parse: {chuoi!r} khong phai ISO-8601") from loi
    else:
        try:
            moc = datetime.strptime(chuoi, dinh_dang)
        except (ValueError, TypeError) as loi:
            raise LoiHam(f"date_parse: {chuoi!r} khong khop dinh dang "
                         f"{dinh_dang!r} ({loi})") from loi
    if moc.utcoffset() is not None:
        # Chuoi da mang offset cua chinh no. ⛔ Khong de `tz` ghi de: doi mot
        # moc sang mui gio khac la mot phep DOI, khong phai mot phep DOC.
        return moc.isoformat()
    return _gan_vung(moc, vung).isoformat()


def _ham_date_format(moc: Any, dinh_dang: Any = "iso", tz: Any = None) -> str:
    gia_tri = _doc_moc(moc, "date_format")
    dinh_dang = _doi_dinh_dang(dinh_dang, "date_format")
    gia_tri = gia_tri.astimezone(_vung(tz))
    if dinh_dang == "iso":
        return gia_tri.isoformat()
    try:
        return gia_tri.strftime(dinh_dang)
    except (ValueError, TypeError) as loi:
        raise LoiHam(f"date_format: dinh dang {dinh_dang!r} khong dung duoc "
                     f"({loi})") from loi


def _ham_date_add(moc: Any, so_buoc: Any, don_vi: Any, tz: Any = None) -> str:
    """Cong theo LICH (`day`) hoac theo THOI LUONG (`hour`/`minute`).

    ⭐ Hai phep nay KHAC NHAU qua ranh gioi DST, va ca hai deu dung — xem
    docstring dau tep. Gop chung lam mot la sai mot ben.
    """
    gia_tri = _doc_moc(moc, "date_add")
    so_buoc = _doi_nguyen(so_buoc, "date_add")
    if don_vi != _DON_VI_LICH and don_vi not in _DON_VI_CONG:
        raise LoiHam(f"date_add: don vi phai la day, hour hoac minute; "
                     f"gap {don_vi!r}")
    if tz is None:
        # Chuoi ISO mang OFFSET chu khong mang TEN VUNG, nen khong co `tz` thi
        # khong co cach nao biet quy tac DST nao ap dung. Giu offset co dinh va
        # noi ro dieu do trong test, thay vi doan mot mui gio.
        vung: Any = gia_tri.tzinfo
    else:
        vung = _vung(tz)
        gia_tri = gia_tri.astimezone(vung)

    if don_vi == _DON_VI_LICH:
        tho = gia_tri.replace(tzinfo=None) + timedelta(days=so_buoc)
        if isinstance(vung, ZoneInfo):
            return _gan_vung(tho, vung).isoformat()
        return tho.replace(tzinfo=vung).isoformat()

    # ⛔ KHONG `gia_tri + timedelta(...)`: tren mot `datetime` co `ZoneInfo`,
    #   Python cong vao GIO TUONG roi tinh lai offset — "+24 gio" qua ngay doi
    #   gio se chi troi qua 23 gio THAT. Doi ve UTC truoc.
    giay = so_buoc * _DON_VI_CONG[don_vi]
    ra = gia_tri.astimezone(timezone.utc) + timedelta(seconds=giay)
    return ra.astimezone(vung).isoformat()


def _ham_date_diff(sau: Any, truoc: Any, don_vi: Any = "second") -> int:
    """`sau - truoc`, do bang THOI LUONG THAT, cat ve 0.

    ⭐ Tinh qua UTC chu khong tru truc tiep: PEP 495 quy dinh phep tru hai moc
    CUNG mui gio **bo qua** `fold`, nen 01:30 (lan 1) va 01:30 (lan 2) cua ngay
    doi gio se ra `0` — do duoc 24/09. Offset trong chuoi ISO phan biet chung.
    """
    if don_vi not in _DON_VI_HIEU:
        raise LoiHam(f"date_diff: don vi phai la mot trong "
                     f"{sorted(_DON_VI_HIEU)}; gap {don_vi!r}")
    a = _doc_moc(sau, "date_diff").astimezone(timezone.utc)
    b = _doc_moc(truoc, "date_diff").astimezone(timezone.utc)
    return math.trunc((a - b).total_seconds() / _DON_VI_HIEU[don_vi])


# ── BANG DONG ─────────────────────────────────────────────────────────────

_NHOM_CHUOI: dict[str, Callable[..., Any]] = {
    "len": _ham_len, "lower": _ham_lower, "upper": _ham_upper,
    "trim": _ham_trim, "split": _ham_split, "join": _ham_join,
    "replace": _ham_replace, "contains": _ham_contains,
    "starts_with": _ham_starts_with, "ends_with": _ham_ends_with,
    "substring": _ham_substring, "slugify": _ham_slugify,
}
_NHOM_SO: dict[str, Callable[..., Any]] = {
    "to_number": _ham_to_number, "round": _ham_round, "floor": _ham_floor,
    "ceil": _ham_ceil, "abs": _ham_abs, "min": _ham_min, "max": _ham_max,
    "sum": _ham_sum,
}
_NHOM_KIEU: dict[str, Callable[..., Any]] = {
    "to_string": _ham_to_string, "to_bool": _ham_to_bool,
    "to_int": _ham_to_int, "is_null": _ham_is_null, "default": _ham_default,
    "coalesce": _ham_coalesce, "type_of": _ham_type_of,
}
_NHOM_JSON: dict[str, Callable[..., Any]] = {
    "json_parse": _ham_json_parse, "json_string": _ham_json_string,
}
_NHOM_DANH_SACH: dict[str, Callable[..., Any]] = {
    "first": _ham_first, "last": _ham_last, "slice": _ham_slice,
    "sort": _ham_sort, "sort_by": _ham_sort_by, "unique": _ham_unique,
    "pluck": _ham_pluck, "flatten": _ham_flatten, "range": _ham_range,
    "count": _ham_count,
}
_NHOM_OBJECT: dict[str, Callable[..., Any]] = {
    "keys": _ham_keys, "values": _ham_values, "get": _ham_get,
    "merge": _ham_merge, "pick": _ham_pick, "omit": _ham_omit,
}
_NHOM_NGAY: dict[str, Callable[..., Any]] = {
    "date_parse": _ham_date_parse, "date_format": _ham_date_format,
    "date_add": _ham_date_add, "date_diff": _ham_date_diff,
}

#: ⭐ Bang DONG cua §6.3 — 49 ten, bay nhom, va khong gi khac.
#:
#: Cam thang vao `ChinhSach.ham` cua phuong ngu §6. `bieu_thuc.py` (hop dong
#: `timeout_expr`) KHONG duoc dung bang nay: no cam goi ham, va dieu cam do la
#: dieu kien de con so tran chi phi ton tai truoc khi ai do tieu tien.
#:
#: ⛔ Them mot nhom vao day la mot QUYET DINH ve be mat, khong phai mot lan
#:   them ham. `test_1765` so bang nay voi van ban spec theo ca hai chieu.
BANG_HAM: dict[str, Callable[..., Any]] = {
    **_NHOM_CHUOI, **_NHOM_SO, **_NHOM_KIEU, **_NHOM_JSON,
    **_NHOM_DANH_SACH, **_NHOM_OBJECT, **_NHOM_NGAY,
}
