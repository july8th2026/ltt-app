"""
TikTok Capability Check — verify app audit status + per-account permissions
─────────────────────────────────────────────────────────────────────────────
Queries TikTok's /v2/post/publish/creator_info/query/ for each connected account
to determine:
  - Granted scopes (user.info.basic, video.upload, video.publish)
  - Privacy levels available (SELF_ONLY only = Sandbox/unaudited;
    + PUBLIC_TO_EVERYONE = FULL APPROVAL)
  - Max video duration allowed
  - Creator-level toggles (duet, comment, stitch)

Usage:
    .venv\\Scripts\\python.exe scripts\\_check_tiktok_capabilities.py
    .venv\\Scripts\\python.exe scripts\\_check_tiktok_capabilities.py --account klcloset96

Prints one line per capability, pass/fail.

Exit codes:
    0 — at least one account is FULL APPROVAL (PUBLIC_TO_EVERYONE available)
    1 — no PUBLIC_TO_EVERYONE on any account (Sandbox)
    2 — config / token errors
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force UTF-8 on Windows cmd (cp1252 chokes on Unicode box-drawing)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="TikTok capability check")
    parser.add_argument("--account", default=None,
                        help="Filter to one account by display_name or open_id prefix")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # Load config + token store
    from core.tiktok.token_store import get_default_store
    from core.tiktok.creator_info import query_creator_info
    from core.tiktok.client import TikTokError

    store = get_default_store()
    accounts = store.all_accounts()
    if not accounts:
        print("[FATAL] No TikTok accounts connected.")
        print("        Run bot → tab 'TikTok Accounts' → Continue with TikTok.")
        return 2

    if args.account:
        filt = args.account.lower()
        accounts = [a for a in accounts
                    if filt in a.display_name.lower() or a.open_id.startswith(args.account)]
        if not accounts:
            print(f"[FATAL] No account matches '{args.account}'")
            return 2

    print("=" * 70)
    print("  TIKTOK CAPABILITY CHECK")
    print("=" * 70)

    any_public = False
    summary = []

    for i, acc in enumerate(accounts, 1):
        # Skip accounts with stale tokens
        if not acc.is_token_valid():
            print(f"\n[{i}] Account: @{acc.display_name}  (open_id={acc.open_id[:16]}...)")
            print(f"    ⚠  Access token expired — refresh via bot GUI first.")
            summary.append((acc.display_name, "TOKEN_EXPIRED", []))
            continue

        print(f"\n[{i}] Account: @{acc.display_name}  ({acc.open_id[:16]}...)")
        print(f"    Scopes granted on token: {','.join(acc.scopes)}")

        try:
            info = query_creator_info(
                access_token=acc.access_token,
                timeout_s=15,
                on_log=(lambda m, l: print(f"    · {m}")) if args.verbose else None,
            )
        except TikTokError as exc:
            print(f"    ❌ TikTok API error: {exc}")
            summary.append((acc.display_name, "API_ERROR", []))
            continue
        except Exception as exc:
            print(f"    ❌ Unexpected error: {type(exc).__name__}: {exc}")
            summary.append((acc.display_name, "ERROR", []))
            continue

        # Display privacy options
        opts = info.privacy_level_options
        has_public = "PUBLIC_TO_EVERYONE" in opts
        if has_public:
            any_public = True
            print(f"    Direct Post: ✅  APPROVED for PUBLIC_TO_EVERYONE")
        else:
            print(f"    Direct Post: ⚠  ONLY SELF_ONLY (Sandbox/unaudited)")

        print(f"    Privacy options available: {len(opts)}")
        for o in opts:
            marker = "[PUBLIC]" if o == "PUBLIC_TO_EVERYONE" else "[OK]    "
            print(f"      {marker} {o}")

        print(f"    Max video duration: {info.max_video_post_duration_sec}s")
        print(f"    Creator settings: "
              f"duet={'disabled' if info.duet_disabled else 'allowed'}, "
              f"comment={'disabled' if info.comment_disabled else 'allowed'}, "
              f"stitch={'disabled' if info.stitch_disabled else 'allowed'}")

        if args.verbose and (info.creator_nickname or info.creator_avatar_url):
            print(f"    Creator nickname: {info.creator_nickname}")
            print(f"    Avatar URL: {info.creator_avatar_url[:80]}")

        summary.append((acc.display_name, "PUBLIC" if has_public else "SELF_ONLY", opts))

    # Final verdict
    print("\n" + "=" * 70)
    if any_public:
        print("  STATUS: ✅ FULL APPROVAL — app moved to Production")
        print("  Ready for Direct Post PUBLIC_TO_EVERYONE.")
    else:
        print("  STATUS: ⚠  No PUBLIC_TO_EVERYONE on any account (Sandbox mode).")
        print("  Possible causes:")
        print("    - Client key/secret in config is Sandbox (not Production)")
        print("    - Account connected before audit Live — re-OAuth needed")
        print("    - App still in Sandbox tab on TikTok Developer Portal")
    print("=" * 70)

    return 0 if any_public else 1


if __name__ == "__main__":
    sys.exit(main())
