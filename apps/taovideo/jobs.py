"""
Handler job app `seedance` (A2, Pha 1). Video ASYNC: submit → poll → tải → quyết toán.

Chạy trong WORKER (không dính trần 100s của Cloudflare). Vòng poll gọi `ctx.progress`
mỗi nhịp → cập nhật heartbeat < ORPHAN_TIMEOUT (5') nên job dài KHÔNG bị nhặt lại.

Hợp đồng: idempotent (resume: nếu video đã lưu thì bỏ qua) · báo tiến độ · NÉM khi
lỗi (nền tảng hoàn credit đã giữ). Giá quyết toán theo token THẬT provider trả.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import io
import os
import time

import random

from apps.taovideo import assets, cost, modelark, models, refs

POLL_INTERVAL_S = 5
POLL_MAX_MINUTES = 15          # đủ cho hầu hết job; worker giữ job suốt thời gian này
_POLL_MAX = POLL_MAX_MINUTES * 60 // POLL_INTERVAL_S
MOD_RETRY_MAX = 5              # kiểm duyệt đầu ra → đổi seed render lại (block bill 0 token)
HEAL_MAX = 2                  # bị chặn INPUT người-thật → chuyển ref sang asset:// (≤2 pass)

_PRIVACY_KW = ("real person", "may contain real", "portrait", "face", "privacy",
               "sensitive", "inputimage", "inputvideo")
_MOD_KW = ("moderat", "risk control", "output_video")


def _looks_privacy(msg: str) -> bool:
    return any(k in msg for k in _PRIVACY_KW)


def _looks_output_mod(msg: str) -> bool:
    return any(k in msg for k in _MOD_KW)


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


def _reference_specs(params: dict, owner_id: str, storage) -> list[dict]:
    """Normalize legacy form refs and typed Canvas inputs behind one owner gate."""
    raw = [dict(item) for item in (params.get("refs") or []) if isinstance(item, dict)]
    typed = (("image_key", "image"), ("video_key", "video"),
             ("audio_key", "audio"))
    for field, kind in typed:
        if params.get(field):
            raw.append({"storage_key": params[field], "kind": kind})
    for key in params.get("image_keys") or []:
        raw.append({"storage_key": key, "kind": "image"})
    clean: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        key = str(item.get("storage_key") or "").strip()
        kind = str(item.get("kind") or "image").strip()
        parts = key.split("/")
        if kind not in {"image", "video", "audio"}:
            raise ValueError(_t('Loại tài nguyên tham chiếu không hợp lệ.'))
        if len(parts) < 3 or parts[1] != owner_id:
            raise ValueError(_t('Tài nguyên tham chiếu không thuộc người dùng.'))
        if not storage.exists(key):
            raise ValueError(_t('Tài nguyên tham chiếu không còn tồn tại.'))
        if key in seen:
            continue
        seen.add(key)
        clean.append({"storage_key": key, "kind": kind,
                      "role": str(item.get("role") or
                                  ("reference_image" if kind == "image" else f"reference_{kind}")),
                      "handle": str(item.get("handle") or "")})
    if len(clean) > 4:
        raise ValueError(_t('Một video chỉ nhận tối đa 4 tài nguyên tham chiếu.'))
    return clean


def _luu_task_id(job_id: str, task_id: str) -> None:
    """Lưu remote task_id vào job.params NGAY sau khi submit ModelArk — để lần chạy lại
    (worker chết/orphan) POLL lại task cũ thay vì submit MỚI (chống double-bill provider)."""
    if not job_id or job_id == "adhoc" or not task_id:
        return
    try:
        from platform_core.db import get_session
        from platform_core.models import Job
        gen = get_session(); db = next(gen)
        try:
            j = db.get(Job, job_id)
            if j is not None:
                p = dict(j.params or {}); p["_remote_task_id"] = task_id
                j.params = p; db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:  # noqa: BLE001
        pass


def handle(params: dict, ctx=None) -> dict:
    prompt = str(params.get("prompt", "")).strip()
    if not prompt:
        raise ValueError(_t('Chưa nhập mô tả video.'))
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
        return {"video_key": vkey, "credit_cost": cost.customer_charge_cap(params)}

    # Refs (Pha 2): ảnh ≤8MB → inline (Pillow); ảnh >8MB / video / audio → asset://
    # (R2 temp presigned → ModelArk CreateAsset). Giữ `data` để heal người-thật sau.
    ref_items = []
    has_video_input = False
    for rs in _reference_specs(params, owner_id, storage):
        if ctx is not None:                 # heartbeat: to_asset có thể mất ~200s/ref
            ctx.progress(3, "chuẩn bị tài nguyên tham chiếu…")
        kind = (rs.get("kind") or "image").strip()
        skey = (rs.get("storage_key") or "").strip()
        if not skey:
            continue
        data = storage.open(skey).read()
        role = rs.get("role") or "reference_image"
        handle = rs.get("handle") or ""
        if kind == "image":
            try:
                url = refs.image_to_inline(data)
            except refs.RefError:
                url = assets.to_asset("image", data)       # >8MB → asset://
        else:                                              # video/audio → asset://
            ext = ".mp4" if kind == "video" else ".m4a"
            url = assets.to_asset(kind, data, ext)
            if kind == "video":
                has_video_input = True
        ref_items.append({"kind": kind, "url": url, "role": role,
                          "handle": handle, "data": data})

    def _content():
        return refs.build_content(prompt, [{"kind": it["kind"], "url": it["url"],
                                            "role": it["role"], "handle": it["handle"]}
                                           for it in ref_items])

    def _heal(faces_only: bool) -> int:
        n = 0
        for it in ref_items:
            if it["kind"] != "image" or it["url"].startswith("asset://"):
                continue
            if faces_only and not assets.has_face(it["data"]):
                continue
            if ctx is not None:             # heartbeat: to_asset chậm, tránh false-orphan
                ctx.progress(6, "bảo vệ ảnh người thật…")
            try:
                it["url"] = assets.to_asset("image", it["data"])
                n += 1
            except Exception as e:  # noqa: BLE001
                pass
        return n

    content = _content()
    api_key, key_id = _lay_key()
    if not api_key:
        raise RuntimeError(_t('Chưa có API key BytePlus (thêm ở /admin → APIKEYS).'))

    endpoint = models.provider_model(model)
    try:
        seed = int(params["seed"]) if params.get("seed") is not None else None
    except (TypeError, ValueError):
        seed = None
    if seed is not None and not 0 <= seed <= 2_147_483_647:
        seed = None
    result = None
    mod_try = heal_stage = 0

    # Chống DOUBLE-BILL: lần chạy trước (crash/orphan) có thể đã submit task rồi. Poll
    # lại task đó tới khi xong thay vì submit MỚI. Chỉ submit mới nếu task cũ hỏng/hết hạn.
    resumed = (params.get("_remote_task_id") or "").strip()
    if resumed:
        try:
            for i in range(_POLL_MAX):
                if ctx is not None:
                    ctx.progress(min(90, 10 + int(i * 80 / _POLL_MAX)), "tiếp tục dựng video…")
                time.sleep(POLL_INTERVAL_S)
                try:
                    st = modelark.poll(api_key, resumed)
                except modelark.ModelArkError:
                    break
                if st["status"] == "succeeded":
                    result = st; break
                if st["status"] in ("failed", "expired", "cancelled"):
                    break
        except Exception:  # noqa: BLE001
            pass

    while result is None:
        if ctx is not None:
            ctx.progress(5, "gửi yêu cầu tạo video")
        err = None
        task_id = None
        try:
            task_id = modelark.submit(
                api_key, model_endpoint=endpoint, content=content,
                resolution=resolution, duration=duration, aspect_ratio=aspect,
                generate_audio=audio, seed=seed)
            _luu_task_id(job_id, task_id)   # persist NGAY để retry poll lại, không submit mới
        except modelark.ModelArkError as e:
            err = str(e).lower()
            if not (e.status_code == 400 and _looks_privacy(err)):
                _ket_qua_key(key_id, thanh_cong=False, last_status=e.status_code)
                raise

        if task_id is not None:
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
            err = (st_final.get("error") or "").lower()

        # Bị chặn INPUT người-thật → chuyển ref sang asset:// rồi gửi lại (≤2 pass).
        if err and _looks_privacy(err) and heal_stage < HEAL_MAX and \
                any(it["kind"] == "image" and not it["url"].startswith("asset://") for it in ref_items):
            if ctx is not None:
                ctx.progress(6, "bảo vệ ảnh người thật (asset://)…")
            n = _heal(faces_only=(heal_stage == 0))
            heal_stage += 1
            if n > 0:
                content = _content()
                continue
        # Kiểm duyệt ĐẦU RA → đổi seed render lại (block bill 0 token).
        if err and _looks_output_mod(err) and mod_try < MOD_RETRY_MAX:
            mod_try += 1
            seed = random.randint(1, 2_147_483_647)
            continue
        _ket_qua_key(key_id, thanh_cong=False)
        raise RuntimeError(f"Tạo video thất bại: {err or 'không rõ'}")

    if ctx is not None:
        ctx.progress(92, "tải video về")
    if not result.get("video_url"):
        raise RuntimeError(_t('Provider không trả URL video.'))
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
            "refs": len(ref_items), "seed": seed}
