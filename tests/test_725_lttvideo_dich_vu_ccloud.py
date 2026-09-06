"""Service C-CLOUD — mọi đường đều phải đòi khoá, và job_id không được đoán ra.

⛔ Hai lỗ này **nhân nhau**: `job_id` đoán được cộng với đường tải không đòi khoá
   nghĩa là tải được video của người khác mà **không cần khoá nào**. Vá một cái
   thôi vẫn còn đường vào.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib

_TEP = (pathlib.Path(__file__).parent.parent / "tools" / "wangp"
        / "dich_vu_ccloud.py")


def _cay() -> ast.Module:
    return ast.parse(_TEP.read_text(encoding="utf-8"))


def _handler() -> dict[str, ast.FunctionDef]:
    ra = {}
    for n in ast.walk(_cay()):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in n.decorator_list:
            if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and d.func.attr in ("get", "post")):
                ra[n.name] = n
    return ra


def test_MOI_duong_deu_doi_khoa_tru_health():
    """`/health` được để ngỏ có chủ đích — nó chỉ nói máy sống và chạy bản nào."""
    thieu = []
    for ten, n in _handler().items():
        if ten == "health":
            continue
        if "_kiem_khoa" not in ast.unparse(n):
            thieu.append(ten)
    assert not thieu, f"đường không đòi khoá: {thieu}"


def test_ba_duong_DOC_cung_phai_doi_khoa():
    """Đường đọc để rò dữ liệu; đường ghi để phá. Cả hai đều cần khoá."""
    h = _handler()
    for ten in ("progress", "result", "tai_ve"):
        assert ten in h, f"thiếu handler {ten}"
        assert "_kiem_khoa" in ast.unparse(h[ten]), f"{ten} không đòi khoá"


def test_job_id_sinh_bang_CSPRNG_chu_khong_bang_dong_ho():
    """`f\"j{int(time.time()*1000)}{len(_JOB)}\"` đoán ra được trong vài lượt thử."""
    ma = _TEP.read_text(encoding="utf-8")
    assert "secrets.token_urlsafe" in ma, "job_id phải sinh bằng CSPRNG"
    assert "time.time() * 1000" not in ma, "còn dấu vết id theo đồng hồ"


def test_so_khop_khoa_khong_ro_ri_qua_thoi_gian():
    ma = _TEP.read_text(encoding="utf-8")
    assert "compare_digest" in ma


def test_job_id_du_dai_de_khong_do_duoc():
    """Nạp thật module và sinh id — đối chứng, không chỉ đọc mã."""
    spec = importlib.util.spec_from_file_location("_dvcc", _TEP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    ids = {m.sinh_job_id() for _ in range(200)}
    assert len(ids) == 200, "id bị trùng"
    for i in ids:
        assert len(i) >= 20, f"id quá ngắn: {i!r}"
