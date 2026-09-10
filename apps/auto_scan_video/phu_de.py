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

CHE_DO_TAT = "tat"
CHE_DO_TU_DONG = "tu_dong"
CHE_DO_TU_CHON = "tu_chon"

CHE_DO: tuple[str, ...] = (CHE_DO_TAT, CHE_DO_TU_DONG, CHE_DO_TU_CHON)

CHE_DO_MAC_DINH = CHE_DO_TAT

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


def cau_hinh_kieu(ho_so: dict | None):
    """Cau hinh CUOI CUNG: preset + tinh chinh cua khach.

    🔑 Mot cho tinh, va ca giao dien lan trinh render deu goi no. Pha 07 da tra
       gia cho bai hoc nguoc lai: muoi cho doc `run.settings`, hai cho lech nhau
       ve mot mac dinh, va mot lan chay **chay** o che do nay trong khi **bang
       chung QC ghi** che do kia.
    """
    kieu = str((ho_so or {}).get("kieu") or KIEU_MAC_DINH)
    goc = cau_hinh_goc(kieu)
    tinh = (ho_so or {}).get("tinh_chinh") or {}
    if not tinh:
        return goc
    return _mo_hinh_kieu()(**{**goc.model_dump(), **tinh})


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
    return ho_so.get("che_do") in (CHE_DO_TU_DONG, CHE_DO_TU_CHON)


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
            (CHE_DO_TU_DONG, N_('Khắc lên hình — kiểu mặc định'),
             N_('Phụ đề được khắc thẳng vào video, dùng kiểu chữ chuẩn.')),
            (CHE_DO_TU_CHON, N_('Khắc lên hình — tự chọn kiểu'),
             N_('Như trên, nhưng bạn chọn kiểu chữ ở ô bên dưới.')),
        ],
        "che_do_mac_dinh": CHE_DO_MAC_DINH,
        "che_do_can_kieu": CHE_DO_TU_CHON,
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
    ra = {k: v for k, v in ho_so.items() if k != "kieu"}
    ra["che_do"] = CHE_DO_TAT
    return ra


# ── Cau noi: KE HOACH (truc RA) -> su kien phu de ────────────────────────────

#: Toi da hai dong moi su kien. Ba dong tren mot khung 16:9 che mat qua nhieu
#: hinh, va `ass_builder` khong tu gioi han.
SO_DONG_TOI_DA = 2

#: Toi da bao nhieu ky tu mot dong truoc khi xuong dong.
KY_TU_MOI_DONG = 42


def _ngat_dong(chu: str) -> tuple[str, int]:
    """Chia mot cau thanh toi da `SO_DONG_TOI_DA` dong. Tra (van, so_dong).

    ⚠️ Ngat theo TU, khong theo ky tu: cat giua mot tu tieng Viet co dau cho ra
       hai manh khong doc duoc, va no chi lo ra khi nhin tep ra.
    """
    tu = str(chu or "").split()
    if not tu:
        return "", 0
    dong: list[str] = []
    hien = ""
    for t in tu:
        thu = (hien + " " + t).strip()
        if hien and len(thu) > KY_TU_MOI_DONG and len(dong) + 1 < SO_DONG_TOI_DA:
            dong.append(hien)
            hien = t
        else:
            hien = thu
    dong.append(hien)
    return "\\N".join(dong), len(dong)


def su_kien_tu_ke_hoach(ke_hoach: dict, van_ban: dict) -> list:
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
    """
    from apps.autosubvideo.segmenter import SubtitleEvent

    chu_theo_ma: dict[str, str] = {}
    for d in (van_ban or {}).get("muc") or []:
        ma = str(d.get("ma") or "")
        if ma:
            chu_theo_ma[ma] = str(d.get("chu") or "")

    ra = []
    for i, m in enumerate((ke_hoach or {}).get("doan") or []):
        chu = chu_theo_ma.get(str(m.get("ma") or ""), "").strip()
        if not chu:
            continue
        bat = float(m.get("dat_tai_ms") or 0) / 1000.0
        dai = float(m.get("dai_ms") or 0) / 1000.0
        if dai <= 0:
            continue
        hien, so_dong = _ngat_dong(chu)
        ra.append(SubtitleEvent(start=bat, end=bat + dai, text=chu,
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
    kieu = cau_hinh_kieu(ho_so)

    # ⚠️ Truyen HAI tham so ro rang thay vi do mot `**dict`: `build_ass` co
    #    tham so vi tri o dau, nen mypy khop `**dict[str, int]` vao tham so thu
    #    tam (`title: str`) va bao sai kieu. Mot `**dict` cung giau di viec tham
    #    so nao that su duoc truyen.
    rong_ass = int(rong) if rong > 0 and cao > 0 else 1920
    cao_ass = int(cao) if rong > 0 and cao > 0 else 1080
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
