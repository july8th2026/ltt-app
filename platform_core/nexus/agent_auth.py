"""Agent chứng minh nó giữ khoá riêng, mà không bao giờ gửi khoá riêng đi.

Q93 ràng buộc 1: khoá riêng **không bao giờ rời máy đó**. Hệ quả là agent không
thể dùng bearer token — một token là thứ chép được, và chép được nghĩa là ai đọc
được ổ đĩa hoặc log của máy đó đều trở thành máy đó. Thay vào đó mỗi request được
**ký**.

## Vì sao Ed25519

Không có tham số nào để chọn sai. RSA đòi chọn độ dài khoá, padding và hàm băm —
ba chỗ để cấu hình sai một cách âm thầm. ECDSA cần nonce ngẫu nhiên cho mỗi lần
ký, và một nonce lặp lại làm **lộ khoá riêng** (đã hạ nhiều hệ thống thật).
Ed25519 tất định, khoá 32 byte, chữ ký 64 byte, và API chỉ có một cách dùng.

## Chuỗi được ký, và vì sao gồm đủ bốn phần

    <METHOD>\\n<path>\\n<timestamp>\\n<sha256 hex cua body>

* **method + path** — thiếu chúng thì một chữ ký lấy từ request vô hại
  (`heartbeat`) đem dùng lại cho request nguy hiểm (`thu hồi`);
* **timestamp** — thiếu nó thì một chữ ký nghe được là dùng lại được **mãi mãi**;
* **băm body** — thiếu nó thì nội dung sửa được mà chữ ký vẫn đúng.

Đây là loại thiết kế mà bỏ một phần nào cũng vẫn "chạy" trong lúc thử, và chỉ
sai khi có người tấn công. Nên bốn phần được viết ra kèm lý do, không phải kèm
một dòng "ký request".

## Cửa sổ thời gian không thay được chống lặp thật

Cửa sổ ±5 phút chặn được việc dùng lại **sau này**, không chặn được việc dùng lại
**ngay lập tức**. Chặn hẳn thì cần lưu nonce đã thấy — một bảng nữa, và một việc
dọn nữa. Với `heartbeat` thì lặp lại vô hại (nó chỉ ghi lại cùng một mốc), nên
cửa sổ là đủ **cho đúng các đường đang mở**. Đường nào có tác dụng phụ không lặp
lại được thì **phải** thêm nonce, và chỗ đó ghi rõ ở đây để không ai mở một
đường như vậy mà tưởng lớp này đã che.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone

#: Tiền tố để một chuỗi khoá lạc ra ngoài còn nhận ra được là gì.
PUBLIC_PREFIX = "ltt_dev_"

#: Ed25519: khoá công khai đúng 32 byte, chữ ký đúng 64 byte. Không có lựa chọn
#: nào khác, và đó là điểm mạnh chứ không phải hạn chế.
KEY_BYTES = 32
SIG_BYTES = 64

#: Lệch đồng hồ cho phép, hai chiều. Máy khách không chạy NTP là chuyện thường,
#: nên quá chặt sẽ khoá người dùng thật ra ngoài; quá rộng thì kéo dài cửa sổ
#: dùng lại chữ ký.
SKEW_S = 300

HEADER_DEVICE = "X-LTT-Device"
HEADER_TIMESTAMP = "X-LTT-Timestamp"
HEADER_SIGNATURE = "X-LTT-Signature"


class AgentAuthError(Exception):
    """Khong xac thuc duoc.

    Thong diep o day la CHAN DOAN CHO NGUOI PHAT TRIEN, khong bao gio den tay
    nguoi dung: `server/nexus/routes.py` bat het va tra ve mot cau chung duy
    nhat, con `devices.doi_ma` doi no thanh mot `NexusError` da dich. Vi vay
    chung co y viet bang ASCII chu khong boc `_()` — boc `_()` se ham y rang
    chung se duoc hien ra, va nguoi doc sau nay se di dich mot thu vo hinh.
    """


def _b64d(value: str) -> bytes:
    """base64url không đệm, cho phép cả bản có đệm."""
    raw = str(value or "").strip()
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def encode_public_key(raw: bytes) -> str:
    """32 byte thô → chuỗi để lưu trong `nexus_devices.public_key`."""
    if len(raw) != KEY_BYTES:
        raise AgentAuthError("public key must be exactly 32 bytes")
    return PUBLIC_PREFIX + _b64e(raw)


def decode_public_key(stored: str) -> bytes:
    """Chuỗi đã lưu → 32 byte thô. Ném `AgentAuthError` nếu sai dạng.

    Kiểm ở **biên nhận vào** (lúc ghép máy) chứ không lúc dùng: một khoá sai dạng
    được lưu xuống nghĩa là thiết bị đó **không bao giờ** xác thực được, và lỗi
    sẽ hiện ra muộn, ở chỗ khó hiểu, dưới dạng "máy không kết nối được".
    """
    value = str(stored or "")
    if not value.startswith(PUBLIC_PREFIX):
        raise AgentAuthError("public key is malformed")
    try:
        raw = _b64d(value[len(PUBLIC_PREFIX):])
    except Exception as exc:                                   # noqa: BLE001
        raise AgentAuthError("public key is malformed") from exc
    if len(raw) != KEY_BYTES:
        raise AgentAuthError("public key has the wrong length")
    return raw


def canonical(method: str, path: str, timestamp: str, body: bytes) -> bytes:
    """Chuỗi được ký. Một chỗ duy nhất, dùng cho cả bên ký và bên kiểm.

    Nếu agent và server tự dựng chuỗi này riêng thì có ngày hai bên lệch một dấu
    xuống dòng, và mọi chữ ký hợp lệ bị từ chối — một sự cố rất khó đọc.
    """
    dau = hashlib.sha256(body or b"").hexdigest()
    return "\n".join([str(method or "").upper(), str(path or ""),
                      str(timestamp or ""), dau]).encode("utf-8")


def check_timestamp(timestamp: str, *, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    try:
        moc = int(str(timestamp or "").strip())
    except (TypeError, ValueError) as exc:
        raise AgentAuthError("timestamp is not an integer") from exc
    lech = abs(current.timestamp() - moc)
    if lech > SKEW_S:
        raise AgentAuthError("timestamp outside the allowed skew")


def verify(*, public_key: str, signature: str, method: str, path: str,
           timestamp: str, body: bytes, now: datetime | None = None) -> None:
    """Ném `AgentAuthError` nếu không hợp lệ. Trả None nếu hợp lệ.

    Trả None thay vì True: một hàm trả bool sẽ có ngày được gọi mà không ai đọc
    giá trị trả về, và lúc đó nó im lặng cho qua. Ném thì không bỏ qua được.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric import ed25519

    check_timestamp(timestamp, now=now)

    raw_key = decode_public_key(public_key)
    try:
        sig = _b64d(signature)
    except Exception as exc:                                   # noqa: BLE001
        raise AgentAuthError("signature is malformed") from exc
    if len(sig) != SIG_BYTES:
        raise AgentAuthError("signature has the wrong length")

    try:
        ed25519.Ed25519PublicKey.from_public_bytes(raw_key).verify(
            sig, canonical(method, path, timestamp, body))
    except InvalidSignature as exc:
        raise AgentAuthError("signature does not verify") from exc


def sign(private_bytes: bytes, *, method: str, path: str,
         timestamp: str, body: bytes) -> str:
    """Ký một request. Đây là ĐƯỜNG CHẠY THẬT của agent, không phải tiện ích test.

    Đặt cạnh `verify` chứ không trong agent: bên ký và bên kiểm phải dùng **cùng**
    hàm `canonical`, và cách chắc chắn nhất để chúng không lệch nhau là ở cùng
    file. Lệch một dấu xuống dòng thì mọi chữ ký hợp lệ bị từ chối, và triệu
    chứng phía khách trông y hệt "sai khoá".

    Tên cũ là `sign_for_test`, và đó là một cái tên nói dối: nó ký **mọi request
    của mọi máy khách**. Đổi tên vì một hàm mang chữ `test` ở đường chạy thật sẽ
    khiến người đọc sau này tưởng có thể bỏ đi.
    """
    from cryptography.hazmat.primitives.asymmetric import ed25519

    key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    return _b64e(key.sign(canonical(method, path, timestamp, body)))


def new_keypair_for_test() -> tuple:
    """`(private_bytes, public_key_da_ma_hoa)`. Chỉ dùng cho test/agent mẫu."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    private = ed25519.Ed25519PrivateKey.generate()
    raw_priv = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption())
    raw_pub = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    return raw_priv, encode_public_key(raw_pub)


__all__ = ["AgentAuthError", "HEADER_DEVICE", "HEADER_SIGNATURE",
           "HEADER_TIMESTAMP", "KEY_BYTES", "PUBLIC_PREFIX", "SIG_BYTES",
           "SKEW_S", "canonical", "check_timestamp", "decode_public_key",
           "encode_public_key", "new_keypair_for_test", "sign",
           "verify"]
