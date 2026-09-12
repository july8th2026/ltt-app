"""
test_618 — Phase 07: sự kiện canonical → `chatltt_execution`, và reload dựng lại sự thật từ CSDL.

  1. Chuỗi sự kiện của facade (`runtime_noi_bo.luong.mo_luong`) áp lên execution:
     partial/reasoning cộng dồn, usage, billing, `finish_reason`, seq tăng đơn điệu.
  2. Thất bại / huỷ / bị cắt (`length`) ⇒ một `status` duy nhất + khối `status`/`error`.
  3. Giữa chừng mất trình duyệt: `su_that()` vẫn trả `partial_text` (AC-02/08/09).
  4. Loại sự kiện lạ ⇒ ném (fail-closed). `nen_ghi` đúng nhịp. `snapshot` đủ để nối lại.
  5. Chạy thật qua facade với luồng giả: sự kiện của `mo_luong` áp được nguyên xi.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import su_kien as S

#: 🔴 BÍ DANH CỦA TOOL THỬ PHẢI LÀ MỘT MODEL **CÓ GIÁ** (D07, dual-model 2.5).
#:    Trước 2.5 chỗ này là chuỗi bịa `_ALIAS_THU` và nó chạy được **chỉ vì**
#:    `gia_token` bỏ qua model. Từ D07 giá đi theo model, nên mọi tool đi qua
#:    `runtime_noi_bo/luong.py` — tức qua `thanh_toan` — phải khai một model mà
#:    bảng giá biết. Đây là ràng buộc thật của tầng đó, không phải phiền toái
#:    của phép kiểm: một model không có giá mà vẫn giữ được tiền nghĩa là tiền
#:    đang được tính bằng bảng giá của một model **khác**.
#:
#: ⛔ Lấy từ `gia_token`, đừng gõ thẳng `"ltt-3.8"`: ngày đổi model mặc định thì
#:    một hằng số gõ tay sẽ làm sáu tệp này hỏng lại cùng lúc.
from platform_core.llm.gia_token import MODEL_GIA_MAC_DINH as _ALIAS_THU


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "e.db").as_posix())
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


def _luot(db, u="u-a"):
    hoi = H.tao_hoi_thoai(db, user_id=u, model_alias="ltt_llm")
    m = H.them_thong_diep(db, user_id=u, conv_id=hoi.id, role="user",
                          blocks=[{"type": "text", "text": "hoi"}])
    a = H.them_thong_diep(db, user_id=u, conv_id=hoi.id, role="assistant", blocks=[],
                          parent_id=m.id, status="streaming")
    ex = S.mo_execution(db, message=a, tool_name="text.chat", mode="stream")
    db.commit()
    return hoi, m, a, ex


def _ap(db, ex, a, sks):
    for sk in sks:
        ket = S.ap_dung(ex, sk, message=a)
        if ket:
            S.dong_bo_khoi_text(a, ex)
    db.commit()


# ── 1. Chuỗi xong ────────────────────────────────────────────────────────────

def test_chuoi_su_kien_xong(db):
    hoi, m, a, ex = _luot(db)
    _ap(db, ex, a, [
        {"type": "response.started", "request_id": "cl_abc", "credit_giu": 12},
        {"type": "reasoning.delta", "text": "nghi "},
        {"type": "reasoning.delta", "text": "ky"},
        {"type": "response.delta", "text": "xin "},
        {"type": "response.delta", "text": "chao"},
        {"type": "usage.updated", "token_vao": 100, "token_ra": 5, "token_cache": 0, "do_duoc": True},
        {"type": "response.completed", "finish_reason": "stop"},
        {"type": "billing.updated", "credit_giu": 12, "credit_thu": 1, "credit_hoan": 11,
         "do_duoc": True, "phien_ban_gia": "v"},
    ])
    assert ex.status == "done" and a.status == "done"
    assert (ex.partial_text, ex.reasoning_text, ex.finish_reason) == ("xin chao", "nghi ky", "stop")
    assert ex.request_id == "cl_abc" and ex.seq == 8
    assert (ex.credit_giu, ex.credit_thu, ex.credit_hoan) == (12, 1, 11)
    assert ex.usage["token_ra"] == 5
    assert a.blocks == [{"type": "reasoning", "text": "nghi ky"}, {"type": "text", "text": "xin chao"}]
    assert ex.finished_at is not None


# ── 2. Ba kết cục còn lại ────────────────────────────────────────────────────

def test_that_bai_huy_va_bi_cat(db):
    hoi, m, a, ex = _luot(db)
    _ap(db, ex, a, [{"type": "response.started", "request_id": "r", "credit_giu": 3},
                    {"type": "response.failed", "code": "ban", "ly_do": "may B dang ban",
                     "retry_after_s": 30},
                    {"type": "billing.updated", "credit_giu": 3, "credit_thu": 0, "credit_hoan": 3}])
    assert (ex.status, ex.error_code, a.status) == ("failed", "ban", "failed")
    assert a.blocks[-1] == {"type": "error", "code": "ban", "text": "may B dang ban"}

    hoi, m, a, ex = _luot(db)
    _ap(db, ex, a, [{"type": "response.started", "request_id": "r", "credit_giu": 3},
                    {"type": "response.delta", "text": "mot nua"},
                    {"type": "response.cancelled"}])
    assert (ex.status, a.status) == ("cancelled", "cancelled")
    assert a.blocks == [{"type": "text", "text": "mot nua"}, {"type": "status", "code": "cancelled"}]

    hoi, m, a, ex = _luot(db)
    _ap(db, ex, a, [{"type": "response.started", "request_id": "r", "credit_giu": 3},
                    {"type": "response.delta", "text": "dai..."},
                    {"type": "response.completed", "finish_reason": "length"}])
    assert ex.status == "done" and a.blocks[-1] == {"type": "status", "code": "length"}


# ── 3. Reload giữa chừng ─────────────────────────────────────────────────────

def test_su_that_giua_chung_tra_partial_tu_csdl(db):
    hoi, m, a, ex = _luot(db)
    _ap(db, ex, a, [{"type": "response.started", "request_id": "r", "credit_giu": 3},
                    {"type": "response.delta", "text": "dang viet "}])
    st = H.su_that(db, user_id="u-a", conv_id=hoi.id)
    assert st["conversation"]["current_leaf_id"] == a.id
    tin = {x["id"]: x for x in st["messages"]}
    assert tin[a.id]["status"] == "streaming"
    assert tin[a.id]["execution"]["partial_text"] == "dang viet "
    assert tin[a.id]["execution"]["seq"] == 2
    assert tin[m.id]["parent_id"] is None and tin[a.id]["parent_id"] == m.id
    # Người khác: không có gì.
    with pytest.raises(H.KhongTimThay):
        H.su_that(db, user_id="u-b", conv_id=hoi.id)


# ── 4. Hợp đồng ──────────────────────────────────────────────────────────────

def test_su_kien_la_thi_nem_va_nhip_ghi_va_snapshot(db):
    hoi, m, a, ex = _luot(db)
    with pytest.raises(ValueError):
        S.ap_dung(ex, {"type": "response.gi_do"})
    assert S.nen_ghi(luc_ghi_cuoi=0.0, bay_gio=0.5, ky_tu_moi=10, ket_thuc=False) is False
    assert S.nen_ghi(luc_ghi_cuoi=0.0, bay_gio=1.2, ky_tu_moi=10, ket_thuc=False) is True
    assert S.nen_ghi(luc_ghi_cuoi=0.0, bay_gio=0.1, ky_tu_moi=250, ket_thuc=False) is True
    assert S.nen_ghi(luc_ghi_cuoi=0.0, bay_gio=0.1, ky_tu_moi=1, ket_thuc=True) is True
    S.ap_dung(ex, {"type": "response.delta", "text": "a"})
    snap = S.snapshot(ex)
    assert snap["seq"] == 1 and snap["partial_text"] == "a" and snap["status"] == "streaming"
    assert set(snap) >= {"execution_id", "credit", "usage", "finish_reason", "error_code"}


# ── 5. Qua facade thật với luồng giả ─────────────────────────────────────────

def test_su_kien_cua_facade_ap_nguyen_xi(db, monkeypatch):
    """Không cần app thật: một ToolSpec giả + `luong_vlm.mo` giả, đúng như test_600."""
    import json

    from platform_core import credit, registry as reg
    from platform_core.llm import luong_vlm
    from platform_core.runtime_noi_bo import luong as L
    from platform_core.users import tao_nguoi_dung
    from tests.test_600_runtime_noi_bo_luong import EXECUTOR_GIA  # noqa: F401

    tool = reg.ToolSpec(name="text.thu618", job_type="t618.j", description="d",
                        params_schema={"messages": {"type": "json[]"}},
                        returns={"content": "text"},
                        sync_executor="tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA")
    man = reg.AppManifest(slug="t618", display_name="x", route_prefix="/t618",
                          job_types=("t618.j",), credit_cost=lambda p: 1, tools=(tool,))
    monkeypatch.setattr(reg, "discover", lambda apps_dir=None: [reg.LoadedApp(manifest=man)])

    NL = bytes([10])

    def sse(g):
        return b"data: " + json.dumps(g).encode() + NL + NL

    class Gia:
        ma, content_type = 200, "text/event-stream"

        def __init__(self):
            self.luong = iter([
                sse({"choices": [{"delta": {"reasoning_content": "n"}}]}),
                sse({"choices": [{"delta": {"content": "xin"}}]}),
                sse({"choices": [{"delta": {"content": " chao"}, "finish_reason": "stop"}]}),
                # 10.000 vao (500 mcredit) + 1.250 ra (500) = DUNG 1,000 credit.
                # Do la co duy nhat cho `thu == 1` o CA C1 (lam tron len) lan C3
                # (chia lay nguyen), nen khang dinh `credit_thu >= 1` duoi day
                # bat bien voi chinh sach lam tron. Co cu (50, 3) chi qua duoc
                # nho CAI SAN cua C1 — tuc mot phep kiem ve SU KIEN dang duoc
                # do boi mot chinh sach TINH TIEN.
                sse({"choices": [],
                     "usage": {"prompt_tokens": 10_000, "completion_tokens": 1_250}}),
                b"data: [DONE]" + NL + NL])

        def xong(self, tokens=0):
            pass

        def hong(self, exc):
            pass

    monkeypatch.setattr(luong_vlm, "mo", lambda db, *, duong, than, timeout_s=0: Gia())
    u = tao_nguoi_dung(db, email="e618@example.com", password="a-good-password-12")
    db.flush()
    credit.cap_tay(db, u.id, 100, by="test")
    db.commit()

    hoi, m, a, ex = _luot(db, u=u.id)
    for sk in L.mo_luong(db, user_id=u.id, tool_name="text.thu618",
                         params={"model": _ALIAS_THU,
                                 "messages": [{"role": "user", "content": "hoi"}]}):
        if S.ap_dung(ex, sk, message=a):
            S.dong_bo_khoi_text(a, ex)
    db.commit()
    assert ex.status == "done" and ex.partial_text == "xin chao" and ex.reasoning_text == "n"
    assert ex.finish_reason == "stop" and ex.request_id.startswith("cl")
    assert ex.credit_giu >= 1 and ex.credit_thu >= 1
    assert ex.credit_giu - ex.credit_thu == ex.credit_hoan
    assert int(credit.so_du(db, u.id)) == 100 - ex.credit_thu
