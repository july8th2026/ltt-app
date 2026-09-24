"""Node điều khiển `core.if` · `core.switch` · `core.stop` (spec §5.4, §5.1).

🔴 VÌ SAO CHÚNG KHÔNG ĐƯỢC SINH JOB

`dieu_khien.py` đã ghi con số: *"hôm nay mỗi bước đều đi qua hàng đợi job, nên
một node `IF` cũng sinh một job — và **một job là một bút toán**. Rẽ nhánh tạo
một dòng trong sổ tiền, dù nó chỉ so sánh hai giá trị."* Nên phép kiểm dưới đây
đo **hai** thứ cho mỗi node điều khiển: nó rẽ đúng nhánh, **và** nó không để lại
một job hay một đồng nào.

## Luật nhánh (spec §5.4) — không phải điều kiện trên cạnh

    "Node `core.if` xuất nhánh `true`/`false`; `core.switch` xuất nhánh theo tên
     khai. Cạnh CONTROL mang `condition = "<tên nhánh>"`; chỉ cạnh khớp nhánh
     được kích hoạt."

⇒ Biểu thức nằm **trong node**, cạnh chỉ mang **tên nhánh**. Một nơi viết biểu
  thức, một nơi hiện trên Canvas.

## Phép này KHÔNG phủ cái gì

Không phủ `foreach`/`join` (Task 5), không phủ `set`/`transform`/`filter`/
`aggregate`/`output` (Task 6), không phủ `call_workflow` (Task 7). Không chạy
trên PostgreSQL thật (Task 8).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import pytest

from platform_core.workflow.cong_cu import CongCu
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3,
                          returns={"text": "text"})}


def _app(nid: str, **params) -> dict:
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": "text.chat", "params": params}}


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    return {"id": f"{a}-{b}-{condition}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": kind,
            "condition": condition}


@pytest.fixture()
def lam(db, monkeypatch):
    """Dựng → publish → tạo run cho một đồ thị bất kỳ; trả về hàm."""
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 1000, note="test")
    dem = {"n": 0}

    def _lam(nodes, edges):
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"t{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3,
            "pages": [{"id": "p1", "nodes": nodes, "edges": edges}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
        w.published_version_id = v.id
        db.flush()
        run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                 trigger_kind="manual",
                                 idempotency_key=f"k{dem['n']}")
        return run
    return _lam


def _tt(db, run, nid):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid)


def _job_cua(db, run, nid):
    from platform_core.models import Job
    from platform_core.workflow import thi_hanh
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid)
    return db.get(Job, anh.job_id) if anh and anh.job_id else None


def _chay(db, run):
    from platform_core.workflow import dong_co
    return dong_co.xu_ly_run(db, run.id, cong_cu=CC)


# ── ĐỐI CHỨNG ───────────────────────────────────────────────────────────────

def test_doi_chung_do_thi_app_khong_doi(db, lam):
    """Đồ thị không có node lõi phải chạy y như trước Task 4."""
    run = lam([_app("a"), _app("b", q="$a.text")], [_canh("a", "b")])
    assert _chay(db, run) == "RUNNING"
    assert _tt(db, run, "a") == "QUEUED" and _tt(db, run, "b") == "PENDING"


# ── core.if ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dieu_kien,chay,bo", [("1 < 2", "t", "f"),
                                               ("1 > 2", "f", "t")])
def test_if_chi_kich_hoat_nhanh_dung(db, lam, dieu_kien, chay, bo):
    run = lam([_core("i", "if", dieu_kien=dieu_kien), _app("t"), _app("f")],
              [_canh("i", "t", kind="CONTROL", condition="true"),
               _canh("i", "f", kind="CONTROL", condition="false")])
    _chay(db, run)
    assert _tt(db, run, "i") == "SUCCEEDED"
    assert _tt(db, run, chay) == "QUEUED"
    assert _tt(db, run, bo) == "SKIPPED"


def test_if_khong_sinh_job_va_khong_but_toan(db, lam):
    """⛔ Một job là một bút toán. Rẽ nhánh không được tạo dòng nào trong sổ."""
    from platform_core.models import Job
    run = lam([_core("i", "if", dieu_kien="true")],
              [])
    truoc = db.query(Job).count()
    _chay(db, run)
    assert _tt(db, run, "i") == "SUCCEEDED"
    assert db.query(Job).count() == truoc
    assert _job_cua(db, run, "i") is None
    assert run.actual_cost == 0


def test_if_doc_duoc_output_node_to_tien(db, lam):
    from platform_core import jobs
    run = lam([_app("a"), _core("i", "if",
                                dieu_kien='nodes.a.output.text == "co"'),
               _app("t")],
              [_canh("a", "i"),
               _canh("i", "t", kind="CONTROL", condition="true")])
    _chay(db, run)
    jobs.complete(db, _job_cua(db, run, "a"), {"text": "co"})
    _chay(db, run)
    assert _tt(db, run, "i") == "SUCCEEDED" and _tt(db, run, "t") == "QUEUED"


def test_if_bieu_thuc_loi_thi_node_FAILED_co_ma(db, lam):
    from platform_core.workflow import thi_hanh
    run = lam([_core("i", "if", dieu_kien="khong_co_ham_nay(1)"), _app("t")],
              [_canh("i", "t", kind="CONTROL", condition="true")])
    _chay(db, run)
    assert _tt(db, run, "i") == "FAILED"
    assert "bieu_thuc_loi" in thi_hanh.anh_chup_hien_tai(db, run.id, "i").error
    assert _tt(db, run, "t") == "SKIPPED"


# ── core.switch ─────────────────────────────────────────────────────────────

def test_switch_khop_ten_nhanh(db, lam):
    run = lam([_core("s", "switch", bieu_thuc='"b"', nhanh=["a", "b"]),
               _app("na"), _app("nb")],
              [_canh("s", "na", kind="CONTROL", condition="a"),
               _canh("s", "nb", kind="CONTROL", condition="b")])
    _chay(db, run)
    assert _tt(db, run, "nb") == "QUEUED" and _tt(db, run, "na") == "SKIPPED"


def test_switch_khong_khop_thi_ve_nhanh_mac_dinh(db, lam):
    run = lam([_core("s", "switch", bieu_thuc='"z"', nhanh=["a"],
                     mac_dinh="khac"),
               _app("na"), _app("nk")],
              [_canh("s", "na", kind="CONTROL", condition="a"),
               _canh("s", "nk", kind="CONTROL", condition="khac")])
    _chay(db, run)
    assert _tt(db, run, "nk") == "QUEUED" and _tt(db, run, "na") == "SKIPPED"


def test_switch_khong_khop_va_khong_mac_dinh_thi_MOI_canh_tat(db, lam):
    """⛔ Không có nhánh nào chạy là một KẾT QUẢ, không phải một lỗi.

    Node vẫn SUCCEEDED (nó đã tính xong), nhưng không cạnh nào được kích hoạt
    ⇒ mọi đích SKIPPED. Đoán một nhánh ở đây là chạy một việc không ai yêu cầu.
    """
    run = lam([_core("s", "switch", bieu_thuc='"z"', nhanh=["a"]), _app("na")],
              [_canh("s", "na", kind="CONTROL", condition="a")])
    assert _chay(db, run) == "SUCCEEDED"
    assert _tt(db, run, "s") == "SUCCEEDED" and _tt(db, run, "na") == "SKIPPED"


# ── core.stop ───────────────────────────────────────────────────────────────

def test_stop_ket_thuc_run_ngay_va_khong_nop_them_job(db, lam):
    from platform_core.models import Job
    run = lam([_core("p", "stop", trang_thai="SUCCEEDED", ly_do="du roi"),
               _app("sau")],
              [_canh("p", "sau")])
    truoc = db.query(Job).filter_by(job_type="ltt_llm.chat").count()
    assert _chay(db, run) == "SUCCEEDED"
    assert _tt(db, run, "sau") == "SKIPPED"
    assert db.query(Job).filter_by(job_type="ltt_llm.chat").count() == truoc
    assert run.actual_cost == 0


def test_stop_trang_thai_FAILED_lam_run_FAILED(db, lam):
    run = lam([_core("p", "stop", trang_thai="FAILED", ly_do="dieu kien xau")],
              [])
    assert _chay(db, run) == "FAILED"


def test_stop_trang_thai_la_khong_hop_le_bi_tu_choi_luc_PUBLISH(db, lam):
    """Chặn ở publish, không ở lúc chạy — lúc chạy là lúc đang tiêu tiền."""
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich):
        lam([_core("p", "stop", trang_thai="HOI_HOI")], [])


# ── Publish: compiler phải BIẾT node lõi ────────────────────────────────────

def test_node_loi_thieu_tham_so_bat_buoc_bi_tu_choi_luc_publish(db, lam):
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich):
        lam([_core("i", "if")], [])          # thieu `dieu_kien`


def test_loai_core_khong_ton_tai_bi_tu_choi(db, lam):
    from platform_core.workflow.bien_dich import LoiBienDich
    with pytest.raises(LoiBienDich):
        lam([_core("x", "khong_co_loai_nay")], [])


def test_node_loi_khong_ton_tien_trong_bao_gia(db, lam):
    from platform_core.models import WorkflowVersion
    run = lam([_core("i", "if", dieu_kien="true"), _app("t")],
              [_canh("i", "t", kind="CONTROL", condition="true")])
    g = db.get(WorkflowVersion, run.version_id).graph
    assert g["bang_gia"]["i"] == 0 and g["bang_gia"]["t"] == 3
    assert run.estimated_max == 3


# ── Trần 500 bước inline (spec §5.1) ────────────────────────────────────────

def test_tran_buoc_inline_moi_vong_la_mot_con_so_khai_ra():
    """§5.1: *"giới hạn 500 bước inline mỗi run mỗi vòng, vượt thì để vòng sau"*."""
    from platform_core.workflow import dong_co
    assert dong_co.TRAN_BUOC_INLINE == 500
