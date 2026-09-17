"""Admission lease chung cho mọi đường gọi tài nguyên LLM.

Lease chỉ trả lời "ai được chạy bây giờ"; durable queue vẫn chỉ là ``jobs``.
Caller giữ quyền commit/rollback để có thể gắn acquire vào transaction nghiệp
vụ của chính nó.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import threading
from typing import Callable, Iterator, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from platform_core.db import get_session
from platform_core.models import ExecutionLease


ORPHAN_TIMEOUT = timedelta(minutes=20)
HEARTBEAT_SECONDS = 60.0

#: Thời hạn mồ côi cho lease `mode='stream'` — NGẮN HƠN HẲN `ORPHAN_TIMEOUT`.
#:
#: 🔴 SỰ CỐ L-11 (13/09/2026). Một deploy chạy giữa lúc sáu lượt stream đang
#:    chảy. Tiến trình web chết ⇒ luồng đập nhịp chết theo ⇒ sáu dòng lease nằm
#:    lại giữ **TOÀN BỘ** sức chứa (3 mỗi card). Đo được: im 516 s và còn hạn
#:    tới phút thứ 20. Tức **deploy giữa lúc có stream = mất tới 20 phút sức
#:    chứa LLM**, khách thật xếp hàng sau những cái xác.
#:
#: ⭐ ĐỐI CHIẾU KUBERNETES Lease API (`coordination/v1/types.go`) — chuẩn cho
#:    đúng bài "lease của một tiến trình đã chết". Họ KHÔNG xoá lease lúc khởi
#:    động; họ dùng ba thứ ta ĐÃ CÓ: `holderIdentity` + `renewTime` +
#:    `leaseDurationSeconds`, với thời hạn là **bội số nhỏ** của nhịp làm mới
#:    (mặc định của họ: làm mới 10 s / thời hạn 15–40 s ⇒ **1,5–4×**).
#:
#: ⇒ Khuyết tật của ta không phải THIẾU CƠ CHẾ mà là **đặt sai dải**: nhịp 60 s
#:   / thời hạn 1200 s = **20×**. Con số 20 phút hợp cho job nền chạy dài, và nó
#:   bị dùng chung cho lease stream chỉ vì cả hai nằm chung một bảng.
#:
#: 180 s = **3×** nhịp — giữa dải Kubernetes, và chịu được hai nhịp lỡ liên tiếp
#: trước khi một lease đang sống bị thu nhầm.
#:
#: ⛔ ĐỪNG hạ xuống dưới 2× (120 s): một lượt prefill dài có thể làm lỡ một nhịp,
#:    và thu lease của một người đang được phục vụ thì tệ hơn giữ xác thêm 60 s.
ORPHAN_TIMEOUT_STREAM = timedelta(seconds=180)

#: Thời hạn mồ côi cho lease `mode='job'`. 300 s = **5 nhịp tim**.
#:
#: 🔴 SỰ CỐ 14/09/2026, cùng họ với L-11 nhưng ở cửa JOB. Một lượt deploy chạy
#:    giữa lúc bốn job đang chạy; worker bị giết ⇒ không handler nào chạy ⇒
#:    `luong.py:_nha_suat` không bao giờ được gọi. Đo được sau đó:
#:
#:        3090: 3 lease / 2 job THẬT   → một suất bị xác chiếm
#:        job đang xếp hàng: 1         → và nó chờ đúng cái suất ấy
#:
#:    Đường lỗi KHÔNG hỏng — nó nhả suất đúng. Thứ hỏng là **hạn đỡ**: 1.200 s.
#:
#: 🔑 VÌ SAO 300 CHỨ KHÔNG PHẢI 1.200, và vì sao KHÔNG phải 60.
#:
#:    `reclaim_expired` đo `heartbeat_at`, **không** đo `acquired_at`. Đó là
#:    khác biệt quyết định so với các hàng đợi chỉ-có-đồng-hồ: `river` để
#:    `RescueStuckJobsAfter` mặc định **1 giờ** và nhiều bản triển khai còn nâng
#:    lên 24 giờ, đúng vì *"it is purely time based — it has no idea whether a
#:    worker is still alive and working"*. Ta thì biết: nhịp tim là bằng chứng
#:    trực tiếp. Nên con số ở đây phải suy từ `HEARTBEAT_SECONDS`, không mượn
#:    của họ.
#:
#:    5 nhịp = chịu được **bốn** nhịp lỡ liên tiếp. Rộng hơn hẳn cửa stream (3×,
#:    đã chạy thật từ 13/09) vì job có thể prefill 221K token; nhưng nhịp tim là
#:    một luồng RIÊNG, không nằm sau lời gọi model, nên nó không lỡ vì prefill.
#:
#: ⛔ ĐỪNG nâng lại lên 20 phút "cho chắc". Mỗi phút thừa ở đây là một suất GPU
#:    nằm không trong khi có job đang xếp hàng — đo được hôm nay, không phải lo xa.
ORPHAN_TIMEOUT_JOB = timedelta(seconds=300)

#: Thời hạn mồ côi cho lease `mode='sync'`. 120 s = **2 nhịp tim**.
#:
#: 🔴 SỰ CỐ 18/09/2026, cùng họ với L-11 nhưng ở cửa ĐỒNG BỘ. Một phiên khác
#:    deploy giữa một lượt `/chat/completions` của 3.8; tiến trình web chết ⇒
#:    nhịp tim chết theo. Đo được (`docs/ltt_llm_dual/artifacts/bench_hang_cho/
#:    KET_QUA_CACHE_18_09.md` §6):
#:
#:        resource='ltt_38_3090' slot=0 mode='sync' token_dat_truoc=14457
#:        acquired_at = heartbeat_at = 00:54:55   (nhịp KHÔNG bao giờ tiến thêm)
#:
#:    ⇒ **mọi** lượt 3.8 nhận `429 reason=het_cho` suốt **20 phút**
#:    (00:55 → 01:14:55). `stream` và `job` đã có hạn riêng; `sync` rơi vào mặc
#:    định 1.200 s — **gấp 6,7 lần** cửa stream, dù nó là cửa NGẮN NHẤT.
#:
#: 🔑 VÌ SAO 120 — hai chặn, và cả hai đều là số của chính hệ này:
#:
#:    * chặn DƯỚI: `SYNC_BILLED_MAX_SECONDS` (90 s). Cửa đồng bộ hứa trả lời
#:      trong ngân sách ấy và kẹp `max_tokens` theo đúng nó, nên một suất sync
#:      còn SỐNG không bao giờ vượt được. Hạ dưới 90 là thu suất của người đang
#:      được phục vụ.
#:    * chặn TRÊN: 2× `HEARTBEAT_SECONDS` — biên nhỏ nhất mà chú thích của
#:      `ORPHAN_TIMEOUT_STREAM` cho phép ("⛔ ĐỪNG hạ xuống dưới 2×").
#:
#: ⛔ Con số này MỘT MÌNH không sửa được sự cố. Nó chỉ khai hoả khi nhịp tim
#:    **ngừng nói dối**: `runtime_noi_bo/luong.py::giu_suat_dong_bo` phải truyền
#:    `con_song` (mốc tiến triển) vào `keep_alive`, y như cửa stream — nếu không
#:    thì tiến trình còn sống + công việc đã bị bỏ rơi = lease bất tử, đúng L-08
#:    dưới một con số nhỏ hơn. Hai vế, `tests/test_1251` chốt cả hai.
ORPHAN_TIMEOUT_SYNC = timedelta(seconds=120)

#: Trần im lặng của `keep_alive(con_song=...)` — LỚP 2 của cơ chế nhả suất.
#:
#: 🔴 NGUỒN CỦA NGƯỠNG, không phải một con số chọn cho tròn: nó phải ≥ MỌI read
#:    timeout mà một cửa mở luồng tới máy B có thể dùng. Ở httpx một số vô hướng
#:    đặt **read timeout**, tức khoảng lặng hợp lệ dài nhất giữa hai byte từ máy
#:    B. Mặc định lớn nhất là `platform_core/llm/luong_vlm.py:mo(timeout_s=900.0)`
#:    (cửa không truyền `timeout_s`); cửa stream `/api/v1` mở với
#:    `runtime_noi_bo/luong.py:MO_LUONG_GIAY` = 75 s và sống qua prefill dài nhờ
#:    nhịp 15 s của cổng B. 900 ≥ cả hai ⇒ trần này không bao giờ giết một lượt
#:    mà chính lượt đọc còn coi là sống. (Chú thích cũ chỉ dẫn 900 như thể mọi
#:    cửa mở với 900 — O-20, sửa 17/09/2026.)
TRAN_IM_LANG_S = 900.0
log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def reclaim_expired(
    db: Session,
    *,
    resource: str = "",
    timeout: timedelta = ORPHAN_TIMEOUT,
) -> int:
    """Xoá lease mồ côi trong transaction hiện tại và trả số dòng đã xoá."""
    cutoff = _now() - timeout
    # 🔴 L-11: lease `stream` có thời hạn RIÊNG, ngắn hơn nhiều. Xem
    #    `ORPHAN_TIMEOUT_STREAM`. Dùng `min` chứ không thay thẳng: người gọi
    #    truyền `timeout` ngắn hơn (ví dụ dọn tay) thì ý họ vẫn phải thắng.
    cutoff_stream = _now() - min(timeout, ORPHAN_TIMEOUT_STREAM)
    cutoff_job = _now() - min(timeout, ORPHAN_TIMEOUT_JOB)
    cutoff_sync = _now() - min(timeout, ORPHAN_TIMEOUT_SYNC)
    query = db.query(ExecutionLease)
    if resource:
        query = query.filter(ExecutionLease.resource == resource)
    leases = query.all()
    #: `min(...)` ở cả hai vế trên, chứ không thay thẳng: người gọi truyền
    #: `timeout` NGẮN hơn (dọn tay) thì ý họ vẫn phải thắng.
    _han = {"stream": cutoff_stream, "job": cutoff_job, "sync": cutoff_sync}
    expired = [lease for lease in leases
               if _aware(lease.heartbeat_at) < _han.get(lease.mode, cutoff)]
    for lease in expired:
        db.delete(lease)
    if expired:
        from platform_core.public_api import metrics
        metrics.increment(metrics.ADMISSION_EXPIRED, len(expired))
        db.flush()
    return len(expired)


def _khoa_resource(db: Session, resource: str) -> None:
    """Tuần tự hoá luật nhận của MỘT tài nguyên trong transaction hiện tại.

    Luật ngân sách cộng token của mọi lease sống rồi mới INSERT — hai tiến trình
    cùng cộng rồi cùng INSERT là vượt pool dù `UNIQUE(resource, slot)` vẫn giữ
    đúng số slot. Khoá advisory của transaction tự nhả ở commit/rollback, cùng
    khuôn `public_api/limits.py:_lock_job_admission`. SQLite bỏ qua (test logic
    đơn luồng); race kiểm bằng PostgreSQL thật.
    """
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text

    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
               {"k": f"llm-admission:{resource}"})


# ── Luật 0 của `luat_nhan`: nhóm GPU đang cư trú cho ai (dual-model 5.3, D01 B) ─

_BAN_DO_CU_TRU: dict[str, set] | None = None

#: Bao lâu mới nhắc lại một lần cùng một câu "không đọc được dòng cư trú". Người
#: chờ đập nhịp 2 lượt/giây; không có phanh này thì MỘT dòng thiếu ghi đầy log
#: bằng một câu và đẩy mọi thứ khác ra khỏi tầm nhìn.
NHAC_LOI_CU_TRU_S = 30.0
_da_nhac: dict[str, float] = {}


def quen_ban_do_cu_tru() -> None:
    """Xoá bộ nhớ đệm bản đồ cư trú (phép kiểm tiêm bản khai giả gọi hàm này)."""
    global _BAN_DO_CU_TRU
    _BAN_DO_CU_TRU = None


def _ban_do_cu_tru() -> dict[str, set]:
    """`{tên tài nguyên: {(nhóm, vai trò)}}`, đọc từ BẢN KHAI của app.

    ⛔ KHÔNG đọc `tool.admission_resource`: một tool khai `admission_theo_model`
       để trường tĩnh ấy RỖNG (multijob 2.2, R20), nên phép đọc cũ sẽ bỏ qua
       đúng cái tool nó đi tìm. Ở đây lấy thẳng các `AdmissionModel` đã khai, nên
       tên tài nguyên và nhóm cư trú đi ra từ CÙNG MỘT đối tượng — không có cách
       nào ghép tên của model này với nhóm của model kia.

    Đệm cả tiến trình: bản khai của app là MÃ, nó không đổi lúc đang chạy. Chỉ
    đệm khi đọc được — hỏng thì lượt sau thử lại.
    """
    global _BAN_DO_CU_TRU
    if _BAN_DO_CU_TRU is not None:
        return _BAN_DO_CU_TRU
    from platform_core.registry import discover

    ban_do: dict[str, set] = {}
    try:
        for app in discover():
            for tool in getattr(app.manifest, "tools", ()) or ():
                for am in (getattr(tool, "admission_theo_model", {}) or {}).values():
                    nhom = str(getattr(am, "residency_group", "") or "").strip()
                    ten = str(getattr(am, "resource", "") or "").strip()
                    if nhom and ten:
                        ban_do.setdefault(ten, set()).add(
                            (nhom, str(getattr(am, "vai_tro", "") or "").strip()))
    except Exception:  # noqa: BLE001 - nói ra, đừng đệm lại
        log.warning("khong doc duoc ban khai nhom cu tru; coi nhu khong co",
                    exc_info=True)
        return {}
    _BAN_DO_CU_TRU = ban_do
    return ban_do


def nhom_cu_tru(resource: str) -> tuple[str, str]:
    """Nhóm cư trú + vai trò của một tài nguyên. `("", "")` = không có trọng tài.

    ⭐ VÌ SAO TRA THEO TÊN TÀI NGUYÊN, chứ không nhận nhóm cư trú như một tham số
       mới của `xet_va_giu`: `xet_va_giu` có **nhiều** chỗ gọi (stream, ChatLTT,
       đồng bộ, job, planner, và ba app ảnh ở Task 5.5), và một tham số mới thì
       mỗi chỗ gọi là một chỗ có thể quên. Quên ở đây **không làm đỏ** phép kiểm
       nào — nó chỉ mở cửa 3090 cho cả hai model, tức đúng cái hỏng mà cả chương
       trình này sinh ra để dẹp. Tra theo tên thì không chỗ gọi nào phải biết gì,
       và một app mới khai `residency_group` là đã được gác ngay từ lượt đầu.

    Hai bản khai khác nhau cho cùng một tên ⇒ **NÉM**, và chỉ ném cho đúng tài
    nguyên ấy: đó là bản khai tự mâu thuẫn (cùng khuôn fail-closed của
    `suc_chua_admission`), còn mọi tài nguyên không liên can vẫn chạy.
    """
    khai = _ban_do_cu_tru().get(str(resource).strip())
    if not khai:
        return "", ""
    if len(khai) > 1:
        raise ValueError(f"tai nguyen {resource!r} duoc khai hai nhom/vai tro "
                         f"cu tru: {sorted(khai)}")
    return next(iter(khai))


def _nhac(cau: str, nhom: str) -> None:
    import time as _time

    bay_gio = _time.monotonic()
    if bay_gio - _da_nhac.get(nhom, -1e9) < NHAC_LOI_CU_TRU_S:
        return
    _da_nhac[nhom] = bay_gio
    log.warning("%s cho nhom %r => DONG cua admission (fail-closed)", cau, nhom)


def _cua_cu_tru_mo(db: Session, *, nhom: str, vai_tro: str) -> bool:
    """Nhóm GPU có đang mở cửa cho vai trò này? Bên gọi phải ĐANG GIỮ khoá resource.

    ⛔ FAIL-CLOSED với cả ba kiểu không-biết: không có dòng, không đọc được bảng,
       trạng thái lạ. "Không có dòng" nghĩa là **chưa ai biết 3090 đang là của
       ai** — coi như mở ở đó là cấp lease LTT-3.8 lên một card có thể đang vẽ,
       tức OOM cả hai bên. Trọng tài (Task 5.5) tạo dòng ở lượt bước đầu tiên
       với trạng thái đọc từ máy B thật; migration cố ý KHÔNG gieo dòng nào.

    ⚠️ Đọc trong một savepoint: bảng chưa migrate thì `OperationalError` chỉ cuộn
       lại savepoint. Không có nó, giao dịch PostgreSQL bị abort và lượt gọi chết
       ở `commit()` — một lỗi khác hẳn, ở một chỗ khác hẳn, sau khi đã tiêu tiền.
    """
    from platform_core.llm import residency
    from platform_core.models import GpuResidency

    try:
        with db.begin_nested():
            dong = db.get(GpuResidency, nhom)
    except Exception as loi:  # noqa: BLE001 - fail-closed, và nói ra
        dong = None
        # ⛔ NÓI RA CÁI GÌ HỎNG, không chỉ "không đọc được". Bảng chưa migrate,
        #    mất kết nối, hay khoá — ba nguyên nhân, ba việc phải làm khác hẳn
        #    nhau, và người trực đọc dòng này lúc 3 giờ sáng không đoán được.
        #
        # 🔴 Và việc **buộc** ngoại lệ vào một tên là thứ `check_silent_except`
        #    đòi: nó nhận ra "có ghi log" bằng **tên hàm** (`warning`/`error`/…),
        #    nên một hàm bọc như `_nhac` thì nó không thấy. ⛔ Đừng nới bộ dò ra
        #    cho nó thấy `_nhac` — nó canh một **tập hợp** 131 chỗ trong mã sống, và
        #    mỗi lần nới là một lần hạ chuẩn cho cả kho.
        _nhac(f"khong doc duoc bang gpu_residency ({loi!r})", nhom)
    if dong is None:
        _nhac("khong co dong gpu_residency", nhom)
        return False
    # `mo_cho` NÉM với vai trò lạ (bản khai gõ sai) và trả False với trạng thái
    # lạ — hai kiểu hỏng khác nhau, xem docstring của nó. Không nuốt cái nào.
    return residency.mo_cho(str(dong.trang_thai or ""), vai_tro)


def _lop_cua(lease: ExecutionLease) -> str:
    """Lease cũ (trước multijob) không có lớp: job là nền, còn lại là tương tác."""
    from platform_core.llm import luat_nhan

    if lease.lop:
        return lease.lop
    return luat_nhan.NEN if lease.mode == "job" else luat_nhan.TUONG_TAC


def xet_va_giu(
    db: Session,
    *,
    resource: str,
    slots: int,
    user_id: str,
    mode: str,
    holder_id: str,
    job_id: str = "",
    timeout: timedelta = ORPHAN_TIMEOUT,
    lop: str = "",
    token_dat_truoc: int = 0,
    token_prefill_moi: int = 0,
    la_whale: bool = False,
    token_pool: int = 0,
    waiter_id: str = "",
    tuoi_cho_s: float = 0.0,
    now: datetime | None = None,
) -> tuple[ExecutionLease | None, str]:
    """Xét theo `luat_nhan` rồi giành một slot. Trả `(lease | None, mã lý do)`.

    ⭐ Khi `token_pool <= 0` và không khai `lop`: ĐÚNG hành vi cũ "đếm slot" —
       mọi tool không phải model nhà (ảnh, tiếng…) không đổi gì.
    ⛔ Caller giữ quyền commit/rollback, như `acquire` luôn làm.
    🔴 Không nhận tham số thời gian nào (whale nhường, backfill, lão hoá): chúng
       đọc ở `tham_so_da_luot.doc()` NGAY TẠI ĐÂY, đủ cả bộ (phương án C, O-09 —
       trước 17/09 `lao_hoa_s` không được truyền nên env của nó không có hiệu lực).
    """
    from platform_core.llm import luat_nhan, phong_cho, tham_so_da_luot

    resource = resource.strip()
    if not resource or slots <= 0:
        return None, luat_nhan.CHO_SLOT

    # ── Luật 0: cư trú GPU (dual-model 5.3, D01 B) ───────────────────────────
    #
    # 🔴 ĐỌC TRONG KHOÁ, KHÔNG TRƯỚC KHOÁ VÀ KHÔNG Ở MỘT GIAO DỊCH KHÁC. Trọng
    #    tài lật trạng thái nhóm trong đúng advisory lock này. Đọc ngoài khoá là
    #    một TOCTOU có hậu quả vật lý: ta thấy `llm`, trọng tài lật sang `anh` và
    #    ra lệnh nạp model ảnh, rồi ta cấp lease LTT-3.8 lên một card 24 GB đang
    #    nhận 19 GB trọng số khác.
    nhom, vai_tro = nhom_cu_tru(resource)
    residency_mo = True
    if nhom:
        _khoa_resource(db, resource)
        residency_mo = _cua_cu_tru_mo(db, nhom=nhom, vai_tro=vai_tro)

    # ⭐ `not nhom` ở điều kiện dưới đây là chỗ luật 0 thành CƠ HỌC: một tài
    #    nguyên có nhóm cư trú không được đi đường tắt "đếm slot" nữa, vì đường
    #    tắt ấy không hỏi `luat_nhan.xet` và sẽ cấp lease bất chấp cư trú. Job
    #    ảnh đi đúng vào đường tắt đó (`AdmissionModel("anh_3090", 1, 0, …)`:
    #    pool 0, không khai lớp), nên thiếu vế này thì luật 0 không áp cho chính
    #    bên mà cửa sổ ảnh sinh ra để phục vụ — và nó sẽ vẽ trong cửa sổ LLM.
    #    Với tài nguyên KHÔNG có nhóm, đây vẫn là hành vi cũ, từng byte.
    if token_pool <= 0 and not lop and not nhom:
        lease = _giu_slot_trong(db, resource=resource, slots=slots, user_id=user_id,
                                mode=mode, holder_id=holder_id, job_id=job_id,
                                timeout=timeout)
        return lease, ("" if lease is not None else luat_nhan.CHO_SLOT)

    _khoa_resource(db, resource)
    reclaim_expired(db, resource=resource, timeout=timeout)
    song = db.query(ExecutionLease).filter(ExecutionLease.resource == resource).all()
    giu = [luat_nhan.Luot(id=l.id, user_id=l.user_id, lop=_lop_cua(l),
                          token_dat_truoc=int(l.token_dat_truoc or 0),
                          la_whale=bool(l.la_whale)) for l in song]
    cho = phong_cho.chup_nguoi_cho(db, resource=resource, now=now)
    yc = luat_nhan.Luot(id=waiter_id or holder_id, user_id=user_id,
                        lop=lop or luat_nhan.TUONG_TAC,
                        token_dat_truoc=int(token_dat_truoc), la_whale=bool(la_whale),
                        tuoi_s=float(tuoi_cho_s))
    # Mọi tham số thời gian đọc ở đây, một lần, đủ bộ — năm cửa gọi (stream,
    # ChatLTT, đồng bộ, job, planner) không cửa nào tự truyền một số.
    px = luat_nhan.xet(yc, giu, cho, tham_so_da_luot.tham_so_nhan(
        so_slot=slots, pool=int(token_pool), residency_mo=residency_mo))
    if not px.nhan:
        from platform_core.public_api import metrics
        metrics.increment(metrics.ADMISSION_REJECTED)
        return None, px.ly_do
    lease = _chen_lease(db, resource=resource, slots=slots,
                        taken={l.slot for l in song}, user_id=user_id, mode=mode,
                        holder_id=holder_id, job_id=job_id, lop=yc.lop,
                        token_dat_truoc=int(token_dat_truoc),
                        token_prefill_moi=int(token_prefill_moi),
                        la_whale=bool(la_whale))
    return lease, ("" if lease is not None else luat_nhan.CHO_SLOT)


def acquire(
    db: Session,
    *,
    resource: str,
    slots: int,
    user_id: str,
    mode: str,
    holder_id: str,
    job_id: str = "",
    timeout: timedelta = ORPHAN_TIMEOUT,
    **luat,
) -> ExecutionLease | None:
    """Giành một slot; ``None`` nghĩa là không nhận được (xem `xet_va_giu` để biết vì sao).

    `**luat` là các tham số đa lượt của `xet_va_giu` (`lop`, `token_dat_truoc`,
    `token_pool`…). Không truyền gì ⇒ đúng hành vi cũ.
    """
    lease, _ly_do = xet_va_giu(db, resource=resource, slots=slots, user_id=user_id,
                               mode=mode, holder_id=holder_id, job_id=job_id,
                               timeout=timeout, **luat)
    return lease


def _giu_slot_trong(
    db: Session,
    *,
    resource: str,
    slots: int,
    user_id: str,
    mode: str,
    holder_id: str,
    job_id: str = "",
    timeout: timedelta = ORPHAN_TIMEOUT,
) -> ExecutionLease | None:
    """Hành vi CŨ: giành slot trống đầu tiên; ``None`` nghĩa là mọi slot còn sống đang bận."""
    reclaim_expired(db, resource=resource, timeout=timeout)
    taken = {
        row[0]
        for row in db.query(ExecutionLease.slot).filter(
            ExecutionLease.resource == resource).all()
    }
    for slot in range(slots):
        if slot in taken:
            continue
        lease = ExecutionLease(
            resource=resource,
            slot=slot,
            user_id=user_id,
            mode=mode,
            holder_id=holder_id,
            job_id=job_id,
        )
        try:
            with db.begin_nested():
                db.add(lease)
                db.flush()
            from platform_core.public_api import metrics
            metrics.increment(metrics.ADMISSION_ACQUIRED)
            return lease
        except IntegrityError:
            # Một tiến trình khác thắng đúng slot giữa SELECT và INSERT.
            continue
    from platform_core.public_api import metrics
    metrics.increment(metrics.ADMISSION_REJECTED)
    return None


def _chen_lease(db: Session, *, resource: str, slots: int, taken: set,
                user_id: str, mode: str, holder_id: str, job_id: str,
                lop: str, token_dat_truoc: int, token_prefill_moi: int,
                la_whale: bool) -> ExecutionLease | None:
    """INSERT lease vào slot trống đầu tiên — cùng khuôn savepoint của đường cũ."""
    from platform_core.public_api import metrics

    for slot in range(slots):
        if slot in taken:
            continue
        lease = ExecutionLease(
            resource=resource, slot=slot, user_id=user_id, mode=mode,
            holder_id=holder_id, job_id=job_id, lop=lop,
            token_dat_truoc=token_dat_truoc, token_prefill_moi=token_prefill_moi,
            la_whale=la_whale)
        try:
            with db.begin_nested():
                db.add(lease)
                db.flush()
            metrics.increment(metrics.ADMISSION_ACQUIRED)
            return lease
        except IntegrityError:
            # Một tiến trình khác thắng đúng slot giữa SELECT và INSERT (SQLite
            # không có advisory lock; PostgreSQL thì không tới được đây).
            continue
    metrics.increment(metrics.ADMISSION_REJECTED)
    return None


def xoa_co_whale(lease_id: str) -> bool:
    """Prefill của lượt này đã xong (byte đầu tiên về) ⇒ nó thôi là whale.

    ⭐ Luật "≤1 whale" (D-05) nói về PREFILL — thứ làm đói người khác. Phần decode
       sau đó rẻ (M-1: người mới chạy lại ~46 tok/s cạnh nó). Giữ cờ suốt lượt là
       bắt whale kế tiếp chờ thêm vài phút vô cớ. Phiên mới, commit riêng; hỏng
       thì chỉ ghi log — tệ nhất là whale kế chờ lâu hơn, không sai tiền.
    """
    if not lease_id:
        return False

    def _xoa(db: Session, lid: str) -> bool:
        lease = db.get(ExecutionLease, lid)
        if lease is None or not lease.la_whale:
            return False
        lease.la_whale = False
        db.flush()
        return True

    try:
        return _with_fresh_session(_xoa, lease_id)
    except Exception:  # noqa: BLE001 - chỉ ảnh hưởng thứ tự, không ảnh hưởng tiền
        log.exception("khong tat duoc co whale cua lease %s", lease_id)
        return False


def heartbeat(db: Session, lease_id: str) -> bool:
    lease = db.get(ExecutionLease, lease_id)
    if lease is None:
        return False
    lease.heartbeat_at = _now()
    db.flush()
    return True


def release(db: Session, lease_id: str) -> bool:
    """Nhả lease idempotent; caller quyết định thời điểm commit."""
    lease = db.get(ExecutionLease, lease_id)
    if lease is None:
        return False
    db.delete(lease)
    from platform_core.public_api import metrics
    metrics.increment(metrics.ADMISSION_RELEASED)
    db.flush()
    return True


def _with_fresh_session(action, lease_id: str) -> bool:  # noqa: ANN001
    sessions = get_session()
    db = next(sessions)
    try:
        changed = action(db, lease_id)
        db.commit()
        return changed
    except Exception:
        db.rollback()
        raise
    finally:
        sessions.close()


def heartbeat_by_id(lease_id: str) -> bool:
    return _with_fresh_session(heartbeat, lease_id)


def release_by_id(lease_id: str) -> bool:
    return _with_fresh_session(release, lease_id)


@contextmanager
def keep_alive(lease_id: str,
               con_song: Optional[Callable[[], bool]] = None) -> Iterator[None]:
    """Đập nhịp một lease đã commit và nhả idempotent khi khối kết thúc.

    ## 🔴 `con_song` — vì sao tham số này tồn tại (sự cố L-08, 13/09/2026)

    Bản trước đập nhịp **vô điều kiện**:

        while not stop.wait(HEARTBEAT_SECONDS):
            heartbeat_by_id(lease_id)

    Nhịp ấy chứng minh **luồng còn sống**, chứ không chứng minh **công việc còn
    tiến triển**. Hai điều đó tách nhau ra đúng lúc tệ nhất: khách cắt giữa một
    lượt stream, generator đồng bộ bị bỏ rơi và treo vĩnh viễn tại `yield`
    (Starlette không bao giờ `aclose()` thân phản hồi — `responses.py:250`),
    nhưng luồng nhịp **vẫn đập đều**. Với `reclaim_expired` thì lease ấy trông
    khoẻ mạnh mãi mãi, nên `ORPHAN_TIMEOUT` **không bao giờ khai hoả**.

    ⇒ Đo được trên máy thật: một suất GPU bị giữ **≥ 643 s**, và lần đo sau bản
      vá đầu vẫn **~225 s**. Không phải "chậm" — là **bất tử**, vì cả ba lớp dọn
      đều bị cùng một lời nói dối bịt mắt.

    Truyền `con_song` vào là biến nhịp tim thành lời khai có kiểm chứng: chỉ đập
    khi vị từ nói công việc còn nhúc nhích. Im quá `TRAN_IM_LANG_S` thì chính
    luồng nhịp **tự nhả** — không chờ ai tới dọn hộ.

    ⚠️ Đây là **lưới**, không phải đường chính. Đường chính là `khi_dut` ở
       `runtime_noi_bo/luong.py`, đo được là chạy ở +0,05 s. Lưới này tồn tại để
       lớp cuối (`reclaim_expired`) **với tới được**, chứ không để nhanh.
    """
    stop = threading.Event()

    def _pulse() -> None:
        while not stop.wait(HEARTBEAT_SECONDS):
            if con_song is not None and not con_song():
                log.warning(
                    "execution lease %s im lang qua %.0fs - luong nhip TU NHA",
                    lease_id, TRAN_IM_LANG_S)
                try:
                    release_by_id(lease_id)
                except Exception:  # noqa: BLE001 - reclaim_expired van la chan cuoi
                    log.exception("khong tu nha duoc execution lease %s", lease_id)
                return
            try:
                heartbeat_by_id(lease_id)
            except Exception:  # noqa: BLE001 - TTL remains the fallback
                log.exception("khong dap nhip duoc execution lease %s", lease_id)

    pulse = threading.Thread(
        target=_pulse, name=f"execution-hb-{lease_id[:8]}", daemon=True)
    pulse.start()
    try:
        yield
    finally:
        stop.set()
        pulse.join(timeout=5)
        try:
            release_by_id(lease_id)
        except Exception:  # noqa: BLE001 - orphan timeout is the final guard
            log.exception("khong nha duoc execution lease %s", lease_id)


@contextmanager
def hold_persisted(
    *,
    resource: str,
    slots: int,
    user_id: str,
    mode: str,
    holder_id: str,
    job_id: str = "",
    **luat,
) -> Iterator[ExecutionLease | None]:
    """Giữ lease đã commit trong suốt khối và luôn nhả khi rời khối.

    `**luat` chuyển thẳng cho `xet_va_giu` (lớp, token đặt chỗ, pool…) — job nền
    đi qua đây với `lop="nen"` (multijob Task 9).
    """
    sessions = get_session()
    db = next(sessions)
    lease: ExecutionLease | None = None
    try:
        lease = acquire(
            db, resource=resource, slots=slots, user_id=user_id, mode=mode,
            holder_id=holder_id, job_id=job_id, **luat)
        db.commit()
        if lease is None:
            yield None
        else:
            with keep_alive(lease.id):
                yield lease
    finally:
        sessions.close()
