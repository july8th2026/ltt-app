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

def tim_profile(db, public_id: str, *, owner_id: str, cho_dung_chung: bool = False):
    """Tìm theo `public_id` **và** chủ sở hữu, trong MỘT truy vấn.

    ⛔ Đừng tách thành "tìm theo id rồi so owner": hai bước thì có một khoảng
       trống ở giữa mà một bản vá sau này rất dễ quên bước hai. Một truy vấn thì
       không quên được.

    `cho_dung_chung=True` mở thêm các giọng **kho chung của nền tảng**
    (`dung_chung=True`) — chúng không thuộc ai nhưng ai cũng ĐỌC được.

    🔴 THAM SỐ NÀY MẶC ĐỊNH `False`, VÀ THỨ TỰ ĐÓ QUAN TRỌNG.

       Hàm này là chỗ **duy nhất** kiểm quyền sở hữu giọng, nên nó cũng là chỗ
       một lỗi ở đây trở thành một lỗ rò dữ liệu sinh trắc. Mặc định đóng nghĩa
       là mọi lời gọi CŨ giữ nguyên hành vi cũ, và chỉ những cửa **cố ý** mở
       mới thấy kho chung.

    ⛔ Và nó chỉ mở đường ĐỌC. Sửa, tắt, xoá một giọng dùng chung vẫn đòi đúng
       chủ — xem `_chi_chu_so_huu`. Gộp "ai dùng được" với "ai sửa được" vào một
       phép kiểm là cách một khách tắt mất giọng của cả nền tảng.
    """
    from sqlalchemy import or_, select

    from .tables import VoiceProfile
    if not public_id:
        return None
    dk = [VoiceProfile.public_id == str(public_id)]
    if cho_dung_chung:
        if owner_id:
            dk.append(or_(VoiceProfile.owner_id == str(owner_id),
                          VoiceProfile.dung_chung.is_(True)))
        else:
            dk.append(VoiceProfile.dung_chung.is_(True))
    elif owner_id:
        dk.append(VoiceProfile.owner_id == str(owner_id))
    else:
        return None
    return db.execute(select(VoiceProfile).where(*dk)).scalar_one_or_none()


def chi_chu_so_huu(ho_so, owner_id: str) -> bool:
    """Người này có được **SỬA** hồ sơ đó không (tắt, đổi tên, xoá).

    ⛔ Tách hẳn khỏi "có được DÙNG không". Một giọng dùng chung thì mọi khách
       đọc được, nhưng chỉ chủ sở hữu — nền tảng — mới đổi được. Không tách thì
       khách đầu tiên bấm "Tắt giọng này" sẽ tắt nó cho tất cả mọi người.
    """
    return bool(ho_so is not None and owner_id
                and str(ho_so.owner_id) == str(owner_id))


def danh_sach(db, *, owner_id: str, gom_tat: bool = False,
              gom_dung_chung: bool = False) -> list:
    """Giọng của một người. `gom_dung_chung` thêm kho chung của nền tảng.

    ⛔ Mặc định KHÔNG gồm kho chung, cùng lý do với `tim_profile`: màn nào muốn
       thấy nó phải nói ra. Một danh sách âm thầm dài thêm là cách một cửa
       "quản lý giọng của tôi" bỗng liệt kê cả giọng nó không được sửa.
    """
    from sqlalchemy import or_, select

    from .tables import VoiceProfile
    dk = VoiceProfile.owner_id == str(owner_id)
    if gom_dung_chung:
        dk = or_(dk, VoiceProfile.dung_chung.is_(True))
    q = select(VoiceProfile).where(dk)
    if not gom_tat:
        q = q.where(VoiceProfile.trang_thai != "revoked")
    # Kho chung xuống dưới giọng của chính khách: thứ họ tự tạo là thứ họ đi tìm.
    return list(db.execute(
        q.order_by(VoiceProfile.dung_chung.asc(),
                   VoiceProfile.tao_luc.desc())).scalars())


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
