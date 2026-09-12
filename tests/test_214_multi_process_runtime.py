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
#: Thoi luong chay cho ca KHONG cho theo dieu kien. Giu 6,0 nhu truoc 12/09 —
#: nam ca ay do nhung thu xay ra TRONG khi worker chay (khong nhan doi, khong
#: chet), khong doi hang phai rut can, nen chung khong can lau hon.
#:
#: ⛔ Ca nao KHANG DINH "xong het" thi KHONG duoc dung con so nay lam thoi luong:
#:    truyen `xong=` va mot tran rong (`TRAN_CHO_S`). Do chinh la khuyet dat da
#:    lam buoc gate nay do: dung worker bang dong ho roi khang dinh cong viec da
#:    xong. Do bon lan lien tiep cung cau hinh: 2/9 -> 5/9 -> 9/9 -> 5/9.
RUN_SECONDS = 6.0

#: Tran cho ca CO dieu kien dung. Khong phai thoi luong: test thoat ngay khi
#: `xong()` dung, nen so lon o day khong lam gate cham — no chi giu cho mot loi
#: that khoi bien thanh mot lan treo vo han.
#:
#: 📈 Do 12/09: dat tran nay lam THOI LUONG cho ca bay ca dua buoc gate tu 145 s
#:    len 622 s. Tran phai thuoc ve LOI GOI biet cho, khong thuoc ve moi nguoi.
TRAN_CHO_S = 90.0

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

    # 🔴 BACK-OFF CỦA PRODUCTION LÀM PHÉP KIỂM NÀY MẤT NGHĨA, nên vá TRONG
    #    tiến trình con — cùng idiom với hai bản vá ở trên, và cùng lý do: ở đây
    #    không có fixture nào.
    #
    #    Từ dual-model 5.5, `thumbnail.generate` giành `anh_3090` với **một** suất
    #    (D01 B: hai model ảnh cùng lúc trên 3090 là một lần OOM). Job bị từ chối
    #    đi qua `_tra_ve_hang_doi` và nằm chờ `GPU_RETRY_DELAY_S` = **20 giây**.
    #    Chín job × một suất × 20 giây ≈ 160 giây để rút cạn — trong khi cửa sổ
    #    của phép kiểm là 6 giây. Đo 12/09: 6 giây chỉ đủ cho 2 job.
    #
    # ⭐ Thứ phép kiểm này đo là **"mỗi job chạy đúng một lần"** — tính chất của
    #    `claim()` + `SKIP LOCKED`, không phải của back-off. Nên nó cần CHÍN job
    #    cùng bị tranh, không cần chúng cách nhau 20 giây.
    #
    # ⛔ KHÔNG hạ `GPU_RETRY_DELAY_S` trong mã sản phẩm để phép kiểm này xanh:
    #    20 giây được chọn cho job GPU dài hàng phút, và quay vòng dày hơn thì
    #    đốt CPU với CSDL. Vá ở đây, chỉ trong tiến trình con của test.
    import platform_core.job_runner as _jr
    _jr.GPU_RETRY_DELAY_S = 1

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


def _con_lai(ids) -> int:
    """Bao nhiêu job trong `ids` CHƯA xong. Dùng làm điều kiện dừng của worker.

    ⚠️ Mở phiên riêng mỗi lần hỏi: phiên của test đã đọc xong ảnh chụp của nó,
       còn worker đang ghi ở tiến trình khác — hỏi lại bằng phiên cũ là đọc lại
       đúng ảnh chụp cũ và vòng chờ sẽ không bao giờ thấy việc xong.
    """
    from platform_core.models import JOB_DONE, Job

    gen, db = _session()
    try:
        return int(db.execute(sa.select(sa.func.count(Job.id)).where(
            Job.id.in_(list(ids)), Job.status != JOB_DONE)).scalar_one())
    finally:
        _close(gen)


def _run_workers(scratch, seconds: float = RUN_SECONDS, *, xong=None) -> None:
    """N tiến trình worker thật, chạy đồng thời, rồi dừng êm.

    🔴 `xong` KHÔNG phải một tiện nghi — nó là thứ giữ phép kiểm khỏi flaky.

       Bản đầu dừng worker bằng **đồng hồ treo tường** rồi khẳng định "cả chín
       job đã xong". Hai mệnh đề ấy không có quan hệ nhân quả: một thay đổi
       thông lượng bất kỳ là tỉ lệ xong đổi. Đo 12/09, cùng cấu hình, bốn lượt:
       **2/9 → 5/9 → 9/9 → 5/9**.

       Thứ làm thông lượng đổi là một quyết định **đúng**: dual-model 5.5 đưa job
       ảnh về **một** suất (D01 B — hai model ảnh cùng lúc trên 3090 là một lần
       OOM), nên chín job chạy **nối tiếp**. Cửa sổ 6 giây mã hoá mức song song
       cũ, và nới nó chỉ dời quả bom sang lần đổi thông lượng kế tiếp.

    ⭐ Tài liệu pytest nói thẳng điều phải làm ở đây: *"Make sure to eventually
       **wait on** any spawned threads — for example at the end of a test, or
       during the teardown of a fixture"*, và flaky thường nghĩa là *"the test
       relies on some system state that is not being appropriately controlled"*.
       Thực hành phổ biến cho cùng hình dạng: **poll theo điều kiện + timeout**
       thay cho một hạn chót cố định.

    ⇒ `xong()` trả `True` khi công việc đã xong ⇒ dừng ngay. `seconds` còn lại
      là **trần an toàn**, không phải thời lượng chạy: máy khoẻ thì test nhanh
      hơn, máy chậm thì vẫn đúng.

    ⛔ Đừng quay lại kiểu "chạy đủ N giây rồi khẳng định": nó xanh đúng tới lần
       ai đó đổi số suất, thêm một bước vào vòng bảo trì, hay chạy trên máy bận.
    """
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

    if xong is not None:
        # Chờ CÔNG VIỆC, không chờ đồng hồ. `seconds` là trần.
        #
        # ⚠️ Chỉ dừng sớm khi `xong()` đã True — lúc đó không còn việc đang chạy
        #    nên `terminate()` không thể cắt ngang một job giữa chừng, và bất
        #    biến "mỗi job chạy đúng một lần" không bị chính phép kiểm phá.
        han = time.monotonic() + float(seconds)
        while time.monotonic() < han:
            try:
                if xong():
                    break
            except Exception:                                  # noqa: BLE001
                pass          # CSDL đang bận/đang khoá: hỏi lại nhịp sau
            time.sleep(0.2)

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
    _run_workers(scratch, TRAN_CHO_S, xong=lambda: _con_lai(ids) == 0)

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
    _run_workers(scratch, TRAN_CHO_S, xong=lambda: _con_lai(ids) == 0)

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
