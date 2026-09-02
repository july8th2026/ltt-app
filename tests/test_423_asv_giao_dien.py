"""Pha 20 — giao dien khach: route, quyen, IDOR, va co mo app.

Cong thoat: *mot nguoi dung binh thuong hoan thanh duoc MVP ma khong can biet
FFmpeg / CUDA / Sheets / duong dan noi bo.*

⭐ Do la mot cong thoat ve **thu KHONG hien ra** nhieu bang thu hien ra, nen phan
   lon tep nay kiem su vang mat: khong duong dan, khong job id, khong ten worker,
   khong ten giai doan bang tieng Anh trong ma nguon.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    """Hai nguoi dung that, qua HTTP that. Khuon lay tu `test_103`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'asv.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_AUTO_SCAN_VIDEO", "1")
    monkeypatch.delenv("LTT_STORAGE", raising=False)

    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    # ⚠️ Phai nap CA bang cua app: `asv_run` chi vao `Base.metadata` khi module
    #    nay duoc import. Ban dau tep nay khong co dong duoi, va no van xanh khi
    #    chay CA BO — vi mot phep kiem truoc do da import ho. Chay RIENG thi do
    #    voi `no such table: asv_run`. Mot phep kiem phu thuoc thu tu import la
    #    mot phep kiem dang do thu tu import.
    import apps.auto_scan_video.tables  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    for email in ("asv-a@example.com", "asv-b@example.com"):
        u = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                           is_verified=True)
        credit.nap(db, u.id, 1000)
    db.commit()
    db.close()
    dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "asv-ui-test-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})

    def dang_nhap(email):
        c = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = c.get("/login")
        tok = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert c.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": tok, "next": "/auto-scan-video"}).status_code == 200
        trang = c.get("/auto-scan-video")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', trang.text).group(1)
        return c, csrf

    a, csrf_a = dang_nhap("asv-a@example.com")
    b, csrf_b = dang_nhap("asv-b@example.com")
    yield app, a, csrf_a, b, csrf_b
    a.close()
    b.close()
    dbmod.reset_engine()
    storage_mod._storage = None


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Co mo app — muc 8
# ══════════════════════════════════════════════════════════════════════════════

def test_co_TAT_thi_moi_route_tra_404(moi_truong, monkeypatch):
    """⛔ `MANIFEST.enabled=False` KHONG dong route — `mount_all` gan router cho
    moi app khong loi. Co nay la thu duy nhat giu app khong cong khai."""
    _app, a, csrf, _b, _cb = moi_truong
    monkeypatch.delenv("LTT_AUTO_SCAN_VIDEO", raising=False)
    for duong in ("/auto-scan-video", "/auto-scan-video/run/x"):
        assert a.get(duong).status_code == 404, f"{duong} van song khi co da tat"


def test_co_tat_thi_KHONG_303_ve_login(moi_truong, monkeypatch):
    """⚠️ Bay thu tu `Depends`, va no co that trong kho nay.

    Neu `_cong_co` dat SAU `require_login`, mot khach chua dang nhap se bi day
    ve `/login` thay vi nhan 404 — tuc route "da dong" van **thua nhan minh ton
    tai**. Chot bang mot client CHUA dang nhap.
    """
    app, *_ = moi_truong
    monkeypatch.delenv("LTT_AUTO_SCAN_VIDEO", raising=False)
    la = TestClient(app, base_url="https://testserver", follow_redirects=False)
    r = la.get("/auto-scan-video")
    assert r.status_code == 404, (
        f"nhan {r.status_code} — `_cong_co` dang dat SAU `require_login`")
    la.close()


def test_MANIFEST_van_chua_mo_cho_khach(moi_truong):
    """Muc 8: vong doi khong cong khai toi luc nghiem thu."""
    from apps.auto_scan_video.manifest import MANIFEST
    assert MANIFEST.enabled is False
    assert MANIFEST.public is False
    assert MANIFEST.lifecycle == "development"


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Quyen + CSRF tren MOI route (muc 7)
# ══════════════════════════════════════════════════════════════════════════════

def test_chua_dang_nhap_thi_khong_vao_duoc(moi_truong):
    app, *_ = moi_truong
    la = TestClient(app, base_url="https://testserver", follow_redirects=False)
    r = la.get("/auto-scan-video")
    assert r.status_code in (302, 303, 307, 401), (
        "trang cua khach mo cho nguoi chua dang nhap")
    la.close()


def test_MOI_route_ghi_deu_doi_CSRF(moi_truong):
    """Chot theo TAP HOP route POST, khong theo mot danh sach chep tay.

    ⚠️ Duyet `router.routes` cua CHINH module nay, khong duyet `app.routes`:
       ban FastAPI o day boc router da include thanh `_IncludedRouter`, nen
       `getattr(r, "path")` tra ve `None` va phep quet tim duoc **khong route
       nao** — mot phep kiem xanh vi no khong nhin thay gi.
    """
    _app, a, _csrf, _b, _cb = moi_truong
    from apps.auto_scan_video.manifest import MANIFEST
    from apps.auto_scan_video.routes import router

    post = [r for r in router.routes
            if "POST" in (getattr(r, "methods", None) or set())]
    assert post, "khong tim thay route POST nao — phep kiem vo nghia"

    for r in post:
        duong = (MANIFEST.route_prefix + r.path).replace("{run_id}", "khong-co")
        resp = a.post(duong, data={"csrf_token": "sai"})
        assert resp.status_code in (400, 404, 422), (
            f"{duong} nhan CSRF sai ma tra {resp.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  IDOR — hai nguoi dung that
# ══════════════════════════════════════════════════════════════════════════════

def _tao_run_cho(client, csrf, tmp_path, ten="a.mp4"):
    from tests.fixtures.asv_media import tiny_mp4
    tep = tiny_mp4(tmp_path / ten, duration_s=1.0)
    with open(tep, "rb") as f:
        return client.post("/auto-scan-video/tao",
                           data={"csrf_token": csrf, "che_do": "fit_original"},
                           files={"video": (ten, f, "video/mp4")})


def test_nguoi_khac_KHONG_xem_duoc_lan_chay_cua_toi(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf_a, b, _cb = moi_truong

    r = _tao_run_cho(a, csrf_a, tmp_path)
    assert r.status_code == 200, r.text[:300]
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    assert run_id and run_id != "auto-scan-video"

    # A xem duoc.
    assert a.get(f"/auto-scan-video/run/{run_id}").status_code == 200
    # B thi khong — va nhan 404, khong phai 403.
    rb = b.get(f"/auto-scan-video/run/{run_id}")
    assert rb.status_code == 404, (
        f"B nhan {rb.status_code}; 403 se xac nhan rang run do co that")


def test_nguoi_khac_KHONG_tai_duoc_ket_qua(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf_a, b, _cb = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    assert b.get(f"/auto-scan-video/run/{run_id}/tai").status_code == 404


def test_nguoi_khac_KHONG_huy_duoc_lan_chay_cua_toi(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf_a, b, csrf_b = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    rb = b.post(f"/auto-scan-video/run/{run_id}/huy",
                data={"csrf_token": csrf_b})
    assert rb.status_code == 404


def test_lich_su_chi_hien_lan_chay_CUA_MINH(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf_a, b, _cb = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    assert run_id in a.get("/auto-scan-video").text
    assert run_id not in b.get("/auto-scan-video").text


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Cong thoat — khach khong phai biet gi ve ben trong
# ══════════════════════════════════════════════════════════════════════════════

#: ⛔ Chuoi khong bao gio duoc hien cho khach thuong. Chot theo TAP HOP.
CAM_TREN_TRANG = ("ffmpeg", "ffprobe", "CUDA", "demucs", "whisper",
                  "C:\\", "/tmp/", "job_id", "worker", "Traceback",
                  "asv-staging", "storage_key")


def test_trang_khach_KHONG_lo_chi_tiet_ky_thuat(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx
    fx.require_ffmpeg()
    _app, a, csrf_a, _b, _cb = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]

    for duong in ("/auto-scan-video",
                  f"/auto-scan-video/run/{run_id}",
                  f"/auto-scan-video/run/{run_id}/tien-do"):
        van = a.get(duong).text
        for dau in CAM_TREN_TRANG:
            assert dau not in van, f"{duong} lo `{dau}`"


def test_chin_buoc_hien_bang_NHAN_TIENG_VIET(moi_truong, tmp_path):
    """Khach thay chin buoc, khong thay `voice_synthesis`."""
    from apps.auto_scan_video import pipeline
    from apps.auto_scan_video.routes import NHAN_GIAI_DOAN
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf_a, _b, _cb = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    van = a.get(f"/auto-scan-video/run/{run_id}").text

    for g in pipeline.CHUOI:
        assert NHAN_GIAI_DOAN[g.ten] in van, f"thieu buoc {g.ten}"
        assert g.ten not in van, f"lo ten ky thuat `{g.ten}` cho khach"


def test_moi_giai_doan_deu_co_NHAN():
    """Chot theo TAP HOP: them mot giai doan ma quen dat nhan se lam do, thay vi
    de giao dien hien mot o trong."""
    from apps.auto_scan_video import pipeline
    from apps.auto_scan_video.routes import NHAN_GIAI_DOAN

    assert set(NHAN_GIAI_DOAN) == set(pipeline.TEN_GIAI_DOAN)


def test_KHONG_co_node_keo_tha_hay_do_thi(moi_truong):
    """Prompt 20 cam ro: khong drag/drop node, khong do thi tuy y."""
    _app, a, _csrf, _b, _cb = moi_truong
    van = a.get("/auto-scan-video").text.lower()
    for dau in ("draggable", "jsplumb", "reactflow", "canvas", "node-editor"):
        assert dau not in van, f"trang co dau hieu trinh dung do thi: {dau}"


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Nghiep vu KHONG nam trong routes.py
# ══════════════════════════════════════════════════════════════════════════════

def test_routes_chi_lo_HTTP():
    """Tran cung cua hop dong app: 900 dong / 30 handler.

    ⭐ Va chot them mot dieu `lint_app_contract` khong chot: `routes.py` khong
       duoc truy van CSDL truc tiep. Mot `select(...)` o day la mot phep loc
       quyen so huu nam trong handler HTTP — tuc mot bat bien khong ap dung cho
       worker.
    """
    import ast
    import inspect

    from apps.auto_scan_video import routes

    ma = inspect.getsource(routes)
    assert len(ma.splitlines()) < 900

    cay = ast.parse(ma)
    ten = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "select" not in ten, "routes.py dang truy van CSDL truc tiep"


def test_uoc_gia_o_TANG_DICH_VU_khong_o_route():
    import inspect

    from apps.auto_scan_video import features, routes

    assert "uoc_credit" not in inspect.getsource(routes)
    assert "uoc_credit" in inspect.getsource(features.tao_run_tu_tai_len)
