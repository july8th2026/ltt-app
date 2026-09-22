"""Giai doan QC bang AI — nua thu hai cua pha 19, va no MAC DINH TAT.

## Vi sao mot giai doan rieng, khong nhet vao `qc`

`qc` thuoc `asv_media` (nang luc `ffmpeg` + `gpu`). Duong nay goi model, tuc can
`api` — cung nang luc ma `edit_plan` va `content_process` dung, va ca hai deu
thuoc `auto_scan_video`. Nhet mot loi goi model vao mot giai doan cua app khac la
pha phep dinh tuyen ma `test_402` chot.

## ⛔ MAC DINH TAT, va cong tat khong nam trong `settings` cua khach

    LTT_ASV_QC_AI=1     bat, o cap NGUOI VAN HANH

🔴 Day la mot khoan chi **moi lan chay**. Bat no la mot quyet dinh ve GIA, khong
   phai mot quyet dinh ky thuat — nen no khong duoc lang le bat theo mot ban va.

⭐ Va cong tat la BIEN MOI TRUONG chu khong phai mot truong trong `settings`: mot
   truong trong `settings` la thu khach gui len, tuc khach tu bat duoc mot thu
   chua duoc dinh gia. Bien moi truong thi chi nguoi van hanh dat duoc.

⚠️ Khi TAT, giai doan van CHAY va van `succeeded` — no chi khong goi model va
   khong ton gi. Bo qua han mot giai doan se lam `len(da_xong) != len(CHUOI)` va
   lan chay khong bao gio ve `done`.

## Pham vi hien tai: CHI ngu nghia

Pha 19 doi ba loai QC. Day la mot:

    ngu nghia   dich sai      -> `content_process`   ✅ lam o day
    giong noi   doc sai       -> `voice_synthesis`   ⛔ can ASR tren ban ra
    hinh        cat sai       -> `edit_plan`         ⛔ can rut khung quanh cho noi

⭐ Ngu nghia truoc vi no la loai vong sua xu ly TOT NHAT: `sua_chua` noi ro mot
   ban dich sai **chi** sua duoc bang cach dich lai — doc lai bao nhieu lan cung
   ra cung mot y sai. Hai loai kia se them sau, cung khuon.
"""
from __future__ import annotations

import io
import json
import logging
import os

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import ai, assets, lat_cat, pipeline, qc_ai
from .giai_doan_qc import ThieuBanRa, _doc_json, _khoa_theo_duoi

log = logging.getLogger(__name__)

#: Doi khi doi loi nhac hoac luoc do. Vao van tay bao cao.
PHIEN_BAN_QC_AI_GD = 1

#: Cong tat, o cap nguoi van hanh. Xem docstring dau tep.
BIEN_BAT = "LTT_ASV_QC_AI"


def bat() -> bool:
    """QC bang AI co duoc bat khong. **Mac dinh TAT.**

    ⛔ Doi dung `"1"`, khong nhan `"true"`/`"yes"`: mot cong tat tieu tien phai
       kho bat mot cach co chu dich, va mot tap gia tri hep thi khong ai vo tinh
       bat no bang mot chuoi rong khac.
    """
    return str(os.environ.get(BIEN_BAT, "")).strip() == "1"


def _cac_muc(ban_dich: dict) -> list[dict]:
    """Cac muc long tieng, moi muc `{ma, goc, chu}` — dung hinh dang QC doi.

    ⭐ Tai lieu long tieng **da mang ca hai ve**: `goc` (cau nguon) va `chu` (cau
       tieng Viet), cung mot ban ghi. Nen QC ngu nghia khong phai doi chieu cheo
       hai artifact — mot cho it di la mot cho it lech di.
    """
    ra = []
    for m in (ban_dich or {}).get("muc") or []:
        ma = str(m.get("ma") or "")
        goc = str(m.get("goc") or "")
        chu = str(m.get("chu") or "")
        if ma and goc and chu:
            ra.append({"ma": ma, "goc": goc, "chu": chu})
    return ra


def _ghi_bao_cao(kho: Storage, *, run, bao_cao: dict, cha: list[str]) -> dict:
    """Ghi bao cao ra kho va tra ve phan `phan` cua ket qua giai doan.

    🔑 Goi o **moi** duong ra, ke ca khi QC dang TAT. `test_403` doi moi giai
       doan ket thuc bang mot asset ref that va kiem duoc, va doi do dung: mot
       giai doan khong de lai gi thi khong ai doi chieu duoc no da chay hay
       chua sau khi lan chay ket thuc.

    ⭐ Va no lam manh them dieu docstring dau tep noi: ly do "chua soat" khong
       chi nam trong `stage.outputs` (trang thai CSDL) ma nam trong chinh chuoi
       bang chung duoc giao. Mot lan chay khong bat QC van tra loi duoc cau
       "da soat chua" tu artifact, khong phai tu mot bang trong CSDL.
    """
    goi = json.dumps(bao_cao, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = assets.bam(goi)
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.QC_AI, van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")
    return {"staging_key": khoa, "kind": "json", "duoi": "json",
            "van_tay": vt, "parent_keys": list(cha)}


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Soat ban dich bang model. Tra ve bao cao; KHONG nem khi co muc khong dat.

    ⚠️ Khong nem, va do la co y: mot ban dich lech y **khong** phai mot lan chay
       hong — no la mot don vi can lam lai. `jobs._sua_chua_neu_can` doc ket qua
       nay va quyet dinh sua; nem o day se giet lan chay truoc khi vong sua kip
       chay, dung loi ma bo chay hang doi vua bi sua vi no.
    """
    bao = None
    if ctx is not None and getattr(ctx, "progress", None):
        bao = ctx.progress

    if not bat():
        # ⭐ Van `succeeded`, van ghi ro LY DO. Mot giai doan xanh khong noi gi la
        #    mot giai doan khong phan biet duoc "da soat, khong co loi" voi
        #    "chua soat lan nao" — va hai cau do dan toi hai quyet dinh khac han.
        tt = {"qc_ai_bat": False, "ly_do": f"{BIEN_BAT} chua dat '1'"}
        return {"phan": [_ghi_bao_cao(kho, run=run, cha=[],
                                      bao_cao={"phien_ban": PHIEN_BAN_QC_AI_GD,
                                               **tt, "ngu_nghia": []})],
                "tom_tat": tt}

    khoa_dich = _khoa_theo_duoi(db, run, pipeline.CONTENT_PROCESS, ".json")
    if not khoa_dich:
        raise ThieuBanRa(_t('Chưa có bản dịch để soát.'))

    muc = _cac_muc(_doc_json(kho, khoa_dich))
    if not muc:
        tt = {"qc_ai_bat": True, "so_muc": 0,
              "ly_do": "ban dich khong co muc nao"}
        return {"phan": [_ghi_bao_cao(kho, run=run, cha=[khoa_dich],
                                      bao_cao={"phien_ban": PHIEN_BAN_QC_AI_GD,
                                               **tt, "ngu_nghia": []})],
                "tom_tat": tt}

    if bao:
        bao(10, _t('Đang soát nghĩa bản dịch'))

    # 🔴 Chia lo TRUOC vong lap, va giu lai danh sach.
    #
    #    Ban dau `so_lo` duoc tang o dau moi vong roi dung lam MAU SO cua vach
    #    tien do: `80 * (i + 1) / so_lo`. O vong thu `i`, `so_lo` da bang
    #    `i + 1` — nen phan so luon bang 1 va vach nhay thang len 90% o lo dau
    #    roi dung yen den het. Dung o 90% suot phan lau nhat doc y het treo.
    #
    # ⛔ Khong truyen `moi_lo=`: `qc_ai.DOAN_MOI_LO` la cho DUY NHAT quyet
    #    dinh co lo, va chinh `qc_ai` ghi ro dieu do o cho khai bao hang so.
    cac_lo = qc_ai.chia_lo(muc)
    from . import cai_dat as cd
    dich = cd.doc(run).ngon_ngu_dich
    so_lo = len(cac_lo)
    phan: list[dict] = []

    # 🔑 LAT CAT (`lat_cat.py`). Truoc 22/09 giai doan nay KHONG co diem chot
    #    nao: mot job bi giet o lo 90 la mat ca 90 phan quyet. Gio moi lo xong
    #    ghi phan quyet cua no vao don vi viec `lo_XXX` (dong so cai da tao san
    #    dong do), kem `phien` cua lat cat.
    #
    # ⚠️ Chi luot NOI TIEP cung `phien` moi doc lai phan quyet cu. Thu lai sau
    #    loi / sau vong sua van soat lai tu dau — dung hanh vi truoc day.
    lc = lat_cat.mo(db, run, pipeline.QC_AI,
                    du_phong_s=(lat_cat.timeout_goi_ai(ai.QC_NGU_NGHIA)
                                + lat_cat.DU_PHONG_NGOAI_GOI_S))
    bat_dau = 0
    if lc.noi_tiep:
        from . import features
        for j in range(min(lc.vi_tri, so_lo)):
            it = features.don_vi_theo_khoa(db, run.id, pipeline.QC_AI,
                                           f"lo_{j:03d}")
            o = (it.outputs or {}) if it is not None else {}
            # Lo truoc con tro khong co phan quyet cung phien = lo da hoi va
            # bo (mo ho / hong) — lan chay mot mach cung bo no.
            if o.get("phien") == lc.phien:
                phan.extend(list(o.get("phan") or []))
        bat_dau = min(lc.vi_tri, so_lo)

    for i in range(bat_dau, so_lo):
        lo = cac_lo[i]
        lc.kiem(vi_tri=i)
        ma_lo = f"lo_{i:03d}"
        ma_trong_lo = {str(d["ma"]) for d in lo}
        # 🔑 Giu lai cau nguon/cau dich de dinh vao phan quyet ben duoi.
        #    `qc_ai.doc_ngu_nghia` co y KHONG tra ve chung — no chi doc thu
        #    model noi, va model khong duoc phep viet lai cau da gui di.
        van_ban = {str(d["ma"]): (d["goc"], d["chu"]) for d in lo}
        try:
            kq = ai.goi_tinh_tien(db, run, ai.QC_NGU_NGHIA,
                                  qc_ai.loi_nhac_ngu_nghia(lo, dich),
                                  stage=pipeline.QC_AI, item_key=ma_lo, ctx=ctx)
            phan_lo: list[dict] = []
            for pq in qc_ai.doc_ngu_nghia(
                    ai.doc_ket_qua(kq, ai.QC_NGU_NGHIA),
                    ma_trong_lo):
                # ⚠️ `sua_chua.tu_qc_ngu_nghia` doc `nguon`/`dich` lam bang
                #    chung. Khong dinh vao thi khiem khuyet van dinh tuyen
                #    dung, nhung bao cao chi noi "doan seg_0007 sai" ma
                #    khong noi SAI CAI GI — tuc khong ai kiem lai duoc
                #    phan quyet cua model trong khi chinh no la ben chu quan.
                g, c = van_ban.get(pq["ma"], ("", ""))
                phan_lo.append({**pq, "nguon": g, "dich": c})
        except ai.AiMoHo:
            # ⛔ Mo ho khong duoc nuot va khong duoc thu lai: khong biet model da
            #    chay chua. So cai da ghi `mo_ho`; lo nay khong co phan quyet.
            log.warning("qc ngu nghia lo %s mo ho — lo nay khong co phan quyet",
                        ma_lo)
            db.commit()
            lc.xong_mot()
            continue
        except Exception as exc:            # noqa: BLE001
            # ⚠️ Mot lo hong khong duoc lam hong ca lan chay — cung nguyen tac
            #    voi `_doc_cac_canh`. Khong co phan quyet nghia la KHONG co
            #    khiem khuyet, tuc khong sinh viec sua: im lang khong duoc doc
            #    thanh "co loi".
            log.warning("qc ngu nghia lo %s hong (%s) — bo lo nay",
                        ma_lo, type(exc).__name__)
            db.commit()
            lc.xong_mot()
            continue
        phan.extend(phan_lo)
        from . import su_dung
        su_dung.danh_dau_xong(db, run, stage=pipeline.QC_AI, item_key=ma_lo,
                              outputs={"phien": lc.phien, "phan": phan_lo})
        db.commit()
        lc.xong_mot()
        if bao:
            bao(10 + int(80 * (i + 1) / max(1, so_lo)), _t('Đang soát nghĩa bản dịch'))

    khong_dat = [p for p in phan if not p.get("dat", True)]
    bao_cao = {
        "phien_ban": PHIEN_BAN_QC_AI_GD,
        "so_muc": len(muc),
        "so_lo": so_lo,
        "so_co_phan_quyet": len(phan),
        "so_khong_dat": len(khong_dat),
        "ngu_nghia": phan,
    }
    phan_ra = _ghi_bao_cao(kho, run=run, bao_cao=bao_cao, cha=[khoa_dich])

    if bao:
        bao(95, _t('Đang lưu báo cáo'))

    return {
        "phan": [phan_ra],
        # 🔑 `tom_tat` do thang vao `stage.outputs` (`thi_hanh:327`), va do la
        #    duong vong sua doc duoc ma KHONG phai mo kho. `_advance` chay o
        #    MOI luot cua MOI lan chay; bat no doc mot tep tu kho de tra loi
        #    mot cau ma CSDL tra loi duoc la mot cai gia phai tra mai mai.
        #
        # ⚠️ Chi ghi phan KHONG DAT, khong ghi ca bang. `tom_tat` duoc mo ta la
        #    "con so cho tien do va giao dien"; nhet ca tram phan quyet vao do
        #    la doi cong dung cua no. Phan day du nam trong artifact.
        "tom_tat": {"qc_ai_bat": True, "so_muc": len(muc), "so_lo": so_lo,
                    "so_co_phan_quyet": len(phan),
                    "so_khong_dat": len(khong_dat),
                    "qc_ai_khong_dat": khong_dat},
        # 🔑 Vong sua doc khoa nay. Ghi CA phan quyet, khong chi phan khong dat:
        #    `sua_chua.tu_qc_ngu_nghia` tu loc, va mot bao cao chi chua loi thi
        #    khong tra loi duoc "da soat bao nhieu muc".
        "_qc_ai_ngu_nghia": phan,
    }
