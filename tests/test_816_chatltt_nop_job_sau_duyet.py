"""
test_816 — duyệt xong thì NỘP JOB, không chạy đồng bộ. (H44 P05)

`image.ltt` và `speech.ltt` không trả kết quả trong một lời gọi hàm. Chạy chúng
đồng bộ trong luồng web là một request giữ 5 phút — tức một **524 của
Cloudflare** (trần 100 giây), và người dùng thấy lượt hỏng trong khi máy B vẫn
đang vẽ.

Hai mệnh đề đắt:

  1. `credit_da_bao` phải là **số người dùng đã nhìn thấy trên phiếu**. Giữa lúc
     báo giá và lúc bấm có thể vài phút; `tao_media.tao` tính lại và từ chối nếu
     lệch, nên người dùng không bị trừ một số khác với số họ đồng ý.
  2. Job gắn vào **đúng tin nhắn của run**, không tạo tin nhắn thứ hai. Không có
     `tin_nhan` thì câu trả lời của model rơi vào một chỗ khác với chỗ nó đang nói.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import bo_chay_tool as B
from apps.chatltt.services import chieu_tool as C
from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import duyet as D
from apps.chatltt.services import luu_run as LR


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


U = "u-chu"
ANH = "image.ltt"

TOOLS = [{"type": "function", "function": {
    "name": ANH, "description": "ve mot buc anh",
    "parameters": {"type": "object",
                   "properties": {"prompt": {"type": "string"},
                                  "so_luong": {"type": "integer"}},
                   "required": ["prompt"]}}}]


@pytest.fixture(autouse=True)
def _mo_cong(monkeypatch):
    monkeypatch.setattr(C, "CHO_MODEL_GOI", (ANH,))


@pytest.fixture()
def nop(monkeypatch):
    """Thay `tao_media.tao` để không phải kéo cả hàng đợi job vào đây."""
    from apps.chatltt.services import tao_media
    da_goi = []

    def gia(db, **kw):
        da_goi.append(kw)
        return {"job_id": "job_abc", "execution_id": "ex_1", "credit": kw.get(
            "credit_da_bao") or 0, "conversation_id": "c-1", "message_id": "m-1"}

    monkeypatch.setattr(tao_media, "tao", gia)
    return da_goi


def _gia(ten, ds):
    return (12 * int(ds.get("so_luong", 1)), "ltt-vlm-2026-08-22")


def _goi(ten, tho):
    return [{"type": "tool_call.delta", "tool_calls": [
                {"index": 0, "id": "call_1", "type": "function",
                 "function": {"name": ten, "arguments": tho}}]},
            {"type": "response.completed", "finish_reason": "tool_calls"}]


def _model(*luot):
    it = iter(luot)
    return lambda _m, _t: next(it)


def _cho_duyet(db, tho='{"prompt":"meo"}'):
    r = LR.mo_run(db, user_id=U, conv_id="c-1", message_id="m-1")
    db.commit()
    ct = B.tao(db, user_id=U, run_id=r.id, khoi_tools=TOOLS, bao_gia=_gia)
    run = DP.chay(messages=[], tools=TOOLS, goi_model=_model(_goi(ANH, tho)),
                  chay_tool=ct, ghi=lambda b: LR.ghi_buoc(db, r, b))
    assert run.trang_thai == DP.AWAITING_APPROVAL
    return r, run


class TinNhanGia:
    id = "m-1"


# ── 1. Duyệt xong ⇒ NỘP JOB, không chạy thẳng ──────────────────────────────

def test_duyet_xong_thi_ra_ChoJob_khong_ra_KetQua(db, nop):
    r, run = _cho_duyet(db)
    ap = D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"]
    D.duyet(db, user_id=U, approval_id=ap)

    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                             tin_nhan=TinNhanGia(), conv_id="c-1")
    assert isinstance(kq[ap], DP.ChoJob)
    assert kq[ap].job_id == "job_abc"
    assert len(nop) == 1


def test_run_di_tu_CHO_NGUOI_sang_CHO_MAY(db, nop):
    """⭐ Duyệt xong KHÔNG có nghĩa là xong việc. Bước vẫn treo, chỉ đổi lý do."""
    r, run = _cho_duyet(db)
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                             tin_nhan=TinNhanGia(), conv_id="c-1")
    run2 = DP.tiep_tuc(run, ket_qua_duyet=kq, goi_model=_model([]),
                       chay_tool=lambda t, d, c: None,
                       ghi=lambda b: LR.ghi_buoc(db, r, b))
    assert run2.trang_thai == DP.WAITING_BACKGROUND
    b = run2.dang_cho_job()[0]
    assert b.cho_job == "job_abc"
    assert b.cho_duyet == "", (
        "phai XOA cho_duyet — mang ca hai thi khoa_treo tra ve phieu DA QUYET, "
        "va vong sau doi lai mot cau tra loi da co")


def test_trang_thai_cho_job_xuong_CSDL(db, nop):
    from apps.chatltt.tables import ChatlttStep
    r, run = _cho_duyet(db)
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                             tin_nhan=TinNhanGia(), conv_id="c-1")
    DP.tiep_tuc(run, ket_qua_duyet=kq, goi_model=_model([]),
                chay_tool=lambda t, d, c: None,
                ghi=lambda b: LR.ghi_buoc(db, r, b))
    st = db.query(ChatlttStep).filter_by(loai="tool").one()
    assert st.trang_thai == "cho_job" and st.job_id == "job_abc"


# ── 2. Tiền: số người dùng ĐÃ NHÌN THẤY ────────────────────────────────────

def test_credit_da_bao_la_so_TREN_PHIEU(db, nop):
    """🔴 Giữa lúc báo giá và lúc bấm có thể vài phút. `tao_media.tao` tính lại
    và từ chối nếu lệch — nên người dùng không bị trừ một số khác với số họ
    đã đồng ý."""
    r, run = _cho_duyet(db, tho='{"prompt":"meo","so_luong":3}')
    ap = D.dang_cho(db, user_id=U, run_id=r.id)[0]
    assert ap["credit"] == 36
    D.duyet(db, user_id=U, approval_id=ap["approval_id"])
    B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                        tin_nhan=TinNhanGia(), conv_id="c-1")
    assert nop[0]["credit_da_bao"] == 36


def test_doi_so_DA_SUA_la_thu_duoc_nop(db, nop):
    """⛔ Nộp bản gốc sau khi người dùng đã sửa là nộp một việc không ai duyệt."""
    r, run = _cho_duyet(db, tho='{"prompt":"meo","so_luong":4}')
    ap = D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"]
    D.duyet(db, user_id=U, approval_id=ap,
            doi_so_da_sua={"prompt": "meo", "so_luong": 1})
    B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                        tin_nhan=TinNhanGia(), conv_id="c-1")
    assert nop[0]["params"] == {"prompt": "meo", "so_luong": 1}


def test_job_noi_voi_run_va_step(db, nop):
    """`chatltt_execution.run_id`/`step_id` — một bút toán nối với bước sinh ra nó."""
    r, run = _cho_duyet(db)
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])
    B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                        tin_nhan=TinNhanGia(), conv_id="c-1")
    assert nop[0]["run_id"] == r.id
    assert nop[0]["step_id"], "phai co step_id that"


# ── 3. Fail-closed ─────────────────────────────────────────────────────────

def test_THIEU_tin_nhan_thi_khong_nop_va_model_doc_duoc_loi(db, nop):
    """Không có tin nhắn để gắn thì kết quả rơi vào hư không. Fail-closed."""
    r, run = _cho_duyet(db)
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS)
    v = list(kq.values())[0]
    assert not isinstance(v, DP.ChoJob)
    assert v.ok is False and v.ma_loi == "khong_gan_duoc"
    assert nop == [], "KHONG duoc nop job nao"


def test_nop_job_NEM_thi_thanh_du_lieu_khong_giet_run(db, monkeypatch):
    from apps.chatltt.services import tao_media

    def hong(db, **kw):
        raise RuntimeError("gia da doi: bao 36, tinh lai 48")

    monkeypatch.setattr(tao_media, "tao", hong)
    r, run = _cho_duyet(db)
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                             tin_nhan=TinNhanGia(), conv_id="c-1")
    v = list(kq.values())[0]
    assert v.ok is False and v.ma_loi == "nop_job_hong"
    assert "gia da doi" in v.thong_diep, "model phai doc duoc VI SAO"
    assert "RuntimeError" in v.thong_diep, "khong duoc nuot kieu ngoai le"


def test_TU_CHOI_thi_KHONG_nop_job(db, nop):
    r, run = _cho_duyet(db)
    D.tu_choi(db, user_id=U,
              approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS,
                             tin_nhan=TinNhanGia(), conv_id="c-1")
    assert nop == []
    assert list(kq.values())[0].ma_loi == "tu_choi"


# ── 4. Seam trong `tao_media.tao` — với CSDL thật ──────────────────────────

def test_tin_nhan_truyen_vao_thi_KHONG_tao_tin_nhan_moi(db):
    """🔴 Không có tham số này thì một lần model gọi `image.ltt` sinh ra một tin
    nhắn THỨ HAI — và câu trả lời rơi vào một chỗ khác với chỗ nó đang nói."""
    from apps.chatltt.services import hoi_thoai as H
    from apps.chatltt.services import tao_media
    from apps.chatltt.tables import ChatlttMessage

    hoi = H.tao_hoi_thoai(db, user_id=U, model_alias="ltt_llm")
    m = H.them_thong_diep(db, user_id=U, conv_id=hoi.id, role="assistant",
                          blocks=[], status="queued")
    db.commit()
    truoc = db.query(ChatlttMessage).count()

    goi = {}
    from platform_core.runtime_noi_bo import job as J

    class BG:
        credit = 7
        phien_ban_gia = "v1"
        tham_so_sach = {"prompt": "meo"}

    import types
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(J, "bao_gia", lambda ten, params, db=None, user_id="": BG())
        monkey.setattr(J, "nop_job",
                       lambda db, **kw: types.SimpleNamespace(id="job_zzz"))
        r = tao_media.tao(db, user_id=U, conv_id=hoi.id, ten=ANH,
                          params={"prompt": "meo"}, tin_nhan=m,
                          run_id="run_x", step_id="st_x")
        goi.update(r)
    finally:
        monkey.undo()

    assert db.query(ChatlttMessage).count() == truoc, "KHONG duoc tao tin nhan moi"
    assert goi["message_id"] == m.id
    from apps.chatltt.tables import ChatlttExecution
    ex = db.get(ChatlttExecution, goi["execution_id"])
    assert (ex.run_id, ex.step_id) == ("run_x", "st_x")
