"""RANG GIONG — Auto Scan quyet dinh CHON giong nao; LTT Voice so huu giong do.

## Ranh gioi, viet ra de khong ai phai doan

    ASV so huu        chinh sach chon: che do, dac diem mong muon, luc nao chot
    LTT VOICE so huu  chinh giong, quyen so huu, tong hop, GPU, chuan hoa van ban

⇒ Tep nay **khong sinh mot mili-giay tieng nao**. No tra loi dung mot cau hoi:
  *lan chay nay se doc bang giong nao, va can cu vao dau.*

## 🔴 `AUTO_MATCH` khong duoc thoai hoa thanh "giong mac dinh"

`ADR-V4-001` D-V4-04 cam dieu do bang ten, va V2 da mac dung loi ay:
`routes.py:135` khai `giong_id: str = Form("")` roi de trong thi lay mac dinh.
Do la mot thu KHAC han: mot gia tri mac dinh **khong doc gi tu video ca**.

Cho nen o day, `AUTO_MATCH` ma chua co `HoSoNoiDung` thi ket qua la
**`CHUA_RANG`** — mot trang thai hop le, khong phai mot that bai va cung khong
phai mot giong. Tang tren phai hoi lai sau khi pha 11 dung xong ho so.

⛔ Va `ma_giong()` **nem** neu goi tren mot rang buoc chua chot. Mot ham tra ve
   `""` o day se cho ra mot lan tong hop bang giong mac dinh ma khong ai bam
   nut — tuc dung ket qua ma ca thiet ke nay dung de tranh.

## Vi sao "hoan lai" chu khong "chon tam roi sua"

Chon tam mot giong roi doi sau nghe co ve mem hon, nhung no tao ra mot cua so
trong do lan chay **da co mot giong** va bat cu buoc nao chay som deu dung phai
giong tam do. Pha 14 (chuyen loi thoai) phu thuoc vao giong that — no doi do dai
cau theo toc do doc cua giong — nen mot giong tam se sinh ra mot ban chuyen loi
phai lam lai. Mot trang thai "chua co" doc duoc thi chan viec do; mot gia tri
tam thi khong.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from platform_core.i18n import _ as _t

from .hop_dong_v4 import (CHE_DO_GIONG, CHE_DO_GIONG_MAC_DINH,
                          CHE_DO_GIONG_TU_CHON, CHE_DO_GIONG_TU_KHOP)

#: Trang thai cua mot rang buoc giong.
CHUA_RANG = "chua_rang"
DA_RANG = "da_rang"
TRANG_THAI: tuple[str, ...] = (CHUA_RANG, DA_RANG)

#: Nguon cua quyet dinh — de hoa don va man ho tro noi duoc "vi sao giong nay".
NGUON_KHACH_CHON = "khach_chon"
NGUON_TU_KHOP = "tu_khop"


class RangGiongError(ValueError):
    """Yeu cau rang giong khong hop le."""


class ChuaRangError(RangGiongError):
    """Doc giong tu mot rang buoc chua chot.

    ⛔ La mot loi, khong phai mot chuoi rong. Xem docstring dau tep.
    """


@dataclass(frozen=True)
class DacDiemMongMuon:
    """Dac diem nguoi noi ma `AUTO_MATCH` muon khop.

    ⭐ Ba mat nay **khong phai do ASV nghi ra** — chung la dung ba mat ma
       `ltt_voice.giong_mau` da phan loai catalog cua no (`NHAN_GIOI`,
       `NHAN_VUNG`, `NHAN_PHONG_CACH`). Bia them mot mat thu tu se cho ra mot bo
       loc khong bao gio khop.

    ⚠️ Chuoi rong = **khong rang buoc mat do**, khong phai "khong biet". Hai
       nghia do khac nhau, va `co_du_de_khop` phan biet chung.
    """

    gioi: str = ""
    vung: str = ""
    phong_cach: str = ""

    @property
    def co_du_de_khop(self) -> bool:
        """It nhat MOT mat co rang buoc.

        ⛔ Khong mat nao rang buoc thi `loc()` tra ve ca catalog, va "lay cai
           dau tien" cua ca catalog chinh la giong mac dinh doi ten.
        """
        return bool(self.gioi or self.vung or self.phong_cach)


@dataclass(frozen=True)
class YeuCau:
    """Yeu cau rang giong. ASV dung xong pha 09; pha 11 dien not `dac_diem`."""

    che_do: str = CHE_DO_GIONG_MAC_DINH
    #: Chi cho `USER_SELECTED`. Ma giong cua khach hoac ma giong mau.
    giong_id: str = ""
    #: Chi cho `AUTO_MATCH`. Rong o pha 09; pha 11 dien tu `HoSoNoiDung`.
    dac_diem: DacDiemMongMuon = field(default_factory=DacDiemMongMuon)

    def __post_init__(self) -> None:
        if self.che_do not in CHE_DO_GIONG:
            raise RangGiongError(f"che do giong khong biet: {self.che_do!r}")
        if self.che_do == CHE_DO_GIONG_TU_CHON and not self.giong_id:
            raise RangGiongError(
                "USER_SELECTED phai kem ma giong — de trong roi lay mac dinh la "
                "dung loi ma ADR-V4-001 D-V4-04 cam")


@dataclass(frozen=True)
class KetQua:
    """Ket qua rang giong. `trang_thai == CHUA_RANG` la mot ket qua HOP LE."""

    trang_thai: str
    giong_id: str = ""
    nguon: str = ""
    #: Vi sao lai la giong nay — cho man ho tro va cho hoa don.
    can_cu: dict = field(default_factory=dict)

    @property
    def da_chot(self) -> bool:
        return self.trang_thai == DA_RANG

    def ma_giong(self) -> str:
        """⛔ Nem neu chua chot. Xem docstring dau tep."""
        if not self.da_chot:
            raise ChuaRangError(
                _t('Chưa chọn được giọng cho lần chạy này — cần hồ sơ nội dung '
                   'trước khi tự khớp.'))
        return self.giong_id


def tu_thiet_lap(settings: dict) -> YeuCau:
    """Doc yeu cau tu `AsvRun.settings`. Khong cham CSDL."""
    s = dict(settings or {})
    che_do = str(s.get("che_do_giong") or CHE_DO_GIONG_MAC_DINH)
    dd = s.get("dac_diem_giong") or {}
    return YeuCau(
        che_do=che_do,
        giong_id=str(s.get("giong_id") or ""),
        dac_diem=DacDiemMongMuon(
            gioi=str(dd.get("gioi") or ""),
            vung=str(dd.get("vung") or ""),
            phong_cach=str(dd.get("phong_cach") or "")))


def rang(db, *, owner_id: str, yeu_cau: YeuCau) -> KetQua:
    """Chot giong neu chot duoc. Tra `CHUA_RANG` neu con thieu can cu.

    🔑 **Quyen so huu do LTT VOICE kiem, khong phai o day.**
       `features.giai_giong` da loc `owner_id`, da xu ly kho giong dung chung, va
       da bo giong khong con `active`. Viet lai ba phep do o ASV la ba cho de
       lam sai, va cai thu nhat lam sai thi hau qua la mot khach doc video bang
       **giong nhan ban cua nguoi khac**.

    ⛔ Nen o nhanh `USER_SELECTED`, ta goi thang ham cua ho va de no nem.
    """
    if yeu_cau.che_do == CHE_DO_GIONG_TU_CHON:
        return _rang_khach_chon(db, owner_id=owner_id, giong_id=yeu_cau.giong_id)
    return _rang_tu_khop(yeu_cau.dac_diem)


def _rang_khach_chon(db, *, owner_id: str, giong_id: str) -> KetQua:
    from apps.ltt_voice.giong_mau import hop_le as la_giong_mau

    # Giong MAU thi ai cung dung duoc — khong co chu so huu de kiem.
    if la_giong_mau(giong_id):
        return KetQua(DA_RANG, giong_id, NGUON_KHACH_CHON,
                      {"loai": "giong_mau"})

    # Con lai la giong CUA KHACH: de app chu kiem quyen so huu.
    from . import giong_noi

    ref, preset = giong_noi.giai_giong(db, owner_id=owner_id, voice_id=giong_id)
    return KetQua(DA_RANG, giong_id, NGUON_KHACH_CHON,
                  {"loai": "giong_cua_khach", "preset": preset,
                   "co_ref": bool(ref)})


def _rang_tu_khop(dac_diem: DacDiemMongMuon) -> KetQua:
    """`AUTO_MATCH`. Thieu dac diem => CHUA_RANG, khong phai giong mac dinh."""
    if not dac_diem.co_du_de_khop:
        # 🔴 Day la ca diem cua pha nay. Xem docstring dau tep.
        return KetQua(CHUA_RANG, can_cu={"ly_do": "chua co ho so noi dung"})

    from apps.ltt_voice.giong_mau import loc

    ung_vien = loc(gioi=dac_diem.gioi, vung=dac_diem.vung,
                   phong_cach=dac_diem.phong_cach)
    if not ung_vien:
        # ⚠️ Khong ung vien nao thi cung la CHUA_RANG, khong phai "lay dai mot
        #    cai". Noi long dieu kien la viec cua tang tren — no biet mat nao
        #    dang gia nhat, con o day ta khong biet.
        return KetQua(CHUA_RANG, can_cu={
            "ly_do": "khong giong nao khop",
            "dac_diem": {"gioi": dac_diem.gioi, "vung": dac_diem.vung,
                         "phong_cach": dac_diem.phong_cach}})

    # ⭐ On dinh: sap theo ma roi lay cai dau. Hai lan chay cung dac diem phai
    #    ra cung mot giong, neu khong van tay nhay va cache truot vo co.
    chon = sorted(ung_vien, key=lambda g: g.ma)[0]
    return KetQua(DA_RANG, chon.ma, NGUON_TU_KHOP, {
        "loai": "giong_mau",
        "so_ung_vien": len(ung_vien),
        "dac_diem": {"gioi": dac_diem.gioi, "vung": dac_diem.vung,
                     "phong_cach": dac_diem.phong_cach}})


def can_cho_ho_so(yeu_cau: YeuCau) -> bool:
    """Lan chay nay co phai doi `HoSoNoiDung` truoc khi chot giong khong?

    Dung o dieu phoi vien: mot lan chay `AUTO_MATCH` khong duoc di toi buoc
    chuyen loi thoai truoc khi giong da chot, vi do dai cau phu thuoc toc do doc
    cua giong that.
    """
    return (yeu_cau.che_do == CHE_DO_GIONG_TU_KHOP
            and not yeu_cau.dac_diem.co_du_de_khop)
