"""
Internationalization (i18n) for LTTStudio VideoBot.

Hai ngôn ngữ supported:
  - English (en) — DEFAULT
  - Vietnamese (vi)

User switch trong tab Settings → Language. Lưa chọn save vào config.json
(`app_language`). Default English để TT reviewer / international users hiểu
ngay; Vietnamese qua 1 click cho người dùng Việt.

Usage:
    from core.i18n import t, set_language, init

    # In main_window startup:
    init(settings_tab.get_config())

    # In any widget:
    btn = ctk.CTkButton(parent, text=t("btn.continue_with_tiktok"))

    # When user changes language:
    set_language("vi")
    # → All registered observers fire to rebuild UI

Translation files: data/translations/{en,vi}.json
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger(__name__)

# ─── Module state ─────────────────────────────────────────────────────────────

_current_lang: str = "en"
_translations: dict[str, dict[str, str]] = {}
_observers: list[Callable[[str], None]] = []
_initialized: bool = False


# ─── Public API ───────────────────────────────────────────────────────────────

def init(config: Optional[dict] = None) -> None:
    """Initialize i18n once at app startup.

    Loads JSON translation files + sets current language from config.
    Safe to call multiple times (idempotent).
    """
    global _initialized
    _load_translations()
    if config and isinstance(config, dict):
        lang = str(config.get("app_language", "en"))
        set_language(lang, notify=False)
    _initialized = True


def t(key: str, default: Optional[str] = None, **fmt) -> str:
    """Translate key into current language.

    Fallback chain: current_lang → English → explicit default → key itself.
    Supports format placeholders: ``t("hello", name="World")``.

    Parameters
    ----------
    key
        Translation key (dot-separated, e.g. "tab.tiktok_audit").
    default
        Fallback if key missing in both current and English.
    **fmt
        Keyword arguments for str.format() substitution.

    Examples
    --------
    >>> t("btn.cancel")
    'Cancel'   # if lang == "en"
    >>> set_language("vi")
    >>> t("btn.cancel")
    'Hủy'
    """
    val = _translations.get(_current_lang, {}).get(key)
    if val is None:
        # Fallback to English
        val = _translations.get("en", {}).get(key)
    if val is None:
        val = default if default is not None else key

    if fmt:
        try:
            return val.format(**fmt)
        except (KeyError, IndexError, ValueError) as exc:
            log.debug("i18n format failed for %s: %s", key, exc)
    return val


def set_language(lang: str, *, notify: bool = True) -> None:
    """Change current language. Fire observers when notify=True (default).

    Recognised values: "en", "vi". Unknown → fallback "en".
    """
    global _current_lang
    lang = (lang or "en").strip().lower()
    if lang not in ("en", "vi"):
        log.warning("Unknown language %r — falling back to 'en'", lang)
        lang = "en"
    if lang == _current_lang and _initialized:
        return
    _current_lang = lang
    if notify:
        for obs in list(_observers):
            try:
                obs(lang)
            except Exception as exc:
                log.debug("i18n observer failed: %s", exc)


def get_language() -> str:
    """Return current language code: 'en' or 'vi'."""
    return _current_lang


def add_observer(fn: Callable[[str], None]) -> None:
    """Register callback fired when language changes.

    fn signature: fn(new_lang: str) -> None
    Useful for live UI rebuild without restart.
    """
    if fn not in _observers:
        _observers.append(fn)


def remove_observer(fn: Callable[[str], None]) -> None:
    """Unregister observer (e.g. on widget destroy)."""
    if fn in _observers:
        _observers.remove(fn)


def available_languages() -> list[tuple[str, str]]:
    """Return list of (code, display_name) for the language switcher UI."""
    return [
        ("en", "🇬🇧  English"),
        ("vi", "🇻🇳  Tiếng Việt"),
    ]


# ─── Internal ─────────────────────────────────────────────────────────────────

def _load_translations() -> None:
    """Load JSON translation files from data/translations/.

    Silent fail if a language file is missing (uses {} for that lang); the
    fallback chain in t() ensures keys still resolve to English or the key
    itself.
    """
    global _translations
    base = Path(__file__).resolve().parent.parent / "data" / "translations"
    for lang in ("en", "vi"):
        f = base / f"{lang}.json"
        try:
            with f.open(encoding="utf-8") as fp:
                _translations[lang] = json.load(fp)
            log.debug("i18n: loaded %d keys for '%s'", len(_translations[lang]), lang)
        except FileNotFoundError:
            log.warning("i18n: translation file not found — %s", f)
            _translations[lang] = {}
        except json.JSONDecodeError as exc:
            log.error("i18n: invalid JSON in %s — %s", f, exc)
            _translations[lang] = {}
