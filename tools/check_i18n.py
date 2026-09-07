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
#
# 🔴 Hai tệp cuối KHÁC HẲN ba tệp trên, và lý do phải ghi ra: chúng chứa **dữ
#    liệu ngữ âm tiếng Việt**, không phải chuỗi giao diện.
#
#    `text_pipeline.py` giữ bảng thay ký hiệu (" phần trăm", " đồng") và bảng số
#    đọc thành chữ ("một", "hai", "mươi", "lăm"). `tu_dien.py` giữ bảng phát âm
#    ("AI" -> "ây ai").
#
#    Chúng là **đầu vào của một model đọc tiếng Việt**. Bọc `_()` rồi dịch sang
#    tiếng Anh nghĩa là ngày một người dùng đặt giao diện tiếng Anh, model sẽ
#    đọc "percent" và "one hundred" **trong một câu tiếng Việt** — tức chính
#    phép dịch làm hỏng giọng đọc.
#
#    Đây là cùng loại với hai ngoại lệ đã có trong `_khong_phai_cau()` (bảng ký
#    tự, `notes=`): thu hẹp phạm vi ĐẾM cho thứ không bao giờ là chuỗi giao
#    diện, không phải nới bánh cóc.
#
# ⚠️ Hệ quả phải biết: một chuỗi giao diện THẬT lỡ đặt vào hai tệp này sẽ không
#    được đếm. Nên đừng đặt — thông điệp lỗi của LTT VOICE nằm ở
#    `apps/ltt_voice/features.py` và `audio_input.py`, cả hai đều được đếm.
BO_QUA_FILE = ("server/admin.py", "server/admin_api.py",
               "server/templates/admin", "server/routes/admin",
               "apps/ltt_voice/text_pipeline.py", "apps/ltt_voice/tu_dien.py")

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

    3. **Lời nhắc gửi cho model.** Một chuỗi nằm ở khoá `"content"` của một dict
       có cả khoá `"role"` là **một tin nhắn LLM**, không phải chữ trên màn hình.
       Nhận theo *hình dạng* chứ không theo tên hàm hay tên tệp: hình dạng
       `{"role": …, "content": …}` là hợp đồng của cửa chat, và nó không đổi
       theo chỗ đặt.

       ⛔ Bọc nó vào `_()` sai theo hướng **nguy hiểm hơn** cả hai dạng trên: nó
          làm model nhận một lời nhắc **khác nhau tuỳ ngôn ngữ giao diện**. Một
          khách để giao diện tiếng Anh sẽ được chọn giọng theo một bộ luật khác
          — tức một thiết lập hiển thị lặng lẽ đổi **hành vi** của sản phẩm.

    Đây là thu hẹp phạm vi ĐẾM, không phải nới bánh cóc: ba dạng trên không bao
    giờ là chuỗi giao diện, nên đếm chúng chỉ tạo áp lực bọc bừa.
    """
    if not gia_tri.strip():
        return True
    if not re.search(r"\s", gia_tri) and not _CHU_ASCII.search(gia_tri):
        return True
    p = cha.get(id(node))
    if isinstance(p, ast.keyword) and p.arg == "notes":
        return True
    if _la_tin_nhan_model(node, cha):
        return True
    return False


def _la_tin_nhan_model(node: ast.AST, cha: dict) -> bool:
    """`node` có nằm trong giá trị của khoá `"content"` (dict có cả `"role"`)?

    ⛔ PHẢI LEO NHIỀU TẦNG, KHÔNG CHỈ NHÌN CHA TRỰC TIẾP. Bản đầu chỉ so cha và
       **không bắt được gì**: một lời nhắc thật luôn được ghép từ nhiều mảnh
       (`f"..." "..."`), nên cha trực tiếp của mỗi mảnh là `JoinedStr`/`BinOp`,
       không phải `Dict`. Nhìn đúng một tầng là nhìn nhầm chỗ.
    """
    con = node
    for _ in range(8):
        p = cha.get(id(con))
        if p is None:
            return False
        if isinstance(p, ast.Dict):
            khoa = [k.value if isinstance(k, ast.Constant) else None for k in p.keys]
            if "role" not in khoa:
                return False
            for k, v in zip(p.keys, p.values):
                if v is con and isinstance(k, ast.Constant) and k.value == "content":
                    return True
            return False
        if not isinstance(p, (ast.JoinedStr, ast.BinOp, ast.FormattedValue,
                              ast.Expr, ast.Tuple, ast.Starred)):
            return False
        con = p
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


# Chu thich cua `dem_template` noi ro y dinh: "Dong co goi ham dich thi coi
# nhu da xu ly". Nen nhan loi goi dich o BAT KY dau tren dong, khong chi sau
# `{{` hay `{% trans`. Hai truong hop that da lam banh cong bao DO cho mot
# template LAM DUNG (`vps_chi_tiet.html`, 24/08): loi goi dich nam trong mot
# the `{% for %}`, va the do vat qua HAI DONG nen dong sau khong con `{%`.
# Bao do cho mot template dung thi nguoi sau se "sua" bang cach boc them mot
# lop `_()` nua hoac be template cho vua long mot phep do.
_JINJA_DICH = re.compile(r"_[nt]?\(|\{%-?\s*trans")


def dem_template(f: pathlib.Path) -> int:
    t = f.read_text(encoding="utf-8")
    t = re.sub(r"\{#.*?#\}", "", t, flags=re.S)          # chú thích jinja
    # Chú thích HTML và CSS/JS: KHÔNG bao giờ render ra cho người dùng, nên đếm
    # chúng chỉ tạo áp lực viết chú thích không dấu — tức là làm mã khó đọc hơn
    # để làm vừa lòng một phép đo. Cố ý chỉ bỏ CHÚ THÍCH: chuỗi trong
    # `content:"…"` của CSS thì có hiện ra, và nó vẫn được đếm.
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    n_thieu = 0
    for dong in t.splitlines():
        if not VN.search(dong):
            continue
        # Chú thích JS một dòng cũng không render ra, đúng cùng lý do với
        # `/* */` ở trên. Chỉ nhận khi `//` đứng ĐẦU dòng (sau khoảng trắng):
        # cắt `//` ở giữa dòng sẽ ăn mất `https://` và mọi URL trong template.
        if dong.lstrip().startswith("//"):
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
