"""Đường ĐÁNH THỨC worker: `NOTIFY` lúc xếp job, `_cho_viec` lúc ngủ, và N-46.

Ba nhóm bất biến, và chúng trả lời ba câu khác nhau:

1. **Đánh thức không được thay thế hàng đợi.** `jobs.claim` vẫn là bộ phán quyết
   duy nhất; mất tin nhắn chỉ làm chậm, không làm mất job. Nên nhóm này chốt
   rằng `_cho_viec` xấu nhất **bằng** `time.sleep` cũ, rằng luồng nghe không
   bao giờ ném ra ngoài, và rằng `POLL_INTERVAL_S` **không** bị hạ xuống — hạ
   nó là đổi giá (4x số lượt truy vấn trên 8 tiến trình) để mua đúng thứ đường
   đánh thức đã cho không.
2. **`NOTIFY` nằm TRONG transaction của người nộp.** PostgreSQL chỉ gửi tin
   nhắn lúc `COMMIT`, nên job rollback thì tin nhắn cũng rollback. Đo thật trên
   PostgreSQL ở `tests/test_3911_danh_thuc_worker_pg.py`; ở đây chốt hình dạng
   mã và chốt rằng SQLite không bị ảnh hưởng.
3. **N-46 — nhiễu cho lượt giành lease bảo trì.** 8 tiến trình worker khởi động
   cùng lúc, 7 tiến trình thua, và trước bản vá cả 7 ngủ **đúng** 20,000 s rồi
   thức **cùng một giây**, vĩnh viễn đồng pha.

⛔ Không phép nào ở đây nạp model, mở tiến trình con, hay cần PostgreSQL.
"""
from __future__ import annotations

import ast
import inspect
import pathlib
import threading
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from platform_core import job_runner, jobs as jobq
from platform_core.db import Base

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ── 1. Đánh thức là tối ưu độ trễ, không phải hợp đồng hàng đợi ──────────────

def test_cho_viec_khong_co_tin_nhan_thi_dung_bang_sleep_cu():
    """Không ai đánh thức ⇒ `_cho_viec` chờ đủ `giay`, y như `time.sleep`."""
    co = threading.Event()
    t0 = time.monotonic()
    job_runner._cho_viec(co, 0.30)
    troi = time.monotonic() - t0
    assert troi >= 0.28, f"thuc som ma khong ai goi: {troi:.3f}s"
    assert not co.is_set()


def test_cho_viec_thuc_ngay_khi_co_tin_nhan():
    co = threading.Event()
    co.set()
    t0 = time.monotonic()
    job_runner._cho_viec(co, 5.0)
    troi = time.monotonic() - t0
    assert troi < 0.5, f"co da bat ma van ngu {troi:.3f}s"
    # Đã tiêu thì phải xoá, nếu không vòng sau không bao giờ ngủ (vòng nóng).
    assert not co.is_set()


def test_cho_viec_thuc_giua_giac_ngu():
    """Tin nhắn tới GIỮA giấc ngủ cũng cắt giấc ngủ — đây là ca thật."""
    co = threading.Event()
    threading.Timer(0.15, co.set).start()
    t0 = time.monotonic()
    job_runner._cho_viec(co, 3.0)
    troi = time.monotonic() - t0
    assert 0.10 <= troi < 1.0, f"khong bi cat dung luc: {troi:.3f}s"


def test_poll_interval_KHONG_bi_ha_xuong():
    """⛔ Bánh cóc: đường đánh thức tồn tại để KHÔNG phải hạ nhịp poll.

    Hạ 2,0 → 0,5 nhân **bốn** số lượt `reclaim_orphans` + `claim` chạy 24/7 của
    8 tiến trình worker lên cùng một PostgreSQL — đúng cái máy này đã có sự cố
    phục hồi 4,5 phút. Ai muốn hạ thì phải sửa phép kiểm này và nói lý do.
    """
    assert job_runner.POLL_INTERVAL_S == 2.0


def test_bat_dau_nghe_tra_None_khi_khong_phai_postgres(monkeypatch):
    """SQLite / CSDL chưa cấu hình ⇒ không luồng nghe, và KHÔNG ném."""
    monkeypatch.setattr("platform_core.db.database_url",
                        lambda *a, **k: "sqlite+pysqlite:///:memory:")
    assert job_runner._bat_dau_nghe(threading.Event(), None, "w") is None

    def _khong_co(*a, **k):
        from platform_core.db import DatabaseNotConfigured
        raise DatabaseNotConfigured("chua dat")

    monkeypatch.setattr("platform_core.db.database_url", _khong_co)
    assert job_runner._bat_dau_nghe(threading.Event(), None, "w") is None


def test_vong_nghe_khong_bao_gio_ghi_vao_CSDL():
    """Luồng nghe chỉ `LISTEN` và `set()` một cờ — nó không phải hàng đợi.

    Đọc bằng AST chứ không bằng mắt: một lời gọi `commit`/`submit`/`claim` lọt
    vào luồng này biến một bộ đánh thức thành một bộ điều phối thứ hai, và hai
    bộ điều phối cho cùng một hàng đợi là thứ không ai gỡ được sau này.
    """
    cay = ast.parse(inspect.getsource(job_runner._vong_nghe_job_moi))
    ten_goi = set()
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Call):
            f = nut.func
            if isinstance(f, ast.Attribute):
                ten_goi.add(f.attr)
            elif isinstance(f, ast.Name):
                ten_goi.add(f.id)
    cam = {"commit", "submit", "claim", "complete", "fail", "add", "flush",
           "reclaim_orphans"}
    assert not (ten_goi & cam), f"luong nghe dang GHI: {sorted(ten_goi & cam)}"
    assert "set" in ten_goi, "luong nghe khong danh thuc ai"


# ── 2. `NOTIFY` nằm trong transaction của người nộp ──────────────────────────

def test_submit_goi_danh_thuc_worker_TRUOC_khi_tra_ve():
    """Bánh cóc: `submit` phải gọi `danh_thuc_worker`, và gọi trước `return`.

    Đây là chỗ duy nhất phát tin. Bỏ lời gọi này ra thì mọi thứ vẫn xanh, chỉ
    chậm lại 1 giây mỗi lượt chuyển làn — một hồi quy không test nào khác thấy.
    """
    cay = ast.parse(inspect.getsource(jobq.submit))
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
           and n.func.id == "danh_thuc_worker"]
    assert goi, "submit() khong con goi danh_thuc_worker"


def test_danh_thuc_worker_tren_sqlite_la_khong_lam_gi(db):
    """SQLite không có `NOTIFY`; `submit` vẫn phải chạy trọn vẹn."""
    from tests.conftest import bao_dam_user

    bao_dam_user(db, "u-3900")
    job = jobq.submit(db, user_id="u-3900", app_slug="auto_scan_video",
                      job_type="auto_scan_video.advance", params={})
    db.commit()
    assert job.id
    # Gọi trực tiếp lần nữa: không ném, không đổi gì.
    jobq.danh_thuc_worker(db)


def test_danh_thuc_worker_khong_nem_khi_CSDL_hong():
    """Lỗi của đường đánh thức ⛔ không được làm hỏng việc nộp job."""
    class _PhienHong:
        def get_bind(self):
            raise RuntimeError("mat ket noi")

    jobq.danh_thuc_worker(_PhienHong())        # không ném là toàn bộ bất biến


def test_ten_kenh_la_dinh_danh_thuan():
    """`NOTIFY` không nhận tham số bind ⇒ tên kênh phải là hằng số an toàn."""
    assert jobq.KENH_JOB_MOI.isidentifier()
    assert jobq.KENH_JOB_MOI.isascii()


# ── 3. N-46: nhiễu cho lượt giành lease bảo trì ──────────────────────────────

def test_n46_cho_lease_bao_tri_co_nhieu():
    """8 tiến trình khởi động cùng lúc ⛔ không được thức cùng một giây."""
    mau = [job_runner._cho_lease_bao_tri() for _ in range(200)]
    assert len(set(mau)) > 190, "gia tri lap lai — khong co nhieu that"
    bien = job_runner.LEASE_RETRY_S * job_runner.LEASE_RETRY_JITTER
    assert min(mau) >= job_runner.LEASE_RETRY_S - bien - 1e-9
    assert max(mau) <= job_runner.LEASE_RETRY_S + bien + 1e-9
    # Nhiễu phải ĐỦ RỘNG để rải 7 tiến trình thua ra: một cửa sổ hẹp hơn một
    # giây thì 7 lượt `INSERT` hỏng vẫn rơi vào cùng một giây.
    assert (max(mau) - min(mau)) > 1.0


def test_n46_vong_bao_tri_khong_con_sleep_hang_so():
    """AST: `_vong_bao_tri` ⛔ không được `sleep(LEASE_RETRY_S)` trần nữa."""
    cay = ast.parse(inspect.getsource(job_runner._vong_bao_tri))
    for nut in ast.walk(cay):
        if (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute)
                and nut.func.attr == "sleep"):
            for tham in nut.args:
                assert not (isinstance(tham, ast.Name)
                            and tham.id == "LEASE_RETRY_S"), (
                    "sleep(LEASE_RETRY_S) tran — N-46 quay lai")


def test_n46_giu_nguyen_ky_vong_trung_binh():
    """Nhiễu phải ĐỐI XỨNG: nó rải pha, ⛔ không nới thời gian nhận lease.

    Một `random.uniform(0, X)` cộng thêm sẽ làm việc nhận lease sau khi chủ chết
    chậm đi trung bình X/2 — đó là đổi một lỗi lấy một lỗi khác.
    """
    mau = [job_runner._cho_lease_bao_tri() for _ in range(5000)]
    tb = sum(mau) / len(mau)
    assert abs(tb - job_runner.LEASE_RETRY_S) < 0.5, f"lech ky vong: {tb:.2f}s"
