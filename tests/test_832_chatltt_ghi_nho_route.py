"""
test_832 — bề mặt HTTP của kho ghi nhớ: CỔNG trước, tính năng sau. (H44 B4 bước 4)

Cùng khuôn `test_829` cho `_p_tep.py`, và **cố ý** chép lại thay vì tham số hoá:
một phép kiểm dùng chung cho hai cổng sẽ xanh khi một trong hai cổng biến mất
(nó vẫn tìm thấy cổng kia). Ở đây thứ được chốt là *"cổng NÀY tồn tại"*, nên
phép kiểm phải nêu đích danh tệp.

## Một mã lỗi mới, và vì sao nó không phải 400

`KhoDay` ⇒ **409**, không 400. Thân request **hợp lệ**; chỉ là kho đã đầy. Giao
diện phải xử lý hai ca khác nhau — một cái bảo *"sửa lại đi"*, cái kia bảo
*"xoá bớt đi"* — nên chúng không được đi chung một mã.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP_ROUTE = GOC / "apps" / "chatltt" / "routes" / "_p_ghi_nho.py"


def _cay():
    return ast.parse(TEP_ROUTE.read_bytes().decode("utf-8"))


# ── 1. Route đã gắn ────────────────────────────────────────────────────────

def test_BON_route_da_gan_va_dung_phuong_thuc():
    from apps.chatltt.routes import router

    co = {(tuple(sorted(r.methods)), r.path) for r in router.routes
          if "ghi-nho" in getattr(r, "path", "")}
    assert (("GET",), "/api/ghi-nho") in co
    assert (("POST",), "/api/ghi-nho") in co
    assert (("PATCH",), "/api/ghi-nho/{ghi_nho_id}") in co
    assert (("DELETE",), "/api/ghi-nho/{ghi_nho_id}") in co


# ── 2. Cờ ──────────────────────────────────────────────────────────────────

def test_CO_GHI_NHO_mac_dinh_TAT(monkeypatch):
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_GHI_NHO, raising=False)
    assert co_v3.ghi_nho_bat() is False
    assert co_v3.trang_thai()["ghi_nho"] is False


def test_CO_GHI_NHO_KHONG_dung_chung_voi_co_tep_hay_co_tool(monkeypatch):
    """⛔ Ghi nhớ đổi **ngữ cảnh của mọi lượt**, kể cả lượt không đính tệp và
    không gọi tool. Bật nhầm nó là đổi hành vi toàn sản phẩm, không phải mở
    thêm một cửa."""
    from apps.chatltt.services import co_v3

    monkeypatch.setenv(co_v3.CO_TEP, "1")
    monkeypatch.setenv(co_v3.CO_TOOLS, "1")
    monkeypatch.delenv(co_v3.CO_GHI_NHO, raising=False)
    assert (co_v3.tep_bat(), co_v3.tool_bat()) == (True, True)
    assert co_v3.ghi_nho_bat() is False


def _ten_trong_depends(mac_dinh) -> str:
    """`Depends(cong_ghi_nho)` → `"cong_ghi_nho"`; thứ khác → `""`."""
    if not (isinstance(mac_dinh, ast.Call) and isinstance(mac_dinh.func, ast.Name)
            and mac_dinh.func.id == "Depends" and mac_dinh.args):
        return ""
    a = mac_dinh.args[0]
    return a.id if isinstance(a, ast.Name) else ""


def _phu_thuoc_theo_thu_tu(ham: ast.AsyncFunctionDef) -> list:
    """Tên các `Depends(...)` của một handler, **theo đúng thứ tự khai báo**."""
    dt = ham.args
    # ⭐ `strict=True` chứ không phải để yên cho ruff: hai dãy này **phải** bằng
    #    nhau (AST bảo đảm `kw_defaults` dài bằng `kwonlyargs`, và lát cắt ở
    #    trên bằng `defaults`). Ngày một giả định ấy sai, `zip` im lặng cắt
    #    ngắn — tức phép kiểm bỏ sót một tham số thay vì báo.
    cap = list(zip(dt.args[len(dt.args) - len(dt.defaults):], dt.defaults,
                   strict=True))
    cap += [(a, d) for a, d in zip(dt.kwonlyargs, dt.kw_defaults, strict=True)
            if d is not None]
    return [t for t in (_ten_trong_depends(d) for _, d in cap) if t]


def _cac_handler() -> list:
    return [n for n in ast.walk(_cay()) if isinstance(n, ast.AsyncFunctionDef)
            and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and isinstance(d.func.value, ast.Name)
                    and d.func.value.id == "router"
                    for d in n.decorator_list)]


def test_cong_co_dat_TRUOC_require_login():
    """🔴 `Depends` chạy theo **thứ tự khai báo**, và `require_login` trả 303 về
    `/login` — đặt cổng sau nó thì route "đã đóng" vẫn khai rằng nó tồn tại.

    ⚠️ Bản đầu của phép kiểm này chép khuôn `test_829`: nó so **vị trí ký tự
       trong một DÒNG**. Nó đỏ ngay, và đỏ vì chính nó — chữ ký ở tệp này xuống
       dòng, nên `require_login` không nằm cùng dòng với cổng. Mã vẫn đúng.

    ⭐ Đúng bẫy *"đọc thứ đại diện thay vì đọc thứ thật"*: một dòng là **biểu
       diễn** của chữ ký, không phải chữ ký. Thứ phải chốt là **thứ tự tham
       số** ⇒ đọc AST. Bản này còn mạnh hơn ở chỗ nó sống sót qua mọi lần định
       dạng lại, và nó bắt được cả trường hợp cổng bị chuyển thành `kwonly`.
    """
    handler = _cac_handler()
    assert len(handler) == 4, [h.name for h in handler]
    for h in handler:
        pt = _phu_thuoc_theo_thu_tu(h)
        assert "cong_ghi_nho" in pt, f"{h.name}: thieu cong co"
        assert "require_login" in pt, f"{h.name}: thieu require_login"
        assert pt.index("cong_ghi_nho") < pt.index("require_login"), (
            f"{h.name}: cong co dat SAU require_login ({pt})")


def test_cong_co_tra_404_chu_khong_403(monkeypatch):
    from fastapi import HTTPException

    from apps.chatltt.routes._chung import cong_ghi_nho
    from apps.chatltt.services import co_v3

    monkeypatch.delenv(co_v3.CO_GHI_NHO, raising=False)
    with pytest.raises(HTTPException) as e:
        cong_ghi_nho()
    assert e.value.status_code == 404

    monkeypatch.setenv(co_v3.CO_GHI_NHO, "1")
    assert cong_ghi_nho() is None


# ── 3. Hợp đồng app: route chỉ lo HTTP ─────────────────────────────────────

def test_route_KHONG_chua_nghiep_vu():
    """Đọc **AST**, không đọc chuỗi — bẫy *"bộ dò quét văn bản trừng phạt việc
    giải thích"* đã bắt đúng phép kiểm tương ứng ở `test_829`."""
    cay = _cay()
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    ten |= {a.name for n in ast.walk(cay) if isinstance(n, ast.Import)
            for a in n.names}
    ten |= {n.module or "" for n in ast.walk(cay) if isinstance(n, ast.ImportFrom)}

    for cam in ("ChatlttGhiNho", "select", "hashlib", "sqlalchemy",
                "TRAN_KY_TU_TIEM", "khoi_ngu_canh"):
        assert cam not in ten, f"nghiep vu {cam!r} nam trong route, khong o service"


def test_khong_lo_cot_bam_ra_ngoai():
    """`bam` là khoá nội bộ chống trùng, không phải dữ liệu của người dùng.

    ⭐ Đối chứng: `noi_dung` PHẢI có mặt — thiếu vế đó thì một `_bay()` trả
       `{}` cũng qua sạch.
    """
    cay = _cay()
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "_bay"]
    assert len(ham) == 1
    khoa = {k.value for n in ast.walk(ham[0]) if isinstance(n, ast.Dict)
            for k in n.keys if isinstance(k, ast.Constant)}
    assert "bam" not in khoa
    assert {"id", "pham_vi", "nguon", "noi_dung"} <= khoa


# ── 4. Mã lỗi ──────────────────────────────────────────────────────────────

def _ma_loi_cua(ten_ngoai_le: str) -> set:
    """Mã HTTP mà mọi nhánh `except <ten_ngoai_le>` trả về. Đọc AST."""
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


def test_kho_day_tra_409_chu_khong_400():
    """Thân request HỢP LỆ, chỉ là kho đầy — hai ca cần hai cách xử lý ở giao diện."""
    assert _ma_loi_cua("KhoDay") == {409}


def test_khong_duoc_phep_tra_404_chu_khong_403():
    """Cùng luật `kho_tep.mot`: phân biệt *"không có"* với *"không phải của bạn"*
    là tự khai rằng id ấy tồn tại."""
    assert _ma_loi_cua("KhongDuocPhep") == {404}


def test_tham_so_sai_tra_400():
    """Đối chứng dương: nếu MỌI nhánh đều 404/409 thì hai phép kiểm trên vô nghĩa."""
    assert _ma_loi_cua("ThamSoSai") == {400}


def test_moi_route_ghi_du_lieu_deu_kiem_CSRF():
    """GET không cần; ba route còn lại thì bắt buộc."""
    ma = TEP_ROUTE.read_bytes().decode("utf-8")
    assert len(re.findall(r"kiem_csrf\(request\)", ma)) == 3
