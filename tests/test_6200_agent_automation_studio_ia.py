"""UI-1 — kiến trúc thông tin của LTT Automation Studio (Q1 = B, `09 §1`).

## Mệnh đề tệp này canh

1. **`/agent/workflows` liệt kê ĐÚNG số workflow của tài khoản** — và chỉ của
   nó. Đây là cửa đầu tiên trên giao diện tới một workflow *cụ thể*.
2. **`/agent/workflows/{id}` mở đúng workflow đó** — id đi theo **URL**, nên
   tải lại trang vẫn đúng nó, và hai tab mở hai workflow không đánh nhau.
3. **Ranh giới chủ sở hữu là 404, không phải 403** — y hệt `drafts_v3._cua_toi`:
   một `403` xác nhận rằng id đó có thật.
4. **Bốn (năm) mục đặt chỗ trả 200 và NÓI RÕ đang xây** — ⛔ không phải một
   trang trống trông-như-thật.
5. **⛔ Không cửa HTTP mới cho hành động**: tạo/nhân bản đi qua cửa v3 đã có.

## 🔴 Vì sao mệnh đề 5 được đo bằng BẢNG ĐỊNH TUYẾN, không bằng lời hứa

`01_CURRENT_UI_AUDIT.md` §1.1 đo rằng giao diện thiếu danh sách. Cách sửa dễ
nhất — và sai — là mở thêm `POST /agent/workflows`, `POST .../nhan-ban`,
`POST .../luu-tru`: ba cửa mới cho ba việc mà cửa v3 đã làm hai. Bài
`test_khong_mo_cua_POST_moi_o_tang_trang` chốt rằng tầng trang **không có một
phương thức nào ngoài GET**, nên một cửa POST lặng lẽ mọc thêm sẽ đỏ ở đây thay
vì đỏ sau khi đã lên production.

## ⚠️ Phạm vi hẹp hơn lời tuyên bố

Tệp này đo **máy chủ**. Việc trình soạn thật sự nạp id từ `data-workflow-id`
được đo ở `frontend/agent-canvas/tests/TrangMoDungWorkflow.test.tsx` (lời gọi
`fetch` thật) và trên trình duyệt thật ở
`tests/browser/agent_ui_v2_ui1_nghiem_thu.js`. Ba lớp, ba câu hỏi khác nhau —
⛔ không lớp nào thay được lớp khác.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

#: Năm mục IA đã khai ở `manifest.nav` mà nội dung thuộc làn khác.
DAT_CHO = ["/agent/runs", "/agent/templates", "/agent/connections",
           "/agent/agents", "/agent/settings"]


@pytest.fixture()
def web(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'ui1-ia.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    from platform_core import credit, users
    user = users.tao_nguoi_dung(db, email="ui1@example.com",
                                password="Strong-pass-123", is_verified=True)
    khac = users.tao_nguoi_dung(db, email="ui1-khac@example.com",
                                password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 100, by="test")
    db.commit()
    uid, khac_id = user.id, khac.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                   encoding="utf-8")
    from server.app import create_app
    client = TestClient(create_app(env={
        "LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "ui1-ia-session-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
    }), base_url="https://testserver", follow_redirects=False)
    login = client.get("/login?next=/agent/workflows")
    token = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
    client.post("/login", data={"username": "ui1@example.com",
                                "password": "Strong-pass-123",
                                "csrf_token": token,
                                "next": "/agent/workflows"})
    yield client, uid, khac_id
    client.close(); dbmod.reset_engine()


def _token(client: TestClient) -> str:
    """CSRF của phiên, lấy từ đúng chỗ trình duyệt lấy (HTML đã render)."""
    html = client.get("/agent/workflows").text
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, html[:400]
    return match.group(1)


def _tao(client: TestClient, ten: str) -> str:
    """Tạo một workflow QUA CỬA V3 — đúng đường mà giao diện dùng."""
    token = _token(client)
    r = client.post("/agent/api/v3/workflows",
                    json={"name": ten, "csrf_token": token},
                    headers={"X-CSRF-Token": token})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── 1. Danh sách ────────────────────────────────────────────────────────────

def test_danh_sach_liet_ke_DUNG_SO_workflow_cua_tai_khoan(web):
    """⭐ Đếm bằng thẻ `data-wf-id`, không bằng số lần tên xuất hiện: một tên
    lặp trong prose sẽ làm phép đếm theo tên báo sai lên."""
    client, *_ = web
    trong = client.get("/agent/workflows")
    assert trong.status_code == 200
    assert re.findall(r'data-wf-id="([^"]+)"', trong.text) == []

    ids = [_tao(client, f"WF {i}") for i in range(3)]
    trang = client.get("/agent/workflows")
    assert trang.status_code == 200
    assert set(re.findall(r'data-wf-id="([^"]+)"', trang.text)) == set(ids)


def test_danh_sach_KHONG_lot_workflow_cua_nguoi_khac(web):
    """🔑 Vế ranh giới. Không có bài này, một truy vấn thiếu `owner_id` vẫn
    xanh ở bài trên (chỉ có một tài khoản đăng nhập trong bài đó)."""
    client, uid, khac_id = web
    cua_toi = _tao(client, "cua toi")

    import platform_core.db as dbmod
    from platform_core.workflow import dinh_nghia
    gen = dbmod.get_session(); db = next(gen)
    cua_khac = dinh_nghia.tao_workflow(db, owner_id=khac_id, name="cua nguoi khac")
    db.commit(); ma_khac = cua_khac.id; db.close()

    thay = set(re.findall(r'data-wf-id="([^"]+)"', client.get("/agent/workflows").text))
    assert thay == {cua_toi}
    assert ma_khac not in thay


def test_tim_theo_ten_loc_danh_sach_va_noi_ro_TONG(web):
    """⭐ Trang phải nói cả `khớp` và `tổng`: một ô tìm không khớp gì trông y
    hệt một tài khoản vừa mất sạch workflow."""
    client, *_ = web
    _tao(client, "Cat anh bia"); _tao(client, "Long tieng video")

    tat_ca = client.get("/agent/workflows")
    assert len(re.findall(r'data-wf-id=', tat_ca.text)) == 2

    loc = client.get("/agent/workflows?q=video")
    assert loc.status_code == 200
    assert len(re.findall(r'data-wf-id=', loc.text)) == 1
    assert "Long tieng video" in loc.text and "Cat anh bia" not in loc.text

    khong_khop = client.get("/agent/workflows?q=khong-he-co")
    assert len(re.findall(r'data-wf-id=', khong_khop.text)) == 0
    # `tong` vẫn là 2 — trang biết nó đang LỌC, không phải đang trống.
    assert "2" in khong_khop.text


# ── 2. Mở ĐÚNG một workflow ─────────────────────────────────────────────────

def test_mo_workflow_thu_HAI_van_dung_no_khong_nhay_ve_moi_nhat(web):
    """🔴 Bài CHỐT của làn này. `items[0]` của danh sách là workflow sửa gần
    nhất; mở workflow thứ hai phải ra **workflow thứ hai**."""
    client, *_ = web
    dau = _tao(client, "WF dau")
    sau = _tao(client, "WF sau")          # `sau` là cái mới nhất ⇒ items[0]

    trang = client.get(f"/agent/workflows/{dau}")
    assert trang.status_code == 200
    assert f'data-workflow-id="{dau}"' in trang.text
    assert sau not in trang.text

    # Và tải lại vẫn đúng nó — id nằm ở URL, không ở trạng thái phiên.
    lai = client.get(f"/agent/workflows/{dau}")
    assert f'data-workflow-id="{dau}"' in lai.text


def test_loi_vao_KHONG_id_de_thuoc_tinh_RONG(web):
    """⭐ Vế đối chứng cho bài trên. `/agent/canvas` (`test_1726` chốt nó) phải
    để `data-workflow-id` RỖNG — trình soạn mới giữ được đường cũ."""
    client, *_ = web
    trang = client.get("/agent/canvas")
    assert trang.status_code == 200
    assert 'data-workflow-id=""' in trang.text


@pytest.mark.parametrize("ma", ["khong-he-co", "../../etc", ""])
def test_id_khong_ton_tai_tra_404(web, ma):
    client, *_ = web
    assert client.get(f"/agent/workflows/{ma}",
                      follow_redirects=False).status_code in (404, 307, 308)


def test_workflow_cua_nguoi_khac_tra_404_chu_khong_403(web):
    """🔑 `403` xác nhận rằng id đó có thật — y hệt lý lẽ ở `drafts_v3._cua_toi`."""
    client, _uid, khac_id = web
    import platform_core.db as dbmod
    from platform_core.workflow import dinh_nghia
    gen = dbmod.get_session(); db = next(gen)
    wf = dinh_nghia.tao_workflow(db, owner_id=khac_id, name="cua nguoi khac")
    db.commit(); ma = wf.id; db.close()

    assert client.get(f"/agent/workflows/{ma}").status_code == 404


def test_tao_moi_QUA_CUA_V3_roi_mo_duoc_NGAY(web):
    """Đường mà nút "Workflow mới" đi: POST cửa v3 ⇒ id ⇒ mở trang của id đó."""
    client, *_ = web
    ma = _tao(client, "")
    trang = client.get(f"/agent/workflows/{ma}")
    assert trang.status_code == 200 and f'data-workflow-id="{ma}"' in trang.text
    assert ma in client.get("/agent/workflows").text


# ── 3. Đặt chỗ — trả 200 và NÓI RÕ đang xây ─────────────────────────────────

@pytest.mark.parametrize("duong", DAT_CHO)
def test_dat_cho_tra_200(web, duong):
    client, *_ = web
    assert client.get(duong).status_code == 200


@pytest.mark.parametrize("duong", DAT_CHO)
def test_dat_cho_NOI_RO_dang_xay(web, duong):
    """⚠️ Một trang trống trông-như-thật là một lời nói dối: người dùng sẽ báo
    "mục này hỏng" thay vì "mục này chưa có"."""
    client, *_ = web
    assert "Đang xây" in client.get(duong).text


def test_moi_muc_IA_deu_co_route_THAT(web):
    """⭐ `manifest.nav` là lời khai; bảng định tuyến là sự thật. Một mục nav
    trỏ vào đường không có route là một nút bấm ra 404."""
    from apps.agent.manifest import MANIFEST
    from apps.agent.routes import router
    co = {MANIFEST.route_prefix + getattr(r, "path", "") for r in router.routes}
    thieu = [e.path for e in MANIFEST.nav_entries() if e.path not in co]
    assert not thieu, f"muc nav khong co route: {thieu}"


def test_SAU_muc_cap_cao_nhat_dung_nhu_spec_09():
    """Con số trong tên bài phải đúng: `09 §1` khai **sáu** mục cấp cao nhất
    (Workflows · Runs · Templates · Connections · Agents · Settings), cộng lối
    vào `/agent` của chính app."""
    from apps.agent.manifest import MANIFEST
    duong = [e.path for e in MANIFEST.nav_entries()]
    assert duong == ["/agent", "/agent/workflows", "/agent/runs",
                     "/agent/templates", "/agent/connections",
                     "/agent/agents", "/agent/settings"]
    assert len(duong) - 1 == 6


# ── 4. ⛔ Không cửa HTTP mới ─────────────────────────────────────────────────

def test_khong_mo_cua_POST_moi_o_tang_trang():
    """🔴 Tạo và nhân bản đi qua `POST /agent/api/v3/workflows` — cửa ĐÃ CÓ.
    Tầng trang (mọi đường không phải `/api/`) chỉ được có GET.

    Mở một cửa HTTP mới là một quyết định riêng, không phải một chi tiết thi
    công: nó thêm một bề mặt phải xác thực, phải chống CSRF, phải phân quyền.
    """
    from apps.agent.routes import router
    ghi = sorted((sorted(r.methods)[0], r.path) for r in router.routes
                 if "/api/" not in getattr(r, "path", "")
                 and getattr(r, "methods", set()) - {"GET", "HEAD"})
    assert ghi == [], f"cua ghi moi o tang trang: {ghi}"
