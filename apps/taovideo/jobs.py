"""
Handler job app `seedance` (A2, Pha 1). Video ASYNC: submit → poll → tải → quyết toán.

Chạy trong WORKER (không dính trần 100s của Cloudflare). Vòng poll gọi `ctx.progress`
mỗi nhịp → cập nhật heartbeat < ORPHAN_TIMEOUT (5') nên job dài KHÔNG bị nhặt lại.

Hợp đồng: idempotent (resume: nếu video đã lưu thì bỏ qua) · báo tiến độ · NÉM khi
lỗi (nền tảng hoàn credit đã giữ). Giá quyết toán theo token THẬT provider trả.
"""
from __future__ import annotations

import io
import os
import time

import random

from apps.taovideo import cost, modelark, models, refs

POLL_INTERVAL_S = 5
POLL_MAX_MINUTES = 15          # đủ cho hầu hết job; worker giữ job suốt thời gian này
_POLL_MAX = POLL_MAX_MINUTES * 60 // POLL_INTERVAL_S
MOD_RETRY_MAX = 5              # kiểm duyệt đầu ra → đổi seed render lại (block bill 0 token)


def _lay_key():
    """Key byteplus từ APIKEYS (category video). Fallback env BYTEPLUS_API_KEY (dev)."""
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        from platform_core.models import APIKEY_CAT_VIDEO
        gen = get_session(); db = next(gen)
        try:
            key = api_pool.lay_key(db, "byteplus", category=APIKEY_CAT_VIDEO)
            cred = api_keys.lay_credential(db, key)
            db.commit()
            return cred, key.id
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return (os.environ.get("BYTEPLUS_API_KEY") or "").strip(), None


def _ket_qua_key(key_id, *, thanh_cong, last_status=None):
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


def handle(params: dict, ctx=None) -> dict:
    prompt = str(params.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Chưa nhập mô tả video.")
    model = str(params.get("model") or models.DEFAULT_MODEL)
    m = models.get(model)
    if m is None:
        raise ValueError(f"Model không hợp lệ: {model}")
    resolution = str(params.get("resolution", "480p"))
    aspect = str(params.get("aspect_ratio", "16:9"))
    try:
        duration = int(params.get("duration", 5))
    except (TypeError, ValueError):
        duration = 5
    audio = bool(params.get("generate_audio", True))
    owner_id = str(params.get("owner_id", "")) or "unknown"
    job_id = getattr(ctx, "job_id", "") or "adhoc"

    from platform_core.storage import get_storage
    storage = get_storage()
    vkey = f"taovideo/{owner_id}/{job_id}/video.mp4"
    if storage.exists(vkey):                      # resume: đã tạo xong trước đó
        return {"video_key": vkey, "credit_cost": cost.uoc_luong_credit(
            model, resolution, duration, False)}

    # Refs (Pha 2): ảnh tham chiếu inline ≤8MB (chuẩn hoá Pillow). Ảnh lớn/video/
    # audio + heal người-thật cần asset:// (Pha 2b, đang bổ sung).
    ref_dicts = []
    has_video_input = False
    for rs in (params.get("refs") or []):
        kind = (rs.get("kind") or "image").strip()
        skey = (rs.get("storage_key") or "").strip()
        if not skey:
            continue
        if kind == "image":
            data = storage.open(skey).read()
            try:
                url = refs.image_to_inline(data)
            except refs.RefError:
                raise RuntimeError("Ảnh tham chiếu > 8MB — bản này hỗ trợ ảnh ≤8MB "
                                   "(ảnh lớn/video ref: Pha 2b asset://).")
            ref_dicts.append({"kind": "image", "url": url,
                              "role": rs.get("role") or "reference_image",
                              "handle": rs.get("handle") or ""})
        else:
            has_video_input = True   # video/audio ref -> Pha 2b
    content = refs.build_content(prompt, ref_dicts)

    api_key, key_id = _lay_key()
    if not api_key:
        raise RuntimeError("Chưa có API key BytePlus (thêm ở /admin → APIKEYS).")

    endpoint = models.provider_model(model)
    seed = None
    result = None
    for mod_try in range(MOD_RETRY_MAX + 1):
        if ctx is not None:
            ctx.progress(5, "gửi yêu cầu tạo video" + (f" (thử lại {mod_try})" if mod_try else ""))
        try:
            task_id = modelark.submit(
                api_key, model_endpoint=endpoint, content=content,
                resolution=resolution, duration=duration, aspect_ratio=aspect,
                generate_audio=audio, seed=seed)
        except modelark.ModelArkError as e:
            _ket_qua_key(key_id, thanh_cong=False, last_status=e.status_code)
            raise

        st_final = None
        for i in range(_POLL_MAX):
            if ctx is not None:
                ctx.progress(min(90, 10 + int(i * 80 / _POLL_MAX)), "đang dựng video…")
            time.sleep(POLL_INTERVAL_S)
            try:
                st = modelark.poll(api_key, task_id)
            except modelark.ModelArkError:
                continue
            if st["status"] in ("succeeded", "failed", "expired", "cancelled"):
                st_final = st
                break
        if st_final is None:
            raise RuntimeError(f"Quá thời gian chờ ({POLL_MAX_MINUTES} phút) — thử lại sau.")
        if st_final["status"] == "succeeded":
            result = st_final
            break
        # Thất bại: nếu do KIỂM DUYỆT đầu ra → đổi seed render lại (block bill 0 token).
        err = (st_final.get("error") or "").lower()
        if mod_try < MOD_RETRY_MAX and ("moderat" in err or "sensitive" in err or "risk control" in err):
            seed = random.randint(1, 2_147_483_647)
            continue
        _ket_qua_key(key_id, thanh_cong=False)
        raise RuntimeError(f"Tạo video thất bại: {st_final.get('error') or st_final['status']}")

    if ctx is not None:
        ctx.progress(92, "tải video về")
    if not result.get("video_url"):
        raise RuntimeError("Provider không trả URL video.")
    video = modelark.download(result["video_url"])
    storage.put(vkey, io.BytesIO(video), content_type="video/mp4")
    _ket_qua_key(key_id, thanh_cong=True)

    tokens = int(result.get("tokens") or 0)
    credit_cost = (cost.credit_tu_token(model, tokens, has_video_input) if tokens
                   else cost.uoc_luong_credit(model, resolution, duration, has_video_input))
    if ctx is not None:
        ctx.progress(100, "xong")
    return {"video_key": vkey, "credit_cost": credit_cost, "tokens": tokens,
            "resolution": resolution, "duration": duration, "model": model,
            "refs": len(ref_dicts)}
