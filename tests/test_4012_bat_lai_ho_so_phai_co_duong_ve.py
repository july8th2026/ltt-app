"""Bật lại một hồ sơ bị hạ phải KHẢ THI — điều kiện hiện tại là bất khả thi.

## Số học, không phải ý kiến

`profiles.py` khai ba nhịp, và chúng nói rõ ai sinh ra bằng chứng nào, bao lâu một lần:

    HEALTH_REFRESH_SECONDS     =  600     # ta tu do suc khoe
    RUNTIME_COLLECTOR_SECONDS  = 1800     # MAY B sinh ban runtime
    RUNTIME_SYNC_SECONDS       =  600     # thoi gian guong ve
    RUNTIME_MAX_AGE_SECONDS    = 2*1800 + 600 = 4200   # nguong BINH THUONG
    ACTIVATION_MAX_AGE_SECONDS =  300     # cua so chat cua nguoi van hanh

`activate_profile` truyền **cùng một `max_age_seconds`** cho **cả hai** cửa sổ:

    health_prerequisites(db, profile.id,
                         max_age_seconds=max_age_seconds,          # quan sat CUA TA
                         generated_max_age_seconds=max_age_seconds, # ban sinh CUA MAY B
                         thanh_phan=REQUIRED_HEALTH_COMPONENTS)

⇒ Nó đòi bản sinh của máy B **tươi hơn 300 giây**, trong khi máy B chỉ sinh mỗi
  **1800 giây**. Trung bình bản mới nhất đã **900 giây** tuổi, tệ nhất là 1800+600.
  ⇒ Điều kiện **không thể thoả** trừ khi bấm đúng trong 300 giây sau một lần sinh.

## Vì sao nó thành một cái bẫy chết người

`admin_profiles._configured_preflight` hạ hồ sơ (`accept_new = False`,
`is_default = False`) khi **bất kỳ** ngoại lệ nào xảy ra — kể cả một khoá API hết
hạn, thứ đã xảy ra thật sáng 25/09/2026. Đường về duy nhất là `activate_profile`.
⇒ Một khoá hết hạn có thể **đóng cửa hàng vĩnh viễn**, và người vận hành bấm "bật
  lại" sẽ nhận `ProfileNotReady: stale health component: runtime` mãi mãi mà ⛔
  không có cách nào làm nó hết.

⚠️ Hai phép kiểm "chứng minh nó chạy" (`test_1014`, `test_1024`) đều tự đặt
   `generated_at=now()`, tức chúng dựng một thế giới mà máy B vừa sinh xong đúng
   lúc — **hình dạng mà production ⛔ không bao giờ có**. Cùng cái bẫy với
   `test_289` và vòng chụp ảnh: một phép kiểm xanh giữ một đường chết.

## Thuốc: hai cửa sổ cho hai thứ khác nhau

Cửa sổ chặt là để nói *"bằng chứng phải vừa được đo XONG"* — điều đó nói về **phép
đo của ta**, thứ ta chạy được ngay trước khi bấm. Nó ⛔ không nói gì về nhịp của
máy B, và ⛔ không có quyền đòi máy B chạy nhanh hơn thiết kế.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import profiles

LUC = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


class _Hang:
    def __init__(self, *, tuoi_quan_sat=5, tuoi_ban_sinh=5, trang_thai="HEALTHY"):
        self.status = trang_thai
        self.observed_at = LUC - timedelta(seconds=tuoi_quan_sat)
        self.generated_at = LUC - timedelta(seconds=tuoi_ban_sinh)


class _Db:
    def __init__(self, hang):
        self._hang = hang

    def execute(self, _stmt):
        hang = self._hang

        class _R:
            @staticmethod
            def scalar_one_or_none():
                return hang
        return _R()


def test_ban_sinh_may_B_o_TUOI_BINH_THUONG_van_phai_bat_lai_duoc():
    """900 giây là tuổi **trung bình** của một bản sinh 1800 giây/lần.

    Nếu ca này đỏ thì đường bật lại là bất khả thi trong vận hành thật.
    """
    xong, ly_do, _ = profiles.health_prerequisites(
        _Db(_Hang(tuoi_quan_sat=5, tuoi_ban_sinh=900)), "ho-so-1", now=LUC,
        max_age_seconds=profiles.ACTIVATION_MAX_AGE_SECONDS,
        generated_max_age_seconds=profiles.ACTIVATION_GENERATED_MAX_AGE_SECONDS,
        thanh_phan=profiles.REQUIRED_HEALTH_COMPONENTS)
    assert xong is True, ly_do


def test_cua_so_ban_sinh_KHONG_duoc_chat_hon_nhip_may_B_sinh_ra():
    """Bất biến số học, chốt trực tiếp trên hằng số — ⛔ không qua một ca dữ liệu.

    Một cửa sổ chặt hơn nhịp sinh là một điều kiện **không thể thoả**, và nó ⛔
    không hỏng theo kiểu ồn ào: nó chỉ làm một đường không bao giờ đi được.
    """
    assert (profiles.ACTIVATION_GENERATED_MAX_AGE_SECONDS
            > profiles.RUNTIME_COLLECTOR_SECONDS), (
        f"doi ban sinh tuoi < {profiles.ACTIVATION_GENERATED_MAX_AGE_SECONDS}s "
        f"trong khi may B sinh moi {profiles.RUNTIME_COLLECTOR_SECONDS}s")


def test_quan_sat_CUA_TA_thi_van_phai_tuoi():
    """Cửa sổ chặt vẫn phải chặt ở chỗ nó có quyền chặt: phép đo của chính ta.

    Người vận hành chạy một lượt preflight ngay trước khi bấm, nên 300 giây là
    thoả được — và nó ngăn việc bật lại dựa trên một quan sát xanh từ hôm qua.
    """
    xong, ly_do, _ = profiles.health_prerequisites(
        _Db(_Hang(tuoi_quan_sat=3600, tuoi_ban_sinh=100)), "ho-so-1", now=LUC,
        max_age_seconds=profiles.ACTIVATION_MAX_AGE_SECONDS,
        generated_max_age_seconds=profiles.ACTIVATION_GENERATED_MAX_AGE_SECONDS,
        thanh_phan=profiles.REQUIRED_HEALTH_COMPONENTS)
    assert xong is False and "stale" in ly_do


def test_ban_sinh_THAT_SU_cu_thi_van_phai_chan():
    """⛔ Nới cửa sổ ⛔ không được thành bỏ cửa: máy B im hẳn thì phải chặn."""
    qua_cu = profiles.ACTIVATION_GENERATED_MAX_AGE_SECONDS + 600
    xong, ly_do, _ = profiles.health_prerequisites(
        _Db(_Hang(tuoi_quan_sat=5, tuoi_ban_sinh=qua_cu)), "ho-so-1", now=LUC,
        max_age_seconds=profiles.ACTIVATION_MAX_AGE_SECONDS,
        generated_max_age_seconds=profiles.ACTIVATION_GENERATED_MAX_AGE_SECONDS,
        thanh_phan=profiles.REQUIRED_HEALTH_COMPONENTS)
    assert xong is False and "stale" in ly_do


def test_activate_profile_dung_HAI_cua_so_khac_nhau(monkeypatch):
    """Chốt chỗ NỐI: `activate_profile` ⛔ không được truyền một số cho cả hai.

    🔴 Đây đúng là chỗ bản cũ sai — hai hằng số đã có sẵn và đều đúng, chỉ cái
       **nối** truyền lẫn chúng.
    """
    da_goi = {}

    def _bat(db, profile_id, **kw):
        da_goi.update(kw)
        return False, "dung lai o day", None

    monkeypatch.setattr(profiles, "health_prerequisites", _bat)

    class _DbHoSo:
        @staticmethod
        def execute(_stmt):
            class _R:
                @staticmethod
                def scalar_one_or_none():
                    return type("P", (), {"id": "ho-so-1"})()
            return _R()

    with pytest.raises(profiles.ProfileNotReady):
        profiles.activate_profile(_DbHoSo(), "ho-so-1")

    assert da_goi["max_age_seconds"] == profiles.ACTIVATION_MAX_AGE_SECONDS
    assert (da_goi["generated_max_age_seconds"]
            == profiles.ACTIVATION_GENERATED_MAX_AGE_SECONDS)
    assert (da_goi["generated_max_age_seconds"]
            != da_goi["max_age_seconds"]), (
        "hai cua so cho hai thu khac nhau — mot so cho ca hai la cai loi da sua")
