"""
translate.py — dịch prompt video qua Gemini chat (seedance Pha 2). Giữ tag @IMG_n
+ thông số kỹ thuật; chỉ trả bản dịch. Key qua APIKEYS (category chat).
"""
from __future__ import annotations

import os

_MODEL = "gemini-2.5-flash"
_BASE = "https://generativelanguage.googleapis.com"
_LANG = {"en": "English", "zh": "Chinese (Simplified)", "vi": "Vietnamese"}


def _key() -> str:
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        from platform_core.models import APIKEY_CAT_CHAT
        gen = get_session(); db = next(gen)
        try:
            k = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_CHAT, model=_MODEL)
            cred = api_keys.lay_credential(db, k)
            db.commit()
            return cred
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return (os.environ.get("GEMINI_API_KEY") or "").strip()


def dich(prompt: str, target: str = "en") -> str:
    import httpx
    api_key = _key()
    if not api_key:
        raise RuntimeError("Chưa có API key Gemini.")
    lang = _LANG.get(target, "English")
    sys = (f"Translate the following AI video prompt to {lang}. Return ONLY the "
           f"translation — no quotes, no notes. Keep unchanged: technical specs "
           f"(fps, aspect ratio, resolution) and any @IMG_n/@VID_n/@AUD_n tags.")
    r = httpx.post(
        f"{_BASE}/v1beta/models/{_MODEL}:generateContent",
        headers={"x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "systemInstruction": {"parts": [{"text": sys}]}},
        timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}")
    for part in (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", []) or []:
        if part.get("text"):
            return part["text"].strip()
    raise RuntimeError("Gemini không trả bản dịch.")
