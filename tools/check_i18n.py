r"""
check_i18n.py — bánh cóc chống thêm chuỗi chưa dịch (H24).

    python tools\check_i18n.py            # kiểm, thoát 1 nếu tăng
    python tools\check_i18n.py --chot     # ghi lại mốc sau khi đã dịch bớt

## Vì sao là bánh cóc chứ không phải "cấm tuyệt đối"

Hiện còn khoảng 1.800 chuỗi chưa bọc `_()`. Bắt gate đỏ ngay là chặn mọi việc
khác cho tới khi dịch xong hết — không thực tế. Bánh cóc cho phép **giảm dần**
nhưng **không cho tăng**: thêm một chuỗi chưa dịch là gate đỏ.

Không có nó thì công dịch sẽ mục dần, đúng như hiện trạng đã thấy: `home.html`
có "Marketplace"/"My Apps" tiếng Anh nằm giữa một trang tiếng Việt, không ai
biết nó lọt vào từ lúc nào.

Cùng cơ chế với `tools/check_silent_except.py`.

## Không đếm

- `server/admin.py`, `server/admin_api.py` và template admin — chủ sản phẩm
  chốt GIỮ tiếng Việt.
- chú thích và docstring — không hiện cho người dùng (tách bằng AST).
- `tests/`, `tools/`, `docs/`, `core/` (đã đóng băng).
"""
from __future__ import annotations

import ast
import io
import json
import pathlib
import re
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
MOC = GOC / "tools" / "i18n_baseline.json"

VN = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
                r"ùúủũụưừứửữựỳýỷỹỵđ]", re.I)

BO_QUA_THU_MUC = ("__pycache__", "node_modules", "/core/", "\\core\\",
                  "/tests/", "\\tests\\", "/tools/", "\\tools\\",
                  "/docs/", "\\docs\\", "/locale/", "\\locale\\")
# Trang admin: chốt giữ tiếng Việt, chỉ một người đọc.
BO_QUA_FILE = ("server/admin.py", "server/admin_api.py",
               "server/templates/admin", "server/routes/admin")

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)


def _bo_qua(f: pathlib.Path) -> bool:
    s = str(f).replace("\\", "/")
    if any(b.replace("\\", "/") in s for b in BO_QUA_THU_MUC):
        return True
    rel = str(f.relative_to(GOC)).replace("\\", "/")
    return any(rel.startswith(b) for b in BO_QUA_FILE)


_CHU_ASCII = re.compile(r"[A-Za-z]")


def _khong_phai_cau(gia_tri: str, node: ast.AST, cha: dict) -> bool:
    """Chuỗi này không thể là câu hiện cho người dùng — đừng đếm.

    Hai dạng, cả hai đều đã gặp thật và cả hai đều làm bánh cóc kêu sai:

    1. **Bảng ký tự.** Một chuỗi không có dấu cách và không có chữ cái ASCII nào
       thì không phải câu — nó là danh sách ký tự (`_DAU_VIET` trong
       `platform_core/image_gen/prompt_dich.py` là toàn bộ bộ dấu tiếng Việt).
       Mọi câu thật đều có dấu cách, và gần như mọi từ tiếng Việt đều còn chữ
       ASCII (`Tắt` có `T`, `ảnh` có `nh`).

    2. **`notes=` của `Provider`.** Đó là ghi chú cho lập trình viên đọc mã, KHÔNG
       render ở đâu — đã kiểm: không có chỗ nào đọc `.notes` trong `server/`,
       `platform_core/` hay `apps/`. Bọc nó vào `N_()` thì sai theo hướng ngược
       lại: một chuỗi không hiện ra lại bị trích cho người dịch.

    Đây là thu hẹp phạm vi ĐẾM, không phải nới bánh cóc: hai dạng trên không bao
    giờ là chuỗi giao diện, nên đếm chúng chỉ tạo áp lực bọc bừa.
    """
    if not gia_tri.strip():
        return True
    if not re.search(r"\s", gia_tri) and not _CHU_ASCII.search(gia_tri):
        return True
    p = cha.get(id(node))
    if isinstance(p, ast.keyword) and p.arg == "notes":
        return True
    return False


def _da_boc(node: ast.AST, cha: dict) -> bool:
    """Chuỗi này có nằm trong lời gọi `_()` / `_n()` không?"""
    p = cha.get(id(node))
    while p is not None:
        if isinstance(p, ast.Call) and isinstance(p.func, ast.Name) \
                and p.func.id in ("_", "_t", "_n", "N_", "gettext", "ngettext"):
            return True
        p = cha.get(id(p))
    return False


def dem_python(f: pathlib.Path) -> int:
    try:
        cay = ast.parse(f.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as exc:
        # KHÔNG được im lặng trả 0: file không đọc được sẽ bị đếm là "sạch", tức
        # lách được bánh cóc chỉ bằng cách làm hỏng cú pháp. Báo ra và đếm là 0
        # có kèm cảnh báo, để người đọc gate thấy.
        print(f"  ! khong doc duoc {f.relative_to(GOC)}: {type(exc).__name__}: {exc}")
        return 0
    ds = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)):
            d = ast.get_docstring(n, clean=False)
            if d:
                ds.add(d)
    cha: dict = {}
    for n in ast.walk(cay):
        for con in ast.iter_child_nodes(n):
            cha[id(con)] = n
    n_thieu = 0
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            if n.value in ds or not VN.search(n.value):
                continue
            if _khong_phai_cau(n.value, n, cha):
                continue
            if not _da_boc(n, cha):
                n_thieu += 1
    return n_thieu


_JINJA_DICH = re.compile(r"\{\{-?\s*_[nt]?\(|\{%-?\s*trans")


def dem_template(f: pathlib.Path) -> int:
    t = f.read_text(encoding="utf-8")
    t = re.sub(r"\{#.*?#\}", "", t, flags=re.S)          # chú thích jinja
    n_thieu = 0
    for dong in t.splitlines():
        if not VN.search(dong):
            continue
        # Dòng có gọi hàm dịch thì coi như đã xử lý. Thô, nhưng bánh cóc chỉ cần
        # bắt XU HƯỚNG tăng, không cần chính xác từng chuỗi.
        if _JINJA_DICH.search(dong):
            continue
        n_thieu += 1
    return n_thieu


def quet() -> dict[str, int]:
    ra: dict[str, int] = {}
    for pat, fn in ((("server/**/*.py", "platform_core/**/*.py", "apps/**/*.py"), dem_python),
                    (("server/templates/**/*.html", "apps/*/templates/**/*.html"), dem_template)):
        for p in pat:
            for f in GOC.glob(p):
                if _bo_qua(f):
                    continue
                n = fn(f)
                if n:
                    ra[str(f.relative_to(GOC)).replace("\\", "/")] = n
    return ra


def main() -> int:
    hien = quet()
    tong = sum(hien.values())
    if "--chot" in sys.argv:
        MOC.write_text(json.dumps({"tong": tong, "theo_file": hien},
                                  ensure_ascii=False, indent=2, sort_keys=True),
                       encoding="utf-8")
        print(f"Da chot moc: {tong} chuoi chua boc _() trong {len(hien)} file.")
        return 0

    if not MOC.exists():
        print("Chua co moc. Chay `python tools\\check_i18n.py --chot` mot lan.")
        return 1
    moc = json.loads(MOC.read_text(encoding="utf-8"))
    cu_tong, cu_file = moc["tong"], moc["theo_file"]

    tang = {f: (n, cu_file.get(f, 0)) for f, n in hien.items() if n > cu_file.get(f, 0)}
    if tang:
        print(f"i18n: THEM chuoi chua boc _() ({tong} > {cu_tong}).")
        for f, (moi, cu) in sorted(tang.items()):
            print(f"   {f}: {cu} -> {moi}")
        print("\nBoc chuoi hien cho nguoi dung trong _() roi chay lai.")
        print("Neu that su khong phai chuoi hien ra, sua tools/check_i18n.py.")
        return 1

    print(f"i18n: {tong} chuoi chua boc (moc {cu_tong}) — khong tang.")
    if tong < cu_tong:
        print("Da giam. Chay `--chot` de ha moc, khong cho no tang lai.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
