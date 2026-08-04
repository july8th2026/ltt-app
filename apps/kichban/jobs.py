"""
Handler job app `script` (di trú A1). Sinh kịch bản YouTube có cấu trúc qua Gemini.

Đầu ra là VĂN BẢN/JSON (title/hook/sections/outro/description/tags) — khác app ảnh.
Prompt ghép từ fragment (`platform_core.prompt_fragments`), gọi Gemini text (category
chat), parse JSON. Key qua APIKEYS (H8), fallback env.

Hợp đồng: idempotent ở mức job (credit quyết toán một lần) · báo tiến độ · NÉM khi lỗi.
"""
from __future__ import annotations

import base64
import io
import json
import os
import pathlib
import time

_MODEL = "gemini-2.5-flash"
_BASE = "https://generativelanguage.googleapis.com"
_TIMEOUT_S = 110
_PROMPTS_DIR = pathlib.Path(__file__).resolve().parent / "prompts"
_SYSTEM = "You are a professional YouTube scriptwriter. Always return valid JSON only."


class GeminiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _sanitize(msg: str, key: str) -> str:
    if key and len(key) > 8:
        msg = msg.replace(key, "***")
    return msg[:400]


def build_prompt(topic: str, *, duration: str = "", tone: str = "",
                 audience: str = "", language: str = "") -> str:
    """Ghép prompt kịch bản TỪ FRAGMENT (trung thành youtube_script_service._build_prompt)."""
    from platform_core import prompt_fragments as pf
    d = _PROMPTS_DIR
    duration = duration or pf.default_option(d, "do_dai_video")
    tone = tone or pf.default_option(d, "giong_van")
    audience = audience or pf.default_option(d, "doi_tuong")
    language = language or pf.default_option(d, "ngon_ngu")
    lbl = lambda g, i: pf.load_labels(d, g).get(i, i)  # noqa: E731
    mapping = {
        "topic": topic.strip(),
        "lang_directive": pf.read_fragment(d, "ngon_ngu", language),
        "do_dai_label": lbl("do_dai_video", duration),
        "doi_tuong_label": lbl("doi_tuong", audience),
        "giong_van_label": lbl("giong_van", tone),
        "giong_van_directive": pf.read_fragment(d, "giong_van", tone),
        "doi_tuong_directive": pf.read_fragment(d, "doi_tuong", audience),
    }
    return pf.build(d, mapping)


def _lay_key(model: str = _MODEL) -> tuple[str, str | None]:
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        from platform_core.models import APIKEY_CAT_CHAT
        gen = get_session(); db = next(gen)
        try:
            key = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_CHAT, model=model)
            cred = api_keys.lay_credential(db, key)
            db.commit()
            return cred, key.id
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return (os.environ.get("GEMINI_API_KEY") or "").strip(), None


def _ket_qua_key(key_id: str | None, *, thanh_cong: bool,
                 last_status: int | None = None) -> None:
    if not key_id:
        return
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        gen = get_session(); db = next(gen)
        try:
            key = api_keys.lay_key_theo_id(db, key_id)
            if key is None:
                return
            if thanh_cong:
                api_pool.danh_dau_thanh_cong(db, key)
            elif last_status is not None:
                api_pool.danh_dau_loi(db, key, http_status=last_status)
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        pass


def _goi_gemini_text(prompt: str, api_key: str, model: str = _MODEL,
                     system: str = _SYSTEM,
                     image_parts: list[dict] | None = None) -> str:
    """Gọi Gemini text/vision (generateContent) và trả chuỗi văn bản."""
    import httpx
    from platform_core.providers import resolve_model_id
    url = f"{_BASE}/v1beta/models/{resolve_model_id(model)}:generateContent"
    headers = {"x-goog-api-key": api_key}
    parts = [{"text": prompt}, *(image_parts or [])]
    body = {
        "contents": [{"parts": parts}],
        "systemInstruction": {"parts": [{"text": system}]},
    }
    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=_TIMEOUT_S)
    except httpx.HTTPError as e:
        raise GeminiError(_sanitize(f"Lỗi kết nối Gemini: {e}", api_key), status_code=None)
    if resp.status_code != 200:
        # KHONG lo nguyen van body/loi provider ra UI nguoi dung. Chi tiet -> log.
        import logging
        logging.getLogger(__name__).warning(
            "kichban Gemini HTTP %s: %s", resp.status_code,
            _sanitize(resp.text, api_key))
        raise GeminiError(
            f"Dịch vụ AI tạm lỗi (mã {resp.status_code}). Vui lòng thử lại sau.",
            status_code=resp.status_code)
    data = resp.json()
    for part in (data.get("candidates") or [{}])[0].get("content", {}).get("parts", []) or []:
        if part.get("text"):
            return part["text"]
    raise RuntimeError("Gemini không trả văn bản.")


def _owned_image_keys(params: dict, owner_id: str) -> list[str]:
    """Chuẩn hoá một/nhiều ảnh và chặn đọc asset của tài khoản khác."""
    raw = []
    if params.get("image_key"):
        raw.append(params["image_key"])
    raw.extend(list(params.get("image_keys") or []))
    keys: list[str] = []
    for value in raw:
        key = str(value or "").replace("\\", "/").strip("/")
        parts = key.split("/")
        if not owner_id or len(parts) < 3 or parts[1] != owner_id:
            raise ValueError("Ảnh đầu vào không thuộc tài khoản đang chạy workflow.")
        if key not in keys:
            keys.append(key)
    if len(keys) > 8:
        raise ValueError("Một node Text chỉ nhận tối đa 8 ảnh.")
    return keys


def _owned_key(value: object, owner_id: str, label: str) -> str:
    key = str(value or "").replace("\\", "/").strip("/")
    parts = key.split("/")
    if not owner_id or len(parts) < 3 or parts[1] != owner_id:
        raise ValueError(f"{label} đầu vào không thuộc tài khoản đang chạy workflow.")
    return key


def _context_text_parts(params: dict) -> list[dict]:
    source_text = str(params.get("source_text") or "").strip()
    if not source_text:
        return []
    if len(source_text) > 32000:
        raise ValueError("Văn bản tham chiếu vượt giới hạn 32.000 ký tự.")
    return [{"text": "Connected text context:\n" + source_text}]


def _load_image_parts(params: dict, owner_id: str) -> list[dict]:
    """Đọc ảnh đã sở hữu, xác minh bytes thật và tạo Gemini inlineData."""
    from PIL import Image, UnidentifiedImageError
    from platform_core.storage import get_storage

    storage = get_storage()
    result: list[dict] = []
    total_size = 0
    mime_by_format = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    for key in _owned_image_keys(params, owner_id):
        if not storage.exists(key):
            raise ValueError("Ảnh đầu vào không còn tồn tại.")
        size = storage.size(key)
        total_size += size
        if size > 8 * 1024 * 1024 or total_size > 20 * 1024 * 1024:
            raise ValueError("Ảnh đầu vào vượt giới hạn 8 MB/ảnh hoặc 20 MB/node.")
        with storage.open(key) as stream:
            data = stream.read()
        try:
            with Image.open(io.BytesIO(data)) as image:
                mime = mime_by_format.get(str(image.format or "").upper())
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Ảnh đầu vào bị hỏng hoặc không đúng định dạng.") from exc
        if not mime:
            raise ValueError("Node Text chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.")
        result.append({"inlineData": {
            "mimeType": mime,
            "data": base64.b64encode(data).decode("ascii"),
        }})
    return result


def _upload_video_part(params: dict, owner_id: str, api_key: str) -> tuple[dict | None, str]:
    """Upload video đã sở hữu qua Gemini Files API và trả part dùng một lần."""
    value = params.get("video_key")
    if not value:
        return None, ""
    from platform_core.storage import get_storage
    storage = get_storage()
    key = _owned_key(value, owner_id, "Video")
    if not storage.exists(key):
        raise ValueError("Video đầu vào không còn tồn tại.")
    size = storage.size(key)
    if size <= 0 or size > 90 * 1024 * 1024:
        raise ValueError("Video đầu vào phải từ 1 byte đến 90 MB.")
    suffix = pathlib.PurePosixPath(key).suffix.lower()
    mime_by_suffix = {
        ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
        ".mpeg": "video/mpeg", ".mpg": "video/mpeg", ".avi": "video/avi",
        ".wmv": "video/wmv", ".3gp": "video/3gpp", ".3gpp": "video/3gpp",
    }
    mime = mime_by_suffix.get(suffix)
    if not mime:
        raise ValueError("Node Text chưa hỗ trợ định dạng video này.")
    with storage.open(key) as stream:
        data = stream.read()

    import httpx
    headers = {
        "x-goog-api-key": api_key,
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(size),
        "X-Goog-Upload-Header-Content-Type": mime,
        "Content-Type": "application/json",
    }
    try:
        started = httpx.post(f"{_BASE}/upload/v1beta/files", headers=headers,
                             json={"file": {"displayName": pathlib.PurePosixPath(key).name}},
                             timeout=_TIMEOUT_S)
    except httpx.HTTPError as exc:
        raise GeminiError(_sanitize(f"Lỗi upload video Gemini: {exc}", api_key)) from exc
    if started.status_code not in {200, 201}:
        raise GeminiError(f"Dịch vụ upload video tạm lỗi (mã {started.status_code}).",
                          status_code=started.status_code)
    upload_url = started.headers.get("x-goog-upload-url", "")
    if not upload_url:
        raise GeminiError("Gemini không trả URL upload video.")
    uploaded = httpx.post(upload_url, content=data, headers={
        "Content-Length": str(size), "X-Goog-Upload-Offset": "0",
        "X-Goog-Upload-Command": "upload, finalize",
    }, timeout=_TIMEOUT_S)
    if uploaded.status_code not in {200, 201}:
        raise GeminiError(f"Dịch vụ upload video tạm lỗi (mã {uploaded.status_code}).",
                          status_code=uploaded.status_code)
    file_info = (uploaded.json() or {}).get("file") or {}
    name, uri = str(file_info.get("name") or ""), str(file_info.get("uri") or "")
    if not name or not uri:
        raise GeminiError("Gemini không trả định danh video đã upload.")
    try:
        deadline = time.monotonic() + _TIMEOUT_S
        state = str(file_info.get("state") or "PROCESSING")
        while state != "ACTIVE":
            if state == "FAILED" or time.monotonic() >= deadline:
                raise GeminiError("Gemini không xử lý được video trong thời gian cho phép.")
            time.sleep(2)
            polled = httpx.get(f"{_BASE}/v1beta/{name}",
                               headers={"x-goog-api-key": api_key}, timeout=15)
            if polled.status_code != 200:
                raise GeminiError(f"Dịch vụ xử lý video tạm lỗi (mã {polled.status_code}).",
                                  status_code=polled.status_code)
            file_info = polled.json() or {}
            state = str(file_info.get("state") or "PROCESSING")
            uri = str(file_info.get("uri") or uri)
        return {"fileData": {"mimeType": mime, "fileUri": uri}}, name
    except Exception:
        _delete_gemini_file(name, api_key)
        raise


def _delete_gemini_file(name: str, api_key: str) -> None:
    if not name:
        return
    try:
        import httpx
        httpx.delete(f"{_BASE}/v1beta/{name}",
                     headers={"x-goog-api-key": api_key}, timeout=15)
    except Exception:
        pass


def _parse_script(raw: str, topic: str) -> dict:
    """Bóc JSON kịch bản (bỏ fence ```json```). Lỗi parse → gói raw để không mất."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    s = s.strip().removeprefix("json").strip()
    try:
        obj = json.loads(s)
    except Exception:
        return {"title": topic, "hook": raw[:200],
                "sections": [{"title": "Nội dung", "content": raw}],
                "outro": "", "description": "", "tags": [], "parse_error": True}
    if not isinstance(obj.get("sections"), list):
        obj["sections"] = []
    obj.setdefault("tags", [])
    obj.setdefault("parse_error", False)
    return obj


def handle(params: dict, ctx=None) -> dict:
    """Sinh một kịch bản YouTube có cấu trúc, trả về dict `script`."""
    from apps.kichban.manifest import CREDIT_PER_SCRIPT
    generic_prompt = str(params.get("prompt", "")).strip()
    if generic_prompt:
        owner_id = str(params.get("owner_id") or "")
        media_parts = [*_context_text_parts(params), *_load_image_parts(params, owner_id)]
        model = str(params.get("model") or _MODEL)
        output_format = str(params.get("format") or "markdown")
        system = ("You are a careful multimodal assistant. Analyze every supplied image "
                  "when present and follow the user's requested task. Follow the requested "
                  f"output format: {output_format}. Do not wrap JSON in markdown fences.")
        api_key, key_id = _lay_key(model)
        if not api_key:
            raise RuntimeError("Chưa có API key Gemini cho nhóm chat.")
        video_part, remote_file = _upload_video_part(params, owner_id, api_key)
        if video_part:
            media_parts.append(video_part)
        if ctx is not None:
            ctx.progress(40, "đang phân tích nội dung" if media_parts else "đang sinh văn bản")
        try:
            text = _goi_gemini_text(generic_prompt, api_key, model, system, media_parts)
        except GeminiError as e:
            _ket_qua_key(key_id, thanh_cong=False, last_status=e.status_code)
            raise
        finally:
            _delete_gemini_file(remote_file, api_key)
        _ket_qua_key(key_id, thanh_cong=True)
        if ctx is not None:
            ctx.progress(100, "xong")
        from apps.kichban.manifest import _cost
        return {"text": text, "format": output_format,
                "input_image_count": len(_owned_image_keys(params, owner_id)),
                "has_text_context": bool(params.get("source_text")),
                "has_video_context": bool(params.get("video_key")),
                "credit_cost": _cost(params)}
    topic = str(params.get("topic", "")).strip()
    if not topic:
        raise ValueError("Chưa nhập chủ đề video.")
    prompt = build_prompt(topic, duration=str(params.get("duration", "")),
                          tone=str(params.get("tone", "")),
                          audience=str(params.get("audience", "")),
                          language=str(params.get("language", "")))
    from apps.kichban.features import context_directive, derive_shot_list
    extra = context_directive(str(params.get("sources") or ""),
                              str(params.get("research") or ""))
    if extra:
        prompt += "\n\n" + extra
    api_key, key_id = _lay_key()
    if not api_key:
        raise RuntimeError("Chưa có API key Gemini (thêm ở /admin → APIKEYS, "
                           "hoặc đặt GEMINI_API_KEY cho dev).")
    if ctx is not None:
        ctx.progress(40, "đang viết kịch bản")
    try:
        raw = _goi_gemini_text(prompt, api_key)
    except GeminiError as e:
        _ket_qua_key(key_id, thanh_cong=False, last_status=e.status_code)
        raise
    _ket_qua_key(key_id, thanh_cong=True)
    script = _parse_script(raw, topic)
    if ctx is not None:
        ctx.progress(100, "xong")
    return {"script": script, "shot_list": derive_shot_list(script),
            "credit_cost": CREDIT_PER_SCRIPT}
