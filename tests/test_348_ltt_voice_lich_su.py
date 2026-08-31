"""Màn Lịch sử: lọc đúng, đếm đúng, và **nói ra** chỗ nó cắt bớt.

## Ba thứ tệp này canh

1. **Lọc theo nguồn thực sự hoạt động.** `nguon` được ghi từ P1 và là thứ duy
   nhất trả lời "lượt này đến từ đâu". Nếu bộ lọc lặng lẽ không khớp thì màn
   hình trả rỗng và người dùng kết luận sai rằng họ chưa từng dùng API.

2. **Con số tóm tắt tính đúng mẫu số.** Tỉ lệ lỗi tính trên số lượt **đã kết
   thúc**, không trên tổng — một lượt đang chạy chưa hỏng, và đếm nó vào mẫu số
   làm tỉ lệ trông đẹp lên một cách sai.

3. 🔴 **Trần đọc phải được nói ra.** `doc_man_lich_su.TRAN_DOC` cắt danh sách ở
   500 lượt. Một cái trần **không nói ra** tệ hơn không có trần: màn hình trông
   như đã liệt kê hết trong khi nó cắt bớt, và người dùng đi tìm một lượt cũ rồi
   kết luận nó đã bị xoá.
"""
from __future__ import annotations

import datetime as dt
import re
from types import SimpleNamespace

import pytest

from apps.ltt_voice import doc_man_lich_su as dls


def _job(**kw):
    """Một job giả, đủ hình dạng cho `doc_man_lich_su`."""
    return SimpleNamespace(
        id=kw.get("id", "job-1"),
        status=kw.get("status", "done"),
        params=kw.get("params", {}),
        result=kw.get("result", {}),
        created_at=kw.get("created_at", dt.datetime(2026, 8, 31, 10, 0)),
    )


# ── Lọc ──────────────────────────────────────────────────────────────────────

def test_loc_theo_nguon():
    ds = [_job(params={"nguon": "studio"}), _job(params={"nguon": "api"}),
          _job(params={"nguon": "api"})]
    assert len(dls.loc(ds, nguon="api")) == 2
    assert len(dls.loc(ds, nguon="studio")) == 1
    assert len(dls.loc(ds)) == 3, "khong loc gi ma van mat dong"


def test_loc_theo_giong_gom_ca_hai_loai():
    """Giọng nhân bản đi qua `voice_id`, giọng mẫu đi qua `preset`.

    ⭐ Hai trường khác nhau ở tầng dưới, nhưng với người xem lịch sử chúng là
       **cùng một câu hỏi**: "lượt này đọc bằng giọng nào". Nên bộ lọc phải
       nhìn cả hai; nhìn một cái thì một nửa lịch sử biến mất khỏi bộ lọc.
    """
    ds = [_job(params={"preset": "Adam"}),
          _job(params={"voice_id": "vc_abc"}),
          _job(params={"preset": "Trúc Ly"})]
    assert len(dls.loc(ds, giong="Adam")) == 1
    assert len(dls.loc(ds, giong="vc_abc")) == 1


def test_loc_gia_tri_la_tra_rong_chu_khong_no():
    """Tham số lọc là chuỗi khách gửi. Giá trị lạ ⇒ rỗng, không ngoại lệ."""
    ds = [_job(params={"nguon": "studio"})]
    assert dls.loc(ds, nguon="'; DROP TABLE jobs; --") == []


def test_job_cu_khong_co_nguon_thi_khong_doan():
    """⛔ Job nộp TRƯỚC P1 không mang `nguon`. Trả rỗng, đừng đoán.

    Đoán một nguồn cho dữ liệu lịch sử là bịa ra một sự thật mà sau đó không ai
    kiểm lại được — và nó sẽ được đọc như thật.
    """
    assert dls._nguon_cua(_job(params={"text": "cu"})) == ""
    # Và job cũ không được lọt vào bất kỳ bộ lọc nguồn nào.
    for n in dls.NGUON:
        assert dls.loc([_job(params={"text": "cu"})], nguon=n) == []


# ── Tóm tắt ──────────────────────────────────────────────────────────────────

def test_ti_le_loi_tinh_tren_luot_DA_KET_THUC():
    """🔴 Mẫu số là done+error, không phải tổng.

    Ba xong, một lỗi, sáu đang chạy: tỉ lệ lỗi là 1/4 = 25%, **không** phải
    1/10 = 10%. Dùng tổng làm mẫu số khiến tỉ lệ lỗi tụt xuống mỗi khi có nhiều
    việc đang xếp hàng — tức nó đẹp nhất đúng lúc hệ thống tắc nhất.
    """
    ds = ([_job(status="done") for _ in range(3)]
          + [_job(status="error")]
          + [_job(status="queued") for _ in range(6)])
    assert dls.tom_tat(ds)["ti_le_loi"] == 25.0


def test_ti_le_loi_khong_chia_cho_khong():
    ds = [_job(status="queued"), _job(status="running")]
    assert dls.tom_tat(ds)["ti_le_loi"] == 0.0


def test_tom_tat_cong_don_giay_va_credit():
    ds = [_job(result={"duration_s": 30.0, "credit_cost": 2}),
          _job(result={"duration_s": 30.0, "credit_cost": 3})]
    t = dls.tom_tat(ds)
    assert t["phut"] == 1.0
    assert t["credit"] == 5


def test_tom_tat_khong_vo_vi_du_lieu_ban():
    """Một `result` méo không được làm sập màn hình."""
    ds = [_job(result={"duration_s": "khong-phai-so", "credit_cost": None}),
          _job(result=None)]
    t = dls.tom_tat(ds)
    assert t["phut"] == 0.0 and t["credit"] == 0


def test_giong_hay_dung():
    ds = ([_job(params={"preset": "Adam"}) for _ in range(3)]
          + [_job(params={"preset": "Trúc Ly"})])
    t = dls.tom_tat(ds)
    assert t["giong_hay_dung"] == "Adam" and t["giong_hay_dung_so"] == 3


# ── Trần đọc phải nói ra ─────────────────────────────────────────────────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-ls.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-ls")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="voice-ls@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.commit()
        uid = str(u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    login = client.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', login.text)
    assert m
    client.post("/login", data={"username": "voice-ls@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _gieo(uid: str, so: int, **kw) -> None:
    import platform_core.db as dbmod
    from platform_core.models import Job

    gen = dbmod.get_session()
    db = next(gen)
    try:
        for i in range(so):
            db.add(Job(user_id=uid, app_slug="ltt_voice",
                       job_type="ltt_voice.synthesize",
                       params={"text": f"cau {i}", "nguon": kw.get("nguon", "studio"),
                               "preset": "Adam"},
                       status=kw.get("status", "done"),
                       result={"duration_s": 1.0, "credit_cost": 1,
                               "audio_key": f"voice/out/{uid}/j{i}/tieng.wav"}))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_khi_cham_tran_thi_MAN_HINH_PHAI_NOI(khach, monkeypatch):
    """🔴 Cắt bớt trong im lặng là nói dối bằng cách bỏ sót.

    Hạ trần xuống 5 rồi gieo 6 lượt: trang phải mang cờ `bi_cat` và in ra câu
    giải thích, chứ không chỉ hiện 5 dòng như thể đó là tất cả.
    """
    monkeypatch.setattr(dls, "TRAN_DOC", 5)
    client, uid = khach
    _gieo(uid, 6)

    html = client.get("/ltt-voice/lich-su").text
    assert "lv-ls-cat" in html, (
        "cham tran ma trang KHONG noi gi — nguoi dung se tuong day la tat ca")


def test_khi_chua_cham_tran_thi_khong_doa_nguoi_dung(khach, monkeypatch):
    """Và ngược lại: chưa cắt gì thì đừng hiện cảnh báo. Một cảnh báo luôn hiện
    là một cảnh báo không ai đọc."""
    monkeypatch.setattr(dls, "TRAN_DOC", 50)
    client, uid = khach
    _gieo(uid, 3)
    assert "lv-ls-cat" not in client.get("/ltt-voice/lich-su").text


# ── Đi qua router thật ───────────────────────────────────────────────────────

def test_loc_qua_url(khach):
    client, uid = khach
    _gieo(uid, 2, nguon="studio")
    _gieo(uid, 3, nguon="api")

    def dem(url):
        return len(re.findall(r'class="lv-ls-dong"', client.get(url).text))

    assert dem("/ltt-voice/lich-su") == 5
    assert dem("/ltt-voice/lich-su?nguon=api") == 3
    assert dem("/ltt-voice/lich-su?nguon=studio") == 2
    assert dem("/ltt-voice/lich-su?nguon=khong-co-that") == 0


def test_lich_su_khong_lo_khoa_kho_tran(khach):
    """URL phát phải đi qua cửa `/audio/` của app, không lộ khoá kho.

    Khoá kho là chi tiết nội bộ; hiện nó ra là mời người ta thử ghép tay một
    khoá khác.
    """
    client, uid = khach
    _gieo(uid, 1)
    html = client.get("/ltt-voice/lich-su").text
    assert 'src="/ltt-voice/audio/voice/out/' in html
    assert 'src="voice/out/' not in html
