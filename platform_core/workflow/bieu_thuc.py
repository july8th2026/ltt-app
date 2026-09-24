"""Bieu thuc tran thoi gian — tap toan tu CO DINH tren `params` cua node.

Nguon: `25_26 §2.6` + rang buoc `Q5`.

## Van de no giai

Video 5 giay va video 60 giay dang chung mot tran `max_runtime_s` TINH. Hoac
tran qua rong (job treo giu slot rat lau), hoac qua chat (job dai bi giet oan).
Windmill cho `timeout` la mot bieu thuc; day la ban co rang buoc cua LTT.

## ⛔ VI SAO KHONG DUNG `eval()`

`eval()` tren mot chuoi do app khai la mot cua thi hanh ma tuy y trong tien
trinh nen tang. App la ma cua ta, nhung mot cua nhu vay khong co cach nao
"dung dan" — no chi cho ta mot ly do de tin. Bo tinh nay doc **AST** va tu
choi moi nut khong nam trong danh sach cho phep.

## ⭐ RANG BUOC THUC SU (`Q5`) — va no khong phai chuyen bao mat

Bieu thuc phai tinh duoc **luc validate**, vi `WF-501` doi tran chi phi TAT
DINH truoc khi chay. Nen no:

    CHI duoc doc `params` cua CHINH node do
    KHONG duoc doc ket qua buoc khac   (chua ton tai luc validate)
    KHONG duoc goi ham                 (khong tat dinh, khong tinh truoc duoc)

⇒ Hai lenh cam sau khong phai de chan ke xau. Chung la dieu kien de con so
  tran **ton tai** truoc khi ai do tieu tien.

## ⭐ RUOT DUNG CHUNG, HOP DONG KHONG DUNG CHUNG

Bo duyet AST da chuyen sang `chinh_sach.py` de ngon ngu bieu thuc §6 dung lai
duoc **may**. Mo-dun nay giu nguyen **hop dong**: `NGHIEM` duoi day la ban khai
day du cua ba dieu cam tren, va no la mot **bang doc duoc** — noi long mot o
trong bang la mot dong diff, khong phai mot phuong thuc bi ghi de o dau do.

⛔ Ngon ngu §6 doi nguoc ca ba dieu cam (doc `nodes.<id>.output`, co bang ham,
  tinh luc chay). No phai mang **chinh sach cua rieng no**. Noi long `NGHIEM`
  de phuc vu §6 la pha bao dam ve tien cua `timeout_expr`.
"""
from __future__ import annotations

import ast
from collections.abc import Callable
from typing import Any

from platform_core.workflow.chinh_sach import (
    ChinhSach,
    kiem_cay,
    ten_duoc_doc,
    tinh_cay,
)

__all__ = ["LoiBieuThuc", "NGHIEM", "kiem_bieu_thuc", "tinh_bieu_thuc",
           "tham_so_dung"]


class LoiBieuThuc(ValueError):
    """Bieu thuc khong hop le. Mang cau noi ro SAI O DAU, khong chi 'invalid'."""


#: Toan tu SO HOC duoc phep. `Pow` co y KHONG nam day: `2 ** 10**9` treo tien
#: trinh trong khi moi nut deu "hop le" — mot bieu thuc tat dinh van co the la
#: mot bieu thuc khong bao gio tra loi.
_NHI_PHAN: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
}
_MOT_NGOI: dict[type, Callable[[Any], Any]] = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}
_SO_SANH: dict[type, Callable[[Any, Any], Any]] = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}

#: Ham duy nhat duoc phep, va chung la ham CHON chu khong phai ham TINH:
#: chung khong the tra ve gia tri ngoai tap dau vao.
_HAM: dict[str, Callable[..., Any]] = {"min": min, "max": max}

#: ⭐ HOP DONG CUA `timeout_expr`, khai bang bang chu khong bang ma.
#:
#: Doc bang nay la doc du ba dieu cam o docstring dau tep:
#:   `ham` chi co ham CHON        ⇒ khong ham nao tra gia tri ngoai tap dau vao
#:   `nut_cho_phep` khong co `Attribute`/`Subscript`/`ListComp`/`Lambda`
#:                               ⇒ khong duong nao ra khoi tap gia tri da khai
#:   ten phai nam trong `params` ⇒ khong doc duoc ket qua buoc khac
#:
#: ⛔ Them mot o vao bang nay la doi hop dong ve tien. `test_1761` chup lai
#:   toan bo hanh vi cua bang nay; sua bang ma khong sua chu dich la lam do.
NGHIEM = ChinhSach(
    ten="timeout_expr",
    lop_loi=LoiBieuThuc,
    nut_cho_phep=frozenset({
        ast.Expression, ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp,
        ast.Compare, ast.BoolOp, ast.IfExp, ast.Call,
    }),
    kieu_hang_so=(bool, int, float),
    nhi_phan=_NHI_PHAN,
    mot_ngoi=_MOT_NGOI,
    so_sanh=_SO_SANH,
    logic=frozenset({ast.And, ast.Or}),
    ham=_HAM,
    cho_tham_so_ten=False,
    chia_bang_0=frozenset({ast.Div, ast.FloorDiv, ast.Mod}),
    van_ban={
        "cu_phap": "cu phap {ten} khong duoc phep",
        "hang_so": "hang so phai la so, gap {kieu}",
        "ten": "ten {ten} khong phai tham so cua tool (co: {co})",
        "khong_co_ten": "khong co tham so nao",
        "nhi_phan": ("toan tu {ten} khong duoc phep "
                     "(** bi cam: no tinh duoc ma khong bao gio tra loi)"),
        "nhi_phan_tinh": "toan tu {ten} khong duoc phep",
        "mot_ngoi": "toan tu {ten} khong duoc phep",
        "so_sanh": "phep so sanh {ten} khong duoc phep",
        "logic": "phep logic khong duoc phep",
        "goi": "chi duoc goi {ds}, khong goi gi khac",
        "goi_tinh": "chi duoc goi {ds}",
        "tu_khoa": "khong dung tham so co ten",
        "khong_co_gia_tri": "tham so {ten} khong co gia tri",
        "chia_0": "chia cho 0",
        # ⭐ Ba cau duoi CHO `min`/`max`. `NGHIEM` co `ast.Call`, nen no di qua
        #    cung doan goi ham voi ngon ngu §6 — va truoc do `min()` hay
        #    `min(a)` voi `a` la so nem `TypeError` THO qua dau `tinh_bieu_thuc`
        #    ra toi tang nap registry. Mot tran `max_runtime_s` khong duoc
        #    phep ngo ra bang mot loi cua Python.
        #    ⛔ `loi_nguoi_dung` cua `NGHIEM` de RONG: `min`/`max` la ham dung
        #    san, khong co lop loi rieng noi cau cho nguoi khai doc.
        "sai_tham_so": "goi {ten} sai so tham so ({msg})",
        "ham_loi": "{msg}",
        "ham_hong": "ham {ten} that bai khi tinh",
    },
)


def _phan_tich(bieu_thuc: str) -> ast.Expression:
    try:
        return ast.parse(bieu_thuc, mode="eval")
    except SyntaxError as loi:
        raise LoiBieuThuc(f"khong phan tich duoc: {loi.msg}") from loi


def tham_so_dung(bieu_thuc: str) -> set[str]:
    """Tap ten tham so ma bieu thuc doc toi. Rong neu bieu thuc rong."""
    if not (bieu_thuc or "").strip():
        return set()
    return ten_duoc_doc(ast.parse(bieu_thuc, mode="eval"), NGHIEM)


def kiem_bieu_thuc(bieu_thuc: str, params_schema: dict) -> None:
    """Kiem LUC NAP. Sai thi nem `LoiBieuThuc` — khong doi toi luc chay.

    ⭐ Day la ca diem cua viec khai bang bieu thuc thay vi bang mot ham: mot
       bang du lieu thi registry **kiem duoc luc nap**; mot ham thi khong kiem
       duoc gi cho toi khi no chay — va cho no chay la cho tieu tien cua khach.
    """
    if not (bieu_thuc or "").strip():
        return
    kiem_cay(_phan_tich(bieu_thuc), NGHIEM, set(params_schema or {}))


def tinh_bieu_thuc(bieu_thuc: str, params: dict) -> float:
    """Tinh gia tri. Goi `kiem_bieu_thuc` truoc do o tang nap.

    ⚠️ Van kiem lai o day chu khong tin tang tren: mot ham "chi duoc goi sau
       khi da kiem" la mot dieu kien khong ai cuong che duoc, va no se bi goi
       thang tu mot duong moi nao do.
    """
    if not (bieu_thuc or "").strip():
        raise LoiBieuThuc("bieu thuc rong")
    cay = _phan_tich(bieu_thuc)
    kiem_cay(cay, NGHIEM, set(params or {}))
    moi_truong: dict[str, Any] = {}
    for k, v in (params or {}).items():
        if isinstance(v, bool) or isinstance(v, (int, float)):
            moi_truong[k] = v
    return tinh_cay(cay, NGHIEM, moi_truong)
