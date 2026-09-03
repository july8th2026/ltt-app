"""Pha 17 §1 — phan loai loi co kieu, va phep dich sang phan loai cua nen tang.

Bat bien duy nhat o day: **khong mot loai loi nao cua Auto Scan duoc roi xuong
nhanh mac dinh `"retry"` cua nen tang chi vi nen tang chua tung nghe ten no.**

Ba hau qua that neu no roi:

  * `MediaError` -> thu lai ba lan mot tep nguon khong co tieng;
  * `GiongMoHo` -> thu lai mot lan sinh tieng **co the da tinh tien** (I5/G7);
  * `MayBan`    -> dot mot lan thu cho mot dieu kien se tu het, roi hong han.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import loi
from apps.auto_scan_video.ban_dung import BanDungError
from apps.auto_scan_video.ban_ghi import BanGhiError
from apps.auto_scan_video.dich_thuat import DichError, DichMoHo
from apps.auto_scan_video.giai_doan_ban_dung import ThieuDauVao
from apps.auto_scan_video.giai_doan_chep_loi import ThieuBanTieng
from apps.auto_scan_video.giai_doan_giong import ThieuBanDich
from apps.auto_scan_video.giai_doan_ket_xuat import ThieuBanDung
from apps.auto_scan_video.giai_doan_qc import ThieuBanRa
from apps.auto_scan_video.qc import QcError
from apps.auto_scan_video.thi_hanh import QcChan
from apps.auto_scan_video.giai_doan_media import ThieuNguon
from apps.auto_scan_video.giai_doan_noi_dung import ThieuBanGhi
from apps.auto_scan_video.giai_doan_thoi_gian import ThieuDauVao as ThieuDauVaoTG
from apps.auto_scan_video.features import TinhHaiLan
from apps.auto_scan_video.giong_noi import GiongError, GiongMoHo, MayBan
from apps.auto_scan_video.ket_xuat import KetXuatError
from apps.auto_scan_video.nhap_media import MediaError
from apps.auto_scan_video.thoi_gian import ThoiGianError
from apps.auto_scan_video.van_ban import VanBanError

#: Moi lop ngoai le co kieu ma Auto Scan nem ra, va loai mong doi.
#:
#: ⭐ Chot bang TAP HOP: `test_moi_lop_ngoai_le_deu_co_mat` doi chieu bang nay
#:    voi ma nguon, nen them mot lop ngoai le moi ma quen phan loai se lam do —
#:    chu khong doi toi luc no roi xuong nhanh mac dinh trong production.
BANG = {
    MayBan: loi.BAN,
    GiongMoHo: loi.MO_HO,
    DichMoHo: loi.MO_HO,
    MediaError: loi.NGUOI_DUNG,
    ThieuNguon: loi.THIEU_THUONG_NGUON,
    ThieuDauVao: loi.THIEU_THUONG_NGUON,
    ThieuDauVaoTG: loi.THIEU_THUONG_NGUON,
    ThieuBanTieng: loi.THIEU_THUONG_NGUON,
    ThieuBanDich: loi.THIEU_THUONG_NGUON,
    ThieuBanDung: loi.THIEU_THUONG_NGUON,
    ThieuBanGhi: loi.THIEU_THUONG_NGUON,
    ThieuBanRa: loi.THIEU_THUONG_NGUON,
    #: QC hong = loi cua KET QUA. Chay lai cung mot ban render cho cung mot
    #: phep do, nen thu lai la ba lan cho vo ich.
    QcChan: loi.NGUOI_DUNG,
    #: `QcError` KHAC `QcChan`: khong CHAY duoc phep do (vd ffmpeg tach), chu
    #: khong phai da do va ket qua hong. Cai dau thu lai duoc, cai sau thi khong.
    QcError: loi.TAM_THOI,
    BanGhiError: loi.NGUOI_DUNG,
    VanBanError: loi.NGUOI_DUNG,
    ThoiGianError: loi.NGUOI_DUNG,
    BanDungError: loi.NGUOI_DUNG,
    KetXuatError: loi.TAM_THOI,
    GiongError: loi.TAM_THOI,
    DichError: loi.TAM_THOI,
    #: 🔴 `TinhHaiLan` la mot lech SO SACH, khong phai mot truot thoang qua.
    #:    Roi xuong nhanh mac dinh `TAM_THOI` nghia la nen tang **THU LAI** —
    #:    va thu bi thu lai la mot lan chay ma so tien cua no da duoc phat hien
    #:    la sai. Chay lai khong sua duoc mot giai doan vua co don vi viec vua
    #:    tu ghi `credit_actual`; no chi lam viec do them mot lan nua.
    #:
    #: ⭐ Nhan `NGUOI_DUNG` o day khong co nghia "khach lam sai" — trong bang
    #:    nay no la nhan cua *that bai cuoi cung, dung thu lai*.
    TinhHaiLan: loi.NGUOI_DUNG,
}


@pytest.mark.parametrize("lop,mong", list(BANG.items()))
def test_phan_loai_dung(lop, mong):
    assert loi.phan_loai(lop("x")) == mong


def test_KetXuatError_la_TAM_THOI_du_no_ke_thua_MediaError():
    """⚠️ Bay thu tu isinstance, va no co that o day.

    `KetXuatError(MediaError)`. Neu hoi `MediaError` truoc thi mot lan render
    hong — thuong la het cho dia hay tien trinh con bi giet — se bi xep la loi
    cua nguoi dung va **khong bao gio duoc thu lai**.
    """
    assert issubclass(KetXuatError, MediaError)
    assert loi.phan_loai(KetXuatError("het cho dia")) == loi.TAM_THOI
    assert loi.phan_loai(MediaError("video khong co tieng")) == loi.NGUOI_DUNG


def test_ThieuNguon_la_THIEU_THUONG_NGUON_chu_KHONG_phai_loi_nguoi_dung():
    """⭐ Hanh vi giong `NGUOI_DUNG` (khong thu lai) nhung TEN thi khac, va cai
    ten la thu duy nhat nguoi doc log co.

    "COMPOSE chay khi TIMING chua co ket qua" khong phai loi cua khach — khach
    khong lam gi ca. Goi no la loi cua nguoi dung se dan mot nguoi dieu tra di
    soi tep khach gui len, trong khi nguyen nhan nam o thu tu giai doan.
    """
    assert issubclass(ThieuNguon, MediaError)
    assert loi.phan_loai(ThieuNguon("khong co tep nguon")) == loi.THIEU_THUONG_NGUON
    # ...nhung van khong duoc thu lai, giong `NGUOI_DUNG`.
    from platform_core.job_runner import _provider_failure_kind
    moi = loi.dich_sang_loi_nen_tang(ThieuDauVao("chua co ban dung"))
    assert _provider_failure_kind(moi, provider_state="")[0] == "loi_nguoi_goi"


def test_ngoai_le_la_hoac_mac_dinh_TAM_THOI():
    """Mac dinh phai la `TAM_THOI`, khong phai `NGUOI_DUNG`.

    Xep nham mot loi he thong thanh loi nguoi dung se **tu choi thu lai** mot
    truot thoang qua — hong theo huong lam khach mat viec, chu khong phai huong
    ton them mot lan thu.
    """
    assert loi.phan_loai(RuntimeError("gi do la")) == loi.TAM_THOI
    assert loi.phan_loai(ZeroDivisionError()) == loi.TAM_THOI


# ══════════════════════════════════════════════════════════════════════════════
#  Phep dich sang loai cua nen tang
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nguoi_dung_thanh_LoiNguoiGoi_KHONG_thu_lai():
    from platform_core import jobs as jobq
    from platform_core.job_runner import _provider_failure_kind

    moi = loi.dich_sang_loi_nen_tang(MediaError("video khong co luong tieng"))
    assert isinstance(moi, jobq.LoiNguoiGoi)
    kind, _ = _provider_failure_kind(moi, provider_state="")
    assert kind == "loi_nguoi_goi", "van roi xuong nhanh retry"


def test_may_ban_thanh_BanError_XEP_LAI_chu_khong_dot_mot_lan_thu():
    from platform_core.job_runner import _provider_failure_kind
    from platform_core.llm.cong_vlm import BanError

    moi = loi.dich_sang_loi_nen_tang(MayBan("may sinh tieng dang ban"))
    assert isinstance(moi, BanError)
    kind, cho = _provider_failure_kind(moi, provider_state="")
    assert kind == "resource_wait"
    assert cho >= 1, "phai co khoang cho, khong xep lai ngay lap tuc"


def test_mo_ho_thanh_AmbiguousProviderError_KHONG_BAO_GIO_tu_dong_thu_lai():
    """I5/G7. Mot lan goi co the da tinh tien; thu lai la tra tien hai lan."""
    from platform_core.job_runner import _provider_failure_kind
    from platform_core.llm.cong_vlm import AmbiguousProviderError

    for exc in (GiongMoHo("mat ket noi"), DichMoHo("mat ket noi")):
        moi = loi.dich_sang_loi_nen_tang(exc)
        assert isinstance(moi, AmbiguousProviderError)
        kind, _ = _provider_failure_kind(moi, provider_state="")
        assert kind == "ambiguous"


def test_loi_TAM_THOI_duoc_giu_NGUYEN_de_nen_tang_thu_lai():
    """Khong boc lai thu da dung. Boc them mot lop chi lam log kho doc hon."""
    goc = KetXuatError("ffmpeg bi giet")
    assert loi.dich_sang_loi_nen_tang(goc) is goc


def test_phep_dich_GIU_chuoi_nguyen_nhan():
    """⛔ Dich khong duoc lam mat dau vet. Nguoi doc log phai van thay loai goc."""
    goc = MediaError("video khong co luong tieng")
    moi = loi.dich_sang_loi_nen_tang(goc)
    assert moi.__cause__ is goc


def test_phep_dich_GIU_thong_diep_cho_khach():
    """Thong diep da qua `_t()` va la thu khach doc duoc. Nuot no la doi mot cau
    giai thich lay mot ma loi."""
    moi = loi.dich_sang_loi_nen_tang(MediaError("video khong co luong tieng"))
    assert "khong co luong tieng" in str(moi)


# ══════════════════════════════════════════════════════════════════════════════
#  Chot TAP HOP — them mot lop ngoai le moi ma quen phan loai thi DO
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_lop_ngoai_le_cua_app_deu_duoc_phan_loai():
    """Doi chieu bang tren voi MA NGUON, hai chieu.

    ⚠️ Loai tru co ghi ro ly do, khong phai mot danh sach im lang:
    `AsvError`/`KhongTimThay`/`XungDot` la loi **nghiep vu o tang route**, khong
    bao gio bay ra tu than mot giai doan; `AssetError` bi `promote_va_ghi` bat
    va doi thanh loai khac truoc khi len toi bien; `DaHuy` khong phai that bai —
    `job_runner` xu ly job da huy o mot nhanh rieng, TRUOC moi phep phan loai.
    """
    import ast
    import pathlib

    from apps.auto_scan_video import loi as _loi

    goc = pathlib.Path(_loi.__file__).resolve().parent
    NGOAI_LE = {
        "AsvError", "KhongTimThay", "XungDot",   # tang route, khong len toi bien
        "AssetError",                            # bi doi loai truoc khi len bien
        "DaHuy",                                 # nhanh rieng cua job_runner
    }

    # ⚠️ Gom lop cha theo CA HAI dang: `class X(MediaError)` (`ast.Name`) va
    #    `class X(nhap_media.MediaError)` (`ast.Attribute`). Ban dau chi doc
    #    `Name`, nen `ThieuNguon` vo hinh voi phep quet.
    khai: dict[str, set[str]] = {}
    for tep in sorted(goc.glob("*.py")):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for nut in cay.body:
            if not isinstance(nut, ast.ClassDef):
                continue
            cha = set()
            for b in nut.bases:
                if isinstance(b, ast.Name):
                    cha.add(b.id)
                elif isinstance(b, ast.Attribute):
                    cha.add(b.attr)
            khai[nut.name] = cha

    # ⚠️ Lap toi diem bat dong, KHONG duyet mot luot theo thu tu tep. Ban dau
    #    duyet mot luot va `KetXuatError(MediaError)` bi bo sot chi vi
    #    `ket_xuat.py` dung truoc `nhap_media.py` theo bang chu cai — mot phep
    #    kiem ma ket qua phu thuoc ten tep thi no dang do ten tep.
    thay: set[str] = set()
    while True:
        them = {ten for ten, cha in khai.items()
                if ten not in thay
                and (cha & {"ValueError", "RuntimeError", "Exception"}
                     or cha & thay)}
        if not them:
            break
        thay |= them

    da_chot = {c.__name__ for c in BANG} | NGOAI_LE
    thieu = sorted(thay - da_chot)
    assert thieu == [], (
        f"lop ngoai le chua duoc phan loai: {thieu}. Chung se roi xuong nhanh "
        f"mac dinh `retry` cua nen tang — them vao BANG, hoac vao NGOAI_LE kem "
        f"mot ly do")

    thua = sorted({c.__name__ for c in BANG} - thay)
    assert thua == [], f"BANG chot mot lop khong con ton tai: {thua}"
