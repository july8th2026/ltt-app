"""
test_627 — Phase 12 nhóm ĐỒNG THỜI và TIỀN. Tấn công, không nghiệm thu.

  1. Hai tab cùng xem một lượt: cả hai thấy, không ai nuốt sự kiện của ai.
  2. Đua Dừng ↔ Xong: bấm Dừng đúng lúc lượt vừa xong ⇒ **không** đảo ngược
     trạng thái đã kết thúc, và **không** thu thêm lần nữa.
  3. Nộp trùng (double-click, F5): một job, một lần giữ tiền.
  4. Sự kiện kết thúc tới HAI lần ⇒ tiền chỉ đi một lần.
  5. Worker chết sau khi giữ tiền: lượt không nằm "đang chảy" vĩnh viễn.
  6. Kết quả một phần (job xong nhưng không có artifact) ⇒ nói ra, không im.
  7. Nhiều lượt của cùng một người: mỗi lượt một sổ riêng, không cộng nhầm.
"""
from __future__ import annotations

import json
import threading
import uuid

import pytest

from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import su_kien as S

NL = bytes([10])


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
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


def _user(db, credits=1000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="t627-" + uuid.uuid4().hex[:6] + "@example.com",
                       password="a-good-password-12", is_verified=True)
    db.flush()
    if credits:
        credit.cap_tay(db, u.id, credits, by="test")
    db.commit()
    return u.id


def _luot(db, uid, mode="stream"):
    hoi = H.tao_hoi_thoai(db, user_id=uid, model_alias="a")
    m = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role="user",
                          blocks=[{"type": "text", "text": "hoi"}])
    a = H.them_thong_diep(db, user_id=uid, conv_id=hoi.id, role="assistant",
                          blocks=[], parent_id=m.id, status="streaming")
    ex = S.mo_execution(db, message=a, tool_name="text.chat", mode=mode)
    db.commit()
    return hoi, a, ex


# ── 1. Hai người xem cùng một lượt ──────────────────────────────────────────

def test_hai_tab_cung_xem_khong_ai_nuot_su_kien_cua_ai():
    from apps.chatltt.services import dang_chay as D

    so = D.bat_dau("ex_627a", "u")
    q1, q2 = so.dang_ky(), so.dang_ky()
    for i in range(5):
        so.phat({"type": "response.delta", "text": str(i)})
    it1, it2 = D.theo_doi(q1, cho_moi_lan_s=0.05), D.theo_doi(q2, cho_moi_lan_s=0.05)
    a = [next(it1)["text"] for _ in range(5)]
    b = [next(it2)["text"] for _ in range(5)]
    assert a == b == ["0", "1", "2", "3", "4"]
    D.ket_thuc("ex_627a")
    assert list(it1) == [] and list(it2) == []


def test_nguoi_xem_cham_bi_bo_delta_CU_chu_khong_chan_luot(monkeypatch):
    """Hàng đợi đầy ⇒ bỏ delta cũ NHẤT của người đó, không chặn cả lượt.

    Sự thật vẫn ở CSDL, nên họ thấy đủ ở snapshot kế tiếp — nhưng lượt không
    được đứng lại vì một trình duyệt đọc chậm.
    """
    from apps.chatltt.services import dang_chay as D

    monkeypatch.setattr(D, "SUC_CHUA_HANG_DOI", 3)
    so = D.bat_dau("ex_627b", "u")
    q = so.dang_ky()
    for i in range(10):
        so.phat({"type": "response.delta", "text": str(i)})   # không treo
    it = D.theo_doi(q, cho_moi_lan_s=0.05)
    con = [next(it)["text"] for _ in range(3)]
    assert con == ["7", "8", "9"]                              # giữ MỚI nhất
    D.ket_thuc("ex_627b")


# ── 2. Đua Dừng ↔ Xong ──────────────────────────────────────────────────────

def test_dung_sau_khi_da_xong_khong_dao_nguoc_va_khong_thu_them(db):
    from apps.chatltt.services import luot as LUOT
    uid = _user(db)
    _hoi, a, ex = _luot(db, uid)
    S.ap_dung(ex, {"type": "response.started", "request_id": "r", "credit_giu": 5}, message=a)
    S.ap_dung(ex, {"type": "response.completed", "finish_reason": "stop"}, message=a)
    S.ap_dung(ex, {"type": "billing.updated", "credit_giu": 5,
                   "credit_thu": 2, "credit_hoan": 3}, message=a)
    db.commit()
    truoc = (ex.status, ex.credit_thu, ex.seq)

    kq = LUOT.dung(db, user_id=uid, execution_id=ex.id)
    assert kq["status"] == "done"                    # KHÔNG thành "cancelled"
    assert (ex.status, ex.credit_thu) == (truoc[0], truoc[1])


def test_su_kien_ket_thuc_toi_hai_lan_thi_tien_chi_di_mot_lan(db):
    uid = _user(db)
    _hoi, a, ex = _luot(db, uid)
    bill = {"type": "billing.updated", "credit_giu": 5, "credit_thu": 2, "credit_hoan": 3}
    S.ap_dung(ex, {"type": "response.completed", "finish_reason": "stop"}, message=a)
    S.ap_dung(ex, bill, message=a)
    S.ap_dung(ex, bill, message=a)                    # lặp
    db.commit()
    assert (ex.credit_thu, ex.credit_hoan) == (2, 3)  # không cộng dồn


# ── 3. Nộp trùng ────────────────────────────────────────────────────────────

def test_nop_trung_mot_job_mot_lan_giu_tien(db):
    from platform_core import credit
    from platform_core.runtime_noi_bo import job as J

    uid = _user(db, 100)
    bg = J.bao_gia("image.ltt", {"prompt": "meo", "count": 2}, db=db, user_id=uid)
    j1 = J.nop_job(db, user_id=uid, bao_gia=bg, idempotency_key="k1")
    db.commit()
    j2 = J.nop_job(db, user_id=uid, bao_gia=bg, idempotency_key="k1")
    db.commit()
    assert j1.id == j2.id
    assert int(credit.so_du(db, uid)) == 100 - bg.credit
    # Khoá khác ⇒ job khác, và giữ tiền lần hai (đúng: hai yêu cầu thật).
    j3 = J.nop_job(db, user_id=uid, bao_gia=bg, idempotency_key="k2")
    db.commit()
    assert j3.id != j1.id
    assert int(credit.so_du(db, uid)) == 100 - 2 * bg.credit


# ── 5. Worker chết / lượt mồ côi ────────────────────────────────────────────

def test_luot_khong_bao_gio_nam_dang_chay_vinh_vien(db, monkeypatch):
    """Thân luồng vỡ giữa chừng ⇒ vẫn để lại một trạng thái KẾT THÚC."""
    from apps.chatltt.services import luot as LUOT
    from platform_core.runtime_noi_bo import luong as L

    uid = _user(db)
    _hoi, a, ex = _luot(db, uid)
    ex_id = ex.id

    def no(*_a, **_k):
        raise RuntimeError("worker chet giua chung")

    monkeypatch.setattr(L, "mo_luong", no)
    LUOT.chay(ex_id, user_id=uid)

    db.expire_all()
    from apps.chatltt.tables import ChatlttExecution, ChatlttMessage
    ex2 = db.get(ChatlttExecution, ex_id)
    a2 = db.get(ChatlttMessage, ex2.message_id)
    assert ex2.status == "failed" and a2.status == "failed"
    assert ex2.finished_at is not None
    assert ex2.error_code == "loi_noi_bo"


def test_luong_can_ma_khong_co_su_kien_ket_thuc_van_dong_lai(db, monkeypatch):
    from apps.chatltt.services import luot as LUOT
    from platform_core.runtime_noi_bo import luong as L

    uid = _user(db)
    _hoi, _a, ex = _luot(db, uid)
    ex_id = ex.id
    monkeypatch.setattr(L, "mo_luong",
                        lambda *a, **k: iter([{"type": "response.delta", "text": "a"}]))
    LUOT.chay(ex_id, user_id=uid)
    db.expire_all()
    from apps.chatltt.tables import ChatlttExecution
    ex2 = db.get(ChatlttExecution, ex_id)
    assert ex2.status == "failed" and ex2.error_code == "luong_cat"
    assert ex2.partial_text == "a"                    # phần đã sinh KHÔNG mất


# ── 6. Kết quả một phần ─────────────────────────────────────────────────────

def test_job_xong_nhung_khong_co_artifact_thi_noi_ra(db, monkeypatch):
    from apps.chatltt.services import tao_media as TM
    from apps.chatltt.tables import ChatlttMessage

    uid = _user(db)
    _hoi, a, ex = _luot(db, uid, mode="job")
    ex.tool_name = "image.ltt"
    ex.job_id = "job-627"
    ex.credit_giu = 6
    db.commit()

    class JobGia:
        id = "job-627"
        status = "done"
        result = {"image_keys": [], "so_anh_xin": 2, "so_anh_that": 0,
                  "credit_cost": 0}
        progress = 100
        error = ""

    monkeypatch.setattr("platform_core.job_history.get_owned",
                        lambda db, u, j: JobGia())
    TM.dong_bo(db, user_id=uid, execution_id=ex.id)
    db.expire_all()
    a2 = db.get(ChatlttMessage, ex.message_id)
    assert a2.blocks == [{"type": "status", "code": "khong_co_ket_qua"}]
    assert ex.credit_thu == 0 and ex.credit_hoan == 6


# ── 7. Nhiều lượt, mỗi lượt một sổ ──────────────────────────────────────────

def test_ba_luot_song_song_moi_luot_mot_so_rieng(db):
    uid = _user(db)
    exs = []
    for _ in range(3):
        _hoi, a, ex = _luot(db, uid)
        exs.append((a, ex))
    for i, (a, ex) in enumerate(exs):
        S.ap_dung(ex, {"type": "response.started", "request_id": f"r{i}",
                       "credit_giu": 10}, message=a)
        S.ap_dung(ex, {"type": "response.delta", "text": f"luot-{i}"}, message=a)
        S.ap_dung(ex, {"type": "billing.updated", "credit_giu": 10,
                       "credit_thu": i + 1, "credit_hoan": 9 - i}, message=a)
    db.commit()
    assert [ex.partial_text for _a, ex in exs] == ["luot-0", "luot-1", "luot-2"]
    assert [ex.credit_thu for _a, ex in exs] == [1, 2, 3]
    assert [ex.request_id for _a, ex in exs] == ["r0", "r1", "r2"]
