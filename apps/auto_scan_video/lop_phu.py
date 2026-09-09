"""LOP PHU CHU — mot dong chu khach dat len hinh, o toa do phan so.

## Vi sao khong phai `subtitle_burn` doi ten

`hop_dong_v4.CAM_TRONG_MVP` cam `subtitle_burn`, va ly do duoc ghi ngay canh no:
**`apps/autosubvideo` da so huu viec do**. `V6_OPERATING_CONTRACT` noi cung mot
cau o muc "Khong duoc pha": *"AutoSubVideo owns subtitle rendering capability"*.

Hai thu dung chung mot bo loc (`drawtext`) nhung khong cung mot nang luc:

    phu de     : mot DAY doan, khoa theo thoi gian, sinh ra TU ban chep loi
    lop phu chu: mot chuoi TINH khach tu go, do khach dat cho

⛔ Va ranh gioi o day la **CO HOC, khong phai loi hua**: `chu` la MOT chuoi mot
   dong (`XUONG_DONG` bi tu choi), va ca lan chay toi da `SO_LOP_PHU_TOI_DA`
   lop. Mot phu de 400 doan khong the di qua cai cua nay du ai co muon.

   ⭐ Mot giao uoc ("dung dung cai nay lam phu de") se bi vi pham boi chinh
      nguoi viet no. Mot tran ba lop thi khong.

## Bon luat hinh hoc — dung cua `vung_che`, khong chep lai

L1 phan so 0..1 · L2 sai thi TU CHOI khong DOAN · L3 ra ngoai khung thi LOAI
khong KEP · L4 phai vao van tay. Xuat xu day du o `vung_che.py`.

⚠️ L3 o day co mot sac thai khac: be rong cua mot dong chu chi biet duoc **khi
   ffmpeg do font**, nen ta khong the kiem "chu co tran ra ngoai khung khong" o
   cong vao. Bi kich cua L3 la "kep ve bien che nham cho khac"; nen o day ta
   **khong kep**: neo o dau khach dat, tran thi tran. Ket qua khach thay dung
   bang ket qua khach xem truoc.

## 🔴 `textfile=` chu khong `text=` — va day la mot phep DO, khong phai gu

Do tren may nay (ffmpeg cua kho, `testsrc2` 640x360), hai cach truyen chu:

| chuoi thu | `text=` da thoat tung ky tu | `textfile=` |
|---|---|---|
| `Kenh cua toi - Dang ky nhe!` | OK | OK |
| `Tieng Viet co dau: Dang ky ngay` | **HONG** | OK |
| `Gio: 12:30` | **HONG** | OK |
| `C:\\Users\\x` | **HONG** | OK |
| `It's mine` | OK | OK |
| `Mot, hai, ba` | OK | OK |
| `Giam 50% hom nay` | OK | OK |
| `It's 50%: a\\b, [x]` | OK | OK |

    A hong 3/7      B hong 0/7

⭐ Ba cai hong khong phai ba loi le te. Chung la ba **tang** khac nhau cua cung
   mot van de: dau `:` (bo tach tham so cua filter), dau `\\` (bo thoat), va bang
   ma cua doi so dong lenh tren Windows. Mot bang thoat ky tu phai dung ca ba,
   va no chi "dung" cho toi chuoi thu tiep theo.

⇒ `textfile=` bo HET viec thoat chu cua khach. Thu duy nhat con phai thoat la
  mot DUONG DAN ma chinh ta sinh ra: ASCII, khong khoang trang, mot dau `:`.

⚠️ Cai gia phai tra: bo loc khong con la mot ham thuan tuy nua — no can mot thu
   muc de ghi tep chu. Do la ly do `viet_tep_chu()` tach rieng khoi `chuan_hoa()`.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from platform_core.i18n import _ as _t

#: So lop phu toi da mot lan chay. Xem doan "ranh gioi CO HOC" o dau tep: con
#: so nay la thu ngan `lop_phu` bien thanh `subtitle_burn`, khong phai mot han
#: muc hieu nang.
SO_LOP_PHU_TOI_DA = 3

#: Do dai mot dong chu. Mot dong 80 ky tu o co chu 6% chieu cao da chiem gan het
#: be ngang khung 16:9 — dai hon la tran ra ngoai, va §L3 khong kep.
CHU_TOI_DA = 80

#: Co chu tinh theo PHAN SO chieu cao khung (L1). 0,02 tren 1080p la 21 px —
#: nho nhat con doc duoc; 0,25 la mot phan tu chieu cao, da la bien hieu.
CO_CHU_TOI_THIEU = 0.02
CO_CHU_TOI_DA = 0.25
CO_CHU_MAC_DINH = 0.06

#: Mau: mot TAP DONG. Khong nhan chuoi tu do — mot ten mau di thang vao bieu
#: thuc filter la mot cho tiem chuoi, va `#RRGGBB` cua khach thi khong ai kiem.
MAU: tuple[str, ...] = ("trang", "den", "vang")
MAU_FFMPEG = {"trang": "white", "den": "black", "vang": "yellow"}
MAU_MAC_DINH = "trang"

#: Vien den quanh chu: mac dinh BAT. Chu trang tren nen trang la chu vo hinh, va
#: khach chi biet dieu do sau khi tra tien cho mot lan render.
VIEN_MAC_DINH = True

DO_MO_MAC_DINH = 1.0
DO_MO_TOI_THIEU = 0.05

#: Font. Uu tien mot bien moi truong de may khac cau hinh duoc, roi toi cac ung
#: vien co du chu tieng Viet.
#:
#: ⛔ Khong co duong lui im lang sang "font mac dinh cua ffmpeg": mot ban render
#:    ra chu vuong hop la mot ban render hong, va no hong SAU khi da tinh tien.
BIEN_FONT = "LTT_ASV_FONT_LOP_PHU"
FONT_UNG_VIEN: tuple[str, ...] = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
)


class LopPhuLoi(ValueError):
    """Lop phu khong dung. Thong bao LA cau tieng Viet cho khach doc."""


def _so(gia_tri, *, ten: str, thap: float, cao: float) -> float:
    try:
        x = float(gia_tri)
    except (TypeError, ValueError):
        raise LopPhuLoi(_t('Lớp phủ chữ có giá trị không đọc được.')) from None
    # ⛔ Cung cai bay `vung_che._so` da chan: `float("nan")` doc duoc, va MOI
    #    phep so sanh voi no deu False — nen no lot qua `thap <= x <= cao`.
    if x != x or x in (float("inf"), float("-inf")):
        raise LopPhuLoi(_t('Lớp phủ chữ có giá trị không đọc được.'))
    if not (thap <= x <= cao):
        raise LopPhuLoi(_t('Lớp phủ chữ có giá trị ngoài khoảng cho phép.'))
    return x


def _chu_sach(tho) -> str:
    """Chuoi khach go -> mot dong da kiem. Nem khi khong dung duoc.

    ⛔ Ky tu dieu khien bi tu choi chu khong bi LOC BO. Mot chuoi bi loc am tham
       la mot chuoi khach khong go, va ho chi thay no tren ban da render.

    ⭐ `XUONG_DONG` nam trong danh sach ay, va no la ranh gioi co hoc voi
       `subtitle_burn` — xem dau tep.
    """
    if not isinstance(tho, str):
        raise LopPhuLoi(_t('Lớp phủ chữ không đọc được.'))
    chu = tho.strip()
    if not chu:
        raise LopPhuLoi(_t('Lớp phủ chữ không được để trống.'))
    if len(chu) > CHU_TOI_DA:
        raise LopPhuLoi(
            _t('Lớp phủ chữ dài quá {n} ký tự.').format(n=CHU_TOI_DA))
    if any(ord(c) < 32 or ord(c) == 127 for c in chu):
        raise LopPhuLoi(_t('Lớp phủ chữ chỉ nhận MỘT dòng, không có ký tự '
                           'điều khiển. Muốn phụ đề theo lời thoại thì dùng '
                           'công cụ phụ đề, không dùng lớp phủ.'))
    return chu


def chuan_hoa_mot(tho: dict) -> dict:
    """Mot lop phu tho tu giao dien -> mot ban da kiem. Nem `LopPhuLoi` khi sai."""
    if not isinstance(tho, dict):
        raise LopPhuLoi(_t('Lớp phủ chữ không đọc được.'))

    ra = {
        "chu": _chu_sach(tho.get("chu")),
        "x": _so(tho.get("x"), ten="x", thap=0.0, cao=1.0),
        "y": _so(tho.get("y"), ten="y", thap=0.0, cao=1.0),
        "co_chu": _so(tho.get("co_chu", CO_CHU_MAC_DINH), ten="co_chu",
                      thap=CO_CHU_TOI_THIEU, cao=CO_CHU_TOI_DA),
        "do_mo": _so(tho.get("do_mo", DO_MO_MAC_DINH), ten="do_mo",
                     thap=DO_MO_TOI_THIEU, cao=1.0),
        "vien": bool(tho.get("vien", VIEN_MAC_DINH)),
    }

    mau = str(tho.get("mau") or MAU_MAC_DINH).strip()
    if mau not in MAU:
        raise LopPhuLoi(_t('Màu chữ không hợp lệ.'))
    ra["mau"] = mau

    # Khoang thoi gian: rong = ca video. Cung khuon `vung_che.chuan_hoa_mot`, va
    # cung ly do — hai cho doc mot luat thi chung khong lech nhau duoc.
    tu = tho.get("tu_giay")
    den = tho.get("den_giay")
    if tu is not None or den is not None:
        try:
            t0 = float(tu if tu is not None else 0.0)
            t1 = float(den) if den is not None else None
        except (TypeError, ValueError):
            raise LopPhuLoi(
                _t('Khoảng thời gian của lớp phủ chữ không đọc được.')) from None
        if t0 != t0 or (t1 is not None and t1 != t1):
            raise LopPhuLoi(_t('Khoảng thời gian của lớp phủ chữ không đọc được.'))
        if t0 < 0 or (t1 is not None and t1 <= t0):
            raise LopPhuLoi(_t('Khoảng thời gian của lớp phủ chữ không hợp lệ.'))
        ra["tu_giay"] = t0
        if t1 is not None:
            ra["den_giay"] = t1
    return ra


def chuan_hoa(danh_sach) -> list[dict]:
    """Ca mang lop phu. Rong la hop le — phan lon lan chay khong co lop nao."""
    if danh_sach in (None, "", []):
        return []
    if not isinstance(danh_sach, (list, tuple)):
        raise LopPhuLoi(_t('Danh sách lớp phủ chữ không đọc được.'))
    if len(danh_sach) > SO_LOP_PHU_TOI_DA:
        raise LopPhuLoi(_t('Tối đa {n} lớp phủ chữ trong một lần chạy.').format(
            n=SO_LOP_PHU_TOI_DA))
    return [chuan_hoa_mot(v) for v in danh_sach]


# ══════════════════════════════════════════════════════════════════════════════
#  Font va tep chu — hai thu bo loc can ma `chuan_hoa` khong sinh ra duoc
# ══════════════════════════════════════════════════════════════════════════════

def duong_font(*, ung_vien=None, moi_truong=None) -> str:
    """Duong dan tep font se dung. Nem khi khong co cai nao.

    ⛔ Khong lui ve font mac dinh cua ffmpeg. `drawtext` khong co font mac dinh
       tren Windows: thieu `fontfile` thi no **tu choi ca chuoi loc**, va thong
       bao khong nhac gi toi font. Ta noi ra truoc, bang tieng Viet.
    """
    import os

    mt = os.environ if moi_truong is None else moi_truong
    tu_bien = str(mt.get(BIEN_FONT) or "").strip()
    ds = [tu_bien] if tu_bien else []
    ds += list(FONT_UNG_VIEN if ung_vien is None else ung_vien)
    for d in ds:
        if d and Path(d).is_file():
            return d
    raise LopPhuLoi(_t('Máy chủ không có phông chữ nào để vẽ lớp phủ. '
                       'Đặt {b} trỏ tới một tệp .ttf.').format(b=BIEN_FONT))


def thoat_duong(duong: str) -> str:
    """Duong dan -> dang dung duoc trong bieu thuc filter cua ffmpeg.

    ⚠️ Hai viec, va ca hai deu bat buoc tren Windows:
       `\\` -> `/`  (dau `\\` la ky tu thoat trong bieu thuc filter)
       `:`  -> `\\:` (dau `:` ngan hai THAM SO cua mot bo loc)

    ⭐ Do duoc: `C:/Windows/Fonts/arial.ttf` chua thoat lam ffmpeg tra
       *"Error : Invalid argument"* — mot thong bao khong nhac gi toi duong dan.
    """
    return str(duong).replace("\\", "/").replace(":", chr(92) + ":")


#: Do day vien = co chu (tinh ra pixel) nhan he so nay. 0,08 cho ra vien 3 px o
#: co chu 6% tren 1080p — du de tach chu khoi nen ma khong bien thanh mot khoi.
_HE_SO_VIEN = 0.08


def vien_px(lop: dict, cao_khung: int) -> int:
    """Do day vien, tinh bang PIXEL, cho mot lop tren mot khung cao `cao_khung`.

    🔴 **Phai la mot so nguyen, va do la mot phep DO chu khong phai mot lua chon.**

       `fontsize` cua `drawtext` NHAN bieu thuc (`H*0.06` chay), nhung `borderw`
       thi KHONG:

           borderw=2                  OK
           borderw=H*0.004            HONG   "Error : Invalid argument"
           borderw=max(1\\,H*0.004)    HONG   nhu tren

    ⛔ Nen khong the de bo loc tu tinh vien theo ti le nhu `_MAU_BAN_KINH` cua
       `che_do_render` lam voi ban kinh lam mo. Ai do dung mot con so tuyet doi
       (`borderw=2`) se duoc mot vien ro tren 480p va gan nhu vo hinh tren 4K —
       dung hinh dang loi ma luat L1 ton tai de tranh.

    ⇒ Chieu cao khung phai di TU NGOAI vao. Do la ly do `loc_cat_noi` doi
      `cao_khung` khi co lop phu, va tu choi khi thieu.
    """
    cao = int(cao_khung or 0)
    if cao <= 0:
        raise LopPhuLoi(_t('Không biết chiều cao khung hình để vẽ viền chữ.'))
    return max(1, round(cao * float(lop["co_chu"]) * _HE_SO_VIEN))


def ten_tep_chu(lop: dict) -> str:
    """Ten tep chua chu cua mot lop — dan xuat tu NOI DUNG, khong tu bo dem.

    ⭐ Cung ly do `assets.py` dan khoa tu van tay: hai lan dung mot cau chu ra
       cung mot ten, nen ghi lai la mot phep luy dang; va ten thuan ASCII nen
       duong dan khong bao gio can thoat gi ngoai dau `:` cua o dia.
    """
    bam = hashlib.sha256(str(lop["chu"]).encode("utf-8")).hexdigest()[:16]
    return f"lop_phu_{bam}.txt"


def viet_tep_chu(lop_phu, thu_muc) -> list[str]:
    """Ghi chu cua tung lop ra tep UTF-8, tra ve duong dan theo dung thu tu.

    ⛔ UTF-8 **khong BOM**: `drawtext` doc nguyen byte, nen ba byte BOM se hien
       ra thanh mot ky tu rac o dau dong chu.

    ⚠️ Va `write_bytes`, khong `write_text`: tren Windows `write_text` dich `\\n`
       thanh `\\r\\n`. Mot dong chu khong co `\\n` — nhung luat nay dung o day de
       khong ai them mot dong thu hai roi tu hoi vi sao co o vuong.
    """
    goc = Path(thu_muc)
    goc.mkdir(parents=True, exist_ok=True)
    ra: list[str] = []
    for lop in lop_phu:
        tep = goc / ten_tep_chu(lop)
        tep.write_bytes(str(lop["chu"]).encode("utf-8"))
        ra.append(str(tep))
    return ra
