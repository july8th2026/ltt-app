"""Gemini text adapter using the platform APIKEYS pool, never app settings."""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)
DEFAULT_MODEL = "gemini-2.5-flash"
BASE_URL = "https://generativelanguage.googleapis.com"


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _redact(value: str, credential: str) -> str:
    text = str(value or "")
    if credential and len(credential) > 8:
        text = text.replace(credential, "***")
    return text[:500]


def lease(model: str) -> tuple[str, str | None]:
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        from platform_core.models import APIKEY_CAT_CHAT
        gen = get_session(); db = next(gen)
        try:
            row = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_CHAT,
                                   model=model)
            credential = api_keys.lay_credential(db, row)
            db.commit()
            return credential, row.id
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        # Dev-only compatibility; production source of truth remains APIKEYS.
        return (os.environ.get("GEMINI_API_KEY") or "").strip(), None


def report(key_id: str | None, *, ok: bool, status_code: int | None = None,
           tokens: int = 0) -> None:
    if not key_id:
        return
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        gen = get_session(); db = next(gen)
        try:
            row = api_keys.lay_key_theo_id(db, key_id)
            if row:
                if ok:
                    api_pool.danh_dau_thanh_cong(db, row, tokens=max(0, int(tokens)))
                elif status_code is not None:
                    api_pool.danh_dau_loi(db, row, http_status=status_code)
                db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        log.exception("Không cập nhật được provider telemetry PROMPT AI OMMI")


def generate_json(system: str, prompt: str, *, model: str = DEFAULT_MODEL) -> tuple[dict, int]:
    import httpx
    from platform_core.providers import resolve_model_id

    credential, key_id = lease(model)
    if not credential:
        raise ProviderError("Chưa có API key cho nhóm chat. Admin cần cấu hình APIKEYS.")
    url = f"{BASE_URL}/v1beta/models/{resolve_model_id(model)}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.45},
    }
    try:
        response = httpx.post(url, json=body, headers={"x-goog-api-key": credential},
                              timeout=115)
    except httpx.HTTPError as exc:
        raise ProviderError(_redact(f"Không kết nối được dịch vụ AI: {exc}", credential)) from None
    if response.status_code != 200:
        log.warning("PROMPT AI OMMI provider HTTP %s: %s", response.status_code,
                    _redact(response.text, credential))
        report(key_id, ok=False, status_code=response.status_code)
        raise ProviderError(f"Dịch vụ AI tạm lỗi (mã {response.status_code}).",
                            response.status_code)
    data = response.json(); text = ""
    for part in ((data.get("candidates") or [{}])[0].get("content", {}).get("parts", []) or []):
        if part.get("text"):
            text = str(part["text"]); break
    if not text:
        report(key_id, ok=False)
        raise ProviderError("Dịch vụ AI không trả dữ liệu.")
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0]
    clean = clean.strip().removeprefix("json").strip()
    try:
        result = json.loads(clean)
    except json.JSONDecodeError:
        report(key_id, ok=False)
        raise ProviderError("Dịch vụ AI trả cấu trúc không hợp lệ; hãy thử lại.") from None
    if not isinstance(result, dict):
        raise ProviderError("Dịch vụ AI trả sai loại dữ liệu.")
    usage = data.get("usageMetadata") or {}
    tokens = int(usage.get("totalTokenCount") or 0)
    report(key_id, ok=True, tokens=tokens)
    return result, tokens
