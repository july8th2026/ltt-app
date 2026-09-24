"""MOT cua bao gia cho CA do thi — `/agent/api/v3/workflows/{id}/bao-gia`.

No §5 cua `docs/superpowers/plans/2026-09-24-wf-v2-MASTER.md`, lan `p10-don`.

## Vi sao co tep nay

`CanvasShell.tsx` goi `quoteTool(...)` **cho tung node**, trong mot effect chay
lai moi lan `page.nodes` doi — tuc moi lan nguoi ta go mot ky tu. Do thi 12
node = **12 request** moi lan bung (do duoc o
`frontend/agent-canvas/tests/BaoGiaMotCua.test.tsx`: `expected 12 to be 1`).

⛔ **Debounce khong phai cau tra loi.** `setTimeout(...,450)` da co san o dong
   do tu truoc; no giam TAN SUAT, khong giam **do lon** cua mot lan bung.

## 🔴 MOT NGUON GIA, KHONG HAI

Cua cu `/agent/api/tools/{ten}/quote` (`workspace.py:165`) tra
`credit_for(...) * fanout * (1 + max_retry)`. Hai thua so ay **khong ton tai
o bat ky cho nao trong runtime v2** (grep `fanout` trong `platform_core/
workflow` va `apps/agent`: chi chinh route do). Con so that ma nen tang GIU
tien theo la `bao_gia._gia_node` × `he_so_lap` (`bao_gia_do_thi`), va
`cau_noi.nop_job` so `gia_that > node["gia_tran"]` voi dung con so ay.

⇒ Cua moi **khong tinh gia lan hai**: no goi thang `bao_gia._gia_node`, cung
  ham ma `bao_gia_do_thi` goi. Bai `test_gia_KHOP_bao_gia_do_thi` la banh coc
  chot dieu do — no so hai ben tren cung mot do thi, nen mot ban chep se do.

## ⚠️ Pham vi hep hon loi tuyen bo

Cua nay tra `gia_tran` cua **MOT luot chay** tung node — dung thu Inspector
hien ("Tối đa N credit"). No **khong** nhan `he_so_lap` cua `foreach` vao;
tong cua ca run la viec cua `/publish` (`credit_max`). Bai duoi co ve khang
dinh cho dieu do de khong ai tuong cua nay tra tong.
"""
from __future__ import annotations

import copy
import json
import re

import pytest
from fastapi.testclient import TestClient

from platform_core.workflow import bao_gia
from platform_core.workflow.cong_cu import CongCu


def _gia_theo_so(params: dict) -> int:
    """Gia phu thuoc `so` va NEM khi thieu — de dung mot node "chua du du lieu"
    that su, thay vi gia dinh mot node hong."""
    if "so" not in params:
        raise ValueError("thieu `so`")
    return int(params["so"]) * 10


def _cc(ten: str) -> CongCu:
    return CongCu(ten=ten, app_slug="app_" + ten.split(".")[0],
                  job_type=ten + ".job", type_version=2,
                  params_schema={"so": {"type": "int", "max": 7}},
                  side_effect="external", idempotency_fields=(),
                  tinh_gia=_gia_theo_so, returns={"text": "text"})


CC = {"text.chat": _cc("text.chat"), "image.generate": _cc("image.generate")}


def _node(nid: str, tool: str, params: dict | None = None) -> dict:
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": tool, "params": {} if params is None else params}}


def _canh(eid: str, a: str, b: str) -> dict:
    return {"id": eid, "source_node": a, "target_node": b,
            "source_port": "text", "target_port": "in", "kind": "DATA"}


#: a -> b, va `c` roi. Gia: a=20, b=50, c=30.
DOC = {"version": 3, "pages": [{"id": "p1",
       "edges": [_canh("e1", "a", "b")],
       "nodes": [_node("a", "text.chat", {"so": 2}),
                 _node("b", "image.generate", {"so": 5}),
                 _node("c", "text.chat", {"so": 3})]}]}


# ── 1. Lop nhan: mot ham, tra bang gia tung node ─────────────────────────

def test_bang_gia_song_tra_gia_TUNG_node():
    ra = bao_gia.bang_gia_song(DOC, cong_cu=CC)
    assert ra.gia == {"a": 20, "b": 50, "c": 30}
    assert ra.loi == {}


def test_gia_KHOP_bao_gia_do_thi():
    """🔑 BANH COC MOT NGUON GIA.

    `bao_gia_do_thi` la duong ma `/publish` di qua — cai GHI `gia_tran` ma
    `cau_noi.nop_job` doi chieu luc nop job that. Cua song phai tra dung con
    so ay; lech mot don vi la giao dien noi mot dang, so tien giu mot dang.
    """
    from platform_core.workflow import bien_dich

    graph = bien_dich.bien_dich(copy.deepcopy(DOC), cong_cu=CC)
    bao_gia.bao_gia_do_thi(graph, cong_cu=CC)
    assert bao_gia.bang_gia_song(DOC, cong_cu=CC).gia == graph["bang_gia"]


def test_node_CHUA_DU_DU_LIEU_chi_mat_gia_cua_CHINH_NO():
    """Nguoi dung dang go: mot node chua co tham so khong duoc lam ca bang
    gia bien mat.

    🔑 Doi chung nam ngay trong bai: hai node kia **van co gia**. Thieu ve ay
       thi mot ban tra bang RONG cung xanh.
    """
    doc = copy.deepcopy(DOC)
    doc["pages"][0]["nodes"][1]["data"]["params"] = {}     # `b` thieu `so`
    ra = bao_gia.bang_gia_song(doc, cong_cu=CC)
    assert ra.gia == {"a": 20, "c": 30}
    assert "b" in ra.loi and "b" not in ra.gia


def test_bang_gia_song_KHONG_ghi_vao_tai_lieu_cua_nguoi_goi():
    """`bao_gia_do_thi` GHI `gia_tran`/`bang_gia`/`he_so_lap` vao do thi no
    nhan. Cua song chay tren ban nhap dang go cua nguoi dung ⇒ no khong duoc
    de lai dau vet nao trong tai lieu ay."""
    doc = copy.deepcopy(DOC)
    truoc = json.dumps(doc, sort_keys=True)
    bao_gia.bang_gia_song(doc, cong_cu=CC)
    assert json.dumps(doc, sort_keys=True) == truoc


def test_gia_la_cua_MOT_luot_chay_khong_nhan_he_so_foreach():
    """⚠️ Ve khang dinh cho pham vi ghi trong docstring dau tep.

    `gia_tran` cua mot node trong than `foreach` van la gia cua MOT luot —
    dung nhu `bao_gia_do_thi` ghi. Ai do nhan `he_so_lap` vao day se noi mot
    con so khac han voi thu Inspector phai hien.
    """
    doc = {"version": 3, "pages": [{"id": "p1", "edges": [
        _canh("e1", "f", "a"), _canh("e2", "a", "fe")], "nodes": [
            {"id": "f", "type": "core.foreach", "position": {"x": 0, "y": 0},
             "params": {"items": "{{ workflow.input.xs }}", "max_items": 9}},
            _node("a", "text.chat", {"so": 2}),
            {"id": "fe", "type": "core.foreach_end", "position": {"x": 0, "y": 0},
             "params": {"foreach": "f"}}]}]}
    ra = bao_gia.bang_gia_song(doc, cong_cu=CC)
    assert ra.gia["a"] == 20, "20 la gia MOT luot; 180 nghia la da nhan he so"


def test_do_thi_HONG_CAU_TRUC_bao_ma_loi_thay_vi_nem():
    """Trinh soan co the o giua mot thao tac: hai node trung id, mot canh tro
    vao hu khong. Cua bao gia khong duoc sap — no bao `loi_do_thi` va giao
    dien xoa bang gia."""
    doc = copy.deepcopy(DOC)
    doc["pages"][0]["nodes"].append(_node("a", "text.chat", {"so": 1}))
    ra = bao_gia.bang_gia_song(doc, cong_cu=CC)
    assert ra.gia == {} and ra.loi_do_thi
    assert ra.loi_do_thi["ma"] == "id_trung"


# ── 2. Cua HTTP ───────────────────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'baogia.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("bg-a@example.com", "bg-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                       is_verified=True)
    db.commit()
    db.close()
    dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "baogia-test-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"',
                          page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
        html = client.get("/agent/canvas").text
        return client, re.search(r'data-csrf-token="([^"]+)"', html).group(1)

    from platform_core.workflow import cong_cu as _cong_cu
    monkeypatch.setattr(_cong_cu, "tat_ca", lambda: dict(CC))
    a, token_a = login("bg-a@example.com")
    b, token_b = login("bg-b@example.com")
    yield app, a, token_a, b, token_b
    a.close()
    b.close()
    dbmod.reset_engine()


def _wf(email: str) -> str:
    import platform_core.db as dbmod
    from platform_core.models import User
    from platform_core.workflow import dinh_nghia
    db = next(dbmod.get_session())
    try:
        uid = db.query(User).filter_by(email=email).one().id
        wf = dinh_nghia.tao_workflow(db, owner_id=uid, name="w")
        dinh_nghia.luu_draft(db, wf.id, document=copy.deepcopy(DOC),
                             revision=0)
        db.commit()
        return wf.id
    finally:
        db.close()


def _goi(client, token, wf_id, body=None):
    return client.post(
        f"/agent/api/v3/workflows/{wf_id}/bao-gia",
        headers={"X-CSRF-Token": token, "Accept": "application/json"},
        json={**(body or {}), "csrf_token": token})


def test_MOT_request_tra_gia_CUA_MOI_NODE(api):
    _app, a, token_a, _b, _token_b = api
    wf_id = _wf("bg-a@example.com")
    r = _goi(a, token_a, wf_id)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["gia"] == {"a": 20, "b": 50, "c": 30}


def test_cua_dung_TAI_LIEU_GUI_KEM_khi_co(api):
    """Nguoi dung vua go xong mot o tham so, autosave chua chay (800 ms).
    Bao gia phai theo thu DANG GO, khong theo ban da luu."""
    _app, a, token_a, _b, _token_b = api
    wf_id = _wf("bg-a@example.com")
    doc = copy.deepcopy(DOC)
    doc["pages"][0]["nodes"][0]["data"]["params"] = {"so": 7}
    r = _goi(a, token_a, wf_id, {"document": doc})
    assert r.status_code == 200, r.text
    assert r.json()["gia"]["a"] == 70      # ⭐ 20 nghia la doc ban da luu


def test_workflow_cua_NGUOI_KHAC_tra_404_va_khong_ro_gia(api):
    _app, _a, _token_a, b, token_b = api
    wf_id = _wf("bg-a@example.com")
    r = _goi(b, token_b, wf_id)
    assert r.status_code == 404
    assert '"a"' not in r.text and "50" not in r.text


def test_chua_dang_nhap_thi_khong_co_bao_gia(api):
    app, _a, _token_a, _b, _token_b = api
    wf_id = _wf("bg-a@example.com")
    khach = TestClient(app, base_url="https://testserver",
                       follow_redirects=False)
    r = khach.post(f"/agent/api/v3/workflows/{wf_id}/bao-gia",
                   headers={"Accept": "application/json"},
                   json={"csrf_token": "x"})
    assert r.status_code in (302, 303, 400, 401, 403)
    assert '"gia"' not in r.text
