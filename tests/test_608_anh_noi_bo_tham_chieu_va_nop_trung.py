"""
test_608 — ẢNH THAM CHIẾU CỦA NGƯỜI KHÁC: lỗi của NGƯỜI GỌI, không chạm máy B,
không thử lại. (H43 Phase 04)

Trước 03/09/2026 mọi lỗi của `features.chuan_hoa` là `LoiTaoAnh` — một `Exception`
thường — nên `job_runner` xếp vào nhánh `retry`: ba lượt thử, ba lần xếp hàng, cho
một khoá ảnh mà cửa vào đã biết là của người khác. Đúng lớp lỗi `LoiNguoiGoi` được
sinh ra để sửa (job `a49ce0d3`, 31/08, ở app tiếng).

Neo ở đây:
  1. `chuan_hoa` với khoá của người khác ⇒ `LoiYeuCauAnh` — vừa là `LoiTaoAnh`
     (mọi `except` cũ giữ nguyên) vừa là `LoiNguoiGoi` (nền tảng KHÔNG thử lại).
  2. Worker thật: job `error` sau ĐÚNG MỘT lượt, hoàn đủ tiền, bộ điều phối KHÔNG
     bao giờ được dựng (không dịch prompt, không cấp vé, không gọi máy B),
     `provider_state` không bị đánh dấu — không provider nào từ chối cả.
  3. Lỗi hạ tầng (`LoiTaoAnh` thường) vẫn đi nhánh `retry` như cũ.
"""
from __future__ import annotations

import uuid

import pytest

TOOL = "image.ltt"


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "anh608.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    yield
    dbmod.reset_engine()


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _user(credits=100) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="a608-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


# ── 1. Hình dạng lỗi ─────────────────────────────────────────────────────────

def test_khoa_cua_nguoi_khac_la_loi_nguoi_goi_va_van_la_LoiTaoAnh():
    from platform_core import jobs as jobq
    from platform_core.job_runner import _provider_failure_kind
    from apps.anhnoibo import features

    with pytest.raises(features.LoiYeuCauAnh) as e:
        features.chuan_hoa({"prompt": "meo", "mode": "edit", "owner_id": "u1",
                            "image_key": "anhnoibo/u2/j9/0.png"})
    assert isinstance(e.value, features.LoiTaoAnh)
    assert isinstance(e.value, jobq.LoiNguoiGoi)
    assert _provider_failure_kind(e.value, provider_state="")[0] == "loi_nguoi_goi"


@pytest.mark.parametrize("params", [
    {"prompt": "   "},
    {"prompt": "meo", "mode": "la"},
    {"prompt": "meo", "mode": "edit"},
    {"prompt": "meo", "mode": "t2i", "image_key": "anhnoibo/u1/j/0.png", "owner_id": "u1"},
    {"prompt": "meo", "mode": "edit", "image_key": "anhnoibo/u1/j/0.png"},
    {"prompt": "meo", "mode": "edit", "owner_id": "u1",
     "image_keys": ["anhnoibo/u1/j/0.png", "anhnoibo/u1/j/1.png", "anhnoibo/u1/j/2.png"]},
])
def test_moi_loi_cua_yeu_cau_deu_khong_thu_lai(params):
    from platform_core import jobs as jobq
    from apps.anhnoibo import features

    with pytest.raises(jobq.LoiNguoiGoi):
        features.chuan_hoa(params)


def test_khoa_cua_chinh_minh_o_app_khac_van_qua():
    from apps.anhnoibo import features
    yc = features.chuan_hoa({"prompt": "meo", "mode": "edit", "owner_id": "u1",
                             "image_key": "taoanh/u1/j3/0.png"})
    assert yc.ref_keys == ("taoanh/u1/j3/0.png",)


def test_loi_ha_tang_van_la_retry():
    """`LoiTaoAnh` thường (cổng hỏng, chưa cấu hình) KHÔNG bị kéo theo thành lỗi khách."""
    from platform_core import jobs as jobq
    from platform_core.job_runner import _provider_failure_kind
    from apps.anhnoibo import features

    e = features.LoiTaoAnh("Mat lien lac voi may tao anh")
    assert not isinstance(e, jobq.LoiNguoiGoi)
    assert _provider_failure_kind(e, provider_state="")[0] == "retry"


# ── 2. Worker thật ──────────────────────────────────────────────────────────

def test_worker_tu_choi_ngay_khong_dung_dieu_phoi_hoan_du_tien(moi_truong, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core import credit
    from platform_core.models import JOB_ERROR, Job, JobEvent
    from platform_core.runtime_noi_bo import job as rj
    from apps.anhnoibo import jobs as aj

    u = _user(100)
    khac = _user(100)
    # Khoá hợp lệ về hình thức, nhưng đoạn thứ hai là NGƯỜI KHÁC.
    bg = rj.bao_gia(TOOL, {"prompt": "meo", "mode": "edit",
                           "image_key": f"anhnoibo/{khac}/j9/0.png"})
    assert bg.credit > 0                      # bao_gia KHÔNG kiểm sở hữu (đúng vai)
    gen, db = _session()
    try:
        j = rj.nop_job(db, user_id=u, bao_gia=bg)
        db.commit()
        job_id, held = j.id, credit.so_da_giu(db, j.id)
    finally:
        _close(gen)
    assert held == bg.credit

    dung = []

    def _khong_duoc_dung():
        dung.append(True)
        raise AssertionError("bo dieu phoi bi dung cho mot yeu cau da sai tu dau")

    monkeypatch.setattr(aj, "_dieu_phoi", _khong_duoc_dung)
    assert runner._chay_mot_job("w-608") is True
    assert dung == []

    gen, db = _session()
    try:
        j = db.get(Job, job_id)
        assert j.status == JOB_ERROR
        assert j.attempts == 1 and j.max_attempts >= 3    # hỏng NGAY lượt đầu
        assert j.provider_state == ""                      # không provider nào từ chối
        assert "không thuộc" in (j.error or "")
        ma = {e.event_code for e in db.query(JobEvent).filter(JobEvent.job_id == job_id)}
        assert "failed" in ma and "retry_scheduled" not in ma
        assert "resource_wait" not in ma
        assert credit.so_du(db, u) == 100                 # hoàn đủ
        assert credit.so_du(db, khac) == 100              # người kia không bị chạm
    finally:
        _close(gen)
