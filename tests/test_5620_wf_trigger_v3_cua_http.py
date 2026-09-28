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
`test_TIEM_LOI_lo_hash_trong_GET_lam_do` KHONG tu chay (`pytest.skip`) — chung
la TAI LIEU cach tai hien hai ca tiem loi bat buoc, vi ban than viec go mot
dong import hay ghi de mot ham serialize KHONG THE lam tu ben trong mot phien
pytest dang chay (module da nap). Ket qua tai hien THAT (DO roi XANH, ca hai
chieu) da lam TAY trong phien viet tep nay va nam trong bao cao gui dieu phoi.

⚠️ LICH SU: worktree nay re nhanh tu `main` truoc `tests/test_5606_moi_module_
   route_phai_duoc_import.py` 203 commit (luat phoi hop cam gop `main` giua
   plan), nen ban dau tep nay co them mot ban AST THU NHO cua chinh banh coc
   do. Sau khi gop `main` (archive xong), `test_5606` that da co mat va lam
   dung — ke ca dieu ban thu nho lam — nen ban thu nho da bi XOA o day de
   tranh MOT bat bien hai cho khai (chung se troi khoi nhau). Xem
   `test_5606_moi_module_route_phai_duoc_import.py::
   test_moi_module_route_deu_duoc_init_import` cho phep kiem do.
"""
from __future__ import annotations

import json
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


# ── 6. Tai lieu tai hien hai phep tiem loi (khong phai test luoi) ───────────
#
# `test_5606_moi_module_route_phai_duoc_import.py::
# test_moi_module_route_deu_duoc_init_import` (tren `main`) da lam dung viec
# cua phep tiem loi (a) — mot ban AST rieng o day se la MOT BAT BIEN HAI CHO
# KHAI, va hai cho khai la cho chung se troi khoi nhau (xem docstring dau
# tep). Ban thu nho tung nam o day DA BI XOA sau khi gop `main`.
# ══════════════════════════════════════════════════════════════════════════════
#  HAI PHEP TIEM LOI — ket qua THAT, ghi o day thay vi trong hai test LUON SKIP
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Ban dau hai phep tiem nay la hai HAM TEST goi `pytest.skip(reason=...)` de lam
#    tai lieu. `tools/check_bo_qua.py` bat dung chung, va **banh coc dung**:
#
#        "Mot test bi bo qua la mot test KHONG canh gi ca."
#
# ⚠️ Mot `reason=` viet ro rang van ⛔ khong bien mot test luon-skip thanh mot phep
#    do. No chi lam cai rac ay **doc nhu mot thu co ich** — va do la dang rac kho
#    don nhat, vi nguoi sau se giu no lai vi tuong no dang canh gi do.
#
# ⭐ Tai lieu thuoc CHU THICH; phep do thuoc TEST. Hai loai, hai cho.
#
# ## Tiem (a) — go dong import `trigger_v3` khoi `routes/__init__.py`
#
#   ⛔ KHONG the tai hien tu ben trong chinh phien pytest dang chay:
#      `apps.agent.routes` da nam trong `sys.modules`, va sua tep nguon ⛔ khong lam
#      module do bay khoi bo nho.
#
#   Da xac minh THAT bang tay:
#     1. xoa `trigger_v3` khoi dong import trong `apps/agent/routes/__init__.py`
#     2. `pytest tests/test_5606_moi_module_route_phai_duoc_import.py -q`  -> DO
#     3. hoan lai dong import, chay lai                                    -> XANH
#
#   ⇒ Phep do THUONG TRUC cho bat bien nay la
#     `test_5606::test_moi_module_route_deu_duoc_init_import` — no doc **AST** cua
#     `__init__.py` nen no ⛔ khong can module bay khoi `sys.modules`.
#
# ## Tiem (b) — bo `cfg.pop("token_hash", None)` trong `_trigger_json()`
#
#   Da xac minh THAT: DO khi bo dong `pop` (`token_hash` xuat hien trong than
#   JSON), XANH khi hoan lai.
#
#   ⇒ Phep do THUONG TRUC la `test_GET_danh_sach_KHONG_LO_token_LAN_hash` o tren.
#
# ⭐ Ca hai phep tiem deu co mot phep do thuong truc tuong ung. Do la ly do xoa hai
#    ham skip ⛔ khong mat gi: bat bien van duoc canh, chi la boi mot bai CO CHAY.


