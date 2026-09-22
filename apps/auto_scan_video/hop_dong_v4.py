"""Hop dong san pham V4 — BAN KHAI, khong phai hanh vi.

Tep nay chi chua HANG SO. No khong goi engine, khong cham CSDL, khong dung
mang. Ly do no ton tai: `MVP_CONTRACT.md` cua V2 la mot tai lieu, va mot tai
lieu khong the lam mot phep kiem do. Pha 01 cua V4 doi "hop dong cu khong duoc
tu khang dinh lai mot cach im lang" — muon chan duoc dieu do thi hop dong phai
o dang **may doc duoc**.

## Vi sao V4 khong sua `MVP_CONTRACT.md` tai cho

`start_here.md` muc 5: *"Never silently rewrite historical decisions. Supersede
them with a new ADR."* Ban dong bang `auto_scan_mvp_v1` van dung voi thu no mo
ta — mot san pham CHI long tieng. V4 khong noi ban do sai; V4 noi pham vi da
doi. Nen tep cu duoc giu nguyen chu, chi dinh them mot bang chi duong toi
`ADR-V4-001`, va tep nay la ban khai moi.

## Ba dieu tep nay co y KHONG lam

1. **Khong khai `job_type`, khong khai giai doan.** Chuoi thi hanh nam o
   `pipeline.py`. Tron hai thu lam mot thi doi mot ten giai doan se lang le doi
   ca hop dong san pham.
2. **Khong khai gia.** Gia o `gia.py`.
3. **Khong khai chuoi hien thi.** Moi nhan nguoi dung thay phai di qua `_t()`
   o tang giao dien (pha 21). Mot hang so ky thuat lot vao ban dich la mot
   chuoi khong bao gio dich duoc.
"""
from __future__ import annotations

#: Ban hop dong. Doi gia tri nay = doi san pham, va phai kem mot ADR moi.
PHIEN_BAN_HOP_DONG = "auto_scan_v4_mvp"

#: Ban khai bi thay the. Giu lai de truy vet, KHONG de dung.
PHIEN_BAN_BI_THAY_THE = "auto_scan_mvp_v1"


# ══════════════════════════════════════════════════════════════════════════════
#  Ngon ngu dich
# ══════════════════════════════════════════════════════════════════════════════

#: 🔑 MVP V4 chi sinh **tieng Viet**.
#:
#: ⚠️ VA LY DO PHAI GHI CHO DUNG, VI LY DO SAI SE BI MOT PHIEN SAU "SUA".
#:
#:    `V4_MVP_PRODUCT_CONTRACT.md` viet: *"Target language for V4 MVP is
#:    Vietnamese because the shipped LTT Voice capability is Vietnamese."*
#:    Cau do **khong dung**. `apps/ltt_voice/lan_ngon_ngu.py:6` ghi ro
#:    VieNeu-TTS v3 Turbo la **song ngu that**, model card khai
#:    `language: ["vi", "en"]`, va `NHAN_LAN` (dong 91) liet ke ca hai lan.
#:
#:    Neu ly do duoc chep lai la "vi may sinh tieng chi biet tieng Viet", thi
#:    phien dau tien mo `lan_ngon_ngu.py` se thay dieu nguoc lai, ket luan rang
#:    han che nay la mot nham lan, va mo `en` — trong khi khong ai do chat luong
#:    dich/QC/ngu nghia cho `en` bao gio.
#:
#: ⇒ Ly do THAT, va no van du de dong bang: ca chuoi hieu-va-dich cua V4 duoc
#:   xay quanh mot ngon ngu dich duy nhat. `ContentProfile`, `EditPlan`,
#:   `DubbingFit` va ba lop QC ngu nghia deu chua co bang chung nao cho `en`.
#:   Mo them mot lan la mo them mot bo bang chung, khong phai them mot dong
#:   cau hinh.
#:
#: 🔑 22/09 (asv-final, chu du an chot): dich MO THEM `en`. Tap hop le va ly do
#:    nay song o `ngon_ngu.py` — mot cho; o day chi con MAC DINH cho ho so cu.
NGON_NGU_DICH = "vi"

from .ngon_ngu import DICH_HOP_LE as NGON_NGU_DICH_HOP_LE  # noqa: E402

#: Ngon ngu NGUON: tu doan, hoac khach khai. Tap hop le: `ngon_ngu.NGUON_HOP_LE`.
NGON_NGU_NGUON_TU_DOAN = "auto"


# ══════════════════════════════════════════════════════════════════════════════
#  Hai preset — va day la cho V4 khac V2
# ══════════════════════════════════════════════════════════════════════════════

#: Giu nguyen hinh anh. Duong di da chung minh cua V2: khong xoa canh, khong
#: ma hoa lai hinh tru khi ky thuat bat buoc.
PRESET_GIU_HINH = "localize_preserve_picture"

#: Viet hoa co bien tap. VLM doc canh, chinh sach quyet dinh GIU hay CAT.
PRESET_CAT_THONG_MINH = "smart_localize"

PRESET: tuple[str, ...] = (PRESET_GIU_HINH, PRESET_CAT_THONG_MINH)

PRESET_MAC_DINH = PRESET_GIU_HINH


# ── Thao tac bien tap ────────────────────────────────────────────────────────

THAO_TAC_GIU = "keep"
THAO_TAC_CAT = "cut"

#: 🔑 Bang nay LA hop dong bien tap, khong phai mot goi y.
#:
#: `localize_preserve_picture` co tuple RONG: no khong duoc phep lam gi voi
#: canh ca. Khong phai "chua lam" — la **khong duoc lam**. G10 doi dung dieu do:
#: *"`localize_preserve_picture` cannot cut"*.
THAO_TAC_CHO_PHEP: dict[str, tuple[str, ...]] = {
    PRESET_GIU_HINH: (),
    PRESET_CAT_THONG_MINH: (THAO_TAC_GIU, THAO_TAC_CAT),
}

#: ⛔ Cam voi MOI preset trong MVP V4. Day la danh sach dong: mot muc roi khoi
#:    day la mot quyet dinh san pham, va no can mot ADR.
#:
#:    ⭐ `reorder` nam day chu khong nam o `THAO_TAC_CHO_PHEP` la co y. Neu no
#:       chi vang mat khoi bang tren, thi "chua khai" va "bi cam" trong giong
#:       nhau — va mot pha sau chi can them mot dong la du. O day thi them dong
#:       do lam mot phep kiem do.
CAM_TRONG_MVP: tuple[str, ...] = (
    "reorder",          # thu tu canh la thu tu goc, moi preset
    "reframe",          # YOLO / doi khung hinh
    "crop",
    "zoom",             # motion / camera path
    "broll",            # sinh canh moi
    "upscale",          # `apps/upscalevideo` da lam viec nay
    "music_replace",
    "transition",
)

#: Hoan sang sau MVP. Khac `CAM_TRONG_MVP` o cho: cai nay se mo, cai kia thi
#: khong thuoc san pham. Ca hai deu khong duoc chan release.
HAU_MVP: tuple[str, ...] = (
    "reframe",
    "zoom",
    "upscale",
    "broll",
    "multi_speaker_voice",      # nhieu giong cho nhieu nguoi noi
    "multilingual_target",      # ngon ngu dich ngoai {vi, en} (`ngon_ngu.py`)
    "social_ingest",
    "social_publish",
)

# ⭐ **`logo_image` DA ROI khoi bang tren o pha 08b/11b**, va vong doi ay dung
#    la vong doi ma `HAU_MVP` mo ta: *"cai nay se mo, cai kia thi khong"*.
#
#    No nam o day tu pha 11 vi mot phu thuoc CO THAT — ASV khong co duong nhap
#    anh. Pha 08 mo duong do (`features.gan_logo`), nen phu thuoc het, va muc ay
#    chuyen sang `NANG_LUC_DOI_DIEM_ANH`.
#
# ⛔ Ghi lai buoc chuyen o day chu khong xoa lang le: mot muc bien mat khoi ca
#    hai bang se lam nguoi doc sau tuong no chua bao gio duoc quyet.


# ── Nang luc DOI DIEM ANH ────────────────────────────────────────────────────

#: Nhung thu **sua diem anh cua khung hinh**, tuc chung khong the ton tai o
#: duong `-c:v copy`.
#:
#: 🔴 Day khong phai mot chinh sach ta chon. `localize_preserve_picture` phat
#:    `-c:v copy`: khong khung nao duoc giai ma, nen khong co khung nao trong bo
#:    nho de sua mot diem anh cua no. `ban_dung.kiem` cuong che, giao dien noi
#:    truoc, va `che_do_render` giai thich.
#:
#: ⭐ Bang nay ton tai de tra loi cau *"tinh nang nay co thuoc MVP khong"* bang
#:    MA thay vi bang mot tep `.md`. Mot muc o day la mot muc DA duoc quyet.
# ⭐ **`subtitle_burn` GIA NHAP o pha 14**, va vong doi cua no giong het
#    `logo_image`: no nam o `CAM_TRONG_MVP` + `HAU_MVP` vi mot phu thuoc CO
#    THAT — ASV khong co duong goi nang luc phu de cua `apps/autosubvideo`.
#    Pha 14 mo duong do (`phu_de.py` + `ass=` trong `-filter_complex` cua
#    `ket_xuat`), nen phu thuoc het.
#
# ⛔ **DOT phu de doi diem anh, nen no BAT KHA o preset giu hinh** — `-c:v copy`
#    khong giai ma khung nao. Cung rang buoc VAT LY voi `mask_region`,
#    `text_overlay`, `logo_image`, khong phai mot chinh sach ta chon.
NANG_LUC_DOI_DIEM_ANH: tuple[str, ...] = (
    "mask_region",      # `vung_che` — V5
    "text_overlay",     # `lop_phu`  — V6 pha 11
    "logo_image",       # `logo`     — V6 pha 08b/11b
    "subtitle_burn",    # `phu_de`   — V6 pha 14
)

#: Nang luc KHONG doi diem anh — hop le o MOI preset.
#:
#: 🔑 Bang nay ton tai de tra loi mot cau ma `NANG_LUC_DOI_DIEM_ANH` khong tra
#:    loi duoc: *"khach o preset giu hinh co lay duoc phu de khong?"* Co — chi la
#:    lay ra mot tep `.srt` roi, khong dot vao hinh.
#:
#: ⛔ Gop hai bang lam mot se khoa mat lua chon phu de DUY NHAT con lai o preset
#:    giu hinh. Do la `hai-rao-bi-gop-lam-mot` o dang khac: hai truc doc lap bi
#:    buoc vao mot cong tac, va cai bi mat khong bao loi — no chi khong ton tai.
NANG_LUC_KHONG_DOI_DIEM_ANH: tuple[str, ...] = (
    "subtitle_srt",     # `phu_de.xuat_srt` — V6 pha 14
)


# ══════════════════════════════════════════════════════════════════════════════
#  Chon giong
# ══════════════════════════════════════════════════════════════════════════════

#: Khach tu chon mot giong minh so huu, hoac mot giong mau.
CHE_DO_GIONG_TU_CHON = "USER_SELECTED"

#: He thong chon giong khop dac diem nguoi noi trong nguon.
#:
#: ⚠️ AUTO_MATCH **khong phai** "de trong thi lay giong mac dinh". V2 lam dung
#:    the (`routes.py:135 giong_id: str = Form("")`), va do la mot thu khac han:
#:    mot gia tri mac dinh khong doc gi tu video ca. AUTO_MATCH phai doc dac
#:    diem nguoi noi roi rang buoc — do la cong viec cua pha 09.
CHE_DO_GIONG_TU_KHOP = "AUTO_MATCH"

CHE_DO_GIONG: tuple[str, ...] = (CHE_DO_GIONG_TU_CHON, CHE_DO_GIONG_TU_KHOP)

CHE_DO_GIONG_MAC_DINH = CHE_DO_GIONG_TU_CHON


# ══════════════════════════════════════════════════════════════════════════════
#  Ket qua khach nhan duoc
# ══════════════════════════════════════════════════════════════════════════════

#: Dinh dang ra. Ke thua tu `MVP_CONTRACT.md` muc 3 — khong doi.
DINH_DANG_RA = "mp4"

#: `localize_preserve_picture`: do dai ra **bang** do dai vao, trong dung sai.
#: `smart_localize`: ngan hon hoac bang — khong bao gio dai hon.
#:
#: ⛔ Khong preset nao duoc lam video DAI RA. Do khong phai mot nguong chat
#:    luong, do la mot loi hua: khach dua vao mot video, khong dua vao mot
#:    khoang thoi gian de dien vao.
DUNG_SAI_DO_DAI_S = 0.50

#: Chinh sach that bai ma khach nhin thay: mot lan chay hong thi hong **han**,
#: khong giao ban nua voi. QC co quyen chan.
GIAO_KHI_QC_HONG = False


# ══════════════════════════════════════════════════════════════════════════════
#  Chot noi tai — no o cap module, co chu y
# ══════════════════════════════════════════════════════════════════════════════

def _kiem_tra_hop_dong() -> None:
    """No luc NAP APP neu ban khai tu mau thuan.

    Cung ly do `pipeline._kiem_tra_chuoi()` chay o cap module: mot hop dong
    hong la loi cau hinh, va no phai no luc nap chu khong phai luc mot khach
    hang dang cho job chay.
    """
    thua = set(THAO_TAC_CHO_PHEP) - set(PRESET)
    if thua:
        raise ValueError(f"THAO_TAC_CHO_PHEP khai preset la {sorted(thua)}")
    thieu = set(PRESET) - set(THAO_TAC_CHO_PHEP)
    if thieu:
        raise ValueError(f"preset {sorted(thieu)} chua khai thao tac cho phep")

    if THAO_TAC_CHO_PHEP[PRESET_GIU_HINH]:
        raise ValueError(
            f"{PRESET_GIU_HINH!r} khong duoc phep co thao tac bien tap nao")

    ngoai = set(THAO_TAC_CHO_PHEP[PRESET_CAT_THONG_MINH]) - {
        THAO_TAC_GIU, THAO_TAC_CAT}
    if ngoai:
        raise ValueError(
            f"{PRESET_CAT_THONG_MINH!r} chi duoc giu/cat, khong duoc {sorted(ngoai)}")

    # Mot thao tac vua duoc phep vua bi cam la mot hop dong khong doc duoc.
    for ten, ds in THAO_TAC_CHO_PHEP.items():
        va_cham = set(ds) & set(CAM_TRONG_MVP)
        if va_cham:
            raise ValueError(
                f"preset {ten!r} vua cho phep vua cam {sorted(va_cham)}")

    # ── Nang luc doi diem anh: mot muc, dung MOT trang thai ────────────────
    #
    # 🔑 Ba bang tren la ba TRANG THAI loai tru nhau — dang phuc vu, bi cam,
    #    hoan lai. Mot ma nam o hai bang la mot hop dong noi hai cau khac nhau
    #    ve cung mot tinh nang, va nguoi doc sau se lay cau nao tien cho ho.
    #
    # ⛔ Va cai nguy hiem khong phai mau thuan tho ("vua cho vua cam") — cai do
    #    ai cung thay. Cai nguy hiem la mot ma trong `NANG_LUC_DOI_DIEM_ANH`
    #    **cung** nam trong `HAU_MVP`: ma thi dang chay, tai lieu thi noi "chua
    #    lam", va khong ai doi chieu hai cho ay.
    doi = set(NANG_LUC_DOI_DIEM_ANH)
    for ten_bang, bang in (("CAM_TRONG_MVP", CAM_TRONG_MVP),
                           ("HAU_MVP", HAU_MVP)):
        va_cham = doi & set(bang)
        if va_cham:
            raise ValueError(
                f"nang luc {sorted(va_cham)} vua dang phuc vu vua nam trong "
                f"{ten_bang}")

    if NGON_NGU_DICH not in NGON_NGU_DICH_HOP_LE:
        raise ValueError("NGON_NGU_DICH khong nam trong tap hop le")


_kiem_tra_hop_dong()
