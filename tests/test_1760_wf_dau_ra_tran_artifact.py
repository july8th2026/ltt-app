"""Spec §5.8 — output JSON > 256 KB lưu thành artifact `kind=json`, output giữ
ref. Plan 01a để node FAILED `dau_ra_qua_lon`; đây là chỗ trả nợ."""
from __future__ import annotations
# ruff: noqa: F811

import json

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1717_wf_tao_run import wf  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC


@pytest.fixture()
def run(db, wf, monkeypatch, tmp_path):
    from platform_core import storage as st
    from platform_core.workflow import cong_cu, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    st.set_storage(st.LocalStorage(str(tmp_path / "kho")))
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k")
    yield r
    st.set_storage(None)


def _node(db, run, nid):
    from platform_core.models import WorkflowVersion
    g = db.get(WorkflowVersion, run.version_id).graph
    return next(n for n in g["nodes"] if n["id"] == nid)


def _to(n: int = 300 * 1024) -> dict:
    return {"text": "x" * n}


def test_output_qua_lon_KHONG_con_lam_node_FAILED(db, run):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, _to())
    assert cau_noi.ap_ket_qua(db, run, "a") == "SUCCEEDED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    tran = anh.output_ref["_tran"]
    assert tran["kind"] == "json" and tran["mime"] == "application/json"
    assert tran["size_bytes"] > cau_noi.GIOI_HAN_DAU_RA
    assert tran["artifact_ref"].startswith("local:")


def test_artifact_duoc_ghi_danh_va_doc_lai_dung_noi_dung(db, run):
    from platform_core import jobs, storage
    from platform_core.models import Artifact, Job
    from platform_core.workflow import artifact, cau_noi, may_trang_thai as mtt
    from platform_core.workflow import thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    goc = _to()
    jobs.complete(db, job, goc)
    cau_noi.ap_ket_qua(db, run, "a")
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    aid = anh.output_ref["_tran"]["artifact_ref"]
    row = db.get(Artifact, aid)
    assert row is not None and row.owner_id == "u1" and row.kind == "json"
    assert row.ttl_class == "RUN"
    # LINEAGE: tra loi duoc "tep nay tu dau ra" bang MOT cot.
    assert row.created_by_snapshot_id == anh.id
    _, key = artifact.tach_id(aid)
    with storage.get_storage().open(key) as f:
        assert json.loads(f.read().decode("utf-8")) == goc


def test_chi_phi_van_tinh_tu_credit_cost_TRUOC_khi_tran(db, run):
    # Thu tu quan trong: doc `credit_cost` TRUOC khi thay `du_lieu` bang ref,
    # neu khong moi node tran deu thu theo `gia_that`.
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, {**_to(), "credit_cost": 1})
    cau_noi.ap_ket_qua(db, run, "a")
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.cost_credit == 1 and run.actual_cost == 1


def test_output_NHO_khong_dung_toi_kho(db, run):
    from platform_core import jobs
    from platform_core.models import Artifact, Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, {"text": "ngan"})
    cau_noi.ap_ket_qua(db, run, "a")
    assert thi_hanh.anh_chup_hien_tai(db, run.id, "a").output_ref == {
        "text": "ngan"}
    assert db.query(Artifact).count() == 0


def test_node_sau_tham_chieu_output_da_tran_thi_bao_MA_RIENG(db, run):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, _to())
    cau_noi.ap_ket_qua(db, run, "a")
    with pytest.raises(cau_noi.LoiThamSo) as loi:
        cau_noi.giai_tham_so(db, run.id, {"q": "{{ nodes.a.output.text }}"})
    assert loi.value.ma == "dau_ra_tran_artifact"


def test_backend_cua_doc_dung_ten_kho():
    from platform_core import storage as st
    from platform_core.workflow import artifact
    assert artifact.backend_cua(st.LocalStorage.__new__(st.LocalStorage),
                                "a/b.json") == "local"
    assert artifact.backend_cua(st.R2Storage.__new__(st.R2Storage),
                                "a/b.json") == "r2"
