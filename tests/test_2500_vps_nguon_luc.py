"""So nguon luc VPS: MOT phep tinh tra loi 'ban duoc goi nay khong, vi sao khong'.

🔴 Su co do 23/09/2026. Trang /vps in "Het cho cho cau hinh nay" cho ca ba goi
   trong khi compute con 14/9/6 cho va gateway con 150. Nguyen nhan: profile
   khong qua duoc `health_prerequisites` (mot bo dem goi roi cua May B), ham
   `_gioi_han_ban` bat `ProfileNotReady` roi tra `None`, va `trang_chinh` doc
   `None` thanh `con_cho = False`. Mot loi suc khoe bi dich sai thanh mot loi
   tu choi ban hang — cau khach doc la mot cau SAI SU THAT.

⭐ Hai bai hoc duoc chot bang test o day:
   1. Moi ly do khong ban duoc phai mang DUNG ten cua no (`rang_buoc`), va cau
      cho khach phai khop ly do do. "Het cho" chi duoc dung khi that su het cho.
   2. Cau cho khach khong bao gio chua ten he thong noi bo. Ban cu in nguyen
      `chua cau hinh Proxmox: ... LTT_VPS_PROXMOX_CA ...` ra trang ban hang
      (do 09/09/2026); tach `cau_cho_khach` / `cau_cho_van_hanh` la de chuyen
      do khong lap lai duoc.
"""
from __future__ import annotations

import pytest

from apps.vps.services import capacity
from apps.vps.services import nguon_luc


def _suc_chua(**doi) -> capacity.SucChua:
    """So do that tren production 23/09/2026, cho phep doi tung truong."""
    so = dict(ram_mb_tong=96648, dia_gb_tong=474, ram_mb_da_hua=37888,
              dia_gb_da_hua=690, dia_gb_dang_dung=231, cpu_tong=24,
              vcpu_da_hua=18)
    so.update(doi)
    return capacity.SucChua(**so)


def _do(**doi) -> nguon_luc.DoDuoc:
    # Ngan sach bang thong de rong co y: cac phep duoi day do TUNG rang buoc
    # mot, nen bang thong chi duoc chan khi chinh phep do dat no chan. Viet
    # cung mot con so o day la buoc test nay phu thuoc bang gia cua lan khac.
    so = dict(suc_chua=_suc_chua(), free_ipv4=7, gateway_slots=150,
              da_hua_bang_thong_gb=0, ngan_sach_bang_thong_gb=1_000_000)
    so.update(doi)
    return nguon_luc.DoDuoc(**so)


def _hua_gb(plan_id: str) -> int:
    """Han muc cua mot goi, doc tu bang gia — khong chep so vao test."""
    from apps.vps.cost import lay_plan
    return int(lay_plan(plan_id).bang_thong_gb)


# ── moi rang buoc mang dung ten cua no ───────────────────────────────────────

def test_du_moi_thu_thi_ban_duoc_va_so_cho_la_rang_buoc_chat_nhat():
    kq = nguon_luc.danh_gia(_do(), "vps-nho")
    assert kq.ban_duoc is True
    # compute 14 · ipv4 7 · gateway 150 · bang thong khong chan ⇒ chat nhat la ipv4
    assert kq.so_cho == 7
    assert kq.rang_buoc == nguon_luc.RANG_BUOC_IPV4


def test_khong_doc_duoc_suc_chua_la_SUC_KHOE_chu_khong_phai_het_cho():
    """Chinh ca do 23/09: suc khoe do khong duoc noi thanh 'het cho'."""
    kq = nguon_luc.danh_gia(_do(suc_chua=None), "vps-nho")
    assert kq.ban_duoc is False
    assert kq.so_cho == 0
    assert kq.rang_buoc == nguon_luc.RANG_BUOC_SUC_KHOE
    assert "hết chỗ" not in kq.cau_cho_khach.lower()


@pytest.mark.parametrize("truong", ["free_ipv4", "gateway_slots"])
def test_khong_doc_duoc_gioi_han_nao_cung_la_SUC_KHOE(truong):
    kq = nguon_luc.danh_gia(_do(**{truong: None}), "vps-nho")
    assert kq.rang_buoc == nguon_luc.RANG_BUOC_SUC_KHOE
    assert kq.ban_duoc is False


def test_het_ipv4_noi_ve_dia_chi_IP_chu_khong_noi_het_cho():
    kq = nguon_luc.danh_gia(_do(free_ipv4=0), "vps-nho")
    assert kq.ban_duoc is False
    assert kq.rang_buoc == nguon_luc.RANG_BUOC_IPV4
    assert "hết chỗ" not in kq.cau_cho_khach.lower()
    assert "IP" in kq.cau_cho_khach


def test_can_ngan_sach_bang_thong_thi_rang_buoc_la_bang_thong():
    # Ngan sach con it hon DUNG MOT may goi Vua ⇒ bang thong la rang buoc,
    # du compute/ipv4/gateway deu con. So lay tu bang gia, khong chep tay.
    hua = _hua_gb("vps-vua")
    kq = nguon_luc.danh_gia(
        _do(da_hua_bang_thong_gb=0, ngan_sach_bang_thong_gb=hua - 1), "vps-vua")
    assert kq.ban_duoc is False
    assert kq.rang_buoc == nguon_luc.RANG_BUOC_BANG_THONG


def test_ngan_sach_du_dung_mot_may_thi_van_ban_duoc_may_do():
    """Ranh gioi duoi: du cho DUNG mot may la ban duoc, khong phai tu choi.

    `bang_thong` van la rang buoc chat nhat o day (1 < ipv4 7) — dung the. Cai
    phai dung la `ban_duoc`, khong phai ten rang buoc.
    """
    hua = _hua_gb("vps-vua")
    kq = nguon_luc.danh_gia(
        _do(da_hua_bang_thong_gb=0, ngan_sach_bang_thong_gb=hua), "vps-vua")
    assert kq.ban_duoc is True
    assert kq.so_cho == 1


def test_het_compute_thi_rang_buoc_la_compute_vi_doi_goi_con_cuu_duoc():
    """Compute la rang buoc DUY NHAT ma khach tu xu ly duoc (chon goi nho hon)."""
    kq = nguon_luc.danh_gia(_do(suc_chua=_suc_chua(dia_gb_da_hua=1287)),
                            "vps-lon")
    assert kq.ban_duoc is False
    assert kq.rang_buoc == nguon_luc.RANG_BUOC_COMPUTE


def test_goi_khong_co_trong_bang_gia_khong_ban_duoc():
    kq = nguon_luc.danh_gia(_do(), "vps-khong-ton-tai")
    assert kq.ban_duoc is False
    assert kq.so_cho == 0


# ── cau cho khach khong bao gio lo he thong noi bo ───────────────────────────

CAM = ("proxmox", "ovh", "vultr", "wireguard", "profile", "ipv4_slots",
       "ltt_vps", "gateway", "nft", "backend", "traceback", "exception")


@pytest.mark.parametrize("rang_buoc", sorted(nguon_luc.CAU_CHO_KHACH))
def test_moi_cau_cho_khach_khong_chua_ten_he_thong_noi_bo(rang_buoc):
    """Do 09/09/2026: trang ban hang in nguyen ten bien moi truong va 'Proxmox'."""
    cau = str(nguon_luc.CAU_CHO_KHACH[rang_buoc]).lower()
    assert cau, f"{rang_buoc} thieu cau cho khach"
    for tu in CAM:
        assert tu not in cau, f"cau cho khach cua {rang_buoc} lo '{tu}': {cau}"


def test_moi_rang_buoc_deu_co_mot_cau_cho_khach():
    """Them mot rang buoc ma quen cau cho khach = mot trang im lang."""
    for ten in (nguon_luc.RANG_BUOC_COMPUTE, nguon_luc.RANG_BUOC_IPV4,
                nguon_luc.RANG_BUOC_GATEWAY, nguon_luc.RANG_BUOC_BANG_THONG,
                nguon_luc.RANG_BUOC_SUC_KHOE):
        assert ten in nguon_luc.CAU_CHO_KHACH


def test_cau_cho_van_hanh_co_so_lieu_de_no_dang_duoc_ghi_log():
    kq = nguon_luc.danh_gia(_do(free_ipv4=0), "vps-nho")
    assert "ipv4" in kq.cau_cho_van_hanh
    assert "0" in kq.cau_cho_van_hanh
