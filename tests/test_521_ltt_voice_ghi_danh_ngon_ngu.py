"""D003/D004 — nguồn gốc làn của giọng nhân bản, và luật sửa làn.

Phần dưới (từ `khach`) là phép kiểm ĐI QUA CỬA WEB THẬT cho D003 — cửa
`/ltt-voice/giong/tao` phải BẮT KHAI làn, không còn lối lui `"vi"` mặc định.
Fixture `khach` chép NGUYÊN từ `tests/test_519_ltt_voice_studio_nop_trung.py`
(đổi DB/email/secret sang `voice-521`) vì đây cũng là một cửa tiêu tiền —
cùng lý do `test_519` cần một khách có credit thật, không phải một mock.
"""
from __future__ import annotations

import re

import pytest

from apps.ltt_voice import giong_vong_doi as V
from apps.ltt_voice import lan_ngon_ngu as L


@pytest.mark.parametrize("tu, den, duoc", [
    ("dang_ghi_danh", "active", True), ("dang_ghi_danh", "loi", True),
    ("dang_ghi_danh", "revoked", False),          # T-07: chặn thu hồi khi đang ghi danh
    ("active", "revoked", True), ("disabled", "revoked", True),
    ("revoked", "active", False), ("revoked", "disabled", False),  # INV-THU-HOI-1
    ("loi", "revoked", True), ("loi", "active", False),
])
def test_bang_chuyen_trang_thai(tu, den, duoc):
    assert V.co_the_chuyen(tu, den) is duoc


def test_khai_lan_la_hoac_rong_bi_tu_choi():
    for x in ("", "auto", "fr", "VN"):
        assert V.khai_lan_hop_le(x, lan_hien="vi", nguon_hien=V.NGUON_KHAI_BAO) \
            == "voice_language_required"


def test_khai_nguoc_PHEP_DO_bi_tu_choi_trung_thi_duoc():
    assert V.khai_lan_hop_le("en", lan_hien="vi", nguon_hien=V.NGUON_DO_ASR) \
        == "voice_language_measured"
    assert V.khai_lan_hop_le("vi", lan_hien="vi", nguon_hien=V.NGUON_DO_ASR) == ""


def test_khai_bao_va_mac_dinh_cu_sua_tu_do():
    for nguon in (V.NGUON_KHAI_BAO, V.NGUON_MAC_DINH_CU):
        assert V.khai_lan_hop_le("en", lan_hien="vi", nguon_hien=nguon) == ""


def test_lan_hop_le_lay_tu_tham_quyen():
    assert set(L.LAN_HOP_LE) == {"vi", "en"}


def test_migration_mot_head_va_danh_dau_dong_cu():
    import pathlib, re
    goc = pathlib.Path(__file__).resolve().parents[1]
    m = (goc / "alembic" / "versions" / "20260911_1000_voice_ngon_ngu_nguon.py").read_text(encoding="utf-8")
    assert re.search(r'down_revision\s*=\s*"d15b8c30f7a4"', m)
    assert "mac_dinh_cu" in m
    # Migration KHÔNG được gán lại `ngon_ngu` của dòng cũ (spec §6.2).
    assert not re.search(r"ngon_ngu\s*=\s*'", m.replace("ngon_ngu_nguon", ""))


# ── Đi qua cửa web thật: `/ltt-voice/giong/tao` phải BẮT KHAI (D003) ─────────

@pytest.fixture()
def khach(tmp_path, monkeypatch):
    """Một khách đã đăng nhập, có credit, trên SQLite tạm. Chép NGUYÊN khuôn của
    `tests/test_519_ltt_voice_studio_nop_trung.py:42-104` — chỉ đổi tên DB
    tệp/email/secret sang `voice-521` để không đụng phiên khác đang chạy cùng
    tệp gốc."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-521.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-521")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="voice-521@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 500, note="test_521")
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
    client.post("/login", data={"username": "voice-521@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf_giong(client) -> str:
    r = client.get("/ltt-voice/giong")
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    assert m
    return m.group(1)


def _wav_1s() -> bytes:
    import io, math, struct, wave
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 9)))
                               for i in range(24000 * 6)))
    return b.getvalue()


def _so_job(uid: str) -> int:
    import platform_core.db as dbmod
    from platform_core.models import Job

    gen = dbmod.get_session()
    db = next(gen)
    try:
        return db.query(Job).filter(Job.user_id == str(uid)).count()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _ho_so(uid: str, ten: str):
    """Đọc lại một `VoiceProfile` theo CHỦ + TÊN — dùng ở test ghi danh, nơi
    câu trả lời của cửa nộp chỉ có `voice_id`+`job_id`, không có sẵn hồ sơ."""
    import platform_core.db as dbmod
    from apps.ltt_voice.tables import VoiceProfile
    from sqlalchemy import select

    gen = dbmod.get_session()
    db = next(gen)
    try:
        return db.execute(select(VoiceProfile).where(
            VoiceProfile.owner_id == str(uid),
            VoiceProfile.ten_hien_thi == ten)).scalar_one_or_none()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@pytest.mark.parametrize("lan", ["", "auto", "fr"])
def test_ghi_danh_KHONG_khai_lan_bi_tu_choi_va_KHONG_tru_tien(khach, lan):
    client, uid = khach
    r = client.post("/ltt-voice/giong/tao",
                    data={"ten": "Giong A", "dong_y": "1", "ngon_ngu": lan,
                          "csrf_token": _csrf_giong(client)},
                    files={"tep": ("a.wav", _wav_1s(), "audio/wav")},
                    headers={"Accept": "application/json"})
    assert r.status_code == 400, r.text
    assert r.json()["ma_loi"] == "voice_language_required"
    assert _so_job(uid) == 0


def test_ghi_danh_khai_en_luu_nguon_khai_bao(khach):
    client, uid = khach
    r = client.post("/ltt-voice/giong/tao",
                    data={"ten": "Giong B", "dong_y": "1", "ngon_ngu": "en",
                          "csrf_token": _csrf_giong(client)},
                    files={"tep": ("b.wav", _wav_1s(), "audio/wav")})
    assert r.status_code in (200, 303), r.text
    ho_so = _ho_so(uid, "Giong B")
    assert (ho_so.ngon_ngu, ho_so.ngon_ngu_nguon) == ("en", "khai_bao")
