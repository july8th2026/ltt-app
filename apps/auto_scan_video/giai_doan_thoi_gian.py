"""Giai doan TIMING_ALIGN — lap ke hoach dat tung doan tieng len truc thoi gian.

Mot artifact ra:

    timing_plan.json   ke hoach dat doan   (kind=json)

## 🔴 Pha 16 doi mot cau o day, va ly do dang ghi lai

Ban truoc noi: *"giai doan nay khong cham mot tep am thanh nao"*. Nay no ra HAI
artifact: ke hoach **truoc**, roi ban phoi am dung theo ke hoach do.

⭐ Va cau cu van dung o cho quan trong nhat: quyet dinh thoi gian **khong** bi
   giau ben trong mot phep ghep. Ke hoach duoc dung, kiem va **luu** truoc; ban
   phoi chi la mot phep thi hanh tat dinh cua no. Doc lai ke hoach van biet duoc
   moi doan nam o dau ma khong phai mo mot tep wav nao.

⛔ Cai KHONG doi: khong render hinh o day, va khong mot loi goi model nao. Pha 16
   cam ca hai bang chu.

⭐ Nho vay ke hoach doc duoc, kiem duoc va **sua duoc** ma khong phai render lai:
   mot lan chay lai chi ton vai mili-giay o phan ke hoach.

Thi hanh `ADR-003-mo-hinh-thoi-gian.md`.
"""
from __future__ import annotations

import io
import json
import logging
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (am_master, assets, hop_dong_v4, nan_thoi_luong, nhap_media,
               pipeline, thoi_gian, van_ban)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)


class ThieuDauVao(ThieuNguon):
    """Chua co ban dich hoac chua co tieng de lap ke hoach."""


def _doc_json(kho: Storage, khoa: str) -> dict:
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _dau_vao(db, kho: Storage, run) -> tuple[dict, dict, str, str]:
    """`(van_ban_da_xu_ly, ban_ke_tieng, checksum_van_ban, checksum_ban_ke)`."""
    from . import features

    s_vb = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    khoa_vb = next((k for k in ((s_vb.outputs or {}).get("khoa_asset") or [])
                    if k.endswith(".json")), "") if s_vb else ""
    if not khoa_vb:
        raise ThieuDauVao(_t('Chưa có bản dịch để lập kế hoạch thời gian.'))

    s_g = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    khoa_ke = next((k for k in ((s_g.outputs or {}).get("khoa_asset") or [])
                    if k.endswith(".json")), "") if s_g else ""
    if not khoa_ke:
        raise ThieuDauVao(_t('Chưa có bản kê tiếng để lập kế hoạch thời gian.'))

    tl_vb = _doc_json(kho, khoa_vb)
    van_ban.kiem(tl_vb)
    ban_ke = _doc_json(kho, khoa_ke)

    with kho.open(khoa_vb) as f:
        cs_vb = assets.bam(f.read())
    with kho.open(khoa_ke) as f:
        cs_ke = assets.bam(f.read())
    return tl_vb, ban_ke, cs_vb, cs_ke


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc ban dich + do dai tieng THAT -> ke hoach dat doan."""
    tl_vb, ban_ke, cs_vb, cs_ke = _dau_vao(db, kho, run)

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(20, _t('Đang lập kế hoạch thời gian'))

    # 🔑 Do dai THAT cua tung tep tieng, khong phai do dai uoc tinh tu so ky tu.
    #    Mot phep uoc o day se lech, va lech tich luy — dung thu ma ca mo hinh
    #    no trong ADR-003 sinh ra de kiem soat.
    do_dai = {str(d["ma"]): float(d.get("giay") or 0.0)
              for d in (ban_ke.get("doan") or [])}

    # Thoi luong nguon lay tu ho so soi cua MEDIA_PREPARE.
    from . import features
    s_media = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    tong_giay = float((s_media.outputs or {}).get("thoi_luong") or 0.0) if s_media else 0.0
    if tong_giay <= 0:
        raise ThieuDauVao(_t('Không biết thời lượng video nguồn.'))

    # ⛔ Truoc pha 07 dong nay chep CUNG chuoi `"fit_original"` — ban thu
    #    BA cua `gia.CHE_DO_MAC_DINH`, va mot trong ba ban do da lech.
    from . import cai_dat as cd
    che_do = cd.doc(run).timing_mode
    # ⭐ Khe da GOP (`nan_thoi_luong.gop_khe`): MOT tep tieng, NHIEU `ma`. Cac
    #    `ma` di theo phai duoc dat LIEN NHAU thay vi o moc goc cua chung —
    #    `thoi_gian.lap_ke_hoach` doi hoi `nhom_gop` de biet dieu do. Rong khi
    #    lan chay khong gop gi, va khi do ke hoach khong doi mot mili-giay.
    # 🔴 **KHONG mot tham so nao doc preset o day (b4 hai giai doan, 25/09).**
    #    Giai doan 1 giao MP4 tieng Viet **toan bo do dai goc**, nen hai preset
    #    di y het mot duong voice. Cat canh nam o giai doan 2 (`ke_cat.py`), sau
    #    render, tren mot tep da xong. `test_4801` ghim menh de nay bang may.
    ke_hoach = thoi_gian.lap_ke_hoach(
        tl_vb.get("muc") or [], do_dai, tong_giay=tong_giay, che_do=che_do,
        nhom_gop=nan_thoi_luong.nhom_theo_ma(ban_ke))

    goi = json.dumps(ke_hoach, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = thoi_gian.van_tay_ke_hoach(checksum_van_ban=cs_vb, ban_ke_tieng=cs_ke,
                                    che_do=che_do)

    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.TIMING_ALIGN, van_tay=vt,
                               duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")
    phan = [{"staging_key": khoa, "kind": "json", "duoi": "json", "van_tay": vt}]

    # ── Ban phoi am, SAU khi ke hoach da ben ───────────────────────────────
    #
    # 🔑 Thu tu la mot phan cua hop dong (pha 16 muc 4): ke hoach truoc, ban phoi
    #    sau. Neu ban phoi hong thi ke hoach van con — va lan chay lai khong phai
    #    tinh lai gi ca, chi tron lai.
    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(50, _t('Đang trộn bản phối'))

    khoa_master, do_duoc, vt_master, he_so_da_kep = _dung_ban_phoi(
        db, kho, run, ke_hoach=ke_hoach, ban_ke=ban_ke, tong_giay=tong_giay,
        van_tay_ke_hoach=vt, ctx=ctx)
    phan.append({"staging_key": khoa_master, "kind": "audio", "duoi": "wav",
                 "van_tay": vt_master})

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    # ⛔ `ban_do` / `so_cho_noi` DA ROI KHOI bao cao nay: o giai doan 1 khong co
    #    cho noi nao — luong hinh di nguyen ven. Hai khoa luon bang `0`/dong nhat
    #    se lam moi bao cao van hanh noi rang "da kiem cho noi" trong khi khong
    #    cho noi nao ton tai. Giai doan 2 khai chung (`ke_cat.tom_tat`).
    tom_tat = {**thoi_gian.tom_tat(ke_hoach), "master": do_duoc}
    # ⛔ Chi ghi khoa nay khi CO kep (N-55) — mot danh sach rong luon co mat se
    #    lam moi bao cao cu (chua tung kep) khac bao cao moi mot cach vo nghia.
    if he_so_da_kep:
        tom_tat["he_so_co_gian_da_kep"] = he_so_da_kep
    return {"phan": phan, "tom_tat": tom_tat}


def _dung_ban_phoi(db, kho: Storage, run, *, ke_hoach: dict, ban_ke: dict,
                   tong_giay: float, van_tay_ke_hoach: str, ctx=None):
    """Tron nen + cac doan tieng theo ke hoach.

    Tra `(khoa, do_duoc, van_tay, da_kep)` — `da_kep` (N-55) liet ke moi doan
    ma `he_so_co_gian` bi kep xuong tran thiet ke truoc khi vao `atempo`."""
    import tempfile

    from . import features
    from .giai_doan_media import _duong_doc_duoc

    s_am = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE)
    khoa_nen = next((k for k in (((s_am.outputs or {}) if s_am else {})
                                 .get("khoa_asset") or []) if k.endswith(".wav")), "")
    if not khoa_nen:
        raise ThieuDauVao(_t('Chưa có bản nền để trộn bản phối.'))

    # 🔴 **`tep_theo_ma`, ⛔ KHONG mot dict comprehension o day.** Voi khe da gop
    #    thi 2-4 `ma` tro vao CUNG mot tep tieng; dat theo tung `ma` se tron tep
    #    ay 2-4 lan — nghe thanh tieng vang, ⛔ khong nem, ⛔ khong log. Ham ay chi
    #    tra ve nhung dong SO HUU mot tep (`nan_thoi_luong.la_dong_theo_sau`).
    khoa_theo_ma = nan_thoi_luong.tep_theo_ma(ban_ke)
    # 🔴 **N-55 (25/09): `he_so_co_gian` cua mot doan `CAN_SUA` co the vuot xa
    #    tran thiet ke.** `nan_cho_vua.ket_luan()` GHI he so THAT SU CAN cho
    #    doan `CAN_SUA` — dung y, do la con so vong sua (`sua_chua`, chay khi
    #    `LTT_ASV_QC_AI=1`) doc de biet can rut gon bao nhieu. ⛔ Nhung
    #    `LTT_ASV_QC_AI` TAT theo mac dinh (quyet dinh gia,
    #    `giai_doan_qc_ai.py`), nen KHONG lan chay nao chac chan di qua vong
    #    sua truoc khi toi day. Mot he so vuot ca tran cung `atempo`
    #    (`am_master.py`: `[0,5; 100]` MOT lan goi, KHONG chain) lam
    #    `timing_align` chet cung ca lan chay — vi mot doan CHUA duoc sua.
    #
    # ⭐ Kep o TRAN THIET KE (`thoi_gian.TRAN_TANG_TOC`, khong phai tran cung
    #    ky thuat cua `atempo`): vuot tran thiet ke la am thanh da bat dau
    #    mat chat luong nghe duoc theo dung tai lieu tham khao (`thoi_gian.py`
    #    §doc). ⛔ **KHONG im lang**: ghi log CANH BAO + kep vao
    #    `tom_tat.he_so_co_gian_da_kep` (giai doan nay tra ve trong outputs)
    #    de ai doc bao cao van hanh thay duoc — mot doan bi kep se ra tieng
    #    LECH thoi luong ke hoach thay vi lam CHET ca lan chay, va dau vet o
    #    lai trong so cai.
    he_so_theo_ma: dict[str, float] = {}
    da_kep: list[dict] = []
    for d in (ban_ke.get("doan") or []):
        # ⛔ Dong DI THEO mang cung `he_so_co_gian` voi dong dau (mot tep, mot
        #    lan `atempo`) — kep no lan thu hai chi in canh bao trung lap.
        if nan_thoi_luong.la_dong_theo_sau(d):
            continue
        ma = str(d["ma"])
        h = float(d.get("he_so_co_gian") or 1.0)
        h_kep = max(1.0 / thoi_gian.TRAN_TANG_TOC,
                   min(thoi_gian.TRAN_TANG_TOC, h))
        if abs(h_kep - h) > 1e-6:
            log.warning(
                "asv timing_align: doan %s co he_so_co_gian=%.4f vuot tran "
                "thiet ke %.2f (CAN_SUA chua duoc vong sua xu ly - QC_AI co "
                "the dang tat) - kep xuong %.4f de lan chay khong chet",
                ma, h, thoi_gian.TRAN_TANG_TOC, h_kep)
            da_kep.append({"ma": ma, "he_so_can": round(h, 4),
                           "he_so_da_kep": round(h_kep, 4)})
        he_so_theo_ma[ma] = h_kep

    # ⛔ Loai cac `ma` DI THEO bang mot truong TUONG MINH (`nhom_theo_ma`), ⛔ KHONG
    #    bang "vang mat khoi `khoa_theo_ma`": hai chuyen khac han nhau va chi mot
    #    trong hai duoc phep im lang.
    #      di theo    -> tep cua nhom da co mot lop, bo qua  (binh thuong)
    #      thieu khoa -> NEM `Doan {ma} chua co tep tieng`   (khiem khuyet)
    #    Loc bang `in khoa_theo_ma` se bien ca hai thanh mot, va ca thu hai bien
    #    thanh mot doan tieng bi vut AM THAM.
    di_theo = nan_thoi_luong.nhom_theo_ma(ban_ke)
    dat = [d for d in (ke_hoach.get("doan") or [])
           if int(d.get("dai_ms") or 0) > 0 and str(d["ma"]) not in di_theo]
    if not dat:
        raise ThieuDauVao(_t('Kế hoạch thời gian không còn đoạn nào có tiếng.'))

    # 🔑 `tong_giay` la do dai NGUON, va o giai doan 1 do cung la do dai ban
    #    phoi: khong canh nao bi cat. Truoc b4 dong nay doc `ban_do.thoi_luong_ra`
    #    — mot con so NHO hon khi preset cat — va do la dung SU GHEP NOI ma thu
    #    tu moi xoa bo.
    tong_giay_ra = float(tong_giay)
    # V6 pha 23: ho so am thanh cua khach — vao van tay VA vao chuoi tron.
    from . import am_thanh, cai_dat as cd
    am = am_thanh.tu_cai_dat(cd.doc(run).am_thanh)
    vt = am_master.van_tay_master(
        van_tay_nen=khoa_nen.rsplit("/", 1)[-1][:32],
        van_tay_ke_hoach=van_tay_ke_hoach,
        phien_ban_ffmpeg_=nhap_media.phien_ban_ffmpeg(),
        am_thanh=am)

    hoi_huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None

    with tempfile.TemporaryDirectory(prefix="asv-master-") as tam:
        thu_muc = Path(tam)
        nen = _duong_doc_duoc(kho, khoa_nen, thu_muc)

        cac_lo = []
        for n_lo, (i, j) in enumerate(am_master.chia_lo(len(dat))):
            duong, moc, he_so = [], [], []
            for d in dat[i:j]:
                ma = str(d["ma"])
                k = khoa_theo_ma.get(ma)
                if not k:
                    raise ThieuDauVao(
                        _t('Đoạn {ma} chưa có tệp tiếng.').format(ma=ma))
                duong.append(_duong_doc_duoc(kho, k, thu_muc / f"t{n_lo}_{ma}"))
                moc.append(int(d["dat_tai_ms"]))
                he_so.append(he_so_theo_ma.get(ma, 1.0))
            cac_lo.append(am_master.tron_lo(
                duong, moc, he_so, str(thu_muc / f"lo_{n_lo}.wav"),
                tong_giay=tong_giay_ra, hoi_huy=hoi_huy))

        dich = str(thu_muc / "master.wav")
        # ⭐ asv-final R-03: `ghim` hung bao cao ghim tran (dinh that cua BAN
        #    GIAO, da do bang chinh tham so ma hoa cua `ket_xuat`) va di thang
        #    sang `kiem_ban_ra` — do mot lan, ghi vao ho so giai doan.
        ghim: dict = {}
        am_master.tron_cuoi(nen, cac_lo, dich, tong_giay=tong_giay_ra,
                            hoi_huy=hoi_huy, am=am, ghim=ghim)

        do_duoc = am_master.kiem_ban_ra(
            dich, mong_doi_giay=tong_giay_ra,
            dung_sai_giay=hop_dong_v4.DUNG_SAI_DO_DAI_S, ghim=ghim)
        # ⭐ Ghi thu DA AP, khong chi thu khach chon: fade bi cat theo do dai ban
        #    phoi (`fade_ap_dung`), va mot lan cat khong ghi lai la mot lan lang le.
        fv, fr = am_master.fade_ap_dung(am, tong_giay_ra)
        do_duoc["am_thanh"] = {**am, "fade_vao": fv, "fade_ra": fr}

        khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.TIMING_ALIGN, van_tay=vt,
                                   duoi="wav")
        with open(dich, "rb") as f:
            kho.put(khoa, f, content_type="audio/wav")

    return khoa, do_duoc, vt, da_kep
