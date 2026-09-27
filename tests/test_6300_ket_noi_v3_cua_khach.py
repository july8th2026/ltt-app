# -*- coding: utf-8 -*-
"""Cua ket noi cua khach — `apps/agent/routes/ket_noi_v3.py` (lan UI-5).

## Dieu phep kiem nay giu

Mo-dun duoi day la **day noi** giua giao dien va `platform_core/credential.py`.
Mot day noi hong theo ba kieu, va ca ba deu IM LANG:

1. **Ro bi mat ra API.** Bi mat duoc ma hoa at-rest rat ky, roi mot cua HTTP
   tra ca `bi_mat_ma_hoa` (hoac nhet `refresh_token` vao `meta`, tuc ra NGOAI
   lop ma hoa). `test_khong_mot_phan_hoi_nao_chua_khoa_META_CAM` quet **moi**
   phan hoi cua **moi** cua, khong liet ke tay tung truong.
2. **Ro su ton tai.** Mot `403` cho credential cua nguoi khac la mot may dem:
   go id bua thi `404`, go dung id cua nguoi khac thi `403`. Cua nay phai tra
   **cung mot 404** cho ca hai.
3. **Moi mot ket noi ma cong publish se tu choi.** `credential.kiem_ref` doi
   `kieu` nam trong `NodeDefinition.credential`; neu o chon liet ke moi kieu
   thi khach gan mot cai sai va chi biet luc bam Xuat ban.

## Doi chung

`test_doi_chung_*` chung minh tung phep phu dinh o tren thuc su do duoc cai no
noi. Khong co chung, mot bo quet rong (vi doc sai khoa) lam moi phep an toan
xanh.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

EMAIL = "ketnoi6300@example.com"
EMAIL_KHAC = "ketnoi6300-khac@example.com"
MAT_KHAU = "Strong-pass-6300"
BI_MAT = "sk-live-6300-KHACH-KHONG-DUOC-LO-4242"


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
                       f"sqlite:///{(tmp_path / 'ketnoi.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-6300-" + "k" * 32)
    # ⛔ Khong de bien nay song sot tu moi truong that: mot `LTT_OAUTH_*` co san
    #    se lam `test_cloud_chua_cau_hinh` xanh gia (no do su VANG MAT cua cau
    #    hinh, nen mot cau hinh co that lam phep do noi nguoc).
    for k in list(__import__("os").environ):
        if k.startswith("LTT_OAUTH_"):
            monkeypatch.delenv(k, raising=False)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import registry as _reg
    _reg.load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email=EMAIL, password=MAT_KHAU, is_verified=True)
    tao_nguoi_dung(db, email=EMAIL_KHAC, password=MAT_KHAU, is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                   encoding="utf-8")
    # 🔴 IMPORT TUONG MINH. `apps/agent/routes/__init__.py` la so dung chung S5
    #    (chu la lan UI-1), nen lan nay KHONG them dong import vao do. Router
    #    la MOT doi tuong dung chung (`_shared.router`), nen import o day gan
    #    cac cua nay vao dung router ma `create_app` se lap.
    #
    #    ⚠️ Khi dieu phoi da dau dong import vao `__init__.py`, dong duoi tro
    #    thanh vo hai (import lai mot module da nap khong dang ky hai lan).
    import apps.agent.routes.ket_noi_v3  # noqa: F401
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ket-noi-6300-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    yield app
    dbmod.reset_engine()


@pytest.fixture()
def api(may_chu):
    client = _dang_nhap(may_chu, EMAIL)
    yield client
    client.close()


def _tao(api: TestClient, **ghi_de):
    than = {"kieu": "api_key", "ten": "Khoa thu",
            "bi_mat": {"gia_tri": BI_MAT}}
    than.update(ghi_de)
    csrf = _csrf(api)
    than["csrf_token"] = csrf
    return api.post("/agent/api/v3/ket-noi", json=than,
                    headers={"X-CSRF-Token": csrf})


# ── Duong song: tao -> liet ke -> thu hoi ──────────────────────────────────

def test_tao_va_liet_ke_ket_noi_cua_chinh_minh(api):
    r = _tao(api)
    assert r.status_code == 201, r.text
    muc = r.json()
    assert muc["kieu"] == "api_key"
    # `preview` la 4 ky tu cuoi CUA CHINH KHOA — du de nhan ra khoa nao, khong
    # du de dung no. ⚠️ Bai nay bat mot loi that: gui `bi_mat` la mot dict mot
    # khoa lam `credential._preview` lay 4 ky tu cuoi cua CHUOI JSON (`42"}`),
    # tuc mot cot `preview` vo nghia.
    assert muc["preview"] == "..." + BI_MAT[-4:]
    ds = api.get("/agent/api/v3/ket-noi").json()["items"]
    assert [m["id"] for m in ds] == [muc["id"]]


def test_thu_hoi_xoa_bi_mat_nhung_hang_o_lai(api):
    ref = _tao(api).json()["id"]
    csrf = _csrf(api)
    r = api.request("DELETE", f"/agent/api/v3/ket-noi/{ref}",
                    json={"csrf_token": csrf},
                    headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200, r.text
    ds = api.get("/agent/api/v3/ket-noi").json()["items"]
    # ⭐ Hang O LAI (bang chung mot run da dung gi) va `preview` bi xoa.
    assert len(ds) == 1 and ds[0]["thu_hoi_luc"] and ds[0]["preview"] == ""


# ── 404, khong 403 ────────────────────────────────────────────────────────

def test_ket_noi_cua_tai_khoan_khac_tra_404_khong_lo_su_ton_tai(may_chu):
    a = _dang_nhap(may_chu, EMAIL)
    ref = _tao(a).json()["id"]
    b = _dang_nhap(may_chu, EMAIL_KHAC)
    # `b` khong thay ket noi cua `a`...
    assert b.get("/agent/api/v3/ket-noi").json()["items"] == []
    csrf = _csrf(b)
    r_that = b.request("DELETE", f"/agent/api/v3/ket-noi/{ref}",
                       json={"csrf_token": csrf},
                       headers={"X-CSRF-Token": csrf})
    r_bua = b.request("DELETE", "/agent/api/v3/ket-noi/khong-he-ton-tai",
                      json={"csrf_token": csrf},
                      headers={"X-CSRF-Token": csrf})
    # ⭐ KHONG phan biet duoc hai ca: id THAT cua nguoi khac va id BUA phai cho
    #    cung mot ma. Phan biet chung la mot may dem cho nguoi ngoai.
    assert r_that.status_code == r_bua.status_code == 404
    # ⚠️ So `detail`, khong so ca than: nen tang gan mot `correlation_id` khac
    #    nhau cho moi request, va no khong noi gi ve id nao ton tai.
    assert r_that.json()["detail"] == r_bua.json()["detail"]
    a.close(); b.close()


def test_doi_chung_chinh_chu_thu_hoi_duoc(may_chu):
    """Doi chung cho bai tren: neu `thu_hoi` luon 404 thi bai kia xanh rong."""
    a = _dang_nhap(may_chu, EMAIL)
    ref = _tao(a).json()["id"]
    csrf = _csrf(a)
    assert a.request("DELETE", f"/agent/api/v3/ket-noi/{ref}",
                     json={"csrf_token": csrf},
                     headers={"X-CSRF-Token": csrf}).status_code == 200
    a.close()


# ── Loc theo `kieu` ma node nhan ──────────────────────────────────────────

def test_loc_dung_kieu_node_do_nhan(api):
    _tao(api, kieu="api_key", ten="A")
    _tao(api, kieu="bearer", ten="B", bi_mat={"gia_tri": "tok-6300"})
    chi_bearer = api.get("/agent/api/v3/ket-noi?kieu=bearer").json()["items"]
    assert [m["ten"] for m in chi_bearer] == ["B"]
    ca_hai = api.get("/agent/api/v3/ket-noi?kieu=bearer,api_key").json()["items"]
    assert {m["ten"] for m in ca_hai} == {"A", "B"}


def test_kieu_la_tra_422_chu_khong_tra_danh_sach_rong(api):
    """⛔ Rong im lang la sai hinh dang: o chon se trong trong khi khach CO ket
    noi, va khong ai biet vi sao."""
    _tao(api)
    r = api.get("/agent/api/v3/ket-noi?kieu=khong_co_kieu_nay")
    assert r.status_code == 422
    assert r.json()["detail"]["ma"] == "kieu_sai"


# ── Hinh dang bi mat ─────────────────────────────────────────────────────

def test_thieu_khoa_bi_mat_bi_tu_choi_kem_TEN_khoa_thieu(api):
    r = _tao(api, kieu="basic", bi_mat={"ten_dang_nhap": "u"})
    assert r.status_code == 422
    ct = r.json()["detail"]
    assert ct["ma"] == "bi_mat_sai_hinh_dang" and ct["thieu"] == ["mat_khau"]


def test_khoa_LA_trong_bi_mat_bi_tu_choi_khong_nuot_lang_le(api):
    """Mot khoa go sai ten la mot bi mat khach TUONG da dat, thuc ra chua."""
    r = _tao(api, bi_mat={"gia_tri": BI_MAT, "gia_tri_2": "x"})
    assert r.status_code == 422
    assert r.json()["detail"]["khoa_la"] == ["gia_tri_2"]


def test_meta_mang_khoa_BI_CAM_bi_tu_choi_boi_LOP_GOC(api):
    """⛔ Khong loc tay o route: `credential._kiem_meta` la ban chan THAT, va
    mot ban loc thu hai se troi khoi no."""
    from platform_core import credential as kho
    r = _tao(api, meta={"refresh_token": "rt-6300"})
    assert r.status_code == 422
    assert r.json()["detail"]["ma"] == "meta_co_bi_mat"
    assert "refresh_token" in kho.META_CAM


# ── Tang cloud (Q4 = C) ──────────────────────────────────────────────────

def test_nha_cung_cap_sinh_TU_CATALOG_khong_tu_bang_go_tay(api):
    so = api.get("/agent/api/v3/ket-noi/nha-cung-cap").json()
    from platform_core.workflow import connector
    from apps.agent.routes.ket_noi_v3 import _nha_cung_cap_cua_piece
    cho_doi = {_nha_cung_cap_cua_piece(m["piece"])
               for m in connector.doc_catalog() if m.get("piece")}
    co = {n["ma"] for n in so["nha_cung_cap"]}
    # ⭐ Moi nha cung cap co piece trong catalog phai xuat hien. Mot piece moi
    #    vao catalog thi tu co dong o day — khong ai phai sua mot bang.
    assert cho_doi and cho_doi <= co, f"thieu: {sorted(cho_doi - co)}"


def test_cloud_chua_cau_hinh_thi_noi_THANG_va_chi_ra_bien_can_dat(api):
    so = api.get("/agent/api/v3/ket-noi/nha-cung-cap").json()
    co_cloud = [n for n in so["nha_cung_cap"] if n["co_tang_cloud"]]
    assert co_cloud, "khong nha cung cap nao doi oauth2 — catalog rong?"
    for n in co_cloud:
        assert n["san_sang"] is False and n["ly_do"] == "chua_cau_hinh"
        # 🔴 Dang ky OAuth app la viec CHI CHU DU AN lam duoc. Cua nay khong
        #    tu nhap bi mat nao — no chi noi ra TEN bien can dat.
        assert len(n["bien_moi_truong"]) == 2
        assert all(b.startswith("LTT_OAUTH_") for b in n["bien_moi_truong"])
    r = _tao(api, kieu="oauth2", tang="cloud",
             nha_cung_cap=co_cloud[0]["ma"],
             bi_mat={"client_id": "ci", "client_secret": "cs"})
    assert r.status_code == 422
    assert r.json()["detail"]["ma"] == "cloud_chua_cau_hinh"


def test_doi_chung_dat_hai_bien_thi_tang_cloud_BAT(api, monkeypatch):
    """⛔ Khong co doi chung nay, `san_sang=False` co the la mot hang so."""
    so = api.get("/agent/api/v3/ket-noi/nha-cung-cap").json()
    n = next(x for x in so["nha_cung_cap"] if x["co_tang_cloud"])
    for b in n["bien_moi_truong"]:
        monkeypatch.setenv(b, "gia-tri-thu-6300")
    lai = api.get("/agent/api/v3/ket-noi/nha-cung-cap").json()
    moi = next(x for x in lai["nha_cung_cap"] if x["ma"] == n["ma"])
    assert moi["san_sang"] is True and moi["ly_do"] == ""


def test_nhan_o_bi_mat_den_tu_MAY_CHU(api):
    """§6 luat 3 + banh coc `test_967`: nhan la viec cua may chu, khong phai
    mot bang tra trong frontend."""
    so = api.get("/agent/api/v3/ket-noi/nha-cung-cap").json()
    o = so["khoa_bi_mat"]["basic"]
    assert [x["ten"] for x in o] == ["ten_dang_nhap", "mat_khau"]
    assert all(x["nhan"] and x["nhan"] != x["ten"] for x in o)
    # O `mat_khau` phai che; `ten_dang_nhap` khong phai bi mat nen de nhin.
    assert dict((x["ten"], x["che"]) for x in o) == {
        "ten_dang_nhap": False, "mat_khau": True}


# ── 🔴 Quet bao mat: khong mot phan hoi nao mang khoa META_CAM ────────────

def _moi_phan_hoi(api: TestClient) -> list[tuple[str, str]]:
    """(nhan, than tho) cua MOI cua mo-dun nay, ke ca cac cua LOI.

    ⛔ Khong liet ke tay tung truong cua tung cua: mot truong moi them vao mot
       cua la dung cho mot phep liet ke tay thoi bao gi.
    """
    ref = _tao(api, meta={"email": "ai@example.com"}).json()["id"]
    csrf = _csrf(api)
    ra = [
        ("tao", _tao(api, kieu="bearer", ten="B",
                     bi_mat={"gia_tri": BI_MAT}).text),
        ("liet_ke", api.get("/agent/api/v3/ket-noi").text),
        ("liet_ke_loc", api.get("/agent/api/v3/ket-noi?kieu=api_key").text),
        ("nha_cung_cap", api.get("/agent/api/v3/ket-noi/nha-cung-cap").text),
        ("tao_loi_meta", _tao(api, meta={"password": "p"}).text),
        ("tao_loi_bi_mat", _tao(api, bi_mat={"sai": "x"}).text),
        ("thu_hoi", api.request("DELETE", f"/agent/api/v3/ket-noi/{ref}",
                                json={"csrf_token": csrf},
                                headers={"X-CSRF-Token": csrf}).text),
    ]
    return ra


#: Nhanh DUY NHAT duoc mien: `khoa_bi_mat` cua `/nha-cung-cap` la mot **so tra
#: cuu** duoc KHOA THEO `kieu` (`api_key`, `oauth2`, …) va gia tri la TEN o cua
#: form. Do la ten TRUONG, khong phai gia tri nao. ⛔ Mot mien tru bang chuoi
#: (`"api_key" khong tinh`) thi ap cho CA cac cua khac — mien tru phai chi dung
#: mot nhanh cua mot cua.
_MIEN_TRU = {("nha_cung_cap", "khoa_bi_mat")}


def _moi_khoa(nhan: str, gia, duong=()) -> set[str]:
    """Moi khoa dict trong mot cay JSON, TRU cac nhanh duoc mien tru."""
    ra: set[str] = set()
    if isinstance(gia, dict):
        for k, v in gia.items():
            if (nhan, *duong, str(k)) in _MIEN_TRU:
                continue
            ra.add(str(k))
            ra |= _moi_khoa(nhan, v, (*duong, str(k)))
    elif isinstance(gia, list):
        for v in gia:
            ra |= _moi_khoa(nhan, v, duong)
    return ra


def test_khong_mot_phan_hoi_nao_chua_khoa_META_CAM(api):
    from platform_core import credential as kho
    for nhan, tho in _moi_phan_hoi(api):
        # ⚠️ Doc KHOA cua cay JSON, khong tim chuoi trong van ban tho: `api_key`
        #    cung la mot GIA TRI hop le cua truong `kieu`, va `META_CAM` la luat
        #    ve KHOA. Mot phep so van ban bat ca hai ca — no khong sai ve bao
        #    mat, no do mot dieu KHAC, va roi nguoi ta se tat no di.
        khoa = {k.lower() for k in _moi_khoa(nhan, json.loads(tho))}
        xau = sorted(khoa & set(kho.META_CAM))
        assert not xau, f"cua {nhan} tra khoa bi cam: {xau}\n{tho[:400]}"
        thap = tho.lower()
        assert "bi_mat_ma_hoa" not in thap, f"cua {nhan} tra cot da ma hoa"
        assert BI_MAT.lower() not in thap, f"cua {nhan} tra BAN RO"


def test_doi_chung_bo_quet_THAT_SU_doc_duoc_than_phan_hoi(api):
    """🔑 Doi chung: neu `_moi_phan_hoi` tra chuoi rong thi bai tren xanh vi no
    khong doc gi ca."""
    ds = _moi_phan_hoi(api)
    assert len(ds) == 7
    # Moi phan hoi phai la JSON co it nhat mot khoa — mot chuoi rong hay mot
    # `null` thi bai tren xanh vi khong co gi de doc.
    for nhan, tho in ds:
        assert _moi_khoa(nhan, json.loads(tho)), f"cua {nhan} tra than rong"
    # Va bo quet PHAI bat duoc mot khoa bi cam khi no that su co mat — bang
    # CHINH ham ma bai tren dung, khong mot phep long hon.
    from platform_core import credential as kho
    gia = {"meta": {"refresh_token": "x"}}
    assert _moi_khoa("liet_ke", gia) & set(kho.META_CAM) == {"refresh_token"}
    # ...va mien tru PHAI hep dung mot nhanh: cung cay do o mot cua khac thi
    # van bi bat.
    assert _moi_khoa("nha_cung_cap", {"khoa_bi_mat": {"api_key": []}}) == set()
    assert "api_key" in _moi_khoa("liet_ke", {"khoa_bi_mat": {"api_key": []}})
