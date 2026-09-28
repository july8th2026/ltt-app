"""KE CAT cua GIAI DOAN 2 — cat tren MP4 DA XONG, khong cat truoc khi co tieng.

## Vi sao module nay ton tai, va vi sao no khong o `ban_bien_tap.py`

Chu du an chot 25/09 (`docs/superpowers/plans/2026-09-25-asv-hai-giai-doan.md`):

    GIAI DOAN 1  media -> demucs -> ASR -> dich -> TTS -> nan -> tron -> render
                 RA: MP4 tieng Viet khop hinh, TOAN BO do dai goc — KHONG cat gi
    GIAI DOAN 2  hinh anh, THAO TAC TREN MP4 DA XONG: cat canh, logo, phu de...

`ban_bien_tap.py` quyet dinh cat o **pha 12**, truoc khi dich, truoc khi co mot
mau tieng nao. Module nay quyet dinh cat o **sau render**. Hai thu khac nhau ve
ban chat, khong phai hai phien ban cua mot thu:

| | `ban_bien_tap` (GD1 cu) | `ke_cat` (GD2) |
|---|---|---|
| khi nao | truoc dich | sau khi co MP4 |
| "co thoai" doc tu | ban chep loi NGUON | tieng VIET DA SINH (ke hoach thoi gian) |
| cat hinh va tieng | hai buoc, phai anh xa moc | MOT lenh tren MOT tep |
| sai so tich luy | co, va `ban_do_thoi_gian` sinh ra de quan ly no | ⛔ khong the sinh ra |

🔑 **Cai loi thu hai moi la cai lon.** Cau hoi *"doan nay co loi thoai khong"* o
   GD1 chi tra loi duoc bang ban chep loi cua NGUON. Nhung tieng Viet khong nam
   dung cho tieng goc nam: `thoi_gian.lap_ke_hoach` doi moc, `nan_cho_vua` keo
   gian, `nan_thoi_luong.gop_khe` don hai ba cau vao mot khe. ⇒ Mot vung "khong
   co thoai o nguon" hoan toan co the la vung ma ban long tieng dang noi.
   O day ta doc DUNG thu se phat ra: ke hoach thoi gian da chot.

## Luat cat — chu du an chot 25/09, va ca ba dong deu la luat

    CHI cat vung KHONG co loi thoai
         + doan CHAT LUONG KEM (tieu chi "nen cat hay khong")
    🔴 TRAN CUNG: cat di KHONG QUA 5% tong do dai video

⭐ Trần khong phai mot tham so tinh chinh. Tieu chi "chat luong kem" la mot phep
   **phan doan**; mot phep phan doan ⛔ khong co tran thi mot ngay no se cat 40 %
   phim cua khach va ⛔ khong gi ngan lai. Vuot 5 % la **tin hieu rang tieu chi
   sai**, ⛔ khong phai rang tran chat — nen `kiem()` **NEM** chu khong kep.

## ⛔ Va `chon()` khong "im lang cat it di"

Hai ham, hai viec, va ranh gioi giua chung la ca thiet ke:

    chon()   xep uu tien roi nhan cho tOI khi het ngan sach 5 %, va **KHAI RA**
             tung ung vien bi loai kem LY DO (`bo_qua`)
    kiem()   NEM neu mot `KeCat` vuot tran — nen mot ke cat hong ⛔ khong bao gio
             ton tai (khuon `hinh_hoc_dien_nen` + `ban_dung.kiem`, 25/09)

`chon()` goi `kiem()` truoc khi tra ve. Nguoi goi ⛔ khong can nho lam dieu do,
va ⛔ khong the quen.

## 🔑 THU TU UU TIEN khi dung tran: KEM NHAT truoc — va day la ly do

Hai cach cho hai ban ra khac nhau, nen no phai duoc **khai ra** chu ⛔ khong duoc
la he qua tinh co cua thu tu duyet (chu du an chot: *"Quyet, khai ra trong ma,
ghi ly do vao commit"*).

    ✅ KEM NHAT truoc  — 5 % la mot ngan sach KHAN HIEM, nen no phai duoc chi o
                         cho moi giay mua duoc nhieu chat luong nhat
    ⛔ DAI NHAT truoc  — mot doan 60 giay chi hoi kem se an het ngan sach cua ca
                         phim, va nhung doan THAT SU te (3 giay, diem 0,95) o
                         lai nguyen trong ban giao cho khach

⚠️ Pha vo the: **dai hon truoc** (cung diem kem thi bo duoc nhieu hon), roi
   **`bat` som hon** — de hai lan chay cung dau vao cho cung mot ke cat.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from platform_core.i18n import _ as _t

#: Doi khi doi cach dung ke cat. Vao van tay giai doan hinh anh.
PHIEN_BAN_KE_CAT = 1

#: 🔴 TRAN CUNG. Chu du an chot 25/09. ⛔ Khong noi. Vuot tran la tin hieu rang
#:    tieu chi "chat luong kem" sai, ⛔ khong phai rang con so nay chat.
#:
#: ⭐ **CHOT LAI 25/09 toi, sau khi da do va da bao cai gia — chu du an noi "GIU".**
#:
#:    Toi da dat cho chu du an dung con so: tran tinh tren DO DAI, nen ngan sach cat
#:    that la
#:        video 190 s  ->  9,5 giay
#:        video 275 s  -> 13,8 giay
#:        phim 30 phut -> 90  giay
#:    ⇒ No cat thoai mai cac doan chet NGAN, va ⛔ gan nhu khong bao gio bo duoc mot
#:      canh yeu DAI. Tren mot ca that, tieu chi doi cat **50 %** va tran chan con
#:      **4,17 %**, loai 11 doan voi ly do `vuot_tran`.
#:
#: ⇒ Chu du an biet dieu do va chon GIU. Nghia la con so nay la mot **LAN CAN** ("he
#:   khong duoc pha phim khach"), ⛔ KHONG phai mot **ngan sach de bo canh yeu**.
#: ⛔ Nen dung "sua" no khi thay `dung_o_tran: true` xuat hien nhieu — do la no dang
#:   LAM DUNG VIEC. Muon bo canh yeu dai thi do la mot YEU CAU SAN PHAM khac, phai
#:   hoi chu du an, ⛔ khong phai mot con so de noi len cho tien.
TRAN_CAT_TI_LE = 0.05

#: Duoi muc nay coi la khong dang cat: mot khoang vai phan tram giay khong bo
#: duoc canh nao ma lam `concat` them mot doan.
TOI_THIEU_GIAY = 0.20

#: Sai so cho phep khi rap khoang (giay). Cung con so voi `ban_do_thoi_gian`.
KHIT_GIAY = 0.001

# ── Ly do mot ung vien KHONG duoc cat ────────────────────────────────────────
#
# ⭐ Hang so co ten, ⛔ khong chuoi tu do o cho goi: ba noi doc chung (ke cat,
#    bao cao van hanh, phep kiem) va mot chuoi go tay se lech o mot trong ba.
LY_DO_CO_THOAI = "co_thoai"
LY_DO_VUOT_TRAN = "vuot_tran"
LY_DO_QUA_NGAN = "qua_ngan"

LY_DO: tuple[str, ...] = (LY_DO_CO_THOAI, LY_DO_VUOT_TRAN, LY_DO_QUA_NGAN)


class KeCatError(ValueError):
    """Ke cat khong dung luat. Thong bao LA cau tieng Viet cho khach doc."""


@dataclass(frozen=True)
class UngVien:
    """Mot doan tieu chi MUON cat. `diem_kem` cao = te hon.

    ⭐ `diem_kem` la mot **phan doan**, va ten truong noi dung dieu do. Doi ten
       no thanh `do_tin_cay` hay `diem` se lam nguoi doc sau tuong day la mot
       phep DO — roi ho se bo tran di.
    """

    bat: float
    ket: float
    diem_kem: float
    #: Vi sao tieu chi muon cat doan nay. Di thang vao bao cao van hanh.
    ly_do_cat: str = ""

    @property
    def dai(self) -> float:
        return max(0.0, float(self.ket) - float(self.bat))


@dataclass(frozen=True)
class KeCat:
    """Cac khoang se bi CAT khoi MP4 cua GD1, cong phan bi loai kem ly do.

    ⛔ Luu `cat` chu khong `giu`, nguoc voi `BanDoThoiGian`. Hai huong khong
       tuong duong nhau ve muc dich doc: cau hoi cua giai doan nay la *"ta da bo
       gi, va bao nhieu phan tram"* — mot danh sach `giu` tra loi cau do bang mot
       phep tru, va mot phep tru la mot cho de lech.
    """

    cat: tuple[tuple[float, float], ...]
    thoi_luong: float
    #: `({bat, ket, ly_do, diem_kem},...)` — ⛔ KHONG duoc rong khi co ung vien
    #: bi loai. Day la nua "KHAI RA" cua luat tran.
    bo_qua: tuple[dict, ...] = ()

    @property
    def giay_cat(self) -> float:
        return round(sum(k - b for b, k in self.cat), 6)

    @property
    def ti_le_cat(self) -> float:
        if self.thoi_luong <= 0:
            return 0.0
        return self.giay_cat / float(self.thoi_luong)

    @property
    def co_cat(self) -> bool:
        return bool(self.cat)

    @property
    def giu(self) -> tuple[tuple[float, float], ...]:
        """Phan bu cua `cat` tren `[0, thoi_luong]` — dau vao cua ban do.

        ⭐ Tinh o day chu khong bat nguoi goi tu tru: mot phep tru go tay o hai
           cho la hai ket qua se lech, va cai lech do khong nem — no chi lam
           lech mot giay hinh.
        """
        ra: list[tuple[float, float]] = []
        con = 0.0
        for b, k in self.cat:
            if b - con > KHIT_GIAY:
                ra.append((con, b))
            con = max(con, k)
        if float(self.thoi_luong) - con > KHIT_GIAY:
            ra.append((con, float(self.thoi_luong)))
        return tuple(ra)

    def ban_do(self):
        """`BanDoThoiGian` tu ke cat nay — moc GD1 -> moc BAN GIAO.

        🔑 **Day la nguoi dung `ban_do_thoi_gian` con lai, va no la nguoi dung
           DUNG.** O thu tu cu, ban do phai doi moc cua mot ke hoach tieng duoc
           lap TRUOC khi cat — hai artifact, hai truc, sai so tich luy. O day
           ban do doi moc tren MOT tep da xong, va hinh voi tieng di qua **cung
           mot** `concat`. Cai con lai can doi moc la nhung thu **khong duoc dot
           vao diem anh**: tep `.srt` ben canh, va moc QC.
        """
        from .ban_do_thoi_gian import BanDoThoiGian

        return BanDoThoiGian.tu_khoang(self.giu,
                                       thoi_luong_nguon=float(self.thoi_luong))

    def sang_dict(self) -> dict:
        return {
            "phien_ban": PHIEN_BAN_KE_CAT,
            "tran_ti_le": TRAN_CAT_TI_LE,
            "thoi_luong": round(float(self.thoi_luong), 4),
            "cat": [[round(b, 4), round(k, 4)] for b, k in self.cat],
            "giay_cat": self.giay_cat,
            "ti_le_cat": round(self.ti_le_cat, 6),
            "bo_qua": [dict(x) for x in self.bo_qua],
        }

    @classmethod
    def tu_dict(cls, goi: dict) -> "KeCat":
        goi = dict(goi or {})
        return cls(
            tuple((float(b), float(k)) for b, k in (goi.get("cat") or ())),
            float(goi.get("thoi_luong") or 0.0),
            tuple(dict(x) for x in (goi.get("bo_qua") or ())))

    def van_tay(self) -> str:
        import hashlib

        goi = json.dumps(self.sang_dict(), sort_keys=True)
        return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:32]


def co_thoai(thoai, bat: float, ket: float) -> bool:
    """Khoang `[bat, ket)` co chong lan mot khe tieng nao khong.

    `thoai` la cac khe tieng **DA SINH**, tren truc cua MP4 GD1 — xem docstring
    dau tep. ⛔ Khong phai cac khe cua ban chep loi nguon.
    """
    b, k = float(bat), float(ket)
    return any(k > float(tb) + KHIT_GIAY and b < float(tk) - KHIT_GIAY
               for tb, tk in (thoai or ()))


def khe_thoai_tu_ke_hoach(ke_hoach: dict) -> tuple[tuple[float, float], ...]:
    """Ke hoach thoi gian -> cac khe tieng `(bat, ket)` giay tren truc BAN RA.

    ⛔ Bo doan `dai_ms <= 0`: do la doan `lap_ke_hoach` DA bo (vuot tran troi,
       hay ca nhom bi cat). Mot doan khong con tieng ⛔ khong chiem mot khe nao,
       va tinh no la chiem se khoa cung mot vung ma khong gi dang phat o do.
    """
    ra: list[tuple[float, float]] = []
    for d in ((ke_hoach or {}).get("doan") or ()):
        dai = int(d.get("dai_ms") or 0)
        if dai <= 0:
            continue
        bat = int(d.get("dat_tai_ms") or 0) / 1000.0
        ra.append((bat, bat + dai / 1000.0))
    ra.sort()
    return tuple(ra)


def thoai_bi_xoa(thoai, khoang) -> tuple[int, int]:
    """So khe `thoai` bi CUA SO KHACH xoa, so voi `khoang` thuc su duoc giao.

    ⭐ Dung lai `khe_thoai_tu_ke_hoach`/`co_thoai` — day chi la mot phep DEM tren
       CUNG du lieu do da tra ve, ⛔ khong tu dinh nghia mot truc thoi gian moi.
       Goi dung: `thoai` la khe tren truc BAN RA (`khe_thoai_tu_ke_hoach`),
       `khoang` la cac khoang GIU SAU KHI giao voi cua so khach
       (`cat_dau_cuoi.giao`) — CUNG mot truc voi `thoai`, nen phep so ⛔ khong
       can doi moc (E1, 28/09).

    Tra `(so_mat_han, so_mat_mot_phan)`:
      · **mat han**      — khe khong con giay nao trong `khoang`
      · **mat mot phan** — khe con it nhat mot giay, nhung khong con TRON VEN

    ⭐ `chon()` da bao dam moi khe trong `thoai` nam TRON trong `ke.giu` (luat
       cung `co_thoai`, xem docstring dau tep) — nen moi mat mat do day tinh ra
       chi co the do CUA SO KHACH thu hep tiep, ⛔ khong bao gio do chinh sach
       tu dong (`ke_cat.chon`). ⛔ Chi CANH BAO — quyet dinh chan hay khong la
       cua noi goi, ham nay chi DEM.
    """
    mat_han = 0
    mat_mot_phan = 0
    for tb, tk in (thoai or ()):
        tb, tk = float(tb), float(tk)
        dai_goc = tk - tb
        if dai_goc <= 0:
            continue
        con_lai = sum(max(0.0, min(tk, float(k)) - max(tb, float(b)))
                      for b, k in (khoang or ()))
        if con_lai <= KHIT_GIAY:
            mat_han += 1
        elif con_lai < dai_goc - KHIT_GIAY:
            mat_mot_phan += 1
    return mat_han, mat_mot_phan


def kiem(ke: KeCat) -> None:
    """NEM `KeCatError` kem ly do cu the. ⛔ Khong kep, ⛔ khong lam tron.

    🔴 Day la BAT BIEN O BIEN theo dung nghia: `chon()` goi ham nay truoc khi
       tra ve, nen mot `KeCat` vuot tran ⛔ khong bao gio ra khoi module — va
       giai doan hinh anh doc lai tu artifact cung goi no (I8: doc lai thi kiem
       lai). Mot `if ti_le > TRAN` o cho goi thi chi canh giu **mot** cho goi.
    """
    tl = float(ke.thoi_luong)
    if tl <= 0:
        raise KeCatError(_t('Kế cắt không biết thời lượng video.'))
    truoc = 0.0
    for b, k in ke.cat:
        if k - b <= KHIT_GIAY:
            raise KeCatError(_t('Kế cắt có khoảng rỗng hoặc ngược.'))
        if b < truoc - KHIT_GIAY:
            raise KeCatError(_t('Kế cắt có hai khoảng chồng lấn.'))
        if b < -KHIT_GIAY or k > tl + KHIT_GIAY:
            raise KeCatError(_t('Kế cắt vượt ra ngoài thời lượng video.'))
        truoc = k
    if ke.ti_le_cat > TRAN_CAT_TI_LE + 1e-9:
        # ⛔ Cau nay la cau KHACH doc, va no phai noi ca hai con so — mot thong
        #    bao "vuot tran" khong noi vuot bao nhieu thi khong ai sua duoc gi.
        raise KeCatError(_t(
            'Kế cắt bỏ {da:.1f}% video, vượt trần {tran:.0f}%. Tiêu chí cắt '
            'đang chọn quá nhiều — hãy siết tiêu chí, đừng nới trần.'
        ).format(da=ke.ti_le_cat * 100.0, tran=TRAN_CAT_TI_LE * 100.0))


def chon(ung_vien, *, thoai=(), thoi_luong: float,
         tran: float = TRAN_CAT_TI_LE) -> KeCat:
    """Xep uu tien roi nhan ung vien tOI KHI het ngan sach `tran`. KHAI RA phan bo.

    ⭐ Ba cong, theo thu tu, va thu tu do la mot phan cua luat:

        1. `TOI_THIEU_GIAY`   — qua ngan thi khong dang mot cho noi
        2. `co_thoai`         — CHI cat vung khong co loi thoai (luat cung)
        3. ngan sach `tran`   — kem nhat truoc; het ngan sach thi KHAI RA

    ⛔ Cong 2 **loai**, ⛔ khong thu hep ung vien de tranh khe tieng. Thu hep la
       tu bien tap ho khach: mot doan bi cat mot nua khong con la quyet dinh ma
       tieu chi da ra, va ⛔ khong ai o day duoc phep ra quyet dinh do.

    Tra `KeCat` da qua `kiem()`.
    """
    tl = float(thoi_luong)
    if tl <= 0:
        raise KeCatError(_t('Kế cắt không biết thời lượng video.'))

    bo_qua: list[dict] = []
    duoc_xet: list[UngVien] = []
    for uv in (ung_vien or ()):
        if uv.dai < TOI_THIEU_GIAY:
            bo_qua.append(_ghi_bo(uv, LY_DO_QUA_NGAN))
        elif co_thoai(thoai, uv.bat, uv.ket):
            bo_qua.append(_ghi_bo(uv, LY_DO_CO_THOAI))
        else:
            duoc_xet.append(uv)

    # ── Xep uu tien — xem docstring dau tep, muc THU TU UU TIEN ─────────────
    xep = sorted(duoc_xet,
                 key=lambda u: (-float(u.diem_kem), -u.dai, float(u.bat)))

    ngan_sach = tl * float(tran)
    nhan: list[UngVien] = []
    da_nhan: list[tuple[float, float]] = []
    for uv in xep:
        # 🔴 **Ngan sach do bang HOP, ⛔ khong bang TONG (E3, 28/09).** Cong
        #    thang `dai` cua tung ung vien dem MOT vung CHONG NHAU hai lan ⇒
        #    ngan sach dong SOM va `vuot_tran` oan cho mot ung vien von vua.
        #    Kho tham chieu `C:\Cut_only ver2\nerf_engine\stages\select.py` tu
        #    to giac dung bay nay: *"counting overlapping chunks twice, which
        #    makes the selector stop early"*. Hom nay moi canh mot ung vien
        #    (khong chong nhau) nen loi CHUA no, nhung day van la dai luong
        #    DUNG — va no phai la CUNG mot dai luong voi `KeCat.giay_cat` bao
        #    cao sau do (ca hai deu doc tren khoang da qua `_gop`).
        thu = da_nhan + [(float(uv.bat), float(uv.ket))]
        if _do_dai_hop(thu) <= ngan_sach + 1e-9:
            nhan.append(uv)
            da_nhan = thu
        else:
            # 🔴 **KHAI RA, ⛔ khong im lang cat it di.** Mot ban ra it hon cai
            #    tieu chi doi la mot su that van hanh; giau no di la de nguoi doc
            #    bao cao tuong tieu chi chi muon bay nhieu.
            bo_qua.append(_ghi_bo(uv, LY_DO_VUOT_TRAN))

    # ⛔ Tra ve theo thu tu THOI GIAN, khong theo thu tu uu tien: `concat` doc
    #    danh sach nay, va mot danh sach khong theo thu tu thoi gian se dung lai
    #    canh phim — dung dieu `ban_do_thoi_gian` tu choi lam.
    cat = tuple(sorted((float(u.bat), float(u.ket)) for u in nhan))
    ke = KeCat(_gop(cat), tl, tuple(bo_qua))
    kiem(ke)
    return ke


def _ghi_bo(uv: UngVien, ly_do: str) -> dict:
    return {"bat": round(float(uv.bat), 4), "ket": round(float(uv.ket), 4),
            "dai": round(uv.dai, 4), "diem_kem": round(float(uv.diem_kem), 4),
            "ly_do": ly_do, "ly_do_cat": str(uv.ly_do_cat or "")}


def _gop(cat: tuple[tuple[float, float], ...]
         ) -> tuple[tuple[float, float], ...]:
    """Gop cac khoang cat lien nhau. Cung ly do voi `BanDoThoiGian.tu_khoang`:
    hai khoang cat lien nhau de roi nhau tao mot ranh gia trong moi phep tinh
    sau do — va mot cho noi gia la mot cho QC hinh se di hoi VLM vo ich."""
    gop: list[tuple[float, float]] = []
    for b, k in cat:
        if gop and b - gop[-1][1] <= KHIT_GIAY:
            gop[-1] = (gop[-1][0], max(gop[-1][1], k))
        else:
            gop.append((b, k))
    return tuple(gop)


def _do_dai_hop(khoang: list[tuple[float, float]]) -> float:
    """Do dai HOP cac khoang (giay) — merge truoc (`_gop`), cong do dai sau.

    ⭐ Dung lai `_gop` thay vi tu viet mot phep quet rieng: hai dinh nghia
       "cham nhau" o hai noi la hai co hoi de lech. Ham nay la mau so cho CA
       cong ngan sach (`chon`) LAN bao cao (`KeCat.giay_cat` doc tren
       `self.cat` cung da qua `_gop`) — CUNG mot dai luong o CA hai cho, dung
       bay "so dung nhung gan cho sai buoc".
    """
    return sum(k - b for b, k in _gop(tuple(sorted(
        (float(b), float(k)) for b, k in khoang))))


def tom_tat(ke: KeCat) -> dict:
    """Bao cao van hanh cua ke cat. ⭐ NOI CA phan khong cat duoc.

    🔑 `giay_muon_cat` / `ti_le_muon` la hai con so lam cau *"he dung o 5 %"*
       **doc duoc**. Thieu chung thi mot lan chay cat 5 % vi tran va mot lan chay
       cat 5 % vi tieu chi chi muon bay nhieu **trong y het nhau** — va do la
       dung cai bay "hai trang thai gop thanh mot gia tri".
    """
    muon = ke.giay_cat + sum(
        float(x.get("dai") or 0.0) for x in ke.bo_qua
        if x.get("ly_do") == LY_DO_VUOT_TRAN)
    tl = float(ke.thoi_luong) or 1.0
    dem: dict[str, int] = {ly: 0 for ly in LY_DO}
    for x in ke.bo_qua:
        ly = str(x.get("ly_do") or "")
        if ly in dem:
            dem[ly] += 1
    return {
        "phien_ban_ke_cat": PHIEN_BAN_KE_CAT,
        "so_doan_cat": len(ke.cat),
        "giay_cat": ke.giay_cat,
        "ti_le_cat": round(ke.ti_le_cat, 6),
        "tran_ti_le": TRAN_CAT_TI_LE,
        "giay_muon_cat": round(muon, 4),
        "ti_le_muon": round(muon / tl, 6),
        "dung_o_tran": bool(dem[LY_DO_VUOT_TRAN]),
        "so_bo_qua": {ly: dem[ly] for ly in LY_DO},
    }
