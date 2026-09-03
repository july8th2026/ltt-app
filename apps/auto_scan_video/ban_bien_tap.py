"""BAN BIEN TAP (EditPlan) — quyet dinh hinh anh, chot TRUOC khi tieu tien tieng.

## Vi sao no phai dung TRUOC long tieng

`V4-R07` (P0) ghi lai mot su dao nguoc trong chuoi cua V2: `content_process`
(dich ca ban chep loi bang model tra tien) chay o vi tri thu **4**, khi chua co
ban bien tap nao. Tuc ta dich — va tra tien cho — nhung cau thoai thuoc nhung
canh se bi **cat bo**.

⇒ Ban bien tap la **quyet dinh hinh anh co tham quyen**. Moi thu tra tien phia
  sau (dich, sinh tieng, canh thoi gian, ket xuat) chi duoc chay tren phan da
  duoc GIU.

## 🔑 Tat dinh: cung bang chung => cung ban

Khong ngau nhien, khong thoi gian thuc. Mot ban bien tap doi giua hai lan chay
tren cung du lieu la mot san pham khach khong the giai thich duoc — va la mot
cache khong bao gio dung duoc.

## ⛔ `localize_preserve_picture` KHONG BAO GIO cat

`hop_dong_v4.THAO_TAC_CHO_PHEP[PRESET_GIU_HINH]` la mot tuple **rong**: preset
nay khong duoc phep co thao tac bien tap nao. Day khong phai mot mac dinh mem —
no la loi hua san pham "long tieng, giu nguyen hinh", va mot khung hinh bi cat
trong che do do la mot loi hua bi pha.

## Vi sao canh CO LOI THOAI kho bi cat hon

Yeu cau 4. Mot canh khong loi thoai bi cat nham thi khan gia mat mot canh; mot
canh **co loi thoai** bi cat nham thi mach truyen dut — nguoi xem nghe mot cau
tra loi cho mot cau hoi khong con. Hai thiet hai khong ngang nhau, nen hai
nguong khong duoc ngang nhau.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field

from .hop_dong_v4 import (PRESET, PRESET_CAT_THONG_MINH, PRESET_GIU_HINH,
                          THAO_TAC_CAT, THAO_TAC_CHO_PHEP, THAO_TAC_GIU)

log = logging.getLogger(__name__)

#: 🔑 Phien ban CHINH SACH, di vao van tay. Doi luat cat = doi san pham.
PHIEN_BAN_BAN = 1

#: Nguong bo mot canh KHONG co loi thoai.
NGUONG_BO = 0.65

#: Nguong bo mot canh CO loi thoai. Xem docstring dau tep.
#:
#: ⚠️ Cao hon co y, khong phai "de cho chac". Hai thiet hai khong ngang nhau.
NGUONG_BO_CO_THOAI = 0.85

#: San: phai giu it nhat ngan nay ti le thoi luong nguon.
#:
#: 🔴 Khong co san thi mot lan VLM "khong chac" tren moi canh co the cat sach ca
#:    video, va khach nhan mot tep 3 giay. Mot san la thu bien mot ket qua vo ly
#:    thanh mot that bai chinh sach doc duoc.
SAN_GIU_LAI = 0.5

#: Tran: cat qua nhieu cung dang ngo nhu cat qua it.
TRAN_CAT = 0.5


class BanBienTapError(ValueError):
    """Khong lap duoc ban, hoac ban khong dat chinh sach an toan."""


@dataclass(frozen=True)
class QuyetDinh:
    """MOT canh: giu hay cat, vi sao, va tin den dau."""

    ma_canh: str
    thao_tac: str = THAO_TAC_GIU
    ly_do: str = ""
    do_tin: float = 0.0
    #: Tro toi bang chung da dung — `HieuCanh.ma_canh`, tin hieu tat dinh.
    bang_chung: tuple[str, ...] = ()

    @property
    def giu(self) -> bool:
        return self.thao_tac == THAO_TAC_GIU


@dataclass(frozen=True)
class BanBienTap:
    """EditPlan. Thu tu la thu tu NGUON, luon luon."""

    preset: str
    quyet_dinh: tuple[QuyetDinh, ...]
    thoi_luong_nguon: float
    phien_ban: int = PHIEN_BAN_BAN
    ghi_chu: dict = field(default_factory=dict)

    @property
    def cac_ma_giu(self) -> tuple[str, ...]:
        return tuple(q.ma_canh for q in self.quyet_dinh if q.giu)

    @property
    def cac_ma_cat(self) -> tuple[str, ...]:
        return tuple(q.ma_canh for q in self.quyet_dinh if not q.giu)

    def sang_dict(self) -> dict:
        return {
            "phien_ban": self.phien_ban, "preset": self.preset,
            "thoi_luong_nguon": round(self.thoi_luong_nguon, 3),
            "quyet_dinh": [
                {"ma_canh": q.ma_canh, "thao_tac": q.thao_tac,
                 "ly_do": q.ly_do, "do_tin": round(q.do_tin, 3),
                 "bang_chung": list(q.bang_chung)} for q in self.quyet_dinh],
            "ghi_chu": dict(self.ghi_chu),
        }

    @classmethod
    def tu_dict(cls, goi: dict) -> "BanBienTap":
        """Doc lai tu dang da luu. Nua con lai cua `sang_dict`.

        🔴 Pha 12 ghi artifact nay ra ma **khong co duong doc lai**, va khong ai
           thay vi pha 12 khong tu doc lai bao gio. Pha 14 la nguoi doc dau tien.

        ⭐ Mot cap `sang_dict` khong co `tu_dict` la mot dinh dang luu tru chua ai
           thu doc — tuc mot dinh dang chua ai kiem chung. Va no chi lo ra o pha
           SAU, khi artifact da nam trong kho cua khach.

        ⛔ `van_tay()` bam tren `sang_dict()`, nen `tu_dict(sang_dict(x))` phai
           cho lai **dung van tay cu**; neu khong thi mot lan doc-ghi vong quanh
           se lam vo hieu ca ha nguon ma khong co gi thay doi that.
        """
        goi = dict(goi or {})
        return cls(
            preset=str(goi.get("preset") or ""),
            quyet_dinh=tuple(
                QuyetDinh(ma_canh=str(q.get("ma_canh") or ""),
                          thao_tac=str(q.get("thao_tac") or THAO_TAC_GIU),
                          ly_do=str(q.get("ly_do") or ""),
                          do_tin=float(q.get("do_tin") or 0.0),
                          bang_chung=tuple(q.get("bang_chung") or ()))
                for q in (goi.get("quyet_dinh") or [])),
            thoi_luong_nguon=float(goi.get("thoi_luong_nguon") or 0.0),
            phien_ban=int(goi.get("phien_ban") or PHIEN_BAN_BAN),
            ghi_chu=dict(goi.get("ghi_chu") or {}))

    def van_tay(self) -> str:
        """⛔ Doi ban = doi van tay = ha nguon phai chay lai. Xem yeu cau 7."""
        return hashlib.sha256(
            json.dumps(self.sang_dict(), ensure_ascii=False, sort_keys=True)
            .encode("utf-8")).hexdigest()[:32]


# ══════════════════════════════════════════════════════════════════════════════
#  Lap ban
# ══════════════════════════════════════════════════════════════════════════════

def _co_thoai(ban_ghi: dict, bat: float, ket: float) -> bool:
    for d in (ban_ghi or {}).get("doan") or []:
        try:
            b, k = float(d.get("bat", 0)), float(d.get("ket", 0))
        except (TypeError, ValueError):
            continue
        if k > bat and b < ket and str(d.get("chu") or "").strip():
            return True
    return False


def lap_ban(*, preset: str, chi_muc, hieu_canh=None, ban_ghi=None) -> BanBienTap:
    """Lap ban bien tap. TAT DINH: cung dau vao => cung ban.

    ⛔ `PRESET_GIU_HINH` khong bao gio doc `hieu_canh` — no khong duoc phep cat,
       nen mot y kien ve viec nen cat gi la mot y kien khong duoc dung toi. Doc
       no o day se tao ra mot duong ma mot ban sua sau co the vo tinh mo ra.
    """
    if preset not in PRESET:
        raise BanBienTapError(f"preset khong biet: {preset!r}")
    canh = list(getattr(chi_muc, "canh", ()) or ())
    if not canh:
        raise BanBienTapError("chi muc canh rong — khong co gi de bien tap")

    thoi_luong = float(getattr(chi_muc, "thoi_luong", 0.0) or 0.0)

    if preset == PRESET_GIU_HINH:
        qd = tuple(QuyetDinh(c.ma, THAO_TAC_GIU,
                             "preset giu nguyen hinh — khong cat bat cu gi",
                             1.0, ()) for c in canh)
        ban = BanBienTap(preset, qd, thoi_luong,
                         ghi_chu={"bat_bien_giu_hinh": True})
        kiem_ban(ban)
        return ban

    theo_ma = {getattr(h, "ma_canh", ""): h for h in (hieu_canh or ())}
    qd = []
    for c in canh:
        h = theo_ma.get(c.ma)
        co_thoai = _co_thoai(ban_ghi or {}, c.bat, c.ket)
        qd.append(_quyet_dinh_mot_canh(c, h, co_thoai=co_thoai))

    ban = BanBienTap(preset, tuple(qd), thoi_luong, ghi_chu={
        "so_canh": len(canh),
        "so_co_bang_chung": sum(1 for c in canh if c.ma in theo_ma),
    })
    ban = _ap_chinh_sach_an_toan(ban, canh)
    kiem_ban(ban)
    return ban


def _quyet_dinh_mot_canh(c, h, *, co_thoai: bool) -> QuyetDinh:
    """Mot canh. **Mac dinh la GIU** — bo la hanh dong phai co can cu.

    ⚠️ Khong co `HieuCanh` (VLM chua doc, hoac doc hong) thi GIU. Cat mot canh
       ma ta khong co bang chung gi ve no la cat mu.
    """
    if h is None:
        return QuyetDinh(c.ma, THAO_TAC_GIU, "khong co bang chung — giu", 0.0, ())

    nguong = NGUONG_BO_CO_THOAI if co_thoai else NGUONG_BO
    de_xuat = str(getattr(h, "de_xuat", "") or "")
    do_tin = float(getattr(h, "do_tin", 0.0) or 0.0)

    if de_xuat == "bo" and do_tin >= nguong:
        return QuyetDinh(
            c.ma, THAO_TAC_CAT,
            f"VLM de xuat bo (tin {do_tin:.2f} >= nguong {nguong:.2f}"
            f"{', canh co loi thoai' if co_thoai else ''})",
            do_tin, (c.ma,))

    # ⭐ Ly do phai noi CA nguong LAN vi sao nguong lai la so do. Mot dong log
    #    ghi "duoi nguong 0.85" khong cho biet vi sao canh nay kho cat hon canh
    #    ben canh — va do dung la cau hoi nguoi doc log dang co.
    vi_sao_nguong = " (canh co loi thoai nen nguong cao hon)" if co_thoai else ""
    ly_do = "VLM de xuat giu" if de_xuat == "giu" else (
        f"de xuat bo nhung do tin {do_tin:.2f} duoi nguong "
        f"{nguong:.2f}{vi_sao_nguong}"
        if de_xuat == "bo" else "VLM khong chac — giu")
    return QuyetDinh(c.ma, THAO_TAC_GIU, ly_do, do_tin, (c.ma,))


def _ap_chinh_sach_an_toan(ban: BanBienTap, canh) -> BanBienTap:
    """San/tran thoi luong. Vuot thi **hoan cat** theo do tin THAP nhat truoc.

    🔑 Hoan theo do tin thap nhat truoc, khong theo thu tu: neu buoc phai giu
       lai mot so canh da bi de nghi cat, ta giu lai nhung canh ma bang chung
       YEU nhat. Giu theo thu tu se giu dau video va cat sach doan cuoi.
    """
    dai = {c.ma: max(0.0, float(c.ket) - float(c.bat)) for c in canh}
    tong = sum(dai.values()) or 1.0

    def _giu_duoc(qds) -> float:
        return sum(dai.get(q.ma_canh, 0.0) for q in qds if q.giu) / tong

    qd = list(ban.quyet_dinh)
    da_hoan = 0
    while _giu_duoc(qd) < SAN_GIU_LAI:
        ung_vien = [i for i, q in enumerate(qd) if not q.giu]
        if not ung_vien:
            break
        i = min(ung_vien, key=lambda j: qd[j].do_tin)
        q = qd[i]
        qd[i] = QuyetDinh(q.ma_canh, THAO_TAC_GIU,
                          f"hoan cat de dat san giu lai {SAN_GIU_LAI:.0%} "
                          f"(ly do cu: {q.ly_do})", q.do_tin, q.bang_chung)
        da_hoan += 1

    ghi = dict(ban.ghi_chu)
    if da_hoan:
        ghi["da_hoan_cat"] = da_hoan
    ghi["ti_le_giu"] = round(_giu_duoc(qd), 4)
    return BanBienTap(ban.preset, tuple(qd), ban.thoi_luong_nguon,
                      ban.phien_ban, ghi)


def kiem_ban(ban: BanBienTap) -> None:
    """Chot chinh sach. Nem `BanBienTapError` neu ban khong hop le."""
    if ban.preset not in PRESET:
        raise BanBienTapError(f"preset khong biet: {ban.preset!r}")
    if not ban.quyet_dinh:
        raise BanBienTapError("ban khong co quyet dinh nao")

    cho_phep = set(THAO_TAC_CHO_PHEP[ban.preset])
    for q in ban.quyet_dinh:
        if q.thao_tac == THAO_TAC_GIU:
            continue
        if q.thao_tac not in cho_phep:
            # ⛔ Day la cho `PRESET_GIU_HINH` duoc cuong che: tuple rong nghia la
            #    KHONG thao tac nao ngoai giu duoc phep.
            raise BanBienTapError(
                f"preset {ban.preset!r} khong cho phep thao tac "
                f"{q.thao_tac!r} (canh {q.ma_canh})")

    if not ban.cac_ma_giu:
        # 🔴 Video rong. Khach tra tien cho mot tep khong co gi.
        raise BanBienTapError("ban cat sach moi canh — khong con video nao")

    if ban.preset == PRESET_GIU_HINH and ban.cac_ma_cat:
        raise BanBienTapError(
            "che do giu nguyen hinh ma van co canh bi cat — loi hua san pham bi pha")

    ti_le = float(ban.ghi_chu.get("ti_le_giu") or 1.0)
    if ti_le < SAN_GIU_LAI - 1e-9:
        raise BanBienTapError(
            f"chi giu lai {ti_le:.1%} thoi luong, duoi san {SAN_GIU_LAI:.0%}")


# ══════════════════════════════════════════════════════════════════════════════
#  Ban chep loi -> phan DUOC GIU
# ══════════════════════════════════════════════════════════════════════════════

def doan_giu_lai(ban_ghi: dict, ban: BanBienTap, chi_muc) -> dict:
    """Ban chep loi rut gon ve **chi nhung doan nam trong canh duoc giu**.

    ⛔ Day la thu chan tien chay ra ngoai: ha nguon (dich, sinh tieng) chi thay
       nhung doan o day. Mot doan thuoc canh da cat ma van lot xuong la mot cau
       duoc dich va doc thanh tieng cho mot doan hinh khong con ton tai.

    ⚠️ Giu NGUYEN thu tu va NGUYEN moc thoi gian goc. Canh thoi gian la viec cua
       pha 16; o day ta chi loc.
    """
    giu = set(ban.cac_ma_giu)
    khoang = [(float(c.bat), float(c.ket))
              for c in getattr(chi_muc, "canh", ()) if c.ma in giu]

    ra = []
    for d in (ban_ghi or {}).get("doan") or []:
        try:
            b, k = float(d.get("bat", 0)), float(d.get("ket", 0))
        except (TypeError, ValueError):
            continue
        # Mot doan thuoc phan duoc giu neu no CHONG LAN voi mot canh duoc giu.
        if any(k > kb and b < kk for kb, kk in khoang):
            ra.append(dict(d))

    moi = dict(ban_ghi or {})
    moi["doan"] = ra
    moi["da_loc_theo_ban"] = ban.van_tay()
    return moi
