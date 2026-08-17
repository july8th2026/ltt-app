"""Nexus N2.5 — bề mặt khách hàng, và cái cờ tắt phải thật sự đóng cửa.

Điều bất ngờ tìm được khi viết app này: `registry.mount_all()` gắn router của
mọi app **bất kể** `manifest.enabled` — nó chỉ kiểm `router is not None and not
item.error`. Nên `enabled=False` giấu app khỏi catalog nhưng **không** đóng URL.

Với một app bán công cụ AI thì đó chỉ là chuyện hiển thị. Với một app điều khiển
máy từ xa thì đó là chênh lệch giữa "chưa bật" và "đang mở cho ai biết đường
dẫn". Vì vậy lớp chặn ở route là **lớp duy nhất** thật sự đóng cửa, và test nặng
nhất ở đây chốt rằng **mọi** handler đều có nó.
"""
from __future__ import annotations

import inspect

import pytest


# ── Cờ tắt phải đóng được cửa ────────────────────────────────────────────────

def test_mount_all_KHONG_nhin_manifest_enabled():
    """Chốt lại sự thật đã tìm ra, để nếu nền tảng đổi hành vi thì ta biết.

    Nếu một ngày `mount_all` bắt đầu tôn trọng `enabled`, test này đỏ — và đó là
    lúc nên xem lại có còn cần lớp chặn ở route không (câu trả lời nhiều khả
    năng vẫn là có, nhưng phải là một quyết định chứ không phải một giả định).
    """
    from platform_core import registry

    src = inspect.getsource(registry.mount_all)
    assert "item.manifest.enabled" not in src, (
        "mount_all da doi hanh vi — xem lai lop chan o route")


def test_MOI_handler_deu_goi_lop_chan():
    """Quên `_bat_buoc_bat()` ở một handler mới là mở lại cửa mà không ai thấy.

    Chốt bằng cấu trúc chứ không bằng cách gọi thử từng route: một test gọi thử
    chỉ phủ những route đã biết, còn cái nguy hiểm là route **sẽ được thêm**.
    """
    from apps.nexus import routes

    handlers = [obj for ten, obj in vars(routes).items()
                if inspect.isfunction(obj) and not ten.startswith("_")
                and obj.__module__ == routes.__name__
                and ten not in ("devices_boi_chu",)]
    assert handlers, "khong tim thay handler nao — test nay da mat tac dung"

    thieu = [fn.__name__ for fn in handlers
             if "_bat_buoc_bat()" not in inspect.getsource(fn)]
    assert thieu == [], f"handler khong co lop chan cua co: {thieu}"


def test_co_tat_thi_manifest_cung_tat(monkeypatch):
    from platform_core import nexus

    monkeypatch.delenv(nexus.FLAG_ENV, raising=False)
    assert nexus.enabled() is False

    import importlib

    from apps.nexus import manifest as manifest_mod
    importlib.reload(manifest_mod)
    assert manifest_mod.MANIFEST.enabled is False


def test_co_bat_thi_manifest_bat(monkeypatch):
    import importlib

    from platform_core import nexus

    monkeypatch.setenv(nexus.FLAG_ENV, "1")
    from apps.nexus import manifest as manifest_mod
    importlib.reload(manifest_mod)
    try:
        assert manifest_mod.MANIFEST.enabled is True
    finally:
        monkeypatch.delenv(nexus.FLAG_ENV, raising=False)
        importlib.reload(manifest_mod)


def test_lop_chan_tra_404_chu_khong_phai_403():
    """403 xác nhận bề mặt này có tồn tại. Với sản phẩm điều khiển máy từ xa thì
    ngay cả việc đó cũng không nên nói."""
    from apps.nexus import routes

    # Đọc THÂN hàm, không đọc docstring: docstring giải thích *vì sao không dùng
    # 403*, nên tìm chuỗi "403" trong cả nguồn sẽ bắt nhầm chính lời giải thích.
    src = inspect.getsource(routes._bat_buoc_bat)
    than = src.split('"""')[-1]

    assert "status_code=404" in than
    assert "403" not in than


# ── Hợp đồng app ─────────────────────────────────────────────────────────────

def test_khong_co_job_va_khong_co_gia():
    """Nexus bán theo **thuê bao tháng** (Q93/D3), không theo lượt — nên không
    có gì để tính giá, và một `credit_cost` thừa sẽ gợi ý sai mô hình tiền."""
    from apps.nexus.manifest import MANIFEST

    assert MANIFEST.job_types == ()
    assert MANIFEST.credit_cost is None


def test_route_khong_tu_viet_prefix():
    """Nền tảng gắn prefix từ manifest; route tự viết sẽ tạo hai nguồn sự thật
    về đường dẫn của app."""
    from apps.nexus import routes

    for route in routes.router.routes:
        assert not route.path.startswith("/nexus"), route.path


def test_nghiep_vu_KHONG_nam_trong_routes():
    """`AGENTS.md` 8.1: routes.py chỉ lo HTTP.

    Kiểm bằng cách khác thay vì đếm dòng: mọi quyết định về thiết bị/phiên phải
    đi qua `platform_core.nexus`, nên trong routes không được có truy vấn thẳng
    vào bảng.
    """
    from apps.nexus import routes

    src = inspect.getsource(routes)
    for cam in ("NexusDevice", "NexusEnrollment", "NexusSession", "select("):
        assert cam not in src, f"routes.py dang tu truy van CSDL: {cam}"


# ── Ngôn ngữ hậu quả (Q93 ràng buộc 8) ───────────────────────────────────────

@pytest.mark.parametrize("ten", ["nexus_ma_ghep.html", "nexus_trang_chinh.html",
                                 "nexus_nhat_ky.html"])
def test_template_ton_tai(ten):
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "server" / "templates" / ten
    assert p.exists(), f"thieu template {ten}"


def test_trang_ma_ghep_canh_bao_bang_HAU_QUA_va_dat_TRUOC_ma():
    """T1 không đóng được bằng kỹ thuật; chữ là thứ duy nhất còn lại.

    Hai tính chất được chốt: cảnh báo nói về **hậu quả** (nhìn thấy màn hình,
    điều khiển máy) chứ không phải thuật ngữ, và nó nằm **trên** mã — một cảnh
    báo đặt dưới mã thì người đã đọc mã xong rồi mới thấy.
    """
    from pathlib import Path

    p = (Path(__file__).resolve().parent.parent / "server" / "templates"
         / "nexus_ma_ghep.html")
    html = p.read_text(encoding="utf-8")

    assert "điều khiển được máy tính của bạn" in html
    assert "gọi điện đến bạn" in html, "phai canh bao ve cuoc goi den — do la T1"

    vi_tri_canh_bao = html.index("điều khiển được máy tính của bạn")
    vi_tri_ma = html.index("{{ ma }}")
    assert vi_tri_canh_bao < vi_tri_ma, "canh bao phai nam TREN ma"


def test_nhat_ky_lam_noi_bat_thao_tac_cua_nhan_vien():
    """Ràng buộc 5 chỉ có nghĩa nếu khách **nhìn thấy** — một dòng admin trôi
    lẫn giữa các dòng khác thì coi như không có ai đọc."""
    from pathlib import Path

    p = (Path(__file__).resolve().parent.parent / "server" / "templates"
         / "nexus_nhat_ky.html")
    html = p.read_text(encoding="utf-8")

    assert "do_admin_lam(su_kien)" in html
    assert "nhân viên LTT" in html
