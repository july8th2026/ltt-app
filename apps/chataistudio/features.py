"""Attachment/search/export helpers for Chat AI Studio."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

MAX_FILES = 3
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_CONTEXT_CHARS = 12_000
TEXT_MIMES = {"text/plain", "text/markdown", "text/csv", "application/json"}
IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}


def parse_attachment(data: bytes, mime: str, filename: str) -> dict:
    if not data or len(data) > MAX_FILE_BYTES:
        raise ValueError("Tệp đính kèm rỗng hoặc vượt giới hạn 8 MB.")
    mime = (mime or "").lower().split(";", 1)[0]
    name = Path(filename or "tep").name[:160]
    if mime in IMAGE_MIMES:
        from apps.thumbnail.features import validate_reference
        validate_reference(data, mime)
        from PIL import Image
        source = Image.open(io.BytesIO(data))
        source = source.convert("RGBA" if "A" in source.getbands() else "RGB")
        normalized = io.BytesIO(); source.save(normalized, "PNG"); data = normalized.getvalue()
        return {"kind": "image", "name": name, "mime": "image/png", "data": data,
                "data_url": f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"}
    if mime in TEXT_MIMES:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Tệp văn bản phải dùng UTF-8.") from exc
    elif mime == "application/pdf":
        try:
            from pypdf import PdfReader
            text = "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Không đọc được nội dung PDF.") from exc
    else:
        raise ValueError("Chỉ nhận PNG/JPEG/WebP, TXT/MD/CSV/JSON hoặc PDF.")
    text = text.strip()
    if not text:
        raise ValueError("Tệp không có nội dung văn bản có thể đọc.")
    return {"kind": "text", "name": name, "mime": mime,
            "text": text[:MAX_CONTEXT_CHARS]}


def context_message(message: str, attachments: list[dict]) -> str:
    blocks = [message.strip()]
    for item in attachments:
        if item["kind"] == "text":
            blocks.append(f"[Tệp {item['name']}]\n{item['text']}")
    return "\n\n".join(blocks)


def export_markdown(title: str, messages: list) -> str:
    rows = [f"# {title or 'Hội thoại'}", ""]
    for msg in messages:
        rows += [f"## {'Bạn' if msg.role == 'user' else 'AI'}", ""]
        if msg.image_key:
            rows.append(f"[Ảnh: {msg.image_prompt or msg.image_key}]")
        else:
            rows.append(msg.content)
        rows.append("")
    return "\n".join(rows)


def export_json(title: str, model: str, messages: list) -> bytes:
    payload = {"version": 1, "title": title, "model": model, "messages": [
        {"role": m.role, "content": m.content, "image_key": m.image_key,
         "image_prompt": m.image_prompt} for m in messages]}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
