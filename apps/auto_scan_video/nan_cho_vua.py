"""Nan mot doan loi thoai cho VUA khe thoi gian cua no.

## Bai toan, noi bang mot cau

Cau tieng Viet doc ra dai bao nhieu giay thi **khong biet truoc**. Pha 14 da noi
cho model biet ngan sach, va phan lon cau ra vua — nhung "phan lon" khong phai
"tat ca", va cai khong vua thi phai sua **rieng no**.

## Bac thang bon nac, va thu tu la mot phan cua chinh sach

    1. Doc ra, DO tren tep that                    (khong tin header may sinh tieng)
    2. Ngoai dung sai -> nho model VIET LAI cho vua, doc lai **rieng doan do**
    3. Het so vong -> cho phep CO GIAN nhe trong tran da khai
    4. Van khong duoc -> danh dau CAN SUA, khong giao bua

⛔ Nac 2 chi lam lai **mot doan**. Sinh lai ca kich ban vi mot cau khong vua la
   dieu `V4_RESOURCE_CPU_GPU_POLICY` cam dich danh, va no cung vo ly ve tien:
   mot cau hong lam hong hoa don cua ca tram cau con lai.

⛔ Nac 3 KHONG duoc dat truoc nac 2. Co gian am thanh lam giong meo di; viet lai
   mot cau cho ngan hon thi khong. Uu tien sua **noi dung** truoc khi sua **tin
   hieu** — mot cau khac mot chut van la giong nguoi, mot cau bi ep 1,3 lan thi
   khong.

## Vi sao dung sai KHONG doi xung

    dai hon khe  -> cau tran sang canh sau, hoac de len loi thoai ke tiep
    ngan hon khe -> mot khoang lang, ma `thoi_gian.py` von da biet cach nuot

Hai hau qua khong ngang nhau, nen hai nguong khong ngang nhau. Mot ban long tieng
hoi thua khoang lang van xem duoc; mot ban long tieng noi de len nhau thi khong.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from platform_core.i18n import _ as _t

#: Doi bat cu thu gi o duoi thi tang so nay. Vao van tay cua doan.
PHIEN_BAN_NAN = 1

#: Vuot bao nhieu phan khe thi phai nan. Xem ghi chu dau tep ve tinh khong doi xung.
#:
#: 🔴 **Phai NHO HON `tran_co_gian() - 1`, va do khong phai mot y thich.**
#:
#:    Ban dau con so nay la 0,15 — dung bang tran co gian (1,15). Hau qua: nac 3
#:    cua bac thang **khong bao gio voi toi duoc**. Mot doan hoac nam trong dung
#:    sai (`VUA`), hoac da vuot ca tran co gian (`CAN_SUA`); khong co khoang nao
#:    de "khong vua nhung co gian nhe la du" ton tai. Bac thang bon nac tren
#:    giay chi con ba nac khi chay.
#:
#: ⭐ Va no khong hong ra loi nao: moi doan van co mot trang thai hop le, bao cao
#:    van day du, chi la mot nhanh chinh sach chua bao gio chay. Tim ra khi mot
#:    phep kiem co dung mot doan vao trang thai `CO_GIAN` va khong dat duoc.
#:
#: ⇒ 0,08: duoi 8% thi de yen; 8-15% thi thu viet lai, va neu viet lai khong an
#:   thi co gian van cuu duoc; tren 15% thi viet lai la co hoi that su duy nhat.
#:
#: ⚠️ Ban than con so 0,08 CHUA DO tren du lieu that — chon theo huong an toan.
#:    Pha 21 do lai. Nhung QUAN HE giua no va tran co gian thi da duoc chot.
DUNG_SAI_DAI = 0.08

#: Ngan hon bao nhieu phan khe thi moi dang nan.
#:
#: ⭐ Rong hon gap doi phia kia, co y: `thoi_gian.lap_ke_hoach` da biet cach nuot
#:    khoang lang, nen mot cau ngan la mot van de no giai duoc. Goi model de keo
#:    dai mot cau chi vi no ngan 20% la tra tien cho mot thu khong ai nghe ra.
DUNG_SAI_NGAN = 0.35

#: So lan VIET LAI toi da cho mot doan (khong ke lan doc dau tien).
#:
#: 🔴 Con so nay la mot **tran cung**, khong phai mot goi y. Mot vong lap "sua
#:    cho toi khi vua" tren mot dich vu tra tien la mot hoa don khong co day, va
#:    `V4_RESOURCE_CPU_GPU_POLICY` cam "no infinite loop" bang chu.
#:
#: ⭐ 2 chu khong phai 5: do dai cau ra khong hoi tu — model rut ngan mot cau hai
#:    lan thuong dung o mot do dai no cho la tu nhien, va lan thu ba tra ve gan
#:    y het lan thu hai. Tra tien cho ba lan de doi lay mot ket qua bang lan hai
#:    la lang phi co the doan truoc.
VONG_TOI_DA = 2

#: Tran co gian thoi gian o nac 3. Muon nguyen tu `thoi_gian.TRAN_TANG_TOC` —
#: mot con so, mot cho khai.
def tran_co_gian() -> float:
    from .thoi_gian import TRAN_TANG_TOC

    return float(TRAN_TANG_TOC)


#: Trang thai cua mot doan sau khi nan.
VUA = "vua"                 #: doc ra vua khe (hoac trong dung sai)
CO_GIAN = "co_gian"         #: khong vua nhung co gian nhe la du — nac 3
CAN_SUA = "can_sua"         #: het bac thang ma van khong vua — nac 4
TRANG_THAI = (VUA, CO_GIAN, CAN_SUA)


def _kiem_chinh_sach() -> None:
    """No luc NAP MODULE neu bac thang tu mau thuan.

    ⛔ Dat o cap module, co chu y: mot chinh sach tu mau thuan phai chan viec nap
       app chu khong doi mot phep kiem chay den. Cung khuon voi
       `hop_dong_v4._kiem_tra_hop_dong`.
    """
    if DUNG_SAI_DAI >= tran_co_gian() - 1.0:
        raise AssertionError(
            "DUNG_SAI_DAI (%.3f) >= tran co gian - 1 (%.3f): nac CO_GIAN cua bac "
            "thang khong bao gio voi toi duoc" % (DUNG_SAI_DAI, tran_co_gian() - 1.0))


class NanError(ValueError):
    """Ban nan khong dung hop dong."""


@dataclass(frozen=True)
class KetQuaNan:
    """Ket qua nan MOT doan. `chu` la van ban CUOI CUNG da dung."""

    ma: str
    trang_thai: str
    chu: str
    giay: float
    khe: float
    so_vong: int = 0
    he_so_co_gian: float = 1.0
    ghi_chu: dict = field(default_factory=dict)

    @property
    def dat(self) -> bool:
        return self.trang_thai in (VUA, CO_GIAN)


def khe_cua(m: dict) -> float:
    """Khe thoi gian cua mot doan = do dai cua chinh no trong ban goc.

    ⭐ Khong phai mot ngan sach do pha 16 chia: pha 16 chay SAU va no can biet
       doan nao vua doan nao khong de chia cho khon. Lay khe goc o day giu hai
       pha doc lap — va khe goc cung la thu khan gia thay: cau thoai phai khop
       voi cai mieng dang nhep tren man hinh.
    """
    try:
        return max(0.0, float(m.get("ket") or 0.0) - float(m.get("bat") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def lech(giay: float, khe: float) -> float:
    """Lech tuong doi so voi khe. Duong = dai hon khe."""
    if khe <= 0:
        return 0.0
    return (float(giay) - float(khe)) / float(khe)


def can_nan(giay: float, khe: float) -> bool:
    """Doan nay co ngoai dung sai khong."""
    if khe <= 0:
        return False
    d = lech(giay, khe)
    return d > DUNG_SAI_DAI or d < -DUNG_SAI_NGAN


def co_gian_du_khong(giay: float, khe: float) -> tuple[bool, float]:
    """Nac 3: co gian nhe co keo duoc doan nay ve khe khong, va he so bao nhieu.

    ⛔ Chi tang toc (cau DAI hon khe) moi bi tran chan. Mot cau NGAN hon khe
       khong can co gian gi ca — `thoi_gian.py` chen khoang lang, va do la cach
       dung: keo dai mot cau bang xu ly tin hieu nghe ra ngay, con mot khoang
       lang thi khong ai de y.
    """
    if khe <= 0 or giay <= 0:
        return True, 1.0
    if giay <= khe:
        return True, 1.0
    he_so = float(giay) / float(khe)
    return he_so <= tran_co_gian(), he_so


# ══════════════════════════════════════════════════════════════════════════════
#  Loi nhac viet lai
# ══════════════════════════════════════════════════════════════════════════════

def loi_nhac_nan(m: dict, *, chu_hien_tai: str, giay_do_duoc: float,
                 khe: float) -> list[dict]:
    """Loi nhac cho `ai.RUT_NGAN_CHO_VUA`. MOT doan, khong phai mot lo.

    🔑 Dua vao ca **do dai da DO DUOC**, khong chi khe muc tieu. Do la khac biet
       giua "hay viet ngan hon" va "cau nay doc ra 4,8 giay, khe co 3,2 giay, hay
       viet lai cho khoang 3,0 giay": cai sau cho model mot muc tieu kiem duoc,
       va no la ly do vong thu hai thuong khong can den.
    """
    dai_hon = float(giay_do_duoc) > float(khe)
    viec = "RUT NGAN" if dai_hon else "VIET DAY DAN HON"
    he_thong = (
        "Ban la bien tap vien long tieng tieng Viet. Mot cau da viet **khong vua**"
        " khe thoi gian cua no.\n"
        f"Viec cua ban: {viec} cau do, giu NGUYEN y nghia va thai do.\n"
        "Quy tac:\n"
        "- Khong bo mat thong tin nao trong cau.\n"
        "- Khong them thong tin khong co trong cau.\n"
        "- Van phai la tieng Viet noi tu nhien, khong phai van viet rut gon.\n"
        "- Nham dung `muc_tieu_giay`; khoang 4,5 am tiet moi giay.\n"
        'Tra ve DUY NHAT: {"doan": {"chu": "..."}}')
    nguoi_dung = json.dumps({
        "ma": str(m.get("ma") or ""),
        "goc": str(m.get("goc") or ""),
        "chu_hien_tai": str(chu_hien_tai or ""),
        "doc_ra_het_giay": round(float(giay_do_duoc), 2),
        "khe_giay": round(float(khe), 2),
        # Nham thap hon khe mot chut: vua khit la vua **du** de mot dao dong nho
        # cua may sinh tieng lam no tran ra lai.
        "muc_tieu_giay": round(max(0.3, float(khe) * 0.92), 2),
    }, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": nguoi_dung}]


def doc_nan(goi: dict) -> str:
    """Lay cau da viet lai. Nem neu model khong tra ve gi dung duoc."""
    doan = (goi or {}).get("doan")
    chu = ""
    if isinstance(doan, dict):
        chu = str(doan.get("chu") or "").strip()
    elif isinstance(doan, str):
        chu = doan.strip()
    if not chu:
        raise NanError(_t('Model không trả về câu đã viết lại.'))
    return chu


def ket_luan(ma: str, *, chu: str, giay: float, khe: float,
             so_vong: int) -> KetQuaNan:
    """Xep mot doan vao mot trong ba trang thai, sau khi da het bac thang."""
    if not can_nan(giay, khe):
        return KetQuaNan(ma, VUA, chu, float(giay), float(khe), so_vong)
    duoc, he_so = co_gian_du_khong(giay, khe)
    if duoc:
        return KetQuaNan(ma, CO_GIAN, chu, float(giay), float(khe), so_vong,
                         he_so_co_gian=round(he_so, 4),
                         ghi_chu={"ly_do": "khong vua nhung co gian nhe la du"})
    return KetQuaNan(ma, CAN_SUA, chu, float(giay), float(khe), so_vong,
                     he_so_co_gian=round(he_so, 4),
                     ghi_chu={"ly_do": "vuot ca tran co gian",
                              "tran": tran_co_gian()})


def tom_tat(cac: list[KetQuaNan]) -> dict:
    dem = {t: 0 for t in TRANG_THAI}
    for k in cac:
        dem[k.trang_thai] = dem.get(k.trang_thai, 0) + 1
    return {
        "so_doan": len(cac),
        **{f"so_{t}": dem.get(t, 0) for t in TRANG_THAI},
        "so_vong_tong": sum(k.so_vong for k in cac),
        "lech_lon_nhat": round(max((abs(lech(k.giay, k.khe)) for k in cac),
                                   default=0.0), 4),
    }


_kiem_chinh_sach()
