"""
http_cong.py — đường HTTP thật tới cổng render trên máy B.

Tách khỏi `jobs.py` để test của app chạy được mà không chạm mạng: `jobs.py` chỉ
biết một hàm `goi(method, path, json=..., timeout=...)`.

⛔ Bearer token lấy qua `api_pool` như mọi provider khác — **không** đọc từ biến
   môi trường của máy A. Khoá nằm trong APIKEYS, xoay vòng và ghi telemetry ở đó.

⚠️ KHÔNG gọi mạng bên trong một transaction CSDL. Lấy khoá trong một phiên ngắn,
   đóng phiên, gọi HTTP, rồi mở một phiên ngắn khác để ghi kết quả. Giữ phiên mở
   suốt lượt gọi là giữ khoá CSDL trong lúc chờ máy B — và một lượt vẽ có thể lâu.
"""
from __future__ import annotations

from typing import Callable

PROVIDER = "ltt_image"


def _voi_db(ham):
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        kq = ham(db)
        db.commit()
        return kq
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def goi_http(base_url: str) -> Callable:
    base = (base_url or "").rstrip("/")

    def goi(method: str, path: str, *, json=None, timeout: float = 30.0):
        import httpx

        from platform_core import api_keys, api_pool
        from platform_core.models import APIKEY_CAT_IMAGE

        def lay(db):
            key = api_pool.lay_key(db, PROVIDER, category=APIKEY_CAT_IMAGE)
            return key.id, api_keys.lay_credential(db, key)

        key_id, cred = _voi_db(lay)

        try:
            r = httpx.request(method, f"{base}{path}",
                              headers={"Authorization": f"Bearer {cred}"},
                              json=json, timeout=timeout)
        except Exception as e:
            _ghi(key_id, None, str(e)[:300])
            raise

        try:
            than = r.json()
        except ValueError:
            than = {"_raw": r.text[:400]}

        # ⛔ 429 = BAN, khong phai HONG. KHONG danh dau loi: `api_pool` se cooldown
        #    roi `disable` sau 5 lan — nghia la mot toi chay video ben du an kia se
        #    TU TAT vinh vien model nha. Canh bao nay nam thuong truc o CLAUDE.md.
        if r.status_code != 429:
            _ghi(key_id, r.status_code, str(than)[:300])
        return r.status_code, than

    return goi


def _ghi(key_id: str, http_status, message: str) -> None:
    """Ghi kết quả một lượt gọi. `http_status=None` nghĩa là lỗi mạng.

    Truyền `None` chứ **không** gán bừa một mã HTTP: `api_pool` phân nhánh theo
    mã, và một mã bịa ra sẽ đẩy key sang nhánh phạt sai.
    """
    from platform_core import api_pool
    from platform_core.models import ApiKey

    def ghi(db):
        key = db.get(ApiKey, key_id)
        if key is None:
            return
        if http_status is not None and http_status < 400:
            api_pool.danh_dau_thanh_cong(db, key)
        else:
            api_pool.danh_dau_loi(db, key, http_status=http_status, message=message)

    _voi_db(ghi)
