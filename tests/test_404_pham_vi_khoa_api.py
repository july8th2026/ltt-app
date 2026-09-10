"""Phạm vi cấp khoá API: pool nền tảng và khoá riêng của người dùng (I7, O15).

## Vì sao bộ kiểm này tồn tại

`ApiKey.owner_user_id` có từ migration đầu tiên của bảng
(`20260731_1600_them_bang_api_keys.py:24`, có index) và `tao_key()` ghi nó —
nhưng **không nơi nào đọc**. `api_pool._ung_vien` lọc theo enabled/status/
categories/supported_models/rpm/tpm và không hề lọc theo chủ sở hữu.

Nghĩa là một khoá RIÊNG của khách sẽ được cấp cho lượt gọi của bất kỳ ai.

⭐ Nói cho đúng: điều đó **chưa** rò rỉ, vì không đường ghi nào trong kho đặt
   `owner_user_id`. Đó cũng là thứ làm cách sửa an toàn — định nghĩa rỗng = pool
   nền tảng là **thiết lập** ngữ nghĩa cho một cột chưa có ngữ nghĩa, không phải
   diễn giải lại một cột đang dùng.

⛔ Nửa dưới của tệp này (`TestTuongThichNguoc`) quan trọng ngang nửa trên. O15
   cấm đổi hành vi allocator theo cách làm hỏng app hiện có, và cách duy nhất để
   biết là **kiểm chính hành vi cũ**.
"""
from __future__ import annotations

import pytest

from tests.conftest import bao_dam_user


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'keys.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "x" * 32)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _khoa(db, *, provider="gemini", ten="k", chu="", credential="bi-mat-gia"):
    from platform_core import api_keys
    if chu:
        bao_dam_user(db, chu)
    k = api_keys.tao_key(db, provider=provider, credential=credential, name=ten,
                         owner_user_id=chu)
    db.commit()
    return k


# ══════════════════════════════════════════════════════════════════════════════
#  Cách ly (I7 / G4)
# ══════════════════════════════════════════════════════════════════════════════

def test_pool_nen_tang_KHONG_BAO_GIO_cham_khoa_rieng(db):
    """Bất biến trung tâm. Pool chỉ được phục vụ khoá của nền tảng."""
    from platform_core import api_pool

    nen_tang = _khoa(db, ten="cua nen tang")
    _khoa(db, ten="cua A", chu="uA")

    for _ in range(5):      # lặp: xếp hạng có yếu tố tải, không được lọt lần nào
        chon = api_pool.chon_key(db)
        assert chon.id == nen_tang.id
        assert (chon.owner_user_id or "") == ""


def test_khoa_rieng_KHONG_roi_ve_pool_nen_tang(db):
    """Mục 5 — không rơi ngược, kể cả khi pool đang rảnh.

    Khách chọn khoá riêng là để hạn mức và hoá đơn thuộc về họ. Lặng lẽ dùng
    khoá nhà là tiêu tiền của nền tảng cho một yêu cầu đã nói rõ không muốn thế
    — và khách sẽ không bao giờ biết.
    """
    from platform_core import api_pool

    _khoa(db, ten="cua nen tang")           # pool có sẵn, vẫn không được dùng
    bao_dam_user(db, "uB"); db.commit()

    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG, owner_user_id="uB")


def test_khoa_rieng_cua_A_KHONG_den_tay_B(db):
    """G4 — hai người dùng, mỗi người một khoá."""
    from platform_core import api_pool

    a = _khoa(db, ten="cua A", chu="uA")
    b = _khoa(db, ten="cua B", chu="uB")

    assert api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                             owner_user_id="uA").id == a.id
    assert api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                             owner_user_id="uB").id == b.id


def test_doan_trung_id_khoa_van_khong_dung_duoc(db):
    """Biết id khoá của người khác không cho phép dùng nó.

    Phép lọc chạy **trong câu truy vấn** theo chủ sở hữu, nên một id đoán trúng
    chỉ dẫn tới một tập ứng viên rỗng.
    """
    from platform_core import api_pool
    from platform_core.models import ApiKey

    a = _khoa(db, ten="cua A", chu="uA")
    assert db.get(ApiKey, a.id) is not None      # id có thật

    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG, owner_user_id="uB")


def test_xin_khoa_rieng_ma_khong_noi_cua_ai_thi_BI_TU_CHOI(db):
    """Fail-closed. Nếu đoán, đường đoán an toàn nhất vẫn là cấp khoá của người
    khác hoặc của nền tảng — đúng hai thứ I7 cấm."""
    from platform_core import api_pool

    _khoa(db, ten="cua nen tang")
    with pytest.raises(api_pool.PhamViError):
        api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG, owner_user_id="")
    with pytest.raises(api_pool.PhamViError):
        api_pool.chon_key(db, pham_vi="pham_vi_bia_ra")


def test_lay_key_va_thu_lan_luot_cung_ton_trong_pham_vi(db):
    """Ba cửa vào, một luật. Một cửa quên lọc là cả hàng rào vô nghĩa."""
    from platform_core import api_pool

    _khoa(db, ten="cua A", chu="uA")

    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.lay_key(db, "gemini")           # pool: không thấy khoá của uA

    assert api_pool.lay_key(db, "gemini", pham_vi=api_pool.PHAM_VI_RIENG,
                            owner_user_id="uA").owner_user_id == "uA"

    assert list(api_pool.thu_lan_luot(db, provider="gemini")) == []
    rieng = list(api_pool.thu_lan_luot(db, provider="gemini",
                                       pham_vi=api_pool.PHAM_VI_RIENG,
                                       owner_user_id="uA"))
    assert [k.owner_user_id for k in rieng] == ["uA"]


# ══════════════════════════════════════════════════════════════════════════════
#  Tương thích ngược (O15) — nửa quan trọng ngang nửa trên
# ══════════════════════════════════════════════════════════════════════════════

class TestTuongThichNguoc:
    """Hành vi mà app hiện có đang dựa vào, phải giữ nguyên từng điểm.

    Prompt 07 mục 4 cấm "lặng lẽ diễn giải lại mọi trường owner rỗng/không rỗng".
    Cách duy nhất để biết mình không làm thế là kiểm chính hành vi cũ.
    """

    def test_goi_khong_truyen_pham_vi_van_chay_nhu_truoc(self, db):
        """Mọi lời gọi hiện có trong kho đều không truyền `pham_vi`."""
        from platform_core import api_pool

        k = _khoa(db, ten="nhu cu")
        assert api_pool.chon_key(db).id == k.id
        assert api_pool.lay_key(db, "gemini").id == k.id

    def test_thu_tu_provider_va_do_uu_tien_khong_doi(self, db):
        from platform_core import api_pool

        _khoa(db, provider="gemini", ten="g")
        _khoa(db, provider="apiai", ten="a")

        assert api_pool.chon_key(db, thu_tu_provider=["apiai", "gemini"]).provider == "apiai"
        assert api_pool.chon_key(db, thu_tu_provider=["gemini", "apiai"]).provider == "gemini"

    def test_khoa_bi_TAT_van_bi_bo_qua_o_ca_hai_pham_vi(self, db):
        from platform_core import api_pool

        nt = _khoa(db, ten="nen tang")
        rieng = _khoa(db, ten="cua A", chu="uA")
        nt.enabled = False; rieng.enabled = False
        db.commit()

        with pytest.raises(api_pool.ThieuKeyError):
            api_pool.chon_key(db)
        with pytest.raises(api_pool.ThieuKeyError):
            api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                              owner_user_id="uA")

    def test_cooldown_van_loai_khoa_o_ca_hai_pham_vi(self, db):
        from datetime import timedelta

        from platform_core import api_pool
        from platform_core.models import APIKEY_COOLDOWN

        rieng = _khoa(db, ten="cua A", chu="uA")
        rieng.status = APIKEY_COOLDOWN
        rieng.cooldown_until = api_pool._bay_gio() + timedelta(hours=1)
        db.commit()

        with pytest.raises(api_pool.ThieuKeyError):
            api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                              owner_user_id="uA")

    def test_cham_tran_rpm_van_loai_khoa_o_pham_vi_rieng(self, db):
        """Hạn mức là thuộc tính của khoá, không phải của phạm vi."""
        from platform_core import api_pool

        k = _khoa(db, ten="cua A", chu="uA")
        k.rpm_limit = 1
        k.window_start = api_pool._bay_gio()
        k.window_requests = 5
        db.commit()

        with pytest.raises(api_pool.ThieuKeyError):
            api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                              owner_user_id="uA")

    def test_loc_theo_category_va_model_van_ap_dung(self, db):
        from platform_core import api_keys, api_pool

        k = _khoa(db, ten="cua A", chu="uA")
        api_keys.cap_nhat_categories(db, k, ["image"])
        db.commit()

        assert api_pool.chon_key(db, category="image",
                                 pham_vi=api_pool.PHAM_VI_RIENG,
                                 owner_user_id="uA").id == k.id
        with pytest.raises(api_pool.ThieuKeyError):
            api_pool.chon_key(db, category="text",
                              pham_vi=api_pool.PHAM_VI_RIENG, owner_user_id="uA")


# ══════════════════════════════════════════════════════════════════════════════
#  Mục 6 + 7 — giải mã đúng ranh giới, telemetry không lộ bí mật
# ══════════════════════════════════════════════════════════════════════════════

def test_chon_key_KHONG_giai_ma_bi_mat(db):
    """Mục 6 — chỉ giải mã ở ranh giới gọi provider.

    `chon_key` trả về bản ghi, không trả về bí mật. Ai cần chuỗi thật thì gọi
    `api_keys.lay_credential()` — đúng một chỗ, dễ soi.
    """
    from platform_core import api_keys, api_pool

    _khoa(db, ten="cua A", chu="uA", credential="BI-MAT-THAT")
    chon = api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                             owner_user_id="uA")

    assert "BI-MAT-THAT" not in str(chon.credential_enc)
    assert api_keys.lay_credential(db, chon) == "BI-MAT-THAT"


def test_mo_ta_an_toan_khong_chua_bi_mat_va_khong_lo_id_chu_so_huu(db):
    """Mục 7 / I16 — cách giữ bí mật khỏi log là làm đường đúng thành đường sẵn có."""
    from platform_core import api_pool

    _khoa(db, ten="cua A", chu="uA", credential="BI-MAT-THAT")
    chon = api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                             owner_user_id="uA")
    mo_ta = api_pool.mo_ta_an_toan(chon)

    goi = repr(mo_ta)
    assert "BI-MAT-THAT" not in goi
    assert "credential" not in mo_ta and "credential_enc" not in mo_ta
    assert mo_ta["pham_vi"] == api_pool.PHAM_VI_RIENG
    assert mo_ta["chu_so_huu"] != "uA", "id chu so huu bi in nguyen ven"
    assert mo_ta["chu_so_huu"].startswith("uA")


def test_pham_vi_cua_suy_tu_du_lieu(db):
    from platform_core import api_pool

    assert api_pool.pham_vi_cua(_khoa(db, ten="nt")) == api_pool.PHAM_VI_POOL
    assert api_pool.pham_vi_cua(
        _khoa(db, ten="cua A", chu="uA")) == api_pool.PHAM_VI_RIENG


# ══════════════════════════════════════════════════════════════════════════════
#  Đồng thời hai người dùng
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_nguoi_dung_xen_ke_nhau_khong_lan_khoa(db):
    """Xen kẽ nhiều lượt: không lượt nào được nhận khoá của người kia.

    Xếp hạng có yếu tố tải (`window_requests`, `total_requests`) nên thứ tự đổi
    theo từng lượt gọi. Một phép kiểm gọi đúng một lần sẽ không thấy điều đó.
    """
    from platform_core import api_pool

    a = _khoa(db, ten="cua A", chu="uA")
    b = _khoa(db, ten="cua B", chu="uB")

    for _ in range(10):
        assert api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                                 owner_user_id="uA").id == a.id
        assert api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                                 owner_user_id="uB").id == b.id
    db.commit()
