"""
Handler job app `image` (di trú A1). Sinh ảnh từ prompt TỰ DO qua Gemini Image API.

Lõi gọi Gemini + lưu storage + tính tiền theo ảnh giống `apps/thumbnail/jobs.py`
(L2 copy theo công thức di trú) nhưng KHÔNG ghép prompt từ catalog — prompt là
văn bản người dùng gõ thẳng. Key lấy từ bộ máy APIKEYS (H8), fallback env.

Hợp đồng handler: idempotent theo job (khoá lưu theo job_id) · báo tiến độ qua ctx
· NÉM exception khi thất bại → nền tảng hoàn credit đã giữ. Khoá API chỉ ở máy chủ.
"""
from __future__ import annotations

import base64
import io
import os

_MODEL = "gemini-2.5-flash-image"
_BASE = "https://generativelanguage.googleapis.com"
_TIMEOUT_S = 110


class GeminiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _sanitize(msg: str, key: str) -> str:
    if key and len(key) > 8:
        msg = msg.replace(key, "***")
    return msg[:400]


def _lay_key(model: str) -> tuple[str, str | None]:
    """Lấy credential Gemini từ APIKEYS (category image). Fallback env cho dev."""
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        from platform_core.models import APIKEY_CAT_IMAGE
        gen = get_session(); db = next(gen)
        try:
            key = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_IMAGE, model=model)
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


def _goi_gemini(prompt: str, aspect_ratio: str, api_key: str,
                model: str = _MODEL) -> bytes:
    """Gọi Gemini Image API một lần → bytes PNG. Ném lỗi nếu thất bại."""
    import httpx
    url = f"{_BASE}/v1beta/models/{model or _MODEL}:generateContent"
    headers = {"x-goog-api-key": api_key}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "imageConfig": {"aspectRatio": aspect_ratio},
        },
    }
    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=_TIMEOUT_S)
    except httpx.HTTPError as e:
        raise GeminiError(_sanitize(f"Lỗi kết nối Gemini: {e}", api_key), status_code=None)
    if resp.status_code != 200:
        raise GeminiError(_sanitize(
            f"Gemini HTTP {resp.status_code}: {resp.text}", api_key),
            status_code=resp.status_code)
    data = resp.json()
    pf = data.get("promptFeedback", {}) or {}
    if pf.get("blockReason"):
        raise RuntimeError(f"Nội dung bị chặn: {pf['blockReason']}")
    candidates = data.get("candidates", []) or []
    if not candidates:
        raise RuntimeError("Gemini không trả candidate nào.")
    cand = candidates[0]
    if cand.get("finishReason") == "SAFETY":
        raise RuntimeError("Bị chặn vì lý do an toàn nội dung.")
    for part in cand.get("content", {}).get("parts", []) or []:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    raise RuntimeError("Gemini không trả ảnh nào (chỉ có văn bản).")


def handle(params: dict, ctx=None) -> dict:
    """Sinh 1-4 ảnh từ prompt tự do, lưu qua storage, trả danh sách khoá ảnh."""
    prompt = str(params.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Chưa nhập mô tả ảnh (prompt).")
    aspect_ratio = str(params.get("aspect_ratio", "16:9")) or "16:9"
    owner_id = str(params.get("owner_id", "")) or "unknown"
    model = str(params.get("model") or _MODEL)
    try:
        count = max(1, min(int(params.get("count", 1)), 4))
    except (TypeError, ValueError):
        count = 1

    api_key, key_id = _lay_key(model)
    if not api_key:
        raise RuntimeError("Chưa có API key Gemini (thêm ở /admin → APIKEYS, "
                           "hoặc đặt GEMINI_API_KEY cho dev).")

    from apps.taoanh.manifest import CREDIT_PER_IMAGE
    from platform_core.storage import get_storage
    storage = get_storage()
    job_id = getattr(ctx, "job_id", "") or "adhoc"

    keys: list[str] = []
    errors: list[str] = []
    last_status: int | None = None
    for i in range(count):
        key = f"taoanh/{owner_id}/{job_id}/{i}.png"
        if storage.exists(key):
            keys.append(key)
            continue
        if ctx is not None:
            ctx.progress(int(i * 100 / count), f"đang tạo ảnh {i + 1}/{count}")
        try:
            img = _goi_gemini(prompt, aspect_ratio, api_key, model)
        except GeminiError as e:
            errors.append(str(e)); last_status = e.status_code; continue
        except Exception as e:  # noqa: BLE001
            errors.append(str(e)); continue
        storage.put(key, io.BytesIO(img), content_type="image/png")
        keys.append(key)

    if not keys:
        _ket_qua_key(key_id, thanh_cong=False, last_status=last_status)
        raise RuntimeError(errors[-1] if errors else "Không tạo được ảnh nào.")
    _ket_qua_key(key_id, thanh_cong=True)
    if ctx is not None:
        ctx.progress(100, "xong")
    return {"image_keys": keys, "count": len(keys), "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "credit_cost": len(keys) * CREDIT_PER_IMAGE, "errors": errors[:3]}
