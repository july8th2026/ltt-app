"""Dich vu dung sau `POST /tai-len/{id}/de-xuat-vung` — tach khoi `routes.py`
26/09 vi tran hop dong app (900 dong / 30 handler, `test_423`).

## Route chi con lam BON viec: CSRF, dang nhap, goi ham o day, dich ngoai le
## thanh ma HTTP. Moi quyet dinh "doc phien the nao, tai tep tam luc nao" nam
## ca o day — dung `test_423::test_routes_chi_lo_HTTP`.

Xem `do_vung.de_xuat` cho luat "GIAI DOAN 2" (day CHI la mot DE XUAT, khong
bao gio tu ghi vao `vung_che`) va docstring cu o `routes.py` (git history) cho
ly do goi diem nay: day la DIEM DUY NHAT con tep cuc bo TRUOC khi tao lan chay
— duong multipart nho thi tep chi song trong than request `POST /tao`, bien
mat ngay sau.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from platform_core import upload_sessions
from platform_core.models import UPLOAD_READY
from platform_core.storage import get_storage

from . import do_vung, features


class PhienChuaSan(Exception):
    """Luot tai khong ton tai, khong phai cua nguoi goi, hoac chua o READY.

    Route bien ngoai le nay thanh 404 (⛔ khong phai 403 — xem `_run_cua_toi`
    trong `routes.py` cho cung ly do I6: 403 xac nhan `upload_id` co that).
    """


def _phan_tich_tranh(tranh: str) -> tuple[tuple[float, float], ...]:
    """JSON `[[y0, y1], ...]` tu trinh duyet -> tuple cap so thuc.

    `tranh` la cac cap vung khach DA VE (bat ky loai nao), de V4b tranh chong
    len chung (BAT BIEN 2 cua `do_vung.py`). Rong = chua ve gi.

    ⛔ Khong bao gio nem: day la du lieu khach GO trong JS, mot loi go dang do
    (`{khong phai json`) khong duoc lam sap ca yeu cau — chi coi nhu chua ve
    gi (`test_4802::test_tranh_json_hong_khong_lam_sap_route`).
    """
    try:
        tho = json.loads(tranh) if tranh else []
    except (TypeError, ValueError):
        return ()
    if not isinstance(tho, list):
        return ()
    ra: list[tuple[float, float]] = []
    for cap in tho:
        try:
            y0, y1 = float(cap[0]), float(cap[1])
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        ra.append((y0, y1))
    return tuple(ra)


def de_xuat_cho_phien(db, upload_id: str, user_id, tranh: str) -> dict:
    """Doc phien tai len (PHAM VI CHU SO HUU) roi goi `do_vung.de_xuat`.

    Nem `PhienChuaSan` khi khong tim thay / khong phai cua `user_id` / chua
    o trang thai `UPLOAD_READY` — route bien thanh 404.
    """
    phien = upload_sessions.owned(db, session_id=str(upload_id or ""),
                                  user_id=user_id, app_slug=features.SLUG)
    if phien is None or phien.status != UPLOAD_READY:
        raise PhienChuaSan()

    tranh_tuples = _phan_tich_tranh(tranh)
    kho = get_storage()
    duong = kho.local_path(phien.staging_key)
    tmp_path = ""
    try:
        if not duong:
            # Kho tu xa (R2): tai VE mot ban cuc bo tam thoi — `do_vung` mo
            # video bang `cv2.VideoCapture`, no doi mot DUONG TEP tren dia.
            suffix = Path(str(phien.filename or "video.mp4")).suffix or ".mp4"
            with tempfile.NamedTemporaryFile(
                    prefix="asv-dovung-", suffix=suffix, delete=False) as tmp:
                tmp_path = tmp.name
                with kho.open(phien.staging_key) as nguon:
                    while True:
                        khoi = nguon.read(1024 * 1024)
                        if not khoi:
                            break
                        tmp.write(khoi)
            duong = tmp_path
        return do_vung.de_xuat(duong, tranh=tranh_tuples)
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
