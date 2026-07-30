"""
test_16_facebook_commenter.py — Tests for Facebook publish-pipeline Stage 7
(post-publish comment) + integration with FacebookPublisher.

Mirrors test_15_tiktok_commenter.py structure for parity.

Coverage:

STAGE 7 — FacebookCommenter unit tests
  FC01: post_comment(empty)         → SKIPPED, no API call
  FC02: post_comment(whitespace)    → SKIPPED
  FC03: post_comment(too long)      → FAILED + comment_too_long
  FC04: post_comment(missing v_id)  → FAILED + missing_video_id
  FC05: post_comment(success)       → calls /{video_id}/comments
  FC06: post_comment(success)       → CommentResult.success=True with comment_id
  FC07: GraphError code=190         → FAILED, never raises (token invalid)
  FC08: GraphError code=200         → FAILED (permission denied)
  FC09: GraphError code=32          → FAILED (rate limit)
  FC10: stop_event set              → user_cancelled
  FC11: unexpected exception        → unexpected_error, never raises
  FC12: None client                 → FacebookCommentError
  FC13: empty page_access_token     → FacebookCommentError
  FC14: response without id         → still success (comment_id="")
  FC15: GraphError code=368         → spam_detected handling
  FC16: passes page access_token in API call

INTEGRATION — FacebookPublisher Stage 7
  FC20: publisher with comment in feed task → calls commenter via TokenStore
  FC21: publisher with comment + reels post_type → SKIPS commenter
  FC22: publisher with empty comment → does NOT call commenter
  FC23: publisher writes facebook_comment_posted on success
  FC24: publisher writes facebook_comment_skipped for empty
  FC25: publisher writes facebook_comment_failed on API error
  FC26: commenter failure does NOT break successful publish
  FC27: commenter exception is swallowed (publish still succeeds)
  FC28: publisher passes empty comment to engine to bypass inline comment
"""
from __future__ import annotations

import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ────────────────────────────────────────────────────────────────────────────
# STAGE 7 — FacebookCommenter unit tests
# ────────────────────────────────────────────────────────────────────────────

class TestFBCommenterValidation(unittest.TestCase):
    """FC01-FC04, FC12-FC14: input validation + boundaries."""

    def _make_client(self, post_result=None):
        from core.graph_client import GraphClient
        client = MagicMock(spec=GraphClient)
        if post_result is not None:
            client.post.return_value = post_result
        return client

    def test_FC01_empty_returns_skipped(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_client()
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("vid_123", "")
        self.assertTrue(result.success)
        self.assertTrue(result.skipped)
        client.post.assert_not_called()

    def test_FC02_whitespace_returns_skipped(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_client()
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("vid_123", "  \n\t  ")
        self.assertTrue(result.skipped)
        client.post.assert_not_called()

    def test_FC03_too_long_returns_failed(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_client()
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        long_text = "x" * 9000     # > 8000
        result = commenter.post_comment("vid_123", long_text)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "comment_too_long")
        client.post.assert_not_called()

    def test_FC04_missing_video_id_returns_failed(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_client()
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("", "Nice video!")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "missing_video_id")
        client.post.assert_not_called()

    def test_FC12_none_client_raises(self):
        from core.facebook.commenter import FacebookCommenter, FacebookCommentError
        with self.assertRaises(FacebookCommentError):
            FacebookCommenter(None, "PAGE_TOKEN")

    def test_FC13_empty_token_raises(self):
        from core.facebook.commenter import FacebookCommenter, FacebookCommentError
        from core.graph_client import GraphClient
        client = MagicMock(spec=GraphClient)
        with self.assertRaises(FacebookCommentError):
            FacebookCommenter(client, "")

    def test_FC14_response_without_id_still_success(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_client(post_result={})    # no id returned
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("vid_123", "Hello")
        self.assertTrue(result.success)
        self.assertEqual(result.comment_id, "")


class TestFBCommenterAPICall(unittest.TestCase):
    """FC05-FC06, FC16: API call shape and response parsing."""

    def test_FC05_calls_correct_endpoint_with_message_body(self):
        from core.graph_client import GraphClient
        from core.facebook.commenter import FacebookCommenter

        client = MagicMock(spec=GraphClient)
        client.post.return_value = {"id": "PAGE_111_2222"}

        commenter = FacebookCommenter(client, "PAGE_TOKEN")
        commenter.post_comment("vid_999", "Awesome!")

        client.post.assert_called_once()
        args, kwargs = client.post.call_args

        # First positional arg should be "<video_id>/comments"
        endpoint = args[0] if args else kwargs.get("path")
        self.assertEqual(endpoint, "vid_999/comments")

        # Data dict should contain message
        data = kwargs.get("data")
        self.assertEqual(data, {"message": "Awesome!"})

    def test_FC06_success_returns_comment_id(self):
        from core.graph_client import GraphClient
        from core.facebook.commenter import FacebookCommenter

        client = MagicMock(spec=GraphClient)
        client.post.return_value = {"id": "PAGE_111_2222"}

        commenter = FacebookCommenter(client, "PAGE_TOKEN")
        result = commenter.post_comment("vid_999", "Awesome!")

        self.assertTrue(result.success)
        self.assertFalse(result.skipped)
        self.assertEqual(result.comment_id, "PAGE_111_2222")

    def test_FC16_passes_token_as_kwarg(self):
        from core.graph_client import GraphClient
        from core.facebook.commenter import FacebookCommenter

        client = MagicMock(spec=GraphClient)
        client.post.return_value = {"id": "x"}

        commenter = FacebookCommenter(client, "MY_PAGE_TOKEN_XYZ")
        commenter.post_comment("vid_1", "Hi")

        kwargs = client.post.call_args.kwargs
        self.assertEqual(kwargs.get("token"), "MY_PAGE_TOKEN_XYZ")


class TestFBCommenterErrorHandling(unittest.TestCase):
    """FC07-FC11, FC15: Graph error mapping + cancellation never raise."""

    def _make_raising_client(self, code: int, msg: str = "test"):
        from core.graph_client import GraphClient, GraphError
        client = MagicMock(spec=GraphClient)
        err = GraphError(msg, code=code)
        client.post.side_effect = err
        return client

    def test_FC07_token_invalid_returns_failed(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_raising_client(190, "OAuth expired")
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("vid_1", "Hi")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "190")

    def test_FC08_permission_denied_returns_failed(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_raising_client(200, "Permission required")
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("vid_1", "Hi")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "200")

    def test_FC09_rate_limit_returns_failed(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_raising_client(32, "Rate limit")
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("vid_1", "Hi")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "32")

    def test_FC10_stop_event_returns_user_cancelled(self):
        from core.graph_client import GraphClient
        from core.facebook.commenter import FacebookCommenter

        client = MagicMock(spec=GraphClient)
        stop = threading.Event()
        stop.set()

        commenter = FacebookCommenter(client, "PAGE_TOKEN", stop_event=stop)
        result = commenter.post_comment("vid_1", "Hi")

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "user_cancelled")
        client.post.assert_not_called()

    def test_FC11_unexpected_exception_no_raise(self):
        from core.graph_client import GraphClient
        from core.facebook.commenter import FacebookCommenter

        client = MagicMock(spec=GraphClient)
        client.post.side_effect = ConnectionError("Network down")

        commenter = FacebookCommenter(client, "PAGE_TOKEN")
        # Must NOT raise
        result = commenter.post_comment("vid_1", "Hi")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "unexpected_error")

    def test_FC15_spam_368_returns_failed(self):
        from core.facebook.commenter import FacebookCommenter
        client = self._make_raising_client(368, "Spam detected")
        commenter = FacebookCommenter(client, "PAGE_TOKEN")

        result = commenter.post_comment("vid_1", "Buy now! www.example.com")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "368")


# ────────────────────────────────────────────────────────────────────────────
# INTEGRATION — FacebookPublisher Stage 7 wiring
# ────────────────────────────────────────────────────────────────────────────

class TestFBPublisherStage7(unittest.TestCase):
    """FC20-FC28: FacebookPublisher correctly invokes FacebookCommenter."""

    def _make_publisher(self, comment_enabled=True):
        # comment_enabled defaults True here so the Stage-7 comment path is
        # exercised. Production config defaults fb_comment_enabled=False (the
        # pages_manage_engagement permission is not in the App Review scope).
        from core.facebook.publisher_service import FacebookPublisher
        return FacebookPublisher(
            config     = {"graph_api_version": "v21.0",
                          "fb_comment_enabled": comment_enabled},
            stop_event = threading.Event(),
            on_log     = lambda m, l: None,
            on_status  = lambda m: None,
        )

    def test_FC29_comment_disabled_skips_commenter(self):
        """fb_comment_enabled=False → feed+comment must NOT invoke commenter."""
        publisher = self._make_publisher(comment_enabled=False)
        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter:
            task = {
                "page":       "MyPage",
                "video_path": "v.mp4",
                "post_type":  "feed",
                "comment":    "Great!",
            }
            result = publisher.publish(task)
            MockCommenter.assert_not_called()
            self.assertTrue(result.success)          # publish still succeeds

    def _patch_engine(self, video_url="https://fb.com/x/videos/V99", video_id="V99"):
        return patch(
            "core.facebook.publisher_service.UploadEngine.run_sync",
            return_value=(video_url, video_id),
        )

    def _patch_token_store(self):
        """Patch get_default_store to return a fake account+page."""
        store = MagicMock()
        account = MagicMock()
        account.is_token_valid.return_value = True
        page = MagicMock()
        page.access_token = "PAGE_TOKEN_XYZ"
        page.name = "MyPage"
        page.id = "111"
        store.find_page_by_name.return_value = (account, page)
        return patch(
            "core.token_store.get_default_store",
            return_value=store,
        )

    def test_FC20_feed_with_comment_invokes_commenter(self):
        publisher = self._make_publisher()

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter:
            from core.facebook.commenter import CommentResult
            instance = MockCommenter.return_value
            instance.post_comment.return_value = CommentResult(
                success=True, comment_id="cm_42", text="Great!",
            )

            task = {
                "page":       "MyPage",
                "video_path": "v.mp4",
                "post_type":  "feed",
                "comment":    "Great!",
            }
            publisher.publish(task)
            instance.post_comment.assert_called_once_with("V99", "Great!")

    def test_FC21_reels_with_comment_SKIPS_commenter(self):
        publisher = self._make_publisher()

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter:
            task = {
                "page":       "MyPage",
                "video_path": "v.mp4",
                "post_type":  "reels",
                "comment":    "Great!",
            }
            publisher.publish(task)
            MockCommenter.assert_not_called()

    def test_FC22_empty_comment_skips_commenter(self):
        publisher = self._make_publisher()

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter:
            task = {
                "page":       "MyPage",
                "video_path": "v.mp4",
                "post_type":  "feed",
                "comment":    "",
            }
            publisher.publish(task)
            MockCommenter.assert_not_called()

    def test_FC23_success_writes_facebook_comment_posted(self):
        publisher = self._make_publisher()
        events: list[dict] = []

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter, \
             patch("utils.audit_logger.append_event",
                   side_effect=lambda ev, **kw: events.append({"event": ev, **kw})):
            from core.facebook.commenter import CommentResult
            MockCommenter.return_value.post_comment.return_value = CommentResult(
                success=True, comment_id="cm_42", text="Yay",
            )
            task = {"page": "MyPage", "video_path": "v.mp4",
                    "post_type": "feed", "comment": "Yay"}
            publisher.publish(task)

        names = [e["event"] for e in events]
        self.assertIn("facebook_comment_posted", names)
        posted = [e for e in events if e["event"] == "facebook_comment_posted"][0]
        self.assertEqual(posted.get("publish_id"), "V99")

    def test_FC24_empty_comment_does_not_write_audit(self):
        """Empty comment: no commenter, no audit event."""
        publisher = self._make_publisher()
        events: list[dict] = []

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("utils.audit_logger.append_event",
                   side_effect=lambda ev, **kw: events.append({"event": ev, **kw})):
            task = {"page": "MyPage", "video_path": "v.mp4",
                    "post_type": "feed", "comment": ""}
            publisher.publish(task)

        names = [e["event"] for e in events]
        self.assertNotIn("facebook_comment_posted", names)
        self.assertNotIn("facebook_comment_skipped", names)
        self.assertNotIn("facebook_comment_failed", names)

    def test_FC25_api_error_writes_facebook_comment_failed(self):
        publisher = self._make_publisher()
        events: list[dict] = []

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter, \
             patch("utils.audit_logger.append_event",
                   side_effect=lambda ev, **kw: events.append({"event": ev, **kw})):
            from core.facebook.commenter import CommentResult
            MockCommenter.return_value.post_comment.return_value = CommentResult(
                success=False, error_code="200",
                message="Permission denied", text="Hi",
            )
            task = {"page": "MyPage", "video_path": "v.mp4",
                    "post_type": "feed", "comment": "Hi"}
            publisher.publish(task)

        names = [e["event"] for e in events]
        self.assertIn("facebook_comment_failed", names)
        failed = [e for e in events if e["event"] == "facebook_comment_failed"][0]
        self.assertEqual(failed.get("error_code"), "200")

    def test_FC26_comment_failure_preserves_publish_success(self):
        """Critical: comment errors must NEVER break a successful publish."""
        publisher = self._make_publisher()

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter:
            from core.facebook.commenter import CommentResult
            MockCommenter.return_value.post_comment.return_value = CommentResult(
                success=False, error_code="32",
                message="rate limit", text="Hi",
            )
            task = {"page": "MyPage", "video_path": "v.mp4",
                    "post_type": "feed", "comment": "Hi"}
            result = publisher.publish(task)

        self.assertTrue(result.success)
        self.assertEqual(result.external_post_id, "V99")
        self.assertEqual(result.status, "published")

    def test_FC27_commenter_exception_does_not_break_publish(self):
        publisher = self._make_publisher()

        with self._patch_engine(), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter:
            MockCommenter.side_effect = RuntimeError("boom")
            task = {"page": "MyPage", "video_path": "v.mp4",
                    "post_type": "feed", "comment": "Hi"}
            result = publisher.publish(task)

        self.assertTrue(result.success)
        self.assertEqual(result.external_post_id, "V99")

    def test_FC28_engine_receives_empty_comment_to_avoid_double_post(self):
        """FB publisher must clear task['comment'] before calling engine —
        otherwise engine ALSO calls post_comment internally → duplicate.
        """
        publisher = self._make_publisher()

        captured = {}

        def fake_run_sync(self_engine, task_arg):
            captured["task"] = task_arg
            return ("https://fb.com/x/videos/V1", "V1")

        with patch("core.upload_engine.UploadEngine.run_sync", fake_run_sync), \
             self._patch_token_store(), \
             patch("core.facebook.commenter.FacebookCommenter") as MockCommenter:
            from core.facebook.commenter import CommentResult
            MockCommenter.return_value.post_comment.return_value = CommentResult(
                success=True, comment_id="cm", text="Yay",
            )
            task = {"page": "MyPage", "video_path": "v.mp4",
                    "post_type": "feed", "comment": "Yay"}
            publisher.publish(task)

        # The task passed to engine must have comment cleared
        self.assertEqual(captured["task"].get("comment"), "")
        # But the original task is untouched
        self.assertEqual(task["comment"], "Yay")


if __name__ == "__main__":
    unittest.main(verbosity=2)
