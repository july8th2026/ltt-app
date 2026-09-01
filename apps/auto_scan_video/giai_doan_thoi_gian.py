"""Giai doan TIMING_ALIGN — lap ke hoach dat tung doan tieng len truc thoi gian.

Mot artifact ra:

    timing_plan.json   ke hoach dat doan   (kind=json)

⛔ Giai doan nay **khong cham mot tep am thanh nao**. No ra mot KE HOACH; viec
   ghep la cua COMPOSE/RENDER (pha 14/15). Tron hai viec lai la giau mot quyet
   dinh thoi gian ben trong mot phep ghep — noi khong ai di tim no.

⭐ Nho vay ke hoach doc duoc, kiem duoc va **sua duoc** ma khong phai render lai:
   mot lan chay lai chi ton vai mili-giay o day, thay vi ca mot luot ghep.

Thi hanh `ADR-003-mo-hinh-thoi-gian.md`.
"""
from __future__ import annotations

import io
import json

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, pipeline, thoi_gian, van_ban
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

    che_do = str((run.settings or {}).get("timing_mode") or "fit_original")
    ke_hoach = thoi_gian.lap_ke_hoach(
        tl_vb.get("muc") or [], do_dai, tong_giay=tong_giay, che_do=che_do)

    goi = json.dumps(ke_hoach, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = thoi_gian.van_tay_ke_hoach(checksum_van_ban=cs_vb, ban_ke_tieng=cs_ke,
                                    che_do=che_do)

    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.TIMING_ALIGN, van_tay=vt,
                               duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "tom_tat": thoi_gian.tom_tat(ke_hoach),
    }
