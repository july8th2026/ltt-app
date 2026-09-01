"""Giai doan CONTENT_PROCESS — dich ban ghi sang tieng Viet.

Mot artifact ra:

    content.json   van ban da xu ly, giu nguyen ma doan   (kind=json)

⛔ Ban ghi nguon **BAT BIEN**. Tep nay chi doc `transcript.json`; no khong bao
   gio ghi de len do (Prompt 11, "explicitly forbidden"). Ly do khong phai su
   gon gang — ban ghi la bang chung ve thu may nghe duoc, ban dich la mot dien
   giai cua no, va ghi de dien giai len bang chung thi mat kha nang doi chieu
   khi khach khieu nai.

⛔ Prompt 11 cam: khong sinh tieng noi trong giai doan nay.

## Day la giai doan DAU TIEN tieu tien that

Nen ba thu chuyen tu ly thuyet sang thuc te o day:

  * `ctx.provider_dispatched()` duoc goi **ngay truoc** khi goi ra ngoai, va no
    ghi xuong CSDL. Mot lan sap sau do doc ra duoc la "co the da goi", chu khong
    phai "chua goi" (I5).
  * `DichMoHo` KHONG BAO GIO duoc thu lai tu dong — provider co the da nhan va
    da tinh tien.
  * `features.kiem_tran_chi` chay truoc moi lo, khong phai mot lan o dau.
"""
from __future__ import annotations

import io
import json

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, ban_ghi, dich_thuat, pipeline, van_ban
from .giai_doan_media import ThieuNguon


class ThieuBanGhi(ThieuNguon):
    """Giai doan chep loi chua sinh ra ban ghi."""


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


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc ban ghi -> dich theo lo -> rap -> kiem. Tra ve phan de promote."""
    goc, checksum = _doc_ban_ghi(db, kho, run)

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(5, _t('Đang dịch'))

    ban_dich = dich_thuat.dich_ban_ghi(db, goc, ctx=ctx)

    tai_lieu = van_ban.dung(goc, ban_dich,
                            provider=dich_thuat.PROVIDER_CHINH,
                            model=dich_thuat.MODEL_CHINH)

    goi = json.dumps(tai_lieu, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = van_ban.van_tay_van_ban(
        checksum_ban_ghi=checksum,
        provider=dich_thuat.PROVIDER_CHINH,
        model=dich_thuat.MODEL_CHINH,
        ngon_ngu_dich=tai_lieu["ngon_ngu_dich"])

    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.CONTENT_PROCESS, van_tay=vt,
                               duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "tom_tat": van_ban.tom_tat(tai_lieu),
    }
