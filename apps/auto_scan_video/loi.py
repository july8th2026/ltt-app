"""Phan loai loi cua Auto Scan -> phan loai cua NEN TANG (Prompt 17 muc 1).

## Van de ma tep nay lap

`platform_core/job_runner.py:573 _provider_failure_kind` da co mot phan loai
day du va tot: `loi_nguoi_goi` · `resource_wait` · `rejected` · `ambiguous` ·
`retry`. Nhung no nhan dien bang **isinstance tren cac lop ngoai le cua provider
LLM**, va moi thu khac roi xuong nhanh mac dinh `"retry"`.

Auto Scan nem chin loai ngoai le co kieu cua rieng no. Khong loai nao trong so
do duoc nhan dien, nen **tat ca** deu roi vao `"retry"`. Ba hau qua that:

  🔴 `MediaError` / `ThieuNguon` — "tep nguon khong co luong tieng", "video dai
     hon tran". Day la du lieu khach gui len. Thu lai **ba lan** mot viec khong
     bao gio thanh cong: ba suat xep hang, ba lan cho, cung mot ket qua.

  🔴 `GiongMoHo` / `DichMoHo` — da co the goi toi may sinh tieng hay model roi
     mat ket noi. `_provider_failure_kind` chi coi la `ambiguous` khi
     `provider_state == dispatched`, ma `giong_noi` goi mot DICH VU cuc bo chu
     khong qua `dieu_phoi`, nen no khong bao gio dat co do. ⇒ Thu lai mot lan
     goi **co the da tinh tien**. Dung dieu ma I5/G7 sinh ra de chan.

  🔴 `MayBan` — may sinh tieng dang ban. **Ban khong phai hong.** Roi vao
     `"retry"` nghia la dot mot lan thu cho mot dieu kien se tu het, va sau ba
     lan thi job hong han — trong khi dung ra no chi can xep lai hang doi.
     `apps/ltt_voice/features.py:219` da ghi bai hoc nay bang chu.

⇒ Tep nay khong dung mot phan loai thu hai. No **dich** loai cua ta sang loai
  cua nen tang, ngay tai bien, de mot loi da co kieu dung khong bi tut xuong
  nhanh mac dinh chi vi nen tang chua tung nghe ten no.

## Vi sao dich o BIEN chu khong nem thang loai cua nen tang

Engine (`nhap_media`, `giong_noi`, …) nem loai cua **mien cua chung**. Bat chung
nem `jobq.LoiNguoiGoi` la buoc moi module engine phai biet ve hang doi job — tuc
doi dung ranh gioi ma hop dong app dung len de giu. `thi_hanh` la cho duy nhat
da biet ca hai phia, nen phep dich thuoc ve no.
"""
from __future__ import annotations

#: ⛔ KHONG thu lai. Nguyen nhan la du lieu nguoi dung gui len.
NGUOI_DUNG = "nguoi_dung"
#: ⛔ KHONG thu lai. Mot artifact thuong nguon dang can lai vang mat.
#:
#: ⭐ Tach rieng khoi `NGUOI_DUNG` du **hanh vi giong het** (ca hai deu khong
#:    thu lai), vi goi day la "loi cua nguoi dung" la noi sai: khach khong lam
#:    gi ca. Do la mot trang thai khong nhat quan cua chinh he thong — vd
#:    COMPOSE chay khi TIMING chua co ket qua.
#:
#: ⚠️ No van duoc dich thanh `LoiNguoiGoi` o bien, vi nen tang **khong co** loai
#:    "trang thai khong nhat quan" va `LoiNguoiGoi` la loai duy nhat cho dung
#:    hanh vi (khong thu lai). Ghi ro o day de mot nguoi doc log khong ket luan
#:    nham rang khach da gui gi do sai.
THIEU_THUONG_NGUON = "thieu_thuong_nguon"
#: Xep lai hang doi sau mot khoang. **Khong phai loi**, khong dot mot lan thu.
BAN = "ban"
#: Da co the goi ra ngoai roi mat ket noi. ⛔ KHONG BAO GIO tu dong thu lai.
MO_HO = "mo_ho"
#: Truot thoang qua. Thu lai la dung.
TAM_THOI = "tam_thoi"

#: Giay cho mac dinh khi may sinh tieng bao ban ma khong noi cho bao lau.
#: ⚠️ So nay CHUA DO. Chon de an toan: du dai de mot lan sinh tieng ngan kip
#: xong, du ngan de khach khong thay lan chay dung hinh. Pha 21 co the do lai.
CHO_KHI_BAN_S = 20


def phan_loai(exc: BaseException) -> str:
    """Mot ngoai le cua Auto Scan -> mot trong bon loai o tren.

    ⚠️ Thu tu quan trong. `MayBan` phai duoc hoi TRUOC cac loai chung hon, va
       `ThieuNguon` truoc `MediaError` (no la lop con). Doi thu tu la lam mot
       nhanh khong bao gio chay toi, va nhanh chet do trong y het mot nhanh dang
       lam viec.
    """
    from .ban_dung import BanDungError
    from .ban_ghi import BanGhiError
    from .dich_thuat import DichError, DichMoHo
    from .giong_noi import GiongError, GiongMoHo, MayBan
    from .giai_doan_media import ThieuNguon
    from .ket_xuat import KetXuatError
    from .nhap_media import MediaError
    from .thoi_gian import ThoiGianError
    from .van_ban import VanBanError

    # ── Ban: hoi TRUOC moi thu, va no khong phai loi ────────────────────────
    if isinstance(exc, MayBan):
        return BAN

    # ── Mo ho: da co the goi ra ngoai. Khong bao gio tu dong thu lai ────────
    if isinstance(exc, (GiongMoHo, DichMoHo)):
        return MO_HO

    # ── Loi cua nguoi dung: dau vao khong hop le, hoac ket qua khong dung
    #    hop dong. Thu lai khong doi duoc gi.
    #
    # ⚠️ `KetXuatError` KE THUA `MediaError` nhung KHONG thuoc nhom nay — mot
    #    lan render hong thuong la truot thoang qua (het cho dia, mot tien
    #    trinh con bi giet), khong phai dau vao sai. Nen phai hoi no truoc.
    if isinstance(exc, KetXuatError):
        return TAM_THOI

    # ── Thieu thuong nguon: hoi TRUOC `MediaError` vi `ThieuNguon` la lop con
    #    cua no, va ca bay lop `Thieu*` deu ke thua `ThieuNguon`.
    if isinstance(exc, ThieuNguon):
        return THIEU_THUONG_NGUON

    # ⛔ QC hong la loi cua KET QUA, khong phai truot thoang qua: chay lai cung
    #    mot ban render cho cung mot phep do. Thu lai ba lan mot phep do tat dinh
    #    la ba lan cho vo ich.
    from .thi_hanh import QcChan
    if isinstance(exc, QcChan):
        return NGUOI_DUNG

    # ⛔ `TinhHaiLan` la mot lech SO SACH, khong phai mot truot thoang qua.
    #
    # 🔴 Neu no roi xuong nhanh mac dinh `TAM_THOI`, nen tang se **THU LAI** —
    #    va thu bi thu lai la mot lan chay ma so tien cua no da duoc phat hien
    #    la sai. Chay lai khong sua duoc mot giai doan vua co don vi viec vua tu
    #    ghi `credit_actual`; no chi lam viec do them mot lan nua.
    #
    # ⭐ `NGUOI_DUNG` o day khong co nghia "khach lam sai" — trong bang nay no
    #    la nhan cua *that bai cuoi cung, dung thu lai*, va do la dieu can noi.
    #    `test_418` vua bat duoc dung cho nay: mot lop ngoai le moi khong duoc
    #    phan loai se im lang thua ke hanh vi nguy hiem nhat trong bang.
    from .features import TinhHaiLan
    if isinstance(exc, TinhHaiLan):
        return NGUOI_DUNG

    if isinstance(exc, (MediaError, BanGhiError, VanBanError, ThoiGianError,
                        BanDungError)):
        return NGUOI_DUNG

    # ── Con lai: truot thoang qua ───────────────────────────────────────────
    if isinstance(exc, (GiongError, DichError)):
        return TAM_THOI
    return TAM_THOI


def dich_sang_loi_nen_tang(exc: BaseException) -> BaseException:
    """Tra ve ngoai le NEN TANG hieu, hoac chinh `exc` neu de nguyen la dung.

    Giu nguyen thong diep goc: no da qua `_t()` va la thu khach doc duoc.
    ⛔ Va giu nguyen **chuoi nguyen nhan** (`from exc`) de nguoi doc log van
       thay loai goc — dich khong duoc lam mat dau vet.
    """
    from platform_core import jobs as jobq
    from platform_core.llm.cong_vlm import AmbiguousProviderError, BanError

    loai = phan_loai(exc)
    if loai in (NGUOI_DUNG, THIEU_THUONG_NGUON):
        moi: BaseException = jobq.LoiNguoiGoi(str(exc))
    elif loai == BAN:
        moi = BanError(str(exc), retry_after_s=CHO_KHI_BAN_S)
    elif loai == MO_HO:
        moi = AmbiguousProviderError(str(exc))
    else:
        return exc
    moi.__cause__ = exc
    return moi
