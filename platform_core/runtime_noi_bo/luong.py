"""
luong.py — cửa STREAM nội bộ: admission → giữ chỗ → commit → mở luồng → đếm → quyết toán.

## Đây là mã **hạ xuống** từ `server/api/streaming.py`, không phải mã mới

Thứ tự bốn bước dưới đây được đo là đúng trên production (H38, Q107, Q114) và
đã có mười lăm tệp test ghim hành vi. Gói này chỉ tách phần **không cần HTTP**
ra khỏi phần cần HTTP, để một client nội bộ (ChatLTT) và cửa `/api/v1` cùng đi
**một** đường tính tiền. Hai đường là hai chỗ lệch tiền.

    chuan_bi()          kiểm alias → admission → ước token → giữ chỗ → COMMIT
    mo_thuong_nguon()   mở luồng tới máy B; hỏng thì hoàn + nhả suất
    LuotLuong.luong     chuyển byte nguyên xi, đếm token, quyết toán ở `finally`
    mo_luong()          bọc ba thứ trên thành SỰ KIỆN CANONICAL cho sản phẩm

⛔ `chuan_bi` **commit** trước khi chạm model — cùng bài học đã học ở
   `server/api/chat.py`: generator chạy sau khi phản hồi đã bắt đầu, lúc đó phiên
   CSDL của request đã đóng. Quyết toán và hoàn tiền vì thế luôn mở phiên MỚI.

⛔ Quyết toán trong `finally`, không phải "sau vòng lặp". Khách đóng kết nối thì
   `GeneratorExit` ném vào ngay chỗ `yield`; nhánh sau vòng lặp không bao giờ chạy.

⭐ Sự kiện canonical (`mo_luong`) là hợp đồng của **sản phẩm** với luồng; byte
   thô (`mo_luong_tho`) là hợp đồng của **khách API** với luồng. Cùng một
   `LuotLuong` bên dưới, nên cùng một cách đếm và cùng một cách thu tiền.
"""
from __future__ import annotations

import json
import logging
import re
import time
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Generator, Iterator, Optional

from platform_core.llm.dem_token_luong import DemToken
from platform_core.llm.model_failure import ModelFailure, model_failure
from platform_core.public_api.executor import for_tool
from platform_core.runtime_noi_bo.tim import KhongCoNangLuc, tim_tool  # noqa: F401

log = logging.getLogger("platform_core.runtime_noi_bo.luong")

#: Ngân sách mở luồng — 75 giây, **dưới** trần 125 giây của Cloudflare, để khi
#: máy B chậm thì **ta** trả lỗi đọc được chứ không để Cloudflare trả 524.
#: Đủ rộng cho ca xấu đã đo: `llama-swap` nạp lại model ~25 giây. Nới số này
#: không mua thêm thời gian — nó chỉ đổi 503 của ta lấy 524 của Cloudflare.
MO_LUONG_GIAY = 75.0

#: Câu cho khách khi máy B không trả lời kịp (C0-34). Đi với mã `overloaded`
#: (Anthropic `overloaded_error`, OpenAI `server_is_overloaded`): client tự thử
#: lại. ⛔ Không lộ chi tiết nội bộ (tên máy, hạn giây).
_CAU_HET_GIO = "The model did not respond in time because it is busy. Please retry shortly."

#: Đường của cổng máy B mà client nội bộ dùng. Hình dạng OpenAI chat chunk là
#: hình dạng **duy nhất** `_su_kien_tu_goi` biết đọc; hai đường kia
#: (`/v1/messages`, `/v1/responses`) chỉ đi qua `mo_luong_tho` (byte nguyên xi).
DUONG_NOI_BO = "/v1/chat/completions"


# ── Lỗi trước khi có byte nào ────────────────────────────────────────────────

class LoiCuaLuong(Exception):
    """Gốc của mọi lỗi phát sinh **trước** khi luồng bắt đầu chảy."""


class ThamSoSai(LoiCuaLuong, ValueError):
    """Alias lạ, thiếu đầu vào… — lỗi của bên gọi, chưa giữ tiền, chưa chạm GPU."""


class DangBan(LoiCuaLuong):
    """Hết suất thực thi (`nguon="suat"`) hoặc máy B trả 429 (`nguon="thuong_nguon"`).

    ⛔ BẬN ≠ HỎNG. Khách không bị thu tiền; bên gọi trả `Retry-After`.
    """

    def __init__(self, ly_do: str = "", *, nguon: str = "suat", tai_nguyen: str = "",
                 thu_lai_sau_s: int = 15, failure: ModelFailure | None = None):
        if failure is None:
            failure = model_failure(
                "concurrency_limited",
                http_status=429,
                retry_after_s=thu_lai_sau_s,
            )
        super().__init__(ly_do or failure.message)
        self.failure = failure
        self.ly_do = ly_do or failure.message
        self.nguon = nguon
        self.tai_nguyen = tai_nguyen
        self.thu_lai_sau_s = int(failure.retry_after_s or thu_lai_sau_s)


class ThieuCredit(LoiCuaLuong):
    """Không đủ số dư để giữ trần ước. Chốt TRƯỚC khi đốt GPU.

    ⛔ Lớp này hay BỌC `credit.ThieuCreditError`. Bọc mà đánh rơi `can`/`con` thì
       cửa stream trả một lỗi nghèo hơn cửa job cho **cùng một sự việc** — đúng
       thứ đợt rà 14/09/2026 tìm ra. `tu_loi()` giữ chúng lại.
    """

    def __init__(self, *args, can: int | None = None, con: int | None = None):
        super().__init__(*args)
        self.can = can
        self.con = con

    @classmethod
    def tu_loi(cls, e: Exception) -> "ThieuCredit":
        return cls(str(e), can=getattr(e, "can", None), con=getattr(e, "con", None))


class KhongMoDuoc(LoiCuaLuong):
    """Không mở được luồng vì lý do khác bận. `qua_dai` = lỗi của đầu vào.

    `failure.http_status=413` là status DÂY như máy B phát trong giai đoạn tương
    thích (spec chuẩn hoá lỗi §3), dùng cho telemetry/phạt key; status công khai do
    renderer lấy từ registry (`context_window_exceeded` = 400, L-34).
    """

    def __init__(self, ly_do: str = "", *, qua_dai: bool = False,
                 token: Optional[int] = None, tran: Optional[int] = None,
                 het_gio: bool = False, failure: ModelFailure | None = None):
        if failure is None:
            code = (
                "context_window_exceeded"
                if qua_dai
                else "upstream_timeout"
                if het_gio
                else "upstream_unknown"
            )
            failure = model_failure(
                code,
                http_status=413 if qua_dai else 504 if het_gio else 502,
                field="context" if qua_dai else None,
                limit=tran,
                actual=token,
            )
        super().__init__(ly_do or failure.message)
        self.failure = failure
        self.ly_do = ly_do or failure.message
        self.qua_dai = failure.is_context_limit
        #: Máy B không trả lời kịp (504 hoặc hết hạn đọc — C0-34): nghẽn, khách
        #: nhận `overloaded` (thử lại được), không phải "không phục vụ được".
        self.het_gio = failure.is_timeout
        #: Số cho câu "prompt is too long: N tokens > M maximum" (R-08), khi biết.
        self.token = token if token is not None else failure.actual
        self.tran = tran if tran is not None else failure.limit


# ── Ước lượng đầu vào / trần đầu ra (hạ từ `server/api/streaming.py`) ────────

def uoc_tin_nhan(than: dict) -> list:
    """Rút phần văn bản đầu vào, dù client nói giao thức nào.

    Chỉ dùng để **ước** token đầu vào cho phần giữ chỗ, nên không cần chính xác
    tuyệt đối — nhưng phải ước **CAO**, vì giữ thiếu thì khách tiêu quá số dư.
    Vì thế nó cố ý sinh ra phần tử **không có `role`** (prompt hệ thống, khối
    `tools`) — KHÔNG được đem danh sách này đi gọi model.
    """
    ra: list = []
    # ⭐ Mỗi khối ngoài `messages`/`input` được BỌC NGUYÊN (`{"content": khối}`), không
    #    rút riêng `text`: phép ước (`platform_core/llm/uoc_token`) đi mọi chuỗi của
    #    khối đúng như máy B đi body gốc. Rút một phần là A ước thấp hơn B (A ⊆ B gãy).
    for khoa in ("system", "instructions"):
        gt = than.get(khoa)
        if isinstance(gt, (str, list)) and gt:
            ra.append({"content": gt})

    tin = than.get("messages")
    if isinstance(tin, list):
        ra.extend(m if isinstance(m, dict) else {"content": m} for m in tin)

    # Responses gọi nó là `input`, và nó có thể là chuỗi trần.
    vao = than.get("input")
    if isinstance(vao, str):
        ra.append({"content": vao})
    elif isinstance(vao, list):
        ra.extend(m if isinstance(m, dict) else {"content": m} for m in vao)

    # Định nghĩa tool đi kèm mỗi lượt và **không hề nhỏ**: đo thật 23/08, prompt
    # hệ thống của Codex là ~21.936 token. Bỏ qua nó là ước thiếu rất nhiều.
    # `so_tool` cho khuôn chat (64 token/tool, `uoc_token.khuon`) — cùng dạng JSON gọn
    # máy B đếm (`uoc_token.json_tool`).
    from platform_core.llm.uoc_token import KhoiTool, json_tool
    for khoa in ("tools", "functions"):
        cong_cu = than.get(khoa)
        if isinstance(cong_cu, list) and cong_cu:
            ra.append(KhoiTool(content=json_tool(cong_cu), so_tool=len(cong_cu)))
    return ra


def tran_token_ra(than: dict, token_vao_uoc: int, executor) -> int:
    """Trần token ra cho lượt này, đã kẹp theo **chỗ còn lại trong ngữ cảnh**.

    Khách khai `max_tokens`/`max_output_tokens` thì kẹp số đó; không khai thì
    lấy mặc định của **cửa stream** (`executor.mac_dinh_cho("stream")`) — KHÔNG
    phải của cửa đồng bộ. Lấy nhầm 1.024 của cửa đồng bộ là gốc của lỗi "hỏi
    dài thì im lặng" đo được 30/08.
    """
    # O-24 cùng lớp (17/09): kẹp theo cửa sổ của ĐÚNG model khách xin, không theo
    # cửa sổ hẹp nhất — không thì một lượt 3.5 dài bị bóp đầu ra theo cửa sổ 3.8.
    tran = int(executor.context_output_cap(token_vao_uoc,
                                           str(than.get("model") or "") or None))
    for ten in ("max_tokens", "max_output_tokens"):
        gt = than.get(ten)
        if isinstance(gt, (int, float)) and not isinstance(gt, bool):
            return max(1, min(int(gt), tran))
    return max(1, min(int(executor.mac_dinh_cho("stream")), tran))


# ── Bước 1: chuẩn bị (admission + giữ chỗ + commit) ──────────────────────────

@dataclass
class ChuanBi:
    """Mọi thứ đã chốt **trước** khi chạm máy B. Sau `chuan_bi()` tiền đã giữ."""

    db: Any
    user_id: str
    tool_name: str
    duong: str
    than_gui: dict
    request_id: str
    lease_id: str
    da_giu: int
    token_vao_uoc: int
    xin_ra: int
    model_alias: str
    executor: Any
    #: Đỉnh KV mà lease máy A đang giữ; chuyển nguyên sang máy B để hai sổ khớp.
    token_dat_truoc: int = 0
    correlation_id: str = ""
    #: Dòng phòng chờ/sổ lượt (multijob) — rỗng ở đường cũ không chờ.
    waiter_id: str = ""
    #: Lượt này là whale ⇒ tắt cờ khi byte đầu về (prefill xong).
    la_whale: bool = False


# ── Bước 0 (multijob D-06): tiền kiểm TRƯỚC 200, chờ + nhận + giữ tiền SAU 200 ──

def dem_anh(than: dict) -> int:
    """Số ảnh trong đầu vào (mọi giao thức) — mỗi ảnh chiếm thêm ô KV."""
    n = 0
    for khoa in ("messages", "input"):
        ds = than.get(khoa)
        if not isinstance(ds, list):
            continue
        for tin in ds:
            noi = tin.get("content") if isinstance(tin, dict) else None
            if isinstance(noi, list):
                n += sum(1 for p in noi if isinstance(p, dict) and p.get("type") in (
                    "image", "image_url", "input_image"))
    return n


def _phien_moi():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def _dong_phien(gen) -> None:
    try:
        next(gen)
    except StopIteration:
        pass


#: Trường THÂN request mang định danh khách/máy khách — gỡ trước khi lên máy B
#: (T4 P2, `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §1a).
#:
#: ⛔ `gui = dict(than)` chép CẢ thân; đo 18/09: Claude Code gửi `metadata.user_id`
#:    = JSON {`device_id` (ổn định THEO MÁY), `session_id`}, Codex gửi
#:    `client_metadata` {`x-codex-installation-id`, `session_id`, `thread_id`} và
#:    `prompt_cache_key` = thread id. `user` / `safety_identifier` là trường định
#:    danh người dùng cuối của giao thức OpenAI. Không trường nào ảnh hưởng việc
#:    sinh chữ (`search_code prompt_cache_key repo:ggml-org/llama.cpp` = 0) —
#:    nhưng llama.cpp CÓ đọc `metadata.user_id` ở cửa Anthropic và chép vào
#:    `__metadata_user_id` (`tools/server/server-chat.cpp`, @ec928150, 19/09) ⇒
#:    định danh máy khách thật sự vào tới tiến trình B. Gỡ không đổi hành vi sinh,
#:    chỉ bớt dữ liệu nằm ở một máy không có chính sách lưu giữ và trái luật "B
#:    không biết khách" (Q102). Phiên khách dừng ở A (`public_api_requests`, P1).
TRUONG_DINH_DANH_KHACH = ("metadata", "client_metadata", "prompt_cache_key",
                          "user", "safety_identifier")


def _go_dinh_danh_khach(gui: dict) -> None:
    """Gỡ `TRUONG_DINH_DANH_KHACH` khỏi BẢN SAO thân gửi B (tại chỗ)."""
    for ten in TRUONG_DINH_DANH_KHACH:
        gui.pop(ten, None)


def _kiem_sinh_boc(kiem, executor, than: dict) -> dict:
    """Gọi bộ kiểm tham số sinh của app, ĐỔI lỗi của app sang `ThamSoSai` của cửa.

    🔴 Lỗi của app (`executor.parameter_error`, ở `ltt_llm` là
       `features.ThamSoSai`) KHÔNG phải `ThamSoSai` của module này; cửa HTTP chỉ
       bắt cái sau ⇒ trước 19/09 `top_p=5` trên `/messages` stream thoát thành
       **500** thay vì 400 (test_1522).

    ⛔ `tool_choice` KHÔNG đưa qua bộ kiểm của app: nó kiểm khuôn
       `/chat/completions` (chỉ chuỗi), còn hai cửa stream nói giao thức khác —
       `chuan_hoa_tool_choice` lo phần đó theo đúng `duong`.
    """
    loi_app = getattr(executor, "parameter_error", None)
    try:
        return kiem({k: v for k, v in than.items() if k != "tool_choice"})
    except Exception as e:
        if isinstance(loi_app, type) and isinstance(e, loi_app):
            raise ThamSoSai(str(e)) from None
        raise


def _ten_tool(t) -> str:
    return str(t.get("name") or "") if isinstance(t, dict) else ""


def _thu_tools(gui: dict, ten: set[str], nguon: str) -> None:
    """Giữ trong `tools` đúng các tool tên `ten` (theo thứ tự khách gửi)."""
    tools = gui.get("tools") or []
    con = [t for t in tools if _ten_tool(t) in ten]
    thieu = ten - {_ten_tool(t) for t in con}
    if thieu:
        raise ThamSoSai(f"`{nguon}` names {sorted(thieu)!r}, which is not in `tools`")
    gui["tools"] = con


_MAU_FN = '{"type": "function", "name": ...}'


def chuan_hoa_tool_choice(gui: dict, duong: str) -> None:
    """Dịch `tool_choice` của khách sang dạng máy B LÀM ĐÚNG, tại chỗ, trên bản sao `gui`.

    Nguồn (llama.cpp @ ec928150, tra 19/09):
      * `/v1/messages` — `server_chat_convert_anthropic_to_oai`
        (`tools/server/server-chat.cpp`) chỉ đọc ĐỐI TƯỢNG: `auto`→"auto",
        `any`/`tool`→"required" (**mất tên tool**), `none` không ánh xạ (⇒ mặc
        định auto), `disable_parallel_tool_use` bị bỏ.
      * `/v1/responses` — `tool_choice` chép nguyên sang chat; đối tượng gặp
        `json_value<std::string>` ⇒ cảnh báo rồi dùng "auto" (**ép tool mất im lặng**).

    Nên A:
      * ép MỘT tool (`{"type":"tool","name"}` / `{"type":"function","name"}`) ⇒
        thu `tools` còn đúng tool đó + "bắt buộc" — đúng nghĩa, B làm được;
      * `none` ở `/messages` ⇒ gỡ `tools` (không tool thì không gọi được);
      * thứ B không làm được (`disable_parallel_tool_use: true`, tool dựng sẵn
        của hãng) ⇒ `ThamSoSai` (400) nói rõ — không nuốt im lặng.
    """
    if gui.get("tool_choice") is None:
        gui.pop("tool_choice", None)
        return
    tc = gui["tool_choice"]
    co_tools = bool(gui.get("tools"))
    if duong == "/v1/messages":
        if not isinstance(tc, dict):
            raise ThamSoSai('`tool_choice` must be an object: '
                            '{"type": "auto"|"any"|"tool"|"none"}')
        loai = tc.get("type")
        khong_song_song = tc.get("disable_parallel_tool_use")
        if khong_song_song is not None and not isinstance(khong_song_song, bool):
            raise ThamSoSai("`tool_choice.disable_parallel_tool_use` must be a boolean")
        if khong_song_song and loai != "none":
            raise ThamSoSai("`tool_choice.disable_parallel_tool_use: true` is not "
                            "supported by this model server; omit it or set false")
        if loai == "auto":
            gui["tool_choice"] = {"type": "auto"}
        elif loai == "none":
            gui.pop("tool_choice", None)
            gui.pop("tools", None)
        elif loai in ("any", "tool"):
            if not co_tools:
                raise ThamSoSai(f"`tool_choice` {loai!r} requires non-empty `tools`")
            if loai == "tool":
                ten = tc.get("name")
                if not isinstance(ten, str) or not ten:
                    raise ThamSoSai('`tool_choice` of type "tool" requires `name`')
                _thu_tools(gui, {ten}, "tool_choice.name")
            gui["tool_choice"] = {"type": "any"}
        else:
            raise ThamSoSai(f"`tool_choice.type` {loai!r} must be one of "
                            "auto|any|tool|none")
        return
    # /v1/responses (OpenAI Responses)
    if isinstance(tc, str):
        if tc not in ("none", "auto", "required"):
            raise ThamSoSai(f"`tool_choice` {tc!r} must be none|auto|required "
                            f"or {_MAU_FN}")
        if tc == "required" and not co_tools:
            raise ThamSoSai('`tool_choice` "required" requires non-empty `tools`')
        return
    loai = tc.get("type") if isinstance(tc, dict) else None
    if loai == "function":
        ten = tc.get("name")
        if not isinstance(ten, str) or not ten:
            raise ThamSoSai('`tool_choice` of type "function" requires `name`')
        _thu_tools(gui, {ten}, "tool_choice.name")
        gui["tool_choice"] = "required"
    elif loai == "allowed_tools":
        che_do = tc.get("mode", "auto")
        ds = tc.get("tools")
        if che_do not in ("auto", "required") or not isinstance(ds, list) or not ds:
            raise ThamSoSai("`tool_choice` allowed_tools needs `mode` auto|required "
                            "and a non-empty `tools` list")
        ten_ds = {_ten_tool(t) for t in ds}
        if "" in ten_ds or any(not isinstance(t, dict) or t.get("type") != "function"
                               for t in ds):
            raise ThamSoSai(f"`tool_choice.tools` may only list {_MAU_FN}")
        _thu_tools(gui, ten_ds, "tool_choice.tools")
        gui["tool_choice"] = che_do
    else:
        raise ThamSoSai(f"`tool_choice` type {loai!r} is not supported here; use "
                        f"none|auto|required or {_MAU_FN}")


def _kep_tran_gui(gui: dict, duong: str, xin_ra: int) -> None:
    """Ghi trần ra đã kẹp vào thân gửi, đúng TÊN TRƯỜNG của cửa (H38/L2)."""
    ten_tran = "max_output_tokens" if duong.endswith("/responses") else "max_tokens"
    for _ten in ("max_tokens", "max_output_tokens"):
        if _ten in gui:
            gui[_ten] = xin_ra
            return
    gui[ten_tran] = xin_ra


def _dat_budget_may_chu(gui: dict, duong: str, executor, ten: str,
                        xin_ra: int) -> None:
    """Ghi budget suy nghĩ MÁY CHỦ đặt (L-26) vào thân gửi, đúng TRƯỜNG của cửa.

    Gọi SAU `chuan_hoa_suy_nghi` (hàm ấy gỡ mọi trường budget — của khách) và
    SAU `_kep_tran_gui` (budget tính từ trần ra đã kẹp) và SAU
    `dat_effort_cho_engine`. Model có nấc (3.8, L-32): budget theo MỨC đã chuẩn
    hoá — đọc ở `reasoning_effort` hoặc, ở `/messages`, nơi `dat_effort_cho_engine`
    đã dời nó (`chat_template_kwargs.reasoning_effort`).

    🔴 TÊN TRƯỜNG THEO CỬA của llama.cpp 91f6a6cf3, và nhầm là mất lặng lẽ:
       * `/v1/responses`: `server-chat.cpp` `server_chat_convert_responses_to_chatcmpl`
         chép NGUYÊN thân ⇒ `reasoning_budget_tokens` tới `server-common.cpp:1366`.
       * `/v1/messages`: `server_chat_convert_anthropic_to_oai` dựng thân MỚI, chỉ
         chép `temperature|top_p|top_k|stream|chat_template_kwargs` và dịch
         `thinking{type:enabled,budget_tokens}` ⇒ `thinking_budget_tokens`
         (mặc định 10.000 khi thiếu số). `reasoning_budget_tokens` cấp cao nhất
         bị VỨT ⇒ phải gửi dạng `thinking`, luôn kèm `budget_tokens`.
    """
    fn = getattr(executor, "sync_thinking_budget", None)
    if not callable(fn):
        return
    ctk = gui.get("chat_template_kwargs")
    muc = gui.get("reasoning_effort") or (
        ctk.get("reasoning_effort") if isinstance(ctk, dict) else None)
    budget = fn({"model": ten, "max_tokens": int(xin_ra), "reasoning_effort": muc})
    if budget is None:
        return
    if duong.endswith("/messages"):
        gui["thinking"] = {"type": "enabled", "budget_tokens": int(budget)}
    else:
        gui["reasoning_budget_tokens"] = int(budget)


# ══════════════════════════════════════════════════════════════════════════
#  SUY NGHĨ DO MÁY CHỦ QUYẾT — một hàm, mọi cửa (plan v2 Task 4, L-26)
# ══════════════════════════════════════════════════════════════════════════
#
# Chủ dự án chốt 18/09/2026: "mục tiêu là chất lượng và sức mạnh kết quả cao;
# giá trị phải theo khuyến nghị chính thức của model". Căn cứ đã đối chiếu:
#
#   * HF model card Qwen/Qwen3.8-27B — mức `xhigh` (mặc định) · `medium` · `low`,
#     truyền qua `reasoning_effort`; KHÔNG có `high`.
#   * HF model card Qwen/Qwen3.5-9B — suy nghĩ BẬT mặc định, chỉ tắt được bằng
#     `chat_template_kwargs.enable_thinking=false`; KHÔNG có mức effort.
#   * `llm_gateway/deploy/chat_template_v22.5.jinja` dòng 6-79 (dùng chung hai
#     model): đọc `enable_thinking`, `preserve_thinking|preserve_reasoning`,
#     `auto_disable_thinking_with_tools`, `reasoning_effort` (none/off ⇒ TẮT;
#     minimal→low; high|max|ultracode|extreme→xhigh) và quét nội dung
#     system/developer/user tìm thẻ `<|think_off|>`, `<|think_on|>`,
#     `<|think_low|>`… — tức nội dung tin nhắn cũng là một cửa ghi đè.
#   * llama.cpp ghim 91f6a6cf3 `tools/server/server-common.cpp:1366-1369`: MỖI
#     request ghi đè budget bằng `reasoning_budget_tokens|thinking_budget_tokens`
#     (và 1375-1376 `reasoning_budget_message`, `reasoning_control`);
#     `:1308-1331` chép `chat_template_kwargs` và `reasoning_effort` vào template.
#   * cùng commit `server-chat.cpp:586-591`: Anthropic `thinking.type=enabled`
#     không ghi số ⇒ budget **10.000** (vượt `--reasoning-budget` 4096/2048);
#     `:286-292`: Responses `reasoning.effort` ⇒ `reasoning_effort`.
#
# ⇒ Budget suy nghĩ chỉ `--reasoning-budget` của `llama-swap.yaml` quyết. Mọi
#   trường trên bị gỡ ở CẢ BA cửa (`/chat/completions` qua
#   `features.kiem_tham_so`; `/messages`, `/responses` qua `tien_kiem`/`chuan_bi`
#   và nhánh không-stream `_mot_cuc`).

#: Trường thân request mà llama.cpp dùng để ghi đè / điều khiển budget suy nghĩ.
_KHOA_GHI_DE_SUY_NGHI = ("reasoning_budget_tokens", "thinking_budget_tokens",
                         "reasoning_budget_message", "reasoning_control",
                         "thinking")
#: Khoá `chat_template_kwargs` DUY NHẤT khách được gửi (T1c, 19/09) — và nó
#: cũng chỉ là một chỗ khai effort, được kiểm rồi dời về `reasoning_effort`.
#: ⛔ DANH SÁCH CHO PHÉP, không phải danh sách cấm: template v22.5 còn đọc
#:    `enable_thinking`, `preserve_*`, `auto_disable_thinking_with_tools` (bật/tắt
#:    suy nghĩ — L-26), `tool_call_format` (`json` ⇒ MỌI tool call thành văn bản
#:    thường, im lặng — docs/CHATLTT_V3/01_M1_NATIVE_HAY_GENERIC.md §5),
#:    `add_vision_id`, `max_tool_arg_chars`, `max_tool_response_chars` (dòng 2-16).
#:    Bản trước chỉ cấm bốn khoá suy nghĩ ⇒ `tool_call_format` của khách đi thẳng
#:    lên máy B. Khoá template mới nào cũng mặc nhiên bị gỡ.
_KHOA_TEMPLATE_KHACH_DUOC_GUI = ("reasoning_effort",)
#: Thẻ điều khiển trong NỘI DUNG (template v22.5 dòng 35-77).
_THE_SUY_NGHI = re.compile(r"<\|think_[a-z]+\|>")
#: Trường mang nội dung hội thoại của ba giao thức.
_KHOA_NOI_DUNG = ("messages", "system", "input", "instructions")


def _bo_the(x: Any) -> Any:
    """Bản sao của `x` với mọi thẻ `<|think_*|>` trong chuỗi đã gỡ."""
    if isinstance(x, str):
        return _THE_SUY_NGHI.sub("", x) if "<|think_" in x else x
    if isinstance(x, list):
        return [_bo_the(v) for v in x]
    if isinstance(x, dict):
        return {k: _bo_the(v) for k, v in x.items()}
    return x


def _muc_effort(gt: Any, alias: str) -> Optional[str]:
    """Chuẩn hoá MỘT giá trị effort cho model có nấc. Ném `ThamSoSai`.

    Trả None cho model cố định (effort bị bỏ qua công khai).
    """
    from platform_core.public_api import examples as E

    muc = str(gt).strip().lower()
    if muc in E.REASONING_EFFORT_TAT:
        raise ThamSoSai(
            f"`reasoning_effort={gt!r}` is not served: these models run with "
            f"thinking-mode sampling parameters, and disabling thinking against "
            f"them collapses output quality (measured: 2 tokens instead of "
            f"~1180 on a long-generation prompt). "
            + ("`ltt-3.5` always thinks; omit reasoning_effort."
               if alias in E.CODEX_MODEL_REASONING_CO_DINH else
               "Use `low` for the shortest answers."))
    cac_muc = E.CODEX_MODEL_REASONING_LEVELS.get(alias)
    if cac_muc is None:
        return str(gt)
    co_dinh = alias in E.CODEX_MODEL_REASONING_CO_DINH
    # Model cố định nhận đúng tập giá trị model có nấc nhận (Codex gửi mọi mức).
    goc = E.CODEX_MODEL_REASONING_LEVELS[E.MODEL_EFFORT_THAM_CHIEU] if co_dinh else cac_muc
    muc = E.REASONING_EFFORT_ALIASES.get(muc, muc)
    if muc not in goc:
        hop_le = sorted(set(goc) | set(E.REASONING_EFFORT_ALIASES))
        raise ThamSoSai(
            f"`reasoning_effort` must be one of {hop_le} for `{alias}`"
            + (" (accepted and ignored: this model always thinks)" if co_dinh else ""))
    return None if co_dinh else muc


def chuan_hoa_suy_nghi(than: dict, model_id: str) -> tuple[dict, bool]:
    """Thân gửi máy B với suy nghĩ do MÁY CHỦ quyết. Trả `(thân mới, bo_qua)`.

    `model_id` nhận bí danh công khai (`ltt-3.8`) hoặc id nội bộ (`qwen38-api`).
    `bo_qua=True` khi khách gửi effort cho model cố định (3.5) và nó đã bị gỡ —
    cửa trả header `X-LTT-Effort-Bo-Qua: 1`.

    1. Gỡ mọi trường ghi đè budget/bật-tắt (`_KHOA_GHI_DE_SUY_NGHI`), MỌI khoá
       `chat_template_kwargs` ngoài `_KHOA_TEMPLATE_KHACH_DUOC_GUI` và thẻ
       `<|think_*|>` trong nội dung.
    2. Effort (ba chỗ: `reasoning_effort`, Responses `reasoning.effort`,
       `chat_template_kwargs.reasoning_effort`): `none|off` ⇒ `ThamSoSai` (400) ở
       mọi model; 3.8 chuẩn hoá `minimal→low`, `high|max→xhigh`, lạ ⇒ 400; 3.5
       gỡ (template dùng nhánh mặc định = prompt chính thức).
    3. (T1c) Kết quả mang effort ở MỘT chỗ: `reasoning_effort` cấp cao nhất —
       trường `/chat/completions` (cửa đồng bộ, job, `_mot_cuc`) đọc. Ưu tiên khi
       khách khai nhiều chỗ: cấp cao nhất > `reasoning.effort` > kwargs (mọi chỗ
       vẫn được kiểm). Cửa nào engine đọc chỗ khác thì `dat_effort_cho_engine`
       dời đi — không cửa nào tự đoán lại từ ba chỗ.
    4. (L-33) Model có nấc, khách không khai chỗ nào ⇒ chèn
       `examples.CODEX_MODEL_REASONING[alias]` (3.8: `medium`).

    ⛔ Không sửa `than` đầu vào. Idempotent: gọi hai lần cho cùng kết quả.
    """
    from platform_core.llm.canonical import ALIAS_SANG_ID

    alias = next((a for a, i in ALIAS_SANG_ID.items() if i == model_id), model_id)
    gui = {k: v for k, v in than.items() if k not in _KHOA_GHI_DE_SUY_NGHI}
    for k in _KHOA_NOI_DUNG:
        if k in gui:
            gui[k] = _bo_the(gui[k])

    # Thu effort từ ba chỗ (thứ tự = ưu tiên), gỡ khỏi chỗ cũ.
    ung_vien: list[Any] = []
    if gui.get("reasoning_effort") is not None:
        ung_vien.append(gui["reasoning_effort"])
    gui.pop("reasoning_effort", None)
    rs = gui.get("reasoning")
    if isinstance(rs, dict) and "effort" in rs:
        if rs["effort"] is not None:
            ung_vien.append(rs["effort"])
        rs = {k: v for k, v in rs.items() if k != "effort"}
        if rs:
            gui["reasoning"] = rs
        else:
            gui.pop("reasoning")
    ctk = gui.pop("chat_template_kwargs", None)
    if isinstance(ctk, dict) and ctk.get("reasoning_effort") is not None:
        ung_vien.append(ctk["reasoning_effort"])
    # `ctk` KHÔNG quay lại thân: khoá cho phép duy nhất là effort, đã thu ở trên.

    # Kiểm MỌI giá trị (một `none` ở chỗ phụ vẫn là 400), giữ cái ưu tiên nhất.
    cac_muc = [_muc_effort(gt, alias) for gt in ung_vien]
    bo_qua = bool(ung_vien) and cac_muc[0] is None
    if cac_muc and cac_muc[0] is not None:
        gui["reasoning_effort"] = cac_muc[0]
    elif not ung_vien:
        # ⭐ L-33 (chủ dự án 19/09 tối): model có nấc mà khách bỏ trống ⇒ MÁY CHỦ
        #    chèn mức mặc định của nền tảng (3.8: `medium`), mọi cửa — không để
        #    `--reasoning-effort xhigh` của máy B quyết. Model cố định: không chèn.
        from platform_core.public_api import examples as E
        if (alias in E.CODEX_MODEL_REASONING_LEVELS
                and alias not in E.CODEX_MODEL_REASONING_CO_DINH):
            gui["reasoning_effort"] = E.CODEX_MODEL_REASONING[alias]
    return gui, bo_qua


def dat_effort_cho_engine(gui: dict, duong: str) -> None:
    """Dời effort đã chuẩn hoá (`reasoning_effort` cấp cao nhất) vào TRƯỜNG mà
    llama.cpp của CỬA ấy thật sự đưa tới template. Gọi SAU `chuan_hoa_suy_nghi`.

    🔴 T1c (đo 18-19/09, engine B, n=5/ô, cùng prompt): `/v1/messages` với
       `reasoning_effort=low` cấp cao nhất ⇒ 74 token prompt, BẰNG xhigh — bộ chọn
       effort của LTTCODE vô tác dụng. Nguồn, llama.cpp 91f6a6cf3:
       * `server-chat.cpp:579` `server_chat_convert_anthropic_to_oai` dựng thân
         MỚI, chỉ chép `temperature|top_p|top_k|stream|chat_template_kwargs` ⇒
         `reasoning_effort` bị vứt ⇒ template dùng `--reasoning-effort xhigh`
         (`common/arg.cpp:3695-3704` ghi vào `default_template_kwargs`).
       * `server-common.cpp:1308-1312` gộp `chat_template_kwargs` của request ĐÈ
         lên mặc định máy chủ ⇒ `chat_template_kwargs.reasoning_effort=low` ⇒ 62
         token (medium 36, xhigh 74): TỚI template (v22.5 dòng 19-29, 83-86, 217).
       * `/v1/responses` chép NGUYÊN thân (`server-chat.cpp:15`) và `/v1/chat/
         completions` đọc `reasoning_effort` cấp cao nhất (`server-common.cpp:
         1325-1332`) ⇒ cả hai đã tới template (đo: low 62) — giữ nguyên.

    ⭐ Model có nấc luôn có effort ở đây (L-33: `chuan_hoa_suy_nghi` chèn mức
       mặc định nền tảng khi khách bỏ trống). Không effort (model cố định) ⇒
       không đặt gì.
    ⚠️ Effort nằm ở ĐẦU system prompt (template dòng 217) ⇒ đổi effort giữa các
       lượt của cùng một phiên là mất prompt cache cả hội thoại. Máy chủ KHÔNG tự
       đổi effort cho request phụ (nén, tiêu đề…); client phải gửi cùng mức.
    """
    if not duong.endswith("/messages"):
        return
    muc = gui.pop("reasoning_effort", None)
    if muc is None:
        return
    gui["chat_template_kwargs"] = {"reasoning_effort": muc}


@dataclass
class TienKiem:
    """Mọi thứ đã kiểm TRƯỚC khi gửi 200. Chưa ghi gì, chưa giữ tiền, chưa giành slot."""

    user_id: str
    tool_name: str
    duong: str
    than_gui: dict
    request_id: str
    token_vao_uoc: int
    xin_ra: int
    model_alias: str
    executor: Any
    tai_nguyen: str
    so_suat: int
    token_pool: int
    token_dat_truoc: int
    token_prefill_moi: int
    la_whale: bool
    cua: str = "stream"
    correlation_id: str = ""
    #: Khách gửi effort cho model cố định (3.5) và nó đã bị gỡ trước máy B
    #: (`chuan_hoa_suy_nghi`) ⇒ cửa trả header `X-LTT-Effort-Bo-Qua: 1`.
    effort_bo_qua: bool = False

    @property
    def dung_phong_cho(self) -> bool:
        """Tool khai ngân sách KV ⇒ đi phòng chờ. Không khai ⇒ đường cũ nguyên vẹn."""
        return bool(self.tai_nguyen) and self.so_suat > 0 and self.token_pool > 0


def _suc_chua(tool, model: str):
    """`AdmissionModel | None` của `tool` cho ĐÚNG `model` này. (multijob 2.2)

    ⭐ Trả NGUYÊN bản khai (phương án C bước 2), không bóc thành bộ ba: ngưỡng
       whale, đệm ước và token mỗi ảnh là số của MODEL, và `luat_cho` đọc chúng
       từ chính đối tượng này. Bóc ra là mở chỗ cho một cửa quên một trường.

    🔴 MỘT tool, NHIỀU pool. `text.chat` phục vụ `ltt-3.8` và `ltt-3.5` trên hai
       pool KV khác nhau, nên `admission_resource/slots/token_pool` tĩnh không
       còn tả nổi sức chứa: đọc thẳng chúng là đọc sức chứa của model *khác*.
       Bản khai của app trả lời theo model, qua `ToolSpec.admission_cho`.

    ⛔ `KeyError` → `ThamSoSai`, KHÔNG để nó thoát. `ThamSoSai` là lỗi hai cửa
       đồng bộ đã biết dịch sang 400 (`_bao_400`); một `KeyError` trần thoát ra
       khỏi đây thành **500**, tức ta trả lời "server hỏng" cho một model ta
       đơn giản là không phục vụ.
    """
    suc = None
    try:
        suc = tool.admission_cho(model)
    except KeyError as e:
        raise ThamSoSai(f"model {model!r} khong duoc phuc vu o cua nay: {e}") from None
    return suc


def _bo_ba(suc) -> tuple[str, int, int]:
    """`(tài nguyên, số suất, pool KV)` của một bản khai — `None` ⇒ không giành gì."""
    if suc is None:
        return ("", 0, 0)
    return (str(suc.resource or ""), int(suc.slots or 0), int(suc.token_pool or 0))


def _dat_cho(suc, *, lop: str, token_vao_uoc: int, xin_ra: int, so_anh: int = 0,
             token_prefill_moi: int | None = None) -> dict:
    """`tham_so_da_luot.luat_cho` + dịch `DatChoVuotPool` sang lỗi "quá dài".

    ⛔ Lượt đặt chỗ vượt cả pool KV không bao giờ được nhận (phương án C bất biến
       1 — không còn kẹp im lặng). Với khách đó là một yêu cầu QUÁ DÀI cho cấu
       hình hiện tại (ảnh cộng vào vượt cửa sổ, hoặc pool đang bị hạ khẩn cấp):
       lỗi quá dài trước 200 (công khai 400 `context_window_exceeded`) để
       client tự nén, không phải chờ hết hạn rồi `overloaded`.
    """
    from platform_core.llm import tham_so_da_luot

    try:
        return tham_so_da_luot.luat_cho(
            suc, lop=lop, token_vao_uoc=token_vao_uoc, xin_ra=xin_ra,
            so_anh=so_anh, token_prefill_moi=token_prefill_moi)
    except tham_so_da_luot.DatChoVuotPool as e:
        raise KhongMoDuoc(f"dau vao + dau ra + anh {e.dat} token vuot ngan sach "
                          f"KV {e.pool} cua model", qua_dai=True,
                          token=int(e.dat), tran=int(e.pool)) from None


def tien_kiem(db, *, user_id: str, tool_name: str, than: dict, duong: str,
              correlation_id: str = "", tien_to: str = "st", cua: str = "stream",
              tim: Optional[Callable[[str], tuple]] = None) -> TienKiem:
    """Kiểm alias → đầu vào → trần vào (quá dài) → số dư (402) → phòng chờ (429). CHỈ ĐỌC.

    Ném `ThamSoSai` / `KhongMoDuoc(qua_dai=True)` / `ThieuCredit` /
    `DangBan(nguon="phong_day")` — cả bốn đều TRƯỚC 200, nên client nhận đúng mã
    HTTP (quá dài công khai = 400 đúng khuôn từng giao thức — Codex/Claude Code
    dựa vào khuôn đó để tự nén hội thoại, `server/api/su_kien_loi.py`).
    """
    from platform_core.llm import (luat_nhan, phong_cho, tham_so_da_luot, thanh_toan,
                                   uoc_moi)
    from platform_core.public_api import metrics

    _manifest, tool = (tim or tim_tool)(tool_name)
    executor = for_tool(tool)
    ten = str(than.get("model") or "")
    aliases = executor.aliases()
    if ten not in aliases:
        raise ThamSoSai(f"`model` phai la mot trong {list(aliases)}")
    tin = uoc_tin_nhan(than)
    if not tin:
        raise ThamSoSai("yeu cau khong mang dau vao nao de tra loi")

    gui = dict(than)

    # 🔴 KIEM THAM SO SINH O DAY, TRUOC KHI THAN DI LEN MAY B.
    #
    #    Dong `gui = dict(than)` ngay tren chep CA than request. Truoc 14/09 do
    #    la toan bo "kiem" cua cua stream, nen do duoc tren production:
    #
    #        top_p=5  ->  /chat/completions (dong bo) : 400 invalid_request
    #        top_p=5  ->  /messages         (stream)  : 200, chay binh thuong
    #
    #    Mot hop dong cong bo, hai cua tra loi khac nhau — va cua sai la cua
    #    KHONG kiem, vi no de mot gia tri hop dong CAM di thang toi bo giai ma.
    #
    # ⭐ Khuon chuan (vLLM `entrypoints/openai/.../protocol.py`): `stream` chi la
    #    MOT TRUONG nhu moi truong khac, va moi validator chay TRUOC khi re
    #    nhanh stream. Kiem mot lan, cho moi cua.
    #
    # ⛔ Goi `validate_generation`, KHONG goi `validate`: `/messages` mang
    #    `system`, `/responses` mang `input` co the la chuoi tran. Bo kiem day
    #    du doi moi phan tu `messages` co `role` va se nem 500 — dung loi
    #    `_tin_that` da ghi. Ham sinh chi kiem tham so sinh va **bo qua moi khoa
    #    no khong biet**, nen `top_k`/`stop_sequences`/`metadata` cua client
    #    Anthropic van di qua duoc.
    _kiem_sinh = getattr(executor, "validate_generation", None)
    if callable(_kiem_sinh):
        gui.update(_kiem_sinh_boc(_kiem_sinh, executor, than))
    chuan_hoa_tool_choice(gui, duong)  # theo giao thức của cửa (test_1522)
    # Suy nghĩ do máy chủ quyết (L-26): gỡ ghi đè budget/bật-tắt, chuẩn hoá effort.
    gui, effort_bo_qua = chuan_hoa_suy_nghi(gui, ten)
    dat_effort_cho_engine(gui, duong)  # T1c: đúng trường llama.cpp của cửa đọc
    gui["model"] = executor.model_id(ten)
    _go_dinh_danh_khach(gui)  # T4 P2: B không được biết khách
    request_id = thanh_toan.ma_luot(tien_to)
    vao_uoc = int(executor.estimate_input(tin))
    xin_ra = tran_token_ra(than, vao_uoc, executor)
    _kep_tran_gui(gui, duong, xin_ra)
    _dat_budget_may_chu(gui, duong, executor, ten, xin_ra)

    tran_vao = getattr(executor, "input_cap", None)
    if tran_vao is not None:
        cap = int(tran_vao(ten))
        if vao_uoc > cap:
            raise KhongMoDuoc(f"dau vao uoc {vao_uoc} token vuot tran {cap}",
                              qua_dai=True, token=vao_uoc, tran=cap)

    ts = tham_so_da_luot.doc()
    suc = _suc_chua(tool, ten)
    tai_nguyen, so_suat, pool = _bo_ba(suc)
    moi = uoc_moi.uoc_token_moi(user_id, tin, executor.estimate_input)
    # MỘT phép tính đặt chỗ + MỘT chỗ gắn cờ whale (ngưỡng THEO MODEL) cho mọi cửa.
    luat = _dat_cho(suc, lop=luat_nhan.TUONG_TAC, token_vao_uoc=vao_uoc,
                    xin_ra=xin_ra, so_anh=dem_anh(than), token_prefill_moi=int(moi))

    if not thanh_toan.du_so_du(db, user_id=user_id, token_vao_uoc=vao_uoc,
                               max_tokens=xin_ra, model=ten):
        metrics.increment(metrics.CREDIT_EXHAUSTED)
        raise ThieuCredit("so du khong du cho phan giu cho cua luot nay")

    tk = TienKiem(user_id=user_id, tool_name=tool_name, duong=duong, than_gui=gui,
                  request_id=request_id, token_vao_uoc=vao_uoc, xin_ra=xin_ra,
                  model_alias=ten, executor=executor, tai_nguyen=tai_nguyen,
                  so_suat=so_suat, token_pool=pool,
                  token_dat_truoc=int(luat.get("token_dat_truoc", 0)),
                  token_prefill_moi=int(luat.get("token_prefill_moi", moi)),
                  la_whale=bool(luat.get("la_whale", False)),
                  cua=cua, correlation_id=correlation_id,
                  effort_bo_qua=effort_bo_qua)
    if tk.dung_phong_cho:
        try:
            # L-12b: phòng chờ chỉ chặn ĐỘ DÀI HÀNG; "có vừa pool KV không" là
            # việc của `luat_nhan` luật 2 lúc xét nhận — lượt chưa vừa thì CHỜ.
            phong_cho.kiem_phong(db, resource=tai_nguyen,
                                 so_nguoi_toi_da=ts.so_nguoi_cho_toi_da,
                                 la_whale=tk.la_whale,
                                 so_ca_voi_toi_da=ts.so_ca_voi_cho_toi_da)
        except phong_cho.PhongDay as e:
            raise DangBan(e.ly_do, nguon="phong_day", tai_nguyen=tai_nguyen,
                          thu_lai_sau_s=15) from None
    return tk


def _yeu_cau_cho(tk: TienKiem):
    """`phong_cho.YeuCauCho` của một lượt stream — dựng MỘT chỗ (vào hàng, xếp lại)."""
    from platform_core.llm import luat_nhan, phong_cho

    return phong_cho.YeuCauCho(
        resource=tk.tai_nguyen, slots=tk.so_suat, token_pool=tk.token_pool,
        user_id=tk.user_id, mode="stream", holder_id=tk.request_id,
        request_id=tk.request_id, cua=tk.cua, lop=luat_nhan.TUONG_TAC,
        token_dat_truoc=tk.token_dat_truoc, token_prefill_moi=tk.token_prefill_moi,
        la_whale=tk.la_whale,
        # `than_gui["model"]` là id model **nội bộ** — `tien_kiem` đã dịch bí danh
        # sang nó (`gui["model"] = executor.model_id(ten)`). ⛔ KHÔNG dùng
        # `tk.model_alias`: bí danh đổi được mà engine không đổi, nên một sổ khoá
        # theo bí danh sẽ nói về hai thứ khác nhau trước và sau một lần đổi tên.
        model=str(tk.than_gui.get("model") or ""))


def vao_va_cho(tk: TienKiem, *, db_luong, han_s: float, dong_ho=None, ngu=None):
    """GENERATOR: vào phòng chờ → `yield` lý do mỗi nhịp → được nhận → GIỮ TIỀN → `return ChuanBi`.

    ⛔ GIỮ TIỀN SAU KHI ĐƯỢC NHẬN (D-06, INV-MJ-1): trong suốt lúc chờ, lượt này
       không có dòng giữ chỗ nào. Hết trần chờ / khách ngắt ⇒ không có gì phải hoàn.
    `db_luong` là phiên sống suốt luồng (luong_vlm cần nó để đánh dấu khoá).
    """
    from platform_core import credit
    from platform_core.llm import phong_cho, thanh_toan
    from platform_core.public_api import metrics

    yc = _yeu_cau_cho(tk)
    gen, db = _phien_moi()
    try:
        waiter_id = phong_cho.vao(db, yc)
        db.commit()
    finally:
        _dong_phien(gen)

    kw = {}
    if dong_ho is not None:
        kw["dong_ho"] = dong_ho
    if ngu is not None:
        kw["ngu"] = ngu
    lease_id = yield from phong_cho.cho_nhan(yc, waiter_id=waiter_id, han_s=han_s, **kw)

    gen, db = _phien_moi()
    try:
        da_giu = thanh_toan.giu_cho_luot(
            db, user_id=tk.user_id, request_id=tk.request_id,
            token_vao_uoc=tk.token_vao_uoc, max_tokens=tk.xin_ra,
            model=tk.model_alias)
        db.commit()
    except credit.ThieuCreditError as e:
        # Số dư tụt giữa lúc tiền kiểm và lúc được nhận (khách chạy song song).
        db.rollback()
        metrics.increment(metrics.CREDIT_EXHAUSTED)
        _nha_suat(lease_id)
        phong_cho.ghi_ket_thuc(waiter_id, "thieu_credit")
        raise ThieuCredit.tu_loi(e) from None
    except BaseException:
        db.rollback()
        _nha_suat(lease_id)
        phong_cho.ghi_ket_thuc(waiter_id, "loi")
        raise
    finally:
        _dong_phien(gen)

    return ChuanBi(db=db_luong, user_id=tk.user_id, tool_name=tk.tool_name,
                   duong=tk.duong, than_gui=tk.than_gui, request_id=tk.request_id,
                   lease_id=lease_id, da_giu=da_giu, token_vao_uoc=tk.token_vao_uoc,
                   xin_ra=tk.xin_ra, model_alias=tk.model_alias, executor=tk.executor,
                   token_dat_truoc=tk.token_dat_truoc,
                   correlation_id=tk.correlation_id, waiter_id=waiter_id,
                   la_whale=tk.la_whale)


# ── Cửa ĐỒNG BỘ: chờ trong phòng chờ, giữ tiền SAU khi được nhận (D04) ───────
#
# ⭐ VÌ SAO ĐIỂM CHỜ NẰM Ở ĐÂY CHỨ KHÔNG NẰM TRONG GIAO DỊCH CỦA REQUEST.
#
#    `idempotency.begin` lấy `pg_advisory_xact_lock` và khoá đó sống hết giao
#    dịch. Chờ 60 giây bên trong giao dịch ấy là giữ khoá 60 giây — mọi lượt
#    trùng khoá treo theo thay vì nhận ngay câu "đang xử lý", và một kết nối
#    CSDL bị giữ suốt lúc chờ. Nên cửa **commit trước**, rồi mới gọi hàm dưới
#    đây (phiên MỚI, như `vao_va_cho` của cửa stream).

#: ⛔ SEAM CHO PHÉP KIỂM, production để `None` (đồng hồ thật + `time.sleep`).
#:    Một trần chờ 60 giây không kiểm được bằng cách ngủ 60 giây thật; và mỗi
#:    nhịp chờ là điểm quan sát duy nhất mà phép kiểm chen vào được để đo
#:    INV-MJ-1 ("đang chờ thì không có dòng giữ tiền nào").
DONG_HO_CHO: Optional[Callable[[], Any]] = None
NGU_CHO: Optional[Callable[[float], None]] = None


def han_cho_dong_bo(*, ngan_sach_s: float, da_tieu_s: float = 0.0,
                    tran_s: Optional[float] = None) -> float:
    """`min(trần chờ, ngân sách thời gian CÒN LẠI của cửa)` — không âm. (D04)

    ⛔ Trần 60 giây một mình là không đủ. Cửa đồng bộ hứa trả lời trong
       `SYNC_BILLED_MAX_SECONDS`, và `max_tokens` của khách đã được kẹp theo
       đúng ngân sách ấy. Chờ hết 60 giây rồi mới bắt đầu gọi model là đẩy lượt
       vượt qua đồng hồ của Cloudflare — khách nhận 524, ta đã đốt GPU.
    """
    from platform_core.llm import tham_so_da_luot

    tran = (tham_so_da_luot.doc().cho_dong_bo_toi_da_s if tran_s is None
            else float(tran_s))
    return max(0.0, min(float(tran), float(ngan_sach_s) - float(da_tieu_s)))


def id_model_noi_bo(executor, alias: str) -> str:
    """Bí danh khách → id model **nội bộ**, cho sổ lượt. `""` = không dịch được.

    ⛔ FAIL SOFT, CÓ CHỦ Ý. `executor.model_id` ném `KeyError` với một bí danh lạ,
       và ở đây một `KeyError` thành **500** — tức ta trả lời "server hỏng" cho
       một lượt hoàn toàn hợp lệ, chỉ vì một cột QUAN SÁT không dịch được tên.
       Sổ thiếu một ô là một sổ kém hơn; một 500 là một lượt mất. `""` đi vào ô
       `khong_khai` của `job_metrics`, nên cái thiếu ấy **nhìn thấy được** chứ
       không bị gộp vào một model nào.
    """
    try:
        ra = executor.model_id(alias)
    except (AttributeError, KeyError, TypeError):
        return ""
    return str(ra or "")


@dataclass
class SuatDongBo:
    """Kết quả của phòng chờ ở cửa đồng bộ. **Chưa** giữ đồng tiền nào.

    ⚠️ KHÔNG `frozen` (phương án C bước 1): máy B 429 ⇒ `goi_dong_bo_co_xep_lai`
       nhả suất cũ, xếp lại và gán `lease_id` MỚI vào chính đối tượng này. Mọi
       đường nhả của cửa (`_nha`, `_release_ticket`, `giu_suat_dong_bo`) đọc
       `suat.lease_id` LÚC NHẢ, nên luôn nhả đúng suất đang giữ.
    """

    lease_id: str
    waiter_id: str
    #: Số token đặt chỗ của lease — đi lên máy B trong `X-LTT-Token-Dat` (O-05).
    token_dat_truoc: int = 0
    #: Yêu cầu chờ đã dùng — cần để XẾP LẠI khi máy B 429. `None` ⇒ không xếp lại.
    yeu_cau: Any = None
    #: 🔴 LỚP 2 của cơ chế nhả suất ở cửa ĐỒNG BỘ (cùng vai với
    #: `LuotLuong.luc_khoi_cuoi` của cửa stream): mốc **lần cuối công việc nhúc
    #: nhích**, theo `time.monotonic()`. `giu_suat_dong_bo` hỏi mốc này trước mỗi
    #: nhịp; im quá `admission.TRAN_IM_LANG_S` thì luồng nhịp tự nhả.
    #:
    #: ⭐ Cửa đồng bộ không có byte chảy dọc đường, nên "nhúc nhích" ở đây là
    #:    **một lượt gọi máy B được bắt đầu** (`goi_dong_bo_co_xep_lai` gọi
    #:    `cham()` mỗi lần thử, kể cả sau khi xếp lại). Đó vẫn là lời khai có
    #:    kiểm chứng: `TRAN_IM_LANG_S` ≥ mọi read timeout đi lên máy B, nên một
    #:    lượt gọi còn sống không bao giờ im lâu hơn thế mà chính httpx không nổ.
    #: ⛔ Khởi tạo bằng `monotonic()` chứ không bằng `0.0` — cùng lý do với cửa
    #:    stream: giữa lúc nhận suất và lượt gọi đầu tiên là một khoảng hợp lệ.
    luc_khoi_cuoi: float = field(default_factory=time.monotonic)

    def cham(self) -> None:
        """Ghi nhận công việc vừa nhúc nhích (một lượt gọi máy B bắt đầu)."""
        self.luc_khoi_cuoi = time.monotonic()


def cho_suat_dong_bo(*, suc, user_id: str, request_id: str, cua: str,
                     token_vao_uoc: int, xin_ra: int, so_anh: int = 0,
                     han_s: float, ngat_chua=None, model: str = "") -> SuatDongBo:
    """Vào phòng chờ → chờ chặn ≤ `han_s` → trả suất. **Không** chạm sổ tiền.

    `suc` là `AdmissionModel | None` của ĐÚNG model (`tool.admission_cho(alias)`).

    Ném `phong_cho.HetCho` (hết trần ⇒ cửa trả 429), `phong_cho.KhachDi`
    (khách đi giữa lúc chờ) hoặc `KhongMoDuoc(qua_dai=True)` (đặt chỗ vượt cả
    pool KV — không bao giờ nhận được). Mọi đường đều để lại **0 khoản giữ** —
    đó là toàn bộ lý do hàm này không biết gì về tiền (INV-MJ-1, INV-MJ-2).
    """
    from platform_core.llm import admission, luat_nhan, phong_cho

    tai_nguyen, so_suat, token_pool = _bo_ba(suc)
    if not tai_nguyen or so_suat <= 0:
        return SuatDongBo("", "")

    # ⭐ Không truyền `token_prefill_moi`: cửa đồng bộ không có lịch sử tiền tố,
    #    `luat_cho` gắn cờ whale theo `token_vao_uoc` (ước CAO — hướng an toàn).
    luat = _dat_cho(suc, lop=luat_nhan.TUONG_TAC, token_vao_uoc=token_vao_uoc,
                    xin_ra=xin_ra, so_anh=so_anh)

    if not luat:
        # Tool KHÔNG khai ngân sách KV ⇒ đường cũ nguyên vẹn: một lần thử, không
        # phòng chờ, không dòng chờ nào trong sổ lượt.
        gen, db = _phien_moi()
        try:
            ve = admission.acquire(db, resource=tai_nguyen, slots=so_suat,
                                   user_id=user_id, mode="sync",
                                   holder_id=request_id)
            db.commit()
        finally:
            _dong_phien(gen)
        if ve is None:
            raise phong_cho.HetCho(luat_nhan.CHO_SLOT)
        return SuatDongBo(ve.id, "")

    kw = _seam_cho()
    bay_gio = DONG_HO_CHO() if DONG_HO_CHO is not None else None

    yc = phong_cho.YeuCauCho(
        resource=tai_nguyen, slots=so_suat, token_pool=int(token_pool),
        user_id=user_id, mode="sync", holder_id=request_id,
        request_id=request_id, cua=cua, lop=luat_nhan.TUONG_TAC,
        token_dat_truoc=int(luat["token_dat_truoc"]),
        token_prefill_moi=int(luat["token_prefill_moi"]),
        la_whale=bool(luat["la_whale"]),
        # Id model nội bộ, do cửa gọi khai. Rỗng ⇒ ô `khong_khai` trong sổ, chứ
        # không bị gộp vào model của một tài nguyên nào.
        model=str(model or ""))

    gen, db = _phien_moi()
    try:
        waiter_id = phong_cho.vao(db, yc, now=bay_gio)
        db.commit()
    finally:
        _dong_phien(gen)

    lease_id = phong_cho.cho_nhan_chan(
        yc, waiter_id=waiter_id, han_s=float(han_s), ngat_chua=ngat_chua, **kw)
    return SuatDongBo(lease_id, waiter_id, token_dat_truoc=yc.token_dat_truoc,
                      yeu_cau=yc)


def _seam_cho() -> dict:
    """Đồng hồ/giấc ngủ của phép kiểm (`DONG_HO_CHO`, `NGU_CHO`) — rỗng ở production."""
    kw: dict = {}
    if DONG_HO_CHO is not None:
        kw["dong_ho"] = DONG_HO_CHO
    if NGU_CHO is not None:
        kw["ngu"] = NGU_CHO
    return kw


@contextmanager
def giu_suat_dong_bo(suat: SuatDongBo) -> Iterator[None]:
    """Đập nhịp suất lúc vào khối, và nhả suất ĐANG GIỮ khi rời khối.

    ⛔ Không phải `admission.keep_alive(suat.lease_id)` trần: hàm ấy chụp id LÚC
       VÀO. Sau một lần xếp lại (máy B 429) suất đang giữ là suất MỚI, và nhả
       theo id cũ là để suất mới mồ côi tới `ORPHAN_TIMEOUT` (20 phút GPU nằm
       không). Suất mới không được đập nhịp — lượt đồng bộ sống ≤ trần ngân sách
       cửa (~100 s), ngắn hơn thời hạn mồ côi rất nhiều.

    ## 🔴 `con_song` — vì sao nhịp ở đây KHÔNG được vô điều kiện (18/09/2026)

    Bản trước gọi `keep_alive(lease_id)` trần, tức đập nhịp **vô điều kiện** —
    đúng lời nói dối của L-08 (`admission.keep_alive`, `test_1247`): nó chứng
    minh *luồng còn sống*, không chứng minh *công việc còn tiến triển*. Chừng
    nào `ORPHAN_TIMEOUT` của lease sync còn là 20 phút thì lời nói dối ấy vô
    hại trên thực tế; `ORPHAN_TIMEOUT_SYNC` (120 s) làm nó thành **quyết định**:
    một tiến trình còn sống ôm một lượt đã bị bỏ rơi sẽ đẩy nhịp mãi, và hạn
    mới **không bao giờ khai hoả**.

    ⇒ Vị từ ở đây hỏi đúng câu mà cửa stream hỏi, bằng đúng hằng số ấy: *lần
      cuối công việc nhúc nhích cách đây có quá `TRAN_IM_LANG_S` không*. Mốc là
      `suat.luc_khoi_cuoi`, do `goi_dong_bo_co_xep_lai` `cham()` mỗi lượt gọi.
    ⛔ Không đo bằng đồng hồ của lease ("đã giữ suất bao lâu"): một lượt đồng bộ
       chạy đúng và lâu hơn 120 s sẽ bị chính ta giết.
    """
    from platform_core.llm import admission

    def _con_nhuc_nhich() -> bool:
        return (time.monotonic() - suat.luc_khoi_cuoi) < admission.TRAN_IM_LANG_S

    try:
        with (admission.keep_alive(suat.lease_id, _con_nhuc_nhich)
              if suat.lease_id else nullcontext()):
            yield
    finally:
        _nha_suat(suat.lease_id)


def goi_dong_bo_co_xep_lai(goi: Callable[[], Any], suat: Optional[SuatDongBo], *,
                           han_s: Callable[[], float],
                           ngat_chua: Optional[Callable[[], bool]] = None) -> Any:
    """Chạy `goi()` (lời gọi model của cửa đồng bộ/một-cục); máy B 429 ⇒ XẾP LẠI.

    Phương án C bước 1 (O-04). `goi()` ném `BanError` (máy B trả 429 cho lượt A
    ĐÃ nhận — hai sổ nhả lệch nhịp) ⇒ nhả suất, dòng chờ quay lại `cho` với
    `created_at` cũ, nghỉ `cho_xep_lai_s`, chờ lại ≤ `han_s()` giây, rồi gọi lại
    — tối đa `so_lan_xep_lai_toi_da` lần. Hết lần hoặc hết hạn ⇒ ném lại chính
    `BanError` cuối, cửa trả kết cục bận cũ (hoàn tiền + 503).

    💰 TIỀN GIỮ NGUYÊN trong lúc xếp lại — CÓ CHỦ Ý. `credit.hoan` kết sổ theo
       mã lượt (`_da_ket_so`): hoàn rồi giữ lại cùng `request_id` là để khoản giữ
       mới KHÔNG BAO GIỜ được quyết toán hay hoàn. Nên luật là *"tiền theo LƯỢT,
       không theo LẦN THỬ"*: một khoản giữ, một lần kết sổ, ở mọi đường ra của
       cửa (các nhánh `except` sẵn có đều hoàn).
    ⛔ Hết hạn trong lúc chờ lại ⇒ `BanError` (bận), khách đi ⇒ `ngat.KhachNgat`
       — đúng hai kết cục cửa đã xử lý, không đẻ nhánh mới.
    ⭐ Mỗi lần gọi đều bọc `dieu_phoi.mang_dat_cho(suat.token_dat_truoc)` — số
       đặt chỗ đi lên máy B cùng lượt gọi (O-05).
    """
    import time as _time

    from platform_core.llm import dieu_phoi, ngat, phong_cho, tham_so_da_luot
    from platform_core.llm.cong_vlm import BanError
    from platform_core.public_api import metrics

    ts = tham_so_da_luot.doc()
    lan = 0
    while True:
        try:
            # ⭐ MỐC TIẾN TRIỂN của lớp 2 (xem `giu_suat_dong_bo`): một lượt gọi
            #    máy B vừa bắt đầu. Cửa đồng bộ không có byte chảy dọc đường nên
            #    đây là thứ duy nhất "nhúc nhích" được, và nó phải được ghi cả ở
            #    lần thử SAU KHI XẾP LẠI — không thì một lượt xếp lại lâu sẽ bị
            #    chính luồng nhịp của mình nhả suất.
            if suat is not None:
                suat.cham()
            with dieu_phoi.mang_dat_cho(suat.token_dat_truoc if suat else 0):
                return goi()
        except BanError:
            con_s = float(han_s())
            if (suat is None or suat.yeu_cau is None or not suat.waiter_id
                    or lan >= ts.so_lan_xep_lai_toi_da or con_s <= 0):
                raise
            lan += 1
            metrics.increment("llm:xep_lai")
            log.warning("XEP LAI dong bo rid=%s lan=%s/%s con=%.0fs (may B 429)",
                        suat.yeu_cau.request_id[-8:], lan,
                        ts.so_lan_xep_lai_toi_da, con_s)
            _nha_suat(suat.lease_id)
            suat.lease_id = ""
            if not phong_cho.xep_lai(suat.waiter_id):
                raise
            (NGU_CHO or _time.sleep)(ts.cho_xep_lai_s)
            try:
                suat.lease_id = phong_cho.cho_nhan_chan(
                    suat.yeu_cau, waiter_id=suat.waiter_id,
                    han_s=max(0.0, float(han_s())), ngat_chua=ngat_chua,
                    **_seam_cho())
            except phong_cho.HetCho as e:
                raise BanError(f"het han cho sau khi may B tu choi ({e.ly_do})",
                               retry_after_s=30) from None
            except phong_cho.KhachDi:
                raise ngat.KhachNgat(None) from None


def _chen_nhip(nguon: Generator[str, None, Any], moi_nhip_s: float,
               dang: Callable[[str], Any]) -> Generator[Any, None, Any]:
    """Chuyển lý do chờ của `nguon` thành nhịp (`dang(ly_do)`) mỗi `moi_nhip_s`; trả giá trị cuối.

    Một vòng cho mọi chỗ chờ có nhịp (vào hàng, xếp lại) — hai cửa (byte SSE của
    `/api/v1`, sự kiện `response.queued` của sản phẩm) chỉ khác nhau ở `dang`.
    ⛔ Không đóng `nguon` — bên gọi đóng trong `finally` của nó.
    """
    t_nhip = time.monotonic()
    while True:
        try:
            ly_do = next(nguon)
        except StopIteration as ket:
            return ket.value
        if time.monotonic() - t_nhip >= moi_nhip_s:
            t_nhip = time.monotonic()
            yield dang(ly_do)


def mo_co_xep_lai(tk: TienKiem, cb: ChuanBi, *, han_s: float, bat_dau: float,
                  timeout_s: float = MO_LUONG_GIAY, trang_thai=None,
                  dong_ho=None, ngu=None) -> Generator[str, None, "LuotLuong"]:
    """GENERATOR: mở luồng tới máy B; B 429 ⇒ nhả suất, XẾP LẠI, chờ, mở lại. Trả `LuotLuong`.

    Phương án C bước 1 (O-04). Lượt đã được A nhận (dòng chờ `nhan`, tiền đã
    giữ) mà máy B trả 429 — vì hai sổ slot/pool nhả lệch nhịp — thì trước 17/09
    khách nhận NGAY một khối `overloaded` sau khi đã chờ cả hàng. Nay:

      1. nhả suất (KHÔNG hoàn tiền — xem 💰), `cb.lease_id = ""`;
      2. `phong_cho.xep_lai` — dòng quay lại `cho`, GIỮ `created_at`;
      3. nghỉ `cho_xep_lai_s`, rồi chờ lại trong phần CÒN LẠI của hạn chờ cửa
         (`han_s` tính từ `bat_dau`, `time.monotonic()`), `yield` lý do mỗi nhịp;
      4. được nhận ⇒ `cb.lease_id` mới ⇒ mở lại.

    Tối đa `so_lan_xep_lai_toi_da` lần. Quá lần / hết hạn ⇒ HOÀN TIỀN rồi ném
    `DangBan` (bên gọi phát `overloaded`), `phong_cho.HetCho` hoặc `KhachDi`.

    💰 TIỀN GIỮ NGUYÊN trong lúc xếp lại — có chủ ý, cùng lý do ở
       `goi_dong_bo_co_xep_lai`: `credit.hoan` kết sổ theo mã lượt, nên hoàn rồi
       giữ lại cùng `request_id` là một khoản giữ không bao giờ kết sổ được.
       Đổi lại, MỌI đường ra khỏi hàm này mà không trả `LuotLuong` đều hoàn —
       kể cả khách ngắt giữa lúc chờ lại (`GeneratorExit`).
    ⛔ `cb.waiter_id` rỗng (đường cũ không phòng chờ) ⇒ không xếp lại: không có
       dòng nào để đưa về hàng, hành vi cũ nguyên vẹn.
    """
    from platform_core.llm import phong_cho, tham_so_da_luot
    from platform_core.public_api import metrics

    ts = tham_so_da_luot.doc()
    lan = 0
    while True:
        try:
            return mo_thuong_nguon(cb, timeout_s=timeout_s, trang_thai=trang_thai,
                                   hoan_khi_ban=False)
        except DangBan:
            con_s = float(han_s) - (time.monotonic() - float(bat_dau))
            if (not cb.waiter_id or lan >= ts.so_lan_xep_lai_toi_da or con_s <= 0
                    or not phong_cho.xep_lai(cb.waiter_id)):
                hoan(cb.user_id, cb.request_id)
                raise
            lan += 1
            cb.lease_id = ""
            metrics.increment("llm:xep_lai")
            log.warning("XEP LAI stream rid=%s lan=%s/%s con=%.0fs (may B 429)",
                        cb.request_id[-8:], lan, ts.so_lan_xep_lai_toi_da, con_s)
        try:
            (ngu or time.sleep)(ts.cho_xep_lai_s)
            kw = {}
            if dong_ho is not None:
                kw["dong_ho"] = dong_ho
            if ngu is not None:
                kw["ngu"] = ngu
            con_s = max(0.0, float(han_s) - (time.monotonic() - float(bat_dau)))
            cb.lease_id = yield from phong_cho.cho_nhan(
                _yeu_cau_cho(tk), waiter_id=cb.waiter_id, han_s=con_s, **kw)
        except BaseException:
            # Hết hạn, khách đi, khách ngắt (`GeneratorExit`) — lượt kết thúc ở
            # đây, nên khoản giữ kết thúc cùng nó.
            hoan(cb.user_id, cb.request_id)
            raise


def luong_co_cho(tk: TienKiem, *, loi_sse: Callable[..., bytes],
                 trang_thai=None, timeout_s: float = MO_LUONG_GIAY,
                 han_s: Optional[float] = None, nhip_s: Optional[float] = None,
                 dong_ho=None, ngu=None,
                 so_tay: Optional[dict] = None,
                 nhip_sse: Optional[Callable[[str], bytes]] = None) -> Iterator[bytes]:
    """Byte của cửa `/api/v1` stream: nhịp tim khi chờ → luồng máy B → quyết toán.

    Sau 200 thì không còn mã HTTP: mọi kết cục xấu là MỘT khối lỗi đúng khuôn
    giao thức do `loi_sse(duong, ma, thong_diep)` dựng (`server/api/su_kien_loi.py`).
    Máy B 429 cho lượt đã nhận ⇒ xếp lại trong hạn chờ (`mo_co_xep_lai`), nhịp
    SSE vẫn chảy; chỉ quá lần/hạn mới thành khối `overloaded`.
    """
    from platform_core.llm import phong_cho, tham_so_da_luot
    from platform_core.public_api import metrics

    ts = tham_so_da_luot.doc()
    han = ts.han_cho_stream(tk.la_whale) if han_s is None else han_s
    moi_nhip = ts.nhip_tim_cho_s if nhip_s is None else nhip_s
    bat_dau = time.monotonic()

    def _loi_typed(failure: ModelFailure, ma_cu: str, thong_diep_cu: str) -> bytes:
        return loi_sse(
            tk.duong,
            ma_cu,
            thong_diep_cu,
            failure=failure,
        )

    def _nhip(ly_do: str) -> bytes:
        # Chú thích SSE: mọi client bỏ qua, Cloudflare thấy byte. `nhip_sse` (bên
        # gọi dựng theo giao thức — `su_kien_loi.bo_nhip`) thay khi có: Codex chỉ
        # nạp lại đồng hồ im lặng SSE bằng SỰ KIỆN, không bằng chú thích (R-08).
        if nhip_sse is not None:
            return nhip_sse(ly_do)
        return f": ltt-cho {ly_do}\n\n".encode("ascii", "replace")

    gen, db_luong = _phien_moi()
    try:
        cho = vao_va_cho(tk, db_luong=db_luong, han_s=han, dong_ho=dong_ho, ngu=ngu)
        try:
            cb = yield from _chen_nhip(cho, moi_nhip, _nhip)
            # 🔴 CÔNG BỐ SUẤT NGAY KHI VỪA GIÀNH ĐƯỢC (L-08).
            #
            #    Bên gọi dựng `StreamingResponse` **trước** khi generator này chạy
            #    dòng đầu, nên lúc ấy chưa có `lease_id` để chụp vào đường nhả. Ô
            #    nhớ này là cách duy nhất để đường nhả (`khi_dut` + `BackgroundTask`)
            #    biết phải nhả cái gì. Sau một lần xếp lại, `cb.lease_id` là suất
            #    MỚI — cùng đối tượng, nên đường nhả vẫn thấy đúng.
            #
            # ⛔ GÁN Ở ĐÂY, KHÔNG SỚM HƠN. Khách cắt lúc còn XẾP HÀNG thì `so_tay`
            #    phải vẫn RỖNG — chưa giành được suất nào thì không có gì để nhả,
            #    và nhả bừa là nhả **suất của người khác**. `test_1248` chốt ca này.
            if so_tay is not None:
                so_tay["cb"] = cb
        except phong_cho.HetCho as e:
            metrics.increment(metrics.CAPACITY_REFUSED)
            log.warning("HET CHO stream user=%s ly_do=%s", tk.user_id[:8], e.ly_do)
            yield _loi_typed(
                model_failure(
                    "concurrency_limited", http_status=429,
                    request_id=tk.request_id,
                ),
                "overloaded",
                "The model is busy right now. Please retry shortly.",
            )
            return
        except ThieuCredit:
            yield _loi_typed(
                model_failure(
                    "insufficient_credit", http_status=409,
                    request_id=tk.request_id,
                ),
                "insufficient_credit",
                "Insufficient credit for this request.",
            )
            return
        except phong_cho.KhachDi:
            return
        finally:
            cho.close()

        mo = mo_co_xep_lai(tk, cb, han_s=han, bat_dau=bat_dau, timeout_s=timeout_s,
                           trang_thai=trang_thai, dong_ho=dong_ho, ngu=ngu)
        try:
            luot = yield from _chen_nhip(mo, moi_nhip, _nhip)
            # Công bố luồng: `dong_nguon` (đóng cửa ra mạng tới máy B) và
            # `dam_bao_quyet_toan` đều cần chính đối tượng này.
            if so_tay is not None:
                so_tay["luot"] = luot
        except phong_cho.HetCho as e:
            # Hết hạn trong lúc XẾP LẠI — tiền đã hoàn trong `mo_co_xep_lai`.
            metrics.increment(metrics.CAPACITY_REFUSED)
            log.warning("HET CHO (xep lai) stream user=%s ly_do=%s",
                        tk.user_id[:8], e.ly_do)
            yield _loi_typed(
                model_failure(
                    "concurrency_limited", http_status=429,
                    request_id=tk.request_id,
                ),
                "overloaded",
                "The model is busy right now. Please retry shortly.",
            )
            return
        except phong_cho.KhachDi:
            return
        except DangBan as e:
            phong_cho.ghi_ket_thuc(cb.waiter_id, "ban")
            yield _loi_typed(
                e.failure,
                "overloaded",
                "The model is busy right now. Please retry shortly.",
            )
            return
        except KhongMoDuoc as e:
            phong_cho.ghi_ket_thuc(cb.waiter_id, "qua_dai" if e.qua_dai else "khong_mo_duoc")
            if e.het_gio and not e.qua_dai:
                yield _loi_typed(e.failure, "overloaded", _CAU_HET_GIO)
                return
            yield _loi_typed(
                e.failure,
                "context_length" if e.qua_dai else "upstream",
                "The input exceeds the model's context limit."
                if e.qua_dai
                else "The model could not serve this request.",
            )
            return
        finally:
            mo.close()
        # 🔴 C0-34 (20/09): máy B im quá hạn đọc giữa luồng ⇒ `httpx.ReadTimeout`
        #    thoát khỏi thân phản hồi. 200 đã gửi, nên Starlette không còn trả
        #    được mã nào: khách thấy luồng đứt không `message_stop`, log ghi
        #    "unhandled public api error". `_phat` đã quyết toán/hoàn trong
        #    `finally` của nó; ở đây chỉ còn dựng MỘT khối lỗi đúng khuôn.
        import httpx

        try:
            yield from luot.luong
        except httpx.HTTPError as e:
            if luot.a_da_dong:
                # Chính A đóng cửa vì khách đi — không còn ai để nhận khối lỗi.
                return
            from platform_core.llm.luong_vlm import la_het_gio_doc

            het_gio = la_het_gio_doc(e)
            log.warning("STREAM DUT (%s) rid=%s - tra khoi loi %s",
                        type(e).__name__, cb.request_id[-8:],
                        "overloaded" if het_gio else "upstream")
            failure = model_failure(
                "stream_idle_timeout" if het_gio else "stream_truncated",
                http_status=504 if het_gio else 502,
                request_id=tk.request_id,
            )
            yield _loi_typed(
                failure,
                "overloaded" if het_gio else "upstream",
                _CAU_HET_GIO
                if het_gio
                else "The connection to the model was interrupted. Please retry.",
            )
    finally:
        _dong_phien(gen)


def chuan_bi(db, *, user_id: str, tool_name: str, than: dict, duong: str,
             holder_id: str = "", correlation_id: str = "",
             tien_to: str = "st",
             tim: Optional[Callable[[str], tuple]] = None) -> ChuanBi:
    """Kiểm alias → giành suất → ước token → giữ chỗ → **commit**.

    Ném `ThamSoSai` / `DangBan(nguon="suat")` / `ThieuCredit` — cả ba đều xảy ra
    **trước** khi có bất kỳ tác dụng phụ nào còn lại (rollback đã dọn).
    """
    from platform_core import credit
    from platform_core.llm import admission, thanh_toan
    from platform_core.public_api import metrics

    _manifest, tool = (tim or tim_tool)(tool_name)
    executor = for_tool(tool)

    ten = str(than.get("model") or "")
    aliases = executor.aliases()
    if ten not in aliases:
        raise ThamSoSai(f"`model` phai la mot trong {list(aliases)}")
    tin = uoc_tin_nhan(than)
    if not tin:
        raise ThamSoSai("yeu cau khong mang dau vao nao de tra loi")

    # Dịch alias -> id nội bộ NGAY TRƯỚC KHI ra khỏi nền tảng. Khách không bao
    # giờ nhìn thấy id thật, và mã của khách không ghim vào nó (test_212).
    gui = dict(than)

    # 🔴 KIEM THAM SO SINH O DAY, TRUOC KHI THAN DI LEN MAY B.
    #
    #    Dong `gui = dict(than)` ngay tren chep CA than request. Truoc 14/09 do
    #    la toan bo "kiem" cua cua stream, nen do duoc tren production:
    #
    #        top_p=5  ->  /chat/completions (dong bo) : 400 invalid_request
    #        top_p=5  ->  /messages         (stream)  : 200, chay binh thuong
    #
    #    Mot hop dong cong bo, hai cua tra loi khac nhau — va cua sai la cua
    #    KHONG kiem, vi no de mot gia tri hop dong CAM di thang toi bo giai ma.
    #
    # ⭐ Khuon chuan (vLLM `entrypoints/openai/.../protocol.py`): `stream` chi la
    #    MOT TRUONG nhu moi truong khac, va moi validator chay TRUOC khi re
    #    nhanh stream. Kiem mot lan, cho moi cua.
    #
    # ⛔ Goi `validate_generation`, KHONG goi `validate`: `/messages` mang
    #    `system`, `/responses` mang `input` co the la chuoi tran. Bo kiem day
    #    du doi moi phan tu `messages` co `role` va se nem 500 — dung loi
    #    `_tin_that` da ghi. Ham sinh chi kiem tham so sinh va **bo qua moi khoa
    #    no khong biet**, nen `top_k`/`stop_sequences`/`metadata` cua client
    #    Anthropic van di qua duoc.
    _kiem_sinh = getattr(executor, "validate_generation", None)
    if callable(_kiem_sinh):
        gui.update(_kiem_sinh_boc(_kiem_sinh, executor, than))
    chuan_hoa_tool_choice(gui, duong)  # theo giao thức của cửa (test_1522)
    gui, _bo_qua = chuan_hoa_suy_nghi(gui, ten)  # L-26, cùng hàm với `tien_kiem`
    dat_effort_cho_engine(gui, duong)  # T1c
    gui["model"] = executor.model_id(ten)
    _go_dinh_danh_khach(gui)  # T4 P2, cùng hàm với `tien_kiem`

    # ⛔ KHÔNG tự ghép chuỗi: `credit_entries.job_id` là VARCHAR(36).
    request_id = thanh_toan.ma_luot(tien_to)

    # Ước TRƯỚC khi giành suất (không tác dụng phụ): lease phải mang số token đặt
    # chỗ, nếu không nó vô hình với sổ ngân sách KV (multijob) và hai đường cộng
    # lại vượt pool.
    vao_uoc = int(executor.estimate_input(tin))
    xin_ra = tran_token_ra(than, vao_uoc, executor)

    lease_id = ""
    token_dat_truoc = 0
    la_whale = False
    suc = _suc_chua(tool, ten)
    tai_nguyen, so_suat, _pool = _bo_ba(suc)
    if tai_nguyen and so_suat > 0:
        from platform_core.llm import luat_nhan
        luat = _dat_cho(suc, lop=luat_nhan.TUONG_TAC, token_vao_uoc=vao_uoc,
                        xin_ra=xin_ra, so_anh=dem_anh(than))
        token_dat_truoc = int(luat.get("token_dat_truoc", 0))
        la_whale = bool(luat.get("la_whale", False))
        ticket = admission.acquire(
            db, resource=tai_nguyen, slots=so_suat, user_id=user_id,
            mode="stream", holder_id=holder_id or request_id, **luat)
        if ticket is None:
            db.rollback()
            raise DangBan("het suat thuc thi", nguon="suat", tai_nguyen=tai_nguyen,
                          thu_lai_sau_s=15)
        lease_id = ticket.id

    # 🔴 GHI GIÁ TRỊ ĐÃ KẸP TRỞ LẠI THÂN GỬI LÊN, đúng TÊN TRƯỜNG của cửa.
    #    Kẹp cái mình thu tiền mà không kẹp cái mình gửi đi ⇒ máy B trả 413
    #    (H38/L2). Không khai gì thì tên theo cửa: `/responses` chỉ đọc
    #    `max_output_tokens` — ghi nhầm tên là llama-server dùng mặc định 1.024.
    _kep_tran_gui(gui, duong, xin_ra)
    _dat_budget_may_chu(gui, duong, executor, ten, xin_ra)

    try:
        da_giu = thanh_toan.giu_cho_luot(
            db, user_id=user_id, request_id=request_id,
            token_vao_uoc=vao_uoc, max_tokens=xin_ra, model=ten)
    except credit.ThieuCreditError as e:
        # Không đủ tiền thì không đốt GPU. Chốt trước, không phải sau.
        metrics.increment(metrics.CREDIT_EXHAUSTED)
        log.info("khach het credit tai %s: user=%s", duong, user_id[:8])
        db.rollback()
        # Suất vừa giành nằm trong savepoint của giao dịch vừa cuộn; nhưng
        # KHÔNG tin điều đó — pysqlite không giữ SAVEPOINT đúng chuẩn, và một
        # suất mồ côi chỉ tự lành sau ORPHAN_TIMEOUT (20 phút GPU nằm không).
        # `release_by_id` idempotent: đã cuộn rồi thì nó chỉ trả False.
        _nha_suat(lease_id)
        raise ThieuCredit.tu_loi(e) from None

    # 🔴 CHỐT GIAO DỊCH TRƯỚC KHI CHẠM MODEL (xem docstring module).
    db.commit()
    return ChuanBi(db=db, user_id=user_id, tool_name=tool_name, duong=duong,
                   than_gui=gui, request_id=request_id, lease_id=lease_id,
                   da_giu=da_giu, token_vao_uoc=vao_uoc, xin_ra=xin_ra,
                   model_alias=ten, executor=executor,
                   token_dat_truoc=token_dat_truoc,
                   correlation_id=correlation_id, la_whale=la_whale)


# ── Bước 2: mở luồng tới máy B ───────────────────────────────────────────────

async def bat_dong_bo_hoa(
        nguon: Iterator[bytes],
        dong_nguon: Optional[Callable[[], None]] = None,
        khi_dut: Optional[Callable[[], None]] = None) -> AsyncIterator[bytes]:
    """Bọc luồng ĐỒNG BỘ thành BẤT ĐỒNG BỘ tại biên phản hồi HTTP — vá L-08.

    ## Sự cố

    Khách cắt giữa một lượt stream ⇒ lease `mode=stream` vẫn sống **≥643 s**
    trong khi máy B đã rảnh (`requests_processing = 0`). Một suất GPU bị giữ cho
    một người đã đóng cửa sổ.

    ## Vì sao phải đổi CẤU TRÚC chứ không thêm một phép thăm

    Đọc mã thư viện đang cài, từng mắt xích:

        1. uvicorn khai ASGI `spec_version` "2.3" (< 2.4) ⇒ nhánh CÓ
           `listen_for_disconnect` mới chạy. Ngắt **có** được nghe.
        2. `await self.background()` nằm NGOÀI `async with` ⇒ `BackgroundTask`
           nhả lease **có** chạy khi khách cắt.
        3. Nhưng `LuotLuong.luong` là `Iterator` **đồng bộ**, nên Starlette bọc
           bằng `iterate_in_threadpool` — và cancel scope của anyio **không cắt
           được một luồng đang chờ đọc socket**.

    ⇒ Huỷ được phát, rồi kẹt chờ luồng; task group không sập; `background()`
      không tới lượt; lease không nhả. 643 s là lúc **máy B buông**.

    ## ⛔ MỘT BẢN VÁ "HIỂN NHIÊN" ĐÃ ĐƯỢC THỬ VÀ ĐÃ HỎNG (13/09)

    Bản trước thăm `request.receive()` theo nhịp 1 s để tự thoát vòng. Nó đã
    deploy, và đo trên máy thật: **không một lần nào** vị từ trả `True`.

    Vì ở cửa stream, Starlette **đã đỗ sẵn** trên `receive` qua
    `listen_for_disconnect` từ lúc phản hồi bắt đầu, nên `http.disconnect` tới
    tay NÓ chứ không tới tay ta. Và thứ nó làm khi nhận được là huỷ cancel scope
    — đúng cái không cắt được threadpool. **Bên thắng cuộc đua là bên không làm
    gì được.** Bản ấy còn thu ~5 % độ trễ của mọi lượt stream để hỏi một câu
    không bao giờ có câu trả lời.

    ## Vì sao bản NÀY khác về bản chất — không phải khác về tham số

    Nó **không tranh `receive` với ai**:

        generator ĐỒNG BỘ bị bỏ rơi  -> không ai ném gì vào  -> `finally` treo
        generator BẤT ĐỒNG BỘ bị huỷ -> `CancelledError` được ném VÀO đúng điểm
                                        `await` -> `finally` chạy NGAY

    Khi khách cắt, Starlette huỷ task group; lượt đang `await` ở đây nhận huỷ,
    `finally` đóng `nguon`, `GeneratorExit` xuống tới `_phat` rồi tới
    `luong_vlm._di` ⇒ `client.close()` ⇒ máy B nhả slot ⇒ `BackgroundTask` nhả
    lease.

    🔴 `abandon_on_cancel=True` là BẢN LỀ, không phải một cờ tinh chỉnh. Mặc
       định của anyio là `False`: lượt bị huỷ **vẫn đứng chờ luồng chạy xong** —
       tức đúng cái ta đang sửa. Bỏ cờ này đi thì hàm này thành vô nghĩa.

    ⚠️ Luồng bị bỏ rơi vẫn kẹt trong `next()` cho tới khi `nguon.close()` ở
       `finally` làm `httpx` đóng socket và lệnh đọc ấy vỡ. Đó là lý do
       `finally` phải đóng nguồn, không chỉ thoát vòng.

    ⛔ CHỈ dùng ở biên phản hồi HTTP. Đường job vẫn tiêu thụ `luot.luong` đồng
       bộ (xem chỗ `for khoi in luot.luong` phía dưới); đổi chính `luot.luong`
       thành async là phá đường ấy.

    ## Bằng chứng — TRA ĐƯỢC, và nó nói ngược điều từng viết ở chính đây

    ⛔ Bản trước của khối này trích `fastapi/fastapi#7572` và
       `Kludex/starlette#2866`. **Cả hai không tồn tại** — API trả 404 ngày
       13/09/2026, trong khi `#3538`/`#3000` cùng kho trả về bình thường. Chúng
       được bịa ra trong lúc tin rằng mình đang đối chiếu cộng đồng. Ghi lại để
       người sau biết: một trích dẫn chỉ được dùng khi tra ra.
       (`ggml-org/llama.cpp#27572` ở các tệp khác thì CÓ THẬT — đừng gỡ nhầm.)

    Thay bằng ba sự thật kiểm được:

    1. `starlette/responses.py:250` (bản 1.3.1 đang cài) — thân phản hồi chỉ
       được `async for`, **không bao giờ `aclose()`**. Nên `finally` của một
       async generator không phải chỗ được bảo đảm chạy ĐÚNG LÚC; nó chạy khi
       Python thu gom. Đo trên máy thật: lease sống thêm **~225 s**.
    2. `starlette/background.py` (cùng bản) — `BackgroundTask.__call__` **không
       có `CancelScope(shield=True)`**. Bản vá che chắn cộng đồng đề xuất ở
       `Kludex/starlette#1438` chưa từng được gộp; issue ấy đóng bằng cách sửa
       `BaseHTTPMiddleware` (PR #1715).
    3. `Kludex/starlette#1438` — *"Background tasks are cancelled if the client
       closes connection"*, và tác giả chốt: **chỉ xảy ra khi có ít nhất một
       `BaseHTTPMiddleware` trong chuỗi**. Ta có **bốn** tầng.
       `Kludex/starlette#3458` (đóng 06/09/2026) cho thấy thời điểm chạy
       background dưới `BaseHTTPMiddleware` **vẫn** lệch hợp đồng tài liệu —
       năm PR đề xuất, **cả năm đóng mà không gộp**.

    ⇒ Hệ quả thiết kế: **đừng treo việc nhả một suất GPU vào `finally` của
      generator, cũng đừng treo vào riêng `BackgroundTask`.** Đường nhả đi theo
      `khi_dut` — thứ đo được là chạy ở **+0,05 s** trong mọi cấu hình thử: có
      và không middleware, cắt lúc treo ở `yield` lẫn lúc nguồn đang bị chặn.
    """
    import anyio.to_thread

    het = object()

    def _mot() -> Any:
        try:
            return next(nguon)
        except StopIteration:
            return het

    try:
        while True:
            khoi = await anyio.to_thread.run_sync(_mot, abandon_on_cancel=True)
            if khoi is het:
                return
            yield khoi
    finally:
        # 🔴 ĐÓNG KẾT NỐI TRƯỚC, ĐÓNG GENERATOR SAU. Thứ tự này là bản vá, không
        #    phải sở thích.
        #
        #    `abandon_on_cancel=True` buông lượt chờ, nhưng LUỒNG kia **vẫn đang
        #    ở trong** `next(nguon)`. Đo bằng một bộ mô phỏng một biến số: gọi
        #    `nguon.close()` lúc ấy ném `ValueError: generator already executing`,
        #    `finally` của nguồn **không bao giờ chạy**, và `client.close()` của
        #    httpx ở lại chưa gọi ⇒ lease nhả mà **máy B vẫn giữ slot**. Mới đi
        #    được nửa đường, và là nửa khách không nhìn thấy.
        #
        # ⭐ `dong_nguon()` đóng thẳng `httpx.Client`. Lượt đọc đang chặn trong
        #    luồng bỏ rơi vỡ ngay, `nguon` bung ra, `finally` của nó chạy TỰ
        #    NHIÊN (và gọi lại `dong_nguon` — nên hàm ấy buộc phải idempotent).
        try:
            if dong_nguon is not None:
                try:
                    dong_nguon()
                except Exception:  # noqa: BLE001 - duong huy khong duoc nem
                    log.warning("khong dong duoc cua ra mang toi may B",
                                exc_info=True)
            # Vét nốt: nguồn đã bung thì `close()` chỉ là xác nhận; còn đang chạy
            # thì nó ném và ta bỏ qua — kết nối đã đóng ở trên mới là thứ có giá
            # trị.
            dong = getattr(nguon, "close", None)
            if callable(dong):
                try:
                    dong()
                except Exception:  # noqa: BLE001
                    log.debug("nguon con dang chay, bo qua close()", exc_info=True)
        finally:
            # 🔴 LỚP 1 CỦA CƠ CHẾ NHẢ SUẤT — và thứ tự ở đây là bản vá, không
            #    phải sở thích: đóng kết nối TRƯỚC (bảo máy B thôi sinh), nhả
            #    suất SAU. Nhả trước thì người thứ bảy được vào trong khi GPU
            #    vẫn đang bận — sổ sách sạch mà máy thì không.
            #
            # ⛔ `khi_dut` nằm trong `finally` LỒNG, nên nó chạy kể cả khi
            #    `dong_nguon` ném. Đó là cả điểm của lớp này: nó là đường nhả
            #    DUY NHẤT đã được đo là chạy đúng giờ ở mọi cấu hình.
            if khi_dut is not None:
                try:
                    khi_dut()
                except Exception:  # noqa: BLE001
                    log.warning("khong nha duoc suat khi khach dut",
                                exc_info=True)


def _luong_rong() -> Generator[bytes, None, None]:
    """Generator rỗng làm mặc định cho `LuotLuong.luong`.

    Là một hàm chứ không phải `iter(())`: mặc định phải có `.close()` như mọi
    giá trị thật của trường này, nếu không thì một `LuotLuong` chưa gán luồng
    sẽ vỡ đúng ở đường khách ngắt — đường ít được chạy nhất.
    """
    return
    yield b""  # pragma: no cover - không bao giờ tới, chỉ để hàm là generator


@dataclass
class LuotLuong:
    """Một luồng đang chảy. `luong` chuyển byte nguyên xi và **tự quyết toán**."""

    chuan_bi: ChuanBi
    content_type: str
    #: ⚠️ `Generator` chứ không `Iterator`: hai chỗ dưới gọi `.close()` để đóng
    #: luồng bên dưới cho `finally` của nó quyết toán tiền (multijob 1.5), mà
    #: `.close()` chỉ generator mới có. Khai `Iterator` thì mypy báo
    #: "has no attribute close" — đúng, và nó đúng về một điều thật: truyền vào
    #: đây một iterator thường sẽ vỡ ở lúc khách ngắt.
    luong: Generator[bytes, None, None] = field(default_factory=_luong_rong)
    #: Đóng cửa ra mạng tới máy B — gọi được từ LUỒNG KHÁC, và idempotent.
    #:
    #: ⛔ KHÔNG thay được bằng `luong.close()`. Đường huỷ của cửa stream chạy ở
    #:    vòng lặp sự kiện trong khi `luong` đang treo giữa một lượt đọc socket ở
    #:    luồng threadpool đã bị bỏ rơi; đóng một generator đang thực thi ở luồng
    #:    khác ném `ValueError: generator already executing`, `finally` không bao
    #:    giờ chạy, và kết nối httpx ở lại mở. Xem L-08.
    dong_nguon: Optional[Callable[[], None]] = None
    dem: DemToken = field(default_factory=DemToken)
    #: Điền sau khi quyết toán (trong `finally` của `luong`).
    ket_qua: Any = None
    #: "xong" | "khach_ngat" | "loi" — điền khi luồng kết thúc.
    ket_thuc: str = ""
    #: 🔴 PHÍA A đã tự đóng cửa ra máy B (`dong_nguon`, đường huỷ khi khách đi).
    #:
    #: Sự cố 19/09/2026: khách (qua Cloudflare) huỷ luồng ⇒ `bat_dong_bo_hoa`
    #: gọi `dong_nguon` ⇒ lượt đọc đang chặn ở luồng threadpool vỡ bằng
    #: `httpx.ReadError` (tái hiện 5/5, httpx 0.28.1) — **không** phải
    #: `GeneratorExit`. `_phat` ghi nó thành `STREAM LOI` rồi `mo.hong()` ⇒
    #: `api_pool.danh_dau_loi` nhánh 5xx/mạng. Năm lượt khách đi liền nhau là
    #: khoá DUY NHẤT của `ltt_llm` sang `APIKEY_ERROR` và mọi khách nhận 500.
    #:
    #: ⇒ Lỗi đọc xảy ra SAU khi cờ này dựng là hệ quả của việc ta đóng, không
    #:   phải lỗi của thượng nguồn. Test: `test_1523_khach_ngat_khong_phat_khoa`.
    a_da_dong: bool = False
    #: Đã quyết toán chưa. Cờ này làm việc quyết toán **idempotent** giữa hai
    #: đường độc lập — xem `dam_bao_quyet_toan`.
    da_quyet_toan: bool = False
    #: 🔴 LỚP 2 của cơ chế nhả suất (L-08): mốc **byte cuối cùng đi qua**, theo
    #: `time.monotonic()`. `admission.keep_alive` hỏi mốc này trước mỗi nhịp;
    #: im quá `TRAN_IM_LANG_S` thì luồng nhịp tự nhả suất.
    #:
    #: ⛔ Khởi tạo bằng `monotonic()` chứ **không** bằng `0.0`: giữa lúc vào
    #:    `with keeper` và byte đầu tiên là cả một lượt prefill hợp lệ, có thể
    #:    hàng trăm giây. Mốc `0.0` làm nhịp đầu tiên thấy "im 400 000 giây" và
    #:    giết ngay một lượt đang chạy đúng.
    luc_khoi_cuoi: float = field(default_factory=time.monotonic)


def dam_bao_quyet_toan(luot: "LuotLuong") -> None:
    """Lưới an toàn: quyết toán nếu `finally` của `_phat` **chưa từng chạy**.

    🔴 VÌ SAO CẦN — ĐO ĐƯỢC 09/09, VÀ NÓ LÀ TIỀN THẬT.

       `_phat` quyết toán trong `finally`. Nhưng một `finally` **chỉ tồn tại sau
       khi generator chạy dòng đầu tiên**. Khách ngắt kết nối *trước byte đầu*
       thì Starlette không bao giờ lặp qua nó, khối `try` chưa từng được vào, và
       khoản `hold` nằm lại, và **không đường nào kết sổ nó cho tới 24 giờ sau**:

           g = _phat(mo, luot); g.close()
             -> quyet_toan KHONG duoc goi          (do that, khong suy luan)
           next(g); g.close()
             -> quyet_toan DUOC goi

    ⛔ VÀ KHÔNG AI QUÉT NÓ. Cửa này **không tạo `Job`**, nên `_hoan_credit` của
       worker — thứ vẫn dọn cho hàng đợi job — không bao giờ nhìn thấy dòng hold
       mồ côi. Đúng câu `test_292_tien_ket_trong_hold.py` đã viết cho cửa đồng
       bộ; chỉ là ở đó nó kết luận *"cửa streaming không dính, vì nó quyết toán
       trong `finally`"* — và **kết luận ấy sai đúng ở ca generator chưa khởi
       động**.

    ⭐ ĐÂY LÀ CÙNG MỘT KHUYẾT TẬT ĐÃ ĐƯỢC HỌC MỘT LẦN, Ở MỘT TẦNG KHÁC. Sự cố
       31/08 trên máy B: `boc_luong` trả suất trong `finally`, generator không
       khởi động, suất bị giữ vĩnh viễn, cổng trả 429 suốt sáu giờ. Bản vá ở đó
       là `BackgroundTask` — *"chạy khi PHẢN HỒI kết thúc, kể cả khi thân chưa
       từng được đọc"*. Máy A học bài đó cho **suất** (`admission.release_by_id`
       đã đi qua `BackgroundTask`) nhưng **không** cho **tiền**.

    ⇒ Hàm này là đường thứ hai, độc lập với việc generator có chạy hay không.
      Nó **cộng thêm** chứ không thay thế `finally`: hai đường cho cùng một
      việc, và `da_quyet_toan` bảo đảm chỉ một đường thật sự thu.
    """
    if luot.da_quyet_toan:
        return
    cb = luot.chuan_bi
    luot.da_quyet_toan = True
    if not luot.ket_thuc:
        luot.ket_thuc = "khach_ngat_truoc_byte_dau"
    log.warning("STREAM CHUA TUNG CHAY rid=%s - quyet toan bang luoi an toan",
                cb.request_id[-8:])
    # 🔴 `model=` LÀ BẮT BUỘC (D07) VÀ ĐƯỜNG NÀY TẮT ĐÃ QUÊN NÓ.
    #    `quyet_toan` đặt `model` sau `*` **có ý** để một bên gọi cũ đỏ ngay thay
    #    vì lặng lẽ nhận `trang_thai` vào đúng chỗ của model. Đường thứ nhất
    #    (bên dưới) truyền đúng; **lưới an toàn này thì không** — tức nó sẽ ném
    #    `TypeError` đúng lúc nó được gọi: khi một lượt stream **chưa từng chạy**
    #    mà vẫn phải quyết toán. Đổi một bút toán lấy một ngoại lệ, ở đúng cái
    #    nhánh sinh ra để cứu những lượt không ai nhìn.
    #    `mypy` bắt được (`call-arg 0 → 1`); không phép kiểm nào đi qua nhánh này.
    luot.ket_qua = quyet_toan(cb.user_id, cb.request_id, luot.dem, cb.da_giu, None,
                              model=cb.model_alias)


def _nha_suat(lease_id: str) -> None:
    if not lease_id:
        return
    from platform_core.llm import admission
    admission.release_by_id(lease_id)


def mo_thuong_nguon(cb: ChuanBi, *, timeout_s: float = MO_LUONG_GIAY,
                    trang_thai=None, hoan_khi_ban: bool = True) -> LuotLuong:
    """Mở luồng tới máy B. Hỏng thì **hoàn đủ + nhả suất** rồi ném.

    Ném `DangBan(nguon="thuong_nguon")` khi máy B trả 429, `KhongMoDuoc` khi
    khác. Cả hai đều đã hoàn tiền trước khi ném — bên gọi không phải hoàn lại.

    `hoan_khi_ban=False` (chỉ `mo_co_xep_lai`): máy B 429 ⇒ nhả suất nhưng GIỮ
    tiền, vì lượt sắp xếp lại và `credit.hoan` kết sổ vĩnh viễn theo mã lượt.
    Bên gọi ấy chịu trách nhiệm hoàn ở mọi đường ra.
    """
    from platform_core.llm import luong_vlm
    from platform_core.public_api import metrics

    try:
        mo = luong_vlm.mo(
            cb.db, duong=cb.duong, than=cb.than_gui, timeout_s=timeout_s,
            request_id=cb.request_id, token_dat_truoc=cb.token_dat_truoc)
    except luong_vlm.KhongMoDuocLuong as e:
        if e.ban and not hoan_khi_ban:
            # 💰 NGOẠI LỆ DUY NHẤT của "hoàn trước mọi thứ" (phương án C bước 1):
            #    lượt sắp XẾP LẠI nên GIỮ tiền; `mo_co_xep_lai` hoàn ở mọi đường ra.
            _nha_suat(cb.lease_id)
            metrics.increment(metrics.CAPACITY_REFUSED)
            log.warning("BAN luong (xep lai): user=%s duong=%s ly_do=%s",
                        cb.user_id[:8], cb.duong, e.ly_do)
            raise DangBan(
                e.ly_do,
                nguon="thuong_nguon",
                thu_lai_sau_s=e.thu_lai_sau_s,
                failure=e.failure,
            ) from e
        hoan(cb.user_id, cb.request_id)
        _nha_suat(cb.lease_id)
        if e.ban:
            # ⛔ BẬN ≠ HỎNG. Khách KHÔNG bị thu tiền. Đếm vào `CAPACITY_REFUSED`
            #    để người trực thấy tần suất, không chỉ thấy một dòng log.
            metrics.increment(metrics.CAPACITY_REFUSED)
            log.warning("BAN luong: user=%s duong=%s ly_do=%s",
                        cb.user_id[:8], cb.duong, e.ly_do)
            raise DangBan(
                e.ly_do,
                nguon="thuong_nguon",
                thu_lai_sau_s=e.thu_lai_sau_s,
                failure=e.failure,
            ) from e
        log.warning("khong mo duoc luong cho user=%s: %s", cb.user_id[:8], e.ly_do)
        raise KhongMoDuoc(e.ly_do, failure=e.failure) from e
    except BaseException:
        hoan(cb.user_id, cb.request_id)
        _nha_suat(cb.lease_id)
        raise

    metrics.increment("chat:stream")
    luot = LuotLuong(chuan_bi=cb, content_type=mo.content_type)
    gan_luong(mo, luot, trang_thai=trang_thai)
    return luot


def gan_luong(mo, luot: LuotLuong, *, trang_thai=None) -> None:
    """Nối một luồng đã mở (`LuongMo`) vào `luot`: `luong` và `dong_nguon`."""
    luot.luong = _phat(mo, luot, trang_thai=trang_thai)
    # Mang theo đường đóng THẲNG tới httpx. Đường huỷ cần nó vì `luong.close()`
    # ném khi luồng đọc còn đang chạy — xem `dong_nguon` ở `LuotLuong`.
    #
    # ⛔ `getattr` CHỨ KHÔNG `mo.dong_nguon`. Bản giả của `LuongMo` trong test
    #    (`GiaLuong`) đóng vai *"một luồng đã mở"*, không đóng vai *"chữ ký đầy
    #    đủ của `LuongMo` hôm nay"*. Viết thẳng làm **57 phép kiểm đỏ** ngay lần
    #    gate kế — không phải vì mã sai mà vì bên tiêu thụ chặt hơn thứ nó nhận.
    #
    # ⚠️ Đây là lần THỨ NĂM trong một phiên cùng một mẫu (`executor.run`,
    #    `danh_dau_loi`, bản giả không giữ tham chiếu, `Test-Path` trên thư mục
    #    rỗng). Luật rút ra: **bên tiêu thụ phải khoan dung với bản giả**, y như
    #    một hàm giả nhận `**kw` thay vì liệt kê tham số.
    dong = getattr(mo, "dong_nguon", None)
    if not callable(dong):
        luot.dong_nguon = None
        return

    def _a_dong_nguon() -> None:
        # 🔴 DỰNG CỜ TRƯỚC, ĐÓNG SAU (sự cố 19/09). Đóng `httpx.Client` làm lượt
        #    đọc đang chặn ở luồng kia vỡ bằng `httpx.ReadError`; `_phat` phải
        #    biết lỗi ấy là do CHÍNH TA đóng — xem `LuotLuong.a_da_dong`.
        luot.a_da_dong = True
        dong()

    luot.dong_nguon = _a_dong_nguon


def mo_luong_tho(db, *, user_id: str, tool_name: str, than: dict, duong: str,
                 holder_id: str = "", correlation_id: str = "",
                 timeout_s: float = MO_LUONG_GIAY, trang_thai=None) -> LuotLuong:
    """`chuan_bi` + `mo_thuong_nguon` — cho cửa cần **byte nguyên xi** (`/api/v1`)."""
    cb = chuan_bi(db, user_id=user_id, tool_name=tool_name, than=than,
                  duong=duong, holder_id=holder_id, correlation_id=correlation_id)
    return mo_thuong_nguon(cb, timeout_s=timeout_s, trang_thai=trang_thai)


# ── Bước 3: chuyển byte, đếm, quyết toán ─────────────────────────────────────

def _co_du_lieu_sse(khoi: bytes) -> bool:
    """Khối có ít nhất một dòng SSE không phải chú thích (`:` đầu dòng) và không rỗng.

    Nhịp tim của cổng B là dòng chú thích — nó nói "luồng còn sống", không nói
    "prefill đã xong". Mảnh giữa dòng (không bắt đầu bằng `:`) tính là dữ liệu.
    """
    return any(d.strip() and not d.startswith(b":") for d in khoi.splitlines())


def _phat(mo, luot: LuotLuong, *, trang_thai=None) -> Generator[bytes, None, None]:
    """Chuyển byte nguyên xi, đếm token dọc đường, quyết toán khi hết.

    ⛔ `finally` chứ không phải "sau vòng lặp" — xem docstring module.
    """
    from platform_core.llm import admission

    cb = luot.chuan_bi
    dem = luot.dem
    vo: Optional[BaseException] = None
    khach_ngat = False
    t0 = time.monotonic()
    n_khoi = 0
    t_byte_dau: Optional[float] = None
    def _con_nhuc_nhich() -> bool:
        """Vị từ LỚP 2: có byte nào đi qua trong hạn không.

        ⭐ Nó trả lời câu **"công việc còn tiến triển không"**, khác hẳn câu mà
           nhịp tim cũ trả lời là **"luồng còn sống không"**. Chính khoảng cách
           giữa hai câu ấy là chỗ L-08 sống sót qua cả ba lớp dọn.
        """
        return (time.monotonic() - luot.luc_khoi_cuoi) < admission.TRAN_IM_LANG_S

    keeper = (admission.keep_alive(cb.lease_id, _con_nhuc_nhich)
              if cb.lease_id else nullcontext())
    with keeper:
        try:
            for khoi in mo.luong:
                if t_byte_dau is None and _co_du_lieu_sse(khoi):
                    t_byte_dau = time.monotonic() - t0
                    if cb.lease_id:
                        # Prefill xong ⇒ thôi là whale (luật ≤1 whale nói về PREFILL)
                        # và thôi "đang prefill" (L-29: whale chờ MỌI lượt còn
                        # prefill — lượt ngắn cũng phải báo, không riêng whale).
                        # ⛔ Chỉ khối có DỮ LIỆU: B gửi `: ping` mỗi 15 s TRONG lúc
                        #    prefill — xoá cờ ở nhịp tim cho whale thứ hai prefill
                        #    chồng (nghiệm thu production 17/09: chồng 24,9 s).
                        admission.danh_dau_prefill_xong(cb.lease_id)
                n_khoi += 1
                luot.luc_khoi_cuoi = time.monotonic()   # lời khai của LỚP 2
                dem.nhin(khoi)
                yield khoi
        except GeneratorExit:
            khach_ngat = True
            raise
        except BaseException as e:                              # noqa: BLE001
            if luot.a_da_dong:
                # Ta đóng cửa ra máy B vì khách đi ⇒ lượt đọc vỡ. KHÁCH NGẮT,
                # không phải thượng nguồn hỏng — xem `LuotLuong.a_da_dong`.
                khach_ngat = True
            else:
                vo = e
            raise
        finally:
            dt = time.monotonic() - t0
            luot.ket_thuc = "khach_ngat" if khach_ngat else ("loi" if vo else "xong")
            log.warning(
                "STREAM %s rid=%s dur=%.1fs ttfb=%s khoi=%s token_ra=%s",
                luot.ket_thuc.upper(), cb.request_id[-8:], dt,
                (f"{t_byte_dau:.1f}s" if t_byte_dau is not None else "-"),
                n_khoi, dem.token_ra)
            # Duong THU NHAT. `dam_bao_quyet_toan` la duong thu hai, doc lap.
            luot.da_quyet_toan = True
            luot.ket_qua = quyet_toan(cb.user_id, cb.request_id, dem, cb.da_giu,
                                      trang_thai, model=cb.model_alias)
            if vo is not None:
                from platform_core.llm.luong_vlm import la_het_gio_doc

                if la_het_gio_doc(vo):
                    # C0-34: máy B im quá hạn đọc = nghẽn, không phải khoá
                    # hỏng. Không `hong`, cũng không `xong` (không có token).
                    log.warning("STREAM HET GIO DOC rid=%s - khong phat khoa",
                                cb.request_id[-8:])
                else:
                    mo.hong(vo)
            else:
                mo.xong(tokens=dem.token_ra)
            if cb.waiter_id:
                from platform_core.llm import phong_cho

                # T4 P2: số đo vào sổ lượt — token (None nếu chưa thấy `usage`)
                # và TTFB phía A (None nếu chết trước byte dữ liệu đầu).
                phong_cho.ghi_ket_thuc(
                    cb.waiter_id, luot.ket_thuc,
                    so_do=phong_cho.SoDo.tu_su_dung(dem.su_dung(), ttfb_s=t_byte_dau))


def quyet_toan(user_id: str, request_id: str, dem: DemToken, da_giu: int,
               trang_thai=None, *, model: str):
    """Chốt tiền, trong một phiên CSDL **mới**. Trả `KetQuaThu` hoặc `None`.

    ⚠️ Phiên của request đã đóng từ lúc phản hồi bắt đầu — generator này chạy sau
       đó. Dùng lại phiên cũ là `DetachedInstanceError` hoặc tệ hơn: một giao
       dịch không bao giờ được commit.

    🔴 `model` là **keyword bắt buộc** (D07): cửa stream giữ tiền lúc được nhận
       và quyết toán ở đây, hai chỗ cách nhau cả một lượt sinh token. Bí danh đi
       kèm trong `ChuanBi.model_alias` suốt đường đó, nên không có chỗ nào phải
       đoán lại — và đặt nó sau `*` là để một bên gọi cũ **đỏ ngay**, chứ không
       lặng lẽ nhận `trang_thai` vào đúng chỗ của model.
    """
    from platform_core.db import get_session
    from platform_core.llm import thanh_toan

    gen = get_session()
    db = next(gen)
    try:
        thu = thanh_toan.quyet_toan_hoac_hoan(
            db, user_id=user_id, request_id=request_id, su_dung=dem.su_dung(),
            model=model)
        db.commit()
        # Sổ request của `/api/v1` đọc `api_credit_delta` SAU generator này
        # (`server/api/guard.py:_write_request_log_muon`). Client nội bộ truyền
        # `None` — nó đọc `ket_qua` trực tiếp.
        if trang_thai is not None:
            trang_thai.api_credit_delta = -int(thu.thu_credit)
        log.info("stream %s: giu=%s thu=%s token_ra=%s do_duoc=%s",
                 request_id[-8:], da_giu, thu.thu_credit, dem.token_ra,
                 dem.do_duoc)
        return thu
    except Exception:                                           # noqa: BLE001
        db.rollback()
        # 🔴 Ồn ào có chủ ý. Không quyết toán được nghĩa là phần giữ chỗ nằm lại
        #    trên tài khoản khách — tiền của họ bị treo, và không có gì khác báo.
        log.exception("KHONG QUYET TOAN DUOC stream %s user=%s",
                      request_id[-8:], user_id[:8])
        return None
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def hoan(user_id: str, request_id: str) -> None:
    """Hoàn đủ phần đã giữ, trong phiên CSDL mới. Idempotent qua `credit.hoan`."""
    from platform_core.db import get_session
    from platform_core.llm import thanh_toan

    gen = get_session()
    db = next(gen)
    try:
        thanh_toan.hoan_luot(db, user_id=user_id, request_id=request_id)
        db.commit()
    except Exception:                                           # noqa: BLE001
        db.rollback()
        log.exception("khong hoan duoc phan giu cho cua %s", request_id[-8:])
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Bước 4: sự kiện canonical cho sản phẩm ───────────────────────────────────

class _DocSSE:
    """Đệm byte cho tới khi đủ một dòng `data:`; trả về JSON đã phân tích.

    `iter_raw()` trả byte theo nhịp mạng, không theo nhịp dòng — một
    `data: {...}` hoàn toàn có thể tới làm ba khối. Phân tích từng khối rời là
    hỏng ngẫu nhiên theo tải (cùng bài học của `dem_token_luong`).
    """

    __slots__ = ("_du",)

    def __init__(self) -> None:
        self._du = b""

    def nhin(self, khoi: bytes) -> Iterator[dict]:
        if not khoi:
            return
        self._du += khoi
        *dong, self._du = self._du.split(b"\n")
        for d in dong:
            d = d.strip()
            if not d.startswith(b"data:"):
                continue
            than = d[5:].strip()
            if not than or than == b"[DONE]":
                continue
            try:
                goi = json.loads(than)
            except (ValueError, TypeError):
                continue
            if isinstance(goi, dict):
                yield goi


def _su_kien_tu_goi(goi: dict, trang_thai: dict) -> Iterator[dict]:
    """Một chunk OpenAI chat → 0..n sự kiện canonical. Ghi `finish_reason` vào `trang_thai`."""
    for ch in goi.get("choices") or ():
        if not isinstance(ch, dict):
            continue
        delta = ch.get("delta") or {}
        if isinstance(delta, dict):
            suy_nghi = delta.get("reasoning_content")
            if isinstance(suy_nghi, str) and suy_nghi:
                yield {"type": "reasoning.delta", "text": suy_nghi}
            chu = delta.get("content")
            if isinstance(chu, str) and chu:
                yield {"type": "response.delta", "text": chu}
            goi_tool = delta.get("tool_calls")
            if isinstance(goi_tool, list) and goi_tool:
                yield {"type": "tool_call.delta", "tool_calls": goi_tool}
        ly_do = ch.get("finish_reason")
        if isinstance(ly_do, str) and ly_do:
            trang_thai["finish_reason"] = ly_do


def mo_luong(db, *, user_id: str, tool_name: str, params: dict,
             correlation_id: str = "", holder_id: str = "",
             timeout_s: float = MO_LUONG_GIAY,
             ghi_nhan: Optional[dict] = None,
             cua: str = "stream", tien_to: str = "st") -> Iterator[dict]:
    """Chạy một lượt text và sinh **sự kiện canonical** (§5.3 kế hoạch H43).

        response.started {request_id, model, credit_giu}
        reasoning.delta  {text}
        response.delta   {text}
        tool_call.delta  {tool_calls}
        usage.updated    {token_vao, token_ra, token_cache, do_duoc}
        response.completed {finish_reason}
        response.failed  {code, ly_do, retry_after_s?}
        billing.updated  {credit_giu, credit_thu, credit_hoan, do_duoc, phien_ban_gia}

    Lỗi **trước** khi giữ tiền (`ThamSoSai`) ném thẳng — chúng là lỗi của bên
    gọi và chưa có tác dụng phụ nào. Từ `response.started` trở đi, mọi kết cục
    là **sự kiện**, kể cả bận và không mở được, để sản phẩm luôn nhận được
    `billing.updated` cuối cùng và biết tiền đã đi đâu.

    ⭐ `response.started` phát **trước** khi mở luồng tới máy B — tức trước
       prefill. Với prompt dài prefill có thể mất hơn 100 giây, và byte đầu tiên
       tới sớm là thứ giữ kết nối qua Cloudflare không bị 524 (D7 kế hoạch).

    Bên tiêu thụ **đóng generator** (`.close()`) để dừng: phần đã sinh vẫn được
    quyết toán đúng trong `finally` của luồng bên dưới. Vì sau `GeneratorExit`
    không còn `yield` được, sự kiện `billing.updated` của lượt bị dừng được ghi
    vào `ghi_nhan` (nếu truyền) để bên tiêu thụ đọc.
    """
    than = dict(params or {})
    than["stream"] = True
    # llama-server chỉ đính `usage` vào chunk cuối khi được xin. Không xin thì
    # `DemToken` không thấy usage ⇒ hoàn đủ, thu 0 — đúng luật nhưng là cho không.
    than.setdefault("stream_options", {"include_usage": True})

    # `cua` / `tien_to` do NGUOI GOI dua xuong, khong viet cung o day.
    #
    # Ban truoc ghim thang "chatltt" / "cl" — mot ten APP nam trong
    # `platform_core`, dung thu `test_60::test_no_app_slug_is_hardcoded_in_the
    # _platform` cam. No lot vao cung voi cong stream cua Multi-Job (52a76dd1)
    # va song sot vi chua ai chay gate day du tren cay hop nhat.
    #
    # Khong phai chuyen hinh thuc: nhan `cua` di vao SO TUNG LUOT cua phong cho
    # (`llm_waiters.cua`), nen mot ten viet cung nghia la moi app goi ham nay ve
    # sau deu bi ghi nham la "chatltt" trong so — va bao cao nghen se tro sai
    # app. Mac dinh "stream" la mo ta DUNG cho mot nguoi goi chua tu khai.
    from platform_core.llm import phong_cho, tham_so_da_luot

    tk = tien_kiem(db, user_id=user_id, tool_name=tool_name, than=than,
                   duong=DUONG_NOI_BO, correlation_id=correlation_id,
                   tien_to=tien_to, cua=cua)
    ts = tham_so_da_luot.doc()
    bat_dau = time.monotonic()

    def _su_kien_cho(ly_do: str) -> dict:
        return {"type": "response.queued", "ly_do": ly_do}

    if tk.dung_phong_cho:
        # multijob D-06: chờ trong phòng chờ, phát `response.queued` theo nhịp
        # (bên tiêu thụ bỏ qua loại lạ; `_p_luot.py` chuyển xuống trình duyệt và
        # nó đồng thời giữ kết nối qua Cloudflare). Hết trần ⇒ `DangBan` — đúng
        # đường ChatLTT đã xử lý bận (`services/luot.py`). Chưa giữ tiền lúc chờ.
        # Chốt giao dịch của bên gọi trước khi các phiên MỚI ghi dòng chờ — đường
        # cũ `chuan_bi` cũng commit phiên này (sau khi giữ tiền).
        db.commit()
        cho = vao_va_cho(tk, db_luong=db, han_s=ts.han_cho_stream(tk.la_whale))
        try:
            cb = yield from _chen_nhip(cho, ts.nhip_tim_cho_s, _su_kien_cho)
        except phong_cho.HetCho as e:
            raise DangBan(f"het tran cho ({e.ly_do})", nguon="het_cho",
                          tai_nguyen=tk.tai_nguyen, thu_lai_sau_s=15) from None
        finally:
            cho.close()
    else:
        cb = chuan_bi(db, user_id=user_id, tool_name=tool_name, than=than,
                      duong=DUONG_NOI_BO, holder_id=holder_id,
                      correlation_id=correlation_id, tien_to="cl")
    yield {"type": "response.started", "request_id": cb.request_id,
           "model": cb.model_alias, "credit_giu": cb.da_giu}

    # Máy B 429 cho lượt đã nhận ⇒ xếp lại trong hạn chờ (chỉ khi có dòng chờ —
    # đường cũ `chuan_bi` không có ⇒ `mo_co_xep_lai` hoàn + ném ngay như trước).
    mo = mo_co_xep_lai(tk, cb, han_s=ts.han_cho_stream(tk.la_whale),
                       bat_dau=bat_dau, timeout_s=timeout_s)
    try:
        luot = yield from _chen_nhip(mo, ts.nhip_tim_cho_s, _su_kien_cho)
    except phong_cho.HetCho as e:
        yield {"type": "response.failed", "code": "ban",
               "ly_do": f"het tran cho ({e.ly_do})", "retry_after_s": 15}
        yield _billing(cb, None)
        return
    except phong_cho.KhachDi:
        yield _billing(cb, None)
        return
    except DangBan as e:
        yield {"type": "response.failed", "code": "ban", "ly_do": e.ly_do,
               "retry_after_s": e.thu_lai_sau_s}
        yield _billing(cb, None)
        return
    except KhongMoDuoc as e:
        yield {"type": "response.failed",
               "code": "qua_dai" if e.qua_dai else "khong_mo_duoc",
               "ly_do": e.ly_do}
        yield _billing(cb, None)
        return
    finally:
        mo.close()

    doc = _DocSSE()
    trang_thai: dict = {}
    vo: Optional[BaseException] = None
    try:
        for khoi in luot.luong:
            for goi in doc.nhin(khoi):
                yield from _su_kien_tu_goi(goi, trang_thai)
    except GeneratorExit:
        # Bên tiêu thụ dừng. Đóng luồng bên dưới để `finally` của nó quyết toán.
        luot.luong.close()
        if ghi_nhan is not None:
            ghi_nhan["billing"] = _billing(cb, luot.ket_qua)
            ghi_nhan["usage"] = {"token_vao": luot.dem.token_vao, "token_ra": luot.dem.token_ra,
                                 "token_cache": luot.dem.token_cache, "do_duoc": luot.dem.do_duoc}
        raise
    except Exception as e:                                      # noqa: BLE001
        vo = e
    finally:
        # Idempotent: generator đã cạn thì `close()` không làm gì.
        luot.luong.close()

    su = luot.dem
    yield {"type": "usage.updated", "token_vao": su.token_vao,
           "token_ra": su.token_ra, "token_cache": su.token_cache,
           "do_duoc": su.do_duoc}
    if vo is not None:
        yield {"type": "response.failed", "code": "luong_vo",
               "ly_do": type(vo).__name__}
    else:
        yield {"type": "response.completed",
               "finish_reason": trang_thai.get("finish_reason", "")}
    yield _billing(cb, luot.ket_qua)


def _billing(cb: ChuanBi, thu) -> dict:
    if thu is None:
        # Chưa chạy hoặc đã hoàn đủ: tiền về đúng chỗ, thu 0.
        return {"type": "billing.updated", "credit_giu": cb.da_giu,
                "credit_thu": 0, "credit_hoan": cb.da_giu, "do_duoc": False,
                "phien_ban_gia": ""}
    return {"type": "billing.updated", "credit_giu": int(thu.da_giu_credit),
            "credit_thu": int(thu.thu_credit), "credit_hoan": int(thu.hoan_credit),
            "do_duoc": bool(getattr(thu, "da_do_duoc", True)),
            "phien_ban_gia": str(getattr(thu, "phien_ban_gia", ""))}
