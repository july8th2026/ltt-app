"""Máy kẹt `dang_tao` vì worker bị giết ⇒ phải có một lưới bắt nó.

## Lỗ hở này hẹp hơn bản rà soát nói, nhưng thật

Đường job hỏng **có** đặt `LOI` tin cậy (`jobs.py:1251`, trong một `except` có
`commit`). Nên máy chỉ kẹt `dang_tao` khi **worker chết mà không chạy nhánh đó**:
bị `kill -9`, máy khởi động lại, mất điện. Trong dự án này chuyện worker bị giết
⛔ không phải giả thuyết — một cú giết cây tiến trình đã làm PostgreSQL sập 4 phút.

Lúc đó:

* `_don_thao_tac_qua_han` đóng thao tác treo và gỡ `tac_vu` — nhưng ⛔ **không** đổi
  `vong_doi`, nên máy vẫn `dang_tao`;
* `billing.den_han_thu` bỏ qua `dang_tao` ⇒ ⛔ không bị thu tiền (đúng);
* `_hoan_may_tao_hong` chỉ quét `trang_thai == "loi"` ⇒ ⛔ **không hoàn, không dọn**;
* vòng đối chiếu ⛔ không gọi nó là VM mồ côi, vì `vmid` **có** trong sổ.

⇒ Một hàng ⛔ không ai thu tiền, ⛔ không ai dọn, có thể kèm một VM thật giữ vmid +
  40 GB đĩa + một địa chỉ trong mạng riêng. ⛔ Không lưới nào bắt.

## Thuốc: NỐI vào đường đã có, ⛔ không dựng đường mới

Chỉ cần đưa máy về `LOI` — rồi `_hoan_may_tao_hong` (đã có, đã test) tự dọn và tự
hoàn. ⭐ Dựng một vòng dọn thứ hai là tạo hai chỗ khai cùng một luật, và đó là lớp
lỗi đã cắn nhiều lần trong kho này.

## Ba điều kiện, ⛔ thiếu một cái là bắt oan máy đang chạy

1. `vong_doi == DANG_TAO`;
2. ⛔ **không** có thao tác đang mở (`tac_vu` rỗng) — còn mở nghĩa là việc **có thể
   vẫn đang chạy** trên Proxmox;
3. cũ hơn một ngưỡng **rộng hơn hẳn** thời gian dựng máy thật (mua IP OVH là một
   lượt đặt hàng + checkout, tính bằng phút).

⛔ Và ⛔ không được bắt máy đã có `tao_xong`: nó đã từng lên, nên nó ⛔ không phải một
   lượt tạo thất bại.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apps.vps import bao_tri, trang_thai_may

LUC = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)


class _SuKien:
    def __init__(self, loai, luc):
        self.loai = loai
        self.created_at = luc


class _May:
    def __init__(self, *, vong_doi=trang_thai_may.DANG_TAO, tac_vu="",
                 tuoi_gio=5.0):
        self.id = "may-4019"
        self.user_id = "u-1"
        self.vmid = 910
        self.trang_thai = vong_doi
        self.vong_doi = vong_doi
        self.tac_vu = tac_vu
        self.ly_do = ""
        self.dien_quan_sat = trang_thai_may.KHONG_RO
        self.dien_mong_muon = trang_thai_may.CHAY
        self.created_at = LUC - timedelta(hours=tuoi_gio)


def test_may_ket_qua_lau_thi_PHAI_bat():
    xong, ly_do = bao_tri.ket_dang_tao(
        _May(tuoi_gio=5.0), su_kien=[_SuKien("tao_moi", LUC - timedelta(hours=5))],
        now=LUC)
    assert xong is True, ly_do


def test_may_VUA_tao_thi_KHONG_bat():
    """Máy đang dựng thật: bắt nó là phá một lượt tạo đang chạy."""
    xong, _ = bao_tri.ket_dang_tao(
        _May(tuoi_gio=0.2), su_kien=[_SuKien("tao_moi", LUC - timedelta(minutes=12))],
        now=LUC)
    assert xong is False


def test_con_THAO_TAC_dang_mo_thi_KHONG_bat():
    """⛔ `tac_vu` còn thì việc **có thể vẫn đang chạy** trên Proxmox."""
    xong, _ = bao_tri.ket_dang_tao(
        _May(tuoi_gio=9.0, tac_vu=trang_thai_may.DANG_CAP_PHAT),
        su_kien=[_SuKien("tao_moi", LUC - timedelta(hours=9))], now=LUC)
    assert xong is False


def test_da_co_tao_xong_thi_KHONG_bat():
    """Đã từng lên ⇒ ⛔ không phải một lượt tạo thất bại."""
    xong, _ = bao_tri.ket_dang_tao(
        _May(tuoi_gio=9.0),
        su_kien=[_SuKien("tao_moi", LUC - timedelta(hours=9)),
                 _SuKien("tao_xong", LUC - timedelta(hours=8))], now=LUC)
    assert xong is False


def test_may_KHONG_o_dang_tao_thi_KHONG_bat():
    xong, _ = bao_tri.ket_dang_tao(
        _May(vong_doi=trang_thai_may.HOAT_DONG, tuoi_gio=9.0),
        su_kien=[_SuKien("tao_moi", LUC - timedelta(hours=9))], now=LUC)
    assert xong is False


def test_khong_co_su_kien_nao_thi_dung_created_at():
    """Một hàng không có sự kiện nào vẫn phải đo được tuổi — nếu không thì đúng
    ca tệ nhất (ghi hàng xong rồi worker chết ngay) lại **lọt**."""
    xong, _ = bao_tri.ket_dang_tao(_May(tuoi_gio=9.0), su_kien=[], now=LUC)
    assert xong is True


def test_nguong_RONG_HON_han_thoi_gian_dung_may_that():
    """Bất biến số học: ngưỡng phải rộng hơn hẳn một lượt dựng máy thật.

    ⛔ Ngưỡng hẹp hơn là bắt oan máy đang dựng — và cái giá là **xoá một máy khách
    đang được tạo**, tệ hơn nhiều so với việc để một hàng mồ côi thêm một giờ.
    """
    assert bao_tri.KET_DANG_TAO_GIAY >= 2 * 3600


def test_ly_do_noi_duoc_PHAI_LAM_GI():
    _, ly_do = bao_tri.ket_dang_tao(_May(tuoi_gio=9.0), su_kien=[], now=LUC)
    assert "dang_tao" in ly_do and ("worker" in ly_do or "gio" in ly_do), ly_do
