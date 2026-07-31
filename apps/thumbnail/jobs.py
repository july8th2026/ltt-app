"""
Handler job của app thumbnail — worker gọi hàm này (H5).

Viết mới, gọn: một khoá `GEMINI_API_KEY` (không api-pool), gọi Gemini Image API
đồng bộ bằng httpx, lưu ảnh qua `platform_core.storage`. Tham chiếu logic từ
`D:/BOT GEMINI/app/modules/thumbnail_api/adapters/api_adapter.py` (chỉ đọc).

Hợp đồng handler (giống mọi app):
- idempotent theo job (khoá lưu theo job_id → chạy lại ghi đè, không nhân bản);
- báo tiến độ qua ctx;
- NÉM exception khi thất bại → nền tảng hoàn credit đã giữ.

Khoá API chỉ ở phía máy chủ, KHÔNG BAO GIỜ xuống trình duyệt.
"""
from __future__ import annotations

import base64
import io
import os

_MODEL = "gemini-2.5-flash-image"
_BASE = "https://generativelanguage.googleapis.com"
_TIMEOUT_S = 110          # < trần 100s Cloudflare không áp cho worker, nhưng giữ gọn


class GeminiError(RuntimeError):
    """Lỗi gọi Gemini kèm mã HTTP (để bộ máy key phân loại: 429 cooldown...)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _sanitize(msg: str, key: str) -> str:
    """Bỏ khoá API khỏi thông báo lỗi trước khi ném ra."""
    if key and len(key) > 8:
        msg = msg.replace(key, "***")
    return msg[:400]


def _lay_key(model: str) -> tuple[str, str | None]:
    """Lấy credential Gemini từ bộ máy APIKEYS (H8). Fallback env `GEMINI_API_KEY`
    khi chưa có CSDL/khoá (dev/test). Trả (credential, key_id|None)."""
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
    """Đánh dấu kết quả lên key ở bộ máy APIKEYS (bỏ qua nếu dùng key env)."""
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


def build_prompt(topic: str, title: str = "", aspect_ratio: str = "16:9") -> str:
    """Ghép prompt thumbnail từ chủ đề + tiêu đề (inline, không phụ thuộc file ngoài)."""
    parts = [
        f"Professional YouTube thumbnail, aspect ratio {aspect_ratio}.",
        f"Topic: {topic.strip()}.",
    ]
    if title.strip():
        parts.append(
            f'Large bold title text "{title.strip()}" with thick outline stroke '
            f"and drop shadow for maximum readability."
        )
    parts.append(
        "Eye-catching, high-contrast, vivid saturated colors, dramatic lighting, "
        "clear focal subject, click-worthy composition, high resolution, sharp details."
    )
    return " ".join(parts)


def _goi_gemini(prompt: str, aspect_ratio: str, api_key: str) -> bytes:
    """Gọi Gemini Image API một lần, trả về bytes ảnh PNG. Ném lỗi nếu thất bại."""
    import httpx

    # Khoá ĐI QUA HEADER `x-goog-api-key`, KHÔNG nhét vào query `?key=` (W2.6):
    # URL hay bị ghi lại (log proxy, access log, lịch sử) → khoá trong query là
    # bề mặt rò khoá. Header không bị log mặc định.
    url = f"{_BASE}/v1beta/models/{_MODEL}:generateContent"
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
    """Sinh 1-4 thumbnail, lưu qua storage, trả về danh sách khoá ảnh."""
    topic = str(params.get("topic", "")).strip()
    if not topic:
        raise ValueError("Chưa nhập chủ đề thumbnail.")
    title = str(params.get("title", ""))
    aspect_ratio = str(params.get("aspect_ratio", "16:9")) or "16:9"
    owner_id = str(params.get("owner_id", "")) or "unknown"
    try:
        count = max(1, min(int(params.get("count", 1)), 4))
    except (TypeError, ValueError):
        count = 1

    model = str(params.get("model") or "gemini-2.5-flash-image")
    # Lấy key từ BỘ MÁY APIKEYS (H8) — app không giữ key nữa. Fallback env cho dev.
    api_key, key_id = _lay_key(model)
    if not api_key:
        # Ném để nền tảng hoàn credit — không âm thầm nuốt.
        raise RuntimeError("Chưa có API key Gemini (thêm ở /admin → APIKEYS, "
                           "hoặc đặt GEMINI_API_KEY cho dev).")

    from apps.thumbnail.manifest import CREDIT_PER_IMAGE
    from platform_core.storage import get_storage
    storage = get_storage()
    prompt = build_prompt(topic, title, aspect_ratio)
    job_id = getattr(ctx, "job_id", "") or "adhoc"

    # Tính tiền theo ảnh THÀNH CÔNG + resume-safe (W1.1):
    #  - Ảnh đã lưu ở lần chạy trước (worker crash rồi job bị reclaim) thì DÙNG
    #    LẠI, không gọi Gemini lần nữa → không trả tiền API hai lần.
    #  - Một ảnh lỗi KHÔNG làm hỏng cả job: tạo được bao nhiêu tính tiền bấy nhiêu
    #    (quyết toán theo `credit_cost` bên dưới, worker hoàn phần chênh). Chỉ khi
    #    KHÔNG tạo được ảnh nào mới ném để hoàn toàn bộ + cho retry.
    keys: list[str] = []
    errors: list[str] = []
    last_status: int | None = None
    for i in range(count):
        key = f"thumbnail/{owner_id}/{job_id}/{i}.png"
        if storage.exists(key):
            keys.append(key)                     # resume: đã tạo trước đó
            continue
        if ctx is not None:
            ctx.progress(int(i * 100 / count), f"đang tạo ảnh {i + 1}/{count}")
        try:
            img = _goi_gemini(prompt, aspect_ratio, api_key)
        except GeminiError as e:                 # lỗi HTTP → nhớ status để chấm key
            errors.append(str(e))
            last_status = e.status_code
            continue
        except Exception as e:                   # noqa: BLE001 — lỗi khác (nội dung...)
            errors.append(str(e))
            continue
        storage.put(key, io.BytesIO(img), content_type="image/png")
        keys.append(key)

    if not keys:
        # Không tạo được ảnh nào → chấm lỗi key (nếu do key), ném để nền tảng
        # HOÀN toàn bộ credit + retry.
        _ket_qua_key(key_id, thanh_cong=False, last_status=last_status)
        raise RuntimeError(errors[-1] if errors else "Không tạo được ảnh nào.")

    _ket_qua_key(key_id, thanh_cong=True)

    if ctx is not None:
        ctx.progress(100, "xong")

    # `credit_cost` = số ảnh thật × giá mỗi ảnh → worker quyết toán đúng phần
    # dùng, hoàn lại phần giữ dư (giữ count ảnh nhưng chỉ tạo được len(keys)).
    return {"image_keys": keys, "count": len(keys), "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "credit_cost": len(keys) * CREDIT_PER_IMAGE,
            "errors": errors[:3]}
