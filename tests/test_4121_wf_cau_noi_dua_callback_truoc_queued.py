"""B1b (plan `2026-09-25-wf-v2-VAN-HANH.md` §5): đua "callback đến TRƯỚC khi
node được ghi `QUEUED`" — chưa có bài nào đặt tên cho kịch bản này.

## Đua ở đâu

`cau_noi.nop_job` làm BA việc không cùng một câu lệnh: (1) `cho_doi.tao_waitpoint`
+ `chan_node` — node bị CHẶN trên một waitpoint trong khi trạng thái còn
`READY`; (2) `jobs.submit` — job đã tồn tại, một worker có thể nhặt và chạy
NGAY; (3) `may_trang_thai.chuyen_node(sang="QUEUED")` — chỉ SAU đó node mới
được ghi là đang chờ job. Nếu job chạy nhanh hơn bước (3) kịp chạy (job xong,
gọi `jobs.complete` → `cau_noi.bao_ket_thuc` → `cho_doi.ghi_tin_hieu` ghi tín
hiệu SUCCEEDED), tín hiệu đó đến khi node **còn READY**, chưa phải QUEUED.

## Vì sao đây KHÔNG phải một khiếm khuyết chưa vá — cơ chế ĐÃ CÓ

- `may_trang_thai.NODE_CHUYEN["QUEUED"]` cho phép thẳng `SUCCEEDED`/`FAILED`/…
  (bình luận trong `may_trang_thai.py`: *"job có thể xong trước khi động cơ
  kịp thấy nó chạy — động cơ không có hook lúc job bắt đầu"*).
- `cho_doi.ghi_tin_hieu` không đòi node đã QUEUED mới ghi được — nó chỉ cần
  `waitpoint_id` đã tồn tại (bước (1) chạy trước bước (2)/(3) rồi).
- `cau_noi.ap_ket_qua` chỉ áp dụng khi node đang `QUEUED`/`RUNNING`
  (`ap_ket_qua`, `hien not in ("QUEUED","RUNNING") -> return None`) — nên nếu
  gọi khi node còn READY, nó bỏ qua (không mất tín hiệu, chỉ CHƯA áp), và tín
  hiệu vẫn nằm trong CSDL để lần gọi SAU (khi node đã QUEUED, do wakeup) áp
  đúng.

Bài này KHOÁ hành vi đó lại bằng một mốc có tên, chứ không chỉ tin vào bình
luận trong mã.

Chạy trên PostgreSQL thật khi máy có sẵn (`tools/chay_test_pg.py`); tự SKIP
khi không có CSDL scratch (`tests/pg_scratch.skip_without_postgres`).
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa

from platform_core.workflow.cong_cu import CongCu
from tests import pg_scratch
from tests.test_3504_wf_cau_noi_connector import _thanh_connector

pytestmark = pg_scratch.skip_without_postgres()

#: Khoá advisory riêng cho tệp này (cùng lý do `test_1787._KHOA_LOCK_KEY`):
#: hai worker `xdist` trở về CÙNG một CSDL scratch, `drop_all`/`create_all`
#: của hai bên không được đua nhau trên catalog Postgres.
_KHOA_LOCK_KEY = 172012004121

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
    # `credit_entries.user_id` mang KHOÁ NGOẠI tới `users.id` — PostgreSQL
    # thật sự ép nó (SQLite mặc định thì không).
    bao_dam_user(s, "u1")
    credit.nap(s, "u1", 10_000, note="test")
    s.commit()
    try:
        yield s
    finally:
        s.close()


def _draft(db):
    from platform_core.workflow import dinh_nghia
    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="t")
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "text.chat", "params": {}}},
        {"id": "b", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "text.chat", "params": {"q": "$a.text"}}}],
        "edges": [{"id": "e", "source_node": "a", "target_node": "b",
                   "source_port": "text", "target_port": "q", "kind": "DATA"}]}]}
    dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
    return wf


@pytest.fixture()
def wf(db):
    from platform_core.workflow import dinh_nghia
    w = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    db.flush()
    return w


@pytest.fixture()
def run(db, wf):
    from platform_core.workflow import tao_run
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k")
    return r


def test_callback_den_TRUOC_khi_node_duoc_ghi_QUEUED_khong_mat_tin_hieu(
        db, run, monkeypatch):
    """Đua thật: patch `may_trang_thai.chuyen_node` để, đúng lúc `nop_job`
    sắp ghi node "a" sang `QUEUED`, tiêm một `jobs.complete()` XEN VÀO
    TRƯỚC — tái hiện đúng thứ tự "job đã xong, callback đã ghi tín hiệu,
    nhưng node còn chưa kịp QUEUED". Xác nhận: (1) tại thời điểm đó node vẫn
    `READY` — tín hiệu đến sớm THẬT, không phải giả lập sai thứ tự; (2)
    `nop_job` vẫn ghi được `QUEUED` sau đó; (3) `ap_ket_qua` gọi SAU cùng vẫn
    tìm thấy tín hiệu đã ghi và chuyển node sang `SUCCEEDED` — không kẹt,
    không mất."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt

    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")

    goc_chuyen_node = mtt.chuyen_node
    da_tiem = {"lan": 0}

    def chuyen_som(db2, run_id, node_id, *, sang, **kw):
        if sang == "QUEUED" and node_id == "a" and da_tiem["lan"] == 0:
            da_tiem["lan"] += 1
            # Callback "tới" đúng lúc job đã nộp (có `job_id`) nhưng node
            # CHƯA được ghi QUEUED — đây là race muốn tái hiện.
            job = db2.get(Job, kw.get("job_id"))
            assert job is not None, "nop_job phai truyen job_id khi ghi QUEUED"
            assert mtt.trang_thai_node(db2, run_id, node_id) == "READY", (
                "tien dieu kien cua dua: node phai CON READY luc tin hieu toi")
            jobs.complete(db2, job, {"video_id": "VID-DUA", "status": {}})
        return goc_chuyen_node(db2, run_id, node_id, sang=sang, **kw)

    monkeypatch.setattr(mtt, "chuyen_node", chuyen_som)
    jid = cau_noi.nop_job(db, run, node, cong_cu=CC)
    monkeypatch.setattr(mtt, "chuyen_node", goc_chuyen_node)

    assert da_tiem["lan"] == 1, "diem tiem (sang='QUEUED') khong hoi chua chay"
    assert jid is not None
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED", (
        "node phai duoc ghi QUEUED sau khi nop_job xong, du tin hieu toi som")
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "SUCCEEDED", (
        "tin hieu toi TRUOC khi node duoc ghi QUEUED bi danh roi - dung dua")
