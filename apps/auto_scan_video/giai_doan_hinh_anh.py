"""Giai doan IMAGE_FINISH — **GIAI DOAN 2**: thao tac tren MP4 DA XONG.

Hai artifact ra:

    <van_tay>.mp4    ban giao cuoi cung          (kind=video)
    <van_tay>.json   ke cat + bao cao            (kind=json)
    <van_tay>.srt    phu de DA DOI MOC, khi co   (kind=subtitle)

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
   phai di qua mot lop doi mocc. O day phep cat chay tren MOT tep trong do hinh
   va tieng la hai dong cua cung mot dong ho: `loc_cat_hai_dong` `trim` ca hai
   trong CUNG mot `concat`, nen ⛔ khong the co mot doan tieng bi cut.

## ⛔ Ba thu giai doan nay KHONG lam

1. **Khong goi model.** Quyet dinh "canh nao kem" da chot o `EDIT_PLAN`; o day
   chi doc lai va ap tran (`ke_cat`).
2. **Khong tinh lai ke hoach tieng.** Ban phoi cua giai doan 1 da chuan am mot
   lan; `atrim` khong chuan am lan hai.
3. **Khong noi tran 5 %.** Vuot tran la tin hieu tieu chi sai — `ke_cat.kiem`
   **nem**, va giai doan nay de no nem.

## ⚠️ Cai giai doan nay CHUA lam, va noi ra thay vi de nguoi doc tuong

Chu du an liet ke ca `logo · watermark · phu de · lat guong · dich mau · zoom`
cho giai doan 2. Hom nay chung **van chay o `render` cua giai doan 1**.

⭐ Va o thu tu moi dieu do van DUNG, chu khong phai mot lo hong: cac phep do dot
   vao DIEM ANH, nen mot khung hinh mang san logo/chu/phu de cua no. Cat sau do
   bo khung nao thi bo luon lop phu tren khung ay — *"cat cung nhau"* van giu.

🔴 **Cai gia phai tra, do duoc:** mot lan chay co phep doi diem anh se ma hoa
   lai HAI lan (render cua GD1, roi cat o GD2). Chuyen chung xuong day se bo mot
   luot ma hoa, nhung do la mot tai cau truc rieng — va no cham `ban_dung`,
   `ket_xuat.dung_lenh`, `phu_de` (PlayRes theo khung ban ra) va bang gia phang
   theo preset (`gia.py`: *"bien dieu khien la PRESET, khong phai tap tinh
   nang"*). ⛔ Khong gop no vao day de khoi lam nua vo cua mot viec.
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
PHIEN_BAN_HINH_ANH = 1

#: Tran thoi gian MOT luot cat-noi. Cung bac voi `RENDER`: no cung doc va ghi
#: lai toan bo luong hinh. Kep vao ngan sach con lai cua job (`lat_cat`).
TIMEOUT_HINH_ANH = 3600


class ThieuBanRaGd1(ThieuNguon):
    """Chua co MP4 cua giai doan 1 de thao tac."""


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

        if bao:
            bao(10, _t('Đang dựng kế cắt'))

        # ── ⛔ CHI cat o duong CAT, va ⛔ KHONG tin giao dien ─────────────────
        #
        # 🔴 `localize_preserve_picture` hua *"do dai ra bang do dai vao"*
        #    (`hop_dong_v4.DUNG_SAI_DO_DAI_S`) va `THAO_TAC_CHO_PHEP` cua no la
        #    tuple RONG: *"khong phai 'chua lam' — la KHONG DUOC lam"*. Nen ca
        #    phep cat tu dong LAN cua so `cat_dau_cuoi` cua khach deu nam TRONG
        #    mot `if` so `cach` voi che do cat.
        #
        # ⚠️ Va o day ⛔ khong tin giao dien: giao dien an hai tay cam khi preset
        #    la giu hinh, nhung mot yeu cau dung tay van toi duoc.
        #
        # ⭐ Chuyen phep cat xuong giai doan 2 ⛔ KHONG duoc lam no rong ra: mot
        #    lop hua khong cat gi van phai khong cat gi. Day la cho cuoi cung con
        #    canh giu loi hua do.
        cach = cdr.che_do_cho(cd.doc(run).preset)
        ke = kc.chon([], thoi_luong=thoi_luong)      # mac dinh: ⛔ khong cat gi
        khoang = [(0.0, thoi_luong)]
        cua = None
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

        ban_do = _ban_do_tu_khoang(khoang, thoi_luong)
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
        # 🔑 ⛔ Khong cat gi ⇒ **remux**, ⛔ khong ma hoa lai. Mot lan ma hoa lai
        #    "cho nhat quan" tren mot tep khong bi cat la lay mot ban sao nguyen
        #    ven doi lay mot ban kem hon — va no lam preset giu hinh mat dung loi
        #    hua *"hinh anh duoc sao chep nguyen ven"*.
        khong_cat = ban_do.so_cho_noi == 0 and abs(
            float(ban_do.thoi_luong_ra) - thoi_luong) <= 1e-3
        bo_ma_hoa = "" if khong_cat else cdr.chon_bo_ma_hoa(cho_phep_gpu=co_gpu)
        cmd = dung_lenh(duong_vao, duong_ra, khoang=khoang,
                        bo_ma_hoa=bo_ma_hoa,
                        thoi_luong_ra=float(ban_do.thoi_luong_ra),
                        ffmpeg_bin=nhap_media.media.ffmpeg_bin())
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

        vt = van_tay(khoa_gd1, ke, cua, bo_ma_hoa)
        phan = [{"staging_key": _dua_len(kho, run, duong_ra, vt, "mp4",
                                        "video/mp4"),
                 "kind": "video", "duoi": "mp4", "van_tay": vt,
                 "parent_keys": [khoa_gd1]}]

        # ── Phu de: DOI MOC roi sinh lai, ⛔ khong chep tep cua GD1 ──────────
        khoa_srt = _sinh_srt(db, kho, run, ban_do=ban_do, thu_muc=thu_muc,
                             van_tay=vt)
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


def _sinh_srt(db, kho: Storage, run, *, ban_do, thu_muc: Path,
              van_tay: str) -> str:
    """`.srt` cua ban giao: su kien cua COMPOSE, DOI MOC sang truc ban giao.

    🔴 **⛔ Khong chep tep `.srt` cua giai doan 1.** Moc cua no nam tren truc GD1;
       sau khi cat, moi moc sau cho noi dau tien deu **tre** dung bang phan da
       cat. Mot tep phu de lech la mot tep khach nhin thay lech ma ⛔ khong loi
       nao bao — dung hinh dang loi ma thu tu moi sinh ra de xoa.
    """
    from . import phu_de as _pd

    khoa_bd = _khoa_theo_duoi(db, run, pipeline.COMPOSE, ".json")
    if not khoa_bd:
        return ""
    ho_so = (_doc_json(kho, khoa_bd).get("hinh") or {}).get("phu_de") or None
    if not (ho_so or {}).get("xuat_srt"):
        return ""
    su_kien = doi_moc_su_kien((ho_so or {}).get("su_kien") or [], ban_do)
    duong = _pd.viet_tep_srt(ho_so, su_kien, thu_muc)
    if not duong:
        return ""
    return _dua_len(kho, run, duong, van_tay, "srt", "application/x-subrip")


def dung_lenh(duong_vao: str, duong_ra: str, *, khoang, bo_ma_hoa: str,
              ffmpeg_bin: str, thoi_luong_ra: float = 0.0,
              tien_do: bool = True) -> list[str]:
    """argv cua mot luot cat-noi. ⛔ Khong cham mot tep nao.

    ⭐ Tach khoi `chay()` de kiem duoc chuoi lenh ma ⛔ khong phai chay ffmpeg —
       cung khuon voi `ket_xuat.dung_lenh`.

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
    cmd = [ffmpeg_bin, "-hide_banner", "-nostdin", "-y"]
    if tien_do:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd += ["-i", duong_vao]
    if not bo_ma_hoa:
        # ⭐ `bo_ma_hoa` RONG = ⛔ khong cat gi = remux. Hai dong di nguyen ven,
        #    ⛔ khong bo loc nao, nen ⛔ khong mot diem anh nao doi.
        cmd += ["-c", "copy"]
    else:
        loc = cdr.loc_cat_hai_dong([(float(b), float(k)) for b, k in khoang])
        cmd += ["-filter_complex", loc,
                "-map", f"[{cdr.NHAN_HINH_RA}]",
                "-map", f"[{cdr.NHAN_TIENG_RA}]"]
        cmd += list(cdr.tham_so(bo_ma_hoa))
        cmd += ["-c:a", "aac", "-b:a", "192k"]
        if float(thoi_luong_ra) > 0:
            cmd += ["-t", f"{float(thoi_luong_ra):.6f}"]
    cmd += ["-movflags", "+faststart", duong_ra]
    return cmd


def van_tay(khoa_gd1: str, ke: kc.KeCat, cua, bo_ma_hoa: str) -> str:
    """Van tay tep ra. Doi tep vao HAY doi ke cat HAY doi cach dung lenh deu doi.

    ⛔ `bo_ma_hoa` **o trong** van tay: `libx264` va `h264_nvenc` cho hai tep
       khac nhau tung byte. Thieu no thi mot lan chay duoc cap card se dung lai
       tep CPU cua lan truoc — dung kieu "sot tham so = serve nham" ma
       `assets.py` goi ten.
    """
    import hashlib

    goi = json.dumps({
        "gd1": khoa_gd1.rsplit("/", 1)[-1][:64],
        "ke_cat": ke.van_tay(),
        "cua_so": [round(float(x), 4) for x in (cua or ())],
        "bo_ma_hoa": bo_ma_hoa,
        "che_do": cdr.PHIEN_BAN_CHE_DO,
        "phien_ban": PHIEN_BAN_HINH_ANH,
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
