"""
Demo v2 — Intro/outro slide generator

Creates 1920×1080 PNG slides for video intro + outro using PIL/Pillow.

Usage:
    .venv\\Scripts\\python.exe tools\\demo_v2\\02_generate_slides.py

Output:
    tools/demo_v2/output/slides/01_intro.png
    tools/demo_v2/output/slides/09_outro.png
"""
from __future__ import annotations

import sys
from pathlib import Path

# Force UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent / "output" / "slides"

# Brand colors
BG_DARK    = (13, 17, 22)        # GitHub dark bg
TT_PINK    = (254, 44, 85)       # TikTok pink-red
TT_CYAN    = (37, 244, 238)      # TikTok cyan
TEXT       = (240, 240, 240)
SUBTLE     = (160, 160, 160)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load Segoe UI from Windows fonts, fallback to default."""
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf"  if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, y: int,
                   font: ImageFont.FreeTypeFont, color, width: int = 1920):
    """Draw text horizontally centered at given y."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (width - text_w) // 2
    draw.text((x, y), text, fill=color, font=font)


def make_intro_slide(out: Path):
    """1920×1080 intro slide."""
    img = Image.new("RGB", (1920, 1080), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Top-left accent bar
    draw.rectangle([(0, 0), (12, 1080)], fill=TT_PINK)

    # TikTok-style gradient accent (simulated with 2 colored circles, low opacity)
    accent_layer = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    accent_draw = ImageDraw.Draw(accent_layer)
    accent_draw.ellipse([(1500, -100), (2100, 500)], fill=(*TT_PINK, 30))
    accent_draw.ellipse([(1400, 300), (2000, 900)], fill=(*TT_CYAN, 25))
    img.paste(accent_layer.convert("RGB"), mask=accent_layer)

    # Title
    font_title = _load_font(80, bold=True)
    _draw_centered(draw, "LTTStudio VideoBot", 380, font_title, TEXT)

    # Subtitle line 1
    font_sub = _load_font(38)
    _draw_centered(draw, "TikTok Content Posting API Integration", 490, font_sub, TT_PINK)

    # Subtitle line 2
    font_caption = _load_font(28)
    _draw_centered(draw, "Demo for App Audit Review", 580, font_caption, SUBTLE)
    _draw_centered(draw, "Direct Post — User Confirmation Flow", 625, font_caption, SUBTLE)

    # Footer
    font_footer = _load_font(22)
    _draw_centered(draw, "https://lttstudios.com", 980, font_footer, SUBTLE)
    _draw_centered(draw, f"Submission: May 2026", 1015, font_footer, SUBTLE)

    img.save(out, "PNG", optimize=True)
    print(f"  -> {out.name}  ({out.stat().st_size // 1024} KB)")


def make_outro_slide(out: Path):
    """1920×1080 outro slide."""
    img = Image.new("RGB", (1920, 1080), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Right-side accent bar
    draw.rectangle([(1908, 0), (1920, 1080)], fill=TT_CYAN)

    # Background gradient
    accent_layer = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    accent_draw = ImageDraw.Draw(accent_layer)
    accent_draw.ellipse([(-200, 600), (400, 1200)], fill=(*TT_CYAN, 25))
    accent_draw.ellipse([(-100, 700), (500, 1300)], fill=(*TT_PINK, 25))
    img.paste(accent_layer.convert("RGB"), mask=accent_layer)

    # Big "Thank you"
    font_title = _load_font(90, bold=True)
    _draw_centered(draw, "Thank you for reviewing", 360, font_title, TEXT)

    # Brand line
    font_sub = _load_font(48)
    _draw_centered(draw, "LTTStudio VideoBot", 500, font_sub, TT_PINK)

    # Contact info
    font_caption = _load_font(28)
    _draw_centered(draw, "Website: https://lttstudios.com", 640, font_caption, SUBTLE)
    _draw_centered(draw, "Privacy: https://lttstudios.com/legal/privacy.html", 685, font_caption, SUBTLE)
    _draw_centered(draw, "Terms: https://lttstudios.com/legal/terms.html", 730, font_caption, SUBTLE)
    _draw_centered(draw, "Support: support@lttstudios.com", 775, font_caption, SUBTLE)

    img.save(out, "PNG", optimize=True)
    print(f"  -> {out.name}  ({out.stat().st_size // 1024} KB)")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating slides in {OUT_DIR}")
    # Slide names match scene IDs in scene_config.py
    make_intro_slide(OUT_DIR / "01_intro.png")
    make_outro_slide(OUT_DIR / "13_outro.png")
    # Remove old 09_outro.png if it exists from previous run
    old = OUT_DIR / "09_outro.png"
    if old.exists():
        old.unlink()
    print("Done.")


if __name__ == "__main__":
    main()
