"""LTT WORKFLOW V2 — đường tiền của một lượt chạy (`23_24` dòng 33).

    QUOTE ──► trần chi phí tất định ──► APPROVAL ──► HOLD (1 lần/run)

## Ba thứ tệp này canh, và cả ba đều là **tiền**

1. **Đúng MỘT khoản giữ cho cả run.** Mỗi node rồi sẽ sinh một job, và đường
   job đã thu tiền. Hôm nay `dieu_phoi.attempt()` chưa nộp job nên chưa hỏng —
   nên đây là lúc duy nhất đặt được cái rào **trước** khi cầu nối ra đời.
2. **Lượt chạy đang sống KHÔNG bị xếp là tiền treo.** Sổ khoá theo `job_id`;
   ta đưa `run_id` vào đó. `credit.giu_cho_treo` hỏi bảng `jobs` để biết khoá
   nào còn sống, nên nếu không dạy nó biết `WorkflowRun` thì mọi run đang chạy
   bị báo treo — và `tu_hoan_treo()` sẽ **hoàn tiền cho một lượt đang chạy**.
3. **Trần TTL của run phải NGẮN HƠN ngưỡng tự hoàn.** Trước 08/09 cả hai đều
   24 giờ ⇒ khách trả `actual_cost` hay trả `0` tuỳ vòng quét nào chạy trước.

⚠️ Bộ test chạy SQLite, nên nó **không** kiểm được thứ chỉ PostgreSQL cưỡng chế.
   Bài `test_khoa_so_VUA_cot` dưới đây kiểm bằng độ dài khai báo, không bằng
   CSDL — cùng cách đã bắt được `"m1:" + id` = 39 ký tự vào `String(36)`.
"""
from __future__ import annotations

from datetime import timedelta

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'tien.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def _nguoi(db, so_du: int = 1000):
    from platform_core import credit
    from platform_core.models import User

    u = User(email="a@b.c", password_hash="x")
    db.add(u)
    db.flush()
    if so_du:
        credit.hoan_phi(db, u.id, so_du, kind="nap", note="test")
    db.flush()
    return u


def _run(db, owner_id: str, *, tran: int = 100, status: str = "RUNNING"):
    from platform_core.models import Workflow, WorkflowRun

    wf = Workflow(owner_id=owner_id, name="w")
    db.add(wf)
    db.flush()
    r = WorkflowRun(workflow_id=wf.id, version_id="v1", owner_id=owner_id,
                    estimated_max=tran, status=status)
    db.add(r)
    db.flush()
    return r


# ── 1. MỘT khoản giữ cho cả run ─────────────────────────────────────────────

def test_giu_cho_dung_MOT_lan_du_goi_nhieu_lan(db):
    """⛔ Rào chống thu hai lần. Nó phải đứng vững **trước** khi cầu nối
    node→job ra đời, vì lúc ấy sẽ có một đường thứ hai muốn giữ tiền."""
    from platform_core.models import CREDIT_HOLD, CreditEntry
    from platform_core.workflow import tien

    u = _nguoi(db)
    r = _run(db, u.id, tran=100)

    assert tien.giu_cho_run(db, r) is True
    assert tien.giu_cho_run(db, r) is False
    assert tien.giu_cho_run(db, r) is False
    db.commit()

    giu = db.query(CreditEntry).filter_by(job_id=r.id, kind=CREDIT_HOLD).all()
    assert len(giu) == 1, f"phai co DUNG MOT khoan giu, co {len(giu)}"
    assert giu[0].delta == -100


def test_tran_0_thi_KHONG_dat_hold_id(db):
    """`hold_id` nghĩa là *"có một khoản đang giữ"*. Đặt nó cho một khoản không
    tồn tại làm `ket_so` đi quyết toán một thứ rỗng."""
    from platform_core.workflow import tien

    u = _nguoi(db)
    r = _run(db, u.id, tran=0)
    assert tien.giu_cho_run(db, r) is False
    assert r.hold_id == ""


def test_khong_du_so_du_thi_NEM_va_khong_ghi_gi(db):
    from platform_core import credit
    from platform_core.models import CreditEntry
    from platform_core.workflow import tien

    u = _nguoi(db, so_du=10)
    r = _run(db, u.id, tran=100)
    truoc = db.query(CreditEntry).count()
    with pytest.raises(credit.ThieuCreditError):
        tien.giu_cho_run(db, r)
    assert db.query(CreditEntry).count() == truoc
    assert r.hold_id == ""


def test_khoa_so_VUA_cot(db):
    """🔴 `String(36)` + một uuid 36 ký tự = vừa khít. Thêm bất kỳ tiền tố nào
    cũng tràn — và SQLite **không** cưỡng chế nên bộ test sẽ không thấy.

    Đây đúng là lỗi đã giết `M-1` sáng nay (`"m1:" + id` = 39). Kiểm bằng độ
    dài **khai báo**, không bằng CSDL.
    """
    from platform_core.models import CreditEntry, WorkflowRun
    from platform_core.workflow import tien

    u = _nguoi(db)
    r = _run(db, u.id)
    tien.giu_cho_run(db, r)
    db.commit()

    for lop, cot, gia_tri in ((WorkflowRun, "hold_id", r.hold_id),
                              (CreditEntry, "job_id", r.id)):
        gioi_han = lop.__table__.columns[cot].type.length
        assert len(gia_tri) <= gioi_han, (
            f"{lop.__tablename__}.{cot}: {len(gia_tri)} > {gioi_han}")


# ── 2. Quyết toán và hoàn ───────────────────────────────────────────────────

def test_ket_so_thu_dung_actual_cost_va_hoan_phan_du(db):
    from platform_core import credit
    from platform_core.models import Workflow  # noqa: F401
    from platform_core.workflow import ket_so, tien

    u = _nguoi(db, so_du=1000)
    r = _run(db, u.id, tran=100)
    tien.giu_cho_run(db, r)
    db.commit()
    assert credit.so_du(db, u.id) == 900

    r.status = "SUCCEEDED"
    db.flush()
    # Chi phí thật 30 trên trần 100.
    from platform_core.models import NodeRunSnapshot
    db.add(NodeRunSnapshot(run_id=r.id, node_id="n1", attempt_number=1,
                           execution_status="SUCCEEDED", description="x",
                           is_valid=True, cost_credit=30))
    db.flush()

    assert ket_so.ket_so(db, r.id) is True
    db.commit()

    assert r.actual_cost == 30
    assert r.hold_id == ""
    assert credit.so_du(db, u.id) == 970, "phai hoan 70 phan chua dung"


def test_SYSTEM_FAILURE_hoan_TOAN_BO(db):
    """⭐ Lỗi **của ta** thì không được bắt khách trả. Đây là lý do
    `SYSTEM_FAILURE` phải tách khỏi `FAILED` (`G21`)."""
    from platform_core import credit
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import ket_so, tien

    u = _nguoi(db, so_du=1000)
    r = _run(db, u.id, tran=100)
    tien.giu_cho_run(db, r)
    db.add(NodeRunSnapshot(run_id=r.id, node_id="n1", attempt_number=1,
                           execution_status="FAILED", description="x",
                           is_valid=True, cost_credit=80))
    r.status = "SYSTEM_FAILURE"
    db.flush()

    ket_so.ket_so(db, r.id)
    db.commit()
    assert r.actual_cost == 0
    assert credit.so_du(db, u.id) == 1000, "loi cua TA thi khach khong mat gi"


def test_FAILED_van_thu_phan_da_dung(db):
    """Đối chứng của bài trên. Không có nó, một bản vá "hoàn tất cả khi lỗi"
    cũng làm bài trên xanh — và ta thu 0 cho mọi thất bại nghiệp vụ."""
    from platform_core import credit
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import ket_so, tien

    u = _nguoi(db, so_du=1000)
    r = _run(db, u.id, tran=100)
    tien.giu_cho_run(db, r)
    db.add(NodeRunSnapshot(run_id=r.id, node_id="n1", attempt_number=1,
                           execution_status="FAILED", description="x",
                           is_valid=True, cost_credit=80))
    r.status = "FAILED"
    db.flush()

    ket_so.ket_so(db, r.id)
    db.commit()
    assert r.actual_cost == 80
    assert credit.so_du(db, u.id) == 920


def test_ket_so_goi_LAI_khong_thu_them(db):
    from platform_core import credit
    from platform_core.workflow import ket_so, tien

    u = _nguoi(db, so_du=1000)
    r = _run(db, u.id, tran=100)
    tien.giu_cho_run(db, r)
    r.status = "SUCCEEDED"
    db.flush()

    ket_so.ket_so(db, r.id)
    db.commit()
    sau_lan_dau = credit.so_du(db, u.id)
    assert ket_so.ket_so(db, r.id) is False
    db.commit()
    assert credit.so_du(db, u.id) == sau_lan_dau


# ── 3. Run đang sống KHÔNG phải tiền treo ───────────────────────────────────

def test_run_DANG_CHAY_khong_bi_xep_la_tien_treo(db):
    """🔴 Không có bản vá này thì `tu_hoan_treo()` **hoàn tiền cho một lượt
    đang chạy**, và sổ chỉ ghi thêm nên khoản hoàn nhầm không xoá được."""
    from datetime import datetime, timezone

    from platform_core import credit
    from platform_core.workflow import tien

    u = _nguoi(db)
    r = _run(db, u.id, tran=100, status="RUNNING")
    tien.giu_cho_run(db, r)
    db.commit()

    mai_sau = datetime.now(timezone.utc) + timedelta(days=30)
    treo = credit.giu_cho_treo(db, now=mai_sau)
    assert not [t for t in treo if t.job_id == r.id], (
        "run dang RUNNING bi xep la tien treo")


def test_run_DA_KET_THUC_ma_chua_ket_so_THI_van_bi_bat(db):
    """⭐ Đối chứng bắt buộc. Không có bài này, một bản vá *"coi mọi run là
    sống"* cũng làm bài trên xanh — và bộ dò tiền treo chết im lặng đúng ở
    lớp nó vừa được mở rộng để bảo vệ.
    """
    from datetime import datetime, timezone

    from platform_core import credit
    from platform_core.workflow import tien

    u = _nguoi(db)
    r = _run(db, u.id, tran=100, status="RUNNING")
    tien.giu_cho_run(db, r)
    # Kết thúc nhưng KHÔNG kết sổ — đúng hình dạng của một khoản treo thật.
    r.status = "FAILED"
    db.commit()

    mai_sau = datetime.now(timezone.utc) + timedelta(days=30)
    treo = credit.giu_cho_treo(db, now=mai_sau)
    assert [t for t in treo if t.job_id == r.id], (
        "run da ket thuc ma chua ket so PHAI bi bat")


# ── 4. Hai ngưỡng không được bằng nhau ──────────────────────────────────────

def test_TRAN_RUN_phai_NGAN_HON_nguong_tu_hoan():
    """🔴 Trước 08/09 cả hai đều 24 giờ.

    Cùng một mốc ⇒ khách trả `actual_cost` hay trả **0** phụ thuộc vòng quét
    nào chạy trước. Sổ vẫn cân, nhưng **số tiền thu là không tất định** — và
    một hệ tính tiền không tất định thì không đối soát được.

    Lưới đỡ phải bung **sau** đường chính; bằng nhau thì nó không phải lưới đỡ
    mà là một đường thứ hai cạnh tranh.
    """
    from platform_core import credit
    from platform_core.workflow import dong_co

    assert dong_co.TRAN_RUN < credit.TU_HOAN_SAU, (
        f"TRAN_RUN={dong_co.TRAN_RUN} phai NGAN HON "
        f"TU_HOAN_SAU={credit.TU_HOAN_SAU}")
    du = credit.TU_HOAN_SAU - dong_co.TRAN_RUN
    assert du >= timedelta(hours=2), (
        f"khoang cach {du} qua hep cho mot vong quet co chu ky")


def test_giu_cho_run_chi_co_MOT_cho_goi_va_cho_do_tu_tao_run():
    """🔴 BÁNH CÓC — thứ đang giữ bất biến "một run = một hold" KHÔNG phải một
    khoá, mà là **hình dạng của chỗ gọi**. Bài này ghim đúng hình dạng đó.

    `giu_cho_run()` đọc `run.hold_id` rồi ghi mà **không** khoá hàng. Đo được
    trên PostgreSQL thật 23/09 (`tests/test_1720_wf_dong_co_pg.py::
    test_giu_cho_run_dong_thoi_chi_mot_hold`): hai phiên cùng cầm MỘT run đã
    commit ⇒ **40 credit bị giữ cho một run có trần 20**. Cuộc đua là thật.

    Hôm nay nó **không chạm tới được**, vì đúng một lý do: chỗ gọi duy nhất là
    `tao_run.tao_run()`, và ở đó hàng `workflow_run` vừa được `INSERT` **trong
    cùng transaction** — không phiên nào khác nhìn thấy nó để mà đua. Hai
    request cùng `Idempotency-Key` thì kẻ thua bị chặn ngay tại `INSERT` bởi
    chỉ mục bộ phận `ux_workflow_run_idem`, **trước** khi tới đường tiền
    (`test_tao_run_dong_thoi_cung_khoa_chi_mot_hold`, xanh trên PostgreSQL).

    ⇒ Nên thay vì thêm một `with_for_update()` vào đường tiền để chống một
      cuộc đua không có đường tới, ta ghim **tiền đề** đang làm nó an toàn.
      Thêm một chỗ gọi thứ hai — trên một run **đã commit** (thử lại, bộ dọn
      nền, một cửa API mới) — là biến cuộc đua đã đo được thành cuộc đua có
      thật. Khi bài này đỏ, câu trả lời gần như chắc chắn là: khoá hàng
      (`with_for_update()`) trong `giu_cho_run` trước khi đọc `hold_id`.
    """
    import ast
    import pathlib

    goc = pathlib.Path(__file__).resolve().parent.parent
    cho_goi: dict[str, list[int]] = {}
    for thu_muc in ("platform_core", "apps", "server"):
        for tep in (goc / thu_muc).rglob("*.py"):
            try:
                cay = ast.parse(tep.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):      # pragma: no cover
                continue
            for nut in ast.walk(cay):
                if not isinstance(nut, ast.Call):
                    continue
                ham = nut.func
                ten = (ham.attr if isinstance(ham, ast.Attribute)
                       else ham.id if isinstance(ham, ast.Name) else "")
                if ten == "giu_cho_run":
                    cho_goi.setdefault(
                        tep.relative_to(goc).as_posix(), []).append(nut.lineno)

    assert set(cho_goi) == {"platform_core/workflow/tao_run.py"}, (
        "`giu_cho_run()` doc `run.hold_id` roi ghi ma KHONG khoa hang. No an "
        "toan CHI VI cho goi duy nhat tao hang run trong cung transaction. "
        f"Cho goi hien tai: {cho_goi}. Neu ban vua them mot cho goi tren mot "
        "run DA COMMIT, cuoc dua o tests/test_1720_wf_dong_co_pg.py::"
        "test_giu_cho_run_dong_thoi_chi_mot_hold tro thanh that - hay khoa "
        "hang (`with_for_update()`) truoc khi doc `hold_id`, roi bo `xfail` "
        "cua bai do.")

    # Chỗ gọi duy nhất phải nằm SAU `thi_hanh.tao_run` trong CÙNG một khối
    # `with db.begin_nested()` — đó mới là thứ làm hàng run vô hình với phiên
    # khác. Một chỗ gọi đúng tệp nhưng ngoài khối ấy không còn tiền đề nào.
    nguon = (goc / "platform_core/workflow/tao_run.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    trong_khoi = False
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.With):
            continue
        goi = [n for n in ast.walk(nut) if isinstance(n, ast.Call)]
        ten = [n.func.attr for n in goi if isinstance(n.func, ast.Attribute)]
        if "begin_nested" in ten and "tao_run" in ten and "giu_cho_run" in ten:
            trong_khoi = True
    assert trong_khoi, (
        "`tien.giu_cho_run()` phai nam trong CUNG khoi `with db.begin_nested()` "
        "voi `thi_hanh.tao_run()`: hang `workflow_run` chi vo hinh voi phien "
        "khac khi no chua commit. Tach hai thu ra la mo lai cuoc dua da do.")
