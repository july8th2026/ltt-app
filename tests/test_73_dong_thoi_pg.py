"""
W0.1/W0.2 — kiểm ĐỒNG THỜI trên PostgreSQL thật (SQLite bỏ qua FOR UPDATE và
pg_advisory_lock nên KHÔNG chứng minh được gì về race). Các test này là bằng
chứng cho hai bất biến tiền/hàng-đợi mà audit 2026-07-31 nêu là chưa được test:

1. `credit.giu_cho` không double-spend khi nhiều request song song của cùng user;
2. `jobs.claim` (FOR UPDATE SKIP LOCKED) không để hai worker nhặt trùng một job.

Chạy: đặt `LTT_TEST_DATABASE_URL` trỏ tới một database PostgreSQL DÙNG RIÊNG cho
test (test này DROP/CREATE mọi bảng). Không đặt → cả file tự bỏ qua, nên
`pytest` trên máy phát triển không có PostgreSQL vẫn xanh.
"""
from __future__ import annotations

import os
import threading

import pytest

PG_URL = os.environ.get("LTT_TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not PG_URL,
    reason="Can LTT_TEST_DATABASE_URL (PostgreSQL rieng) de kiem dong thoi.",
)


@pytest.fixture()
def Sess():
    """Sessionmaker trỏ tới DB test PostgreSQL, bảng dựng sạch mỗi test."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import platform_core.models  # noqa: F401 — đăng ký bảng vào Base
    from platform_core.db import Base

    engine = create_engine(PG_URL, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield maker
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_giu_cho_khong_double_spend_dong_thoi(Sess):
    """Số dư 10, tám request song song mỗi cái giữ 10: đúng MỘT thành công,
    số dư cuối = 0 (không âm). Không có advisory lock thì nhiều cái cùng qua và
    số dư âm — đây chính là lỗ hổng P0-1."""
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    s = Sess()
    u = tao_nguoi_dung(s, email="race@x.com", password="matkhau-tot-12")
    s.commit()
    uid = u.id
    credit.cap_tay(s, uid, 10, by="test")
    s.commit()
    s.close()

    N = 8
    ket_qua: list[str] = []
    barrier = threading.Barrier(N)

    def worker(i: int) -> None:
        ss = Sess()
        try:
            barrier.wait()  # ép tất cả vào giu_cho gần như cùng lúc
            credit.giu_cho(ss, uid, 10, job_id=f"job-{i}")
            ss.commit()
            ket_qua.append("ok")
        except credit.ThieuCreditError:
            ss.rollback()
            ket_qua.append("thieu")
        except Exception as e:  # noqa: BLE001 — ghi lại để chẩn đoán nếu vỡ
            ss.rollback()
            ket_qua.append(f"err:{type(e).__name__}:{e}")
        finally:
            ss.close()

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    assert ket_qua.count("ok") == 1, ket_qua        # đúng một lần giữ được
    s2 = Sess()
    try:
        assert credit.so_du(s2, uid) == 0            # không âm, không mất tiền
    finally:
        s2.close()


def test_claim_khong_nhac_trung_hai_worker(Sess):
    """Hàng đợi 20 job, hai worker nhặt song song: mỗi job đúng một worker lấy,
    tổng đúng 20, không trùng. Chứng minh FOR UPDATE SKIP LOCKED (P0 hàng đợi)."""
    from platform_core import jobs
    from platform_core.users import tao_nguoi_dung

    s = Sess()
    u = tao_nguoi_dung(s, email="q@x.com", password="matkhau-tot-12")
    s.commit()
    uid = u.id
    N = 20
    for i in range(N):
        jobs.submit(s, user_id=uid, app_slug="demo", job_type="demo.reverse",
                    params={"i": i})
    s.commit()
    s.close()

    lay: dict[str, list[str]] = {"w1": [], "w2": []}
    start = threading.Barrier(2)

    def worker(name: str) -> None:
        start.wait()
        while True:
            ss = Sess()
            try:
                job = jobs.claim(ss, worker_id=name)
                if job is None:
                    ss.commit()
                    ss.close()
                    break
                lay[name].append(job.id)
                ss.commit()      # giữ trạng thái running -> không bị nhặt lại
            finally:
                ss.close()

    ts = [threading.Thread(target=worker, args=(n,)) for n in ("w1", "w2")]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    tat_ca = lay["w1"] + lay["w2"]
    assert len(tat_ca) == N                 # nhặt hết
    assert len(set(tat_ca)) == N            # không job nào bị nhặt hai lần
