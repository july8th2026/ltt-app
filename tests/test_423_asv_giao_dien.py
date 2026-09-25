"""Pha 20 — giao dien khach: route, quyen, IDOR, va co mo app.

Cong thoat: *mot nguoi dung binh thuong hoan thanh duoc MVP ma khong can biet
FFmpeg / CUDA / Sheets / duong dan noi bo.*

⭐ Do la mot cong thoat ve **thu KHONG hien ra** nhieu bang thu hien ra, nen phan
   lon tep nay kiem su vang mat: khong duong dan, khong job id, khong ten worker,
   khong ten giai doan bang tieng Anh trong ma nguon.
"""
from __future__ import annotations

import json
import os
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    """Hai nguoi dung that, qua HTTP that. Khuon lay tu `test_103`."""
    # 🔑 PostgreSQL NHAP khi co khai, SQLite khi khong.
    #
    #    SQLite chi cho MOT nguoi ghi, con bo nay mo nhieu phien cung luc theo
    #    dung thiet ke: handler mot phien, `ctx.progress` mot phien,
    #    `ctx.provider_dispatched` mot phien (ghi ben ngay truoc cu HTTP - bat
    #    bien I5). Voi ban model gia, moi phien chi giu vai mili-giay va khong
    #    ai thay. Voi model THAT, mot loi goi giu ket noi vai giay va chung dam
    #    nhau: `doc_canh` bi ghi `tu_choi` voi ly do that su la
    #    `database is locked [SQL: UPDATE jobs SET`.
    #
    # ⛔ `pg_scratch.scratch_url()` la duong DUY NHAT lay URL do: no doi ten CSDL
    #    chua `test` va `pytest.fail` neu khong, vi cac bai nay goi `drop_all`.
    #    Di qua bo canh, khong di quanh no.
    from tests import pg_scratch

    _nhap = pg_scratch.scratch_url()
    monkeypatch.setenv(
        "LTT_DATABASE_URL",
        _nhap or f"sqlite:///{(tmp_path / 'asv.db').as_posix()}")
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
    # ⭐ V6 pha 19: cua `routes.tao` nay KIEM quyen so huu giong qua LTT Voice, tuc
    #    doc bang `voice_profile`. Production luon co bang nay; mot fixture thieu
    #    no la mot fixture LECH production, va lech theo huong lam loi ha tang
    #    (500) trong nhu mot loi san pham.
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.reset_engine()
    if _nhap:
        # ⚠️ CSDL nhap song qua nhieu lan chay, nen phai don TRUOC. Khong don thi
        #    `tao_nguoi_dung` o duoi va cham UNIQUE email cua lan chay truoc, va
        #    thong bao do khong nhac gi toi viec CSDL con du lieu cu.
        #
        # 🔴 **GIU KHOA `postgres_test` QUANH DDL (N-53, 25/09).** `conftest.py`
        #    bo khoa nay khoi `_KHOA_PHIEN` tu 24/09 voi ly do "moi lan da co
        #    schema RIENG (`pg_scratch.schema_lan`), khong con gi de tranh". Do
        #    THAT 25/09 (lan `asv-day-truyen`) noi nguoc lai: `drop_all()` o day
        #    treo **20 phut** cho mot khoa bang, ke ca khi schema cua lan nay la
        #    RIENG va MOI (chua ai dung). ⛔ **KHONG THAY the lam sao ma van con
        #    tranh chap** — nghi ngo la `search_path=<lan>,public` khien mot
        #    schema RONG roi ve `public` cho ca doc lan ghi. Chua chung minh het,
        #    nhung do da CO va lap lai duoc, nen o day GIU LAI khoa nay bat ke ly
        #    do cu con dung hay khong: `postgres_test` la tai nguyen DOC QUYEN
        #    (khac `cpu_nhieu` chia suc tinh) — giu suot pha DDL la DUNG, va no
        #    la thu duy nhat chan `drop_all` xoa CSDL scratch cua mot lan/phien
        #    khac ngay duoi chan ho (nguy hiem hon treo).
        from tools.cua_so_yen import CuaSoYen
        with CuaSoYen(os.environ.get("LTT_PHIEN") or f"pytest:{os.getpid()}",
                     "moi_truong: drop_all+create_all Postgres",
                     tai_nguyen=("postgres_test",)):
            dbmod.Base.metadata.drop_all(dbmod.get_engine())
            dbmod.Base.metadata.create_all(dbmod.get_engine())
    else:
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


def test_MANIFEST_van_chua_mo_cho_khach_AN_DANH(moi_truong):
    """Muc 8: vong doi khong cong khai toi luc nghiem thu.

    ⚠️ 13/09/2026 — chu san pham chot BAT app cho khach DA DANG NHAP kiem thu.
       Ba menh de cu la `enabled is False` + `public is False` + `lifecycle ==
       "development"`. Ve DAU khong con dung: `enabled=True`.

    ⭐ Nhung ranh gioi that su dang duoc canh KHONG mat di, no chi HEP LAI: app
       van phai kin voi khach AN DANH. Nen bo nay giu nguyen hai ve con lai thay
       vi bi xoa — mot banh coc do "su vang mat" ma bi go han thi xoa cung xanh.

    ⛔ Va doi luon TEN. Ten cu (`..._van_chua_mo_cho_khach`) gio phat bieu SAI ve
       thu no kiem: app DA mo cho khach dang nhap. Mot phep kiem mang ten sai noi
       doi voi nguoi doc tiep theo — nguy hiem hon mot phep kiem do.
    """
    from apps.auto_scan_video.manifest import MANIFEST
    assert MANIFEST.enabled is True, (
        "chu san pham da bat app cho khach dang nhap (13/09); tat lai la mot "
        "thay doi CO Y va phai sua ca chu thich tren")
    assert MANIFEST.public is False, "app lot vao catalog AN DANH"
    assert MANIFEST.lifecycle == "development", "badge khong con trung thuc"


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

def _tao_run_cho(client, csrf, tmp_path, ten="a.mp4", **them):
    """Nop form nhu mot KHACH THAT nop.

    ⚠️ **Pha 21 them `giong_id`, va do khong phai mot chi tieu ky thuat.**

       Truoc pha 21 form khong doi giong: giao dien moi khach chon "Giọng mặc
       định" — mot lua chon ma engine TU CHOI phuc vu (pha 09 da bo giong mac
       dinh im lang). Mot lan nop nhu the di qua bon giai doan, bi giu credit,
       roi hong o giua chuoi.

    ⇒ Form gio doi mot giong CO THAT, va mau thu nay nop mot giong co that. Neu
      no khong nop thi no dang mo phong mot khach khong the ton tai.
    """
    from tests.fixtures.asv_media import tiny_mp4
    tep = tiny_mp4(tmp_path / ten, duration_s=1.0)
    du_lieu = {"csrf_token": csrf, "che_do": "fit_original",
               "giong_id": "Minh Đức"}
    du_lieu.update(them)
    with open(tep, "rb") as f:
        return client.post("/auto-scan-video/tao", data=du_lieu,
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


def test_MOI_buoc_hien_bang_NHAN_TIENG_VIET(moi_truong, tmp_path):
    """Khach thay nhan tieng Viet cua MOI buoc, khong thay `voice_synthesis`.

    ⚠️ Ten cu la `test_chin_buoc_...` trong khi than bai duyet
       `pipeline.CHUOI` — tuc no chua bao gio chot con so chin. Chuoi da la
       10 tu pha 12 va thanh 11 khi `qc_ai` duoc noi vao (06/09), va ten do
       van doc troi chay trong ca hai lan. Mot con so trong TEN khong duoc
       than bai kiem la mot con so khong ai sua khi no sai.
    """
    from apps.auto_scan_video import pipeline
    from apps.auto_scan_video.routes import NHAN_GIAI_DOAN
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf_a, _b, _cb = moi_truong
    r = _tao_run_cho(a, csrf_a, tmp_path)
    run_id = str(r.url).rstrip("/").rsplit("/", 1)[-1]
    van = a.get(f"/auto-scan-video/run/{run_id}").text

    for g in pipeline.CHUOI:
        assert NHAN_GIAI_DOAN[g.ten] in van, (
            f"thieu buoc {g.ten} tren trang tien do")
        # 🔴 Doi khop THEO TU, khong theo chuoi con.
        #
        #    `"qc" in van` cung dung voi `qc_ai`, nen khi `qc_ai` duoc noi
        #    vao chuoi (06/09) dong nay to cao `qc` — mot ten khong he lo
        #    ra. Mot phep kiem chi sai TEN thu pham dat nguoi doc vao duong
        #    tim kiem sai, va no ton kem hon la khong co gi.
        #
        # ⭐ Va khi do that, no phai NOI RA cho nao lo. Bai nay tung do
        #    mot lan duy nhat trong mot luot `-n 4` toan dai 4xx (06/09)
        #    roi khong tai hien lai; thong bao cu chi dua ra mot ban do
        #    HTML bi cat, nen khong con gi de lan theo. Lan sau se co.
        m = re.search(r"(?<![A-Za-z0-9_])" + re.escape(g.ten)
                      + r"(?![A-Za-z0-9_])", van)
        assert m is None, (
            f"lo ten ky thuat `{g.ten}` cho khach, tai vi tri {m.start()}:\n"
            f"  ...{van[max(0, m.start() - 120):m.end() + 120]}...")


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
