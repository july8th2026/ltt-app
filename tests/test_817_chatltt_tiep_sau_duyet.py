"""
test_817 — `luot_v3.tiep_sau_duyet()`: MỐI NỐI, không phải mảnh. (H44 P04)

`test_809`…`test_816` kiểm từng mảnh và đều xanh. Nhưng ba hàm **khâu chúng lại**
— `tiep_sau_duyet`, `chay_tiep_nen`, `_danh_thuc_run` — **không phép kiểm nào
chạm tới** (đo 05/09: 0 tệp nhắc tên chúng).

⭐ Đó đúng hình dạng của lỗi `LOAI_KHOI` vừa tìm được bằng trình duyệt: các mảnh
được kiểm kỹ, mối nối thì không — và mối nối là chỗ duy nhất biết cả hai bên.

Tệp này chạy đúng con đường sau khi người dùng bấm "đồng ý":

    run dung o AWAITING_APPROVAL  (trong CSDL, khong con trong RAM)
      -> tiep_sau_duyet() dung lai Run tu CSDL
      -> chay tool da duyet
      -> goi model vong sau
      -> dong so: trang thai, tien, khoi noi dung
"""
from __future__ import annotations

import json
import re
import threading
import uuid

import pytest

NL = bytes([10])


def _sse(g):
    return b"data: " + json.dumps(g).encode() + NL + NL


def _chu(t):
    return [_sse({"choices": [{"delta": {"content": t}, "finish_reason": "stop"}]}),
            _sse({"choices": [], "usage": {"prompt_tokens": 30, "completion_tokens": 5}}),
            b"data: [DONE]" + NL + NL]


def _goi_tool(ten, doi_so):
    return [_sse({"choices": [{"delta": {"tool_calls": [
                {"index": 0, "id": "call_1", "type": "function",
                 "function": {"name": ten, "arguments": doi_so}}]}}]}),
            _sse({"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}),
            _sse({"choices": [], "usage": {"prompt_tokens": 60, "completion_tokens": 9}}),
            b"data: [DONE]" + NL + NL]


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "s.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    from fastapi.testclient import TestClient
    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-817",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    from apps.chatltt.services import luot as LUOT

    def inline(execution_id, *, user_id):
        LUOT.chay(execution_id, user_id=user_id)
        return threading.current_thread()

    monkeypatch.setattr(LUOT, "khoi_chay_nen", inline)
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


@pytest.fixture()
def may(monkeypatch):
    from platform_core import registry as reg
    from platform_core.llm import luong_vlm
    from tests.test_600_runtime_noi_bo_luong import EXECUTOR_GIA  # noqa: F401

    tool = reg.ToolSpec(name="text.chat", job_type="t817.j", description="d",
                        params_schema={"messages": {"type": "json[]"},
                                       "tools": {"type": "json[]"},
                                       "model": {"type": "enum", "values": ["thu_alias"],
                                                 "default": "thu_alias"}},
                        returns={"content": "text"},
                        admission_resource="thu_gpu817", admission_slots=1,
                        sync_executor="tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA")
    man = reg.AppManifest(slug="t817", display_name="t817", route_prefix="/t817",
                          job_types=("t817.j",), credit_cost=lambda p: 1,
                          surface="runtime", lifecycle="internal", tools=(tool,))
    goc = reg.discover
    loaded = reg.LoadedApp(manifest=man, router=None)
    monkeypatch.setattr(reg, "discover",
                        lambda apps_dir=None: [x for x in goc()
                                               if x.manifest.slug != "ltt_llm"] + [loaded])

    class Kho:
        def __init__(self):
            self.than, self.luot = [], []

        def dat(self, *luot):
            self.luot = list(luot)
            return self

    kho = Kho()

    class Gia:
        ma, content_type = 200, "text/event-stream"

        def __init__(self, ks):
            self.luong = iter(ks)

        def xong(self, tokens=0):
            pass

        def hong(self, exc):
            pass

    monkeypatch.setattr(luong_vlm, "mo",
                        lambda db, *, duong, than, timeout_s=900.0:
                        (kho.than.append(than),
                         Gia(kho.luot.pop(0) if kho.luot else _chu("mac dinh")))[1])
    return kho


@pytest.fixture(autouse=True)
def _tool_co_phi(monkeypatch):
    """⭐ Biến `noi_bo.tinh` thành `PAID` — nên nó **cần duyệt** nhưng vẫn chạy
    ĐỒNG BỘ (không phải job). Tệp này kiểm mối nối chạy-tiếp, không kiểm hàng
    đợi job; trộn hai thứ thì một phép kiểm đỏ không nói được đỏ vì cái nào."""
    from apps.chatltt.services import chieu_tool as C
    monkeypatch.setitem(C.LOP_CUA, "noi_bo.tinh", C.PAID)
    monkeypatch.setattr(C, "CHO_MODEL_GOI", ("noi_bo.tinh",))


@pytest.fixture(autouse=True)
def _bao_gia(monkeypatch):
    from apps.chatltt.services import luot_v3
    monkeypatch.setattr(luot_v3, "_bao_gia",
                        lambda db, *, user_id, conv_id: (
                            lambda ten, ds: (5, "gia-thu-817")))


@pytest.fixture()
def bat_co(monkeypatch):
    from apps.chatltt.services import co_v3
    monkeypatch.setenv(co_v3.CO_TOOLS, "1")


def _user(credits=5000):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "s817-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12",
                           is_verified=True)
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id, email
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _phien(app, email):
    from fastapi.testclient import TestClient
    c = TestClient(app, base_url="https://testserver")
    r = c.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    c.post("/login", data={"username": email, "password": "a-good-password-12",
                           "csrf_token": m.group(1), "next": "/chatltt"},
           follow_redirects=True)
    csrf = re.search(r'data-csrf="([^"]+)"', c.get("/chatltt").text).group(1)
    return c, {"X-CSRF-Token": csrf}


def _phien_db():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _dong(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _dung_cho_duyet(web, may, chu="tinh 8123*4471"):
    """Gửi một lượt, model đòi tool có phí ⇒ run dừng ở `AWAITING_APPROVAL`."""
    may.dat(_goi_tool("noi_bo.tinh", '{"bieu_thuc": "8123*4471"}'))
    uid, email = _user()
    c, h = _phien(web.app, email)
    cv = c.post("/chatltt/api/hoi-thoai", json={"model_alias": "thu_alias"},
                headers=h).json()["id"]
    r = c.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": chu}, headers=h)
    assert r.status_code == 202, r.text
    return uid, c, h, cv


def _run_dang_cho(user_id):
    from apps.chatltt.tables import ChatlttRun
    gen, db = _phien_db()
    try:
        r = db.query(ChatlttRun).filter_by(user_id=user_id).one()
        return r.id, r.trang_thai
    finally:
        _dong(gen)


class SoGia:
    """`dang_chay.LuotDangChay` giả — chỉ cần `phat` và `dung`."""

    def __init__(self):
        self.sk = []
        self.dung = threading.Event()
        self.execution_id = "ex-gia"

    def phat(self, sk):
        self.sk.append(sk)


# ── 1. Dừng đúng chỗ ───────────────────────────────────────────────────────

def test_tool_co_phi_lam_run_dung_o_AWAITING_APPROVAL(web, may, bat_co):
    uid, c, h, _cv = _dung_cho_duyet(web, may)
    _rid, tt = _run_dang_cho(uid)
    assert tt == "AWAITING_APPROVAL"
    ds = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"]
    assert len(ds) == 1 and ds[0]["credit"] == 5


# ── 2. MỐI NỐI: `tiep_sau_duyet` dựng lại từ CSDL và chạy hết ──────────────

def test_tiep_sau_duyet_chay_het_luot(web, may, bat_co):
    """🔴 Đây là hàm chưa phép kiểm nào chạm tới. Nó khâu `dung_lai` +
    `ket_qua_sau_duyet` + `tiep_tuc` + `_dong` — bốn mảnh đều xanh riêng lẻ."""
    from apps.chatltt.services import duyet as D
    from apps.chatltt.services import luot_v3

    uid, c, h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    ap = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"][0]

    may.dat(_chu("Ket qua la 36317933."))
    gen, db = _phien_db()
    try:
        D.duyet(db, user_id=uid, approval_id=ap["approval_id"])
        db.commit()
        run = luot_v3.tiep_sau_duyet(db, run_id=rid, user_id=uid, so=SoGia())
    finally:
        _dong(gen)

    assert run.trang_thai == "COMPLETED"
    assert run.ly_do_ket == "xong"
    assert run.van_ban_cuoi == "Ket qua la 36317933."


def test_ket_qua_tool_that_su_toi_duoc_vong_sau(web, may, bat_co):
    """Mối nối dễ đứt nhất: tool chạy đúng nhưng kết quả không vào lịch sử."""
    from apps.chatltt.services import duyet as D
    from apps.chatltt.services import luot_v3

    uid, c, h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    ap = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"][0]

    may.dat(_chu("xong"))
    gen, db = _phien_db()
    try:
        D.duyet(db, user_id=uid, approval_id=ap["approval_id"])
        db.commit()
        luot_v3.tiep_sau_duyet(db, run_id=rid, user_id=uid, so=SoGia())
    finally:
        _dong(gen)

    vai = [m["role"] for m in may.than[-1]["messages"]]
    assert vai[-2:] == ["assistant", "tool"]
    assert "36317933" in str(may.than[-1]["messages"][-1]["content"])


def test_dong_so_run_va_buoc_xuong_CSDL(web, may, bat_co):
    from sqlalchemy import text

    from apps.chatltt.services import duyet as D
    from apps.chatltt.services import luot_v3

    uid, c, h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    ap = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"][0]

    may.dat(_chu("xong"))
    gen, db = _phien_db()
    try:
        D.duyet(db, user_id=uid, approval_id=ap["approval_id"])
        db.commit()
        luot_v3.tiep_sau_duyet(db, run_id=rid, user_id=uid, so=SoGia())
        db.commit()
    finally:
        _dong(gen)

    gen, db = _phien_db()
    try:
        r = db.execute(text("SELECT trang_thai, so_vong_model, ly_do_ket "
                            "FROM chatltt_run")).one()
        assert r == ("COMPLETED", 2, "xong")
        treo = db.execute(text("SELECT COUNT(*) FROM chatltt_step "
                               "WHERE trang_thai='cho_duyet'")).scalar()
        assert treo == 0, "buoc treo phai da co ket qua"
    finally:
        _dong(gen)


def test_TU_CHOI_roi_tiep_sau_duyet_van_ket_tu_te(web, may, bat_co):
    from apps.chatltt.services import duyet as D
    from apps.chatltt.services import luot_v3

    uid, c, h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    ap = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"][0]

    may.dat(_chu("Ban da tu choi, toi tra loi bang loi vay."))
    gen, db = _phien_db()
    try:
        D.tu_choi(db, user_id=uid, approval_id=ap["approval_id"])
        db.commit()
        run = luot_v3.tiep_sau_duyet(db, run_id=rid, user_id=uid, so=SoGia())
    finally:
        _dong(gen)

    assert run.trang_thai == "COMPLETED" and run.ly_do_ket == "xong"
    assert "TU CHOI" in str(may.than[-1]["messages"][-1]["content"])


# ── 3. Fail-closed ở mối nối ───────────────────────────────────────────────

def test_CHUA_bam_thi_tiep_sau_duyet_NEM(web, may, bat_co):
    """⛔ Chạy tiếp khi người dùng chưa trả lời là chạy một việc không ai duyệt."""
    from apps.chatltt.services import luot_v3

    uid, _c, _h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    gen, db = _phien_db()
    try:
        with pytest.raises(ValueError, match="thieu ket qua duyet"):
            luot_v3.tiep_sau_duyet(db, run_id=rid, user_id=uid, so=SoGia())
    finally:
        _dong(gen)


def test_nguoi_KHAC_khong_chay_tiep_duoc(web, may, bat_co):
    """🔴 `run_id` đoán được mà chạy tiếp được là một đường tiêu tiền người khác."""
    from apps.chatltt.services import luot_v3

    uid, _c, _h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    gen, db = _phien_db()
    try:
        with pytest.raises(luot_v3.KhongChayTiepDuoc):
            luot_v3.tiep_sau_duyet(db, run_id=rid, user_id="u-nguoi-la", so=SoGia())
    finally:
        _dong(gen)


def test_run_DA_XONG_khong_chay_tiep_duoc(web, may, bat_co):
    """Một run `COMPLETED` mà chạy lại được là một run tính tiền hai lần."""
    from apps.chatltt.services import duyet as D
    from apps.chatltt.services import luot_v3

    uid, c, h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    ap = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"][0]

    may.dat(_chu("xong"))
    gen, db = _phien_db()
    try:
        D.duyet(db, user_id=uid, approval_id=ap["approval_id"])
        db.commit()
        luot_v3.tiep_sau_duyet(db, run_id=rid, user_id=uid, so=SoGia())
        db.commit()
        with pytest.raises(luot_v3.KhongChayTiepDuoc):
            luot_v3.tiep_sau_duyet(db, run_id=rid, user_id=uid, so=SoGia())
    finally:
        _dong(gen)


def test_run_khong_co_that(web, may, bat_co):
    from apps.chatltt.services import luot_v3
    gen, db = _phien_db()
    try:
        with pytest.raises(luot_v3.KhongChayTiepDuoc):
            luot_v3.tiep_sau_duyet(db, run_id="run_bia", user_id="u1", so=SoGia())
    finally:
        _dong(gen)


# ── 4. Cổng `nen_chay_tiep` khớp với thực tế ───────────────────────────────

def test_nen_chay_tiep_dung_theo_tung_giai_doan(web, may, bat_co):
    from apps.chatltt.services import duyet as D
    from apps.chatltt.services import luot_v3

    uid, c, h, _cv = _dung_cho_duyet(web, may)
    rid, _ = _run_dang_cho(uid)
    ap = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"][0]

    gen, db = _phien_db()
    try:
        assert luot_v3.nen_chay_tiep(db, user_id=uid, run_id=rid) is False
        D.duyet(db, user_id=uid, approval_id=ap["approval_id"])
        db.commit()
        assert luot_v3.nen_chay_tiep(db, user_id=uid, run_id=rid) is True
        assert luot_v3.nen_chay_tiep(db, user_id="u-la", run_id=rid) is False
    finally:
        _dong(gen)
