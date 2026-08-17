"""Giữ khoá riêng của thiết bị sao cho chép file KHÔNG bằng nhân bản máy.

Q93 ràng buộc 1 nói khoá riêng không bao giờ rời máy đó. Một file chứa 32 byte
thô **không** thoả điều đó theo nghĩa có ý nghĩa: ai copy được file là có được
thiết bị, và "không rời máy" chỉ còn là một câu trong tài liệu.

Trên Windows, DPAPI (`CryptProtectData`) mã hoá bằng khoá dẫn xuất từ **tài
khoản Windows đang chạy**. Hệ quả đúng thứ ta cần: mang file sang máy khác, hay
mở bằng tài khoản khác trên cùng máy, đều **không giải mã được**. Đây là biện
pháp đối ứng của T3 trong `docs/nexus/04_THREAT_MODEL.md`.

Nói rõ giới hạn, vì nó quyết định T3 được giảm tới đâu: DPAPI **không** chống
được kẻ đã chiếm quyền chính tài khoản đó trên chính máy đó — kẻ ấy gọi
`CryptUnprotectData` được y như agent. Threat model đã ghi "một máy đã bị chiếm
hoàn toàn thì đã mất"; mục tiêu ở đây là chặn việc **lan sang máy khác**, không
phải cứu một máy đã mất.

## Vì sao không ném khoá vào Credential Manager hay TPM

Credential Manager cũng dùng DPAPI bên dưới, thêm một API mà không thêm tính
chất. TPM thì mạnh hơn thật (khoá không trích xuất được kể cả bởi admin), nhưng
đòi máy có TPM, đòi xử lý máy không có, và đòi một đường di trú khi thay máy —
ba nhánh nữa cho một sản phẩm chưa có người dùng đầu tiên. Ghi ra đây là để lần
sau nâng cấp thì biết đổi cái gì lấy cái gì, chứ không phải để bảo TPM là thừa.

## Máy không phải Windows

Chỉ để phát triển. Ghi khoá thô ra file thì **mất** tính chất trên, nên đường đó
mặc định **đóng**: phải đặt `LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY=1` mới chạy
được, và agent nói thẳng ra rằng nó đang kém an toàn. Fail-closed, vì một bản
build lỡ tay mang đường plaintext ra production là đúng loại lỗi không ai phát
hiện cho tới khi muộn.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

#: Đặt tên rõ để một file lạc ra ngoài còn nhận ra được là gì, và để người tìm
#: thấy nó biết ngay đây không phải rác tạm.
KEY_FILENAME = "device_key.bin"
PUBLIC_FILENAME = "device_public.txt"
DEVICE_ID_FILENAME = "device_id.txt"

PLAINTEXT_ENV = "LTT_NEXUS_AGENT_ALLOW_PLAINTEXT_KEY"


class KeystoreError(Exception):
    """Không đọc/ghi được khoá. Thông điệp không bao giờ chứa khoá."""


def _is_windows() -> bool:
    return sys.platform.startswith("win")


# ── DPAPI qua ctypes ─────────────────────────────────────────────────────────
#
# Dùng `ctypes` chứ không `pywin32`: agent chạy trên máy KHÁCH, nên mỗi phụ
# thuộc thêm là một thứ nữa phải đóng gói, ký, và vá khi có CVE. `ctypes` nằm
# trong thư viện chuẩn.

def _dpapi(protect: bool, data: bytes) -> bytes:
    import ctypes
    import ctypes.wintypes as wt

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wt.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _blob(raw: bytes) -> BLOB:
        buf = ctypes.create_string_buffer(raw, len(raw))
        return BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

    vao, ra = _blob(data), BLOB()
    # `entropy` gắn thêm một chuỗi cố định của ứng dụng: một tiến trình khác
    # chạy cùng tài khoản mà không biết chuỗi này thì không giải mã được, kể cả
    # khi nó gọi đúng DPAPI.
    entropy = _blob(b"ltt-nexus-agent-v1")

    crypt32 = ctypes.windll.crypt32
    ham = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    ok = ham(ctypes.byref(vao), None, ctypes.byref(entropy), None, None, 0,
             ctypes.byref(ra))
    if not ok:
        raise KeystoreError(
            "DPAPI tu choi. Khoa nay thuoc mot tai khoan Windows khac, hoac "
            "mot may khac." if not protect else "DPAPI khong ma hoa duoc.")
    try:
        return ctypes.string_at(ra.pbData, ra.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(ra.pbData)


def _cho_phep_plaintext() -> bool:
    return str(os.environ.get(PLAINTEXT_ENV, "")).strip().lower() in (
        "1", "true", "yes", "on")


class Keystore:
    """Thư mục chứa danh tính của một thiết bị."""

    def __init__(self, thu_muc: str | Path):
        self.dir = Path(thu_muc)

    # ── Đường dẫn ────────────────────────────────────────────────────────────

    @property
    def key_path(self) -> Path:
        return self.dir / KEY_FILENAME

    @property
    def public_path(self) -> Path:
        return self.dir / PUBLIC_FILENAME

    @property
    def device_id_path(self) -> Path:
        return self.dir / DEVICE_ID_FILENAME

    # ── Khoá riêng ───────────────────────────────────────────────────────────

    def da_co_khoa(self) -> bool:
        return self.key_path.exists()

    def sinh_khoa(self) -> str:
        """Sinh cặp khoá **tại chỗ**. Trả khoá công khai đã mã hoá chuỗi.

        Khoá riêng không bao giờ được trả về từ hàm này — nơi gọi không cần nó,
        và một giá trị đã trả về là một giá trị có thể bị log.
        """
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

        self.dir.mkdir(parents=True, exist_ok=True)
        self._ghi_khoa(raw_priv)

        public = _ma_hoa_public(raw_pub)
        self.public_path.write_text(public, encoding="ascii")
        return public

    def _ghi_khoa(self, raw_priv: bytes) -> None:
        if _is_windows():
            self.key_path.write_bytes(_dpapi(True, raw_priv))
            return
        if not _cho_phep_plaintext():
            raise KeystoreError(
                "May nay khong phai Windows nen khong co DPAPI. Luu khoa tho "
                f"lam mat tinh chat 'chep file khong bang nhan ban may'. Dat "
                f"{PLAINTEXT_ENV}=1 neu day la may phat trien.")
        self.key_path.write_bytes(raw_priv)
        # 0600: khong thay the duoc DPAPI, chi la thu it te nhat con lam duoc.
        try:
            os.chmod(self.key_path, 0o600)
        except OSError as exc:
            raise KeystoreError(f"khong siet duoc quyen file khoa: {exc}") from exc

    def doc_khoa(self) -> bytes:
        """Khoá riêng thô. Chỉ dùng ngay để ký, không cất lại đi đâu."""
        if not self.da_co_khoa():
            raise KeystoreError("Chua co khoa thiet bi. Chay `enroll` truoc.")
        raw = self.key_path.read_bytes()
        if _is_windows():
            return _dpapi(False, raw)
        if not _cho_phep_plaintext():
            raise KeystoreError(
                f"Khoa dang o dang tho. Dat {PLAINTEXT_ENV}=1 de doc.")
        return raw

    def doc_public(self) -> str:
        if not self.public_path.exists():
            raise KeystoreError("Chua co khoa cong khai. Chay `enroll` truoc.")
        return self.public_path.read_text(encoding="ascii").strip()

    # ── Danh tính do server cấp ──────────────────────────────────────────────

    def luu_device_id(self, device_id: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.device_id_path.write_text(str(device_id or "").strip(),
                                       encoding="ascii")

    def doc_device_id(self) -> str:
        if not self.device_id_path.exists():
            raise KeystoreError("Chua ghep may nay. Chay `enroll` truoc.")
        return self.device_id_path.read_text(encoding="ascii").strip()

    def xoa(self) -> None:
        """Quên hẳn danh tính. Dùng khi máy bị thu hồi.

        Xoá cả ba file: giữ lại `device_id` mà mất khoá thì agent sẽ gõ cửa mãi
        bằng một danh tính nó không chứng minh được.
        """
        for p in (self.key_path, self.public_path, self.device_id_path):
            try:
                p.unlink()
            except FileNotFoundError:
                pass


def _ma_hoa_public(raw_pub: bytes) -> str:
    """Cùng định dạng mà server chờ. Import muộn để giữ agent nhẹ."""
    from platform_core.nexus.agent_auth import encode_public_key

    return encode_public_key(raw_pub)


__all__ = ["DEVICE_ID_FILENAME", "KEY_FILENAME", "Keystore", "KeystoreError",
           "PLAINTEXT_ENV", "PUBLIC_FILENAME"]
