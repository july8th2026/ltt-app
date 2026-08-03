"""
Handler job app `script` (di trú A1). Sinh kịch bản YouTube có cấu trúc qua Gemini.

Đầu ra là VĂN BẢN/JSON (title/hook/sections/outro/description/tags) — khác app ảnh.
Prompt ghép từ fragment (`platform_core.prompt_fragments`), gọi Gemini text (category
chat), parse JSON. Key qua APIKEYS (H8), fallback env.

Hợp đồng: idempotent ở mức job (credit quyết toán một lần) · báo tiến độ · NÉM khi lỗi.
"""
from __future__ import annotations

import json
import os
import pathlib

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


def _lay_key() -> tuple[str, str | None]:
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        from platform_core.models import APIKEY_CAT_CHAT
        gen = get_session(); db = next(gen)
        try:
            key = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_CHAT, model=_MODEL)
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


def _goi_gemini_text(prompt: str, api_key: str) -> str:
    """Gọi Gemini text (generateContent) → chuỗi văn bản. Ném lỗi nếu thất bại."""
    import httpx
    url = f"{_BASE}/v1beta/models/{_MODEL}:generateContent"
    headers = {"x-goog-api-key": api_key}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
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
