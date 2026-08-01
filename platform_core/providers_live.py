"""
providers_live.py — làm mới danh sách model TỪ NHÀ CUNG CẤP (H8 Pha 2).

Provider Registry (`providers.py`) khai model tĩnh trong mã. Với provider có
`list_models_path` (Gemini, apiai, cheapkeyai — OpenAI-compat), ta gọi endpoint
sống để lấy danh sách model thật rồi ghi vào `supported_models` của key — hết
hardcode, tự cập nhật khi provider thêm model.

Parse cả hai dạng phổ biến:
- OpenAI-compat (bearer): ``{"data": [{"id": "gpt-..."}]}``
- Gemini (query_key):     ``{"models": [{"name": "models/gemini-..."}]}``

Che credential khỏi mọi thông báo lỗi. Không tự commit.
"""
from __future__ import annotations

from typing import Optional

from platform_core import providers as P
from platform_core.providers import Provider


class ProviderLiveError(Exception):
    """Không lấy được danh sách model sống (HTTP lỗi / mạng / parse)."""


def _che(msg: str, secret: str) -> str:
    if secret and len(secret) > 6:
        msg = msg.replace(secret, "***")
    return msg[:200]


def parse_models(data, auth_style: str) -> list:
    """Rút danh sách model id từ payload JSON. Tách riêng để test không cần mạng."""
    ids: list = []
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        # OpenAI-compat: {"data":[{"id":...}]}
        for m in data["data"]:
            mid = (m.get("id") if isinstance(m, dict) else None) or ""
            if mid:
                ids.append(str(mid))
    elif isinstance(data, dict) and isinstance(data.get("models"), list):
        # Gemini: {"models":[{"name":"models/gemini-..."}]}
        for m in data["models"]:
            name = (m.get("name") if isinstance(m, dict) else None) or ""
            if name.startswith("models/"):
                name = name[len("models/"):]
            if name:
                ids.append(str(name))
    elif isinstance(data, list):
        for m in data:
            if isinstance(m, dict) and m.get("id"):
                ids.append(str(m["id"]))
            elif isinstance(m, str):
                ids.append(m)
    # Duy nhất + ổn định thứ tự.
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def lay_models_song(prov: Optional[Provider], credential: str, *, timeout: int = 10) -> list:
    """Gọi `list_models_path` của provider và trả danh sách model id sống.

    Raise `ProviderLiveError` nếu provider không có endpoint, HTTP != 200, hay lỗi
    mạng/parse (credential luôn bị che trong thông báo).
    """
    if prov is None or not prov.list_models_path:
        raise ProviderLiveError("provider khong co endpoint liet ke model")
    import httpx
    url = prov.base_url + prov.list_models_path
    try:
        if prov.auth_style == P.AUTH_QUERY_KEY:
            r = httpx.get(url, params={"key": credential}, timeout=timeout)
        elif prov.auth_style == P.AUTH_BEARER:
            r = httpx.get(url, headers={"Authorization": f"Bearer {credential}"}, timeout=timeout)
        else:
            r = httpx.get(url, headers={"X-API-Key": credential}, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        raise ProviderLiveError(_che(str(e), credential)) from None
    if r.status_code != 200:
        raise ProviderLiveError(_che(f"HTTP {r.status_code}: {r.text[:200]}", credential))
    try:
        data = r.json()
    except Exception as e:  # noqa: BLE001
        raise ProviderLiveError(_che(f"JSON loi: {e}", credential)) from None
    return parse_models(data, prov.auth_style)
