"""Tầng TRANG của lưu trữ — khung nhìn `?luu_tru=1` và đường về.

## ⚠️ Vì sao tệp này tồn tại tách khỏi `test_5603`

`test_5603` chứng minh **cửa HTTP** đặt và xoá được `archived_at`. Nó ⛔ không
nói gì về việc người dùng **với tới** được cửa ấy hay không — và đó chính là nửa
dễ mất: một cửa POST đúng đắn sau một trang ⛔ không có nút nào là một cửa ⛔
không ai bấm.

Ba mệnh đề ở đây, cả ba đều về **đường đi của người dùng**, không về CSDL:

1. Danh sách chính ⛔ không hiện bản đã lưu trữ, nhưng `?luu_tru=1` thì hiện.
2. `tong` đếm trong **cùng khung nhìn** đang hiển thị — một con số đếm bản đang
   dùng trong lúc trang hiện kho sẽ nói ngược với danh sách ngay dưới nó.
3. Kho **có lối vào** khi nó có gì, và **có lối về** khi đang ở trong nó.

## 🔴 Mệnh đề 3 là mệnh đề đắt nhất

Một workflow đã lưu trữ biến mất khỏi danh sách chính — đó là cả ý nghĩa của nó.
Nếu lối vào kho không được vẽ ra, người dùng mất workflow mà ⛔ không ai xoá gì
cả, và họ ⛔ không có cách nào biết nó còn đó. Nút *Mở lại* khi ấy tồn tại trong
mã mà ⛔ không tồn tại trên đường đi.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


_MAT_KHAU = "Strong-pass-123"
_EMAIL = "kho-luu-tru@example.com"


class _Web:
    def __init__(self, client: TestClient, csrf: str, user_id: str):
        self.client, self.csrf, self.user_id = client, csrf, user_id

    def tao(self, ten: str) -> str:
        r = self.client.post("/agent/api/v3/workflows",
                             json={"name": ten, "csrf_token": self.csrf})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def luu_tru(self, wf_id: str) -> None:
        r = self.client.post(f"/agent/api/v3/workflows/{wf_id}/luu-tru",
                             json={"csrf_token": self.csrf})
        assert r.status_code == 200, r.text

    def trang(self, *, kho: bool = False, q: str = "") -> str:
        duong = "/agent/workflows"
        tham = ([("luu_tru", "1")] if kho else []) + ([("q", q)] if q else [])
        if tham:
            duong += "?" + "&".join(f"{k}={v}" for k, v in tham)
        r = self.client.get(duong)
        assert r.status_code == 200, r.text
        return r.text


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'kho.db').as_posix()}")
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
    cfg.write_text(json.dumps({}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "test-5604-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    with TestClient(app, base_url="https://testserver",
                    follow_redirects=True) as client:
        tok = re.search(r'name="csrf_token" value="([^"]+)"',
                        client.get("/login").text)
        assert tok, "khong lay duoc csrf o /login"
        assert client.post("/login", data={
            "username": _EMAIL, "password": _MAT_KHAU,
            "csrf_token": tok.group(1), "next": "/agent/canvas"},
        ).status_code == 200
        canvas = client.get("/agent/canvas")
        csrf = re.search(r'data-csrf-token="([^"]+)"', canvas.text)
        assert csrf, f"/agent/canvas khong in csrf ({canvas.status_code})"
        yield _Web(client, csrf.group(1), user_id)
    dbmod.reset_engine()


# ── 1. Hai khung nhìn là hai TẬP ────────────────────────────────────────────

def test_hai_khung_nhin_chia_doi_danh_sach(web):
    a, b = web.tao("con dung"), web.tao("da cat")
    web.luu_tru(b)

    chinh = web.trang()
    assert f'data-wf-id="{a}"' in chinh
    assert f'data-wf-id="{b}"' not in chinh, "ban da luu tru con o danh sach chinh"

    kho = web.trang(kho=True)
    assert f'data-wf-id="{b}"' in kho
    assert f'data-wf-id="{a}"' not in kho, "kho hien ca ban dang dung"


def test_tong_dem_trong_CUNG_khung_nhin(web):
    """⚠️ Không có bài này, `tong` có thể đếm bản đang dùng trong lúc trang hiện
    kho — con số sẽ nói ngược với danh sách ngay bên dưới nó."""
    for ten in ("a", "b", "c"):
        web.tao(ten)
    cat = web.tao("d")
    web.luu_tru(cat)

    assert "<b>3</b>" in web.trang(), "danh sach chinh dem ca ban da luu tru"
    assert "<b>1</b>" in web.trang(kho=True), "kho dem theo khung nhin khac"


# ── 2. Lối vào và lối về ────────────────────────────────────────────────────

def test_KHO_RONG_thi_khong_ve_loi_vao(web):
    """Một liên kết tới một trang rỗng là một lời mời bấm vào hư không."""
    web.tao("con dung")
    assert "luu_tru=1" not in web.trang()


def test_co_ban_trong_kho_thi_CO_loi_vao(web):
    """🔴 Bài đắt nhất ở đây. Không có lối vào, nút *Mở lại* tồn tại trong mã mà
    ⛔ không tồn tại trên đường đi của người dùng — và workflow đã lưu trữ thì
    ⛔ không còn ở danh sách nào để tìm lại."""
    web.tao("con dung")
    web.luu_tru(web.tao("da cat"))

    chinh = web.trang()
    assert "/agent/workflows?luu_tru=1" in chinh, \
        "co ban trong kho ma trang chinh khong co duong vao kho"
    assert "(1)" in chinh, "loi vao khong noi trong kho co bao nhieu ban"


def test_trong_kho_thi_co_loi_VE_va_KHONG_co_nut_tao(web):
    """Kho là nơi tìm lại, không phải nơi dựng mới. Một nút *Workflow mới* ở đây
    sẽ tạo ra một bản **đang dùng** rồi biến mất khỏi chính trang vừa bấm."""
    web.luu_tru(web.tao("da cat"))
    kho = web.trang(kho=True)
    assert 'href="/agent/workflows"' in kho, "trong kho ma khong co duong ve"
    assert 'id="wfl-tao"' not in kho, "kho van hien nut tao workflow moi"


# ── 3. Hành động đúng theo khung nhìn ───────────────────────────────────────

def test_nut_theo_dung_khung_nhin(web):
    a = web.tao("con dung")
    b = web.tao("da cat")
    web.luu_tru(b)

    chinh = web.trang()
    assert f'data-wfl-luu-tru="{a}"' in chinh
    # ⚠️ Phải có dấu `="`. Chuỗi `data-wfl-mo-lai` TRẦN khớp cả bảng bộ chọn
    #    trong `<script>` — bảng đó có mặt ở CẢ HAI khung nhìn, nên một phép đo
    #    không có dấu `=` sẽ đo *"trang có nhắc tên thuộc tính này không"*, chứ
    #    ⛔ KHÔNG đo *"trang có vẽ nút này không"*. Lượt chạy đầu (28/09) đỏ
    #    đúng ở đây: phép đo chạy đúng, nhưng nó trả lời một câu HỎI KHÁC.
    assert 'data-wfl-mo-lai="' not in chinh, "danh sach chinh hien nut Mo lai"

    kho = web.trang(kho=True)
    assert f'data-wfl-mo-lai="{b}"' in kho
    assert 'data-wfl-luu-tru="' not in kho, "kho hien nut Luu tru mot lan nua"
    assert 'data-wfl-nhan-ban="' not in kho, \
        "nhan ban trong kho se sinh mot ban DANG DUNG tu mot trang kho"


def test_tim_theo_ten_van_chay_TRONG_kho(web):
    """`q` và `luu_tru` là hai tham số độc lập. Nếu tìm chỉ chạy ở danh sách
    chính thì một kho lớn ⛔ không có cách nào lần ra một cái tên."""
    web.luu_tru(web.tao("bao cao thang chin"))
    web.luu_tru(web.tao("dich phu de"))

    ket_qua = web.trang(kho=True, q="phu de")
    assert "dich phu de" in ket_qua
    assert "bao cao thang chin" not in ket_qua


# ── 4. Ranh giới chủ sở hữu ở TẦNG TRANG ────────────────────────────────────

def test_kho_khong_lo_workflow_cua_nguoi_khac(web):
    """`?luu_tru=1` mở một mệnh đề WHERE mới — nên nó phải được đo lại ở đây,
    ⛔ không suy ra từ việc danh sách chính đã đúng."""
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung
    from platform_core.workflow import dinh_nghia

    db = next(dbmod.get_session())
    try:
        khac = tao_nguoi_dung(db, email="khac-kho@example.com",
                              password=_MAT_KHAU, is_verified=True)
        wf = dinh_nghia.tao_workflow(db, owner_id=khac.id, name="cua nguoi khac")
        db.flush()
        wf.archived_at = datetime.now(timezone.utc)
        db.commit()
        lac = wf.id
    finally:
        db.close()

    assert f'data-wf-id="{lac}"' not in web.trang(kho=True)
    assert "cua nguoi khac" not in web.trang(kho=True)
