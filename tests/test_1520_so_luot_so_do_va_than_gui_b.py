"""test_1520 — sổ lượt `llm_waiters` mang SỐ ĐO; thân gửi máy B không mang định danh khách. (T4 P2)

Thiết kế: `docs/ltt_llm_dual/artifacts/THIET_KE_R06_R07_ID_PHIEN.md` §1a, §2.3, §6.3.

Chốt:
  1. Lượt xong ⇒ `llm_waiters.token_vao/token_ra/token_cache` = số đếm của A,
     `ttfb_s` = byte dữ liệu đầu (phía A). Không đo được ⇒ **NULL, không 0**
     (cùng luật sổ B `so_luot.py`: 0 là khẳng định, null là thú nhận).
  2. Cửa một cục (`/messages` stream:false) và `/chat/completions` ghi token,
     `ttfb_s` NULL (không có byte nào chảy trước cả lượt).
  3. Thân gửi B **không** có `metadata` / `client_metadata` / `prompt_cache_key`
     / `user` / `safety_identifier`; mọi khoá sinh khác còn nguyên (so TẬP khoá).
  4. Migration add-only, nullable, nối đúng head trước, một head duy nhất.

Đối chứng (tiêm lỗi, chạy tay khi viết — ghi ở báo cáo commit):
  * `SoDo.tu_su_dung` trả `0` thay `None` khi không đo được ⇒ (1b) ĐỎ.
  * gỡ lời gọi `_go_dinh_danh_khach` ở `tien_kiem` ⇒ (3) ĐỎ.
"""
from __future__ import annotations

import json

import pytest

from tests import test_1511_so_request_phien as _t1511
from tests.test_1511_so_request_phien import (
    CHAT, MSG, MODEL, RSP, _account, _close, _dat_mot_cuc, _h_claude, _h_codex,
    _khoi, _session, _than, _than_rsp)

#: Giàn app + B giả của P1 — dùng lại, không chép (cùng khuôn `test_272`).
api = _t1511.api

DINH_DANH = {"metadata", "client_metadata", "prompt_cache_key", "user",
             "safety_identifier"}
REV = "e4a19c07b5d2"
REV_CHA = "b7d41e2c9a05"
COT_SO_DO = ("token_vao", "token_ra", "token_cache", "ttfb_s")


# ── Giàn: B giả bắt THÂN gửi lên ─────────────────────────────────────────────

def _dat_luong_bat_than(monkeypatch, tao_khoi=_khoi):
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
        da_goi.append({"duong": duong, "than": json.loads(json.dumps(than)),
                       "request_id": request_id})
        return GiaLuong(tao_khoi())

    monkeypatch.setattr(luong_vlm, "mo", gia)
    return da_goi


def _waiter(user_id: str):
    from platform_core.models import LlmWaiter
    gen, db = _session()
    try:
        rows = db.query(LlmWaiter).filter(LlmWaiter.user_id == user_id).all()
        for r in rows:
            db.expunge(r)
        return rows
    finally:
        _close(gen)


# ── 1. Luồng: token + TTFB vào sổ lượt ──────────────────────────────────────

def test_luong_xong_ghi_token_va_ttfb(api, monkeypatch):
    goi = _dat_luong_bat_than(monkeypatch)
    user_id, token = _account()
    r = api.post(MSG, json=_than(), headers=_h_claude(token))
    assert r.status_code == 200, r.text
    r.read()

    (w,) = _waiter(user_id)
    assert w.ket_qua == "xong", w.ket_qua
    assert (w.token_vao, w.token_ra, w.token_cache) == (100, 50, 0)
    assert w.ttfb_s is not None and 0.0 <= w.ttfb_s < 30.0, w.ttfb_s
    assert goi and goi[0]["request_id"] == w.request_id


def _chet_truoc_byte_dau():
    raise RuntimeError("B dut truoc byte dau")
    yield b""  # pragma: no cover - generator


def test_luong_chet_truoc_byte_dau_thi_NULL_khong_phai_0(api, monkeypatch):
    """(1b) Không đo được là NULL. `0` sẽ nói dối là "đo được, không sinh gì"."""
    _dat_luong_bat_than(monkeypatch, tao_khoi=_chet_truoc_byte_dau)
    user_id, token = _account()
    try:
        r = api.post(MSG, json=_than(), headers=_h_claude(token))
        r.read()
    except RuntimeError:
        pass  # TestClient có thể nổi lỗi của generator — chỉ sổ là thứ cần đo

    (w,) = _waiter(user_id)
    assert w.ket_qua == "loi", w.ket_qua
    assert (w.token_vao, w.token_ra, w.token_cache, w.ttfb_s) == (
        None, None, None, None), (
        "luong khong do duoc ma so ghi so — 0 la mot khang dinh, phai la NULL")


# ── 2. Cửa một cục + /chat/completions ─────────────────────────────────────

def test_mot_cuc_ghi_token_ttfb_null(api, monkeypatch):
    _dat_mot_cuc(monkeypatch)
    user_id, token = _account()
    than = _than(max_tokens=2_000)
    than.pop("stream")
    r = api.post(MSG, json=than, headers=_h_claude(token))
    assert r.status_code == 200, r.text

    (w,) = _waiter(user_id)
    assert w.ket_qua == "xong"
    assert (w.token_vao, w.token_ra, w.token_cache, w.ttfb_s) == (
        8_000, 2_000, 0, None)


def test_chat_completions_ghi_token(api, monkeypatch):
    import uuid
    _dat_mot_cuc(monkeypatch)
    user_id, token = _account()
    h = _h_codex(token)
    h["Idempotency-Key"] = uuid.uuid4().hex
    r = api.post(CHAT, json={"model": MODEL, "max_tokens": 2_000,
                             "messages": [{"role": "user", "content": "xin chao"}]},
                 headers=h)
    assert r.status_code == 200, r.text

    (w,) = _waiter(user_id)
    assert (w.token_vao, w.token_ra, w.ttfb_s) == (8_000, 2_000, None)


# ── 3. Thân gửi B: gỡ định danh khách, giữ mọi khoá sinh ────────────────────

_TOOL = {"name": "doc_tep", "description": "doc mot tep",
         "input_schema": {"type": "object", "properties": {"p": {"type": "string"}}}}


def test_messages_stream_than_gui_B_khong_co_dinh_danh(api, monkeypatch):
    goi = _dat_luong_bat_than(monkeypatch)
    user_id, token = _account()
    than = _than(system="ban la tro ly", tools=[_TOOL],
                 top_p=0.9, top_k=40, stop_sequences=["HET"],
                 metadata={"user_id": json.dumps({
                     "device_id": "d" * 64, "account_uuid": "",
                     "session_id": "829c76f3-5d2a-4b1e-9c3f-38eea5feef82"})})
    r = api.post(MSG, json=than, headers=_h_claude(token))
    assert r.status_code == 200, r.text
    r.read()

    (g,) = goi
    gui = set(g["than"])
    assert not (DINH_DANH & gui), f"dinh danh khach di xuong B: {DINH_DANH & gui}"
    mat = (set(than) - DINH_DANH) - gui
    assert not mat, f"go nham khoa sinh: {mat}"
    assert "d" * 64 not in json.dumps(g["than"])


def test_responses_stream_than_gui_B_khong_co_dinh_danh_codex(api, monkeypatch):
    goi = _dat_luong_bat_than(monkeypatch)
    user_id, token = _account()
    than = _than_rsp(
        prompt_cache_key="01a0b544-0000-7c21-9d44-000000000abc",
        client_metadata={"session_id": "s", "x-codex-installation-id": "inst-x"},
        user="khach-noi-bo-42", safety_identifier="sid-9",
        tools=[{"type": "function", "name": "doc_tep",
                "parameters": {"type": "object", "properties": {}}}],
        tool_choice="auto", parallel_tool_calls=True, top_p=0.9)
    r = api.post(RSP, json=than, headers=_h_codex(token))
    assert r.status_code == 200, r.text
    r.read()

    (g,) = goi
    gui = set(g["than"])
    assert not (DINH_DANH & gui), f"dinh danh khach di xuong B: {DINH_DANH & gui}"
    mat = (set(than) - DINH_DANH) - gui
    assert not mat, f"go nham khoa sinh: {mat}"
    assert "inst-x" not in json.dumps(g["than"])


def test_ham_go_thuan_va_khong_sua_than_goc():
    from platform_core.runtime_noi_bo import luong

    assert set(luong.TRUONG_DINH_DANH_KHACH) == DINH_DANH
    goc = {"model": "m", "metadata": {"user_id": "x"}, "prompt_cache_key": "k",
           "tools": [], "top_p": 0.5}
    ban = dict(goc)
    luong._go_dinh_danh_khach(ban)
    assert ban == {"model": "m", "tools": [], "top_p": 0.5}
    assert "metadata" in goc, "ham go phai sua BAN SAO `gui`, khong phai than cua khach"


def test_ca_hai_cua_stream_deu_go():
    """`tien_kiem` (cửa có phòng chờ) và `chuan_bi` (cửa cũ) đều chép `dict(than)`."""
    import inspect

    from platform_core.runtime_noi_bo import luong

    for ten in ("tien_kiem", "chuan_bi"):
        nguon = inspect.getsource(getattr(luong, ten))
        assert "_go_dinh_danh_khach(gui)" in nguon, (
            f"`luong.{ten}` chep than khach len B ma khong go dinh danh")


# ── 4. phong_cho: SoDo thuần ────────────────────────────────────────────────

def test_so_do_tu_su_dung():
    from platform_core.llm.cong_vlm import SuDung
    from platform_core.llm.phong_cho import SoDo

    s = SoDo.tu_su_dung(SuDung(token_vao=10, token_ra=3, token_vao_cache=4,
                               dang_tin=True), ttfb_s=1.23456)
    assert (s.token_vao, s.token_ra, s.token_cache, s.ttfb_s) == (10, 3, 4, 1.235)
    s = SoDo.tu_su_dung(SuDung(dang_tin=False), ttfb_s=None)
    assert (s.token_vao, s.token_ra, s.token_cache, s.ttfb_s) == (
        None, None, None, None)
    s = SoDo.tu_su_dung(None, ttfb_s=0.5)
    assert (s.token_vao, s.ttfb_s) == (None, 0.5)


def test_ghi_ket_thuc_khong_so_do_thi_cot_NULL(tmp_path, monkeypatch):
    """Đường ra không đo (bận, lỗi trước lượt) để cột NULL — không ghi 0."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "w.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen, db = _session()
    try:
        for wid in ("w1", "w2"):
            db.add(LlmWaiter(id=wid, resource="r", user_id="u", request_id=wid,
                             trang_thai="nhan"))
        db.commit()
        phong_cho.ghi_ket_thuc("w1", "ban")
        phong_cho.ghi_ket_thuc("w2", "xong", so_do=phong_cho.SoDo(
            token_vao=7, token_ra=0, token_cache=0, ttfb_s=0.0))
        db.expire_all()
        w1, w2 = db.get(LlmWaiter, "w1"), db.get(LlmWaiter, "w2")
        assert (w1.token_vao, w1.token_ra, w1.ttfb_s) == (None, None, None)
        # 0 đo được là khẳng định hợp lệ — phải giữ được, không bị coi là "không có".
        assert (w2.token_vao, w2.token_ra, w2.token_cache, w2.ttfb_s) == (7, 0, 0, 0.0)
    finally:
        _close(gen)
        dbmod.reset_engine()


# ── 5. Migration ────────────────────────────────────────────────────────────

def _cfg():
    from pathlib import Path

    from alembic.config import Config
    goc = Path(__file__).resolve().parent.parent
    cfg = Config(str(goc / "alembic.ini"))
    cfg.set_main_option("script_location", str(goc / "alembic"))
    return cfg


def test_migration_mot_head_noi_sau_P1():
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(_cfg())
    assert len(scripts.get_heads()) == 1, scripts.get_heads()
    assert scripts.get_revision(REV).down_revision == REV_CHA


def test_mo_hinh_cot_so_do_nullable():
    from platform_core.models import LlmWaiter

    for ten in COT_SO_DO:
        c = LlmWaiter.__table__.c[ten]
        assert c.nullable and c.server_default is None and c.default is None, ten


@pytest.mark.timeout(300)
def test_sqlite_upgrade_roi_ma_cu_van_insert_va_downgrade_sach(tmp_path, monkeypatch):
    from alembic import command
    from sqlalchemy import create_engine, inspect, text

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    cfg = _cfg()
    command.upgrade(cfg, REV)
    eng = create_engine(url)
    cot = {c["name"] for c in inspect(eng).get_columns("llm_waiters")}
    assert set(COT_SO_DO) <= cot
    with eng.begin() as c:
        c.execute(text(
            "INSERT INTO llm_waiters (id, resource, cua, lop, user_id, request_id, "
            "token_dat_truoc, token_prefill_moi, la_whale, created_at, heartbeat_at, "
            "trang_thai, ly_do_cho, so_nhip, ket_qua, lease_id) VALUES ('1','r','',"
            "'','u','m',0,0,0,'2026-09-19 00:00:00','2026-09-19 00:00:00','cho','',"
            "0,'','')"))
        assert c.execute(text(
            "SELECT token_vao, token_ra, token_cache, ttfb_s FROM llm_waiters")
        ).one() == (None, None, None, None)
    command.downgrade(cfg, REV_CHA)
    cot = {c["name"] for c in inspect(eng).get_columns("llm_waiters")}
    assert not set(COT_SO_DO) & cot, "downgrade khong go het cot so do"
    command.upgrade(cfg, "head")
    eng.dispose()
