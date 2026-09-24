"""**FLOW D** trên PostgreSQL thật — điều kiện ra của P6 (spec §18.5).

| Flow | Đồ thị | Chứng minh |
|---|---|---|
| D | trigger poll → filter → app | **chỉ bản ghi mới tạo run; poll lần hai không trùng** |

## ⚠️ Phạm vi — đọc trước khi coi đây là "FLOW D đạt"

Phép này dùng **piece giả** cho lớp poll, ⛔ không phải Google Sheets thật.
Điều đó **cố ý**, và nó thu hẹp kết luận một cách cụ thể:

- ✅ Nó đo thứ FLOW D nói là phải đo: *chỉ bản ghi mới tạo run*, *lần poll thứ
  hai không tạo run trùng*, và cả hai lớp khử trùng cùng lúc trên **PostgreSQL
  thật** (nơi `ux_workflow_run_idem` thật sự ép, còn SQLite thì nuốt bề rộng
  `String(120)`).
- ⛔ Nó **không** đo rằng piece `google-sheets` trả về đúng hình dạng ta nghĩ.
  Không đo được: cần một service account của khách.
- 🔴 Và **quan trọng hơn**: đo 24/09 cho thấy piece `google-sheets` ở bản đã
  ghim **KHÔNG có trigger POLLING nào về dòng mới** — `google-sheets-new-or-
  updated-row` là `WEBHOOK`, mà trigger webhook của piece **ngoài phạm vi**
  (spec §11.4). Nên "trigger poll Sheets" của spec §18.5 **không tồn tại** ở
  bản này; hai trigger POLLING duy nhất là `new-spreadsheet` và `new-worksheet`.

## Vì sao PostgreSQL

`ux_workflow_run_idem` là chốt khử trùng cuối cùng, và nó chỉ **thật sự** ép
trên PostgreSQL. Cùng lý do `test_1787`/`test_1798`: SQLite không phân biệt
được bề rộng `String(120)` của `idempotency_key`, và nó nuốt im lặng.
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa

from platform_core.workflow.cong_cu import CongCu
from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()

#: Khoá advisory riêng cho tệp này (cùng lý do `test_1787._KHOA_LOCK_KEY`).
_KHOA_LOCK_KEY = 172012003505

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 1,
                          returns={"text": "text"})}


@pytest.fixture()
def pg(monkeypatch):
    url = pg_scratch.scratch_url()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    khoa_engine = sa.create_engine(url, future=True)
    khoa_conn = khoa_engine.connect()
    khoa_conn.execute(sa.text("SELECT pg_advisory_lock(:k)"),
                      {"k": _KHOA_LOCK_KEY})
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


@pytest.fixture()
def db(pg, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu
    from tests.conftest import bao_dam_user
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    s = next(pg.get_session())
    bao_dam_user(s, "u1")
    credit.nap(s, "u1", 10_000, note="test")
    s.commit()
    try:
        yield s
    finally:
        s.close()


_DEM = {"n": 0}


def _publish_wf(db):
    """Đồ thị FLOW D: `trigger.manual → set → app`.

    ⚠️ Node trigger trong ĐỒ THỊ vẫn là `trigger.manual`: trigger poll sống
       trong bảng `workflow_trigger`, ⛔ không trong đồ thị — `tao_run` nhận
       `trigger_kind` làm tham số. Phần "filter" của FLOW D là một `core.set`
       đọc `inputs.ban_ghi`, vì thứ đang được đo là **ai tạo run**, không phải
       bộ lọc biểu thức (đã có phép riêng ở P2/P3).
    """
    from platform_core.workflow import dinh_nghia
    _DEM["n"] += 1
    w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"flowd{_DEM['n']}")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": [
            {"id": "t", "type": "core.trigger.manual",
             "position": {"x": 0, "y": 0}, "params": {}},
        ], "edges": []}]})
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    db.commit()
    return w


def _trigger_poll(db, w, chu_ky_s=300):
    from platform_core.workflow import poll_connector as pc
    from platform_core.workflow import trigger as tg
    cau_hinh = pc.tao_cau_hinh(
        piece="@ltt/piece-gia", piece_version="0.0.0",
        ten_trigger="poll_gia", chu_ky_s=chu_ky_s)
    t = tg.tao(db, workflow_id=w.id, owner_id="u1", kind=pc.KIND,
               cau_hinh=cau_hinh)
    db.commit()
    return t


def _goi_gia(ban_ghi):
    """Thay lớp gọi runner. ⛔ KHÔNG thay logic khử trùng — thứ đang được đo.

    ⭐ Nó mô phỏng đúng hành vi của một trigger POLLING: trả về **những bản ghi
       chưa thấy**, và tự nhớ đã thấy gì. Hành vi ấy được đo **thật** (trong
       AppContainer, qua `runner.js`) ở `test_3506`; ở đây ta cần một nguồn
       **quyết định được** để nói về phần CSDL.
    """
    trang_thai = {"da_thay": set()}

    def goi(db, t):
        moi = [b for b in ban_ghi if str(b["id"]) not in trang_thai["da_thay"]]
        trang_thai["da_thay"].update(str(b["id"]) for b in moi)
        return moi

    return goi, trang_thai


# ── FLOW D ─────────────────────────────────────────────────────────────────

def test_FLOW_D_chi_ban_ghi_MOI_tao_run_va_poll_lan_hai_KHONG_TRUNG(db):
    """🔴 Điều kiện ra của P6 (spec §18.5, dòng D)."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import poll_connector as pc

    w = _publish_wf(db)
    t = _trigger_poll(db, w)
    goi, _ = _goi_gia([{"id": "r1", "ten": "a"}, {"id": "r2", "ten": "b"}])
    from datetime import datetime, timezone
    luc = datetime.now(timezone.utc).replace(tzinfo=None)

    # Lượt 1: hai bản ghi mới ⇒ hai run.
    assert pc.mot_luot_poll(db, t, moc=luc, goi=goi) == 2
    db.commit()
    assert db.query(WorkflowRun).filter_by(workflow_id=w.id).count() == 2

    # Lượt 2: piece không trả bản ghi nào ⇒ KHÔNG run mới.
    assert pc.mot_luot_poll(db, t, moc=luc, goi=goi) == 0
    db.commit()
    assert db.query(WorkflowRun).filter_by(workflow_id=w.id).count() == 2


def test_STORE_MAT_ma_van_KHONG_tao_run_trung(db):
    """🔴 Lớp khử trùng thứ hai, và vì sao cần nó.

    Store của piece **mất được**: khôi phục CSDL, sửa tay, một `xoa_pham_vi`
    nhầm. Khi ấy lần poll kế tiếp coi **mọi** bản ghi là mới. Không có khoá
    `poll:<trigger>:<ban_ghi>` thì đó là *tạo lại run cho cả lịch sử*, tức
    **tiêu credit thật**.

    Ở đây ta mô phỏng đúng sự cố ấy: một `goi` **quên sạch**, luôn trả về cả
    hai bản ghi.
    """
    from platform_core.models import WorkflowRun
    from platform_core.workflow import poll_connector as pc
    from datetime import datetime, timezone

    w = _publish_wf(db)
    t = _trigger_poll(db, w)
    ban_ghi = [{"id": "r1"}, {"id": "r2"}]

    def goi_quen_sach(db_, t_):
        return list(ban_ghi)

    luc = datetime.now(timezone.utc).replace(tzinfo=None)
    assert pc.mot_luot_poll(db, t, moc=luc, goi=goi_quen_sach) == 2
    db.commit()
    assert pc.mot_luot_poll(db, t, moc=luc, goi=goi_quen_sach) == 0
    db.commit()
    assert db.query(WorkflowRun).filter_by(workflow_id=w.id).count() == 2


def test_DOI_CHUNG_ban_ghi_THU_BA_van_tao_duoc_run(db):
    """⛔ Không có phép này, "0 run mới" ở trên có thể chỉ là *"poll không bao
    giờ tạo run"* — tức một trigger chết, và mọi phép trên đều xanh."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import poll_connector as pc
    from datetime import datetime, timezone

    w = _publish_wf(db)
    t = _trigger_poll(db, w)
    luc = datetime.now(timezone.utc).replace(tzinfo=None)
    pc.mot_luot_poll(db, t, moc=luc, goi=lambda d, x: [{"id": "r1"}])
    db.commit()
    pc.mot_luot_poll(db, t, moc=luc, goi=lambda d, x: [{"id": "r3"}])
    db.commit()
    assert db.query(WorkflowRun).filter_by(workflow_id=w.id).count() == 2


def test_ban_ghi_KHONG_co_id_van_khu_trung_duoc_theo_NOI_DUNG(db):
    """Một bản ghi không có `id` phải băm **nội dung**, ⛔ không lấy chỉ số
    trong danh sách: thứ tự của một API bên thứ ba không phải hợp đồng, và một
    bản ghi chen vào giữa sẽ làm mọi chỉ số sau nó trỏ sang bản ghi khác."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import poll_connector as pc
    from datetime import datetime, timezone

    w = _publish_wf(db)
    t = _trigger_poll(db, w)
    luc = datetime.now(timezone.utc).replace(tzinfo=None)
    pc.mot_luot_poll(db, t, moc=luc, goi=lambda d, x: [{"ten": "A"}])
    db.commit()
    # Cùng nội dung, nhưng nay đứng SAU một bản ghi mới ⇒ chỉ số đổi.
    pc.mot_luot_poll(db, t, moc=luc,
                     goi=lambda d, x: [{"ten": "B"}, {"ten": "A"}])
    db.commit()
    assert db.query(WorkflowRun).filter_by(workflow_id=w.id).count() == 2


def test_TRAN_ban_ghi_MOT_LUOT_cat_bot_khong_tao_100_run(db):
    """Lượt poll ĐẦU TIÊN của một Sheet 50 000 dòng. Mỗi bản ghi là một run có
    **giữ credit**; không có trần thì một lần bật trigger khoá sạch ví khách."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import poll_connector as pc
    from datetime import datetime, timezone

    w = _publish_wf(db)
    t = _trigger_poll(db, w)
    nhieu = [{"id": f"r{i}"} for i in range(pc.TRAN_BAN_GHI_MOI_LUOT + 25)]
    luc = datetime.now(timezone.utc).replace(tzinfo=None)
    so = pc.mot_luot_poll(db, t, moc=luc, goi=lambda d, x: nhieu)
    db.commit()
    assert so == pc.TRAN_BAN_GHI_MOI_LUOT
    assert (db.query(WorkflowRun).filter_by(workflow_id=w.id).count()
            == pc.TRAN_BAN_GHI_MOI_LUOT)


# ── Cấu hình + vòng bắn ────────────────────────────────────────────────────

def test_chu_ky_duoi_300s_bi_TU_CHOI_luc_TAO(db):
    """⛔ Từ chối lúc CHẠY thì khách đã lưu được một thứ không chạy."""
    from platform_core.workflow import poll_connector as pc
    with pytest.raises(pc.LoiPoll):
        pc.tao_cau_hinh(piece="@ltt/piece-gia", piece_version="0.0.0",
                        ten_trigger="poll_gia", chu_ky_s=5)


def test_ban_den_han_DI_QUA_duong_poll_va_day_lich(db):
    """Vòng bắn chung phải gọi `PiecePoll.ban`, ⛔ không tạo một run lịch.

    Nếu `ban_trigger` bỏ qua hợp đồng mở rộng, phép này thấy **1** run (run của
    mốc lịch) thay vì **2** (hai bản ghi) — và đó đúng là ca hỏng.
    """
    from datetime import datetime, timezone

    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger, poll_connector as pc

    w = _publish_wf(db)
    t = _trigger_poll(db, w)
    luc = datetime.now(timezone.utc).replace(tzinfo=None)
    t.next_fire_at = luc
    db.flush()

    goc = pc.PiecePoll.ban

    def ban_gia(self, db_, t_, *, moc, la_bu):
        return pc.mot_luot_poll(db_, t_, moc=moc,
                                goi=lambda d, x: [{"id": "a"}, {"id": "b"}])

    pc.PiecePoll.ban = ban_gia
    try:
        ra = ban_trigger.ban_den_han(db, bay_gio=luc)
    finally:
        pc.PiecePoll.ban = goc
    db.commit()
    assert ra["da_ban"] == 1
    assert db.query(WorkflowRun).filter_by(workflow_id=w.id).count() == 2
    db.refresh(t)
    assert t.next_fire_at is not None and t.next_fire_at > luc
