"""FLOW B · E trên **PostgreSQL thật** — điều kiện ra của P4 (spec §18.5).

| Flow | Đồ thị | Chứng minh |
|---|---|---|
| B | manual → `core.delay` → app mock | **không worker nào bị giữ** trong lúc chờ; **khởi động lại worker giữa chừng thì run vẫn xong** |
| E | app mock → `core.human` → approve đi tiếp / reject đi nhánh khác | cả hai nhánh, **và hết hạn ⇒ reject** |

Cộng hai bài khác cũng chỉ lộ trên PostgreSQL:

- `core.call_workflow` **trong thân `foreach`** (có đối chứng ngoài `foreach`) —
  lỗ tiền đo được 24/09, xem `test_1797`;
- webhook **trùng** không tạo 2 run: ở đây chốt cuối là chỉ mục bộ phận
  `ux_workflow_run_idem` **thật**, không phải điều kiện `sqlite_where`.

## ⚠️ Vì sao PostgreSQL chứ không SQLite (không phải vì "cẩn thận hơn")

`test_1720` đã ghi một ca đo được: `WorkflowRun.started_at` trả **naive** trên
SQLite nhưng **aware** trên PostgreSQL thật, và phép so trong `dong_co.ttl` ném
`TypeError` ở production mà chưa từng lộ trên SQLite. Phase này thêm **bốn** cột
thời gian đi vào cùng một họ phép so (`waitpoint.het_han_luc`, `due_at`,
`workflow_trigger.next_fire_at`, `last_fired_at`), một so sánh **bộ đôi**
(`tuple_(het_han_luc, id)` — cú pháp row-value mà hai dialect thực thi khác
nhau), và bề rộng `String(120)` của `waitpoint.idempotency_key` (SQLite nuốt,
PostgreSQL ném).

Chạy qua `tools/check_multiproc.py` (tệp này nằm trong `TEP_PG`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from platform_core.workflow.cong_cu import CongCu
from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()

#: Khoá advisory riêng cho tệp này — cùng lý do `test_1787._KHOA_LOCK_KEY`:
#: hai worker `xdist` trở về CÙNG một CSDL scratch, và `drop_all`/`create_all`
#: của hai bên đua nhau trên catalog Postgres.
_KHOA_LOCK_KEY = 172012001798

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3,
                          returns={"text": "text"})}


@pytest.fixture()
def pg(monkeypatch):
    url = pg_scratch.scratch_url()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    khoa_engine = sa.create_engine(url, future=True)
    khoa_conn = khoa_engine.connect()
    khoa_conn.execute(sa.text("SELECT pg_advisory_lock(:k)"),
                      {"k": _KHOA_LOCK_KEY})
    try:
        dbmod.Base.metadata.drop_all(dbmod.get_engine())
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        yield dbmod
    finally:
        dbmod.reset_engine()
        khoa_conn.execute(sa.text("SELECT pg_advisory_unlock(:k)"),
                          {"k": _KHOA_LOCK_KEY})
        khoa_conn.close()
        khoa_engine.dispose()


@pytest.fixture()
def db(pg, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu
    from tests.conftest import bao_dam_user
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    s = next(pg.get_session())
    bao_dam_user(s, "u1")
    credit.nap(s, "u1", 100_000, note="test")
    s.commit()
    try:
        yield s
    finally:
        s.close()


def _db_factory():
    from platform_core.db import get_session
    return next(get_session())


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _app(nid: str) -> dict:
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": "text.chat", "params": {}}}


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    return {"id": f"{a}-{b}-{condition}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": kind,
            "condition": condition}


_DEM = {"n": 0}


def _publish(db, nodes, edges=()):
    from platform_core.workflow import dinh_nghia
    _DEM["n"] += 1
    w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"be{_DEM['n']}")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                 "edges": list(edges)}]})
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    db.commit()
    return w, v


def _chay(db, w):
    from platform_core.workflow import tao_run
    _DEM["n"] += 1
    run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                             trigger_kind="manual",
                             idempotency_key=f"bek{_DEM['n']}")
    db.commit()
    return run


def _tt(db, run, nid, vong=()):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid, vong)


def _ra(db, run, nid, vong=()):
    from platform_core.workflow import thi_hanh
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid, vong)
    return dict(anh.output_ref or {}) if anh else {}


def _job_cua(db, run):
    from platform_core.job_scheduler import ORIGIN_WORKFLOW
    from platform_core.models import Job
    from platform_core.workflow import tao_run
    return db.query(Job).filter(
        Job.plan_id == run.id, Job.origin == ORIGIN_WORKFLOW,
        Job.job_type != tao_run.DONG_CO_JOB).all()


def _dong_ho(monkeypatch, giay: int) -> None:
    from platform_core.workflow import danh_thuc, dong_co, han_cho, noi_lai
    from platform_core.workflow.nut_loi import cho

    lech = timedelta(seconds=giay)

    def _moi():
        return datetime.now(timezone.utc).replace(tzinfo=None) + lech

    for mod in (cho, danh_thuc, dong_co, han_cho, noi_lai):
        monkeypatch.setattr(mod, "_bay_gio", _moi)


# ── FLOW B ─────────────────────────────────────────────────────────────────

def test_FLOW_B_delay_KHONG_GIU_WORKER_NAO(db):
    """*"không worker nào bị giữ trong lúc chờ"* — đo bằng bảng `jobs`.

    ⚠️ Câu phép đo trả lời: *trong lúc `core.delay` đang chờ, có hàng `jobs`
       nào thuộc run này không?* Nó **không** trả lời "có luồng nào đang
       `sleep` không" — nhưng `core.delay` không có đường nào khác để chiếm
       một worker ngoài việc nộp job, nên hai câu đó trùng nhau ở đây.
    """
    from platform_core.workflow import dong_co

    w, _v = _publish(db, [_core("d", "delay", duration_s=120), _app("x")],
                     [_canh("d", "x")])
    run = _chay(db, w)
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    db.commit()
    assert _tt(db, run, "d") == "WAITING"
    assert _job_cua(db, run) == []
    assert run.status == "WAITING", "run dang DO co chu dich"


def test_FLOW_B_KHOI_DONG_LAI_worker_giua_chung_run_VAN_XONG(db, monkeypatch):
    """Resume đi qua `mot_vong(db_factory)` — **phiên CSDL MỚI** mỗi lượt.

    ⭐ Không một byte trạng thái nào của phiên cũ sống sót qua `db_factory()`,
       nên nếu run đi tiếp được thì mọi thứ cần nhớ đã nằm trong bảng. Đó là
       định nghĩa đo được của *"khởi động lại worker giữa chừng"*.
    """
    from platform_core import jobs
    from platform_core.models import WorkflowRun
    from platform_core.workflow import cong_cu, dong_co
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)

    w, _v = _publish(db, [_core("d", "delay", duration_s=60), _app("x")],
                     [_canh("d", "x")])
    run = _chay(db, w)
    dong_co.mot_vong(_db_factory)
    db.expire_all()
    assert db.get(WorkflowRun, run.id).status == "WAITING"

    _dong_ho(monkeypatch, 61)
    for _ in range(4):
        dong_co.mot_vong(_db_factory)
    db.expire_all()
    cho_job = [j for j in _job_cua(db, run) if j.status == "queued"]
    assert cho_job, "sau khi het cho, node app phai duoc nop"
    for j in cho_job:
        jobs.complete(db, j, {"text": "ok"})
    db.commit()
    for _ in range(4):
        dong_co.mot_vong(_db_factory)
    db.expire_all()
    xong = db.get(WorkflowRun, run.id)
    assert xong.status == "SUCCEEDED", xong.status
    assert xong.ket_so_luc is not None, "khoan giu cho phai duoc ket so"


def test_FLOW_B_delay_TRONG_foreach_moi_vong_mot_diem_cho(db, monkeypatch):
    """Bề rộng `String(120)` của `waitpoint.idempotency_key` và ràng buộc
    `ux_waitpoint_idem` là THẬT ở đây — SQLite nuốt cả hai."""
    from platform_core.models import Waitpoint
    from platform_core.workflow import dong_co, khoa_idem

    w, _v = _publish(db, [
        _core("f", "foreach", items="[1, 2]", max_items=5, parallelism=2),
        _core("d", "delay", duration_s=60),
        _core("fe", "foreach_end", foreach="f")],
        [_canh("f", "d"), _canh("d", "fe")])
    run = _chay(db, w)
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    db.commit()
    khoa = {x.idempotency_key for x in
            db.query(Waitpoint).filter_by(run_id=run.id, kind="DELAY").all()}
    assert khoa == {
        khoa_idem.khoa_cho(run.id, "d", "DELAY", vong=(("f", 0),)),
        khoa_idem.khoa_cho(run.id, "d", "DELAY", vong=(("f", 1),))}

    _dong_ho(monkeypatch, 61)
    for _ in range(6):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        db.commit()
    assert _tt(db, run, "d", (("f", 0),)) == "SUCCEEDED"
    assert _tt(db, run, "d", (("f", 1),)) == "SUCCEEDED"
    assert run.status == "SUCCEEDED"


# ── FLOW E ─────────────────────────────────────────────────────────────────

def _do_thi_E():
    return ([_app("v"), _core("h", "human", cau_hoi="Duyet video?"),
             _core("dang", "set", bien={"da_dang": "1"}),
             _core("bo", "set", bien={"da_bo": "1"})],
            [_canh("v", "h"),
             _canh("h", "dang", kind="CONTROL", condition="approve"),
             _canh("h", "bo", kind="CONTROL", condition="reject")])


def _toi_human(db, run):
    from platform_core import jobs
    from platform_core.workflow import dong_co
    for _ in range(6):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        db.commit()
        cho_job = [j for j in _job_cua(db, run) if j.status == "queued"]
        for j in cho_job:
            jobs.complete(db, j, {"text": "video.mp4"})
        db.commit()
        if _tt(db, run, "h") == "WAITING":
            return
    raise AssertionError(f"khong toi duoc core.human: {_tt(db, run, 'h')}")


@pytest.mark.parametrize("quyet_dinh,chay,bo", [("approve", "dang", "bo"),
                                                ("reject", "bo", "dang")])
def test_FLOW_E_hai_nhanh_deu_di_dung_duong(db, quyet_dinh, chay, bo):
    from platform_core.workflow import dong_co, noi_lai

    nodes, edges = _do_thi_E()
    w, _v = _publish(db, nodes, edges)
    run = _chay(db, w)
    _toi_human(db, run)
    ra = _ra(db, run, "h")
    assert ra["url"].startswith("/hooks/wp/") and ra["token"]

    assert noi_lai.mo_bang_token(
        db, ra["url"].rsplit("/", 1)[-1], token=ra["token"],
        du_lieu={"than": {"quyet_dinh": quyet_dinh}}) is noi_lai.DA_MO
    db.commit()
    for _ in range(4):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        db.commit()
    assert _tt(db, run, chay) == "SUCCEEDED"
    assert _tt(db, run, bo) == "SKIPPED"
    assert run.status == "SUCCEEDED" and run.ket_so_luc is not None


def test_FLOW_E_HET_HAN_thi_REJECT(db, monkeypatch):
    """Spec §18.5: *"và hết hạn ⇒ reject"*; §5.7: `core.human` mặc định
    `reject`. ⛔ Không `approve`: một workflow duyệt-trước-khi-đăng mà tự
    duyệt khi người bận là đúng thứ node này sinh ra để chặn."""
    from platform_core.workflow import dong_co

    nodes, edges = _do_thi_E()
    nodes[1]["params"]["timeout_s"] = 60
    w, _v = _publish(db, nodes, edges)
    run = _chay(db, w)
    _toi_human(db, run)

    _dong_ho(monkeypatch, 61)
    for _ in range(4):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        db.commit()
    assert _ra(db, run, "h").get("quyet_dinh") == "reject"
    assert _tt(db, run, "bo") == "SUCCEEDED"
    assert _tt(db, run, "dang") == "SKIPPED"


def test_FLOW_E_bo_quet_HET_HAN_danh_thuc_run_khong_co_wakeup(db, monkeypatch):
    """Lưới an toàn T6 trên CSDL thật: xoá hết `wakeup` của run (giả lập một
    hàng hẹn **mất**), rồi chỉ chạy bộ quét — run phải quay lại được.

    ⛔ Không có bước này, một `core.human` hết hạn mà mất hàng hẹn sẽ đứng tới
       `TRAN_RUN` 20 giờ **với tiền bị giữ**, và không dòng nào nói vì sao.
    """
    from platform_core.models import Wakeup
    from platform_core.workflow import dong_co, noi_lai

    nodes, edges = _do_thi_E()
    nodes[1]["params"]["timeout_s"] = 60
    w, _v = _publish(db, nodes, edges)
    run = _chay(db, w)
    _toi_human(db, run)
    db.query(Wakeup).filter_by(run_id=run.id).delete()
    db.commit()

    _dong_ho(monkeypatch, 61)
    assert noi_lai.quet_het_han(db) >= 1
    db.commit()
    assert db.query(Wakeup).filter_by(run_id=run.id, kind="het_han").count() >= 1
    for _ in range(4):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        db.commit()
    assert _tt(db, run, "bo") == "SUCCEEDED"


# ── `core.call_workflow` trong thân `foreach` (lỗ tiền 24/09) ──────────────

def _cay_goi(db, *, trong_foreach: bool):
    con_w, con_v = _publish(db, [
        _core("s", "set", bien={"x": "1"}),
        _core("o", "output", ten="r", gia_tri="vars.x")], [_canh("s", "o")])
    goi = _core("g", "call_workflow", workflow_id=con_w.id,
                version_id=con_v.id, inputs={})
    if trong_foreach:
        nodes = [_core("f", "foreach", items="[1, 2]", max_items=5,
                       parallelism=2), goi,
                 _core("fe", "foreach_end", foreach="f")]
        edges = [_canh("f", "g"), _canh("g", "fe")]
    else:
        nodes, edges = [goi], []
    w, _v = _publish(db, nodes, edges)
    run = _chay(db, w)

    from platform_core.models import WorkflowRun
    from platform_core.workflow import dong_co
    for _ in range(12):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        for c in db.query(WorkflowRun).filter_by(parent_run_id=run.id).all():
            dong_co.xu_ly_run(db, c.id, cong_cu=CC)
        db.commit()
    return run


def test_doi_chung_call_workflow_NGOAI_foreach_chot_binh_thuong(db):
    run = _cay_goi(db, trong_foreach=False)
    assert _tt(db, run, "g") == "SUCCEEDED"
    assert run.status == "SUCCEEDED" and run.ket_so_luc is not None


def test_call_workflow_TRONG_foreach_moi_vong_duoc_chot(db):
    """Trước bản sửa 24/09: `f:0/g` và `f:1/g` đứng `WAITING`, run `RUNNING`,
    `ket_so_luc IS NULL` — **hai run con đã xong** mà tiền vẫn bị giam."""
    from platform_core.models import WorkflowRun

    run = _cay_goi(db, trong_foreach=True)
    assert _tt(db, run, "g", (("f", 0),)) == "SUCCEEDED"
    assert _tt(db, run, "g", (("f", 1),)) == "SUCCEEDED"
    assert run.status == "SUCCEEDED" and run.ket_so_luc is not None
    con = db.query(WorkflowRun).filter_by(parent_run_id=run.id).all()
    assert {c.parent_node_id for c in con} == {"f:0/g", "f:1/g"}


# ── Webhook trùng: chốt cuối là CHỈ MỤC THẬT ───────────────────────────────

def test_webhook_TRUNG_khong_tao_2_run_chot_o_chi_muc_that(db):
    """`ux_workflow_run_idem` là chỉ mục **bộ phận** — trên PostgreSQL nó là
    `WHERE idempotency_key <> ''` thật, không phải một `sqlite_where` mà bộ
    kiểm SQLite bỏ qua."""
    from sqlalchemy.exc import IntegrityError

    from platform_core.models import WorkflowRun
    from platform_core.workflow import khoa_idem, tao_run

    w, _v = _publish(db, [_core("s", "set", bien={"a": "1"})], [])
    khoa = khoa_idem.khoa_webhook("t-pg", idempotency_key="k-1")
    a, moi_a = tao_run.tao_run(db, workflow=w, owner_id="u1",
                               trigger_kind="webhook", idempotency_key=khoa)
    db.commit()
    b, moi_b = tao_run.tao_run(db, workflow=w, owner_id="u1",
                               trigger_kind="webhook", idempotency_key=khoa)
    db.commit()
    assert moi_a is True and moi_b is False and a.id == b.id
    assert db.query(WorkflowRun).filter_by(idempotency_key=khoa).count() == 1

    # ĐỐI CHỨNG: ràng buộc là THẬT — chèn thẳng một hàng thứ hai phải ném.
    with pytest.raises(IntegrityError):
        db.add(WorkflowRun(owner_id="u1", workflow_id=w.id,
                           version_id=w.published_version_id,
                           idempotency_key=khoa))
        db.flush()
    db.rollback()


def test_khoa_diem_cho_DAI_khong_lam_PostgreSQL_nem(db):
    """`waitpoint.idempotency_key` là `String(120)`: PostgreSQL ném
    `StringDataRightTruncation` ở ký tự 121, SQLite nuốt im lặng."""
    from platform_core.models import Waitpoint
    from platform_core.workflow import cho_doi, khoa_idem

    khoa = khoa_idem.khoa_cho("r" * 36, "n" * 60, "HUMAN",
                              vong=tuple((f"vong{i}", i) for i in range(20)))
    assert len(khoa) <= 120
    wp = cho_doi.tao_waitpoint(db, run_id="r1", owner_id="u1", kind="HUMAN",
                               idempotency_key=khoa)
    db.commit()
    assert db.get(Waitpoint, wp.id).idempotency_key == khoa


def test_quet_het_han_dung_SO_SANH_BO_DOI_tren_postgres(db):
    """`tuple_(het_han_luc, id) > tuple_(…)` — cú pháp row-value mà hai
    dialect thực thi khác nhau. Ở đây nó chạy trên bản thật."""
    from platform_core.workflow import cho_doi

    luc = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    ids = []
    for _ in range(12):
        wp = cho_doi.tao_waitpoint(db, run_id="rr", owner_id="u1",
                                   kind="WEBHOOK")
        wp.het_han_luc = luc          # CÙNG một mốc cho tất cả — ca khó
        ids.append(wp.id)
    db.commit()

    thay: list[str] = []
    con_tro = None
    for _ in range(10):
        trang = cho_doi.het_han_den_han(db, con_tro=con_tro, gioi_han=5)
        if not trang:
            break
        assert len(trang) <= 5
        thay.extend(x.id for x in trang)
        con_tro = (trang[-1].het_han_luc, trang[-1].id)
    assert sorted(thay) == sorted(ids)
    assert len(thay) == len(set(thay)), "co hang bi LAP"
