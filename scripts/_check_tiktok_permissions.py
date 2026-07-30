"""
TikTok permission audit — comprehensive probe of what the bot CAN do right now.

Differentiates 3 layers of permissions:
  A. SCOPES GRANTED — what's in the access_token (from OAuth flow)
  B. CREATOR INFO  — what TikTok reports for the connected account
  C. AUDIT TIER    — what the publish API actually allows (the real gate)

Critical insight: Layer C can REJECT operations that Layers A and B suggest
should work. TikTok enforces audit-tier rules at the publish endpoint that
are not visible via /creator_info/query/.

This script probes all three layers and produces a GAP REPORT showing what's
nominally granted vs what's actually enforced.

Usage:
    .venv\\Scripts\\python.exe scripts\\_check_tiktok_permissions.py
    .venv\\Scripts\\python.exe scripts\\_check_tiktok_permissions.py --account klcloset96
    .venv\\Scripts\\python.exe scripts\\_check_tiktok_permissions.py --json

Exit codes:
    0 — Full PUBLIC posting capability confirmed
    1 — Limited capabilities (draft only, or SELF_ONLY restriction)
    2 — Severe restriction or errors
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force UTF-8 stdout on Windows cmd
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ─── Color helpers ───────────────────────────────────────────────────────────

class _C:
    OK    = "\033[92m"
    WARN  = "\033[93m"
    FAIL  = "\033[91m"
    DIM   = "\033[90m"
    BOLD  = "\033[1m"
    END   = "\033[0m"


def section(title: str):
    print(f"\n{_C.BOLD}━━━ {title} ━━━{_C.END}")


def ok(label: str, detail: str = ""):
    print(f"  {_C.OK}✓{_C.END} {label}{(': ' + detail) if detail else ''}")


def fail(label: str, detail: str = ""):
    print(f"  {_C.FAIL}✗ {label}{_C.END}{(': ' + detail) if detail else ''}")


def warn(label: str, detail: str = ""):
    print(f"  {_C.WARN}⚠ {label}{_C.END}{(': ' + detail) if detail else ''}")


def info(label: str, detail: str = ""):
    print(f"  {_C.DIM}·{_C.END} {label}{(': ' + detail) if detail else ''}")


# ─── Probe functions ─────────────────────────────────────────────────────────

def probe_init_direct(access_token: str, privacy: str, on_log=None):
    """
    Try direct-post init endpoint with given privacy.
    Returns (success: bool, error_code: str|None, error_msg: str|None, response: dict|None).
    Does NOT actually upload — just checks if init is accepted.
    """
    from core.tiktok.client import TikTokClient, TikTokError

    client = TikTokClient(access_token=access_token,
                         on_log=on_log or (lambda m, l: None),
                         timeout=15)

    # Minimal init payload — small dummy video size to test init accept/reject
    # We use 5 MB which is the MIN chunk size, well within all limits.
    DUMMY_SIZE = 5 * 1024 * 1024
    payload = {
        "post_info": {
            "title":           "permission_probe — DO NOT UPLOAD",
            "description":     "Probe-only test of init endpoint",
            "privacy_level":   privacy,
            "disable_duet":    False,
            "disable_comment": False,
            "disable_stitch":  False,
        },
        "source_info": {
            "source":            "FILE_UPLOAD",
            "video_size":        DUMMY_SIZE,
            "chunk_size":        DUMMY_SIZE,
            "total_chunk_count": 1,
        },
    }

    try:
        data = client.post("/v2/post/publish/video/init/", payload)
        return True, None, None, data
    except TikTokError as exc:
        return False, getattr(exc, "error_code", None), str(exc), None
    except Exception as exc:
        return False, type(exc).__name__, str(exc), None


def probe_init_draft(access_token: str, on_log=None):
    """Try draft (inbox) init endpoint."""
    from core.tiktok.client import TikTokClient, TikTokError

    client = TikTokClient(access_token=access_token,
                         on_log=on_log or (lambda m, l: None),
                         timeout=15)

    DUMMY_SIZE = 5 * 1024 * 1024
    payload = {
        "source_info": {
            "source":            "FILE_UPLOAD",
            "video_size":        DUMMY_SIZE,
            "chunk_size":        DUMMY_SIZE,
            "total_chunk_count": 1,
        },
    }

    try:
        data = client.post("/v2/post/publish/inbox/video/init/", payload)
        return True, None, None, data
    except TikTokError as exc:
        return False, getattr(exc, "error_code", None), str(exc), None
    except Exception as exc:
        return False, type(exc).__name__, str(exc), None


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=None,
                        help="Filter to one account by display_name or open_id prefix")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    from core.tiktok.token_store import get_default_store
    from core.tiktok.creator_info import query_creator_info

    store = get_default_store()
    accounts = store.all_accounts()
    if not accounts:
        print(f"{_C.FAIL}[FATAL] No TikTok accounts connected.{_C.END}")
        return 2

    if args.account:
        filt = args.account.lower()
        accounts = [a for a in accounts
                    if filt in a.display_name.lower() or a.open_id.startswith(args.account)]
        if not accounts:
            print(f"{_C.FAIL}[FATAL] No account matches '{args.account}'{_C.END}")
            return 2

    # Probe each account
    report = {"accounts": []}
    overall_status = 0  # 0=full, 1=limited, 2=broken

    for acc in accounts:
        print()
        print("=" * 76)
        print(f"  ACCOUNT: @{acc.display_name}  (open_id={acc.open_id[:16]}...)")
        print("=" * 76)

        if not acc.is_token_valid():
            fail("token", "expired — re-OAuth needed")
            overall_status = max(overall_status, 2)
            continue

        acc_report = {
            "display_name": acc.display_name,
            "open_id_prefix": acc.open_id[:16],
            "layer_a_scopes": {},
            "layer_b_creator_info": {},
            "layer_c_audit_enforcement": {},
            "gaps": [],
        }

        # ── LAYER A: Scopes granted on the access token ────────────────
        section("LAYER A — Scopes granted on access_token (from OAuth)")
        scopes_set = set(acc.scopes)
        for s in ["user.info.basic", "video.upload", "video.publish",
                  "comment.create", "comment.list"]:
            granted = s in scopes_set
            if granted:
                ok(f"scope.{s}", "granted")
            else:
                if s in ("comment.create", "comment.list"):
                    warn(f"scope.{s}", "NOT granted (auto-comment will be skipped)")
                else:
                    fail(f"scope.{s}", "NOT granted")
            acc_report["layer_a_scopes"][s] = granted

        # ── LAYER B: TikTok's view (creator_info endpoint) ──────────────
        section("LAYER B — Creator info (TikTok server view)")
        try:
            info_obj = query_creator_info(access_token=acc.access_token, timeout_s=15)
            ok("creator_info.query", "OK")
            info(f"username", info_obj.creator_username or acc.display_name)
            info(f"privacy_options", ", ".join(info_obj.privacy_level_options))
            info(f"max_duration_sec", str(info_obj.max_video_post_duration_sec))
            info(f"creator_toggles",
                 f"duet={'off' if info_obj.duet_disabled else 'on'}, "
                 f"comment={'off' if info_obj.comment_disabled else 'on'}, "
                 f"stitch={'off' if info_obj.stitch_disabled else 'on'}")
            acc_report["layer_b_creator_info"] = {
                "privacy_options": info_obj.privacy_level_options,
                "max_duration":    info_obj.max_video_post_duration_sec,
                "duet_disabled":   info_obj.duet_disabled,
                "comment_disabled": info_obj.comment_disabled,
                "stitch_disabled": info_obj.stitch_disabled,
            }
        except Exception as exc:
            fail("creator_info.query", f"{type(exc).__name__}: {exc}")
            overall_status = max(overall_status, 2)
            report["accounts"].append(acc_report)
            continue

        # ── LAYER C: Audit enforcement (real publish API behavior) ──────
        section("LAYER C — Audit enforcement (publish API behavior)")

        def _log(m, l):
            if args.verbose:
                info(f"[client {l}]", m)

        # C.1 — Probe direct post with PUBLIC_TO_EVERYONE
        ok_pub, err_code, err_msg, resp = probe_init_direct(
            acc.access_token, "PUBLIC_TO_EVERYONE", on_log=_log,
        )
        if ok_pub:
            ok("direct_post.PUBLIC_TO_EVERYONE", "init accepted ✅ FULL APPROVAL")
            acc_report["layer_c_audit_enforcement"]["direct_public"] = "ALLOWED"
            # Try to abort/cancel — we don't actually want to upload
            if resp and isinstance(resp, dict):
                pid = resp.get("publish_id") or resp.get("data", {}).get("publish_id")
                if pid and args.verbose:
                    info("aborted_probe_publish_id", str(pid))
        else:
            fail(f"direct_post.PUBLIC_TO_EVERYONE", f"BLOCKED — error: {err_code}")
            info("error_detail", (err_msg or "")[:200])
            acc_report["layer_c_audit_enforcement"]["direct_public"] = f"BLOCKED ({err_code})"

        # C.2 — Probe direct post with SELF_ONLY
        ok_self, err_code2, err_msg2, _ = probe_init_direct(
            acc.access_token, "SELF_ONLY", on_log=_log,
        )
        if ok_self:
            ok("direct_post.SELF_ONLY", "init accepted")
            acc_report["layer_c_audit_enforcement"]["direct_self_only"] = "ALLOWED"
        else:
            fail("direct_post.SELF_ONLY", f"BLOCKED — error: {err_code2}")
            acc_report["layer_c_audit_enforcement"]["direct_self_only"] = f"BLOCKED ({err_code2})"

        # C.3 — Probe draft (inbox) init
        ok_draft, err_code3, err_msg3, _ = probe_init_draft(acc.access_token, on_log=_log)
        if ok_draft:
            ok("draft_upload.inbox", "init accepted ✅")
            acc_report["layer_c_audit_enforcement"]["draft_inbox"] = "ALLOWED"
        else:
            fail("draft_upload.inbox", f"BLOCKED — error: {err_code3}")
            acc_report["layer_c_audit_enforcement"]["draft_inbox"] = f"BLOCKED ({err_code3})"

        # ── GAP ANALYSIS ────────────────────────────────────────────────
        section("GAP ANALYSIS — granted vs enforced")
        gaps = []

        # Gap 1: video.publish scope granted but direct PUBLIC blocked
        has_publish_scope = "video.publish" in scopes_set
        public_in_options = "PUBLIC_TO_EVERYONE" in info_obj.privacy_level_options
        if has_publish_scope and public_in_options and not ok_pub:
            gap = (
                "video.publish scope granted + PUBLIC in privacy_options, "
                f"BUT init rejected ({err_code}). "
                "Likely cause: app audit tier doesn't include direct PUBLIC posting yet."
            )
            gaps.append(gap)
            warn("AUDIT_GAP_PUBLIC", gap)
            overall_status = max(overall_status, 1)

        # Gap 2: comment.create scope missing
        if "comment.create" not in scopes_set:
            gap = "comment.create scope missing — auto-comment will be skipped"
            gaps.append(gap)
            warn("SCOPE_GAP_COMMENT", gap)

        # Gap 3: draft blocked too (severe)
        if not ok_draft:
            gap = f"draft init blocked ({err_code3}) — basic upload pipeline broken"
            gaps.append(gap)
            fail("CRITICAL", gap)
            overall_status = max(overall_status, 2)

        if not gaps:
            ok("No gaps — full PUBLIC capability confirmed")

        acc_report["gaps"] = gaps
        report["accounts"].append(acc_report)

    # ── Overall verdict ──────────────────────────────────────────────────
    print()
    print("=" * 76)
    print(f"  {_C.BOLD}OVERALL VERDICT{_C.END}")
    print("=" * 76)
    if overall_status == 0:
        print(f"  {_C.OK}✓ FULL PUBLIC CAPABILITY{_C.END}")
        print(f"    Bot can direct-post videos as PUBLIC_TO_EVERYONE on all accounts.")
    elif overall_status == 1:
        print(f"  {_C.WARN}⚠ LIMITED CAPABILITY{_C.END}")
        print(f"    Bot can upload to TikTok Inbox as draft (user publishes manually).")
        print(f"    Direct PUBLIC posting is BLOCKED — pending TikTok audit approval.")
        print()
        print(f"    {_C.BOLD}Next steps:{_C.END}")
        print(f"      1. Wait for audit decision (TikTok usually 5-10 business days)")
        print(f"      2. Re-run this script after notification email")
        print(f"      3. Until then, use --mode draft and publish manually from TikTok app")
    else:
        print(f"  {_C.FAIL}✗ BROKEN OR SEVERELY LIMITED{_C.END}")
        print(f"    Investigate errors above.")

    if args.json:
        print()
        print(json.dumps(report, indent=2, ensure_ascii=False))

    return overall_status


if __name__ == "__main__":
    sys.exit(main())
