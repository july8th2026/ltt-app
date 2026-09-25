"""`cau_noi.giai_tham_so` giải được ĐÚNG tập biểu thức mà `_doi` publish nhận
(plan `docs/superpowers/plans/2026-09-25-wf-v2-VAN-HANH.md` §P-B, làn wfb5,
round 2 — sau khi chủ dự án từ chối gộp round 1 vì lộ đúng chỗ này).

## Chuyện đã xảy ra (không suy diễn, đọc log điều phối)

Round 1 nối `bien_dich._doi` (cổng publish node app/tool) với ngôn ngữ §6 đầy
đủ — publish CHẤP NHẬN `{{ nodes.a.output.json.prompt }}` (đường dẫn LỒNG).
Nhưng `cau_noi.giai_tham_so` (thay giá trị THẬT lúc job chạy — đường tiền)
KHÔNG đổi: nó chỉ khớp `la_tham_chieu` (regex một-đoạn), không khớp thì
`_giai()` cũ TRẢ NGUYÊN VĂN chuỗi `"{{ nodes.a.output.json.prompt }}"` —
một node sinh video thật sẽ nhận đúng chuỗi mẫu CHƯA THAY làm "prompt". Tiền
thật, kết quả sai, không một dòng lỗi. Chủ dự án từ chối gộp round 1 chính
vì phát hiện này — publish RỘNG hơn RUNTIME giải được là fail-OPEN.

## Round 2 — hai việc khớp nhau

1. `bien_dich._NAMESPACE_APP_TOOL` hẹp cổng publish còn ĐÚNG namespace
   `nodes` (xem `test_4201::test_namespace_khac_nodes_van_bi_tu_choi_o_publish`).
2. `cau_noi._giai_bieu_thuc_s6` (tệp này) GIẢI được đúng tập đó — dùng LẠI
   `bien_dich.trich_tham_chieu` (AST, đã có) + `chinh_sach.moi_truong_wf` +
   `ngon_ngu.tinh` (ngôn ngữ §6, đã có) — KHÔNG một bộ đọc đường dẫn thứ hai.

⛔ Test dưới đây dựng `WorkflowRun`/`NodeRunSnapshot` THẬT qua đúng đường sản
xuất (`dinh_nghia.xuat_ban_draft` → `tao_run.tao_run` → `cau_noi.nop_job` →
`jobs.complete` → `cau_noi.ap_ket_qua`) — KHÔNG mock `giai_tham_so` hay tự
tạo `NodeRunSnapshot` tay, để phép kiểm chứng minh đúng đường thi hành thật,
không phải một đơn vị bị cô lập khỏi ngữ cảnh của nó.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from platform_core.workflow.cong_cu import CongCu

# `http.fetch` trả một OBJECT (`json`) — cần cho ca LỒNG (`.output.json.prompt`).
# `video.generate` chỉ để có một node app/tool THỨ HAI đọc tham chiếu.
CC = {
    "http.fetch": CongCu(ten="http.fetch", app_slug="ltt_llm",
                        job_type="ltt_llm.fetch", type_version=1,
                        params_schema={}, side_effect="external",
                        idempotency_fields=(), tinh_gia=lambda p: 1,
                        returns={"json": "object"}),
    "video.generate": CongCu(ten="video.generate", app_slug="ltt_llm",
                             job_type="ltt_llm.video", type_version=1,
                             params_schema={}, side_effect="external",
                             idempotency_fields=(), tinh_gia=lambda p: 2,
                             returns={"video_key": "text"}),
}


def _draft(db, params_b):
    from platform_core.workflow import dinh_nghia
    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="t-4202")
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "http.fetch", "params": {}}},
        {"id": "b", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "video.generate", "params": params_b}}],
        "edges": [{"id": "e", "source_node": "a", "target_node": "b",
                   "source_port": "json", "target_port": "in", "kind": "DATA"}]}]}
    dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
    return wf


@pytest.fixture()
def run_long(db):
    """`b.prompt` = `{{ nodes.a.output.json.prompt }}` — ca LỒNG của FLOW G."""
    from platform_core import credit
    from platform_core.workflow import dinh_nghia, tao_run
    wf = _draft(db, {"prompt": "{{ nodes.a.output.json.prompt }}"})
    v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu=CC)
    wf.published_version_id = v.id
    credit.nap(db, "u1", 100, note="test")
    db.flush()
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k-long")
    return r


def _node(db, run, nid):
    from platform_core.models import WorkflowVersion
    g = db.get(WorkflowVersion, run.version_id).graph
    return next(n for n in g["nodes"] if n["id"] == nid)


def _hoan_thanh_a(db, run, output):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, output)
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "SUCCEEDED"


# ── (a) Round-trip THẬT: publish qua, runtime thay đúng giá trị ────────────

def test_publish_qua_VA_runtime_thay_dung_gia_tri_that(db, run_long):
    """⭐ Phép kiểm trung tâm của round 2. `run_long` (fixture) đã CHỨNG MINH
    vế PUBLISH (nếu `xuat_ban_draft` ném, fixture đã đỏ trước khi vào đây)."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt

    _hoan_thanh_a(db, run_long,
                 {"json": {"prompt": "ve mot con meo", "khac": 1}})
    mtt.chuyen_node(db, run_long.id, "b", sang="READY", mo_ta="t")
    jb = db.get(Job, cau_noi.nop_job(db, run_long, _node(db, run_long, "b"),
                                     cong_cu=CC))
    assert jb.params["prompt"] == "ve mot con meo"


def test_bieu_thuc_co_ham_s6_cung_giai_duoc(db):
    """`{{ upper(nodes.a.output.json.prompt) }}` — round 2 KHÔNG hẹp bảng
    hàm §6.3, chỉ hẹp namespace (xem `test_4201`)."""
    from platform_core import credit
    from platform_core.workflow import cau_noi, dinh_nghia, tao_run

    wf = _draft(db, {"prompt": "{{ upper(nodes.a.output.json.prompt) }}"})
    v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu=CC)
    wf.published_version_id = v.id
    credit.nap(db, "u1", 100, note="test")
    db.flush()
    run, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                             trigger_kind="manual", idempotency_key="k-ham")
    _hoan_thanh_a(db, run, {"json": {"prompt": "ve mot con meo"}})
    ra = cau_noi.giai_tham_so(
        db, run.id, {"prompt": "{{ upper(nodes.a.output.json.prompt) }}"})
    assert ra == {"prompt": "VE MOT CON MEO"}


# ── (b) Node chưa SUCCEEDED — vẫn báo dau_vao_sai như cũ ────────────────────

def test_node_chua_succeeded_van_bao_dau_vao_sai(db, run_long):
    from platform_core.workflow import cau_noi

    with pytest.raises(cau_noi.LoiThamSo) as e:
        cau_noi.giai_tham_so(
            db, run_long.id,
            {"prompt": "{{ nodes.a.output.json.prompt }}"})
    assert e.value.ma == "dau_vao_sai"


def test_node_dang_chay_chua_xong_van_bao_dau_vao_sai(db, run_long):
    """`a` đã QUEUED (có ảnh chụp) nhưng chưa SUCCEEDED — khác ca (b) ở trên
    (chưa có ảnh chụp nào), cùng mã lỗi."""
    from platform_core.workflow import cau_noi, may_trang_thai as mtt

    mtt.chuyen_node(db, run_long.id, "a", sang="READY", mo_ta="t")
    cau_noi.nop_job(db, run_long, _node(db, run_long, "a"), cong_cu=CC)
    with pytest.raises(cau_noi.LoiThamSo) as e:
        cau_noi.giai_tham_so(
            db, run_long.id,
            {"prompt": "{{ nodes.a.output.json.prompt }}"})
    assert e.value.ma == "dau_vao_sai"


# ── Ba tên khoá `status`/`output`/`error` — chốt ĐÚNG, không suy đoán ──────
#
# 🔴 Đây là chỗ chủ dự án cảnh báo: `_MatNode` đọc `ban_ghi.get("status")`
#   bằng `.get()` — gõ sai tên khoá KHÔNG ném lỗi, nó chỉ âm thầm trả `None`
#   rồi bị hiểu là "chưa SUCCEEDED"/rỗng. Ba phép dưới đây dùng BA đường khác
#   nhau (`.status` trên node SUCCEEDED, `.output.<cổng>` trên node
#   SUCCEEDED, `.error` trên node FAILED) — nếu một tên khoá sai, ĐÚNG MỘT
#   trong ba bài này đỏ (không phải cả ba), nên không con nào đứng một mình
#   là đủ.

def test_ten_khoa_status_dung(db, run_long):
    from platform_core.workflow import cau_noi

    _hoan_thanh_a(db, run_long, {"json": {"prompt": "x"}})
    assert cau_noi.giai_tham_so(
        db, run_long.id, {"x": "{{ nodes.a.status }}"}) == {"x": "SUCCEEDED"}


def test_ten_khoa_output_dung(db, run_long):
    from platform_core.workflow import cau_noi

    _hoan_thanh_a(db, run_long, {"json": {"prompt": "x"}})
    assert cau_noi.giai_tham_so(
        db, run_long.id,
        {"x": "{{ nodes.a.output.json.prompt }}"}) == {"x": "x"}


def test_ten_khoa_error_dung(db, run_long):
    """`error` — namespace chưa test ở đâu khác trong tệp này. Node `a` FAIL
    với một thông điệp cụ thể; đọc lại đúng thông điệp đó qua `nodes.a.error`
    chứng minh khoá `"error"` (không phải `error_message` hay tên cột nào
    khác trên `NodeRunSnapshot`) được đọc đúng."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt

    mtt.chuyen_node(db, run_long.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run_long, _node(db, run_long, "a"),
                                      cong_cu=CC))
    jobs.fail(db, job, "loi_gia_lap_4202", retry=False)
    assert cau_noi.ap_ket_qua(db, run_long, "a", cong_cu=CC) == "FAILED"
    ra = cau_noi.giai_tham_so(db, run_long.id, {"e": "{{ nodes.a.error }}"})
    assert "loi_gia_lap_4202" in ra["e"]


# ── (c) Output tràn artifact — vẫn báo dau_ra_tran_artifact ─────────────────

@pytest.fixture()
def kho_tam(tmp_path, monkeypatch):
    from platform_core import storage as st
    st.set_storage(st.LocalStorage(str(tmp_path / "kho")))
    yield
    st.set_storage(None)


def test_output_tran_artifact_van_bao_dung_ma_qua_bieu_thuc_long(
        db, run_long, kho_tam):
    from platform_core.workflow import cau_noi

    _hoan_thanh_a(db, run_long, {"json": "x" * (300 * 1024)})
    with pytest.raises(cau_noi.LoiThamSo) as e:
        cau_noi.giai_tham_so(
            db, run_long.id,
            {"prompt": "{{ nodes.a.output.json.prompt }}"})
    assert e.value.ma == "dau_ra_tran_artifact"


def test_tran_artifact_KHONG_chan_oan_tham_chieu_status_rieng(
        db, run_long, kho_tam):
    """Biểu thức chỉ đọc `.status` (không đọc `.output`) không bị chặn oan
    vì `.output` của node đó (không liên quan) đã tràn artifact."""
    from platform_core.workflow import cau_noi

    _hoan_thanh_a(db, run_long, {"json": "x" * (300 * 1024)})
    ra = cau_noi.giai_tham_so(db, run_long.id, {"x": "{{ nodes.a.status }}"})
    assert ra == {"x": "SUCCEEDED"}


# ── (d) Đường CŨ (tham chiếu đơn) — hồi quy, KHÔNG đổi hành vi ──────────────

def test_duong_cu_tham_chieu_don_khong_doi_hanh_vi(db):
    from platform_core import credit
    from platform_core.workflow import cau_noi, dinh_nghia, tao_run

    wf = _draft(db, {"prompt": "$a.json"})
    v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu=CC)
    wf.published_version_id = v.id
    credit.nap(db, "u1", 100, note="test")
    db.flush()
    run, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                             trigger_kind="manual", idempotency_key="k-cu")
    _hoan_thanh_a(db, run, {"json": {"prompt": "khong quan trong"}})
    ra = cau_noi.giai_tham_so(db, run.id, {"prompt": "{{ nodes.a.output.json }}"})
    assert ra == {"prompt": {"prompt": "khong quan trong"}}


# ── (e) Lưới an toàn chiều sâu (Phần B) — tiêm lỗi, phải ĐỎ khi gỡ ──────────

def test_luoi_an_toan_nem_khi_go(db, run_long, monkeypatch):
    """Tiêm lỗi: nếu `_giai_bieu_thuc_s6` (do bug tương lai) trả NGUYÊN VĂN
    một chuỗi còn `{{`, lưới an toàn (Phần B, `giai_tham_so`) PHẢI ném —
    không được để giá trị mang hình dạng template đi tới job thật.

    ⛔ Bài này ĐỎ nếu ai đó gỡ khối kiểm "con sot {{" trong `giai_tham_so`."""
    from platform_core.workflow import cau_noi

    monkeypatch.setattr(
        cau_noi, "_giai_bieu_thuc_s6",
        lambda db, run_id, v, vong=(): v)          # tra nguyen van - LOI GIA
    with pytest.raises(cau_noi.LoiThamSo) as e:
        cau_noi.giai_tham_so(
            db, run_long.id,
            {"prompt": "{{ nodes.a.output.json.prompt }}"})
    assert e.value.ma == "bieu_thuc_khong_giai_duoc"


def test_chuoi_boc_sai_dang_bi_tu_choi_khong_lang_le_qua(db):
    """`_doi` (publish) không bao giờ để lọt một chuỗi `{{` dạng nội suy
    (`"Ve: {{ nodes.a.output.json }} nhe"`) — nhưng `giai_tham_so` (đường
    CHẠY THẬT) không được TIN publish đã chạy đúng (Phần B): nếu một giá trị
    dạng đó vẫn tới được đây (vd hàng CSDL cũ, graph publish bởi một bản
    `_doi` khác), nó phải NÉM, không được trả nguyên văn."""
    from platform_core.workflow import cau_noi

    with pytest.raises(cau_noi.LoiThamSo) as e:
        cau_noi._giai_bieu_thuc_s6(
            db, "run-khong-ton-tai",
            "Ve: {{ nodes.a.output.json }} nhe")
    assert e.value.ma == "bieu_thuc_khong_giai_duoc"
