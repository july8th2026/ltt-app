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
from typing import Any, Callable, Iterator, Optional

from platform_core.llm.model_failure import ModelFailure, decode_gateway_failure, model_failure

log = logging.getLogger("platform_core.llm.luong_vlm")

#: Provider duy nhất phục vụ streaming hôm nay.
PROVIDER = "ltt_llm"


class KhongMoDuocLuong(Exception):
    """Không mở được luồng. Bên gọi dịch sang 502/503 tuỳ `ban`."""

    def __init__(
        self,
        ly_do: str = "",
        *,
        failure: Optional[ModelFailure] = None,
        ban: bool = False,
        qua_dai: bool = False,
        het_gio: bool = False,
        thu_lai_sau_s: int = 30,
    ):
        if failure is None:
            code = (
                "concurrency_limited"
                if ban
                else "context_window_exceeded"
                if qua_dai
                else "upstream_timeout"
                if het_gio
                else "upstream_unknown"
            )
            status = 429 if ban else 413 if qua_dai else 504 if het_gio else 502
            failure = model_failure(
                code,
                http_status=status,
                retry_after_s=thu_lai_sau_s if ban else None,
            )
        super().__init__(ly_do or failure.message)
        self.failure = failure
        self.ly_do = ly_do or failure.message
        self._ban_legacy = bool(ban)
        self._qua_dai_legacy = bool(qua_dai)
        self._het_gio_legacy = bool(het_gio)
        #: Máy B nhận yêu cầu nhưng không trả lời kịp (cổng trả 504).
        #:
        #: ⛔ KHÁC `ban`, và khác một cách quan trọng. `ban` nói *"thử lại sau
        #:    30 giây thì được"*; `het_gio` **không** hứa điều đó — một yêu cầu
        #:    hết giờ vì nó quá lớn sẽ hết giờ y hệt ở lần sau.
        #:
        #: ⛔ Và khác cả hai ở chỗ quan trọng nhất: **không** `danh_dau_loi`.
        #:    Prefill 200K mất hàng phút là công việc hằng ngày của hệ này, chứ
        #:    không phải dấu hiệu khoá hỏng.
        #: Đầu vào vượt trần token của máy B (413) — lỗi CLIENT (ngữ cảnh quá
        #: dài), KHÔNG phải hỏng tạm. Bên gọi phải trả 413 để client NÉN hội
        #: thoại, KHÔNG được dịch thành 503 (retry vô ích → bão).
        self.thu_lai_sau_s = int(failure.retry_after_s or thu_lai_sau_s)

    @property
    def ban(self) -> bool:
        return self._ban_legacy or self.failure.is_busy

    @property
    def qua_dai(self) -> bool:
        return self._qua_dai_legacy or self.failure.is_context_limit

    @property
    def het_gio(self) -> bool:
        return self._het_gio_legacy or self.failure.is_timeout


@dataclass
class LuongMo:
    ma: int
    content_type: str
    luong: Iterator[bytes]
    #: Đóng cửa ra mạng của lượt này — gọi được từ LUỒNG KHÁC, và idempotent.
    #: Đường huỷ của cửa stream cần nó vì `luong.close()` ném
    #: `ValueError: generator already executing` khi luồng đọc còn đang chạy.
    #: Xem `_dong_thuong_nguon` và mục L-08 trong `SO_LOI_DO_TAI.md`.
    dong_nguon: Optional[Callable[[], None]] = None
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
        except Exception as exc:  # noqa: BLE001
            log.info("khong danh dau duoc thanh cong cho khoa: %s", type(exc).__name__)

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
        except Exception as e:  # noqa: BLE001
            log.info("khong danh dau duoc loi cho khoa: %s", type(e).__name__)


#: Dấu hiệu của **đúng một lớp lỗi**: parser tool-call của llama.cpp vỡ.
#:
#: ⛔ PHẢI HẸP. Thử lại một lỗi thật của hạ tầng (hết VRAM, model chết, cấu hình
#:    sai) chỉ đốt GPU thêm một lượt rồi hỏng y hệt, và giấu mất triệu chứng.
#:    Ba chuỗi này lấy từ thông điệp THẬT máy B trả về (đo 29-30/08), không đoán:
#:      "Failed to parse tool call arguments as JSON: [json.exception.parse_error.101]"
#:      "unparsed peg-native output"
#:      "Failed to parse input at pos"
_DAU_HIEU_PARSER = (
    "failed to parse tool call",
    "peg-native",
    "failed to parse input at pos",
)


def _loi_parser_tool_call(than_loi: str) -> bool:
    """Thân lỗi có phải do parser tool-call vỡ không (chứ không phải hỏng thật)."""
    thap = (than_loi or "").lower()
    return any(d in thap for d in _DAU_HIEU_PARSER)


def la_het_gio_doc(exc: BaseException) -> bool:
    """Máy B nhận kết nối nhưng im quá hạn đọc (`httpx.ReadTimeout`) — C0-34.

    Đó là NGHẼN (lượt khác đang giữ card, prefill dài), không phải khoá hỏng:
    **không** `danh_dau_loi`. ⛔ Hẹp có chủ ý: `ConnectTimeout`/`ConnectError`
    (máy B không với tới) vẫn là hỏng thật và vẫn phạt như cũ.
    """
    import httpx

    return isinstance(exc, httpx.ReadTimeout)


def mo(
    db,
    *,
    duong: str,
    than: dict,
    timeout_s: float = 900.0,
    request_id: str = "",
    token_dat_truoc: int = 0,
    _da_thu_lai: bool = False,
) -> LuongMo:
    """Mở luồng tới model nhà. `duong` là `/v1/messages` hoặc `/v1/responses`.

    ⚠️ **Chưa đọc byte nào khi hàm này trả về.** Nó chỉ chắc rằng thượng nguồn đã
       nhận và trả header. Việc đó vẫn có thể mất hàng chục giây khi `llama-swap`
       phải nạp lại model — nên bên gọi **phải** phát nhịp tim trước khi gọi vào
       đây, không phải sau (xem C1b của lộ trình).
    """
    from platform_core import api_keys, api_pool, providers
    from platform_core.models import APIKEY_CAT_CHAT

    try:
        key = api_pool.chon_key(
            db,
            category=APIKEY_CAT_CHAT,
            model=str(than.get("model") or "") or None,
            thu_tu_provider=[PROVIDER],
        )
    except Exception as e:  # noqa: BLE001
        failure = model_failure("internal_error", http_status=503, request_id=request_id)
        raise KhongMoDuocLuong(
            f"khong cap duoc khoa cho {PROVIDER} ({type(e).__name__})", failure=failure
        ) from None

    credential = api_keys.lay_credential(db, key)
    prov = providers.get(PROVIDER)
    # `base_url` của KHOÁ đi trước của registry — cùng lý do đã ghi trong
    # `dieu_phoi.goi`: registry đọc biến môi trường, mà biến đó vắng mặt trong
    # một script chạy tay và làm mọi thứ trông như "máy B chết".
    base = (getattr(key, "base_url", "") or "").strip() or (
        getattr(prov, "base_url", "") or ""
    ).strip()
    if not base:
        # Thiếu cấu hình, KHÔNG phải provider hỏng. Đừng đánh dấu lỗi cho khoá.
        raise KhongMoDuocLuong(
            "thieu base_url (ca o khoa lan o registry)",
            failure=model_failure("internal_error", http_status=503, request_id=request_id),
        )

    import httpx

    headers = {"Authorization": f"Bearer {credential}"}
    if request_id:
        headers["X-LTT-Request-Id"] = str(request_id)
    if int(token_dat_truoc or 0) > 0:
        headers["X-LTT-Token-Dat"] = str(int(token_dat_truoc))
    # 🔴 `X-LTT-Whale` ĐÃ GỠ (phương án C, O-01, 17/09/2026): máy B là rào vật lý,
    #    không còn luật whale riêng (bước 3). Máy A là nơi DUY NHẤT quyết định
    #    công bằng prefill (`luat_nhan` luật 5).

    client = httpx.Client(timeout=timeout_s)
    try:
        ctx = client.stream("POST", base.rstrip("/") + duong, json=than, headers=headers)
        r = ctx.__enter__()
    except httpx.HTTPError as e:
        client.close()
        if la_het_gio_doc(e):
            # 🔴 C0-34 (20/09): máy B đã nhận kết nối nhưng không trả header kịp
            #    = đang nghẽn, KHÔNG phải khoá hỏng. Cùng lý do nhánh 504 bên
            #    dưới: phạt ở đây là năm lượt nghẽn liền nhau tắt khoá DUY NHẤT
            #    của `ltt_llm` (sự cố khoá pool 19/09).
            raise KhongMoDuocLuong(
                f"may B khong tra loi kip ({type(e).__name__})",
                failure=model_failure("upstream_timeout", http_status=504, request_id=request_id),
            ) from None
        api_pool.danh_dau_loi(db, key, message=type(e).__name__)
        raise KhongMoDuocLuong(
            f"khong noi duoc toi may B ({type(e).__name__})",
            failure=model_failure("upstream_unreachable", http_status=502, request_id=request_id),
        ) from None

    if r.status_code >= 400:
        than_loi = _doc_het(r, ctx, client)
        failure = decode_gateway_failure(
            r.status_code,
            dict(r.headers or {}),
            than_loi.encode("utf-8", "replace"),
        )
        code = failure.canonical_code

        # Status is only a compatibility hint for old B responses. It must not
        # invent a specific semantic such as "413 means context".
        if failure.is_busy or (r.status_code == 429 and code == "upstream_unknown"):
            raise KhongMoDuocLuong(
                failure.message,
                failure=failure,
                ban=code == "upstream_unknown",
                thu_lai_sau_s=int(failure.retry_after_s or _retry_after(r)),
            )
        if failure.is_timeout or (r.status_code == 504 and code == "upstream_unknown"):
            raise KhongMoDuocLuong(
                failure.message,
                failure=failure,
                het_gio=code == "upstream_unknown",
            )
        if failure.is_cancelled or r.status_code == 499:
            raise KhongMoDuocLuong(failure.message, failure=failure)

        if failure.retry_same_generation:
            if not _da_thu_lai:
                log.warning(
                    "model_failure action=retry_once code=%s request_id=%s",
                    code,
                    failure.request_id or "missing",
                )
                return mo(
                    db,
                    duong=duong,
                    than=than,
                    timeout_s=timeout_s,
                    request_id=request_id,
                    token_dat_truoc=token_dat_truoc,
                    _da_thu_lai=True,
                )
            log.warning(
                "model_failure action=terminal code=%s request_id=%s",
                code,
                failure.request_id or "missing",
            )
        elif code == "upstream_unknown" and _loi_parser_tool_call(than_loi):
            # Rollout telemetry only. Unknown prose is never permission to retry.
            log.warning(
                "model_failure action=legacy_observed_no_retry code=%s request_id=%s",
                code,
                failure.request_id or "missing",
            )

        if r.status_code >= 500 and failure.penalizes_key:
            api_pool.danh_dau_loi(
                db,
                key,
                http_status=r.status_code,
                retry_after_s=failure.retry_after_s,
                message=f"HTTP {r.status_code} code={code}",
            )
        raise KhongMoDuocLuong(failure.message, failure=failure)

    def _di() -> Iterator[bytes]:
        try:
            for khoi in r.iter_raw():
                yield khoi
        finally:
            _dong_thuong_nguon()

    def _dong_thuong_nguon() -> None:
        """Đóng cửa ra mạng của lượt này. **Gọi được từ luồng khác**, và idempotent.

        🔴 VÌ SAO PHẢI TÁCH RA KHỎI `finally` CỦA `_di` (L-08, đo 13/09).

           Đường huỷ của cửa stream chạy ở **vòng lặp sự kiện**, trong khi
           `_di` đang bị treo giữa `r.iter_raw()` ở một **luồng threadpool đã bị
           bỏ rơi**. Cách hiển nhiên — gọi `_di.close()` — KHÔNG chạy:

               ValueError: generator already executing

           Đo bằng một bộ mô phỏng một biến số: đóng một generator đang thực thi
           ở luồng khác thì `close()` ném, `finally` **không bao giờ chạy**, và
           kết nối httpx ở lại mở. Lease nhả mà **máy B vẫn giữ slot** — mới đi
           được nửa đường.

        ⭐ Đóng thẳng `client` thì khác: lượt đọc đang chặn trong luồng bỏ rơi vỡ
           ngay, `_di` bung ra, và `finally` của nó chạy **tự nhiên** — gọi lại
           hàm này một lần nữa, nên nó buộc phải idempotent.
        """
        if getattr(_dong_thuong_nguon, "_xong", False):
            return
        _dong_thuong_nguon._xong = True  # type: ignore[attr-defined]
        try:
            ctx.__exit__(None, None, None)
        finally:
            client.close()

    return LuongMo(
        ma=r.status_code,
        content_type=r.headers.get("content-type", "text/event-stream"),
        luong=_di(),
        _db=db,
        _key=key,
        dong_nguon=_dong_thuong_nguon,
    )


def _doc_het(r, ctx, client) -> str:
    try:
        return b"".join(r.iter_raw()).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
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
