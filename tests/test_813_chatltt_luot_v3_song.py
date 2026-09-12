"""
test_813 — một lượt agentic THẬT, đi qua `luot.chay`. (H44 P04)

Từ 800 tới 812 mỗi tệp ghim một mảnh. Tệp này là mảnh cuối và là mảnh duy nhất
đi qua **đúng cửa người dùng đi**: gửi một tin nhắn, và ChatLTT tự gọi tool rồi
trả lời.

Ba mệnh đề, và mệnh đề đầu là mệnh đề của đường lùi:

  1. **Cờ tắt ⇒ V3 không tồn tại.** Đúng một vòng model, không `chatltt_run`
     nào, `params` không có khoá `tools`.
  2. Cờ bật ⇒ nhiều vòng, mỗi vòng **một `chatltt_execution` riêng** cùng
     `run_id` (R2), và một `chatltt_run` tổng hợp.
  3. Khối `tool_call` nối vào `blocks` mà **không** đè phần chữ — hình dạng cũ,
     phần tử mới (A5).
"""
from __future__ import annotations

import json
import re
import threading
import uuid

import pytest

#: 🔴 BÍ DANH CỦA TOOL THỬ PHẢI LÀ MỘT MODEL **CÓ GIÁ** (D07, dual-model 2.5).
#:    Trước 2.5 chỗ này là chuỗi bịa `_ALIAS_THU` và nó chạy được **chỉ vì**
#:    `gia_token` bỏ qua model. Từ D07 giá đi theo model, nên mọi tool đi qua
#:    `runtime_noi_bo/luong.py` — tức qua `thanh_toan` — phải khai một model mà
#:    bảng giá biết. Đây là ràng buộc thật của tầng đó, không phải phiền toái
#:    của phép kiểm: một model không có giá mà vẫn giữ được tiền nghĩa là tiền
#:    đang được tính bằng bảng giá của một model **khác**.
#:
#: ⛔ Lấy từ `gia_token`, đừng gõ thẳng `"ltt-3.8"`: ngày đổi model mặc định thì
#:    một hằng số gõ tay sẽ làm sáu tệp này hỏng lại cùng lúc.
from platform_core.llm.gia_token import MODEL_GIA_MAC_DINH as _ALIAS_THU

NL = bytes([10])


def _sse(g):
    return b"data: " + json.dumps(g).encode() + NL + NL


def _chu(t, ly_do="stop"):
    return [_sse({"choices": [{"delta": {"content": t}, "finish_reason": ly_do}]}),
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
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-813",
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
    """Máy B giả. `may.dat(*luot)` xếp sẵn một luồng SSE cho mỗi vòng model."""
    from platform_core import registry as reg
    from platform_core.llm import luong_vlm
    from tests.test_600_runtime_noi_bo_luong import EXECUTOR_GIA  # noqa: F401

    tool = reg.ToolSpec(name="text.chat", job_type="t813.j", description="d",
                        params_schema={"messages": {"type": "json[]"},
                                       "tools": {"type": "json[]"},
                                       "model": {"type": "enum", "values": [_ALIAS_THU],
                                                 "default": _ALIAS_THU}},
                        returns={"content": "text"},
                        admission_resource="thu_gpu813", admission_slots=1,
                        sync_executor="tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA")
    man = reg.AppManifest(slug="t813", display_name="t813", route_prefix="/t813",
                          job_types=("t813.j",), credit_cost=lambda p: 1,
                          surface="runtime", lifecycle="internal", tools=(tool,))
    goc = reg.discover
    loaded = reg.LoadedApp(manifest=man, router=None)
    monkeypatch.setattr(reg, "discover",
                        lambda apps_dir=None: [x for x in goc()
                                               if x.manifest.slug != "ltt_llm"] + [loaded])

    class Kho:
        def __init__(self):
            self.than = []
            self.luot = []

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

    def mo(db, *, duong, than, timeout_s=900.0):
        kho.than.append(than)
        return Gia(kho.luot.pop(0) if kho.luot else _chu("mac dinh"))

    monkeypatch.setattr(luong_vlm, "mo", mo)
    return kho


def _user(credits=5000):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "s813-" + uuid.uuid4().hex[:6] + "@example.com"
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


def _gui(c, h, chu="tinh 8123 * 4471 giup toi"):
    cv = c.post("/chatltt/api/hoi-thoai", json={"model_alias": _ALIAS_THU},
                headers=h).json()["id"]
    r = c.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": chu}, headers=h)
    assert r.status_code == 202, r.text
    return cv, r.json()["execution_id"]


def _su_that(c, h, cv):
    return c.get(f"/chatltt/api/hoi-thoai/{cv}", headers=h).json()


def _dem(bang):
    from platform_core.db import get_session
    from sqlalchemy import text
    gen = get_session()
    db = next(gen)
    try:
        return db.execute(text(f"SELECT COUNT(*) FROM {bang}")).scalar()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── 1. Cờ TẮT ⇒ V3 không tồn tại ───────────────────────────────────────────

def test_co_TAT_thi_mot_vong_khong_run_khong_khoa_tools(web, may):
    """⛔ Điều kiện của đường lùi (`02_ADR` §7). Cờ tắt mà `params` vẫn khác V1
    dù một khoá thì "tắt cờ để lùi" là một câu trong tài liệu, không phải cơ chế.

    ⭐ Và `tools` không chỉ là một khoá thừa: có nó là **bật cưỡng chế sinh**
       bằng văn phạm GBNF (`01_M1_NATIVE_HAY_GENERIC.md` §5b).
    """
    may.dat(_chu("8123 * 4471 = 36317933"))
    _uid, email = _user()
    c, h = _phien(web.app, email)
    cv, _ex = _gui(c, h)

    assert len(may.than) == 1, "cho dung MOT vong model"
    assert "tools" not in may.than[0]
    assert "parallel_tool_calls" not in may.than[0]
    assert _dem("chatltt_run") == 0 and _dem("chatltt_step") == 0

    tin = _su_that(c, h, cv)["messages"][-1]
    assert tin["status"] == "done"
    assert [k["type"] for k in tin["blocks"]] == ["text"]


# ── 2. Cờ BẬT ⇒ vòng lặp thật ──────────────────────────────────────────────

@pytest.fixture()
def bat_co(monkeypatch):
    from apps.chatltt.services import co_v3
    monkeypatch.setenv(co_v3.CO_TOOLS, "1")


def test_co_BAT_thi_model_goi_tool_roi_tra_loi(web, may, bat_co):
    may.dat(_goi_tool("noi_bo.tinh", '{"bieu_thuc": "8123*4471"}'),
            _chu("Ket qua la 36317933."))
    _uid, email = _user()
    c, h = _phien(web.app, email)
    cv, _ex = _gui(c, h)

    assert len(may.than) == 2, "mot vong goi tool + mot vong tra loi"
    assert may.than[0]["tools"], "vong dau phai mang khoi tools"
    assert may.than[0]["parallel_tool_calls"] is True

    tin = _su_that(c, h, cv)["messages"][-1]
    assert tin["status"] == "done"
    loai = [k["type"] for k in tin["blocks"]]
    assert "tool_call" in loai and "text" in loai
    assert loai.index("tool_call") < loai.index("text"), (
        "khoi tool phai dung TRUOC phan chu — cau tra loi can ngu canh cua chinh no")
    chu = [k for k in tin["blocks"] if k["type"] == "text"][0]["text"]
    assert "36317933" in chu


def test_ket_qua_tool_that_su_toi_duoc_vong_hai(web, may, bat_co):
    """🔴 Mắt xích dễ đứt nhất: tool chạy đúng nhưng kết quả không vào lịch sử,
    và model vòng hai trả lời như chưa từng gọi gì."""
    may.dat(_goi_tool("noi_bo.tinh", '{"bieu_thuc": "8123*4471"}'), _chu("xong"))
    _uid, email = _user()
    c, h = _phien(web.app, email)
    _gui(c, h)

    vai = [m["role"] for m in may.than[1]["messages"]]
    assert vai[-2:] == ["assistant", "tool"], (
        "phai co CA assistant mang tool_calls VA ket qua tool")
    assert "36317933" in str(may.than[1]["messages"][-1]["content"])


def test_MOI_VONG_mot_execution_rieng_cung_run_id(web, may, bat_co):
    """⭐ R2: ba cột tiền của `chatltt_execution` **vẫn đúng** cho thứ chúng đo —
    một lần gọi model. Dùng lại một hàng cho N vòng làm chúng cộng dồn, và lúc
    ấy không còn đối chiếu được với `credit_entries`."""
    from platform_core.db import get_session
    from sqlalchemy import text
    may.dat(_goi_tool("noi_bo.tinh", '{"bieu_thuc": "2+2"}'), _chu("bang 4"))
    _uid, email = _user()
    c, h = _phien(web.app, email)
    _gui(c, h)

    gen = get_session()
    db = next(gen)
    try:
        hang = db.execute(text(
            "SELECT run_id, COUNT(*) FROM chatltt_execution GROUP BY run_id")).all()
        assert len(hang) == 1, "tat ca phai cung MOT run_id"
        assert hang[0][0], "run_id khong duoc NULL o duong V3"
        assert hang[0][1] == 2, "hai vong model = hai execution"
        r = db.execute(text("SELECT trang_thai, so_vong_model, ly_do_ket "
                            "FROM chatltt_run")).one()
        assert r == ("COMPLETED", 2, "xong")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_buoc_duoc_ghi_xuong_chatltt_step(web, may, bat_co):
    from platform_core.db import get_session
    from sqlalchemy import text
    may.dat(_goi_tool("noi_bo.tinh", '{"bieu_thuc": "2+2"}'), _chu("bang 4"))
    _uid, email = _user()
    c, h = _phien(web.app, email)
    _gui(c, h)

    gen = get_session()
    db = next(gen)
    try:
        ds = db.execute(text("SELECT loai, tool_name, trang_thai, doi_so_tho "
                             "FROM chatltt_step ORDER BY thu_tu")).all()
        assert [x[0] for x in ds] == ["model", "tool", "model"]
        assert ds[1][1] == "noi_bo.tinh" and ds[1][2] == "ok"
        assert ds[1][3] == '{"bieu_thuc": "2+2"}', "chuoi THO phai qua duoc"
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_tool_bia_ten_bi_chan_va_model_doc_duoc_loi(web, may, bat_co):
    """⛔ Cổng thứ tư đứng cả khi model tệ đi. P01 đo 0/266 lượt bịa tên, nhưng
    đó là **chất lượng**, không phải **rào**."""
    may.dat(_goi_tool("xoa_het_du_lieu", "{}"), _chu("toi khong lam duoc viec do"))
    _uid, email = _user()
    c, h = _phien(web.app, email)
    cv, _ = _gui(c, h)

    tra = str(may.than[1]["messages"][-1]["content"])
    assert "LOI[" in tra and "xoa_het_du_lieu" in tra
    tin = _su_that(c, h, cv)["messages"][-1]
    assert tin["status"] == "done", "ten la KHONG duoc giet luot"


def test_TRAN_VONG_cuong_che_o_may_chu(web, may, bat_co):
    """Model gọi tool mãi ⇒ dừng ở trần, `COMPLETED` kèm lý do, không `FAILED`."""
    from apps.chatltt.services import dieu_phoi as DP
    from platform_core.db import get_session
    from sqlalchemy import text
    may.dat(*[_goi_tool("noi_bo.tinh", '{"bieu_thuc": "%d+1"}' % i)
              for i in range(DP.TRAN_VONG_MODEL + 2)])
    _uid, email = _user()
    c, h = _phien(web.app, email)
    cv, _ = _gui(c, h)

    assert len(may.than) == DP.TRAN_VONG_MODEL, "khong duoc goi qua tran"
    gen = get_session()
    db = next(gen)
    try:
        r = db.execute(text("SELECT trang_thai, ly_do_ket FROM chatltt_run")).one()
        assert r == ("COMPLETED", DP.KET_TRAN_VONG)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    tin = _su_that(c, h, cv)["messages"][-1]
    ma = [k.get("code") for k in tin["blocks"] if k["type"] == "status"]
    assert DP.KET_TRAN_VONG in ma, "cham tran phai NOI RA cho nguoi dung"


def test_khong_tool_nao_duoc_moi_thi_ve_duong_V1(web, may, bat_co, monkeypatch):
    """⛔ `chieu()` rỗng ⇒ **không gửi khoá `tools`**, và không mở `chatltt_run`.
    Bật cờ mà chưa mời tool nào thì lượt ấy vẫn phải là một lượt V1."""
    from apps.chatltt.services import chieu_tool as C
    monkeypatch.setattr(C, "CHO_MODEL_GOI", ())
    may.dat(_chu("chao ban"))
    _uid, email = _user()
    c, h = _phien(web.app, email)
    _gui(c, h)
    assert "tools" not in may.than[0]
    assert _dem("chatltt_run") == 0
