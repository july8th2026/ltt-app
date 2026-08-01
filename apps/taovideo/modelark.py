"""
modelark.py — adapter BytePlus ModelArk (di trú từ `adapters/modelark_adapter.py`).

Async video: POST tạo task → GET poll tới khi xong → tải video. Auth Bearer (key
lấy từ APIKEYS provider `byteplus`). Chỉ phần API thuần — KHÔNG kéo asset://
AK/SK (Pha 2).
"""
from __future__ import annotations

BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3"
DOWNLOAD_CAP = 200 * 1024 * 1024      # 200MB an toàn


class ModelArkError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _che(msg: str, key: str) -> str:
    if key and len(key) > 8:
        msg = msg.replace(key, "***")
    return msg[:500]


def submit(api_key: str, *, model_endpoint: str, prompt: str, resolution: str,
           duration: int, aspect_ratio: str, generate_audio: bool = True,
           images_data_url: list | None = None, seed: int | None = None,
           timeout: int = 30) -> str:
    """Tạo task video → trả task_id. `images_data_url`: danh sách data: URL (inline, ≤8MB)."""
    import httpx
    content = [{"type": "text", "text": prompt}]
    for url in (images_data_url or []):
        content.append({"type": "image_url", "image_url": {"url": url},
                        "role": "reference_image"})
    body = {
        "model": model_endpoint, "content": content,
        "ratio": aspect_ratio, "resolution": resolution,
        "duration": int(duration), "generate_audio": bool(generate_audio),
        "watermark": False,
    }
    if seed is not None:
        body["seed"] = int(seed)
    try:
        r = httpx.post(f"{BASE_URL}/contents/generations/tasks",
                       headers={"Authorization": f"Bearer {api_key}"},
                       json=body, timeout=timeout)
    except httpx.HTTPError as e:
        raise ModelArkError(_che(f"ModelArk mang loi: {e}", api_key), None)
    if r.status_code != 200:
        raise ModelArkError(_che(f"ModelArk submit HTTP {r.status_code}: {r.text}", api_key),
                            r.status_code)
    data = r.json()
    tid = data.get("id") or data.get("task_id") or (data.get("data") or {}).get("id")
    if not tid:
        raise ModelArkError(_che(f"ModelArk khong tra task_id: {r.text}", api_key), None)
    return str(tid)


def poll(api_key: str, task_id: str, *, timeout: int = 30) -> dict:
    """Đọc trạng thái task → {status, video_url, tokens}. status: pending/running/
    succeeded/failed/expired/cancelled."""
    import httpx
    try:
        r = httpx.get(f"{BASE_URL}/contents/generations/tasks/{task_id}",
                      headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
    except httpx.HTTPError as e:
        raise ModelArkError(_che(f"ModelArk poll loi: {e}", api_key), None)
    if r.status_code != 200:
        raise ModelArkError(_che(f"ModelArk poll HTTP {r.status_code}: {r.text}", api_key),
                            r.status_code)
    d = r.json()
    status = (d.get("status") or "").lower()
    content = d.get("content") or {}
    video_url = content.get("video_url") or d.get("video_url") or content.get("output_url") or ""
    usage = d.get("usage") or {}
    tokens = usage.get("total_tokens") or usage.get("completion_tokens") or 0
    err = ""
    if status in ("failed", "expired", "cancelled"):
        err = (d.get("error") or {}).get("message") if isinstance(d.get("error"), dict) else str(d.get("error") or "")
    return {"status": status, "video_url": video_url, "tokens": int(tokens or 0),
            "error": _che(err or "", api_key)}


def download(video_url: str, *, timeout: int = 300) -> bytes:
    """Tải video (stream, chặn trần DOWNLOAD_CAP)."""
    import httpx
    buf = bytearray()
    try:
        with httpx.stream("GET", video_url, timeout=timeout, follow_redirects=True) as r:
            if r.status_code != 200:
                raise ModelArkError(f"Tai video HTTP {r.status_code}", r.status_code)
            for chunk in r.iter_bytes():
                buf.extend(chunk)
                if len(buf) > DOWNLOAD_CAP:
                    raise ModelArkError("Video vuot tran 200MB", None)
    except httpx.HTTPError as e:
        raise ModelArkError(f"Tai video loi: {type(e).__name__}", None)
    return bytes(buf)
