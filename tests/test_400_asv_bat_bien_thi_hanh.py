"""Auto Scan Video — guardrails for the ADR-001 execution/billing/resource model.

## What this file is for

`docs/auto_scan_video/adr/ADR-001-execution-billing-resource.md` makes claims about how
the *platform* behaves. Those claims are what make the Auto Scan design safe, and none
of them is currently protected by a test that mentions Auto Scan. If one of them
quietly changes, the failure surfaces as a money bug in a product that does not exist
yet — the worst possible place to find out.

So these tests are deliberately written **before** any Auto Scan code (Phase 04, before
Phase 05 builds the app). They pin platform behaviour that ADR-001 depends on.

⛔ **They are not tests of Auto Scan.** They are tests of the ground Auto Scan stands on.
   When the app exists, its own tests go elsewhere; these stay as the contract.

Evidence for every assertion is cited inline, because a guardrail whose reason is lost
is a guardrail someone deletes.
"""
from __future__ import annotations

import pytest

from tests.conftest import APP_THU_JOB, APP_THU_SLUG, bao_dam_user


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Temp SQLite, same shape as `tests/test_68_credit.py:22`."""
    url = f"sqlite:///{(tmp_path / 'asv.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


# ══════════════════════════════════════════════════════════════════════════════
#  I3 / G3 — one billing owner. The single most expensive thing to get wrong.
# ══════════════════════════════════════════════════════════════════════════════

def test_job_nop_bang_jobs_submit_KHONG_giu_credit(db, app_thu):
    """ADR-001 D4 step 2 rests entirely on this.

    Auto Scan submits its nine stage jobs with `jobs.submit`, not
    `job_submit.submit_with_credit`, precisely so they carry no hold and the run can be
    the only billing owner. If `jobs.submit` ever started holding credit by itself,
    every run would be charged **ten** times — once for the run and once per stage —
    and the ledger would still balance, so nothing would look wrong.
    """
    from platform_core import credit, jobs

    bao_dam_user(db, "u1")
    job = jobs.submit(db, user_id="u1", app_slug=APP_THU_SLUG,
                      job_type=APP_THU_JOB, params={"text": "x"})
    db.commit()
    assert credit.so_da_giu(db, job.id) == 0, (
        "jobs.submit da tu giu credit -> child job cua Auto Scan se tinh tien hai lan")


def test_quyet_toan_bo_qua_job_khong_co_giu_cho(db, app_thu):
    """ADR-001 D4: what makes double-charging structurally impossible, not just avoided.

    `job_runner._quyet_toan_credit` returns early when `so_da_giu(job.id) == 0`
    (`platform_core/job_runner.py:660`). That early return is the reason a stage job
    finishing cannot touch the ledger at all.
    """
    from platform_core import credit, jobs
    from platform_core.job_runner import _quyet_toan_credit

    bao_dam_user(db, "u1")
    credit.nap(db, "u1", 500)
    job = jobs.submit(db, user_id="u1", app_slug=APP_THU_SLUG,
                      job_type=APP_THU_JOB, params={"text": "x"})
    db.commit()
    truoc = credit.so_du(db, "u1")

    assert _quyet_toan_credit(db, job, {"credit_cost": 999}) is None
    db.commit()
    assert credit.so_du(db, "u1") == truoc, (
        "job khong co hold ma van doi so du -> stage job co the tu tinh tien")


def test_giu_cho_dung_duoc_voi_id_KHONG_phai_job(db):
    """ADR-001 D4 step 1 holds credit against a **run id**, not a job id.

    Legitimate because `credit.giu_cho` keys on an opaque string, and
    `platform_core/agent/budget.py:90` already does exactly this with `run.id`. Pinned
    here because the whole billing model collapses if a foreign key ever appears.
    """
    from platform_core import credit

    bao_dam_user(db, "u1")
    credit.nap(db, "u1", 1000); db.commit()

    run_id = "asv-run-0001-not-a-job"
    credit.giu_cho(db, "u1", 300, run_id); db.commit()
    assert credit.so_da_giu(db, run_id) == 300
    assert credit.so_du(db, "u1") == 700

    credit.quyet_toan(db, "u1", run_id, 120); db.commit()
    assert credit.so_du(db, "u1") == 880, "phan khong dung phai duoc hoan"


def test_quyet_toan_it_hon_giu_cho_thi_hoan_phan_du(db):
    """The property that lets ADR-001 D4 settle on **measured** cost.

    Auto Scan estimates a hold from duration before it knows the transcript, then
    settles on what was really consumed. That only works if settling for less than the
    hold refunds the difference.

    ⭐ This is the mechanism that makes rejecting `agent/executor.actual_cost` viable:
       measuring low is safe, so we never have to price by `credit_for(...) x attempts`.
    """
    from platform_core import credit

    bao_dam_user(db, "u2")
    credit.nap(db, "u2", 1000); db.commit()
    credit.giu_cho(db, "u2", 400, "asv-run-refund"); db.commit()
    assert credit.so_du(db, "u2") == 600

    credit.quyet_toan(db, "u2", "asv-run-refund", 0); db.commit()
    assert credit.so_du(db, "u2") == 1000, "quyet toan 0 phai hoan toan bo hold"


def test_quyet_toan_hai_lan_khong_tinh_tien_hai_lan(db):
    """I2 — a settlement identity may be charged exactly once.

    `asv.advance` is re-enqueued repeatedly and is explicitly allowed to re-run after a
    crash (ADR-001 D1). If settlement were not idempotent, a coordinator that died
    after settling but before committing its own status would charge again on the next
    tick.
    """
    from platform_core import credit

    bao_dam_user(db, "u3")
    credit.nap(db, "u3", 1000); db.commit()
    credit.giu_cho(db, "u3", 500, "asv-run-idem"); db.commit()

    credit.quyet_toan(db, "u3", "asv-run-idem", 200); db.commit()
    sau_lan_dau = credit.so_du(db, "u3")
    credit.quyet_toan(db, "u3", "asv-run-idem", 200); db.commit()
    assert credit.so_du(db, "u3") == sau_lan_dau, "quyet toan lan hai da tinh tien them"


# ══════════════════════════════════════════════════════════════════════════════
#  I12 / G5 — worker routing. The highest-risk unknown in Phase 00.
# ══════════════════════════════════════════════════════════════════════════════

def _manifest_gia(reg, slug: str, requires: tuple, job_type: str):
    """A runtime executor shaped exactly like ADR-001 D5 prescribes."""
    return reg.AppManifest(
        slug=slug, display_name=f"exec {slug}", route_prefix=f"/{slug}",
        job_types=(job_type,), requires=requires,
        credit_cost=lambda params: 1,
        enabled=False, public=False, surface="runtime", lifecycle="internal",
        catalog_parent="auto_scan_video",
    )


@pytest.fixture()
def hai_executor_gia(monkeypatch):
    """Two hidden runtime executors: one ffmpeg, one gpu. ADR-001 D5 in miniature."""
    from platform_core import registry as reg

    media = _manifest_gia(reg, "asv_media_thu", ("ffmpeg",), "asvthu.render")
    gpu = _manifest_gia(reg, "asv_gpu_thu", ("gpu",), "asvthu.transcribe")
    them = [reg.LoadedApp(manifest=media, router=None),
            reg.LoadedApp(manifest=gpu, router=None)]

    goc = reg.discover
    monkeypatch.setattr(reg, "discover",
                        lambda apps_dir=None: list(goc() if apps_dir is None
                                                   else goc(apps_dir)) + them)
    return {"media": media, "gpu": gpu}


def test_worker_chi_nhat_job_cua_app_ma_no_du_nang_luc(db, hai_executor_gia):
    """ADR-001 D5 is only correct if claim really filters by `manifest.requires`.

    `platform_core/jobs.py:158-164` intersects `set(manifest.requires)` with the
    worker's capabilities **at app granularity**. That is the whole reason Auto Scan is
    split into narrow runtime executors instead of one app declaring the union.
    """
    from platform_core import jobs

    bao_dam_user(db, "u1")
    jobs.submit(db, user_id="u1", app_slug="asv_media_thu",
                job_type="asvthu.render", params={})
    jobs.submit(db, user_id="u1", app_slug="asv_gpu_thu",
                job_type="asvthu.transcribe", params={})
    db.commit()

    chi_ffmpeg = jobs.claim(db, worker_id="w-ffmpeg", capabilities={"ffmpeg"})
    assert chi_ffmpeg is not None
    assert chi_ffmpeg.app_slug == "asv_media_thu", (
        "worker chi co ffmpeg da nhat duoc job GPU")
    db.commit()

    assert jobs.claim(db, worker_id="w-ffmpeg2", capabilities={"ffmpeg"}) is None, (
        "chi con job GPU, worker ffmpeg khong duoc nhat no")

    co_gpu = jobs.claim(db, worker_id="w-gpu", capabilities={"gpu"})
    assert co_gpu is not None and co_gpu.app_slug == "asv_gpu_thu"


def test_app_gop_ca_hai_nang_luc_bi_ca_HAI_lan_le_tu_choi(db, monkeypatch):
    """The failure ADR-001 D5 exists to prevent — proven, not asserted.

    A single Auto Scan app declaring `requires=("ffmpeg","gpu")` is claimable **only**
    by a lane holding both. On a fleet split into `ffmpeg:N` and `gpu:M` lanes, its jobs
    are invisible to every worker and sit `queued` forever with no error raised anywhere
    (RISK-00-02 — the same silent failure `apps/ltt_voice/manifest.py:112` documents).
    """
    from platform_core import jobs
    from platform_core import registry as reg

    gop = _manifest_gia(reg, "asv_gop_thu", ("ffmpeg", "gpu"), "asvthu.gop")
    goc = reg.discover
    monkeypatch.setattr(reg, "discover",
                        lambda apps_dir=None: list(goc() if apps_dir is None
                                                   else goc(apps_dir))
                        + [reg.LoadedApp(manifest=gop, router=None)])

    bao_dam_user(db, "u1")
    jobs.submit(db, user_id="u1", app_slug="asv_gop_thu",
                job_type="asvthu.gop", params={})
    db.commit()

    assert jobs.claim(db, worker_id="w1", capabilities={"ffmpeg"}) is None
    assert jobs.claim(db, worker_id="w2", capabilities={"gpu"}) is None
    assert jobs.claim(db, worker_id="w3", capabilities={"ffmpeg", "gpu"}) is not None, (
        "chi lan co CA HAI nang luc moi nhat duoc — day chinh la ly do phai tach app")


# ══════════════════════════════════════════════════════════════════════════════
#  I4 — retry accounting
# ══════════════════════════════════════════════════════════════════════════════

def test_tai_nguyen_ban_dua_job_ve_hang_doi_chu_khong_phai_LOI(db, app_thu):
    """ADR-001 D3 maps `defer_resource` to `failed_retryable`, not a terminal failure.

    Auto Scan's GPU stages will hit a busy card routinely — three other tenants share
    it (CLAUDE.md). If a busy resource counted as an error, ordinary contention would
    burn `max_attempts` and fail paid runs for no reason.
    """
    from platform_core import jobs
    from platform_core.models import JOB_QUEUED

    bao_dam_user(db, "u1")
    job = jobs.submit(db, user_id="u1", app_slug=APP_THU_SLUG,
                      job_type=APP_THU_JOB, params={"text": "x"})
    db.commit()
    claimed = jobs.claim(db, worker_id="w1")
    assert claimed is not None
    truoc = claimed.attempts

    jobs.defer_resource(db, claimed, retry_after=1)
    db.commit()
    assert claimed.status == JOB_QUEUED
    assert claimed.attempts == truoc, "cho tai nguyen khong duoc dot mot lan thu"


def test_dedupe_khong_tao_job_thu_hai_khi_job_cu_con_chay(db, app_thu):
    """I4 — the guard behind ADR-001's "a new run is a new hold, a retry is not".

    `jobs.submit` dedupes on `(user, dedupe_key)` while the previous job is unfinished
    (`platform_core/jobs.py:116`). Auto Scan's coordinator re-enqueues itself on every
    tick, so without this a crashed-and-restarted run would fan out coordinators.
    """
    from platform_core import jobs

    bao_dam_user(db, "u1")
    a = jobs.submit(db, user_id="u1", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
                    params={"text": "x"}, dedupe_key="asv:advance:run1")
    db.commit()
    b = jobs.submit(db, user_id="u1", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
                    params={"text": "x"}, dedupe_key="asv:advance:run1")
    db.commit()
    assert a.id == b.id, "nop trung khi job cu con chay phai tra ve job cu"


# ══════════════════════════════════════════════════════════════════════════════
#  I13 / G10 — cancellation cannot become success
# ══════════════════════════════════════════════════════════════════════════════

def test_huy_roi_thi_khong_the_nhat_lai(db, app_thu):
    """ADR-001 D9 relies on a cancelled job never re-entering the queue.

    `jobs.cancel` only acts on `queued`/`running` (`jobs.py:324`), and a cancelled job
    is no longer claimable. That is half of "cancellation cannot later become success";
    the other half — the run refusing to advance — belongs to Phase 17.
    """
    from platform_core import jobs
    from platform_core.models import JOB_CANCELLED

    bao_dam_user(db, "u1")
    job = jobs.submit(db, user_id="u1", app_slug=APP_THU_SLUG,
                      job_type=APP_THU_JOB, params={"text": "x"})
    db.commit()
    assert jobs.cancel(db, job) is True
    db.commit()
    assert job.status == JOB_CANCELLED
    assert jobs.claim(db, worker_id="w1") is None, "job da huy van bi nhat lai"


# ══════════════════════════════════════════════════════════════════════════════
#  I5 — provider ambiguity seam
# ══════════════════════════════════════════════════════════════════════════════

def test_dispatch_mo_ho_la_LOI_CUOI_khong_duoc_thu_lai(db, app_thu):
    """I5 / G7. Auto Scan makes paid remote calls in CONTENT and VOICE.

    A crash after a provider may have accepted a request must fail **terminally**, not
    retry: retrying is how one paid TTS call becomes two. `jobs.mark_ambiguous`
    (`jobs.py:274`) sets `error` directly rather than re-queueing, and this pins that.
    """
    from platform_core import jobs
    from platform_core.models import JOB_ERROR

    bao_dam_user(db, "u1")
    job = jobs.submit(db, user_id="u1", app_slug=APP_THU_SLUG,
                      job_type=APP_THU_JOB, params={"text": "x"}, max_attempts=5)
    db.commit()
    claimed = jobs.claim(db, worker_id="w1")
    jobs.mark_provider_dispatched(db, claimed, provider="thu")
    db.commit()
    assert claimed.provider_state == "dispatched"
    assert claimed.provider_dispatched_at is not None

    jobs.mark_ambiguous(db, claimed, "mat ket noi sau khi da goi provider")
    db.commit()
    assert claimed.status == JOB_ERROR, "dispatch mo ho phai la loi CUOI"
    assert jobs.claim(db, worker_id="w2") is None, (
        "job mo ho van con trong hang doi -> se goi provider lan hai")


# ══════════════════════════════════════════════════════════════════════════════
#  I19 / I10 — cache privacy and fingerprint identity
# ══════════════════════════════════════════════════════════════════════════════

def test_cung_noi_dung_hai_chu_KHONG_dung_chung_ket_qua(db, app_thu):
    """I19 / guardrail §8 — cache reuse is owner-scoped in MVP.

    Two customers uploading the same file produce the same fingerprint (ADR-001 D8).
    Reusing one's output for the other would reveal that the other holds that exact
    material. MVP recomputes; cross-tenant reuse needs its own privacy ADR.

    Pinned at the queue level: identical params from two users must be two jobs.
    """
    from platform_core import jobs

    bao_dam_user(db, "uA"); bao_dam_user(db, "uB")
    params = {"text": "cung mot noi dung"}
    a = jobs.submit(db, user_id="uA", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
                    params=params, dedupe_key="van-tay-giong-nhau")
    b = jobs.submit(db, user_id="uB", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
                    params=params, dedupe_key="van-tay-giong-nhau")
    db.commit()
    assert a.id != b.id, "dedupe da vuot qua ranh gioi chu so huu"
    assert a.user_id != b.user_id


# ══════════════════════════════════════════════════════════════════════════════
#  I7 — RED TARGET, owned by Phase 07. Do NOT make this green by weakening it.
# ══════════════════════════════════════════════════════════════════════════════

def test_khoa_rieng_cua_nguoi_dung_khong_duoc_cap_cho_nguoi_khac(db):
    """I7 — ĐÃ ĐÓNG ở Phase 07. Trước đó đây là mục tiêu ĐỎ `xfail(strict=True)`.

    Lịch sử đáng giữ, vì nó là lý do phép kiểm này tồn tại:
    `ApiKey.owner_user_id` được GHI (`api_keys.py:94`) nhưng **không nơi nào ĐỌC**
    — `api_pool._ung_vien` lọc theo enabled/status/categories/models/rate và
    không hề lọc theo chủ sở hữu. Một khoá riêng của khách sẽ được cấp cho lượt
    gọi của bất kỳ ai.

    Chưa rò rỉ thật vào lúc đó, và lý do rất cụ thể: **không đường ghi nào trong
    kho đặt `owner_user_id`** (trang admin `server/admin.py:734` không truyền,
    hai công cụ nạp khoá cũng không). Nên mọi dòng đều mang chuỗi rỗng.

    ⭐ Chính điều đó làm cách sửa an toàn: định nghĩa rỗng = pool nền tảng là
       **thiết lập** ngữ nghĩa cho một cột chưa có ngữ nghĩa, không phải diễn
       giải lại một cột đang dùng. Không dòng nào đổi hành vi (O15).
    """
    from platform_core import api_keys, api_pool

    bao_dam_user(db, "uA"); bao_dam_user(db, "uB")
    api_keys.tao_key(db, provider="gemini", credential="khoa-cua-A",
                     name="cua A", owner_user_id="uA")
    db.commit()

    # Pool nen tang: khoa DUY NHAT dang co la khoa rieng cua uA, nen dung cau tra
    # loi la "khong co khoa nao" — chu KHONG phai "day, cam tam khoa cua uA".
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.chon_key(db)

    # uB xin khoa rieng: cung khong duoc thay khoa cua uA.
    with pytest.raises(api_pool.ThieuKeyError):
        api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG, owner_user_id="uB")

    # Chinh uA thi duoc.
    cua_a = api_pool.chon_key(db, pham_vi=api_pool.PHAM_VI_RIENG,
                              owner_user_id="uA")
    assert cua_a.owner_user_id == "uA"
