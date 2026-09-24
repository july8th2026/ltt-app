"""
Font checker — verify font availability before subtitle render.

Uses matplotlib.font_manager (if available) or falls back to
platform-specific registry checks (Windows registry, fc-list on Linux).

This prevents silent fallback to a default font that may not match
the user's intended style.
"""
from __future__ import annotations

import os
import platform
import subprocess
from functools import lru_cache
from typing import Optional

import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_system_fonts() -> set[str]:
    """
    Build a set of available font family names (lowercase) on this system.
    Cached for the lifetime of the process.
    """
    fonts: set[str] = set()

    # Method 1: matplotlib (most reliable cross-platform)
    try:
        from matplotlib.font_manager import fontManager
        for f in fontManager.ttflist:
            fonts.add(f.name.lower())
        if fonts:
            logger.debug("[font_checker] loaded %d fonts via matplotlib", len(fonts))
            return fonts
    except Exception:
        pass

    # Method 2: Windows — scan registry
    if platform.system() == "Windows":
        try:
            import winreg
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                i = 0
                while True:
                    try:
                        name, _, _ = winreg.EnumValue(key, i)
                        # Registry entry like "Arial (TrueType)" → extract font name
                        clean = name.split("(")[0].strip().lower()
                        fonts.add(clean)
                        i += 1
                    except OSError:
                        break
            if fonts:
                logger.debug("[font_checker] loaded %d fonts via Windows registry", len(fonts))
                return fonts
        except Exception:
            pass

    # Method 3: Linux/macOS — fc-list
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}\n"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                for name in line.split(","):
                    name = name.strip().lower()
                    if name:
                        fonts.add(name)
            if fonts:
                logger.debug("[font_checker] loaded %d fonts via fc-list", len(fonts))
                return fonts
    except Exception:
        pass

    # Method 4: Scan common font directories
    font_dirs = []
    if platform.system() == "Windows":
        font_dirs.append(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))
    elif platform.system() == "Darwin":
        font_dirs.extend(["/Library/Fonts", os.path.expanduser("~/Library/Fonts")])
    else:
        font_dirs.extend(["/usr/share/fonts", "/usr/local/share/fonts",
                          os.path.expanduser("~/.fonts")])

    for d in font_dirs:
        if os.path.isdir(d):
            for root, _, files in os.walk(d):
                # `ten_tep`, khong `f`: Method 1 o tren da dung `f` cho mot
                # `FontEntry` cua matplotlib, va hai nghia cho mot ten trong cung
                # mot ham la mot cho doc sai cho san. Do bang `mypy`
                # [assignment]/[call-overload] 24/09.
                for ten_tep in files:
                    if ten_tep.lower().endswith((".ttf", ".otf", ".ttc", ".woff", ".woff2")):
                        # Use filename (without extension) as rough font name
                        name = os.path.splitext(ten_tep)[0].lower()
                        # Strip common suffixes like -Regular, -Bold
                        for suffix in ("-regular", "-bold", "-italic", "-bolditalic",
                                       " regular", " bold", " italic"):
                            if name.endswith(suffix):
                                name = name[:-len(suffix)]
                        fonts.add(name)

    logger.debug("[font_checker] loaded %d fonts via directory scan", len(fonts))
    return fonts


def is_font_available(font_name: str) -> bool:
    """Check if a font family is available on this system."""
    system_fonts = _get_system_fonts()
    if not system_fonts:
        # Can't determine — assume available (don't block render)
        return True
    return font_name.lower() in system_fonts


def check_font_with_fallback(
    font_name: str,
    fallback_chain: str = "",
) -> dict:
    """
    Check font availability and find first available fallback if needed.

    Returns:
        {
            "requested": "Montserrat",
            "available": True/False,
            "resolved": "Montserrat" or first available fallback,
            "warning": None or warning message,
        }
    """
    result = {
        "requested": font_name,
        "available": is_font_available(font_name),
        "resolved": font_name,
        "warning": None,
    }

    if result["available"]:
        return result

    # Try fallbacks
    fallbacks = [f.strip() for f in fallback_chain.split(",") if f.strip()]
    for fb in fallbacks:
        if is_font_available(fb):
            result["resolved"] = fb
            result["warning"] = (
                f"Font '{font_name}' không có trên hệ thống. "
                f"Sẽ dùng '{fb}' thay thế."
            )
            logger.warning(
                "[font_checker] '%s' not found, falling back to '%s'",
                font_name, fb,
            )
            return result

    # No fallback found either
    result["resolved"] = "Arial"  # Ultimate fallback
    result["warning"] = (
        f"Font '{font_name}' và các fallback ({fallback_chain}) "
        f"không có trên hệ thống. Sẽ dùng 'Arial'."
    )
    logger.warning(
        "[font_checker] '%s' and all fallbacks not found, using Arial",
        font_name,
    )
    return result


@lru_cache(maxsize=64)
def _cmap_of(font_name: str) -> Optional[frozenset[int]]:
    """Code points the INSTALLED font `font_name` maps, or None if unresolved.

    Availability (`is_font_available`) answers "is there a font with this
    name"; it does not answer "can it draw these characters". Arial exists on
    every Windows machine and has no Han glyph.
    """
    try:
        from fontTools.ttLib import TTFont
        from matplotlib.font_manager import FontProperties, findfont
    except Exception:
        return None
    try:
        path = findfont(FontProperties(family=font_name), fallback_to_default=False)
    except Exception:
        return None
    try:
        kw = {"fontNumber": 0} if str(path).lower().endswith((".ttc", ".otc")) else {}
        with TTFont(path, lazy=True, **kw) as f:
            cmap = f.getBestCmap() or {}
        return frozenset(cmap)
    except Exception:
        return None


def missing_glyphs(font_name: str, text: str) -> Optional[str]:
    """Characters of `text` the installed font `font_name` has no glyph for.

    Returns "" when every visible character is covered, the missing characters
    (deduplicated, in order) otherwise, or None when the font cannot be
    resolved/read on this machine (unknown is not the same as "covered").
    Whitespace and ASS line breaks are ignored.
    """
    cmap = _cmap_of(str(font_name or "").strip())
    if cmap is None:
        return None
    seen: list[str] = []
    for ch in str(text or "").replace("\\N", " "):
        if ch.isspace() or ord(ch) in cmap or ch in seen:
            continue
        seen.append(ch)
    return "".join(seen)


def list_available_fonts() -> list[str]:
    """Return sorted list of all available font family names."""
    return sorted(_get_system_fonts())
