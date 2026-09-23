"""Tai len NHIEU PHAN, tiep tuc duoc sau khi dut — tep 2 GB dut o 73% chay tiep tu 73%.

## Vi sao thay mot lenh PUT bang nhieu phan

Duong ben vung cu (`features.tao_ve_tai_len`, V6 pha 08) cap MOT presigned PUT
cho ca tep. Dut mang o 73% cua 2 GB = gui lai tu 0%, va "thu lai 3 lan" chi la
ba lan gui lai tu 0%.

⇒ Hop dong S3 multipart qua `platform_core.storage` (`multipart_*`):
  trinh duyet cat tep thanh phan `CO_PHAN`, xin ve TUNG phan, PUT thang len kho
  (R2) hoac qua route cua app (kho cuc bo — dev/test). Tiep tuc = hoi kho phan
  nao da co (`ListParts`) roi chi gui phan con thieu.

## Chu so huu, han, toan ven

- Moi thao tac tra `UploadSession` qua `upload_sessions.owned(...)` — loc theo
  `user_id` + `app_slug` NGAY TRONG truy van: ma cua nguoi khac = "khong tim
  thay", khong phai "khong co quyen".
- Han TRUOT `GIA_HAN_S` sau moi phan (tran `HAN_TOI_DA_S` tinh tu luc tao): bo
  do thi het han nhanh va `upload_sessions.sweep` huy luot dang do
  (`multipart_abort`); dang tai cham thi khong bi cat giua chung.
- Moi phan co MD5 (base64, dung dinh dang `Content-MD5`): R2 kiem nho header da
  ky; kho cuc bo tu tinh. Kich thuoc phan phai DUNG ke hoach — phan lech co bi
  coi nhu chua co, va `hoan_tat` tu choi ghep.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from platform_core import upload_sessions
from platform_core.i18n import _ as _t
from platform_core.models import UPLOAD_DELETED, UPLOAD_PENDING, UPLOAD_READY
from platform_core.storage import StorageError

from .features import (KIEU_VIDEO_HOP_LE, SLUG, TRAN_BEN_VUNG, AsvError,
                       KhongTimThay)

#: Co mot phan. 16 MiB: >= 5 MiB (san cua R2 cho moi phan tru phan cuoi), xa
#: duoi tran 100 MB cua Cloudflare (duong cuc bo di qua tunnel), va 2 GiB chi
#: con 128 phan — dut mang mat toi da 16 MiB, khong phai ca tep.
CO_PHAN = 16 * 1024 * 1024

#: Truoc F-08 (`platform_core/upload_sessions.py`): `expected_size` la
#: `Integer` (int4 tren PostgreSQL) trong khi `TRAN_BEN_VUNG` = 2 GiB = 2**31
#: dung bang tran do -> tep DUNG 2 GiB thanh loi 500 `DataError`. Kep tam thoi
#: o `2**31-1` o day. Cot do nay la BigInteger (migration `d7bc2f8fbf0f`) nen
#: tran that su di theo `TRAN_BEN_VUNG`, khong con can kep rieng.
TRAN_BYTE = int(TRAN_BEN_VUNG)

GIA_HAN_S = 2 * 60 * 60
HAN_TOI_DA_S = 48 * 60 * 60
HAN_VE_PHAN_S = 60 * 60


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _utc(v: datetime) -> datetime:
    return v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)


def so_phan(co: int) -> int:
    return max(1, -(-int(co) // CO_PHAN))


def co_cua_phan(co: int, so: int) -> int:
    """Kich thuoc KE HOACH cua phan `so` (1..so_phan). Moi phan CO_PHAN, tru phan cuoi."""
    n = so_phan(co)
    if not 1 <= int(so) <= n:
        raise AsvError(_t('Số thứ tự phần không hợp lệ.'))
    return CO_PHAN if int(so) < n else int(co) - CO_PHAN * (n - 1)


def md5_hop_le(md5_b64: str) -> str:
    s = str(md5_b64 or "").strip()
    try:
        if len(base64.b64decode(s, validate=True)) == 16:
            return s
    except (binascii.Error, ValueError):
        pass
    raise AsvError(_t('Thiếu hoặc sai mã kiểm MD5 của phần.'))


def _phien(db: Session, *, owner_id: str, upload_id: str,
           cho_phep_xong: bool = False):
    phien = upload_sessions.owned(db, session_id=str(upload_id or ""),
                                  user_id=owner_id, app_slug=SLUG)
    if phien is None:
        raise KhongTimThay(_t('Không tìm thấy lượt tải lên.'))
    if cho_phep_xong and phien.status == UPLOAD_READY:
        return phien
    if phien.status != UPLOAD_PENDING or _utc(phien.expires_at) <= _bay_gio():
        raise AsvError(_t('Lượt tải lên đã hết hạn hoặc đã kết thúc.'))
    return phien


def _gia_han(phien) -> None:
    moi = min(_bay_gio() + timedelta(seconds=GIA_HAN_S),
              _utc(phien.created_at) + timedelta(seconds=HAN_TOI_DA_S))
    if moi > _utc(phien.expires_at):
        phien.expires_at = moi


def _mo_ta(phien, da_co: list[int]) -> dict:
    n = so_phan(phien.expected_size)
    return {"upload_id": phien.id, "co": int(phien.expected_size),
            "co_phan": CO_PHAN, "so_phan": n, "da_co": da_co,
            "xong": phien.status == UPLOAD_READY}


def bat_dau(db: Session, kho, *, owner_id: str, ten_tep: str, kieu: str,
            co: int) -> dict:
    if not kho.multipart_supported():
        raise AsvError(_t('Kho không hỗ trợ tải lên nhiều phần.'))
    phien = upload_sessions.create(
        db, user_id=owner_id, app_slug=SLUG, filename=ten_tep,
        content_type=kieu, expected_size=int(co), max_size=TRAN_BYTE,
        allowed_types=KIEU_VIDEO_HOP_LE, ttl_s=GIA_HAN_S)
    kho.multipart_create(phien.staging_key, content_type=phien.content_type)
    return _mo_ta(phien, [])


def phan_da_co(kho, phien) -> list[int]:
    """Phan kho DA nhan VA dung kich thuoc ke hoach. Phan lech = chua co."""
    try:
        ds = kho.multipart_list_parts(phien.staging_key)
    except StorageError as exc:
        raise AsvError(_t('Lượt tải lên không còn trên kho. Hãy tải lại từ đầu.')) from exc
    n = so_phan(phien.expected_size)
    return [p.part_number for p in ds if 1 <= p.part_number <= n
            and p.size == co_cua_phan(phien.expected_size, p.part_number)]


def trang_thai(db: Session, kho, *, owner_id: str, upload_id: str) -> dict:
    phien = _phien(db, owner_id=owner_id, upload_id=upload_id, cho_phep_xong=True)
    if phien.status == UPLOAD_READY:
        return _mo_ta(phien, list(range(1, so_phan(phien.expected_size) + 1)))
    return _mo_ta(phien, phan_da_co(kho, phien))


def ve_phan(db: Session, kho, *, owner_id: str, upload_id: str, so: int,
            md5_b64: str) -> dict:
    """Ve PUT cho phan `so`. `url` None = kho cuc bo: route tu nhan phan."""
    phien = _phien(db, owner_id=owner_id, upload_id=upload_id)
    co = co_cua_phan(phien.expected_size, so)
    md5 = md5_hop_le(md5_b64)
    _gia_han(phien)
    dich = kho.multipart_part_url(phien.staging_key, int(so), md5,
                                  ttl_s=HAN_VE_PHAN_S)
    if dich is None:
        return {"url": None, "method": "PUT", "headers": {}, "co": co}
    return {"url": dich.url, "method": dich.method,
            "headers": dict(dich.headers or {}), "co": co}


def nhan_phan(db: Session, kho, *, owner_id: str, upload_id: str, so: int,
              md5_b64: str, luong) -> int:
    """Nhan mot phan QUA may chu (kho cuc bo). Sai MD5 / sai co -> AsvError."""
    phien = _phien(db, owner_id=owner_id, upload_id=upload_id)
    co = co_cua_phan(phien.expected_size, so)
    md5 = md5_hop_le(md5_b64)
    try:
        nhan = kho.multipart_put_part(phien.staging_key, int(so), luong, md5,
                                      max_bytes=co)
    except StorageError as exc:
        raise AsvError(str(exc)) from exc
    if nhan != co:
        raise AsvError(_t('Kích thước phần không khớp kế hoạch tải lên.'))
    _gia_han(phien)
    return nhan


def hoan_tat(db: Session, kho, *, owner_id: str, upload_id: str) -> dict:
    """Ghep du phan -> object `staging_key` -> `upload_sessions.confirm` (READY).

    ⭐ Goi lai sau khi da xong (phan hoi lan truoc bi dut mang) tra ve cung ket
       qua, khong loi: phien READY, hoac object da ghep ma chua kip confirm.
    """
    phien = _phien(db, owner_id=owner_id, upload_id=upload_id, cho_phep_xong=True)
    if phien.status != UPLOAD_READY:
        n = so_phan(phien.expected_size)
        try:
            da_co = phan_da_co(kho, phien)
        except AsvError:
            if not kho.exists(phien.staging_key):
                raise
            da_co = None                     # da ghep o lan goi truoc
        if da_co is not None:
            thieu = sorted(set(range(1, n + 1)) - set(da_co))
            if thieu:
                raise AsvError(_t('Còn thiếu {n} phần, chưa ghép được tệp.')
                               .format(n=len(thieu)))
            try:
                kho.multipart_complete(phien.staging_key, n)
            except StorageError as exc:
                raise AsvError(str(exc)) from exc
        try:
            phien = upload_sessions.confirm(db, kho, phien)
        except upload_sessions.UploadSessionError as exc:
            raise AsvError(str(exc)) from exc
    return _mo_ta(phien, list(range(1, so_phan(phien.expected_size) + 1)))


def huy(db: Session, kho, *, owner_id: str, upload_id: str) -> None:
    """Khach bo luot tai: huy phan tren kho NGAY, khong doi bo don."""
    phien = _phien(db, owner_id=owner_id, upload_id=upload_id)
    kho.multipart_abort(phien.staging_key)
    phien.status = UPLOAD_DELETED
    phien.updated_at = _bay_gio()
    db.flush()
