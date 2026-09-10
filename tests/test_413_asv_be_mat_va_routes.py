"""`surface` cua Auto Scan Video phai DI THEO su ton tai cua `routes.py`.

Ly do ton tai cua tep nay la mot loi that trong kho nay, va cach no duoc sua.

`apps/ltt_llm` tung khai `surface="customer"` khi chua co `routes.py`. Ket qua:
`nav_entries()` **tu sinh** mot dong nav mac dinh — `nav=()` KHONG co nghia la
"khong co nav" — va moi khach da dang nhap thay mot link chet vao 404 suot nhieu
tuan. `tests/test_60` da dong bat bien do cho **toan nen tang**.

⭐ Nhung `test_60` chi tra loi duoc mot nua cau hoi: no bat "hien ma khong co
   router". No **khong** bat chieu nguoc lai — mot app da co giao dien nhung
   quen doi `surface` lai thi khong hien o dau ca, va thu do hong **im lang**:
   khong 404, khong loi, chi la khach khong bao gio tim thay san pham.

Auto Scan Video dang o dung khoang giua do (chua co `routes.py` o pha 14), nen
no can ca hai chieu.
"""
from __future__ import annotations

import pathlib

from apps.auto_scan_video import manifest as m

GOC_APP = pathlib.Path(m.__file__).resolve().parent
CO_ROUTES = (GOC_APP / "routes.py").exists() or (GOC_APP / "routes").is_dir()


def test_co_routes_thi_PHAI_la_customer():
    """Chieu de quen: giao dien da xong ma `surface` con `runtime`.

    Hong im lang — khong 404, khong loi, chi la san pham khong xuat hien o dau.
    """
    if not CO_ROUTES:
        # Khong `pytest.skip`: mot phep kiem bi bo qua la mot phep kiem KHONG
        # canh gi ca, va no con lam banh coc `check_bo_qua` bao mot muc moi.
        # Chieu con lai duoi day van chay va van co nghia.
        return
    assert m.MANIFEST.surface == "customer", (
        "da co routes.py nhung surface van la runtime — app se khong hien o "
        "catalog lan header, va khong co loi nao bao")


def test_chua_co_routes_thi_KHONG_duoc_la_customer():
    """Chieu da co nan nhan: hien trong nav ma khong co router -> link 404."""
    if CO_ROUTES:
        return
    assert m.MANIFEST.surface != "customer", (
        "chua co routes.py ma khai surface=customer — `nav_entries()` se TU "
        "SINH mot dong nav mac dinh tro vao 404 (dung loi cua ltt_llm)")


def test_enabled_False_KHONG_phai_la_luoi_an_toan():
    """Chot chinh dieu de hieu nham nhat, bang chinh ma nguon cua nen tang.

    Rat de tin rang `enabled=False` du de giau mot app chua xong. Khong phai:
    `visible_on_surface` khong doc `enabled` mot lan nao.
    """
    import inspect

    from platform_core import registry

    ma = inspect.getsource(registry.visible_on_surface)
    assert "enabled" not in ma, (
        "`visible_on_surface` nay da doc `enabled` — neu dung the thi ghi chu "
        "trong manifest cua auto_scan_video da loi thoi, sua no")


def test_ba_vo_thi_hanh_KHONG_BAO_GIO_hien_ra():
    """`asv_media` · `asv_gpu` · `asv_voice` khong phai san pham ban duoc.

    Chung khai `catalog_parent`, nen `visible_on_surface` tra `False` ke ca voi
    khach da dang nhap. Mot lan lo tay go `catalog_parent` se moc ba dong nav
    tro vao ba trang 404.
    """
    from platform_core.registry import visible_on_surface

    for ten in ("asv_media", "asv_gpu", "asv_voice"):
        mod = __import__(f"apps.{ten}.manifest", fromlist=["MANIFEST"])
        man = mod.MANIFEST
        assert man.catalog_parent == "auto_scan_video", (
            f"{ten} mat catalog_parent — no se tu moc mot dong nav")
        assert not visible_on_surface(man, authenticated=True)
        assert not visible_on_surface(man, authenticated=False)
