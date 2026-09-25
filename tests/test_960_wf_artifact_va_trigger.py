"""LTT WORKFLOW V2 · Đợt 5.1 + 5.4 — artifact tự mô tả backend, và trigger mô-đun.

## 5.1 — `artifact.id = "<backend>:<key>"` (`G33` `G35` `G36`)

🔴 Đây là bản vá cho một lỗ **sẽ nổ**, không phải một lỗ đang nổ: ngày LTT bật
   R2 **song song** Local, `storage.get_storage()` là một singleton toàn cục ⇒
   **mọi khoá cũ thành mơ hồ**. Một `"abc/def.png"` trong `output_ref` của bước
   trước không nói nó nằm ở đâu.

⭐ Bài học n8n (`05 §4.1`): id **tự mô tả backend**, vì tham chiếu đi vào `output_ref`
   của bước sau và **JSONB không tra bảng được**.

⚠️ Hợp đồng lưu trữ có `delete` **TUỲ CHỌN**: backend nào có vòng đời riêng
   (R2 lifecycle) thì **không** ép nó tự xoá — đừng chồng TTL của ta lên TTL
   của R2.

## 5.4 — mỗi loại trigger là một MÔ-ĐUN (`G42`)

Bài học Windmill: 11 crate trigger, không phải 11 nhánh `if`. Ngưỡng: **thêm
loại thứ tư không sửa `platform_core`**.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def _bay_gio():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wfa.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


# ── 5.1 Artifact ─────────────────────────────────────────────────────────────

def test_id_artifact_TU_MO_TA_backend(db):
    from platform_core.workflow import artifact

    a = artifact.ghi_danh(db, owner_id="u1", backend="r2", key="a/b.png",
                          kind="image", ttl_class="RUN")
    db.commit()
    assert a.id == "r2:a/b.png"
    assert artifact.tach_id(a.id) == ("r2", "a/b.png")


def test_hai_backend_CUNG_KEY_khong_mo_ho(db):
    """🔴 Chính là lỗ sẽ nổ khi R2 chạy song song Local."""
    from platform_core.workflow import artifact

    a = artifact.ghi_danh(db, owner_id="u1", backend="local", key="x.png",
                          kind="image", ttl_class="RUN")
    b = artifact.ghi_danh(db, owner_id="u1", backend="r2", key="x.png",
                          kind="image", ttl_class="RUN")
    db.commit()
    assert a.id != b.id


def test_backend_bia_dat_bi_TU_CHOI(db):
    from platform_core.workflow import artifact

    with pytest.raises(ValueError, match="backend"):
        artifact.ghi_danh(db, owner_id="u1", backend="dropbox", key="x",
                          kind="file", ttl_class="RUN")


def test_key_chua_DAU_HAI_CHAM_bi_tu_choi(db):
    """Nếu key chứa `:` thì `tach_id` không còn tách đúng được nữa."""
    from platform_core.workflow import artifact

    with pytest.raises(ValueError):
        artifact.ghi_danh(db, owner_id="u1", backend="local", key="a:b",
                          kind="file", ttl_class="RUN")


def test_LINEAGE_tro_ve_anh_chup_da_sinh_ra_no(db):
    """⭐ `created_by_snapshot_id` — trả lời "tệp này từ đâu ra" bằng một cột."""
    from platform_core.workflow import artifact

    a = artifact.ghi_danh(db, owner_id="u1", backend="local", key="k",
                          kind="image", ttl_class="RUN",
                          created_by_snapshot_id="snap-1")
    db.commit()
    assert a.created_by_snapshot_id == "snap-1"


def test_ttl_class_PERMANENT_khong_co_han(db):
    from platform_core.workflow import artifact

    a = artifact.ghi_danh(db, owner_id="u1", backend="local", key="k",
                          kind="image", ttl_class="PERMANENT")
    db.commit()
    assert a.expires_at is None


def test_ttl_class_khac_thi_CO_han(db):
    from platform_core.workflow import artifact

    for lop in ("EPHEMERAL", "RUN", "PROJECT"):
        a = artifact.ghi_danh(db, owner_id="u1", backend="local",
                              key=f"k-{lop}", kind="image", ttl_class=lop)
        assert a.expires_at is not None, lop


def test_quet_HET_HAN_khong_dung_toi_PERMANENT(db):
    from platform_core.workflow import artifact

    artifact.ghi_danh(db, owner_id="u1", backend="local", key="vinh_vien",
                      kind="image", ttl_class="PERMANENT")
    cu = artifact.ghi_danh(db, owner_id="u1", backend="local", key="cu",
                           kind="image", ttl_class="EPHEMERAL")
    cu.expires_at = _bay_gio() - timedelta(days=1)
    db.commit()

    assert [a.id for a in artifact.het_han(db)] == ["local:cu"]


def test_PERMANENT_co_expires_at_VAN_khong_bi_quet(db):
    """⭐ Bài này ghim cái RÀO `ttl_class <> 'PERMANENT'`, không ghim hệ quả.

    Đối chứng vừa cho thấy: gỡ vế ấy khỏi `het_han()` thì **không phép kiểm nào
    đỏ** — vì `PERMANENT` luôn có `expires_at IS NULL`, nên vế `is_not(None)`
    đã đủ. Tức cái rào là **mã chết**, và bài trên xanh vì một lý do khác lý do
    nó khai.

    Ở đây ta đặt `expires_at` cho một artifact `PERMANENT` — trạng thái sai
    nhưng **dựng được**, và nó dựng được bằng đúng một lệnh `UPDATE` tay. Rào
    phải chặn nó. Đó là cách duy nhất cái rào có nghĩa: nó phòng đúng một
    chuyện — dữ liệu lệch, không phải mã lệch.
    """
    from platform_core.workflow import artifact

    vinh_vien = artifact.ghi_danh(db, owner_id="u1", backend="local",
                                  key="vinh_vien", kind="image",
                                  ttl_class="PERMANENT")
    vinh_vien.expires_at = _bay_gio() - timedelta(days=30)   # <- du lieu lech
    db.commit()

    assert artifact.het_han(db) == [], (
        "PERMANENT co han sai van KHONG duoc quet — no la du lieu vinh vien")


def test_backend_co_VONG_DOI_RIENG_thi_ta_KHONG_tu_xoa(db):
    """⚠️ Bài học n8n: `delete` là **tuỳ chọn** của hợp đồng lưu trữ.

    R2 có lifecycle rule của chính nó. Chồng TTL của ta lên trên là hai bộ đếm
    cùng nhắm một tệp, và bộ nào chạy trước thì bộ kia thao tác trên hư không.
    """
    from platform_core.workflow import artifact

    assert artifact.ta_tu_xoa("local") is True
    assert artifact.ta_tu_xoa("r2") is False


# ── 5.4 Trigger ──────────────────────────────────────────────────────────────

def test_moi_loai_trigger_la_MOT_mo_dun(db):
    """⭐ `CRON` và `EVENT` thêm vào ở plan wf-v2 P4 (spec §8.2) — và nó vào bằng đúng
    cách mà `test_them_loai_THU_NAM…` bên dưới đòi: một lớp + một `dang_ky()`,
    không một nhánh `if` nào trong lõi.

    `SCHEDULE` (theo giây) còn ở đây vì hàng cũ trong CSDL vẫn mang loại ấy;
    spec §8.2 nói nó **bị thay** bởi `cron`, và việc di trú các hàng ấy chưa
    làm — xem báo cáo P4 task 7.

    ⭐ `PIECE_POLL` (25/09, làn wft): sống ngoài `trigger.py` (`poll_connector.py`,
    spec §11.4 FLOW D) — cùng khuôn `G42` (lõi không biết tên loại). Trước
    25/09 nó chỉ có mặt trong `SO_DANG_KY` khi có TEST KHÁC chạy trước đã
    import `poll_connector`/`ban_trigger` (đỏ khi chạy chung cả cụm, xanh khi
    chạy một mình — xem `test_4290_wf_trigger_dang_ky_tat_dinh.py`). Vá:
    `platform_core/workflow/__init__.py` giờ tự import `poll_connector` lúc
    gói được chạm tới (cùng khuôn `nut_loi/__init__.py` dùng cho `_SO`), nên
    `SO_DANG_KY` giờ LUÔN có `PIECE_POLL` — tất định, không phụ thuộc thứ tự
    import của phiên test.
    """
    from platform_core.workflow import trigger

    assert set(trigger.SO_DANG_KY) == {"MANUAL", "API", "SCHEDULE", "WEBHOOK",
                                       "CRON", "EVENT", "PIECE_POLL"}


def test_them_loai_THU_NAM_khong_sua_platform_core(db):
    """🔴 Ngưỡng của `G42`: thêm loại mới là **đăng ký**, không phải sửa lõi.

    Bài học Windmill: 11 crate trigger, không phải 11 nhánh `if` trong lõi.
    """
    from platform_core.workflow import trigger

    class _Nhip:
        kind = "NHIP_TIM"

        def toi_han(self, cau_hinh, bay_gio):
            return True

        def lan_ke_tiep(self, cau_hinh, bay_gio):
            return bay_gio + timedelta(seconds=int(cau_hinh["moi_giay"]))

    trigger.dang_ky(_Nhip())
    try:
        assert "NHIP_TIM" in trigger.SO_DANG_KY
        t = trigger.tao(db, workflow_id="w1", owner_id="u1", kind="NHIP_TIM",
                        cau_hinh={"moi_giay": 30})
        db.commit()
        assert t.next_fire_at is not None
    finally:
        trigger.go_dang_ky("NHIP_TIM")


def test_loai_CHUA_dang_ky_bi_tu_choi_LUC_TAO(db):
    from platform_core.workflow import trigger

    with pytest.raises(ValueError, match="chua dang ky"):
        trigger.tao(db, workflow_id="w1", owner_id="u1", kind="TELEPATHY",
                    cau_hinh={})


def test_chi_lay_trigger_DANG_BAT_va_DEN_HAN(db):
    from platform_core.workflow import trigger

    a = trigger.tao(db, workflow_id="w1", owner_id="u1", kind="SCHEDULE",
                    cau_hinh={"moi_giay": 60})
    a.next_fire_at = _bay_gio() - timedelta(seconds=1)
    b = trigger.tao(db, workflow_id="w2", owner_id="u1", kind="SCHEDULE",
                    cau_hinh={"moi_giay": 60})
    b.next_fire_at = _bay_gio() - timedelta(seconds=1)
    b.enabled = False
    c = trigger.tao(db, workflow_id="w3", owner_id="u1", kind="SCHEDULE",
                    cau_hinh={"moi_giay": 60})
    c.next_fire_at = _bay_gio() + timedelta(hours=1)
    db.commit()

    assert [t.workflow_id for t in trigger.den_han(db)] == ["w1"]


def test_MANUAL_khong_co_lich_nen_KHONG_bao_gio_den_han(db):
    """Một trigger thủ công mà tự chạy được là một lượt chạy không ai bấm."""
    from platform_core.workflow import trigger

    t = trigger.tao(db, workflow_id="w1", owner_id="u1", kind="MANUAL",
                    cau_hinh={})
    db.commit()
    assert t.next_fire_at is None
    assert trigger.den_han(db) == []
