"""Hợp đồng giao diện `lttvideo` — **ba lỗi trình duyệt bắt được, test thì không.**

Ngày 07/09 `A-4` mở trang bằng Playwright thật và tìm ra ba lỗi liên tiếp, cả ba
đều nằm trên đường người dùng đi, và **không phép kiểm nào đỏ**:

| # | Triệu chứng | Gốc |
|---|---|---|
| 1 | `/lttvideo` trả **404** | `surface="admin"` ⇒ `access_middleware.py:71` chặn mọi `role != "admin"` |
| 2 | `/lttvideo` trả **500** | `require_login` trả **chuỗi**; route đọc `user.id` |
| 3 | Bấm *Tạo video* → **404 `/tao`** | `action="tao"` là URL tương đối; trang ở `/lttvideo` (không gạch chéo) nên nó giải ra `/tao` |

⭐ Lỗi **2** nguy hiểm hơn cả 404: cạnh `user.id` (nổ to) là
   `getattr(user, "vai", "nhan_vien")` (**không nổ gì**). Nó trả về mặc định, mặc
   định nằm trong danh sách cho phép, nên cổng quyền luôn nói *có* — chấm trên
   hằng số của chính nó. Và bộ test cũ xanh vì nó truyền thẳng `vai="nhan_vien"`
   thay vì đi qua một `User` thật.

⇒ Bài học chung: mọi phép kiểm dưới đây đo **thứ thật** — chữ ký hàm, cột CSDL,
  HTML đã dựng — chứ không đo một đối tượng giả do chính phép kiểm nặn ra.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from apps.lttvideo import kha_nang, routes

_TEMPLATE = (pathlib.Path(inspect.getsourcefile(routes)).parent
             / "templates" / "lttvideo.html")


# ── 1. Cong `surface` cua nen tang ──────────────────────────────────────────

def test_manifest_khai_surface_admin_va_tai_lieu_noi_dung_hau_qua():
    """`surface="admin"` không phải "ẩn khỏi trang chủ" — nó là **404** với mọi
    tài khoản `role != "admin"`. Chú thích nói sai điều này khiến người sau đi
    tìm lỗi ở app trong khi cổng nằm ở nền tảng."""
    from apps.lttvideo.manifest import MANIFEST

    assert MANIFEST.surface == "admin"
    ma = pathlib.Path(inspect.getsourcefile(
        __import__("apps.lttvideo.manifest", fromlist=["x"]))).read_text(
            encoding="utf-8")
    assert "404" in ma, "chu thich manifest phai noi ro hau qua cua surface"


# ── 2. `require_login` tra CHUOI, khong tra User ────────────────────────────

def test_require_login_van_tra_ve_chuoi():
    """⭐ Sự thật độc lập. Nếu thượng nguồn đổi sang trả `User` thì phép kiểm này
    đỏ, và ta biết `_nguoi_dung` có thể bỏ đi — thay vì đoán."""
    from server.auth.session import require_login

    # ⚠️ `server/auth/session.py` co `from __future__ import annotations`, nen
    #    chu kieu la CHUOI `'str'` chu khong phai lop `str`. Doc thu that.
    assert inspect.signature(require_login).return_annotation in (str, "str")


def test_route_KHONG_doc_thuoc_tinh_tu_gia_tri_cua_require_login():
    """Không route nào được đối xử với giá trị `Depends(require_login)` như một
    đối tượng. Đọc AST: tìm tham số nhận `require_login`, rồi xem tên ấy có bị
    truy cập thuộc tính ở đâu trong thân hàm không."""
    cay = ast.parse(pathlib.Path(inspect.getsourcefile(routes)).read_text(
        encoding="utf-8"))
    loi = []
    for ham in ast.walk(cay):
        if not isinstance(ham, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        a = ham.args
        ten_dinh_danh = set()
        # Ghep tham so voi mac dinh cua no: `args` can le ve PHAI, `kwonlyargs`
        # thi khop 1-1 voi `kw_defaults`.
        cap = list(zip(a.args[len(a.args) - len(a.defaults):], a.defaults,
                       strict=True))
        cap += list(zip(a.kwonlyargs, a.kw_defaults, strict=True))
        for arg, mac_dinh in cap:
            if (isinstance(mac_dinh, ast.Call)
                    and isinstance(mac_dinh.func, ast.Name)
                    and mac_dinh.func.id == "Depends"
                    and any(isinstance(x, ast.Name)
                            and x.id == "require_login" for x in mac_dinh.args)):
                ten_dinh_danh.add(arg.arg)
        for n in ast.walk(ham):
            if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id in ten_dinh_danh):
                loi.append(f"{ham.name}: {n.value.id}.{n.attr}")
    assert not loi, ("doc thuoc tinh tu gia tri cua require_login (no la mot "
                     f"CHUOI): {loi}")


def test_co_ham_giai_ra_user_that():
    from server.deps import user_hien_tai

    assert callable(routes._nguoi_dung)
    cay = ast.parse(inspect.getsource(routes._nguoi_dung))
    ten = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "user_hien_tai" in ten
    # `Request` phai co chu kieu, neu khong FastAPI hieu no la query param.
    assert (inspect.signature(user_hien_tai).parameters["request"].annotation
            is not inspect.Parameter.empty)


# ── 3. Tu vung vai la tu vung cua NEN TANG ──────────────────────────────────

def test_vai_duoc_dung_chi_chua_gia_tri_CO_THAT_trong_cot_role():
    """`platform_core/models.py` khai `role` với hai giá trị `admin`/`user`.
    Một vai ngoài tập ấy là một vai không ai có, nên nó hoặc luôn từ chối (vô
    hại nhưng chết) hoặc — như bản đầu — luôn cho qua vì nó là giá trị mặc định
    của một `getattr`."""
    assert kha_nang.VAI_DUOC_DUNG <= {"admin", "user"}


def _hang_chuoi_khong_ke_docstring(cay: ast.AST) -> set:
    """Hằng chuỗi **đang được dùng**, bỏ qua docstring.

    ⭐ Phân biệt này là bắt buộc chứ không phải cầu kỳ: chú thích ở
       `routes._nguoi_dung` và `kha_nang.VAI_DUOC_DUNG` **trích lại** chuỗi sai
       cũ để kể vì sao nó sai. Một bộ dò quét văn bản sẽ báo động đúng vào đoạn
       giải thích nó — cái bẫy đã dính bốn lần ở kho này
       (`docs/BAY_TRONG_CONG_CHAT_LUONG.md`).
    """
    docstring = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)):
            than = getattr(n, "body", None) or []
            if (than and isinstance(than[0], ast.Expr)
                    and isinstance(than[0].value, ast.Constant)
                    and isinstance(than[0].value.value, str)):
                docstring.add(id(than[0].value))
    return {n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstring}


def test_khong_con_tu_vung_tu_che_trong_ma_app():
    """`"nhan_vien"` không tồn tại ở bất cứ đâu khác trong nền tảng, nên nó
    không được là một giá trị mã app **dùng** — chỉ được là một giá trị mã app
    **kể lại** trong docstring."""
    goc = pathlib.Path(inspect.getsourcefile(routes)).parent
    for tep in sorted(goc.glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        assert "nhan_vien" not in _hang_chuoi_khong_ke_docstring(cay), (
            f"{tep.name} con DUNG hang 'nhan_vien'")


def test_tu_kiem_bo_loc_docstring():
    """⛔ Đối chứng cho chính bộ lọc trên: nếu nó lọc nhầm cả hằng đang dùng thì
    phép kiểm kia xanh vĩnh viễn và không canh gì cả."""
    nguon = '"""noi ve abc."""' + chr(10) + 'x = "abc"' + chr(10)
    assert "abc" in _hang_chuoi_khong_ke_docstring(ast.parse(nguon))

    chi_docstring = '"""chi noi ve abc thoi."""' + chr(10)
    assert "chi noi ve abc thoi." not in _hang_chuoi_khong_ke_docstring(
        ast.parse(chi_docstring))


def test_route_doc_role_chu_khong_doc_vai():
    """Cột thật tên `role`. Đọc `.vai` là đọc một thuộc tính không tồn tại — và
    `getattr` kèm mặc định biến việc đó thành im lặng."""
    cay = ast.parse(inspect.getsource(routes))
    for n in ast.walk(cay):
        if isinstance(n, ast.Attribute):
            assert n.attr != "vai", "route van doc `.vai`"
    assert "vai" not in _hang_chuoi_khong_ke_docstring(cay), (
        "route van truyen chuoi 'vai' cho getattr")
    assert "role" in _hang_chuoi_khong_ke_docstring(cay), (
        "route khong doc cot `role` cua nen tang")


# ── 4. Bieu mau phai post dung cho ────────────────────────────────────────

def test_form_action_KHONG_phai_duong_dan_tuong_doi():
    """🔴 `action="tao"` giải ra `/tao` khi trang ở `/lttvideo` (không gạch
    chéo) — và đó là URL mà thanh điều hướng dùng. Bấm nút ra 404."""
    html = _TEMPLATE.read_text(encoding="utf-8")
    import re

    for m in re.finditer(r'action="([^"]*)"', html):
        gia_tri = m.group(1)
        assert gia_tri.startswith("/") or gia_tri.startswith("{{"), (
            f"action tuong doi: {gia_tri!r}")


def test_route_truyen_app_de_template_dung_duoc_route_prefix():
    """Template viết `{{ app.route_prefix }}`; thiếu `app` trong context thì
    Jinja dựng ra `action="/tao"` — im lặng, và sai."""
    ma = inspect.getsource(routes.trang_chinh)
    assert '"app": MANIFEST' in ma
    assert '"nav": MANIFEST.slug' in ma


# ── 5. Nhanh mo rong prompt van dung duoc khi nang luc mo ──────────────────

def _yeu_cau_gia():
    """`Request` toi thieu — `base.html` doc `request.scope`, nen `None` khong du."""
    from starlette.requests import Request

    return Request({"type": "http", "method": "GET", "path": "/lttvideo",
                    "headers": [], "query_string": b"", "scheme": "http",
                    "server": ("127.0.0.1", 0), "root_path": "", "session": {}})


def _dung(duoc_mo_rong: bool) -> str:
    from server.templating import templates

    from apps.lttvideo.manifest import MANIFEST

    return templates.env.get_template("lttvideo.html").render(
        request=_yeu_cau_gia(), app=MANIFEST, nav=MANIFEST.slug, user=None,
        csrf_token="x", ti_le=routes.TI_LE, do_dai=routes.DO_DAI_S,
        uoc_gia=routes._uoc_gia(), duoc_dung=True, ly_do_tu_choi="",
        duoc_mo_rong=duoc_mo_rong, video_gan_day=[])


def test_template_dung_duoc_khi_BAT_o_tick():
    """Ô tick hiện chưa hiện (`kha_nang` đóng), nên trình duyệt **không** soi
    được nhánh ấy. Dựng thẳng template với `duoc_mo_rong=True` để biết nhánh
    Jinja ấy không vỡ vào ngày đợt B mở nó."""
    html = _dung(True)
    assert 'name="mo_rong_prompt"' in html
    assert 'type="checkbox"' in html
    # Tien the: bieu mau phai post dung cho sau khi da dung that.
    assert 'action="/lttvideo/tao"' in html


def test_template_KHONG_ve_o_tick_khi_nang_luc_dong():
    """Đối chứng chiều ngược — nếu thiếu, phép kiểm trên vẫn xanh với một
    template vẽ ô tick vô điều kiện."""
    assert 'name="mo_rong_prompt"' not in _dung(False)


# ── 6. Ban kiem giao dien phai co lop chan production ─────────────────────

def test_harness_khong_the_cham_CSDL_that():
    """Máy này LÀ máy chủ production (`C:\\LTTPlatform`), cổng 8100 đang phục vụ
    khách. Bản kiểm phải tự dựng sqlite trong thư mục tạm."""
    goc = pathlib.Path(inspect.getsourcefile(routes)).parents[2]
    ma = (goc / "tools" / "lttvideo_browser_server.py").read_text(
        encoding="utf-8")
    cay = ast.parse(ma)
    goi = {n.func.attr for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "mkdtemp" in goi, "khong dung thu muc tam => co the cham CSDL that"
    assert "sqlite:///" in ma


@pytest.mark.parametrize("cong", ["8100", "8000"])
def test_harness_khong_chay_o_cong_dang_phuc_vu_that(cong):
    goc = pathlib.Path(inspect.getsourcefile(routes)).parents[2]
    ma = (goc / "tools" / "lttvideo_browser_server.py").read_text(
        encoding="utf-8")
    cay = ast.parse(ma)
    for n in ast.walk(cay):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "add_argument":
            for kw in n.keywords:
                if kw.arg == "default" and isinstance(kw.value, ast.Constant):
                    assert str(kw.value.value) != cong
