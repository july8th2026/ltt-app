"""
video_crawler — dedup BỀN bằng bảng `vc_da_tai` (PLAN_MVP §C W2-L6, Q4; spec §13, §17; SO_LOI L4).

Trước bảng này, "không trùng" suy từ `jobs.result` (bị xoá sau 30 ngày, chỉ quét 500 job gần nhất) và hai job
cùng lúc cùng video của một user đều tải + đều thu tiền. Các mệnh đề chốt:
- GIÀNH chỗ trước khi tải: hai phiên DB cùng giành (owner, nền, video) ⇒ đúng MỘT thắng (UNIQUE ở CSDL);
- hai job của cùng user cùng video chạy chồng nhau ⇒ chỉ một lượt tải, chỉ một lượt thu tiền, job kia bỏ qua
  "trùng" và có sự kiện rõ cho khách;
- huỷ/lỗi giữa chừng ⇒ dòng giành chỗ của job bị xoá (như dọn storage) ⇒ lượt sau tải lại được;
- giành chỗ 'dang_tai' quá 3 giờ (job chết) được giành lại;
- "không trùng" nhận ra video tải từ > 30 ngày trước, kể cả khi `jobs.result` đã bị dọn;
- cách ly theo user; migration khớp ORM; governance khai bảng.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import tests.test_1905_video_crawler_job as _t1905
from tests.test_1905_video_crawler_job import (
    NAP_BAN_DAU, _DNS, AdapterGia, _chay, _dung_adapter, _muc, _nop_tai, _so_du,
)

kho = _t1905.kho            # fixture dùng chung (storage tạm, người dùng u1/u2 có credit)
nguoi = _t1905.nguoi

_A, _B, _C = "a" * 11, "b" * 11, "c" * 11


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'j.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


@pytest.fixture(autouse=True)
def _khong_nghi(monkeypatch):
    import apps.video_crawler.jobs as vc_jobs
    monkeypatch.setattr(vc_jobs, "_ngu", lambda s: None)


def _phien_moi():
    from platform_core.db import get_session
    gen = get_session()
    return next(gen)


def _dong(db, owner="u1"):
    from apps.video_crawler.tables import VcDaTai
    db.expire_all()
    return {(r.video_id, r.trang_thai) for r in db.query(VcDaTai).filter_by(owner_id=owner)}


# ── Giành chỗ ở tầng CSDL ─────────────────────────────────────────────────────

def test_hai_phien_db_cung_gianh_chi_mot_thang(db):
    from apps.video_crawler import features
    s1, s2 = _phien_moi(), _phien_moi()
    try:
        assert features.gianh_cho(s1, "u1", "youtube", _A, "job-1") is True
        assert features.gianh_cho(s2, "u1", "youtube", _A, "job-2") is False
        assert features.gianh_cho(s2, "u2", "youtube", _A, "job-3") is True       # user khác: độc lập
        assert features.gianh_cho(s2, "u1", "tiktok", _A, "job-4") is True        # nền khác: độc lập
        assert features.gianh_cho(s1, "u1", "youtube", _A, "job-1") is True       # lượt thử lại của chính job
    finally:
        s1.close(); s2.close()


def test_gianh_cho_qua_3_gio_thi_gianh_lai_duoc(db):
    from apps.video_crawler import features
    t0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert features.gianh_cho(db, "u1", "youtube", _A, "job-chet", bay_gio=t0)
    assert not features.gianh_cho(db, "u1", "youtube", _A, "job-2", bay_gio=t0 + timedelta(hours=2, minutes=59))
    assert features.gianh_cho(db, "u1", "youtube", _A, "job-2", bay_gio=t0 + timedelta(hours=3, minutes=1))
    features.danh_dau_xong(db, "u1", "job-2", {_A: "video_crawler/u1/job-2/a.mp4"})
    # Dòng 'xong' không bao giờ "quá cũ": chừng nào tệp còn, job khác không giành được.
    assert not features.gianh_cho(db, "u1", "youtube", _A, "job-3", bay_gio=t0 + timedelta(days=90))


def test_dong_xong_ma_tep_da_het_han_thi_tai_lai_duoc_khi_chon_tuong_minh(db):
    """Tệp đi theo `jobs` (30 ngày). Khách chọn đích danh video đã tải mà tệp đã mất ⇒ được tải lại."""
    from apps.video_crawler import features
    assert features.gianh_cho(db, "u1", "youtube", _A, "job-1")
    features.danh_dau_xong(db, "u1", "job-1", {_A: "video_crawler/u1/job-1/a.mp4"})
    assert not features.gianh_cho(db, "u1", "youtube", _A, "job-2", tep_con=lambda k: True)
    assert features.gianh_cho(db, "u1", "youtube", _A, "job-2", tep_con=lambda k: False)
    assert _dong(db) == {(_A, "dang_tai")}


# ── Chuỗi job thật ────────────────────────────────────────────────────────────

def test_hai_job_chong_nhau_cung_video_chi_tai_va_thu_tien_mot_lan(db, kho, nguoi, monkeypatch):
    """Review W1 'hai job cùng video thu hai lần': job 2 chạy TRỌN trong lúc job 1 đang tải mục a."""
    from apps.video_crawler import gia
    from platform_core import job_events
    from platform_core.models import JOB_DONE

    lich = {}

    def chay_job_2_giua_chung(item):
        if item.id == _A and "j2" in lich and not lich.get("da_chay"):
            lich["da_chay"] = True
            lich["job2"] = _chay(db, lich["j2"])            # worker thứ hai nhận job 2 lúc job 1 đang tải a

    adapter = AdapterGia(truoc_tai=chay_job_2_giua_chung)
    _dung_adapter(monkeypatch, adapter)
    j1 = _nop_tai(db, "u1", [_A])
    lich["j2"] = _nop_tai(db, "u1", [_A, _C])      # params khác ⇒ khoá chống nộp trùng của nền tảng không gộp
    job1 = _chay(db, j1)
    job2 = lich["job2"]
    assert sorted(adapter.da_tai) == [_A, _C]                  # a chỉ tải MỘT lần (bởi job 1)
    assert job1.status == JOB_DONE and job1.result["credit_cost"] == gia.gia_muc(None)
    assert job2.status == JOB_DONE and job2.result["credit_cost"] == gia.gia_muc(None)   # chỉ c
    assert job2.result["bo_qua_trung"] == 1 and job2.result["video_keys"] == [f"video_crawler/u1/{job2.id}/{_C}.mp4"]
    assert "muc_trung" in [e.event_code for e in job_events.timeline(db, job2.id)]
    assert _so_du(db, "u1") == NAP_BAN_DAU - 2 * gia.gia_muc(None)   # a thu MỘT lần, c một lần
    assert _dong(db) == {(_A, "xong"), (_C, "xong")}


def test_moi_muc_dang_duoc_job_khac_tai_thi_xong_mien_phi(db, kho, nguoi, monkeypatch):
    """Mọi mục của job đều đang bị job khác giữ ⇒ hoàn tất, KHÔNG thu tiền, nói rõ (không ném lỗi rỗng)."""
    from apps.video_crawler import features
    from platform_core.models import JOB_DONE
    assert features.gianh_cho(db, "u1", "youtube", _A, "job-khac")
    adapter = AdapterGia()
    _dung_adapter(monkeypatch, adapter)
    job = _chay(db, _nop_tai(db, "u1", [_A]))
    assert job.status == JOB_DONE and adapter.da_tai == []
    assert job.result["credit_cost"] == 0 and job.result["bo_qua_trung"] == 1
    assert _so_du(db, "u1") == NAP_BAN_DAU


def test_huy_giua_chung_thi_xoa_dong_gianh_cho(db, kho, nguoi, monkeypatch):
    from platform_core import jobs as jobq
    from platform_core.models import JOB_CANCELLED, Job

    giu = {}

    def huy_truoc_muc_b(item):
        if item.id != _B:
            return
        assert _dong(_phien_moi()) >= {(_B, "dang_tai")}        # đã giành chỗ TRƯỚC khi tải
        s = _phien_moi()
        try:
            assert jobq.cancel(s, s.get(Job, giu["id"]))
            s.commit()
        finally:
            s.close()

    _dung_adapter(monkeypatch, AdapterGia(truoc_tai=huy_truoc_muc_b))
    giu["id"] = jid = _nop_tai(db, "u1", [_A, _B])
    assert _chay(db, jid).status == JOB_CANCELLED
    assert _dong(db) == set()                                    # cả mục a (đã lưu) lẫn b (đang tải) đều nhả
    adapter = AdapterGia()
    _dung_adapter(monkeypatch, adapter)
    _chay(db, _nop_tai(db, "u1", [_A, _B]))
    assert adapter.da_tai == [_A, _B]                            # lượt sau tải lại được


def test_moi_muc_loi_thi_xoa_dong_gianh_cho(db, kho, nguoi, monkeypatch):
    from apps.video_crawler.adapters.base import LoiCao
    from platform_core.models import JOB_ERROR
    _dung_adapter(monkeypatch, AdapterGia(loi={_A: LoiCao("rieng_tu", "Video riêng tư.", tam_thoi=False)}))
    assert _chay(db, _nop_tai(db, "u1", [_A])).status == JOB_ERROR
    assert _dong(db) == set()


def test_mot_phan_loi_chi_giu_dong_cua_muc_xong(db, kho, nguoi, monkeypatch):
    from apps.video_crawler.adapters.base import LoiCao
    _dung_adapter(monkeypatch, AdapterGia(loi={_B: LoiCao("rieng_tu", "Video riêng tư.", tam_thoi=False)}))
    job = _chay(db, _nop_tai(db, "u1", [_A, _B]))
    assert _dong(db) == {(_A, "xong")}
    from apps.video_crawler.tables import VcDaTai
    dong = db.query(VcDaTai).filter_by(owner_id="u1", video_id=_A).one()
    assert dong.job_id == job.id and dong.tep == f"video_crawler/u1/{job.id}/{_A}.mp4"


def test_khong_trung_nho_qua_30_ngay_ke_ca_khi_result_da_bi_don(db, kho, nguoi, monkeypatch):
    from apps.video_crawler import features
    from apps.video_crawler.tables import VcDaTai
    from platform_core.models import Job

    _dung_adapter(monkeypatch, AdapterGia())
    cu = _chay(db, _nop_tai(db, "u1", [_A]))
    # Mô phỏng 40 ngày sau: dọn nội dung job hết hạn đã xoá result, dòng dedup đã cũ.
    db.query(Job).filter_by(id=cu.id).update({"result": None})
    db.query(VcDaTai).update({"tao_luc": datetime.now(timezone.utc) - timedelta(days=40),
                              "cap_nhat_luc": datetime.now(timezone.utc) - timedelta(days=40)})
    db.commit()
    assert features.da_tai_ids(db, "u1", "youtube") == {_A}
    assert features.da_tai_ids(db, "u2", "youtube") == set()                    # cách ly theo user
    assert features.da_tai_ids(db, "u1", "tiktok") == set()

    adapter = AdapterGia(muc=[_muc(_A), _muc(_B)])
    _dung_adapter(monkeypatch, adapter)
    params = features.dung_params_tai(owner_id="u1", nen_tang="youtube",
                                      nguon={"che_do": "tu_khoa", "dau_vao": "meo", "so_luong": 2,
                                             "khong_trung": True}, phan_giai=_DNS)
    job = features.nop(db, owner_id="u1", job_type="video_crawler.tai", params=params)
    db.commit()
    job = _chay(db, job.id)
    assert adapter.da_tai == [_B] and job.result["bo_qua_trung"] == 1


def test_khong_trung_khong_bi_anh_huong_boi_user_khac(db, kho, nguoi, monkeypatch):
    _dung_adapter(monkeypatch, AdapterGia())
    _chay(db, _nop_tai(db, "u2", [_A]))
    adapter = AdapterGia()
    _dung_adapter(monkeypatch, adapter)
    _chay(db, _nop_tai(db, "u1", [_A]))
    assert adapter.da_tai == [_A]
    assert _dong(db, "u1") == {(_A, "xong")} and _dong(db, "u2") == {(_A, "xong")}


# ── Migration khớp ORM + governance ───────────────────────────────────────────

def _migration():
    p = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260923_0900_vc_da_tai.py"
    spec = importlib.util.spec_from_file_location("mig_vc_da_tai", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_noi_tiep_head_cu_va_khop_orm(tmp_path):
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from apps.video_crawler.tables import VcDaTai

    mig = _migration()
    assert mig.down_revision == "9c3e5a1d7f20"
    eng = sa.create_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    with eng.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            mig.upgrade()
    insp = sa.inspect(eng)
    cot = {c["name"]: c for c in insp.get_columns("vc_da_tai")}
    orm = VcDaTai.__table__
    assert set(cot) == {c.name for c in orm.columns}
    for c in orm.columns:
        assert cot[c.name]["nullable"] == c.nullable, c.name
    uq = {tuple(u["column_names"]) for u in insp.get_unique_constraints("vc_da_tai")}
    assert ("owner_id", "nen_tang", "video_id") in uq
    orm_uq = {tuple(c.name for c in u.columns) for u in orm.constraints if isinstance(u, sa.UniqueConstraint)}
    assert orm_uq <= uq
    idx = {i["name"]: tuple(i["column_names"]) for i in insp.get_indexes("vc_da_tai")}
    orm_idx = {i.name: tuple(c.name for c in i.columns) for i in orm.indexes}
    assert orm_idx == idx and ("owner_id",) in idx.values()
    with eng.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            mig.downgrade()
    assert "vc_da_tai" not in sa.inspect(eng).get_table_names()


def test_governance_khai_vc_da_tai():
    from platform_core.public_api import governance
    hang = governance.store_for("vc_da_tai")
    assert hang is not None and hang.klass == governance.CONTENT
