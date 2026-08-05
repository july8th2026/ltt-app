"""Validation và prompt contract cho Image Studio generate/edit."""
from __future__ import annotations

from platform_core.image_input import validate_reference

EDIT_MODES = ("generate", "edit", "semantic_inpaint", "outpaint", "style_transfer")


def clean_mode(value: str) -> str:
    value = (value or "generate").strip()
    return value if value in EDIT_MODES else "generate"


def edit_directive(mode: str, prompt: str, refs: list[dict]) -> str:
    """Dựng chỉ dẫn rõ vai trò ảnh; không giả vờ hỗ trợ precision mask."""
    mode = clean_mode(mode)
    labels = ", ".join(str(r.get("role") or "reference") for r in refs)
    prefix = {
        "generate": "Create a new image from the request.",
        "edit": "Edit the SOURCE image. Preserve all areas the request does not change.",
        "semantic_inpaint": ("Semantically replace or repair only the area described in "
                              "the request; preserve the rest of the SOURCE image."),
        "outpaint": ("Extend the SOURCE image naturally to the requested aspect ratio; "
                     "keep the original image as the central composition."),
        "style_transfer": ("Preserve the content and structure of the SOURCE image while "
                           "applying the visual language of the STYLE image."),
    }[mode]
    context = f" Input image roles in order: {labels}." if labels else ""
    return f"{prefix}{context}\nUser request: {prompt.strip()}"


__all__ = ["EDIT_MODES", "clean_mode", "edit_directive", "validate_reference"]
