"""
test_607 — MÁY B BẬN KHÔNG PHẢI HỎNG, và worker phải hiểu đúng như vậy. (H43 Phase 04)

Phát hiện ở Phase 02 (`reports/02_runtime_noi_bo.md`): `cong_render.BanError` bị
`apps/anhnoibo/jobs.py` bọc thành `LoiTaoAnh` — một `Exception` thường — nên
`job_runner._provider_failure_kind` xếp nó vào nhánh `retry`: **tiêu một lượt thử**,
và sau ba lượt bận thì job HỎNG kèm hoàn tiền cho một việc chưa từng chạy.

Bản sửa (nhỏ nhất, generic): tín hiệu nền tảng `platform_core.jobs.DangBan` mà
app nào cũng ném được không cần import cổng của app khác; `_provider_failure_kind`
nhận ra nó ⇒ `resource_wait`. App ảnh dịch `BanError` → `DangBan` (giữ câu chữ).

Neo ở đây:
  1. `_provider_failure_kind(DangBan)` ⇒ `resource_wait`, chờ theo `retry_after_s`.
  2. `handle` dịch `BanError` → `DangBan`: giữ ETA, giữ thông điệp, KHÔNG là lỗi khách.
  3. Hỏi `/health` TRƯỚC khi dịch prompt: bận ⇒ xếp lại mà không tốn lượt dịch;
     cổng không trả lời ⇒ KHÔNG coi là bận (đi đường thường, hỏng có đếm lượt).
  4. Worker thật (`_chay_mot_job`): bận ⇒ job về `queued`, `attempts` KHÔNG tăng,
     tiền vẫn GIỮ (không thu, không hoàn), sự kiện `resource_wait`; bận nhiều lần
     hơn `max_attempts` vẫn không hỏng; hết bận thì chạy xong và thu đúng.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

TOOL = "image.ltt"


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "anh607.db").as_posix())
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
        u = tao_nguoi_dung(db, email="a607-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


class _KetQuaAnh:
    def __init__(self, job_id, keys):
        self.job_id = job_id
        self.image_keys = tuple(keys)
        self.prompt_da_gui = "x"
        self.da_dich = False
        self.canh_bao = ()


class _CongGia:
    """Cổng render giả: chỉ có `health()`."""

    def __init__(self, health=None, loi=None):
        self._health = health or {}
        self._loi = loi
        self.hoi = 0

    def health(self):
        self.hoi += 1
        if self._loi is not None:
            raise self._loi
        return dict(self._health)


class _DieuPhoiGia:
    """`chay` ném `loi` nếu có, không thì trả `nhan` ảnh. Có `cong` tuỳ chọn."""

    def __init__(self, *, nhan=1, loi=None, cong=None):
        self.nhan, self.loi, self.cong = nhan, loi, cong
        self.goi = []

    def chay(self, **kw):
        self.goi.append(kw)
        if self.loi is not None:
            raise self.loi
        return _KetQuaAnh(kw["job_id"], [f"k{i}" for i in range(self.nhan)])


# ── 1. Phân loại của nền tảng ───────────────────────────────────────────────

@pytest.mark.parametrize("cho, mong", [(90, 90), (7.5, 7), (0.4, 1), (None, 20), (0, 20)])
def test_DangBan_la_resource_wait_theo_retry_after(cho, mong):
    from platform_core import jobs as jobq
    from platform_core.job_runner import _provider_failure_kind

    kind, cho_lai = _provider_failure_kind(
        jobq.DangBan("ban", retry_after_s=cho), provider_state="")
    assert kind == "resource_wait" and cho_lai == mong


def test_DangBan_khong_phai_loi_khach_khong_phai_BanError_cua_VLM():
    """Tín hiệu nền tảng đứng riêng: không kéo theo mô-đun cổng VLM, không là LoiNguoiGoi."""
    from platform_core import jobs as jobq
    from platform_core.llm.cong_vlm import BanError as BanVlm

    assert not issubclass(jobq.DangBan, jobq.LoiNguoiGoi)
    assert not issubclass(jobq.DangBan, BanVlm)
    e = jobq.DangBan("ly do", retry_after_s=3)
    assert e.ly_do == "ly do" and e.retry_after_s == 3 and str(e) == "ly do"


def test_duong_text_BanError_VLM_van_resource_wait_nhu_cu():
    """Không đụng đường text đang bán: `cong_vlm.BanError` vẫn được nhận ra."""
    from platform_core.job_runner import _provider_failure_kind
    from platform_core.llm.cong_vlm import BanError

    assert _provider_failure_kind(BanError("busy", retry_after_s=17),
                                  provider_state="") == ("resource_wait", 17)


# ── 2. App ảnh dịch BanError → DangBan ──────────────────────────────────────

def test_handle_dich_BanError_thanh_DangBan_giu_ETA_va_thong_diep(monkeypatch):
    from platform_core import jobs as jobq
    from platform_core.image_gen import cong_render
    from apps.anhnoibo import features, jobs as aj

    ban = cong_render.BanError("video dang chay", eta_s=150)
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: _DieuPhoiGia(loi=ban))
    with pytest.raises(jobq.DangBan) as e:
        aj.handle({"prompt": "mot con meo", "count": 2})

    assert e.value.retry_after_s == 150
    assert e.value.__cause__ is ban
    assert "2 phút" in str(e.value)                 # ETA đi vào câu khách đọc
    assert "bận" in str(e.value)
    assert not isinstance(e.value, features.LoiTaoAnh)
    assert not isinstance(e.value, jobq.LoiNguoiGoi)


def test_handle_ETA_khong_biet_thi_khong_bia_so_phut(monkeypatch):
    from platform_core import jobs as jobq
    from platform_core.image_gen import cong_render
    from apps.anhnoibo import jobs as aj

    monkeypatch.setattr(aj, "_dieu_phoi",
                        lambda: _DieuPhoiGia(loi=cong_render.BanError("ban")))
    with pytest.raises(jobq.DangBan) as e:
        aj.handle({"prompt": "mot con meo"})
    assert e.value.retry_after_s is None
    assert "phút" not in str(e.value)


def test_hong_that_van_la_LoiTaoAnh_de_duoc_thu_lai_co_dem(monkeypatch):
    """`DieuPhoiError` (cổng hỏng, hết giờ) KHÔNG phải bận: retry có đếm lượt."""
    from platform_core.image_gen import dieu_phoi
    from platform_core.job_runner import _provider_failure_kind
    from platform_core import jobs as jobq
    from apps.anhnoibo import features, jobs as aj

    monkeypatch.setattr(aj, "_dieu_phoi",
                        lambda: _DieuPhoiGia(loi=dieu_phoi.DieuPhoiError("mat lien lac")))
    with pytest.raises(features.LoiTaoAnh) as e:
        aj.handle({"prompt": "mot con meo"})
    assert not isinstance(e.value, jobq.DangBan)
    assert not isinstance(e.value, jobq.LoiNguoiGoi)
    assert _provider_failure_kind(e.value, provider_state="")[0] == "retry"


# ── 3. Hỏi bận trước khi dịch prompt ────────────────────────────────────────

def test_health_bao_ban_thi_xep_lai_TRUOC_khi_chay_dieu_phoi(monkeypatch):
    from platform_core import jobs as jobq
    from apps.anhnoibo import jobs as aj

    cong = _CongGia(health={"busy": True, "reason": "video", "eta_s": 300})
    dp = _DieuPhoiGia(cong=cong)
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: dp)
    with pytest.raises(jobq.DangBan) as e:
        aj.handle({"prompt": "mot con meo"})
    assert e.value.retry_after_s == 300 and "5 phút" in str(e.value)
    assert cong.hoi == 1
    assert dp.goi == [], "may ban ma van dich prompt + gui = ton mot luot dich vo ich"


def test_health_khong_tra_loi_thi_KHONG_coi_la_ban(monkeypatch):
    """Cổng chết ≠ cổng bận. Bận xếp lại vô hạn; chết phải hỏng có đếm lượt."""
    from platform_core.image_gen import cong_render
    from apps.anhnoibo import jobs as aj

    cong = _CongGia(loi=cong_render.CongRenderError("health tra 502"))
    dp = _DieuPhoiGia(nhan=1, cong=cong)
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: dp)
    kq = aj.handle({"prompt": "mot con meo"})
    assert cong.hoi == 1 and len(dp.goi) == 1
    assert kq["so_anh_that"] == 1


def test_health_ranh_thi_chay_binh_thuong(monkeypatch):
    from apps.anhnoibo import jobs as aj

    cong = _CongGia(health={"busy": False})
    dp = _DieuPhoiGia(nhan=1, cong=cong)
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: dp)
    assert aj.handle({"prompt": "mot con meo"})["so_anh_that"] == 1


def test_bo_dieu_phoi_khong_co_cong_thi_bo_qua_phep_hoi(monkeypatch):
    """Khuôn `_DP` của `test_276` (không có `cong`) vẫn chạy nguyên."""
    from apps.anhnoibo import jobs as aj

    dp = _DieuPhoiGia(nhan=2)
    assert not hasattr(dp, "cong") or dp.cong is None
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: dp)
    assert aj.handle({"prompt": "mot con meo", "count": 2})["so_anh_that"] == 2


# ── 4. Worker thật ──────────────────────────────────────────────────────────

def _nop(user_id: str, *, count: int):
    from platform_core import credit
    from platform_core.runtime_noi_bo import job as rj
    bg = rj.bao_gia(TOOL, {"prompt": "mot con meo", "count": count})
    gen, db = _session()
    try:
        j = rj.nop_job(db, user_id=user_id, bao_gia=bg, idempotency_key="idem-607")
        db.commit()
        return j.id, credit.so_da_giu(db, j.id)
    finally:
        _close(gen)


def _doc(job_id):
    from platform_core.models import Job, JobEvent
    gen, db = _session()
    try:
        j = db.get(Job, job_id)
        ma = [e.event_code for e in
              db.query(JobEvent).filter(JobEvent.job_id == job_id)
              .order_by(JobEvent.sequence).all()]
        db.expunge(j)
        return j, ma
    finally:
        _close(gen)


def _cho_chay_ngay(job_id):
    from platform_core.models import Job
    gen, db = _session()
    try:
        j = db.get(Job, job_id)
        j.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        _close(gen)


def test_worker_ban_thi_ve_hang_doi_khong_tieu_luot_khong_cham_tien(moi_truong, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core import credit
    from platform_core.image_gen import cong_render
    from platform_core.models import JOB_QUEUED
    from apps.anhnoibo import jobs as aj

    u = _user(100)
    job_id, held = _nop(u, count=2)
    assert held > 0

    ban = _DieuPhoiGia(loi=cong_render.BanError("video dang chay", eta_s=150))
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: ban)
    assert runner._chay_mot_job("w-607") is True

    j, ma = _doc(job_id)
    assert j.status == JOB_QUEUED
    assert j.attempts == 0, "ban ma tieu luot thu la sai ban chat cua H43.4"
    assert j.provider_state == "rejected"           # từ chối XÁC ĐỊNH, không mập mờ
    assert j.worker_id == ""
    assert j.next_run_at is not None
    assert "resource_wait" in ma and "retry_scheduled" not in ma
    assert "failed" not in ma and "credit_settled" not in ma

    gen, db = _session()
    try:
        assert credit.so_da_giu(db, job_id) == held     # vẫn giữ, chưa thu
        assert credit.so_du(db, u) == 100 - held        # chưa hoàn (job chưa hỏng)
    finally:
        _close(gen)

    # Chưa tới giờ hẹn ⇒ worker không nhặt lại (hoãn thật, không phải mất).
    assert runner._chay_mot_job("w-607") is False


def test_worker_ban_qua_max_attempts_van_khong_hong(moi_truong, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core.image_gen import cong_render
    from platform_core.models import JOB_QUEUED
    from apps.anhnoibo import jobs as aj

    u = _user(100)
    job_id, _ = _nop(u, count=1)
    j, _ = _doc(job_id)
    so_lan = j.max_attempts
    assert so_lan >= 1

    ban = _DieuPhoiGia(loi=cong_render.BanError("ban", eta_s=5))
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: ban)
    for _ in range(so_lan + 2):
        _cho_chay_ngay(job_id)
        assert runner._chay_mot_job("w-607") is True
    j, _ = _doc(job_id)
    assert j.status == JOB_QUEUED and j.attempts == 0
    assert len(ban.goi) == so_lan + 2


def test_worker_het_ban_thi_chay_xong_va_thu_dung(moi_truong, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core import credit
    from platform_core.image_gen import cong_render
    from platform_core.models import JOB_DONE
    from apps.anhnoibo import gia, jobs as aj

    u = _user(100)
    job_id, held = _nop(u, count=2)

    ban = _DieuPhoiGia(loi=cong_render.BanError("ban", eta_s=5))
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: ban)
    assert runner._chay_mot_job("w-607") is True

    _cho_chay_ngay(job_id)
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: _DieuPhoiGia(nhan=2))
    assert runner._chay_mot_job("w-607") is True

    j, ma = _doc(job_id)
    assert j.status == JOB_DONE
    assert ma.count("resource_wait") == 1 and "credit_settled" in ma
    gen, db = _session()
    try:
        assert credit.so_du(db, u) == 100 - gia.tinh(so_anh=2, che_do="t2i")
        assert held == gia.tinh(so_anh=2, che_do="t2i")
    finally:
        _close(gen)
