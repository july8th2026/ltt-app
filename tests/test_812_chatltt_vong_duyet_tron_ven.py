"""
test_812 — vòng duyệt TRỌN VẸN, có CSDL thật. (H44 P04)

`test_809` ghim luật duyệt, `test_810` ghim máy trạng thái, `test_811` ghim hai
cửa HTTP. Cả ba đều xanh mà hệ thống vẫn có thể hỏng — vì chỗ hỏng nằm **giữa**
chúng. Tệp này chạy đúng con đường một người dùng thật đi:

    model doi tool co phi
      -> phieu duyet mo ra, BEN (commit) truoc khi ai duoc bao
      -> run dung o AWAITING_APPROVAL
      -> nguoi dung bam dong y (co the SUA doi so)
      -> tool chay bang doi so DA SUA
      -> model noi tiep va tra loi

Và con đường thứ hai, quan trọng ngang bằng: người dùng bấm **từ chối**, và
lượt vẫn kết thúc tử tế.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import bo_chay_tool as B
from apps.chatltt.services import chieu_tool as C
from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import duyet as D
from apps.chatltt.services import luu_run as LR
from apps.chatltt.services import thi_hanh as T


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


U = "u-chu"

TOOLS = [
    {"type": "function", "function": {
        "name": "image.ltt", "description": "ve mot buc anh",
        "parameters": {"type": "object",
                       "properties": {"prompt": {"type": "string"},
                                      "so_luong": {"type": "integer"}},
                       "required": ["prompt"]}}},
    {"type": "function", "function": {
        "name": "noi_bo.tinh", "description": "tinh mot bieu thuc",
        "parameters": {"type": "object",
                       "properties": {"bieu_thuc": {"type": "string"}},
                       "required": ["bieu_thuc"]}}},
]


@pytest.fixture(autouse=True)
def _mo_cong(monkeypatch):
    """Mở cổng thứ tư cho `image.ltt` và cài một handler giả cho nó.

    ⚠️ `monkeypatch.setitem` chứ không gán thẳng vào `T._SO_HANDLER` — gán thẳng
       để lại rác trong sổ đăng ký cho mọi tệp chạy sau, và đó đúng là cái bẫy
       `bay-trang-thai-ngoai-ro-vao-test`.
    """
    monkeypatch.setattr(C, "CHO_MODEL_GOI", ("image.ltt", "noi_bo.tinh"))
    da_chay = []
    monkeypatch.setitem(T._SO_HANDLER, "image.ltt",
                        lambda db, uid, ds: (da_chay.append(ds),
                                             {"url": f"anh/{ds.get('so_luong', 1)}.png"})[1])
    return da_chay


def _gia(ten, ds):
    return (12 * int(ds.get("so_luong", 1)), "ltt-vlm-2026-08-22")


def _chu(t):
    return [{"type": "response.delta", "text": t},
            {"type": "response.completed", "finish_reason": "stop"}]


def _goi(*cap):
    return [{"type": "tool_call.delta", "tool_calls": [
                {"index": i, "id": f"call_{i+1}", "type": "function",
                 "function": {"name": t, "arguments": d}}
                for i, (t, d) in enumerate(cap)]},
            {"type": "response.completed", "finish_reason": "tool_calls"}]


def _model(*luot):
    it = iter(luot)
    return lambda _m, _t: next(it)


def _bat_dau(db, *, model, bao_gia=_gia, co_phi=False):
    r = LR.mo_run(db, user_id=U, conv_id="c-1", message_id="m-1")
    db.commit()
    ct = B.tao(db, user_id=U, run_id=r.id, khoi_tools=TOOLS, bao_gia=bao_gia,
               cho_chay_co_phi=lambda: co_phi)
    run = DP.chay(messages=[{"role": "user", "content": "ve con meo"}], tools=TOOLS,
                  goi_model=model, chay_tool=ct,
                  ghi=lambda b: LR.ghi_buoc(db, r, b))
    return r, run, ct


# ── 1. Đường chính: hỏi → đồng ý → chạy ────────────────────────────────────

def test_tool_co_phi_lam_run_dung_va_MO_PHIEU_that(db):
    r, run, _ = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    assert run.trang_thai == DP.AWAITING_APPROVAL

    ds = D.dang_cho(db, user_id=U, run_id=r.id)
    assert len(ds) == 1
    assert ds[0]["tool_name"] == "image.ltt" and ds[0]["credit"] == 12


def test_phieu_gan_dung_vao_HANG_step_that(db):
    """🔴 `step_id` phải là id hàng `chatltt_step` thật, không phải một chuỗi
    bịa. Nếu không, `UNIQUE(step_id)` bảo vệ một thứ không tồn tại."""
    from apps.chatltt.tables import ChatlttApproval, ChatlttStep
    r, _run, _ = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    p = db.query(ChatlttApproval).one()
    st = db.get(ChatlttStep, p.step_id)
    assert st is not None
    assert st.run_id == r.id and st.tool_name == "image.ltt"
    assert st.trang_thai == "cho_duyet", "cho_duyet KHONG duoc gop vao 'ok'"


def test_phieu_da_COMMIT_truoc_khi_run_tra_ve(db):
    """⛔ Phát `approval.required` cho một hàng chưa commit là mời người dùng
    bấm vào một thứ có thể biến mất. Kiểm bằng một **phiên CSDL khác**."""
    r, _run, _ = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    from platform_core.db import get_session
    gen = get_session()
    db2 = next(gen)
    try:
        assert len(D.dang_cho(db2, user_id=U, run_id=r.id)) == 1
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_dong_y_thi_tool_chay_va_run_ket_thuc(db, _mo_cong):
    r, run, ct = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    ap = D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"]
    D.duyet(db, user_id=U, approval_id=ap)

    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS)
    run2 = DP.tiep_tuc(run, ket_qua_duyet=kq, goi_model=_model(_chu("day la anh")),
                       chay_tool=ct, ghi=lambda b: LR.ghi_buoc(db, r, b))
    assert run2.trang_thai == DP.COMPLETED and run2.ly_do_ket == DP.KET_XONG
    assert len(_mo_cong) == 1, "tool phai chay DUNG MOT lan"
    assert run2.van_ban_cuoi == "day la anh"


def test_SUA_doi_so_thi_tool_chay_ban_DA_SUA(db, _mo_cong):
    """🔴 Mệnh đề đắt nhất của cả P04. Chạy bản gốc sau khi người dùng đã sửa
    là chạy một việc **không ai duyệt** — và ở đây `so_luong` là số nhân giá."""
    r, run, ct = _bat_dau(db, model=_model(
        _goi(("image.ltt", '{"prompt":"meo","so_luong":4}'))))
    ap = D.dang_cho(db, user_id=U, run_id=r.id)[0]
    assert ap["credit"] == 48, "bao gia phai theo doi so model DE NGHI"

    D.duyet(db, user_id=U, approval_id=ap["approval_id"],
            doi_so_da_sua={"prompt": "meo", "so_luong": 1})
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS)
    DP.tiep_tuc(run, ket_qua_duyet=kq, goi_model=_model(_chu("xong")), chay_tool=ct)

    assert _mo_cong == [{"prompt": "meo", "so_luong": 1}], "phai chay BAN DA SUA"


def test_ket_qua_tool_di_vao_lich_su_cho_model(db):
    r, run, ct = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])
    thay = {}

    def gm(messages, tools):
        thay["ls"] = list(messages)
        return _chu("ok")

    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS)
    DP.tiep_tuc(run, ket_qua_duyet=kq, goi_model=gm, chay_tool=ct)
    assert "anh/1.png" in thay["ls"][-1]["content"]


# ── 2. Đường từ chối ───────────────────────────────────────────────────────

def test_TU_CHOI_thi_tool_KHONG_chay_va_run_van_ket_tu_te(db, _mo_cong):
    r, run, ct = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    D.tu_choi(db, user_id=U,
              approval_id=D.dang_cho(db, user_id=U, run_id=r.id)[0]["approval_id"])

    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS)
    run2 = DP.tiep_tuc(run, ket_qua_duyet=kq, chay_tool=ct,
                       goi_model=_model(_chu("ban da tu choi, toi ta bang loi vay")))
    assert _mo_cong == [], "TU CHOI ma tool van chay la loi nang nhat co the"
    assert run2.trang_thai == DP.COMPLETED
    assert run2.ly_do_ket == DP.KET_XONG, "tu choi KHONG phai mot loi"


def test_HET_HAN_cung_khong_chay_tool(db, _mo_cong):
    from datetime import datetime, timedelta, timezone

    from apps.chatltt.tables import ChatlttApproval
    r, run, ct = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    p = db.query(ChatlttApproval).one()
    p.created_at = datetime.now(timezone.utc) - timedelta(minutes=D.HAN_CHO_PHUT + 1)
    D.quet_het_han(db)

    kq = B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS)
    DP.tiep_tuc(run, ket_qua_duyet=kq, chay_tool=ct,
                goi_model=_model(_chu("de nghi da het han")))
    assert _mo_cong == []


def test_CHUA_quyet_thi_khong_co_ket_qua_va_tiep_tuc_NEM(db):
    """⛔ Chạy tiếp khi người dùng chưa trả lời là chạy một việc không ai duyệt.
    `ket_qua_sau_duyet` trả rỗng, và `tiep_tuc` ném vì thiếu — hai lớp."""
    _r, run, ct = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    assert B.ket_qua_sau_duyet(db, user_id=U, run=run, khoi_tools=TOOLS) == {}
    with pytest.raises(ValueError, match="thieu ket qua duyet"):
        DP.tiep_tuc(run, ket_qua_duyet={}, goi_model=_model(_chu("x")), chay_tool=ct)


def test_phieu_cua_NGUOI_KHAC_khong_duoc_dung_de_chay(db, _mo_cong):
    """🔴 `ket_qua_sau_duyet` tra phiếu **kèm `user_id`**. Không thì một
    `approval_id` đoán được là một đường chạy tool bằng tiền người khác."""
    _r, run, _ct = _bat_dau(db, model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))))
    assert B.ket_qua_sau_duyet(db, user_id="u-nguoi-la", run=run,
                               khoi_tools=TOOLS) == {}


# ── 3. Fail-closed quanh báo giá ───────────────────────────────────────────

def test_KHONG_bao_gia_duoc_thi_KHONG_mo_phieu(db):
    """⛔ Một thẻ duyệt ghi "đồng ý tiêu 0 credit" tệ hơn không có thẻ duyệt."""
    from apps.chatltt.tables import ChatlttApproval
    _r, run, _ = _bat_dau(db, bao_gia=None,
                          model=_model(_goi(("image.ltt", '{"prompt":"meo"}')),
                                       _chu("khong dung duoc tool do")))
    assert db.query(ChatlttApproval).count() == 0
    assert run.trang_thai == DP.COMPLETED, "khong treo — model nhan loi va noi tiep"
    b = [x for x in run.buoc if x.loai == "tool"][0]
    assert b.ket_qua.ma_loi == "khong_bao_gia_duoc"


def test_bao_gia_NEM_thi_thanh_du_lieu_cho_model_khong_giet_run(db):
    def hong(ten, ds):
        raise RuntimeError("bang gia chua nap")

    _r, run, _ = _bat_dau(db, bao_gia=hong,
                          model=_model(_goi(("image.ltt", '{"prompt":"meo"}')),
                                       _chu("thu cach khac")))
    b = [x for x in run.buoc if x.loai == "tool"][0]
    assert b.ket_qua.ma_loi == "bao_gia_hong"
    assert "RuntimeError" in b.ket_qua.thong_diep, "khong duoc nuot kieu ngoai le"
    assert run.trang_thai == DP.COMPLETED


def test_doi_so_SAI_HOP_DONG_bi_chan_TRUOC_khi_mo_phieu(db):
    """Hỏi người dùng có đồng ý chạy một lời gọi chắc chắn hỏng là bắt họ đọc
    một thứ vô nghĩa — và tính công cho một quyết định không đáng có."""
    from apps.chatltt.tables import ChatlttApproval
    _r, run, _ = _bat_dau(db, model=_model(_goi(("image.ltt", '{"so_luong":2}')),
                                           _chu("thieu prompt")))
    assert db.query(ChatlttApproval).count() == 0
    b = [x for x in run.buoc if x.loai == "tool"][0]
    assert b.ket_qua.ma_loi == T.LOI_DOI_SO


def test_co_TU_CHAY_TOOL_CO_PHI_bat_thi_khong_hoi(db, _mo_cong):
    """⭐ Đường thứ hai, và nó phải đi được — nhưng chỉ khi cờ RIÊNG bật."""
    from apps.chatltt.tables import ChatlttApproval
    _r, run, _ = _bat_dau(db, co_phi=True,
                          model=_model(_goi(("image.ltt", '{"prompt":"meo"}')),
                                       _chu("xong")))
    assert db.query(ChatlttApproval).count() == 0
    assert run.trang_thai == DP.COMPLETED
    assert len(_mo_cong) == 1


# ── 4. Tool miễn phí không đi qua đường duyệt ──────────────────────────────

def test_tool_MIEN_PHI_chay_thang_khong_hoi(db):
    from apps.chatltt.tables import ChatlttApproval
    _r, run, _ = _bat_dau(db, model=_model(_goi(("noi_bo.tinh", '{"bieu_thuc":"2+2"}')),
                                           _chu("bang 4")))
    assert db.query(ChatlttApproval).count() == 0
    assert run.trang_thai == DP.COMPLETED
    b = [x for x in run.buoc if x.loai == "tool"][0]
    assert b.ket_qua.ok and b.ket_qua.noi_dung["ket_qua"] == 4


def test_MOT_mien_phi_MOT_co_phi_trong_cung_mot_luot(db):
    """Lời gọi song song trộn hai lớp: cái miễn phí chạy xong, cái có phí treo."""
    _r, run, _ = _bat_dau(db, model=_model(_goi(("noi_bo.tinh", '{"bieu_thuc":"6*7"}'),
                                               ("image.ltt", '{"prompt":"meo"}'))))
    tool_buoc = [b for b in run.buoc if b.loai == "tool"]
    assert tool_buoc[0].ket_qua.noi_dung["ket_qua"] == 42
    assert tool_buoc[1].cho_duyet and tool_buoc[1].ket_qua is None
    assert run.trang_thai == DP.AWAITING_APPROVAL


# ── 5. Sổ handler sạch sau khi chạy ────────────────────────────────────────

def test_so_handler_KHONG_con_rac_sau_tep_nay(db):
    """⛔ `monkeypatch.setitem` phải gỡ handler giả khi tệp kết thúc. Một handler
    giả sót lại làm mọi tệp chạy sau thấy một `image.ltt` chạy được — và đó là
    kiểu lỗi chỉ hiện ra trong gate, không hiện khi chạy riêng."""
    assert T.da_cai("noi_bo.tinh"), "tool that phai con"
