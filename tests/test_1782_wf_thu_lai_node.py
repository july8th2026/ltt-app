"""Retry CẤP NODE — một lớp mỏng trên retry của `jobs.py`, không phải cơ chế thứ hai.

🔴 NỢ ĐÃ ĐO (plan wf-v2 §4 P3)

`platform_core/jobs.py` **đã có** đủ bốn mảnh: backoff mũ (`fail()`:
`base * 2**(n-1)`, chặn trên `_RETRY_MAX_S`), `max_attempts`, `dedupe_key`,
`reclaim_orphans`. ⛔ Dựng một bộ đếm/lịch thứ hai ở tầng workflow là dựng một
chỗ thứ hai để hai con số lệch nhau — và con số lệch ấy là **tiền** và **side
effect**.

Spec §5.6 nói đúng ranh giới: *"Job giữ nguyên retry của nó (`max_attempts`,
backoff mũ, reclaim). **Retry node** chỉ xảy ra khi job đã kết thúc ERROR:
`settings.retry = {max ≤ 5, backoff_s}`, mặc định `{max: 0}` (retry job đã đủ
cho lỗi tạm)."*

## Phép này KHÔNG phủ cái gì

Không phủ ca `reclaim_orphans` (worker chết giữa chừng) — đó vẫn hoàn toàn là
việc của `jobs.py` và node không nhìn thấy. Không phủ retry trong thân
`foreach` (Task 5 nối ngữ cảnh vòng lặp vào `danh_thuc.hen_node`).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import ast
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC
from tests.test_1717_wf_tao_run import wf  # noqa: F401


@pytest.fixture()
def run(db, wf, monkeypatch):
    from platform_core.workflow import cong_cu, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k")
    return r


def _dat_retry(db, run, nid, chinh_sach):
    """Ghi `settings.retry` vào đồ thị ĐÃ publish của run (bản ghim version)."""
    from platform_core.models import WorkflowVersion
    v = db.get(WorkflowVersion, run.version_id)
    g = dict(v.graph)
    g["nodes"] = [dict(n) for n in g["nodes"]]
    node = next(n for n in g["nodes"] if n["id"] == nid)
    node["settings"] = dict(node.get("settings") or {})
    if chinh_sach is not None:
        node["settings"]["retry"] = chinh_sach
    v.graph = g
    db.flush()
    return node


def _node_cua(db, run, nid):
    from platform_core.models import WorkflowVersion
    g = db.get(WorkflowVersion, run.version_id).graph
    return next(n for n in g["nodes"] if n["id"] == nid)


def _hong_mot_luot(db, run, nid):
    """Nộp job cho node rồi cho job kết thúc ERROR (retry của JOB đã cạn)."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi
    job = db.get(Job, cau_noi.nop_job(db, run, _node_cua(db, run, nid),
                                      cong_cu=CC))
    jobs.fail(db, job, "provider hong", retry=False)
    return cau_noi.ap_ket_qua(db, run, nid, cong_cu=CC)


def _bay_gio():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── ĐỐI CHỨNG: mặc định `{max: 0}` ⇒ hành vi CŨ không đổi ────────────────────

def test_doi_chung_khong_khai_retry_thi_FAILED_ngay(db, run):
    """Nếu phép này đỏ thì lớp mới đang thử lại những node không xin thử lại."""
    from platform_core.workflow import may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert _hong_mot_luot(db, run, "a") == "FAILED"
    assert mtt.trang_thai_node(db, run.id, "a") == "FAILED"
    assert run.actual_cost == 0


# ── LUẬT MỚI ────────────────────────────────────────────────────────────────

def test_con_luot_thi_vao_RETRY_SCHEDULED_va_co_wakeup(db, run):
    from platform_core.models import Wakeup
    from platform_core.workflow import may_trang_thai as mtt, thi_hanh
    _dat_retry(db, run, "a", {"max": 2})
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert _hong_mot_luot(db, run, "a") == "RETRY_SCHEDULED"
    assert mtt.trang_thai_node(db, run.id, "a") == "RETRY_SCHEDULED"
    # Lượt thử kế đã được ghi vào ảnh chụp — `nop_job` đọc đúng con số này.
    assert thi_hanh.anh_chup_hien_tai(db, run.id, "a").attempt_number == 2
    assert db.query(Wakeup).filter_by(run_id=run.id, kind="retry").count() == 1


def test_khoa_wakeup_retry_theo_duong_thi_hanh(db, run):
    """Khoá của wakeup retry phải đi qua Task 1, không phải node_id trần."""
    from platform_core.models import Wakeup
    from platform_core.workflow import danh_thuc, may_trang_thai as mtt
    _dat_retry(db, run, "a", {"max": 1})
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    _hong_mot_luot(db, run, "a")
    w = db.query(Wakeup).filter_by(run_id=run.id, kind="retry").one()
    assert w.node_run_id == danh_thuc.duong_thi_hanh("a")


def test_den_han_thi_ve_READY_va_nop_lai_voi_luot_moi(db, run):
    from platform_core.models import Job
    from platform_core.workflow import dong_co, may_trang_thai as mtt, thu_lai
    _dat_retry(db, run, "a", {"max": 2, "backoff_s": 1})
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    _hong_mot_luot(db, run, "a")
    # Chưa tới hạn ⇒ đứng yên. (Đối chứng cho phép kiểm ngay dưới.)
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert mtt.trang_thai_node(db, run.id, "a") == "RETRY_SCHEDULED"
    # Tới hạn ⇒ READY rồi được nộp lại trong CÙNG lượt động cơ.
    thu_lai.den_han(db, run.id, [_node_cua(db, run, "a")],
                    bay_gio=_bay_gio() + timedelta(hours=1))
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"
    moi = db.query(Job).filter_by(plan_id=run.id, job_type="ltt_llm.chat").all()
    assert len(moi) == 2


def test_het_luot_thi_FAILED(db, run):
    from platform_core.workflow import dong_co, may_trang_thai as mtt, thu_lai
    _dat_retry(db, run, "a", {"max": 1, "backoff_s": 1})
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert _hong_mot_luot(db, run, "a") == "RETRY_SCHEDULED"
    thu_lai.den_han(db, run.id, [_node_cua(db, run, "a")],
                    bay_gio=_bay_gio() + timedelta(hours=1))
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert _hong_mot_luot(db, run, "a") == "FAILED"     # lượt 2 là lượt cuối
    assert mtt.trang_thai_node(db, run.id, "a") == "FAILED"
    assert run.actual_cost == 0                          # lượt hỏng không thu tiền


def test_mo_ho_irreversible_KHONG_BAO_GIO_tu_thu_lai(db, run):
    """§5.6: `irreversible` + kết quả mơ hồ ⇒ `ABANDONED`, *không bao giờ tự thử*.

    ⛔ `settings.retry` không được phép thắng luật này — provider **có thể đã
       nhận**, nên một lượt thử lại là một side effect thứ hai không đảo được.
    """
    from dataclasses import replace
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt

    _dat_retry(db, run, "a", {"max": 5})
    cc = {"text.chat": replace(CC["text.chat"], side_effect="irreversible")}
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node_cua(db, run, "a"),
                                      cong_cu=cc))
    job.provider_state = jobs.PROVIDER_AMBIGUOUS
    jobs.fail(db, job, "mo ho", retry=False)
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=cc) == "ABANDONED"


def test_bi_huy_khong_thu_lai(db, run):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    _dat_retry(db, run, "a", {"max": 5})
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node_cua(db, run, "a"),
                                      cong_cu=CC))
    jobs.cancel(db, job)
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "CANCELLED"


# ── Chính sách: đọc, và TỪ CHỐI rác ─────────────────────────────────────────

@pytest.mark.parametrize("xau", [{"max": 6}, {"max": -1}, {"max": "hai"},
                                 {"max": 1, "backoff_s": 0}, "nhieu", 3])
def test_chinh_sach_rac_bi_tu_choi(xau):
    from platform_core.workflow.thu_lai import LoiChinhSach, doc_chinh_sach
    with pytest.raises(LoiChinhSach):
        doc_chinh_sach({"id": "n", "settings": {"retry": xau}})


def test_mac_dinh_la_khong_thu_lai():
    from platform_core.workflow.thu_lai import doc_chinh_sach
    assert doc_chinh_sach({"id": "n", "settings": {}}).so_lan == 0
    assert doc_chinh_sach({"id": "n"}).so_lan == 0


# ── BÁNH CÓC: ⛔ không dựng cơ chế thứ hai ───────────────────────────────────

def test_banh_coc_thu_lai_khong_tu_tinh_backoff():
    """`thu_lai.py` phải GỌI `jobs.gian_cach_retry`, không tự viết `2 ** n`.

    ⭐ Bánh cóc này **cắn thật**: đổi lời gọi trong `thu_lai.py` thành một phép
       `base * 2 ** (lan - 1)` viết tay là đủ để nó đỏ (đã tiêm thử — xem báo
       cáo Task 3).

    ⛔ Hai công thức backoff cho cùng một ý nghĩa là hai con số sẽ trôi khỏi
       nhau, và không ai để ý vì cả hai đều "hợp lý".
    """
    nguon = pathlib.Path("platform_core/workflow/thu_lai.py").read_text(
        encoding="utf-8")
    cay = ast.parse(nguon)
    luy_thua = [n for n in ast.walk(cay)
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow)]
    assert not luy_thua, "thu_lai.py tu tinh backoff mu - phai goi jobs.py"
    goi = {ast.unparse(n.func) for n in ast.walk(cay) if isinstance(n, ast.Call)}
    assert "jobs.gian_cach_retry" in goi, goi
    # Đối chứng: đường dẫn sai ⇒ tập rỗng ⇒ xanh giả. Neo vào nội dung thật.
    assert len(nguon) > 500 and "def hen" in nguon
