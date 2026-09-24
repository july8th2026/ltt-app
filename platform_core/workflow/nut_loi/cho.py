"""`core.delay` — node CHỜ, và cửa RESUME của mọi node chờ (spec §5.7).

## 🔴 Ba luật, và mỗi luật là một run bị treo ở đâu đó

1. **⛔ Không `sleep`.** Node ghi một `waitpoint` + một `wakeup` rồi **kết thúc
   lượt**. Spec §5.7: *"Delay ≤ 60 s vẫn đi cùng đường (không có đường tắt
   trong bộ nhớ — một đường duy nhất để kiểm)."* Một `sleep(60)` trong động cơ
   giữ một worker suốt 60 giây cho một việc **không tính gì cả**, và worker của
   máy này restart 13,6 lần/ngày — mỗi lần restart là một `sleep` mất trắng.

2. **Mọi trạng thái nằm trong BẢNG.** Giữa hai lượt động cơ chỉ còn `waitpoint`
   và `wakeup`; không có biến cục bộ nào sống sót. Đó là điều làm *"khởi động
   lại worker giữa chừng thì run vẫn xong"* thành một câu có thể đo.

3. **🔴 Khoá theo ĐƯỜNG THI HÀNH.** Điểm chờ của `f:0/d` và của `f:1/d` là
   **hai** hàng. Activepieces `000015` (activepieces@`17e2ac0b`): *"a delay or
   approval inside a loop used to reuse one waitpoint row across every
   iteration, so iteration 2 found iteration 1's COMPLETED row … and skipped
   its pause entirely."* Ta lấy khoá từ `khoa_idem.khoa_cho`, tức từ **cùng**
   bộ sinh khoá mà `wakeup` và `node_run` đã dùng.

## Ai gọi cái gì

| Lúc | Hàm | Ai gọi |
|---|---|---|
| Node lần đầu READY | `chay_delay` | `dong_co._pha_inline` · `vong_lap._mot_phan_tu` |
| Node đang WAITING, một lượt động cơ sau | `tiep_mot` | `tiep_cho` (cấp run) · `vong_lap._mot_phan_tu` (trong thân `foreach`) |

⛔ `_lan_truyen` **không** đưa một node `WAITING` về `READY` (bảng `NODE_CHUYEN`
   không có lối ấy), nên không có `tiep_cho` thì node chờ đứng tới TTL 20 giờ —
   đúng hình dạng lỗi mà `vong_lap.tiep_vong` đã phải sinh ra để chặn cho vòng
   lặp.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from platform_core.i18n import N_
from platform_core.workflow import (cho_doi, danh_thuc, han_cho, he_kieu,
                                    khoa_idem, may_trang_thai, ngon_ngu,
                                    noi_lai)
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.nut import Gia, NodeDefinition
from platform_core.workflow.nut_loi.chay import KetQua

#: Loại wakeup mà một điểm chờ hẹn. Một hằng vì hai chỗ ghi và một chỗ đọc.
KIND_WAKEUP = "waitpoint_due"

#: Trần của `duration_s`. Không phải sự thận trọng: hạn CỘNG DỒN của run
#: (`han_cho.tran_cua_run`) sẽ kẹp mọi thứ vượt quá, nên một `duration_s` lớn
#: hơn chỉ là một lời hứa mà máy không giữ. Từ chối lúc publish trung thực hơn.
TRAN_DURATION_S = 20 * 3600


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _khong_tzinfo(luc: datetime) -> datetime:
    return luc.replace(tzinfo=None) if luc.tzinfo is not None else luc


def _han_cua(node: dict, moi_truong: dict) -> datetime:
    """`due_at` của một `core.delay` — từ `duration_s` hoặc từ `until`."""
    p = node.get("params") or {}
    if p.get("duration_s") is not None:
        giay = int(p["duration_s"])
        if giay < 0 or giay > TRAN_DURATION_S:
            raise ValueError(
                f"duration_s phai trong [0, {TRAN_DURATION_S}], nhan {giay}")
        return _bay_gio() + timedelta(seconds=giay)
    gia_tri = ngon_ngu.tinh(str(p.get("until") or ""), moi_truong)
    if isinstance(gia_tri, datetime):
        return _khong_tzinfo(gia_tri)
    try:
        return _khong_tzinfo(datetime.fromisoformat(str(gia_tri)))
    except ValueError as loi:
        raise ValueError(
            f"`until` phai la thoi diem ISO-8601, nhan {str(gia_tri)[:60]!r}"
        ) from loi


def _tim(db, run, node_id: str, kind: str, vong=()):
    """Điểm chờ ĐÃ CÓ của lần chạy này, hoặc `None` — tra bằng khoá đường."""
    khoa = khoa_idem.khoa_cho(run.id, node_id, kind, vong=vong)
    return cho_doi.theo_khoa(db, run.owner_id, khoa), khoa


def mo_diem_cho(db, run, node: dict, *, kind: str, due_at: Optional[datetime],
                che_do_het_han: str = "", vong=(), token_hash: str = "",
                han_rieng_s: Optional[float] = None):
    """Mở MỘT điểm chờ cho một lần node chạy. Luỹ đẳng theo khoá đường.

    Ba việc trong **một** lượt, và thứ tự quan trọng: waitpoint được tạo
    **trước** khi node rời `READY` (spec §5.7 — *"waitpoint được tạo trước khi
    nộp job/phát URL"*), nên không tồn tại tín hiệu cho một waitpoint chưa có.
    """
    nid = str(node["id"])
    cu, khoa = _tim(db, run, nid, kind, vong=vong)
    if cu is not None:
        return cu
    wp = cho_doi.tao_waitpoint(
        db, run_id=run.id, owner_id=run.owner_id, kind=kind,
        due_at=due_at, idempotency_key=khoa)
    wp.het_han_luc = han_cho.han_cho(run, giay=han_rieng_s, moc=due_at)
    wp.che_do_het_han = han_cho.kiem_che_do(
        che_do_het_han or han_cho.che_do_mac_dinh(kind))
    wp.token_hash = token_hash or ""
    # ⭐ `so_nguon = 1`: điểm chờ này có ĐÚNG một nguồn tín hiệu (đồng hồ, cú
    #    POST, người duyệt). Để 0 nghĩa là "barrier động, kết luận bằng
    #    `sealed`" — và không ai niêm phong nó, nên `da_mo()` trả `False` mãi.
    wp.so_nguon = 1
    db.flush()
    cho_doi.chan_node(db, run_id=run.id, node_id=nid, waitpoint_id=wp.id,
                      vong=vong)
    if due_at is not None:
        danh_thuc.hen_luy_dang(
            db, run_id=run.id, kind=KIND_WAKEUP, due_at=due_at,
            node_run_id=danh_thuc.duong_thi_hanh(nid, vong=vong))
    return wp


def chay_delay(db, run, node: dict, *, moi_truong: dict, vong=(),
               **_) -> KetQua:
    """Lần chạy ĐẦU của một `core.delay`: mở điểm chờ, rồi `WAITING`."""
    try:
        due = _han_cua(node, moi_truong)
    except LoiNgonNgu as loi:
        return KetQua(sang="FAILED", error=f"bieu_thuc_loi: {loi}"[:2000])
    except ValueError as loi:
        return KetQua(sang="FAILED", error=f"dau_vao_sai: {loi}"[:2000])
    wp = mo_diem_cho(db, run, node, kind="DELAY", due_at=due, vong=vong)
    # ⚠️ Hạn ĐÃ QUA (một `until` ở quá khứ, hoặc `duration_s = 0`): không mở ra
    #    một lượt chờ rồi chờ một vòng động cơ nữa cho một việc đã tới hạn.
    kq = tiep_mot(db, run, node, vong=vong)
    if kq is not None:
        return kq
    return KetQua(sang="WAITING",
                  output={"cho_den": wp.due_at.isoformat() if wp.due_at else ""})


def _ket_het_han(wp) -> KetQua:
    """Điểm chờ hết hạn ⇒ kết quả theo `che_do_het_han` (spec §5.7).

    ⛔ Không có nhánh "coi như xong": một điểm chờ hết hạn là một câu trả lời
       **không tới**, và giả vờ nó tới là cách im lặng nhất để một workflow
       duyệt-trước-khi-đăng tự đăng.
    """
    che_do = str(wp.che_do_het_han or "fail")
    if che_do == "fail":
        return KetQua(sang="FAILED", error="het_han_cho: diem cho qua han")
    if che_do == "route":
        return KetQua(nhanh=NHANH_HET_HAN, output={"het_han": True})
    # `approve` / `reject` — nghĩa của chúng thuộc về `core.human` (T4).
    return KetQua(nhanh=che_do, output={"het_han": True, "quyet_dinh": che_do})


def tiep_mot(db, run, node: dict, *, vong=()) -> Optional[KetQua]:
    """Điểm chờ của lần chạy này đã hết chờ chưa? `None` = **còn phải chờ**.

    ⚠️ Trả `None` chứ không trả `KetQua(sang="WAITING")`, và đó là chủ ý:
       `WAITING → WAITING` không nằm trong `NODE_CHUYEN`, nên bên gọi mà
       "chuyển" node sang chính trạng thái nó đang có sẽ ghi một ảnh chụp
       `is_valid=False` mỗi 5 giây — một bảng chỉ-thêm đầy rác cho một việc
       không xảy ra.
    """
    nid = str(node["id"])
    kinds = tuple(getattr(
        _dinh_nghia_cua(node), "cho", ()) or ("DELAY",))
    for kind in kinds:
        wp, _khoa = _tim(db, run, nid, kind, vong=vong)
        if wp is None:
            continue
        luc = _bay_gio()
        if wp.status != noi_lai.DANG_CHO:
            # Đã có ai đó mở nó từ ngoài (webhook, người duyệt, bộ phát sự kiện).
            ra = dict(wp.output_ref or {})
            if wp.output_is_error:
                return KetQua(sang="FAILED",
                              error=str(ra.get("error") or "diem_cho_loi"))
            return KetQua(output=ra, nhanh=str(ra.get("_nhanh") or ""))
        if wp.due_at is not None and _khong_tzinfo(wp.due_at) <= luc:
            noi_lai.mo(db, wp, status="SUCCEEDED", ra={}, nguon="dong ho")
            return KetQua(output={"cho_den": wp.due_at.isoformat()})
        if kind == "EVENT":
            # ⭐ Sự kiện được hỏi **lười**, ngay tại đây, thay vì bởi một bộ
            #    phát riêng. Lý do không phải cho gọn: bộ phát riêng sẽ phải
            #    **tìm lại** node (và chỉ số vòng) từ một hàng waitpoint, còn
            #    hàm này đã cầm sẵn cả `node` lẫn `vong` — và chính việc "tìm
            #    lại ngữ cảnh" là chỗ đẻ ra một bộ sinh khoá thứ hai.
            try:
                ev = _su_kien_khop(db, run, node, wp)
            except LoiNgonNgu as loi:
                noi_lai.mo(db, wp, status="FAILED",
                           ra={"error": f"bieu_thuc_loi: {loi}"[:500]},
                           la_loi=True, nguon="loc hong")
                return KetQua(sang="FAILED",
                              error=f"bieu_thuc_loi: {loi}"[:2000])
            if ev is not None:
                noi_lai.mo(db, wp, status="SUCCEEDED", ra={"event": ev},
                           nguon=str(ev.get("id") or ""))
                return KetQua(output={"event": ev})
        if wp.het_han_luc is not None \
                and _khong_tzinfo(wp.het_han_luc) <= luc:
            noi_lai.mo(db, wp, status="FAILED", ra={"het_han": True},
                       la_loi=True, nguon="het han")
            return _ket_het_han(wp)
        return None
    return KetQua(sang="FAILED",
                  error="loi_he_thong: node dang WAITING ma khong co diem cho")


def _dinh_nghia_cua(node: dict):
    from platform_core.workflow import nut_loi

    return nut_loi.tat_ca().get(str(node.get("type")))


def la_node_cho(node: dict) -> bool:
    nd = _dinh_nghia_cua(node)
    return bool(nd is not None and nd.cho)


def tiep_cho(db, run, g: dict, *, bo_qua=frozenset()) -> int:
    """Đẩy tiếp MỌI node chờ đang `WAITING` ở CẤP RUN. Trả số node đã chuyển.

    ⭐ Đây là cửa RESUME, cùng vai với `vong_lap.tiep_vong`. Node chờ nằm
       TRONG thân `foreach` **không** đi qua đây (`bo_qua`): thân do
       `core.foreach` lái, và lái nó ở hai chỗ là hai chỗ để hai chỉ số vòng
       khác nhau cùng tiến một node.
    """
    dem = 0
    for n in g.get("nodes") or []:
        nid = str(n["id"])
        if nid in bo_qua or not la_node_cho(n):
            continue
        if may_trang_thai.trang_thai_node(db, run.id, nid) != "WAITING":
            continue
        kq = tiep_mot(db, run, n)
        if kq is None:
            continue
        ra = dict(kq.output or {})
        if kq.nhanh:
            from platform_core.workflow import moi_truong as _mt
            ra[_mt.KHOA_NHANH] = kq.nhanh
        may_trang_thai.chuyen_node(db, run.id, nid, sang=kq.sang,
                                   mo_ta="diem cho da mo", error=kq.error,
                                   output_ref=ra)
        dem += 1
    return dem


#: Tên nhánh khi `che_do_het_han = "route"`. CỐ ĐỊNH — Canvas vẽ một cổng ra
#: theo đúng chuỗi này.
NHANH_HET_HAN = "het_han"

#: Hai nhánh của `core.human`. Tên CỐ ĐỊNH, và trùng đúng hai giá trị
#: `che_do_het_han` (`approve` / `reject`) của spec §5.7 — nên "hết hạn thì
#: định tuyến" không cần một bảng ánh xạ thứ hai.
NHANH_HUMAN = ("approve", "reject")

#: Chế độ của `core.wait`. ⛔ Danh sách ĐÓNG.
CHE_DO_WAIT = ("webhook", "event")

#: Loại `workflow_event` mà `core.wait mode=event` nghe được (spec §8.4:
#: *"Nguồn sự kiện trong phạm vi: **chỉ** `workflow.run.finished`"*).
LOAI_SU_KIEN = ("WorkflowCompleted", "WorkflowFailed", "WorkflowCancelled")


def _token_moi() -> tuple[str, str]:
    """`(token thô, sha256)` — token URL một-lần của `core.wait mode=webhook`.

    ⛔ Chỉ bản BĂM vào CSDL. Bản thô đi ra `output_ref` của node đúng một lần,
       để đồ thị gửi nó đi (email, Slack, một node HTTP). Lưu bản thô là lưu
       một chìa khoá mở được điểm chờ của khách.
    """
    import secrets

    tho = secrets.token_urlsafe(32)
    return tho, noi_lai.bam_token(tho)


def chay_wait(db, run, node: dict, *, moi_truong: dict, vong=(), **_) -> KetQua:
    """`core.wait` — chờ một cú POST (`webhook`) hoặc một sự kiện (`event`).

    ⭐ ADOPT Activepieces: điểm chờ được tạo **trước** khi URL được phát ra
       (spec §5.7 — *"tín hiệu tới trước khi WAITING"* không tồn tại vì hàng
       waitpoint đã có). `activepieces#14388` (*"Support multiple pauses within
       a single step run"*) là ca mà khoá theo đường thi hành giải hộ ta.
    """
    p = node.get("params") or {}
    che_do = str(p.get("mode") or "webhook")
    if che_do not in CHE_DO_WAIT:
        return KetQua(sang="FAILED",
                      error=f"dau_vao_sai: mode phai la mot trong "
                            f"{list(CHE_DO_WAIT)}")
    kind = "WEBHOOK" if che_do == "webhook" else "EVENT"
    han_s = p.get("timeout_s")
    cu, _khoa = _tim(db, run, str(node["id"]), kind, vong=vong)
    tho = ""
    bam = ""
    if cu is None and kind == "WEBHOOK":
        tho, bam = _token_moi()
    wp = mo_diem_cho(db, run, node, kind=kind, due_at=None,
                     che_do_het_han=str(p.get("het_han") or ""),
                     vong=vong, token_hash=bam,
                     han_rieng_s=float(han_s) if han_s else None)
    kq = tiep_mot(db, run, node, vong=vong)
    if kq is not None:
        return kq
    ra: dict = {}
    if kind == "WEBHOOK":
        ra = {"url": f"/hooks/wp/{wp.id}", "token": tho}
    return KetQua(sang="WAITING", output=ra)


def chay_human(db, run, node: dict, *, moi_truong: dict, vong=(),
               **_) -> KetQua:
    """`core.human` — chờ người duyệt (spec §5.7, ADOPT Flowise/Langflow).

    ⭐ Hai thứ lấy từ họ, và cả hai là *quyết định*, không phải mã:
       resume bằng **API** (không phải một callback trong tiến trình), và
       **hết hạn thì ĐỊNH TUYẾN** chứ không treo. Mặc định `che_do_het_han`
       của node này là `reject` (spec §5.7) — ⛔ không phải `approve`: một
       workflow duyệt-trước-khi-đăng mà tự duyệt khi người bận là đúng thứ
       `core.human` sinh ra để chặn.
    """
    p = node.get("params") or {}
    cu, _khoa = _tim(db, run, str(node["id"]), "HUMAN", vong=vong)
    tho = ""
    bam = ""
    if cu is None:
        tho, bam = _token_moi()
    han_s = p.get("timeout_s")
    wp = mo_diem_cho(db, run, node, kind="HUMAN", due_at=None,
                     che_do_het_han=str(p.get("het_han") or ""),
                     vong=vong, token_hash=bam,
                     han_rieng_s=float(han_s) if han_s else None)
    kq = tiep_mot(db, run, node, vong=vong)
    if kq is not None:
        return kq
    return KetQua(sang="WAITING",
                  output={"url": f"/hooks/wp/{wp.id}", "token": tho,
                          "cau_hoi": str(p.get("cau_hoi") or ""),
                          "het_han_luc": (wp.het_han_luc.isoformat()
                                          if wp.het_han_luc else "")})


def _su_kien_khop(db, run, node: dict, wp) -> Optional[dict]:
    """Sự kiện đầu tiên KHỚP bộ lọc của một `core.wait mode=event`.

    ⚠️ Quét từ `wp.created_at` trở đi, không quét cả bảng: điểm chờ chỉ nghe
       những gì xảy ra SAU khi nó mở. Đây cũng là lý do waitpoint phải được
       tạo trước khi node rời `READY`.

    ⛔ Phạm vi HẸP theo spec §8.4: chỉ dòng kết thúc run (`LOAI_SU_KIEN`).
       Sự kiện của job ngoài workflow *"buộc `jobs.py` ghi vào bảng của
       workflow cho mọi job, phá luật §3.1-3"*.
    """
    from sqlalchemy import select

    from platform_core.models import WorkflowEvent

    loc = str((node.get("params") or {}).get("loc") or "")
    hang = db.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.loai.in_(LOAI_SU_KIEN),
               WorkflowEvent.created_at >= wp.created_at,
               WorkflowEvent.run_id != run.id)
        .order_by(WorkflowEvent.created_at, WorkflowEvent.id)
        .limit(200)).scalars()
    for ev in hang:
        mt = {"event": {"id": ev.id, "run_id": ev.run_id, "loai": ev.loai,
                        "status": str((ev.du_lieu or {}).get("status") or ""),
                        "outputs": dict((ev.du_lieu or {}).get("outputs") or {})}}
        if not loc:
            return mt["event"]
        try:
            if bool(ngon_ngu.tinh(loc, mt)):
                return mt["event"]
        except LoiNgonNgu:
            # Bộ lọc hỏng ⇒ điểm chờ này không bao giờ khớp được. Nói ra bằng
            # một ngoại lệ ở bên gọi, ⛔ không bỏ qua im lặng.
            raise
    return None


_CHO_VAO = (("in", he_kieu.Cong(type="any", required=False, nhan="in")),)

DINH_NGHIA = (
    (NodeDefinition(
        type="core.delay", type_version=1, kind="control", category="FLOW",
        title=N_("Chờ"),
        description=N_("Dừng một khoảng thời gian rồi chạy tiếp."),
        icon="⏳",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(("cho_den", he_kieu.Cong(type="text", required=False,
                                          nhan="cho_den")),),
        tham_so={"type": "object",
                 "properties": {"duration_s": {"type": "int",
                                               "max": TRAN_DURATION_S},
                                "until": {"type": "bieu_thuc"}},
                 "required": [],
                 # ⭐ Không có cái nào ⇒ một điểm chờ KHÔNG BAO GIỜ tới hạn.
                 "mot_trong": [["duration_s", "until"]],
                 "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=("DELAY",), ma_loi=("bieu_thuc_loi", "dau_vao_sai",
                                "het_han_cho"),
        publish_duoc=True), chay_delay),
    (NodeDefinition(
        type="core.wait", type_version=1, kind="control", category="FLOW",
        title=N_("Chờ tín hiệu"),
        description=N_("Chờ một cú gọi webhook hoặc một sự kiện khớp bộ lọc."),
        icon="⇩",
        cong_vao=_CHO_VAO,
        cong_ra=(("url", he_kieu.Cong(type="text", required=False, nhan="url")),
                 ("token", he_kieu.Cong(type="text", required=False,
                                        nhan="token")),
                 ("event", he_kieu.Cong(type="any", required=False,
                                        nhan="event")),
                 ("than", he_kieu.Cong(type="any", required=False,
                                       nhan="than"))),
        tham_so={"type": "object",
                 "properties": {
                     "mode": {"type": "enum", "values": list(CHE_DO_WAIT)},
                     "timeout_s": {"type": "int", "max": TRAN_DURATION_S},
                     "loc": {"type": "bieu_thuc"},
                     "het_han": {"type": "enum",
                                 "values": list(han_cho.CHE_DO_HET_HAN)}},
                 "required": ["mode"], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        # ⚠️ HAI loại: một node `core.wait` chỉ mở MỘT trong hai, nhưng
        #    `tiep_mot` phải tra được cả hai — `mode` nằm trong `params`, còn
        #    `cho` là thứ nền tảng đọc mà KHÔNG cần biết tên tham số của node.
        cho=("WEBHOOK", "EVENT"),
        ma_loi=("bieu_thuc_loi", "dau_vao_sai", "het_han_cho"),
        publish_duoc=True), chay_wait),
    (NodeDefinition(
        type="core.human", type_version=1, kind="control", category="FLOW",
        title=N_("Chờ người duyệt"),
        description=N_("Dừng cho tới khi có người duyệt hoặc từ chối."),
        icon="✋",
        cong_vao=_CHO_VAO,
        cong_ra=(("url", he_kieu.Cong(type="text", required=False, nhan="url")),
                 ("token", he_kieu.Cong(type="text", required=False,
                                        nhan="token")),
                 ("quyet_dinh", he_kieu.Cong(type="text", required=False,
                                             nhan="quyet_dinh")),
                 ("du_lieu", he_kieu.Cong(type="any", required=False,
                                          nhan="du_lieu"))),
        tham_so={"type": "object",
                 "properties": {
                     "cau_hoi": {"type": "string"},
                     "timeout_s": {"type": "int", "max": TRAN_DURATION_S},
                     "het_han": {"type": "enum",
                                 "values": list(han_cho.CHE_DO_HET_HAN)}},
                 "required": [], "additionalProperties": False},
        thi_hanh="inline", gia=Gia.mien_phi(), quyen=frozenset(),
        cho=("HUMAN",), ma_loi=("het_han_cho",),
        publish_duoc=True), chay_human),
)

__all__ = ["CHE_DO_WAIT", "DINH_NGHIA", "KIND_WAKEUP", "LOAI_SU_KIEN",
           "NHANH_HET_HAN", "NHANH_HUMAN", "TRAN_DURATION_S", "chay_delay",
           "chay_human", "chay_wait", "la_node_cho", "mo_diem_cho",
           "tiep_cho", "tiep_mot"]
