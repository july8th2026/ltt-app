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

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional

log = logging.getLogger("platform_core.llm.luong_vlm")

#: Provider duy nhất phục vụ streaming hôm nay.
PROVIDER = "ltt_llm"


class KhongMoDuocLuong(Exception):
    """Không mở được luồng. Bên gọi dịch sang 502/503 tuỳ `ban`."""

    def __init__(self, ly_do: str, *, ban: bool = False,
                 qua_dai: bool = False, het_gio: bool = False,
                 thu_lai_sau_s: int = 30):
        super().__init__(ly_do)
        self.ly_do = ly_do
        self.ban = ban
        #: Máy B nhận yêu cầu nhưng không trả lời kịp (cổng trả 504).
        #:
        #: ⛔ KHÁC `ban`, và khác một cách quan trọng. `ban` nói *"thử lại sau
        #:    30 giây thì được"*; `het_gio` **không** hứa điều đó — một yêu cầu
        #:    hết giờ vì nó quá lớn sẽ hết giờ y hệt ở lần sau.
        #:
        #: ⛔ Và khác cả hai ở chỗ quan trọng nhất: **không** `danh_dau_loi`.
        #:    Prefill 200K mất hàng phút là công việc hằng ngày của hệ này, chứ
        #:    không phải dấu hiệu khoá hỏng.
        self.het_gio = het_gio
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


def mo(db, *, duong: str, than: dict, timeout_s: float = 900.0,
       request_id: str = "", token_dat_truoc: int = 0,
       _da_thu_lai: bool = False) -> LuongMo:
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
        ctx = client.stream("POST", base.rstrip("/") + duong, json=than,
                            headers=headers)
        r = ctx.__enter__()
    except httpx.HTTPError as e:
        client.close()
        api_pool.danh_dau_loi(db, key, message=type(e).__name__)
        raise KhongMoDuocLuong(f"khong noi duoc toi may B ({type(e).__name__})") from None

    if r.status_code == 429:
        # ⛔ BẬN ≠ HỎNG (D-005). Không đánh dấu lỗi cho khoá.
        #
        # 🔴 NHUNG LY DO PHAI DI THEO. Máy B phân biệt **ba** kiểu bận, và
        #    mỗi kiểu sửa một cách khác hẳn:
        #
        #      "cong dang day"                   -> suất bị rò, cổng tự bóp cổ mình
        #      "may B dang ban"                  -> việc KHÁC đang giữ card
        #      "card chua san sang de nap model" -> ComfyUI không nhả VRAM
        #
        #    Bản trước đọc thân lỗi vào `than_loi` rồi **vứt đi**, thay bằng một
        #    chuỗi cứng — nên cả ba kiểu tới người trực dưới đúng một câu chữ.
        #
        # ⛔ Đo 31/08: một đợt 503 kéo hơn năm giờ (89/117 lượt của một khách)
        #    mà nhật ký không có lấy một dòng nói vì sao. Đó đúng là bài học đã
        #    ghi cho nhánh 5xx ngay bên dưới — chỉ là chưa ai áp cho nhánh này.
        than_loi = _doc_het(r, ctx, client)
        raise KhongMoDuocLuong(f"may B dang ban: {_ly_do_ban(than_loi)}",
                               ban=True, thu_lai_sau_s=_retry_after(r))
    if r.status_code >= 400:
        than_loi = _doc_het(r, ctx, client)
        if r.status_code == 413:
            # Đầu vào vượt trần token của máy B (`-c − max_out − DEM_UOC` theo model,
            # `llm_gateway/vat_ly.py`). Lỗi
            # CLIENT, không phải hỏng: đánh dấu `qua_dai` để bên gọi trả 413 và
            # client tự nén hội thoại. Từng bị dịch nhầm sang 503 → Codex retry
            # → bão, và khách thấy "im lặng" ở phản hồi/hội thoại dài (đo 27/08).
            raise KhongMoDuocLuong(
                f"may B tra 413: {than_loi[:200]}", qua_dai=True)
        if r.status_code == 504:
            # 🔴 HẾT GIỜ Ở MÁY B **KHÔNG PHẢI** LỖI CỦA KHOÁ — VÀ CỬA NÀY LÀ CỬA
            #    NGUY HIỂM NHẤT ĐỂ QUÊN.
            #
            #    Cổng máy B trả 504 khi thượng nguồn không kịp trả lời (tách khỏi
            #    502 ngày 09/09). Không có nhánh này thì 504 rơi xuống `>= 500`
            #    ngay dưới ⇒ `api_pool.danh_dau_loi()` ⇒ sau 5 lần
            #    `key.status = APIKEY_ERROR`, và `APIKEY_ERROR` **không tự hồi**
            #    (`api_pool._ung_vien` chỉ tự hồi `COOLDOWN`).
            #
            # ⛔ VÀ ĐÂY LÀ CỬA **STREAMING** — cửa Codex và Claude Code thật sự
            #    dùng, tức cửa của những prompt 100–200K, tức đúng chỗ hết giờ
            #    dễ xảy ra nhất. Bản vá cho cửa đồng bộ (`cong_vlm`) mà bỏ quên
            #    chỗ này là một bản vá **nhìn thì xong mà chưa chạm tới đường
            #    hay hỏng nhất**.
            #
            # ⚠️ KHÔNG đặt `ban=True`. "Bận" nghĩa là *thử lại sau 30 giây thì
            #    được*; nhưng một yêu cầu hết giờ vì nó **quá lớn** sẽ hết giờ
            #    y hệt ở lần sau. Gắn `ban` vào đây là dựng một vòng thử lại vô
            #    ích — đúng cái bẫy mà chú thích 413 ngay trên đã cảnh báo
            #    ("retry vô ích → bão").
            raise KhongMoDuocLuong(
                f"may B khong tra loi kip (504): {than_loi[:300]}", het_gio=True)
        if r.status_code >= 500:
            if _loi_parser_tool_call(than_loi):
                # 🔴 BUG THƯỢNG NGUỒN, KHÔNG PHẢI HỎNG MÁY — VÀ NÓ NGẪU NHIÊN.
                #
                #    llama.cpp (`peg-native`) thỉnh thoảng vỡ khi phân tích lượt
                #    có tool call: model sinh XONG một lượt hợp lệ rồi phát thừa
                #    một mẩu (`<think>`, dấu nháy trong here-string...), parser
                #    hỏng ở phần đuôi và **vứt toàn bộ kết quả đã sinh**.
                #    Upstream đang mở: ggml-org/llama.cpp#27733, #20260, #18353.
                #
                # ⭐ VÌ SAO THỬ LẠI LÀ ĐÚNG CHỨ KHÔNG PHẢI CHE LỖI: đây là lỗi
                #    **ngẫu nhiên theo lần sinh**, không phải lỗi của yêu cầu.
                #    Cùng một request chạy lại thường qua. Khách không mất tiền
                #    cho lượt hỏng (phần giữ chỗ được hoàn), nên thử lại là công
                #    bằng — còn KHÔNG thử lại thì khách chỉ thấy "chạy xong rồi
                #    không có gì", đúng triệu chứng đã đo 29-30/08.
                #
                # ⛔ ĐÚNG MỘT LẦN. Hai lần là bắt đầu đốt GPU cho một lỗi ta
                #    không sửa được, và giấu mất tần suất thật khỏi nhật ký.
                if not _da_thu_lai:
                    log.warning(
                        "may B vo o parser tool-call, thu lai MOT lan: %s",
                        than_loi[:300])
                    return mo(
                        db, duong=duong, than=than, timeout_s=timeout_s,
                        request_id=request_id, token_dat_truoc=token_dat_truoc,
                        _da_thu_lai=True)
                log.warning("thu lai roi van vo o parser tool-call: %s",
                            than_loi[:300])
            api_pool.danh_dau_loi(db, key, message=f"HTTP {r.status_code}")
            # 🔴 GHI ĐỦ LÝ DO THƯỢNG NGUỒN, ĐỪNG CẮT Ở 200.
            #
            #    Lỗi 5xx của máy B mang câu quan trọng nhất **ở cuối**: llama.cpp
            #    trả `Failed to parse tool call arguments as JSON: ... parse
            #    error at line 1, column NNNN ... last read: '<đoạn gây vỡ>'`.
            #    Cắt 200 ký tự là mất đúng cột lỗi và đoạn văn bản gây vỡ — thứ
            #    duy nhất chỉ ra bug nằm ở parser tool-call chứ không ở ta.
            #
            # ⛔ Đo 29/08: 70 lượt hỏng vì đúng lỗi đó, và mất nhiều giờ mới
            #    thấy được vì thông điệp đã bị cắt trước khi tới nhật ký.
            log.warning("may B tra %s (day du): %s", r.status_code,
                        than_loi[:4000])
        raise KhongMoDuocLuong(
            f"may B tra {r.status_code}: {than_loi[:600]}")

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
        _dong_thuong_nguon._xong = True          # type: ignore[attr-defined]
        try:
            ctx.__exit__(None, None, None)
        finally:
            client.close()

    return LuongMo(ma=r.status_code,
                   content_type=r.headers.get("content-type", "text/event-stream"),
                   luong=_di(), _db=db, _key=key, dong_nguon=_dong_thuong_nguon)


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


def _ly_do_ban(than: str) -> str:
    """Rút lý do người-đọc-được từ thân 429 của máy B.

    Cổng bên đó ném `HTTPException(detail={"ly_do": ..., "chi_tiet": ...})`, nên
    JSON tới đây có dạng `{"detail": {...}}`.

    ⛔ Nhưng **đừng đòi hỏi hình dạng đó**. Một proxy, một trang lỗi của
       Cloudflare, hay một bản cổng cũ hơn đều trả thứ khác — và đúng lúc ấy ta
       cần thông tin nhất. Không đọc được thì trả **văn bản thô**, vì thô vẫn hơn
       rỗng; cả hàm không có đường nào ném ra ngoài.
    """
    try:
        goc = json.loads(than)
    except (ValueError, TypeError):
        return than.strip()[:300] or "khong ro (thuong nguon khong noi gi)"
    if isinstance(goc, dict) and isinstance(goc.get("detail"), (dict, str)):
        goc = goc["detail"]
    if not isinstance(goc, dict):
        return str(goc)[:300]
    phan = [str(goc[k]) for k in ("ly_do", "chi_tiet") if goc.get(k)]
    if goc.get("vram_dung_mb"):
        phan.append("VRAM dang dung %s MB" % goc["vram_dung_mb"])
    return " | ".join(phan)[:300] or than.strip()[:300]
