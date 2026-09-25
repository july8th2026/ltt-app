"""Giai doan IMAGE_FINISH — **GIAI DOAN 2**: thao tac tren MP4 DA XONG.

Artifact ra:

    <van_tay>.mp4    ban giao cuoi cung          (kind=video)
    <van_tay>.srt    phu de DA DOI MOC, khi co   (kind=subtitle)

⭐ Ke cat + bao cao di vao `tom_tat` (`asv_stage.outputs`), ⛔ KHONG thanh artifact
   thu ba — xem chu thich o cuoi `chay()`. `la_ban_giao` la luat cua ca GIAI DOAN,
   nen mot artifact JSON o day se mang `han=None` nhu video: mot bao cao van hanh
   nam trong kho cua khach MAI MAI (`test_451` bat dung chuyen do).

## Vi sao giai doan nay ton tai — chu du an chot 25/09

    GIAI DOAN 1  media -> demucs -> ASR -> dich -> TTS -> nan -> tron -> render
                 RA: MP4 tieng Viet khop hinh, TOAN BO do dai goc — KHONG cat gi
    GIAI DOAN 2  hinh anh, THAO TAC TREN MP4 DA XONG: cat canh, ...

🔑 **Cai duoc khong phai "quan ly sai so tot hon", ma la "sai so khong co cho
   sinh ra".** `ban_do_thoi_gian.py` mo dau bang chinh van de:

    *"canh bi cat bien mat khoi ban ra, nen giay 120 cua nguon co the la giay 74
    cua ban ra — hoac khong ton tai ... sai so do tich luy theo tung canh bi
    cat."*

   O thu tu cu, phep cat chay TRUOC khi co tieng, nen moi moc cua ke hoach tieng
   phai di qua mot lop doi moc. O day phep cat chay tren MOT tep trong do hinh
   va tieng la hai dong cua cung mot dong ho: `loc_cat_hai_dong` `trim` ca hai
   trong CUNG mot `concat`, nen ⛔ khong the co mot doan tieng bi cut.

## ⛔ Ba thu giai doan nay KHONG lam

1. **Khong goi model.** Quyet dinh "canh nao kem" da chot o `EDIT_PLAN`; o day
   chi doc lai va ap tran (`ke_cat`).
2. **Khong tinh lai ke hoach tieng.** Ban phoi cua giai doan 1 da chuan am mot
   lan; `atrim` khong chuan am lan hai.
3. **Khong noi tran 5 %.** Vuot tran la tin hieu tieu chi sai — `ke_cat.kiem`
   **nem**, va giai doan nay de no nem.

## Chang DIEM ANH — logo/watermark/phu de/lat guong/dich mau/zoom (gd2-diem-anh)

🔑 **Chuyen tu `render` (GD1) xuong day, va day CHINH LA tai cau truc ma chu
   thich cu (truoc 25/09) khai la CHUA lam.** Truoc lan nay, mot lan chay CO
   logo/watermark/phu de/lat guong/dich mau/khung(crop-zoom-doi ti le) VA co cat
   canh se ma hoa lai luong hinh **HAI lan** (mot lan o `render` de dan logo/dot
   phu de/..., mot lan o day de cat). Nay chi **MOT lan**, o day, cung mot luot
   voi phep cat — `che_do_render.loc_cat_hai_dong` cat XONG roi moi di qua chang
   nay (`khung -> diem_anh -> logo -> lop_phu -> phu de`), dung CUNG cac ham
   thap voi `loc_cat_noi` (GD1) nen mot khung hinh burn ra Y HET.

⛔ **`vung` (lam mo/dien nen) va `toc_do` VAN o GD1, khong chuyen.** `vung` dat
   TRUOC concat tren toa do NGUON — no chi co nghia truoc khi hinh bi cat/noi
   lai; `toc_do` doi MOC THOI GIAN cua CA hinh lan tieng (`setpts`/`atempo` dung
   chung he so, ap tren toan bo do dai) — chuyen no xuong day se lam ke cat
   (tinh tren truc bien tap, TRUOC toc do) va toc do tranh nhau tren HAI truc
   thoi gian khac nhau ma khong ai doi chieu.

🔑 **Nguon cua logo/lop_phu/bien_tap: doc thang `cai_dat.doc(run)`, ⛔ khong qua
   ban dung cua COMPOSE.** Ba truong nay tu than khong can mot artifact thuong
   nguon nao (khac `phu_de`, can `ke_hoach` + van ban de chot `su_kien` — nen no
   VAN di qua ban dung, chi la GD1 khong con TU MINH dot no vao hinh). `.ass`
   (khi co) duoc sinh LAI o day tu `hinh.phu_de.su_kien` cua ban dung, DOI MOC
   qua `doi_moc_su_kien` — dung ham, dung truc voi `.srt` rieng ben duoi.
"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (assets, che_do_render as cdr, ke_cat as kc, ket_xuat, lat_cat,
               nhap_media, pipeline)
from .giai_doan_media import ThieuNguon, _duong_doc_duoc

log = logging.getLogger(__name__)

#: Doi khi doi cach dung lenh cua giai doan nay. Vao van tay (O13).
#: ⬆️ 1 -> 2 (gd2-diem-anh, 25/09): `chay()`/`dung_lenh()`/`van_tay()` gio tai
#:    logo, ghi chu lop phu, sinh `.ass` va lam viec voi `bien_tap` — mot ban
#:    giao CU (khong logo) va mot ban giao MOI (co logo, cung dau vao/ke cat)
#:    phai la HAI van tay khac nhau.
PHIEN_BAN_HINH_ANH = 2

#: Dau vao ffmpeg dau tien la LOGO — khac `ket_xuat.py` (`= 2`, vi GD1 co mot
#: dau vao "ban phoi am" rieng o vi tri 1). O day dau vao `0` la MOT tep MP4 da
#: co san CA hinh lan tieng, nen logo dau tien la dau vao `1`.
CHI_SO_LOGO_DAU = 1

#: Tran thoi gian MOT luot cat-noi. Cung bac voi `RENDER`: no cung doc va ghi
#: lai toan bo luong hinh. Kep vao ngan sach con lai cua job (`lat_cat`).
TIMEOUT_HINH_ANH = 3600


class ThieuBanRaGd1(ThieuNguon):
    """Chua co MP4 cua giai doan 1 de thao tac."""


def loc_bien_tap_gd2(cai_bien_tap) -> dict | None:
    """`cai_dat.doc(run).bien_tap` -> phan CHI GD2 dung (bo `toc_do`, viec GD1).

    ⭐ MOT noi loc, dung lai o CA `chay()` (o day) LAN `giai_doan_qc._do_vmaf`
       (tham chieu VMAF) — hai noi doc cung mot cai dat ma tu loc rieng la hai
       co hoi de lech, va lech o day nghia la tham chieu VMAF sai hinh hoc.
    """
    if not cai_bien_tap:
        return None
    return {k: v for k, v in cai_bien_tap.items() if k != "toc_do"} or None


def _khoa_theo_duoi(db, run, ten: str, duoi: str) -> str:
    from . import features

    s = features.giai_doan_theo_ten(db, run.id, ten)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(duoi)), "") if s else ""


def _doc_json(kho: Storage, khoa: str) -> dict:
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


# ══════════════════════════════════════════════════════════════════════════════
#  Dung ke cat — quyet dinh da chot o EDIT_PLAN, tran ap o day
# ══════════════════════════════════════════════════════════════════════════════

def ung_vien_tu_ban_bien_tap(ban, chi_muc) -> list[kc.UngVien]:
    """`BanBienTap` + `ChiMucCanh` -> cac doan tieu chi MUON cat.

    ⭐ Doc canh BI CAT tu quyet dinh, va khoang thoi gian cua no tu chi muc —
       cung khuon voi `ban_do_thoi_gian.tu_ban_bien_tap` (ban noi *canh nao*, chi
       muc noi *canh do la khoang nao*).

    🔑 `do_tin` cua quyet dinh **la** `diem_kem`: no la do tin cua de xuat BO. Mot
       canh bi de xuat bo voi do tin 0,95 te hon mot canh bi de xuat bo voi 0,70,
       va thu tu uu tien cua `ke_cat` doc dung con so do.

    ⛔ Tra danh sach RONG khi thieu mot trong hai nua — ⛔ khong nem. Thieu ban
       bien tap nghia la *"khong co can cu de cat"*, va mac dinh cua ca he la
       GIU (`ban_bien_tap._quyet_dinh_mot_canh`: *"bo la hanh dong phai co can
       cu"*).
    """
    if ban is None or chi_muc is None:
        return []
    theo_ma = {str(c.ma): c for c in (getattr(chi_muc, "canh", ()) or ())}
    ra: list[kc.UngVien] = []
    for q in (getattr(ban, "quyet_dinh", ()) or ()):
        if q.giu:
            continue
        c = theo_ma.get(str(q.ma_canh))
        if c is None:
            # ⛔ KHAI RA bang log, ⛔ khong bo im lang: mot `ma_canh` khong co
            #    trong chi muc la hai artifact da lech phien ban, va do la dung
            #    cai bay "cho noi hai module vut truong im lang".
            log.warning("image_finish: quyet dinh cat canh %s nhung chi muc "
                        "khong co canh do — bo qua", q.ma_canh)
            continue
        ra.append(kc.UngVien(bat=float(c.bat), ket=float(c.ket),
                             diem_kem=float(q.do_tin or 0.0),
                             ly_do_cat=str(q.ly_do or "")))
    return ra


def _ke_cat(db, kho: Storage, run, *, thoi_luong: float) -> kc.KeCat:
    """Ke cat cua lan chay. ⭐ MOT noi tra loi cau *"ta bo gi"*."""
    from . import ban_bien_tap as bbt, canh as canh_mod

    ke_hoach = {}
    khoa_kh = _khoa_theo_duoi(db, run, pipeline.TIMING_ALIGN, ".json")
    if khoa_kh:
        ke_hoach = _doc_json(kho, khoa_kh)

    ban = chi_muc = None
    khoa_ep = _khoa_theo_duoi(db, run, pipeline.EDIT_PLAN, ".json")
    if khoa_ep:
        goi = _doc_json(kho, khoa_ep)
        ban = bbt.BanBienTap.tu_dict(goi.get("ban") or {})
        chi_muc = canh_mod.tu_dict(goi.get("chi_muc") or {})

    return kc.chon(ung_vien_tu_ban_bien_tap(ban, chi_muc),
                   thoai=kc.khe_thoai_tu_ke_hoach(ke_hoach),
                   thoi_luong=thoi_luong)


def _cua_so_khach(db, run):
    """Cua so `cat_dau_cuoi` cua khach -> cap PHAN SO `(tu, den)`, hay `None`.

    🔴 **CO Y nam NGOAI ngan sach 5 %, va ly do phai duoc viet ra.**

       Tran 5 % ton tai vi tieu chi *"chat luong kem"* la mot phep **phan doan**,
       va mot phep phan doan khong tran thi mot ngay no cat 40 % phim cua khach
       (plan §3). Cua so nay ⛔ khong phai mot phan doan — no la **khach tu keo**
       hai tay cam va tu thay ket qua. Ep no vao cung mot tran se lam mot yeu cau
       ro rang cua khach bi he thong tu choi vi mot ly do noi ve do tin cua VLM.

    ⚠️ Nhung no vao `tom_tat` rieng (`cua_so_khach`), nen mot bao cao doc duoc
       phan biet *"he thong cat"* voi *"khach cat"*.
    """
    from . import cai_dat as cd, cat_dau_cuoi

    return cat_dau_cuoi.chuan_hoa(cd.doc(run).cat)


# ══════════════════════════════════════════════════════════════════════════════
#  Phu de: doi moc, ⛔ khong tinh lai
# ══════════════════════════════════════════════════════════════════════════════

def doi_moc_su_kien(goi_su_kien, ban_do) -> list[dict]:
    """Su kien phu de tren truc GD1 -> truc BAN GIAO. ⛔ Bo su kien da bi cat.

    ⛔ `ra()` chu khong `ra_gan_nhat()` cho moc BAT — cung ly do
       `ban_do_thoi_gian.ra` viet ra: mot cau thoai thuoc phan da cat phai **bien
       mat**, ⛔ khong duoc troi sang cho khac. Ep no ve moc gan nhat la doi mot
       mat mat NHIN THAY duoc thanh mot loi KHO TIM.

    ⭐ Moc KET thi `ra_gan_nhat` la dung: mot su kien bat trong phan giu va ket
       trong phan cat chi bi **cat ngan**, khong bi di doi.
    """
    ra: list[dict] = []
    for g in (goi_su_kien or ()):
        b = ban_do.ra(float(g.get("start") or 0.0))
        if b is None:
            continue
        k = ban_do.ra(float(g.get("end") or 0.0))
        if k is None:
            k = ban_do.ra_gan_nhat(float(g.get("end") or 0.0))
        if float(k) - float(b) <= 0.0:
            continue
        ra.append({**dict(g), "start": round(float(b), 3),
                   "end": round(float(k), 3)})
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  Than giai doan
# ══════════════════════════════════════════════════════════════════════════════

def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """MP4 cua GD1 + ke cat -> ban giao cuoi. ⛔ Khong goi model, khong TTS."""
    khoa_gd1 = _khoa_theo_duoi(db, run, pipeline.RENDER, ".mp4")
    if not khoa_gd1:
        raise ThieuBanRaGd1(_t('Chưa có bản kết xuất của giai đoạn 1.'))

    from . import cai_dat as cd, cat_dau_cuoi

    cai = cd.doc(run)
    bao = getattr(ctx, "progress", None) if ctx is not None else None
    hoi_huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None
    co_gpu = bool(str(getattr(ctx, "gpu_uuid", "") or "")) if ctx is not None else False

    with tempfile.TemporaryDirectory(
            prefix=f"asv-gd2-{str(run.id)[:12]}-") as tam:
        thu_muc = Path(tam)
        duong_vao = _duong_doc_duoc(kho, khoa_gd1, thu_muc)

        # 🔑 Do dai doc tu CHINH tep se bi cat, ⛔ khong tu mot ban khai thuong
        #    nguon: ke cat phai dung tren truc cua tep that. Mot lech nua giay
        #    giua ban khai va tep se lam khoang cat cuoi vuot ra ngoai.
        tt_vao = nhap_media.soi(duong_vao)
        thoi_luong = float(tt_vao["thoi_luong"])
        if thoi_luong <= 0:
            raise ThieuBanRaGd1(
                _t('Không đọc được thời lượng bản kết xuất giai đoạn 1.'))
        # 🔑 Khung NGUON cua chang DIEM ANH (khung/logo/lop_phu/phu de) — day la
        #    khung cua CHINH MP4 GD1 giao, ⛔ khong phai khung cua nguon that:
        #    GD1 da ma hoa lai (preset cat luon di duong CAT_MA_HOA_LAI), nen
        #    moi rotation-tag da duoc nuong vao diem anh roi, khong con phai bu
        #    nhu `_co_khung` cua COMPOSE (do tren nguon THO).
        rong_nguon, cao_nguon = int(tt_vao["rong"]), int(tt_vao["cao"])

        if bao:
            bao(10, _t('Đang dựng kế cắt'))

        # ── ⛔ CHI cat/dan diem anh o duong CAT, va ⛔ KHONG tin giao dien ─────
        #
        # 🔴 `localize_preserve_picture` hua *"do dai ra bang do dai vao"*
        #    (`hop_dong_v4.DUNG_SAI_DO_DAI_S`) va `THAO_TAC_CHO_PHEP` cua no la
        #    tuple RONG: *"khong phai 'chua lam' — la KHONG DUOC lam"*. Nen ca
        #    phep cat tu dong LAN cua so `cat_dau_cuoi` cua khach, LAN logo/
        #    lop_phu/bien_tap/phu-de-DOT deu nam TRONG mot `if` so `cach` voi
        #    che do cat.
        #
        # ⚠️ Va o day ⛔ khong tin giao dien: giao dien an hai tay cam khi preset
        #    la giu hinh, nhung mot yeu cau dung tay van toi duoc.
        #
        # ⭐ Chuyen phep cat xuong giai doan 2 ⛔ KHONG duoc lam no rong ra: mot
        #    lop hua khong cat gi van phai khong cat gi. Day la cho cuoi cung con
        #    canh giu loi hua do.
        cach = cdr.che_do_cho(cai.preset)
        ke = kc.chon([], thoi_luong=thoi_luong)      # mac dinh: ⛔ khong cat gi
        khoang = [(0.0, thoi_luong)]
        cua = None
        ds_logo: list = []
        lop_phu: list = []
        bien_tap_gd2: dict | None = None
        if cach == cdr.CAT_MA_HOA_LAI:
            ke = _ke_cat(db, kho, run, thoi_luong=thoi_luong)
            # ⭐ MOT lan doc cua so, dung cho CA phep giao LAN bao cao: hai lan
            #    doc cung mot cai dat la hai cho co the lech (`cai_dat.doc` co the
            #    doc mot `run.settings` da bi ghi lai giua chuoi — xem
            #    `thi_hanh.van_tay` ve `cai_dat.KHOA_DAN_XUAT`).
            cua = _cua_so_khach(db, run)
            # ⭐ Giao **sau** ke cat, cung thu tu voi ban truoc o `compose`: quyet
            #    dinh cua chinh sach co tham quyen (`V4-R07`), cua so khach la mot
            #    lop THU HEP dat len tren no. Lam nguoc lai la de khach vut mat
            #    mot canh ma chinh sach da quyet giu, roi ⛔ khong ai ghi lai.
            khoang = cat_dau_cuoi.giao(list(ke.giu), cua, thoi_luong)
            # 🔑 Logo/lop_phu/bien_tap: doc THANG `cai_dat.doc(run)` — chung
            #    khong can artifact thuong nguon nao. Xem docstring dau tep.
            ds_logo = list(cai.logo or ())
            lop_phu = list(cai.lop_phu or ())
            bien_tap_gd2 = loc_bien_tap_gd2(cai.bien_tap)

        ban_do = _ban_do_tu_khoang(khoang, thoi_luong)
        # ⭐ MOT lan tinh, dung lai cho CA logo/lop_phu (`dung_lenh`) LAN
        #    `PlayRes` cua phu de — `_khung_ra` la noi DUY NHAT tra loi cau hoi
        #    "khung BAN RA cua chang diem anh la bao nhieu".
        rong_khung, cao_khung = _khung_ra(bien_tap_gd2, rong_nguon, cao_nguon)

        # ── Phu de: ho so DA CHOT o COMPOSE, doc lai — ⛔ khong tinh lai ──────
        #
        # 🔑 `hinh.phu_de` cua ban dung GD1 mang `su_kien` (tren truc bien tap),
        #    da chot 1 lan o COMPOSE (can `ke_hoach` + van ban, hai artifact CHI
        #    COMPOSE moi doc). O day chi DOI MOC su kien do sang truc BAN GIAO
        #    that (GD2), ⛔ khong tinh lai NOI DUNG.
        from . import phu_de as _pd

        khoa_ban = _khoa_theo_duoi(db, run, pipeline.COMPOSE, ".json")
        ho_so_pd = ((_doc_json(kho, khoa_ban).get("hinh") or {}).get("phu_de")
                    or None) if khoa_ban else None
        su_kien_ra = (doi_moc_su_kien(ho_so_pd.get("su_kien") or [], ban_do)
                      if ho_so_pd else [])

        duong_chu: list[str] = []
        duong_logo: list[str] = []
        duong_ass = ""
        if cach == cdr.CAT_MA_HOA_LAI:
            from . import lop_phu as _lp
            from .giai_doan_ket_xuat import _tai_ve

            duong_chu = _lp.viet_tep_chu(lop_phu, thu_muc)
            duong_logo = [
                _tai_ve(kho, str(l["khoa"]),
                        thu_muc / f"logo{i}{Path(str(l['khoa'])).suffix or '.png'}")
                for i, l in enumerate(ds_logo)]
            if _pd.co_dot_vao_hinh(ho_so_pd):
                duong_ass = _pd.viet_tep_ass(ho_so_pd, su_kien_ra, thu_muc,
                                             rong=rong_khung, cao=cao_khung)

        tom = {**kc.tom_tat(ke),
               "cua_so_khach": list(cua or ()),
               "cach": cach,
               "thoi_luong_vao": round(thoi_luong, 3),
               "thoi_luong_ra": round(float(ban_do.thoi_luong_ra), 3),
               "so_cho_noi": ban_do.so_cho_noi,
               # 🔴 **Khoang THAT SU duoc giu — ke cat GIAO cua so khach.**
               #    `ke_cat` mot minh ⛔ khong tra loi duoc: cua so `cat_dau_cuoi`
               #    la mot lop thu hep dat len tren no. Va QC **can** chinh danh
               #    sach nay: tham chieu VMAF la nguon chay qua CUNG chuoi loc,
               #    nen mot ban khai thu hai o do se lech va T18 hong vo co.
               "khoang_giu": [[round(float(b), 4), round(float(k), 4)]
                              for b, k in khoang]}

        if bao:
            bao(20, _t('Đang cắt và ghép lại'))

        duong_ra = str(thu_muc / "ra.mp4")
        # 🔑 ⛔ Khong cat gi VA ⛔ khong logo/lop_phu/bien_tap/phu-de-dot nao ⇒
        #    **remux**, ⛔ khong ma hoa lai. Mot lan ma hoa lai "cho nhat quan"
        #    tren mot tep khong co gi thay doi la lay mot ban sao nguyen ven
        #    doi lay mot ban kem hon — va no lam preset giu hinh mat dung loi
        #    hua *"hinh anh duoc sao chep nguyen ven"*.
        #
        # ⚠️ **`co_diem_anh` la them moi (gd2-diem-anh).** Truoc lan nay `khong_cat`
        #    chi hoi "co cat khong": mot job smart_localize BAT logo nhung
        #    KHONG cat canh nao van phai ma hoa lai — neu khong logo se bien
        #    mat im lang tren duong remux.
        co_diem_anh = bool(ds_logo or lop_phu or bien_tap_gd2 or duong_ass)
        khong_cat = (ban_do.so_cho_noi == 0
                    and abs(float(ban_do.thoi_luong_ra) - thoi_luong) <= 1e-3
                    and not co_diem_anh)
        bo_ma_hoa = "" if khong_cat else cdr.chon_bo_ma_hoa(cho_phep_gpu=co_gpu)
        cmd = dung_lenh(duong_vao, duong_ra, khoang=khoang,
                        bo_ma_hoa=bo_ma_hoa,
                        thoi_luong_ra=float(ban_do.thoi_luong_ra),
                        ffmpeg_bin=nhap_media.media.ffmpeg_bin(),
                        bien_tap=bien_tap_gd2,
                        rong_nguon=rong_nguon, cao_nguon=cao_nguon,
                        ds_logo=ds_logo, duong_logo=duong_logo,
                        rong_khung=rong_khung,
                        lop_phu=lop_phu, duong_chu=duong_chu,
                        cao_khung=cao_khung, duong_ass=duong_ass)
        try:
            ket_xuat._chay_co_tien_do(
                cmd, tong_giay=float(ban_do.thoi_luong_ra),
                timeout=lat_cat.han_tien_trinh_con(pipeline.IMAGE_FINISH,
                                                   TIMEOUT_HINH_ANH),
                hoi_huy=hoi_huy,
                env=(ctx.gpu_env() if ctx is not None
                     and getattr(ctx, "gpu_env", None) else None),
                bao_tien_do=(lambda p: bao(20 + p * 0.7,
                                           _t('Đang cắt và ghép lại')))
                if bao else None)
        except subprocess.TimeoutExpired as exc:
            raise ket_xuat.KetXuatError(_t('Giai đoạn hình ảnh quá hạn.')) from exc

        if bao:
            bao(92, _t('Đang kiểm tệp kết quả'))

        # ── Do lai tep ra, TRUOC khi promote (cung thu tu voi RENDER) ────────
        tt_ra = nhap_media.soi(duong_ra)
        _kiem_do_dai(float(tt_ra["thoi_luong"]), float(ban_do.thoi_luong_ra))
        _kiem_khung_ra(tt_ra, bien_tap_gd2, rong_nguon, cao_nguon)

        vt = van_tay(khoa_gd1, ke, cua, bo_ma_hoa, ds_logo=ds_logo,
                    lop_phu=lop_phu, phu_de=ho_so_pd, bien_tap=bien_tap_gd2)
        phan = [{"staging_key": _dua_len(kho, run, duong_ra, vt, "mp4",
                                        "video/mp4"),
                 "kind": "video", "duoi": "mp4", "van_tay": vt,
                 "parent_keys": [khoa_gd1]}]

        # ── Phu de: .srt DOI MOC roi sinh lai, ⛔ khong chep tep cua GD1 ──────
        khoa_srt = _sinh_srt(kho, run, ho_so_pd=ho_so_pd, su_kien_ra=su_kien_ra,
                             thu_muc=thu_muc, van_tay=vt)
        if khoa_srt:
            phan.append({"staging_key": khoa_srt, "kind": "subtitle",
                         "duoi": "srt", "van_tay": vt,
                         "parent_keys": [khoa_gd1]})

    # 🔴 **Ke cat di vao `tom_tat` (tuc `asv_stage.outputs`), ⛔ KHONG thanh mot
    #    artifact thu ba.** `thi_hanh.la_ban_giao` dung cho ca GIAI DOAN, nen moi
    #    artifact cua giai doan nay se mang `han=None` — ke ca mot bao cao van
    #    hanh. Mot bao cao "khong bao gio het han" la mot bao cao **nam trong kho
    #    cua khach mai mai** va `test_451` bat dung chuyen do.
    #
    # ⭐ Va `outputs` la dung cho cua no: `giai_doan_qc` + `giai_doan_qc_ai` doc
    #    ke cat qua `features.giai_doan_theo_ten(...).outputs`, y het cach chung
    #    doc moi con so tom tat khac. Mot artifact JSON chi de hai giai doan ke
    #    tiep doc la mot tep ton han luu de thay cho mot truong.
    return {"phan": phan, "tom_tat": {**tom,
                                      "ke_cat": ke.sang_dict(),
                                      "bo_ma_hoa": bo_ma_hoa,
                                      "co_byte": int(tt_ra["co_byte"]),
                                      "codec_video": tt_ra["codec_video"]}}


def _khung_ra(bien_tap_gd2, rong_nguon: int, cao_nguon: int) -> tuple[int, int]:
    """`(rong, cao)` cua BAN RA — thu logo, vien chu va `PlayRes` phu de dat theo.

    ⭐ Khong co truong hinh hoc nao trong `bien_tap_gd2` thi ban ra cung khung
       voi nguon (GD1 khong doi kich thuoc). `hinh_hoc.khung_bien_tap` la MOT
       noi duy nhat tinh dieu nay — `dung_lenh`/`_kiem_khung_ra` dung lai.
    """
    from . import bien_tap as _bt, hinh_hoc as _hh

    if bien_tap_gd2 and set(bien_tap_gd2) & set(_bt.TRUONG_HINH_HOC):
        return _hh.khung_bien_tap(rong_nguon, cao_nguon, bien_tap_gd2)["ra"]
    return rong_nguon, cao_nguon


def _kiem_khung_ra(tt_ra: dict, bien_tap_gd2, rong_nguon: int,
                   cao_nguon: int) -> None:
    """Tep ra phai DUNG kich thuoc `_khung_ra` da khai — logo/lop_phu/phu de
    dat theo no. Chuyen tu `ket_xuat.kiem_tep_ra` xuong day (gd2-diem-anh): GD1
    khong con doi kich thuoc khung nen phep kiem o do khong con y nghia."""
    from . import bien_tap as _bt

    if not (bien_tap_gd2 and set(bien_tap_gd2) & set(_bt.TRUONG_HINH_HOC)):
        return
    rong, cao = _khung_ra(bien_tap_gd2, rong_nguon, cao_nguon)
    that = (int(tt_ra.get("rong") or 0), int(tt_ra.get("cao") or 0))
    if that != (rong, cao):
        raise ket_xuat.KetXuatError(
            _t('Tệp kết quả khung {a}, kế cắt khai {b}.').format(
                a=f"{that[0]}x{that[1]}", b=f"{rong}x{cao}"))


def _ban_do_tu_khoang(khoang, thoi_luong: float):
    from .ban_do_thoi_gian import BanDoThoiGian

    return BanDoThoiGian.tu_khoang(khoang, thoi_luong_nguon=thoi_luong)


def _dua_len(kho: Storage, run, duong: str, vt: str, duoi: str,
             content_type: str) -> str:
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                              stage=pipeline.IMAGE_FINISH, van_tay=vt,
                              duoi=duoi)
    with open(duong, "rb") as f:
        kho.put(khoa, f, content_type=content_type)
    return khoa


def _sinh_srt(kho: Storage, run, *, ho_so_pd, su_kien_ra, thu_muc: Path,
              van_tay: str) -> str:
    """`.srt` cua ban giao tu `ho_so_pd`/`su_kien_ra` DA DOI MOC (`chay()`).

    🔴 **⛔ Khong chep tep `.srt` cua giai doan 1.** Moc cua no nam tren truc GD1;
       sau khi cat, moi moc sau cho noi dau tien deu **tre** dung bang phan da
       cat. Mot tep phu de lech la mot tep khach nhin thay lech ma ⛔ khong loi
       nao bao — dung hinh dang loi ma thu tu moi sinh ra de xoa.

    ⭐ Nhan `ho_so_pd`/`su_kien_ra` da tinh san (`chay()`), ⛔ khong tu doc lai
       COMPOSE hay tu doi moc lan hai: chang DOT vao hinh (`.ass`) va chang
       `.srt` nay CUNG mot nguon su kien — hai lan doi moc doc lap la hai co
       hoi de chung lech nhau.
    """
    from . import phu_de as _pd

    if not (ho_so_pd or {}).get("xuat_srt"):
        return ""
    duong = _pd.viet_tep_srt(ho_so_pd, su_kien_ra, thu_muc)
    if not duong:
        return ""
    return _dua_len(kho, run, duong, van_tay, "srt", "application/x-subrip")


def dung_lenh(duong_vao: str, duong_ra: str, *, khoang, bo_ma_hoa: str,
              ffmpeg_bin: str, thoi_luong_ra: float = 0.0,
              tien_do: bool = True,
              bien_tap: dict | None = None,
              rong_nguon: int = 0, cao_nguon: int = 0,
              ds_logo=(), duong_logo: list[str] | None = None,
              rong_khung: int = 0,
              lop_phu=(), duong_chu: list[str] | None = None,
              cao_khung: int = 0, duong_ass: str = "") -> list[str]:
    """argv cua mot luot cat-noi (+ chang DIEM ANH khi co). ⛔ Khong cham mot
    tep nao.

    ⭐ Tach khoi `chay()` de kiem duoc chuoi lenh ma ⛔ khong phai chay ffmpeg —
       cung khuon voi `ket_xuat.dung_lenh`.

    ⭐ **Cac tham so `bien_tap`/`ds_logo`/`lop_phu`/`duong_ass` moi (gd2-diem-anh,
       25/09) deu tuy chon va mac dinh RONG** — mot lan goi CHI truyen `khoang`/
       `bo_ma_hoa`/`ffmpeg_bin` van ra dung chuoi loc nhu truoc lan tai cau truc
       nay (kiem boi `test_dung_lenh_duong_CAT_map_ca_hai_dong_va_MA_HOA_LAI`).

    ⚠️ **⛔ KHONG co duong `-c:v copy` o day, ke ca khi `khoang` la ca video.**
       `-c copy` chi cat duoc tai keyframe, va GOP cua chinh chuoi nay do duoc la
       8,333 giay (xem `apps/asv_media/manifest.py`) ⇒ mot cho cat lech toi 8
       giay. Mot luot ma hoa lai la gia PHAI tra de cat dung cho.

    ## 🔴 `-t` GHIM do dai ra, va no ⛔ khong phai mot phep lam dep

    `concat` noi N manh, va moi manh bi **luong tu hoa theo khung**: mot manh
    0,3 s o 12 fps la 3,6 khung, nen ffmpeg giao 4 khung (0,333 s). Voi 3 cho noi
    tep ra dai hon TONG SO HOC toi ~0,25 s.

    ⛔ Va do la mot van de THAT: `qc` do T2 voi `DAI_HON_CHO_PHEP_S = 0,01` —
       *"ban ra ⛔ khong bao gio dai hon mong doi"*. Mot ban giao dai hon ban khai
       vi luong tu hoa khung se lam T2 **hong** tren mot tep ⛔ khong sai gi.

    ⇒ Ban khai la HOP DONG, va bo ma hoa phai ton trong no. `-t` ghim do dai ra
      o `thoi_luong_ra` ma ke cat da khai.

    🔴 **Va no ghim tOI MOT KHUNG, ⛔ khong tuyet doi** — do la ca ly do phai ghi
       con so nay ra: ffmpeg giao KHUNG TRON VEN, nen tep ra van dai hon ban khai
       toi `1/fps` (do that: 12 fps, ban khai 23,100 s, tep 23,167 s). Cai `-t`
       dap tat la su **tich luy**: ⛔ khong con mot khung du cho MOI cho noi, chi
       con mot khung cho CA tep.
       ⇒ `qc` T2 cong dung mot khung vao phan *"⛔ khong bao gio dai hon"*, va no
         **do fps tu chinh tep** thay vi go tay (xem `qc.py` khoi T2).

    ⚠️ `0.0` = ⛔ khong ghim. Duong remux (`-c copy`, ⛔ khong cat gi) ⛔ khong can:
       ⛔ khong manh nao duoc noi nen ⛔ khong co luong tu hoa nao.
    """
    if not khoang:
        raise ket_xuat.KetXuatError(
            _t('Kế cắt không còn khoảng nào để giao.'))
    ds_logo = list(ds_logo or ())
    dlogo = list(duong_logo or ())
    if len(dlogo) != len(ds_logo):
        raise ket_xuat.KetXuatError(
            _t('Số tệp logo ({co}) không khớp số logo trong yêu cầu ({can}).')
            .format(co=len(dlogo), can=len(ds_logo)))
    lop_phu = list(lop_phu or ())
    dchu = list(duong_chu or ())
    if len(dchu) != len(lop_phu):
        raise ket_xuat.KetXuatError(
            _t('Số tệp chữ ({co}) không khớp số lớp phủ trong yêu cầu ({can}).')
            .format(co=len(dchu), can=len(lop_phu)))

    cmd = [ffmpeg_bin, "-hide_banner", "-nostdin", "-y"]
    if tien_do:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd += ["-i", duong_vao]
    for _d in dlogo:
        cmd += ["-i", str(_d)]
    if not bo_ma_hoa:
        # ⭐ `bo_ma_hoa` RONG = ⛔ khong cat gi VA ⛔ khong diem anh nao = remux.
        #    Dong hinh+tieng di nguyen ven, ⛔ khong bo loc nao, nen ⛔ khong mot
        #    diem anh nao doi. (`chay()` da chot dieu nay o `co_diem_anh`.)
        cmd += ["-c", "copy"]
    else:
        loc = cdr.loc_cat_hai_dong(
            [(float(b), float(k)) for b, k in khoang],
            bien_tap=bien_tap, rong_nguon=rong_nguon, cao_nguon=cao_nguon,
            ds_logo=ds_logo, rong_khung=rong_khung,
            chi_so_logo_dau=CHI_SO_LOGO_DAU,
            lop_phu=lop_phu, duong_chu=dchu,
            cao_khung=cao_khung, duong_ass=duong_ass)
        cmd += ["-filter_complex", loc,
                "-map", f"[{cdr.NHAN_HINH_RA}]",
                "-map", f"[{cdr.NHAN_TIENG_RA}]"]
        cmd += list(cdr.tham_so(bo_ma_hoa))
        cmd += ["-c:a", "aac", "-b:a", "192k"]
        if float(thoi_luong_ra) > 0:
            cmd += ["-t", f"{float(thoi_luong_ra):.6f}"]
    cmd += ["-movflags", "+faststart", duong_ra]
    return cmd


def van_tay(khoa_gd1: str, ke: kc.KeCat, cua, bo_ma_hoa: str, *,
           ds_logo=(), lop_phu=(), phu_de=None, bien_tap=None) -> str:
    """Van tay tep ra. Doi tep vao HAY doi ke cat HAY doi cach dung lenh deu doi.

    ⛔ `bo_ma_hoa` **o trong** van tay: `libx264` va `h264_nvenc` cho hai tep
       khac nhau tung byte. Thieu no thi mot lan chay duoc cap card se dung lai
       tep CPU cua lan truoc — dung kieu "sot tham so = serve nham" ma
       `assets.py` goi ten.

    ⭐ **`ds_logo`/`lop_phu`/`phu_de`/`bien_tap` moi (gd2-diem-anh, 25/09), tat ca
       tuy chon.** Bon tham so nay THUC THI o day tu lan nay — thieu chung trong
       van tay thi doi mot logo (hay bat lat guong, hay doi kieu phu de) ma van
       tay khong doi, va lan chay lai dung lai tep CU tu cache **im lang**.
       ⛔ `bien_tap` o day chi con truong hinh hoc/mau/guong (`chay()` da loc bo
       `toc_do` — no khong con tac dung o GD2).
    """
    import hashlib

    goi = json.dumps({
        "gd1": khoa_gd1.rsplit("/", 1)[-1][:64],
        "ke_cat": ke.van_tay(),
        "cua_so": [round(float(x), 4) for x in (cua or ())],
        "bo_ma_hoa": bo_ma_hoa,
        "che_do": cdr.PHIEN_BAN_CHE_DO,
        "phien_ban": PHIEN_BAN_HINH_ANH,
        # 🔑 Bam khoa cua logo (khong bam noi dung anh — khoa da la van tay cua
        #    chinh tep do, xem `ban_dung.van_tay_che_do`).
        "logo": [[l.get("khoa"),
                  round(float(l["x"]), 4), round(float(l["y"]), 4),
                  round(float(l["rong"]), 4), round(float(l["do_mo"]), 3),
                  None if l.get("tu_giay") is None else round(float(l["tu_giay"]), 3),
                  None if l.get("den_giay") is None else round(float(l["den_giay"]), 3)]
                 for l in (ds_logo or ())],
        "lop_phu": [[l.get("chu"), l.get("mau"),
                     round(float(l["x"]), 4), round(float(l["y"]), 4),
                     round(float(l["co_chu"]), 4), round(float(l["do_mo"]), 3),
                     bool(l.get("vien")),
                     None if l.get("tu_giay") is None else round(float(l["tu_giay"]), 3),
                     None if l.get("den_giay") is None else round(float(l["den_giay"]), 3)]
                    for l in (lop_phu or ())],
        # ⭐ Ho so phu de NGUYEN VEN (su_kien tren truc bien tap): remap qua
        #    `ke_cat` la mot ham THUAN cua (`su_kien`, `ke`), va `ke_cat` da
        #    nam trong van tay — bam ca ban da doi moc la bam mot thu hai lan.
        "phu_de": phu_de or None,
        "bien_tap": dict(bien_tap) if bien_tap else None,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def _kiem_do_dai(do_duoc: float, mong_doi: float) -> None:
    """Tep ra phai dai dung nhu ban do noi. ⛔ Khong lam tron, ⛔ khong bo qua.

    🔑 Day la cong DUY NHAT chung minh *"hinh va tieng bi cat cung nhau"* da
       thuc su xay ra: `concat=v=1:a=1` cho ra MOT do dai cho ca hai dong, nen
       mot tep ra dai dung `thoi_luong_ra` la mot tep ma hai dong da di cung
       nhau. Lech nghia la mot trong hai dong da khong qua `trim`.
    """
    from .hop_dong_v4 import DUNG_SAI_DO_DAI_S

    if mong_doi > 0 and abs(do_duoc - mong_doi) > DUNG_SAI_DO_DAI_S:
        raise ket_xuat.KetXuatError(_t(
            'Tệp sau khi cắt dài {co:.2f} s nhưng kế cắt nói {can:.2f} s.'
        ).format(co=do_duoc, can=mong_doi))
