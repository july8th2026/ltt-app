"""Goi y cho trinh soan bieu thuc §6 — `/bieu-thuc/goi-y` (P2 Task 8).

## Ba menh de tep nay canh

1. **Danh sach SINH TU NGUON.** Bang ham cua goi y phai la `BANG_HAM`, khong
   phai mot ban chep. Phep kiem do bang cach **lam lech nguon** (bo mot ham ra
   khoi `BANG_HAM`) va doi goi y lech theo. Mot bang chep tay se xanh o day —
   nen phep kiem viet theo kieu TIEM LOI chu khong theo kieu so voi mot danh
   sach thu hai (mot danh sach thu hai cung la mot ban chep).

2. **Chi goi y thu DUNG DUOC o vi tri do** — CA HAI CHIEU:
   - node **khong phai to tien** ⇒ KHONG duoc co trong goi y;
   - node **to tien hop le** ⇒ PHAI co.
   ⚠️ Thieu ve thu hai thi mot ban tra danh sach RONG cung xanh.

3. **Mot luat to tien, khong hai.** Moi goi y `nodes.…` duoc dua NGUOC lai
   dung cong publish (`bien_dich.bien_dich`): goi y phai qua duoc, va mot node
   KHONG duoc goi y phai bi cong do tu choi. Hai chieu ay la bang chung rang
   goi y HOI LAI `bien_dich` chu khong cai lai luat lan hai.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from platform_core.workflow import bien_dich, chinh_sach, goi_y
from platform_core.workflow.cong_cu import CongCu
from platform_core.workflow.ham_bieu_thuc import BANG_HAM


def _cc(ten, returns):
    return CongCu(ten=ten, app_slug="app_" + ten.split(".")[0],
                  job_type=ten + ".job", type_version=2, params_schema={},
                  side_effect="external", idempotency_fields=(),
                  tinh_gia=lambda p: 1, returns=dict(returns))


CC = {"text.chat": _cc("text.chat", {"text": "text"}),
      "image.generate": _cc("image.generate",
                            {"image_keys": "image[]", "prompt": "text"})}


def _node(nid, tool, params=None):
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": tool, "params": params or {}}}


def _canh(eid, a, b):
    return {"id": eid, "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": "DATA"}


#: a -> b -> c  ·  `d` roi, KHONG phai to tien cua ai.
DOC = {"version": 3, "pages": [{"id": "p1", "edges": [
    _canh("e1", "a", "b"), _canh("e2", "b", "c")], "nodes": [
        _node("a", "text.chat"), _node("b", "image.generate"),
        _node("c", "text.chat"), _node("d", "text.chat")]}]}


def _duong(ket_qua, loai=None):
    return {m["duong"] for m in ket_qua["muc"]
            if loai is None or m["loai"] == loai}


def _thay_params(doc, node_id, params):
    ra = json.loads(json.dumps(doc))
    for n in ra["pages"][0]["nodes"]:
        if n["id"] == node_id:
            n["data"]["params"] = params
    return ra


# ── 1. Bang ham sinh tu `BANG_HAM` ────────────────────────────────────────

def test_bang_ham_dung_BANG_HAM_ca_hai_chieu():
    ten = {m["ten"] for m in goi_y.goi_y(DOC, "c", cong_cu=CC)["ham"]}
    assert ten == set(BANG_HAM)


def test_bo_mot_ham_khoi_nguon_thi_goi_y_MAT_ham_do(monkeypatch):
    """🔑 TIEM LOI: lam lech NGUON, doi goi y lech theo.

    Mot bang chep tay van tra `upper` sau khi `BANG_HAM` mat no ⇒ do.
    """
    import platform_core.workflow.ham_bieu_thuc as hbt
    monkeypatch.setattr(hbt, "NHOM_HAM",
                        {n: {k: v for k, v in b.items() if k != "upper"}
                         for n, b in hbt.NHOM_HAM.items()})
    monkeypatch.setattr(hbt, "BANG_HAM",
                        {k: v for k, v in hbt.BANG_HAM.items()
                         if k != "upper"})
    ten = {m["ten"] for m in goi_y.goi_y(DOC, "c", cong_cu=CC)["ham"]}
    assert "upper" not in ten
    assert "lower" in ten          # doi chung: khong phai ca bang bien mat


def test_chu_ky_ham_doc_tu_chu_ky_PYTHON_khong_go_tay():
    ham = {m["ten"]: m["chu_ky"]
           for m in goi_y.goi_y(DOC, "c", cong_cu=CC)["ham"]}
    # Ten tham so la ten TIENG VIET trong `ham_bieu_thuc.py`; tham so tuy chon
    # nam trong ngoac vuong; `*args` mang dau `…`. Mot bang chep tay khong
    # biet nhung ten nay.
    assert ham["upper"] == "upper(chuoi)"
    assert ham["substring"].startswith("substring(chuoi, bat_dau, [")
    assert ham["coalesce"] == "coalesce(…dau_vao)"


# ── 2 + 3. To tien: ca hai chieu, va CUNG luat voi cong publish ───────────

def test_goi_y_CO_node_to_tien_va_KHONG_co_node_ngoai():
    duong = _duong(goi_y.goi_y(DOC, "c", cong_cu=CC), "cong")
    assert "nodes.a.output.text" in duong             # ⭐ ve KHANG DINH
    assert "nodes.b.output.image_keys" in duong
    assert "nodes.b.output.prompt" in duong
    assert not [d for d in duong if d.startswith("nodes.d.")]   # khong to tien
    assert not [d for d in duong if d.startswith("nodes.c.")]   # chinh no


def test_cong_KHONG_co_trong_registry_thi_khong_duoc_goi_y():
    duong = _duong(goi_y.goi_y(DOC, "c", cong_cu=CC), "cong")
    assert "nodes.a.output.image_keys" not in duong   # `text.chat` khong co
    assert {d for d in duong if d.startswith("nodes.a.")} == {
        "nodes.a.output.text"}


@pytest.mark.parametrize("dich,ngoai", [("c", "d"), ("b", "c"), ("b", "d")])
def test_moi_goi_y_QUA_duoc_cong_publish_va_node_ngoai_thi_KHONG(dich, ngoai):
    """🔑 Mot luat to tien, khong hai — do bang chinh cong publish."""
    goi = sorted(_duong(goi_y.goi_y(DOC, dich, cong_cu=CC), "cong"))
    assert goi, "danh sach rong khong chung minh duoc gi"

    for duong in goi:                      # chieu THUAN: goi y nao cung qua
        bien_dich.bien_dich(
            _thay_params(DOC, dich, {"x": "{{ %s }}" % duong}), cong_cu=CC)

    # chieu NGHICH: mot node KHONG duoc goi y thi cong publish tu choi
    with pytest.raises(bien_dich.LoiBienDich) as loi:
        bien_dich.bien_dich(
            _thay_params(DOC, dich,
                         {"x": "{{ nodes.%s.output.text }}" % ngoai}),
            cong_cu=CC)
    assert loi.value.ma == "tham_chieu_khong_phai_to_tien"


def test_node_khong_co_trong_do_thi_thi_khong_goi_y_node_nao():
    ket = goi_y.goi_y(DOC, "khong-co", cong_cu=CC)
    assert not _duong(ket, "cong")
    assert ket["loi"]["ma"] == "node_khong_trong_do_thi"
    assert ket["ham"], "bang ham van phai con — no khong phu thuoc do thi"


def test_bieu_thuc_DANG_GO_DO_khong_duoc_lam_mat_goi_y():
    """🔴 Lỗi THẬT, tìm ra trên trình duyệt 24/09 (cổng 8199, fixture cô lập).

    Người dùng gõ `"Vẽ: {{ nodes"` vào ô `prompt` rồi mở hộp gợi ý. Trình soạn
    gửi tài liệu ĐANG GÕ lên, `cau_truc()` chạy `_doi` NGHIÊM và ném
    `bieu_thuc_chua_ho_tro` ⇒ cửa trả `loi`, phần `nodes.*` biến mất **đúng
    giây người ta cần nó**. Cấu trúc đồ thị không phụ thuộc vào việc một chuỗi
    tham số đã gõ xong hay chưa.

    ⛔ Vế đối chứng: cổng PUBLISH vẫn phải từ chối đúng chuỗi ấy.
    """
    dang_go = _thay_params(DOC, "c", {"prompt": "Vẽ: {{ nodes"})
    ket = goi_y.goi_y(dang_go, "c", cong_cu=CC)
    assert ket["loi"] is None
    assert "nodes.a.output.text" in _duong(ket, "cong")

    with pytest.raises(bien_dich.LoiBienDich) as loi:
        bien_dich.bien_dich(dang_go, cong_cu=CC)
    assert loi.value.ma == "bieu_thuc_chua_ho_tro"


def test_do_thi_hong_thi_FAIL_CLOSED_o_phan_node():
    hong = json.loads(json.dumps(DOC))
    hong["pages"][0]["nodes"][0]["data"]["tool"] = "khong.ton.tai"
    ket = goi_y.goi_y(hong, "c", cong_cu=CC)
    assert not _duong(ket, "cong")
    assert ket["loi"]["ma"] == "node_khong_ton_tai"


# ── Goc namespace §6.2 ────────────────────────────────────────────────────

def test_goc_namespace_lay_tu_chinh_sach_NAMESPACE():
    goc = _duong(goi_y.goi_y(DOC, "c", cong_cu=CC), "goc")
    # `nodes` khong nam trong goc: no duoc BUNG ra thanh tung cong.
    assert goc == set(chinh_sach.NAMESPACE) - {"nodes"}


def test_moi_muc_khai_THAT_ve_viec_no_qua_duoc_cong_publish_hay_khong():
    """⭐ 25/09 (làn wfb5): `bien_dich._doi` không còn chỉ nhận đúng
    `{{ nodes.<id>.output.<cổng> }}` — nó uỷ quyền câu hỏi HÌNH DẠNG cho
    ngôn ngữ §6 đầy đủ (`ngon_ngu.kiem`), nên `qua_publish` giờ ĐÚNG theo
    ngôn ngữ §6: mọi namespace (`nodes.a.status`, `trigger` trần…) và mọi lời
    gọi hàm trong `BANG_HAM` đều là biểu thức HÌNH DẠNG hợp lệ ở cổng publish
    (không có nghĩa `bien_dich()` sẽ CHẤP NHẬN một đồ thị dùng chúng — cổng
    tổ tiên/cổng ra §6.2 vẫn xét riêng, và lúc CHẠY THẬT `cau_noi.giai_tham_so`
    lẫn `bao_gia` vẫn chỉ đọc được đúng MỘT đoạn sau `.output.` — xem
    `bien_dich._doi.__doc__`).

    Goi y khong duoc giau dieu do: `qua_publish` phai do bang chinh cong ay,
    va phep kiem nay do lai bang cong THAT chu khong tin loi khai.
    """
    ket = goi_y.goi_y(DOC, "c", cong_cu=CC)
    theo_duong = {m["duong"]: m for m in ket["muc"]}
    assert theo_duong["nodes.a.output.text"]["qua_publish"] is True
    assert theo_duong["nodes.a.status"]["qua_publish"] is True
    assert theo_duong["trigger"]["qua_publish"] is True
    assert all(m["qua_publish"] is True for m in ket["ham"])

    for duong, muc in theo_duong.items():
        try:
            bien_dich.bien_dich(
                _thay_params(DOC, "c", {"x": "{{ %s }}" % duong}), cong_cu=CC)
            that = True
        except bien_dich.LoiBienDich:
            that = False
        assert muc["qua_publish"] is that, duong


# ── Cua HTTP ──────────────────────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'goiy.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("goiy-a@example.com", "goiy-b@example.com"):
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
                          "LTT_SESSION_SECRET": "goiy-test-session",
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
    a, token_a = login("goiy-a@example.com")
    b, token_b = login("goiy-b@example.com")
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
        dinh_nghia.luu_draft(db, wf.id, document=DOC, revision=0)
        db.commit()
        return wf.id
    finally:
        db.close()


def _goi(client, token, wf_id, body):
    return client.post(
        f"/agent/api/v3/workflows/{wf_id}/bieu-thuc/goi-y",
        headers={"X-CSRF-Token": token, "Accept": "application/json"},
        json={**body, "csrf_token": token})


def test_cua_tra_goi_y_cho_chu_so_huu(api):
    _app, a, token_a, _b, _token_b = api
    wf_id = _wf("goiy-a@example.com")
    r = _goi(a, token_a, wf_id, {"node_id": "c"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    duong = {m["duong"] for m in r.json()["muc"]}
    assert "nodes.a.output.text" in duong
    assert not [d for d in duong if d.startswith("nodes.d.")]
    assert {m["ten"] for m in r.json()["ham"]} == set(BANG_HAM)


def test_cua_dung_TAI_LIEU_GUI_KEM_khi_co(api):
    """Trinh soan vua them mot node chua kip luu ⇒ goi y phai thay no."""
    _app, a, token_a, _b, _token_b = api
    wf_id = _wf("goiy-a@example.com")
    doc = json.loads(json.dumps(DOC))
    doc["pages"][0]["nodes"].append(_node("e", "image.generate"))
    doc["pages"][0]["edges"].append(_canh("e3", "c", "e"))
    r = _goi(a, token_a, wf_id, {"node_id": "e", "document": doc})
    assert r.status_code == 200, r.text
    duong = {m["duong"] for m in r.json()["muc"]}
    assert "nodes.c.output.text" in duong
    assert not [d for d in duong if d.startswith("nodes.d.")]


def test_workflow_cua_NGUOI_KHAC_tra_404_va_khong_ro_ten_node(api):
    _app, _a, _token_a, b, token_b = api
    wf_id = _wf("goiy-a@example.com")
    r = _goi(b, token_b, wf_id, {"node_id": "c"})
    assert r.status_code == 404
    assert "nodes.a" not in r.text


def test_chua_dang_nhap_thi_khong_co_goi_y(api):
    app, _a, _token_a, _b, _token_b = api
    wf_id = _wf("goiy-a@example.com")
    khach = TestClient(app, base_url="https://testserver",
                       follow_redirects=False)
    r = khach.post(f"/agent/api/v3/workflows/{wf_id}/bieu-thuc/goi-y",
                   headers={"Accept": "application/json"},
                   json={"node_id": "c"})
    assert r.status_code in (302, 303, 401, 403)
    assert "nodes.a.output.text" not in r.text
