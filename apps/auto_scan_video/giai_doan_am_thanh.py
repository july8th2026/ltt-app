"""Giai doan AUDIO_PREPARE — tach giong goc ra khoi nen.

Mot artifact ra:

    bed.wav   nhac nen + tieng dong, da chuan am luong   (kind=audio)

⛔ `vocals.wav` KHONG duoc luu. No la giong goc cua khach; giu lai mot ban sao
   tach rieng cua no la giu mot thu ta khong can va khong hua se giu. Xoa cung
   thu muc tam khi tien trinh con ket thuc.

## Vi sao giai doan nay tu rut ban tieng rieng

Pha 08 da sinh ra mot ban 16 kHz **mot kenh** cho ASR. Dua chinh ban do vao
demucs la sai hai huong: mat toan bo dai tren 8 kHz (Nyquist) — tuc phan lon
thong tin ma phep tach dua vao — va mat anh stereo ma htdemucs dung de phan biet
nguon. Nen o day rut mot ban 44,1 kHz stereo tu **tep goc**. Hai ban tieng cho
hai muc dich khac nhau la dung, khong phai trung lap.

⛔ Prompt 09 cam: khong chep loi, khong dich, khong dieu phoi render trong day.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, lat_cat, nhap_media, tach_tieng
from .giai_doan_media import ThieuNguon, _duong_doc_duoc


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Rut ban day du -> tach nguon -> tron nen -> kiem. Tra ve phan de promote."""
    if not run.source_key:
        raise ThieuNguon(_t('Phiên chạy không có tệp nguồn.'))

    hoi_huy = None
    if ctx is not None and getattr(ctx, "is_cancelled", None):
        hoi_huy = ctx.is_cancelled

    # 🔑 Card do NEN TANG cap. Handler khong bao gio tu chon (I11/O6).
    #    `gpu_env()` tra ve moi truong da gan card duoc lease; khong co GPU thi
    #    no tra ve moi truong hien tai va tien trinh con chay CPU.
    import os
    gpu_env = None
    if ctx is not None and getattr(ctx, "gpu_env", None):
        gpu_env = ctx.gpu_env(base=dict(os.environ))
    # 🔑 Card DA duoc giu cho hay chua — cha biet, con khong. Truyen xuong de con
    #    tu choi thay vi tut xuong CPU im lang (`demucs_runner.chon_thiet_bi`).
    uuid_cap = str(getattr(ctx, "gpu_uuid", "") or "") if ctx is not None else ""

    with tempfile.TemporaryDirectory(prefix="asv-audio-") as tam:
        thu_muc = Path(tam)
        nguon = _duong_doc_duoc(kho, run.source_key, thu_muc)

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(10, _t('Đang chuẩn bị tiếng'))

        day_du = tach_tieng.rut_ban_day_du(nguon, str(thu_muc / "day_du.wav"),
                                           hoi_huy=hoi_huy)

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(30, _t('Đang tách giọng khỏi nhạc nền'))

        # 🔑 Timeout demucs <= ngan sach con lai cua job (`lat_cat`): mac dinh
        #    5.400 s cua `tach_nguon` LON HON tran job 3.600 s, nen truoc day job
        #    bi giet truoc va demucs mo coi van giu GPU.
        ket_qua = tach_tieng.tach_nguon(
            day_du, str(thu_muc / "stem"), gpu_env=gpu_env,
            buoc_gpu=bool(uuid_cap), hoi_huy=hoi_huy,
            timeout=lat_cat.han_tien_trinh_con(
                "audio_prepare",
                tach_tieng.TIMEOUT_TACH_S))

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(75, _t('Đang trộn nhạc nền'))

        nen = tach_tieng.tron_nen(ket_qua["duong"], str(thu_muc / "bed.wav"),
                                  hoi_huy=hoi_huy)

        # ── Kiem ban ra (Prompt 09 muc 7) ────────────────────────────────
        tt = nhap_media.soi(nen)
        if tt["tan_so"] != tach_tieng.TAN_SO_TACH:
            raise nhap_media.MediaError(_t('Nhạc nền sai tần số lấy mẫu.'))
        if tt["so_kenh"] != tach_tieng.SO_KENH_TACH:
            raise nhap_media.MediaError(_t('Nhạc nền sai số kênh.'))

        goc_tt = nhap_media.soi(nguon)
        if abs(tt["thoi_luong"] - goc_tt["thoi_luong"]) > 0.5:
            # Lech thoi luong o day se lam moc thoi gian cua ban long tieng
            # troi so voi hinh — va no troi cang luc cang xa ve cuoi.
            raise nhap_media.MediaError(_t('Nhạc nền lệch thời lượng so với bản gốc.'))

        am = tach_tieng.do_am_luong(nen)

        checksum_nguon = assets.bam_tep(nguon)
        vt = tach_tieng.van_tay_tach(
            checksum_nguon=checksum_nguon,
            phien_ban_ffmpeg_=nhap_media.phien_ban_ffmpeg())

        khoa_nen = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                       stage="audio_prepare", van_tay=vt,
                                       duoi="wav")
        with open(nen, "rb") as f:
            kho.put(khoa_nen, f, content_type="audio/wav")

        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(95, _t('Đang lưu kết quả'))

        return {
            "phan": [{"staging_key": khoa_nen, "kind": "audio", "duoi": "wav",
                      "van_tay": vt}],
            "tom_tat": {
                # ⭐ Ba manh, va chung chi co nghia KHI DUNG CANH NHAU:
                #    `gpu_cap` la card CHA giu cho, `ten_card` la card CON thay.
                #    Mot dau tu bao cao ca hai thi khong doi chieu duoc gi.
                "thiet_bi": ket_qua.get("thiet_bi", ""),
                "gpu_cap": uuid_cap,
                "ten_card": ket_qua.get("ten_card", ""),
                "so_khoi": ket_qua.get("so_khoi", 0),
                "khoi_giay": ket_qua.get("khoi_giay", 0),
                "stem_giu": list(tach_tieng.STEM_GIU),
                "lufs": am["lufs"],
                "dinh_that": am["dinh_that"],
                "thoi_luong": tt["thoi_luong"],
            },
        }
