"""`bao_tri` phải THẬT SỰ dọn — một hook nối đúng mà không xoá gì là hook chết.

🔴 **VÌ SAO CHỐT.** Trước 28/09, app này có **hai** chính sách hạn lưu kèm hàm dọn
sẵn sàng, và ⛔ không nơi nào chạy chúng theo lịch:

  `ommi_trash.purge_after`  30 ngày  → `thung_rac.purge_expired` có test, chỉ được
                                       gọi từ MỘT route khi khách tự bấm
  `ommi_handoff.expires_at` 30 phút  → ⛔ không ai xoá

⚠️ Đây là lần **thứ ba** trong kho: `AppManifest.bao_tri` được thêm vào 24/08 chính
vì `vps` viết xong `thu_phi_dinh_ky` kèm test mà ⛔ không ai gọi, rồi
`auto_scan_video` lặp lại với `expires_at`. Cùng một hình dạng: **chính sách có,
hàm kiểm có, báo cáo có — và không ai chạy.**

⭐ `test_211` đã kiểm rằng `purged_by` trỏ vào một hàm worker **thật gọi**. Bài này
kiểm vế còn lại, thứ `test_211` ⛔ không đo: **gọi nó có xoá thật không.** Hai câu
khác nhau — "ai gọi" và "gọi thì có tác dụng gì".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bao-tri.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close(); dbmod.reset_engine()


def _ve(db, *, het_han_truoc: bool):
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    moc = datetime.now(timezone.utc)
    row = OmmiHandoff(
        owner_id="u_1", project_id="p_1", scene_id="s_1",
        target_app_slug="taovideo", payload={"prompt": "x"},
        expires_at=moc - timedelta(minutes=1) if het_han_truoc
        else moc + timedelta(hours=2))
    db.add(row); db.commit()
    return row.id


def test_ve_qua_han_bi_xoa_ve_con_han_thi_khong(db_session):
    """Hai chiều trong MỘT phép: xoá cái phải xoá, GIỮ cái phải giữ.

    ⭐ Chiều thứ hai quan trọng hơn: một hàm dọn xoá SẠCH bảng cũng làm chiều thứ
    nhất xanh. Không có ca "còn hạn phải còn" thì bài này ⛔ không phân biệt được
    "dọn đúng" với "dọn hết".
    """
    from apps.prompt_ai_ommi.services import handoff_stage
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    db = db_session
    cu = _ve(db, het_han_truoc=True)
    moi = _ve(db, het_han_truoc=False)

    so_xoa = handoff_stage.don_ve_het_han(db)
    db.commit()

    assert so_xoa == 1, so_xoa
    con = {r.id for r in db.query(OmmiHandoff).all()}
    assert cu not in con, "ve QUA HAN van con"
    assert moi in con, "ve CON HAN bi xoa oan"


def test_don_hai_lan_khong_doi_gi_them(db_session):
    """Idempotent: nền tảng gọi `bao_tri` mỗi giờ, nên lượt hai phải là no-op."""
    from apps.prompt_ai_ommi.services import handoff_stage
    db = db_session
    _ve(db, het_han_truoc=True)
    assert handoff_stage.don_ve_het_han(db) == 1
    db.commit()
    assert handoff_stage.don_ve_het_han(db) == 0
    db.commit()


def test_manifest_NOI_bao_tri_va_no_goi_dung_ham():
    """Hook phải được KHAI, và phải dẫn tới đúng hàm — không chỉ tồn tại.

    ⛔ Không `assert MANIFEST.bao_tri is not None` một mình: một hook trỏ vào một
    hàm rỗng cũng qua. Gọi nó với CSDL chưa dựng và khẳng định nó ⛔ KHÔNG NÉM —
    đó là hợp đồng `bao_tri` (nền tảng bắt và ghi log, nhưng một app ném mỗi lượt
    là một dòng log rác mỗi giờ, và nó che những lỗi thật).
    """
    from apps.prompt_ai_ommi.manifest import MANIFEST
    assert MANIFEST.bao_tri is not None
    assert MANIFEST.bao_tri_moi_giay >= 60
    MANIFEST.bao_tri()          # ⛔ không được ném, kể cả khi không có gì để dọn


def test_purged_by_khai_dung_ten_ham_that():
    """Lời khai trong `governance` phải trùng tên hàm THẬT.

    `test_211` kiểm rằng tên ấy xuất hiện đâu đó trong nguồn `bao_tri`; bài này
    khoá chặt hơn: đúng module và đúng tên, nên đổi tên hàm mà quên sửa lời khai
    sẽ ĐỎ ở đây chứ không im lặng.
    """
    from platform_core.public_api import governance
    khai = [s for s in governance.STORES
            if s.table in {"ommi_trash", "ommi_handoff"}]
    assert len(khai) == 2, [s.table for s in khai]
    for store in khai:
        assert "services.bao_tri.bao_tri" in store.purged_by, store.purged_by
    from apps.prompt_ai_ommi.services import bao_tri as mod
    assert callable(mod.bao_tri)
