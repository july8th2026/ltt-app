"""LTT WORKFLOW V2 · Đợt 3B — hệ con `finally`: kết sổ ĐÚNG MỘT LẦN.

Nguồn thiết kế: `23_24 §6`. Đây là hệ con đáng chú ý nhất của scheduler, và nó
đóng lại một khiếm khuyết **đo được trên production**:

    145 dong "GIU CHO TREO: <n> khoan, <n> credit cua khach dang bi giu"
        trong 28 ngay log worker        (`01 §A`, `G16` -> `G32`)

Hôm nay việc kết sổ nằm **rải rác** và dựa vào một bộ dọn nền: `_terminal_status`
ở một chỗ, `budget.settle` ở chỗ khác, và giữa hai chỗ đó là một cửa sổ mà một
lần restart (13,6 lần/ngày) làm khoản giữ chỗ nằm lại.

⭐ Ở đây kết sổ là **một hệ con chạy trong CÙNG transaction** với lần chuyển
   sang trạng thái kết thúc. Không có cửa sổ nào để restart lọt vào.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf6.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


@pytest.fixture()
def run(db):
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual",
                         estimated_max=100)
    r.hold_id = "hold-1"
    db.commit()
    return r


def _toi_ket_thuc(db, run, trang_thai="SUCCEEDED"):
    from platform_core.workflow import may_trang_thai

    for sang in ("QUEUED", "RUNNING", trang_thai):
        may_trang_thai.chuyen_run(db, run.id, sang=sang)


# ── Đúng một lần ──────────────────────────────────────────────────────────────

def test_ket_so_chay_khi_run_sang_trang_thai_KET_THUC(db, run):
    from platform_core.workflow import ket_so

    _toi_ket_thuc(db, run)
    db.commit()
    db.refresh(run)

    assert run.hold_id == "", "khoan giu cho phai duoc nha"
    assert ket_so.da_ket_so(db, run.id) is True


def test_ket_so_KHONG_chay_khi_run_chua_ket_thuc(db, run):
    from platform_core.workflow import ket_so, may_trang_thai

    for sang in ("QUEUED", "RUNNING"):
        may_trang_thai.chuyen_run(db, run.id, sang=sang)
    db.commit()
    db.refresh(run)

    assert run.hold_id == "hold-1"
    assert ket_so.da_ket_so(db, run.id) is False


def test_goi_ket_so_LAN_HAI_khong_lam_gi_them(db, run):
    """⭐ Luỹ đẳng — vì bộ dọn nền, retry, và người vận hành đều có thể gọi lại."""
    from platform_core.models import CreditEntry
    from platform_core.workflow import ket_so

    _toi_ket_thuc(db, run)
    db.commit()
    db.refresh(run)
    truoc_credit = db.query(CreditEntry).filter_by(user_id="u1").count()
    truoc_luc = run.ket_so_luc

    lan_hai = ket_so.ket_so(db, run.id, ly_do="goi lai bang tay")
    db.commit()
    db.refresh(run)

    # ⚠️ Chi dem CreditEntry thi bai nay XANH-RONG: ma hien tai chua ghi
    #    CreditEntry nao, nen "khong tang" dung ca khi ket so chay lai tu dau.
    #    Ba khang dinh duoi day moi do dung thu can do.
    assert lan_hai is False, "lan hai phai bao KHONG lam gi"
    assert run.ket_so_luc == truoc_luc, "dau ket so khong duoc ghi de"
    assert db.query(CreditEntry).filter_by(user_id="u1").count() == truoc_credit


def test_ket_so_ghi_actual_cost_tu_TONG_anh_chup(db, run):
    """Chi phí thật = tổng `cost_credit` của các ảnh chụp HỢP LỆ, không tính lại."""
    from platform_core.workflow import ket_so, thi_hanh

    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="SUCCEEDED",
                        description="x", cost_credit=30)
    thi_hanh.ghi_chuyen(db, run.id, "n1", execution_status="SUCCEEDED",
                        description="y", cost_credit=12)
    db.commit()
    _toi_ket_thuc(db, run)
    db.commit()
    db.refresh(run)

    assert run.actual_cost == 42
    assert ket_so.da_ket_so(db, run.id) is True


def test_anh_chup_BI_TU_CHOI_khong_duoc_tinh_tien(db, run):
    """⛔ Một lần chuyển bị từ chối là một lần chuyển KHÔNG xảy ra — không thu tiền."""
    from platform_core.workflow import ket_so, thi_hanh

    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="SUCCEEDED",
                        description="that", cost_credit=30)
    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="SUCCEEDED",
                        description="bi tu choi", cost_credit=999,
                        is_valid=False)
    db.commit()
    _toi_ket_thuc(db, run)
    db.commit()
    db.refresh(run)

    assert run.actual_cost == 30, "hang is_valid=False khong duoc vao so"
    assert ket_so.da_ket_so(db, run.id) is True


# ── Ngưỡng M10 ────────────────────────────────────────────────────────────────

def test_M10_moi_trang_thai_KET_THUC_deu_nha_khoan_giu_cho(db):
    """🔴 `M10`: 145 hold treo / 28 ngày → 0.

    Đo trên **tất cả** trạng thái kết thúc, không chỉ đường thành công. Hình
    dạng của khiếm khuyết cũ đúng là như vậy: đường `SUCCEEDED` có người kết
    sổ, còn `SYSTEM_FAILURE` và `TIMED_OUT` thì rơi vào bộ dọn nền.
    """
    from platform_core.workflow import dinh_nghia, ket_so, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="To")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()

    treo = []
    for tt in ("SUCCEEDED", "FAILED", "SYSTEM_FAILURE", "CANCELLED",
               "TIMED_OUT"):
        r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                             owner_id="u1", trigger_kind="manual",
                             estimated_max=50)
        r.hold_id = f"hold-{tt}"
        db.commit()
        _toi_ket_thuc(db, r, tt)
        db.commit()
        db.refresh(r)
        if r.hold_id or not ket_so.da_ket_so(db, r.id):
            treo.append(tt)

    assert treo == [], f"con giu cho treo o: {treo}"


def test_SYSTEM_FAILURE_hoan_TOAN_BO_con_FAILED_thi_khong(db):
    """⭐ Vì sao `SYSTEM_FAILURE` phải tách khỏi `FAILED`: khác nhau về TIỀN.

    Lỗi nghiệp vụ (`FAILED`) — khách vẫn tiêu tài nguyên, thu phần đã dùng.
    Lỗi **của ta** (`SYSTEM_FAILURE`) — không được bắt khách trả.

    LTT hôm nay gộp cả hai vào `AGENT_ERROR` (`G21`), nên không phân biệt được.
    """
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="To")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()

    ra = {}
    for tt in ("FAILED", "SYSTEM_FAILURE"):
        r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                             owner_id="u1", trigger_kind="manual",
                             estimated_max=50)
        r.hold_id = f"h-{tt}"
        thi_hanh.ghi_chuyen(db, r.id, "n0", execution_status="SUCCEEDED",
                            description="da tieu that", cost_credit=20)
        db.commit()
        _toi_ket_thuc(db, r, tt)
        db.commit()
        db.refresh(r)
        ra[tt] = r.actual_cost

    assert ra["FAILED"] == 20, "loi nghiep vu: thu phan da dung"
    assert ra["SYSTEM_FAILURE"] == 0, "loi CUA TA: khong duoc bat khach tra"


def test_ket_so_va_chuyen_trang_thai_o_CUNG_transaction(db, run):
    """⭐ Không có cửa sổ nào để một lần restart lọt vào.

    Kiểm bằng cách **rollback**: nếu kết sổ nằm ngoài transaction chuyển trạng
    thái thì một trong hai sẽ sống sót qua rollback, và ta sẽ thấy trạng thái
    lệch. Cả hai cùng biến mất mới là bằng chứng chúng cùng một transaction.
    """
    from platform_core.workflow import ket_so

    _toi_ket_thuc(db, run)
    db.rollback()
    db.refresh(run)

    assert run.status not in ("SUCCEEDED",)
    assert run.hold_id == "hold-1"
    assert ket_so.da_ket_so(db, run.id) is False
