"""
test_150 - giành GPU phải NGUYÊN TỬ, không phải "đọc VRAM rồi quyết".

Vì sao file này tồn tại: máy chủ có 2 GPU từ 2026-08-06. Cách làm hiển nhiên —
hỏi `nvidia-smi` xem card nào trống rồi dùng card đó — hỏng đúng lúc nó cần
đúng: hai worker khởi động cùng lúc **cùng đọc thấy GPU 0 trống**, cùng chọn,
cùng nạp model, cùng OOM. Và lỗi hiện ra giữa job của khách hàng.

Các test dưới đây kiểm chính cái đó, không kiểm "hàm có chạy không".
"""
from __future__ import annotations

import threading
from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from platform_core import gpu as gpu_mod
from platform_core import gpu_lease
from platform_core.db import Base
from platform_core.models import GpuLease


@pytest.fixture(autouse=True)
def _cach_ly_claim_gpu(gpu_khong_claim_toan_may):
    """Autouse trong PHAM VI TEP NAY: cat khoi claim GPU toan may.

    Xem `tests/conftest.py` cuoi tep de biet vi sao. Tom tat: mot claim THAT
    tren GPU 0 cua ho khac bi tru vao card GIA cung index 0, nen phep kiem do
    hay xanh tuy theo luc do ai dang dung GPU — chu khong theo ma.
    """


def _gpu(i, uuid, free_mb=16000, total_mb=16311, util=0):
    return gpu_mod.GpuInfo(index=i, name="Card giả", uuid=uuid,
                           total_mb=total_mb, free_mb=free_mb, util_pct=util)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/gpu.db")
    Base.metadata.create_all(engine, tables=[GpuLease.__table__])
    monkeypatch.setattr(gpu_lease, "host_name", lambda: "may-thu")
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def hai_gpu(monkeypatch):
    gpus = [_gpu(0, "GPU-aaa"), _gpu(1, "GPU-bbb")]
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: list(gpus))
    return gpus


def test_hai_worker_khong_the_cung_giu_mot_gpu(db, monkeypatch):
    """Đây là lý do cả module tồn tại."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-chi-mot-cai")])

    a = gpu_lease.acquire(db, worker_id="w1", job_id="job-a")
    b = gpu_lease.acquire(db, worker_id="w2", job_id="job-b")

    assert a is not None, "worker đầu phải giành được"
    assert b is None, ("worker thứ hai giành được cùng một GPU — hai job sẽ cùng "
                       "nạp model lên một card và OOM")


def test_moi_worker_mot_gpu_khac_nhau(db, hai_gpu):
    a = gpu_lease.acquire(db, worker_id="w1", job_id="ja")
    b = gpu_lease.acquire(db, worker_id="w2", job_id="jb")
    c = gpu_lease.acquire(db, worker_id="w3", job_id="jc")

    assert a and b and a.gpu_uuid != b.gpu_uuid, "hai job phải rơi vào hai card"
    assert c is None, "card thứ ba không tồn tại thì phải trả None, không bịa ra"


def test_gianh_cho_dua_that_su_bang_nhieu_luong(db, tmp_path, monkeypatch):
    """Không mô phỏng cuộc đua bằng lời — cho 8 luồng cùng giành 2 GPU."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    monkeypatch.setattr(gpu_mod, "list_gpus",
                        lambda: [_gpu(0, "GPU-aaa"), _gpu(1, "GPU-bbb")])
    engine = create_engine(f"sqlite:///{tmp_path}/race.db")
    Base.metadata.create_all(engine, tables=[GpuLease.__table__])
    Maker = sessionmaker(bind=engine)

    thang: list[str] = []
    loi: list[str] = []
    khoa = threading.Lock()

    def chay(i):
        s = Maker()
        try:
            lease = gpu_lease.acquire(s, worker_id=f"w{i}", job_id=f"j{i}")
            if lease is not None:
                with khoa:
                    thang.append(lease.gpu_uuid)
        except Exception as exc:             # noqa: BLE001
            # KHÔNG nuốt: nuốt lỗi ở đây làm test xanh giả — luồng nào ném cũng
            # chỉ đơn giản là "không thắng", và cuộc đua coi như không xảy ra.
            # SQLite khoá ghi (`database is locked`) là đường chạy bình thường
            # của fixture này, mọi lỗi khác thì phải báo.
            if "locked" not in str(exc).lower():
                with khoa:
                    loi.append(f"{type(exc).__name__}: {exc}")
        finally:
            s.close()

    ts = [threading.Thread(target=chay, args=(i,)) for i in range(8)]
    for t in ts: t.start()
    for t in ts: t.join()

    assert loi == [], f"luồng ném lỗi ngoài dự kiến: {loi}"
    assert thang, "không luồng nào giành được GPU — fixture hỏng, test vô nghĩa"
    assert len(thang) == len(set(thang)), (
        f"cùng một GPU được cấp cho nhiều luồng: {thang}")
    assert len(thang) <= 2, f"cấp ra nhiều hơn số GPU thật: {thang}"


def test_khong_gianh_gpu_thieu_vram(db, monkeypatch):
    """Xin 12 GB mà card chỉ còn 2 GB thì phải từ chối, không cấp bừa rồi OOM."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-day", free_mb=2000)])
    assert gpu_lease.acquire(db, worker_id="w1", need_mb=12000) is None


def test_chua_lai_headroom_chu_khong_xin_sat_nut(db, monkeypatch):
    """Card còn đúng 6000 MB, job xin 6000 MB → vẫn phải từ chối.

    Xin sát dung lượng còn trống là công thức chắc chắn OOM: phân mảnh và phần
    driver chiếm luôn ăn thêm vài trăm MB.
    """
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-vua-du", free_mb=6000)])
    assert gpu_lease.acquire(db, worker_id="w1", need_mb=6000) is None
    assert gpu_lease.acquire(db, worker_id="w1", need_mb=6000 - gpu_lease.HEADROOM_MB) is not None


def test_tra_cho_xong_thi_worker_sau_dung_duoc(db, monkeypatch):
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-mot")])
    a = gpu_lease.acquire(db, worker_id="w1", job_id="ja")
    assert gpu_lease.acquire(db, worker_id="w2", job_id="jb") is None
    gpu_lease.release(db, a)
    assert gpu_lease.acquire(db, worker_id="w2", job_id="jb") is not None


def test_worker_chet_thi_gpu_duoc_thu_hoi(db, monkeypatch):
    """Không có bước này thì một worker sập sẽ khoá GPU vĩnh viễn."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-mot")])
    a = gpu_lease.acquire(db, worker_id="w-chet", job_id="ja")
    assert gpu_lease.acquire(db, worker_id="w2") is None

    a.heartbeat_at = gpu_lease._now() - timedelta(hours=2)   # giả worker đã chết
    db.commit()

    assert gpu_lease.reclaim_orphans(db) == 1
    assert gpu_lease.acquire(db, worker_id="w2") is not None


def test_dap_nhip_giu_gpu_khong_bi_cuop(db, monkeypatch):
    """Job chạy lâu nhưng còn đập nhịp thì KHÔNG được coi là mồ côi."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-mot")])
    a = gpu_lease.acquire(db, worker_id="w1", job_id="ja")
    a.heartbeat_at = gpu_lease._now() - timedelta(hours=2)
    db.commit()
    gpu_lease.heartbeat(db, a)                      # job báo còn sống
    assert gpu_lease.reclaim_orphans(db) == 0
    assert gpu_lease.acquire(db, worker_id="w2") is None


def test_khoi_with_luon_tra_cho_ke_ca_khi_handler_nem(db, monkeypatch):
    """Quên trả lease = GPU khoá 10 phút. Đường dùng mặc định phải an toàn."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [_gpu(0, "GPU-mot")])
    with pytest.raises(RuntimeError):
        with gpu_lease.hold(db, worker_id="w1", job_id="ja") as lease:
            assert lease is not None
            raise RuntimeError("handler vỡ giữa chừng")
    assert gpu_lease.acquire(db, worker_id="w2") is not None, (
        "handler ném xong mà GPU vẫn bị giữ")


def test_may_khong_co_gpu_van_chay_duoc(db, monkeypatch):
    """Máy phát triển không GPU là hợp lệ — trả None, không ném."""
    monkeypatch.setattr(gpu_mod, "list_gpus", lambda: [])
    assert gpu_lease.acquire(db, worker_id="w1") is None
    with gpu_lease.hold(db, worker_id="w1") as lease:
        assert lease is None


def test_neo_bang_uuid_chu_khong_bang_index(db, monkeypatch):
    """Index đổi khi cắm thêm card; lease ghi index sẽ trỏ nhầm card.

    Mô phỏng: giữ card có uuid GPU-bbb (đang là index 1), rồi cắm thêm một card
    khiến nó thành index 2. Lease vẫn phải chỉ đúng card cũ.
    """
    monkeypatch.setattr(gpu_mod, "list_gpus",
                        lambda: [_gpu(0, "GPU-aaa", free_mb=1000),
                                 _gpu(1, "GPU-bbb", free_mb=16000)])
    lease = gpu_lease.acquire(db, worker_id="w1", job_id="ja")
    assert lease.gpu_uuid == "GPU-bbb" and lease.gpu_index == 1

    # Cắm thêm card ở bus thấp hơn -> driver đánh lại số
    monkeypatch.setattr(gpu_mod, "list_gpus",
                        lambda: [_gpu(0, "GPU-moi"), _gpu(1, "GPU-aaa"),
                                 _gpu(2, "GPU-bbb")])
    assert gpu_lease.busy_uuids(db) == {"GPU-bbb"}, "lease phải bám UUID, không bám số"
    khac = gpu_lease.acquire(db, worker_id="w2", job_id="jb")
    assert khac.gpu_uuid != "GPU-bbb", "cấp trùng card đang bận vì đọc theo index"
