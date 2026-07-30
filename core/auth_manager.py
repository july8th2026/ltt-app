"""
core/auth_manager.py — Facebook OAuth2 + token lifecycle.

The OAuth flow is split so the web app can drive it across two HTTP requests:

    build_authorize_url(redirect_uri, state)  -> where to send the operator
    complete_oauth(code, redirect_uri)        -> code to a saved AccountInfo

The provider redirects back to the app itself
(`/oauth/facebook/callback`, see server/routes/oauth.py). There is no local
callback server: the earlier desktop build opened a browser on the bot's own
machine and bound localhost:8765, neither of which is possible on a server.
`state` and single-use/TTL enforcement live in server/services/oauth_service.py.

`import_system_user_token` is the other way in, and needs no browser at all.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Callable, Optional
from urllib.parse import urlencode

from core.graph_client import GraphClient, GraphError
from core.token_store import AccountInfo, PageInfo, TokenStore

# Facebook OAuth scopes
_SCOPES = ",".join([
    "pages_show_list",
    "pages_manage_posts",
    "pages_read_engagement",
])

class AuthManager:
    """
    Manages Facebook OAuth2 flow and token lifecycle.
    Cheap to construct; the web app makes one per request.
    """

    def __init__(self, config: dict, token_store: Optional[TokenStore] = None):
        # Round 1.5: pool-aware OAuth. When meta_app_pool is configured,
        # pick the next healthy app; otherwise fall back to legacy single-app
        # config keys (meta_app_id / meta_app_secret).
        self._config = dict(config)
        try:
            from core.multi_app import MetaAppPool
            self._app_pool = MetaAppPool.from_config(config)
            chosen = self._app_pool.next_healthy()
        except Exception:
            self._app_pool = None
            chosen = None

        if chosen is not None:
            self.app_id       = chosen.app_id
            self.app_secret   = chosen.app_secret
            self.redirect_uri = chosen.redirect_uri or str(config.get("meta_redirect_uri", "")).strip()
        else:
            self.app_id     = str(config.get("meta_app_id", "")).strip()
            self.app_secret = str(config.get("meta_app_secret", "")).strip()
            # Must be the app's own HTTPS callback, registered at Meta.
            # server/services/oauth_service.py validates it before use.
            self.redirect_uri = str(config.get("meta_redirect_uri", "")).strip()

        self.api_version = str(config.get("graph_api_version", "v21.0")).strip() or "v21.0"
        self.token_store = token_store or TokenStore()
        self._client     = GraphClient(version=self.api_version)

    # ── Configuration ──────────────────────────────────────────────────────

    def update_config(self, config: dict):
        """Hot-update credentials without recreating the object."""
        self.app_id     = str(config.get("meta_app_id", "")).strip()
        self.app_secret = str(config.get("meta_app_secret", "")).strip()
        self.api_version = str(config.get("graph_api_version", "v21.0")).strip() or "v21.0"
        self.redirect_uri = str(config.get("meta_redirect_uri", "")).strip()
        self._client    = GraphClient(version=self.api_version)

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    # ── OAuth flow ─────────────────────────────────────────────────────────
    #
    # Two halves with the browser round-trip in between. Neither opens a
    # browser nor binds a port, so the web app drives them from two separate
    # HTTP requests.

    def build_authorize_url(self, redirect_uri: str, state: str) -> str:
        """The Facebook login dialog URL.

        Every value is percent-encoded. An earlier build interpolated raw,
        which worked only because the scope list and a localhost URI contain
        no characters needing escapes; an HTTPS redirect_uri carrying a query
        string would have silently truncated the URL.
        """
        if not self.is_configured():
            raise ValueError(
                "Chưa cấu hình Meta App ID / Secret.\n"
                "Vào trang Cài đặt → mục 'Meta App (Facebook Login)' để nhập."
            )
        query = urlencode({
            "client_id":     self.app_id,
            "redirect_uri":  redirect_uri,
            "scope":         _SCOPES,
            "response_type": "code",
            "state":         state,
        })
        return f"https://www.facebook.com/{self.api_version}/dialog/oauth?{query}"

    def complete_oauth(
        self,
        code: str,
        redirect_uri: str,
        on_status: Callable[[str], None] = None,
    ) -> AccountInfo:
        """Code -> long-lived token -> user -> pages -> saved AccountInfo.

        `redirect_uri` must be byte-identical to the one used to obtain the
        code; Facebook rejects the exchange otherwise.
        """
        log = on_status or (lambda m: None)

        # ── Exchange code → short-lived token ──────────────────────────────
        log("Đang lấy Access Token...")
        resp = self._client.get("oauth/access_token", params={
            "client_id":     self.app_id,
            "redirect_uri":  redirect_uri,
            "client_secret": self.app_secret,
            "code":          code,
        })
        short_token = resp.get("access_token", "")
        if not short_token:
            raise RuntimeError("Không lấy được access_token từ Facebook")

        # ── Exchange short → long-lived (60 days) ──────────────────────────
        log("Đang đổi sang Long-Lived Token (60 ngày)...")
        long_token, expires_in = self._client.exchange_short_for_long(
            self.app_id, self.app_secret, short_token
        )
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()

        # ── Fetch user info ────────────────────────────────────────────────
        log("Đang lấy thông tin tài khoản...")
        user_info  = self._client.get_user_info(long_token)
        fb_user_id = str(user_info.get("id", ""))
        name       = str(user_info.get("name", "Tài khoản FB"))
        if not fb_user_id:
            raise RuntimeError("Không lấy được User ID từ Facebook")

        # ── Fetch pages ────────────────────────────────────────────────────
        log("Đang lấy danh sách Pages...")
        pages_raw = self._client.get_pages(long_token)
        pages: list[PageInfo] = []
        for p in pages_raw:
            pic_url = ""
            pic = p.get("picture", {})
            if isinstance(pic, dict):
                pic_url = pic.get("data", {}).get("url", "")
            pages.append(PageInfo(
                id            = str(p.get("id", "")),
                name          = str(p.get("name", "")),
                access_token  = str(p.get("access_token", "")),
                category      = str(p.get("category", "")),
                picture_url   = pic_url,
                selected      = True,
            ))

        # ── Build & save AccountInfo ───────────────────────────────────────
        account = AccountInfo(
            fb_user_id       = fb_user_id,
            name             = name,
            user_token       = long_token,
            token_expires_at = expires_at,
            pages            = [pg.to_dict() for pg in pages],
            connected_at     = datetime.now().isoformat(),
        )
        self.token_store.save_account(account)

        log(f"✅ Kết nối thành công: {name} — {len(pages)} page")
        return account

    # ── System User token (Business Manager) ───────────────────────────────

    @staticmethod
    def _sanitize_token(raw: str) -> str:
        """Clean a pasted token: strip quotes, common prefixes, wrapped newlines.

        Users frequently paste `"EAAB..."`, `access_token=EAAB...`, or a token
        that copy-wrapped across lines. FB tokens contain no whitespace, so we
        can safely collapse all internal whitespace after removing prefixes.
        """
        t = (raw or "").strip()
        if len(t) >= 2 and t[0] in "\"'" and t[-1] == t[0]:
            t = t[1:-1].strip()
        for prefix in ("access_token=", "Bearer ", "OAuth ", "token="):
            if t.lower().startswith(prefix.lower()):
                t = t[len(prefix):].strip()
                break
        return "".join(t.split())

    def import_system_user_token(
        self,
        token: str,
        on_status: Callable[[str], None] = None,
    ) -> AccountInfo:
        """
        Import a Business Manager **System User** access token (dán thủ công).

        Khác OAuth: không cần trình duyệt. Token thường là long-lived hoặc
        không hết hạn (never-expiring). Luồng:
          1. GET /me                → id + tên System User
          2. GET /debug_token       → dò hạn thật (expires_at == 0 ⇒ vĩnh viễn)
          3. GET /me/accounts       → danh sách Page + Page Access Token riêng
          4. Lưu AccountInfo(is_system_user=True) vào TokenStore (mã hoá)

        Raise nếu token sai / không có Page nào được gán.
        """
        log = on_status or (lambda m: None)
        token = self._sanitize_token(token)
        if not token:
            raise ValueError("Token rỗng — hãy dán System User token.")

        # 1. Chủ sở hữu token
        log("Đang kiểm tra token...")
        try:
            user_info = self._client.get_user_info(token)
        except GraphError as exc:
            raise RuntimeError(
                f"Token không hợp lệ hoặc đã bị thu hồi: {exc}"
            ) from exc
        uid  = str(user_info.get("id", ""))
        name = str(user_info.get("name", "") or "System User")
        if not uid:
            raise RuntimeError(
                "Token không hợp lệ — không lấy được ID (kiểm tra lại chuỗi token)."
            )

        # 2. Dò hạn thật qua debug_token (cần app access token = app_id|app_secret)
        expires_at = ""   # "" = vĩnh viễn (never expires)
        try:
            if self.app_id and self.app_secret:
                app_token = f"{self.app_id}|{self.app_secret}"
                dbg = self._client.get(
                    "debug_token",
                    params={"input_token": token},
                    token=app_token,
                )
                data = dbg.get("data", {}) or {}
                exp = int(data.get("expires_at", 0) or 0)
                if exp > 0:
                    expires_at = datetime.fromtimestamp(exp).isoformat()
                # exp == 0 → không hết hạn → giữ ""
        except Exception:
            # Không nghiêm trọng: coi như vĩnh viễn. Refresher vốn bỏ qua
            # System User nên sẽ không cố refresh nhầm.
            pass

        # 3. Lấy Pages (mỗi Page có Page Access Token long-lived riêng)
        log("Đang lấy danh sách Pages...")
        pages_raw = self._client.get_pages(token)
        if not pages_raw:
            raise RuntimeError(
                "Token hợp lệ nhưng không thấy Page nào.\n"
                "Kiểm tra: System User đã được gán Page trong "
                "Business Settings → Người dùng hệ thống → Chỉ định tài sản chưa?"
            )

        # W1 fix — preserve the user's page-selection when re-importing (the
        # "add pages later" flow): pages previously unticked stay unticked.
        prior = self.token_store.get_account(uid)
        prior_selected = (
            {p.id: p.selected for p in prior.get_pages_list()} if prior else {}
        )

        pages: list[PageInfo] = []
        skipped: list[str] = []          # W2 — pages without a usable token
        for p in pages_raw:
            pid   = str(p.get("id", ""))
            pname = str(p.get("name", "") or pid)
            ptok  = str(p.get("access_token", "") or "")
            # W2 fix — a page with no Page Access Token can't be posted to: the
            # System User was assigned the page but NOT full control / content
            # permission. Storing it would only surface a cryptic error later.
            if not ptok:
                skipped.append(pname)
                continue
            pic_url = ""
            pic = p.get("picture", {})
            if isinstance(pic, dict):
                pic_url = pic.get("data", {}).get("url", "")
            pages.append(PageInfo(
                id           = pid,
                name         = pname,
                access_token = ptok,
                category     = str(p.get("category", "")),
                picture_url  = pic_url,
                selected     = prior_selected.get(pid, True),
            ))

        if not pages:
            raise RuntimeError(
                "Token hợp lệ nhưng KHÔNG page nào có quyền đăng.\n"
                "Vào Business Settings → Người dùng hệ thống → Chỉ định tài sản, "
                "gán Page cho System User với quyền 'Toàn quyền' (Quản lý Trang)."
            )
        if skipped:
            log(
                f"⚠ Bỏ qua {len(skipped)} page thiếu quyền đăng "
                f"(chưa cấp Toàn quyền): {', '.join(skipped[:5])}"
                + (" ..." if len(skipped) > 5 else "")
            )

        account = AccountInfo(
            fb_user_id       = uid,
            name             = f"{name} (BM)",
            user_token       = token,
            token_expires_at = expires_at,
            pages            = [pg.to_dict() for pg in pages],
            connected_at     = datetime.now().isoformat(),
            is_system_user   = True,
        )
        self.token_store.save_account(account)

        msg = f"✅ Đã nhập token: {name} — {len(pages)} page sẵn sàng đăng"
        if skipped:
            msg += f" ({len(skipped)} page bị bỏ qua)"
        log(msg)
        return account

    # ── Token test & refresh ───────────────────────────────────────────────

    def test_token(self, account: AccountInfo) -> tuple[bool, str]:
        """Test if the account's user token is still valid."""
        try:
            info = self._client.get_user_info(account.user_token)
            return True, f"OK — {info.get('name', '?')}"
        except GraphError as exc:
            if exc.is_token_error():
                return False, f"Token hết hạn — cần làm mới ({exc})"
            return False, f"Lỗi API: {exc}"
        except Exception as exc:
            return False, f"Lỗi kết nối: {exc}"

    def revoke_account(self, fb_user_id: str):
        """Remove account from local TokenStore."""
        self.token_store.delete_account(fb_user_id)

    # ── Public helpers ─────────────────────────────────────────────────────

    @property
    def token_store_ref(self) -> TokenStore:
        return self.token_store


# ─── Module helpers ───────────────────────────────────────────────────────────
