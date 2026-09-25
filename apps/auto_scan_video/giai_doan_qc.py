"""Giai doan QC — cong PHAT HANH, khong phai mot buoc ghi chu.

Mot artifact ra:

    qc_report.json    bao cao muoi hai dung sai   (kind=json)

## Vi sao QC duoc phep lam HONG ca lan chay (Prompt 18 muc 2)

Neu QC chi ghi lai roi de lan chay ve `done`, no khong phai mot cong — no la mot
loi binh luan. Khach nhan mot video khong dat chuan kem mot tep JSON noi rang no
khong dat chuan, va khong ai doc tep do.

⇒ QC hong ⇒ giai doan hong ⇒ `_advance` cho ca run ve `error`. Va vi QC la giai
  doan **cuoi**, dieu do dung nghia la: mot lan chay chi `done` khi ban ra da
  qua cong (Prompt 16 muc 9).

⚠️ QC hong la `LoiNguoiGoi` chu khong phai loi tam thoi: chay lai cung mot ban
   render se cho cung mot ket qua do. Thu lai ba lan mot phep do tat dinh la ba
   lan cho vo ich.

## Vi sao no van GHI bao cao khi hong

Bao cao duoc promote **truoc** khi giai doan bao hong. Do la thu khac biet giua
"lan chay cua ban hong" va "lan chay cua ban hong vi tieng to hon chuan 3 dB o
muc T5" — va nguoi can cau thu hai nhat la nguoi ho tro, chu khong phai khach.
"""
from __future__ import annotations

import io
import json
import logging
from pathlib import Path
import tempfile

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, cai_dat, nhap_media, pipeline, qc, tach_tieng
from .giai_doan_media import ThieuNguon, _duong_doc_duoc

log = logging.getLogger(__name__)


class ThieuBanRa(ThieuNguon):
    """Chua co ban render de kiem."""


def _khoa_theo_duoi(db, run, ten_giai_doan: str, duoi: str) -> str:
    from . import features
    s = features.giai_doan_theo_ten(db, run.id, ten_giai_doan)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(duoi)), "") if s else ""


def _doc_json(kho: Storage, khoa: str) -> dict:
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _thoi_luong_mong_doi(ke_hoach: dict, goi_ke_cat: dict) -> float:
    """Do dai (giay) ma TEP DUOC DO phai co, truoc phep chia `toc_do`.

    ⭐ MOT noi tra loi cau hoi nay, va no tra loi tu mot BAN KHAI:

        co ke cat  -> `ke_cat.KeCat.ban_do().thoi_luong_ra`
        khong      -> `tong_ms` cua ke hoach (= do dai nguon, giai doan 1 khong cat)

    ⛔ **⛔ Khong doan tu tep dang do.** Suy do dai mong doi tu chinh tep la bien
       mot phep kiem thanh mot phep tu khang dinh — no se xanh voi MOI tep.

    ⚠️ Doc lai thi kiem lai (I8): `ke_cat.kiem` chay o day nua, nen mot ke cat
       vuot tran 5 % ⛔ khong the di qua cong nay bang cach duoc ghi ra tep.
    """
    from . import ke_cat as _kc

    if goi_ke_cat:
        ke = _kc.KeCat.tu_dict(goi_ke_cat)
        _kc.kiem(ke)
        return float(ke.ban_do().thoi_luong_ra)
    return float(ke_hoach.get("tong_ms") or 0) / 1000.0


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Do ban ra so voi muoi hai dung sai. Tra ve bao cao, KHONG nem.

    ⚠️ Ham nay khong quyet dinh so phan cua lan chay. No do va bao cao; `thi_hanh`
       doc `_qc_hong` roi nem `QcChan` **sau khi** artifact da duoc promote — thu
       tu do la thu giu lai bang chung khi mot lan chay hong.

    ⭐ Ban dau o day co mot lop `QcKhongDat` cho muc dich do, va no chua bao gio
       duoc nem tu bat cu dau. Chinh guard chot-tap-hop cua `test_418` bat duoc:
       mot lop ngoai le khong ai nem van la mot lop phai phan loai, va lan theo
       no thi thay no la ma chet. Da go.
    """
    # 🔴 **Do tep cua IMAGE_FINISH — tep KHACH NHAN (b4 hai giai doan, 25/09).**
    #    `render` giao mot ban trung gian chua qua phep cat cua giai doan 2. Do
    #    ban trung gian la chung nhan mot tep ⛔ khong ai duoc giao, tuc mot cong
    #    ⛔ khong canh giu ban giao.
    khoa_ra = _khoa_theo_duoi(db, run, pipeline.IMAGE_FINISH, ".mp4")
    if not khoa_ra:
        raise ThieuBanRa(_t('Chưa có bản kết xuất để kiểm.'))
    # ⭐ Ke cat nam trong `outputs` cua `image_finish`, ⛔ khong thanh artifact:
    #    moi artifact cua giai doan do la BAN GIAO (`han=None`), va mot bao cao
    #    van hanh ⛔ khong duoc nam trong kho cua khach mai mai.
    from . import features as _ft
    _s_if = _ft.giai_doan_theo_ten(db, run.id, pipeline.IMAGE_FINISH)
    _out_if = (_s_if.outputs or {}) if _s_if else {}
    goi_kc = _out_if.get("ke_cat") or {}
    khoang_gd2 = _out_if.get("khoang_giu") or ()
    khoa_kh = _khoa_theo_duoi(db, run, pipeline.TIMING_ALIGN, ".json")
    khoa_ke = _khoa_theo_duoi(db, run, pipeline.VOICE_SYNTHESIS, ".json")
    khoa_ban = _khoa_theo_duoi(db, run, pipeline.COMPOSE, ".json")
    if not (khoa_kh and khoa_ke and khoa_ban):
        raise ThieuBanRa(_t('Chưa đủ tài liệu thượng nguồn để kiểm chất lượng.'))

    bao = None
    if ctx is not None and getattr(ctx, "progress", None):
        bao = ctx.progress

    ke_hoach = _doc_json(kho, khoa_kh)
    ban_ke = _doc_json(kho, khoa_ke)
    ban_dung = _doc_json(kho, khoa_ban)

    if bao:
        bao(15, _t('Đang đo bản kết xuất'))

    with tempfile.TemporaryDirectory(
            prefix=f"asv-qc-{str(run.id)[:12]}-") as tam:
        thu_muc = Path(tam)
        duong_ra = _duong_doc_duoc(kho, khoa_ra, thu_muc)
        duong_nguon = _duong_doc_duoc(kho, run.source_key, thu_muc)

        tt_ra = nhap_media.soi(duong_ra)
        tt_nguon = nhap_media.soi(duong_nguon)

        if bao:
            bao(45, _t('Đang đo âm lượng'))
        am_luong = tach_tieng.do_am_luong(duong_ra)

        # ── Che do render quyet dinh QC do CAI GI ──────────────────────────
        #
        # 🔑 Doc tu BAN DUNG, khong suy lai tu `settings`: ban dung la thu da
        #    thuc su duoc render, va neu hai nguon lech nhau thi cai dung la cai
        #    da chay. Suy lai o day se cho QC do mot lan chay khac voi lan chay
        #    that.
        from . import che_do_render as cdr

        cach = str((ban_dung.get("hinh") or {}).get("cach_render") or cdr.SAO_CHEP)

        # ── Thoi luong MONG DOI (b4 hai giai doan, 25/09) ───────────────────
        #
        # 🔴 Truoc b4, dong nay doc `ke_hoach["ban_do"].thoi_luong_ra` — ngan hon
        #    nguon dung bang phan `edit_plan` da cat. Nay giai doan 1 ⛔ KHONG cat
        #    gi, nen mong doi la **do dai nguon**, cho CA HAI preset. Cat canh o
        #    giai doan 2 (`giai_doan_hinh_anh`), va cong nay do dung tep ma giai
        #    doan 2 giao.
        #
        # ⭐ asv-final: truc bien tap -> ban ra la mot phep chia cho `toc_do`.
        from .bien_tap import moc_ban_ra
        mong_doi = moc_ban_ra(
            _thoi_luong_mong_doi(ke_hoach, goi_kc),
            (ban_dung.get("hinh") or {}).get("bien_tap"))

        bam_ra = bam_nguon = ""
        if cach != cdr.CAT_MA_HOA_LAI:
            if bao:
                bao(70, _t('Đang đối chiếu luồng hình'))
            # T3 — bam RIENG luong hinh. Neu ffmpeg khong bam duoc thi T3 thanh
            # `khong_ap_dung` chu khong thanh `hong`: khong do duoc khac voi do
            # ra sai.
            #
            # ⭐ Chi bam o che do SAO CHEP. O che do cat, bam la mot phep tinh
            #    chac chan khong khop — ton thoi gian de tra loi mot cau hoi ta
            #    da biet cau tra loi.
            try:
                bam_ra = qc.bam_luong_hinh(duong_ra)
                bam_nguon = qc.bam_luong_hinh(duong_nguon)
            except Exception as exc:  # noqa: BLE001 - khong do duoc != do ra sai
                log.warning("qc: khong bam duoc luong hinh (%s: %s)",
                            type(exc).__name__, exc)
                bam_ra = bam_nguon = ""

        if bao:
            bao(75, _t('Đang kiểm bản ra có hình'))
        # ── T13 + T17: MOT luot giai ma ban ra, mot luot giai ma nguon ────────
        #
        # ⭐ Nguon chi can do khi luong hinh KHONG giong nguon tung bit: o preset
        #    giu hinh ma bam khop (T3), luong hinh ra CHINH LA luong hinh nguon,
        #    nen so do cua nguon = so do cua ban ra — giai ma lan hai la tra
        #    tien cho mot cau tra loi da biet.
        hinh_ra = hinh_nguon = None
        try:
            hinh_ra = qc.do_hinh(
                duong_ra, thoi_luong=float(tt_ra.get("thoi_luong") or 0.0))
            if bam_ra and bam_ra == bam_nguon:
                hinh_nguon = {"den_s": hinh_ra["den_s"],
                              "dong_s": hinh_ra["dong_s"]}
            else:
                hinh_nguon = qc.do_hinh(
                    duong_nguon,
                    thoi_luong=float(tt_nguon.get("thoi_luong") or 0.0))
        except Exception as exc:      # noqa: BLE001 - khong do duoc != do ra sai
            log.warning("qc: khong do duoc hinh (%s: %s)",
                        type(exc).__name__, exc)

        # ── T18: VMAF — chi preset cat (ma hoa lai) ──────────────────────────
        vmaf = None
        if cach == cdr.CAT_MA_HOA_LAI:
            if bao:
                bao(85, _t('Đang đo chất lượng hình (VMAF)'))
            vmaf = _do_vmaf(kho, ban_dung.get("hinh") or {}, thu_muc,
                            duong_nguon=duong_nguon, duong_ra=duong_ra,
                            tt_ra=tt_ra, khoang_gd2=khoang_gd2)

        bao_cao = qc.kiem(
            tt_ra=tt_ra, tt_nguon=tt_nguon, am_luong=am_luong,
            ke_hoach=ke_hoach, ban_ke_tieng=ban_ke,
            ban_dung_lop=(ban_dung.get("tieng") or {}).get("lop") or [],
            bam_ra=bam_ra, bam_nguon=bam_nguon,
            # 🔴 **Sua loi o pha 07, khong phai mot doi ten.**
            #
            #    Dong nay tung mac dinh `""` trong khi
            #    `giai_doan_thoi_gian` mac dinh `"fit_original"`. Tuc
            #    mot lan chay thieu khoa se CHAY o `fit_original` con
            #    **bang chung QC ghi rong** — hai cau tra loi khac nhau
            #    cho cung mot cau hoi, va khong cho nao bao loi vi ca hai
            #    deu tim thay mot gia tri hop le cua rieng minh.
            #
            # ⭐ Ban vá lay gia tri ma duong ong THUC SU dung, nen bang
            #    chung thanh dung thay vi thanh khac.
            che_do_thoi_gian=cai_dat.doc(run).timing_mode,
            che_do_render=cach, thoi_luong_mong_doi=mong_doi,
            hinh_ra=hinh_ra, hinh_nguon=hinh_nguon, vmaf=vmaf,
            # ⭐ V6 pha 27. T14/T15 doc tu day: chinh sach render da khai va
            #    su kien phu de DA CHOT. Khong truyen thi ca hai luon tra
            #    `KHONG_AP_DUNG` — mot phep kiem ton tai ma khong ai di qua,
            #    dung hang `nang-luc-co-nhung-khong-ai-di-tren-duong`.
            ban_hinh=(ban_dung.get("hinh") or {}))

    goi = json.dumps(bao_cao, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = _van_tay(kho, khoa_ra, khoa_kh)
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.QC, van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if bao:
        bao(95, _t('Đang lưu báo cáo'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt, "parent_keys": [khoa_ra]}],
        "tom_tat": qc.tom_tat(bao_cao),
        # 🔑 Nguoi goi (`thi_hanh`) promote bao cao TRUOC roi moi doc co nay va
        #    nem. Nho vay mot lan chay hong van de lai bang chung ve VI SAO.
        "_qc_hong": bao_cao["muc_hong"],
    }


def _do_vmaf(kho: Storage, hinh: dict, thu_muc: Path, *, duong_nguon: str,
             duong_ra: str, tt_ra: dict, khoang_gd2=()) -> dict:
    """Dung lai DUNG tep phu cua RENDER (chu, logo, `.ass`) roi do VMAF.

    ⭐ Ba tep phu di cung ba ham `giai_doan_ket_xuat` dung — cung dau vao, cung
       chuoi loc (`qc.loc_tham_chieu`, `test_2012` chot bang nhau voi render).
    ⛔ Khong do duoc => `{"loi": ...}` => T18 `khong_kha_dung`; khong lui ve
       mot uoc luong tu che.
    """
    from . import lop_phu as _lp, phu_de as _pd
    from .giai_doan_ket_xuat import _tai_ve

    try:
        tm = thu_muc / "vmaf"
        tm.mkdir(exist_ok=True)
        duong_chu = _lp.viet_tep_chu(list(hinh.get("lop_phu") or ()), tm)
        duong_logo = []
        for i, lg in enumerate(hinh.get("logo") or ()):
            khoa = str(lg["khoa"])
            duong_logo.append(_tai_ve(
                kho, khoa, tm / f"logo{i}{Path(khoa).suffix or '.png'}"))
        ho_so_pd = hinh.get("phu_de") or None
        duong_ass = _pd.viet_tep_ass(
            ho_so_pd, (ho_so_pd or {}).get("su_kien") or [], tm,
            rong=int(hinh.get("rong_khung") or 0),
            cao=int(hinh.get("cao_khung") or 0))
        # ⭐ Tham chieu chay qua CUNG phep cat cua giai doan 2 — xem
        #    `qc.loc_tham_chieu`. Thieu no thi hai ben lech tung khung va T18
        #    bao `hong` du bo ma hoa khong lam gi sai.
        loc = qc.loc_tham_chieu(hinh, duong_chu=duong_chu, duong_ass=duong_ass,
                                khoang_giu=khoang_gd2)
        return qc.do_vmaf(duong_nguon=duong_nguon, duong_ra=duong_ra,
                          loc_hinh=loc, duong_logo=duong_logo,
                          rong=int(tt_ra.get("rong") or 0),
                          cao=int(tt_ra.get("cao") or 0), thu_muc=str(tm))
    except Exception as exc:          # noqa: BLE001 - khong do duoc != do ra sai
        log.warning("qc: khong do duoc VMAF (%s: %s)", type(exc).__name__, exc)
        return {"loi": f"{type(exc).__name__}: {exc}"}


def _van_tay(kho: Storage, khoa_ra: str, khoa_kh: str) -> str:
    """Doi ban render, doi ke hoach, HAY doi nguong QC deu doi van tay (O13)."""
    import hashlib

    with kho.open(khoa_ra) as f:
        cs_ra = assets.bam(f.read())
    with kho.open(khoa_kh) as f:
        cs_kh = assets.bam(f.read())
    goi = json.dumps({"ra": cs_ra, "ke_hoach": cs_kh,
                      "qc": qc.PHIEN_BAN_QC}, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()
