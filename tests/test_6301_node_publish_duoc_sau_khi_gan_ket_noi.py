# -*- coding: utf-8 -*-
"""33 node MO KHOA khi co `credential_ref` — do bang CONG PUBLISH THAT (UI-5).

## Vi sao bai nay ton tai

Lan UI-5 khong sua mot dong nao trong `bien_dich`/`dinh_nghia`: cong chan da
dung tu 25/09. Thu duoc them la mot **duong** de gan `credential_ref`. Nen phep
do phai tra loi dung mot cau: *"bao nhieu node chuyen tu KHONG publish duoc
sang publish duoc, chi vi co mot ref?"*

⚠️ BAY DA GAP KHI DUNG PHEP DO NAY (28/09): do voi `params = {}` cho ra **7**
   thay vi 33, vi `_kiem_tham_so_loi` chay TRUOC cong credential va nem
   `thieu_tham_so`. Mot phep do dung nhung nham cau hoi: no do *"node nao
   publish duoc voi tham so rong"*. Bai nay dien DU tham so bat buoc tu chinh
   luoc do, nen cong credential moi la thu duy nhat con lai.

## Va bai kiem ca DUONG DAY

`test_gan_ket_noi_qua_HTTP_roi_publish_duoc` di dung duong ma trinh duyet di:
`POST /agent/api/v3/ket-noi` -> `PUT` draft co `credential_ref` o **muc tren
cung** cua buoc -> `POST .../publish`. ⛔ Ghi ref duoi `data` thi
`bien_dich._node_tu_dinh_nghia` khong thay no, va publish van bao "chua gan ket
noi" trong khi giao dien hien mot ket noi da chon — mot bat dong IM LANG.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

EMAIL = "publish6301@example.com"
MAT_KHAU = "Strong-pass-6301"

#: ⛔ Chot DUOI, khong chot bang: catalog piece co the mọc thêm mục, và một bài
#: đòi ĐÚNG 33 sẽ đỏ vì một lý do không liên quan gì tới cửa kết nối.
SAN_MO_KHOA = 33


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'pub.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-6301-" + "p" * 32)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import registry as _reg
    _reg.load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.credit import cap_tay
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email=EMAIL, password=MAT_KHAU, is_verified=True)
    db.flush()
    cap_tay(db, u.id, 5000, by="test", note="6301")
    db.commit()
    yield db
    db.close()
    dbmod.reset_engine()


def _gia_tri(luat: dict):
    """Mot gia tri HOP LE cho mot truong, doc tu chinh luoc do.

    ⛔ Khong mot bang gia tri go tay: mot truong moi trong luoc do phai tu co
       gia tri, khong thi phep do lai roi ve `thieu_tham_so` va noi doi."""
    if luat.get("default") is not None:
        return luat["default"]
    if isinstance(luat.get("enum"), list) and luat["enum"]:
        return luat["enum"][0]
    t = luat.get("type")
    if t == "integer":
        return int(luat.get("minimum") or 1)
    if t == "number":
        return float(luat.get("minimum") or 1)
    if t == "boolean":
        return True
    if t == "array":
        return []
    if t == "object":
        return {}
    return "x"


def _params_day_du(nd) -> dict:
    lo = nd.tham_so or {}
    thuoc = lo.get("properties") or {}
    ra = {k: _gia_tri(thuoc.get(k) or {}) for k in (lo.get("required") or [])}
    for nhom in (lo.get("mot_trong") or []):
        if nhom and not any(k in ra for k in nhom):
            ra[nhom[0]] = _gia_tri(thuoc.get(nhom[0]) or {})
    return ra


def _thu_publish(db, u_id, nd, cc, ref: str = "") -> str:
    """`""` = publish duoc; nguoc lai la `ma` loi. Mot workflow moi moi lan."""
    from platform_core.workflow import dinh_nghia
    wf = dinh_nghia.tao_workflow(db, owner_id=u_id, name="do-6301")
    db.commit()
    buoc = {"id": "n1", "type": nd.type, "params": _params_day_du(nd)}
    if ref:
        buoc["credential_ref"] = ref
    dinh_nghia.luu_draft(db, wf.id, document={
        "version": 3, "goal": "", "budget_max_credit": 0,
        "active_page_id": "p1",
        "pages": [{"id": "p1", "name": "", "nodes": [buoc], "edges": []}]},
        revision=0)
    db.commit()
    try:
        dinh_nghia.xuat_ban_draft(db, wf.id, created_by=u_id, cong_cu=cc)
        db.commit()
        return ""
    except Exception as exc:                        # noqa: BLE001
        db.rollback()
        return str(getattr(exc, "ma", "") or type(exc).__name__)


def test_ket_noi_MO_KHOA_it_nhat_33_node_tren_cong_publish_that(moi_truong):
    db = moi_truong
    from platform_core import credential as kho
    from platform_core.models import User
    from platform_core.workflow import cong_cu, nut
    u = db.query(User).filter_by(email=EMAIL).one()
    cc = dict(cong_cu.tat_ca())
    so = nut.tat_ca(cong_cu=cc)
    # Mot ket noi cho MOI kieu, de moi node duoc gan dung kieu no nhan.
    ref = {k: kho.tao(db, owner_id=u.id, kieu=k, ten="t",
                      bi_mat="x" * 20).id for k in kho.KIEU}
    db.commit()

    truoc, sau, mo_khoa = 0, 0, []
    for _ten, nd in sorted(so.items()):
        yc = tuple(getattr(nd, "credential", ()) or ())
        ma0 = _thu_publish(db, u.id, nd, cc)
        ma1 = _thu_publish(db, u.id, nd, cc, ref[yc[0]] if yc else "")
        truoc += not ma0
        sau += not ma1
        if ma0 and not ma1:
            mo_khoa.append((nd.type, ma0))

    # 🔴 CON SO CUA LAN NAY. Do 28/09 tren cay nay: 72 node, 34 doi credential,
    #    27 -> 60 publish duoc, 33 mo khoa.
    assert len(mo_khoa) >= SAN_MO_KHOA, (
        f"chi {len(mo_khoa)} node mo khoa (san {SAN_MO_KHOA}); "
        f"truoc={truoc} sau={sau}")
    # ⭐ Va MOI node mo khoa phai mo khoa vi DUNG mot ly do. Mot node "mo khoa"
    #    vi mot ma loi khac la mot phep do dang tu khen minh.
    assert {ma for _t, ma in mo_khoa} == {"credential_khong_hop_le"}
    assert sau > truoc


def test_doi_chung_ref_CUA_NGUOI_KHAC_khong_mo_khoa_gi(moi_truong):
    """🔑 Doi chung: neu cong chi hoi *"co ref hay khong"* thi ref cua nguoi
    khac cung mo khoa — va bai tren xanh trong khi bao mat da vo."""
    db = moi_truong
    from platform_core import credential as kho
    from platform_core.models import User
    from platform_core.users import tao_nguoi_dung
    from platform_core.workflow import cong_cu, nut
    u = db.query(User).filter_by(email=EMAIL).one()
    khac = tao_nguoi_dung(db, email="khac6301@example.com",
                          password=MAT_KHAU, is_verified=True)
    db.flush()
    ref_khac = kho.tao(db, owner_id=khac.id, kieu="oauth2", ten="cua-nguoi-khac",
                       bi_mat="y" * 20).id
    db.commit()
    cc = dict(cong_cu.tat_ca())
    nd = next(x for x in nut.tat_ca(cong_cu=cc).values()
              if "oauth2" in (getattr(x, "credential", ()) or ()))
    assert _thu_publish(db, u.id, nd, cc, ref_khac) == "credential_khong_hop_le"


def test_doi_chung_tham_so_RONG_do_mot_cau_hoi_KHAC(moi_truong):
    """⚠️ Bay da gap. Voi `params={}` thi cong tham so nem TRUOC cong credential,
    nen phep do do *"publish duoc voi tham so rong"* — mot cau hoi khac."""
    db = moi_truong
    from platform_core.models import User
    from platform_core.workflow import cong_cu, dinh_nghia, nut
    u = db.query(User).filter_by(email=EMAIL).one()
    cc = dict(cong_cu.tat_ca())
    nd = next(x for x in nut.tat_ca(cong_cu=cc).values()
              if (getattr(x, "credential", ()) or ())
              and (x.tham_so or {}).get("required"))
    wf = dinh_nghia.tao_workflow(db, owner_id=u.id, name="rong")
    db.commit()
    dinh_nghia.luu_draft(db, wf.id, document={
        "version": 3, "goal": "", "budget_max_credit": 0,
        "active_page_id": "p1",
        "pages": [{"id": "p1", "name": "",
                   "nodes": [{"id": "n1", "type": nd.type, "params": {}}],
                   "edges": []}]}, revision=0)
    db.commit()
    try:
        dinh_nghia.xuat_ban_draft(db, wf.id, created_by=u.id, cong_cu=cc)
        raise AssertionError("publish khong duoc phep thanh cong o day")
    except Exception as exc:                        # noqa: BLE001
        assert getattr(exc, "ma", "") == "thieu_tham_so"


# ── Duong day THAT: HTTP -> draft -> publish ─────────────────────────────

@pytest.fixture()
def api(tmp_path, moi_truong, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                   encoding="utf-8")
    # 🔴 Import tuong minh — `routes/__init__.py` la so dung chung S5 (UI-1).
    import apps.agent.routes.ket_noi_v3  # noqa: F401
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "publish-6301-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver",
                        follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": EMAIL, "password": MAT_KHAU, "csrf_token": token,
        "next": "/agent/canvas"}).status_code == 200
    yield client
    client.close()


def _csrf(client: TestClient) -> str:
    page = client.get("/agent/canvas")
    m = re.search(r'data-csrf-token="([^"]+)"', page.text)
    return (m or re.search(r'name="csrf_token" value="([^"]+)"',
                           page.text)).group(1)


def _mot_buoc_doi_api_key():
    """Mot buoc nhan `api_key` VA thuoc dien bi chan khi thieu ref.

    ⚠️ ⛔ Khong lay buoc dau tien nhan `api_key`: `core.http` nhan no nhung
       `job_type` cua no NGOAI `JOB_TYPE_KHONG_TOOLSPEC`, nen
       `dinh_nghia._kiem_credential` **khong** chan no khi thieu ref. Dung no o
       day thi buoc 1 cua bai (publish phai TU CHOI) xanh gia theo chieu
       nguoc — no do mot node khong he bi chan.
    """
    from platform_core.workflow import cong_cu, nut
    cc = dict(cong_cu.tat_ca())
    for nd in sorted(nut.tat_ca(cong_cu=cc).values(), key=lambda x: x.type):
        if ("api_key" in (getattr(nd, "credential", ()) or ())
                and nd.job_type in nut.JOB_TYPE_KHONG_TOOLSPEC):
            return nd
    raise AssertionError("khong node nao nhan `api_key` va bi chan khi thieu ref")


def _rev(api: TestClient, wf_id: str) -> int:
    return int(api.get(f"/agent/api/v3/workflows/{wf_id}").json()["revision"])


def _publish(api: TestClient, wf_id: str, doc: dict):
    """Luu draft roi publish. ⭐ Doc `revision` TU MAY CHU chu khong dem tay:
    cua tao workflow co the tu ghi mot draft rong, va mot so dem tay thi lech
    ngay tu luot dau (409 da gap 28/09)."""
    rev = _rev(api, wf_id)
    csrf = _csrf(api)
    r = api.put(f"/agent/api/v3/workflows/{wf_id}",
                json={"document": doc, "revision": rev, "csrf_token": csrf},
                headers={"X-CSRF-Token": csrf, "If-Match": f'"{rev}"'})
    assert r.status_code == 200, r.text
    csrf = _csrf(api)
    return api.post(f"/agent/api/v3/workflows/{wf_id}/publish",
                    json={"csrf_token": csrf},
                    headers={"X-CSRF-Token": csrf})


def test_gan_ket_noi_qua_HTTP_roi_publish_duoc(api):
    nd = _mot_buoc_doi_api_key()
    csrf = _csrf(api)
    wf = api.post("/agent/api/v3/workflows",
                  json={"name": "e2e-6301", "csrf_token": csrf},
                  headers={"X-CSRF-Token": csrf}).json()
    buoc = {"id": "n1", "type": nd.type, "params": _params_day_du(nd)}
    doc = {"version": 3, "goal": "", "budget_max_credit": 0,
           "active_page_id": "p1",
           "pages": [{"id": "p1", "name": "", "nodes": [buoc], "edges": []}]}

    # 1. Chua co ket noi -> publish TU CHOI, kem `node_id` de giao dien to node.
    r = _publish(api, wf["id"], doc)
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["ma"] == "credential_khong_hop_le"
    assert r.json()["detail"]["node_id"] == "n1"

    # 2. Tao ket noi qua DUNG cua ma Inspector goi.
    csrf = _csrf(api)
    kn = api.post("/agent/api/v3/ket-noi",
                  json={"kieu": "api_key", "ten": "Khoa cua toi",
                        "bi_mat": {"gia_tri": "sk-6301-abcdefgh"},
                        "csrf_token": csrf},
                  headers={"X-CSRF-Token": csrf})
    assert kn.status_code == 201, kn.text

    # 3. Ghi ref o MUC TREN CUNG cua buoc -> publish DUOC.
    buoc["credential_ref"] = kn.json()["id"]
    r = _publish(api, wf["id"], doc)
    assert r.status_code == 200, r.text


def test_ref_ghi_duoi_data_KHONG_dung_duoc(api):
    """🔴 Bat dong IM LANG: giao dien hien mot ket noi da chon, cong publish bao
    "chua gan". `bien_dich._node_tu_dinh_nghia` doc khoa o MUC TREN CUNG."""
    nd = _mot_buoc_doi_api_key()
    csrf = _csrf(api)
    wf = api.post("/agent/api/v3/workflows",
                  json={"name": "sai-cho-6301", "csrf_token": csrf},
                  headers={"X-CSRF-Token": csrf}).json()
    csrf = _csrf(api)
    kn = api.post("/agent/api/v3/ket-noi",
                  json={"kieu": "api_key", "ten": "K",
                        "bi_mat": {"gia_tri": "sk-6301-ijklmnop"},
                        "csrf_token": csrf},
                  headers={"X-CSRF-Token": csrf}).json()
    doc = {"version": 3, "goal": "", "budget_max_credit": 0,
           "active_page_id": "p1",
           "pages": [{"id": "p1", "name": "", "nodes": [
               {"id": "n1", "type": nd.type, "params": _params_day_du(nd),
                "data": {"credential_ref": kn["id"]}}], "edges": []}]}
    r = _publish(api, wf["id"], doc)
    assert r.status_code == 422
    assert r.json()["detail"]["ma"] == "credential_khong_hop_le"
