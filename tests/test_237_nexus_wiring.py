"""Nexus wiring W1/W2 — cầu nối vé → kết nối RustDesk, ở tầng nghiệp vụ.

Đây là chỗ mật khẩu một-lần của phiên sống rất ngắn: agent báo → controller lấy
một lần → xoá khi phiên kết thúc. Ba tính chất được chốt kỹ vì hỏng chúng là hỏng
đúng phần bảo mật: mật khẩu **không bao giờ ở dạng thô** trong DB, **thiết bị
người khác không lấy được**, và nó **biến mất khi phiên đóng**.
"""
from __future__ import annotations

import pytest

from platform_core import secretbox
from platform_core.nexus import sessions
from platform_core.nexus.devices import NexusError


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'wiring.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "wiring-test-key-0123456789")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _khoa_that() -> str:
    from platform_core.nexus import agent_auth
    _priv, pub = agent_auth.new_keypair_for_test()
    return pub


def _phien_da_mo(db, *, user="u-owner"):
    """Tạo một user + device + phiên đã đổi vé (đang mở)."""
    from platform_core.users import tao_nguoi_dung
    from platform_core.nexus import devices
    u = tao_nguoi_dung(db, email=f"{user}@ex.com", password="mat-khau-dai-123456",
                       is_verified=True)
    db.commit()
    row, ma = devices.tao_ma_ghep(db, user_id=u.id)
    dev = devices.doi_ma(db, code=ma, public_key=_khoa_that(), display_name="M")
    sess, ve = sessions.cap_ve(db, user_id=u.id, device=dev)
    sessions.doi_ve(db, ticket=ve)              # -> consumed, dang chay
    return u, dev, sess


# ── Round-trip: agent báo → controller lấy ──────────────────────────────────

def test_bao_roi_lay_lai_dung_mat_khau(db):
    u, dev, sess = _phien_da_mo(db)
    sessions.bao_engine(db, sess, engine_id="288780716", secret="MatKhauPhien-Xyz")
    kn = sessions.lay_ket_noi(db, sess, user_id=u.id)
    assert kn["engine_id"] == "288780716"
    assert kn["secret"] == "MatKhauPhien-Xyz"
    assert kn["quyen"] == sess.quyen


def test_mat_khau_KHONG_luu_tho_trong_db(db):
    u, dev, sess = _phien_da_mo(db)
    sessions.bao_engine(db, sess, engine_id="1", secret="BiMat-KhongDuocLoRa")
    # Cot luu phai la ciphertext, khong chua mat khau tho.
    assert "BiMat-KhongDuocLoRa" not in sess.engine_secret_enc
    # Va phai giai ma nguoc lai duoc bang secretbox.
    assert secretbox.giai_ma(sess.engine_secret_enc) == "BiMat-KhongDuocLoRa"


# ── Chủ sở hữu: người khác trả lỗi (404 ở route) ────────────────────────────

def test_nguoi_khac_khong_lay_duoc_ket_noi(db):
    u, dev, sess = _phien_da_mo(db)
    sessions.bao_engine(db, sess, engine_id="1", secret="pw")
    with pytest.raises(NexusError):
        sessions.lay_ket_noi(db, sess, user_id="ke-khac")


# ── Vòng đời: xoá khi phiên đóng ────────────────────────────────────────────

def test_ket_thuc_xoa_mat_khau(db):
    u, dev, sess = _phien_da_mo(db)
    sessions.bao_engine(db, sess, engine_id="1", secret="pw")
    sessions.ket_thuc(db, sess)
    assert sess.engine_secret_enc == ""
    with pytest.raises(NexusError):
        sessions.lay_ket_noi(db, sess, user_id=u.id)   # phien dong -> tu choi


def test_thu_hoi_xoa_mat_khau(db):
    u, dev, sess = _phien_da_mo(db)
    sessions.bao_engine(db, sess, engine_id="1", secret="pw")
    sessions.thu_hoi_ve(db, sess, by="chu-may")
    assert sess.engine_secret_enc == ""


# ── Không báo cho phiên chưa mở / đã đóng ───────────────────────────────────

def test_khong_bao_duoc_cho_phien_da_ket_thuc(db):
    u, dev, sess = _phien_da_mo(db)
    sessions.ket_thuc(db, sess)
    with pytest.raises(NexusError):
        sessions.bao_engine(db, sess, engine_id="1", secret="pw")


def test_lay_khi_agent_chua_bao_thi_tu_choi(db):
    u, dev, sess = _phien_da_mo(db)
    # chua bao engine
    with pytest.raises(NexusError):
        sessions.lay_ket_noi(db, sess, user_id=u.id)


def test_engine_id_giu_lai_sau_khi_xoa_secret(db):
    """engine_id không bí mật + có giá trị kiểm toán → giữ; chỉ secret bị xoá."""
    u, dev, sess = _phien_da_mo(db)
    sessions.bao_engine(db, sess, engine_id="288780716", secret="pw")
    sessions.ket_thuc(db, sess)
    assert sess.engine_id == "288780716"
    assert sess.engine_secret_enc == ""
