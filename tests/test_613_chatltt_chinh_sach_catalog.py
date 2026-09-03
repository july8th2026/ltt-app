"""
test_613 — Phase 06: catalog ChatLTT theo CHÍNH SÁCH SẢN PHẨM, fail-closed.

  1. Chỉ ba năng lực V1 được mời; tên khác — kể cả tool có thật, `api_exposed=True` —
     không hiện và `kiem_cho_phep` ném.
  2. Ba cổng độc lập: `customer_visible=False` hay không bán qua API vẫn không đổi
     việc ChatLTT có mời hay không (và ngược lại).
  3. Modality lạ (vd `video`) trong allowlist thì KHÔNG hiện — bộ hiển thị không vẽ được.
  4. Sức khoẻ đến từ `AppManifest.suc_khoe` (đệm, fail-closed), không từ tên app.
  5. Route `/chatltt/api/danh-muc` đòi đăng nhập và không lộ id nội bộ.
"""
from __future__ import annotations

import json
import uuid

import pytest

from apps.chatltt.services import chinh_sach


def _loaded(manifest):
    from platform_core import registry as reg
    return reg.LoadedApp(manifest=manifest, router=None)


def _manifest(slug, tools, **g):
    from platform_core import registry as reg
    goc = dict(slug=slug, display_name=slug, route_prefix=f"/{slug}",
               job_types=tuple(sorted({t.job_type for t in tools})),
               credit_cost=lambda p: 1, enabled=True, surface="runtime",
               lifecycle="internal", tools=tuple(tools))
    goc.update(g)
    return reg.AppManifest(**goc)


def _tool(name, job_type, *, returns=None, api_exposed=True, customer_visible=True):
    from platform_core import registry as reg
    return reg.ToolSpec(
        name=name, job_type=job_type, description="d",
        params_schema={"prompt": {"type": "string", "required": True}},
        returns=returns or {"content": "text"},
        customer_visible=customer_visible, api_exposed=api_exposed,
        api_contract={"description": "cho khach", "scopes": ("jobs:create",),
                      "models": {"chuan": {"id": "engine-x-noi-bo"}}},
    )


# ── 1 + 2. Allowlist là cổng thứ ba ─────────────────────────────────────────

def test_allowlist_v1_va_kiem_cho_phep_fail_closed():
    assert chinh_sach.CONG_CU_CHO_PHEP == ("text.chat", "image.ltt", "speech.ltt")
    assert chinh_sach.kiem_cho_phep("text.chat") == "text.chat"
    with pytest.raises(chinh_sach.KhongDuocPhep):
        chinh_sach.kiem_cho_phep("image.generate")      # có thật, api_exposed, KHÔNG được mời
    with pytest.raises(chinh_sach.KhongDuocPhep):
        chinh_sach.kiem_cho_phep("text.khong_co")


def test_tool_ngoai_allowlist_khong_hien_du_api_exposed_va_customer_visible():
    apps = [
        _loaded(_manifest("a613", [_tool("text.chat", "a613.j")])),
        _loaded(_manifest("b613", [_tool("text.khac", "b613.j", api_exposed=True,
                                         customer_visible=True)])),
    ]
    ds = chinh_sach.danh_muc(None, user_id="u", apps=apps)
    assert [n.ten for n in ds] == ["text.chat"]


def test_customer_visible_false_van_duoc_moi_neu_trong_allowlist():
    """Ba cổng độc lập: palette Agent tắt không có nghĩa ChatLTT tắt."""
    apps = [_loaded(_manifest("c613", [_tool("text.chat", "c613.j", customer_visible=False)]))]
    ds = chinh_sach.danh_muc(None, user_id="u", apps=apps)
    assert [n.ten for n in ds] == ["text.chat"]


# ── 3. Modality lạ fail-closed ───────────────────────────────────────────────

def test_modality_video_trong_allowlist_van_khong_hien(monkeypatch):
    monkeypatch.setattr(chinh_sach, "CONG_CU_CHO_PHEP",
                        ("text.chat", "video.thu613"))
    apps = [
        _loaded(_manifest("d613", [_tool("text.chat", "d613.j")])),
        _loaded(_manifest("e613", [_tool("video.thu613", "e613.j",
                                         returns={"video_key": "video"})])),
    ]
    ds = chinh_sach.danh_muc(None, user_id="u", apps=apps)
    assert [n.ten for n in ds] == ["text.chat"]


def test_thu_tu_theo_allowlist_khong_theo_ten():
    apps = [
        _loaded(_manifest("f613", [_tool("speech.ltt", "f613.j", returns={"audio_key": "audio"})])),
        _loaded(_manifest("g613", [_tool("image.ltt", "g613.j", returns={"image_keys": "image[]"})])),
        _loaded(_manifest("h613", [_tool("text.chat", "h613.j")])),
    ]
    ds = chinh_sach.danh_muc(None, user_id="u", apps=apps)
    assert [n.ten for n in ds] == ["text.chat", "image.ltt", "speech.ltt"]
    assert [n.phuong_thuc for n in ds] == ["text", "image", "audio"]


# ── 4. Sức khoẻ qua hợp đồng ─────────────────────────────────────────────────

def test_suc_khoe_tu_manifest_dem_va_fail_closed():
    from platform_core.runtime_noi_bo import danh_muc as dm
    goi = []

    def hook():
        goi.append(1)
        return "ban"

    m = _manifest("i613", [_tool("text.chat", "i613.j")], suc_khoe=hook)
    dm._DEM_SUC_KHOE.clear()
    assert dm.suc_khoe_cua(m, now=100.0) == "ban"
    assert dm.suc_khoe_cua(m, now=105.0) == "ban" and len(goi) == 1     # đệm 10 s
    assert dm.suc_khoe_cua(m, now=120.0) == "ban" and len(goi) == 2

    def nem():
        raise RuntimeError("sidecar chet")

    m2 = _manifest("j613", [_tool("text.chat", "j613.j")], suc_khoe=nem)
    assert dm.suc_khoe_cua(m2) == "chua_san_sang"
    m3 = _manifest("k613", [_tool("text.chat", "k613.j")], suc_khoe=lambda: "xanh-la")
    assert dm.suc_khoe_cua(m3) == "chua_san_sang"                        # giá trị lạ
    m4 = _manifest("l613", [_tool("text.chat", "l613.j")])
    assert dm.suc_khoe_cua(m4) == "san_sang"                             # không khai
    m5 = _manifest("m613", [_tool("text.chat", "m613.j")], enabled=False)
    assert dm.suc_khoe_cua(m5) == "chua_san_sang"


def test_ltt_voice_va_ltt_llm_khai_suc_khoe():
    from apps.ltt_llm.manifest import MANIFEST as LLM
    from apps.ltt_voice.manifest import MANIFEST as VOICE
    assert callable(VOICE.suc_khoe) and callable(LLM.suc_khoe)


# ── 5. Route thật ────────────────────────────────────────────────────────────

@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "w.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    from fastapi.testclient import TestClient
    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-value-x",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


def _dang_nhap(web):
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "k613-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12",
                           is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    r = web.get("/login")
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    r = web.post("/login", data={"username": email, "password": "a-good-password-12",
                                 "csrf_token": m.group(1) if m else "", "next": "/chatltt"},
                 follow_redirects=True)
    assert r.status_code == 200, r.text[:300]
    return u.id


def test_api_danh_muc_doi_dang_nhap_va_khong_lo_id_noi_bo(web, monkeypatch):
    r = web.get("/chatltt/api/danh-muc", follow_redirects=False)
    assert r.status_code in (302, 303, 401)
    _dang_nhap(web)
    # Không thăm dò dịch vụ thật trong test.
    from platform_core.runtime_noi_bo import danh_muc as dm
    monkeypatch.setattr(dm, "suc_khoe_cua", lambda m, now=None: "san_sang")
    r = web.get("/chatltt/api/danh-muc")
    assert r.status_code == 200 and r.headers.get("cache-control") == "no-store"
    than = r.json()
    ten = [n["ten"] for n in than["nang_luc"]]
    assert ten == ["text.chat", "image.ltt", "speech.ltt"]
    van = json.dumps(than)
    for cam in ("qwen38", "hidream", "8299", "8199", "8120", "192.168."):
        assert cam not in van, cam
    assert all(n["san_sang"] == "san_sang" for n in than["nang_luc"])
    r = web.get("/chatltt")
    assert r.status_code == 200
