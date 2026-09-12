"""test_1208_cua_dong_bo_cho — cửa ĐỒNG BỘ chờ trong phòng chờ (D04). (ltt-llm dual T1.5)

Trước D04, hai cửa đồng bộ (`/api/v1/chat/completions` và nhánh không-stream của
`/api/v1/messages`) trả **429 ngay** khi hết suất. D04 đổi: chúng **chờ** — nhưng
chờ ở ĐÚNG MỘT CHỖ, và chỗ đó là thứ cả tệp này canh.

## Vì sao chỗ chờ lại quan trọng hơn việc có chờ hay không

`idempotency.begin` lấy `pg_advisory_xact_lock` và khoá đó sống **hết giao dịch**
(`platform_core/public_api/idempotency.py:_lock`). Cửa cũ giành suất **trước**
`db.commit()`. Đặt điểm chờ ở đúng chỗ ấy nghĩa là: một lượt chờ 60 giây giữ khoá
idempotency 60 giây, nên **mọi** yêu cầu trùng khoá treo theo — kể cả lượt thử
lại lẽ ra phải nhận ngay câu "đang xử lý". Và nó giữ luôn một kết nối trong pool.

⇒ Trình tự D04, và `test_ban_ghi_idempotency_DA_COMMIT_khi_dang_cho` là phép đo
  trực tiếp của nó:

      kiểm tham số / trần vào (413) → số dư (402) → `idempotency.begin`
      → `db.commit()`  ← NHẢ KHOÁ, bản ghi nằm lại ở trạng thái "đang xử lý"
      → chờ phòng chờ ≤ min(60 s, ngân sách thời gian còn lại của cửa)
      → được nhận ⇒ GIỮ TIỀN ⇒ gọi máy B ⇒ quyết toán ⇒ nhả suất
      → hết giờ ⇒ 429 + `Retry-After`, đóng bản ghi, **0 khoản giữ**

## Bất biến tiền

* **INV-MJ-1** — đang chờ thì **không có dòng giữ tiền nào**. Không phải "giữ rồi
  hoàn": không có bút toán nào chạm sổ.
* **INV-MJ-2** — hết trần chờ ⇒ 0 khoản treo, 0 bút toán mồ côi.

## Đồng hồ

⛔ Không `time.sleep` thật lần nào. `luong.DONG_HO_CHO` / `luong.NGU_CHO` là hai
   seam có chủ ý: `NGU_CHO` đẩy đồng hồ giả đi, nên một trần chờ 60 giây chạy hết
   trong vài mili-giây — và, quan trọng hơn, **mỗi nhịp chờ là một điểm quan sát**
   mà phép kiểm chen vào được (nhả lease, đếm bút toán, bắn request thứ hai).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import mo_cu_tru_3090
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ)
from server.api.inventory import API_V1_PREFIX

#: Ten model cong khai, doc tu `canonical` chu KHONG go tay (D02, 2.3).
from platform_core.llm.canonical import MODEL_MAC_DINH as MODEL

PEPPER = "cho-test-pepper-" + "d" * 40
DUONG = f"{API_V1_PREFIX}/chat/completions"
MSG = f"{API_V1_PREFIX}/messages"
TOOL = "text.chat"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ)


# ── Khung (khuôn `test_259`/`test_272`: HTTP thật qua TestClient) ─────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'cho.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    # Luật 0 của admission (dual-model 5.3): một CSDL mới chưa nói card
    # 3090 đang là của ai, và fail-closed nghĩa là cửa LTT-3.8 đóng. Cửa
    # này là thứ tệp test đang kiểm, nên nó phải nói ra — như production.
    mo_cu_tru_3090()
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "cho-secret-value-here",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
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


def _account(credits: int = 10_000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"w-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return user.id, token
    finally:
        _close(gen)


def _h(token, idem=None):
    return {"Authorization": f"Bearer {token}",
            "Idempotency-Key": idem or uuid.uuid4().hex}


def _than(**ghi_de):
    d = {"model": MODEL, "messages": [{"role": "user", "content": "xin chao"}],
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


def _dem_but_toan(user_id: str) -> int:
    """Số bút toán credit của một khách. INV-MJ-1 đo bằng đúng con số này."""
    from platform_core.models import CreditEntry
    gen, db = _session()
    try:
        return int(db.query(CreditEntry)
                   .filter(CreditEntry.user_id == user_id).count())
    finally:
        _close(gen)


#: Người giữ chỗ giả trong `_giu_het_suat` — KHÔNG phải tài khoản đang thử.
NGUOI_GIU_CHO = "u-khac"


def _dem_lease() -> int:
    """Số lease **của lượt đang thử** — không đếm lease của người giữ chỗ.

    🔴 Bản cũ đếm TOÀN BỘ bảng và đúng chỉ vì `_giu_het_suat` tạo đúng một
       lease. Từ dual-model 2.6 nó tạo `SO_SLOT` = 3 cái, nên "0" trong các
       phép kiểm dưới đây sẽ là "2" mà chẳng có gì hỏng thật.

    ⭐ Mọi câu khẳng định ở tệp này đều là *"lượt CỦA TA không rò suất"*, nên
       phép đếm phải hỏi đúng câu đó. Lease của người giữ chỗ đếm riêng ở
       `_dem_lease_giu_cho()`.
    """
    from platform_core.models import ExecutionLease
    gen, db = _session()
    try:
        return int(db.query(ExecutionLease)
                   .filter(ExecutionLease.user_id != NGUOI_GIU_CHO).count())
    finally:
        _close(gen)


def _dem_lease_giu_cho() -> int:
    from platform_core.models import ExecutionLease
    gen, db = _session()
    try:
        return int(db.query(ExecutionLease)
                   .filter(ExecutionLease.user_id == NGUOI_GIU_CHO).count())
    finally:
        _close(gen)


def _so_suat() -> int:
    """Sức chứa của tài nguyên model mặc định, đọc từ **bản khai**."""
    from platform_core.llm.canonical import tai_nguyen_nha
    return int(tai_nguyen_nha(MODEL).slots)


def _ban_ghi_idem(key: str):
    """`(status, co_response)` của bản ghi idempotency, đọc ở PHIÊN KHÁC."""
    from platform_core.public_api.tables import ApiIdempotencyRecord
    gen, db = _session()
    try:
        r = (db.query(ApiIdempotencyRecord)
             .filter(ApiIdempotencyRecord.idempotency_key == key)
             .one_or_none())
        return None if r is None else (r.status, bool(r.response))
    finally:
        _close(gen)


def _dong_cho(user_id: str):
    from platform_core.models import LlmWaiter
    gen, db = _session()
    try:
        return [(w.trang_thai, w.ket_qua, w.ly_do_cho, w.cua, w.lop)
                for w in db.query(LlmWaiter)
                .filter(LlmWaiter.user_id == user_id).all()]
    finally:
        _close(gen)


def _giu_het_suat() -> str:
    """Những lượt khác giữ **trọn suất của model mặc định**.

    ⛔ Tên tài nguyên đọc từ BẢN KHAI, không gõ `"llm_remote"`: từ dual-model
       2.3 mỗi model có tài nguyên riêng, nên một tên gõ tay sẽ giữ một
       tài nguyên không ai dùng — cửa vẫn thông và phép kiểm xanh rỗng.

    🔴 VÀ SỐ SUẤT CŨNG PHẢI ĐỌC TỪ BẢN KHAI, KHÔNG CHỈ TÊN — một lần `acquire`
       giữ **một** suất, còn `slots=` là **sức chứa** của tài nguyên, không phải
       số suất người gọi lấy. Chừng nào `SO_SLOT` còn bằng 1 thì hai nghĩa ấy
       trùng nhau và không ai thấy khác biệt; dual-model 2.6 nâng lên **3**
       (L-14) và lập tức tám phép kiểm ở tệp này xanh rỗng — cửa còn 2 suất
       trống nên lượt thử **được nhận**, không hề chờ.

    ⭐ Nên hàm này lặp cho tới hết sức chứa. Nó trả id của lease **cuối**, giữ
       đúng giao ước cũ với bên gọi (chúng chỉ dùng id để nhả một suất ra).
    """
    from platform_core.llm import admission
    from platform_core.llm.canonical import tai_nguyen_nha

    suc = tai_nguyen_nha(MODEL)
    gen, db = _session()
    try:
        cuoi = None
        for i in range(int(suc.slots)):
            lease = admission.acquire(
                db, resource=suc.resource, slots=suc.slots, user_id=NGUOI_GIU_CHO,
                mode="job", holder_id=f"job-khac-{i}")
            assert lease is not None, f"khong giu duoc suat thu {i + 1}/{suc.slots}"
            cuoi = lease
        db.commit()
        assert cuoi is not None
        return cuoi.id
    finally:
        _close(gen)


def _dat_model(monkeypatch, *, token_vao=100, token_ra=50, do_duoc=True,
               truoc_khi_chay=None):
    """Thay `features.chay` — KHÔNG chạm máy B.

    ⚠️ Giữ NGUYÊN chữ ký `(db, params, *, timeout_s=…)`: đường tiền không được
       đòi thêm tham số ở `executor.run`, vì `apps/ltt_llm/executor.py` là hợp
       đồng app và mọi phép kiểm khác đã ghim vào hình dạng ấy.
    """
    from apps.ltt_llm import features
    goi = []

    def gia(db, params, *, timeout_s=300.0):
        goi.append(params)
        if truoc_khi_chay is not None:
            truoc_khi_chay()
        return features.KetQua(
            noi_dung="chao ban", suy_nghi="", tool_calls=(), finish_reason="stop",
            model=params["model"], token_vao=token_vao, token_ra=token_ra,
            token_vao_cache=0, do_duoc=do_duoc)

    monkeypatch.setattr(features, "chay", gia)
    return goi


class DongHoGia:
    """Đồng hồ tiêm. `ngu(s)` không ngủ — nó **đẩy đồng hồ**, rồi gọi `moi_nhip`."""

    def __init__(self, moi_nhip=None):
        self.t = datetime.now(timezone.utc)
        self.nhip = 0
        self.moi_nhip = moi_nhip
        self.da_ngu = 0.0

    def bay_gio(self) -> datetime:
        return self.t

    def ngu(self, s: float) -> None:
        self.da_ngu += float(s)
        self.t = self.t + timedelta(seconds=float(s))
        self.nhip += 1
        if self.moi_nhip is not None:
            self.moi_nhip(self.nhip)


def _tiem_dong_ho(monkeypatch, dong_ho: DongHoGia) -> None:
    from platform_core.runtime_noi_bo import luong

    monkeypatch.setattr(luong, "DONG_HO_CHO", dong_ho.bay_gio)
    monkeypatch.setattr(luong, "NGU_CHO", dong_ho.ngu)


# ── (a) Hết suất ⇒ CHỜ, và trong lúc chờ KHÔNG có dòng giữ tiền ─────────────

def test_het_suat_thi_CHO_va_dang_cho_KHONG_co_dong_giu_tien(api, monkeypatch):
    """INV-MJ-1 nghĩa MẠNH: không phải "giữ rồi hoàn" — **không bút toán nào**.

    Nhả lease ở nhịp thứ hai ⇒ lượt được nhận ⇒ 200. Tức phép kiểm chứng minh
    cả hai nửa: chờ được, và chờ xong thì chạy thật.
    """
    from platform_core.llm import admission

    lease_id = _giu_het_suat()
    goi = _dat_model(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)
    but_toan_truoc = _dem_but_toan(user_id)
    do_khi_cho: list = []

    def moi_nhip(n: int) -> None:
        if n == 1:
            do_khi_cho.append(("but_toan", _dem_but_toan(user_id)))
            do_khi_cho.append(("so_du", _so_du(user_id)))
        if n == 2:
            admission.release_by_id(lease_id)

    _tiem_dong_ho(monkeypatch, DongHoGia(moi_nhip))

    r = api.post(DUONG, json=_than(), headers=_h(token))

    assert r.status_code == 200, r.text
    assert len(goi) == 1, "duoc nhan roi ma khong goi model"
    assert do_khi_cho, "khong chờ nhịp nào — cửa van tra 429 ngay, D04 chua vao"
    assert dict(do_khi_cho)["but_toan"] == but_toan_truoc, (
        "dang CHO ma da co but toan credit — INV-MJ-1 vo")
    assert dict(do_khi_cho)["so_du"] == truoc, "dang cho ma so du da doi"
    # Được nhận rồi mới giữ tiền, rồi quyết toán ⇒ có thu, và không rò lease.
    assert _dem_but_toan(user_id) > but_toan_truoc
    assert _dem_lease() == 0, "lease ro sau khi xong"
    assert _dong_cho(user_id) == [("xong", "xong", "cho_slot", "sync", "tuong_tac")]


def test_ban_ghi_idempotency_DA_COMMIT_khi_dang_cho(api, monkeypatch):
    """🔴 ĐÂY LÀ PHÉP ĐO CỦA D04, KHÔNG PHẢI MỘT PHÉP KIỂM PHỤ.

    Đặt điểm chờ **trước** `db.commit()` thì bản ghi idempotency chưa tồn tại với
    bất kỳ phiên nào khác — và trên PostgreSQL nó còn giữ `pg_advisory_xact_lock`
    suốt lúc chờ. Đọc được bản ghi ở một phiên KHÁC, ở trạng thái "đang xử lý",
    trong lúc lượt còn đang chờ, là bằng chứng cơ học rằng giao dịch đã chốt.
    """
    from platform_core.llm import admission
    from platform_core.public_api.tables import IDEMPOTENCY_IN_PROGRESS

    lease_id = _giu_het_suat()
    _dat_model(monkeypatch)
    user_id, token = _account()
    key = "idem-" + uuid.uuid4().hex
    thay: list = []

    def moi_nhip(n: int) -> None:
        if n == 1:
            thay.append(_ban_ghi_idem(key))
        if n == 2:
            admission.release_by_id(lease_id)

    _tiem_dong_ho(monkeypatch, DongHoGia(moi_nhip))
    r = api.post(DUONG, json=_than(), headers=_h(token, idem=key))

    assert r.status_code == 200, r.text
    assert thay and thay[0] is not None, (
        "dang cho ma phien khac KHONG doc duoc ban ghi idempotency — giao dich "
        "cua request con mo, tuc diem cho dat TRUOC commit (sai D04)")
    assert thay[0] == (IDEMPOTENCY_IN_PROGRESS, False)
    assert _ban_ghi_idem(key) is not None


# ── (b) Không ai nhả ⇒ 429 + Retry-After, 0 khoản treo ──────────────────────

def test_het_tran_cho_thi_429_va_KHONG_mot_but_toan_nao(api, monkeypatch):
    """INV-MJ-2. Và bản ghi idempotency **không kẹt** "đang xử lý"."""
    monkeypatch.setenv("LTT_LLM_CHO_DONG_BO_S", "5")
    lease_id = _giu_het_suat()
    goi = _dat_model(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)
    but_toan_truoc = _dem_but_toan(user_id)
    key = "idem-" + uuid.uuid4().hex
    dong_ho = DongHoGia()
    _tiem_dong_ho(monkeypatch, dong_ho)

    r = api.post(DUONG, json=_than(), headers=_h(token, idem=key))

    assert r.status_code == 429, r.text
    assert r.json()["code"] == "concurrency_limited"
    assert r.headers["Retry-After"]
    assert goi == [], "het gio ma van goi model"
    assert _so_du(user_id) == truoc
    assert _dem_but_toan(user_id) == but_toan_truoc, (
        "het tran cho ma van co but toan — INV-MJ-2 vo")
    assert dong_ho.da_ngu >= 5.0, (
        "khong cho du tran — 429 nay la 429 cu, khong phai 429 sau khi cho")
    assert _dem_lease() == 0, "het gio cho ma luot CUA TA van giu mot suat"
    assert _dem_lease_giu_cho() == _so_suat(), (
        "nguoi giu cho phai van giu TRON suc chua — khong thi phep kiem nay "
        "khong con do canh gi (cua da thong tu truoc)")
    # Đóng bản ghi ⇒ lượt thử lại cùng khoá chạy được, không nhận 409 vĩnh viễn.
    trang_thai, _co = _ban_ghi_idem(key)
    from platform_core.public_api.tables import IDEMPOTENCY_IN_PROGRESS
    assert trang_thai != IDEMPOTENCY_IN_PROGRESS, (
        "ban ghi ket 'dang xu ly' — khach khong bao gio thu lai duoc khoa nay")

    # Đối chứng sống: thử lại CÙNG khoá, lần này có suất ⇒ phải chạy thật.
    from platform_core.llm import admission
    admission.release_by_id(lease_id)
    _tiem_dong_ho(monkeypatch, DongHoGia())
    r2 = api.post(DUONG, json=_than(), headers=_h(token, idem=key))
    assert r2.status_code == 200, r2.text
    assert len(goi) == 1


def test_tran_cho_bi_kep_boi_NGAN_SACH_THOI_GIAN_cua_cua():
    """min(60 s, ngân sách còn lại) — chờ không được ăn hết giờ của lời gọi model."""
    from platform_core.runtime_noi_bo import luong

    assert luong.han_cho_dong_bo(ngan_sach_s=90.0, da_tieu_s=0.0, tran_s=60.0) == 60.0
    # Ngân sách 30 s thì chờ tối đa 30 s, không phải 60.
    assert luong.han_cho_dong_bo(ngan_sach_s=30.0, da_tieu_s=0.0, tran_s=60.0) == 30.0
    # Đã tiêu 25 s ở khâu kiểm ⇒ còn 5 s.
    assert luong.han_cho_dong_bo(ngan_sach_s=30.0, da_tieu_s=25.0, tran_s=60.0) == 5.0
    # Tiêu quá ngân sách ⇒ không chờ nữa, không âm.
    assert luong.han_cho_dong_bo(ngan_sach_s=30.0, da_tieu_s=40.0, tran_s=60.0) == 0.0


# ── Hai cổng ĐỨNG TRƯỚC phòng chờ: 413 (trần vào) và 402 (số dư) ───────────
#
# ⭐ Cả hai đều là "câu trả lời đã biết trước". Để một lượt quá dài hoặc một
#    khách hết tiền vào phòng chờ là bắt họ chờ 60 giây để nghe một chữ KHÔNG mà
#    ta đã biết ngay từ đầu — và giữ một chỗ trong hàng của người khác.

def test_qua_TRAN_VAO_thi_413_TRUOC_ca_phong_cho_lan_tien(api, monkeypatch):
    """413 đứng trước mọi thứ (spec §6), kể cả trước lúc giành/chờ suất.

    ⛔ Và nó phải là **mã HTTP 413**: Codex/Claude Code dựa đúng vào mã ấy để
       TỰ NÉN hội thoại. Một câu 400 chung chung làm client ngừng tự nén.
    """
    lease_id = _giu_het_suat()          # hết suất: nếu 413 đi sau, lượt sẽ CHỜ
    goi = _dat_model(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)
    but_toan_truoc = _dem_but_toan(user_id)

    def cam_cho(*a, **k):               # noqa: ANN002, ANN003
        raise AssertionError("qua tran vao ma van vao phong cho")

    from platform_core.runtime_noi_bo import luong
    monkeypatch.setattr(luong, "cho_suat_dong_bo", cam_cho)

    # ⛔ ĐỘ DÀI PHẢI DẪN XUẤT TỪ TRẦN, KHÔNG GÕ TAY. Bản đầu gõ `450_000` ký tự
    #    — vượt trần 169.984 token của hồ sơ 204.800. Dual-model 2.6 nâng cửa sổ
    #    lên 221.184 ⇒ trần vào thành 186.368 ⇒ 450.000 ký tự (≈180.001 token)
    #    **lọt**, và 413 đổi thành 400 của ngân sách thời gian. Phép kiểm không
    #    bắt được gì nữa mà vẫn trông như đang bắt.
    from apps.ltt_llm import ngan_sach
    qua_tran = int((ngan_sach.TOKEN_VAO_TRAN + 5_000) * ngan_sach.KY_TU_MOI_TOKEN)
    r = api.post(DUONG, json=_than(messages=[{"role": "user",
                                              "content": "x" * qua_tran}],
                                   max_tokens=16),
                 headers=_h(token))

    assert r.status_code == 413, r.text
    assert goi == [], "qua tran vao ma van cham model"
    assert _so_du(user_id) == truoc
    assert _dem_but_toan(user_id) == but_toan_truoc, "413 ma da cham so tien"
    assert _dong_cho(user_id) == [], "413 ma van ghi mot dong cho"
    from platform_core.llm import admission
    admission.release_by_id(lease_id)


def test_khong_du_so_du_thi_402_TRUOC_phong_cho_va_0_khoan_giu(api, monkeypatch):
    """402 chỉ ĐỌC số dư — không giữ đồng nào, không lease, không dòng chờ."""
    goi = _dat_model(monkeypatch)
    user_id, token = _account(credits=0)
    but_toan_truoc = _dem_but_toan(user_id)

    def cam_cho(*a, **k):               # noqa: ANN002, ANN003
        raise AssertionError("het tien ma van vao phong cho")

    from platform_core.runtime_noi_bo import luong
    monkeypatch.setattr(luong, "cho_suat_dong_bo", cam_cho)

    r = api.post(DUONG, json=_than(), headers=_h(token))

    # ⚠️ Spec §6 viết "402"; nền tảng này trả **409 `insufficient_credit`** cho
    #    mọi cửa (`errors.insufficient_credit`), và `test_259`/`test_272` đã ghim
    #    con số ấy từ trước. Đổi mã HTTP là đổi hợp đồng công khai — ngoài phạm
    #    vi task này. Nên chot theo `code` ỔN ĐỊNH, không theo chữ trong spec.
    assert r.json()["code"] == "insufficient_credit", r.text
    assert r.status_code == 409, r.text
    assert goi == [], "het tien ma van dot GPU"
    assert _dem_but_toan(user_id) == but_toan_truoc, "402 ma da co but toan"
    assert _dem_lease() == 0, "402 ma van giu mot suat"
    assert _dong_cho(user_id) == []


def test_het_tien_o_cua_MOT_CUC_cung_402_truoc_phong_cho(api, monkeypatch):
    goi = _dat_model(monkeypatch)
    user_id, token = _account(credits=0)

    def cam_cho(*a, **k):               # noqa: ANN002, ANN003
        raise AssertionError("het tien ma van vao phong cho")

    from platform_core.runtime_noi_bo import luong
    monkeypatch.setattr(luong, "cho_suat_dong_bo", cam_cho)

    r = api.post(MSG, json={"model": MODEL, "max_tokens": 200,
                            "messages": [{"role": "user", "content": "hi"}]},
                 headers={"Authorization": f"Bearer {token}"})

    assert r.json()["code"] == "insufficient_credit", r.text
    assert goi == []
    assert _dem_lease() == 0


# ── Ngân sách thời gian: CHỜ và GỌI ăn chung MỘT đồng hồ ────────────────────

def test_loi_goi_model_nhan_ngan_sach_CON_LAI_khong_phai_tran_nguyen(api, monkeypatch):
    """🔴 Chờ 60 s rồi chạy thêm 90 s = 150 s ⇒ đúng cái 524 của Cloudflare.

    Bản đầu đặt mốc đồng hồ **sau** phòng chờ, nên phép trừ "trần − đã tiêu"
    luôn ra gần đúng trần và không kẹp gì cả. Phép kiểm này đo thứ duy nhất
    chứng minh được điều ngược lại: `timeout_s` mà lời gọi model thật sự nhận.
    """
    from platform_core.public_api.protocol import SYNC_BILLED_MAX_SECONDS

    lease_id = _giu_het_suat()
    nhan: list = []

    from apps.ltt_llm import features

    def gia(db, params, *, timeout_s=300.0):
        nhan.append(timeout_s)
        return features.KetQua(
            noi_dung="chao", suy_nghi="", tool_calls=(), finish_reason="stop",
            model=params["model"], token_vao=10, token_ra=5,
            token_vao_cache=0, do_duoc=True)

    monkeypatch.setattr(features, "chay", gia)
    _user_id, token = _account()

    from platform_core.llm import admission

    # Đồng hồ giả đẩy 30 giây mỗi nhịp; nhả lease ở nhịp 2 ⇒ đã "chờ" 60 giây.
    dong_ho = DongHoGia()
    dong_ho_that = {"tieu": 0.0}

    def moi_nhip(n: int) -> None:
        dong_ho_that["tieu"] += 30.0
        if n >= 2:
            admission.release_by_id(lease_id)

    dong_ho.moi_nhip = moi_nhip
    _tiem_dong_ho(monkeypatch, dong_ho)

    # `_con_lai_s` đọc `time.monotonic()` thật, nên tiêm luôn cái đó: mỗi nhịp
    # chờ cộng 30 giây vào đồng hồ mà cửa dùng để tính ngân sách.
    import server.api.chat as chat_mod
    goc = chat_mod.time.monotonic
    monkeypatch.setattr(chat_mod.time, "monotonic",
                        lambda: goc() + dong_ho_that["tieu"], raising=False)

    r = api.post(DUONG, json=_than(), headers=_h(token))

    assert r.status_code == 200, r.text
    assert nhan, "khong goi model"
    assert nhan[0] < float(SYNC_BILLED_MAX_SECONDS) - 50, (
        f"loi goi model nhan {nhan[0]}s sau khi da cho ~60s — ngan sach "
        f"KHONG bi tru, tong se vuot dong ho Cloudflare")


# ── (c) Hai request cùng khoá cùng chờ ⇒ đúng MỘT lượt chạy model ───────────

def test_hai_request_cung_khoa_cung_cho_thi_dung_MOT_luot_chay_model(api, monkeypatch):
    """Lượt thứ hai nhận 409 "đang xử lý" — **không** treo, **không** gọi model.

    ⭐ Chính vì bản ghi đã commit (phép kiểm trên) mà lượt thứ hai trả lời được
       ngay. Cửa cũ giữ khoá advisory suốt lượt gọi ⇒ lượt thứ hai treo theo.
    """
    from platform_core.llm import admission

    lease_id = _giu_het_suat()
    goi = _dat_model(monkeypatch)
    _user_id, token = _account()
    key = "idem-" + uuid.uuid4().hex
    thu_hai: list = []

    def moi_nhip(n: int) -> None:
        if n == 1:
            # Phiên/cổng HTTP KHÁC, trong lúc lượt đầu còn đang chờ.
            khach = TestClient(api.app, base_url="https://testserver")
            r2 = khach.post(DUONG, json=_than(), headers=_h(token, idem=key))
            thu_hai.append((r2.status_code, r2.json().get("code")))
        if n == 2:
            admission.release_by_id(lease_id)

    _tiem_dong_ho(monkeypatch, DongHoGia(moi_nhip))
    r1 = api.post(DUONG, json=_than(), headers=_h(token, idem=key))

    assert r1.status_code == 200, r1.text
    assert thu_hai, "khong ban duoc request thu hai"
    assert thu_hai[0][0] == 409, f"luot trung khoa phai 409, nhan {thu_hai[0]}"
    assert len(goi) == 1, "hai request cung khoa ma model chay hai lan"


# ── (d) Planner: lớp `noi_bo`, KHÔNG chờ ────────────────────────────────────

def test_planner_di_lop_NOI_BO_va_mang_dat_cho(monkeypatch):
    """Spec §6 dòng Planner: lớp `noi_bo`, một lần thử, không lấy slot chừa."""
    from platform_core.agent import planner
    from platform_core.llm import admission, dieu_phoi, luat_nhan

    da_giu: dict = {}

    class VeGia:
        id = "lease-gia"

    def gia_acquire(db, *, resource, slots, user_id, mode, holder_id, **luat):
        da_giu.update(luat)
        da_giu["resource"] = resource
        return VeGia()

    class KetQua:
        noi_dung = '{"version":1,"steps":[]}'

    monkeypatch.setattr(admission, "acquire", gia_acquire)
    monkeypatch.setattr(admission, "release_by_id", lambda i: None)
    monkeypatch.setattr(dieu_phoi, "goi", lambda db, **kw: KetQua())

    planner._goi_model(None, "prompt thu")

    assert da_giu.get("lop") == luat_nhan.NOI_BO, (
        "planner van di lop mac dinh — mot viec noi bo dang tranh cho nhu khach")
    assert int(da_giu.get("token_dat_truoc", 0)) > 0, (
        "lease planner khong mang dat cho ⇒ vo hinh voi so ngan sach KV")
    assert int(da_giu.get("token_dat_truoc", 0)) <= int(da_giu.get("token_pool", 0))


def test_planner_KHONG_CHO_khi_het_cho(monkeypatch):
    """Hết chỗ ⇒ hỏng **có tên** ngay, không một dòng phòng chờ nào."""
    from platform_core.agent import planner
    from platform_core.llm import admission, dieu_phoi, phong_cho

    monkeypatch.setattr(admission, "acquire", lambda db, **kw: None)

    def cam(*a, **k):                       # noqa: ANN002, ANN003
        raise AssertionError("planner da xep hang cho — sai D-03")

    monkeypatch.setattr(phong_cho, "vao", cam)
    monkeypatch.setattr(phong_cho, "cho_nhan_chan", cam)

    def cam_goi(db, **kw):                  # noqa: ANN001, ANN003
        raise AssertionError("het suat ma van cham may B")

    monkeypatch.setattr(dieu_phoi, "goi", cam_goi)

    with pytest.raises(planner.PlannerError) as loi:
        planner._goi_model(None, "prompt thu")
    assert "admission" in str(loi.value)


# ── (e) Khách ngắt TRONG LÚC gọi model (spec §16) ───────────────────────────

def test_khach_ngat_giua_luot_thi_DONG_HTTPX_nha_lease_va_khong_treo_tien(
        api, monkeypatch):
    """Đóng client httpx tới máy B, nhả suất, không để lại khoản giữ mồ côi.

    Không đo được `usage` ⇒ **hoàn trọn** (INV-003 và luật chung của cửa).
    """
    import threading

    from platform_core.llm import ngat
    from platform_core.llm.cong_vlm import CongVlmError

    da_dong: list = []
    da_dong_xong = threading.Event()

    from apps.ltt_llm import features
    goi = []

    def gia(db, params, *, timeout_s=300.0):
        """Máy B "đang chạy": ghi nhận cửa ra mạng rồi **chờ cửa ấy bị đóng**.

        ⚠️ Chờ bằng `Event` chứ không ngủ: lượt này phải còn sống ở đúng lúc cửa
           thăm `is_disconnected`, nếu không phép kiểm đo một cuộc đua chứ không
           đo hành vi.
        """
        goi.append(params)
        ngat.ghi_nhan(lambda: (da_dong.append("httpx"), da_dong_xong.set()))
        assert da_dong_xong.wait(10), "cua KHONG dong httpx khi khach ngat"
        # Đóng httpx ⇒ lời gọi thật vỡ đúng như đường `AmbiguousProviderError`.
        raise CongVlmError("ket noi bi dong giua chung")

    monkeypatch.setattr(features, "chay", gia)
    # Khách ngắt ngay ở nhịp thăm đầu tiên.
    monkeypatch.setattr(ngat, "do_ngat", lambda request: (lambda: True))
    monkeypatch.setattr(ngat, "NHIP_THAM_S", 0.0)

    user_id, token = _account()
    truoc = _so_du(user_id)
    but_toan_truoc = _dem_but_toan(user_id)

    r = api.post(DUONG, json=_than(), headers=_h(token))

    assert goi, "chua cham model lan nao — phep kiem khong do dung thu no noi"
    assert da_dong == ["httpx"], (
        "khach ngat ma khong dong client httpx toi may B — llama.cpp giu slot")
    assert r.status_code in (499, 503), r.text
    assert _dem_lease() == 0, "lease ro sau khi khach ngat"
    assert _so_du(user_id) == truoc, "khach ngat ma van bi thu tien"
    # Hoàn trọn: bút toán giữ + bút toán hoàn, hoặc không bút toán nào; điều
    # KHÔNG được phép là một khoản giữ nằm lại.
    assert _so_du(user_id) == truoc
    assert _dem_but_toan(user_id) >= but_toan_truoc


def test_khach_ngat_SAU_KHI_model_da_chay_thi_KHOA_bi_CHOT_khong_mo_lai(
        api, monkeypatch):
    """🔴 BẢN ĐẦU THU TIỀN HAI LẦN. Rà soát 1.5 bắt được, phép kiểm này ghim.

    Khách ngắt **sau** khi lời gọi đã về: model đã chạy, tiền đã thu theo
    `usage`. Bản đầu vẫn gọi `_mo_lai_khoa` ⇒ bản ghi thành `failed` ⇒
    `idempotency.begin` NHẬN LẠI nó với `replay=False` ⇒ lượt thử lại cùng khoá
    chạy model **lần hai** và thu **lần hai**. Đúng thứ INV-011/012 cấm, và
    đúng thứ chú thích ⛔ của `mo_lai` tự nói là không được làm.

    ⇒ Có `usage` ⇒ `complete` với câu trả lời; thử lại ⇒ **replay**, miễn phí.
    """
    from platform_core.llm import ngat
    from platform_core.public_api.tables import IDEMPOTENCY_COMPLETED

    goi = _dat_model(monkeypatch, token_vao=1_000, token_ra=3_000)
    # Khách "đã đi", nhưng lời gọi kịp về: nhịp thăm chỉ chạy sau khi luồng
    # gọi model kết thúc, nên `KhachNgat.ket_qua` mang kết quả thật.
    monkeypatch.setattr(ngat, "do_ngat", lambda request: (lambda: True))

    def canh_gia(chay, *, ngat_chua=None, nhip_s=None):
        """Đúng ngữ nghĩa của ca này: lời gọi XONG rồi mới phát hiện khách đi."""
        with ngat.so_dong():
            return_value = chay()
        raise ngat.KhachNgat(return_value)

    monkeypatch.setattr(ngat, "chay_canh_ngat", canh_gia)

    user_id, token = _account()
    key = "idem-" + uuid.uuid4().hex
    truoc = _so_du(user_id)

    r1 = api.post(DUONG, json=_than(), headers=_h(token, idem=key))
    assert len(goi) == 1, "chua goi model lan nao"
    thu = truoc - _so_du(user_id)
    assert thu > 0, "doi chung TRUOT: luot nay khong thu gi, phep kiem vo nghia"
    assert _ban_ghi_idem(key) == (IDEMPOTENCY_COMPLETED, True), (
        "khoa bi MO LAI sau mot luot da thu tien — luot thu lai se thu lan hai")

    # Thử lại cùng khoá: replay, KHÔNG chạy model, KHÔNG thu thêm.
    sau_lan_mot = _so_du(user_id)
    r2 = api.post(DUONG, json=_than(), headers=_h(token, idem=key))
    assert r2.status_code == 200, r2.text
    assert r2.headers.get("Idempotency-Replayed") == "true"
    assert len(goi) == 1, "thu lai cung khoa ma model chay LAN HAI"
    assert _so_du(user_id) == sau_lan_mot, "thu lai cung khoa ma THU LAN HAI"
    assert r1.status_code in (200, 499)
    assert _dem_lease() == 0


def test_so_luot_ghi_KET_CUC_THAT_khong_phai_luon_luon_xong(api, monkeypatch):
    """Sổ 30 ngày chỉ biết nói "xong" thì nó không phân tích được gì.

    Chủ dự án giữ `llm_waiters` **để phân tích sau**; một cột kết cục ghi cứng
    một chữ là một cột giả làm bằng chứng.
    """
    from platform_core.llm.cong_vlm import BanError

    from apps.ltt_llm import features

    def gia(db, params, *, timeout_s=300.0):
        raise BanError("3/3 suat dang dung")

    monkeypatch.setattr(features, "chay", gia)
    user_id, token = _account()
    _tiem_dong_ho(monkeypatch, DongHoGia())

    r = api.post(DUONG, json=_than(), headers=_h(token))

    assert r.status_code == 503, r.text
    assert _dong_cho(user_id) == [("xong", "ban", "", "sync", "tuong_tac")], (
        "so luot ghi ket cuc SAI — mot luot BAN vao so duoi chu 'xong'")


# ── Nhánh không-stream của `/messages` đi cùng một trình tự ──────────────────

def test_mot_cuc_cung_CHO_va_khong_giu_tien_luc_cho(api, monkeypatch):
    """`_mot_cuc` là cửa đồng bộ thứ hai — cùng D04, cùng bất biến tiền."""
    from platform_core.llm import admission

    lease_id = _giu_het_suat()
    goi = _dat_model(monkeypatch)
    user_id, _token = _account()
    user_id, token = user_id, _token
    but_toan_truoc = _dem_but_toan(user_id)
    khi_cho: list = []

    def moi_nhip(n: int) -> None:
        if n == 1:
            khi_cho.append(_dem_but_toan(user_id))
        if n == 2:
            admission.release_by_id(lease_id)

    _tiem_dong_ho(monkeypatch, DongHoGia(moi_nhip))
    r = api.post(MSG, json={"model": MODEL, "max_tokens": 200,
                            "messages": [{"role": "user", "content": "hi"}]},
                 headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200, r.text
    assert len(goi) == 1
    assert khi_cho == [but_toan_truoc], "dang cho ma da giu tien o `_mot_cuc`"
    assert _dem_lease() == 0


def test_mot_cuc_het_tran_cho_thi_429_khong_but_toan(api, monkeypatch):
    monkeypatch.setenv("LTT_LLM_CHO_DONG_BO_S", "3")
    _giu_het_suat()
    goi = _dat_model(monkeypatch)
    user_id, token = _account()
    but_toan_truoc = _dem_but_toan(user_id)
    _tiem_dong_ho(monkeypatch, DongHoGia())

    r = api.post(MSG, json={"model": MODEL, "max_tokens": 200,
                            "messages": [{"role": "user", "content": "hi"}]},
                 headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 429, r.text
    assert r.headers["Retry-After"]
    assert goi == []
    assert _dem_but_toan(user_id) == but_toan_truoc


# ── `luat_cho`: MỘT phép tính đặt chỗ cho năm chỗ gọi ───────────────────────

def test_luat_cho_kep_ve_pool_va_tra_rong_khi_khong_co_pool():
    from platform_core.llm import luat_nhan, tham_so_da_luot

    assert tham_so_da_luot.luat_cho(0, lop=luat_nhan.TUONG_TAC,
                                    token_vao_uoc=10, xin_ra=10) == {}
    ts = tham_so_da_luot.doc()
    ra = tham_so_da_luot.luat_cho(100_000, lop=luat_nhan.NEN,
                                  token_vao_uoc=10, xin_ra=20)
    assert ra["lop"] == luat_nhan.NEN and ra["token_pool"] == 100_000
    assert ra["token_dat_truoc"] == 30 + ts.dem_dat_truoc
    # Ảnh cũng vào phép tính, cùng một chỗ.
    co_anh = tham_so_da_luot.luat_cho(100_000, lop=luat_nhan.NEN,
                                      token_vao_uoc=10, xin_ra=20, so_anh=2)
    assert co_anh["token_dat_truoc"] == 30 + ts.dem_dat_truoc + 2 * ts.token_moi_anh
    # ⛔ Kẹp về pool: một lượt dùng trọn cửa sổ + đệm + ảnh KHÔNG BAO GIỜ được
    #    nhận nếu không kẹp, dù engine phục vụ được nó khi chạy một mình.
    lon = tham_so_da_luot.luat_cho(1_000, lop=luat_nhan.TUONG_TAC,
                                   token_vao_uoc=900, xin_ra=900, so_anh=4)
    assert lon["token_dat_truoc"] == 1_000


def test_cua_stream_va_cua_job_dung_CHUNG_phep_tinh_luat_cho():
    """⭐ Năm bản sao của một phép tính là năm chỗ lệch nhau."""
    import ast
    import pathlib

    goc = pathlib.Path(__file__).resolve().parents[1]
    for ten in ("platform_core/runtime_noi_bo/luong.py",
                "platform_core/job_runner.py",
                "platform_core/agent/planner.py"):
        ma = (goc / ten).read_text(encoding="utf-8")
        assert "luat_cho(" in ma, f"{ten} chua di qua `tham_so_da_luot.luat_cho`"
    # Và không còn bản sao tự cộng `dem_dat_truoc` ngoài chính `luat_cho`.
    cay = ast.parse((goc / "platform_core/runtime_noi_bo/luong.py")
                    .read_text(encoding="utf-8"))
    thay = [n for n in ast.walk(cay)
            if isinstance(n, ast.Attribute) and n.attr == "dem_dat_truoc"]
    assert not thay, ("luong.py van tu cong `dem_dat_truoc` — ban sao thu hai "
                      "cua phep tinh dat cho")


# ── ĐỐI CHỨNG: đặt điểm chờ TRƯỚC commit thì khoá idempotency bị giữ ────────

@pytest.mark.skipif(True, reason=(
    "Doi chung can PostgreSQL that: `pg_advisory_xact_lock` cua "
    "`idempotency._lock` la KHONG-OP tren SQLite (xem `idempotency._lock`), nen "
    "tren SQLite phep kiem nay xanh ca khi diem cho dat SAI cho. Khuon chay "
    "that o `tests/test_73_dong_thoi_pg.py` (bien `LTT_TEST_PG_URL`). Doi chung "
    "CHAY DUOC tren SQLite la "
    "`test_ban_ghi_idempotency_DA_COMMIT_khi_dang_cho`: no do dung mot nua co "
    "the do duoc o day — ban ghi da commit hay chua."))
def test_doi_chung_cho_truoc_commit_giu_khoa_idempotency():   # pragma: no cover
    """Tiêm bản CŨ (chờ trước `db.commit()`) ⇒ lượt trùng khoá phải TREO.

    Trên PostgreSQL: mở một giao dịch lấy `pg_advisory_xact_lock` cùng khoá rồi
    đo rằng phiên thứ hai không lấy được — tức chờ ở đó là chờ **thay cho** mọi
    lượt trùng khoá.
    """
    raise AssertionError("chi chay tren PostgreSQL")
