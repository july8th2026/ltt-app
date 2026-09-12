"""dual-model Task 5.3 — luật 0 `CHO_RESIDENCY`: cửa admission của một nhóm GPU.

`test_1216` chứng minh MÁY TRẠNG THÁI chia RTX 3090 (hàm thuần). Tệp này chứng
minh cái cửa: một lượt chỉ được nhận khi nhóm GPU của tài nguyên nó xin **đang
cư trú cho vai trò của nó** — và mọi tài nguyên KHÔNG thuộc nhóm nào vẫn chảy y
như cũ, vì một hồi quy ở đó dừng cả nền tảng chứ không riêng 3090.

Bốn thứ mỗi phép kiểm dưới đây phải đi kèm một đối chứng ngược chiều, vì cả bốn
đều xanh được bằng cách làm sai:

  · `ANH` chặn `ltt-3.8`  ⇒ đối chứng: `ltt-3.5` (5060 Ti) **vẫn được nhận**.
    Không có vế sau thì "chặn hết" cũng xanh, và ta vừa tắt cả model thứ hai.
  · `LLM` chặn job ảnh    ⇒ đối chứng: `ANH` thì đúng job ấy được nhận.
  · thiếu dòng cư trú ⇒ đóng ⇒ đối chứng: tài nguyên KHÔNG có nhóm vẫn mở dù
    bảng `gpu_residency` rỗng tuếch.
  · luật 0 chạy TRƯỚC luật 1–2 ⇒ đối chứng: cùng đầu vào ấy, một bản `xet` xếp
    cư trú SAU luật slot trả về mã lý do KHÁC — tức ca này phân biệt được thứ tự,
    chứ không chỉ tình cờ xanh.
"""
from __future__ import annotations

import ast
import pathlib
import threading
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from apps.ltt_llm.ngan_sach import (NHOM_CU_TRU_38, POOL_35, POOL_38, SO_SLOT,
                                    TAI_NGUYEN_35, TAI_NGUYEN_38)
from platform_core.llm import luat_nhan as L
from platform_core.llm import residency as R
from platform_core.registry import AdmissionModel

GOC = pathlib.Path(__file__).resolve().parents[1]
T0 = datetime(2026, 9, 12, 9, 0, tzinfo=timezone.utc)
#: Tên tài nguyên của model ảnh trên 3090. Task 5.5 khai nó trong ba manifest
#: ảnh; tới 5.3 nó chưa tồn tại trong bản khai nào, nên các ca "job ảnh" dưới
#: đây TIÊM một bản khai giả (`ban_do_anh`) — và bản khai giả ấy đi qua đúng hàm
#: dựng bản đồ thật, chứ không thay bản đồ bằng một dict gõ tay.
TAI_NGUYEN_ANH = "anh_3090"


class DongHo:
    """Đồng hồ + hàm ngủ TIÊM (memory "tiêm nửa đối tượng thì phép đo vẫn sai")."""

    def __init__(self, t0=T0):
        self.t = t0

    def __call__(self):
        return self.t

    def ngu(self, s):
        self.t += timedelta(seconds=s)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'res.db').as_posix()}")
    import platform_core.db as dbmod
    from platform_core.llm import admission

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    admission.quen_ban_do_cu_tru()
    # Phanh chống ngập log của `_nhac` là trạng thái CẢ TIẾN TRÌNH: không xoá thì
    # ca "đóng cửa mà có nói ra" xanh/đỏ tuỳ thứ tự chạy của tệp này.
    admission._da_nhac.clear()
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()
        admission.quen_ban_do_cu_tru()


@pytest.fixture()
def ban_do_anh(monkeypatch):
    """Tiêm bản khai của một app ảnh (Task 5.5) vào `registry.discover`."""
    from platform_core.llm import admission

    tool = SimpleNamespace(
        name="image.generate",
        admission_theo_model={"*": AdmissionModel(
            TAI_NGUYEN_ANH, 1, 0, NHOM_CU_TRU_38, R.THEO_LO)})
    from platform_core import registry

    that = registry.discover

    def gia(*a, **k):
        return list(that(*a, **k)) + [
            SimpleNamespace(manifest=SimpleNamespace(slug="anh_gia", tools=(tool,)))]

    monkeypatch.setattr("platform_core.registry.discover", gia)
    admission.quen_ban_do_cu_tru()
    yield
    admission.quen_ban_do_cu_tru()


def _dat(db, trang_thai: str, nhom: str = NHOM_CU_TRU_38) -> None:
    """Ghi trạng thái cư trú của một nhóm (vai trò trọng tài của Task 5.5)."""
    from platform_core.models import GpuResidency

    dong = db.get(GpuResidency, nhom)
    if dong is None:
        dong = GpuResidency(nhom=nhom, trang_thai=trang_thai, tu_luc=T0)
        db.add(dong)
    else:
        dong.trang_thai = trang_thai
    db.commit()


def _xin(db, *, resource=TAI_NGUYEN_38, pool=POOL_38, slots=SO_SLOT,
         user="u", holder="h", lop=L.TUONG_TAC, tok=10_000, mode="stream", **kw):
    from platform_core.llm import admission

    return admission.xet_va_giu(db, resource=resource, slots=slots, user_id=user,
                                mode=mode, holder_id=holder, token_pool=pool,
                                lop=lop, token_dat_truoc=tok, **kw)


def _so_lease(db, resource: str) -> int:
    from platform_core.models import ExecutionLease

    db.expire_all()
    return db.query(ExecutionLease).filter(
        ExecutionLease.resource == resource).count()


# ── 1. Cửa sổ ảnh: 3.8 chờ, 3.5 KHÔNG chờ ────────────────────────────────────

def test_trang_thai_anh_chan_38_nhung_35_van_duoc_nhan(db):
    """Vế sau là đối chứng quan trọng nhất của cả tệp: luật 0 theo TỪNG CARD.

    `ltt-3.5` ở trên 5060 Ti, không khai `residency_group`, nên không có trọng
    tài nào để hỏi. Một bản cài "đóng cửa khi nhóm không mở" mà quên phân biệt
    sẽ chặn luôn nó — và thứ dừng lại khi ấy là cả nền tảng.
    """
    _dat(db, R.ANH)

    ve, ly_do = _xin(db, resource=TAI_NGUYEN_38, pool=POOL_38)
    assert ve is None and ly_do == L.CHO_RESIDENCY
    assert _so_lease(db, TAI_NGUYEN_38) == 0
    db.rollback()

    ve35, ly_do35 = _xin(db, resource=TAI_NGUYEN_35, pool=POOL_35, holder="h35")
    assert ve35 is not None, ly_do35
    assert ly_do35 == ""
    db.commit()


def test_lease_38_duoc_cap_lai_ngay_khi_cua_so_anh_dong(db):
    _dat(db, R.ANH)
    assert _xin(db, holder="a")[1] == L.CHO_RESIDENCY
    db.rollback()

    _dat(db, R.LLM)
    ve, ly_do = _xin(db, holder="a")
    assert ve is not None, ly_do
    db.commit()
    assert _so_lease(db, TAI_NGUYEN_38) == 1


def test_trang_thai_la_thi_dong_cua(db):
    """Trạng thái không có trong `residency.TRANG_THAI` ⇒ đóng (fail-closed)."""
    _dat(db, "vo_danh")
    assert _xin(db)[1] == L.CHO_RESIDENCY


# ── 2. Chiều ngược: cửa sổ LLM chặn job ảnh ──────────────────────────────────

def test_trang_thai_llm_chan_job_anh(db, ban_do_anh):
    """Job ảnh KHÔNG khai pool KV và KHÔNG khai lớp ⇒ nó đi vào đúng đường tắt
    "đếm slot" cũ. Nếu luật 0 chỉ nằm ở nhánh đa lượt thì ca này xanh sai: job
    ảnh sẽ được nhận ngay trong lúc LTT-3.8 đang cư trú trên card.
    """
    from platform_core.llm import admission

    _dat(db, R.LLM)
    ve, ly_do = admission.xet_va_giu(
        db, resource=TAI_NGUYEN_ANH, slots=1, user_id="u", mode="job",
        holder_id="w1", job_id="j1")
    assert ve is None and ly_do == L.CHO_RESIDENCY
    assert _so_lease(db, TAI_NGUYEN_ANH) == 0
    db.rollback()

    # Đối chứng: cùng lượt ấy, cửa sổ ảnh đang mở ⇒ được nhận.
    _dat(db, R.ANH)
    ve2, ly_do2 = admission.xet_va_giu(
        db, resource=TAI_NGUYEN_ANH, slots=1, user_id="u", mode="job",
        holder_id="w1", job_id="j1")
    assert ve2 is not None, ly_do2
    db.commit()


def test_hai_thanh_vien_khong_bao_gio_cung_mo(db, ban_do_anh):
    """Bất biến cốt tuỷ của D01 B, đọc qua CỬA chứ không qua bảng `TRANG_THAI_MO`:
    không trạng thái nào cho cả `ltt_38_3090` lẫn `anh_3090` được nhận."""
    from platform_core.llm import admission

    for tt in R.TRANG_THAI:
        _dat(db, tt)
        mo38 = _xin(db, holder="h38")[0] is not None
        db.rollback()
        mo_anh = admission.xet_va_giu(
            db, resource=TAI_NGUYEN_ANH, slots=1, user_id="u", mode="job",
            holder_id="wanh")[0] is not None
        db.rollback()
        assert not (mo38 and mo_anh), f"trang thai {tt!r} mo cua cho CA HAI"


# ── 3. Fail-closed, và giới hạn của nó ───────────────────────────────────────

def test_thieu_dong_gpu_residency_thi_dong_cua(db, caplog):
    """Không dòng = **chưa ai biết 3090 đang là của ai**. Đó không phải "mở"."""
    import logging

    with caplog.at_level(logging.WARNING, logger="platform_core.llm.admission"):
        assert _xin(db)[1] == L.CHO_RESIDENCY
    assert any("gpu_residency" in r.getMessage() for r in caplog.records), \
        "dong cua trong im lang: khong log gi"


def test_bang_gpu_residency_khong_doc_duoc_thi_dong_cua(db, monkeypatch):
    """Bảng chưa migrate ⇒ đóng, và giao dịch bên ngoài KHÔNG bị đầu độc:
    sau lượt đóng ấy, phiên vẫn dùng được (savepoint, không abort)."""
    from platform_core.models import GpuResidency

    _dat(db, R.LLM)
    that = db.get

    def no(lop, khoa, *a, **k):
        if lop is GpuResidency:
            raise RuntimeError("no such table: gpu_residency")
        return that(lop, khoa, *a, **k)

    monkeypatch.setattr(db, "get", no)
    assert _xin(db)[1] == L.CHO_RESIDENCY
    monkeypatch.undo()
    # Phiên còn sống: đọc được tiếp, và lượt sau (bảng đọc được) vẫn nhận.
    assert db.get(GpuResidency, NHOM_CU_TRU_38) is not None
    assert _xin(db, holder="sau")[0] is not None


def test_tai_nguyen_khong_nhom_cu_tru_khong_doi_mot_hanh_vi_nao(db):
    """Đường cũ, từng byte: bảng `gpu_residency` RỖNG mà tool cũ vẫn chạy.

    Đây là ca chặn hồi quy tốn nhất của Task 5.3: `residency_mo` mặc định `True`
    và bản đồ cư trú rỗng với mọi tài nguyên không khai — nếu hỏng, thứ dừng lại
    là giọng nói, ảnh ngoài 3090 và mọi app cũ, không phải 3090.
    """
    from platform_core.llm import admission
    from platform_core.models import GpuResidency

    assert db.query(GpuResidency).count() == 0
    ve = admission.acquire(db, resource="vieneu_gpu", slots=1, user_id="u1",
                           mode="sync", holder_id="h1")
    assert ve is not None and ve.lop == "" and ve.token_dat_truoc == 0
    db.commit()
    # ...và slot thứ hai vẫn bị chặn bởi ĐÚNG lý do cũ, không phải cư trú.
    ve2, ly_do2 = admission.xet_va_giu(db, resource="vieneu_gpu", slots=1,
                                       user_id="u2", mode="sync", holder_id="h2")
    assert ve2 is None and ly_do2 == L.CHO_SLOT


def test_ban_khai_lech_thi_nem_va_chi_nem_cho_tai_nguyen_do(monkeypatch):
    """Hai bản khai khác nhau cho một tên tài nguyên = bản khai tự mâu thuẫn."""
    from platform_core.llm import admission

    t1 = SimpleNamespace(name="a", admission_theo_model={
        "*": AdmissionModel(TAI_NGUYEN_ANH, 1, 0, NHOM_CU_TRU_38, R.THEO_LO)})
    t2 = SimpleNamespace(name="b", admission_theo_model={
        "*": AdmissionModel(TAI_NGUYEN_ANH, 1, 0, NHOM_CU_TRU_38, R.MAC_DINH)})
    monkeypatch.setattr("platform_core.registry.discover", lambda *a, **k: [
        SimpleNamespace(manifest=SimpleNamespace(slug="x", tools=(t1, t2)))])
    admission.quen_ban_do_cu_tru()
    try:
        with pytest.raises(ValueError):
            admission.nhom_cu_tru(TAI_NGUYEN_ANH)
        assert admission.nhom_cu_tru("khong_lien_can") == ("", "")
    finally:
        admission.quen_ban_do_cu_tru()


def test_ban_do_cu_tru_doc_tu_ban_khai_that():
    """Không gõ tay ánh xạ: `ltt_38_3090` phải ra `(rtx3090, mac_dinh)` từ chính
    `apps/ltt_llm/manifest.py`, còn `ltt_35_5060` phải KHÔNG có nhóm nào."""
    from platform_core.llm import admission

    admission.quen_ban_do_cu_tru()
    assert admission.nhom_cu_tru(TAI_NGUYEN_38) == (NHOM_CU_TRU_38, R.MAC_DINH)
    assert admission.nhom_cu_tru(TAI_NGUYEN_35) == ("", "")


# ── 4. Luật 0 LÀ luật 0 — và ca này phân biệt được thứ tự ─────────────────────

def _xet_sai_thu_tu(yc, giu, cho, ts) -> L.PhanXu:
    """Bản `xet` xếp cư trú SAU luật slot/ngân sách — thứ Task 5.3 KHÔNG làm.

    Có mặt ở đây để phép kiểm dưới nói được một điều mà "assert CHO_RESIDENCY"
    một mình không nói được: rằng cùng bộ đầu vào ấy, hai thứ tự cho hai câu trả
    lời KHÁC nhau. Nếu ca này xanh với cả hai thứ tự thì nó không kiểm gì cả.
    """
    if len(list(giu)) >= ts.so_slot:
        return L.PhanXu(False, L.CHO_SLOT)
    if not ts.residency_mo:
        return L.PhanXu(False, L.CHO_RESIDENCY)
    return L.xet(yc, giu, cho, ts)


def test_luat_0_chay_truoc_luat_slot_va_luat_ngan_sach():
    yc = L.Luot(id="moi", user_id="u", token_dat_truoc=200_000)
    day = [L.Luot(id=f"g{i}", user_id="k", token_dat_truoc=60_000) for i in range(2)]
    ts = L.ThamSo(so_slot=2, pool=100_000, residency_mo=False)

    # Lượt này vi phạm CẢ luật slot (2/2) và luật ngân sách (200K > 100K).
    assert L.xet(yc, day, [], ts).ly_do == L.CHO_RESIDENCY
    # Đối chứng thứ tự: xếp cư trú sau luật slot ⇒ mã lý do đổi.
    assert _xet_sai_thu_tu(yc, day, [], ts).ly_do == L.CHO_SLOT

    # Và chỉ vướng ngân sách: vẫn là cư trú, không phải `cho_ngan_sach`.
    ts1 = L.ThamSo(so_slot=4, pool=100_000, residency_mo=False)
    assert L.xet(yc, [], [], ts1).ly_do == L.CHO_RESIDENCY
    assert _xet_sai_thu_tu(yc, [], [], ts1).ly_do == L.CHO_RESIDENCY


def test_residency_mo_mac_dinh_la_true():
    """Mặc định là một lời khai, nên nó được kiểm như một lời khai."""
    assert L.ThamSo(so_slot=1).residency_mo is True
    assert L.xet(L.Luot(id="a", user_id="u"), [], [], L.ThamSo(so_slot=1)).nhan


def test_cho_residency_khong_giu_slot_khong_giu_ngan_sach(db):
    """Lượt chờ cư trú KHÔNG được tính vào, và không giữ, hai ngân sách kia.

    Cách đo: sau ba lượt bị từ chối vì cư trú, mở cửa ra thì **cả ba slot** và
    **toàn bộ pool** vẫn còn nguyên — nếu lượt bị từ chối có để lại dấu (dòng
    lease, token đặt chỗ) thì lượt lớn dưới đây sẽ không vừa.
    """
    _dat(db, R.ANH)
    for i in range(3):
        assert _xin(db, holder=f"h{i}", tok=POOL_38 // 2)[1] == L.CHO_RESIDENCY
        db.rollback()
    assert _so_lease(db, TAI_NGUYEN_38) == 0

    _dat(db, R.LLM)
    ve, ly_do = _xin(db, holder="lon", tok=POOL_38)
    assert ve is not None, ly_do
    assert ve.token_dat_truoc == POOL_38


# ── 5. Phòng chờ: nhịp tim khi chờ cư trú, và 429 khi hết ngân sách thời gian ─

def _yc(rid, resource=TAI_NGUYEN_38, pool=POOL_38, slots=SO_SLOT):
    from platform_core.llm.phong_cho import YeuCauCho

    return YeuCauCho(resource=resource, slots=slots, token_pool=pool, user_id="u",
                     mode="stream", holder_id=rid, request_id=rid, cua="stream",
                     lop=L.TUONG_TAC, token_dat_truoc=10_000, token_prefill_moi=1_000)


def test_stream_cho_vi_cu_tru_nhan_nhip_tim_lien_tuc_roi_duoc_nhan(db):
    """Chờ cư trú là CHỜ, không phải lỗi và không phải im lặng.

    Cửa stream dịch mỗi `yield` thành một chú thích SSE (`luong_co_cho`), nên
    điều phải đúng ở tầng này là: generator **yield đều** với mã lý do
    `cho_residency`, và mã ấy nằm trong sổ lượt ở cột `ly_do_cho`.
    """
    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter

    _dat(db, R.ANH)
    dh = DongHo()
    yc = _yc("r1")
    wid = phong_cho.vao(db, yc, now=dh())
    db.commit()

    g = phong_cho.cho_nhan(yc, waiter_id=wid, han_s=600.0, dong_ho=dh, ngu=dh.ngu)
    nhip = [next(g) for _ in range(4)]
    assert nhip == [L.CHO_RESIDENCY] * 4, nhip
    db.expire_all()
    assert db.get(LlmWaiter, wid).ly_do_cho == L.CHO_RESIDENCY

    _dat(db, R.LLM)
    with pytest.raises(StopIteration) as het:
        next(g)
    assert het.value.value, "duoc nhan thi phai tra ve lease_id"
    db.expire_all()
    w = db.get(LlmWaiter, wid)
    assert w.trang_thai == "nhan" and w.lease_id == het.value.value


def test_cho_dong_bo_qua_ngan_sach_thoi_gian_thi_het_cho_voi_ly_do_cu_tru(db):
    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter

    _dat(db, R.ANH)
    dh = DongHo()
    yc = _yc("r2")
    wid = phong_cho.vao(db, yc, now=dh())
    db.commit()

    with pytest.raises(phong_cho.HetCho) as e:
        phong_cho.cho_nhan_chan(yc, waiter_id=wid, han_s=5.0, dong_ho=dh,
                                ngu=dh.ngu, moi_nhip_s=1.0)
    assert e.value.ly_do == L.CHO_RESIDENCY
    db.expire_all()
    assert db.get(LlmWaiter, wid).trang_thai == "het_han"


def test_het_cho_o_cua_dong_bo_thanh_429_kem_retry_after():
    """`HetCho` ⇒ 429 + `Retry-After` — hai nửa, kiểm cả hai.

    Nửa thứ nhất là **đường đi**: nhánh `except phong_cho.HetCho` của
    `server/api/chat.py` ném `limits.execution_busy(..., retry_after=…)`. Đọc
    bằng AST chứ không bằng phép tìm chuỗi: một chú thích nhắc tên hàm không
    phải một lời gọi, và memory "bộ dò quét văn bản trừng phạt việc giải thích"
    nói đúng chỗ này.

    Nửa thứ hai là **cái ra dây**: `problem_response` phải đặt header thật.
    """
    from platform_core.public_api import limits, protocol
    from server.api.errors import problem_response

    cay = ast.parse((GOC / "server/api/chat.py").read_text(encoding="utf-8"))
    nhanh = [n for n in ast.walk(cay) if isinstance(n, ast.ExceptHandler)
             and n.type is not None and "HetCho" in ast.unparse(n.type)]
    assert nhanh, "cua dong bo khong con bat HetCho"
    for h in nhanh:
        goi = [c for c in ast.walk(h) if isinstance(c, ast.Call)
               and "execution_busy" in ast.unparse(c.func)]
        assert goi, ast.unparse(h)[:200]
        assert any("retry_after" in [k.arg for k in c.keywords] for c in goi)

    tl = problem_response(limits.execution_busy(TAI_NGUYEN_38, retry_after=7)
                          .problem(instance="/api/v1/chat"))
    assert tl.status_code == 429
    assert tl.headers[protocol.HEADER_RETRY_AFTER] == "7"


# ── 6. Sổ `cho_residency_s`: con số phải ĐÚNG, không chỉ phải có ─────────────

def test_cong_cho_residency_cong_dung_va_khong_cong_so_khong():
    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter

    w = LlmWaiter()
    assert phong_cho.cong_cho_residency(w, 1.5) is True
    assert phong_cho.cong_cho_residency(w, 2.0) is True
    assert w.cho_residency_s == pytest.approx(3.5)
    assert phong_cho.cong_cho_residency(w, 0.0) is False
    assert phong_cho.cong_cho_residency(w, -5.0) is False
    assert w.cho_residency_s == pytest.approx(3.5)


def test_cho_vi_cu_tru_vao_so_cho_residency_s_theo_dung_so_giay(db):
    """Ba nhịp cách nhau 2 s ⇒ HAI khoảng được quy về cư trú (nhịp đầu chưa có
    lý do nào trước nó), và con số nằm trong CSDL chứ không trong RAM."""
    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter

    _dat(db, R.ANH)
    dh = DongHo()
    yc = _yc("r3")
    wid = phong_cho.vao(db, yc, now=dh())
    db.commit()

    g = phong_cho.cho_nhan(yc, waiter_id=wid, han_s=600.0, dong_ho=dh, ngu=dh.ngu,
                           moi_nhip_s=2.0)
    for _ in range(3):
        next(g)
    db.expire_all()
    assert db.get(LlmWaiter, wid).cho_residency_s == pytest.approx(4.0)

    # Mở cửa ⇒ được nhận, và sổ NGỪNG tăng (khoảng cuối vẫn là chờ cư trú).
    _dat(db, R.LLM)
    with pytest.raises(StopIteration):
        next(g)
    db.expire_all()
    sau = db.get(LlmWaiter, wid).cho_residency_s
    assert sau == pytest.approx(6.0)


def test_cho_vi_THIEU_SLOT_khong_vao_so_cu_tru(db):
    """Đối chứng của phép đo trên: cùng cơ chế chờ, lý do khác ⇒ sổ cư trú = 0.

    Không có ca này thì "cộng mọi khoảng chờ vào `cho_residency_s`" cũng xanh —
    và cột sẽ nói cửa sổ ảnh gây ra mọi lần chờ của nền tảng.
    """
    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter

    _dat(db, R.LLM)
    for i in range(SO_SLOT):                     # lấp kín sức chứa
        ve, ld = _xin(db, user=f"giu{i}", holder=f"giu{i}", tok=1_000)
        assert ve is not None, ld
    db.commit()

    dh = DongHo()
    yc = _yc("r4")
    wid = phong_cho.vao(db, yc, now=dh())
    db.commit()
    g = phong_cho.cho_nhan(yc, waiter_id=wid, han_s=600.0, dong_ho=dh, ngu=dh.ngu,
                           moi_nhip_s=2.0)
    nhip = [next(g) for _ in range(3)]
    g.close()
    assert nhip == [L.CHO_SLOT] * 3, nhip
    db.expire_all()
    w = db.get(LlmWaiter, wid)
    assert w.cho_residency_s == 0.0 and w.ly_do_cho == L.CHO_SLOT


# ── 7. PostgreSQL: lật trạng thái giữa 50 lượt xin ───────────────────────────

from tests.pg_scratch import scratch_url  # noqa: E402 - cùng khuôn `test_73`

PG_URL = scratch_url()


@pytest.mark.skipif(not PG_URL,
                    reason="Can LTT_TEST_DATABASE_URL (PostgreSQL rieng) — khuon test_73")
def test_pg_lat_llm_sang_xa_llm_giua_50_luot_xin(monkeypatch):
    """Đây là phép kiểm DUY NHẤT nói được gì về đua: SQLite bỏ qua advisory lock.

    Hai điều được chốt, và chúng khác nhau:

    1. **Không cấp quá suất trong lúc lật** — 50 lượt cùng xin, một lượt lật
       `LLM → XA_LLM`; số lease cấp ra không bao giờ quá `SO_SLOT`.
    2. **Sau khi lật, KHÔNG một lease `ltt_38_3090` mới nào được cấp** — nhả hết
       lease của đợt một rồi hỏi thêm 20 lượt: cả 20 phải nhận `cho_residency`.
       Chốt thứ hai là chốt có nhân chứng vững: nó không dựa vào việc so hai
       đồng hồ ở hai luồng, mà dựa vào **trạng thái cuối** của sổ lease.
    """
    monkeypatch.setenv("LTT_DATABASE_URL", PG_URL)
    import platform_core.db as dbmod
    from platform_core.llm import admission
    from platform_core.models import ExecutionLease, GpuResidency

    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    admission.quen_ban_do_cu_tru()
    # Phanh chống ngập log của `_nhac` là trạng thái CẢ TIẾN TRÌNH: không xoá thì
    # ca "đóng cửa mà có nói ra" xanh/đỏ tuỳ thứ tự chạy của tệp này.
    admission._da_nhac.clear()
    gen = dbmod.get_session()
    s = next(gen)
    s.query(ExecutionLease).filter(
        ExecutionLease.resource == TAI_NGUYEN_38).delete()
    s.query(GpuResidency).filter(GpuResidency.nhom == NHOM_CU_TRU_38).delete()
    s.add(GpuResidency(nhom=NHOM_CU_TRU_38, trang_thai=R.LLM,
                       tu_luc=datetime.now(timezone.utc)))
    s.commit()
    s.close()

    N = 50
    rao = threading.Barrier(N)
    nhan: list[str] = []
    ly_do: list[str] = []

    def mot(i: int) -> None:
        g = dbmod.get_session()
        d = next(g)
        try:
            rao.wait()
            if i == 0:                      # trọng tài: lật cư trú
                dong = d.get(GpuResidency, NHOM_CU_TRU_38)
                dong.trang_thai = R.XA_LLM
                dong.phien_ban = int(dong.phien_ban or 0) + 1
                d.commit()
                return
            ve, ld = admission.xet_va_giu(
                d, resource=TAI_NGUYEN_38, slots=SO_SLOT, user_id=f"u{i}",
                mode="stream", holder_id=f"h{i}", token_pool=POOL_38,
                lop=L.TUONG_TAC, token_dat_truoc=1_000)
            d.commit()
            (nhan.append(ve.id) if ve is not None else ly_do.append(ld))
        finally:
            d.close()

    ts = [threading.Thread(target=mot, args=(i,)) for i in range(N)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    assert len(nhan) <= SO_SLOT, f"cap qua suat: {len(nhan)} > {SO_SLOT}"
    assert ly_do, "khong luot nao bi tu choi: phep kiem khong do duoc gi"

    # Nhả hết đợt một, rồi hỏi lại 20 lượt SAU khi đã lật.
    g = dbmod.get_session()
    d = next(g)
    try:
        d.query(ExecutionLease).filter(
            ExecutionLease.resource == TAI_NGUYEN_38).delete()
        d.commit()
        assert d.get(GpuResidency, NHOM_CU_TRU_38).trang_thai == R.XA_LLM
        sau = [admission.xet_va_giu(
            d, resource=TAI_NGUYEN_38, slots=SO_SLOT, user_id=f"v{i}",
            mode="stream", holder_id=f"g{i}", token_pool=POOL_38,
            lop=L.TUONG_TAC, token_dat_truoc=1_000) for i in range(20)]
        d.rollback()
        assert [ld for _ve, ld in sau] == [L.CHO_RESIDENCY] * 20
        assert d.query(ExecutionLease).filter(
            ExecutionLease.resource == TAI_NGUYEN_38).count() == 0
    finally:
        d.close()
        dbmod.reset_engine()
