"""http_cong.py — đường HTTP thật tới cổng render trên máy B (LTT_IMAGE).

🔴 NÂNG LÊN NỀN TẢNG 09/09/2026 — AI CLEAN REBUILD V2 pha 06.2.
   Thân mã nguyên gốc ở `apps/anhnoibo/http_cong.py`; tệp ấy nay **trỏ về
   đây**, nên `anhnoibo` không đổi một dòng.

   Lý do nâng: `taoanh` (và `thumbnail` ở 06.3) di trú sang LTT_IMAGE cũng
   cần đúng đường này, mà `.importlinter` cấm app import app. Đây là lần
   **thứ tư** trong chiến dịch một thứ phải lên `platform_core` vì nhiều
   app cùng cần và một contract chặn — ba lần trước: `canonical`,
   `tai_nguyen_nha`, `loi_ra_ngoai`.

⛔ Bearer token lấy qua `api_pool` như mọi provider khác — **không** đọc từ
   biến môi trường của máy A. Khoá nằm trong APIKEYS, xoay vòng và ghi
   telemetry ở đó.

⚠️ KHÔNG gọi mạng bên trong một transaction CSDL. Lấy khoá trong một phiên
   ngắn, đóng phiên, gọi HTTP, rồi mở một phiên ngắn khác để ghi kết quả.
   Giữ phiên mở suốt lượt gọi là giữ khoá CSDL trong lúc chờ máy B — và một
   lượt vẽ có thể lâu.
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

        def lay(db, bo_qua):
            # ⭐ Thử lần lượt các khoá, KHÔNG bao giờ quay lại khoá vừa hỏng.
            #    Hôm nay cổng render chỉ có một khoá, nên vòng này chạy đúng một
            #    lượt. Nó có mặt vì ngày thêm khoá thứ hai thì không ai phải nhớ
            #    quay lại sửa chỗ này — và vì khoá **đầu tiên** cũng hỏng được.
            for key in api_pool.thu_lan_luot(db, provider=PROVIDER,
                                             category=APIKEY_CAT_IMAGE,
                                             so_lan=1 + len(bo_qua)):
                if key.id in bo_qua:
                    continue
                return key.id, api_keys.lay_credential(db, key)
            return None, None

        da_hong: list[str] = []
        while True:
            key_id, cred = _voi_db(lambda db: lay(db, da_hong))
            if key_id is None:
                from platform_core.api_pool import ThieuKeyError
                raise ThieuKeyError(
                    "het khoa kha dung cho cong render (da thu "
                    f"{len(da_hong)} khoa)")
            try:
                r = httpx.request(method, f"{base}{path}",
                                  headers={"Authorization": f"Bearer {cred}"},
                                  json=json, timeout=timeout)
            except Exception as e:
                _ghi(key_id, None, str(e)[:300])
                # Lỗi mạng: máy B có thể đang khởi động lại. Đổi khoá không chữa
                # được chuyện đó, nên ném ra thay vì thử lại một cách vô ích.
                raise
            # ⛔ 401/403 = khoá này sai, khoá khác có thể đúng ⇒ ĐÁNG thử lại.
            #    Mọi mã khác — kể cả 429 — thì đổi khoá không giúp gì: 429 nghĩa là
            #    MÁY bận, không phải khoá bận.
            if r.status_code in (401, 403) and key_id not in da_hong:
                _ghi(key_id, r.status_code, "cong render tu choi khoa nay")
                da_hong.append(key_id)
                continue
            break

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
