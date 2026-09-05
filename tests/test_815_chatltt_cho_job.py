"""
test_815 — run DỪNG chờ một job nền rồi CHẠY TIẾP. (H44 P05)

`ChoJob` là anh em của `CanDuyet`: hai lý do dừng khác nhau — chờ **người** và
chờ **máy** — nhưng cùng một cơ chế. Tệp này kiểm rằng chúng thật sự cùng cơ
chế, và kiểm hai chỗ chúng **phải** khác nhau:

  1. Lối ra khác nhau. `AWAITING_APPROVAL → TOOL_RUNNING → TOOL_RESULT_READY`,
     còn `WAITING_BACKGROUND → TOOL_RESULT_READY` thẳng. Quay lại "đang chạy"
     sau khi job đã xong là nói sai về thứ vừa xảy ra.
  2. Một lô vừa chờ người vừa chờ máy đứng ở `AWAITING_APPROVAL` — trạng thái
     cần **người** làm gì đó, và việc nó hiện ra quan trọng hơn.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import thi_hanh


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


def _ok(noi="xong"):
    return thi_hanh.KetQua(ok=True, noi_dung=noi)


def _dung_cho_job(chay_tool=None, model=None, **kw):
    return DP.chay(
        messages=[{"role": "user", "content": "ve con meo"}], tools=[],
        goi_model=model or _model(_goi(("image.ltt", '{"prompt":"meo"}'))),
        chay_tool=chay_tool or (lambda t, d, c: DP.ChoJob(job_id="job_1")), **kw)


# ── 1. Dừng ────────────────────────────────────────────────────────────────

def test_ChoJob_dua_run_vao_WAITING_BACKGROUND():
    run = _dung_cho_job()
    assert run.trang_thai == DP.WAITING_BACKGROUND
    assert run.xong() is False
    assert run.ly_do_ket == ""


def test_buoc_giu_job_id_va_chua_co_ket_qua():
    run = _dung_cho_job()
    b = run.dang_cho_job()[0]
    assert b.cho_job == "job_1" and b.ket_qua is None
    assert b.cho_duyet == "", "cho_job va cho_duyet la HAI truong khac nhau"


def test_phat_su_kien_task_queued():
    """Người dùng phải thấy "đang tạo ảnh", không phải một khoảng im lặng."""
    sk = []
    _dung_cho_job(phat=sk.append)
    q = [x for x in sk if x.get("type") == "task.queued"]
    assert len(q) == 1 and q[0]["job_id"] == "job_1"


def test_KHONG_phat_run_completed_khi_moi_dung_cho_job():
    sk = []
    _dung_cho_job(phat=sk.append)
    assert not [x for x in sk if x.get("type") in ("run.completed", "run.failed")]


def test_buoc_duoc_ghi_TRUOC_khi_goi_tool_va_ghi_lai_khi_co_job_id():
    da_ghi = []

    def tool(t, d, c):
        assert [b for b in da_ghi if b.loai == "tool"], "phai ghi TRUOC khi nop job"
        return DP.ChoJob(job_id="job_1")

    _dung_cho_job(chay_tool=tool, ghi=da_ghi.append)
    tool_ghi = [b for b in da_ghi if b.loai == "tool"]
    assert len(tool_ghi) == 2 and tool_ghi[0] is tool_ghi[1]
    assert tool_ghi[0].cho_job == "job_1"


# ── 2. Chạy tiếp ───────────────────────────────────────────────────────────

def test_job_xong_thi_chay_tiep_va_ket_thuc():
    run = _dung_cho_job(model=_model(_goi(("image.ltt", '{"prompt":"meo"}')),
                                     _chu("day la anh")))
    run2 = DP.tiep_tuc(run, ket_qua_duyet={"job_1": _ok("anh/1.png")},
                       goi_model=_model(_chu("day la anh")),
                       chay_tool=lambda t, d, c: _ok())
    assert run2.trang_thai == DP.COMPLETED and run2.ly_do_ket == DP.KET_XONG


def test_LOI_RA_cua_WAITING_BACKGROUND_khong_qua_TOOL_RUNNING():
    """🔴 `WAITING_BACKGROUND → TOOL_RUNNING` **không** có trong `CHUYEN_HOP_LE`.

    Nếu `tiep_tuc` đi qua đó thì `chuyen()` ném — và phép kiểm này đỏ. Đó là
    cách một bảng chuyển đổi cưỡng chế được một mệnh đề về nghĩa: job đã chạy
    xong rồi, quay lại "đang chạy" là nói sai về thứ vừa xảy ra.
    """
    assert DP.TOOL_RUNNING not in DP.CHUYEN_HOP_LE[DP.WAITING_BACKGROUND]
    run = _dung_cho_job()
    DP.tiep_tuc(run, ket_qua_duyet={"job_1": _ok()},
                goi_model=_model(_chu("ok")), chay_tool=lambda t, d, c: _ok())


def test_ket_qua_job_di_vao_lich_su():
    run = _dung_cho_job()
    thay = {}

    def gm(messages, tools):
        thay["ls"] = list(messages)
        return _chu("ok")

    DP.tiep_tuc(run, ket_qua_duyet={"job_1": _ok("anh/1.png")}, goi_model=gm,
                chay_tool=lambda t, d, c: _ok())
    assert thay["ls"][-1]["role"] == "tool"
    assert "anh/1.png" in thay["ls"][-1]["content"]


def test_job_HONG_la_du_lieu_khong_giet_run():
    """Job hỏng là một kết quả model đọc được, không phải một lượt chết."""
    run = _dung_cho_job()
    hong = thi_hanh.KetQua(False, ma_loi="job_that_bai",
                           thong_diep="may B het VRAM")
    run2 = DP.tiep_tuc(run, ket_qua_duyet={"job_1": hong},
                       goi_model=_model(_chu("khong ve duoc, toi ta bang loi")),
                       chay_tool=lambda t, d, c: _ok())
    assert run2.trang_thai == DP.COMPLETED and run2.ly_do_ket == DP.KET_XONG


def test_THIEU_ket_qua_job_thi_NEM():
    run = _dung_cho_job()
    with pytest.raises(ValueError, match="thieu ket qua duyet"):
        DP.tiep_tuc(run, ket_qua_duyet={}, goi_model=_model(_chu("x")),
                    chay_tool=lambda t, d, c: _ok())


# ── 3. Trộn hai kiểu chờ ───────────────────────────────────────────────────

def test_vua_cho_NGUOI_vua_cho_MAY_thi_dung_o_AWAITING_APPROVAL():
    """⭐ Trạng thái cần **người** làm gì đó phải là trạng thái hiện ra: một job
    tự xong, một phiếu duyệt thì không."""
    def tool(ten, ds, c):
        return (DP.CanDuyet(approval_id="ap_1") if ten == "speech.ltt"
                else DP.ChoJob(job_id="job_1"))

    run = DP.chay(messages=[], tools=[],
                  goi_model=_model(_goi(("image.ltt", "{}"), ("speech.ltt", "{}"))),
                  chay_tool=tool)
    assert run.trang_thai == DP.AWAITING_APPROVAL
    assert len(run.dang_cho_job()) == 1 and len(run.dang_cho_duyet()) == 1
    assert len(run.dang_treo()) == 2


def test_tiep_tuc_doi_DU_ca_hai_kieu():
    """⛔ `dang_treo()` là MỘT danh sách, không hai. Tách đôi là để một lần quên
    kiểm danh sách thứ hai biến một lời gọi tool thành im lặng."""
    def tool(ten, ds, c):
        return (DP.CanDuyet(approval_id="ap_1") if ten == "speech.ltt"
                else DP.ChoJob(job_id="job_1"))

    run = DP.chay(messages=[], tools=[],
                  goi_model=_model(_goi(("image.ltt", "{}"), ("speech.ltt", "{}"))),
                  chay_tool=tool)
    with pytest.raises(ValueError, match="thieu ket qua"):
        DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok()},
                    goi_model=_model(_chu("x")), chay_tool=tool)

    xong = DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok("tieng"), "job_1": _ok("anh")},
                       goi_model=_model(_chu("xong ca hai")),
                       chay_tool=lambda t, d, c: _ok())
    assert xong.trang_thai == DP.COMPLETED


def test_dung_hai_lan_bang_hai_LY_DO_khac_nhau():
    """Một lượt thật có thể chờ duyệt ở vòng 1 rồi chờ job ở vòng 2."""
    lan = {"n": 0}

    def tool(ten, ds, c):
        lan["n"] += 1
        return (DP.CanDuyet(approval_id="ap_1") if lan["n"] == 1
                else DP.ChoJob(job_id="job_2"))

    run = DP.chay(messages=[], tools=[],
                  goi_model=_model(_goi(("image.ltt", "{}"))), chay_tool=tool)
    assert run.trang_thai == DP.AWAITING_APPROVAL

    run = DP.tiep_tuc(run, ket_qua_duyet={"ap_1": _ok("anh")}, chay_tool=tool,
                      goi_model=_model(_goi(("speech.ltt", "{}"))))
    assert run.trang_thai == DP.WAITING_BACKGROUND

    run = DP.tiep_tuc(run, ket_qua_duyet={"job_2": _ok("tieng")},
                      goi_model=_model(_chu("xong ca hai")),
                      chay_tool=lambda t, d, c: _ok())
    assert run.trang_thai == DP.COMPLETED
    assert len([b for b in run.buoc if b.loai == "tool"]) == 2


# ── 4. Bảng chuyển đổi vẫn cưỡng chế ───────────────────────────────────────

def test_CHO_DUOC_dung_hai_trang_thai():
    assert DP.CHO_DUOC == {DP.AWAITING_APPROVAL, DP.WAITING_BACKGROUND}


@pytest.mark.parametrize("tt", ["CREATED", "MODEL_RUNNING", "TOOL_REQUESTED",
                                "TOOL_RUNNING", "TOOL_RESULT_READY",
                                "MODEL_RESUMING", "WAITING_SLOT",
                                "COMPLETED", "FAILED", "CANCELLED"])
def test_tiep_tuc_tu_trang_thai_KHAC_deu_nem(tt):
    run = DP.Run(trang_thai=tt)
    with pytest.raises(DP.ChuyenTrangThaiSai):
        DP.tiep_tuc(run, ket_qua_duyet={}, goi_model=_model(_chu("x")),
                    chay_tool=lambda t, d, c: _ok())


# ── 5. Bước chờ job sống sót qua CSDL ──────────────────────────────────────

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
GOC = [{"role": "user", "content": "ve con meo"}]


def test_buoc_cho_job_ghi_dung_trang_thai_va_job_id(db):
    from apps.chatltt.services import luu_run as LR
    from apps.chatltt.tables import ChatlttStep
    r = LR.mo_run(db, user_id=U, conv_id="c-1", message_id="m-1")
    _dung_cho_job(ghi=lambda b: LR.ghi_buoc(db, r, b))
    st = db.query(ChatlttStep).filter_by(loai="tool").one()
    assert st.trang_thai == "cho_job", "cho_job KHONG duoc gop vao cho_duyet hay ok"
    assert st.job_id == "job_1"


def test_run_cho_job_DUNG_LAI_duoc_tu_CSDL(db):
    """⭐ Cùng cơ chế với chờ duyệt, nên cùng phải sống qua một lần khởi động
    lại. Một run kẹt ở `WAITING_BACKGROUND` mà không dựng lại được là một job
    chạy xong rồi không ai nhặt kết quả."""
    from apps.chatltt.services import luu_run as LR
    from apps.chatltt.tables import ChatlttRun
    r = LR.mo_run(db, user_id=U, conv_id="c-1", message_id="m-1")
    db.commit()
    goc = DP.chay(messages=list(GOC), tools=[],
                  goi_model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))),
                  chay_tool=lambda t, d, c: DP.ChoJob(job_id="job_1"),
                  ghi=lambda b: LR.ghi_buoc(db, r, b))
    LR.dong_run(db, r, goc)
    db.commit()

    lai = LR.dung_lai(db, user_id=U, run_row=db.get(ChatlttRun, r.id),
                      messages_goc=list(GOC), tools=[])
    assert lai.trang_thai == DP.WAITING_BACKGROUND
    assert lai.lich_su == goc.lich_su
    assert [b.cho_job for b in lai.dang_cho_job()] == ["job_1"]
    assert lai.dang_cho_duyet() == [], "job KHONG duoc lan sang danh sach cho duyet"


def test_dung_lai_roi_chay_tiep_bang_ket_qua_job(db):
    from apps.chatltt.services import luu_run as LR
    from apps.chatltt.tables import ChatlttRun
    r = LR.mo_run(db, user_id=U, conv_id="c-1", message_id="m-1")
    db.commit()
    DP.chay(messages=list(GOC), tools=[],
            goi_model=_model(_goi(("image.ltt", '{"prompt":"meo"}'))),
            chay_tool=lambda t, d, c: DP.ChoJob(job_id="job_1"),
            ghi=lambda b: LR.ghi_buoc(db, r, b))
    LR.dong_run(db, r, DP.Run(trang_thai=DP.WAITING_BACKGROUND))
    db.commit()

    r2 = db.get(ChatlttRun, r.id)
    lai = LR.dung_lai(db, user_id=U, run_row=r2, messages_goc=list(GOC), tools=[])
    xong = DP.tiep_tuc(lai, ket_qua_duyet={"job_1": _ok("anh/1.png")},
                       goi_model=_model(_chu("day la anh")),
                       chay_tool=lambda t, d, c: _ok(),
                       ghi=lambda b: LR.ghi_buoc(db, r2, b))
    assert xong.trang_thai == DP.COMPLETED
    db.commit()
    from apps.chatltt.tables import ChatlttStep
    assert db.query(ChatlttStep).filter_by(trang_thai="cho_job").count() == 0
