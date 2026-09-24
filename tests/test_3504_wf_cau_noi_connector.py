"""`cau_noi` mở đường cho node connector — và giữ luật `irreversible`.

Trước plan P6, `cau_noi.nop_job` **từ chối** mọi node không thuộc `app.*`
bằng `LoiTienTo`: `nut.tu_piece` nói thẳng điều đó trong bình luận. Tệp này đo
rằng đường mới đã mở, và — quan trọng hơn — rằng nó **không** làm rơi hai thứ
mà đường cũ đang giữ:

1. Trần báo giá (`gia_tran`) vẫn cắn.
2. Một kết quả **mơ hồ** trên node `irreversible` ra **ABANDONED**, ⛔ không
   phải FAILED-rồi-thử-lại. Đây là chỗ một lượt "thử lại cho chắc" biến thành
   video thứ hai trên kênh khách.

## ⛔ Vì sao rẽ theo BỘ THI HÀNH chứ không theo tiền tố tên

`piece.*` và `connector.*` là hai không gian tên khác nhau nhưng **cùng** một
tính chất: không bọc ToolSpec nào. Rẽ bằng `type.startswith("piece.")` là
hardcode một cái tên trong `platform_core/` — Global Constraint cấm, và nó sẽ
sai im lặng vào ngày có không gian tên thứ ba.
"""
from __future__ import annotations
# ruff: noqa: F811 -- fixture pytest duoc import co chu y.

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


def _thanh_connector(db, run, loai="connector.youtube.upload", params=None,
                     gia_tran=3):
    """Đổi node `a` của đồ thị ĐÃ GHIM thành một node connector.

    ⚠️ Sửa **đồ thị**, không chỉ truyền dict: `ap_ket_qua` đọc node từ
       `WorkflowVersion.graph`. Một phép truyền dict riêng đo `nop_job` mà
       **không** đo `ap_ket_qua` — đúng nhánh đang cần kiểm.
    """
    from platform_core.models import WorkflowVersion
    v = db.get(WorkflowVersion, run.version_id)
    g = dict(v.graph)
    g["nodes"] = [dict(n) for n in g["nodes"]]
    node = next(n for n in g["nodes"] if n["id"] == "a")
    node["type"] = loai
    node["params"] = dict(params or {})
    node["gia_tran"] = gia_tran
    v.graph = g
    db.flush()
    return node


def test_nop_job_connector_RA_JOB_THAT_tren_lane_rieng(db, run):
    """Đường cũ trả `LoiTienTo` cho `connector.*`. Nay nó ra một job thật."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut
    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    jid = cau_noi.nop_job(db, run, node, cong_cu=CC)
    assert jid is not None, "van con bi tu choi"
    job = db.get(Job, jid)
    assert job.job_type == nut.JOB_TYPE_CONNECTOR
    assert job.app_slug == "connector_runner"
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"


def test_job_connector_GIU_SUAT_admission_cua_lane(db, run):
    """🔴 Máy A là production. Mỗi lệnh connector là một tiến trình Node ~400 MB;
    một lane không khai admission là một lane không có trần."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    assert job.admission_resource == cau_noi.TAI_NGUYEN_CONNECTOR
    # ⚠️ `admission_slots` la SUC CHUA, khong phai so suat mot job xin:
    #    `jobs.claim` so `dang_giu < Job.admission_slots`.
    assert job.admission_slots == cau_noi.SUAT_CONNECTOR >= 2


def test_tham_so_mang_du_thu_handler_can(db, run):
    """Handler chạy ở tiến trình khác, giờ khác. Nó phải đọc được **từ job**
    piece/bản/action nào — ⛔ không tra lại catalog lúc chạy, vì catalog có thể
    đã đổi sau khi version được publish."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    meta = job.params["_connector"]
    assert meta["node_type"] == "connector.youtube.upload"
    assert meta["run_id"] == run.id and meta["node_id"] == "a"


def test_vuot_TRAN_BAO_GIA_thi_FAILED_khong_nop_job(db, run):
    """Đường mới không được làm rơi trần báo giá của đường cũ."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, nut
    from platform_core.workflow.nut_loi import connector as nc
    node = _thanh_connector(db, run, gia_tran=0)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    # Đẩy giá node lên trên trần để phép này nói về ĐÚNG luật trần.
    import dataclasses
    dat = dataclasses.replace(nc.YOUTUBE_UPLOAD, gia=nut.Gia.co_dinh(5))
    from platform_core.workflow import nut_loi
    cu = nut_loi._SO["connector.youtube.upload"]
    nut_loi._SO["connector.youtube.upload"] = dat
    try:
        assert cau_noi.nop_job(db, run, node, cong_cu=CC) is None
    finally:
        nut_loi._SO["connector.youtube.upload"] = cu
    assert mtt.trang_thai_node(db, run.id, "a") == "FAILED"
    assert db.query(Job).filter(Job.job_type == nut.JOB_TYPE_CONNECTOR).count() == 0


def test_MO_HO_tren_node_irreversible_ra_ABANDONED_khong_thu_lai(db, run):
    """🔴 Luật đắt nhất của phase này.

    `provider_state = AMBIGUOUS` nghĩa là *"ta không biết nó đã chạy chưa"*.
    Với `irreversible`, "không biết" phải dừng lại — ⛔ không FAILED rồi thử
    lại, vì một lần thử lại là một video thứ hai trên kênh khách.
    """
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    jobs.mark_ambiguous(db, job, "mat ket noi giua chung")
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "ABANDONED"


def test_DOI_CHUNG_loi_KHONG_mo_ho_thi_van_FAILED(db, run):
    """Không có phép này, `ABANDONED` ở trên có thể chỉ là "mọi lỗi đều
    ABANDONED" — tức node connector không bao giờ báo hỏng."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    jobs.fail(db, job, "400 tham so sai")
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "FAILED"


def test_HAU_KIEM_van_chay_cho_node_connector(db, run):
    """`job.status == SUCCEEDED` không đảm bảo video đã lên."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    jobs.complete(db, job, {"video_id": ""})
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "ABANDONED"
    # ⛔ Không thu tiền cho một kết quả không dùng được.
    assert run.actual_cost == 0


def test_doi_chung_video_id_co_that_thi_SUCCEEDED(db, run):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    node = _thanh_connector(db, run)
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, node, cong_cu=CC))
    jobs.complete(db, job, {"video_id": "VID", "status": {}})
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=CC) == "SUCCEEDED"


def test_khoa_khu_trung_theo_DUONG_THI_HANH_khong_theo_node_id(db, run):
    """Cùng bài học ba lần lặp ở phase 4: một node trong `foreach` phải sinh
    khoá KHÁC nhau ở mỗi vòng, không thì `jobs.submit` trả lại job vòng 1."""
    from platform_core.workflow import cau_noi
    from platform_core.workflow.nut_loi import connector as nc
    shim = cau_noi._NhuCongCu(nc.YOUTUBE_UPLOAD)
    node = {"id": "a"}
    k0 = cau_noi._khoa_idem(run, node, 1, shim, {"video": "v", "title": "t"},
                            ())
    k1 = cau_noi._khoa_idem(run, node, 1, shim, {"video": "v", "title": "t"},
                            (("f", 1),))
    assert k0 != k1, "khoa khong phan biet duoc hai vong cua foreach"


def test_CUA_VAO_handle_mo_duoc_phien_CSDL(monkeypatch):
    """🔴 `handle()` la CUA VAO ma production goi cho MOI job connector — va no
       tung nem `TypeError` ngay dong dau.

    `with get_session() as db:` — `get_session()` la mot **generator** (kieu
    dependency cua FastAPI), khong phai context manager:

        >>> with get_session() as db: ...
        TypeError: 'generator' object does not support the context manager protocol

    ⛔ VI SAO BO TEST CU KHONG THAY: moi bai deu goi THANG `_chay_youtube` /
       `_chay_piece`. Chung do dung phan ben trong, va bo qua dung cai cua ma
       production di qua. "FLOW D 7/7 xanh" la that — nhung no khong noi gi ve
       `handle()`.

    ⭐ Bai nay co y goi `handle()` voi mot `_connector` KHONG hop le, de no hong
       o buoc sau cua chinh no. Thu duy nhat bai chot la: **mo duoc phien**, tuc
       khong con `TypeError` ve context manager.
    """
    from apps.connector_runner import jobs as cj

    with pytest.raises(Exception) as e:
        cj.handle({"_connector": {"node_type": "connector.khong_ton_tai"}})
    assert not isinstance(e.value, TypeError), (
        f"cua vao chet truoc khi lam gi: {e.value!r}")
    assert "context manager" not in str(e.value)


def test_handle_KHONG_CO__connector_thi_noi_ro_la_loi_he_thong():
    """🔑 Doi chung cho bai tren: neu `handle` ngã ngay truoc khi mo phien thi
       bai kia xanh ma khong chung minh duoc gi ve viec mo phien."""
    from apps.connector_runner import jobs as cj

    with pytest.raises(cj.LoiHandler, match="loi_he_thong"):
        cj.handle({})
