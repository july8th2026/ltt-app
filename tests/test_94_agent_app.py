"""P8 regression: trang `/agent` co xac thuc va hop dong UX cua no.

⛔ 23/09 (spec §17.4) — luong `POST /agent/plan` -> `/agent/runs/{id}` (lap ke
   hoach bang AI roi duyet/tick) DA BI GO cung runtime v1, nen bay bai di qua
   no o day da bi xoa: chung do mot duong KHONG CON TON TAI. Cac menh de that
   cua chung khong bi mat — chung di tiep tren cua v3:

       giu cho truoc khi chay   -> `test_1723::test_tao_run_di_qua_tao_run_nen_CO_giu_tien`
       thieu credit khong chay  -> `test_1723::test_thieu_credit_tra_402_chu_khong_500`
       ranh gioi chu so huu 404 -> `test_1723::test_doc_run_cua_nguoi_khac_tra_404`
       huy lan chay             -> `test_1724::test_huy_lan_dau_tra_CANCELLED_va_ghi_su_kien`

⭐ Bai CON LAI o day do thu khong app nao khac do: trang HTML `/agent` — no vua
   chuyen tu `legacy_runs.py` sang `trang.py` va phai giu NGUYEN hanh vi
   (chuyen huong an danh ve `/login?next=`, va render 200 cho nguoi da dang
   nhap). `test_1726` chot rang duong van co trong bang dinh tuyen; bai duoi
   day chot rang no van CHAY.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, html[:500]
    return match.group(1)


@pytest.fixture()
def web(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'agent-web.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    from platform_core import credit, users
    user = users.tao_nguoi_dung(db, email="agent@example.com", password="Strong-pass-123",
                                is_verified=True)
    other = users.tao_nguoi_dung(db, email="other@example.com", password="Strong-pass-123",
                                 is_verified=True)
    credit.cap_tay(db, user.id, 100, by="test")
    db.commit(); uid, other_id = user.id, other.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    client = TestClient(create_app(env={
        "LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "agent-test-session-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
    }), base_url="https://testserver", follow_redirects=False)
    login = client.get("/login?next=/agent")
    response = client.post("/login", data={"username": "agent@example.com",
        "password": "Strong-pass-123", "csrf_token": _csrf(login.text), "next": "/agent"})
    assert response.status_code == 303 and response.headers["location"] == "/agent"

    yield client, uid, other_id, db_url
    client.close(); dbmod.reset_engine()


def test_manifest_nap_sach_va_an_danh_return_to(web):
    client, *_ = web
    from platform_core.registry import discover
    app = {item.slug: item for item in discover()}["agent"]
    assert not app.error and app.router is not None and app.manifest.public
    anon = TestClient(client.app, base_url="https://testserver", follow_redirects=False)
    response = anon.get("/agent")
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/agent"
    # 🔑 Ve doi chung: nguoi DA dang nhap phai thay trang that. Truoc 23/09
    #    menh de nay chi di nho trong `_make_plan` (no doc `csrf_token` tu
    #    HTML nay); xoa `_make_plan` ma khong viet lai day se lam mat luon
    #    phep kiem duy nhat RENDER trang `/agent`.
    trang = client.get("/agent")
    assert trang.status_code == 200 and _csrf(trang.text)
