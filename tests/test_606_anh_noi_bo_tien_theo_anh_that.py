"""
test_606 — `image.ltt` qua cửa nội bộ: XIN 4 NHẬN 2 ⇒ THU 2. (H43 Phase 04)

Đường đi thật, không đường tắt: `runtime_noi_bo.job.bao_gia` → `nop_job` (giữ chỗ
theo trần ước cao) → worker `job_runner._chay_mot_job` → `apps.anhnoibo.jobs.handle`
→ `features.chuan_hoa` → `DieuPhoi.chay` (GIẢ — không chạm máy B, không dịch prompt)
→ `features.KetQua.as_result()` báo `credit_cost` theo ảnh THẬT →
`job_runner._quyet_toan_credit` thu đúng số đó và hoàn phần dư.

Ba tính chất neo ở đây:
  1. Xin 4 nhận 2 ⇒ `result.credit_cost` = giá 2 ảnh, sổ tiền thu đúng 2 ảnh,
     phần giữ dư được hoàn. Không có `credit_cost` thì nền tảng thu trọn phần giữ.
  2. Nhận đủ ⇒ thu bằng đúng trần đã giữ (không thu dư, không hoàn âm).
  3. Nộp trùng cùng `idempotency_key` ⇒ MỘT job, giữ tiền MỘT lần.

Không sửa giá, không sửa model: mọi con số đọc từ `apps/anhnoibo/gia.py`.
"""
from __future__ import annotations

import uuid

import pytest

TOOL = "image.ltt"
LANE = "anhnoibo.generate"


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "anh606.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    _mo_cua_so_anh()
    yield
    dbmod.reset_engine()


def _mo_cua_so_anh() -> None:
    """Khai 3090 đang trong **cửa sổ ảnh** (dual-model 5.5, D01 B).

    🔴 VÌ SAO MỘT CSDL VỪA `create_all` KHÔNG CHẠY ĐƯỢC JOB ẢNH NỮA. Từ 5.5
       `image.ltt` khai `AdmissionModel("anh_3090", …, "rtx3090", "theo_lo")`,
       và luật 0 của admission fail-closed: **không có dòng `gpu_residency` thì
       không ai được nhận**. Worker sẽ trả job về hàng đợi thay vì chạy handler,
       nên `dp.goi` rỗng và `job.result` là `None` — một kiểu đỏ trông như "điều
       phối hỏng" trong khi thứ hỏng là "chưa ai nói card đang thuộc về ai".

    Trên máy chủ thật, dòng ấy do trọng tài (`residency.buoc`) tạo, và job ảnh
    chỉ chạy khi nó mở cửa sổ `ANH`. Tệp này chạy job ảnh nên phải nói ra điều
    đó, đúng như production phải nói.
    """
    from platform_core.llm import residency

    from tests.conftest import mo_cu_tru_3090

    mo_cu_tru_3090(residency.ANH)


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
        u = tao_nguoi_dung(db, email="a606-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


class _KetQuaAnh:
    """Cùng hình dạng `platform_core.image_gen.dieu_phoi.KetQuaAnh`."""

    def __init__(self, job_id, keys):
        self.job_id = job_id
        self.image_keys = tuple(keys)
        self.prompt_da_gui = "a cat (translated)"
        self.da_dich = True
        self.canh_bao = ("thu",)


class _DieuPhoiGia:
    """Bộ điều phối giả: trả đúng `nhan` khoá ảnh bất kể xin bao nhiêu.

    Cố ý KHÔNG có thuộc tính `cong` — cùng khuôn `_DP` của `test_276` — để
    chốt hỏi-bận-trước bỏ qua và test này chỉ đo phần TIỀN.
    """

    def __init__(self, nhan: int):
        self.nhan = nhan
        self.goi = []

    def chay(self, **kw):
        self.goi.append(kw)
        return _KetQuaAnh(kw["job_id"],
                          [f"anhnoibo/x/{kw['job_id']}/{i}.png" for i in range(self.nhan)])


def _nop(user_id: str, *, count: int, idem: str = "", mode: str = "t2i"):
    """`bao_gia` + `nop_job` trong một phiên, commit, trả `(job_id, held)`."""
    from platform_core import credit
    from platform_core.runtime_noi_bo import job as rj
    bg = rj.bao_gia(TOOL, {"prompt": "mot con meo", "count": count, "mode": mode})
    gen, db = _session()
    try:
        j = rj.nop_job(db, user_id=user_id, bao_gia=bg, idempotency_key=idem)
        db.commit()
        return j.id, credit.so_da_giu(db, j.id)
    finally:
        _close(gen)


def _chay_worker(monkeypatch, dp) -> bool:
    import platform_core.job_runner as runner
    from apps.anhnoibo import jobs as aj
    monkeypatch.setattr(aj, "_dieu_phoi", lambda: dp)
    return runner._chay_mot_job("w-606")


def _job(job_id):
    from platform_core.models import Job
    gen, db = _session()
    try:
        j = db.get(Job, job_id)
        db.expunge(j)
        return j
    finally:
        _close(gen)


# ── 1. Xin 4 nhận 2 ⇒ thu 2 ─────────────────────────────────────────────────

def test_xin_4_nhan_2_thu_dung_2_va_hoan_phan_du(moi_truong, monkeypatch):
    from apps.anhnoibo import gia
    from platform_core import credit
    from platform_core.models import JOB_DONE

    u = _user(100)
    job_id, held = _nop(u, count=4)
    assert held == gia.uoc_tran(so_anh_xin=4, che_do="t2i")

    dp = _DieuPhoiGia(nhan=2)
    assert _chay_worker(monkeypatch, dp) is True

    # Handler nhận đúng tham số đã chuẩn hoá, và job_id là khoá idempotency của máy B.
    assert len(dp.goi) == 1
    kw = dp.goi[0]
    assert kw["job_id"] == job_id and kw["so_anh"] == 4 and kw["mode"] == "t2i"
    assert kw["tien_to_khoa"] == f"anhnoibo/{u}"

    j = _job(job_id)
    assert j.status == JOB_DONE
    gia_2 = gia.tinh(so_anh=2, che_do="t2i")
    assert j.result["credit_cost"] == gia_2                # sau quyết toán = số THU
    assert j.result["so_anh_xin"] == 4 and j.result["so_anh_that"] == 2
    assert len(j.result["image_keys"]) == 2
    assert j.result["phien_ban_gia"] == gia.PHIEN_BAN_GIA

    gen, db = _session()
    try:
        # Thu đúng 2 ảnh, phần giữ dư (4 - 2 ảnh) đã về ví.
        assert credit.so_du(db, u) == 100 - gia_2
        assert gia_2 < held
    finally:
        _close(gen)


def test_nhan_du_thi_thu_bang_dung_tran_da_giu(moi_truong, monkeypatch):
    from apps.anhnoibo import gia
    from platform_core import credit

    u = _user(100)
    job_id, held = _nop(u, count=2)
    assert _chay_worker(monkeypatch, _DieuPhoiGia(nhan=2)) is True
    j = _job(job_id)
    assert j.result["credit_cost"] == held == gia.tinh(so_anh=2, che_do="t2i")
    gen, db = _session()
    try:
        assert credit.so_du(db, u) == 100 - held
    finally:
        _close(gen)


def test_ket_qua_co_du_truong_khach_can(moi_truong, monkeypatch):
    """Khuôn kết quả mà ChatLTT sẽ đọc: khoá ảnh, prompt đã gửi, cờ dịch, cảnh báo."""
    u = _user(100)
    job_id, _ = _nop(u, count=1)
    assert _chay_worker(monkeypatch, _DieuPhoiGia(nhan=1)) is True
    r = _job(job_id).result
    for k in ("image_keys", "prompt", "da_dich", "canh_bao", "so_anh_xin",
              "so_anh_that", "credit_cost", "phien_ban_gia"):
        assert k in r, k
    assert r["da_dich"] is True and r["canh_bao"] == ["thu"]


# ── 3. Nộp trùng ⇒ một job ───────────────────────────────────────────────────

def test_nop_trung_cung_idempotency_key_chi_mot_job_mot_lan_giu_tien(moi_truong):
    from platform_core import credit
    from platform_core.models import Job

    u = _user(100)
    j1, held = _nop(u, count=3, idem="idem-606")
    j2, _ = _nop(u, count=3, idem="idem-606")
    assert j1 == j2
    gen, db = _session()
    try:
        assert db.query(Job).filter(Job.user_id == u).count() == 1
        assert credit.so_du(db, u) == 100 - held          # giữ đúng MỘT lần
    finally:
        _close(gen)

    # Khoá KHÁC thì là một yêu cầu khác — dedupe theo khoá, không theo may rủi.
    j3, _ = _nop(u, count=3, idem="idem-606-b")
    assert j3 != j1
    gen, db = _session()
    try:
        assert db.query(Job).filter(Job.user_id == u).count() == 2
        assert credit.so_du(db, u) == 100 - 2 * held
    finally:
        _close(gen)


def test_nop_trung_khong_key_suy_tu_tham_so(moi_truong):
    """Không truyền khoá ⇒ suy từ `(lane, tham số)` như mọi route web."""
    from platform_core.models import Job
    u = _user(100)
    j1, _ = _nop(u, count=2)
    j2, _ = _nop(u, count=2)
    assert j1 == j2
    gen, db = _session()
    try:
        assert db.query(Job).filter(Job.user_id == u).count() == 1
    finally:
        _close(gen)
