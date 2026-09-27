"""Phu de cho Auto Scan Video — mien + cau noi, V6 pha 14.

## 🔑 Tep nay KHONG dung phu de. No noi phu de nao duoc dung, va o dau.

`apps/autosubvideo` so huu hai viec that, va ASV chi tai dung MOT:

  · **tac gia** — preset kieu chu, phan doan, dung `.ass`/`.srt`
    (`style_registry.py`, `ass_builder.py`, `segmenter.py`)     -> TAI DUNG
  · **ma hoa** — chay ffmpeg dot phu de vao hinh (`burn.py`)     -> KHONG

⛔ **Vi sao khong goi `burn.burn()`** — cach doc tu nhien nhat cua *"khong
   duplicate renderer"*, va la cach SAI: no chay mot luot ffmpeg DAY DU cua
   rieng no, tuc video bi ma hoa lai **hai lan**. Pha 26 (*Renderer fusion*) ton
   tai de gop moi bien doi diem anh vao MOT lan encode; goi `burn()` o day la tu
   tao ra dung khoan no ma pha 26 phai tra.

⇒ ASV dung `.ass` roi dua `ass=` vao **chinh `-filter_complex` ma `ket_xuat.py`
  da dung** — dung canh `drawtext` (lop phu) va `overlay` (logo).

## 🔴 TRUC THOI GIAN — cho de sai nhat, va no da co mot tien le

`che_do_render.loc_cat_noi` CAT cac khoang giu lai roi NOI chung, nen moc cua
ban ra **khong bang** moc cua ban goc: mot cau o giay 180 cua nguon co the roi
vao giay 74 cua tep ra, hoac **khong ton tai**. Bo loc `ass=` doc moc TUYET DOI.

⇒ `.ass` **phai** dung tu `ke_hoach` (`thoi_gian.lap_ke_hoach`), noi
  `dat_tai_ms` DA nam tren truc RA — no di qua `ban_do.ra()`.

⛔ Dung tu ban chep loi nguon (`content.json`, `ban_ghi`) se cho phu de troi
   **dung nhu tieng da troi truoc pha 16**. Docstring cua `lap_ke_hoach` ghi
   nguyen van: *"`ban_do` la thu pha 16 them vao, va thieu no thi preset cat sai
   AM THAM"*. Do la cung mot loi, phat hien lai lan hai.

⭐ Nen cau noi o duoi khong tu anh xa gi ca — no chi doc `dat_tai_ms`/`dai_ms`.
   Phep anh xa da co chu so huu, va chu so huu do la `ban_do_thoi_gian`.

## ⛔ HAI TRUC, gop lam mot la khoa mat mot tinh nang

|  | doi diem anh? | chay o preset giu hinh? |
|---|---|---|
| **dot** phu de vao hinh | co | **khong the** — `-c:v copy` khong giai ma khung nao |
| **xuat** tep `.srt` | khong | **duoc**, va day la lua chon phu de DUY NHAT o do |

⚠️ Ban nhap dau tra `None` ngay khi `che_do == tat`, **truoc khi** doc
   `xuat_srt` — nghia la to hop *"chi xuat SRT"* khong dien dat duoc. Cai bi mat
   khong bao loi; no chi **khong ton tai**.

## 🔴 Va mot bay im lang o bien

`style_registry.get_config(style_id)` **roi ve `default`** khi id la:

    preset = _PRESETS.get(style_id) or _PRESETS["default"]

Voi `autosubvideo` do la lua chon hop ly. Voi ASV thi **khong**: khach chon mot
kieu, mot id cu hay go sai di qua, va ho nhan `default` ma khong ai noi gi. Dung
hang loi ma `lop_phu` da tu choi khi no **nem** thay vi loc bo ky tu dieu khien.
"""
from __future__ import annotations

from pathlib import Path
from typing import get_args

from platform_core.i18n import N_
from platform_core.i18n import _ as _t

# ── Che do DOT phu de vao hinh ───────────────────────────────────────────────

#: Nam che do (asv-final, lan phu-de 22/09). Bang day du + ly do:
#: `docs/auto_scan_video_final/L_PHU_DE.md` §1.
#:
#:   che_do    chu tren hinh            vi tri                    kieu chu
#:   tat       —                        —                         —
#:   tu_dong   BAN DICH (loi thuyet     tranh dai phu de goc      preset (mac dinh
#:             minh dang doc)           da danh dau (xem          `default`)
#:                                      `vi_tri_tu_dong`)
#:   nguon     LOI GOC (ban ghi chuan   cua preset                preset
#:             — ASR hay OCR, `goc`)
#:   dich      BAN DICH                 cua preset                preset
#:   tu_chon   `chu` = dich | nguon     cua preset + tinh chinh   preset + tinh chinh
#:
#: ⛔ "Tu dong" KHONG phai "dich voi ten khac": no la che do DUY NHAT tu quyet
#:    vi tri. Do 22/09 tren 4 clip `TEST VIDEO`: dai hardsub nam o 0,76–0,98
#:    chieu cao, va kieu `default` dat o 0,78–0,94 ⇒ chong len hardsub o CA 4.
CHE_DO_TAT = "tat"
CHE_DO_TU_DONG = "tu_dong"
CHE_DO_NGUON = "nguon"
CHE_DO_DICH = "dich"
CHE_DO_TU_CHON = "tu_chon"

CHE_DO: tuple[str, ...] = (CHE_DO_TAT, CHE_DO_TU_DONG, CHE_DO_NGUON,
                           CHE_DO_DICH, CHE_DO_TU_CHON)

#: Nhung che do DOT vao hinh — tat ca tru `tat`.
CHE_DO_DOT: tuple[str, ...] = tuple(c for c in CHE_DO if c != CHE_DO_TAT)

CHE_DO_MAC_DINH = CHE_DO_TAT

#: Nguon CHU cua phu de. Khoa trong tai lieu `CONTENT_PROCESS` (`van_ban.dung`):
#: `goc` = loi cua ban ghi chuan (ASR hom nay, OCR khi lan L-E them — no ghi
#: `nguon_loi` o ban ghi, con chu van nam o `goc`), `chu` = ban dich.
CHU_DICH = "dich"
CHU_NGUON = "nguon"
CHU: tuple[str, ...] = (CHU_DICH, CHU_NGUON)
_KHOA_CHU = {CHU_DICH: "chu", CHU_NGUON: "goc"}

#: ⚠️ Trung voi id `default` cua `style_registry`, va do la ban sao duy nhat
#:    khong tranh duoc: phai neu duoc mot kieu khoi diem bang ten.
#:    `kieu_hop_le()` kiem no moi lan chay, nen neu `autosubvideo` doi ten id do
#:    thi `test_471` do ngay chu khong troi im lang.
KIEU_MAC_DINH = "default"

PHAN_DOAN_MAC_DINH = "sentence"


class PhuDeLoi(ValueError):
    """Yeu cau phu de khong hop le. Xep loai `NGUOI_DUNG` o `loi.py`."""


# ── Nguon chan ly: hoi APP CHU, khong chep ───────────────────────────────────

def kieu_hop_le() -> tuple[str, ...]:
    """Id kieu, lay tu `style_registry`.

    ⛔ **Khong chep danh sach nay.** Mot ban sao troi ngay lan dau `autosubvideo`
       them mot kieu — va troi IM LANG: khach thay kieu moi o app kia ma khong
       thay o day, khong loi nao o dau.
    """
    from apps.autosubvideo.style_registry import list_ids

    return tuple(list_ids())


def phan_doan_hop_le() -> tuple[str, ...]:
    """Che do phan doan, lay tu `segmenter.SegmentMode`.

    ⚠️ `autosubvideo` DA co hai ban cua danh sach nay: kieu `Literal` o
       `segmenter.py:20` va mot regex o `schemas.py:105`. Doc ban `Literal` bang
       `get_args` chu **khong tao ban thu ba** — no se lech voi ca hai ban kia
       theo hai huong khac nhau.
    """
    from apps.autosubvideo.segmenter import SegmentMode

    return tuple(get_args(SegmentMode))


# ── Tinh chinh kieu chu (V6 pha 16) ─────────────────────────────────────────

#: Nhung truong cua `SubtitleStyleConfig` mo ra cho khach.
#:
#: 🔴 **Danh sach nay la mot QUYET DINH SAN PHAM, khong phai mot bo loc ky
#:    thuat.** Mo hinh co 27 truong; do het ra man hinh la doi khach thiet ke
#:    mot kieu chu thay vi chon mot kieu chu — trong khi 9 preset da lam dung
#:    viec do. Muoi tam truong nay tra loi dung nhung truc ma pha 16 goi ten:
#:    font · co · mau · vien · vi tri · nen · karaoke/nhan manh · chuyen dong.
#:
#: ⛔ Chin truong CON LAI co y khong mo, va moi truong mot ly do:
#:
#:      `font_fallback`         chuoi font he thong — mot quyet dinh HA TANG
#:      `italic`                khong truc nao cua pha 16 goi ten no
#:      `shadow_color`          bong do chong len vien; hai nut cho cung mot
#:      `shadow_offset`         hieu ung thi khach chinh mai khong ra
#:      `bg_padding`            chi co nghia khi `bg_box`; mot nut hang hai
#:      `margin_h`              le ngang doi rat it tren video doc va ngang
#:      `line_spacing`          `ass_builder` da can theo `font_size`
#:      `keyword_highlights`    can mot trinh soan danh sach tu — pha rieng
#:      `keyword_highlight_color`  di kem truong tren
#:
#: ⭐ Chung KHONG bi cam — chung chi khong co o giao dien. Mo them mot truong
#:    sau nay chi la them mot ten vao day; khong tang nao khac phai doi, vi ca
#:    tang duyet doc mo hinh chu khong doc danh sach nay.
TRUONG_MO: tuple[str, ...] = (
    "font_family", "font_size", "font_color", "bold",
    "outline_color", "outline_width",
    "alignment", "margin_v", "safe_area_percent",
    "bg_box", "bg_color", "bg_opacity",
    "highlight_mode", "highlight_color",
    "animation", "animation_ms",
    "max_chars_per_line", "max_lines",
)


def _mo_hinh_kieu():
    """`SubtitleStyleConfig` cua app chu. Mot cho import, de doi chung de dat."""
    from apps.autosubvideo.schemas import SubtitleStyleConfig

    return SubtitleStyleConfig


def chuan_hoa_tinh_chinh(tho, *, kieu: str) -> dict:
    """Tinh chinh THUA cua khach -> dict da duyet. Nem `PhuDeLoi`.

    🔑 **Duyet bang cach DUNG THU ca cau hinh cuoi cung**, khong bang cach kiem
       tung truong roi hy vong. Mo hinh cua app chu biet mien cua moi truong va
       `extra="forbid"` bat ca loi go sai TEN — thu ma mot vong `for` tu viet
       khong bao gio bat duoc, vi no chi nhin nhung ten no biet.

    ⭐ Giu THUA: chi ghi lai nhung khoa khach thuc su doi. Mot ban day du se lam
       ho so cua moi lan chay mang 27 truong, va ho so cua hai lan chay dung
       cung preset se khac nhau ngay khi app chu doi mot mac dinh — tuc van tay
       doi ma cau hinh thi khong.
    """
    if not tho:
        return {}
    if not isinstance(tho, dict):
        raise PhuDeLoi(_t('Tinh chỉnh phụ đề không đọc được.'))

    la = [k for k in tho if k not in TRUONG_MO]
    if la:
        # ⛔ Neu ten thuoc mo hinh nhung khong nam trong `TRUONG_MO` thi day la
        #    mot truong CO Y khong mo, khong phai mot loi go sai. Hai tinh
        #    huong, hai cau tra loi.
        raise PhuDeLoi(_t('Không chỉnh được thuộc tính: {ten}')
                       .format(ten=", ".join(sorted(la))))

    goc = cau_hinh_goc(kieu)
    try:
        _mo_hinh_kieu()(**{**goc.model_dump(), **tho})
    except Exception as exc:                       # pydantic.ValidationError
        raise PhuDeLoi(_t('Tinh chỉnh phụ đề không hợp lệ: {ly_do}')
                       .format(ly_do=_ly_do_ngan(exc))) from exc
    return dict(tho)


def _ly_do_ngan(exc) -> str:
    """Rut mot cau doc duoc tu `ValidationError`.

    ⚠️ Ban day du cua Pydantic in ca duong dan model, so loi va URL tai lieu —
       huu ich cho lap trinh vien, vo nghia voi khach.
    """
    loi = getattr(exc, "errors", None)
    if not callable(loi):
        return str(exc)[:120]
    ra = []
    for e in loi()[:3]:
        ten = ".".join(str(x) for x in e.get("loc") or ())
        ra.append(f"{ten} — {e.get('msg', '')}" if ten else str(e.get("msg")))
    return "; ".join(ra)


def cau_hinh_goc(kieu: str):
    """Cau hinh cua mot preset, chua ap tinh chinh."""
    from apps.autosubvideo.style_registry import get_config

    if kieu not in kieu_hop_le():
        raise PhuDeLoi(_t('Kiểu phụ đề không có trong danh sách.'))
    return get_config(kieu)


def chu_cua(ho_so: dict | None) -> str:
    """Nguon CHU cua mot ho so: `CHU_DICH` hay `CHU_NGUON`.

    🔑 Mot cho tra loi — ca COMPOSE (dung su kien) lan xem truoc (chon cau mau)
       deu hoi o day. `tu_dong` la BAN DICH vi Auto Scan luon long tieng: phu de
       khop voi loi khach dang NGHE. Loi goc thuong da nam tren hinh (hardsub)
       o chinh video nguon, nen lap lai no la che them hinh ma khong them y.
    """
    che_do = (ho_so or {}).get("che_do")
    if che_do == CHE_DO_NGUON:
        return CHU_NGUON
    if che_do in (CHE_DO_TU_CHON, CHE_DO_TAT):
        return str((ho_so or {}).get("chu") or CHU_DICH)
    return CHU_DICH


# ── Vi tri TU DONG: tranh dai phu de goc ────────────────────────────────────

#: Khoang ho giua phu de moi va dai phu de goc khi dat PHIA TREN no, theo phan
#: so chieu cao khung. 2% cua 576 = 12 px — vua mot net vien day.
KHOANG_HO_DAI = 0.02


def dai_phu_de_goc(vung) -> dict | None:
    """Dai phu de goc tu vung khach DANH DAU, hoac `None`.

    ⛔ **`danh_dau_phu_de` la mot tinh nang CO MA KHONG AI DOC truoc lan nay.**
       `vung_che.LOAI_DANH_DAU_PHU_DE` khai y nghia *"dung ve phu de dich chong
       len day"*, giao dien cho ve, ban dung luu — va khong mot dong nao doc
       `loai` do. `tu_dong` la nguoi doc dau tien.

    ⭐ `da_che=True`: `che_do_render._loc_lam_mo` lam mo MOI vung, ke ca vung
       danh dau (no khong loc theo `loai`). Nen dai da danh dau luon bi che, va
       phu de moi dat DE LEN no. Mot dai CHUA che (vd. hop OCR cua lan L-E) di
       nhanh `da_che=False` va phu de dat PHIA TREN.
    """
    from .vung_che import LOAI_DANH_DAU_PHU_DE

    ds = [v for v in (vung or ()) if v.get("loai") == LOAI_DANH_DAU_PHU_DE]
    if not ds:
        return None
    return {"y0": round(min(float(v["y0"]) for v in ds), 4),
            "y1": round(max(float(v["y1"]) for v in ds), 4),
            "da_che": True}


def dai_len_khung_ra(dai, *, buoc: dict, cao_nguon: int) -> dict | None:
    """Dai chu goc: phan so khung NGUON -> phan so khung RA. `None` = mat han.

    🔴 **Bug B8 (do 27/09).** `dai_phu_de_goc` la phan so khung NGUON (khach ve
       tren nguon), nhung `vi_tri_tu_dong` tinh `margin_v` voi chieu cao khung
       **RA**. Khi GD2 cat theo chieu DOC thi hai phan so ⛔ khong bang nhau:

         cat_khung nua TREN   margin_v 27  ·  dung phai  0   ·  lech +27 px
         cat_khung nua DUOI   margin_v 27  ·  dung phai 54   ·  lech -27 px

       ⭐ HAI cua so cat nguoc nhau cho CUNG mot so — bang chung rang phep tinh
          ⛔ khong he biet co cua so cat.

    ⭐ Ham nay lay GIAO cua dai voi khung ra, ⛔ khong "kep cho gan": mot dai bi
       cat MOT PHAN thi phan con lai VAN co chu goc, nen phu de moi van phai
       tranh no. Chi khi mat HAN thi ⛔ khong con gi de tranh.

    ⛔ Va khi mat han, tra `None` chu ⛔ khong tra mot dai o `0`: `vi_tri_tu_dong`
       doc `None` la *"giu vi tri cua preset"*, con mot dai o `0` se day chu len
       DINH khung — mot ban sua sai theo huong khac.
    """
    from . import hinh_hoc as _hh

    if not dai:
        return None
    y0 = _hh.doi_phan_so_doc(buoc, cao_nguon, float(dai["y0"]))
    y1 = _hh.doi_phan_so_doc(buoc, cao_nguon, float(dai["y1"]))
    if y0 is None and y1 is None:
        return None
    # ⭐ Mot bien bi cat: dai van giao khung ra, nen KEP bien do vao khung.
    #    `y0` mat ⇒ dai keo qua canh TREN; `y1` mat ⇒ keo qua canh DUOI.
    a = 0.0 if y0 is None else max(0.0, min(1.0, y0))
    b = 1.0 if y1 is None else max(0.0, min(1.0, y1))
    if b <= a:
        return None
    return {"y0": round(a, 4), "y1": round(b, 4), "da_che": bool(dai.get("da_che"))}


def doi_truc_dai_phu_de(ho_so: dict | None, *, bien_tap_gd2,
                        rong_nguon: int, cao_nguon: int) -> dict | None:
    """Ho so phu de voi `dai_phu_de_goc` DA doi sang truc khung RA. Tra ban MOI.

    ⛔ **⛔ Khong sua tai cho.** Cung mot `ho_so_pd` con di vao `van_tay` va vao
       bao cao; mot dai da doi truc lot vao do se lam hai lan chay giong nhau co
       hai van tay, hay te hon: mot bao cao noi mot con so ma ⛔ khong ai biet no
       o truc nao.

    ⭐ ⛔ Khong hinh hoc GD2 ⇒ tra **chinh** doi tuong cu: mot phep bien doi vo
       dieu kien la mot cho de lam tron va de sai them, tren duong ma phan lon
       lan chay di qua.
    """
    from . import bien_tap as _bt, hinh_hoc as _hh

    dai = (ho_so or {}).get("dai_phu_de_goc")
    if not ho_so or not dai:
        return ho_so
    if not (bien_tap_gd2 and set(bien_tap_gd2) & set(_bt.TRUONG_HINH_HOC)):
        return ho_so
    buoc = _hh.khung_bien_tap(int(rong_nguon), int(cao_nguon), bien_tap_gd2)
    moi = dai_len_khung_ra(dai, buoc=buoc, cao_nguon=int(cao_nguon))
    ra = dict(ho_so)
    if moi is None:
        # ⭐ Dai bi cat MAT HAN ⇒ ⛔ khong con chu goc nao de tranh. Bo khoa di
        #    thi `vi_tri_tu_dong` giu vi tri cua preset — dung hanh vi.
        ra.pop("dai_phu_de_goc", None)
    else:
        ra["dai_phu_de_goc"] = moi
    return ra


def vi_tri_tu_dong(ho_so: dict | None, *, cao: int) -> dict:
    """Ghi de vi tri cua che do `tu_dong`. `{}` = giu vi tri cua preset.

    Hai nhanh, mot luat: **khong de chu moi len chu cu con doc duoc.**
      · dai DA che  -> day chu moi trung day dai: chu moi phu len vet mo
      · dai CHUA che -> day chu moi o tren dinh dai + `KHOANG_HO_DAI`

    ⚠️ `margin_v` tinh bang pixel cua PlayRes (= khung that, xem
       `viet_tep_ass`), nen can `cao`. `safe_area_percent` ve 0: `ass_builder`
       lay `max(margin_v, safe)` va se day chu khoi dai ma khong bao.
    """
    if not ho_so or ho_so.get("che_do") != CHE_DO_TU_DONG or cao <= 0:
        return {}
    dai = ho_so.get("dai_phu_de_goc") or None
    if not dai:
        return {}
    if dai.get("da_che"):
        mv = (1.0 - float(dai["y1"])) * cao
    else:
        mv = (1.0 - float(dai["y0"]) + KHOANG_HO_DAI) * cao
    return {"alignment": 2, "margin_v": max(0, int(round(mv))),
            "safe_area_percent": 0}


def nhan_manh(ho_so: dict | None) -> tuple[str, str]:
    """Che do + mau NHAN MANH cuoi cung. Tra `(che_do, mau)`.

    🔴 **Ham nay ton tai vi mot false feature co that, do duoc.**

       `style_registry` giu che do nhan manh o **HAI** cho, va chung khong bang
       nhau: `FullStylePreset.highlight_mode` (cap preset) va
       `SubtitleStyleConfig.highlight_mode` (cap cau hinh). Do ngay 11/09: **7
       trong 9** preset khai o cap preset (`word`, `bg_flash`, `all_text`), va
       ca chin preset co `config.highlight_mode == "none"`.

    ⛔ Nen doc `config.highlight_mode` — cach tu nhien nhat, vi moi truong khac
       deu o do — se lam MOI preset render khong nhan manh gi. Kieu ten
       `word_emphasis` se khong nhan manh mot tu nao. Khong loi nao bao, va tep
       `.ass` van hop le: dung hinh dang **tinh nang khong ton tai**.

    ⭐ `build_ass` nhan hai gia tri nay qua THAM SO chu khong doc tu `style`,
       nen day la cho duy nhat quyet dinh chung.

    Thu tu: tinh chinh cua khach > cap preset > cap cau hinh.
    """
    kieu_id = str((ho_so or {}).get("kieu") or KIEU_MAC_DINH)
    tinh = (ho_so or {}).get("tinh_chinh") or {}

    che_do, mau = "none", "#FFD700"
    for p in _kieu_de_hien():
        if p.id == kieu_id:
            che_do = str(p.highlight_mode or p.config.highlight_mode or "none")
            mau = str(p.highlight_color or p.config.highlight_color or mau)
            break
    return (str(tinh.get("highlight_mode") or che_do),
            str(tinh.get("highlight_color") or mau))


def cau_hinh_kieu(ho_so: dict | None, *, cao: int = 0):
    """Cau hinh CUOI CUNG: preset + vi tri tu dong + tinh chinh cua khach.

    🔑 Mot cho tinh, va ca xem truoc lan trinh render deu goi no (qua
       `viet_tep_ass`). Pha 07 da tra gia cho bai hoc nguoc lai: muoi cho doc
       `run.settings`, hai cho lech nhau ve mot mac dinh, va mot lan chay
       **chay** o che do nay trong khi **bang chung QC ghi** che do kia.

    Thu tu: preset < vi tri tu dong < tinh chinh cua khach (khach chinh tay
    `alignment`/`margin_v` thi tay khach thang).

    ⚠️ Vi tri tu dong ap bang `model_copy`, KHONG qua duyet: `margin_v` cua mo
       hinh chan o 200 (mot tran cho o nhap cua khach), trong khi dai phu de
       goc o 0,76 tren khung 1080 can 259. Gia tri nay do he thong tinh tu hinh
       hoc, khong phai khach go.
    """
    kieu = str((ho_so or {}).get("kieu") or KIEU_MAC_DINH)
    goc = cau_hinh_goc(kieu)
    tinh = (ho_so or {}).get("tinh_chinh") or {}
    cfg = _mo_hinh_kieu()(**{**goc.model_dump(), **tinh}) if tinh else goc
    vt = {k: v for k, v in vi_tri_tu_dong(ho_so, cao=cao).items()
          if k not in tinh}
    return cfg.model_copy(update=vt) if vt else cfg


def luoc_do_tinh_chinh() -> list[dict]:
    """Luoc do tung truong mo — DOC TU MO HINH, khong go tay.

    ⛔ Mot ban sao cua mien gia tri trong template la mot ban sao se troi: giao
       dien cho keo toi 200 trong khi may chu tu choi o 120, va khach chi biet
       sau khi bam Gui. Cung ly do `lop_phu_chu_toi_da` phai lay tu module.
    """
    from typing import Literal, get_args, get_origin

    mh = _mo_hinh_kieu()
    ra = []
    for ten in TRUONG_MO:
        f = mh.model_fields[ten]
        muc: dict = {"ten": ten, "mac_dinh": f.default,
                     "mo_ta": f.description or ""}
        kieu_py = f.annotation
        if kieu_py is bool:
            muc["dang"] = "co_khong"
        elif get_origin(kieu_py) is Literal:
            muc["dang"] = "chon"
            muc["chon"] = list(get_args(kieu_py))
        elif isinstance(f.default, str) and f.default.startswith("#"):
            muc["dang"] = "mau"
        elif kieu_py in (int, float):
            muc["dang"] = "so"
            for m in f.metadata:
                if hasattr(m, "ge"):
                    muc["nho_nhat"] = m.ge
                if hasattr(m, "le"):
                    muc["lon_nhat"] = m.le
        else:
            muc["dang"] = "chu"
            # `highlight_mode` khai mien bang `pattern`, khong bang `Literal`.
            for m in f.metadata:
                mau = getattr(m, "pattern", "")
                if mau and mau.startswith("^(") and mau.endswith(")$"):
                    muc["dang"] = "chon"
                    muc["chon"] = mau[2:-2].split("|")
        ra.append(muc)
    return ra


# ── Chuan hoa ────────────────────────────────────────────────────────────────

def chuan_hoa(tho) -> dict | None:
    """Yeu cau tho -> ho so chuan, hoac `None` khi TAT HAN (ca hai truc).

    ⭐ Tra `None` chu khong phai `{"che_do": "tat"}`: cung luat voi
       `cat_dau_cuoi` L4 — *khong thu hep gi thi khong ghi khoa nao*. Mot ho so
       mang `che_do: tat` o **moi** lan chay lam van tay cua nhung lan khong
       dung phu de khac di ma khong vi ly do gi.
    """
    if not tho:
        return None
    if not isinstance(tho, dict):
        raise PhuDeLoi(_t('Yêu cầu phụ đề không đọc được.'))

    che_do = str(tho.get("che_do") or CHE_DO_MAC_DINH)
    if che_do not in CHE_DO:
        raise PhuDeLoi(_t('Chế độ phụ đề không hợp lệ.'))

    xuat_srt = bool(tho.get("xuat_srt"))
    dot = che_do != CHE_DO_TAT
    if not dot and not xuat_srt:
        return None

    ra: dict = {"che_do": che_do, "xuat_srt": xuat_srt}

    # ⭐ `phan_doan` can cho CA HAI truc: no quyet dinh ranh gioi tung dong, va
    #    mot tep `.srt` cung co dong.
    phan_doan = str(tho.get("phan_doan") or PHAN_DOAN_MAC_DINH)
    if phan_doan not in phan_doan_hop_le():
        raise PhuDeLoi(_t('Cách chia dòng phụ đề không hợp lệ.'))
    ra["phan_doan"] = phan_doan

    # ⭐ `chu` chi o `tu_chon` va `tat` (tep `.srt` rieng cung co nguon chu):
    #    ba che do con lai da CO DINH nguon chu (xem `chu_cua`). Nhan no o do
    #    la nhan mot yeu cau mau thuan — `nguon` ma chu = dich — roi lang le
    #    chon mot ben.
    chu = tho.get("chu")
    if chu not in (None, ""):
        if che_do not in (CHE_DO_TU_CHON, CHE_DO_TAT):
            raise PhuDeLoi(_t('Chế độ này đã cố định nguồn chữ; chỉ “tự chọn '
                              'kiểu” mới chọn được lời gốc hay bản dịch.'))
        if chu not in CHU:
            raise PhuDeLoi(_t('Nguồn chữ phụ đề không hợp lệ.'))
        # Giu THUA: `dich` la mac dinh, khong ghi.
        if chu != CHU_DICH:
            ra["chu"] = chu

    # ⛔ `kieu` CHI co nghia khi dot: `.srt` khong mang kieu chu nao. Ghi no vao
    #    mot ho so chi-xuat-SRT la ghi mot truong khong ai doc — va no lam hai
    #    lan chay giong het nhau co hai van tay khac nhau.
    if dot:
        kieu = str(tho.get("kieu") or KIEU_MAC_DINH)
        if kieu not in kieu_hop_le():
            raise PhuDeLoi(_t('Kiểu phụ đề không có trong danh sách.'))
        ra["kieu"] = kieu
        # ⭐ V6 pha 16. Giu THUA cung mot ly do voi `kieu`: mot ho so mang 27
        #    truong o moi lan chay se doi ngay khi app chu doi mot mac dinh —
        #    tuc van tay doi trong khi cau hinh thi khong.
        tinh = chuan_hoa_tinh_chinh(tho.get("tinh_chinh"), kieu=kieu)
        if tinh:
            ra["tinh_chinh"] = tinh

    return ra


def co_dot_vao_hinh(ho_so: dict | None) -> bool:
    """Ho so nay co doi diem anh khong.

    🔑 Cau hoi rieng, vi `xuat_srt` khong doi diem anh. Mot ho so chi xuat SRT
       chay duoc o preset giu hinh; mot ho so dot phu de thi khong — cung rang
       buoc VAT LY voi `vung_che`, `lop_phu`, `logo`.
    """
    # ⚠️ `return bool(ho_so) and ho_so.get(...)` chay dung nhung mypy khong
    #    thu hep kieu qua `bool()`, nen no van thay `None` o ve phai. Viet ro
    #    hai nhanh thi ca nguoi doc lan may deu khong phai suy.
    if not ho_so:
        return False
    return ho_so.get("che_do") in CHE_DO_DOT


def _kieu_de_hien() -> list:
    """Preset kieu, kem nhan va mo ta. CHI cho giao dien.

    ⚠️ Tach khoi `kieu_hop_le()` co chu dich: ham kia chay o MOI request de
       duyet mot id va chi can mot danh sach chuoi; ham nay chay khi mo trang va
       can `label` + `description`. Ca hai deu doc `_PRESETS` nen khong lech.
    """
    from apps.autosubvideo.style_registry import list_presets

    return list(list_presets())


def cho_giao_dien() -> dict:
    """Moi thu giao dien can de dung o phu de. MOT khoa ngu canh, khong sau.

    ⛔ **Khong go danh sach kieu vao template.** `style_registry` la chu so huu,
       va mot ban sao trong HTML se troi ngay lan dau app kia them mot kieu —
       troi IM LANG, vi khong phep kiem nao doi chieu HTML voi mot dict Python.
       Cung ly do `preset_can_cho_vung` lay tu hop dong chu khong go chuoi.

    ⚠️ **Ham nay goi vao app khac, nen no chay MOT lan moi lan mo trang.**
       `list_ids()` doc mot dict da nap san — khong cham dia, khong cham mang.
    """
    return {
        # ⭐ `(ma, ten, mo_ta)` — dung khuon `gia.CHE_DO_GIONG_BANG`, va vi cung
        #    ly do: neu template phai viet `{% if ma == "tu_dong" %}` de biet
        #    nhan nao di voi ma nao thi ba chuoi ma da bi go tay vao HTML.
        #    Nhan de TRAN o day, `_()` trong template dich — y het khoi kia.
        # ⚠️ `N_()` — danh dau de TRICH, khong dich ngay. Dich xay ra o template
        #    (`{{ _(ten) }}`), y het `gia._giong_bang()`. Boc `_t()` o day se
        #    dich luc **import module**, tuc chot cung ngon ngu cua nguoi khoi
        #    dong may chu cho moi khach ve sau.
        "che_do": [
            (CHE_DO_TAT, N_('Không khắc lên hình'),
             N_('Video giữ nguyên. Bạn vẫn có thể xuất tệp phụ đề rời.')),
            (CHE_DO_TU_DONG, N_('Tự động — bản dịch, tránh phụ đề gốc'),
             N_('Khắc bản dịch (đúng lời thuyết minh) và tự đặt đè lên dải '
                'phụ đề gốc bạn đã đánh dấu.')),
            (CHE_DO_NGUON, N_('Lời gốc'),
             N_('Khắc lời gốc của video, kiểu chữ chuẩn.')),
            (CHE_DO_DICH, N_('Bản dịch'),
             N_('Khắc bản dịch, kiểu chữ chuẩn.')),
            (CHE_DO_TU_CHON, N_('Khắc lên hình — tự chọn kiểu'),
             N_('Bạn chọn kiểu chữ, tinh chỉnh, và chọn lời gốc hay bản dịch.')),
        ],
        "che_do_mac_dinh": CHE_DO_MAC_DINH,
        "che_do_can_kieu": CHE_DO_TU_CHON,
        "che_do_tu_dong": CHE_DO_TU_DONG,
        # ⭐ Nguon chu — chi hien o `tu_chon` (xem `chuan_hoa`).
        "chu": [(CHU_DICH, N_('Bản dịch')), (CHU_NGUON, N_('Lời gốc'))],
        # ⛔ **Nhan, khong phai id.** `tiktok_bold` la mot dinh danh cho MA
        #    doc; dua no ra man hinh la bat khach doc dinh danh. `style_registry`
        #    da co san `label` va `description` — dung chung.
        #
        # ⚠️ Nhan de NGUYEN, khong boc `_t()`: chung den tu app khac va khong
        #    nam trong so dich cua ta. Boc chung se sinh nhung msgid khong bao
        #    gio duoc dich, va `i18n.py` se dem chung nhu no dich thieu.
        "kieu": [(p.id, p.label, p.description)
                 for p in _kieu_de_hien()],
        "kieu_mac_dinh": KIEU_MAC_DINH,
        # ⭐ V6 pha 16. Luoc do doc TU mo hinh cua app chu, nen mien gia tri o
        #    giao dien va mien may chu duyet la **cung mot con so**.
        "tinh_chinh": luoc_do_tinh_chinh(),
        # 🔑 **Gia tri KHOI DIEM cua tung preset, khong phai mac dinh cua mo
        #    hinh.** Hai thu nay khac nhau: mo hinh mac dinh `font_size=48`,
        #    nhung `tiktok_bold` khoi diem o mot con so khac. Neu giao dien hien
        #    mac dinh cua MO HINH thi khach chon `tiktok_bold` se thay mot bang
        #    so khong phai cua kieu ho vua chon — va moi o ho cham vao deu tro
        #    thanh mot "tinh chinh" du ho khong doi y gi.
        #
        # ⭐ Va do la thu cho phep gui THUA: giao dien so voi bang nay de biet
        #    khach that su doi gi.
        "kieu_cau_hinh": {
            p.id: {t: getattr(p.config, t) for t in TRUONG_MO}
            for p in _kieu_de_hien()
        },
    }


def tu_form(tho: str, *, preset: str) -> dict | None:
    """Chuoi JSON tu form -> ho so chuan, da doi chieu preset. Nem `PhuDeLoi`.

    🔑 **Cua HTTP, nhung khong nam o `routes.py`.** Route chi con mot loi goi.
       Hop dong app noi ro route khong phai cho chua nghiep vu, va tep do dang o
       880/900 dong — mot tang doc + duyet + doi chieu nua se day no qua tran.

    ⭐ **Tang thu nhat trong ba tang**, y het `vung`/`lop_phu`/`logo`: chan o
       CUA, truoc khi giu credit. Mot lan chay bi chan o `ban_dung.kiem` la mot
       lan chay da di qua chin giai doan.

    ⛔ **Va day la cho de nham nhat cua ca pha.** Cach doc tu nhien la *"preset
       giu hinh thi tu choi phu de"* — nhu ta lam voi ba tinh nang kia. Sai:
       chi truc DOT bi cam. Mot yeu cau chi `.srt` khong cham diem anh nao, va
       tu choi no la khoa mat lua chon phu de DUY NHAT con lai o preset do.
    """
    import json

    from .hop_dong_v4 import PRESET_GIU_HINH

    tho = (tho or "").strip()
    if not tho:
        return None
    # 🔴 **Hai buoc, khong mot buoc.** `PhuDeLoi` KE THUA `ValueError`, nen mot
    #    `except (ValueError, TypeError)` bao quanh ca hai se nuot chinh cau tra
    #    loi cu the cua `chuan_hoa` roi boc lai thanh mot cau chung chung —
    #    khach go sai mot id kieu chu se doc *"khong doc duoc"* va khong biet
    #    minh vua lam gi sai. Do dung la hang loi ma `lop_phu` da tu choi.
    try:
        goi = json.loads(tho)
    except (ValueError, TypeError) as exc:
        raise PhuDeLoi(_t('Yêu cầu phụ đề không đọc được.')) from exc
    ho_so = chuan_hoa(goi)
    if not ho_so:
        return None

    if co_dot_vao_hinh(ho_so) and preset == PRESET_GIU_HINH:
        raise PhuDeLoi(_t(
            'Kiểu “Giữ nguyên hình ảnh” sao chép nguyên vẹn từng điểm ảnh, nên '
            'không thể khắc phụ đề lên hình. Bỏ chọn “khắc vào hình” để vẫn '
            'nhận tệp phụ đề rời, hoặc chọn “Rút gọn có biên tập”.'))
    return ho_so


def ha_ve_srt(ho_so: dict | None) -> dict | None:
    """Bo truc DOT, giu truc SRT. Dung o preset giu hinh.

    🔑 **Ham nay ton tai vi hai truc, va no la ly do thuc te de tach chung.**
       `vung`/`lop_phu`/`logo` o preset giu hinh chi co mot cau tra loi: bo. Phu
       de co HAI — bo phan dot, nhung `.srt` thi van giao duoc, va do la lua
       chon phu de duy nhat con lai o do.

    ⛔ Neu gop hai truc lam mot co, ham nay se phai tra `None` cho ca hai — va
       khach chon preset giu hinh se **khong bao gio** lay duoc phu de, khong
       mot loi nao noi vi sao.

    ⚠️ Bo luon `kieu`: mot `.srt` khong mang kieu chu nao. Giu lai la giu mot
       truong khong ai doc, va no lam hai lan chay giong het nhau co hai van
       tay khac nhau — cung lo ma `chuan_hoa` da bit.
    """
    if not ho_so:
        return None
    if not co_dot_vao_hinh(ho_so):
        return dict(ho_so)
    if not ho_so.get("xuat_srt"):
        return None
    # ⚠️ Giu NGUON CHU: ha `nguon` ve `tat` ma quen `chu` se giao mot `.srt`
    #    BAN DICH cho nguoi da chon loi goc — dung chu, sai thu tieng.
    chu = chu_cua(ho_so)
    ra = {k: v for k, v in ho_so.items()
          if k not in ("kieu", "tinh_chinh", "chu", "dai_phu_de_goc")}
    ra["che_do"] = CHE_DO_TAT
    if chu != CHU_DICH:
        ra["chu"] = chu
    return ra


# ── Cau noi: KE HOACH (truc RA) -> su kien phu de ────────────────────────────

#: Toi da hai dong moi su kien. Ba dong tren mot khung 16:9 che mat qua nhieu
#: hinh, va `ass_builder` khong tu gioi han.
SO_DONG_TOI_DA = 2

#: Toi da bao nhieu ky tu mot dong truoc khi xuong dong.
KY_TU_MOI_DONG = 42


def _ngat_dong(chu: str) -> tuple[str, int]:
    """Chia mot cau thanh toi da `SO_DONG_TOI_DA` dong. Tra (van, so_dong).

    🔑 **Ngat dong la cua `autosubvideo.segmenter.wrap_lines`, khong viet o
       day.** Ban tu viet cu chi ngat theo dau cach — mot cau tieng Trung (che
       do `nguon`) ra MOT dong dai vo han. Sua o app chu thi AutoSub huong luon.

    ⚠️ Van ngat theo TU voi chu co dau cach: cat giua mot tu tieng Viet co dau
       cho ra hai manh khong doc duoc.
    """
    from apps.autosubvideo.segmenter import wrap_lines

    s = " ".join(str(chu or "").split())
    if not s:
        return "", 0
    dong = wrap_lines(s, KY_TU_MOI_DONG, SO_DONG_TOI_DA)
    return "\\N".join(dong), len(dong)


def su_kien_tu_ke_hoach(ke_hoach: dict, van_ban: dict, *,
                        chu: str = CHU_DICH) -> list:
    """`ke_hoach` + van ban da xu ly -> `SubtitleEvent` tren TRUC RA.

    ⛔ **`van_ban` la tai lieu `CONTENT_PROCESS`, KHONG phai ban ke tieng.**
       Ban ke tieng cua `giai_doan_giong` la `{ma, khoa, giay}` — no tro toi tep
       WAV, no khong mang mot chu nao. Chinh `giai_doan_giong` cung phai doc tai
       lieu nay (`_doc_ban_dich`) de co `m["chu"]` ma doc thanh tieng.

    ⚠️ **Hai tai lieu dung hai khoa khac nhau, va do khong phai loi danh may.**
       Ke hoach dung `doan` (`thoi_gian.py`), van ban dung `muc` (`van_ban.py`).
       Ban dau tien cua ham nay doc **nguoc ca hai** — va no van xanh, vi phep
       kiem dung mot dict do chinh toi bia ra khop voi gia dinh cua chinh toi.

    🔑 **Day la cho quyet dinh ca pha, va no chi doc chu khong tinh.**
       `ke_hoach["muc"][i]["dat_tai_ms"]` DA nam tren truc ban ra — no di qua
       `ban_do.ra()` trong `thoi_gian.lap_ke_hoach`. Nen ham nay **khong** anh
       xa gi; anh xa da co chu so huu la `ban_do_thoi_gian`.

    ⛔ Dung `content.json` / `ban_ghi` o day se cho phu de troi **dung nhu tieng
       da troi truoc pha 16**, va troi AM THAM: chu van chay, chi lech cau.

    ⚠️ Bo qua muc khong co chu: mot doan chua dich xong khong duoc thanh mot o
       phu de rong nhap nhay tren man hinh.

    ⭐ `chu` chon KHOA cua muc: `dich` -> `chu` (ban dich), `nguon` -> `goc`
       (loi cua ban ghi chuan). Ca hai nam trong CUNG muc, cung `ma`, nen phu de
       loi goc dung dung moc cua ban dich — khong co truc thoi gian thu hai.
    """
    from apps.autosubvideo.segmenter import SubtitleEvent

    if chu not in _KHOA_CHU:
        raise PhuDeLoi(_t('Nguồn chữ phụ đề không hợp lệ.'))
    khoa = _KHOA_CHU[chu]
    chu_theo_ma: dict[str, str] = {}
    for d in (van_ban or {}).get("muc") or []:
        ma = str(d.get("ma") or "")
        if ma:
            chu_theo_ma[ma] = str(d.get(khoa) or "")

    ra = []
    for i, m in enumerate((ke_hoach or {}).get("doan") or []):
        cau = chu_theo_ma.get(str(m.get("ma") or ""), "").strip()
        if not cau:
            continue
        bat = float(m.get("dat_tai_ms") or 0) / 1000.0
        dai = float(m.get("dai_ms") or 0) / 1000.0
        if dai <= 0:
            continue
        hien, so_dong = _ngat_dong(cau)
        ra.append(SubtitleEvent(start=bat, end=bat + dai, text=cau,
                                display_text=hien, line_count=so_dong,
                                scene_id=str(m.get("ma") or ""), index=i))
    return ra

# ── Su kien <-> goi JSON: ban dung mang QUYET DINH, ket xuat chi thi hanh ────
#
# 🔑 **Vi sao su kien phai nam TRONG ban dung.**
#
#    COMPOSE va RENDER la HAI job. COMPOSE doc ke hoach + van ban da dich;
#    RENDER **khong doc ca hai** — no chi mo mot tep: ban dung. Neu su kien
#    khong nam trong ban dung thi RENDER phai di doc lai hai artifact cua giai
#    doan khac, tuc mo mot duong phu thuoc thu hai cho cung mot du lieu.
#
# ⭐ Va do la dung khuon ma `lop_phu` da dung: chu cua khach nam trong ban dung,
#    con `viet_tep_chu()` chi doi no thanh tep o thu muc tam cua lan render.
#    `.ass` di duong y het — xem `viet_tep_ass` o duoi.
#
# ⚠️ Dong tren truc RA da duoc chot o COMPOSE. RENDER khong duoc phep tinh lai
#    moc: tinh lai la mo duong cho hai cau tra loi khac nhau cho cung mot cau
#    hoi, va lan nay hai cau tra loi deu **trong nhu dung**.

def su_kien_ra_goi(ds) -> list[dict]:
    """`SubtitleEvent` -> dict JSON hoa duoc, dung `to_dict()` cua chinh no."""
    return [e.to_dict() for e in (ds or ())]


def goi_ra_su_kien(goi) -> list:
    """dict -> `SubtitleEvent`. Nguoc cua `su_kien_ra_goi`."""
    from apps.autosubvideo.segmenter import SubtitleEvent

    ra = []
    for g in (goi or ()):
        ra.append(SubtitleEvent(
            start=float(g.get("start") or 0.0), end=float(g.get("end") or 0.0),
            text=str(g.get("text") or ""),
            display_text=str(g.get("display_text") or g.get("text") or ""),
            line_count=int(g.get("line_count") or 1),
            scene_id=str(g.get("scene_id") or ""),
            index=int(g.get("index") or 0)))
    return ra


# ── Sinh tep o thu muc TAM cua lan render ───────────────────────────────────

TEN_TEP_ASS = "phu_de.ass"
TEN_TEP_SRT = "phu_de.srt"


def viet_tep_ass(ho_so, goi_su_kien, thu_muc, *,
                 rong: int = 0, cao: int = 0) -> str:
    """Viet `.ass` vao `thu_muc`. Tra duong dan, hoac `""` khi khong phai dot.

    ⛔ **Khong goi `burn.burn()`.** Do la cach doc tu nhien nhat cua *"tai dung
       app kia"* va la cach SAI: `burn()` chay mot luot ffmpeg DAY DU cua rieng
       no, tuc video bi ma hoa lai hai lan. Ta chi muon tang TAC GIA cua no.

    ⚠️ **Kich thuoc khung la BAT BUOC ve mat noi dung, khong phai tuy chon.**
       `build_ass` dung `video_width/height` de tinh co chu va le — mac dinh cua
       no la 1920x1080. Mot video doc 1080x1920 dung mac dinh do se co phu de
       nho bang mot phan ba va dat sai le, **khong bao mot loi nao**. Nen o day
       roi ve mac dinh cua `build_ass` chi khi ta that su khong biet khung.
    """
    if not co_dot_vao_hinh(ho_so):
        return ""
    su_kien = goi_ra_su_kien(goi_su_kien)
    if not su_kien:
        # ⭐ Khong su kien thi khong tep. Mot `.ass` rong van la mot `ass=` hop
        #    le trong chuoi loc — no chay, no khong che gi, va no ton mot vong
        #    giai ma. Tra `""` de `ket_xuat` bo han mat xich do.
        return ""

    from apps.autosubvideo.ass_builder import build_ass

    # 🔴 `cau_hinh_kieu` goi `cau_hinh_goc`, va ham do NEM khi id la thay vi roi
    #    ve `default` nhu `get_config`. Chan o day mot lan nua chu khong tin
    #    `chuan_hoa`: hai duong goi khac nhau, va duong nay chay khi `chuan_hoa`
    #    da lui ve qua khu tu lau (ban dung cu).
    # ⚠️ Truyen HAI tham so ro rang thay vi do mot `**dict`: `build_ass` co
    #    tham so vi tri o dau, nen mypy khop `**dict[str, int]` vao tham so thu
    #    tam (`title: str`) va bao sai kieu. Mot `**dict` cung giau di viec tham
    #    so nao that su duoc truyen.
    rong_ass = int(rong) if rong > 0 and cao > 0 else 1920
    cao_ass = int(cao) if rong > 0 and cao > 0 else 1080
    # ⭐ `cao` di vao cau hinh: vi tri tu dong tinh `margin_v` bang pixel cua
    #    PlayRes, va PlayRes chinh la `cao_ass`.
    kieu = cau_hinh_kieu(ho_so, cao=cao_ass)
    # ⭐ `build_ass` nhan che do nhan manh qua THAM SO, khong doc tu `style` —
    #    nen phai chuyen tay. Doc tu chinh cau hinh cuoi cung de mot tinh chinh
    #    `highlight_mode` co tac dung that, khong chi nam trong ho so.
    nm_che_do, nm_mau = nhan_manh(ho_so)
    return build_ass(su_kien, kieu, str(Path(thu_muc) / TEN_TEP_ASS),
                     highlight_mode=nm_che_do,
                     highlight_color=nm_mau,
                     keyword_highlights=list(kieu.keyword_highlights or ()),
                     keyword_highlight_color=kieu.keyword_highlight_color,
                     video_width=rong_ass, video_height=cao_ass)


def viet_tep_srt(ho_so, goi_su_kien, thu_muc) -> str:
    """Viet `.srt` vao `thu_muc`. Tra duong dan, hoac `""` khi khong xin SRT.

    🔑 Truc DOC LAP voi `viet_tep_ass`: mot ho so co the xin ca hai, hoac chi
       mot. Va `.srt` la lua chon phu de DUY NHAT con lai o preset giu hinh —
       no khong cham mot diem anh nao.
    """
    if not (ho_so or {}).get("xuat_srt"):
        return ""
    su_kien = goi_ra_su_kien(goi_su_kien)
    if not su_kien:
        return ""

    from apps.autosubvideo.ass_builder import build_srt

    return build_srt(su_kien, str(Path(thu_muc) / TEN_TEP_SRT))


# ── Chot o COMPOSE: vi tri tu dong + su kien + glyph ───────────────────────

#: Font he thong ma libass tim toi khi font cua kieu thieu glyph (do 22/09 tren
#: may A: `Montserrat`/`Anton`/`Oswald` KHONG cai, chu Han va tieng Viet van ra
#: dung — libass tu lui qua DirectWrite). Danh sach nay la phia BAO THU cua
#: phep kiem: mot ky tu khong font nao o day ve duoc thi rat co the ra o vuong.
FONT_DU_PHONG_GLYPH: tuple[str, ...] = ("Arial", "Microsoft YaHei", "SimSun")

#: Ho font chung cua CSS/fontconfig — `matplotlib` phan giai chung ra DejaVu
#: cua CHINH NO, khong phai font libass dung. Hoi chung la hoi sai may.
_HO_CHUNG = {"sans-serif", "serif", "cursive", "monospace", "fantasy"}


def glyph_thieu(ho_so: dict | None, goi_su_kien) -> str | None:
    """Ky tu cua phu de ma KHONG font nao (kieu -> du phong) ve duoc.

    `""` = du glyph · chuoi = ky tu thieu · `None` = khong phan giai duoc font
    nao tren may nay (khong biet — khong phai "du").

    ⛔ `font_checker.is_font_available` tra loi *"co font ten do khong"*, khong
       tra loi *"font do ve duoc chu Han khong"*: Arial co mat moi may Windows
       va khong co mot glyph Han nao. Nen hoi `missing_glyphs` (mo rong o app
       chu), tung font mot, chi mang theo phan con thieu.
    """
    from apps.autosubvideo.font_checker import missing_glyphs

    tat_ca = "".join(str(g.get("text") or "") for g in (goi_su_kien or ()))
    if not tat_ca.strip():
        return ""
    con: str = tat_ca
    cfg = cau_hinh_kieu(ho_so)
    ten = [cfg.font_family, *str(cfg.font_fallback or "").split(","),
           *FONT_DU_PHONG_GLYPH]
    da_hoi: set[str] = set()
    biet = False
    for f in (t.strip() for t in ten):
        if not f or f.lower() in _HO_CHUNG or f.lower() in da_hoi:
            continue
        da_hoi.add(f.lower())
        m = missing_glyphs(f, con)
        if m is None:
            continue
        biet, con = True, m
        if not con:
            return ""
    return con if biet else None


def chot_o_compose(ho_so: dict, *, ke_hoach: dict, van_ban: dict,
                   vung=()) -> dict:
    """Hoan tat ho so o COMPOSE: dai phu de goc, su kien, glyph. Tra CHINH NO.

    🔑 Moi quyet dinh ve NOI DUNG phu de chot o day, mot lan, va di theo ban
       dung. RENDER va XEM TRUOC chi doc ho so nay qua `viet_tep_ass`.
    """
    import logging

    if ho_so.get("che_do") == CHE_DO_TU_DONG:
        dai = dai_phu_de_goc(vung)
        if dai:
            ho_so["dai_phu_de_goc"] = dai
    ho_so["su_kien"] = su_kien_ra_goi(
        su_kien_tu_ke_hoach(ke_hoach, van_ban, chu=chu_cua(ho_so)))
    if co_dot_vao_hinh(ho_so):
        thieu = glyph_thieu(ho_so, ho_so["su_kien"])
        if thieu:
            # ⚠️ Ghi lai, KHONG chan: libass con lui qua DirectWrite rong hon
            #    danh sach bao thu o tren. Ho so mang no thi QC va nguoi doc
            #    ban dung thay duoc.
            ho_so["glyph_thieu"] = thieu[:64]
            logging.getLogger(__name__).warning(
                "phu de: %d ky tu khong font nao ve duoc", len(thieu))
    return ho_so


# ── XEM TRUOC: cung ho so, cung `.ass`, cung chuoi loc voi ban render ──────
#
# 🔴 **Mot xem truoc chi dang tin khi no KHONG THE lech ban render.** Nen o day
#    khong co mot dong dung phu de nao cua rieng no:
#
#      ho so    <- `tu_form`             (CHINH cua nop that)
#      .ass     <- `viet_tep_ass`        (CHINH ham RENDER goi)
#      chuoi loc<- `che_do_render.loc_cat_noi` (CHINH chuoi `ket_xuat` dung,
#                   ca vung che lan `ass=`)
#
#    Khac biet DUY NHAT la dau vao (mot khung hinh thay vi video) va cau mau
#    thay vi ban dich that. Bang chung do tung diem anh: L_PHU_DE.md §4.

#: Khung xem truoc lay o giay thu may TRONG su kien. Qua hieu ung vao
#: (`animation_ms` toi da 1000 nhung 9/9 preset <= 300) de khach thay trang thai
#: DUNG YEN cua chu, khong phai khung dau cua `fade`.
XEM_TRUOC_GIAY = 1.0
XEM_TRUOC_DAI_SU_KIEN = 4.0
XEM_TRUOC_TRAN_BYTE = 8 * 1024 * 1024
XEM_TRUOC_CANH_TOI_DA = 3840

#: Cau mau theo NGON NGU (khong phai theo che do): che do chon nguon chu, nguon
#: chu + cap ngon ngu chon cau. Dai du hai dong de khach thay cach ngat dong.
CAU_MAU = {
    "zh": "从屠宰场运送过来的牛肠还带着温热，清洗牛肠才是最关键的一步",
    "en": "The tripe arrives from the slaughterhouse still warm, "
          "and cleaning it is the most important step",
    "vi": "Lòng bò chở từ lò mổ về vẫn còn ấm, và rửa sạch "
          "mới là bước quan trọng nhất",
}


def cau_mau(ho_so: dict | None, *, nguon: str = "", dich: str = "") -> str:
    """Cau mau cho xem truoc. Nguon `auto`/rong -> `zh` (video nghiem thu)."""
    from . import ngon_ngu as nn

    if chu_cua(ho_so) == CHU_NGUON:
        ma = nn.chuan_nguon(nguon)
        return CAU_MAU.get(ma, CAU_MAU[nn.ZH])
    return CAU_MAU.get(nn.chuan_dich(dich), CAU_MAU[nn.DICH_MAC_DINH])


#: Dinh dang diem anh cua video DUA VAO render (h264 nguon cua khach). Xem
#: truoc doi khung anh sang dung dinh dang nay TRUOC chuoi loc.
DINH_DANG_VAO = "yuv420p"


def lenh_xem_truoc(*, ffmpeg: str, anh: str, duong_ass: str, vung,
                   duong_tam: str, duong_ra: str,
                   rong: int = 0, cao: int = 0) -> list[list[str]]:
    """HAI lenh ffmpeg dung MOT khung xem truoc — qua `loc_cat_noi` cua render.

    🔴 **Buoc 1 (khung anh -> video `yuv420p` khong mat) khong phai trang tri.**
       Do 22/09: cung chuoi loc, cung diem anh, dau vao `rgb24` tu tep PNG va
       dau vao `rgb24` tu tep MOV cho ra **1.488 diem anh lech** (toi 3 muc) o
       vung lam mo — ffmpeg thuong luong dinh dang KHAC nhau tuy dau vao (mot
       ben doi sang `yuva420p` ngay dau, ben kia doi SAU `crop`). Render that doc
       h264 `yuv420p`; dua xem truoc ve dung dinh dang do thi chuoi loc thuong
       luong y het, va xem truoc khop render TUNG diem anh (L_PHU_DE.md §4).

    ⚠️ `-ss` dat SAU `-i` (tim o dau RA): bo loc van thay moc that cua tung
       khung, nen `ass=` ve dung trang thai o giay `XEM_TRUOC_GIAY`. Dat `-ss`
       truoc `-i` se dat lai moc ve 0 va xem truoc luon la khung dau hieu ung.
    """
    from . import che_do_render as cdr

    dai = XEM_TRUOC_GIAY + 0.2
    chuan = [ffmpeg, "-v", "error", "-nostdin", "-y",
             "-loop", "1", "-framerate", "25", "-t", f"{dai:.2f}", "-i", anh,
             "-pix_fmt", DINH_DANG_VAO, "-c:v", "ffv1", duong_tam]
    # ⭐ `rong`/`cao` la kich thuoc cua CHINH khung anh nay. Chang VUNG can
    #    chung tu V5: `dien_nen` tinh hinh hoc bang PIXEL (dai nguon <= 4 px), va
    #    mot phan so khong noi duoc "4 px" la bao nhieu.
    #
    # ⚠️ Xem truoc phai di qua DUNG chuoi loc cua render — do la ca ly do tep nay
    #    goi `loc_cat_noi` thay vi tu dung mot chuoi rieng. Bo trong hai tham so
    #    nay thi xem truoc se NEM o dung cai vung ma render dung duoc, tuc khach
    #    ve mot vung hop le ma o xem truoc bao loi.
    loc = cdr.loc_cat_noi([(0.0, dai)], vung=vung, duong_ass=duong_ass,
                          rong_nguon=int(rong or 0), cao_nguon=int(cao or 0))
    dung = [ffmpeg, "-v", "error", "-nostdin", "-y", "-i", duong_tam,
            "-filter_complex", loc, "-map", "[ra]",
            "-ss", f"{XEM_TRUOC_GIAY:.2f}", "-frames:v", "1",
            "-pix_fmt", "rgb24", duong_ra]
    return [chuan, dung]


def xem_truoc(ho_so: dict | None, anh: bytes, *, vung=(), nguon: str = "",
              dich: str = "") -> bytes:
    """Mot khung PNG: `anh` + vung che + phu de theo `ho_so`. Nem `PhuDeLoi`."""
    import io
    import subprocess
    import tempfile

    from PIL import Image

    if not anh or len(anh) > XEM_TRUOC_TRAN_BYTE:
        raise PhuDeLoi(_t('Ảnh khung hình xem trước rỗng hoặc quá lớn.'))
    try:
        with Image.open(io.BytesIO(anh)) as im:
            dang, (rong, cao) = im.format, im.size
    except Exception as exc:
        raise PhuDeLoi(_t('Ảnh khung hình xem trước không đọc được.')) from exc
    if dang not in ("PNG", "JPEG") or not (
            16 <= rong <= XEM_TRUOC_CANH_TOI_DA and 16 <= cao <= XEM_TRUOC_CANH_TOI_DA):
        raise PhuDeLoi(_t('Ảnh khung hình xem trước không đọc được.'))

    # Vung xem truoc ap CA khung: mot khung khong co truc thoi gian.
    vung_xt = [{k: v[k] for k in ("loai", "x0", "y0", "x1", "y1")}
               for v in (vung or ())]
    ho = dict(ho_so) if ho_so else None
    if ho and ho.get("che_do") == CHE_DO_TU_DONG:
        dai = dai_phu_de_goc(vung_xt)
        if dai:
            ho["dai_phu_de_goc"] = dai

    from apps.autosubvideo.segmenter import SubtitleEvent

    from . import nhap_media

    with tempfile.TemporaryDirectory(prefix="asv_pd_xt_") as tam:
        duong_anh = str(Path(tam) / ("khung.png" if dang == "PNG" else "khung.jpg"))
        Path(duong_anh).write_bytes(anh)
        duong_ass = ""
        if co_dot_vao_hinh(ho):
            cau = cau_mau(ho, nguon=nguon, dich=dich)
            hien, so_dong = _ngat_dong(cau)
            su_kien = [SubtitleEvent(start=0.0, end=XEM_TRUOC_DAI_SU_KIEN,
                                     text=cau, display_text=hien,
                                     line_count=so_dong)]
            duong_ass = viet_tep_ass(ho, su_kien_ra_goi(su_kien), tam,
                                     rong=rong, cao=cao)
        duong_ra = str(Path(tam) / "xem_truoc.png")
        for cmd in lenh_xem_truoc(ffmpeg=nhap_media.media.ffmpeg_bin(),
                                  anh=duong_anh, duong_ass=duong_ass,
                                  vung=vung_xt, duong_ra=duong_ra,
                                  rong=rong, cao=cao,
                                  duong_tam=str(Path(tam) / "khung.mkv")):
            try:
                kq = subprocess.run(cmd, capture_output=True, timeout=30,
                                    check=False)
            except subprocess.TimeoutExpired as exc:
                raise PhuDeLoi(_t('Dựng khung xem trước quá hạn.')) from exc
            if kq.returncode != 0:
                raise PhuDeLoi(_t('Không dựng được khung xem trước.'))
        if not Path(duong_ra).is_file():
            raise PhuDeLoi(_t('Không dựng được khung xem trước.'))
        return Path(duong_ra).read_bytes()


def xem_truoc_tu_form(phu_de: str, *, anh: bytes, vung: str = "",
                      preset: str = "", nguon: str = "", dich: str = "") -> bytes:
    """Cua HTTP cua xem truoc. Duyet Y HET nop that (`tu_form`) roi dung khung.

    🔑 Nam o day, khong o `routes.py` (tran 900 dong, `test_423`): route chi
       doc form va goi mot ham.

    ⭐ Preset giu hinh: vung che KHONG ap (ban dung bo vung o duong sao chep),
       nen xem truoc cung khong ap — va `tu_form` da tu choi khac vao hinh o do.
    """
    import json

    from . import vung_che
    from .hop_dong_v4 import PRESET_GIU_HINH

    ho_so = tu_form(phu_de, preset=preset)
    try:
        tho_vung = json.loads(vung) if (vung or "").strip() else []
    except (ValueError, TypeError) as exc:
        raise PhuDeLoi(_t('Vùng che không đọc được.')) from exc
    try:
        ds_vung = vung_che.chuan_hoa(tho_vung)
    except vung_che.VungLoi as exc:
        raise PhuDeLoi(str(exc)) from exc
    if preset == PRESET_GIU_HINH:
        ds_vung = []
    return xem_truoc(ho_so, anh, vung=ds_vung, nguon=nguon, dich=dich)
