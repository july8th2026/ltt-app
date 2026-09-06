"""
test_259_cua_dong_bo — `POST /api/v1/chat/completions`, chế độ `SYNC_BILLED`. (Q106, H38 V3)

Cửa này là cửa **thứ hai** thu tiền của `/api/v1`, và nó thu **không có quote**.
Đó là điều làm nó khác mọi thứ đã có, nên phần lớn file này là về tiền:

  1. **Bắt buộc `Idempotency-Key`**, và lặp lại không được gọi model lần hai.
     Không có quote thì đây là thứ duy nhất chặn một lần thử lại vì mạng mua
     hàng hai lần.
  2. **Giữ TRẦN trước, thu THẬT sau.** Sinh ít thì trả ít. Đây chính là lỗi tiền
     im lặng đã tìm ra ở cửa job hôm 23/08.
  3. **Không đo được thì hoàn đủ, không thu.**
  4. 🔴 **BẬN ≠ HỎNG.** Máy B bận ⇒ **503 + `Retry-After`, và hoàn đủ**. Khách
     không trả tiền cho một lượt không chạy. (429 ở bề mặt này nghĩa là *bạn gọi
     quá nhanh* — chuyện khác hẳn; xem test tương ứng.)
  5. **Không đủ tiền thì không đốt GPU** — chốt trước, không phải sau.
  6. **Chế độ thử không chạm GPU.** Ở cửa job một lượt thử vẫn xếp hàng; ở đây nó
     chiếm card ngay lập tức mà không ai trả tiền.
  7. **Không đẩy vào hàng đợi** — lời hứa của `SYNC_BILLED`, đo bằng hành vi.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ)
from server.api.inventory import API_V1_PREFIX

PEPPER = "chat-test-pepper-" + "c" * 40
DUONG = f"{API_V1_PREFIX}/chat/completions"
TOOL = "text.chat"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ)


# ── Khung ────────────────────────────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'chat.db').as_posix()}")
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
        "LTT_SESSION_SECRET": "chat-secret-value-here",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
        "LTT_PUBLIC_API_RPM": "600",
    })
    # ⚠️ `https://` chứ không phải `http://`: cookie phiên đặt cờ `secure`, nên
    #    qua http nó không được gửi lại và mọi trang cần đăng nhập âm thầm
    #    thành trang login — trang vẫn 200, chỉ là trang khác.
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
        user = tao_nguoi_dung(db, email=f"c-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, user.id, credits, by="test")
        them = {"mode": mode} if mode else {}
        _key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
                                    env={devkeys.PEPPER_ENV: PEPPER}, **them)
        db.commit()
        return user.id, token
    finally:
        _close(gen)


def _h(token, idem=None):
    return {"Authorization": f"Bearer {token}",
            "Idempotency-Key": idem or uuid.uuid4().hex}


def _than(**ghi_de):
    d = {"model": "ltt_llm", "messages": [{"role": "user", "content": "xin chao"}],
         "max_tokens": 500}
    d.update(ghi_de)
    return d


def _so_du(user_id: str) -> int:
    from platform_core import credit
    gen, db = _session()
    try:
        return int(credit.so_du(db, user_id))
    finally:
        _close(gen)


def _dat_model(monkeypatch, *, token_vao=100, token_ra=50, do_duoc=True, nem=None):
    """Thay `features.chay` — KHÔNG chạm máy B trong test."""
    from apps.ltt_llm import features
    goi = []

    def gia(db, params, *, timeout_s=300.0):
        goi.append(params)
        if nem is not None:
            raise nem
        return features.KetQua(
            noi_dung="chao ban", suy_nghi="", tool_calls=(), finish_reason="stop",
            model=params["model"], token_vao=token_vao, token_ra=token_ra,
            token_vao_cache=0, do_duoc=do_duoc)

    monkeypatch.setattr(features, "chay", gia)
    return goi


def _dem_job() -> int:
    import sqlalchemy as sa
    from platform_core.models import Job
    gen, db = _session()
    try:
        return int(db.execute(sa.select(sa.func.count(Job.id))).scalar_one())
    finally:
        _close(gen)


def _giu_execution_slot() -> str:
    from platform_core.llm import admission
    gen, db = _session()
    try:
        lease = admission.acquire(
            db, resource="llm_remote", slots=1, user_id="u-khac",
            mode="job", holder_id="job-khac")
        assert lease is not None
        db.commit()
        return lease.id
    finally:
        _close(gen)


def _dem_execution_lease() -> int:
    from platform_core.models import ExecutionLease
    gen, db = _session()
    try:
        return db.query(ExecutionLease).count()
    finally:
        _close(gen)


# ── 1. Hợp đồng chế độ ───────────────────────────────────────────────────────

def test_route_khai_dung_SYNC_BILLED():
    from platform_core.public_api.protocol import SYNC_BILLED
    from server.api.inventory import API_V1_ROUTES

    r = [x for x in API_V1_ROUTES if x.path.endswith("/chat/completions")]
    assert len(r) == 1 and r[0].execution_mode == SYNC_BILLED


def test_chi_MOT_route_dong_bo_co_thu_tien():
    """Thêm cái thứ hai là thêm một chỗ tiền có thể rò. Phải cố ý."""
    from platform_core.public_api.protocol import SYNC_BILLED
    from server.api.inventory import API_V1_ROUTES

    assert [f"{r.method} {r.path}" for r in API_V1_ROUTES
            if r.execution_mode == SYNC_BILLED] == [f"POST {DUONG}"]


def test_hop_dong_TU_CHOI_SYNC_BILLED_thieu_idempotency_key():
    """🔴 Không có quote thì khoá này là thứ DUY NHẤT chặn thử-lại-mua-hai-lần."""
    from platform_core.public_api.protocol import (ProtocolError,
                                                   PublicOperationContract,
                                                   SYNC_BILLED)
    with pytest.raises(ProtocolError) as e:
        PublicOperationContract(name="x.chat", execution_mode=SYNC_BILLED,
                                chargeable=True)
    assert "Idempotency-Key" in str(e.value)


def test_hop_dong_TU_CHOI_SYNC_BILLED_doi_quote():
    """Quote là giá ký TRƯỚC khi chạy; giá token không biết trước được."""
    from platform_core.public_api.protocol import (ProtocolError,
                                                   PublicOperationContract,
                                                   SYNC_BILLED)
    with pytest.raises(ProtocolError):
        PublicOperationContract(name="x.chat", execution_mode=SYNC_BILLED,
                                chargeable=True, requires_idempotency_key=True,
                                requires_quote=True)


def test_hop_dong_TU_CHOI_SYNC_BILLED_mien_phi():
    """Miễn phí mà trả trong request thì là `SYNC`, và `SYNC` khắt khe hơn."""
    from platform_core.public_api.protocol import (ProtocolError,
                                                   PublicOperationContract,
                                                   SYNC_BILLED)
    with pytest.raises(ProtocolError):
        PublicOperationContract(name="x.free", execution_mode=SYNC_BILLED,
                                requires_idempotency_key=True)


# ── 2. Tiền: giữ TRẦN, thu THẬT ─────────────────────────────────────────────

def _credit_delta_da_ghi(user_id: str):
    """Cột `credit_delta` trong sổ request — thứ `anomalies.py` cộng để dò tiền."""
    from sqlalchemy import select
    from platform_core.public_api.tables import ApiRequestLog
    gen, db = _session()
    try:
        return [r for (r,) in db.execute(
            select(ApiRequestLog.credit_delta)
            .where(ApiRequestLog.user_id == user_id)
            .order_by(ApiRequestLog.id)).all()]
    finally:
        _close(gen)


def test_so_REQUEST_ghi_dung_so_tien_da_thu(api, monkeypatch):
    """🔴 P08 F-01 — cột này TỪNG luôn bằng 0 ở cửa đồng bộ, dù thu bao nhiêu.

    `request.state.api_credit_delta` chỉ được gán ở `server/api/jobs.py`. Cửa
    này và cửa stream không gán lần nào, nên mọi dòng của chúng đọc ra `+0`.

    ⛔ Vì sao tệ hơn một cột trống: nó **giả làm bằng chứng**. `reports/06`
       chứng minh bất biến "bận thì không thu tiền" bằng câu *"89 lượt hỏng,
       credit=+0 mọi dòng"* — trên đúng cái cửa mà cột ấy không bao giờ khác 0.
       Một bằng chứng không thể sai thì không chứng minh gì.
    """
    # ⭐ Cỡ cố ý VƯỢT 1 credit: đối chứng `thu_that > 0` phải đúng vì lượt này
    #    thật sự tốn tiền, không phải vì một chính sách làm tròn có sàn.
    _dat_model(monkeypatch, token_vao=30_000, token_ra=1_000)   # 1,9 credit
    user_id, token = _account()
    truoc = _so_du(user_id)
    # ⚠️ `max_tokens` phải nằm dưới trần ngân sách 90 giây của cửa ĐỒNG BỘ
    #    (~2.372) — vượt là HTTP 400, không phải một phép kiểm tiền.
    r = api.post(DUONG, json=_than(max_tokens=2_000), headers=_h(token))
    assert r.status_code == 200, r.text
    thu_that = truoc - _so_du(user_id)
    assert thu_that > 0, "doi chung TRUOT: khong thu gi ca, phep kiem duoi vo nghia"

    ghi = _credit_delta_da_ghi(user_id)
    assert ghi, "khong co dong nao trong so request"
    assert ghi[-1] == -thu_that, (
        f"so ghi {ghi[-1]} nhung so THAT bi tru la {-thu_that} — cot nay dang "
        f"noi mot dang con so tien noi mot dang khac")


def test_lot_binh_thuong_va_thu_theo_TOKEN_DA_DO(api, monkeypatch):
    # ⭐ Chi phí thật ĐÚNG 1,000 credit: 10.000 vào (500) + 1.250 ra (500).
    #    Đó là số duy nhất cho `thu == 1` ở CẢ C1 (làm tròn lên) lẫn C3 (chia
    #    lấy phần nguyên), nên `0 < thu < giu` bất biến với chính sách.
    goi = _dat_model(monkeypatch, token_vao=10_000, token_ra=1_250)
    user_id, token = _account()
    truoc = _so_du(user_id)

    r = api.post(DUONG, json=_than(
        messages=[{"role": "user", "content": "x" * 25_000}],
        max_tokens=1_800), headers=_h(token))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["object"] == "chat.completion"
    assert b["choices"][0]["message"]["content"] == "chao ban"
    assert b["usage"]["prompt_tokens"] == 10_000
    assert b["usage"]["completion_tokens"] == 1_250
    assert goi and goi[0]["model"] == "ltt_llm"

    thu = b["x_ltt"]["credit_charged"]
    assert thu == truoc - _so_du(user_id), "hoa don khong khop so du"
    assert 0 < thu < b["x_ltt"]["credit_held"], (
        "sinh 1.250 token ma thu tron phan da giu cho 1.800 token")
    assert _dem_execution_lease() == 0


def test_execution_slot_ban_tra_429_truoc_credit_va_model(api, monkeypatch):
    lease_id = _giu_execution_slot()
    called = _dat_model(monkeypatch)
    user_id, token = _account()
    before = _so_du(user_id)

    response = api.post(DUONG, json=_than(), headers=_h(token))

    assert response.status_code == 429, response.text
    assert response.json()["code"] == "concurrency_limited"
    assert response.headers["Retry-After"]
    assert called == []
    assert _so_du(user_id) == before
    from platform_core.llm import admission
    admission.release_by_id(lease_id)


def test_sinh_it_thi_tra_it_KHONG_tra_tron_tran(api, monkeypatch):
    """🔴 Đây đúng là lỗi tiền im lặng đã tìm ra ở cửa job hôm 23/08."""
    user_id, token = _account()

    than = _than(messages=[{"role": "user", "content": "x" * 25_000}],
                 max_tokens=1400)
    _dat_model(monkeypatch, token_vao=10_000, token_ra=20)
    a = api.post(DUONG, json=than, headers=_h(token)).json()

    _dat_model(monkeypatch, token_vao=10_000, token_ra=1_400)
    b = api.post(DUONG, json=than, headers=_h(token)).json()

    assert a["x_ltt"]["credit_charged"] < b["x_ltt"]["credit_charged"], (
        "hai luot sinh khac han nhau ma cung gia -> dang thu theo tran")


def test_khong_do_duoc_thi_HOAN_DU_va_khong_thu(api, monkeypatch):
    """⛔ Thu tiền mà không có bằng chứng còn tệ hơn mất một ít tiền."""
    _dat_model(monkeypatch, token_vao=999, token_ra=999, do_duoc=False)
    user_id, token = _account()
    truoc = _so_du(user_id)

    b = api.post(DUONG, json=_than(), headers=_h(token)).json()
    assert b["x_ltt"]["credit_charged"] == 0
    assert b["x_ltt"]["usage_measured"] is False
    assert _so_du(user_id) == truoc


def test_khong_du_tien_thi_KHONG_goi_model(api, monkeypatch):
    """Chốt đứng TRƯỚC GPU, không phải sau. Hết tiền thì không đốt card."""
    goi = _dat_model(monkeypatch)
    _user_id, token = _account(credits=0)

    r = api.post(DUONG, json=_than(), headers=_h(token))
    assert r.status_code in (402, 409), r.text
    assert goi == [], "da goi model roi moi phat hien khong du tien"


# ── 3. Bận ≠ hỏng ────────────────────────────────────────────────────────────

def test_may_B_ban_thi_503_co_Retry_After_va_HOAN_DU(api, monkeypatch):
    """🔴 D-005. Khách không trả tiền cho một lượt không chạy.

    ⚠️ **503, KHÔNG PHẢI 429 — và ranh giới đó có chủ ý.** Tôi viết 429 lúc đầu vì
       quen luật của `llm_gateway`, nơi *máy A đọc máy B* và 429 nghĩa là "bận".
       Ở bề mặt khách thì hai mã nói hai chuyện khác hẳn, và `error_registry` đã
       chốt: **429 = "bạn đang gọi quá nhanh"** (`rate_limited`,
       `concurrency_limited`, `quota_exceeded`), **503 = "máy không phục vụ được
       lúc này"** (`service_unavailable`). Máy B bận là vế sau — lỗi của khách thì
       không có, và bảo họ chậm lại cũng không giúp gì.

       `_refuse_if_no_capacity` ở cửa job trả lời đúng như vậy. Hai cửa phải nói
       cùng một ngôn ngữ, nếu không khách viết hai nhánh xử lý cho cùng một sự việc.

    Cả hai mã đều mang `Retry-After`, nên bên gọi tự động vẫn làm đúng việc."""
    from platform_core.llm.cong_vlm import BanError

    _dat_model(monkeypatch, nem=BanError("may B dang ban"))
    user_id, token = _account()
    truoc = _so_du(user_id)

    r = api.post(DUONG, json=_than(), headers=_h(token))
    assert r.status_code == 503, r.text
    assert int(r.headers.get("Retry-After", 0)) > 0
    assert _so_du(user_id) == truoc, "ban ma van thu tien"


def test_thuong_nguon_hong_thi_HOAN_DU(api, monkeypatch):
    from platform_core.llm.cong_vlm import CongVlmError

    _dat_model(monkeypatch, nem=CongVlmError("cong chet"))
    user_id, token = _account()
    truoc = _so_du(user_id)

    r = api.post(DUONG, json=_than(), headers=_h(token))
    assert r.status_code >= 500
    assert _so_du(user_id) == truoc, "loi ma van giu tien cua khach"


# ── 4. Idempotency ───────────────────────────────────────────────────────────

def test_thieu_idempotency_key_thi_TU_CHOI(api, monkeypatch):
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    r = api.post(DUONG, json=_than(),
                 headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400, r.text
    assert goi == []


def test_lap_lai_cung_khoa_KHONG_goi_model_lan_hai(api, monkeypatch):
    """Không có quote để đối chiếu, nên đây là toàn bộ hàng rào chống mua đúp."""
    goi = _dat_model(monkeypatch, token_vao=500, token_ra=200)
    user_id, token = _account()
    idem = uuid.uuid4().hex

    a = api.post(DUONG, json=_than(), headers=_h(token, idem))
    sau_lan_dau = _so_du(user_id)
    b = api.post(DUONG, json=_than(), headers=_h(token, idem))

    assert a.status_code == 200 and b.status_code == 200
    assert b.headers.get("Idempotency-Replayed") == "true"
    assert a.json() == b.json()
    assert len(goi) == 1, "goi model lan hai -> khach tra tien hai lan"
    assert _so_du(user_id) == sau_lan_dau, "tru tien lan hai"


# ── 5. Lời hứa của chế độ, đo bằng hành vi ──────────────────────────────────

def test_KHONG_tao_job(api, monkeypatch):
    """`SYNC_BILLED` hứa không đẩy vào hàng đợi. Đo, đừng tin."""
    _dat_model(monkeypatch)
    _user_id, token = _account()
    truoc = _dem_job()
    api.post(DUONG, json=_than(), headers=_h(token))
    assert _dem_job() == truoc


def test_max_tokens_vuot_tran_thoi_gian_thi_TU_CHOI_va_chi_sang_cua_job(api, monkeypatch):
    """⛔ Từ chối bằng 400 nói rõ lý do, thay vì để Cloudflare cắt bằng 524."""
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    from server.api.chat import _tran_max_tokens

    r = api.post(DUONG, json=_than(max_tokens=_tran_max_tokens(1) + 1),
                 headers=_h(token))
    assert r.status_code == 400, r.text
    assert "/api/v1/jobs" in r.text, "tu choi ma khong chi duong khac"
    assert goi == []


def test_tran_thoi_gian_dan_ra_tu_so_do_va_nam_duoi_tran_Cloudflare():
    from platform_core.public_api.protocol import SYNC_BILLED_MAX_SECONDS
    from server.api.chat import _tran_max_tokens

    assert SYNC_BILLED_MAX_SECONDS < 125, "phai nam DUOI tran 125s cua Cloudflare"
    assert 1_000 < _tran_max_tokens(1) <= 2_500


def test_input_cang_lon_thi_tran_output_dong_bo_cang_nho():
    """Prefill và decode dùng chung đồng hồ; không được chỉ tính output."""
    from server.api.chat import _tran_max_tokens

    ngan = _tran_max_tokens(100)
    vua = _tran_max_tokens(20_000)
    dai = _tran_max_tokens(65_000)  # cap Q116; sync gần cap vẫn dành cho stream/job
    assert ngan > vua > dai
    assert dai == 0, "request gần 65K phải đi stream/job, không được chạm GPU sync"


def test_input_gan_65K_bi_TU_CHOI_truoc_GPU_du_xin_output_nho(api, monkeypatch):
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    # 2,5 ký tự/token là phép ước đang dùng; 162.5K ký tự ~65K token + 1.
    than = _than(messages=[{"role": "user", "content": "x" * 162_500}],
                 max_tokens=100)

    r = api.post(DUONG, json=than, headers=_h(token))

    assert r.status_code == 400, r.text
    assert "/api/v1/jobs" in r.text
    assert "stream" in r.text.lower()
    assert goi == [], "admission phải từ chối trước khi chạm model/GPU"


def test_schema_tools_lon_cung_phai_tinh_vao_prefill(api, monkeypatch):
    """Agent gửi schema tool trong mỗi request; bỏ nó là ước thiếu input thật."""
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    cong_cu = [{
        "type": "function",
        "function": {
            "name": "tra_cuu",
            "description": "x" * 225_000,
            "parameters": {"type": "object", "properties": {}},
        },
    }]

    r = api.post(DUONG, json=_than(max_tokens=100, tools=cong_cu),
                 headers=_h(token))

    assert r.status_code == 400, r.text
    assert goi == [], "schema tool lớn phải bị admission chặn trước model/GPU"


def test_khong_khai_max_tokens_thi_dung_mac_dinh_AN_TOAN_cua_sync(api, monkeypatch):
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    than = _than()
    than.pop("max_tokens")

    r = api.post(DUONG, json=than, headers=_h(token))

    assert r.status_code == 200, r.text
    assert goi[0]["max_tokens"] == 1024


def test_stream_true_bi_TU_CHOI_ro_rang(api, monkeypatch):
    """Nhận rồi trả một lượt không-stream là nói dối SDK: nó đang chờ
    `text/event-stream` và sẽ vỡ ở chỗ khó lần hơn nhiều."""
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    r = api.post(DUONG, json=_than(stream=True), headers=_h(token))
    assert r.status_code == 400 and "stream" in r.text.lower()
    assert goi == []


def test_tham_so_sai_KHONG_toi_duoc_so_tien(api, monkeypatch):
    goi = _dat_model(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)
    r = api.post(DUONG, json={"messages": []}, headers=_h(token))
    assert r.status_code == 400
    assert goi == [] and _so_du(user_id) == truoc


def test_id_noi_bo_KHONG_goi_duoc_qua_cua_nay(api, monkeypatch):
    """Lớp đệm alias phải đứng ở CẢ HAI cửa, không chỉ cửa job."""
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    r = api.post(DUONG, json=_than(model="qwen38-api"), headers=_h(token))
    assert r.status_code == 400
    assert goi == []


# ── 6. Fail-closed: route có sẵn ≠ tool đã mở ───────────────────────────────

def test_chua_mo_tool_thi_route_van_song_nhung_TU_CHOI(tmp_path, monkeypatch):
    """⭐ Hai câu hỏi khác nhau. `/capabilities` nói "bản này BIẾT làm chat";
    `/tools` nói "tài khoản này ĐƯỢC gọi gì". Có route riêng KHÔNG cho `text.chat`
    đi vòng qua công tắc người vận hành (Q92)."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'c2.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "d2"))
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
        "LTT_SESSION_SECRET": "chat-secret-value-here",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
        "LTT_PUBLIC_API": "1",           # bat co, nhung TOOLS rong
    })
    try:
        with TestClient(app) as client:
            goi = _dat_model(monkeypatch)
            _user_id, token = _account()
            r = client.post(DUONG, json=_than(), headers=_h(token))
            assert r.status_code in (403, 404), r.text
            assert goi == []
            assert "chat" in client.get(f"{API_V1_PREFIX}/capabilities").json()[
                "capabilities"]
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        limits.reset()
        dbmod.reset_engine()


# ── 7. Chế độ thử: không chạm GPU, không chạm sổ tiền ───────────────────────

def test_che_do_thu_KHONG_goi_model_va_KHONG_thu_tien(api, monkeypatch):
    """⛔ ĐỪNG BỎ NHÁNH NÀY.

    Ở cửa job, một lượt thử vẫn chạy thật vì nó xếp hàng và chịu mọi hạn mức. Ở
    cửa đồng bộ thì nó chiếm card NGAY LẬP TỨC mà không ai trả tiền — tức là một
    cách miễn phí để giữ GPU của máy B, và khoá thử thì ai đăng ký cũng có."""
    from platform_core.public_api.sandbox import MODE_TEST

    goi = _dat_model(monkeypatch)
    user_id, token = _account(mode=MODE_TEST)
    truoc = _so_du(user_id)

    r = api.post(DUONG, json=_than(), headers=_h(token))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["x_ltt"]["test_mode"] is True
    assert b["x_ltt"]["credit_charged"] == 0
    assert goi == [], "khoa THU ma van dot GPU that"
    assert _so_du(user_id) == truoc


def test_che_do_thu_van_ton_trong_idempotency(api, monkeypatch):
    from platform_core.public_api.sandbox import MODE_TEST

    _dat_model(monkeypatch)
    _user_id, token = _account(mode=MODE_TEST)
    idem = uuid.uuid4().hex
    a = api.post(DUONG, json=_than(), headers=_h(token, idem))
    b = api.post(DUONG, json=_than(), headers=_h(token, idem))
    assert a.json() == b.json()
    assert b.headers.get("Idempotency-Replayed") == "true"


# ── 8. Giao dịch KHÔNG được trùm lên lượt gọi model ─────────────────────────

def test_giu_cho_da_CHOT_truoc_khi_goi_model(api, monkeypatch):
    """🔴 Ba thứ hỏng nếu giao dịch trùm lên cả 90 giây gọi model:

      1. `idempotency.begin` lay `pg_advisory_xact_lock`, song het giao dich ->
         yeu cau trung khoa TREO 90 giay thay vi nhan ngay "dang xu ly";
      2. mot ket noi CSDL bi giu suot luot goi -> N luot dong thoi la het pool,
         va thu chet truoc la nhung trang KHONG lien quan gi;
      3. tien trinh chet giua chung thi cuon nguoc xoa CA phan giu cho LAN ban
         ghi idempotency -> lan thu lai dot GPU them mot lan nua.

    Do bang cach nhin vao so du TU MOT PHIEN KHAC ngay giua luc model dang chay.
    Phien do chi thay duoc thu da commit."""
    from apps.ltt_llm import features

    user_id, token = _account()
    truoc = _so_du(user_id)
    thay_giua_chung = {}

    def gia(db, params, *, timeout_s=300.0):
        thay_giua_chung["so_du"] = _so_du(user_id)
        return features.KetQua(noi_dung="ok", suy_nghi="", tool_calls=(),
                               finish_reason="stop", model=params["model"],
                               token_vao=100, token_ra=50, token_vao_cache=0,
                               do_duoc=True)

    monkeypatch.setattr(features, "chay", gia)
    r = api.post(DUONG, json=_than(max_tokens=2000), headers=_h(token))
    assert r.status_code == 200, r.text
    assert thay_giua_chung["so_du"] < truoc, (
        "phien khac khong thay phan giu cho -> giao dich con dang mo suot "
        "luot goi model")


def test_bang_chung_idempotency_ton_tai_ngay_giua_luc_model_chay(api, monkeypatch):
    """Khoa da duoc chot, nen mot yeu cau trung khoa toi giua chung nhan cau tra
    loi DUNG ("dang xu ly") thay vi treo cho het luot."""
    from apps.ltt_llm import features
    from platform_core.public_api import idempotency

    _user_id, token = _account()
    idem = uuid.uuid4().hex
    thay = {}

    def gia(db, params, *, timeout_s=300.0):
        gen, db2 = _session()
        try:
            from platform_core.public_api.keys import DeveloperApiKey  # noqa: F401
            import sqlalchemy as sa
            from platform_core.models import ApiIdempotencyRecord
            thay["co"] = db2.execute(sa.select(
                sa.func.count(ApiIdempotencyRecord.id)).where(
                ApiIdempotencyRecord.idempotency_key == idem)).scalar_one()
        finally:
            _close(gen)
        return features.KetQua(noi_dung="ok", suy_nghi="", tool_calls=(),
                               finish_reason="stop", model=params["model"],
                               token_vao=10, token_ra=5, token_vao_cache=0,
                               do_duoc=True)

    monkeypatch.setattr(features, "chay", gia)
    assert api.post(DUONG, json=_than(), headers=_h(token, idem)).status_code == 200
    assert thay.get("co") == 1, "ban ghi idempotency chua duoc chot khi model chay"


# ── 9. SDK OpenAI thật, chạy vào chính route này ────────────────────────────
#
# ⭐ VÌ SAO DÙNG SDK THẬT CHỨ KHÔNG GIẢ LẬP NÓ. Cả lời hứa của Q106 lẫn cả chương
#    1b của `DEVELOPER_GUIDE.md` đứng trên một câu: *"trỏ base_url vào /api/v1 là
#    xong, trừ header Idempotency-Key"*. Câu đó chỉ đúng chừng nào SDK cư xử như
#    ta nghĩ. Giả lập SDK là giả lập luôn cái điều đang cần kiểm.
#
# 🔴 Và nó đã bắt được một điều tôi suýt viết sai vào tài liệu: SDK của OpenAI
#    **tự sinh** một khoá idempotency cho mỗi POST rồi **vứt đi**, vì nó chỉ gửi
#    khi `_idempotency_header` được đặt — với client OpenAI thì nó là `None`.

@pytest.fixture()
def sdk(api):
    """Client OpenAI thật, nói chuyện với chính app trong `api`."""
    openai = pytest.importorskip("openai")
    return openai


def _client(sdk, api, token, **them):
    return sdk.OpenAI(api_key=token, base_url="http://testserver/api/v1",
                      http_client=api, max_retries=0, **them)


def test_SDK_openai_goi_TRAN_thi_400_va_loi_DAY_CACH_SUA(sdk, api, monkeypatch):
    """⭐ Thông báo lỗi là trang tài liệu duy nhất chắc chắn được đọc.

    "Endpoint này cần header X" đúng nhưng vô dụng: người đọc đang dùng SDK và
    không biết chèn header vào đâu."""
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    c = _client(sdk, api, token)

    with pytest.raises(sdk.BadRequestError) as e:
        c.chat.completions.create(model="ltt_llm", max_tokens=100,
                                  messages=[{"role": "user", "content": "hi"}])
    loi = str(e.value)
    assert "Idempotency-Key" in loi
    assert "extra_headers" in loi, "loi khong day cach sua cho nguoi dung SDK"
    assert "default" in loi, "loi khong canh bao cai bay khoa co dinh"
    assert goi == [], "da tu choi ma van dot GPU"


def test_SDK_openai_kem_extra_headers_thi_CHAY(sdk, api, monkeypatch):
    """Đây đúng là đoạn mã `examples.openai_python_chat()` in ra cho khách."""
    _dat_model(monkeypatch, token_vao=12, token_ra=18)
    _user_id, token = _account()
    c = _client(sdk, api, token)

    r = c.chat.completions.create(
        model="ltt_llm", max_tokens=300,
        messages=[{"role": "user", "content": "Viet mot cau chao"}],
        extra_headers={"Idempotency-Key": uuid.uuid4().hex})

    assert r.choices[0].message.content == "chao ban"
    # `usage` giu DUNG hinh dang OpenAI de ma san co cua khach doc duoc...
    assert r.usage.prompt_tokens == 12 and r.usage.completion_tokens == 18
    # ...con thu cua ta nam trong `x_ltt`. Nhet vao `usage` se lam vo client
    # parse chat.
    assert r.model_extra["x_ltt"]["credit_charged"] >= 0


def test_BAY_khoa_co_dinh_o_default_headers(sdk, api, monkeypatch):
    """⛔ Cái bẫy mà tài liệu cảnh báo, hỏng theo HAI kiểu — và test này chốt cả hai.

    Người ta sẽ thử `default_headers` vì nó gọn hơn `extra_headers` mỗi lượt."""
    _dat_model(monkeypatch)
    _user_id, token = _account()
    c = _client(sdk, api, token,
                default_headers={"Idempotency-Key": "mot-khoa-cho-tat-ca"})

    def hoi(noi_dung):
        return c.chat.completions.create(
            model="ltt_llm", max_tokens=100,
            messages=[{"role": "user", "content": noi_dung}])

    hoi("thu do Viet Nam la gi")
    # Kieu ON AO: cau hoi khac -> 409. Kho chiu, nhung nhin thay duoc.
    with pytest.raises(sdk.ConflictError):
        hoi("thu do Nhat Ban la gi")
    # Kieu IM LANG, va la kieu nguy hiem: cau hoi GIONG HET -> nhan lai cau tra
    # loi cu, khong co luot chay moi nao, khong co dau hieu gi.
    lai = hoi("thu do Viet Nam la gi")
    assert lai.choices[0].message.content == "chao ban"


def test_vi_du_trong_tai_lieu_la_ma_CHAY_DUOC(sdk, api, monkeypatch):
    """Ví dụ ship cho khách phải biên dịch được, và phải mang header.

    ⛔ Một ví dụ "sạch đẹp" bỏ `Idempotency-Key` đi là một ví dụ không chạy, và
       người đọc sẽ kết luận API hỏng chứ không kết luận ví dụ sai."""
    from platform_core.public_api import examples

    for nhan, ma in examples.chat_snippets():
        assert "Idempotency-Key" in ma, f"vi du {nhan!r} thieu header bat buoc"
        assert "ltt_sk_" not in ma, f"vi du {nhan!r} co ve chua khoa that"
    # Loc theo NGON NGU, khong theo nhan: doi chu tren nhan khong duoc lam test
    # im lang bo qua viec kiem cu phap.
    python = [(n, m) for n, m in examples.chat_snippets() if n.startswith("Python")]
    assert len(python) >= 2, "mat vi du Python — test nay hoa ra khong kiem gi"
    for nhan, ma in python:
        compile(ma, f"<{nhan}>", "exec")          # cu phap phai dung

    ts = [m for n, m in examples.chat_snippets() if n.startswith("TypeScript")]
    assert ts, "mat vi du TypeScript"
    assert "extra_headers" not in ts[0],         "TypeScript dung `headers`, khong phai `extra_headers`"


# ── 10. Trang tài liệu thật sự dạy cửa này ──────────────────────────────────
#
# ⭐ Mã đúng mà tài liệu không nói thì khách vẫn không gọi được. Và tài liệu phải
#    theo đúng fail-closed của Q92: dạy một lời gọi mà tài khoản chưa gọi được
#    là dạy người ta gặp 403.

def _csrf(html: str) -> str:
    import re
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _dang_nhap(client) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"q-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 200, by="test")
        db.commit()
    finally:
        _close(gen)
    page = client.get("/login").text
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)
    return email


def test_quickstart_day_cua_chat_khi_tool_DA_MO(api):
    _dang_nhap(api)
    page = api.get("/developers/quickstart").text
    for manh in ("/api/v1/chat/completions", "Idempotency-Key", "extra_headers",
                 "default_headers", "base_url", "x_ltt", "credit_charged",
                 "ltt_llm", "503"):
        assert manh in page, f"trang quickstart thieu {manh!r}"


def test_quickstart_KHONG_day_cua_chat_khi_tool_chua_mo(tmp_path, monkeypatch):
    """Fail-closed của Q92 phải nhìn thấy được ở tài liệu, không chỉ ở máy chủ."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'q2.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "d3"))
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
        "LTT_SESSION_SECRET": "chat-secret-value-here",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "q.json"),
        "LTT_PUBLIC_API": "1",              # bat co, nhung TOOLS rong
    })
    try:
        with TestClient(app, base_url="https://testserver") as client:
            _dang_nhap(client)
            page = client.get("/developers/quickstart").text
            assert "/api/v1/chat/completions" not in page
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        limits.reset()
        dbmod.reset_engine()
