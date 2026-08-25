"""Ba đường đã viết ra mà chưa bao giờ chạy.

Bản chấm điểm trung thực (`AUDIT_API_2026-08-15.md` §4b) chỉ ra ba chỗ có code,
có mô tả, có cả test — nhưng **hàm thật chưa chạy lần nào**:

* ``job_runner._het_gio`` — mọi test đều `monkeypatch` nó đi, trong khi nó hoàn
  credit và gọi ``os._exit``;
* vòng cha giám sát và thay thế worker con đã chết — không có test nào;
* luồng xả metrics của tiến trình web — chỉ được xác minh thủ công một lần.

Hai trong ba là đường **phá huỷ hoặc vận hành**, tức đúng loại phải chạy thử
trước chứ không phải sau. Một hàm chưa chạy lần nào là một hàm chưa tồn tại về
mặt hành vi, dù nó nằm sẵn trong file.

Cả ba đều chạy **tiến trình thật** ở đây, vì cả ba đều chỉ có ý nghĩa khi có một
tiến trình để kết thúc hoặc để thay thế.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ── 1. Job vượt trần: hoàn tiền, rồi kết thúc tiến trình ─────────────────────

KICH_BAN_HET_GIO = '''
import os, sys, uuid
sys.path.insert(0, r"{root}")
os.environ["LTT_DATABASE_URL"] = "sqlite:///{db}"
os.environ["LTT_DATA_DIR"] = r"{data}"

import platform_core.models  # noqa
from platform_core.db import Base, get_engine, get_session
Base.metadata.create_all(get_engine())

from datetime import datetime, timezone
from platform_core import credit
from platform_core.models import JOB_RUNNING, Job
from platform_core.users import tao_nguoi_dung

gen = get_session(); db = next(gen)
u = tao_nguoi_dung(db, email="hetgio@example.com",
                   password="a-good-password-12", is_verified=True)
db.flush()
credit.cap_tay(db, u.id, 100, by="test")
job = Job(id="{job_id}", user_id=u.id, app_slug="thumbnail",
          job_type="thumbnail.generate", params={{}}, status=JOB_RUNNING,
          max_attempts=3, attempts=0,
          created_at=datetime.now(timezone.utc),
          next_run_at=datetime.now(timezone.utc))
db.add(job); db.flush()
credit.giu_cho(db, u.id, 30, job.id)
db.commit()

from platform_core import job_runner
job_runner._het_gio("{job_id}", "thumbnail.generate", 60)
print("KHONG BAO GIO TOI DAY")   # `_het_gio` phải kết thúc tiến trình
'''


def test_job_vuot_tran_hoan_tien_roi_ket_thuc_tien_trinh(tmp_path):
    """Chạy `_het_gio` THẬT, trong một tiến trình có thể chết.

    Trước đây mọi test đều thay nó bằng một hàm đếm, nên phần quan trọng nhất —
    ghi trạng thái xuống CSDL **trước** khi thoát, và hoàn credit — chưa bao giờ
    được kiểm. Nếu thứ tự đó sai thì khách mất tiền cho một job không bao giờ
    hoàn tất, và không ai biết vì tiến trình đã biến mất.
    """
    db_file = (tmp_path / "hetgio.db").as_posix()
    job_id = str(uuid.uuid4())
    script = tmp_path / "chay.py"
    script.write_text(
        KICH_BAN_HET_GIO.format(root=ROOT, db=db_file, data=tmp_path / "data",
                                job_id=job_id),
        encoding="utf-8")

    ra = subprocess.run([sys.executable, str(script)], capture_output=True,
                        text=True, timeout=180)

    assert ra.returncode == 3, (
        f"`_het_gio` phải kết thúc tiến trình với mã 3, nhận {ra.returncode}. "
        f"{ra.stdout[-300:]} {ra.stderr[-500:]}")
    assert "KHONG BAO GIO TOI DAY" not in ra.stdout, (
        "tiến trình vẫn chạy tiếp sau khi hết giờ — slot không được giải phóng")

    # Trạng thái phải đã bền vững TRƯỚC khi tiến trình biến mất.
    import sqlalchemy as sa

    engine = sa.create_engine(f"sqlite:///{db_file}", future=True)
    with engine.connect() as conn:
        status, loi = conn.execute(sa.text(
            "SELECT status, error FROM jobs WHERE id = :i"),
            {"i": job_id}).one()
        assert status == "error", f"job kết thúc ở trạng thái {status!r}"
        assert "tran thoi gian" in (loi or "").lower()

        # Credit đã giữ phải được trả lại: job không bao giờ cho ra kết quả.
        tong = conn.execute(sa.text(
            "SELECT COALESCE(SUM(delta), 0) FROM credit_entries "
            "WHERE job_id = :i"), {"i": job_id}).scalar_one()
        assert tong == 0, (
            f"credit ròng của job hết giờ là {tong}, phải là 0 — khách không "
            f"được trả tiền cho việc không bao giờ hoàn tất")
    engine.dispose()


def test_job_het_gio_khong_duoc_xep_chay_lai(tmp_path):
    """Cùng đường chạy trên, kiểm phần `retry=False`.

    Thử lại một job treo chỉ tiêu thêm một slot rồi treo tiếp — ba lần.
    """
    db_file = (tmp_path / "hetgio2.db").as_posix()
    job_id = str(uuid.uuid4())
    script = tmp_path / "chay2.py"
    script.write_text(
        KICH_BAN_HET_GIO.format(root=ROOT, db=db_file, data=tmp_path / "data",
                                job_id=job_id),
        encoding="utf-8")
    subprocess.run([sys.executable, str(script)], capture_output=True,
                   text=True, timeout=180)

    import sqlalchemy as sa

    engine = sa.create_engine(f"sqlite:///{db_file}", future=True)
    with engine.connect() as conn:
        status, lan = conn.execute(sa.text(
            "SELECT status, attempts FROM jobs WHERE id = :i"),
            {"i": job_id}).one()
    engine.dispose()

    assert status == "error"
    assert lan == 1, f"job hết giờ bị tính {lan} lượt — nó không được thử lại"


# ── 2. Cha thay thế con đã chết ──────────────────────────────────────────────

@pytest.mark.slow
def test_cha_thay_the_worker_con_da_chet(tmp_path):
    """Giết một tiến trình con thật, xem cha có dựng lại không.

    Trước thay đổi này cha chỉ `join()`: một worker con chết vì bất cứ lý do gì
    sẽ biến mất tới lần khởi động lại dịch vụ, đội hình teo dần, và không ai được
    báo. Với trần thời gian chạy (job treo **cố ý** kết thúc tiến trình của nó),
    tính chất này chuyển từ "nên có" thành "bắt buộc" — không có nó thì mỗi job
    treo là mất vĩnh viễn một worker.
    """
    import psutil  # noqa: F401 — chỉ để bỏ qua sạch nếu máy không có

    env = dict(os.environ)
    env["LTT_DATABASE_URL"] = f"sqlite:///{(tmp_path / 'sup.db').as_posix()}"
    env["LTT_DATA_DIR"] = str(tmp_path / "data")
    env["LTT_API_KEY_PEPPER"] = "supervise-pepper-" + "s" * 40
    env["LTT_WORKER_POOLS"] = "api:2"
    env["LTT_FILE_LOGGING"] = "0"

    # Ghi ra FILE chứ không phải `PIPE`. Với `PIPE` mà không ai đọc, ống 64 KB
    # đầy lên là tiến trình cha **chặn ngay tại lệnh ghi** — vòng giám sát đứng,
    # và test kết luận "cha không thay thế con" trong khi cha chỉ đang bị bịt
    # miệng. Chính test này đã dính đúng bẫy đó một lần.
    log_file = tmp_path / "worker.log"
    fh = log_file.open("w", encoding="utf-8", errors="replace")
    cha = subprocess.Popen([sys.executable, "-u", "job_worker.py"],
                           cwd=str(ROOT), env=env, stdout=fh,
                           stderr=subprocess.STDOUT, text=True)
    try:
        import psutil

        cha_ps = psutil.Process(cha.pid)
        con = []
        for _ in range(60):                 # đợi hai con khởi động
            con = cha_ps.children()
            if len(con) >= 2:
                break
            time.sleep(1.0)
        assert len(con) >= 2, f"cha chỉ đẻ {len(con)} con, mong đợi 2"

        nan_nhan = con[0]
        nan_nhan.kill()
        nan_nhan.wait(timeout=30)

        for _ in range(60):                 # đợi cha thay thế
            con_moi = [c for c in cha_ps.children() if c.is_running()]
            if len(con_moi) >= 2 and nan_nhan.pid not in {c.pid for c in con_moi}:
                break
            time.sleep(1.0)
        else:
            pytest.fail("cha không thay thế worker con đã chết")
    finally:
        cha.terminate()
        try:
            cha.wait(timeout=30)
        except subprocess.TimeoutExpired:
            cha.kill()
        fh.close()


# ── 3. Luồng xả metrics của tiến trình web ──────────────────────────────────

def test_tien_trinh_web_that_su_xa_bo_dem_xuong_csdl(tmp_path, monkeypatch):
    """Luồng nền của `server/app.py`, chạy thật qua vòng đời ứng dụng.

    Phần lớn con số đáng xem — request, lỗi xác thực, lần bị chặn nhịp — phát
    sinh ở tiến trình web. Trước khi có luồng này chúng **không bao giờ rời khỏi
    tiến trình**, nên trang vận hành cộng lại được mọi thứ trừ chính thứ nó cần
    nhất. Xác minh thủ công một lần không phải là một bánh cóc.
    """
    import sqlalchemy as sa
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'webflush.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_API_KEY_PEPPER", "webflush-pepper-" + "w" * 40)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    from platform_core.public_api import metrics
    from platform_core.public_api.tables import ApiMetricSample

    Base.metadata.create_all(get_engine())
    metrics.reset()

    import server.app as app_mod
    monkeypatch.setattr(app_mod, "METRICS_FLUSH_INTERVAL_S", 0.3)

    app = app_mod.create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "webflush-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
    })

    with TestClient(app):
        metrics.increment("requests", 7)
        metrics.increment("auth_failure", 2)
        for _ in range(40):
            with get_engine().connect() as conn:
                co = conn.execute(sa.text(
                    "SELECT COUNT(*) FROM api_metric_samples")).scalar_one()
            if co:
                break
            time.sleep(0.25)

    with get_engine().connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT process, name, value FROM api_metric_samples")).all()

    assert rows, "luồng xả của tiến trình web không ghi được dòng nào"
    theo_ten = {r.name: r.value for r in rows}
    assert theo_ten.get("requests") == 7
    assert theo_ten.get("auth_failure") == 2
    assert all(r.process.startswith(metrics.WEB_PREFIX) for r in rows), (
        "số của tiến trình web bị ghi dưới tiền tố worker — trang vận hành sẽ "
        "đếm nhầm số tiến trình web, tức mất chính cái cảnh báo nó sinh ra để đưa")

    dbmod.reset_engine()
