"""
Encrypted token storage for Facebook OAuth2 tokens.
Fernet (AES-128-CBC + HMAC-SHA256) via cryptography lib.
Key is derived from machine UUID — tokens won't work on other machines.
Falls back to plain JSON if cryptography is not installed (with warning).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False
    import warnings
    warnings.warn(
        "\n\n"
        "⚠️  SECURITY WARNING: 'cryptography' package is NOT installed.\n"
        "   Facebook OAuth tokens will be stored as PLAIN TEXT.\n"
        "   Run:  pip install cryptography\n"
        "   Then restart the application.\n",
        stacklevel=2,
    )

# None = tu dong giai qua LTT_DATA_DIR luc tao doi tuong (xem _default_token_file).
# Dat mot duong dan cu the de ep buoc — test dang dung cach nay.
TOKEN_FILE: Optional[str] = None


def _default_token_file() -> str:
    """Nơi lưu token, giải qua ranh giới đường dẫn của P2.

    Trước đây là hằng số `os.path.join("data", "tokens.enc")` — tương đối theo
    thư mục làm việc. Trên máy chủ, dịch vụ chạy tại `C:\\LTTPlatform\\app` nên
    token rơi vào `app\\data\\tokens.enc`, tức **nằm trong thư mục bị xoá và
    thay toàn bộ mỗi lần cập nhật**. Mất token là mọi tài khoản Facebook/TikTok
    phải kết nối lại, và không có cách khôi phục.
    """
    if TOKEN_FILE:
        return TOKEN_FILE
    try:
        from core.runtime_paths import data_path
        return data_path("tokens.enc")
    except Exception:
        return os.path.join("data", "tokens.enc")


_SALT = b"fb_bot_token_salt_v1_2026"

# BUG-07/OPT-01 fix: shared singleton instance for the default TOKEN_FILE path.
# Callers without a specific path should use get_default_store() instead of
# constructing TokenStore() repeatedly (which re-decrypts on every call).
_default_store: Optional["TokenStore"] = None
_default_store_lock = threading.Lock()


def get_default_store() -> "TokenStore":
    """Return the process-wide shared TokenStore instance for TOKEN_FILE.

    Thread-safe (double-checked locking). All read-only access should
    prefer this over `TokenStore()` to avoid repeated file decryption.
    Writers still hold the store's own `_lock` for mutations.
    """
    global _default_store
    if _default_store is None:
        with _default_store_lock:
            if _default_store is None:
                _default_store = TokenStore()
    return _default_store


# ─── Machine-key derivation ───────────────────────────────────────────────────

def _get_machine_id() -> str:
    """Return a stable, machine-specific string for key derivation."""
    try:
        if platform.system() == "Windows":
            import winreg
            reg = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            guid, _ = winreg.QueryValueEx(reg, "MachineGuid")
            return str(guid)
    except Exception:
        pass
    return f"{platform.node()}_{platform.system()}_{platform.machine()}"


def _external_key_material() -> Optional[bytes]:
    """Operator-provisioned key material (ADR-013), independent of machine
    identity.

    Set via `LTT_TOKEN_ENCRYPTION_KEY` (the raw secret string) or
    `LTT_TOKEN_ENCRYPTION_KEY_FILE` (path to a file containing it) so
    encrypted tokens survive a VPS reinstall/redeploy without forcing
    every account to be re-authorized. Neither variable is required — when
    unset, key derivation falls back to the existing machine-bound method,
    so desktop behavior is byte-for-byte unchanged. Never logged.
    """
    raw = os.environ.get("LTT_TOKEN_ENCRYPTION_KEY", "").strip()
    if raw:
        return raw.encode("utf-8")
    key_file = os.environ.get("LTT_TOKEN_ENCRYPTION_KEY_FILE", "").strip()
    if key_file and os.path.exists(key_file):
        material = Path(key_file).read_bytes().strip()
        if material:
            return material
    return None


def _derive_key(salt: bytes = _SALT) -> bytes:
    """Derive a Fernet key from either the external override (if set) or
    the machine identity, combined with *salt* so different token stores
    (Facebook vs. TikTok) sharing one external secret still get distinct
    keys — matching the pre-existing per-store-salt design."""
    material = _external_key_material() or _get_machine_id().encode("utf-8")
    digest = hashlib.sha256(material + salt).digest()
    return base64.urlsafe_b64encode(digest)


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class PageInfo:
    id: str
    name: str
    access_token: str
    category: str = ""
    picture_url: str = ""
    selected: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "access_token": self.access_token,
            "category": self.category,
            "picture_url": self.picture_url,
            "selected": self.selected,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PageInfo":
        return cls(
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            access_token=str(d.get("access_token", "")),
            category=str(d.get("category", "")),
            picture_url=str(d.get("picture_url", "")),
            selected=bool(d.get("selected", True)),
        )


@dataclass
class AccountInfo:
    fb_user_id: str
    name: str
    user_token: str
    token_expires_at: str           # ISO datetime string; "" = no expiry
    pages: list = field(default_factory=list)   # list[dict] — PageInfo.to_dict()
    connected_at: str = ""
    is_system_user: bool = False    # True = BM System User token (paste-imported, not OAuth)

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        pages_out = []
        for p in self.pages:
            if isinstance(p, PageInfo):
                pages_out.append(p.to_dict())
            elif isinstance(p, dict):
                pages_out.append(p)
        return {
            "fb_user_id": self.fb_user_id,
            "name": self.name,
            "user_token": self.user_token,
            "token_expires_at": self.token_expires_at,
            "pages": pages_out,
            "connected_at": self.connected_at,
            "is_system_user": self.is_system_user,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AccountInfo":
        return cls(
            fb_user_id=str(d.get("fb_user_id", "")),
            name=str(d.get("name", "")),
            user_token=str(d.get("user_token", "")),
            token_expires_at=str(d.get("token_expires_at", "")),
            pages=list(d.get("pages", [])),
            connected_at=str(d.get("connected_at", "")),
            is_system_user=bool(d.get("is_system_user", False)),
        )

    # ── Page helpers ───────────────────────────────────────────────────────

    def get_pages_list(self) -> list[PageInfo]:
        result = []
        for p in self.pages:
            if isinstance(p, dict):
                result.append(PageInfo.from_dict(p))
            elif isinstance(p, PageInfo):
                result.append(p)
        return result

    def get_selected_pages(self) -> list[PageInfo]:
        return [p for p in self.get_pages_list() if p.selected]

    def get_page_by_id(self, page_id: str) -> Optional[PageInfo]:
        for p in self.get_pages_list():
            if p.id == page_id:
                return p
        return None

    def get_page_by_name(self, name: str) -> Optional[PageInfo]:
        for p in self.get_pages_list():
            if p.name == name:
                return p
        return None

    def set_page_selected(self, page_id: str, selected: bool):
        for p in self.pages:
            pid = p.get("id") if isinstance(p, dict) else getattr(p, "id", "")
            if pid == page_id:
                if isinstance(p, dict):
                    p["selected"] = selected
                else:
                    p.selected = selected

    # ── Token expiry ───────────────────────────────────────────────────────

    def days_until_expiry(self) -> int:
        """
        Days until token expires.
        Returns -1 if no expiry set (e.g. Page Access Token = permanent).
        Returns negative int if already expired.
        """
        if not self.token_expires_at:
            return -1
        try:
            # BUG-04 fix: handle both naive (legacy) and tz-aware ISO timestamps.
            # Naive timestamps are assumed to be local time (matches legacy writers).
            from datetime import timezone as _tz
            exp = datetime.fromisoformat(self.token_expires_at)
            if exp.tzinfo is not None:
                # Modern path: tz-aware, compare in UTC
                delta = exp - datetime.now(_tz.utc)
            else:
                # Legacy path: both naive, both local
                delta = exp - datetime.now()
            return int(delta.total_seconds() // 86400)
        except Exception:
            return -1

    def token_status_label(self) -> tuple[str, str]:
        """Returns (label_text, color_hex)."""
        days = self.days_until_expiry()
        if days == -1:
            return "✅ Vĩnh viễn", "#4CAF50"
        if days > 14:
            return f"✅ {days} ngày còn", "#4CAF50"
        if days > 7:
            return f"⚠️ {days} ngày còn", "#FF9800"
        if days > 0:
            return f"🔴 {days} ngày còn", "#F44336"
        return "❌ Đã hết hạn", "#F44336"

    def is_token_valid(self) -> bool:
        days = self.days_until_expiry()
        return days == -1 or days > 0


# ─── Token Store ──────────────────────────────────────────────────────────────

class TokenStore:
    """
    Encrypted JSON storage for FB OAuth2 tokens.
    Uses Fernet (AES-128-CBC + HMAC-SHA256).
    Key derived from machine UUID → tokens are machine-specific.
    Thread-safe: all mutations hold _lock.
    """

    def __init__(self, path: Optional[str] = None):
        # Giai luc tao doi tuong, khong phai luc import: bien moi truong
        # LTT_DATA_DIR phai duoc ton trong ke ca khi module da nap tu truoc.
        self.path = path or _default_token_file()
        self._accounts: dict[str, AccountInfo] = {}
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()
        if _HAS_CRYPTO:
            from cryptography.fernet import Fernet
            self._fernet = Fernet(_derive_key())
        else:
            self._fernet = None
        self._load()

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self):
        """Populate self._accounts, recording *why* on failure.

        Distinguishes three states that were previously collapsed into a
        silent "0 accounts" (which made an undecryptable token file
        indistinguishable from a fresh install — see docs/_luutru/AUDIT_REPORT.md
        finding D2):

          1. file absent            -> no accounts, no error (normal)
          2. file present, unreadable -> no accounts, self.load_error set
          3. file present, readable   -> accounts loaded
        """
        self._load_error = None
        if not os.path.exists(self.path):
            return

        try:
            raw = Path(self.path).read_bytes()
        except OSError as exc:
            self._load_error = f"Không đọc được {self.path}: {exc}"
            self._accounts = {}
            return

        if not raw.strip():
            return   # empty file == no accounts yet

        payload = raw
        decrypt_failed = False
        if self._fernet:
            try:
                payload = self._fernet.decrypt(raw)
            except Exception:
                # Keep the plain-JSON migration path working for stores
                # written before encryption was introduced.
                decrypt_failed = True
                payload = raw

        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._accounts = {}
            self._load_error = (
                f"Không giải mã được {self.path} bằng khoá của máy này. "
                "File token nhiều khả năng được tạo trên máy khác (hoặc sau "
                "khi cài lại Windows). Cần kết nối lại tài khoản Facebook. "
                "Đặt LTT_TOKEN_ENCRYPTION_KEY để token dùng được trên nhiều máy."
            ) if decrypt_failed else (
                f"{self.path} không phải JSON hợp lệ — file có thể đã hỏng."
            )
            return

        try:
            self._accounts = {
                item["fb_user_id"]: AccountInfo.from_dict(item)
                for item in data
                if item.get("fb_user_id")
            }
        except (AttributeError, TypeError) as exc:
            self._accounts = {}
            self._load_error = f"Cấu trúc dữ liệu token không hợp lệ: {exc}"

    def _save(self):
        """Atomic write: serialise → tmp file → os.replace (crash-safe)."""
        dir_ = os.path.dirname(self.path) or "."
        os.makedirs(dir_, exist_ok=True)
        data = [acc.to_dict() for acc in self._accounts.values()]
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        if self._fernet:
            raw = self._fernet.encrypt(raw)
        tmp = Path(self.path).with_suffix(".tmp")
        tmp.write_bytes(raw)
        tmp.replace(Path(self.path))

    def reload(self):
        """Re-read the file from disk — picks up changes made by another process."""
        with self._lock:
            self._load()

    # ── CRUD ───────────────────────────────────────────────────────────────

    def save_account(self, account: AccountInfo):
        with self._lock:
            self._accounts[account.fb_user_id] = account
            self._save()

    def delete_account(self, fb_user_id: str):
        with self._lock:
            self._accounts.pop(fb_user_id, None)
            self._save()

    def get_account(self, fb_user_id: str) -> Optional[AccountInfo]:
        return self._accounts.get(fb_user_id)

    def all_accounts(self) -> list[AccountInfo]:
        return list(self._accounts.values())

    def is_empty(self) -> bool:
        return len(self._accounts) == 0

    def count(self) -> int:
        return len(self._accounts)

    # ── Page lookup ────────────────────────────────────────────────────────

    def update_page_selection(self, fb_user_id: str, page_id: str, selected: bool):
        with self._lock:
            acc = self._accounts.get(fb_user_id)
            if not acc:
                return
            acc.set_page_selected(page_id, selected)
            self._save()

    def find_page_by_name(
        self, page_name: str
    ) -> tuple[Optional[AccountInfo], Optional[PageInfo]]:
        """Find first account+page where page.name matches and page.selected=True."""
        for acc in self._accounts.values():
            for p in acc.get_selected_pages():
                if p.name == page_name:
                    return acc, p
        return None, None

    def find_page_by_id(
        self, page_id: str
    ) -> tuple[Optional[AccountInfo], Optional[PageInfo]]:
        for acc in self._accounts.values():
            page = acc.get_page_by_id(page_id)
            if page:
                return acc, page
        return None, None

    def all_selected_pages(self) -> list[tuple[AccountInfo, PageInfo]]:
        """Return [(account, page), ...] for all selected pages across all accounts."""
        result = []
        for acc in self._accounts.values():
            for p in acc.get_selected_pages():
                result.append((acc, p))
        return result

    def all_page_names(self) -> list[str]:
        """All selected page names (for dropdowns, etc.).

        DEPRECATED: prefer all_page_options() which preserves account ownership.
        Kept for backwards compat with callers that only need names.
        """
        return [p.name for _, p in self.all_selected_pages()]

    def all_page_options(self) -> list[dict]:
        """Return [{page_id, page_name, account_id, account_name, label}, ...]
        for every selected page across every account.

        `label` is the GUI-friendly string "Page Name  ← Account Name".
        When two accounts share admin access to the same page, both rows
        appear so the user can pick which token to use explicitly.

        This is the SAFE replacement for all_page_names(): callers should
        store page_id (unique) in their data and use the label only for
        display. Use find_page_by_id() to resolve back to (account, page).
        """
        result = []
        for acc in self._accounts.values():
            for p in acc.get_selected_pages():
                result.append({
                    "page_id":      p.id,
                    "page_name":    p.name,
                    "account_id":   acc.fb_user_id,
                    "account_name": acc.name,
                    "label":        f"{p.name}  ← {acc.name}",
                })
        return result

    @property
    def is_encrypted(self) -> bool:
        return self._fernet is not None

    @property
    def load_error(self) -> Optional[str]:
        """Human-readable reason the store could not be read, or None.

        Non-None means "there is a token file we could not use" — which is
        very different from "no accounts connected yet". Callers showing an
        account list should surface this instead of an empty list.
        """
        return self._load_error

    @property
    def is_unreadable(self) -> bool:
        return self._load_error is not None
