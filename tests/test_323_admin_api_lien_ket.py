"""Lo C5-C8 — khu API Platform het ngo cut (`05_PAGE_CONTRACT_MATRIX.md` P6-P9).

## Van de duoc sua

Truoc dot nay khu API co **nam ngo cut**: nguoi van hanh toi duoc mot con so bao
hong roi khong di tiep duoc dau.

  · trang Tong quan bao "Job hong: 7" — khong bam duoc;
  · ba trang Governance (Cong cu, Chinh sach, Kill switch) khong co MOT lien ket
    nao ca;
  · bang request hien email khach duoi dang chu tran;
  · bang job hien ten tool duoi dang chu tran;
  · trang Provider Credentials khong co duong nao sang khu Operations, nen mot
    khoa o trang thai `error` la het duong di.

Hop dong P1 va P6 doi moi con so bao hong phai mo dung trang xu ly duoc no,
**kem bo loc da dat san** — mot lien ket ra danh sach chua loc chi doi viec di
cho khac.

## Cai bay tep nay canh

Hai dinh danh khac nhau cung ten "tool":

  · `jobs_by_tool()` gom theo `Job.job_type`      → "render"
  · `jobs_page(tool=)` loc theo `params._api.tool` → "image.ltt"

Dung nham thi lien ket tra **200 voi danh sach rong** — kieu hong te nhat, vi no
trong nhu du lieu that. `test_khong_dung_nham_dinh_danh_tool` chot dieu do.
"""
from __future__ import annotations

import re
import uuid

import pytest

NAV = {
    "/admin/", "/admin/khach-hang", "/admin/doanh-thu", "/admin/api-tong-quan",
    "/admin/apikeys", "/admin/he-thong", "/admin/api-tai-khoan",
    "/admin/api-cong-cu", "/admin/api-request", "/admin/api-gia",
    "/admin/api-khoa", "/admin/api-chinh-sach", "/admin/api-kill-switch",
    "/admin/api-job", "/admin/api-bao-mat", "/admin/api-margin",
    "/admin/nguoi-dung", "/admin/credit-entry/list", "/admin/job/list",
    "/admin/nhat-ky-admin/list", "/admin/api-models", "/admin/nang-cao",
    "/admin/don", "/admin/goi", "/status",
}


@pytest.fixture()
def api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'apilink.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-api-lien-ket")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.models import Job
    from platform_core.public_api.invocation import API_META_KEY
    from platform_core.public_api.tables import ApiRequestLog
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        u = tao_nguoi_dung(db, email="khach@example.com",
                           password="matkhau-tot-12", role="user",
                           is_verified=True)
        job = Job(user_id=u.id, app_slug="anhnoibo", job_type="render",
                  status="error", params={API_META_KEY: {"tool": "image.ltt"}})
        db.add(job); db.flush()
        for i, (st, code) in enumerate(((200, ""), (502, "provider_error"),
                                        (429, "rate_limited"))):
            db.add(ApiRequestLog(
                id=str(uuid.uuid4()), request_id=f"req_t_{i:03d}",
                user_id=u.id, key_id="k_t", method="POST",
                route="/v1/tools/image.ltt", status=st, code=code,
                latency_ms=100 + i, tool="image.ltt",
                job_id=job.id if i else "", credit_delta=0))
        db.commit()
        ids = {"uid": u.id, "job": job.id}
    finally:
        try: next(gen)
        except StopIteration: pass

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    r = client.post("/login", data={"username": "sep@example.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok.group(1)},
                    follow_redirects=False)
    assert r.status_code == 303
    client.ids = ids
    try:
        yield client
    finally:
        dbmod.reset_engine()


def _than(client, url: str) -> str:
    """Than trang, bo phan vo (thanh ben + dai muc con dung chung moi trang)."""
    t = client.get(url).text
    i = t.find("adm-chrome")
    return t[i:] if i >= 0 else t


def _lien_ket(client, url: str) -> list[str]:
    return [l for l in dict.fromkeys(
        re.findall(r'href="(/admin/[^"]*)"', _than(client, url)))
        if l.split("?")[0] not in NAV or "?" in l]


# ── Khong con ngo cut ────────────────────────────────────────────────────────

@pytest.mark.parametrize("trang", [
    "/admin/api-tong-quan", "/admin/api-cong-cu", "/admin/api-request",
    "/admin/api-job",
])
def test_moi_trang_api_deu_dan_di_dau_do(api, trang):
    assert _lien_ket(api, trang), f"{trang} la ngo cut"


def test_moi_lien_ket_trong_than_deu_mo_duoc(api):
    """Lien ket tra 4xx/5xx con te hon khong co lien ket."""
    hong = []
    for trang in ("/admin/api-tong-quan", "/admin/api-cong-cu",
                  "/admin/api-request", "/admin/api-job",
                  "/admin/api-bao-mat", "/admin/apikeys"):
        for l in _lien_ket(api, trang):
            ma = api.get(l).status_code
            if ma != 200:
                hong.append(f"{trang} -> {l} = {ma}")
    assert not hong, hong


def test_o_chi_so_tong_quan_bam_duoc(api):
    than = _than(api, "/admin/api-tong-quan")
    assert than.count("adm-o-link") >= 10, "phan lon o chi so van la ngo cut"


# ── Bo loc PHAI duoc dat san ─────────────────────────────────────────────────

def test_lien_ket_ma_loi_dat_san_bo_loc(api):
    """Hop dong P1: mo dung trang xu ly duoc no, KEM BO LOC.

    Mot lien ket ra danh sach chua loc chi doi viec sang cho khac.
    """
    day_du = _than(api, "/admin/api-request").count("req_t_")
    da_loc = _than(api, "/admin/api-request?code=provider_error").count("req_t_")
    assert day_du > da_loc > 0, (day_du, da_loc)


def test_lien_ket_chi_hong_dat_san_bo_loc(api):
    day_du = _than(api, "/admin/api-request").count("req_t_")
    chi_hong = _than(api, "/admin/api-request?status=failed").count("req_t_")
    assert day_du > chi_hong > 0, (day_du, chi_hong)


def test_lien_ket_tool_tu_trang_cong_cu_ra_job_that(api):
    than = _than(api, "/admin/api-cong-cu")
    assert "/admin/api-job?tool=image.ltt" in than
    assert api.ids["job"][:12] in _than(api, "/admin/api-job?tool=image.ltt")


# ── Cai bay dinh danh ────────────────────────────────────────────────────────

def test_khong_dung_nham_dinh_danh_tool(api):
    """🔴 `jobs_by_tool()` gom theo `Job.job_type`; `jobs_page(tool=)` loc theo
    ten tool API. Bang "Job theo loai" o trang Tong quan dung khoa THU NHAT, nen
    no khong duoc sinh ra `?tool=`.

    Neu ai do "sua lai cho dep" thanh `?tool={job_type}`, lien ket se tra 200 voi
    danh sach rong — va khong ai phat hien vi trang van chay.
    """
    than = _than(api, "/admin/api-tong-quan")
    khoi = than[than.index("Job theo loại"):] if "Job theo loại" in than else ""
    assert khoi, "khong tim thay bang job theo loai"
    assert "/admin/api-job?tool=render" not in khoi
    # Dich dung: bang job cua nen tang, noi `job_type` la cot tim duoc.
    assert "/admin/job/list?search=render" in khoi


def test_o_job_noi_ro_pham_vi_la_toan_nen_tang(api):
    """`overview()["jobs"]` dem job toan nen tang (khong loc `_api`).

    Neu nhan khong noi dieu do thi con so tren mot bang dieu khien API se bi doc
    thanh "job cua API", va no khong phai.
    """
    than = _than(api, "/admin/api-tong-quan")
    assert "toàn nền tảng" in than


# ── Het luong copy UUID ──────────────────────────────────────────────────────

def test_dong_request_dan_sang_ho_so_khach(api):
    than = _than(api, "/admin/api-request")
    assert f'/admin/nguoi-dung?q={api.ids["uid"]}' in than
    assert f'/admin/api-tai-khoan?user={api.ids["uid"]}' in than


def test_dong_job_dan_sang_ho_so_khach(api):
    assert f'/admin/nguoi-dung?q={api.ids["uid"]}' in _than(api, "/admin/api-job")


def test_provider_credential_hong_dan_sang_operations(api):
    """Hop dong P9: provider/khoa loi -> API Operations.

    Truoc dot nay trang Provider Credentials khong co MOT lien ket nao sang khu
    Operations, nen mot khoa o trang thai `error` la het duong di.
    """
    import platform_core.db as dbmod
    from platform_core import api_keys

    gen = dbmod.get_session(); db = next(gen)
    try:
        k = api_keys.tao_key(db, provider="gemini", credential="AIzaTEST0001",
                             name="k-hong", categories=["image"])
        k.status = "error"
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    than = _than(api, "/admin/apikeys")
    assert "k-hong" in than
    assert "/admin/api-request?status=failed" in than
