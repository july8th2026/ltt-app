"""Giai doan VOICE_SYNTHESIS — doc ban dich thanh tieng, TUNG DOAN mot.

N artifact ra: mot tep WAV cho MOI doan, cong mot ban ke `voice_index.json`.

## Vi sao mot tep cho moi doan chu khong mot tep cho ca bai

TIMING dat **tung doan** vao dung khe thoi gian cua no. Mot tep lien mach thi
khong con cho de dat — va neu mot doan phai doc lai (dich sua, giong doi), ca
bai phai doc lai theo.

## Phuc hoi o muc DOAN — Prompt 12 muc 7 va cong thoat

Moi doan co van tay rieng (`giong_noi.van_tay_doan`), va khoa luu tru dan xuat
tu van tay do. Nen khi giai doan chay lai:

  * doan da co artifact **con song va con dung** -> BO QUA, khong goi lai,
    khong tra tien lan hai;
  * chi nhung doan con thieu moi duoc sinh.

⭐ Do la **hat nho nhat an toan** ma cong thoat doi. Hat nho hon (chia mot cau
   thanh hai luot) khong an toan: no doi mot doan thanh hai giong doc khac nhau
   o giua cau.

## Ban va mot dieu KHONG duoc lam o day

⛔ Prompt 12 cam ghep/canh thoi gian trong bo chuyen doi provider. Tep nay sinh
   ra cac doan tieng va **khong** ghep chung. Ghep la viec cua TIMING_ALIGN
   (pha 13), va tron vao day la giau mot quyet dinh timing ben trong mot lop
   provider — noi khong ai di tim no.
"""
from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, giong_noi, pipeline, van_ban
from .giai_doan_media import ThieuNguon


class ThieuBanDich(ThieuNguon):
    """Giai doan dich chua sinh ra van ban."""


def _doc_ban_dich(db, kho: Storage, run) -> dict:
    """Van ban da xu ly cua run. Chi doc."""
    from . import features

    truoc = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    khoa = next((k for k in ((truoc.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if truoc else ""
    if not khoa:
        raise ThieuBanDich(_t('Chưa có bản dịch để đọc thành tiếng.'))
    with kho.open(khoa) as f:
        tai_lieu = json.loads(f.read().decode("utf-8"))
    van_ban.kiem(tai_lieu)
    return tai_lieu


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc tung doan thanh tieng. Bo qua doan da co san va con dung."""
    if not giong_noi.san_sang():
        raise giong_noi.GiongError(
            _t('Máy tạo tiếng nói chưa được thiết lập trên máy chủ này.'))

    tai_lieu = _doc_ban_dich(db, kho, run)
    cai_dat = run.settings or {}

    # Giai giong MOT LAN cho ca lan chay — day cung la noi quyen so huu giong
    # duoc kiem (I6/I7). Lam lai cho tung doan la N luot tra CSDL cho mot cau
    # tra loi khong doi.
    ref_b64, preset = giong_noi.giai_giong(
        db, owner_id=run.owner_id,
        voice_id=str(cai_dat.get("voice_id") or ""),
        preset=str(cai_dat.get("preset") or ""))

    muc = list(tai_lieu.get("muc") or [])
    phan: list[dict] = []
    ban_ke: list[dict] = []
    da_sinh = 0

    with tempfile.TemporaryDirectory(prefix="asv-voice-") as tam:
        thu_muc = Path(tam)

        for i, m in enumerate(muc, start=1):
            if ctx is not None and getattr(ctx, "is_cancelled", None) and ctx.is_cancelled():
                raise giong_noi.GiongError(_t('Phiên chạy đã bị huỷ giữa chừng.'))
            if ctx is not None and getattr(ctx, "progress", None):
                ctx.progress(int(5 + 85 * i / max(1, len(muc))),
                             _t('Đang đọc thành tiếng'))

            vt = giong_noi.van_tay_doan(
                ma_doan=m["ma"], chu=m["chu"],
                voice_id=str(cai_dat.get("voice_id") or ""),
                preset=str(preset or ""))

            # ── Phuc hoi o muc DOAN ───────────────────────────────────────
            khoa_ben = assets.dat_khoa(owner_id=run.owner_id, run_id=run.id,
                                       stage=pipeline.VOICE_SYNTHESIS,
                                       van_tay=vt, duoi="wav")
            cu = _doan_con_dung(db, kho, run, khoa_ben)
            if cu is not None:
                ban_ke.append({"ma": m["ma"], "khoa": khoa_ben,
                               "giay": float(cu), "tu_cu": True})
                continue

            wav, _headers = giong_noi.doc_mot_doan(m["chu"], ref_b64=ref_b64,
                                                   preset=preset)
            # ⛔ Kiem TRUOC khi coi doan la xong (muc 8). Do tren TEP THAT, khong
            #    tin header cua may sinh tieng — cung ly do `apps/ltt_voice`
            #    doi chieu hai phia va ghi log khi lech.
            tep = thu_muc / f"{m['ma']}.wav"
            tep.write_bytes(wav)
            giay = giong_noi.kiem_tep_tieng(str(tep))

            khoa_tam = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                           stage=pipeline.VOICE_SYNTHESIS,
                                           van_tay=vt, duoi="wav")
            with open(tep, "rb") as f:
                kho.put(khoa_tam, f, content_type="audio/wav")

            phan.append({"staging_key": khoa_tam, "kind": "audio", "duoi": "wav",
                         "van_tay": vt})
            ban_ke.append({"ma": m["ma"], "khoa": khoa_ben, "giay": giay})
            da_sinh += 1

        # ── Ban ke: cai TIMING doc de biet doan nao o dau ─────────────────
        goi = json.dumps({"schema": 1, "doan": ban_ke}, sort_keys=True,
                         ensure_ascii=False).encode("utf-8")
        vt_ke = assets.bam(goi)[:32]
        khoa_ke = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                      stage=pipeline.VOICE_SYNTHESIS,
                                      van_tay=vt_ke, duoi="json")
        kho.put(khoa_ke, io.BytesIO(goi), content_type="application/json")
        phan.append({"staging_key": khoa_ke, "kind": "json", "duoi": "json",
                     "van_tay": vt_ke})

        return {
            "phan": phan,
            "tom_tat": {
                "so_doan": len(muc),
                "so_doan_moi_sinh": da_sinh,
                "so_doan_dung_lai": len(muc) - da_sinh,
                "tong_giay": round(sum(float(d["giay"]) for d in ban_ke), 2),
                "preset": str(preset or ""),
            },
        }


def _doan_con_dung(db, kho: Storage, run, khoa: str):
    """Thoi luong cua mot doan da co san VA con dung, hoac None.

    Hai dieu kien, ca hai bat buoc (I10): ban ghi con, **va** tep con song va
    con dung checksum. "Co mot tep dung ten" khong phai la cache hop le (O13).
    """
    from .tables import ASSET_OK, AsvAsset
    from sqlalchemy import select

    row = db.execute(select(AsvAsset).where(
        AsvAsset.storage_key == khoa,
        AsvAsset.owner_id == run.owner_id)).scalars().first()
    if row is None:
        return None
    if assets.kiem_toan_ven(db, kho, row) != ASSET_OK:
        return None
    duong = kho.local_path(khoa) if hasattr(kho, "local_path") else None
    if not duong:
        return 0.0      # khong doc duoc duong dan cuc bo: tin ban ghi da kiem
    try:
        return giong_noi.kiem_tep_tieng(duong)
    except giong_noi.GiongError:
        return None
