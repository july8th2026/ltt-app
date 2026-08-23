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

from platform_core.i18n import _ as _t
from platform_core.public_api import costing
import base64
import io
import os
import pathlib

_MODEL = "gemini-2.5-flash-image"          # mặc định khi không chọn model
_BASE = "https://generativelanguage.googleapis.com"
_PROMPTS_DIR = pathlib.Path(__file__).resolve().parent / "prompts"
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


def build_prompt(topic: str, *, title: str = "", subtitle: str = "",
                 phong_cach: str = "", kieu_trend: str = "", text_style: str = "",
                 ngon_ngu: str = "", aspect_ratio: str = "16:9",
                 brand: dict | None = None) -> str:
    """Ghép prompt thumbnail TỪ FRAGMENT (di trú trung thành từ BOT GEMINI
    `service.py`): base_prompt.txt + phong_cách + kiểu trend + style chữ + ngôn
    ngữ + tiêu đề/phụ đề. KHÔNG hardcode chuỗi prompt (dùng `apps/thumbnail/prompts/`).

    Lựa chọn rỗng/không hợp lệ → lấy mặc định (mục đầu trong `_labels.json`)."""
    from platform_core import prompt_fragments as pf
    d = _PROMPTS_DIR
    phong_cach = phong_cach or pf.default_option(d, "phong_cach")
    kieu_trend = kieu_trend or pf.default_option(d, "kieu_trend")
    text_style = text_style or pf.default_option(d, "text_style")
    ngon_ngu = ngon_ngu or pf.default_option(d, "ngon_ngu")
    title, subtitle = title.strip(), subtitle.strip()
    mapping = {
        "aspect_ratio": aspect_ratio,
        "user_input": topic.strip(),
        "phong_cach_style": pf.read_fragment(d, "phong_cach", phong_cach),
        "kieu_trend_layout": pf.read_fragment(d, "kieu_trend", kieu_trend),
        "text_style_directive": pf.read_fragment(d, "text_style", text_style),
        "ngon_ngu_directive": pf.read_fragment(d, "ngon_ngu", ngon_ngu),
        "title_text": (f'Large prominent text "{title}" with outline stroke and drop shadow.'
                       if title else ""),
        "subtitle_text": (f'Smaller subtitle text: "{subtitle}".' if subtitle else ""),
    }
    from apps.thumbnail.features import brand_directive
    prompt = pf.build(d, mapping)
    directive = brand_directive(brand)
    return f"{prompt}\n\n{directive}" if directive else prompt


def _goi_gemini(prompt: str, aspect_ratio: str, api_key: str,
                model: str = _MODEL, reference: tuple[bytes, str] | None = None) -> bytes:
    """Gọi Gemini Image API một lần, trả về bytes ảnh PNG. Ném lỗi nếu thất bại."""
    import httpx

    # Khoá ĐI QUA HEADER `x-goog-api-key`, KHÔNG nhét vào query `?key=` (W2.6):
    # URL hay bị ghi lại (log proxy, access log, lịch sử) → khoá trong query là
    # bề mặt rò khoá. Header không bị log mặc định.
    url = f"{_BASE}/v1beta/models/{model or _MODEL}:generateContent"
    headers = {"x-goog-api-key": api_key}
    parts = [{"text": prompt}]
    if reference:
        data, mime = reference
        parts.append({"inlineData": {"mimeType": mime,
                                     "data": base64.b64encode(data).decode("ascii")}})
        parts.append({"text": "Use the attached image as visual composition/style reference; do not copy protected logos or text unless requested."})
    body = {
        "contents": [{"parts": parts}],
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
        raise RuntimeError(_t('Gemini không trả candidate nào.'))
    cand = candidates[0]
    if cand.get("finishReason") == "SAFETY":
        raise RuntimeError(_t('Bị chặn vì lý do an toàn nội dung.'))

    for part in cand.get("content", {}).get("parts", []) or []:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])

    raise RuntimeError(_t('Gemini không trả ảnh nào (chỉ có văn bản).'))


def handle(params: dict, ctx=None) -> dict:
    """Sinh 1-4 thumbnail, lưu qua storage, trả về danh sách khoá ảnh."""
    topic = str(params.get("topic", "")).strip()
    if not topic:
        raise ValueError(_t('Chưa nhập chủ đề thumbnail.'))
    title = str(params.get("title", ""))
    subtitle = str(params.get("subtitle", ""))
    phong_cach = str(params.get("phong_cach", ""))
    kieu_trend = str(params.get("kieu_trend", ""))
    text_style = str(params.get("text_style", ""))
    ngon_ngu = str(params.get("ngon_ngu", ""))
    brand = params.get("brand") if isinstance(params.get("brand"), dict) else {}
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
    prompt = build_prompt(topic, title=title, subtitle=subtitle, phong_cach=phong_cach,
                          kieu_trend=kieu_trend, text_style=text_style, ngon_ngu=ngon_ngu,
                          aspect_ratio=aspect_ratio, brand=brand)
    job_id = getattr(ctx, "job_id", "") or "adhoc"
    reference = None
    reference_key = str(params.get("reference_key") or "")
    reference_mime = str(params.get("reference_mime") or "")
    if reference_key:
        if not reference_key.startswith(f"thumbnail/{owner_id}/"):
            raise ValueError(_t('Ảnh tham chiếu không thuộc người dùng hiện tại.'))
        with storage.open(reference_key) as stream:
            reference = (stream.read(), reference_mime)

    # Tính tiền theo ảnh THÀNH CÔNG + resume-safe (W1.1):
    #  - Ảnh đã lưu ở lần chạy trước (worker crash rồi job bị reclaim) thì DÙNG
    #    LẠI, không gọi Gemini lần nữa → không trả tiền API hai lần.
    #  - Một ảnh lỗi KHÔNG làm hỏng cả job: tạo được bao nhiêu tính tiền bấy nhiêu
    #    (quyết toán theo `credit_cost` bên dưới, worker hoàn phần chênh). Chỉ khi
    #    KHÔNG tạo được ảnh nào mới ném để hoàn toàn bộ + cho retry.
    def score_image(data: bytes) -> dict:
        from apps.thumbnail.features import technical_score
        try:
            return technical_score(data)
        except Exception:  # legacy/provider payload invalid: generation must still settle normally
            return {"score": None, "method": "unavailable"}

    keys: list[str] = []
    scores: list[dict] = []
    errors: list[str] = []
    last_status: int | None = None
    for i in range(count):
        key = f"thumbnail/{owner_id}/{job_id}/{i}.png"
        if storage.exists(key):
            keys.append(key)                     # resume: đã tạo trước đó
            with storage.open(key) as stream:
                scores.append(score_image(stream.read()))
            continue
        if ctx is not None:
            ctx.progress(int(i * 100 / count), f"đang tạo ảnh {i + 1}/{count}")
        try:
            img = _goi_gemini(prompt, aspect_ratio, api_key, model, reference)
        except GeminiError as e:                 # lỗi HTTP → nhớ status để chấm key
            errors.append(str(e))
            last_status = e.status_code
            continue
        except Exception as e:                   # noqa: BLE001 — lỗi khác (nội dung...)
            errors.append(str(e))
            continue
        storage.put(key, io.BytesIO(img), content_type="image/png")
        keys.append(key)
        scores.append(score_image(img))

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
    return {"image_keys": keys, "scores": scores, "count": len(keys), "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "credit_cost": len(keys) * CREDIT_PER_IMAGE,
            "errors": errors[:3],
            # App nay tinh gia PHANG bat ke model, nen day la cho duy nhat biet
            # model that su da dung. Thieu no thi bang bien loi nhuan se thay
            # doanh thu ma khong thay khoan chi lon nhat.
            costing.KHOA_GOI_PROVIDER: [{"model": model, "count": len(keys)}]}
