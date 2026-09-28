"""Viec nen dinh ky cua PROMPT AI OMMI — NGUOI GOI cho hai chinh sach da co.

🔑 **Day la nguoi goi ma pha 4-5 thieu.** Hai bang nay khai mot han luu va co san
   ham don, nhung ⛔ khong noi nao chay chung theo lich:

     `ommi_trash.purge_after`  30 ngay  -> `thung_rac.purge_expired` (co san, co
                                           test) chi duoc goi tu MOT route, khi
                                           khach tu bam xoa vinh vien mot muc
     `ommi_handoff.expires_at` 30 phut  -> ⛔ khong ai xoa

⚠️ Day la lan THU BA trong kho nay: `AppManifest.bao_tri` duoc them vao 24/08
   chinh vi `vps` da viet xong `thu_phi_dinh_ky` kem test ma khong ai goi, roi
   `auto_scan_video` lap lai voi `expires_at`. Cung mot hinh dang: **chinh sach
   co, ham kiem co, bao cao co — va khong ai chay.** Mot han luu khong co nguoi
   quet ⛔ khong phai mot chinh sach, no la mot cau van.

⭐ Chay duoi lease `bao_tri` cua nen tang => dung MOT lan tren toan cum du co bao
   nhieu worker. Do la ly do viec nay phai di qua hop dong thay vi mot vong lap
   rieng: so worker mac dinh bang so GPU, va mot vong lap tu dung se xoa N lan
   moi gio.
"""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


def bao_tri() -> None:
    """Don hai thu qua han. ⛔ KHONG duoc nem.

    Nen tang bat va ghi log, nhung mot app nem moi luot la mot dong log rac moi
    gio, va no che nhung loi that (cung ly le voi `auto_scan_video.bao_tri`).
    """
    # ⛔ Import BEN TRONG ham: `manifest.py` duoc nap boi `registry.discover()` o
    #    MOI tien trinh, ke ca nhung tien trinh khong bao gio chay viec nay.
    from platform_core.db import get_session
    from platform_core.storage import get_storage

    from apps.prompt_ai_ommi.services import handoff_stage, thung_rac

    try:
        kho = get_storage()
        for db in get_session():
            try:
                ket_qua = thung_rac.purge_expired(db, storage=kho)
                ve = handoff_stage.don_ve_het_han(db)
                db.commit()
                if ket_qua or ve:
                    _log.info("prompt_ai_ommi bao tri: thung rac %s, ve het han %s",
                              ket_qua, ve)
            finally:
                db.close()
            break
    except Exception:                                    # noqa: BLE001
        # Ghi `exc_info` chu khong nem: mot luot bao tri that bai khong duoc lam
        # dung vong bao tri cua nen tang, va mot `except` im lang o day se an
        # dung cai ta vua dung cong de bat duoc.
        _log.exception("prompt_ai_ommi bao tri that bai")
