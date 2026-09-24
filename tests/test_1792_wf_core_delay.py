"""`core.delay` BỀN — waitpoint + wakeup, ⛔ không `sleep`, không giữ worker.

Spec §5.7: *"`core.delay` **không bao giờ** `sleep`: ghi waitpoint + wakeup rồi
kết thúc vòng. Delay ≤ 60 s vẫn đi cùng đường (không có đường tắt trong bộ nhớ
— một đường duy nhất để kiểm)."*

Điều kiện ra của P4 mà tệp này phủ:

  - **không worker nào bị giữ trong lúc chờ** — node đi `WAITING`, `xu_ly_run`
    trả về ngay, và **không một hàng `jobs` nào** được nộp cho nó;
  - **khởi động lại worker giữa chừng thì run vẫn xong** — resume chạy qua
    `dong_co.mot_vong(db_factory)`, tức những **phiên CSDL MỚI**. Mọi thứ cần
    nhớ giữa hai lượt phải nằm trong bảng; không có gì trong bộ nhớ sống sót
    qua một `db_factory()`.

🔴 VÀ CÂU HỎI BẮT BUỘC CỦA PHASE: **hai vòng `foreach` có đụng nhau không?**

Activepieces `000015` (activepieces@`17e2ac0b`): *"a delay or approval inside a
loop used to reuse one waitpoint row across every iteration, so iteration 2
found iteration 1's COMPLETED row … and skipped its pause entirely."* Nên
`test_delay_TRONG_foreach_moi_vong_mot_diem_cho` là phép quan trọng nhất ở đây,
và nó có đối chứng: với khoá trần, vòng 2 sẽ thấy điểm chờ **đã mở** của vòng 1.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from datetime import datetime, timedelta, timezone

import pytest

from platform_core.workflow.cong_cu import CongCu
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 1,
                          returns={"text": "text"})}


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str) -> dict:
    return {"id": f"{a}-{b}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": "DATA",
            "condition": ""}


def _db_factory():
    from platform_core.db import get_session
    return next(get_session())


@pytest.fixture()
def lam(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 100_000, note="test")
    dem = {"n": 0}

    def _lam(nodes, edges):
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"d{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                     "edges": edges}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
        w.published_version_id = v.id
        db.flush()
        run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                 trigger_kind="manual",
                                 idempotency_key=f"dk{dem['n']}")
        db.commit()
        return run
    return _lam


def _tt(db, run, nid, vong=()):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid, vong)


def _di_chuyen_dong_ho(monkeypatch, giay: int) -> None:
    """Đẩy "bây giờ" của MỌI mô-đun workflow lên `giay` giây.

    ⚠️ Phải vá từng mô-đun vì mỗi mô-đun tự định nghĩa `_bay_gio()` (quy ước
       của kho này, 8+ chỗ). Vá `datetime` toàn cục sẽ đụng cả SQLAlchemy.
    """
    from platform_core.workflow import (danh_thuc, dong_co, han_cho, noi_lai)
    from platform_core.workflow.nut_loi import cho

    lech = timedelta(seconds=giay)

    def _moi():
        return datetime.now(timezone.utc).replace(tzinfo=None) + lech

    for mod in (cho, danh_thuc, dong_co, han_cho, noi_lai):
        monkeypatch.setattr(mod, "_bay_gio", _moi)


# ── Node đi WAITING, KHÔNG nộp job nào ──────────────────────────────────────

def test_delay_di_WAITING_va_KHONG_NOP_JOB_NAO(db, lam):
    """*"Không worker nào bị giữ trong lúc chờ"* — đo bằng bảng `jobs`."""
    from platform_core.job_scheduler import ORIGIN_WORKFLOW
    from platform_core.models import Job
    from platform_core.workflow import dong_co, tao_run

    run = lam([_core("d", "delay", duration_s=120)], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "d") == "WAITING"
    assert run.status != "SUCCEEDED"
    assert db.query(Job).filter(
        Job.plan_id == run.id, Job.origin == ORIGIN_WORKFLOW,
        Job.job_type != tao_run.DONG_CO_JOB).count() == 0, \
        "core.delay khong duoc sinh mot bút toán nào"


def test_delay_ghi_DUNG_MOT_waitpoint_va_MOT_wakeup_dung_han(db, lam):
    from platform_core.models import Waitpoint, Wakeup
    from platform_core.workflow import dong_co

    run = lam([_core("d", "delay", duration_s=120)], [])
    truoc = datetime.now(timezone.utc).replace(tzinfo=None)
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)

    wps = db.query(Waitpoint).filter_by(run_id=run.id, kind="DELAY").all()
    assert len(wps) == 1
    assert timedelta(seconds=115) <= (wps[0].due_at - truoc) \
        <= timedelta(seconds=125)
    w = [x for x in db.query(Wakeup).filter_by(run_id=run.id).all()
         if x.node_run_id == "d"]
    assert len(w) == 1 and w[0].due_at == wps[0].due_at


def test_goi_lai_TRUOC_HAN_khong_mo_them_diem_cho(db, lam):
    """Luỹ đẳng: động cơ chạy nhiều lượt trong lúc chờ là chuyện bình thường."""
    from platform_core.models import Waitpoint
    from platform_core.workflow import cho_doi, dong_co

    run = lam([_core("d", "delay", duration_s=120)], [])
    for _ in range(4):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert db.query(Waitpoint).filter_by(run_id=run.id, kind="DELAY").count() == 1
    assert _tt(db, run, "d") == "WAITING"
    wp = db.query(Waitpoint).filter_by(run_id=run.id).first()
    assert cho_doi.node_dang_bi_chan(db, wp.id) == ["d"]


# ── Tới hạn ⇒ đi tiếp, và đi tiếp QUA PHIÊN MỚI (restart worker) ────────────

def test_toi_han_thi_chay_tiep_va_NHANH_SAU_CHAY(db, lam, monkeypatch):
    from platform_core.workflow import dong_co

    run = lam([_core("d", "delay", duration_s=60),
               _core("s", "set", bien={"xong": "1"})],
              [_canh("d", "s")])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "d") == "WAITING" and _tt(db, run, "s") == "PENDING"

    _di_chuyen_dong_ho(monkeypatch, 61)
    assert dong_co.xu_ly_run(db, run.id, cong_cu=CC) == "SUCCEEDED"
    assert _tt(db, run, "d") == "SUCCEEDED" and _tt(db, run, "s") == "SUCCEEDED"


def test_KHOI_DONG_LAI_giua_chung_run_van_xong(db, lam, monkeypatch):
    """Resume đi qua `mot_vong(db_factory)` — **phiên CSDL MỚI** mỗi lượt.

    ⭐ Đây là phép chứng minh *"khởi động lại worker giữa chừng thì run vẫn
       xong"*: không một byte trạng thái nào trong bộ nhớ của phiên cũ sống sót
       qua `db_factory()`, nên nếu run đi tiếp được thì mọi thứ cần nhớ đã nằm
       trong bảng.
    """
    from platform_core.models import WorkflowRun
    from platform_core.workflow import cong_cu, dong_co
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)

    run = lam([_core("d", "delay", duration_s=60),
               _core("s", "set", bien={"xong": "1"})],
              [_canh("d", "s")])
    db.commit()
    dong_co.mot_vong(_db_factory)
    db.expire_all()
    assert db.get(WorkflowRun, run.id).status == "WAITING"

    _di_chuyen_dong_ho(monkeypatch, 61)
    for _ in range(4):
        dong_co.mot_vong(_db_factory)
    db.expire_all()
    assert db.get(WorkflowRun, run.id).status == "SUCCEEDED"


# ── 🔴 Hai vòng `foreach` KHÔNG đụng nhau ───────────────────────────────────

def test_delay_TRONG_foreach_moi_vong_mot_diem_cho(db, lam, monkeypatch):
    """⭐ Phép quan trọng nhất của tệp (activepieces `000015`).

    Hai vòng, mỗi vòng một `core.delay` — phải ra **hai** waitpoint và **hai**
    wakeup, khoá theo `f:0/d` và `f:1/d`.

    ĐỐI CHỨNG bên dưới: nếu khoá là `node_id` trần thì cả hai vòng cùng một
    chuỗi, và vòng 2 sẽ thấy điểm chờ **đã mở** của vòng 1.
    """
    from platform_core.models import Waitpoint, Wakeup
    from platform_core.workflow import dong_co, khoa_idem

    run = lam([_core("f", "foreach", items="[1, 2]", max_items=5,
                     parallelism=2),
               _core("d", "delay", duration_s=60),
               _core("fe", "foreach_end", foreach="f")],
              [_canh("f", "d"), _canh("d", "fe")])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)

    wps = db.query(Waitpoint).filter_by(run_id=run.id, kind="DELAY").all()
    assert len(wps) == 2, [w.idempotency_key for w in wps]
    assert {w.idempotency_key for w in wps} == {
        khoa_idem.khoa_cho(run.id, "d", "DELAY", vong=(("f", 0),)),
        khoa_idem.khoa_cho(run.id, "d", "DELAY", vong=(("f", 1),))}

    duong = {w.node_run_id for w in db.query(Wakeup).filter_by(run_id=run.id)}
    assert {"f:0/d", "f:1/d"} <= duong, duong

    # ĐỐI CHỨNG: khoá trần cho MỘT chuỗi cho cả hai vòng.
    assert (khoa_idem.khoa_cho(run.id, "d", "DELAY")
            not in {w.idempotency_key for w in wps})

    # …và cả hai vòng thật sự chờ rồi thật sự xong.
    assert _tt(db, run, "d", (("f", 0),)) == "WAITING"
    assert _tt(db, run, "d", (("f", 1),)) == "WAITING"
    _di_chuyen_dong_ho(monkeypatch, 61)
    for _ in range(6):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _tt(db, run, "d", (("f", 0),)) == "SUCCEEDED"
    assert _tt(db, run, "d", (("f", 1),)) == "SUCCEEDED"
    assert run.status == "SUCCEEDED"


# ── Tham số ─────────────────────────────────────────────────────────────────

def test_delay_nhan_bieu_thuc_until(db, lam):
    from platform_core.models import Waitpoint
    from platform_core.workflow import dong_co

    run = lam([_core("d", "delay", until="'2099-01-01T00:00:00'")], [])
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    wp = db.query(Waitpoint).filter_by(run_id=run.id, kind="DELAY").one()
    assert wp.due_at.year == 2099


def test_delay_khong_co_tham_so_nao_bi_TU_CHOI_LUC_PUBLISH(db, lam):
    """⛔ Chặn ở publish, không lúc chạy: lúc chạy là lúc đang tiêu tiền."""
    from platform_core.workflow import bien_dich

    with pytest.raises(bien_dich.LoiBienDich) as e:
        lam([_core("d", "delay")], [])
    assert e.value.ma in ("thieu_tham_so", "dau_vao_sai"), e.value.ma
