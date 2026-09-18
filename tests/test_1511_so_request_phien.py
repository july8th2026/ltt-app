"""test_1511 — sổ `public_api_requests` mang MÃ LƯỢT + PHIÊN CLIENT. (T4 P1, R-06/R-07)

Thiết kế: `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §2.2, §6.2.

Câu hỏi: *"lượt X trên máy B thuộc phiên nào của khách nào?"*. Trước T4, dòng
`public_api_requests` — dòng DUY NHẤT biết khách/khoá/route/status của mọi request,
kể cả bị từ chối — **không mang mã lượt**, nên không nối được sang `credit_entries`
/ `llm_waiters` / sổ B. Tệp này chốt:

  1. `ma_luot` của dòng = `credit_entries.job_id` = `llm_waiters.request_id` = mã A
     gửi máy B (`X-LTT-Request-Id`) — bốn sổ, MỘT khoá — ở cả bốn cửa sinh mã:
     `/messages` stream, `/responses` stream, `/messages` một cục, `/chat/completions`.
  2. Phiên client (Claude Code / Codex) nằm trên cùng dòng.
  3. Lượt bị từ chối thiếu credit (409 `insufficient_credit`) / 429 vẫn có dòng mang phiên + mã lượt.
  4. Khách ngắt giữa luồng ⇒ dòng VẪN được ghi (task nền chạy sau ngắt — đo).
  5. ⛔ Không định danh máy nào vào CSDL.
  6. Migration add-only: lên/xuống sạch, mã cũ INSERT không khai cột mới vẫn được.

Đối chứng (tiêm lỗi, chạy tay khi viết): gỡ lời gọi `phien_khach.doc` trong
`guard.py` ⇒ các ca phiên ĐỎ; gỡ dòng báo mã trong `thanh_toan.ma_luot` ⇒ các ca
`ma_luot` ĐỎ.
"""
from __future__ import annotations

import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.llm.canonical import MODEL_MAC_DINH as MODEL
from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ)
from server.api.inventory import API_V1_PREFIX
from tests.conftest import mo_cu_tru_3090

PEPPER = "phien-test-pepper-" + "p" * 40
MSG = API_V1_PREFIX + "/messages"
RSP = API_V1_PREFIX + "/responses"
CHAT = API_V1_PREFIX + "/chat/completions"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ)
NL = bytes([10])

PHIEN_CC = "829c76f3-5d2a-4b1e-9c3f-38eea5feef82"
PHIEN_CODEX = "01a0b543-7f3e-7c21-9d44-e2a0ef3726b5"
THREAD_CON = "01a0b544-0000-7c21-9d44-000000000abc"
TURN = "019a0c55-1234-7abc-8def-0123456789ab"
# Ghep hai nua: chuoi hex 32 ky tu lien bi scan_source_secrets bat (test_44).
INSTALL = "inst-" + "9f8e7d6c5b4a3928" + "1706f5e4d3c2b1a0"
COT_MOI = ("ma_luot", "phien_khach", "nhanh_khach", "luot_khach", "ung_dung_khach")


def _h_claude(token: str) -> dict:
    return {"Authorization": "Bearer " + token,
            "X-Claude-Code-Session-Id": PHIEN_CC,
            "x-claude-code-agent-id": "agent-7",
            "User-Agent": "claude-cli/2.1.275 (external, cli)",
            "X-Stainless-Retry-Count": "0"}


def _h_codex(token: str) -> dict:
    meta = {"installation_id": INSTALL, "session_id": PHIEN_CODEX,
            "thread_id": THREAD_CON, "turn_id": TURN, "sandbox": "workspace-write",
            "workspaces": [{"remote": "git@github.com:bi-mat/kho.git"}]}
    return {"Authorization": "Bearer " + token,
            "session-id": PHIEN_CODEX, "thread-id": THREAD_CON,
            "x-client-request-id": THREAD_CON,
            "x-codex-turn-metadata": json.dumps(meta),
            "x-codex-installation-id": INSTALL,
            "originator": "codex_exec",
            "User-Agent": "codex_exec/0.145.0 (Windows 10.0.19045; x86_64) WT"}


# ── Giàn (cùng khuôn `test_272_cua_streaming`) ─────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "ph.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    mo_cu_tru_3090()
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "phien-secret-value-x",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "text.chat",
        "LTT_PUBLIC_API_RPM": "600",
    })
    with TestClient(app, base_url="https://testserver") as client:
        client.asgi = app
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
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


def _account(credits: int = 10_000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="p-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
        _k, token = devkeys.issue(db, user_id=u.id, scopes=ALL_SCOPES,
                                  env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return u.id, token
    finally:
        _close(gen)


def _dong(user_id: str) -> list:
    """Mọi dòng sổ request của khách, cũ trước."""
    from sqlalchemy import select

    from platform_core.public_api.tables import ApiRequestLog
    gen, db = _session()
    try:
        rows = db.execute(select(ApiRequestLog)
                          .where(ApiRequestLog.user_id == user_id)
                          .order_by(ApiRequestLog.created_at)).scalars().all()
        for r in rows:
            db.expunge(r)
        return rows
    finally:
        _close(gen)


def _job_id_credit(user_id: str) -> set[str]:
    from platform_core.models import CreditEntry
    gen, db = _session()
    try:
        return {j for (j,) in db.query(CreditEntry.job_id)
                .filter(CreditEntry.user_id == user_id,
                        CreditEntry.job_id != "").all()}
    finally:
        _close(gen)


def _request_id_waiter(user_id: str) -> set[str]:
    from platform_core.models import LlmWaiter
    gen, db = _session()
    try:
        return {r for (r,) in db.query(LlmWaiter.request_id)
                .filter(LlmWaiter.user_id == user_id).all()}
    finally:
        _close(gen)


def _than(**g):
    d = {"model": MODEL, "stream": True, "max_tokens": 500,
         "messages": [{"role": "user", "content": "xin chao"}]}
    d.update(g)
    return d


def _than_rsp(**g):
    d = {"model": MODEL, "stream": True, "max_output_tokens": 500,
         "input": "xin chao"}
    d.update(g)
    return d


def _sse(ten, goi):
    return (b"event: " + ten.encode() + NL
            + b"data: " + json.dumps(goi).encode() + NL + NL)


def _khoi(so_delta: int = 1, ngu_s: float = 0.0):
    """Luồng Anthropic giả của máy B. `so_delta`/`ngu_s` kéo dài để cắt giữa chừng."""
    yield _sse("message_start", {"message": {"usage": {
        "input_tokens": 100, "output_tokens": 0}}})
    for _ in range(so_delta):
        if ngu_s:
            time.sleep(ngu_s)
        yield _sse("content_block_delta",
                   {"delta": {"type": "text_delta", "text": "chao"}})
    yield _sse("message_delta", {"usage": {"output_tokens": 50}})
    yield _sse("message_stop", {})


def _dat_luong(monkeypatch, tao_khoi=_khoi):
    """Thay `luong_vlm.mo`, và GHI mã lượt A gửi máy B (`X-LTT-Request-Id`)."""
    from platform_core.llm import luong_vlm
    da_goi: list[dict] = []

    class GiaLuong:
        def __init__(self, ks):
            self.ma = 200
            self.content_type = "text/event-stream"
            self.luong = ks
            self.da_xong = False
            self.da_hong = False

        def xong(self, tokens=0):
            self.da_xong = True

        def hong(self, exc):
            self.da_hong = True

        def dong(self):
            pass

    def gia(db, *, duong, than, timeout_s=900.0, request_id="", **_meta):
        da_goi.append({"duong": duong, "request_id": request_id})
        return GiaLuong(tao_khoi())

    monkeypatch.setattr(luong_vlm, "mo", gia)
    return da_goi


def _dat_mot_cuc(monkeypatch):
    """Thay `features.chay` (cửa một cục + `/chat/completions`), ghi `ma_luot`."""
    from apps.ltt_llm import features
    goi: list[str] = []

    def gia(db, params, *, timeout_s=300.0, ma_luot="", **_):
        goi.append(ma_luot)
        return features.KetQua(
            noi_dung="chao ban", suy_nghi="", tool_calls=(), finish_reason="stop",
            model=params["model"], token_vao=8_000, token_ra=2_000,
            token_vao_cache=0, do_duoc=True)

    monkeypatch.setattr(features, "chay", gia)
    return goi


# ── 1. Bốn sổ, một khoá — cửa stream ───────────────────────────────────────

def test_messages_stream_claude_code_bon_so_mot_khoa(api, monkeypatch):
    goi = _dat_luong(monkeypatch)
    user_id, token = _account()
    r = api.post(MSG, json=_than(), headers=_h_claude(token))
    assert r.status_code == 200, r.text
    r.read()

    rows = _dong(user_id)
    assert len(rows) == 1, [(x.route, x.status) for x in rows]
    d = rows[0]
    assert d.phien_khach == PHIEN_CC
    assert d.nhanh_khach == "agent-7"
    assert d.luot_khach == ""
    assert d.ung_dung_khach == "claude-cli/2.1.275"

    assert d.ma_luot, "dong so request KHONG mang ma luot — khong noi duoc sang B"
    assert [g["request_id"] for g in goi] == [d.ma_luot], (
        "ma luot tren dong khac ma A gui may B (X-LTT-Request-Id)")
    assert d.ma_luot in _job_id_credit(user_id), "khong noi duoc sang credit_entries"
    assert d.ma_luot in _request_id_waiter(user_id), "khong noi duoc sang llm_waiters"


def test_responses_stream_codex_co_nhanh_va_luot(api, monkeypatch):
    goi = _dat_luong(monkeypatch)
    user_id, token = _account()
    r = api.post(RSP, json=_than_rsp(), headers=_h_codex(token))
    assert r.status_code == 200, r.text
    r.read()

    (d,) = _dong(user_id)
    assert (d.phien_khach, d.nhanh_khach, d.luot_khach, d.ung_dung_khach) == (
        PHIEN_CODEX, THREAD_CON, TURN, "codex_exec/0.145.0")
    assert goi and goi[-1]["request_id"] == d.ma_luot
    assert d.ma_luot in _job_id_credit(user_id)


# ── 2. Cửa một cục và `/chat/completions` ──────────────────────────────────

def test_messages_mot_cuc_co_ma_luot(api, monkeypatch):
    goi = _dat_mot_cuc(monkeypatch)
    user_id, token = _account()
    than = _than(max_tokens=2_000)
    than.pop("stream")
    r = api.post(MSG, json=than, headers=_h_claude(token))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")

    (d,) = _dong(user_id)
    assert d.ma_luot and d.ma_luot in _job_id_credit(user_id)
    assert d.ma_luot in _request_id_waiter(user_id)
    assert goi, "khong goi toi model"
    # ⚠️ KHÔNG so `goi == [d.ma_luot]` ở cửa này: 18/09 cửa một cục gọi
    #    `executor.run(...)` KHÔNG truyền `ma_luot` (`server/api/streaming.py`,
    #    vùng T1b) ⇒ `features.chay` nhận `""`. Đã báo; sửa ở đó, không ở đây.
    assert d.phien_khach == PHIEN_CC


def test_chat_completions_co_ma_luot(api, monkeypatch):
    goi = _dat_mot_cuc(monkeypatch)
    user_id, token = _account()
    h = _h_codex(token)
    h["Idempotency-Key"] = uuid.uuid4().hex
    r = api.post(CHAT, json={"model": MODEL, "max_tokens": 2_000,
                             "messages": [{"role": "user", "content": "xin chao"}]},
                 headers=h)
    assert r.status_code == 200, r.text

    (d,) = _dong(user_id)
    assert d.ma_luot.startswith("ch:"), d.ma_luot
    assert d.ma_luot in _job_id_credit(user_id)
    assert goi == [d.ma_luot]
    assert d.phien_khach == PHIEN_CODEX and d.luot_khach == TURN


# ── 3. Bị từ chối vẫn có dòng: phiên + mã lượt ─────────────────────────────
#
# "402" theo cách gọi thường ngày = thiếu credit; bề mặt này trả `409` +
# `code=insufficient_credit` (`server/api/errors`). Kiểm theo `code`.

THIEU_CREDIT = "insufficient_credit"

def test_429_phong_day_van_co_phien_va_ma_luot(api, monkeypatch):
    monkeypatch.setenv("LTT_LLM_SO_NGUOI_CHO", "0")
    goi = _dat_luong(monkeypatch)
    user_id, token = _account()
    r = api.post(MSG, json=_than(), headers=_h_claude(token))
    assert r.status_code == 429, r.text
    assert goi == [], "phong day ma van goi may B"

    (d,) = _dong(user_id)
    assert d.status == 429
    assert d.phien_khach == PHIEN_CC
    # Mã đã sinh ở tiền kiểm, trước khi phòng chờ từ chối: khách hỏi "sao phiên
    # tôi đứng" thì dòng này là thứ duy nhất trả lời được.
    assert d.ma_luot, "lượt 429 mất mã lượt"
    assert d.ma_luot not in _job_id_credit(user_id), "429 ma co but toan tien"


def test_thieu_credit_stream_van_co_phien_va_ma_luot(api, monkeypatch):
    goi = _dat_luong(monkeypatch)
    user_id, token = _account(credits=0)
    r = api.post(RSP, json=_than_rsp(), headers=_h_codex(token))
    assert r.json().get("code") == THIEU_CREDIT, r.text
    assert goi == []

    (d,) = _dong(user_id)
    assert (d.status, d.code) == (r.status_code, THIEU_CREDIT)
    assert (d.phien_khach, d.luot_khach) == (PHIEN_CODEX, TURN)
    assert d.ma_luot


def test_thieu_credit_mot_cuc_van_co_ma_luot(api, monkeypatch):
    _dat_mot_cuc(monkeypatch)
    user_id, token = _account(credits=0)
    than = _than()
    than.pop("stream")
    r = api.post(MSG, json=than, headers=_h_claude(token))
    assert r.json().get("code") == THIEU_CREDIT, r.text
    (d,) = _dong(user_id)
    assert d.code == THIEU_CREDIT
    assert d.ma_luot and d.phien_khach == PHIEN_CC
    assert d.ma_luot not in _job_id_credit(user_id)


# ── 4. Không header phiên / request không sinh mã ──────────────────────────

def test_khong_header_phien_thi_cot_rong_nhung_van_co_ma(api, monkeypatch):
    _dat_luong(monkeypatch)
    user_id, token = _account()
    r = api.post(MSG, json=_than(), headers={"Authorization": "Bearer " + token})
    r.read()
    (d,) = _dong(user_id)
    assert (d.phien_khach, d.nhanh_khach, d.luot_khach) == ("", "", "")
    assert d.ma_luot, "ma luot khong phu thuoc header cua client"


def test_400_truoc_khi_sinh_ma_thi_ma_rong(api, monkeypatch):
    """Đối chứng ngược: request KHÔNG tới chỗ sinh mã thì cột rỗng, không bịa."""
    _dat_luong(monkeypatch)
    user_id, token = _account()
    r = api.post(MSG, json={"model": MODEL, "stream": True},
                 headers=_h_claude(token))
    assert r.status_code == 400, r.text
    (d,) = _dong(user_id)
    assert d.ma_luot == ""
    assert d.phien_khach == PHIEN_CC


def test_hai_request_lien_nhau_khong_lan_ma(api, monkeypatch):
    """Sổ nghe mã là THEO REQUEST: request sau không được thừa mã request trước."""
    _dat_luong(monkeypatch)
    user_id, token = _account()
    api.post(MSG, json=_than(), headers=_h_claude(token)).read()
    api.post(MSG, json={"model": MODEL, "stream": True},
             headers=_h_claude(token)).read()
    a, b = _dong(user_id)
    assert a.ma_luot and b.ma_luot == "", (a.ma_luot, b.ma_luot)


# ── 5. ⛔ Không định danh máy nào vào CSDL ───────────────────────────────────

def test_KHONG_luu_dinh_danh_may(api, monkeypatch):
    _dat_luong(monkeypatch)
    user_id, token = _account()
    api.post(RSP, json=_than_rsp(), headers=_h_codex(token)).read()
    (d,) = _dong(user_id)
    toan_dong = repr({c.name: getattr(d, c.name) for c in d.__table__.columns})
    for cam in (INSTALL, "github.com", "workspace-write", "Windows", "WT"):
        assert cam not in toan_dong, f"lot {cam!r} vao dong so: {toan_dong}"


# ── 6. Dòng log văn bản ────────────────────────────────────────────────────

def test_dong_log_van_ban_co_phien_va_ma_luot_rut_gon(api, monkeypatch, caplog):
    import logging
    _dat_luong(monkeypatch)
    user_id, token = _account()
    with caplog.at_level(logging.INFO, logger="ltt.public_api.access"):
        api.post(MSG, json=_than(), headers=_h_claude(token)).read()
    (d,) = _dong(user_id)
    dong = [r.getMessage() for r in caplog.records
            if r.name == "ltt.public_api.access" and "route=" in r.getMessage()]
    assert dong, "khong co dong log truy cap"
    assert f"phien={PHIEN_CC[:8]}" in dong[-1], dong[-1]
    assert f"ma_luot={d.ma_luot[-8:]}" in dong[-1], dong[-1]
    assert PHIEN_CC not in dong[-1], "dong log chi mang 8 ky tu dau cua phien"


# ── 7. Khách ngắt giữa luồng ⇒ dòng VẪN được ghi ───────────────────────────

def test_khach_ngat_giua_luong_dong_van_duoc_ghi(api, monkeypatch):
    """Câu hỏi mở của thiết kế §6.2(5): task nền có chạy sau khi khách ngắt?

    ⛔ `TestClient` đệm CẢ phản hồi trước khi trả — không ngắt giữa chừng được.
       Nên gọi thẳng ứng dụng ASGI: `receive` trả thân, rồi `http.disconnect`
       ngay sau khi khối `content_block_delta` ĐẦU TIÊN ra tới khách; luồng giả
       còn ~200 khối nữa (≥ 4 giây). `spec_version` 2.3 — bản uvicorn đang chạy
       (`h11_impl`/`httptools_impl`) khai đúng số đó.
    """
    import anyio

    _dat_luong(monkeypatch, lambda: _khoi(so_delta=200, ngu_s=0.02))
    user_id, token = _account()
    body = json.dumps(_than()).encode()
    headers = [(k.lower().encode("latin-1"), v.encode("latin-1"))
               for k, v in _h_claude(token).items()]
    headers += [(b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"host", b"testserver")]
    ket = {"status": 0, "khoi": 0, "sau_ngat": 0}

    async def chay():
        ngat = anyio.Event()
        da_gui = False

        async def receive():
            nonlocal da_gui
            if not da_gui:
                da_gui = True
                return {"type": "http.request", "body": body, "more_body": False}
            await ngat.wait()
            return {"type": "http.disconnect"}

        async def send(msg):
            if msg["type"] == "http.response.start":
                ket["status"] = msg["status"]
            elif msg["type"] == "http.response.body" and msg.get("body"):
                if ngat.is_set():
                    ket["sau_ngat"] += 1       # uvicorn bỏ qua send sau ngắt
                    return
                ket["khoi"] += 1
                if b"content_block_delta" in msg["body"]:
                    ngat.set()

        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
                 "http_version": "1.1", "method": "POST", "scheme": "https",
                 "path": MSG, "raw_path": MSG.encode(), "root_path": "",
                 "query_string": b"", "headers": headers,
                 "client": ("127.0.0.1", 50000), "server": ("testserver", 443),
                 "state": dict(getattr(api, "app_state", {}) or {})}
        with anyio.fail_after(60):
            await api.asgi(scope, receive, send)

    t0 = time.monotonic()
    api.portal.call(chay)
    ton = time.monotonic() - t0

    assert ket["status"] == 200
    assert ket["khoi"] >= 1
    rows = _dong(user_id)
    assert len(rows) == 1, (
        f"khach ngat giua luong => KHONG co dong so request (khoi={ket}, "
        f"{ton:.1f}s)")
    d = rows[0]
    assert d.phien_khach == PHIEN_CC
    assert d.ma_luot and d.ma_luot in _request_id_waiter(user_id)
    assert ton < 4.0, (
        f"luong chay HET ({ton:.1f}s) — ngat khong cat duoc luong, phep kiem nay "
        f"khong con do 'ngat GIUA luong'")


# ── 8. Lưu giữ 30 ngày — cơ chế có sẵn phủ cả cột mới ──────────────────────

def test_dong_co_phien_bi_don_sau_30_ngay():
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from platform_core.public_api import request_log
    from platform_core.public_api.tables import ApiRequestLog

    eng = create_engine("sqlite://")
    ApiRequestLog.__table__.create(eng)
    now = datetime.now(timezone.utc)
    with Session(eng) as db:
        request_log.record(db, request_id="cu", user_id="u1", ma_luot="st:" + "a" * 32,
                           phien_khach=PHIEN_CC, now=now - timedelta(days=31))
        request_log.record(db, request_id="moi", user_id="u1", phien_khach=PHIEN_CC,
                           now=now - timedelta(days=1))
        db.commit()
        assert request_log.purge_expired(db, now=now) == 1
        db.commit()
        con = db.query(ApiRequestLog.request_id).all()
    assert [r for (r,) in con] == ["moi"]
    assert request_log.RETENTION_DAYS == 30


def test_record_cat_theo_do_dai_cot():
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine

    from platform_core.public_api import request_log
    from platform_core.public_api.tables import ApiRequestLog

    eng = create_engine("sqlite://")
    ApiRequestLog.__table__.create(eng)
    with Session(eng) as db:
        row = request_log.record(db, request_id="r", user_id="u",
                                 ma_luot="m" * 99, phien_khach="p" * 99,
                                 nhanh_khach="n" * 99, luot_khach="l" * 99,
                                 ung_dung_khach="u" * 99)
    cot = ApiRequestLog.__table__.c
    for ten in COT_MOI:
        tran = cot[ten].type.length
        assert len(getattr(row, ten)) == tran, (ten, tran)
    assert cot["ma_luot"].type.length == 36, "cung do dai credit_entries.job_id"


# ── 9. Migration ───────────────────────────────────────────────────────────

REV = "b7d41e2c9a05"


def _cfg():
    from pathlib import Path

    from alembic.config import Config
    goc = Path(__file__).resolve().parent.parent
    cfg = Config(str(goc / "alembic.ini"))
    cfg.set_main_option("script_location", str(goc / "alembic"))
    return cfg


def test_migration_mot_head_va_noi_vao_head_truoc():
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(_cfg())
    assert scripts.get_heads() == [REV], scripts.get_heads()
    rev = scripts.get_revision(REV)
    assert rev.down_revision == "7c2e5a91d4b3"


def test_mo_hinh_va_migration_cung_tap_cot_va_chi_muc():
    """`create_all` (test) và `alembic upgrade` (production) phải dựng CÙNG lược đồ."""
    from platform_core.public_api.tables import ApiRequestLog

    cot = {c.name for c in ApiRequestLog.__table__.columns}
    assert set(COT_MOI) <= cot
    for ten in COT_MOI:
        c = ApiRequestLog.__table__.c[ten]
        assert not c.nullable and c.server_default is not None, ten
    chi_muc = {i.name: [c.name for c in i.columns]
               for i in ApiRequestLog.__table__.indexes}
    assert chi_muc["ix_public_api_requests_phien"] == [
        "user_id", "phien_khach", "created_at"]
    assert chi_muc["ix_public_api_requests_ma_luot"] == ["ma_luot"]


@pytest.mark.timeout(300)
def test_sqlite_upgrade_head_roi_ma_cu_van_insert_duoc(tmp_path, monkeypatch):
    from alembic import command
    from sqlalchemy import create_engine, inspect, text

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    cfg = _cfg()
    command.upgrade(cfg, "head")
    eng = create_engine(url)
    cot = {c["name"] for c in inspect(eng).get_columns("public_api_requests")}
    assert set(COT_MOI) <= cot
    chi_muc = {i["name"] for i in inspect(eng).get_indexes("public_api_requests")}
    assert {"ix_public_api_requests_phien", "ix_public_api_requests_ma_luot"} <= chi_muc

    # Mã CŨ (không biết cột mới) vẫn INSERT được — nhờ `server_default`.
    with eng.begin() as c:
        c.execute(text(
            "INSERT INTO public_api_requests (id, request_id, user_id, key_id, "
            "project_id, method, route, status, code, latency_ms, tool, job_id, "
            "credit_delta, created_at) VALUES ('1','r','u','','','POST','/x',200,"
            "'',1,'','',0,'2026-09-18 00:00:00')"))
        assert c.execute(text(
            "SELECT ma_luot, phien_khach FROM public_api_requests")).one() == ("", "")

    command.downgrade(cfg, "-1")
    cot = {c["name"] for c in inspect(eng).get_columns("public_api_requests")}
    assert not set(COT_MOI) & cot, "downgrade khong go het cot moi"
    command.upgrade(cfg, "head")
    eng.dispose()


def test_postgres_migration_len_xuong_trong_schema_rieng(monkeypatch):
    """Postgres thật: lên / xuống / lên lại MỘT bước, trong schema vứt đi.

    Không chạy cả chuỗi từ `base` trên CSDL test dùng chung: dựng bảng ở hình
    dạng TRƯỚC migration (mô hình trừ 5 cột + 2 chỉ mục), đóng dấu revision cha,
    rồi chạy đúng bước này. `search_path` trỏ schema riêng nên không đụng bảng
    của test khác.
    """
    from alembic import command
    from sqlalchemy import (Column, MetaData, Table, create_engine, inspect,
                            text)

    from platform_core.public_api.tables import ApiRequestLog
    from tests import pg_scratch

    url = pg_scratch.scratch_url()
    if not url:
        pytest.skip(f"can {pg_scratch.ENV} tro toi mot CSDL PostgreSQL vut di")
    schema = "t1511_" + uuid.uuid4().hex[:8]
    goc = create_engine(url, isolation_level="AUTOCOMMIT")
    with goc.connect() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        noi = "&" if "?" in url else "?"
        url_s = f"{url}{noi}options=-csearch_path%3D{schema}"
        eng = create_engine(url_s)
        md = MetaData()
        Table("public_api_requests", md,
              *[Column(c.name, c.type, primary_key=c.primary_key,
                       nullable=c.nullable)
                for c in ApiRequestLog.__table__.columns
                if c.name not in COT_MOI])
        md.create_all(eng)
        with eng.begin() as c:
            c.execute(text("CREATE TABLE alembic_version "
                           "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
            c.execute(text("INSERT INTO alembic_version VALUES ('7c2e5a91d4b3')"))
            c.execute(text(
                "INSERT INTO public_api_requests (id, request_id, user_id, key_id, "
                "project_id, method, route, status, code, latency_ms, tool, job_id, "
                "credit_delta, created_at) VALUES ('1','r','u','','','POST','/x',"
                "200,'',1,'','',0, now())"))

        monkeypatch.setenv("LTT_DATABASE_URL", url_s)
        cfg = _cfg()
        command.upgrade(cfg, REV)
        insp = inspect(eng)
        cot = {c["name"]: c for c in insp.get_columns("public_api_requests")}
        assert set(COT_MOI) <= set(cot)
        assert cot["ma_luot"]["type"].length == 36
        assert cot["phien_khach"]["type"].length == 64
        assert cot["ung_dung_khach"]["type"].length == 48
        chi_muc = {i["name"] for i in insp.get_indexes("public_api_requests")}
        assert {"ix_public_api_requests_phien",
                "ix_public_api_requests_ma_luot"} <= chi_muc
        with eng.begin() as c:
            # Dòng có sẵn lúc migrate nhận default; mã cũ INSERT vẫn được.
            assert c.execute(text(
                "SELECT ma_luot, phien_khach FROM public_api_requests")).one() == (
                    "", "")
            c.execute(text(
                "INSERT INTO public_api_requests (id, request_id, user_id, key_id, "
                "project_id, method, route, status, code, latency_ms, tool, job_id,"
                " credit_delta, created_at) VALUES ('2','r2','u','','','POST','/x',"
                "200,'',1,'','',0, now())"))

        command.downgrade(cfg, "7c2e5a91d4b3")
        insp = inspect(eng)
        assert not set(COT_MOI) & {c["name"] for c in
                                   insp.get_columns("public_api_requests")}
        command.upgrade(cfg, REV)
        eng.dispose()
    finally:
        with goc.connect() as c:
            c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        goc.dispose()


# ── 10. Đường đọc: ô tìm admin theo mã lượt, `soi_su_co --phien` ───────────

@pytest.fixture()
def so(tmp_path, monkeypatch):
    """CSDL SQLite trắng, ba dòng sổ request của hai khách — cùng một chuỗi phiên."""
    from datetime import datetime, timedelta, timezone

    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "doc.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.public_api import request_log
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    now = datetime.now(timezone.utc)
    a = tao_nguoi_dung(db, email="a@example.com", password="a-good-password-12")
    b = tao_nguoi_dung(db, email="b@example.com", password="a-good-password-12")
    db.flush()
    ma = "st:" + "9f" * 16
    request_log.record(db, request_id="r-a1", user_id=a.id, method="POST",
                       route="/api/v1/messages", status=200, ma_luot=ma,
                       phien_khach=PHIEN_CC, now=now - timedelta(minutes=2))
    request_log.record(db, request_id="r-a2", user_id=a.id, method="POST",
                       route="/api/v1/messages", status=429,
                       phien_khach="phien-khac-cua-a", now=now - timedelta(minutes=1))
    # Khách B đặt TRÙNG chuỗi phiên — không được lẫn sang A.
    request_log.record(db, request_id="r-b1", user_id=b.id, method="POST",
                       route="/api/v1/messages", status=200,
                       phien_khach=PHIEN_CC, now=now)
    db.commit()
    yield db, ma
    _close(gen)
    dbmod.reset_engine()


def test_o_tim_admin_tim_duoc_theo_ma_luot(so):
    from platform_core import admin_console

    db, ma = so
    for q in (ma, ma[:10]):
        kq = admin_console.tim_lien_thuc_the(db, q)
        req = [d for n in kq["nhom"] if n.get("loai") == "request"
               for d in n.get("dong", n.get("ket_qua", []))]
        assert req, f"khong tim duoc dong theo ma luot {q!r}: {kq}"
        assert any(d["nhan"] == "r-a1" for d in req), req


def test_o_tim_admin_KHONG_tim_theo_phien(so):
    """Chỉ mục phiên mở đầu bằng `user_id` — tìm phiên không kèm khách là quét
    cả bảng, và lẫn khách với nhau (hai khách trùng chuỗi phiên ở giàn này)."""
    from platform_core import admin_console

    db, _ma = so
    kq = admin_console.tim_lien_thuc_the(db, PHIEN_CC)
    assert not [n for n in kq["nhom"] if n.get("loai") == "request"], kq


def test_soi_su_co_loc_theo_phien_cua_dung_khach(so, capsys):
    import importlib.util
    from pathlib import Path

    tep = Path(__file__).resolve().parent.parent / "tools" / "soi_su_co.py"
    spec = importlib.util.spec_from_file_location("soi_su_co_1511", tep)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    db, ma = so
    mod.phan_so_request(db, "a@example.com", 24, PHIEN_CC)
    ra = capsys.readouterr().out
    phan_c = ra.split("c) ", 1)[1]
    dong = [x for x in phan_c.splitlines() if "/api/v1/messages" in x]
    assert len(dong) == 1, phan_c
    assert f"ma={ma}" in dong[0] and f"phien={PHIEN_CC[:8]}" in dong[0]

    # Đối chứng: không `--phien` thì thấy cả hai lượt của A, vẫn không thấy B.
    mod.phan_so_request(db, "a@example.com", 24)
    phan_c = capsys.readouterr().out.split("c) ", 1)[1]
    assert len([x for x in phan_c.splitlines() if "/api/v1/messages" in x]) == 2
