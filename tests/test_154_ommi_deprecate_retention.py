"""
test_154 - H19.6: ngừng dùng mẫu catalog, và dọn dữ liệu cũ.

Hai tính năng, mỗi cái có đúng một cách hỏng đắt tiền:

**Ngừng dùng mẫu:** nếu nó cũng cất luôn bản riêng của người đã clone thì họ
mất công cụ đang dùng để làm việc, và không hiểu vì sao. "Ngừng chào mời" và
"cất đi" là hai việc khác nhau.

**Dọn dữ liệu:** nếu nó xoá bản mà cảnh đang dùng thì ảnh của khách hàng biến
mất. Đây là loại lỗi không sửa lại được — file đã xoá là đã xoá.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.prompt_ai_ommi.services import library as lib
from apps.prompt_ai_ommi.services import retention
from apps.prompt_ai_ommi.services import storyboard as sb

A = "user-a"
B = "user-b"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'r.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def _mau_catalog(db, kind="meta", name="Mẫu chung"):
    row = lib.create(db, kind, owner_id=A, name=name, body="noi dung mau")
    db.commit()
    published = lib.publish_to_catalog(db, kind, item_id=row.id, owner_id=A,
                                       is_admin=True)
    db.commit()
    return published


# ── Ngừng dùng mẫu catalog ──────────────────────────────────────────────────

def test_ngung_dung_KHONG_dung_toi_ban_da_clone(db):
    """Cách hỏng đắt nhất của tính năng này."""
    mau = _mau_catalog(db)
    cua_toi = lib.clone_from_catalog(db, "meta", item_id=mau.id, owner_id=B)
    db.commit()

    lib.deprecate(db, "meta", item_id=mau.id, is_admin=True,
                  note="Dùng 'Mẫu chung v2' thay thế")
    db.commit()

    rieng, _ = lib.list_items(db, "meta", B)
    assert cua_toi.id in [r.id for r in rieng], (
        "ngừng dùng mẫu chung đã cất luôn bản riêng — người dùng mất công cụ "
        "đang dùng mà không hiểu vì sao")
    db.refresh(cua_toi)
    assert cua_toi.archived_at is None


def test_ngung_dung_thi_mau_bien_khoi_danh_sach_chao_moi(db):
    mau = _mau_catalog(db)
    truoc, _ = lib.list_items(db, "meta", B, catalog=True)
    assert mau.id in [r.id for r in truoc]

    lib.deprecate(db, "meta", item_id=mau.id, is_admin=True)
    db.commit()

    sau, _ = lib.list_items(db, "meta", B, catalog=True)
    assert mau.id not in [r.id for r in sau]


def test_khong_clone_MOI_duoc_tu_mau_da_ngung_dung(db):
    """Ẩn khỏi danh sách mà vẫn clone được bằng ID là 'ngừng dùng' trên danh
    nghĩa — người biết ID vẫn tiếp tục tạo bản mới từ thứ đã bị rút."""
    mau = _mau_catalog(db)
    lib.deprecate(db, "meta", item_id=mau.id, is_admin=True, note="đã có bản mới")
    db.commit()
    with pytest.raises(lib.LibraryError) as loi:
        lib.clone_from_catalog(db, "meta", item_id=mau.id, owner_id=B)
    assert "đã có bản mới" in str(loi.value), "không nói người dùng nên dùng gì thay"


def test_chi_admin_duoc_ngung_dung_mau(db):
    mau = _mau_catalog(db)
    with pytest.raises(lib.LibraryError):
        lib.deprecate(db, "meta", item_id=mau.id, is_admin=False)


def test_bo_ngung_dung_thi_mau_quay_lai(db):
    mau = _mau_catalog(db)
    lib.deprecate(db, "meta", item_id=mau.id, is_admin=True, note="tạm rút")
    db.commit()
    lib.deprecate(db, "meta", item_id=mau.id, is_admin=True, deprecated=False)
    db.commit()
    sau, _ = lib.list_items(db, "meta", B, catalog=True)
    assert mau.id in [r.id for r in sau]
    db.refresh(mau)
    assert mau.deprecated_note == ""


def test_nguoi_dung_biet_mau_goc_cua_minh_da_ngung_dung(db):
    """Không có phép tra này thì người dùng chỉ phát hiện khi kết quả tệ đi."""
    mau = _mau_catalog(db)
    lib.clone_from_catalog(db, "meta", item_id=mau.id, owner_id=B)
    db.commit()
    assert lib.deprecated_sources(db, "meta", B) == []

    lib.deprecate(db, "meta", item_id=mau.id, is_admin=True, note="xem bản v2")
    db.commit()
    canh_bao = lib.deprecated_sources(db, "meta", B)
    assert len(canh_bao) == 1 and canh_bao[0]["note"] == "xem bản v2"


# ── Dọn dữ liệu cũ ──────────────────────────────────────────────────────────

def _canh_nhieu_ban(db, so_ban=15, tuoi_ngay=200):
    board = sb.create_board(db, owner_id=A, project_id="p1", name="B")
    db.commit()
    scene = sb.add_scene(db, board_id=board.id, owner_id=A, prompt="x")
    db.commit()
    cu = datetime.now(timezone.utc) - timedelta(days=tuoi_ngay)
    for i in range(so_ban):
        v = sb.record_version(db, scene_id=scene.id, owner_id=A,
                              image_key=f"anh-{i}")
        v.created_at = cu
    db.commit()
    return scene


def test_plan_khong_dung_gi_vao_du_lieu(db):
    """Một công cụ dọn không chạy thử được là công cụ không ai dám chạy."""
    scene = _canh_nhieu_ban(db)
    truoc = len(sb.versions(db, scene.id, A))
    ke = retention.plan(db)
    assert ke.version_ids, "kế hoạch rỗng — test này thành vô nghĩa"
    assert len(sb.versions(db, scene.id, A)) == truoc, "plan() đã xoá dữ liệu"


def test_KHONG_BAO_GIO_xoa_ban_ma_canh_dang_dung(db):
    """Kể cả khi nó là bản cũ nhất — người dùng có thể đã khôi phục về bản 1.

    Đây là lỗi không sửa lại được: file đã xoá là đã xoá.
    """
    scene = _canh_nhieu_ban(db, so_ban=20)
    sb.restore_version(db, scene_id=scene.id, owner_id=A, version=1)
    db.commit()
    db.refresh(scene)
    dang_dung = scene.image_key
    assert dang_dung == "anh-0"

    ke = retention.plan(db)
    assert dang_dung not in ke.storage_keys, (
        "kế hoạch định xoá ảnh mà cảnh đang hiển thị")
    assert ke.giu_vi_dang_dung >= 1


def test_giu_du_N_ban_gan_nhat_du_chung_rat_cu(db):
    """Dọn theo tuổi thuần tuý sẽ xoá sạch lịch sử của cảnh làm xong từ lâu —
    đúng cảnh người dùng quay lại tham chiếu."""
    scene = _canh_nhieu_ban(db, so_ban=15, tuoi_ngay=900)
    ke = retention.plan(db, giu=10)
    retention.apply(db, ke)
    db.commit()
    con = sb.versions(db, scene.id, A)
    assert len(con) >= 10, f"còn {len(con)} bản, ít hơn hạn mức giữ"


def test_khong_dung_toi_ban_con_moi(db):
    """Người dùng còn đang lặp trên một cảnh thì đừng dọn dưới chân họ."""
    _canh_nhieu_ban(db, so_ban=20, tuoi_ngay=0)      # vừa tạo
    ke = retention.plan(db)
    assert ke.version_ids == [], "dọn cả bản vừa tạo hôm nay"
    assert ke.giu_vi_con_moi > 0


def test_khong_xoa_file_con_duoc_ban_khac_dung(db):
    """Hai bản trỏ cùng một ảnh (provider trả lại ảnh cũ) — xoá file khi mới
    dọn một bản là làm hỏng bản còn lại."""
    board = sb.create_board(db, owner_id=A, project_id="p1", name="B")
    db.commit()
    scene = sb.add_scene(db, board_id=board.id, owner_id=A, prompt="x")
    db.commit()
    cu = datetime.now(timezone.utc) - timedelta(days=400)
    for i in range(14):
        # Bản ĐẦU (sẽ bị dọn) và bản CUỐI (nằm trong hạn mức giữ) trỏ cùng một
        # ảnh — đúng tình huống provider trả lại ảnh cũ.
        chung = i in (0, 13)
        v = sb.record_version(db, scene_id=scene.id, owner_id=A,
                              image_key="dung-chung" if chung else f"anh-{i}")
        v.created_at = cu
    db.commit()

    ke = retention.plan(db, giu=3)
    assert ke.version_ids, "không bản nào bị dọn — test này thành vô nghĩa"
    assert "dung-chung" not in ke.storage_keys, (
        "xoá file mà một bản còn lại vẫn đang trỏ vào")


def test_apply_chay_dung_ke_hoach_da_xem(db):
    """Tính lại lúc chạy nghĩa là thứ người vận hành đã duyệt không còn là thứ
    sẽ xảy ra."""
    scene = _canh_nhieu_ban(db, so_ban=15)
    ke = retention.plan(db, giu=5)
    du_dinh = len(ke.version_ids)
    ra = retention.apply(db, ke)
    db.commit()
    assert ra["da_xoa_ban"] == du_dinh
    assert len(sb.versions(db, scene.id, A)) == 15 - du_dinh


def test_xoa_file_loi_khong_lam_hong_ca_luot_don(db):
    _canh_nhieu_ban(db, so_ban=15)
    ke = retention.plan(db, giu=5)

    class KhoHong:
        def delete(self, key):
            raise OSError("đĩa lỗi")

    ra = retention.apply(db, ke, storage=KhoHong())
    db.commit()
    assert ra["da_xoa_ban"] > 0, "lỗi xoá file làm mất luôn phần dọn CSDL"
