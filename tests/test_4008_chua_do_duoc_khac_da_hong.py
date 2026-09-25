""""Chưa đo được" ⛔ không phải "đã đo và nó hỏng" — và phân biệt hai cái ⛔ không
được nới cửa bán một milimet.

## Ca thật 25/09/2026

Consumer key OVH hết hạn (tạo với hạn 30 ngày, ngày hết hạn ghi sẵn trong tài liệu,
⛔ không hệ thống nào canh ngày đó). Hậu quả trong mã:

`run_configured_profile_preflight` gọi `provider.health()` **trước** khi đo bất kỳ
thành phần nào, nên nó nổ ở đó. `refresh_active_profiles` bắt ngoại lệ và ghi
`CRITICAL` cho **cả bốn** thành phần `CHAN_BAN` — kể cả `compute` (Proxmox), thứ
hoàn toàn khoẻ và **chưa hề được hỏi**. Chủ dự án chỉ thấy *"Hệ thống đang bảo trì"*
ở cửa hàng, và mất sáu phép đo mới lần ra một khoá API hết hạn.

## Vì sao sửa được mà không nới cửa bán

`health_prerequisites` chặn ở `row.status != "HEALTHY"` (`profiles.py:150`) — nó ⛔
**không** đòi `CRITICAL`. Nên `UNKNOWN` fail-closed y hệt. Đổi `CRITICAL` → `UNKNOWN`
là một thay đổi về **sự thật**, ⛔ không phải về **chính sách**.

⚠️ Và đó chính là chỗ phép kiểm này phải đứng canh: nếu một ngày ai đó "dọn dẹp"
   thành `if row.status == "CRITICAL"` thì cửa bán mở ra trong im lặng cho mọi
   profile chưa đo được. Một lỗi như vậy ⛔ không có triệu chứng — nó chỉ bán máy
   trên một hạ tầng không ai biết còn sống hay không.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import profiles

LUC = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


class _Hang:
    def __init__(self, trang_thai):
        self.status = trang_thai
        self.observed_at = LUC - timedelta(seconds=5)
        self.generated_at = LUC - timedelta(seconds=5)


class _KetQua:
    def __init__(self, hang):
        self._hang = hang

    def scalar_one_or_none(self):
        return self._hang


class _Db:
    """Trả cùng một hàng sức khoẻ cho mọi thành phần được hỏi."""

    def __init__(self, hang):
        self._hang = hang

    def execute(self, _stmt):
        return _KetQua(self._hang)


@pytest.mark.parametrize("trang_thai", ["UNKNOWN", "CRITICAL", "WARNING",
                                        "DEGRADED", ""])
def test_moi_trang_thai_KHAC_HEALTHY_deu_chan_ban(trang_thai):
    """Fail-closed theo nghĩa mạnh: chỉ `HEALTHY` mới mở, ⛔ không phải "khác
    CRITICAL thì mở". Đây là bất biến cho phép khai `UNKNOWN` trung thực."""
    xong, ly_do, _ = profiles.health_prerequisites(
        _Db(_Hang(trang_thai)), "ho-so-1", now=LUC)
    assert xong is False, f"{trang_thai!r} phai chan ban"
    assert trang_thai in ly_do or "unhealthy" in ly_do


def test_HEALTHY_thi_mo():
    xong, ly_do, _ = profiles.health_prerequisites(
        _Db(_Hang("HEALTHY")), "ho-so-1", now=LUC)
    assert xong is True and ly_do == ""


def test_thieu_hang_suc_khoe_cung_chan_ban():
    """Không có bản ghi nào ⇒ chặn. "Chưa đo" ⛔ không bao giờ được thành "ổn"."""
    xong, ly_do, _ = profiles.health_prerequisites(_Db(None), "ho-so-1", now=LUC)
    assert xong is False and "missing" in ly_do


# ── Vòng làm mới định kỳ ghi UNKNOWN, ⛔ không phải CRITICAL ─────────────────

def test_preflight_no_som_thi_ghi_UNKNOWN_kem_nguyen_nhan_phan_loai_duoc():
    """Một thành phần **chưa hề được hỏi** ⛔ không được khai là hỏng, và dòng chữ
    phải nêu nguyên nhân đủ để hành động — `(OvhError)` một mình thì không."""
    from apps.vps.services import preflight

    class _OvhChet(Exception):
        status = 403
        ma_loi = "INVALID_CREDENTIAL"

    hang_da_ghi: list = []

    class _DbGhi:
        def execute(self, _stmt):
            class _R:
                @staticmethod
                def scalars():
                    class _S:
                        @staticmethod
                        def all():
                            return ["ho-so-1"]
                    return _S()
            return _R()

        def get(self, _lop, _id):
            return type("Row", (), {"id": "ho-so-1", "last_health_at": None})()

        def add(self, hang):
            hang_da_ghi.append(hang)

        def commit(self):
            pass

        def rollback(self):
            pass

    def _no(db, row, demote_on_failure=False):
        raise _OvhChet("OVH request failed (HTTPError)")

    ket_qua = preflight.refresh_active_profiles(_DbGhi(), run=_no)
    assert ket_qua == {"ho-so-1": False}, "ho so khong ban duoc nua"
    assert hang_da_ghi, "phai ghi ban ghi suc khoe"
    assert {h.status for h in hang_da_ghi} == {"UNKNOWN"}, (
        "chua do duoc thi la UNKNOWN, khong phai CRITICAL")
    for hang in hang_da_ghi:
        assert "khong do duoc" in hang.summary
        assert "403" in hang.summary and "INVALID_CREDENTIAL" in hang.summary, (
            "dong chu phai dan tới hanh dong: ma HTTP + ma loi, khong chi ten lop")


def test_nguyen_nhan_ngan_KHONG_lay_message_cua_nha_cung_cap():
    """`message` của OVH có khi vọng lại chính yêu cầu (đường dẫn, tham số) —
    ⛔ không được vào bảng sức khoẻ. Chỉ mã HTTP + mã lỗi định danh."""
    from apps.vps.services import preflight

    class _Loi(Exception):
        status = 403
        ma_loi = "INVALID_CREDENTIAL"

    cau = preflight.nguyen_nhan_ngan(_Loi("bi mat: /ip/1.2.3.4/reverse?token=abc"))
    assert "403" in cau and "INVALID_CREDENTIAL" in cau
    assert "token" not in cau and "1.2.3.4" not in cau
