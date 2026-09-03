"""
test_617 — Phase 07: cây hội thoại ChatLTT — nhánh, lá, sửa/tạo-lại, sở hữu, bất biến thời gian.

  1. Sửa-gửi-lại = anh em mới cùng cha; con cũ KHÔNG bị xoá; đổi lá quay lại nhánh cũ.
  2. Tạo-lại = assistant anh em mới dưới cùng message user.
  3. `duong_toi_la` đúng gốc→lá theo nhánh đang xem, lưu ở CSDL.
  4. Người khác không đọc/ghi được — cùng một `KhongTimThay`.
  5. `created_at(con) > created_at(cha)` kể cả khi đồng hồ lùi.
  6. `dung_cay` dựng đúng từ danh sách phẳng XÁO TRỘN (AC-01, đặc tả `convoStructure.spec.ts`).
  7. Tìm kiếm theo tiêu đề/nội dung; lưu trữ; xoá mềm huỷ lượt đang chảy.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

from apps.chatltt.services import hoi_thoai as H


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
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


def _text(t):
    return [{"type": "text", "text": t}]


def _hoi_thoai_mau(db, u="u-a"):
    hoi = H.tao_hoi_thoai(db, user_id=u, model_alias="ltt_llm", title="thu")
    m1 = H.them_thong_diep(db, user_id=u, conv_id=hoi.id, role="user", blocks=_text("hoi 1"))
    a1 = H.them_thong_diep(db, user_id=u, conv_id=hoi.id, role="assistant",
                           blocks=_text("dap 1"), parent_id=m1.id)
    m2 = H.them_thong_diep(db, user_id=u, conv_id=hoi.id, role="user",
                           blocks=_text("hoi 2"), parent_id=a1.id)
    a2 = H.them_thong_diep(db, user_id=u, conv_id=hoi.id, role="assistant",
                           blocks=_text("dap 2"), parent_id=m2.id)
    db.commit()
    return hoi, m1, a1, m2, a2


# ── 1 + 2 + 3 ────────────────────────────────────────────────────────────────

def test_sua_gui_lai_la_anh_em_moi_va_khong_xoa_con(db):
    hoi, m1, a1, m2, a2 = _hoi_thoai_mau(db)
    assert hoi.current_leaf_id == a2.id
    # Sửa "hoi 2" → gửi lại: anh em mới của m2 dưới a1.
    m2b = H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="user",
                            blocks=_text("hoi 2 sua"), parent_id=a1.id)
    a2b = H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="assistant",
                            blocks=_text("dap 2 sua"), parent_id=m2b.id)
    db.commit()
    anh_em = H.anh_em(db, user_id="u-a", conv_id=hoi.id, parent_id=a1.id)
    assert [m.id for m in anh_em] == [m2.id, m2b.id]
    assert H.lay_thong_diep(db, user_id="u-a", conv_id=hoi.id, msg_id=a2.id).status == "done"
    assert hoi.current_leaf_id == a2b.id
    duong = H.duong_toi_la(db, user_id="u-a", conv_id=hoi.id)
    assert [m.id for m in duong] == [m1.id, a1.id, m2b.id, a2b.id]
    # Quay lại nhánh cũ: chọn lá a2 ⇒ đường cũ nguyên vẹn.
    H.chon_la(db, user_id="u-a", conv_id=hoi.id, msg_id=a2.id)
    db.commit()
    duong = H.duong_toi_la(db, user_id="u-a", conv_id=hoi.id)
    assert [m.id for m in duong] == [m1.id, a1.id, m2.id, a2.id]


def test_tao_lai_la_assistant_anh_em_duoi_cung_user(db):
    hoi, m1, a1, m2, a2 = _hoi_thoai_mau(db)
    a2b = H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="assistant",
                            blocks=_text("dap 2 lan 2"), parent_id=m2.id)
    db.commit()
    anh_em = H.anh_em(db, user_id="u-a", conv_id=hoi.id, parent_id=m2.id)
    assert [m.id for m in anh_em] == [a2.id, a2b.id]
    assert hoi.current_leaf_id == a2b.id


# ── 4. Sở hữu ────────────────────────────────────────────────────────────────

def test_nguoi_khac_khong_doc_khong_ghi_cung_mot_cau(db):
    hoi, m1, a1, m2, a2 = _hoi_thoai_mau(db)
    for goi in (
        lambda: H.lay_hoi_thoai(db, user_id="u-b", conv_id=hoi.id),
        lambda: H.lay_hoi_thoai(db, user_id="u-b", conv_id="cv_khong_co"),
        lambda: H.them_thong_diep(db, user_id="u-b", conv_id=hoi.id, role="user",
                                  blocks=_text("x"), parent_id=a2.id),
        lambda: H.chon_la(db, user_id="u-b", conv_id=hoi.id, msg_id=a2.id),
        lambda: H.xoa(db, user_id="u-b", conv_id=hoi.id),
    ):
        with pytest.raises(H.KhongTimThay) as e1:
            goi()
    # Cha thuộc hội thoại khác của CÙNG người ⇒ cũng không nối được.
    hoi2 = H.tao_hoi_thoai(db, user_id="u-a")
    with pytest.raises(H.KhongTimThay):
        H.them_thong_diep(db, user_id="u-a", conv_id=hoi2.id, role="user",
                          blocks=_text("x"), parent_id=a2.id)
    assert H.liet_ke(db, user_id="u-b") == []


# ── 5. Bất biến thời gian ────────────────────────────────────────────────────

def test_con_luon_tre_hon_cha_ke_ca_khi_dong_ho_lui(db, monkeypatch):
    hoi, m1, a1, m2, a2 = _hoi_thoai_mau(db)
    qua_khu = a2.created_at - timedelta(minutes=5)
    monkeypatch.setattr(H, "_now", lambda: qua_khu)
    con = H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="user",
                            blocks=_text("sau"), parent_id=a2.id)
    assert con.created_at > a2.created_at
    phang = H.tat_ca(db, user_id="u-a", conv_id=hoi.id)
    assert [m.id for m in phang][-1] == con.id           # cha luôn trước con


# ── 6. Dựng cây từ danh sách xáo trộn ────────────────────────────────────────

def test_dung_cay_tu_danh_sach_xao_tron(db):
    hoi, m1, a1, m2, a2 = _hoi_thoai_mau(db)
    a2b = H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="assistant",
                            blocks=_text("dap 2b"), parent_id=m2.id)
    m2c = H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="user",
                            blocks=_text("hoi 2c"), parent_id=a1.id)
    db.commit()
    phang = H.tat_ca(db, user_id="u-a", conv_id=hoi.id)
    for _ in range(5):
        xao = list(phang)
        random.shuffle(xao)
        rung = H.dung_cay(xao)
        assert [n["message"].id for n in rung] == [m1.id]              # đúng một gốc
        n_a1 = rung[0]["children"][0]
        assert n_a1["message"].id == a1.id and n_a1["depth"] == 1
        con_a1 = [c["message"].id for c in n_a1["children"]]
        assert con_a1 == [m2.id, m2c.id]
        assert [c["sibling_index"] for c in n_a1["children"]] == [0, 1]
        n_m2 = n_a1["children"][0]
        assert [c["message"].id for c in n_m2["children"]] == [a2.id, a2b.id]
        assert n_m2["children"][1]["depth"] == 3


def test_cha_vang_mat_thi_len_goc_khong_mat_nut():
    from types import SimpleNamespace
    t0 = datetime(2026, 9, 3, tzinfo=timezone.utc)
    a = SimpleNamespace(id="a", parent_id=None, created_at=t0)
    b = SimpleNamespace(id="b", parent_id="khong_co", created_at=t0 + timedelta(seconds=1))
    rung = H.dung_cay([b, a])
    assert [n["message"].id for n in rung] == ["a", "b"]


# ── 7. Tìm · lưu trữ · xoá mềm ──────────────────────────────────────────────

def test_tim_kiem_luu_tru_va_xoa_mem_huy_luot_dang_chay(db):
    from apps.chatltt.services import su_kien as S
    hoi, m1, a1, m2, a2 = _hoi_thoai_mau(db)
    hoi2 = H.tao_hoi_thoai(db, user_id="u-a", title="ke hoach chuyen di")
    H.them_thong_diep(db, user_id="u-a", conv_id=hoi2.id, role="user",
                      blocks=_text("di Da Lat"))
    db.commit()
    assert [h.id for h in H.liet_ke(db, user_id="u-a", tim="chuyen di")] == [hoi2.id]
    assert [h.id for h in H.liet_ke(db, user_id="u-a", tim="dap 2")] == [hoi.id]
    assert len(H.liet_ke(db, user_id="u-a")) == 2
    H.luu_tru(db, user_id="u-a", conv_id=hoi2.id)
    db.commit()
    assert [h.id for h in H.liet_ke(db, user_id="u-a")] == [hoi.id]
    assert len(H.liet_ke(db, user_id="u-a", gom_luu_tru=True)) == 2
    # Xoá mềm hội thoại đang có lượt chảy ⇒ execution + message thành cancelled.
    a3 = H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="assistant",
                           blocks=[], parent_id=a2.id, status="streaming")
    ex = S.mo_execution(db, message=a3, tool_name="text.chat", mode="stream")
    db.commit()
    H.xoa(db, user_id="u-a", conv_id=hoi.id)
    db.commit()
    assert ex.status == "cancelled" and a3.status == "cancelled"
    assert H.liet_ke(db, user_id="u-a", gom_luu_tru=True) == [hoi2] or \
        [h.id for h in H.liet_ke(db, user_id="u-a", gom_luu_tru=True)] == [hoi2.id]
    with pytest.raises(H.KhongTimThay):
        H.lay_hoi_thoai(db, user_id="u-a", conv_id=hoi.id)
    assert H.lay_hoi_thoai(db, user_id="u-a", conv_id=hoi.id, gom_da_xoa=True).deleted_at


def test_khoi_sai_loai_bi_tu_choi(db):
    hoi = H.tao_hoi_thoai(db, user_id="u-a")
    with pytest.raises(H.ThamSoSai):
        H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="user",
                          blocks=[{"type": "video", "key": "x"}])
    with pytest.raises(H.ThamSoSai):
        H.them_thong_diep(db, user_id="u-a", conv_id=hoi.id, role="bot", blocks=_text("x"))
