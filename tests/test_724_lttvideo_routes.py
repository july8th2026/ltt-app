"""Route của `lttvideo` — CHỈ lo HTTP.

⛔ Không nghiệp vụ trong route (hợp đồng app `AGENTS.md` §8.1). Quy tắc nằm ở
   `ho_so` / `kha_nang` / `cost`; route chỉ đọc request, kiểm quyền, gọi, dựng
   phản hồi.
"""
from __future__ import annotations

import ast
import inspect
import pathlib
import re

from apps.lttvideo import routes


def test_router_KHONG_tu_viet_prefix():
    """Nền tảng gắn prefix từ `MANIFEST.route_prefix` — route tự viết là gắn hai lần."""
    ma = inspect.getsource(routes)
    assert '"/lttvideo' not in ma and "'/lttvideo" not in ma


def test_chi_dung_DUNG_BON_module_cua_server():
    """`AGENTS.md` §8.2b: app được chạm đúng bốn module của `server`, không hơn."""
    cho_phep = {
        "server.deps",
        "server.auth.session",
        "server.auth.csrf",
        "server.templating",
    }
    cay = ast.parse(inspect.getsource(routes))
    cham = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("server"):
            cham.add(n.module)
        elif isinstance(n, ast.Import):
            cham.update(a.name for a in n.names if a.name.startswith("server"))
    thua = cham - cho_phep
    assert not thua, f"chạm module ngoài hợp đồng: {sorted(thua)}"


def test_moi_route_deu_doi_dang_nhap():
    """Không có cửa nào để ngỏ."""
    cay = ast.parse(inspect.getsource(routes))
    thieu = []
    for n in ast.walk(cay):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        la_route = any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr in ("get", "post")
            for d in n.decorator_list
        )
        if not la_route:
            continue
        nguon = ast.unparse(n.args)
        if "require_login" not in nguon:
            thieu.append(n.name)
    assert not thieu, f"route không đòi đăng nhập: {thieu}"


def test_route_KHONG_chua_quy_tac_gia_hay_ho_so():
    """Nghiệp vụ phải ở `cost`/`ho_so`, không rơi vào route."""
    ma = inspect.getsource(routes)
    for cam in ("USD_MOI_GIO_GPU", "flow_shift", "guidance_scale", "t2v_2_2"):
        assert cam not in ma, f"route mang nghiệp vụ: {cam}"


def test_routes_khong_vuot_tran_hop_dong():
    """Trần cứng 900 dòng / 30 handler (`AGENTS.md` §8.2)."""
    tep = pathlib.Path(inspect.getsourcefile(routes))
    so_dong = len(tep.read_text(encoding="utf-8").splitlines())
    assert so_dong <= 900, f"routes.py {so_dong} dòng — tách sang services/"

    cay = ast.parse(tep.read_text(encoding="utf-8"))
    handler = sum(
        1
        for n in ast.walk(cay)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr in ("get", "post")
            for d in n.decorator_list
        )
    )
    assert handler <= 30, f"{handler} handler — tách theo miền"


def test_co_du_ba_cua_nguoi_dung_can():
    """Trang chính, gửi job, và xem lại kết quả."""
    duong = set()
    cay = ast.parse(inspect.getsource(routes))
    for n in ast.walk(cay):
        for d in getattr(n, "decorator_list", []):
            if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and d.func.attr in ("get", "post") and d.args):
                v = d.args[0]
                if isinstance(v, ast.Constant):
                    duong.add(v.value)
    assert "" in duong or "/" in duong, "thiếu trang chính"
    assert any("tao" in d for d in duong), "thiếu đường gửi job"
    assert any("video" in d for d in duong), "thiếu đường phục vụ video"


def test_template_ton_tai_va_khong_co_tab_mode():
    """Composer phẳng: không tab T2V/I2V/Control (kiến trúc đã khoá)."""
    tep = (pathlib.Path(inspect.getsourcefile(routes)).parents[2]
           / "server" / "templates" / "lttvideo.html")
    assert tep.is_file(), "thiếu template"
    # ⭐ Bỏ khối chú thích Jinja trước khi kiểm. Luật nói về thứ NGƯỜI DÙNG
    #    THẤY, mà `{# ... #}` không bao giờ render. Quét cả tệp thì phép kiểm
    #    báo động trên chính đoạn giải thích nó — tức nó trừng phạt việc giải
    #    thích, và cách chữa duy nhất là xoá lời giải thích đi.
    html = re.sub(r"\{#.*?#\}", "", tep.read_text(encoding="utf-8"), flags=re.S).lower()
    for cam in ("t2v", "i2v", "v2v", "vace", "animate"):
        assert cam not in html, f"giao diện lộ mode kỹ thuật: {cam}"


def test_template_dinh_asset_ver_de_cache_bust():
    """`CLAUDE.md` luật 6: đổi static phải cache-bust."""
    tep = (pathlib.Path(inspect.getsourcefile(routes)).parents[2]
           / "server" / "templates" / "lttvideo.html")
    html = tep.read_text(encoding="utf-8")
    if "ltt.css" in html:
        assert "asset_ver" in html, "link ltt.css phải đính ?v={{ asset_ver }}"
