"""Ghép máy, thu hồi máy, và nhịp tim. Không có gì chạm luồng điều khiển.

Framework-free có chủ ý: các quy tắc ở đây quyết định **một máy có được tin
không**, và chúng phải kiểm được mà không cần dựng HTTP app.

## Mã ghép: cái gì thật sự chống được dò

`NexusEnrollment.attempts` **không** phải hàng rào chống dò mã, và nói rõ ở đây
để không ai tưởng thế. Việc đổi mã tra cứu **theo digest**, nên một mã sai không
khớp dòng nào — không có dòng để tăng bộ đếm. Bộ đếm đó chỉ đếm những lần đổi
hỏng của một mã **đã tìm thấy** (hết hạn, đã dùng), tức là dấu hiệu ai đó đang
mò một mã có thật.

Cái thật sự chống dò là ba thứ khác:

1. **Entropy** — 8 ký tự từ bảng 32 ký tự = 40 bit. Trong cửa sổ 5 phút, dò trúng
   đòi hàng tỉ lần thử.
2. **Cửa sổ ngắn** — `ENROLL_TTL_S` = 5 phút, và mã chết hẳn khi đã dùng.
3. **Giới hạn nhịp ở tầng HTTP** — việc của route, không phải của module này.
   Module này **không** tự giới hạn nhịp; nơi gọi phải làm, và đó là một phần
   của hợp đồng chứ không phải chi tiết bỏ quên.

Bảng chữ cái bỏ `0/O/1/I/L` không phải để đẹp: mã này được **đọc cho nhau nghe
và gõ tay**, nên nhầm `0` với `O` là lỗi người dùng chắc chắn xảy ra.

## Vì sao không có hàm nào cấp vé phiên ở đây

Vé phiên (Q93 ràng buộc 2) là miền riêng, sẽ ở `sessions.py`. Trộn nó vào đây sẽ
làm "máy này của ai" và "ai được vào máy này" thành cùng một câu hỏi — trong khi
chúng là hai câu, và câu thứ hai mới là chỗ uỷ quyền được quyết định.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from platform_core.i18n import _ as _t
from platform_core.nexus.tables import (ENROLL_TTL_S, NexusDevice,
                                        NexusEnrollment)

#: Bỏ 0/O/1/I/L: mã được đọc miệng và gõ tay.
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LEN = 8
CODE_GROUP = 4

#: Bao lâu không có nhịp tim thì coi là offline. Rộng hơn nhịp gửi vài lần để
#: một lần mất mạng thoáng qua không làm máy nhấp nháy trong danh sách.
OFFLINE_AFTER_S = 180


class NexusError(Exception):
    """Không ghép được. Thông điệp an toàn để hiện cho khách."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def digest_code(code: str) -> str:
    """Băm có domain separation. Không dùng KDF chậm — xem docstring module."""
    sach = normalize_code(code)
    return hashlib.sha256(("ltt-nexus-enroll\0" + sach).encode("utf-8")).hexdigest()


def normalize_code(code: str) -> str:
    """Bỏ gạch/khoảng trắng, viết hoa. Người gõ thế nào cũng nhận."""
    return "".join(ch for ch in str(code or "").upper()
                   if ch in ALPHABET)


def format_code(code: str) -> str:
    """`ABCD-EFGH` — chia nhóm để đọc và gõ đỡ sai."""
    sach = normalize_code(code)
    return "-".join(sach[i:i + CODE_GROUP]
                    for i in range(0, len(sach), CODE_GROUP))


# ── Ghép máy ─────────────────────────────────────────────────────────────────

def tao_ma_ghep(db, *, user_id: str, now: datetime | None = None) -> tuple:
    """Sinh một mã ghép cho tài khoản. Trả `(row, mã gốc)`.

    Mã gốc **chỉ trả về một lần** — CSDL chỉ giữ digest. Nơi gọi hiện nó cho
    người dùng rồi quên đi.
    """
    chu = str(user_id or "").strip()
    if not chu:
        raise NexusError(_t("Mã ghép phải thuộc về một tài khoản."))

    current = now or _now()
    raw = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
    row = NexusEnrollment(
        id=str(uuid.uuid4()), user_id=chu, code_digest=digest_code(raw),
        created_at=current, expires_at=current + timedelta(seconds=ENROLL_TTL_S))
    db.add(row)
    db.flush()
    return row, raw


def doi_ma(db, *, code: str, public_key: str, display_name: str = "",
           hardware_fingerprint: str = "", platform: str = "",
           agent_version: str = "", ip: str = "",
           now: datetime | None = None) -> NexusDevice:
    """Đổi mã ghép lấy một thiết bị được tin. Mã chết ngay sau đó.

    Mọi lý do từ chối đều ném **cùng một thông điệp**: mã sai, mã hết hạn và mã
    đã dùng phải không phân biệt được từ bên ngoài, nếu không thì việc dò mã
    biết được mình đang tới gần.
    """
    from platform_core.nexus import agent_auth

    current = now or _now()
    sach = normalize_code(code)
    khoa = str(public_key or "").strip()
    if not khoa:
        raise NexusError(_t("Thiết bị phải gửi khoá công khai của nó."))
    # Kiểm dạng khoá NGAY Ở BIÊN. Lưu một khoá sai dạng nghĩa là thiết bị đó
    # không bao giờ xác thực được, và lỗi sẽ hiện ra muộn dưới dạng "máy không
    # kết nối được" — một triệu chứng không dẫn về nguyên nhân này.
    try:
        agent_auth.decode_public_key(khoa)
    except agent_auth.AgentAuthError as exc:
        raise NexusError(_t("Khoá công khai của thiết bị không hợp lệ.")) from exc
    if len(sach) != CODE_LEN:
        raise NexusError(_t("Mã ghép không dùng được."))

    row = db.execute(select(NexusEnrollment).where(
        NexusEnrollment.code_digest == digest_code(sach))).scalar_one_or_none()
    if row is None:
        raise NexusError(_t("Mã ghép không dùng được."))

    if not row.is_open(now=current):
        # Đếm cả lần hỏng trên một mã CÓ THẬT: đó là dấu hiệu ai đó đang mò.
        row.attempts = int(row.attempts or 0) + 1
        db.flush()
        raise NexusError(_t("Mã ghép không dùng được."))

    trung = db.execute(select(NexusDevice).where(
        NexusDevice.public_key == khoa)).scalar_one_or_none()
    if trung is not None:
        # Cùng khoá công khai = cùng máy đó cài lại. Không tạo dòng thứ hai:
        # hai dòng cùng khoá làm "thu hồi máy này" thành câu không trả lời được.
        if trung.user_id != row.user_id:
            raise NexusError(_t("Mã ghép không dùng được."))
        trung.revoked_at = None
        trung.revoked_by = ""
        trung.display_name = str(display_name or trung.display_name)[:120]
        trung.agent_version = str(agent_version or "")[:32]
        device = trung
    else:
        device = NexusDevice(
            id=str(uuid.uuid4()), user_id=row.user_id,
            display_name=str(display_name or "")[:120], public_key=khoa,
            hardware_fingerprint=str(hardware_fingerprint or "")[:128],
            platform=str(platform or "")[:32],
            agent_version=str(agent_version or "")[:32], created_at=current)
        db.add(device)
        db.flush()

    row.consumed_at = current
    row.device_id = device.id
    row.claimed_ip = str(ip or "")[:64]
    db.flush()
    return device


def dang_ky_bang_tai_khoan(db, *, email: str, password: str, public_key: str,
                           display_name: str = "", hardware_fingerprint: str = "",
                           platform: str = "", agent_version: str = "",
                           now: datetime | None = None) -> NexusDevice:
    """Model B (Q101 / D-P7): client đăng nhập bằng **tài khoản LTT** (email+mật
    khẩu) rồi tự đăng ký MÁY này dưới tài khoản đó — thay đường mã-ghép-từ-web
    (`doi_ma`), vì Model B bỏ web-broker: web chỉ còn docs/tài khoản/credit.

    Xác thực qua `users.xac_thuc` (constant-time, không lộ email nào có thật).
    Cùng khoá công khai = cùng máy cài lại → tái dùng dòng cũ, **không** tạo dòng
    thứ hai (giống `doi_ma`), để "thu hồi máy này" vẫn là câu trả lời được. Khoá
    đã thuộc tài khoản KHÁC thì từ chối — không cướp máy giữa các tài khoản.
    """
    from platform_core import users
    from platform_core.nexus import agent_auth

    current = now or _now()
    khoa = str(public_key or "").strip()
    if not khoa:
        raise NexusError(_t("Thiết bị phải gửi khoá công khai của nó."))
    try:
        agent_auth.decode_public_key(khoa)
    except agent_auth.AgentAuthError as exc:
        raise NexusError(_t("Khoá công khai của thiết bị không hợp lệ.")) from exc

    user = users.xac_thuc(db, email=str(email or ""), password=str(password or ""))
    if user is None:
        raise NexusError(_t("Email hoặc mật khẩu không đúng."))

    trung = db.execute(select(NexusDevice).where(
        NexusDevice.public_key == khoa)).scalar_one_or_none()
    if trung is not None:
        if trung.user_id != user.id:
            raise NexusError(_t("Máy này đã đăng ký ở tài khoản khác."))
        trung.revoked_at = None
        trung.revoked_by = ""
        trung.display_name = str(display_name or trung.display_name)[:120]
        trung.agent_version = str(agent_version or "")[:32]
        db.flush()
        return trung

    device = NexusDevice(
        id=str(uuid.uuid4()), user_id=user.id,
        display_name=str(display_name or "")[:120], public_key=khoa,
        hardware_fingerprint=str(hardware_fingerprint or "")[:128],
        platform=str(platform or "")[:32],
        agent_version=str(agent_version or "")[:32], created_at=current)
    db.add(device)
    db.flush()
    return device


# ── Quyền sở hữu, thu hồi, hiện diện ─────────────────────────────────────────

def cua_chu(db, *, user_id: str, device_id: str) -> NexusDevice | None:
    """Thiết bị của đúng chủ này, hoặc None.

    Nơi gọi phải biến None thành **404**, không bao giờ 403 — Q93 ràng buộc 9,
    cùng lý do đã viết trong `public_api/principal.py`: trả 403 biến mỗi
    `device_id` thành một máy tra cứu.
    """
    chu = str(user_id or "").strip()
    if not chu:
        return None
    row = db.get(NexusDevice, str(device_id or ""))
    if row is None or row.user_id != chu:
        return None
    return row


def danh_sach(db, *, user_id: str, gom_da_thu_hoi: bool = False) -> list:
    stmt = select(NexusDevice).where(NexusDevice.user_id == str(user_id or ""))
    if not gom_da_thu_hoi:
        stmt = stmt.where(NexusDevice.revoked_at.is_(None))
    return list(db.execute(stmt.order_by(NexusDevice.created_at.desc())).scalars())


def thu_hoi(db, device: NexusDevice, *, by: str,
            now: datetime | None = None) -> bool:
    """Thu hồi một thiết bị. Trả False nếu nó đã bị thu hồi rồi.

    `by` bắt buộc và được ghi lại: Q93 ràng buộc 5 đòi mọi hành động của admin
    để lại dấu **chủ thiết bị đọc được**. Một hàm cho phép thu hồi ẩn danh là
    một hàm xoá mất câu trả lời đó.
    """
    ai = str(by or "").strip()
    if not ai:
        raise NexusError(_t("Thu hồi phải ghi rõ ai thu hồi."))
    if device.revoked_at is not None:
        return False
    device.revoked_at = now or _now()
    device.revoked_by = ai[:64]
    db.flush()
    return True


def nhip_tim(db, device: NexusDevice, *, now: datetime | None = None) -> bool:
    """Ghi nhận thiết bị còn sống. Thiết bị đã thu hồi thì KHÔNG được ghi.

    Trả về False khi bị từ chối, để nơi gọi biết mà bảo agent dừng hẳn thay vì
    tiếp tục gõ cửa mãi.
    """
    if device.revoked_at is not None:
        return False
    device.last_seen_at = now or _now()
    db.flush()
    return True


def dang_online(device: NexusDevice, *, now: datetime | None = None) -> bool:
    """Suy ra từ nhịp tim gần nhất, không lưu cột trạng thái riêng.

    Một cột `is_online` sẽ nói dối ngay khi tiến trình ghi nó chết giữa chừng —
    và đó chính là lúc người ta cần con số này đúng nhất.
    """
    if device.revoked_at is not None:
        return False
    moc = _aware(device.last_seen_at)
    if moc is None:
        return False
    return (now or _now()) - moc <= timedelta(seconds=OFFLINE_AFTER_S)


# ── Dọn dẹp ──────────────────────────────────────────────────────────────────
#
# Hai thời hạn khác nhau vì hai loại dòng có giá trị khác nhau:
#
# * mã **đã dùng** là một mẩu kiểm toán — nó trả lời "máy này được ghép lúc nào,
#   từ IP nào". Giữ theo cùng cửa sổ mà Q75 đặt cho lịch sử của khách;
# * mã **hết hạn mà không ai dùng** không kiểm toán gì cả. Giữ một tháng đủ để
#   nhìn ra một chuỗi lần dò, rồi bỏ.
#
# Không có "dọn presence": trạng thái online được **suy ra** từ `last_seen_at`
# chứ không lưu thành cột, nên không có gì để hết hạn. Một cột `is_online` mới
# là thứ cần người đi dọn — và nó sẽ nói dối đúng lúc tiến trình ghi nó chết.

GIU_MA_DA_DUNG_NGAY = 365
GIU_MA_HET_HAN_NGAY = 30


def don_ma_het_han(db, *, now: datetime | None = None) -> int:
    """Xoá mã ghép đã hết giá trị. Trả số dòng đã xoá.

    Gọi từ vòng bảo trì đã có lease, **không** gọi trong vòng job: số tiến trình
    worker mặc định bằng số GPU, nên một việc nền đặt sai chỗ sẽ chạy ở mọi tiến
    trình. Đó là nguyên nhân gốc của cả ba lỗi P0 mà H36 phải đi sửa.
    """
    from sqlalchemy import and_, delete, or_

    current = now or _now()
    ket = db.execute(delete(NexusEnrollment).where(or_(
        # Đã dùng: mốc tính từ lúc ghép, vì đó là thời điểm có ý nghĩa kiểm toán.
        and_(NexusEnrollment.consumed_at.isnot(None),
             NexusEnrollment.consumed_at
             < current - timedelta(days=GIU_MA_DA_DUNG_NGAY)),
        # Không ai dùng: mốc tính từ lúc hết hạn, không phải lúc tạo.
        and_(NexusEnrollment.consumed_at.is_(None),
             NexusEnrollment.expires_at
             < current - timedelta(days=GIU_MA_HET_HAN_NGAY)),
    )))
    db.flush()
    return int(ket.rowcount or 0)


__all__ = ["ALPHABET", "CODE_LEN", "GIU_MA_DA_DUNG_NGAY", "GIU_MA_HET_HAN_NGAY",
           "NexusError", "OFFLINE_AFTER_S", "cua_chu", "dang_online",
           "danh_sach", "digest_code", "doi_ma", "don_ma_het_han", "format_code",
           "nhip_tim", "normalize_code", "tao_ma_ghep", "thu_hoi"]
