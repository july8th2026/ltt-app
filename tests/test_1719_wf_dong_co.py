"""Động cơ: đồ thị thẳng a→b chạy tới SUCCEEDED; lỗi rẽ nhánh ERROR; huỷ; hạn.

Fix round 1 (review `task-10-review.md`): thêm test cho `danh_thuc_dong_co`
không nhân bản job động cơ (Critical #1), `mot_vong` cách ly lỗi theo từng
run + chạy thật qua `db_factory` (Important #1 / item 6a), node bị từ chối
NGAY TRONG `nop_job` trên cạnh ERROR không để run kẹt không wakeup
(Important #2), `con_viec` chỉ dựa trên wakeup chưa nhặt (Important #3),
quyết định nộp lại của handler `_dong_co` (item 6b), lưới đỡ `bao_tri` không
làm gì khi đã có job động cơ sống (item 6c), và phục hồi đầy đủ bất biến G23
kế thừa từ `test_962` (danh sách cấm đầy đủ + ca đối chứng + `__file__`).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import ast
import pathlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1717_wf_tao_run import wf  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC


@pytest.fixture()
def run(db, wf, monkeypatch):
    from platform_core.workflow import cong_cu, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k")
    return r


def _job_cua(db, run, nid):
    from platform_core.models import Job
    from platform_core.workflow import thi_hanh
    return db.get(Job, thi_hanh.anh_chup_hien_tai(db, run.id, nid).job_id)


def _db_factory():
    """`db_factory` cho `mot_vong` — phiên MỚI trên CÙNG engine sqlite mà
    fixture `db` đã trỏ `LTT_DATABASE_URL` tới (khuôn `apps/agent/jobs._mo`)."""
    from platform_core.db import get_session
    return next(get_session())


def test_do_thi_thang_chay_het(db, run):
    from platform_core import jobs
    from platform_core.workflow import dong_co, may_trang_thai as mtt
    assert dong_co.xu_ly_run(db, run.id, cong_cu=CC) == "RUNNING"
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"
    assert mtt.trang_thai_node(db, run.id, "b") == "PENDING"
    jobs.complete(db, _job_cua(db, run, "a"), {"text": "x"})
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert mtt.trang_thai_node(db, run.id, "b") == "QUEUED"
    assert _job_cua(db, run, "b").params["q"] == "x"
    jobs.complete(db, _job_cua(db, run, "b"), {"text": "y"})
    assert dong_co.xu_ly_run(db, run.id, cong_cu=CC) == "SUCCEEDED"
    assert run.actual_cost == 6 and run.ket_so_luc is not None


def test_nguon_hong_thi_dich_SKIPPED_va_run_FAILED(db, run):
    from platform_core import jobs
    from platform_core.workflow import dong_co, may_trang_thai as mtt, su_kien
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    jobs.fail(db, _job_cua(db, run, "a"), "hong", retry=False)
    assert dong_co.xu_ly_run(db, run.id, cong_cu=CC) == "FAILED"
    assert mtt.trang_thai_node(db, run.id, "b") == "SKIPPED"
    assert su_kien.doc(db, run.id)[-1].loai == "WorkflowFailed"


def test_xu_ly_hai_lan_khong_nop_doi(db, run):
    from platform_core.models import Job
    from platform_core.workflow import dong_co
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert db.query(Job).filter_by(plan_id=run.id).count() == 1


def test_huy_run_huy_job(db, run):
    """⚠️ Tra job bằng `Job.plan_id == run.id` trực tiếp — KHÔNG qua ảnh chụp
    mới nhất: `huy_run` chuyển node sang CANCELLED bằng `chuyen_node(...)`
    không kèm `job_id`, nên ảnh chụp CANCELLED mới nhất mang `job_id == ""`
    (mặc định của `thi_hanh.ghi_chuyen`) — tra qua `anh_chup_hien_tai` sẽ vỡ."""
    from platform_core.models import JOB_CANCELLED, Job
    from platform_core.workflow import dong_co
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert dong_co.huy_run(db, run.id, "nguoi dung huy") is True
    assert run.status == "CANCELLED"
    job = db.query(Job).filter_by(plan_id=run.id).one()
    assert job.status == JOB_CANCELLED


# ── Critical #1 (review round 1): danh_thuc_dong_co không nhân bản ─────────

def test_danh_thuc_dong_co_khong_nhan_ban_khi_da_co_job_dang_song(db):
    """`jobs.submit` chỉ khử trùng ĐÚNG `dedupe_key` — job kế tiếp mà
    `_dong_co` tự nộp dùng khoá RIÊNG (`workflow:dong_co:sau:<id>`), nên gọi
    thẳng `jobs.submit(..., dedupe_key="workflow:dong_co")` không thấy job đó
    và nộp thêm một job động cơ MỚI mỗi lượt — nhân bản không giới hạn.
    `danh_thuc_dong_co` phải tự hỏi bằng Ý NGHĨA (có job động cơ nào CHƯA kết
    thúc không, bất kể khoá) trước khi nộp."""
    from platform_core.models import JOB_DONE, JOB_QUEUED, Job
    from platform_core.workflow import tao_run

    dang_song = Job(user_id=tao_run.DONG_CO_USER, app_slug="agent",
                    job_type=tao_run.DONG_CO_JOB, params={},
                    dedupe_key="workflow:dong_co:sau:cu-nao-do",
                    status=JOB_QUEUED)
    db.add(dang_song)
    db.commit()

    for _ in range(10):
        tao_run.danh_thuc_dong_co(db)
    db.commit()
    assert db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).count() == 1

    dang_song.status = JOB_DONE
    db.commit()
    tao_run.danh_thuc_dong_co(db)
    db.commit()
    assert db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).count() == 2


# ── Important #1 + item 6a: mot_vong chạy thật, cách ly lỗi theo run ────────

def test_mot_vong_end_to_end_va_cach_ly_loi_tung_run(db, wf, monkeypatch):
    """`mot_vong` phải: (a) chạy thật qua `db_factory` trên cùng engine sqlite
    — nhặt đúng run có wakeup tới hạn, xử lý nó, và đánh dấu ĐÚNG wakeup đó
    `claimed_at`; (b) khi run KHÁC trong cùng lượt ném lỗi bên trong
    `xu_ly_run`, lỗi đó không được chặn run lành — cuộn transaction CỦA RIÊNG
    run hỏng, để wakeup của nó CHƯA CLAIM (thử lại đúng lượt sau), đếm vào
    `loi`, và đi tiếp."""
    from platform_core.models import Wakeup, WorkflowRun
    from platform_core.workflow import cong_cu, dong_co, may_trang_thai as mtt
    from platform_core.workflow import tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)

    r_hong, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                                trigger_kind="manual", idempotency_key="k-hong")
    r_lanh, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                                trigger_kind="manual", idempotency_key="k-lanh")
    db.commit()

    goc = dong_co.xu_ly_run

    def _gay_loi(db_, run_id, **kw):
        if run_id == r_hong.id:
            raise RuntimeError("gia lap loi dong co")
        return goc(db_, run_id, **kw)

    monkeypatch.setattr(dong_co, "xu_ly_run", _gay_loi)

    kq = dong_co.mot_vong(_db_factory)
    assert kq["run_da_xu_ly"] == 1, "chi run lanh duoc dem la da xu ly"
    assert kq["loi"] == 1, "run hong phai duoc dem vao 'loi'"

    db.expire_all()
    assert db.get(WorkflowRun, r_lanh.id).status == "RUNNING"
    assert mtt.trang_thai_node(db, r_lanh.id, "a") == "QUEUED"
    w_lanh = db.query(Wakeup).filter_by(run_id=r_lanh.id).all()
    assert w_lanh and all(w.claimed_at is not None for w in w_lanh), (
        "wakeup cua run lanh phai duoc claim (mot_vong da xu ly xong no)")

    assert db.get(WorkflowRun, r_hong.id).status == "QUEUED", (
        "run hong phai giu nguyen trang thai - transaction cua no da cuon")
    w_hong = db.query(Wakeup).filter_by(run_id=r_hong.id).all()
    assert w_hong and all(w.claimed_at is None for w in w_hong), (
        "wakeup cua run hong phai CON CHUA claim de thu lai luot sau")


# ── Important #3 + item 4: con_viec chỉ dựa trên wakeup chưa nhặt ───────────

def test_con_viec_false_khi_run_dang_doi_khong_con_wakeup(db, wf, monkeypatch):
    """Run vừa nộp job cho node "a" (đang chờ job đó xong, chưa có wakeup nào
    — job hoàn tất mới sinh wakeup qua `cau_noi.bao_ket_thuc`) không được coi
    là "còn việc": không có wakeup nào tới hạn ⇒ không có gì để động cơ làm
    ngay bây giờ, và (trước bản vá) `con_viec` vẫn `True` chỉ vì run còn
    RUNNING — khiến `_dong_co` tự nộp lại mỗi 2 giây mãi mãi trên một run
    đang đỗ có chủ đích."""
    from platform_core.workflow import cong_cu, dong_co, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k-park")
    db.commit()

    kq = dong_co.mot_vong(_db_factory)
    assert kq["run_da_xu_ly"] == 1
    assert kq["con_viec"] is False
    assert kq["han_ke_tiep"] is None


# ── Important #2 + item 3: node bị từ chối trong nop_job trên cạnh ERROR ────

def _draft_loi(db):
    from platform_core.workflow import dinh_nghia
    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="loi-error")
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "tool.a", "params": {}}},
        {"id": "b", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "tool.b", "params": {}}}],
        "edges": [{"id": "e", "source_node": "a", "target_node": "b",
                   "source_port": "error", "target_port": "in",
                   "kind": "ERROR"}]}]}
    dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
    return wf


def _cc_hai_cong_cu(gia_a: int, gia_b: int):
    from platform_core.workflow.cong_cu import CongCu
    khuon = dict(app_slug="ltt_llm", job_type="ltt_llm.chat",
                type_version=1, params_schema={}, side_effect="external",
                idempotency_fields=())
    return {
        "tool.a": CongCu(ten="tool.a", tinh_gia=lambda p, g=gia_a: g, **khuon),
        "tool.b": CongCu(ten="tool.b", tinh_gia=lambda p, g=gia_b: g, **khuon),
    }


@pytest.fixture()
def run_loi(db):
    from platform_core import credit
    from platform_core.workflow import dinh_nghia, tao_run
    cc_xuat_ban = _cc_hai_cong_cu(3, 3)   # gia_tran cua CA HAI node = 3
    w = _draft_loi(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=cc_xuat_ban)
    w.published_version_id = v.id
    credit.nap(db, "u1", 100, note="test")
    db.flush()
    r, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k-loi")
    return r


def test_loi_trong_nop_job_khong_ket_khong_wakeup(db, run_loi):
    """`nop_job` từ chối node "a" NGAY TRONG chính nó (giá thật > trần báo
    giá) trước khi có job/waitpoint nào — node "a" chuyển FAILED mà chưa từng
    QUEUED. Cạnh ERROR từ "a" kích hoạt "b" thành READY ở vòng lan truyền THỨ
    HAI, tức SAU khi vòng nộp job của lượt này đã chạy xong — "b" không được
    nộp trong lượt này, và không job/waitpoint nào sinh wakeup cho nó. Nếu
    động cơ không tự ghi một wakeup, run này kẹt tới hạn TTL 20 giờ dù
    `con_viec` vẫn báo `True`. `tool.b` giá thật (3) NẰM TRONG trần (3) — lượt
    xử lý KẾ TIẾP phải nộp được "b" (QUEUED), chứng minh cú kẹt đã được gỡ."""
    from platform_core.models import Wakeup
    from platform_core.workflow import dong_co, may_trang_thai as mtt

    # Mô phỏng mot_vong: wakeup "start" coi như đã được claim TRƯỚC khi
    # xu_ly_run chạy (đúng thứ tự thật — xem `mot_vong`), để phép kiểm này
    # cô lập đúng hành vi của `xu_ly_run` một mình.
    db.query(Wakeup).filter_by(run_id=run_loi.id).update(
        {"claimed_at": datetime.now(timezone.utc)})
    db.flush()

    cc_chay = _cc_hai_cong_cu(999, 3)     # "a" vuot tran (999>3); "b" trong tran
    assert dong_co.xu_ly_run(db, run_loi.id, cong_cu=cc_chay) == "RUNNING"
    assert mtt.trang_thai_node(db, run_loi.id, "a") == "FAILED"
    assert mtt.trang_thai_node(db, run_loi.id, "b") == "READY"

    con_cho = db.query(Wakeup).filter_by(
        run_id=run_loi.id, claimed_at=None).count()
    assert con_cho == 1, (
        "dong co phai tu ghi mot wakeup 'tick' de khong ket toi han TTL")

    dong_co.xu_ly_run(db, run_loi.id, cong_cu=cc_chay)
    assert mtt.trang_thai_node(db, run_loi.id, "b") == "QUEUED"


# ── Item 6b: quyết định nộp lại của handler `_dong_co` ──────────────────────

def test_dong_co_handler_khong_nop_lai_khi_het_viec(db, monkeypatch):
    """`con_viec=False` (không wakeup nào tới hạn) ⇒ handler KHÔNG được nộp
    job động cơ kế tiếp — nếu không, một run đang đỗ có chủ đích sẽ bị đánh
    thức mỗi 2 giây mãi mãi."""
    from apps.agent import jobs as agent_jobs
    from platform_core.models import Job
    from platform_core.workflow import dong_co, tao_run

    monkeypatch.setattr(dong_co, "mot_vong", lambda *_a, **_k: {
        "run_da_xu_ly": 0, "timed_out": 0, "loi": 0,
        "con_viec": False, "han_ke_tiep": None})
    truoc = db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).count()

    ctx = SimpleNamespace(job_type="workflow.dong_co", job_id="job-hien-tai")
    kq = agent_jobs.handle({}, ctx)

    assert kq["con_viec"] is False
    assert (db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).count()
            == truoc), "khong wakeup nao toi han thi khong duoc nop lai"


def test_dong_co_handler_nop_dung_mot_ke_tiep_khi_con_viec(db, monkeypatch):
    """`con_viec=True` ⇒ handler nộp ĐÚNG MỘT job kế tiếp, dưới khoá
    `workflow:dong_co:sau:<job hien tai>`, hẹn chạy trong vòng 2 giây."""
    from apps.agent import jobs as agent_jobs
    from platform_core.models import JOB_RUNNING, Job
    from platform_core.workflow import dong_co, tao_run

    # Job "hien tai" (dang chay handler nay) da la mot hang trong CSDL, đúng
    # hình dạng thật — job_runner đặt status=running TRƯỚC khi gọi handler.
    hien_tai = Job(id="job-hien-tai", user_id=tao_run.DONG_CO_USER,
                   app_slug="agent", job_type=tao_run.DONG_CO_JOB, params={},
                   dedupe_key="workflow:dong_co", status=JOB_RUNNING)
    db.add(hien_tai)
    db.commit()

    monkeypatch.setattr(dong_co, "mot_vong", lambda *_a, **_k: {
        "run_da_xu_ly": 1, "timed_out": 0, "loi": 0,
        "con_viec": True, "han_ke_tiep": None})

    ctx = SimpleNamespace(job_type="workflow.dong_co", job_id=hien_tai.id)
    kq = agent_jobs.handle({}, ctx)
    assert kq["con_viec"] is True

    tat_ca = db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).all()
    ke_tiep = [j for j in tat_ca if j.id != hien_tai.id]
    assert len(ke_tiep) == 1, (
        "phai co DUNG MOT job ke tiep (khong nhan ban qua danh_thuc_dong_co)")
    assert ke_tiep[0].dedupe_key == f"workflow:dong_co:sau:{hien_tai.id}"
    han = ke_tiep[0].next_run_at.replace(
        tzinfo=ke_tiep[0].next_run_at.tzinfo or timezone.utc)
    assert han <= datetime.now(timezone.utc) + timedelta(seconds=2, milliseconds=500)


# ── Item 6c: lưới đỡ bao_tri không làm gì khi đã có job động cơ sống ────────

def test_luoi_do_khong_lam_gi_khi_da_co_job_dang_song(db):
    from platform_core.models import JOB_QUEUED, Job
    from platform_core.workflow import tao_run

    dang_song = Job(user_id=tao_run.DONG_CO_USER, app_slug="agent",
                    job_type=tao_run.DONG_CO_JOB, params={},
                    dedupe_key="workflow:dong_co", status=JOB_QUEUED)
    db.add(dang_song)
    db.commit()
    truoc = db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).count()

    from apps.agent.manifest import _luoi_do_dong_co
    _luoi_do_dong_co()

    sau = db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).count()
    assert sau == truoc, "co san mot job dang song thi luoi do khong duoc nop them"


# ── G23 — không I/O ngoài (phục hồi đầy đủ từ `test_962`, review round 1) ───

def test_dong_co_khong_import_io():
    """Kế thừa NGUYÊN VẸN bất biến `test_962` (đã bị thu hẹp danh sách cấm
    lúc chuyển sang đây — review round 1 bắt được): danh sách cấm ĐẦY ĐỦ,
    và tệp nguồn resolve theo `__file__` (không cwd-relative — phụ thuộc
    ngầm vào thư mục làm việc lúc chạy pytest)."""
    cam = {"requests", "httpx", "urllib", "urllib3", "subprocess", "socket",
           "aiohttp", "smtplib", "ftplib", "telnetlib"}
    tep = (pathlib.Path(__file__).resolve().parent.parent
           / "platform_core" / "workflow" / "dong_co.py")
    cay = ast.parse(tep.read_text(encoding="utf-8"))

    thay = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            thay |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            thay.add(n.module.split(".")[0])

    assert not (thay & cam), (
        f"`dong_co` import thu goi ra ngoai: {sorted(thay & cam)} — "
        "I/O ngoai KHONG duoc nam trong transaction (`G23`)")


def test_doi_chung_bo_do_G23_bat_duoc_mau_xau(tmp_path):
    """Đối chứng: bộ dò phải thật sự bắt được, không chỉ "không thấy gì"."""
    xau = tmp_path / "xau.py"
    xau.write_text("import requests\ndef f(): pass\n", encoding="utf-8")
    cay = ast.parse(xau.read_text(encoding="utf-8"))
    thay = {a.name.split(".")[0]
            for n in ast.walk(cay) if isinstance(n, ast.Import)
            for a in n.names}
    assert "requests" in thay
