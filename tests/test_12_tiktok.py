"""
test_12_tiktok.py — Unit tests for TikTok integration modules.

Coverage:
  T1:  TikTokAccount dataclass (is_token_valid, serialisation)
  T2:  TikTokTokenStore (upsert, get, remove, encryption smoke-test)
  T3:  _generate_pkce_pair() (length, S256 correctness)
  T4:  TikTokClient._parse() error handling
  T5:  TikTokClient HTTP methods (get, post, put_binary) via mock
  T6:  TikTokError classification (auth, rate-limit, server-error)
  T7:  poll_until_done() — success, failure, stop_event, timeout
  T8:  TikTokDraftUploader.upload() — init + chunk + poll flow
  T9:  TikTokDirectUploader.upload() — privacy mapping + flow
  T10: TikTokPublisher.publish() — account resolution, draft/direct dispatch
  T11: publisher_registry — "tiktok" resolves to TikTokPublisher
  T12: config.json has all new TikTok keys
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch, call

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# T1 — TikTokAccount dataclass
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokAccount(unittest.TestCase):

    def _make(self, expires_in=3600, refresh_in=86400*365) -> "TikTokAccount":
        from core.tiktok.token_store import TikTokAccount
        now = time.time()
        return TikTokAccount(
            open_id            = "user_001",
            display_name       = "Test User",
            avatar_url         = "https://cdn.tiktok.com/avatar.jpg",
            access_token       = "tok_abc",
            refresh_token      = "ref_xyz",
            expires_at         = now + expires_in,
            refresh_expires_at = now + refresh_in,
            scopes             = ["user.info.basic", "video.upload"],
            connected_at       = "2026-05-14T00:00:00",
        )

    def test_is_token_valid_fresh(self):
        acc = self._make(expires_in=3600)
        self.assertTrue(acc.is_token_valid())

    def test_is_token_valid_expired(self):
        acc = self._make(expires_in=-10)
        self.assertFalse(acc.is_token_valid())

    def test_is_token_valid_margin(self):
        """Token with < 60 s remaining should be treated as invalid."""
        acc = self._make(expires_in=30)   # 30 s < 60 s buffer
        self.assertFalse(acc.is_token_valid())

    def test_is_refresh_valid_fresh(self):
        acc = self._make(refresh_in=86400 * 365)
        self.assertTrue(acc.is_refresh_valid())

    def test_is_refresh_valid_expired(self):
        acc = self._make(refresh_in=-10)
        self.assertFalse(acc.is_refresh_valid())

    def test_days_until_expiry_positive(self):
        acc = self._make(expires_in=86400 * 2)
        self.assertGreaterEqual(acc.days_until_expiry(), 1)

    def test_days_until_expiry_zero_when_expired(self):
        acc = self._make(expires_in=-3600)
        self.assertEqual(acc.days_until_expiry(), 0)

    def test_roundtrip_serialisation(self):
        from core.tiktok.token_store import TikTokAccount
        acc = self._make()
        d   = acc.to_dict()
        acc2 = TikTokAccount.from_dict(d)
        self.assertEqual(acc.open_id,       acc2.open_id)
        self.assertEqual(acc.display_name,  acc2.display_name)
        self.assertEqual(acc.access_token,  acc2.access_token)
        self.assertAlmostEqual(acc.expires_at, acc2.expires_at, delta=0.001)
        self.assertEqual(acc.scopes,        acc2.scopes)

    def test_token_status_label_fresh(self):
        acc = self._make(expires_in=86400 * 3)
        label, color = acc.token_status_label()
        self.assertIn("✅", label)
        self.assertEqual(color, "#4CAF50")

    def test_token_status_label_expired(self):
        acc = self._make(expires_in=-10)
        label, color = acc.token_status_label()
        self.assertIn("❌", label)
        self.assertEqual(color, "#F44336")


# ─────────────────────────────────────────────────────────────────────────────
# T2 — TikTokTokenStore
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokTokenStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".enc", delete=False)
        self._tmp.close()
        from core.tiktok.token_store import TikTokTokenStore
        self._store = TikTokTokenStore(path=self._tmp.name)

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except Exception:
            pass
        for ext in (".tmp",):
            try:
                os.unlink(self._tmp.name.replace(".enc", ext))
            except Exception:
                pass

    def _account(self, open_id="u1", name="Alice") -> "TikTokAccount":
        from core.tiktok.token_store import TikTokAccount
        now = time.time()
        return TikTokAccount(
            open_id=open_id, display_name=name, avatar_url="",
            access_token="tok", refresh_token="ref",
            expires_at=now + 3600, refresh_expires_at=now + 86400 * 365,
            scopes=["user.info.basic"], connected_at="2026-01-01",
        )

    def test_upsert_then_get(self):
        acc = self._account()
        self._store.upsert_account(acc)
        got = self._store.get_account("u1")
        self.assertIsNotNone(got)
        self.assertEqual(got.display_name, "Alice")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self._store.get_account("nonexistent"))

    def test_remove_account(self):
        acc = self._account()
        self._store.upsert_account(acc)
        self._store.remove_account("u1")
        self.assertIsNone(self._store.get_account("u1"))

    def test_all_accounts(self):
        self._store.upsert_account(self._account("u1", "Alice"))
        self._store.upsert_account(self._account("u2", "Bob"))
        all_ = self._store.all_accounts()
        self.assertEqual(len(all_), 2)

    def test_upsert_updates_existing(self):
        acc = self._account()
        self._store.upsert_account(acc)
        acc2 = self._account()
        acc2.display_name = "Alice Updated"
        self._store.upsert_account(acc2)
        got = self._store.get_account("u1")
        self.assertEqual(got.display_name, "Alice Updated")

    def test_is_empty_initially(self):
        from core.tiktok.token_store import TikTokTokenStore
        empty_store = TikTokTokenStore(path=self._tmp.name + ".empty")
        try:
            self.assertTrue(empty_store.is_empty())
        finally:
            try:
                os.unlink(self._tmp.name + ".empty")
            except Exception:
                pass

    def test_persistence_across_instances(self):
        """Data saved by one store instance must be loadable by another."""
        acc = self._account()
        self._store.upsert_account(acc)

        from core.tiktok.token_store import TikTokTokenStore
        store2 = TikTokTokenStore(path=self._tmp.name)
        got = store2.get_account("u1")
        self.assertIsNotNone(got)
        self.assertEqual(got.open_id, "u1")


# ─────────────────────────────────────────────────────────────────────────────
# T3 — PKCE pair generation
# ─────────────────────────────────────────────────────────────────────────────

class TestPKCE(unittest.TestCase):

    def test_verifier_length_in_range(self):
        from core.tiktok.auth_manager import _generate_pkce_pair
        v, _ = _generate_pkce_pair()
        # RFC 7636: code_verifier length must be 43..128
        self.assertGreaterEqual(len(v), 43)
        self.assertLessEqual(len(v),   128)

    def test_challenge_is_s256(self):
        import base64
        import hashlib
        from core.tiktok.auth_manager import _generate_pkce_pair
        v, c = _generate_pkce_pair()
        expected_digest = hashlib.sha256(v.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
        self.assertEqual(c, expected_challenge)

    def test_pairs_are_unique(self):
        from core.tiktok.auth_manager import _generate_pkce_pair
        pairs = {_generate_pkce_pair()[0] for _ in range(10)}
        self.assertEqual(len(pairs), 10)   # all verifiers unique

    def test_challenge_url_safe(self):
        """Challenge must be URL-safe base64 (no +, /, =)."""
        from core.tiktok.auth_manager import _generate_pkce_pair
        _, c = _generate_pkce_pair()
        self.assertNotIn("+", c)
        self.assertNotIn("/", c)
        self.assertNotIn("=", c)


# ─────────────────────────────────────────────────────────────────────────────
# T4 — TikTokError classification
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokError(unittest.TestCase):

    def _make(self, code="", status=200) -> "TikTokError":
        from core.tiktok.client import TikTokError
        return TikTokError("test", error_code=code, http_status=status)

    def test_auth_error_by_code(self):
        err = self._make(code="access_token_invalid")
        self.assertTrue(err.is_auth_error())

    def test_auth_error_by_http_401(self):
        err = self._make(status=401)
        self.assertTrue(err.is_auth_error())

    def test_rate_limit_by_code(self):
        err = self._make(code="rate_limit_exceeded")
        self.assertTrue(err.is_rate_limit())

    def test_rate_limit_by_http_429(self):
        err = self._make(status=429)
        self.assertTrue(err.is_rate_limit())

    def test_server_error_500(self):
        err = self._make(status=500)
        self.assertTrue(err.is_server_error())

    def test_server_error_503(self):
        err = self._make(status=503)
        self.assertTrue(err.is_server_error())

    def test_normal_error_not_auth_or_rate(self):
        err = self._make(code="some_other_error", status=400)
        self.assertFalse(err.is_auth_error())
        self.assertFalse(err.is_rate_limit())
        self.assertFalse(err.is_server_error())


# ─────────────────────────────────────────────────────────────────────────────
# T5 — TikTokClient._parse()
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokClientParse(unittest.TestCase):

    def _resp(self, body: dict, status: int = 200) -> MagicMock:
        r = MagicMock()
        r.json.return_value = body
        r.ok = (200 <= status < 300)
        r.status_code = status
        r.text = str(body)
        return r

    def test_ok_response_returns_data(self):
        from core.tiktok.client import TikTokClient
        resp = self._resp({
            "data": {"publish_id": "abc"},
            "error": {"code": "ok", "message": ""}
        })
        result = TikTokClient._parse(resp)
        self.assertEqual(result["publish_id"], "abc")

    def test_error_code_raises(self):
        from core.tiktok.client import TikTokClient, TikTokError
        resp = self._resp({
            "data": {},
            "error": {"code": "access_token_invalid", "message": "bad token"}
        })
        with self.assertRaises(TikTokError) as ctx:
            TikTokClient._parse(resp)
        self.assertEqual(ctx.exception.error_code, "access_token_invalid")

    def test_non_json_non_ok_raises(self):
        from core.tiktok.client import TikTokClient, TikTokError
        r = MagicMock()
        r.json.side_effect = ValueError("not json")
        r.ok = False
        r.status_code = 503
        r.text = "Service Unavailable"
        with self.assertRaises(TikTokError) as ctx:
            TikTokClient._parse(r)
        self.assertEqual(ctx.exception.http_status, 503)

    def test_success_code_string_variants(self):
        """'success' and '' are also valid ok codes."""
        from core.tiktok.client import TikTokClient
        for ok_code in ("ok", "success", "OK"):
            resp = self._resp({"data": {"x": 1}, "error": {"code": ok_code}})
            result = TikTokClient._parse(resp)
            self.assertEqual(result.get("x"), 1)


# ─────────────────────────────────────────────────────────────────────────────
# T6 — poll_until_done()
# ─────────────────────────────────────────────────────────────────────────────

class TestPollUntilDone(unittest.TestCase):

    def _client(self, statuses: list[str]) -> MagicMock:
        """Mock TikTokClient.post that returns statuses in sequence."""
        client = MagicMock()
        responses = [
            {"process_info": {"status": s, "uploaded_bytes": 0, "fail_reason": ""}}
            for s in statuses
        ]
        client.post.side_effect = responses
        return client

    def test_immediate_success(self):
        from core.tiktok.status_poller import poll_until_done
        client = self._client(["PROCESS_SUCCESS"])
        result = poll_until_done(client, "pub_1", poll_interval_s=0)
        self.assertEqual(result, "PROCESS_SUCCESS")

    def test_success_after_two_polls(self):
        from core.tiktok.status_poller import poll_until_done
        client = self._client([
            "PROCESSING_UPLOAD",
            "PROCESSING_INTERCUT_AND_UPLOAD",
            "PROCESS_SUCCESS",
        ])
        with patch("core.tiktok.status_poller.time.sleep"):
            result = poll_until_done(client, "pub_2", poll_interval_s=0.001)
        self.assertEqual(result, "PROCESS_SUCCESS")
        self.assertEqual(client.post.call_count, 3)

    def test_process_failed_raises(self):
        from core.tiktok.status_poller import poll_until_done, TikTokError
        client = self._client(["PROCESS_FAILED"])
        client.post.side_effect = [
            {"process_info": {"status": "PROCESS_FAILED", "fail_reason": "bad video", "uploaded_bytes": 0}}
        ]
        with self.assertRaises(TikTokError) as ctx:
            poll_until_done(client, "pub_3", poll_interval_s=0)
        self.assertIn("bad video", str(ctx.exception))

    def test_stop_event_raises_interrupted(self):
        from core.tiktok.status_poller import poll_until_done
        stop = threading.Event()
        stop.set()
        client = MagicMock()
        with self.assertRaises(InterruptedError):
            poll_until_done(client, "pub_4", stop_event=stop)

    def test_inbox_status_treated_as_success(self):
        from core.tiktok.status_poller import poll_until_done
        client = self._client(["SEND_TO_USER_INBOX"])
        result = poll_until_done(client, "pub_5", poll_interval_s=0)
        self.assertEqual(result, "SEND_TO_USER_INBOX")

    def test_timeout_raises_tiktok_error(self):
        from core.tiktok.status_poller import poll_until_done, TikTokError
        client = MagicMock()
        client.post.return_value = {
            "process_info": {"status": "PROCESSING_UPLOAD", "uploaded_bytes": 0, "fail_reason": ""}
        }
        with patch("core.tiktok.status_poller.time.sleep"):
            with self.assertRaises(TikTokError) as ctx:
                poll_until_done(client, "pub_6", poll_interval_s=0, timeout_s=0.001)
        self.assertEqual(ctx.exception.error_code, "timeout")


# ─────────────────────────────────────────────────────────────────────────────
# T7 — TikTokDraftUploader
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokDraftUploader(unittest.TestCase):

    def _make_video(self, size=1024) -> str:
        f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        f.write(b"X" * size)
        f.close()
        return f.name

    def _make_client(self, publish_id="pub_draft_1"):
        client = MagicMock()
        client.post.side_effect = [
            # Phase 1: init response
            {"publish_id": publish_id, "upload_url": "https://upload.tiktok.com/x"},
            # Phase 3: status poll response
            {"process_info": {"status": "SEND_TO_USER_INBOX", "uploaded_bytes": 1024, "fail_reason": ""}},
        ]
        client.put_binary.return_value = 200
        return client

    def _make_uploader(self, client):
        from core.tiktok.uploader_draft import TikTokDraftUploader
        return TikTokDraftUploader(
            client=client, config={},
            stop_event=threading.Event(),
        )

    def test_upload_returns_publish_id(self):
        video = self._make_video()
        client = self._make_client("pub_42")
        uploader = self._make_uploader(client)
        try:
            publish_id, post_url = uploader.upload({
                "video_path":  video,
                "title":       "Test",
                "description": "Draft test",
            })
        finally:
            os.unlink(video)
        self.assertEqual(publish_id, "pub_42")
        self.assertEqual(post_url, "")   # draft has no public URL

    def test_upload_calls_init_endpoint(self):
        video = self._make_video()
        client = self._make_client()
        uploader = self._make_uploader(client)
        try:
            uploader.upload({"video_path": video, "title": "T"})
        finally:
            os.unlink(video)
        first_call_path = client.post.call_args_list[0][0][0]
        self.assertIn("inbox", first_call_path)

    def test_upload_calls_put_binary(self):
        video = self._make_video(1024)
        client = self._make_client()
        uploader = self._make_uploader(client)
        try:
            uploader.upload({"video_path": video, "title": "T"})
        finally:
            os.unlink(video)
        client.put_binary.assert_called_once()

    def test_missing_video_raises(self):
        from core.tiktok.uploader_draft import TikTokDraftUploader
        client = MagicMock()
        uploader = TikTokDraftUploader(client=client, config={})
        with self.assertRaises(FileNotFoundError):
            uploader.upload({"video_path": "/nonexistent/video.mp4"})

    def test_init_failure_raises_tiktok_error(self):
        from core.tiktok.client import TikTokError
        from core.tiktok.uploader_draft import TikTokDraftUploader
        video = self._make_video()
        client = MagicMock()
        client.post.side_effect = TikTokError("API down", error_code="server_error", http_status=500)
        uploader = TikTokDraftUploader(client=client, config={})
        try:
            with self.assertRaises(TikTokError):
                uploader.upload({"video_path": video, "title": "T"})
        finally:
            os.unlink(video)

    def test_stop_event_during_upload(self):
        from core.tiktok.uploader_draft import TikTokDraftUploader
        video = self._make_video(1024)
        stop = threading.Event()
        stop.set()   # already stopped

        client = MagicMock()
        uploader = TikTokDraftUploader(client=client, config={}, stop_event=stop)
        try:
            with self.assertRaises(InterruptedError):
                uploader.upload({"video_path": video, "title": "T"})
        finally:
            os.unlink(video)


# ─────────────────────────────────────────────────────────────────────────────
# T8 — TikTokDirectUploader
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokDirectUploader(unittest.TestCase):

    def _make_video(self, size=512) -> str:
        f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        f.write(b"Y" * size)
        f.close()
        return f.name

    def _make_client(self, publish_id="pub_direct_1"):
        client = MagicMock()
        client.post.side_effect = [
            {"publish_id": publish_id, "upload_url": "https://upload.tiktok.com/d"},
            {"process_info": {"status": "PROCESS_SUCCESS", "uploaded_bytes": 512, "fail_reason": ""}},
        ]
        client.put_binary.return_value = 200
        return client

    def _make_uploader(self, client, config=None):
        from core.tiktok.uploader_direct import TikTokDirectUploader
        return TikTokDirectUploader(
            client=client,
            config=config or {},
            stop_event=threading.Event(),
        )

    def test_upload_returns_publish_id(self):
        video = self._make_video()
        client = self._make_client("pub_d_99")
        uploader = self._make_uploader(client)
        try:
            publish_id, url = uploader.upload({"video_path": video, "title": "T"})
        finally:
            os.unlink(video)
        self.assertEqual(publish_id, "pub_d_99")
        self.assertEqual(url, "")   # no public URL from API

    def test_upload_calls_direct_endpoint(self):
        video = self._make_video()
        client = self._make_client()
        uploader = self._make_uploader(client)
        try:
            uploader.upload({"video_path": video, "title": "T"})
        finally:
            os.unlink(video)
        first_path = client.post.call_args_list[0][0][0]
        self.assertNotIn("inbox", first_path)
        self.assertIn("publish", first_path)

    def test_privacy_default_self_only(self):
        """Default privacy_level must be SELF_ONLY (safe for unaudited apps)."""
        video = self._make_video()
        client = self._make_client()
        uploader = self._make_uploader(client)
        captured = {}

        original_post = client.post.side_effect

        def capture_post(path, payload):
            if not captured:
                captured["payload"] = payload
            return next(iter([
                {"publish_id": "pub_x", "upload_url": "https://x"},
                {"process_info": {"status": "PROCESS_SUCCESS", "uploaded_bytes": 0, "fail_reason": ""}},
            ]))

        # We need sequential side_effect, so re-build:
        responses = [
            {"publish_id": "pub_x", "upload_url": "https://upload.tiktok.com/x"},
            {"process_info": {"status": "PROCESS_SUCCESS", "uploaded_bytes": 0, "fail_reason": ""}},
        ]
        idx = [0]
        def seq_post(path, payload):
            if "publish" in path and idx[0] == 0:
                captured["payload"] = payload
            r = responses[idx[0]]
            idx[0] += 1
            return r
        client.post.side_effect = seq_post

        try:
            uploader.upload({"video_path": video, "title": "T"})
        finally:
            os.unlink(video)

        post_info = captured.get("payload", {}).get("post_info", {})
        self.assertEqual(post_info.get("privacy_level"), "SELF_ONLY")

    def test_keywords_appended_as_hashtags(self):
        """Keywords should appear as #tag in the description."""
        video = self._make_video()
        client = self._make_client()
        captured = {}

        responses = [
            {"publish_id": "pub_h", "upload_url": "https://upload.tiktok.com/h"},
            {"process_info": {"status": "PROCESS_SUCCESS", "uploaded_bytes": 0, "fail_reason": ""}},
        ]
        idx = [0]
        def seq_post(path, payload):
            if idx[0] == 0:
                captured["payload"] = payload
            r = responses[idx[0]]
            idx[0] += 1
            return r
        client.post.side_effect = seq_post

        uploader = self._make_uploader(client)
        try:
            uploader.upload({
                "video_path":  video,
                "title":       "Test",
                "description": "Hello world",
                "keywords":    "python, coding, tutorial",
            })
        finally:
            os.unlink(video)

        desc = captured.get("payload", {}).get("post_info", {}).get("description", "")
        self.assertIn("#python", desc)
        self.assertIn("#coding", desc)

    def test_privacy_mismatch_raises_runtime_error(self):
        """privacy_level_option_mismatch → clear RuntimeError."""
        from core.tiktok.client import TikTokError
        video = self._make_video()
        client = MagicMock()
        client.post.side_effect = TikTokError(
            "not allowed",
            error_code="privacy_level_option_mismatch",
            http_status=400,
        )
        uploader = self._make_uploader(client, config={})
        try:
            with self.assertRaises(RuntimeError) as ctx:
                uploader.upload({
                    "video_path":    video,
                    "title":         "T",
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                })
        finally:
            os.unlink(video)
        self.assertIn("SELF_ONLY", str(ctx.exception))


# ─────────────────────────────────────────────────────────────────────────────
# T9 — TikTokPublisher account resolution + dispatch
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokPublisher(unittest.TestCase):

    def _make_account(self, open_id="u1") -> "TikTokAccount":
        from core.tiktok.token_store import TikTokAccount
        now = time.time()
        return TikTokAccount(
            open_id=open_id, display_name="User", avatar_url="",
            access_token="tok", refresh_token="ref",
            expires_at=now + 3600, refresh_expires_at=now + 86400 * 365,
            scopes=["video.upload"], connected_at="2026-01-01",
        )

    def _make_publisher(self, accounts=None) -> "TikTokPublisher":
        from core.tiktok.publisher_service import TikTokPublisher
        pub = TikTokPublisher(
            config={}, stop_event=threading.Event(),
        )
        store = MagicMock()
        store.all_accounts.return_value = accounts or [self._make_account()]
        store.get_account.side_effect = lambda oid: next(
            (a for a in (accounts or [self._make_account()]) if a.open_id == oid), None
        )
        pub._token_store = store
        return pub

    def test_no_accounts_raises(self):
        from core.tiktok.publisher_service import TikTokPublisher
        pub = TikTokPublisher(config={}, stop_event=threading.Event())
        pub._token_store = MagicMock()
        pub._token_store.all_accounts.return_value = []
        with self.assertRaises(RuntimeError) as ctx:
            pub.publish({"video_path": "/tmp/x.mp4", "title": "T"})
        self.assertIn("Chưa kết nối", str(ctx.exception))

    def test_unknown_open_id_raises(self):
        from core.tiktok.publisher_service import TikTokPublisher
        pub = TikTokPublisher(config={}, stop_event=threading.Event())
        pub._token_store = MagicMock()
        pub._token_store.get_account.return_value = None
        with self.assertRaises(RuntimeError):
            pub.publish({"video_path": "/tmp/x.mp4", "account": "bad_id"})

    def test_dispatch_draft(self):
        """post_type=tiktok_draft → calls TikTokDraftUploader.upload()"""
        pub = self._make_publisher()
        with patch("core.tiktok.publisher_service.TikTokClient") as MockClient, \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   return_value=("pub_draft_X", "")) as mock_upload, \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            result = pub.publish({
                "video_path": "/tmp/v.mp4",
                "post_type":  "tiktok_draft",
                "title":      "T",
            })
        mock_upload.assert_called_once()
        self.assertEqual(result.status, "draft")
        self.assertEqual(result.external_post_id, "pub_draft_X")

    def test_dispatch_direct(self):
        """post_type=tiktok_direct → calls TikTokDirectUploader.upload()"""
        pub = self._make_publisher()
        with patch("core.tiktok.publisher_service.TikTokClient") as MockClient, \
             patch("core.tiktok.uploader_direct.TikTokDirectUploader.upload",
                   return_value=("pub_direct_Y", "")) as mock_upload, \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            result = pub.publish({
                "video_path": "/tmp/v.mp4",
                "post_type":  "tiktok_direct",
                "title":      "T",
            })
        mock_upload.assert_called_once()
        self.assertEqual(result.status, "published")

    def test_publish_result_success_true(self):
        pub = self._make_publisher()
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   return_value=("p_id", "")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            result = pub.publish({"video_path": "/x.mp4", "post_type": "tiktok_draft"})
        self.assertTrue(result.success)

    def test_expired_token_triggers_refresh(self):
        """Expired token → _ensure_token_fresh() → refresh_access_token()"""
        from core.tiktok.token_store import TikTokAccount
        from core.tiktok.publisher_service import TikTokPublisher

        expired = TikTokAccount(
            open_id="u_exp", display_name="Exp", avatar_url="",
            access_token="old_tok", refresh_token="ref_ok",
            expires_at=time.time() - 100,      # expired
            refresh_expires_at=time.time() + 86400 * 365,
            scopes=["video.upload"], connected_at="2026-01-01",
        )

        pub = TikTokPublisher(config={}, stop_event=threading.Event())
        pub._token_store = MagicMock()
        pub._token_store.all_accounts.return_value = [expired]
        pub._token_store.get_account.return_value = None

        refreshed = MagicMock()
        refreshed.is_token_valid.return_value = True
        refreshed.access_token = "new_tok"

        with patch("core.tiktok.auth_manager.TikTokAuthManager") as MockAuth:
            mock_mgr = MagicMock()
            mock_mgr.refresh_access_token.return_value = refreshed
            MockAuth.return_value = mock_mgr

            with patch("core.tiktok.publisher_service.TikTokClient") as MockClient, \
                 patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                       return_value=("p", "")), \
                 patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                       return_value=[]):
                pub.publish({"video_path": "/x.mp4", "post_type": "tiktok_draft"})

        mock_mgr.refresh_access_token.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# T10 — Publisher registry — tiktok keys
# ─────────────────────────────────────────────────────────────────────────────

class TestPublisherRegistryTikTok(unittest.TestCase):

    def test_facebook_resolves_to_facebook_publisher(self):
        from core.publisher_registry import get_publisher, _registry, _ensure_defaults_registered
        _ensure_defaults_registered()
        self.assertIn("facebook", _registry)
        from core.facebook.publisher_service import FacebookPublisher
        self.assertIs(_registry["facebook"], FacebookPublisher)

    def test_tiktok_resolves_to_tiktok_publisher(self):
        from core.publisher_registry import get_publisher, _registry, _ensure_defaults_registered
        _ensure_defaults_registered()
        self.assertIn("tiktok", _registry)
        from core.tiktok.publisher_service import TikTokPublisher
        self.assertIs(_registry["tiktok"], TikTokPublisher)

    def test_tiktok_draft_resolves_to_tiktok_publisher(self):
        from core.publisher_registry import _registry, _ensure_defaults_registered
        _ensure_defaults_registered()
        from core.tiktok.publisher_service import TikTokPublisher
        self.assertIs(_registry.get("tiktok_draft"), TikTokPublisher)

    def test_tiktok_direct_resolves_to_tiktok_publisher(self):
        from core.publisher_registry import _registry, _ensure_defaults_registered
        _ensure_defaults_registered()
        from core.tiktok.publisher_service import TikTokPublisher
        self.assertIs(_registry.get("tiktok_direct"), TikTokPublisher)

    def test_unknown_platform_raises_value_error(self):
        from core.publisher_registry import get_publisher
        with self.assertRaises(ValueError) as ctx:
            get_publisher("instagram", config={}, stop_event=threading.Event())
        self.assertIn("instagram", str(ctx.exception))

    def test_get_publisher_returns_publisher_instance(self):
        from core.publisher_registry import get_publisher
        from core.publisher import Publisher
        pub = get_publisher("facebook", config={}, stop_event=threading.Event())
        self.assertIsInstance(pub, Publisher)


# ─────────────────────────────────────────────────────────────────────────────
# T11 — config.json has new TikTok keys
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokConfigKeys(unittest.TestCase):

    REQUIRED_TIKTOK_KEYS = [
        "tiktok_client_key",
        "tiktok_client_secret",
        "tiktok_scopes",
        "tiktok_privacy_level",
        "tiktok_poll_interval_s",
        "tiktok_upload_timeout_s",
        "tiktok_request_timeout_s",
        "col_platform",
        "col_tiktok_link",
        "col_tiktok_id",
    ]

    def _load_config(self):
        import json
        cfg_path = os.path.join(BASE_DIR, "data", "config.json")
        if not os.path.exists(cfg_path):
            self.skipTest("data/config.json not found")
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)

    def test_all_tiktok_keys_present(self):
        config = self._load_config()
        missing = [k for k in self.REQUIRED_TIKTOK_KEYS if k not in config]
        self.assertEqual(missing, [], f"Thiếu keys trong config.json: {missing}")

    def test_tiktok_privacy_default_self_only(self):
        from core.config_defaults import DEFAULTS
        self.assertEqual(DEFAULTS.get("tiktok_privacy_level"), "SELF_ONLY")

    def test_tiktok_disable_flags_are_bool(self):
        config = self._load_config()
        for key in ("tiktok_disable_duet", "tiktok_disable_comment", "tiktok_disable_stitch"):
            self.assertIsInstance(config.get(key), bool, f"{key} must be bool")


if __name__ == "__main__":
    unittest.main(verbosity=2)
