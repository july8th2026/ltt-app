"""Ban ghi SU DUNG DA GIAO cho mot luot goi nang luc — va cua chan truoc khi tieu.

## Vi sao khong dung thang `credit_actual`

`AsvWorkItem.credit_actual` tra loi "het bao nhieu". No khong tra loi duoc ba cau
hoi ma mot lan doi soat tien can:

    nang luc nao da chay        -> khach hoi "toi tra cho cai gi"
    do bang don vi gi           -> 1.200 token va 12 giay la hai the gioi khac nhau
    lan goi do co CHAC da chay  -> ADR-001 D9: dispatch mo ho khong duoc thu lai mu

⇒ `SuDung` la ban ghi **da giao**, `credit_actual` la mot truong cua no. Tach ra
  vi mot con so khong tu giai thich duoc, va hoa don thi phai.

## 🔑 DA GIAO, khong phai DA YEU CAU

ADR-001 D4: `actual = tong do duoc`, **khong bao gio** tinh lai tu bang gia. Ham
`ghi()` doi `don_vi_da_giao` va tu choi mot ban ghi khong co no.

⛔ Ly do khong phai su nghiem khac ve hinh thuc. `agent/executor.actual_cost`
   tinh tien theo thu **da yeu cau**, va no da gay hai loi tien that trong du an
   nay. Mot ban ghi "da giao" ma so lieu lay tu tham so dau vao thi mang dung cai
   ten no khong xung.

## Ba trang thai dispatch, va vi sao hai trong so do khong duoc thu lai

    DA_GIAO    provider tra ket qua      -> tinh tien, dung lai duoc
    TU_CHOI    provider tu choi ro rang  -> khong tinh tien, thu lai duoc
    MO_HO      mat ket noi SAU khi gui   -> **khong biet** da chay chua

`MO_HO` la trang thai dat nhat: co the provider da chay va da tinh tien ta, co
the chua. Thu lai mu la co the tra tien hai lan cho mot viec; bo qua la co the
mat mot ket qua da tra tien. Nen no **khong tu dong** lam gi ca — no cham mot
dau va de nguoi/ tang tren quyet dinh.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from platform_core.i18n import _ as _t

# ── Trang thai dispatch (ADR-001 D9) ─────────────────────────────────────────
DA_GIAO = "da_giao"
TU_CHOI = "tu_choi"
MO_HO = "mo_ho"
TRANG_THAI = (DA_GIAO, TU_CHOI, MO_HO)

#: Chi trang thai nay moi duoc tinh tien.
TINH_TIEN = frozenset({DA_GIAO})

#: ⛔ Trang thai nay khong duoc tu dong thu lai. Xem docstring dau tep.
KHONG_TU_DONG_THU_LAI = frozenset({MO_HO})

# ── Don vi do ────────────────────────────────────────────────────────────────
#: Don vi phai di KEM so. "1.200" khong noi len dieu gi; "1.200 token" thi co.
TOKEN = "token"
GIAY = "giay"
KY_TU = "ky_tu"
KHUNG_HINH = "khung_hinh"
DON_VI = (TOKEN, GIAY, KY_TU, KHUNG_HINH)


class SuDungError(ValueError):
    """Ban ghi su dung khong hop le. LUON la loi lap trinh, khong phai loi khach."""


@dataclass(frozen=True)
class SuDung:
    """MOT luot goi nang luc, do duoc.

    Bat bien o cap doi tuong: mot ban ghi da giao khong duoc sua sau khi ghi.
    Muon sua nghia la lan goi do khac di, tuc la mot ban ghi KHAC.
    """

    #: Nang luc nao — `text.chat`, `speech.ltt`, `autosubvideo.transcribe`...
    nang_luc: str
    #: Chu so huu nang luc do. Khong phai ten provider ben ngoai: ta khong ban
    #: ten vendor cho khach (`ltt_llm.ALIAS_SANG_ID` giu lop dem do).
    app_chu: str
    trang_thai: str
    don_vi: str = ""
    #: 🔑 So DO DUOC. Rong voi TU_CHOI/MO_HO — va do la mot su that, khong phai
    #:    mot cho trong can dien.
    so_luong: float = 0.0
    #: Credit DO DUOC. Khong bao gio tinh lai tu bang gia (ADR-001 D4).
    credit: int = 0
    #: Danh tinh lan gui, de doi soat khi MO_HO. Rong neu tang duoi khong cap.
    ma_dispatch: str = ""
    ghi_chu: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.trang_thai not in TRANG_THAI:
            raise SuDungError(f"trang thai khong biet: {self.trang_thai!r}")
        if not self.nang_luc or not self.app_chu:
            raise SuDungError("thieu nang_luc hoac app_chu")
        if self.credit < 0 or self.so_luong < 0:
            raise SuDungError("so am")

        if self.trang_thai in TINH_TIEN:
            # ⛔ Mot ban ghi DA GIAO ma khong co don vi do la mot con so khong
            #    kiem duoc. Doi soat sau nay se khong biet no den tu dau.
            if not self.don_vi or self.don_vi not in DON_VI:
                raise SuDungError(
                    f"{self.nang_luc}: da giao thi phai khai don vi do "
                    f"({'/'.join(DON_VI)}), nhan duoc {self.don_vi!r}")
            if self.so_luong <= 0:
                raise SuDungError(f"{self.nang_luc}: da giao ma so luong = 0")
        elif self.credit:
            # 🔴 Cho de sai nhat trong ca tep: mot lan TU_CHOI/MO_HO khong duoc
            #    mang credit. Neu no mang, tong cua lan chay se cong ca nhung
            #    viec **chua chac da chay** — va no cong am tham.
            raise SuDungError(
                f"{self.nang_luc}: trang thai {self.trang_thai} khong duoc mang "
                f"credit (nhan {self.credit})")

    @property
    def duoc_tinh_tien(self) -> bool:
        return self.trang_thai in TINH_TIEN

    @property
    def duoc_tu_dong_thu_lai(self) -> bool:
        return self.trang_thai not in KHONG_TU_DONG_THU_LAI


def tong_credit(cac_su_dung) -> int:
    """Tong credit cua nhung luot **da giao**. Bo qua tu choi/mo ho."""
    return sum(int(s.credit) for s in cac_su_dung if s.duoc_tinh_tien)


def cua_chan_truoc_khi_tieu(db, run, *, uoc_them: int) -> None:
    """⛔ Goi TRUOC moi luot co the ton tien. Nem neu se vuot muc da giu.

    Mong hon `features.kiem_tran_chi` mot lop: no nhan **uoc** cua lan goi sap
    toi, con `kiem_tran_chi` chi biet nhung gi da tieu.

    🔑 Vi sao can mot cua o day thay vi de `quyet_toan` phat hien sau: `quyet_toan`
       chay khi lan chay da ket thuc. Luc do tien da tieu roi, va thu duy nhat
       con lam duoc la bao cho khach mot con so ho khong dong y.

    ⇒ Mot uoc luong te phai thanh mot **that bai chinh sach sach se** truoc khi
      tieu, khong phai mot hoa don bat ngo sau khi tieu.
    """
    from . import features

    features.kiem_tran_chi(db, run, max(0, int(uoc_them)))


def cua_chan_cho_lo(db, run, *, uoc_moi_don_vi: int, so_don_vi: int) -> None:
    """Cua chan cho mot LO — vd sinh tieng 200 doan, doc anh 40 canh.

    ⭐ Kiem CA LO truoc khi chay don vi dau tien, khong phai kiem tung cai mot.

       Kiem tung cai thi lo se chay toi doan thu 137 roi dung — khach da tra cho
       136 doan cua mot san pham **khong dung duoc**, vi mot ban long tieng thieu
       mot phan ba cuoi khong phai mot ban long tieng.

    ⇒ Het ngan sach thi hong TRUOC KHI bat dau, khong phai o giua.
    """
    cua_chan_truoc_khi_tieu(
        db, run, uoc_them=max(0, int(uoc_moi_don_vi)) * max(0, int(so_don_vi)))


def loi_khong_du_ngan_sach() -> str:
    return _t('Chi phí thực tế sẽ vượt mức đã giữ cho phiên chạy này.')
