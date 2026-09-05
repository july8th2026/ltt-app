"""
test_814 — dựng lại một `Run` từ CSDL. (H44 P04, bước cuối)

"Duyệt bền" chỉ đúng nếu cái đang chờ duyệt cũng sống qua một lần khởi động
lại dịch vụ. Một `Run` giữ trong RAM giữa hai yêu cầu HTTP là một `Run` biến
mất khi worker bị thay — và người dùng bấm "đồng ý" vào hư không.

## Mệnh đề trung tâm: DỰNG LẠI == BẢN GỐC

`LR.dung_lai` không thêm cột nào; nó đọc `chatltt_step` + đường hội thoại rồi
dựng lại. Nên phép kiểm mạnh nhất có thể viết là so **từng byte** lịch sử dựng
lại với lịch sử bản gốc còn trong bộ nhớ.

⭐ Nếu chúng khác nhau thì thứ đang thiếu là một cột **thật sự cần**, chứ không
   phải một tiện tay — và phép kiểm này là chỗ nói ra điều đó.

## Và một cái bẫy riêng: bộ đếm trùng

🔴 Trần "gọi trùng 2 lần" đếm theo `bam_trung`. Không dựng lại bộ đếm ấy thì mỗi
lần chờ duyệt là một lần **xoá sạch** nó — và một model kẹt vòng lặp chỉ cần xin
duyệt một lần là thoát trần, mãi mãi.
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
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    yield
    dbmod.reset_engine()


def _phien():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _dong(gen):
    try:
        next(gen)
    except StopIteration:
        pass


@pytest.fixture()
def db(moi_truong):
    gen, s = _phien()
    yield s
    _dong(gen)


U = "u-chu"
GOC = [{"role": "user", "content": "ve con meo va tinh 2+2"}]

TOOLS = [
    {"type": "function", "function": {
        "name": "image.ltt", "description": "ve mot buc anh",
        "parameters": {"type": "object",
                       "properties": {"prompt": {"type": "string"}},
                       "required": ["prompt"]}}},
    {"type": "function", "function": {
        "name": "noi_bo.tinh", "description": "tinh mot bieu thuc",
        "parameters": {"type": "object",
                       "properties": {"bieu_thuc": {"type": "string"}},
                       "required": ["bieu_thuc"]}}},
]


@pytest.fixture(autouse=True)
def _mo_cong(monkeypatch):
    monkeypatch.setattr(C, "CHO_MODEL_GOI", ("image.ltt", "noi_bo.tinh"))
    monkeypatch.setitem(T._SO_HANDLER, "image.ltt",
                        lambda db, uid, ds: {"url": "anh/1.png"})


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


def _gia(ten, ds):
    return (12, "ltt-vlm-2026-08-22")


def _chay_toi_khi_cho_duyet(db, model=None):
    """Chạy một lượt tới lúc dừng chờ duyệt. Trả `(run_row_id, run_goc)`."""
    r = LR.mo_run(db, user_id=U, conv_id="c-1", message_id="m-1")
    db.commit()
    ct = B.tao(db, user_id=U, run_id=r.id, khoi_tools=TOOLS, bao_gia=_gia)
    run = DP.chay(messages=list(GOC), tools=TOOLS,
                  goi_model=model or _model(_goi(("noi_bo.tinh", '{"bieu_thuc":"2+2"}'),
                                                 ("image.ltt", '{"prompt":"meo"}'))),
                  chay_tool=ct, ghi=lambda b: LR.ghi_buoc(db, r, b))
    LR.dong_run(db, r, run)
    db.commit()
    assert run.trang_thai == DP.AWAITING_APPROVAL
    return r.id, run


# ── 1. Dựng lại == bản gốc ─────────────────────────────────────────────────

def test_LICH_SU_dung_lai_GIONG_HET_ban_goc(db):
    """🔴 Mệnh đề trung tâm. Khác một byte nghĩa là có thứ chỉ sống trong RAM —
    và thứ đó sẽ mất khi dịch vụ khởi động lại."""
    run_id, goc = _chay_toi_khi_cho_duyet(db)
    from apps.chatltt.tables import ChatlttRun
    lai = LR.dung_lai(db, user_id=U, run_row=db.get(ChatlttRun, run_id),
                      messages_goc=list(GOC), tools=TOOLS)
    assert lai.lich_su == goc.lich_su


def test_BUOC_dung_lai_khop_ban_goc(db):
    run_id, goc = _chay_toi_khi_cho_duyet(db)
    from apps.chatltt.tables import ChatlttRun
    lai = LR.dung_lai(db, user_id=U, run_row=db.get(ChatlttRun, run_id),
                      messages_goc=list(GOC), tools=TOOLS)
    assert [(b.thu_tu, b.loai, b.ten) for b in lai.buoc] == \
           [(b.thu_tu, b.loai, b.ten) for b in goc.buoc]
    assert [b.doi_so_tho for b in lai.buoc] == [b.doi_so_tho for b in goc.buoc]


def test_buoc_TREO_giu_dung_approval_id(db):
    run_id, goc = _chay_toi_khi_cho_duyet(db)
    from apps.chatltt.tables import ChatlttRun
    lai = LR.dung_lai(db, user_id=U, run_row=db.get(ChatlttRun, run_id),
                      messages_goc=list(GOC), tools=TOOLS)
    assert [b.cho_duyet for b in lai.dang_cho_duyet()] == \
           [b.cho_duyet for b in goc.dang_cho_duyet()]
    assert lai.dang_cho_duyet()[0].cho_duyet.startswith("ap_")


def test_so_dem_giu_nguyen(db):
    run_id, goc = _chay_toi_khi_cho_duyet(db)
    from apps.chatltt.tables import ChatlttRun
    lai = LR.dung_lai(db, user_id=U, run_row=db.get(ChatlttRun, run_id),
                      messages_goc=list(GOC), tools=TOOLS)
    assert (lai.so_vong_model, lai.so_loi_goi_tool) == \
           (goc.so_vong_model, goc.so_loi_goi_tool)
    assert lai.trang_thai == DP.AWAITING_APPROVAL


def test_BO_DEM_TRUNG_song_sot_qua_lan_dung_lai(db):
    """🔴 Không dựng lại `_dem_bam` thì mỗi lần chờ duyệt là một lần xoá sạch
    nó — và một model kẹt vòng lặp chỉ cần xin duyệt một lần là thoát trần."""
    run_id, goc = _chay_toi_khi_cho_duyet(db)
    from apps.chatltt.tables import ChatlttRun
    lai = LR.dung_lai(db, user_id=U, run_row=db.get(ChatlttRun, run_id),
                      messages_goc=list(GOC), tools=TOOLS)
    assert lai._dem_bam == goc._dem_bam
    assert sum(lai._dem_bam.values()) == 2, "hai loi goi tool"


# ── 2. Sống qua một PHIÊN CSDL MỚI ─────────────────────────────────────────

def test_dung_lai_duoc_tu_mot_PHIEN_HOAN_TOAN_MOI(db):
    """⭐ Đây là thứ mô phỏng "dịch vụ khởi động lại": một phiên CSDL khác, không
    một đối tượng Python nào chung với lượt đã chạy."""
    run_id, goc = _chay_toi_khi_cho_duyet(db)
    gen2, db2 = _phien()
    try:
        from apps.chatltt.tables import ChatlttRun
        lai = LR.dung_lai(db2, user_id=U, run_row=db2.get(ChatlttRun, run_id),
                          messages_goc=list(GOC), tools=TOOLS)
        assert lai.lich_su == goc.lich_su
        assert len(lai.dang_cho_duyet()) == 1
    finally:
        _dong(gen2)


def test_nguoi_KHAC_dung_lai_ra_run_RONG(db):
    """`dung_lai` truy vấn `chatltt_step` kèm `user_id`. Không thì một `run_id`
    đoán được là một đường đọc cả lịch sử tool của người khác."""
    run_id, _goc = _chay_toi_khi_cho_duyet(db)
    from apps.chatltt.tables import ChatlttRun
    lai = LR.dung_lai(db, user_id="u-nguoi-la", run_row=db.get(ChatlttRun, run_id),
                      messages_goc=list(GOC), tools=TOOLS)
    assert lai.buoc == [] and lai.lich_su == GOC


# ── 3. Chạy tiếp từ bản dựng lại ───────────────────────────────────────────

def test_duyet_roi_CHAY_TIEP_tu_ban_dung_lai(db):
    run_id, _goc = _chay_toi_khi_cho_duyet(db)
    ap = D.dang_cho(db, user_id=U, run_id=run_id)[0]["approval_id"]
    D.duyet(db, user_id=U, approval_id=ap)
    db.commit()

    gen2, db2 = _phien()
    try:
        from apps.chatltt.tables import ChatlttRun
        r2 = db2.get(ChatlttRun, run_id)
        lai = LR.dung_lai(db2, user_id=U, run_row=r2, messages_goc=list(GOC),
                          tools=TOOLS)
        kq = B.ket_qua_sau_duyet(db2, user_id=U, run=lai, khoi_tools=TOOLS)
        ct = B.tao(db2, user_id=U, run_id=run_id, khoi_tools=TOOLS, bao_gia=_gia)
        xong = DP.tiep_tuc(lai, ket_qua_duyet=kq, chay_tool=ct,
                           goi_model=_model(_chu("day la anh, va 2+2=4")),
                           ghi=lambda b: LR.ghi_buoc(db2, r2, b))
        assert xong.trang_thai == DP.COMPLETED
        assert xong.ly_do_ket == DP.KET_XONG
        assert xong.van_ban_cuoi == "day la anh, va 2+2=4"
    finally:
        _dong(gen2)


def test_chay_tiep_ghi_ket_qua_DE_LEN_dung_hang_step(db):
    """⛔ `ghi_buoc` lần hai phải CẬP NHẬT. Chèn mới thì mỗi bước thành hai hàng
    và `ux_chatltt_step_thu_tu` ném — ở tận lúc commit, sau khi tool đã chạy."""
    from apps.chatltt.tables import ChatlttRun, ChatlttStep
    run_id, _ = _chay_toi_khi_cho_duyet(db)
    truoc = db.query(ChatlttStep).filter_by(run_id=run_id).count()
    ap = D.dang_cho(db, user_id=U, run_id=run_id)[0]["approval_id"]
    D.duyet(db, user_id=U, approval_id=ap)

    r = db.get(ChatlttRun, run_id)
    lai = LR.dung_lai(db, user_id=U, run_row=r, messages_goc=list(GOC), tools=TOOLS)
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=lai, khoi_tools=TOOLS)
    DP.tiep_tuc(lai, ket_qua_duyet=kq, goi_model=_model(_chu("xong")),
                chay_tool=B.tao(db, user_id=U, run_id=run_id, khoi_tools=TOOLS,
                                bao_gia=_gia),
                ghi=lambda b: LR.ghi_buoc(db, r, b))
    db.commit()
    sau = db.query(ChatlttStep).filter_by(run_id=run_id).count()
    assert sau == truoc + 1, "chi THEM mot buoc model cua vong cuoi"
    treo = db.query(ChatlttStep).filter_by(run_id=run_id,
                                           trang_thai="cho_duyet").count()
    assert treo == 0, "buoc treo phai da co ket qua"


def test_TU_CHOI_roi_chay_tiep_tu_ban_dung_lai(db):
    run_id, _ = _chay_toi_khi_cho_duyet(db)
    D.tu_choi(db, user_id=U,
              approval_id=D.dang_cho(db, user_id=U, run_id=run_id)[0]["approval_id"])
    from apps.chatltt.tables import ChatlttRun
    r = db.get(ChatlttRun, run_id)
    lai = LR.dung_lai(db, user_id=U, run_row=r, messages_goc=list(GOC), tools=TOOLS)
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=lai, khoi_tools=TOOLS)
    thay = {}

    def gm(messages, tools):
        thay["ls"] = list(messages)
        return _chu("ban da tu choi")

    xong = DP.tiep_tuc(lai, ket_qua_duyet=kq, goi_model=gm,
                       chay_tool=B.tao(db, user_id=U, run_id=run_id,
                                       khoi_tools=TOOLS, bao_gia=_gia))
    assert xong.trang_thai == DP.COMPLETED
    assert "TU CHOI" in str(thay["ls"][-1]["content"])


def test_CHUA_quyet_thi_chay_tiep_NEM(db):
    run_id, _ = _chay_toi_khi_cho_duyet(db)
    from apps.chatltt.tables import ChatlttRun
    r = db.get(ChatlttRun, run_id)
    lai = LR.dung_lai(db, user_id=U, run_row=r, messages_goc=list(GOC), tools=TOOLS)
    kq = B.ket_qua_sau_duyet(db, user_id=U, run=lai, khoi_tools=TOOLS)
    assert kq == {}
    with pytest.raises(ValueError, match="thieu ket qua duyet"):
        DP.tiep_tuc(lai, ket_qua_duyet=kq, goi_model=_model(_chu("x")),
                    chay_tool=B.tao(db, user_id=U, run_id=run_id,
                                    khoi_tools=TOOLS, bao_gia=_gia))


# ── 4. Khi nào ĐƯỢC chạy tiếp ──────────────────────────────────────────────

def test_nen_chay_tiep_dung_khi_da_bam_het(db):
    from apps.chatltt.services import luot_v3 as V3
    run_id, _ = _chay_toi_khi_cho_duyet(db)
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_id) is False, "con phieu cho"
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=run_id)[0]["approval_id"])
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_id) is True


def test_con_MOT_phieu_chua_bam_thi_CHUA_chay_tiep(db):
    """🔴 Một lượt có hai lời gọi có phí thì có hai phiếu. Chạy tiếp khi mới một
    phiếu được bấm là chạy một việc người dùng chưa nhìn tới."""
    from apps.chatltt.services import luot_v3 as V3
    run_id, _ = _chay_toi_khi_cho_duyet(db, model=_model(
        _goi(("image.ltt", '{"prompt":"meo"}'), ("image.ltt", '{"prompt":"cho"}'))))
    ds = D.dang_cho(db, user_id=U, run_id=run_id)
    assert len(ds) == 2
    D.duyet(db, user_id=U, approval_id=ds[0]["approval_id"])
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_id) is False
    D.tu_choi(db, user_id=U, approval_id=ds[1]["approval_id"])
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_id) is True


def test_nguoi_khac_khong_khoi_dong_lai_duoc_run_cua_toi(db):
    from apps.chatltt.services import luot_v3 as V3
    run_id, _ = _chay_toi_khi_cho_duyet(db)
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=run_id)[0]["approval_id"])
    assert V3.nen_chay_tiep(db, user_id="u-nguoi-la", run_id=run_id) is False


def test_run_DA_XONG_khong_chay_tiep_duoc(db):
    """⛔ Một run đã `COMPLETED` mà chạy lại được là một run có thể tính tiền
    hai lần."""
    from apps.chatltt.services import luot_v3 as V3
    from apps.chatltt.tables import ChatlttRun
    run_id, _ = _chay_toi_khi_cho_duyet(db)
    D.duyet(db, user_id=U,
            approval_id=D.dang_cho(db, user_id=U, run_id=run_id)[0]["approval_id"])
    db.get(ChatlttRun, run_id).trang_thai = DP.COMPLETED
    db.flush()
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_id) is False


def test_phieu_HET_HAN_khong_chan_viec_chay_tiep(db):
    """Hết hạn là một quyết định (`het_han`), không phải "vẫn đang chờ". Coi nó
    là đang chờ thì run kẹt vĩnh viễn — không ai bấm được nữa."""
    from datetime import datetime, timedelta, timezone

    from apps.chatltt.services import luot_v3 as V3
    from apps.chatltt.tables import ChatlttApproval
    run_id, _ = _chay_toi_khi_cho_duyet(db)
    for p in db.query(ChatlttApproval).all():
        p.created_at = datetime.now(timezone.utc) - timedelta(
            minutes=D.HAN_CHO_PHUT + 1)
    db.flush()
    assert V3.nen_chay_tiep(db, user_id=U, run_id=run_id) is True
