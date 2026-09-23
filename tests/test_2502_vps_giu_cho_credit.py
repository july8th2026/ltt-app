"""Tao VPS GIU CHO credit, quyet toan khi may that su len — khong thu roi hoan.

🔴 Do tren production 22/09/2026, hai lan lien tiep cua chu du an:

      13:07  vps-01      thu 1.490 -> 3 su kien `loi` -> hoan 1.490 -> xoa
      16:25  May Tram 2  thu 1.490 -> 3 su kien `loi` -> hoan 1.490 -> xoa

   Ca hai chet o `OVH_IP_ACQUIRE` (`pre_checkout_failure`): gio hang OVH chua
   bao gio dung xong, khong dong nao roi khoi tui. Nhung so credit thi DA bi
   tru truoc do, trong chinh request `POST /vps/tao`.

⭐ `platform_core/credit.py` DA CO `giu_cho` / `quyet_toan` theo `job_id`
   (`actual=0` nha het, quyet toan idempotent). VPS khong dung — no goi `tru()`
   thang. Day la ca "dung lai truoc, tu viet sau" dung nghia: nguyen thuy da co,
   da co test, va no giai dung bai toan nay.

Sau ban nay:
  - `POST /vps/tao` GIU credit, khong tru. Khach het tien van khong chiem duoc cho.
  - May len that (`tao_xong`) -> quyet toan -> luc do moi co su kien `thu_phi`.
  - Job hong -> nha het. KHONG co su kien `thu_phi`, nen quet hoan tien trong
    `bao_tri._hoan_tien_may_hong` (khoa theo `thu_phi`) tu dong bo qua — khong
    hoan mot khoan chua bao gio thu.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.db import Base
from tests.conftest import bao_dam_user


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


USER = "u-khach"
JOB = "job-tao-may"


def _nap(db, so: int):
    # Dung lai `bao_dam_user` cua conftest: `credit.cap_tay` kiem nguoi dung co
    # that (F-01), va tu viet mot User gia o day la dung lai dung cai lo do.
    bao_dam_user(db, USER)
    credit.nap(db, USER, so)
    db.flush()


def _job(db):
    from platform_core.models import Job
    db.add(Job(id=JOB, user_id=USER, app_slug="vps", job_type="vps.provision",
               status="queued", params={}))
    db.flush()


# ── giu cho khong phai tru ───────────────────────────────────────────────────

def test_giu_cho_khong_lam_giam_so_du_kha_dung_ngoai_phan_giu(db):
    _nap(db, 5000)
    _job(db)
    credit.giu_cho(db, USER, 1490, JOB)
    db.flush()
    assert credit.so_da_giu(db, JOB) == 1490


def test_quyet_toan_khong_dong_nao_tra_lai_het_phan_giu(db):
    """Job hong = nha het. Khach khong mat gi, va khong co gi de 'hoan'."""
    _nap(db, 5000)
    _job(db)
    truoc = credit.so_du(db, USER)
    credit.giu_cho(db, USER, 1490, JOB)
    db.flush()
    credit.quyet_toan(db, USER, JOB, 0)
    db.flush()
    assert credit.so_du(db, USER) == truoc


def test_quyet_toan_dung_gia_thi_thu_dung_gia(db):
    _nap(db, 5000)
    _job(db)
    truoc = credit.so_du(db, USER)
    credit.giu_cho(db, USER, 1490, JOB)
    db.flush()
    kq = credit.quyet_toan(db, USER, JOB, 1490)
    db.flush()
    assert kq.charged_credit == 1490
    assert credit.so_du(db, USER) == truoc - 1490


def test_quyet_toan_chay_lai_khong_thu_hai_lan(db):
    """Job runner chay lai mot job da xong la chuyen binh thuong."""
    _nap(db, 5000)
    _job(db)
    truoc = credit.so_du(db, USER)
    credit.giu_cho(db, USER, 1490, JOB)
    db.flush()
    credit.quyet_toan(db, USER, JOB, 1490)
    db.flush()
    credit.quyet_toan(db, USER, JOB, 1490)
    db.flush()
    assert credit.so_du(db, USER) == truoc - 1490


# ── seam voi quet hoan tien ──────────────────────────────────────────────────

def test_may_hong_khong_co_su_kien_thu_phi_nen_khong_bi_hoan_lan_hai(db):
    """Chot cai SEAM, khong chi chot y dinh.

    `bao_tri._hoan_tien_may_hong` quyet bang su kien `thu_phi`: khong co no thi
    `so = 0` va no bo qua. Doi sang giu cho ma van phat `thu_phi` luc tao la
    tra lai dung cai vong thu-roi-hoan, chi khac ten.
    """
    from apps.vps.tables import VpsEvent, VpsGateway, VpsInstance
    bao_dam_user(db, USER)
    db.add(VpsGateway(id="gw", ten="cong vao", vung="sgp",
                      ip_cong_khai="203.0.113.1", dang_nhan_may_moi=True))
    db.flush()
    db.add(VpsInstance(
        id="i-hong", user_id=USER, plan_id="vps-nho", os_id="winsrv2016-core",
        ten="may-hong", trang_thai="loi", gateway_id="gw"))
    db.flush()
    loai = {e.loai for e in db.execute(
        select(VpsEvent).where(VpsEvent.instance_id == "i-hong")).scalars()}
    assert "thu_phi" not in loai
