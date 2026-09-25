"""Hai lỗ trong vòng bảo trì, cùng một hậu quả: thế giới thật trôi khỏi sổ sách.

🔴 LỖ 1 — máy `loi` không được dọn từ 23/09.
   `_hoan_may_tao_hong` là đường **duy nhất** nộp job xoá cho máy tạo hỏng, và nó
   `continue` khi không tìm thấy sự kiện `thu_phi` (`so <= 0`). Từ `cd3c7058`
   (23/09) đường tạo mới **không phát `thu_phi` khi job hỏng** — tiền nhả qua
   `credit` chứ không hoàn qua sổ VPS. Nên máy hỏng mới không hoàn (đúng) và
   cũng **không được xoá** (sai): VM ở lại Proxmox, giữ vmid, đĩa và một IP nội bộ.
   Đo 24/09: VM 207 `vps-c74d4fd8` vẫn `stopped` trên Proxmox sau khi máy
   `Maytram01` vào trạng thái `loi`.

🔴 LỖ 2 — phép soi duy nhất đo điện thật KHÔNG AI GỌI.
   `doi_chieu.quet` là chỗ duy nhất ghi `dien_quan_sat`/`quan_sat_luc`, và nó chỉ
   được gọi từ `_doi_chieu_dinh_ky` — hàm mà **không mã sản phẩm nào gọi** (chỉ
   test). `mot_luot` gọi `_doi_chieu_profiles`, mà module `reconciliation` khai
   rõ là read-only và không đọc điện.
   Đo 24/09: máy 204 mang `dien_quan_sat = chay` từ 16/09 20:41 trong khi
   Proxmox trả `tat` ⇒ trang khách khẳng định "Đang chạy" cho một máy đã tắt.
   Và docstring của chính `_doi_chieu_dinh_ky` viết: *"Một phép soi không ai chạy
   là một phép soi không tồn tại"*.

   ⚠️ Nối lại lời gọi là chưa đủ: hai hàm dùng **chung** biến `_moc_doi_chieu`,
      nên `_doi_chieu_profiles` chạy trước sẽ khoá phép soi kia đúng 24 giờ.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from platform_core.db import Base


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _may_hong(db, *, co_thu_phi: bool, da_tung_chay=False, vmid=207):
    """Máy `loi` đúng như production dựng nó sau bản sửa 23/09."""
    from platform_core.models import User
    from apps.vps.tables import VpsEvent, VpsGateway, VpsInstance

    db.add(User(id="chu-may", email="chu@vi.du", password_hash="x"))
    db.add(VpsGateway(id="gateway-ovh", ten="OVH gateway", vung="sgp",
                      ip_cong_khai="192.0.2.1"))
    may = VpsInstance(
        id=f"may-{vmid}", user_id="chu-may", plan_id="vps-nho", ten=f"May{vmid}",
        os_id="winsrv2016-core", gateway_id="gateway-ovh", vmid=vmid,
        trang_thai="loi", vong_doi="loi", ip_noi_bo="10.50.0.51")
    db.add(may)
    db.add(VpsEvent(instance_id=may.id, loai="tao_moi", boi="chu-may", chi_tiet={}))
    if co_thu_phi:
        db.add(VpsEvent(instance_id=may.id, loai="thu_phi", boi="he_thong",
                        chi_tiet={"credit": 1490}))
    if da_tung_chay:
        db.add(VpsEvent(instance_id=may.id, loai="tao_xong", boi="he_thong",
                        chi_tiet={"vmid": vmid}))
    db.commit()
    return may


def _bat_job_xoa(monkeypatch):
    from apps.vps import bao_tri

    da_nop = []
    monkeypatch.setattr(bao_tri, "_nop_job_xoa",
                        lambda db, may: da_nop.append(may.id) or True)
    return da_nop


def test_may_hong_KHONG_thu_phi_van_phai_duoc_nop_job_xoa(db, monkeypatch):
    """Ca của production sau 23/09: tiền nhả bằng giữ chỗ, không có `thu_phi`."""
    from apps.vps import bao_tri

    may = _may_hong(db, co_thu_phi=False)
    da_nop = _bat_job_xoa(monkeypatch)

    bao_tri._hoan_may_tao_hong(db)

    assert da_nop == [may.id], "VM mo coi se o lai Proxmox mai mai"


def test_may_hong_KHONG_thu_phi_thi_KHONG_hoan_tien(db, monkeypatch):
    """Dọn thì phải dọn, nhưng ⛔ không được hoàn một khoản chưa bao giờ thu."""
    from apps.vps import bao_tri
    from apps.vps.tables import VpsEvent

    may = _may_hong(db, co_thu_phi=False)
    _bat_job_xoa(monkeypatch)

    bao_tri._hoan_may_tao_hong(db)

    loai = {e.loai for e in db.execute(
        select(VpsEvent).where(VpsEvent.instance_id == may.id)).scalars()}
    assert "hoan_tien" not in loai


def test_may_DA_TUNG_chay_thi_khong_bi_xoa(db, monkeypatch):
    """Bánh cóc: máy từng chạy có thể có dữ liệu của khách — ⛔ không dọn."""
    from apps.vps import bao_tri

    _may_hong(db, co_thu_phi=True, da_tung_chay=True)
    da_nop = _bat_job_xoa(monkeypatch)

    bao_tri._hoan_may_tao_hong(db)

    assert da_nop == []


def test_khong_nop_xoa_hai_lan_cho_cung_mot_may(db, monkeypatch):
    """`_nop_job_xoa` dedupe theo máy, nhưng vòng lặp cũng không được đếm khống."""
    from apps.vps import bao_tri

    _may_hong(db, co_thu_phi=False)
    goi = []
    monkeypatch.setattr(bao_tri, "_nop_job_xoa",
                        lambda db, may: goi.append(may.id) or False)

    bao_tri._hoan_may_tao_hong(db)
    bao_tri._hoan_may_tao_hong(db)

    assert len(goi) == 2, "van hoi moi luot (dedupe o hang doi), nhung khong duoc no"


def test_vong_bao_tri_THAT_SU_chay_phep_soi_do_dien(db, monkeypatch):
    """LỖ 2: `doi_chieu.quet` phải **chạy thật** trong một lượt bảo trì.

    ⛔ Không đo bằng "có lời gọi tới `_doi_chieu_dinh_ky`": `mot_luot` đặt
       `client = None` một cách CỐ Ý (máy pinned không đi qua endpoint global),
       nên một lời gọi truyền `client` ấy vào sẽ bị `if client is None: return 0`
       chặn — dây nối đủ, nhưng không có điện. Đo thứ thật: `quet` có chạy không.
    """
    from apps.vps import bao_tri, doi_chieu
    from apps.vps.tables import VpsInfrastructureProfile

    db.add(VpsInfrastructureProfile(
        id="profile-ovh", slug="ovh-sgp-prod", name="OVH", region="sgp",
        status="ACTIVE", accept_new=True, is_default=True,
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH"))
    db.commit()

    da_quet = []
    monkeypatch.setattr(doi_chieu, "quet",
                        lambda db_, client: da_quet.append(client) or doi_chieu.KetQua())
    monkeypatch.setattr(bao_tri, "_doi_chieu_profiles", lambda db_: 0)
    # Phep soi thu tu (25/09) cung cham Proxmox; probe nay dung client gia la mot
    # chuoi nen phai tat no tuong minh, giong moi ham cham CSDL khac o day.
    monkeypatch.setattr(bao_tri, "_kiem_chuan_hoa_dinh_ky", lambda *a, **k: 0)
    monkeypatch.setattr(bao_tri.backend_factory, "compute_backend",
                        lambda profile: type("B", (), {"client": "proxmox-that"})())
    for ten in ("_thu_tien_den_han", "_treo_may_het_han", "_dong_bo_bang_thong",
                "_chup_anh_den_han", "_hoan_may_tao_hong", "_don_thao_tac_qua_han",
                "_chinh_sach_ip_rong", "_dong_bo_bang_thong_pinned"):
        if hasattr(bao_tri, ten):
            monkeypatch.setattr(bao_tri, ten, lambda *a, **k: 0)
    bao_tri._moc_doi_chieu = 0.0

    bao_tri.mot_luot(db)

    assert da_quet == ["proxmox-that"], "phep soi do dien khong chay, hoac chay voi client rong"


def test_hai_phep_soi_co_MOC_RIENG(db, monkeypatch):
    """Một mốc dùng chung = phép soi chạy sau bị khoá 24 giờ, im lặng.

    ⛔ Đo bằng hành vi, không bằng tên biến: cho `_doi_chieu_profiles` chạy
       trước, rồi đòi `_doi_chieu_dinh_ky` VẪN chạy trong cùng lượt.
    """
    from apps.vps import bao_tri, doi_chieu

    da_quet = []
    monkeypatch.setattr(doi_chieu, "quet",
                        lambda db_, client: da_quet.append(1) or doi_chieu.KetQua())
    # Mốc là biến module: dọn cả hai để phép đo nói về LƯỢT NÀY, không về lượt
    # của một test đứng trước trong cùng tiến trình.
    monkeypatch.setattr(bao_tri, "_moc_doi_chieu", 0.0)
    monkeypatch.setattr(bao_tri, "_moc_doi_chieu_profile", 0.0)

    # Lượt đối chiếu profile chạy TRƯỚC và đặt mốc của NÓ.
    bao_tri._doi_chieu_profiles(db)
    bao_tri._doi_chieu_dinh_ky(db, object())

    assert da_quet, "phep soi do dien bi mot moc cua ham khac khoa lai"
