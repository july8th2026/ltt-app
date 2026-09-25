"""`core.code` được ĐĂNG KÝ — lan `wfd2`, P-D mục 3 (điều kiện `wfd` đã đạt).

Không lặp lại `test_4230` (lớp isolated-vm) hay `test_4231` (bảy đường thoát
D1–D7 của AppContainer) — cả hai đã xanh trên `main` và đo đúng CÁI VỎ. Tệp
này đo phần `wfd2` thêm vào: NODE có thật trong registry, đi ĐÚNG cửa
`bao_gia`/`bien_dich`/`cau_noi`, và không đổi hình dạng an ninh khi đi qua
những cửa đó.

⛔ Bài "mã người dùng vẫn bị chặn" ở đây KHÔNG chạy lại cả bảy đường D1–D7:
   nó chỉ cần chứng minh MỘT điều mà `test_4230`/`test_4231` không đo được —
   rằng đường ĐĂNG KÝ MỚI (node → job → handler) thật sự **gọi tới**
   `code_sandbox.chay()` (vỏ riêng, không proxy), không lặng lẽ rơi vào
   `_chay_piece` (vỏ khác, luôn mở `proxy_egress`) hay một đường tắt nào
   khác. Đó là phép TIÊM LỖI đúng nghĩa của lan này: "nếu ai đó đăng ký node
   mà quên đưa qua vỏ" — mô phỏng bằng theo dõi ĐÚNG hàm nào chạy.
"""
from __future__ import annotations
# ruff: noqa: F811 -- fixture pytest duoc import co chu y.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC
from tests.test_1717_wf_tao_run import wf  # noqa: F401
from tests.test_3504_wf_cau_noi_connector import _thanh_connector


# ── 1. Đăng ký: đúng registry, đúng job_type, đúng nhánh KHÔNG-ToolSpec ─────

def test_core_code_co_trong_nut_loi_va_khai_JOB_TYPE_CODE():
    from platform_core.workflow import nut, nut_loi

    so = nut_loi.tat_ca()
    assert "core.code" in so, "core.code chua duoc dang ky trong nut_loi"
    nd = so["core.code"]
    assert nd.thi_hanh == "job"
    assert nd.job_type == nut.JOB_TYPE_CODE == "workflow.code"
    assert nd.job_type in nut.JOB_TYPE_KHONG_TOOLSPEC, (
        "khong o trong tap mien ToolSpec -- __post_init__ le ra da nem luc import")
    assert nd.ten_toolspec == "", "core.code khong boc ToolSpec nao"
    assert nd.publish_duoc is True
    # Khong xin quyen nao ma vo khong cho: dung mo ta nhung gi node THAT SU
    # cham toi (khong mang, khong credential, khong tep, khong tien trinh con).
    assert nd.quyen == frozenset()
    assert nd.credential == ()
    assert nd.side_effect == "none"


def test_workflow_code_co_CHU_trong_registry_khong_thi_QUEUED_mai_mai():
    """`_chu_job` (cau_noi.py) tra `registry.job_type_owners()` -- thieu chu
    thi node dung QUEUED toi khi TRAN_RUN (20 gio) het han, im lang."""
    from platform_core import registry
    from platform_core.workflow import nut

    chu = registry.job_type_owners().get(nut.JOB_TYPE_CODE)
    assert chu == "connector_runner", (
        f"workflow.code chua co chu (hoac sai chu): {chu!r} -- "
        "kiem apps/connector_runner/manifest.py::job_types")


# ── 2. bao_gia._gia_node -- ĐÚNG nhánh giá cố định, KHÔNG qua ToolSpec ──────

def test_gia_node_di_nhanh_CO_DINH_khong_can_ToolSpec_nao():
    """`cc={}` (registry ToolSpec RONG) van bao gia duoc: chung minh
    `core.code` khong roi vao nhanh `cc.get(ten_cong_cu)` phia duoi -- dung
    nhu chu thich `bao_gia._gia_node` da chot 25/09 (gop wfp+wfg)."""
    from platform_core.workflow import bao_gia

    node = {"id": "n1", "type": "core.code", "thi_hanh": "job",
            "params": {"code": "module.exports.code=function(i){return i;};"}}
    gia = bao_gia._gia_node(node, cc={})
    assert gia == 1, f"gia co dinh cua core.code phai la 1 (Gia.co_dinh(1)), duoc {gia}"


def test_bao_gia_do_thi_mot_do_thi_co_core_code_ra_so_KHAC_0():
    """`toi_da` cua ca do thi phai la mot so **dung va khac 0** -- 0 se lam
    node nay bien mat vao nhom "mien phi" cung nhung node khong co tran nao
    ngoai nen tang kiem soat (xem ly do trong `nut_loi/code.py::CORE_CODE`)."""
    from platform_core.workflow import bao_gia

    graph = {
        "schema": "ltt.workflow/3", "inputs": [], "outputs": [],
        "settings": {"max_concurrency": 4, "timeout_s": 600},
        "nodes": [
            {"id": "n1", "type": "core.code", "type_version": 1,
             "params": {"code": "module.exports.code=function(i){return i;};"},
             "credential_ref": "", "settings": {}, "thi_hanh": "job"},
        ],
        "edges": [], "thu_tu": ["n1"],
    }
    bg = bao_gia.bao_gia_do_thi(graph, cong_cu={})
    assert bg.toi_da == 1 and bg.toi_da != 0
    assert graph["bang_gia"] == {"n1": 1}


def test_xuat_ban_draft_THAT_co_node_core_code_qua_bien_dich(db):
    """Duong PUBLISH THAT (`dinh_nghia.xuat_ban_draft` -> `bien_dich.cau_truc`),
    khong phai mot graph da bien dich dung tay: chung minh trinh bien dich
    chap nhan `"type": "core.code"` o dang draft nguyen ban, dung hinh dang
    ma trinh soan se gui (`{"id","type","params"}` o cap node, KHONG boc
    `data.tool` -- khac han node app.*, giong `core.http`/piece)."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="co-core-code")
    doc = {"version": 3, "pages": [{"id": "p1", "edges": [], "nodes": [
        {"id": "n1", "type": "core.code",
         "params": {"code": "module.exports.code=function(i){return i;};",
                    "inputs": {}}},
    ]}]}
    dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
    v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu=CC)
    assert v.graph["bang_gia"] == {"n1": 1}
    assert v.estimated_max == 1
    node = next(n for n in v.graph["nodes"] if n["id"] == "n1")
    assert node["type"] == "core.code" and node["thi_hanh"] == "job"


# ── 3. cau_noi.nop_job -- publish được, nộp job THẬT (không LoiTienTo) ──────

@pytest.fixture()
def run(db, wf, monkeypatch):
    from platform_core.workflow import cong_cu, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k-code")
    return r


def test_publish_va_nop_JOB_THAT_cho_core_code(db, run):
    """Trước lan này, mọi `type` không thuộc `app.*`/`piece.*`/`connector.*`
    ném `LoiTienTo` ở `nop_job`. Đo rằng `core.code` nay ra một job THẬT,
    trên đúng lane connector, đúng `job_type` MỚI (không lẫn với
    `workflow.piece`/`workflow.connector` của hai nguồn kia — lý do ở
    `nut_loi/code.py`)."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut

    node = _thanh_connector(
        db, run, loai="core.code",
        params={"code": "module.exports.code=function(i){return {tong:(i.a||0)+(i.b||0)};};",
                "inputs": {"a": 1, "b": 2}},
        gia_tran=1)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    jid = cau_noi.nop_job(db, run, node, cong_cu=CC)
    assert jid is not None, "core.code van bi tu choi (LoiTienTo hoac tran gia)"
    job = db.get(Job, jid)
    assert job.job_type == nut.JOB_TYPE_CODE == "workflow.code"
    assert job.app_slug == "connector_runner"
    assert job.params["_connector"]["node_type"] == "core.code"
    assert job.params["code"] == node["params"]["code"]
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"


def test_vuot_TRAN_BAO_GIA_thi_FAILED_khong_nop_job_cho_core_code(db, run):
    """Cùng luật trần mà `test_3504` đã chốt cho connector -- không được rơi
    mất chỉ vì đường mới thêm một `job_type` thứ ba."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut

    node = _thanh_connector(db, run, loai="core.code",
                            params={"code": "module.exports.code=function(){};"},
                            gia_tran=0)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert cau_noi.nop_job(db, run, node, cong_cu=CC) is None
    assert mtt.trang_thai_node(db, run.id, "a") == "FAILED"
    assert db.query(Job).filter(Job.job_type == nut.JOB_TYPE_CODE).count() == 0


# ── 4. TIÊM LỖI: quên đưa qua vỏ -- bài nào bắt được? ───────────────────────

def test_TIEM_LOI_handle_core_code_PHAI_goi_code_sandbox_chay_khong_phai_gi_khac(
        db, monkeypatch):
    """Mo phong dung ca "ai do dang ky node ma QUEN dua qua vo": neu dispatch
    trong `apps/connector_runner/jobs.py::handle` bi doi (vo tinh hay co y)
    sang `_chay_piece` (mo `proxy_egress`, vo `ltt-connector-runner` khac han)
    hoac goi thang mot ham chay JS nao khac, bai nay phai do duoc -- theo doi
    DUNG ham `code_sandbox.chay` co duoc goi, voi dung `code`/`inputs` cua
    node, khong phai mot duong nao khac."""
    from platform_core.workflow.code_sandbox import KetQuaCode

    goi = {}

    def gia_chay(nguon, inputs=None, **kw):
        goi["nguon"] = nguon
        goi["inputs"] = inputs
        return KetQuaCode(ok=True, output={"echo": inputs})

    monkeypatch.setattr(
        "platform_core.workflow.code_sandbox.chay", gia_chay)

    from apps.connector_runner import jobs as cj

    ra = cj.handle({
        "code": "module.exports.code=function(i){return i;};",
        "inputs": {"x": 1},
        "_connector": {"node_type": "core.code", "run_id": "r1", "node_id": "n1"},
    })
    assert goi.get("nguon") == "module.exports.code=function(i){return i;};", (
        "khong thay _chay_code goi code_sandbox.chay voi dung `code` -- "
        "dispatch co the da roi vao mot duong KHONG qua vo rieng")
    assert goi.get("inputs") == {"x": 1}
    assert ra["output"] == {"echo": {"x": 1}}


def test_TIEM_LOI_khong_di_qua_chay_piece_mo_proxy_egress(db, monkeypatch):
    """Doi chung theo chieu khac: neu `_connector.chay` (duong cua
    `piece.*`/`_chay_piece`, luon mo `proxy_egress`) bi goi cho mot node
    `core.code`, do la dung hinh dang loi ma phep tren duoc viet ra de bat.

    ⭐ Van mock `code_sandbox.chay` (khong can vo AppContainer that o day --
       do da la viec cua `test_4230`/`test_4231`): phep nay CHI do dispatch
       co di NHAM sang `_connector.chay` hay khong.
    """
    from platform_core.workflow.code_sandbox import KetQuaCode

    monkeypatch.setattr(
        "platform_core.workflow.code_sandbox.chay",
        lambda nguon, inputs=None, **kw: KetQuaCode(ok=True, output=42))

    goi_connector_chay = {"da_goi": False}

    def gia_connector_chay(*a, **kw):
        goi_connector_chay["da_goi"] = True
        raise AssertionError("khong duoc goi toi day cho core.code")

    monkeypatch.setattr(
        "platform_core.workflow.connector.chay", gia_connector_chay)

    from apps.connector_runner import jobs as cj

    ra = cj.handle({
        "code": "module.exports.code=function(i){return 42;};",
        "inputs": {},
        "_connector": {"node_type": "core.code", "run_id": "r1", "node_id": "n1"},
    })
    assert goi_connector_chay["da_goi"] is False, (
        "⛔ core.code di qua _connector.chay -- vo SAI (proxy_egress mo, "
        "khac han ltt-code-runner)")
    assert "output" in ra
