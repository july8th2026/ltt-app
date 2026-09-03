"""Giai doan `edit_plan` — chot quyet dinh hinh anh truoc khi tieu tien tieng.

Giai doan nay khong tra tien khi preset la `localize_preserve_picture`: khong co
canh nao duoc cat, nen khong co gi de hoi VLM. Do la mot **duong re re tien** co
chu dinh, khong phai mot loi tat.
"""
from __future__ import annotations

import json
import logging

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import ban_bien_tap, canh as canh_mod, hop_dong_v4
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)

#: Phien ban MA cua giai doan, di vao van tay.
PHIEN_BAN_MA = 1


class ThieuChiMuc(ThieuNguon):
    """Chua co chi muc canh de lap ban bien tap."""


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Lap `BanBienTap` va tra ve phan de promote.

    🔑 Thu tu o day la mot phan cua hop dong: **quyet dinh hinh anh chot TRUOC**,
       roi ban chep loi moi duoc loc ve phan giu lai. Doi thu tu la quay lai dung
       `V4-R07` — dich va tra tien cho nhung cau thuoc canh se bi cat.
    """
    from . import features

    settings = dict(run.settings or {})
    preset = str(settings.get("preset") or hop_dong_v4.PRESET_MAC_DINH)

    tt = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    thoi_luong = float(((tt.outputs or {}) if tt else {}).get("thoi_luong") or 0.0)

    # ── Chi muc canh ────────────────────────────────────────────────────────
    #
    # ⛔ `PRESET_GIU_HINH` khong can chi muc chi tiet: khong canh nao bi cat, nen
    #    mot chi muc mot-canh la du va dung. Chay tach canh o day la tra tien
    #    ffmpeg cho mot cau tra loi khong ai doc.
    if preset == hop_dong_v4.PRESET_GIU_HINH:
        if thoi_luong <= 0:
            raise ThieuChiMuc(_t('Chưa có bản media để phân tích cảnh.'))
        ci = canh_mod.ChiMucCanh(
            (canh_mod.Canh("canh_0001", 0.0, thoi_luong),), thoi_luong,
            ghi_chu={"bo_qua_tach_canh": "preset giu nguyen hinh"})
        hieu = ()
    else:
        duong = _nguon_soi_duoc(db, kho, run)
        ci = canh_mod.phan_tich(duong, thoi_luong=thoi_luong,
                                hoi_huy=getattr(ctx, "is_cancelled", None))
        canh_mod.kiem_chi_muc(ci)
        hieu = ()      # ⚠️ Pha 11 dung mien; nguoi goi VLM la pha sau.

    ban_ghi = _ban_ghi(db, kho, run)
    ban = ban_bien_tap.lap_ban(preset=preset, chi_muc=ci,
                               hieu_canh=hieu, ban_ghi=ban_ghi)

    # ── Luu ban + chi muc thanh MOT artifact ───────────────────────────────
    #
    # ⭐ Mot tep chu khong hai: ban bien tap va chi muc canh khong doc duoc tach
    #    roi — mot quyet dinh "cat canh_0007" vo nghia neu khong biet canh do la
    #    khoang thoi gian nao. Luu roi la mo mot duong de hai nua lech phien ban.
    import io

    from . import assets

    vt = van_tay_ban(ban)
    goi = json.dumps({"ban": ban.sang_dict(), "chi_muc": _chi_muc_dict(ci)},
                     ensure_ascii=False, sort_keys=True).encode("utf-8")
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage="edit_plan", van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu bản biên tập'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "ban": ban,
        "chi_muc": ci,
        "tom_tat": {
            "preset": preset,
            "so_canh": len(ci.canh),
            "so_giu": len(ban.cac_ma_giu),
            "so_cat": len(ban.cac_ma_cat),
            "van_tay_ban": ban.van_tay(),
            **dict(ban.ghi_chu),
        },
    }


def _nguon_soi_duoc(db, kho, run) -> str:
    from . import assets, features

    gd = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    khoa = [k for k in ((gd.outputs or {}).get("khoa_asset") or [])
            if str(k).endswith((".mp4", ".mkv", ".mov"))]
    if not khoa:
        raise ThieuChiMuc(_t('Chưa có bản media để phân tích cảnh.'))
    return assets.nguon_soi_duoc(kho, khoa[0])


def _ban_ghi(db, kho, run) -> dict:
    from . import features

    gd = features.giai_doan_theo_ten(db, run.id, "transcribe")
    khoa = [k for k in (((gd.outputs or {}) if gd else {}).get("khoa_asset") or [])
            if str(k).endswith(".json")]
    if not khoa:
        return {}
    try:
        with kho.open(khoa[0]) as f:
            return json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("khong doc duoc ban chep loi (%s)", type(exc).__name__)
        return {}


def _chi_muc_dict(ci) -> dict:
    """Chi muc canh dang luu tru. Cung dang voi `canh.sang_json`, dang doi tuong."""
    return json.loads(canh_mod.sang_json(ci))


def van_tay_ban(ban) -> str:
    """Van tay cua giai doan nay.

    🔑 Gom `PHIEN_BAN_MA` (ma cua giai doan) **va** van tay cua chinh ban bien
       tap. Hai thu doi doc lap: sua mot dong ma o day khong doi quyet dinh, va
       doi mot nguong chinh sach khong doi ma.
    """
    return f"{PHIEN_BAN_MA}-{ban.van_tay()}"
