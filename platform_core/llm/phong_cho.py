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
    #: Id model **nội bộ** của máy B. Vào cột `llm_waiters.model` (dual-model 6.3)
    #: để `job_metrics` đọc độ sâu phòng chờ **theo model** mà không phải dịch
    #: `resource` → model bằng một bảng ánh xạ nhập từ `apps/`.
    #: Rỗng = cửa gọi chưa khai; sổ ghi ô `khong_khai`, không gộp vào model nào.
    model: str = ""


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


def kiem_phong(db: Session, *, resource: str, so_nguoi_toi_da: int,
               la_whale: bool, so_ca_voi_toi_da: int,
               now: datetime | None = None) -> None:
    """Ném `PhongDay` nếu phòng chờ đã chạm trần. Chạy TRƯỚC khi gửi 200.

    Phòng chờ CHỈ trả lời *"hàng có vô hạn không"* — bằng SỐ NGƯỜI:
      * số người chờ còn sống — không có hàng vô hạn;
      * số WHALE chờ còn sống — whale chạy nối tiếp (≤1 mỗi tài nguyên), nên hàng
        whale dài bao nhiêu là chờ bấy nhiêu lượt 150K; chặn nó để 429 đến TRƯỚC
        200 thay vì hết trần chờ giữa SSE.

    🔴 L-12b (17/09/2026): phòng chờ KHÔNG còn trần TOKEN. Câu *"có vừa không"*
       có đúng MỘT người trả lời — `luat_nhan.xet` luật 2: Σ token đặt chỗ của
       lượt ĐANG CHẠY + lượt này ≤ pool KV của model (`-kvu`: một bể `-c` chung
       cho mọi slot). Lượt chưa vừa thì CHỜ trong hàng, có nhịp tim, có backfill
       có chặn; không bị đuổi.

       Trần cũ (`token_prefill_cho_toi_da` 57.000 trên Σ token MỚI của người
       CHỜ) là luật thứ hai cho cùng câu hỏi, và đo được nó đuổi oan:
         * 13/09 J10: lượt 67.989 token → 429 khi có người chờ, 200 khi phòng
           trống (bản vá 13/09 chỉ nới cho MỘT món lớn);
         * sau bản vá: một whale 68K đang chờ ⇒ MỌI lượt mới, kể cả 10 token, 429
           (`68K + x > 57K`) — `test_1250::test_mot_whale_dang_cho_khong_duoi_luot_nho`.
    """
    now = now or _bay_gio()
    song = [w for w in (db.query(LlmWaiter)
                        .filter(LlmWaiter.resource == resource,
                                LlmWaiter.trang_thai == "cho").all())
            if (now - _aware(w.heartbeat_at)).total_seconds() <= HAN_NHIP_CHO_S]
    if len(song) >= so_nguoi_toi_da:
        raise PhongDay("phong_day_so_nguoi")
    if la_whale and sum(1 for w in song if bool(getattr(w, "la_whale", False))) >= max(
            1, int(so_ca_voi_toi_da)):
        raise PhongDay("phong_day_ca_voi")


def vao(db: Session, yc: YeuCauCho, *, now: datetime | None = None) -> str:
    """Ghi dòng chờ; caller commit. Trả `waiter_id`."""
    now = now or _bay_gio()
    w = LlmWaiter(resource=yc.resource, model=str(yc.model or "")[:64],
                  cua=yc.cua, lop=yc.lop, user_id=yc.user_id,
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


def cong_cho_residency(w, giay: float) -> bool:
    """Cộng `giay` vào `llm_waiters.cho_residency_s` của một dòng chờ.

    ⭐ VÌ SAO TÁCH KHỎI TỔNG THỜI GIAN CHỜ. `finished_at - created_at` trả lời
       *"khách đợi bao lâu"*; câu người vận hành phải trả lời ngay sau đó là
       *"đợi vì ta thiếu slot, hay vì 3090 lúc ấy đang vẽ ảnh"* — và hai câu ấy
       dẫn tới hai việc sửa khác nhau (mở thêm slot vs. siết cửa sổ ảnh). Một
       tổng gộp không tách ra được, nên nó sẽ đẩy người đọc đi sửa số slot cho
       một chuyện không liên quan gì tới slot.

    ⛔ KHÔNG suy được từ `ly_do_cho`: cột ấy giữ lý do của nhịp **cuối**, tức
       "lúc bỏ cuộc thì đang vướng gì", không phải "đã vướng gì bao lâu".

    Cột do migration `d91f6c37ab24` thêm (5.3 — bên GHI đi trước bên đọc; Task
    6.3 công bố nó ở `/ops/jobs-metrics`). Trả `False` khi không cộng gì.
    """
    if giay <= 0:
        return False
    w.cho_residency_s = float(getattr(w, "cho_residency_s", 0.0) or 0.0) + float(giay)
    return True


def _mot_nhip(yc: YeuCauCho, waiter_id: str,
              dong_ho: Callable[[], datetime]) -> tuple[str, str]:
    """Đập nhịp + hỏi luật nhận một lần, trong một transaction. Trả `(lease_id, lý do)`."""
    from platform_core.llm import admission, luat_nhan

    gen, db = _phien()
    try:
        w = db.get(LlmWaiter, waiter_id)
        if w is None or w.trang_thai != "cho":
            raise KhachDi(waiter_id)
        now = dong_ho()
        # ⭐ Khoảng [nhịp trước → giờ] được quy về lý do ĐANG GHI ở dòng, không
        #    về lý do sắp tính ra: đó là lý do thật sự đã có hiệu lực trong lúc
        #    người này ngủ. Quy theo lý do MỚI sẽ dán nhãn một khoảng chờ vì
        #    thiếu slot thành chờ vì cư trú chỉ vì cư trú vừa đóng ở cuối khoảng.
        if (w.ly_do_cho or "") == luat_nhan.CHO_RESIDENCY:
            cong_cho_residency(w, (now - _aware(w.heartbeat_at)).total_seconds())
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
            now=now)
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
             moi_nhip_s: float = MOI_NHIP_S,
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
            lease_id, ly_do = _mot_nhip(yc, waiter_id, dong_ho)
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


#: Mã lý do ghi vào `llm_waiters.ly_do_cho` khi một lượt ĐÃ nhận bị máy B trả 429
#: và quay lại hàng (phương án C bước 1, O-04). Nhịp chờ kế tiếp ghi đè bằng lý
#: do của `luat_nhan`; dấu vết bền là dòng log `XEP LAI` + bộ đếm `llm:xep_lai`.
LY_DO_MAY_B_TU_CHOI = "may_b_tu_choi"


def xep_lai(waiter_id: str, *, now: datetime | None = None) -> bool:
    """Dòng `nhan` quay lại `cho` — GIỮ `created_at` (tuổi chờ không đặt lại).

    ⭐ Vì sao giữ tuổi: lượt này đã chờ đúng lượt; máy B từ chối nó vì hai sổ
       nhả lệch nhịp (O-04), không phải vì nó đến muộn. Đặt lại tuổi là đẩy nó
       xuống cuối hàng cho một lỗi không phải của nó.
    ⛔ Chỉ đụng dòng đang `nhan`. Trả `False` khi không đổi gì (dòng đã chốt,
       không tồn tại) — bên gọi coi như không xếp lại được.
    """
    if not waiter_id:
        return False
    gen, db = _phien()
    try:
        w = db.get(LlmWaiter, waiter_id)
        if w is None or w.trang_thai != "nhan":
            return False
        bay_gio = now or _bay_gio()
        w.trang_thai = "cho"
        w.lease_id = ""
        w.admitted_at = None
        w.ly_do_cho = LY_DO_MAY_B_TU_CHOI
        w.heartbeat_at = bay_gio
        db.commit()
        return True
    except Exception:  # noqa: BLE001 - so luot khong duoc lam hong luot that
        db.rollback()
        log.exception("khong xep lai duoc dong cho %s", waiter_id)
        return False
    finally:
        _dong(gen)


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
