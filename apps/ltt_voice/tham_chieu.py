"""
tham_chieu.py — tra cứu và lưu Voice Profile / biểu diễn engine.

Tách khỏi `features.py` vì hai lý do khác nhau, và cả hai đều đáng:

  · `features.py` là **quy tắc**; tệp này là **cách chạm CSDL và kho**. Trộn hai
    thứ đó thì không test được quy tắc mà không dựng một CSDL.
  · Phiên truy vấn phải **ngắn**. Một lượt sinh tiếng có thể mất hàng chục giây;
    giữ một transaction mở suốt thời gian đó là giữ khoá CSDL trong lúc chờ mạng.
    Cùng bài học đã ghi ở `apps/anhnoibo/jobs.py`.
"""
from __future__ import annotations

import hashlib
import io
import logging

log = logging.getLogger(__name__)

#: Tiền tố khoá trong `platform_core.storage`. Có `owner_id` trong đường dẫn để
#: một lần nhìn vào kho là biết tệp thuộc về ai.
def khoa_nguon(owner_id: str, public_id: str) -> str:
    return f"voice/{owner_id}/{public_id}/source"


def khoa_bieu_dien(owner_id: str, public_id: str, van_tay: str) -> str:
    #: Có vân tay trong khoá để hai biểu diễn của hai revision **không đè nhau**.
    #: Đè nhau thì lùi model về bản cũ sẽ đọc phải biểu diễn của bản mới.
    return f"voice/{owner_id}/{public_id}/repr-{van_tay}.npz"


def van_tay(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


# ── tra cứu ──────────────────────────────────────────────────────────────────

def tim_profile(db, public_id: str, *, owner_id: str):
    """Tìm theo `public_id` **và** chủ sở hữu, trong MỘT truy vấn.

    ⛔ Đừng tách thành "tìm theo id rồi so owner": hai bước thì có một khoảng
       trống ở giữa mà một bản vá sau này rất dễ quên bước hai. Một truy vấn thì
       không quên được.
    """
    from sqlalchemy import select

    from .tables import VoiceProfile
    if not public_id or not owner_id:
        return None
    return db.execute(
        select(VoiceProfile).where(
            VoiceProfile.public_id == str(public_id),
            VoiceProfile.owner_id == str(owner_id))
    ).scalar_one_or_none()


def danh_sach(db, *, owner_id: str, gom_tat: bool = False) -> list:
    from sqlalchemy import select

    from .tables import VoiceProfile
    q = select(VoiceProfile).where(VoiceProfile.owner_id == str(owner_id))
    if not gom_tat:
        q = q.where(VoiceProfile.trang_thai != "revoked")
    return list(db.execute(q.order_by(VoiceProfile.tao_luc.desc())).scalars())


def tim_repr_active(db, profile_id: int):
    from sqlalchemy import select

    from .tables import VoiceRepr
    return db.execute(
        select(VoiceRepr).where(
            VoiceRepr.profile_id == int(profile_id),
            VoiceRepr.trang_thai == "dang_dung")
        .order_by(VoiceRepr.tao_luc.desc())
    ).scalars().first()


def tim_ref_theo_hash(db, profile_id: int, sha256: str):
    from sqlalchemy import select

    from .tables import VoiceRef
    return db.execute(
        select(VoiceRef).where(VoiceRef.profile_id == int(profile_id),
                               VoiceRef.sha256 == str(sha256))
    ).scalar_one_or_none()


# ── kho ──────────────────────────────────────────────────────────────────────

def nap_ref_b64(bieu_dien) -> str:
    """Đọc `.npz` biểu diễn từ kho, trả base64 để gửi sang sidecar."""
    import base64

    from platform_core.storage import get_storage
    st = get_storage()
    with st.open(bieu_dien.storage_key) as f:
        return base64.b64encode(f.read()).decode("ascii")


def luu_bieu_dien(*, owner_id: str, public_id: str, ref_b64: str) -> tuple:
    """Ghi `.npz` biểu diễn vào kho. Trả `(storage_key, van_tay)`."""
    import base64

    from platform_core.storage import get_storage
    raw = base64.b64decode(ref_b64)
    vt = van_tay(raw)
    khoa = khoa_bieu_dien(owner_id, public_id, vt)
    get_storage().put(khoa, io.BytesIO(raw), content_type="application/octet-stream")
    return khoa, vt


def luu_nguon(*, owner_id: str, public_id: str, data: bytes, mime: str) -> str:
    """Ghi tệp GỐC bất biến. Không nén, không chuyển đổi, không cắt.

    ⛔ Bản gốc là thứ duy nhất cho phép **dựng lại** biểu diễn khi lên engine mới
       (QĐ-3). Xử lý nó trước khi lưu là vứt đi khả năng đó, và không ai phát
       hiện ra cho tới ngày cần dùng.
    """
    from platform_core.storage import get_storage
    duoi = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
            "audio/mp4": "m4a", "audio/x-m4a": "m4a"}.get(mime, "bin")
    khoa = f"{khoa_nguon(owner_id, public_id)}.{duoi}"
    get_storage().put(khoa, io.BytesIO(data), content_type=mime)
    return khoa
