"""
test_272_cua_streaming — `POST /api/v1/messages` và `/responses`. (Q107, Đợt 4)

Hai route này là cửa **thứ ba** thu tiền của `/api/v1`, và là cửa duy nhất thu mà
**không có `Idempotency-Key`**. Thứ giữ tiền thay nó là **thu theo token đã thật
sự sinh ra**, nên phần lớn file này là về chuyện đó.

Bảy tính chất neo ở đây:

  1. Khai đúng `STREAM`, và hợp đồng được **bộ kiểm chạy trên đường thật**.
  2. **Không đòi `Idempotency-Key`** (Q107) — đòi là tính năng không tồn tại.
  3. Sinh ít trả ít; **cắt giữa chừng vẫn thu đúng phần đã sinh**.
  4. Không đo được ⇒ hoàn đủ, thu 0.
  5. 🔴 Bận ⇒ **503 + Retry-After, hoàn đủ**. Khách không trả cho lượt không chạy.
  6. Chế độ thử không chạm GPU, không chạm sổ tiền.
  7. Alias là lớp đệm ở **cả ba** cửa, không riêng cửa job.
"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ)
from server.api.inventory import API_V1_PREFIX

PEPPER = "stream-test-pepper-" + "s" * 40
MSG = API_V1_PREFIX + "/messages"
RSP = API_V1_PREFIX + "/responses"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ)
NL = bytes([10])


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "st.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "stream-secret-value-x",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "text.chat",
        "LTT_PUBLIC_API_RPM": "600",
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
    dbmod.reset_engine()


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _account(credits: int = 10_000, mode: str = ""):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="s-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
        them = {"mode": mode} if mode else {}
        _k, token = devkeys.issue(db, user_id=u.id, scopes=ALL_SCOPES,
                                  env={devkeys.PEPPER_ENV: PEPPER}, **them)
        db.commit()
        return u.id, token
    finally:
        _close(gen)


def _h(token):
    return {"Authorization": "Bearer " + token}


def _so_du(user_id):
    from platform_core import credit
    gen, db = _session()
    try:
        return int(credit.so_du(db, user_id))
    finally:
        _close(gen)


def _than(**g):
    d = {"model": "ltt_llm", "stream": True, "max_tokens": 500,
         "messages": [{"role": "user", "content": "xin chao"}]}
    d.update(g)
    return d


def _sse(ten, goi):
    return (b"event: " + ten.encode() + NL
            + b"data: " + json.dumps(goi).encode() + NL + NL)


def _khoi(vao=100, ra=50, co_usage=True):
    ds = []
    if co_usage:
        ds.append(_sse("message_start", {"message": {"usage": {
            "input_tokens": vao, "output_tokens": 0}}}))
    ds.append(_sse("content_block_delta",
                   {"delta": {"type": "text_delta", "text": "chao"}}))
    if co_usage:
        ds.append(_sse("message_delta", {"usage": {"output_tokens": ra}}))
    ds.append(_sse("message_stop", {}))
    return ds


def _dat_luong(monkeypatch, khoi=None, *, nem=None, ban=False):
    """Thay `luong_vlm.mo` — KHÔNG chạm máy B trong test."""
    from platform_core.llm import luong_vlm
    da_goi = []

    class GiaLuong:
        def __init__(self, ks):
            self.ma = 200
            self.content_type = "text/event-stream"
            self.luong = iter(ks)
            self.da_xong = False
            self.da_hong = False

        def xong(self, tokens=0):
            self.da_xong = True

        def hong(self, exc):
            self.da_hong = True

    def gia(db, *, duong, than, timeout_s=900.0):
        da_goi.append({"duong": duong, "than": than})
        if ban:
            raise luong_vlm.KhongMoDuocLuong("may B dang ban", ban=True,
                                             thu_lai_sau_s=30)
        if nem is not None:
            raise nem
        return GiaLuong(khoi if khoi is not None else _khoi())

    monkeypatch.setattr(luong_vlm, "mo", gia)
    return da_goi


# ── 1. Hợp đồng ─────────────────────────────────────────────────────────────

def test_hai_route_khai_dung_STREAM():
    from platform_core.public_api.protocol import STREAM
    from server.api.inventory import API_V1_ROUTES

    duong = {r.path for r in API_V1_ROUTES if r.execution_mode == STREAM}
    assert duong == {MSG, RSP}


def test_hop_dong_duoc_kiem_khi_NAP_APP():
    """⭐ Dựng ở cấp module, nên `check_mode_rules` chạy lúc import — bỏ mất một
    lời hứa của `STREAM` là app **không khởi động được**, thay vì lặng lẽ sai."""
    from server.api.streaming import HOP_DONG
    assert HOP_DONG.extra["settles_from_measured_usage"] is True


# ── 2. Không đòi Idempotency-Key ────────────────────────────────────────────

def test_KHONG_doi_idempotency_key(api, monkeypatch):
    """⭐ Q107, và nó là cả lý do cửa này dùng được: **không CLI nào gửi nó**."""
    goi = _dat_luong(monkeypatch)
    _u, token = _account()
    r = api.post(MSG, json=_than(), headers=_h(token))
    assert r.status_code == 200, r.text
    assert goi, "khong goi toi model"


# ── 3. Tiền: giữ TRẦN, thu THẬT ─────────────────────────────────────────────

def test_thu_theo_TOKEN_DA_SINH_khong_theo_tran(api, monkeypatch):
    _dat_luong(monkeypatch, _khoi(vao=1_000, ra=20))
    user_id, token = _account()
    truoc = _so_du(user_id)
    api.post(MSG, json=_than(max_tokens=8000), headers=_h(token)).read()
    thu = truoc - _so_du(user_id)
    assert thu > 0, "khong thu gi ca"

    _dat_luong(monkeypatch, _khoi(vao=1_000, ra=3_000))
    truoc2 = _so_du(user_id)
    api.post(MSG, json=_than(max_tokens=8000), headers=_h(token)).read()
    thu2 = truoc2 - _so_du(user_id)
    assert thu2 > thu, "hai luot sinh khac han nhau ma cung gia -> thu theo tran"


def test_CAT_GIUA_CHUNG_van_thu_dung_phan_da_sinh(api, monkeypatch):
    """🔴 Đây là ca mà cả thiết kế này sinh ra để xử. GPU đã đốt rồi."""
    khoi = [_sse("message_start", {"message": {"usage": {"input_tokens": 500,
                                                         "output_tokens": 0}}}),
            _sse("message_delta", {"usage": {"output_tokens": 42}})]
    khoi += [_sse("content_block_delta", {"delta": {"text": "x"}})] * 50
    _dat_luong(monkeypatch, khoi)
    user_id, token = _account()
    truoc = _so_du(user_id)

    with api.stream("POST", MSG, json=_than(max_tokens=8000),
                    headers=_h(token)) as r:
        assert r.status_code == 200
        next(r.iter_bytes())

    assert _so_du(user_id) < truoc, "cat giua chung ma khong thu gi"


def test_khong_do_duoc_thi_HOAN_DU(api, monkeypatch):
    """⛔ Thu tiền mà không có bằng chứng còn tệ hơn mất một ít tiền."""
    _dat_luong(monkeypatch, _khoi(co_usage=False))
    user_id, token = _account()
    truoc = _so_du(user_id)
    api.post(MSG, json=_than(), headers=_h(token)).read()
    assert _so_du(user_id) == truoc


def test_khong_du_tien_thi_KHONG_goi_model(api, monkeypatch):
    goi = _dat_luong(monkeypatch)
    _u, token = _account(credits=0)
    r = api.post(MSG, json=_than(), headers=_h(token))
    assert r.status_code in (402, 409), r.text
    assert goi == [], "da goi model roi moi phat hien khong du tien"


# ── 4. Bận ≠ hỏng ───────────────────────────────────────────────────────────

def test_ban_thi_503_va_HOAN_DU(api, monkeypatch):
    """🔴 D-005. Khách không trả tiền cho một lượt không chạy."""
    _dat_luong(monkeypatch, ban=True)
    user_id, token = _account()
    truoc = _so_du(user_id)
    r = api.post(MSG, json=_than(), headers=_h(token))
    assert r.status_code == 503, r.text
    assert int(r.headers.get("Retry-After", 0)) > 0
    assert _so_du(user_id) == truoc, "ban ma van thu tien"


# ── 5. Chế độ thử ───────────────────────────────────────────────────────────

def test_che_do_thu_KHONG_cham_GPU_va_KHONG_thu_tien(api, monkeypatch):
    from platform_core.public_api.sandbox import MODE_TEST

    goi = _dat_luong(monkeypatch)
    user_id, token = _account(mode=MODE_TEST)
    truoc = _so_du(user_id)
    r = api.post(MSG, json=_than(), headers=_h(token))
    assert r.status_code == 200
    assert b"message_start" in r.content
    assert goi == [], "khoa THU ma van dot GPU that"
    assert _so_du(user_id) == truoc


def test_che_do_thu_dung_hinh_dang_responses(api, monkeypatch):
    from platform_core.public_api.sandbox import MODE_TEST

    _dat_luong(monkeypatch)
    _u, token = _account(mode=MODE_TEST)
    r = api.post(RSP, json=_than(input="hi"), headers=_h(token))
    assert b"response.completed" in r.content


# ── 6. Alias là lớp đệm ở CẢ BA cửa ─────────────────────────────────────────

def test_id_noi_bo_KHONG_goi_duoc(api, monkeypatch):
    goi = _dat_luong(monkeypatch)
    _u, token = _account()
    r = api.post(MSG, json=_than(model="qwen38-api"), headers=_h(token))
    assert r.status_code == 400
    assert goi == []


def test_alias_duoc_dich_TRUOC_KHI_roi_nen_tang(api, monkeypatch):
    goi = _dat_luong(monkeypatch)
    _u, token = _account()
    api.post(MSG, json=_than(), headers=_h(token)).read()
    assert goi[0]["than"]["model"] == "qwen38-api", "chua dich alias"


def test_hai_route_di_dung_duong_thuong_nguon(api, monkeypatch):
    goi = _dat_luong(monkeypatch)
    _u, token = _account()
    api.post(MSG, json=_than(), headers=_h(token)).read()
    api.post(RSP, json=_than(input="hi"), headers=_h(token)).read()
    assert [g["duong"] for g in goi] == ["/v1/messages", "/v1/responses"]


# ── 7. Tham số ──────────────────────────────────────────────────────────────

# ⛔ GO 26/08 — `test_thieu_stream_true_thi_TU_CHOI_va_chi_sang_cua_kia`.
#
#    No chot rang `/messages` TU CHOI (400) mot request khong-stream. Hanh vi do
#    da bi doi CO CHU Y o `cee5ca1`: cau tu choi ay CHAN LUON Claude Desktop —
#    ung dung tham do model bang mot request khong streaming, nhan 400, va ket
#    luan "Gateway rejected model", chan o o chat.
#
# ⛔ Nen tu do co HAI phep kiem noi nguoc nhau trong cung mot kho:
#      test_272 (day)  : "khong-stream phai bi TU CHOI"
#      test_285        : "ma nguon KHONG con tu choi request khong-stream"
#
#    Mot trong hai phai sai, va cai sai la cai nay. Giu ca hai thi lan sau ai do
#    se "sua" cai dang do bang cach mo lai lo hong da vit.
#
# ⭐ Hanh vi MOI duoc phu day du o `tests/test_285_messages_khong_stream.py`
#    (19 phep kiem), gom ca mot chot tho chan cau tu choi cu quay lai. Khong mat
#    do phu nao khi go phep kiem nay.


def test_prompt_he_thong_va_tools_duoc_TINH_vao_uoc_token():
    """⚠️ Đo thật 23/08: prompt hệ thống của Codex là **~21.936 token**. Bỏ qua
    `system` và `tools` khi ước là giữ chỗ thiếu rất nhiều."""
    from apps.ltt_llm.features import uoc_token_vao
    from server.api.streaming import _tin_nhan

    it = _tin_nhan({"messages": [{"role": "user", "content": "hi"}]})
    nhieu = _tin_nhan({
        "messages": [{"role": "user", "content": "hi"}],
        "system": [{"type": "text", "text": "x" * 5000}],
        "tools": [{"name": "Read", "input_schema": {"a": "b" * 2000}}]})
    assert uoc_token_vao(nhieu) > uoc_token_vao(it) * 10


def test_input_dang_chuoi_tran_cua_responses():
    from server.api.streaming import _tin_nhan
    assert _tin_nhan({"input": "xin chao"})


# ── 8. Trang "Cắm vào CLI" trong cổng dev ───────────────────────────────────
#
# ⭐ Bài học từ `api.nghimmo.com`: thứ chặn một lập trình viên gần như không bao
#    giờ là giao thức, mà là **điền đúng một file cấu hình**. Mã đúng mà khách
#    không cấu hình được thì vẫn là mã không ai gọi.

def _csrf(html):
    import re
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _dang_nhap(client):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = "cli-" + uuid.uuid4().hex[:6] + "@example.com"
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        u.is_verified = True
        db.flush()
        credit.cap_tay(db, u.id, 200, by="test")
        db.commit()
    finally:
        _close(gen)
    page = client.get("/login").text
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)


def test_trang_cli_day_du_ba_cong_cu(api):
    _dang_nhap(api)
    page = api.get("/developers/cli").text
    for manh in ("model_providers.ltt", "ltt.config.toml", "wire_api",
                 "ANTHROPIC_BASE_URL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                 "Third-Party Inference", "inferenceModels", "ltt_llm"):
        assert manh in page, "trang /developers/cli thieu " + repr(manh)


def test_trang_cli_khai_DUNG_hai_dia_chi(api):
    """🔴 Hai base URL lệch nhau bốn ký tự. Đổi chỗ là 404 không manh mối."""
    _dang_nhap(api)
    page = api.get("/developers/cli").text
    assert "/api/v1</code>" in page, "thieu dia chi cua Codex"
    assert "/api</code>" in page, "thieu dia chi cua Claude"


def test_trang_cli_KHONG_chua_khoa_that(api):
    """⛔ Cùng luật mọi ví dụ khác đã theo: *"No snippet ever contains a key."*
    Khoá chỉ hiện một lần lúc tạo; trang này không điền hộ được, và không nên."""
    _dang_nhap(api)
    page = api.get("/developers/cli").text
    assert "ltt_sk_" not in page.replace("ltt_sk_… key", "").replace("ltt_sk_…", "")


def test_cau_hinh_codex_KHONG_dung_id_noi_bo():
    from platform_core.public_api import examples
    ma = examples.codex_profile()
    assert "qwen38" not in ma, "lo id noi bo -> tich hop se ghim vao no"
    assert examples.CLI_MODEL == "ltt_llm"


# ── 9. Giám sát KHÁCH, không phải giám sát máy ──────────────────────────────
#
# 🔴 Hôm nay ta giám sát "máy B còn sống không". Ta KHÔNG giám sát "khách gọi có
#    được không". Một khách hết credit giữa chừng là người **muốn dùng mà không
#    dùng được** — và nếu không đếm, ta chỉ biết khi họ chịu khó viết thư. Phần
#    lớn thì không: họ đi chỗ khác.

def test_het_credit_duoc_DEM(api, monkeypatch):
    from platform_core.public_api import metrics

    dem = []
    monkeypatch.setattr(metrics, "increment", lambda ten, *a, **k: dem.append(ten))
    _dat_luong(monkeypatch)
    _u, token = _account(credits=0)
    api.post(MSG, json=_than(), headers=_h(token))
    assert metrics.CREDIT_EXHAUSTED in dem, (
        "khach het credit ma khong dem -> ta chi biet khi ho viet thu")


def test_het_credit_KHONG_bi_gop_vao_loi_he_thong():
    """⛔ Một khách hết tiền không phải một hệ thống hỏng.

    Trộn hai thứ làm người trực mất khả năng phân biệt "cần sửa" với "cần gọi
    điện" — và khi mọi thứ đều là báo động thì không gì là báo động."""
    from platform_core.public_api import metrics
    from platform_core.public_api.ops_alerts import NGUONG

    assert metrics.CREDIT_EXHAUSTED != metrics.RESPONSES_5XX
    assert metrics.CREDIT_EXHAUSTED != metrics.AUTH_FAILURE
    assert NGUONG[metrics.CREDIT_EXHAUSTED] == 3, (
        "mot lan la binh thuong; ba lan lien tiep moi la co nguoi dang mac ket")
