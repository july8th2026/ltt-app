"""Node bọc ToolSpec phải **KHAI** tên nó bọc — và kết quả job phải qua HẬU KIỂM.

## 🔴 Vì sao khai tường minh, chứ không suy ra

Cách "thông minh" là tra ngược `job_type → tên tool`: `ai.llm` khai
`job_type="ltt_llm.chat"`, vậy cứ tìm `CongCu` nào có `job_type` ấy.
**Đo rồi, không dùng được** — trên registry hôm nay (19 tool) có **ba**
`job_type` bị hai tool dùng chung:

    {'prompt_ai_ommi.generate': 2, 'taoanh.generate': 2, 'upscalevideo.render': 2}

Một tra ngược đúng hôm nay và sai vào đúng ngày ai đó thêm tool thứ hai trên
`ltt_llm.chat` — **im lặng**, và nó chọn tool nào thì tuỳ thứ tự dict. Cùng
hạng lỗi với số cứng `[4:]` mà `test_1788` vừa chặn: một phép suy **đúng hôm
nay** và **sai im lặng** vào ngày dữ liệu đổi.

⇒ `NodeDefinition.ten_toolspec`. Thiếu nó ⇒ **ném lúc ĐĂNG KÝ**, tức lúc
  `import`, chỗ người viết node nhìn thấy ngay — không phải lúc chạy, chỗ đang
  tiêu tiền của khách (`nut.LoiNut` docstring).

## 🔴 Hậu kiểm: job SUCCEEDED **không** đảm bảo có kết quả dùng được

`nut_loi/ai_loi.py` ghi lại ca đã đo trên máy B (10–12/09): HTTP **200**, job
**SUCCEEDED**, mà `content` **RỖNG** — khối suy nghĩ không bao giờ đóng. *"Vô
hình với quan trắc"*: `dem.ok` vẫn cộng một, không log lỗi nào.

`cau_noi.ap_ket_qua` chỉ đọc `job.status`/`sig.status`; nó **không mở `result`
ra xem**. Với `app.image.generate` thế là đúng (job xong là có tệp). Với
`text.chat` thì **không**: job xong không đảm bảo có chữ.

⇒ `NodeDefinition.hau_kiem` — một lớp diễn giải node tự khai, chạy **trước** khi
  cầu nối coi kết quả là SUCCEEDED. ⛔ `cau_noi` **không** được biết `ai` là gì;
  nó chỉ hỏi định nghĩa node *"kết quả này dùng được không"*.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import json

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


def _khung(**ghi_de):
    """`NodeDefinition` tối thiểu, để phép kiểm nói về ĐÚNG một trường."""
    from platform_core.workflow import he_kieu
    from platform_core.workflow.nut import Gia, NodeDefinition
    tham = dict(
        type="thu.nghiem", type_version=1, kind="ai", category="AI",
        title="t", description="d", icon="x",
        cong_vao=(("in", he_kieu.Cong(type="any", required=False, nhan="in")),),
        cong_ra=(("text", he_kieu.Cong(type="text", required=True,
                                       nhan="text")),),
        tham_so={"type": "object", "properties": {}, "required": [],
                 "additionalProperties": False},
        thi_hanh="job", job_type="ltt_llm.chat", gia=Gia.mien_phi(),
        quyen=frozenset(), cho=(), ma_loi=())
    tham.update(ghi_de)
    return NodeDefinition(**tham)


# ── Trường mới: bắt buộc, và ném LÚC DỰNG ───────────────────────────────────

def test_node_job_thieu_ten_toolspec_NEM_luc_dung():
    from platform_core.workflow.nut import LoiNut
    with pytest.raises(LoiNut) as e:
        _khung(ten_toolspec="")
    assert "ten_toolspec" in str(e.value)


def test_doi_chung_node_INLINE_khong_can_khai():
    """Node lõi chạy trong động cơ không bọc ToolSpec nào — không được đòi nó."""
    nd = _khung(thi_hanh="inline", job_type="", ten_toolspec="")
    assert nd.ten_toolspec == ""


def test_tu_toolspec_tu_khai_ten_cua_chinh_no():
    """Node `app.*` suy từ `CongCu` ⇒ tên đã biết, không được để trống."""
    from platform_core.workflow.nut import tu_toolspec
    nd = tu_toolspec(CC["text.chat"])
    assert nd.type == "app.text.chat" and nd.ten_toolspec == "text.chat"


# ── Bánh cóc: trường này KHÔNG được mục ─────────────────────────────────────

def test_banh_coc_moi_node_job_khai_ten_CO_THAT_trong_registry():
    """⛔ Tên khai phải tồn tại trong registry — không thì trường này mục đúng
    lúc ai đó thêm node mới, y như một danh sách chép tay.

    ⭐ Cắn thật: đổi `ten_toolspec` của `ai.llm` thành `"text.chatt"` là đủ để
       nó đỏ (đã tiêm thử — xem báo cáo).

    Đối chứng: khẳng định có ÍT NHẤT một node job trong sổ trước, để một sổ
    rỗng không cho ra "0 vi phạm" rồi xanh giả.
    """
    from platform_core.workflow import cong_cu, nut_loi
    from platform_core.workflow.nut import JOB_TYPE_PIECE
    so = nut_loi.tat_ca()
    job = {ten: nd for ten, nd in so.items() if nd.thi_hanh == "job"}
    assert job, "khong co node job nao trong so - phep kiem dang do tap rong"
    co_that = set(cong_cu.tat_ca())
    xau = {ten: nd.ten_toolspec for ten, nd in job.items()
           if nd.ten_toolspec not in co_that
           and nd.job_type != JOB_TYPE_PIECE}
    assert not xau, f"khai ten khong co trong registry: {xau}"


def test_banh_coc_NGOAI_LE_dung_bang_MOT_bo_thi_hanh():
    """⛔ Chỉ `piece.*` được miễn khai, và miễn theo **bộ thi hành**.

    Node piece chạy trên runner Node (`JOB_TYPE_PIECE`), không đi qua
    registry ToolSpec — nó không bọc ToolSpec nào để mà khai. Nhưng một
    ngoại lệ không ai canh sẽ thành một cái cửa: nếu mai có bộ thi hành
    THỨ BA mà không khai gì, `__post_init__` phải NÉM lúc import.

    ⇒ Phép này đo chính điều đó, thay vì tin vào một câu bình luận.
    """
    from platform_core.workflow.nut import JOB_TYPE_PIECE, LoiNut

    # Miễn: đúng bộ thi hành piece.
    nd = _khung(kind="connector", category="CONNECTORS",
                job_type=JOB_TYPE_PIECE, ten_toolspec="")
    assert nd.job_type == JOB_TYPE_PIECE and nd.ten_toolspec == ""
    # ⛔ Không miễn: một bộ thi hành thứ ba.
    with pytest.raises(LoiNut):
        _khung(job_type="runner.thu_ba", ten_toolspec="")


# ── `cau_noi` đọc được node `ai.*` nhờ khai báo ─────────────────────────────

def test_ten_cong_cu_doc_khai_bao_cua_node_loi():
    from platform_core.workflow.cau_noi import ten_cong_cu
    assert ten_cong_cu("ai.llm") == "text.chat"
    assert ten_cong_cu("ai.extract") == "text.chat"
    assert ten_cong_cu("ai.router") == "text.chat"


def test_nop_job_cho_node_ai_nay_RA_JOB_THAT(db, run):
    """Trước bản này, `ai.llm` qua `nop_job` ra tên tool `"lm"` rồi FAILED."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = {"id": "a", "type": "ai.llm", "type_version": 1,
            "params": {}, "credential_ref": "", "settings": {},
            "thi_hanh": "job", "gia_tran": 3}
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    jid = cau_noi.nop_job(db, run, node, cong_cu=CC)
    assert jid is not None
    assert db.get(Job, jid).job_type == "ltt_llm.chat"
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"


# ── HẬU KIỂM: job SUCCEEDED mà kết quả không dùng được ──────────────────────

def _thanh_ai(db, run, params=None):
    """Đổi node `a` của đồ thị ĐÃ GHIM thành `ai.llm`.

    ⚠️ Phải sửa **đồ thị**, không chỉ truyền một dict: `ap_ket_qua` đọc node
       bằng `_node_cua` từ `WorkflowVersion.graph` — đúng như vậy, vì đồ thị đã
       ghim là nguồn chân lý lúc chạy. Một phép kiểm truyền dict riêng sẽ đo
       `nop_job` mà **không** đo `ap_ket_qua`, và im lặng bỏ sót đúng nhánh
       đang cần kiểm.
    """
    from platform_core.models import WorkflowVersion
    v = db.get(WorkflowVersion, run.version_id)
    g = dict(v.graph)
    g["nodes"] = [dict(n) for n in g["nodes"]]
    node = next(n for n in g["nodes"] if n["id"] == "a")
    node["type"] = "ai.llm"
    node["params"] = dict(params or {})
    v.graph = g
    db.flush()
    return node


def _nop_va_xong(db, run, ket_qua: dict, params=None):
    """Nộp job cho một node `ai.llm` rồi cho job SUCCEEDED với `ket_qua`."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = _thanh_ai(db, run, params)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    jobs.complete(db, job, ket_qua)
    return cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC), node


def test_doi_chung_content_dung_duoc_thi_SUCCEEDED(db, run):
    """Nếu phép này đỏ thì hậu kiểm đang từ chối cả kết quả tốt."""
    sang, _ = _nop_va_xong(db, run, {"content": "xin chao"})
    assert sang == "SUCCEEDED" and run.actual_cost == 3


def test_content_RONG_thi_node_FAILED_dau_ra_rong(db, run):
    """🔴 HTTP 200 · job SUCCEEDED · `content` rỗng — ca đã đo trên máy B."""
    from platform_core.workflow import thi_hanh
    sang, _ = _nop_va_xong(db, run, {"content": "   "})
    assert sang == "FAILED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert "dau_ra_rong" in anh.error
    # ⛔ Không thu tiền cho một câu trả lời rỗng — cùng luật với mọi node FAILED.
    assert anh.cost_credit == 0 and run.actual_cost == 0


def test_content_khong_khop_luoc_do_thi_FAILED(db, run):
    from platform_core.workflow import thi_hanh
    luoc_do = {"type": "object", "properties": {"n": {"type": "integer"}},
               "required": ["n"]}
    sang, _ = _nop_va_xong(db, run, {"content": json.dumps({"n": "khong phai so"})},
                           params={"luoc_do": luoc_do})
    assert sang == "FAILED"
    assert "dau_ra_sai_luoc_do" in thi_hanh.anh_chup_hien_tai(
        db, run.id, "a").error


def test_khop_luoc_do_thi_SUCCEEDED(db, run):
    luoc_do = {"type": "object", "properties": {"n": {"type": "integer"}},
               "required": ["n"]}
    sang, _ = _nop_va_xong(db, run, {"content": json.dumps({"n": 7})},
                           params={"luoc_do": luoc_do})
    assert sang == "SUCCEEDED"


def test_doi_chung_node_APP_khong_bi_hau_kiem(db, run):
    """Node `app.*` không khai `hau_kiem` ⇒ đường cũ y nguyên.

    ⛔ Nếu hậu kiểm áp cho mọi node thì `app.text.chat` trả `{"text": ...}`
       (không có khoá `content`) sẽ bị coi là rỗng và FAILED — một hồi quy im
       lặng trên đường đang chạy thật.
    """
    from platform_core import jobs
    from platform_core.models import Job, WorkflowVersion
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    g = db.get(WorkflowVersion, run.version_id).graph
    node = next(n for n in g["nodes"] if n["id"] == "a")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    jobs.complete(db, job, {"text": "xin chao"})
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "SUCCEEDED"


def test_banh_coc_cau_noi_khong_biet_ai_la_gi():
    """⛔ `cau_noi.py` KHÔNG được nhắc tên không gian `ai.` hay import `ai_loi`.

    Global Constraint của kho: nền tảng không hardcode tên app/tool. Một `if
    node["type"].startswith("ai.")` trong cầu nối là đúng hạng ấy — và nó buộc
    mọi loại node mới cần hậu kiểm phải sửa lại chính hàm đang giữ sổ tiền.
    """
    import ast
    import pathlib

    nguon = pathlib.Path("platform_core/workflow/cau_noi.py").read_text(
        encoding="utf-8")
    assert "hau_kiem" in nguon and len(nguon) > 1000      # doi chung
    cay = ast.parse(nguon)
    # ⚠️ Đọc AST, KHÔNG grep chuỗi thô: docstring của tệp ấy *phải* được kể lại
    #    ca `"ai.llm"` ra `"lm"` — nhắc trong TÀI LIỆU là đúng, nhánh trong MÃ
    #    mới là sai. Một bánh cóc không phân biệt được hai chuyện đó sẽ dạy
    #    người ta xoá lời giải thích.
    tai_lieu = {ast.get_docstring(n) for n in ast.walk(cay)
                if isinstance(n, (ast.Module, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef))}
    xau = [ast.unparse(n) for n in ast.walk(cay)
           if isinstance(n, ast.Constant) and isinstance(n.value, str)
           and n.value not in tai_lieu and n.value.startswith("ai.")]
    assert not xau, f"cau noi co hang so chuoi khong gian `ai.`: {xau}"
    nhap = [ast.unparse(n) for n in ast.walk(cay)
            if isinstance(n, (ast.Import, ast.ImportFrom))
            and "ai_" in ast.unparse(n)]
    assert not nhap, f"cau noi import mo-dun AI: {nhap}"
