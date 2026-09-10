"""HAI quy tac dung chung cua moi thu khach dat len khung hinh.

## Vi sao module nay ra doi o pha 08, khong phai o pha 05

`vung_che` (V5) viet ra **bon luat** hinh hoc va giai thich xuat xu tung luat.
Nhung hai phep **thi hanh** cua chung — doc mot phan so 0..1, va doc mot khoang
thoi gian — thi moi module tu chep lai:

    vung_che._so        + khoi `tu_giay`/`den_giay`
    cat_dau_cuoi        (mot bien the tren truc thoi luong)
    lop_phu._so         + khoi `tu_giay`/`den_giay`     <- ban thu ba

⛔ Ba ban cua mot quy tac la ba ban se lech, va chung se lech **im lang**: mot
   ban quen chan `NaN` van xanh o moi phep kiem cua chinh no.

⭐ Va toi biet dieu do vi vua viet mot phep kiem cho dung hinh dang ay o cho
   khac — `test_462::test_ma_nguon_khong_tu_tinh_anh_xa` chot rang phep anh xa
   `moc nguon -> moc ra` co DUNG MOT chu so huu. Hai quy tac o day dang o tinh
   trang ma phep kiem do ton tai de cam.

## Pham vi: DUNG lai, khong VIET LAI

Pha 08 dung module nay cho `lop_phu` va `logo`. `vung_che` va `cat_dau_cuoi`
**chua** chuyen — chung la ma V5 dang chay kem bo kiem rieng, va mot lan di tru
phai di cung doi chung cua chinh no.

⚠️ Nen hom nay con **hai** ban chep. Viet ra day de no la mot mon no CO TEN chu
   khong phai mot su trung lap khong ai de y — va de nguoi di tru sau nay biet
   dich den o dau.
"""
from __future__ import annotations

from typing import Callable


def so_phan_so(gia_tri, *, thap: float, cao: float,
               loi: Callable[[str], Exception], khong_doc_duoc: str,
               ngoai_khoang: str) -> float:
    """Doc mot so trong `[thap, cao]`. Nem `loi(...)` khi khong dung.

    ⛔ **`NaN` phai duoc chan RIENG.** `float("nan")` doc duoc, va MOI phep so
       sanh voi no deu `False` — nen no lot qua `thap <= x <= cao` neu ta chi
       viet mot phep so sanh. Do la bay ma ca `vung_che._so` lan `lop_phu._so`
       deu phai chan tay, va la ly do dau tien de gom chung lai.

    ⚠️ `inf` cung the: no khong phai `NaN`, no chi vuot moi khoang — nhung mot
       `-inf` thi lot qua `thap <= x` neu `thap` la `-inf`. Chan tuong minh.
    """
    try:
        x = float(gia_tri)
    except (TypeError, ValueError):
        raise loi(khong_doc_duoc) from None
    if x != x or x in (float("inf"), float("-inf")):
        raise loi(khong_doc_duoc)
    if not (thap <= x <= cao):
        raise loi(ngoai_khoang)
    return x


def khoang_thoi_gian(tho: dict, *, loi: Callable[[str], Exception],
                     khong_doc_duoc: str, khong_hop_le: str) -> dict:
    """`{tu_giay?, den_giay?}` da kiem, hoac `{}` khi khach khong dat gio.

    🔑 **Vang mat va `0` la HAI y dinh khac nhau**, va phan biet duoc chung la
       ca diem cua ham nay:

           khong co khoa  -> ap ca video
           `tu_giay: 0`   -> "tu dau video", mot cau KHAC

       Tu pha 12a hai cau ay cho hai van tay khac nhau, nen mot ham "tien tay"
       tra ve `{"tu_giay": 0.0}` cho truong hop dau se lam **moi** lan chay cu
       mat cache ma khong vi ly do gi.

    ⛔ Nem khi `den_giay <= tu_giay`: khoang nguoc bi TU CHOI chu khong bi dao
       lai. Mot khoang bi "sua ho" la mot khoang khach khong ve.
    """
    tu = tho.get("tu_giay")
    den = tho.get("den_giay")
    if tu is None and den is None:
        return {}
    try:
        t0 = float(tu if tu is not None else 0.0)
        t1 = float(den) if den is not None else None
    except (TypeError, ValueError):
        raise loi(khong_doc_duoc) from None
    if t0 != t0 or (t1 is not None and t1 != t1):
        raise loi(khong_doc_duoc)
    if t0 < 0 or (t1 is not None and t1 <= t0):
        raise loi(khong_hop_le)
    ra = {"tu_giay": t0}
    if t1 is not None:
        ra["den_giay"] = t1
    return ra
