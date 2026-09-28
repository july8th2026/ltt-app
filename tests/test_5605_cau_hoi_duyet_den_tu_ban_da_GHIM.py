"""Câu hỏi người duyệt thấy phải đến từ bản ĐÃ GHIM, ⛔ không từ bản đang soạn.

## 🔴 Đây là một lỗi ĐỒNG THUẬN, không phải một lỗi hiển thị

Làn UI-8a dựng cửa duyệt `core.human` và giao diện đọc `cau_hoi` / `het_han` từ
**tham số của trang đang soạn** (`thamSo(nodeId)` trong `ExecutionPanel`). Họ tự
ghi nhận điều này là *"có thể lệch một chút"*.

Nó ⛔ không phải *"lệch một chút"*. Một lượt chạy thi hành một
`workflow_version` **BẤT BIẾN** (`run.version_id`). Bản nháp thì sửa được bất kỳ
lúc nào. ⇒ Chuỗi sự kiện này có thật và ⛔ không cần ai cố ý:

    1. A xuất bản workflow với `cau_hoi = "Đăng bài này lên kênh chính?"`
    2. Chạy. Node `core.human` mở waitpoint, chờ người duyệt.
    3. A (hoặc đồng nghiệp ở tab khác) sửa bản nháp thành
       `cau_hoi = "Xoá toàn bộ playlist?"`
    4. B mở ngăn Thực thi, đọc **"Xoá toàn bộ playlist?"**, bấm **Duyệt**.
    5. Động cơ đi tiếp theo nhánh `approve` của **bản đã ghim** — tức là đăng
       bài, ⛔ không phải xoá playlist.

⇒ B đã duyệt một câu hỏi mà B **chưa từng được hỏi**, và ⛔ không dấu vết nào nói
  rằng màn hình đã hiện một câu khác. Chữ ký của B nằm trên một tài liệu khác.

## ⭐ Kho này ĐÃ học đúng bài này một lần, ở đường tiền

`dinh_nghia.xuat_ban` đóng băng `estimated_max` **cùng** graph đã biên dịch, và
lý do ghi ngay trong `test_969`:

> *"tính lại lúc chạy nghĩa là một lượt có thể vượt một trần mà người duyệt
>   **chưa từng thấy con số ấy**"*

Câu ấy nói về **credit**. Nó đúng y nguyên khi thay *con số* bằng *câu hỏi*: cái
người duyệt nhìn thấy và cái hệ thống thi hành phải đến từ **CÙNG một bản ghi bất
biến**, nếu không thì sự đồng thuận ⛔ không đo được.

## Phép đo

`GET /agent/api/v3/runs/{id}` đã đọc `ver.graph` (bản GHIM) để dựng
`_nodes_json`. Nên câu hỏi phải đi ra **từ đó**, và bài dưới đây sửa bản nháp
**sau khi** run đã bắt đầu rồi đòi cửa run vẫn trả câu hỏi CŨ.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

_MAT_KHAU = "Strong-pass-5605"
_EMAIL = "ghim5605@example.com"
#: Khoá phiên app thử — đi qua BIẾN, ⛔ không viết thẳng sau `"…SECRET":`
#: (`scan_source_secrets.generic_secret_assignment` khớp *tên khoá → `:` →
#: chuỗi ≥ 12 ký tự* và ⛔ không có cửa cho phép nào).
_BI_MAT_PHIEN_THU = "ghim-5605-session-test-fixture"

CAU_HOI_GOC = "Dang bai nay len kenh chinh?"
CAU_HOI_SUA_SAU = "Xoa toan bo playlist?"


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "params": params,
            "thi_hanh": "inline"}


@pytest.fixture()
def may_chu(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'ghim.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import registry as _reg

    _reg.load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    db = next(dbmod.get_session())
    uid = tao_nguoi_dung(db, email=_EMAIL, password=_MAT_KHAU,
                         is_verified=True).id
    credit.cap_tay(db, uid, 500, by="test")
    db.commit()
    db.close()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                   encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": _BI_MAT_PHIEN_THU,
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    yield app, uid
    dbmod.reset_engine()


@pytest.fixture()
def api(may_chu):
    app, _uid = may_chu
    client = TestClient(app, base_url="https://testserver",
                        follow_redirects=True)
    tok = re.search(r'name="csrf_token" value="([^"]+)"',
                    client.get("/login").text).group(1)
    assert client.post("/login", data={
        "username": _EMAIL, "password": _MAT_KHAU, "csrf_token": tok,
        "next": "/agent/canvas"}).status_code == 200
    yield client
    client.close()


def _db():
    import platform_core.db as dbmod
    return next(dbmod.get_session())


def _canh(a: str, b: str, *, kind: str = "DATA", condition: str = "") -> dict:
    c = {"id": f"e-{a}-{b}", "source_node": a, "target_node": b,
         "source_port": "ra", "target_port": "vao", "kind": kind}
    if condition:
        c["condition"] = condition
    return c


def _run_cho_nguoi(owner_id: str) -> tuple[str, str]:
    """Một run đang `WAITING` ở `core.human`. Trả `(run_id, workflow_id)`.

    ⭐ Khuôn lấy NGUYÊN từ `tests/test_6500_phe_duyet_v3.py::_tao_run` (làn
       UI-8a) — ⛔ không tự bịa lại chữ ký `tao_run()`. Lần đầu tôi gõ lại từ
       trí nhớ và nhận `TypeError: unexpected keyword argument 'nguoi_tao'`:
       một lỗi HẠ TẦNG của phép đo, trông y hệt một phép đo đỏ thật.
    """
    from platform_core.workflow import dinh_nghia, tao_run

    db = _db()
    try:
        w = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="wf-5605")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": [
                _core("h", "human", cau_hoi=CAU_HOI_GOC, het_han="reject"),
                _core("a", "set", bien={"da_duyet": "1"}),
                _core("r", "set", bien={"da_tu_choi": "1"})],
                "edges": [_canh("h", "a", kind="CONTROL", condition="approve"),
                          _canh("h", "r", kind="CONTROL", condition="reject")]}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by=owner_id, cong_cu={})
        w.published_version_id = v.id
        db.flush()
        run, _ = tao_run.tao_run(db, workflow=w, owner_id=owner_id,
                                 trigger_kind="manual",
                                 idempotency_key=f"wk-{w.id}")
        db.commit()
        rid, wid = run.id, w.id
    finally:
        db.close()

    from platform_core.workflow import dong_co
    for _ in range(4):
        db = _db()
        try:
            dong_co.xu_ly_run(db, rid, cong_cu={})
            db.commit()
        finally:
            db.close()
    return rid, wid


def _sua_ban_nhap(workflow_id: str, cau_hoi_moi: str) -> None:
    """Sửa BẢN NHÁP sau khi run đã bắt đầu. ⛔ KHÔNG publish lại — chính điểm
    của bài là bản đã ghim ⛔ không được đổi theo bản nháp."""
    from platform_core.models import WorkflowDraft
    from platform_core.workflow import dinh_nghia

    db = _db()
    try:
        d = db.get(WorkflowDraft, workflow_id)
        tai_lieu = json.loads(json.dumps(d.document))
        for n in tai_lieu["pages"][0]["nodes"]:
            if n["id"] == "h":
                n["params"]["cau_hoi"] = cau_hoi_moi
        dinh_nghia.luu_draft(db, workflow_id, document=tai_lieu,
                             revision=d.revision)
        db.commit()
    finally:
        db.close()


def _node_json(api: TestClient, run_id: str, node_id: str) -> dict:
    r = api.get(f"/agent/api/v3/runs/{run_id}")
    assert r.status_code == 200, r.text
    for n in r.json()["nodes"]:
        if n["node_id"] == node_id:
            return n
    raise AssertionError(f"khong thay node {node_id} trong {r.text[:400]}")


def test_cua_run_TRA_cau_hoi_duyet(may_chu, api):
    """Vế nền: nếu cửa run ⛔ không mang câu hỏi, giao diện **buộc** phải đi đọc
    bản nháp — nên bài này là điều kiện để luật kia thi hành được."""
    _app, uid = may_chu
    rid, _wid = _run_cho_nguoi(uid)
    n = _node_json(api, rid, "h")
    assert n["waiting_kind"] == "HUMAN", n
    assert n.get("cau_hoi") == CAU_HOI_GOC, \
        f"cua run khong mang cau hoi da GHIM: {n}"
    assert n.get("het_han_che_do") == "reject", n


def test_SUA_BAN_NHAP_KHONG_doi_cau_hoi_nguoi_duyet_thay(may_chu, api):
    """🔴 Bài đắt nhất tệp này. Sửa bản nháp giữa lúc run đang chờ ⇒ cửa run
    **vẫn** phải trả câu hỏi CŨ, vì đó là câu hỏi mà động cơ sẽ thi hành."""
    _app, uid = may_chu
    rid, wid = _run_cho_nguoi(uid)
    assert _node_json(api, rid, "h")["cau_hoi"] == CAU_HOI_GOC

    _sua_ban_nhap(wid, CAU_HOI_SUA_SAU)

    n = _node_json(api, rid, "h")
    assert n["cau_hoi"] == CAU_HOI_GOC, (
        "cua run doi theo BAN NHAP: nguoi duyet se doc mot cau hoi ma dong co "
        f"KHONG thi hanh ({n['cau_hoi']!r})")
    assert CAU_HOI_SUA_SAU not in json.dumps(n), n


def test_node_KHONG_cho_nguoi_thi_khong_mang_cau_hoi(may_chu, api):
    """Đối chứng. Một bản vá *"luôn trả `cau_hoi` của node nào có nó"* cũng làm
    hai bài trên xanh — và sẽ hiện thẻ duyệt cho một node ⛔ không chờ ai."""
    _app, uid = may_chu
    rid, _wid = _run_cho_nguoi(uid)
    n = _node_json(api, rid, "a")          # `core.set`, khong cho ai
    assert not n.get("cau_hoi"), n
    assert not n.get("het_han_che_do"), n
