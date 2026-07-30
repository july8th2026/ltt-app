"""
LTTStudio VideoBot — Single source of truth for version metadata.

F6-02 fix: previously version was hardcoded in main_window.py status bar
("v1.0") AND about_dialog.py (APP_VERSION = "1.0.0"). Drift between the two
was a real risk. All version references now read from here.
"""

APP_NAME    = "LTTStudios VideoBot"
APP_VERSION = "1.0.0"
APP_BUILD   = "2025-01"
APP_AUTHOR  = "LTTStudios"
APP_URL     = "https://lttstudios.com"

# Display version (short, for status bars)
APP_VERSION_SHORT = "v" + ".".join(APP_VERSION.split(".")[:2])  # "v1.0"


def get_version_string() -> str:
    """Return full version display string for About / logs."""
    return f"{APP_NAME} {APP_VERSION_SHORT} · Build {APP_BUILD}"
