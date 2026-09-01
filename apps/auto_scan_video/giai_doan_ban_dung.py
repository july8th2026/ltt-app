"""Giai doan COMPOSE — dung ban dung, va doi chieu MOI tham chieu truoc render.

Mot artifact ra:

    render_manifest.json   ban dung   (kind=json)

⛔ Giai doan nay **khong sinh media**. Prompt 14 cam ro, va ly do la ranh gioi
   G9: tron bien tap vao thi hanh nghia la mot lan doi cong cu render keo theo
   mot lan chay lai ca chuoi AI o thuong nguon.

## Viec that su cua giai doan nay

Dung mot tai lieu thi de. Phan dat gia la **doi chieu moi tham chieu TRUOC khi
ton mot suat render** (Prompt 14 muc 5):

  * moi khoa trong ban dung phai tro toi mot `AsvAsset` **cua chinh chu so huu**;
  * moi artifact do phai con song va con dung checksum;
  * moi doan trong ke hoach phai co mot tep tieng that.

Mot ban dung tro toi mot artifact khong con la mot lan render that bai o phut
thu muoi — sau khi da chiem suat, da tai tep, da giai ma. Bat o day ton vai mili
giay.
"""
from __future__ import annotations

import io
import json

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, ban_dung, nhap_media, pipeline, thoi_gian
from .giai_doan_media import ThieuNguon
from .tables import ASSET_OK


class ThieuDauVao(ThieuNguon):
    """Thieu mot trong cac tai lieu thuong nguon."""


def _khoa_json(db, run, ten_giai_doan: str) -> str:
    from . import features
    s = features.giai_doan_theo_ten(db, run.id, ten_giai_doan)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if s else ""


def _khoa_theo_duoi(db, run, ten_giai_doan: str, duoi: str) -> str:
    from . import features
    s = features.giai_doan_theo_ten(db, run.id, ten_giai_doan)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(duoi)), "") if s else ""


def _doc(kho: Storage, khoa: str) -> dict:
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _khoa_con_dung(db, kho: Storage, run) -> set[str]:
    """Moi khoa artifact CUA CHINH chu so huu, da kiem toan ven.

    ⭐ Kiem toan ven **o day**, khong tin cot `integrity` da luu: ban ghi noi
       `ok` tu lan kiem truoc, con tep thi co the da bien mat trong khoang giua.
    """
    from sqlalchemy import select

    from .tables import AsvAsset

    hang = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run.id,
        AsvAsset.owner_id == run.owner_id)).scalars().all()
    return {a.storage_key for a in hang
            if assets.kiem_toan_ven(db, kho, a) == ASSET_OK}


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc ke hoach + ban ke tieng -> ban dung, da doi chieu day du."""
    khoa_kh = _khoa_json(db, run, pipeline.TIMING_ALIGN)
    if not khoa_kh:
        raise ThieuDauVao(_t('Chưa có kế hoạch thời gian để dựng.'))
    khoa_ke = _khoa_json(db, run, pipeline.VOICE_SYNTHESIS)
    if not khoa_ke:
        raise ThieuDauVao(_t('Chưa có bản kê tiếng để dựng.'))
    khoa_nen = _khoa_theo_duoi(db, run, pipeline.AUDIO_PREPARE, ".wav")
    if not khoa_nen:
        raise ThieuDauVao(_t('Chưa có nhạc nền để dựng.'))
    if not run.source_key:
        raise ThieuDauVao(_t('Phiên chạy không có tệp nguồn.'))

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(20, _t('Đang dựng bản dựng'))

    ke_hoach = _doc(kho, khoa_kh)
    thoi_gian.kiem(ke_hoach)          # con dat hop dong sau khi doc lai (I8)
    ban_ke = _doc(kho, khoa_ke)

    ban = ban_dung.dung(
        khoa_video=run.source_key,
        khoa_nen=khoa_nen,
        ke_hoach=ke_hoach,
        ban_ke_tieng=ban_ke,
        phien_ban_ffmpeg=nhap_media.phien_ban_ffmpeg(),
        tong_giay=float(ke_hoach.get("tong_ms") or 0) / 1000.0)

    # 🔑 Muc 5: doi chieu MOI tham chieu TRUOC khi ton mot suat render.
    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(60, _t('Đang đối chiếu tài nguyên'))
    hop_le = _khoa_con_dung(db, kho, run)
    hop_le.add(run.source_key)        # tep nguon khong phai `AsvAsset`
    ban_dung.kiem(ban, khoa_hop_le=hop_le)

    goi = json.dumps(ban, sort_keys=True, ensure_ascii=False).encode("utf-8")
    with kho.open(khoa_kh) as f:
        cs_kh = assets.bam(f.read())
    vt = ban_dung.van_tay_ban_dung(
        checksum_ke_hoach=cs_kh, khoa_video=run.source_key,
        khoa_nen=khoa_nen,
        phien_ban_ffmpeg=(ban.get("cong_cu") or {}).get("ffmpeg", ""))

    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.COMPOSE, van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "tom_tat": ban_dung.tom_tat(ban),
    }
