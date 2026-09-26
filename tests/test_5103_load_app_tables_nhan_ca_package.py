"""`load_app_tables()` phai nhan CA `tables.py` (tep) LAN `tables/` (package).

🔴 VI SAO CO TEP NAY

   Truoc 26/09/2026 `platform_core/registry.py::load_app_tables()` chi kiem
   `(entry / "tables.py").exists()` — mot TEP. `apps/prompt_ai_ommi` tach
   `tables.py` thanh package `tables/` (viec binh thuong khi tep phinh qua) va
   lien bi bo qua **IM LANG**: khong loi, khong canh bao, chi la
   `Base.metadata` thieu het bang cua app do.

   `alembic/env.py:30` goi chinh ham nay. Do duoc 26/09: 0 bang `ommi_*` vao
   metadata ⇒ mot lan `alembic revision --autogenerate` ke tiep sinh
   **DROP TABLE cho ca 14 bang**. Khong ai bao loi, vi mat mat chi lo ra khi
   migration do da chay tren production.

⭐ Phep kiem nay do MOT TINH CHAT ("app tach package van duoc nap"), khong do
   cach go. Them mot hinh dang thu ba (vi du `tables/__init__.pyi`) thi sua ham,
   phep kiem nay van dung.
"""
from __future__ import annotations

import pytest

from platform_core.db import Base
from platform_core.registry import load_app_tables

#: App da tach `tables.py` thanh package `tables/` (pha 1, 26/09).
APP_DA_TACH = "prompt_ai_ommi"

#: Bang cua app do PHAI co mat trong metadata sau khi nap. Day la ba bang dai
#: dien cho ba tep con khac nhau cua package — mot tep con bi quen se lo ra.
BANG_DAI_DIEN = ("ommi_resource", "ommi_meta_prompt", "ommi_binding")


@pytest.fixture(scope="module")
def da_nap() -> list[str]:
    return load_app_tables()


def test_app_tach_package_van_duoc_nap(da_nap):
    """⛔ Bo qua im lang la dang loi te nhat: khong loi, chi thieu du lieu."""
    assert APP_DA_TACH in da_nap, (
        f"{APP_DA_TACH} tach `tables.py` thanh package `tables/` va bi bo qua. "
        "Xem `load_app_tables()` — no phai nhan ca hai hinh dang.")


def test_metadata_co_du_bang_cua_app_da_tach(da_nap):
    """Nap duoc app khong dong nghia nap duoc BANG cua no."""
    co = set(Base.metadata.tables)
    thieu = [t for t in BANG_DAI_DIEN if t not in co]
    assert thieu == [], f"metadata thieu bang: {thieu}"


def test_moi_bang_ommi_deu_dung_tien_to(da_nap):
    """Doi chung cho phep kiem tien to san co: nap duoc thi tien to phai dung.

    `load_app_tables` raise khi tien to sai, nen phep nay xanh la du; no o day
    de neu ai noi long phep tien to thi co cho bao.
    """
    la = [t for t in Base.metadata.tables
          if t.startswith("ommi") and not t.startswith("ommi_")]
    assert la == [], f"bang sai tien to: {la}"


def test_doi_chung_ham_thuc_su_loc_theo_hai_hinh_dang(tmp_path):
    """Tiem loi: mot thu muc app KHONG co `tables.py` lan `tables/` phai bi bo qua.

    Khong co phep doi chung nay thi ba phep tren co the xanh chi vi ham nap MOI
    thu muc — bai hoc `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`.
    """
    gia = tmp_path / "apps_gia"
    (gia / "app_khong_co_bang").mkdir(parents=True)
    (gia / "app_khong_co_bang" / "__init__.py").write_text("", encoding="utf-8")
    assert load_app_tables(gia) == []
