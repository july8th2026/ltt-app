"""
test_601 — `runtime_noi_bo.danh_muc` + `runtime_noi_bo.job`. (H43 Phase 02)

  1. `danh_muc` chỉ trả tool trong allowlist; tên lạ, app tắt, tool không có
     `api_contract` đều **không hiện** (fail-closed) — và không lộ id nội bộ.
  2. Tuỳ chọn động theo NGƯỜI DÙNG đi qua `ToolSpec.tuy_chon_dong`.
  3. `bao_gia` validate theo ToolSpec rồi tính giá đúng làn; `nop_job` giữ đúng
     số đã báo, ép `owner_id`, truyền `so_lan_thu` của manifest, dedupe.
"""
from __future__ import annotations

import uuid

import pytest

SLUG = "appthu601"
JOB = "appthu601.ve"
TOOL = "image.thu601"
TOOL_KHONG_HOP_DONG = "image.thu601_noi_bo"


def tuy_chon_thu(db, user_id):
    """Danh sách "của tôi": phụ thuộc người dùng, không phụ thuộc tiến trình."""
    return [{"value": f"vc_{user_id[:4]}", "label": "Giong cua toi"}]


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "j.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    yield
    dbmod.reset_engine()


def _manifest(enabled=True):
    from platform_core import registry as reg
    return reg.AppManifest(
        slug=SLUG, display_name="App thu 601", route_prefix=f"/{SLUG}",
        job_types=(JOB,), credit_cost=lambda p: 3 * int(p.get("count", 1)),
        so_lan_thu={JOB: 5},
        bang_gia=lambda: {"don_vi": "credit / anh", "phien_ban_gia": "thu-2026-09"},
        enabled=enabled, public=False, surface="runtime", lifecycle="internal",
        tools=(
            reg.ToolSpec(
                name=TOOL, job_type=JOB, description="ve anh thu",
                params_schema={
                    "prompt": {"type": "string", "required": True, "max_length": 100},
                    "count": {"type": "int", "min": 1, "max": 4, "default": 1},
                    "voice_id": {"type": "string", "required": False},
                },
                returns={"image_keys": "image[]"},
                admission_resource="thu_gpu2", admission_slots=1,
                tuy_chon_dong={"voice_id": "tests.test_601_runtime_noi_bo_danh_muc_job:tuy_chon_thu"},
                api_exposed=True,
                api_contract={
                    "scopes": ("jobs:create",),
                    "description": "Ve anh (mo ta cho khach)",
                    "models": {"thu_std": {"id": "engine-noi-bo-x1",
                                           "stability": "stable"}},
                },
            ),
            reg.ToolSpec(
                name=TOOL_KHONG_HOP_DONG, job_type=JOB, description="noi bo",
                params_schema={"prompt": {"type": "string", "required": True}},
                returns={"image_keys": "image[]"},
            ),
        ),
    )


@pytest.fixture()
def app_601(monkeypatch, moi_truong):
    from platform_core import registry as reg
    m = _manifest()
    loaded = reg.LoadedApp(manifest=m, router=None)
    goc = reg.discover
    monkeypatch.setattr(reg, "discover",
                        lambda apps_dir=None: list(goc() if apps_dir is None
                                                   else goc(apps_dir)) + [loaded])
    return m


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _user(credits=100):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="j-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


# ── 1. Catalog fail-closed ───────────────────────────────────────────────────

def test_danh_muc_chi_tra_tool_trong_allowlist_va_khong_lo_id_noi_bo(app_601):
    from platform_core.runtime_noi_bo.danh_muc import danh_muc
    gen, db = _session()
    try:
        ds = danh_muc(db, user_id="u-1", cho_phep={TOOL, "text.khong_co"})
    finally:
        _close(gen)
    assert [n.ten for n in ds] == [TOOL]
    n = ds[0]
    assert n.phuong_thuc == "image" and n.che_do == "job"
    assert n.nhan == "Ve anh (mo ta cho khach)"
    assert n.duong_dan_app == f"/{SLUG}"
    assert n.gia["phien_ban_gia"] == "thu-2026-09"
    assert list(n.models) == ["thu_std"]
    import json
    assert "engine-noi-bo-x1" not in json.dumps(
        {"hop_dong": n.hop_dong, "models": n.models, "tuy_chon": n.tuy_chon})
    assert n.hop_dong["input_schema"]["properties"]["count"]["maximum"] == 4


def test_tool_khong_co_api_contract_khong_hien(app_601):
    from platform_core.runtime_noi_bo.danh_muc import danh_muc
    gen, db = _session()
    try:
        ds = danh_muc(db, user_id="u-1", cho_phep={TOOL_KHONG_HOP_DONG})
    finally:
        _close(gen)
    assert ds == []


def test_app_tat_thi_san_sang_la_chua_san_sang(monkeypatch, moi_truong):
    from platform_core import registry as reg
    from platform_core.runtime_noi_bo.danh_muc import danh_muc
    loaded = reg.LoadedApp(manifest=_manifest(enabled=False), router=None)
    gen, db = _session()
    try:
        ds = danh_muc(db, user_id="u", cho_phep={TOOL}, apps=[loaded])
    finally:
        _close(gen)
    assert ds[0].san_sang == "chua_san_sang"


# ── 2. Tuỳ chọn động theo người dùng ────────────────────────────────────────

def test_tuy_chon_dong_theo_nguoi_dung(app_601):
    from platform_core.runtime_noi_bo.danh_muc import danh_muc
    gen, db = _session()
    try:
        a = danh_muc(db, user_id="aaaa-1", cho_phep={TOOL})[0]
        b = danh_muc(db, user_id="bbbb-2", cho_phep={TOOL})[0]
    finally:
        _close(gen)
    assert a.tuy_chon["voice_id"] == [{"value": "vc_aaaa", "label": "Giong cua toi"}]
    assert b.tuy_chon["voice_id"] == [{"value": "vc_bbbb", "label": "Giong cua toi"}]


def test_agent_tools_resolve_tuy_chon_dong_khi_co_db(app_601):
    from platform_core.agent.tools import resolve_params_schema
    gen, db = _session()
    try:
        co = resolve_params_schema(TOOL, {}, db=db, user_id="cccc-3")
        khong = resolve_params_schema(TOOL, {})
    finally:
        _close(gen)
    assert co["voice_id"]["values"] == ["vc_cccc"]
    assert "values" not in khong["voice_id"]     # caller cũ: không đổi gì


# ── 3. Báo giá + nộp job ─────────────────────────────────────────────────────

def test_bao_gia_validate_roi_tinh_dung_gia(app_601):
    from platform_core.runtime_noi_bo import job
    bg = job.bao_gia(TOOL, {"prompt": "meo", "count": 2})
    assert (bg.lane, bg.credit, bg.phien_ban_gia) == (JOB, 6, "thu-2026-09")
    assert bg.tham_so_sach == {"prompt": "meo", "count": 2}
    with pytest.raises(job.ThamSoSai):
        job.bao_gia(TOOL, {"prompt": "meo", "count": 9})
    with pytest.raises(job.ThamSoSai):
        job.bao_gia(TOOL, {"prompt": "meo", "la": 1})
    with pytest.raises(job.KhongCoNangLuc):
        job.bao_gia("image.khong_co", {"prompt": "x"})


def test_nop_job_giu_dung_so_bao_ep_owner_va_so_lan_thu(app_601):
    from platform_core import credit
    from platform_core.runtime_noi_bo import job
    u = _user(100)
    bg = job.bao_gia(TOOL, {"prompt": "meo", "count": 2})
    gen, db = _session()
    try:
        j = job.nop_job(db, user_id=u, bao_gia=bg, correlation_id="corr-1",
                        idempotency_key="idem-1")
        db.commit()
        assert j.params["owner_id"] == u
        assert j.job_type == JOB and j.app_slug == SLUG
        assert j.max_attempts == 5                       # từ manifest.so_lan_thu
        assert j.admission_resource == "thu_gpu2" and j.admission_slots == 1
        assert j.correlation_id == "corr-1"
        assert credit.so_da_giu(db, j.id) == 6
        assert int(credit.so_du(db, u)) == 94
        # Nộp lại cùng khoá idempotency ⇒ job cũ, KHÔNG giữ lần hai.
        j2 = job.nop_job(db, user_id=u, bao_gia=bg, idempotency_key="idem-1")
        db.commit()
        assert j2.id == j.id and int(credit.so_du(db, u)) == 94
    finally:
        _close(gen)


def test_nop_job_thieu_credit_nem_va_khong_tao_job(app_601):
    from platform_core import credit
    from platform_core.models import Job
    from platform_core.runtime_noi_bo import job
    u = _user(2)
    bg = job.bao_gia(TOOL, {"prompt": "meo", "count": 4})
    gen, db = _session()
    try:
        with pytest.raises(credit.ThieuCreditError):
            job.nop_job(db, user_id=u, bao_gia=bg)
        db.rollback()
        assert db.query(Job).filter(Job.user_id == u).count() == 0
    finally:
        _close(gen)
