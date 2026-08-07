"""
H24 — bọc `_()` ở lớp Python: ba cái bẫy, khoá bằng test.

Bọc chuỗi trong Python rủi ro hơn hẳn trong template, vì chuỗi ở đó không chỉ để
hiện ra — nó còn được đem so sánh, lưu xuống CSDL, hoặc dùng làm khoá.

**Bẫy 1 — `_` bị che.** Python dùng `_` làm biến vứt đi (`for _ in ...`). Đặt tên
hàm dịch là `_` thì trong những hàm đó nó bị che, và lỗi
`UnboundLocalError: cannot access local variable '_'` chỉ nổ khi chạy ĐÚNG nhánh
ấy — không lộ lúc nạp module, không lộ ở phần lớn test. Đã xảy ra thật.
Vì vậy lớp Python dùng `_t`, template mới dùng `_`.

**Bẫy 2 — dịch chuỗi đem đi so sánh.** `'Công khai'`, `'Chưa có page'`,
`'Chưa kết nối'` được so với giá trị đã lưu. Dịch chúng là điều kiện sai lặng lẽ,
không lỗi nào báo.

**Bẫy 3 — dịch ở cấp module.** `_t()` lúc nạp module đóng băng ngôn ngữ theo
người vào đầu tiên. Chuỗi khai báo sẵn phải dùng `N_()`.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
BO = ("__pycache__", "node_modules", "core", "tests", "tools")


def _file_python():
    for pat in ("server/**/*.py", "platform_core/**/*.py", "apps/**/*.py"):
        for f in GOC.glob(pat):
            if any(b in f.parts for b in BO):
                continue
            yield f


# ── Bẫy 1: `_` bị che ────────────────────────────────────────────────────────
def test_lop_python_khong_dung_ten_gach_duoi_cho_ham_dich():
    """`from ... import _` trong .py la mot qua bom hen gio."""
    xau = []
    for f in _file_python():
        t = f.read_text(encoding="utf-8")
        if re.search(r"from platform_core\.i18n import _\s*$", t, re.M):
            xau.append(str(f.relative_to(GOC)))
    assert not xau, (
        "Nhap ham dich duoi ten `_` trong Python: `_` la bien vut di quen thuoc "
        f"nen se bi che va nem UnboundLocalError. Dung `_ as _t`. {xau}")


def test_ham_vua_goi_dich_vua_dung_gach_duoi_lam_bien():
    """Trong CUNG mot ham ma vua co `_t(...)` vua gan `_` thi van an toan, nhung
    neu ai do doi lai thanh `_(...)` la no gay ngay. Chot bang cach cam han."""
    xau = []
    for f in _file_python():
        try:
            cay = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(cay):
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            goi_ = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                       and c.func.id == "_" for c in ast.walk(n))
            gan_ = any(isinstance(c, ast.Name) and c.id == "_"
                       and isinstance(c.ctx, ast.Store) for c in ast.walk(n))
            if goi_ and gan_:
                xau.append(f"{f.relative_to(GOC)}::{n.name}")
    assert not xau, f"vua goi `_()` vua dung `_` lam bien: {xau}"


# ── Bẫy 2: chuỗi đem đi so sánh ──────────────────────────────────────────────
KHONG_DUOC_DICH = ("Công khai", "Chưa có page", "Chưa kết nối")


@pytest.mark.parametrize("chuoi", KHONG_DUOC_DICH)
def test_chuoi_dem_di_so_sanh_khong_duoc_boc(chuoi):
    """Bọc chuỗi này là điều kiện sai lặng lẽ — không lỗi nào báo."""
    xau = []
    for f in _file_python():
        t = f.read_text(encoding="utf-8")
        for mau in (f'_t("{chuoi}")', f"_t('{chuoi}')",
                    f'_("{chuoi}")', f"_('{chuoi}')"):
            if mau in t:
                xau.append(f"{f.relative_to(GOC)}: {mau}")
    assert not xau, (
        f"{chuoi!r} duoc dem di SO SANH voi gia tri da luu; dich no la dieu kien "
        f"sai lang le. {xau}")


# ── Bẫy 3: dịch ở cấp module ─────────────────────────────────────────────────
def test_khong_goi_dich_o_cap_module():
    """`_t()` luc nap module dong bang ngon ngu theo nguoi vao DAU TIEN."""
    xau = []
    for f in _file_python():
        try:
            cay = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        trong_ham = set()
        for n in ast.walk(cay):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                for c in ast.walk(n):
                    trong_ham.add(id(c))
        for n in ast.walk(cay):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in ("_t", "_") and id(n) not in trong_ham):
                xau.append(f"{f.relative_to(GOC)}:{n.lineno}")
    assert not xau, (
        "Goi ham dich o cap module: ngon ngu se bi dong bang theo lan nap dau "
        f"tien, moi nguoi deu thay ngon ngu cua nguoi vao dau tien. Dung N_(). {xau}")


# ── Log giữ tiếng Việt ───────────────────────────────────────────────────────
def test_log_khong_bi_dich():
    """Log la de CHU MAY doc. Dich log lam kho tra cuu su co, va con lam thong
    diep doi theo ngon ngu cua NGUOI DUNG cuoi cung goi vao — vo nghia."""
    xau = []
    for f in _file_python():
        try:
            cay = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(cay):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                continue
            if n.func.attr not in ("debug", "info", "warning", "error",
                                   "exception", "critical"):
                continue
            for a in n.args:
                if (isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
                        and a.func.id in ("_t", "_")):
                    xau.append(f"{f.relative_to(GOC)}:{n.lineno}")
    assert not xau, f"log bi dich: {xau}"
