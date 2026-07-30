"""
accounts.py — read-only account/page views for the web dashboard (P4/P5).

Hard rule: this module converts token-store objects into plain view
dataclasses that carry **no token material**. Routes and templates only
ever see what is defined here, so a template change can never accidentally
render an access token into HTML.

The `unreadable` state is first-class rather than an empty list, because
the 2026-07-30 audit found a real 27KB token file being displayed as "no
accounts connected" (docs/_luutru/AUDIT_REPORT.md B1/D2).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PageView:
    page_id:   str
    name:      str
    category:  str = ""
    selected:  bool = True


@dataclass(frozen=True)
class AccountView:
    account_id:     str
    name:           str
    platform:       str
    token_valid:    bool
    status_label:   str
    days_to_expiry: int = -1
    is_system_user: bool = False
    pages:          list = field(default_factory=list)   # list[PageView]


@dataclass(frozen=True)
class AccountListing:
    platform:   str
    accounts:   list = field(default_factory=list)       # list[AccountView]
    unreadable: str = ""     # non-empty => store exists but cannot be read

    @property
    def is_unreadable(self) -> bool:
        return bool(self.unreadable)

    @property
    def total_pages(self) -> int:
        return sum(len(a.pages) for a in self.accounts)


def list_facebook_accounts(store=None) -> AccountListing:
    """Facebook accounts + their selected pages, stripped of tokens."""
    if store is None:
        from core.token_store import get_default_store
        store = get_default_store()

    if getattr(store, "is_unreadable", False):
        return AccountListing(platform="facebook", unreadable=store.load_error or "")

    accounts = []
    for acc in store.all_accounts():
        label, _colour = acc.token_status_label()
        accounts.append(AccountView(
            account_id     = acc.fb_user_id,
            name           = acc.name,
            platform       = "facebook",
            token_valid    = acc.is_token_valid(),
            status_label   = label,
            days_to_expiry = acc.days_until_expiry(),
            is_system_user = acc.is_system_user,
            pages          = [
                PageView(page_id=p.id, name=p.name, category=p.category,
                         selected=p.selected)
                for p in acc.get_pages_list()
            ],
        ))
    return AccountListing(platform="facebook", accounts=accounts)


def list_tiktok_accounts(store=None) -> AccountListing:
    """TikTok accounts, stripped of tokens. TikTok has no page concept."""
    if store is None:
        from core.tiktok.token_store import get_default_store
        store = get_default_store()

    if getattr(store, "is_unreadable", False):
        return AccountListing(platform="tiktok", unreadable=store.load_error or "")

    accounts = []
    for acc in store.all_accounts():
        label, _colour = acc.token_status_label()
        accounts.append(AccountView(
            account_id     = acc.open_id,
            name           = acc.display_name or acc.open_id,
            platform       = "tiktok",
            token_valid    = acc.is_token_valid(),
            status_label   = label,
            days_to_expiry = acc.days_until_expiry(),
        ))
    return AccountListing(platform="tiktok", accounts=accounts)
