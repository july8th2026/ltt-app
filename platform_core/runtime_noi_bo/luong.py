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
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional

from platform_core.llm.dem_token_luong import DemToken
from platform_core.public_api.executor import for_tool
from platform_core.runtime_noi_bo.tim import KhongCoNangLuc, tim_tool  # noqa: F401

log = logging.getLogger("platform_core.runtime_noi_bo.luong")

#: Ngân sách mở luồng — 75 giây, **dưới** trần 125 giây của Cloudflare, để khi
#: máy B chậm thì **ta** trả lỗi đọc được chứ không để Cloudflare trả 524.
#: Đủ rộng cho ca xấu đã đo: `llama-swap` nạp lại model ~25 giây. Nới số này
#: không mua thêm thời gian — nó chỉ đổi 503 của ta lấy 524 của Cloudflare.
MO_LUONG_GIAY = 75.0

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

    def __init__(self, ly_do: str, *, nguon: str = "suat", tai_nguyen: str = "",
                 thu_lai_sau_s: int = 15):
        super().__init__(ly_do)
        self.ly_do = ly_do
        self.nguon = nguon
        self.tai_nguyen = tai_nguyen
        self.thu_lai_sau_s = int(thu_lai_sau_s)


class ThieuCredit(LoiCuaLuong):
    """Không đủ số dư để giữ trần ước. Chốt TRƯỚC khi đốt GPU."""


class KhongMoDuoc(LoiCuaLuong):
    """Không mở được luồng vì lý do khác bận. `qua_dai` = 413 (lỗi của đầu vào)."""

    def __init__(self, ly_do: str, *, qua_dai: bool = False):
        super().__init__(ly_do)
        self.ly_do = ly_do
        self.qua_dai = qua_dai


# ── Ước lượng đầu vào / trần đầu ra (hạ từ `server/api/streaming.py`) ────────

def uoc_tin_nhan(than: dict) -> list:
    """Rút phần văn bản đầu vào, dù client nói giao thức nào.

    Chỉ dùng để **ước** token đầu vào cho phần giữ chỗ, nên không cần chính xác
    tuyệt đối — nhưng phải ước **CAO**, vì giữ thiếu thì khách tiêu quá số dư.
    Vì thế nó cố ý sinh ra phần tử **không có `role`** (prompt hệ thống, khối
    `tools`) — KHÔNG được đem danh sách này đi gọi model.
    """
    ra: list = []
    he_thong = than.get("system")
    if isinstance(he_thong, str):
        ra.append({"content": he_thong})
    elif isinstance(he_thong, list):
        ra.extend({"content": (m or {}).get("text", "")} for m in he_thong
                  if isinstance(m, dict))

    tin = than.get("messages")
    if isinstance(tin, list):
        ra.extend(m for m in tin if isinstance(m, dict))

    # Responses gọi nó là `input`, và nó có thể là chuỗi trần.
    vao = than.get("input")
    if isinstance(vao, str):
        ra.append({"content": vao})
    elif isinstance(vao, list):
        ra.extend(m for m in vao if isinstance(m, dict))

    # Định nghĩa tool đi kèm mỗi lượt và **không hề nhỏ**: đo thật 23/08, prompt
    # hệ thống của Codex là ~21.936 token. Bỏ qua nó là ước thiếu rất nhiều.
    cong_cu = than.get("tools")
    if isinstance(cong_cu, list) and cong_cu:
        ra.append({"content": json.dumps(cong_cu, ensure_ascii=False)})
    return ra


def tran_token_ra(than: dict, token_vao_uoc: int, executor) -> int:
    """Trần token ra cho lượt này, đã kẹp theo **chỗ còn lại trong ngữ cảnh**.

    Khách khai `max_tokens`/`max_output_tokens` thì kẹp số đó; không khai thì
    lấy mặc định của **cửa stream** (`executor.mac_dinh_cho("stream")`) — KHÔNG
    phải của cửa đồng bộ. Lấy nhầm 1.024 của cửa đồng bộ là gốc của lỗi "hỏi
    dài thì im lặng" đo được 30/08.
    """
    tran = int(executor.context_output_cap(token_vao_uoc))
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
    correlation_id: str = ""


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
    gui["model"] = executor.model_id(ten)

    # ⛔ KHÔNG tự ghép chuỗi: `credit_entries.job_id` là VARCHAR(36).
    request_id = thanh_toan.ma_luot(tien_to)

    lease_id = ""
    tai_nguyen = str(getattr(tool, "admission_resource", "") or "")
    so_suat = int(getattr(tool, "admission_slots", 0) or 0)
    if tai_nguyen and so_suat > 0:
        ticket = admission.acquire(
            db, resource=tai_nguyen, slots=so_suat, user_id=user_id,
            mode="stream", holder_id=holder_id or request_id)
        if ticket is None:
            db.rollback()
            raise DangBan("het suat thuc thi", nguon="suat", tai_nguyen=tai_nguyen,
                          thu_lai_sau_s=15)
        lease_id = ticket.id

    vao_uoc = int(executor.estimate_input(tin))
    xin_ra = tran_token_ra(than, vao_uoc, executor)

    # 🔴 GHI GIÁ TRỊ ĐÃ KẸP TRỞ LẠI THÂN GỬI LÊN, đúng TÊN TRƯỜNG của cửa.
    #    Kẹp cái mình thu tiền mà không kẹp cái mình gửi đi ⇒ máy B trả 413
    #    (H38/L2). Không khai gì thì tên theo cửa: `/responses` chỉ đọc
    #    `max_output_tokens` — ghi nhầm tên là llama-server dùng mặc định 1.024.
    ten_tran = "max_output_tokens" if duong.endswith("/responses") else "max_tokens"
    for _ten in ("max_tokens", "max_output_tokens"):
        if _ten in gui:
            gui[_ten] = xin_ra
            break
    else:
        gui[ten_tran] = xin_ra

    try:
        da_giu = thanh_toan.giu_cho_luot(
            db, user_id=user_id, request_id=request_id,
            token_vao_uoc=vao_uoc, max_tokens=xin_ra)
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
        raise ThieuCredit(str(e)) from None

    # 🔴 CHỐT GIAO DỊCH TRƯỚC KHI CHẠM MODEL (xem docstring module).
    db.commit()
    return ChuanBi(db=db, user_id=user_id, tool_name=tool_name, duong=duong,
                   than_gui=gui, request_id=request_id, lease_id=lease_id,
                   da_giu=da_giu, token_vao_uoc=vao_uoc, xin_ra=xin_ra,
                   model_alias=ten, executor=executor,
                   correlation_id=correlation_id)


# ── Bước 2: mở luồng tới máy B ───────────────────────────────────────────────

@dataclass
class LuotLuong:
    """Một luồng đang chảy. `luong` chuyển byte nguyên xi và **tự quyết toán**."""

    chuan_bi: ChuanBi
    content_type: str
    luong: Iterator[bytes] = field(default=iter(()))
    dem: DemToken = field(default_factory=DemToken)
    #: Điền sau khi quyết toán (trong `finally` của `luong`).
    ket_qua: Any = None
    #: "xong" | "khach_ngat" | "loi" — điền khi luồng kết thúc.
    ket_thuc: str = ""


def _nha_suat(lease_id: str) -> None:
    if not lease_id:
        return
    from platform_core.llm import admission
    admission.release_by_id(lease_id)


def mo_thuong_nguon(cb: ChuanBi, *, timeout_s: float = MO_LUONG_GIAY,
                    trang_thai=None) -> LuotLuong:
    """Mở luồng tới máy B. Hỏng thì **hoàn đủ + nhả suất** rồi ném.

    Ném `DangBan(nguon="thuong_nguon")` khi máy B trả 429, `KhongMoDuoc` khi
    khác. Cả hai đều đã hoàn tiền trước khi ném — bên gọi không phải hoàn lại.
    """
    from platform_core.llm import luong_vlm
    from platform_core.public_api import metrics

    try:
        mo = luong_vlm.mo(cb.db, duong=cb.duong, than=cb.than_gui,
                          timeout_s=timeout_s)
    except luong_vlm.KhongMoDuocLuong as e:
        hoan(cb.user_id, cb.request_id)
        _nha_suat(cb.lease_id)
        if e.ban:
            # ⛔ BẬN ≠ HỎNG. Khách KHÔNG bị thu tiền. Đếm vào `CAPACITY_REFUSED`
            #    để người trực thấy tần suất, không chỉ thấy một dòng log.
            metrics.increment(metrics.CAPACITY_REFUSED)
            log.warning("BAN luong: user=%s duong=%s ly_do=%s",
                        cb.user_id[:8], cb.duong, e.ly_do)
            raise DangBan(e.ly_do, nguon="thuong_nguon",
                          thu_lai_sau_s=e.thu_lai_sau_s) from None
        log.warning("khong mo duoc luong cho user=%s: %s", cb.user_id[:8], e.ly_do)
        raise KhongMoDuoc(e.ly_do, qua_dai=bool(getattr(e, "qua_dai", False))) from None
    except BaseException:
        hoan(cb.user_id, cb.request_id)
        _nha_suat(cb.lease_id)
        raise

    metrics.increment("chat:stream")
    luot = LuotLuong(chuan_bi=cb, content_type=mo.content_type)
    luot.luong = _phat(mo, luot, trang_thai=trang_thai)
    return luot


def mo_luong_tho(db, *, user_id: str, tool_name: str, than: dict, duong: str,
                 holder_id: str = "", correlation_id: str = "",
                 timeout_s: float = MO_LUONG_GIAY, trang_thai=None) -> LuotLuong:
    """`chuan_bi` + `mo_thuong_nguon` — cho cửa cần **byte nguyên xi** (`/api/v1`)."""
    cb = chuan_bi(db, user_id=user_id, tool_name=tool_name, than=than,
                  duong=duong, holder_id=holder_id, correlation_id=correlation_id)
    return mo_thuong_nguon(cb, timeout_s=timeout_s, trang_thai=trang_thai)


# ── Bước 3: chuyển byte, đếm, quyết toán ─────────────────────────────────────

def _phat(mo, luot: LuotLuong, *, trang_thai=None) -> Iterator[bytes]:
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
    keeper = admission.keep_alive(cb.lease_id) if cb.lease_id else nullcontext()
    with keeper:
        try:
            for khoi in mo.luong:
                if t_byte_dau is None:
                    t_byte_dau = time.monotonic() - t0
                n_khoi += 1
                dem.nhin(khoi)
                yield khoi
        except GeneratorExit:
            khach_ngat = True
            raise
        except BaseException as e:                              # noqa: BLE001
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
            luot.ket_qua = quyet_toan(cb.user_id, cb.request_id, dem, cb.da_giu,
                                      trang_thai)
            if vo is not None:
                mo.hong(vo)
            else:
                mo.xong(tokens=dem.token_ra)


def quyet_toan(user_id: str, request_id: str, dem: DemToken, da_giu: int,
               trang_thai=None):
    """Chốt tiền, trong một phiên CSDL **mới**. Trả `KetQuaThu` hoặc `None`.

    ⚠️ Phiên của request đã đóng từ lúc phản hồi bắt đầu — generator này chạy sau
       đó. Dùng lại phiên cũ là `DetachedInstanceError` hoặc tệ hơn: một giao
       dịch không bao giờ được commit.
    """
    from platform_core.db import get_session
    from platform_core.llm import thanh_toan

    gen = get_session()
    db = next(gen)
    try:
        thu = thanh_toan.quyet_toan_hoac_hoan(
            db, user_id=user_id, request_id=request_id, su_dung=dem.su_dung())
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
             ghi_nhan: Optional[dict] = None) -> Iterator[dict]:
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

    cb = chuan_bi(db, user_id=user_id, tool_name=tool_name, than=than,
                  duong=DUONG_NOI_BO, holder_id=holder_id,
                  correlation_id=correlation_id, tien_to="cl")
    yield {"type": "response.started", "request_id": cb.request_id,
           "model": cb.model_alias, "credit_giu": cb.da_giu}

    try:
        luot = mo_thuong_nguon(cb, timeout_s=timeout_s)
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
