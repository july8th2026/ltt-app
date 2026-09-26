"""Giai doan `edit_plan` — phan quyet "canh nao kem" cua GIAI DOAN 2.

⭐ **26/09/2026: giai doan nay ⛔ KHONG goi model nao nua** (B1 §9b, nam can cu).
   Ba tieu chi cua no — *khong co loi thoai* · *toi den / chay sang* · *dung
   hinh* — deu do duoc **TAT DINH**, va ca ba bo do deu DA CO trong kho. Xem
   khoi ghi chu o `_do_cac_canh`.

⭐ Va no chay **SAU `render`** (`pipeline.CHUOI`): GD1 giao mot MP4 tieng Viet
   full do dai truoc khi ai duoc cat mot khung nao, nen ke cat va phep phan
   quyet dung tren **cung mot dong ho**.

Giai doan nay gan nhu khong ton gi khi preset la `localize_preserve_picture`:
khong canh nao duoc cat, nen ⛔ khong tach canh va ⛔ khong do hinh.
"""
from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (ban_bien_tap, canh as canh_mod, hieu_canh as hc, hop_dong_v4,
               lat_cat, nhap_media, qc)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)

#: Phien ban MA cua giai doan, di vao van tay.
#:
#: 🔑 **2 tu pha 27**: truoc do giai doan nay truyen `hieu = ()` cho `lap_ban`,
#:    nen moi ban bien tap la mot ban "khong co bang chung — giu het". Mot ban
#:    bien tap sinh boi ma CU va mot ban sinh boi ma NAY tra loi hai cau hoi
#:    khac nhau, va van tay phai noi duoc dieu do.
#:
#: 🔑 **3 tu 26/09/2026**: bang chung chuyen tu **VLM** sang **phep do tat dinh**.
#:    Cung mot canh, cung mot video, hai phien ban ma cho hai cau tra loi khac
#:    nhau — nen mot bo dem khong biet so nay la mot bo dem noi doi.
PHIEN_BAN_MA = 3


class ThieuChiMuc(ThieuNguon):
    """Chua co chi muc canh de lap ban bien tap."""


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Lap `BanBienTap` va tra ve phan de promote.

    🔑 **Thu tu 26/09: buoc nay chay SAU `render`.** Quyet dinh cat va phep cat
       (`ke_cat`/`image_finish`) dung tren **cung mot truc** — bo di phep doi
       truc mà `thoi_gian.ngan_sach_doan` da goi la *"tron hai dong ho"*.

    ⛔ Ly do CU (`V4-R07`: *"dung dich nhung cau thuoc canh se bi cat"*) het
       dung khi GD1 giu nguyen hinh va xuat MP4 full do dai — ⛔ khong con canh
       nao bi cat trong GD1 de tiet kiem. Cai gia (tra tien tieng cho <= 5 %
       se bi bo) da duoc nhan o B1 §9a.
    """
    from . import cai_dat as cd, features

    preset = cd.doc(run).preset

    tt = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    thoi_luong = float(((tt.outputs or {}) if tt else {}).get("thoi_luong") or 0.0)

    # ── Chi muc canh ────────────────────────────────────────────────────────
    #
    # ⛔ `PRESET_GIU_HINH` khong can chi muc chi tiet: khong canh nao bi cat, nen
    #    mot chi muc mot-canh la du va dung. Chay tach canh o day la tra tien
    #    ffmpeg cho mot cau tra loi khong ai doc.
    if preset == hop_dong_v4.PRESET_GIU_HINH:
        if thoi_luong <= 0:
            raise ThieuChiMuc(_t('Chưa có bản media để phân tích cảnh.'))
        ci = canh_mod.ChiMucCanh(
            (canh_mod.Canh("canh_0001", 0.0, thoi_luong),), thoi_luong,
            ghi_chu={"bo_qua_tach_canh": "preset giu nguyen hinh"})
        hieu = ()
    else:
        # 🔑 LAT CAT: luot NOI TIEP dung lai chi muc canh cua luot dau (luu
        #    trong con tro) thay vi tach canh lai tren ca video 120 phut — vua
        #    tiet kiem mot lan ffmpeg dai, vua bao dam ma canh KHONG doi giua
        #    hai luot (diem chot khoa theo ma canh).
        lc = (lat_cat.mo(db, run, "edit_plan", du_phong_s=0.0)
              if db is not None and run is not None else None)
        cu = (lc.trang_thai.get("chi_muc")
              if lc is not None and lc.noi_tiep else None)
        # ⭐ Duong hinh can cho CA HAI viec (tach canh va do den/dung hinh), nen
        #    lay MOT lan — ke ca o luot noi tiep, cai von bo qua buoc nay.
        duong = _nguon_soi_duoc(db, kho, run)
        if cu:
            ci = canh_mod.tu_dict(cu)
        else:
            ci = canh_mod.phan_tich(duong, thoi_luong=thoi_luong,
                                    hoi_huy=getattr(ctx, "is_cancelled", None))
        canh_mod.kiem_chi_muc(ci)
        # 🔑 Diem chot DUY NHAT cua giai doan nay: chi muc canh. Mot lan tach canh
        #    tren video 120 phut la mot lenh ffmpeg dai, va ma canh ⛔ khong duoc
        #    doi giua hai luot. ⛔ Khong con diem chot theo TUNG canh — tu 26/09
        #    ⛔ khong canh nao ton tien rieng.
        if lc is not None:
            lc.kiem(vi_tri=1, trang_thai={"chi_muc": _chi_muc_dict(ci)})

    ban_ghi = _ban_ghi(db, kho, run)
    # 🔑 **Phep do nam SAU khi co ban chep loi, va truoc `lap_ban`.** Nguong bo
    #    cua mot canh CO loi thoai khac han, nen bang chung hinh chi co nghia khi
    #    ta da biet canh nao giao doan thoai.
    if preset == hop_dong_v4.PRESET_GIU_HINH:
        hieu, hong = (), []
    else:
        hieu, hong = _do_cac_canh(duong, ci, ban_ghi)
        _chot_do_phu(preset, ci, hieu, hong)
        if lc is not None:
            lc.xong_mot()
    ban = ban_bien_tap.lap_ban(preset=preset, chi_muc=ci,
                               hieu_canh=hieu, ban_ghi=ban_ghi)
    if hieu:
        # ⚠️ **Phien ban ffmpeg vao GHI CHU, tuc vao `ban.van_tay()`** —
        #    `sang_dict()` bam ca `ghi_chu`. Tu 26/09 quyet dinh cat LA ket qua
        #    cua `blackdetect`/`freezedetect`: doi ffmpeg co the doi ranh gioi
        #    khoang ⇒ doi QUYET DINH. Khuon lay tu `nhap_media.phien_ban_ffmpeg`,
        #    y nhu `media_prepare`/`compose` da lam.
        #
        # ⛔ Nhanh giu hinh KHONG mang khoa nay, va do la co y: no ⛔ khong chay
        #    ffmpeg de quyet dinh gi, nen mot phien ban ffmpeg trong van tay cua
        #    no la mot ban khai ve mot thu khong tham gia.
        ban = dataclasses.replace(
            ban, ghi_chu={**dict(ban.ghi_chu),
                          "ffmpeg": nhap_media.phien_ban_ffmpeg()})

    # ── Luu ban + chi muc thanh MOT artifact ───────────────────────────────
    #
    # ⭐ Mot tep chu khong hai: ban bien tap va chi muc canh khong doc duoc tach
    #    roi — mot quyet dinh "cat canh_0007" vo nghia neu khong biet canh do la
    #    khoang thoi gian nao. Luu roi la mo mot duong de hai nua lech phien ban.
    import io

    from . import assets

    vt = van_tay_ban(ban)
    goi = json.dumps({"ban": ban.sang_dict(), "chi_muc": _chi_muc_dict(ci)},
                     ensure_ascii=False, sort_keys=True).encode("utf-8")
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage="edit_plan", van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu bản biên tập'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "ban": ban,
        "chi_muc": ci,
        "tom_tat": {
            "preset": preset,
            "so_canh": len(ci.canh),
            "so_giu": len(ban.cac_ma_giu),
            "so_cat": len(ban.cac_ma_cat),
            "van_tay_ban": ban.van_tay(),
            "so_canh_da_doc": len(hieu),
            # 🔑 **Canh doc HONG phai nhin thay duoc trong bang chung cua luot
            #    chay, khong chi trong log.** Luot nen v3 (23/09) ghi
            #    `so_canh_da_doc: 4` cho 6 canh va khong mot chu nao noi hai
            #    canh kia hong the nao — nen "smart_localize khong cat gi" doc
            #    ra giong het mot quyet dinh dung dan.
            "so_canh_hong": len(hong),
            "canh_hong": list(hong),
            "do_phu_bang_chung": (round(len(hieu) / len(ci.canh), 4)
                                  if ci.canh else 0.0),
            **dict(ban.ghi_chu),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Bang chung TAT DINH cho tung canh — ⛔ KHONG goi model
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔑 **26/09/2026 — VLM thoi viec o day (B1 §9b).** Truoc do giai doan nay hoi
#    `ai.DOC_CANH` ve tung canh: *"canh nay co gi, ai dang noi, co quan trong
#    khong"* — mot phan quyet **NGU NGHIA**. Nhung tieu chi chu du an dat la
#    *"cat vung KHONG co loi thoai, chat luong doan kem, ⛔ khong qua 5%"*, va
#    ⛔ khong mot ve nao trong do doi mot y kien:
#
#        khong co loi thoai  ->  SO HOC tren ban chep loi DA CO MOC
#        ranh gioi canh      ->  PySceneDetect ContentDetector (`canh.phan_tich`)
#        toi den / chay sang ->  ffmpeg `blackdetect`   (`qc.BLACKDETECT`)
#        dung hinh           ->  ffmpeg `freezedetect`  (`qc.FREEZEDETECT`)
#
# ⭐ **Lop TINH la thu vien chuan; ta chi viet phan NOI.** Ca ba phep do deu DA
#    CO trong kho va da duoc do: `canh.py` chon PySceneDetect bang benchmark,
#    `qc.py` §T13 chay `blackdetect`+`freezedetect` trong MOT luot giai ma.
#    ⛔ Khong mot nguong moi nao duoc dat o day — nguong quyet dinh van la
#    `ban_bien_tap.NGUONG_BO`, doc tu module chu.
#
# ⭐ Va tat dinh la mot **tinh chat san pham**, khong phai mot toi uu: cat la
#    thao tac ⛔ KHONG DAO DUOC tren ban giao khach, nen cung mot video phai cat
#    cung mot cho o moi luot chay. VLM ⛔ khong bao dam dieu do — no con pha ca
#    van tay lan bo dem.
#
# ⚠️ **Cai mat, noi thang:** mat kha nang noi *"canh nay nham"*. Tinh nang do
#    ⛔ chua ai dat hang (B1 §9b). Them lai mot nac VLM **tuy chon** de hon
#    nhieu so voi go no ra khoi duong mac dinh.

#: Ten phep do, di vao `ly_do` cua tung quyet dinh va vao bao cao van hanh.
LOAI_DO_TAT_DINH = "do_tat_dinh"


@dataclass(frozen=True)
class BangChungCanh:
    """Bang chung TAT DINH ve MOT canh. Duck-type cua thu `lap_ban` doc.

    ⚠️ **⛔ Co y KHONG dung `hieu_canh.HieuCanh`**, du hai thu co cung ba truong
       ma `ban_bien_tap.lap_ban` doc (`ma_canh`, `de_xuat`, `do_tin`).
       `HieuCanh` khai ro *"moi truong deu la thu VLM tra ve, da kiem"* — nhet
       mot phep do ffmpeg vao do la mot ban khai **SAI ve xuat xu** cua con so.
       Va `hieu_canh.py` con phuc vu `HO_SO_NOI_DUNG` (duong chon giong), nen
       ⛔ khong duoc lam nhap nhang no.
    """

    ma_canh: str
    de_xuat: str
    do_tin: float
    ly_do: str = ""
    #: Ten cac phep do DA NO tren canh nay. Rong = canh sach.
    canh_bao: tuple[str, ...] = ()


def _khoang_kem(do: dict) -> tuple[tuple[float, float], ...]:
    """HOP cua khoang den va khoang dung hinh, da gop.

    ⚠️ **Gop TRUOC khi do, ⛔ khong cong hai con so.** Mot khoang vua den vua
       dung hinh duoc ffmpeg bao ra o **CA HAI** bo loc; cong hai lan cho ra ti
       le > 1, tuc mot canh sach cung co the vuot nguong. `ke_cat._gop` la phep
       gop DA CO trong kho (cung luat `KHIT_GIAY`), nen ⛔ khong viet ban thu hai.
    """
    from . import ke_cat as kc

    kh = [(float(a), float(b)) for a, b in
          (list(do.get("khoang_den") or []) + list(do.get("khoang_dong") or []))]
    return kc._gop(tuple(sorted(kh)))


def _phan_giao(khoang, bat: float, ket: float) -> float:
    """Tong thoi luong cua `khoang` nam trong `[bat, ket)`. Thuan, kiem duoc."""
    return sum(max(0.0, min(float(k), float(ket)) - max(float(b), float(bat)))
               for b, k in khoang)


def _han_do_hinh() -> int:
    """Timeout cua luot ffmpeg do hinh, KEP boi ngan sach con lai cua job.

    🔴 Cung khuon voi demucs va render (`lat_cat.han_tien_trinh_con`): giai doan
       nay ⛔ khong chia duoc — mot luot giai ma tren CA video — nen neu timeout
       cua ffmpeg lon hon tran job thi `job_runner._het_gio` ban `os._exit(3)`
       TRUOC, va tren Windows tien trinh con ⛔ khong chet theo cha: mot ffmpeg
       mo coi tiep tuc doc ca tep sau khi job da bao hong.

    ⛔ `mac_dinh` doc tu chinh tran cua giai doan (MANIFEST), ⛔ khong go tay mot
       so thu hai ve cung mot dieu.
    """
    return lat_cat.han_tien_trinh_con("edit_plan",
                                      lat_cat.tran_giai_doan("edit_plan"))


def _do_cac_canh(duong: str, ci, ban_ghi: dict) -> tuple[tuple, list[dict]]:
    """Bang chung tat dinh cho TUNG canh. `(tuple[BangChungCanh, ...], hong)`.

    🔑 **Hai ve, y nhu ban VLM cu**, va ly do khong doi: mot canh *"khong co bang
       chung"* va mot canh *"do duoc, sach"* ⛔ khong duoc ra ngoai giong nhau —
       neu khong thi `so_cat = 0` doc ra y het mot quyet dinh dung dan. Ve thu
       hai la thu `_chot_do_phu` gac.

    ⛔ **Thieu ban chep loi la THIEU BANG CHUNG, ⛔ khong phai "khong co thoai".**
       `_co_thoai` tra `False` cho MOI canh khi ban ghi rong, tuc ca video bien
       thanh *"khong loi thoai"* va thanh ung vien cat khap noi. Day dung lop
       *"hai trang thai gop thanh mot gia tri"* ma kho da ghi so — nen no la mot
       **bat bien o bien**, ⛔ khong phai mot canh bao.

    ⚠️ Phep do chay tren **ban NGUON** con `image_finish` cat tren **ban RA**, va
       hai truc do trung nhau **vi mot dieu kien co that**: GD1 giu MOI khung va
       xuat MP4 full do dai (B1 §9a), nen `render` ⛔ khong dich moc nao. Chinh
       `qc.py` §T13 da do dieu do: nguon 0 s den / 0 s dung hinh, ban ma hoa lai
       libx264 crf23 cung 0 s / 0 s ⇒ lan ma hoa ⛔ khong sinh khoang nao.
    """
    canh = list(getattr(ci, "canh", ()) or ())
    if not (ban_ghi or {}).get("doan"):
        return (), [{"ma_canh": c.ma, "loai": "thieu_ban_chep_loi"} for c in canh]
    try:
        do = qc.do_hinh(duong,
                        thoi_luong=float(getattr(ci, "thoi_luong", 0.0) or 0.0),
                        timeout=_han_do_hinh())
    except qc.QcError as exc:
        # ⛔ KHONG nem: mot bo do hong = "khong co bang chung ve canh nao", va
        #    `_chot_do_phu` moi la cho phan xu dieu do (mot cho, khong hai).
        # ⭐ THONG DIEP, khong chi ten lop: nhat ky luot nen v3 chi ghi
        #    `(LuocDoSai)` nen phai goi lai 18 luot that moi biet vi sao.
        log.warning("edit_plan: khong do duoc hinh (%s: %s)",
                    type(exc).__name__, str(exc)[:200])
        return (), [{"ma_canh": c.ma, "loai": "khong_do_duoc_hinh"} for c in canh]

    kem = _khoang_kem(do)
    den = list(do.get("khoang_den") or [])
    dong = list(do.get("khoang_dong") or [])
    ra: list[BangChungCanh] = []
    for c in canh:
        bat, ket = float(c.bat), float(c.ket)
        dai = max(0.0, ket - bat)
        # ⭐ CUNG mot `_co_thoai` ma `lap_ban` dung de chon nguong. Hai ban sao
        #    cua phep "canh nay co thoai khong" se troi khoi nhau, va cai troi do
        #    lam cat vao cho co tieng.
        if ban_bien_tap._co_thoai(ban_ghi, bat, ket):
            ra.append(BangChungCanh(
                c.ma, hc.GIU, 1.0,
                "canh giao doan thoai — ⛔ khong bao gio la ung vien cat",
                ("co_thoai",)))
            continue
        ti_le = (_phan_giao(kem, bat, ket) / dai) if dai > 0 else 0.0
        # ⭐ Nguong DOC tu module chu. `_quyet_dinh_mot_canh` so `do_tin` voi
        #    DUNG hang so nay, nen hai ben ⛔ khong the troi khoi nhau.
        de_xuat = hc.BO if ti_le >= ban_bien_tap.NGUONG_BO else hc.GIU
        canh_bao = tuple(ten for ten, co in (
            ("toi_den", _phan_giao(den, bat, ket) > 0.0),
            ("dung_hinh", _phan_giao(dong, bat, ket) > 0.0),
        ) if co)
        ra.append(BangChungCanh(
            c.ma, de_xuat, ti_le,
            f"{LOAI_DO_TAT_DINH}: {ti_le:.0%} thoi luong canh la khung den / "
            f"dung hinh, va canh ⛔ khong giao doan thoai nao",
            canh_bao))
    return tuple(ra), []


#: 🔴 **`smart_localize` doi bang chung cho MOI canh — khong phai "phan lon".**
#:
#:    Mot canh khong co bang chung **luon duoc GIU**
#:    (`ban_bien_tap._quyet_dinh_mot_canh`), va do la quyet dinh dung: cat mu
#:    nguy hiem hon giu thua. Nhung hau qua o cap SAN PHAM thi khong dung: khach
#:    bam "cat thong minh", tra tien cho duong cat thong minh, va nhan ve mot
#:    ban ma hoa lai cua chinh video ho — giong het `localize_preserve_picture`,
#:    khong mot loi nao noi vi sao.
#:
#:    Do that 23/09 (luot nen v3): 2/6 canh doc hong ⇒ `so_cat = 0/6` ⇒ khac
#:    biet san pham giua hai preset **bien mat**, va giai doan bao `succeeded`.
#:
#: ⭐ Vi sao 1,0 chu khong phai mot nguong hieu chinh: mot nguong 0,8 tra loi
#:    cau *"bao nhieu phan tram la du"* — mot cau khong ai do duoc va khong ai
#:    do cho. `1,0` tra loi mot cau khac han: *"co lo hong im lang nao khong"*.
#:    Do la mot bat bien, khong phai mot tham so.
#:
#: ⭐ Va cho DUNG la re: `edit_plan` chay TRUOC `content_process` va
#:    `voice_synthesis`, nen mot lan tu choi o day tra lai cho khach ca doan
#:    dat nhat cua chuoi (84 + 943 giay o luot nen v3).
#:
#: ⚠️ **Nen tang KHONG tu dong thu lai loi nay**, va do la co y.
#:    `ThieuBangChungCanh` ke thua `ThieuNguon` ⇒ `loi.phan_loai` tra
#:    `THIEU_THUONG_NGUON` ⇒ khong thu lai. Lan hoi lai da xay ra roi, ngay
#:    trong giai doan (`SO_LAN_DOC_CANH`); mot vong thu lai thu hai o tang job
#:    chi la cung mot phep goi, cung mot khung hinh, them mot hoa don. Nguoi
#:    quyet dinh chay lai la KHACH, va thong diep noi ro ho co hai lua chon.
PHU_BANG_CHUNG_TOI_THIEU = 1.0


class ThieuBangChungCanh(ThieuNguon):
    """`smart_localize` khong doc duoc het cac canh — khong lap ban cat duoc."""


def _chot_do_phu(preset: str, ci, hieu, hong) -> None:
    """Chan `smart_localize` giao mot ban "giu het" vi doc canh hong.

    ⛔ Khong ap cho `PRESET_GIU_HINH`: preset do khong doc canh nao ca, va mot
       do phu 0 o do la dung hop dong chu khong phai mot lo hong.
    """
    so_canh = len(getattr(ci, "canh", ()) or ())
    if preset != hop_dong_v4.PRESET_CAT_THONG_MINH or not so_canh:
        return
    phu = len(hieu) / so_canh
    if phu + 1e-9 >= PHU_BANG_CHUNG_TOI_THIEU:
        return
    thieu = so_canh - len(hieu)
    log.warning("edit_plan: %d/%d canh khong co bang chung (%s)",
                thieu, so_canh, [h.get("loai") for h in hong][:8])
    raise ThieuBangChungCanh(
        _t('Không đọc được hình của {thieu}/{tong} cảnh nên chưa thể cắt thông '
           'minh. Hãy chạy lại, hoặc chọn chế độ giữ nguyên hình.')
        .format(thieu=thieu, tong=so_canh))


def _nguon_soi_duoc(db, kho, run) -> str:
    """Tep HINH de tach canh.

    🔴 **Ban dau ham nay chi tim trong artifact cua `media_prepare`, va do la mot
       cho chet.** `media_prepare` co y **khong** xuat ban hinh nao: no sinh
       `source_probe.json` va `audio_full.wav`, con ban goc thi khong bi cham
       ("Mat ban goc la mat kha nang tinh lai moi thu ha nguon").

    ⇒ Nen preset `smart_localize` hong ngay o buoc DAU TIEN cua no, voi thong
      bao "chua co ban media de phan tich canh" — mot cau dung ve chu nghia va
      sai ve nguyen nhan.

    ⭐ No khong bi phat hien vi `PRESET_MAC_DINH` la `localize_preserve_picture`,
       va nhanh do **di vong qua ham nay** (mot canh la du). Tuc ca preset cat
       chua tung chay het chuoi mot lan nao. Pha 14 la cho no chay lan dau.

    ⇒ Nguon dung la **ban goc cua run**. Van uu tien mot artifact hinh cua
      `media_prepare` neu sau nay co, nhung khong con phu thuoc vao no.
    """
    from . import assets, features

    gd = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    # ⚠️ Hai ten cho hai hinh dang: mot danh sach ung vien, roi mot khoa duy
    #    nhat. Ban truoc dung chung ten `khoa` cho ca hai.
    ds_khoa = [k for k in (((gd.outputs or {}) if gd else {}).get("khoa_asset") or [])
               if str(k).endswith((".mp4", ".mkv", ".mov"))]
    khoa = str(ds_khoa[0]) if ds_khoa else str(run.source_key or "")
    if not khoa:
        raise ThieuChiMuc(_t('Chưa có bản media để phân tích cảnh.'))
    return assets.nguon_soi_duoc(kho, khoa)


def _ban_ghi(db, kho, run) -> dict:
    from . import features

    gd = features.giai_doan_theo_ten(db, run.id, "transcribe")
    khoa = [k for k in (((gd.outputs or {}) if gd else {}).get("khoa_asset") or [])
            if str(k).endswith(".json")]
    if not khoa:
        return {}
    try:
        with kho.open(khoa[0]) as f:
            return json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("khong doc duoc ban chep loi (%s)", type(exc).__name__)
        return {}


def _chi_muc_dict(ci) -> dict:
    """Chi muc canh dang luu tru. Cung dang voi `canh.sang_json`, dang doi tuong."""
    return json.loads(canh_mod.sang_json(ci))


def van_tay_ban(ban) -> str:
    """Van tay cua giai doan nay.

    🔑 Gom `PHIEN_BAN_MA` (ma cua giai doan) **va** van tay cua chinh ban bien
       tap. Hai thu doi doc lap: sua mot dong ma o day khong doi quyet dinh, va
       doi mot nguong chinh sach khong doi ma.
    """
    return f"{PHIEN_BAN_MA}-{ban.van_tay()}"
