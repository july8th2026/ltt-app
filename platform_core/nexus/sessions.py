"""Vé phiên: chỗ DUY NHẤT quyết định ai được vào máy nào (Q93 ràng buộc 2).

`devices.py` trả lời "máy này của ai". Đây trả lời "ai được mở phiên vào nó" —
hai câu khác nhau, và câu thứ hai mới là chỗ uỷ quyền xảy ra. Trộn chúng vào một
module sẽ làm ranh giới ấy mờ đi đúng chỗ nó cần rõ nhất.

## Ràng buộc nằm trong CHỮ KÝ, không nằm trong kỷ luật

Q93 ràng buộc 5: admin **không cấp được vé** cho thiết bị mình không sở hữu.
Cách sai là viết một hàm `cap_ve(user_id, device_id)` rồi dặn nhau "nhớ kiểm chủ
sở hữu trước khi gọi". Dặn nhau thì có ngày quên, và ngày quên đó không ai thấy.

Cách ở đây: `cap_ve` nhận **đối tượng thiết bị** và **tự** so `device.user_id`
với người xin vé. Không có tham số nào cho phép bỏ qua phép so đó, và không có
cờ `force`. Muốn cấp vé cho máy người khác thì phải sửa hàm này — một thay đổi
nhìn thấy được trong diff, không phải một lần quên.

## Vì sao dùng một lần

Một vé dùng lại được là một vé bị chép lại được. Vé ở đây chết ngay khi đổi
thành phiên: `consumed_at` khác NULL là hết. Cửa sổ sống tính bằng **phút** —
đủ để agent nhận và nối, không đủ để nằm trong một file log rồi bị nhặt lại.

## Vì sao hàng phiên KHÔNG bị xoá

Q93 ràng buộc 6: mỗi phiên là một bản ghi **bất biến**. Sau sự cố, câu hỏi duy
nhất quan trọng là "ai đã vào máy tôi, lúc nào, từ đâu" — và không ai hỏi nó
trước khi cần. Kết thúc phiên **ghi thêm** (`ended_at`, `end_reason`), không xoá
và không sửa lại quá khứ.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from platform_core import secretbox
from platform_core.i18n import _ as _t
from platform_core.nexus.devices import NexusError
from platform_core.nexus.tables import NexusDevice, NexusSession

#: Vé sống bao lâu. Phút, không phải giờ: nó chỉ cần đủ cho agent nhận và nối.
TICKET_TTL_S = 120

#: Quyền của một phiên. `xem` không gửi phím/chuột — có thật ở tầng engine hay
#: không là việc N1 phải **đo**, không phải việc tin.
QUYEN_XEM = "xem"
QUYEN_DIEU_KHIEN = "dieu_khien"
QUYEN_HOP_LE = (QUYEN_XEM, QUYEN_DIEU_KHIEN)

#: Lý do kết thúc. Ghi thành hằng số vì chúng đi vào báo cáo kiểm toán, nên
#: chúng đổi như một hợp đồng đổi, không như một chuỗi trong code đổi.
KET_THUC_BINH_THUONG = "binh_thuong"
KET_THUC_HET_HAN = "het_han"
KET_THUC_THU_HOI = "thu_hoi"
KET_THUC_MAT_KET_NOI = "mat_ket_noi"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def digest_ticket(raw: str) -> str:
    """Băm có domain separation, khác hẳn không gian của mã ghép.

    Domain separation không phải nghi thức: nếu hai loại bí mật băm cùng cách,
    một digest lấy được ở bảng này có thể đem thử ở bảng kia.
    """
    return hashlib.sha256(
        ("ltt-nexus-ticket\0" + str(raw or "")).encode("utf-8")).hexdigest()


def cap_ve(db, *, user_id: str, device: NexusDevice, quyen: str = QUYEN_DIEU_KHIEN,
           controller_ip: str = "", now: datetime | None = None) -> tuple:
    """Cấp vé cho **chủ** của thiết bị. Trả `(row, vé gốc)`.

    Ném `NexusError` khi người xin không phải chủ, khi thiết bị đã bị thu hồi,
    hoặc khi quyền không hợp lệ. Vé gốc chỉ trả về **một lần**.
    """
    xin = str(user_id or "").strip()
    if not xin:
        raise NexusError(_t("Phiên phải thuộc về một tài khoản."))
    if str(quyen) not in QUYEN_HOP_LE:
        raise NexusError(_t("Quyền của phiên không hợp lệ."))

    # Q93 ràng buộc 5, thi hành ở đây chứ không nhờ nơi gọi nhớ.
    if device is None or device.user_id != xin:
        raise NexusError(_t("Không tìm thấy thiết bị."))
    if device.revoked_at is not None:
        raise NexusError(_t("Thiết bị này đã bị thu hồi."))

    current = now or _now()
    raw = secrets.token_urlsafe(32)
    row = NexusSession(
        id=str(uuid.uuid4()), user_id=xin, device_id=device.id,
        ticket_digest=digest_ticket(raw), quyen=str(quyen),
        controller_ip=str(controller_ip or "")[:64], issued_at=current,
        expires_at=current + timedelta(seconds=TICKET_TTL_S))
    db.add(row)
    db.flush()
    return row, raw


def doi_ve(db, *, ticket: str, now: datetime | None = None) -> NexusSession:
    """Đổi vé lấy một phiên đang mở. Vé chết ngay sau đó.

    Kiểm **lại** thiết bị ở đây chứ không tin lúc cấp: giữa lúc cấp vé và lúc
    dùng, chủ máy có thể đã bấm thu hồi — và đó chính là lúc việc thu hồi phải
    có tác dụng.

    Mọi lý do từ chối nói **cùng một câu**, cùng lý do như mã ghép.
    """
    current = now or _now()
    raw = str(ticket or "").strip()
    if len(raw) < 16:
        raise NexusError(_t("Vé phiên không dùng được."))

    row = db.execute(select(NexusSession).where(
        NexusSession.ticket_digest == digest_ticket(raw))).scalar_one_or_none()
    if row is None or not row.con_doi_duoc(now=current):
        raise NexusError(_t("Vé phiên không dùng được."))

    device = db.get(NexusDevice, row.device_id)
    if device is None or device.revoked_at is not None:
        raise NexusError(_t("Vé phiên không dùng được."))

    row.consumed_at = current
    db.flush()
    return row


def ket_thuc(db, session: NexusSession, *, ly_do: str = KET_THUC_BINH_THUONG,
             now: datetime | None = None) -> bool:
    """Đóng một phiên. Trả False nếu nó đã đóng rồi.

    Ghi thêm chứ không sửa lại quá khứ: `ended_at` và `end_reason` là hai cột
    mới được điền, phần còn lại của dòng giữ nguyên như lúc phiên bắt đầu.
    """
    if session.ended_at is not None:
        return False
    session.ended_at = now or _now()
    session.end_reason = str(ly_do or KET_THUC_BINH_THUONG)[:32]
    _xoa_engine(session)
    db.flush()
    return True


def thu_hoi_ve(db, session: NexusSession, *, by: str,
               now: datetime | None = None) -> bool:
    """Giết một vé chưa dùng, hoặc cắt một phiên đang chạy.

    `by` bắt buộc, cùng lý do như `devices.thu_hoi`: một hành động không ghi ai
    làm là một hành động xoá mất câu trả lời sau sự cố.
    """
    ai = str(by or "").strip()
    if not ai:
        raise NexusError(_t("Thu hồi phải ghi rõ ai thu hồi."))
    if session.revoked_at is not None:
        return False
    current = now or _now()
    session.revoked_at = current
    session.revoked_by = ai[:64]
    if session.ended_at is None:
        session.ended_at = current
        session.end_reason = KET_THUC_THU_HOI
    _xoa_engine(session)
    db.flush()
    return True


def bao_engine(db, session: NexusSession, *, engine_id: str, secret: str,
               now: datetime | None = None) -> None:
    """Agent của máy đích báo chi tiết kết nối RustDesk cho một phiên (W3/W4).

    Chỉ chấp nhận khi vé **đã đổi** (`consumed_at` khác NULL) và phiên **còn mở**:
    báo engine cho một vé chưa đổi, hoặc một phiên đã kết thúc/thu hồi, là báo
    cho một thứ không còn tồn tại — từ chối thẳng thay vì lưu một credential mồ côi.

    `secret` (mật khẩu một-lần) được **mã hoá at-rest ngay tại đây** rồi mới chạm
    tới ORM — không có đường nào để mật khẩu thô đi vào `session` rồi lỡ được ghi
    log/nhìn thấy. `engine_id` không bí mật nên lưu thẳng.
    """
    current = now or _now()
    eid = str(engine_id or "").strip()
    sec = str(secret or "")
    if not eid or not sec:
        raise NexusError(_t("Thiếu thông tin kết nối."))

    # Báo engine cũng chính là lúc **kích hoạt** phiên: agent chỉ đặt mật khẩu
    # SAU KHI thấy một vé hợp lệ dành cho nó (Q93 ràng buộc 2 — engine kiểm vé,
    # không chỉ control plane cấp). Nếu vé còn đổi được thì tiêu nó ngay đây; nếu
    # đã đổi rồi (agent báo lại) thì chấp nhận; còn lại — đã đóng/hết hạn — từ chối.
    if session.con_doi_duoc(now=current):
        session.consumed_at = current
    if not session.dang_chay(now=current):
        raise NexusError(_t("Phiên không còn mở."))

    session.engine_id = eid[:64]
    session.engine_secret_enc = secretbox.ma_hoa(sec)
    session.engine_reported_at = current
    db.flush()


def lay_ket_noi(db, session: NexusSession, *, user_id: str,
                now: datetime | None = None) -> dict:
    """Controller (chủ phiên) lấy chi tiết kết nối để mở RustDesk.

    Hai phép kiểm độc lập, cùng tinh thần `cap_ve`: **chủ** (`session.user_id`
    phải khớp người xin — nếu không, 404 ở tầng route, không phải 403), và phiên
    **còn mở + đã có agent báo**. Chỉ khi đó mới giải mã mật khẩu và trả về.

    Mật khẩu chỉ tồn tại **trong phản hồi này** — không ghi log, không cache.
    """
    if session.user_id != str(user_id or "").strip():
        raise NexusError(_t("Không tìm thấy phiên."))
    current = now or _now()
    if not session.dang_chay(now=current):
        raise NexusError(_t("Phiên không còn mở."))
    if session.engine_reported_at is None or not session.engine_secret_enc:
        raise NexusError(_t("Máy đích chưa sẵn sàng."))

    return {
        "engine_id": session.engine_id,
        "secret": secretbox.giai_ma(session.engine_secret_enc),
        "quyen": session.quyen,
        "expires_at": session.expires_at,
    }


def _xoa_engine(session: NexusSession) -> None:
    """Xoá mật khẩu phiên khỏi dòng. Gọi khi phiên kết thúc/thu hồi — mật khẩu
    một-lần không được sống lâu hơn phiên nó phục vụ. `engine_id` giữ lại (không
    bí mật, còn giá trị kiểm toán)."""
    session.engine_secret_enc = ""


def cho_kich_hoat(db, *, device_id: str, now: datetime | None = None) -> list:
    """Vé đã cấp cho một thiết bị mà **chưa đổi** và **còn hạn**.

    Đây là thứ agent cần biết ở mỗi nhịp tim: một phiên khách vừa yêu cầu điều
    khiển, agent phải đặt mật khẩu engine rồi báo lại (`bao_engine` sẽ kích hoạt).
    Chỉ trả vé còn đổi được — vé hết hạn/thu hồi không phải việc agent làm gì nữa.
    """
    current = now or _now()
    rows = db.execute(select(NexusSession).where(
        NexusSession.device_id == str(device_id or ""),
        NexusSession.consumed_at.is_(None),
        NexusSession.revoked_at.is_(None))).scalars().all()
    return [r for r in rows if r.con_doi_duoc(now=current)]


def lay_phien(db, *, session_id: str) -> NexusSession | None:
    """Một phiên theo id, hoặc None. Không kiểm quyền — nơi gọi kiểm."""
    return db.get(NexusSession, str(session_id or ""))


def dang_mo(db, *, device_id: str, now: datetime | None = None) -> list:
    """Các phiên đang chạy trên một thiết bị.

    Dùng để hiện chỉ báo "đang có người điều khiển" (Q93 ràng buộc 7) và để cắt
    hết khi chủ máy bấm thu hồi.
    """
    current = now or _now()
    rows = db.execute(select(NexusSession).where(
        NexusSession.device_id == str(device_id or ""),
        NexusSession.consumed_at.isnot(None),
        NexusSession.ended_at.is_(None))).scalars().all()
    return [row for row in rows if row.dang_chay(now=current)]


def lich_su(db, *, user_id: str, limit: int = 50) -> list:
    """Nhật ký phiên của một tài khoản, mới nhất trước.

    Đây là thứ trả lời "ai đã vào máy tôi" — nên nó là bề mặt của **khách**,
    không phải của admin.
    """
    return list(db.execute(
        select(NexusSession)
        .where(NexusSession.user_id == str(user_id or ""))
        .order_by(NexusSession.issued_at.desc())
        .limit(max(1, min(int(limit), 500)))).scalars())


__all__ = ["KET_THUC_BINH_THUONG", "KET_THUC_HET_HAN", "KET_THUC_MAT_KET_NOI",
           "KET_THUC_THU_HOI", "QUYEN_DIEU_KHIEN", "QUYEN_HOP_LE", "QUYEN_XEM",
           "TICKET_TTL_S", "cap_ve", "dang_mo", "digest_ticket", "doi_ve",
           "ket_thuc", "lich_su", "thu_hoi_ve"]
