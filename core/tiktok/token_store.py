"""
Encrypted token storage for TikTok OAuth2 tokens.

Same Fernet (AES-128-CBC + HMAC-SHA256) pattern as core.token_store,
but with a TikTok-specific salt so keys are distinct from Facebook.

File: data/tiktok_tokens.enc
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# Reuse key derivation (machine-bound, or the ADR-013 external-key override)
# from the FB store; only the salt differs, keeping the two stores' keys
# distinct even when an external key is shared across both.
from core.token_store import _derive_key as _shared_derive_key

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False
    import warnings
    warnings.warn(
        "\n\n"
        "⚠️  SECURITY WARNING: 'cryptography' package is NOT installed.\n"
        "   TikTok OAuth tokens will be stored as PLAIN TEXT.\n"
        "   Run:  pip install cryptography\n"
        "   Then restart the application.\n",
        stacklevel=2,
    )

# None = tu dong giai qua LTT_DATA_DIR luc tao doi tuong. Dat duong dan cu the
# de ep buoc. Cung khuon voi core/token_store.py — xem giai thich day du o do.
_TOKEN_FILE: Optional[str] = None
_SALT = b"tiktok_bot_token_salt_v1_2026"


def _default_token_file() -> str:
    """Nơi lưu token TikTok, giải qua ranh giới đường dẫn của P2.

    Cùng lý do với `core/token_store.py::_default_token_file`: đường dẫn tương
    đối theo thư mục làm việc sẽ rơi vào `app\\data\\` trên máy chủ — thư mục
    bị thay toàn bộ mỗi lần cập nhật.
    """
    if _TOKEN_FILE:
        return _TOKEN_FILE
    try:
        from core.runtime_paths import data_path
        return data_path("tiktok_tokens.enc")
    except Exception:
        return os.path.join("data", "tiktok_tokens.enc")

# P1-01 fix: singleton instance to avoid repeated Fernet decrypt on every
# GUI render. Callers without a custom path should use get_default_store().
_default_store: Optional["TikTokTokenStore"] = None
_default_store_lock = threading.Lock()


def get_default_store() -> "TikTokTokenStore":
    """Return the process-wide shared TikTokTokenStore singleton.

    Thread-safe. Prefer this over `TikTokTokenStore()` in GUI render code
    paths to avoid expensive re-decrypt of tiktok_tokens.enc per call.
    """
    global _default_store
    if _default_store is None:
        with _default_store_lock:
            if _default_store is None:
                _default_store = TikTokTokenStore()
    return _default_store


def _derive_key() -> bytes:
    return _shared_derive_key(salt=_SALT)


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass
class TikTokAccount:
    """
    Represents one connected TikTok user and their OAuth2 tokens.

    TikTok access_token TTL: 24 h (may change; check expires_at).
    TikTok refresh_token TTL: 365 days.
    """

    open_id: str               # TikTok's permanent user identifier
    display_name: str
    avatar_url: str
    access_token: str
    refresh_token: str
    expires_at: float          # Unix timestamp — when access_token expires
    refresh_expires_at: float  # Unix timestamp — when refresh_token expires
    scopes: list = field(default_factory=list)   # granted scope strings
    connected_at: str = ""     # ISO datetime string

    # ── Token state helpers ────────────────────────────────────────────────

    def is_token_valid(self) -> bool:
        """True if access_token has at least 60 s remaining."""
        return time.time() < self.expires_at - 60

    def is_refresh_valid(self) -> bool:
        """True if refresh_token has not expired."""
        return time.time() < self.refresh_expires_at - 60

    def days_until_expiry(self) -> int:
        remaining = self.expires_at - time.time()
        return max(0, int(remaining // 86400))

    def token_status_label(self) -> tuple[str, str]:
        """Returns (label_text, color_hex) for display."""
        if self.is_token_valid():
            d = self.days_until_expiry()
            if d > 1:
                return f"✅ Còn {d} ngày", "#4CAF50"
            hours = max(0, int((self.expires_at - time.time()) // 3600))
            return f"⚠️ Còn {hours}h", "#FF9800"
        return "❌ Đã hết hạn", "#F44336"

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "open_id":            self.open_id,
            "display_name":       self.display_name,
            "avatar_url":         self.avatar_url,
            "access_token":       self.access_token,
            "refresh_token":      self.refresh_token,
            "expires_at":         self.expires_at,
            "refresh_expires_at": self.refresh_expires_at,
            "scopes":             list(self.scopes),
            "connected_at":       self.connected_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TikTokAccount":
        return cls(
            open_id            = str(d.get("open_id", "")),
            display_name       = str(d.get("display_name", "")),
            avatar_url         = str(d.get("avatar_url", "")),
            access_token       = str(d.get("access_token", "")),
            refresh_token      = str(d.get("refresh_token", "")),
            expires_at         = float(d.get("expires_at", 0)),
            refresh_expires_at = float(d.get("refresh_expires_at", 0)),
            scopes             = list(d.get("scopes", [])),
            connected_at       = str(d.get("connected_at", "")),
        )


# ─── Token Store ──────────────────────────────────────────────────────────────

class TikTokTokenStore:
    """
    Encrypted JSON storage for TikTok OAuth2 tokens.
    Thread-safe; uses same Fernet pattern as Facebook TokenStore.
    """

    def __init__(self, path: Optional[str] = None):
        # Giai luc tao doi tuong, khong phai luc import.
        self.path = path or _default_token_file()
        self._accounts: dict[str, TikTokAccount] = {}
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()
        if _HAS_CRYPTO:
            self._fernet = Fernet(_derive_key())
        else:
            self._fernet = None
        self._load()

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self):
        """Populate self._accounts, recording *why* on failure.

        Mirrors core.token_store.TokenStore._load — see its docstring and
        docs/AUDIT_REPORT.md finding D2 for why an unreadable store must
        not look identical to a fresh install.
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
            except Exception as _dec_err:
                # Keep the plain-JSON migration path working for stores
                # written before encryption was introduced.
                decrypt_failed = True
                payload = raw
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "TikTokTokenStore: Fernet decrypt failed (%s) — "
                    "attempting plain-text fallback. "
                    "If this persists, re-connect your TikTok account.",
                    _dec_err,
                )

        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._accounts = {}
            self._load_error = (
                f"Không giải mã được {self.path} bằng khoá của máy này. "
                "File token nhiều khả năng được tạo trên máy khác (hoặc sau "
                "khi cài lại Windows). Cần kết nối lại tài khoản TikTok. "
                "Đặt LTT_TOKEN_ENCRYPTION_KEY để token dùng được trên nhiều máy."
            ) if decrypt_failed else (
                f"{self.path} không phải JSON hợp lệ — file có thể đã hỏng."
            )
            return

        try:
            self._accounts = {
                item["open_id"]: TikTokAccount.from_dict(item)
                for item in data
                if item.get("open_id")
            }
        except (AttributeError, TypeError) as exc:
            self._accounts = {}
            self._load_error = f"Cấu trúc dữ liệu token không hợp lệ: {exc}"

    def _save(self):
        """Atomic write: serialise → tmp → os.replace."""
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
        with self._lock:
            self._load()

    # ── CRUD ───────────────────────────────────────────────────────────────

    def upsert_account(self, account: TikTokAccount) -> None:
        with self._lock:
            self._accounts[account.open_id] = account
            self._save()

    def remove_account(self, open_id: str) -> None:
        with self._lock:
            self._accounts.pop(open_id, None)
            self._save()

    def get_account(self, open_id: str) -> Optional[TikTokAccount]:
        # BUG-02 fix: read under lock to avoid race with upsert_account/remove_account
        with self._lock:
            return self._accounts.get(open_id)

    def all_accounts(self) -> list[TikTokAccount]:
        # BUG-02 fix: snapshot under lock to avoid RuntimeError during iteration
        with self._lock:
            return list(self._accounts.values())

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._accounts) == 0

    def count(self) -> int:
        with self._lock:
            return len(self._accounts)

    @property
    def is_encrypted(self) -> bool:
        return self._fernet is not None

    @property
    def load_error(self) -> Optional[str]:
        """Human-readable reason the store could not be read, or None.
        See core.token_store.TokenStore.load_error."""
        return self._load_error

    @property
    def is_unreadable(self) -> bool:
        return self._load_error is not None
