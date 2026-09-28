"""UI-9 — danh mục MẪU (`apps/agent/mau.py`) + trang `/agent/templates`.

## Mệnh đề tệp này canh

1. **Mỗi mẫu publish được THẬT** — qua `dinh_nghia.xuat_ban_draft` (không chỉ
   `bien_dich.bien_dich` đứng một mình), và số credit trả về khớp
   `Mau.toi_da` tính lúc `mau.py` nạp.
2. **`/agent/templates` không còn là DAT_CHO** — trang không nói "Đang xây",
   và liệt kê đúng tên/mô tả các mẫu.
3. **"Dùng mẫu này" tạo một workflow THẬT** qua cửa `POST /agent/api/v3/…`
   đã có — ⛔ không cửa HTTP mới — với ĐÚNG `document` của mẫu, rồi mở được
   đúng workflow đó (không phải `items[0]`).
4. **CSRF thiếu ⇒ không tạo gì** — cùng luật với "Nhân bản"/"Workflow mới".

⚠️ Phạm vi: tệp này đo MÁY CHỦ (HTTP + `dinh_nghia`). Nghiệm thu trên trình
   duyệt thật ở `tests/browser/agent_ui_v2_ui9_nghiem_thu.js`.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from platform_core.workflow import bien_dich

from apps.agent import mau


# ── 1. Bản thân danh mục — không qua HTTP ───────────────────────────────────

def test_co_it_nhat_mot_mau():
    assert len(mau.tat_ca()) >= 1


@pytest.mark.parametrize("m", mau.tat_ca(), ids=lambda m: m.id)
def test_moi_mau_bien_dich_sach(m):
    """Lặp lại phép mà `mau.py` đã làm lúc IMPORT — đo lại, không tin lời hứa
    của module (một chỗ nuốt lỗi lặng lẽ ở đâu đó sẽ không lộ ra nếu chỉ tin
    `mau.tat_ca()` trả về không rỗng)."""
    graph = bien_dich.bien_dich(m.document)
    assert graph["nodes"], m.id
    assert m.toi_da > 0, m.id


@pytest.mark.parametrize("m", mau.tat_ca(), ids=lambda m: m.id)
def test_moi_mau_chi_dung_node_khong_doi_credential(m):
    """Node `connector.*`/`piece.*` cần credential khách CHƯA cấu hình
    (`/agent/connections` vẫn là DAT_CHO) — một mẫu dùng chúng thì "sửa được
    ngay" chỉ đúng cho biên dịch, sai cho việc bấm Chạy thử. Chốt tại đây để
    một mẫu sau này KHÔNG lặng lẽ thêm một node như vậy."""
    xau = ("connector.", "piece.")
    for loai in m.loai_node:
        assert not loai.startswith(xau), f"{m.id}: {loai}"


# ── 2 & 3. Trang + luồng "Dùng mẫu này" — qua HTTP thật ─────────────────────

def _csrf(html: str) -> str:
    # ⭐ Menu tài khoản (`server/templates/_menu_tai_khoan.html`) nhúng một
    #    `input[name=csrf_token]` trên MỌI trang qua `base.html` — cùng cách
    #    `test_6200_agent_automation_studio_ia.py` đọc token, khác trang
    #    Canvas (nơi có `data-csrf-token` riêng cho React).
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "khong tim thay csrf_token trong trang"
    return match.group(1)


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ui9-mau.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="ui9@example.com", password="Strong-pass-123",
                   is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ui9-mau-test-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "ui9@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/agent/templates"}).status_code == 200
    yield client, _csrf(client.get("/agent/templates").text)
    client.close(); dbmod.reset_engine()


def test_trang_khong_con_noi_dang_xay(web):
    """⚠️ Chuỗi "Đang xây" CÒN xuất hiện trên trang — nó ở NAV, cho các mục
    khác (`/agent/runs` v.v.) vẫn là DAT_CHO. Mốc đúng của MỘT trang đặt chỗ
    là `data-dang-xay="1"` (`agent_dang_xay.html`) — trang thật không render
    khối đó."""
    client, _ = web
    trang = client.get("/agent/templates")
    assert trang.status_code == 200
    assert 'data-dang-xay' not in trang.text


def test_trang_liet_ke_dung_ten_va_credit_moi_mau(web):
    client, _ = web
    html = client.get("/agent/templates").text
    for m in mau.tat_ca():
        assert m.id in html
        assert str(m.toi_da) in html


def test_dat_cho_KHONG_con_templates():
    from apps.agent.routes.trang import DAT_CHO
    assert "/templates" not in [d[0] for d in DAT_CHO]


def test_bam_dung_mau_tao_workflow_that_voi_dung_document(web):
    client, token = web
    m = mau.tat_ca()[0]
    truoc = client.get("/agent/api/v3/workflows").json()["items"]
    assert truoc == []

    r = client.post("/agent/api/v3/workflows",
                    headers={"X-CSRF-Token": token},
                    json={"name": m.ten, "document": m.document,
                          "csrf_token": token})
    assert r.status_code == 201, r.text
    wf = r.json()
    assert wf["document"] == m.document

    sau = client.get("/agent/api/v3/workflows").json()["items"]
    assert len(sau) == 1 and sau[0]["id"] == wf["id"]

    # Mo dung workflow VUA TAO — khong phai `items[0]` cua mot danh sach khac.
    trang = client.get(f"/agent/workflows/{wf['id']}")
    assert trang.status_code == 200
    assert f'data-workflow-id="{wf["id"]}"' in trang.text


def test_mo_dung_id_khi_co_HAI_workflow_tu_mau(web):
    """Tạo hai workflow từ hai mẫu khác nhau — mở workflow ĐẦU phải vẫn ra
    đúng nó, dù nó không còn là bản mới nhất (`updated_at DESC`)."""
    client, token = web
    ms = mau.tat_ca()
    m0 = ms[0]
    m1 = ms[1] if len(ms) > 1 else ms[0]

    def _tao(m):
        r = client.post("/agent/api/v3/workflows",
                        headers={"X-CSRF-Token": token},
                        json={"name": m.ten, "document": m.document,
                              "csrf_token": token})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    id_dau = _tao(m0)
    id_sau = _tao(m1)
    assert id_dau != id_sau

    trang = client.get(f"/agent/workflows/{id_dau}")
    assert trang.status_code == 200
    assert f'data-workflow-id="{id_dau}"' in trang.text
    assert f'data-workflow-id="{id_sau}"' not in trang.text


def test_csrf_thieu_khong_tao_gi(web):
    client, _token_khong_dung = web
    m = mau.tat_ca()[0]
    r = client.post("/agent/api/v3/workflows",
                    json={"name": m.ten, "document": m.document})
    assert r.status_code in (400, 403, 422), r.text
    assert client.get("/agent/api/v3/workflows").json()["items"] == []


# ── 4. `dinh_nghia.xuat_ban_draft` THẬT cho từng mẫu ────────────────────────

@pytest.mark.parametrize("m", mau.tat_ca(), ids=lambda m: m.id)
def test_publish_that_qua_cua_v3_khop_gia_da_tinh(web, m):
    """`POST …/publish` gọi ĐÚNG `dinh_nghia.xuat_ban_draft` — không phải một
    phép biên dịch đứng riêng ở test. `credit_max` trả về phải khớp `m.toi_da`
    (cùng đồ thị, cùng bảng giá registry)."""
    client, token = web
    r = client.post("/agent/api/v3/workflows",
                    headers={"X-CSRF-Token": token},
                    json={"name": m.ten, "document": m.document,
                          "csrf_token": token})
    assert r.status_code == 201, r.text
    wf_id = r.json()["id"]

    r2 = client.post(f"/agent/api/v3/workflows/{wf_id}/publish",
                     headers={"X-CSRF-Token": token},
                     json={"csrf_token": token})
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["credit_max"] == m.toi_da
    assert body["version_id"]
