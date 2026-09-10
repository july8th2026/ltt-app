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

from . import (ai, assets, ban_bien_tap, ban_ghi, long_tieng, pipeline,
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


def _giong_da_chot(db, run) -> tuple[str, dict]:
    """Chot VoiceBinding va DONG BANG no vao ban long tieng.

    🔑 Pha 09 cho phep `AUTO_MATCH` **hoan lai** khi chua co ho so noi dung. Den
       day thi khong hoan duoc nua: loi thoai duoc viet CHO mot giong cu the —
       xung ho, giong dieu, do trang trong deu bam vao no — nen viet truoc roi
       chon giong sau la viet mu.

    ⛔ Nen `ma_giong()` **nem** khi chua chot, thay vi rot ve giong mac dinh. Mot
       giong mac dinh o day khong hong ra loi nao: no cho ra mot ban long tieng
       nghe duoc, chi la khong phai giong khach dat.
    """
    yc = rang_giong.tu_thiet_lap(dict(run.settings or {}))
    kq = rang_giong.rang(db, owner_id=run.owner_id, yeu_cau=yc)
    return kq.ma_giong(), dict(kq.can_cu or {})


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

    ma_giong, can_cu = _giong_da_chot(db, run)
    provider = ai.THU_TU_PROVIDER[0]
    model = ai.model_cho(ai.CHUYEN_LOI_THOAI, provider=provider)

    vt = long_tieng.van_tay_long_tieng(
        checksum_ban_ghi=checksum, van_tay_ban=ban.van_tay(),
        ma_giong=ma_giong, provider=provider, model=model)

    # ⭐ Diem chot mang van tay nay. Doi giong hay doi ban bien tap => van tay
    #    doi => khong doan nao duoc tinh la da lam roi.
    xong = su_dung.da_xong(db, run, stage=pipeline.CONTENT_PROCESS, fingerprint=vt)

    dac_diem = dict(can_cu.get("dac_diem") or {}) or can_cu
    con_lai = [d for d in doan_giu if str(d.get("ma") or "") not in xong]
    chuyen: dict[str, dict] = _lay_lai_doan_da_xong(db, run, xong)

    lo_lo = long_tieng.chia_lo(con_lai)
    for i, lo in enumerate(lo_lo):
        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(5 + int(85 * i / max(1, len(lo_lo))), _t('Đang viết lời thoại'))

        ma_da_gui = {str(d.get("ma") or "") for d in lo}
        messages = long_tieng.loi_nhac(
            lo, tat_ca=doan_giu, ngon_ngu_goc=str(goc.get("ngon_ngu") or ""),
            dac_diem_giong=dac_diem)

        kq = ai.goi_tinh_tien(
            db, run, ai.CHUYEN_LOI_THOAI, messages,
            stage=pipeline.CONTENT_PROCESS,
            # 🔑 Khoa cua so cai la LO (mot lan goi = mot dong so cai), con diem
            #    chot la DOAN. Hai truc khac nhau va gop chung lai se hong: mot
            #    lo chua 12 doan nhung chi mot lan tinh tien.
            item_key=f"lo_{i:03d}",
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
                                           "kieu_noi": v["kieu_noi"]})
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

    tai_lieu = long_tieng.dung(giu, chuyen, ma_giong=ma_giong,
                               van_tay_ban=ban.van_tay(),
                               provider=provider, model=model)
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
                    "so_lo": len(lo_lo),
                    "nguon_giong": str(can_cu.get("nguon") or "")},
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
            }
    return ra
