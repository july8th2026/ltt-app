"""
test_837 — bề mặt HTTP của dự án: CỔNG trước, tính năng sau. (H44 B5 bước 5)

Cùng khuôn `test_829`/`test_832`, và **cố ý chép lại** thay vì tham số hoá: một
phép kiểm dùng chung cho ba cổng sẽ xanh khi một trong ba biến mất (nó vẫn tìm
thấy hai cổng kia). Thứ được chốt ở đây là *"cổng NÀY tồn tại"*.

## Hai mã lỗi, và không mã nào được gộp

* `ProjectConflict` ⇒ **409**. Thân request **hợp lệ**; chỉ là có người sửa
  trước. Giao diện phải tải lại rồi hỏi người dùng, không phải báo "tham số sai".
* thiếu `revision` ⇒ **400**, và **không** có mặc định. Một mặc định ở đây là
  tắt khoá lạc quan đi, rồi hai tab lại ghi đè nhau im lặng.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP = GOC / "apps" / "chatltt" / "routes" / "_p_du_an.py"


def _cay():
    return ast.parse(TEP.read_bytes().decode("utf-8"))


def _handler() -> list:
    return [n for n in ast.walk(_cay()) if isinstance(n, ast.AsyncFunctionDef)
            and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and isinstance(d.func.value, ast.Name)
                    and d.func.value.id == "router"
                    for d in n.decorator_list)]


def _ten_depends(mac_dinh) -> str:
    if not (isinstance(mac_dinh, ast.Call) and isinstance(mac_dinh.func, ast.Name)
            and mac_dinh.func.id == "Depends" and mac_dinh.args):
        return ""
    a = mac_dinh.args[0]
    return a.id if isinstance(a, ast.Name) else ""


def _phu_thuoc(ham) -> list:
    dt = ham.args
    cap = list(zip(dt.args[len(dt.args) - len(dt.defaults):], dt.defaults,
                   strict=True))
    cap += [(a, d) for a, d in zip(dt.kwonlyargs, dt.kw_defaults, strict=True)
            if d is not None]
    return [t for t in (_ten_depends(d) for _, d in cap) if t]


# ── 1. Route ───────────────────────────────────────────────────────────────

def test_SAU_route_da_gan_va_dung_phuong_thuc():
    from apps.chatltt.routes import router

    co = {(tuple(sorted(r.methods)), r.path) for r in router.routes
          if "du-an" in getattr(r, "path", "")}
    assert (("GET",), "/api/du-an") in co
    assert (("POST",), "/api/du-an") in co
    assert (("PATCH",), "/api/du-an/{du_an_id}") in co
    assert (("DELETE",), "/api/du-an/{du_an_id}") in co
    assert (("GET",), "/api/du-an/{du_an_id}/hoi-thoai") in co
    assert (("POST",), "/api/hoi-thoai/{conv_id}/du-an") in co


def test_MOT_route_cho_ca_gan_lan_go():
    """⭐ `du_an_id` rỗng nghĩa là gỡ. Giao diện chỉ có **một** ô chọn dự án, và
    *"— không thuộc dự án nào —"* là cùng một thao tác với *"chọn dự án khác"*.
    Tách đôi ở tầng HTTP là bắt giao diện tự chọn động từ, rồi một ngày nó chọn
    sai."""
    from apps.chatltt.routes import router

    ds = [r for r in router.routes
          if getattr(r, "path", "") == "/api/hoi-thoai/{conv_id}/du-an"]
    assert len(ds) == 1


# ── 2. Cờ ──────────────────────────────────────────────────────────────────

def test_CO_DU_AN_mac_dinh_TAT(monkeypatch):
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_DU_AN, raising=False)
    assert co_v3.du_an_bat() is False
    assert co_v3.trang_thai()["du_an"] is False


def test_CO_DU_AN_doc_lap_voi_bon_co_kia(monkeypatch):
    from apps.chatltt.services import co_v3

    for c in (co_v3.CO_TOOLS, co_v3.CO_TEP, co_v3.CO_GHI_NHO,
              co_v3.CO_TOOL_CO_PHI):
        monkeypatch.setenv(c, "1")
    monkeypatch.delenv(co_v3.CO_DU_AN, raising=False)
    assert co_v3.du_an_bat() is False


def test_cong_co_dat_TRUOC_require_login():
    """🔴 `Depends` chạy theo **thứ tự khai báo**, và `require_login` trả 303 —
    đặt cổng sau nó thì route "đã đóng" vẫn khai rằng nó tồn tại.

    ⭐ Đọc AST thứ tự tham số, không đọc vị trí ký tự trong một dòng: bản
       dò-theo-dòng ở `test_829` đỏ ngay khi một chữ ký xuống dòng (đã dính thật
       ở `test_832`).
    """
    hs = _handler()
    assert len(hs) == 6, [h.name for h in hs]
    for h in hs:
        pt = _phu_thuoc(h)
        assert "cong_du_an" in pt, f"{h.name}: thieu cong co"
        assert "require_login" in pt, f"{h.name}: thieu require_login"
        assert pt.index("cong_du_an") < pt.index("require_login"), f"{h.name}: {pt}"


def test_cong_co_tra_404_chu_khong_403(monkeypatch):
    from fastapi import HTTPException

    from apps.chatltt.routes._chung import cong_du_an
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_DU_AN, raising=False)
    with pytest.raises(HTTPException) as e:
        cong_du_an()
    assert e.value.status_code == 404

    monkeypatch.setenv(co_v3.CO_DU_AN, "1")
    assert cong_du_an() is None


# ── 3. Hợp đồng app ────────────────────────────────────────────────────────

def test_route_KHONG_chua_nghiep_vu():
    cay = _cay()
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    ten |= {a.name for n in ast.walk(cay) if isinstance(n, ast.Import) for a in n.names}
    ten |= {n.module or "" for n in ast.walk(cay) if isinstance(n, ast.ImportFrom)}

    for cam in ("ChatlttConversation", "AppProject", "select", "update",
                "sqlalchemy"):
        assert cam not in ten, f"nghiep vu {cam!r} nam trong route"


def test_payload_KHONG_ra_ngoai():
    """Bản v1 rỗng, và một trường rỗng trên đường dây là một trường ai đó sẽ
    nhét thứ gì vào — rồi nó thành hợp đồng công khai mà không ai chấm."""
    ham = [n for n in ast.walk(_cay())
           if isinstance(n, ast.FunctionDef) and n.name == "_bay"]
    assert len(ham) == 1
    khoa = {k.value for n in ast.walk(ham[0]) if isinstance(n, ast.Dict)
            for k in n.keys if isinstance(k, ast.Constant)}
    assert "payload" not in khoa
    assert {"id", "ten", "revision"} <= khoa      # doi chung


# ── 4. Mã lỗi ──────────────────────────────────────────────────────────────

def _ma_cua(ten_ngoai_le: str) -> set:
    ra = set()
    for nut in ast.walk(_cay()):
        if not isinstance(nut, ast.ExceptHandler) or nut.type is None:
            continue
        t = nut.type
        ten = (t.attr if isinstance(t, ast.Attribute)
               else t.id if isinstance(t, ast.Name) else "")
        if ten != ten_ngoai_le:
            continue
        for con in ast.walk(nut):
            if (isinstance(con, ast.Call) and isinstance(con.func, ast.Name)
                    and con.func.id == "loi" and con.args
                    and isinstance(con.args[0], ast.Constant)):
                ra.add(con.args[0].value)
    return ra


def test_xung_dot_revision_tra_409_chu_khong_400():
    assert _ma_cua("ProjectConflict") == {409}


def test_khong_duoc_phep_tra_404():
    assert _ma_cua("KhongDuocPhep") == {404}


def test_doi_chung_ProjectError_tra_400():
    """Nếu MỌI nhánh đều 409/404 thì hai phép kiểm trên vô nghĩa."""
    assert _ma_cua("ProjectError") == {400}


def test_thieu_revision_KHONG_co_mac_dinh():
    """⛔ Một mặc định ở đây là tắt khoá lạc quan đi, rồi hai tab lại ghi đè
    nhau im lặng. Chốt bằng AST: `than.get("revision")` không được có đối số
    thứ hai."""
    for nut in ast.walk(_cay()):
        if (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute)
                and nut.func.attr == "get" and nut.args
                and isinstance(nut.args[0], ast.Constant)
                and nut.args[0].value == "revision"):
            assert len(nut.args) == 1, "`revision` co gia tri mac dinh"


def test_moi_route_GHI_deu_kiem_CSRF():
    """Hai GET không cần; bốn route còn lại thì bắt buộc."""
    ma = TEP.read_bytes().decode("utf-8")
    assert len(re.findall(r"kiem_csrf\(request\)", ma)) == 4
