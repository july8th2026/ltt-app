"""`cau_noi.nop_job` nộp job THẬT cho `piece.*` (lan wfp, plan 08, 25/09).

`_nop_job_connector` (P6) đã có từ trước và đã có test riêng
(`test_3504_wf_cau_noi_connector.py`, qua `connector.youtube.upload`) — nó
CHẠY ĐƯỢC cho `piece.*` từ lâu, chỉ là không CÓ AI GỌI TỚI nó: `nop_job` rẽ
nhánh bằng `cau_noi._dinh_nghia(node["type"])`, và hàm đó trước bản vá này
chỉ tra `nut_loi.tat_ca()` — một sổ không bao giờ chứa node piece (nguồn thứ
ba, catalog runner). Hệ quả: một node `piece.*` luôn rơi xuống nhánh
`ten_cong_cu()` cũ và bị `LoiTienTo` — dù đã publish được (đã compile OK).

Tệp này đo ĐÚNG khoảng nối đó, cộng một khoảng nối THỨ HAI phát hiện trong
lúc sửa (không nằm trong ba chỗ đầu bài đã nêu): `_nop_job_connector` chưa
bao giờ chuyển `credential_ref` của node vào tham số job — MỌI job piece/
connector (kể cả `connector.youtube.upload` đang sống) chạy với credential
RỖNG ở phía handler, bất kể node đã gắn credential thật hay chưa.
"""
from __future__ import annotations
# ruff: noqa: F811 -- fixture pytest duoc import co chu y.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

GIA_PIECE = 11
TEN_PIECE = "piece.demo.gui_tin"


def _catalog_gia() -> list:
    return [{
        "type": TEN_PIECE, "type_version": 1,
        "title": "Demo gui tin", "description": "Piece gia cho test 4271",
        "icon": "D", "auth": ["oauth2"],
        "params": {"noi_dung": {"type": "string", "required": True}},
        "returns": {"ok": "json"}, "gia": GIA_PIECE, "side_effect": "external",
    }]


@pytest.fixture()
def nguon_piece_gia(monkeypatch):
    """Xem `test_4270_wf_piece_publish_duoc.py::nguon_piece_gia` — phải ép
    nhập `nut_loi` TRƯỚC monkeypatch, không thì hiệu ứng phụ nhập lần đầu
    (`nut_loi/connector.py`) ghi đè catalog giả bằng catalog thật."""
    from platform_core.workflow import nut, nut_loi
    nut_loi.tat_ca()
    monkeypatch.setattr(nut, "NGUON_PIECE", _catalog_gia)
    return nut


@pytest.fixture()
def run(db, nguon_piece_gia):
    """Workflow một node piece, publish thật, có credential thật, có run."""
    from platform_core import credential as kho, credit
    from platform_core.workflow import dinh_nghia, tao_run

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="wf-nop-job")
    cred = kho.tao(db, owner_id="u1", kieu="oauth2", bi_mat="tok-demo")
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": TEN_PIECE, "position": {"x": 0, "y": 0},
         "params": {"noi_dung": "chao"}, "credential_ref": cred.id},
    ], "edges": []}]}
    dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
    v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu={})
    wf.published_version_id = v.id
    credit.nap(db, "u1", 100, note="test")
    db.flush()
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k")
    return r, cred


# ── 1. Publish được VÀ nộp được job thật ────────────────────────────────────

def test_node_piece_publish_duoc_VA_nop_duoc_job_that(db, run):
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut

    r, _cred = run
    mtt.chuyen_node(db, r.id, "a", sang="READY", mo_ta="t")
    jid = cau_noi.nop_job(db, r, {"id": "a", "type": TEN_PIECE,
                                  "params": {"noi_dung": "chao"},
                                  "credential_ref": "", "gia_tran": GIA_PIECE},
                          cong_cu={})
    assert jid is not None, "van con bi LoiTienTo tu choi"
    job = db.get(Job, jid)
    assert job.job_type == nut.JOB_TYPE_PIECE
    assert job.app_slug == "connector_runner"
    assert mtt.trang_thai_node(db, r.id, "a") == "QUEUED"


def test_nop_job_doc_TU_DUNG_do_thi_da_ghim(db, run):
    """`nop_job` phải nhận node THẬT đọc từ `WorkflowVersion.graph` (đường
    production đi qua `dong_co`), không chỉ một dict tay dựng riêng cho test
    trên — đối chứng rằng con đường publish → chạy khớp nhau đầu-cuối."""
    from platform_core.models import Job, WorkflowVersion
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut

    r, _cred = run
    v = db.get(WorkflowVersion, r.version_id)
    node = next(n for n in v.graph["nodes"] if n["id"] == "a")
    assert node["type"] == TEN_PIECE and node["thi_hanh"] == "job"
    mtt.chuyen_node(db, r.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, r, node, cong_cu={}))
    assert job.job_type == nut.JOB_TYPE_PIECE


# ── 2. Credential được CHUYỂN vào job — khoảng nối thứ hai ──────────────────

def test_credential_ref_DUOC_CHUYEN_vao_tham_so_job(db, run):
    """🔴 Trước bản vá: `tham_so` không mang `credential_ref` — handler
    (`apps/connector_runner/jobs.py::_bi_mat`) luôn nhận ref RỖNG."""
    from platform_core.models import Job, WorkflowVersion
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    from platform_core.workflow.connector import THAM_SO_CREDENTIAL

    r, cred = run
    v = db.get(WorkflowVersion, r.version_id)
    node = next(n for n in v.graph["nodes"] if n["id"] == "a")
    assert node["credential_ref"] == cred.id      # doi chung: ref co that
    mtt.chuyen_node(db, r.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, r, node, cong_cu={}))
    assert job.params[THAM_SO_CREDENTIAL] == cred.id, (
        "job khong mang credential_ref -- handler se chay KHONG co credential")


def test_khong_gan_credential_thi_job_mang_ref_RONG_khong_phai_LOI(db, run):
    """Đối chứng: một node KHÔNG gắn ref (draft khác, node vẫn hợp lệ vì
    node piece không bắt buộc publish phải có ref — bắt buộc là chuyện của
    `_kiem_credential`, đã đo ở `test_4270`) thì job mang chuỗi rỗng, không
    phải `None`/`KeyError` làm handler vỡ."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    from platform_core.workflow.connector import THAM_SO_CREDENTIAL

    r, _cred = run
    mtt.chuyen_node(db, r.id, "a", sang="READY", mo_ta="t")
    node = {"id": "a", "type": TEN_PIECE, "params": {"noi_dung": "chao"},
            "credential_ref": "", "gia_tran": GIA_PIECE}
    job = db.get(Job, cau_noi.nop_job(db, r, node, cong_cu={}))
    assert job.params[THAM_SO_CREDENTIAL] == ""


# ── 3. Trần báo giá vẫn cắn ──────────────────────────────────────────────────

def test_vuot_tran_bao_gia_van_FAILED_khong_nop_job(db, run):
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut

    r, _cred = run
    mtt.chuyen_node(db, r.id, "a", sang="READY", mo_ta="t")
    node = {"id": "a", "type": TEN_PIECE, "params": {"noi_dung": "chao"},
            "credential_ref": "", "gia_tran": 0}   # tran duoi gia that (11)
    assert cau_noi.nop_job(db, r, node, cong_cu={}) is None
    assert mtt.trang_thai_node(db, r.id, "a") == "FAILED"
    assert db.query(Job).filter(Job.job_type == nut.JOB_TYPE_PIECE).count() == 0


# ── 4. Tiêm lỗi: nếu `_dinh_nghia` lùi về CHỈ tra nut_loi ───────────────────

def test_TIEM_LOI_lui_ve_chi_tra_nut_loi_thi_bai_1_do(db, run, monkeypatch):
    """⭐ Tái hiện đúng lỗi cũ: `cau_noi._dinh_nghia` chỉ tra `nut_loi.tat_ca()`
    (bỏ nhánh `nut.dinh_nghia_piece` mà bản vá vừa thêm). Node piece khi đó
    lại rơi xuống `ten_cong_cu()`/`LoiTienTo` — CHỨNG MINH
    `test_node_piece_publish_duoc_VA_nop_duoc_job_that` ở trên thật sự đo
    đúng cửa `_dinh_nghia`, không xanh vì một lý do khác."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut, nut_loi

    def _dinh_nghia_cu(loai):
        return nut_loi.tat_ca().get(str(loai))

    monkeypatch.setattr(cau_noi, "_dinh_nghia", _dinh_nghia_cu)
    r, _cred = run
    mtt.chuyen_node(db, r.id, "a", sang="READY", mo_ta="t")
    node = {"id": "a", "type": TEN_PIECE, "params": {"noi_dung": "chao"},
            "credential_ref": "", "gia_tran": GIA_PIECE}
    assert cau_noi.nop_job(db, r, node, cong_cu={}) is None
    anh_trang_thai = mtt.trang_thai_node(db, r.id, "a")
    assert anh_trang_thai == "FAILED", (
        "voi cua long leo (chi tra nut_loi), node PHAI FAILED bang LoiTienTo, "
        f"khong phai {anh_trang_thai!r}")
    # ⛔ KHONG so `db.query(Job).count() == 0`: `tao_run` da tu tao mot job
    #    DONG CO rieng (`tao_run.DONG_CO_JOB`) truoc khi bai nay chay toi day
    #    -- dem CA BANG la dem lan ca job khong lien quan. Loc dung job_type.
    assert db.query(Job).filter(Job.job_type == nut.JOB_TYPE_PIECE).count() == 0
