# -*- coding: utf-8 -*-
"""Cua duyet/tu choi `core.human` — `apps/agent/routes/phe_duyet_v3.py` (UI-8a).

## Dieu phep kiem nay giu

`platform_core/workflow/nut_loi/cho.py::chay_human` va `noi_lai.mo()` da song
tu truoc (dong bang test_1793). Tep nay chi do PHAN MOI: mot cua HTTP dung
CHINH cac ham do, va bon bat bien rieng cua mot cua CO PHIEN NGUOI DUNG (khac
`/hooks/wp/{id}` la cua CONG KHAI dung token):

1. **404, khong 403, cho run cua nguoi khac** — ranh gioi chu so huu la mot
   404, khong phai mot may dem.
2. **Thieu CSRF -> 400, KHONG dong waitpoint** — do bang chinh dong ho: goi
   sai CSRF roi kiem waitpoint van `PENDING`.
3. **Luy dang** — duyet hai lan khong sinh hai lan di tiep, va khong 500.
4. **`core.delay`/`core.wait` khong co cua duyet** — node WAITING vi DELAY thi
   cua nay tra 404 rieng (`khong_co_diem_cho_nguoi_duyet`), khong lien quan
   gi den waitpoint DELAY dang mo.

## Doi chung

Moi phu dinh o tren deu duoc chung minh DO DUOC (test danh dau "doi chung" tu
mot trang thai se pha vo no neu logic sai).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

import json
import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

EMAIL = "pheduyet6500@example.com"
EMAIL_KHAC = "pheduyet6500-khac@example.com"
MAT_KHAU = "Strong-pass-6500"
#: Xem chu thich o `test_6300_ket_noi_v3_cua_khach.py` — phai di qua BIEN.
_BI_MAT_PHIEN_THU = "phe-duyet-6500-session"


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    return {"id": f"{a}-{b}-{condition}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": kind,
            "condition": condition}


def _dang_nhap(app, email: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": email, "password": MAT_KHAU, "csrf_token": token,
        "next": "/agent/canvas"}).status_code == 200
    return client


def _csrf(client: TestClient) -> str:
    page = client.get("/agent/canvas")
    m = re.search(r'data-csrf-token="([^"]+)"', page.text)
    if m:
        return m.group(1)
    return re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)


@pytest.fixture()
def may_chu(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'pheduyet.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-6500-" + "k" * 32)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import credit
    from platform_core import registry as _reg
    from platform_core.users import tao_nguoi_dung

    _reg.load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    u1 = tao_nguoi_dung(db, email=EMAIL, password=MAT_KHAU, is_verified=True)
    u2 = tao_nguoi_dung(db, email=EMAIL_KHAC, password=MAT_KHAU, is_verified=True)
    credit.nap(db, u1.id, 100_000, note="test")
    credit.nap(db, u2.id, 100_000, note="test")
    db.commit()
    u1_id, u2_id = u1.id, u2.id
    db.close()
    dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                   encoding="utf-8")
    # 🔴 IMPORT TUONG MINH — `routes/__init__.py` la so dung chung (dieu phoi
    #    giu), lan nay KHONG them dong import vao do. Xem `test_6300`.
    import apps.agent.routes.phe_duyet_v3  # noqa: F401
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": _BI_MAT_PHIEN_THU,
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    yield {"app": app, "u1": u1_id, "u2": u2_id}
    dbmod.reset_engine()


@pytest.fixture()
def api(may_chu):
    client = _dang_nhap(may_chu["app"], EMAIL)
    yield client
    client.close()


@pytest.fixture()
def api_khac(may_chu):
    client = _dang_nhap(may_chu["app"], EMAIL_KHAC)
    yield client
    client.close()


def _db():
    import platform_core.db as dbmod
    return next(dbmod.get_session())


def _tao_run(owner_id: str, nodes: list, edges: list) -> str:
    """Dung TRUC TIEP `platform_core.workflow` — cung khuon `test_1793::lam` —
    de dua mot run toi `WAITING`, tren CHINH db file ma app HTTP se doc.
    """
    from platform_core.workflow import dinh_nghia, tao_run

    db = _db()
    w = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="wf-6500")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": nodes, "edges": edges}]})
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by=owner_id, cong_cu={})
    w.published_version_id = v.id
    db.flush()
    run, _ = tao_run.tao_run(db, workflow=w, owner_id=owner_id,
                             trigger_kind="manual",
                             idempotency_key=f"wk-{w.id}")
    db.commit()
    run_id = run.id
    db.close()
    return run_id


def _tick(run_id: str) -> None:
    from platform_core.workflow import dong_co

    db = _db()
    dong_co.xu_ly_run(db, run_id, cong_cu={})
    db.commit()
    db.close()


def _trang_thai(run_id: str, node_id: str, vong=()) -> str:
    from platform_core.workflow import may_trang_thai as mtt

    db = _db()
    try:
        return mtt.trang_thai_node(db, run_id, node_id, vong)
    finally:
        db.close()


def _waitpoint_status(run_id: str, kind: str) -> str:
    from platform_core.models import Waitpoint

    db = _db()
    try:
        wp = db.query(Waitpoint).filter_by(run_id=run_id, kind=kind).one()
        return wp.status
    finally:
        db.close()


def _run_human(owner_id: str) -> str:
    return _tao_run(owner_id, [
        _core("h", "human", cau_hoi="Duyet khong?"),
        _core("a", "set", bien={"da_duyet": "1"}),
        _core("r", "set", bien={"da_tu_choi": "1"})],
        [_canh("h", "a", kind="CONTROL", condition="approve"),
         _canh("h", "r", kind="CONTROL", condition="reject")])


def _duyet(api: TestClient, run_id: str, node_id: str, quyet_dinh: str,
          *, csrf: str | None = None, ghi_chu: str = "") -> "object":
    csrf = _csrf(api) if csrf is None else csrf
    than: dict = {"quyet_dinh": quyet_dinh, "csrf_token": csrf}
    if ghi_chu:
        than["ghi_chu"] = ghi_chu
    return api.post(f"/agent/api/v3/runs/{run_id}/nodes/{node_id}/duyet",
                    json=than, headers={"X-CSRF-Token": csrf})


# ── Đường sống: duyệt / từ chối đi đúng nhánh ────────────────────────────────

@pytest.mark.parametrize("quyet_dinh,chay,bo", [("approve", "a", "r"),
                                                ("reject", "r", "a")])
def test_duyet_di_dung_nhanh(may_chu, api, quyet_dinh, chay, bo):
    run_id = _run_human(may_chu["u1"])
    _tick(run_id)
    assert _trang_thai(run_id, "h") == "WAITING"

    r = _duyet(api, run_id, "h", quyet_dinh)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"ok": True, "da_dong_truoc_do": False,
                    "quyet_dinh": quyet_dinh}

    for _ in range(3):
        _tick(run_id)
    assert _trang_thai(run_id, chay) == "SUCCEEDED"
    assert _trang_thai(run_id, bo) == "SKIPPED"


def test_quyet_dinh_sai_422(may_chu, api):
    run_id = _run_human(may_chu["u1"])
    _tick(run_id)
    r = _duyet(api, run_id, "h", "co_le")
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["ma"] == "quyet_dinh_sai"
    assert _trang_thai(run_id, "h") == "WAITING", "doi chung: khong dong waitpoint"


# ── Bất biến 1: ranh giới chủ sở hữu là 404, không phải 403 ─────────────────

def test_run_cua_nguoi_khac_tra_404_khong_403(may_chu, api_khac):
    run_id = _run_human(may_chu["u1"])
    _tick(run_id)
    r = _duyet(api_khac, run_id, "h", "approve")
    assert r.status_code == 404, r.text
    # Doi chung: mot run_id BUA cung phai 404, khong phan biet duoc voi run
    # co that cua nguoi khac — do la dinh nghia cua "khong lo su ton tai".
    r2 = _duyet(api_khac, "khong-ton-tai", "h", "approve")
    assert r2.status_code == 404
    assert _trang_thai(run_id, "h") == "WAITING", "khong bi cham vao"


# ── Bất biến 2: thiếu CSRF -> 400, KHÔNG đóng waitpoint ─────────────────────

def test_thieu_csrf_tra_400_khong_dong_waitpoint(may_chu, api):
    run_id = _run_human(may_chu["u1"])
    _tick(run_id)
    r = api.post(f"/agent/api/v3/runs/{run_id}/nodes/h/duyet",
                json={"quyet_dinh": "approve"})  # KHONG X-CSRF-Token, KHONG csrf_token
    assert r.status_code == 400, r.text
    assert _waitpoint_status(run_id, "HUMAN") == "PENDING", \
        "doi chung: waitpoint van mo sau khi CSRF bi tu choi"
    assert _trang_thai(run_id, "h") == "WAITING"


# ── Bất biến 3: LUỸ ĐẲNG — duyệt hai lần không lật kết quả, không 500 ───────

def test_duyet_hai_lan_khong_500_khong_lat_ket_qua(may_chu, api):
    run_id = _run_human(may_chu["u1"])
    _tick(run_id)
    r1 = _duyet(api, run_id, "h", "approve")
    assert r1.status_code == 200
    # Lan hai: van la HTTP, van cung waitpoint (dong co CHUA can chay lai —
    # cu goi ngay de mo phong "bam dup"/hai tab).
    r2 = _duyet(api, run_id, "h", "reject")
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["da_dong_truoc_do"] is True
    assert body2["quyet_dinh"] == "approve", "khong duoc lat sang reject"

    for _ in range(3):
        _tick(run_id)
    assert _trang_thai(run_id, "a") == "SUCCEEDED"
    assert _trang_thai(run_id, "r") == "SKIPPED"


def test_duyet_waitpoint_da_het_han_tra_409_khong_lat(may_chu, api, monkeypatch):
    """Khe hở đã khai trong docstring module: `het_han_luc` đã qua nhưng động
    cơ chưa kịp chạy `tiep_mot()` để đóng waitpoint. Cửa này phải TỪ CHỐI,
    ⛔ không tự quyết định thay `che_do_het_han`."""
    import apps.agent.routes.phe_duyet_v3 as cua

    run_id = _tao_run(may_chu["u1"], [
        _core("h", "human", timeout_s=30),
        _core("a", "set", bien={"da_duyet": "1"}),
        _core("r", "set", bien={"da_tu_choi": "1"})],
        [_canh("h", "a", kind="CONTROL", condition="approve"),
         _canh("h", "r", kind="CONTROL", condition="reject")])
    _tick(run_id)
    assert _trang_thai(run_id, "h") == "WAITING"
    assert _waitpoint_status(run_id, "HUMAN") == "PENDING"

    tuong_lai = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=31)
    monkeypatch.setattr(cua, "_bay_gio", lambda: tuong_lai)
    r = _duyet(api, run_id, "h", "approve")
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["ma"] == "da_het_han"
    assert _waitpoint_status(run_id, "HUMAN") == "PENDING", \
        "doi chung: cua nay KHONG tu dong waitpoint thay dong co"

    # Doi chung nguoc: dong co (voi cung dong ho gia) mac dinh REJECT, ⛔
    # khong phai APPROVE ma request vua thu.
    monkeypatch.setattr("platform_core.workflow.nut_loi.cho._bay_gio",
                        lambda: tuong_lai)
    monkeypatch.setattr("platform_core.workflow.noi_lai._bay_gio",
                        lambda: tuong_lai)
    for _ in range(3):
        _tick(run_id)
    assert _trang_thai(run_id, "r") == "SUCCEEDED"
    assert _trang_thai(run_id, "a") == "SKIPPED"


# ── Bất biến 4: `core.delay`/`core.wait` không có nút duyệt (cũng ở backend) ─

def test_node_dang_cho_DELAY_khong_co_cua_duyet(may_chu, api):
    run_id = _tao_run(may_chu["u1"], [_core("d", "delay", duration_s=999)], [])
    _tick(run_id)
    assert _trang_thai(run_id, "d") == "WAITING"
    r = _duyet(api, run_id, "d", "approve")
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["ma"] == "khong_co_diem_cho_nguoi_duyet"
    # Doi chung: waitpoint DELAY van con nguyen, khong bi cham vao.
    assert _waitpoint_status(run_id, "DELAY") == "PENDING"


def test_node_khong_ton_tai_trong_run_tra_404(may_chu, api):
    run_id = _run_human(may_chu["u1"])
    _tick(run_id)
    r = _duyet(api, run_id, "khong-co-node-nay", "approve")
    assert r.status_code == 404
