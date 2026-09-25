"""Ràng buộc (c) ai được cài + ghim phiên bản TUYỆT ĐỐI.

Ràng buộc (c): tái dùng `User.role` đã có (`app_access.py` cùng luật), ⛔
không tự chế vai trò mới. Ghim phiên bản: `latest`/dải/`*` bị từ chối ở CẢ
`yeu_cau()` (chặn sớm) LẪN `cai_dat()` (phòng thủ theo chiều sâu — một hàng
cũ từ trước khi có kiểm tra này vẫn phải bị chặn).
"""
from __future__ import annotations

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _admin(id_="admin1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="admin",
               password_hash="x", display_name="Admin")


def _user(id_="u1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="user",
               password_hash="x", display_name="User")


# ── (c) Ai được cài ─────────────────────────────────────────────────────

@pytest.mark.parametrize("hanh_dong", ["duyet", "tu_choi", "cai_dat", "thu_hoi"])
def test_nguoi_dung_thuong_khong_duoc_duyet_tu_choi_cai_thu_hoi(db, hanh_dong):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    ham = getattr(mp, hanh_dong)
    with pytest.raises(mp.LoiKhongDuQuyen):
        if hanh_dong == "tu_choi":
            ham(db, yeu_cau_id=hang.id, nguoi=_user("u2"), ly_do="x")
        else:
            ham(db, yeu_cau_id=hang.id, nguoi=_user("u2"))


def test_nguoi_dung_None_khong_duoc_duyet(db):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    with pytest.raises(mp.LoiKhongDuQuyen):
        mp.duyet(db, yeu_cau_id=hang.id, nguoi=None)


def test_admin_duyet_duoc(db):  # noqa: F811
    from platform_core.models import MARKETPLACE_DA_DUYET
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    ra = mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    assert ra.trang_thai == MARKETPLACE_DA_DUYET


# ── Ghim phiên bản TUYỆT ĐỐI ─────────────────────────────────────────────

@pytest.mark.parametrize("ban_xau", [
    "latest", "next", "", "*", "^1.2.3", "~1.2.3", ">=1.2.3", "1.x", "1",
    "1.2", "1.2.3-", " 1.2.3", "1.2.3 ", "1.2.3\n; rm -rf",
])
def test_yeu_cau_tu_choi_phien_ban_khong_ghim(db, ban_xau):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    with pytest.raises(mp.LoiPhienBanKhongGhim):
        mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban=ban_xau)


@pytest.mark.parametrize("ban_tot", ["1.2.3", "0.0.1", "12.34.56", "1.2.3-beta.1"])
def test_yeu_cau_chap_nhan_phien_ban_ghim(db, ban_tot):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban=ban_tot)
    assert hang.phien_ban == ban_tot


def test_yeu_cau_tu_choi_ten_khong_hop_le(db):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    for ten_xau in ["../../etc/passwd", "", "@scope/", "foo bar", "@a/b/c"]:
        with pytest.raises(mp.LoiTenKhongHopLe):
            mp.yeu_cau(db, nguoi=_user(), ten=ten_xau, phien_ban="1.0.0")


def test_cai_dat_phong_thu_chieu_sau_cho_hang_cu_ban_khong_ghim(db, tmp_path, monkeypatch):  # noqa: F811
    """Mô phỏng một hàng `da_duyet` được tạo TRƯỚC khi có kiểm ghim (đường
    dữ liệu cũ) — `cai_dat()` vẫn phải chặn nó, không được tin tưởng ngầm
    rằng mọi hàng trong bảng đã đi qua `yeu_cau()` phiên bản mới."""
    from platform_core.models import MARKETPLACE_DA_DUYET, MarketplacePiece
    from platform_core.workflow import connector, marketplace as mp
    monkeypatch.setattr(connector, "THU_MUC_MARKETPLACE", tmp_path / "mkt")
    hang = MarketplacePiece(ten="@foo/piece-bar", phien_ban="latest",
                            nguoi_yeu_cau_id="u1",
                            trang_thai=MARKETPLACE_DA_DUYET)
    db.add(hang)
    db.flush()
    with pytest.raises(mp.LoiPhienBanKhongGhim):
        mp.cai_dat(db, yeu_cau_id=hang.id, nguoi=_admin(),
                  giai_quyet_integrity=lambda t, v: "x",
                  thuc_thi_install=lambda argv, mien: {"ok": True, "log": ""})
