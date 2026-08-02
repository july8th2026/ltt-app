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
                for f in files:
                    if f.lower().endswith((".ttf", ".otf", ".ttc", ".woff", ".woff2")):
                        # Use filename (without extension) as rough font name
                        name = os.path.splitext(f)[0].lower()
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


def list_available_fonts() -> list[str]:
    """Return sorted list of all available font family names."""
    return sorted(_get_system_fonts())
