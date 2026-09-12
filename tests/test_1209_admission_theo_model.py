"""`AdmissionModel` + `ToolSpec.admission_cho()` — một tool, hai pool (multijob 2.1).

🔴 VÌ SAO: hôm nay `admission_resource/admission_slots/admission_token_pool` chỉ
tả được MỘT pool cho cả tool. `ltt_llm` sắp có hai model (`ltt-3.8`, `ltt-3.5`)
chạy trên hai pool KV khác nhau trên CÙNG một tool `text.chat` — cần một ánh xạ
theo model, không phải một bộ ba số tĩnh. Task 5.5 (ảnh) dùng khoá `"*"` để áp
một sức chứa cho MỌI model của tool, nên bộ kiểm ở đây phải chứng minh cả hai
nhánh (theo model cụ thể VÀ theo `"*"`) trước khi có tool thật nào dùng tới.

Dải test của chương trình multijob: 1200-1249 (Task 1.2).
"""
from __future__ import annotations

import dataclasses

import pytest

from typing import Any

from platform_core.registry import AdmissionModel, ToolSpec
from tests.conftest import mo_cu_tru_3090


def _tool(**overrides: Any) -> ToolSpec:
    base: dict[str, Any] = dict(
        name="test.tool",
        job_type="test.tool",
        description="tool test cho admission_cho",
        params_schema={"x": {"type": "string"}},
        returns={"y": "text"},
    )
    base.update(overrides)
    return ToolSpec(**base)


def test_anh_xa_theo_model_tra_dung_pool():
    """Mỗi model có resource/slots/pool riêng — đúng nhu cầu ltt-3.8 vs ltt-3.5."""
    tool = _tool(admission_theo_model={
        "ltt-3.8": AdmissionModel("llm_remote", 4, 1000, "rtx3090", "mac_dinh"),
        "ltt-3.5": AdmissionModel("llm_remote", 4, 500, "rtx3090", "mac_dinh"),
    })
    assert tool.admission_cho("ltt-3.8") == AdmissionModel(
        "llm_remote", 4, 1000, "rtx3090", "mac_dinh")
    assert tool.admission_cho("ltt-3.5") == AdmissionModel(
        "llm_remote", 4, 500, "rtx3090", "mac_dinh")


def test_wildcard_ap_dung_moi_model():
    """`"*"` là khoá áp cho MỌI model của tool (khuôn Task 5.5 — ảnh trên 3090)."""
    tool = _tool(admission_theo_model={
        "*": AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo"),
    })
    ky_vong = AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo")
    assert tool.admission_cho("bat_ky_model_nao") == ky_vong
    assert tool.admission_cho("mot_model_khac") == ky_vong
    assert tool.admission_cho("") == ky_vong


def test_model_la_khong_co_trong_anh_xa_va_khong_co_wildcard_thi_loi():
    """Model lạ, không có `"*"` để rơi về ⇒ `KeyError` — fail-closed, không im lặng."""
    tool = _tool(admission_theo_model={
        "ltt-3.8": AdmissionModel("llm_remote", 4),
    })
    with pytest.raises(KeyError):
        tool.admission_cho("ltt-3.5")


def test_tool_cu_chi_khai_admission_resource_slots_tuong_duong():
    """Tool cũ (trước 2.1) chỉ khai `admission_resource/slots[/token_pool]` —
    hành vi phải giữ nguyên, không phân biệt theo model."""
    tool = _tool(admission_resource="llm_remote", admission_slots=4,
                 admission_token_pool=262144)
    ky_vong = AdmissionModel("llm_remote", 4, 262144)
    assert tool.admission_cho() == ky_vong
    # Tool cũ không biết "model" là gì — mọi model đều nhận cùng một sức chứa.
    assert tool.admission_cho("bat_ky_model_nao") == ky_vong


def test_tool_cu_khong_token_pool_van_tuong_duong():
    """Nhánh cũ không khai `admission_token_pool` ⇒ mặc định 0, hành vi không đổi."""
    tool = _tool(admission_resource="ffmpeg", admission_slots=2)
    assert tool.admission_cho() == AdmissionModel("ffmpeg", 2, 0)


def test_tool_khong_khai_gi_tra_none():
    """Tool không khai admission gì ⇒ không có lease nào để giành — `None`."""
    tool = _tool()
    assert tool.admission_cho() is None
    assert tool.admission_cho("mot_model") is None


def test_doi_chung_bo_wildcard_lam_hong_ap_dung_moi_model(monkeypatch):
    """Đối chứng bắt buộc: tiêm bản `admission_cho` KHÔNG có nhánh `"*"` vào
    `ToolSpec`, rồi chứng minh ca 'wildcard áp mọi model' phải ĐỎ.

    Đây là phép kiểm cho chính bộ kiểm: nếu `test_wildcard_ap_dung_moi_model`
    xanh dù nhánh `"*"` bị rút ra, thì bộ kiểm đó không đo được cái nó tuyên bố
    đo — đúng bẫy "chốt không ghi vào cây" / "sự thật độc lập" đã gặp trước đây.
    """
    import platform_core.registry as registry

    def admission_cho_khong_wildcard(self, model: str = ""):
        m = self.admission_theo_model
        if m:
            if model in m:
                return m[model]
            # ⛔ Cố ý BỎ nhánh `if "*" in m: return m["*"]`.
            raise KeyError(
                f"{self.name}: model {model!r} khong co trong admission_theo_model")
        if self.admission_resource and self.admission_slots > 0:
            return registry.AdmissionModel(
                self.admission_resource, self.admission_slots,
                int(getattr(self, "admission_token_pool", 0) or 0))
        return None

    monkeypatch.setattr(registry.ToolSpec, "admission_cho",
                        admission_cho_khong_wildcard, raising=True)

    tool = _tool(admission_theo_model={
        "*": AdmissionModel("anh_3090", 1, 0, "rtx3090", "theo_lo"),
    })
    with pytest.raises(KeyError):
        tool.admission_cho("bat_ky_model_nao")


def test_catalog_khong_lo_admission_theo_model_ra_khach():
    """Chiếu catalog mang `admission_theo_model` để dùng nội bộ (giống
    `admission_token_pool`, `test_1201`), nhưng KHÔNG lộ nó ra `to_public_dict()`.
    """
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.public_api.catalog import project_tool

    goc = MANIFEST.tools[0]
    anh_xa = {
        "ltt-3.8": AdmissionModel("tn_bi_mat_lon", 4, 1000, "rtx3090", "mac_dinh"),
        "ltt-3.5": AdmissionModel("tn_bi_mat_nho", 4, 500, "rtx5060", "phu"),
    }
    tool_moi = dataclasses.replace(goc, admission_theo_model=anh_xa)

    projected = project_tool(MANIFEST, tool_moi)
    assert projected.admission_theo_model == anh_xa
    cong_khai = projected.to_public_dict()
    assert "admission_theo_model" not in cong_khai
    # ⚠️ DÒ BẰNG **GIÁ TRỊ**, KHÔNG BẰNG KHOÁ. Trước 2.3 phép kiểm này dò
    #    `"ltt-3.8" not in str(...)` — và từ 2.3 `ltt-3.8` là một bí danh **được
    #    công bố**, nên phép dò ấy đỏ vì đúng thứ đáng lẽ phải có mặt. Thứ không
    #    được rò là **tên tài nguyên và nhóm cư trú** nội bộ.
    for bi_mat in ("tn_bi_mat_lon", "tn_bi_mat_nho", "rtx3090", "rtx5060"):
        assert bi_mat not in str(cong_khai), (
            f"ban chieu cong khai dang lo metadata van hanh: {bi_mat}")


# ═══════════════════════════════════════════════════════════════════════════
# multijob 2.2 — MỌI CỬA đi qua `admission_cho(model)`
#
# Ba lớp kiểm, và chúng đo ba thứ khác nhau:
#
#   A. TĨNH (AST)  — không cửa nào còn đọc thẳng bộ ba tĩnh của tool.
#   B. HÀNH VI     — cửa job giành lease trên ĐÚNG tài nguyên của model nó xin.
#   C. ĐỐI CHỨNG   — model không có trong bản khai ⇒ lỗi có tên, KHÔNG phải 500.
#
# ⚠️ A một mình là xanh rỗng: một tệp có thể sạch `admission_resource` mà vẫn
#    giành sai pool. B một mình cũng không đủ: nó chỉ đi qua cửa job. Cần cả ba.
# ═══════════════════════════════════════════════════════════════════════════

import ast
import pathlib
import uuid

_GOC = pathlib.Path(__file__).resolve().parents[1]

#: Bảy tệp Task 2.2 rewire. Không quét cả kho: `registry.py` PHẢI đọc bộ ba tĩnh
#: (nó là nơi định nghĩa nhánh tương thích), `catalog.py` phải chiếu chúng, và
#: các app khai chúng trong manifest — cả ba đều hợp lệ.
_TEP_CUA = (
    "server/api/chat.py",
    "server/api/streaming.py",
    "platform_core/runtime_noi_bo/luong.py",
    "platform_core/job_runner.py",
    "platform_core/llm/canonical.py",
    "platform_core/agent/planner.py",
    "platform_core/image_gen/dich_llm.py",
)

_TRUONG_CAM = frozenset({"admission_resource", "admission_slots",
                         "admission_token_pool"})

#: Cột CSDL của hàng `jobs`, KHÔNG phải bản khai của tool. Hàng đợi
#: (`platform_core/jobs.py`, `job_scheduler.py`) đếm sức chứa bằng đúng hai cột
#: này, nên `job_runner` còn được đọc chúng **trên một hàng Job**. Thứ 2.2 cấm
#: là đọc chúng trên một **tool**.
_TEN_HANG_JOB = frozenset({"job", "Job", "peer", "candidate", "row",
                           "job_entity"})


def _goc_ten(node) -> str:
    """Tên biến gốc của một chuỗi thuộc tính: `a.b.c` -> `"a"`. `""` nếu không có."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else ""


def _vi_pham(duong_dan: pathlib.Path) -> list:
    """Mọi chỗ đọc bộ ba tĩnh trên một tool trong MỘT tệp. `[(dòng, cách đọc)]`.

    🔴 ĐỌC AST, KHÔNG QUÉT VĂN BẢN — và ở đây lý do không phải "tránh phạt phần
       giải thích", mà là **đúng/sai**: `getattr(tool, "admission_resource", "")`
       là một `Call`, không phải `Attribute`. Một bộ dò chỉ nhìn `Attribute` sẽ
       bỏ lọt **đúng khuôn mà mã trước 2.2 dùng ở mọi cửa** — tức nó xanh ngay
       cả khi chưa ai sửa gì. Nên phải bắt CẢ HAI hình dạng.
    """
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"))
    thay = []
    for node in ast.walk(cay):
        if isinstance(node, ast.Attribute) and node.attr in _TRUONG_CAM:
            if _goc_ten(node.value) in _TEN_HANG_JOB:
                continue
            thay.append((node.lineno, _goc_ten(node.value) + "." + node.attr))
        elif (isinstance(node, ast.Call)
              and isinstance(node.func, ast.Name) and node.func.id == "getattr"
              and len(node.args) >= 2
              and isinstance(node.args[1], ast.Constant)
              and node.args[1].value in _TRUONG_CAM):
            if _goc_ten(node.args[0]) in _TEN_HANG_JOB:
                continue
            thay.append((node.lineno,
                         'getattr(..., "' + str(node.args[1].value) + '")'))
    return thay


@pytest.mark.parametrize("ten_tep", _TEP_CUA)
def test_cua_khong_con_doc_thang_bo_ba_tinh(ten_tep):
    """Mọi cửa hỏi bản khai bằng `admission_cho(model)`, không bằng ba trường tĩnh.

    Bộ ba `admission_resource/slots/token_pool` tả được đúng MỘT pool. Một cửa
    còn đọc thẳng chúng sẽ giành tài nguyên của model *khác* ngay khi `text.chat`
    khai hai model (Task 2.3) — và giành sai pool không bảo vệ gì cả.
    """
    vi_pham = _vi_pham(_GOC / ten_tep)
    assert vi_pham == [], (
        ten_tep + " con doc thang ban khai admission cua tool: " + str(vi_pham))


def test_doi_chung_bo_do_tinh_bat_duoc_ca_getattr(tmp_path):
    """Đối chứng cho chính bộ dò: tiêm lại HAI khuôn của mã trước 2.2 ⇒ phải ĐỎ.

    Khuôn `getattr` là khuôn **thật** mà `streaming.py`/`luong.py` dùng trước
    2.2. Nếu bộ dò chỉ thấy khuôn dấu chấm thì nó xanh mà chẳng đo được gì.
    """
    cu = tmp_path / "cua_cu.py"
    cu.write_text(
        "def f(tool, job):\n"
        "    a = tool.admission_resource\n"
        '    b = int(getattr(tool, "admission_token_pool", 0) or 0)\n'
        "    c = job.admission_slots      # hang Job - HOP LE, khong tinh\n"
        "    return a, b, c\n", encoding="utf-8")
    thay = _vi_pham(cu)
    assert [t[1] for t in thay] == ["tool.admission_resource",
                                    'getattr(..., "admission_token_pool")']


# ── B. Hành vi: cửa job giành lease theo model trong `params` ────────────────

@pytest.fixture()
def db_job(tmp_path, monkeypatch):
    """SQLite sạch + phiên, khuôn `test_151`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "ad.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    # Luật 0 của admission (dual-model 5.3): một CSDL mới chưa nói card
    # 3090 đang là của ai, và fail-closed nghĩa là cửa LTT-3.8 đóng. Cửa
    # này là thứ tệp test đang kiểm, nên nó phải nói ra — như production.
    mo_cu_tru_3090()
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


#: Bản khai vứt đi, HAI model trên HAI tài nguyên. Cố ý **không** dùng tên thật
#: (`ltt_35_5060`/`ltt_38_3090`): tới Task 2.3 mới đổi tên model công khai, và
#: một phép kiểm ghim vào tên chưa tồn tại là một phép kiểm đo tương lai.
_HAI_MODEL = {
    "ltt-3.5": AdmissionModel("tn_nho_thu", 2, 111),
    "ltt-3.8": AdmissionModel("tn_lon_thu", 1, 222),
}


def _tool_hai_model(job_type: str, anh_xa=None) -> ToolSpec:
    return _tool(name="thu.chat", job_type=job_type,
                 admission_theo_model=dict(
                     _HAI_MODEL if anh_xa is None else anh_xa))


def _chay_job_voi_model(db, monkeypatch, model: str, anh_xa=None):
    """Nộp một job `params={"model": model}`, chạy nó, trả danh sách lease mà
    worker thật sự giành — đọc ở PHIÊN KHÁC, lúc handler đang chạy.
    """
    import platform_core.job_runner as jr
    from platform_core.jobs import submit
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG

    monkeypatch.setattr(jr, "_tool_cua_job",
                        lambda jt: _tool_hai_model(jt, anh_xa))
    thay = {}

    def _handler(params, ctx):
        # `hold_persisted` commit lease ở phiên RIÊNG ⇒ phiên khác đọc thấy.
        import platform_core.db as dbmod
        from platform_core.models import ExecutionLease
        g = dbmod.get_session()
        s = next(g)
        try:
            thay["lease"] = [(v.resource, v.token_dat_truoc)
                             for v in s.query(ExecutionLease).all()]
        finally:
            s.close()
        return {"ok": True}

    monkeypatch.setattr(jr.jobq, "resolve_handler", lambda jt: _handler)
    # ⛔ Nộp KHÔNG kèm `admission_resource`: trước 2.2 worker đọc hai cột ấy của
    #    hàng Job, nên để rỗng thì bản cũ giành 0 lease — đối chứng nằm sẵn
    #    trong chính phép kiểm.
    submit(db, user_id="u-ad", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
           params={"text": "xin chao", "model": model})
    db.commit()
    assert jr._chay_mot_job("w-ad") is True
    return thay.get("lease")


#: `token_dat_truoc` = CẢ POOL của model ấy, vì tool vứt đi này không có
#: `sync_executor` nên `_luat_cho_job` không ước được token và đi đúng đường
#: AN TOÀN đã ghi trong docstring của nó. Nhờ vậy phép kiểm đo được **cả**
#: `resource` lẫn `token_pool` — hai nửa của `AdmissionModel` mà 2.2 phải
#: lấy theo model, chứ không chỉ cái tên tài nguyên.
@pytest.mark.parametrize("model,mong_doi", [
    ("ltt-3.5", ("tn_nho_thu", 111)),
    ("ltt-3.8", ("tn_lon_thu", 222)),
])
def test_job_giu_lease_tren_tai_nguyen_CUA_MODEL_no_xin(db_job, monkeypatch,
                                                       model, mong_doi):
    """Hai model của CÙNG một tool ⇒ hai lease trên hai tài nguyên khác nhau.

    Đây là toàn bộ lý do `admission_theo_model` tồn tại: `ltt-3.8` (3090) và
    `ltt-3.5` (5060 Ti) không dùng chung một pool KV, nên đếm chung là đếm sai.
    """
    from platform_core.models import Job

    assert _chay_job_voi_model(db_job, monkeypatch, model) == [mong_doi]
    # 🔴 ĐỐI CHỨNG NẰM TRONG CHÍNH PHÉP KIỂM. Hai cột cũ của hàng `jobs` RỖNG,
    #    nên bản trước 2.2 — đọc `job.admission_resource`/`job.admission_slots` —
    #    đi thẳng vào `nullcontext` và giành **0 lease**. Lease ở trên chỉ có
    #    một nguồn gốc khả dĩ: bản khai theo model của tool.
    job = db_job.query(Job).one()
    assert (job.admission_resource, job.admission_slots) == ("", 0)


def test_job_xin_model_KHONG_co_trong_ban_khai_thi_hong_HAN_khong_no_500(
        db_job, monkeypatch):
    """Fail-closed, và fail MỘT LẦN.

    `KeyError` của `admission_cho` là "bản khai và yêu cầu không khớp" — một
    trạng thái vĩnh viễn. Hai kết cục sai đều đã cân nhắc:

      * để `KeyError` thoát ⇒ worker vỡ giữa vòng lặp, job kẹt `running`;
      * `_tra_ve_hang_doi` ⇒ job quay lại hàng đợi mãi mãi, tiêu một slot claim
        mỗi vòng và không bao giờ khá hơn.

    Kết cục đúng: `error`, không thử lại, KHÔNG lease nào, và handler KHÔNG chạy
    (chạy mà chưa giành suất là đúng cái lỗ `admission` sinh ra để bịt).
    """
    from platform_core.models import JOB_ERROR, ExecutionLease, Job

    lease = _chay_job_voi_model(db_job, monkeypatch, "ltt-9.9-khong-ton-tai")
    assert lease is None, "handler da chay du chua gianh duoc suat nao"
    db_job.expire_all()
    job = db_job.query(Job).one()
    assert job.status == JOB_ERROR
    assert db_job.query(ExecutionLease).count() == 0

def test_tool_khong_khai_gi_thi_BAN_CHUP_LUC_NOP_van_la_cau_tra_loi(
        db_job, monkeypatch):
    """Tool không khai admission ⇒ hai cột của hàng `jobs` VẪN cầm quyền.

    🔴 ĐÂY LÀ MỘT CHỐT AN TOÀN THẬT, KHÔNG PHẢI TƯƠNG THÍCH NGƯỢC CHO VUI.
       `auto_scan_video` khai sức chứa theo **giai đoạn pipeline**, không theo
       tool — manifest của nó viết thẳng lý do: tài nguyên là thuộc tính của một
       *lần chạy*, không phải của cả app. Giai đoạn `tach_nguon_cuc_bo` chạy
       `demucs` với `suat=1`, và một bản 2.2 coi bản khai của tool là câu trả
       lời DUY NHẤT sẽ cho giai đoạn ấy chạy **không lease** ⇒ nhiều `demucs`
       cùng lúc. Đó là sự cố đã thật sự làm máy chết (CLAUDE.md máy: 12 tiến
       trình `demucs`, mỗi cái 460–984% CPU).

    ⇒ Luật hai nhánh: tool khai gì thì tool thắng (theo model); tool không khai
      gì thì bản chụp lúc nộp thắng. Phép kiểm này canh nhánh thứ hai.
    """
    import platform_core.job_runner as jr
    from platform_core.jobs import submit
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG

    # Tool KHÔNG khai admission — đúng hình dạng ToolSpec của ASV.
    monkeypatch.setattr(jr, "_tool_cua_job", lambda jt: _tool(job_type=jt))
    thay = {}

    def _handler(params, ctx):
        import platform_core.db as dbmod
        from platform_core.models import ExecutionLease
        g = dbmod.get_session()
        s = next(g)
        try:
            thay["lease"] = [(v.resource, v.slot is not None)
                             for v in s.query(ExecutionLease).all()]
        finally:
            s.close()
        return {"ok": True}

    monkeypatch.setattr(jr.jobq, "resolve_handler", lambda jt: _handler)
    submit(db_job, user_id="u-asv", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
           params={"text": "xin chao"},
           admission_resource="tach_nguon_thu", admission_slots=1)
    db_job.commit()
    assert jr._chay_mot_job("w-asv") is True
    assert thay.get("lease") == [("tach_nguon_thu", True)]


# ── C. Đối chứng ở CỬA ĐỒNG BỘ (đường tiền) ─────────────────────────────────

def test_cua_dong_bo_tra_4xx_chu_khong_phai_500_khi_ban_khai_thieu_model(
        tmp_path, monkeypatch):
    """Cửa `/chat/completions` gặp bản khai thiếu model ⇒ lỗi CÓ TÊN, không 500.

    🔴 VÌ SAO ĐO Ở CỬA TIỀN. `admission_cho` fail-closed bằng `KeyError`; một
       `KeyError` trần thoát ra khỏi route là `500`, và `500` ở đây tệ gấp đôi:
       khách không biết phải làm gì, còn ta thì mất luôn thông tin rằng bản khai
       lệch. Phép kiểm này chốt rằng cửa **dịch** lỗi ấy chứ không để nó rơi.

    ⛔ Và chốt luôn bất biến tiền của Task 1.5: lỗi xảy ra TRƯỚC
       `idempotency.begin`, nên không bản ghi idempotency nào và không bút toán
       nào ra đời.
    """
    import dataclasses as _dc

    from fastapi.testclient import TestClient

    from platform_core.public_api import keys as devkeys
    from platform_core.public_api import limits
    from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE,
                                                 SCOPE_JOBS_READ,
                                                 SCOPE_TOOLS_READ)
    from server.api.inventory import API_V1_PREFIX

    pepper = "ad-test-pepper-" + "d" * 40
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "cua.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, pepper)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    # Luật 0 của admission (dual-model 5.3): một CSDL mới chưa nói card
    # 3090 đang là của ai, và fail-closed nghĩa là cửa LTT-3.8 đóng. Cửa
    # này là thứ tệp test đang kiểm, nên nó phải nói ra — như production.
    mo_cu_tru_3090()

    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db,
                              email="ad-" + uuid.uuid4().hex[:8] + "@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, 10_000, by="test")
        _k, token = devkeys.issue(
            db, user_id=user.id,
            scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ),
            env={devkeys.PEPPER_ENV: pepper})
        db.commit()
        user_id = user.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # Bản khai chỉ phục vụ MỘT model lạ ⇒ model khách xin không có, và không có
    # `"*"` để rơi về.
    import server.api.chat as chat_mod
    goc_build = chat_mod.build_catalog

    def build_lech(config):
        return [_dc.replace(t, admission_theo_model={
                    "mot-model-khac": AdmissionModel("tn_khac", 1, 0)})
                if t.name == "text.chat" else t
                for t in goc_build(config)]

    monkeypatch.setattr(chat_mod, "build_catalog", build_lech)

    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "ad-secret-value-here",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "text.chat",
        "LTT_PUBLIC_API_RPM": "600",
    })
    try:
        with TestClient(app, base_url="https://testserver",
                        raise_server_exceptions=False) as client:
            r = client.post(
                API_V1_PREFIX + "/chat/completions",
                headers={"Authorization": "Bearer " + token,
                         "Idempotency-Key": uuid.uuid4().hex},
                # 🔴 MODEL **HỢP LỆ** (`ltt-3.8`), bản khai admission thì thiếu.
                #    Từ 2.3 cửa có một chốt TÊN chạy trước (`kiem_ten_model`),
                #    nên xin một tên đã cắt (`ltt_llm`) sẽ dừng ở chốt ấy và
                #    phép kiểm này lặng lẽ thôi đo đường `KeyError` mà nó sinh
                #    ra để đo — xanh, và rỗng.
                json={"model": "ltt-3.8", "max_tokens": 100,
                      "messages": [{"role": "user", "content": "xin chao"}]})
        assert r.status_code != 500, r.text
        assert 400 <= r.status_code < 500, r.text

        from platform_core.models import CreditEntry
        from platform_core.public_api.tables import ApiIdempotencyRecord
        gen2 = dbmod.get_session()
        db2 = next(gen2)
        try:
            assert db2.query(ApiIdempotencyRecord).count() == 0, (
                "loi xay ra sau `idempotency.begin` - ban ghi treo lai")
            assert db2.query(CreditEntry).filter(
                CreditEntry.user_id == user_id).count() == 1, (
                "chi con dong nap tay ban dau moi duoc ton tai")
        finally:
            db2.close()
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        limits.reset()
        dbmod.reset_engine()


# ── Bánh cóc: tool khai TĨNH với `slots = 0` vẫn phải giữ LỚP TÀI NGUYÊN ─────
#
# 🔴 MỘT HỒI QUY ĐÃ XẢY RA THẬT, ở HAI chỗ, và một ghi chú "đã đo" nói sai về nó.
#
#    `suc_chua_admission` trả `None` cho tool khai `admission_resource` mà
#    `admission_slots == 0` — nhánh 2 của nó đòi `slots > 0`. Đó là câu trả lời
#    ĐÚNG cho câu hỏi *"tool này giành mấy suất lease?"* (không suất nào).
#
#    Nhưng hai chỗ gọi lại dùng nó để trả lời một câu KHÁC: *"job này thuộc lớp
#    tài nguyên nào?"* — và rơi về `"api"` khi nhận `None`:
#
#        platform_core/public_api/invocation.py   cột `Job.admission_resource`
#        server/api/jobs.py::_resource_of         khoá tra `class_concurrency`
#
#    `image.upscale`/`video.upscale` đúng hình dạng ấy (`resource="gpu"`,
#    `slots=0`): chúng **chụp sức chứa theo giai đoạn**. Nên
#    `LTT_PUBLIC_API_CLASS_CONCURRENCY="gpu:1"` thôi gác — job GPU thứ hai vào
#    được (201) thay vì bị chặn (429).
#
# ⭐ Hai ca dưới KHÔNG kiểm `suc_chua_admission` (nó vẫn đúng khi trả `None`);
#    chúng kiểm rằng HAI CHỖ GỌI không đánh mất bản khai tĩnh. Một phép kiểm đặt
#    ở `suc_chua_admission` sẽ ép sửa nhầm chỗ.


# ── Bánh cóc: tool khai TĨNH với `slots = 0` vẫn phải giữ LỚP TÀI NGUYÊN ─────
#
# 🔴 MỘT HỒI QUY ĐÃ XẢY RA THẬT, VÀ MỘT BẢN SỬA SAI TẦNG.
#
#    `suc_chua_admission` trả `None` cho tool khai `admission_resource` mà
#    `admission_slots == 0` — nhánh 2 của nó đòi `slots > 0`. Đó là câu trả lời
#    ĐÚNG cho câu hỏi *"tool này giành mấy suất lease?"* (không suất nào).
#
#    Nhưng `admission_luc_nop` trả lời một câu KHÁC — *"job này thuộc lớp tài
#    nguyên nào?"* — và trước 12/09 nó rơi thẳng về `mac_dinh`. Với cửa công
#    khai `mac_dinh="api"`, nên cột `Job.admission_resource` của một job
#    `image.upscale` (`resource="gpu"`, `slots=0`: **chụp sức chứa theo giai
#    đoạn**) mang `"api"`. `limits.active_job_count(resource="gpu")` đếm 0, và
#    `LTT_PUBLIC_API_CLASS_CONCURRENCY="gpu:1"` thôi gác.
#
# ⚠️ BẢN SỬA ĐẦU CỦA TÔI ĐẶT SAI CHỖ: truyền `getattr(tool,
#    "admission_resource")` làm `mac_dinh` ngay tại `invocation.py`.
#    `test_1210::test_cho_nop_khong_con_doc_bo_ba_tinh` bắt đúng — hai đường nộp
#    **không được** đọc bộ ba tĩnh. Bánh cóc ấy chỉ đường về `registry`, nơi bộ
#    ba tĩnh vốn đã được đọc một lần, và sửa ở đó chữa cho **cả hai** cửa.
#
# ⭐ NÊN HAI CA DƯỚI GHIM BẤT BIẾN, KHÔNG GHIM CÁCH HIỆN THỰC. Bản trước của
#    chúng ghim đúng cái `mac_dinh` mà bản sửa đúng đã xoá — tức chúng cưỡng chế
#    một chi tiết, và chi tiết ấy sai.

def test_ban_khai_TINH_thang_mac_dinh_du_slots_bang_0():
    """`mac_dinh` KHÔNG được che lớp tài nguyên mà tool đã tự khai."""
    from platform_core.registry import admission_luc_nop, suc_chua_admission

    tool = _tool(admission_resource="gpu", admission_slots=0)
    # Tiền đề: đúng là `None`, và đó KHÔNG phải lỗi — xem khối trên.
    assert suc_chua_admission(tool, "") is None

    # Bất biến: bản khai thắng, **bất kể** `mac_dinh` là gì.
    assert admission_luc_nop(tool, {}, mac_dinh="api") == ("gpu", 0)
    assert admission_luc_nop(tool, {}, mac_dinh="") == ("gpu", 0)
    assert admission_luc_nop(tool, {}, mac_dinh="ffmpeg") == ("gpu", 0)

    # ⛔ ĐỐI CHỨNG: `mac_dinh` vẫn phải còn tác dụng cho tool KHÔNG khai gì —
    #    nếu không thì bản sửa đã đi quá xa và nuốt cả đường cũ.
    assert admission_luc_nop(_tool(), {}, mac_dinh="api") == ("api", 0)
    assert admission_luc_nop(_tool(), {}, mac_dinh="gpu") == ("gpu", 0)


def test_hai_cua_hoi_admission_luc_nop_chu_khong_tu_roi_ve():
    """Chốt TĨNH (AST): `server/api/jobs.py` đi qua `admission_luc_nop`.

    🔴 Lớp tài nguyên dùng lúc **xét nhận** và lớp ghi vào **cột** phải là một.
       Trước 12/09 `_resource_of` chép riêng phép rơi-về của nó và trả `"api"`,
       trong khi cột mang một giá trị khác — hai câu trả lời cho một câu hỏi.

    ⚠️ Đọc AST chứ không quét văn bản: chuỗi `admission_resource` xuất hiện hợp
       lệ nhiều lần trong tệp (chú thích kể lại chính lỗi này). Thứ phải chốt là
       **có một lời gọi `admission_luc_nop`**, một mệnh đề DƯƠNG — nên xoá lời
       gọi đi là ca này đỏ, đúng khuôn `banh-coc-do-su-vang-mat`.
    """
    import ast as _ast
    import pathlib as _pl

    goc = _pl.Path(__file__).resolve().parents[1]
    cay = _ast.parse((goc / "server" / "api" / "jobs.py").read_text(encoding="utf-8"))
    goi = [n.lineno for n in _ast.walk(cay)
           if isinstance(n, _ast.Call)
           and (getattr(n.func, "id", "") or getattr(n.func, "attr", "")) == "admission_luc_nop"]
    assert goi, (
        "`server/api/jobs.py` khong con goi `admission_luc_nop` — nghia la no "
        "tu roi ve mot lop tai nguyen rieng, va lop ay se lech voi cot "
        "`Job.admission_resource` dung nhu hoi quy 12/09 (`test_188`).")
