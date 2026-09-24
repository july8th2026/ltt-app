"""FLOW A · C · F trên **PostgreSQL thật** — điều kiện ra của P3 (spec §18.5).

⚠️ Vì sao phải là PostgreSQL chứ không phải SQLite: `test_1720` đã ghi lại một
   ca đo được — `WorkflowRun.started_at` trả về **naive** trên SQLite nhưng
   **aware** trên PostgreSQL thật, và phép so trong `dong_co.ttl` ném `TypeError`
   ở production mà **chưa từng** lộ trên SQLite. Node điều khiển thêm ba thứ mà
   SQLite không phân biệt được: `JSON` lồng trong `output_ref` (kết quả
   `foreach`), khoá ngoại `credit_entries.user_id`, và bề rộng `String(64)` của
   `Wakeup.node_run_id` (SQLite nuốt, PostgreSQL ném).

## Ba flow, và chúng chứng minh ĐÚNG cái gì

| Flow | Đồ thị | Chứng minh |
|---|---|---|
| A | manual → set → if → (true) http-mock / (false) stop | nhánh đúng, nhánh kia SKIPPED |
| C | mảng → foreach(max 5) → thân → foreach_end → aggregate | 5 kết quả ĐÚNG THỨ TỰ |
| F | call_workflow (version ghim) → output | output con về cha · huỷ cha huỷ con · chu trình bị từ chối lúc publish |

## ⛔ FLOW C ở đây KHÔNG phủ "app mock trong thân"

Spec §18.5 viết thân FLOW C là một **app mock** (node job). Bản này từ chối node
job trong thân `foreach` **lúc publish** (`than_foreach_co_node_job`) vì
`node_run` khoá `(run_id, node_id)` — 30 vòng không có chỗ cho 30 trạng thái.
Lý do đầy đủ: `nut_loi/vong_lap.py`, báo cáo Task 5. Phép dưới đây dùng thân
**inline** và **nói ra** rằng nó không phủ ca kia; ⛔ nó KHÔNG được đọc là
"FLOW C đạt".

Chạy qua `tools/check_multiproc.py` (tệp này nằm trong `TEP_PG`).
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa

from platform_core.workflow.cong_cu import CongCu
from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()

#: Khoá advisory riêng cho tệp này — cùng lý do `test_1720._KHOA_LOCK_KEY`:
#: hai worker `xdist` trở về CÙNG một CSDL scratch, và `drop_all`/`create_all`
#: của hai bên đua nhau trên catalog Postgres.
_KHOA_LOCK_KEY = 172012001787

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
    # `credit_entries.user_id` mang KHOÁ NGOẠI tới `users.id`, và PostgreSQL
    # THẬT SỰ ép nó (SQLite mặc định thì không — `test_1720` đã ghi lại).
    bao_dam_user(s, "u1")
    credit.nap(s, "u1", 10_000, note="test")
    s.commit()
    try:
        yield s
    finally:
        s.close()


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _app(nid: str) -> dict:
    """"HTTP mock" của FLOW A: một tool registry giả, không ra mạng."""
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
    w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"pg{_DEM['n']}")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                 "edges": list(edges)}]})
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    db.commit()
    return w


def _chay(db, w):
    from platform_core.workflow import tao_run
    _DEM["n"] += 1
    run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                             trigger_kind="manual",
                             idempotency_key=f"pgk{_DEM['n']}")
    db.commit()
    return run


def _vong(db, run, lan=6):
    from platform_core.models import WorkflowRun
    from platform_core.workflow import dong_co
    tt = ""
    for _ in range(lan):
        tt = dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        for con in db.query(WorkflowRun).filter_by(parent_run_id=run.id).all():
            dong_co.xu_ly_run(db, con.id, cong_cu=CC)
        db.commit()
    return tt


def _tt(db, run, nid):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid)


# ── FLOW A ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nguong,chay_http", [(1, True), (99, False)])
def test_FLOW_A_set_if_http_hoac_stop(db, nguong, chay_http):
    """manual → set → if → (true) http-mock / (false) stop."""
    w = _publish(db, [
        _core("s", "set", bien={"diem": "10"}),
        _core("i", "if", dieu_kien=f"vars.diem > {nguong}"),
        _app("http"),
        _core("dung", "stop", trang_thai="SUCCEEDED", ly_do="diem thap")],
        [_canh("s", "i"),
         _canh("i", "http", kind="CONTROL", condition="true"),
         _canh("i", "dung", kind="CONTROL", condition="false")])
    run = _chay(db, w)
    _vong(db, run, lan=1)
    assert _tt(db, run, "s") == "SUCCEEDED" and _tt(db, run, "i") == "SUCCEEDED"
    if chay_http:
        assert _tt(db, run, "http") == "QUEUED"
        assert _tt(db, run, "dung") == "SKIPPED"
    else:
        # `core.stop` kết thúc CẢ run; node http chưa từng được nộp.
        assert run.status == "SUCCEEDED"
        assert _tt(db, run, "http") == "SKIPPED"


def test_FLOW_A_nhanh_khong_chay_KHONG_TON_TIEN(db):
    """Nhánh bị SKIPPED không được để lại một job nào — một job là một bút toán."""
    from platform_core.job_scheduler import ORIGIN_WORKFLOW
    from platform_core.models import Job
    from platform_core.workflow import tao_run
    w = _publish(db, [
        _core("i", "if", dieu_kien="false"), _app("http")],
        [_canh("i", "http", kind="CONTROL", condition="true")])
    run = _chay(db, w)
    _vong(db, run, lan=1)
    assert _tt(db, run, "http") == "SKIPPED"
    assert db.query(Job).filter(
        Job.plan_id == run.id, Job.origin == ORIGIN_WORKFLOW,
        Job.job_type != tao_run.DONG_CO_JOB).count() == 0
    assert run.actual_cost == 0


# ── FLOW C ──────────────────────────────────────────────────────────────────

def test_FLOW_C_foreach_5_ket_qua_DUNG_THU_TU(db):
    """mảng 5 phần tử → foreach(max 5) → thân → foreach_end → aggregate.

    ⛔ Thân là node **inline**, không phải app mock — xem docstring đầu tệp.
    """
    from platform_core.workflow import thi_hanh
    w = _publish(db, [
        _core("f", "foreach", items="[5, 3, 9, 1, 7]", max_items=5,
              parallelism=2),
        _core("x", "transform", gia_tri="loop.item * 10"),
        _core("fe", "foreach_end", foreach="f"),
        _core("g", "aggregate", items="nodes.fe.output.results", phep="sum")],
        [_canh("f", "x"), _canh("x", "fe"), _canh("fe", "g")])
    run = _chay(db, w)
    assert _vong(db, run) == "SUCCEEDED"
    ra = thi_hanh.anh_chup_hien_tai(db, run.id, "fe").output_ref
    # THỨ TỰ ĐẦU VÀO, không phải thứ tự hoàn thành (`foreach.gom_ket_qua`).
    assert ra["results"] == [50, 30, 90, 10, 70]
    assert thi_hanh.anh_chup_hien_tai(db, run.id, "g").output_ref["gia_tri"] == 250


def test_FLOW_C_trang_thai_moi_phan_tu_nam_trong_CSDL(db):
    """`M7` — trạng thái theo CHỈ SỐ, trong CSDL, không phải một con trỏ."""
    from platform_core.models import ForeachMuc, ForeachVong
    w = _publish(db, [
        _core("f", "foreach", items="[1, 2, 3, 4, 5]", max_items=5),
        _core("x", "transform", gia_tri="loop.item"),
        _core("fe", "foreach_end", foreach="f")],
        [_canh("f", "x"), _canh("x", "fe")])
    run = _chay(db, w)
    _vong(db, run)
    vong = db.query(ForeachVong).filter_by(run_id=run.id, node_id="f").one()
    assert vong.so_muc == 5
    # `mo_vong`: xin 8 (mặc định) cho 5 phần tử ⇒ giữ 5. *"Xin 50 luồng cho 3
    # phần tử là một con số vô nghĩa đi vào bộ xếp chỗ."*
    assert vong.parallelism == 5
    muc = db.query(ForeachMuc).filter_by(vong_id=vong.id).all()
    assert len(muc) == 5 and all(m.xong for m in muc)
    # ⭐ Mỗi phần tử MỘT hàng, ghi sẵn từ đầu — `M7` ("100 kết quả, 0 lượt lặp")
    #   chỉ trả lời được nhờ điều đó.
    assert sorted(m.chi_so for m in muc) == [0, 1, 2, 3, 4]


def test_FLOW_C_tran_chi_phi_cua_than_da_duoc_NHAN(db):
    """Trần = `max_items × Σ giá trần node thân` (Task 2), đo trên PG thật."""
    from platform_core.models import WorkflowVersion
    # ⚠️ Thân có node job bị TỪ CHỐI lúc publish (`than_foreach_co_node_job`),
    #    nên trần được đo trên một thân **inline** cạnh một node app NẰM NGOÀI
    #    thân — node ngoài là đối chứng: nó KHÔNG được nhân.
    w = _publish(db, [
        _core("f", "foreach", items="[1]", max_items=5),
        _core("x", "transform", gia_tri="1"),
        _core("fe", "foreach_end", foreach="f"),
        _app("ngoai")],
        [_canh("f", "x"), _canh("x", "fe"), _canh("fe", "ngoai")])
    g = db.get(WorkflowVersion, w.published_version_id).graph
    assert g["he_so_lap"] == {"f": 1, "x": 5, "fe": 1, "ngoai": 1}


# ── FLOW F ──────────────────────────────────────────────────────────────────

def test_FLOW_F_output_con_ve_cha_va_version_da_GHIM(db):
    from platform_core.models import WorkflowVersion
    from platform_core.workflow import thi_hanh
    con = _publish(db, [
        _core("t", "transform", gia_tri='"ket qua con"'),
        _core("o", "output", ten="ra", gia_tri="nodes.t.output.gia_tri")],
        [_canh("t", "o")])
    cha = _publish(db, [
        _core("g", "call_workflow", workflow_id=con.id, version_id="latest",
              inputs={}),
        _core("o", "output", ten="ra_cha",
              gia_tri='nodes.g.output.outputs["ra"]')],
        [_canh("g", "o")])
    g_cha = db.get(WorkflowVersion, cha.published_version_id).graph
    assert g_cha["nodes"][0]["params"]["version_id"] == con.published_version_id

    run = _chay(db, cha)
    assert _vong(db, run) == "SUCCEEDED"
    assert thi_hanh.anh_chup_hien_tai(db, run.id, "g").output_ref["outputs"] \
        == {"ra": "ket qua con"}
    from platform_core.workflow import ket_qua_run
    assert ket_qua_run.doc(db, run.id) == {"ra_cha": "ket qua con"}


def test_FLOW_F_huy_CHA_huy_luon_CON(db):
    from platform_core.models import WorkflowRun
    from platform_core.workflow import dong_co
    con = _publish(db, [_app("a")])
    cha = _publish(db, [_core("g", "call_workflow", workflow_id=con.id,
                              version_id="latest", inputs={})])
    run = _chay(db, cha)
    _vong(db, run, lan=1)
    [rc] = db.query(WorkflowRun).filter_by(parent_run_id=run.id).all()
    assert rc.status in ("QUEUED", "RUNNING")     # doi chung: dang song
    assert dong_co.huy_run(db, run.id, "khach bam Huy") is True
    db.commit()
    assert run.status == "CANCELLED" and rc.status == "CANCELLED"


def test_FLOW_F_chu_trinh_bi_tu_choi_luc_PUBLISH(db):
    from platform_core.workflow import dinh_nghia
    from platform_core.workflow.bien_dich import LoiBienDich
    w = dinh_nghia.tao_workflow(db, owner_id="u1", name="tu goi pg")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": [
            _core("g", "call_workflow", workflow_id=w.id,
                  version_id="latest", inputs={})], "edges": []}]})
    with pytest.raises(LoiBienDich) as e:
        dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    assert e.value.ma == "goi_de_quy"
    db.rollback()


def test_FLOW_F_run_con_KHONG_giu_khoan_thu_hai_tren_PG(db):
    """Bất biến tiền, đo trên sổ credit THẬT (khoá ngoại được ép)."""
    from platform_core import credit
    from platform_core.models import WorkflowRun
    con = _publish(db, [_app("a")])
    cha = _publish(db, [_core("g", "call_workflow", workflow_id=con.id,
                              version_id="latest", inputs={})])
    run = _chay(db, cha)
    _vong(db, run, lan=1)
    [rc] = db.query(WorkflowRun).filter_by(parent_run_id=run.id).all()
    assert rc.hold_id == "" and credit.so_da_giu(db, rc.id) == 0
    assert credit.so_da_giu(db, run.id) == run.estimated_max == 3


# ── Bề rộng cột: thứ SQLite nuốt còn PostgreSQL thì ném ─────────────────────

def test_wakeup_node_run_id_khong_bao_gio_vuot_cot_tren_PG(db):
    """`Wakeup.node_run_id` là `String(64)`; PostgreSQL ném ở ký tự 65.

    Task 1 băm khi đường thi hành quá dài. Đây là chỗ DUY NHẤT phép băm ấy
    được đo trên một CSDL thật sự cưỡng chế bề rộng.
    """
    from platform_core.models import Wakeup
    from platform_core.workflow import danh_thuc
    from datetime import datetime, timedelta, timezone
    sau = tuple((f"vong_lap_ten_rat_dai_so_{i}", i) for i in range(6))
    han = (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(tzinfo=None)
    danh_thuc.hen_node(db, run_id="r-pg-1",
                       node_id="mot_node_ten_cung_rat_dai_de_day_qua_64",
                       kind="delay", due_at=han, vong=sau)
    db.commit()
    w = db.query(Wakeup).filter_by(run_id="r-pg-1").one()
    assert len(w.node_run_id) <= 64 and w.node_run_id.startswith("#")
