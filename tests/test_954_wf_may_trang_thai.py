"""LTT WORKFLOW V2 · Đợt 3A — máy trạng thái, và việc GHI LẠI lần chuyển bị từ chối.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §5`.

Ba trạng thái lấy từ Trigger.dev (`09 §1.4`), mỗi cái vá một khiếm khuyết mà
bản nháp `WF-207` của chính ta mắc phải:

  RUNNING_WITH_WAITPOINTS  *đang chạy* và *đang chờ* KHÔNG loại trừ nhau. Bản
                           nháp viết `RUNNING ⇄ WAITING` tách rời; với ForEach
                           (vài vòng xong, vài vòng đang chờ) thì **không biểu
                           đạt được** — một run có thật không có tên trạng thái.
  SYSTEM_FAILURE           tách khỏi `FAILED` vì hai chuyện khác nhau về **hoàn
                           tiền** và **cảnh báo vận hành**. LTT hôm nay gộp hết
                           vào `AGENT_ERROR` (`G21`).
  ABANDONED                provider CÓ THỂ ĐÃ nhận. `AmbiguousProviderError`
                           xảy ra **10 lần / 28 ngày** (`01 §A.4`) — có thật.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf5.db').as_posix()}")
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
                         owner_id="u1", trigger_kind="manual")
    db.commit()
    return r


# ── Bảng chuyển ───────────────────────────────────────────────────────────────

def test_bon_trang_thai_KET_THUC_cua_run_deu_co_ten_rieng(db):
    """`SYSTEM_FAILURE` phải TÁCH khỏi `FAILED` — khác nhau về tiền và cảnh báo."""
    from platform_core.workflow.may_trang_thai import RUN_KET_THUC

    assert RUN_KET_THUC >= {"SUCCEEDED", "FAILED", "SYSTEM_FAILURE",
                            "CANCELLED", "TIMED_OUT"}
    assert "SYSTEM_FAILURE" in RUN_KET_THUC and "FAILED" in RUN_KET_THUC


def test_node_co_RUNNING_WITH_WAITPOINTS(db):
    """⭐ Đang chạy và đang chờ không loại trừ nhau (ForEach một phần)."""
    from platform_core.workflow.may_trang_thai import NODE_CHUYEN

    assert "RUNNING_WITH_WAITPOINTS" in NODE_CHUYEN
    assert "RUNNING_WITH_WAITPOINTS" in NODE_CHUYEN["RUNNING"]
    assert "RUNNING" in NODE_CHUYEN["RUNNING_WITH_WAITPOINTS"]


def test_node_co_ABANDONED_tach_khoi_FAILED(db):
    """`ABANDONED` = provider CÓ THỂ ĐÃ nhận. Thử lại có thể tính tiền hai lần."""
    from platform_core.workflow.may_trang_thai import NODE_KET_THUC

    assert {"ABANDONED", "FAILED", "SKIPPED"} <= NODE_KET_THUC


def test_chuyen_HOP_LE_duoc_chap_nhan(db, run):
    from platform_core.workflow import may_trang_thai

    ok = may_trang_thai.chuyen_node(db, run.id, "n0",
                                    sang="READY", mo_ta="san sang")
    db.commit()
    assert ok is True


def test_chuyen_KHONG_HOP_LE_bi_tu_choi(db, run):
    """PENDING không nhảy thẳng sang SUCCEEDED được."""
    from platform_core.workflow import may_trang_thai

    ok = may_trang_thai.chuyen_node(db, run.id, "n0",
                                    sang="SUCCEEDED", mo_ta="nhay coc")
    db.commit()
    assert ok is False


def test_chuyen_tu_trang_thai_KET_THUC_bi_tu_choi(db, run):
    """Đã xong thì không quay lại chạy — worker chậm chân không được ghi đè."""
    from platform_core.workflow import may_trang_thai

    for sang in ("READY", "QUEUED", "RUNNING", "SUCCEEDED"):
        assert may_trang_thai.chuyen_node(db, run.id, "n0", sang=sang,
                                          mo_ta="di duong") is True
    db.commit()

    assert may_trang_thai.chuyen_node(db, run.id, "n0", sang="RUNNING",
                                      mo_ta="worker cham chan") is False


# ── ⭐ Lần chuyển bị TỪ CHỐI vẫn được GHI ─────────────────────────────────────

def test_lan_chuyen_bi_tu_choi_VAN_ghi_mot_anh_chup(db, run):
    """`23_24 §5`: *mọi lần chuyển bị từ chối vẫn ghi một snapshot `is_valid=false`*.

    Đây là điều khiến một tranh chấp **điều tra được**. Không ghi thì thứ duy
    nhất còn lại là trạng thái cuối — thứ không nói **ai đã thử gì**.
    """
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import may_trang_thai

    may_trang_thai.chuyen_node(db, run.id, "n0", sang="SUCCEEDED",
                               mo_ta="nhay coc")
    db.commit()

    rows = db.query(NodeRunSnapshot).filter_by(run_id=run.id,
                                               node_id="n0").all()
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert "nhay coc" in rows[0].description


def test_lan_chuyen_bi_tu_choi_KHONG_doi_con_tro(db, run):
    from platform_core.models import NodeRun
    from platform_core.workflow import may_trang_thai

    may_trang_thai.chuyen_node(db, run.id, "n0", sang="READY", mo_ta="ok")
    db.commit()
    may_trang_thai.chuyen_node(db, run.id, "n0", sang="SUCCEEDED",
                               mo_ta="nhay coc")
    db.commit()

    from platform_core.models import NodeRunSnapshot
    con_tro = db.get(NodeRun, (run.id, "n0"))
    assert db.get(NodeRunSnapshot, con_tro.latest_snapshot_id
                  ).execution_status == "READY"


def test_ly_do_TU_CHOI_duoc_ghi_ro_trong_anh_chup(db, run):
    """Ghi lại mà không nói **vì sao** thì vẫn phải đoán khi điều tra."""
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import may_trang_thai

    may_trang_thai.chuyen_node(db, run.id, "n0", sang="SUCCEEDED", mo_ta="x")
    db.commit()

    row = db.query(NodeRunSnapshot).filter_by(run_id=run.id).one()
    assert "PENDING" in row.error and "SUCCEEDED" in row.error


# ── Run ───────────────────────────────────────────────────────────────────────

def test_run_di_het_duong_hop_le(db, run):
    from platform_core.workflow import may_trang_thai

    for sang in ("VALIDATING", "QUEUED", "RUNNING", "SUCCEEDED"):
        assert may_trang_thai.chuyen_run(db, run.id, sang=sang) is True
    db.commit()
    db.refresh(run)
    assert run.status == "SUCCEEDED"


def test_run_RUNNING_va_WAITING_qua_lai_duoc(db, run):
    from platform_core.workflow import may_trang_thai

    for sang in ("VALIDATING", "QUEUED", "RUNNING", "WAITING", "RUNNING"):
        assert may_trang_thai.chuyen_run(db, run.id, sang=sang) is True
    db.commit()


def test_run_da_ket_thuc_thi_khong_chuyen_nua(db, run):
    from platform_core.workflow import may_trang_thai

    for sang in ("VALIDATING", "QUEUED", "RUNNING", "FAILED"):
        may_trang_thai.chuyen_run(db, run.id, sang=sang)
    db.commit()

    assert may_trang_thai.chuyen_run(db, run.id, sang="RUNNING") is False
    db.refresh(run)
    assert run.status == "FAILED"


def test_KHONG_trang_thai_ket_thuc_nao_la_KHOA_cua_bang_chuyen(db):
    """Bất biến cấu trúc: trạng thái kết thúc không có đường đi ra.

    Ghim nó vì nó là **tiền đề** của bài trên: nếu một ngày ai đó thêm
    `"FAILED": frozenset({...})` vào `RUN_CHUYEN`, bài trên vẫn xanh (nó chỉ
    thử đúng một đích) trong khi bất biến đã vỡ.
    """
    from platform_core.workflow.may_trang_thai import RUN_CHUYEN, RUN_KET_THUC

    assert set(RUN_CHUYEN) & RUN_KET_THUC == set()


def test_rao_KET_THUC_van_chan_ke_ca_khi_bang_chuyen_MO_duong(db, run,
                                                              monkeypatch):
    """⭐ Bài này ghim cái RÀO, không ghim cái BẢNG.

    Đối chứng vừa cho thấy: gỡ vế `hien in RUN_KET_THUC` khỏi `chuyen_run` thì
    **không phép kiểm nào đỏ** — vì không trạng thái kết thúc nào là khoá của
    `RUN_CHUYEN`, nên vế kia đã đủ. Tức cái rào là **mã chết**, và bài trên xanh
    vì một lý do khác lý do nó khai.

    Ở đây ta mở một đường đi ra khỏi `FAILED` trong bảng, rồi đòi rào vẫn chặn.
    Đó là cách duy nhất làm cái rào **sống**: nó phòng đúng một chuyện — một
    lần sửa bảng trong tương lai.
    """
    from platform_core.workflow import may_trang_thai

    for sang in ("VALIDATING", "QUEUED", "RUNNING", "FAILED"):
        may_trang_thai.chuyen_run(db, run.id, sang=sang)
    db.commit()

    monkeypatch.setitem(may_trang_thai.RUN_CHUYEN, "FAILED",
                        frozenset({"RUNNING"}))
    assert may_trang_thai.chuyen_run(db, run.id, sang="RUNNING") is False
    db.refresh(run)
    assert run.status == "FAILED"


def test_run_ket_thuc_ghi_finished_at(db, run):
    from platform_core.workflow import may_trang_thai

    for sang in ("VALIDATING", "QUEUED", "RUNNING", "SUCCEEDED"):
        may_trang_thai.chuyen_run(db, run.id, sang=sang)
    db.commit()
    db.refresh(run)
    assert run.finished_at is not None
