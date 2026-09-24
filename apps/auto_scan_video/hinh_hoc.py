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


# ══════════════════════════════════════════════════════════════════════════════
#  Khung hinh bien tap: cat khung -> phong -> doi ti le (asv-final 22/09)
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔑 **Ham thuan, so NGUYEN, tinh MOT lan.** Ban dung ghi `khung_ra`, trinh render
#    dung lenh tu cung ham nay, va `ban_dung.kiem` tinh lai de doi chieu. Ba noi
#    doc mot ham thi khong the lech nhau ve kich thuoc ban ra — thu logo, vien
#    chu va `PlayRes` cua phu de deu dua vao.
#
# ⭐ Thu tu la mot quyet dinh, khong phai tien tay: VUNG CHE dat TRUOC ham nay
#    (toa do nguon — no bam theo noi dung), con logo / chu / phu de dat SAU (toa
#    do ban ra — no bam theo man hinh). Nen luat L3 cua `vung_che` ("bien doi hinh
#    lam hop ra ngoai khung thi LOAI, khong KEP") tu dung ma khong can anh xa:
#    mot vung nam ngoai cua so cat chi don gian la khong con trong khung.

def _chan_duoi(x: float) -> int:
    """Lam tron XUONG so chan. `yuv420p` lay mau 2x2 — xem `_loc_lam_mo`."""
    return max(0, int(x) // 2 * 2)


def _canh(x: float) -> int:
    """Kich thuoc: so chan, it nhat 2."""
    return max(2, int(x) // 2 * 2)


def _dat_tam(tam: float, dai: int, cua_so: int) -> int:
    """Goc cua mot cua so dai `cua_so` sao cho TAM nam o `tam*dai`, trong `[0, dai-cua_so]`.

    ⭐ Kep CUA SO vao khung o day la dung, khac L3: ta dich khung nhin cho no
       khong ra ngoai anh, chu khong dich mot vung khach da ve.
    """
    goc = float(tam) * dai - cua_so / 2.0
    return _chan_duoi(min(max(goc, 0.0), float(dai - cua_so)))


def khung_bien_tap(rong: int, cao: int, ho_so: dict) -> dict:
    """Ho so bien tap (`bien_tap.chuan_hoa`) + khung NGUON -> cac buoc pixel.

    Tra ve::

        {"cat":   (w, h, x, y) | None,   # mot `crop` tren khung nguon
         "phong": (w, h) | None,         # `scale` tro lai sau khi phong
         "khung": {...} | None,          # doi ti le: `cat` hoac `nen_mo`
         "ra":    (w, h)}                # kich thuoc BAN RA

    ⛔ Nem `ValueError` khi khong biet khung nguon: doan mot kich thuoc la cat
       sai cho, va ffmpeg chi bao khi `crop` vuot khung — tuc o phut thu muoi.
    """
    rong, cao = int(rong or 0), int(cao or 0)
    if rong <= 0 or cao <= 0:
        raise ValueError("khung nguon chua biet — khong tinh duoc bien tap khung")
    ho_so = dict(ho_so or {})

    # 1. Cat khung (phan so nguon)
    ck = ho_so.get("cat_khung") or {}
    x0, y0 = float(ck.get("x0", 0.0)), float(ck.get("y0", 0.0))
    x1, y1 = float(ck.get("x1", 1.0)), float(ck.get("y1", 1.0))
    if ck:
        cx, cy = _chan_duoi(rong * x0), _chan_duoi(cao * y0)
        cw = min(_canh(rong * (x1 - x0)), rong - cx)
        ch = min(_canh(cao * (y1 - y0)), cao - cy)
        cat = (cw, ch, cx, cy)
    else:
        cx = cy = 0
        cw, ch, cat = rong, cao, None
    phong = None

    # 2. Phong tinh: mot cua so nho hon trong khung da cat, roi phong ve (cw, ch)
    zm = ho_so.get("zoom") or {}
    if zm:
        z = float(zm["he_so"])
        zw, zh = _canh(cw / z), _canh(ch / z)
        zx = cx + _dat_tam(float(zm.get("tam_x", 0.5)), cw, zw)
        zy = cy + _dat_tam(float(zm.get("tam_y", 0.5)), ch, zh)
        cat, phong = (zw, zh, zx, zy), (cw, ch)
    hien_w, hien_h = cw, ch

    # 3. Doi ti le
    kh = ho_so.get("khung") or {}
    khung = None
    if kh:
        tu, mau = (int(s) for s in str(kh["ti_le"]).split(":"))
        a = tu / mau
        if abs(hien_w / hien_h - a) > 0.01:
            if kh.get("cach") == "nen_mo":
                ngan = min(hien_w, hien_h)
                cw2, ch2 = ((_canh(ngan * a), _canh(ngan)) if a >= 1
                            else (_canh(ngan), _canh(ngan / a)))
                f = min(cw2 / hien_w, ch2 / hien_h)
                fw, fh = min(_canh(hien_w * f), cw2), min(_canh(hien_h * f), ch2)
                khung = {"cach": "nen_mo", "nen": (cw2, ch2), "hinh": (fw, fh),
                         "vi_tri": (_chan_duoi((cw2 - fw) / 2),
                                    _chan_duoi((ch2 - fh) / 2))}
                hien_w, hien_h = cw2, ch2
            else:
                if hien_w / hien_h > a:
                    nw, nh = min(_canh(hien_h * a), hien_w), hien_h
                else:
                    nw, nh = hien_w, min(_canh(hien_w / a), hien_h)
                khung = {"cach": "cat", "cat": (
                    nw, nh,
                    _dat_tam(float(kh.get("tam_x", 0.5)), hien_w, nw),
                    _dat_tam(float(kh.get("tam_y", 0.5)), hien_h, nh))}
                hien_w, hien_h = nw, nh

    return {"cat": cat, "phong": phong, "khung": khung, "ra": (hien_w, hien_h)}
