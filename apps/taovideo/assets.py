"""
assets.py — pipeline asset:// cho ModelArk (seedance Pha 2b). Di trú trung thành từ
`adapters/modelark_asset_adapter.py` + `face_detect.py`.

Dùng cho: ảnh > 8MB, video/audio tham chiếu, và "heal" ảnh người-thật khi ModelArk
chặn INPUT. Luồng: PUT file tạm lên R2 (private) → presigned GET 1h → volcengine
CreateAsset (ModelArk fetch + copy về TOS, kiểm duyệt tại đây) → poll GetAsset tới
Active → `asset://<id>` → xoá file tạm R2.

Ký AK/SK bằng volcengine SignerV4 (BytePlus OpenAPI, KHÁC S3). Creds ở env
`LTT_MODELARK_ACCESS_KEY/SECRET_KEY/REGION` (nhập từ BOT GEMINI). Nhận diện mặt
dùng opencv Haar (insightface cần MSVC — tạm Haar, đủ để quyết định heal).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid

log = logging.getLogger("ltt.taovideo.assets")

HOST = "open.byteplusapi.com"
SERVICE = "ark"
_SHARED_GROUP_NAME = "ltt_seedance_aigc"
_shared_group_id = None
_group_lock = threading.Lock()
_create_lock = threading.Lock()
_create_last = 0.0
_CREATE_MIN_INTERVAL = 3.0
_CREATE_MAX_RETRY = 6

_ST_PROCESSING = ("process", "pending", "wait", "creat", "queue", "audit", "review", "run")
_ST_FAILED = ("fail", "reject", "illegal", "error", "block", "forbid", "violat", "denied", "expire")


class AssetError(RuntimeError):
    pass


def _creds():
    ak = (os.environ.get("LTT_MODELARK_ACCESS_KEY") or "").strip()
    sk = (os.environ.get("LTT_MODELARK_SECRET_KEY") or "").strip()
    region = (os.environ.get("LTT_MODELARK_REGION") or "ap-southeast-1").strip()
    if not (ak and sk):
        raise AssetError("Chưa có ModelArk AK/SK (LTT_MODELARK_*).")
    return ak, sk, region


def _err(d: dict) -> str:
    e = ((d.get("ResponseMetadata") or {}).get("Error")) or d.get("error") or {}
    if isinstance(e, dict):
        return f"{e.get('Code') or e.get('code') or ''}: {e.get('Message') or e.get('message') or ''}".strip(": ") or str(d)[:200]
    return str(d)[:200]


def _signed_api(action: str, version: str, body: dict, *, timeout: float = 30.0):
    """BytePlus OpenAPI call ký SignerV4 (volcengine SDK)."""
    import requests
    from volcengine.auth.SignerV4 import SignerV4
    from volcengine.base.Request import Request
    from volcengine.Credentials import Credentials
    ak, sk, region = _creds()
    r = Request()
    r.set_shema("https")
    r.set_method("POST")
    r.set_connection_timeout(10)
    r.set_socket_timeout(timeout)
    r.set_headers({"Accept": "application/json", "Content-Type": "application/json", "Host": HOST})
    r.set_query({"Action": action, "Version": version})
    r.set_host(HOST)
    r.set_path("/")
    r.set_body(json.dumps(body))
    SignerV4.sign(r, Credentials(ak, sk, SERVICE, region))
    resp = requests.post(f"https://{HOST}/", params={"Action": action, "Version": version},
                         headers=dict(r.headers), data=r.body, timeout=timeout + 5)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text[:400]}


def _list_groups() -> list:
    out, page = [], 1
    while len(out) < 500:
        try:
            code, d = _signed_api("ListAssetGroups", "2024-01-01",
                                  {"Filter": {"GroupType": "AIGC"}, "PageNumber": page, "PageSize": 100})
        except Exception:
            return []
        if code != 200 or ((d.get("ResponseMetadata", {}) or {}).get("Error")):
            return []
        r = d.get("Result") or {}
        items = r.get("Items") or []
        out += [{"id": it.get("Id"), "name": it.get("Name")} for it in items]
        if len(items) < 100 or len(out) >= int(r.get("TotalCount") or 0):
            break
        page += 1
    return out


def _shared_group() -> str:
    global _shared_group_id
    if _shared_group_id:
        return _shared_group_id
    with _group_lock:
        if _shared_group_id:
            return _shared_group_id
        for g in _list_groups():
            if g.get("name") == _SHARED_GROUP_NAME and g.get("id"):
                _shared_group_id = g["id"]
                return _shared_group_id
        c, r = _signed_api("CreateAssetGroup", "2024-01-01",
                           {"Name": _SHARED_GROUP_NAME, "GroupType": "AIGC"})
        gid = (r.get("Result") or {}).get("Id")
        if c != 200 or not gid:
            raise AssetError(f"CreateAssetGroup: {_err(r)}")
        _shared_group_id = gid
        return gid


def _create_asset(gid: str, asset_type: str, name: str, url: str):
    global _create_last
    c, r = 0, {}
    for attempt in range(_CREATE_MAX_RETRY + 1):
        with _create_lock:
            wait = _CREATE_MIN_INTERVAL - (time.time() - _create_last)
            if wait > 0:
                time.sleep(wait)
            c, r = _signed_api("CreateAsset", "2024-01-01",
                               {"GroupId": gid, "AssetType": asset_type, "Name": name, "URL": url})
            _create_last = time.time()
        if c == 200:
            return r
        msg = _err(r)
        if ("QPM" in msg or "rate limit" in msg.lower() or "QuotaWrite" in msg) and attempt < _CREATE_MAX_RETRY:
            time.sleep(min(2.0 * (2 ** attempt), 15.0))
            continue
        raise AssetError(f"CreateAsset: {msg}")
    raise AssetError("CreateAsset: hết lần thử")


def _wait_active(asset_id: str, timeout: float = 180.0) -> None:
    t0, last = time.time(), ""
    while time.time() - t0 < timeout:
        c, r = _signed_api("GetAsset", "2024-01-01", {"Id": asset_id}, timeout=20)
        st = str((r.get("Result") or {}).get("Status") or "").lower()
        if c == 200 and st:
            last = st
            if any(k in st for k in _ST_FAILED):
                raise AssetError(f"Asset bị từ chối/kiểm duyệt (status={st})")
            if not any(k in st for k in _ST_PROCESSING):
                return
        time.sleep(6)
    raise AssetError(f"Asset chưa sẵn sàng sau {int(timeout)}s (status={last or '?'})")


def _delete_asset(asset_id: str) -> None:
    try:
        _signed_api("DeleteAsset", "2024-01-01", {"Id": asset_id}, timeout=20)
    except Exception:
        pass


def to_asset(kind: str, data: bytes, ext: str = ".png") -> str:
    """Đưa 1 ảnh/video (bytes) thành `asset://<id>` dùng được trong body ModelArk.

    Host tạm = R2 (qua platform storage) presigned 1h → CreateAsset → wait Active →
    xoá temp. Cần storage R2 (dev Local không có presigned → raise)."""
    from platform_core.storage import get_storage
    import io
    storage = get_storage()
    tmp_key = f"sdv-tmp/{uuid.uuid4().hex}{ext}"
    storage.put(tmp_key, io.BytesIO(data),
                content_type="video/mp4" if kind == "video" else "image/png")
    try:
        url = storage.url_for(tmp_key, ttl_s=3600)
        if not url:
            raise AssetError("Cần R2 (presigned) cho asset:// — Local không hỗ trợ.")
        gid = _shared_group()
        asset_type = "Video" if kind == "video" else "Image"
        r = _create_asset(gid, asset_type, f"ltt_{uuid.uuid4().hex[:8]}", url)
        aid = (r.get("Result") or {}).get("Id")
        if not aid:
            raise AssetError(f"CreateAsset không trả Id ({str(r)[:150]})")
        _wait_active(aid)
        return f"asset://{aid}"
    finally:
        try:
            storage.delete(tmp_key)
        except Exception:
            pass


# ── Nhận diện mặt (opencv Haar; insightface cần MSVC — dùng Haar) ─────────────
_haar = None
_haar_lock = threading.Lock()


def _get_haar():
    global _haar
    if _haar is not None:
        return _haar
    with _haar_lock:
        if _haar is None:
            import cv2
            _haar = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return _haar


def has_face(data: bytes) -> bool:
    """True nếu ảnh có mặt người (để quyết định heal → asset://). Lỗi → False."""
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        h, w = img.shape[:2]
        if max(h, w) > 2000:
            sc = 2000.0 / max(h, w)
            img = cv2.resize(img, (int(w * sc), int(h * sc)))
        cas = _get_haar()
        faces = cas.detectMultiScale(img, scaleFactor=1.1, minNeighbors=9,
                                     minSize=(max(8, img.shape[0] // 12),) * 2)
        return len(faces) > 0
    except Exception:
        return False
