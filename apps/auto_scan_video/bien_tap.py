"""Ho so BIEN TAP KHUNG + TOC DO cua mot lan chay — asv-final 22/09.

Bon dieu khien, mot ho so, mot khoa `bien_tap` trong `cai_dat` (THUA — vang mat
khi khach khong doi gi, `cai_dat.KHOA_THUA`):

| truong | nghia | mien |
|---|---|---|
| `toc_do` | tang toc CA ban ra (hinh + tieng + phu de cung mot he so) | `(1.0, 1.5]` |
| `cat_khung` | `{x0,y0,x1,y1}` phan so khung NGUON | moi canh >= `CANH_TOI_THIEU` |
| `zoom` | `{he_so, tam_x?, tam_y?}` — phong TINH quanh mot tam | `(1.0, 3.0]` |
| `khung` | `{ti_le, cach, tam_x?, tam_y?}` — doi ti le khung | `TI_LE` x `CACH_KHUNG` |

Quyet dinh san pham va ly do: `docs/auto_scan_video_final/ADR_BIEN_TAP.md`.

## Toc do: nhan DEU sau cung, khong lap lai ke hoach

🔑 `toc_do` ap o CUOI chuoi loc (`setpts=PTS/s`) va tren ban phoi (`atempo=s`),
   sau khi hinh, loi long, nen, phu de da dat dung cho tren truc thoi gian BIEN
   TAP. Nen anh xa nguon -> ban ra la hai buoc, va buoc hai la mot phep chia:

       t_ban_ra = BanDoThoiGian.ra(t_nguon) / toc_do        (`moc_ban_ra`)

⇒ Moi doan loi long, moi dong phu de, moi canh deu di cung MOT phep chia — dong
  bo hinh/tieng dung **theo cau truc**, khong phai theo mot phep do may man. Ke
  hoach thoi gian, TTS va ban phoi van lap tren truc bien tap nhu truoc — toc do
  chi vao cuoc choi o COMPOSE (thoi luong mong doi) va RENDER (chuoi loc).

⛔ `toc_do < 1` bi TU CHOI: `hop_dong_v4.DUNG_SAI_DO_DAI_S` hua KHONG preset nao
   lam video dai ra. Tran 1,5 giu loi long con nghe duoc (`atempo` giu cao do,
   nhung loi da co the bi `he_so_toc` nen san — xem ADR).
"""
from __future__ import annotations

import json
import math

from platform_core.i18n import _ as _t

TOC_DO_TOI_DA = 1.5
ZOOM_TOI_DA = 3.0
#: Canh nho nhat cua cua so cat khung, phan so. Nho hon la mot lan keo nham,
#: va mot cua so 5% cua 720p la 36 dong — khong con la mot video.
CANH_TOI_THIEU = 0.2

TI_LE: tuple[str, ...] = ("16:9", "9:16", "1:1", "4:5")
CACH_CAT = "cat"
CACH_NEN_MO = "nen_mo"
CACH_KHUNG: tuple[str, ...] = (CACH_CAT, CACH_NEN_MO)

_TRUONG = ("toc_do", "cat_khung", "zoom", "khung")


class BienTapLoi(ValueError):
    """Ho so bien tap khong hop le. Thong diep cho khach, tieng Viet."""


def _so(gt, ten: str) -> float:
    if isinstance(gt, bool) or not isinstance(gt, (int, float)) or not math.isfinite(gt):
        raise BienTapLoi(_t('Giá trị biên tập không hợp lệ: {ten}.').format(ten=ten))
    return round(float(gt), 4)


def _tam(tho: dict, ra: dict) -> None:
    for k in ("tam_x", "tam_y"):
        if k in tho:
            v = _so(tho[k], k)
            if not 0.0 <= v <= 1.0:
                raise BienTapLoi(_t('Tâm khung hình phải nằm trong khung (0–100%).'))
            if v != 0.5:
                ra[k] = v


def _thua(tho: dict, cho_phep: tuple[str, ...], ten: str) -> None:
    la = set(tho) - set(cho_phep)
    if la:
        raise BienTapLoi(_t('Biên tập khung hình có trường lạ: {ds}.').format(
            ds=", ".join(f"{ten}.{k}" for k in sorted(la))))


def chuan_hoa(tho) -> dict:
    """Ho so THUA da duyet: chi nhung truong khac mac dinh. Nem `BienTapLoi`. Luy dang.

    ⛔ Sai thi TU CHOI, khong kep ve bien (cung luat L2 cua `vung_che`): mot cua so
       bi "sua ho" la mot cua so khach khong ve.
    """
    if not isinstance(tho, dict):
        raise BienTapLoi(_t('Biên tập khung hình không đọc được.'))
    _thua(tho, _TRUONG, "bien_tap")
    ra: dict = {}

    if tho.get("toc_do") is not None:
        v = _so(tho["toc_do"], "toc_do")
        if not 1.0 <= v <= TOC_DO_TOI_DA:
            raise BienTapLoi(_t('Tốc độ phải từ 1× đến {n}× — video ra không được '
                                'dài hơn video vào.').format(n=TOC_DO_TOI_DA))
        if v != 1.0:
            ra["toc_do"] = v

    ck = tho.get("cat_khung")
    if ck:
        if not isinstance(ck, dict):
            raise BienTapLoi(_t('Biên tập khung hình không đọc được.'))
        _thua(ck, ("x0", "y0", "x1", "y1"), "cat_khung")
        x0, y0 = _so(ck.get("x0", 0.0), "x0"), _so(ck.get("y0", 0.0), "y0")
        x1, y1 = _so(ck.get("x1", 1.0), "x1"), _so(ck.get("y1", 1.0), "y1")
        if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
            raise BienTapLoi(_t('Khung cắt phải nằm trong hình, cạnh đầu trước cạnh cuối.'))
        if x1 - x0 < CANH_TOI_THIEU or y1 - y0 < CANH_TOI_THIEU:
            raise BienTapLoi(_t('Khung cắt quá nhỏ — mỗi cạnh ít nhất {p}% khung hình.')
                             .format(p=int(CANH_TOI_THIEU * 100)))
        if (x0, y0, x1, y1) != (0.0, 0.0, 1.0, 1.0):
            ra["cat_khung"] = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}

    zm = tho.get("zoom")
    if zm:
        if not isinstance(zm, dict):
            raise BienTapLoi(_t('Biên tập khung hình không đọc được.'))
        _thua(zm, ("he_so", "tam_x", "tam_y"), "zoom")
        z = _so(zm.get("he_so", 1.0), "he_so")
        if not 1.0 <= z <= ZOOM_TOI_DA:
            raise BienTapLoi(_t('Mức phóng to phải từ 1× đến {n}×.').format(n=ZOOM_TOI_DA))
        if z != 1.0:
            ra["zoom"] = {"he_so": z}
            _tam(zm, ra["zoom"])

    kh = tho.get("khung")
    if kh:
        if not isinstance(kh, dict):
            raise BienTapLoi(_t('Biên tập khung hình không đọc được.'))
        _thua(kh, ("ti_le", "cach", "tam_x", "tam_y"), "khung")
        if kh.get("ti_le") not in TI_LE:
            raise BienTapLoi(_t('Tỉ lệ khung hình không có trong danh sách.'))
        cach = kh.get("cach") or CACH_CAT
        if cach not in CACH_KHUNG:
            raise BienTapLoi(_t('Cách đổi tỉ lệ khung hình không hợp lệ.'))
        ra["khung"] = {"ti_le": kh["ti_le"], "cach": cach}
        if cach == CACH_CAT:
            _tam(kh, ra["khung"])
    return ra


def tu_form(chuoi: str, *, preset: str) -> dict | None:
    """JSON tu form -> ho so de LUU, hoac `None` khi rong / bang mac dinh.

    ⭐ Tang thu nhat trong ba tang (y het `vung`/`lop_phu`/`logo`): tu choi o CUA,
       truoc khi giu credit. Hai tang kia: giao dien an khoi o preset giu hinh, va
       `ban_dung.kiem` chan mot ban dung `sao_chep` mang bien tap.
    """
    from . import hop_dong_v4

    if not (chuoi or "").strip():
        return None
    try:
        tho = json.loads(chuoi)
    except (ValueError, TypeError) as exc:
        raise BienTapLoi(_t('Biên tập khung hình không đọc được.')) from exc
    ra = chuan_hoa(tho)
    if not ra:
        return None
    if preset != hop_dong_v4.PRESET_CAT_THONG_MINH:
        if set(ra) == {"toc_do"}:
            raise BienTapLoi(_t(
                'Kiểu “Giữ nguyên hình ảnh” hứa video ra dài đúng bằng video vào, '
                'nên không đổi tốc độ được. Chọn “Rút gọn có biên tập” nếu bạn '
                'muốn tăng tốc.'))
        raise BienTapLoi(_t(
            'Kiểu “Giữ nguyên hình ảnh” sao chép nguyên vẹn từng điểm ảnh, nên '
            'không thể cắt khung, phóng to, đổi tỉ lệ hay đổi tốc độ. Chọn “Rút '
            'gọn có biên tập” nếu bạn muốn biên tập khung hình.'))
    return ra


def toc_do(ho_so: dict | None) -> float:
    """He so toc do cua mot ho so da luu. `1.0` khi vang mat."""
    return float((ho_so or {}).get("toc_do") or 1.0)


def moc_ban_ra(t_bien_tap: float, ho_so: dict | None) -> float:
    """Moc tren truc BIEN TAP (sau cat canh) -> moc tren BAN RA (sau toc do).

    🔑 Buoc thu hai cua anh xa nguon -> ban ra; buoc thu nhat la
       `BanDoThoiGian.ra`. Mot cho, cho QC va cho thoi luong mong doi.
    """
    return float(t_bien_tap) / toc_do(ho_so)


def cho_giao_dien() -> dict:
    """Mien gia tri cho giao dien — MOT nguon voi phep duyet o tren."""
    return {"toc_do_max": TOC_DO_TOI_DA, "zoom_max": ZOOM_TOI_DA,
            "canh_min_pct": int(CANH_TOI_THIEU * 100),
            "ti_le": list(TI_LE), "cach": list(CACH_KHUNG)}
