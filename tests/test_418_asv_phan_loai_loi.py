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
from apps.auto_scan_video.cat_dau_cuoi import CatLoi
from apps.auto_scan_video.lop_phu import LopPhuLoi
from apps.auto_scan_video.phu_de import PhuDeLoi
from apps.auto_scan_video.logo import LogoLoi
from apps.auto_scan_video.tu_dien import TuDienLoi
from apps.auto_scan_video.vung_che import VungLoi
from apps.auto_scan_video.ban_ghi import BanGhiError
from apps.auto_scan_video.dich_thuat import DichError, DichMoHo
from apps.auto_scan_video.giai_doan_ban_dung import ThieuDauVao
from apps.auto_scan_video.giai_doan_chep_loi import ThieuBanTieng
from apps.auto_scan_video.giai_doan_giong import ThieuBanDich
from apps.auto_scan_video.giai_doan_ket_xuat import ThieuBanDung
from apps.auto_scan_video.giai_doan_qc import ThieuBanRa
from apps.auto_scan_video.qc import QcError
from apps.auto_scan_video.su_dung import XungDotDonVi
from apps.auto_scan_video.ai import AiError, AiMoHo, LuocDoSai
from apps.auto_scan_video.canh import CanhError
from apps.auto_scan_video.demucs_runner import ThieuCard
from apps.auto_scan_video.long_tieng import LongTiengError, ThieuDoan
from apps.auto_scan_video.am_master import MasterError
from apps.auto_scan_video.ban_do_thoi_gian import BanDoError
from apps.auto_scan_video.che_do_render import CheDoError
from apps.auto_scan_video.qc_ai import QcAiError
from apps.auto_scan_video.sua_chua import SuaChuaError
from apps.auto_scan_video.nan_cho_vua import NanError
from apps.auto_scan_video.ban_bien_tap import BanBienTapError
from apps.auto_scan_video.giai_doan_ban_bien_tap import ThieuChiMuc
from apps.auto_scan_video.hieu_canh import HieuCanhError
from apps.auto_scan_video.rang_giong import ChuaRangError, RangGiongError
from apps.auto_scan_video.su_dung import DaGhiRoi, DoiSoatLech, SuDungError
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

# 🔴 Pha 13: cac phep kiem trong tep nay chay HET chuoi, nen chung cham toi
#    `audio_prepare` — va truoc pha 13 dieu do co nghia la chung nap
#    **htdemucs THAT** moi luot gate, tren mot may dang phuc vu khach.
#    Fixture autouse duoi day thay dung mieng nang do; ffmpeg, kho, CSDL,
#    hang doi va worker van that.  (`LTT_TEST_NANG=1` de chay model that)
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401

#: Moi lop ngoai le co kieu ma Auto Scan nem ra, va loai mong doi.
#:
#: ⭐ Chot bang TAP HOP: `test_moi_lop_ngoai_le_deu_co_mat` doi chieu bang nay
#:    voi ma nguon, nen them mot lop ngoai le moi ma quen phan loai se lam do —
#:    chu khong doi toi luc no roi xuong nhanh mac dinh trong production.
BANG = {
    MayBan: loi.BAN,
    # ⛔ Toa do vung che sai — sai dinh dang, ngoai khoang 0..1, ve
    #    nguoc, hay qua nho. Chay lai cung mot bo toa do hong y het.
    # ⚠️ Hom nay no bi bat ngay trong `routes.tao`, nen chua bao gio
    #    toi duoc `phan_loai`. Chot o day de mot pha sau goi
    #    `vung_che.chuan_hoa` TU TRONG mot job khong roi xuong `retry`.
    VungLoi: loi.NGUOI_DUNG,
    TuDienLoi: loi.NGUOI_DUNG,
    # 🔑 `CatLoi` KHAC hai dong tren o mot cho co that: no **di toi `phan_loai`
    #    hom nay**. `giai_doan_ban_dung` goi `cat_dau_cuoi.giao` ben trong mot
    #    JOB, va `giao` nem khi cua so cat khong cham khoang giu nao.
    # ⛔ Thieu dong nay thi mot cua so cat rong roi xuong nhanh `retry`, va ca ba
    #    luot chay lai deu cho cung mot ket qua — cung mot cua so tren cung mot
    #    ban do. Khach cho ba lan de nhan cung mot cau tra loi.
    CatLoi: loi.NGUOI_DUNG,
    # 🔑 `PhuDeLoi` (V6 pha 14) di toi `phan_loai` qua **HAI** duong, va duong
    #    thu hai moi la ly do dong nay ton tai:
    #
    #      `phu_de.tu_form`       bat ngay o `routes.tao` — chua toi `phan_loai`
    #      `phu_de.viet_tep_ass`  goi tu `giai_doan_ket_xuat`, tuc TU TRONG mot
    #                             JOB, dung luc dung tep `.ass`
    #
    # ⛔ Mot kieu chu khong con ton tai — `autosubvideo` doi ten mot preset — se
    #    nem giua giai doan ket xuat. Roi xuong `retry` thi ba luot deu hong y
    #    het: cung mot ho so, cung mot id da bien mat, va moi luot ton mot suat
    #    render.
    PhuDeLoi: loi.NGUOI_DUNG,
    # 🔑 `LopPhuLoi` di toi `phan_loai` qua **HAI** duong, va duong thu hai moi
    #    la ly do dong nay ton tai:
    #
    #      `routes.tao`            bat ngay tai cho — chua toi `phan_loai`
    #      `lop_phu.duong_font()`  goi tu `che_do_render._loc_chu`, tuc tu trong
    #                              mot JOB, dung luc dung chuoi loc
    #      `lop_phu.vien_px()`     nhu tren
    #
    # ⛔ Mot may chu khong co phong chu nao se nem giua giai doan ket xuat. Roi
    #    xuong `retry` thi ba lan chay lai deu hong y het — may van khong co
    #    phong chu — va khach cho ba lan de nhan cung mot cau tra loi.
    LopPhuLoi: loi.NGUOI_DUNG,
    # Cung nhom, cung ly do: `logo.rong_px()` duoc goi tu
    # `che_do_render._loc_logo`, tuc tu trong mot JOB. Mot ban dung thieu
    # `rong_khung` se nem giua giai doan ket xuat, va ba luot thu lai deu
    # hong y het — cung mot ban dung, cung mot truong thieu.
    LogoLoi: loi.NGUOI_DUNG,
    # ⭐ THU LAI la viec dung: nen tang co the cap mot card KHAC lan sau. Truoc
    #    pha 13 truong hop nay khong nem gi ca — no **im lang chay CPU**, cham
    #    hon 9,5 lan, va giu suat `tach_nguon_cuc_bo` suot ~37 phut o tran 2 gio.
    ThieuCard: loi.TAM_THOI,
    # ⛔ Loi HOP DONG voi model: thu lai la tra tien lan hai cho cung mot cau tra
    #    loi sai. Xem ghi chu trong `loi.py`.
    LongTiengError: loi.NGUOI_DUNG,
    ThieuDoan: loi.NGUOI_DUNG,
    # ⭐ Khac hai lop tren: model tra ve mot cau viet lai khong doc duoc la mot
    #    truot ngau nhien, khong phai mot loi hop dong. Lan sau thuong duoc.
    NanError: loi.TAM_THOI,
    # ⭐ TAM_THOI — thua mot cuoc dua khong phai mot loi. `XungDotDonVi` nghia
    #    la mot tien trinh khac vua ghi dong don vi viec nay giua chung: du lieu
    #    khong sai, ta chi cham chan. Doc lai lan sau thuong khong con gi de lam.
    #
    # ⚠️ Lop nay ra doi o pha 27 cung voi phep UPDATE co dieu kien tren
    #    `AsvWorkItem.revision` — truoc do cuoc dua ket thuc bang mot ban ghi de
    #    im lang, tuc khong co gi de phan loai vi khong co gi duoc nem.
    XungDotDonVi: loi.TAM_THOI,
    # ⛔ Ket luan cua mot phep tinh TAT DINH: lan thu hai cho dung ket qua do.
    BanDoError: loi.NGUOI_DUNG,
    MasterError: loi.NGUOI_DUNG,
    CheDoError: loi.NGUOI_DUNG,
    SuaChuaError: loi.NGUOI_DUNG,
    QcAiError: loi.NGUOI_DUNG,
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
    #: ── So cai su dung (pha 06) ─────────────────────────────────────────────
    #:
    #: 🔑 `SuDungError` la **loi lap trinh**, khong phai loi khach: mot ban ghi
    #:    "da giao" thieu don vi do, mot trang thai mo ho mang credit, mot con
    #:    so am. Chay lai cung mot ma se dung y het — `TAM_THOI` chi dot ba lan
    #:    thu cho mot ket qua khong doi.
    SuDungError: loi.NGUOI_DUNG,
    #: 🔴 `DoiSoatLech` nguy hiem nhat khi bi thu lai: no la luc **tien cua mot
    #:    don vi viec khong khop voi bang chung cua chinh no**. Thu lai mot lan
    #:    quyet toan da phat hien lech la co chot lai dung con so sai do.
    DoiSoatLech: loi.NGUOI_DUNG,
    #: ⭐ `DaGhiRoi` nguoc lai — no la mot **thanh cong**: rang buoc
    #:    `UNIQUE(run_id, ma_dispatch)` vua chan mot lan tinh tien thu hai.
    #:    Nguoi goi phai bat va di tiep; neu no len toi bien thi ai do da khong
    #:    bat, va thu lai chi lam CSDL tu choi them mot lan nua.
    DaGhiRoi: loi.NGUOI_DUNG,
    #: ── Cua goi model (pha 08) ──────────────────────────────────────────────
    #:
    #: 🔑 `AiMoHo` = mat ket noi SAU khi da gui. Cung nghia voi `DichMoHo`/
    #:    `GiongMoHo`: khong biet model da chay chua, nen khong duoc thu lai mu.
    AiMoHo: loi.MO_HO,
    #: ⭐ `AiError` va con cua no `LuocDoSai` roi vao `TAM_THOI` CO CHU Y: model
    #:    la ngau nhien, nen mot lan sinh ra JSON sai hinh dang thuong het o lan
    #:    sau. Khac han `QcChan` — mot phep do TAT DINH chay lai cho ra dung ket
    #:    qua cu, nen thu lai no la ba lan cho vo ich.
    AiError: loi.TAM_THOI,
    LuocDoSai: loi.TAM_THOI,
    #: ── Rang giong (pha 09) ─────────────────────────────────────────────
    #:
    #: 🔑 Ca hai la that bai CUOI CUNG. `RangGiongError` = yeu cau khong hop
    #:    le (che do bia ra, USER_SELECTED de trong ma giong) — chay lai cung
    #:    mot thiet lap se hong y het. `ChuaRangError` = doc giong tu mot rang
    #:    buoc chua chot, tuc mot loi LAP TRINH o tang goi: thu lai khong lam
    #:    `HoSoNoiDung` xuat hien.
    RangGiongError: loi.NGUOI_DUNG,
    ChuaRangError: loi.NGUOI_DUNG,
    #: ⭐ `CanhError` la `TAM_THOI`: gan nhu luon la mot lan ffmpeg khong
    #:    chay duoc. No cung dung cho "chi muc sai hinh dang" — thu lai vo
    #:    ich — nhung hai truong hop khong tach duoc bang mot lop, va chon
    #:    `TAM_THOI` la hong ve phia ton them mot lan thu chu khong phai ve
    #:    phia lam khach mat viec.
    CanhError: loi.TAM_THOI,
    #: 🔴 Cho de xep nham nhat trong bang. `HieuCanhError` nghia la model
    #:    DA CHAY, DA tinh tien, va tra ve phan hoi sai luoc do. Thu lai la
    #:    **tra tien lan hai cho mot canh da tra tien**.
    #:
    #: ⚠️ Khac han `ai.LuocDoSai` (TAM_THOI): o do phep doc JSON that bai o
    #:    tang VAN CHUYEN, truoc khi ta biet noi dung co nghia gi. O day ta
    #:    da doc duoc JSON va no MANG MOT GIA TRI SAI.
    HieuCanhError: loi.NGUOI_DUNG,
    #: 🔑 `BanBienTapError` = ban khong dat chinh sach an toan (cat sach,
    #:    giu duoi san, thao tac cat lot vao che do giu nguyen hinh). Ba
    #:    dieu do la ket luan cua mot phep tinh TAT DINH tren cung du lieu —
    #:    chay lai cho ra dung ket qua cu.
    BanBienTapError: loi.NGUOI_DUNG,
    #: ⭐ `ThieuChiMuc` ke thua `ThieuNguon` nen HANH VI da dung san — nhung
    #:    bang nay chot TAP HOP, khong chot hanh vi. Mot lop khong co trong
    #:    day la mot lop khong ai quyet dinh so phan, va lan sau ai do doi
    #:    cay ke thua thi khong gi bao.
    ThieuChiMuc: loi.THIEU_THUONG_NGUON,
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
        # 🔑 Chi song trong TIEN TRINH CON demucs. Chot an toan cua pha 13 nem no
        #    khi mot phep kiem cham toi model that; production khong bao gio co
        #    `PYTEST_CURRENT_TEST` nen no khong the len toi bien cua nen tang.
        "ChayTrongBoTest",
        # 🔑 `ThieuBanBienTap` ke thua `ThieuNguon` — da co trong BANG. No chi dat
        #    ten cho MOT truong hop thieu thuong nguon cu the.
        "ThieuBanBienTap",
        # 🔑 Chi song trong `giai_doan_giong._viet_lai`, bi bat ngay tai cho de
        #    dung bac thang nan — khong bao gio len toi bien cua nen tang.
        "_KhongNanDuoc",
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
