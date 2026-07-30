"""
Generate opening + closing slide PNG (1920x1080) cho demo recording.
Chạy 1 lần: python scripts/demo_assets/_gen_slides.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.dirname(__file__)
W, H = 1920, 1080

# Tìm font Windows
def _load(name: str, size: int):
    for path in [
        rf"C:\Windows\Fonts\{name}.ttf",
        rf"C:\Windows\Fonts\{name}bd.ttf",
        rf"C:\Windows\Fonts\consola.ttf",
        rf"C:\Windows\Fonts\Arial.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _center_text(draw, text, y, font, color="#E6EAF2"):
    """Draw centered text at vertical y."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, y), text, font=font, fill=color)


def make_opening():
    img = Image.new("RGB", (W, H), "#0d1117")
    d = ImageDraw.Draw(img)
    # Accent bar trên
    d.rectangle([(0, 0), (W, 8)], fill="#9C27B0")
    # Logo + brand
    _center_text(d, "🎬",  340, _load("seguiemj", 96), "#4A90D9")
    _center_text(d, "LTTStudio VideoBot",        470, _load("consola", 72), "#E6EAF2")
    _center_text(d, "TikTok Content Posting API Integration",  570, _load("consola", 32), "#9C27B0")
    # Subtitle
    _center_text(d, "Demo for App Audit Review",  680, _load("consola", 28), "#A0AEC0")
    _center_text(d, "May 2026",                   730, _load("consola", 22), "#6B7280")
    # Footer
    _center_text(d, "Built on TikTok Content Posting API v2 + Login Kit",
                 980, _load("consola", 18), "#4a5568")
    img.save(os.path.join(OUT_DIR, "opening_slide.png"), optimize=True)
    print(f"✅ opening_slide.png")


def make_closing():
    img = Image.new("RGB", (W, H), "#0d1117")
    d = ImageDraw.Draw(img)
    # Accent bar dưới
    d.rectangle([(0, H - 8), (W, H)], fill="#9C27B0")
    # Body
    _center_text(d, "Thank you for reviewing",  380, _load("consola", 56), "#E6EAF2")
    _center_text(d, "",                          440, _load("consola", 16))
    _center_text(d, "LTTStudio VideoBot",        540, _load("consola", 48), "#9C27B0")
    _center_text(d, "https://lttstudios.com",     640, _load("consola", 28), "#4A90D9")
    _center_text(d, "Support: support@lttstudios.com",
                 720, _load("consola", 22), "#A0AEC0")
    img.save(os.path.join(OUT_DIR, "closing_slide.png"), optimize=True)
    print(f"✅ closing_slide.png")


if __name__ == "__main__":
    make_opening()
    make_closing()
    print(f"\nĐã lưu tại: {OUT_DIR}")
