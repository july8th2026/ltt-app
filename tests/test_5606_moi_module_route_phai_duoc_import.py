"""Mọi module route trong `apps/agent/routes/` phải được `__init__.py` IMPORT.

## 🔴 Sự cố thật, 28/09/2026 — một tính năng CHẾT trên production

Làn UI-8a dựng `apps/agent/routes/phe_duyet_v3.py` (cửa duyệt `core.human`), có
**9 bài test xanh**, nghiệm thu trình duyệt thật PASS, và báo điều phối đúng một
việc phải làm: *"thêm `phe_duyet_v3` vào tuple import của `routes/__init__.py`"*.

Điều phối (tôi) **quên**. Hậu quả đo được trên `https://app.lttstudios.com` sau
khi deploy:

    POST /agent/api/v3/runs/{id}/nodes/{id}/duyet  ->  404 {"detail":"Not Found"}

⇒ Tính năng đi qua mọi cổng chất lượng rồi **chết im lặng** trên production.

## ⚠️ Vì sao KHÔNG phép kiểm nào của làn đó bắt được

`_shared.router` là một đối tượng **dùng chung**. Fixture của UI-8a làm đúng
theo hướng dẫn của tôi:

    import apps.agent.routes.phe_duyet_v3   # noqa: F401  (dang ky route)

Import tường minh ấy gắn route vào router **trong tiến trình test**. Nên bài test
thấy route, còn `create_app()` ngoài đời thì ⛔ không — vì nó chỉ nạp những gì
`routes/__init__.py` import.

⇒ Đây là *"một mô-đun đăng ký mà ⛔ không ai import là một mô-đun CHẾT"*, câu đã
  viết sẵn trong `platform_core/workflow/nut_loi/__init__.py` cho đúng ca này ở
  tầng node — và lặp lại ở tầng route vì ⛔ không ai cơ học hoá nó.

## ⭐ Bài này là phần CƠ HỌC HOÁ

Nó ⛔ không đếm route, ⛔ không chốt danh sách tên. Nó hỏi một câu duy nhất:
**có tệp `.py` nào trong thư mục này mà `__init__.py` ⛔ không import không?**

⚠️ Và nó ⛔ KHÔNG dùng `import` tường minh của chính nó để kiểm — làm thế là lặp
   lại đúng cái bẫy. Nó đọc **AST của `__init__.py`**.
"""
from __future__ import annotations

import ast
import pathlib

GOC = pathlib.Path(__file__).resolve().parent.parent
THU_MUC = GOC / "apps" / "agent" / "routes"

#: Tệp ⛔ không phải module route. Giữ danh sách này **ngắn** và mỗi dòng có lý do —
#: một danh sách loại trừ dài là chỗ một module chết trốn vào.
KHONG_PHAI_ROUTE = {
    "__init__.py",   # chính nó
    "_shared.py",    # router + helper dùng chung, ⛔ không khai route nào
}


def _ten_duoc_import(init: pathlib.Path) -> set[str]:
    """Tên module mà `__init__.py` import, đọc từ AST.

    ⛔ KHÔNG `import` gói rồi soi `sys.modules`: một module có thể đã nằm trong
       `sys.modules` vì **một tệp test khác** vừa import nó, và khi ấy phép kiểm
       này sẽ xanh vì lý do ⛔ không liên quan gì tới `__init__.py`. Đúng hình
       dạng bẫy mà bài này tồn tại để chặn.
    """
    cay = ast.parse(init.read_bytes().decode("utf-8"))
    ra: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                ra.add(a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                ra.add(a.name.rsplit(".", 1)[-1])
    return ra


def test_moi_module_route_deu_duoc_init_import():
    init = THU_MUC / "__init__.py"
    duoc_import = _ten_duoc_import(init)
    tren_dia = {p.name for p in THU_MUC.glob("*.py")} - KHONG_PHAI_ROUTE

    thieu = sorted(t for t in tren_dia if t[:-3] not in duoc_import)
    assert not thieu, (
        "module route KHONG duoc `routes/__init__.py` import ⇒ route cua no "
        f"CHET tren production du test co the van xanh: {thieu}\n"
        "Them vao tuple import trong `apps/agent/routes/__init__.py`.")


def test_tep_bo_qua_thuc_su_KHONG_khai_route():
    """Đối chứng cho danh sách loại trừ.

    ⛔ Không có bài này, ai gặp đỏ ở bài trên có thể "sửa" bằng cách thêm tên tệp
    vào `KHONG_PHAI_ROUTE` — và thế là cái chết im lặng quay lại, lần này có một
    dòng trong kho nói rằng nó ổn.
    """
    for ten in sorted(KHONG_PHAI_ROUTE - {"__init__.py"}):
        cay = ast.parse((THU_MUC / ten).read_bytes().decode("utf-8"))
        trang_tri = [
            d for n in ast.walk(cay)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            for d in n.decorator_list
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and isinstance(d.func.value, ast.Name) and d.func.value.id == "router"]
        assert not trang_tri, (
            f"{ten} nam trong KHONG_PHAI_ROUTE nhung no CO khai route "
            f"(@router.{trang_tri[0].func.attr}) — bo no khoi danh sach do")


def test_route_duyet_CO_tren_router_that():
    """Mệnh đề cụ thể của sự cố, giữ lại như một bánh cóc chỉ đích danh.

    ⭐ Đọc `router` mà `create_app()` sẽ lắp — ⛔ KHÔNG import
       `phe_duyet_v3` ở đây. Nếu bài này cần một import tường minh để xanh thì nó
       ⛔ không còn đo điều nó tưởng.
    """
    from apps.agent.routes import router

    co = {(sorted(r.methods)[0], r.path) for r in router.routes
          if getattr(r, "methods", None)}
    assert ("POST", "/api/v3/runs/{run_id}/nodes/{node_id}/duyet") in co, \
        "cua duyet `core.human` khong co tren router — no se tra 404 tren production"
