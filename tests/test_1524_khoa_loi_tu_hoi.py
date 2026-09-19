"""test_1524 — loi 5xx/mang KHONG duoc lam mot khoa chet vinh vien. Su co 19/09/2026.

## Su viec

Nam lan `ReadError` (khach ngat, xem `test_1523`) dua khoa DUY NHAT cua
`ltt_llm` sang `APIKEY_ERROR`. `_ung_vien` chi tu hoi `COOLDOWN`, nen tu 23:54:47
moi khach nhan `ThieuKeyError` -> 500 cho toi khi admin reset tay luc ~00:10 —
16 phut mat dich vu trong khi may B khoe.

## Thiet ke — theo dung y do dau `api_pool.py` (hoc BOT GEMINI)

Dau tep ghi: *"5xx/mang -> error; sang trang thai error sau nhieu lan"*. BOT
GEMINI (`app/resources/api_pool_manager.py`) co cung khuyet tat nay cho 5xx
(`status == error and error_count >= MAX` -> bo qua, khong tu hoi), va da tu sua
DUNG khuyet tat ay o nhanh auth: *"transient auth error -> recoverable COOLDOWN"*
(`mark_auth_error`, `AUTH_COOLDOWN_SECONDS`) — mot trang thai chet vinh vien tu
mot loi thoang qua da lam sap ho mot lan. Ta ap cung bai hoc cho 5xx/mang:

* van sang `APIKEY_ERROR` (nguoi truc van thay "error", khong giau di);
* nhung kem `cooldown_until` — het han thi khoa duoc thu lai (nua mo);
* `error_count` KHONG xoa khi tu hoi: mot loi nua la ERROR ngay, mot thanh cong
  moi xoa ve 0 (`danh_dau_thanh_cong`, da co tu truoc).

⛔ Giu nguyen: 401/403 -> COOLDOWN roi DISABLED sau 5 lan (DISABLED khong tu hoi).
"""
from __future__ import annotations

import logging
from datetime import timedelta

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'k1524.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "test-material-cho-secretbox-1524")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _nam_lan_mang(api_pool, db, k):
    for _ in range(api_pool.ERROR_TO_STATUS_THRESHOLD):
        api_pool.danh_dau_loi(db, k, message="ReadError")
    db.commit()


def _tua_toi(monkeypatch, api_pool, giay: float):
    that = api_pool._bay_gio()
    monkeypatch.setattr(api_pool, "_bay_gio", lambda: that + timedelta(seconds=giay))


def test_5xx_mang_van_ra_ERROR_va_chan_ngay(db):
    """Đối chứng: ngưỡng và trạng thái ERROR giữ nguyên — không nới hành vi tức thời."""
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_ERROR
    k = api_keys.tao_key(db, provider="ltt_llm", credential="k"); db.commit()
    _nam_lan_mang(api_pool, db, k)
    assert k.status == APIKEY_ERROR and k.error_count == 5
    assert k.cooldown_until is not None, "ERROR khong kem han -> chet vinh vien"
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "ltt_llm")


def test_ERROR_TU_HOI_sau_han(db, monkeypatch):
    """🔴 Mệnh đề trung tâm: khoá duy nhất KHÔNG chết vĩnh viễn vì lỗi thoáng qua."""
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_ACTIVE
    k = api_keys.tao_key(db, provider="ltt_llm", credential="k"); db.commit()
    _nam_lan_mang(api_pool, db, k)
    _tua_toi(monkeypatch, api_pool, api_pool.ERROR_COOLDOWN_S + 1)
    chon = api_pool.lay_key(db, "ltt_llm")
    assert chon.id == k.id and chon.status == APIKEY_ACTIVE, (
        "APIKEY_ERROR khong tu hoi: mot dot loi mang giet ltt_llm toi khi admin "
        "reset tay (su co 19/09, 16 phut 500)")


def test_nua_mo_mot_loi_nua_la_ERROR_ngay_thanh_cong_moi_xoa(db, monkeypatch):
    """Tự hồi là THỬ LẠI, không phải xoá án: bộ đếm lỗi còn nguyên."""
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_ACTIVE, APIKEY_ERROR
    k = api_keys.tao_key(db, provider="ltt_llm", credential="k"); db.commit()
    _nam_lan_mang(api_pool, db, k)
    _tua_toi(monkeypatch, api_pool, api_pool.ERROR_COOLDOWN_S + 1)
    k = api_pool.lay_key(db, "ltt_llm")
    api_pool.danh_dau_loi(db, k, message="ReadError"); db.commit()
    assert k.status == APIKEY_ERROR and k.error_count == 6

    _tua_toi(monkeypatch, api_pool, 2 * api_pool.ERROR_COOLDOWN_S + 2)
    k = api_pool.lay_key(db, "ltt_llm")
    api_pool.danh_dau_thanh_cong(db, k); db.commit()
    assert k.status == APIKEY_ACTIVE and k.error_count == 0


def test_DOI_CHUNG_AM_401_van_DISABLED_khong_tu_hoi(db, monkeypatch):
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_DISABLED
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    for _ in range(api_pool.AUTH_DISABLE_THRESHOLD):
        api_pool.danh_dau_loi(db, k, http_status=401)
    db.commit()
    assert k.status == APIKEY_DISABLED
    _tua_toi(monkeypatch, api_pool, 10 * api_pool.ERROR_COOLDOWN_S)
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "gemini")


def test_ERROR_cu_khong_han_van_bi_bo_qua(db, monkeypatch):
    """Dòng ERROR không có `cooldown_until` (đặt tay / bản cũ) không tự sống lại."""
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_ERROR
    k = api_keys.tao_key(db, provider="ltt_llm", credential="k")
    k.status = APIKEY_ERROR; k.error_count = 5; k.cooldown_until = None
    db.commit()
    _tua_toi(monkeypatch, api_pool, 10 * api_pool.ERROR_COOLDOWN_S)
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "ltt_llm")


# ── (c) cảnh báo khi khoá CUỐI của một provider rời ACTIVE ───────────────────

def _loi_khoa_cuoi(caplog):
    return [r for r in caplog.records
            if r.name == "platform_core.api_pool" and r.levelno >= logging.ERROR
            and "KHOA CUOI" in r.getMessage()]


def test_khoa_cuoi_roi_ACTIVE_thi_log_ERROR(db, caplog):
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="ltt_llm", credential="bi-mat-khong-in")
    db.commit()
    with caplog.at_level(logging.WARNING, logger="platform_core.api_pool"):
        _nam_lan_mang(api_pool, db, k)
    ds = _loi_khoa_cuoi(caplog)
    assert len(ds) == 1, [r.getMessage() for r in caplog.records]
    msg = ds[0].getMessage()
    assert "ltt_llm" in msg and "error" in msg
    assert "bi-mat-khong-in" not in msg


def test_DOI_CHUNG_con_khoa_khac_song_thi_KHONG_log_ERROR(db, caplog):
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="gemini", credential="k1")
    api_keys.tao_key(db, provider="gemini", credential="k2")
    db.commit()
    with caplog.at_level(logging.WARNING, logger="platform_core.api_pool"):
        _nam_lan_mang(api_pool, db, k)
    assert _loi_khoa_cuoi(caplog) == []


def test_khoa_cuoi_vao_cooldown_429_cung_log_ERROR(db, caplog):
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="gemini", credential="k"); db.commit()
    with caplog.at_level(logging.WARNING, logger="platform_core.api_pool"):
        api_pool.danh_dau_loi(db, k, http_status=429, retry_after_s=30)
        db.commit()
    assert len(_loi_khoa_cuoi(caplog)) == 1


def test_loi_khong_doi_trang_thai_thi_khong_bao(db, caplog):
    """Một lỗi dưới ngưỡng không đổi trạng thái ⇒ không báo (không ồn giả)."""
    from platform_core import api_keys, api_pool
    k = api_keys.tao_key(db, provider="ltt_llm", credential="k"); db.commit()
    with caplog.at_level(logging.WARNING, logger="platform_core.api_pool"):
        api_pool.danh_dau_loi(db, k, message="ReadError"); db.commit()
    assert _loi_khoa_cuoi(caplog) == []


def test_duong_GIAO_DICH_RIENG_cung_tu_hoi_ERROR(db, monkeypatch):
    """Đường production (PostgreSQL, L-01) tự hồi trong CÂU SQL của `chon_key`.

    Máy này không có PostgreSQL vứt đi (`LTT_TEST_DATABASE_URL`), nên ép đường
    giao dịch riêng chạy trên SQLite: cùng câu `UPDATE ... CASE WHEN status IN
    (...)`, cùng `_ghi_so_pool`. Đỏ nếu câu SQL chỉ còn hồi `COOLDOWN`.
    """
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_ACTIVE, APIKEY_ERROR
    k = api_keys.tao_key(db, provider="ltt_llm", credential="k"); db.commit()
    monkeypatch.setattr(api_pool, "_ghi_rieng_duoc", lambda _db: True)
    _nam_lan_mang(api_pool, db, k)
    db.refresh(k)
    assert k.status == APIKEY_ERROR and k.cooldown_until is not None
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "ltt_llm")
    _tua_toi(monkeypatch, api_pool, api_pool.ERROR_COOLDOWN_S + 1)
    chon = api_pool.lay_key(db, "ltt_llm")
    db.commit(); db.refresh(chon)
    assert chon.id == k.id and chon.status == APIKEY_ACTIVE
    assert chon.cooldown_until is None and chon.error_count == 5
