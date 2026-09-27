"""UI-1 phần còn treo — cửa LƯU TRỮ workflow (chủ dự án duyệt mở 28/09/2026).

## Vì sao cần cửa này

`Workflow.archived_at` đã có trong lược đồ, và **ba** nơi đã ĐỌC nó:

    drafts_v3.v3_danh_sach     `WHERE archived_at IS NULL`   — ẩn khỏi danh sách
    tao_run.tao_run            từ chối tạo run mới
    nut.type_version_thieu     bỏ qua khi dò drift

⇒ Toàn bộ **ngữ nghĩa** của lưu trữ đã sống. Thiếu đúng một thứ: **không cửa nào
ĐẶT được nó**. Làn UI-1 phát hiện và **dừng lại hỏi** thay vì tự mở bề mặt HTTP.

## 🔴 Vì sao PHẢI có cả cửa MỞ LẠI và cửa NHÌN THẤY

Một workflow lưu trữ rồi thì **biến mất khỏi danh sách** — đó là cả ý nghĩa của
nó. Nếu ⛔ không có đường mở lại và ⛔ không có cách nhìn thấy bản đã lưu trữ thì
"lưu trữ" là một **cánh cửa một chiều không lối về**: người dùng mất workflow mà
⛔ không ai xoá gì cả, và họ ⛔ không có cách nào biết nó còn đó.

⇒ Bộ này có **ba** phần, thiếu phần nào cũng thành bẫy:
  1. đặt `archived_at`            (lưu trữ)
  2. xoá `archived_at`            (mở lại)
  3. **nhìn thấy** bản đã lưu trữ (`?luu_tru=1`) — nếu không, (2) ⛔ không với tới

## ⛔ Lưu trữ KHÔNG dừng một lượt chạy đang chạy

Nó chặn **tạo run MỚI** (`tao_run.py:205`). Một lượt đang chạy vẫn chạy nốt —
huỷ một lượt là một hành động khác, có cửa riêng. Gộp hai việc vào một nút là
làm người dùng huỷ mất một lượt đã tiêu tiền mà ⛔ không định.

## ⚠️ Mọi bài ở đây đi qua HTTP, không gọi thẳng hàm

Thứ cần chứng minh là **cửa mà người dùng gặp** đặt được `archived_at` — một bài
gọi `dinh_nghia.*` trực tiếp sẽ xanh ngay cả khi route không tồn tại. Đó đúng là
lỗ hổng UI-1 báo: nghĩa đã có, cửa thì không.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from platform_core.models import Workflow

_MAT_KHAU = "Strong-pass-123"
_EMAIL = "v3-luu-tru@example.com"


class _Web:
    def __init__(self, client: TestClient, csrf: str, user_id: str):
        self.client, self.csrf, self.user_id = client, csrf, user_id

    def phien(self):
        import platform_core.db as dbmod
        return next(dbmod.get_session())

    def tao(self, ten: str) -> str:
        r = self.client.post("/agent/api/v3/workflows",
                             json={"name": ten, "csrf_token": self.csrf})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def danh_sach(self, *, luu_tru: bool = False) -> list[dict]:
        duong = "/agent/api/v3/workflows" + ("?luu_tru=1" if luu_tru else "")
        r = self.client.get(duong)
        assert r.status_code == 200, r.text
        return r.json()["items"]

    def ids(self, *, luu_tru: bool = False) -> set[str]:
        return {w["id"] for w in self.danh_sach(luu_tru=luu_tru)}

    def bam(self, wf_id: str, cua: str, *, csrf: bool = True):
        body = {"csrf_token": self.csrf} if csrf else {}
        return self.client.post(
            f"/agent/api/v3/workflows/{wf_id}/{cua}", json=body)

    def moc(self, wf_id: str):
        db = self.phien()
        try:
            return db.get(Workflow, wf_id).archived_at
        finally:
            db.close()


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'lt.db').as_posix()}")
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
    cfg.write_text("{}", encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "test-5603-session",
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
        # Token CSRF gắn theo PHIÊN và phiên xoay lúc đăng nhập ⇒ phải đọc lại
        # SAU khi vào (`server/auth/csrf.py`).
        canvas = client.get("/agent/canvas")
        csrf = re.search(r'data-csrf-token="([^"]+)"', canvas.text)
        assert csrf, f"/agent/canvas khong in csrf ({canvas.status_code})"
        yield _Web(client, csrf.group(1), user_id)
    dbmod.reset_engine()


# ── 1. Lưu trữ ──────────────────────────────────────────────────────────────

def test_luu_tru_dat_moc_VA_an_khoi_danh_sach(web):
    """Hai vế trong một bài vì chúng là MỘT hành động: nếu chỉ đặt mốc mà danh
    sách vẫn hiện thì người dùng thấy một nút không làm gì."""
    a = web.tao("giu lai")
    b = web.tao("dem cat di")
    assert {a, b} <= web.ids()
    assert web.moc(b) is None

    r = web.bam(b, "luu-tru")
    assert r.status_code == 200, r.text
    assert r.json()["da_luu_tru"] is True

    assert web.moc(b) is not None, "route tra 200 ma khong dat archived_at"
    sau = web.ids()
    assert a in sau, "luu tru mot workflow lam mat workflow KHAC"
    assert b not in sau, "workflow da luu tru van con trong danh sach"


def test_luu_tru_hai_lan_KHONG_lam_moc_troi(web):
    """Bấm hai lần là một ý định, không phải hai. Mốc trôi nghĩa là thứ tự
    trong bất kỳ danh sách nào sắp theo nó cũng trôi theo."""
    b = web.tao("bam hai lan")
    web.bam(b, "luu-tru")
    lan_dau = web.moc(b)
    assert lan_dau is not None

    r = web.bam(b, "luu-tru")
    assert r.status_code == 200, r.text
    assert web.moc(b) == lan_dau


# ── 2. Nhìn thấy lại, rồi mở lại ────────────────────────────────────────────

def test_van_NHIN_THAY_duoc_ban_da_luu_tru(web):
    """⛔ Không có cửa này thì 'mở lại' KHÔNG VỚI TỚI ĐƯỢC từ giao diện."""
    a = web.tao("dang dung")
    b = web.tao("cat di roi tim lai")
    web.bam(b, "luu-tru")

    kho = web.danh_sach(luu_tru=True)
    assert b in {w["id"] for w in kho}
    assert all(w.get("da_luu_tru") for w in kho), \
        "?luu_tru=1 phai tra DUNG ban da luu tru, khong tron lan"
    assert a not in {w["id"] for w in kho}, \
        "?luu_tru=1 tra ca ban dang dung ⇒ no khong phai mot bo loc"


def test_danh_sach_mac_dinh_khai_da_luu_tru_la_False(web):
    """Đối chứng cho bài trên: một bản vá `da_luu_tru=True` cho MỌI dòng cũng
    làm bài trên xanh. Trường này phải PHÂN BIỆT được, không chỉ tồn tại."""
    web.tao("dang dung")
    ds = web.danh_sach()
    assert ds and all(w.get("da_luu_tru") is False for w in ds)


def test_mo_lai_dua_workflow_VE_danh_sach(web):
    b = web.tao("cat roi mo lai")
    web.bam(b, "luu-tru")
    assert b not in web.ids()

    r = web.bam(b, "mo-lai")
    assert r.status_code == 200, r.text
    assert r.json()["da_luu_tru"] is False

    assert web.moc(b) is None
    assert b in web.ids(), "mo lai roi ma van khong thay trong danh sach"
    assert b not in web.ids(luu_tru=True)


def test_mo_lai_mot_ban_CHUA_luu_tru_khong_no(web):
    """Cửa này phải luỹ đẳng: giao diện có thể gọi nó từ một danh sách đã cũ."""
    b = web.tao("chua he luu tru")
    r = web.bam(b, "mo-lai")
    assert r.status_code == 200, r.text
    assert r.json()["da_luu_tru"] is False
    assert b in web.ids()


# ── 3. Ranh giới ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cua", ["luu-tru", "mo-lai"])
def test_workflow_cua_nguoi_khac_tra_404(web, cua):
    """⛔ KHÔNG phải 403: một 403 là một máy đếm cho người ngoài biết id nào có
    thật. Cùng luật với `_cua_toi`.

    🔴 Bài này TỪNG XANH GIẢ. Lượt chạy đỏ đầu (28/09) cho nó `PASS` khi route
       **còn chưa tồn tại** — vì một route vắng mặt cũng trả `404`. Mã trạng
       thái một mình ⛔ không phân biệt được *"tôi đã kiểm chủ sở hữu và không
       thấy"* với *"tôi chưa từng nghe về đường này"*.
    ⇒ Phải đo cả `detail`: `_cua_toi` nói bằng tiếng người, FastAPI nói
      `"Not Found"`.
    """
    r = web.bam("00000000-0000-0000-0000-000000000000", cua)
    assert r.status_code == 404, r.text
    assert r.json().get("detail") != "Not Found", \
        f"404 nay den tu ROUTER (route chua ton tai), khong tu _cua_toi: {r.text}"


@pytest.mark.parametrize("cua", ["luu-tru", "mo-lai"])
def test_thieu_csrf_bi_tu_choi(web, cua):
    b = web.tao("kiem csrf")
    r = web.bam(b, cua, csrf=False)
    assert r.status_code == 400, r.text
    if cua == "luu-tru":
        assert web.moc(b) is None, "CSRF bi tu choi ma moc van duoc dat"
