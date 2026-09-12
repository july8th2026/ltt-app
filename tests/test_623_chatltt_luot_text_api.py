"""
test_623 — Phase 08 (backend): ChatLTT chỉ-text qua HTTP thật, model giả.

  1. Gửi lượt → 202 + id; lượt chạy (inline trong test) → sự thật ở CSDL: text, usage, tiền.
  2. SSE `stream`: snapshot đầu + `end` khi đã xong; sự kiện sống qua hàng đợi trong tiến trình.
  3. Dừng: `cancelled` ở CSDL + cờ; phần đã sinh giữ lại; tiền thu đúng phần đã sinh.
  4. Tạo lại = assistant anh em; sửa-gửi-lại = user anh em; chọn lá.
  5. IDOR: người khác 404 ở mọi cửa; thiếu CSRF ⇒ 403; nội dung rỗng ⇒ 400.
  6. `dang_chay`: fan-out nhiều người xem, `None` khi chờ (ping), kết thúc.
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


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "w.db").as_posix())
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
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-value-623",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    # Lượt chạy INLINE (không thread) để test tất định; luồng thật kiểm ở mục 6.
    from apps.chatltt.services import luot as LUOT

    def inline(execution_id, *, user_id):
        LUOT.chay(execution_id, user_id=user_id)
        return threading.current_thread()

    monkeypatch.setattr(LUOT, "khoi_chay_nen", inline)
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


def _user(credits=1000):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "c623-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12", is_verified=True)
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id, email
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dang_nhap(web, email):
    r = web.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    r = web.post("/login", data={"username": email, "password": "a-good-password-12",
                                 "csrf_token": m.group(1), "next": "/chatltt"},
                 follow_redirects=True)
    assert r.status_code == 200
    r = web.get("/chatltt")
    csrf = re.search(r'data-csrf="([^"]+)"', r.text).group(1)
    return {"X-CSRF-Token": csrf}


def _so_du(user_id):
    from platform_core import credit
    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        return int(credit.so_du(db, user_id))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _sse(g):
    return b"data: " + json.dumps(g).encode() + NL + NL


def _tool_thu(monkeypatch, khoi=None, ban=False):
    """`text.chat` giả: ToolSpec + executor giả (khuôn test_600) + `luong_vlm.mo` giả."""
    from platform_core import registry as reg
    from platform_core.llm import luong_vlm
    from tests.test_600_runtime_noi_bo_luong import EXECUTOR_GIA  # noqa: F401

    tool = reg.ToolSpec(name="text.chat", job_type="t623.j", description="d",
                        params_schema={"messages": {"type": "json[]"},
                                       "model": {"type": "enum", "values": [_ALIAS_THU],
                                                 "default": _ALIAS_THU}},
                        returns={"content": "text"},
                        admission_resource="thu_gpu623", admission_slots=1,
                        sync_executor="tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA",
                        api_exposed=True,
                        api_contract={"description": "chat thu", "scopes": ("jobs:create",),
                                      "models": {_ALIAS_THU: {"id": "noi-bo-623"}}})
    man = reg.AppManifest(slug="t623", display_name="t623", route_prefix="/t623",
                          job_types=("t623.j",), credit_cost=lambda p: 1,
                          surface="runtime", lifecycle="internal", tools=(tool,))
    goc = reg.discover
    loaded = reg.LoadedApp(manifest=man, router=None)
    monkeypatch.setattr(reg, "discover",
                        lambda apps_dir=None: [x for x in goc() if x.manifest.slug != "ltt_llm"]
                        + [loaded])
    da_goi = []

    class Gia:
        ma, content_type = 200, "text/event-stream"

        def __init__(self, ks):
            self.luong = iter(ks)

        def xong(self, tokens=0):
            pass

        def hong(self, exc):
            pass

    def mo(db, *, duong, than, timeout_s=0):
        da_goi.append(than)
        if ban:
            raise luong_vlm.KhongMoDuocLuong("may B dang ban", ban=True, thu_lai_sau_s=20)
        return Gia(list(khoi) if khoi is not None else [
            _sse({"choices": [{"delta": {"reasoning_content": "nghi"}}]}),
            _sse({"choices": [{"delta": {"content": "xin "}}]}),
            _sse({"choices": [{"delta": {"content": "chao"}, "finish_reason": "stop"}]}),
            # Cỡ vượt 1 credit: các phép kiểm tiền ở tệp này khẳng định
            # `0 < thu < giu`, và mệnh đề ấy phải đúng ở CẢ HAI chính sách
            # làm tròn chứ không nhờ sàn của C1.
            _sse({"choices": [],
                  "usage": {"prompt_tokens": 40_000, "completion_tokens": 2_000}}),
            b"data: [DONE]" + NL + NL])

    monkeypatch.setattr(luong_vlm, "mo", mo)
    return da_goi


def _tao(web, h, alias=_ALIAS_THU):
    r = web.post("/chatltt/api/hoi-thoai", json={"model_alias": alias}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── 1 + 2. Gửi → chạy → sự thật; SSE snapshot/end ────────────────────────────

def test_gui_luot_roi_su_that_va_stream(web, monkeypatch):
    da_goi = _tool_thu(monkeypatch)
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = _tao(web, h)
    r = web.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "hoi gi do"}, headers=h)
    assert r.status_code == 202, r.text
    kq = r.json()
    assert set(kq) == {"conversation_id", "user_message_id", "assistant_message_id", "execution_id"}
    # Ngữ cảnh gửi model = đường gốc→user; alias dịch sang id nội bộ do
    # **executor** của app quyết (không phải `api_contract`), và id đó không
    # bao giờ rời nền tảng.
    assert da_goi[0]["messages"] == [{"role": "user", "content": "hoi gi do"}]
    assert da_goi[0]["model"] == "noi-bo-model-1"

    st = web.get(f"/chatltt/api/hoi-thoai/{cv}").json()
    for cam in ("noi-bo-model-1", "noi-bo-623"):
        assert cam not in json.dumps(st)
    tin = {m["id"]: m for m in st["messages"]}
    a = tin[kq["assistant_message_id"]]
    assert a["status"] == "done" and a["parent_id"] == kq["user_message_id"]
    assert a["blocks"] == [{"type": "reasoning", "text": "nghi"}, {"type": "text", "text": "xin chao"}]
    assert a["execution"]["usage"]["token_ra"] == 2_000
    assert a["execution"]["credit"]["thu"] >= 1
    assert st["conversation"]["current_leaf_id"] == kq["assistant_message_id"]
    assert st["conversation"]["title"].startswith("hoi gi do")
    assert _so_du(uid) == 1000 - a["execution"]["credit"]["thu"]

    with web.stream("GET", f"/chatltt/api/luot/{kq['execution_id']}/stream") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        than = b"".join(r.iter_bytes()).decode()
    assert "event: snapshot" in than and "event: end" in than
    assert '"partial_text": "xin chao"' in than


def test_ban_truoc_byte_dau_thanh_failed_ban_khong_thu(web, monkeypatch):
    _tool_thu(monkeypatch, ban=True)
    uid, email = _user(500)
    h = _dang_nhap(web, email)
    cv = _tao(web, h)
    kq = web.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "hoi"}, headers=h).json()
    a = {m["id"]: m for m in web.get(f"/chatltt/api/hoi-thoai/{cv}").json()["messages"]}[
        kq["assistant_message_id"]]
    assert a["status"] == "failed" and a["execution"]["error_code"] == "ban"
    assert a["blocks"][-1]["type"] == "error"
    assert _so_du(uid) == 500


# ── 3. Dừng ──────────────────────────────────────────────────────────────────

def test_dung_giua_chung_giu_phan_da_sinh_va_thu_dung(web, monkeypatch):
    from apps.chatltt.services import luot as LUOT

    khoi = [_sse({"choices": [{"delta": {"content": "a"}}],
                  # 10.000 vào (500) + 1.250 ra (500) = ĐÚNG 1,000 credit ⇒
                  # `thu == 1` ở cả C1 lẫn C3, trong khi giữ chỗ là 2.
                  "usage": {"prompt_tokens": 10_000, "completion_tokens": 1_250}})]
    khoi += [_sse({"choices": [{"delta": {"content": "b"}}]})] * 400
    _tool_thu(monkeypatch, khoi=khoi)
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = _tao(web, h)

    # Giả lập nút Dừng bấm ở tiến trình khác: sau 250 ký tự, ghi cancelled vào CSDL.
    nen_ghi_that = LUOT.S.nen_ghi
    da_dung = {"x": False}

    def nen_ghi_va_dung(**kw):
        ket = nen_ghi_that(**kw)
        if ket and not da_dung["x"] and kw["ky_tu_moi"] >= 200:
            da_dung["x"] = True
            from apps.chatltt.services import dang_chay
            for k in list(dang_chay._SO):
                dang_chay.yeu_cau_dung(k)
        return ket

    monkeypatch.setattr(LUOT.S, "nen_ghi", nen_ghi_va_dung)
    kq = web.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "dai"}, headers=h).json()
    a = {m["id"]: m for m in web.get(f"/chatltt/api/hoi-thoai/{cv}").json()["messages"]}[
        kq["assistant_message_id"]]
    assert a["status"] == "cancelled"
    assert 200 <= len(a["execution"]["partial_text"]) < 401
    assert a["blocks"][-1] == {"type": "status", "code": "cancelled"}
    thu = a["execution"]["credit"]["thu"]
    assert 0 < thu < a["execution"]["credit"]["giu"]
    assert _so_du(uid) == 1000 - thu
    # Dừng lại lần nữa qua API: idempotent.
    r = web.post(f"/chatltt/api/luot/{kq['execution_id']}/dung", json={}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"


# ── 4. Tạo lại · sửa-gửi-lại · chọn lá ───────────────────────────────────────

def test_tao_lai_va_sua_gui_lai_la_anh_em(web, monkeypatch):
    _tool_thu(monkeypatch)
    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = _tao(web, h)
    k1 = web.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "hoi 1"}, headers=h).json()
    k2 = web.post(f"/chatltt/api/hoi-thoai/{cv}/luot",
                  json={"tao_lai_cua": k1["assistant_message_id"]}, headers=h).json()
    assert k2["user_message_id"] == k1["user_message_id"]
    st = web.get(f"/chatltt/api/hoi-thoai/{cv}").json()
    con = [m for m in st["messages"] if m["parent_id"] == k1["user_message_id"]]
    assert [m["id"] for m in con] == [k1["assistant_message_id"], k2["assistant_message_id"]]
    assert st["conversation"]["current_leaf_id"] == k2["assistant_message_id"]
    # Sửa "hoi 1" → gửi lại: user anh em mới ở gốc.
    k3 = web.post(f"/chatltt/api/hoi-thoai/{cv}/luot",
                  json={"text": "hoi 1 sua", "parent_id": None}, headers=h).json()
    st = web.get(f"/chatltt/api/hoi-thoai/{cv}").json()
    goc = [m["id"] for m in st["messages"] if m["parent_id"] is None]
    assert goc == [k1["user_message_id"], k3["user_message_id"]]
    # Chọn lại lá cũ.
    r = web.post(f"/chatltt/api/hoi-thoai/{cv}/chon-la",
                 json={"message_id": k1["assistant_message_id"]}, headers=h)
    assert r.status_code == 200 and r.json()["current_leaf_id"] == k1["assistant_message_id"]
    # Liệt kê + tìm.
    assert [x["id"] for x in web.get("/chatltt/api/hoi-thoai?tim=hoi 1").json()["hoi_thoai"]] == [cv]


# ── 5. IDOR · CSRF · tham số ─────────────────────────────────────────────────

def test_idor_csrf_va_tham_so(web, monkeypatch):
    _tool_thu(monkeypatch)
    uid_a, email_a = _user(100)
    h = _dang_nhap(web, email_a)
    cv = _tao(web, h)
    kq = web.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "x"}, headers=h).json()
    assert web.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": ""}, headers=h).status_code == 400
    assert web.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "y"}).status_code == 403
    assert web.post("/chatltt/api/hoi-thoai", json={}).status_code == 403
    # Người B
    uid_b, email_b = _user(100)
    from fastapi.testclient import TestClient
    hb = _dang_nhap(web, email_b)
    for duong, method in ((f"/chatltt/api/hoi-thoai/{cv}", "get"),
                          (f"/chatltt/api/hoi-thoai/{cv}/luot", "post"),
                          (f"/chatltt/api/hoi-thoai/{cv}/xoa", "post"),
                          (f"/chatltt/api/luot/{kq['execution_id']}/dung", "post")):
        r = (web.get(duong, headers=hb) if method == "get"
             else web.post(duong, json={"text": "z"}, headers=hb))
        assert r.status_code == 404, (duong, r.status_code)
    with web.stream("GET", f"/chatltt/api/luot/{kq['execution_id']}/stream", headers=hb) as r:
        than = b"".join(r.iter_bytes()).decode()
    assert "khong_tim_thay" in than and "partial_text" not in than
    assert web.get("/chatltt/api/hoi-thoai", headers=hb).json()["hoi_thoai"] == []


# ── 6. dang_chay ─────────────────────────────────────────────────────────────

def test_dang_chay_fan_out_ping_va_ket_thuc():
    from apps.chatltt.services import dang_chay as D
    so = D.bat_dau("ex_623", "u")
    q1, q2 = so.dang_ky(), so.dang_ky()
    so.phat({"type": "response.delta", "text": "a"})
    assert D.tim("ex_623") is so and D.yeu_cau_dung("ex_623") is True and so.dung.is_set()

    # Fan-out: MỖI người xem nhận bản của mình, không ai lấy mất của ai.
    it1 = D.theo_doi(q1, cho_moi_lan_s=0.05)
    it2 = D.theo_doi(q2, cho_moi_lan_s=0.05)
    assert next(it1) == {"type": "response.delta", "text": "a"}
    assert next(it2) == {"type": "response.delta", "text": "a"}
    # Rỗng ⇒ `None` (route dịch thành `: ping`), KHÔNG chặn vô hạn.
    assert next(it2) is None
    # Kết thúc ⇒ generator cạn (nếu không, `list()` dưới đây treo mãi).
    D.ket_thuc("ex_623")
    assert list(it2) == []
    assert list(it1) == []
    assert D.tim("ex_623") is None and so.dang_ky() is None
    assert D.yeu_cau_dung("khong_co") is False
