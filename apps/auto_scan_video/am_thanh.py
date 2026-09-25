"""Ho so AM THANH cua mot lan chay — V6 pha 23 (Audio Studio).

Ban phoi (`am_master`) da co tu V4: nen (demucs da bo loi goc) + cac doan tieng
long + `loudnorm` hai luot ve -14 LUFS. Truoc pha nay moi con so trong do la
hang so: nen luon ha **-6 dB**, tren **ca bai**, ke ca giua hai cau khong ai noi.

## 🔴 Vi sao KHONG co thanh "muc giong" canh thanh "muc nen"

De bai goi ten ba muc (goc/nen/giong). Do truoc khi dung (`PHA23_AUDIO_STUDIO.md`
§1): ban phoi ket thuc bang `loudnorm`, va `loudnorm` dua CA ban ve -14 LUFS. Nen
"giong +3, nen -3" va "giong 0, nen -6" ra **cung mot tep** (SNR 69,7 dB giua
hai ban — tuc trung nhau toi sai so lam tron), con doi TI LE thi khac han (9,4 dB).

⇒ Giong va nen **khong** phai hai bac tu do, chi TI LE giua chung la mot. Hai
  thanh keo o do la mot thanh that va mot thanh gia: khach keo "giong" len, ban
  ra khong to hon, va khong gi bao cho ho biet vi sao. Nen o day chi co MOT so:
  `nen_db` — muc nen **so voi loi thoai**.

## Ba dieu khien, va dieu KHONG phai dieu khien

| truong | nghia | mac dinh |
|---|---|---|
| `nen_db` | muc nen so voi loi; `None` = tat nen (chi con loi) | -6 (dung hang so V4) |
| `giam_theo_loi` | ha nen THEM ~7 dB **chi luc co loi**, tra lai giua hai cau | tat |
| `fade_vao` / `fade_ra` | lam to dan / nho dan o dau / cuoi, giay | 0 |
| `nhac_nen` | nhac KHACH TAI LEN — xem khoi rieng duoi day | vang mat |

⛔ **Muc tieu am luong (-14 LUFS, -1,5 dBTP) KHONG phai lua chon cua khach.** No la
   tran QC T4/T5 (`qc.py`): mo no ra thi hoac QC doc theo tung lan chay — mot
   cong khach tu noi long duoc — hoac QC chan chinh ban khach vua chon.

⚠️ Mac dinh ra **dung tung byte** ban phoi truoc pha 23 (`test_479` chot chuoi loc),
   nen ho so mac dinh khong duoc ghi (`cai_dat.KHOA_THUA`) va bao cao nghiem thu
   hien hanh van hieu luc.

## 🔴 V3 (25/09) — `nhac_nen`: MOT nguon KHAC voi lop "nhac" cua `tach_tieng`

`tach_tieng.LOP_STEM["nhac"]` (drums+bass) la nhac **tach ra tu chinh video
goc** boi demucs — no la mot PHAN CUA `nen` (dau vao 0 cua `tron_cuoi`), da
tron xong TRUOC KHI toi module nay. `nhac_nen` o day la MOT TEP KHACH TU TAI
LEN (`asv-nhac`, V3) — mot nguon am thanh THU HAI, hoan toan doc lap, chi gap
`nen` ngay tai `bieu_thuc_tron` (xem `am_master.py`). Lam mot API doc chung
mot cai ten "nhac" cho ca hai la troi hai khai niem lam mot — xem canh bao
`CLAUDE.md` luat 8 cua V3.

Loi giai da co o `D:/Viral/resources/app-src/xu_ly_video.py` (mac dinh
`bg_volume = 0.25`, `-stream_loop -1` dat TRUOC `-i` de LAP khi nhac ngan hon
video, `apad` BAT BUOC de khong mat duoi khi nhac ngan hon video ma khach tat
lap) — mang sang thay vi tu nghi. Mien `am_luong_nen` **dung lai** mien gain
cua `tach_tieng` (0,0-2,0 buoc 0,05, `Cut_only ver2/bot_gui.py:909-913`): mot
san pham, mot mien gia tri cho moi thanh truot gain, du hai nguon la hai thu
khac nhau.
"""
from __future__ import annotations

import json
import math

from platform_core.i18n import _ as _t

from .am_master import NEN_GIAM_DB
from .tach_tieng import GAIN_LON_NHAT as _NHAC_NEN_GAIN_LON_NHAT
from .tach_tieng import GAIN_NHO_NHAT as _NHAC_NEN_GAIN_NHO_NHAT

#: Mac dinh = dung ban phoi truoc pha 23, va la CHINH hang so cua `am_master` chu
#: khong phai mot ban chep: hai cho khai cung mot con so la hai cho se lech nhau.
NEN_DB_MAC_DINH = NEN_GIAM_DB
NEN_DB_NHO_NHAT = -24.0
NEN_DB_LON_NHAT = 0.0
FADE_TOI_DA = 5.0

#: V3 (25/09) — mien am luong `nhac_nen`. DUNG LAI mien gain cua `tach_tieng`
#: (xem khoi docstring dau tep): khong tu dat mot mien thu hai cho cung mot
#: y niem "gain tuyen tinh cho mot nguon am thanh phu".
NHAC_NEN_AM_LUONG_NHO_NHAT = _NHAC_NEN_GAIN_NHO_NHAT
NHAC_NEN_AM_LUONG_LON_NHAT = _NHAC_NEN_GAIN_LON_NHAT
#: Khop `xu_ly_video.py:51` (`bg_volume = 0.25`) cua Viral — loi giai da co.
NHAC_NEN_AM_LUONG_MAC_DINH = 0.25
#: Cac khoa hop le cua MOT ho so `nhac_nen`.
_KHOA_NHAC_NEN = frozenset({"khoa", "am_luong_nen", "lap"})

MAC_DINH = {"nen_db": NEN_DB_MAC_DINH, "giam_theo_loi": False,
            "fade_vao": 0.0, "fade_ra": 0.0, "nhac_nen": None}

#: Tham so nen ha theo loi, DO o `PHA23_AUDIO_STUDIO.md` §2: giua hai cau nen doi
#: -0,33 dB, duoi loi ha 6,5-7,8 dB; giong doi 18 dB thi do ha chi lech 1,3 dB —
#: nho khoa da chuan hoa (khuech dai + han bien), khong nho giong to hay nho.
THAM_SO_HA_THEO_LOI = "threshold=0.1:ratio=2.5:attack=10:release=300"


class AmThanhLoi(ValueError):
    """Ho so am thanh khong hop le. Thong diep noi cho khach, tieng Viet."""


def _so(gt, ten: str) -> float:
    if isinstance(gt, bool) or not isinstance(gt, (int, float)) or not math.isfinite(gt):
        raise AmThanhLoi(_t('Giá trị âm thanh không hợp lệ: {ten}.').format(ten=ten))
    return round(float(gt), 1)


def _am_luong_nhac_nen(gt) -> float:
    """`am_luong_nen` — khuon `tach_tieng._gain` (lam tron 2 chu so, khong phai
    1 nhu `_so` o tren: buoc 0,05 can do chinh xac hon)."""
    if isinstance(gt, bool) or not isinstance(gt, (int, float)) or not math.isfinite(gt):
        raise AmThanhLoi(_t('Âm lượng nhạc nền không hợp lệ.'))
    v = round(float(gt), 2)
    if not NHAC_NEN_AM_LUONG_NHO_NHAT <= v <= NHAC_NEN_AM_LUONG_LON_NHAT:
        raise AmThanhLoi(_t('Âm lượng nhạc nền phải từ {a} đến {b}.').format(
            a=NHAC_NEN_AM_LUONG_NHO_NHAT, b=NHAC_NEN_AM_LUONG_LON_NHAT))
    return v


def chuan_hoa_nhac_nen(tho: dict) -> dict:
    """Ho so `nhac_nen` — MOT TEP KHACH TU TAI LEN, xem khoi docstring dau tep
    ve vi sao no la mot nguon KHAC voi lop "nhac" cua `tach_tieng`.

    Nem `AmThanhLoi`. Luy dang (khuon `chuan_hoa` / `tach_tieng.chuan_hoa_lop`:
    tu choi truong la, dien mac dinh cho truong vang trong ho so, `khoa` luon
    bat buoc khi ho so nay CO MAT).

    ⛔ **`khoa` KHONG duoc kiem quyen so huu o day** — cung hop dong voi
       `logo.chuan_hoa_mot`: ham nay thuan hinh dang, khong co `db`/`kho`. Kiem
       quyen thuoc ve bien goi (`assets.asset_cua`) o noi CO phien CSDL.
    """
    if not isinstance(tho, dict):
        raise AmThanhLoi(_t('Hồ sơ nhạc nền không đọc được.'))
    la = set(tho) - _KHOA_NHAC_NEN
    if la:
        raise AmThanhLoi(_t('Hồ sơ nhạc nền có trường lạ: {ds}.').format(
            ds=", ".join(sorted(la))))
    # Cung ba luat hinh dang `logo.chuan_hoa_mot` da dung cho `khoa`: khong
    # phai mot phep doan, chi la mot hang rao hinh dang truoc khi khoa di tiep
    # toi `assets.asset_cua` (kiem quyen so huu THAT, o bien co CSDL).
    khoa = str(tho.get("khoa") or "").strip()
    if not khoa or ".." in khoa or "://" in khoa or khoa.startswith("/"):
        raise AmThanhLoi(_t('Nhạc nền trỏ tới một tệp không hợp lệ.'))
    lap = tho.get("lap", True)
    if not isinstance(lap, bool):
        raise AmThanhLoi(_t('Giá trị lặp nhạc nền không hợp lệ.'))
    return {"khoa": khoa,
            "am_luong_nen": _am_luong_nhac_nen(
                tho.get("am_luong_nen", NHAC_NEN_AM_LUONG_MAC_DINH)),
            "lap": lap}


def chuan_hoa(tho: dict) -> dict:
    """Ho so DAY DU, da duyet. Nem `AmThanhLoi`. Luy dang."""
    if not isinstance(tho, dict):
        raise AmThanhLoi(_t('Hồ sơ âm thanh không đọc được.'))
    la = set(tho) - set(MAC_DINH)
    if la:
        raise AmThanhLoi(_t('Hồ sơ âm thanh có trường lạ: {ds}.').format(
            ds=", ".join(sorted(la))))
    ra: dict = dict(MAC_DINH)
    if "nen_db" in tho:
        if tho["nen_db"] is None:
            ra["nen_db"] = None
        else:
            v = _so(tho["nen_db"], "nen_db")
            if not NEN_DB_NHO_NHAT <= v <= NEN_DB_LON_NHAT:
                raise AmThanhLoi(_t('Mức nhạc nền phải từ {a} đến {b} dB.').format(
                    a=int(NEN_DB_NHO_NHAT), b=int(NEN_DB_LON_NHAT)))
            ra["nen_db"] = v
    if "giam_theo_loi" in tho:
        if not isinstance(tho["giam_theo_loi"], bool):
            raise AmThanhLoi(_t('Giá trị âm thanh không hợp lệ: {ten}.').format(
                ten="giam_theo_loi"))
        ra["giam_theo_loi"] = tho["giam_theo_loi"]
    for k in ("fade_vao", "fade_ra"):
        if k in tho:
            v = _so(tho[k], k)
            if not 0.0 <= v <= FADE_TOI_DA:
                raise AmThanhLoi(_t('Thời gian to dần / nhỏ dần phải từ 0 đến {n} giây.')
                                 .format(n=int(FADE_TOI_DA)))
            ra[k] = v
    # ⛔ Tat nen ma van "ha nen theo loi" la mot lua chon khong lam gi — tu choi
    #    thay vi lang le bo, de khach khong tuong no dang chay.
    if ra["nen_db"] is None and ra["giam_theo_loi"]:
        raise AmThanhLoi(_t('Đã tắt nhạc nền thì không còn gì để hạ theo lời thoại.'))
    # V3 (25/09): `nhac_nen` la MOT KHOA rieng, gia tri `None` (hoac vang mat)
    # nghia la khach KHONG tai nhac — ho so THUA giu nguyen (⛔ KHONG dien
    # `am_luong_nen=NHAC_NEN_AM_LUONG_MAC_DINH` khi khach chua tai gi).
    if "nhac_nen" in tho and tho["nhac_nen"] is not None:
        ra["nhac_nen"] = chuan_hoa_nhac_nen(tho["nhac_nen"])
    return ra


def tu_form(chuoi: str) -> dict | None:
    """JSON tu form -> ho so de LUU, hoac `None` khi rong / bang mac dinh.

    ⭐ `None` khi bang mac dinh: mot ho so "mac dinh" ghi vao moi lan chay lam
       ho so cua lan chay khong chinh gi khac di ma khong vi ly do gi.
    """
    if not (chuoi or "").strip():
        return None
    try:
        tho = json.loads(chuoi)
    except (ValueError, TypeError) as exc:
        raise AmThanhLoi(_t('Hồ sơ âm thanh không đọc được.')) from exc
    ra = chuan_hoa(tho)
    return None if ra == MAC_DINH else ra


def tu_cai_dat(ho_so: dict | None) -> dict:
    """Ban DOC day du tu ho so da luu (hoac `None`)."""
    return dict(MAC_DINH) if not ho_so else chuan_hoa(dict(ho_so))


def cho_giao_dien() -> dict:
    """Mien gia tri cho giao dien — MOT nguon voi phep duyet o tren."""
    return {"nen_db": NEN_DB_MAC_DINH, "nen_min": NEN_DB_NHO_NHAT,
            "nen_max": NEN_DB_LON_NHAT, "fade_max": FADE_TOI_DA,
            "nhac_nen_am_luong_mac_dinh": NHAC_NEN_AM_LUONG_MAC_DINH,
            "nhac_nen_am_luong_min": NHAC_NEN_AM_LUONG_NHO_NHAT,
            "nhac_nen_am_luong_max": NHAC_NEN_AM_LUONG_LON_NHAT}
