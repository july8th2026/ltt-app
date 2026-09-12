"""test_1234 — L-01: mot luot goi model KHONG duoc giu khoa hang `api_keys`.

## Bat bien no giu

`api_pool.chon_key()` cap phat mot khoa dung chung. Nhieu luot goi DONG THOI
chia se duoc cung mot khoa — chinh chu thich dau `api_pool.py` noi the:

    "mot API key CHIA SE duoc cho nhieu request dong thoi, nen KHONG can khoa
     doc quyen (`FOR UPDATE`)"

Cau ay dung ve **y dinh** va sai ve **co che**. Khong xin `FOR UPDATE` khong co
nghia la khong co khoa: tren PostgreSQL, mot `UPDATE` thuong cung lay khoa hang
DOC QUYEN, va khoa do song **toi khi giao dich commit**. `chon_key` tang bo dem
(`total_requests`, `window_requests`, `last_used_at`) roi chi `flush()`, con
giao dich nghiep vu thi commit **sau khi model tra loi**
(`server/api/chat.py::_finish_chat`). Giua hai moc do la 3-20 giay goi may B.

## Vi sao no la loi CHEO GIUA HAI MODEL, khong phai loi cua mot model

Production co **dung MOT hang** `api_keys` cho provider `ltt_llm`, va **ca hai**
model (LTT-3.8 tren 3090, LTT-3.5 tren 5060 Ti) di qua provider ay
(`apps/ltt_llm/features.py`: `model_theo_provider={"ltt_llm": ...}`). Nen mot
luot 3.8 dang chay chan mot luot 3.5 vua toi — hai GPU roi rang doc lap, ma
duong vao thi khong.

Hang khoa cung **khong mang `user_id`**, nen doi tai khoan khong go duoc no.
Do la ly do phep do "nen bang tai khoan khac" (7,15x/2,36x) khong bac bo duoc
gia thuyet nay, trong khi no da bac bo gia thuyet "khoa advisory theo tai khoan".

## Vi sao test nay PHAI chay tren PostgreSQL

SQLite khoa **ca CSDL** khi ghi, nen no che dung cuoc dua nay: moi thu trong nom
tuan tu du co loi hay khong, va mot test xanh vi ly do sai con te hon khong co
test. Cung ly do `test_214_multi_process_runtime.py` da viet o dau tep no.

## Doi chung khi test nay duoc viet (12/09/2026)

Do bang hai luong, mot hang khoa, moi luong `chon_key -> ngu 2s -> commit`:

    luot1: chon_key mat  0.011s
    luot2: chon_key mat  2.015s      <-- cho DUNG bang thoi luong luot1 giu
    => TUAN TU HOA

Sổ lỗi: `docs/ltt_llm_dual/SO_LOI_DO_TAI.md`, muc L-01.
"""
from __future__ import annotations

import threading
import time
import uuid

import pytest
import sqlalchemy as sa

from tests.pg_scratch import scratch_url, skip_without_postgres

PG_URL = scratch_url()
postgres_only = skip_without_postgres()

#: Bao lau luot thu nhat giu giao dich nghiep vu mo. Dai gap boi lan nguong
#: duoi, de phan quyet khong phu thuoc vao mot phep do thoi gian sat sao.
GIU_S = 3.0

#: Luot thu hai duoc coi la KHONG bi chan neu `chon_key` cua no ve trong khoang
#: nay. Day khong phai mot phep do hieu nang — no la mot phep phan biet nhi
#: phan giua "ve ngay" (~0,01 s do duoc) va "cho het luot thu nhat" (~3 s).
#: Bien rong gap 100 lan gia tri do duoc va gap 3 lan de an toan truoc may tai.
TRAN_KHONG_CHAN_S = 1.0


@pytest.fixture()
def engine():
    from platform_core.db import Base

    import platform_core.models  # noqa: F401  (nap moi bang vao metadata)

    eng = sa.create_engine(PG_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def mot_hang_khoa(engine):
    """Gieo DUNG MOT hang khoa — dung hinh dang production cua `ltt_llm`."""
    from platform_core.models import APIKEY_CAT_CHAT, ApiKey

    provider = "ltt_llm_t1234_" + uuid.uuid4().hex[:6]
    SF = sa.orm.sessionmaker(bind=engine, expire_on_commit=False)
    s = SF()
    try:
        k = ApiKey(provider=provider, name="t1234", categories=[APIKEY_CAT_CHAT],
                   status="active", priority=50, health_score=100,
                   credential_enc=b"x", key_preview="x",
                   base_url="http://127.0.0.1:1")
        s.add(k)
        s.commit()
    finally:
        s.close()
    return provider, SF


@postgres_only
def test_chon_key_khong_chan_luot_khac_dang_goi_model(mot_hang_khoa):
    """Luot 2 phai cap duoc khoa TRONG KHI luot 1 dang goi model.

    ⛔ Day la bat bien cua L-01. Do do: luot 1 `chon_key` roi GIU giao dich mo
       (dung nhu `dieu_phoi.goi` giu no suot `_goi_openai`); luot 2 goi
       `chon_key` va phai ve ngay, khong phai cho luot 1 commit.
    """
    from platform_core import api_pool
    from platform_core.models import APIKEY_CAT_CHAT

    provider, SF = mot_hang_khoa

    luot1_da_chon = threading.Event()
    luot1_duoc_tha = threading.Event()
    loi: list[BaseException] = []

    def luot_1():
        db = SF()
        try:
            api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                              thu_tu_provider=[provider])
            luot1_da_chon.set()
            # ⬇ Cho nay la luot goi may B: giao dich VAN MO suot thoi gian ay.
            luot1_duoc_tha.wait(timeout=GIU_S + 5.0)
            db.commit()
        except BaseException as e:                     # noqa: BLE001
            loi.append(e)
            luot1_da_chon.set()
        finally:
            db.close()

    t1 = threading.Thread(target=luot_1, daemon=True)
    t1.start()
    assert luot1_da_chon.wait(timeout=10.0), "luot 1 khong chon duoc khoa"

    try:
        db2 = SF()
        try:
            t0 = time.monotonic()
            api_pool.chon_key(db2, category=APIKEY_CAT_CHAT,
                              thu_tu_provider=[provider])
            mat = time.monotonic() - t0
            db2.commit()
        finally:
            db2.close()
    finally:
        luot1_duoc_tha.set()
        t1.join(timeout=10.0)

    assert not loi, f"luot 1 hong: {loi[0]!r}"
    assert mat < TRAN_KHONG_CHAN_S, (
        f"`chon_key` cua luot 2 mat {mat:.3f}s trong khi luot 1 dang goi model. "
        f"No dang cho khoa hang `api_keys` — tuc moi luot chat qua may A tuan tu "
        f"hoa tren MOT hang, ke ca khi hai luot chay tren HAI GPU khac nhau "
        f"(L-01). Tran: {TRAN_KHONG_CHAN_S}s.")


@postgres_only
def test_danh_dau_thanh_cong_khong_giu_khoa_hang(mot_hang_khoa):
    """Ke toan token sau luot goi cung khong duoc giu hang lai.

    `dieu_phoi.goi` goi `danh_dau_thanh_cong` roi tra ve; commit xay ra mai o
    cua. Neu ham ay de lai mot khoa hang thi luot ke tiep chan o day thay vi o
    `chon_key` — cung mot loi, doi cho.
    """
    from platform_core import api_pool
    from platform_core.models import APIKEY_CAT_CHAT

    provider, SF = mot_hang_khoa

    xong = threading.Event()
    tha = threading.Event()
    loi: list[BaseException] = []

    def luot_1():
        db = SF()
        try:
            key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                                    thu_tu_provider=[provider])
            api_pool.danh_dau_thanh_cong(db, key, tokens=1234)
            xong.set()
            tha.wait(timeout=GIU_S + 5.0)
            db.commit()
        except BaseException as e:                     # noqa: BLE001
            loi.append(e)
            xong.set()
        finally:
            db.close()

    t1 = threading.Thread(target=luot_1, daemon=True)
    t1.start()
    assert xong.wait(timeout=10.0), "luot 1 khong chay xong phan ghi so"

    try:
        db2 = SF()
        try:
            t0 = time.monotonic()
            api_pool.chon_key(db2, category=APIKEY_CAT_CHAT,
                              thu_tu_provider=[provider])
            mat = time.monotonic() - t0
            db2.commit()
        finally:
            db2.close()
    finally:
        tha.set()
        t1.join(timeout=10.0)

    assert not loi, f"luot 1 hong: {loi[0]!r}"
    assert mat < TRAN_KHONG_CHAN_S, (
        f"`chon_key` mat {mat:.3f}s sau khi mot luot khac goi "
        f"`danh_dau_thanh_cong` va chua commit — hang khoa van bi giu (L-01).")


@postgres_only
def test_bo_dem_van_tang_that(mot_hang_khoa):
    """⛔ Doi chung cua chinh ban sua: go khoa KHONG duoc go luon phep dem.

    Mot ban sua lam `chon_key` thoi ghi se lam hai test tren XANH ngay lap tuc
    va lam `rpm_limit`/`tpm_limit` thanh trang tri. Ca nay chot rang so lieu
    van duoc ghi THAT xuong CSDL.
    """
    from platform_core import api_pool
    from platform_core.models import APIKEY_CAT_CHAT, ApiKey

    provider, SF = mot_hang_khoa

    for _ in range(3):
        db = SF()
        try:
            key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                                    thu_tu_provider=[provider])
            api_pool.danh_dau_thanh_cong(db, key, tokens=100)
            db.commit()
        finally:
            db.close()

    db = SF()
    try:
        k = db.query(ApiKey).filter(ApiKey.provider == provider).one()
        assert k.total_requests == 3, f"total_requests={k.total_requests}, doi 3"
        assert k.total_success == 3, f"total_success={k.total_success}, doi 3"
        assert k.total_tokens == 300, f"total_tokens={k.total_tokens}, doi 300"
        assert k.window_requests == 3, f"window_requests={k.window_requests}, doi 3"
        assert k.last_used_at is not None, "last_used_at khong duoc ghi"
    finally:
        db.close()
