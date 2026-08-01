"""
refs.py — dựng phần tham chiếu (ảnh/video/audio) cho body ModelArk (seedance Pha 2).

Di trú trung thành từ `adapters/modelark_adapter.py` (build_content/_ref_to_part/
_provider_url/_image_role/normalize_tags):
- ảnh ≤ 8 MiB → INLINE `data:` base64 (chuẩn hoá về PNG/JPEG bằng Pillow);
- ảnh > 8 MiB / video / audio → BẮT BUỘC `asset://` (hoặc URL công khai) — không inline;
- role hợp lệ + remap legacy; @handle → tag vị trí @IMG_n/@VID_n/@AUD_n.

Ref (dict) worker nhận: {kind, url|data, role, handle}. `url` có thể là data:/http:/asset://.
"""
from __future__ import annotations

import base64
import re

MAX_INLINE_BYTES = 8 * 1024 * 1024

VALID_IMAGE_ROLES = {"reference_image", "first_frame", "last_frame", "mask"}
_ROLE_REMAP = {"reference": "reference_image", "character": "reference_image",
               "start_frame": "first_frame", "end_frame": "last_frame"}
_TAG_PREFIX = {"image": "IMG", "video": "VID", "audio": "AUD"}


class RefError(RuntimeError):
    pass


def image_role(role: str) -> str:
    r = (role or "").strip() or "reference_image"
    r = _ROLE_REMAP.get(r, r)
    return r if r in VALID_IMAGE_ROLES else "reference_image"


def normalize_image(data: bytes) -> tuple[bytes, str]:
    """Trả (bytes, mime). Giữ nguyên nếu đã JPEG/PNG; còn lại convert PNG (Pillow)."""
    if data[:3] == b"\xff\xd8\xff":
        return data, "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data, "image/png"
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA" if "A" in im.mode else "RGB")
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue(), "image/png"


def image_to_inline(data: bytes) -> str:
    """bytes ảnh → data URL. Ném RefError nếu sau chuẩn hoá vẫn > 8 MiB (cần asset://)."""
    norm, mime = normalize_image(data)
    if len(norm) > MAX_INLINE_BYTES:
        raise RefError("anh > 8MiB — can asset:// / URL cong khai")
    b64 = base64.b64encode(norm).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _ref_to_part(ref: dict) -> dict | None:
    kind = (ref.get("kind") or "image").strip()
    url = (ref.get("url") or "").strip()
    if not url:
        return None
    if kind == "image":
        return {"type": "image_url", "image_url": {"url": url},
                "role": image_role(ref.get("role") or "")}
    if kind == "video":
        return {"type": "video_url", "video_url": {"url": url}, "role": "reference_video"}
    if kind == "audio":
        return {"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"}
    return None


def normalize_tags(prompt: str, refs: list) -> str:
    """@handle (vd @swat) → tag vị trí @IMG_n/@VID_n/@AUD_n theo thứ tự ref mỗi loại."""
    counts = {"image": 0, "video": 0, "audio": 0}
    handle_to_tag = {}
    for r in refs:
        kind = (r.get("kind") or "image").strip()
        if kind not in counts:
            continue
        counts[kind] += 1
        h = (r.get("handle") or "").strip().lstrip("@").lower()
        if h:
            handle_to_tag[h] = f"@{_TAG_PREFIX[kind]}_{counts[kind]}"
    if not handle_to_tag:
        return prompt

    def _sub(m):
        return handle_to_tag.get(m.group(1).lower(), m.group(0))
    return re.sub(r"@(\w+)", _sub, prompt)


def build_content(prompt: str, refs: list) -> list:
    """content[] = [text] + các *_url part. @tag đã chuẩn hoá vào text."""
    content = [{"type": "text", "text": normalize_tags(prompt, refs)}]
    for ref in (refs or []):
        part = _ref_to_part(ref)
        if part is not None:
            content.append(part)
    return content
