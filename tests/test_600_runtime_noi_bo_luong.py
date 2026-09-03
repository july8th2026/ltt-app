"""
test_600 — `platform_core/runtime_noi_bo/luong.py`: cửa STREAM nội bộ. (H43 Phase 02)

Một app THỬ khai `ToolSpec` có `sync_executor` giả; `luong_vlm.mo` bị thay bằng
luồng SSE OpenAI giả — KHÔNG chạm máy B, KHÔNG cần khoá API, KHÔNG có `Principal`.

Sáu tính chất neo ở đây:

  1. Không Principal, không URL máy: chỉ `user_id` + tên tool + tham số.
  2. Thứ tự cửa: giữ chỗ TRƯỚC khi mở luồng; `response.started` phát TRƯỚC prefill.
  3. Sinh ít trả ít: token thật ⇒ thu đúng, hoàn phần dư; `billing.updated` nói đúng số.
  4. Bận ⇒ `response.failed{code:"ban"}` + hoàn đủ + nhả suất; không ném.
  5. Dừng giữa chừng (`.close()`) vẫn quyết toán phần đã sinh.
  6. Alias lạ / thiếu tiền / hết suất là ngoại lệ TRƯỚC byte đầu, chưa giữ tiền.
"""
from __future__ import annotations

import json
import uuid

import pytest

NL = bytes([10])
TOOL_THU = "text.thu"
JOB_THU = "appthu6.luong"
SLUG_THU = "appthu6"


# ── Executor giả — cùng bề mặt `apps/ltt_llm/executor.py` ────────────────────

class _ThamSoSai(ValueError):
    pass


class _ExecutorGia:
    parameter_error = _ThamSoSai

    @staticmethod
    def mac_dinh_cho(cua):
        return {"sync": 1024, "stream": 4096, "job": 4096}[cua]

    def aliases(self):
        return {"thu_alias": "noi-bo-model-1"}

    def model_id(self, alias):
        return self.aliases()[alias]

    def validate(self, params):
        return dict(params)

    def estimate_input(self, messages, tools=None):
        return sum(len(str(m.get("content", ""))) for m in messages) // 2 + 10

    def sync_output_cap(self, token_input, budget_seconds):
        return 1024

    def context_output_cap(self, token_input):
        return 40000


EXECUTOR_GIA = _ExecutorGia()


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "l.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    yield
    dbmod.reset_engine()


@pytest.fixture()
def app_luong(monkeypatch, moi_truong):
    """App thử có ToolSpec + sync_executor giả, cắm vào registry bằng monkeypatch."""
    from platform_core import registry as reg

    manifest = reg.AppManifest(
        slug=SLUG_THU, display_name="App thu luong", route_prefix=f"/{SLUG_THU}",
        job_types=(JOB_THU,), credit_cost=lambda p: 1,
        enabled=True, public=False, surface="runtime", lifecycle="internal",
        tools=(reg.ToolSpec(
            name=TOOL_THU, job_type=JOB_THU, description="tool thu",
            params_schema={"messages": {"type": "json[]", "required": True},
                           "model": {"type": "enum", "values": ["thu_alias"],
                                     "default": "thu_alias"}},
            returns={"content": "text"},
            admission_resource="thu_gpu", admission_slots=1,
            sync_executor="tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA",
        ),),
    )
    loaded = reg.LoadedApp(manifest=manifest, router=None)
    goc = reg.discover

    def discover_kem(apps_dir=None):
        return list(goc() if apps_dir is None else goc(apps_dir)) + [loaded]

    monkeypatch.setattr(reg, "discover", discover_kem)
    return manifest


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _user(credits=10_000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="l-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


def _so_du(user_id):
    from platform_core import credit
    gen, db = _session()
    try:
        return int(credit.so_du(db, user_id))
    finally:
        _close(gen)


def _sse(goi):
    return b"data: " + json.dumps(goi).encode() + NL + NL


def _khoi_openai(chu="xin chao", suy_nghi="", vao=100, ra=50, usage=True):
    ds = []
    if suy_nghi:
        ds.append(_sse({"choices": [{"delta": {"reasoning_content": suy_nghi}}]}))
    for phan in (chu[: len(chu) // 2], chu[len(chu) // 2:]):
        ds.append(_sse({"choices": [{"delta": {"content": phan}}]}))
    ds.append(_sse({"choices": [{"delta": {}, "finish_reason": "stop"}]}))
    if usage:
        ds.append(_sse({"choices": [], "usage": {"prompt_tokens": vao,
                                                 "completion_tokens": ra}}))
    ds.append(b"data: [DONE]" + NL + NL)
    return ds


def _dat_luong(monkeypatch, khoi=None, *, ban=False, nem=None):
    from platform_core.llm import luong_vlm
    da_goi = []

    class Gia:
        def __init__(self, ks):
            self.ma = 200
            self.content_type = "text/event-stream"
            self.luong = iter(ks)
            self.xong_voi = None
            self.hong_voi = None

        def xong(self, tokens=0):
            self.xong_voi = tokens

        def hong(self, exc):
            self.hong_voi = exc

    def mo(db, *, duong, than, timeout_s=900.0):
        da_goi.append({"duong": duong, "than": than})
        if ban:
            raise luong_vlm.KhongMoDuocLuong("may B dang ban", ban=True,
                                             thu_lai_sau_s=30)
        if nem is not None:
            raise nem
        return Gia(khoi if khoi is not None else _khoi_openai())

    monkeypatch.setattr(luong_vlm, "mo", mo)
    return da_goi


def _params(**g):
    d = {"model": "thu_alias", "messages": [{"role": "user", "content": "xin chao ban"}]}
    d.update(g)
    return d


def _chay(user_id, params, monkeypatch, **kw):
    from platform_core.runtime_noi_bo import luong
    gen, db = _session()
    try:
        return list(luong.mo_luong(db, user_id=user_id, tool_name=TOOL_THU,
                                   params=params, **kw))
    finally:
        _close(gen)


def _dem_lease():
    from platform_core.models import ExecutionLease
    gen, db = _session()
    try:
        return db.query(ExecutionLease).count()
    finally:
        _close(gen)


# ── 1+2. Không Principal, đúng thứ tự, đúng sự kiện ─────────────────────────

def test_luong_chay_tron_va_sinh_su_kien_canonical(app_luong, monkeypatch):
    da_goi = _dat_luong(monkeypatch, _khoi_openai("xin chao", suy_nghi="nghi da"))
    u = _user(1000)
    sk = _chay(u, _params(), monkeypatch)
    loai = [s["type"] for s in sk]
    assert loai[0] == "response.started"
    assert loai[-1] == "billing.updated"
    assert "reasoning.delta" in loai and "response.delta" in loai
    assert "usage.updated" in loai and "response.completed" in loai
    assert "".join(s["text"] for s in sk if s["type"] == "response.delta") == "xin chao"
    assert [s["text"] for s in sk if s["type"] == "reasoning.delta"] == ["nghi da"]
    xong = next(s for s in sk if s["type"] == "response.completed")
    assert xong["finish_reason"] == "stop"

    # Thân gửi lên máy B: alias đã dịch sang id nội bộ, xin usage, có stream.
    than = da_goi[0]["than"]
    assert da_goi[0]["duong"] == "/v1/chat/completions"
    assert than["model"] == "noi-bo-model-1"
    assert than["stream"] is True
    assert than["stream_options"] == {"include_usage": True}
    assert than["max_tokens"] == 4096            # mặc định CỬA STREAM của executor
    # `response.started` không lộ id nội bộ.
    assert sk[0]["model"] == "thu_alias"
    assert "noi-bo-model-1" not in json.dumps(sk)


def test_response_started_phat_TRUOC_khi_mo_luong(app_luong, monkeypatch):
    """D7: byte đầu phải tới trước prefill — `started` ra trước `luong_vlm.mo`."""
    from platform_core.runtime_noi_bo import luong
    da_goi = _dat_luong(monkeypatch)
    u = _user(1000)
    gen, db = _session()
    try:
        it = luong.mo_luong(db, user_id=u, tool_name=TOOL_THU, params=_params())
        dau = next(it)
        assert dau["type"] == "response.started"
        assert da_goi == []                     # chưa chạm máy B
        assert dau["credit_giu"] > 0            # nhưng tiền ĐÃ giữ
        assert _so_du(u) == 1000 - dau["credit_giu"]
        list(it)
    finally:
        _close(gen)


# ── 3. Sinh ít trả ít ────────────────────────────────────────────────────────

def test_thu_dung_theo_usage_va_hoan_phan_du(app_luong, monkeypatch):
    _dat_luong(monkeypatch, _khoi_openai(vao=100, ra=50))
    u = _user(1000)
    # 30.000 token ra ⇒ giữ ~12 credit; sinh 50 ⇒ thu 1 (làm tròn lên). Hai số
    # phải KHÁC nhau thì phép kiểm "hoàn phần dư" mới có nghĩa.
    sk = _chay(u, _params(max_tokens=30000), monkeypatch)
    tien = sk[-1]
    assert tien["type"] == "billing.updated"
    assert tien["do_duoc"] is True
    assert 0 < tien["credit_thu"] < tien["credit_giu"]
    assert tien["credit_giu"] - tien["credit_thu"] == tien["credit_hoan"]
    assert _so_du(u) == 1000 - tien["credit_thu"]
    usage = next(s for s in sk if s["type"] == "usage.updated")
    assert (usage["token_vao"], usage["token_ra"]) == (100, 50)
    assert _dem_lease() == 0                    # suất đã nhả


def test_khong_do_duoc_usage_thi_hoan_du_thu_0(app_luong, monkeypatch):
    _dat_luong(monkeypatch, _khoi_openai(usage=False))
    u = _user(1000)
    sk = _chay(u, _params(), monkeypatch)
    tien = sk[-1]
    assert tien["credit_thu"] == 0 and tien["do_duoc"] is False
    assert _so_du(u) == 1000


# ── 4. Bận ⇒ sự kiện, hoàn đủ, nhả suất ─────────────────────────────────────

def test_may_B_ban_thi_failed_ban_va_hoan_du(app_luong, monkeypatch):
    _dat_luong(monkeypatch, ban=True)
    u = _user(1000)
    sk = _chay(u, _params(), monkeypatch)
    loai = [s["type"] for s in sk]
    assert loai == ["response.started", "response.failed", "billing.updated"]
    assert sk[1]["code"] == "ban" and sk[1]["retry_after_s"] == 30
    assert sk[2]["credit_thu"] == 0
    assert _so_du(u) == 1000
    assert _dem_lease() == 0


def test_het_suat_thuc_thi_la_ngoai_le_truoc_byte_dau(app_luong, monkeypatch):
    from platform_core.llm import admission
    from platform_core.runtime_noi_bo import luong
    _dat_luong(monkeypatch)
    u = _user(1000)
    gen, db = _session()
    try:
        lease = admission.acquire(db, resource="thu_gpu", slots=1, user_id="khac",
                                  mode="job", holder_id="job-khac")
        assert lease is not None
        db.commit()
        with pytest.raises(luong.DangBan) as ex:
            next(luong.mo_luong(db, user_id=u, tool_name=TOOL_THU, params=_params()))
        assert ex.value.nguon == "suat" and ex.value.tai_nguyen == "thu_gpu"
        assert _so_du(u) == 1000                # chưa giữ tiền
    finally:
        _close(gen)


# ── 5. Dừng giữa chừng vẫn quyết toán phần đã sinh ──────────────────────────

def test_dong_generator_giua_chung_van_quyet_toan(app_luong, monkeypatch):
    khoi = [_sse({"choices": [{"delta": {"content": "a"}}],
                  "usage": {"prompt_tokens": 100, "completion_tokens": 20}})]
    khoi += [_sse({"choices": [{"delta": {"content": "b"}}]})] * 5
    _dat_luong(monkeypatch, khoi)
    from platform_core.runtime_noi_bo import luong
    u = _user(1000)
    gen, db = _session()
    try:
        it = luong.mo_luong(db, user_id=u, tool_name=TOOL_THU,
                            params=_params(max_tokens=30000))
        dau = next(it)
        giu = dau["credit_giu"]
        assert next(it)["type"] == "response.delta"
        it.close()                              # người dùng bấm Dừng
    finally:
        _close(gen)
    thu = 1000 - _so_du(u)
    assert 0 < thu < giu                        # thu phần đã sinh, hoàn phần dư
    assert _dem_lease() == 0


# ── 6. Lỗi của bên gọi: trước tiền, trước GPU ───────────────────────────────

def test_alias_la_thi_ThamSoSai_chua_giu_tien(app_luong, monkeypatch):
    from platform_core.runtime_noi_bo import luong
    da_goi = _dat_luong(monkeypatch)
    u = _user(1000)
    gen, db = _session()
    try:
        with pytest.raises(luong.ThamSoSai):
            next(luong.mo_luong(db, user_id=u, tool_name=TOOL_THU,
                                params=_params(model="qwen-that")))
    finally:
        _close(gen)
    assert da_goi == [] and _so_du(u) == 1000


def test_thieu_credit_la_ThieuCredit_chua_cham_GPU(app_luong, monkeypatch):
    from platform_core.runtime_noi_bo import luong
    da_goi = _dat_luong(monkeypatch)
    u = _user(0)
    gen, db = _session()
    try:
        with pytest.raises(luong.ThieuCredit):
            next(luong.mo_luong(db, user_id=u, tool_name=TOOL_THU, params=_params()))
    finally:
        _close(gen)
    assert da_goi == [] and _dem_lease() == 0


def test_ten_tool_la_thi_KhongCoNangLuc(app_luong, monkeypatch):
    from platform_core.runtime_noi_bo import luong
    u = _user(10)
    gen, db = _session()
    try:
        with pytest.raises(luong.KhongCoNangLuc):
            next(luong.mo_luong(db, user_id=u, tool_name="text.khong_co",
                                params=_params()))
    finally:
        _close(gen)


# ── Đường byte thô cho `/api/v1` dùng CÙNG lắp ráp ───────────────────────────

def test_mo_luong_tho_chuyen_byte_nguyen_xi_va_quyet_toan(app_luong, monkeypatch):
    from platform_core.runtime_noi_bo import luong
    ks = _khoi_openai("nguyen xi", vao=10, ra=5)
    _dat_luong(monkeypatch, list(ks))
    u = _user(1000)
    gen, db = _session()
    try:
        luot = luong.mo_luong_tho(db, user_id=u, tool_name=TOOL_THU,
                                  than=_params(), duong="/v1/messages")
        ra = list(luot.luong)
    finally:
        _close(gen)
    assert b"".join(ra) == b"".join(ks)         # không sửa một byte
    assert luot.ket_thuc == "xong"
    assert luot.ket_qua is not None and luot.ket_qua.thu_credit >= 1
    assert luot.chuan_bi.than_gui["max_tokens"] == 4096
    assert _dem_lease() == 0
