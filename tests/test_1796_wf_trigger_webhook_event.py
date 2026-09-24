"""`trigger.webhook` · `trigger.event` — khử trùng và hạn mức (spec §8.1, §8.3, §8.4).

## Điều kiện ra của P4 mà tệp này phủ

*"webhook trùng không tạo 2 run"* — đo ở **hai** tầng, vì chúng hỏng khác nhau:

  - tầng **khoá** (`test_1790`): cùng `Idempotency-Key` ⇒ cùng chuỗi;
  - tầng **CSDL** (ở đây): hai request **song song** cùng khoá ⇒ chỉ mục bộ
    phận `ux_workflow_run_idem` là thứ phân xử, không phải một câu `SELECT`
    cẩn thận ở tầng trên.

## Nguồn

- `activepieces#14808` — *"Rejected webhook auth returns HTTP 200 with no run
  and no log"*: quá hạn mức cũng phải **nói ra** (429), không im lặng bỏ.
- Spec §8.4: nguồn sự kiện trong phạm vi **chỉ** `workflow.run.finished`.
  *"Sự kiện của job ngoài workflow **không** làm: nó buộc `jobs.py` ghi vào
  bảng của workflow cho mọi job, phá luật §3.1-3."*

## ⛔ Tệp này KHÔNG trả lời

Không đo hai request **thật sự** song song (một phiên SQLite, một luồng). Nó
đo rằng **đường** khử trùng đi qua ràng buộc CSDL — cửa còn lại là `test_951`
(`tao_run` bắt `IntegrityError` ở `flush()`).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from datetime import datetime, timedelta, timezone

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def wf(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: {})
    credit.nap(db, "u1", 1_000_000, note="test")
    dem = {"n": 0}

    def _lam():
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"e{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": [
                {"id": "s", "type": "core.set", "position": {"x": 0, "y": 0},
                 "params": {"bien": {"a": "1"}}}], "edges": []}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu={})
        w.published_version_id = v.id
        db.flush()
        return w
    return _lam


# ── Hạn mức webhook (§7.3) ─────────────────────────────────────────────────

def test_han_muc_dem_theo_TUNG_TRIGGER_khong_theo_workflow(db, wf):
    from platform_core.workflow import han_muc, khoa_idem, tao_run, trigger

    w = wf()
    a = trigger.tao(db, workflow_id=w.id, owner_id="u1", kind="WEBHOOK",
                    cau_hinh={"token_hash": trigger.bam_token("x")})
    b = trigger.tao(db, workflow_id=w.id, owner_id="u1", kind="WEBHOOK",
                    cau_hinh={"token_hash": trigger.bam_token("y")})
    for i in range(5):
        tao_run.tao_run(db, workflow=w, owner_id="u1", trigger_kind="webhook",
                        idempotency_key=khoa_idem.khoa_webhook(
                            a.id, idempotency_key=f"k{i}"))
    db.flush()
    assert han_muc.dem_webhook_gan_day(db, a) == 5
    # ĐỐI CHỨNG: trigger kia trên CÙNG workflow vẫn là 0 — hạn mức là của
    # TỪNG trigger, không của workflow.
    assert han_muc.dem_webhook_gan_day(db, b) == 0


def test_han_muc_chi_dem_CUA_SO_MOT_PHUT(db, wf):
    from platform_core.models import WorkflowRun
    from platform_core.workflow import han_muc, khoa_idem, tao_run, trigger

    w = wf()
    t = trigger.tao(db, workflow_id=w.id, owner_id="u1", kind="WEBHOOK",
                    cau_hinh={"token_hash": trigger.bam_token("x")})
    for i in range(3):
        r = tao_run.tao_run(db, workflow=w, owner_id="u1",
                            trigger_kind="webhook",
                            idempotency_key=khoa_idem.khoa_webhook(
                                t.id, idempotency_key=f"cu{i}"))[0]
        r.created_at = _bay_gio() - timedelta(seconds=120)
    db.flush()
    assert han_muc.dem_webhook_gan_day(db, t) == 0, \
        "run cua 2 phut truoc khong duoc tinh vao han muc phut nay"
    assert db.query(WorkflowRun).count() == 3


def test_vuot_han_muc_khi_DU_so(db, wf, monkeypatch):
    from platform_core.workflow import han_muc, khoa_idem, tao_run, trigger

    monkeypatch.setattr(trigger, "WEBHOOK_MOI_PHUT_MOI_TRIGGER", 3)
    w = wf()
    t = trigger.tao(db, workflow_id=w.id, owner_id="u1", kind="WEBHOOK",
                    cau_hinh={"token_hash": trigger.bam_token("x")})
    assert han_muc.vuot_han_webhook(db, t) is False
    for i in range(3):
        tao_run.tao_run(db, workflow=w, owner_id="u1", trigger_kind="webhook",
                        idempotency_key=khoa_idem.khoa_webhook(
                            t.id, idempotency_key=f"k{i}"))
    db.flush()
    assert han_muc.vuot_han_webhook(db, t) is True


def test_hook_wf_tra_429_khi_qua_han_muc(tmp_path, monkeypatch):
    """⛔ 429, không phải im lặng bỏ (activepieces#14808)."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hm.db').as_posix()}")
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

    monkeypatch.setattr(trigger, "WEBHOOK_MOI_PHUT_MOI_TRIGGER", 2)
    s = next(dbmod.get_session())
    bao_dam_user(s, "u1")
    credit.nap(s, "u1", 100_000, note="t")
    w = dinh_nghia.tao_workflow(s, owner_id="u1", name="hm")
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
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "hm-secret-vvv",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json")})
    with TestClient(app) as c:
        ma = [c.post(f"/hooks/wf/{tid}", json={"i": i},
                     headers={"X-LTT-Token": "bi-mat",
                              "Idempotency-Key": f"k{i}"}).status_code
              for i in range(4)]
    dbmod.reset_engine()
    assert ma[:2] == [202, 202]
    assert 429 in ma[2:], ma


# ── `trigger.event` (§8.4) ─────────────────────────────────────────────────

def _trigger_event(db, w, **cfg):
    from platform_core.workflow import trigger
    return trigger.tao(db, workflow_id=w.id, owner_id="u1", kind="EVENT",
                       cau_hinh=cfg)


def test_event_tao_run_khi_mot_workflow_KHAC_ket_thuc(db, wf):
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger, su_kien, tao_run

    dich = wf()
    nguon = wf()
    t = _trigger_event(db, dich, loc="event.status == 'SUCCEEDED'")
    r_nguon = tao_run.tao_run(db, workflow=nguon, owner_id="u1",
                              trigger_kind="manual", idempotency_key="n1")[0]
    su_kien.ghi(db, r_nguon.id, "WorkflowCompleted",
                du_lieu={"status": "SUCCEEDED"})
    db.flush()

    kq = ban_trigger.ban_su_kien(db)
    assert kq["da_ban"] == 1
    assert db.query(WorkflowRun).filter_by(
        workflow_id=dich.id, trigger_kind="event").count() == 1
    assert t.con_tro.get("id")


def test_event_BO_LOC_that_su_loc(db, wf):
    """ĐỐI CHỨNG: không có vế này thì một bộ lọc *luôn đúng* cũng xanh."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger, su_kien, tao_run

    dich = wf()
    nguon = wf()
    _trigger_event(db, dich, loc="event.status == 'SUCCEEDED'")
    r = tao_run.tao_run(db, workflow=nguon, owner_id="u1",
                        trigger_kind="manual", idempotency_key="n2")[0]
    su_kien.ghi(db, r.id, "WorkflowFailed", du_lieu={"status": "FAILED"})
    db.flush()
    assert ban_trigger.ban_su_kien(db)["da_ban"] == 0
    assert db.query(WorkflowRun).filter_by(trigger_kind="event").count() == 0


def test_event_QUET_LAI_khong_tao_run_thu_hai(db, wf):
    """Hai chốt cùng lúc: con trỏ `(created_at, id)` **và** khoá
    `evt:<tid>:<event_id>`. Xoá con trỏ đi thì khoá vẫn phải giữ."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger, su_kien, tao_run

    dich = wf()
    nguon = wf()
    t = _trigger_event(db, dich)
    r = tao_run.tao_run(db, workflow=nguon, owner_id="u1",
                        trigger_kind="manual", idempotency_key="n3")[0]
    su_kien.ghi(db, r.id, "WorkflowCompleted", du_lieu={"status": "SUCCEEDED"})
    db.flush()
    ban_trigger.ban_su_kien(db)
    assert ban_trigger.ban_su_kien(db)["da_ban"] == 0      # con trỏ chặn

    t.con_tro = {}                                          # xoá con trỏ
    db.flush()
    ban_trigger.ban_su_kien(db)
    assert db.query(WorkflowRun).filter_by(
        trigger_kind="event").count() == 1, "khoa khu trung phai chan lan hai"


def test_event_KHONG_nghe_su_kien_cua_CHINH_workflow_minh(db, wf):
    """⛔ Một workflow nghe chính nó kết thúc là một vòng vô hạn có tiền
    thật: mỗi run sinh một sự kiện, sự kiện sinh một run."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger, su_kien, tao_run

    w = wf()
    _trigger_event(db, w)
    r = tao_run.tao_run(db, workflow=w, owner_id="u1",
                        trigger_kind="manual", idempotency_key="tu1")[0]
    su_kien.ghi(db, r.id, "WorkflowCompleted", du_lieu={"status": "SUCCEEDED"})
    db.flush()
    assert ban_trigger.ban_su_kien(db)["da_ban"] == 0
    assert db.query(WorkflowRun).filter_by(trigger_kind="event").count() == 0


def test_event_chi_nghe_ba_loai_KET_THUC_RUN(db, wf):
    """Spec §8.4: nguồn sự kiện trong phạm vi **chỉ** `workflow.run.finished`."""
    from platform_core.workflow import ban_trigger, su_kien, tao_run

    dich = wf()
    nguon = wf()
    _trigger_event(db, dich)
    r = tao_run.tao_run(db, workflow=nguon, owner_id="u1",
                        trigger_kind="manual", idempotency_key="n4")[0]
    for loai in ("WorkflowStarted", "TriggerReceived", "WaitpointOpened"):
        su_kien.ghi(db, r.id, loai, du_lieu={})
    db.flush()
    assert ban_trigger.ban_su_kien(db)["da_ban"] == 0


def test_event_con_tro_di_bang_KEYSET_khong_bo_sot(db, wf):
    from platform_core.workflow import ban_trigger, su_kien, tao_run

    dich = wf()
    nguon = wf()
    t = _trigger_event(db, dich)
    # ⚠️ Đánh dấu run NGUỒN đã kết thúc: `tao_run.MAX_RUN_DONG_THOI` là 5, và
    #    phép này không nói gì về hạn mức đó — để nó chen vào là để một phép
    #    kiểm trả lời một câu hỏi khác câu nó hỏi.
    for i in range(4):
        r = tao_run.tao_run(db, workflow=nguon, owner_id="u1",
                            trigger_kind="manual", idempotency_key=f"m{i}")[0]
        su_kien.ghi(db, r.id, "WorkflowCompleted",
                    du_lieu={"status": "SUCCEEDED"})
        r.status = "SUCCEEDED"
    db.flush()
    tong = 0
    for _ in range(10):
        n = ban_trigger.ban_su_kien(db, gioi_han=2)["da_ban"]
        tong += n
        if not n:
            break
    # 4 sự kiện, mỗi lượt quét tối đa 2 ⇒ phải cần nhiều lượt, và KHÔNG được
    # bỏ sót dòng nào ở ranh giới trang.
    assert tong == 4, (tong, t.con_tro)


def test_event_bo_loc_HONG_bi_tu_choi_LUC_TAO(db, wf):
    from platform_core.workflow import trigger

    w = wf()
    with pytest.raises(ValueError):
        _trigger_event(db, w, loc="event.(((")
    # …và một bộ lọc HỢP LỆ vẫn qua được.
    assert trigger.tao(db, workflow_id=w.id, owner_id="u1", kind="EVENT",
                       cau_hinh={"loc": "event.status == 'SUCCEEDED'"})
