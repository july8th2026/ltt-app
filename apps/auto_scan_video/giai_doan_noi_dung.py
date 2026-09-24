"""Giai doan CONTENT_PROCESS — viet loi long tieng cho phan DUOC GIU LAI.

Mot artifact ra:

    content.json   ban long tieng, giu nguyen ma doan   (kind=json)

⛔ Ban ghi nguon **BAT BIEN**. Tep nay chi doc `transcript.json`; no khong bao
   gio ghi de len do (Prompt 11, "explicitly forbidden"). Ly do khong phai su
   gon gang — ban ghi la bang chung ve thu may nghe duoc, ban long tieng la mot
   dien giai cua no, va ghi de dien giai len bang chung thi mat kha nang doi
   chieu khi khach khieu nai.

⛔ Prompt 14 cam: khong sinh tieng noi trong giai doan nay.

## 🔴 Pha 14 doi CAI GI o day, va vi sao

Truoc pha 14 giai doan nay **dich ca ban chep loi** — moi doan, ke ca nhung doan
thuoc canh se bi cat. Do la V4-R07, va pha 12 da dong no o phia CHUOI (dat
`EDIT_PLAN` truoc). Pha 14 dong no o phia **noi dung**: dau vao cua giai doan nay
gio la `ban_bien_tap.doan_giu_lai(...)`, tuc **chi nhung doan nam trong canh con
lai**. Mot doan thuoc canh da cat khong duoc gui di, khong duoc tra tien, va
khong duoc xuat hien trong ban ra.

## Day la giai doan DAU TIEN tieu tien that

Nen ba thu chuyen tu ly thuyet sang thuc te o day:

  * `ctx.provider_dispatched()` duoc goi **ngay truoc** khi goi ra ngoai, va no
    ghi xuong CSDL. Mot lan sap sau do doc ra duoc la "co the da goi", chu khong
    phai "chua goi" (I5).
  * `AiMoHo` KHONG BAO GIO duoc thu lai tu dong — provider co the da nhan va da
    tinh tien.
  * `su_dung.cua_chan_truoc_khi_tieu` chay truoc **moi lo**, khong phai mot lan
    o dau.

## Diem chot theo TUNG DOAN, khong phai theo giai doan

Mot lan chay lai sau khi lo thu bay hong khong duoc viet lai sau lo dau. Diem
chot ghi kem **van tay**, nen doi giong hay doi ban bien tap thi nhung doan cu
khong con duoc tinh la "da lam roi" — chung la cau tra loi cho mot cau hoi khac.
"""
from __future__ import annotations

import io
import json
import logging

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (ai, assets, ban_bien_tap, ban_ghi, lat_cat, long_tieng, pipeline,
               rang_giong, su_dung)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)


class ThieuBanGhi(ThieuNguon):
    """Giai doan chep loi chua sinh ra ban ghi."""


class ThieuBanBienTap(ThieuNguon):
    """Chua co ban bien tap nen chua biet phan nao duoc giu."""


def _doc_ban_ghi(db, kho: Storage, run) -> tuple[dict, str]:
    """Ban ghi CHINH TAC cua run + checksum cua no. Chi doc, khong bao gio ghi."""
    from . import features

    truoc = features.giai_doan_theo_ten(db, run.id, pipeline.TRANSCRIBE)
    khoa = next((k for k in ((truoc.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if truoc else ""
    if not khoa:
        raise ThieuBanGhi(_t('Chưa có bản ghi để dịch.'))

    with kho.open(khoa) as f:
        goi = f.read()
    tai_lieu = json.loads(goi.decode("utf-8"))
    # Kiem lai sau khi doc tu kho: mot artifact hop le luc ghi van co the bi sua
    # sau do, va I8 noi DONE phai keo theo mot ket qua **con dung**.
    ban_ghi.kiem(tai_lieu)
    return tai_lieu, assets.bam(goi)


def _doc_ban_bien_tap(db, kho: Storage, run) -> tuple[object, object]:
    """`BanBienTap` + `ChiMucCanh` cua run. Ca hai nam trong MOT artifact."""
    from . import canh as canh_mod, features

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.EDIT_PLAN)
    khoa = next((k for k in (((gd.outputs or {}) if gd else {})
                             .get("khoa_asset") or []) if k.endswith(".json")), "")
    if not khoa:
        raise ThieuBanBienTap(_t('Chưa có bản biên tập nên chưa biết giữ phần nào.'))
    with kho.open(khoa) as f:
        goi = json.loads(f.read().decode("utf-8"))

    return (ban_bien_tap.BanBienTap.tu_dict(goi.get("ban") or {}),
            canh_mod.tu_dict(goi.get("chi_muc") or {}))


def _giong_da_chot(db, run, *, ban_ghi: dict, ctx=None) -> tuple[str, dict, str]:
    """Chot VoiceBinding va DONG BANG no vao ban long tieng.

    🔑 Pha 09 cho phep `AUTO_MATCH` **hoan lai** khi chua co ho so noi dung. Den
       day thi khong hoan duoc nua: loi thoai duoc viet CHO mot giong cu the —
       xung ho, giong dieu, do trang trong deu bam vao no — nen viet truoc roi
       chon giong sau la viet mu.

    ⇒ Nen day chinh la cho **dung** ho so, ngay truoc khi no het duoc hoan:
      `ho_so_noi_dung.bao_dam` doc bang chung lan chay DA tra tien (F0 cua stem
      `vocals` do o `audio_prepare`, ban chep loi cua `transcribe`) va ghi
      `dac_diem_giong` xuong `run.settings`. Ca hai nguon nam TRUOC `edit_plan`,
      nen duong nay chay y het nhau o hai preset — ke ca preset giu hinh, cai
      **khong** chay mot lan `edit_plan` nao co nghia.

    ⛔ Nen `ma_giong()` **nem** khi chua chot, thay vi rot ve giong mac dinh. Mot
       giong mac dinh o day khong hong ra loi nao: no cho ra mot ban long tieng
       nghe duoc, chi la khong phai giong khach dat. Cai doi tu 23/09 la CAU
       LOI: `vi_sao_chua_rang` noi thieu gi, thay vi mot cau chung chung ve mot
       "ho so noi dung" ma khach khong biet la thu gi.
    """
    # `tu_thiet_lap` van nhan mot dict — `rang_giong` KHONG duoc import
    # `cai_dat` (vong tron: `cai_dat` doc `CHE_DO_GIONG_MAC_DINH` cua no).
    # Nen ta chuan hoa TRUOC roi dua vao.
    from . import cai_dat as cd, ho_so_noi_dung

    yc = rang_giong.tu_thiet_lap(cd.chuan_hoa(run.settings))
    if rang_giong.can_cho_ho_so(yc):
        ho_so = ho_so_noi_dung.bao_dam(db, run, ban_ghi=ban_ghi, ctx=ctx)
        log.info("run %s: ho so noi dung %s", run.id, ho_so_noi_dung.mo_ta(ho_so))
        # Doc LAI tu thiet lap da ghi: mot duong doc duy nhat cho ca hai luot
        # (luot dau vua sinh ho so, luot chay lai doc ho so cu) — hai duong doc
        # la hai co hoi chon ra hai giong khac nhau cho cung mot lan chay.
        yc = rang_giong.tu_thiet_lap(cd.chuan_hoa(run.settings))

    kq = rang_giong.rang_noi_long(db, owner_id=run.owner_id, yeu_cau=yc)
    if not kq.da_chot:
        # ⭐ Cau + MA. Khong co ma thi cau nay dung lai o cot `error` — mot cot
        #    ma man hinh cua khach co y khong doc (`quan_sat.LOI_CO_MA`), vi chu
        #    tu do cua van hanh co the mang duong dan hay ten model.
        raise rang_giong.ChuaRangError(rang_giong.vi_sao_chua_rang(kq),
                                       ma_loi=rang_giong.ma_chua_rang(kq))
    # 🔴 **`nguon` tra ve RIENG, khong nhet vao `can_cu`.** No la mot TRUONG cua
    #    `KetQua`, con `tom_tat` cua giai doan nay lai doc `can_cu["nguon"]` —
    #    nen truoc 23/09 `nguon_giong` cua MOI lan chay deu la chuoi rong. Mot
    #    cot bao cao luon rong khong keu len bao gio; no chi tra loi sai cau hoi
    #    "vi sao giong nay".
    #
    # ⛔ Va khong nhet vao `can_cu` vi `can_cu` di THANG vao loi nhac (`dac_diem`
    #    duoi kia roi ve `can_cu` khi khong co khoa `dac_diem`). Them mot khoa o
    #    day la doi loi nhac cua duong `USER_SELECTED` da nghiem thu.
    return kq.ma_giong(), dict(kq.can_cu or {}), kq.nguon


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Loc theo ban bien tap -> chot giong -> viet loi theo lo -> rap -> kiem."""
    goc, checksum = _doc_ban_ghi(db, kho, run)
    ban, chi_muc = _doc_ban_bien_tap(db, kho, run)

    # ⛔ Ban ghi nguon khong bi cham. `doan_giu_lai` tra ve mot BAN SAO da loc.
    giu = ban_bien_tap.doan_giu_lai(goc, ban, chi_muc)
    doan_giu = list(giu.get("doan") or [])
    if not doan_giu:
        raise long_tieng.LongTiengError(
            _t('Bản biên tập không giữ lại đoạn thoại nào.'))

    ma_giong, can_cu, nguon_giong = _giong_da_chot(db, run, ban_ghi=goc, ctx=ctx)
    from . import cai_dat as cd
    dich = cd.doc(run).ngon_ngu_dich
    provider = ai.THU_TU_PROVIDER[0]
    model = ai.model_cho(ai.CHUYEN_LOI_THOAI, provider=provider)

    vt = long_tieng.van_tay_long_tieng(
        checksum_ban_ghi=checksum, van_tay_ban=ban.van_tay(),
        ma_giong=ma_giong, provider=provider, model=model, ngon_ngu_dich=dich)

    # ⭐ Diem chot mang van tay nay. Doi giong hay doi ban bien tap => van tay
    #    doi => khong doan nao duoc tinh la da lam roi.
    xong = su_dung.da_xong(db, run, stage=pipeline.CONTENT_PROCESS, fingerprint=vt)

    dac_diem = dict(can_cu.get("dac_diem") or {}) or can_cu
    con_lai = [d for d in doan_giu if str(d.get("ma") or "") not in xong]
    chuyen: dict[str, dict] = _lay_lai_doan_da_xong(db, run, xong)

    lo_lo = long_tieng.chia_lo(con_lai)

    # 🔑 LAT CAT (`lat_cat.py`): 120 phut video ~ 150 lo x ~142 s — gap ~6 lan
    #    tran job. Truoc MOI lo hoi co con du cho cho mot lo te nhat khong; het
    #    thi nhuong, job ke tiep doc diem chot va di tiep. Lo la nguyen tu (thieu
    #    mot doan thi `doc_chuyen` nem), nen luot sau chia lai `con_lai` ra
    #    DUNG cac lo con lai cua lan chay mot mach.
    lc = lat_cat.mo(db, run, pipeline.CONTENT_PROCESS, van_tay=vt,
                    du_phong_s=(lat_cat.timeout_goi_ai(ai.CHUYEN_LOI_THOAI)
                                + lat_cat.DU_PHONG_NGOAI_GOI_S))
    # `so_lo` cua tom tat = so lo DA GUI cua ca giai doan, cong qua cac luot.
    so_lo_truoc = int(lc.trang_thai.get("so_lo") or 0) if lc.noi_tiep else 0
    # ⭐ Khoa so cai cua lo theo vi tri TRONG `doan_giu`, khong theo vi tri
    #    trong `con_lai`: luot noi tiep bat dau lai `i` tu 0, va `lo_000` thu
    #    hai se dung `UNIQUE(run_id, ma_dispatch)` — `DaGhiRoi` bi nuot va mot
    #    lan goi DA GIAO bien mat khoi so cai.
    vi_tri_cua = {str(d.get("ma") or ""): k for k, d in enumerate(doan_giu)}
    co_lo = max(1, int(long_tieng.DOAN_MOI_LO))

    for i, lo in enumerate(lo_lo):
        lc.kiem(vi_tri=i, trang_thai={"so_lo": so_lo_truoc + i})
        dau = vi_tri_cua.get(str(lo[0].get("ma") or ""), 0)
        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(5 + int(85 * dau / max(1, len(doan_giu))),
                         _t('Đang viết lời thoại'))

        ma_da_gui = {str(d.get("ma") or "") for d in lo}
        messages = long_tieng.loi_nhac(
            lo, tat_ca=doan_giu, ngon_ngu_goc=str(goc.get("ngon_ngu") or ""),
            dac_diem_giong=dac_diem, ngon_ngu_dich=dich)

        kq = ai.goi_tinh_tien(
            db, run, ai.CHUYEN_LOI_THOAI, messages,
            stage=pipeline.CONTENT_PROCESS,
            # ⭐ N-23: ep luoc do o tang GIAI MA. 2/21 lo hong -> 0/20,
            #    gia +0 luot goi (`long_tieng.luoc_do_phan_hoi`).
            luoc_do=long_tieng.luoc_do_phan_hoi(lo),
            # 🔑 Khoa cua so cai la LO (mot lan goi = mot dong so cai), con diem
            #    chot la DOAN. Hai truc khac nhau va gop chung lai se hong: mot
            #    lo chua 12 doan nhung chi mot lan tinh tien.
            item_key=f"lo_{dau // co_lo:03d}",
            ctx=ctx)

        # 🔴 **`noi_dung` la MOT CHUOI, khong phai mot dict.** `ai.goi` tra ve
        #    nguyen van phan hoi cua model (`ai.py:270`), va viec doc no thanh
        #    JSON la viec cua `ai.doc_json` — ham ton tai dung de lam dieu do va
        #    de kiem cac truong bat buoc cua tung thao tac.
        #
        #    Truoc pha 22 dong nay truyen thang chuoi vao `doc_chuyen`, va
        #    `doc_chuyen` goi `.get("doan")` tren no: **moi lan goi model that
        #    deu nem `AttributeError`**, tuc giai doan tra tien nay chua bao gio
        #    chay noi mot lan voi mot model that.
        #
        # ⭐ Vi sao khong bo test nao bat duoc: `tests/fixtures/asv_media.cua_ai_gia`
        #    thay `goi_tinh_tien` va tra ve mot **dict** o `noi_dung` — thu ma cua
        #    that khong bao gio tra ve. Mot ban gia tra ve dung thu ma ma nguon
        #    muon nhan, thay vi thu cua that tra ve, se lam ca bo test xanh
        #    quanh mot loi khong the khong xay ra.
        moi = long_tieng.doc_chuyen(
            ai.doc_ket_qua(kq, ai.CHUYEN_LOI_THOAI),
            ma_da_gui)
        chuyen.update(moi)

        # ⛔ Ghi diem chot NGAY sau moi lo, khong doi den cuoi: mot lan sap o lo
        #    thu bay khong duoc lam mat sau lo dau.
        for ma, v in moi.items():
            su_dung.danh_dau_xong(db, run, stage=pipeline.CONTENT_PROCESS,
                                  item_key=ma, fingerprint=vt,
                                  outputs={"chu": v["chu"],
                                           "cam_xuc": v["cam_xuc"],
                                           "kieu_noi": v["kieu_noi"],
                                           # ⭐ DUONG B — chi THU vao so, ⛔
                                           #    khong hien cho khach, ⛔ khong
                                           #    lai vong sua, ⛔ khong chan gi.
                                           #    `long_tieng.QUY_TAC_TU_KHAI`.
                                           "khong_chac": v["khong_chac"]})
        # 🔴 **`commit`, khong phai `flush`** — va no khong phai mot chi tiet ky
        #    thuat, no la dinh nghia cua "diem chot".
        #
        #    Mot `flush` chi day cau lenh xuong giao dich dang mo. Worker chet
        #    ngay sau do thi ca giao dich bi cuon lai, va "diem chot" cua ta
        #    khong ton tai. Chot ma khong ben thi khong chot gi ca.
        #
        # ⭐ Va no con sua mot loi DO DUOC: `su_dung.ghi` + `danh_dau_xong` giu
        #    khoa ghi tren phien cua handler, trong khi `ctx.progress` mo mot
        #    phien THU HAI de cap nhat bang `jobs`. Tren SQLite hai cai do gap
        #    nhau thanh `database is locked`, va lo thu hai cua giai doan nay la
        #    lan dau tien trong ca kho hai duong do chay canh nhau — pha 11 co
        #    `goi_tinh_tien` nhung chua duoc noi vao chuoi.
        db.commit()
        lc.xong_mot()

    tai_lieu = long_tieng.dung(giu, chuyen, ma_giong=ma_giong,
                               van_tay_ban=ban.van_tay(),
                               provider=provider, model=model,
                               ngon_ngu_dich=dich)
    long_tieng.kiem(tai_lieu, giu)

    goi = json.dumps(tai_lieu, sort_keys=True, ensure_ascii=False).encode("utf-8")
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.CONTENT_PROCESS, van_tay=vt,
                               duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "tom_tat": {**long_tieng.tom_tat(tai_lieu),
                    "so_doan_goc": len(goc.get("doan") or []),
                    "so_lo": so_lo_truoc + len(lo_lo),
                    "nguon_giong": nguon_giong},
    }


def _lay_lai_doan_da_xong(db, run, xong: set[str]) -> dict[str, dict]:
    """Doc lai ket qua cua nhung doan da xong tu diem chot.

    ⭐ Doc tu `AsvWorkItem.outputs` chu khong goi lai model: do la ca ly do ton
       tai cua diem chot. Mot lan chay lai sau khi lo thu bay hong phai tra tien
       cho **sau lo**, khong phai bay.
    """
    from . import features

    ra: dict[str, dict] = {}
    if not xong:
        return ra
    for it in features.cac_don_vi(db, run.id, pipeline.CONTENT_PROCESS):
        if it.item_key in xong and (it.outputs or {}).get("chu"):
            o = dict(it.outputs)
            ra[it.item_key] = {
                "chu": str(o.get("chu") or ""),
                "cam_xuc": o.get("cam_xuc") or long_tieng.CAM_XUC[0],
                "kieu_noi": o.get("kieu_noi") or long_tieng.KIEU_NOI[0],
                "nhan_manh": list(o.get("nhan_manh") or []),
                # ⛔ Doan da xong TRUOC khi co truong nay se khong co no —
                #    `[]` la cau tra loi dung, ⛔ khong phai mot thieu sot.
                "khong_chac": list(o.get("khong_chac") or []),
            }
    return ra
