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
    khoa_ra = _khoa_theo_duoi(db, run, pipeline.RENDER, ".mp4")
    if not khoa_ra:
        raise ThieuBanRa(_t('Chưa có bản kết xuất để kiểm.'))
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
        from . import ban_do_thoi_gian, che_do_render as cdr

        cach = str((ban_dung.get("hinh") or {}).get("cach_render") or cdr.SAO_CHEP)

        # Thoi luong MONG DOI: preset cat ngan hon nguon dung bang phan da cat,
        # va do la muc dich cua san pham chu khong phai mot khiem khuyet.
        bdo = ban_do_thoi_gian.BanDoThoiGian.tu_dict(ke_hoach.get("ban_do") or {})
        mong_doi = float(bdo.thoi_luong_ra or 0.0)

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
            bao(80, _t('Đang kiểm bản ra có hình'))
        try:
            do_sang = qc.do_sang_trung_binh(
                duong_ra, thoi_luong=float(tt_ra.get("thoi_luong") or 0.0))
        except Exception as exc:      # noqa: BLE001 - khong do duoc != do ra sai
            log.warning("qc: khong do duoc do sang (%s: %s)",
                        type(exc).__name__, exc)
            do_sang = None

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
            do_sang=do_sang)

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
