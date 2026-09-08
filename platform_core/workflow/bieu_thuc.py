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
"""
from __future__ import annotations

import ast
from typing import Any

__all__ = ["LoiBieuThuc", "kiem_bieu_thuc", "tinh_bieu_thuc", "tham_so_dung"]


class LoiBieuThuc(ValueError):
    """Bieu thuc khong hop le. Mang cau noi ro SAI O DAU, khong chi 'invalid'."""


#: Toan tu SO HOC duoc phep. `Pow` co y KHONG nam day: `2 ** 10**9` treo tien
#: trinh trong khi moi nut deu "hop le" — mot bieu thuc tat dinh van co the la
#: mot bieu thuc khong bao gio tra loi.
_NHI_PHAN = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)
_MOT_NGOI = (ast.UAdd, ast.USub)
_SO_SANH = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)
_LOGIC = (ast.And, ast.Or)

#: Ham duy nhat duoc phep, va chung la ham CHON chu khong phai ham TINH:
#: chung khong the tra ve gia tri ngoai tap dau vao.
_HAM = {"min": min, "max": max}


def _kiem_nut(nut: ast.AST, cho_phep: set[str]) -> None:
    if isinstance(nut, ast.Expression):
        return _kiem_nut(nut.body, cho_phep)

    if isinstance(nut, ast.Constant):
        if isinstance(nut.value, bool) or isinstance(nut.value, (int, float)):
            return
        raise LoiBieuThuc(
            f"hang so phai la so, gap {type(nut.value).__name__}")

    if isinstance(nut, ast.Name):
        if nut.id in _HAM:
            return
        if nut.id not in cho_phep:
            raise LoiBieuThuc(
                f"ten {nut.id!r} khong phai tham so cua tool "
                f"(co: {sorted(cho_phep) or 'khong co tham so nao'})")
        return

    if isinstance(nut, ast.BinOp):
        if not isinstance(nut.op, _NHI_PHAN):
            raise LoiBieuThuc(
                f"toan tu {type(nut.op).__name__} khong duoc phep "
                "(** bi cam: no tinh duoc ma khong bao gio tra loi)")
        _kiem_nut(nut.left, cho_phep)
        return _kiem_nut(nut.right, cho_phep)

    if isinstance(nut, ast.UnaryOp):
        if not isinstance(nut.op, _MOT_NGOI):
            raise LoiBieuThuc(f"toan tu {type(nut.op).__name__} khong duoc phep")
        return _kiem_nut(nut.operand, cho_phep)

    if isinstance(nut, ast.Compare):
        for op in nut.ops:
            if not isinstance(op, _SO_SANH):
                raise LoiBieuThuc(
                    f"phep so sanh {type(op).__name__} khong duoc phep")
        _kiem_nut(nut.left, cho_phep)
        for v in nut.comparators:
            _kiem_nut(v, cho_phep)
        return

    if isinstance(nut, ast.BoolOp):
        if not isinstance(nut.op, _LOGIC):
            raise LoiBieuThuc("phep logic khong duoc phep")
        for v in nut.values:
            _kiem_nut(v, cho_phep)
        return

    if isinstance(nut, ast.IfExp):
        _kiem_nut(nut.test, cho_phep)
        _kiem_nut(nut.body, cho_phep)
        return _kiem_nut(nut.orelse, cho_phep)

    if isinstance(nut, ast.Call):
        # ⚠️ Chi cho `min`/`max` va chi khi ten la mot `Name` TRAN. `a.b()` di
        #    qua `ast.Attribute` — tu choi o duoi, va do la co y: mot chuoi
        #    thuoc tinh la duong ra khoi tap gia tri da khai.
        if not isinstance(nut.func, ast.Name) or nut.func.id not in _HAM:
            raise LoiBieuThuc(
                f"chi duoc goi {sorted(_HAM)}, khong goi gi khac")
        if nut.keywords:
            raise LoiBieuThuc("khong dung tham so co ten")
        for v in nut.args:
            _kiem_nut(v, cho_phep)
        return

    raise LoiBieuThuc(f"cu phap {type(nut).__name__} khong duoc phep")


def tham_so_dung(bieu_thuc: str) -> set[str]:
    """Tap ten tham so ma bieu thuc doc toi. Rong neu bieu thuc rong."""
    if not (bieu_thuc or "").strip():
        return set()
    cay = ast.parse(bieu_thuc, mode="eval")
    return {n.id for n in ast.walk(cay)
            if isinstance(n, ast.Name) and n.id not in _HAM}


def kiem_bieu_thuc(bieu_thuc: str, params_schema: dict) -> None:
    """Kiem LUC NAP. Sai thi nem `LoiBieuThuc` — khong doi toi luc chay.

    ⭐ Day la ca diem cua viec khai bang bieu thuc thay vi bang mot ham: mot
       bang du lieu thi registry **kiem duoc luc nap**; mot ham thi khong kiem
       duoc gi cho toi khi no chay — va cho no chay la cho tieu tien cua khach.
    """
    if not (bieu_thuc or "").strip():
        return
    try:
        cay = ast.parse(bieu_thuc, mode="eval")
    except SyntaxError as loi:
        raise LoiBieuThuc(f"khong phan tich duoc: {loi.msg}") from loi
    _kiem_nut(cay, set(params_schema or {}))


_NHI_PHAN_TINH = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
}
_SO_SANH_TINH = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}


def _tinh(nut: ast.AST, moi_truong: dict) -> Any:
    """Tinh mot nut. ⛔ KHONG dung `eval`/`exec`/`compile` — xem docstring module.

    Bo tinh de quy nay dai hon mot lenh `eval`, va do la cai gia dung. Mot
    `eval` "an toan vi da duyet AST truoc" van la mot cua thi hanh ma: no dua
    vao viec bo duyet KHONG BO SOT mot dang nut nao. Bo tinh nay thi khong co
    gi de bo sot — thu no khong biet tinh, no khong tinh.
    """
    if isinstance(nut, ast.Expression):
        return _tinh(nut.body, moi_truong)
    if isinstance(nut, ast.Constant):
        return nut.value
    if isinstance(nut, ast.Name):
        if nut.id not in moi_truong:
            raise LoiBieuThuc(f"tham so {nut.id!r} khong co gia tri")
        return moi_truong[nut.id]
    if isinstance(nut, ast.BinOp):
        pt = _NHI_PHAN_TINH.get(type(nut.op))
        if pt is None:
            raise LoiBieuThuc(f"toan tu {type(nut.op).__name__} khong duoc phep")
        phai = _tinh(nut.right, moi_truong)
        if isinstance(nut.op, (ast.Div, ast.FloorDiv, ast.Mod)) and phai == 0:
            raise LoiBieuThuc("chia cho 0")
        return pt(_tinh(nut.left, moi_truong), phai)
    if isinstance(nut, ast.UnaryOp):
        gt = _tinh(nut.operand, moi_truong)
        return +gt if isinstance(nut.op, ast.UAdd) else -gt
    if isinstance(nut, ast.Compare):
        trai = _tinh(nut.left, moi_truong)
        # `strict=True` dung nghia o day chu khong chi de qua linter: trong mot
        # `ast.Compare` hop le, `ops` va `comparators` LUON cung do dai. Neu mot
        # ngay nao do chung lech thi im lang cat bot ve ngan hon la bo qua mot
        # phep so sanh — tuc tinh ra mot con so tran KHAC voi thu da khai.
        for op, ve in zip(nut.ops, nut.comparators, strict=True):
            pt = _SO_SANH_TINH.get(type(op))
            if pt is None:
                raise LoiBieuThuc(f"phep so sanh {type(op).__name__} khong duoc phep")
            phai = _tinh(ve, moi_truong)
            if not pt(trai, phai):
                return False
            trai = phai
        return True
    if isinstance(nut, ast.BoolOp):
        gia_tri = [_tinh(v, moi_truong) for v in nut.values]
        return all(gia_tri) if isinstance(nut.op, ast.And) else any(gia_tri)
    if isinstance(nut, ast.IfExp):
        return (_tinh(nut.body, moi_truong) if _tinh(nut.test, moi_truong)
                else _tinh(nut.orelse, moi_truong))
    if isinstance(nut, ast.Call):
        if not isinstance(nut.func, ast.Name) or nut.func.id not in _HAM:
            raise LoiBieuThuc(f"chi duoc goi {sorted(_HAM)}")
        return _HAM[nut.func.id](*[_tinh(v, moi_truong) for v in nut.args])
    raise LoiBieuThuc(f"cu phap {type(nut).__name__} khong duoc phep")


def tinh_bieu_thuc(bieu_thuc: str, params: dict) -> float:
    """Tinh gia tri. Goi `kiem_bieu_thuc` truoc do o tang nap.

    ⚠️ Van kiem lai o day chu khong tin tang tren: mot ham "chi duoc goi sau
       khi da kiem" la mot dieu kien khong ai cuong che duoc, va no se bi goi
       thang tu mot duong moi nao do.
    """
    if not (bieu_thuc or "").strip():
        raise LoiBieuThuc("bieu thuc rong")
    try:
        cay = ast.parse(bieu_thuc, mode="eval")
    except SyntaxError as loi:
        raise LoiBieuThuc(f"khong phan tich duoc: {loi.msg}") from loi
    _kiem_nut(cay, set(params or {}))
    moi_truong: dict[str, Any] = {}
    for k, v in (params or {}).items():
        if isinstance(v, bool) or isinstance(v, (int, float)):
            moi_truong[k] = v
    return _tinh(cay, moi_truong)
