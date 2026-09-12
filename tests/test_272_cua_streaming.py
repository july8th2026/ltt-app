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

#: Ten model cong khai, doc tu `canonical` chu KHONG go tay: D02 cat
#: `ltt_llm`/`ltt_llm_vision` ngay 11/09/2026, va mot ten go tay o day se do
#: vi CHINH NO da cu chu khong vi cua hong.
from platform_core.llm.canonical import MODEL_MAC_DINH as MODEL

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
    d = {"model": MODEL, "stream": True, "max_tokens": 500,
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


def _giu_execution_slot() -> str:
    """Giữ hết suất của **model mặc định**, đọc tên tài nguyên từ BẢN KHAI.

    ⛔ Trước 11/09/2026 chỗ này gõ `resource="llm_remote"`. Từ dual-model 2.3
       sức chứa khai **theo model**, nên một tên gõ tay giành tài nguyên không
       ai dùng: cửa vẫn chạy thông, phép kiểm xanh, và nó thôi đo điều nó sinh
       ra để đo.
    """
    from platform_core.llm import admission
    from platform_core.llm.canonical import tai_nguyen_nha

    suc = tai_nguyen_nha(MODEL)
    gen, db = _session()
    try:
        # 🔴 MỘT LẦN `acquire` GIỮ MỘT SUẤT; `slots=` là **sức chứa**. Hai nghĩa
        #    ấy trùng nhau đúng chừng nào `SO_SLOT` = 1 — dual-model 2.6 nâng
        #    lên 3 (L-14) và hàm này chỉ còn giữ 1/3, tức cửa vẫn thông.
        cuoi = None
        for i in range(int(suc.slots)):
            lease = admission.acquire(
                db, resource=suc.resource, slots=suc.slots, user_id="u-khac",
                mode="job", holder_id=f"job-khac-{i}")
            assert lease is not None, f"khong giu duoc suat {i + 1}/{suc.slots}"
            cuoi = lease
        db.commit()
        assert cuoi is not None
        return cuoi.id
    finally:
        _close(gen)


def _dem_execution_lease() -> int:
    from platform_core.models import ExecutionLease
    gen, db = _session()
    try:
        return db.query(ExecutionLease).count()
    finally:
        _close(gen)


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
    assert _dem_execution_lease() == 0


# ── 3. Tiền: giữ TRẦN, thu THẬT ─────────────────────────────────────────────

def test_thu_theo_TOKEN_DA_SINH_khong_theo_tran(api, monkeypatch):
    # ⚠️ Ba nghin token RA = 1.200 mcredit > 1 credit. Con so nay KHONG tuy y:
    #    tu 05/09 phan le duoi 1 credit duoc TICH LUY (`users.mcredit_du`) chu
    #    khong lam tron len, nen mot kich ban vai chuc mcredit thu dung 0 va moi
    #    doi chung `thu > 0` ben duoi thanh vo nghia. Dung ha xuong.
    _dat_luong(monkeypatch, _khoi(vao=1_000, ra=3_000))
    user_id, token = _account()
    truoc = _so_du(user_id)
    api.post(MSG, json=_than(max_tokens=8000), headers=_h(token)).read()
    thu = truoc - _so_du(user_id)
    assert thu > 0, "khong thu gi ca"

    _dat_luong(monkeypatch, _khoi(vao=1_000, ra=6_000))
    truoc2 = _so_du(user_id)
    api.post(MSG, json=_than(max_tokens=8000), headers=_h(token)).read()
    thu2 = truoc2 - _so_du(user_id)
    assert thu2 > thu, "hai luot sinh khac han nhau ma cung gia -> thu theo tran"


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


def test_so_REQUEST_ghi_dung_so_tien_da_thu_o_cua_stream(api, monkeypatch):
    """🔴 P08 F-01 — cột này TỪNG luôn bằng 0 ở cửa stream, dù thu bao nhiêu.

    `request.state.api_credit_delta` chỉ được gán ở `server/api/jobs.py`. Cửa
    stream và cửa đồng bộ không gán lần nào, nên mọi dòng của chúng đọc ra `+0`.

    ⛔ Vì sao nó tệ hơn một cột trống: nó **giả làm bằng chứng**. `reports/06`
       chứng minh bất biến "bận thì không thu tiền" bằng câu *"89 lượt hỏng,
       credit=+0 mọi dòng"* — trên đúng cái cửa mà cột ấy không bao giờ khác 0.
       Một bằng chứng không thể sai thì không chứng minh gì.

    ⭐ Và `platform_core/public_api/anomalies.py` cộng chính cột này để dò bất
       thường tiền, nên nó mù với hai cửa khách dùng nhiều nhất.
    """
    # ⚠️ Ba nghin token RA = 1.200 mcredit > 1 credit. Con so nay KHONG tuy y:
    #    tu 05/09 phan le duoi 1 credit duoc TICH LUY (`users.mcredit_du`) chu
    #    khong lam tron len, nen mot kich ban vai chuc mcredit thu dung 0 va moi
    #    doi chung `thu > 0` ben duoi thanh vo nghia. Dung ha xuong.
    _dat_luong(monkeypatch, _khoi(vao=1_000, ra=3_000))
    user_id, token = _account()
    truoc = _so_du(user_id)
    api.post(MSG, json=_than(max_tokens=8000), headers=_h(token)).read()
    thu_that = truoc - _so_du(user_id)
    assert thu_that > 0, "doi chung TRUOT: khong thu gi ca, phep kiem duoi vo nghia"

    ghi = _credit_delta_da_ghi(user_id)
    assert ghi, "khong co dong nao trong so request"
    assert ghi[-1] == -thu_that, (
        f"so ghi {ghi[-1]} nhung so THAT bi tru la {-thu_that} — cot nay dang "
        f"noi mot dang con so tien noi mot dang khac")


def test_tools_sai_khuon_tra_400_QUA_HTTP(api, monkeypatch):
    """🔴 CÙNG HÌNH DẠNG VỚI `test_385`, NHƯNG ĐI QUA ĐƯỜNG HTTP THẬT.

    `test_385_tools_sai_khuon` kiểm hàm thuần `tool_dich.vi_sao_khong_dung_duoc`.
    Nó xanh suốt — trong khi bản vá trên production trả **500 thay vì 400**, và
    bộ test không thấy gì. Hồi quy sống trên máy khách hàng một buổi.

    ⛔ Đây không phải "không ai kiểm HTTP": giàn ngay trong tệp này đã có 25 phép
       kiểm qua `TestClient`. Khuyết tật hẹp hơn và khó chịu hơn — **hồi quy được
       chốt ở tầng hàm thuần dù giàn HTTP nằm sẵn bên cạnh**. Prompt 08 tìm thêm
       ba tệp cùng hình dạng (`test_285`, `test_290`, `test_360`), và cả ba đều
       canh đúng những lỗi mà *triệu chứng không chỉ về phía nguyên nhân*.

    ⭐ Phép kiểm này chốt **ba** thứ mà tầng hàm thuần không với tới được:
       mã trạng thái, thông điệp tới tay khách, và **không thu tiền**.
    """
    _dat_luong(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)

    than = _than()
    than["tools"] = [{"type": "function", "function": {
        "name": "tra_ton_kho", "parameters": {"type": "object"}}}]
    r = api.post(MSG, json=than, headers=_h(token))

    assert r.status_code == 400, (
        f"khuon OpenAI o cua Anthropic phai la 400, nhan {r.status_code}. "
        f"200 = tra loi hop ly ma sai; 500 = loi cua khach bi ke thanh loi cua ta")
    b = r.json()
    assert b.get("code") == "invalid_request", b
    assert "input_schema" in b.get("detail", ""), (
        "thong diep phai chi ra khuon DUNG, khong chi noi 'sai'")
    assert b.get("retry") == "never", "khuon sai thi thu lai khong bao gio giup"
    assert _so_du(user_id) == truoc, "yeu cau bi tu choi ma van thu tien"


def test_tools_khuon_DUNG_van_qua_HTTP(api, monkeypatch):
    """⛔ ĐỐI CHỨNG. Không có nó thì phép kiểm trên vẫn xanh khi cửa từ chối
    **mọi** `tools`, kể cả khuôn đúng — tức một hồi quy nặng hơn hẳn."""
    goi = _dat_luong(monkeypatch)
    _u, token = _account()
    than = _than()
    than["tools"] = [{"name": "tra_ton_kho", "description": "d",
                      "input_schema": {"type": "object", "properties": {}}}]
    r = api.post(MSG, json=than, headers=_h(token))
    assert r.status_code == 200, r.text
    assert goi, "khong goi toi model"


def test_so_REQUEST_ghi_dung_so_tien_o_nhanh_KHONG_STREAM(api, monkeypatch):
    """🔴 CÙNG route `/api/v1/messages`, nhưng ĐƯỜNG TIỀN THỨ HAI.

    Bản vá đầu của P08 F-01 chỉ chạm `_quyet_toan` — hàm chốt tiền của
    *generator*. Nhánh một-cục (`stream` vắng mặt, đường Claude Desktop dùng để
    thăm dò model) chốt tiền ở một chỗ khác và vẫn ghi `+0`.

    ⛔ Đo thật trên production ngay sau khi deploy bắt được, trong hai dòng liền
       nhau của cùng một route:

           18:12:29  200  /api/v1/messages   credit=-3   <- stream, DA SUA
           18:12:37  200  /api/v1/messages   credit=+0   <- mot cuc, CHUA SUA

    ⭐ Bài học đáng hơn khuyết tật: **một route có thể có hai đường tiền**, và
       đọc dòng log đầu tiên thấy số đúng là đủ để tin rằng đã xong.
    """
    # ⚠️ Nhánh một-cục KHÔNG đi qua `luong_vlm.mo` — nó gọi `features.chay`.
    # Dùng nhầm bộ giả là đo một đường khác và nhận `ThieuKeyError`.
    from apps.ltt_llm import features

    def _gia(db, params, *, timeout_s=300.0):
        return features.KetQua(
            noi_dung="chao ban", suy_nghi="", tool_calls=(), finish_reason="stop",
            # ⚠️ Đủ lớn để vượt 1 credit — để phép kiểm đúng cả khi bật C3
            #    (`LTT_TINH_TIEN_TICH_LUY=1`), lúc đó phần lẻ không bị làm tròn lên.
            model=params["model"], token_vao=8_000, token_ra=2_000,
            token_vao_cache=0, do_duoc=True)

    monkeypatch.setattr(features, "chay", _gia)
    user_id, token = _account()
    truoc = _so_du(user_id)
    than = _than(max_tokens=2_000)
    than.pop("stream", None)                      # <- KHAC BIET DUY NHAT
    r = api.post(MSG, json=than, headers=_h(token))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json"), (
        "khong phai nhanh mot-cuc -> phep kiem nay dang do nham duong")
    thu_that = truoc - _so_du(user_id)
    assert thu_that > 0, "doi chung TRUOT: nhanh mot-cuc khong thu gi"

    ghi = _credit_delta_da_ghi(user_id)
    assert ghi and ghi[-1] == -thu_that, (
        f"so ghi {ghi[-1] if ghi else None} != so that {-thu_that}")


def test_stream_het_slot_CHO_trong_SSE_roi_bao_overloaded_khong_giu_tien(api, monkeypatch):
    """multijob D-06 (đổi hợp đồng CÓ CHỦ Ý, chủ dự án chốt 11/09).

    Trước: hết slot ⇒ 429 ngay. Nay: 200 + SSE, chờ trong phòng chờ (nhịp tim),
    hết trần chờ ⇒ MỘT khối lỗi đúng khuôn Anthropic (`overloaded_error`).
    ⛔ Hai bất biến cũ GIỮ NGUYÊN: không gọi model, không đụng tiền (INV-MJ-1 —
       tiền chỉ giữ SAU khi được nhận).
    """
    monkeypatch.setenv("LTT_LLM_CHO_STREAM_S", "1")
    lease_id = _giu_execution_slot()
    called = _dat_luong(monkeypatch)
    user_id, token = _account()
    before = _so_du(user_id)
    from platform_core.db import get_session
    from platform_core.llm import admission
    from platform_core.models import CreditEntry, LlmWaiter

    def _so_but_toan():
        g = get_session()
        d = next(g)
        try:
            return d.query(CreditEntry).filter(CreditEntry.user_id == user_id).count()
        finally:
            d.close()

    but_toan_truoc = _so_but_toan()

    response = api.post(MSG, json=_than(), headers=_h(token))

    assert response.status_code == 200, response.text
    assert b"event: error" in response.content
    assert b"overloaded_error" in response.content
    assert called == []
    assert _so_du(user_id) == before
    # INV-MJ-1 theo nghĩa MẠNH: không phải "giữ rồi hoàn" (số dư cũng y nguyên) mà
    # là KHÔNG CÓ bút toán nào — lượt chờ không bao giờ chạm sổ tiền.
    assert _so_but_toan() == but_toan_truoc, "luot dang cho da cham so tien"
    gen = get_session()
    db = next(gen)
    try:
        # Sổ lượt ghi lại lượt chờ này và VÌ SAO nó không được nhận.
        w = db.query(LlmWaiter).filter(LlmWaiter.user_id == user_id).one()
        assert (w.trang_thai, w.ket_qua, w.ly_do_cho) == ("het_han", "het_cho", "cho_slot")
    finally:
        db.close()
    admission.release_by_id(lease_id)


def test_stream_qua_tran_vao_van_413_TRUOC_200(api, monkeypatch):
    """multijob D-06: 200 nay gửi trước khi chạm máy B — nhưng 413 phải vẫn là MÃ HTTP.

    Codex/Claude Code dựa vào HTTP 413 để tự nén hội thoại (`streaming.py`, nhánh
    413). Nếu "quá dài" chỉ tới dưới dạng sự kiện sau 200, client ngừng tự nén.
    """
    called = _dat_luong(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)
    # ⛔ DẪN XUẤT TỪ TRẦN, KHÔNG GÕ TAY: `450_000` ký tự (≈180.001 token) vượt
    #    trần 169.984 của hồ sơ 204.800 nhưng **lọt** trần 186.368 của hồ sơ
    #    221.184 (dual-model 2.6) — phép kiểm sẽ thôi đo 413 mà vẫn trông như đo.
    from apps.ltt_llm import ngan_sach
    qua_tran = int((ngan_sach.TOKEN_VAO_TRAN + 5_000) * ngan_sach.KY_TU_MOI_TOKEN)
    than = _than(messages=[{"role": "user", "content": "x" * qua_tran}])
    r = api.post(MSG, json=than, headers=_h(token))
    assert r.status_code == 413, r.text
    assert called == []
    assert _so_du(user_id) == truoc


def test_stream_tron_ven_ghi_so_luot_xong_va_whale(api, monkeypatch):
    """Sổ lượt (chủ dự án: 'log lưu để phân tích sau') ghi đủ một lượt trọn vẹn."""
    monkeypatch.setenv("LTT_LLM_NGUONG_WHALE", "1")      # mọi lượt đều là whale
    _dat_luong(monkeypatch)
    user_id, token = _account()
    r = api.post(MSG, json=_than(), headers=_h(token))
    assert r.status_code == 200
    r.read()
    from platform_core.db import get_session
    from platform_core.models import ExecutionLease, LlmWaiter
    gen = get_session()
    db = next(gen)
    try:
        w = db.query(LlmWaiter).filter(LlmWaiter.user_id == user_id).one()
        assert (w.trang_thai, w.ket_qua, w.cua, w.lop) == ("xong", "xong", "stream", "tuong_tac")
        assert w.la_whale is True and w.token_dat_truoc > 0
        assert w.admitted_at is not None and w.finished_at is not None
        # Lease đã nhả sau luồng — không slot nào rò.
        assert db.query(ExecutionLease).filter(ExecutionLease.id == w.lease_id).count() == 0
    finally:
        db.close()


def test_stream_phong_cho_day_thi_429_TRUOC_200(api, monkeypatch):
    """Phòng chờ có trần — không hàng vô hạn. Chạm trần ⇒ 429 khi còn đổi được mã HTTP."""
    monkeypatch.setenv("LTT_LLM_SO_NGUOI_CHO", "0")
    called = _dat_luong(monkeypatch)
    user_id, token = _account()
    before = _so_du(user_id)

    response = api.post(MSG, json=_than(), headers=_h(token))

    assert response.status_code == 429, response.text
    assert response.json()["code"] == "concurrency_limited"
    assert response.headers["Retry-After"]
    assert called == []
    assert _so_du(user_id) == before


def test_nonstream_execution_slot_cung_bi_chan_truoc_model(api, monkeypatch):
    lease_id = _giu_execution_slot()
    from apps.ltt_llm import features
    called = []
    monkeypatch.setattr(
        features, "chay",
        lambda *_args, **_kwargs: called.append(True))
    user_id, token = _account()
    before = _so_du(user_id)

    response = api.post(MSG, json=_than(stream=False), headers=_h(token))

    assert response.status_code == 429, response.text
    assert response.json()["code"] == "concurrency_limited"
    assert called == []
    assert _so_du(user_id) == before
    from platform_core.llm import admission
    admission.release_by_id(lease_id)


def test_CAT_GIUA_CHUNG_van_thu_dung_phan_da_sinh(api, monkeypatch):
    """🔴 Đây là ca mà cả thiết kế này sinh ra để xử. GPU đã đốt rồi."""
    # ⚠️ Ba nghin token RA = 1.200 mcredit > 1 credit. Con so nay KHONG tuy y:
    #    tu 05/09 phan le duoi 1 credit duoc TICH LUY (`users.mcredit_du`) chu
    #    khong lam tron len, nen mot kich ban vai chuc mcredit thu dung 0 va moi
    #    doi chung `thu > 0` ben duoi thanh vo nghia. Dung ha xuong.
    khoi = [_sse("message_start", {"message": {"usage": {"input_tokens": 500,
                                                         "output_tokens": 0}}}),
            _sse("message_delta", {"usage": {"output_tokens": 3_000}})]
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

def test_may_B_ban_sau_200_thi_su_kien_overloaded_va_HOAN_DU(api, monkeypatch):
    """🔴 D-005. Khách không trả tiền cho một lượt không chạy.

    multijob D-06: lượt đã được nhận (200 đã gửi, tiền đã giữ) rồi máy B mới báo
    bận ⇒ không còn 503 được nữa; thay bằng khối `overloaded_error` và phần giữ
    chỗ PHẢI được hoàn đủ — bất biến tiền không đổi.
    """
    _dat_luong(monkeypatch, ban=True)
    user_id, token = _account()
    truoc = _so_du(user_id)
    r = api.post(MSG, json=_than(), headers=_h(token))
    assert r.status_code == 200, r.text
    assert b"overloaded_error" in r.content
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
                 "Third-Party Inference", "inferenceModels", MODEL):
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
    assert examples.CLI_MODEL == MODEL


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
