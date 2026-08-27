"""
luong_vlm.py — mở một luồng SSE tới model nhà, và **chuyển tiếp nguyên xi**. (Q107, C6)

⭐ VÌ SAO TÁCH KHỎI `dieu_phoi`. `dieu_phoi.goi()` là **bộ điều phối nhiều nhà
   cung cấp**: nó thử `ltt_llm`, bận thì đi tiếp sang Gemini, hỏng thì đánh dấu
   lỗi cho khoá. Cascade đó chỉ có nghĩa khi ta **giữ trọn** câu trả lời rồi mới
   giao — thử nhà thứ hai sau khi đã giao nửa câu trả lời của nhà thứ nhất là
   giao hai nửa của hai model khác nhau.

   Streaming thì giao ngay từ byte đầu. Nên ở đây **không cascade**, và điều đó
   khớp đúng với `features.THU_TU_PROVIDER = ("ltt_llm",)`: hàng bán ra ngoài
   không được đổi model giữa chừng (D-010).

⛔ KHÔNG PHÂN TÍCH RỒI DỰNG LẠI SSE. Lớp này chuyển byte, không dịch. Việc nhìn
   qua để đếm token là của `dem_token_luong`, và nó cũng chỉ **nhìn**.

⛔ BẬN KHÔNG PHẢI HỎNG. Máy B trả 429 khi việc ảnh hoặc video đang giữ card. Đánh
   dấu lỗi cho khoá lúc đó thì `api_pool` cooldown rồi `disable` sau 5 lần, và
   một tối chạy video sẽ **tự tắt vĩnh viễn model nhà** (D-005).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Optional

log = logging.getLogger("platform_core.llm.luong_vlm")

#: Provider duy nhất phục vụ streaming hôm nay.
PROVIDER = "ltt_llm"


class KhongMoDuocLuong(Exception):
    """Không mở được luồng. Bên gọi dịch sang 502/503 tuỳ `ban`."""

    def __init__(self, ly_do: str, *, ban: bool = False,
                 qua_dai: bool = False, thu_lai_sau_s: int = 30):
        super().__init__(ly_do)
        self.ly_do = ly_do
        self.ban = ban
        #: Đầu vào vượt trần token của máy B (413) — lỗi CLIENT (ngữ cảnh quá
        #: dài), KHÔNG phải hỏng tạm. Bên gọi phải trả 413 để client NÉN hội
        #: thoại, KHÔNG được dịch thành 503 (retry vô ích → bão).
        self.qua_dai = qua_dai
        self.thu_lai_sau_s = thu_lai_sau_s


@dataclass
class LuongMo:
    ma: int
    content_type: str
    luong: Iterator[bytes]
    #: Khoá đã dùng — bên gọi báo lại kết quả qua `xong()` / `hong()`.
    _db: Any = None
    _key: Any = None
    _da_bao: bool = False

    def xong(self, tokens: int = 0) -> None:
        """Luồng kết thúc bình thường. Nuôi telemetry tpm của H8 Pha 2."""
        if self._da_bao or self._key is None:
            return
        self._da_bao = True
        try:
            from platform_core import api_pool

            api_pool.danh_dau_thanh_cong(self._db, self._key, tokens=tokens)
        except Exception as exc:                                # noqa: BLE001
            log.info("khong danh dau duoc thanh cong cho khoa: %s",
                     type(exc).__name__)

    def hong(self, exc: BaseException) -> None:
        """Luồng vỡ **vì thượng nguồn**, không phải vì khách bỏ đi.

        ⛔ Bên gọi phải phân biệt hai thứ đó. Khách đóng kết nối là chuyện bình
           thường và **không** phải lỗi của khoá; đánh dấu lỗi cho nó là đường
           thẳng tới D-005.
        """
        if self._da_bao or self._key is None:
            return
        self._da_bao = True
        try:
            from platform_core import api_pool

            api_pool.danh_dau_loi(self._db, self._key, message=type(exc).__name__)
        except Exception as e:                                  # noqa: BLE001
            log.info("khong danh dau duoc loi cho khoa: %s", type(e).__name__)


def mo(db, *, duong: str, than: dict, timeout_s: float = 900.0) -> LuongMo:
    """Mở luồng tới model nhà. `duong` là `/v1/messages` hoặc `/v1/responses`.

    ⚠️ **Chưa đọc byte nào khi hàm này trả về.** Nó chỉ chắc rằng thượng nguồn đã
       nhận và trả header. Việc đó vẫn có thể mất hàng chục giây khi `llama-swap`
       phải nạp lại model — nên bên gọi **phải** phát nhịp tim trước khi gọi vào
       đây, không phải sau (xem C1b của lộ trình).
    """
    from platform_core import api_keys, api_pool, providers
    from platform_core.models import APIKEY_CAT_CHAT

    try:
        key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                                model=str(than.get("model") or "") or None,
                                thu_tu_provider=[PROVIDER])
    except Exception as e:                                      # noqa: BLE001
        raise KhongMoDuocLuong(
            f"khong cap duoc khoa cho {PROVIDER} ({type(e).__name__})") from None

    credential = api_keys.lay_credential(db, key)
    prov = providers.get(PROVIDER)
    # `base_url` của KHOÁ đi trước của registry — cùng lý do đã ghi trong
    # `dieu_phoi.goi`: registry đọc biến môi trường, mà biến đó vắng mặt trong
    # một script chạy tay và làm mọi thứ trông như "máy B chết".
    base = (getattr(key, "base_url", "") or "").strip() \
        or (getattr(prov, "base_url", "") or "").strip()
    if not base:
        # Thiếu cấu hình, KHÔNG phải provider hỏng. Đừng đánh dấu lỗi cho khoá.
        raise KhongMoDuocLuong("thieu base_url (ca o khoa lan o registry)")

    import httpx

    client = httpx.Client(timeout=timeout_s)
    try:
        ctx = client.stream("POST", base.rstrip("/") + duong, json=than,
                            headers={"Authorization": f"Bearer {credential}"})
        r = ctx.__enter__()
    except httpx.HTTPError as e:
        client.close()
        api_pool.danh_dau_loi(db, key, message=type(e).__name__)
        raise KhongMoDuocLuong(f"khong noi duoc toi may B ({type(e).__name__})") from None

    if r.status_code == 429:
        # ⛔ BẬN ≠ HỎNG (D-005). Không đánh dấu lỗi cho khoá.
        than_loi = _doc_het(r, ctx, client)
        raise KhongMoDuocLuong("may B dang ban", ban=True,
                               thu_lai_sau_s=_retry_after(r))
    if r.status_code >= 400:
        than_loi = _doc_het(r, ctx, client)
        if r.status_code == 413:
            # Đầu vào vượt trần token của máy B (LTT_LLM_MAX_INPUT_TOKENS). Lỗi
            # CLIENT, không phải hỏng: đánh dấu `qua_dai` để bên gọi trả 413 và
            # client tự nén hội thoại. Từng bị dịch nhầm sang 503 → Codex retry
            # → bão, và khách thấy "im lặng" ở phản hồi/hội thoại dài (đo 27/08).
            raise KhongMoDuocLuong(
                f"may B tra 413: {than_loi[:200]}", qua_dai=True)
        if r.status_code >= 500:
            api_pool.danh_dau_loi(db, key, message=f"HTTP {r.status_code}")
        raise KhongMoDuocLuong(
            f"may B tra {r.status_code}: {than_loi[:200]}")

    def _di() -> Iterator[bytes]:
        try:
            for khoi in r.iter_raw():
                yield khoi
        finally:
            try:
                ctx.__exit__(None, None, None)
            finally:
                client.close()

    return LuongMo(ma=r.status_code,
                   content_type=r.headers.get("content-type", "text/event-stream"),
                   luong=_di(), _db=db, _key=key)


def _doc_het(r, ctx, client) -> str:
    try:
        return b"".join(r.iter_raw()).decode("utf-8", "replace")
    except Exception:                                           # noqa: BLE001
        log.info("khong doc duoc than loi cua thuong nguon")
        return ""
    finally:
        try:
            ctx.__exit__(None, None, None)
        finally:
            client.close()


def _retry_after(r) -> int:
    try:
        return max(1, int(r.headers.get("retry-after") or 30))
    except (TypeError, ValueError):
        return 30
