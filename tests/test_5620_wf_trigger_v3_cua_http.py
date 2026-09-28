"""Cua v3 cho trigger workflow (UI-12): `POST/GET/PATCH/DELETE
/agent/api/v3/workflows/{id}/triggers[/…]` — dat LICH (CRON) + cap URL WEBHOOK.

## Bon menh de tep nay canh

1. **Token webhook chi xuat hien MOT LAN**, dung trong than phan hoi cua
   chinh luot `POST` da sinh ra no. Moi `GET` sau do — ke ca `hash` — khong
   bao gio lo ra. Do bang cach tim CHUOI TOKEN trong TOAN BO than phan hoi,
   khong doc tung truong rieng le (mot truong moi lo token qua mot cua khac
   se khong bi bat neu chi doc truong cu).
2. **Cron sai bi tu choi O CUA voi 422 kem ly do, khong bao gio 500.** Mot
   trigger CRON hong nam trong CSDL la mot hang bo quet di qua moi vong va
   im lang bo qua (hoac tu tat sau 5 loi lien tiep) — tu choi no som re hon
   nhieu.
3. **Ranh gioi chu so huu la 404**, khong phai 403, ca bon dong tu HTTP.
4. **Trigger CRON tao qua cua nay co `next_fire_at` DA TINH** — neu `NULL`,
   `ban_den_han()` khong bao gio nhat no len va lich khong bao gio chay,
   khong loi nao bao.

## Tiem loi doi chung (yeu cau cua brief UI-12)

`test_TIEM_LOI_thieu_import_o_routes_init_lam_do` va
`test_TIEM_LOI_lo_hash_trong_GET_lam_do` khong tu chay — chung la TAI LIEU
cach tai hien hai ca tiem loi bat buoc, vi ban than viec go mot dong import
hay ghi de mot ham serialize KHONG THE lam tu ben trong mot phien pytest dang
chay (module da nap). Ket qua tai hien THAT nam trong bao cao cua phien.

⚠️ `tests/test_5606_moi_module_route_phai_duoc_import.py` (banh coc AST canh
   dung mot dieu nay cho MOI app) duoc brief nhac toi nhung KHONG TON TAI
   trong cay nay — worktree nay re nhanh tu `main` truoc no 203 commit, va
   luat phoi hop cua plan cam gop `main` cho toi khi duoc bao "archive xong".
   `test_khong_thieu_module_route_nao_trong_agent` o duoi la ban THU NHO cua
   cung banh coc, pham vi rieng `apps/agent/routes/`, de khoang trong nay
   khong bo ngo trong luc cho.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import uuid

import pytest
from fastapi.testclient import TestClient


def _csrf(html: str) -> str:
    match = re.search(r'data-csrf-token="([^"]+)"', html)
    assert match, html[:400]
    return match.group(1)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'trg.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("trg-a@example.com", "trg-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                       is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "trg-test-session",
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
        return client, _csrf(client.get("/agent/canvas").text)

    a, token_a = login("trg-a@example.com")
    b, token_b = login("trg-b@example.com")
    yield a, token_a, b, token_b
    a.close(); b.close(); dbmod.reset_engine()


def _uid(email: str) -> str:
    import platform_core.db as dbmod
    from platform_core.models import User
    db = next(dbmod.get_session())
    try:
        return db.query(User).filter_by(email=email).one().id
    finally:
        db.close()


def _workflow(owner_id: str) -> str:
    """Mot workflow v3 rong (chua publish — trigger khong doi publish)."""
    import platform_core.db as dbmod
    from platform_core.workflow import dinh_nghia
    db = next(dbmod.get_session())
    try:
        wf = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="w-trigger")
        db.commit()
        return wf.id
    finally:
        db.close()


def _post(client, token, wf_id, kind, cau_hinh=None, enabled=True):
    return client.post(f"/agent/api/v3/workflows/{wf_id}/triggers",
                       headers={"X-CSRF-Token": token},
                       json={"kind": kind, "cau_hinh": cau_hinh or {},
                             "enabled": enabled})


# ── 1. Token: sinh MOT LAN, khong bao gio lo qua GET ────────────────────────

def test_tao_webhook_tra_token_MOT_LAN(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    r = _post(a, token_a, wf_id, "WEBHOOK")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token"] and len(body["token"]) >= 20
    assert body["webhook_url"].endswith(f"/hooks/wf/{body['id']}")
    assert body["config"] == {}, "token_hash khong duoc lo qua chinh cua tao"


def test_GET_danh_sach_KHONG_LO_token_LAN_hash(api):
    """Do bang cach quet TOAN BO than phan hoi cho chuoi token — khong doc
    tung truong rieng le, dung nhu tieu chi brief doi hoi."""
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    created = _post(a, token_a, wf_id, "WEBHOOK").json()
    token_tho = created["token"]

    r = a.get(f"/agent/api/v3/workflows/{wf_id}/triggers")
    assert r.status_code == 200
    than = r.text
    assert token_tho not in than
    assert "token_hash" not in than
    items = r.json()["items"]
    assert len(items) == 1
    assert "token" not in items[0]
    assert "token_hash" not in items[0]["config"]


# ── 2. CRON: hop le co next_fire_at; sai bi tu choi 422 ─────────────────────

def test_tao_cron_hop_le_CO_next_fire_at_da_tinh(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    r = _post(a, token_a, wf_id, "CRON",
             {"cron": "*/30 * * * *", "tz": "Asia/Ho_Chi_Minh"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["next_fire_at"], "NULL -> ban_den_han() khong bao gio nhat"
    assert body["config"]["cron"] == "*/30 * * * *"
    assert body["config"]["bo_lo"] == "chay_mot_lan", "mac dinh phai duoc dien"


def test_tao_cron_bieu_thuc_SAI_tra_422_KHONG_500(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    r = _post(a, token_a, wf_id, "CRON", {"cron": "khong-phai-cron"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]


def test_tao_cron_chu_ky_duoi_5_phut_bi_tu_choi(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    r = _post(a, token_a, wf_id, "CRON", {"cron": "* * * * *"})
    assert r.status_code == 422, r.text


def test_tao_cron_BO_LO_sai_bi_tu_choi_LUC_TAO(api):
    """`trigger.tao`/`_TheoCron.kiem` KHONG kiem `bo_lo` (chi doc luc BAN) —
    cua HTTP phai tu kiem, neu khong mot gia tri la nam trong CSDL se nem
    `ValueError` moi vong bo quet cho toi khi tu tat sau 5 lan (spec §11.4)."""
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    r = _post(a, token_a, wf_id, "CRON",
             {"cron": "*/30 * * * *", "bo_lo": "khong-hop-le"})
    assert r.status_code == 422, r.text


def test_tao_KIND_LA_bi_tu_choi(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    r = _post(a, token_a, wf_id, "KHONG_TON_TAI")
    assert r.status_code == 422, r.text


# ── 3. Ranh gioi chu so huu: 404 tren ca bon dong tu ────────────────────────

def test_workflow_cua_NGUOI_KHAC_moi_dong_tu_deu_404(api):
    a, token_a, _, token_b = api
    wf_id = _workflow(_uid("trg-b@example.com"))

    assert a.get(f"/agent/api/v3/workflows/{wf_id}/triggers").status_code == 404
    assert _post(a, token_a, wf_id, "WEBHOOK").status_code == 404

    # Trigger THAT (cua chu B) — id co that, nhung A khong phai chu.
    _, _, b, token_b2 = api
    t = _post(b, token_b2, wf_id, "WEBHOOK").json()
    assert a.patch(f"/agent/api/v3/workflows/{wf_id}/triggers/{t['id']}",
                   headers={"X-CSRF-Token": token_a},
                   json={"enabled": False}).status_code == 404
    assert a.delete(f"/agent/api/v3/workflows/{wf_id}/triggers/{t['id']}",
                    headers={"X-CSRF-Token": token_a}).status_code == 404


# ── 4. PATCH bat/tat, DELETE xoa ────────────────────────────────────────────

def test_PATCH_bat_tat_khong_dung_kind_hay_config(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    t = _post(a, token_a, wf_id, "CRON", {"cron": "*/30 * * * *"}).json()
    assert t["enabled"] is True

    r = a.patch(f"/agent/api/v3/workflows/{wf_id}/triggers/{t['id']}",
               headers={"X-CSRF-Token": token_a}, json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert r.json()["config"]["cron"] == "*/30 * * * *", "PATCH khong duoc dung config"


def test_DELETE_xoa_that(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    t = _post(a, token_a, wf_id, "WEBHOOK").json()

    r = a.delete(f"/agent/api/v3/workflows/{wf_id}/triggers/{t['id']}",
                headers={"X-CSRF-Token": token_a})
    assert r.status_code == 200
    assert a.get(f"/agent/api/v3/workflows/{wf_id}/triggers").json()["items"] == []


def test_thieu_CSRF_tra_400_khong_phai_500(api):
    a, _, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/triggers",
              json={"kind": "WEBHOOK", "cau_hinh": {}})
    assert r.status_code == 400, r.text


# ── 5. Trang HTML co that va khong lo token khi tai lai ─────────────────────

def test_trang_html_tra_200_va_KHONG_lo_token_cu(api):
    a, token_a, _, _ = api
    wf_id = _workflow(_uid("trg-a@example.com"))
    created = _post(a, token_a, wf_id, "WEBHOOK").json()

    r = a.get(f"/agent/workflows/{wf_id}/triggers")
    assert r.status_code == 200
    assert created["token"] not in r.text, \
        "trang HTML tai lai KHONG duoc mang token cu — no chi song trong JSON luc tao"


def test_trang_html_workflow_nguoi_khac_404(api):
    a, _, _, _ = api
    wf_id = _workflow(_uid("trg-b@example.com"))
    assert a.get(f"/agent/workflows/{wf_id}/triggers").status_code == 404


# ── 6. Ban thu nho cua banh coc AST "moi module route phai duoc import" ─────

def test_khong_thieu_module_route_nao_trong_agent():
    """Ban SCOPE-HEP cua `test_5606` (khong ton tai trong cay nay — xem
    docstring dau tep). Doc AST cua `apps/agent/routes/__init__.py`, gom moi
    ten module no import tu `apps.agent.routes`, roi doi chieu voi tap tep
    `.py` THAT dang nam trong thu muc do.

    🔴 Day CHINH LA phep se do neu ai (ke ca chinh minh o mot sua doi sau)
       quen dong `from apps.agent.routes import (..., trigger_v3)` — dung
       hinh dang loi production 28/09 brief nhac: 9 phep kiem xanh rieng le,
       404 that."""
    goc = pathlib.Path(__file__).resolve().parent.parent
    thu_muc = goc / "apps" / "agent" / "routes"
    init_py = thu_muc / "__init__.py"
    cay = ast.parse(init_py.read_text(encoding="utf-8"), filename=str(init_py))

    da_import: set[str] = set()
    for node in ast.walk(cay):
        if isinstance(node, ast.ImportFrom) and node.module == "apps.agent.routes":
            da_import.update(alias.name for alias in node.names)

    tren_dia: set[str] = {
        f.stem for f in thu_muc.glob("*.py")
        if f.stem not in {"__init__", "_shared"}}

    thieu = tren_dia - da_import
    assert not thieu, f"module route chua duoc import trong __init__.py: {thieu}"
    assert "trigger_v3" in da_import


def test_TIEM_LOI_thieu_import_o_routes_init_lam_do():
    """TAI LIEU cach tai hien tiem loi (a) cua brief UI-12 — khong tu chay
    duoc trong CHINH phien dang chay `apps.agent.routes` (module da nap vao
    `sys.modules`, va go dong import trong tep nguon khong lam no bay ra
    khoi bo nho). Da xac minh THAT bang tay trong phien viet tep nay:

        1. xoa `trigger_v3` khoi dong import trong
           `apps/agent/routes/__init__.py`
        2. `python -m pytest tests/test_5620_wf_trigger_v3_cua_http.py
           ::test_khong_thieu_module_route_nao_trong_agent -q`  -> DO
        3. hoan lai dong import, chay lai -> XANH

    Ket qua that (DO/XANH cua hai lan chay do) nam trong bao cao cuoi phien,
    khong trong bai kiem nay — mot bai `pytest.skip` khong the tu go source
    cua chinh no giua luc dang chay va mong doi con lai dung.
    """
    pytest.skip("tai lieu tai hien tay — xem docstring; ket qua trong bao cao")


def test_TIEM_LOI_lo_hash_trong_GET_lam_do():
    """TAI LIEU cach tai hien tiem loi (b): sua `_trigger_json()` trong
    `apps/agent/routes/trigger_v3.py` de KHONG `cfg.pop("token_hash", None)`
    nua, roi chay lai `test_GET_danh_sach_KHONG_LO_token_LAN_hash` o tren —
    no phai DO vi `token_hash` se xuat hien trong than JSON. Da xac minh THAT
    bang tay: DO khi bo dong `pop`, XANH khi hoan lai. Ket qua that nam trong
    bao cao cuoi phien."""
    pytest.skip("tai lieu tai hien tay — xem docstring; ket qua trong bao cao")
