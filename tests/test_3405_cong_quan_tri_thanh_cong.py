"""Phép kiểm cổng quản trị phải là một CỔNG, không phải một lệnh chạy tay.

🔴 24/09/2026 buổi chiều: `tcp dport 22 accept` không nêu địa chỉ đích ⇒ SSH của
   cổng vào trả lời trên **cả 11 địa chỉ IPv4**, gồm địa chỉ vừa bán cho khách.
   Đã chặn, và `tools/vps_doi_soat_cong.py` đo được.

⚠️ Nhưng một phép kiểm an ninh **chạy bằng tay** gộp hai trạng thái vào cùng một
   sự im lặng: *"chưa ai chạy"* và *"chạy rồi, đạt"*. Đúng khuôn đã cắn sáu lần
   trong một ngày — một giá trị mang hai nghĩa, và ta mất khả năng phân biệt.

⇒ Vòng bảo trì phải tự đo và **ghi một bản ghi sức khoẻ** mỗi lượt, cả khi đạt
  lẫn khi hỏng. Thiếu bản ghi = STALE trên trang admin, khác hẳn "đạt".

⚠️ Thành phần này phải nằm NGOÀI `REQUIRED_HEALTH_COMPONENTS` — `preflight`
   duyệt tập đó và đòi trạng thái cho từng thành phần, nên thêm vào đấy một thứ
   nó không đo được là một `KeyError` giữa đường đo sức khoẻ (bài học 23/09).
"""
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


def _profile(db):
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile, VpsIp

    p = VpsInfrastructureProfile(
        id="profile-ovh", slug="ovh-sgp-prod", name="OVH", region="sgp",
        status="ACTIVE", accept_new=True, is_default=True,
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH")
    gw = VpsGateway(id="gw", infrastructure_profile_id=p.id, ten="gw",
                    vung="sgp", ip_cong_khai="51.79.166.36")
    db.add_all((p, gw,
                VpsIp(id="ip1", gateway_id="gw", dia_chi="51.79.215.194",
                      state="BOUND", infrastructure_profile_id=p.id),
                VpsIp(id="ip2", gateway_id="gw", dia_chi="15.235.149.206",
                      state="QUARANTINED", infrastructure_profile_id=p.id)))
    db.commit()
    return p


def _ban_ghi(db, thanh_phan):
    from apps.vps.tables import VpsProfileHealth

    return db.execute(select(VpsProfileHealth).where(
        VpsProfileHealth.component == thanh_phan)).scalars().all()


def test_cong_dong_het_thi_ghi_HEALTHY(db):
    from apps.vps import bao_tri

    p = _profile(db)
    bao_tri._kiem_cong_quan_tri(db, p, mo_cong=lambda ip, cong: (
        ip == "51.79.166.36", "gia lap"))
    db.commit()

    ban = _ban_ghi(db, bao_tri.THANH_PHAN_CONG_QUAN_TRI)
    assert len(ban) == 1 and ban[0].status == "HEALTHY"


def test_cong_22_LO_tren_IP_khach_thi_ghi_CRITICAL_kem_dia_chi(db):
    """Đây là ca thật của chiều 24/09, và nó phải kêu to nhất."""
    from apps.vps import bao_tri

    p = _profile(db)
    bao_tri._kiem_cong_quan_tri(db, p, mo_cong=lambda ip, cong: (True, "gia lap"))
    db.commit()

    ban = _ban_ghi(db, bao_tri.THANH_PHAN_CONG_QUAN_TRI)
    assert len(ban) == 1 and ban[0].status == "CRITICAL"
    assert "51.79.215.194" in ban[0].summary


def test_mat_duong_quan_tri_cung_phai_keu(db):
    """Chặn quá tay cũng là hỏng: cổng 22 đóng trên CHÍNH IP quản trị."""
    from apps.vps import bao_tri

    p = _profile(db)
    bao_tri._kiem_cong_quan_tri(db, p, mo_cong=lambda ip, cong: (False, "gia lap"))
    db.commit()

    ban = _ban_ghi(db, bao_tri.THANH_PHAN_CONG_QUAN_TRI)
    assert ban[0].status in ("CRITICAL", "DEGRADED")
    assert "51.79.166.36" in ban[0].summary


def test_MOI_luot_deu_ghi_mot_ban_ghi(db):
    """'Chưa ai chạy' phải khác 'chạy rồi, đạt' — nên im lặng không được là kết quả."""
    from apps.vps import bao_tri

    p = _profile(db)
    for _ in range(3):
        bao_tri._kiem_cong_quan_tri(db, p, mo_cong=lambda ip, cong: (
            ip == "51.79.166.36", ""))
    db.commit()

    assert len(_ban_ghi(db, bao_tri.THANH_PHAN_CONG_QUAN_TRI)) == 3


def test_thanh_phan_nay_NGOAI_tap_bat_buoc():
    """Bài học 23/09: `preflight` duyệt `REQUIRED_HEALTH_COMPONENTS` và đòi
    trạng thái cho từng thành phần ⇒ thêm vào đấy một thứ nó không đo được là
    một `KeyError` giữa đường đo sức khoẻ."""
    from apps.vps import bao_tri, profiles

    assert bao_tri.THANH_PHAN_CONG_QUAN_TRI in profiles.CANH_BAO_BAO_TRI
    assert bao_tri.THANH_PHAN_CONG_QUAN_TRI not in profiles.REQUIRED_HEALTH_COMPONENTS


def test_khong_chan_ban_hang(db):
    """Cổng quản trị lộ là việc của người vận hành, ⛔ không phải lý do đóng cửa
    hàng: khách không làm gì được với tín hiệu này."""
    from apps.vps import bao_tri, profiles

    assert bao_tri.THANH_PHAN_CONG_QUAN_TRI not in profiles.CHAN_BAN


def test_do_SONG_SONG_chu_khong_tuan_tu(db):
    """🔴 Đo thật 24/09: bản đầu đo tuần tự 11 địa chỉ × 6 giây = **66 giây**, và
    vòng bảo trì **mất lease giữa chừng** (`mat lease bao tri — dung viec nen`).

    ⭐ Điều đáng nhớ: trạng thái **ĐÚNG** của mọi địa chỉ khách là *timeout* —
    nên phép kiểm này tốn nhiều thời gian nhất **khi mọi thứ đều ổn**. Một phép
    đo mà chi phí tệ nhất rơi vào ca bình thường sẽ bị gỡ, không phải bị sửa.

    ⛔ Đo bằng thời gian tường, không bằng việc đọc mã: một `ThreadPoolExecutor`
       gọi tuần tự bên trong vẫn "trông như" song song.
    """
    import time

    from apps.vps import bao_tri

    p = _profile(db)

    def cham(ip, cong):
        time.sleep(0.4)
        return (ip == "51.79.166.36", "gia lap cham")

    t0 = time.monotonic()
    bao_tri._kiem_cong_quan_tri(db, p, mo_cong=cham)
    mat = time.monotonic() - t0

    # 3 dia chi (2 IP + IP quan tri) x 0,4s = 1,2s neu tuan tu.
    assert mat < 0.9, f"do tuan tu ({mat:.2f}s) — vong bao tri se mat lease"
