"""
test_254 — `image.ltt` chạy thật qua `/api/v1`, từ ngoài vào. (H37/A9)

Đây là thứ mà `test_253` **không** chứng minh được. `test_253` đọc manifest và
catalog; tệp này bắt một khoá lập trình viên thật gọi vào HTTP thật.

**Không cần GPU, không cần máy B, không cần credit** — nhờ khoá **chế độ thử**
(`mode="test"`), thứ đã được dựng sẵn cho đúng việc này (EXT-12). Nó cũng có nghĩa
là tệp này chứng minh **hợp đồng**, không chứng minh model vẽ đẹp.

⛔ Công tắc `LTT_PUBLIC_API_TOOLS` ở đây **chỉ mở trong tiến trình test**. Nó không
   đụng gì tới production: production đọc `secrets/app.env`, nơi biến này vẫn rỗng.
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from server.api.inventory import API_V1_PREFIX

PEPPER = "anhnoibo-e2e-pepper-" + "n" * 40
TOOL = "image.ltt"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read",
          "uploads:write", "usage:read")
#: Header PNG tối thiểu, đủ để qua vòng kiểm magic-byte của tầng upload.
#:
#: Viết thành hai mảnh có tên, KHÔNG viết một chuỗi hex 32 ký tự liền: bộ quét bí
#: mật bắt mọi chuỗi hex 32 ký tự trần vì đó đúng là hình dạng của một khoá bị lộ,
#: và nó không có cách nào biết chuỗi này chỉ là mấy byte đầu của một tấm ảnh.
#: Cũng không viết bằng escape `\\x89…`: khi tệp test được sinh ra bằng script thì
#: một tầng thoát chuỗi nữa biến chúng thành byte NUL thật, và cả tệp hết parse.
PNG_CHU_KY = bytes.fromhex("89504e47") + bytes.fromhex("0d0a1a0a")
PNG = PNG_CHU_KY + bytes.fromhex("0000000d") + b"IHDR" + bytes(40)


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'e2e.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "anhnoibo-e2e-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": TOOL,
        "LTT_PUBLIC_API_RPM": "600", "LTT_PUBLIC_API_CREATE_RPM": "300",
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    storage_mod.set_storage(None)
    limits.reset()
    dbmod.reset_engine()


def _csrf(html: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _sign_in(client) -> str:
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    email = f"e2e-{uuid.uuid4().hex[:6]}@example.com"
    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 500, by="test")
        db.commit()
        user_id = user.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    page = client.get("/login").text
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)
    return user_id


def _issue(client, mode: str = "test") -> str:
    page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": f"{mode} key", "mode": mode,
                                "csrf_token": _csrf(page),
                                "scopes": list(SCOPES)})
    found = re.search(r"<code>(ltt_[st]k_[^<]+)</code>", created.text)
    assert found, created.text[:400]
    return found.group(1)


@pytest.fixture()
def token(portal):
    _sign_in(portal)
    return _issue(portal)


def _auth(token: str, idem: str = "") -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if idem:
        h["Idempotency-Key"] = idem
    return h


# ───────────────── tool nhìn thấy được từ ngoài ─────────────────────────────
def test_khach_liet_ke_duoc_tool(portal, token):
    r = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert r.status_code == 200
    assert TOOL in [t["name"] for t in r.json()["items"]]


def test_khach_doc_duoc_hop_dong_day_du_cua_tool(portal, token):
    r = portal.get(f"{API_V1_PREFIX}/tools/{TOOL}", headers=_auth(token))
    assert r.status_code == 200
    d = r.json()
    thuoc_tinh = d["input_schema"]["properties"]
    assert "prompt" in thuoc_tinh and "mode" in thuoc_tinh
    # Tham số ẩn phải KHÔNG lọt ra — đây là chỗ một hợp đồng sai sẽ hứa thừa.
    assert "image_keys" not in thuoc_tinh
    assert "model" not in thuoc_tinh


def test_khong_id_model_noi_bo_nao_lot_ra_hop_dong(portal, token):
    """Tên model thật là tài sản (bảo mật chống dịch ngược). Khách thấy `image.ltt`,
    không thấy `hidream-o1`."""
    r = portal.get(f"{API_V1_PREFIX}/tools/{TOOL}", headers=_auth(token))
    assert "hidream" not in r.text.lower()


def _upload(client, token: str, field: str = "image_key") -> str:
    """Đưa một ảnh vào đúng bằng đường khách ngoài phải đi: xin chỗ → đẩy nội dung
    → xác nhận. Trả về id để đặt vào tham số media."""
    created = client.post(f"{API_V1_PREFIX}/uploads",
                          json={"tool": TOOL, "field": field, "filename": "in.png",
                                "content_type": "image/png", "size": len(PNG)},
                          headers=_auth(token))
    assert created.status_code == 201, created.text
    upload_id = created.json()["id"]
    client.post(f"{API_V1_PREFIX}/uploads/{upload_id}/content",
                files={"file": ("in.png", PNG, "image/png")}, headers=_auth(token))
    client.post(f"{API_V1_PREFIX}/uploads/{upload_id}/confirm", headers=_auth(token))
    return upload_id


# ───────────────── báo giá: khách biết trước phải trả bao nhiêu ─────────────
def _quote(portal, token, dau_vao: dict):
    return portal.post(f"{API_V1_PREFIX}/quotes",
                       json={"tool": TOOL, "input": dau_vao}, headers=_auth(token))


def test_bao_gia_truoc_khi_chay(portal, token):
    r = _quote(portal, token, {"prompt": "a lighthouse at dawn"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["credit"] > 0 and d["quote"] and d["tool"] == TOOL


def test_che_do_dung_anh_tham_chieu_bao_gia_DAT_HON(portal, token):
    """Giá phải phản ánh thời gian máy, và khách phải thấy điều đó **trước** khi chạy."""
    re_ = _quote(portal, token, {"prompt": "x", "mode": "t2i"})
    dat = _quote(portal, token, {"prompt": "x", "mode": "subject",
                                 "image_key": _upload(portal, token)})
    assert re_.status_code == 200, re_.text
    assert dat.status_code == 200, dat.text
    assert re_.json()["credit"] < dat.json()["credit"]


def test_bao_gia_nhan_theo_count(portal, token):
    mot = _quote(portal, token, {"prompt": "x", "count": 1})
    bon = _quote(portal, token, {"prompt": "x", "count": 4})
    assert mot.status_code == 200 and bon.status_code == 200, bon.text
    assert bon.json()["credit"] == 4 * mot.json()["credit"]


# ───────────────── nộp việc: đi hết đường vào hàng đợi ──────────────────────
def test_nop_viec_duoc_va_job_vao_hang_doi(portal, token):
    dau_vao = {"prompt": "a lighthouse at dawn"}
    bao_gia = _quote(portal, token, dau_vao).json()["quote"]
    r = portal.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "input": dau_vao, "quote": bao_gia},
                    headers=_auth(token, idem=uuid.uuid4().hex))
    assert r.status_code in (200, 201, 202), r.text
    job = r.json()
    assert job.get("id")

    got = portal.get(f"{API_V1_PREFIX}/jobs/{job['id']}", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["tool"] == TOOL


def test_goi_lai_cung_Idempotency_Key_KHONG_tao_job_thu_hai(portal, token):
    """Khách thử lại sau một cú vấp mạng là chuyện thường. Tạo hai job là **tính
    tiền hai lần** cho một yêu cầu."""
    idem = uuid.uuid4().hex
    dau_vao = {"prompt": "a lighthouse at dawn"}
    than = {"tool": TOOL, "input": dau_vao,
            "quote": _quote(portal, token, dau_vao).json()["quote"]}
    a = portal.post(f"{API_V1_PREFIX}/jobs", json=than, headers=_auth(token, idem))
    b = portal.post(f"{API_V1_PREFIX}/jobs", json=than, headers=_auth(token, idem))
    assert a.status_code in (200, 201, 202), a.text
    assert a.json()["id"] == b.json()["id"]


# ───────────────── hợp đồng từ chối đúng thứ phải từ chối ───────────────────
def test_nop_viec_CO_ANH_THAM_CHIEU_di_het_duong(portal, token):
    """Nhánh đắt nhất, và là nhánh khác biệt của model này. Nếu nó chỉ chạy được
    trong lý thuyết thì `edit`/`subject` là một lời hứa suông."""
    dau_vao = {"prompt": "same person, on a beach", "mode": "subject",
               "image_key": _upload(portal, token)}
    bao_gia = _quote(portal, token, dau_vao)
    assert bao_gia.status_code == 200, bao_gia.text
    r = portal.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "input": dau_vao,
                          "quote": bao_gia.json()["quote"]},
                    headers=_auth(token, idem=uuid.uuid4().hex))
    assert r.status_code in (200, 201, 202), r.text
    assert r.json().get("id")


def test_upload_cua_NGUOI_KHAC_khong_dung_duoc(portal):
    """Hai tài khoản, một upload. Tài khoản thứ hai không được mượn ảnh của người
    thứ nhất chỉ bằng cách biết id."""
    _sign_in(portal)
    token_a = _issue(portal)
    cua_a = _upload(portal, token_a)
    portal.get("/logout")
    _sign_in(portal)
    token_b = _issue(portal)
    r = _quote(portal, token_b, {"prompt": "x", "mode": "edit", "image_key": cua_a})
    assert r.status_code in (400, 403, 404), r.text


def test_tham_so_la_bi_TU_CHOI_chu_khong_bi_bo_qua(portal, token):
    """Bỏ qua một tham số viết sai chính tả là để khách trả tiền cho một job đã
    lặng lẽ phớt lờ điều họ yêu cầu."""
    r = portal.post(f"{API_V1_PREFIX}/quotes",
                    json={"tool": TOOL, "input": {"prompt": "x", "modee": "edit"}},
                    headers=_auth(token))
    assert r.status_code == 400, r.text


def test_tham_so_AN_khong_dat_duoc_tu_ngoai(portal, token):
    """`image_keys` bị ẩn. Khách đặt được nó nghĩa là hợp đồng công khai chỉ là
    trang trí."""
    r = portal.post(f"{API_V1_PREFIX}/quotes",
                    json={"tool": TOOL,
                          "input": {"prompt": "x", "image_keys": ["a/b/c"]}},
                    headers=_auth(token))
    assert r.status_code == 400, r.text


def test_count_vuot_tran_bi_TU_CHOI(portal, token):
    r = portal.post(f"{API_V1_PREFIX}/quotes",
                    json={"tool": TOOL, "input": {"prompt": "x", "count": 99}},
                    headers=_auth(token))
    assert r.status_code == 400, r.text


def test_thieu_prompt_bi_TU_CHOI(portal, token):
    r = portal.post(f"{API_V1_PREFIX}/quotes",
                    json={"tool": TOOL, "input": {"mode": "t2i"}},
                    headers=_auth(token))
    assert r.status_code == 400, r.text


def test_khoa_thieu_scope_KHONG_nop_duoc_viec(portal):
    """Scope là hợp đồng, không phải trang trí."""
    _sign_in(portal)
    page = portal.get("/developers/keys").text
    created = portal.post("/developers/keys",
                          data={"name": "chi doc", "mode": "test",
                                "csrf_token": _csrf(page),
                                "scopes": ["tools:read"]})
    chi_doc = re.search(r"<code>(ltt_[st]k_[^<]+)</code>", created.text).group(1)
    r = portal.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "input": {"prompt": "x"}},
                    headers=_auth(chi_doc, idem=uuid.uuid4().hex))
    assert r.status_code == 403, r.text
