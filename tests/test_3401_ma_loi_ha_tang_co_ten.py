"""Lỗi hạ tầng phải mang tên của nó — nhất là lỗi *có thể đã tiêu tiền*.

🔴 Đo 24/09/2026: `vps_event` của máy `c74d4fd8` ghi `{'ma_loi': 'khong_ro'}` ba
   lần cho một `BackendConflict`. Log vận hành có tên lỗi
   (`job_runner | job … that bai: BackendConflict: …`), nhưng **khách** đọc
   *"Thao tác không hoàn tất"* và **mã tra cứu thì mất**.

Nguy hiểm nhất là `AcquisitionNeedsReview`: nó nghĩa là *một đơn mua IP có thể
đã được trả tiền* và cần người xác nhận. Khách đọc "thao tác không hoàn tất" sẽ
bấm tạo máy lần nữa — tức đơn thứ hai, địa chỉ thứ hai, tiền thật lần thứ hai.
"""
import pytest


@pytest.mark.parametrize("ma", ["ha_tang_tu_choi", "cap_ip_can_ra_soat"])
def test_ma_moi_co_cau_cho_khach(ma):
    from apps.vps import nhan

    cau = nhan.MA_LOI[ma]
    assert cau and cau != nhan.MA_LOI_KHONG_RO


@pytest.mark.parametrize("cam", ["OVH", "Proxmox", "BackendConflict", "8006",
                                 "LTT_OVH", "cart", "checkout"])
def test_cau_khong_ro_ten_he_thong_noi_bo(cam):
    from apps.vps import nhan

    for ma in ("ha_tang_tu_choi", "cap_ip_can_ra_soat"):
        assert cam.lower() not in nhan.MA_LOI[ma].lower()


def test_can_ra_soat_noi_khach_DUNG_tao_lai():
    """Câu phải nói việc khách cần làm, và việc đó là **đừng** tạo máy khác."""
    from apps.vps import nhan

    cau = nhan.MA_LOI["cap_ip_can_ra_soat"].lower()
    assert "đừng" in cau or "khong tao" in cau or "không tạo" in cau


def test_ngoai_le_mua_ip_duoc_phan_loai_dung(monkeypatch):
    """Sợi dây thật: ngoại lệ → mã. ⛔ Không đo bằng bảng, đo bằng hàm phân loại."""
    from apps.vps import jobs
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.ovh_acquisition import AcquisitionNeedsReview

    assert jobs._ma_loi_cua(AcquisitionNeedsReview("x")) == "cap_ip_can_ra_soat"
    assert jobs._ma_loi_cua(BackendConflict("y")) == "ha_tang_tu_choi"
