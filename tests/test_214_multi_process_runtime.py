"""Nhiều tiến trình worker thật, một CSDL: có gì xảy ra hai lần không?

Ba lỗi P0 của bản audit 2026-08-15 lọt qua hơn ba nghìn test vì **chưa từng có
gì chạy hai tiến trình worker cùng lúc trên một CSDL**. Có test chống gửi
webhook trùng, và nó *đúng* — nhưng nó chạy worker tuần tự trong một tiến trình,
nên nó khẳng định một điều không ai nghi ngờ.

File này là phép đo còn thiếu. Nó đẻ **tiến trình thật** (không phải luồng,
không phải giả lập), cho chúng chạy đúng vòng `run_forever` của production, rồi
hỏi một câu duy nhất: *có thứ gì xảy ra hai lần không?*

**Phải chạy trên PostgreSQL.** SQLite khoá cả CSDL khi ghi, nên nó **che đúng
những cuộc đua này**: bản dựng lại lỗi gửi trùng trông như vô hại chỉ vì SQLite
đã chặn lượt ghi thứ hai, và suýt nữa điều đó được đọc thành "có bảo vệ". Một
test xanh vì lý do sai còn tệ hơn không có test.

Ba bất biến dưới đây **đỏ khi file này được viết**. Đó là mục đích: có một phép
đo khách quan cho "đã sửa xong", thay vì niềm tin rằng đã sửa.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import pathlib
import tempfile
import time
import uuid

import pytest
import sqlalchemy as sa

from tests.pg_scratch import scratch_url, skip_without_postgres

PG_URL = scratch_url()
postgres_only = skip_without_postgres()

PEPPER = "multiproc-pepper-" + "m" * 40
WORKERS = 3
RUN_SECONDS = 6.0

#: Mỗi lần gửi webhook ghi một dòng vào đây. Dùng file chứ không dùng biến vì
#: người đếm và người gửi là hai tiến trình khác nhau.
SEND_LOG = "ltt-multiproc-sends.jsonl"


# ── Tiến trình con ───────────────────────────────────────────────────────────

def _child(url: str, data_dir: str, send_log: str, seconds: float,
           index: int) -> None:
    """Thân MỘT tiến trình worker. Ở cấp module để Windows `spawn` được.

    Nó dựng môi trường **từ tham số truyền vào**, không thừa hưởng — một tiến
    trình con nhặt nhầm `LTT_DATABASE_URL` của máy chủ sẽ giành job thật của
    khách hàng, nên đường đó phải bị bịt bằng thiết kế chứ không bằng cẩn thận.
    """
    os.environ["LTT_DATABASE_URL"] = url
    os.environ["LTT_DATA_DIR"] = data_dir
    os.environ["LTT_API_KEY_PEPPER"] = PEPPER
    os.environ["GEMINI_API_KEY"] = "multiproc-stub-not-used"
    os.environ["LTT_FILE_LOGGING"] = "0"

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    # Nhà cung cấp bị chặn: test này không được tiêu tiền hay gọi ra ngoài.
    #
    # 🔴 Pha 06.3: gán thẳng chứ không `monkeypatch` vì đoạn này chạy trong
    #    TIẾN TRÌNH CON — ở đó không có fixture nào. Ranh giới vá nay là
    #    `_dieu_phoi()`; `_goi_gemini` đã bị xoá cùng động cơ Gemini.
    import apps.thumbnail.jobs as thumbnail_jobs
    from tests.gia_dieu_phoi_anh import DieuPhoiGia
    thumbnail_jobs._dieu_phoi = lambda: DieuPhoiGia()

    # Người gửi webhook được thay bằng một cái đếm. Mỗi lần gửi ghi một dòng —
    # đó là thứ duy nhất chứng minh được "gửi hai lần", vì hai tiến trình ghi
    # đè cùng một giá trị lên hàng delivery thì bảng vẫn hiện attempts=1.
    from platform_core.public_api import delivery as delivery_mod

    def _dem(subscription, row) -> int:
        with open(send_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"delivery": row.id, "worker": index,
                                 "pid": os.getpid()}) + "\n")
        return 200

    delivery_mod.send_delivery = _dem
    import platform_core.public_api.outbox as outbox_mod
    outbox_mod.send_delivery = _dem       # nếu module đã import sẵn tên đó

    from platform_core.job_runner import run_forever

    han = time.monotonic() + float(seconds)
    run_forever(f"multiproc-{index}-{os.getpid()}",
                stop=lambda: time.monotonic() >= han)


# ── Dựng dữ liệu ─────────────────────────────────────────────────────────────

@pytest.fixture()
def scratch(tmp_path):
    """CSDL sạch, thư mục dữ liệu riêng, và dọn sau khi xong."""
    engine = sa.create_engine(PG_URL, future=True)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    os.environ["LTT_DATABASE_URL"] = PG_URL
    os.environ["LTT_DATA_DIR"] = str(tmp_path / "data")
    os.environ["LTT_API_KEY_PEPPER"] = PEPPER
    import platform_core.models  # noqa: F401
    from platform_core.db import Base

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    dbmod.reset_engine()
    # Job anh gianh `anh_3090` tu dual-model 5.5, va luat 0 fail-closed: khong co
    # dong `gpu_residency` thi worker chi tra job ve hang doi. Cac job o day la
    # `thumbnail.generate`. Ly do day du: `tests/conftest.py::mo_cu_tru_3090`.
    from platform_core.llm import residency as _residency

    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090(_residency.ANH)

    send_log = pathlib.Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}-{SEND_LOG}"
    try:
        yield {"engine": engine, "data_dir": str(tmp_path / "data"),
               "send_log": str(send_log)}
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
        dbmod.reset_engine()
        send_log.unlink(missing_ok=True)


def _session():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _seed_account(credits: int = 10_000) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"mp-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12", is_verified=True)
        db.flush()
        credit.cap_tay(db, user.id, credits, by="multiproc-test")
        db.commit()
        return user.id
    finally:
        _close(gen)


def _seed_jobs(user_id: str, count: int) -> list:
    """Job thật qua đúng đường submit của nền tảng."""
    from platform_core import job_submit

    ids = []
    gen, db = _session()
    try:
        for i in range(count):
            job = job_submit.submit_with_credit(
                db, user_id=user_id, app_slug="thumbnail",
                job_type="thumbnail.generate",
                params={"topic": f"multiproc {i}", "count": 1})
            ids.append(job.id)
        db.commit()
    finally:
        _close(gen)
    return ids


def _seed_deliveries(user_id: str, count: int) -> list:
    """Delivery đang chờ, đến hạn ngay."""
    from datetime import datetime, timezone

    from platform_core.public_api import outbox
    from platform_core.public_api.tables import (WebhookDelivery,
                                                 WebhookSubscription)

    now = datetime.now(timezone.utc)
    ids = []
    gen, db = _session()
    try:
        sub = WebhookSubscription(
            id=uuid.uuid4().hex, user_id=user_id,
            url="https://example.com/multiproc", events=["job.succeeded"],
            enabled=True, secret_enc="enc:" + "s" * 40)
        db.add(sub)
        db.flush()
        for _ in range(count):
            row = WebhookDelivery(
                id=uuid.uuid4().hex, subscription_id=sub.id, user_id=user_id,
                event_id=uuid.uuid4().hex, event_type="job.succeeded",
                job_id="", payload={"job_id": "", "tool": "image.thumbnail",
                                    "status": "succeeded", "mode": "live"},
                status=outbox.WEBHOOK_PENDING, attempts=0,
                next_attempt_at=now, created_at=now)
            db.add(row)
            ids.append(row.id)
        db.commit()
    finally:
        _close(gen)
    return ids


def _run_workers(scratch, seconds: float = RUN_SECONDS) -> None:
    """N tiến trình worker thật, chạy đồng thời, rồi dừng êm."""
    ctx = multiprocessing.get_context("spawn")
    # `daemon=True` khong cuu duoc moi truong hop, nhung no cuu truong hop HAY
    # XAY RA NHAT: cha thoat binh thuong hoac thoat vi ngoai le. Luc do Python
    # tu ket lieu con daemon. Chi khi cha bi SIGKILL thi khong gi giup duoc —
    # va do la ly do `gate.py` don xac truoc moi luot.
    procs = [ctx.Process(target=_child,
                         args=(PG_URL, scratch["data_dir"],
                               scratch["send_log"], seconds, i),
                         name=f"mp-worker-{i}", daemon=True)
             for i in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=seconds + 60)
        if p.is_alive():
            p.terminate()
            p.join(timeout=10)

    # Một tiến trình con chết lúc khởi động sẽ làm MỌI bất biến dưới đây xanh
    # một cách vô nghĩa: không có gì chạy thì cũng không có gì xảy ra hai lần.
    chet = [(p.name, p.exitcode) for p in procs if p.exitcode not in (0, None)]
    assert not chet, f"worker chết bất thường: {chet}"


def _sends(scratch) -> list:
    path = pathlib.Path(scratch["send_log"])
    if not path.exists():
        return []
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ── Bất biến ─────────────────────────────────────────────────────────────────

@postgres_only
def test_moi_job_chay_dung_mot_lan(scratch):
    """Hàng đợi job vốn đã đúng — đây là chỗ chứng minh nó đúng thật.

    `claim()` dùng `FOR UPDATE SKIP LOCKED`, nên bất biến này phải xanh ngay từ
    đầu. Nó ở đây để khi một bất biến khác đỏ, ta biết bộ khung không hỏng.
    """
    from platform_core.models import JOB_DONE, Job

    user_id = _seed_account()
    ids = _seed_jobs(user_id, 9)
    _run_workers(scratch)

    gen, db = _session()
    try:
        rows = db.execute(sa.select(Job).where(Job.id.in_(ids))).scalars().all()
        assert len(rows) == len(ids)
        chua_xong = [r.id for r in rows if r.status != JOB_DONE]
        assert not chua_xong, f"job chưa xong: {chua_xong}"
        chay_lai = [(r.id, r.attempts) for r in rows if int(r.attempts or 0) > 1]
        assert not chay_lai, f"job chạy nhiều hơn một lượt: {chay_lai}"
    finally:
        _close(gen)


@postgres_only
def test_moi_webhook_gui_dung_mot_lan(scratch):
    """Hôm nay ĐỎ: `claim_due()` là SELECT trần và gửi trước khi ghi.

    Đếm bằng file chứ không bằng cột `attempts`: hai tiến trình ghi đè **cùng
    một giá trị** lên hàng delivery, nên bảng vẫn hiện `attempts=1` trong khi
    khách đã nhận hai callback. Hỏng im lặng chỉ đếm được ở phía người gửi.
    """
    user_id = _seed_account()
    ids = _seed_deliveries(user_id, 6)
    _run_workers(scratch)

    sends = _sends(scratch)
    theo_delivery: dict = {}
    for row in sends:
        theo_delivery[row["delivery"]] = theo_delivery.get(row["delivery"], 0) + 1

    gui_trung = {k: v for k, v in theo_delivery.items() if v > 1}
    assert not gui_trung, (
        f"{len(gui_trung)}/{len(ids)} delivery được gửi nhiều lần: "
        f"{list(gui_trung.items())[:3]}")
    assert set(theo_delivery) == set(ids), (
        f"gửi {len(theo_delivery)} delivery, dựng {len(ids)}")


@postgres_only
def test_chi_mot_tien_trinh_chay_vong_bao_tri(scratch):
    """Hôm nay ĐỎ: chưa có cơ chế nào chọn một tiến trình chạy việc nền.

    Đo gián tiếp qua thứ việc nền để lại dấu vết: nếu N tiến trình cùng quét thì
    N lượt gửi webhook xảy ra trong cùng một khoảnh khắc. Khi đã có lease, mọi
    lượt gửi phải đến từ **một pid duy nhất**.
    """
    user_id = _seed_account()
    _seed_deliveries(user_id, 4)
    _run_workers(scratch)

    pids = {row["pid"] for row in _sends(scratch)}
    assert len(pids) <= 1, (
        f"{len(pids)} tiến trình cùng chạy vòng bảo trì: {sorted(pids)}")


@postgres_only
def test_canh_bao_khong_bi_nhan_doi(scratch):
    """Hôm nay ĐỎ: cooldown là đọc-rồi-ghi, index dedupe không UNIQUE.

    Hai tiến trình quét cùng lúc đều thấy "chưa có cảnh báo nào gần đây" và đều
    ghi. Khách nhận email trùng — thứ họ **thấy được**.
    """
    from platform_core.public_api import budgets
    from platform_core.public_api.tables import ApiNotification

    user_id = _seed_account()
    gen, db = _session()
    try:
        budgets.create(db, user_id=user_id, amount=10, period="month",
                       scope="account", thresholds=(50,), hard_cap=False)
        db.commit()
    finally:
        _close(gen)

    _seed_jobs(user_id, 3)          # tiêu tiền để vượt ngưỡng
    _run_workers(scratch)

    gen, db = _session()
    try:
        rows = db.execute(sa.select(ApiNotification).where(
            ApiNotification.user_id == user_id)).scalars().all()
        theo_khoa: dict = {}
        for row in rows:
            khoa = (row.kind, row.subject)
            theo_khoa[khoa] = theo_khoa.get(khoa, 0) + 1
        trung = {k: v for k, v in theo_khoa.items() if v > 1}
        assert not trung, f"cảnh báo bị nhân đôi: {trung}"
    finally:
        _close(gen)


@postgres_only
def test_so_credit_van_khop_sau_khi_chay_dong_thoi(scratch):
    """Tiền là thứ không được sai dù có bao nhiêu tiến trình.

    `usage.reconcile` đã dùng ở `test_193` cho một tiến trình; đây là cùng bất
    biến đó dưới tranh chấp thật.
    """
    from platform_core.public_api import usage

    user_id = _seed_account()
    _seed_jobs(user_id, 9)
    _run_workers(scratch)

    gen, db = _session()
    try:
        bao_cao = usage.reconcile(db, user_id=user_id)
        assert bao_cao["ok"] is True, bao_cao
    finally:
        _close(gen)


@postgres_only
def test_don_du_lieu_chay_dong_thoi_khong_lam_hong_gi(scratch):
    """Sáu vòng dọn của EXT-19 chạy trong N tiến trình cùng lúc.

    Xoá là thao tác lặp lại được, nên cái cần chứng minh không phải "chỉ chạy
    một lần" mà là **không tiến trình nào chết** vì tranh chấp — một vòng dọn
    làm sập worker sẽ kéo theo cả job của khách.
    """
    from platform_core.models import JOB_DONE, Job

    user_id = _seed_account()
    ids = _seed_jobs(user_id, 6)
    _seed_deliveries(user_id, 3)
    _run_workers(scratch)

    gen, db = _session()
    try:
        xong = db.execute(sa.select(sa.func.count(Job.id)).where(
            Job.id.in_(ids), Job.status == JOB_DONE)).scalar_one()
        assert xong == len(ids), (
            f"chỉ {xong}/{len(ids)} job xong — có worker chết giữa chừng")
    finally:
        _close(gen)


def _child_chi_gui(url: str, data_dir: str, send_log: str, lan: int,
                   index: int) -> None:
    """Tiến trình chỉ gọi thẳng `deliver_due`, KHÔNG qua lease bảo trì."""
    import time as _time

    os.environ["LTT_DATABASE_URL"] = url
    os.environ["LTT_DATA_DIR"] = data_dir
    os.environ["LTT_API_KEY_PEPPER"] = PEPPER
    os.environ["LTT_FILE_LOGGING"] = "0"

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import get_session
    from platform_core.public_api import delivery as delivery_mod, outbox

    def _dem(subscription, row) -> int:
        with open(send_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"delivery": row.id, "worker": index,
                                 "pid": os.getpid()}) + "\n")
        # Gửi thật thì mất vài chục mili-giây; độ trễ đó chính là cửa sổ mà một
        # `claim_due` chỉ-đọc để hở cho tiến trình khác đọc cùng một hàng.
        _time.sleep(0.05)
        return 200

    delivery_mod.send_delivery = _dem

    for _ in range(lan):
        gen = get_session()
        db = next(gen)
        try:
            outbox.deliver_due(db, sender=_dem)
            db.commit()
        except Exception:                   # noqa: BLE001
            db.rollback()
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


@postgres_only
def test_gui_webhook_van_dung_mot_lan_khi_lease_khong_can_thiep(scratch):
    """Lớp thứ hai: outbox phải tự đúng, không nhờ lease.

    Bất biến ở trên xanh **cả khi `claim_due` còn là SELECT trần**, vì lease chỉ
    cho một tiến trình chạy việc nền nên không ai đọc cùng lúc với ai. Lease che
    mất lỗi — đúng như dự đoán khi thiết kế hai lớp, và cũng là lý do một test
    xanh ở đó không chứng minh được gì về outbox.

    Test này bỏ qua lease và gọi thẳng `deliver_due` từ nhiều tiến trình, tức
    dựng lại đúng tình huống "chính sách hỏng hoặc bị ai đó chỉnh": tính đúng
    đắn có còn không.
    """
    ctx = multiprocessing.get_context("spawn")
    user_id = _seed_account()
    ids = _seed_deliveries(user_id, 8)

    procs = [ctx.Process(target=_child_chi_gui,
                         args=(PG_URL, scratch["data_dir"],
                               scratch["send_log"], 4, i),
                         name=f"mp-gui-{i}")
             for i in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=120)
        if p.is_alive():
            p.terminate()
            p.join(timeout=10)

    chet = [(p.name, p.exitcode) for p in procs if p.exitcode not in (0, None)]
    assert not chet, f"tiến trình gửi chết bất thường: {chet}"

    theo_delivery: dict = {}
    for row in _sends(scratch):
        theo_delivery[row["delivery"]] = theo_delivery.get(row["delivery"], 0) + 1

    trung = {k: v for k, v in theo_delivery.items() if v > 1}
    assert not trung, (
        f"{len(trung)}/{len(ids)} delivery được gửi nhiều lần: "
        f"{list(trung.items())[:3]}")
