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

## Pham vi: ngu nghia + HINH

Pha 19 doi ba loai QC. Giai doan nay lam hai:

    ngu nghia   dich sai      -> `content_process`   ✅ lo 10 muc, `qc_ngu_nghia`
    hinh        cat sai       -> `edit_plan`         ✅ moi CHO NOI, `qc_hinh`
    giong noi   doc sai       -> `voice_synthesis`   -> da chuyen sang lan `gpu`
                                                        (`giai_doan_qc_do_luong`,
                                                         ASR + WER/CER that)

🔑 **Hai vong lap, MOT lat cat.** Lo ngu nghia chiem vi tri `0..so_lo-1` cua con
   tro; cho noi hinh chiem `so_lo..`. Hai con tro se bat luot sau doan xem nua
   nao da xong, va "doan" o day nghia la hoi (va tra tien) lai.

## ⛔ Lop HINH chi TU VAN — phan quyet duoc GHI, khong sinh viec sua

Xem `sua_chua.QC_HINH_LA_TU_VAN`. Ngan gon, va noi dung chu dung:

  * do chinh xac DA DO va no khong dat: 54 cho noi that tren hai phim, 15 bi
    cham `dat=false`, **9/9 cai soi bang mat la bao dong gia**, va **14/15**
    vuot `DO_TIN_TOI_THIEU` — tuc nguong do tin khong loc duoc gi
    (`L_QC_HINH.md` §4);
  * `cat_sai` la vong sua DAT NHAT cua he: `edit_plan` la giai doan som nhat,
    nen dat lai no keo theo gan nhu ca chuoi phia sau.

⭐ "Tu van" = *khong tu dong tieu tien*, khong phai *khong ai duoc biet*: phan
   quyet van vao artifact, van vao `stage.outputs`, van hien o bao cao van hanh.
"""
from __future__ import annotations

import io
import json
import logging
import os

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import ai, assets, canh, lat_cat, pipeline, qc_ai, sua_chua
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
                                               **tt, "ngu_nghia": [],
                                               "hinh": []})],
                "tom_tat": tt}

    khoa_dich = _khoa_theo_duoi(db, run, pipeline.CONTENT_PROCESS, ".json")
    if not khoa_dich:
        raise ThieuBanRa(_t('Chưa có bản dịch để soát.'))

    muc = _cac_muc(_doc_json(kho, khoa_dich))
    if not muc:
        # ⚠️ Ban dich rong khong noi gi ve LOP HINH — mot preset cat van co
        #    cho noi de soat. Nhung hai lop dung chung mot LAT CAT va lop hinh
        #    nam SAU lop nghia trong danh sach don vi; tra ve som o day la bo
        #    han lop hinh, nen ghi ro ly do thay vi de no im lang.
        tt = {"qc_ai_bat": True, "so_muc": 0,
              "ly_do": "ban dich khong co muc nao",
              "qc_hinh_khong_kha_dung": "bo qua cung luot voi lop nghia"}
        return {"phan": [_ghi_bao_cao(kho, run=run, cha=[khoa_dich],
                                      bao_cao={"phien_ban": PHIEN_BAN_QC_AI_GD,
                                               **tt, "ngu_nghia": [],
                                               "hinh": []})],
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
    #
    # 🔑 **`du_phong_s` phai la don vi TE NHAT cua CA HAI vong lap.** Mot con tro
    #    duy nhat chay qua ca lo ngu nghia lan cho noi hinh, va don vi hinh ton
    #    them hai lenh ffmpeg rut khung truoc khi goi model. Tinh du phong chi
    #    theo vong nghia se lam job cham tran ngay o cho noi cuoi cung — dung
    #    luc `lat_cat` ton tai de ngan.
    lc = lat_cat.mo(db, run, pipeline.QC_AI,
                    du_phong_s=(max(lat_cat.timeout_goi_ai(ai.QC_NGU_NGHIA),
                                    lat_cat.timeout_goi_ai(ai.QC_HINH)
                                    + qc_ai.KHUNG_MOI_CHO_NOI
                                    * canh.CHO_RUT_KHUNG_S)
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
                                  stage=pipeline.QC_AI, item_key=ma_lo, ctx=ctx,
                                  temperature=qc_ai.NHIET_DO_NGU_NGHIA)
            phan_lo: list[dict] = []
            for pq in qc_ai.doc_ngu_nghia(
                    ai.doc_ket_qua(kq, ai.QC_NGU_NGHIA),
                    ma_trong_lo, van_ban):
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
            # ⚠️ Vach chia lam DOI: lop nghia 10->45, lop hinh 50->95.
            #    De nguyen `80` thi vach cham 90% xong lop nghia roi TUT
            #    ve 50% khi lop hinh bat dau — mot vach di lui doc y het
            #    mot lan chay vua bi dat lai.
            bao(10 + int(35 * (i + 1) / max(1, so_lo)), _t('Đang soát nghĩa bản dịch'))

    # ── QC HINH: nhin lai tung cho noi cua BAN RA ──────────────────────────
    #
    # 🔑 **Cung mot LAT CAT, khong mot lat cat thu hai.** Hai vong lap la hai
    #    danh sach don vi viec noi tiep nhau: lo ngu nghia chiem vi tri
    #    `0..so_lo-1`, cho noi hinh chiem `so_lo..`. Mot con tro duy nhat thi
    #    mot job bi giet o cho noi thu 12 quay lai dung do — hai con tro thi
    #    luot sau phai doan xem nua nao da xong.
    #
    # ⚠️ `_soat_hinh` KHONG nem. Mot lop QC chu quan khong duoc giet lan chay:
    #    `qc` (tat dinh) moi la cong phat hanh. Thieu ban ra / doc khong duoc =>
    #    `khong_kha_dung` co ly do, **khong** => "khong cho noi nao hong".
    if bao:
        bao(50, _t('Đang soát chỗ nối hình'))
    hinh, tt_hinh = _soat_hinh(db, kho, run=run, lc=lc, tu_vi_tri=so_lo,
                               ctx=ctx, bao=bao)

    khong_dat = [p for p in phan if not p.get("dat", True)]
    hinh_khong_dat = [p for p in hinh if not p.get("dat", True)]
    bao_cao = {
        "phien_ban": PHIEN_BAN_QC_AI_GD,
        "so_muc": len(muc),
        "so_lo": so_lo,
        "so_co_phan_quyet": len(phan),
        "so_khong_dat": len(khong_dat),
        "ngu_nghia": phan,
        # 🔑 Phan quyet DAY DU cua lop hinh nam o artifact, khong o `tom_tat`:
        #    `tom_tat` di thang vao `stage.outputs` (CSDL) va duoc mo ta la
        #    "con so cho tien do va giao dien".
        "hinh": hinh,
        "hinh_tom_tat": dict(tt_hinh),
        # ⭐ Ghi thang vao BANG CHUNG rang lop nay dang TU VAN. Mot bao cao noi
        #    "3 cho noi khong dat" ma khong noi *"va khong cai nao sinh viec
        #    sua"* se duoc doc thanh "he thong da xu ly" — xem
        #    `sua_chua.QC_HINH_LA_TU_VAN`.
        "hinh_la_tu_van": bool(sua_chua.QC_HINH_LA_TU_VAN),
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
                    "qc_ai_khong_dat": khong_dat,
                    # 🔑 `jobs._qc_hinh` doc DUNG khoa nay, tu CSDL. Cung ly do
                    #    voi `qc_ai_khong_dat`: `_advance` chay o moi luot cua
                    #    moi lan chay, va bat no mo mot tep tu kho de tra loi
                    #    mot cau `stage.outputs` tra loi duoc la mot cai gia
                    #    phai tra mai mai.
                    "qc_hinh_khong_dat": hinh_khong_dat,
                    "qc_hinh_la_tu_van": bool(sua_chua.QC_HINH_LA_TU_VAN),
                    **{f"qc_hinh_{k}": v for k, v in tt_hinh.items()
                       if k != "hong"}},
        # 🔑 Vong sua doc khoa nay. Ghi CA phan quyet, khong chi phan khong dat:
        #    `sua_chua.tu_qc_ngu_nghia` tu loc, va mot bao cao chi chua loi thi
        #    khong tra loi duoc "da soat bao nhieu muc".
        "_qc_ai_ngu_nghia": phan,
        "_qc_ai_hinh": hinh,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  QC HINH — nhin lai tung CHO NOI cua BAN RA
# ══════════════════════════════════════════════════════════════════════════════

#: So lan hoi VLM ve MOT cho noi khi phan hoi SAI HINH DANG. `2` = mot lan hoi
#: + mot lan hoi lai.
#:
#: 🔑 Cung con so va cung ranh gioi voi `giai_doan_ban_bien_tap.SO_LAN_DOC_CANH`,
#:    va vi cung mot phep do: lan `fix-toc-do` do 18 canh voi loi nhac cu va
#:    **8/18 hong deu la phan hoi HTTP thanh cong co hinh dang sai** — thu
#:    re-roll duoc. `AiMoHo` va `AiError` tran thi khong (xem vong lap ben duoi).
SO_LAN_HOI_HINH = 2


def _bien_tap_cua_ban_dung(ban_dung: dict) -> dict | None:
    return (ban_dung.get("hinh") or {}).get("bien_tap")


def _soat_hinh(db, kho: Storage, *, run, lc, tu_vi_tri: int, ctx=None,
               bao=None) -> tuple[list[dict], dict]:
    """Hoi VLM ve TUNG cho noi cua tep DA RENDER. `(phan quyet, tom tat)`.

    🔴 **Tren tep DA RENDER, va tren truc BAN RA — khong phai tren nguon.**

       Cau hoi la *"cho noi nay, nhu khach se nhin thay, co dut mach khong"*.
       Hoi no tren tep nguon la hoi ve hai canh **truoc** khi che logo, dan chu,
       dan phu de, doi toc do va ma hoa lai — tuc tra loi ve mot ban dung khong
       ai nhan duoc. Va no khong phai mot khac biet ly thuyet: mot cho noi co
       the dut mach **vi** mot lop phu bat qua no.

    🔑 **Diem chot theo CHO NOI, cung khuon voi `_doc_cac_canh`.** Moi cho noi
       la mot `AsvWorkItem` (`hinh_XXX`); mot job bi giet o cho noi thu 40 khong
       duoc bat 39 cho noi truoc hoi (va tra tien) lai.

    ⚠️ **Thieu bat cu manh nao ⇒ `khong_kha_dung` co LY DO, khong ⇒ "khong co
       cho noi nao hong".** Hai cau do dan toi hai quyet dinh khac han nhau, va
       cai thu hai la mot loi khai ma khong phep do nao ung ho.

    ⛔ Khong nem. Giai doan nay khong duoc giet mot lan chay vi lop QC chu quan
       — `qc` (tat dinh) moi la cong phat hanh. Xem docstring cua `chay`.
    """
    import base64
    from pathlib import Path
    import tempfile

    from . import (ban_do_thoi_gian as bdtg, bien_tap, canh as canh_mod,
                   features, su_dung as sd)
    from .giai_doan_media import _duong_doc_duoc

    khoa_ra = _khoa_theo_duoi(db, run, pipeline.RENDER, ".mp4")
    khoa_kh = _khoa_theo_duoi(db, run, pipeline.TIMING_ALIGN, ".json")
    khoa_bd = _khoa_theo_duoi(db, run, pipeline.COMPOSE, ".json")
    khoa_ep = _khoa_theo_duoi(db, run, pipeline.EDIT_PLAN, ".json")
    thieu = [t for t, k in (("render", khoa_ra), ("timing_align", khoa_kh),
                            ("compose", khoa_bd)) if not k]
    if thieu:
        return [], {"khong_kha_dung": f"thieu ban ra cua {', '.join(thieu)}"}

    ke_hoach = _doc_json(kho, khoa_kh)
    ban_dung = _doc_json(kho, khoa_bd)
    bdo = bdtg.BanDoThoiGian.tu_dict(ke_hoach.get("ban_do") or {})
    ho_so_bt = _bien_tap_cua_ban_dung(ban_dung)
    td = float(bien_tap.toc_do(ho_so_bt) or 1.0)

    # 🔑 Chi muc canh + danh sach canh BI CAT: thu bien mot phan quyet thanh
    #    mot viec sua. Thieu no thi phan quyet van duoc ghi — chi khong dat lai
    #    duoc don vi nao. Xem `qc_ai.cac_cho_noi`.
    chi_muc = None
    ma_cat: tuple = ()
    if khoa_ep:
        try:
            from . import ban_bien_tap as _bbt
            goi_ep = _doc_json(kho, khoa_ep)
            chi_muc = canh_mod.tu_dict(goi_ep.get("chi_muc") or {})
            # ⛔ Doc qua `BanBienTap.tu_dict`, khong boi khoa `cac_ma_cat` ra
            #    khoi JSON: `sang_dict` KHONG ghi khoa do (no la mot thuoc tinh
            #    tinh ra tu `quyet_dinh`), nen mot phep `goi["ban"]["cac_ma_cat"]`
            #    se luon ra rong — mot tap rong im lang, tuc khong cho noi nao
            #    sinh duoc viec sua va khong loi nao bao.
            ma_cat = tuple(_bbt.BanBienTap.tu_dict(goi_ep.get("ban") or {})
                           .cac_ma_cat)
        except Exception as exc:        # noqa: BLE001 - khong doc duoc != hong
            log.warning("qc hinh: khong doc duoc ban bien tap (%s: %s)",
                        type(exc).__name__, exc)

    cho_noi = qc_ai.cac_cho_noi(bdo, chi_muc=chi_muc, cac_ma_cat=ma_cat,
                                toc_do=td)
    if not cho_noi:
        # ⭐ Duong CHAY THAT, khong phai truong hop bien: preset giu hinh khong
        #    cat canh nao nen ban do co dung MOT khoang — khong cho noi nao de
        #    hoi. Ghi ro de bao cao khong doc ra giong "da soat, khong thay gi".
        return [], {"so_cho_noi": 0, "ly_do": "ban do chi co mot khoang giu"}

    # Chan khung o trong ban ra: mot moc am hay vuot duoi tep cho ra mot lenh
    # ffmpeg khong sinh khung nao, tuc mot cau hoi hoi bang mot buc anh.
    dai_ra = bien_tap.moc_ban_ra(float(bdo.thoi_luong_ra or 0.0), ho_so_bt)

    phan: list[dict] = []
    hong: list[dict] = []
    so = len(cho_noi)

    # ── Luot NOI TIEP: doc lai phan quyet cua cac cho noi truoc con tro ────
    bat_dau = 0
    if lc.noi_tiep and lc.vi_tri > tu_vi_tri:
        for j in range(min(lc.vi_tri - tu_vi_tri, so)):
            it = features.don_vi_theo_khoa(db, run.id, pipeline.QC_AI,
                                           f"hinh_{j:03d}")
            o = (it.outputs or {}) if it is not None else {}
            if o.get("phien") == lc.phien and o.get("phan"):
                phan.append(dict(o["phan"]))
        bat_dau = min(lc.vi_tri - tu_vi_tri, so)

    with tempfile.TemporaryDirectory(
            prefix=f"asv-qcai-{str(run.id)[:12]}-") as tam:
        duong_ra = _duong_doc_duoc(kho, khoa_ra, Path(tam))

        for j in range(bat_dau, so):
            cn = cho_noi[j]
            lc.kiem(vi_tri=tu_vi_tri + j)
            ma_dv = f"hinh_{j:03d}"

            moc_s = [m for m in cn["khung_s"]
                     if 0.0 <= m <= (dai_ra + 0.05 if dai_ra > 0 else m)]
            khung = canh_mod.rut_khung(duong_ra, moc_s)
            if len(khung) < qc_ai.KHUNG_MOI_CHO_NOI:
                # 🔴 **Doi DU hai khung, khong chiu mot.**
                #
                #    `canh.rut_khung` ghi rang mot cau hoi hai khung ma mot khung
                #    hong "van la mot cau hoi tra loi duoc (kem hon)" — dung cho
                #    `doc_canh` (mo ta MOT canh), sai cho day. Cau hoi o day la
                #    ve mot CHUYEN TIEP, va mot chuyen tiep khong nhin duoc tu
                #    mot phia: model se ta buc anh no co va tra ve mot phan
                #    quyet trong nhu that.
                #
                # ⚠️ Ghi ra `hong`, KHONG ghi mot phan quyet `dat=true`. "Khong
                #    hoi duoc" khac han "da hoi va khong thay gi".
                hong.append({"moc_giay": cn["moc_ra"], "loai": "thieu_khung",
                             "ly_do": f"chi rut duoc {len(khung)}/"
                                      f"{qc_ai.KHUNG_MOI_CHO_NOI} khung"})
                db.commit()
                lc.xong_mot()
                continue

            b64 = [base64.b64encode(b).decode("ascii") for b in khung]
            messages = qc_ai.loi_nhac_hinh(b64, moc_giay=cn["moc_ra"])

            pq = None
            loi_cuoi = None
            for lan in range(SO_LAN_HOI_HINH):
                try:
                    kq = ai.goi_tinh_tien(
                        db, run, ai.QC_HINH, messages,
                        stage=pipeline.QC_AI,
                        # ⭐ `item_key` khac giua hai lan: `UNIQUE(run_id,
                        #    ma_dispatch)` se nuot but toan cua lan thu hai, tuc
                        #    mot luot DA tra tien bien mat khoi so cai.
                        item_key=ma_dv if lan == 0 else f"{ma_dv}:lai{lan}",
                        ctx=ctx)
                    pq = qc_ai.doc_hinh(kq, moc_giay=cn["moc_ra"],
                                        ma_cat=cn["ma_cat"],
                                        so_khung=len(khung))
                    break
                except ai.AiMoHo:
                    # ⛔ Khong biet model da chay chua ⇒ khong thu lai.
                    loi_cuoi = ("AiMoHo", "mat ket noi sau khi gui")
                    break
                except (ai.LuocDoSai, qc_ai.QcAiError) as exc:
                    # 🔑 CHI hinh dang sai moi duoc hoi lai — cung ranh gioi
                    #    voi `_doc_cac_canh`, va vi cung phep do.
                    loi_cuoi = (type(exc).__name__, str(exc)[:200])
                    log.warning("qc hinh %s sai hinh dang lan %d/%d (%s: %s)",
                                ma_dv, lan + 1, SO_LAN_HOI_HINH, *loi_cuoi)
                except ai.AiError as exc:
                    loi_cuoi = (type(exc).__name__, str(exc)[:200])
                    log.warning("qc hinh %s hong (%s: %s) — KHONG hoi lai",
                                ma_dv, *loi_cuoi)
                    break

            if pq is None:
                hong.append({"moc_giay": cn["moc_ra"],
                             "loai": (loi_cuoi or ("?", ""))[0],
                             "ly_do": (loi_cuoi or ("", ""))[1]})
                db.commit()
                lc.xong_mot()
                continue

            pq = {**pq, "cat_nguon": cn["cat_nguon"]}
            phan.append(pq)
            sd.danh_dau_xong(db, run, stage=pipeline.QC_AI, item_key=ma_dv,
                             outputs={"phien": lc.phien, "phan": pq})
            db.commit()
            lc.xong_mot()
            if bao:
                bao(50 + int(45 * (j + 1) / max(1, so)),
                    _t('Đang soát chỗ nối hình'))

    khong_dat = [p for p in phan if not p.get("dat", True)]
    return phan, {
        "so_cho_noi": so,
        "so_co_phan_quyet": len(phan),
        "so_hong": len(hong),
        "hong": hong[:20],
        "so_khong_dat": len(khong_dat),
        "toc_do": round(td, 4),
        # 🔑 Bat bien de doc, cung khuon voi `so_canh_da_doc + so_canh_hong`:
        #    moi cho noi hoac co phan quyet hoac co mot dong ly do.
        "du_phu": len(phan) + len(hong) == so,
    }
