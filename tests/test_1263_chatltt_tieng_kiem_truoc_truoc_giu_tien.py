"""
test_1263 — `speech.ltt` qua ChatLTT phai chay CUNG pre-check voi `/api/v1`
(D007, `docs/LTT_VOICE/GUI_DOI_SOAT_VA_PLAN_V2.md` W4').

Truoc ban sua: `runtime_noi_bo/job.py` khong goi `ToolSpec.kiem_truoc`, nen mot
giong VI + van ban EN **giu credit + xep job** roi moi bi worker tu choi
`voice_language_mismatch` va hoan. Luat san pham: chan TRUOC moi job/credit.

  1. `runtime_noi_bo.job.bao_gia` nem `ThamSoSai` mang `ma` cua app.
  2. `/chatltt/api/bao-gia` -> 400 `voice_language_mismatch`.
  3. `/chatltt/api/hoi-thoai/{id}/tao` -> 400, KHONG job, KHONG tin nhan, so du nguyen.
  4. V3 (model tu goi): `ma_loi` cua ket qua la ma nghiep vu, khong phai `bao_gia_hong`.

⛔ Khong chep luat lan ngon ngu vao day: cau "EN + giong Adam" la cung cau ma
   `tests/test_524_public_api_kiem_truoc.py` dung, va nguon chan ly van la
   `apps/ltt_voice/lan_ngon_ngu.quyet_dinh`.
"""
from __future__ import annotations

import re
import uuid

import pytest

TOOL_TIENG = "speech.ltt"
MA = "voice_language_mismatch"
LECH = {"text": "The quick brown fox jumps over the lazy dog that we know.",
        "preset": "Adam"}


def test_bao_gia_noi_bo_chay_kiem_truoc_va_mang_ma():
    from platform_core.runtime_noi_bo import job as J

    with pytest.raises(J.ThamSoSai) as e:
        J.bao_gia(TOOL_TIENG, dict(LECH), db=None, user_id="u-1263")
    assert e.value.ma == MA


def test_bao_gia_noi_bo_hop_le_van_ra_gia():
    from platform_core.runtime_noi_bo import job as J

    bg = J.bao_gia(TOOL_TIENG, {"text": "Xin chào, hôm nay trời rất đẹp.",
                                "preset": "Adam"}, db=None, user_id="u-1263")
    assert bg.credit > 0


# ── HTTP that ────────────────────────────────────────────────────────────────

@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "m.db").as_posix())
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
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-1263",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


def _voi_db(fn):
    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        return fn(db)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _user(credits=1000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    def _tao(db):
        email = "m1263-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12",
                           is_verified=True)
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id, email
    return _voi_db(_tao)


def _dang_nhap(web, email):
    r = web.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    web.post("/login", data={"username": email, "password": "a-good-password-12",
                             "csrf_token": m.group(1), "next": "/chatltt"},
             follow_redirects=True)
    r = web.get("/chatltt")
    return {"X-CSRF-Token": re.search(r'data-csrf="([^"]+)"', r.text).group(1)}


def test_bao_gia_chatltt_lech_lan_ra_400_co_ma(web):
    _uid, email = _user()
    h = _dang_nhap(web, email)
    r = web.post("/chatltt/api/bao-gia", headers=h,
                 json={"nang_luc": TOOL_TIENG, "tham_so": dict(LECH)})
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == MA


def test_tao_chatltt_lech_lan_khong_giu_tien_khong_job_khong_tin_nhan(web):
    from apps.chatltt.tables import ChatlttExecution, ChatlttMessage
    from platform_core import credit
    from platform_core.models import Job

    uid, email = _user(1000)
    h = _dang_nhap(web, email)
    cv = web.post("/chatltt/api/hoi-thoai", json={"model_alias": "ltt_llm"},
                  headers=h).json()["id"]
    tin_truoc = _voi_db(lambda db: db.query(ChatlttMessage).count())

    r = web.post(f"/chatltt/api/hoi-thoai/{cv}/tao", headers=h,
                 json={"nang_luc": TOOL_TIENG, "tham_so": dict(LECH)})
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == MA

    assert _voi_db(lambda db: int(credit.so_du(db, uid))) == 1000
    assert _voi_db(lambda db: db.query(Job).filter(Job.user_id == uid).count()) == 0
    assert _voi_db(lambda db: db.query(ChatlttExecution).count()) == 0
    assert _voi_db(lambda db: db.query(ChatlttMessage).count()) == tin_truoc


# ── V3: model tu goi ─────────────────────────────────────────────────────────

def test_v3_bao_gia_bi_tu_choi_thi_model_doc_duoc_ma_nghiep_vu():
    from apps.chatltt.services import bo_chay_tool, tao_media
    from apps.chatltt.services import dieu_phoi as DP

    def bg(ten, doi_so):
        raise tao_media.ThamSoSai("giong VI, van ban EN", ma=MA)

    chay = bo_chay_tool.tao(None, user_id="u-1263", run_id="r-1263",
                            khoi_tools=[], bao_gia=bg)
    kq = chay(TOOL_TIENG, dict(LECH), DP.NgoCanhGoi(thu_tu=1))
    assert kq.ok is False
    assert kq.ma_loi == MA
