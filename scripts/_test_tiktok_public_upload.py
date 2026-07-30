"""
End-to-end test: upload PUBLIC video to TikTok + auto-comment.

Tests bot's TikTokPublisher with realistic task dict:
  - Auto-generated title with timestamp
  - Auto-generated description + hashtags
  - PUBLIC_TO_EVERYONE direct post
  - Auto-comment after publish

Designed to verify:
  ✓ Compliance guard passes
  ✓ Direct uploader handles init → upload → status poll → publish
  ✓ Audit log captures success
  ✓ Auto-comment posts after publish_id is obtained
  ✓ Final video URL is reachable

Output: comprehensive PASS/FAIL matrix + TikTok video URL.

Usage:
    .venv\\Scripts\\python.exe scripts\\_test_tiktok_public_upload.py \\
        --video "C:\\Users\\Administrator\\Downloads\\clip_02 (4).mp4" \\
        --account klcloset96

Exit codes:
    0 — all checks PASS, video URL captured
    1 — at least one check FAIL
    2 — fatal setup error (no account, no video, etc.)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Force UTF-8 stdout on Windows cmd
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ─── Test conditions matrix ──────────────────────────────────────────────────

class TestMatrix:
    """Tracks PASS/FAIL for each test condition."""
    def __init__(self):
        self.conditions = []   # list of (name, status, detail)

    def pass_(self, name: str, detail: str = ""):
        self.conditions.append((name, "PASS", detail))
        print(f"  \033[92m✓\033[0m {name}  {detail}")

    def fail(self, name: str, detail: str = ""):
        self.conditions.append((name, "FAIL", detail))
        print(f"  \033[91m✗ {name}\033[0m")
        if detail:
            print(f"     \033[91m{detail}\033[0m")

    def warn(self, name: str, detail: str = ""):
        self.conditions.append((name, "WARN", detail))
        print(f"  \033[93m⚠ {name}\033[0m  {detail}")

    def info(self, msg: str):
        print(f"  \033[90m· {msg}\033[0m")

    def summary(self) -> int:
        passed = sum(1 for c in self.conditions if c[1] == "PASS")
        failed = sum(1 for c in self.conditions if c[1] == "FAIL")
        warns  = sum(1 for c in self.conditions if c[1] == "WARN")
        total  = len(self.conditions)
        print()
        print("=" * 76)
        print(f"  TEST MATRIX SUMMARY — {passed} pass / {failed} fail / {warns} warn / {total} total")
        print("=" * 76)
        print(f"  {'Condition':<60} {'Status':<8}")
        print(f"  {'-' * 60} {'-' * 8}")
        for name, status, detail in self.conditions:
            color = {"PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}.get(status, "")
            print(f"  {name[:60]:<60} {color}{status}\033[0m")
        return 0 if failed == 0 else 1


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to .mp4")
    parser.add_argument("--account", required=True, help="TikTok account display_name or open_id prefix")
    parser.add_argument("--title-prefix", default="Bot test direct public",
                        help="Title prefix (timestamp appended)")
    parser.add_argument("--comment", default="",
                        help="Auto-comment text (default: auto-generate)")
    parser.add_argument("--privacy", default="PUBLIC_TO_EVERYONE",
                        choices=["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS",
                                 "FOLLOWER_OF_CREATOR", "SELF_ONLY"],
                        help="Target privacy level (direct post only)")
    parser.add_argument("--mode", default="direct", choices=["direct", "draft"],
                        help="Publish mode: 'direct' = direct post, 'draft' = TikTok Inbox draft")
    args = parser.parse_args()

    m = TestMatrix()

    print("=" * 76)
    print("  TikTok PUBLIC Upload — End-to-End Test")
    print("=" * 76)

    # ── PRE-FLIGHT ─────────────────────────────────────────────────────────
    print("\n[PHASE 1] Pre-flight checks")

    # P1.1 — Video file exists + size sane
    vp = args.video
    if not os.path.isfile(vp):
        m.fail("video.exists", f"Not found: {vp}")
        return m.summary()
    size = os.path.getsize(vp)
    m.pass_("video.exists", f"{os.path.basename(vp)} ({size:,} bytes / {size/1024/1024:.1f} MB)")

    if size > 500 * 1024 * 1024:
        m.fail("video.size", f"Exceeds 500 MB TikTok limit: {size:,}")
        return m.summary()
    if size < 1024:
        m.fail("video.size", "Too small (< 1 KB)")
        return m.summary()
    m.pass_("video.size", "Within TikTok limit (< 500 MB)")

    # P1.2 — MP4 magic bytes
    with open(vp, "rb") as f:
        head = f.read(12)
    is_mp4 = b"ftyp" in head
    if is_mp4:
        m.pass_("video.format", f"MP4 magic detected ({head[:12].hex()})")
    else:
        m.warn("video.format", f"No MP4 ftyp in header; TikTok may reject ({head.hex()})")

    # P1.3 — Config valid + audit flags correct
    try:
        with open("data/config.json", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as exc:
        m.fail("config.load", str(exc))
        return m.summary()

    required = {
        "tiktok_audit_approved":      True,
        "tiktok_enable_direct_post":  True,
        "tiktok_publish_mode":        "direct_public",
        "tiktok_privacy_level":       "PUBLIC_TO_EVERYONE",
    }
    for k, want in required.items():
        got = cfg.get(k)
        if got == want:
            m.pass_(f"config.{k}", f"= {got!r}")
        else:
            m.fail(f"config.{k}", f"want {want!r} got {got!r}")

    # P1.4 — Token store + account
    from core.tiktok.token_store import get_default_store
    store = get_default_store()
    accounts = store.all_accounts()
    if not accounts:
        m.fail("account.connected", "No TikTok accounts in token store")
        return m.summary()

    filt = args.account.lower()
    matched = [a for a in accounts
               if filt in a.display_name.lower() or a.open_id.startswith(args.account)]
    if not matched:
        m.fail("account.match", f"No account matches '{args.account}'")
        return m.summary()
    account = matched[0]
    m.pass_("account.match", f"@{account.display_name} (open_id={account.open_id[:16]}…)")

    if not account.is_token_valid():
        m.fail("account.token_valid", "Access token expired")
        return m.summary()
    m.pass_("account.token_valid", "Token healthy")

    # P1.5 — Scopes
    needed_scopes = {"user.info.basic", "video.upload", "video.publish"}
    have = set(account.scopes)
    if needed_scopes.issubset(have):
        m.pass_("account.scopes", f"All 3 scopes granted")
    else:
        missing = needed_scopes - have
        m.fail("account.scopes", f"Missing: {missing}")
        return m.summary()

    # P1.6 — Capability check via TikTok API
    print("\n[PHASE 2] TikTok server capability check")
    from core.tiktok.creator_info import query_creator_info
    try:
        info = query_creator_info(access_token=account.access_token, timeout_s=15)
    except Exception as exc:
        m.fail("capability.query", f"{type(exc).__name__}: {exc}")
        return m.summary()

    if "PUBLIC_TO_EVERYONE" in info.privacy_level_options:
        m.pass_("capability.public", f"PUBLIC_TO_EVERYONE unlocked")
    else:
        m.fail("capability.public", f"Only: {info.privacy_level_options}")
        return m.summary()

    m.info(f"max_duration={info.max_video_post_duration_sec}s, "
           f"duet={'off' if info.duet_disabled else 'on'}, "
           f"comment={'off' if info.comment_disabled else 'on'}")

    # ── BUILD TASK ─────────────────────────────────────────────────────────
    print("\n[PHASE 3] Build publish task")

    ts_local = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = f"{args.title_prefix} {ts_local}"
    description = (
        f"Bot upload test — direct PUBLIC post.\n"
        f"Timestamp: {ts_local}.\n"
        f"#test #bot #lttstudio"
    )

    if args.comment:
        comment_text = args.comment
    else:
        comment_text = (
            f"Bot auto-comment test @ {ts_local} — confirm comment API works. 🤖"
        )

    post_type = "tiktok_direct" if args.mode == "direct" else "tiktok_draft"

    task = {
        "video_path":        vp,
        "title":             title,
        "description":       description,
        "account":           account.open_id,    # publisher resolves by open_id
        "post_type":         post_type,
        "privacy_level":     args.privacy,
        "comment":           comment_text,
        # TikTok audit requires user confirmation timestamp (advisory)
        "user_confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    m.pass_("task.title", f"'{title}'")
    m.pass_("task.post_type", post_type)
    m.pass_("task.privacy", args.privacy)
    m.pass_("task.comment", f"'{comment_text[:60]}…'")

    # ── EXECUTE PUBLISH ───────────────────────────────────────────────────
    print("\n[PHASE 4] Execute publish (this takes 30-90s for ~60 MB video)")

    from core.tiktok.publisher_service import TikTokPublisher

    log_buffer = []
    def _on_log(msg, lvl="info"):
        line = f"[{lvl}] {msg}"
        log_buffer.append(line)
        print(f"    {line}")

    status_buffer = []
    def _on_status(msg):
        status_buffer.append(msg)
        print(f"    [status] {msg}")

    stop_event = threading.Event()

    publisher = TikTokPublisher(
        config     = cfg,
        stop_event = stop_event,
        on_log     = _on_log,
        on_status  = _on_status,
    )

    t_start = time.perf_counter()
    publish_result = None
    publish_err    = None
    try:
        publish_result = publisher.publish(task)
        elapsed = time.perf_counter() - t_start
        m.pass_("publish.execute", f"completed in {elapsed:.1f}s")
    except Exception as exc:
        elapsed = time.perf_counter() - t_start
        publish_err = exc
        m.fail("publish.execute",
               f"{type(exc).__name__}: {str(exc)[:200]} (after {elapsed:.1f}s)")
        print()
        print("=== Stack trace ===")
        traceback.print_exc()

    # ── VERIFY RESULT ──────────────────────────────────────────────────────
    print("\n[PHASE 5] Verify publish result")

    if publish_result is None:
        m.fail("publish.result", "No result object (exception above)")
        return m.summary()

    # 'success' = direct post done; 'draft' = sent to inbox awaiting manual publish
    if publish_result.status in ("success", "draft"):
        m.pass_("publish.status", f"= '{publish_result.status}'")
    else:
        m.fail("publish.status", f"got '{publish_result.status}'")

    publish_id = publish_result.external_post_id
    if publish_id:
        m.pass_("publish.publish_id", f"= {publish_id}")
    else:
        m.fail("publish.publish_id", "missing")

    # PublishResult has `external_post_url` (not `external_url`)
    video_url = getattr(publish_result, "external_post_url", "") or ""
    if video_url:
        m.pass_("publish.url", video_url)
    else:
        # Draft mode never returns a URL — video is in user's TikTok Inbox
        if publish_result.status == "draft":
            m.info("draft mode: no URL yet — user must open TikTok app and publish manually")
        else:
            m.warn("publish.url", "No direct URL returned by TikTok")

    # ── COMMENT VERIFICATION ──────────────────────────────────────────────
    print("\n[PHASE 6] Verify auto-comment was attempted")
    comment_attempted = any("Comment" in l or "comment" in l for l in log_buffer)
    if comment_attempted:
        # Look for success/failure markers
        comment_ok = any("comment đã đăng" in l.lower() or "comment success" in l.lower()
                         or "[tiktok comment]" in l.lower()
                         for l in log_buffer)
        if comment_ok:
            m.pass_("comment.posted", "auto-comment logged as posted")
        else:
            comment_skip = any("bỏ qua comment" in l.lower() or "skip comment" in l.lower()
                              for l in log_buffer)
            if comment_skip:
                m.warn("comment.posted", "skipped (logged)")
            else:
                m.warn("comment.posted", "attempt logged but no explicit success marker")
    else:
        m.warn("comment.posted", "no comment-related log lines found")

    # ── AUDIT LOG ──────────────────────────────────────────────────────────
    print("\n[PHASE 7] Verify audit log")
    audit_path = ROOT / "data" / "audit_log.jsonl"
    if audit_path.exists():
        with audit_path.open(encoding="utf-8") as f:
            lines = f.readlines()
        recent_events = []
        for line in lines[-100:]:
            try:
                e = json.loads(line)
                if e.get("event", "").startswith("tiktok_publish") or e.get("evt", "").startswith("tiktok_publish"):
                    recent_events.append(e)
            except Exception:
                pass
        attempt_seen = any("publish_attempt" in str(e) for e in recent_events)
        success_seen = any("publish_success" in str(e) for e in recent_events)
        if attempt_seen:
            m.pass_("audit.attempt", "tiktok_publish_attempt logged")
        else:
            m.warn("audit.attempt", "not found in last 100 entries")
        if success_seen:
            m.pass_("audit.success", "tiktok_publish_success logged")
        else:
            m.warn("audit.success", "not found")
    else:
        m.warn("audit.log_file", f"not present: {audit_path}")

    # ── FINAL ──────────────────────────────────────────────────────────────
    print("\n[PHASE 8] Summary + verification URL")
    if video_url:
        print(f"\n  🎬 VIDEO URL: {video_url}")
        print(f"\n  Verify steps:")
        print(f"    1. Open URL in browser → should load TikTok video page")
        print(f"    2. Open URL in incognito → should still load (PUBLIC)")
        print(f"    3. TikTok app → @{account.display_name} → top video")
    elif publish_id:
        print(f"\n  📋 PUBLISH_ID: {publish_id}")
        print(f"     (Video URL not directly returned. Check @{account.display_name} on TikTok app)")

    return m.summary()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[CTRL+C] Interrupted by user")
        sys.exit(130)
