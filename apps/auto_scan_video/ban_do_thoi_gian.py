"""Ban do thoi gian: doi moc **NGUON** sang moc **BAN RA** sau khi da cat canh.

## Vi sao pha 16 khong the dung lai `thoi_gian.lap_ke_hoach` nhu cu

`thoi_gian.py` lap ke hoach tren truc thoi gian **cua nguon**: doan thu i bat dau
o giay 120 thi no dat quanh giay 120. Dieu do dung cho preset `giu hinh`, noi
luong hinh duoc sao chep nguyen ven.

⛔ Voi `smart_localize` thi khong: canh bi cat **bien mat khoi ban ra**, nen giay
   120 cua nguon co the la giay 74 cua ban ra — hoac khong ton tai. Dat mot doan
   tieng o giay 120 cua ban ra la dat no vao mot cho khac han cho ma no thuoc ve,
   va sai so do **tich luy** theo tung canh bi cat.

⭐ Nen phai co mot **phep doi** truoc khi lap ke hoach, va no la mot ham thuan
   tuy: chi phu thuoc danh sach khoang duoc giu.

## Mot bien thu hai ma phep doi phai tra loi duoc

Khong phai moi moc nguon deu co anh: mot moc nam **trong** canh bi cat thi khong
ton tai o ban ra. `ra()` tra `None` cho truong hop do thay vi ep no ve moc gan
nhat — ep ve la bien mot cau thoai da bi cat thanh mot cau thoai dat sai cho, tuc
doi mot mat mat NHIN THAY duoc thanh mot loi KHO TIM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from platform_core.i18n import _ as _t

#: Doi khi doi cach dung ban do. Vao van tay.
PHIEN_BAN_BAN_DO = 1

#: Sai so cho phep khi rap cac khoang lai (giay). Duoi muc nay coi la lien nhau.
KHIT_GIAY = 0.001


class BanDoError(ValueError):
    """Ban do thoi gian khong dung hop dong."""


@dataclass(frozen=True)
class BanDoThoiGian:
    """Cac khoang NGUON duoc giu, theo thu tu nguon.

    ⛔ Thu tu la thu tu NGUON, luon luon. Sap xep lai la dung lai canh phim, va
       do la mot quyet dinh bien tap khong ai o day duoc phep lam.
    """

    giu: tuple[tuple[float, float], ...]
    thoi_luong_nguon: float

    # ── Dung ────────────────────────────────────────────────────────────────

    @classmethod
    def tu_khoang(cls, khoang, *, thoi_luong_nguon: float) -> "BanDoThoiGian":
        """Dung tu cac khoang duoc giu. Gop cac khoang lien nhau, bo khoang rong.

        ⭐ Gop la can thiet chu khong phai lam dep: hai canh lien nhau cung duoc
           giu thi giua chung **khong co cho cat nao**, va de chung tach roi se
           tao ra mot ranh gia trong moi phep tinh sau do.
        """
        sach = []
        for b, k in khoang:
            b, k = float(b), float(k)
            if k - b > KHIT_GIAY:
                sach.append((b, k))
        sach.sort()

        gop: list[tuple[float, float]] = []
        for b, k in sach:
            if gop and b - gop[-1][1] <= KHIT_GIAY:
                gop[-1] = (gop[-1][0], max(gop[-1][1], k))
            else:
                gop.append((b, k))
        return cls(tuple(gop), float(thoi_luong_nguon))

    @classmethod
    def giu_nguyen(cls, thoi_luong_nguon: float) -> "BanDoThoiGian":
        """Ban do cua preset GIU HINH: mot khoang, khong cat gi.

        ⭐ Co ham rieng thay vi de nguoi goi tu dung `[(0, T)]`: preset giu hinh
           la mot **truong hop dac biet co ten**, va goi ten no o day lam moi cho
           dung no doc duoc ma khong phai suy.
        """
        return cls(((0.0, float(thoi_luong_nguon)),), float(thoi_luong_nguon))

    # ── Doi ────────────────────────────────────────────────────────────────

    def ra(self, t_nguon: float) -> float | None:
        """Moc nguon -> moc ban ra. `None` neu moc do nam trong phan da cat.

        ⛔ KHONG ep ve moc gan nhat khi roi vao phan bi cat. Ep ve la bien mot
           cau thoai **da bi cat** thanh mot cau thoai **dat sai cho** — tuc doi
           mot mat mat nhin thay duoc thanh mot loi kho tim.
        """
        t = float(t_nguon)
        truoc = 0.0
        for b, k in self.giu:
            if t < b - KHIT_GIAY:
                return None
            if t <= k + KHIT_GIAY:
                return truoc + (t - b)
            truoc += k - b
        return None

    def ra_gan_nhat(self, t_nguon: float) -> float:
        """Nhu `ra`, nhung moc trong phan bi cat ve **dau khoang giu ke tiep**.

        🔑 Ton tai cho mot viec DUY NHAT: dat nen nhac. Nen la mot dong lien tuc
           — cat mot doan giua roi noi lai thi cho noi phai la mot moc co that,
           khong duoc la `None`. Loi thoai thi **khong dung ham nay**: mot cau
           thoai thuoc canh da cat phai bien mat, khong duoc troi sang canh khac.
        """
        t = float(t_nguon)
        truoc = 0.0
        for b, k in self.giu:
            if t < b:
                return truoc
            if t <= k:
                return truoc + (t - b)
            truoc += k - b
        return truoc

    def trong_phan_giu(self, bat: float, ket: float) -> bool:
        """Khoang `[bat, ket)` co chong lan bat cu phan duoc giu nao khong."""
        return any(float(ket) > b and float(bat) < k for b, k in self.giu)

    def ra_khoang(self, bat: float, ket: float) -> list[tuple[float, float]]:
        """Mot KHOANG nguon -> cac khoang tuong ung tren ban ra.

        `ra()` doi mot MOC. Vung che doi mot KHOANG, va hai thu do khong quy ve
        nhau duoc: goi `ra()` hai lan cho hai dau roi noi lai la SAI ngay khi
        khoang do bat qua mot cho cat — dau cat co the tra `None`, va mot cap
        `(None, x)` khong con noi gi.

        ⛔ Tra DANH SACH chu khong mot cap. Mot khoang nguon bat qua **hai** vung
           duoc giu khong lien nhau se cho hai khoang ra; ep chung thanh mot cap
           `(min, max)` la che ca doan o giua — doan ma khach **khong** chon.

        ⭐ Nhung hai khoang ra LIEN NHAU thi gop lai la dung, khong phai lam dep:
           `concat` noi khong ke ho, nen hai manh nguon nam hai ben mot cho cat
           tro thanh lien tuc tren ban ra. Gop chung bot mot bo loc ma khong doi
           mot khung hinh nao.

        Rong = ca khoang nay da bi cat het. Nguoi goi phai xu ly, dung bo qua:
        mot vung che khong con cho de ap la mot vung khach ve ma khong bao gio
        xay ra.
        """
        bat, ket = float(bat), float(ket)
        tho: list[tuple[float, float]] = []
        truoc = 0.0
        for b, k in self.giu:
            lo, hi = max(bat, b), min(ket, k)
            if hi - lo > KHIT_GIAY:
                tho.append((truoc + (lo - b), truoc + (hi - b)))
            truoc += k - b

        gop: list[tuple[float, float]] = []
        for b, k in tho:
            if gop and b - gop[-1][1] <= KHIT_GIAY:
                gop[-1] = (gop[-1][0], max(gop[-1][1], k))
            else:
                gop.append((b, k))
        return gop

    # ── Do ─────────────────────────────────────────────────────────────────

    @property
    def thoi_luong_ra(self) -> float:
        return round(sum(k - b for b, k in self.giu), 6)

    @property
    def so_cho_noi(self) -> int:
        """So cho hai canh khong lien nhau bi noi lai — moi cho la mot chuyen canh."""
        return max(0, len(self.giu) - 1)

    def van_tay(self) -> str:
        import hashlib

        goi = json.dumps({
            "giu": [[round(b, 4), round(k, 4)] for b, k in self.giu],
            "nguon": round(self.thoi_luong_nguon, 4),
            "phien_ban": PHIEN_BAN_BAN_DO,
        }, sort_keys=True)
        return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:32]

    def sang_dict(self) -> dict:
        return {
            "phien_ban": PHIEN_BAN_BAN_DO,
            "giu": [[round(b, 4), round(k, 4)] for b, k in self.giu],
            "thoi_luong_nguon": round(self.thoi_luong_nguon, 4),
            "thoi_luong_ra": self.thoi_luong_ra,
        }

    @classmethod
    def tu_dict(cls, goi: dict) -> "BanDoThoiGian":
        """Nua con lai cua `sang_dict` — xem bai hoc o pha 14."""
        goi = dict(goi or {})
        return cls(tuple((float(b), float(k)) for b, k in (goi.get("giu") or ())),
                   float(goi.get("thoi_luong_nguon") or 0.0))


def kiem(bd: BanDoThoiGian) -> None:
    """Nem `BanDoError` kem ly do cu the."""
    if not bd.giu:
        raise BanDoError(_t('Bản đồ thời gian không giữ lại khoảng nào.'))
    truoc = None
    for b, k in bd.giu:
        if k <= b:
            raise BanDoError(_t('Bản đồ thời gian có khoảng rỗng hoặc ngược.'))
        if truoc is not None and b < truoc - KHIT_GIAY:
            raise BanDoError(_t('Bản đồ thời gian có hai khoảng chồng lấn.'))
        truoc = k
    if bd.thoi_luong_nguon > 0 and bd.giu[-1][1] > bd.thoi_luong_nguon + 0.05:
        raise BanDoError(_t('Bản đồ thời gian vượt quá thời lượng nguồn.'))

    # 🔴 **O day tung co mot chot thu ba, va no KHONG BAO GIO no duoc.**
    #
    #    Chot do la: "ban ra khong duoc dai hon nguon". Nghe nhu mot phep bao ve
    #    can thiet — do la loi hua cua hop dong V4. Nhung hai chot O TREN da
    #    chung minh no roi: cac khoang khong chong lan (chot 2) va deu ket thuc
    #    trong `[0, T]` (chot 3), nen **tong cua chung luon <= T**. Khong co dau
    #    vao nao lam chot thu ba no.
    #
    # ⭐ Mot chot khong bao gio no con te hon khong co chot: no trong nhu mot lop
    #    bao ve, no khong bao ve gi, va no noi doi voi nguoi doc ve nhung gi that
    #    su dang duoc canh giu. Day la lan thu BA trong pha 12-16 gap dung mot
    #    hinh dang do (chot "khong bao gio cat sach" o pha 12, nac `CO_GIAN`
    #    khong voi toi duoc o pha 15).
    #
    # ⇒ Menh de van duoc chot — nhung o TEST, nhu mot **he qua** do qua duong
    #   dung that (`tu_khoang`), chu khong gia vo la mot nhanh ma.


# 🔴 **`tu_ban_bien_tap` DA BI XOA o b4 hai giai doan (25/09).**
#
#    No doi `BanBienTap` + `ChiMucCanh` thanh mot ban do, va no la MAT XICH lam
#    phep cat chay TRUOC khi co tieng: `giai_doan_thoi_gian._ban_do` goi no, roi
#    `lap_ke_hoach` phai doi moi moc cua ke hoach tieng theo ban do do. Chinh
#    docstring dau tep nay ghi cai gia: *"sai so tich luy theo tung canh bi cat"*.
#
# ⭐ Chu du an chot doi THU TU: cat canh nam SAU render (`ke_cat.py`). Ban do van
#    can — nhung nguoi dung cua no da doi. Nay ⛔ khong ai dung mot ban do suy tu
#    ban bien tap nua; `ke_cat.KeCat.ban_do()` suy no tu ke cat, tren truc cua
#    MOT tep da xong.
#
# ⛔ Ghi lai o day chu khong xoa lang le: mot ham bien mat khong loi giai thich
#    se duoc mot pha sau "viet lai" khi ho gap dung bai toan ma no giai — va lan
#    do ho se cam no lai vao dung cho da duoc go ra.
