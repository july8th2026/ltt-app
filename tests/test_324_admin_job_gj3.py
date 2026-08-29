"""GJ3 — dieu tra viec chay hong (`05_PAGE_CONTRACT_MATRIX.md` P1 + P10).

## Van de duoc sua, do tren PRODUCTION 29/08

Hang doi chu y o `/admin/` bao "4 viec chay hong" va dan toi `/admin/job/list`.
Trang do khi ay hien:

  · `user_id` la **UUID tran, khong bam duoc** — muon biet do la ai phai chep no
    sang mot trang khac;
  · **khong co cot loi nao ca** — `Job.error` ton tai trong model nhung khong
    nam trong `column_list`.

Nguoi van hanh di het hang doi roi van khong biet **vi sao hong** va **cua ai**.
Hop dong P1 noi moi muc chu y phai mo trang **giai quyet duoc** no; mot bang chi
noi "error" thi chua giai quyet duoc gi.

⛔ Khong phep kiem nao truoc do bat duoc, vi trang van tra 200 va van co du lieu.
   "Ngo cut" khong phai mot loi HTTP.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def gj3(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'gj3.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-gj3")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.models import Job
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        u = tao_nguoi_dung(db, email="khach@example.com",
                           password="matkhau-tot-12", role="user",
                           is_verified=True)
        db.add(Job(user_id=u.id, app_slug="ltt_llm", job_type="ltt_llm.chat",
                   status="error",
                   error="ProviderTimeout: may B khong tra loi sau 120s"))
        db.commit()
        uid = u.id
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
    client.uid = uid
    try:
        yield client
    finally:
        dbmod.reset_engine()


def test_bang_job_noi_VI_SAO_hong(gj3):
    """Truoc dot nay bang chi noi "error" va dung o do."""
    body = gj3.get("/admin/job/list").text
    assert "ProviderTimeout" in body, "khong thay thong bao loi tren bang"


def test_bang_job_dan_sang_khach_khong_bat_chep_uuid(gj3):
    body = gj3.get("/admin/job/list").text
    assert f'/admin/nguoi-dung?q={gj3.uid}' in body


def test_gj3_di_het_duong_tu_hang_doi_toi_khach(gj3):
    """Tong quan -> "Viec chay hong" -> bang job -> ho so khach.

    Di THAT tung buoc, khong chi kiem tung trang mo duoc.
    """
    tq = gj3.get("/admin/").text
    assert "Việc chạy hỏng" in tq
    dich = re.search(r'href="(/admin/job/list[^"]*)"', tq)
    assert dich, "muc hang doi khong tro di dau"

    bang = gj3.get(dich.group(1))
    assert bang.status_code == 200
    assert "ProviderTimeout" in bang.text

    ho_so = re.search(r'href="(/admin/nguoi-dung\?q=[^"]+)"', bang.text)
    assert ho_so, "tu bang job khong sang duoc ho so khach"
    r = gj3.get(ho_so.group(1).replace("&amp;", "&"))
    assert r.status_code == 200
    assert "khach@example.com" in r.text


def test_loi_dai_bi_cat_o_danh_sach_nhung_giu_du_o_title(gj3):
    """Mot traceback dai khong duoc day bang rong ra che moi cot khac."""
    import platform_core.db as dbmod
    from platform_core.models import Job
    dai = "X" * 400
    gen = dbmod.get_session(); db = next(gen)
    try:
        db.add(Job(user_id=gj3.uid, app_slug="a", job_type="b",
                   status="error", error=dai))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    body = gj3.get("/admin/job/list").text
    # Phan NHIN THAY bi cat; ban day du van o `title` de re chuot doc duoc —
    # cung khuon voi `.adm-id-cat` o bang khach hang.
    assert f'title="{dai}"' in body, "ban day du phai giu o title"
    nhin_thay = body.split(f'title="{dai}"')[1][:200]
    assert "…" in nhin_thay, "o bang phai co dau cat"
    assert "X" * 71 not in nhin_thay, "phan nhin thay khong duoc qua 70 ky tu"
