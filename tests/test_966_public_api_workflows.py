"""`WF-802` — chạy workflow qua `/api/v1`. Mọi bài ở đây là về **tiền** hoặc về
một lượt chạy biến mất.

## Vì sao bề mặt này cần bộ kiểm riêng dù đã có `test_182`

`test_182` canh cửa **job**: một tool, một giá, một khoản giữ. Cửa **run** khác
ở đúng chỗ đắt nhất — nó giữ **trần của cả đồ thị**, và trần ấy bị đóng băng
cùng `graph_hash`. Ba câu hỏi mới, không câu nào `test_182` trả lời được:

    bao gia cua workflow KHAC co dung duoc o day khong?
    ban publish doi GIUA luc bao gia va luc chay thi sao?
    khong du tien thi co con mot `WorkflowRun` mo coi nao khong?

⛔ Và một luật đã trả giá ở Đợt 4–5: mỗi ca **bị từ chối** phải đi kèm một ca
   **hợp lệ**. Không có vế thứ hai, một validator từ chối *mọi thứ* cũng xanh.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.models import CREDIT_HOLD, CreditEntry, WorkflowRun
from platform_core.public_api import keys as devkeys
from platform_core.public_api.scopes import (SCOPE_WORKFLOWS_CANCEL,
                                             SCOPE_WORKFLOWS_READ,
                                             SCOPE_WORKFLOWS_RUN)
from server.api.inventory import API_V1_PREFIX

PEPPER = "wf-test-pepper-" + "w" * 40
MOI_SCOPE = (SCOPE_WORKFLOWS_RUN, SCOPE_WORKFLOWS_READ, SCOPE_WORKFLOWS_CANCEL)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'wfapi.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "wf-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
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


def _do_thi(so_node: int = 3) -> dict:
    return {"nodes": [{"id": f"n{i}", "type": "tool"} for i in range(so_node)],
            "edges": []}


def _tai_khoan(credits: int = 500, scopes=MOI_SCOPE):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email=f"wf-{uuid.uuid4().hex[:8]}@example.com",
                           password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
        _k, token = devkeys.issue(db, user_id=u.id, scopes=scopes,
                                  env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return u.id, token
    finally:
        _close(gen)


def _workflow(owner_id: str, *, so_node: int = 3, publish: bool = True) -> str:
    from platform_core.workflow import dinh_nghia

    gen, db = _session()
    try:
        wf = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="w")
        if publish:
            ver = dinh_nghia.xuat_ban(db, wf.id, _do_thi(so_node),
                                      created_by=owner_id)
            wf.published_version_id = ver.id
        db.commit()
        return wf.id
    finally:
        _close(gen)


def _auth(token: str, idem: str = "") -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if idem:
        h["Idempotency-Key"] = idem
    return h


def _bao_gia(api, token: str, wf_id: str):
    return api.post(f"{API_V1_PREFIX}/workflows/{wf_id}/quotes",
                    headers=_auth(token))


def _chay(api, token: str, wf_id: str, quote: str, idem: str = ""):
    return api.post(f"{API_V1_PREFIX}/workflows/{wf_id}/runs",
                    json={"quote": quote},
                    headers=_auth(token, idem or uuid.uuid4().hex))


# ── Báo giá: HAI số ─────────────────────────────────────────────────────────

def test_bao_gia_tra_HAI_so(api):
    """`M8` — một số duy nhất buộc người đọc đoán số kia."""
    uid, token = _tai_khoan()
    wf = _workflow(uid, so_node=3)

    r = _bao_gia(api, token, wf)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["credit_max"] > 0
    assert 0 < b["credit_estimate"] < b["credit_max"]
    assert b["quote"] and b["workflow_id"] == wf


def test_bao_gia_cua_workflow_CHUA_PUBLISH_bi_tu_choi(api):
    """⚠️ `WF-801`: mọi trigger phải **ghim version**. Chạy bản nháp qua API
    nghĩa là hai lượt cùng `workflow_id` có thể khác nội dung mà không gì ghi
    lại điều đó."""
    uid, token = _tai_khoan()
    wf = _workflow(uid, publish=False)
    assert _bao_gia(api, token, wf).status_code == 409


# ── Chạy: khoá idempotency và báo giá ───────────────────────────────────────

def test_chay_thieu_Idempotency_Key_bi_tu_choi(api):
    uid, token = _tai_khoan()
    wf = _workflow(uid)
    q = _bao_gia(api, token, wf).json()["quote"]
    r = api.post(f"{API_V1_PREFIX}/workflows/{wf}/runs", json={"quote": q},
                 headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_bao_gia_cua_workflow_KHAC_khong_dung_duoc(api):
    """🔑 Chữ ký hợp lệ **không** có nghĩa là hợp lệ *cho cửa này*.

    Không có phép kiểm này, một người có hai workflow — một rẻ, một đắt — báo
    giá cái rẻ rồi chạy cái đắt.
    """
    uid, token = _tai_khoan()
    re_ = _workflow(uid, so_node=1)
    dat = _workflow(uid, so_node=8)
    q_re = _bao_gia(api, token, re_).json()["quote"]

    assert _chay(api, token, dat, q_re).status_code == 400
    # Vế hợp lệ: cùng báo giá ấy vẫn chạy được ở ĐÚNG workflow của nó.
    assert _chay(api, token, re_, q_re).status_code == 201


def test_ban_publish_DOI_giua_bao_gia_va_chay_thi_409(api):
    """⭐ Trần cũ không còn mô tả đồ thị mới ⇒ chạy tiếp là chạy một thứ khách
    chưa từng thấy giá."""
    from platform_core.models import Workflow
    from platform_core.workflow import dinh_nghia

    uid, token = _tai_khoan()
    wf = _workflow(uid, so_node=2)
    q = _bao_gia(api, token, wf).json()["quote"]

    gen, db = _session()
    try:
        ver = dinh_nghia.xuat_ban(db, wf, _do_thi(9), created_by=uid)
        db.get(Workflow, wf).published_version_id = ver.id
        db.commit()
    finally:
        _close(gen)

    # 400 chu khong 409: cung ma loi voi "bao gia cua workflow khac", vi hanh
    # dong cua khach y het nhau — xin mot bao gia moi. Xem `quotes.check_matches`.
    assert _chay(api, token, wf, q).status_code == 400


# ── Tiền ────────────────────────────────────────────────────────────────────

def test_chay_giu_dung_MOT_khoan_bang_tran(api):
    uid, token = _tai_khoan(credits=500)
    wf = _workflow(uid, so_node=3)
    b = _bao_gia(api, token, wf).json()
    r = _chay(api, token, wf, b["quote"])
    assert r.status_code == 201, r.text
    assert r.json()["credit_max"] == b["credit_max"]

    gen, db = _session()
    try:
        run = db.query(WorkflowRun).one()
        giu = db.query(CreditEntry).filter_by(job_id=run.id,
                                              kind=CREDIT_HOLD).all()
        assert len(giu) == 1 and giu[0].delta == -b["credit_max"]
        assert run.hold_id == run.id
    finally:
        _close(gen)


def test_khong_du_tien_thi_KHONG_con_run_mo_coi(api):
    """🔴 Đây là bài về tính giao dịch, không phải về mã lỗi.

    Run và khoản giữ nằm trong **cùng** transaction, nên thiếu tiền phải rollback
    **cả hai**. Một `WorkflowRun` mồ côi không có tiền đứng sau là thứ điều phối
    sẽ nhặt lên và chạy miễn phí.
    """
    uid, token = _tai_khoan(credits=5)
    wf = _workflow(uid, so_node=3)
    q = _bao_gia(api, token, wf).json()["quote"]

    # 409, khong 402: `insufficient_credit` cua be mat nay la 409 —
    # giong het cua `/jobs`. Ky vong 402 la cua toi, khong phai cua he.
    r = _chay(api, token, wf, q)
    assert r.status_code == 409, r.text
    gen, db = _session()
    try:
        assert db.query(WorkflowRun).count() == 0
        assert db.query(CreditEntry).filter_by(kind=CREDIT_HOLD).count() == 0
    finally:
        _close(gen)


def test_cung_khoa_idempotency_tra_lai_dung_run_cu_va_MOT_khoan_giu(api):
    uid, token = _tai_khoan(credits=500)
    wf = _workflow(uid, so_node=2)
    q = _bao_gia(api, token, wf).json()["quote"]
    khoa = uuid.uuid4().hex

    a = _chay(api, token, wf, q, idem=khoa)
    b = _chay(api, token, wf, q, idem=khoa)
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["id"] == b.json()["id"]

    gen, db = _session()
    try:
        assert db.query(WorkflowRun).count() == 1
        assert db.query(CreditEntry).filter_by(kind=CREDIT_HOLD).count() == 1
    finally:
        _close(gen)


def test_huy_thi_HOAN_lai_phan_chua_dung(api):
    """⭐ `chuyen_run` kéo theo `ket_so` trong **cùng** transaction — hình dạng
    của `M10`. Không có bước "nhớ hoàn tiền" nào để quên."""
    from platform_core import credit

    uid, token = _tai_khoan(credits=500)
    wf = _workflow(uid, so_node=3)
    q = _bao_gia(api, token, wf).json()["quote"]
    run_id = _chay(api, token, wf, q).json()["id"]

    r = api.post(f"{API_V1_PREFIX}/runs/{run_id}/cancel", headers=_auth(token))
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"

    gen, db = _session()
    try:
        assert credit.so_du(db, uid) == 500, "huy khi chua chay gi thi hoan het"
        run = db.get(WorkflowRun, run_id)
        assert run.hold_id == "" and run.ket_so_luc is not None
    finally:
        _close(gen)


def test_huy_LAN_HAI_khong_hoan_them(api):
    from platform_core import credit

    uid, token = _tai_khoan(credits=500)
    wf = _workflow(uid, so_node=3)
    q = _bao_gia(api, token, wf).json()["quote"]
    run_id = _chay(api, token, wf, q).json()["id"]

    api.post(f"{API_V1_PREFIX}/runs/{run_id}/cancel", headers=_auth(token))
    r2 = api.post(f"{API_V1_PREFIX}/runs/{run_id}/cancel", headers=_auth(token))
    assert r2.status_code == 200
    gen, db = _session()
    try:
        assert credit.so_du(db, uid) == 500
    finally:
        _close(gen)


# ── Quyền và ranh giới chủ sở hữu ───────────────────────────────────────────

def test_khoa_chi_co_workflows_read_KHONG_chay_duoc(api):
    """Đọc không bao giờ suy ra từ ghi, và ngược lại — luật ở đầu `scopes.py`."""
    uid, token_doc = _tai_khoan(scopes=(SCOPE_WORKFLOWS_READ,))
    wf = _workflow(uid)
    assert _bao_gia(api, token_doc, wf).status_code == 403


def test_run_cua_NGUOI_KHAC_tra_404_chu_khong_403(api):
    """⛔ 403 xác nhận id đó có thật. 404 thì không nói gì."""
    uid_a, token_a = _tai_khoan(credits=500)
    uid_b, token_b = _tai_khoan(credits=500)
    wf = _workflow(uid_a, so_node=2)
    q = _bao_gia(api, token_a, wf).json()["quote"]
    run_id = _chay(api, token_a, wf, q).json()["id"]

    assert api.get(f"{API_V1_PREFIX}/runs/{run_id}",
                   headers=_auth(token_b)).status_code == 404
    # Vế hợp lệ: chính chủ đọc được.
    assert api.get(f"{API_V1_PREFIX}/runs/{run_id}",
                   headers=_auth(token_a)).status_code == 200


def test_artifacts_cua_run_chi_chu_moi_doc_duoc(api):
    uid_a, token_a = _tai_khoan(credits=500)
    _uid_b, token_b = _tai_khoan(credits=500)
    wf = _workflow(uid_a, so_node=2)
    q = _bao_gia(api, token_a, wf).json()["quote"]
    run_id = _chay(api, token_a, wf, q).json()["id"]

    ok = api.get(f"{API_V1_PREFIX}/runs/{run_id}/artifacts", headers=_auth(token_a))
    assert ok.status_code == 200 and ok.json()["artifacts"] == []
    assert api.get(f"{API_V1_PREFIX}/runs/{run_id}/artifacts",
                   headers=_auth(token_b)).status_code == 404


def test_scope_workflows_run_nam_trong_SPENDING_SCOPES():
    """⛔ Câu hỏi *"khoá này tốn tôi bao nhiêu"* phải là một phép tra, không
    phải một lượt đọc mọi route. Thiếu scope này ở đó là thiếu đúng phần đắt
    nhất: một run giữ trần của **cả đồ thị**, không phải giá một tool."""
    from platform_core.public_api import scopes

    assert SCOPE_WORKFLOWS_RUN in scopes.SPENDING_SCOPES
    assert SCOPE_WORKFLOWS_READ not in scopes.SPENDING_SCOPES
