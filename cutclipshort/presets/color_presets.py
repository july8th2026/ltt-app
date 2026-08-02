"""Color grading presets.

Ported from NerfWarAI's bot_gui.py COLOR_PRESETS.
Each preset is a dict compatible with the FFmpeg filter chain builder.
"""

from __future__ import annotations

from typing import Any

# ── Color Preset Registry ────────────────────────────────────────────────

COLOR_PRESETS: dict[str, dict[str, Any]] = {
    "original": {
        "display_name": "Original (No Filter)",
        "film_enabled": False,
        "film_curves": "",
        "film_hue_deg": 0,
        "film_sat": 1.0,
        "eq_contrast": 1.0,
        "eq_saturation": 1.0,
        "eq_brightness": 0.0,
        "unsharp_luma": 0.0,
        "noise": 0,
    },
    "cinematic": {
        "display_name": "Cinematic (Teal/Gold)",
        "film_enabled": True,
        "film_curves": (
            "r='0/0 0.15/0.10 0.5/0.48 0.85/0.88 1/1':"
            "g='0/0 0.15/0.13 0.5/0.50 0.85/0.85 1/1':"
            "b='0/0.02 0.15/0.18 0.5/0.52 0.85/0.82 1/0.95'"
        ),
        "film_hue_deg": -8,
        "film_sat": 1.05,
        "eq_contrast": 1.05,
        "eq_saturation": 1.05,
        "eq_brightness": -0.02,
        "unsharp_luma": 0.15,
        "noise": 1,
    },
    "clear_fresh": {
        "display_name": "Clear / Fresh",
        "film_enabled": True,
        "film_curves": (
            "r='0/0 0.25/0.22 0.5/0.50 0.75/0.78 1/1':"
            "g='0/0 0.25/0.23 0.5/0.51 0.75/0.77 1/1':"
            "b='0/0 0.25/0.24 0.5/0.52 0.75/0.76 1/1'"
        ),
        "film_hue_deg": 0,
        "film_sat": 1.10,
        "eq_contrast": 1.03,
        "eq_saturation": 1.08,
        "eq_brightness": 0.02,
        "unsharp_luma": 0.20,
        "noise": 0,
    },
    "warm_vintage": {
        "display_name": "Warm Vintage",
        "film_enabled": True,
        "film_curves": (
            "r='0/0.02 0.15/0.14 0.5/0.52 0.85/0.90 1/1':"
            "g='0/0.01 0.15/0.12 0.5/0.48 0.85/0.84 1/0.96':"
            "b='0/0 0.15/0.10 0.5/0.44 0.85/0.78 1/0.90'"
        ),
        "film_hue_deg": 12,
        "film_sat": 0.95,
        "eq_contrast": 1.06,
        "eq_saturation": 0.95,
        "eq_brightness": 0.01,
        "unsharp_luma": 0.10,
        "noise": 2,
    },
    "cool_drama": {
        "display_name": "Cool Drama",
        "film_enabled": True,
        "film_curves": (
            "r='0/0 0.15/0.10 0.5/0.46 0.85/0.84 1/0.95':"
            "g='0/0 0.15/0.12 0.5/0.48 0.85/0.85 1/0.98':"
            "b='0/0.03 0.15/0.18 0.5/0.54 0.85/0.88 1/1'"
        ),
        "film_hue_deg": -15,
        "film_sat": 1.00,
        "eq_contrast": 1.08,
        "eq_saturation": 1.02,
        "eq_brightness": -0.03,
        "unsharp_luma": 0.12,
        "noise": 1,
    },
}


def get_color_preset(name: str) -> dict[str, Any]:
    """Get a color preset by name. Falls back to 'original' if not found."""
    return dict(COLOR_PRESETS.get(name, COLOR_PRESETS["original"]))


def list_color_presets() -> list[dict[str, str]]:
    """List all available presets with name and display_name."""
    return [
        {"name": name, "display_name": preset["display_name"]}
        for name, preset in COLOR_PRESETS.items()
    ]
