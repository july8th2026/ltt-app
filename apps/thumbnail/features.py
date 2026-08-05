"""Feature helpers for Thumbnail: brand normalization, references and real scores."""
from __future__ import annotations

import io
import re

# Kiem anh tai len la kiem AN TOAN dung chung, khong phai nghiep vu rieng cua
# app nay — no o `platform_core/image_input.py`. Tai xuat de code va test cu
# import tu day van chay, nhung ban goc chi con MOT cho.
from platform_core.image_input import (  # noqa: F401
    ALLOWED_REFERENCE_MIME, MAX_REFERENCE_BYTES, MAX_REFERENCE_PIXELS,
    validate_reference)
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def clean_brand(data: dict | None) -> dict:
    raw = data or {}
    primary = str(raw.get("primary_color") or "#E53935").strip()
    secondary = str(raw.get("secondary_color") or "#111111").strip()
    return {
        "name": str(raw.get("name") or "").strip()[:80],
        "primary_color": primary.upper() if _HEX.fullmatch(primary) else "#E53935",
        "secondary_color": secondary.upper() if _HEX.fullmatch(secondary) else "#111111",
        "font": str(raw.get("font") or "").strip()[:80],
        "tone": str(raw.get("tone") or "").strip()[:160],
    }


def brand_directive(brand: dict | None) -> str:
    item = clean_brand(brand)
    if not any((item["name"], item["font"], item["tone"])):
        return ""
    return ("Brand consistency: "
            f"brand={item['name'] or 'unnamed'}; primary={item['primary_color']}; "
            f"secondary={item['secondary_color']}; font={item['font'] or 'unspecified'}; "
            f"tone={item['tone'] or 'unspecified'}.")


def technical_score(data: bytes) -> dict:
    """Transparent zero-provider technical score; never claims semantic/CTR quality."""
    from PIL import Image, ImageFilter, ImageStat
    with Image.open(io.BytesIO(data)) as image:
        rgb = image.convert("RGB")
        gray = rgb.convert("L")
        width, height = rgb.size
        contrast = min(100.0, ImageStat.Stat(gray).stddev[0] / 64.0 * 100.0)
        entropy = min(100.0, gray.entropy() / 8.0 * 100.0)
        edge = gray.filter(ImageFilter.FIND_EDGES)
        sharpness = min(100.0, ImageStat.Stat(edge).mean[0] / 32.0 * 100.0)
        exposure = max(0.0, 100.0 - abs(ImageStat.Stat(gray).mean[0] - 127.5) / 1.275)
        score = round(.30 * contrast + .25 * entropy + .25 * sharpness + .20 * exposure)
        return {"score": max(0, min(100, score)), "width": width, "height": height,
                "contrast": round(contrast), "detail": round(sharpness),
                "exposure": round(exposure), "method": "technical-v1"}
