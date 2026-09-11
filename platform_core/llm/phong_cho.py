"""phong_cho.py — phòng chờ của cửa TƯƠNG TÁC tới model nhà, và sổ từng lượt. (multijob)

⭐ MỘT hàng, liên tiến trình: dòng nằm trong CSDL (`llm_waiters`) nên mọi web worker
   cùng thấy cùng một thứ tự. Không phải hàng thứ hai của `jobs` (việc nền không có
   dòng ở đây), không phải hàng ẩn trong một tiến trình, không phải hàng ở gateway.

⭐ Bảng cũng là SỔ TỪNG LƯỢT, giữ 30 ngày để phân tích sau khi mở vận hành (chủ dự
   án yêu cầu 11/09): lúc vào, lúc được nhận, lúc xong, lý do chờ cuối, số nhịp.

Spec: `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md` §4.2, §5, §9.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Generator

from sqlalchemy import delete
from sqlalchemy.orm import Session

from platform_core.models import LlmWaiter

log = logging.getLogger("platform_core.llm.phong_cho")

#: Khoảng giữa hai lần hỏi lại luật nhận khi đang chờ. Mỗi lần hỏi cũng là một
#: nhịp tim của dòng chờ.
MOI_NHIP_S = 0.5


class PhongDay(Exception):
    """Phòng chờ đầy — trả 429 TRƯỚC khi mở luồng (spec §9). Chưa ghi gì."""

    def __init__(self, ly_do: str):
        super().__init__(ly_do)
        self.ly_do = ly_do


class HetCho(Exception):
    """Chờ quá trần mà chưa được nhận. `ly_do` là mã lý do của nhịp chờ cuối."""

    def __init__(self, ly_do: str):
        super().__init__(ly_do)
        self.ly_do = ly_do


class KhachDi(Exception):
    """Dòng chờ không còn ở trạng thái `cho` (vòng dọn đã chốt nó, hoặc bị rời)."""


@dataclass(frozen=True)
class YeuCauCho:
    """Mọi thứ luật nhận cần biết về một lượt đang chờ."""

    resource: str
    slots: int
    token_pool: int
    user_id: str
    mode: str
    holder_id: str
    request_id: str
    cua: str
    lop: str
    token_dat_truoc: int
    token_prefill_moi: int = 0
    la_whale: bool = False


def _dong_ho_that() -> datetime:
    return datetime.now(timezone.utc)

#: Một người chờ phải đập nhịp (mỗi lần hỏi lại) trong khoảng này; quá thì coi như
#: tiến trình đang giữ nó đã chết và dòng không còn tranh chỗ.
HAN_NHIP_CHO_S = 10.0

#: Dòng `cho` im lặng quá lâu (tiến trình web chết giữa lúc chờ) bị vòng dọn chốt
#: thành `het_han` — để sổ lượt không nói "đang chờ" mãi mãi.
HAN_CHO_MO_COI = timedelta(minutes=10)

#: Sổ lượt ở lại 30 ngày (`governance.py`: OPERATIONAL, 30).
GIU_SO_LUOT = timedelta(days=30)


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


def chup_nguoi_cho(db: Session, *, resource: str,
                   now: datetime | None = None) -> list:
    """Người đang chờ CÒN SỐNG của một tài nguyên, dưới dạng `luat_nhan.Luot`.

    Dòng mất nhịp quá `HAN_NHIP_CHO_S` không còn tranh chỗ: tiến trình giữ nó đã
    chết hoặc treo, và để nó chặn FCFS là để một xác chết giữ hàng.
    """
    from platform_core.llm import luat_nhan

    now = now or _bay_gio()
    ra = []
    for w in (db.query(LlmWaiter)
              .filter(LlmWaiter.resource == resource, LlmWaiter.trang_thai == "cho")
              .all()):
        if (now - _aware(w.heartbeat_at)).total_seconds() > HAN_NHIP_CHO_S:
            continue
        ra.append(luat_nhan.Luot(
            id=w.id, user_id=w.user_id, lop=w.lop or luat_nhan.TUONG_TAC,
            token_dat_truoc=int(w.token_dat_truoc or 0), la_whale=bool(w.la_whale),
            tuoi_s=max(0.0, (now - _aware(w.created_at)).total_seconds())))
    return ra


def kiem_phong(db: Session, *, resource: str, token_prefill_moi: int,
               so_nguoi_toi_da: int, token_prefill_toi_da: int,
               now: datetime | None = None) -> None:
    """Ném `PhongDay` nếu phòng chờ đã chạm trần. Chạy TRƯỚC khi gửi 200.

    Hai trần độc lập (nguyên tắc vLLM `max_num_queued_reqs`/`_tokens`):
      * số người chờ — không có hàng vô hạn;
      * tổng token cần prefill MỚI đang chờ — hàng 30 người nhẹ khác hàng 3 whale.
    Phòng TRỐNG thì luôn nhận: nếu không, một whale lớn hơn trần token sẽ không
    bao giờ vào được hàng.
    """
    now = now or _bay_gio()
    song = [w for w in (db.query(LlmWaiter)
                        .filter(LlmWaiter.resource == resource,
                                LlmWaiter.trang_thai == "cho").all())
            if (now - _aware(w.heartbeat_at)).total_seconds() <= HAN_NHIP_CHO_S]
    if len(song) >= so_nguoi_toi_da:
        raise PhongDay("phong_day_so_nguoi")
    if song and sum(int(w.token_prefill_moi or 0) for w in song) + int(
            token_prefill_moi) > token_prefill_toi_da:
        raise PhongDay("phong_day_token_prefill")


def vao(db: Session, yc: YeuCauCho, *, now: datetime | None = None) -> str:
    """Ghi dòng chờ; caller commit. Trả `waiter_id`."""
    now = now or _bay_gio()
    w = LlmWaiter(resource=yc.resource, cua=yc.cua, lop=yc.lop, user_id=yc.user_id,
                  request_id=yc.request_id, token_dat_truoc=int(yc.token_dat_truoc),
                  token_prefill_moi=int(yc.token_prefill_moi),
                  la_whale=bool(yc.la_whale), created_at=now, heartbeat_at=now,
                  trang_thai="cho")
    db.add(w)
    db.flush()
    return w.id


def _phien():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def _dong(gen) -> None:
    try:
        next(gen)
    except StopIteration:
        pass


def _mot_nhip(yc: YeuCauCho, waiter_id: str, dong_ho: Callable[[], datetime],
              cho_whale_toi_da_s: float) -> tuple[str, str]:
    """Đập nhịp + hỏi luật nhận một lần, trong một transaction. Trả `(lease_id, lý do)`."""
    from platform_core.llm import admission

    gen, db = _phien()
    try:
        w = db.get(LlmWaiter, waiter_id)
        if w is None or w.trang_thai != "cho":
            raise KhachDi(waiter_id)
        now = dong_ho()
        # Đập nhịp TRƯỚC khi xét: chính dòng này phải có mặt trong ảnh chụp.
        w.heartbeat_at = now
        w.so_nhip = int(w.so_nhip or 0) + 1
        db.flush()
        lease, ly_do = admission.xet_va_giu(
            db, resource=yc.resource, slots=yc.slots, user_id=yc.user_id,
            mode=yc.mode, holder_id=yc.holder_id, lop=yc.lop,
            token_dat_truoc=yc.token_dat_truoc, token_prefill_moi=yc.token_prefill_moi,
            la_whale=yc.la_whale, token_pool=yc.token_pool, waiter_id=waiter_id,
            tuoi_cho_s=max(0.0, (now - _aware(w.created_at)).total_seconds()),
            cho_whale_toi_da_s=cho_whale_toi_da_s, now=now)
        if lease is not None:
            w.trang_thai = "nhan"
            w.lease_id = lease.id
            w.admitted_at = now
            db.commit()
            return lease.id, ""
        w.ly_do_cho = ly_do
        db.commit()
        return "", ly_do
    except BaseException:
        db.rollback()
        raise
    finally:
        _dong(gen)


def _chot(waiter_id: str, trang_thai: str, ket_qua: str,
          now: datetime | None = None, *, chi_khi: str = "cho") -> None:
    """Chốt trạng thái cuối của một dòng (phiên mới). Hỏng thì chỉ ghi log."""
    gen, db = _phien()
    try:
        w = db.get(LlmWaiter, waiter_id)
        if w is not None and (not chi_khi or w.trang_thai == chi_khi):
            w.trang_thai = trang_thai
            w.ket_qua = ket_qua
            w.finished_at = now or _bay_gio()
            db.commit()
    except Exception:  # noqa: BLE001 - sổ lượt không được làm hỏng lượt thật
        db.rollback()
        log.exception("khong chot duoc dong cho %s -> %s", waiter_id, trang_thai)
    finally:
        _dong(gen)


def cho_nhan(yc: YeuCauCho, *, waiter_id: str, han_s: float,
             cho_whale_toi_da_s: float = 30.0, moi_nhip_s: float = MOI_NHIP_S,
             dong_ho: Callable[[], datetime] = _dong_ho_that,
             ngu: Callable[[float], None] = time.sleep,
             ) -> Generator[str, None, str]:
    """GENERATOR: mỗi nhịp chưa được nhận thì `yield` mã lý do; được nhận thì `return lease_id`.

    ⭐ Kiểu là `Generator[str, None, str]` chứ **không** phải `Iterator[str]`:
       `Iterator` chỉ mô tả thứ **yield** ra, không mô tả thứ **return** về. Mà
       cả giá trị của hàm này nằm ở chỗ `return lease_id` — bên gọi lấy nó bằng
       `lease_id = yield from cho_nhan(...)`. Khai `Iterator` thì mypy đọc
       `return lease_id` là *"No return value expected"* và đọc lời gọi là
       *"Function does not return a value"*: hai lỗi, một gốc.

    Dùng `lease_id = yield from cho_nhan(...)` trong một generator khác (cửa stream
    chèn nhịp tim SSE giữa các nhịp), hoặc `cho_nhan_chan(...)` khi chờ chặn.

    ⛔ Đóng generator giữa chừng (khách ngắt ⇒ `GeneratorExit` ở `yield`) ⇒ dòng
       thành `roi` trong `finally`. CHƯA giữ tiền ở đây — không có gì phải hoàn.
    ⛔ Quá `han_s` ⇒ `het_han` rồi ném `HetCho`.
    """
    bat_dau = dong_ho()
    xong = False
    try:
        while True:
            lease_id, ly_do = _mot_nhip(yc, waiter_id, dong_ho, cho_whale_toi_da_s)
            if lease_id:
                xong = True
                return lease_id
            if (dong_ho() - bat_dau).total_seconds() >= han_s:
                _chot(waiter_id, "het_han", "het_cho", dong_ho())
                xong = True
                raise HetCho(ly_do)
            yield ly_do
            ngu(moi_nhip_s)
    except KhachDi:
        xong = True
        raise
    finally:
        if not xong:
            _chot(waiter_id, "roi", "khach_di", dong_ho())


def cho_nhan_chan(yc: YeuCauCho, *, waiter_id: str, han_s: float,
                  ngat_chua: Callable[[], bool] | None = None, **kw) -> str:
    """Chờ CHẶN tới khi được nhận (cửa đồng bộ). Ném `HetCho` khi quá `han_s`.

    `ngat_chua` được hỏi sau mỗi nhịp: khách đi trong lúc chờ ⇒ đóng generator
    (dòng thành `roi`) rồi ném `KhachDi`. Chưa giữ tiền ở đây nên **không có gì
    phải hoàn** — đó chính là lý do điểm giữ tiền nằm sau chỗ này (INV-MJ-1).
    """
    g = cho_nhan(yc, waiter_id=waiter_id, han_s=han_s, **kw)
    while True:
        try:
            next(g)
        except StopIteration as e:
            return e.value
        if ngat_chua is not None and ngat_chua():
            g.close()
            raise KhachDi(waiter_id)


def ghi_ket_thuc(waiter_id: str, ket_qua: str, *, now: datetime | None = None) -> None:
    """Lượt đã được nhận rồi kết thúc: `xong` + kết cục (`xong`/`khach_ngat`/`loi`…)."""
    if waiter_id:
        _chot(waiter_id, "xong", ket_qua, now, chi_khi="nhan")


def don_het_han(db: Session, *, now: datetime | None = None) -> int:
    """Vòng dọn của worker (`job_runner._don_du_lieu_het_han`). Trả số dòng đã đụng.

    Hai việc, cả hai idempotent:
      1. dòng `cho` mất nhịp quá `HAN_CHO_MO_COI` ⇒ `het_han` (tiến trình chết lúc chờ);
      2. xoá dòng tạo trước `GIU_SO_LUOT` (30 ngày).
    """
    now = now or _bay_gio()
    mo_coi = 0
    for w in db.query(LlmWaiter).filter(LlmWaiter.trang_thai == "cho").all():
        if now - _aware(w.heartbeat_at) > HAN_CHO_MO_COI:
            w.trang_thai = "het_han"
            w.ket_qua = w.ket_qua or "mat_nhip"
            w.finished_at = now
            mo_coi += 1
    if mo_coi:
        db.flush()
    # `synchronize_session=False`: SQLite trả giờ KHÔNG múi, `now` có múi — để
    # SQLAlchemy tự đối chiếu phiên trong Python là so hai kiểu giờ, và nó ném.
    xoa = db.execute(
        delete(LlmWaiter).where(LlmWaiter.created_at < now - GIU_SO_LUOT)
        .execution_options(synchronize_session=False)
    ).rowcount or 0
    return mo_coi + int(xoa)
