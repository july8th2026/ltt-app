"""
test_32_system_user_token.py — Business Manager System User token import.

Covers AuthManager.import_system_user_token() (paste-token path, Giai đoạn 3):

  SU01: valid token, never-expiring     → AccountInfo(is_system_user=True, expiry="")
  SU02: 60-day token via debug_token    → token_expires_at set to ISO of expires_at
  SU03: empty token                     → ValueError
  SU04: token valid but no pages        → RuntimeError (no assets assigned)
  SU05: get_user_info raises GraphError → RuntimeError (invalid/revoked)
  SU06: pages carry per-page token      → stored on PageInfo
  SU07: AccountInfo round-trips is_system_user through to_dict/from_dict
  SU08: TokenRefresher skips system-user accounts (no exchange attempt)
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.auth_manager import AuthManager
from core.graph_client import GraphError
from core.token_store import AccountInfo, TokenStore


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = TokenStore(path=os.path.join(self._tmp.name, "tokens.enc"))
        config = {
            "meta_app_id": "APPID",
            "meta_app_secret": "APPSECRET",
            "graph_api_version": "v21.0",
        }
        self.mgr = AuthManager(config, self.store)

    def tearDown(self):
        self._tmp.cleanup()

    def _stub(self, *, user=None, pages=None, debug=None):
        self.mgr._client.get_user_info = lambda token: (
            user or {"id": "SU999", "name": "Lttstudio Bot"}
        )
        self.mgr._client.get_pages = lambda token: (pages if pages is not None else [])
        self.mgr._client.get = lambda path, params=None, token=None: (
            debug or {"data": {"expires_at": 0}}
        )


class TestImportSystemUserToken(_Base):

    def test_SU01_valid_never_expiring(self):
        self._stub(pages=[{"id": "111", "name": "Page A",
                           "access_token": "pt_a", "category": "Media"}])
        acc = self.mgr.import_system_user_token("VALIDTOKEN")
        self.assertTrue(acc.is_system_user)
        self.assertEqual(acc.token_expires_at, "")       # permanent
        self.assertEqual(acc.fb_user_id, "SU999")
        self.assertTrue(acc.name.endswith("(BM)"))
        self.assertEqual(acc.user_token, "VALIDTOKEN")
        self.assertIsNotNone(self.store.get_account("SU999"))

    def test_SU02_sixty_day_sets_expiry(self):
        future = int(datetime(2099, 1, 1).timestamp())
        self._stub(
            pages=[{"id": "111", "name": "Page A", "access_token": "pt_a"}],
            debug={"data": {"expires_at": future}},
        )
        acc = self.mgr.import_system_user_token("SHORTTOKEN")
        self.assertNotEqual(acc.token_expires_at, "")
        self.assertTrue(acc.token_expires_at.startswith("2099"))

    def test_SU03_empty_token(self):
        with self.assertRaises(ValueError):
            self.mgr.import_system_user_token("   ")

    def test_SU04_no_pages(self):
        self._stub(pages=[])
        with self.assertRaises(RuntimeError) as ctx:
            self.mgr.import_system_user_token("VALIDTOKEN")
        self.assertIn("Page", str(ctx.exception))

    def test_SU05_invalid_token(self):
        def _boom(token):
            raise GraphError("Invalid OAuth access token", code=190)
        self.mgr._client.get_user_info = _boom
        with self.assertRaises(RuntimeError):
            self.mgr.import_system_user_token("BADTOKEN")

    def test_SU06_page_tokens_stored(self):
        self._stub(pages=[
            {"id": "111", "name": "Page A", "access_token": "pt_a"},
            {"id": "222", "name": "Page B", "access_token": "pt_b"},
        ])
        acc = self.mgr.import_system_user_token("VALIDTOKEN")
        pages = acc.get_pages_list()
        self.assertEqual({p.id for p in pages}, {"111", "222"})
        self.assertEqual({p.access_token for p in pages}, {"pt_a", "pt_b"})
        self.assertTrue(all(p.selected for p in pages))

    def test_SU09_reimport_preserves_selection(self):
        # W1 — re-import must keep the user's tick/untick choices.
        self._stub(pages=[
            {"id": "111", "name": "A", "access_token": "pt_a"},
            {"id": "222", "name": "B", "access_token": "pt_b"},
        ])
        self.mgr.import_system_user_token("TOKEN")
        self.store.update_page_selection("SU999", "222", False)   # user unticks B
        acc = self.mgr.import_system_user_token("TOKEN")          # re-import
        sel = {p.id: p.selected for p in acc.get_pages_list()}
        self.assertFalse(sel["222"])                             # stayed unticked
        self.assertTrue(sel["111"])

    def test_SU10_skips_pages_without_token(self):
        # W2 — a page assigned without full control returns no access_token.
        self._stub(pages=[
            {"id": "111", "name": "A", "access_token": "pt_a"},
            {"id": "222", "name": "NoPerm", "access_token": ""},
        ])
        acc = self.mgr.import_system_user_token("TOKEN")
        self.assertEqual({p.id for p in acc.get_pages_list()}, {"111"})

    def test_SU12_all_pages_without_token_raises(self):
        self._stub(pages=[{"id": "111", "name": "A", "access_token": ""}])
        with self.assertRaises(RuntimeError) as ctx:
            self.mgr.import_system_user_token("TOKEN")
        self.assertIn("KHÔNG page", str(ctx.exception))


class TestSystemUserPlumbing(unittest.TestCase):

    def test_SU11_token_sanitization(self):
        # W3 — clean pasted tokens (quotes / prefix / wrapped newlines).
        san = AuthManager._sanitize_token
        self.assertEqual(san('  "EAAB123"  '), "EAAB123")
        self.assertEqual(san("access_token=EAAB123"), "EAAB123")
        self.assertEqual(san("EAAB\n123\n"), "EAAB123")
        self.assertEqual(san("Bearer EAAB123"), "EAAB123")
        self.assertEqual(san("'EAAB123'"), "EAAB123")

    def test_SU07_account_roundtrip_flag(self):
        acc = AccountInfo(
            fb_user_id="X", name="N", user_token="T",
            token_expires_at="", is_system_user=True,
        )
        restored = AccountInfo.from_dict(acc.to_dict())
        self.assertTrue(restored.is_system_user)

    def test_SU08_refresher_skips_system_user(self):
        from core.token_refresher import TokenRefresher

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = TokenStore(path=os.path.join(tmp.name, "tokens.enc"))
        store.save_account(AccountInfo(
            fb_user_id="SU1", name="Bot (BM)", user_token="T",
            token_expires_at=datetime(2000, 1, 1).isoformat(),   # past → would be 'expired'
            is_system_user=True,
        ))

        expired_called = []
        refresher = TokenRefresher(
            config={"meta_app_id": "A", "meta_app_secret": "B"},
            token_store=store,
            on_expired=lambda name: expired_called.append(name),
        )
        refresher._check_one(store.get_account("SU1"), "A", "B", object())
        self.assertEqual(expired_called, [])   # skipped, not reported expired


if __name__ == "__main__":
    unittest.main()
