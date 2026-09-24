"""Khoá của phase P4 — waitpoint theo ĐƯỜNG THI HÀNH, và khoá khử trùng trigger.

🔴 BÀI HỌC MANG THEO TỪ PHASE 4 (plan wf-v2 §4 P4)

Ba bảng — `wakeup`, `node_run`, `dedupe_key` — đều **đã** từng khoá theo
`node_id` **trần**, và cả ba đều hỏng cùng một kiểu: hai vòng của một `foreach`
sinh **một** khoá, nên vòng 2 va vào vòng 1 và run treo/chạy thiếu **trong im
lặng**. Phase này mở thêm một khoá mới (`waitpoint.idempotency_key`), nên câu
hỏi *"hai vòng foreach có đụng nhau không"* phải được trả lời **bằng một phép
kiểm**, trước khi có mã dùng nó.

## Nguồn (tra trước, không tự suy)

- Activepieces `brain/knowledge/decisions/000015-…-waitpoint-barrier.md`
  (activepieces@`17e2ac0b`): *"Identity is path-keyed… a delay or approval
  **inside a loop** used to reuse one waitpoint row across every iteration, so
  iteration 2 found iteration 1's COMPLETED row … and skipped its pause
  entirely."* ⇒ ta lấy cùng hình dạng khoá, qua **cùng một hàm**
  (`danh_thuc.duong_thi_hanh`) mà `wakeup`/`node_run` đã dùng — ⛔ không dựng
  bộ sinh khoá thứ hai.
- Activepieces `#3798` *"Create Approval Link ⇒ Wait for Approval doesn't work
  when there's a step in between"* — cùng họ lỗi: định danh điểm chờ không mang
  đủ ngữ cảnh.
- Activepieces `#14808` *"Rejected webhook auth returns HTTP 200 with no run and
  no log"* ⇒ token sai ở đây phải là **401**, không phải một 200 im lặng.
- n8n `#17187` *"Scheduled tasks executing multiple times at once"* ⇒ khoá cron
  phải là **mốc lịch**, không phải thời điểm bắn.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from datetime import datetime, timezone

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


# ── ĐỐI CHỨNG: mối nguy có thật ──────────────────────────────────────────────

def test_doi_chung_khoa_tran_thi_hai_vong_foreach_TRUNG_NHAU():
    """⛔ Cách SAI (node_id trần) — đối chứng của cả tệp.

    Nếu phép này không còn chứng minh được va chạm thì mọi phép "khác nhau"
    phía dưới là xanh giả (`docs` — *"không đối chứng thì số 0 không phải phát
    hiện"*).
    """
    def khoa_tran(run_id, node_id, kind, *, vong=()):
        return f"wp:{run_id}:{node_id}:{kind}"

    a = khoa_tran("r1", "delay1", "DELAY", vong=(("f1", 0),))
    b = khoa_tran("r1", "delay1", "DELAY", vong=(("f1", 1),))
    assert a == b, "doi chung hong: cach sai phai TRUNG"


def test_hai_vong_foreach_KHONG_dung_nhau():
    from platform_core.workflow import khoa_idem

    a = khoa_idem.khoa_cho("r1", "delay1", "DELAY", vong=(("f1", 0),))
    b = khoa_idem.khoa_cho("r1", "delay1", "DELAY", vong=(("f1", 1),))
    assert a != b
    # …và cùng vòng ⇒ CÙNG khoá (điều kiện để `chay_delay` luỹ đẳng).
    assert a == khoa_idem.khoa_cho("r1", "delay1", "DELAY", vong=(("f1", 0),))


def test_vong_long_nhau_va_kind_khac_nhau_deu_tach():
    from platform_core.workflow import khoa_idem

    trong = khoa_idem.khoa_cho("r1", "x", "HUMAN", vong=(("f1", 2), ("f2", 0)))
    ngoai = khoa_idem.khoa_cho("r1", "x", "HUMAN", vong=(("f1", 2),))
    assert trong != ngoai
    assert (khoa_idem.khoa_cho("r1", "x", "HUMAN")
            != khoa_idem.khoa_cho("r1", "x", "WEBHOOK"))
    # Hai RUN khác nhau không bao giờ chia một khoá.
    assert khoa_idem.khoa_cho("r1", "x", "DELAY") != \
        khoa_idem.khoa_cho("r2", "x", "DELAY")


def test_khoa_khong_bao_gio_vuot_cot_120():
    """`waitpoint.idempotency_key` là `String(120)`: PostgreSQL NÉM ở ký tự 121,
    SQLite nuốt im lặng — nên trần phải được cưỡng chế ở hàm, không ở may mắn."""
    from platform_core.workflow import khoa_idem

    dai = khoa_idem.khoa_cho("r" * 36, "n" * 64, "CHILD_RUN",
                             vong=tuple((f"vong{i}", i) for i in range(20)))
    assert len(dai) <= khoa_idem.TRAN_KHOA == 120
    # ⛔ Cắt cụt là cách im lặng nhất để hai đường thành một khoá: đường dài
    #    phải được BĂM, và hai đường dài khác nhau vẫn phải khác khoá.
    dai2 = khoa_idem.khoa_cho("r" * 36, "m" * 64, "CHILD_RUN",
                              vong=tuple((f"vong{i}", i) for i in range(20)))
    assert dai != dai2


# ── Khoá khử trùng trigger (spec §8.1) ───────────────────────────────────────

def test_khoa_webhook_uu_tien_header_idempotency_key():
    from platform_core.workflow import khoa_idem

    a = khoa_idem.khoa_webhook("t1", idempotency_key="abc", than=b'{"x":1}',
                               luc=datetime(2026, 9, 24, 10, 0, 30))
    b = khoa_idem.khoa_webhook("t1", idempotency_key="abc", than=b'{"x":2}',
                               luc=datetime(2026, 9, 24, 10, 59, 59))
    assert a == b, "co header Idempotency-Key thi than va phut KHONG duoc dem"
    assert khoa_idem.khoa_webhook("t2", idempotency_key="abc") != a


def test_khoa_webhook_khong_header_thi_sha256_than_cong_PHUT():
    from platform_core.workflow import khoa_idem

    luc = datetime(2026, 9, 24, 10, 0, 30)
    a = khoa_idem.khoa_webhook("t1", than=b'{"x":1}', luc=luc)
    assert a == khoa_idem.khoa_webhook(
        "t1", than=b'{"x":1}', luc=datetime(2026, 9, 24, 10, 0, 59))
    assert a != khoa_idem.khoa_webhook("t1", than=b'{"x":2}', luc=luc)
    # Phút KHÁC ⇒ khoá khác: một webhook lặp lại sau 1 phút là một việc MỚI.
    assert a != khoa_idem.khoa_webhook(
        "t1", than=b'{"x":1}', luc=datetime(2026, 9, 24, 10, 1, 0))


def test_khoa_cron_la_MOC_LICH_khong_phai_luc_ban():
    """n8n `#17187`: khoá theo lúc bắn ⇒ một mốc lỡ bắn hai lần là hai run."""
    from platform_core.workflow import khoa_idem

    moc = datetime(2026, 9, 24, 7, 0, tzinfo=timezone.utc)
    assert khoa_idem.khoa_cron("t1", moc) == khoa_idem.khoa_cron("t1", moc)
    assert khoa_idem.khoa_cron("t1", moc).startswith("cron:t1:")
    assert khoa_idem.khoa_cron("t1", moc) != khoa_idem.khoa_cron("t2", moc)
    assert khoa_idem.khoa_cron("t1", moc) != khoa_idem.khoa_cron(
        "t1", datetime(2026, 9, 25, 7, 0, tzinfo=timezone.utc))


def test_khoa_event_va_poll_theo_id_ban_ghi():
    from platform_core.workflow import khoa_idem

    assert khoa_idem.khoa_event("t1", "e9").startswith("evt:t1:")
    assert khoa_idem.khoa_event("t1", "e9") != khoa_idem.khoa_event("t1", "e8")
    assert khoa_idem.khoa_poll("t1", "row7").startswith("poll:t1:")


# ── Cột mới trên mô hình (spec §5.7, §8.1) ───────────────────────────────────

def test_waitpoint_co_cot_han_va_che_do_het_han(db):
    from platform_core.models import Waitpoint

    wp = Waitpoint(run_id="r1", owner_id="u1", kind="HUMAN")
    db.add(wp)
    db.flush()
    assert wp.het_han_luc is None
    assert wp.che_do_het_han == "fail"


def test_trigger_co_cot_version_mode_con_tro_va_loi_lien_tiep(db):
    from platform_core.models import WorkflowTrigger

    t = WorkflowTrigger(workflow_id="w1", owner_id="u1", kind="MANUAL",
                        config={})
    db.add(t)
    db.flush()
    assert t.version_mode == "published"
    assert t.pinned_version_id == ""
    assert t.con_tro == {}
    assert t.last_fired_at is None
    assert t.loi_lien_tiep == 0


# ── Router `/hooks/*` ────────────────────────────────────────────────────────

@pytest.fixture()
def hook(tmp_path, monkeypatch):
    """App thật + CSDL sạch + một trigger WEBHOOK trên một workflow đã publish."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hooks.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from fastapi.testclient import TestClient

    from platform_core import credit
    from platform_core.workflow import dinh_nghia, trigger
    from server.app import create_app
    from tests.conftest import bao_dam_user

    s = next(dbmod.get_session())
    bao_dam_user(s, "u1")
    credit.nap(s, "u1", 10_000, note="test")
    w = dinh_nghia.tao_workflow(s, owner_id="u1", name="hookwf")
    dinh_nghia.luu_draft(s, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": [
            {"id": "s", "type": "core.set", "position": {"x": 0, "y": 0},
             "params": {"bien": {"a": "1"}}}], "edges": []}]})
    v = dinh_nghia.xuat_ban_draft(s, w.id, created_by="u1", cong_cu={})
    w.published_version_id = v.id
    t = trigger.tao(s, workflow_id=w.id, owner_id="u1", kind="WEBHOOK",
                    cau_hinh={"token_hash": trigger.bam_token("bi-mat")})
    s.commit()
    tid = t.id
    s.close()

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "hook-secret-v",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json")})
    with TestClient(app) as c:
        yield c, tid
    dbmod.reset_engine()


def test_hook_wf_token_sai_tra_401_KHONG_tao_run(hook):
    """Activepieces `#14808`: từ chối im lặng bằng 200 là một lỗi, không phải
    một lựa chọn bảo mật."""
    from platform_core.models import WorkflowRun
    import platform_core.db as dbmod

    c, tid = hook
    r = c.post(f"/hooks/wf/{tid}", json={"x": 1},
               headers={"X-LTT-Token": "sai"})
    assert r.status_code == 401, r.text
    s = next(dbmod.get_session())
    assert s.query(WorkflowRun).count() == 0
    s.close()


def test_hook_wf_token_dung_tra_202_va_run_id(hook):
    c, tid = hook
    r = c.post(f"/hooks/wf/{tid}", json={"x": 1},
               headers={"X-LTT-Token": "bi-mat"})
    assert r.status_code == 202, r.text
    assert r.json()["run_id"]


def test_hook_wf_webhook_TRUNG_khong_tao_run_thu_hai(hook):
    """Điều kiện ra P4: *"webhook trùng không tạo 2 run"*."""
    from platform_core.models import WorkflowRun
    import platform_core.db as dbmod

    c, tid = hook
    h = {"X-LTT-Token": "bi-mat", "Idempotency-Key": "k-1"}
    a = c.post(f"/hooks/wf/{tid}", json={"x": 1}, headers=h)
    b = c.post(f"/hooks/wf/{tid}", json={"x": 1}, headers=h)
    assert a.status_code == 202 and b.status_code == 202
    assert a.json()["run_id"] == b.json()["run_id"]
    s = next(dbmod.get_session())
    assert s.query(WorkflowRun).count() == 1
    s.close()


def test_hook_wf_than_qua_lon_tra_413(hook):
    c, tid = hook
    r = c.post(f"/hooks/wf/{tid}", content=b"x" * (1024 * 1024 + 1),
               headers={"X-LTT-Token": "bi-mat",
                        "Content-Type": "application/json"})
    assert r.status_code == 413, r.text


def test_hook_wf_trigger_khong_co_tra_404(hook):
    c, _tid = hook
    r = c.post("/hooks/wf/khong-co-that", json={},
               headers={"X-LTT-Token": "bi-mat"})
    assert r.status_code == 404


def test_hook_wf_trigger_TAT_tra_404(hook):
    import platform_core.db as dbmod
    from platform_core.models import WorkflowTrigger

    c, tid = hook
    s = next(dbmod.get_session())
    s.get(WorkflowTrigger, tid).enabled = False
    s.commit()
    s.close()
    r = c.post(f"/hooks/wf/{tid}", json={}, headers={"X-LTT-Token": "bi-mat"})
    assert r.status_code == 404
