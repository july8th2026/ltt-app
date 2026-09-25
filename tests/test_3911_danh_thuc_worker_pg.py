"""PHÉP ĐO: một job phải chờ bao lâu để được nhặt, trên PostgreSQL THẬT.

Đây là phép đo mà `docs/auto_scan_video_final/L_TOC_DO_GPU.md` §3.1 gọi là còn
thiếu: con số 16–20 s ở đó **suy ra từ hằng số** `POLL_INTERVAL_S` chứ không đo
đầu-cuối. Tệp này đo đúng đơn vị nhân lên thành con số đó:

    ĐỘ TRỄ MỘT LƯỢT CHUYỂN LÀN
    = từ lúc job được `commit` vào hàng đợi
      đến lúc tiến trình worker DUY NHẤT phục vụ được nó nhặt nó lên.

⭐ **Vì sao phải là `run_forever` thật.** Cái đang được đo là *giấc ngủ của vòng
   worker*. Viết một vòng `while` riêng trong test rồi đo nó là dựng một **cửa
   giả** rồi hỏi nó đúng câu mà nó thay thế — cùng khuyết điểm mà
   `L_TOC_DO_GPU.md` §1 ghi lại về `_chay_hang_doi`. Nên ở đây worker là
   `job_runner.run_forever`, `claim` là `jobs.claim`, và nộp job là `jobs.submit`.

⚠️ **Phạm vi — đọc trước khi trích số.** Tệp này đo **một lượt chuyển làn**, ⛔
   KHÔNG đo "một video tiết kiệm bao nhiêu giây". Muốn ra con số thứ hai thì phải
   nhân với số lượt chuyển làn THẬT của một lần chạy ASV trên đội hình worker
   thật — và con số đó chưa ai có: nhật ký worker production 28 ngày **không có
   một job `auto_scan_video` nào** (mọi lần chạy ASV tới nay đi qua bộ nghiệm thu
   `_chay_hang_doi`, một vòng `for` trong một tiến trình, nơi các lượt nối nhau
   tức thì và độ trễ này **bằng 0**).

Chạy qua `python tools/check_multiproc.py`.
"""
from __future__ import annotations

import random
import threading
import time

import pytest
import sqlalchemy as sa

from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()

#: Khoá advisory mức phiên, giữ suốt một test của tệp này — cùng lý do như
#: `test_1720`: hai worker `xdist` dùng chung một CSDL scratch.
_KHOA_LOCK_KEY = 390139013901

#: Loại job dùng làm vật đo. `asv_voice` khai `requires=("voice",)`, nên trong
#: đội hình production (`api:6, gpu+ffmpeg:1, voice:1`) chỉ **một** tiến trình
#: nhặt được nó — đúng hình dạng "chuyển làn" mà ta cần đo.
LOAI_JOB = "asv_voice.voice_synthesis"
APP = "asv_voice"
NANG_LUC = {"api", "voice"}

#: Số lượt đo mỗi nhánh. Mỗi lượt nộp job ở một PHA ngẫu nhiên trong giấc ngủ
#: của worker — trung bình của phân bố đó mới là "độ trễ một lượt chuyển làn",
#: một lượt đơn lẻ không nói gì.
#: ⛔ 6, không phải 12: cả tệp phải chạy dưới 30 giây để còn là lệnh **Vừa**
#: (`docs/QUY_TAC_CHAY_LENH_NANG.md` §1) — nó đốt ~0 CPU (chủ yếu là `sleep`), nên
#: bọc nó vào khoá `cpu_nhieu` là giữ cả máy chờ một việc không tính gì.
SO_LUOT = 6

#: Trần chờ một lượt. ⛔ Không phải thời lượng: test thoát ngay khi job được
#: nhặt. Nó chỉ giữ cho một lỗi thật khỏi thành một lần treo vô hạn.
TRAN_CHO_S = 30.0


@pytest.fixture()
def pg(monkeypatch):
    url = pg_scratch.scratch_url()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    khoa_engine = sa.create_engine(url, future=True)
    khoa_conn = khoa_engine.connect()
    khoa_conn.execute(sa.text("SELECT pg_advisory_lock(:k)"), {"k": _KHOA_LOCK_KEY})
    try:
        dbmod.Base.metadata.drop_all(dbmod.get_engine())
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        yield dbmod
    finally:
        dbmod.reset_engine()
        khoa_conn.execute(sa.text("SELECT pg_advisory_unlock(:k)"),
                          {"k": _KHOA_LOCK_KEY})
        khoa_conn.close()
        khoa_engine.dispose()


def _do_mot_nhanh(dbmod, *, danh_thuc: bool) -> list[float]:
    """Trả về `SO_LUOT` độ trễ (giây) từ lúc commit job tới lúc worker nhặt.

    `danh_thuc=False` dựng lại hành vi **trước 25/09/2026**: `jobs.submit` không
    phát `NOTIFY`, nên worker chỉ thức theo nhịp `POLL_INTERVAL_S`. Không có
    nhánh này thì con số của nhánh kia không có gì để so — và một con số không
    có đối chứng không phải một phát hiện.

    🔴 **`MonkeyPatch` RIÊNG cho mỗi nhánh, không dùng fixture chung.** Bản đầu
       của tệp này nhận `monkeypatch` của test: bản vá "tắt đánh thức" của nhánh
       CŨ chỉ được hoàn lại ở **teardown**, nên nhánh MỚI chạy với `NOTIFY` vẫn
       đang bị tắt và đo ra **đúng con số của nhánh cũ** (0,990 s). Một phép đo
       hai nhánh mà bản vá rò từ nhánh này sang nhánh kia thì hai nhánh là một.
    """
    from platform_core import job_runner, jobs as jobq
    from tests.conftest import bao_dam_user

    mp = pytest.MonkeyPatch()

    da_nhat: dict[str, float] = {}
    co_nhat = threading.Event()

    def _handler(params, ctx=None):
        # Ghi mốc NGAY khi handler bắt đầu. Khoảng từ `claim` tới đây là vài ms
        # công việc CSDL và nó **giống nhau ở cả hai nhánh**, nên nó không vào
        # được hiệu số — thứ duy nhất tệp này kết luận.
        da_nhat[str(params.get("dau"))] = time.monotonic()
        co_nhat.set()
        return {}

    mp.setattr(jobq, "resolve_handler", lambda _jt: _handler)
    # ⛔ Ta đo ĐÁNH THỨC, không đo cấp lease GPU: để `_vram_can` thật thì mỗi
    #    lượt còn tốn một vòng `gpu_lease.acquire` trên card thật của máy này,
    #    và nó rơi vào cả hai nhánh như nhau nhưng thêm nhiễu cho không.
    mp.setattr(job_runner, "_vram_can", lambda _jt: 0)
    if not danh_thuc:
        mp.setattr(jobq, "danh_thuc_worker", lambda _db: None)

    with next(dbmod.get_session()) as db:
        bao_dam_user(db, "u-3901")
        db.commit()

    dung = {"c": False}
    worker = threading.Thread(
        target=job_runner.run_forever,
        args=(f"do-3901-{'moi' if danh_thuc else 'cu'}",),
        kwargs={"stop": lambda: dung["c"], "maintenance": False,
                "capabilities": set(NANG_LUC)},
        name="worker-3901", daemon=True)
    worker.start()
    # Cho worker vào đúng trạng thái cần đo: đang NGỦ giữa hai lượt poll.
    time.sleep(job_runner.POLL_INTERVAL_S + 0.5)

    tre: list[float] = []
    try:
        for i in range(SO_LUOT):
            dau = f"{'moi' if danh_thuc else 'cu'}-{i}"
            co_nhat.clear()
            with next(dbmod.get_session()) as db:
                jobq.submit(db, user_id="u-3901", app_slug=APP,
                            job_type=LOAI_JOB, params={"dau": dau},
                            dedupe_key=f"do3901:{dau}")
                t0 = time.monotonic()
                db.commit()
            het = t0 + TRAN_CHO_S
            while dau not in da_nhat and time.monotonic() < het:
                co_nhat.wait(0.05)
            assert dau in da_nhat, f"job {dau} khong duoc nhat trong {TRAN_CHO_S}s"
            tre.append(da_nhat[dau] - t0)
            # Pha NGẪU NHIÊN: nếu luôn nộp ngay sau một lượt nhặt thì mọi lượt
            # đo rơi vào cùng một điểm trong giấc ngủ, và trung bình thu về là
            # trung bình của MỘT pha, không phải của phân bố.
            time.sleep(random.uniform(0.0, job_runner.POLL_INTERVAL_S))
    finally:
        dung["c"] = True
        worker.join(timeout=30)
        mp.undo()
    return tre


def test_danh_thuc_worker_rut_ngan_mot_luot_chuyen_lan(pg, capsys):
    cu = _do_mot_nhanh(pg, danh_thuc=False)
    moi = _do_mot_nhanh(pg, danh_thuc=True)

    def _bang(ten, m):
        return (f"{ten:4s} n={len(m)} tb={sum(m)/len(m):6.3f}s "
                f"min={min(m):6.3f}s max={max(m):6.3f}s")

    from platform_core import job_runner

    with capsys.disabled():
        print()
        print("DO TRE MOT LUOT CHUYEN LAN (PostgreSQL that, run_forever that)")
        print("  POLL_INTERVAL_S =", job_runner.POLL_INTERVAL_S)
        print("  " + _bang("CU", cu))
        print("  " + _bang("MOI", moi))
        print(f"  tiet kiem trung binh moi luot chuyen lan = "
              f"{sum(cu)/len(cu) - sum(moi)/len(moi):.3f}s")

    tb_cu = sum(cu) / len(cu)
    tb_moi = sum(moi) / len(moi)

    # Nhánh CŨ phải thật sự đo được cái nó nói: nếu nó cũng nhanh thì phép đo
    # không có đối chứng và mọi kết luận bên dưới vô nghĩa.
    assert tb_cu > 0.4, (f"nhanh CU chi {tb_cu:.3f}s — phep do khong con doi "
                         f"chung, doc lai truoc khi tin nhanh MOI")
    assert max(cu) > 1.0, "nhanh CU khong lan nao doi gan het mot nhip poll"

    assert tb_moi < 0.2, f"duong danh thuc khong hieu qua: tb {tb_moi:.3f}s"
    assert max(moi) < 1.0, f"con mot luot roi vao nhip poll: {max(moi):.3f}s"
    assert tb_cu / max(tb_moi, 1e-6) > 4.0
