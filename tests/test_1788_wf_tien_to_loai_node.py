"""Cầu nối job suy tên ToolSpec bằng `type[4:]` — một số cứng SAI IM LẶNG.

## 🔴 Lỗi, nguyên văn từ người phát hiện

`platform_core/workflow/nut_loi/ai_llm.py` (làn p7) đã ghi nó ra trước khi nó
kịp cắn:

    "CHƯA nối vào `cau_noi.nop_job`/`ap_ket_qua`: cầu nối job chung suy tên
     ToolSpec bằng `node["type"][4:]` (cắt đúng 4 ký tự cho tiền tố `"app."`)
     — áp trực tiếp cho `"ai.llm"` ra `"lm"`, vô nghĩa."

Số 4 là độ dài của `"app."`. Nó đúng cho **một** không gian tên và sai cho mọi
không gian khác — và cái sai ấy **không ném**: nó tra registry bằng `"lm"`,
không thấy, rồi báo `cong_cu_khong_con: 'lm'`. Thông điệp ấy **đổ lỗi cho
registry** cho một lỗi của chính cầu nối, và người đọc log sẽ đi tìm một tool
tên `"lm"` không bao giờ tồn tại.

⭐ Cùng hạng lỗi Task 4 đã đo: `core.if` qua đúng đường này thành `".if"`.

## ⛔ Vì sao KHÔNG tra ngược `job_type → tên tool`

Cách "thông minh" là: `ai.llm` khai `job_type="ltt_llm.chat"`, nên cứ tìm
`CongCu` nào có `job_type` ấy. **Đo rồi, không dùng được**: trong 19 tool của
registry hôm nay có **ba** `job_type` bị hai tool dùng chung
(`prompt_ai_ommi.generate`, `taoanh.generate`, `upscalevideo.render`). Một tra
ngược đúng hôm nay và sai vào đúng ngày ai đó thêm tool thứ hai trên
`ltt_llm.chat` — im lặng, và nó chọn tool nào thì tuỳ thứ tự dict.

⇒ Node `ai.*` phải **khai** ToolSpec nó bọc. Chưa có trường ấy, nên bản này
  làm đúng một việc: **ném to**, đúng tên loại node thật.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import pathlib

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


def _node_ai(nid: str = "a", loai: str = "ai.llm") -> dict:
    """Node `ai.*` đúng hình dạng đồ thị đã biên dịch (`thi_hanh="job"`)."""
    return {"id": nid, "type": loai, "type_version": 1,
            "params": {"prompt": "chao"}, "credential_ref": "",
            "settings": {}, "thi_hanh": "job", "gia_tran": 3}


# ── Việc A: ba node `ai.*` phải SỐNG trong sổ node lõi ──────────────────────

def test_A_ba_node_ai_da_duoc_khai_trong_so(db):
    """`ai_llm.py`/`ai_router.py` gọi `dang_ky` **lúc import**.

    Không ai import chúng thì chúng không tồn tại — palette không thấy, và
    `bien_dich._node_loi` báo `node_khong_ton_tai` cho một node đã được viết ra
    đầy đủ. Một mô-đun đăng ký mà không ai import là một mô-đun chết.
    """
    from platform_core.workflow import nut_loi
    so = nut_loi.tat_ca()
    for loai in ("ai.llm", "ai.extract", "ai.router"):
        assert loai in so, f"{loai} chua song trong nut_loi.tat_ca()"
    # Đối chứng: sổ không rỗng vì một lý do khác (vd import hỏng nuốt hết).
    assert len(so) >= 12, sorted(so)


# ── Việc B: cắt tiền tố TƯỜNG MINH ──────────────────────────────────────────

def test_B_doi_chung_node_app_van_ra_dung_ten_tool():
    """Nếu phép này đỏ thì bản sửa đã làm hỏng đường đang chạy thật."""
    from platform_core.workflow.cau_noi import ten_cong_cu
    assert ten_cong_cu("app.text.chat") == "text.chat"
    assert ten_cong_cu("app.video.render") == "video.render"


@pytest.mark.parametrize("loai", ["core.if", "core.foreach", "piece.slack",
                                  "ai.khong_co_that", "", "app.", "text.chat"])
def test_B_tien_to_la_thi_NEM_chu_khong_cat_bua(loai):
    """⛔ Loại node không `app.` và **không KHAI** `ten_toolspec` phải NÉM.

    ⚠️ `ai.llm`/`ai.extract`/`ai.router` **không** còn nằm trong danh sách này:
       từ `test_1789` chúng KHAI `ten_toolspec="text.chat"`, nên cầu nối đọc
       được chúng. Đó là tiến triển có chủ đích, không phải nới rào — rào nay
       là *"khai hay không khai"*, chặt hơn *"tiền tố nào"*.

    Đặc biệt `"app."` rỗng phần đuôi: cắt đúng 4 ký tự cho ra `""`, và `""`
    tra registry không thấy — lại một `cong_cu_khong_con: ''` đổ lỗi nhầm chỗ.
    """
    from platform_core.workflow.cau_noi import LoiTienTo, ten_cong_cu
    with pytest.raises(LoiTienTo) as e:
        ten_cong_cu(loai)
    assert loai in str(e.value) or not loai


def test_B_nop_job_loai_khong_doc_duoc_FAILED_co_TEN_THAT(db, run):
    """`nop_job` một node `piece.slack`: lỗi phải nói `piece.slack`.

    Bản cũ cắt 4 ký tự ⇒ `"e.slack"`, rồi `cong_cu_khong_con: 'e.slack'` —
    một cái tên chưa bao giờ tồn tại, và câu lỗi đổ lên đầu registry.
    """
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert cau_noi.nop_job(db, run, _node_ai(loai="piece.slack"),
                           cong_cu=CC) is None
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.execution_status == "FAILED"
    assert "piece.slack" in anh.error, anh.error
    # ⛔ Câu lỗi CŨ đổ lỗi cho registry bằng một tên bịa.
    # Ten BI CAT (dat trong nhay don) khong duoc xuat hien.
    assert "'e.slack'" not in anh.error and 'cong_cu_khong_con' not in anh.error


def test_B_ap_ket_qua_cung_noi_TEN_THAT(db, run, monkeypatch):
    """Cửa thứ hai (`ap_ket_qua`, dòng ~249) có **cùng** số cứng, cùng cách sai.

    Đối chứng của chính phép này: nó phải đi qua nhánh THẤT BẠI của
    `ap_ket_qua` — nếu node không vào được QUEUED thì phép kiểm không đo gì.
    """
    from platform_core import jobs
    from platform_core.models import Job, WorkflowVersion
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh

    # Nộp job bằng một node APP hợp lệ, rồi ĐỔI `type` trong đồ thị đã ghim
    # thành một loại cầu nối KHÔNG đọc nổi — đúng ca "node đã publish, rồi
    # định nghĩa của nó biến mất khỏi sổ".
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    v = db.get(WorkflowVersion, run.version_id)
    node_app = next(n for n in v.graph["nodes"] if n["id"] == "a")
    job = db.get(Job, cau_noi.nop_job(db, run, node_app, cong_cu=CC))
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"   # doi chung
    g = dict(v.graph)
    g["nodes"] = [dict(n) for n in g["nodes"]]
    next(n for n in g["nodes"] if n["id"] == "a")["type"] = "piece.slack"
    v.graph = g
    db.flush()

    jobs.fail(db, job, "provider hong", retry=False)
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "FAILED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert 'piece.slack' in anh.error and "'e.slack'" not in anh.error


# ── Bánh cóc ────────────────────────────────────────────────────────────────

def test_banh_coc_cau_noi_khong_con_so_cung_cat_tien_to():
    """⛔ Không thay `[4:]` bằng một số cứng khác — cấm mọi lát cắt hằng số.

    ⭐ Cắn thật: viết lại `ten_cong_cu` thành `loai[4:]` là đủ để nó đỏ (đã
       tiêm thử — xem báo cáo).

    Đối chứng: khẳng định tệp có thật và có hàm, để một đường dẫn sai không
    cho ra "0 lát cắt" rồi xanh giả.
    """
    import ast

    nguon = pathlib.Path("platform_core/workflow/cau_noi.py").read_text(
        encoding="utf-8")
    assert "def ten_cong_cu" in nguon and len(nguon) > 1000
    cay = ast.parse(nguon)
    xau = []
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Subscript) or \
                not isinstance(nut.slice, ast.Slice):
            continue
        lat = nut.slice
        # Cắt bằng một HẰNG SỐ (`x[4:]`) là thứ bị cấm; `x[len(TIEN_TO):]` thì
        # không — độ dài đọc từ chính chuỗi tiền tố nên không lệch được.
        if isinstance(lat.lower, ast.Constant) and \
                isinstance(lat.lower.value, int) and lat.lower.value != 0:
            xau.append(ast.unparse(nut))
    assert not xau, f"cat tien to bang so cung: {xau}"
