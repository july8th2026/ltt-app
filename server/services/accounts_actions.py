"""
accounts_actions.py — the account operations from the desktop tabs that work
on a remote server without a browser OAuth round-trip.

Ported from `gui/account_tab.py` / `gui/tiktok_account_tab.py`. What is here
and what is deliberately not:

  works on the web today
    - import a Business-Manager System User token (no browser needed: it is
      a paste + Graph API validation, `AuthManager.import_system_user_token`)
    - test a token          (`AuthManager.test_token`)
    - toggle page selection (`TokenStore.update_page_selection`)
    - disconnect            (`TokenStore.delete_account`, and for TikTok the
                             server-side revoke via `revoke_account`)

  still needs the P-next OAuth work
    - "Kết nối tài khoản Facebook" / "Continue with TikTok": both open a
      browser and bind a localhost callback, which cannot work on a remote
      server. Those buttons stay disabled with an explanation rather than
      silently failing.

Every function returns (ok, message) so routes can render the desktop's own
wording instead of inventing new copy.
"""
from __future__ import annotations


def _fb_store():
    from core.token_store import get_default_store
    return get_default_store()


def _tt_store():
    from core.tiktok.token_store import get_default_store
    return get_default_store()


# ── Facebook ──────────────────────────────────────────────────────────────────

def import_system_user_token(config: dict, token: str) -> tuple[bool, str]:
    """Paste-import a BM System User token. Desktop equivalent:
    '🔑  Dán token System User (BM)'.

    This is the one way to connect a Facebook account with no browser, so it
    is the web's path until OAuth is ported.
    """
    if not (token or "").strip():
        return False, "Token rỗng — hãy dán System User token."

    from core.auth_manager import AuthManager
    logs: list = []
    try:
        account = AuthManager(config, _fb_store()).import_system_user_token(
            token, on_status=logs.append,
        )
    except Exception as exc:
        return False, str(exc)

    pages = len(account.get_selected_pages())
    detail = ("  " + "  ".join(logs[-2:])) if logs else ""
    return True, f"✅ Đã nhập token: {account.name} — {pages} page sẵn sàng đăng{detail}"


def test_facebook_token(config: dict, fb_user_id: str) -> tuple[bool, str]:
    """Desktop equivalent: '🧪  Test kết nối'."""
    store = _fb_store()
    account = store.get_account(fb_user_id)
    if account is None:
        return False, "Không tìm thấy tài khoản."
    from core.auth_manager import AuthManager
    try:
        ok, msg = AuthManager(config, store).test_token(account)
        return ok, f"{'✅' if ok else '❌'} {msg}"
    except Exception as exc:
        return False, f"❌ Lỗi kết nối: {exc}"


def set_page_selected(fb_user_id: str, page_id: str, selected: bool) -> tuple[bool, str]:
    """Desktop equivalent: the 'Chọn' checkbox in the PAGES card."""
    store = _fb_store()
    account = store.get_account(fb_user_id)
    if account is None:
        return False, "Không tìm thấy tài khoản."
    try:
        store.update_page_selection(fb_user_id, page_id, selected)
    except Exception as exc:
        return False, f"Không lưu được lựa chọn page: {exc}"
    n = len(store.get_account(fb_user_id).get_selected_pages())
    total = len(store.get_account(fb_user_id).get_pages_list())
    return True, f"✅ {n}/{total} page được chọn"


def disconnect_facebook(fb_user_id: str) -> tuple[bool, str]:
    """Desktop equivalent: '🗑  Ngắt kết nối'.

    Facebook has no server-side revoke in the desktop flow either — this
    only deletes the stored token.
    """
    store = _fb_store()
    account = store.get_account(fb_user_id)
    if account is None:
        return False, "Không tìm thấy tài khoản."
    name = account.name
    try:
        store.delete_account(fb_user_id)
    except Exception as exc:
        return False, f"Không xoá được token: {exc}"
    return True, f"Đã ngắt kết nối: {name}"


# ── TikTok ────────────────────────────────────────────────────────────────────

def refresh_tiktok_token(config: dict, open_id: str) -> tuple[bool, str]:
    """Desktop equivalent: '🔄  Làm mới token'. Works headless — it is a
    refresh_token grant, no browser involved."""
    store = _tt_store()
    account = store.get_account(open_id)
    if account is None:
        return False, "Không tìm thấy tài khoản TikTok."
    if not account.is_refresh_valid():
        return False, (f"Refresh token của '{account.display_name}' đã hết hạn.\n"
                       "Bạn cần ngắt kết nối và đăng nhập lại từ đầu.")
    from core.tiktok.auth_manager import TikTokAuthManager
    try:
        updated = TikTokAuthManager(config, token_store=store).refresh_access_token(account)
        store.upsert_account(updated)
    except Exception as exc:
        return False, f"Làm mới thất bại: {exc}"
    return True, f"✅ Token {updated.display_name} đã được làm mới."


def disconnect_tiktok(config: dict, open_id: str) -> tuple[bool, str]:
    """Desktop equivalent: '🗑  Ngắt kết nối' — calls TikTok's revoke
    endpoint first, then removes the local token. If the revoke fails the
    local token is still removed, and the caller is told to revoke manually
    (same behaviour and same warning as the desktop)."""
    store = _tt_store()
    account = store.get_account(open_id)
    if account is None:
        return False, "Không tìm thấy tài khoản TikTok."
    name = account.display_name

    from core.tiktok.auth_manager import TikTokAuthManager
    try:
        TikTokAuthManager(config, token_store=store).revoke_account(open_id)
        return True, f"✅ Đã ngắt kết nối và thu hồi token: {name}"
    except Exception as revoke_err:
        try:
            store.delete_account(open_id)
        except Exception as exc:
            return False, (f"Không thể xóa token cục bộ: {exc}\n"
                           "Kiểm tra quyền ghi file trong thư mục data/")
        return True, (
            "⚠ Đã xoá token khỏi máy chủ, NHƯNG thu hồi phía TikTok thất bại: "
            f"{revoke_err}\n"
            "Để chắc chắn, vào app TikTok → Settings → Privacy → "
            "Manage account access → Remove LTTStudio thủ công."
        )
