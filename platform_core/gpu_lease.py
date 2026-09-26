"""
gpu_lease.py — giành và trả chỗ trên GPU, nguyên tử (H23).

Bài toán: một máy có **N** GPU, worker có thể chạy nhiều tiến trình. Nếu mỗi tiến
trình tự hỏi `nvidia-smi` rồi chọn card trống nhất thì hai tiến trình khởi động
cùng lúc sẽ **cùng đọc thấy GPU 0 trống**, cùng chọn nó, cùng nạp model, cùng
OOM. Lỗi hiện ra giữa job của khách hàng, không phải lúc xếp lịch.

⚠️ Module này cấp card của **máy A** (nền tảng). N là bao nhiêu thì hỏi máy —
`acquire()` dò bằng `nvidia-smi` lúc chạy, không có con số nào chép trong mã.
Vai trò hai máy và máy nào có card gì: `docs/HAI_MAY_A_VA_B.md`.

Cách giải: đúng khuôn mà hàng đợi job đã dùng và đã chạy ổn từ H2 —

    thu hồi lease mồ côi → giành chỗ → đập nhịp trong lúc chạy → trả chỗ

Điểm khác một chút: hàng đợi job giành bằng `FOR UPDATE SKIP LOCKED`, ở đây
giành bằng **ràng buộc UNIQUE(host, gpu_uuid)**. Hai INSERT cùng lúc thì CSDL
cho đúng một cái thắng, cái thua nhận `IntegrityError` và thử GPU tiếp theo.
Không cần khoá bảng, không có cửa sổ đọc-rồi-ghi.

Máy không có GPU vẫn dùng được module này: `acquire()` trả None và caller chạy
bằng CPU như trước.
"""
from __future__ import annotations

import logging
import socket
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from platform_core import gpu as gpu_mod
from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, GpuLease,
                                  Job)

log = logging.getLogger(__name__)

# ── Mặt phẳng chung cấp máy — mã ở platform_core, dữ liệu ở ProgramData ──────
#
# Máy A còn HAI hệ khác dùng chung card RTX 5060 Ti của nó: `gpu_arbiter` (6 bot
# ở D:\FULL AUTO VIDEO) và Cut_only ver2. Cả ta lẫn họ đều đã kiểm `free_mb` thật
# nên không mù nhau hoàn toàn — nhưng còn đúng MỘT khoảng hở:
#
#   CỬA SỔ NẠP MODEL. Từ lúc giành được card tới lúc VRAM hiện ra trong
#   nvidia-smi mất 20-60 giây. Trong khoảng đó `free_mb` NÓI DỐI với mọi bên,
#   nên hai hệ cùng thấy card trống và cùng nhảy vào.
#
# Và một luật cứng hơn: CHÍNH SÁCH CARD cấp máy. `acquire()` bên dưới sắp xếp
# theo `free_mb` giảm dần, nên khi bot chiếm GPU0 thì GPU1 thành card trống
# nhất và job nặng của khách sẽ rơi vào đó — GPU1 LÀ CARD ĐANG XUẤT HÌNH.
#
# ⚠️ BẢN GHI CỦA THỜI MÁY A CÓ HAI CARD (08/2026). Máy A nay còn một card, nên
#    không có "GPU1" nữa — nhưng luật thì còn: card đang xuất hình không được
#    nhận job nặng, và `acquire()` vẫn phải xếp theo chính sách, không theo
#    `free_mb` trần. Cấu hình hôm nay: `docs/HAI_MAY_A_VA_B.md`.
# Máy đã sập thật 2026-08-26, bugcheck 0x116 VIDEO_TDR_FAILURE, vì một job
# ~12.6 GB chạy 100% suốt 9 phút trên đúng card đó: trình điều khiển hiển thị
# mất quyền điều khiển GPU quá hạn 2 giây và reset thất bại.
#
# Lớp này KHÔNG đổi mô hình lease, KHÔNG đụng bảng PostgreSQL, KHÔNG thêm phụ
# thuộc. Nó chỉ đọc/ghi vài tệp JSON nhỏ ở thư mục trung lập.
#
# ⚠️ TOÀN BỘ bọc try/except và fail-open: thiếu tệp, hỏng tệp, hay lỗi bất kỳ
#    đều quay về ĐÚNG hành vi trước đây. Job của khách không bao giờ được chết
#    vì lớp phối hợp này.
_CLAIM_OWNER = "lttplatform"
_claim_tokens: dict[int, str] = {}

# Chỉ tính công bố còn trong cửa sổ nạp model. Công bố cũ hơn thì VRAM của nó đã
# nằm trong `free_mb` rồi — trừ tiếp là trừ hai lần và ta tự chặn mình vô cớ.
_CUA_SO_NAP_MODEL_S = 90.0


def _claims():
    """Module gpu_claims, hoặc None nếu chưa có (khi đó chạy đúng như cũ).

    ⚠️ Nạp từ TRONG KHO, không phải từ thư mục dùng chung. Bản đầu tiên của
    bản vá này làm sys.path.insert(0, thư-mục-chung) rồi import — thư mục đó
    có quyền ghi cho mọi tài khoản trên máy, nên đó là đường thực thi mã lạ
    vào tiến trình dịch vụ, và insert(0) còn cho phép che khuất module chuẩn.
    Chỉ DỮ LIỆU (claims/, policy.json) mới nằm ở thư mục chung.
    """
    try:
        from platform_core import gpu_claims
        return gpu_claims
    except Exception as e:
        log.debug("gpu_lease/claims bo qua loi: %s", e)
        return None

# Worker chết giữa chừng thì lease phải tự hết hạn, nếu không GPU khoá vĩnh viễn.
# Rộng hơn nhịp đập nhiều lần để một lần GC dài hay đĩa chậm không cướp mất GPU
# của job đang chạy thật.
ORPHAN_TIMEOUT = timedelta(minutes=10)

# Chừa lại cho phân mảnh và cho phần driver/desktop chiếm. Xin đúng sát dung
# lượng còn trống là công thức chắc chắn OOM.
HEADROOM_MB = 1024

#: Đếm được, không chỉ log. Ba đại lượng này đều từng là **sự vắng mặt của bản
#: ghi**, nên không phép đo nào bắt được chúng (Task 23, 26/09/2026):
#:
#:   ``release_khong_thay_dong``  `release` chạy mà dòng đã biến mất — trước đây
#:                               là một no-op IM LẶNG (`if obj is not None:` rồi
#:                               thôi). Nó đã che một lease bị rò suốt một lượt.
#:   ``release_loi``             `release` NÉM (ví dụ `database is locked`).
#:   ``thu_hoi_job_da_xong``     thu hồi theo luật "job đã kết thúc".
#:   ``thu_hoi_het_nhip``        thu hồi theo `ORPHAN_TIMEOUT` (worker đã chết).
#:
#: ⚠️ Hai cột thu hồi phải TÁCH: gộp lại thì "worker chết" và "worker xong rồi
#:    nhưng không xoá được dòng" lại về chung một con số, đúng cái lẫn lộn mà
#:    Task 23 phải gỡ.
THONG_KE: dict[str, int] = {
    "release_khong_thay_dong": 0,
    "release_loi": 0,
    "thu_hoi_job_da_xong": 0,
    "thu_hoi_het_nhip": 0,
}

#: Trạng thái job mà sau đó ⛔ KHÔNG còn ai dùng card nữa. Lấy CHÍNH hằng số của
#: `models`, ⛔ không gõ lại ba chuỗi — hai chỗ khai cùng một điều thì sẽ trôi.
_JOB_DA_XONG = frozenset({JOB_CANCELLED, JOB_DONE, JOB_ERROR})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def host_name() -> str:
    return socket.gethostname()


def lease_cua_job(db: DbSession, job_id: str) -> list[GpuLease]:
    """Mọi lease còn mang `job_id` này, trên máy này.

    ⭐ **Đây là phép đo của một bất biến ở biên**, ⛔ không phải một tiện ích:
       *sau khi một job kết thúc, ⛔ không được còn lease nào mang `job_id` của
       nó.* Một phép kiểm cơ học thắng một lời dặn dò — và trước Task 23 bất biến
       ấy chỉ tồn tại trong docstring của `hold()`, nên nó vỡ suốt một lượt
       nghiệm thu mà ⛔ không ai đo được.
    """
    if not job_id:
        return []
    return list(db.execute(select(GpuLease).where(
        GpuLease.host == host_name(), GpuLease.job_id == job_id)).scalars().all())


def _job_da_ket_thuc(db: DbSession, job_id: str) -> bool:
    """Job của lease này đã ở trạng thái cuối chưa. Fail-CLOSED khi không biết.

    ⭐ Đây là **nửa còn lại** của `ORPHAN_TIMEOUT`, ⛔ không phải bản thay thế:

        job còn `queued`/`running`  → chỉ nhịp đập nói được nó sống (một job nạp
                                      model 8 phút ⛔ không ghi dòng nào) ⇒ giữ
                                      nguyên 10 phút, ⛔ không rút ngắn.
        job đã `done`/`error`/`cancelled`
                                    → ⛔ KHÔNG còn ai dùng card, và ⛔ không còn
                                      ai đập nhịp ⇒ dòng lease là RÁC ⇒ thu hồi
                                      NGAY.

    🔴 Vì sao thiếu nó lại đắt tới vậy (đo 26/09/2026): hệ thống ⛔ không phân
       biệt được *"worker đã chết"* với *"worker xong rồi nhưng ⛔ không xoá được
       dòng"*. Hai cảnh đó trông y như nhau, nên **cả hai** phải chờ hết 10 phút.
       Ba giai đoạn GPU × hai preset ⇒ tới ~60 phút **thuần chờ** mỗi lượt nghiệm
       thu, và triệu chứng biểu hiện thành *"treo, CPU bằng 0"*.

    ⛔ `job_id` rỗng (giành card ⛔ không kèm job) hoặc ⛔ không đọc được bảng
       `jobs` ⇒ trả False. Fail-closed: thà chờ 10 phút còn hơn cướp card của một
       job có thể đang chạy.
    """
    if not job_id:
        return False
    try:
        st = db.execute(select(Job.status).where(
            Job.id == job_id)).scalar_one_or_none()
    except Exception as e:                  # noqa: BLE001
        # Ví dụ CSDL của phép kiểm chỉ có bảng `gpu_leases`. Phải `rollback`:
        # sau một câu lệnh lỗi, session còn lại là session KHÔNG dùng được, và
        # nhánh mồ côi theo nhịp đập ngay bên dưới sẽ chết theo.
        db.rollback()
        log.debug("gpu_lease: khong doc duoc trang thai job %s: %s", job_id[:8], e)
        return False
    if st is None:
        # Job biến mất (bị xoá) — ⛔ không kết luận, để `ORPHAN_TIMEOUT` xử.
        return False
    return str(st) in _JOB_DA_XONG


def reclaim_orphans(db: DbSession, *, timeout: timedelta = ORPHAN_TIMEOUT) -> int:
    """Xoá lease ⛔ không còn ai dùng. Trả số lease thu hồi được.

    HAI luật, hai lý do khác nhau — xem `_job_da_ket_thuc`:

    1. **job đã kết thúc** ⇒ rác, thu hồi ngay (⛔ không chờ nhịp đập);
    2. **hết hạn nhịp đập** (`ORPHAN_TIMEOUT`) ⇒ worker đã chết.
    """
    cutoff = _now() - timeout
    rows = db.execute(select(GpuLease).where(GpuLease.host == host_name())).scalars().all()
    n = 0
    for row in rows:
        if _job_da_ket_thuc(db, row.job_id):
            log.warning("Thu hoi lease GPU cua job DA KET THUC: %s (job=%s, "
                        "worker=%s) — job xong ma lease con treo nghia la "
                        "`release` da khong toi duoc CSDL",
                        row.gpu_uuid[:20], row.job_id[:8], row.worker_id)
            THONG_KE["thu_hoi_job_da_xong"] += 1
            db.delete(row)
            n += 1
            continue
        hb = row.heartbeat_at
        if hb is not None and hb.tzinfo is None:        # SQLite trả naive
            hb = hb.replace(tzinfo=timezone.utc)
        if hb is None or hb < cutoff:
            log.warning("Thu hồi lease GPU mồ côi: %s (job=%s, worker=%s)",
                        row.gpu_uuid[:20], row.job_id[:8], row.worker_id)
            THONG_KE["thu_hoi_het_nhip"] += 1
            db.delete(row)
            n += 1
    if n:
        db.commit()
    return n


def busy_uuids(db: DbSession) -> set[str]:
    """UUID của các GPU đang có lease trên máy này."""
    return set(db.execute(
        select(GpuLease.gpu_uuid).where(GpuLease.host == host_name())
    ).scalars().all())


def acquire(db: DbSession, *, worker_id: str, job_id: str = "",
            need_mb: int = 0) -> GpuLease | None:
    """Giành một GPU còn đủ chỗ. Trả None nếu không có cái nào.

    None có hai nghĩa và caller phải xử cả hai: máy **không có GPU** (chạy CPU),
    hoặc GPU **đều đang bận** (chờ lượt sau). Cả hai đều không phải lỗi.

    Chọn GPU trống nhiều nhất trước — job nặng vào card rảnh nhất, và hai job
    liên tiếp không dồn vào cùng một card.
    """
    gpus = gpu_mod.list_gpus()
    if not gpus:
        return None

    reclaim_orphans(db)
    taken = busy_uuids(db)
    cm = _claims()
    da_giu = {}
    if cm is not None:
        try:
            da_giu = cm.reserved_mb_by_gpu(exclude_owner=_CLAIM_OWNER,
                                           only_unrealized_s=_CUA_SO_NAP_MODEL_S)
        except Exception as e:
            log.debug("gpu_lease/claims bo qua loi: %s", e)
            da_giu = {}

    def _con_cho(g) -> bool:
        # Trừ phần hệ khác vừa công bố nhưng nvidia-smi chưa thấy.
        con = g.free_mb - da_giu.get(g.index, 0)
        if con < need_mb + HEADROOM_MB:
            return False
        # Chính sách máy: card đang xuất hình không nhận job nặng (chống TDR).
        if cm is not None:
            try:
                if not cm.gpu_allows(g.index, need_mb):
                    log.info("Bo qua GPU %s: chinh sach may cam job %sMB (%s)",
                             g.index, need_mb, cm.gpu_note(g.index)[:60])
                    return False
            except Exception as e:
                log.debug("gpu_lease/claims bo qua loi: %s", e)
        return True

    ung_vien = [g for g in gpus if g.uuid not in taken and _con_cho(g)]
    ung_vien.sort(key=lambda g: g.free_mb - da_giu.get(g.index, 0), reverse=True)

    for g in ung_vien:
        lease = GpuLease(host=host_name(), gpu_uuid=g.uuid, gpu_index=g.index,
                         worker_id=worker_id, job_id=job_id, vram_mb=need_mb,
                         acquired_at=_now(), heartbeat_at=_now())
        db.add(lease)
        try:
            db.commit()
        except IntegrityError:
            # Worker khác vừa giành đúng GPU này giữa lúc ta đọc và ghi. Đây là
            # đường chạy BÌNH THƯỜNG của cơ chế, không phải sự cố — lùi lại và
            # thử card tiếp theo.
            db.rollback()
            continue
        db.refresh(lease)
        # Công bố ra mặt phẳng chung. exclusive=True vì mô hình của ta là
        # UNIQUE(host, gpu_uuid) — một job chiếm TRỌN card. Bên kia chia phần
        # theo VRAM nên nếu không nói rõ, họ sẽ nhét thêm job vào card của ta.
        if cm is not None:
            try:
                tok = cm.publish(owner=_CLAIM_OWNER, gpu_index=g.index,
                                 mb=max(need_mb, 1024), job=job_id[:32],
                                 exclusive=True)
                if tok:
                    _claim_tokens[lease.id] = tok
            except Exception as e:
                log.debug("gpu_lease/claims bo qua loi: %s", e)
        log.info("Giành GPU %s (index %s) cho job %s", g.uuid[:20], g.index, job_id[:8])
        return lease
    return None


def heartbeat(db: DbSession, lease: GpuLease) -> None:
    """Báo lease còn sống. Phải gọi định kỳ suốt thời gian chạy."""
    cm = _claims()
    tok = _claim_tokens.get(lease.id)
    if cm is not None and tok:
        try:
            cm.heartbeat(tok)
        except Exception as e:
            log.debug("gpu_lease/claims bo qua loi: %s", e)
    lease.heartbeat_at = _now()
    db.commit()


def release(db: DbSession, lease: GpuLease) -> bool:
    """Trả chỗ. Gọi được nhiều lần mà không sao. Trả **True nếu lượt này xoá dòng**.

    ⚠️ `False` nghĩa là *"⛔ không có dòng nào để xoá"*, ⛔ không phải *"xong rồi"*.
       Gộp hai ca vào một giá trị (`None` cho cả hai, như bản trước Task 23) là
       mất đúng khả năng phân biệt cần để chẩn đoán: dòng biến mất trước khi ta
       xoá chỉ có hai nguồn, và **cả hai đều đáng biết** —

         · `reclaim_orphans` đã dọn trước ⇒ lease của ta **bị người khác thu
           hồi** trong lúc job còn chạy (ca nguy hiểm: card có thể đã bị cấp cho
           job khác);
         · `release` bị gọi hai lần ⇒ một đường mã gọi thừa.

    🔴 Bản cũ là `if obj is not None:` rồi thôi — một **no-op im lặng**, và nó đã
       che một lease bị rò suốt cả một lượt nghiệm thu (Task 23, 26/09/2026). Nay
       nó log ở mức cảnh báo VÀ đếm được (`THONG_KE`).

    ⛔ **⛔ Không bọc try/except quanh `commit`, và ⛔ không retry.** Người gọi
       (`job_runner._giu_gpu`) chỉ commit transaction của **nó** SAU KHI hàm này
       trả về, nên nếu `DELETE` đang bị chặn bởi chính transaction đó thì chờ lâu
       hơn chỉ là chờ lâu hơn. Ném ra để người gọi xử; thu hồi thật là việc của
       `reclaim_orphans` luật "job đã kết thúc".
    """
    cm = _claims()
    tok = _claim_tokens.pop(lease.id, None)
    if cm is not None and tok:
        try:
            cm.release(tok)
        except Exception as e:
            log.debug("gpu_lease/claims bo qua loi: %s", e)
    obj = db.get(GpuLease, lease.id)
    if obj is None:
        THONG_KE["release_khong_thay_dong"] += 1
        log.warning("Tra GPU: KHONG thay dong lease %s (job %s) de xoa — hoac "
                    "`reclaim_orphans` da thu hoi no khi job con chay, hoac "
                    "`release` bi goi hai lan. Ca hai deu can xem lai.",
                    str(lease.id)[:8], str(getattr(lease, "job_id", ""))[:8])
        return False
    try:
        db.delete(obj)
        db.commit()
    except Exception:
        THONG_KE["release_loi"] += 1
        raise
    log.info("Trả GPU %s (job %s)", obj.gpu_uuid[:20], obj.job_id[:8])
    return True


@contextmanager
def hold(db: DbSession, *, worker_id: str, job_id: str = "", need_mb: int = 0):
    """Giành GPU trong một khối `with`, **luôn** trả lại kể cả khi handler ném.

    Quên trả lease thì GPU khoá tới khi hết hạn mồ côi (10 phút) — đủ để một
    chuỗi job lỗi làm đứng cả hàng đợi. Nên đường dùng mặc định phải là khối
    `with` chứ không phải gọi tay `acquire`/`release`.

        with gpu_lease.hold(db, worker_id=wid, job_id=jid, need_mb=6000) as l:
            env = gpu.env_for(l.gpu_uuid) if l else None
            ...
    """
    lease = acquire(db, worker_id=worker_id, job_id=job_id, need_mb=need_mb)
    try:
        yield lease
    finally:
        if lease is not None:
            try:
                release(db, lease)
            except Exception:               # noqa: BLE001 - trả chỗ không được nuốt job
                log.exception("Không trả được lease GPU %s — sẽ hết hạn sau %s",
                              lease.gpu_uuid[:20], ORPHAN_TIMEOUT)
