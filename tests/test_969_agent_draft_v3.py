"""Đợt 5.2 phần C — cửa nội bộ cho bản nháp Canvas **v3** (`WorkflowDraft`).

## Ba mệnh đề tệp này canh

1. **`revision` là khoá lạc quan thật**, không phải một bộ đếm trang trí: tab
   đến sau nhận `409` thay vì ghi đè âm thầm phần người kia vừa gõ.
2. **Ranh giới chủ sở hữu là `404`, không phải `403`** — `403` xác nhận id đó
   có thật.
3. **Xuất bản lại cùng nội dung không đẻ version thứ hai** — do
   `UNIQUE (workflow_id, graph_hash)` cưỡng chế, không do mã cẩn thận.

4. **Cửa chạy v3 CÓ tồn tại, và nó thật sự giữ đủ ba bảo vệ tiền.**

## ⚠️ Mệnh đề số 4 trước đây là một mệnh đề PHỦ ĐỊNH, và nó đã lỗi thời

Bản đầu của tệp này khẳng định: *"cửa v3 **không** có đường chạy — chạy một
workflow đi qua `/api/v1/workflows/{id}/runs`, nơi có báo giá đã ký,
`Idempotency-Key` và một khoản giữ chỗ"*.

Lý lẽ ấy **đúng lúc viết** và nó bảo vệ đúng thứ đáng bảo vệ. Nhưng thứ nó bảo
vệ là **ba bất biến**, không phải **một URL** — và kiến trúc V2 đã dời cả ba ra
khỏi `server/api/workflows.py` vào `platform_core/workflow/tao_run.py`, **cửa
DUY NHẤT tạo run** (API v1, Canvas v3 và trigger đều gọi đúng hàm đó). Kể từ
lúc ấy, mệnh đề phủ định không còn đo cái nó tưởng: nó cấm một **cửa**, trong
khi thứ phải cấm là một **đường vòng qua `tao_run`**. Giữ nguyên nó nghĩa là
bộ test đỏ vĩnh viễn trong khi tiền vẫn an toàn — và tệ hơn, nếu ai đó "sửa cho
xanh" bằng cách xoá bài, ta mất luôn chỗ duy nhất canh ba bất biến ở tầng này.

⇒ Mệnh đề được **đảo thành dương**, và mỗi vế được khẳng định bằng **hành vi đo
  được** qua HTTP trên app thật, không bằng việc đọc tên hàm trong mã:

| Bảo vệ | Đo bằng | Vế đối chứng |
|---|---|---|
| giữ chỗ credit | 201 ⇒ đúng **một** bút toán `CREDIT_HOLD` khoá theo `run.id` | thiếu credit ⇒ **402** và **không** run nào được tạo |
| idempotency | `tao_run(khoa)` hai lần ⇒ **một** run | cửa v3 cố ý **không** đọc `Idempotency-Key` (hai lần bấm = hai ý định); rào của nó là `MAX_RUN_DONG_THOI` ⇒ 429 |
| giá đã ký | hold = `version.estimated_max` **dù** thân request khai số khác | đổi bản publish ⇒ hold **đi theo** số mới |

🔴 Vế "giá không đến từ thân request" là **lỗi production vừa sửa 23/09** — nó
   ở lại đây dưới dạng bánh cóc, không phải trang trí.
"""
from __future__ import annotations

import pathlib
import re
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.models import Workflow, WorkflowDraft, WorkflowVersion


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'v3.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _do_thi(n: int = 3) -> dict:
    return {"version": 3, "goal": "g", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "edges": [],
                       "nodes": [{"id": f"n{i}", "type": "tool"}
                                 for i in range(n)]}]}


# ── 1. Khoá lạc quan ────────────────────────────────────────────────────────

def test_revision_lech_thi_XUNG_DOT_chu_khong_ghi_de(db):
    """🔴 Đây là bài đắt nhất ở đây. Không có nó, hai tab cùng mở thì tab đến
    sau **ghi đè im lặng** phần người kia vừa gõ — và không dấu vết nào."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(1), revision=0)
    db.commit()

    # Tab A ghi thành công, revision 1 -> 2.
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(2), revision=1)
    db.commit()

    # Tab B vẫn giữ revision 1 — phải bị chặn.
    with pytest.raises(dinh_nghia.XungDotRevision):
        dinh_nghia.luu_draft(db, wf.id, document=_do_thi(9), revision=1)
    db.rollback()

    assert len(db.get(WorkflowDraft, wf.id).document["pages"][0]["nodes"]) == 2


def test_revision_KHOP_thi_ghi_duoc(db):
    """⭐ Vế hợp lệ. Không có nó, một bản vá "luôn từ chối" cũng làm bài trên
    xanh — và không ai lưu được gì nữa."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(1), revision=0)
    db.commit()
    d = dinh_nghia.luu_draft(db, wf.id, document=_do_thi(5), revision=1)
    db.commit()
    assert d.revision == 2
    assert len(d.document["pages"][0]["nodes"]) == 5


# ── 2. Xuất bản ─────────────────────────────────────────────────────────────

def test_xuat_ban_LAI_cung_noi_dung_KHONG_de_version_thu_hai(db):
    """Ràng buộc CSDL, không phải mã cẩn thận: `UNIQUE (workflow_id, graph_hash)`
    khiến hai request song song cũng không lách được."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    g = _do_thi(3)
    a = dinh_nghia.xuat_ban(db, wf.id, g, created_by="u1", estimated_max=30)
    db.commit()
    b = dinh_nghia.xuat_ban(db, wf.id, dict(g), created_by="u1", estimated_max=30)
    db.commit()
    assert a.id == b.id
    assert db.query(WorkflowVersion).count() == 1


def test_xuat_ban_noi_dung_KHAC_thi_ra_version_moi(db):
    """Đối chứng: không có bài này, một bản vá *"luôn trả version cũ"* cũng làm
    bài trên xanh — và mọi lần publish sau đều không có tác dụng."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    a = dinh_nghia.xuat_ban(db, wf.id, _do_thi(3), created_by="u1")
    db.commit()
    b = dinh_nghia.xuat_ban(db, wf.id, _do_thi(4), created_by="u1")
    db.commit()
    assert a.id != b.id and db.query(WorkflowVersion).count() == 2


def test_tran_chi_phi_DONG_BANG_cung_graph(db):
    """⚠️ `23_24`: tính lại lúc chạy nghĩa là một lượt có thể vượt một trần mà
    người duyệt **chưa từng thấy con số ấy**."""
    from platform_core.workflow import bao_gia, dinh_nghia
    from platform_core.workflow.cong_cu import CongCu

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    cc = {"t.x": CongCu(ten="t.x", app_slug="t", job_type="t.x", type_version=1,
                        params_schema={}, side_effect="external",
                        idempotency_fields=(), tinh_gia=lambda p: 5)}
    g = {"schema": "ltt.workflow/3", "nodes": [
        {"id": f"n{i}", "type": "app.t.x", "params": {}, "thi_hanh": "job"}
        for i in range(3)], "edges": []}
    gia = bao_gia.bao_gia_do_thi(g, cong_cu=cc)
    ver = dinh_nghia.xuat_ban(db, wf.id, g, created_by="u1",
                              estimated_max=gia.toi_da)
    db.commit()
    assert ver.estimated_max == gia.toi_da > 0


# ── 3. Bề mặt: cửa chạy v3 CÓ tồn tại, và nó giữ đủ ba bảo vệ tiền ──────────

_MAT_KHAU = "Strong-pass-123"
_EMAIL = "v3-runs@example.com"


def _graph(n: int = 2) -> dict:
    """Đồ thị **đã biên dịch** (khác `_do_thi` — cái đó là tài liệu draft).

    `schema: ltt.workflow/3` là dấu hiệu `_ban_publish` đọc để chấp nhận một
    version cho quote/chạy; giá được khai TƯỜNG MINH ở nơi gọi `xuat_ban`, không
    phải một con số còn lại trong `params` của client.
    """
    return {"schema": "ltt.workflow/3", "edges": [],
            "nodes": [{"id": f"n{i}", "type": "tool"} for i in range(n)]}


class _Web:
    """App thật + một tài khoản đã đăng nhập. Mọi lời khẳng định về tiền bên
    dưới đi qua HTTP, không gọi thẳng `tao_run` — vì thứ cần chứng minh là
    **cửa mà người dùng gặp** có ba bảo vệ, không phải hàm bên dưới nó."""

    def __init__(self, client, csrf: str, user_id: str):
        self.client, self.csrf, self.user_id = client, csrf, user_id

    def phien(self):
        import platform_core.db as dbmod
        return next(dbmod.get_session())

    def nap(self, so: int) -> None:
        from platform_core import credit
        db = self.phien()
        try:
            credit.cap_tay(db, self.user_id, so, by="test")
            db.commit()
        finally:
            db.close()

    def wf_da_publish(self, *, tran: int, n: int = 2) -> str:
        from platform_core.workflow import dinh_nghia
        db = self.phien()
        try:
            wf = dinh_nghia.tao_workflow(db, owner_id=self.user_id, name="w")
            ver = dinh_nghia.xuat_ban(db, wf.id, _graph(n),
                                      created_by=self.user_id,
                                      estimated_max=tran)
            wf.published_version_id = ver.id
            db.commit()
            return wf.id
        finally:
            db.close()

    def publish_lai(self, wf_id: str, *, tran: int, n: int) -> None:
        """Đổi bản đang publish sang một version có giá KHÁC."""
        from platform_core.workflow import dinh_nghia
        db = self.phien()
        try:
            ver = dinh_nghia.xuat_ban(db, wf_id, _graph(n),
                                      created_by=self.user_id,
                                      estimated_max=tran)
            db.get(Workflow, wf_id).published_version_id = ver.id
            db.commit()
        finally:
            db.close()

    def chay(self, wf_id: str, *, body: dict | None = None,
             headers: dict | None = None, khoa: str | None = None):
        """POST cửa tạo run.

        ⭐ `khoa=None` ⇒ sinh một `Idempotency-Key` **mới cho mỗi lần gọi**.

        Cửa này đòi header ấy (`runs_v3._khoa_idempotency`). Một mặc định
        **cố định** sẽ làm mọi bài gọi `chay()` hai lần im lặng nhận lại đúng
        một run — và các bài đếm run sẽ đo nhầm đối tượng mà vẫn xanh.

        Truyền `khoa=""` để **bỏ hẳn** header (bài đo mệnh đề "thiếu ⇒ 400"),
        hoặc một chuỗi cụ thể để hai lần gọi dùng CHUNG một khoá.
        """
        h = {"X-CSRF-Token": self.csrf}
        if khoa is None:
            khoa = f"tk-{uuid.uuid4()}"
        if khoa:
            h["Idempotency-Key"] = khoa
        h.update(headers or {})
        return self.client.post(f"/agent/api/v3/workflows/{wf_id}/runs",
                                json=body if body is not None else {},
                                headers=h)


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'v3web.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.users import tao_nguoi_dung
    db = next(dbmod.get_session())
    user_id = tao_nguoi_dung(db, email=_EMAIL, password=_MAT_KHAU,
                             is_verified=True).id
    db.commit()
    db.close()

    cfg = tmp_path / "config.json"
    cfg.write_text("{}", encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "test-969-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    with TestClient(app, base_url="https://testserver",
                    follow_redirects=True) as client:
        trang = client.get("/login")
        tok = re.search(r'name="csrf_token" value="([^"]+)"', trang.text)
        assert tok, "khong lay duoc csrf o /login"
        assert client.post("/login", data={
            "username": _EMAIL, "password": _MAT_KHAU,
            "csrf_token": tok.group(1), "next": "/agent/canvas"},
        ).status_code == 200
        # ⭐ Token CSRF gắn theo PHIÊN (`server/auth/csrf.py`), và phiên xoay
        #    lúc đăng nhập — nên phải đọc lại SAU khi vào, không dùng token của
        #    trang `/login`. `/agent/canvas` là trang duy nhất của app in nó ra.
        canvas = client.get("/agent/canvas")
        csrf = re.search(r'data-csrf-token="([^"]+)"', canvas.text)
        assert csrf, f"/agent/canvas khong in csrf (status {canvas.status_code})"
        yield _Web(client, csrf.group(1), user_id)
    dbmod.reset_engine()


def test_cua_chay_v3_CO_TON_TAI_tren_bang_dinh_tuyen():
    """Vế "có tồn tại" của mệnh đề đã đảo — đo trên **bảng định tuyến**, thứ
    người dùng thật gặp, không phải trên tên tệp."""
    from apps.agent.routes import router

    v3 = {(sorted(r.methods)[0], r.path) for r in router.routes
          if "/api/v3/" in getattr(r, "path", "")}
    assert v3, "khong route v3 nao duoc dang ky — nghi phep kiem quet nham cho"
    assert ("POST", "/api/v3/workflows/{workflow_id}/runs") in v3


# ── Bảo vệ 1: giữ chỗ credit ────────────────────────────────────────────────

def test_bao_ve_1_tao_run_GIU_CHO_dung_MOT_khoan_credit(web):
    """201 ⇒ phải có đúng **một** bút toán `CREDIT_HOLD`, khoá theo `run.id`.

    Không có bài này, một cửa "tạo run rồi thôi" cũng trả 201 — và mọi lượt
    chạy đều miễn phí cho tới khi ai đó đọc sổ.
    """
    from platform_core.models import CREDIT_HOLD, CreditEntry, WorkflowRun

    web.nap(500)
    wf = web.wf_da_publish(tran=30)

    r = web.chay(wf)
    assert r.status_code == 201, r.text

    db = web.phien()
    try:
        runs = db.query(WorkflowRun).all()
        assert len(runs) == 1
        giu = db.query(CreditEntry).filter_by(kind=CREDIT_HOLD).all()
        assert len(giu) == 1, f"phai co DUNG MOT khoan giu, co {len(giu)}"
        assert giu[0].job_id == runs[0].id
        assert giu[0].delta == -30
    finally:
        db.close()


def test_bao_ve_1_DOI_CHUNG_thieu_credit_thi_402_va_KHONG_co_run(web):
    """🔑 Vế đối chứng. Không có nó, một cửa **không hề gọi** đường tiền cũng
    làm bài trên xanh — và cửa ấy tạo run cho người không còn đồng nào.

    Đồng thời canh luôn *"không run mồ côi"*: 402 rồi mà còn một `WorkflowRun`
    nằm lại là một lượt chạy **không ai giữ tiền cho nó**.
    """
    from platform_core.models import CREDIT_HOLD, CreditEntry, WorkflowRun

    web.nap(5)
    wf = web.wf_da_publish(tran=30)

    r = web.chay(wf)
    assert r.status_code == 402, r.text
    assert r.json()["detail"]["ma"] == "thieu_credit"

    db = web.phien()
    try:
        assert db.query(WorkflowRun).count() == 0, "run mo coi sau 402"
        assert db.query(CreditEntry).filter_by(kind=CREDIT_HOLD).count() == 0
    finally:
        db.close()


# ── Bảo vệ 2: idempotency ───────────────────────────────────────────────────

def test_bao_ve_2_cung_KHOA_hai_lan_chi_ra_MOT_run(db):
    """Bất biến sống ở `tao_run`, cửa DUY NHẤT tạo run — nên đo ở đó.

    Với một khoá, lần gọi thứ hai trả **đúng run cũ** và `moi=False`; không có
    run thứ hai nào được ghi.
    """
    from platform_core.models import WorkflowRun
    from platform_core.workflow import dinh_nghia, tao_run

    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="idem@example.com", password=_MAT_KHAU,
                       is_verified=True)
    wf = dinh_nghia.tao_workflow(db, owner_id=u.id, name="w")
    ver = dinh_nghia.xuat_ban(db, wf.id, _graph(2), created_by=u.id,
                              estimated_max=0)
    wf.published_version_id = ver.id
    db.flush()

    a, moi_a = tao_run.tao_run(db, workflow=wf, owner_id=u.id,
                               trigger_kind="api", idempotency_key="k-1")
    db.commit()
    b, moi_b = tao_run.tao_run(db, workflow=wf, owner_id=u.id,
                               trigger_kind="api", idempotency_key="k-1")
    db.commit()

    assert (moi_a, moi_b) == (True, False)
    assert a.id == b.id
    assert db.query(WorkflowRun).count() == 1


def test_bao_ve_2_khoa_dung_lai_cho_workflow_KHAC_thi_NEM(db):
    """🔑 Vế đối chứng của bài trên: một cửa *"khoá nào cũng trả run đầu tiên"*
    cũng làm nó xanh — và lượt thứ hai của khách sẽ im lặng trả nhầm run."""
    from platform_core.users import tao_nguoi_dung
    from platform_core.workflow import dinh_nghia, tao_run

    u = tao_nguoi_dung(db, email="idem2@example.com", password=_MAT_KHAU,
                       is_verified=True)
    wfs = []
    for _ in range(2):
        wf = dinh_nghia.tao_workflow(db, owner_id=u.id, name="w")
        ver = dinh_nghia.xuat_ban(db, wf.id, _graph(len(wfs) + 2),
                                  created_by=u.id, estimated_max=0)
        wf.published_version_id = ver.id
        wfs.append(wf)
    db.flush()

    tao_run.tao_run(db, workflow=wfs[0], owner_id=u.id, trigger_kind="api",
                    idempotency_key="k-2")
    db.commit()
    with pytest.raises(tao_run.TrungKhoaKhacWorkflow):
        tao_run.tao_run(db, workflow=wfs[1], owner_id=u.id,
                        trigger_kind="api", idempotency_key="k-2")
    db.rollback()


def test_bao_ve_2_cua_v3_DOI_Idempotency_Key_va_THI_HANH_no(web):
    """⭐ Đảo mệnh đề, 23/09/2026 — bài này trước đây chốt rằng cửa v3 **cố ý
    bỏ qua** `Idempotency-Key`, với lập luận *"hai lần bấm là hai ý định"*.

    🔴 Lập luận ấy sai ở chỗ nó đọc **thứ đại diện**: cái đo được không phải
       "ý định" mà là **bút toán**. Đo qua HTTP thật cho thấy bấm hai lần ⇒ hai
       run, hai khoản `hold`, hai lần trừ tiền — và người dùng bấm lần hai vì
       lần một **trông như** chưa ăn, không phải vì họ muốn trả tiền hai lần.

    ⇒ Cửa nay đòi khoá (`runs_v3._khoa_idempotency`). Ba mệnh đề dương:

        thieu khoa          -> 400 `thieu_idempotency_key`, KHONG co run
        cung khoa hai lan   -> MOT run, MOT but toan `hold`  (201 roi 200)
        khoa khac nhau      -> HAI run

    ⭐ `201` rồi `200`: mã trạng thái tự nói lần nào **tạo** và lần nào **phát
       lại**. Nếu cả hai cùng `201` thì một cửa tạo hai run cũng khai y hệt một
       cửa phát lại, và bài này sẽ phải đi đếm bảng mới biết sự khác nhau.

    Mệnh đề thứ ba là vế đối chứng bắt buộc: thiếu nó, một cửa trả lại run đầu
    tiên cho **mọi** khoá cũng xanh — và khách sẽ không bao giờ chạy được lần
    thứ hai.
    """
    from platform_core.models import CREDIT_HOLD, CreditEntry, WorkflowRun

    web.nap(500)
    wf = web.wf_da_publish(tran=10)

    # 1. Thiếu khoá ⇒ 400, và KHÔNG được ghi run nào.
    thieu = web.chay(wf, khoa="")
    assert thieu.status_code == 400, thieu.text
    assert thieu.json()["detail"]["ma"] == "thieu_idempotency_key"
    db = web.phien()
    try:
        assert db.query(WorkflowRun).count() == 0
    finally:
        db.close()

    # 2. Cùng khoá hai lần ⇒ MỘT run, MỘT bút toán giữ chỗ.
    a = web.chay(wf, khoa="nguoi-dung-bam-hai-lan")
    b = web.chay(wf, khoa="nguoi-dung-bam-hai-lan")
    assert (a.status_code, b.status_code) == (201, 200), (a.text, b.text)
    assert a.json()["id"] == b.json()["id"]
    db = web.phien()
    try:
        assert db.query(WorkflowRun).count() == 1
        assert db.query(CreditEntry).filter_by(kind=CREDIT_HOLD).count() == 1
    finally:
        db.close()

    # 3. 🔑 Đối chứng: khoá KHÁC ⇒ một run thật sự mới.
    c = web.chay(wf, khoa="lan-bam-thu-hai-that-su")
    assert c.status_code == 201, c.text
    assert c.json()["id"] != a.json()["id"]
    db = web.phien()
    try:
        assert db.query(WorkflowRun).count() == 2
        assert db.query(CreditEntry).filter_by(kind=CREDIT_HOLD).count() == 2
    finally:
        db.close()


def test_bao_ve_2_TRAN_run_dong_thoi_chan_bam_lien_tay(web):
    """Rào thật của cửa v3: run thứ `MAX_RUN_DONG_THOI + 1` nhận **429**, và
    không có run nào được ghi thêm."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow.tao_run import MAX_RUN_DONG_THOI

    web.nap(1000)
    wf = web.wf_da_publish(tran=10)

    for i in range(MAX_RUN_DONG_THOI):
        assert web.chay(wf).status_code == 201, f"run thu {i + 1}"
    r = web.chay(wf)
    assert r.status_code == 429, r.text
    assert r.json()["detail"]["ma"] == "qua_han_muc"

    db = web.phien()
    try:
        assert db.query(WorkflowRun).count() == MAX_RUN_DONG_THOI
    finally:
        db.close()


# ── Bảo vệ 3: giá đến từ bản ĐÃ PUBLISH ─────────────────────────────────────

def test_bao_ve_3_gia_den_tu_ban_DA_PUBLISH_khong_tu_than_request(web):
    """🔴 Bánh cóc cho lỗi production sửa 23/09.

    Thân request khai mọi tên gọi mà một client có thể thử —
    `estimated_max`, `credit_max`, `budget_max_credit` — với một con số to.
    Trần và khoản giữ vẫn phải là con số của **version đã publish**.
    """
    from platform_core.models import CREDIT_HOLD, CreditEntry, WorkflowRun

    web.nap(500)
    wf = web.wf_da_publish(tran=30)

    r = web.chay(wf, body={"estimated_max": 9999, "credit_max": 9999,
                           "budget_max_credit": 9999,
                           "inputs": {"gia": 9999}})
    assert r.status_code == 201, r.text
    assert r.json()["credit_max"] == 30

    db = web.phien()
    try:
        assert db.query(WorkflowRun).one().estimated_max == 30
        assert db.query(CreditEntry).filter_by(
            kind=CREDIT_HOLD).one().delta == -30
    finally:
        db.close()


def test_bao_ve_3_DOI_CHUNG_doi_ban_publish_thi_gia_DI_THEO(web):
    """🔑 Vế đối chứng. Không có nó, một cửa **hardcode 30** hay một cửa bỏ
    qua giá hoàn toàn cũng làm bài trên xanh."""
    from platform_core.models import CREDIT_HOLD, CreditEntry

    web.nap(500)
    wf = web.wf_da_publish(tran=30)
    web.publish_lai(wf, tran=70, n=5)

    r = web.chay(wf, body={"estimated_max": 1})
    assert r.status_code == 201, r.text
    assert r.json()["credit_max"] == 70

    db = web.phien()
    try:
        assert db.query(CreditEntry).filter_by(
            kind=CREDIT_HOLD).one().delta == -70
    finally:
        db.close()


def test_MUOI_MOT_route_v3_deu_duoc_dang_ky():
    """⚠️ Tên bài mang con số, nên con số phải đúng: cửa v3 nay có **mười một**
    route.

    Lịch sử con số: năm → **tám** (ba route `runs` ra đời cùng kiến trúc V2)
    → **mười** (plan 02 thêm `/palette` và `/luat-noi-day`, spec §13.1)
    → **mười một** (plan wf-v2 P2 Task 8 thêm `/bieu-thuc/goi-y`, spec §6.2).

    ⭐ Đây là bài đã bắt plan 02: Task 8 thêm hai route mà không ai sửa con số,
       và bộ test NHẮM của plan (12 tệp `test_175x`) **không phủ** tệp này —
       chỉ lượt chạy lan-toả ở Task 16 mới thấy.
    """
    from apps.agent.routes import router

    co = {(sorted(r.methods)[0], r.path) for r in router.routes
          if "/api/v3/" in getattr(r, "path", "")}
    assert co == {
        ("GET", "/api/v3/workflows"),
        ("POST", "/api/v3/workflows"),
        ("GET", "/api/v3/workflows/{workflow_id}"),
        ("PUT", "/api/v3/workflows/{workflow_id}"),
        ("POST", "/api/v3/workflows/{workflow_id}/publish"),
        ("POST", "/api/v3/workflows/{workflow_id}/runs"),
        ("GET", "/api/v3/runs/{run_id}"),
        ("POST", "/api/v3/runs/{run_id}/cancel"),
        ("GET", "/api/v3/palette"),
        ("GET", "/api/v3/luat-noi-day"),
        ("POST", "/api/v3/workflows/{workflow_id}/bieu-thuc/goi-y"),
    }
    assert len(co) == 11


def test_tai_lieu_rong_dung_HINH_DANG_ma_M1_sinh_ra():
    """⭐ Một bản di trú và một bản tạo mới không được khác nhau ở chỗ người đọc
    phải nhớ. Cả hai đều là `version 3` + một trang `p1`."""
    from apps.agent.routes.drafts_v3 import _tai_lieu_rong

    d = _tai_lieu_rong()
    assert d["version"] == 3
    assert d["active_page_id"] == d["pages"][0]["id"] == "p1"
    assert set(d) == {"version", "goal", "budget_max_credit",
                      "active_page_id", "pages"}


def test_cua_v3_KHONG_dung_bang_cua_Canvas_v2(db):
    """`AgentWorkflow` và `Workflow` là hai bảng khác nhau. Ghi nhầm bảng sẽ làm
    bản nháp v3 hiện ra ở trình soạn v2 dưới dạng một đồ thị rỗng."""
    from platform_core.models import AgentWorkflow
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(2), revision=0)
    db.commit()
    assert db.query(Workflow).count() == 1
    assert db.query(WorkflowDraft).count() == 1
    assert db.query(AgentWorkflow).count() == 0


# ── 4. Bề mặt HTML: không template nào trỏ tới một đường ĐÃ CHẾT ────────────
#
# 🔴 Vì sao bài này tồn tại: sau khi luồng chạy v1 bị gỡ (§17.4), `agent.html`
#    vẫn còn `<form action="/agent/plan">`. Route đó không còn trong bảng định
#    tuyến, nên người dùng bấm nút "Lập kế hoạch và xem giá" nhận **405**. Bộ
#    test lúc ấy xanh: `test_1726` chốt rằng ROUTE đã biến mất, nhưng không ai
#    hỏi các TEMPLATE có biết điều đó chưa.
#
# ⭐ Đo bằng bảng định tuyến THẬT, không đối chiếu với danh sách `CHET` của
#    `test_1726`. Một danh sách chép tay chỉ bắt được những đường ta nhớ đã gỡ;
#    "không khớp route nào đang sống" bắt được cả những đường ta quên.

_TEMPLATES = (pathlib.Path(__file__).resolve().parent.parent
              / "apps" / "agent" / "templates")
#: Mọi thuộc tính mang một URL mà trình duyệt (hoặc htmx) sẽ thật sự gọi.
_THUOC_TINH = re.compile(
    r'\b(?:action|href|hx-get|hx-post|hx-put|hx-patch|hx-delete)="([^"]*)"')
#: Số template tối thiểu phải đọc được — vế đối chứng cho "quét nhầm chỗ".
_TOI_THIEU_TEP = 2


def _duong_song() -> list[re.Pattern]:
    """Bảng định tuyến thật của app, đã gắn `route_prefix`, thành regex."""
    from apps.agent.manifest import MANIFEST
    from apps.agent.routes import router

    ra = []
    for r in router.routes:
        p = MANIFEST.route_prefix + getattr(r, "path", "")
        ra.append(re.compile("^" + re.sub(r"\\{[^/]*?\\}", "[^/]+",
                                          re.escape(p)) + "/?$"))
    return ra


def _chuan_hoa(url: str) -> str:
    """Bỏ biểu thức Jinja và query/fragment — còn lại là hình dạng đường dẫn."""
    url = re.sub(r"\{\{.*?\}\}", "X", url)
    return url.split("?")[0].split("#")[0]


def _url_trong_template() -> list[tuple[str, str]]:
    ra = []
    for tep in sorted(_TEMPLATES.glob("*.html")):
        for url in _THUOC_TINH.findall(tep.read_text(encoding="utf-8")):
            if url.startswith("/agent"):
                ra.append((tep.name, url))
    return ra


def test_moi_url_trong_template_agent_deu_con_song():
    """⛔ Một `action=`/`href=` trỏ vào app mà không khớp route nào đang sống
    là một nút bấm ra 404/405 — hỏng hóc thật, trên giao diện thật."""
    song = _duong_song()
    chet = [(tep, url) for tep, url in _url_trong_template()
            if not any(p.match(_chuan_hoa(url)) for p in song)]
    assert not chet, f"template tro toi duong da chet: {chet}"


def test_DOI_CHUNG_phep_quet_that_su_doc_duoc_template_va_url():
    """🔑 Không có vế này, một `glob` sai thư mục hay một regex hỏng cũng làm
    bài trên xanh — và nó sẽ xanh **mãi mãi**, kể cả khi mọi nút đều chết."""
    tep = {t for t, _ in _url_trong_template()}
    assert len(list(_TEMPLATES.glob("*.html"))) >= _TOI_THIEU_TEP
    assert tep, "khong doc duoc URL nao trong template app agent"


@pytest.mark.parametrize("url,song", [
    ("/agent/canvas", True),
    ("/agent", True),
    ("/agent/api/v3/runs/{{ run.id }}/cancel", True),
    # Ba đường đã chết (`test_1726::CHET`) — bộ dò PHẢI bắt được chúng.
    ("/agent/plan", False),
    ("/agent/runs/{{ run.id }}/tick", False),
    ("/agent/api/runs/{{ run.id }}/approve", False),
])
def test_DOI_CHUNG_bo_do_phan_biet_duoc_duong_song_va_duong_chet(url, song):
    """🔑 Tiêm cả hai chiều. Một bộ dò *"luôn nói còn sống"* làm bài trên xanh;
    một bộ dò *"luôn nói đã chết"* thì đỏ oan mọi nút còn dùng được."""
    khop = any(p.match(_chuan_hoa(url)) for p in _duong_song())
    assert khop is song, url
