"""
test_629 — Phase 12 nhóm DỮ LIỆU và HIỆU NĂNG.

Dữ liệu:
  1. Xoá khi đang chạy: lượt bị huỷ, và sự kiện tới SAU đó không hồi sinh gì.
  2. Dọn dữ liệu đã xoá mềm: đúng hạn, đúng thứ tự con→cha, không đụng hội
     thoại còn sống, an toàn gọi nhiều lần.
  3. Không để lại hàng mồ côi (execution/message trỏ tới hội thoại đã dọn).
  4. Vòng bảo trì **không được ném** dù CSDL hỏng.

Hiệu năng (ngưỡng rộng có chủ ý — chúng bắt lỗi ĐỘ PHỨC TẠP, không đo máy):
  5. Cây 400 nút: dựng + đi đường + liệt kê anh em.
  6. Một lượt 5.000 delta: `ap_dung` không bậc hai.
  7. `su_that()` của một hội thoại dài trả về trong một truy vấn có giới hạn.
"""
from __future__ import annotations

import time
import uuid
from datetime import timedelta

import pytest

from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import su_kien as S
from apps.chatltt.tables import ChatlttConversation, ChatlttExecution, ChatlttMessage


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "d.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _luot(db, uid="u-d"):
    hoi = H.tao_hoi_thoai(db, user_id=uid, model_alias="a")
    m = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role="user",
                          blocks=[{"type": "text", "text": "hoi"}])
    a = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role="assistant",
                          blocks=[], parent_id=m.id, status="streaming")
    ex = S.mo_execution(db, message=a, tool_name="text.chat", mode="stream")
    db.commit()
    return hoi, a, ex


# ── 1. Xoá khi đang chạy ────────────────────────────────────────────────────

def test_xoa_khi_dang_chay_va_su_kien_toi_sau_khong_hoi_sinh(db):
    hoi, a, ex = _luot(db)
    S.ap_dung(ex, {"type": "response.delta", "text": "dang viet"}, message=a)
    db.commit()

    H.xoa(db, user_id="u-d", conv_id=hoi.id)
    db.commit()
    assert ex.status == "cancelled" and a.status == "cancelled"

    # Luồng chậm chân: sự kiện tới SAU khi xoá. Nó ghi vào execution (đúng —
    # tiền phải được quyết toán), nhưng KHÔNG được làm hội thoại sống lại.
    S.ap_dung(ex, {"type": "billing.updated", "credit_giu": 5,
                   "credit_thu": 1, "credit_hoan": 4}, message=a)
    db.commit()
    assert ex.credit_thu == 1                       # tiền vẫn chốt đúng
    assert hoi.deleted_at is not None               # nhưng vẫn là đã xoá
    with pytest.raises(H.KhongTimThay):
        H.lay_hoi_thoai(db, user_id="u-d", conv_id=hoi.id)
    assert H.liet_ke(db, user_id="u-d") == []


# ── 2 + 3. Dọn dữ liệu đã xoá mềm ───────────────────────────────────────────

def test_don_dung_han_dung_thu_tu_va_khong_de_lai_mo_coi(db):
    song, _a1, _e1 = _luot(db)
    cu, _a2, _e2 = _luot(db)
    moi_xoa, _a3, _e3 = _luot(db)

    H.xoa(db, user_id="u-d", conv_id=cu.id)
    H.xoa(db, user_id="u-d", conv_id=moi_xoa.id)
    cu.deleted_at = H._now() - timedelta(days=40)        # quá hạn
    db.commit()

    kq = H.don_da_xoa(db)
    db.commit()
    assert kq == {"hoi_thoai": 1, "thong_diep": 2, "thi_hanh": 1}

    con = {c.id for c in db.query(ChatlttConversation).all()}
    assert con == {song.id, moi_xoa.id}                  # còn sống + mới xoá đều ở lại

    # Không hàng con nào trỏ tới một hội thoại không còn.
    for bang in (ChatlttMessage, ChatlttExecution):
        mo_coi = [r for r in db.query(bang).all() if r.conversation_id not in con]
        assert mo_coi == [], (bang.__name__, mo_coi)

    # Gọi lại: không đổi gì, không ném.
    assert H.don_da_xoa(db) == {"hoi_thoai": 0, "thong_diep": 0, "thi_hanh": 0}


def test_hoi_thoai_CON_SONG_khong_bao_gio_bi_don_du_rat_cu(db):
    hoi, _a, _e = _luot(db)
    hoi.created_at = H._now() - timedelta(days=3650)
    hoi.updated_at = hoi.created_at
    db.commit()
    assert H.don_da_xoa(db, gia_han_ngay=1) == {"hoi_thoai": 0, "thong_diep": 0, "thi_hanh": 0}
    assert db.get(ChatlttConversation, hoi.id) is not None


def test_bao_tri_khong_bao_gio_nem(db, monkeypatch):
    monkeypatch.setattr(H, "don_da_xoa",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("CSDL hong")))
    H.bao_tri()          # không ném ⇒ vòng bảo trì của app khác vẫn chạy


def test_manifest_khai_bao_tri_va_governance_biet_ba_bang():
    from apps.chatltt.manifest import MANIFEST
    from platform_core.public_api import governance

    assert callable(MANIFEST.bao_tri) and MANIFEST.bao_tri_moi_giay > 0
    ten = {s.table for s in governance.STORES}
    assert {"chatltt_conversation", "chatltt_message", "chatltt_execution"} <= ten
    for s in governance.STORES:
        if s.table.startswith("chatltt_"):
            assert s.klass == governance.CONTENT
            assert s.retention_days is None       # không tự già đi
            assert s.purged_by                    # nhưng phải nói ra cách nó biến mất


# ── 5. Cây lớn ──────────────────────────────────────────────────────────────

def test_cay_400_nut_van_nhanh_va_dung(db):
    uid = "u-lon"
    hoi = H.tao_hoi_thoai(db, user_id=uid, model_alias="a")
    cha = None
    la_cuoi = None
    for i in range(200):
        u = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role="user",
                              blocks=[{"type": "text", "text": f"hoi {i}"}],
                              parent_id=cha)
        a = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role="assistant",
                              blocks=[{"type": "text", "text": f"dap {i}"}],
                              parent_id=u.id)
        cha = a.id
        la_cuoi = a.id
    db.commit()

    t0 = time.monotonic()
    phang = H.tat_ca(db, user_id=uid, conv_id=hoi.id)
    rung = H.dung_cay(phang)
    duong = H.duong_toi_la(db, user_id=uid, conv_id=hoi.id, leaf_id=la_cuoi)
    dt = time.monotonic() - t0

    assert len(phang) == 400
    assert len(rung) == 1                              # đúng một gốc
    assert len(duong) == 400 and duong[-1].id == la_cuoi
    assert duong[0].parent_id is None
    # Ngưỡng rộng: nó bắt độ phức tạp bậc hai, không đo tốc độ máy.
    assert dt < 5.0, dt


def test_su_that_cua_hoi_thoai_dai_van_dung_hinh_dang(db):
    uid = "u-dai"
    hoi = H.tao_hoi_thoai(db, user_id=uid, model_alias="a")
    cha = None
    for i in range(60):
        m = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role="user",
                              blocks=[{"type": "text", "text": "x" * 500}],
                              parent_id=cha)
        cha = m.id
    db.commit()
    t0 = time.monotonic()
    st = H.su_that(db, user_id=uid, conv_id=hoi.id)
    dt = time.monotonic() - t0
    assert len(st["messages"]) == 60
    assert st["conversation"]["current_leaf_id"] == cha
    assert dt < 3.0, dt


# ── 6. Stream rất dài ───────────────────────────────────────────────────────

def test_nam_nghin_delta_khong_bac_hai(db):
    _hoi, a, ex = _luot(db)
    S.ap_dung(ex, {"type": "response.started", "request_id": "r", "credit_giu": 9}, message=a)

    t0 = time.monotonic()
    for i in range(5000):
        S.ap_dung(ex, {"type": "response.delta", "text": "x"}, message=a)
    dt = time.monotonic() - t0

    assert len(ex.partial_text) == 5000
    assert ex.seq == 5001
    assert dt < 5.0, dt

    # Khối mã rất lớn vẫn đồng bộ được vào message.
    S.ap_dung(ex, {"type": "response.completed", "finish_reason": "stop"}, message=a)
    S.dong_bo_khoi_text(a, ex)
    db.commit()
    assert a.blocks[-1]["type"] == "text" and len(a.blocks[-1]["text"]) == 5000
