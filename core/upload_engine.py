"""
Upload engine — API-only (Graph API).

Không còn Selenium fallback. Nếu page không có token → raise rõ ràng.

Call modes:
  run(task)      — async callback-based (OperationTab)
  run_sync(task) — blocking, trả về video_link (SheetRunner)
"""

import threading
import traceback

from core.graph_client import GraphError
from core.token_store import TokenStore, get_default_store
from utils.logger import BotLogger


class TokenNotFoundError(RuntimeError):
    """Page không có API token trong TokenStore."""


class TokenExpiredError(RuntimeError):
    """Token đã hết hạn."""


class UploadEngine:
    def __init__(
        self,
        config: dict,
        stop_event: threading.Event,
        on_log=None,
        on_status=None,
        on_result=None,
        on_done=None,
        on_error=None,
        rate_limiter=None,
    ):
        self.config        = config
        self.stop_event    = stop_event
        self.on_log        = on_log    or (lambda msg, lvl: None)
        self.on_status     = on_status or (lambda msg: None)
        self.on_result     = on_result or (lambda task, status, link: None)
        self.on_done       = on_done   or (lambda: None)
        self.on_error      = on_error  or (lambda msg: None)
        self._rate_limiter = rate_limiter

        self.logger = BotLogger(callback=self.on_log)

    # ─── Async mode ──────────────────────────────────────────────────────────

    def run(self, task: dict):
        try:
            self._run_inner(task)
        except InterruptedError:
            self.logger.warning("Đã dừng theo yêu cầu người dùng")
            self.on_result(task, "stopped", "")
        except (TokenNotFoundError, TokenExpiredError) as e:
            msg = str(e)
            self.logger.error(f"[Token] {msg}")
            self.on_error(msg)
            self.on_result(task, "error", msg)
        except GraphError as e:
            msg = _format_graph_error(e)
            self.logger.error(f"[GraphAPI] {msg}")
            self.logger.debug(traceback.format_exc())
            self.on_error(msg)
            self.on_result(task, "error", msg)
        except FileNotFoundError as e:
            msg = f"File không tồn tại: {e}"
            self.logger.error(msg)
            self.on_error(msg)
            self.on_result(task, "error", msg)
        except Exception as e:
            self.logger.error(f"Lỗi: {e}")
            self.logger.debug(traceback.format_exc())
            self.on_error(str(e))
            self.on_result(task, "error", str(e))
        finally:
            self.on_status("Sẵn sàng")
            self.on_done()

    # ─── Sync mode ───────────────────────────────────────────────────────────

    def run_sync(self, task: dict) -> tuple[str, str]:
        """Blocking. Trả về (video_url, video_id). Raise nếu thất bại."""
        return self._run_inner(task)

    # ─── Inner logic ─────────────────────────────────────────────────────────

    def _run_inner(self, task: dict) -> tuple[str, str]:
        page_name = task.get("page", "")
        page_id   = task.get("page_id", "")

        try:
            # Prefer page_id (unique) over page_name (may collide across
            # accounts that both admin the same Page). Falls back to name
            # for legacy callers/workers that haven't been migrated.
            store = get_default_store()
            if page_id:
                account, page = store.find_page_by_id(page_id)
            else:
                account, page = store.find_page_by_name(page_name)
        except Exception as e:
            raise TokenNotFoundError(
                f"Lỗi đọc TokenStore khi tìm page '{page_name}': {e}"
            ) from e

        if account is None or page is None:
            raise TokenNotFoundError(
                f"Không tìm thấy API token cho page '{page_name}'.\n"
                "Vào tab 🔐 Tài khoản → Kết nối Facebook → tick chọn page này."
            )

        if not account.is_token_valid():
            raise TokenExpiredError(
                f"Token cho page '{page_name}' đã hết hạn.\n"
                "Vào tab 🔐 Tài khoản → Làm mới token."
            )

        return self._run_api(task, account, page)

    # ─── API path ────────────────────────────────────────────────────────────

    def _run_api(self, task: dict, account, page) -> tuple[str, str]:
        account_id = str(getattr(account, "fb_user_id", "") or "")
        if self._rate_limiter:
            wait = self._rate_limiter.wait_until_ready(page.name)
            if wait > 0:
                self.logger.upload(f"[RateLimit] Chờ {wait:.0f}s → {page.name}")
                self.on_status(f"[RateLimit] Chờ {wait:.0f}s → {page.name}...")
            self._rate_limiter.acquire(
                page.name, self.stop_event, account_id=account_id,
            )

        try:
            post_type = str(task.get("post_type", "feed")).lower().strip()

            if post_type == "reels":
                from core.reels_uploader import ReelsUploader
                self.logger.upload(f"[Engine] Reels API → Page: {page.name}")
                self.on_status(f"[Reels] Đang kết nối → {page.name}...")
                uploader = ReelsUploader(
                    account    = account,
                    page       = page,
                    config     = self.config,
                    stop_event = self.stop_event,
                    logger     = self.logger,
                    on_status  = self.on_status,
                    on_progress= lambda done, total: None,
                )
            else:
                from core.graph_uploader import GraphUploader
                self.logger.upload(f"[Engine] Graph API → Page: {page.name}")
                self.on_status(f"[API] Đang kết nối → {page.name}...")
                uploader = GraphUploader(
                    account    = account,
                    page       = page,
                    config     = self.config,
                    stop_event = self.stop_event,
                    logger     = self.logger,
                    on_status  = self.on_status,
                    on_progress= lambda done, total: None,
                )

            video_url, video_id = uploader.upload(task)

            # Post comment (feed only — Reels comments are not supported via API).
            # Gated behind fb_comment_enabled (default OFF): commenting needs the
            # pages_manage_engagement permission, which is intentionally NOT part
            # of the App Review submission. Keep the feature dormant until that
            # permission is approved, then flip the flag.
            comment = task.get("comment", "")
            if (
                comment
                and post_type != "reels"
                and self.config.get("fb_comment_enabled", False)
            ):
                uploader.post_comment(video_id, comment)

            self.on_result(task, "success", video_url)
            return video_url, video_id

        finally:
            if self._rate_limiter:
                self._rate_limiter.release(page.name, account_id=account_id)


# ─── Error formatting ──────────────────────────────────────────────────────────

def _format_graph_error(e: GraphError) -> str:
    if e.is_token_error():
        return (
            f"Token hết hạn hoặc không hợp lệ: {e}\n"
            "→ Vào tab 🔐 Tài khoản FB → Kết nối lại hoặc Làm mới token."
        )
    if e.is_permission_error():
        return (
            f"Thiếu quyền API: {e}\n"
            "→ Kiểm tra App Review và quyền pages_manage_posts."
        )
    if e.is_page_restricted():
        return f"Page bị hạn chế đăng bài: {e}"
    if e.is_rate_limit():
        return f"Facebook rate limit — thử lại sau vài phút: {e}"
    return f"Graph API lỗi: {e}"
