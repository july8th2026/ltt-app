"""
test_807 — `luu_run.py`: đưa một run xuống CSDL và đọc lại được. (H44 P03)

Mệnh đề đắt nhất ở đây là **số 4**: ba cột tiền là *dẫn xuất*, nên chạy
`cong_tien()` hai lần phải ra **cùng một số**. Một hàm tên là "cộng" mà lại
`+=` vào cột sẵn có sẽ nhân đôi mỗi lần bị gọi lại — và nó sẽ bị gọi lại, vì
một run dài cập nhật tiền nhiều lần trên đường đi.

⛔ Ba cột đó **không phải sổ**. Đối soát tiền đọc `credit_entries`
(`02_ADR_ORCHESTRATION.md` §5). Test này chốt rằng chúng chỉ *phản chiếu*.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import dieu_phoi as DP
from apps.chatltt.services import luu_run as LR
from apps.chatltt.services import thi_hanh


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
KHACH = "u-nguoi-la"


def _mo(db, user=U):
    return LR.mo_run(db, user_id=user, conv_id="c-1", message_id="m-1")


def _buoc(thu_tu=1, loai="tool", ten="tim_kiem", **kw):
    return DP.Buoc(thu_tu=thu_tu, loai=loai, ten=ten, **kw)


# ── 1. Mở run ──────────────────────────────────────────────────────────────

def test_mo_run_bat_dau_o_CREATED(db):
    r = _mo(db)
    assert r.trang_thai == DP.CREATED
    assert r.id and r.id.startswith("run_")
    assert r.finished_at is None


# ── 2. Ghi bước ────────────────────────────────────────────────────────────

def test_ghi_buoc_giu_CHUOI_THO_khong_dung_lai_duoc_tu_doi_so(db):
    """🔴 `doi_so_tho` là thứ model **thật sự phát ra**, `doi_so` là thứ ta
    **đọc hiểu được**. Chúng khác nhau, và ngày điều tra một lượt sai thì cái
    cần là bản thô — `json.dumps(doi_so)` sinh lại chuỗi khác (khoảng trắng,
    thứ tự khoá) nên không thay thế được."""
    r = _mo(db)
    tho = '{"q":  "ha noi",\n "n":3}'
    LR.ghi_buoc(db, r, _buoc(doi_so={"q": "ha noi", "n": 3}, doi_so_tho=tho))
    hang = LR.su_that(db, user_id=U, run_id=r.id)
    import json

    from apps.chatltt.tables import ChatlttStep
    st = db.query(ChatlttStep).one()
    assert st.doi_so_tho == tho
    assert st.doi_so_tho != json.dumps(st.doi_so)
    assert hang["buoc"][0]["doi_so"] == {"q": "ha noi", "n": 3}


def test_ghi_buoc_LOI_van_duoc_luu_va_danh_dau(db):
    """Lỗi là kết quả (`thi_hanh` §2). Một bước lỗi mà không có hàng trong CSDL
    thì lịch sử của run có lỗ đúng ở chỗ cần nhìn nhất."""
    r = _mo(db)
    kq = thi_hanh.KetQua(ok=False, ma_loi="HET_GIO", thong_diep="qua 30 giay")
    LR.ghi_buoc(db, r, _buoc(ket_qua=kq))
    from apps.chatltt.tables import ChatlttStep
    st = db.query(ChatlttStep).one()
    assert st.trang_thai == "loi"
    assert st.ket_qua["ma_loi"] == "HET_GIO"
    assert "HET_GIO" in st.ket_qua["cho_model"], "phai luu dung chuoi MODEL DA DOC"


def test_hai_buoc_cung_thu_tu_trong_mot_run_bi_CSDL_chan(db):
    """⭐ Ràng buộc ở tầng CSDL, không ở một `if`. Thứ tự bước là thứ dựng lại
    cả cuộc hội thoại; hai bước cùng số thứ tự làm nó thành mơ hồ vĩnh viễn."""
    from sqlalchemy.exc import IntegrityError
    r = _mo(db)
    LR.ghi_buoc(db, r, _buoc(thu_tu=1))
    with pytest.raises(IntegrityError):
        LR.ghi_buoc(db, r, _buoc(thu_tu=1, ten="khac"))
    db.rollback()


def test_ket_qua_dai_bi_CAT_truoc_khi_vao_CSDL(db):
    r = _mo(db)
    kq = thi_hanh.KetQua(ok=True, noi_dung="x" * 50_000)
    LR.ghi_buoc(db, r, _buoc(ket_qua=kq))
    from apps.chatltt.tables import ChatlttStep
    st = db.query(ChatlttStep).one()
    assert len(st.ket_qua["cho_model"]) <= 8_000


# ── 3. Đóng run ────────────────────────────────────────────────────────────

def test_dong_run_chep_trang_thai_va_dat_finished_at(db):
    r = _mo(db)
    run = DP.Run(trang_thai=DP.COMPLETED, so_vong_model=3, so_loi_goi_tool=1,
                 ly_do_ket=DP.KET_TRAN_VONG)
    LR.dong_run(db, r, run)
    assert (r.trang_thai, r.so_vong_model, r.ly_do_ket) == (
        DP.COMPLETED, 3, DP.KET_TRAN_VONG)
    assert r.finished_at is not None


def test_run_CHUA_ket_thuc_thi_finished_at_van_RONG(db):
    """Một `finished_at` đặt sớm làm mọi phép đo thời lượng sai, và sai *về
    phía ngắn* — tức về phía "mọi thứ đang nhanh", đúng hướng không ai đi tìm."""
    r = _mo(db)
    LR.dong_run(db, r, DP.Run(trang_thai=DP.TOOL_RUNNING, so_vong_model=2))
    assert r.finished_at is None
    assert r.so_vong_model == 2


# ── 4. Tiền: DẪN XUẤT, không tích luỹ ──────────────────────────────────────

def _exec(db, run, giu, thu, hoan):
    from apps.chatltt.tables import ChatlttExecution
    e = ChatlttExecution(message_id="m-1", conversation_id="c-1", user_id=run.user_id,
                         tool_name="llm", mode="chat", run_id=run.id,
                         credit_giu=giu, credit_thu=thu, credit_hoan=hoan)
    db.add(e)
    db.flush()
    return e


def test_cong_tien_cong_tu_execution_con(db):
    r = _mo(db)
    _exec(db, r, 10, 7, 3)
    _exec(db, r, 20, 18, 2)
    LR.cong_tien(db, r)
    assert (r.credit_giu_tong, r.credit_thu_tong, r.credit_hoan_tong) == (30, 25, 5)


def test_cong_tien_GOI_HAI_LAN_ra_CUNG_MOT_SO(db):
    """🔴 Mệnh đề đắt nhất của tệp này.

    Ba cột là *phản chiếu* của các hàng con, không phải bộ đếm. Một `+=` ở đây
    nhân đôi tiền mỗi lần hàm bị gọi lại — và nó **sẽ** bị gọi lại, vì một run
    dài cập nhật tiền nhiều lần trên đường đi.
    """
    r = _mo(db)
    _exec(db, r, 10, 7, 3)
    LR.cong_tien(db, r)
    dau = (r.credit_giu_tong, r.credit_thu_tong, r.credit_hoan_tong)
    LR.cong_tien(db, r)
    LR.cong_tien(db, r)
    assert (r.credit_giu_tong, r.credit_thu_tong, r.credit_hoan_tong) == dau


def test_cong_tien_KHONG_dem_execution_cua_run_khac(db):
    r1, r2 = _mo(db), _mo(db)
    _exec(db, r1, 10, 10, 0)
    _exec(db, r2, 99, 99, 0)
    LR.cong_tien(db, r1)
    assert r1.credit_giu_tong == 10


def test_cong_tien_run_RONG_ra_KHONG_khong_phai_None(db):
    """`SUM()` trên tập rỗng trả `NULL` ở SQL. Không bọc `coalesce` thì ba cột
    `nullable=False` nhận `None` và vỡ ở tận lúc `commit`, xa chỗ gây ra."""
    r = _mo(db)
    LR.cong_tien(db, r)
    assert (r.credit_giu_tong, r.credit_thu_tong, r.credit_hoan_tong) == (0, 0, 0)


# ── 5. Đọc lại: IDOR chặn ở tầng service ───────────────────────────────────

def test_nguoi_khac_doc_khong_ra_gi(db):
    r = _mo(db)
    LR.ghi_buoc(db, r, _buoc())
    assert LR.su_that(db, user_id=KHACH, run_id=r.id) == {}
    assert LR.su_that(db, user_id=U, run_id=r.id)["run_id"] == r.id


def test_su_that_KHONG_do_ca_ket_qua_ra_giao_dien(db):
    """Một kết quả 8 KB × 12 bước là ~96 KB JSON cho một thứ người dùng hiếm
    khi mở. Giao diện xin riêng khi cần."""
    r = _mo(db)
    LR.ghi_buoc(db, r, _buoc(ket_qua=thi_hanh.KetQua(ok=True, noi_dung="y" * 7_000)))
    b = LR.su_that(db, user_id=U, run_id=r.id)["buoc"][0]
    assert len(b["tom_tat"]) <= 160
    assert "ket_qua" not in b


def test_buoc_tra_ve_DUNG_THU_TU(db):
    r = _mo(db)
    for i in (3, 1, 2):
        LR.ghi_buoc(db, r, _buoc(thu_tu=i, ten=f"t{i}"))
    ds = LR.su_that(db, user_id=U, run_id=r.id)["buoc"]
    assert [x["thu_tu"] for x in ds] == [1, 2, 3]


# ── 6. Khối nối vào message — hình dạng CŨ, phần tử MỚI ────────────────────

def test_cham_tran_thi_co_khoi_status(db):
    """Một lượt dừng vì trần mà im lặng trông y hệt một lượt model tự thấy đủ.
    Với người đang chờ, hai chuyện đó khác nhau."""
    r = DP.Run(trang_thai=DP.COMPLETED, ly_do_ket=DP.KET_TRAN_VONG,
               van_ban_cuoi="toi da thu 8 vong")
    loai = [k["type"] for k in LR.khoi_cho_message(r)]
    assert loai[-1] == "status"


def test_ket_binh_thuong_thi_KHONG_co_khoi_status(db):
    r = DP.Run(trang_thai=DP.COMPLETED, ly_do_ket=DP.KET_XONG, van_ban_cuoi="xong")
    assert [k["type"] for k in LR.khoi_cho_message(r)] == ["text"]


def test_khoi_van_la_PHAN_TU_trong_mang_cu(db):
    """⛔ Điều kiện của A5: `blocks` **không đổi hình dạng**, chỉ có phần tử lạ.
    Đó là lý do một bản V1 đọc dữ liệu V3 vẫn vẽ được phần nó hiểu."""
    r = DP.Run(trang_thai=DP.COMPLETED, ly_do_ket=DP.KET_XONG, van_ban_cuoi="ok")
    r.buoc = [_buoc(ket_qua=thi_hanh.KetQua(ok=True, noi_dung="ha noi 30 do"))]
    khoi = LR.khoi_cho_message(r)
    assert isinstance(khoi, list)
    assert all(isinstance(k, dict) and isinstance(k.get("type"), str) for k in khoi)
    assert [k["type"] for k in khoi] == ["tool_call", "text"]


# ── 7. Nối THẬT: `dieu_phoi.chay(ghi=…)` → CSDL ────────────────────────────

def _chu(t):
    return [{"type": "response.delta", "text": t},
            {"type": "response.completed", "finish_reason": "stop"}]


def _goi_tool(ten, ds_tho, idx=0):
    return [{"type": "tool_call.delta", "tool_calls": [
                {"index": idx, "id": f"call_{idx+1}", "type": "function",
                 "function": {"name": ten, "arguments": ds_tho}}]},
            {"type": "response.completed", "finish_reason": "tool_calls"}]


def _model(*luot):
    it = iter(luot)

    def f(_messages, _tools):
        return next(it)
    return f


def test_chay_voi_ghi_dat_MOI_BUOC_xuong_CSDL(db):
    """⭐ Đây là phép kiểm nối hai nửa: máy trạng thái thuần ở một bên, ba bảng ở
    bên kia. Chạy riêng thì cả hai đã xanh; thứ chỉ hỏng ở chỗ nối là thứ này
    bắt được."""
    r = _mo(db)
    run = DP.chay(
        messages=[{"role": "user", "content": "may do?"}], tools=[],
        goi_model=_model(_goi_tool("thoi_tiet", '{"tp":"ha noi"}'), _chu("30 do")),
        chay_tool=lambda t, d, c: thi_hanh.KetQua(ok=True, noi_dung="30"),
        ghi=lambda b: LR.ghi_buoc(db, r, b))
    LR.dong_run(db, r, run)

    from apps.chatltt.tables import ChatlttStep
    hang = db.query(ChatlttStep).order_by(ChatlttStep.thu_tu).all()
    assert [h.loai for h in hang] == ["model", "tool", "model"]
    assert hang[1].tool_name == "thoi_tiet"
    assert hang[1].doi_so_tho == '{"tp":"ha noi"}', "chuoi THO phai qua duoc"
    assert r.trang_thai == DP.COMPLETED and r.ly_do_ket == DP.KET_XONG


def test_ghi_thay_DUNG_so_buoc_ma_run_giu(db):
    """Số hàng trong CSDL phải bằng `len(run.buoc)`. Lệch nghĩa là có một lối
    vào thứ hai không đi qua `_them` — thứ mà `_them` sinh ra để chặn."""
    r = _mo(db)
    run = DP.chay(
        messages=[], tools=[],
        goi_model=_model(_goi_tool("a", "{}"), _goi_tool("b", "{}"), _chu("xong")),
        chay_tool=lambda t, d, c: thi_hanh.KetQua(ok=True, noi_dung="1"),
        ghi=lambda b: LR.ghi_buoc(db, r, b))
    from apps.chatltt.tables import ChatlttStep
    assert db.query(ChatlttStep).count() == len(run.buoc) == 5


def test_KHONG_truyen_ghi_thi_may_trang_thai_van_chay(db):
    """⛔ `ghi` tuỳ chọn là điều kiện để `test_803` kiểm được máy trạng thái bằng
    số học thuần, không cần CSDL."""
    run = DP.chay(messages=[], tools=[], goi_model=_model(_chu("chao")),
                  chay_tool=lambda t, d, c: thi_hanh.KetQua(ok=True))
    assert run.trang_thai == DP.COMPLETED
    from apps.chatltt.tables import ChatlttStep
    assert db.query(ChatlttStep).count() == 0
