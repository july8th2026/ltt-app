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
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (am_master, assets, ban_do_thoi_gian, hop_dong_v4,
               nhap_media, pipeline, thoi_gian, van_ban)
from .giai_doan_media import ThieuNguon


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
    ban_do = _ban_do(db, kho, run, tong_giay=tong_giay)
    ke_hoach = thoi_gian.lap_ke_hoach(
        tl_vb.get("muc") or [], do_dai, tong_giay=tong_giay, che_do=che_do,
        ban_do=ban_do)

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

    khoa_master, do_duoc, vt_master = _dung_ban_phoi(
        db, kho, run, ke_hoach=ke_hoach, ban_ke=ban_ke, ban_do=ban_do,
        van_tay_ke_hoach=vt, ctx=ctx)
    phan.append({"staging_key": khoa_master, "kind": "audio", "duoi": "wav",
                 "van_tay": vt_master})

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    return {
        "phan": phan,
        "tom_tat": {**thoi_gian.tom_tat(ke_hoach),
                    "ban_do": ban_do.sang_dict(),
                    "so_cho_noi": ban_do.so_cho_noi,
                    "master": do_duoc},
    }


def _ban_do(db, kho: Storage, run, *, tong_giay: float):
    """Ban do thoi gian cua run: preset giu hinh -> dong nhat; preset cat -> tu ban.

    ⭐ Doc tu artifact cua `EDIT_PLAN` chu khong tinh lai: ban bien tap la mot
       **quyet dinh da chot**, va tinh lai mot quyet dinh la mo duong cho hai
       cau tra loi khac nhau cho cung mot cau hoi.
    """
    from . import ban_bien_tap, cai_dat as cd, canh as canh_mod, features

    preset = cd.doc(run).preset
    if preset == hop_dong_v4.PRESET_GIU_HINH:
        # ⛔ Preset giu hinh **sao chep** luong hinh: khong canh nao bi cat, nen
        #    ban do la dong nhat. Doc ban bien tap o day khong sai nhung thua —
        #    va mot duong thua la mot duong co the hong.
        return ban_do_thoi_gian.BanDoThoiGian.giu_nguyen(tong_giay)

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.EDIT_PLAN)
    khoa = next((k for k in (((gd.outputs or {}) if gd else {})
                             .get("khoa_asset") or []) if k.endswith(".json")), "")
    if not khoa:
        raise ThieuDauVao(_t('Chưa có bản biên tập để dựng bản đồ thời gian.'))
    goi = _doc_json(kho, khoa)
    return ban_do_thoi_gian.tu_ban_bien_tap(
        ban_bien_tap.BanBienTap.tu_dict(goi.get("ban") or {}),
        canh_mod.tu_dict(goi.get("chi_muc") or {}),
        thoi_luong_nguon=tong_giay)


def _dung_ban_phoi(db, kho: Storage, run, *, ke_hoach: dict, ban_ke: dict,
                   ban_do, van_tay_ke_hoach: str, ctx=None):
    """Tron nen + cac doan tieng theo ke hoach. Tra `(khoa, do_duoc, van_tay)`."""
    import tempfile

    from . import features
    from .giai_doan_media import _duong_doc_duoc

    s_am = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE)
    khoa_nen = next((k for k in (((s_am.outputs or {}) if s_am else {})
                                 .get("khoa_asset") or []) if k.endswith(".wav")), "")
    if not khoa_nen:
        raise ThieuDauVao(_t('Chưa có bản nền để trộn bản phối.'))

    khoa_theo_ma = {str(d["ma"]): str(d.get("khoa") or "")
                    for d in (ban_ke.get("doan") or [])}
    he_so_theo_ma = {str(d["ma"]): float(d.get("he_so_co_gian") or 1.0)
                     for d in (ban_ke.get("doan") or [])}

    dat = [d for d in (ke_hoach.get("doan") or []) if int(d.get("dai_ms") or 0) > 0]
    if not dat:
        raise ThieuDauVao(_t('Kế hoạch thời gian không còn đoạn nào có tiếng.'))

    tong_giay_ra = float(ban_do.thoi_luong_ra)
    vt = am_master.van_tay_master(
        van_tay_nen=khoa_nen.rsplit("/", 1)[-1][:32],
        van_tay_ke_hoach=van_tay_ke_hoach,
        van_tay_ban_do=ban_do.van_tay(),
        phien_ban_ffmpeg_=nhap_media.phien_ban_ffmpeg())

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
        am_master.tron_cuoi(nen, cac_lo, dich, tong_giay=tong_giay_ra,
                            hoi_huy=hoi_huy)

        do_duoc = am_master.kiem_ban_ra(
            dich, mong_doi_giay=tong_giay_ra,
            dung_sai_giay=hop_dong_v4.DUNG_SAI_DO_DAI_S)

        khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.TIMING_ALIGN, van_tay=vt,
                                   duoi="wav")
        with open(dich, "rb") as f:
            kho.put(khoa, f, content_type="audio/wav")

    return khoa, do_duoc, vt
