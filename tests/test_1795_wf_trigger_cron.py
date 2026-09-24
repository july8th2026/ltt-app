"""`trigger.cron` — bù lịch và DST, bằng `cronsim`, ⛔ không tự viết bộ lịch.

## Vì sao `cronsim` chứ không `croniter` (spec §8.2 nói `croniter`)

Đây là một **đổi ý so với spec**, và nó tra được chứ không phải một sở thích:

- `pallets-eco/croniter#258` (MỞ, 02/08/2026) — *"get_next skips a fire time
  when the DST shift is not a whole hour; get_prev and match disagree"*;
  `#259` — *"croniter_range stop test ignores the UTC offset: silently drops
  results and returns out-of-interval values"*. Hai lỗi còn mở, và cả hai đúng
  vào hai phép ta cần: **tiến** (lần bắn kế) và **lùi** (mốc lỡ gần nhất).
- `cronsim` (BSD-3-Clause, `cuu508/cronsim`, dùng trong Healthchecks) khai
  thẳng mục tiêu *"Correctness… match Debian's cron as closely as possible,
  including its quirky behaviour during DST transitions"*, và có `reverse=True`
  — thứ ta CẦN để trả lời *"mốc lịch gần nhất đã lỡ là mốc nào"*.

⭐ Bù lịch là một bài đã có người trả giá: n8n `#34628` / `#23906` — *"Missed
   schedule trigger can cause unexpectedly long delays"*. Và mặt kia của nó,
   n8n `#17187` — *"Scheduled tasks executing multiple times at once"* — là lý
   do khoá khử trùng mang **MỐC LỊCH**, không mang thời điểm bắn.

## ⛔ Tệp này KHÔNG trả lời

Không đo DST thật của một múi giờ CÓ DST trên máy này (Asia/Ho_Chi_Minh không
có DST). Phép `test_dst_mua_thu_khong_ban_hai_lan` dùng `America/New_York` —
nó kiểm **ta gọi thư viện đúng**, không kiểm lại chính thư viện; tác giả
`cronsim` đã có `TestDstTransitions` cho phần đó.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from datetime import datetime, timedelta, timezone

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

HCM = "Asia/Ho_Chi_Minh"


def _utc(y, mo, d, h=0, mi=0) -> datetime:
    """Naive-UTC, đúng quy ước cột `DateTime(timezone=True)` của kho này."""
    return datetime(y, mo, d, h, mi)


# ── Mô-đun trigger CRON ─────────────────────────────────────────────────────

def test_lan_ke_tiep_doi_sang_naive_UTC_theo_mui_gio():
    """07:00 giờ Việt Nam = 00:00 UTC. Sai múi giờ ở đây là một run chạy lệch
    7 tiếng mỗi ngày — và không ai thấy cho tới khi khách hỏi."""
    from platform_core.workflow import trigger

    m = trigger.SO_DANG_KY["CRON"]
    cfg = {"cron": "0 7 * * *", "tz": HCM}
    assert m.lan_ke_tiep(cfg, _utc(2026, 9, 24, 1, 0)) == _utc(2026, 9, 25, 0, 0)
    # …và STRICT: đứng đúng mốc thì lần kế là mốc SAU, không phải chính nó
    # (nếu không, `next_fire_at` không bao giờ tiến và trigger bắn vô hạn).
    assert m.lan_ke_tiep(cfg, _utc(2026, 9, 24, 0, 0)) == _utc(2026, 9, 25, 0, 0)


def test_moc_gan_nhat_la_moc_LO_MOI_NHAT_khong_phai_moc_cu_nhat():
    """Spec §8.2: *"`chay_mot_lan` ⇒ một run cho mốc **lỡ gần nhất**"*."""
    from platform_core.workflow import trigger

    m = trigger.SO_DANG_KY["CRON"]
    cfg = {"cron": "0 7 * * *", "tz": HCM}
    # Máy tắt 3 ngày. Mốc lỡ: 22, 23, 24 — phải lấy 24, ⛔ không phải 22.
    assert m.moc_gan_nhat(cfg, _utc(2026, 9, 24, 3, 0)) == _utc(2026, 9, 24, 0, 0)


def test_chu_ky_duoi_5_phut_bi_TU_CHOI_LUC_TAO(db):
    """Spec §8.2: *"Chu kỳ tối thiểu 5 phút"*. ⛔ Từ chối lúc TẠO, không lúc
    chạy: một trigger mỗi giây nằm trong CSDL là một cỗ máy tiêu credit."""
    from platform_core.workflow import trigger

    with pytest.raises(ValueError) as e:
        trigger.tao(db, workflow_id="w1", owner_id="u1", kind="CRON",
                    cau_hinh={"cron": "* * * * *", "tz": HCM})
    assert "5" in str(e.value) or "300" in str(e.value)
    # …và một chu kỳ HỢP LỆ vẫn phải qua được (không có vế này thì một
    # validator từ chối mọi thứ cũng xanh).
    t = trigger.tao(db, workflow_id="w1", owner_id="u1", kind="CRON",
                    cau_hinh={"cron": "*/5 * * * *", "tz": HCM})
    assert t.next_fire_at is not None


@pytest.mark.parametrize("cfg", [
    {"cron": "khong phai cron", "tz": HCM},
    {"cron": "0 7 * * *", "tz": "Khong/Co_That"},
    {"cron": "", "tz": HCM},
])
def test_cau_hinh_cron_HONG_bi_tu_choi_luc_tao(db, cfg):
    from platform_core.workflow import trigger

    with pytest.raises(ValueError):
        trigger.tao(db, workflow_id="w1", owner_id="u1", kind="CRON",
                    cau_hinh=cfg)


def test_dst_mua_thu_khong_ban_hai_lan():
    """⚠️ Phép này kiểm **ta gọi thư viện đúng**, không kiểm lại thư viện.

    02/11/2025, `America/New_York` lùi 1 giờ lúc 02:00 — 01:30 xảy ra HAI lần.
    Lịch `30 1 * * *` phải cho ĐÚNG MỘT mốc trong ngày đó.
    """
    from platform_core.workflow import trigger

    m = trigger.SO_DANG_KY["CRON"]
    cfg = {"cron": "30 1 * * *", "tz": "America/New_York"}
    moc = []
    luc = _utc(2025, 11, 2, 0, 0)
    for _ in range(3):
        luc = m.lan_ke_tiep(cfg, luc)
        moc.append(luc)
    trong_ngay = [x for x in moc if x.date().isoformat() in ("2025-11-02",
                                                             "2025-11-03")]
    assert len(trong_ngay) == len(set(trong_ngay))
    assert len(moc) == len(set(moc)), moc


# ── Bắn thật: tạo run, khử trùng theo MỐC ──────────────────────────────────

@pytest.fixture()
def wf(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: {})
    credit.nap(db, "u1", 100_000, note="test")
    w = dinh_nghia.tao_workflow(db, owner_id="u1", name="cron")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": [
            {"id": "s", "type": "core.set", "position": {"x": 0, "y": 0},
             "params": {"bien": {"a": "1"}}}], "edges": []}]})
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu={})
    w.published_version_id = v.id
    db.flush()
    return w


def _trigger(db, wf, **cfg):
    from platform_core.workflow import trigger
    return trigger.tao(db, workflow_id=wf.id, owner_id="u1", kind="CRON",
                       cau_hinh={"cron": "0 7 * * *", "tz": HCM, **cfg})


def test_ban_tao_run_va_day_next_fire_at(db, wf):
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger

    t = _trigger(db, wf)
    t.next_fire_at = _utc(2026, 9, 24, 0, 0)
    db.flush()
    kq = ban_trigger.ban_den_han(db, bay_gio=_utc(2026, 9, 24, 0, 1))
    assert kq["da_ban"] == 1
    assert db.query(WorkflowRun).filter_by(trigger_kind="cron").count() == 1
    assert t.next_fire_at == _utc(2026, 9, 25, 0, 0)
    assert t.last_fired_at is not None and t.loi_lien_tiep == 0


def test_ban_HAI_LAN_cung_MOC_chi_mot_run(db, wf):
    """n8n `#17187`: khoá theo lúc bắn ⇒ một mốc bắn hai lần là hai run.
    Khoá theo MỐC ⇒ bắn mấy lần cũng đúng một run."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger

    t = _trigger(db, wf)
    luc = _utc(2026, 9, 24, 0, 1)
    t.next_fire_at = _utc(2026, 9, 24, 0, 0)
    db.flush()
    ban_trigger.ban_den_han(db, bay_gio=luc)
    # Giả lập một tiến trình thứ hai quay lại đúng mốc cũ.
    t.next_fire_at = _utc(2026, 9, 24, 0, 0)
    db.flush()
    ban_trigger.ban_den_han(db, bay_gio=luc)
    assert db.query(WorkflowRun).filter_by(trigger_kind="cron").count() == 1


def test_LO_LICH_chay_mot_lan_ban_DUNG_MOT_run_cho_moc_GAN_NHAT(db, wf):
    """Máy tắt 3 ngày ⇒ ⛔ không bắn bù 3 run. Một run, cho mốc gần nhất."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger, khoa_idem

    t = _trigger(db, wf, bo_lo="chay_mot_lan")
    t.next_fire_at = _utc(2026, 9, 21, 0, 0)
    db.flush()
    kq = ban_trigger.ban_den_han(db, bay_gio=_utc(2026, 9, 24, 3, 0))
    assert kq["da_ban"] == 1
    runs = db.query(WorkflowRun).filter_by(trigger_kind="cron").all()
    assert len(runs) == 1
    assert runs[0].idempotency_key == khoa_idem.khoa_cron(
        t.id, _utc(2026, 9, 24, 0, 0)), "phai la moc GAN NHAT, khong phai 21/09"
    assert t.next_fire_at == _utc(2026, 9, 25, 0, 0)


def test_LO_LICH_bo_qua_KHONG_ban_nhung_van_day_lich(db, wf):
    """⛔ Không bắn, nhưng `next_fire_at` **phải** tiến — nếu không, trigger
    đứng mãi ở một mốc quá khứ và mỗi vòng quét lại nhặt nó lên."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger

    t = _trigger(db, wf, bo_lo="bo_qua")
    t.next_fire_at = _utc(2026, 9, 21, 0, 0)
    db.flush()
    kq = ban_trigger.ban_den_han(db, bay_gio=_utc(2026, 9, 24, 3, 0))
    assert kq["da_ban"] == 0 and kq["bo_qua"] == 1
    assert db.query(WorkflowRun).filter_by(trigger_kind="cron").count() == 0
    assert t.next_fire_at == _utc(2026, 9, 25, 0, 0)


def test_bo_qua_van_ban_khi_CHI_VUA_toi_han(db, wf):
    """ĐỐI CHỨNG cho phép trên: `bo_qua` chặn **bù lịch**, không chặn lịch.
    Không có vế này thì một `bo_qua` chặn mọi thứ cũng xanh."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger

    t = _trigger(db, wf, bo_lo="bo_qua")
    t.next_fire_at = _utc(2026, 9, 24, 0, 0)
    db.flush()
    ban_trigger.ban_den_han(db, bay_gio=_utc(2026, 9, 24, 0, 2))
    assert db.query(WorkflowRun).filter_by(trigger_kind="cron").count() == 1


def test_trigger_TAT_khong_bao_gio_ban(db, wf):
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger

    t = _trigger(db, wf)
    t.next_fire_at = _utc(2026, 9, 24, 0, 0)
    t.enabled = False
    db.flush()
    ban_trigger.ban_den_han(db, bay_gio=_utc(2026, 9, 24, 0, 1))
    assert db.query(WorkflowRun).filter_by(trigger_kind="cron").count() == 0


def test_NAM_LAN_LOI_LIEN_TIEP_thi_TU_TAT(db, wf):
    """Spec §11.4: *"5 lần lỗi liên tiếp ⇒ tự tắt trigger"*.

    ⛔ Không tự tắt = một trigger hỏng gọi `tao_run` mỗi 5 giây, mãi mãi.
    """
    from platform_core.workflow import ban_trigger, tao_run

    t = _trigger(db, wf)

    def _no(*a, **k):
        raise RuntimeError("gia lap loi")

    goc = tao_run.tao_run
    tao_run.tao_run = _no
    try:
        for i in range(5):
            t.next_fire_at = _utc(2026, 9, 24, 0, 0) + timedelta(days=i)
            db.flush()
            ban_trigger.ban_den_han(
                db, bay_gio=_utc(2026, 9, 24, 0, 1) + timedelta(days=i))
    finally:
        tao_run.tao_run = goc
    assert t.loi_lien_tiep >= ban_trigger.TRAN_LOI_LIEN_TIEP
    assert t.enabled is False


def test_mot_trigger_LOI_khong_chan_trigger_LANH(db, wf):
    """Cùng hình dạng cách ly lỗi với `dong_co.mot_vong` (Important #1): một
    hàng hỏng luôn đứng đầu mọi lượt quét sau, nên nó sẽ nghẽn vĩnh viễn."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import ban_trigger

    hong = _trigger(db, wf)
    lanh = _trigger(db, wf)
    hong.config = {"cron": "0 7 * * *", "tz": "Khong/Co_That"}
    hong.next_fire_at = _utc(2026, 9, 24, 0, 0)
    lanh.next_fire_at = _utc(2026, 9, 24, 0, 0)
    db.flush()
    kq = ban_trigger.ban_den_han(db, bay_gio=_utc(2026, 9, 24, 0, 1))
    assert kq["loi"] == 1 and kq["da_ban"] == 1
    assert db.query(WorkflowRun).filter_by(trigger_kind="cron").count() == 1


def test_khoa_cron_dung_MUI_GIO_khong_phai_gio_may(db, wf):
    """Khoá mang mốc **naive-UTC**, nên hai tiến trình ở hai múi giờ hệ điều
    hành khác nhau vẫn sinh **cùng** một khoá cho cùng một mốc."""
    from platform_core.workflow import khoa_idem

    moc = _utc(2026, 9, 24, 0, 0)
    a = khoa_idem.khoa_cron("t1", moc)
    b = khoa_idem.khoa_cron("t1", moc.replace(tzinfo=timezone.utc))
    assert a == b
